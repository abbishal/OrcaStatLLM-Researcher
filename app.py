from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os
import uuid
import threading
import asyncio
import json
import sys
import logging
from datetime import datetime
from pathlib import Path
import io
import urllib.parse

from modules.researcher import OrcaStatLLMScientist
from modules.utils.async_buffer import AsyncBuffer
from modules.guided_research import GuidedResearchAssistant
from modules.document.pdf_converter import PDFConverter

app = Flask(__name__)


RESEARCH_DIR = Path.home() / ".orcallm" / "research"


class LogCapture(io.StringIO):
    def __init__(self, buffer):
        super().__init__()
        self.buffer = buffer
        self.old_stdout = None
        self.old_stderr = None
        self._recursive_guard = False
        
    def write(self, s):
        if s.strip() and not self._recursive_guard:  
            try:
                self._recursive_guard = True
                self.buffer.add_log(s.strip(), high_level=False)
            finally:
                self._recursive_guard = False
        return super().write(s)
    
    def flush(self):
        pass
        
    def start_capture(self):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        
    def stop_capture(self):
        if self.old_stdout:
            sys.stdout = self.old_stdout
        if self.old_stderr:
            sys.stderr = self.old_stderr

active_sessions = {}

def load_api_keys():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_research', methods=['POST'])
def start_research():
    research_details = request.form.get('research_details')
    action_type = request.form.get('action_type')
    
    if not research_details or not action_type:
        return redirect(url_for('index', error=urllib.parse.quote("Research topic and action type are required.")))
    
    session_id = str(uuid.uuid4())

    researcher = OrcaStatLLMScientist(verbose=True)
    buffer = AsyncBuffer(verbose=False)  

    active_sessions[session_id] = {
        'researcher': researcher,
        'buffer': buffer,
        'topic': research_details,
        'status': 'initializing',
        'start_time': datetime.now().isoformat(),
        'markdown_content': '',
        'logs': [],
        'log_capture': LogCapture(buffer),
        'action_type': action_type
    }
    
    buffer.add_log("Starting research process...", high_level=True)
    buffer.add_log(f"Session ID: {session_id}", high_level=True)
    buffer.add_log("Initializing research process...", high_level=True)
    
    if action_type == 'write_paper':
        thread = threading.Thread(
            target=run_research_async,
            args=(session_id, research_details, researcher, buffer)
        )
    elif action_type == 'guided_research':
        thread = threading.Thread(
            target=run_guided_research_async,
            args=(session_id, research_details, buffer)
        )
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('session', session_id=session_id))

def run_research_async(session_id, topic, researcher, buffer):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    log_capture = active_sessions[session_id]['log_capture']
    log_capture.start_capture()
    
    def navigation_handler(url):
        buffer.add_log(f"Navigating to URL: {url}", high_level=True)
    
    try:
        active_sessions[session_id]['status'] = 'researching'
        
        if hasattr(researcher, 'set_navigation_callback'):
            researcher.set_navigation_callback(navigation_handler)
        
        if hasattr(researcher, 'logger'):
            class ResearchLogHandler(logging.Handler):
                def emit(self, record):
                    log_message = self.format(record)
                    buffer.add_log(log_message, high_level=record.levelno >= logging.INFO)
            
            handler = ResearchLogHandler()
            handler.setFormatter(logging.Formatter('%(message)s'))
            researcher.logger.addHandler(handler)
            researcher.logger.setLevel(logging.DEBUG)
        
        try:
            markdown_file = loop.run_until_complete(researcher.generate_research_paper(topic))
        except TypeError as e:
            if "can't be used in 'await' expression" in str(e):
                buffer.add_log(f"Async error detected: {str(e)}. Using synchronous fallback.", high_level=True)

                markdown_file = str(Path.home() / ".orcallm" / "research" / f"{session_id}" / "error_report.md")
                with open(markdown_file, 'w') as f:
                    f.write(f"# Error Report for {topic}\n\nAn error occurred during research: {str(e)}")
            else:
                raise
    
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        active_sessions[session_id]['markdown_content'] = markdown_content
        active_sessions[session_id]['markdown_file'] = markdown_file
        active_sessions[session_id]['status'] = 'completed'
        
        buffer.add_log("Step 10: Research completed successfully", high_level=True)
        buffer.add_log("Research completed successfully!", high_level=True)
        
        if hasattr(researcher, 'progress'):
            researcher.progress['current_step'] = 10
            researcher.progress['step_name'] = "Final Document"
            researcher.progress['step_details'] = "Research document is ready"
            researcher.progress['completed_subtasks'] = len(researcher.progress.get('subtasks', []))

        pdf_file = markdown_file.replace('.md', '.pdf')

        if os.path.exists(pdf_file):
            active_sessions[session_id]['pdf_file'] = pdf_file
            buffer.add_log("PDF document generated successfully", high_level=True)
    except Exception as e:
        active_sessions[session_id]['status'] = 'error'
        active_sessions[session_id]['error'] = str(e)
        buffer.add_log(f"Error in research process: {str(e)}", high_level=True)
    finally:
        log_capture.stop_capture()
        loop.close()

def run_guided_research_async(session_id, topic, buffer):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    log_capture = active_sessions[session_id]['log_capture']
    log_capture.start_capture()
    
    try:
        active_sessions[session_id]['status'] = 'researching'

        guided_researcher = GuidedResearchAssistant(verbose=True)
        
        active_sessions[session_id]['researcher'] = guided_researcher
        
        if hasattr(guided_researcher, 'set_navigation_callback'):
            def navigation_handler(url):
                buffer.add_log(f"Navigating to URL: {url}", high_level=True)
            guided_researcher.set_navigation_callback(navigation_handler)
        
        if hasattr(guided_researcher, 'logger'):
            class ResearchLogHandler(logging.Handler):
                def emit(self, record):
                    log_message = self.format(record)
                    buffer.add_log(log_message, high_level=record.levelno >= logging.INFO)
            
            handler = ResearchLogHandler()
            handler.setFormatter(logging.Formatter('%(message)s'))
            guided_researcher.logger.addHandler(handler)
            guided_researcher.logger.setLevel(logging.DEBUG)

        markdown_file = loop.run_until_complete(guided_researcher.generate_research_guidance(topic, ["academic_sources", "literature_review", "methodology", "data_analysis"]))
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        active_sessions[session_id]['markdown_content'] = markdown_content
        active_sessions[session_id]['markdown_file'] = markdown_file
        active_sessions[session_id]['status'] = 'completed'
        
        buffer.add_log("Guided research completed successfully!", high_level=True)

        pdf_file = markdown_file.replace('.md', '.pdf')
        if os.path.exists(pdf_file):
            active_sessions[session_id]['pdf_file'] = pdf_file
            buffer.add_log("PDF document generated successfully", high_level=True)
    except Exception as e:
        active_sessions[session_id]['status'] = 'error'
        active_sessions[session_id]['error'] = str(e)
        buffer.add_log(f"Error in guided research process: {str(e)}", high_level=True)
    finally:
        log_capture.stop_capture()
        loop.close()

@app.route('/session/<session_id>')
def session(session_id):
    if session_id not in active_sessions:
        return redirect(url_for('index'))
    
    session_data = active_sessions[session_id]
    
    return render_template('session.html', 
                          session_id=session_id, 
                          topic=session_data['topic'],
                          status=session_data['status'])

@app.route('/api/session/<session_id>/status')
def session_status(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = active_sessions[session_id]
    buffer = session_data['buffer']

    all_logs = buffer.get_logs()
    for i, log in enumerate(all_logs):
        if 'id' not in log:
            log['id'] = f"log_{session_id}_{i}"
    
    url_tracking = {}
    progress_data = {}
    
    if 'researcher' in session_data:
        researcher = session_data['researcher']
        if hasattr(researcher, 'url_tracking'):
            url_tracking = researcher.url_tracking
        elif hasattr(researcher, 'research_data') and hasattr(researcher, 'get_url_tracking'):
            try:
                url_tracking = researcher.get_url_tracking()
            except:
                try:
                    url_tracking = researcher.research_data.get('url_tracking', {})
                except:
                    pass

        if hasattr(researcher, 'progress'):
            progress_data = researcher.progress
        elif hasattr(researcher, 'research_data') and hasattr(researcher, 'get_progress'):
            try:
                progress_data = researcher.get_progress()
            except:
                try:
                    progress_data = researcher.research_data.get('progress', {})
                except:
                    pass
    
    word_count = 0
    if 'markdown_content' in session_data and session_data['markdown_content']:
        word_count = len(session_data['markdown_content'].split())
    
    current_step = progress_data.get('current_step', 0)
    
    if session_data['status'] == 'completed':
        current_step = 10
        progress_data['current_step'] = 10
        progress_data['step_name'] = "Final Document"
        progress_data['step_details'] = "Research document is ready"
    
    has_pdf = False
    if 'pdf_file' in session_data:
        pdf_path = session_data['pdf_file']
        if os.path.exists(pdf_path):
            has_pdf = True
    elif 'markdown_file' in session_data:
        potential_pdf = session_data['markdown_file'].replace('.md', '.pdf')
        if os.path.exists(potential_pdf):
            session_data['pdf_file'] = potential_pdf  
            has_pdf = True

    if not has_pdf and session_data['status'] == 'completed':
        for log in all_logs:
            if "PDF document generated successfully" in log.get('message', ''):
                if 'markdown_file' in session_data:
                    potential_pdf = session_data['markdown_file'].replace('.md', '.pdf')
                    if os.path.exists(potential_pdf):
                        session_data['pdf_file'] = potential_pdf
                        has_pdf = True
                        break
    
    if session_data['status'] == 'completed':
        completion_found = False
        for log in all_logs:
            if "Research completed successfully" in log.get('message', ''):
                log['high_level'] = True
                completion_found = True

        if not completion_found:
            timestamp = datetime.now().isoformat()
            all_logs.append({
                'id': f"completion_{session_id}",
                'timestamp': timestamp,
                'message': "Research completed successfully!",
                'high_level': True
            })
    
    return jsonify({
        'status': session_data['status'],
        'logs': all_logs,
        'markdown': session_data.get('markdown_content', ''),
        'has_pdf': has_pdf,
        'url_tracking': url_tracking,
        'word_count': word_count,
        'current_step': min(current_step, 10),  
        'progress': progress_data,
        'action_type': session_data.get('action_type', 'write_paper')  
    })



@app.route('/api/session/<session_id>/download_docx')
async def download_docx(session_id):
    try:
        if session_id not in active_sessions:
            return jsonify({'error': 'Session not found'}), 404
            
        session_data = active_sessions[session_id]
        markdown_file = None
        if 'markdown_file' in session_data and os.path.exists(session_data['markdown_file']):
            markdown_file = session_data['markdown_file']
        else:
            if 'researcher' in session_data and hasattr(session_data['researcher'], 'research_dir'):
                research_dir = session_data['researcher'].research_dir
                for file in os.listdir(research_dir):
                    if file.endswith('.md') and file != 'README.md':
                        markdown_file = os.path.join(research_dir, file)
                        break
            if not markdown_file:
                session_dir = RESEARCH_DIR / session_id
                if os.path.exists(session_dir):
                    for file in os.listdir(session_dir):
                        if file.endswith('.md') and file != 'README.md':
                            markdown_file = os.path.join(session_dir, file)
                            break
        
        if not markdown_file:
            return jsonify({'error': 'Markdown file not found'}), 404
        buffer = AsyncBuffer(verbose=True)
        docx_file = markdown_file.replace('.md', '.docx')
        if not os.path.exists(docx_file):
            pdf_converter = PDFConverter()
            docx_file = await pdf_converter.convert_to_docx(markdown_file, buffer)
            if not docx_file:
                return jsonify({'error': 'Failed to generate DOCX file'}), 500
        session_data['docx_file'] = docx_file
        filename = os.path.basename(docx_file)
        return send_file(
            docx_file,
            as_attachment=True,
            download_name=filename or f"research_{session_id}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        app.logger.error(f"Error generating DOCX: {str(e)}")
        return jsonify({'error': f"Error generating DOCX: {str(e)}"}), 500
    
@app.route('/api/session/<session_id>/download_pdf')
def download_pdf(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    session_data = active_sessions[session_id]
    if 'pdf_file' not in session_data:
        return jsonify({'error': 'PDF file not found'}), 404
    pdf_file = session_data['pdf_file']
    filename = os.path.basename(pdf_file)
    return send_file(
        pdf_file,
        as_attachment=True,
        download_name=filename or f"research_{session_id}.pdf",
        mimetype='application/pdf'
    )

@app.route('/api/session/<session_id>/download_markdown')
def download_markdown(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    session_data = active_sessions[session_id]
    if 'markdown_file' not in session_data:
        return jsonify({'error': 'Markdown file not found'}), 404
    markdown_file = session_data['markdown_file']
    filename = os.path.basename(markdown_file)
    return send_file(
        markdown_file,
        as_attachment=True,
        download_name=filename or f"research_{session_id}.md",
        mimetype='text/markdown'
    )

@app.route('/api/session/<session_id>/view_pdf')
def view_pdf(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    session_data = active_sessions[session_id]
    if 'pdf_file' not in session_data:
        return jsonify({'error': 'PDF file not found'}), 404
    pdf_file = session_data['pdf_file']
    return send_file(pdf_file, mimetype='application/pdf')




if __name__ == '__main__':
    app.run(debug=True)

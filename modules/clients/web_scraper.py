from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import PyPDF2
import aiohttp
from io import BytesIO
import asyncio
import tempfile
import os
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.rate_limiter import RateLimitHandler

class WebScraper:
    def __init__(self, rate_limiter: RateLimitHandler):
        self.rate_limiter = rate_limiter
    
    async def scrape_url(self, url: str, buffer: AsyncBuffer) -> str:
        try:
            if "medium.com" in url:
                new_url = url.replace("medium.com", "md.vern.cc")
                buffer.add_log(f"Replacing medium.com URL with md.vern.cc: {new_url}", high_level=True)
                url = new_url
            
            if url.lower().endswith('.pdf'):
                buffer.add_log(f"Detected PDF URL: {url}", high_level=True)
                return await self.extract_pdf_content(url, buffer)
            
            buffer.add_log(f"Scraping URL: {url}", high_level=True)
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                if buffer.verbose:
                    buffer.add_log(f"Navigating to URL: {url}")
                
                try:
                    await page.goto(url, timeout=30000)
                except Exception as e:
                    buffer.add_log(f"Navigation error: {str(e)}")
                    await browser.close()
                    return ""
                
                title = await page.title()
                
                text = await page.evaluate("""() => {
                    const contentSelectors = [
                        'article', 'main', '.content', '#content', '.post', '.article',
                        '[role="main"]', '.main-content', '.post-content', '.entry-content',
                        'body'
                    ];
                    
                    for (const selector of contentSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.innerText.length > 200) {
                            return element.innerText;
                        }
                    }
                    
                    return document.body.innerText;
                }""")
                
                await browser.close()
                
                if buffer.verbose:
                    buffer.add_log(f"Successfully scraped URL: {url}")
                
                if len(text) > 8000:
                    text = text[:8000] + "... [content truncated]"
                
                return f"Title: {title}\nURL: {url}\nContent:\n\n{text}"
        except Exception as e:
            buffer.add_log(f"Error scraping URL {url}: {str(e)}", high_level=True)
            return f"Error scraping {url}: {str(e)}"
    
    async def extract_pdf_content(self, url: str, buffer: AsyncBuffer) -> str:

        temp_file = None
        
        try:
            if buffer.verbose:
                buffer.add_log(f"Downloading PDF from: {url}")
            timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            buffer.add_log(f"Failed to download PDF: HTTP status {response.status}")
                            return f"Failed to download PDF from {url}: HTTP status {response.status}"
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                        temp_file_path = temp_file.name
                        temp_file.close()  # Close the file so we can write to it
                        with open(temp_file_path, 'wb') as f:
                            chunk_size = 1024 * 8  # 8KB chunks
                            while True:
                                chunk = await response.content.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                        
                        buffer.add_log(f"PDF downloaded to temporary file: {temp_file_path}")
                
            except asyncio.TimeoutError:
                buffer.add_log(f"Timeout while downloading PDF from {url}", high_level=True)
                return f"Timeout while downloading PDF from {url}"
            except Exception as e:
                buffer.add_log(f"Error downloading PDF: {str(e)}", high_level=True)
                return f"Error downloading PDF: {str(e)}"
            try:
                with open(temp_file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file, strict=False)
                    num_pages = len(pdf_reader.pages)
                    buffer.add_log(f"PDF has {num_pages} pages, extracting text")
                    max_pages = min(15, num_pages)
                    
                    text_content = []
                    for page_num in range(max_pages):
                        try:
                            page = pdf_reader.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:  # Only add non-empty text
                                text_content.append(page_text)
                        except Exception as e:
                            buffer.add_log(f"Error extracting text from page {page_num}: {str(e)}")
                            continue
                    result_text = "\n\n".join(text_content)
                    if len(result_text) > 100:  # Reasonable minimum length
                        if len(result_text) > 10000:
                            result_text = result_text[:10000] + "... [PDF content truncated]"
                            
                        buffer.add_log(f"Successfully extracted {len(result_text)} characters from PDF")
                        return result_text
                    else:
                        buffer.add_log("Extracted text too short, trying alternative method", high_level=True)
            except Exception as e:
                buffer.add_log(f"Error with PyPDF2 extraction: {str(e)}", high_level=True)
            try:
                import pdfplumber
                buffer.add_log("Trying extraction with pdfplumber")
                
                with pdfplumber.open(temp_file_path) as pdf:
                    text_content = []
                    max_pages = min(15, len(pdf.pages))
                    
                    for page_num in range(max_pages):
                        try:
                            page = pdf.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:
                                text_content.append(page_text)
                        except Exception as page_error:
                            buffer.add_log(f"Error with pdfplumber on page {page_num}: {str(page_error)}")
                            continue
                    
                    result_text = "\n\n".join(text_content)
                    
                    if len(result_text) > 100:
                        if len(result_text) > 10000:
                            result_text = result_text[:10000] + "... [PDF content truncated]"
                        
                        buffer.add_log(f"Successfully extracted {len(result_text)} characters with pdfplumber")
                        return result_text
                    else:
                        buffer.add_log("pdfplumber extraction too short, trying command line tools", high_level=True)
            except ImportError:
                buffer.add_log("pdfplumber not available", high_level=True)
            except Exception as e:
                buffer.add_log(f"Error with pdfplumber extraction: {str(e)}", high_level=True)
            try:
                buffer.add_log("Trying extraction with pdftotext command line tool")
                import subprocess
                
                output_text_path = temp_file_path + ".txt"
                process = await asyncio.create_subprocess_exec(
                    "pdftotext", temp_file_path, output_text_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                _, stderr = await process.communicate()
                if process.returncode != 0:
                    buffer.add_log(f"pdftotext error: {stderr.decode()}", high_level=True)
                    raise Exception("pdftotext command failed")
                with open(output_text_path, 'r', encoding='utf-8', errors='ignore') as f:
                    result_text = f.read()
                try:
                    os.remove(output_text_path)
                except:
                    pass
                    
                if len(result_text) > 100:
                    if len(result_text) > 10000:
                        result_text = result_text[:10000] + "... [PDF content truncated]"
                        
                    buffer.add_log(f"Successfully extracted {len(result_text)} characters with pdftotext")
                    return result_text
                else:
                    buffer.add_log("pdftotext extraction too short", high_level=True)
            except Exception as e:
                buffer.add_log(f"Error with pdftotext extraction: {str(e)}", high_level=True)
            return f"Failed to extract meaningful text content from PDF at {url}"
            
        except Exception as e:
            buffer.add_log(f"Critical error in PDF extraction: {str(e)}", high_level=True)
            return f"Error extracting PDF content: {str(e)}"
            
        finally:
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass


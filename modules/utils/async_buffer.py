import datetime
import logging
import colorama
from typing import Dict, List, Any
import re
import uuid
import sys

colorama.init(autoreset=True)

logger = logging.getLogger("OrcaStatLLM-Scientist")

class AsyncBuffer:
    def __init__(self, verbose=False):
        self.buffer = ""
        self.complete = False
        self.response_metadata = None
        self.logs = []
        self.verbose = verbose
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._stdout = sys.stdout  # Store the original stdout
        self._in_add_log = False   # Flag to prevent recursion

    def add_chunk(self, text: str):
        self.buffer += text
        return text

    def add_log(self, log: str, high_level=False, timestamp=None):
        if self._in_add_log:
            return None
            
        self._in_add_log = True
        
        try:
            if timestamp is None:
                timestamp = datetime.datetime.now().isoformat()
            if isinstance(log, str):
                log = self._strip_ansi(log)
            log_id = str(uuid.uuid4())
            
            log_entry = {
                'id': log_id,
                'timestamp': timestamp,
                'message': log,
                'high_level': high_level
            }
            
            logger.info(log)
            if high_level or self.verbose:
                print(f"{colorama.Fore.GREEN}[RESEARCHER]{colorama.Style.RESET_ALL} {log}", file=self._stdout)
                    
            self.logs.append(log_entry)
            
            return log_entry
        finally:
            self._in_add_log = False

    def get_buffer(self) -> str:
        return self.buffer

    def get_logs(self) -> List[Dict]:
        return self.logs

    def mark_complete(self, metadata: Dict):
        self.complete = True
        self.response_metadata = metadata
        
    def _strip_ansi(self, text):

        return self._ansi_escape.sub('', text)

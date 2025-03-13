import traceback
import datetime
import logging
from typing import Dict, Callable, Any, Optional

logger = logging.getLogger("OrcaStatLLM-Scientist")

def log_exception(e: Exception, message: str, buffer: Any = None, 
                 research_data: Optional[Dict] = None, 
                 save_callback: Optional[Callable] = None):
    tb_str = traceback.format_exception(type(e), e, e.__traceback__)
    error_details = "".join(tb_str)
    logger.error(f"{message}: {str(e)}\n{error_details}")
    
    if buffer:
        buffer.add_log(f"{message}: {str(e)}", high_level=True)
    if research_data is not None:
        if "errors" not in research_data:
            research_data["errors"] = []
        
        research_data["errors"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "message": message,
            "error": str(e),
            "traceback": error_details
        })
        
        if save_callback:
            save_callback()


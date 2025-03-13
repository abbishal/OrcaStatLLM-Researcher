from typing import Dict, List, Any

class ProgressTracker:
    def __init__(self):
        self.progress = self.get_initial_progress()
        
    def get_initial_progress(self) -> Dict[str, Any]:

        return {
            "current_step": 0,
            "max_steps": 10,
            "step_name": "Initializing",
            "step_details": "",
            "subtasks": [],
            "completed_subtasks": 0,
            "analyzing_count": 0
        }
        
    def reset_progress(self) -> Dict[str, Any]:

        self.progress = self.get_initial_progress()
        return self.progress
        
    def update_step(self, step_number: int, step_name: str, step_details: str, 
                   subtasks: List[str], completed_subtasks: int = 0) -> Dict[str, Any]:

        self.progress["current_step"] = step_number
        self.progress["step_name"] = step_name
        self.progress["step_details"] = step_details
        self.progress["subtasks"] = subtasks
        self.progress["completed_subtasks"] = completed_subtasks
        return self.progress
        
    def complete_current_step(self) -> Dict[str, Any]:

        self.progress["completed_subtasks"] = len(self.progress["subtasks"])
        return self.progress


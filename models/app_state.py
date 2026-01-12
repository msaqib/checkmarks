"""Application state management"""
import threading


class AppState:
    """Manages application state"""
    
    def __init__(self):
        # Browser session management
        self.playwright = None
        self.browser = None
        self.page = None
        self.browser_ready = False
        self.browser_lock = threading.Lock()
        
        # State management
        self.courses = []
        self.assignments = []
        self.students_missing = []
        self.current_course_index = None
        self.current_assignment_index = None
        self.course_list_url = "https://lms.lums.edu.pk/"
        
        # Loading state
        self.is_loading = False
    
    def reset(self):
        """Reset state for new session"""
        self.browser_ready = False
        self.courses = []
        self.assignments = []
        self.students_missing = []
        self.current_course_index = None
        self.current_assignment_index = None
        self.is_loading = False

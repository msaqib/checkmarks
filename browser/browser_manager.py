"""Browser management with threading and queue-based operations"""
import threading
import time
import traceback
import sys
from queue import Queue, Empty
from playwright.sync_api import sync_playwright
from browser.portal_scraper import PortalScraper


class BrowserManager:
    """Manages browser thread and queues Playwright operations"""
    
    def __init__(self, state_manager, ui_callback):
        """
        Initialize browser manager
        
        Args:
            state_manager: Object with browser_lock, browser, page, etc.
            ui_callback: Function to safely schedule UI updates (safe_after wrapper)
        """
        self.state_manager = state_manager
        self.ui_callback = ui_callback
        
        self.playwright = None
        self.browser_thread = None
        self.browser_queue = Queue()
        self.scraper = None
    
    def start_browser_worker(self):
        """Start the browser worker thread if not already running"""
        if self.browser_thread is None or not self.browser_thread.is_alive():
            self.browser_thread = threading.Thread(target=self._browser_worker, daemon=True)
            self.browser_thread.start()
            # Give thread time to initialize
            time.sleep(0.5)
    
    def queue_login(self, username, password, on_success, on_error, status_callback):
        """
        Queue a login operation
        
        Args:
            username: Login username
            password: Login password
            on_success: Callback(courses) for successful login
            on_error: Callback(error_type) for login error
            status_callback: Callback(message) for status updates
        """
        self.start_browser_worker()
        
        self.browser_queue.put({
            'type': 'login',
            'username': username,
            'password': password,
            'on_success': on_success,
            'on_error': on_error,
            'status_callback': status_callback
        })
    
    def queue_fetch_assignments(self, selected_course, on_success, on_error):
        """
        Queue a fetch assignments operation
        
        Args:
            selected_course: Course dict with index
            on_success: Callback(assignments) for success
            on_error: Callback(error_message) for error
        """
        self.browser_queue.put({
            'type': 'fetch_assignments',
            'course': selected_course,
            'on_success': on_success,
            'on_error': on_error
        })
    
    def queue_process_assignment(self, selected_assignment, on_success, on_error):
        """
        Queue a process assignment operation
        
        Args:
            selected_assignment: Assignment dict with index
            on_success: Callback(students_missing) for success
            on_error: Callback(error_message) for error
        """
        self.browser_queue.put({
            'type': 'process_assignment',
            'assignment': selected_assignment,
            'on_success': on_success,
            'on_error': on_error
        })
    
    def _browser_worker(self):
        """Single browser worker thread that handles all Playwright operations"""
        browser = None
        try:
            print(f"[DEBUG] browser_worker started in thread: {threading.current_thread().name}")
            
            # Initialize playwright in this thread
            self.playwright = sync_playwright().start()
            browser = self.playwright.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Store browser/page in this thread's context
            with self.state_manager.browser_lock:
                self.state_manager.browser = browser
                self.state_manager.page = page
            
            # Create scraper instance
            self.scraper = PortalScraper(page, self.state_manager, self.ui_callback)
            
            # Process operations from queue
            while True:
                try:
                    operation = self.browser_queue.get(timeout=1.0)
                    if operation is None:  # Shutdown signal
                        break
                    
                    op_type = operation.get('type')
                    
                    if op_type == 'login':
                        self._handle_login(operation, page)
                    elif op_type == 'fetch_assignments':
                        self._handle_fetch_assignments(operation, page)
                    elif op_type == 'process_assignment':
                        self._handle_process_assignment(operation, page)
                    
                    self.browser_queue.task_done()
                except Empty:
                    # Queue timeout - continue loop to check for shutdown
                    continue
                except Exception as e:
                    print(f"ERROR in browser_worker processing operation: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    sys.stderr.flush()
                    try:
                        self.browser_queue.task_done()
                    except:
                        pass
                    
        except Exception as e:
            print(f"ERROR in browser_worker: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
    
    def _handle_login(self, operation, page):
        """Handle login operation"""
        username = operation['username']
        password = operation['password']
        on_success = operation['on_success']
        on_error = operation['on_error']
        status_callback = operation['status_callback']
        
        success, courses, course_list_url, error_type = self.scraper.login(
            username, password, status_callback
        )
        
        if success:
            self.ui_callback(0, on_success, courses)
        else:
            self.ui_callback(0, on_error, error_type)
    
    def _handle_fetch_assignments(self, operation, page):
        """Handle fetch assignments operation"""
        selected_course = operation['course']
        on_success = operation['on_success']
        on_error = operation['on_error']
        
        success, assignments, error_message = self.scraper.fetch_assignments(selected_course)
        
        if success:
            self.ui_callback(0, on_success, assignments)
        else:
            self.ui_callback(0, on_error, error_message)
    
    def _handle_process_assignment(self, operation, page):
        """Handle process assignment operation"""
        selected_assignment = operation['assignment']
        on_success = operation['on_success']
        on_error = operation['on_error']
        
        success, students_missing, error_message = self.scraper.process_assignment(selected_assignment)
        
        if success:
            with self.state_manager.browser_lock:
                self.state_manager.students_missing = students_missing
            self.ui_callback(0, on_success, students_missing)
        else:
            self.ui_callback(0, on_error, error_message)
    
    def shutdown(self):
        """Signal browser worker to shutdown"""
        if self.browser_queue:
            try:
                self.browser_queue.put(None)  # Shutdown signal
            except:
                pass
        
        # Wait for browser thread to finish (with timeout)
        if self.browser_thread and self.browser_thread.is_alive():
            self.browser_thread.join(timeout=2.0)
        
        # Fallback cleanup
        if hasattr(self.state_manager, 'browser') and self.state_manager.browser:
            try:
                self.state_manager.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
        
        self.playwright = None
        if hasattr(self.state_manager, 'browser'):
            self.state_manager.browser = None
        if hasattr(self.state_manager, 'page'):
            self.state_manager.page = None
    
    def reset(self):
        """Reset browser manager for new session"""
        old_thread = self.browser_thread
        old_queue = self.browser_queue
        
        # Create new queue
        self.browser_queue = Queue()
        self.browser_thread = None
        
        # Cleanup old thread in background
        def cleanup_async():
            if old_queue:
                try:
                    old_queue.put(None)  # Shutdown signal
                except:
                    pass
            if old_thread and old_thread.is_alive():
                old_thread.join(timeout=2.0)
            if hasattr(self.state_manager, 'browser') and self.state_manager.browser:
                try:
                    self.state_manager.browser.close()
                except:
                    pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
            self.playwright = None
        
        cleanup_thread = threading.Thread(target=cleanup_async, daemon=True)
        cleanup_thread.start()

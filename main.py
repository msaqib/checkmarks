from playwright.sync_api import sync_playwright
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import traceback
import sys
from queue import Queue, Empty
import keyring

class CoursePortalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Course Portal - Missing Grades Checker")
        self.root.geometry("900x700")
        
        # Browser session management
        self.playwright = None
        self.browser = None
        self.page = None
        self.browser_ready = False
        self.browser_thread = None
        self.browser_queue = Queue()
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
        
        self.create_login_widgets()
        
    def create_login_widgets(self):
        """Create login window - shown initially"""
        # Login container
        self.login_frame = ttk.Frame(self.root, padding="20")
        self.login_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Center the login form
        login_container = ttk.Frame(self.login_frame)
        login_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        ttk.Label(login_container, text="Username:", font=("", 10)).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.username_entry = ttk.Entry(login_container, width=30, font=("", 10))
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(login_container, text="Password:", font=("", 10)).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.password_entry = ttk.Entry(login_container, width=30, show="*", font=("", 10))
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)
        
        # Remember me checkbox
        self.remember_me_var = tk.BooleanVar()
        remember_me_checkbox = ttk.Checkbutton(login_container, text="Remember me", variable=self.remember_me_var)
        remember_me_checkbox.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)
        
        self.login_button = ttk.Button(login_container, text="Login", command=self.on_login_clicked, width=15)
        self.login_button.grid(row=3, column=0, columnspan=2, padx=10, pady=20)
        
        # Error message label
        self.login_error_label = ttk.Label(login_container, text="", foreground="red", font=("", 9))
        self.login_error_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5)
        
        # Load saved credentials
        self.load_saved_credentials()
        
        # Bind Enter key to login
        self.username_entry.bind('<Return>', lambda e: self.on_login_clicked())
        self.password_entry.bind('<Return>', lambda e: self.on_login_clicked())
        
    def create_main_widgets(self):
        """Create main application window - shown after successful login"""
        # Main container with padding
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Three column layout for courses, assignments, and students
        courses_frame = ttk.LabelFrame(self.main_frame, text="Courses", padding="10")
        courses_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        courses_frame.columnconfigure(0, weight=1)
        courses_frame.rowconfigure(0, weight=1)
        
        courses_scrollbar = ttk.Scrollbar(courses_frame, orient=tk.VERTICAL)
        self.courses_listbox = tk.Listbox(courses_frame, yscrollcommand=courses_scrollbar.set, height=15)
        courses_scrollbar.config(command=self.courses_listbox.yview)
        self.courses_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        courses_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.courses_listbox.bind('<<ListboxSelect>>', self.on_course_selected)
        
        assignments_frame = ttk.LabelFrame(self.main_frame, text="Assignments", padding="10")
        assignments_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        assignments_frame.columnconfigure(0, weight=1)
        assignments_frame.rowconfigure(0, weight=1)
        
        assignments_scrollbar = ttk.Scrollbar(assignments_frame, orient=tk.VERTICAL)
        self.assignments_listbox = tk.Listbox(assignments_frame, yscrollcommand=assignments_scrollbar.set, height=15)
        assignments_scrollbar.config(command=self.assignments_listbox.yview)
        self.assignments_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        assignments_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.assignments_listbox.bind('<<ListboxSelect>>', self.on_assignment_selected)
        
        students_frame = ttk.LabelFrame(self.main_frame, text="Students Missing Grades", padding="10")
        students_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        students_frame.columnconfigure(0, weight=1)
        students_frame.rowconfigure(0, weight=1)
        
        students_scrollbar = ttk.Scrollbar(students_frame, orient=tk.VERTICAL)
        self.students_listbox = tk.Listbox(students_frame, yscrollcommand=students_scrollbar.set, height=15)
        students_scrollbar.config(command=self.students_listbox.yview)
        self.students_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        students_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Sign Out button at the top right
        signout_frame = ttk.Frame(self.main_frame)
        signout_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.E, tk.N), padx=5, pady=5)
        self.signout_button = ttk.Button(signout_frame, text="Sign Out", command=self.on_signout_clicked)
        self.signout_button.pack(side=tk.RIGHT)
        
        # Status bar at the bottom
        status_frame = ttk.Frame(self.main_frame, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Ready", anchor=tk.W, padding="5")
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=1)
        self.main_frame.rowconfigure(1, weight=1)  # Row 1 is for courses/assignments/students
        
    def safe_after(self, delay, func, *args):
        """Safely schedule a callback on the main thread from any thread"""
        try:
            self.root.after(delay, func, *args)
        except (tk.TclError, RuntimeError) as e:
            # Handle cases where root is destroyed or thread issues occur
            print(f"ERROR in safe_after: {type(e).__name__}: {e}")
            print("Traceback:")
            traceback.print_exc()
            sys.stderr.flush()
        
    def show_loading(self, message="Loading..."):
        """Show loading animation on status bar"""
        try:
            self.status_label.config(text=message, foreground="blue")
            self.is_loading = True
            self.safe_after(0, self._animate_loading, message, 0)
        except (tk.TclError, RuntimeError) as e:
            print(f"ERROR in show_loading: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        except Exception as e:
            print(f"UNEXPECTED ERROR in show_loading: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        
    def _animate_loading(self, base_message, dot_count):
        """Animate loading dots"""
        try:
            if not self.is_loading:
                try:
                    self.status_label.config(text="")
                except (tk.TclError, RuntimeError) as e:
                    print(f"ERROR in _animate_loading (label.config): {type(e).__name__}: {e}")
                    traceback.print_exc()
                    sys.stderr.flush()
                return
            dots = "." * ((dot_count % 3) + 1)
            self.status_label.config(text=f"{base_message}{dots}", foreground="blue")
            self.safe_after(500, self._animate_loading, base_message, dot_count + 1)
        except (tk.TclError, RuntimeError) as e:
            # Handle cases where root is destroyed or thread issues occur
            print(f"ERROR in _animate_loading: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        except Exception as e:
            print(f"UNEXPECTED ERROR in _animate_loading: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        
    def hide_loading(self):
        """Hide loading animation"""
        try:
            self.status_label.config(text="")
            self.is_loading = False
        except (tk.TclError, RuntimeError):
            # Handle cases where root is destroyed
            pass
    
    def set_status(self, message, color="black"):
        """Set status bar message"""
        try:
            self.status_label.config(text=message, foreground=color)
        except (tk.TclError, RuntimeError):
            pass
        
    def save_credentials(self, username, password):
        """Save credentials to system keyring"""
        try:
            service_name = "CoursePortalLMS"
            keyring.set_password(service_name, username, password)
            # Store that we have saved credentials
            keyring.set_password(service_name, "_remember_me", "true")
            keyring.set_password(service_name, "_username", username)
        except Exception as e:
            print(f"Error saving credentials: {e}")
    
    def load_saved_credentials(self):
        """Load saved credentials from system keyring and pre-fill form"""
        try:
            service_name = "CoursePortalLMS"
            # Check if we have saved credentials
            remember_me = keyring.get_password(service_name, "_remember_me")
            if remember_me == "true":
                username = keyring.get_password(service_name, "_username")
                if username:
                    password = keyring.get_password(service_name, username)
                    if password:
                        self.username_entry.insert(0, username)
                        self.password_entry.insert(0, password)
                        self.remember_me_var.set(True)
        except Exception as e:
            print(f"Error loading credentials: {e}")
    
    def clear_saved_credentials(self):
        """Clear saved credentials from system keyring"""
        try:
            service_name = "CoursePortalLMS"
            username = keyring.get_password(service_name, "_username")
            if username:
                keyring.delete_password(service_name, username)
            keyring.delete_password(service_name, "_remember_me")
            keyring.delete_password(service_name, "_username")
        except Exception as e:
            print(f"Error clearing credentials: {e}")
    
    def on_login_clicked(self):
        """Handle login button click"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Clear previous error
        self.login_error_label.config(text="")
        
        if not username or not password:
            self.login_error_label.config(text="Please enter both username and password")
            return
            
        self.login_button.config(state="disabled")
        self.username_entry.config(state="disabled")
        self.password_entry.config(state="disabled")
        self.login_error_label.config(text="Logging in...", foreground="blue")
        
        # Store username and remember_me state for later use
        self.current_username = username
        self.current_remember_me = self.remember_me_var.get()
        
        # Run login in separate thread
        thread = threading.Thread(target=self.login_and_fetch_courses, args=(username, password), daemon=True)
        thread.start()
        
    def browser_worker(self):
        """Single browser worker thread that handles all Playwright operations"""
        browser = None
        try:
            print(f"[DEBUG] browser_worker started in thread: {threading.current_thread().name}")
            
            # Initialize playwright in this thread
            self.playwright = sync_playwright().start()
            browser = self.playwright.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Store browser/page in this thread's context
            with self.browser_lock:
                self.browser = browser
                self.page = page
            
            # Process operations from queue
            while True:
                try:
                    operation = self.browser_queue.get(timeout=1.0)
                    if operation is None:  # Shutdown signal
                        break
                        
                    op_type = operation.get('type')
                    
                    if op_type == 'login':
                        username = operation['username']
                        password = operation['password']
                        self._do_login(page, username, password)
                    elif op_type == 'fetch_assignments':
                        selected_course = operation['course']
                        self._do_fetch_assignments(page, selected_course)
                    elif op_type == 'process_assignment':
                        selected_assignment = operation['assignment']
                        self._do_process_assignment(page, selected_assignment)
                        
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
    
    def _do_login(self, page, username, password):
        """Perform login operation - runs in browser thread"""
        try:
            print("[DEBUG] _do_login: Opening browser...")
            self.safe_after(0, self.update_login_status, "Connecting to server...")
            
            page.goto("https://lms.lums.edu.pk/", timeout=30000)

            print("[DEBUG] _do_login: Entering credentials...")
            self.safe_after(0, self.update_login_status, "Entering credentials...")
            
            page.fill('input[name="eid"]', username)
            page.fill('input[name="pw"]', password)
            page.click('input[type="submit"]')
            page.wait_for_load_state("networkidle")

            # Check if login was successful by verifying login form fields are gone
            # If login failed, we're still on the login page and the fields will still exist
            eid_input = page.query_selector('input[name="eid"]')
            pw_input = page.query_selector('input[name="pw"]')
            
            if eid_input is not None or pw_input is not None:
                # Login fields still exist - login failed
                raise Exception("Login failed: Invalid credentials")

            print("[DEBUG] _do_login: Login successful! Fetching courses...")
            self.safe_after(0, self.update_login_status, "Fetching courses...")
            time.sleep(0.5)
            
            # Fetch courses
            course_elements = page.query_selector_all(".link-container")
            courses = []
            for element in course_elements:
                name = element.inner_text().strip()
                if name:
                    courses.append({"name": name, "index": len(courses)})
            
            # Store course list URL and browser/page for later use
            course_list_url = page.url
            with self.browser_lock:
                self.browser_ready = True
                self.courses = courses
                self.course_list_url = course_list_url
            
            print("[DEBUG] _do_login: Calling on_login_success")
            self.safe_after(0, self.on_login_success, courses)
            
        except Exception as e:
            print(f"ERROR in _do_login: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
            # Check if it's a network/timeout error
            error_msg = str(e).lower()
            if "timeout" in error_msg or "network" in error_msg or "navigation" in error_msg or "net::" in error_msg or "err_name_not_resolved" in error_msg:
                self.safe_after(0, self.on_login_error, "connection")
            else:
                self.safe_after(0, self.on_login_error, "credentials")
    
    def login_and_fetch_courses(self, username, password):
        """Queue login operation to browser thread"""
        # Start browser worker thread if not already running
        if self.browser_thread is None or not self.browser_thread.is_alive():
            self.browser_thread = threading.Thread(target=self.browser_worker, daemon=True)
            self.browser_thread.start()
            # Give thread time to initialize
            time.sleep(0.5)
        
        # Queue the login operation
        self.browser_queue.put({
            'type': 'login',
            'username': username,
            'password': password
        })
            
    def update_loading_message(self, message):
        """Update status message from worker thread (main window)"""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.config(text=message, foreground="blue")
        except (tk.TclError, RuntimeError) as e:
            print(f"ERROR in update_loading_message: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        except Exception as e:
            print(f"UNEXPECTED ERROR in update_loading_message: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
    
    def update_login_status(self, message):
        """Update login status message (login window)"""
        try:
            if hasattr(self, 'login_error_label'):
                self.login_error_label.config(text=message, foreground="blue")
        except (tk.TclError, RuntimeError) as e:
            print(f"ERROR in update_login_status: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        except Exception as e:
            print(f"UNEXPECTED ERROR in update_login_status: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        
    def on_login_success(self, courses):
        """Handle successful login - switch to main window"""
        # Save credentials if "Remember me" is checked
        if hasattr(self, 'current_remember_me') and self.current_remember_me:
            if hasattr(self, 'current_username'):
                password = self.password_entry.get().strip()
                self.save_credentials(self.current_username, password)
        else:
            # Clear saved credentials if "Remember me" is unchecked
            self.clear_saved_credentials()
        
        # Hide login window
        self.login_frame.grid_remove()
        
        # Create and show main window
        if not hasattr(self, 'main_frame'):
            self.create_main_widgets()
        else:
            self.main_frame.grid()
        
        # Populate courses list
        self.courses_listbox.delete(0, tk.END)
        for course in courses:
            self.courses_listbox.insert(tk.END, course["name"])
        
        self.set_status("Ready", "black")
            
    def on_login_error(self, error_type):
        """Handle login error - show error message in login window"""
        # Clean up browser if it exists
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
        self.browser_ready = False
        
        # Show appropriate error message
        if error_type == "connection":
            error_msg = "You may not be connected to the Internet"
        else:  # credentials
            error_msg = "Username or password is incorrect"
        
        self.login_error_label.config(text=error_msg, foreground="red")
        
        # Re-enable login controls
        self.login_button.config(state="normal")
        self.username_entry.config(state="normal")
        self.password_entry.config(state="normal")
        # Clear password field on error for security
        self.password_entry.delete(0, tk.END)
        
    def on_course_selected(self, event):
        """Handle course selection"""
        try:
            print(f"[DEBUG] on_course_selected called in thread: {threading.current_thread().name}")
            if not self.browser_ready:
                return
                
            selection = self.courses_listbox.curselection()
            if not selection:
                return
                
            course_index = selection[0]
            
            # If clicking the same course, do nothing
            if course_index == self.current_course_index:
                return
                
            self.current_course_index = course_index
            selected_course = self.courses[course_index]
            
            # Clear assignments and students when switching courses
            self.assignments_listbox.delete(0, tk.END)
            self.students_listbox.delete(0, tk.END)
            self.current_assignment_index = None
            self.assignments = []
            self.students_missing = []
            
            # Show loading for assignments
            self.is_loading = True
            print("[DEBUG] Calling show_loading for assignments")
            self.show_loading("Fetching assignments...")
            
            # Queue fetch_assignments operation to browser thread
            print("[DEBUG] Queueing fetch_assignments operation")
            self.browser_queue.put({
                'type': 'fetch_assignments',
                'course': selected_course
            })
            print("[DEBUG] Operation queued")
        except Exception as e:
            print(f"ERROR in on_course_selected: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
        
    def _do_fetch_assignments(self, page, selected_course):
        """Fetch assignments for selected course - runs in browser thread"""
        try:
            print(f"[DEBUG] _do_fetch_assignments started in thread: {threading.current_thread().name}")
            # Navigate back to course list if we're not already there
            current_url = page.url
            with self.browser_lock:
                course_list_url = self.course_list_url
            if course_list_url not in current_url:
                page.goto(course_list_url)
            page.wait_for_load_state("networkidle")

            # Re-fetch course elements
            course_elements = page.query_selector_all(".link-container")
            course_index = selected_course["index"]
            
            if course_index < len(course_elements):
                course_elements[course_index].click()
                page.wait_for_load_state("networkidle")
            else:
                raise Exception(f"Course element at index {course_index} not found")
            
            # Click on Assignments section
            assignment_div = page.get_by_text("Assignments", exact=True)
            assignment_div.wait_for(state="visible")
            assignment_div.click()
            page.wait_for_load_state("networkidle")
                
                # Fetch assignment elements
            row_elems = page.query_selector_all('td:has(> strong > a[name="asnActionLink"])')
            assignment_elements = []
            grades_elements = []
                
            for td in row_elems:
                anchors = td.query_selector_all('strong > a[name="asnActionLink"]')
                grades = td.query_selector_all('xpath=.//*[normalize-space(text())="Grade"]')
                assignment_elements.extend(anchors)
                grades_elements.extend(grades)
            
            assignments = []
            for i, element in enumerate(assignment_elements):
                name = element.inner_text().strip()
                if name and i < len(grades_elements):
                    assignments.append({
                        "name": name,
                        "index": len(assignments),
                        "grade_element_index": i
                    })
                
                # Store assignments (without element references - they'll be re-fetched when needed)
                with self.browser_lock:
                    self.assignments = assignments
                
                print("[DEBUG] Calling safe_after for on_assignments_fetched")
                self.safe_after(0, self.on_assignments_fetched, assignments)
                print("[DEBUG] _do_fetch_assignments completed")
            
        except Exception as e:
            print(f"ERROR in _do_fetch_assignments: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
            self.safe_after(0, self.on_assignments_error, str(e))
            
    def on_assignments_fetched(self, assignments):
        """Handle assignments fetched - update UI"""
        self.is_loading = False
        self.hide_loading()
        self.set_status(f"Found {len(assignments)} assignment(s)", "black")
        
        # Populate assignments list
        self.assignments_listbox.delete(0, tk.END)
        for assignment in assignments:
            self.assignments_listbox.insert(tk.END, assignment["name"])
            
    def on_assignments_error(self, error_message):
        """Handle error fetching assignments"""
        self.is_loading = False
        self.hide_loading()
        self.set_status(f"Error: {error_message}", "red")
        
    def on_assignment_selected(self, event):
        """Handle assignment selection"""
        if not self.browser_ready or not self.assignments:
            return
            
        selection = self.assignments_listbox.curselection()
        if not selection:
            return
            
        assignment_index = selection[0]
        
        # If clicking the same assignment, do nothing
        if assignment_index == self.current_assignment_index:
            return
            
        self.current_assignment_index = assignment_index
        selected_assignment = self.assignments[assignment_index]
        
        # Clear students list
        self.students_listbox.delete(0, tk.END)
        self.students_missing = []
        
        # Show loading for students
        self.is_loading = True
        self.show_loading("Processing assignment...")
        
        # Queue process_assignment operation to browser thread
        self.browser_queue.put({
            'type': 'process_assignment',
            'assignment': selected_assignment
        })
    
    def _do_process_assignment(self, page, selected_assignment):
        """Process assignment and find students with missing grades - runs in browser thread"""
        try:
            print(f"[DEBUG] _do_process_assignment started in thread: {threading.current_thread().name}")
            
            # Check if we're on a submission page (from a previous assignment)
            # If so, navigate back to assignments page
            submission_table = page.query_selector("table#submissionList")
            if submission_table:
                # We're on a submission page, need to go back to assignments
                print("[DEBUG] On submission page, navigating back to assignments")
                # page.go_back()
                btn_assgn = page.query_selector('li.firstToolBarItem span a')
                btn_assgn.click()
                page.wait_for_load_state("networkidle")
            
            # Ensure we're on the assignments page (should be after _do_fetch_assignments)
            # Check for span element with class "Mrphs-toolTitleNav__text" and text "Assignments"
            assignment_span = page.query_selector('span.Mrphs-toolTitleNav__text')
            is_on_assignments_page = assignment_span and "Assignments" in assignment_span.inner_text()
            
            if not is_on_assignments_page:
                # Not on assignments page, need to navigate back
                print("[DEBUG] Not on assignments page, navigating...")
                with self.browser_lock:
                    current_course_index = self.current_course_index
                    course_list_url = self.course_list_url
                
                current_url = page.url
                if course_list_url not in current_url:
                    page.goto(course_list_url)
                    page.wait_for_load_state("networkidle")
                
                course_elements = page.query_selector_all(".link-container")
                if current_course_index < len(course_elements):
                    course_elements[current_course_index].click()
                    page.wait_for_load_state("networkidle")
                
                assignment_div = page.get_by_text("Assignments", exact=True)
                assignment_div.wait_for(state="visible")
                assignment_div.click()
                page.wait_for_load_state("networkidle")

            # Re-fetch assignment grade elements (handles may be stale)
            row_elems = page.query_selector_all('td:has(> strong > a[name="asnActionLink"])')
            grades_elements = []
            for td in row_elems:
                grades = td.query_selector_all('xpath=.//*[normalize-space(text())="Grade"]')
                grades_elements.extend(grades)
            
            # Click on Grade button for the selected assignment
            assignment_index = selected_assignment["index"]
            if assignment_index < len(grades_elements):
                grades_elements[assignment_index].click()
                page.wait_for_load_state("networkidle")
            else:
                raise Exception(f"Grade element at index {assignment_index} not found")
            
            # Find students without marks
            table = page.query_selector("table#submissionList")
            rows = table.query_selector_all("tr") if table else []
            
            students_missing = []
            for row in rows:
                td_elements = row.query_selector_all("td")
                if len(td_elements) > 0:
                    status_elem = row.query_selector('td[headers="status"]')
                    student_elem = row.query_selector('td[headers="studentname"]')
                    
                    if status_elem and student_elem:
                        status = status_elem.inner_text().strip()
                        student_name = student_elem.inner_text().strip()
                        
                                # Logic: If status is not "Returned" and not "No Submission - Not Started"
                    if status and status != "Returned" and status != "No Submission - Not Started":
                                    students_missing.append({"name": student_name, "status": status})
                    # except Exception:
                    #     continue  # Skip rows that don't match expected format
            
            with self.browser_lock:
                self.students_missing = students_missing
                
            print("[DEBUG] Calling safe_after for on_students_processed")
            # Update UI on main thread
            self.safe_after(0, self.on_students_processed, students_missing)
            print("[DEBUG] _do_process_assignment completed")
            
        except Exception as e:
            print(f"ERROR in _do_process_assignment: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
            self.safe_after(0, self.on_students_error, str(e))
            
    def on_students_processed(self, students_missing):
        """Handle students processed - update UI"""
        self.is_loading = False
        self.hide_loading()
        
        # Populate students list
        self.students_listbox.delete(0, tk.END)
        if students_missing:
            for student in students_missing:
                self.students_listbox.insert(tk.END, f"{student['name']} - {student['status']}")
            count_text = f"Found {len(students_missing)} student(s) with missing grades"
            self.set_status(count_text, "orange")
        else:
            self.students_listbox.insert(tk.END, "All students have marks entered!")
            self.set_status("All students have marks!", "green")
            
    def on_students_error(self, error_message):
        """Handle error processing students"""
        self.is_loading = False
        self.hide_loading()
        self.set_status(f"Error: {error_message}", "red")
        
    def on_signout_clicked(self):
        """Handle sign out button click"""
        # Hide main window first (immediate UI response)
        if hasattr(self, 'main_frame'):
            self.main_frame.grid_remove()
        
        # Show login window immediately (before cleanup)
        self.login_frame.grid()
        
        # Clear password field for security
        self.password_entry.delete(0, tk.END)
        self.login_error_label.config(text="")
        
        # Reset remember me checkbox state
        self.remember_me_var.set(False)
        
        # Re-enable login controls
        self.login_button.config(state="normal")
        self.username_entry.config(state="normal")
        self.password_entry.config(state="normal")
        
        # Clear state
        self.browser_ready = False
        self.courses = []
        self.assignments = []
        self.students_missing = []
        self.current_course_index = None
        self.current_assignment_index = None
        
        # Clear listboxes
        if hasattr(self, 'courses_listbox'):
            self.courses_listbox.delete(0, tk.END)
        if hasattr(self, 'assignments_listbox'):
            self.assignments_listbox.delete(0, tk.END)
        if hasattr(self, 'students_listbox'):
            self.students_listbox.delete(0, tk.END)
        
        # Save old thread and queue references before resetting (for cleanup)
        old_thread = self.browser_thread
        old_queue = self.browser_queue
        
        # Reset browser thread and queue immediately (so login can start fresh)
        self.browser_thread = None
        self.browser_queue = Queue()
        
        # Clean up browser resources in background thread (non-blocking)
        def cleanup_async():
            # Signal old thread to shutdown using old queue
            if old_queue:
                try:
                    old_queue.put(None)  # Shutdown signal
                except:
                    pass
            
            # Wait for old thread to finish (with timeout)
            if old_thread and old_thread.is_alive():
                old_thread.join(timeout=2.0)
            
            # Fallback cleanup of browser resources
            if hasattr(self, 'browser') and self.browser:
                try:
                    self.browser.close()
                except:
                    pass
            if hasattr(self, 'playwright') and self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
            
            # Final cleanup
            self.browser = None
            self.page = None
            self.playwright = None
        
        cleanup_thread = threading.Thread(target=cleanup_async, daemon=True)
        cleanup_thread.start()
    
    def cleanup_browser(self):
        """Clean up browser resources"""
        # Signal browser thread to shutdown
        if hasattr(self, 'browser_queue') and self.browser_queue:
            try:
                self.browser_queue.put(None)  # Shutdown signal
            except:
                pass
        
        # Wait for browser thread to finish (with timeout)
        if hasattr(self, 'browser_thread') and self.browser_thread and self.browser_thread.is_alive():
            self.browser_thread.join(timeout=2.0)
        
        # Fallback cleanup
        if hasattr(self, 'browser') and self.browser:
            try:
                self.browser.close()
            except:
                pass
        if hasattr(self, 'playwright') and self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
    
    def cleanup(self):
        """Clean up browser resources - called on window close"""
        self.cleanup_browser()

def exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler to catch all unhandled exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    print("=" * 80)
    print("UNHANDLED EXCEPTION CAUGHT:")
    print(f"Type: {exc_type.__name__}")
    print(f"Value: {exc_value}")
    print("\nFull traceback:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("=" * 80)
    sys.stderr.flush()

def main():
    # Set up global exception handler
    sys.excepthook = exception_handler
    
    root = tk.Tk()
    app = CoursePortalGUI(root)
    
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

"""Main GUI class for Course Portal application"""
import tkinter as tk
from tkinter import ttk
import threading
import traceback
import sys
import os
from models.app_state import AppState
from browser.browser_manager import BrowserManager
from utils.credential_manager import CredentialManager


class CoursePortalGUI:
    """Main GUI application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Course Portal - Missing Grades Checker")
        
        # Set favicon - get path relative to this file's location
        favicon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
        if os.path.exists(favicon_path):
            try:
                self.root.iconbitmap(favicon_path)
            except Exception as e:
                print(f"Warning: Could not load favicon: {e}")
        
        self.root.geometry("900x700")
        
        # Initialize components
        self.state = AppState()
        self.credential_manager = CredentialManager()
        self.browser_manager = BrowserManager(self.state, self.safe_after)
        
        # Hover state tracking for listboxes
        self.hovered_item = {}  # dict to track hovered item index for each listbox
        
        style = ttk.Style()
        style.theme_use('vista')
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
        
        # Set up hover effects for all listboxes
        self.setup_listbox_hover(self.courses_listbox)
        self.setup_listbox_hover(self.assignments_listbox)
        self.setup_listbox_hover(self.students_listbox)
        
        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=1)
        self.main_frame.rowconfigure(1, weight=1)  # Row 1 is for courses/assignments/students
    
    def setup_listbox_hover(self, listbox):
        """Set up hover effects for a listbox"""
        # Get the default background color from the listbox
        default_bg = listbox.cget("background")
        hover_bg = "#e0e0e0"  # Light gray for hover
        
        # Initialize hover state for this listbox
        listbox_id = id(listbox)
        self.hovered_item[listbox_id] = None
        
        def on_motion(event):
            """Handle mouse motion over the listbox"""
            # Get the item index under the cursor
            index = listbox.nearest(event.y)
            
            # Only process if we're actually over a valid item
            if 0 <= index < listbox.size():
                # Remove hover from previous item if different
                if self.hovered_item[listbox_id] is not None and self.hovered_item[listbox_id] != index:
                    listbox.itemconfig(self.hovered_item[listbox_id], bg=default_bg)
                
                # Apply hover to current item if not already hovered
                if self.hovered_item[listbox_id] != index:
                    listbox.itemconfig(index, bg=hover_bg)
                    self.hovered_item[listbox_id] = index
        
        def on_leave(event):
            """Handle mouse leaving the listbox"""
            # Remove hover from any hovered item
            if self.hovered_item[listbox_id] is not None:
                listbox.itemconfig(self.hovered_item[listbox_id], bg=default_bg)
                self.hovered_item[listbox_id] = None
        
        # Bind mouse motion and leave events
        listbox.bind('<Motion>', on_motion)
        listbox.bind('<Leave>', on_leave)
    
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
            self.state.is_loading = True
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
            if not self.state.is_loading:
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
            self.state.is_loading = False
        except (tk.TclError, RuntimeError):
            # Handle cases where root is destroyed
            pass
    
    def set_status(self, message, color="black"):
        """Set status bar message"""
        try:
            self.status_label.config(text=message, foreground=color)
        except (tk.TclError, RuntimeError):
            pass
    
    def load_saved_credentials(self):
        """Load saved credentials from system keyring and pre-fill form"""
        creds = self.credential_manager.load_saved_credentials()
        if creds:
            self.username_entry.insert(0, creds["username"])
            self.password_entry.insert(0, creds["password"])
            self.remember_me_var.set(True)
    
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
        
        # Queue login operation
        self.browser_manager.queue_login(
            username, password,
            self.on_login_success,
            self.on_login_error,
            self.update_login_status
        )
    
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
                self.credential_manager.save_credentials(self.current_username, password)
        else:
            # Clear saved credentials if "Remember me" is unchecked
            self.credential_manager.clear_saved_credentials()
        
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
        self.state.browser_ready = False
        
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
            if not self.state.browser_ready:
                return
            
            selection = self.courses_listbox.curselection()
            if not selection:
                return
            
            course_index = selection[0]
            
            # If clicking the same course, do nothing
            if course_index == self.state.current_course_index:
                return
            
            self.state.current_course_index = course_index
            selected_course = self.state.courses[course_index]
            
            # Clear assignments and students when switching courses
            self.assignments_listbox.delete(0, tk.END)
            self.students_listbox.delete(0, tk.END)
            self.state.current_assignment_index = None
            self.state.assignments = []
            self.state.students_missing = []
            
            # Show loading for assignments
            self.state.is_loading = True
            print("[DEBUG] Calling show_loading for assignments")
            self.show_loading("Fetching assignments...")
            
            # Queue fetch_assignments operation
            print("[DEBUG] Queueing fetch_assignments operation")
            self.browser_manager.queue_fetch_assignments(
                selected_course,
                self.on_assignments_fetched,
                self.on_assignments_error
            )
            print("[DEBUG] Operation queued")
        except Exception as e:
            print(f"ERROR in on_course_selected: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stderr.flush()
    
    def on_assignments_fetched(self, assignments):
        """Handle assignments fetched - update UI"""
        self.state.is_loading = False
        self.hide_loading()
        self.set_status(f"Found {len(assignments)} assignment(s)", "black")
        
        # Populate assignments list
        self.assignments_listbox.delete(0, tk.END)
        for assignment in assignments:
            self.assignments_listbox.insert(tk.END, assignment["name"])
    
    def on_assignments_error(self, error_message):
        """Handle error fetching assignments"""
        self.state.is_loading = False
        self.hide_loading()
        self.set_status(f"Error: {error_message}", "red")
    
    def on_assignment_selected(self, event):
        """Handle assignment selection"""
        if not self.state.browser_ready or not self.state.assignments:
            return
        
        selection = self.assignments_listbox.curselection()
        if not selection:
            return
        
        assignment_index = selection[0]
        
        # If clicking the same assignment, do nothing
        if assignment_index == self.state.current_assignment_index:
            return
        
        self.state.current_assignment_index = assignment_index
        selected_assignment = self.state.assignments[assignment_index]
        
        # Clear students list
        self.students_listbox.delete(0, tk.END)
        self.state.students_missing = []
        
        # Show loading for students
        self.state.is_loading = True
        self.show_loading("Processing assignment...")
        
        # Queue process_assignment operation
        self.browser_manager.queue_process_assignment(
            selected_assignment,
            self.on_students_processed,
            self.on_students_error
        )
    
    def on_students_processed(self, students_missing):
        """Handle students processed - update UI"""
        self.state.is_loading = False
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
        self.state.is_loading = False
        self.hide_loading()
        self.set_status(f"Error: {error_message}", "red")
    
    def on_signout_clicked(self):
        """Handle sign out button click"""
        # Reset browser manager (creates new queue and thread)
        self.browser_manager.reset()
        
        # Reset state
        self.state.reset()
        
        # Clear listboxes
        if hasattr(self, 'courses_listbox'):
            self.courses_listbox.delete(0, tk.END)
        if hasattr(self, 'assignments_listbox'):
            self.assignments_listbox.delete(0, tk.END)
        if hasattr(self, 'students_listbox'):
            self.students_listbox.delete(0, tk.END)
        
        # Hide main window and show login window
        if hasattr(self, 'main_frame'):
            self.main_frame.grid_forget()
        
        # Show login window
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
        
        # Force update
        self.root.update_idletasks()
        self.root.update()
        
        # Workaround for Windows repaint issue: minimize and restore to force repaint
        try:
            # Minimize the window
            self.root.state('iconic')
            self.root.update_idletasks()
            # Immediately restore it
            self.root.state('normal')
            self.root.update_idletasks()
            self.root.update()
        except Exception as e:
            # If state change doesn't work, continue anyway
            print(f"[DEBUG] Minimize/restore workaround failed: {e}")
    
    def cleanup(self):
        """Clean up browser resources - called on window close"""
        self.browser_manager.shutdown()

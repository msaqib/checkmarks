"""Portal scraping logic using Playwright"""
import time
import traceback


class PortalScraper:
    """Handles all scraping operations for the course portal"""
    
    LOGIN_URL = "https://lms.lums.edu.pk/"
    
    def __init__(self, page, state_manager, ui_callback):
        """
        Initialize scraper
        
        Args:
            page: Playwright page object
            state_manager: Object with browser_lock, courses, assignments, etc.
            ui_callback: Function to call for UI updates (safe_after wrapper)
        """
        self.page = page
        self.state_manager = state_manager
        self.ui_callback = ui_callback
    
    def login(self, username, password, status_callback):
        """
        Perform login and fetch courses
        
        Args:
            username: Login username
            password: Login password
            status_callback: Function to update login status messages
            
        Returns:
            tuple: (success: bool, courses: list, course_list_url: str, error_type: str)
        """
        try:
            print("[DEBUG] _do_login: Opening browser...")
            self.ui_callback(0, status_callback, "Connecting to server...")
            
            self.page.goto(self.LOGIN_URL, timeout=30000)

            print("[DEBUG] _do_login: Entering credentials...")
            self.ui_callback(0, status_callback, "Entering credentials...")
            
            self.page.fill('input[name="eid"]', username)
            self.page.fill('input[name="pw"]', password)
            self.page.click('input[type="submit"]')
            self.page.wait_for_load_state("networkidle")

            # Check if login was successful by verifying login form fields are gone
            eid_input = self.page.query_selector('input[name="eid"]')
            pw_input = self.page.query_selector('input[name="pw"]')
            
            if eid_input is not None or pw_input is not None:
                # Login fields still exist - login failed
                raise Exception("Login failed: Invalid credentials")

            print("[DEBUG] _do_login: Login successful! Fetching courses...")
            self.ui_callback(0, status_callback, "Fetching courses...")
            time.sleep(0.5)
            
            # Fetch courses
            course_elements = self.page.query_selector_all(".link-container")
            courses = []
            for element in course_elements:
                name = element.inner_text().strip()
                if name:
                    courses.append({"name": name, "index": len(courses)})
            
            # Store course list URL
            course_list_url = self.page.url
            
            # Update state
            with self.state_manager.browser_lock:
                self.state_manager.browser_ready = True
                self.state_manager.courses = courses
                self.state_manager.course_list_url = course_list_url
            
            return True, courses, course_list_url, None
            
        except Exception as e:
            print(f"ERROR in login: {type(e).__name__}: {e}")
            traceback.print_exc()
            
            # Determine error type
            error_msg = str(e).lower()
            if "timeout" in error_msg or "network" in error_msg or "navigation" in error_msg or "net::" in error_msg or "err_name_not_resolved" in error_msg:
                error_type = "connection"
            else:
                error_type = "credentials"
            
            return False, [], "", error_type
    
    def fetch_assignments(self, selected_course):
        """
        Fetch assignments for a selected course
        
        Args:
            selected_course: Dict with course info including "index"
            
        Returns:
            tuple: (success: bool, assignments: list, error_message: str)
        """
        try:
            print(f"[DEBUG] fetch_assignments started")
            
            # Navigate back to course list if we're not already there
            current_url = self.page.url
            with self.state_manager.browser_lock:
                course_list_url = self.state_manager.course_list_url
            
            if course_list_url not in current_url:
                self.page.goto(course_list_url)
            self.page.wait_for_load_state("networkidle")

            # Re-fetch course elements
            course_elements = self.page.query_selector_all(".link-container")
            course_index = selected_course["index"]
            
            if course_index < len(course_elements):
                course_elements[course_index].click()
                self.page.wait_for_load_state("networkidle")
            else:
                raise Exception(f"Course element at index {course_index} not found")
            
            # Click on Assignments section
            assignment_div = self.page.get_by_text("Assignments", exact=True)
            assignment_div.wait_for(state="visible")
            assignment_div.click()
            self.page.wait_for_load_state("networkidle")
                    
            # Fetch assignment elements
            row_elems = self.page.query_selector_all('td:has(> strong > a[name="asnActionLink"])')
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
            
            # Store assignments
            with self.state_manager.browser_lock:
                self.state_manager.assignments = assignments
            
            return True, assignments, None
            
        except Exception as e:
            print(f"ERROR in fetch_assignments: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False, [], str(e)
    
    def process_assignment(self, selected_assignment):
        """
        Process an assignment and find students with missing grades
        
        Args:
            selected_assignment: Dict with assignment info including "index"
            
        Returns:
            tuple: (success: bool, students_missing: list, error_message: str)
        """
        try:
            print(f"[DEBUG] process_assignment started")
            
            # Check if we're on a submission page (from a previous assignment)
            submission_table = self.page.query_selector("table#submissionList")
            if submission_table:
                # We're on a submission page, need to go back to assignments
                print("[DEBUG] On submission page, navigating back to assignments")
                btn_assgn = self.page.query_selector('li.firstToolBarItem span a')
                if btn_assgn:
                    btn_assgn.click()
                    self.page.wait_for_load_state("networkidle")
            
            # Ensure we're on the assignments page
            assignment_span = self.page.query_selector('span.Mrphs-toolTitleNav__text')
            is_on_assignments_page = assignment_span and "Assignments" in assignment_span.inner_text()
            
            if not is_on_assignments_page:
                # Not on assignments page, need to navigate back
                print("[DEBUG] Not on assignments page, navigating...")
                with self.state_manager.browser_lock:
                    current_course_index = self.state_manager.current_course_index
                    course_list_url = self.state_manager.course_list_url
                
                current_url = self.page.url
                if course_list_url not in current_url:
                    self.page.goto(course_list_url)
                    self.page.wait_for_load_state("networkidle")
                
                course_elements = self.page.query_selector_all(".link-container")
                if current_course_index is not None and current_course_index < len(course_elements):
                    course_elements[current_course_index].click()
                    self.page.wait_for_load_state("networkidle")
                
                assignment_div = self.page.get_by_text("Assignments", exact=True)
                assignment_div.wait_for(state="visible")
                assignment_div.click()
                self.page.wait_for_load_state("networkidle")

            # Re-fetch assignment grade elements (handles may be stale)
            row_elems = self.page.query_selector_all('td:has(> strong > a[name="asnActionLink"])')
            grades_elements = []
            for td in row_elems:
                grades = td.query_selector_all('xpath=.//*[normalize-space(text())="Grade"]')
                grades_elements.extend(grades)
            
            # Click on Grade button for the selected assignment
            assignment_index = selected_assignment["index"]
            if assignment_index < len(grades_elements):
                grades_elements[assignment_index].click()
                self.page.wait_for_load_state("networkidle")
            else:
                raise Exception(f"Grade element at index {assignment_index} not found")
            
            # Find students without marks
            table = self.page.query_selector("table#submissionList")
            rows = table.query_selector_all("tr") if table else []
        
            students_missing = []
            for row in rows:
                status_elem = row.query_selector('td[headers="status"]')
                student_elem = row.query_selector('td[headers="studentname"]')
                
                if status_elem and student_elem:
                    status = status_elem.inner_text().strip()
                    student_name = student_elem.inner_text().strip()
                    
                    # Logic: If status is not "Returned" and not "No Submission - Not Started"
                    if status and status != "Returned" and status != "No Submission - Not Started":
                        students_missing.append({"name": student_name, "status": status})
            
            return True, students_missing, None
            
        except Exception as e:
            print(f"ERROR in process_assignment: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False, [], str(e)

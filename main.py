from playwright.sync_api import sync_playwright
import argparse

def scrape_course_portal(username, password):
    with sync_playwright() as p:
        # 1. Launch Browser (headed mode so you can see what's happening)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Replace with your actual maintenance URL
        page.goto("https://lms.lums.edu.pk/")

        # --- AUTHENTICATION STEP (If needed) ---
        page.fill('input[name="eid"]', username)
        page.fill('input[name="pw"]', password)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")

        # 2. LIST COURSES
        print("\n--- Available Courses ---")
        # Change '.course-link' to the actual selector for course titles/links
        course_elements = page.query_selector_all(".link-container")
        
        courses = []
        for i, element in enumerate(course_elements):
            name = element.inner_text().strip()
            courses.append({"name": name, "element": element})
            print(f"[{i}] {name}")

        # USER INTERACTION: Selection
        selection = int(input("\nSelect course ID to inspect: "))
        selected_course = courses[selection]
        selected_course["element"].click()
        page.wait_for_load_state("networkidle")

        # 3. SHOW ASSIGNMENTS
        print(f"\n--- Assignments in {selected_course['name']} ---")
        assignment_div = page.get_by_text("Assignments", exact=True)
        assignment_div.wait_for(state="visible")
        assignment_div.click()
        page.wait_for_load_state("networkidle")
        # Change '.assignment-item' to your site's assignment selector
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
            assignments.append({"name": name, "element": element})
            print(f"[{i}] {name}")

        selection = int(input("\nSelect assignment ID to check marks: "))
        grades_elements[selection].click()
        page.wait_for_load_state("networkidle")

        # 4. FIND STUDENTS WITHOUT MARKS
        print("\n--- Students Missing Marks ---")
        # Update these selectors based on your gradebook table structure
        # Assumes a table row contains student name and a mark input/cell
        table = page.query_selector("table#submissionList")
        rows = table.query_selector_all("tr") if table else []
        
        missing_count = 0
        for row in rows:
            td_elements = row.query_selector_all("td")
            if len(td_elements) > 0:
                
                status = row.query_selector('td[headers="status"]').inner_text().strip()
                student_name = row.query_selector('td[headers="studentname"]').inner_text().strip()
                # mark_cell = row.query_selector(".mark-value").inner_text().strip()
                
                # Logic: If the cell is empty or contains a specific placeholder like "-"
                if status and status != "Returned" and status != "No Submission - Not Started":
                    print(f"⚠️ Missing: {student_name}")
                    missing_count += 1

        if missing_count == 0:
            print("All students have marks entered!")
        else:
            print(f"\nTotal students missing marks: {missing_count}")

        input("\nPress Enter to close the browser...")
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape course portal to check assignment grades and missing marks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -u saqibm -p mypassword
  python main.py --username saqibm --password mypassword
        """
    )
    parser.add_argument(
        '-u', '--username',
        type=str,
        required=True,
        help='Username (eid) for LMS login'
    )
    parser.add_argument(
        '-p', '--password',
        type=str,
        required=True,
        help='Password for LMS login'
    )
    
    args = parser.parse_args()
    scrape_course_portal(args.username, args.password)
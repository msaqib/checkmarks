"""Main entry point for Course Portal application"""
import tkinter as tk
import sys
import traceback
from gui.course_portal_gui import CoursePortalGUI


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

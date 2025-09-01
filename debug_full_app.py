#!/usr/bin/env python3
"""
Debug launcher for full app to find exact blocking point
"""

import sys
import os
import locale
import threading
import time
from pathlib import Path

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def debug_step(step_name):
    """Debug step with timing"""
    print(f"[{time.time():.2f}] {step_name}")

if __name__ == "__main__":
    try:
        debug_step("Starting debug session")
        
        # Suppress console logging to prevent encoding issues
        import logging
        logging.getLogger().handlers = []
        
        debug_step("Logging disabled")
        
        # Import step by step
        debug_step("Importing AppController...")
        from src.ui.components.app_controller import AppController
        
        debug_step("AppController imported successfully")
        
        # Create app in separate thread to monitor blocking
        app_created = threading.Event()
        app_instance = None
        error_occurred = threading.Event()
        
        def create_app():
            try:
                global app_instance
                debug_step("Creating AppController instance...")
                app_instance = AppController()
                debug_step("AppController created successfully")
                app_created.set()
                
                debug_step("Starting mainloop...")
                app_instance.main_window.root.mainloop()
                debug_step("Mainloop ended")
                
            except Exception as e:
                debug_step(f"ERROR in create_app: {e}")
                error_occurred.set()
        
        # Start app creation in thread
        app_thread = threading.Thread(target=create_app, daemon=True)
        app_thread.start()
        
        # Monitor progress
        debug_step("Waiting for app creation...")
        
        # Wait with timeout
        if app_created.wait(timeout=10):
            debug_step("App created successfully - running normally")
            app_thread.join()  # Wait for completion
        elif error_occurred.is_set():
            debug_step("ERROR occurred during app creation")
        else:
            debug_step("TIMEOUT: App creation taking too long - likely blocking")
            debug_step("App creation is blocking - this is the root cause")
            
        debug_step("Debug session ended")
            
    except Exception as e:
        debug_step(f"CRITICAL ERROR: {e}")
        import traceback
        with open("debug_error.txt", "w", encoding="utf-8") as f:
            f.write(f"Critical Error: {e}\n")
            traceback.print_exc(file=f)
        
        input("Press Enter to exit...")
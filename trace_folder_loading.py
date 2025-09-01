#!/usr/bin/env python3
"""
Trace folder loading flow để tìm exact blocking point
"""

import sys
import os
import time
import threading
from pathlib import Path

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def trace_point(message, start_time=None):
    current_time = time.time()
    if start_time:
        elapsed = current_time - start_time
        print(f"[{elapsed:.3f}s] {message}")
    else:
        print(f"[{current_time:.3f}] {message}")
    return current_time

def trace_folder_browse():
    """Simulate folder browse và trace blocking points"""
    start_time = trace_point("=== FOLDER LOADING TRACE START ===")
    
    try:
        # Step 1: Import components
        trace_point("Importing FolderSelectorComponent...", start_time)
        from src.ui.components.folder_selector import FolderSelectorComponent
        
        trace_point("Importing FilePreviewComponent...", start_time)  
        from src.ui.components.file_preview import FilePreviewComponent
        
        trace_point("Importing AppController...", start_time)
        from src.ui.components.app_controller import AppController
        
        trace_point("All imports successful", start_time)
        
        # Step 2: Create minimal GUI để test folder selection
        import tkinter as tk
        from tkinter import filedialog
        
        trace_point("Creating test GUI...", start_time)
        root = tk.Tk()
        root.title("Folder Loading Trace")
        root.geometry("400x300")
        
        status_label = tk.Label(root, text="Click Browse to test folder loading")
        status_label.pack(pady=20)
        
        def test_folder_selection():
            """Test actual folder selection process"""
            trace_point("=== FOLDER SELECTION START ===", start_time)
            
            # Step 3: Simulate filedialog.askdirectory() 
            trace_point("Opening folder dialog...", start_time)
            folder_path = filedialog.askdirectory(title="Select test folder")
            
            if not folder_path:
                trace_point("No folder selected", start_time)
                return
                
            trace_point(f"Folder selected: {len(folder_path)} chars", start_time)
            status_label.config(text=f"Testing folder: {os.path.basename(folder_path)}")
            
            # Step 4: Test actual folder processing 
            def process_folder_async():
                try:
                    trace_point("=== FOLDER PROCESSING START ===", start_time)
                    
                    # Test basic file listing
                    trace_point("Calling os.listdir()...", start_time)
                    items = os.listdir(folder_path)
                    trace_point(f"Found {len(items)} items", start_time)
                    
                    if len(items) > 100:
                        trace_point("Large directory - limiting to 100 items", start_time)
                        items = items[:100]
                    
                    # Test file processing
                    trace_point("Processing files...", start_time)
                    files_count = 0
                    for i, item in enumerate(items):
                        full_path = os.path.join(folder_path, item)
                        if os.path.isfile(full_path):
                            files_count += 1
                            
                        # Report progress every 20 items
                        if (i + 1) % 20 == 0:
                            trace_point(f"Processed {i+1}/{len(items)} items", start_time)
                    
                    trace_point(f"Found {files_count} files total", start_time)
                    
                    # Test Vietnamese normalization
                    trace_point("Testing Vietnamese normalization...", start_time)
                    from src.core.services.normalize_service import VietnameseNormalizer
                    normalizer = VietnameseNormalizer()
                    
                    test_files = [item for item in items[:5] if os.path.isfile(os.path.join(folder_path, item))]
                    for test_file in test_files:
                        try:
                            normalized = normalizer.normalize_filename(test_file)
                            trace_point(f"Normalized sample file OK", start_time)
                            break
                        except Exception as e:
                            trace_point(f"Normalization ERROR: {e}", start_time)
                    
                    trace_point("=== FOLDER PROCESSING COMPLETE ===", start_time)
                    
                    # Update UI
                    root.after(0, lambda: status_label.config(text=f"SUCCESS: {files_count} files processed"))
                    
                except Exception as e:
                    trace_point(f"PROCESSING ERROR: {e}", start_time)
                    root.after(0, lambda: status_label.config(text=f"ERROR: {str(e)[:50]}"))
            
            # Run processing in background thread
            trace_point("Starting background processing thread...", start_time)
            thread = threading.Thread(target=process_folder_async, daemon=True)
            thread.start()
        
        browse_button = tk.Button(root, text="Browse & Test Folder", command=test_folder_selection)
        browse_button.pack(pady=10)
        
        quit_button = tk.Button(root, text="Quit", command=root.quit)
        quit_button.pack(pady=5)
        
        trace_point("Test GUI created, starting mainloop...", start_time)
        root.mainloop()
        
        trace_point("=== TRACE SESSION COMPLETE ===", start_time)
        
    except Exception as e:
        trace_point(f"CRITICAL ERROR: {e}", start_time)
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    trace_folder_browse()
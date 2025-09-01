#!/usr/bin/env python3
"""
Test drag-drop functionality independently
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os

def test_tkinterdnd2():
    """Test tkinterdnd2 implementation"""
    print("Testing tkinterdnd2...")
    try:
        import tkinterdnd2
        from tkinterdnd2 import DND_FILES, TkinterDnD
        
        root = TkinterDnD.Tk()
        root.title("Drag-Drop Test - tkinterdnd2")
        root.geometry("400x200")
        
        def on_drop(event):
            files = root.tk.splitlist(event.data)
            if files:
                folder_path = files[0]
                if os.path.isdir(folder_path):
                    messagebox.showinfo("Success", f"Dropped folder: {folder_path}")
                else:
                    messagebox.showwarning("Warning", "Please drop a folder, not a file")
        
        def on_drag_enter(event):
            label.config(bg='lightblue', text='Drop folder here!')
        
        def on_drag_leave(event):
            label.config(bg='lightgray', text='Drag a folder here')
        
        label = tk.Label(root, text='Drag a folder here', bg='lightgray', width=50, height=10)
        label.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Register drop target
        label.drop_target_register(DND_FILES)
        label.dnd_bind('<<Drop>>', on_drop)
        label.dnd_bind('<<DragEnter>>', on_drag_enter)
        label.dnd_bind('<<DragLeave>>', on_drag_leave)
        
        print("tkinterdnd2 setup successful")
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"tkinterdnd2 failed: {e}")
        return False

def test_windnd():
    """Test windnd implementation"""
    print("Testing windnd...")
    try:
        import windnd
        
        root = tk.Tk()
        root.title("Drag-Drop Test - windnd")
        root.geometry("400x200")
        
        def on_drop(files):
            if files:
                folder_path = files[0]
                if os.path.isdir(folder_path):
                    messagebox.showinfo("Success", f"Dropped folder: {folder_path}")
                else:
                    messagebox.showwarning("Warning", "Please drop a folder, not a file")
        
        label = tk.Label(root, text='Drag a folder here (windnd)', bg='lightgreen', width=50, height=10)
        label.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Hook drop files
        windnd.hook_dropfiles(root, func=on_drop)
        
        print("windnd setup successful")
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"windnd failed: {e}")
        return False

if __name__ == "__main__":
    print("Choose drag-drop test:")
    print("1. tkinterdnd2")
    print("2. windnd")
    
    choice = input("Enter choice (1 or 2): ")
    
    if choice == "1":
        test_tkinterdnd2()
    elif choice == "2":
        test_windnd()
    else:
        print("Invalid choice")
"""
Help Documentation System for File Rename Tool

Comprehensive help system with user guides, keyboard shortcuts,
context-sensitive help, and troubleshooting resources.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, Callable
from pathlib import Path


class HelpContent:
    """Help content data and management"""
    
    @staticmethod
    def get_user_guide() -> str:
        """Get comprehensive user guide content"""
        return """# File Rename Tool - User Guide

## Getting Started

### 1. Select a Folder
- Click "Browse" or drag-and-drop a folder onto the application
- The folder contents will be loaded and displayed in the preview area
- Large folders are loaded progressively for better performance

### 2. Preview Changes
- File rename previews are generated automatically
- Vietnamese text is normalized (diacritics removed)
- Special characters are cleaned up
- Preview shows original → processed filename

### 3. Customize Settings
- Access Settings through the menu or Ctrl+, 
- Configure normalization rules
- Adjust performance settings
- Set UI preferences

### 4. Execute Rename Operation
- Review all changes in the preview
- Use checkboxes to select/deselect files
- Click "Rename Files" to execute
- Operations can be undone if needed

## Vietnamese Text Processing

### Diacritic Removal
- Converts: á, à, ả, ã, ạ → a
- Converts: é, è, ẻ, ẽ, ệ → e
- Converts: í, ì, ỉ, ĩ, ị → i
- And all other Vietnamese diacritics

### Special Character Handling
- Removes or replaces special characters
- Handles spaces and punctuation
- Maintains file extensions
- Preserves folder structure

## Advanced Features

### Batch Operations
- Process hundreds or thousands of files
- Progress tracking with cancellation support
- Memory-efficient processing
- Error handling and recovery

### Undo Support
- Full undo capability for rename operations
- Maintains operation history
- Safe operation with backup options

### Performance Optimization
- Progressive loading for large directories
- Background processing maintains UI responsiveness
- Memory management for sustained operations
- Adaptive performance based on system capabilities

## Tips and Best Practices

1. **Always Preview First**: Review all changes before executing
2. **Use Undo**: Keep undo capability available for safety
3. **Backup Important Files**: Consider backing up before major operations
4. **Check Results**: Verify renamed files meet your expectations
5. **Report Issues**: Use Help → System Info for troubleshooting

For more detailed help, press F1 in any dialog or screen for context-specific assistance."""

    @staticmethod
    def get_keyboard_shortcuts() -> str:
        """Get keyboard shortcuts reference"""
        return """# Keyboard Shortcuts

## Main Window
- **Ctrl+O**: Open/Browse for folder
- **Ctrl+R**: Refresh current folder
- **Ctrl+,**: Open Settings
- **Ctrl+Z**: Undo last operation
- **Ctrl+A**: Select all files
- **Ctrl+D**: Deselect all files
- **Enter**: Execute rename operation
- **Escape**: Cancel current operation
- **F1**: Show help
- **F5**: Refresh folder contents

## File List
- **Space**: Toggle file selection
- **Ctrl+Click**: Toggle individual file selection
- **Shift+Click**: Select range of files
- **Arrow Keys**: Navigate file list
- **Home/End**: Go to first/last file

## Dialogs
- **Enter**: Accept/OK
- **Escape**: Cancel/Close
- **Tab**: Navigate between controls
- **Alt+Letter**: Access menu items

## Advanced
- **Ctrl+Shift+R**: Force refresh with cache clear
- **Ctrl+I**: Show system information
- **Ctrl+L**: Show operation log
- **F11**: Toggle fullscreen (if supported)

## Quick Actions
- **Double-click folder**: Select folder and load contents
- **Right-click file**: Context menu (future feature)
- **Drag-drop folder**: Select and load folder
- **Middle-click**: Open file location (future feature)

Press F1 in any dialog for context-specific shortcuts."""

    @staticmethod
    def get_troubleshooting() -> str:
        """Get troubleshooting guide"""
        return """# Troubleshooting Guide

## Common Issues

### Application Won't Start
- **Check Requirements**: Ensure Windows 7+ with proper permissions
- **Antivirus Software**: Add application to exclusion list
- **Missing Dependencies**: Reinstall application
- **Corrupted Installation**: Uninstall and reinstall

### Folder Loading Issues
- **Permission Denied**: Run as Administrator or check folder permissions
- **Network Drives**: Copy files locally for better performance
- **Very Large Folders**: Use progressive loading (automatic)
- **Special Characters**: Some paths may need ASCII names

### Preview Generation Problems
- **Slow Performance**: Adjust performance settings in Settings
- **Memory Issues**: Close other applications, restart if needed
- **Missing Previews**: Check file permissions and formats
- **Wrong Normalization**: Review and adjust normalization rules

### Rename Operation Failures
- **Files in Use**: Close applications using the files
- **Read-Only Files**: Change file attributes or run as Administrator
- **Path Too Long**: Use shorter folder structure
- **Disk Full**: Free up disk space

### Performance Issues
- **High Memory Usage**: Restart application, process smaller batches
- **Slow Response**: Check system resources, close other applications
- **UI Freezing**: Cancel operation and restart if needed
- **Long Processing**: Normal for very large folders

## Error Recovery

### If Application Crashes
1. Restart the application
2. Check for unsaved changes
3. Review operation log if available
4. Report persistent issues

### If Rename Operation Fails
1. Use Undo if available
2. Check file system integrity
3. Verify file permissions
4. Process files in smaller batches

### Data Recovery
1. Check Recycle Bin for accidentally deleted files
2. Use Windows File History if enabled
3. Restore from backup if available
4. Use file recovery tools if necessary

## Getting Help

### System Information
Use Help → System Info to gather:
- Application version and build info
- System specifications
- Memory and resource usage
- Error logs and diagnostics

### Reporting Issues
When reporting problems, include:
- Steps to reproduce the issue
- System information
- Error messages (exact text)
- File types and folder structure involved

### Performance Optimization
- Close unnecessary applications
- Ensure adequate free disk space
- Process files in smaller batches for very large operations
- Use SSD storage for better performance
- Ensure stable internet connection for network drives

Contact support with system information for persistent issues."""

    @staticmethod
    def get_vietnamese_guide() -> str:
        """Get Vietnamese normalization guide"""
        return """# Vietnamese Text Normalization Guide

## Overview
This tool specializes in normalizing Vietnamese text by removing diacritical marks
and converting text to ASCII-compatible format suitable for file systems.

## Vietnamese Diacritics

### Vowel Transformations
- **A family**: á, à, ả, ã, ạ, ă, ắ, ằ, ẳ, ẵ, ặ, â, ấ, ầ, ẩ, ẫ, ậ → a
- **E family**: é, è, ẻ, ẽ, ẹ, ê, ế, ề, ể, ễ, ệ → e  
- **I family**: í, ì, ỉ, ĩ, ị → i
- **O family**: ó, ò, ỏ, õ, ọ, ô, ố, ồ, ổ, ỗ, ộ, ơ, ớ, ờ, ở, ỡ, ợ → o
- **U family**: ú, ù, ủ, ũ, ụ, ư, ứ, ừ, ử, ữ, ự → u
- **Y family**: ý, ỳ, ỷ, ỹ, ỵ → y

### Special Characters
- **Đ, đ** → D, d (Vietnamese D with stroke)

## Normalization Rules

### Default Settings
- Remove all Vietnamese diacritics
- Convert to lowercase (optional)
- Replace spaces with underscores or hyphens
- Remove special punctuation
- Preserve file extensions

### Customizable Options
- Case handling (preserve, lowercase, title case)
- Space replacement character
- Special character handling
- Extension preservation
- Custom character mappings

## Examples

### Common Transformations
- `Tài liệu quan trọng.docx` → `tai lieu quan trong.docx`
- `Báo cáo tháng 12.pdf` → `bao cao thang 12.pdf`
- `Hình ảnh đẹp.jpg` → `hinh anh dep.jpg`
- `Văn bản pháp lý.txt` → `van ban phap ly.txt`

### Before and After
| Original | Normalized |
|----------|------------|
| `Công việc hàng ngày` | `cong viec hang ngay` |
| `Thông báo khẩn cấp` | `thong bao khan cap` |
| `Tệp âm thanh.mp3` | `tep am thanh.mp3` |
| `Dữ liệu quan trọng` | `du lieu quan trong` |

## Best Practices

### File Organization
- Use consistent naming conventions
- Group related files in folders
- Include dates in standardized format
- Avoid overly long filenames

### Character Encoding
- Ensures compatibility with older systems
- Prevents issues with network file sharing
- Improves search and indexing
- Reduces encoding-related errors

### Quality Control
- Always preview changes before applying
- Verify important files after normalization
- Keep backups of original filenames if needed
- Test with small batches first

## Advanced Features

### Custom Rules
- Add specific character replacements
- Define word-based transformations
- Set up abbreviation expansions
- Create domain-specific rules

### Batch Processing
- Process entire folder hierarchies
- Maintain folder structure
- Handle duplicate names intelligently
- Support for various file types

This comprehensive Vietnamese normalization ensures your files have clean,
system-friendly names while preserving their meaning and organization."""


class HelpDialog:
    """Main help dialog with tabbed interface"""
    
    def __init__(self, parent: tk.Widget, initial_tab: str = "guide"):
        self.parent = parent
        self.window: Optional[tk.Toplevel] = None
        self.initial_tab = initial_tab
        self.notebook: Optional[ttk.Notebook] = None
        
        self.setup_dialog()
    
    def setup_dialog(self):
        """Create and configure the help dialog"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("File Rename Tool - Help")
        self.window.geometry("800x600")
        
        # Center on parent and set as modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Configure window
        self.window.minsize(600, 400)
        
        self._create_content()
        self._center_window()
        
        # Keyboard bindings
        self.window.bind('<Escape>', lambda e: self.close_dialog())
        self.window.bind('<F1>', lambda e: None)  # Prevent recursive F1
        self.window.focus_set()
    
    def _create_content(self):
        """Create tabbed help content"""
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 10))
        
        # Add help tabs
        self._add_user_guide_tab()
        self._add_shortcuts_tab()
        self._add_vietnamese_tab()
        self._add_troubleshooting_tab()
        
        # Select initial tab
        self._select_initial_tab()
        
        # Bottom buttons
        self._create_buttons(main_frame)
    
    def _add_user_guide_tab(self):
        """Add user guide tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="User Guide")
        
        # Create scrollable text widget
        text_widget, scrollbar = self._create_text_widget(tab_frame)
        text_widget.insert('1.0', HelpContent.get_user_guide())
        text_widget.configure(state='disabled')
    
    def _add_shortcuts_tab(self):
        """Add keyboard shortcuts tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Shortcuts")
        
        text_widget, scrollbar = self._create_text_widget(tab_frame)
        text_widget.insert('1.0', HelpContent.get_keyboard_shortcuts())
        text_widget.configure(state='disabled')
    
    def _add_vietnamese_tab(self):
        """Add Vietnamese normalization guide tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Vietnamese Guide")
        
        text_widget, scrollbar = self._create_text_widget(tab_frame)
        text_widget.insert('1.0', HelpContent.get_vietnamese_guide())
        text_widget.configure(state='disabled')
    
    def _add_troubleshooting_tab(self):
        """Add troubleshooting tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Troubleshooting")
        
        text_widget, scrollbar = self._create_text_widget(tab_frame)
        text_widget.insert('1.0', HelpContent.get_troubleshooting())
        text_widget.configure(state='disabled')
    
    def _create_text_widget(self, parent):
        """Create scrollable text widget"""
        # Frame for text and scrollbar
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Text widget
        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            padx=10,
            pady=10,
            bg='white',
            fg='black',
            selectbackground='#0078d4',
            selectforeground='white'
        )
        text_widget.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        
        return text_widget, scrollbar
    
    def _select_initial_tab(self):
        """Select the initial tab based on parameter"""
        if not self.notebook:
            return
            
        tab_mapping = {
            "guide": 0,
            "shortcuts": 1,
            "vietnamese": 2,
            "troubleshooting": 3
        }
        
        tab_index = tab_mapping.get(self.initial_tab, 0)
        self.notebook.select(tab_index)
    
    def _create_buttons(self, parent):
        """Create bottom button section"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x')
        
        # System info button
        system_info_btn = ttk.Button(
            button_frame,
            text="System Info",
            command=self._show_system_info
        )
        system_info_btn.pack(side='left')
        
        # Print/Save button
        save_btn = ttk.Button(
            button_frame,
            text="Save Help",
            command=self._save_help
        )
        save_btn.pack(side='left', padx=(10, 0))
        
        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=self.close_dialog,
            width=12
        )
        close_btn.pack(side='right')
        close_btn.focus_set()
    
    def _center_window(self):
        """Center dialog on parent"""
        self.window.update_idletasks()
        
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = self.window.winfo_width()
        dialog_height = self.window.winfo_height()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Keep on screen
        x = max(0, min(x, self.window.winfo_screenwidth() - dialog_width))
        y = max(0, min(y, self.window.winfo_screenheight() - dialog_height))
        
        self.window.geometry(f"+{x}+{y}")
    
    def _show_system_info(self):
        """Show system information dialog"""
        try:
            from ..dialogs.about_dialog import show_about_dialog
            about_dialog = show_about_dialog(self.window)
            # Trigger system info directly
            about_dialog._show_system_info()
        except ImportError:
            messagebox.showinfo(
                "System Info",
                "System information is available through Help → About → System Info",
                parent=self.window
            )
    
    def _save_help(self):
        """Save help content to file"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                parent=self.window,
                title="Save Help Documentation",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Markdown files", "*.md"),
                    ("All files", "*.*")
                ]
            )
            
            if filename:
                content = []
                content.append("File Rename Tool - Complete Help Documentation")
                content.append("=" * 50)
                content.append("")
                content.append(HelpContent.get_user_guide())
                content.append("\n" + "=" * 50 + "\n")
                content.append(HelpContent.get_keyboard_shortcuts())
                content.append("\n" + "=" * 50 + "\n")
                content.append(HelpContent.get_vietnamese_guide())
                content.append("\n" + "=" * 50 + "\n")
                content.append(HelpContent.get_troubleshooting())
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("\n".join(content))
                
                messagebox.showinfo(
                    "Success",
                    f"Help documentation saved to:\n{filename}",
                    parent=self.window
                )
                
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save help documentation:\n{e}",
                parent=self.window
            )
    
    def close_dialog(self):
        """Close help dialog"""
        if self.window:
            self.window.destroy()
            self.window = None


class HelpSystem:
    """Integrated help system for the application"""
    
    def __init__(self, main_window: tk.Widget):
        self.main_window = main_window
        self._setup_help_bindings()
    
    def _setup_help_bindings(self):
        """Setup F1 key binding and Help menu"""
        self.main_window.bind('<F1>', self.show_help_dialog)
        
        # Add Help menu to main menu bar if available
        try:
            if hasattr(self.main_window, 'menubar'):
                self._add_help_menu()
        except Exception:
            pass
    
    def _add_help_menu(self):
        """Add Help menu to main menu bar"""
        help_menu = tk.Menu(self.main_window.menubar, tearoff=0)
        
        help_menu.add_command(label="User Guide", command=lambda: self.show_help_dialog(tab="guide"))
        help_menu.add_command(label="Keyboard Shortcuts", command=lambda: self.show_help_dialog(tab="shortcuts"))
        help_menu.add_command(label="Vietnamese Guide", command=lambda: self.show_help_dialog(tab="vietnamese"))
        help_menu.add_separator()
        help_menu.add_command(label="Troubleshooting", command=lambda: self.show_help_dialog(tab="troubleshooting"))
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about_dialog)
        
        self.main_window.menubar.add_cascade(label="Help", menu=help_menu)
    
    def show_help_dialog(self, event=None, tab: str = "guide"):
        """Show help dialog with specified tab"""
        HelpDialog(self.main_window, initial_tab=tab)
    
    def show_about_dialog(self):
        """Show About dialog"""
        try:
            from ..dialogs.about_dialog import show_about_dialog
            show_about_dialog(self.main_window)
        except ImportError:
            messagebox.showinfo("About", "About dialog not available")
    
    def show_context_help(self, context: str):
        """Show context-sensitive help"""
        if context == "normalization":
            self.show_help_dialog(tab="vietnamese")
        elif context == "shortcuts":
            self.show_help_dialog(tab="shortcuts")
        elif context == "troubleshooting":
            self.show_help_dialog(tab="troubleshooting")
        else:
            self.show_help_dialog(tab="guide")


# Convenience functions
def show_help_dialog(parent: tk.Widget, tab: str = "guide"):
    """Show help dialog"""
    return HelpDialog(parent, initial_tab=tab)

def create_help_system(main_window: tk.Widget) -> HelpSystem:
    """Create and return help system for main window"""
    return HelpSystem(main_window)


if __name__ == "__main__":
    # Test the help system
    root = tk.Tk()
    root.title("File Rename Tool")
    root.geometry("400x300")
    
    # Create menu bar
    root.menubar = tk.Menu(root)
    root.config(menu=root.menubar)
    
    # Create help system
    help_system = HelpSystem(root)
    
    # Test button
    button = ttk.Button(root, text="Show Help (F1)", command=lambda: help_system.show_help_dialog())
    button.pack(expand=True)
    
    root.mainloop()
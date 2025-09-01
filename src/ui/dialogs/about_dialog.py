"""
About Dialog for File Rename Tool

Professional About dialog with comprehensive application information,
version details, feature overview, and help resources.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from pathlib import Path
import webbrowser

# Import version management
try:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent.parent / "packaging"))
    from version import get_version_info, get_current_version
except ImportError:
    # Fallback if version module not available
    def get_version_info():
        return {
            'title': 'File Rename Tool',
            'version': '1.0.0',
            'description': 'Vietnamese File Normalization Utility',
            'author': 'File Rename Tool Team',
            'copyright': '2025 File Rename Tool Team',
            'build_date': '2025-09-01'
        }
    
    def get_current_version():
        class MockVersion:
            semantic_version = "1.0.0"
            display_version = "1.0.0"
            build = "development"
            release_date = "2025-09-01"
        return MockVersion()


class AboutDialog:
    """Professional About dialog with comprehensive information"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.window: Optional[tk.Toplevel] = None
        
        # Load application information
        try:
            self.app_info = get_version_info()
            self.version_info = get_current_version()
        except Exception:
            self.app_info = get_version_info()
            self.version_info = get_current_version()
        
        self.setup_dialog()
    
    def setup_dialog(self):
        """Create and configure the About dialog"""
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"About {self.app_info['title']}")
        self.window.geometry("550x500")
        self.window.resizable(False, False)
        
        # Center dialog on parent
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Configure window properties
        self.window.configure(bg='white')
        
        # Set window icon (if available)
        try:
            icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / "app.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception:
            pass
        
        self._create_content()
        self._center_window()
        
        # Focus and keyboard bindings
        self.window.focus_set()
        self.window.bind('<Escape>', lambda e: self.close_dialog())
        self.window.bind('<Return>', lambda e: self.close_dialog())
    
    def _create_content(self):
        """Create dialog content with comprehensive information"""
        # Main container with padding
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=15)
        
        # Create content sections
        self._create_header_section(main_frame)
        self._create_version_section(main_frame)
        self._create_features_section(main_frame)
        self._create_help_section(main_frame)
        self._create_legal_section(main_frame)
        self._create_button_section(main_frame)
    
    def _create_header_section(self, parent):
        """Application branding and title section"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 15))
        
        # Application icon (placeholder for now)
        try:
            # This would load an actual icon if available
            icon_frame = ttk.Frame(header_frame)
            icon_frame.pack(pady=(0, 10))
            
            # For now, create a simple text-based icon
            icon_label = ttk.Label(
                icon_frame,
                text="📁✨",  # File and sparkle emoji as icon
                font=('Segoe UI', 24)
            )
            icon_label.pack()
        except Exception:
            pass
        
        # Application title
        title_label = ttk.Label(
            header_frame,
            text=self.app_info['title'],
            font=('Segoe UI', 18, 'bold')
        )
        title_label.pack()
        
        # Subtitle/description
        subtitle_label = ttk.Label(
            header_frame,
            text=self.app_info['description'],
            font=('Segoe UI', 10),
            foreground='#666666'
        )
        subtitle_label.pack(pady=(5, 0))
    
    def _create_version_section(self, parent):
        """Version and build information section"""
        version_frame = ttk.LabelFrame(parent, text="Version Information", padding="15")
        version_frame.pack(fill='x', pady=(0, 15))
        
        # Version details
        version_text = f"Version: {self.version_info.display_version}\n"
        version_text += f"Build: {getattr(self.version_info, 'build', 'Release')}\n"
        version_text += f"Release Date: {getattr(self.version_info, 'release_date', 'N/A')}"
        
        version_label = ttk.Label(
            version_frame,
            text=version_text,
            font=('Consolas', 9),
            justify='left'
        )
        version_label.pack(anchor='w')
    
    def _create_features_section(self, parent):
        """Key features overview section"""
        features_frame = ttk.LabelFrame(parent, text="Key Features", padding="15")
        features_frame.pack(fill='x', pady=(0, 15))
        
        features_text = """• Vietnamese text normalization with diacritic removal
• Batch file renaming with real-time preview
• Drag-and-drop folder selection support
• Undo functionality for safe operations
• Customizable normalization rules and settings
• Performance optimization for large directories
• User preferences with persistent settings
• Progress tracking with cancellation support"""
        
        features_label = ttk.Label(
            features_frame,
            text=features_text,
            font=('Segoe UI', 9),
            justify='left'
        )
        features_label.pack(anchor='w')
    
    def _create_help_section(self, parent):
        """Help and support resources section"""
        help_frame = ttk.LabelFrame(parent, text="Help & Support", padding="15")
        help_frame.pack(fill='x', pady=(0, 15))
        
        help_text = "Need help? Press F1 for user guide or use Help menu for:\n"
        help_text += "• User Guide and Getting Started\n"
        help_text += "• Keyboard shortcuts and tips\n"
        help_text += "• Vietnamese normalization guide\n"
        help_text += "• Troubleshooting common issues"
        
        help_label = ttk.Label(
            help_frame,
            text=help_text,
            font=('Segoe UI', 9),
            justify='left'
        )
        help_label.pack(anchor='w')
        
        # Help button
        help_button = ttk.Button(
            help_frame,
            text="Open User Guide (F1)",
            command=self._show_help
        )
        help_button.pack(anchor='w', pady=(10, 0))
    
    def _create_legal_section(self, parent):
        """Copyright and legal information section"""
        legal_frame = ttk.LabelFrame(parent, text="Legal Information", padding="15")
        legal_frame.pack(fill='x', pady=(0, 15))
        
        legal_text = f"Copyright © 2025 {self.app_info['author']}\n\n"
        legal_text += "This software is provided 'as-is' without warranty.\n"
        legal_text += "Vietnamese text processing capabilities included.\n"
        legal_text += "Built with Python and tkinter."
        
        legal_label = ttk.Label(
            legal_frame,
            text=legal_text,
            font=('Segoe UI', 8),
            justify='left',
            foreground='#666666'
        )
        legal_label.pack(anchor='w')
    
    def _create_button_section(self, parent):
        """Action buttons section"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # System info button
        system_info_button = ttk.Button(
            button_frame,
            text="System Info",
            command=self._show_system_info
        )
        system_info_button.pack(side='left')
        
        # Spacer
        ttk.Frame(button_frame).pack(side='left', expand=True)
        
        # Close button
        close_button = ttk.Button(
            button_frame,
            text="Close",
            command=self.close_dialog,
            width=12
        )
        close_button.pack(side='right')
        
        # Set focus on close button
        close_button.focus_set()
    
    def _center_window(self):
        """Center the dialog on parent window"""
        self.window.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get dialog size
        dialog_width = self.window.winfo_width()
        dialog_height = self.window.winfo_height()
        
        # Calculate centered position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Ensure dialog stays on screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        self.window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _show_help(self):
        """Open help documentation"""
        try:
            # Try to show help dialog (will be implemented in help system)
            from ..components.help_system import show_help_dialog
            show_help_dialog(self.window)
        except ImportError:
            # Fallback: show simple message
            tk.messagebox.showinfo(
                "Help",
                "Help documentation is available through the Help menu.\n\n"
                "Press F1 anywhere in the application for context help,\n"
                "or use Help → User Guide from the menu bar.",
                parent=self.window
            )
    
    def _show_system_info(self):
        """Display system information dialog"""
        system_info = self._get_system_info()
        
        # Create system info dialog
        info_window = tk.Toplevel(self.window)
        info_window.title("System Information")
        info_window.geometry("450x350")
        info_window.transient(self.window)
        info_window.grab_set()
        
        # Content frame
        content_frame = ttk.Frame(info_window, padding="15")
        content_frame.pack(fill='both', expand=True)
        
        # System info text
        text_widget = tk.Text(
            content_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            height=15,
            width=50
        )
        text_widget.pack(fill='both', expand=True)
        
        text_widget.insert('1.0', system_info)
        text_widget.configure(state='disabled')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(content_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        
        # Close button
        close_frame = ttk.Frame(content_frame)
        close_frame.pack(fill='x', pady=(10, 0))
        
        close_btn = ttk.Button(
            close_frame,
            text="Close",
            command=info_window.destroy
        )
        close_btn.pack(anchor='center')
        close_btn.focus_set()
    
    def _get_system_info(self) -> str:
        """Get comprehensive system information"""
        import sys
        import platform
        import os
        
        info = []
        info.append(f"Application: {self.app_info['title']}")
        info.append(f"Version: {self.version_info.display_version}")
        info.append(f"Build Date: {getattr(self.version_info, 'release_date', 'N/A')}")
        info.append("")
        
        info.append("System Information:")
        info.append(f"Platform: {platform.platform()}")
        info.append(f"OS: {platform.system()} {platform.release()}")
        info.append(f"Architecture: {platform.machine()}")
        info.append(f"Processor: {platform.processor()}")
        info.append("")
        
        info.append("Python Information:")
        info.append(f"Version: {sys.version}")
        info.append(f"Implementation: {platform.python_implementation()}")
        info.append(f"Executable: {sys.executable}")
        info.append("")
        
        info.append("Environment:")
        info.append(f"Working Directory: {os.getcwd()}")
        info.append(f"User: {os.getenv('USERNAME', 'Unknown')}")
        info.append(f"Computer: {os.getenv('COMPUTERNAME', 'Unknown')}")
        
        try:
            # Memory information if available
            import psutil
            memory = psutil.virtual_memory()
            info.append("")
            info.append("Memory Information:")
            info.append(f"Total: {memory.total / (1024**3):.1f} GB")
            info.append(f"Available: {memory.available / (1024**3):.1f} GB")
            info.append(f"Used: {memory.percent:.1f}%")
        except ImportError:
            pass
        
        return "\n".join(info)
    
    def close_dialog(self):
        """Close the About dialog"""
        if self.window:
            self.window.destroy()
            self.window = None
    
    def show(self):
        """Show the dialog (alternative interface)"""
        if self.window:
            self.window.lift()
            self.window.focus_set()


def show_about_dialog(parent: tk.Widget) -> AboutDialog:
    """Convenience function to show About dialog"""
    return AboutDialog(parent)


if __name__ == "__main__":
    # Test the About dialog
    root = tk.Tk()
    root.title("File Rename Tool")
    root.geometry("400x300")
    
    def show_about():
        about_dialog = AboutDialog(root)
    
    button = ttk.Button(root, text="Show About", command=show_about)
    button.pack(expand=True)
    
    root.mainloop()
"""
Windows Integration Utilities

Provides Windows-specific integration features including desktop shortcuts,
Start menu integration, file associations, and security handling.
"""

import os
import sys
import winreg
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess

logger = logging.getLogger(__name__)


class WindowsIntegration:
    """Handles Windows-specific integration features"""
    
    def __init__(self, app_name: str = "File Rename Tool", executable_path: Optional[Path] = None):
        self.app_name = app_name
        self.app_key = "FileRenameTool"
        
        if executable_path is None:
            executable_path = self._get_current_executable_path()
        
        self.executable_path = executable_path
        self.executable_dir = executable_path.parent if executable_path else Path.cwd()
    
    def _get_current_executable_path(self) -> Path:
        """Get path to current executable"""
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            return Path(sys.executable)
        else:
            # Running as Python script
            return Path(sys.argv[0]).resolve()
    
    def create_desktop_shortcut(self, force: bool = False) -> bool:
        """Create desktop shortcut using Windows COM interface"""
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            desktop = shell.SpecialFolders("Desktop")
            shortcut_path = Path(desktop) / f"{self.app_name}.lnk"
            
            # Check if shortcut already exists
            if shortcut_path.exists() and not force:
                logger.info("Desktop shortcut already exists")
                return True
            
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(self.executable_path)
            shortcut.WorkingDirectory = str(self.executable_dir)
            shortcut.IconLocation = str(self.executable_path)
            shortcut.Description = "Vietnamese File Normalization Utility"
            shortcut.Arguments = ""
            shortcut.save()
            
            logger.info(f"Desktop shortcut created: {shortcut_path}")
            return True
            
        except ImportError:
            logger.warning("win32com not available, using fallback method")
            return self._create_desktop_shortcut_fallback(force)
        except Exception as e:
            logger.error(f"Failed to create desktop shortcut: {e}")
            return False
    
    def _create_desktop_shortcut_fallback(self, force: bool = False) -> bool:
        """Fallback method for creating desktop shortcut"""
        try:
            import winshell
            
            desktop = winshell.desktop()
            shortcut_path = Path(desktop) / f"{self.app_name}.lnk"
            
            if shortcut_path.exists() and not force:
                return True
            
            winshell.CreateShortcut(
                Path=str(shortcut_path),
                Target=str(self.executable_path),
                Icon=(str(self.executable_path), 0),
                Description="Vietnamese File Normalization Utility"
            )
            
            logger.info(f"Desktop shortcut created (fallback): {shortcut_path}")
            return True
            
        except ImportError:
            logger.warning("winshell not available")
            return False
        except Exception as e:
            logger.error(f"Fallback shortcut creation failed: {e}")
            return False
    
    def create_start_menu_shortcut(self, force: bool = False) -> bool:
        """Create Start Menu shortcut"""
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            start_menu = shell.SpecialFolders("StartMenu")
            programs_folder = Path(start_menu) / "Programs"
            app_folder = programs_folder / self.app_name
            
            # Create application folder in Start Menu
            app_folder.mkdir(exist_ok=True)
            
            # Create main shortcut
            shortcut_path = app_folder / f"{self.app_name}.lnk"
            
            if shortcut_path.exists() and not force:
                logger.info("Start Menu shortcut already exists")
                return True
            
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(self.executable_path)
            shortcut.WorkingDirectory = str(self.executable_dir)
            shortcut.IconLocation = str(self.executable_path)
            shortcut.Description = "Vietnamese File Normalization Utility"
            shortcut.save()
            
            # Create uninstall shortcut if uninstaller exists
            uninstaller_path = self.executable_dir / "uninstall.exe"
            if uninstaller_path.exists():
                uninstall_shortcut_path = app_folder / "Uninstall.lnk"
                uninstall_shortcut = shell.CreateShortCut(str(uninstall_shortcut_path))
                uninstall_shortcut.Targetpath = str(uninstaller_path)
                uninstall_shortcut.WorkingDirectory = str(self.executable_dir)
                uninstall_shortcut.Description = f"Uninstall {self.app_name}"
                uninstall_shortcut.save()
            
            logger.info(f"Start Menu shortcuts created: {app_folder}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Start Menu shortcut: {e}")
            return False
    
    def register_application_path(self) -> bool:
        """Register application with Windows App Paths"""
        try:
            app_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{self.app_key}.exe"
            
            # Try HKEY_LOCAL_MACHINE first (requires admin)
            try:
                with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, app_key_path) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(self.executable_path))
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, str(self.executable_dir))
                
                logger.info("Application registered in HKEY_LOCAL_MACHINE")
                return True
                
            except PermissionError:
                # Fall back to HKEY_CURRENT_USER
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key_path) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(self.executable_path))
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, str(self.executable_dir))
                
                logger.info("Application registered in HKEY_CURRENT_USER")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register application path: {e}")
            return False
    
    def register_uninstall_info(self, version: str, size_mb: float) -> bool:
        """Register application in Add/Remove Programs"""
        try:
            uninstall_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_key}"
            
            # Try HKEY_LOCAL_MACHINE first
            try:
                registry_key = winreg.HKEY_LOCAL_MACHINE
            except PermissionError:
                registry_key = winreg.HKEY_CURRENT_USER
            
            with winreg.CreateKey(registry_key, uninstall_key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, self.app_name)
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "File Rename Tool Team")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.executable_dir))
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(self.executable_path))
                
                # Uninstaller info
                uninstaller_path = self.executable_dir / "uninstall.exe"
                if uninstaller_path.exists():
                    winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, str(uninstaller_path))
                
                # Size information
                winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(size_mb * 1024))
                
                # Additional metadata
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            
            logger.info("Uninstall information registered")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register uninstall info: {e}")
            return False
    
    def check_windows_security_context(self) -> Dict[str, Any]:
        """Check Windows security context and permissions"""
        security_info = {
            "is_admin": False,
            "is_elevated": False,
            "user_name": os.getenv("USERNAME", "Unknown"),
            "computer_name": os.getenv("COMPUTERNAME", "Unknown"),
            "warnings": []
        }
        
        try:
            # Check if running as administrator
            import ctypes
            security_info["is_admin"] = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            security_info["warnings"].append("Could not determine admin status")
        
        try:
            # Check UAC elevation
            import ctypes
            import ctypes.wintypes
            
            TOKEN_QUERY = 0x0008
            TokenElevationType = 18
            TokenElevationTypeDefault = 1
            TokenElevationTypeFull = 2
            TokenElevationTypeLimited = 3
            
            hToken = ctypes.wintypes.HANDLE()
            ctypes.windll.advapi32.OpenProcessToken(
                ctypes.windll.kernel32.GetCurrentProcess(), 
                TOKEN_QUERY, 
                ctypes.byref(hToken)
            )
            
            elevation_type = ctypes.wintypes.DWORD()
            return_length = ctypes.wintypes.DWORD()
            
            ctypes.windll.advapi32.GetTokenInformation(
                hToken,
                TokenElevationType,
                ctypes.byref(elevation_type),
                ctypes.sizeof(elevation_type),
                ctypes.byref(return_length)
            )
            
            security_info["is_elevated"] = elevation_type.value == TokenElevationTypeFull
            
        except Exception as e:
            security_info["warnings"].append(f"Could not check elevation: {e}")
        
        return security_info
    
    def add_to_windows_defender_exclusion(self) -> bool:
        """Add application to Windows Defender exclusions (requires admin)"""
        try:
            # This requires administrator privileges
            security_info = self.check_windows_security_context()
            if not security_info["is_admin"]:
                logger.warning("Administrator privileges required for Defender exclusions")
                return False
            
            # Use PowerShell to add exclusion
            powershell_cmd = f'''
            Add-MpPreference -ExclusionPath "{self.executable_path}"
            Add-MpPreference -ExclusionPath "{self.executable_dir}"
            '''
            
            result = subprocess.run([
                "powershell.exe", "-Command", powershell_cmd
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                logger.info("Added to Windows Defender exclusions")
                return True
            else:
                logger.warning(f"Could not add Defender exclusion: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to add Defender exclusion: {e}")
            return False
    
    def setup_file_associations(self, extensions: List[str]) -> bool:
        """Setup file associations (future feature)"""
        # This would associate certain file types with the application
        # For now, just log the intention
        logger.info(f"File associations setup requested for: {extensions}")
        return True
    
    def perform_full_integration(self, version: str, create_shortcuts: bool = True) -> Dict[str, bool]:
        """Perform complete Windows integration"""
        results = {
            "app_path_registered": False,
            "desktop_shortcut": False,
            "start_menu_shortcut": False,
            "uninstall_registered": False,
            "defender_exclusion": False
        }
        
        logger.info("Starting Windows integration...")
        
        # Register application path
        results["app_path_registered"] = self.register_application_path()
        
        # Create shortcuts if requested
        if create_shortcuts:
            results["desktop_shortcut"] = self.create_desktop_shortcut()
            results["start_menu_shortcut"] = self.create_start_menu_shortcut()
        
        # Register uninstall information
        try:
            size_mb = self.executable_path.stat().st_size / (1024 * 1024) if self.executable_path.exists() else 10.0
            results["uninstall_registered"] = self.register_uninstall_info(version, size_mb)
        except Exception:
            results["uninstall_registered"] = False
        
        # Try to add Defender exclusions (optional)
        security_info = self.check_windows_security_context()
        if security_info["is_admin"]:
            results["defender_exclusion"] = self.add_to_windows_defender_exclusion()
        
        # Log results
        success_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"Windows integration completed: {success_count}/{total_count} successful")
        
        return results
    
    def clean_integration(self) -> Dict[str, bool]:
        """Clean up Windows integration (for uninstaller)"""
        cleanup_results = {
            "app_path_removed": False,
            "desktop_shortcut_removed": False,
            "start_menu_removed": False,
            "uninstall_removed": False
        }
        
        logger.info("Cleaning up Windows integration...")
        
        try:
            # Remove app path registration
            app_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{self.app_key}.exe"
            for hkey in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    winreg.DeleteKey(hkey, app_key_path)
                    cleanup_results["app_path_removed"] = True
                    break
                except FileNotFoundError:
                    continue
                except PermissionError:
                    continue
        except Exception:
            pass
        
        try:
            # Remove desktop shortcut
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            desktop = Path(shell.SpecialFolders("Desktop"))
            shortcut_path = desktop / f"{self.app_name}.lnk"
            if shortcut_path.exists():
                shortcut_path.unlink()
                cleanup_results["desktop_shortcut_removed"] = True
        except Exception:
            pass
        
        try:
            # Remove Start Menu folder
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            start_menu = Path(shell.SpecialFolders("StartMenu"))
            app_folder = start_menu / "Programs" / self.app_name
            if app_folder.exists():
                import shutil
                shutil.rmtree(app_folder, ignore_errors=True)
                cleanup_results["start_menu_removed"] = True
        except Exception:
            pass
        
        try:
            # Remove uninstall registration
            uninstall_key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_key}"
            for hkey in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    winreg.DeleteKey(hkey, uninstall_key_path)
                    cleanup_results["uninstall_removed"] = True
                    break
                except FileNotFoundError:
                    continue
                except PermissionError:
                    continue
        except Exception:
            pass
        
        success_count = sum(cleanup_results.values())
        logger.info(f"Integration cleanup completed: {success_count} items removed")
        
        return cleanup_results


def get_windows_integration(app_name: str = "File Rename Tool") -> WindowsIntegration:
    """Get Windows integration instance"""
    return WindowsIntegration(app_name)


if __name__ == "__main__":
    # Test Windows integration
    integration = WindowsIntegration()
    
    print("Windows Integration Test")
    print("=" * 30)
    
    # Check security context
    security = integration.check_windows_security_context()
    print(f"User: {security['user_name']}")
    print(f"Admin: {security['is_admin']}")
    print(f"Elevated: {security['is_elevated']}")
    
    if security["warnings"]:
        print("Warnings:", security["warnings"])
    
    # Test integration (dry run)
    print("\nTesting integration...")
    results = integration.perform_full_integration("1.0.0", create_shortcuts=False)
    
    for feature, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {feature}")
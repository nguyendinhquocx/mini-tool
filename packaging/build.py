#!/usr/bin/env python3
"""
Build script for File Rename Tool
Creates standalone Windows executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Add packaging directory to path
sys.path.insert(0, os.path.dirname(__file__))
from version import __version__, APP_NAME

def clean_build_directories():
    """Remove existing build artifacts"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/ directory...")
            shutil.rmtree(dir_name)
            
def get_git_commit_hash():
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 'unknown'

def update_version_info():
    """Update build metadata in version.py"""
    version_file = os.path.join(os.path.dirname(__file__), 'version.py')
    
    if not os.path.exists(version_file):
        raise FileNotFoundError(f"Version file not found: {version_file}")
    
    commit_hash = get_git_commit_hash()
    build_date = datetime.now().isoformat()
    
    # Read current version file
    with open(version_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update build metadata - handle both None and existing values
    import re
    content = re.sub(
        r'BUILD_DATE = .*',
        f'BUILD_DATE = "{build_date}"',
        content
    )
    content = re.sub(
        r'BUILD_COMMIT = .*',
        f'BUILD_COMMIT = "{commit_hash}"',
        content
    )
    
    # Write updated version file
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Updated build metadata: {commit_hash} at {build_date}")

def create_version_info_file():
    """Create Windows version info file for executable"""
    version_info_content = f'''# UTF-8
#
# Version information for PyInstaller
#

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({__version__.replace('.', ', ')}, 0),
    prodvers=({__version__.replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904E4', [
        StringStruct('CompanyName', 'File Rename Tool Team'),
        StringStruct('FileDescription', 'Vietnamese File Rename Tool'),
        StringStruct('FileVersion', '{__version__}'),
        StringStruct('InternalName', '{APP_NAME}'),
        StringStruct('LegalCopyright', 'Copyright © 2025 File Rename Tool Team'),
        StringStruct('OriginalFilename', '{APP_NAME}.exe'),
        StringStruct('ProductName', 'File Rename Tool'),
        StringStruct('ProductVersion', '{__version__}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1252])])
  ]
)'''

    version_info_file = os.path.join(os.path.dirname(__file__), 'version_info.txt')
    with open(version_info_file, 'w') as f:
        f.write(version_info_content)
    
    print("Created version info file for executable")

def run_pyinstaller(onefile=True):
    """Run PyInstaller với appropriate options"""
    project_root = os.path.dirname(os.path.dirname(__file__))
    spec_file = os.path.join(project_root, 'file-rename-tool.spec')
    
    if not os.path.exists(spec_file):
        raise FileNotFoundError(f"PyInstaller spec file not found: {spec_file}")
    
    # Use correct pyinstaller path from venv
    venv_pyinstaller = os.path.join(project_root, 'venv', 'Scripts', 'pyinstaller.exe')
    if not os.path.exists(venv_pyinstaller):
        # Fallback to system pyinstaller
        venv_pyinstaller = 'pyinstaller'
    
    cmd = [venv_pyinstaller, '--clean', '--noconfirm', spec_file]
    
    print(f"Running PyInstaller: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            cwd=project_root,
            capture_output=True,
            text=True
        )
        print("PyInstaller completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed with error code {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError as e:
        print(f"PyInstaller executable not found: {e}")
        return False

def validate_executable():
    """Check if executable was created successfully"""
    project_root = os.path.dirname(os.path.dirname(__file__))
    dist_dir = os.path.join(project_root, 'dist')
    exe_path = os.path.join(dist_dir, f'{APP_NAME}.exe')
    
    if not os.path.exists(dist_dir):
        print("[FAIL] dist/ directory not found")
        return False
    
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"[OK] Executable created: {exe_path}")
        print(f"[OK] File size: {file_size:.1f} MB")
        
        # Additional validation
        if file_size < 1.0:
            print("[WARNING] Executable size seems too small (< 1MB)")
        elif file_size > 100.0:
            print("[WARNING] Executable size seems large (> 100MB)")
        
        return True
    else:
        print("[FAIL] Executable not found in dist/ directory")
        print(f"Expected: {exe_path}")
        # List what's actually in dist/
        try:
            dist_contents = os.listdir(dist_dir)
            print(f"dist/ contains: {dist_contents}")
        except OSError:
            pass
        return False

def main():
    """Main build process"""
    parser = argparse.ArgumentParser(description='Build File Rename Tool executable')
    parser.add_argument('--onefile', action='store_true', default=True,
                        help='Create single-file executable (default)')
    parser.add_argument('--onedir', action='store_true',
                        help='Create directory distribution')
    parser.add_argument('--clean', action='store_true', default=True,
                        help='Clean build directories first (default)')
    
    args = parser.parse_args()
    
    # Use onefile unless explicitly requested onedir
    onefile = not args.onedir
    
    print(f"Building {APP_NAME} v{__version__}")
    print("=" * 50)
    
    try:
        if args.clean:
            clean_build_directories()
        
        update_version_info()
        create_version_info_file()
        
        if run_pyinstaller(onefile=onefile):
            if validate_executable():
                print("\n[SUCCESS] Build completed successfully!")
                return 0
            else:
                print("\n[FAILED] Build validation failed")
                return 1
        else:
            print("\n[FAILED] Build failed")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] Build error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
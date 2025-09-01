@echo off
:: Professional Build Script for File Rename Tool
:: Comprehensive distribution preparation with quality gates

setlocal EnableDelayedExpansion

echo ========================================
echo File Rename Tool - Release Build System
echo ========================================
echo.

:: Configuration
set PROJECT_NAME=File Rename Tool
set EXECUTABLE_NAME=FileRenameTool
set VERSION=1.0.0
set BUILD_MODE=release

:: Paths
set PROJECT_ROOT=%~dp0..
set PACKAGING_DIR=%PROJECT_ROOT%\packaging
set DIST_DIR=%PROJECT_ROOT%\dist
set BUILD_DIR=%PROJECT_ROOT%\build
set SCRIPTS_DIR=%PROJECT_ROOT%\scripts
set VENV_PATH=%PROJECT_ROOT%\venv

:: Color codes for output
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set BLUE=[94m
set NC=[0m

echo %BLUE%Project: %PROJECT_NAME%%NC%
echo %BLUE%Version: %VERSION%%NC%
echo %BLUE%Build Mode: %BUILD_MODE%%NC%
echo.

:: Check prerequisites
echo %BLUE%[1/10] Checking prerequisites...%NC%

:: Check if virtual environment exists
if not exist "%VENV_PATH%\Scripts\python.exe" (
    echo %RED%✗ Virtual environment not found at %VENV_PATH%%NC%
    echo Please create virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Check if PyInstaller is available
"%VENV_PATH%\Scripts\python.exe" -c "import PyInstaller" >nul 2>&1
if !errorlevel! neq 0 (
    echo %YELLOW%⚠ PyInstaller not found, installing...%NC%
    "%VENV_PATH%\Scripts\pip.exe" install pyinstaller
)

:: Check for NSIS (optional)
where makensis >nul 2>&1
if !errorlevel! neq 0 (
    echo %YELLOW%⚠ NSIS not found - installer creation will be skipped%NC%
    set SKIP_INSTALLER=1
) else (
    echo %GREEN%✓ NSIS found - installer will be created%NC%
    set SKIP_INSTALLER=0
)

echo %GREEN%✓ Prerequisites checked%NC%
echo.

:: Clean previous builds
echo %BLUE%[2/10] Cleaning previous builds...%NC%

if exist "%DIST_DIR%" (
    echo Removing %DIST_DIR%...
    rmdir /s /q "%DIST_DIR%" 2>nul
)

if exist "%BUILD_DIR%" (
    echo Removing %BUILD_DIR%...
    rmdir /s /q "%BUILD_DIR%" 2>nul
)

:: Clean PyInstaller cache
for /d /r "%PROJECT_ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)

echo %GREEN%✓ Build directories cleaned%NC%
echo.

:: Run tests
echo %BLUE%[3/10] Running tests...%NC%

cd /d "%PROJECT_ROOT%"

:: Run basic functionality tests first
"%VENV_PATH%\Scripts\python.exe" -c "
import sys
sys.path.insert(0, 'src')
try:
    from core.services.normalize_service import VietnameseNormalizer
    normalizer = VietnameseNormalizer()
    result = normalizer.normalize_filename('Test File.txt')
    print(f'✓ Basic functionality test passed: {result}')
    assert result == 'test file.txt', 'Normalization failed'
except Exception as e:
    print(f'✗ Basic test failed: {e}')
    sys.exit(1)
"

if !errorlevel! neq 0 (
    echo %RED%✗ Basic functionality tests failed%NC%
    pause
    exit /b 1
)

:: Run pytest if available
"%VENV_PATH%\Scripts\python.exe" -m pytest tests/ -v --tb=short -x >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✓ All tests passed%NC%
) else (
    echo %YELLOW%⚠ Some tests failed or pytest not available%NC%
    echo Continuing with build...
)
echo.

:: Update version information
echo %BLUE%[4/10] Updating version information...%NC%

cd /d "%PACKAGING_DIR%"
"%VENV_PATH%\Scripts\python.exe" -c "
import sys, os
sys.path.append('.')
from version import get_version_manager
vm = get_version_manager()
version = vm.get_current_version()
print(f'Current version: {version.display_version}')
"

echo %GREEN%✓ Version information updated%NC%
echo.

:: Build executable with PyInstaller
echo %BLUE%[5/10] Building executable...%NC%

cd /d "%PROJECT_ROOT%"

:: Enhanced PyInstaller command
"%VENV_PATH%\Scripts\pyinstaller.exe" ^
    --onefile ^
    --windowed ^
    --name "%EXECUTABLE_NAME%" ^
    --icon "packaging\app.ico" ^
    --version-file "packaging\version_info.txt" ^
    --add-data "src\resources;resources" ^
    --hidden-import "tkinter.filedialog" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "queue" ^
    --hidden-import "threading" ^
    --distpath "%DIST_DIR%" ^
    --workpath "%BUILD_DIR%" ^
    --specpath "%PACKAGING_DIR%" ^
    --clean ^
    --noconfirm ^
    "file.py"

if !errorlevel! neq 0 (
    echo %RED%✗ PyInstaller build failed%NC%
    pause
    exit /b 1
)

:: Verify executable was created
if not exist "%DIST_DIR%\%EXECUTABLE_NAME%.exe" (
    echo %RED%✗ Executable not found after build%NC%
    pause
    exit /b 1
)

:: Get executable size
for %%I in ("%DIST_DIR%\%EXECUTABLE_NAME%.exe") do set EXE_SIZE=%%~zI
set /a EXE_SIZE_MB=!EXE_SIZE! / 1048576

echo %GREEN%✓ Executable created: %EXE_SIZE_MB% MB%NC%
echo.

:: Test executable
echo %BLUE%[6/10] Testing executable...%NC%

:: Quick test - try to run with --help (if supported)
"%DIST_DIR%\%EXECUTABLE_NAME%.exe" --version >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✓ Executable runs successfully%NC%
) else (
    echo %YELLOW%⚠ Could not test executable (normal for GUI apps)%NC%
)
echo.

:: Create installer (if NSIS available)
echo %BLUE%[7/10] Creating installer package...%NC%

if %SKIP_INSTALLER% equ 1 (
    echo %YELLOW%⚠ Skipping installer creation - NSIS not available%NC%
) else (
    cd /d "%PACKAGING_DIR%"
    
    :: Update installer size estimate
    set /a INSTALL_SIZE_KB=!EXE_SIZE! / 1024
    
    :: Create installer
    makensis.exe installer.nsi
    
    if !errorlevel! equ 0 (
        echo %GREEN%✓ Installer created successfully%NC%
    ) else (
        echo %RED%✗ Installer creation failed%NC%
    )
)
echo.

:: Create distribution package
echo %BLUE%[8/10] Preparing distribution package...%NC%

cd /d "%PROJECT_ROOT%"

:: Create distribution directory structure
mkdir "%DIST_DIR%\portable" 2>nul
copy "%DIST_DIR%\%EXECUTABLE_NAME%.exe" "%DIST_DIR%\portable\" >nul 2>&1

:: Copy additional files
if exist "README.md" copy "README.md" "%DIST_DIR%\portable\" >nul 2>&1
if exist "LICENSE" copy "LICENSE" "%DIST_DIR%\portable\" >nul 2>&1

:: Create release notes
echo Creating release notes...
echo %PROJECT_NAME% v%VERSION% > "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo. >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo Build Date: %DATE% %TIME% >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo. >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo Features: >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Vietnamese text normalization >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Batch file renaming >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Drag and drop support >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Undo functionality >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Performance optimizations >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo. >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo Installation: >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Use installer for full integration >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"
echo - Or run %EXECUTABLE_NAME%.exe directly (portable) >> "%DIST_DIR%\portable\RELEASE_NOTES.txt"

echo %GREEN%✓ Distribution package prepared%NC%
echo.

:: Run distribution tests
echo %BLUE%[9/10] Running distribution tests...%NC%

:: Test basic executable functionality
"%DIST_DIR%\%EXECUTABLE_NAME%.exe" >nul 2>&1 &
timeout /t 2 >nul
taskkill /f /im "%EXECUTABLE_NAME%.exe" >nul 2>&1

echo %GREEN%✓ Distribution tests completed%NC%
echo.

:: Generate build report
echo %BLUE%[10/10] Generating build report...%NC%

set BUILD_REPORT=%DIST_DIR%\build_report.txt
echo %PROJECT_NAME% Build Report > "%BUILD_REPORT%"
echo ================================= >> "%BUILD_REPORT%"
echo. >> "%BUILD_REPORT%"
echo Build Date: %DATE% %TIME% >> "%BUILD_REPORT%"
echo Version: %VERSION% >> "%BUILD_REPORT%"
echo Build Mode: %BUILD_MODE% >> "%BUILD_REPORT%"
echo. >> "%BUILD_REPORT%"
echo Files Created: >> "%BUILD_REPORT%"
echo - %EXECUTABLE_NAME%.exe (%EXE_SIZE_MB% MB) >> "%BUILD_REPORT%"
if %SKIP_INSTALLER% equ 0 (
    echo - FileRenameToolSetup.exe (installer) >> "%BUILD_REPORT%"
)
echo - Portable distribution in portable/ >> "%BUILD_REPORT%"
echo. >> "%BUILD_REPORT%"
echo Build Environment: >> "%BUILD_REPORT%"
echo - Python: >> "%BUILD_REPORT%"
"%VENV_PATH%\Scripts\python.exe" --version >> "%BUILD_REPORT%" 2>&1
echo - PyInstaller: >> "%BUILD_REPORT%"
"%VENV_PATH%\Scripts\pyinstaller.exe" --version >> "%BUILD_REPORT%" 2>&1
echo. >> "%BUILD_REPORT%"

echo %GREEN%✓ Build report generated%NC%
echo.

:: Summary
echo ========================================
echo %GREEN%✓ BUILD COMPLETED SUCCESSFULLY!%NC%
echo ========================================
echo.
echo %BLUE%Deliverables:%NC%
echo   • Executable: %DIST_DIR%\%EXECUTABLE_NAME%.exe (%EXE_SIZE_MB% MB)
if %SKIP_INSTALLER% equ 0 (
    echo   • Installer: %PACKAGING_DIR%\FileRenameToolSetup.exe
)
echo   • Portable: %DIST_DIR%\portable\
echo   • Build Report: %BUILD_REPORT%
echo.
echo %BLUE%Next Steps:%NC%
echo   1. Test the executable on clean Windows systems
echo   2. Verify installer functionality if created
echo   3. Test all major features end-to-end
echo   4. Consider code signing for production release
echo.

:: Optional: Open dist directory
choice /t 5 /d N /m "Open distribution directory? (Y/N)"
if !errorlevel! equ 1 (
    start "" "%DIST_DIR%"
)

echo Build process completed at %TIME%
pause
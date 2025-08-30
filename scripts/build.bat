@echo off
setlocal EnableDelayedExpansion

REM File Rename Tool - Windows Build Script
REM Automates PyInstaller executable creation

echo ===============================================
echo File Rename Tool - Windows Build Script
echo ===============================================

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: py -m venv venv
    echo Then install dependencies: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if PyInstaller is installed
venv\Scripts\pyinstaller.exe --version >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] PyInstaller not found in virtual environment
    echo Please install: venv\Scripts\pip install pyinstaller
    pause 
    exit /b 1
)

REM Clean previous builds
echo [INFO] Cleaning previous builds...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul

REM Run build script
echo [INFO] Starting build process...
venv\Scripts\python.exe packaging\build.py --onefile --clean

REM Check build result
if exist "dist\FileRenameTool.exe" (
    echo.
    echo [SUCCESS] Build completed successfully!
    echo Executable created: dist\FileRenameTool.exe
    
    REM Show file size
    for %%A in ("dist\FileRenameTool.exe") do (
        set /a size=%%~zA/1024/1024
        echo File size: !size! MB
    )
    
    echo.
    echo Press any key to exit...
    pause >nul
) else (
    echo.
    echo [ERROR] Build failed - executable not found
    echo Check the build output above for errors
    pause
    exit /b 1
)

endlocal
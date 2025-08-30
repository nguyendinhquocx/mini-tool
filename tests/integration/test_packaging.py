"""
Integration tests for packaging system
"""

import os
import pytest
import subprocess
import tempfile
from pathlib import Path

class TestPyInstallerIntegration:
    """Test PyInstaller integration"""
    
    def test_spec_file_exists(self):
        """Test PyInstaller spec file exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        spec_file = os.path.join(project_root, 'file-rename-tool.spec')
        assert os.path.exists(spec_file)
    
    def test_spec_file_syntax(self):
        """Test spec file has valid Python syntax"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        spec_file = os.path.join(project_root, 'file-rename-tool.spec')
        
        # Try to compile the spec file
        with open(spec_file, 'r') as f:
            content = f.read()
        
        try:
            compile(content, spec_file, 'exec')
        except SyntaxError as e:
            pytest.fail(f"Spec file has syntax error: {e}")

class TestBuildAutomation:
    """Test build automation scripts"""
    
    def test_batch_script_exists(self):
        """Test Windows batch script exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        batch_script = os.path.join(project_root, 'scripts', 'build.bat')
        assert os.path.exists(batch_script)
    
    def test_makefile_exists(self):
        """Test Makefile exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        makefile = os.path.join(project_root, 'Makefile')
        assert os.path.exists(makefile)
    
    @pytest.mark.slow
    def test_build_script_validation(self):
        """Test build script can be imported without errors"""
        import sys
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        packaging_path = os.path.join(project_root, 'packaging')
        
        # Add to path temporarily
        if packaging_path not in sys.path:
            sys.path.insert(0, packaging_path)
        
        try:
            import build
            # Test that main functions exist
            assert hasattr(build, 'main')
            assert hasattr(build, 'run_pyinstaller')
            assert hasattr(build, 'validate_executable')
        except ImportError as e:
            pytest.fail(f"Build script import failed: {e}")
        finally:
            if packaging_path in sys.path:
                sys.path.remove(packaging_path)

class TestExecutableValidation:
    """Test executable validation (if available)"""
    
    def test_executable_exists_if_built(self):
        """Test executable exists if dist directory is present"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dist_dir = os.path.join(project_root, 'dist')
        
        if os.path.exists(dist_dir):
            exe_path = os.path.join(dist_dir, 'FileRenameTool.exe')
            assert os.path.exists(exe_path), "Executable should exist in dist directory"
            
            # Check file size (should be reasonable)
            file_size = os.path.getsize(exe_path)
            assert file_size > 1024 * 1024, "Executable should be larger than 1MB"
            assert file_size < 100 * 1024 * 1024, "Executable should be smaller than 100MB"
    
    def test_venv_structure(self):
        """Test virtual environment structure"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        venv_dir = os.path.join(project_root, 'venv')
        
        if os.path.exists(venv_dir):
            # Check for key venv components
            scripts_dir = os.path.join(venv_dir, 'Scripts')  # Windows
            lib_dir = os.path.join(venv_dir, 'Lib')  # Windows
            
            assert os.path.exists(scripts_dir), "Venv Scripts directory should exist"
            assert os.path.exists(lib_dir), "Venv Lib directory should exist"
            
            # Check for PyInstaller
            pyinstaller_exe = os.path.join(scripts_dir, 'pyinstaller.exe')
            if os.path.exists(pyinstaller_exe):
                assert os.path.isfile(pyinstaller_exe), "PyInstaller should be executable file"
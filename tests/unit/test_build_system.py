"""
Unit tests for build system components
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
import sys

# Add packaging to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'packaging'))
from version import __version__, APP_NAME, get_version_info

class TestVersionManagement:
    """Test version management functionality"""
    
    def test_version_info_structure(self):
        """Test version info has correct structure"""
        version_info = get_version_info()
        
        required_keys = ['version', 'title', 'description', 'author', 'copyright']
        for key in required_keys:
            assert key in version_info
            assert version_info[key] is not None
    
    def test_version_format(self):
        """Test version follows semantic versioning"""
        version_parts = __version__.split('.')
        assert len(version_parts) == 3
        
        for part in version_parts:
            assert part.isdigit()
    
    def test_app_name_valid(self):
        """Test app name is valid for executable"""
        assert APP_NAME
        assert ' ' not in APP_NAME  # No spaces in executable name
        assert len(APP_NAME) > 0

class TestBuildConfiguration:
    """Test build configuration files"""
    
    def test_pyproject_toml_exists(self):
        """Test pyproject.toml exists and is valid"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        pyproject_path = os.path.join(project_root, 'pyproject.toml')
        assert os.path.exists(pyproject_path)
    
    def test_requirements_txt_exists(self):
        """Test requirements.txt exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        requirements_path = os.path.join(project_root, 'requirements.txt')
        assert os.path.exists(requirements_path)
    
    def test_gitignore_exists(self):
        """Test .gitignore exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        gitignore_path = os.path.join(project_root, '.gitignore')
        assert os.path.exists(gitignore_path)
        
        # Check it contains Python patterns
        with open(gitignore_path, 'r') as f:
            content = f.read()
            assert '__pycache__/' in content
            assert '*.py[cod]' in content or '*.pyc' in content
            assert 'dist/' in content

class TestProjectStructure:
    """Test project structure compliance"""
    
    def test_packaging_directory_exists(self):
        """Test packaging directory exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        packaging_path = os.path.join(project_root, 'packaging')
        assert os.path.exists(packaging_path)
        assert os.path.isdir(packaging_path)
    
    def test_scripts_directory_exists(self):
        """Test scripts directory exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        scripts_path = os.path.join(project_root, 'scripts')
        assert os.path.exists(scripts_path)
        assert os.path.isdir(scripts_path)
    
    def test_build_script_exists(self):
        """Test build.py script exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        build_script_path = os.path.join(project_root, 'packaging', 'build.py')
        assert os.path.exists(build_script_path)
    
    def test_version_file_exists(self):
        """Test version.py file exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        version_file_path = os.path.join(project_root, 'packaging', 'version.py')
        assert os.path.exists(version_file_path)
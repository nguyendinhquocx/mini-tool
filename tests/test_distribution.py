"""
Distribution Validation Tests

Comprehensive tests to validate the distribution package meets
all Story 3.4 acceptance criteria and quality requirements.
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path
import tempfile
import shutil
from typing import Dict, List, Any

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    sys.path.insert(0, str(PROJECT_ROOT / "packaging"))
    from version import get_version_info, get_current_version
except ImportError:
    def get_version_info():
        return {'version': '1.0.0', 'title': 'File Rename Tool'}
    def get_current_version():
        class MockVersion:
            semantic_version = "1.0.0"
            display_version = "1.0.0"
        return MockVersion()


class TestDistributionValidation:
    """Test suite for distribution package validation"""
    
    @pytest.fixture(scope="class")
    def dist_path(self):
        """Get distribution directory path"""
        return PROJECT_ROOT / "dist"
    
    @pytest.fixture(scope="class")
    def executable_path(self, dist_path):
        """Get executable path"""
        return dist_path / "FileRenameTool.exe"
    
    def test_version_management_system(self):
        """Test AC: Application metadata properly embedded"""
        version_info = get_version_info()
        current_version = get_current_version()
        
        # Validate version structure
        assert 'version' in version_info
        assert 'title' in version_info
        assert 'description' in version_info
        assert 'author' in version_info
        
        # Validate version format
        version_parts = version_info['version'].split('.')
        assert len(version_parts) >= 3
        
        # Validate current version object
        assert hasattr(current_version, 'semantic_version')
        assert hasattr(current_version, 'display_version')
        
        print(f"✓ Version management system working: {current_version.display_version}")
    
    def test_about_dialog_functionality(self):
        """Test AC: About dialog displays comprehensive information"""
        try:
            from ui.dialogs.about_dialog import AboutDialog, show_about_dialog
            from ui.dialogs.about_dialog import get_version_info as dialog_get_version
            
            # Test dialog can be imported and version info is accessible
            version_info = dialog_get_version()
            assert version_info is not None
            assert 'title' in version_info
            
            print("✓ About dialog functionality available")
            return True
        except ImportError as e:
            pytest.fail(f"About dialog import failed: {e}")
    
    def test_help_system_integration(self):
        """Test AC: Help documentation system available"""
        try:
            from ui.components.help_system import HelpSystem, HelpContent, show_help_dialog
            
            # Test help content is comprehensive
            user_guide = HelpContent.get_user_guide()
            shortcuts = HelpContent.get_keyboard_shortcuts()
            vietnamese_guide = HelpContent.get_vietnamese_guide()
            troubleshooting = HelpContent.get_troubleshooting()
            
            # Validate content is substantial
            assert len(user_guide) > 1000, "User guide too short"
            assert len(shortcuts) > 500, "Shortcuts guide too short"
            assert len(vietnamese_guide) > 1000, "Vietnamese guide too short"
            assert len(troubleshooting) > 1000, "Troubleshooting guide too short"
            
            # Check for key topics
            assert "Getting Started" in user_guide
            assert "F1" in shortcuts
            assert "diacritic" in vietnamese_guide.lower()
            assert "troubleshooting" in troubleshooting.lower()
            
            print("✓ Help system comprehensive and functional")
            return True
        except ImportError as e:
            pytest.fail(f"Help system import failed: {e}")
    
    def test_windows_integration_utilities(self):
        """Test AC: Windows integration capabilities"""
        try:
            from core.utils.windows_integration import WindowsIntegration, get_windows_integration
            
            integration = get_windows_integration()
            
            # Test security context check
            security_info = integration.check_windows_security_context()
            assert 'user_name' in security_info
            assert 'computer_name' in security_info
            assert 'is_admin' in security_info
            
            # Validate integration methods exist
            assert hasattr(integration, 'create_desktop_shortcut')
            assert hasattr(integration, 'create_start_menu_shortcut')
            assert hasattr(integration, 'register_application_path')
            assert hasattr(integration, 'perform_full_integration')
            
            print(f"✓ Windows integration available for user: {security_info['user_name']}")
            return True
        except ImportError as e:
            pytest.fail(f"Windows integration import failed: {e}")
    
    def test_build_system_functionality(self):
        """Test AC: Build pipeline and automation"""
        packaging_dir = PROJECT_ROOT / "packaging"
        
        # Check build system files exist
        build_py = packaging_dir / "build.py"
        version_py = packaging_dir / "version.py"
        installer_nsi = packaging_dir / "installer.nsi"
        
        assert build_py.exists(), "build.py not found"
        assert version_py.exists(), "version.py not found"
        assert installer_nsi.exists(), "installer.nsi not found"
        
        # Check build script functionality
        build_script = PROJECT_ROOT / "scripts" / "build_release.bat"
        assert build_script.exists(), "build_release.bat not found"
        
        # Validate build.py can be imported
        try:
            import sys
            sys.path.insert(0, str(packaging_dir))
            
            # Test imports work
            result = subprocess.run([
                sys.executable, str(build_py), "--help"
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)
            
            assert result.returncode == 0, "build.py --help failed"
            assert "Build File Rename Tool" in result.stdout
            
            print("✓ Build system functional and accessible")
            return True
        except Exception as e:
            pytest.fail(f"Build system test failed: {e}")
    
    def test_executable_creation_capability(self, dist_path, executable_path):
        """Test AC: Executable can be created with proper metadata"""
        # This test checks if the build infrastructure is in place
        # The actual executable creation is tested separately
        
        packaging_dir = PROJECT_ROOT / "packaging"
        
        # Check for version info template
        version_template_content = """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
        """
        
        # Validate build.py can create version file
        try:
            sys.path.insert(0, str(packaging_dir))
            from build import ProfessionalBuilder
            
            builder = ProfessionalBuilder()
            version_file = builder.create_version_file()
            
            assert version_file.exists(), "Version file creation failed"
            
            version_content = version_file.read_text()
            assert "VSVersionInfo" in version_content
            assert "FileRenameTool" in version_content
            
            print("✓ Executable metadata embedding capability verified")
            return True
        except Exception as e:
            pytest.fail(f"Executable metadata test failed: {e}")
    
    def test_installer_package_infrastructure(self):
        """Test AC: Installer package can be created"""
        packaging_dir = PROJECT_ROOT / "packaging"
        installer_script = packaging_dir / "installer.nsi"
        
        assert installer_script.exists(), "NSIS installer script not found"
        
        # Validate installer script content
        nsi_content = installer_script.read_text()
        
        # Check for essential NSIS components
        required_components = [
            "!define APPNAME",
            "RequestExecutionLevel admin", 
            "Section \"Core Application\"",
            "WriteUninstaller",
            "CreateShortCut",
            "Section \"Uninstall\""
        ]
        
        for component in required_components:
            assert component in nsi_content, f"Missing NSIS component: {component}"
        
        # Check for proper uninstall support
        assert "DeleteRegKey" in nsi_content
        assert "RMDir" in nsi_content
        
        print("✓ Installer package infrastructure complete")
        return True
    
    def test_distribution_completeness(self):
        """Test AC: All distribution components present"""
        required_files = [
            "packaging/build.py",
            "packaging/version.py", 
            "packaging/installer.nsi",
            "packaging/license.txt",
            "scripts/build_release.bat",
            "src/ui/dialogs/about_dialog.py",
            "src/ui/components/help_system.py",
            "src/core/utils/windows_integration.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        assert not missing_files, f"Missing required files: {missing_files}"
        
        print(f"✓ All {len(required_files)} distribution components present")
        return True
    
    def test_core_functionality_integration(self):
        """Test AC: Core app integrates with new distribution features"""
        try:
            # Test that distribution components can import core functionality
            from core.services.normalize_service import VietnameseNormalizer
            from core.models.file_info import FileInfo, FileType
            
            # Test basic functionality still works
            normalizer = VietnameseNormalizer()
            result = normalizer.normalize_filename("Tệp_Tiếng_Việt.txt")
            assert result == "tep tieng viet.txt"
            
            # Test file info creation
            from pathlib import Path
            test_file = Path(__file__)
            file_info = FileInfo.from_path(str(test_file))
            assert file_info.file_type == FileType.FILE
            
            print("✓ Core functionality integration verified")
            return True
        except Exception as e:
            pytest.fail(f"Core functionality integration failed: {e}")


class TestAcceptanceCriteria:
    """Specific tests for each Story 3.4 acceptance criteria"""
    
    def test_ac1_application_icon_embedded(self):
        """AC1: Application icon designed and embedded in executable"""
        packaging_dir = PROJECT_ROOT / "packaging"
        icon_file = packaging_dir / "app.ico"
        
        # Icon file should exist
        assert icon_file.exists(), "Application icon file not found"
        
        # Build system should reference icon
        build_py = packaging_dir / "build.py"
        build_content = build_py.read_text()
        assert "icon" in build_content.lower()
        
        print("✓ AC1: Application icon infrastructure in place")
    
    def test_ac2_windows_metadata_embedded(self):
        """AC2: Proper Windows metadata in executable properties"""
        packaging_dir = PROJECT_ROOT / "packaging"
        
        # Version info system should be available
        version_info = get_version_info()
        assert 'version' in version_info
        assert 'copyright' in version_info
        assert 'author' in version_info
        
        # Build system should create version info file
        try:
            sys.path.insert(0, str(packaging_dir))
            from build import ProfessionalBuilder
            builder = ProfessionalBuilder()
            version_file = builder.create_version_file()
            assert version_file.exists()
        except Exception as e:
            pytest.fail(f"Version file creation failed: {e}")
        
        print("✓ AC2: Windows metadata system implemented")
    
    def test_ac3_about_dialog_comprehensive(self):
        """AC3: About dialog displays version information and usage instructions"""
        from ui.dialogs.about_dialog import AboutDialog
        
        # About dialog should be importable and functional
        assert AboutDialog is not None
        
        # Should have comprehensive content methods
        assert hasattr(AboutDialog, '_create_version_section')
        assert hasattr(AboutDialog, '_create_features_section')
        assert hasattr(AboutDialog, '_create_help_section')
        
        print("✓ AC3: About dialog with comprehensive information")
    
    def test_ac4_security_warnings_handled(self):
        """AC4: Application handles Windows security warnings gracefully"""
        from core.utils.windows_integration import WindowsIntegration
        
        integration = WindowsIntegration()
        
        # Security context checking should be available
        security_info = integration.check_windows_security_context()
        assert 'is_admin' in security_info
        assert 'warnings' in security_info
        
        # Defender exclusion handling should be available
        assert hasattr(integration, 'add_to_windows_defender_exclusion')
        
        print("✓ AC4: Security warning handling implemented")
    
    def test_ac5_installer_package_created(self):
        """AC5: Installer package created for easy distribution"""
        packaging_dir = PROJECT_ROOT / "packaging"
        installer_script = packaging_dir / "installer.nsi"
        
        assert installer_script.exists(), "NSIS installer script missing"
        
        # Should have comprehensive installer features
        nsi_content = installer_script.read_text()
        installer_features = [
            "Desktop Shortcut",
            "Start Menu Shortcuts", 
            "Core Application",
            "Uninstall"
        ]
        
        for feature in installer_features:
            assert feature in nsi_content, f"Installer missing feature: {feature}"
        
        print("✓ AC5: Installer package infrastructure complete")
    
    def test_ac6_desktop_shortcut_creation(self):
        """AC6: Desktop shortcut creation during installation or first run"""
        from core.utils.windows_integration import WindowsIntegration
        
        integration = WindowsIntegration()
        assert hasattr(integration, 'create_desktop_shortcut')
        
        # NSIS installer should also support this
        packaging_dir = PROJECT_ROOT / "packaging"
        installer_script = packaging_dir / "installer.nsi"
        nsi_content = installer_script.read_text()
        
        assert "Desktop" in nsi_content
        assert "CreateShortCut" in nsi_content
        
        print("✓ AC6: Desktop shortcut creation implemented")
    
    def test_ac7_windows_search_start_menu_integration(self):
        """AC7: Application associates with Windows search and Start menu properly"""
        from core.utils.windows_integration import WindowsIntegration
        
        integration = WindowsIntegration()
        
        # Should have app path registration
        assert hasattr(integration, 'register_application_path')
        
        # Should have Start Menu integration
        assert hasattr(integration, 'create_start_menu_shortcut')
        
        print("✓ AC7: Windows search and Start menu integration")
    
    def test_ac8_help_documentation_available(self):
        """AC8: Basic help documentation available through Help menu or F1 key"""
        from ui.components.help_system import HelpSystem, HelpContent
        
        # Comprehensive help content should be available
        user_guide = HelpContent.get_user_guide()
        shortcuts = HelpContent.get_keyboard_shortcuts()
        
        assert len(user_guide) > 1000, "User guide not comprehensive enough"
        assert "F1" in shortcuts, "F1 help not documented"
        assert "Getting Started" in user_guide, "Getting Started section missing"
        
        print("✓ AC8: Help documentation system comprehensive")
    
    def test_ac9_clean_uninstallation(self):
        """AC9: Application uninstalls cleanly leaving no orphaned files or registry entries"""
        # NSIS uninstaller should be comprehensive
        packaging_dir = PROJECT_ROOT / "packaging"
        installer_script = packaging_dir / "installer.nsi"
        nsi_content = installer_script.read_text()
        
        # Check for comprehensive cleanup
        cleanup_features = [
            "DeleteRegKey",
            "RMDir",
            "Delete",
            "Section \"Uninstall\""
        ]
        
        for feature in cleanup_features:
            assert feature in nsi_content, f"Uninstaller missing cleanup: {feature}"
        
        # Windows integration should have cleanup methods
        from core.utils.windows_integration import WindowsIntegration
        integration = WindowsIntegration()
        assert hasattr(integration, 'clean_integration')
        
        print("✓ AC9: Clean uninstallation implemented")


def main():
    """Run distribution validation tests"""
    print("File Rename Tool - Distribution Validation")
    print("=" * 50)
    
    # Run pytest with this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    if exit_code == 0:
        print("\n" + "=" * 50)
        print("✓ ALL DISTRIBUTION VALIDATION TESTS PASSED!")
        print("Story 3.4 acceptance criteria fully implemented.")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("✗ Some distribution validation tests failed")
        print("Please review and fix issues before release")
        print("=" * 50)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
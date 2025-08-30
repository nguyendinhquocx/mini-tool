# Unified Project Structure

```
file-rename-tool/
├── .github/                    # CI/CD workflows  
│   └── workflows/
│       ├── build.yml           # Build và test automation
│       └── release.yml         # Release packaging workflow
├── src/                        # Application source code
│   ├── main.py                 # Application entry point
│   ├── ui/                     # User interface layer
│   │   ├── __init__.py
│   │   ├── main_window.py      # Primary application window
│   │   ├── components/         # Reusable UI components
│   │   │   ├── __init__.py
│   │   │   ├── folder_selector.py
│   │   │   ├── file_preview.py
│   │   │   ├── progress_dialog.py
│   │   │   ├── settings_panel.py
│   │   │   └── status_bar.py
│   │   ├── dialogs/           # Modal dialogs
│   │   │   ├── __init__.py
│   │   │   ├── error_dialog.py
│   │   │   ├── confirm_dialog.py
│   │   │   └── about_dialog.py
│   │   └── styles/            # UI styling và theming
│   │       ├── __init__.py
│   │       ├── themes.py
│   │       └── constants.py
│   ├── core/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── application.py     # Main application controller
│   │   ├── services/          # Business services
│   │   │   ├── __init__.py
│   │   │   ├── file_service.py
│   │   │   ├── config_service.py
│   │   │   ├── history_service.py
│   │   │   └── normalize_service.py
│   │   ├── repositories/      # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── config_repository.py
│   │   │   ├── history_repository.py
│   │   │   └── file_repository.py
│   │   ├── models/            # Data models
│   │   │   ├── __init__.py
│   │   │   ├── file_info.py
│   │   │   ├── operation.py
│   │   │   └── config.py
│   │   └── utils/             # Utility functions
│   │       ├── __init__.py
│   │       ├── error_handler.py
│   │       ├── logger.py
│   │       └── validators.py
│   └── resources/             # Static resources
│       ├── icons/             # Application icons
│       ├── styles/            # CSS/styling resources
│       └── config/            # Default configuration files
├── tests/                     # Test suites
│   ├── __init__.py
│   ├── unit/                  # Unit tests
│   │   ├── test_file_service.py
│   │   ├── test_normalize_service.py
│   │   └── test_config_service.py
│   ├── integration/           # Integration tests
│   │   ├── test_file_operations.py
│   │   └── test_ui_workflows.py
│   └── fixtures/              # Test data và fixtures
│       ├── sample_files/
│       └── test_configs/
├── packaging/                 # Distribution và packaging
│   ├── build.py              # PyInstaller build script
│   ├── installer.nsi         # NSIS installer script (optional)
│   ├── requirements.txt      # Python dependencies
│   └── version.py            # Version management
├── docs/                     # Documentation
│   ├── prd.md
│   ├── front-end-spec.md
│   ├── architecture.md
│   ├── user-guide.md
│   └── developer-guide.md
├── scripts/                  # Build và utility scripts
│   ├── build.bat            # Windows build script
│   ├── test.bat             # Test execution script
│   └── clean.bat            # Cleanup script
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup configuration
├── pyproject.toml           # Modern Python project configuration
├── Makefile                 # Build automation (cross-platform)
└── README.md                # Project documentation
```

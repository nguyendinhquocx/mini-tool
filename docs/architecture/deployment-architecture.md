# Deployment Architecture

## Deployment Strategy

**Application Packaging**:
- **Platform**: PyInstaller executable generation
- **Build Command**: `python packaging/build.py --onefile`
- **Output Directory**: `dist/`
- **Distribution Method**: Direct download, optional Windows installer

**Executable Distribution**:
- **Primary**: Standalone .exe file (~50MB)
- **Secondary**: MSI installer package (optional)
- **Update Mechanism**: Manual download và replacement
- **Installation**: Copy-to-run hoặc installer-based

## CI/CD Pipeline
```yaml
name: Build and Release
on:
  push:
    branches: [main]
    tags: [v*]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e .
      
      - name: Run tests
        run: python -m pytest tests/ --cov=src/
      
      - name: Code quality checks
        run: |
          black --check src/ tests/
          flake8 src/ tests/
          mypy src/

  build:
    needs: test
    runs-on: windows-latest
    if: startsWith(github.ref, 'refs/tags/')
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      
      - name: Build executable
        run: python packaging/build.py --release
      
      - name: Create installer (optional)
        run: makensis packaging/installer.nsi
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: file-rename-tool-${{ github.ref_name }}
          path: dist/
```

## Environments
| Environment | Purpose | Distribution Method |
|-------------|---------|-------------------|
| Development | Local development và testing | Direct Python execution |
| Staging | Pre-release testing | Beta executable distribution |
| Production | End user release | Official executable + installer |

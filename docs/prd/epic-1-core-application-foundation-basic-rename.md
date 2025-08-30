# Epic 1: Core Application Foundation & Basic Rename

**Goal**: Establish foundational application infrastructure với packaging pipeline while delivering core Vietnamese text normalization functionality for single folder batch rename operations, creating deployable MVP.

## Story 1.1: Project Setup & Build Pipeline
As a developer,
I want a properly configured development environment với automated build process,
so that I can consistently package Python code into standalone Windows executable.

**Acceptance Criteria**:
1. Git repository initialized với proper .gitignore for Python projects
2. PyInstaller configured to create single-file executable từ existing Python codebase
3. Build script automates executable creation với consistent naming và metadata
4. Generated executable runs on clean Windows system without Python installation
5. Build artifacts are organized in dedicated output directory
6. Version information embedded in executable properties

## Story 1.2: Core UI Framework Migration
As a developer,
I want to refactor existing Tkinter interface into clean desktop application structure,
so that users have intuitive folder selection và file list display functionality.

**Acceptance Criteria**:
1. Main application window displays với proper title và icon
2. Folder browsing dialog allows user to select target directory
3. Selected folder path displayed in UI với clear indication
4. File list shows all files in selected folder với original names
5. Basic application menu và exit functionality implemented
6. Window resizing và basic layout management working properly
7. Application handles folder access permissions gracefully

## Story 1.3: Vietnamese Text Normalization Engine
As a user,
I want the application to apply Vietnamese text normalization rules to file names,
so that I can standardize file names for better searchability và system compatibility.

**Acceptance Criteria**:
1. Normalization function removes Vietnamese diacritics (ủ → u, đ → d, etc.)
2. All text converted to lowercase
3. Special characters (!@#$%^&*) removed hoặc replaced with safe alternatives
4. Multiple consecutive spaces collapsed to single space
5. Leading và trailing whitespace trimmed
6. File extensions preserved unchanged
7. Function handles edge cases: empty strings, numbers, mixed languages
8. Original normalization logic from Python script preserved và tested

## Story 1.4: Basic Batch Rename Execution
As a user,
I want to execute batch rename operations on selected folder,
so that I can apply Vietnamese normalization to multiple files simultaneously.

**Acceptance Criteria**:
1. "Rename Files" button triggers batch operation on all files in selected folder
2. Each file renamed according to Vietnamese normalization rules
3. File extensions preserved during rename process
4. Operation handles files that would result in duplicate names
5. Basic success/failure messaging displayed to user
6. Application remains responsive during rename operation
7. File system errors handled với appropriate user feedback
8. Operation completes successfully for typical use cases (50-100 files)

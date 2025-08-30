# Technical Assumptions

## Repository Structure: Monorepo
Single repository containing all components: UI code, business logic, build scripts, và documentation. Simple structure appropriate for single-developer utility application.

## Service Architecture
Monolithic desktop application với modular internal structure. Clear separation between UI layer (Tkinter), business logic (file operations), và data layer (settings/logging). No external services hoặc network dependencies required.

## Testing Requirements
Unit testing for core file operation logic và Vietnamese normalization functions. Manual testing for UI workflows và edge cases. Integration testing for full rename workflows với various file types và edge cases.

## Additional Technical Assumptions and Requests
- **Packaging**: Use PyInstaller để create standalone executable từ Python codebase
- **Error Handling**: Comprehensive logging to local files cho debugging và support
- **Configuration**: INI hoặc JSON file cho user preferences và application settings
- **Backward Compatibility**: Support Windows 10 và newer, focus on 64-bit systems
- **Code Reuse**: Leverage existing Python file operation logic với minimal modifications

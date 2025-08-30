# Requirements

## Functional Requirements
1. **FR1**: User can browse và select target folder containing files to rename
2. **FR2**: System displays preview list showing original names và proposed new names before applying changes
3. **FR3**: System applies Vietnamese text normalization rules: remove diacritics, convert to lowercase, remove special characters, trim excess spaces
4. **FR4**: User can execute batch rename operation on selected files với progress indication
5. **FR5**: System provides basic undo functionality to restore original file names nếu operation unsatisfactory
6. **FR6**: System handles file operation errors gracefully với clear error messaging và partial rollback capability
7. **FR7**: User can cancel rename operation in progress without corrupting file system
8. **FR8**: System logs all rename operations cho audit trail và debugging purposes

## Non-Functional Requirements
1. **NFR1**: Application startup time must be under 2 seconds on Windows 10/11
2. **NFR2**: System can process 1000+ files trong single batch operation without performance degradation
3. **NFR3**: Application file size should remain under 50MB cho easy distribution
4. **NFR4**: All file operations must be atomic - no partial renames that leave system in inconsistent state
5. **NFR5**: Application must run without requiring Python installation hoặc additional dependencies
6. **NFR6**: UI must be responsive and provide feedback during long-running operations
7. **NFR7**: Application must handle Windows file system permissions gracefully

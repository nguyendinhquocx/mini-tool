# Epic 3: Advanced Features & Polish

**Goal**: Add professional polish với drag-and-drop support, user preferences, performance optimizations, và distribution preparation to create market-ready application suitable for daily use.

## Story 3.1: Drag-and-Drop Folder Support
As a user,
I want to drag folders directly into the application,
so that I can quickly initiate rename operations without using browse dialogs.

**Acceptance Criteria**:
1. Application window accepts folder drops from Windows Explorer
2. Dropped folder automatically becomes selected target directory
3. File list updates immediately upon successful folder drop
4. Visual feedback during drag-over indicates valid drop target
5. Invalid drops (files instead of folders) provide clear feedback
6. Multiple folder drops handled gracefully (use most recent)
7. Drag-and-drop works consistently across different Windows versions
8. Feature integrates seamlessly với existing folder browse functionality

## Story 3.2: User Preferences & Settings
As a user,
I want to customize normalization rules và application behavior,
so that I can tailor the tool to my specific workflow needs.

**Acceptance Criteria**:
1. Settings dialog accessible through main menu hoặc button
2. User can enable/disable specific normalization rules (diacritics, case, special chars)
3. Custom replacement rules for specific characters hoặc patterns
4. Application remembers window size và position between sessions
5. Recent folders list for quick access to commonly used directories
6. Settings persist to configuration file in user profile directory
7. "Reset to Defaults" functionality available for all preferences
8. Settings changes apply immediately without requiring application restart

## Story 3.3: Performance Optimization & Large File Handling
As a user,
I want the application to handle large directories efficiently,
so that I can process thousands of files without performance degradation.

**Acceptance Criteria**:
1. File list populates progressively for directories với 1000+ files
2. Preview generation optimized to handle large file counts quickly
3. Memory usage remains stable during large batch operations
4. Background processing doesn't block UI interactions
5. File system monitoring detects external changes to selected directory
6. Application startup time remains under 2 seconds regardless of last used folder size
7. Batch operations provide estimated completion times for large operations
8. System resource usage optimized for sustained operation

## Story 3.4: Distribution Preparation & Final Polish
As a user,
I want a polished, professional application experience,
so that I can confidently use this as my daily file management utility.

**Acceptance Criteria**:
1. Application icon designed và embedded in executable
2. Proper Windows metadata (version, description, copyright) in executable properties
3. About dialog displays version information và basic usage instructions
4. Application handles Windows security warnings gracefully
5. Installer package created for easy distribution (optional vs standalone .exe)
6. Desktop shortcut creation during installation hoặc first run
7. Application associates với Windows search và Start menu properly
8. Basic help documentation available through Help menu hoặc F1 key
9. Application uninstalls cleanly leaving no orphaned files hoặc registry entries

# Project Brief: File Rename Tool

## Executive Summary

**File Rename Tool** là ứng dụng desktop Windows nhẹ, khởi động nhanh giúp người dùng đổi tên file và thư mục hàng loạt một cách hiệu quả. Ứng dụng giải quyết vấn đề phải mở IDE và chạy script Python mỗi lần cần sử dụng, thay vào đó trở thành ứng dụng độc lập có thể tìm kiếm và chạy như các phần mềm thông thường. Target user là các professional cần tổ chức và chuẩn hóa tên file/thư mục trong công việc hàng ngày. Key value proposition là khả năng chuẩn hóa tên file theo rules Việt Nam (loại bỏ dấu, ký tự đặc biệt, chuyển thường, xóa khoảng trắng thừa) với giao diện thân thiện và workflow linh hoạt.

## Problem Statement

### Current State và Pain Points:
- **Workflow không tối ưu**: Mỗi lần cần đổi tên file phải mở VSCode → navigate to script → run Python command, tốn 2-3 phút cho task 30 giây
- **Context switching cost**: Phải rời khỏi công việc hiện tại, mở development environment chỉ để chạy utility tool
- **Không accessible**: Script Python không thể tìm kiếm được như app thông thường, phải nhớ đường dẫn file
- **Dependency hell**: Cần Python environment setup, có thể conflict hoặc break khi update system

### Impact of the Problem:
- **Time waste**: Ước tính mất 2-3 phút mỗi lần vs 30 giây nếu là standalone app
- **Friction tăng**: High barrier to entry khiến skip việc organize files, dẫn đến messy file system theo thời gian  
- **Productivity loss**: Context switching làm gián đoạn deep work flow
- **Scalability issue**: Không thể share tool với team members dễ dàng

### Why Existing Solutions Fall Short:
- **Built-in Windows tools**: Chỉ rename từng file, không batch processing, không có rules chuẩn hóa tiếng Việt
- **Third-party tools**: Thường bloated với features không cần, không customize được rules cụ thể cho tiếng Việt
- **Command line tools**: Require technical knowledge, không friendly với non-dev users

## Proposed Solution

**File Rename Tool** sẽ là standalone Windows desktop application được package từ Python codebase hiện tại thành executable file (.exe). Solution approach là "evolutionary upgrade" thay vì rebuild - giữ lại proven business logic, enhance deployment method và user experience.

### Key Differentiators:
- **Vietnamese-optimized**: Built-in rules chuẩn hóa tiếng Việt (bỏ dấu, loại ký tự đặc biệt, lowercase, trim spaces)
- **Zero-installation friction**: Single .exe file, double-click to run, không cần Python environment
- **Workflow-integrated**: Có thể pin to taskbar, search từ Start menu, integrate vào daily workflow natural
- **Batch processing intelligence**: Hỗ trợ cả simple rules và advanced mapping file Excel cho complex scenarios
- **Preview-first approach**: Show preview trước khi apply changes, reduce risk của accidental renames

### High-level Vision:
Desktop utility với clean, intuitive interface cho phép users: Quick rename với drag folder → apply Vietnamese normalization rules → preview → confirm; Advanced mapping với Import/export Excel templates; Batch operations handle hundreds of files efficiently với progress indication; Undo/history safety net cho accidental changes.

## Target Users

### Primary User Segment: Knowledge Workers & Content Creators
- **Demographic**: Professionals 25-45 tuổi, làm việc với nhiều digital files hàng ngày
- **Current behaviors**: Thường xuyên download, organize và share files; sử dụng multiple devices và cloud storage
- **Specific needs**: Cần file naming consistency để dễ search và organize; làm việc với file tiếng Việt có dấu gây khó khăn cho systems
- **Goals**: Tăng productivity trong file management; giảm time spent on repetitive tasks; maintain organized file structure

### Secondary User Segment: Small Team Leaders & Project Managers
- **Demographic**: Team leads, project managers quản lý shared folders và documents
- **Current behaviors**: Phải standardize naming conventions across team members; thường cleanup và reorganize shared folders
- **Specific needs**: Enforce naming standards; batch process files từ multiple sources; maintain audit trail của changes
- **Goals**: Team efficiency improvements; consistent file organization; reduced confusion trong shared workspaces

## Goals & Success Metrics

### Business Objectives:
- **Productivity gain**: Giảm 80% time spent on file renaming tasks (từ 2-3 phút xuống 30 giây)
- **Adoption rate**: Achieve daily active usage trong 2 tuần đầu sau install
- **User satisfaction**: 90%+ users rate experience as "significantly better" than previous method
- **Foundation establishment**: Stable platform cho future mini-tool expansion

### User Success Metrics:
- **Task completion time**: Average rename operation < 1 minute
- **Error reduction**: 95% reduction trong accidental file name corruption
- **Workflow integration**: Users keep app pinned to taskbar và use 3+ times per week
- **Learning curve**: New users complete first successful batch rename trong 5 phút

### Key Performance Indicators (KPIs):
- **Usage frequency**: Daily/weekly active sessions per user
- **Batch size efficiency**: Average files processed per session
- **Error rate**: Percentage of operations requiring undo/correction
- **Feature adoption**: Usage distribution across simple vs advanced features

## MVP Scope

### Core Features (Must Have):
- **Vietnamese text normalization**: Automatic removal của dấu, special characters, convert to lowercase, trim excess spaces
- **Folder scanning**: Browse và select target folder, display file list with preview của renamed versions
- **Batch rename execution**: Apply changes to selected files với progress indication và error handling
- **Preview mode**: Show before/after names trước khi commit changes để avoid mistakes
- **Basic undo**: Restore original names nếu user không satisfied với results

### Out of Scope for MVP:
- Advanced mapping file support (Excel import/export)
- Multiple folder processing simultaneously
- Custom rule creation/editing
- Integration với cloud storage services
- Scheduled/automated operations
- Multi-language support beyond Vietnamese

### MVP Success Criteria:
User có thể successfully select folder, preview rename results, và execute batch rename operation trong một workflow session mà không cần external documentation hoặc support.

## Post-MVP Vision

### Phase 2 Features:
- **Advanced mapping**: Excel file import/export cho complex rename scenarios
- **Custom rules engine**: User-defined transformation rules beyond Vietnamese normalization
- **Multiple folder support**: Process several directories trong single operation
- **Integration hooks**: Context menu integration, drag-and-drop support

### Long-term Vision:
Trở thành comprehensive mini-tool suite cho Windows productivity: file operations, image processing, text utilities, và other workflow automation tools với consistent UI/UX paradigm.

### Expansion Opportunities:
- **File operations suite**: Copy, move, duplicate detection, size analysis
- **Image processing tools**: Batch resize, format conversion, compression
- **Text utilities**: Batch text processing, encoding conversion, content search/replace
- **Cloud integration**: Direct integration với Google Drive, OneDrive, Dropbox

## Technical Considerations

### Platform Requirements:
- **Target Platforms**: Windows 10/11 (64-bit primary)
- **Browser/OS Support**: Native Windows desktop application, no browser dependencies
- **Performance Requirements**: < 2 second startup time, handle 1000+ files trong single batch operation

### Technology Preferences:
- **Frontend**: Python + Tkinter (leverage existing codebase)
- **Backend**: Python file system operations với error handling và logging
- **Database**: SQLite cho settings và operation history (optional for MVP)
- **Hosting/Infrastructure**: Local desktop application, no server dependencies

### Architecture Considerations:
- **Repository Structure**: Single repository với clear separation của UI, business logic, và file operations
- **Service Architecture**: Monolithic desktop app với modular internal structure
- **Integration Requirements**: Windows shell integration cho context menus (post-MVP)
- **Security/Compliance**: Safe file operations với backup/undo capabilities, no data collection

## Constraints & Assumptions

### Constraints:
- **Budget**: Personal project, minimize external costs
- **Timeline**: Target 2-4 weeks cho MVP development và packaging
- **Resources**: Single developer (part-time development)
- **Technical**: Python-based solution để leverage existing code

### Key Assumptions:
- Users prefer familiar workflow với enhanced accessibility over learning completely new tool
- Performance của packaged Python app acceptable cho file operations use case
- Vietnamese text normalization rules cover 90%+ của real-world use cases
- Single .exe distribution method preferred over installer package
- Windows-only focus acceptable for initial release

## Risks & Open Questions

### Key Risks:
- **Performance risk**: Packaged Python executable có thể có slower startup time hoặc larger file size than expected
- **Compatibility risk**: Windows Defender hoặc other security software có thể flag unknown executable
- **User adoption risk**: Users might resist changing từ familiar script-based workflow

### Open Questions:
- What is acceptable file size cho packaged executable? (under 50MB preferred)
- How to handle Windows security warnings for unsigned executable?
- Should include auto-update mechanism trong MVP or defer to later?
- What level của logging và error reporting appropriate cho desktop utility?

### Areas Needing Further Research:
- PyInstaller vs other packaging options (cx_Freeze, Nuitka) performance comparison
- Distribution strategy: direct download vs Microsoft Store vs other channels
- User onboarding approach: embedded tutorial vs external documentation
- Backup/recovery strategy cho accidental bulk renames

## Next Steps

### Immediate Actions:
1. **Technical spike**: Test PyInstaller packaging với current Python codebase để validate performance assumptions
2. **UI/UX design**: Create wireframes cho enhanced desktop interface based on existing Tkinter layout
3. **Feature prioritization**: Refine MVP scope based on technical constraints discovered trong spike
4. **Development environment setup**: Establish build pipeline cho consistent executable generation

### PM Handoff:
This Project Brief provides the full context for **File Rename Tool**. Please start in 'PRD Generation Mode', review the brief thoroughly to work with the user to create the PRD section by section as the template indicates, asking for any necessary clarification or suggesting improvements.
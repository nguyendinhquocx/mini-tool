# Expert Auto-Completion Configuration

## Auto-Complete Source
Expert files from: `.expert/*.md`

## Completion Behavior
- **Trigger**: When typing `/expert "`
- **Source**: All `.md` files in `.expert/` directory  
- **Matching**: Case-insensitive, partial filename matching
- **Display**: Show available expert filenames as suggestions

## Expert Files Available (Auto-Updated)
This list is dynamically generated from the `.expert/` directory:

### Design & UX Experts
- Chuyên gia thiết kế toàn cục.md
- Chuyên gia thiết kế.md
- Chuyên gia thiết kế tối giản.md
- Chuyên gia UX.md
- Chuyên gia huyền thoại tư vấn thiết kế.md

### Technical Specialists  
- Chuyên gia bảo mật.md
- Chuyên gia chuẩn code.md
- Chuyên gia tối ưu.md
- Chuyên gia DevOps.md
- Chuyên gia Quality.md

### Platform Experts
- Chuyên gia Android.md
- Chuyên gia React.md
- Chuyên gia Frontend.md
- Chuyên gia Mobile.md
- Chuyên gia Web.md

### Automation & Tools
- Chuyên gia Automation.md
- Chuyên gia Excel.md
- Chuyên gia Apps script.md
- Chuyên gia tự động hoá.md

### Strategic Advisors
- Chuyên gia kiến trúc sư chiến lược.md
- Chuyên gia quản lí dự án.md
- Chuyên gia Data Analyst.md
- Chuyên gia AI.md

## Usage Examples
```bash
# Start typing and get suggestions:
/expert "Chuyên<TAB>
/expert "thiết<TAB>  
/expert "bảo<TAB>

# Full command examples:
/expert "Chuyên gia thiết kế toàn cục.md"
/expert "Chuyên gia bảo mật.md"
/expert "Chuyên gia tối ưu.md"
```

## Implementation Notes
- Auto-completion is provided by Claude Code's command system
- Expert filenames are read dynamically from `.expert/` directory
- No manual maintenance required - auto-updates when new experts are added
- Supports fuzzy matching for easier discovery
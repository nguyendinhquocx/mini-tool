# /expert Command

When this command is used, execute expert consultation workflow:

# expert

## Description
Consult with specialized experts from .expert directory for advanced guidance and expert-level reviews

## Parameters
- **expert_file**: Expert filename (required) - Auto-completed from .expert/*.md files  
- **question**: Optional immediate question for quick consultation

## Command Format
```bash
/expert "[expert-filename]" "[optional-question]"
```

## Auto-completion Configuration
Expert files are dynamically loaded from `.expert/` directory for auto-completion suggestions.

## Usage

### Quick Consultation (Recommended)
```bash
/expert "Chuyên gia thiết kế toàn cục.md" "Review TodoFlow design direction"
```

### Interactive Session  
```bash
/expert "Chuyên gia bảo mật.md"
```

### Auto-completion Support
Expert filenames are auto-completed from `.expert/` directory:
- Type `/expert "` and use TAB for suggestions
- Supports partial matching (e.g., "thiết" matches design experts)
- Case-insensitive search

## Expert Categories

### Strategic Advisors
- **Chuyên gia thiết kế toàn cục.md** - Design philosophy & direction
- **Chuyên gia kiến trúc sư chiến lược.md** - Technical architecture strategy  
- **Chuyên gia quản lí dự án.md** - Project management excellence

### Technical Specialists  
- **Chuyên gia bảo mật.md** - Security architecture & audits
- **Chuyên gia chuẩn code.md** - Code quality & standards
- **Chuyên gia tối ưu.md** - Performance optimization
- **Chuyên gia DevOps.md** - Infrastructure & deployment

### Platform Experts
- **Chuyên gia React.md** - React ecosystem specialist
- **Chuyên gia Android.md** - Android development
- **Chuyên gia Frontend.md** - Frontend architecture
- **Chuyên gia UX.md** - User experience design

### Automation & Tools
- **Chuyên gia Automation.md** - Automation strategy
- **Chuyên gia Excel.md** - Excel automation & analysis
- **Chuyên gia Apps script.md** - Google Apps Script

### Domain Specialists
- **Chuyên gia y tế.md** - Healthcare systems
- **Chuyên gia AI.md** - Artificial Intelligence integration
- **Chuyên gia Data Analyst.md** - Data analysis & insights

## Integration with BMad

### Context Preservation
- Current BMad agent context is automatically preserved
- Quick consultations auto-return to previous context
- Interactive sessions require manual exit with `/exit`

### Documentation
All consultations are automatically logged to:
```
docs/consultations/YYYY-MM-DD-[expert-name]-[session-id].md
```

### Workflow Integration
Expert recommendations can be integrated into BMad workflow:
- New stories for /sm to create
- Architecture updates for /architect  
- Code improvements for /dev
- Quality standards for /qa

## Examples

### Design Review (Post-Epic)
```bash
/expert "Chuyên gia thiết kế toàn cục.md" "Review TodoFlow design consistency after Epic 1 completion"
```

### Security Audit (During Development)
```bash
/expert "Chuyên gia bảo mật.md" "Audit JWT authentication implementation for vulnerabilities"
```

### Performance Optimization
```bash
/expert "Chuyên gia tối ưu.md" "Analyze TodoFlow performance bottlenecks and optimization strategy"
```

### Interactive Technical Deep Dive
```bash
/expert "Chuyên gia React.md"
# Enter interactive mode for detailed discussion
# Use /exit to return to BMad workflow
```

## Best Practices

1. **Use quick consultations** for specific questions
2. **Interactive sessions** for complex problem solving
3. **Strategic experts** for major decisions and milestone reviews
4. **Technical experts** for implementation guidance and quality assurance
5. **Document insights** are auto-saved for future reference

## Notes
- Compatible with all 85+ experts in .expert directory
- Non-intrusive to BMad core workflow
- Expert responses adapt to loaded expert's style and expertise
- Safe to use - does not modify BMad core files
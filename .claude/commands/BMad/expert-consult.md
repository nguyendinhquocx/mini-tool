# Expert Consultation System

## Command
expert

## Description
Consult with specialized experts from .expert directory for advanced guidance and reviews

## Usage Patterns

### Quick Consultation (Recommended)
```bash
/expert "Chuyên gia thiết kế toàn cục.md" "Question or request here"
```
**Response:** Expert analysis + automatic return to previous BMad context

### Interactive Session
```bash
/expert "Chuyên gia thiết kế toàn cục.md"
```
**Response:** Enter interactive consultation mode
**Exit:** Type `/exit` or `/return` to go back to BMad workflow

## Expert Discovery
- All expert files are located in `.expert/` directory
- Use tab completion for expert filename suggestions
- Expert files contain specialized knowledge and unique perspectives

## Auto-Documentation
All consultations are automatically logged to:
```
docs/consultations/YYYY-MM-DD-[expert-name]-[session-id].md
```

## Integration with BMad
- **Context Preservation**: Your current BMad agent context is preserved
- **Non-Intrusive**: Does not affect core BMad workflow
- **Action Items**: Expert recommendations can be integrated into current stories
- **Follow-up**: Consultation insights feed back into planning and development

## Examples

### Design Review
```bash
/expert "Chuyên gia thiết kế toàn cục.md" "Review TodoFlow UI after Epic 1 completion"
```

### Security Audit
```bash
/expert "Chuyên gia bảo mật.md" "Audit authentication implementation for vulnerabilities"
```

### Performance Optimization
```bash
/expert "Chuyên gia tối ưu.md" "Analyze current app performance bottlenecks"
```

### Code Quality Review
```bash
/expert "Chuyên gia chuẩn code.md" "Review React component structure for maintainability"
```

## Expert Categories Available

Based on current .expert directory:
- **Strategic Advisors**: Design philosophy, business intelligence, architecture strategy
- **Technical Specialists**: Security, performance, code standards, DevOps
- **Platform Experts**: Android, React, Cloud, Excel, automation tools
- **Domain Specialists**: Healthcare, data analysis, specific industries
- **Workflow Optimizers**: Automation, testing, project management

## Safety & Rollback
- **Non-destructive**: Does not modify existing BMad files
- **Optional**: Can be disabled by removing this command file
- **Isolated**: Expert consultations are separate from core workflow

## Implementation Notes
- Expert consultation responses adapt to the loaded expert's style and expertise
- Consultation context includes current BMad project state
- Expert recommendations can generate action items for BMad agents
- Full consultation history is maintained for project continuity
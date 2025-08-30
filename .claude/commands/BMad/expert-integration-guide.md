# Expert Consultation Integration Guide

## Integration với BMad Workflow

### Quick Reference: Khi nào gọi Expert
```bash
# Trong Development Flow:
/dev → /expert "Chuyên gia chuẩn code.md" "Review component structure" → /dev

# Trong QA Review:  
/qa → /expert "Chuyên gia tối ưu.md" "Performance recommendations" → /qa

# Sau Epic completion:
/po → /expert "Chuyên gia thiết kế toàn cục.md" "Strategic review" → /po
```

## Consultation Points trong BMad Method

### **Phase 1: Planning**
- **Post-Analyst**: Expert brainstorming cho complex domains
- **Post-PM**: Strategic consultation cho PRD validation
- **Post-UX**: Design philosophy review và refinement
- **Post-Architect**: Technical architecture validation

### **Phase 2: Development** 
- **Pre-Development**: Code standards và pattern establishment
- **During Development**: Quick technical consultations
- **Post-Development**: Quality review và optimization
- **Pre-QA**: Performance và security pre-checks

### **Phase 3: Epic Completion**
- **Design Review**: Overall aesthetic và UX validation
- **Security Audit**: Comprehensive security assessment
- **Performance Analysis**: Scalability và optimization review
- **Strategic Planning**: Next epic direction setting

## Expert Categories for BMad Integration

### **Strategic Consultants** (Milestone Reviews)
- Chuyên gia thiết kế toàn cục.md → Overall design direction
- Chuyên gia kiến trúc sư chiến lược.md → Architecture decisions
- Chuyên gia quản lí dự án.md → Project strategy alignment

### **Technical Specialists** (Development Support)
- Chuyên gia bảo mật.md → Security implementation
- Chuyên gia chuẩn code.md → Code quality standards
- Chuyên gia tối ưu.md → Performance optimization
- Chuyên gia DevOps.md → Deployment và infrastructure

### **Platform Experts** (Technology-Specific)
- Chuyên gia React.md → Frontend architecture
- Chuyên gia Android.md → Mobile development
- Chuyên gia Excel.md → Data processing features

## Context Preservation Rules

### **Auto-Return Behavior**
```bash
# Single question consultations auto-return:
Current Agent: /dev
↓
/expert "..." "question"
↓ 
Expert Response
↓
Auto-return to: /dev (context preserved)
```

### **Interactive Session Management**
```bash
# Interactive sessions require manual exit:
Current Agent: /sm
↓
/expert "..." (no question = interactive mode)
↓
Multi-turn conversation
↓
User types: /exit
↓
Return to: /sm (context preserved)
```

## Action Item Integration

### **From Expert to BMad Agents**
```bash
# Expert recommendations become:
1. New stories for /sm to create
2. Architecture updates for /architect
3. Code refactoring tasks for /dev
4. Design refinements for /ux-expert
5. Quality checks for /qa
```

### **Documentation Flow**
```bash
Expert Consultation
↓
Auto-saved to docs/consultations/
↓
Action items extracted
↓
Integrated into BMad workflow:
- Update PRD
- Create follow-up stories  
- Modify architecture docs
- Schedule reviews
```

## Workflow Examples

### **Example 1: Epic 1 Completion Review**
```bash
# Complete Epic 1
/qa
*review final-story
*exit

# Strategic consultation
/expert "Chuyên gia thiết kế toàn cục.md" "Review Epic 1 outcomes, guide Epic 2 direction"

# Auto-return to planning
/po
*execute-checklist-po
```

### **Example 2: Security Implementation**
```bash
# During authentication development
/dev
*develop-story auth-system

# Quick security check
/expert "Chuyên gia bảo mật.md" "Validate JWT implementation approach"

# Continue development with expert recommendations
/dev
*implement-security-improvements
```

### **Example 3: Performance Optimization**
```bash
# After feature completion
/qa
*review performance

# Expert consultation
/expert "Chuyên gia tối ưu.md"
> Interactive session for detailed performance analysis

# Apply optimizations
/dev
*implement-performance-improvements
```

## Integration Best Practices

### **Consultation Timing**
- **Early**: Architectural và design decisions
- **During**: Quick technical validations
- **Late**: Quality assurance và optimization

### **Expert Selection**
- **Strategic decisions**: Design philosophy, architecture strategy
- **Technical implementation**: Code standards, security, performance
- **Platform specific**: React, Android, specific technologies

### **Documentation Integration**
- Expert insights automatically logged
- Action items tracked in BMad workflow
- Consultation history available for future reference

## Safety Measures

### **Non-Intrusive Design**
- Expert consultation never modifies BMad core files
- Consultations are additive to existing workflow
- Can be disabled by removing expert-consult.md

### **Context Safety**
- Current BMad agent context always preserved
- Auto-return behavior prevents context loss
- Manual exit required for long consultations

### **Data Safety**
- All consultations logged for audit trail
- No sensitive data exposed to experts
- Consultation logs can be reviewed và managed
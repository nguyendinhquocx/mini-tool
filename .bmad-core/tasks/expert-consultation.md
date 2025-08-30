# Expert Consultation Task

## Purpose
Tích hợp với hệ thống expert consultation để user có thể consult với domain experts từ bất kỳ BMad agent nào.

## Available Expert Domains
- **frontend**: Chuyên gia Frontend Development
- **android**: Chuyên gia Android Development  
- **react**: Chuyên gia React
- **nodejs**: Chuyên gia Node.js
- **python**: Chuyên gia Python
- **devops**: Chuyên gia DevOps
- **ai**: Chuyên gia AI
- **automation**: Chuyên gia Automation
- **excel**: Chuyên gia Excel
- **blockchain**: Chuyên gia Blockchain
- **cybersecurity**: Chuyên gia Cybersecurity

## Workflow Steps

### Step 1: Validate Expert Domain
- Kiểm tra domain parameter có trong available experts không
- Nếu không có, show list available experts
- Case-insensitive matching (frontend = Frontend = FRONTEND)

### Step 2: Load Expert Profile
- Load file từ `.expert/Chuyên gia {Domain}.md`
- Parse expert specialization và capabilities
- Prepare consultation context

### Step 3: Create Consultation Session
- Chuyển current conversation context sang expert
- Introduce expert với background và specialization
- Explain consultation format và available commands

### Step 4: Expert Introduction Response
```markdown
🤝 **Chuyển consultation sang Chuyên gia {Domain}**

Xin chào! Tôi là {Expert_Name} - {Expert_Title}

{Expert_Brief_Introduction}

**Chuyên môn của tôi:**
{List_Of_Specializations}

**Enhanced Commands Available:**
- `*save {filename}` - Lưu consultation session
- `*recommendations` - Đưa ra recommendations có cấu trúc  
- `*exit` - Quay về BMad workflow

**Context từ conversation trước:**
{Summary_Of_Previous_Discussion}

Bạn có vấn đề gì trong {domain} mà tôi có thể hỗ trợ?
```

### Step 5: Enable Expert Mode
- Set consultation context với expert identity
- Enable expert-specific commands
- Maintain conversation history cho recommendations

## Implementation Notes
- Always communicate in Vietnamese
- Preserve conversation context from BMad agent
- Expert files in `.expert/` directory follow naming pattern: `Chuyên gia {Domain}.md`
- Expert mode supports enhanced commands (*save, *recommendations, *exit)
- When user types *exit trong expert mode, return to original BMad agent context

## Error Handling
- Domain not found: List available experts
- Expert file missing: Graceful fallback với generic expert
- Invalid syntax: Show help và examples

## Example Usage
```
User: *expert frontend
Agent: [Loads Chuyên gia Frontend.md và introduces expert]

User: tôi muốn optimize performance cho React app
Expert: [Responds với frontend expertise]

User: *recommendations  
Expert: [Provides structured recommendations for React performance]

User: *save react-performance-optimization
Expert: [Saves consultation to docs/consultations/]

User: *exit
Agent: [Returns to original BMad agent context]
```
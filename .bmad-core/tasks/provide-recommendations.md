# Provide Recommendations Task

## Purpose
Phân tích ngữ cảnh consultation hiện tại và đưa ra các recommendations có cấu trúc, actionable dựa trên conversation history.

## Critical Instructions
- DO NOT use web search tools
- DO NOT call external APIs
- Work ONLY with current conversation context
- Focus on analyzing what has been discussed

## Workflow Steps

### Step 1: Context Analysis  
- Review conversation history in current session
- Extract main topics, technologies, challenges discussed
- Identify user's expertise level from questions and responses
- Note specific requirements or constraints mentioned

### Step 2: Generate Structured Recommendations

#### Immediate Actions (Next 24-48 hours)
- Quick wins có thể implement ngay lập tức
- Specific, actionable steps

#### Short-term Goals (Next 1-2 weeks)
- Strategic implementations
- Learning objectives
- Research tasks

#### Long-term Vision (Next 1-3 months)
- Architecture decisions
- Skill development path
- Technology roadmap

### Step 3: Personalized Guidance
Based on discussion context, provide:
- **Learning Resources**: Specific links, books, courses
- **Best Practices**: Industry standards và conventions
- **Tools & Libraries**: Recommended tech stack
- **Community Resources**: Forums, groups, experts to follow

### Step 4: Risk Assessment
- Potential pitfalls to avoid
- Common mistakes trong domain này
- Performance considerations
- Security implications

### Step 5: Success Metrics
- How to measure progress
- Key performance indicators
- Validation methods
- Testing strategies

## Output Format
```markdown
# 🎯 Recommendations Report

## Immediate Actions (Next 24-48h)
1. [Specific action with rationale]
2. [Another immediate step]

## Short-term Goals (1-2 weeks)
1. [Strategic implementation]
2. [Learning objective]

## Long-term Vision (1-3 months)
1. [Architecture decision]
2. [Advanced skill development]

## 📚 Learning Resources
- [Specific resource with why it's relevant]

## ⚠️ Potential Pitfalls
- [Risk with mitigation strategy]

## 📊 Success Metrics
- [How to measure progress]

## 🔄 Next Steps
[Clear call-to-action for user]
```

## Implementation Notes
- Always communicate in Vietnamese 
- Base recommendations ONLY on conversation context
- Do NOT search for external information
- Provide immediate, actionable steps
- Reference specific parts of previous conversation
- Include rationale based on discussed topics
- Keep recommendations focused and practical
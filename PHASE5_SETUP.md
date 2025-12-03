# Phase 5 Setup: Intelligence Layer Enhancements

Phase 5 improves the AI-powered intelligence layer with better extraction, smarter deduplication, and enhanced todo management.

## What Phase 5 Includes

### 1. Enhanced Deduplication
**Current**: Simple hash-based matching
**Enhanced**: Semantic similarity using embeddings

- Detect todos that mean the same thing but are worded differently
- Cross-source deduplication (same todo in Slack and Gmail)
- Fuzzy matching for near-duplicates
- Merge related todos into single items

### 2. Priority Scoring
**Current**: All todos have equal priority
**Enhanced**: AI-inferred priority based on signals

Priority signals to detect:
- Urgency words: "ASAP", "urgent", "critical", "today"
- Deadline proximity: Due dates within 24-48 hours
- Sender importance: Manager/executive vs peer
- Thread activity: Multiple follow-ups indicate importance
- Explicit priority markers: "P0", "high priority"

### 3. Due Date Inference
**Current**: Only explicit dates extracted
**Enhanced**: Contextual date inference

Patterns to detect:
- "by end of week" → Friday
- "next Monday" → Specific date
- "tomorrow" → Next day
- "within 2 days" → Date calculation
- "before the meeting" → Meeting date lookup

### 4. Todo Categorization
**Current**: No categorization
**Enhanced**: Auto-tagging by type

Categories:
- `follow-up` - Waiting on someone else
- `review` - Documents/PRs to review
- `meeting` - Schedule or attend meetings
- `finance` - Budget, invoices, expenses
- `hr` - Hiring, onboarding, team
- `technical` - Code, infrastructure, bugs
- `communication` - Emails, calls to make

### 5. Recurring Todo Detection
**Current**: Each mention creates new todo
**Enhanced**: Pattern recognition for recurring items

Features:
- Detect weekly/monthly patterns
- Link related recurring todos
- Track completion streaks
- Suggest automation opportunities

### 6. Completion Signal Enhancement
**Current**: Basic completion detection
**Enhanced**: Multi-signal completion confidence

Signals:
- "Done", "Completed", "Finished" in messages
- PRs merged (for code tasks)
- Meetings held (for scheduling tasks)
- Replies sent (for email tasks)
- Time elapsed without follow-up

## Implementation Approach

### Option A: Enhanced Prompts (Low Effort)
Improve Claude prompts to extract more structured data:

```python
ENHANCED_EXTRACTION_PROMPT = """
Extract todos with the following structure:
- task: What needs to be done
- assigned_to: Who should do it
- due_date: When it's due (infer from context)
- priority: high/medium/low based on urgency signals
- category: Type of task (follow-up, review, meeting, etc.)
- confidence: How certain you are (0-1)
- context: Why this is a todo
"""
```

### Option B: Embedding-Based Deduplication (Medium Effort)
Use embeddings for semantic similarity:

```python
from anthropic import Anthropic

def get_embedding(text: str) -> list[float]:
    # Use Claude or external embedding model
    pass

def semantic_similarity(todo1: dict, todo2: dict) -> float:
    emb1 = get_embedding(todo1["task"])
    emb2 = get_embedding(todo2["task"])
    return cosine_similarity(emb1, emb2)
```

### Option C: Two-Pass Processing (Higher Effort)
1. First pass: Extract raw todos
2. Second pass: Enrich with priority, category, links

## Suggested Implementation Order

### Quick Wins (Week 1)
1. **Enhanced extraction prompt** - Add priority and category fields
2. **Better date parsing** - Handle relative dates
3. **Improved filtering** - Better MY_NAME matching

### Medium Term (Week 2)
4. **Priority scoring** - Implement urgency detection
5. **Category tagging** - Auto-categorize todos
6. **Duplicate detection** - Fuzzy string matching

### Long Term (Week 3+)
7. **Embedding-based dedup** - Semantic similarity
8. **Recurring detection** - Pattern recognition
9. **Completion signals** - Multi-source verification

## Files to Modify

### `src/processors/claude_processor.py`
- Update extraction prompt with new fields
- Add priority scoring logic
- Implement category inference
- Enhanced deduplication algorithm

### `src/mcp_clients/notion_client.py`
- Add Priority property support
- Add Category/Tags property
- Update page creation with new fields

### `src/config.py`
- Add configuration for new features
- Feature flags for gradual rollout

### Notion Database Schema
Add new properties:
- Priority (Select: High/Medium/Low)
- Category (Multi-select)
- Recurring (Checkbox)
- Original Source (Text - for dedup tracking)

## Configuration Options

```bash
# Phase 5 Feature Flags
ENABLE_PRIORITY_SCORING=true
ENABLE_CATEGORY_TAGGING=true
ENABLE_SEMANTIC_DEDUP=false  # Requires embeddings
ENABLE_RECURRING_DETECTION=false

# Priority Thresholds
HIGH_PRIORITY_KEYWORDS=urgent,asap,critical,today,p0
PRIORITY_DUE_DATE_THRESHOLD_HOURS=48

# Category Keywords (optional overrides)
CATEGORY_FINANCE_KEYWORDS=invoice,budget,expense,payment
CATEGORY_HR_KEYWORDS=hire,onboard,interview,candidate
```

## Expected Outcomes

### Before Phase 5
```
- 30 todos extracted
- Some duplicates across sources
- No priority information
- Basic due date extraction
```

### After Phase 5
```
- 25 unique todos (5 duplicates merged)
- 8 high priority, 12 medium, 5 low
- Categories: 6 follow-up, 5 review, 4 meeting, 10 other
- 3 todos with inferred due dates
```

## Testing Plan

### Unit Tests
- Priority keyword detection
- Date parsing edge cases
- Category classification
- Similarity scoring

### Integration Tests
- End-to-end with real data
- Deduplication accuracy
- Priority distribution analysis

### Metrics to Track
- Duplicate detection rate
- Priority accuracy (manual validation)
- Category accuracy
- False positive/negative rates

## Cost Considerations

**Additional Claude API usage:**
- Priority/category extraction: +10-20% tokens
- Embedding-based dedup: Depends on model choice
- Two-pass processing: 2x extraction cost

**Estimated increase:** $1-3/month additional

## Next Steps After Phase 5

### Phase 6: Scheduling and Output
- Configurable run schedules
- Multiple output formats (Slack summary, email digest)
- Custom notification rules
- Dashboard/reporting

# FLIO API Reference

**Base URL**: `http://localhost:8000/api/v1`

All endpoints require `/api/v1/` prefix.

---

## Trust Score

```http
GET  /trust/score/{user_id}       # Detailed breakdown
GET  /trust/summary/{user_id}     # Simple summary
GET  /trust/upgrade-path/{user_id} # Upgrade recommendations
GET  /trust/tiers/info            # All tier information
POST /trust/recalculate/{user_id} # Force recalculation
POST /trust/behavior/log          # Log user behavior
```

## Questions

```http
GET    /questions/initial?user_id={id}&language=ko  # Get questions (dynamic count)
POST   /questions/answer                            # Save answer
GET    /questions/user/{user_id}/profile            # Get user's answers + progress
GET    /questions/stats                             # Question statistics
DELETE /questions/user/{user_id}/answer/{question_id}
```

## Verification

```http
POST   /verification/document/verify  # Upload document for OCR
GET    /verification/status/{user_id} # All verification statuses
GET    /verification/document/{doc_id}/status
DELETE /verification/document/{doc_id}
```

## Matching

```http
GET  /matching/matches/{user_id}?limit=10&min_score=0.5
POST /matching/profile/create-embedding
```

**Hybrid Matching Algorithm**:
- 60% Static Question Matching (concrete answer alignment)
- 20% Importance/Dealbreaker Bonus (critical preferences)
- 20% Azure OpenAI Embedding Similarity (semantic understanding)

---

## Key Integration Points

### Dynamic Question Count
Questions are retrieved dynamically from database. No hardcoded counts.

```typescript
// Mobile fetches count from stats
const stats = await fetch('/api/v1/questions/stats');
```

### Photo Verification Required
Matching requires photo verification:

```typescript
const canMatch = await supabase.rpc('can_user_access_matches', { p_user_id });
```

### Trust Score Tiers (Ocean Pearl Theme)
- 💎 Diamond (80-100%): 30 matches/day, ₩59,900/mo
- 🪸 Coral (60-79%): 20 matches/day, ₩39,900/mo
- 🦪 Pearl (40-59%): 15 matches/day, ₩19,900/mo
- 🐚 Shell (20-39%): 10 matches/day, ₩9,900/mo
- 🪨 Pebble (0-19%): 5 matches/day, Free

---

For database schema, see `DATABASE.md`.

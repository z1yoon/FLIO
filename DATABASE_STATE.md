# Database State Summary
**Last Updated:** 2026-01-10

## Migration Files Status

### Active Migrations (Applied to Database)
1. ✅ `001_initial_schema.sql` - Base schema (profiles, user_profiles, etc.)
2. ✅ `002_upgrade_embeddings.sql` - Vector embeddings upgrade
3. ✅ `004_questions_database.sql` - 44 questions (4 dealbreakers + 40 regular)
4. ✅ `005_ai_backend_functions.sql` - Database functions
5. ✅ `006_user_answers_table.sql` - User answers table
6. ✅ `007_reshuffle_feedback.sql` - Reshuffle feedback system
7. ✅ `008_preference_analysis_cache.sql` - AI preference caching
8. ✅ MCP Migration: `update_dealbreaker_questions_to_3_core` (2026-01-10)

### Missing Migration File (003)
- No `003_*.sql` file exists (skipped number)

## Current Database Tables
```
answer_history
matches
meeting_feedback
messages
preference_analysis_cache
profiles
question_performance
questions (44 total)
reshuffle_feedback
reshuffle_history
user_answers
user_feedback
user_profiles
verifications
```

## Questions Breakdown

### Total: 44 Questions
- **4 Dealbreaker Questions** (hard filters - must match)
- **39 Choice Questions** (importance ratings 1-5)
- **5 Text Questions** (open-ended for embeddings)

### 4 Dealbreaker Questions (can_be_dealbreaker = true)
1. `age_range_preference` - 선호하는 상대방의 나이 범위는?
2. `disability_acceptance` - 신체적 차이가 있는 분과의 연애에 대해 어떻게 생각하시나요?
3. `divorce_status` - 상대방의 이혼 경험에 대해 어떻게 생각하시나요?
4. `gender_preference` - 어떤 성별의 분을 만나고 싶으세요?

### 5 Text Questions (for embeddings)
1. `conflict_growth_philosophy` - 관계에서 어려움이나 갈등이 생겼을 때, 어떻게 극복하고 성장해왔나요?
2. `future_life_vision` - 5년 후, 10년 후 당신의 삶은 어떤 모습일까요?
3. `ideal_relationship_dynamic` - 이상적인 연애 관계는 어떤 모습이라고 생각하시나요?
4. `life_philosophy_happiness` - 당신에게 행복한 삶이란 무엇이며, 어떤 순간에 가장 만족감을 느끼시나요?
5. `personal_values_lifestyle` - 당신의 일상과 삶에서 가장 중요하게 생각하는 가치는 무엇이며, 어떻게 실천하고 계신가요?

### 39 Choice Questions (importance ratings)
All other questions including:
- marriage_timeline, children_plan, conflict_resolution, trust_jealousy
- emotional_support, communication_frequency, attachment_style, love_language
- date_frequency, anniversary_importance, future_planning, personal_space
- social_life_balance, physical_affection, parents_relationship, holiday_obligations
- financial_transparency, career_priority, household_division, religion_spirituality
- political_views, environmental_values, life_goals, money_attitude
- living_location, pet_preference, exercise_habits, drinking_habits
- smoking_status, travel_preference, food_preference, sleep_schedule
- cleanliness, introvert_extrovert, sexual_orientation

## Matching Algorithm

### Score Breakdown (60/20/20)
- **60%** - Static exact matching (39 choice questions)
- **20%** - Importance bonus (questions marked 4-5 stars)
- **20%** - Embedding similarity (5 text questions only)

### Matching Flow
1. **Hard Filter:** Check 4 dealbreaker questions (pass/fail)
2. **Vector Search:** Find similar profiles using embeddings (5 text questions)
3. **Calculate Score:** Apply 60/20/20 algorithm
4. **Filter:** Minimum 50% exact match rate required
5. **Return:** Top matches sorted by total score

## Embedding Architecture

### What Gets Embedded
- **ONLY** the 5 text questions (Q36-40)
- Static choice questions are NOT embedded
- Embeddings are pre-computed once per user

### Embedding Process
1. User answers 5 text questions
2. Build Korean narrative from text answers
3. Translate to English (cost optimization)
4. Generate embedding via Azure OpenAI (text-embedding-3-small)
5. Store in `profiles.profile_embedding` (vector 1024)

### Vector Search
- Uses Supabase pgvector extension
- RPC function: `find_similar_profiles()`
- Excludes rejected matches at database level
- Returns similarity score (cosine distance)

## Reshuffle System

### Tables
- `reshuffle_feedback` - Stores user preferences and rejected matches
- `preference_analysis_cache` - Caches AI analysis to reduce costs

### Flow
1. User clicks reshuffle with preference text
2. Store preference + rejected match IDs
3. Check cache for similar preference analysis
4. If not cached, analyze with Azure OpenAI GPT-4o-mini
5. Find matches excluding rejected IDs
6. Re-rank by preference match
7. Return new matches

## Azure OpenAI Usage

### Embedding Generation
- Model: `text-embedding-3-small`
- Dimension: 1024
- Cost: ~$0.00002 per 1K tokens
- When: Once per user when profile is created/updated

### Preference Analysis
- Model: `gpt-4o-mini`
- Cost: ~$0.00015 per 1K tokens
- When: On reshuffle (cached after first use)

### Match Explanation
- Model: `gpt-4o-mini`
- Cost: ~$0.00015 per 1K tokens
- When: On-demand when user clicks "Why we matched"

## Sync Status

### ✅ Synced
- Database has 44 questions
- 4 dealbreakers correctly set
- SQL file `004_questions_database.sql` matches database
- Backend code documentation matches system
- All migrations applied successfully

### ⚠️ Notes
- `sexual_orientation` exists in database but is NOT a dealbreaker (importance rating)
- Migration file 003 is missing (number skipped)
- Some MCP migrations don't have corresponding SQL files (applied programmatically)

## Recommendations

### Keep As-Is
- All 7 SQL migration files are in use
- All tables are actively used by the application
- Current architecture is clean and efficient

### Future Considerations
- Consider adding migration 003 placeholder or renaming 004→003
- Document MCP-only migrations in a separate file
- Add database backup/restore procedures

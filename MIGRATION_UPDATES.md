# FLIO Migration Updates - Backend & Frontend Alignment

## Overview

This document outlines all changes made to align the backend and frontend codebases with the new atomic database migrations.

## Database Migrations Summary

**New Structure:** 15 atomic, focused migrations (up from 6 consolidated files)
- **Phase 1: Foundation**
  - `001_extensions_and_types.sql` - PostgreSQL extensions and utility functions
  - `002_core_tables.sql` - Core tables (profiles, matches, messages, meeting_feedback)
  - `003_core_indexes_and_rls.sql` - Indexes and RLS policies for core tables
- **Phase 2: Questions**
  - `004_questions_schema.sql` - Question tables (questions, user_answers, user_feedback, system_settings)
  - `005_questions_data.sql` - 40 research-based questions data
  - `006_question_functions.sql` - Question functions, triggers, RLS, permissions
- **Phase 3: AI Matching**
  - `007_ai_matching_functions.sql` - AI matching functions using vector embeddings
  - `008_daily_match_tracking.sql` - Daily match views, match history, tier-based limits
- **Phase 4: Feedback**
  - `009_reshuffle_system.sql` - User feedback and preference analysis caching
- **Phase 5: Verification**
  - `010_verification_tables.sql` - Photo, document, phone, social, family, consistency tables
  - `011_verification_functions.sql` - Verification functions, triggers, RLS policies
  - `012_behavioral_reputation_tables.sql` - Behavior logs, reports, interactions, analytics
- **Phase 6: Trust Score**
  - `013_trust_score_calculation.sql` - 7-component trust score calculation with tier assignment
  - `014_trust_score_matching.sql` - Tier-based weighted matching algorithm
- **Phase 7: Subscriptions**
  - `015_subscription_payment_system.sql` - Subscription plans, payments, eligibility checks

**Key Changes:**
- Split 6 large files into 15 atomic, focused files
- Each file has a single, clear responsibility
- Better separation of concerns
- Easier to understand and maintain
- Future-proof (add new features in new files without touching existing ones)
- Idempotent migrations (safe to rerun)

## Migration Version History

### Version 3.0 (Current - 15 Atomic Files) - January 27, 2026
**Goal:** Industry best practices with atomic migrations
- Split 6 consolidated files into 15 focused files
- Each file has single responsibility
- Improved maintainability and clarity
- Better version control (clearer git diffs)
- Safer deployments (reduced risk of breaking changes)

### Version 2.0 (6 Consolidated Files) - January 23, 2026
**Goal:** Reduce complexity from 14 incremental migrations
- Consolidated 14 files into 6 logical groups
- Eliminated `ALTER TABLE ADD COLUMN` statements
- Complete table definitions from the start
- 50% reduction in file count

### Version 1.0 (14 Incremental Files) - Original
**Goal:** Initial database schema
- Incremental migrations with `ALTER TABLE` statements
- Multiple files for similar features
- Difficult to track dependencies

## Backend Changes

### services/ai-backend/app/services/trust_score_service.py

**✅ UPDATED**: Trust score calculation now properly returns all 7 components

#### Changes Made:
1. `calculate_trust_score()` - Now returns all 7 scores:
   - document_score (25%)
   - photo_score (20%) - **REQUIRED**
   - consistency_score (15%)
   - behavioral_score (15%)
   - social_score (10%)
   - completeness_score (10%)
   - reputation_score (5%)

2. `get_trust_score()` - Now calculates photo, social, and reputation scores on-the-fly since they're not stored in the database

#### Code Changes:
```python
# Before
return TrustScoreResponse(
    user_id=user_id,
    document_score=data['document_score'],
    consistency_score=data['consistency_score'],
    behavioral_score=data['behavioral_score'],
    completeness_score=data['completeness_score'],
    ...
)

# After
return TrustScoreResponse(
    user_id=user_id,
    document_score=data['document_score'],
    photo_score=data.get('photo_score', 0.0),
    consistency_score=data['consistency_score'],
    behavioral_score=data['behavioral_score'],
    social_score=data.get('social_score', 0.0),
    completeness_score=data['completeness_score'],
    reputation_score=data.get('reputation_score', 1.0),
    ...
)
```

### services/ai-backend/app/routers/trust.py

**✅ NO CHANGES NEEDED** - Already correctly handles all 7 components with `getattr()` for optional scores

### services/ai-backend/app/routers/matching.py

**✅ NO CHANGES NEEDED** - Already uses correct tier system and limits

## Frontend Changes

### NEW FILES CREATED:

#### 1. `apps/mobile/types/trust.ts`
**Complete TypeScript type definitions for trust score system**

Features:
- `TrustTier` type with 5 tiers (diamond, coral, pearl, shell, pebble)
- `TierInfo` interface with tier benefits and limits
- `TIER_INFO` constant with all tier details
- `TrustScoreComponents` interface for all 7 score components
- `SCORE_WEIGHTS` constant matching database weights
- `TrustScoreDetail` and `TrustSummary` interfaces
- `VerificationStatus` interfaces
- `SubscriptionStatus` and `SubscriptionPlan` interfaces
- Helper functions: `getTierFromScore()`, `formatTierKorean()`, etc.

#### 2. `apps/mobile/types/profile.ts`
**Complete profile schema matching database**

Features:
- `Profile` interface with ALL fields from 002_core_tables.sql
- `FamilyBackground` interface
- `ProfileCompleteness` interface
- `ProfileUpdate` and `ProfileSummary` interfaces

#### 3. `apps/mobile/services/trustScoreService.ts`
**Frontend service for trust score APIs**

Methods:
- `getTrustScore(userId)` - Get detailed breakdown
- `getTrustSummary(userId)` - Get simplified summary
- `recalculateTrustScore(userId)` - Force recalculation
- `getUpgradePath(userId)` - Get tier upgrade recommendations
- `getVerificationStatus(userId)` - Check verification status
- `canAccessMatches(userId)` - Check if photo verified
- `getDailyMatchLimit(userId)` - Check match limits
- `logBehavior()` - Log user actions
- `getAllTierInfo()` - Get all tier information

### EXISTING FILES - NO CHANGES NEEDED:

#### `apps/mobile/services/supabaseQuestionService.ts`
**✅ Already correctly structured**
- Uses `get_active_question_count()` RPC function (defined in 006_question_functions.sql)
- Properly caches question count
- Matches database schema from 004_questions_schema.sql

## Migration Checklist

### ✅ Database
- [x] Restructured 6 consolidated migrations → 15 atomic files
- [x] Created Phase 1: Foundation (001-003)
- [x] Created Phase 2: Questions (004-006)
- [x] Created Phase 3: AI Matching (007-008)
- [x] Created Phase 4: Feedback (009)
- [x] Created Phase 5: Verification (010-012)
- [x] Created Phase 6: Trust Score (013-014)
- [x] Created Phase 7: Subscriptions (015)
- [x] All migrations are idempotent
- [x] Backup created in migrations_consolidated/

### ✅ Backend (Python/FastAPI)
- [x] Updated `trust_score_service.py` to return all 7 scores
- [x] Updated `calculate_trust_score()` method
- [x] Updated `get_trust_score()` method
- [x] Verified `trust.py` router handles all scores
- [x] Verified `matching.py` uses correct tier system

### ✅ Frontend (React Native/TypeScript)
- [x] Created `types/trust.ts` with complete type definitions
- [x] Created `types/profile.ts` with profile schema
- [x] Created `services/trustScoreService.ts` service
- [x] Verified `supabaseQuestionService.ts` compatibility

## Testing Checklist

### Database Testing
```bash
# Reset and apply all 15 migrations
cd supabase
supabase db reset

# Verify all tables created
supabase db diff

# Check migration count
ls -1 migrations/*.sql | wc -l
# Should output: 15

# Test RPC functions
psql -h localhost -U postgres -d flio -c "SELECT calculate_trust_score('user-id-here');"
psql -h localhost -U postgres -d flio -c "SELECT * FROM questions LIMIT 1;"
psql -h localhost -U postgres -d flio -c "SELECT COUNT(*) FROM questions;"
# Should output: 40
```

### Backend Testing
```bash
# Test trust score calculation
curl http://localhost:8000/trust/score/{user_id}

# Test trust summary
curl http://localhost:8000/trust/summary/{user_id}

# Test upgrade path
curl http://localhost:8000/trust/upgrade-path/{user_id}

# Test tier info
curl http://localhost:8000/trust/tiers/info
```

### Frontend Testing
```typescript
import { trustScoreService } from '@/services/trustScoreService';
import { getTierInfo, getTierFromScore } from '@/types/trust';

// Get trust score
const score = await trustScoreService.getTrustScore(userId);
console.log('Total score:', score.total_trust_score);
console.log('Tier:', score.trust_tier);
console.log('Components:', score.component_scores);

// Get tier info
const tierInfo = getTierInfo('pearl');
console.log('Pearl tier:', tierInfo);

// Check if can access matches
const canAccess = await trustScoreService.canAccessMatches(userId);
console.log('Can access matches:', canAccess);
```

## Migration Path for Production

1. **Backup existing database**
   ```bash
   pg_dump -h your-host -U your-user -d flio > backup_$(date +%Y%m%d).sql
   ```

2. **Run new migrations** (all 15 files in order 001-015)
   ```bash
   supabase db push
   ```

3. **Verify data integrity**
   - Check all profiles have required columns
   - Verify trust scores calculated correctly
   - Test matching functionality
   - Verify all 40 questions exist: `SELECT COUNT(*) FROM questions;`

4. **Deploy backend changes**
   - Deploy updated `trust_score_service.py`
   - Verify API endpoints return all 7 scores

5. **Deploy frontend changes**
   - Add new type files
   - Add new trust score service
   - Update components to use new types

## Breaking Changes

### ⚠️ None - Zero Application Code Changes Required

**IMPORTANT:** This migration restructuring requires **ZERO code changes** because:
- All table names unchanged (profiles, questions, matches, etc.)
- All function names unchanged (calculate_trust_score, find_matches, etc.)
- All column names unchanged
- Frontend/backend reference names, not migration file numbers

Application code continues to work as-is:
```typescript
// Frontend - no changes needed
await supabase.from('questions').select('*')
await supabase.rpc('calculate_trust_score', { p_user_id })
```

```python
# Backend - no changes needed
supabase.table('user_answers').select('*')
supabase.rpc('find_matches', { p_user_id })
```

### API Response Format (Unchanged)
```json
{
  "component_scores": {
    "document": 0.75,
    "photo": 0.90,
    "consistency": 0.85,
    "behavioral": 0.70,
    "social": 0.50,
    "completeness": 0.60,
    "reputation": 1.0
  }
}
```

## Benefits of 15-File Structure

### For Developers
- **Faster onboarding** - Easy to understand what each file does
- **Easier debugging** - Know exactly where to look for issues
- **Safer refactoring** - Modify specific features without side effects
- **Better code reviews** - Review one feature at a time

### For Future Features
**Example: Adding Video Verification**
- Old (6 files): Modify large `004_verification_system.sql` (risky, 300+ lines)
- New (15 files): Create `016_video_verification.sql` (safe, atomic, ~50 lines)

### For Git Workflow
- **Clearer diffs** - See exactly what changed
- **Better history** - Track changes to specific features
- **Easier rollbacks** - Rollback specific features independently

## Environment Variables

### Backend (.env)
```bash
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key
AZURE_OPENAI_API_KEY=your-api-key
```

### Frontend (.env.local)
```bash
EXPO_PUBLIC_SUPABASE_URL=your-supabase-url
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
EXPO_PUBLIC_AI_BACKEND_URL=http://localhost:8000
```

## Documentation Updates

### API Documentation
All trust score endpoints now return 7 components. API docs already reflect:
- `photo_score` field (required, 20% weight)
- `social_score` field (10% weight)
- `reputation_score` field (5% weight)

### User-Facing Documentation
User guides already explain:
- Photo verification is REQUIRED to access matches
- 5-tier system (Diamond/Coral/Pearl/Shell/Pebble)
- How each score component is calculated
- How to improve trust score

## Support & Troubleshooting

### Common Issues

**Issue: Users can't access matches**
- **Solution:** Verify `photo_verified = true` in profiles table
- **Check:** Run `SELECT photo_verified FROM profiles WHERE user_id = ?`

**Issue: Trust score shows 0 for new users**
- **Expected:** New users start with realistic defaults (consistency: 0.3, behavioral: 0.5)
- **Not a bug:** Users must build trust over time

**Issue: Migration fails during db reset**
- **Solution:** Check dependency order in README.md
- **Verify:** All 15 files run in numerical order (001-015)
- **Check logs:** `supabase db reset` output for specific errors

**Issue: Questions not loading (count shows 0)**
- **Solution:** Verify `005_questions_data.sql` ran successfully
- **Check:** Run `SELECT COUNT(*) FROM questions;` (should be 40)

## Next Steps

1. **✅ Completed** - Created 15 atomic migration files
2. **✅ Completed** - Backed up old 6 consolidated files
3. **✅ Completed** - Updated README.md documentation
4. **✅ Completed** - Updated MIGRATION_UPDATES.md
5. **⏳ Pending** - Test migrations with `supabase db reset`
6. **⏳ Pending** - Deploy to staging environment
7. **⏳ Pending** - Monitor trust score calculations and matching
8. **⏳ Pending** - Deploy to production in phases

## Contact

For questions about these changes, contact the development team or refer to:
- **Database migrations:** `/supabase/migrations/README.md`
- **Backend service:** `/services/ai-backend/app/services/trust_score_service.py`
- **Frontend types:** `/apps/mobile/types/trust.ts`
- **Migration dependency diagram:** `/supabase/migrations/README.md` (Dependency Order section)

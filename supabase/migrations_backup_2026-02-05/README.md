# FLIO Database Migrations

## Overview

This directory contains the official database migrations for FLIO. These migrations follow industry best practices with atomic, focused files that are easy to understand and maintain.

## Migration Files

Run migrations in numerical order:

| File | Description | Lines |
|------|-------------|-------|
| **Phase 1: Foundation** | | |
| **001_extensions_and_types.sql** | PostgreSQL extensions (pgvector) and utility functions | ~30 |
| **002_core_tables.sql** | Core tables: profiles, matches, messages, meeting_feedback | ~175 |
| **003_core_indexes_and_rls.sql** | Indexes and Row Level Security policies for core tables | ~105 |
| **Phase 2: Questions** | | |
| **004_questions_schema.sql** | Questions, user answers, feedback, system settings tables | ~100 |
| **005_questions_data.sql** | 40 research-based questions (INSERT statements) | ~360 |
| **006_question_functions.sql** | Question functions, triggers, RLS policies, permissions | ~110 |
| **Phase 3: AI Matching** | | |
| **007_ai_matching_functions.sql** | AI matching functions using vector embeddings | ~110 |
| **008_daily_match_tracking.sql** | Daily match views, match history, tier-based limits | ~300 |
| **Phase 4: Feedback** | | |
| **009_reshuffle_system.sql** | User feedback and preference analysis caching | ~150 |
| **Phase 5: Verification** | | |
| **010_verification_tables.sql** | Photo, document, phone, social, family, consistency tables | ~250 |
| **011_verification_functions.sql** | Verification functions, triggers, RLS policies | ~180 |
| **012_behavioral_reputation_tables.sql** | Behavior logs, reports, interactions, analytics | ~100 |
| **Phase 6: Trust Score** | | |
| **013_trust_score_calculation.sql** | 7-component trust score calculation with tier assignment | ~420 |
| **014_trust_score_matching.sql** | Tier-based weighted matching algorithm | ~90 |
| **Phase 7: Subscriptions** | | |
| **015_subscription_payment_system.sql** | Subscription plans, payments, eligibility checks | ~290 |

**Total**: 15 files, ~2,270 lines (down from 6 files, ~2,400 lines)

## ⚠️ MANDATORY ONBOARDING REQUIREMENTS

Before users can access the app, they **MUST** complete:
1. **📱 Phone Verification** - SMS code verification (Korean phone numbers)
2. **📸 Photo Verification** - Live selfie with liveness detection

See [ONBOARDING_REQUIREMENTS.md](/ONBOARDING_REQUIREMENTS.md) for complete details.

## Key Features

### 5-Tier Trust Score System
- **Diamond** (80-100%): ₩59,900/month, 30 matches/day + Priority
- **Coral** (60-79%): ₩39,900/month, 20 matches/day
- **Pearl** (40-59%): ₩19,900/month, 15 matches/day
- **Shell** (20-39%): ₩9,900/month, 10 matches/day
- **Pebble** (0-19%): Free, 5 matches/day

### Trust Score Components
1. **Document** (25%) - ID card, diploma, income verification
2. **Photo** (20%) - **REQUIRED** baseline security
3. **Consistency** (15%) - Answer consistency checks
4. **Behavioral** (15%) - Account age + engagement metrics
5. **Social** (10%) - LinkedIn/Instagram/Kakao/Naver verification
6. **Completeness** (10%) - Profile completion
7. **Reputation** (5%) - Community feedback

### Matching Algorithm
- **Formula**: Embedding similarity (60%) + Weighted answers (40%)
- **Photo verification required** to access matches
- **Tier-based matching** within same or lower tiers

## Architecture Principles

### Atomic Migrations
- **One responsibility per file** - Each migration has a single, clear purpose
- **Easier maintenance** - Modify specific features without touching others
- **Better version control** - Clear git diffs showing what changed
- **Safer deployments** - Reduced risk of breaking changes

### Dependency Order
```
001 (extensions) → 002 (core tables) → 003 (indexes/RLS)
                                     ↓
                 004 (questions schema) → 005 (questions data) → 006 (question functions)
                                     ↓
                 007 (AI functions) → 008 (match tracking)
                                     ↓
                 009 (reshuffle system)
                                     ↓
                 010 (verification tables) → 011 (verification functions) → 012 (behavioral tables)
                                     ↓
                 013 (trust calculation) → 014 (trust matching)
                                     ↓
                 015 (subscriptions)
```

### Idempotent Design
- All migrations use `CREATE TABLE IF NOT EXISTS`
- Functions use `CREATE OR REPLACE`
- Indexes use `CREATE INDEX IF NOT EXISTS`
- Safe to run multiple times without errors

## Running Migrations

### Fresh Database
```bash
# Using Supabase CLI (recommended)
supabase db reset

# Verify all tables created
supabase db diff
```

### Production Deployment
```bash
# Push to Supabase
supabase db push

# Or deploy via CI/CD
supabase link --project-ref your-project-ref
supabase db push
```

## Default Values for New Users

To prevent artificial trust scores, new users start with realistic defaults:
- **Consistency score**: 0.3 (builds to 1.0 with 30+ answers)
- **Behavioral score**: 0.5 (builds to 0.8 with 6+ months account age)
- **Reputation score**: 1.0 (decreases with negative behavior)
- **Starting tier**: Pebble (0-19% trust score)

Users must earn higher tiers through:
1. Completing profile + answering questions → Shell tier
2. Photo + ID verification → Pearl tier
3. Education + income + LinkedIn → Coral tier
4. Employment + social proof + good behavior → Diamond tier

## Migration History

### Version 3.0 (Current - 15 Atomic Files)
Restructured 6 consolidated files into 15 focused, atomic migrations following industry best practices:
- **Better separation of concerns** - Each file has a single responsibility
- **Easier to understand** - Clear what each migration does
- **Future-proof** - Add new features without modifying existing files
- **Improved maintainability** - Smaller files are easier to review and modify

### Version 2.0 (6 Consolidated Files)
Consolidated 14 incremental migrations into 6 logical files (January 2026)

### Version 1.0 (14 Incremental Files)
Original migration structure with incremental ALTER TABLE statements

## Benefits of 15-File Structure

### For Developers
- **Faster onboarding** - Easy to understand what each file does
- **Easier debugging** - Know exactly where to look for issues
- **Safer refactoring** - Modify specific features without side effects

### For Future Features
**Example: Adding Video Verification**
- Old (6 files): Modify large `004_verification_system.sql` (risky, 300+ lines)
- New (15 files): Create `016_video_verification.sql` (safe, atomic, ~50 lines)

### For Code Review
- **Clear diffs** - See exactly what changed
- **Focused reviews** - Review one feature at a time
- **Better approval process** - Approve specific changes independently

## Backup

Original 6 consolidated migration files are backed up at:
```
supabase/migrations_consolidated/
├── 001_core_schema.sql
├── 002_questions_and_answers.sql
├── 003_reshuffle_system.sql
├── 004_verification_system.sql
├── 005_trust_score_system.sql
└── 006_subscription_payment_system.sql
```

## Notes

- All migrations are idempotent (safe to run multiple times)
- Tables use `IF NOT EXISTS` and `IF EXISTS` clauses appropriately
- Indexes use `IF NOT EXISTS` to prevent conflicts
- Functions use `CREATE OR REPLACE` for safe updates
- Row Level Security (RLS) is enabled on all user-facing tables
- **Zero application code changes required** - All table/function names unchanged

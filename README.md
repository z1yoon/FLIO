# FLIO 🌊

**Finding Love In the Ocean** - AI-Powered Korean Marriage Platform

> **"Trust by System, Not by People"**

---

## Quick Start

```bash
# Backend + Database
docker-compose up -d
curl http://localhost:8000/health

# Mobile App
cd apps/mobile
npm install
npx expo start
```

---

## Trust Score (7 Components)

### Scoring System
| Component | Weight | How to Improve |
|-----------|--------|----------------|
| 📄 **Documents** | 25% | Upload ID, diploma, income, employment certs |
| 📸 **Photo Verification** | 20% | **REQUIRED** - Selfie verification (expires 6 months) |
| 🔗 **Social Verification** | 10% | Link LinkedIn, Instagram, KakaoTalk, Naver |
| ✅ **Consistency** | 15% | No contradictions in profile/answers |
| 💬 **Behavioral** | 15% | High response rate, good conversation quality |
| 📝 **Completeness** | 10% | Fill profile + answer all 44 questions |
| ⭐ **Reputation** | 5% | No reports, no ghosting, positive outcomes |

**Total Score = Weighted sum of all 7 components**

### 5-Tier System

```
💎 Diamond (80-100%)  ₩59,900/월  30 matches/day + Priority Support
🪸 Coral   (60-79%)   ₩39,900/월  20 matches/day
🫧 Pearl   (40-59%)   ₩19,900/월  15 matches/day
🐚 Shell   (20-39%)   ₩9,900/월   10 matches/day
🪨 Pebble  (0-19%)    Free        5 matches/day
```

### Tier Progression

| From → To | Requirements |
|-----------|-------------|
| Pebble → Shell | Complete profile + All 44 questions answered |
| Shell → Pearl | **+ Photo verification (REQUIRED)** + ID card |
| Pearl → Coral | + Diploma + Income cert + LinkedIn |
| Coral → Diamond | + Employment cert + Instagram + 90 days good behavior |

---

## Photo Verification (REQUIRED)

**🔒 Must verify photo to access matches**

**How it works:**
1. Take selfie with random pose (smile, turn left, thumbs up, etc.)
2. AI checks:
   - ✅ Face matches profile photos
   - ✅ Real person (liveness detection)
   - ✅ Correct pose performed
3. ✅ Verified → Can see matches
   ❌ Not verified → Blocked from matches
4. 🔄 Re-verify every 6 months

**Industry standard** - Used by Bumble, Tinder, Hinge

---

## Matching Algorithm

### Formula
```
Match Score = (Embedding × 60%) + (Weighted Answers × 40%)
```

### Components

**1. Embedding Similarity (60%)**
- AI semantic understanding using Azure OpenAI
- Captures overall vibe and values
- 1024D vector embeddings

**2. Weighted Answer Alignment (40%)** ← **BUG FIX**
```
Question Weight = base_weight × (1 + importance/5) × (effectiveness/10)

Example:
"Want children?" → Weight 2.0 (high importance)
"Like pets?"     → Weight 0.4 (low importance)

Final = Σ(weight × alignment) / Σ(weight)
```

**Note:** Trust score NOT included in matching (users already matched within same/similar tiers)

**Result:** Important questions (marriage, kids) weighted higher than trivial ones (pets, food)

---

## 44 Research-Based Questions

**Categories:**
- **Dealbreakers (4):** Gender, age, divorce, disability - 100% match required
- **Gottman's Four Horsemen (3):** 94% divorce prediction accuracy
- **Attachment Theory (2):** 90%+ relationship prediction
- **Korean Cultural (3):** Family approval, filial piety, traditional values
- **Core Compatibility (15):** Marriage timeline, children, conflict resolution
- **Lifestyle (11):** Location, pets, exercise, drinking, travel
- **Deep Reflection (3):** Life values, relationship vision, conflict philosophy

---

## Database Schema (10 Migrations)

**Consolidated from 12 → 10 clean migrations:**

```sql
001_initial_schema.sql                    -- Core database
002_upgrade_embeddings.sql                -- AI embeddings
003_questions_database.sql                -- 44 questions
004_ai_backend_functions.sql              -- Matching functions
005_user_answers_table.sql                -- User answers
006_user_feedback_preferences.sql         -- User feedback (MERGED)
007_verification_trust_system.sql         -- Verification & trust (MERGED)
008_daily_match_tracking.sql              -- Match limits
009_tier_based_matching.sql               -- Tier filtering
010_trust_score_system.sql                -- ⭐ Complete trust & matching system
```

**Migration 010 Features:**
- Photo verification table (REQUIRED for matching)
- Social verification table (LinkedIn/Instagram/Kakao/Naver)
- User reports table (harassment, scams, ghosting)
- User interactions table (messages, blocks)
- Conversation analytics table (ghosting detection, positive outcomes)
- Enhanced behavioral scoring (7 components)
- Weighted matching algorithm (important questions weighted higher)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Mobile** | React Native + Expo 52 |
| **Backend** | FastAPI + Python 3.11 |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **AI** | Azure OpenAI (GPT-4o-mini + Embeddings) |
| **OCR** | Azure AI Vision |
| **Translation** | Azure Translator (Korean ↔ English) |
| **Cache** | Redis |

---

## Environment Setup

### Backend (.env)
```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your_service_role_key

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_CHAT_MODEL=gpt-4o-mini

# Azure Vision (OCR)
AZURE_VISION_ENDPOINT=https://your-vision.cognitiveservices.azure.com/
AZURE_VISION_KEY=your_key

# Azure Translator
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com/
AZURE_TRANSLATOR_KEY=your_key
AZURE_TRANSLATOR_REGION=koreacentral

# Cache
REDIS_URL=redis://localhost:6379/0
```

### Mobile (.env)
```bash
EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
EXPO_PUBLIC_AI_BACKEND_URL=http://localhost:8000
```

---

## API Endpoints

### Trust Score
```bash
GET  /api/v1/trust/score/{user_id}           # Get detailed score breakdown
GET  /api/v1/trust/tier/{user_id}            # Get tier only
POST /api/v1/trust/recalculate/{user_id}     # Recalculate score
GET  /api/v1/trust/upgrade-path/{user_id}    # Get upgrade recommendations
```

### Photo Verification
```bash
POST /api/v1/verification/photo/request      # Get random pose challenge
POST /api/v1/verification/photo/submit       # Submit selfie
GET  /api/v1/verification/photo/status       # Check verification status
```

### Document Verification
```bash
POST /api/v1/verification/document/verify    # Upload & verify document
GET  /api/v1/verification/status/{user_id}   # Get all verifications
```

### Matching
```bash
GET /api/v1/matching/matches/{user_id}?limit=10
# Returns: compatibility_score, embedding_similarity, answer_alignment

GET /api/v1/matching/match-explanation/{user_a}/{user_b}
# Shows: why matched, aligned questions, compatibility breakdown
```

---

## Project Structure

```
FLIO/
├── apps/mobile/                    # React Native app
│   ├── app/
│   │   ├── (onboarding)/
│   │   │   ├── questions.tsx       # 44 questions
│   │   │   ├── document-verification.tsx
│   │   │   └── extended-profile.tsx
│   │   ├── (tabs)/
│   │   │   ├── matches.tsx         # Shows trust badges
│   │   │   └── profile.tsx
│   │   └── tier.tsx                # Tier upgrade screen
│   └── services/
│       └── aiQuestionService.ts
│
├── services/ai-backend/            # FastAPI backend
│   ├── app/
│   │   ├── routers/
│   │   │   ├── trust.py
│   │   │   ├── verification.py
│   │   │   └── matching.py
│   │   └── services/
│   │       ├── trust_score_service.py
│   │       ├── photo_verification_service.py
│   │       ├── social_verification_service.py
│   │       ├── ocr_service.py
│   │       └── matching_service.py
│   └── requirements.txt
│
├── supabase/migrations/            # 10 clean migrations
│   └── 001-010_*.sql
│
├── docker-compose.yml
└── README.md
```

---

## Implementation Status

### ✅ Implemented (Backend)
- [x] Trust Score (7 components)
- [x] Photo verification system (REQUIRED)
- [x] Social verification (LinkedIn/Instagram/Kakao/Naver)
- [x] Enhanced behavioral tracking
- [x] Community reputation system
- [x] Weighted matching algorithm
- [x] 5-tier system (Diamond/Coral/Pearl/Shell/Pebble)
- [x] 10 consolidated migrations
- [x] Document OCR verification
- [x] NLI consistency checking

### 🚧 To Implement (Mobile)
- [ ] Photo verification UI flow
- [ ] Social OAuth integration
- [ ] Conversation quality tracking
- [ ] Report/block functionality
- [ ] Trust score breakdown UI
- [ ] Match explanation screen

### 🔮 Future Features
- [ ] Video verification
- [ ] AI matchmaker recommendations
- [ ] Professional background checks
- [ ] Meeting scheduler
- [ ] Success story tracking

---

## Cost Estimate (1000 users/month)

| Service | Cost |
|---------|------|
| Supabase Pro | $25 |
| Azure OpenAI | $30-50 |
| Azure Translator | $10-15 |
| Azure AI Vision (OCR) | $1-5 |
| Redis | $0 (Docker) |
| **Total** | **$66-95/month** |

**Per user:** $0.07-0.10/month

**Revenue:** Tier subscriptions (₩9,900 - ₩59,900/month per user)

---

## Development Workflow

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f ai-backend

# Start mobile
cd apps/mobile && npx expo start

# Test API
curl http://localhost:8000/docs

# Stop services
docker-compose down
```

---

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Get trust score
curl http://localhost:8000/api/v1/trust/score/{user_id}

# Find matches
curl http://localhost:8000/api/v1/matching/matches/{user_id}?limit=10

# Check photo verification
curl http://localhost:8000/api/v1/verification/photo/status/{user_id}
```

---

## Key Features

### 🎯 Weighted Question Matching
Questions are weighted by importance - dealbreakers like marriage timeline and children matter more than lifestyle preferences like pets or food. Uses research-based weights (Gottman, attachment theory).

### 🔒 Required Photo Verification
All users MUST complete photo verification to access matches. Liveness detection prevents fake profiles. Verification expires every 6 months for continued security.

### 📊 7-Component Trust Score
Comprehensive scoring system: Documents (25%), Photo (20%), Social (10%), Consistency (15%), Behavioral (15%), Completeness (10%), Reputation (5%). More balanced than document-only systems.

### 💎 5-Tier System
Diamond/Coral/Pearl/Shell/Pebble tiers with clear progression path. Higher tiers get more daily matches and additional features.

---

## Philosophy

Traditional marriage agencies rely on human consultants. FLIO achieves the same credibility through:

- ✅ AI-driven verification (not manual review)
- ✅ Algorithmic trust scoring (not subjective judgment)
- ✅ Photo verification REQUIRED (baseline security)
- ✅ Transparent tier system (not binary approval/rejection)
- ✅ Data-driven matching (research-based questions)

---

**Version:** 1.0
**Status:** ✅ Database Ready | 🚧 Mobile Integration Needed
**Last Updated:** 2026-01-22

# FLIO 🌊

**Finding Love In the Ocean** - AI-powered Korean dating app with hybrid matching algorithm combining choice-based and semantic compatibility.

## Features

- 🧠 **Hybrid Matching Algorithm** - Combines Azure AI embeddings with static question scoring
- 🎯 **Smart Question Design** - 44 research-based questions (Gottman Institute, Attachment Theory, Korean culture)
- 🚫 **Dealbreaker Filtering** - Critical compatibility factors (marriage, children, values)
- ♿ **Inclusive & Accessible** - Simple yes/no disability acceptance dealbreaker
- 💰 **Cost Optimized** - Korean text translated to English for AI processing to reduce token costs
- 📊 **AI Answer Analysis** - Real-time clarity scoring and insight extraction
- 💬 **Match Explanations** - Azure OpenAI GPT-4o-mini generates personalized compatibility reasons
- 🇰🇷 **Korean-Optimized** - Cultural values and relationship compatibility focus
- 📱 **Modern Mobile App** - React Native + Expo with seamless UX
- ✅ **Verified Names** - Real name verification for authentic connections

---

## ⚠️ Development Principles

> **ALWAYS use Context7 or Web Search to find latest AI models before coding.**
> 
> - Accuracy is the #1 priority
> - Use highest benchmark models available
> - Prefer Korean fine-tuned models for Korean language tasks
> - Check MTEB, Open LLM Leaderboard, Hugging Face for latest benchmarks
> - Azure OpenAI for production-grade reliability and performance

---

## Quick Start

### 1. Environment Setup

**Configure Azure Services:**
```bash
cd services/ai-backend
# Create .env file with your credentials:
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - AZURE_TRANSLATOR_ENDPOINT (for cost optimization)
# - AZURE_TRANSLATOR_KEY
# - AZURE_TRANSLATOR_REGION (e.g., koreacentral)
# - SUPABASE_URL
# - SUPABASE_SECRET_KEY
```

### 2. AI Backend (Docker Compose)

```bash
# Start backend + Redis with Docker Compose
docker-compose up

# Or run in detached mode
docker-compose up -d
```

**Backend runs on:** `http://localhost:8000`
**Redis runs on:** `localhost:6379`

### 3. Mobile App (Expo)

```bash
cd apps/mobile
npm install
npx expo start
```

**Test on iPhone:**
1. Install "Expo Go" from App Store
2. Scan QR code with camera
3. Must be on same WiFi network

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Mobile** | React Native + Expo 52 |
| **Backend** | FastAPI + Python 3.11 |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **AI Platform** | Azure OpenAI |
| **Embeddings** | text-embedding-3-large (1024D) |
| **Chat/Analysis** | gpt-4o-mini |
| **Vector Search** | pgvector (cosine similarity) |
| **Deployment** | Docker Compose + Redis |

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │   AI Backend    │    │  Azure OpenAI   │
│ (React Native)  │────│   (FastAPI)     │────│   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│   Supabase      │──────────────┘
                        │  (PostgreSQL    │
                        │   + pgvector)   │
                        └─────────────────┘
```

### Core AI Services

| Service | Purpose | Technology |
|---------|---------|------------|
| **Hybrid Matching** | Choice questions + semantic embeddings | PostgreSQL + pgvector |
| **Profile Embedding** | Convert text answers to vectors | Azure OpenAI text-embedding-3-large |
| **Translation** | Korean to English for cost optimization | Azure Translator (60% cost reduction) |
| **Answer Analysis** | Analyze clarity and extract insights | Azure OpenAI gpt-4o-mini |
| **Match Explanation** | Generate compatibility reasons | Azure OpenAI gpt-4o-mini |
| **Dealbreaker Filter** | Exclude incompatible matches | PostgreSQL functions |

### Consistency / Source of Truth

- **Questions list & IDs**: `supabase/migrations/003_questions_database.sql` is the source of truth
- **Backend matching**: must reference the same `question_id` values from the `questions` table
- **Mobile UI**: should render questions from Supabase and never hardcode extra question IDs
- **README**: documents the current system behavior and should be updated if question IDs/counts change

## Key Features

### 1. Hybrid Matching Algorithm

**Three-Component Scoring System:**

1. **Static Question Matching (60% weight)** - PRIMARY
   - Direct comparison of **41 active choice questions** (excludes 3 text questions)
   - Exact matches score 1.0, partial matches score 0.5
   - Covers lifestyle, values, and relationship preferences
   - Fast PostgreSQL-based comparison
   - Prioritizes concrete compatibility over abstract similarity

2. **Importance Bonus (20% weight)** - HIGH-PRIORITY MATCHING
   - Rewards matching on questions marked as important (4-5 importance)
   - Ensures critical compatibility factors are weighted heavily
   - User-defined priorities influence final score

3. **Azure Embedding Similarity (20% weight)** - SEMANTIC UNDERSTANDING
   - Uses Azure OpenAI text-embedding-3-large (1024 dimensions)
   - Based on **3 open-ended text questions** only (reduced from 5 for less user fatigue)
   - Semantic understanding of values, life philosophy, relationship dynamics
   - Captures nuanced compatibility beyond explicit answers
   - Cosine similarity between profile embeddings
   - **Cost optimization**: Korean text translated to English before embedding (60% cost reduction)

**Formula:** `Total Score = (Static × 0.6) + (Importance × 0.2) + (Embedding × 0.2)`

**Critical Filtering Requirements:**
- **100% Dealbreaker Match Required**: Users with ANY dealbreaker mismatch are filtered out before scoring
- **50% Minimum Static Match**: Users must match on at least 50% of static choice questions to be shown as matches

**Question Breakdown (2024 Research-Optimized):**
- **41 Active Choice Questions**: Used for exact/partial matching (60% weight)
- **3 Open-Ended Text Questions**: Used for embedding similarity (20% weight)
- **Total: 44 Active Questions**
- **Research Basis**: Gottman Institute (94% divorce prediction), Attachment Theory (90%+ accuracy), Korean marriage agencies

**Quality Thresholds:**
- **Minimum Static Match: 50%** - Users must match on at least 50% of static choice questions
- Static questions are fundamental compatibility indicators (values, lifestyle, goals)
- Embedding similarity alone is insufficient - concrete compatibility is required
- Ensures all matches have meaningful baseline compatibility

**Dealbreaker Filtering:** 
- **100% match required** on all 4 dealbreaker questions (gender, age range, divorce status, disability acceptance)
- Incompatible users are excluded BEFORE compatibility scoring
- No exceptions - dealbreakers are hard filters

**Static Question Threshold:**
- **50% minimum match required** on static choice questions
- Ensures baseline compatibility - embedding similarity alone is insufficient
- Users below 50% match rate are filtered out even with high embedding similarity

**Performance:** Optimized with pgvector for sub-second matching

### 2. Smart Question Design (2024 Research-Optimized)

**44 Total Questions** based on psychological research (Gottman Institute, Attachment Theory, Korean cultural priorities)

**Question Categories:**
- **Dealbreakers** (4): Gender preference, age range, divorce status, disability acceptance
- **Core Compatibility** (15): Marriage timeline, children, conflict resolution, Gottman's Four Horsemen, attachment security
- **Family & Values** (11): Korean cultural priorities (family approval, filial piety, traditional/modern balance), holiday obligations, financial management
- **Lifestyle** (11): Living location, pets, exercise, drinking, smoking, travel, food, cleanliness, personality
- **Deep Reflection** (3 text questions): Values/happiness, ideal relationship/future vision, conflict growth philosophy

**New 2024 Research-Based Questions:**
- **Gottman's Four Horsemen** (94% divorce prediction accuracy):
  - How you express frustration with partner
  - First reaction to partner's mistakes (contempt detection)
  - How you reconnect after arguments (repair attempts)
- **Attachment Security** (90%+ prediction accuracy):
  - Response to good news sharing (active-constructive responding)
  - Comfort level with disagreements (conflict tolerance)
- **Korean Cultural Priorities** (82% consider family approval critical):
  - Importance of family approval for relationship
  - Expected role of parents in married life (filial piety)
  - Traditional vs modern relationship values balance

**Design Principles:**
- **No Vague Options**: All choices are distinct and meaningful
- **Inclusive Design**: Simple yes/no disability acceptance dealbreaker
- **Research-Backed**: Every question validated by psychological research or Korean cultural studies
- **Reduced Text Questions**: 3 instead of 5 to reduce user fatigue while maintaining semantic matching quality

---

## SQL Question Database Structure

### Question Schema (`supabase/migrations/003_questions_database.sql`)

```sql
CREATE TABLE questions (
    id VARCHAR(100) PRIMARY KEY,           -- Question identifier (e.g., 'marriage_timeline')
    category VARCHAR(50) NOT NULL,         -- Korean category (e.g., '결혼계획')
    text_ko TEXT NOT NULL,                 -- Korean question text
    text_en TEXT NOT NULL,                 -- English question text
    answer_type VARCHAR(50) NOT NULL,      -- 'choice' or 'text'
    options JSONB NOT NULL,                -- Answer options with match_weight
    base_weight FLOAT DEFAULT 0.5,         -- Base importance weight (0.0-1.0)
    effectiveness_score FLOAT DEFAULT 5.0, -- Research-based score (1.0-10.0)
    can_be_dealbreaker BOOLEAN DEFAULT false,
    tags TEXT[],                           -- Category tags
    placeholder TEXT,                      -- Placeholder for text questions
    max_length INTEGER,                    -- Max length for text answers
    is_active BOOLEAN DEFAULT true,        -- Active status
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Question Ordering Logic

**CRITICAL:** Questions are ordered by `answer_type` FIRST, then by `effectiveness_score`:

```sql
ORDER BY answer_type ASC, effectiveness_score DESC, base_weight DESC
```

**Why this matters:**
- `answer_type = 'choice'` comes before `answer_type = 'text'` alphabetically
- **ALL choice questions appear FIRST** (Q1-41)
- **ALL text questions appear LAST** (Q42-44)
- Within each type, highest `effectiveness_score` appears first

### Question ID Conventions

**Format:** `{topic}_{descriptor}` (snake_case)

**Examples:**
- `marriage_timeline` - When do you want to get married?
- `criticism_expression` - How do you express frustration?
- `family_approval_importance` - How important is family approval?

### Options Structure (JSONB)

**Choice Questions:**
```json
[
  {
    "value": "within_1_year",
    "text_ko": "1년 이내에 하고 싶어요",
    "text_en": "Within 1 year",
    "match_weight": 1.0
  },
  {
    "value": "1_2_years",
    "text_ko": "1-2년 정도 생각해요",
    "text_en": "1-2 years",
    "match_weight": 0.95
  }
]
```

**Text Questions:** Empty array `[]`

### Effectiveness Scores (Research-Based)

| Score Range | Category | Research Basis |
|-------------|----------|----------------|
| **10.0** | Dealbreakers | Must-match criteria |
| **9.5-9.9** | Core Compatibility | Gottman's Four Horsemen, Attachment Theory |
| **9.0-9.4** | High Priority | Korean cultural priorities, relationship dynamics |
| **8.5-8.9** | Important Values | Financial, career, family relationships |
| **7.0-8.4** | Lifestyle Factors | Daily habits, social life, personality |
| **6.0-6.9** | Secondary Factors | Exercise, food, environment |

### Adding/Modifying Questions

**1. Update SQL File:**
```sql
-- Add to INSERT statement in 003_questions_database.sql
('new_question_id', 'category_korean', 'text_ko', 'text_en',
 'choice', '[{"value": "option1", "text_ko": "...", "text_en": "...", "match_weight": 1.0}]'::jsonb,
 0.85, 9.2, false, ARRAY['tag1', 'tag2'], NULL, NULL)
```

**2. Apply to Supabase:**
```sql
-- Use MCP Supabase tool or direct SQL
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options,
                       base_weight, effectiveness_score, can_be_dealbreaker, tags)
VALUES (...);
```

**3. Update Mobile Constants:**
```typescript
// apps/mobile/services/supabaseQuestionService.ts
private readonly TOTAL_QUESTIONS = 44;  // Update count
private readonly MIN_QUESTIONS_FOR_MATCHING = 44;

// Update questionOrder array with new question ID
```

**4. Update README:**
- Update question counts in relevant sections
- Document new question purpose and research basis

### Question Count Management

**Current Count (2024):** 44 active questions
- **41 choice questions** (answer_type = 'choice')
- **3 text questions** (answer_type = 'text')

**Verify Count:**
```sql
SELECT is_active, COUNT(*) FROM questions GROUP BY is_active;
-- Should return: {is_active: true, count: 44}
```

**Check Text Questions:**
```sql
SELECT id, effectiveness_score FROM questions
WHERE answer_type = 'text' AND is_active = true
ORDER BY effectiveness_score DESC;
-- Should return: personal_values_lifestyle (9.9), ideal_relationship_dynamic (9.8), conflict_growth_philosophy (9.4)
```

---

### 3. AI-Powered Analysis
- Real-time answer quality scoring (1-10 scale)
- Automatic insight extraction from user responses
- Vagueness detection with follow-up suggestions
- Korean cultural context awareness
- AI-generated compatibility summaries and conversation starters

### 4. Cost Optimization for Korean Text
- **Translation Pipeline**: Korean → English → AI Processing → Korean
- **Why**: Korean text uses ~2-3x more tokens than English in GPT models
- **Savings**: ~60% reduction in embedding and gpt-4o-mini costs
- **Implementation**:
  - Text answers translated to English before embedding generation
  - gpt-4o-mini analysis done on English text, results translated back
  - Maintains semantic accuracy while reducing costs

## API Endpoints

### Questions & Answers
```bash
# Get all 44 questions (41 choice + 3 text)
GET /api/v1/questions/initial?language=ko

# Submit answer with AI analysis
POST /api/v1/questions/answer
{
  "user_id": "uuid",
  "question_id": "marriage_timeline",
  "answer_value": "within_year",
  "importance": 5,
  "is_dealbreaker": true
}
```

### Profile Matching
```bash
# Create profile embedding (after answering all 3 text questions)
POST /api/v1/matching/profile/create-embedding?user_id={id}

# Find matches using hybrid algorithm
GET /api/v1/matching/matches/{user_id}?limit=10

# Response includes:
# - compatibility_score: Total hybrid score (0-1)
# - name: Match name
# - age: Match age
# - user_id: Match user ID

# Get match explanation with AI
GET /api/v1/matching/match-explanation/{user_a_id}/{user_b_id}
```

## Documentation

- `docs/ARCHITECTURE.md` - System design and data flow
- `docs/AI_MODELS_2025.md` - AI model selection criteria
- `docs/BUSINESS_PLAN.md` - Product vision and roadmap
- `CODING_STANDARDS.md` - Development guidelines

## Project Structure

```
FLIO/
├── apps/mobile/              # React Native Expo app
│   ├── app/                  # Screens (Expo Router)
│   ├── components/           # Reusable UI components
│   ├── services/             # API clients
│   │   ├── aiQuestionService.ts  # Question & answer API
│   │   └── ai/cloudAI.ts         # AI service integration
│   └── package.json
│
├── services/ai-backend/      # FastAPI AI backend
│   ├── app/
│   │   ├── main.py           # FastAPI app with Azure OpenAI
│   │   ├── routers/
│   │   │   ├── questions.py  # Question & answer endpoints
│   │   │   ├── matching.py   # Hybrid matching endpoints
│   │   │   └── auth.py       # Authentication
│   │   ├── services/
│   │   │   ├── azure_openai_service.py      # Azure OpenAI integration
│   │   │   └── profile_embedding_service.py # Profile embedding service
│   │   └── models/
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Environment configuration
│
├── supabase/                 # Database & migrations
│   ├── migrations/
│   │   ├── 001_initial_schema.sql        # Base schema
│   │   ├── 002_upgrade_embeddings.sql    # Vector embeddings
│   │   ├── 003_questions_database.sql    # 44 questions (41 choice + 3 text) - 2024 research-optimized
│   │   ├── 004_ai_backend_functions.sql  # Hybrid matching functions
│   │   └── 006_user_answers_functions.sql # User answer processing
│   └── config.toml
│
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md
│   ├── AI_MODELS_2025.md
│   └── BUSINESS_PLAN.md
│
└── README.md                 # This file
```

## Environment Variables

### Backend (.env)
```bash
# Azure OpenAI (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-large
AZURE_OPENAI_CHAT_MODEL=gpt-4o-mini

# Azure Translator (Required for cost optimization)
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com/
AZURE_TRANSLATOR_KEY=your_translator_key
AZURE_TRANSLATOR_REGION=koreacentral

# Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your_secret_key

# Optional
REDIS_URL=redis://localhost:6379/0
```

### Mobile (.env)
```bash
EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
EXPO_PUBLIC_AI_BACKEND_URL=http://localhost:8000
```

## Coding Standards

See `CODING_STANDARDS.md` for detailed guidelines.

### Core Principles
- Clean and simple code only
- No unnecessary code or features
- Consistent style across all files
- Minimal dependencies
- One responsibility per function
- Use early returns to avoid deep nesting

## Development Workflow

1. **Start Backend + Redis**: `docker-compose up`
2. **Start Mobile**: `cd apps/mobile && npx expo start`
3. **Check Health**: Visit `http://localhost:8000/health`
4. **View API Docs**: Visit `http://localhost:8000/docs`

### Docker Commands
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f ai-backend

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

## Hybrid Matching Algorithm

### How It Works

```sql
-- 1. Dealbreaker Filtering (100% match required) - FIRST
-- Filters out users with ANY dealbreaker mismatch
-- 4 dealbreakers: gender_preference, age_range_preference, divorce_status, disability_acceptance
WHERE check_dealbreaker_compatibility(user_a, user_b) = TRUE

-- 2. Static Question Threshold (50% minimum) - SECOND
-- Filters out users with less than 50% exact match on choice questions
-- Compares Q1-41 answers (exact matches only, no partial)
WHERE calculate_exact_match_rate(user_a, user_b) >= 0.5

-- 3. Static Question Compatibility (60% weight)
-- Compares Q1-41 answers using match_weight values (includes partial matches)
SELECT calculate_static_score(user_a, user_b) * 0.6
-- Returns: 0.0 (no match) to 0.6 (perfect match)

-- 4. Importance Bonus (20% weight)
-- Rewards matching on questions marked as important (4-5 importance)
SELECT calculate_importance_bonus(user_a, user_b) * 0.2
-- Returns: 0.0 to 0.2

-- 5. Embedding Similarity (20% weight)
-- Compares Q42-44 text answers using cosine similarity
-- (Korean text translated to English for cost efficiency)
SELECT (1 - (embedding_a <=> embedding_b)) * 0.2 as embedding_score
-- Returns: 0.0 to 0.2

-- 6. Combined Score
total_score = (static_score * 0.6) + (importance_bonus * 0.2) + (embedding_similarity * 0.2)
-- Returns: 0.0 to 1.0
```

### Example Match Calculation

**User A & User B:**
- **Dealbreakers**: ✅ 100% match (all 4 dealbreakers aligned) - PASS
- **Exact match rate**: ✅ 58.5% (24/41 exact matches) - PASS (≥50% required)
- **Static compatibility**: 0.85 (includes partial matches with match_weight)
- **Importance bonus**: 0.75 (matching on 75% of important questions)
- **Embedding similarity**: 0.78 (similar values in text answers)

**Final Score:**
```
total_score = (0.85 * 0.6) + (0.75 * 0.2) + (0.78 * 0.2)
            = 0.510 + 0.150 + 0.156
            = 0.816 (81.6% compatibility)
```

**Filtering Logic:**
1. ✅ Dealbreaker check: 100% match required → PASS
2. ✅ Static threshold: 58.5% ≥ 50% required → PASS
3. ✅ Calculate compatibility score: 81.6%
4. ✅ Show as match

### Database Functions

| Function | Purpose |
|----------|---------|
| `find_similar_profiles_v2()` | Main hybrid matching function |
| `calculate_choice_compatibility()` | Choice question scoring |
| `get_user_answers_with_metadata()` | Fetch answers with question data |

---

## Matching Architecture Details

### Static Questions (Q1-41) - Choice Matching

**When User Answers:**
```sql
-- User submits answer to choice question
INSERT INTO user_answers (user_id, question_id, answer_value, importance, is_dealbreaker)
VALUES ('user-123', 'marriage_timeline', 'within_1_year', 5, true);

-- Stored in database immediately, no AI processing needed
```

**How Matching Works:**
```sql
-- SQL function compares answers using match_weight from options JSONB
WITH choice_matches AS (
    SELECT 
        q.base_weight,
        -- Extract match_weight for each user's answer
        (SELECT (opt->>'match_weight')::float 
         FROM jsonb_array_elements(q.options) opt
         WHERE opt->>'value' = ua.answer_value) as weight_a,
        (SELECT (opt->>'match_weight')::float 
         FROM jsonb_array_elements(q.options) opt
         WHERE opt->>'value' = ub.answer_value) as weight_b
    FROM user_answers ua
    JOIN user_answers ub ON ua.question_id = ub.question_id
    JOIN questions q ON ua.question_id = q.id
    WHERE ua.user_id = 'user-a' AND ub.user_id = 'user-b'
      AND q.answer_type = 'choice'
)
SELECT AVG(weight_a * weight_b) as choice_score FROM choice_matches;
```

**Example:**
- User A: "never_drink" (match_weight: 1.0)
- User B: "regularly" (match_weight: 0.4)
- Score: 1.0 × 0.4 = 0.4 (lower compatibility)

---

### Open-Ended Questions (Q42-44) - Embedding Matching

**When User Answers:**
```python
# Step 1: User submits text answer
POST /api/v1/questions/answer
{
  "user_id": "user-123",
  "question_id": "personal_values_lifestyle",
  "answer_text": "성실함을 중요하게 여겨 매일 아침 운동하고..."
}

# Step 2: Stored in database
INSERT INTO user_answers (user_id, question_id, answer_text)

# Step 3: After all 3 text questions answered, create embedding
POST /api/v1/matching/profile/create-embedding?user_id=user-123
```

**Embedding Generation Flow:**
```python
# 1. Fetch all 3 text answers
answers = fetch_text_answers(user_id)

# 2. Combine into single profile text (Korean)
profile_korean = build_profile_text(answers)
# "한국인 결혼 대상자 프로필: 가치관과 일상: 성실함을..."

# 3. Translate to English (cost optimization: 60% savings)
profile_english = translator.translate_to_english(profile_korean)
# "Korean marriage candidate profile: Values and daily life: I value sincerity..."

# 4. Generate embedding (1536 dimensions)
embedding = openai.embeddings.create(
    model="text-embedding-3-large",
    input=profile_english
)
# [0.234, -0.567, 0.891, ..., 0.123]

# 5. Store in database (pgvector)
store_user_embedding(user_id, embedding, profile_korean)
```

**How Matching Works:**
```sql
-- SQL function uses pgvector for cosine similarity
SELECT 
    user_id,
    1 - (embedding <=> query_embedding) as similarity
FROM user_profiles
WHERE user_id != 'user-123'
ORDER BY embedding <=> query_embedding  -- Vector distance
LIMIT 50;

-- Returns similarity: 0.0 (opposite) to 1.0 (identical)
```

---

### Complete Matching Flow

```python
# Find matches for user
async def find_matches(user_id):
    # 1. Get user's embedding
    user_embedding = get_embedding(user_id)
    
    # 2. Find candidates with similar embeddings (40% weight)
    candidates = find_similar_profiles_v2(user_embedding, limit=50)
    # Returns: [{user_id: 'user-b', similarity: 0.85}, ...]
    
    # 3. For each candidate, calculate choice compatibility (50% weight)
    for candidate in candidates:
        choice_score = calculate_choice_compatibility(user_id, candidate.user_id)
        # Returns: {total_score: 0.82, matched: 34/41}
        
        # 4. Check dealbreakers (filter)
        if has_dealbreaker_conflict(user_id, candidate.user_id):
            continue  # Skip this candidate
        
        # 5. Calculate final hybrid score
        combined_score = (
            choice_score * 0.5 +      # 50% choice questions
            candidate.similarity * 0.4 + # 40% text embedding
            0.1                        # 10% base bonus
        )
        
        candidate.combined_score = combined_score
    
    # 6. Return top matches sorted by combined score
    return sorted(candidates, reverse=True)[:10]
```

---

### Summary Table

| Question Type | Storage | Processing | Matching Method | Weight |
|---------------|---------|------------|-----------------|--------|
| **Dealbreakers (4 questions)** | Flag in DB | SQL check | 100% match required | **Hard Filter** |
| **Q1-41 Exact Match** | Immediate DB | SQL comparison | Exact match rate | **50% Min Threshold** |
| **Q1-41 (Choice)** | Immediate DB | None (SQL only) | match_weight multiplication | **60%** |
| **Importance Bonus** | DB with importance | SQL check | Match on important questions | **20%** |
| **Q42-44 (Text)** | DB → Batch | Translate → Embed | Cosine similarity (pgvector) | **20%** |
| **Combined Score** | - | Hybrid calculation | Weighted sum | **100%** |

**Cost Optimization:**
- Korean text → English translation before embedding
- Reduces token costs by ~60% (Korean uses 2-3x more tokens)
- Translation: $0.0001 per answer
- Embedding: $0.0002 per user (English)
- Total: $0.0003 per user vs $0.0005 (direct Korean)

## Testing

### Backend Health Check
```bash
curl http://localhost:8000/health
```

### Test Embedding Generation
```bash
curl -X POST "http://localhost:8000/api/v1/matching/profile/create-embedding?user_id=test-user-id"
```

### Test Answer Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/questions/answer" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "question_id": "test-q",
    "answer_value": "가족과 함께 시간을 보내는 것을 중요하게 생각합니다",
    "importance": 5,
    "is_dealbreaker": false
  }'
```

## Contributing

Before making changes:
1. Check `docs/ARCHITECTURE.md` for system design
2. Follow coding standards in `CODING_STANDARDS.md`
3. Test locally before committing
4. Update documentation if adding features

## License

Private project - All rights reserved

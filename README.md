# FLIO 🌊

**Finding Love In the Ocean** - AI-powered Korean dating app with hybrid matching algorithm combining choice-based and semantic compatibility.

## Features

- 🧠 **Hybrid Matching Algorithm** - 50% choice questions + 40% embeddings + 10% importance weighting
- 🎯 **Smart Question Design** - 35 choice questions + 5 open-ended questions optimized for matching
- 🚫 **Dealbreaker Filtering** - 5 critical dealbreakers (marriage, children, disability acceptance, conflict, trust)
- ♿ **Inclusive & Accessible** - Simple yes/no disability acceptance dealbreaker
- 💰 **Cost Optimized** - Korean text translated to English for AI processing to reduce token costs
- 📊 **AI Answer Analysis** - Real-time clarity scoring and insight extraction
- 💬 **Match Explanations** - AI-generated compatibility reasons and conversation starters
- 🇰🇷 **Korean-Optimized** - Cultural values and relationship compatibility focus
- 📱 **Modern Mobile App** - React Native + Expo with seamless UX

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
| **Answer Analysis** | Analyze clarity and extract insights | Azure OpenAI gpt-4o-mini |
| **Match Explanation** | Generate compatibility reasons | Azure OpenAI gpt-4o-mini |
| **Dealbreaker Filter** | Exclude incompatible matches | PostgreSQL functions |

## Key Features

### 1. Hybrid Matching Algorithm
- **Choice Questions (Q1-35)**: Exact matching with semantic `match_weight` values
- **Text Questions (Q36-40)**: Semantic embedding similarity
- **Scoring Formula**: 50% choice + 40% embedding + 10% importance
- **Dealbreaker Filtering**: Automatic exclusion of incompatible users
- **Performance**: SQL-optimized for sub-100ms matching

### 2. Smart Question Design
- **Dealbreakers First** (Q1-5): Marriage timeline, children, **disability acceptance (yes/no)**, conflict resolution, trust
- **Relationship Core** (Q6-9): Emotional support, communication, attachment, affection
- **Marriage & Family** (Q10-18): Marriage priorities, family values, parents (allowance/care)
- **Economic Partnership** (Q19-22): Financial transparency, dual career, crisis response
- **Lifestyle & Health** (Q23-27): Work-life balance, health, **drinking habits**, **smoking status**
- **Personality & Values** (Q28-35): MBTI, social energy, decision making, stress response, life values
- **Deep Reflection** (Q36-40): AI-powered semantic matching questions
  - Captures values, life philosophy, relationship dynamics
  - Analyzes **semantic meaning**, not just keywords
  - Finds partners with similar worldviews and life approaches
  - Questions designed to elicit thoughtful, narrative responses
- **No Vague Options**: All choices are distinct and meaningful
- **Inclusive Design**: Simple yes/no disability acceptance dealbreaker

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
# Get all 40 questions (35 choice + 5 text)
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
# Create profile embedding (from text answers Q36-40)
POST /api/v1/matching/profile/create-embedding?user_id={id}

# Find matches using hybrid algorithm
GET /api/v1/matching/matches/{user_id}?limit=10&min_compatibility=0.3

# Response includes:
# - choice_score: Choice question compatibility (0-1)
# - similarity: Embedding similarity (0-1)
# - combined_score: Hybrid total (0-1)
# - has_dealbreaker_conflict: Boolean

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
│   │   ├── 003_feedback_system.sql       # User feedback
│   │   ├── 004_questions_database.sql    # 40 questions (35 choice + 5 text)
│   │   └── 005_ai_backend_functions.sql  # Hybrid matching functions
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
-- 1. Choice Question Compatibility (50%)
-- Compares Q1-35 answers using match_weight values
SELECT calculate_choice_compatibility(user_a, user_b)
-- Returns: 0.0 (no match) to 1.0 (perfect match)

-- 2. Embedding Similarity (40%)
-- Compares Q36-40 text answers using cosine similarity
-- (Korean text translated to English for cost efficiency)
SELECT 1 - (embedding_a <=> embedding_b) as similarity
-- Returns: 0.0 (opposite) to 1.0 (identical)

-- 3. Combined Score (with 10% base bonus)
combined_score = (choice_score * 0.5) + (similarity * 0.4) + 0.1

-- 4. Dealbreaker Filtering
-- Excludes users where dealbreaker answers conflict
WHERE NOT has_dealbreaker_conflict
```

### Example Match Calculation

**User A & User B:**
- Choice compatibility: 0.85 (34/35 questions aligned)
- Embedding similarity: 0.78 (similar values in text answers)
- Dealbreakers: No conflicts (all 5 dealbreakers match)

**Final Score:**
```
combined_score = (0.85 * 0.5) + (0.78 * 0.4) + 0.1
               = 0.425 + 0.312 + 0.1
               = 0.837 (83.7% compatibility)
```

### Database Functions

| Function | Purpose |
|----------|---------|
| `find_similar_profiles_v2()` | Main hybrid matching function |
| `calculate_choice_compatibility()` | Choice question scoring |
| `get_user_answers_with_metadata()` | Fetch answers with question data |

---

## Matching Architecture Details

### Static Questions (Q1-35) - Choice Matching

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

### Open-Ended Questions (Q36-40) - Embedding Matching

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

# Step 3: After all 5 text questions answered, create embedding
POST /api/v1/matching/profile/create-embedding?user_id=user-123
```

**Embedding Generation Flow:**
```python
# 1. Fetch all 5 text answers (Q36-40)
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
        # Returns: {total_score: 0.82, matched: 30/35}
        
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
| **Q1-35 (Choice)** | Immediate DB | None (SQL only) | match_weight multiplication | 50% |
| **Q36-40 (Text)** | DB → Batch | Translate → Embed | Cosine similarity (pgvector) | 40% |
| **Dealbreakers (Q1-5)** | Flag in DB | SQL check | Binary pass/fail | Filter |
| **Combined Score** | - | Hybrid calculation | Weighted sum + bonus | 100% |

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

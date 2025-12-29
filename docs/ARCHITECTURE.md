# FLIO Architecture

## ⚠️ AI Model Selection Rule

> **ALWAYS search Context7 or Web for latest benchmarks before selecting AI models.**
> 
> Priority:
> 1. **Accuracy first** - Use highest benchmark scores
> 2. **Korean fine-tuned** - For Korean language tasks
> 3. **Self-hosted** - For privacy and cost control
> 4. **Open source** - Apache 2.0 or MIT license preferred
>
> Sources to check:
> - MTEB Leaderboard (embeddings)
> - Open LLM Leaderboard (LLMs)
> - Hugging Face Korean models
> - Papers with Code

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Mobile** | React Native + Expo |
| **Avatar** | Rive (State Machine) |
| **Backend** | FastAPI + Modal.com (GPU) |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **AI Models** | See `AI_MODELS_2025.md` |

---

## System Flow

```
Mobile App (Expo)
    ↓
Supabase (Auth, DB, Storage)
    ↓
AI Backend (Modal.com)
├── Face: InsightFace (512D)
├── Matching: bge-m3-korean (1024D)
├── Questions: Qwen2.5-7B
├── STT: Whisper large-v3 (self-hosted)
├── TTS: CosyVoice2 (150ms latency, Korean)
├── RAG: Question database with BGE-M3
└── RL: Thompson Sampling for question selection
```

---

## Key Features

### 1. Face Verification (85% threshold)
```
Profile Photo → InsightFace → 512D embedding
Live Selfie → InsightFace → 512D embedding
→ Cosine Similarity ≥ 0.85 → ✅ Verified
```

### 2. Voice Conversation (STT/TTS)
```
User Speech → Whisper large-v3 → Text (4% WER Korean)
AI Response → CosyVoice2 → Voice (150ms latency)
→ Natural avatar conversations with emotion control
```

### 3. Intelligent Question Selection (RAG + RL)
```
User Answer → RAG retrieves relevant questions
→ RL (Thompson Sampling) selects best question
→ Qwen2.5 personalizes the question
→ Learns from answer quality and match outcomes
```

### 4. Adaptive Questions
```
User Answer → Qwen2.5 → Analyze clarity
→ If vague → Generate follow-up questions
→ Update profile embedding
```

### 5. Reshuffle Analysis
```
User requests reshuffle → Ask why
→ Qwen2.5 analyzes reason
→ Suggest additional questions if needed
→ Better matches
```

### 6. Secret Profile Verification ⭐ NEW
```
User A meets User B → Post-meeting feedback
→ "프로필 사진과 실제 모습이 비슷했나요?"
→ Anonymous report (B never knows who reported)
→ 2+ inaccurate reports → B is blocked
→ B must correct info to unblock
```

### 7. A/B Testing Framework ⭐ NEW
```
50% users → Question order A (결혼관 먼저)
50% users → Question order B (라이프스타일 먼저)
→ Track profile completion rate
→ Winner becomes default for all users
```

---

## Project Structure

```
FLIO/
├── apps/mobile/           # React Native Expo
│   ├── app/               # Screens (Expo Router)
│   ├── components/avatar/ # RiveAvatar.tsx
│   └── services/ai/       # cloudAI.ts
│
├── services/ai-backend/   # FastAPI
│   ├── app/models/        # AI models
│   ├── app/routers/       # API endpoints
│   └── modal_deploy.py    # GPU deployment
│
├── supabase/migrations/   # Database schema
└── docs/                  # Documentation
```

---

## What is RAG & RL?

| Tech | Simple Explanation |
|------|-------------------|
| **RAG** | 질문 DB에서 관련 질문 찾기 (검색) |
| **RL** | 어떤 질문이 효과적인지 학습 (개선) |

```
RAG = "이 답변에 맞는 후속 질문 찾아줘" (검색)
RL  = "이 질문이 좋은 결과를 냈어? 기억해둘게" (학습)
```

---

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| **Face** | |
| `POST /api/face/embed` | Extract embedding |
| `POST /api/face/verify` | Verify match |
| **Match** | |
| `POST /api/match/embed` | Profile embedding |
| **Questions** | |
| `POST /api/questions/analyze` | Analyze answer |
| `POST /api/questions/generate` | Generate followup |
| `POST /api/questions/reshuffle` | Analyze reshuffle |
| **Speech** | |
| `POST /api/speech/transcribe` | STT |
| `POST /api/speech/synthesize` | TTS |
| **RAG + RL** | |
| `POST /api/rag/next` | Get next questions |
| `POST /api/rag/process` | Process answer |
| `POST /api/rag/coverage` | Question coverage |
| `POST /api/rl/feedback` | Update RL |
| **Feedback** | |
| `POST /api/feedback/outcome` | Match outcome |
| `POST /api/feedback/verify` | Secret verification |
| `GET /api/feedback/status/{id}` | User status |
| **A/B Test** | |
| `POST /api/ab/variant` | Get variant |
| `POST /api/ab/convert` | Record conversion |
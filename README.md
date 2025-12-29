# FLIO 🌊

**Finding Love In the Ocean** - AI-powered dating app with face verification.

## Features

- 🎤 **Voice-guided onboarding** with AI avatar (Whisper + MeloTTS)
- 🔐 **Face verification** (85% match threshold)
- 🧠 **Smart matching** with RAG + RL
- 🔄 **Adaptive questions** that improve over time

---

## ⚠️ Development Principles

> **ALWAYS use Context7 or Web Search to find latest AI models before coding.**
> 
> - Accuracy is the #1 priority
> - Use highest benchmark models available
> - Prefer Korean fine-tuned models for Korean language tasks
> - Check MTEB, Open LLM Leaderboard, Hugging Face for latest benchmarks

---

## Quick Start

### 1. Mobile App (Expo)

```bash
cd apps/mobile
npm install
npx expo start
```

**Test on iPhone:**
1. Install "Expo Go" from App Store
2. Scan QR code with camera
3. Must be on same WiFi

### 2. AI Backend (Local)

```bash
cd services/ai-backend
docker-compose up
```

### 3. AI Backend (Production)

```bash
cd services/ai-backend
modal deploy modal_deploy.py
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Mobile | React Native + Expo |
| Avatar | Rive |
| Backend | FastAPI + Modal.com |
| Database | Supabase |
| Face AI | InsightFace |
| Matching AI | bge-m3-korean |
| Question AI | Qwen2.5-7B |

## Docs

- `docs/ARCHITECTURE.md` - System design
- `docs/AI_MODELS_2025.md` - AI model details
- `docs/BUSINESS_PLAN.md` - Product vision

## Project Structure

```
FLIO/
├── apps/mobile/        # React Native app
├── services/ai-backend/ # FastAPI AI services
├── supabase/           # Database migrations
└── docs/               # Documentation
```

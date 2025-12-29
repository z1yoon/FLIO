# FLIO AI Models

## ⚠️ Model Selection Rule

> **Before selecting any AI model, ALWAYS:**
> 1. Search Context7 for latest documentation
> 2. Search Web for latest benchmarks
> 3. Check Hugging Face for Korean fine-tuned versions
> 4. Prioritize: Accuracy > Speed > Cost

---

## Quick Reference

| Feature | Model | Why |
|---------|-------|-----|
| **Profile Matching** | `upskyy/bge-m3-korean` | Korean fine-tuned, 87.4% accuracy |
| **Question Generation** | `Qwen/Qwen2.5-7B-Instruct` | Apache 2.0, best Korean LLM |
| **Face Verification** | InsightFace (ArcFace) | 99.8% accuracy, 512D |
| **STT** | Whisper large-v3 | Best Korean ASR (~4% WER) |
| **TTS** | CosyVoice2-0.5B | 150ms latency, Korean emotion control |
| **RAG** | BGE-M3 + Question DB | Semantic question retrieval |
| **Reranker** | Qwen3-Reranker-0.6B | +15-20% RAG accuracy |
| **RL** | Thompson Sampling | Learn optimal question order |
| **Sentiment** | Qwen2.5 (shared) | Emotion & personality analysis |
| **Avatar** | Rive | State Machine, 90.8 benchmark |

---

## Profile Matching: upskyy/bge-m3-korean

```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel('upskyy/bge-m3-korean', use_fp16=True)
embedding = model.encode("프로필 텍스트", return_dense=True)['dense_vecs']
```

- **Dimension**: 1024D
- **Korean STS**: 87.4 (vs 82.1 for original BGE-M3)
- **Max Tokens**: 8192

---

## STT: Whisper large-v3

```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, info = model.transcribe(audio, language="ko")
```

- **Korean WER**: ~4% (best self-hosted)
- **License**: Apache 2.0
- Uses `faster-whisper` (CTranslate2) for 4x speed

---

## TTS: CosyVoice2-0.5B

```python
from cosyvoice import CosyVoice

model = CosyVoice('CosyVoice-300M-SFT')
audio = model.inference_sft("안녕하세요", 'Korean')
```

- **Latency**: 150ms (streaming mode)
- **Languages**: Korean, Chinese, English, Japanese
- **Emotion control**: Fine-grained style control
- **License**: Apache 2.0
- Fallbacks: MeloTTS → edge-tts (Microsoft)

---

## RAG: Question Database

```python
# RAG retrieves relevant questions
questions = rag_retriever.retrieve_by_context(
    user_answer="글쎄요, 아직 잘 모르겠어요",
    current_question="결혼 시기는?",
    top_k=5
)
```

- Uses BGE-M3 embeddings for semantic search
- 15+ curated questions across 5 categories
- Categories: 결혼관/가치관/재정/라이프스타일/가족

---

## RL: Thompson Sampling

```python
# RL selects best question
selected = rl_selector.select_question(
    candidate_questions=questions,
    user_context={"age": 30, "gender": "F"}
)

# Update from answer quality
rl_selector.update_from_answer_analysis(question_id, analysis)

# Update from match outcome
rl_selector.update_from_match_success(questions_asked, match_accepted=True)
```

- **Algorithm**: Multi-Armed Bandit (Thompson Sampling)
- **Learns from**: Answer clarity, engagement, match success
- **No training required**: Works with limited data

---

## Reranker: Qwen3-Reranker-0.6B

```python
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Reranker-0.6B")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-Reranker-0.6B")

# Rerank candidates for better accuracy
# BGE-M3 (10 candidates) → Reranker → Top 3 (15-20% more accurate)
```

- **MTEB Reranking**: #1 multilingual
- **Improvement**: +15-20% over bi-encoder only
- **License**: Apache 2.0

---

## Sentiment & Personality Analysis

```python
# Detect user emotions from answers
sentiment = analyzer.analyze_sentiment(answer)
# Returns: {"primary_emotion": "hesitation", "engagement_level": "low"}

# Extract Big 5 personality traits
traits = personality.extract_traits(answers)
# Returns: {"openness": 0.7, "extraversion": 0.4, ...}
```

Used for:
- Detect vague answers → Ask follow-up to get CLEAR answer
- Match compatible communication styles
- Personality-based compatibility scoring

**⚠️ Never skip questions! Always get clear answers.**

---

## Cost (Modal.com)

| Model | GPU | Monthly (10K requests) |
|-------|-----|------------------------|
| bge-m3-korean | T4 | ~$15 |
| Qwen2.5-7B | A10G | ~$50 |
| Qwen3-Reranker | A10G | ~$10 |
| Whisper large-v3 | A10G | ~$30 |
| CosyVoice2 | A10G | ~$20 |
| **Total** | | **~$125** |

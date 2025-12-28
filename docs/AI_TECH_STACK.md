# FLIO 필수 AI 기술 스택

## 📋 개요

FLIO는 **11개 핵심 AI 기술**로 구성됩니다. 모두 MVP 출시에 필수적입니다.

---

## 🎯 1. 프로필 작성 AI (4개)

### 1.1 적응형 질문 생성
**모델:** `EleutherAI/polyglot-ko-1.3b`
**용도:** 사용자 답변 분석 후 다음 질문 자동 생성
**라이센스:** Apache 2.0 (상업용 가능)
**호스팅:** 자체 서버 (Supabase Edge Functions)

```python
# 구현 예시
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("EleutherAI/polyglot-ko-1.3b")
tokenizer = AutoTokenizer.from_pretrained("EleutherAI/polyglot-ko-1.3b")

def generate_follow_up_question(user_answer):
    prompt = f"""
    사용자 답변: "{user_answer}"

    이 답변이 애매하다면 더 구체적인 정보를 얻기 위한 후속 질문을 생성하세요.
    답변이 명확하다면 "CLEAR"라고 답하세요.

    후속 질문:
    """

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=200)
    response = tokenizer.decode(outputs[0])

    return response
```

**필요 이유:** 고정된 질문만으로는 정확한 프로필 작성 불가

---

### 1.2 음성 → 텍스트 변환 (STT)
**모델:** `OpenAI Whisper` (base 모델)
**용도:** 사용자 음성 답변을 텍스트로 변환
**라이센스:** MIT (상업용 가능)
**호스팅:** 자체 서버 (GPU 인스턴스)

```python
# 구현 예시
import whisper

model = whisper.load_model("base")

def transcribe_voice(audio_file_path):
    """
    음성 파일을 한국어 텍스트로 변환
    """
    result = model.transcribe(
        audio_file_path,
        language="ko",
        fp16=False  # CPU에서도 작동
    )
    return result["text"]

# 사용 예시
audio = "user_answer.wav"
text = transcribe_voice(audio)
# Output: "저는 2년 이내에 결혼하고 싶어요"
```

**성능:**
- 정확도: 한국어 ~95%
- 속도: 1분 음성 → 3초 처리 (CPU 기준)
- 비용: 무료 (자체 호스팅)

**필요 이유:** 음성 입력 = 핵심 차별화 요소 (완료율 3배)

---

### 1.3 텍스트 → 음성 변환 (TTS)
**모델:** `MeloTTS-Korean`
**용도:** AI 아바타가 질문을 음성으로 읽어줌
**라이센스:** MIT (상업용 가능)
**호스팅:** 자체 서버

```python
# 구현 예시
from melo.api import TTS

device = 'cpu'  # GPU 있으면 'cuda'
model = TTS(language='KR', device=device)
speaker_ids = model.hps.data.spk2id

def text_to_speech(text, output_path='output.wav'):
    """
    한국어 텍스트를 음성으로 변환
    """
    model.tts_to_file(
        text=text,
        speaker_id=speaker_ids['KR'],
        output_path=output_path,
        speed=1.0
    )
    return output_path

# 사용 예시
question = "결혼 계획이 있으신가요?"
audio_file = text_to_speech(question)
# → output.wav 생성됨
```

**필요 이유:** 음성 UX 완성 (듣고 → 말하기)

---

### 1.4 질문 순서 최적화
**기술:** 강화학습 (Reinforcement Learning)
**프레임워크:** `Stable Baselines3` (PPO 알고리즘)
**용도:** 완료율 최대화하는 질문 순서 학습
**호스팅:** 자체 서버 (학습), Supabase (추론)

```python
# 구현 예시
from stable_baselines3 import PPO
import gymnasium as gym

# 환경 정의
class QuestionOrderEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.questions = load_questions()  # 150개 질문
        self.current_step = 0

    def step(self, action):
        # action = 다음 질문 ID
        next_question = self.questions[action]

        # 사용자 반응 시뮬레이션 (실제로는 DB에서 가져옴)
        user_completed = self.ask_question(next_question)

        reward = 100 if user_completed else -50
        done = self.current_step >= 30  # 30개 질문 완료

        return next_question, reward, done, {}

# 학습
env = QuestionOrderEnv()
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=100000)
model.save("question_optimizer")

# 추론
model = PPO.load("question_optimizer")
next_question_id = model.predict(current_state)[0]
```

**필요 이유:** 질문 순서에 따라 완료율 30% → 75% 차이

---

## 💕 2. 매칭 AI (2개)

### 2.1 의미 기반 매칭
**모델:** `jhgan/ko-sroberta-multitask`
**용도:** 프로필 답변을 벡터로 변환 후 유사도 계산
**라이센스:** Apache 2.0 (상업용 가능)
**호스팅:** Supabase (pgvector)

```python
# 구현 예시
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('jhgan/ko-sroberta-multitask')

def create_profile_embedding(profile_answers):
    """
    사용자 답변들을 하나의 벡터(768차원)로 변환
    """
    # 모든 답변을 하나의 텍스트로 결합
    combined_text = " ".join([
        f"{q}: {a}" for q, a in profile_answers.items()
    ])

    # 임베딩 생성
    embedding = model.encode(combined_text)
    return embedding  # shape: (768,)

# 매칭 점수 계산
from sklearn.metrics.pairwise import cosine_similarity

user_a = create_profile_embedding(profile_a)
user_b = create_profile_embedding(profile_b)

similarity = cosine_similarity([user_a], [user_b])[0][0]
match_score = int(similarity * 100)  # 0-100점

print(f"매칭 점수: {match_score}%")  # 출력: 89%
```

**Supabase 저장:**
```sql
-- pgvector 확장 활성화
CREATE EXTENSION vector;

-- 테이블 생성
CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    user_id UUID,
    embedding vector(768),
    created_at TIMESTAMP
);

-- 유사 프로필 검색 (빠름!)
SELECT user_id,
       1 - (embedding <=> query_embedding) AS similarity
FROM profiles
WHERE user_id != current_user_id
ORDER BY embedding <=> query_embedding
LIMIT 20;
```

**필요 이유:** 핵심 기능 = 정확한 매칭

---

### 2.2 매칭 이유 설명 생성
**모델:** `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct`
**용도:** 왜 매칭되는지 한국어로 설명
**라이센스:** CC-BY-NC-SA-4.0 (비상업 연구용)
**호스팅:** 자체 서버 (GPU)

```python
# 구현 예시
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
)
tokenizer = AutoTokenizer.from_pretrained(
    "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
)

def generate_match_explanation(user_a_profile, user_b_profile, score):
    prompt = f"""
    두 사람의 프로필을 비교하여 매칭 이유를 설명하세요.

    사용자A:
    - 결혼 시기: 2년 이내
    - 자녀 계획: 2명
    - 재정 관리: 공동 계좌 선호
    - 종교: 무교

    사용자B:
    - 결혼 시기: 3년 이내
    - 자녀 계획: 1-2명
    - 재정 관리: 투명하게 관리
    - 종교: 기독교

    매칭 점수: {score}%

    설명을 3-5개 항목으로 작성하세요 (✅ 일치, ⚠️ 차이):
    """

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=500)
    explanation = tokenizer.decode(outputs[0])

    return explanation

# 출력 예시:
# ✅ 결혼·가족관이 비슷해요 (2년 vs 3년 이내)
# ✅ 자녀 계획 일치 (모두 1-2명 희망)
# ✅ 재정 관리 투명성 중시
# ⚠️ 종교 차이 있음 (대화 필요)
```

**필요 이유:** 결혼정보회사 대비 차별화 (투명성)

---

## 🚨 3. 안전/인증 AI (5개)

### 3.1 부적절한 채팅 감지
**모델:** `beomi/kcbert-base` (Fine-tuned)
**용도:** 성희롱, 사기, 협박 메시지 실시간 탐지
**라이센스:** Apache 2.0
**호스팅:** Supabase Edge Functions (실시간)

```python
# 구현 예시
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

model = AutoModelForSequenceClassification.from_pretrained(
    "beomi/kcbert-base",
    num_labels=3  # 안전, 경고, 위험
)
tokenizer = AutoTokenizer.from_pretrained("beomi/kcbert-base")

# Fine-tuning 필요 (한국 데이팅앱 부적절 메시지 데이터셋)
def detect_unsafe_message(message):
    inputs = tokenizer(message, return_tensors="pt", truncation=True)
    outputs = model(**inputs)

    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    labels = ["안전", "경고", "위험"]

    prediction = labels[torch.argmax(probs)]
    confidence = torch.max(probs).item()

    return {
        "status": prediction,
        "confidence": confidence,
        "should_block": prediction == "위험" and confidence > 0.8
    }

# 사용 예시
msg1 = "안녕하세요! 프로필 보니 등산 좋아하시네요"
result1 = detect_unsafe_message(msg1)
# {'status': '안전', 'confidence': 0.95, 'should_block': False}

msg2 = "사진 더 보내줘. 집 주소 알려줄래?"
result2 = detect_unsafe_message(msg2)
# {'status': '위험', 'confidence': 0.92, 'should_block': True}
```

**필요 이유:** 여성 사용자 안전 = 가장 중요 (한국 앱 최대 이슈)

---

### 3.2 부적절한 사진 필터링
**모델:** `Falconsai/nsfw_image_detection`
**용도:** 선정적/부적절한 프로필 사진 자동 차단
**라이센스:** MIT
**호스팅:** 자체 서버

```python
# 구현 예시
from transformers import pipeline

classifier = pipeline(
    "image-classification",
    model="Falconsai/nsfw_image_detection"
)

def check_profile_photo(image_path):
    results = classifier(image_path)

    # results = [
    #   {'label': 'normal', 'score': 0.85},
    #   {'label': 'nsfw', 'score': 0.15}
    # ]

    for result in results:
        if result['label'] == 'nsfw' and result['score'] > 0.5:
            return {
                "approved": False,
                "reason": "부적절한 사진입니다"
            }

    return {"approved": True}

# 사용
result = check_profile_photo("uploaded_photo.jpg")
if not result['approved']:
    # 업로드 거부
    send_error_message(result['reason'])
```

**필요 이유:** 자동화 (수동 검토 불필요 → 인건비 절감)

---

### 3.3 얼굴 일관성 검사
**모델:** `DeepFace`
**용도:** 여러 사진이 같은 사람인지 확인 (사기 방지)
**라이센스:** MIT
**호스팅:** 자체 서버

```python
# 구현 예시
from deepface import DeepFace

def verify_same_person(photo1_path, photo2_path):
    result = DeepFace.verify(
        img1_path=photo1_path,
        img2_path=photo2_path,
        model_name="VGG-Face"
    )

    return {
        "is_same_person": result['verified'],
        "similarity": result['distance'],
        "threshold": result['threshold']
    }

# 사용 예시: 프로필 사진 3장 검증
photos = ["photo1.jpg", "photo2.jpg", "photo3.jpg"]

for i in range(len(photos)-1):
    result = verify_same_person(photos[0], photos[i+1])

    if not result['is_same_person']:
        reject_photo(photos[i+1], "다른 사람으로 보입니다")
```

**필요 이유:** 모델 사진 도용 방지 (한국 앱 자주 발생)

---

### 3.4 얼굴 생체 인식 (Liveness Detection)
**라이브러리:** `OpenCV` + 맞춤 알고리즘
**용도:** 실제 사람 vs 사진 구분
**라이센스:** Apache 2.0
**호스팅:** 자체 서버

```python
# 구현 예시
import cv2
import numpy as np

def detect_liveness(video_frames):
    """
    사용자에게 "눈 깜빡여주세요" 요청 후
    비디오 프레임에서 눈 깜빡임 감지
    """
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_eye.xml'
    )

    blink_count = 0
    previous_eyes = None

    for frame in video_frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eyes = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(eyes) == 0 and previous_eyes is not None:
            blink_count += 1

        previous_eyes = eyes

    # 2-3초 동안 최소 1회 깜빡임 필요
    return {
        "is_real_person": blink_count >= 1,
        "blink_count": blink_count
    }

# 사용
frames = capture_video(duration=3)  # 3초 촬영
result = detect_liveness(frames)

if not result['is_real_person']:
    reject_verification("실제 사람이 아닙니다")
```

**필요 이유:** 사진으로 인증 통과 방지

---

### 3.5 문서 인증 (OCR)
**서비스:** `Naver Clova OCR API`
**용도:** 졸업장, 재직증명서 텍스트 추출
**비용:** ₩50/건
**호스팅:** Naver Cloud

```python
# 구현 예시
import requests
import json

def extract_document_info(image_path):
    """
    졸업장/재직증명서 이미지에서 정보 추출
    """
    url = "https://api-ocr.ncloud.com/v1/vision/document"

    with open(image_path, 'rb') as f:
        files = {'file': f}
        headers = {
            'X-OCR-SECRET': 'YOUR_SECRET_KEY'
        }

        response = requests.post(url, files=files, headers=headers)
        result = response.json()

    # 결과 파싱
    extracted_text = ""
    for field in result['images'][0]['fields']:
        extracted_text += field['inferText'] + " "

    return parse_education_doc(extracted_text)

def parse_education_doc(text):
    """
    OCR 결과에서 학교명, 전공, 졸업년도 추출
    """
    # 간단한 정규식 매칭
    import re

    university = re.search(r'(.*?대학교)', text)
    major = re.search(r'(.*?학과)', text)
    year = re.search(r'(\d{4})년', text)

    return {
        "university": university.group(1) if university else None,
        "major": major.group(1) if major else None,
        "graduation_year": year.group(1) if year else None,
        "verified": True
    }

# 사용
doc_info = extract_document_info("graduation_certificate.jpg")
# {'university': '서울대학교', 'major': '경영학과',
#  'graduation_year': '2018', 'verified': True}
```

**필요 이유:** 학력/재직 인증 배지 (신뢰도 향상)

---

## 📊 기술 스택 요약

| AI 기술 | 모델/서비스 | 용도 | 호스팅 | 비용 |
|---------|-------------|------|--------|------|
| 질문 생성 | polyglot-ko-1.3b | 적응형 질문 | 자체 | 무료 |
| STT | Whisper base | 음성→텍스트 | 자체 | 무료 |
| TTS | MeloTTS | 텍스트→음성 | 자체 | 무료 |
| 질문 최적화 | RL (PPO) | 순서 학습 | 자체 | 무료 |
| 매칭 | ko-sroberta | 유사도 | Supabase | 무료 |
| 설명 생성 | EXAONE-2.4B | 이유 설명 | 자체 | 무료 |
| 채팅 안전 | kcbert | 부적절 감지 | Supabase | 무료 |
| 사진 필터 | NSFW detector | 선정적 차단 | 자체 | 무료 |
| 얼굴 검증 | DeepFace | 동일인 확인 | 자체 | 무료 |
| Liveness | OpenCV | 실제 사람 | 자체 | 무료 |
| OCR | Clova OCR | 문서 인증 | Naver | ₩50/건 |

**총 인프라 비용 (1년차):**
- 0-5K 사용자: ₩500K/월 (GPU 인스턴스)
- 5K-50K: ₩3M/월
- 50K-60K: ₩5M/월

---

## 🚀 구현 우선순위

### Phase 1: MVP (Month 1)
**필수 8개**
1. ✅ polyglot-ko (질문 생성)
2. ✅ Whisper (STT)
3. ✅ MeloTTS (TTS)
4. ✅ ko-sroberta (매칭)
5. ✅ EXAONE (설명)
6. ✅ kcbert (채팅 안전)
7. ✅ NSFW (사진 필터)
8. ✅ DeepFace (얼굴 검증)

### Phase 2: 최적화 (Month 2-3)
9. ✅ Reinforcement Learning (질문 순서)
10. ✅ OpenCV (Liveness)
11. ✅ Clova OCR (문서 인증)

---

## 💾 데이터 흐름

```
┌─────────────────────────────────────────┐
│  사용자가 "음성" 버튼 클릭               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  1. MeloTTS가 질문 읽어줌               │
│     "결혼 계획이 있으신가요?"            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  2. 사용자 음성 녹음                     │
│     "2년 이내에 결혼하고 싶어요"         │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  3. Whisper STT 변환                    │
│     → "2년 이내에 결혼하고 싶어요"       │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  4. polyglot-ko 분석                    │
│     → 답변 명확함 → 다음 주제로          │
│     (또는)                               │
│     → 답변 애매 → 후속 질문 생성         │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  5. 30-50개 질문 완료 후                │
│     ko-sroberta로 프로필 임베딩 생성     │
│     → vector(768) 저장                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  6. pgvector로 유사 프로필 검색         │
│     → 상위 20명 매칭 후보               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  7. EXAONE이 매칭 이유 설명 생성        │
│     "✅ 결혼 시기 비슷, ⚠️ 종교 차이"  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  8. 사용자가 메시지 전송 시             │
│     kcbert가 안전 여부 실시간 체크       │
└─────────────────────────────────────────┘
```

---

## 🔧 기술 선택 이유

### 왜 이 모델들인가?

1. **polyglot-ko** - 한국어 생성 능력 최고 (1.3B 파라미터, 오픈소스 중 최대)
2. **Whisper** - STT 업계 표준 (OpenAI, 95% 한국어 정확도)
3. **MeloTTS** - 한국어 자연스러움 (무료 중 최고 품질)
4. **ko-sroberta** - 한국어 문장 임베딩 1위 (KLUE 벤치마크)
5. **EXAONE** - LG AI 연구원, 한국어 특화 LLM (2.4B, 무료)
6. **kcbert** - 한국어 BERT 기반 (Beomi, 신뢰도 높음)
7. **DeepFace** - 페이스북 연구, 97% 정확도
8. **Clova OCR** - 한국 문서 인식 1위 (네이버)

**모두 검증됨 + 무료/저렴 + 한국어 특화**

---

## 📈 성능 지표

| AI 기능 | 목표 성능 | 측정 방법 |
|---------|----------|----------|
| STT 정확도 | 95%+ | WER (Word Error Rate) |
| TTS 자연스러움 | 4.0/5+ | 사용자 평가 |
| 질문 적응성 | 애매한 답변 10% 이하 | 답변 분석 |
| 매칭 정확도 | 85%+ | 실제 만남 후 만족도 |
| 채팅 안전 감지 | 95%+ | Precision/Recall |
| 얼굴 인증 | 97%+ | False Accept Rate |

---

## 🔐 보안 & 개인정보

### 데이터 처리 원칙
1. **음성 데이터:** 텍스트 변환 후 즉시 삭제 (저장 안 함)
2. **프로필 임베딩:** vector(768)만 저장 (원본 답변 암호화)
3. **채팅:** Signal Protocol E2EE (서버도 못 봄)
4. **사진:** 인증 후 해시값만 저장

### AI 모델 보안
- 모든 모델 자체 호스팅 (제3자 전송 없음)
- Clova OCR만 Naver 전송 (HTTPS, 즉시 삭제 요청)

---

**작성:** 2025년 12월
**버전:** v1.0
**다음 업데이트:** MVP 베타 테스트 후 성능 수치 추가

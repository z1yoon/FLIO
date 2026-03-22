# 신고 분류·레이블링·자동화 검증 (FLIO)

운영 초기에는 **관리자 판정이 골드 스탠다드**이고, Phase 2부터는 그 판정을 **학습 데이터**로 쓴다.  
“모든 종류의 신고”를 한 번에 다루려면 **계층 구조(L1/L2)** 로 나눈다.

---

## 1. 두 계층 (L1 + L2)

| 계층 | 의미 | 누가 채움 | 예 |
|------|------|-----------|-----|
| **L1** | 앱에서 유저가 고르는 **대분류** (`report_type`) | 유저 | `fake_profile`, `harassment`, `scam` … |
| **L2** | 운영이 정한 **세부 이유 코드** (`admin_label`) | 관리자 (확인 시) | `identity_photo_mismatch`, `financial_fraud`, … |

- 유저는 긴 문장만 쓸 수도 있고, L1만 고를 수도 있다.
- **자동화는 L2를 예측**하는 게 목표다. (L1은 이미 입력값)

---

## 2. L2 표준 코드 예시 (초안 12개)

| 코드 | 설명 | 흔한 L1 매핑 |
|------|------|----------------|
| `identity_photo_mismatch` | 프로필 사진·실물과 다름 | fake_profile, catfishing |
| `document_fraud` | 서류 위조·타인 | fake_profile, scam |
| `financial_scam` | 금전 요구·투자 사기 | scam |
| `harassment_message` | 욕설·협박·스토킹 | harassment |
| `harassment_meet` | 만남 후 폭언·폭력 | harassment |
| `ghosting_pattern` | 반복 유령·무응답 | ghosting |
| `spam_promo` | 홍보·다른 앱 유도 | spam |
| `inappropriate_media` | 사진·콘텐츠 부적절 | inappropriate_content |
| `impersonation` | 타인 사칭 | fake_profile |
| `other_verified` | 기타·확인됨 | other |
| `false_report` | 신고 무효(신고자 과실) | (dismissed) |
| `insufficient_evidence` | 증거 부족 | (dismissed) |

새로운 패턴이 나오면 **코드 추가**하고, 모델은 `other`로 묶거나 “미분류” 큐로 보낸다.

---

## 3. DB에 어떻게 남기나

- `user_reports.report_type` → L1 (기존)
- `user_reports.admin_label` → L2 (관리자 확정 시 필수에 가깝게)
- `user_reports.reason_text` 또는 `report_reason` → 유저 자유 텍스트
- **모델 입력** (나중에): `report_type` + `reason_text` + `evidence_data`(이미지 URL, 채팅 메타 등) + 피신고자 **행동 요약** (신고 횟수, NLI 플래그 등)

Phase 2에서 추가:

- `ai_suggested_label` — 모델 예측 L2
- `ai_confidence` — 0~1
- `decision` — `pending` | `auto_escalate` | `auto_dismiss_candidate` (정책에 따라)

---

## 4. “자동화가 맞는지” 어떻게 확인하나

1. **골드 세트**: 과거에 관리자가 이미 `admin_label` + `status`를 단 건들만 모은다.
2. **Hold-out**: 80% 학습 / 20% 검증 (시간 순으로 나중 20% = 리크 방지).
3. **지표**:
   - **자동 확정**만 쓸 거면: `Precision@auto_confirm` ≥ 0.95 (잘못된 자동 확정 최소화)
   - **자동 기각**만 쓸 거면: `Recall@dismiss` 검토
   - **다중 클래스**: 혼동 행렬(confusion matrix), `macro-F1`
4. **운영 안전장치**:
   - `confidence < 0.9` → **무조건 사람**
   - `severity_level >= 4` 또는 금전·폭력 키워드 → **무조건 사람**
   - 자동 처리는 **일일 상한** (예: 100건/일)

---

## 5. 종류가 너무 많으면?

- **모든 세부 사유를 한 번에 분류할 필요 없음.**
- 1단계: `needs_human` vs `likely_spam` 같은 **이진/소수 클래스**만
- 2단계: 사람 큐에서만 L2 세분
- 또는 **멀티 라벨**: 한 사건에 `financial_scam` + `harassment_message` 동시

---

## 6. OCR과 동일한 원리

| 단계 | 신고 | OCR |
|------|------|-----|
| 라벨 | 관리자 `admin_label` + 확정/기각 | 관리자가 OCR 필드 수정 → ground truth |
| 학습 | 텍스트 분류 / 소형 LLM | Document Intelligence 커스텀 모델 |
| 검증 | Precision on hold-out | Field-level accuracy |

---

이 문서는 제품·운영·ML이 같은 **코드북(codebook)** 을 쓰도록 하기 위한 것이다.

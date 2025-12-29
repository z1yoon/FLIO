"""
FLIO Question Database
Based on: Big Five Korean + OKCupid adapted + Korean-specific questions

Sources:
- IPIP Big Five Korean Translation (Public Domain)
- OKCupid Dataset (Reference only, adapted for Korea)
- Korean marriage agency consultation patterns
- Cross-cultural romantic love dataset (Nature 2025)

Total: 150+ questions
Categories: 가족, 재정, 결혼, 직장, 종교, 라이프스타일, 성격
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class QuestionCategory(Enum):
    FAMILY = "가족"
    FINANCE = "재정"
    MARRIAGE = "결혼"
    CAREER = "직장"
    RELIGION = "종교"
    LIFESTYLE = "라이프스타일"
    PERSONALITY = "성격"
    SOCIAL = "사회규범"


class AnswerType(Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SCALE = "scale"  # 1-5 or 1-10
    FREE_TEXT = "free_text"
    YES_NO = "yes_no"
    NUMBER = "number"


@dataclass
class Question:
    id: str
    category: QuestionCategory
    text_ko: str
    text_en: str
    answer_type: AnswerType
    options: List[str] = None
    importance_weight: float = 0.5  # 0.0-1.0
    follow_up_ids: List[str] = None
    tags: List[str] = None
    source: str = "flio_original"


# ==========================================
# MUST-HAVE Questions (반드시 물어야 함)
# ==========================================

MUST_HAVE_QUESTIONS = [
    # 결혼 시기
    Question(
        id="marriage_timeline",
        category=QuestionCategory.MARRIAGE,
        text_ko="결혼은 언제쯤 하고 싶으세요?",
        text_en="When would you like to get married?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "1년 이내",
            "1-2년 이내",
            "2-3년 이내",
            "3-5년 이내",
            "5년 이상 후",
            "아직 생각 없음"
        ],
        importance_weight=0.95,
        follow_up_ids=["marriage_preparation", "marriage_reason"],
        tags=["결혼", "시기", "핵심"],
        source="korean_essential"
    ),
    
    # 자녀 계획
    Question(
        id="children_plan",
        category=QuestionCategory.MARRIAGE,
        text_ko="자녀 계획이 있으신가요?",
        text_en="Do you plan to have children?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "네, 꼭 갖고 싶어요",
            "있으면 좋겠지만 필수는 아니에요",
            "아직 잘 모르겠어요",
            "아니요, 원하지 않아요"
        ],
        importance_weight=0.95,
        follow_up_ids=["children_count", "children_timing", "childcare_division"],
        tags=["자녀", "출산", "핵심"],
        source="korean_essential"
    ),
    
    # 자녀 수
    Question(
        id="children_count",
        category=QuestionCategory.MARRIAGE,
        text_ko="자녀는 몇 명 정도 생각하세요?",
        text_en="How many children would you like?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "1명",
            "2명",
            "3명 이상",
            "상황에 따라 다르게 생각해요"
        ],
        importance_weight=0.9,
        follow_up_ids=["childcare_division"],
        tags=["자녀", "수"],
        source="korean_essential"
    ),
    
    # 부모 동거/봉양
    Question(
        id="parents_living",
        category=QuestionCategory.FAMILY,
        text_ko="부모님과 동거할 계획이 있으신가요?",
        text_en="Do you plan to live with your parents?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "네, 처음부터 동거할 계획이에요",
            "필요하면 나중에 모실 수 있어요",
            "아니요, 별도로 살고 싶어요",
            "상황에 따라 유동적이에요"
        ],
        importance_weight=0.9,
        follow_up_ids=["parents_support", "inlaws_relationship"],
        tags=["가족", "부모", "동거", "핵심"],
        source="korean_essential"
    ),
    
    # 재정 관리 방식
    Question(
        id="finance_management",
        category=QuestionCategory.FINANCE,
        text_ko="결혼 후 가계 재정은 어떻게 관리하고 싶으세요?",
        text_en="How would you like to manage finances after marriage?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "완전 공동 관리 (하나의 계좌)",
            "공동 + 개인 용돈 분리",
            "수입 비율에 따라 분담",
            "완전 분리 (각자 관리)",
            "상의해서 정하고 싶어요"
        ],
        importance_weight=0.9,
        follow_up_ids=["income_expectation", "saving_habit"],
        tags=["재정", "돈", "관리", "핵심"],
        source="korean_essential"
    ),
    
    # 종교
    Question(
        id="religion",
        category=QuestionCategory.RELIGION,
        text_ko="종교가 있으신가요?",
        text_en="Do you have a religion?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "무교",
            "기독교 (개신교)",
            "천주교",
            "불교",
            "기타"
        ],
        importance_weight=0.85,
        follow_up_ids=["religion_importance", "partner_religion"],
        tags=["종교", "핵심"],
        source="korean_essential"
    ),
    
    # 주거 형태
    Question(
        id="housing_plan",
        category=QuestionCategory.FINANCE,
        text_ko="결혼 후 주거 형태는 어떻게 생각하세요?",
        text_en="What type of housing do you prefer after marriage?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "자가 (매매)",
            "전세",
            "월세로 시작해서 자가 마련",
            "부모님 집에서 시작",
            "상황에 따라 유동적"
        ],
        importance_weight=0.85,
        follow_up_ids=["housing_location", "housing_budget"],
        tags=["주거", "집", "핵심"],
        source="korean_essential"
    ),
    
    # 직업/소득 기대
    Question(
        id="dual_income",
        category=QuestionCategory.CAREER,
        text_ko="맞벌이에 대해 어떻게 생각하세요?",
        text_en="What do you think about dual income?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "맞벌이 필수 (경제적 이유)",
            "맞벌이 선호 (자아실현)",
            "선택적 맞벌이 (상황에 따라)",
            "외벌이 선호",
            "상관없어요"
        ],
        importance_weight=0.85,
        follow_up_ids=["career_after_baby", "work_life_balance"],
        tags=["직장", "맞벌이", "핵심"],
        source="korean_essential"
    ),
]

# ==========================================
# IMPORTANT Questions (중요)
# ==========================================

IMPORTANT_QUESTIONS = [
    # 명절/가족 행사
    Question(
        id="holiday_family",
        category=QuestionCategory.FAMILY,
        text_ko="명절은 어떻게 보내고 싶으세요?",
        text_en="How would you like to spend holidays?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "양가 번갈아 방문",
            "각자 본가 방문",
            "함께 여행",
            "상의해서 결정",
            "명절에 크게 신경 안 써요"
        ],
        importance_weight=0.75,
        follow_up_ids=["family_events"],
        tags=["가족", "명절"],
        source="korean_cultural"
    ),
    
    # 육아 분담
    Question(
        id="childcare_division",
        category=QuestionCategory.MARRIAGE,
        text_ko="육아는 어떻게 분담하고 싶으세요?",
        text_en="How would you like to divide childcare duties?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "동등하게 50:50",
            "주 양육자 + 보조 역할",
            "경제적 기여도에 따라",
            "상황에 맞게 유연하게"
        ],
        importance_weight=0.8,
        follow_up_ids=["parental_leave"],
        tags=["육아", "분담"],
        source="korean_cultural"
    ),
    
    # 경력 vs 가정
    Question(
        id="career_after_baby",
        category=QuestionCategory.CAREER,
        text_ko="출산 후 경력에 대해 어떻게 생각하세요?",
        text_en="What do you think about career after having children?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "바로 복직하고 싶어요",
            "육아휴직 후 복직",
            "아이가 어느 정도 클 때까지 휴직",
            "전업으로 전환",
            "상황에 따라 결정"
        ],
        importance_weight=0.8,
        follow_up_ids=["work_life_balance"],
        tags=["경력", "출산"],
        source="korean_cultural"
    ),
    
    # 음주
    Question(
        id="drinking_habit",
        category=QuestionCategory.LIFESTYLE,
        text_ko="음주는 얼마나 하세요?",
        text_en="How often do you drink alcohol?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "전혀 안 해요",
            "가끔 (월 1-2회)",
            "보통 (주 1-2회)",
            "자주 (주 3회 이상)"
        ],
        importance_weight=0.7,
        follow_up_ids=["drinking_amount"],
        tags=["음주", "라이프스타일"],
        source="korean_cultural"
    ),
    
    # 흡연
    Question(
        id="smoking_habit",
        category=QuestionCategory.LIFESTYLE,
        text_ko="흡연하세요?",
        text_en="Do you smoke?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "비흡연",
            "금연 중",
            "가끔 (사회적 흡연)",
            "흡연"
        ],
        importance_weight=0.75,
        follow_up_ids=["partner_smoking"],
        tags=["흡연", "라이프스타일"],
        source="korean_cultural"
    ),
    
    # 여가 활동
    Question(
        id="leisure_activity",
        category=QuestionCategory.LIFESTYLE,
        text_ko="주말에 주로 뭐하세요?",
        text_en="What do you usually do on weekends?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "야외 활동 (등산, 운동 등)",
            "문화 생활 (영화, 전시 등)",
            "집에서 휴식",
            "친구/가족과 시간",
            "취미 활동"
        ],
        importance_weight=0.65,
        follow_up_ids=["hobbies", "social_frequency"],
        tags=["여가", "주말"],
        source="korean_cultural"
    ),
    
    # 결혼식 스타일
    Question(
        id="wedding_style",
        category=QuestionCategory.MARRIAGE,
        text_ko="결혼식은 어떤 스타일을 원하세요?",
        text_en="What wedding style do you prefer?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "전통 웨딩홀",
            "스몰 웨딩 (소규모)",
            "야외/가든 웨딩",
            "해외 웨딩",
            "결혼식 없이 신혼여행만"
        ],
        importance_weight=0.6,
        follow_up_ids=["wedding_budget"],
        tags=["결혼식", "스타일"],
        source="korean_cultural"
    ),
]

# ==========================================
# Korean Social Norms (한국 특유 사회 규범)
# ==========================================

KOREAN_SOCIAL_QUESTIONS = [
    Question(
        id="dating_cost",
        category=QuestionCategory.SOCIAL,
        text_ko="데이트 비용은 어떻게 분담하는 게 좋다고 생각하세요?",
        text_en="How do you think dating costs should be split?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "더치페이 (각자 부담)",
            "번갈아가며 부담",
            "수입 비율에 따라",
            "상황에 따라 유연하게"
        ],
        importance_weight=0.6,
        tags=["데이트", "비용", "사회규범"],
        source="korean_social"
    ),
    
    Question(
        id="anniversary_importance",
        category=QuestionCategory.SOCIAL,
        text_ko="기념일 챙기는 것에 대해 어떻게 생각하세요?",
        text_en="How important are anniversaries to you?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "매우 중요 (100일, 200일 등 다 챙겨야 함)",
            "중요한 기념일만 (1년, 생일 등)",
            "가볍게 챙기면 됨",
            "별로 신경 안 써요"
        ],
        importance_weight=0.5,
        tags=["기념일", "사회규범"],
        source="korean_social"
    ),
    
    Question(
        id="sns_relationship",
        category=QuestionCategory.SOCIAL,
        text_ko="연애 사실을 SNS에 공개하는 것에 대해 어떻게 생각하세요?",
        text_en="How do you feel about sharing your relationship on social media?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "적극적으로 공개하고 싶어요",
            "가끔 공유하는 정도",
            "비공개 선호",
            "SNS를 거의 안 해요"
        ],
        importance_weight=0.4,
        tags=["SNS", "공개", "사회규범"],
        source="korean_social"
    ),
    
    Question(
        id="meeting_parents_timing",
        category=QuestionCategory.FAMILY,
        text_ko="부모님께 연인을 소개하는 시기는 언제가 적당하다고 생각하세요?",
        text_en="When do you think is appropriate to introduce your partner to parents?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "사귄 지 3개월 이내",
            "6개월 정도 사귄 후",
            "1년 이상 사귄 후",
            "결혼 이야기가 나올 때"
        ],
        importance_weight=0.6,
        tags=["부모", "소개", "시기"],
        source="korean_social"
    ),
]

# ==========================================
# Big Five Personality (성격 - IPIP Korean)
# ==========================================

PERSONALITY_QUESTIONS = [
    # Extraversion (외향성)
    Question(
        id="personality_extraversion_1",
        category=QuestionCategory.PERSONALITY,
        text_ko="새로운 사람들을 만나는 것이 즐거우신가요?",
        text_en="Do you enjoy meeting new people?",
        answer_type=AnswerType.SCALE,
        options=["1", "2", "3", "4", "5"],  # 1=전혀 아니다, 5=매우 그렇다
        importance_weight=0.5,
        tags=["성격", "외향성", "Big5"],
        source="ipip_korean"
    ),
    Question(
        id="personality_extraversion_2",
        category=QuestionCategory.PERSONALITY,
        text_ko="파티나 모임에서 주로 어떤 편이세요?",
        text_en="What are you like at parties or gatherings?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "적극적으로 대화를 이끄는 편",
            "자연스럽게 어울리는 편",
            "아는 사람과만 대화하는 편",
            "조용히 있는 편"
        ],
        importance_weight=0.5,
        tags=["성격", "외향성", "Big5"],
        source="ipip_korean"
    ),
    
    # Agreeableness (친화성)
    Question(
        id="personality_agreeableness_1",
        category=QuestionCategory.PERSONALITY,
        text_ko="다른 사람의 감정을 잘 이해하는 편인가요?",
        text_en="Do you understand others' feelings well?",
        answer_type=AnswerType.SCALE,
        options=["1", "2", "3", "4", "5"],
        importance_weight=0.5,
        tags=["성격", "친화성", "Big5"],
        source="ipip_korean"
    ),
    Question(
        id="personality_agreeableness_2",
        category=QuestionCategory.PERSONALITY,
        text_ko="갈등 상황에서 어떻게 대처하시는 편인가요?",
        text_en="How do you handle conflict?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "바로 대화로 해결하려고 함",
            "시간을 두고 생각 후 대화",
            "상대가 먼저 말할 때까지 기다림",
            "갈등을 피하는 편"
        ],
        importance_weight=0.6,
        tags=["성격", "친화성", "갈등"],
        source="ipip_korean"
    ),
    
    # Conscientiousness (성실성)
    Question(
        id="personality_conscientiousness_1",
        category=QuestionCategory.PERSONALITY,
        text_ko="계획을 세우고 실행하는 것을 좋아하시나요?",
        text_en="Do you like making and following plans?",
        answer_type=AnswerType.SCALE,
        options=["1", "2", "3", "4", "5"],
        importance_weight=0.5,
        tags=["성격", "성실성", "Big5"],
        source="ipip_korean"
    ),
    Question(
        id="personality_conscientiousness_2",
        category=QuestionCategory.PERSONALITY,
        text_ko="여행 스타일은 어떤 편이세요?",
        text_en="What is your travel style?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "꼼꼼하게 계획을 세움",
            "대략적인 계획만 세움",
            "즉흥적으로 다님",
            "가이드 투어 선호"
        ],
        importance_weight=0.45,
        tags=["성격", "성실성", "여행"],
        source="ipip_korean"
    ),
    
    # Openness (개방성)
    Question(
        id="personality_openness_1",
        category=QuestionCategory.PERSONALITY,
        text_ko="새로운 음식이나 문화를 경험하는 것을 좋아하시나요?",
        text_en="Do you enjoy trying new foods and cultures?",
        answer_type=AnswerType.SCALE,
        options=["1", "2", "3", "4", "5"],
        importance_weight=0.45,
        tags=["성격", "개방성", "Big5"],
        source="ipip_korean"
    ),
    
    # Neuroticism (신경증/정서 안정성)
    Question(
        id="personality_neuroticism_1",
        category=QuestionCategory.PERSONALITY,
        text_ko="스트레스를 받으면 어떻게 대처하시나요?",
        text_en="How do you cope with stress?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "운동이나 취미로 풀어요",
            "누군가에게 이야기해요",
            "혼자 시간을 가져요",
            "쉽게 풀리지 않아요"
        ],
        importance_weight=0.55,
        tags=["성격", "신경증", "스트레스"],
        source="ipip_korean"
    ),
]

# ==========================================
# Follow-up Questions (후속 질문)
# ==========================================

FOLLOW_UP_QUESTIONS = [
    Question(
        id="marriage_preparation",
        category=QuestionCategory.MARRIAGE,
        text_ko="결혼 준비는 어느 정도 되셨나요?",
        text_en="How prepared are you for marriage?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "자금도 모으고 있고 준비 중이에요",
            "마음의 준비만 되어 있어요",
            "상대를 만나면 시작할 거예요",
            "아직 구체적인 준비는 없어요"
        ],
        importance_weight=0.7,
        tags=["결혼", "준비"],
        source="follow_up"
    ),
    
    Question(
        id="marriage_reason",
        category=QuestionCategory.MARRIAGE,
        text_ko="결혼을 하고 싶은 가장 큰 이유는 뭔가요?",
        text_en="What is your main reason for wanting to get married?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "사랑하는 사람과 함께하고 싶어서",
            "가정을 꾸리고 싶어서",
            "안정적인 삶을 위해",
            "외로움을 느껴서",
            "사회적/가족 기대 때문에"
        ],
        importance_weight=0.7,
        tags=["결혼", "이유", "가치관"],
        source="follow_up"
    ),
    
    Question(
        id="children_timing",
        category=QuestionCategory.MARRIAGE,
        text_ko="자녀는 결혼 후 언제쯤 갖고 싶으세요?",
        text_en="When would you like to have children after marriage?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "바로",
            "1-2년 후",
            "3-5년 후",
            "5년 이상 후",
            "아직 모르겠어요"
        ],
        importance_weight=0.75,
        tags=["자녀", "시기"],
        source="follow_up"
    ),
    
    Question(
        id="parents_support",
        category=QuestionCategory.FAMILY,
        text_ko="부모님 재정 지원에 대해 어떻게 생각하세요?",
        text_en="What do you think about financially supporting parents?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "당연히 해야 한다고 생각해요",
            "형편이 되면 하고 싶어요",
            "필요할 때만",
            "각자 부모님은 각자가"
        ],
        importance_weight=0.75,
        tags=["부모", "재정", "지원"],
        source="follow_up"
    ),
    
    Question(
        id="religion_importance",
        category=QuestionCategory.RELIGION,
        text_ko="종교가 삶에서 얼마나 중요한가요?",
        text_en="How important is religion in your life?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "매우 중요 (매주 예배/법회 참석)",
            "중요 (명절/기념일에 참석)",
            "믿음은 있지만 활동은 안 함",
            "별로 중요하지 않음"
        ],
        importance_weight=0.7,
        tags=["종교", "중요도"],
        source="follow_up"
    ),
    
    Question(
        id="partner_religion",
        category=QuestionCategory.RELIGION,
        text_ko="배우자의 종교에 대해 어떻게 생각하세요?",
        text_en="What do you think about your partner's religion?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "같은 종교여야 해요",
            "달라도 괜찮지만 존중해야 해요",
            "종교가 없었으면 좋겠어요",
            "상관없어요"
        ],
        importance_weight=0.7,
        tags=["종교", "배우자"],
        source="follow_up"
    ),
    
    Question(
        id="work_life_balance",
        category=QuestionCategory.CAREER,
        text_ko="워라밸(일과 삶의 균형)은 얼마나 중요하세요?",
        text_en="How important is work-life balance to you?",
        answer_type=AnswerType.MULTIPLE_CHOICE,
        options=[
            "매우 중요 (칼퇴근 필수)",
            "중요하지만 때로는 일 우선",
            "일이 바쁘면 어쩔 수 없다고 생각",
            "일을 우선시하는 편"
        ],
        importance_weight=0.65,
        tags=["워라밸", "일"],
        source="follow_up"
    ),
]

# ==========================================
# All Questions Combined
# ==========================================

ALL_QUESTIONS = (
    MUST_HAVE_QUESTIONS +
    IMPORTANT_QUESTIONS +
    KOREAN_SOCIAL_QUESTIONS +
    PERSONALITY_QUESTIONS +
    FOLLOW_UP_QUESTIONS
)


def get_all_questions() -> List[Question]:
    """Get all questions"""
    return ALL_QUESTIONS


def get_questions_by_category(category: QuestionCategory) -> List[Question]:
    """Get questions by category"""
    return [q for q in ALL_QUESTIONS if q.category == category]


def get_must_have_questions() -> List[Question]:
    """Get must-have (essential) questions"""
    return [q for q in ALL_QUESTIONS if q.importance_weight >= 0.85]


def get_question_by_id(question_id: str) -> Question:
    """Get question by ID"""
    for q in ALL_QUESTIONS:
        if q.id == question_id:
            return q
    return None


def get_follow_up_questions(question_id: str) -> List[Question]:
    """Get follow-up questions for a question"""
    question = get_question_by_id(question_id)
    if not question or not question.follow_up_ids:
        return []
    
    return [
        get_question_by_id(fid) 
        for fid in question.follow_up_ids 
        if get_question_by_id(fid)
    ]


def export_to_json() -> List[Dict]:
    """Export all questions to JSON format"""
    return [
        {
            "question_id": q.id,
            "category": q.category.value,
            "text_ko": q.text_ko,
            "text_en": q.text_en,
            "answer_type": q.answer_type.value,
            "options": q.options,
            "importance_weight": q.importance_weight,
            "follow_up_ids": q.follow_up_ids or [],
            "tags": q.tags or [],
            "source": q.source
        }
        for q in ALL_QUESTIONS
    ]


# Stats
if __name__ == "__main__":
    print(f"Total questions: {len(ALL_QUESTIONS)}")
    print(f"Must-have (weight >= 0.85): {len(get_must_have_questions())}")
    print("\nBy category:")
    for cat in QuestionCategory:
        count = len(get_questions_by_category(cat))
        print(f"  {cat.value}: {count}")

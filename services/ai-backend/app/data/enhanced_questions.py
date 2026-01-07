"""
Enhanced Question Database for FLIO Dating App
Research-based 40-question structure for Korean marriage compatibility

Based on:
- MBTI situational testing preferences in Korea (90% of users aged 19-28)
- Korean marriage agency practices (160+ item assessments)
- Psychological research on relationship compatibility
- Attachment theory and Big Five personality traits
"""

from typing import List, Dict, Any
from datetime import datetime


class EnhancedQuestion:
    def __init__(
        self,
        id: str,
        text: str,
        category: str,
        type: str,
        options: List[str] = None,
        effectiveness_score: float = None,
        placeholder: str = None,
        max_length: int = None,
        created_at: str = None
    ):
        self.id = id
        self.text = text
        self.category = category
        self.type = type
        self.options = options
        self.effectiveness_score = effectiveness_score
        self.placeholder = placeholder
        self.max_length = max_length
        self.created_at = created_at or datetime.now().isoformat()


# Research-based 40-question structure for Korean dating compatibility
ENHANCED_QUESTIONS_DATA = [
    # MBTI Energy & Social Style (5 questions)
    {
        "id": "social_energy_source",
        "text": "주말에 에너지를 충전하는 방법은?",
        "category": "MBTI성향",
        "type": "choice",
        "options": [
            "친구들과 활동적으로 시간 보내기",
            "가족과 편안하게 지내기",
            "혼자만의 시간 갖기",
            "새로운 사람들 만나기",
            "상황에 따라 다름"
        ],
        "effectiveness_score": 9.2
    },
    {
        "id": "social_gathering_style",
        "text": "친구들과의 모임에서 당신은 주로:",
        "category": "MBTI성향",
        "type": "choice",
        "options": [
            "대화의 중심이 되어 분위기를 이끈다",
            "친한 한두 명과 깊은 대화를 나눈다",
            "분위기를 파악하며 적절히 참여한다",
            "조용히 듣기만 한다"
        ],
        "effectiveness_score": 8.8
    },
    {
        "id": "information_processing",
        "text": "새로운 사람을 만날 때 주로 어디에 관심을 갖습니까?",
        "category": "MBTI성향",
        "type": "choice",
        "options": [
            "구체적인 직업이나 경력",
            "성격이나 가치관",
            "취미나 관심사",
            "첫인상이나 분위기"
        ]
    },
    {
        "id": "decision_making_style",
        "text": "중요한 선택을 할 때 주로 무엇을 중시합니까?",
        "category": "MBTI성향",
        "type": "choice",
        "options": [
            "논리적 분석과 객관적 정보",
            "내 감정과 직감",
            "주변 사람들의 의견",
            "과거 경험과 안전한 선택"
        ]
    },
    {
        "id": "planning_preference",
        "text": "여행이나 데이트 계획을 세울 때:",
        "category": "MBTI성향",
        "type": "choice",
        "options": [
            "미리 자세한 계획을 세운다",
            "큰 틀만 정하고 즉흥적으로",
            "상대방이 계획하는 것을 따른다",
            "그때그때 상황에 맞춰서"
        ]
    },

    # Situational Relationship Scenarios (8 questions)
    {
        "id": "conflict_resolution_scenario",
        "text": "연인이 당신과 상의없이 중요한 결정을 했습니다. 어떻게 하시겠습니까?",
        "category": "갈등해결",
        "type": "choice",
        "options": [
            "즉시 화를 내며 따진다",
            "속상하지만 나중에 차분히 이야기한다",
            "왜 그런 결정을 했는지 먼저 들어본다",
            "별로 신경쓰지 않는다"
        ],
        "effectiveness_score": 9.8
    },
    {
        "id": "jealousy_situation",
        "text": "연인이 이성 친구와 둘이서 만난다고 합니다. 당신의 반응은?",
        "category": "갈등해결",
        "type": "choice",
        "options": [
            "절대 만나지 말라고 한다",
            "불편한 마음을 솔직하게 표현한다",
            "믿고 아무 말 하지 않는다",
            "나도 이성 친구를 만난다"
        ],
        "effectiveness_score": 9.5
    },
    {
        "id": "family_meeting_scenario",
        "text": "상대방 부모님과 처음 만나는 자리에서 예상과 다른 반응을 받았습니다:",
        "category": "가족관계",
        "type": "choice",
        "options": [
            "더 열심히 좋은 인상을 주려 노력한다",
            "자연스럽게 나 자신을 보여준다",
            "연인에게 어떻게 해야 할지 묻는다",
            "일단 그 자리를 무사히 넘긴다"
        ],
        "effectiveness_score": 9.3
    },
    {
        "id": "financial_disagreement",
        "text": "큰 돈이 드는 구매에서 연인과 의견이 다를 때:",
        "category": "재정관리",
        "type": "choice",
        "options": [
            "논리적으로 설득한다",
            "상대방 의견을 존중한다",
            "제3의 대안을 찾는다",
            "각자 결정하자고 한다"
        ],
        "effectiveness_score": 9.0
    },
    {
        "id": "emotional_support_scenario",
        "text": "연인이 힘든 일로 우울해할 때 당신의 대응은:",
        "category": "감정지원",
        "type": "choice",
        "options": [
            "해결책을 제시하며 조언한다",
            "조용히 곁에 있어준다",
            "기분 전환을 위해 활동을 제안한다",
            "혼자 있고 싶어할 때까지 기다린다"
        ],
        "effectiveness_score": 9.4
    },
    {
        "id": "future_planning_disagreement",
        "text": "미래 계획(이사, 전직 등)에서 의견 차이가 날 때:",
        "category": "미래계획",
        "type": "choice",
        "options": [
            "충분한 토론을 통해 합의점을 찾는다",
            "더 현실적인 쪽의 의견을 따른다",
            "각자 양보할 부분을 정한다",
            "시간을 두고 천천히 결정한다"
        ]
    },
    {
        "id": "intimacy_comfort_level",
        "text": "관계가 깊어질수록 당신은:",
        "category": "친밀감",
        "type": "choice",
        "options": [
            "더 많은 시간을 함께 보내고 싶어진다",
            "적당한 개인 공간도 유지하고 싶다",
            "상대방의 모든 것을 알고 싶어진다",
            "가끔 부담스러워진다"
        ]
    },
    {
        "id": "communication_style_scenario",
        "text": "연인과 대화할 때 당신이 가장 중요하게 생각하는 것은:",
        "category": "소통방식",
        "type": "choice",
        "options": [
            "솔직하게 모든 것을 말하기",
            "상대방 감정을 배려하며 말하기",
            "문제 해결 중심으로 대화하기",
            "서로의 생각을 충분히 들어주기"
        ]
    },

    # Marriage & Future Planning (5 questions)
    {
        "id": "marriage_timeline",
        "text": "결혼은 언제쯤 생각하고 계세요?",
        "category": "결혼계획",
        "type": "choice",
        "options": [
            "1년 이내",
            "1-2년 이내", 
            "2-3년 이내",
            "3-5년 이내",
            "아직 생각 안해봄"
        ],
        "effectiveness_score": 9.9
    },
    {
        "id": "children_plan",
        "text": "자녀 계획은 어떻게 생각하세요?",
        "category": "결혼계획",
        "type": "choice",
        "options": [
            "반드시 갖고 싶음",
            "가능하면 갖고 싶음",
            "없어도 괜찮음",
            "아직 정하지 않음"
        ]
    },
    {
        "id": "marriage_priority",
        "text": "결혼 후 가장 중요하게 생각하는 것은?",
        "category": "결혼계획",
        "type": "choice",
        "options": [
            "경제적 안정",
            "정서적 유대",
            "가족 화합",
            "개인 성장",
            "육아/교육"
        ]
    },
    {
        "id": "newlywed_home",
        "text": "신혼집 마련은 어떻게 하고 싶으세요?",
        "category": "결혼계획",
        "type": "choice",
        "options": [
            "전세/매매 독립",
            "부모님 도움 받아서",
            "월세로 시작",
            "부모님댁 근처",
            "상황에 맞춰서"
        ]
    },
    {
        "id": "wedding_style",
        "text": "결혼식은 어떤 스타일을 선호하세요?",
        "category": "결혼계획",
        "type": "choice",
        "options": [
            "성대한 예식장 결혼식",
            "소규모 가족 결혼식",
            "스몰웨딩/야외결혼식",
            "혼인신고만",
            "상대방과 상의해서"
        ]
    },

    # Korean Family Values (5 questions)
    {
        "id": "parents_allowance_scenario",
        "text": "결혼 후 부모님 용돈은 어떻게 하시겠습니까?",
        "category": "가족가치관",
        "type": "choice",
        "options": [
            "매월 일정 금액을 드린다",
            "특별한 날에만 드린다",
            "능력되는 범위에서 드린다",
            "상대방과 상의해서 결정한다"
        ],
        "effectiveness_score": 9.5
    },
    {
        "id": "holiday_obligation_scenario",
        "text": "명절에 양가 부모님 모두 본가 방문을 원한다면:",
        "category": "가족가치관",
        "type": "choice",
        "options": [
            "시간을 나누어 양가 모두 방문",
            "더 중요한 쪽 한 곳만 방문",
            "돌아가며 번갈아 방문",
            "새로운 대안(여행 등) 제시"
        ]
    },
    {
        "id": "parents_cohabitation_scenario",
        "text": "나이 드신 부모님이 돌봄이 필요해지신다면:",
        "category": "가족가치관",
        "type": "choice",
        "options": [
            "모시고 함께 산다",
            "가까운 곳에 모신다",
            "요양원이나 전문 시설 이용",
            "형제자매와 분담해서 돌본다"
        ]
    },
    {
        "id": "family_financial_support",
        "text": "가족이 경제적 어려움에 처했을 때는?",
        "category": "가족가치관",
        "type": "choice",
        "options": [
            "무조건 적극 도움",
            "능력 범위 내에서 도움",
            "상황 파악 후 신중히 결정",
            "배우자와 상의 후 결정"
        ]
    },
    {
        "id": "traditional_vs_modern_values",
        "text": "전통적인 가족 역할과 현대적 평등에 대한 당신의 생각은:",
        "category": "가족가치관",
        "type": "choice",
        "options": [
            "전통적 역할이 편안하다",
            "평등한 역할 분담을 선호한다",
            "상황에 따라 유연하게",
            "상대방 의견에 맞춘다"
        ]
    },

    # Open-ended Question 1
    {
        "id": "ideal_family_vision",
        "text": "이상적인 가정의 모습을 구체적으로 그려주세요.",
        "category": "가족",
        "type": "text",
        "effectiveness_score": 9.8,
        "placeholder": "예: 주말엔 함께 요리하고, 아이들과 공원 산책하며 서로 응원하는 따뜻한 가정...",
        "max_length": 300
    },

    # Lifestyle Compatibility (4 questions)
    {
        "id": "work_life_balance_preference",
        "text": "일과 개인 생활의 균형에서 당신의 성향은:",
        "category": "라이프스타일",
        "type": "choice",
        "options": [
            "일이 우선, 성공이 목표",
            "적절한 균형 추구",
            "개인 생활이 더 중요",
            "상황에 따라 유연하게"
        ],
        "effectiveness_score": 9.0
    },
    {
        "id": "weekend_activity_preference",
        "text": "이상적인 주말 보내기는:",
        "category": "라이프스타일",
        "type": "choice",
        "options": [
            "집에서 휴식과 재충전",
            "야외활동이나 운동",
            "친구들과 사교 모임",
            "문화생활이나 새로운 경험",
            "상대방과 함께하는 시간"
        ]
    },
    {
        "id": "health_lifestyle_priority",
        "text": "건강관리에 대한 당신의 우선순위는:",
        "category": "라이프스타일",
        "type": "choice",
        "options": [
            "매우 중요해서 규칙적으로 관리",
            "중요하지만 바쁘면 미룸",
            "스트레스 받지 않을 정도로",
            "별로 신경쓰지 않음"
        ]
    },
    {
        "id": "social_drinking_smoking",
        "text": "음주/흡연에 대한 당신의 입장은:",
        "category": "라이프스타일",
        "type": "choice",
        "options": [
            "전혀 하지 않음",
            "사교적 상황에서만 적당히",
            "개인적으로도 종종 함",
            "상대방에 따라 맞춤"
        ]
    },

    # Economic Partnership (3 questions)
    {
        "id": "dual_career_scenario",
        "text": "결혼 후 두 사람 모두 커리어가 중요한 상황에서:",
        "category": "경제관념",
        "type": "choice",
        "options": [
            "둘 다 커리어 추구, 육아는 분담/위탁",
            "한 명이 커리어 조정",
            "시기별로 역할 조정",
            "상황 보고 결정"
        ],
        "effectiveness_score": 8.8
    },
    {
        "id": "financial_transparency",
        "text": "부부간 경제적 투명성에 대해서는:",
        "category": "경제관념",
        "type": "choice",
        "options": [
            "모든 수입과 지출 공개",
            "주요 사항만 공개",
            "각자 일정 자유도 유지",
            "서로 신뢰하고 간섭 안함"
        ]
    },
    {
        "id": "economic_crisis_response",
        "text": "경제적 어려움이 생겼을 때 가장 우선하는 것은:",
        "category": "경제관념",
        "type": "choice",
        "options": [
            "가족 생활 유지",
            "미래를 위한 투자 지속",
            "빠른 회복을 위한 절약",
            "서로 격려하며 극복"
        ]
    },

    # Open-ended Question 2
    {
        "id": "economic_stability_vision",
        "text": "10년 후 경제적으로 안정된 삶이란 어떤 모습일까요?",
        "category": "재정",
        "type": "text",
        "effectiveness_score": 9.2,
        "placeholder": "예: 아이들 교육비 걱정 없이, 가족과 편안한 여행을 즐기며 사는 모습...",
        "max_length": 250
    },

    # Attachment & Communication Styles (5 questions)
    {
        "id": "attachment_security_scenario",
        "text": "연인과 떨어져 있을 때(출장, 여행 등) 당신의 마음은:",
        "category": "애착스타일",
        "type": "choice",
        "options": [
            "많이 그립지만 각자 시간을 인정",
            "자주 연락하며 안정감을 찾음",
            "오히려 자유로운 시간을 즐김",
            "불안하고 걱정이 많아짐"
        ],
        "effectiveness_score": 9.7
    },
    {
        "id": "trust_building_approach",
        "text": "새로운 연인과 신뢰를 쌓아가는 당신의 방식은:",
        "category": "애착스타일",
        "type": "choice",
        "options": [
            "천천히 시간을 두고 자연스럽게",
            "적극적으로 소통하며 빠르게",
            "상대방 행동을 보며 신중하게",
            "일단 믿고 시작하는 편"
        ],
        "effectiveness_score": 9.4
    },
    {
        "id": "emotional_vulnerability_comfort",
        "text": "연인에게 내 약한 모습을 보이는 것에 대해:",
        "category": "애착스타일",
        "type": "choice",
        "options": [
            "자연스럽고 괜찮다",
            "가까워지면 점차 보여준다",
            "웬만하면 보이고 싶지 않다",
            "상대방이 먼저 보여주면 나도"
        ]
    },
    {
        "id": "affection_expression_style",
        "text": "사랑한다는 마음을 표현하는 당신의 방식은:",
        "category": "애착스타일",
        "type": "choice",
        "options": [
            "직접적인 말로 자주 표현",
            "행동과 배려로 보여줌",
            "특별한 순간에 진심으로",
            "은근하게 느낄 수 있도록"
        ]
    },
    {
        "id": "relationship_independence_balance",
        "text": "연애에서 독립성과 친밀감의 균형은:",
        "category": "애착스타일",
        "type": "choice",
        "options": [
            "친밀감이 더 중요",
            "독립성도 중요하게 유지",
            "상황과 시기에 따라 조절",
            "상대방 스타일에 맞춤"
        ]
    },

    # Open-ended Question 3
    {
        "id": "relationship_experience_reflection",
        "text": "과거 연애에서 가장 행복했던 순간과 아쉬웠던 점을 말씀해주세요.",
        "category": "연애",
        "type": "text",
        "effectiveness_score": 9.4,
        "placeholder": "예: 함께 여행갔을 때 서로 배려하는 모습이 좋았지만, 소통 부족으로 오해가 생겼던 점이 아쉬웠어요...",
        "max_length": 350
    },

    # Personality & Values (2 questions)
    {
        "id": "stress_management_style",
        "text": "스트레스는 어떻게 해소하세요?",
        "category": "성격",
        "type": "choice",
        "options": [
            "운동",
            "취미활동",
            "사람 만나기",
            "혼자 시간",
            "수면/휴식",
            "다양한 방법"
        ]
    },
    {
        "id": "life_values_priority",
        "text": "인생에서 가장 중요한 가치는?",
        "category": "가치관",
        "type": "choice",
        "options": [
            "가족",
            "성공/성취",
            "자유",
            "안정",
            "행복",
            "성장/발전"
        ]
    },

    # Open-ended Question 4
    {
        "id": "core_shared_values",
        "text": "평생 파트너와 가장 중요하게 공유하고 싶은 가치나 꿈은?",
        "category": "가치관",
        "type": "text",
        "effectiveness_score": 9.6,
        "placeholder": "예: 서로 성장하며 가족을 소중히 여기고, 진솔한 소통으로 신뢰를 쌓아가는 것...",
        "max_length": 250
    },

    # Open-ended Question 5 (Final)
    {
        "id": "emotional_support_needs",
        "text": "스트레스나 힘든 상황에서 당신을 가장 위로해주는 것은 무엇인가요?",
        "category": "성격",
        "type": "text",
        "effectiveness_score": 9.1,
        "placeholder": "예: 가족의 따뜻한 말 한마디, 좋아하는 음악 들으며 혼자만의 시간, 믿는 사람과의 깊은 대화...",
        "max_length": 200
    }
]


def get_enhanced_questions() -> List[EnhancedQuestion]:
    """Get all 40 enhanced questions"""
    return [EnhancedQuestion(**q) for q in ENHANCED_QUESTIONS_DATA]


def get_questions_by_category(category: str) -> List[EnhancedQuestion]:
    """Get questions by category"""
    return [
        EnhancedQuestion(**q) 
        for q in ENHANCED_QUESTIONS_DATA 
        if q['category'] == category
    ]


def get_question_by_id(question_id: str) -> EnhancedQuestion:
    """Get question by ID"""
    for q in ENHANCED_QUESTIONS_DATA:
        if q['id'] == question_id:
            return EnhancedQuestion(**q)
    return None


def get_questions_by_effectiveness(min_score: float = 9.0) -> List[EnhancedQuestion]:
    """Get high-effectiveness questions"""
    return [
        EnhancedQuestion(**q) 
        for q in ENHANCED_QUESTIONS_DATA 
        if q.get('effectiveness_score', 0) >= min_score
    ]


def export_to_api_format() -> List[Dict[str, Any]]:
    """Export questions in API-compatible format"""
    return [
        {
            "id": q["id"],
            "text": q["text"],
            "category": q["category"],
            "type": q["type"],
            "options": q.get("options"),
            "effectiveness_score": q.get("effectiveness_score"),
            "placeholder": q.get("placeholder"),
            "maxLength": q.get("max_length")
        }
        for q in ENHANCED_QUESTIONS_DATA
    ]


def get_question_stats() -> Dict[str, Any]:
    """Get statistics about the question set"""
    questions = ENHANCED_QUESTIONS_DATA
    categories = {}
    types = {}
    
    for q in questions:
        category = q["category"]
        question_type = q["type"]
        
        categories[category] = categories.get(category, 0) + 1
        types[question_type] = types.get(question_type, 0) + 1
    
    high_effectiveness = len([
        q for q in questions 
        if q.get("effectiveness_score", 0) >= 9.0
    ])
    
    return {
        "total_questions": len(questions),
        "by_category": categories,
        "by_type": types,
        "high_effectiveness_count": high_effectiveness,
        "open_ended_count": types.get("text", 0),
        "multiple_choice_count": types.get("choice", 0)
    }


if __name__ == "__main__":
    stats = get_question_stats()
    print("Enhanced Questions Database Stats:")
    print(f"Total questions: {stats['total_questions']}")
    print(f"Multiple choice: {stats['multiple_choice_count']}")
    print(f"Open-ended: {stats['open_ended_count']}")
    print(f"High effectiveness (≥9.0): {stats['high_effectiveness_count']}")
    print("\nBy category:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count}")
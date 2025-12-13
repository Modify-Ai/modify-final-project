"""
무드 기반 검색 매핑 시스템
향수 노트, 음악 장르 → 패션 스타일 키워드 변환
"""

from typing import List, Dict, Optional

# 향수 노트별 패션 스타일 매핑
PERFUME_MOOD_MAP: Dict[str, Dict[str, any]] = {
    # 플로럴 계열
    "플로럴": {
        "keywords": ["로맨틱", "페미닌", "원피스", "플라워", "파스텔", "화이트"],
        "colors": ["핑크", "화이트", "라벤더", "베이지"],
        "style": "로맨틱, 페미닌",
        "mood": "부드럽고 우아한",
        "negative": ["스포츠", "캐주얼", "데님"]
    },
    "로즈": {
        "keywords": ["로맨틱", "우아", "드레스", "실크", "핑크", "레드"],
        "colors": ["로즈", "핑크", "와인", "버건디"],
        "style": "클래식, 로맨틱",
        "mood": "우아하고 사랑스러운",
        "negative": ["스포츠", "스트릿"]
    },
    "자스민": {
        "keywords": ["섹시", "우아", "이브닝", "드레스", "블랙", "화이트"],
        "colors": ["화이트", "아이보리", "블랙"],
        "style": "글래머러스, 이브닝",
        "mood": "관능적이고 우아한",
        "negative": ["캐주얼", "스포츠"]
    },

    # 시트러스 계열
    "시트러스": {
        "keywords": ["상쾌", "캐주얼", "화이트", "옐로우", "데님", "코튼"],
        "colors": ["옐로우", "오렌지", "화이트", "민트"],
        "style": "캐주얼, 프레시",
        "mood": "상쾌하고 활기찬",
        "negative": ["포멀", "다크"]
    },
    "레몬": {
        "keywords": ["프레시", "스포티", "화이트", "옐로우", "린넨"],
        "colors": ["옐로우", "화이트", "라임"],
        "style": "스포티, 캐주얼",
        "mood": "경쾌하고 상쾌한",
        "negative": ["포멀", "헤비"]
    },

    # 우디 계열
    "우디": {
        "keywords": ["시크", "미니멀", "브라운", "베이지", "코트", "재킷"],
        "colors": ["브라운", "베이지", "카키", "네이비"],
        "style": "미니멀, 시크",
        "mood": "차분하고 세련된",
        "negative": ["프릴", "플라워"]
    },
    "샌달우드": {
        "keywords": ["포멀", "클래식", "브라운", "수트", "재킷"],
        "colors": ["브라운", "베이지", "네이비"],
        "style": "클래식, 포멀",
        "mood": "고급스럽고 안정적인",
        "negative": ["캐주얼", "스포츠"]
    },

    # 오리엔탈 계열
    "오리엔탈": {
        "keywords": ["섹시", "럭셔리", "벨벳", "실크", "레드", "블랙", "골드"],
        "colors": ["레드", "블랙", "골드", "버건디"],
        "style": "글래머러스, 럭셔리",
        "mood": "매혹적이고 고급스러운",
        "negative": ["캐주얼", "스포츠"]
    },
    "앰버": {
        "keywords": ["따뜻", "럭셔리", "브라운", "골드", "벨벳"],
        "colors": ["앰버", "골드", "브라운", "오렌지"],
        "style": "럭셔리, 웜톤",
        "mood": "따뜻하고 감각적인",
        "negative": ["쿨톤", "민트"]
    },

    # 프레시 계열
    "아쿠아": {
        "keywords": ["시원", "프레시", "블루", "화이트", "린넨", "코튼"],
        "colors": ["블루", "화이트", "민트", "스카이블루"],
        "style": "프레시, 마린",
        "mood": "시원하고 상쾌한",
        "negative": ["다크", "헤비"]
    },
    "그린": {
        "keywords": ["내추럴", "캐주얼", "그린", "화이트", "린넨"],
        "colors": ["그린", "카키", "올리브", "화이트"],
        "style": "내추럴, 캐주얼",
        "mood": "자연스럽고 편안한",
        "negative": ["포멀", "글램"]
    },

    # 파우더리 계열
    "파우더리": {
        "keywords": ["소프트", "페미닌", "파스텔", "핑크", "베이비블루", "니트"],
        "colors": ["파스텔", "핑크", "라벤더", "베이비블루"],
        "style": "소프트, 페미닌",
        "mood": "부드럽고 포근한",
        "negative": ["다크", "스트릿"]
    },

    # 스파이시 계열
    "스파이시": {
        "keywords": ["강렬", "섹시", "레드", "블랙", "레더", "체인"],
        "colors": ["레드", "블랙", "버건디"],
        "style": "모던, 섹시",
        "mood": "강렬하고 도발적인",
        "negative": ["파스텔", "소프트"]
    }
}

# 음악 장르별 패션 스타일 매핑
MUSIC_MOOD_MAP: Dict[str, Dict[str, any]] = {
    # 클래식/재즈
    "클래식": {
        "keywords": ["우아", "포멀", "클래식", "수트", "드레스", "블랙", "화이트"],
        "colors": ["블랙", "화이트", "네이비", "와인"],
        "style": "클래식, 포멀",
        "mood": "우아하고 품격있는",
        "negative": ["스트릿", "힙합"]
    },
    "재즈": {
        "keywords": ["빈티지", "레트로", "블랙", "베이지", "페도라", "재킷"],
        "colors": ["블랙", "베이지", "브라운", "네이비"],
        "style": "빈티지, 재즈",
        "mood": "세련되고 시크한",
        "negative": ["네온", "스포츠"]
    },

    # 팝
    "팝": {
        "keywords": ["트렌디", "컬러풀", "모던", "믹스매치", "스타일리시"],
        "colors": ["핑크", "블루", "화이트", "레드"],
        "style": "트렌디, 모던",
        "mood": "밝고 활기찬",
        "negative": ["다크", "고스"]
    },
    "케이팝": {
        "keywords": ["트렌디", "스트릿", "컬러풀", "오버핏", "레이어드"],
        "colors": ["블랙", "화이트", "레드", "핑크"],
        "style": "스트릿, K-패션",
        "mood": "트렌디하고 개성있는",
        "negative": ["클래식", "포멀"]
    },

    # 락/메탈
    "락": {
        "keywords": ["락", "레더", "블랙", "데님", "부츠", "체인"],
        "colors": ["블랙", "레드", "그레이"],
        "style": "락, 레벨",
        "mood": "강렬하고 반항적인",
        "negative": ["파스텔", "페미닌"]
    },
    "펑크": {
        "keywords": ["펑크", "찢어진", "체인", "스터드", "블랙", "레드"],
        "colors": ["블랙", "레드", "네온"],
        "style": "펑크, 스트릿",
        "mood": "반항적이고 독특한",
        "negative": ["클래식", "우아"]
    },

    # 힙합/R&B
    "힙합": {
        "keywords": ["스트릿", "오버핏", "후드", "스니커즈", "캡", "트레이닝"],
        "colors": ["블랙", "화이트", "그레이", "네온"],
        "style": "스트릿, 힙합",
        "mood": "쿨하고 자유로운",
        "negative": ["포멀", "수트"]
    },
    "알앤비": {
        "keywords": ["섹시", "시크", "블랙", "화이트", "미니멀", "슬릿"],
        "colors": ["블랙", "화이트", "베이지"],
        "style": "섹시, 미니멀",
        "mood": "섹시하고 세련된",
        "negative": ["프릴", "파스텔"]
    },

    # 일렉트로닉
    "일렉트로닉": {
        "keywords": ["퓨처", "네온", "메탈릭", "실버", "블랙", "테크"],
        "colors": ["블랙", "실버", "네온", "화이트"],
        "style": "퓨처, 테크",
        "mood": "미래적이고 실험적인",
        "negative": ["빈티지", "클래식"]
    },
    "하우스": {
        "keywords": ["파티", "컬러풀", "글리터", "네온", "크롭"],
        "colors": ["네온", "실버", "블랙", "핑크"],
        "style": "파티, 클럽",
        "mood": "화려하고 에너제틱한",
        "negative": ["미니멀", "베이직"]
    },

    # 인디/어쿠스틱
    "인디": {
        "keywords": ["빈티지", "레트로", "데님", "니트", "내추럴"],
        "colors": ["베이지", "브라운", "그린", "네이비"],
        "style": "빈티지, 인디",
        "mood": "자유롭고 감성적인",
        "negative": ["글램", "럭셔리"]
    },
    "어쿠스틱": {
        "keywords": ["내추럴", "편안", "코튼", "린넨", "베이지", "화이트"],
        "colors": ["베이지", "화이트", "브라운", "그린"],
        "style": "내추럴, 캐주얼",
        "mood": "편안하고 따뜻한",
        "negative": ["화려", "네온"]
    },

    # 발라드
    "발라드": {
        "keywords": ["로맨틱", "우아", "드레스", "니트", "파스텔"],
        "colors": ["파스텔", "화이트", "핑크", "베이지"],
        "style": "로맨틱, 소프트",
        "mood": "감성적이고 부드러운",
        "negative": ["강렬", "다크"]
    }
}


def map_perfume_to_fashion(perfume_note: str) -> Optional[Dict[str, any]]:
    """향수 노트를 패션 스타일로 변환"""
    # 대소문자 구분 없이 검색
    perfume_note_lower = perfume_note.lower()

    for note, mapping in PERFUME_MOOD_MAP.items():
        if note.lower() in perfume_note_lower or perfume_note_lower in note.lower():
            return mapping

    return None


def map_music_to_fashion(music_genre: str) -> Optional[Dict[str, any]]:
    """음악 장르를 패션 스타일로 변환"""
    music_genre_lower = music_genre.lower()

    for genre, mapping in MUSIC_MOOD_MAP.items():
        if genre.lower() in music_genre_lower or music_genre_lower in genre.lower():
            return mapping

    return None


def extract_mood_keywords(input_text: str) -> Dict[str, any]:
    """
    입력 텍스트에서 무드 키워드 추출 및 패션 스타일 변환
    향수와 음악 키워드를 동시에 검색
    """
    result = {
        "type": None,  # "perfume" or "music"
        "detected": None,  # 감지된 항목
        "keywords": [],
        "colors": [],
        "style": "",
        "mood": "",
        "negative": []
    }

    # 향수 노트 검색
    for note in PERFUME_MOOD_MAP.keys():
        if note in input_text or note.lower() in input_text.lower():
            mapping = PERFUME_MOOD_MAP[note]
            result["type"] = "perfume"
            result["detected"] = note
            result["keywords"] = mapping["keywords"]
            result["colors"] = mapping["colors"]
            result["style"] = mapping["style"]
            result["mood"] = mapping["mood"]
            result["negative"] = mapping.get("negative", [])
            return result

    # 음악 장르 검색
    for genre in MUSIC_MOOD_MAP.keys():
        if genre in input_text or genre.lower() in input_text.lower():
            mapping = MUSIC_MOOD_MAP[genre]
            result["type"] = "music"
            result["detected"] = genre
            result["keywords"] = mapping["keywords"]
            result["colors"] = mapping["colors"]
            result["style"] = mapping["style"]
            result["mood"] = mapping["mood"]
            result["negative"] = mapping.get("negative", [])
            return result

    return result


def build_mood_search_query(mood_data: Dict[str, any]) -> str:
    """무드 데이터로부터 검색 쿼리 생성"""
    if not mood_data.get("keywords"):
        return ""

    # 상위 3개 키워드를 조합하여 검색 쿼리 생성
    top_keywords = mood_data["keywords"][:3]
    return " ".join(top_keywords)

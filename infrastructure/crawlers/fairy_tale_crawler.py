"""
유치부 동화 소재 크롤러
동화 관련 주제와 소재를 수집합니다.
Gemini API를 통한 LLM 기반 소재 검색을 지원합니다.
"""
import json
import logging
from typing import List

from core.entities import AgeGroup
from core.interfaces import IContentCrawler
from core.exceptions import CrawlingError

logger = logging.getLogger(__name__)


class FairyTaleCrawler(IContentCrawler):
    """유치부(3~7세) 동화 소재 크롤러

    Gemini API 키가 제공되면 LLM 기반 소재 검색을 수행하고,
    API 키가 없거나 빈 문자열이면 기본 소재(DEFAULT_TOPICS)를 반환합니다.
    """

    # 기본 제공 동화 소재 (API 연동 전 또는 폴백용)
    DEFAULT_TOPICS = [
        {"title": "마법의 숲 속 모험", "summary": "숲 속에서 동물 친구들과 마법 같은 모험을 떠나는 이야기", "keywords": ["숲", "마법", "동물 친구"], "source": "기본 소재"},
        {"title": "하늘을 나는 작은 새", "summary": "용기를 내어 하늘 높이 날아오르는 작은 새의 이야기", "keywords": ["새", "하늘", "용기"], "source": "기본 소재"},
        {"title": "무지개 나라 여행", "summary": "알록달록 무지개 나라에서 새 친구를 사귀는 여행 이야기", "keywords": ["무지개", "색깔", "우정"], "source": "기본 소재"},
        {"title": "바다 속 인어 공주", "summary": "깊은 바다 속에서 펼쳐지는 인어 공주의 모험 이야기", "keywords": ["바다", "인어", "모험"], "source": "기본 소재"},
        {"title": "달님과 별님 이야기", "summary": "밤하늘의 달님과 별님이 들려주는 꿈 이야기", "keywords": ["달", "별", "꿈"], "source": "기본 소재"},
    ]

    def __init__(self, api_key: str = "", model_name: str = "gemini-2.5-flash"):
        """FairyTaleCrawler 초기화

        Args:
            api_key: Gemini API 키. 빈 문자열이면 DEFAULT_TOPICS 폴백.
            model_name: 사용할 Gemini 모델 이름.
        """
        self._api_key = api_key
        self._model_name = model_name
        self._client = None

        # API 키가 유효하면 Gemini 클라이언트 초기화
        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
                logger.info("Gemini 클라이언트 초기화 완료 (모델: %s)", self._model_name)
            except Exception as e:
                logger.warning("Gemini 클라이언트 초기화 실패, DEFAULT_TOPICS로 폴백: %s", e)
                self._client = None

    def _search_with_llm(self, topic: str) -> List[dict]:
        """Gemini API를 사용하여 주제 관련 동화 소재를 검색합니다.

        Args:
            topic: 검색할 주제 문자열.

        Returns:
            [{"title": ..., "summary": ..., "keywords": [...]}] 형태의 소재 리스트.

        Raises:
            Exception: Gemini API 호출 또는 응답 파싱 실패 시.
        """
        prompt = (
            f"다음 주제에 대해 유치부(3~7세) 아이들을 위한 동화 소재를 5개 제안해주세요: {topic}\n\n"
            f"반드시 아래 JSON 배열 형식으로만 응답해주세요. 다른 텍스트 없이 JSON만 출력하세요:\n"
            f'[{{"title": "소재 제목", "summary": "간단한 줄거리 요약", "keywords": ["키워드1", "키워드2", "키워드3"]}}]'
        )

        logger.info("Gemini API로 동화 소재 검색 요청: topic=%s", topic)

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )

        # 응답 텍스트에서 JSON 파싱
        response_text = response.text.strip()

        # 마크다운 코드 블록으로 감싸져 있는 경우 처리
        if response_text.startswith("```"):
            # ```json ... ``` 또는 ``` ... ``` 패턴 처리
            lines = response_text.split("\n")
            # 첫 줄(```)과 마지막 줄(```) 제거
            lines = [line for line in lines if not line.strip().startswith("```")]
            response_text = "\n".join(lines).strip()

        materials = json.loads(response_text)

        # 결과 검증 및 source 필드 추가
        results = []
        for item in materials:
            if isinstance(item, dict) and "title" in item:
                item.setdefault("summary", "")
                item.setdefault("keywords", [])
                item["source"] = "gemini"
                results.append(item)

        if not results:
            raise ValueError("Gemini 응답에서 유효한 소재를 찾을 수 없습니다.")

        logger.info("Gemini API로 동화 소재 %d건 검색 완료", len(results))
        return results

    def crawl(self, topic: str, age_group: AgeGroup) -> List[dict]:
        """동화 소재를 수집합니다.

        API 키가 설정되어 있으면 Gemini LLM 검색을 시도하고,
        실패 시 또는 API 키가 없으면 DEFAULT_TOPICS를 반환합니다.

        Args:
            topic: 검색할 주제 문자열.
            age_group: 대상 연령 그룹.

        Returns:
            소재 딕셔너리 리스트.

        Raises:
            CrawlingError: 크롤링 중 복구 불가능한 오류 발생 시.
        """
        logger.info("동화 소재 크롤링 시작: topic=%s, age_group=%s", topic, age_group.value)

        try:
            # API 키와 클라이언트가 유효하면 LLM 검색 시도
            if self._api_key and self._client:
                try:
                    results = self._search_with_llm(topic)
                    return results
                except Exception as e:
                    logger.warning("Gemini 검색 실패, DEFAULT_TOPICS로 폴백: %s", e)

            # 기본 소재 중 주제와 관련된 것 필터링
            results = []
            for material in self.DEFAULT_TOPICS:
                if topic in material["title"] or any(k in topic for k in material["keywords"]):
                    results.append(material)

            # 매칭 없으면 전체 기본 소재 반환
            if not results:
                results = self.DEFAULT_TOPICS.copy()

            logger.info("동화 소재 %d건 수집 완료", len(results))
            return results

        except Exception as e:
            raise CrawlingError("FairyTaleCrawler", str(e))

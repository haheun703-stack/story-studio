"""
초등부 교과서 소재 크롤러
교과서 관련 주제와 소재를 수집합니다.
Gemini API를 통한 LLM 기반 소재 검색을 지원합니다.
"""
import json
import logging
from typing import List

from core.entities import AgeGroup
from core.interfaces import IContentCrawler
from core.exceptions import CrawlingError

logger = logging.getLogger(__name__)


class TextbookCrawler(IContentCrawler):
    """초등부(8~13세) 교과서 소재 크롤러

    Gemini API 키가 제공되면 LLM 기반 소재 검색을 수행하고,
    API 키가 없거나 빈 문자열이면 기본 소재(DEFAULT_TOPICS)를 반환합니다.
    """

    # 기본 제공 교과서 소재 (API 연동 전 또는 폴백용)
    DEFAULT_TOPICS = [
        {"title": "태양계와 행성들", "summary": "태양계를 이루는 행성들의 특징과 순서를 알아봅니다", "keywords": ["태양계", "행성", "우주"], "subject": "과학", "grade": "3~4학년", "source": "기본 소재"},
        {"title": "물의 순환", "summary": "물이 증발하고 구름이 되어 비로 내리는 과정을 배웁니다", "keywords": ["물", "증발", "구름"], "subject": "과학", "grade": "3~4학년", "source": "기본 소재"},
        {"title": "한국의 역사 인물", "summary": "한국 역사 속 위대한 인물들의 이야기를 만나봅니다", "keywords": ["역사", "인물", "한국"], "subject": "사회", "grade": "5~6학년", "source": "기본 소재"},
        {"title": "분수와 소수", "summary": "분수와 소수의 개념과 계산 방법을 재미있게 배웁니다", "keywords": ["분수", "소수", "계산"], "subject": "수학", "grade": "3~4학년", "source": "기본 소재"},
        {"title": "식물의 성장", "summary": "씨앗에서 꽃이 피기까지 식물의 성장 과정을 관찰합니다", "keywords": ["식물", "성장", "씨앗"], "subject": "과학", "grade": "3~4학년", "source": "기본 소재"},
    ]

    def __init__(self, api_key: str = "", model_name: str = "gemini-2.5-flash"):
        """TextbookCrawler 초기화

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
        """Gemini API를 사용하여 주제 관련 교육 콘텐츠 소재를 검색합니다.

        Args:
            topic: 검색할 주제 문자열.

        Returns:
            [{"title": ..., "summary": ..., "keywords": [...]}] 형태의 소재 리스트.

        Raises:
            Exception: Gemini API 호출 또는 응답 파싱 실패 시.
        """
        prompt = (
            f"다음 주제에 대해 초등학생(8~13세)을 위한 교육 콘텐츠 소재를 5개 제안해주세요: {topic}\n\n"
            f"반드시 아래 JSON 배열 형식으로만 응답해주세요. 다른 텍스트 없이 JSON만 출력하세요:\n"
            f'[{{"title": "소재 제목", "summary": "간단한 내용 요약", "keywords": ["키워드1", "키워드2", "키워드3"]}}]'
        )

        logger.info("Gemini API로 교육 콘텐츠 소재 검색 요청: topic=%s", topic)

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

        logger.info("Gemini API로 교육 콘텐츠 소재 %d건 검색 완료", len(results))
        return results

    def crawl(self, topic: str, age_group: AgeGroup) -> List[dict]:
        """교과서 소재를 수집합니다.

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
        logger.info("교과서 소재 크롤링 시작: topic=%s, age_group=%s", topic, age_group.value)

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
                if topic in material["title"] or topic in material.get("subject", ""):
                    results.append(material)

            # 매칭 없으면 전체 기본 소재 반환
            if not results:
                results = self.DEFAULT_TOPICS.copy()

            logger.info("교과서 소재 %d건 수집 완료", len(results))
            return results

        except Exception as e:
            raise CrawlingError("TextbookCrawler", str(e))

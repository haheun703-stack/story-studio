"""
초등부 교과서 소재 크롤러
교과서 관련 주제와 소재를 수집합니다.
"""
import logging
from typing import List

from core.entities import AgeGroup
from core.interfaces import IContentCrawler
from core.exceptions import CrawlingError

logger = logging.getLogger(__name__)


class TextbookCrawler(IContentCrawler):
    """초등부(8~13세) 교과서 소재 크롤러"""

    # 기본 제공 교과서 소재 (API 연동 전 사용)
    DEFAULT_TOPICS = [
        {"title": "태양계와 행성들", "subject": "과학", "grade": "3~4학년", "source": "기본 소재"},
        {"title": "물의 순환", "subject": "과학", "grade": "3~4학년", "source": "기본 소재"},
        {"title": "한국의 역사 인물", "subject": "사회", "grade": "5~6학년", "source": "기본 소재"},
        {"title": "분수와 소수", "subject": "수학", "grade": "3~4학년", "source": "기본 소재"},
        {"title": "식물의 성장", "subject": "과학", "grade": "3~4학년", "source": "기본 소재"},
    ]

    def crawl(self, topic: str, age_group: AgeGroup) -> List[dict]:
        """교과서 소재를 수집합니다."""
        logger.info("교과서 소재 크롤링 시작: topic=%s, age_group=%s", topic, age_group.value)

        try:
            results = []
            for material in self.DEFAULT_TOPICS:
                if topic in material["title"] or topic in material.get("subject", ""):
                    results.append(material)

            if not results:
                results = self.DEFAULT_TOPICS.copy()

            logger.info("교과서 소재 %d건 수집 완료", len(results))
            return results

        except Exception as e:
            raise CrawlingError("TextbookCrawler", str(e))

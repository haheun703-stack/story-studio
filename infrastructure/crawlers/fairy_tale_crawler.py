"""
유치부 동화 소재 크롤러
동화 관련 주제와 소재를 수집합니다.
"""
import logging
from typing import List

from core.entities import AgeGroup
from core.interfaces import IContentCrawler
from core.exceptions import CrawlingError

logger = logging.getLogger(__name__)


class FairyTaleCrawler(IContentCrawler):
    """유치부(3~7세) 동화 소재 크롤러"""

    # 기본 제공 동화 소재 (API 연동 전 사용)
    DEFAULT_TOPICS = [
        {"title": "마법의 숲 속 모험", "keywords": ["숲", "마법", "동물 친구"], "source": "기본 소재"},
        {"title": "하늘을 나는 작은 새", "keywords": ["새", "하늘", "용기"], "source": "기본 소재"},
        {"title": "무지개 나라 여행", "keywords": ["무지개", "색깔", "우정"], "source": "기본 소재"},
        {"title": "바다 속 인어 공주", "keywords": ["바다", "인어", "모험"], "source": "기본 소재"},
        {"title": "달님과 별님 이야기", "keywords": ["달", "별", "꿈"], "source": "기본 소재"},
    ]

    def crawl(self, topic: str, age_group: AgeGroup) -> List[dict]:
        """동화 소재를 수집합니다."""
        logger.info("동화 소재 크롤링 시작: topic=%s, age_group=%s", topic, age_group.value)

        try:
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

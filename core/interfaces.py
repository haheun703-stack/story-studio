from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import (
    Story, TargetAudience, AgeGroup,
    MediaAsset, Episode,
)


class IStoryGenerator(ABC):
    @abstractmethod
    def generate_story(self, audience: TargetAudience, theme: str) -> Story:
        """
        주어진 타겟 오디언스와 주제를 바탕으로 스토리(대본)를 생성합니다.
        """
        pass


class IStoryRepository(ABC):
    """스토리 저장/조회 인터페이스"""

    @abstractmethod
    def save(self, story: Story) -> str:
        """스토리를 저장하고 고유 식별자(파일명 등)를 반환합니다."""
        pass

    @abstractmethod
    def find_by_id(self, story_id: str) -> Optional[Story]:
        """식별자로 스토리를 조회합니다. 없으면 None을 반환합니다."""
        pass

    @abstractmethod
    def list_all(self) -> List[str]:
        """저장된 모든 스토리의 식별자 목록을 반환합니다."""
        pass


# ── 미디어 생성 인터페이스 ────────────────────────────────────

class IImageGenerator(ABC):
    """이미지 생성 인터페이스 (Imagen 4 등)"""

    @abstractmethod
    def generate_image(self, prompt: str, style: str = "") -> MediaAsset:
        """프롬프트로 이미지를 생성하고 MediaAsset을 반환합니다."""
        pass


class IVideoGenerator(ABC):
    """영상 생성 인터페이스 (Veo 3.1 등)"""

    @abstractmethod
    def generate_video(self, prompt: str, duration_seconds: int = 8) -> MediaAsset:
        """프롬프트로 영상을 생성하고 MediaAsset을 반환합니다."""
        pass


class ITTSGenerator(ABC):
    """TTS 음성 생성 인터페이스 (Gemini TTS 등)"""

    @abstractmethod
    def generate_speech(self, text: str, voice: str = "") -> MediaAsset:
        """텍스트를 음성으로 변환하고 MediaAsset을 반환합니다."""
        pass


# ── 콘텐츠 크롤링 인터페이스 ──────────────────────────────────

class IContentCrawler(ABC):
    """콘텐츠 소재 크롤링 인터페이스"""

    @abstractmethod
    def crawl(self, topic: str, age_group: AgeGroup) -> List[dict]:
        """주제와 연령 그룹에 맞는 소재를 크롤링하여 반환합니다."""
        pass


# ── 에피소드 저장소 인터페이스 ─────────────────────────────────

class IEpisodeRepository(ABC):
    """에피소드 저장/조회 인터페이스"""

    @abstractmethod
    def save(self, episode: Episode) -> str:
        """에피소드를 저장하고 고유 식별자를 반환합니다."""
        pass

    @abstractmethod
    def find_by_id(self, episode_id: str) -> Optional[Episode]:
        """식별자로 에피소드를 조회합니다."""
        pass

    @abstractmethod
    def list_by_age_group(self, age_group: AgeGroup) -> List[str]:
        """연령 그룹별 에피소드 식별자 목록을 반환합니다."""
        pass

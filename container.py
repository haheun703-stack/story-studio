"""
의존성 주입 컨테이너 (Composition Root)
설정에 따라 모든 계층의 객체를 조립합니다.
"""
import logging
from typing import Optional

from infrastructure.config import Settings, load_settings
from infrastructure.llm_router import LLMRouter
from infrastructure.json_story_repository import JsonStoryRepository
from core.interfaces import (
    IStoryRepository,
    IImageGenerator, IVideoGenerator, ITTSGenerator,
    IContentCrawler, IEpisodeRepository,
)
from application.use_cases import StoryGenerationUseCase, EpisodeProductionUseCase
from application.pipeline import PipelineManager
from presentation.cli import StoryStudioCLI

logger = logging.getLogger(__name__)


class Container:
    """
    애플리케이션 의존성 조립기.
    Settings를 받아 모든 구성 요소를 생성하고 연결합니다.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or load_settings()
        self._router: Optional[LLMRouter] = None
        self._repository: Optional[IStoryRepository] = None
        self._use_case: Optional[StoryGenerationUseCase] = None
        self._image_generator: Optional[IImageGenerator] = None
        self._video_generator: Optional[IVideoGenerator] = None
        self._tts_generator: Optional[ITTSGenerator] = None
        self._content_crawler: Optional[IContentCrawler] = None
        self._episode_repository: Optional[IEpisodeRepository] = None

    # ── 기존 팩토리 ──────────────────────────────────────────

    def story_generator(self) -> LLMRouter:
        """LLM 라우터를 생성/반환합니다. 사용 가능한 LLM 제공자를 자동 등록합니다."""
        if self._router is not None:
            return self._router

        router = LLMRouter(default_provider=self.settings.llm.default_provider)

        # Gemini 등록
        if self.settings.llm.gemini_api_key:
            try:
                from infrastructure.gemini_adapter import GeminiStoryGenerator
                router.register(
                    "gemini",
                    GeminiStoryGenerator(
                        api_key=self.settings.llm.gemini_api_key,
                        model_name=self.settings.llm.gemini_model,
                    ),
                )
            except ImportError:
                logger.warning("google-genai 패키지가 설치되지 않아 Gemini를 사용할 수 없습니다.")

        # OpenAI 등록
        if self.settings.llm.openai_api_key:
            try:
                from infrastructure.openai_adapter import OpenAIStoryGenerator
                router.register(
                    "gpt",
                    OpenAIStoryGenerator(
                        api_key=self.settings.llm.openai_api_key,
                        model_name=self.settings.llm.openai_model,
                    ),
                )
            except ImportError:
                logger.warning("openai 패키지가 설치되지 않아 GPT를 사용할 수 없습니다.")

        # Claude 등록
        if self.settings.llm.claude_api_key:
            try:
                from infrastructure.claude_adapter import ClaudeStoryGenerator
                router.register(
                    "claude",
                    ClaudeStoryGenerator(
                        api_key=self.settings.llm.claude_api_key,
                        model_name=self.settings.llm.claude_model,
                    ),
                )
            except ImportError:
                logger.warning("anthropic 패키지가 설치되지 않아 Claude를 사용할 수 없습니다.")

        # Mock 폴백 (아무 API 키도 없는 경우)
        if not router.available_providers:
            from core.entities import Story, Scene
            from core.interfaces import IStoryGenerator as _ISG
            from core.entities import TargetAudience as _TA

            class _MockStoryGenerator(_ISG):
                def generate_story(self, audience: _TA, theme: str) -> Story:
                    scenes = [
                        Scene(scene_number=i, narration=f"테스트 나레이션 {i}",
                              image_prompt="테스트 이미지", video_prompt="테스트 비디오")
                        for i in range(1, 156)
                    ]
                    return Story(title=f"더미 타이틀: {theme}", audience=audience,
                                 theme=theme, scenes=scenes)

            router.register("mock", _MockStoryGenerator())
            router._default_provider = "mock"
            logger.warning("API 키가 없어 Mock 모드로 실행합니다.")

        self._router = router
        return router

    def story_repository(self) -> IStoryRepository:
        """JSON 파일 기반 저장소를 생성/반환합니다."""
        if self._repository is None:
            self._repository = JsonStoryRepository(
                output_dir=self.settings.storage.output_dir,
            )
        return self._repository

    def use_case(self) -> StoryGenerationUseCase:
        """StoryGenerationUseCase를 생성/반환합니다."""
        if self._use_case is None:
            self._use_case = StoryGenerationUseCase(
                story_generator=self.story_generator(),
                story_repository=self.story_repository(),
            )
        return self._use_case

    # ── 미디어 생성기 팩토리 ──────────────────────────────────

    def image_generator(self) -> Optional[IImageGenerator]:
        """Imagen 4 이미지 생성기를 생성/반환합니다."""
        if self._image_generator is not None:
            return self._image_generator

        if self.settings.llm.gemini_api_key:
            try:
                from infrastructure.imagen_adapter import Imagen4ImageGenerator
                self._image_generator = Imagen4ImageGenerator(
                    api_key=self.settings.llm.gemini_api_key,
                    model_name=self.settings.media.imagen_model,
                    output_dir=f"{self.settings.storage.media_dir}/images",
                )
            except ImportError:
                logger.warning("google-genai 패키지 문제로 Imagen을 사용할 수 없습니다.")

        return self._image_generator

    def video_generator(self) -> Optional[IVideoGenerator]:
        """Veo 3.1 영상 생성기를 생성/반환합니다."""
        if self._video_generator is not None:
            return self._video_generator

        if self.settings.llm.gemini_api_key:
            try:
                from infrastructure.veo_adapter import Veo31VideoGenerator
                self._video_generator = Veo31VideoGenerator(
                    api_key=self.settings.llm.gemini_api_key,
                    model_name=self.settings.media.veo_model,
                    output_dir=f"{self.settings.storage.media_dir}/videos",
                    tier=self.settings.media.veo_tier,
                )
            except ImportError:
                logger.warning("google-genai 패키지 문제로 Veo를 사용할 수 없습니다.")

        return self._video_generator

    def tts_generator(self) -> Optional[ITTSGenerator]:
        """Gemini TTS 음성 생성기를 생성/반환합니다."""
        if self._tts_generator is not None:
            return self._tts_generator

        if self.settings.llm.gemini_api_key:
            try:
                from infrastructure.tts_adapter import GeminiTTSGenerator
                self._tts_generator = GeminiTTSGenerator(
                    api_key=self.settings.llm.gemini_api_key,
                    model_name=self.settings.media.tts_model,
                    output_dir=f"{self.settings.storage.media_dir}/audio",
                    default_voice=self.settings.media.tts_default_voice,
                )
            except ImportError:
                logger.warning("google-genai 패키지 문제로 TTS를 사용할 수 없습니다.")

        return self._tts_generator

    def content_crawler(self, age_group_value: str = "유치부") -> Optional[IContentCrawler]:
        """연령 그룹에 맞는 크롤러를 생성/반환합니다."""
        from core.entities import AgeGroup
        try:
            if age_group_value == AgeGroup.PRESCHOOL.value or age_group_value == "preschool":
                from infrastructure.crawlers import FairyTaleCrawler
                return FairyTaleCrawler()
            else:
                from infrastructure.crawlers import TextbookCrawler
                return TextbookCrawler()
        except ImportError:
            logger.warning("크롤러를 로드할 수 없습니다.")
            return None

    # ── 에피소드 관련 팩토리 ──────────────────────────────────

    def episode_repository(self) -> IEpisodeRepository:
        """에피소드 JSON 저장소를 생성/반환합니다."""
        if self._episode_repository is None:
            from infrastructure.json_episode_repository import JsonEpisodeRepository
            self._episode_repository = JsonEpisodeRepository(
                output_dir=self.settings.storage.episode_dir,
            )
        return self._episode_repository

    def pipeline_manager(self, age_group_value: str = "유치부") -> PipelineManager:
        """PipelineManager를 생성합니다. age_group에 따라 크롤러가 달라지므로 캐싱하지 않습니다."""
        return PipelineManager(
            story_generator=self.story_generator(),
            image_generator=self.image_generator(),
            video_generator=self.video_generator(),
            tts_generator=self.tts_generator(),
            content_crawler=self.content_crawler(age_group_value),
            max_retries=self.settings.pipeline.max_retries,
            retry_delay=self.settings.pipeline.retry_delay_seconds,
        )

    def episode_use_case(self, age_group_value: str = "유치부") -> EpisodeProductionUseCase:
        """EpisodeProductionUseCase를 생성합니다. age_group에 따라 파이프라인이 달라지므로 캐싱하지 않습니다."""
        return EpisodeProductionUseCase(
            pipeline_manager=self.pipeline_manager(age_group_value),
            episode_repository=self.episode_repository(),
        )

    # ── CLI ──────────────────────────────────────────────────

    def cli(self) -> StoryStudioCLI:
        """CLI 인스턴스를 생성합니다."""
        router = self.story_generator()
        return StoryStudioCLI(
            use_case=self.use_case(),
            container=self,
            available_llms=router.available_providers,
        )

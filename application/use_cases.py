"""
스토리 생성 및 에피소드 제작 유즈케이스
"""
import logging
from typing import Optional

from core.entities import Story, TargetAudience, AssetStatus
from core.interfaces import IStoryGenerator, IStoryRepository, IEpisodeRepository
from .dto import StoryRequest, StoryResult, EpisodeRequest, EpisodeResult, PipelineStatus
from .pipeline import PipelineManager

logger = logging.getLogger(__name__)


class StoryGenerationUseCase:
    """
    스토리 생성 비즈니스 로직 (유즈케이스)
    외부 기술(어떤 AI를 쓸지)은 IStoryGenerator 인터페이스를 통해 주입받아 사용합니다.
    """
    def __init__(
        self,
        story_generator: IStoryGenerator,
        story_repository: Optional[IStoryRepository] = None,
    ):
        self.story_generator = story_generator
        self.story_repository = story_repository

    def execute(self, audience: TargetAudience, theme: str) -> Story:
        """
        기존 호환용 메서드. Story 객체를 직접 반환합니다.
        """
        logger.info("[%s] 타겟으로 '%s' 주제의 스토리 생성을 시작합니다...", audience.value, theme)
        story = self.story_generator.generate_story(audience, theme)

        scene_count = len(story.scenes)
        if not story.is_long_form_ready():
            logger.warning("씬 수(%d개)가 150개에 미달합니다.", scene_count)
        else:
            logger.info("총 %d개의 씬이 정상적으로 분할되었습니다. (롱폼 제작 기준 충족)", scene_count)

        return story

    def run(self, request: StoryRequest) -> StoryResult:
        """
        DTO 기반 입출력 메서드. 프레젠테이션 계층에서 사용합니다.
        """
        logger.info(
            "스토리 생성 시작: audience=%s, theme=%s, llm=%s",
            request.audience.value, request.theme, request.preferred_llm,
        )

        # 1. 스토리 생성 위임
        story = self.story_generator.generate_story(request.audience, request.theme)

        # 2. 비즈니스 규칙 검증
        warnings = []
        scene_count = len(story.scenes)

        if not story.is_long_form_ready():
            msg = (
                f"생성된 씬의 수({scene_count}개)가 150개에 미달합니다. "
                "13~15분 롱폼 영상 제작 시 B-roll 이미지가 부족할 수 있습니다."
            )
            warnings.append(msg)
            logger.warning(msg)

        # 3. 저장
        saved_path = ""
        if request.save_to_file and self.story_repository:
            try:
                saved_path = self.story_repository.save(story)
                logger.info("스토리 저장 완료: %s", saved_path)
            except Exception as e:
                warnings.append(f"스토리 저장 실패: {e}")
                logger.error("스토리 저장 실패: %s", e)

        # 4. 미리보기 씬 준비 (처음 3개)
        preview = [
            {
                "scene_number": s.scene_number,
                "narration": s.narration,
                "image_prompt": s.image_prompt,
                "video_prompt": s.video_prompt,
            }
            for s in story.scenes[:3]
        ]

        return StoryResult(
            title=story.title,
            audience_label=story.audience.value,
            theme=story.theme,
            scene_count=scene_count,
            is_long_form_ready=story.is_long_form_ready(),
            saved_path=saved_path,
            warnings=warnings,
            preview_scenes=preview,
        )


class EpisodeProductionUseCase:
    """
    에피소드 제작 유즈케이스.
    PipelineManager를 사용하여 전체 제작 파이프라인을 실행합니다.
    """

    def __init__(
        self,
        pipeline_manager: PipelineManager,
        episode_repository: Optional[IEpisodeRepository] = None,
    ):
        self.pipeline_manager = pipeline_manager
        self.episode_repository = episode_repository

    def produce(self, request: EpisodeRequest) -> EpisodeResult:
        """에피소드 제작을 실행합니다."""
        logger.info(
            "에피소드 제작 시작: age_group=%s, type=%s, theme=%s",
            request.age_group.value, request.content_type.value, request.theme,
        )

        # 파이프라인 실행
        episode = self.pipeline_manager.run(
            age_group=request.age_group,
            content_type=request.content_type,
            theme=request.theme,
            output_format=request.output_format,
            character_name=request.character_name,
        )

        # 저장
        warnings = []
        output_paths = []
        if self.episode_repository:
            try:
                saved_path = self.episode_repository.save(episode)
                output_paths.append(saved_path)
                logger.info("에피소드 저장 완료: %s", saved_path)
            except Exception as e:
                warnings.append(f"에피소드 저장 실패: {e}")
                logger.error("에피소드 저장 실패: %s", e)

        # 실패한 단계 경고
        for stage_result in episode.pipeline_stages:
            if stage_result.status == AssetStatus.FAILED:
                warnings.append(f"[{stage_result.stage.value}] 실패: {stage_result.error_message}")

        # 단계별 요약
        stage_summary = {
            sr.stage.value: sr.status.value
            for sr in episode.pipeline_stages
        }

        return EpisodeResult(
            episode_id=episode.episode_id,
            title=episode.title,
            age_group_label=episode.age_group.value,
            content_type_label=episode.content_type.value,
            stage_summary=stage_summary,
            media_count=len(episode.media_assets),
            output_paths=output_paths,
            warnings=warnings,
        )

    def get_status(self, episode_id: str) -> Optional[PipelineStatus]:
        """에피소드 제작 진행 상황을 조회합니다."""
        if not self.episode_repository:
            return None

        episode = self.episode_repository.find_by_id(episode_id)
        if not episode:
            return None

        return PipelineStatus(
            episode_id=episode.episode_id,
            current_stage=episode.current_stage.value if episode.current_stage else "",
            completed_stages=[
                sr.stage.value for sr in episode.pipeline_stages
                if sr.status == AssetStatus.COMPLETED
            ],
            failed_stages=[
                sr.stage.value for sr in episode.pipeline_stages
                if sr.status == AssetStatus.FAILED
            ],
            progress_percent=episode.progress_percent,
        )

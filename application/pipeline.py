"""
파이프라인 매니저 - 10단계 PDCA 기반 에피소드 제작 오케스트레이터
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.entities import (
    Episode, AgeGroup, ContentType, OutputFormat,
    Story, Scene, TargetAudience, Character,
    MediaAsset, MediaType, AssetStatus,
    StageResult, PipelineStage,
)
from core.interfaces import (
    IStoryGenerator, IImageGenerator, IVideoGenerator,
    ITTSGenerator, IContentCrawler,
)
from core.exceptions import PipelineStageError

logger = logging.getLogger(__name__)


# AgeGroup → TargetAudience 매핑
AGE_GROUP_TO_AUDIENCE = {
    AgeGroup.PRESCHOOL: TargetAudience.PRE_SCHOOL,
    AgeGroup.ELEMENTARY: TargetAudience.ELEMENTARY,
}

# AgeGroup → 기본 캐릭터
DEFAULT_CHARACTERS = {
    AgeGroup.PRESCHOOL: Character(
        name="별이",
        role="안내자",
        age_group=AgeGroup.PRESCHOOL,
        description="호기심 많고 친절한 꼬마 별",
        visual_features="cute baby star character, kawaii style, warm golden glow, friendly smile", # 기본값 추가
        avatar_prompt="cute baby star character, kawaii style, warm golden glow, friendly smile, children's book illustration",
    ),
    AgeGroup.ELEMENTARY: Character(
        name="로보",
        role="선생님",
        age_group=AgeGroup.ELEMENTARY,
        description="똑똑하고 재치 있는 AI 로봇",
        visual_features="friendly robot character, rounded design, blue and white colors, digital face", # 기본값 추가
        avatar_prompt="friendly robot character, rounded design, blue and white colors, digital face, educational style",
    ),
}


class PipelineManager:
    """
    10단계 에피소드 제작 파이프라인 오케스트레이터.

    단계:
    1. CRAWLING      - 소재 수집
    2. TOPIC_SELECTION - 주제 선정
    3. SCENARIO       - 시나리오/대본 생성
    4. IMAGE_GEN      - 이미지 생성
    5. VIDEO_GEN      - 영상 생성
    6. TTS            - 나레이션 음성 생성
    7. EDITING         - 편집 메타데이터
    8. QA             - 품질 검수
    9. BLOG_PUBLISH   - 블로그 게시 준비
    10. YOUTUBE_PUBLISH - 유튜브 업로드 준비
    """

    def __init__(
        self,
        story_generator: IStoryGenerator,
        image_generator: Optional[IImageGenerator] = None,
        video_generator: Optional[IVideoGenerator] = None,
        tts_generator: Optional[ITTSGenerator] = None,
        content_crawler: Optional[IContentCrawler] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        self.story_generator = story_generator
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.tts_generator = tts_generator
        self.content_crawler = content_crawler
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def run(
        self,
        age_group: AgeGroup,
        content_type: ContentType,
        theme: str,
        output_format: OutputFormat = OutputFormat.BOTH,
        character_name: str = "",
    ) -> Episode:
        """전체 파이프라인을 실행하여 에피소드를 생성합니다."""
        episode_id = f"ep_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # 캐릭터 설정
        character = DEFAULT_CHARACTERS.get(age_group)
        if character and character_name:
            character = Character(
                name=character_name,
                role=character.role,
                age_group=character.age_group,
                description=character.description,
                avatar_prompt=character.avatar_prompt,
            )

        # 파이프라인에 필요한 단계 결정
        stages = self._determine_stages(output_format)

        episode = Episode(
            episode_id=episode_id,
            age_group=age_group,
            content_type=content_type,
            title="",
            character=character,
            output_format=output_format,
            pipeline_stages=[
                StageResult(stage=stage, status=AssetStatus.PENDING)
                for stage in stages
            ],
        )

        logger.info(
            "파이프라인 시작: id=%s, age_group=%s, type=%s, theme=%s",
            episode_id, age_group.value, content_type.value, theme,
        )

        # 각 단계 순차 실행
        for i, stage in enumerate(stages):
            episode = self._execute_stage(episode, stage, theme)

        logger.info(
            "파이프라인 완료: id=%s, 진행률=%.1f%%",
            episode_id, episode.progress_percent,
        )

        return episode

    def _determine_stages(self, output_format: OutputFormat) -> List[PipelineStage]:
        """출력 형식에 따라 필요한 파이프라인 단계를 결정합니다."""
        # 공통 단계
        stages = [
            PipelineStage.CRAWLING,
            PipelineStage.TOPIC_SELECTION,
            PipelineStage.SCENARIO,
            PipelineStage.IMAGE_GEN,
        ]

        # 유튜브 영상이 필요한 경우
        if output_format in (OutputFormat.YOUTUBE_VIDEO, OutputFormat.BOTH):
            stages.extend([
                PipelineStage.VIDEO_GEN,
                PipelineStage.TTS,
                PipelineStage.EDITING,
            ])

        # 공통 마무리 단계
        stages.append(PipelineStage.QA)

        if output_format in (OutputFormat.BLOG, OutputFormat.BOTH):
            stages.append(PipelineStage.BLOG_PUBLISH)

        if output_format in (OutputFormat.YOUTUBE_VIDEO, OutputFormat.BOTH):
            stages.append(PipelineStage.YOUTUBE_PUBLISH)

        return stages

    def _execute_stage(self, episode: Episode, stage: PipelineStage, theme: str) -> Episode:
        """단일 파이프라인 단계를 실행합니다 (재시도 포함)."""
        stage_result = self._find_stage_result(episode, stage)
        if not stage_result:
            return episode

        stage_result.status = AssetStatus.GENERATING
        stage_result.started_at = datetime.now()
        logger.info("[%s] 단계 시작: %s", episode.episode_id, stage.value)

        for attempt in range(1, self.max_retries + 1):
            try:
                episode = self._run_stage_logic(episode, stage, theme)
                stage_result.status = AssetStatus.COMPLETED
                stage_result.completed_at = datetime.now()
                logger.info("[%s] 단계 완료: %s", episode.episode_id, stage.value)
                return episode
            except Exception as e:
                logger.warning(
                    "[%s] %s 단계 실패 (시도 %d/%d): %s",
                    episode.episode_id, stage.value, attempt, self.max_retries, e,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    stage_result.status = AssetStatus.FAILED
                    stage_result.completed_at = datetime.now()
                    stage_result.error_message = str(e)
                    logger.error("[%s] %s 단계 최종 실패", episode.episode_id, stage.value)

        return episode

    def _run_stage_logic(self, episode: Episode, stage: PipelineStage, theme: str) -> Episode:
        """각 단계별 실제 로직을 실행합니다."""
        handlers = {
            PipelineStage.CRAWLING: self._stage_crawling,
            PipelineStage.TOPIC_SELECTION: self._stage_topic_selection,
            PipelineStage.SCENARIO: self._stage_scenario,
            PipelineStage.IMAGE_GEN: self._stage_image_gen,
            PipelineStage.VIDEO_GEN: self._stage_video_gen,
            PipelineStage.TTS: self._stage_tts,
            PipelineStage.EDITING: self._stage_editing,
            PipelineStage.QA: self._stage_qa,
            PipelineStage.BLOG_PUBLISH: self._stage_blog_publish,
            PipelineStage.YOUTUBE_PUBLISH: self._stage_youtube_publish,
        }

        handler = handlers.get(stage)
        if handler:
            return handler(episode, theme)
        return episode

    # ── 개별 단계 구현 ──────────────────────────────────────

    def _stage_crawling(self, episode: Episode, theme: str) -> Episode:
        """1단계: 소재 수집"""
        if self.content_crawler:
            materials = self.content_crawler.crawl(theme, episode.age_group)
            stage_result = self._find_stage_result(episode, PipelineStage.CRAWLING)
            if stage_result:
                stage_result.output_data = {"materials": materials, "count": len(materials)}
        else:
            logger.info("크롤러 미등록 - 기본 소재 사용")
        return episode

    def _stage_topic_selection(self, episode: Episode, theme: str) -> Episode:
        """2단계: 주제 선정 (현재는 사용자 입력 theme을 그대로 사용)"""
        episode.title = theme
        stage_result = self._find_stage_result(episode, PipelineStage.TOPIC_SELECTION)
        if stage_result:
            stage_result.output_data = {"selected_topic": theme}
        return episode

    def _stage_scenario(self, episode: Episode, theme: str) -> Episode:
        """3단계: 시나리오/대본 생성"""
        audience = AGE_GROUP_TO_AUDIENCE.get(episode.age_group, TargetAudience.ELEMENTARY)
        story = self.story_generator.generate_story(audience, theme)
        episode.story = story
        episode.title = story.title

        stage_result = self._find_stage_result(episode, PipelineStage.SCENARIO)
        if stage_result:
            stage_result.output_data = {
                "scene_count": len(story.scenes),
                "is_long_form_ready": story.is_long_form_ready(),
            }
        return episode

    def _stage_image_gen(self, episode: Episode, theme: str) -> Episode:
        """4단계: 이미지 생성"""
        if not self.image_generator or not episode.story:
            logger.info("이미지 생성기 미등록 또는 스토리 없음 - 스킵")
            return episode

        generated = 0
        for scene in episode.story.scenes[:10]:  # 초기에는 10장만
            try:
                asset = self.image_generator.generate_image(scene.image_prompt)
                episode.media_assets.append(asset)
                generated += 1
            except Exception as e:
                logger.warning("씬 %d 이미지 생성 실패: %s", scene.scene_number, e)

        stage_result = self._find_stage_result(episode, PipelineStage.IMAGE_GEN)
        if stage_result:
            stage_result.output_data = {"generated_images": generated}
        return episode

    def _stage_video_gen(self, episode: Episode, theme: str) -> Episode:
        """5단계: 영상 생성"""
        if not self.video_generator or not episode.story:
            logger.info("영상 생성기 미등록 또는 스토리 없음 - 스킵")
            return episode

        generated = 0
        for scene in episode.story.scenes[:5]:  # 초기에는 5개만
            try:
                asset = self.video_generator.generate_video(scene.video_prompt)
                episode.media_assets.append(asset)
                generated += 1
            except Exception as e:
                logger.warning("씬 %d 영상 생성 실패: %s", scene.scene_number, e)

        stage_result = self._find_stage_result(episode, PipelineStage.VIDEO_GEN)
        if stage_result:
            stage_result.output_data = {"generated_videos": generated}
        return episode

    def _stage_tts(self, episode: Episode, theme: str) -> Episode:
        """6단계: TTS 음성 생성"""
        if not self.tts_generator or not episode.story:
            logger.info("TTS 생성기 미등록 또는 스토리 없음 - 스킵")
            return episode

        generated = 0
        for scene in episode.story.scenes[:10]:  # 초기에는 10개만
            try:
                asset = self.tts_generator.generate_speech(scene.narration)
                episode.media_assets.append(asset)
                generated += 1
            except Exception as e:
                logger.warning("씬 %d TTS 생성 실패: %s", scene.scene_number, e)

        stage_result = self._find_stage_result(episode, PipelineStage.TTS)
        if stage_result:
            stage_result.output_data = {"generated_audio": generated}
        return episode

    def _stage_editing(self, episode: Episode, theme: str) -> Episode:
        """7단계: 편집 메타데이터 생성 (ffmpeg 연동 준비)"""
        stage_result = self._find_stage_result(episode, PipelineStage.EDITING)
        if stage_result:
            image_assets = [a for a in episode.media_assets if a.asset_type == MediaType.IMAGE]
            video_assets = [a for a in episode.media_assets if a.asset_type == MediaType.VIDEO]
            audio_assets = [a for a in episode.media_assets if a.asset_type == MediaType.AUDIO]

            stage_result.output_data = {
                "editing_plan": {
                    "total_images": len(image_assets),
                    "total_videos": len(video_assets),
                    "total_audio": len(audio_assets),
                    "status": "메타데이터 준비 완료 (ffmpeg 연동 대기)",
                },
            }
        logger.info("편집 메타데이터 생성 완료")
        return episode

    def _stage_qa(self, episode: Episode, theme: str) -> Episode:
        """8단계: 품질 검수"""
        issues = []

        if episode.story and not episode.story.is_long_form_ready():
            issues.append(f"씬 수 부족: {len(episode.story.scenes)}개 (150개 미만)")

        image_count = sum(1 for a in episode.media_assets if a.asset_type == MediaType.IMAGE)
        if image_count == 0:
            issues.append("생성된 이미지 없음")

        failed_assets = [a for a in episode.media_assets if a.status == AssetStatus.FAILED]
        if failed_assets:
            issues.append(f"실패한 에셋 {len(failed_assets)}건")

        stage_result = self._find_stage_result(episode, PipelineStage.QA)
        if stage_result:
            stage_result.output_data = {
                "issues": issues,
                "passed": len(issues) == 0,
            }

        if issues:
            logger.warning("QA 이슈 %d건: %s", len(issues), issues)
        else:
            logger.info("QA 통과")

        return episode

    def _stage_blog_publish(self, episode: Episode, theme: str) -> Episode:
        """9단계: 블로그 게시 준비 (마크다운 생성)"""
        stage_result = self._find_stage_result(episode, PipelineStage.BLOG_PUBLISH)
        if stage_result:
            stage_result.output_data = {
                "status": "마크다운 생성 준비 완료",
                "platform": "블로그",
            }
        logger.info("블로그 게시 준비 완료")
        return episode

    def _stage_youtube_publish(self, episode: Episode, theme: str) -> Episode:
        """10단계: 유튜브 업로드 메타데이터 생성"""
        stage_result = self._find_stage_result(episode, PipelineStage.YOUTUBE_PUBLISH)
        if stage_result:
            stage_result.output_data = {
                "status": "업로드 메타데이터 준비 완료",
                "platform": "YouTube",
                "title": episode.title,
                "description": f"{episode.age_group.value} 대상 {episode.content_type.value} 콘텐츠",
            }
        logger.info("유튜브 게시 준비 완료")
        return episode

    # ── 유틸리티 ─────────────────────────────────────────────

    def _find_stage_result(self, episode: Episode, stage: PipelineStage) -> Optional[StageResult]:
        """에피소드에서 특정 단계의 StageResult를 찾습니다."""
        for sr in episode.pipeline_stages:
            if sr.stage == stage:
                return sr
        return None

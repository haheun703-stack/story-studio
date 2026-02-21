from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class TargetAudience(Enum):
    PRE_SCHOOL = "미취학"
    ELEMENTARY = "초등학생"
    MIDDLE_SCHOOL = "중학생"
    HIGH_SCHOOL = "고등학생"
    ADULT = "성인"


class AgeGroup(Enum):
    """콘텐츠 대상 연령 그룹"""
    PRESCHOOL = "유치부"      # 3~7세
    ELEMENTARY = "초등부"     # 8~13세


class ContentType(Enum):
    """콘텐츠 유형"""
    FAIRY_TALE = "동화"       # 유치부용
    TEXTBOOK = "교과서"       # 초등부용


class OutputFormat(Enum):
    """최종 출력 형식"""
    BLOG = "블로그"
    YOUTUBE_VIDEO = "유튜브영상"
    BOTH = "블로그+유튜브"


class MediaType(Enum):
    """미디어 에셋 유형"""
    IMAGE = "이미지"
    VIDEO = "영상"
    AUDIO = "음성"
    THUMBNAIL = "썸네일"


class AssetStatus(Enum):
    """에셋/단계 처리 상태"""
    PENDING = "대기"
    GENERATING = "생성중"
    COMPLETED = "완료"
    FAILED = "실패"


class PipelineStage(Enum):
    """에피소드 제작 파이프라인 단계"""
    CRAWLING = "소재수집"
    TOPIC_SELECTION = "주제선정"
    SCENARIO = "시나리오"
    IMAGE_GEN = "이미지생성"
    VIDEO_GEN = "영상생성"
    TTS = "음성생성"
    EDITING = "편집"
    QA = "품질검수"
    BLOG_PUBLISH = "블로그게시"
    YOUTUBE_PUBLISH = "유튜브게시"


# ── 기존 Dataclass ──────────────────────────────────────────

@dataclass
class Scene:
    scene_number: int
    narration: str
    image_prompt: str
    video_prompt: str


@dataclass
class Story:
    title: str
    audience: TargetAudience
    theme: str
    scenes: List[Scene]
    characters: List['Character'] = field(default_factory=list)

    def is_long_form_ready(self) -> bool:
        """
        13~15분 롱폼 영상을 위해 최소 150개의 씬이 필요한지 확인하는 비즈니스 규칙
        """
        return len(self.scenes) >= 150


# ── 신규 Dataclass ──────────────────────────────────────────

@dataclass
class Character:
    """에피소드 진행 캐릭터 (사회자)"""
    name: str
    role: str                           # 예: "사회자", "안내자"
    age_group: AgeGroup
    description: str                    # 캐릭터 설명
    visual_features: str                # 캐릭터 외형 묘사 (영어, 프롬프트용)
    avatar_prompt: str                  # 아바타 이미지 생성용 프롬프트


@dataclass
class MediaAsset:
    """생성된 미디어 에셋 (이미지/영상/음성)"""
    asset_type: MediaType
    file_path: str = ""
    prompt_used: str = ""
    status: AssetStatus = AssetStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """파이프라인 단계 실행 결과"""
    stage: PipelineStage
    status: AssetStatus = AssetStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


@dataclass
class Episode:
    """에피소드 (콘텐츠 제작 단위)"""
    episode_id: str
    age_group: AgeGroup
    content_type: ContentType
    title: str = ""
    story: Optional[Story] = None
    character: Optional[Character] = None
    media_assets: List[MediaAsset] = field(default_factory=list)
    pipeline_stages: List[StageResult] = field(default_factory=list)
    output_format: OutputFormat = OutputFormat.BOTH
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def current_stage(self) -> Optional[PipelineStage]:
        """현재 진행 중인 파이프라인 단계"""
        for stage_result in self.pipeline_stages:
            if stage_result.status == AssetStatus.GENERATING:
                return stage_result.stage
        return None

    @property
    def progress_percent(self) -> float:
        """전체 파이프라인 진행률 (0~100)"""
        if not self.pipeline_stages:
            return 0.0
        completed = sum(1 for s in self.pipeline_stages if s.status == AssetStatus.COMPLETED)
        return round(completed / len(self.pipeline_stages) * 100, 1)

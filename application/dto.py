"""
DTO (Data Transfer Object) 모듈
유즈케이스의 입출력 데이터 구조를 정의합니다.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from core.entities import TargetAudience, AgeGroup, ContentType, OutputFormat


@dataclass
class StoryRequest:
    """스토리 생성 요청 DTO"""
    audience: TargetAudience
    theme: str
    save_to_file: bool = True
    preferred_llm: str = "gemini"


@dataclass
class StoryResult:
    """스토리 생성 결과 DTO"""
    title: str
    audience_label: str
    theme: str
    scene_count: int
    is_long_form_ready: bool
    saved_path: str = ""
    warnings: List[str] = field(default_factory=list)
    preview_scenes: List[dict] = field(default_factory=list)


# ── 에피소드 프로덕션 DTO ────────────────────────────────────

@dataclass
class EpisodeRequest:
    """에피소드 제작 요청 DTO"""
    age_group: AgeGroup
    content_type: ContentType
    theme: str
    output_format: OutputFormat = OutputFormat.BOTH
    preferred_llm: str = "gemini"
    character_name: str = ""


@dataclass
class EpisodeResult:
    """에피소드 제작 결과 DTO"""
    episode_id: str
    title: str
    age_group_label: str
    content_type_label: str
    stage_summary: Dict[str, str] = field(default_factory=dict)
    media_count: int = 0
    output_paths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PipelineStatus:
    """파이프라인 진행 상황 DTO"""
    episode_id: str
    current_stage: str = ""
    completed_stages: List[str] = field(default_factory=list)
    failed_stages: List[str] = field(default_factory=list)
    progress_percent: float = 0.0

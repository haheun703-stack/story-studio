"""
core 패키지 - 도메인 계층
비즈니스 규칙과 엔티티를 정의합니다. 외부 의존성이 없습니다.
"""
from .entities import (
    Story, Scene, TargetAudience,
    AgeGroup, ContentType, OutputFormat,
    MediaType, AssetStatus, PipelineStage,
    Character, MediaAsset, StageResult, Episode,
)
from .interfaces import (
    IStoryGenerator, IStoryRepository,
    IImageGenerator, IVideoGenerator, ITTSGenerator,
    IContentCrawler, IEpisodeRepository,
)
from .exceptions import (
    StoryDomainError,
    InsufficientScenesError,
    StoryGenerationError,
    StoryNotFoundError,
    StoryPersistenceError,
    InvalidConfigurationError,
    MediaGenerationError,
    PipelineStageError,
    CrawlingError,
)

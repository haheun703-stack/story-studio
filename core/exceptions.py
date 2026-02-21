"""
도메인 예외 클래스 모음
모든 비즈니스 로직 관련 예외를 정의합니다.
"""


class StoryDomainError(Exception):
    """스토리 도메인의 기본 예외 클래스"""
    pass


class InsufficientScenesError(StoryDomainError):
    """생성된 씬 수가 롱폼 기준(150개)에 미달할 때 발생"""
    def __init__(self, actual_count: int, required_count: int = 150):
        self.actual_count = actual_count
        self.required_count = required_count
        super().__init__(
            f"씬 수 부족: {actual_count}개 생성됨 (최소 {required_count}개 필요)"
        )


class StoryGenerationError(StoryDomainError):
    """LLM API 호출 또는 응답 파싱 중 오류 발생 시"""
    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"[{provider}] 스토리 생성 실패: {detail}")


class StoryNotFoundError(StoryDomainError):
    """요청한 스토리를 저장소에서 찾을 수 없을 때"""
    def __init__(self, story_id: str):
        self.story_id = story_id
        super().__init__(f"스토리를 찾을 수 없습니다: {story_id}")


class StoryPersistenceError(StoryDomainError):
    """스토리 저장/로드 중 I/O 오류 발생 시"""
    pass


class InvalidConfigurationError(StoryDomainError):
    """설정값이 유효하지 않을 때 (API 키 누락 등)"""
    pass


class MediaGenerationError(StoryDomainError):
    """이미지/영상/TTS 생성 실패"""
    def __init__(self, media_type: str, detail: str):
        self.media_type = media_type
        self.detail = detail
        super().__init__(f"[{media_type}] 미디어 생성 실패: {detail}")


class PipelineStageError(StoryDomainError):
    """파이프라인 특정 단계 실패"""
    def __init__(self, stage: str, detail: str):
        self.stage = stage
        self.detail = detail
        super().__init__(f"파이프라인 [{stage}] 단계 실패: {detail}")


class CrawlingError(StoryDomainError):
    """콘텐츠 크롤링 실패"""
    def __init__(self, source: str, detail: str):
        self.source = source
        self.detail = detail
        super().__init__(f"크롤링 실패 [{source}]: {detail}")

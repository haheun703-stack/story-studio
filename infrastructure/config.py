"""
설정 관리 모듈
.env 파일과 환경 변수에서 설정값을 로드합니다.
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv


@dataclass
class LLMSettings:
    """LLM 관련 설정"""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-pro-preview"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    default_provider: str = "gemini"


@dataclass
class StorageSettings:
    """저장 관련 설정"""
    output_dir: str = "output/stories"
    episode_dir: str = "output/episodes"
    media_dir: str = "output/media"


@dataclass
class MediaSettings:
    """미디어 생성 관련 설정 (Imagen, Veo, TTS)"""
    imagen_model: str = "imagen-4.0-generate-001"
    veo_model: str = "veo-3.1-generate-preview"
    veo_tier: str = "FAST"
    tts_model: str = "gemini-2.5-flash-preview-tts"
    tts_default_voice: str = "Kore"
    ffmpeg_path: str = "ffmpeg"


@dataclass
class PipelineSettings:
    """파이프라인 관련 설정"""
    max_retries: int = 3
    retry_delay_seconds: int = 5
    concurrent_media_generation: bool = False


@dataclass
class Settings:
    """전체 앱 설정"""
    llm: LLMSettings = field(default_factory=LLMSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    media: MediaSettings = field(default_factory=MediaSettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)
    debug: bool = False


def load_settings(env_path: Optional[str] = None) -> Settings:
    """
    .env 파일에서 설정을 로드하여 Settings 객체를 반환합니다.
    """
    load_dotenv(dotenv_path=env_path)

    placeholder = "여기에_API_키를_입력하세요"

    def _get_key(name: str) -> str:
        val = os.getenv(name, "")
        return "" if val == placeholder else val

    return Settings(
        llm=LLMSettings(
            gemini_api_key=_get_key("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            openai_api_key=_get_key("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            claude_api_key=_get_key("CLAUDE_API_KEY"),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            default_provider=os.getenv("DEFAULT_LLM", "gemini"),
        ),
        storage=StorageSettings(
            output_dir=os.getenv("STORY_OUTPUT_DIR", "output/stories"),
            episode_dir=os.getenv("EPISODE_OUTPUT_DIR", "output/episodes"),
            media_dir=os.getenv("MEDIA_OUTPUT_DIR", "output/media"),
        ),
        media=MediaSettings(
            imagen_model=os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001"),
            veo_model=os.getenv("VEO_MODEL", "veo-3.1-generate-preview"),
            veo_tier=os.getenv("VEO_TIER", "FAST"),
            tts_model=os.getenv("TTS_MODEL", "gemini-2.5-flash-preview-tts"),
            tts_default_voice=os.getenv("TTS_DEFAULT_VOICE", "Kore"),
            ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg"),
        ),
        pipeline=PipelineSettings(
            max_retries=int(os.getenv("PIPELINE_MAX_RETRIES", "3")),
            retry_delay_seconds=int(os.getenv("PIPELINE_RETRY_DELAY", "5")),
            concurrent_media_generation=os.getenv("PIPELINE_CONCURRENT", "false").lower() == "true",
        ),
        debug=os.getenv("DEBUG", "false").lower() == "true",
    )

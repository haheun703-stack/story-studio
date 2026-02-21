"""
멀티 LLM 라우터
여러 LLM 제공자 중 적절한 것을 선택하여 스토리를 생성합니다.
IStoryGenerator 인터페이스를 구현합니다.
"""
import logging
from typing import Dict

from core.entities import Story, TargetAudience
from core.interfaces import IStoryGenerator
from core.exceptions import StoryGenerationError, InvalidConfigurationError

logger = logging.getLogger(__name__)


class LLMRouter(IStoryGenerator):
    """
    여러 LLM 제공자를 등록하고, 선택된 제공자로 스토리를 생성하는 라우터.
    자체적으로 IStoryGenerator를 구현하므로 기존 의존성 주입 구조에 그대로 삽입 가능합니다.
    """

    def __init__(self, default_provider: str = "gemini"):
        self._providers: Dict[str, IStoryGenerator] = {}
        self._default_provider = default_provider
        self._current_provider = default_provider

    def register(self, name: str, generator: IStoryGenerator) -> None:
        """LLM 제공자를 등록합니다."""
        self._providers[name] = generator
        logger.info("LLM 제공자 등록: %s", name)

    def set_provider(self, name: str) -> None:
        """현재 사용할 LLM 제공자를 설정합니다."""
        if name not in self._providers:
            available = ", ".join(self._providers.keys()) or "(없음)"
            raise InvalidConfigurationError(
                f"LLM 제공자 '{name}'이(가) 등록되지 않았습니다. 사용 가능: {available}"
            )
        self._current_provider = name

    @property
    def available_providers(self) -> list[str]:
        """등록된 LLM 제공자 이름 목록을 반환합니다."""
        return list(self._providers.keys())

    def generate_story(self, audience: TargetAudience, theme: str) -> Story:
        """현재 설정된 LLM 제공자를 사용하여 스토리를 생성합니다."""
        provider_name = self._current_provider

        if provider_name not in self._providers:
            raise InvalidConfigurationError(
                f"LLM 제공자 '{provider_name}'이(가) 등록되지 않았습니다."
            )

        generator = self._providers[provider_name]
        logger.info("LLM 라우터: '%s' 제공자로 스토리 생성 시작", provider_name)

        try:
            return generator.generate_story(audience, theme)
        except StoryGenerationError:
            raise
        except Exception as e:
            raise StoryGenerationError(provider_name, str(e))

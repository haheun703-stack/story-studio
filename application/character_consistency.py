"""
캐릭터 일관성 관리 모듈

에피소드 내 모든 씬에서 동일 캐릭터가 동일한 외형으로 등장하도록
프롬프트를 관리하는 시스템입니다.

사용 예시:
    >>> from core.entities import Character, AgeGroup, Story, Scene
    >>> character = Character(
    ...     name="별이",
    ...     role="안내자",
    ...     age_group=AgeGroup.PRESCHOOL,
    ...     description="호기심 많고 친절한 꼬마 별",
    ...     visual_features="cute baby star character, kawaii style, warm golden glow",
    ...     avatar_prompt="cute baby star character, kawaii style, children's book illustration",
    ... )
    >>> manager = CharacterConsistencyManager(character)
    >>> scene = Scene(scene_number=1, narration="별이가 숲을 걷습니다.",
    ...              image_prompt="a star walking in the forest",
    ...              video_prompt="a star walking slowly through a green forest")
    >>> print(manager.build_scene_prompt(scene))
"""

from dataclasses import dataclass, replace
from typing import List

from core.entities import Character, CharacterBible, Scene, Story, AgeGroup


# ── 연령 그룹별 스타일 프리셋 ──────────────────────────────────

_STYLE_PRESETS = {
    AgeGroup.PRESCHOOL: {
        "style_keywords": "kawaii, pastel colors, soft shading, rounded shapes, simple backgrounds",
        "illustration_type": "children's picture book illustration, digital art",
        "color_palette": "soft pastel tones, warm and gentle colors, low contrast",
        "mood": "warm, friendly, safe, comforting",
    },
    AgeGroup.ELEMENTARY: {
        "style_keywords": "adventure, vibrant colors, dynamic composition, detailed backgrounds",
        "illustration_type": "animated adventure book illustration, digital art",
        "color_palette": "vibrant and rich colors, high contrast, saturated",
        "mood": "exciting, curious, energetic, inspiring",
    },
}


class CharacterConsistencyManager:
    """
    캐릭터 일관성 관리자.

    단일 캐릭터의 시각적 일관성을 보장하기 위해,
    각 씬의 이미지/영상 프롬프트에 캐릭터 외형 정보를 주입합니다.
    """

    def __init__(self, character: Character) -> None:
        """
        Args:
            character: 일관성을 유지할 대상 캐릭터 엔티티.
                       character.bible이 있으면 바이블 기반 정규화 프롬프트 사용,
                       없으면 기존 visual_features 방식으로 폴백.
        """
        self._character = character

    # ── 퍼블릭 메서드 ──────────────────────────────────────────

    def build_scene_prompt(self, scene: Scene) -> str:
        """
        씬의 image_prompt에 캐릭터 외형 정보를 일관되게 주입합니다.

        바이블이 있으면 불변 캐릭터 블록 + 아트 스타일을 사용하고,
        없으면 기존 visual_features 방식으로 폴백합니다.
        """
        bible = self._character.bible
        if bible:
            # 바이블 기반: 캐릭터 블록(40%) + 씬 + 스타일
            parts = [
                bible.build_character_block(),
                scene.image_prompt,
                bible.art_style,
                "consistent character design, same face same hairstyle",
            ]
            return ", ".join(parts)

        # 기존 방식 폴백
        style_ref = self.generate_style_reference()
        parts = [
            self._character.visual_features,
            scene.image_prompt,
            f"{style_ref}, consistent character design",
        ]
        return ", ".join(parts)

    def build_video_prompt(self, scene: Scene) -> str:
        """씬의 video_prompt에 캐릭터 일관성 정보를 적용합니다."""
        bible = self._character.bible
        if bible:
            parts = [
                bible.build_character_block(),
                scene.video_prompt,
                bible.art_style,
                "consistent character design, smooth animation, continuous motion",
            ]
            return ", ".join(parts)

        style_ref = self.generate_style_reference()
        parts = [
            self._character.visual_features,
            scene.video_prompt,
            f"{style_ref}, consistent character design",
            "smooth animation, continuous motion",
        ]
        return ", ".join(parts)

    def generate_style_reference(self) -> str:
        """
        에피소드 전체에 적용할 스타일 레퍼런스 프롬프트를 생성합니다.

        캐릭터의 age_group에 따라 다른 스타일을 적용합니다:
        - 유치부(PRESCHOOL): kawaii, pastel colors, soft shading 등
        - 초등부(ELEMENTARY): adventure, vibrant colors, dynamic composition 등

        Returns:
            연령 그룹에 맞는 스타일 레퍼런스 프롬프트 문자열
        """
        preset = _STYLE_PRESETS.get(self._character.age_group)

        if preset is None:
            # 알 수 없는 연령 그룹일 경우 안전한 기본값 반환
            return "children's book illustration style"

        return f"{preset['illustration_type']}, {preset['style_keywords']}, {preset['color_palette']}"

    # ── 프로퍼티 ───────────────────────────────────────────────

    @property
    def character(self) -> Character:
        """관리 대상 캐릭터를 반환합니다."""
        return self._character


# ── 모듈 레벨 유틸리티 함수 ────────────────────────────────────

def apply_consistency(story: Story, character: Character) -> Story:
    """
    Story의 모든 씬에 캐릭터 일관성 프롬프트를 적용한 새 Story를 반환합니다.

    원본 Story 객체는 변경하지 않으며, 프롬프트가 갱신된 새 Scene들로
    구성된 새 Story 인스턴스를 반환합니다 (불변성 보장).

    Args:
        story: 원본 스토리
        character: 일관성을 적용할 캐릭터

    Returns:
        모든 씬의 image_prompt, video_prompt에 캐릭터 일관성이 적용된 새 Story

    사용 예시:
        >>> updated_story = apply_consistency(original_story, character)
        >>> # original_story는 변경되지 않음
        >>> # updated_story의 모든 씬에 캐릭터 외형 정보가 포함됨
    """
    manager = CharacterConsistencyManager(character)

    updated_scenes: List[Scene] = []
    for scene in story.scenes:
        updated_scene = Scene(
            scene_number=scene.scene_number,
            narration=scene.narration,
            image_prompt=manager.build_scene_prompt(scene),
            video_prompt=manager.build_video_prompt(scene),
        )
        updated_scenes.append(updated_scene)

    # Story 객체를 새로 생성하여 불변성 보장
    updated_story = Story(
        title=story.title,
        audience=story.audience,
        theme=story.theme,
        scenes=updated_scenes,
        characters=story.characters if character in story.characters else story.characters + [character],
    )

    return updated_story

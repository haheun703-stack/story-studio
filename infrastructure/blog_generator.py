"""
블로그 마크다운 생성기 모듈

에피소드(Episode)를 블로그용 마크다운 포스트로 변환하여
output/blog 디렉토리에 .md 파일로 저장합니다.
"""

import logging
from pathlib import Path
from datetime import date
from typing import List, Optional

from core.entities import (
    Episode,
    Story,
    Scene,
    Character,
    MediaAsset,
    MediaType,
)

logger = logging.getLogger(__name__)


class BlogMarkdownGenerator:
    """에피소드를 블로그 마크다운 포스트로 변환합니다."""

    def __init__(self, output_dir: str = "output/blog") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("BlogMarkdownGenerator 초기화 완료 (출력 경로: %s)", self.output_dir)

    # ── 공개 API ─────────────────────────────────────────────

    def generate(self, episode: Episode) -> str:
        """에피소드를 마크다운 파일로 변환하고 파일 경로를 반환합니다.

        Args:
            episode: 변환 대상 에피소드 객체

        Returns:
            생성된 마크다운 파일의 경로 문자열
        """
        logger.info("마크다운 생성 시작: episode_id=%s", episode.episode_id)

        sections: List[str] = []

        # 1. 헤더 (YAML frontmatter + 제목)
        sections.append(self._build_header(episode))

        # 2. 캐릭터 소개 섹션
        if episode.character is not None:
            sections.append(self._build_character_intro(episode.character))

        # 3. 씬별 본문 (나레이션 + 이미지 참조)
        if episode.story is not None:
            image_assets = [
                asset
                for asset in episode.media_assets
                if asset.asset_type == MediaType.IMAGE
            ]
            for scene in episode.story.scenes:
                sections.append(self._build_scene_content(scene, image_assets))

        # 4. 마무리 섹션
        sections.append(self._build_footer(episode))

        # 마크다운 조합 및 파일 저장
        markdown_text = "\n\n".join(sections) + "\n"
        output_path = self.output_dir / f"{episode.episode_id}.md"
        output_path.write_text(markdown_text, encoding="utf-8")

        logger.info("마크다운 파일 저장 완료: %s", output_path)
        return str(output_path)

    # ── 내부 빌더 메서드 ─────────────────────────────────────

    def _build_header(self, episode: Episode) -> str:
        """YAML frontmatter + 제목을 생성합니다.

        Args:
            episode: 대상 에피소드

        Returns:
            YAML frontmatter와 마크다운 H1 제목 문자열
        """
        title = episode.title or "제목 없음"
        age_group_value = episode.age_group.value
        content_type_value = episode.content_type.value
        today = date.today().isoformat()

        # 태그: 콘텐츠 유형, 연령 그룹, 스토리 테마(있으면)
        tags: List[str] = [content_type_value, age_group_value]
        if episode.story is not None and episode.story.theme:
            tags.append(episode.story.theme)

        tags_str = ", ".join(tags)

        frontmatter = (
            f"---\n"
            f'title: "{title}"\n'
            f"date: {today}\n"
            f"age_group: {age_group_value}\n"
            f"content_type: {content_type_value}\n"
            f"tags: [{tags_str}]\n"
            f"---"
        )

        heading = f"# {title}"

        return f"{frontmatter}\n\n{heading}"

    def _build_character_intro(self, character: Character) -> str:
        """캐릭터 소개 섹션을 생성합니다.

        Args:
            character: 소개할 캐릭터 객체

        Returns:
            캐릭터 소개 마크다운 문자열
        """
        lines = [
            f"## 오늘의 친구: {character.name}",
            "",
            f"> {character.description}",
        ]
        return "\n".join(lines)

    def _build_scene_content(
        self, scene: Scene, image_assets: List[MediaAsset]
    ) -> str:
        """씬별 본문을 생성합니다.

        나레이션 텍스트와 해당 씬에 매핑되는 이미지 에셋이 있으면
        마크다운 이미지 참조를 포함합니다.

        Args:
            scene: 대상 씬 객체
            image_assets: 에피소드 전체 이미지 에셋 목록

        Returns:
            씬 본문 마크다운 문자열
        """
        lines = [
            f"### 장면 {scene.scene_number}",
            "",
            scene.narration,
        ]

        # 씬 번호에 매핑되는 이미지 에셋 탐색
        # metadata에 scene_number가 기록된 에셋을 우선 매칭하고,
        # 없으면 인덱스 기반으로 폴백합니다.
        matched_asset = self._find_image_for_scene(scene, image_assets)
        if matched_asset is not None and matched_asset.file_path:
            # 상대 경로로 이미지 참조
            rel_path = matched_asset.file_path
            lines.append("")
            lines.append(f"![장면 {scene.scene_number} 이미지]({rel_path})")

        return "\n".join(lines)

    def _build_footer(self, episode: Episode) -> str:
        """마무리 섹션을 생성합니다.

        Args:
            episode: 대상 에피소드

        Returns:
            마무리 마크다운 문자열
        """
        lines = [
            "---",
            "",
            "*이 콘텐츠는 Story Studio에서 자동 생성되었습니다.*",
        ]
        return "\n".join(lines)

    # ── 유틸리티 ─────────────────────────────────────────────

    @staticmethod
    def _find_image_for_scene(
        scene: Scene, image_assets: List[MediaAsset]
    ) -> Optional[MediaAsset]:
        """씬에 해당하는 이미지 에셋을 찾습니다.

        1차: metadata['scene_number']가 일치하는 에셋
        2차: 인덱스 기반 매핑 (scene_number - 1)

        Args:
            scene: 대상 씬
            image_assets: 이미지 에셋 목록

        Returns:
            매칭된 MediaAsset 또는 None
        """
        # 1차: metadata 기반 매칭
        for asset in image_assets:
            scene_num = asset.metadata.get("scene_number")
            if scene_num is not None and int(scene_num) == scene.scene_number:
                return asset

        # 2차: 인덱스 기반 폴백
        idx = scene.scene_number - 1
        if 0 <= idx < len(image_assets):
            return image_assets[idx]

        return None

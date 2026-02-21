"""
JSON 파일 기반 스토리 저장소
IStoryRepository 인터페이스를 구현합니다.
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import asdict

from core.entities import Story, Scene, TargetAudience
from core.interfaces import IStoryRepository
from core.exceptions import StoryPersistenceError

logger = logging.getLogger(__name__)


class JsonStoryRepository(IStoryRepository):
    """스토리를 JSON 파일로 저장하고 로드하는 저장소 구현체"""

    def __init__(self, output_dir: str = "output/stories"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save(self, story: Story) -> str:
        """스토리를 JSON 파일로 저장합니다. 반환값: 저장된 파일의 전체 경로"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(
            c if c.isalnum() or c in ("_", "-") else "_"
            for c in story.title[:30]
        )
        filename = f"{timestamp}_{safe_title}.json"
        filepath = os.path.join(self.output_dir, filename)

        try:
            data = {
                "title": story.title,
                "audience": story.audience.value,
                "theme": story.theme,
                "scene_count": len(story.scenes),
                "created_at": datetime.now().isoformat(),
                "scenes": [asdict(scene) for scene in story.scenes],
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("스토리 저장 완료: %s", filepath)
            return filepath
        except (IOError, OSError) as e:
            raise StoryPersistenceError(f"파일 저장 실패: {filepath} - {e}")

    def find_by_id(self, story_id: str) -> Optional[Story]:
        """파일명(story_id)으로 스토리를 로드합니다."""
        filepath = os.path.join(self.output_dir, story_id)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenes = [
                Scene(
                    scene_number=s["scene_number"],
                    narration=s["narration"],
                    image_prompt=s["image_prompt"],
                    video_prompt=s["video_prompt"],
                )
                for s in data["scenes"]
            ]
            audience = TargetAudience(data["audience"])

            return Story(
                title=data["title"],
                audience=audience,
                theme=data["theme"],
                scenes=scenes,
            )
        except (json.JSONDecodeError, KeyError, IOError) as e:
            raise StoryPersistenceError(f"파일 로드 실패: {filepath} - {e}")

    def list_all(self) -> List[str]:
        """저장된 모든 스토리 파일명 목록을 반환합니다."""
        try:
            return sorted(
                [f for f in os.listdir(self.output_dir) if f.endswith(".json")],
                reverse=True,
            )
        except OSError:
            return []

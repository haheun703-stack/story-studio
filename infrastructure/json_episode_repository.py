"""
에피소드 JSON 파일 저장소
에피소드를 JSON 파일로 저장하고 조회합니다.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from core.entities import (
    Episode, AgeGroup, ContentType, OutputFormat,
    Story, Scene, TargetAudience, Character,
    MediaAsset, MediaType, AssetStatus,
    StageResult, PipelineStage,
)
from core.interfaces import IEpisodeRepository
from core.exceptions import StoryPersistenceError

logger = logging.getLogger(__name__)


class JsonEpisodeRepository(IEpisodeRepository):
    """JSON 파일 기반 에피소드 저장소"""

    def __init__(self, output_dir: str = "output/episodes"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, episode: Episode) -> str:
        """에피소드를 JSON 파일로 저장합니다."""
        file_name = f"{episode.episode_id}.json"
        file_path = self.output_dir / file_name

        try:
            data = self._episode_to_dict(episode)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            logger.info("에피소드 저장 완료: %s", file_path)
            return str(file_path)

        except Exception as e:
            raise StoryPersistenceError(f"에피소드 저장 실패: {e}")

    def find_by_id(self, episode_id: str) -> Optional[Episode]:
        """식별자로 에피소드를 조회합니다."""
        file_path = self.output_dir / f"{episode_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_episode(data)
        except Exception as e:
            logger.error("에피소드 로드 실패: %s", e)
            return None

    def list_by_age_group(self, age_group: AgeGroup) -> List[str]:
        """연령 그룹별 에피소드 ID 목록을 반환합니다."""
        results = []
        for file_path in sorted(self.output_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("age_group") == age_group.value:
                    results.append(data["episode_id"])
            except Exception:
                continue
        return results

    def _episode_to_dict(self, episode: Episode) -> dict:
        """Episode 객체를 dict로 변환합니다."""
        story_dict = None
        if episode.story:
            story_dict = {
                "title": episode.story.title,
                "audience": episode.story.audience.value,
                "theme": episode.story.theme,
                "scenes": [
                    {
                        "scene_number": s.scene_number,
                        "narration": s.narration,
                        "image_prompt": s.image_prompt,
                        "video_prompt": s.video_prompt,
                    }
                    for s in episode.story.scenes
                ],
            }

        char_dict = None
        if episode.character:
            char_dict = {
                "name": episode.character.name,
                "role": episode.character.role,
                "age_group": episode.character.age_group.value,
                "description": episode.character.description,
                "avatar_prompt": episode.character.avatar_prompt,
            }

        return {
            "episode_id": episode.episode_id,
            "age_group": episode.age_group.value,
            "content_type": episode.content_type.value,
            "title": episode.title,
            "story": story_dict,
            "character": char_dict,
            "media_assets": [
                {
                    "asset_type": a.asset_type.value,
                    "file_path": a.file_path,
                    "prompt_used": a.prompt_used,
                    "status": a.status.value,
                    "metadata": a.metadata,
                }
                for a in episode.media_assets
            ],
            "pipeline_stages": [
                {
                    "stage": sr.stage.value,
                    "status": sr.status.value,
                    "started_at": sr.started_at.isoformat() if sr.started_at else None,
                    "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
                    "output_data": sr.output_data,
                    "error_message": sr.error_message,
                }
                for sr in episode.pipeline_stages
            ],
            "output_format": episode.output_format.value,
            "created_at": episode.created_at.isoformat(),
        }

    def _dict_to_episode(self, data: dict) -> Episode:
        """dict를 Episode 객체로 변환합니다."""
        story = None
        if data.get("story"):
            sd = data["story"]
            story = Story(
                title=sd["title"],
                audience=TargetAudience(sd["audience"]),
                theme=sd["theme"],
                scenes=[
                    Scene(
                        scene_number=s["scene_number"],
                        narration=s["narration"],
                        image_prompt=s["image_prompt"],
                        video_prompt=s["video_prompt"],
                    )
                    for s in sd.get("scenes", [])
                ],
            )

        character = None
        if data.get("character"):
            cd = data["character"]
            character = Character(
                name=cd["name"],
                role=cd["role"],
                age_group=AgeGroup(cd["age_group"]),
                description=cd["description"],
                avatar_prompt=cd["avatar_prompt"],
            )

        # Enum 매핑 헬퍼
        stage_map = {s.value: s for s in PipelineStage}
        status_map = {s.value: s for s in AssetStatus}
        media_map = {m.value: m for m in MediaType}

        return Episode(
            episode_id=data["episode_id"],
            age_group=AgeGroup(data["age_group"]),
            content_type=ContentType(data["content_type"]),
            title=data.get("title", ""),
            story=story,
            character=character,
            media_assets=[
                MediaAsset(
                    asset_type=media_map[a["asset_type"]],
                    file_path=a["file_path"],
                    prompt_used=a["prompt_used"],
                    status=status_map[a["status"]],
                    metadata=a.get("metadata", {}),
                )
                for a in data.get("media_assets", [])
            ],
            pipeline_stages=[
                StageResult(
                    stage=stage_map[sr["stage"]],
                    status=status_map[sr["status"]],
                    started_at=datetime.fromisoformat(sr["started_at"]) if sr.get("started_at") else None,
                    completed_at=datetime.fromisoformat(sr["completed_at"]) if sr.get("completed_at") else None,
                    output_data=sr.get("output_data", {}),
                    error_message=sr.get("error_message", ""),
                )
                for sr in data.get("pipeline_stages", [])
            ],
            output_format=OutputFormat(data.get("output_format", "블로그+유튜브")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

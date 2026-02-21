"""
Veo 3.1 영상 생성 어댑터
google.genai SDK를 사용하여 영상을 생성합니다.
비동기 폴링 방식: 생성 요청 → 상태 확인 → 완료 시 다운로드
"""
import logging
import time
from pathlib import Path

from google import genai
from google.genai import types

from core.entities import MediaAsset, MediaType, AssetStatus
from core.interfaces import IVideoGenerator
from core.exceptions import MediaGenerationError

logger = logging.getLogger(__name__)


class Veo31VideoGenerator(IVideoGenerator):
    """Veo 3.1을 사용한 영상 생성기"""

    def __init__(
        self,
        api_key: str,
        model_name: str = "veo-3.1-generate-preview",
        output_dir: str = "output/media/videos",
        tier: str = "FAST",
        poll_interval: int = 10,
        max_poll_time: int = 300,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tier = tier
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time

    def generate_video(self, prompt: str, duration_seconds: int = 8) -> MediaAsset:
        """프롬프트로 영상을 생성합니다 (비동기 폴링)."""
        logger.info("Veo 3.1 영상 생성 요청: %s", prompt[:80])

        try:
            operation = self.client.models.generate_videos(
                model=self.model_name,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    person_generation="allow_all",
                    aspect_ratio="16:9",
                ),
            )

            logger.info("영상 생성 작업 시작, 폴링 대기 중...")

            elapsed = 0
            while not operation.done:
                if elapsed >= self.max_poll_time:
                    raise MediaGenerationError("Veo3.1", f"타임아웃: {self.max_poll_time}초 초과")
                time.sleep(self.poll_interval)
                elapsed += self.poll_interval
                operation = self.client.operations.get(operation)
                logger.info("영상 생성 진행 중... (%d초 경과)", elapsed)

            if not operation.response or not operation.response.generated_videos:
                raise MediaGenerationError("Veo3.1", "영상이 생성되지 않았습니다")

            video = operation.response.generated_videos[0]
            file_name = f"vid_{hash(prompt) & 0xFFFFFFFF:08x}.mp4"
            file_path = self.output_dir / file_name
            video.video.save(str(file_path))

            logger.info("영상 저장 완료: %s", file_path)

            return MediaAsset(
                asset_type=MediaType.VIDEO,
                file_path=str(file_path),
                prompt_used=prompt,
                status=AssetStatus.COMPLETED,
                metadata={"duration_seconds": duration_seconds},
            )

        except MediaGenerationError:
            raise
        except Exception as e:
            raise MediaGenerationError("Veo3.1", str(e))

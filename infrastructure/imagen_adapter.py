"""
Imagen 4 이미지 생성 어댑터
google.genai SDK를 사용하여 이미지를 생성합니다.
"""
import logging
import os
from pathlib import Path

from google import genai
from google.genai import types

from core.entities import MediaAsset, MediaType, AssetStatus
from core.interfaces import IImageGenerator
from core.exceptions import MediaGenerationError

logger = logging.getLogger(__name__)


class Imagen4ImageGenerator(IImageGenerator):
    """Imagen 4를 사용한 이미지 생성기"""

    def __init__(
        self,
        api_key: str,
        model_name: str = "imagen-4.0-generate-001",
        output_dir: str = "output/media/images",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # Imagen 4에 최적화된 기본 네거티브/품질 지시어
    DEFAULT_QUALITY_SUFFIX = (
        "high quality, sharp details, professional children's illustration, "
        "no text, no watermark, no signature, safe for children"
    )

    def generate_image(self, prompt: str, style: str = "") -> MediaAsset:
        """프롬프트로 이미지를 생성합니다."""
        parts = []
        if style:
            parts.append(style)
        parts.append(prompt)
        parts.append(self.DEFAULT_QUALITY_SUFFIX)
        full_prompt = ", ".join(parts)
        logger.info("Imagen 4 이미지 생성 중: %s", full_prompt[:100])

        try:
            response = self.client.models.generate_images(
                model=self.model_name,
                prompt=full_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                ),
            )

            if not response.generated_images:
                raise MediaGenerationError("Imagen4", "이미지가 생성되지 않았습니다")

            image = response.generated_images[0].image
            
            # 파일명 생성 (타임스탬프 + 랜덤)
            import uuid
            from datetime import datetime
            
            filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            file_path = self.output_dir / filename
            
            # 이미지 저장
            image.save(file_path)
            logger.info("이미지 저장 완료: %s", file_path)

            return MediaAsset(
                asset_type=MediaType.IMAGE,
                file_path=str(file_path),
                prompt_used=prompt,
                status=AssetStatus.COMPLETED,
            )

        except MediaGenerationError:
            raise
        except Exception as e:
            raise MediaGenerationError("Imagen4", str(e))

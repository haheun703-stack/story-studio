"""
Subject Reference 이미지 생성기
Vertex AI + imagen-3.0-capability-001을 사용하여
캐릭터 레퍼런스 이미지 기반으로 일관된 캐릭터 이미지를 생성합니다.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from google import genai
from google.genai import types

from core.entities import (
    MediaAsset, MediaType, AssetStatus, CharacterBible,
)
from core.interfaces import IImageGenerator
from core.exceptions import MediaGenerationError

logger = logging.getLogger(__name__)


class SubjectRefImageGenerator(IImageGenerator):
    """Subject + Style Reference 기반 이미지 생성기 (Vertex AI)"""

    def __init__(
        self,
        gcp_project: str,
        location: str = "us-central1",
        output_dir: str = "output/media/images",
        api_key: str = "",
    ):
        # Vertex AI 클라이언트 (Subject Reference용)
        self.vertex_client = genai.Client(
            vertexai=True,
            project=gcp_project,
            location=location,
        )
        # API Key 클라이언트 (레퍼런스 이미지 최초 생성용)
        self.api_client = genai.Client(api_key=api_key) if api_key else None

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 캐릭터별 Subject Reference 캐시
        self._ref_cache: dict[str, types.SubjectReferenceImage] = {}
        # Style Reference 캐시
        self._style_ref_cache: dict[str, types.StyleReferenceImage] = {}

    def _build_subject_ref(
        self, bible: CharacterBible, reference_id: int = 1,
    ) -> types.SubjectReferenceImage:
        """CharacterBible에서 SubjectReferenceImage 객체 생성"""
        cache_key = bible.reference_image_path
        if cache_key in self._ref_cache:
            return self._ref_cache[cache_key]

        ref_image = types.Image.from_file(location=bible.reference_image_path)
        subject_ref = types.SubjectReferenceImage(
            reference_id=reference_id,
            reference_image=ref_image,
            config=types.SubjectReferenceConfig(
                subject_description=bible.build_character_block(),
                subject_type=bible.subject_type,
            ),
        )
        self._ref_cache[cache_key] = subject_ref
        return subject_ref

    def _build_style_ref(
        self, bible: CharacterBible, reference_id: int = 99,
    ) -> types.StyleReferenceImage:
        """CharacterBible에서 StyleReferenceImage 객체 생성 (화풍 고정용)"""
        cache_key = f"style_{bible.reference_image_path}"
        if cache_key in self._style_ref_cache:
            return self._style_ref_cache[cache_key]

        ref_image = types.Image.from_file(location=bible.reference_image_path)
        style_ref = types.StyleReferenceImage(
            reference_id=reference_id,
            reference_image=ref_image,
            config=types.StyleReferenceConfig(
                style_description=f"{bible.art_style}, consistent character design",
            ),
        )
        self._style_ref_cache[cache_key] = style_ref
        return style_ref

    def generate_image(self, prompt: str, style: str = "") -> MediaAsset:
        """기본 IImageGenerator 인터페이스 구현 (Subject Reference 없이)"""
        full_prompt = f"{style}, {prompt}" if style else prompt
        return self._generate_basic(full_prompt)

    def generate_with_bible(
        self,
        bible: CharacterBible,
        action: str,
        environment: str,
        emotion: str = "",
        camera: str = "",
        reference_id: int = 1,
    ) -> MediaAsset:
        """캐릭터 바이블 기반 Subject Reference 이미지 생성"""
        if not bible.reference_image_path:
            raise MediaGenerationError(
                "SubjectRef", "레퍼런스 이미지 경로가 설정되지 않았습니다"
            )

        # [reference_id]로 프롬프트에서 캐릭터 참조
        action_with_ref = action.replace(
            "the character", f"the character[{reference_id}]"
        )
        if f"[{reference_id}]" not in action_with_ref:
            action_with_ref = f"the character[{reference_id}] {action_with_ref}"

        prompt = bible.build_full_prompt(
            action=action_with_ref,
            environment=environment,
            emotion=emotion,
            camera=camera,
        )
        negative = bible.build_negative_prompt()

        subject_ref = self._build_subject_ref(bible, reference_id)
        style_ref = self._build_style_ref(bible, reference_id=reference_id + 10)

        logger.info("Subject+Style Reference 이미지 생성: %s", prompt[:100])

        try:
            result = self.vertex_client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=[subject_ref, style_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )

            if not result.generated_images:
                raise MediaGenerationError("SubjectRef", "이미지가 생성되지 않았습니다")

            filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            file_path = self.output_dir / filename
            result.generated_images[0].image.save(file_path)
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
            raise MediaGenerationError("SubjectRef", str(e))

    def generate_with_multi_bible(
        self,
        bibles: List[CharacterBible],
        prompt: str,
    ) -> MediaAsset:
        """다중 캐릭터 Subject Reference 이미지 생성 (나리[1] + 고양이[2] 등)"""
        refs = []
        for i, bible in enumerate(bibles, 1):
            if bible.reference_image_path:
                refs.append(self._build_subject_ref(bible, reference_id=i))

        if not refs:
            raise MediaGenerationError("SubjectRef", "레퍼런스 이미지가 없습니다")

        # 첫 번째 바이블의 Style Reference 추가 (화풍 통일)
        style_ref = self._build_style_ref(bibles[0], reference_id=len(bibles) + 10)
        refs.append(style_ref)

        # 모든 바이블의 네거티브 합산
        all_forbidden = set()
        for bible in bibles:
            all_forbidden.update(bible.forbidden)
        negative = ", ".join(all_forbidden)

        logger.info("다중 캐릭터+Style 이미지 생성 (%d명): %s", len(bibles), prompt[:100])

        try:
            result = self.vertex_client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=refs,
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )

            if not result.generated_images:
                raise MediaGenerationError("SubjectRef", "이미지가 생성되지 않았습니다")

            filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            file_path = self.output_dir / filename
            result.generated_images[0].image.save(file_path)

            return MediaAsset(
                asset_type=MediaType.IMAGE,
                file_path=str(file_path),
                prompt_used=prompt,
                status=AssetStatus.COMPLETED,
            )

        except MediaGenerationError:
            raise
        except Exception as e:
            raise MediaGenerationError("SubjectRef", str(e))

    def generate_reference_image(
        self, avatar_prompt: str, output_path: str = "",
    ) -> str:
        """캐릭터 레퍼런스 이미지 최초 생성 (Imagen 4 - API Key)"""
        if not self.api_client:
            raise MediaGenerationError("SubjectRef", "API 키가 설정되지 않았습니다")

        try:
            result = self.api_client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=avatar_prompt,
                config=types.GenerateImagesConfig(number_of_images=1),
            )

            if not result.generated_images:
                raise MediaGenerationError("SubjectRef", "레퍼런스 이미지 생성 실패")

            if not output_path:
                output_path = str(
                    self.output_dir
                    / f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
                )

            result.generated_images[0].image.save(output_path)
            logger.info("레퍼런스 이미지 생성: %s", output_path)
            return output_path

        except Exception as e:
            raise MediaGenerationError("SubjectRef", str(e))

    def _generate_basic(self, prompt: str) -> MediaAsset:
        """기본 이미지 생성 (Subject Reference 없이, Imagen 4)"""
        if not self.api_client:
            raise MediaGenerationError("SubjectRef", "API 키가 설정되지 않았습니다")

        try:
            result = self.api_client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1),
            )

            if not result.generated_images:
                raise MediaGenerationError("SubjectRef", "이미지가 생성되지 않았습니다")

            filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            file_path = self.output_dir / filename
            result.generated_images[0].image.save(file_path)

            return MediaAsset(
                asset_type=MediaType.IMAGE,
                file_path=str(file_path),
                prompt_used=prompt,
                status=AssetStatus.COMPLETED,
            )
        except Exception as e:
            raise MediaGenerationError("SubjectRef", str(e))

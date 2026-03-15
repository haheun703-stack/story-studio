
import logging
import os
from pathlib import Path
from typing import List
import re

from core.entities import Story, Character, MediaType, MediaAsset
from core.interfaces import IImageGenerator

logger = logging.getLogger(__name__)

class ImageGenerationService:
    def __init__(self, image_generator: IImageGenerator):
        self.image_generator = image_generator
        # Nano Banana 프롬프트 로드
        self.nano_banana_prompt = ""
        try:
            with open("nano_banana_prompt.txt", "r", encoding="utf-8") as f:
                self.nano_banana_prompt = f.read().strip()
            logger.info("Nano Banana 프롬프트 로드 완료")
        except FileNotFoundError:
            logger.warning("Nano Banana 프롬프트 파일을 찾을 수 없습니다.")

    def generate_character_images(self, characters: List[Character], style: str = "children's book illustration, cute, friendly, colorful, white background") -> List[MediaAsset]:
        """캐릭터들의 이미지를 생성합니다."""
        assets = []
        for char in characters:
            logger.info(f"캐릭터 '{char.name}' 이미지 생성 중...")
            try:
                # Nano Banana 프롬프트 적용 (주인공인 경우 또는 전체)
                final_prompt = char.avatar_prompt
                
                # 사용자의 요청: "위의 이름으로 사진을 넣어 놨어 참고해서 적용해줘"
                # Nano Banana 프롬프트는 캐릭터 시트를 만드는 프롬프트이므로 이를 적용
                if self.nano_banana_prompt:
                     # 캐릭터의 고유 특징이 있다면 Nano Banana 프롬프트와 결합할 수도 있지만,
                     # 일단 사용자가 제공한 프롬프트 스타일을 강력하게 적용
                     final_prompt = self.nano_banana_prompt
                     logger.info(f"  [Nano Banana] 프롬프트 적용: {final_prompt[:50]}...")

                asset = self.image_generator.generate_image(
                    prompt=final_prompt,
                    style="" # 프롬프트 자체에 스타일 포함됨
                )
                # 메타데이터 추가
                asset.metadata["character_name"] = char.name
                asset.metadata["role"] = char.role
                assets.append(asset)
            except Exception as e:
                logger.error(f"캐릭터 '{char.name}' 이미지 생성 실패: {e}")
        
        return assets

    def generate_scene_images(self, story: Story, max_scenes: int = 5, style: str = "children's book illustration, consistent character style") -> List[MediaAsset]:
        """스토리의 씬 이미지를 생성합니다. (비용 문제로 max_scenes 제한)"""
        assets = []
        
        # Nano Banana 핵심 외형 묘사 추출 (프롬프트에서 직접 가져옴)
        nano_appearance = "cute little girl with short straight brown bob hair, full fringe, light blue and white striped t-shirt, yellow overalls, brown flat shoes"
        nano_style = "vibrant 2D digital illustration, clean lines, soft gradient shading, watercolor-like blush, children's storybook art"

        for i, scene in enumerate(story.scenes[:max_scenes]):
            logger.info(f"씬 {scene.scene_number} 이미지 생성 중...")
            
            # 캐릭터 일관성을 위한 프롬프트 보정
            enhanced_prompt = scene.image_prompt
            
            # 1. Nano Banana 스타일 및 외형 강제 주입
            # 주인공(girl, character 등)이 등장하면 무조건 Nano Banana 외형으로 덮어씀
            if "girl" in enhanced_prompt.lower() or "character" in enhanced_prompt.lower() or "she" in enhanced_prompt.lower():
                 enhanced_prompt += f", {nano_appearance}"
            
            # 2. 스타일 강조
            final_prompt = f"{enhanced_prompt}, {nano_style}"
            logger.info(f"  [최종 프롬프트] {final_prompt[:100]}...")

            try:
                asset = self.image_generator.generate_image(
                    prompt=final_prompt,
                    style="" # 스타일은 이미 프롬프트에 포함됨
                )
                asset.metadata["scene_number"] = scene.scene_number
                assets.append(asset)
            except Exception as e:
                logger.error(f"씬 {scene.scene_number} 이미지 생성 실패: {e}")
        
        return assets

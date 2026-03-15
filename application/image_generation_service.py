import logging
import os
from pathlib import Path
from typing import List

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
                        # 한글 이름을 영문 묘사로 치환
                        enhanced_prompt = enhanced_prompt.replace(char_name_clean, f"a character named {english_name_part if english_name_part else 'main character'} ({char.visual_features})")            logger.info(f"씬 {scene.scene_number} 이미지 생성 중...")
                        found = True
                    # 캐릭터 일관성을 위한 프롬프트 보정
                    if found:_prompt = scene.image_prompt
                         logger.info(f"  [캐릭터 감지] {char.name} -> {char.visual_features[:30]}...")

            # Nano Banana 강제 적용 (주인공 소녀의 경우)                for char in story.characters:
            # 만약 프롬프트에 'girl', 'main character', 'child' 등이 있으면 Nano Banana 외형으로 덮어씀    # 씬 프롬프트에 캐릭터 이름(영어)이 포함되어 있으면 외형 묘사 추가
            if "girl" in enhanced_prompt.lower() or "character" in enhanced_prompt.lower():
                 enhanced_prompt += f", {nano_appearance}" (Bom)" 등으로 올 수 있으므로 정제
split('(')[0].strip()
            # 스타일 강조   english_name_part = ""
            final_prompt = f"{enhanced_prompt}, {nano_style}"
            logger.info(f"  [최종 프롬프트] {final_prompt[:100]}...")름이 있을 수 있음 "봄이 (Bom)"
ar.name.split('(')
            try:
                asset = self.image_generator.generate_image(                    english_name_part = parts[1].replace(')', '').strip()
                    prompt=final_prompt,
                    style="" # 스타일은 이미 프롬프트에 포함됨                    # 프롬프트에 한글 이름이나 영문 이름이 있는지 확인








        return assets                        logger.error(f"씬 {scene.scene_number} 이미지 생성 실패: {e}")            except Exception as e:                assets.append(asset)                asset.metadata["scene_number"] = scene.scene_number                )                    found = False
                    
                    # 1. 영문 이름이 있고 프롬프트에 포함된 경우 -> 영문 이름을 상세 묘사로 치환
                    if english_name_part and english_name_part.lower() in enhanced_prompt.lower():
                        replacement = f"{english_name_part} ({char.visual_features})"
                        # 대소문자 무시 치환을 위해 정규식 사용 권장되나 여기서는 간단히 replace (대소문자 차이 있을 수 있음)
                        # 단순화를 위해, 영문 이름이 정확히 일치하는 부분이 있으면 치환 시도
                        # 하지만 대소문자 문제를 해결하기 위해 re 모듈 사용이 좋음
                        import re
                        pattern = re.compile(re.escape(english_name_part), re.IGNORECASE)
                        enhanced_prompt = pattern.sub(replacement, enhanced_prompt)
                        found = True
                    
                    # 2. 한글 이름이 포함된 경우 (보통 영문 프롬프트라 없을 수 있지만 혹시 몰라)
                    elif char_name_clean in enhanced_prompt:
                        # 한글 이름을 영문 묘사로 치환
                        enhanced_prompt = enhanced_prompt.replace(char_name_clean, f"a character named {english_name_part if english_name_part else 'main character'} ({char.visual_features})")
                        found = True
                    
                    if found:
                         logger.info(f"  [캐릭터 감지] {char.name} -> {char.visual_features[:30]}...")

            # 중복 묘사를 방지하기 위해 앞단에 추가하는 로직은 제거 (치환 방식으로 변경했으므로)
            
            # 스타일 강조
            final_prompt = f"In the style of {style}, {enhanced_prompt}"
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

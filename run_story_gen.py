
import logging
from container import Container
from core.entities import TargetAudience, AgeGroup, Character, Story
from application.image_generation_service import ImageGenerationService

def main():
    # 1. 설정 및 컨테이너 초기화
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    container = Container()
    
    story_generator = container.story_generator()
    image_generator = container.image_generator()
    image_service = ImageGenerationService(image_generator)

    # 2. 사용자 입력 (또는 하드코딩)
    theme = "숲속 마을의 잃어버린 보물"
    audience = TargetAudience.PRE_SCHOOL # 3-7세

    print(f"=== 스토리 생성 시작: {theme} (대상: {audience.value}) ===")

    # 3. 스토리 및 캐릭터 생성
    story = story_generator.generate_story(audience, theme)
    
    print(f"\n=== 스토리 생성 완료: {story.title} ===")
    print(f"총 {len(story.scenes)}개의 씬이 생성되었습니다.")
    
    if story.characters:
        print(f"\n=== 등장인물 ({len(story.characters)}명) ===")
        for char in story.characters:
            print(f"- {char.name} ({char.role}): {char.description}")
    else:
        print("\n(캐릭터 정보가 생성되지 않았습니다.)")

    # 4. 캐릭터 이미지 생성
    print("\n=== 캐릭터 일러스트 생성 시작 ===")
    if story.characters:
        char_assets = image_service.generate_character_images(story.characters)
        for asset in char_assets:
            print(f"  [생성 완료] {asset.metadata['character_name']}: {asset.file_path}")
    
    # 5. 씬 이미지 생성 (테스트로 앞부분 3개만)
    print("\n=== 씬 일러스트 생성 시작 (앞부분 3개) ===")
    scene_assets = image_service.generate_scene_images(story, max_scenes=3)
    for asset in scene_assets:
        print(f"  [생성 완료] 씬 {asset.metadata['scene_number']}: {asset.file_path}")

    print("\n=== 모든 작업 완료 ===")

if __name__ == "__main__":
    main()

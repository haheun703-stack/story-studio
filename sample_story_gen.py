
import logging
import sys
from container import Container
from core.entities import TargetAudience, AgeGroup, Character, Story
from application.image_generation_service_v2 import ImageGenerationService

def main():
    # 1. 설정 및 컨테이너 초기화
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    container = Container()
    
    # 의존성 가져오기
    try:
        story_generator = container.story_generator()
        image_generator = container.image_generator()
        from application.image_generation_service_v2 import ImageGenerationService
        image_service = ImageGenerationService(image_generator)
    except Exception as e:
        print(f"오류: 필수 구성 요소를 초기화할 수 없습니다. .env 설정을 확인하세요.\n상세: {e}")
        return

    # 2. 주제 선정 (엄마가 유령이 되었어요 변형)
    # 주제: "내 단짝 친구 몽이가 구름이 되었어요" (반려견의 죽음을 다룸)
    theme = "내 단짝 강아지 몽이가 구름이 되어서 찾아왔어요"
    audience = TargetAudience.PRE_SCHOOL # 3-7세
    
    # 스타일: 따뜻하고 부드러운 수채화풍, 몽글몽글한 느낌
    art_style = "warm watercolor style, soft pastel colors, whimsical, touching, children's book illustration, fluffy clouds"

    print(f"=== 스토리 생성 시작: {theme} (대상: {audience.value}) ===")
    print(f"=== 아트 스타일: {art_style} ===")

    # 3. 스토리 및 캐릭터 생성
    try:
        # 샘플 생성을 위해 직접 Gemini 생성기 생성 (씬 개수 20개로 제한)
        from infrastructure.gemini_adapter import GeminiStoryGenerator
        story_generator = GeminiStoryGenerator(
            api_key=container.settings.llm.gemini_api_key,
            target_scene_count=20
        )
        
        story = story_generator.generate_story(audience, theme)
    except Exception as e:
        print(f"스토리 생성 중 오류 발생: {e}")
        return
    
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
        try:
            char_assets = image_service.generate_character_images(story.characters, style=art_style)
            for asset in char_assets:
                print(f"  [생성 완료] {asset.metadata['character_name']}: {asset.file_path}")
        except Exception as e:
            print(f"캐릭터 이미지 생성 중 오류: {e}")
    
    # 5. 씬 이미지 생성 (테스트로 앞부분 3개만)
    print("\n=== 씬 일러스트 생성 시작 (앞부분 3개) ===")
    try:
        scene_assets = image_service.generate_scene_images(story, max_scenes=3, style=art_style)
        for asset in scene_assets:
            print(f"  [생성 완료] 씬 {asset.metadata['scene_number']}: {asset.file_path}")
    except Exception as e:
        print(f"씬 이미지 생성 중 오류: {e}")

    print("\n=== 모든 작업 완료 ===")

if __name__ == "__main__":
    main()

"""
Story Studio 진입점
"""
import logging
import sys

from core.entities import Story, TargetAudience, Scene
from core.interfaces import IStoryGenerator


# 기존 MockStoryGenerator 유지 (하위 호환성 및 테스트용)
class MockStoryGenerator(IStoryGenerator):
    """IStoryGenerator 인터페이스를 임시로 구현한 더미(Mock) 클래스"""
    def generate_story(self, audience: TargetAudience, theme: str) -> Story:
        dummy_scenes = [
            Scene(
                scene_number=i,
                narration=f"테스트 나레이션 {i}",
                image_prompt="테스트 이미지 프롬프트",
                video_prompt="테스트 비디오 프롬프트",
            )
            for i in range(1, 156)
        ]
        return Story(
            title=f"더미 타이틀: {theme}",
            audience=audience,
            theme=theme,
            scenes=dummy_scenes,
        )


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from container import Container

    container = Container()

    if len(sys.argv) > 1:
        # CLI 모드: python main.py generate --theme "우주 정거장의 비밀"
        cli = container.cli()
        cli.run()
    else:
        # 기존 호환 모드: 인자 없이 실행 시 기존 동작 유지
        router = container.story_generator()
        print(f"\n  사용 가능한 LLM 제공자: {', '.join(router.available_providers)}")

        use_case = container.use_case()
        result_story = use_case.execute(
            TargetAudience.ELEMENTARY, "우주 정거장의 비밀"
        )

        print(f"\n{'='*60}")
        print(f"  생성된 스토리 제목: {result_story.title}")
        print(f"  생성된 씬 개수: {len(result_story.scenes)}")
        print(f"{'='*60}")

        print("\n  씬 미리보기 (처음 3개):")
        for scene in result_story.scenes[:3]:
            print(f"\n--- 씬 {scene.scene_number} ---")
            print(f"  나레이션: {scene.narration}")
            print(f"  이미지 프롬프트: {scene.image_prompt}")
            print(f"  비디오 프롬프트: {scene.video_prompt}")

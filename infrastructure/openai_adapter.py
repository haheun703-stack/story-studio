"""
OpenAI(GPT) 기반 스토리 생성 어댑터
IStoryGenerator 인터페이스를 구현합니다.
"""
import json
import logging

from core.entities import Story, Scene, TargetAudience
from core.interfaces import IStoryGenerator
from core.exceptions import StoryGenerationError

logger = logging.getLogger(__name__)


class OpenAIStoryGenerator(IStoryGenerator):
    """GPT 모델을 사용하여 동화 스토리를 생성하는 어댑터"""

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def generate_story(self, audience: TargetAudience, theme: str) -> Story:
        all_scenes: list[Scene] = []
        batch_num = 0

        while len(all_scenes) < 150:
            batch_num += 1
            start_scene = len(all_scenes) + 1
            remaining = 150 - len(all_scenes)
            request_count = min(remaining + 10, 50)

            prompt = self._build_prompt(audience, theme, start_scene, request_count, all_scenes)
            logger.info("OpenAI API 호출 중... (배치 %d, 씬 %d번부터 %d개 요청)", batch_num, start_scene, request_count)

            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": f"당신은 {audience.value} 대상 동화 작가입니다. JSON으로만 응답하세요."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.8,
                )
                response_text = response.choices[0].message.content
            except Exception as e:
                raise StoryGenerationError("OpenAI", str(e))

            new_scenes = self._parse_scenes(response_text, start_scene)
            all_scenes.extend(new_scenes)
            logger.info("%d개 씬 수신 (누적: %d개)", len(new_scenes), len(all_scenes))

        title = self._generate_title(audience, theme)
        return Story(title=title, audience=audience, theme=theme, scenes=all_scenes)

    def _build_prompt(self, audience: TargetAudience, theme: str, start: int, count: int, existing: list[Scene]) -> str:
        context = ""
        if existing:
            context = f'\n이전까지의 마지막 나레이션: "{existing[-1].narration}"\n이어서 씬 번호 {start}번부터 이전 이야기의 흐름을 자연스럽게 이어가세요.\n'

        return f"""주제: "{theme}"
{context}
아래 JSON 형식으로 정확히 {count}개의 씬(scene)을 생성하세요.
각 씬은 13~15분 분량의 롱폼 유튜브 영상의 한 장면입니다.

규칙:
- narration: {audience.value} 수준에 맞는 서술 (2~4문장)
- image_prompt: 해당 장면의 일러스트레이션 생성용 영어 프롬프트 (Midjourney 스타일)
- video_prompt: 해당 장면의 영상 생성용 영어 프롬프트 (Runway/Sora 스타일)

JSON 형식:
{{
  "scenes": [
    {{
      "scene_number": {start},
      "narration": "...",
      "image_prompt": "...",
      "video_prompt": "..."
    }}
  ]
}}"""

    def _generate_title(self, audience: TargetAudience, theme: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "JSON으로만 응답하세요."},
                    {"role": "user", "content": f'{audience.value} 대상 동화의 제목을 1개만 생성하세요.\n주제: "{theme}"\nJSON 형식: {{"title": "..."}}'},
                ],
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("title", f"{theme} 이야기")
        except Exception:
            return f"{theme} 이야기"

    def _parse_scenes(self, response_text: str, start_number: int) -> list[Scene]:
        try:
            data = json.loads(response_text)
            scenes_data = data.get("scenes", [])
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 빈 씬 목록 반환")
            return []

        return [
            Scene(
                scene_number=start_number + i,
                narration=s.get("narration", ""),
                image_prompt=s.get("image_prompt", ""),
                video_prompt=s.get("video_prompt", ""),
            )
            for i, s in enumerate(scenes_data)
        ]

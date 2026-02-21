import json
import logging
from google import genai
from google.genai import types
from core.entities import Story, TargetAudience, Scene, Character, AgeGroup
from core.interfaces import IStoryGenerator
from core.exceptions import StoryGenerationError

logger = logging.getLogger(__name__)


class GeminiStoryGenerator(IStoryGenerator):
    """
    Gemini 3.1 Pro를 사용하여 동화 스토리를 생성하는 어댑터.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-3.1-pro-preview", target_scene_count: int = 150):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.target_scene_count = target_scene_count

    def generate_story(self, audience: TargetAudience, theme: str) -> Story:
        # 캐릭터 생성
        characters = self._generate_characters(audience, theme)
        
        all_scenes: list[Scene] = []
        batch_num = 0

        # 목표 씬 수를 확보할 때까지 반복 생성
        while len(all_scenes) < self.target_scene_count:
            batch_num += 1
            start_scene = len(all_scenes) + 1
            remaining = self.target_scene_count - len(all_scenes)
            request_count = min(remaining + 10, 50)  # 배치당 최대 50씬

            if batch_num == 1:
                prompt = self._build_initial_prompt(audience, theme, request_count)
            else:
                prompt = self._build_continuation_prompt(
                    audience, theme, start_scene, request_count, all_scenes
                )

            logger.info("Gemini API 호출 중... (배치 %d, 씬 %d번부터 %d개 요청)", batch_num, start_scene, request_count)

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.8,
                    ),
                )
            except Exception as e:
                raise StoryGenerationError("Gemini", str(e))

            new_scenes = self._parse_scenes(response.text, start_scene)
            all_scenes.extend(new_scenes)
            logger.info("%d개 씬 수신 (누적: %d개)", len(new_scenes), len(all_scenes))

        # 타이틀 생성
        title = self._generate_title(audience, theme)

        return Story(
            title=title,
            audience=audience,
            theme=theme,
            scenes=all_scenes,
            characters=characters,
        )

    def _generate_characters(self, audience: TargetAudience, theme: str) -> list['Character']:
        from core.entities import Character, AgeGroup
        
        prompt = f"""당신은 {audience.value} 대상 동화 작가입니다.
주제: "{theme}"

이 동화에 등장할 주요 캐릭터 3~5명을 생성하세요.
각 캐릭터는 {audience.value}가 좋아할 만한 매력적인 외모와 성격을 가져야 합니다.

규칙:
- name: 캐릭터 이름
- role: 역할 (예: 주인공, 조력자, 악당 등)
- description: 성격 및 외모 묘사 (한국어)
- visual_features: 캐릭터 외형 상세 묘사 (영어, 일관성 유지를 위해 매우 구체적으로 작성: "5yo girl, short brown bob hair with bangs, round face, wearing yellow overalls and white t-shirt, red sneakers". 옷차림과 헤어스타일 고정)
- avatar_prompt: 캐릭터 전신 일러스트 생성용 영어 프롬프트 (Midjourney 스타일, 흰 배경, 전신 샷)

JSON 형식:
{{
  "characters": [
    {{
      "name": "...",
      "role": "...",
      "description": "...",
      "visual_features": "...",
      "avatar_prompt": "..."
    }}
  ]
}}"""

        logger.info("캐릭터 생성 중...")
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9,
                ),
            )
            data = json.loads(response.text)
            char_list = []
            for c in data.get("characters", []):
                char_list.append(Character(
                    name=c.get("name"),
                    role=c.get("role"),
                    age_group=AgeGroup.PRESCHOOL if audience == TargetAudience.PRE_SCHOOL else AgeGroup.ELEMENTARY,
                    description=c.get("description"),
                    visual_features=c.get("visual_features", c.get("avatar_prompt", "")), # fallback
                    avatar_prompt=c.get("avatar_prompt"),
                ))
            logger.info("캐릭터 %d명 생성 완료", len(char_list))
            return char_list
        except Exception as e:
            logger.error("캐릭터 생성 실패: %s", e)
            return []

    def _build_initial_prompt(self, audience: TargetAudience, theme: str, count: int) -> str:
        return f"""당신은 {audience.value} 대상 동화 작가입니다.
주제: "{theme}"

아래 JSON 형식으로 정확히 {count}개의 씬(scene)을 생성하세요.
각 씬은 13~15분 분량의 롱폼 유튜브 영상의 한 장면입니다.

규칙:
- narration: {audience.value} 수준에 맞는 서술 (2~4문장)
- image_prompt: 해당 장면의 일러스트레이션 생성용 영어 프롬프트 (Midjourney 스타일). **중요: 캐릭터의 외모(머리색, 옷 등)를 묘사하지 마세요. 오직 이름과 행동/표정만 묘사하세요.**
- video_prompt: 해당 장면의 영상 생성용 영어 프롬프트 (Runway/Sora 스타일)

JSON 형식:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "...",
      "image_prompt": "...",
      "video_prompt": "..."
    }}
  ]
}}"""

    def _build_continuation_prompt(
        self, audience: TargetAudience, theme: str,
        start: int, count: int, existing: list[Scene]
    ) -> str:
        last_narration = existing[-1].narration if existing else ""
        return f"""당신은 {audience.value} 대상 동화 작가입니다.
주제: "{theme}"

이전까지의 마지막 나레이션: "{last_narration}"

이어서 씬 번호 {start}번부터 {count}개의 씬을 생성하세요.
이전 이야기의 흐름을 자연스럽게 이어가세요.

규칙:
- narration: {audience.value} 수준에 맞는 서술 (2~4문장)
- image_prompt: 해당 장면의 일러스트레이션 생성용 영어 프롬프트 (Midjourney 스타일). **중요: 캐릭터의 외모(머리색, 옷 등)를 묘사하지 마세요. 오직 이름과 행동/표정만 묘사하세요.**
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
        prompt = f"""{audience.value} 대상 동화의 제목을 1개만 생성하세요.
주제: "{theme}"
JSON 형식: {{"title": "..."}}"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.9,
            ),
        )
        try:
            data = json.loads(response.text)
            return data.get("title", f"{theme} 이야기")
        except (json.JSONDecodeError, KeyError):
            return f"{theme} 이야기"

    def _parse_scenes(self, response_text: str, start_number: int) -> list[Scene]:
        try:
            data = json.loads(response_text)
            scenes_data = data.get("scenes", [])
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 빈 씬 목록 반환")
            return []

        scenes = []
        for i, s in enumerate(scenes_data):
            scenes.append(Scene(
                scene_number=start_number + i,
                narration=s.get("narration", ""),
                image_prompt=s.get("image_prompt", ""),
                video_prompt=s.get("video_prompt", ""),
            ))
        return scenes

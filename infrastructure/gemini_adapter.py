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

        age_guide = (
            "3~7세 유치부: 동글동글하고 귀여운 디자인, 밝은 파스텔 톤, 큰 눈과 작은 코, "
            "단순하고 알아보기 쉬운 실루엣, 동물이나 판타지 캐릭터 선호"
            if audience == TargetAudience.PRE_SCHOOL else
            "8~13세 초등부: 좀 더 디테일한 디자인, 생동감 있는 색감, "
            "또래 아이 캐릭터 또는 멋진 동물/로봇, 개성 있는 패션과 소품"
        )

        prompt = f"""당신은 {audience.value} 대상 아동 콘텐츠 전문 캐릭터 디자이너입니다.
주제: "{theme}"

## 목표
이 동화에 등장할 주요 캐릭터 3~5명을 생성하세요.

## 연령별 디자인 가이드
{age_guide}

## 캐릭터 설계 규칙
1. **name**: 한국어 이름 (2~3글자, 발음하기 쉬운 이름)
2. **role**: 역할 — 주인공(1명), 조력자(1~2명), 갈등 유발자 또는 멘토(0~1명)
3. **description**: 성격 + 외모 한국어 요약 (3문장 이내)
4. **visual_features**: 캐릭터 외형을 영어로 매우 구체적으로 묘사. 모든 씬에서 동일하게 적용되므로 아래 요소를 반드시 포함:
   - 종류/나이 (예: "7-year-old Korean girl", "baby fox character")
   - 머리 스타일과 색 (예: "short brown bob hair with bangs")
   - 얼굴 특징 (예: "round face, large brown eyes, small button nose")
   - 옷차림 고정 (예: "wearing yellow overalls over a white t-shirt")
   - 신발/액세서리 (예: "red sneakers, small star-shaped backpack")
5. **avatar_prompt**: 캐릭터 레퍼런스 시트용 영어 프롬프트. 반드시 포함:
   - visual_features 전체 내용
   - "full body character reference sheet, front view, white background"
   - "children's picture book illustration, clean line art, soft shading"

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
        narration_guide = (
            "유치부(3~7세) 수준: 짧고 단순한 문장, 의성어·의태어 활용, "
            "\"~했어요\" 존댓말 어미, 반복 구조로 리듬감"
            if audience == TargetAudience.PRE_SCHOOL else
            "초등부(8~13세) 수준: 묘사가 풍부한 서술체, 감정 표현과 대화 포함, "
            "\"~했다/~였다\" 서술체, 교훈적 메시지 자연스럽게 녹이기"
        )

        return f"""당신은 {audience.value} 대상 전문 동화 작가입니다.
주제: "{theme}"

## 목표
아래 JSON 형식으로 정확히 {count}개의 씬(scene)을 생성하세요.
전체 씬을 이어 붙이면 13~15분 분량의 유튜브 영상이 됩니다.

## 스토리 구조 가이드
- 도입(처음 20%): 배경과 캐릭터 소개, 일상 묘사
- 전개(20~50%): 사건 발생, 모험 시작, 새로운 만남
- 위기(50~75%): 갈등 고조, 시련과 도전
- 절정(75~90%): 최대 위기, 캐릭터 성장
- 결말(마지막 10%): 문제 해결, 교훈, 따뜻한 마무리

## 나레이션 작성 규칙
{narration_guide}
- 씬당 3~5문장 (TTS로 읽었을 때 약 5~6초 분량)
- 시각적 장면 전환이 분명하도록 각 씬의 장소/상황을 명시

## image_prompt 작성 규칙 (Imagen 4 최적화)
- 영어로 작성
- 구조: "[장면 설명], [배경/환경], [조명/분위기], children's picture book illustration, digital art"
- **중요: 캐릭터 외모(머리색, 옷 등)를 묘사하지 마세요. 캐릭터의 이름과 행동/표정/포즈만 묘사하세요. 외형은 별도로 자동 주입됩니다.**
- 예시: "a small girl joyfully jumping over a puddle, enchanted forest with glowing mushrooms, warm golden sunlight filtering through trees, children's picture book illustration, digital art"

## video_prompt 작성 규칙 (Veo 3.1 최적화)
- 영어로 작성
- 구조: "[카메라 워크], [캐릭터 동작], [배경 움직임], cinematic lighting, 8 seconds"
- 카메라 워크 예시: "slow zoom in", "tracking shot following", "wide establishing shot", "close-up on face"
- 예시: "slow zoom in on a small girl as she jumps over a puddle, water splashing around her feet, enchanted forest background with floating particles, warm cinematic lighting, 8 seconds"

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
        # 최근 3개 씬의 나레이션을 컨텍스트로 제공
        recent_narrations = [s.narration for s in existing[-3:]] if existing else []
        context_text = "\n".join(f"  씬 {existing[-len(recent_narrations)+i].scene_number}: {n}"
                                 for i, n in enumerate(recent_narrations))

        total_target = self.target_scene_count
        progress_pct = int(start / total_target * 100)

        # 스토리 아크 위치 판단
        if progress_pct < 20:
            arc_guide = "현재 '도입' 구간입니다. 배경과 캐릭터를 자연스럽게 소개하세요."
        elif progress_pct < 50:
            arc_guide = "현재 '전개' 구간입니다. 사건을 전개하고 새로운 만남/발견을 추가하세요."
        elif progress_pct < 75:
            arc_guide = "현재 '위기' 구간입니다. 갈등을 고조시키고 도전적 상황을 만드세요."
        elif progress_pct < 90:
            arc_guide = "현재 '절정' 구간입니다. 최대 위기를 만들고 캐릭터의 성장을 보여주세요."
        else:
            arc_guide = "현재 '결말' 구간입니다. 문제를 해결하고 따뜻한 교훈으로 마무리하세요."

        return f"""당신은 {audience.value} 대상 전문 동화 작가입니다.
주제: "{theme}"

## 이전 이야기 맥락 (최근 씬)
{context_text}

## 스토리 진행 상황
- 현재 씬 {start}번 / 전체 약 {total_target}씬 (진행률 {progress_pct}%)
- {arc_guide}

## 지시
이어서 씬 번호 {start}번부터 {count}개의 씬을 생성하세요.
이전 이야기의 감정선과 사건 흐름을 자연스럽게 이어가되, 새로운 장면 전환을 포함하세요.

## 작성 규칙 (초기 프롬프트와 동일)
- narration: {audience.value} 수준 서술 (3~5문장, TTS 5~6초 분량)
- image_prompt: 장면 일러스트 영어 프롬프트 (캐릭터 외모 묘사 금지, 이름+행동+표정만)
- video_prompt: 장면 영상 영어 프롬프트 (카메라 워크 + 캐릭터 동작 + 배경)

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
규칙: 한국어, 10자 이내, 호기심을 자극하는 제목, 부제목 없음
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

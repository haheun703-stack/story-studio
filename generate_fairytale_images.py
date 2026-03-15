import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
import requests

try:
    import google.generativeai as genai
    from openai import OpenAI
except ImportError:
    print("필요한 라이브러리가 설치되지 않았습니다. 터미널에서 'pip install -r requirements_auto.txt'를 실행해주세요.")
    exit(1)

# .env 파일에서 환경 변수를 자동으로 불러옵니다.
load_dotenv()

# ==========================================
# 0. API 및 인증 초기화
# ==========================================
# 1. Gemini API 설정 (LLM용)
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다. LLM 호출 시 오류가 발생할 수 있습니다.")
else:
    genai.configure(api_key=gemini_api_key)

# 2. OpenAI 설정 (DALL-E 3용)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다. 이미지 생성이 불가능합니다.")
else:
    client = OpenAI(api_key=openai_api_key)

# ==========================================
# 1. 고정값 세팅 (절대 변하지 않는 캐릭터와 화풍)
# ==========================================
CHARACTER_DNA = "A simple, highly stylized 2D children's book illustration. Flat hand-drawn watercolor, zero 3D elements. An adorable small, chubby-cheeked Asian baby girl with a brown bob-cut and tidy fringe. She is smiling joyfully with her mouth open and rosy cheeks. She is standing barefoot and centered, with both arms fully outstretched to the sides in a wide, welcoming gesture. She wears simple light yellow denim overalls with copper buttons, over a clean white short-sleeved t-shirt."
STYLE_DNA = "Absolutely NO 3D, NO CGI, NO photorealism. Extremely flat 2D vector-like pure watercolor wash. Minimalist and innocent style. The background is a clean white canvas with a soft, dreamlike arrangement of pastel blue and cream-colored watercolor clouds."

# ==========================================
# 2. 텍스트 AI API 호출 (Gemini - 대본 -> 장면별 JSON 변환)
# ==========================================
def analyze_story_to_scenes(story_text: str) -> list:
    """구글 Gemini API를 사용해 전체 대본을 여러 씬(행동/배경) 단위로 쪼개고 JSON으로 반환합니다."""
    system_prompt = """너는 동화책 일러스트레이터 디렉터야. 내가 줄 동화 대본을 읽고, 의미 있는 단위로 장면(Scene)을 나눠줘.
각 장면마다 캐릭터가 무엇을 하고 있는지(action), 배경은 어떤지(background) 영어로 1~2문장으로 묘사해 줘.
단, 캐릭터의 외모나 옷차림은 절대 묘사하지 마! (내가 나중에 합칠 거니까).
결과는 반드시 아래와 같은 순수 JSON 배열 형식으로만 출력해 줘. 

[
  {"scene_id": 1, "action_and_background": "walking on a muddy path in a dark forest, looking scared."},
  {"scene_id": 2, "action_and_background": "running joyfully towards a bright castle on a hill."}
]"""

    print("▶️ [1단계] 구글 Gemini API로 대본을 분석하여 장면을 분할합니다...")
    
    try:
        # gemini-1.5-pro 또는 gemini-2.5-flash 사용 가능
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_prompt)
        
        # response_mime_type을 application/json으로 설정하면 깔끔한 JSON만 반환합니다.
        response = model.generate_content(
            story_text,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        
        raw_content = response.text.strip()
        scenes_data = json.loads(raw_content)
        return scenes_data
    except Exception as e:
        print(f"❌ Gemini API 호출 또는 JSON 파싱 중 오류 발생: {e}")
        return []

# ==========================================
# 3. 이미지 생성 API 호출 (OpenAI DALL-E 3)
# ==========================================
def generate_image_for_scene(prompt: str, save_path: str):
    """최종 프롬프트를 DALL-E 3 API에 보내 이미지를 생성하고 로컬에 저장합니다."""
    print(f"   ⏳ 이미지 생성 중 (DALL-E 3)... 프롬프트: {prompt[:50]}...")

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # 이미지 다운로드 및 저장
        img_data = requests.get(image_url).content
        with open(save_path, 'wb') as handler:
            handler.write(img_data)
    except Exception as e:
        print(f"❌ 이미지 생성 중 오류 발생: {e}")

# ==========================================
# 메인 자동화 파이프라인
# ==========================================
def generate_fairytale_pipeline(story_text: str, output_dir: str = "output/automated_story"):
    # 0. 출력 폴더 생성
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # [1단계] 텍스트 AI를 호출하여 대본을 장면별 프롬프트(JSON)로 변환
    scenes_data = analyze_story_to_scenes(story_text)
    
    if not scenes_data:
        print("장면 데이터를 얻지 못해 파이프라인을 종료합니다.")
        return

    print(f"   👉 총 {len(scenes_data)}개의 장면이 추출되었습니다.\n")

    # [2단계 & 3단계] 파이썬이 DNA를 조립하고 이미지 생성기 호출
    for scene in scenes_data:
        scene_id = scene.get("scene_id", 0)
        action = scene.get("action_and_background", scene.get("action", ""))
        
        # [2단계] DNA + 행동/배경 + 화풍 결합!
        final_prompt = f"{CHARACTER_DNA} {action} {STYLE_DNA}"
        print(f"▶️ [2단계 & 3단계: {scene_id}번 씬] 프롬프트 조립 및 생성 시작")
        print(f"   - 조립된 프롬프트: {final_prompt}")
        
        # [3단계] 이미지 생성 및 폴더에 저장
        save_path = os.path.join(output_dir, f"scene_{scene_id}.png")
        generate_image_for_scene(final_prompt, save_path)
        
        # API Rate Limit (호출 빈도 제한) 방지를 위한 짧은 대기
        time.sleep(2)

    print("\n🎉 완벽합니다! 구글 AI(Gemini + Imagen 3)를 활용한 동화책 일러스트 렌더링이 완료되었습니다.")
    print(f"   결과물 폴더를 확인하세요: {os.path.abspath(output_dir)}")

# ==========================================
# 실행 테스트
# ==========================================
if __name__ == "__main__":
    # 사용자가 입력한 예시 대본
    raw_story_text = """
    옛날 옛적에 귀여운 꼬마 소녀가 평화로운 숲속을 걷고 있었어요. 소녀는 신기한 것들을 구경하며 즐겁게 걸었죠.
    그러다 멀리서 반짝이는 예쁜 언덕을 발견하고 기뻐서 달려갔어요!
    """
    
    print("===== 구글 생태계 동화 자동 생성 파이프라인 시작 =====")
    
    # 설정 확인 후 실행
    if os.getenv("GEMINI_API_KEY") and os.getenv("GCP_PROJECT_ID"):
        generate_fairytale_pipeline(raw_story_text)
    else:
        print("⚠️ GEMINI_API_KEY 또는 GCP_PROJECT_ID가 .env에 설정되지 않아 실제 실행은 보류합니다.")
        print("API 설정을 완료한 후 다시 실행해주세요!")

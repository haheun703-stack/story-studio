"""
Subject Reference Image 테스트 - 캐릭터 일관성 유지
Imagen 3 Capability 모델의 edit_image + SubjectReferenceImage를 사용하여
동일 캐릭터가 다른 장면에서도 같은 얼굴/외형을 유지하는지 테스트합니다.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')

# ── 캐릭터 레퍼런스 이미지 경로 ──────────────────────────────
REF_IMAGE_PATH = "output/media/characters/img_20260316_000033_347dc488.png"

# ── 테스트 장면 프롬프트 ───────────────────────────────────────
SCENES = [
    "a 5-year-old Korean girl[1] sitting in bed in a quiet morning room, hugging a teddy bear, "
    "soft morning sunlight through window, children's picture book illustration, pastel colors",

    "a 5-year-old Korean girl[1] being hugged by her father in the living room, "
    "warm and comforting atmosphere, gentle light, children's picture book illustration",

    "a 5-year-old Korean girl[1] standing at an open window at night, gentle magical wind blowing, "
    "her hair softly flowing, moonlit room, dreamy atmosphere, children's picture book illustration",
]

OUTPUT_DIR = Path("output/media/fairytale_subject_ref")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def test_with_api_key():
    """AI Studio API 키로 Subject Reference 테스트"""
    print("=" * 60)
    print("방법 1: AI Studio API Key + edit_image")
    print("=" * 60)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)

    # 레퍼런스 이미지 로드
    ref_image = types.Image.from_file(location=REF_IMAGE_PATH)

    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description="a 5-year-old Korean girl with short brown bob hair, yellow overalls, round face",
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    for i, prompt in enumerate(SCENES, 1):
        print(f"\n장면 {i} 생성 중...")
        try:
            result = client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=[subject_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    person_generation="ALLOW_ALL",
                ),
            )

            if result.generated_images:
                filename = f"scene_{i}_{datetime.now().strftime('%H%M%S')}.png"
                save_path = OUTPUT_DIR / filename
                result.generated_images[0].image.save(save_path)
                print(f"  저장 완료: {save_path}")
            else:
                print(f"  이미지 생성 실패 (빈 응답)")

        except Exception as e:
            print(f"  에러: {e}")
            return False

    return True


def test_with_vertex():
    """Vertex AI로 Subject Reference 테스트"""
    print("=" * 60)
    print("방법 2: Vertex AI + edit_image")
    print("=" * 60)

    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT,
        location="us-central1",
    )

    ref_image = types.Image.from_file(location=REF_IMAGE_PATH)

    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description="a 5-year-old Korean girl with short brown bob hair, yellow overalls, round face",
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    for i, prompt in enumerate(SCENES, 1):
        print(f"\n장면 {i} 생성 중...")
        try:
            result = client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=[subject_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    person_generation="ALLOW_ALL",
                ),
            )

            if result.generated_images:
                filename = f"scene_vtx_{i}_{datetime.now().strftime('%H%M%S')}.png"
                save_path = OUTPUT_DIR / filename
                result.generated_images[0].image.save(save_path)
                print(f"  저장 완료: {save_path}")
            else:
                print(f"  이미지 생성 실패 (빈 응답)")

        except Exception as e:
            print(f"  에러: {e}")
            return False

    return True


def test_gemini_native_image():
    """Gemini 네이티브 이미지 생성 (대화 컨텍스트로 일관성 유지)"""
    print("=" * 60)
    print("방법 3: Gemini 네이티브 이미지 생성 (참조 이미지 + 프롬프트)")
    print("=" * 60)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)

    # 레퍼런스 이미지를 대화에 포함
    ref_image = types.Part.from_image(types.Image.from_file(location=REF_IMAGE_PATH))

    scenes_korean = [
        "이 캐릭터가 아침 햇살이 비치는 조용한 방에서 침대에 앉아 곰인형을 안고 있는 장면을 그려주세요. "
        "파스텔 톤의 동화책 일러스트 스타일로, 이 캐릭터의 얼굴과 옷차림을 정확히 유지해주세요.",

        "이 캐릭터가 거실에서 아빠에게 안기고 있는 장면을 그려주세요. "
        "따뜻하고 포근한 분위기, 동화책 일러스트 스타일로, 이 캐릭터의 얼굴과 옷차림을 정확히 유지해주세요.",

        "이 캐릭터가 밤에 열린 창가에 서서 마법 같은 바람을 맞고 있는 장면을 그려주세요. "
        "머리카락이 살랑이고, 달빛이 비치는 몽환적인 분위기, 동화책 일러스트 스타일로, 이 캐릭터의 얼굴과 옷차림을 정확히 유지해주세요.",
    ]

    for i, scene_prompt in enumerate(scenes_korean, 1):
        print(f"\n장면 {i} 생성 중...")
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    ref_image,
                    scene_prompt,
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            # 이미지 파트 찾기
            saved = False
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    filename = f"scene_gemini_{i}_{datetime.now().strftime('%H%M%S')}.png"
                    save_path = OUTPUT_DIR / filename
                    save_path.write_bytes(part.inline_data.data)
                    print(f"  저장 완료: {save_path}")
                    saved = True
                    break

            if not saved:
                print(f"  이미지 응답 없음 (텍스트만 반환됨)")

        except Exception as e:
            print(f"  에러: {e}")
            return False

    return True


if __name__ == "__main__":
    if not Path(REF_IMAGE_PATH).exists():
        print(f"레퍼런스 이미지 없음: {REF_IMAGE_PATH}")
        sys.exit(1)

    print(f"레퍼런스 이미지: {REF_IMAGE_PATH}")
    print(f"GCP 프로젝트: {GCP_PROJECT}")
    print(f"출력 디렉토리: {OUTPUT_DIR}")
    print()

    # 방법 1: API Key + edit_image
    success = test_with_api_key()

    if not success:
        print("\n API Key 방식 실패, Vertex AI로 재시도...\n")
        success = test_with_vertex()

    if not success:
        print("\n Vertex AI도 실패, Gemini 네이티브 이미지 생성으로 재시도...\n")
        success = test_gemini_native_image()

    if success:
        print(f"\n테스트 완료! 결과: {OUTPUT_DIR}")
    else:
        print("\n모든 방법 실패. 아래 사항을 확인하세요:")
        print("1. GEMINI_API_KEY가 유효한지")
        print("2. Vertex AI API가 활성화되어 있는지")
        print("3. gcloud auth application-default login을 실행했는지")

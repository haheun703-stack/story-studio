"""
다중 캐릭터 Subject Reference 테스트
- 동물 (고양이) + 사람 (아빠) 캐릭터 일관성 검증
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')

OUTPUT_DIR = Path("output/media/multi_char_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# 1단계: 레퍼런스 캐릭터 이미지 생성 (Imagen 4 - API Key)
# ═══════════════════════════════════════════════════════════════

CAT_PROMPT = (
    "a small fluffy gray kitten with bright green eyes, white paws, "
    "pink nose, round face, playful expression, "
    "children's storybook illustration, soft lines, pastel colors, "
    "full body, white background, character reference sheet, "
    "no text, no watermark"
)

DAD_PROMPT = (
    "a warm gentle Korean father, early 30s, short neat black hair, "
    "round glasses, kind smile, slightly chubby face, "
    "wearing a light blue button-up shirt and khaki pants, "
    "children's storybook illustration, soft lines, pastel colors, "
    "full body, white background, character reference sheet, "
    "no text, no watermark"
)


def generate_reference_images():
    """Imagen 4로 레퍼런스 캐릭터 이미지 생성"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    refs = {}

    for name, prompt in [("cat", CAT_PROMPT), ("dad", DAD_PROMPT)]:
        print(f"레퍼런스 생성: {name}...")
        ref_path = OUTPUT_DIR / f"ref_{name}.png"

        if ref_path.exists():
            print(f"  이미 존재: {ref_path}")
            refs[name] = ref_path
            continue

        try:
            result = client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1),
            )
            if result.generated_images:
                result.generated_images[0].image.save(ref_path)
                print(f"  저장: {ref_path}")
                refs[name] = ref_path
        except Exception as e:
            print(f"  에러: {e}")

    return refs


# ═══════════════════════════════════════════════════════════════
# 2단계: Subject Reference로 장면 생성
# ═══════════════════════════════════════════════════════════════

# 고양이 장면들
CAT_SCENES = [
    "a small gray kitten[1] sitting on a sunny windowsill, looking outside curiously, "
    "butterflies flying outside, children's storybook illustration, warm light",

    "a small gray kitten[1] playing with a ball of yarn in a cozy living room, "
    "playful pose, tail up, children's storybook illustration, soft pastel colors",

    "a small gray kitten[1] sleeping curled up on a soft cushion, "
    "peaceful sleeping face, children's storybook illustration, moonlit room",
]

# 아빠 장면들
DAD_SCENES = [
    "a Korean father[1] cooking in the kitchen, wearing an apron, "
    "stirring a pot with a gentle smile, warm kitchen light, "
    "children's storybook illustration, pastel colors",

    "a Korean father[1] reading a storybook to his child on the sofa, "
    "cozy living room, warm lamp light, "
    "children's storybook illustration, soft pastel tones",

    "a Korean father[1] walking in a park holding hands with the air beside him, "
    "cherry blossom trees, spring atmosphere, "
    "children's storybook illustration, warm sunlight",
]

# 나리 (기존 캐릭터) + 고양이 함께 나오는 장면
TOGETHER_SCENES = [
    # 나리[1] + 고양이[2] 함께
    "a 5-year-old Korean girl[1] sitting on the grass with a small gray kitten[2] on her lap, "
    "garden with colorful flowers, warm afternoon sunlight, "
    "children's storybook illustration, pastel colors",

    "a 5-year-old Korean girl[1] and a small gray kitten[2] looking at a butterfly together, "
    "flower meadow, blue sky, "
    "children's storybook illustration, soft warm tones",
]


def test_single_character(client, types, name, ref_path, subject_type, description, scenes, prefix):
    """단일 캐릭터 Subject Reference 테스트"""
    ref_image = types.Image.from_file(location=str(ref_path))

    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description=description,
            subject_type=subject_type,
        ),
    )

    print(f"\n{'='*50}")
    print(f"{name} 캐릭터 테스트 ({subject_type})")
    print(f"{'='*50}")

    for i, prompt in enumerate(scenes, 1):
        print(f"  장면 {i} 생성 중...")
        try:
            result = client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=[subject_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    person_generation="ALLOW_ALL",
                    negative_prompt="text, watermark, 3D render, realistic photo, horror",
                ),
            )
            if result.generated_images:
                filename = f"{prefix}_{i}_{datetime.now().strftime('%H%M%S')}.png"
                save_path = OUTPUT_DIR / filename
                result.generated_images[0].image.save(save_path)
                size_kb = save_path.stat().st_size / 1024
                print(f"    저장: {save_path} ({size_kb:.0f}KB)")
            else:
                print(f"    실패: 빈 응답")
        except Exception as e:
            print(f"    에러: {e}")
            return False
    return True


def test_two_characters(client, types, nari_ref_path, cat_ref_path):
    """두 캐릭터 동시 Subject Reference 테스트"""
    nari_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=types.Image.from_file(location=str(nari_ref_path)),
        config=types.SubjectReferenceConfig(
            subject_description="a 5-year-old Korean girl with brown bob hair and yellow overalls",
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )
    cat_ref = types.SubjectReferenceImage(
        reference_id=2,
        reference_image=types.Image.from_file(location=str(cat_ref_path)),
        config=types.SubjectReferenceConfig(
            subject_description="a small fluffy gray kitten with green eyes",
            subject_type="SUBJECT_TYPE_ANIMAL",
        ),
    )

    print(f"\n{'='*50}")
    print(f"나리 + 고양이 함께 테스트 (2캐릭터 동시)")
    print(f"{'='*50}")

    for i, prompt in enumerate(TOGETHER_SCENES, 1):
        print(f"  장면 {i} 생성 중...")
        try:
            result = client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=[nari_ref, cat_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    person_generation="ALLOW_ALL",
                    negative_prompt="text, watermark, 3D render, realistic photo",
                ),
            )
            if result.generated_images:
                filename = f"together_{i}_{datetime.now().strftime('%H%M%S')}.png"
                save_path = OUTPUT_DIR / filename
                result.generated_images[0].image.save(save_path)
                size_kb = save_path.stat().st_size / 1024
                print(f"    저장: {save_path} ({size_kb:.0f}KB)")
            else:
                print(f"    실패: 빈 응답")
        except Exception as e:
            print(f"    에러: {e}")
            return False
    return True


if __name__ == "__main__":
    NARI_REF = Path("output/media/characters/img_20260316_000033_347dc488.png")
    if not NARI_REF.exists():
        print(f"나리 레퍼런스 없음: {NARI_REF}")
        sys.exit(1)

    # 1단계: 고양이/아빠 레퍼런스 이미지 생성
    print("=" * 60)
    print("1단계: 레퍼런스 캐릭터 이미지 생성")
    print("=" * 60)
    refs = generate_reference_images()

    if "cat" not in refs or "dad" not in refs:
        print("레퍼런스 생성 실패")
        sys.exit(1)

    # 2단계: Vertex AI로 Subject Reference 테스트
    print("\n" + "=" * 60)
    print("2단계: Subject Reference 장면 생성 (Vertex AI)")
    print("=" * 60)

    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")

    # 고양이 테스트
    cat_ok = test_single_character(
        client, types, "고양이", refs["cat"],
        "SUBJECT_TYPE_ANIMAL",
        "a small fluffy gray kitten with green eyes and white paws",
        CAT_SCENES, "cat"
    )

    # 아빠 테스트
    dad_ok = test_single_character(
        client, types, "아빠", refs["dad"],
        "SUBJECT_TYPE_PERSON",
        "a Korean father in his 30s with glasses and blue shirt",
        DAD_SCENES, "dad"
    )

    # 두 캐릭터 동시 테스트
    together_ok = False
    if cat_ok:
        together_ok = test_two_characters(client, types, NARI_REF, refs["cat"])

    print(f"\n{'='*60}")
    print(f"결과 요약")
    print(f"{'='*60}")
    print(f"  고양이 단독: {'성공' if cat_ok else '실패'}")
    print(f"  아빠 단독:   {'성공' if dad_ok else '실패'}")
    print(f"  나리+고양이: {'성공' if together_ok else '실패'}")
    print(f"  출력: {OUTPUT_DIR}")

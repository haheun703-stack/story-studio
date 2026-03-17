"""
Triple Reference 테스트:
Subject(캐릭터) + Style(화풍) + Control(FACE_MESH) 동시 적용

목표: 10장 연속 생성하면서 캐릭터 일관성 최대화
"""

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')
API_KEY = os.getenv("GEMINI_API_KEY", "")

OUTPUT_DIR = Path("output/media/triple_ref_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SOYUL_BIBLE = {
    "immutable": {
        "age": "6-7 year old Korean girl",
        "hair": "dark brown hair in two low pigtails with red hair ties",
        "eyes": "large round dark brown eyes with long eyelashes",
        "face": "round soft face, rosy pink cheeks, small button nose",
        "skin": "warm fair skin",
    },
    "semi_fixed": {
        "outfit": "cream-colored knit sweater and denim overalls",
        "shoes": "yellow rain boots",
    },
    "forbidden": [
        "long loose hair", "different eye color", "older child",
        "realistic adult proportions", "dark horror mood",
        "3D render", "text", "watermark", "extra fingers",
        "different child", "harsh shadows",
    ],
    "art_style": (
        "warm emotional children's storybook illustration, "
        "soft watercolor texture, gentle warm lighting, "
        "pastel palette with warm golden tones, clean composition"
    ),
    "avatar_prompt": (
        "a 6-7 year old Korean girl with dark brown hair in two low pigtails "
        "with red hair ties, large round dark brown eyes, round soft face, "
        "rosy pink cheeks, wearing cream knit sweater and denim overalls, "
        "yellow rain boots, warm children's storybook illustration, "
        "full body, white background, character reference sheet, "
        "no text, no watermark"
    ),
}


def build_char_block(bible: dict) -> str:
    parts = list(bible["immutable"].values()) + list(bible["semi_fixed"].values())
    return ", ".join(parts)


SCENES_10 = [
    "the girl[1] standing in a sunny flower garden, smiling happily, butterflies around her",
    "the girl[1] sitting under a big tree reading a picture book, autumn leaves falling",
    "the girl[1] running through puddles in the rain, splashing water, laughing",
    "the girl[1] building a snowman in a snowy park, mittens on her hands",
    "the girl[1] painting with watercolors at a small table, colorful paints everywhere",
    "the girl[1] feeding a small white puppy in a warm kitchen",
    "the girl[1] looking up at a night sky full of stars, standing on a hill",
    "the girl[1] riding a bicycle along a riverside path, wind in her hair",
    "the girl[1] blowing out candles on a birthday cake, party decorations",
    "the girl[1] sleeping peacefully in bed, hugging a teddy bear, moonlight through window",
]


def main():
    from google import genai
    from google.genai import types

    api_client = genai.Client(api_key=API_KEY)
    vtx_client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")

    negative = ", ".join(SOYUL_BIBLE["forbidden"])

    # ── 1. 레퍼런스 이미지 생성 ──
    ref_path = OUTPUT_DIR / "ref_soyul.png"
    if not ref_path.exists():
        print("레퍼런스 이미지 생성 중...")
        result = api_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=SOYUL_BIBLE["avatar_prompt"],
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        if result.generated_images:
            result.generated_images[0].image.save(ref_path)
            print(f"  레퍼런스 저장: {ref_path}")
        else:
            print("레퍼런스 생성 실패!")
            return
    else:
        print(f"레퍼런스 이미 존재: {ref_path}")

    ref_image = types.Image.from_file(location=str(ref_path))
    char_desc = build_char_block(SOYUL_BIBLE)

    # ── 2. 방법 A: Subject Reference만 (기존) ──
    print("\n" + "=" * 60)
    print("방법 A: SubjectReference만 (기존 방식)")
    print("=" * 60)

    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description=char_desc,
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    for i, scene_prompt in enumerate(SCENES_10):
        out_path = OUTPUT_DIR / f"A_{i:02d}.png"
        if out_path.exists():
            print(f"  A_{i:02d}: 이미 존재, 스킵")
            continue
        full_prompt = f"{scene_prompt}, {SOYUL_BIBLE['art_style']}"
        print(f"  A_{i:02d}: 생성 중...")
        try:
            result = vtx_client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=full_prompt,
                reference_images=[subject_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )
            if result.generated_images:
                result.generated_images[0].image.save(out_path)
                print(f"    저장: {out_path}")
            else:
                print(f"    실패: 빈 응답")
        except Exception as e:
            print(f"    에러: {e}")

    # ── 3. 방법 B: Subject + Style 동시 적용 ──
    print("\n" + "=" * 60)
    print("방법 B: Subject + Style Reference 동시 적용")
    print("=" * 60)

    style_ref = types.StyleReferenceImage(
        reference_image=ref_image,
        config=types.StyleReferenceConfig(
            style_description=(
                "warm emotional children's storybook illustration, "
                "soft watercolor texture, gentle warm lighting, "
                "pastel palette with warm golden tones, "
                "consistent character design, same art style throughout"
            ),
        ),
    )

    for i, scene_prompt in enumerate(SCENES_10):
        out_path = OUTPUT_DIR / f"B_{i:02d}.png"
        if out_path.exists():
            print(f"  B_{i:02d}: 이미 존재, 스킵")
            continue
        full_prompt = f"{scene_prompt}, {SOYUL_BIBLE['art_style']}"
        print(f"  B_{i:02d}: 생성 중...")
        try:
            result = vtx_client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=full_prompt,
                reference_images=[subject_ref, style_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )
            if result.generated_images:
                result.generated_images[0].image.save(out_path)
                print(f"    저장: {out_path}")
            else:
                print(f"    실패: 빈 응답")
        except Exception as e:
            print(f"    에러: {e}")

    # ── 4. 방법 C: Subject + Control(FACE_MESH) 동시 적용 ──
    print("\n" + "=" * 60)
    print("방법 C: Subject + Control(FACE_MESH) 동시 적용")
    print("=" * 60)

    face_ref = types.ControlReferenceImage(
        reference_image=ref_image,
        config=types.ControlReferenceConfig(
            control_type="CONTROL_TYPE_FACE_MESH",
            enable_control_image_computation=True,
        ),
    )

    for i, scene_prompt in enumerate(SCENES_10):
        out_path = OUTPUT_DIR / f"C_{i:02d}.png"
        if out_path.exists():
            print(f"  C_{i:02d}: 이미 존재, 스킵")
            continue
        full_prompt = f"{scene_prompt}, {SOYUL_BIBLE['art_style']}"
        print(f"  C_{i:02d}: 생성 중...")
        try:
            result = vtx_client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=full_prompt,
                reference_images=[subject_ref, face_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )
            if result.generated_images:
                result.generated_images[0].image.save(out_path)
                print(f"    저장: {out_path}")
            else:
                print(f"    실패: 빈 응답")
        except Exception as e:
            print(f"    에러: {e}")

    # ── 5. 방법 D: Subject + Style + Control(FACE_MESH) 트리플 ──
    print("\n" + "=" * 60)
    print("방법 D: Subject + Style + Control(FACE_MESH) 트리플!")
    print("=" * 60)

    for i, scene_prompt in enumerate(SCENES_10):
        out_path = OUTPUT_DIR / f"D_{i:02d}.png"
        if out_path.exists():
            print(f"  D_{i:02d}: 이미 존재, 스킵")
            continue
        full_prompt = f"{scene_prompt}, {SOYUL_BIBLE['art_style']}"
        print(f"  D_{i:02d}: 생성 중...")
        try:
            result = vtx_client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=full_prompt,
                reference_images=[subject_ref, style_ref, face_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )
            if result.generated_images:
                result.generated_images[0].image.save(out_path)
                print(f"    저장: {out_path}")
            else:
                print(f"    실패: 빈 응답")
        except Exception as e:
            print(f"    에러: {e}")

    print("\n" + "=" * 60)
    print("완료! 4가지 방법 x 10장 = 최대 40장 생성")
    print(f"출력: {OUTPUT_DIR}")
    print("  A_* = Subject만")
    print("  B_* = Subject + Style")
    print("  C_* = Subject + FaceMesh")
    print("  D_* = Subject + Style + FaceMesh (트리플)")


if __name__ == "__main__":
    main()

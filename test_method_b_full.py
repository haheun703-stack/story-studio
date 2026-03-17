"""
방법 B (Subject + Style) 풀 10장 테스트
이미 B_00~02는 생성됨, B_03~09 추가 생성
"""

import os, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')
OUTPUT_DIR = Path("output/media/triple_ref_test")

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

DELAY = 15


def main():
    from google import genai
    from google.genai import types

    vtx_client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")

    ref_path = OUTPUT_DIR / "ref_soyul.png"
    ref_image = types.Image.from_file(location=str(ref_path))
    char_desc = build_char_block(SOYUL_BIBLE)
    negative = ", ".join(SOYUL_BIBLE["forbidden"])

    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description=char_desc,
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    style_ref = types.StyleReferenceImage(
        reference_id=2,
        reference_image=ref_image,
        config=types.StyleReferenceConfig(
            style_description=(
                "warm emotional children's storybook illustration, "
                "soft watercolor texture, gentle warm lighting, "
                "pastel palette with warm golden tones, "
                "consistent character design"
            ),
        ),
    )

    print("방법 B (Subject + Style) 풀 10장 생성")
    print("=" * 60)

    success = 0
    for i, scene_prompt in enumerate(SCENES_10):
        out_path = OUTPUT_DIR / f"B_{i:02d}.png"
        if out_path.exists():
            print(f"  B_{i:02d}: 이미 존재, 스킵")
            success += 1
            continue

        full_prompt = f"{scene_prompt}, {SOYUL_BIBLE['art_style']}"
        print(f"  B_{i:02d}: 생성 중...")
        time.sleep(DELAY)

        for attempt in range(3):
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
                    size_kb = out_path.stat().st_size / 1024
                    print(f"    저장: {out_path} ({size_kb:.0f}KB)")
                    success += 1
                    break
                else:
                    print(f"    빈 응답, 재시도 {attempt+1}/3")
                    time.sleep(30)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 60 * (attempt + 1)
                    print(f"    쿼타 초과! {wait}초 대기 후 재시도 {attempt+1}/3")
                    time.sleep(wait)
                else:
                    print(f"    에러: {e}")
                    break

    print(f"\n완료! 성공: {success}/10")
    print(f"출력: {OUTPUT_DIR}/B_*.png")


if __name__ == "__main__":
    main()

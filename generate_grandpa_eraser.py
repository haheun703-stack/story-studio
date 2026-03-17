"""
「할아버지의 지우개」 전체 동화 이미지 생성
캐릭터 바이블 + Subject Reference 파이프라인 통합 테스트
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')

OUTPUT_DIR = Path("output/media/grandpa_eraser")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 캐릭터 바이블
# ═══════════════════════════════════════════════════════════════

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
    "subject_type": "SUBJECT_TYPE_PERSON",
    "avatar_prompt": (
        "a 6-7 year old Korean girl with dark brown hair in two low pigtails "
        "with red hair ties, large round dark brown eyes, round soft face, "
        "rosy pink cheeks, wearing cream knit sweater and denim overalls, "
        "yellow rain boots, warm children's storybook illustration, "
        "full body, white background, character reference sheet, "
        "no text, no watermark"
    ),
}

GRANDPA_BIBLE = {
    "immutable": {
        "age": "70-year-old gentle Korean grandfather",
        "hair": "white silver hair, slightly messy and thin on top",
        "eyes": "small gentle eyes behind big round tortoiseshell glasses",
        "face": "wrinkled kind face with deep smile lines, warm gentle smile",
        "skin": "aged warm skin with light wrinkles",
    },
    "semi_fixed": {
        "outfit": "brown wool cardigan over a checkered shirt, beige pants",
        "accessories": "big round tortoiseshell glasses",
    },
    "forbidden": [
        "young face", "no glasses", "dark hair", "muscular build",
        "realistic photo", "3D render", "text", "watermark",
        "harsh shadows", "different person",
    ],
    "art_style": (
        "warm emotional children's storybook illustration, "
        "soft watercolor texture, gentle warm lighting, "
        "pastel palette with warm golden tones, clean composition"
    ),
    "subject_type": "SUBJECT_TYPE_PERSON",
    "avatar_prompt": (
        "a 70-year-old gentle Korean grandfather with white silver hair, "
        "big round tortoiseshell glasses, wrinkled kind face with smile lines, "
        "wearing brown wool cardigan over checkered shirt, beige pants, "
        "warm gentle expression, children's storybook illustration, "
        "full body, white background, character reference sheet, "
        "no text, no watermark"
    ),
}


# ═══════════════════════════════════════════════════════════════
# 16장 + 표지 장면 정의
# ═══════════════════════════════════════════════════════════════

SCENES = [
    {
        "id": "00_cover",
        "chars": "both",
        "prompt": (
            "the grandfather[1] and the little girl[2] sitting together at a table, "
            "drawing pictures with colored pencils, warm golden light, "
            "a pink eraser on the table, scattered drawings around them, "
            "heartwarming atmosphere, title illustration composition"
        ),
    },
    {
        "id": "01",
        "chars": "grandpa",
        "prompt": (
            "the grandfather[1] sitting at a wooden table happily painting a picture, "
            "a sun and mountains drawn on the paper, golden warm light shining, "
            "paint brushes and watercolors on the table, peaceful cozy room"
        ),
    },
    {
        "id": "02",
        "chars": "none",
        "prompt": (
            "silhouette of an elderly man's head in profile, "
            "inside the head a small pink eraser is floating, "
            "question marks scattered around inside, "
            "soft dreamy atmosphere, metaphorical illustration, "
            "warm emotional children's storybook illustration, "
            "soft watercolor texture, pastel palette"
        ),
    },
    {
        "id": "03",
        "chars": "none",
        "prompt": (
            "memory bubbles floating in the air, a house, a key, eyeglasses, "
            "each bubble becoming transparent and fading away, "
            "a pink eraser sweeping across leaving eraser dust, "
            "dreamlike ethereal atmosphere, "
            "warm emotional children's storybook illustration, "
            "soft watercolor texture, pastel palette"
        ),
    },
    {
        "id": "04",
        "chars": "grandpa",
        "prompt": (
            "the grandfather[1] wearing his big round glasses on his nose, "
            "looking confused with a thought bubble saying question mark, "
            "a key lying on the floor nearby, "
            "gentle humorous atmosphere, cozy living room"
        ),
    },
    {
        "id": "05",
        "chars": "grandpa",
        "prompt": (
            "the grandfather[1] standing alone in the middle of an empty street "
            "between buildings, looking lost and confused, "
            "question marks floating around him, "
            "small lonely figure, quiet melancholy atmosphere, "
            "soft muted colors"
        ),
    },
    {
        "id": "06",
        "chars": "both",
        "prompt": (
            "the grandfather[1] with arms wide open, beaming with joy, "
            "the little girl[2] running toward him happily, "
            "small hearts floating between them, "
            "warm golden light, loving atmosphere, cozy living room"
        ),
    },
    {
        "id": "07",
        "chars": "both",
        "prompt": (
            "the grandfather[1] looking at the little girl[2] with blank confused eyes, "
            "speech bubble with question mark, "
            "the girl standing still with shocked frozen expression, "
            "cold quiet winter atmosphere, muted blue tones, "
            "emotional moment"
        ),
    },
    {
        "id": "08",
        "chars": "soyul",
        "prompt": (
            "the little girl[1] curled up under a blanket in a dark room, "
            "moonlight through the window, eyes closed, "
            "a single tear rolling down her cheek, "
            "quiet sad atmosphere, soft blue moonlight"
        ),
    },
    {
        "id": "09",
        "chars": "soyul",
        "prompt": (
            "the little girl[1] under a blanket with a bright lightbulb glowing "
            "above her head, eyes sparkling with determination, "
            "hopeful expression, idea moment, "
            "warm light breaking through darkness"
        ),
    },
    {
        "id": "10",
        "chars": "both",
        "prompt": (
            "the little girl[2] sitting at a table excitedly drawing pictures, "
            "colored pencils and crayons scattered around, "
            "multiple papers with drawings on the table, "
            "the grandfather[1] sitting beside her watching warmly, "
            "bright cheerful atmosphere, warm sunlight"
        ),
    },
    {
        "id": "11",
        "chars": "soyul",
        "prompt": (
            "the little girl[1] holding up two crayon drawings proudly, "
            "one showing a fish-shaped bread with two people, "
            "another showing a snowman with two people, "
            "childlike crayon art style within the drawings, "
            "bright happy expression"
        ),
    },
    {
        "id": "12",
        "chars": "grandpa",
        "prompt": (
            "the grandfather[1] holding a child's drawing, eyes gently closed, "
            "peaceful warm smile on his face, rosy cheeks, "
            "warm golden light surrounding him, "
            "serene peaceful atmosphere, emotional moment"
        ),
    },
    {
        "id": "13",
        "chars": "grandpa",
        "prompt": (
            "close-up of the grandfather[1]'s trembling hand holding a pencil, "
            "drawing a wobbly circle on white paper, "
            "the beginning of a face, "
            "emotional intimate moment, soft warm lighting"
        ),
    },
    {
        "id": "14",
        "chars": "none",
        "prompt": (
            "a piece of white paper with a childlike wobbly drawing of "
            "a round smiling face, beneath it shaky handwritten Korean text, "
            "small teardrops on the paper, warm light glowing around the paper, "
            "emotional climax moment, "
            "warm emotional children's storybook illustration, "
            "soft watercolor texture"
        ),
    },
    {
        "id": "15",
        "chars": "none",
        "prompt": (
            "abstract symbolic scene, on the left a translucent pink eraser "
            "passing by leaving eraser dust, "
            "in the center a large glowing heart with three layers of warm light, "
            "the heart cannot be erased and shines brightly, "
            "metaphorical illustration about love and memory, "
            "warm emotional children's storybook illustration, "
            "soft watercolor texture, golden warm tones"
        ),
    },
    {
        "id": "16",
        "chars": "both",
        "prompt": (
            "the grandfather[1] and the little girl[2] holding hands side by side, "
            "their drawings floating around them like butterflies, "
            "warm golden light wrapping around both of them, "
            "peaceful hopeful ending atmosphere, "
            "full body, facing forward together"
        ),
    },
]


# ═══════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════

def build_char_block(bible: dict) -> str:
    parts = list(bible["immutable"].values()) + list(bible["semi_fixed"].values())
    return ", ".join(parts)


def build_negative(bible: dict) -> str:
    return ", ".join(bible["forbidden"])


def main():
    from google import genai
    from google.genai import types

    api_client = genai.Client(api_key=API_KEY)
    vtx_client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")

    # ── 1. 레퍼런스 이미지 생성 ──
    print("=" * 60)
    print("1단계: 레퍼런스 캐릭터 이미지 생성")
    print("=" * 60)

    refs = {}
    for name, bible in [("soyul", SOYUL_BIBLE), ("grandpa", GRANDPA_BIBLE)]:
        ref_path = OUTPUT_DIR / f"ref_{name}.png"
        if ref_path.exists():
            print(f"  {name}: 이미 존재 - {ref_path}")
            refs[name] = ref_path
            continue

        print(f"  {name} 레퍼런스 생성 중...")
        result = api_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=bible["avatar_prompt"],
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        if result.generated_images:
            result.generated_images[0].image.save(ref_path)
            refs[name] = ref_path
            print(f"  {name}: 저장 완료 - {ref_path}")

    if len(refs) < 2:
        print("레퍼런스 생성 실패!")
        return

    # ── 2. Subject Reference 객체 준비 ──
    soyul_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=types.Image.from_file(location=str(refs["soyul"])),
        config=types.SubjectReferenceConfig(
            subject_description=build_char_block(SOYUL_BIBLE),
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )
    grandpa_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=types.Image.from_file(location=str(refs["grandpa"])),
        config=types.SubjectReferenceConfig(
            subject_description=build_char_block(GRANDPA_BIBLE),
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )
    # 두 캐릭터 동시용 (할아버지=1, 소율=2)
    grandpa_ref_multi = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=types.Image.from_file(location=str(refs["grandpa"])),
        config=types.SubjectReferenceConfig(
            subject_description=build_char_block(GRANDPA_BIBLE),
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )
    soyul_ref_multi = types.SubjectReferenceImage(
        reference_id=2,
        reference_image=types.Image.from_file(location=str(refs["soyul"])),
        config=types.SubjectReferenceConfig(
            subject_description=build_char_block(SOYUL_BIBLE),
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    all_forbidden = set(SOYUL_BIBLE["forbidden"] + GRANDPA_BIBLE["forbidden"])
    negative = ", ".join(all_forbidden)

    # ── 3. 장면 생성 ──
    print("\n" + "=" * 60)
    print("2단계: 17장면 이미지 생성")
    print("=" * 60)

    success = 0
    fail = 0

    for scene in SCENES:
        sid = scene["id"]
        chars = scene["chars"]
        prompt = scene["prompt"]

        # art_style 추가
        full_prompt = f"{prompt}, {SOYUL_BIBLE['art_style']}"

        # 레퍼런스 이미지 선택
        if chars == "both":
            ref_images = [grandpa_ref_multi, soyul_ref_multi]
        elif chars == "grandpa":
            ref_images = [grandpa_ref]
        elif chars == "soyul":
            ref_images = [soyul_ref]
        else:
            ref_images = None

        print(f"\n[{sid}] ({chars}) 생성 중...")

        try:
            if ref_images:
                result = vtx_client.models.edit_image(
                    model="imagen-3.0-capability-001",
                    prompt=full_prompt,
                    reference_images=ref_images,
                    config=types.EditImageConfig(
                        edit_mode="EDIT_MODE_DEFAULT",
                        number_of_images=1,
                        negative_prompt=negative,
                        person_generation="ALLOW_ALL",
                    ),
                )
            else:
                # 추상/메타포 장면은 Imagen 4로 생성
                result = api_client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=full_prompt,
                    config=types.GenerateImagesConfig(number_of_images=1),
                )

            if result.generated_images:
                filename = f"{sid}_{datetime.now().strftime('%H%M%S')}.png"
                save_path = OUTPUT_DIR / filename
                result.generated_images[0].image.save(save_path)
                size_kb = save_path.stat().st_size / 1024
                print(f"  저장: {save_path} ({size_kb:.0f}KB)")
                success += 1
            else:
                print(f"  실패: 빈 응답")
                fail += 1

        except Exception as e:
            print(f"  에러: {e}")
            fail += 1

    print(f"\n{'='*60}")
    print(f"완료! 성공: {success}/{success+fail}")
    print(f"출력: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

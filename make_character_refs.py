"""
캐릭터별 레퍼런스 이미지 생성
각 캐릭터를 개별적으로 뽑아서 외형 확인
"""

import json, time, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"')
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
REF_DIR = EPISODE_DIR / "character_refs"
REF_DIR.mkdir(exist_ok=True)

with open(EPISODE_DIR / "characters.json", "r", encoding="utf-8") as f:
    characters = json.load(f)

ART_STYLE = characters["art_style"]


def main():
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 캐릭터 목록 구성
    char_list = []

    mc = characters["main_character"]
    char_list.append({
        "name": mc["name_kr"],
        "filename": "ref_jiwoo",
        "prompt": (
            f"A single character standing alone, full body portrait. "
            f"{mc['description_en']}. "
            f"The character is standing in a neutral white background, facing slightly to the right. "
            f"Style: {ART_STYLE}. "
            f"No text, no watermark, no other characters, just this one character clearly visible."
        ),
    })

    for sc in characters.get("supporting_characters", []):
        safe_name = sc["name_en"].lower().replace(" ", "_")
        char_list.append({
            "name": sc["name_kr"],
            "filename": f"ref_{safe_name}",
            "prompt": (
                f"A single character standing alone, full body portrait. "
                f"{sc['description_en']}. "
                f"The character is standing in a neutral white background, facing slightly to the right. "
                f"Style: {ART_STYLE}. "
                f"No text, no watermark, no other characters, just this one character clearly visible."
            ),
        })

    # 추가: 엄마+지우 함께 있는 장면 (크기 차이 확인용)
    char_list.append({
        "name": "엄마+지우 (크기비교)",
        "filename": "ref_mother_and_child",
        "prompt": (
            f"Two characters standing side by side, full body portrait. "
            f"LEFT: An adult Korean woman in her early 30s, tall (about 165cm), "
            f"shoulder-length wavy dark brown hair, wearing a soft pink cardigan over white dress, "
            f"gentle smile, slender adult build. "
            f"RIGHT: A small 5-6 year old Korean child (about 110cm, much shorter than the woman), "
            f"short black bob haircut with straight bangs, wearing yellow t-shirt with white cloud pattern "
            f"and denim overalls, white sneakers, round cherubic face. "
            f"The woman is clearly MUCH TALLER than the child. They look like mother and child, NOT twins. "
            f"Different clothes, different hair, different height, different body proportions. "
            f"Neutral white background. "
            f"Style: {ART_STYLE}. "
            f"No text, no watermark."
        ),
    })

    # 추가: 할머니+지우 함께
    char_list.append({
        "name": "할머니+지우 (크기비교)",
        "filename": "ref_grandmother_and_child",
        "prompt": (
            f"Two characters standing side by side, full body portrait. "
            f"LEFT: An elderly Korean woman in her late 60s, short permed gray hair, "
            f"wearing traditional Korean-style beige vest over floral print blouse, "
            f"kind crescent-shaped eyes with crow's feet, plump motherly build, about 155cm tall. "
            f"RIGHT: A small 5-6 year old Korean child (about 110cm, much shorter), "
            f"short black bob haircut with straight bangs, wearing yellow t-shirt with white cloud pattern "
            f"and denim overalls, white sneakers, round cherubic face. "
            f"The elderly woman is clearly TALLER than the child. They look like grandmother and grandchild. "
            f"Different clothes, different hair color (gray vs black), different body proportions. "
            f"Neutral white background. "
            f"Style: {ART_STYLE}. "
            f"No text, no watermark."
        ),
    })

    print(f"캐릭터 레퍼런스 이미지 생성: {len(char_list)}개")
    print("=" * 60)

    for i, char in enumerate(char_list):
        out_path = REF_DIR / f"{char['filename']}.png"

        if out_path.exists():
            print(f"  [{i}] {char['name']} - 이미 존재, 스킵")
            continue

        print(f"  [{i}] {char['name']} 생성 중...")

        for attempt in range(3):
            try:
                result = client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=char["prompt"],
                    config=types.GenerateImagesConfig(number_of_images=1),
                )
                if result.generated_images:
                    result.generated_images[0].image.save(str(out_path))
                    print(f"       → 저장: {out_path.name}")
                    break
                else:
                    print(f"       빈 응답, 재시도 {attempt+1}/3")
                    time.sleep(30)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 60 * (attempt + 1)
                    print(f"       쿼타 초과! {wait}초 대기... ({attempt+1}/3)")
                    time.sleep(wait)
                else:
                    print(f"       에러: {e}")
                    break

        time.sleep(10)

    print(f"\n완료! 저장 폴더: {REF_DIR}")
    print(f"\n생성된 파일:")
    for f in sorted(REF_DIR.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()

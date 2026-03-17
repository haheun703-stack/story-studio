"""
60장면 그리드 이미지 생성 (v3 - 캐릭터 구분 명확화)
각 장면에 등장하는 캐릭터를 자동 감지하여 프롬프트에 명시
"""

import json, time, os, re
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"')
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
IMAGES_DIR = EPISODE_DIR / "images_v3"
IMAGES_DIR.mkdir(exist_ok=True)


# ─── 캐릭터 감지 ───
CHAR_KEYWORDS = {
    "child": ["child", "jiwoo"],
    "mother": ["mother", "mom"],
    "grandmother": ["grandmother", "grandma"],
    "teacher": ["teacher"],
}

def detect_characters(image_prompt: str) -> list[str]:
    """image_prompt_en에서 등장 캐릭터 감지"""
    prompt_lower = image_prompt.lower()
    found = []
    for char_key, keywords in CHAR_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            found.append(char_key)
    # child가 명시 안 되어도 대부분 등장
    if "child" not in found:
        found.insert(0, "child")
    return found


def build_character_block(chars_in_scene: list[str], characters: dict) -> str:
    """등장 캐릭터별 외형 설명 블록 생성"""
    mc = characters["main_character"]
    sc_map = {sc["name_en"].lower(): sc for sc in characters.get("supporting_characters", [])}

    parts = []
    for char_key in chars_in_scene:
        if char_key == "child":
            parts.append(
                f"THE CHILD (small, about 110cm tall, SHORT BLACK BOB HAIRCUT with straight bangs): {mc['description_en']}"
            )
        elif char_key == "mother":
            sc = sc_map.get("mother", {})
            parts.append(
                f"THE MOTHER (tall adult woman, about 165cm, clearly MUCH BIGGER than the child): "
                f"{sc.get('description_en', 'adult Korean woman in pink cardigan and white dress')}"
            )
        elif char_key == "grandmother":
            sc = sc_map.get("grandmother", {})
            parts.append(
                f"THE GRANDMOTHER (elderly woman, about 155cm, gray permed hair, wrinkled face): "
                f"{sc.get('description_en', 'elderly Korean woman with gray hair')}"
            )
        elif char_key == "teacher":
            sc = sc_map.get("teacher", {})
            parts.append(
                f"THE TEACHER (young adult woman with glasses and ponytail): "
                f"{sc.get('description_en', 'young Korean woman with glasses')}"
            )

    return ". ".join(parts)


def make_grid_prompt(scenes_subset: list[dict], characters: dict) -> str:
    """캐릭터 구분이 명확한 그리드 프롬프트 생성"""
    n = len(scenes_subset)
    if n == 4:
        layout = "2x2 grid"
        positions = ["top-left", "top-right", "bottom-left", "bottom-right"]
    elif n == 2:
        layout = "1x2 grid (two panels side by side)"
        positions = ["left", "right"]
    else:
        layout = "single illustration"
        positions = ["center"]

    style = characters["art_style"]

    # 장면별 캐릭터 감지 + 통합
    all_chars = set()
    scene_descs = []
    for i, s in enumerate(scenes_subset):
        chars = detect_characters(s["image_prompt_en"])
        all_chars.update(chars)
        scene_descs.append(f"{positions[i]}: {s['image_prompt_en']}")

    char_block = build_character_block(list(all_chars), characters)
    scene_desc = ". ".join(scene_descs)

    prompt = (
        f"A {layout} of children's storybook illustrations. "
        f"IMPORTANT CHARACTER DESCRIPTIONS - each character must look DIFFERENT from each other: "
        f"{char_block}. "
        f"The child must look consistent across all panels (same face, same hair, same clothes). "
        f"Adults must be clearly TALLER and BIGGER than the child. "
        f"Mother and child must NOT look like twins - they have different heights, different clothes, different hair styles. "
        f"Scenes: {scene_desc}. "
        f"Style: {style}. "
        f"Each panel has a thin white border. "
        f"No text, no watermarks, no signatures, no 3D render."
    )
    return prompt


def main():
    from google import genai
    from google.genai import types

    api_client = genai.Client(api_key=GEMINI_API_KEY)

    with open(EPISODE_DIR / "images_v2" / "scenario_v2_60.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(EPISODE_DIR / "characters.json", "r", encoding="utf-8") as f:
        characters = json.load(f)

    scenes = data["scenes"]

    # 4컷씩 나누기
    batches = [scenes[i:i+4] for i in range(0, len(scenes), 4)]
    print(f"총 {len(scenes)}장면 → {len(batches)}개 그리드")
    print("=" * 60)

    for batch_idx, batch in enumerate(batches):
        n = len(batch)
        panel_paths = [IMAGES_DIR / f"scene_{batch_idx*4+j:02d}.png" for j in range(n)]
        grid_path = IMAGES_DIR / f"grid_{batch_idx:02d}.png"

        if all(p.exists() for p in panel_paths):
            print(f"[{batch_idx:02d}/{len(batches)-1}] 이미 존재, 스킵")
            continue

        prompt = make_grid_prompt(batch, characters)
        print(f"[{batch_idx:02d}/{len(batches)-1}] {n}컷 생성 중...")

        # 등장 캐릭터 표시
        all_chars = set()
        for s in batch:
            all_chars.update(detect_characters(s["image_prompt_en"]))
        print(f"  등장: {', '.join(all_chars)}")

        for attempt in range(3):
            try:
                result = api_client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=prompt,
                    config=types.GenerateImagesConfig(number_of_images=1),
                )
                if result.generated_images:
                    result.generated_images[0].image.save(str(grid_path))

                    # 크롭
                    pil_grid = Image.open(grid_path)
                    w, h = pil_grid.size
                    if n == 4:
                        hw, hh = w // 2, h // 2
                        crops = [(0, 0, hw, hh), (hw, 0, w, hh), (0, hh, hw, h), (hw, hh, w, h)]
                    elif n == 2:
                        hw = w // 2
                        crops = [(0, 0, hw, h), (hw, 0, w, h)]
                    else:
                        crops = [(0, 0, w, h)]

                    for box, pp in zip(crops, panel_paths):
                        panel = pil_grid.crop(box)
                        pw, ph = panel.size
                        mx, my = int(pw * 0.03), int(ph * 0.03)
                        panel = panel.crop((mx, my, pw - mx, ph - my))
                        panel.save(pp)

                        # 업스케일
                        scale = 1024 / max(panel.size)
                        if scale > 1:
                            up = panel.resize(
                                (int(panel.size[0] * scale), int(panel.size[1] * scale)),
                                Image.LANCZOS,
                            )
                            up.save(pp.parent / f"{pp.stem}_up{pp.suffix}")

                    print(f"  완료! ({pil_grid.size})")
                    break
                else:
                    print(f"  빈 응답, 재시도 {attempt+1}/3")
                    time.sleep(30)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 60 * (attempt + 1)
                    print(f"  쿼타 초과! {wait}초 대기... ({attempt+1}/3)")
                    time.sleep(wait)
                else:
                    print(f"  에러: {e}")
                    break

        if batch_idx < len(batches) - 1:
            time.sleep(12)

    # 결과 확인
    up_files = sorted(IMAGES_DIR.glob("scene_*_up.png"))
    print(f"\n완료! 업스케일 이미지: {len(up_files)}장")
    print(f"폴더: {IMAGES_DIR}")


if __name__ == "__main__":
    main()

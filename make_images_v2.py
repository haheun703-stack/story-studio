"""
60장면 그리드 이미지 생성 (v2 시나리오)
"""

import json, time, os
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"')
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
IMAGES_DIR = EPISODE_DIR / "images_v2"
IMAGES_DIR.mkdir(exist_ok=True)


def main():
    from google import genai
    from google.genai import types

    api_client = genai.Client(api_key=GEMINI_API_KEY)

    with open(EPISODE_DIR / "scenario_v2_60.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(EPISODE_DIR / "characters.json", "r", encoding="utf-8") as f:
        characters = json.load(f)

    scenes = data["scenes"]
    main_char = characters["main_character"]["description_en"]
    art_style = characters["art_style"]

    # 4컷씩 나누기
    batches = [scenes[i:i+4] for i in range(0, len(scenes), 4)]
    print(f"총 {len(scenes)}장면 → {len(batches)}개 그리드")
    print("=" * 60)

    for batch_idx, batch in enumerate(batches):
        grid_path = IMAGES_DIR / f"grid_{batch_idx:02d}.png"
        n = len(batch)
        panel_paths = [IMAGES_DIR / f"scene_{batch_idx*4+j:02d}.png" for j in range(n)]

        if all(p.exists() for p in panel_paths):
            print(f"[{batch_idx:02d}/{len(batches)-1}] 이미 존재, 스킵")
            continue

        # 프롬프트
        if n == 4:
            layout = "2x2 grid"
            positions = ["top-left", "top-right", "bottom-left", "bottom-right"]
        elif n == 2:
            layout = "1x2 grid (two panels side by side)"
            positions = ["left", "right"]
        else:
            layout = "single illustration"
            positions = ["center"]

        scene_desc = ". ".join(
            f"{positions[i]}: {s['image_prompt_en']}" for i, s in enumerate(batch)
        )

        prompt = (
            f"A {layout} of children's storybook illustrations, "
            f"all featuring the exact same character: {main_char}. "
            f"Each panel shows the same character in a different scene. "
            f"{scene_desc}. "
            f"Style: {art_style}. "
            f"The character must look identical in every panel - same face, same hair, same body proportions. "
            f"Each panel has a thin white border separating them. "
            f"No text, no watermarks, no signatures, no 3D render."
        )

        print(f"[{batch_idx:02d}/{len(batches)-1}] {n}컷 생성 중...")

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

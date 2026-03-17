"""
그리드 기반 캐릭터 일관성 파이프라인
- 2x2 그리드로 생성 → 자동 크롭 → 업스케일
- 그리드 간 일관성: Style Reference로 연결
"""

import os, time
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"')
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')
OUTPUT_DIR = Path("output/media/grid_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── 캐릭터 설정 ───
CHARACTER = {
    "name": "소율",
    "description": (
        "6-7 year old Korean girl, "
        "dark brown hair in two low pigtails with red hair ties, "
        "large round dark brown eyes, "
        "round soft face with rosy pink cheeks, "
        "cream-colored knit sweater and denim overalls, "
        "yellow rain boots"
    ),
    "art_style": (
        "warm emotional children's storybook illustration, "
        "soft watercolor texture, gentle warm lighting, "
        "pastel palette with warm golden tones, clean composition"
    ),
    "negative": (
        "text, watermark, signature, extra fingers, "
        "realistic photo, 3D render, dark horror mood, "
        "harsh shadows, different child"
    ),
}

# ─── 장면 목록 (10장 = 3그리드: 4+4+2) ───
SCENES = [
    "standing in a sunny flower garden, smiling happily, butterflies flying around",
    "sitting under a big tree reading a picture book, autumn leaves falling gently",
    "running through puddles in the rain, splashing water joyfully, laughing",
    "building a snowman in a snowy park, wearing mittens, breath visible in cold air",
    "painting with watercolors at a small wooden table, colorful paints everywhere",
    "feeding a small white puppy in a warm cozy kitchen, sunlight through window",
    "looking up at a night sky full of stars, standing on a grassy hill",
    "riding a bicycle along a riverside path, cherry blossoms in the wind",
    "blowing out candles on a birthday cake, party decorations and balloons",
    "sleeping peacefully in bed hugging a teddy bear, soft moonlight through curtains",
]


def make_grid_prompt(scenes_subset: list[str], char: dict) -> str:
    """2x2 그리드 프롬프트 생성"""
    n = len(scenes_subset)
    if n == 4:
        layout = "2x2 grid"
        positions = ["top-left", "top-right", "bottom-left", "bottom-right"]
    elif n == 3:
        layout = "2x2 grid (bottom-right panel is blank/empty)"
        positions = ["top-left", "top-right", "bottom-left"]
    elif n == 2:
        layout = "1x2 grid (two panels side by side)"
        positions = ["left", "right"]
    else:
        layout = "single illustration"
        positions = ["center"]

    scene_desc = ". ".join(
        f"{positions[i]}: the same girl {s}" for i, s in enumerate(scenes_subset)
    )

    prompt = (
        f"A {layout} of children's storybook illustrations, "
        f"all featuring the exact same character: {char['description']}. "
        f"Each panel shows the same girl in a different scene. "
        f"{scene_desc}. "
        f"Style: {char['art_style']}. "
        f"The character must look identical in every panel - same face, same hair, same body proportions. "
        f"Each panel has a thin white border separating them. "
        f"No text, no watermarks, no signatures, no 3D render."
    )
    return prompt


def crop_grid(image: Image.Image, n_panels: int, output_paths: list[Path]) -> list[Path]:
    """그리드 이미지를 개별 패널로 크롭"""
    w, h = image.size
    saved = []

    if n_panels == 4:
        # 2x2 그리드
        half_w, half_h = w // 2, h // 2
        crops = [
            (0, 0, half_w, half_h),           # top-left
            (half_w, 0, w, half_h),            # top-right
            (0, half_h, half_w, h),            # bottom-left
            (half_w, half_h, w, h),            # bottom-right
        ]
    elif n_panels == 2:
        half_w = w // 2
        crops = [
            (0, 0, half_w, h),     # left
            (half_w, 0, w, h),     # right
        ]
    else:
        crops = [(0, 0, w, h)]

    for i, (box, out_path) in enumerate(zip(crops, output_paths)):
        panel = image.crop(box)
        # 테두리 여백 제거 (각 방향 3% 정도)
        pw, ph = panel.size
        margin_x = int(pw * 0.03)
        margin_y = int(ph * 0.03)
        panel = panel.crop((margin_x, margin_y, pw - margin_x, ph - margin_y))
        panel.save(out_path)
        saved.append(out_path)
        print(f"    크롭 저장: {out_path.name} ({panel.size[0]}x{panel.size[1]})")

    return saved


def upscale_lanczos(image_path: Path, target_size: int = 1024) -> Path:
    """Pillow LANCZOS 업스케일 (기본)"""
    img = Image.open(image_path)
    w, h = img.size
    # 긴 변 기준으로 target_size에 맞춤
    scale = target_size / max(w, h)
    if scale <= 1.0:
        return image_path  # 이미 충분히 큼

    new_w = int(w * scale)
    new_h = int(h * scale)
    img_up = img.resize((new_w, new_h), Image.LANCZOS)

    up_path = image_path.parent / f"{image_path.stem}_up{image_path.suffix}"
    img_up.save(up_path)
    print(f"    업스케일: {up_path.name} ({new_w}x{new_h})")
    return up_path


def generate_grid(client, prompt: str, negative: str, style_ref_image=None):
    """Imagen으로 그리드 이미지 생성"""
    from google.genai import types

    if style_ref_image:
        # 이전 그리드를 Style Reference로 사용 (Vertex AI)
        style_ref = types.StyleReferenceImage(
            reference_id=1,
            reference_image=style_ref_image,
            config=types.StyleReferenceConfig(
                style_description=CHARACTER["art_style"],
            ),
        )
        result = client.models.edit_image(
            model="imagen-3.0-capability-001",
            prompt=prompt,
            reference_images=[style_ref],
            config=types.EditImageConfig(
                edit_mode="EDIT_MODE_DEFAULT",
                number_of_images=1,
                negative_prompt=negative,
                person_generation="ALLOW_ALL",
            ),
        )
    else:
        # 첫 그리드: Style Reference 없이 생성 (API Key로 가능)
        result = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )

    if result.generated_images:
        return result.generated_images[0].image
    return None


def main():
    from google import genai
    from google.genai import types

    # 첫 그리드는 API Key로, 이후는 Vertex AI로
    api_client = genai.Client(api_key=API_KEY)
    vtx_client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")

    print("=" * 60)
    print("그리드 기반 캐릭터 일관성 파이프라인")
    print("=" * 60)

    # 장면을 4컷씩 나누기
    batches = []
    for i in range(0, len(SCENES), 4):
        batches.append(SCENES[i:i+4])

    print(f"총 {len(SCENES)}장면 → {len(batches)}개 그리드\n")

    prev_grid_image = None
    all_panels = []

    for batch_idx, batch_scenes in enumerate(batches):
        grid_path = OUTPUT_DIR / f"grid_{batch_idx:02d}.png"
        n_panels = len(batch_scenes)
        panel_paths = [
            OUTPUT_DIR / f"scene_{batch_idx * 4 + j:02d}.png"
            for j in range(n_panels)
        ]

        # 이미 크롭된 패널이 모두 존재하면 스킵
        if all(p.exists() for p in panel_paths):
            print(f"[그리드 {batch_idx}] 이미 존재, 스킵")
            # 다음 그리드를 위해 이 그리드 로드
            if grid_path.exists():
                prev_grid_image = types.Image.from_file(location=str(grid_path))
            all_panels.extend(panel_paths)
            continue

        # 프롬프트 생성
        prompt = make_grid_prompt(batch_scenes, CHARACTER)
        print(f"[그리드 {batch_idx}] {n_panels}컷 생성 중...")
        print(f"  장면: {', '.join(s[:30]+'...' for s in batch_scenes)}")

        # 생성
        use_vtx = prev_grid_image is not None  # 두 번째 그리드부터 Style Ref 사용
        client = vtx_client if use_vtx else api_client

        for attempt in range(3):
            try:
                gen_image = generate_grid(
                    client, prompt, CHARACTER["negative"],
                    style_ref_image=prev_grid_image,
                )
                if gen_image:
                    # 그리드 원본 저장
                    gen_image.save(str(grid_path))
                    print(f"  그리드 저장: {grid_path.name}")

                    # 크롭
                    pil_grid = Image.open(grid_path)
                    print(f"  그리드 크기: {pil_grid.size}")
                    cropped = crop_grid(pil_grid, n_panels, panel_paths)

                    # 업스케일
                    for cp in cropped:
                        upscale_lanczos(cp, target_size=1024)

                    # 다음 그리드를 위한 Style Reference
                    prev_grid_image = types.Image.from_file(location=str(grid_path))
                    all_panels.extend(panel_paths)
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

        # 그리드 간 딜레이
        if batch_idx < len(batches) - 1:
            print(f"  다음 그리드까지 20초 대기...")
            time.sleep(20)

    print("\n" + "=" * 60)
    print(f"완료! 총 {len(all_panels)}개 패널 생성")
    print(f"출력 폴더: {OUTPUT_DIR}")
    print("\n패널 목록:")
    for p in sorted(OUTPUT_DIR.glob("scene_*.png")):
        size = Image.open(p).size
        print(f"  {p.name}: {size[0]}x{size[1]}")
    print("\n업스케일 목록:")
    for p in sorted(OUTPUT_DIR.glob("scene_*_up.png")):
        size = Image.open(p).size
        print(f"  {p.name}: {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()

"""
동화 자동 제작 파이프라인
[1] 주제 입력 → [2] Claude가 시나리오 작성 → 승인
→ [3] Claude가 캐릭터 설계 → 승인
→ [4] Imagen 4 그리드 이미지 생성 → 크롭 → 업스케일
"""

import os, sys, json, time
from datetime import datetime
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
import anthropic

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "").strip('"')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"')
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')

BASE_OUTPUT = Path("output/episodes")


# ═══════════════════════════════════════════════════════════
# STEP 1: Claude로 시나리오 생성
# ═══════════════════════════════════════════════════════════

def generate_scenario(theme: str) -> dict:
    """Claude API로 동화 시나리오 생성"""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    prompt = f"""당신은 유치부(3~7세) 동화 시나리오 작가입니다.

주제: "{theme}"

다음 JSON 형식으로 동화 시나리오를 작성하세요:

{{
    "title": "동화 제목 (한국어)",
    "title_en": "English Title",
    "age_group": "3-7세",
    "theme": "{theme}",
    "moral": "교훈/메시지 (한 문장)",
    "synopsis": "전체 줄거리 요약 (3-4문장, 한국어)",
    "scenes": [
        {{
            "scene_number": 1,
            "narration_kr": "나레이션 한국어 (TTS용, 2-3문장)",
            "narration_en": "English narration for TTS",
            "image_prompt_en": "Detailed scene description in English for image generation (visual only, no text/dialogue)"
        }}
    ]
}}

규칙:
- 장면은 정확히 10개
- 나레이션은 유치부 아이에게 읽어줄 수 있는 쉬운 말투
- image_prompt_en은 이미지 생성 AI에게 줄 영어 프롬프트 (시각적 묘사만, 대사/텍스트 없이)
- 기승전결 구조: 도입(1-2) → 전개(3-5) → 위기(6-7) → 해결(8-9) → 마무리(10)
- JSON만 출력, 다른 텍스트 없이"""

    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # JSON 파싱 (코드블록 제거)
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


# ═══════════════════════════════════════════════════════════
# STEP 2: Claude로 캐릭터 설계
# ═══════════════════════════════════════════════════════════

def generate_characters(scenario: dict) -> dict:
    """Claude API로 캐릭터 설계"""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    prompt = f"""당신은 동화 캐릭터 디자이너입니다.

동화 제목: "{scenario['title']}"
줄거리: {scenario['synopsis']}

장면 목록:
{json.dumps([s['image_prompt_en'] for s in scenario['scenes']], indent=2, ensure_ascii=False)}

다음 JSON 형식으로 캐릭터를 설계하세요:

{{
    "main_character": {{
        "name_kr": "한국어 이름",
        "name_en": "English name",
        "description_en": "Detailed visual description in English for image generation: age, gender, ethnicity, hair (color, style, accessories), eyes (color, shape), face shape, skin tone, outfit, shoes - be very specific",
        "personality": "성격 한 줄 설명 (한국어)"
    }},
    "supporting_characters": [
        {{
            "name_kr": "이름",
            "name_en": "Name",
            "description_en": "Detailed visual description in English",
            "role": "역할 설명 (한국어)"
        }}
    ],
    "art_style": "Consistent art style description in English for all images (e.g. warm watercolor children's storybook illustration, soft lighting, pastel palette)",
    "negative_prompt": "Things to avoid in English (e.g. text, watermark, realistic photo, 3D render, dark mood, harsh shadows)"
}}

규칙:
- 주인공은 반드시 1명
- 조연은 시나리오에 등장하는 인물/동물만 (0~3명)
- description_en은 이미지 생성 AI가 매번 동일한 캐릭터를 그릴 수 있도록 매우 구체적으로
- JSON만 출력"""

    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


# ═══════════════════════════════════════════════════════════
# STEP 3: 그리드 이미지 생성 (기존 파이프라인 활용)
# ═══════════════════════════════════════════════════════════

def make_grid_prompt(scenes_subset: list[dict], characters: dict) -> str:
    """2x2 그리드 프롬프트 생성"""
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

    main_char = characters["main_character"]["description_en"]
    style = characters["art_style"]

    scene_desc = ". ".join(
        f"{positions[i]}: {s['image_prompt_en']}"
        for i, s in enumerate(scenes_subset)
    )

    prompt = (
        f"A {layout} of children's storybook illustrations, "
        f"all featuring the exact same character: {main_char}. "
        f"Each panel shows the same character in a different scene. "
        f"{scene_desc}. "
        f"Style: {style}. "
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
        half_w, half_h = w // 2, h // 2
        crops = [
            (0, 0, half_w, half_h),
            (half_w, 0, w, half_h),
            (0, half_h, half_w, h),
            (half_w, half_h, w, h),
        ]
    elif n_panels == 2:
        half_w = w // 2
        crops = [
            (0, 0, half_w, h),
            (half_w, 0, w, h),
        ]
    else:
        crops = [(0, 0, w, h)]

    for box, out_path in zip(crops, output_paths):
        panel = image.crop(box)
        pw, ph = panel.size
        margin_x = int(pw * 0.03)
        margin_y = int(ph * 0.03)
        panel = panel.crop((margin_x, margin_y, pw - margin_x, ph - margin_y))
        panel.save(out_path)
        saved.append(out_path)
        print(f"    크롭: {out_path.name} ({panel.size[0]}x{panel.size[1]})")

    return saved


def upscale_lanczos(image_path: Path, target_size: int = 1024) -> Path:
    """LANCZOS 업스케일"""
    img = Image.open(image_path)
    w, h = img.size
    scale = target_size / max(w, h)
    if scale <= 1.0:
        return image_path

    new_w, new_h = int(w * scale), int(h * scale)
    img_up = img.resize((new_w, new_h), Image.LANCZOS)
    up_path = image_path.parent / f"{image_path.stem}_up{image_path.suffix}"
    img_up.save(up_path)
    print(f"    업스케일: {up_path.name} ({new_w}x{new_h})")
    return up_path


def generate_images(scenario: dict, characters: dict, output_dir: Path):
    """Imagen 4로 그리드 이미지 생성 → 크롭 → 업스케일"""
    from google import genai
    from google.genai import types

    api_client = genai.Client(api_key=GEMINI_API_KEY)
    scenes = scenario["scenes"]

    # 4컷씩 나누기
    batches = []
    for i in range(0, len(scenes), 4):
        batches.append(scenes[i:i+4])

    print(f"\n총 {len(scenes)}장면 → {len(batches)}개 그리드")

    all_panels = []

    for batch_idx, batch_scenes in enumerate(batches):
        grid_path = output_dir / f"grid_{batch_idx:02d}.png"
        n_panels = len(batch_scenes)
        panel_paths = [
            output_dir / f"scene_{batch_idx * 4 + j:02d}.png"
            for j in range(n_panels)
        ]

        if all(p.exists() for p in panel_paths):
            print(f"[그리드 {batch_idx}] 이미 존재, 스킵")
            all_panels.extend(panel_paths)
            continue

        prompt = make_grid_prompt(batch_scenes, characters)
        print(f"\n[그리드 {batch_idx}] {n_panels}컷 생성 중...")

        for attempt in range(3):
            try:
                result = api_client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                    ),
                )
                if result.generated_images:
                    result.generated_images[0].image.save(str(grid_path))
                    print(f"  그리드 저장: {grid_path.name}")

                    pil_grid = Image.open(grid_path)
                    print(f"  그리드 크기: {pil_grid.size}")
                    cropped = crop_grid(pil_grid, n_panels, panel_paths)

                    for cp in cropped:
                        upscale_lanczos(cp, target_size=1024)

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

        if batch_idx < len(batches) - 1:
            print(f"  다음 그리드까지 15초 대기...")
            time.sleep(15)

    return all_panels


# ═══════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════

def user_approve(message: str) -> bool:
    """사용자 승인 받기"""
    while True:
        answer = input(f"\n{message} (y/n/수정요청): ").strip().lower()
        if answer in ("y", "yes", "ㅛ"):
            return True
        elif answer in ("n", "no", "ㅜ"):
            return False
        else:
            print(f"  → 수정 요청: {answer}")
            return False


def main():
    print("=" * 60)
    print("  동화 자동 제작 파이프라인")
    print("  Claude AI 시나리오 → Imagen 4 이미지 생성")
    print("=" * 60)

    # ─── STEP 1: 주제 입력 ───
    if len(sys.argv) > 1:
        theme = " ".join(sys.argv[1:])
    else:
        theme = input("\n주제를 입력하세요: ").strip()

    if not theme:
        print("주제가 비어있습니다.")
        return

    print(f"\n주제: {theme}")

    # ─── STEP 2: 시나리오 생성 ───
    print("\n[STEP 2] Claude가 시나리오를 작성합니다...")
    scenario = generate_scenario(theme)

    # 에피소드 폴더 생성 (날짜_제목)
    today = datetime.now().strftime("%Y-%m-%d")
    safe_title = scenario["title_en"].replace(" ", "_")[:30]
    episode_dir = BASE_OUTPUT / f"{today}_{safe_title}"
    episode_dir.mkdir(parents=True, exist_ok=True)

    # 시나리오 저장
    scenario_path = episode_dir / "scenario.json"
    with open(scenario_path, "w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)

    # 시나리오 표시
    print(f"\n{'─' * 50}")
    print(f"  제목: {scenario['title']}")
    print(f"  교훈: {scenario['moral']}")
    print(f"  줄거리: {scenario['synopsis']}")
    print(f"{'─' * 50}")
    for s in scenario["scenes"]:
        print(f"  [{s['scene_number']:2d}] {s['narration_kr']}")
    print(f"{'─' * 50}")
    print(f"  저장: {scenario_path}")

    if not user_approve("시나리오를 승인하시겠습니까?"):
        print("시나리오가 거절되었습니다. 다시 실행해주세요.")
        return

    # ─── STEP 3: 캐릭터 설계 ───
    print("\n[STEP 3] Claude가 캐릭터를 설계합니다...")
    characters = generate_characters(scenario)

    characters_path = episode_dir / "characters.json"
    with open(characters_path, "w", encoding="utf-8") as f:
        json.dump(characters, f, ensure_ascii=False, indent=2)

    print(f"\n{'─' * 50}")
    mc = characters["main_character"]
    print(f"  주인공: {mc['name_kr']} ({mc['name_en']})")
    print(f"  외모: {mc['description_en']}")
    print(f"  성격: {mc['personality']}")
    for sc in characters.get("supporting_characters", []):
        print(f"\n  조연: {sc['name_kr']} ({sc['name_en']})")
        print(f"  외모: {sc['description_en']}")
        print(f"  역할: {sc['role']}")
    print(f"\n  화풍: {characters['art_style']}")
    print(f"{'─' * 50}")
    print(f"  저장: {characters_path}")

    if not user_approve("캐릭터 설계를 승인하시겠습니까?"):
        print("캐릭터가 거절되었습니다. 다시 실행해주세요.")
        return

    # ─── STEP 4: 이미지 생성 ───
    print("\n[STEP 4] Imagen 4로 그리드 이미지를 생성합니다...")
    images_dir = episode_dir / "images"
    images_dir.mkdir(exist_ok=True)

    panels = generate_images(scenario, characters, images_dir)

    print(f"\n{'═' * 60}")
    print(f"  완료!")
    print(f"  에피소드 폴더: {episode_dir}")
    print(f"  시나리오: {scenario_path}")
    print(f"  캐릭터: {characters_path}")
    print(f"  이미지: {len(panels)}장 → {images_dir}")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()

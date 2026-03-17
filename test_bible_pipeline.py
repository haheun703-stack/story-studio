"""
캐릭터 바이블 + Subject Reference + 정규화 프롬프트 통합 테스트
가이드의 구조화 + Vertex AI Subject Reference = 최강 조합 검증
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "").strip('"')

# ═══════════════════════════════════════════════════════════════
# 1. 캐릭터 바이블 (불변 / 반고정 / 가변 분리)
# ═══════════════════════════════════════════════════════════════

CHARACTER_BIBLE = {
    "character_id": "Nari_Yellow_01",
    "name": "나리",
    "age_look": "5-6 years old",

    # ── 불변 요소 (절대 바꾸지 않음) ──
    "immutable": {
        "face": "round face, small nose, rosy cheeks",
        "eyes": "large warm brown eyes",
        "hair": "dark brown short bob haircut with straight bangs",
        "skin": "soft fair skin",
        "age": "5-6 year old Korean girl",
    },

    # ── 반고정 요소 (특별한 이유 없으면 유지) ──
    "semi_fixed": {
        "default_outfit": "white short-sleeve t-shirt and yellow overalls",
        "default_shoes": "red sneakers",
        "default_mood": "curious, warm, cheerful",
    },

    # ── 스타일 고정 ──
    "art_style": (
        "children's storybook illustration, soft lines, warm sunlight, "
        "pastel palette, clean composition, 2D digital art"
    ),

    # ── 금지 요소 (네거티브 프롬프트) ──
    "forbidden": [
        "long hair", "different eye color", "older child appearance",
        "realistic adult proportions", "dark horror mood",
        "harsh shadows", "extra fingers", "distorted face",
        "asymmetrical eyes", "different child", "3D render",
        "text", "watermark", "signature",
    ],
}


def build_character_block(bible: dict) -> str:
    """불변 캐릭터 블록 생성 (모든 프롬프트 앞에 붙임)"""
    im = bible["immutable"]
    sf = bible["semi_fixed"]
    return (
        f"{bible['character_id']}, "
        f"{im['age']}, "
        f"{im['hair']}, "
        f"{im['eyes']}, "
        f"{im['face']}, "
        f"{im['skin']}, "
        f"{sf['default_outfit']}, "
        f"{sf['default_shoes']}"
    )


def build_negative_prompt(bible: dict) -> str:
    """네거티브 프롬프트 생성"""
    return ", ".join(bible["forbidden"])


def build_full_prompt(bible: dict, action: str, environment: str,
                      emotion: str = "", camera: str = "") -> str:
    """정규화된 전체 프롬프트 생성
    구조: 캐릭터(40%) → 행동(15%) → 배경(20%) → 감정(10%) → 구도(10%) → 스타일(5%)
    """
    parts = [
        build_character_block(bible),   # 40% 캐릭터
        action,                          # 15% 행동
        environment,                     # 20% 배경/상황
    ]
    if emotion:
        parts.append(emotion)            # 10% 감정
    if camera:
        parts.append(camera)             # 10% 구도
    parts.append(bible["art_style"])     # 5% 스타일

    return ", ".join(parts)


# ═══════════════════════════════════════════════════════════════
# 2. 테스트 장면 (동화 "봄바람 속 나리의 하루")
# ═══════════════════════════════════════════════════════════════

SCENES = [
    {
        "scene_id": "S01",
        "title": "아침 인사",
        "action": "waving at an open window with a bright smile",
        "environment": "sunny morning bedroom, spring flowers outside the window, warm golden light",
        "emotion": "excited and happy expression",
        "camera": "medium shot, eye-level",
    },
    {
        "scene_id": "S02",
        "title": "벚꽃 나무 아래",
        "action": "standing under a cherry blossom tree, reaching up to catch falling petals",
        "environment": "beautiful spring park, pink cherry blossom petals floating in the air, green grass",
        "emotion": "wonder and amazement, looking up with sparkling eyes",
        "camera": "wide shot, slightly low angle",
    },
    {
        "scene_id": "S03",
        "title": "고양이 친구",
        "action": "kneeling down and gently petting a small gray kitten",
        "environment": "garden path with colorful flowers, soft afternoon sunlight, wooden fence",
        "emotion": "gentle loving smile, caring expression",
        "camera": "close-up shot, eye-level",
    },
    {
        "scene_id": "S04",
        "title": "연못 구경",
        "action": "leaning over a small pond, looking at her reflection with a goldfish swimming",
        "environment": "peaceful garden pond with lily pads, dragonflies, soft dappled light through trees",
        "emotion": "curious and fascinated expression",
        "camera": "medium shot, high angle looking down",
    },
    {
        "scene_id": "S05",
        "title": "석양 귀가",
        "action": "walking on a path toward home, waving goodbye, looking back with a warm smile",
        "environment": "golden sunset, warm orange sky, small cozy house in the background, long shadows",
        "emotion": "peaceful happy expression, satisfied smile",
        "camera": "wide establishing shot, golden hour lighting",
    },
]


# ═══════════════════════════════════════════════════════════════
# 3. Subject Reference + 정규화 프롬프트로 이미지 생성
# ═══════════════════════════════════════════════════════════════

REF_IMAGE_PATH = "output/media/characters/img_20260316_000033_347dc488.png"
OUTPUT_DIR = Path("output/media/bible_test")


def generate_with_bible():
    """캐릭터 바이블 + Subject Reference 조합 생성"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT,
        location="us-central1",
    )

    # Subject Reference 설정
    ref_image = types.Image.from_file(location=REF_IMAGE_PATH)
    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description=build_character_block(CHARACTER_BIBLE),
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    negative = build_negative_prompt(CHARACTER_BIBLE)

    print(f"캐릭터 블록: {build_character_block(CHARACTER_BIBLE)}")
    print(f"네거티브: {negative}")
    print(f"레퍼런스: {REF_IMAGE_PATH}")
    print()

    results = []

    for scene in SCENES:
        prompt = build_full_prompt(
            CHARACTER_BIBLE,
            action=f"the girl[1] {scene['action']}",
            environment=scene["environment"],
            emotion=scene.get("emotion", ""),
            camera=scene.get("camera", ""),
        )

        print(f"[{scene['scene_id']}] {scene['title']}")
        print(f"  프롬프트: {prompt[:120]}...")

        try:
            result = client.models.edit_image(
                model="imagen-3.0-capability-001",
                prompt=prompt,
                reference_images=[subject_ref],
                config=types.EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=1,
                    negative_prompt=negative,
                    person_generation="ALLOW_ALL",
                ),
            )

            if result.generated_images:
                filename = f"{scene['scene_id']}_{datetime.now().strftime('%H%M%S')}.png"
                save_path = OUTPUT_DIR / filename
                result.generated_images[0].image.save(save_path)
                size_kb = save_path.stat().st_size / 1024
                print(f"  저장: {save_path} ({size_kb:.0f}KB)")
                results.append({"scene": scene["scene_id"], "path": str(save_path), "status": "OK"})
            else:
                print(f"  실패: 빈 응답")
                results.append({"scene": scene["scene_id"], "status": "EMPTY"})

        except Exception as e:
            print(f"  에러: {e}")
            results.append({"scene": scene["scene_id"], "status": "ERROR", "error": str(e)})

    # 결과 요약 저장
    summary_path = OUTPUT_DIR / "generation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "character_bible": CHARACTER_BIBLE,
            "negative_prompt": negative,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    print(f"\n요약: {summary_path}")
    return results


if __name__ == "__main__":
    if not Path(REF_IMAGE_PATH).exists():
        print(f"레퍼런스 이미지 없음: {REF_IMAGE_PATH}")
        sys.exit(1)

    print("=" * 60)
    print("캐릭터 바이블 + Subject Reference 통합 테스트")
    print("=" * 60)
    print()

    results = generate_with_bible()

    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"\n결과: {ok}/{len(results)} 성공")
    print(f"출력: {OUTPUT_DIR}")

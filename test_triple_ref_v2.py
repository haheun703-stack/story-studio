"""
Triple Reference v2: reference_id 수정 + 딜레이 + 3장씩만 비교
B(Subject+Style), C(Subject+FaceMesh), D(트리플) 비교
A는 이미 완료됨
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


# 동일한 3장면으로 비교 (A와 같은 장면)
SCENES_3 = [
    "the girl[1] standing in a sunny flower garden, smiling happily, butterflies around her",
    "the girl[1] sitting under a big tree reading a picture book, autumn leaves falling",
    "the girl[1] running through puddles in the rain, splashing water, laughing",
]

DELAY = 15  # 쿼타 회복을 위해 15초 간격


def main():
    from google import genai
    from google.genai import types

    vtx_client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")

    ref_path = OUTPUT_DIR / "ref_soyul.png"
    if not ref_path.exists():
        print("레퍼런스 없음! 먼저 test_triple_reference.py 실행 필요")
        return

    ref_image = types.Image.from_file(location=str(ref_path))
    char_desc = build_char_block(SOYUL_BIBLE)
    negative = ", ".join(SOYUL_BIBLE["forbidden"])

    # Subject Reference (공통)
    subject_ref = types.SubjectReferenceImage(
        reference_id=1,
        reference_image=ref_image,
        config=types.SubjectReferenceConfig(
            subject_description=char_desc,
            subject_type="SUBJECT_TYPE_PERSON",
        ),
    )

    # Style Reference (reference_id 추가!)
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

    # Control Reference - FaceMesh (reference_id 추가!)
    face_ref = types.ControlReferenceImage(
        reference_id=3,
        reference_image=ref_image,
        config=types.ControlReferenceConfig(
            control_type="CONTROL_TYPE_FACE_MESH",
            enable_control_image_computation=True,
        ),
    )

    methods = {
        "B": {
            "name": "Subject + Style",
            "refs": [subject_ref, style_ref],
        },
        "C": {
            "name": "Subject + FaceMesh",
            "refs": [subject_ref, face_ref],
        },
        "D": {
            "name": "Subject + Style + FaceMesh (트리플)",
            "refs": [subject_ref, style_ref, face_ref],
        },
    }

    for method_key, method_info in methods.items():
        print(f"\n{'='*60}")
        print(f"방법 {method_key}: {method_info['name']}")
        print(f"{'='*60}")

        for i, scene_prompt in enumerate(SCENES_3):
            out_path = OUTPUT_DIR / f"{method_key}_{i:02d}.png"
            if out_path.exists():
                print(f"  {method_key}_{i:02d}: 이미 존재, 스킵")
                continue

            full_prompt = f"{scene_prompt}, {SOYUL_BIBLE['art_style']}"
            print(f"  {method_key}_{i:02d}: 생성 중... ({DELAY}초 대기 후)")
            time.sleep(DELAY)

            try:
                result = vtx_client.models.edit_image(
                    model="imagen-3.0-capability-001",
                    prompt=full_prompt,
                    reference_images=method_info["refs"],
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
                else:
                    print(f"    실패: 빈 응답")
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"    쿼타 초과! 60초 대기 후 재시도...")
                    time.sleep(60)
                    try:
                        result = vtx_client.models.edit_image(
                            model="imagen-3.0-capability-001",
                            prompt=full_prompt,
                            reference_images=method_info["refs"],
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
                            print(f"    재시도 성공: {out_path} ({size_kb:.0f}KB)")
                        else:
                            print(f"    재시도 실패: 빈 응답")
                    except Exception as e2:
                        print(f"    재시도 에러: {e2}")
                else:
                    print(f"    에러: {e}")

    print(f"\n{'='*60}")
    print("완료! 비교:")
    print("  A_00~02 = Subject만 (기존)")
    print("  B_00~02 = Subject + Style")
    print("  C_00~02 = Subject + FaceMesh")
    print("  D_00~02 = Subject + Style + FaceMesh")
    print(f"출력: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

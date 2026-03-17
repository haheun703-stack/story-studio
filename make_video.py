"""
30장면 Ken Burns 효과 영상 합성
각 장면에 줌인/줌아웃/패닝 효과 적용 → 전체 연결
"""

import subprocess, os, json
from pathlib import Path

FFMPEG = "ffmpeg"
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
IMAGES_DIR = EPISODE_DIR / "images2"
VIDEO_DIR = EPISODE_DIR / "video"
VIDEO_DIR.mkdir(exist_ok=True)

DURATION = 18  # 초 per scene
FPS = 30
TOTAL_FRAMES = DURATION * FPS


def get_ken_burns_filter(index: int) -> str:
    """장면 인덱스에 따라 Ken Burns 효과 번갈아 적용"""
    pattern = index % 4

    if pattern == 0:
        # 느린 줌인 (중앙)
        return (
            f"zoompan=z='min(zoom+0.0005,1.3)':d={TOTAL_FRAMES}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    elif pattern == 1:
        # 느린 줌아웃 (중앙)
        return (
            f"zoompan=z='if(lte(on,1),1.3,max(1.001,zoom-0.0005))':d={TOTAL_FRAMES}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    elif pattern == 2:
        # 왼쪽→오른쪽 패닝
        return (
            f"zoompan=z='1.2':d={TOTAL_FRAMES}"
            f":x='if(lte(on,1),0,min(x+0.5,(iw-iw/zoom)))'"
            f":y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    else:
        # 위→아래 패닝
        return (
            f"zoompan=z='1.2':d={TOTAL_FRAMES}"
            f":x='iw/2-(iw/zoom/2)'"
            f":y='if(lte(on,1),0,min(y+0.3,(ih-ih/zoom)))'"
            f":s=1920x1080:fps={FPS}"
        )


def main():
    scene_files = sorted(IMAGES_DIR.glob("scene_*_up.png"))
    print(f"장면 수: {len(scene_files)}")
    print(f"장면당 {DURATION}초 → 예상 총 길이: {len(scene_files) * DURATION // 60}분 {len(scene_files) * DURATION % 60}초")
    print("=" * 60)

    # 1. 각 장면 → Ken Burns 클립 생성
    clips = []
    for i, img_path in enumerate(scene_files):
        clip_path = VIDEO_DIR / f"clip_{i:02d}.mp4"
        clips.append(clip_path)

        if clip_path.exists():
            print(f"  [{i:02d}] 이미 존재, 스킵")
            continue

        vf = get_ken_burns_filter(i)

        cmd = [
            FFMPEG, "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf", vf,
            "-t", str(DURATION),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(clip_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"  [{i:02d}] 완료: {clip_path.name}")
        else:
            print(f"  [{i:02d}] 에러: {result.stderr[-200:]}")

    # 2. concat 파일 생성
    concat_path = VIDEO_DIR / "concat.txt"
    with open(concat_path, "w", encoding="utf-8") as f:
        for clip in clips:
            abs_path = os.path.abspath(str(clip)).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    # 3. 전체 영상 합성
    final_path = EPISODE_DIR / "final_video.mp4"
    print(f"\n전체 영상 합성 중...")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(final_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        probe = subprocess.run(
            [FFMPEG, "-i", str(final_path)],
            capture_output=True, text=True,
        )
        for line in probe.stderr.split("\n"):
            if "Duration" in line:
                print(f"  {line.strip()}")
                break
        size_mb = final_path.stat().st_size / (1024 * 1024)
        print(f"  크기: {size_mb:.1f}MB")
        print(f"  저장: {final_path}")
    else:
        print(f"에러: {result.stderr[-300:]}")

    print("\n완료!")


if __name__ == "__main__":
    main()

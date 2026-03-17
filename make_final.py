"""
최종 합성: 나레이션(TTS) + 이미지(Ken Burns) → 완성 영상
각 장면의 길이를 나레이션 길이에 맞춤
"""

import subprocess, os, json, wave
from pathlib import Path

FFMPEG = "ffmpeg"
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
IMAGES_DIR = EPISODE_DIR / "images2"
TTS_DIR = EPISODE_DIR / "tts"
FINAL_DIR = EPISODE_DIR / "final_clips"
FINAL_DIR.mkdir(exist_ok=True)

FPS = 30


def get_wav_duration(wav_path: Path) -> float:
    """WAV 파일 길이(초) 반환"""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def get_ken_burns_filter(index: int, total_frames: int) -> str:
    """Ken Burns 효과"""
    pattern = index % 4
    if pattern == 0:
        return (
            f"zoompan=z='min(zoom+0.0005,1.3)':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    elif pattern == 1:
        return (
            f"zoompan=z='if(lte(on,1),1.3,max(1.001,zoom-0.0005))':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    elif pattern == 2:
        return (
            f"zoompan=z='1.2':d={total_frames}"
            f":x='if(lte(on,1),0,min(x+0.5,(iw-iw/zoom)))'"
            f":y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    else:
        return (
            f"zoompan=z='1.2':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)'"
            f":y='if(lte(on,1),0,min(y+0.3,(ih-ih/zoom)))'"
            f":s=1920x1080:fps={FPS}"
        )


def main():
    scene_images = sorted(IMAGES_DIR.glob("scene_*_up.png"))
    scene_audios = sorted(TTS_DIR.glob("narration_*.wav"))

    n_scenes = min(len(scene_images), len(scene_audios))
    print(f"장면 수: {n_scenes}")
    print("=" * 60)

    # 1. 각 장면: 이미지 + 나레이션 → 클립
    clips = []
    total_duration = 0

    for i in range(n_scenes):
        img_path = scene_images[i]
        wav_path = scene_audios[i]
        clip_path = FINAL_DIR / f"clip_{i:02d}.mp4"
        clips.append(clip_path)

        if clip_path.exists():
            # 기존 클립 길이 확인
            probe = subprocess.run(
                [FFMPEG, "-i", str(clip_path)],
                capture_output=True, text=True,
            )
            print(f"  [{i:02d}] 이미 존재, 스킵")
            continue

        # 나레이션 길이 + 앞뒤 여유 2초
        audio_dur = get_wav_duration(wav_path)
        scene_dur = audio_dur + 3.0  # 나레이션 후 여운 3초
        total_frames = int(scene_dur * FPS)
        total_duration += scene_dur

        vf = get_ken_burns_filter(i, total_frames)

        # 이미지 → 영상 + 오디오 합성
        cmd = [
            FFMPEG, "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-i", str(wav_path),
            "-vf", vf,
            "-t", str(scene_dur),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            str(clip_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            total_duration += scene_dur
            print(f"  [{i:02d}] 완료: {clip_path.name} (나레이션 {audio_dur:.1f}초 + 여운 → {scene_dur:.1f}초)")
        else:
            print(f"  [{i:02d}] 에러: {result.stderr[-200:]}")

    # 2. concat 파일 생성
    concat_path = FINAL_DIR / "concat.txt"
    with open(concat_path, "w", encoding="utf-8") as f:
        for clip in clips:
            abs_path = os.path.abspath(str(clip)).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    # 3. 최종 영상 합성
    final_path = EPISODE_DIR / "엄마는_햇님이_되었어요_완성.mp4"
    print(f"\n최종 영상 합성 중...")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "128k",
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

"""
60장면 최종 합성: 나레이션(TTS) + 이미지(Ken Burns) → 완성 영상
각 장면의 길이를 나레이션 길이에 맞춤
"""

import subprocess, os, json, wave
from pathlib import Path

FFMPEG = "ffmpeg"
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
IMAGES_DIR = EPISODE_DIR / "images_v2"
TTS_DIR = EPISODE_DIR / "tts_v2"
FINAL_DIR = EPISODE_DIR / "final_clips_v2"
FINAL_DIR.mkdir(exist_ok=True)

FPS = 30


def get_wav_duration(wav_path: Path) -> float:
    """WAV 파일 길이(초) 반환"""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def get_ken_burns_filter(index: int, total_frames: int) -> str:
    """Ken Burns 효과 (4가지 패턴 순환)"""
    pattern = index % 4
    if pattern == 0:
        # 느린 줌인 (중앙)
        return (
            f"zoompan=z='min(zoom+0.0005,1.3)':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    elif pattern == 1:
        # 느린 줌아웃 (중앙)
        return (
            f"zoompan=z='if(lte(on,1),1.3,max(1.001,zoom-0.0005))':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    elif pattern == 2:
        # 왼쪽→오른쪽 패닝
        return (
            f"zoompan=z='1.2':d={total_frames}"
            f":x='if(lte(on,1),0,min(x+0.5,(iw-iw/zoom)))'"
            f":y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS}"
        )
    else:
        # 위→아래 패닝
        return (
            f"zoompan=z='1.2':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)'"
            f":y='if(lte(on,1),0,min(y+0.3,(ih-ih/zoom)))'"
            f":s=1920x1080:fps={FPS}"
        )


def main():
    # 업스케일 이미지 우선, 없으면 일반 이미지
    scene_images = sorted(IMAGES_DIR.glob("scene_*_up.png"))
    if not scene_images:
        scene_images = sorted(IMAGES_DIR.glob("scene_*.png"))
        scene_images = [p for p in scene_images if "_up" not in p.stem]

    scene_audios = sorted(TTS_DIR.glob("narration_*.wav"))

    n_scenes = min(len(scene_images), len(scene_audios))
    print(f"이미지: {len(scene_images)}장, 나레이션: {len(scene_audios)}개")
    print(f"합성할 장면 수: {n_scenes}")
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
            dur = get_clip_duration(clip_path)
            if dur > 0:
                total_duration += dur
                print(f"  [{i:02d}] 이미 존재 ({dur:.1f}초), 스킵")
                continue

        # 나레이션 길이 + 여운
        audio_dur = get_wav_duration(wav_path)
        scene_dur = audio_dur + 2.0  # 나레이션 후 여운 2초
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

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            print(f"  [{i:02d}] 완료: {clip_path.name} (나레이션 {audio_dur:.1f}초 → 클립 {scene_dur:.1f}초)")
        else:
            stderr = result.stderr.decode("utf-8", errors="ignore")
            print(f"  [{i:02d}] 에러: {stderr[-200:]}")

    est_min = int(total_duration // 60)
    est_sec = int(total_duration % 60)
    print(f"\n예상 총 길이: {est_min}분 {est_sec}초")

    # 2. concat 파일 생성
    concat_path = FINAL_DIR / "concat.txt"
    with open(concat_path, "w", encoding="utf-8") as f:
        for clip in clips:
            if clip.exists():
                abs_path = os.path.abspath(str(clip)).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

    # 3. 최종 영상 합성
    final_path = EPISODE_DIR / "final_complete_v2.mp4"
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

    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if result.returncode == 0:
        probe = subprocess.run(
            [FFMPEG, "-i", str(final_path)],
            capture_output=True,
        )
        stderr = probe.stderr.decode("utf-8", errors="ignore")
        for line in stderr.split("\n"):
            if "Duration" in line:
                print(f"  {line.strip()}")
                break
        size_mb = final_path.stat().st_size / (1024 * 1024)
        print(f"  크기: {size_mb:.1f}MB")
        print(f"  저장: {final_path}")
    else:
        stderr = result.stderr.decode("utf-8", errors="ignore")
        print(f"에러: {stderr[-300:]}")

    print("\n완료!")


def get_clip_duration(clip_path: Path) -> float:
    """기존 클립 길이 반환"""
    try:
        result = subprocess.run(
            [FFMPEG, "-i", str(clip_path)],
            capture_output=True,
        )
        stderr = result.stderr.decode("utf-8", errors="ignore")
        for line in stderr.split("\n"):
            if "Duration" in line:
                parts = line.strip().split("Duration:")[1].split(",")[0].strip()
                h, m, s = parts.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    main()

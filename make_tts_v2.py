"""
60장면 TTS 나레이션 생성 (v2 시나리오, Gemini 2.5 Flash TTS)
"""

import os, json, time, wave
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"')
EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
TTS_DIR = EPISODE_DIR / "tts_v2"
TTS_DIR.mkdir(exist_ok=True)


def generate_tts(text: str, output_path: Path, voice: str = "Kore") -> bool:
    """Gemini 2.5 Flash TTS로 음성 생성"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                )
            ),
        ),
    )

    # WAV 파일 저장
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(24000)
        wf.writeframes(audio_data)

    return True


def main():
    # v2 60장면 시나리오 로드
    with open(EPISODE_DIR / "scenario_v2_60.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data["scenes"]
    print(f"TTS 생성: {len(scenes)}장면")
    print("=" * 60)

    success = 0
    for i, scene in enumerate(scenes):
        wav_path = TTS_DIR / f"narration_{i:02d}.wav"

        if wav_path.exists():
            print(f"  [{i:02d}] 이미 존재, 스킵")
            success += 1
            continue

        text = scene["narration_kr"]
        print(f"  [{i:02d}] \"{text[:40]}...\"")

        for attempt in range(3):
            try:
                generate_tts(text, wav_path)
                size_kb = wav_path.stat().st_size / 1024
                print(f"       → 저장: {wav_path.name} ({size_kb:.0f}KB)")
                success += 1
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 30 * (attempt + 1)
                    print(f"       쿼타 초과! {wait}초 대기... ({attempt+1}/3)")
                    time.sleep(wait)
                else:
                    print(f"       에러: {e}")
                    break

        time.sleep(2)  # API 딜레이

    print(f"\n완료! 성공: {success}/{len(scenes)}")
    print(f"저장 폴더: {TTS_DIR}")


if __name__ == "__main__":
    main()

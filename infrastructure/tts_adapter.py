"""
Gemini 2.5 Flash TTS 어댑터
google.genai SDK를 사용하여 텍스트를 음성으로 변환합니다.
"""
import logging
import wave
from pathlib import Path

from google import genai
from google.genai import types

from core.entities import MediaAsset, MediaType, AssetStatus
from core.interfaces import ITTSGenerator
from core.exceptions import MediaGenerationError

logger = logging.getLogger(__name__)


class GeminiTTSGenerator(ITTSGenerator):
    """Gemini 2.5 Flash TTS를 사용한 음성 생성기"""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-preview-tts",
        output_dir: str = "output/media/audio",
        default_voice: str = "Kore",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_voice = default_voice

    def generate_speech(self, text: str, voice: str = "") -> MediaAsset:
        """텍스트를 음성으로 변환합니다."""
        voice_name = voice or self.default_voice
        logger.info("TTS 생성 중 (voice=%s): %s", voice_name, text[:60])

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                ),
            )

            if not response.candidates or not response.candidates[0].content.parts:
                raise MediaGenerationError("TTS", "음성이 생성되지 않았습니다")

            audio_data = response.candidates[0].content.parts[0].inline_data.data

            file_name = f"tts_{hash(text) & 0xFFFFFFFF:08x}.wav"
            file_path = self.output_dir / file_name

            with wave.open(str(file_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(audio_data)

            logger.info("TTS 저장 완료: %s", file_path)

            return MediaAsset(
                asset_type=MediaType.AUDIO,
                file_path=str(file_path),
                prompt_used=text[:200],
                status=AssetStatus.COMPLETED,
                metadata={"voice": voice_name},
            )

        except MediaGenerationError:
            raise
        except Exception as e:
            raise MediaGenerationError("TTS", str(e))

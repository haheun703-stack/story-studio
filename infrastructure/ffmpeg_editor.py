"""
FFmpeg 기반 영상 편집 모듈

이미지 슬라이드쇼 생성, 영상 연결, 오디오 합성 등
ffmpeg CLI를 사용한 편집 기능의 뼈대를 제공합니다.
"""
import logging
import os
import subprocess
import tempfile
from typing import List, Optional

logger = logging.getLogger(__name__)


class FFmpegEditor:
    """ffmpeg를 사용한 영상 편집기"""

    # 최종 출력 기본 하위 디렉토리
    DEFAULT_OUTPUT_SUBDIR = os.path.join("output", "media", "final")

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._available = self._check_ffmpeg()

    # ── 내부 유틸 ──────────────────────────────────────────────

    def _check_ffmpeg(self) -> bool:
        """ffmpeg 설치 여부를 확인합니다.

        ffmpeg -version 을 실행하여 정상 응답이 오는지 검사합니다.
        ffmpeg가 설치되어 있지 않아도 크래시 없이 경고만 출력합니다.

        Returns:
            True이면 ffmpeg 사용 가능, False이면 사용 불가.
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            if result.returncode == 0:
                # 첫 줄에서 버전 정보 추출
                version_line = result.stdout.decode("utf-8", errors="replace").split("\n")[0]
                logger.info("ffmpeg 확인 완료: %s", version_line.strip())
                return True
            else:
                logger.warning(
                    "ffmpeg가 비정상 종료되었습니다 (exit code %d). "
                    "영상 편집 기능이 비활성화됩니다.",
                    result.returncode,
                )
                return False
        except FileNotFoundError:
            logger.warning(
                "ffmpeg를 찾을 수 없습니다 (경로: %s). "
                "영상 편집 기능이 비활성화됩니다. "
                "ffmpeg를 설치하거나 FFMPEG_PATH 환경변수를 설정해 주세요.",
                self.ffmpeg_path,
            )
            return False
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg 버전 확인 시 타임아웃이 발생했습니다.")
            return False
        except Exception as e:
            logger.warning("ffmpeg 확인 중 예기치 않은 오류: %s", e)
            return False

    def _ensure_output_dir(self, output_path: str) -> None:
        """출력 파일의 디렉토리가 존재하지 않으면 생성합니다."""
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    def _run_ffmpeg(self, args: List[str], description: str = "") -> subprocess.CompletedProcess:
        """ffmpeg 명령어를 실행하고 결과를 반환합니다.

        Args:
            args: ffmpeg에 전달할 인자 리스트 (ffmpeg 경로 제외).
            description: 로그에 표시할 작업 설명.

        Returns:
            subprocess.CompletedProcess 객체.

        Raises:
            RuntimeError: ffmpeg가 사용 불가능하거나 명령 실행에 실패한 경우.
        """
        if not self._available:
            raise RuntimeError(
                "ffmpeg를 사용할 수 없습니다. ffmpeg를 설치해 주세요."
            )

        cmd = [self.ffmpeg_path] + args
        logger.debug("ffmpeg 실행: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,  # 최대 10분
            )
            if result.returncode != 0:
                stderr_text = result.stderr.decode("utf-8", errors="replace")
                logger.error(
                    "ffmpeg %s 실패 (exit code %d): %s",
                    description, result.returncode, stderr_text[-500:],
                )
                raise RuntimeError(
                    f"ffmpeg {description} 실패 (exit code {result.returncode})"
                )
            logger.info("ffmpeg %s 완료", description)
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ffmpeg {description} 시 타임아웃 (600초 초과)")

    # ── 공개 메서드 ─────────────────────────────────────────────

    def create_slideshow(
        self,
        image_paths: List[str],
        audio_path: str,
        output_path: str,
        duration_per_image: float = 5.0,
    ) -> str:
        """이미지 슬라이드쇼 + 오디오 -> 영상을 생성합니다.

        각 이미지를 duration_per_image 초 동안 보여주는 슬라이드쇼를 만들고,
        오디오 트랙을 함께 합성합니다.

        Args:
            image_paths: 슬라이드쇼에 사용할 이미지 파일 경로 리스트 (순서대로).
            audio_path: 배경 오디오 파일 경로.
            output_path: 출력 영상 파일 경로.
            duration_per_image: 이미지 한 장당 표시 시간(초). 기본 5초.

        Returns:
            생성된 영상 파일의 절대 경로.

        Raises:
            RuntimeError: ffmpeg 미설치 또는 명령 실행 실패 시.
            ValueError: 입력 파일이 없는 경우.
        """
        if not image_paths:
            raise ValueError("슬라이드쇼를 만들 이미지가 없습니다.")

        self._ensure_output_dir(output_path)

        # concat demuxer용 입력 목록 파일 생성
        # 절대 경로로 변환 (임시 파일 위치와 무관하게 동작하도록)
        concat_lines = []
        for img_path in image_paths:
            abs_path = os.path.abspath(img_path).replace("\\", "/")
            safe_path = abs_path.replace("'", "'\\''")
            concat_lines.append(f"file '{safe_path}'")
            concat_lines.append(f"duration {duration_per_image}")
        # 마지막 이미지를 한 번 더 추가 (concat demuxer 특성상 필요)
        abs_last = os.path.abspath(image_paths[-1]).replace("\\", "/")
        safe_last = abs_last.replace("'", "'\\''")
        concat_lines.append(f"file '{safe_last}'")

        concat_content = "\n".join(concat_lines)

        # 임시 파일에 concat 목록 저장
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(concat_content)
            concat_file = f.name

        try:
            # ffmpeg 명령어 구성
            # -f concat: concat demuxer 사용
            # -safe 0: 절대 경로 허용
            # -i concat.txt: 이미지 목록
            # -i audio: 오디오 입력
            # -c:v libx264: H.264 코덱
            # -pix_fmt yuv420p: 호환성 높은 픽셀 포맷
            # -c:a aac: AAC 오디오 코덱
            # -shortest: 짧은 쪽에 맞춰 종료
            # -y: 출력 파일 덮어쓰기
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-i", audio_path,
                "-c:v", "libx264",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # 짝수 해상도 보정
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                "-y",
                output_path,
            ]
            self._run_ffmpeg(args, description="슬라이드쇼 생성")
        finally:
            # 임시 concat 파일 정리
            try:
                os.unlink(concat_file)
            except OSError:
                pass

        logger.info(
            "슬라이드쇼 생성 완료: 이미지 %d장, 출력=%s",
            len(image_paths), output_path,
        )
        return os.path.abspath(output_path)

    def concat_videos(self, video_paths: List[str], output_path: str) -> str:
        """여러 영상을 순서대로 이어붙입니다.

        ffmpeg concat demuxer 방식을 사용하여 동일 코덱의 영상들을
        재인코딩 없이 빠르게 연결합니다.

        Args:
            video_paths: 연결할 영상 파일 경로 리스트 (순서대로).
            output_path: 출력 영상 파일 경로.

        Returns:
            생성된 영상 파일의 절대 경로.

        Raises:
            RuntimeError: ffmpeg 미설치 또는 명령 실행 실패 시.
            ValueError: 입력 영상이 없는 경우.
        """
        if not video_paths:
            raise ValueError("이어붙일 영상이 없습니다.")

        if len(video_paths) == 1:
            logger.info("영상이 1개뿐이므로 그대로 반환합니다.")
            return os.path.abspath(video_paths[0])

        self._ensure_output_dir(output_path)

        # concat demuxer용 입력 목록 파일 생성
        # 절대 경로로 변환 (임시 파일 위치와 무관하게 동작하도록)
        concat_lines = []
        for vpath in video_paths:
            abs_path = os.path.abspath(vpath).replace("\\", "/")
            safe_path = abs_path.replace("'", "'\\''")
            concat_lines.append(f"file '{safe_path}'")

        concat_content = "\n".join(concat_lines)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(concat_content)
            concat_file = f.name

        try:
            # -f concat: concat demuxer 사용
            # -safe 0: 절대 경로 허용
            # -c copy: 재인코딩 없이 복사
            # -y: 출력 파일 덮어쓰기
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y",
                output_path,
            ]
            self._run_ffmpeg(args, description="영상 연결")
        finally:
            try:
                os.unlink(concat_file)
            except OSError:
                pass

        logger.info(
            "영상 연결 완료: %d개 영상 -> %s", len(video_paths), output_path,
        )
        return os.path.abspath(output_path)

    def add_audio_to_video(
        self, video_path: str, audio_path: str, output_path: str
    ) -> str:
        """영상에 오디오 트랙을 추가합니다.

        기존 영상의 비디오 스트림은 재인코딩 없이 복사하고,
        오디오는 AAC 코덱으로 인코딩하여 합성합니다.

        Args:
            video_path: 입력 영상 파일 경로.
            audio_path: 추가할 오디오 파일 경로.
            output_path: 출력 영상 파일 경로.

        Returns:
            생성된 영상 파일의 절대 경로.

        Raises:
            RuntimeError: ffmpeg 미설치 또는 명령 실행 실패 시.
        """
        self._ensure_output_dir(output_path)

        # -i video: 영상 입력
        # -i audio: 오디오 입력
        # -c:v copy: 비디오 스트림 복사 (재인코딩 없음)
        # -c:a aac: 오디오를 AAC로 인코딩
        # -map 0:v:0: 첫 번째 입력의 비디오 스트림 선택
        # -map 1:a:0: 두 번째 입력의 오디오 스트림 선택
        # -shortest: 짧은 쪽에 맞춰 종료
        # -y: 출력 파일 덮어쓰기
        args = [
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            output_path,
        ]
        self._run_ffmpeg(args, description="오디오 합성")

        logger.info(
            "오디오 합성 완료: 영상=%s, 오디오=%s -> %s",
            video_path, audio_path, output_path,
        )
        return os.path.abspath(output_path)

    def create_episode_video(self, episode_media: dict) -> str:
        """에피소드의 모든 미디어를 조합하여 최종 영상을 생성합니다.

        처리 흐름:
          1. 이미지가 있으면 -> 슬라이드쇼 영상 생성
          2. 개별 영상 클립이 있으면 -> concat으로 연결
          3. 슬라이드쇼 + 연결 영상을 하나로 결합
          4. 오디오가 있으면 -> 최종 영상에 오디오 합성

        Args:
            episode_media: 미디어 정보 딕셔너리.
                - "images": List[str] - 이미지 파일 경로 리스트
                - "videos": List[str] - 영상 파일 경로 리스트
                - "audio": List[str] - 오디오 파일 경로 리스트
                - "output_dir": str - 출력 디렉토리 (기본: output/media/final)
                - "episode_id": str - 에피소드 ID (파일명에 사용)
                - "duration_per_image": float - 이미지당 표시 시간(초, 기본 5.0)

        Returns:
            최종 생성된 영상 파일의 절대 경로.

        Raises:
            RuntimeError: ffmpeg 미설치 또는 처리 실패 시.
            ValueError: 이미지와 영상이 모두 없는 경우.
        """
        images: List[str] = episode_media.get("images", [])
        videos: List[str] = episode_media.get("videos", [])
        audio_files: List[str] = episode_media.get("audio", [])
        output_dir: str = episode_media.get("output_dir", self.DEFAULT_OUTPUT_SUBDIR)
        episode_id: str = episode_media.get("episode_id", "episode")
        duration_per_image: float = episode_media.get("duration_per_image", 5.0)

        if not images and not videos:
            raise ValueError(
                "최종 영상을 생성할 이미지 또는 영상 소스가 없습니다."
            )

        os.makedirs(output_dir, exist_ok=True)

        # 중간 생성물 경로들 (나중에 정리)
        temp_files: List[str] = []

        try:
            # ── 1단계: 이미지 슬라이드쇼 생성 ──────────────────────
            slideshow_path: Optional[str] = None
            if images:
                slideshow_path = os.path.join(output_dir, f"{episode_id}_slideshow.mp4")
                # 오디오가 있으면 첫 번째 오디오를 슬라이드쇼 배경으로 사용
                if audio_files:
                    self.create_slideshow(
                        image_paths=images,
                        audio_path=audio_files[0],
                        output_path=slideshow_path,
                        duration_per_image=duration_per_image,
                    )
                else:
                    # 오디오 없이 무음 슬라이드쇼 생성
                    self._create_silent_slideshow(
                        image_paths=images,
                        output_path=slideshow_path,
                        duration_per_image=duration_per_image,
                    )
                temp_files.append(slideshow_path)
                logger.info("1단계 완료: 슬라이드쇼 생성 (%d장)", len(images))

            # ── 2단계: 영상 클립 연결 ───────────────────────────
            concat_path: Optional[str] = None
            if videos:
                if len(videos) > 1:
                    concat_path = os.path.join(output_dir, f"{episode_id}_concat.mp4")
                    self.concat_videos(video_paths=videos, output_path=concat_path)
                    temp_files.append(concat_path)
                else:
                    concat_path = videos[0]
                logger.info("2단계 완료: 영상 연결 (%d개)", len(videos))

            # ── 3단계: 슬라이드쇼 + 연결 영상 결합 ─────────────────
            combined_path: str
            if slideshow_path and concat_path:
                # 슬라이드쇼와 영상 클립 모두 있으면 이어붙이기
                combined_path = os.path.join(output_dir, f"{episode_id}_combined.mp4")
                self.concat_videos(
                    video_paths=[slideshow_path, concat_path],
                    output_path=combined_path,
                )
                temp_files.append(combined_path)
                logger.info("3단계 완료: 슬라이드쇼 + 영상 결합")
            elif slideshow_path:
                combined_path = slideshow_path
            elif concat_path:
                combined_path = concat_path
            else:
                # 여기까지 오지 않아야 함 (위에서 ValueError 처리)
                raise RuntimeError("결합할 영상이 없습니다.")

            # ── 4단계: 최종 오디오 합성 ─────────────────────────
            final_path = os.path.join(output_dir, f"{episode_id}_final.mp4")

            # 슬라이드쇼에 이미 오디오가 포함된 경우가 아닌,
            # 별도 배경 음악 등 추가 오디오가 있는 경우 합성
            if audio_files and len(audio_files) > 1 and combined_path != slideshow_path:
                # 두 번째 오디오 파일을 배경 음악으로 합성
                self.add_audio_to_video(
                    video_path=combined_path,
                    audio_path=audio_files[1],
                    output_path=final_path,
                )
                logger.info("4단계 완료: 추가 오디오 합성")
            elif audio_files and not images:
                # 이미지 없이 영상만 있는 경우, 오디오 합성
                self.add_audio_to_video(
                    video_path=combined_path,
                    audio_path=audio_files[0],
                    output_path=final_path,
                )
                logger.info("4단계 완료: 오디오 합성 (영상 전용)")
            else:
                # 추가 오디오 처리 불필요 -> 결합 영상을 최종 결과로 복사/이동
                if combined_path != final_path:
                    import shutil
                    shutil.copy2(combined_path, final_path)
                logger.info("4단계 완료: 추가 오디오 없음, 영상 복사")

        finally:
            # 중간 생성물 정리 (최종 파일 제외)
            for tmp in temp_files:
                if tmp != final_path and os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                        logger.debug("임시 파일 삭제: %s", tmp)
                    except OSError:
                        pass

        logger.info(
            "에피소드 영상 생성 완료: %s (이미지 %d장, 영상 %d개, 오디오 %d개)",
            final_path, len(images), len(videos), len(audio_files),
        )
        return os.path.abspath(final_path)

    # ── 보조 메서드 ─────────────────────────────────────────────

    def _create_silent_slideshow(
        self,
        image_paths: List[str],
        output_path: str,
        duration_per_image: float = 5.0,
    ) -> str:
        """오디오 없이 무음 슬라이드쇼를 생성합니다.

        Args:
            image_paths: 이미지 파일 경로 리스트.
            output_path: 출력 영상 파일 경로.
            duration_per_image: 이미지 한 장당 표시 시간(초).

        Returns:
            생성된 영상 파일의 절대 경로.
        """
        if not image_paths:
            raise ValueError("슬라이드쇼를 만들 이미지가 없습니다.")

        self._ensure_output_dir(output_path)

        # concat demuxer용 입력 목록 파일 생성
        # 절대 경로로 변환 (임시 파일 위치와 무관하게 동작하도록)
        concat_lines = []
        for img_path in image_paths:
            abs_path = os.path.abspath(img_path).replace("\\", "/")
            safe_path = abs_path.replace("'", "'\\''")
            concat_lines.append(f"file '{safe_path}'")
            concat_lines.append(f"duration {duration_per_image}")
        abs_last = os.path.abspath(image_paths[-1]).replace("\\", "/")
        safe_last = abs_last.replace("'", "'\\''")
        concat_lines.append(f"file '{safe_last}'")

        concat_content = "\n".join(concat_lines)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(concat_content)
            concat_file = f.name

        try:
            # 오디오 없는 슬라이드쇼 생성
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-pix_fmt", "yuv420p",
                "-y",
                output_path,
            ]
            self._run_ffmpeg(args, description="무음 슬라이드쇼 생성")
        finally:
            try:
                os.unlink(concat_file)
            except OSError:
                pass

        return os.path.abspath(output_path)

    @property
    def is_available(self) -> bool:
        """ffmpeg 사용 가능 여부를 반환합니다."""
        return self._available

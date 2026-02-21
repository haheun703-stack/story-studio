"""
YouTube Data API v3를 사용한 영상 업로드 어댑터
OAuth 2.0 인증 기반

사용 전 Google Cloud Console에서:
1. YouTube Data API v3 활성화
2. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
3. 클라이언트 시크릿 JSON 다운로드 → credentials/youtube_oauth.json
"""

import json
import logging
from pathlib import Path
from typing import Optional

from core.entities import Episode, AgeGroup, ContentType

logger = logging.getLogger(__name__)

# YouTube API 스코프
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = "credentials/youtube_token.json"


class YouTubeUploader:
    """YouTube Data API v3를 사용한 영상 업로더

    아동 콘텐츠(COPPA) 규정을 준수하여 모든 영상을
    made_for_kids=True, privacy_status="private"로 기본 설정합니다.

    Attributes:
        credentials_path: OAuth 클라이언트 시크릿 파일 경로
    """

    def __init__(self, credentials_path: str = "credentials/youtube_oauth.json"):
        self.credentials_path = credentials_path
        self._service = None  # YouTube API service 객체 (lazy init)

    # ── 인증 ─────────────────────────────────────────────────

    def authenticate(self) -> bool:
        """OAuth 2.0 인증을 수행합니다.

        기존 토큰이 유효하면 재사용하고, 만료되었으면 갱신합니다.
        토큰이 없으면 브라우저 기반 OAuth 플로우를 실행합니다.

        Returns:
            인증 성공 여부
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None
            token_path = Path(TOKEN_PATH)

            # 1. 기존 토큰 로드 시도
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                logger.info("기존 토큰 로드 완료")

            # 2. 토큰이 없거나 만료된 경우
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                    logger.info("토큰 갱신 완료")
                else:
                    # OAuth 시크릿 파일 확인
                    secret_path = Path(self.credentials_path)
                    if not secret_path.exists():
                        logger.error(
                            "OAuth 시크릿 파일 없음: %s\n"
                            "Google Cloud Console에서 다운로드하여 해당 경로에 저장하세요.",
                            self.credentials_path,
                        )
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(secret_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth 인증 완료 (브라우저)")

                # 3. 토큰 저장
                token_path.parent.mkdir(parents=True, exist_ok=True)
                token_path.write_text(creds.to_json())
                logger.info("토큰 저장: %s", token_path)

            # 4. YouTube API 서비스 객체 생성
            self._service = build("youtube", "v3", credentials=creds)
            logger.info("YouTube API 서비스 초기화 완료")
            return True

        except ImportError as e:
            logger.error("필수 패키지 미설치: %s (pip install google-auth-oauthlib google-api-python-client)", e)
            return False
        except Exception as e:
            logger.error("YouTube OAuth 인증 실패: %s", e)
            return False

    # ── 영상 업로드 ──────────────────────────────────────────

    def upload(self, video_path: str, episode: Episode) -> Optional[str]:
        """영상을 YouTube에 업로드하고 영상 URL을 반환합니다.

        Args:
            video_path: 업로드할 영상 파일 경로
            episode: 메타데이터 생성에 사용할 에피소드 객체

        Returns:
            업로드 성공 시 YouTube 영상 URL (https://youtu.be/{video_id}),
            실패 시 None
        """
        # 인증 확인
        if self._service is None:
            logger.warning("YouTube API 미인증 - 자동 인증 시도")
            if not self.authenticate():
                logger.error("YouTube 인증 실패, 업로드 중단")
                return None

        # 영상 파일 확인
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error("영상 파일 없음: %s", video_path)
            return None

        metadata = self.build_metadata(episode)

        try:
            from googleapiclient.http import MediaFileUpload

            body = {
                "snippet": {
                    "title": metadata["title"],
                    "description": metadata["description"],
                    "tags": metadata["tags"],
                    "categoryId": metadata["category_id"],
                },
                "status": {
                    "privacyStatus": metadata["privacy_status"],
                    "selfDeclaredMadeForKids": metadata["made_for_kids"],
                },
            }

            media = MediaFileUpload(
                str(video_file),
                mimetype="video/*",
                resumable=True,
                chunksize=10 * 1024 * 1024,  # 10MB 청크
            )

            request = self._service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            logger.info("YouTube 업로드 시작: %s (%d bytes)", video_file.name, video_file.stat().st_size)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info("업로드 진행률: %d%%", int(status.progress() * 100))

            video_id = response["id"]
            video_url = f"https://youtu.be/{video_id}"
            logger.info("YouTube 업로드 완료: %s", video_url)
            return video_url

        except Exception as e:
            logger.error("YouTube 업로드 실패: %s", e)
            return None

    # ── 메타데이터 생성 ──────────────────────────────────────

    def build_metadata(self, episode: Episode) -> dict:
        """에피소드 정보로 YouTube 메타데이터를 생성합니다.

        연령 그룹과 콘텐츠 유형에 따라 적절한 카테고리, 태그,
        설명문을 자동 구성합니다.

        Args:
            episode: 메타데이터를 생성할 에피소드 객체

        Returns:
            YouTube 업로드에 필요한 메타데이터 딕셔너리:
            - title: 영상 제목
            - description: 영상 설명
            - tags: 태그 목록
            - category_id: YouTube 카테고리 ID
            - privacy_status: 공개 상태 ("private")
            - made_for_kids: 아동용 콘텐츠 여부 (True)
        """
        # 연령 그룹별 카테고리/태그 설정
        age_label = episode.age_group.value
        type_label = episode.content_type.value

        tags = [age_label, type_label, "교육", "아동"]
        if episode.age_group == AgeGroup.PRESCHOOL:
            tags.extend(["유치원", "동화", "어린이"])
            category_id = "22"  # People & Blogs
        else:
            tags.extend(["초등학교", "학습", "교과서"])
            category_id = "27"  # Education

        # 설명문 구성
        description_lines = [
            f"\U0001F4DA {episode.title}",
            f"",
            f"\U0001F3AF 대상: {age_label} ({episode.content_type.value})",
            f"",
        ]

        if episode.story:
            description_lines.append(
                f"\U0001F4D6 총 {len(episode.story.scenes)}개 장면으로 구성"
            )

        if episode.character:
            description_lines.append(
                f"\U0001F464 캐릭터: {episode.character.name} - {episode.character.description}"
            )

        description_lines.extend([
            "",
            "---",
            "Story Studio에서 자동 생성된 콘텐츠입니다.",
            "#아동교육 #AI콘텐츠",
        ])

        return {
            "title": f"[{age_label}] {episode.title}",
            "description": "\n".join(description_lines),
            "tags": tags,
            "category_id": category_id,
            "privacy_status": "private",     # 기본 비공개 (안전)
            "made_for_kids": True,            # 아동용 콘텐츠 (COPPA 준수)
        }

    # ── 썸네일 설정 ──────────────────────────────────────────

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """업로드된 영상의 썸네일을 설정합니다.

        Args:
            video_id: YouTube 영상 ID
            thumbnail_path: 썸네일 이미지 파일 경로

        Returns:
            설정 성공 여부
        """
        if self._service is None:
            logger.error("YouTube API 미인증 상태입니다.")
            return False

        thumb_file = Path(thumbnail_path)
        if not thumb_file.exists():
            logger.error("썸네일 파일 없음: %s", thumbnail_path)
            return False

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(str(thumb_file), mimetype="image/jpeg")
            self._service.thumbnails().set(
                videoId=video_id, media_body=media
            ).execute()

            logger.info("썸네일 설정 완료: video_id=%s", video_id)
            return True

        except Exception as e:
            logger.error("썸네일 설정 실패: %s", e)
            return False

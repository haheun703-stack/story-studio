"""
YouTube Data API v3를 사용한 영상 업로드 어댑터
OAuth 2.0 인증 기반

실제 업로드 기능은 google-api-python-client 패키지 설치 후 구현 예정입니다.
현재는 메타데이터 생성(build_metadata)만 완전히 동작하며,
인증/업로드/썸네일 설정은 뼈대(TODO)로 남겨져 있습니다.
"""

import logging
from pathlib import Path
from typing import Optional

from core.entities import Episode, AgeGroup, ContentType

logger = logging.getLogger(__name__)


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

        google-auth, google-api-python-client 패키지를 사용하여
        브라우저 기반 OAuth 인증 플로우를 실행합니다.
        인증 성공 시 토큰을 credentials/youtube_token.json에 저장합니다.

        Returns:
            인증 성공 여부 (현재는 항상 False)
        """
        # TODO: google-auth, google-api-python-client 사용
        # 1. credentials_path에서 OAuth 클라이언트 시크릿 로드
        #    client_secret = Path(self.credentials_path)
        #    if not client_secret.exists():
        #        logger.error("OAuth 시크릿 파일 없음: %s", self.credentials_path)
        #        return False
        #
        # 2. 사용자 인증 플로우 실행 (브라우저 기반)
        #    from google_auth_oauthlib.flow import InstalledAppFlow
        #    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        #    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
        #    credentials = flow.run_local_server(port=0)
        #
        # 3. 토큰 저장 (credentials/youtube_token.json)
        #    token_path = Path("credentials/youtube_token.json")
        #    token_path.write_text(credentials.to_json())
        #
        # 4. YouTube API 서비스 객체 생성
        #    from googleapiclient.discovery import build
        #    self._service = build("youtube", "v3", credentials=credentials)

        logger.info("YouTube OAuth 인증 (TODO: 실제 구현)")
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
        # TODO: 실제 YouTube API 호출
        # 1. 인증 확인
        #    if self._service is None:
        #        logger.error("YouTube API 미인증 상태입니다. authenticate()를 먼저 호출하세요.")
        #        return None
        #
        # 2. 영상 파일 존재 확인
        #    video_file = Path(video_path)
        #    if not video_file.exists():
        #        logger.error("영상 파일 없음: %s", video_path)
        #        return None
        #
        # 3. 메타데이터 생성
        metadata = self.build_metadata(episode)
        #
        # 4. YouTube API 요청 바디 구성
        #    body = {
        #        "snippet": {
        #            "title": metadata["title"],
        #            "description": metadata["description"],
        #            "tags": metadata["tags"],
        #            "categoryId": metadata["category_id"],
        #        },
        #        "status": {
        #            "privacyStatus": metadata["privacy_status"],
        #            "selfDeclaredMadeForKids": metadata["made_for_kids"],
        #        },
        #    }
        #
        # 5. MediaFileUpload로 파일 업로드
        #    from googleapiclient.http import MediaFileUpload
        #    media = MediaFileUpload(video_path, mimetype="video/*", resumable=True)
        #    request = self._service.videos().insert(
        #        part="snippet,status", body=body, media_body=media
        #    )
        #
        # 6. 업로드 진행률 로깅
        #    response = None
        #    while response is None:
        #        status, response = request.next_chunk()
        #        if status:
        #            logger.info("업로드 진행률: %d%%", int(status.progress() * 100))
        #
        # 7. 성공 시 video_id 반환
        #    video_id = response["id"]
        #    video_url = f"https://youtu.be/{video_id}"
        #    logger.info("업로드 완료: %s", video_url)
        #    return video_url

        logger.info("YouTube 업로드 (TODO): title=%s", metadata["title"])
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
            f"📚 {episode.title}",
            f"",
            f"🎯 대상: {age_label} ({episode.content_type.value})",
            f"",
        ]

        if episode.story:
            description_lines.append(
                f"📖 총 {len(episode.story.scenes)}개 장면으로 구성"
            )

        if episode.character:
            description_lines.append(
                f"👤 캐릭터: {episode.character.name} - {episode.character.description}"
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
            설정 성공 여부 (현재는 항상 False)
        """
        # TODO: thumbnails.set API 호출
        # 1. 파일 존재 확인
        #    thumb_file = Path(thumbnail_path)
        #    if not thumb_file.exists():
        #        logger.error("썸네일 파일 없음: %s", thumbnail_path)
        #        return False
        #
        # 2. 썸네일 설정 API 호출
        #    from googleapiclient.http import MediaFileUpload
        #    media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        #    self._service.thumbnails().set(
        #        videoId=video_id, media_body=media
        #    ).execute()
        #
        # 3. 성공 로깅
        #    logger.info("썸네일 설정 완료: video_id=%s", video_id)
        #    return True

        logger.info("썸네일 설정 (TODO): video_id=%s", video_id)
        return False

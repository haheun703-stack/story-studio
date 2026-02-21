"""
출력 포맷팅 유틸리티
CLI에서 사용하는 모든 출력 형식을 정의합니다.
"""
from application.dto import StoryResult


def format_story_result(result: StoryResult) -> str:
    """StoryResult를 사용자에게 보여줄 문자열로 포맷팅합니다."""
    lines = []

    for warning in result.warnings:
        lines.append(f"  주의: {warning}")

    if result.is_long_form_ready:
        lines.append(
            f"  완료: 총 {result.scene_count}개의 씬이 정상적으로 분할되었습니다. "
            "(롱폼 제작 기준 충족)"
        )

    separator = "=" * 60
    lines.append(f"\n{separator}")
    lines.append(f"  생성된 스토리 제목: {result.title}")
    lines.append(f"  대상: {result.audience_label}")
    lines.append(f"  주제: {result.theme}")
    lines.append(f"  생성된 씬 개수: {result.scene_count}")

    if result.saved_path:
        lines.append(f"  저장 위치: {result.saved_path}")

    lines.append(separator)

    if result.preview_scenes:
        lines.append(f"\n  씬 미리보기 (처음 {len(result.preview_scenes)}개):")
        for scene in result.preview_scenes:
            lines.append(f"\n--- 씬 {scene['scene_number']} ---")
            lines.append(f"  나레이션: {scene['narration']}")
            lines.append(f"  이미지 프롬프트: {scene['image_prompt']}")
            lines.append(f"  비디오 프롬프트: {scene['video_prompt']}")

    return "\n".join(lines)


def format_story_list(story_ids: list[str]) -> str:
    """저장된 스토리 목록을 포맷팅합니다."""
    if not story_ids:
        return "  저장된 스토리가 없습니다."

    lines = [f"  저장된 스토리 목록 ({len(story_ids)}개):"]
    for i, sid in enumerate(story_ids, 1):
        lines.append(f"  {i}. {sid}")
    return "\n".join(lines)


def format_error(error: Exception) -> str:
    """예외를 사용자 친화적 문자열로 포맷팅합니다."""
    return f"  오류 발생: {error}"

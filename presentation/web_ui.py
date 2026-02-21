"""
Story Studio 웹 인터페이스
Streamlit 기반의 에피소드 제작 UI
"""
import streamlit as st


def main():
    st.set_page_config(page_title="Story Studio", page_icon="\U0001F4DA", layout="wide")
    st.title("\U0001F4DA Story Studio - \uC544\uB3D9 \uCF58\uD150\uCE20 \uC790\uB3D9 \uC81C\uC791")

    # Container 초기화 (세션 상태로 캐싱)
    if "container" not in st.session_state:
        from container import Container
        st.session_state.container = Container()
    container = st.session_state.container

    # ── 사이드바: 제작 설정 ─────────────────────────────────────
    with st.sidebar:
        st.header("제작 설정")

        age_group = st.selectbox(
            "연령 그룹",
            ["유치부 (3~7세)", "초등부 (8~13세)"],
        )

        content_type = st.selectbox(
            "콘텐츠 유형",
            ["동화", "교과서"],
        )

        output_format = st.selectbox(
            "출력 형식",
            ["블로그+유튜브", "블로그", "유튜브영상"],
        )

        available_llms = container.story_generator().available_providers
        llm_provider = st.selectbox(
            "LLM 제공자",
            available_llms if available_llms else ["mock"],
        )

        character_name = st.text_input(
            "캐릭터 이름 (선택)",
            placeholder="기본: 자동 설정",
        )

    # ── 메인: 주제 입력 및 제작 ─────────────────────────────────
    theme = st.text_input(
        "\U0001F4DD 에피소드 주제를 입력하세요",
        placeholder="예: 마법의 숲 속 모험",
    )

    if st.button("\U0001F680 에피소드 제작 시작", type="primary", disabled=not theme):
        from application.dto import EpisodeRequest
        from core.entities import AgeGroup, ContentType, OutputFormat

        # 선택값 → Enum 매핑
        age_group_enum = AgeGroup.PRESCHOOL if "유치부" in age_group else AgeGroup.ELEMENTARY
        content_type_enum = ContentType.FAIRY_TALE if content_type == "동화" else ContentType.TEXTBOOK
        output_format_enum = OutputFormat(output_format)

        request = EpisodeRequest(
            age_group=age_group_enum,
            content_type=content_type_enum,
            theme=theme,
            output_format=output_format_enum,
            preferred_llm=llm_provider,
            character_name=character_name,
        )

        episode_use_case = container.episode_use_case(age_group_enum.value)

        with st.spinner("에피소드를 제작하고 있습니다..."):
            try:
                result = episode_use_case.produce(request)
                st.session_state.last_result = result
            except Exception as e:
                st.error(f"제작 실패: {e}")
                st.stop()

        # 결과 표시
        st.success(f"에피소드 제작 완료: {result.title}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("에피소드 ID", result.episode_id[:20])
        with col2:
            st.metric("미디어 에셋", f"{result.media_count}개")
        with col3:
            completed = sum(1 for s in result.stage_summary.values() if s == "완료")
            total = len(result.stage_summary)
            st.metric("진행률", f"{completed}/{total} 단계")

        # 단계별 결과
        st.subheader("파이프라인 단계 요약")
        for stage, status in result.stage_summary.items():
            if status == "완료":
                st.write(f"\u2705 {stage}: {status}")
            elif status == "실패":
                st.write(f"\u274C {stage}: {status}")
            else:
                st.write(f"\u2796 {stage}: {status}")

        if result.output_paths:
            st.subheader("저장 경로")
            for path in result.output_paths:
                st.code(path)

        if result.warnings:
            st.subheader("경고")
            for w in result.warnings:
                st.warning(w)

    # ── 하단: 에피소드 제작 이력 ────────────────────────────────
    st.divider()
    st.subheader("\U0001F4CB 제작 이력")

    episode_repo = container.episode_repository()
    from core.entities import AgeGroup
    for ag in AgeGroup:
        episode_ids = episode_repo.list_by_age_group(ag)
        if episode_ids:
            st.write(f"**{ag.value}**: {len(episode_ids)}건")
            for eid in episode_ids[-5:]:  # 최근 5건만 표시
                st.text(f"  - {eid}")
        else:
            st.write(f"**{ag.value}**: 없음")


if __name__ == "__main__":
    main()

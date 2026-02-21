"""
Story Studio 웹 인터페이스
Streamlit 기반의 에피소드 제작 UI
"""
import streamlit as st


def main():
    st.set_page_config(page_title="Story Studio", page_icon="📚", layout="wide")
    st.title("📚 Story Studio - 아동 콘텐츠 자동 제작")

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

        llm_provider = st.selectbox(
            "LLM 제공자",
            ["gemini", "gpt", "claude"],
        )

        character_name = st.text_input(
            "캐릭터 이름 (선택)",
            placeholder="기본: 자동 설정",
        )

    # ── 메인: 주제 입력 및 제작 ─────────────────────────────────
    theme = st.text_input(
        "📝 에피소드 주제를 입력하세요",
        placeholder="예: 마법의 숲 속 모험",
    )

    if st.button("🚀 에피소드 제작 시작", type="primary", disabled=not theme):
        # TODO: Container에서 episode_use_case 생성
        #   from container import Container
        #   container = Container()
        #   age_group_value = "유치부" if "유치부" in age_group else "초등부"
        #   use_case = container.episode_use_case(age_group_value)

        # TODO: EpisodeRequest 생성
        #   from application.dto import EpisodeRequest
        #   from core.entities import AgeGroup, ContentType, OutputFormat
        #   request = EpisodeRequest(
        #       age_group=AgeGroup.PRESCHOOL if "유치부" in age_group else AgeGroup.ELEMENTARY,
        #       content_type=ContentType.FAIRY_TALE if content_type == "동화" else ContentType.TEXTBOOK,
        #       theme=theme,
        #       output_format=OutputFormat(output_format),
        #       preferred_llm=llm_provider,
        #       character_name=character_name,
        #   )

        # TODO: produce() 호출 및 결과 표시
        #   result = use_case.produce(request)

        with st.spinner("에피소드를 제작하고 있습니다..."):
            st.info("파이프라인 실행 중... (이 부분은 실제 연동 시 구현)")
            # TODO: 실제 container 연동

        # 결과 표시 영역
        st.success("에피소드 제작 완료!")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("생성된 씬", "150개")
        with col2:
            st.metric("이미지", "10개")
        with col3:
            st.metric("진행률", "100%")

    # ── 하단: 에피소드 제작 이력 ────────────────────────────────
    st.divider()
    st.subheader("📋 제작 이력")
    st.info("저장된 에피소드가 여기에 표시됩니다.")


if __name__ == "__main__":
    main()

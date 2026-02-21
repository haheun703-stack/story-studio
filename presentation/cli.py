"""
CLI 인터페이스
사용자와의 상호작용을 담당하는 프레젠테이션 계층입니다.
"""
import argparse
import sys
from typing import Optional, TYPE_CHECKING

from core.entities import TargetAudience, AgeGroup, ContentType, OutputFormat
from core.exceptions import StoryDomainError
from application.dto import StoryRequest, EpisodeRequest
from application.use_cases import StoryGenerationUseCase
from .formatters import format_story_result, format_story_list, format_error

if TYPE_CHECKING:
    from container import Container


class StoryStudioCLI:
    """Story Studio CLI 애플리케이션"""

    def __init__(
        self,
        use_case: StoryGenerationUseCase,
        available_llms: list[str],
        container: Optional['Container'] = None,
    ):
        self.use_case = use_case
        self.available_llms = available_llms
        self.container = container

    def run(self, args: list[str] = None) -> None:
        """CLI 진입점"""
        parser = self._build_parser()
        parsed = parser.parse_args(args)

        if parsed.command == "generate":
            self._handle_generate(parsed)
        elif parsed.command == "list":
            self._handle_list()
        elif parsed.command == "produce":
            self._handle_produce(parsed)
        elif parsed.command == "status":
            self._handle_status(parsed)
        else:
            parser.print_help()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="story-studio",
            description="Story Studio - 동화/교육 콘텐츠 제작 도구",
        )
        subparsers = parser.add_subparsers(dest="command")

        # 'generate' 서브커맨드 (기존)
        gen_parser = subparsers.add_parser("generate", help="새 스토리를 생성합니다")
        gen_parser.add_argument(
            "--audience",
            type=str,
            choices=[a.name.lower() for a in TargetAudience],
            default="elementary",
            help="대상 연령층 (기본: elementary)",
        )
        gen_parser.add_argument(
            "--theme",
            type=str,
            required=True,
            help="스토리 주제 (예: '우주 정거장의 비밀')",
        )
        gen_parser.add_argument(
            "--llm",
            type=str,
            default=None,
            help="사용할 LLM 제공자 (gemini, gpt, claude)",
        )
        gen_parser.add_argument(
            "--no-save",
            action="store_true",
            help="생성된 스토리를 파일로 저장하지 않음",
        )

        # 'list' 서브커맨드 (기존)
        subparsers.add_parser("list", help="저장된 스토리 목록을 표시합니다")

        # 'produce' 서브커맨드 (신규 - 전체 파이프라인)
        prod_parser = subparsers.add_parser("produce", help="에피소드 전체 제작 파이프라인을 실행합니다")
        prod_parser.add_argument(
            "--age-group",
            type=str,
            choices=["preschool", "elementary"],
            default="preschool",
            help="대상 연령 그룹 (기본: preschool)",
        )
        prod_parser.add_argument(
            "--content-type",
            type=str,
            choices=["fairy_tale", "textbook"],
            default="fairy_tale",
            help="콘텐츠 유형 (기본: fairy_tale)",
        )
        prod_parser.add_argument(
            "--theme",
            type=str,
            required=True,
            help="에피소드 주제",
        )
        prod_parser.add_argument(
            "--output-format",
            type=str,
            choices=["blog", "youtube", "both"],
            default="both",
            help="출력 형식 (기본: both)",
        )
        prod_parser.add_argument(
            "--character",
            type=str,
            default="",
            help="사회자 캐릭터 이름 (기본: 자동 설정)",
        )
        prod_parser.add_argument(
            "--llm",
            type=str,
            default="gemini",
            help="사용할 LLM 제공자",
        )

        # 'status' 서브커맨드 (신규)
        status_parser = subparsers.add_parser("status", help="에피소드 제작 진행 상황을 조회합니다")
        status_parser.add_argument(
            "--episode-id",
            type=str,
            required=True,
            help="에피소드 ID",
        )

        return parser

    def _handle_generate(self, args) -> None:
        """스토리 생성 명령 처리"""
        audience_map = {a.name.lower(): a for a in TargetAudience}
        audience = audience_map[args.audience]

        preferred_llm = args.llm or "gemini"

        # LLM 라우터에 제공자 설정
        from infrastructure.llm_router import LLMRouter
        generator = self.use_case.story_generator
        if isinstance(generator, LLMRouter) and args.llm:
            generator.set_provider(args.llm)

        request = StoryRequest(
            audience=audience,
            theme=args.theme,
            save_to_file=not args.no_save,
            preferred_llm=preferred_llm,
        )

        print(f"\n  [{audience.value}] 타겟으로 '{args.theme}' 주제의 스토리 생성을 시작합니다...")
        print(f"  LLM 제공자: {preferred_llm}")

        try:
            result = self.use_case.run(request)
            print(format_story_result(result))
        except StoryDomainError as e:
            print(format_error(e))
            sys.exit(1)

    def _handle_list(self) -> None:
        """저장된 스토리 목록 표시"""
        if self.use_case.story_repository:
            stories = self.use_case.story_repository.list_all()
            print(format_story_list(stories))
        else:
            print("  스토리 저장소가 설정되지 않았습니다.")

    def _handle_produce(self, args) -> None:
        """에피소드 제작 명령 처리"""
        if not self.container:
            print("  에피소드 제작 기능이 설정되지 않았습니다.")
            sys.exit(1)

        age_group_map = {"preschool": AgeGroup.PRESCHOOL, "elementary": AgeGroup.ELEMENTARY}
        content_type_map = {"fairy_tale": ContentType.FAIRY_TALE, "textbook": ContentType.TEXTBOOK}
        output_format_map = {"blog": OutputFormat.BLOG, "youtube": OutputFormat.YOUTUBE_VIDEO, "both": OutputFormat.BOTH}

        request = EpisodeRequest(
            age_group=age_group_map[args.age_group],
            content_type=content_type_map[args.content_type],
            theme=args.theme,
            output_format=output_format_map[args.output_format],
            preferred_llm=args.llm,
            character_name=args.character,
        )

        # age_group에 맞는 episode_use_case를 동적 생성
        episode_use_case = self.container.episode_use_case(request.age_group.value)

        print(f"\n  에피소드 제작 시작")
        print(f"  연령 그룹: {request.age_group.value}")
        print(f"  콘텐츠 유형: {request.content_type.value}")
        print(f"  주제: {args.theme}")
        print(f"  출력 형식: {request.output_format.value}")

        try:
            result = episode_use_case.produce(request)

            print(f"\n{'='*60}")
            print(f"  에피소드 제작 완료")
            print(f"{'='*60}")
            print(f"  ID: {result.episode_id}")
            print(f"  제목: {result.title}")
            print(f"  연령: {result.age_group_label}")
            print(f"  유형: {result.content_type_label}")
            print(f"  미디어 에셋: {result.media_count}개")

            print(f"\n  파이프라인 단계 요약:")
            for stage, status in result.stage_summary.items():
                marker = "V" if status == "완료" else ("X" if status == "실패" else "-")
                print(f"    [{marker}] {stage}: {status}")

            if result.output_paths:
                print(f"\n  저장 경로:")
                for path in result.output_paths:
                    print(f"    {path}")

            if result.warnings:
                print(f"\n  경고:")
                for w in result.warnings:
                    print(f"    - {w}")

        except StoryDomainError as e:
            print(format_error(e))
            sys.exit(1)

    def _handle_status(self, args) -> None:
        """에피소드 제작 진행 상황 조회"""
        if not self.container:
            print("  에피소드 제작 기능이 설정되지 않았습니다.")
            sys.exit(1)

        # status 조회는 age_group 무관 (저장소만 필요)
        episode_use_case = self.container.episode_use_case()
        status = episode_use_case.get_status(args.episode_id)
        if not status:
            print(f"  에피소드를 찾을 수 없습니다: {args.episode_id}")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"  에피소드 상태: {status.episode_id}")
        print(f"{'='*60}")
        print(f"  진행률: {status.progress_percent:.1f}%")

        if status.current_stage:
            print(f"  현재 단계: {status.current_stage}")

        if status.completed_stages:
            print(f"  완료 단계: {', '.join(status.completed_stages)}")

        if status.failed_stages:
            print(f"  실패 단계: {', '.join(status.failed_stages)}")

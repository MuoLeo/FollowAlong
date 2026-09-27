"""Usage: python ai/tutorial_analysis/main.py path/to/tutorial.mp4 [--export-clips]."""

import argparse
import logging
import math
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

if __package__:
    from .pipeline import analyze, resolve_video
else:
    # Support direct execution as well as importing this module from a server.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tutorial_analysis.pipeline import analyze, resolve_video


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("0보다 큰 유한한 숫자를 입력하세요.")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="튜토리얼 영상의 검토용 단계 후보 생성")
    parser.add_argument("video", help="MP4 파일 경로 또는 MP4 하나가 있는 폴더")
    parser.add_argument("--output", type=Path, help="새 결과 폴더. 기존 폴더는 덮어쓰지 않음")
    parser.add_argument("--model", default="small", help="faster-whisper 모델 크기 또는 로컬 모델 경로")
    parser.add_argument("--language", default="ko", help="ko, en, auto 등")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--scene-threshold", type=positive, default=27.0)
    parser.add_argument("--min-step", type=positive, default=5.0, help="최소 후보 길이(초)")
    parser.add_argument("--pause", type=positive, default=1.5, help="음성 구간 사이 휴지 기준(초)")
    parser.add_argument("--snap", type=positive, default=2.0, help="장면 전환과 음성 경계 결합 범위(초)")
    parser.add_argument("--export-clips", action="store_true", help="후보별 MP4도 저장")
    parser.add_argument("--skip-speech", action="store_true", help="장면 탐지 단독 점검용")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        video = resolve_video(args.video)
        run_name = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
        output = (args.output or Path(__file__).resolve().parents[2] / "storage" / "analysis" / run_name).resolve()
        result = analyze(video, output, model_size=args.model, language=args.language,
                         device=args.device, scene_threshold=args.scene_threshold,
                         min_step=args.min_step, pause=args.pause, snap=args.snap,
                         export_clips=args.export_clips, skip_speech=args.skip_speech)
    except (ValueError, OSError, RuntimeError) as exc:
        logging.error("%s", exc)
        return 1
    print(f"단계 후보 {len(result['steps'])}개: {output / 'steps.json'}")
    for warning in result["warnings"]:
        print(f"주의: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

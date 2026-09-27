"""File/media adapters. Keep model calls outside the segmentation algorithm."""

import json
import logging
import shutil
import subprocess
from pathlib import Path

from .segmentation import build_steps

LOG = logging.getLogger(__name__)


def run_command(args):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed: {result.stderr[-2000:]}")
    return result.stdout


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def resolve_video(value):
    path = Path(value).expanduser().resolve()
    if path.is_dir():
        videos = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".mp4")
        if len(videos) != 1:
            raise ValueError(f"폴더에는 MP4가 정확히 1개 있어야 합니다. 발견: {len(videos)}. 파일 경로를 지정하세요.")
        path = videos[0]
    if not path.is_file() or path.suffix.lower() != ".mp4":
        raise ValueError(f"MP4 파일을 찾을 수 없습니다: {path}")
    return path


def analyze(video, output, *, model_size="small", language="ko", device="cpu",
            scene_threshold=27.0, min_step=5.0, pause=1.5, snap=2.0,
            export_clips=False, skip_speech=False):
    # Fail before creating a run directory or downloading a model.
    for program in ("ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise RuntimeError(f"{program}가 PATH에 없습니다. FFmpeg 설치 후 새 터미널을 여세요.")
    try:
        from scenedetect import ContentDetector, detect
        if not skip_speech:
            from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("먼저 python -m pip install -r ai/tutorial_analysis/requirements.txt 를 실행하세요.") from exc

    output.mkdir(parents=True, exist_ok=False)
    # Use one zero-based, constant-frame-rate timeline for speech/scenes/clips.
    # This also avoids differences in VFR decoding between the two libraries.
    playback = output / "playback.mp4"
    LOG.info("1/4 재생용 영상 정규화 (30 FPS)")
    run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                 "-i", str(video), "-map", "0:v:0", "-map", "0:a:0?",
                 "-vf", "fps=30", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                 "-c:a", "aac", "-movflags", "+faststart", str(playback)])
    probe = json.loads(run_command(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                    "-of", "json", str(playback)]))
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    duration = float(video_stream["duration"])
    has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
    warnings = ["규칙 기반 단계 후보입니다. 조립 의미/완료 상태를 자동 이해한 결과가 아닙니다."]
    segments = []
    detected_language = None
    if has_audio and not skip_speech:
        LOG.info("2/4 음성 인식: %s (%s), 최초 실행 시 모델 다운로드", model_size, device)
        audio = output / "audio.wav"
        run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                     "-i", str(playback), "-vn", "-ac", "1", "-ar", "16000", str(audio)])
        model = WhisperModel(model_size, device=device,
                             compute_type="int8" if device == "cpu" else "float16")
        result, info = model.transcribe(str(audio), language=None if language == "auto" else language,
                                        vad_filter=True, word_timestamps=True)
        for segment in result:  # Inference runs when this generator is consumed.
            start = max(0.0, float(segment.start))
            end = min(duration, float(segment.end))
            if end <= start:
                continue
            segments.append({"segment_id": len(segments), "start_sec": start,
                             "end_sec": end, "text": segment.text.strip(),
                             "words": [{"start_sec": w.start, "end_sec": w.end, "text": w.word}
                                       for w in (segment.words or [])]})
        detected_language = info.language
        del model
        if not segments:
            warnings.append("인식된 음성이 없습니다. 장면 전환만 사용했습니다.")
    else:
        LOG.info("2/4 음성 인식 생략")
        warnings.append("음성 인식을 생략했거나 오디오 트랙이 없어 장면 전환만 사용했습니다.")
    save_json(output / "transcript.json", {"language": detected_language, "segments": segments})

    LOG.info("3/4 장면 전환 탐지")
    scenes = detect(str(playback), ContentDetector(threshold=scene_threshold),
                    start_in_scene=True, show_progress=True)
    scene_rows = [{"start_sec": a.get_seconds(), "end_sec": b.get_seconds()} for a, b in scenes]
    save_json(output / "scenes.json", {"threshold": scene_threshold, "scenes": scene_rows})
    cuts = [s["start_sec"] for s in scene_rows[1:]]
    LOG.info("4/4 단계 후보 생성")
    steps = build_steps(duration, segments, cuts, min_step=min_step, pause=pause, snap=snap)
    if len(steps) == 1:
        warnings.append("유효한 단계 경계를 찾지 못해 전체 영상을 하나의 후보로 유지했습니다.")
    document = {
        "schema_version": "0.1", "status": "draft", "method": "heuristic_v1",
        "source_video": str(video), "playback_file": "playback.mp4", "duration_sec": duration,
        "timeline": "playback.mp4; all exported times use this file",
        "config": {"model": model_size, "language": language, "device": device,
                   "scene_threshold": scene_threshold, "min_step_sec": min_step,
                   "pause_sec": pause, "snap_sec": snap, "skip_speech": skip_speech},
        "warnings": warnings, "steps": steps,
    }
    save_json(output / "steps.json", document)
    if export_clips:
        clips = output / "clips"
        clips.mkdir()
        for step in steps:
            filename = clips / f"{step['step_id']}.mp4"
            # Re-encode to avoid stream-copy boundaries snapping to keyframes.
            run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                         "-ss", str(step["start_sec"]), "-i", str(playback),
                         "-t", str(step["end_sec"] - step["start_sec"]),
                         "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264",
                         "-preset", "fast", "-crf", "20", "-c:a", "aac",
                         "-movflags", "+faststart", str(filename)])
            step["clip_file"] = f"clips/{filename.name}"
        save_json(output / "steps.json", document)
    return document

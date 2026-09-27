"""Dependency-free heuristic baseline; outputs reviewable candidates, not semantics."""

import math
import re


TRANSITION = re.compile(r"^(?:그\s*다음|다음(?:으로|은|에는)?|이제|마지막으로|먼저|next\b|then\b|finally\b)", re.I)


def build_steps(duration, segments, scene_cuts, *, min_step=5.0, pause=1.5, snap=2.0):
    """Combine cuts, speech pauses and transition cues on one seconds timeline.

    Priority: a transition cue > a pause > a visual cut. Nearby candidates are
    suppressed, not averaged, to keep the boundary on an observed timestamp.
    Speech overlap is retained in each affected step for transparent review.
    """
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration must be finite and positive")
    if not all(math.isfinite(v) for v in (min_step, pause, snap)) or min_step <= 0 or pause < 0 or snap < 0:
        raise ValueError("Invalid segmentation thresholds")
    ordered = sorted(segments, key=lambda s: s["start_sec"])
    for s in ordered:
        a, b = s["start_sec"], s["end_sec"]
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b <= duration + 0.1):
            raise ValueError("Transcript segment is outside the video timeline")

    speech_candidates = []
    previous_end = 0.0
    for i, s in enumerate(ordered):
        start = s["start_sec"]
        if i and start - previous_end >= pause:
            speech_candidates.append((start, 2, "speech_pause"))
        if TRANSITION.search(s["text"].strip()):
            speech_candidates.append((start, 3, "transition_phrase"))
        previous_end = max(previous_end, s["end_sec"])

    candidates = list(speech_candidates)
    for cut in scene_cuts:
        if not math.isfinite(cut) or not 0 < cut < duration:
            continue
        nearby = [c for c in speech_candidates if abs(c[0] - cut) <= snap]
        if nearby:
            closest = min(nearby, key=lambda c: (abs(c[0] - cut), -c[1]))
            candidates.append((closest[0], closest[1] + 1, closest[2] + "+scene_cut"))
        else:
            candidates.append((cut, 1, "scene_cut"))

    selected = []
    for candidate in sorted(candidates, key=lambda c: (-c[1], c[0])):
        t = candidate[0]
        if t < min_step or duration - t < min_step:
            continue
        if all(abs(t - chosen[0]) >= min_step for chosen in selected):
            selected.append(candidate)
    boundaries = [(0.0, 0, "video_start"), *sorted(selected), (duration, 0, "video_end")]
    steps = []
    for index, (left, right) in enumerate(zip(boundaries, boundaries[1:]), 1):
        start, end = left[0], right[0]
        overlaps = [s for s in ordered if s["start_sec"] < end and s["end_sec"] > start]
        steps.append({
            "step_id": f"step_{index:03d}", "order": index,
            "start_sec": start, "end_sec": end,
            "title": f"단계 후보 {index}",
            "transcript_text": " ".join(s["text"].strip() for s in overlaps),
            "transcript_segment_ids": [s["segment_id"] for s in overlaps],
            "boundary_reason": left[2], "needs_review": True,
            "target_state_id": None,
        })
    return steps

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tutorial_analysis.segmentation import build_steps
from tutorial_analysis.pipeline import resolve_video


def speech(start, end, text="설명", index=0):
    return {"segment_id": index, "start_sec": start, "end_sec": end, "text": text}


class SegmentationTests(unittest.TestCase):
    def test_no_signal_keeps_whole_video(self):
        steps = build_steps(20, [], [])
        self.assertEqual([(s["start_sec"], s["end_sec"]) for s in steps], [(0, 20)])

    def test_scene_cut_aligns_to_speech_cue(self):
        steps = build_steps(30, [speech(0, 8), speech(10, 18, "다음으로 블록을 끼웁니다", 1)], [9])
        self.assertEqual(steps[0]["end_sec"], 10)
        self.assertIn("scene_cut", steps[1]["boundary_reason"])

    def test_suppresses_short_tail_and_duplicate_cuts(self):
        steps = build_steps(25, [], [1, 10, 11, 24])
        self.assertEqual([(s["start_sec"], s["end_sec"]) for s in steps], [(0, 10), (10, 25)])

    def test_long_continuous_explanation_not_arbitrarily_split(self):
        self.assertEqual(len(build_steps(120, [speech(0, 120)], [])), 1)

    def test_crossing_transcript_is_not_lost(self):
        steps = build_steps(30, [speech(8, 12, "경계를 가로지르는 설명", 7)], [10])
        self.assertTrue(all(7 in s["transcript_segment_ids"] for s in steps))

    def test_invalid_timestamps_rejected(self):
        with self.assertRaises(ValueError):
            build_steps(20, [speech(10, 9)], [])
        with self.assertRaises(ValueError):
            build_steps(float("nan"), [], [])

    def test_folder_input_is_unambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                resolve_video(folder)
            first = folder / "한글 영상.MP4"
            first.touch()
            self.assertEqual(resolve_video(folder), first.resolve())
            (folder / "second.mp4").touch()
            with self.assertRaises(ValueError):
                resolve_video(folder)


if __name__ == "__main__":
    unittest.main()

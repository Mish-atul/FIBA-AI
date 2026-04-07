"""
SOP Validator — Standard Operating Procedure Compliance Checker.
================================================================
Uses a fine-tuned YOLOv8n-cls classifier trained on the assembly dataset
to classify each frame into task 0-6, detect task transitions, and
validate the sequence against the expected SOP.

No reference video needed — the classifier knows what each task looks like.

Fallback: If no trained classifier exists, uses scene-cut detection +
visual fingerprinting (reference-based approach).
"""

import cv2
import numpy as np
import time
import os
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass, field
import base64


# ── SOP Definition ────────────────────────────────────────

@dataclass
class SOPStep:
    step_num: int
    task_name: str
    description: str = ""


DEFAULT_SOP = [
    SOPStep(0, "Assembling the spring", "Pliers used to assemble spring component"),
    SOPStep(1, "Placing white plastic part", "White plastic piece positioned on assembly"),
    SOPStep(2, "Screwing-1", "First screwing with electric screwdriver"),
    SOPStep(3, "Inflating the valve", "Valve inflation using inflating tool"),
    SOPStep(4, "Placing black plastic part", "Black plastic piece positioned on assembly"),
    SOPStep(5, "Screwing-2", "Second screwing with electric screwdriver"),
    SOPStep(6, "Fixing the cable", "Cable/pipe package attached and fixed"),
]


# ── Data classes ──────────────────────────────────────────

@dataclass
class SOPSegment:
    """One detected task segment in the video."""
    start_frame: int
    end_frame: int
    duration_frames: int
    predicted_task: int = -1
    task_name: str = ""
    confidence: float = 0.0
    keyframe_b64: str = ""
    skeleton_b64: str = ""
    is_correct: bool = False


@dataclass
class SOPReferenceResult:
    """Result from learning reference (legacy mode)."""
    success: bool
    segments: List[SOPSegment] = field(default_factory=list)
    sop_steps: List[SOPStep] = field(default_factory=list)
    total_frames: int = 0
    fps: float = 0.0
    processing_time_s: float = 0.0
    error: str = ""


@dataclass
class SOPValidateResult:
    """Result from validating a video."""
    success: bool
    passed: bool = False
    segments: List[SOPSegment] = field(default_factory=list)
    step_results: List[dict] = field(default_factory=list)
    total_frames: int = 0
    fps: float = 0.0
    processing_time_s: float = 0.0
    error: str = ""
    summary: str = ""
    mode: str = "classifier"  # "classifier" or "fingerprint"


# ── Utilities ─────────────────────────────────────────────

def _encode_frame_b64(frame: np.ndarray, quality: int = 80) -> str:
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode("utf-8")


def _compute_histogram(frame: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv], [0], None, [32], [0, 180])
    s_hist = cv2.calcHist([hsv], [1], None, [16], [0, 256])
    v_hist = cv2.calcHist([hsv], [2], None, [16], [0, 256])
    hist = np.concatenate([h_hist.flatten(), s_hist.flatten(), v_hist.flatten()])
    total = hist.sum()
    if total > 0:
        hist = hist / total
    return hist


# ── Classifier-based SOP Validator ────────────────────────

class SOPClassifier:
    """Classifies video frames into task 0-6 using fine-tuned YOLOv8n-cls."""

    def __init__(self, model_path: str = "weights/sop_classifier.pt"):
        self.model = None
        self.available = False

        if os.path.exists(model_path):
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                self.available = True
                print(f"[SOP] Classifier loaded: {model_path}")
            except Exception as e:
                print(f"[SOP] Failed to load classifier: {e}")
        else:
            print(f"[SOP] No classifier at {model_path}. Run train_sop_classifier.py first.")

    def classify_frame(self, frame: np.ndarray) -> Tuple[int, float, str]:
        """Classify a single frame. Returns (task_id, confidence, task_name)."""
        if not self.available:
            return -1, 0.0, "unknown"

        results = self.model(frame, verbose=False)
        if not results:
            return -1, 0.0, "unknown"

        top1 = int(results[0].probs.top1)
        conf = float(results[0].probs.top1conf)
        name = str(self.model.names[top1])
        return top1, conf, name

    def classify_batch(self, frames: List[np.ndarray]) -> List[Tuple[int, float]]:
        """Classify multiple frames efficiently."""
        if not self.available:
            return [(-1, 0.0)] * len(frames)

        results_list = []
        # Process in small batches
        batch_size = 16
        for i in range(0, len(frames), batch_size):
            batch = frames[i:i+batch_size]
            results = self.model(batch, verbose=False)
            for r in results:
                top1 = int(r.probs.top1)
                conf = float(r.probs.top1conf)
                results_list.append((top1, conf))

        return results_list


# ── Main SOP Validator ────────────────────────────────────

class SOPValidator:
    """Validates assembly videos against SOP using trained classifier."""

    def __init__(self, sop_steps: List[SOPStep] = None):
        self.sop_steps = sop_steps or DEFAULT_SOP
        self.classifier = SOPClassifier()

        # Legacy fingerprint-based reference
        self.reference_fingerprints: List[np.ndarray] = []
        self.reference_segments: List[SOPSegment] = []
        self.has_reference = False

    def _get_hand_helpers(self):
        """Get hand detector and skeleton drawer if available."""
        try:
            from pipeline.hand_detector import HandDetector
            from pipeline.hand_skeleton import draw_hand_skeleton
            hd = HandDetector(min_detection_confidence=0.4)
            return hd, draw_hand_skeleton
        except Exception:
            return None, None

    def validate_with_classifier(
        self,
        video_path: str,
        progress_cb: Optional[Callable] = None,
    ) -> SOPValidateResult:
        """Validate a video using the trained classifier. No reference needed."""
        t0 = time.time()

        def progress(pct, msg):
            if progress_cb:
                progress_cb(pct, msg)

        try:
            progress(5, "Opening video...")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return SOPValidateResult(success=False, error=f"Cannot open: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Adaptive frame skip for speed
            if total_frames <= 300:
                skip = 3
            elif total_frames <= 1000:
                skip = 5
            else:
                skip = 8

            progress(10, f"Classifying {total_frames} frames (skip={skip})...")

            hand_detector, draw_skeleton = self._get_hand_helpers()

            # Read and classify frames
            all_predictions = []  # (frame_id, task_id, confidence)
            sampled_frames = {}   # frame_id -> frame (for key frame extraction)
            frame_id = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_id % skip == 0:
                    # Resize
                    h, w = frame.shape[:2]
                    if w > 640:
                        scale = 640 / w
                        frame = cv2.resize(frame, (640, int(h * scale)))

                    task_id, conf, _ = self.classifier.classify_frame(frame)
                    all_predictions.append((frame_id, task_id, conf))
                    sampled_frames[frame_id] = frame.copy()

                    if len(all_predictions) % 20 == 0:
                        pct = 10 + int((frame_id / max(total_frames, 1)) * 55)
                        progress(min(pct, 65), f"Classified {len(all_predictions)} frames...")

                frame_id += 1

            cap.release()

            if not all_predictions:
                return SOPValidateResult(success=False, error="No frames classified.")

            progress(68, "Detecting task transitions...")

            # ── Detect task transitions using sliding-window majority vote ──
            # Smooth predictions with a window to remove noise
            window_size = max(5, len(all_predictions) // 30)
            smoothed = []
            for i in range(len(all_predictions)):
                start = max(0, i - window_size // 2)
                end = min(len(all_predictions), i + window_size // 2 + 1)
                window_tasks = [all_predictions[j][1] for j in range(start, end)]
                # Majority vote
                from collections import Counter
                majority = Counter(window_tasks).most_common(1)[0][0]
                smoothed.append((all_predictions[i][0], majority, all_predictions[i][2]))

            # Find transitions: where majority class changes
            segments = []
            current_task = smoothed[0][1]
            seg_start_frame = smoothed[0][0]
            seg_confs = [smoothed[0][2]]

            for i in range(1, len(smoothed)):
                fid, task, conf = smoothed[i]
                if task != current_task:
                    # End current segment, start new one
                    segments.append({
                        "start_frame": seg_start_frame,
                        "end_frame": smoothed[i-1][0],
                        "task_id": current_task,
                        "avg_conf": float(np.mean(seg_confs)),
                    })
                    current_task = task
                    seg_start_frame = fid
                    seg_confs = [conf]
                else:
                    seg_confs.append(conf)

            # Last segment
            segments.append({
                "start_frame": seg_start_frame,
                "end_frame": smoothed[-1][0],
                "task_id": current_task,
                "avg_conf": float(np.mean(seg_confs)),
            })

            # Filter out very short segments (noise) — must be at least 3 frames
            min_seg_frames = max(3, len(all_predictions) // 50)
            segments = [s for s in segments if (s["end_frame"] - s["start_frame"]) >= min_seg_frames * skip]

            progress(75, f"Found {len(segments)} task segments. Extracting key frames...")

            # ── Build result segments with key frames ──
            result_segments = []
            for idx, seg in enumerate(segments):
                # Find closest sampled frame to segment midpoint
                mid_frame = (seg["start_frame"] + seg["end_frame"]) // 2
                closest_fid = min(sampled_frames.keys(), key=lambda f: abs(f - mid_frame))
                keyframe = sampled_frames[closest_fid]

                keyframe_b64 = _encode_frame_b64(keyframe)

                # Hand skeleton overlay
                skeleton_b64 = ""
                if hand_detector and draw_skeleton:
                    hand_result = hand_detector.detect(keyframe)
                    if hand_result.detected and hand_result.landmarks:
                        skel_frame = draw_skeleton(keyframe, hand_result.landmarks)
                        skeleton_b64 = _encode_frame_b64(skel_frame)

                task_id = seg["task_id"]
                task_name = ""
                if 0 <= task_id < len(self.sop_steps):
                    task_name = self.sop_steps[task_id].task_name

                result_segments.append(SOPSegment(
                    start_frame=seg["start_frame"],
                    end_frame=seg["end_frame"],
                    duration_frames=seg["end_frame"] - seg["start_frame"],
                    predicted_task=task_id,
                    task_name=task_name,
                    confidence=seg["avg_conf"],
                    keyframe_b64=keyframe_b64,
                    skeleton_b64=skeleton_b64,
                ))

                pct = 75 + int((idx / max(len(segments), 1)) * 15)
                progress(pct, f"Processing segment {idx+1}/{len(segments)}...")

            progress(92, "Validating sequence order...")

            # ── Validate sequence ──
            detected_sequence = [s.predicted_task for s in result_segments]
            expected_sequence = list(range(len(self.sop_steps)))

            all_correct = (detected_sequence == expected_sequence)

            step_results = []
            for i, seg in enumerate(result_segments):
                expected_task = i  # 0-indexed
                is_correct = (seg.predicted_task == expected_task)
                seg.is_correct = is_correct

                expected_sop = self.sop_steps[expected_task] if expected_task < len(self.sop_steps) else None
                detected_sop = self.sop_steps[seg.predicted_task] if 0 <= seg.predicted_task < len(self.sop_steps) else None

                step_results.append({
                    "position": i + 1,
                    "expected_step": expected_task,
                    "expected_task": expected_sop.task_name if expected_sop else f"Task {expected_task}",
                    "detected_step": seg.predicted_task,
                    "detected_task": detected_sop.task_name if detected_sop else f"Task {seg.predicted_task}",
                    "is_correct": is_correct,
                    "similarity": round(float(seg.confidence), 3),
                    "keyframe_b64": seg.keyframe_b64,
                    "skeleton_b64": seg.skeleton_b64,
                })

            elapsed = time.time() - t0

            # Build summary
            n_steps = len(step_results)
            if all_correct:
                summary = f"✅ SOP COMPLIANCE PASSED — All {n_steps} steps detected in correct order."
            else:
                violations = [r for r in step_results if not r["is_correct"]]
                # Check for specific known violations
                if len(detected_sequence) != len(expected_sequence):
                    summary = (
                        f"❌ SOP VIOLATION — Expected {len(expected_sequence)} steps "
                        f"but detected {len(detected_sequence)} segments. "
                    )
                else:
                    summary = (
                        f"❌ SOP VIOLATION — {len(violations)} step(s) out of order. "
                        + "; ".join(
                            f"Position {r['position']}: expected '{r['expected_task']}' but found '{r['detected_task']}'"
                            for r in violations
                        )
                    )

            progress(100, f"Done! ({elapsed:.1f}s)")

            return SOPValidateResult(
                success=True,
                passed=all_correct,
                segments=result_segments,
                step_results=step_results,
                total_frames=total_frames,
                fps=fps,
                processing_time_s=round(elapsed, 2),
                summary=summary,
                mode="classifier",
            )

        except Exception as e:
            import traceback
            return SOPValidateResult(success=False, error=f"{e}\n{traceback.format_exc()}")

    # ── Legacy fingerprint-based methods ──────────────────

    def learn_reference(
        self,
        video_path: str,
        progress_cb: Optional[Callable] = None,
    ) -> SOPReferenceResult:
        """Learn reference from known-correct video (fingerprint mode).
        If classifier is available, instead just validates and confirms."""
        t0 = time.time()

        def progress(pct, msg):
            if progress_cb:
                progress_cb(pct, msg)

        # If classifier is available, validate directly and use as "reference"
        if self.classifier.available:
            progress(5, "Classifier available — validating reference video...")
            result = self.validate_with_classifier(video_path, progress_cb)
            self.has_reference = True

            segments = []
            for seg in result.segments:
                segments.append(SOPSegment(
                    start_frame=seg.start_frame,
                    end_frame=seg.end_frame,
                    duration_frames=seg.duration_frames,
                    predicted_task=seg.predicted_task,
                    task_name=seg.task_name,
                    confidence=seg.confidence,
                    keyframe_b64=seg.keyframe_b64,
                    skeleton_b64=seg.skeleton_b64,
                ))

            return SOPReferenceResult(
                success=True,
                segments=segments,
                sop_steps=self.sop_steps[:len(segments)],
                total_frames=result.total_frames,
                fps=result.fps,
                processing_time_s=result.processing_time_s,
            )

        # Fallback: fingerprint-based reference learning
        try:
            progress(5, "Detecting scene boundaries...")

            boundaries, all_frames, vid_fps, total_frames = _detect_scene_boundaries(
                video_path,
                progress_cb=lambda p, m: progress(5 + int(p * 0.4), m),
            )

            if not boundaries:
                return SOPReferenceResult(
                    success=False,
                    error="No scene boundaries detected.",
                )

            progress(50, f"Found {len(boundaries)} segments. Computing fingerprints...")

            hand_detector, draw_skeleton = self._get_hand_helpers()

            segments = []
            for idx, (start, end) in enumerate(boundaries):
                seg_frames = all_frames[start:end + 1]
                fp = _compute_segment_fingerprint(seg_frames)

                mid = len(seg_frames) // 2
                keyframe = seg_frames[mid].copy()
                keyframe_b64 = _encode_frame_b64(keyframe)

                skeleton_b64 = ""
                if hand_detector and draw_skeleton:
                    hand_result = hand_detector.detect(keyframe)
                    if hand_result.detected and hand_result.landmarks:
                        skel_frame = draw_skeleton(keyframe, hand_result.landmarks)
                        skeleton_b64 = _encode_frame_b64(skel_frame)

                seg = SOPSegment(
                    start_frame=start,
                    end_frame=end,
                    duration_frames=end - start + 1,
                    predicted_task=idx,
                    task_name=self.sop_steps[idx].task_name if idx < len(self.sop_steps) else f"Step {idx}",
                    confidence=1.0,
                    keyframe_b64=keyframe_b64,
                    skeleton_b64=skeleton_b64,
                )
                segments.append(seg)

                pct = 50 + int((idx / len(boundaries)) * 40)
                progress(pct, f"Processing segment {idx + 1}/{len(boundaries)}...")

            self.reference_fingerprints = [_compute_segment_fingerprint(all_frames[s:e+1])
                                            for s, e in boundaries]
            self.reference_segments = segments
            self.has_reference = True

            elapsed = time.time() - t0
            progress(100, f"Reference learned! ({len(segments)} steps, {elapsed:.1f}s)")

            return SOPReferenceResult(
                success=True,
                segments=segments,
                sop_steps=self.sop_steps[:len(segments)],
                total_frames=total_frames,
                fps=vid_fps,
                processing_time_s=round(elapsed, 2),
            )

        except Exception as e:
            import traceback
            return SOPReferenceResult(success=False, error=f"{e}\n{traceback.format_exc()}")

    def validate(
        self,
        video_path: str,
        progress_cb: Optional[Callable] = None,
    ) -> SOPValidateResult:
        """Validate a video. Uses classifier if available, else fingerprints."""
        if self.classifier.available:
            return self.validate_with_classifier(video_path, progress_cb)

        # Fallback to fingerprint-based validation
        if not self.has_reference:
            return SOPValidateResult(
                success=False,
                error="No classifier trained and no reference loaded. "
                      "Either run train_sop_classifier.py or upload a reference video first.",
            )
        return self._validate_fingerprint(video_path, progress_cb)

    def _validate_fingerprint(
        self,
        video_path: str,
        progress_cb: Optional[Callable] = None,
    ) -> SOPValidateResult:
        """Fingerprint-based validation (legacy fallback)."""
        t0 = time.time()

        def progress(pct, msg):
            if progress_cb:
                progress_cb(pct, msg)

        try:
            progress(5, "Detecting scene boundaries in test video...")

            boundaries, all_frames, vid_fps, total_frames = _detect_scene_boundaries(
                video_path,
                progress_cb=lambda p, m: progress(5 + int(p * 0.4), m),
            )

            if not boundaries:
                return SOPValidateResult(success=False, error="No scene boundaries detected.")

            progress(50, f"Found {len(boundaries)} segments. Matching...")

            hand_detector, draw_skeleton = self._get_hand_helpers()

            test_fps = []
            test_segments = []
            for idx, (start, end) in enumerate(boundaries):
                seg_frames = all_frames[start:end + 1]
                fp = _compute_segment_fingerprint(seg_frames)
                test_fps.append(fp)

                mid = len(seg_frames) // 2
                keyframe = seg_frames[mid].copy()
                keyframe_b64 = _encode_frame_b64(keyframe)

                skeleton_b64 = ""
                if hand_detector and draw_skeleton:
                    hand_result = hand_detector.detect(keyframe)
                    if hand_result.detected and hand_result.landmarks:
                        skel_frame = draw_skeleton(keyframe, hand_result.landmarks)
                        skeleton_b64 = _encode_frame_b64(skel_frame)

                test_segments.append(SOPSegment(
                    start_frame=start,
                    end_frame=end,
                    duration_frames=end - start + 1,
                    keyframe_b64=keyframe_b64,
                    skeleton_b64=skeleton_b64,
                ))

            progress(80, "Matching against reference...")

            # Match test segments to reference
            n_ref = len(self.reference_fingerprints)
            n_test = len(test_fps)

            sim_matrix = np.zeros((n_test, n_ref), dtype=np.float32)
            for i in range(n_test):
                for j in range(n_ref):
                    corr = cv2.compareHist(test_fps[i].astype(np.float32),
                                            self.reference_fingerprints[j].astype(np.float32),
                                            cv2.HISTCMP_CORREL)
                    sim_matrix[i, j] = max(0.0, float(corr))

            # Greedy assignment
            used = set()
            for i in range(n_test):
                best_j, best_sim = -1, -1.0
                for j in range(n_ref):
                    if j not in used and sim_matrix[i, j] > best_sim:
                        best_sim = sim_matrix[i, j]
                        best_j = j
                if best_j >= 0:
                    test_segments[i].predicted_task = best_j
                    test_segments[i].confidence = best_sim
                    test_segments[i].task_name = self.sop_steps[best_j].task_name if best_j < len(self.sop_steps) else f"Step {best_j}"
                    used.add(best_j)

            # Check order
            all_correct = True
            step_results = []
            for i, seg in enumerate(test_segments):
                expected = i
                is_correct = (seg.predicted_task == expected)
                if not is_correct:
                    all_correct = False
                seg.is_correct = is_correct

                expected_sop = self.sop_steps[expected] if expected < len(self.sop_steps) else None
                detected_sop = self.sop_steps[seg.predicted_task] if 0 <= seg.predicted_task < len(self.sop_steps) else None

                step_results.append({
                    "position": i + 1,
                    "expected_step": expected,
                    "expected_task": expected_sop.task_name if expected_sop else f"Step {expected}",
                    "detected_step": seg.predicted_task,
                    "detected_task": detected_sop.task_name if detected_sop else f"Step {seg.predicted_task}",
                    "is_correct": is_correct,
                    "similarity": round(float(seg.confidence), 3),
                    "keyframe_b64": seg.keyframe_b64,
                    "skeleton_b64": seg.skeleton_b64,
                })

            elapsed = time.time() - t0
            if all_correct:
                summary = f"✅ SOP PASSED — All {len(step_results)} steps correct."
            else:
                violations = [r for r in step_results if not r["is_correct"]]
                summary = (f"❌ SOP VIOLATION — {len(violations)} step(s) out of order. "
                           + "; ".join(f"Pos {r['position']}: expected '{r['expected_task']}' got '{r['detected_task']}'" for r in violations))

            progress(100, f"Done! ({elapsed:.1f}s)")

            return SOPValidateResult(
                success=True, passed=all_correct, segments=test_segments,
                step_results=step_results, total_frames=total_frames,
                fps=vid_fps, processing_time_s=round(elapsed, 2),
                summary=summary, mode="fingerprint",
            )

        except Exception as e:
            import traceback
            return SOPValidateResult(success=False, error=f"{e}\n{traceback.format_exc()}")


# ── Legacy helper functions ───────────────────────────────

def _compute_segment_fingerprint(frames: List[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.zeros(64, dtype=np.float32)
    indices = np.linspace(0, len(frames) - 1, min(10, len(frames)), dtype=int)
    hists = [_compute_histogram(frames[i]) for i in indices]
    return np.mean(hists, axis=0).astype(np.float32)


def _detect_scene_boundaries(
    video_path: str,
    threshold: float = 25.0,
    min_segment_frames: int = 15,
    progress_cb: Optional[Callable] = None,
) -> Tuple[List[Tuple[int, int]], List[np.ndarray], float, int]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return [], [], 30.0, 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    all_frames = []
    frame_diffs = []
    prev_gray = None
    frame_id = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        if w > 640:
            scale = 640 / w
            frame = cv2.resize(frame, (640, int(h * scale)))
        all_frames.append(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            frame_diffs.append(float(np.mean(diff)))
        else:
            frame_diffs.append(0.0)
        prev_gray = gray
        frame_id += 1
        if progress_cb and frame_id % 30 == 0:
            pct = int((frame_id / max(total_frames, 1)) * 40)
            progress_cb(pct, f"Reading frames {frame_id}/{total_frames}...")

    cap.release()

    if not all_frames:
        return [], [], fps, 0

    diffs = np.array(frame_diffs)
    if len(diffs) > 10:
        mean_d = np.mean(diffs)
        std_d = np.std(diffs)
        adaptive_thresh = max(threshold, mean_d + 2.5 * std_d)
    else:
        adaptive_thresh = threshold

    cut_indices = []
    for i in range(1, len(diffs)):
        if diffs[i] > adaptive_thresh:
            if not cut_indices or (i - cut_indices[-1]) >= min_segment_frames:
                cut_indices.append(i)

    boundaries = []
    prev_start = 0
    for cut_idx in cut_indices:
        if cut_idx - prev_start >= min_segment_frames:
            boundaries.append((prev_start, cut_idx - 1))
            prev_start = cut_idx
    if len(all_frames) - prev_start >= min_segment_frames:
        boundaries.append((prev_start, len(all_frames) - 1))

    return boundaries, all_frames, fps, total_frames

"""Object detector with text grounding and hand-aware scoring.

Major improvements for accuracy:
  - Expanded alias groups covering common YOLO misclassifications
  - Multi-pass detection strategy (class-filtered → all-class → hand-vicinity)
  - Lower grounding floor to prevent over-rejection
  - Longer class lock for tracking stability
  - Smarter hand-vicinity fallback with larger search region
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class ObjectDetectionResult:
    detected: bool
    object_bbox: Optional[List[float]] = None
    object_label: Optional[str] = None
    detection_confidence: float = 0.0
    grounding_score: float = 0.0
    center: Optional[Tuple[float, float]] = None
    area: float = 0.0


# ── Alias groups: YOLO frequently confuses items within these groups ──────────
ALIAS_GROUPS = [
    {"hot dog", "hotdog", "frankfurter", "sausage", "wiener", "sandwich"},
    {"cell phone", "mobile phone", "smartphone", "phone", "remote"},
    {"couch", "sofa"},
    {"cup", "mug", "glass", "bowl"},
    {"motorbike", "motorcycle"},
    {"aeroplane", "airplane"},
    {"bottle", "vase"},
    {"knife", "scissors"},
    {"spoon", "fork"},
    {"banana", "carrot"},
    {"apple", "orange"},
    {"pizza", "cake"},
    {"donut", "bagel"},
    {"laptop", "keyboard", "mouse"},
    {"tv", "monitor"},
    {"backpack", "handbag", "suitcase"},
    {"toothbrush", "hair drier"},
    {"teddy bear", "stuffed animal"},
]

# ── Extra soft aliases: query terms that should match YOLO labels ─────────────
SOFT_ALIASES = {
    "ketchup": {"bottle"},
    "mustard": {"bottle"},
    "sauce": {"bottle", "cup"},
    "condiment": {"bottle"},
    "tea bag": {"cup", "bowl"},
    "teabag": {"cup", "bowl"},
    "bread": {"sandwich", "cake"},
    "bun": {"sandwich", "cake", "donut"},
    "plate": {"bowl", "dining table"},
    "pan": {"bowl", "oven"},
    "pot": {"bowl", "vase"},
    "container": {"bowl", "cup", "bottle"},
    "box": {"suitcase", "book", "laptop"},
    "lid": {"frisbee", "bowl"},
    "wrapper": {"book", "cell phone"},
    "towel": {"book"},
    "cloth": {"book", "tie"},
    "onion": {"apple", "orange", "sports ball"},
    "tomato": {"apple", "orange", "sports ball"},
    "potato": {"apple", "orange", "sports ball"},
    "egg": {"sports ball", "apple"},
    "ingredient": {"bowl", "cup"},
    "food": {"sandwich", "pizza", "cake", "hot dog", "bowl"},
}


def _normalize_compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower().strip())


def _expand_aliases(term: str) -> set[str]:
    """Expand a term to known aliases (for query-label matching)."""
    base = term.lower().strip()
    compact = _normalize_compact(base)
    expanded = {base}

    for group in ALIAS_GROUPS:
        compact_group = {_normalize_compact(item) for item in group}
        if base in group or compact in compact_group:
            expanded.update(group)

    # Also include soft aliases
    if base in SOFT_ALIASES:
        expanded.update(SOFT_ALIASES[base])

    return expanded


def text_similarity(a: str, b: str) -> float:
    """Compute robust string similarity in [0,1] for object grounding."""
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()
    if not a_norm or not b_norm:
        return 0.0

    # Fast path for exact and compact-equal forms (e.g. hotdog vs hot dog).
    if a_norm == b_norm:
        return 1.0
    if _normalize_compact(a_norm) == _normalize_compact(b_norm):
        return 1.0

    # Compare across alias-expanded candidates and keep the best score.
    best = 0.0
    a_expanded = _expand_aliases(a_norm)
    b_expanded = _expand_aliases(b_norm)

    for a_term in a_expanded:
        for b_term in b_expanded:
            if a_term == b_term:
                return 1.0
            if _normalize_compact(a_term) == _normalize_compact(b_term):
                return 1.0

            if a_term in b_term or b_term in a_term:
                best = max(best, 0.95)

            a_tokens = set(re.findall(r"[a-zA-Z]+", a_term))
            b_tokens = set(re.findall(r"[a-zA-Z]+", b_term))
            if a_tokens and b_tokens:
                intersection = len(a_tokens & b_tokens)
                union = len(a_tokens | b_tokens)
                jaccard = intersection / union
                best = max(best, jaccard)

            seq_ratio = difflib.SequenceMatcher(None, a_term, b_term).ratio()
            best = max(best, seq_ratio)

    # Bonus: if either term is a soft-alias of the other, boost to 0.85 minimum
    if a_norm in SOFT_ALIASES:
        if b_norm in SOFT_ALIASES[a_norm]:
            best = max(best, 0.85)
    if b_norm in SOFT_ALIASES:
        if a_norm in SOFT_ALIASES[b_norm]:
            best = max(best, 0.85)

    return float(best)


def _label_names(model_names) -> List[str]:
    if isinstance(model_names, dict):
        return [str(model_names[idx]) for idx in sorted(model_names.keys())]
    return [str(name) for name in model_names]


def _label_by_id(model_names, idx: int) -> str:
    if isinstance(model_names, dict):
        return str(model_names[idx])
    return str(model_names[idx])


def _resolve_candidate_class_ids(model_names, query_object: str, threshold: float = 0.55) -> List[int]:
    """Resolve likely class ids for the query to optionally restrict YOLO inference.

    Lowered threshold from 0.72 to 0.55 to catch more alias/soft-alias matches.
    """
    ids: List[int] = []
    if isinstance(model_names, dict):
        iterable = model_names.items()
    else:
        iterable = enumerate(model_names)

    for idx, label in iterable:
        sim = text_similarity(query_object, str(label))
        if sim >= threshold:
            ids.append(int(idx))
    return ids


class ObjectDetector:
    """YOLOv8n-based detector with query grounding and hand-proximity prioritization.

    Improved for egocentric video accuracy:
      - Lower grounding floor (0.28 vs 0.45) to avoid rejecting valid detections
      - Multi-pass detection: class-filtered → broader filter → unfiltered → hand fallback
      - Longer class lock (24 frames) for tracking stability
      - Larger hand-vicinity search region for PICK-like actions
      - Smarter fallback: uses grip_bbox or larger wrist region
    """

    def __init__(
        self,
        query_object: str,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.15,
    ) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise ImportError(
                "ultralytics is required for ObjectDetector. Install with: pip install ultralytics"
            ) from exc

        self.query_object = (query_object or "object").strip().lower()
        self.conf_threshold = conf_threshold
        self.model = YOLO(model_path)
        self.target_class_ids = _resolve_candidate_class_ids(self.model.names, self.query_object)
        self.min_grounding_score = 0.28     # lowered from 0.45
        self.lock_duration_frames = 24      # increased from 12
        self.locked_class_id: Optional[int] = None
        self.lock_remaining_frames = 0
        self.pick_roi_scale = 3.0           # slightly larger ROI

        # Track the best-ever detection for recovery
        self._best_ever_class_id: Optional[int] = None
        self._best_ever_grounding: float = 0.0

    def _tick_class_lock(self) -> None:
        if self.lock_remaining_frames > 0:
            self.lock_remaining_frames -= 1
            if self.lock_remaining_frames <= 0:
                self.locked_class_id = None
                self.lock_remaining_frames = 0

    def _refresh_class_lock(self, class_id: int, grounding_score: float) -> None:
        # Refresh lock when semantic match is reasonable (lowered from 0.60)
        if grounding_score >= 0.40:
            self.locked_class_id = class_id
            self.lock_remaining_frames = self.lock_duration_frames
            # Track best-ever for recovery
            if grounding_score > self._best_ever_grounding:
                self._best_ever_class_id = class_id
                self._best_ever_grounding = grounding_score
        else:
            self._tick_class_lock()

    def _compute_hand_roi(self, frame_shape, hand_result) -> Optional[Tuple[int, int, int, int]]:
        """Build a larger search ROI around hand bbox for PICK-like actions."""
        if hand_result is None or not getattr(hand_result, "detected", False):
            return None

        # Prefer grip_bbox (tighter around fingertips) if available
        grip_bbox = getattr(hand_result, "grip_bbox", None)
        hand_bbox = getattr(hand_result, "hand_bbox", None)
        ref_bbox = grip_bbox if grip_bbox else hand_bbox
        if ref_bbox is None:
            return None

        h, w = frame_shape[:2]
        hx1, hy1, hx2, hy2 = [float(v) for v in ref_bbox]
        cx = (hx1 + hx2) / 2.0
        cy = (hy1 + hy2) / 2.0
        bw = max(1.0, hx2 - hx1)
        bh = max(1.0, hy2 - hy1)

        roi_w = bw * self.pick_roi_scale
        roi_h = bh * self.pick_roi_scale

        x1 = int(max(0, cx - roi_w / 2.0))
        y1 = int(max(0, cy - roi_h / 2.0))
        x2 = int(min(w, cx + roi_w / 2.0))
        y2 = int(min(h, cy + roi_h / 2.0))

        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2, y2)

    def _score_detection(
        self,
        label: str,
        confidence: float,
        center: Tuple[float, float],
        hand_wrist: Optional[np.ndarray],
        frame_diag: float = 800.0,
    ) -> Tuple[float, float]:
        label_score = text_similarity(self.query_object, label)

        if hand_wrist is not None:
            distance = np.linalg.norm(np.array(center, dtype=float) - hand_wrist)
            # Normalise by frame diagonal for resolution-independence
            norm_dist = distance / max(frame_diag, 1.0)
            proximity_score = max(0.0, 1.0 - norm_dist * 3.0)
        else:
            proximity_score = 0.5

        # Weighted: grounding most important, then hand proximity, then raw confidence
        total_score = 0.55 * label_score + 0.25 * proximity_score + 0.20 * confidence
        return total_score, label_score

    def _fallback_from_hand(self, frame_shape, hand_result) -> Optional[ObjectDetectionResult]:
        """Create a larger hand-vicinity detection when YOLO can't find the query object."""
        if hand_result is None or not getattr(hand_result, "detected", False):
            return None

        # Prefer fingertip center for better contact accuracy
        ftip = getattr(hand_result, "fingertip_center", None)
        wrist = getattr(hand_result, "wrist_pos", None)
        ref_point = ftip if ftip else wrist
        if ref_point is None:
            return None

        h, w = frame_shape[:2]
        cx, cy = int(ref_point[0]), int(ref_point[1])
        # Larger fallback region (was 60, now 100)
        half = 100

        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(w - 1, cx + half)
        y2 = min(h - 1, cy + half)

        area = float(max(1, x2 - x1) * max(1, y2 - y1))
        center = (float((x1 + x2) / 2), float((y1 + y2) / 2))

        return ObjectDetectionResult(
            detected=True,
            object_bbox=[float(x1), float(y1), float(x2), float(y2)],
            object_label=self.query_object,
            detection_confidence=0.18,
            grounding_score=0.30,   # raised from 0.2 so it doesn't get immediately rejected
            center=center,
            area=area,
        )

    def detect(
        self,
        frame: np.ndarray,
        hand_result=None,
        action_category: Optional[str] = None,
    ) -> ObjectDetectionResult:
        """Detect the query-relevant object on a frame.

        Multi-pass strategy:
          1. Class-filtered detection (fastest, most precise)
          2. If empty + lock active → retry with target candidates
          3. If still empty → unfiltered detection (score by grounding)
          4. If still empty → hand-vicinity fallback
        """
        if frame is None or frame.size == 0:
            return ObjectDetectionResult(detected=False)

        frame_h, frame_w = frame.shape[:2]
        frame_diag = float(np.sqrt(frame_h**2 + frame_w**2))

        hand_wrist = None
        if hand_result is not None and getattr(hand_result, "detected", False):
            # Prefer fingertip center for better positional accuracy
            ftip = getattr(hand_result, "fingertip_center", None)
            wrist = getattr(hand_result, "wrist_pos", None)
            ref = ftip if ftip else wrist
            if ref is not None:
                hand_wrist = np.array([ref[0], ref[1]], dtype=float)

        action_category_u = (action_category or "").upper()
        is_pick_like = action_category_u in {"PICK", "GRAB", "TAKE", "PLACE", "PUT"}

        # --- Determine class filter ---
        lock_active = self.lock_remaining_frames > 0 and self.locked_class_id is not None
        if lock_active:
            class_filter = [self.locked_class_id]
        elif self.target_class_ids:
            class_filter = self.target_class_ids
        else:
            class_filter = None

        # --- PASS 1: ROI detection for pick-like actions ---
        det_frame = frame
        frame_offset_x = 0
        frame_offset_y = 0
        roi_used = False
        if is_pick_like:
            roi = self._compute_hand_roi(frame.shape, hand_result)
            if roi is not None:
                rx1, ry1, rx2, ry2 = roi
                crop = frame[ry1:ry2, rx1:rx2]
                if crop.size > 0:
                    det_frame = crop
                    frame_offset_x = rx1
                    frame_offset_y = ry1
                    roi_used = True

        results = self.model(det_frame, conf=self.conf_threshold, classes=class_filter, verbose=False)

        # If ROI was used but empty, retry on full frame
        if roi_used and (not results or len(results[0].boxes) == 0):
            det_frame = frame
            frame_offset_x = 0
            frame_offset_y = 0
            roi_used = False
            results = self.model(det_frame, conf=self.conf_threshold, classes=class_filter, verbose=False)

        # --- PASS 2: If class-lock was too strict, retry with target candidates ---
        if class_filter and (not results or len(results[0].boxes) == 0):
            if lock_active and self.target_class_ids:
                det_frame = frame
                frame_offset_x = 0
                frame_offset_y = 0
                results = self.model(
                    det_frame,
                    conf=self.conf_threshold,
                    classes=self.target_class_ids,
                    verbose=False,
                )

        # --- PASS 3: If filtered still empty, try UNFILTERED and pick by grounding ---
        if class_filter and (not results or len(results[0].boxes) == 0):
            det_frame = frame
            frame_offset_x = 0
            frame_offset_y = 0
            results = self.model(det_frame, conf=self.conf_threshold, verbose=False)

        # --- PASS 4: Also try with best-ever class if known ---
        if (not results or len(results[0].boxes) == 0) and self._best_ever_class_id is not None:
            det_frame = frame
            frame_offset_x = 0
            frame_offset_y = 0
            results = self.model(
                det_frame, conf=self.conf_threshold,
                classes=[self._best_ever_class_id], verbose=False,
            )

        # --- Final fallback: hand-vicinity ---
        if not results or len(results[0].boxes) == 0:
            self._tick_class_lock()
            fallback = self._fallback_from_hand(frame.shape, hand_result)
            return fallback if fallback is not None else ObjectDetectionResult(detected=False)

        boxes = results[0].boxes
        names = self.model.names

        best = None
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().tolist()
            x1 += frame_offset_x
            y1 += frame_offset_y
            x2 += frame_offset_x
            y2 += frame_offset_y
            conf = float(boxes.conf[i])
            class_id = int(boxes.cls[i])
            label = _label_by_id(names, class_id)

            cx = float((x1 + x2) / 2.0)
            cy = float((y1 + y2) / 2.0)
            area = float(max(1.0, (x2 - x1) * (y2 - y1)))
            hand_distance = (
                float(np.linalg.norm(np.array([cx, cy], dtype=float) - hand_wrist))
                if hand_wrist is not None
                else None
            )

            score, grounding = self._score_detection(
                label=label,
                confidence=conf,
                center=(cx, cy),
                hand_wrist=hand_wrist,
                frame_diag=frame_diag,
            )

            candidate = {
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "label": str(label),
                "conf": conf,
                "grounding": grounding,
                "center": (cx, cy),
                "area": area,
                "hand_distance": hand_distance,
                "class_id": class_id,
                "score": score,
            }

            if best is None or candidate["score"] > best["score"]:
                best = candidate

        if best is None:
            self._tick_class_lock()
            fallback = self._fallback_from_hand(frame.shape, hand_result)
            return fallback if fallback is not None else ObjectDetectionResult(detected=False)

        # If grounding is very weak AND there's a hand nearby, use hand fallback
        # but only if grounding is truly terrible (lowered threshold)
        if best["grounding"] < self.min_grounding_score and hand_wrist is not None:
            # Still use the detection if it's close to hand — proximity trumps grounding
            if best.get("hand_distance") is not None and best["hand_distance"] < 0.25 * frame_diag:
                pass  # keep the detection — it's near the hand
            else:
                self._tick_class_lock()
                fallback = self._fallback_from_hand(frame.shape, hand_result)
                if fallback is not None:
                    return fallback

        # If object is VERY far from hand and grounding is not strong, prefer fallback
        if (
            hand_wrist is not None
            and best.get("hand_distance") is not None
            and best["hand_distance"] > (0.5 * frame_diag)
            and best["grounding"] < 0.7
        ):
            self._tick_class_lock()
            fallback = self._fallback_from_hand(frame.shape, hand_result)
            if fallback is not None:
                return fallback

        self._refresh_class_lock(best["class_id"], best["grounding"])

        return ObjectDetectionResult(
            detected=True,
            object_bbox=best["bbox"],
            object_label=best["label"],
            detection_confidence=best["conf"],
            grounding_score=best["grounding"],
            center=best["center"],
            area=best["area"],
        )

    def draw(self, frame: np.ndarray, result: ObjectDetectionResult) -> np.ndarray:
        """Draw object box and label."""
        if not result.detected:
            return frame

        out = frame.copy()
        x1, y1, x2, y2 = [int(v) for v in result.object_bbox]
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 80, 255), 2)

        label = (
            f"{result.object_label} conf={result.detection_confidence:.2f} "
            f"ground={result.grounding_score:.2f}"
        )
        cv2.putText(
            out,
            label,
            (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 80, 255),
            1,
        )
        return out


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "cup"
    detector = ObjectDetector(query)

    cap = cv2.VideoCapture(0)
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        result = detector.detect(frame)
        vis = detector.draw(frame, result)
        cv2.imshow(f"FIBA AI - Object Detector ({query})", vis)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

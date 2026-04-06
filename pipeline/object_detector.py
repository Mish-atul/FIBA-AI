"""Object detector with text grounding and hand-aware scoring."""

from __future__ import annotations

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


def text_similarity(a: str, b: str) -> float:
    """Compute lightweight token overlap similarity in [0,1]."""
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()

    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    if a_norm in b_norm or b_norm in a_norm:
        return 0.95

    a_tokens = set(re.findall(r"[a-zA-Z]+", a_norm))
    b_tokens = set(re.findall(r"[a-zA-Z]+", b_norm))
    if not a_tokens or not b_tokens:
        return 0.0

    intersection = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return intersection / union


class ObjectDetector:
    """YOLOv8n-based detector with query grounding and hand-proximity prioritization."""

    def __init__(
        self,
        query_object: str,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.25,
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

    def _score_detection(
        self,
        label: str,
        confidence: float,
        center: Tuple[float, float],
        hand_wrist: Optional[np.ndarray],
    ) -> Tuple[float, float]:
        label_score = text_similarity(self.query_object, label)

        if hand_wrist is not None:
            distance = np.linalg.norm(np.array(center, dtype=float) - hand_wrist)
            proximity_score = 1.0 / (1.0 + (distance / 100.0))
        else:
            proximity_score = 0.5

        # Prioritize query grounding, then hand-object relation.
        total_score = 0.6 * label_score + 0.3 * proximity_score + 0.1 * confidence
        return total_score, label_score

    def _fallback_from_hand(self, frame_shape, hand_result) -> Optional[ObjectDetectionResult]:
        if hand_result is None or not getattr(hand_result, "detected", False):
            return None
        wrist = getattr(hand_result, "wrist_pos", None)
        if wrist is None:
            return None

        h, w = frame_shape[:2]
        cx, cy = int(wrist[0]), int(wrist[1])
        half = 60

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
            detection_confidence=0.12,
            grounding_score=0.2,
            center=center,
            area=area,
        )

    def detect(self, frame: np.ndarray, hand_result=None) -> ObjectDetectionResult:
        """Detect the query-relevant object on a frame."""
        if frame is None or frame.size == 0:
            return ObjectDetectionResult(detected=False)

        hand_wrist = None
        if hand_result is not None and getattr(hand_result, "detected", False):
            wrist = getattr(hand_result, "wrist_pos", None)
            if wrist is not None:
                hand_wrist = np.array([wrist[0], wrist[1]], dtype=float)

        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        if not results or len(results[0].boxes) == 0:
            fallback = self._fallback_from_hand(frame.shape, hand_result)
            return fallback if fallback is not None else ObjectDetectionResult(detected=False)

        boxes = results[0].boxes
        names = self.model.names

        best = None
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().tolist()
            conf = float(boxes.conf[i])
            class_id = int(boxes.cls[i])
            label = names[class_id] if isinstance(names, dict) else names[class_id]

            cx = float((x1 + x2) / 2.0)
            cy = float((y1 + y2) / 2.0)
            area = float(max(1.0, (x2 - x1) * (y2 - y1)))

            score, grounding = self._score_detection(
                label=label,
                confidence=conf,
                center=(cx, cy),
                hand_wrist=hand_wrist,
            )

            candidate = {
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "label": str(label),
                "conf": conf,
                "grounding": grounding,
                "center": (cx, cy),
                "area": area,
                "score": score,
            }

            if best is None or candidate["score"] > best["score"]:
                best = candidate

        if best is None:
            fallback = self._fallback_from_hand(frame.shape, hand_result)
            return fallback if fallback is not None else ObjectDetectionResult(detected=False)

        # If grounding is extremely weak, use wrist-local fallback to avoid random object drift.
        if best["grounding"] < 0.1 and hand_wrist is not None:
            fallback = self._fallback_from_hand(frame.shape, hand_result)
            if fallback is not None:
                return fallback

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

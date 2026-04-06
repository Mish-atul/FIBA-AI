"""Hand detector module using MediaPipe Hands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - runtime dependency
    mp = None


@dataclass
class HandDetectionResult:
    detected: bool
    hand_bbox: Optional[List[float]] = None
    landmarks: Optional[List[List[float]]] = None
    handedness: Optional[str] = None
    confidence: float = 0.0
    wrist_pos: Optional[Tuple[float, float]] = None
    index_tip: Optional[Tuple[float, float]] = None
    thumb_tip: Optional[Tuple[float, float]] = None


class HandDetector:
    """Real-time hand detector with 21 keypoints and wrist/index/thumb helpers."""

    def __init__(
        self,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
        max_num_hands: int = 2,
        input_size: Tuple[int, int] = (640, 480),
    ) -> None:
        if mp is None:
            raise ImportError(
                "mediapipe is required for HandDetector. Install with: pip install mediapipe"
            )

        self.input_size = input_size
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, frame: np.ndarray) -> HandDetectionResult:
        """Detect the strongest hand in a BGR frame."""
        if frame is None or frame.size == 0:
            return HandDetectionResult(detected=False)

        frame_h, frame_w = frame.shape[:2]
        infer_w, infer_h = self.input_size

        resized = cv2.resize(frame, (infer_w, infer_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks or not results.multi_handedness:
            return HandDetectionResult(detected=False)

        best_idx = 0
        best_score = -1.0
        for idx, hand_info in enumerate(results.multi_handedness):
            score = hand_info.classification[0].score
            if score > best_score:
                best_idx = idx
                best_score = score

        hand_landmarks = results.multi_hand_landmarks[best_idx]
        hand_meta = results.multi_handedness[best_idx].classification[0]

        x_coords: List[int] = []
        y_coords: List[int] = []
        landmarks: List[List[float]] = []

        for landmark in hand_landmarks.landmark:
            x = int(landmark.x * frame_w)
            y = int(landmark.y * frame_h)
            landmarks.append([x, y, float(landmark.z)])
            x_coords.append(x)
            y_coords.append(y)

        pad = 20
        x1 = max(0, min(x_coords) - pad)
        y1 = max(0, min(y_coords) - pad)
        x2 = min(frame_w - 1, max(x_coords) + pad)
        y2 = min(frame_h - 1, max(y_coords) + pad)

        wrist = (landmarks[0][0], landmarks[0][1])
        index_tip = (landmarks[8][0], landmarks[8][1])
        thumb_tip = (landmarks[4][0], landmarks[4][1])

        return HandDetectionResult(
            detected=True,
            hand_bbox=[x1, y1, x2, y2],
            landmarks=landmarks,
            handedness=hand_meta.label,
            confidence=float(hand_meta.score),
            wrist_pos=wrist,
            index_tip=index_tip,
            thumb_tip=thumb_tip,
        )

    def draw(self, frame: np.ndarray, result: HandDetectionResult) -> np.ndarray:
        """Draw hand bbox and key reference points."""
        if not result.detected:
            return frame

        out = frame.copy()
        x1, y1, x2, y2 = [int(v) for v in result.hand_bbox]
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 220, 0), 2)
        cv2.putText(
            out,
            f"{result.handedness} {result.confidence:.2f}",
            (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 220, 0),
            1,
        )

        if result.wrist_pos is not None:
            cv2.circle(out, (int(result.wrist_pos[0]), int(result.wrist_pos[1])), 4, (255, 0, 0), -1)
        if result.index_tip is not None:
            cv2.circle(out, (int(result.index_tip[0]), int(result.index_tip[1])), 4, (0, 255, 255), -1)
        if result.thumb_tip is not None:
            cv2.circle(out, (int(result.thumb_tip[0]), int(result.thumb_tip[1])), 4, (0, 128, 255), -1)

        return out

    def release(self) -> None:
        """Release MediaPipe resources."""
        self.hands.close()


if __name__ == "__main__":
    detector = HandDetector()
    cap = cv2.VideoCapture(0)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        hand = detector.detect(frame)
        vis = detector.draw(frame, hand)
        cv2.imshow("FIBA AI - Hand Detector", vis)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    detector.release()
    cv2.destroyAllWindows()

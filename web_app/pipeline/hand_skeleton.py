"""
Hand Skeleton Visualizer — 21-joint MediaPipe with per-finger color coding.

Inspired by the HATREC paper (IEEE Access 2025, Fig. 3):
  - Each finger gets a distinct color
  - Joints drawn as circles, connections as lines
  - Fingertip trajectories drawn over time
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
import base64

# MediaPipe hand landmark connections
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring finger
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm connections
    (5, 9), (9, 13), (13, 17),
]

# BGR colors for each finger
FINGER_COLORS = {
    "wrist":  (255, 255, 255),   # White
    "thumb":  (60, 60, 255),     # Red
    "index":  (60, 255, 60),     # Green
    "middle": (255, 120, 60),    # Blue
    "ring":   (0, 255, 255),     # Yellow
    "pinky":  (255, 60, 255),    # Magenta
    "palm":   (200, 200, 200),   # Light gray
}

# Map joint IDs to finger names
def _joint_finger(joint_id: int) -> str:
    if joint_id == 0:
        return "wrist"
    elif 1 <= joint_id <= 4:
        return "thumb"
    elif 5 <= joint_id <= 8:
        return "index"
    elif 9 <= joint_id <= 12:
        return "middle"
    elif 13 <= joint_id <= 16:
        return "ring"
    elif 17 <= joint_id <= 20:
        return "pinky"
    return "wrist"


def _connection_color(j1: int, j2: int) -> Tuple[int, int, int]:
    """Get color for a connection based on which finger it belongs to."""
    # Palm connections
    if (j1, j2) in [(5, 9), (9, 13), (13, 17)] or (j2, j1) in [(5, 9), (9, 13), (13, 17)]:
        return FINGER_COLORS["palm"]
    # Wrist-to-finger-base connections
    if j1 == 0 or j2 == 0:
        other = j2 if j1 == 0 else j1
        return FINGER_COLORS[_joint_finger(other)]
    # Same finger
    return FINGER_COLORS[_joint_finger(j1)]


def draw_hand_skeleton(
    frame: np.ndarray,
    landmarks: List[List[float]],
    joint_radius: int = 4,
    line_thickness: int = 2,
    alpha: float = 0.85,
) -> np.ndarray:
    """Draw 21-joint hand skeleton with per-finger color coding.

    Args:
        frame: BGR image
        landmarks: list of 21 [x, y, z] coordinates (pixel space)
        joint_radius: radius of joint circles
        line_thickness: thickness of connection lines
        alpha: overlay opacity
    """
    if landmarks is None or len(landmarks) < 21:
        return frame

    overlay = frame.copy()

    # Draw connections
    for j1, j2 in HAND_CONNECTIONS:
        if j1 < len(landmarks) and j2 < len(landmarks):
            pt1 = (int(landmarks[j1][0]), int(landmarks[j1][1]))
            pt2 = (int(landmarks[j2][0]), int(landmarks[j2][1]))
            color = _connection_color(j1, j2)
            cv2.line(overlay, pt1, pt2, color, line_thickness, cv2.LINE_AA)

    # Draw joints
    for i, lm in enumerate(landmarks):
        pt = (int(lm[0]), int(lm[1]))
        finger = _joint_finger(i)
        color = FINGER_COLORS[finger]
        # Fingertips get larger circles
        r = joint_radius + 2 if i in [4, 8, 12, 16, 20] else joint_radius
        cv2.circle(overlay, pt, r, color, -1, cv2.LINE_AA)
        cv2.circle(overlay, pt, r, (40, 40, 40), 1, cv2.LINE_AA)  # dark border

    result = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    return result


def draw_hand_skeleton_on_keyframe(
    frame: np.ndarray,
    hand_result,
) -> np.ndarray:
    """Draw hand skeleton on a key frame using HandDetectionResult."""
    if hand_result is None or not getattr(hand_result, "detected", False):
        return frame
    landmarks = getattr(hand_result, "landmarks", None)
    if landmarks is None or len(landmarks) < 21:
        return frame
    return draw_hand_skeleton(frame, landmarks)


def draw_finger_trajectories(
    frame_shape: Tuple[int, int, int],
    landmark_history: List[Optional[List[List[float]]]],
    fingertip_ids: List[int] = None,
    trail_length: int = 60,
) -> np.ndarray:
    """Draw fingertip trajectories over time.

    Args:
        frame_shape: (h, w, c) of output canvas
        landmark_history: list of per-frame landmarks (21x3 each, or None)
        fingertip_ids: which joints to trace (default: all 5 fingertips)
        trail_length: max number of recent frames to show per finger
    """
    if fingertip_ids is None:
        fingertip_ids = [4, 8, 12, 16, 20]

    canvas = np.zeros(frame_shape, dtype=np.uint8)

    # Header
    cv2.putText(canvas, "Finger Trajectories", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    finger_names = {4: "thumb", 8: "index", 12: "middle", 16: "ring", 20: "pinky"}

    for tip_id in fingertip_ids:
        finger = finger_names.get(tip_id, "unknown")
        color = FINGER_COLORS.get(finger, (255, 255, 255))

        # Collect trajectory points
        points = []
        start = max(0, len(landmark_history) - trail_length)
        for i in range(start, len(landmark_history)):
            lm = landmark_history[i]
            if lm is not None and len(lm) > tip_id:
                pt = (int(lm[tip_id][0]), int(lm[tip_id][1]))
                points.append(pt)

        # Draw trajectory as connected line with fading alpha
        for j in range(1, len(points)):
            alpha = int(255 * (j / len(points)))
            line_color = (
                min(255, color[0] * alpha // 255),
                min(255, color[1] * alpha // 255),
                min(255, color[2] * alpha // 255),
            )
            cv2.line(canvas, points[j - 1], points[j], line_color, 2, cv2.LINE_AA)

        # Draw current position
        if points:
            cv2.circle(canvas, points[-1], 6, color, -1, cv2.LINE_AA)

    # Legend
    y_legend = frame_shape[0] - 20
    x = 10
    for tip_id in fingertip_ids:
        finger = finger_names.get(tip_id, "?")
        color = FINGER_COLORS.get(finger, (255, 255, 255))
        cv2.circle(canvas, (x, y_legend), 6, color, -1)
        cv2.putText(canvas, finger.capitalize(), (x + 12, y_legend + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        x += 90

    return canvas


def encode_frame_b64(frame: np.ndarray, quality: int = 85) -> str:
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode("utf-8")

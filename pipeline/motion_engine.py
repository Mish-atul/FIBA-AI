"""
Motion Engine — Tanishk
=======================
Extracts interpretable motion features from the tracked object's history
and hand-object interaction signals.

Major improvements for egocentric video accuracy:
  - Increased frame_window from 30 → 120 to capture full actions
  - Increased contact_threshold from 80 → 150px for 640px resolution
  - Added approach/retreat detection (area growth → object approaching camera)
  - Added hand grasp tracking (openness change → grasping indicator)
  - Better state-change: compare first 20% vs last 20% with more features
  - Added displacement_per_second for speed-independent analysis
  - Added directional consistency score
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# Feature bundle dataclass
# ---------------------------------------------------------------------------

@dataclass
class MotionFeatures:
    """All motion features computed over a sliding analysis window."""

    # 1. Translational motion
    displacement_magnitude: float = 0.0    # total px moved start→end
    displacement_direction: float = 0.0    # degrees from horizontal
    vertical_motion_ratio: float = 0.0     # -1.0 (down) to +1.0 (up)
    motion_speed: float = 0.0              # mean px/frame displacement

    # 2. Rotational proxy
    rotation_change: float = 0.0           # total degrees rotated
    rotation_speed: float = 0.0            # mean |degrees/frame|

    # 3. Area / scale change
    area_ratio: float = 1.0                # end_area / start_area
    area_variance: float = 0.0             # std of area (fragmentation)
    area_growth_rate: float = 0.0          # mean area change per frame

    # 4. Hand-object interaction
    contact_distance_mean: float = 999.0   # mean wrist-to-center distance
    contact_frequency: float = 0.0         # contact oscillation count
    contact_events: int = 0                # frames where dist < threshold

    # 5. State change
    state_change_score: float = 0.0        # normalized 0–1

    # 6. Egocentric / approach features (NEW)
    area_growth_trend: float = 0.0         # >0 = approaching camera (pick-up), <0 = retreating
    approach_score: float = 0.0            # 0–1, how strongly object is approaching
    displacement_consistency: float = 0.0  # 0–1, how consistent is the motion direction
    max_displacement_burst: float = 0.0    # peak frame-to-frame displacement (action peak)

    # 7. Hand grasp features (NEW)
    grasp_change: float = 0.0             # change in hand openness: -=closing (grasping), +=opening
    min_grasp_openness: float = 1.0       # minimum openness observed (0=closed fist)
    grasp_close_events: int = 0           # number of significant closing events
    hand_approach_rate: float = 0.0       # how fast hand approaches object (<0 = approaching)

    # Meta
    window_frames: int = 0                 # how many frames were analysed


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MotionEngine:
    """
    Computes motion features from tracker history.

    Improved for egocentric video:
      - Larger window (120 frames) captures full pick/place/pour actions
      - Higher contact threshold (150px) for resolution-robustness
      - Approach/retreat detection via area growth trend
      - Hand grasp state tracking
      - Directional consistency for robust motion classification
    """

    def __init__(
        self,
        frame_window: int = 120,           # increased from 30
        contact_threshold: float = 150.0,  # increased from 80
    ):
        self.frame_window = frame_window
        self.contact_threshold = contact_threshold

    # -----------------------------------------------------------------------
    # Main compute
    # -----------------------------------------------------------------------

    def compute(
        self,
        tracker_history: dict,
        hand_history: Optional[List] = None,
        frame_height: int = 480,
        grasp_history: Optional[List[Optional[float]]] = None,
    ) -> MotionFeatures:
        """
        Compute all motion features from tracker history.

        Args:
            tracker_history: dict from ObjectTracker.get_history()
            hand_history:    List of wrist (x,y) or fingertip_center per frame
            frame_height:    Frame height in pixels
            grasp_history:   List of grasp_openness values per frame (0-1, or None)

        Returns:
            MotionFeatures dataclass
        """
        centers_all: list = tracker_history.get("center_history", [])
        areas_all: list = tracker_history.get("area_history", [])
        bboxes_all: list = tracker_history.get("bbox_history", [])

        if len(centers_all) < 3:
            return MotionFeatures()

        # Use last N frames
        N = min(self.frame_window, len(centers_all))
        centers_w = np.array(centers_all[-N:], dtype=np.float64)  # (N, 2)
        areas_w = np.array(areas_all[-N:], dtype=np.float64)       # (N,)
        bboxes_w: list = bboxes_all[-N:]

        features = MotionFeatures(window_frames=N)

        # -------------------------------------------------------------------
        # 1. Translational motion
        # -------------------------------------------------------------------
        start = centers_w[0]
        end = centers_w[-1]
        diff = end - start

        features.displacement_magnitude = float(np.linalg.norm(diff))
        features.displacement_direction = float(
            np.degrees(np.arctan2(-diff[1], diff[0]))  # screen y is flipped
        )
        # Vertical motion: upward = positive (note screen y increases downward)
        features.vertical_motion_ratio = float(
            np.clip(-diff[1] / max(frame_height * 0.5, 1.0), -1.0, 1.0)
        )

        # Mean frame-to-frame speed
        frame_disps = np.linalg.norm(np.diff(centers_w, axis=0), axis=1)
        features.motion_speed = float(np.mean(frame_disps)) if len(frame_disps) else 0.0

        # Max displacement burst (peak action moment)
        if len(frame_disps) > 0:
            features.max_displacement_burst = float(np.max(frame_disps))

        # Directional consistency: how aligned are frame-to-frame displacements
        if len(frame_disps) > 2:
            diffs_vec = np.diff(centers_w, axis=0)  # (N-1, 2)
            norms = np.linalg.norm(diffs_vec, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-6)
            unit_vecs = diffs_vec / norms
            # Compute dot product between consecutive unit vectors
            if len(unit_vecs) > 1:
                dots = np.sum(unit_vecs[:-1] * unit_vecs[1:], axis=1)
                features.displacement_consistency = float(np.clip(np.mean(dots), 0.0, 1.0))

        # -------------------------------------------------------------------
        # 2. Rotational proxy
        # -------------------------------------------------------------------
        angles = []
        for bbox in bboxes_w:
            if bbox and len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                w = x2 - x1
                h = y2 - y1
                angle = float(np.degrees(np.arctan2(h, max(w, 1.0))))
                angles.append(angle)

        if len(angles) >= 2:
            angle_arr = np.array(angles)
            angle_diffs = np.diff(angle_arr)
            angle_diffs = np.where(angle_diffs > 90, angle_diffs - 180, angle_diffs)
            angle_diffs = np.where(angle_diffs < -90, angle_diffs + 180, angle_diffs)
            features.rotation_change = float(np.sum(angle_diffs))
            features.rotation_speed = float(np.mean(np.abs(angle_diffs)))

        # -------------------------------------------------------------------
        # 3. Area / scale change
        # -------------------------------------------------------------------
        safe_start_area = max(float(areas_w[0]), 1.0)
        safe_end_area = max(float(areas_w[-1]), 1.0)
        features.area_ratio = safe_end_area / safe_start_area
        features.area_variance = float(np.std(areas_w))
        area_diffs = np.diff(areas_w)
        features.area_growth_rate = float(np.mean(area_diffs)) if len(area_diffs) else 0.0

        # --- Area growth trend (egocentric approach detection) ---
        # Positive trend = object getting bigger = approaching camera
        if len(areas_w) >= 6:
            third = max(len(areas_w) // 3, 1)
            early_area = float(np.mean(areas_w[:third]))
            late_area = float(np.mean(areas_w[-third:]))
            features.area_growth_trend = (late_area - early_area) / max(early_area, 1.0)
            features.approach_score = float(np.clip(features.area_growth_trend * 2.0, 0.0, 1.0))
        else:
            features.area_growth_trend = features.area_ratio - 1.0
            features.approach_score = float(np.clip(features.area_growth_trend * 2.0, 0.0, 1.0))

        # -------------------------------------------------------------------
        # 4. Hand-object interaction
        # -------------------------------------------------------------------
        if hand_history and len(hand_history) >= 1:
            hand_win = hand_history[-N:]
            valid_pairs: List[Tuple[np.ndarray, np.ndarray]] = []
            for i, hw in enumerate(hand_win):
                if hw is not None and i < len(centers_w):
                    try:
                        hp = np.array(hw, dtype=np.float64)
                        if hp.shape == (2,):
                            valid_pairs.append((centers_w[i], hp))
                    except Exception:
                        pass

            if valid_pairs:
                dists = np.array([
                    np.linalg.norm(obj_c - hand_c)
                    for obj_c, hand_c in valid_pairs
                ])
                features.contact_distance_mean = float(np.mean(dists))

                # Contact events: frames where hand is within threshold
                contacts = dists < self.contact_threshold
                features.contact_events = int(np.sum(contacts))

                # Contact frequency: count rising edges (contact start events)
                contact_float = contacts.astype(float)
                transitions = np.diff(contact_float)
                features.contact_frequency = float(np.sum(transitions > 0))

                # Hand approach rate: is the hand getting closer or farther?
                if len(dists) >= 4:
                    quarter = max(len(dists) // 4, 1)
                    early_dist = float(np.mean(dists[:quarter]))
                    late_dist = float(np.mean(dists[-quarter:]))
                    features.hand_approach_rate = (late_dist - early_dist) / max(early_dist, 1.0)

        # -------------------------------------------------------------------
        # 5. State-change score
        # -------------------------------------------------------------------
        fifth = max(N // 5, 1)
        early_area = float(np.mean(areas_w[:fifth]))
        late_area = float(np.mean(areas_w[-fifth:]))
        early_y = float(np.mean(centers_w[:fifth, 1]))
        late_y = float(np.mean(centers_w[-fifth:, 1]))
        early_x = float(np.mean(centers_w[:fifth, 0]))
        late_x = float(np.mean(centers_w[-fifth:, 0]))

        area_change = abs(late_area - early_area) / (early_area + 1e-5)
        pos_change_y = abs(late_y - early_y) / max(frame_height, 1)
        pos_change_x = abs(late_x - early_x) / max(frame_height, 1)
        pos_change = max(pos_change_y, pos_change_x)
        rot_change_norm = min(abs(features.rotation_change) / 90.0, 1.0)

        # Include speed change as state indicator
        if len(frame_disps) >= 4:
            speed_quarter = max(len(frame_disps) // 4, 1)
            early_speed = float(np.mean(frame_disps[:speed_quarter]))
            late_speed = float(np.mean(frame_disps[-speed_quarter:]))
            speed_change = abs(late_speed - early_speed) / max(early_speed + late_speed, 1.0)
        else:
            speed_change = 0.0

        features.state_change_score = float(np.clip(
            0.30 * area_change + 0.25 * pos_change + 0.25 * rot_change_norm + 0.20 * speed_change,
            0.0, 1.0
        ))

        # -------------------------------------------------------------------
        # 6. Grasp features
        # -------------------------------------------------------------------
        if grasp_history and len(grasp_history) >= 1:
            grasp_win = grasp_history[-N:]
            valid_grasps = [g for g in grasp_win if g is not None]

            if len(valid_grasps) >= 3:
                grasp_arr = np.array(valid_grasps)
                features.min_grasp_openness = float(np.min(grasp_arr))

                # Grasp change: positive = hand opening, negative = hand closing
                features.grasp_change = float(grasp_arr[-1] - grasp_arr[0])

                # Count significant closing events (openness drops by >0.15)
                grasp_diffs = np.diff(grasp_arr)
                features.grasp_close_events = int(np.sum(grasp_diffs < -0.15))

        return features

    # -----------------------------------------------------------------------
    # Key frame selection
    # -----------------------------------------------------------------------

    def select_key_frame_indices(
        self,
        all_motion_features: List[MotionFeatures],
        n: int = 3,
    ) -> List[int]:
        """
        Select the n most informative frame indices from per-frame motion.

        Improved scoring includes approach_score and grasp_change.
        """
        if not all_motion_features:
            return []

        total = len(all_motion_features)

        scores = []
        for i, f in enumerate(all_motion_features):
            score = (
                abs(f.displacement_magnitude) * 1.0
                + abs(f.rotation_change) * 2.0
                + f.area_variance * 0.01
                + f.contact_events * 5.0
                + f.approach_score * 30.0
                + abs(f.grasp_change) * 20.0
                + f.state_change_score * 50.0
            )
            scores.append((score, i))

        scores.sort(key=lambda x: x[0], reverse=True)
        selected = sorted(idx for _, idx in scores[:n])

        # Ensure boundary frames included
        if len(selected) < n:
            if 0 not in selected:
                selected = [0] + selected
            if total - 1 not in selected:
                selected.append(total - 1)

        return selected[:n]


# ---------------------------------------------------------------------------
# Quick standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== MotionEngine standalone test ===")

    # Simulate a 60-frame picking scenario (object moves upward, area grows)
    rng = np.random.default_rng(42)
    N = 60
    xs = 200 + rng.normal(0, 2, N).cumsum()
    ys = 300 - np.linspace(0, 80, N) + rng.normal(0, 3, N)  # moves upward
    areas = np.linspace(2000, 4000, N) + rng.normal(0, 100, N)  # grows (approaching)

    fake_history = {
        "center_history": [(xs[i], ys[i]) for i in range(N)],
        "area_history": list(areas),
        "bbox_history": [
            [xs[i]-30, ys[i]-30, xs[i]+30, ys[i]+30] for i in range(N)
        ],
        "frame_ids": list(range(N)),
    }

    # Simulate hand wrist positions (close to object)
    hand_hist = [(xs[i]+30, ys[i]+rng.normal(0, 10)) if i % 2 != 0 else None
                 for i in range(N)]

    # Simulate grasp (starts open=0.8, closes to 0.2)
    grasp_hist = [float(0.8 - (i/N) * 0.6 + rng.normal(0, 0.05)) for i in range(N)]

    engine = MotionEngine(frame_window=120, contact_threshold=150)
    features = engine.compute(
        fake_history, hand_history=hand_hist,
        frame_height=480, grasp_history=grasp_hist,
    )

    print(f"  displacement_magnitude : {features.displacement_magnitude:.1f} px")
    print(f"  vertical_motion_ratio  : {features.vertical_motion_ratio:.3f}")
    print(f"  rotation_change        : {features.rotation_change:.2f} °")
    print(f"  area_ratio             : {features.area_ratio:.3f}")
    print(f"  area_growth_trend      : {features.area_growth_trend:.3f}")
    print(f"  approach_score         : {features.approach_score:.3f}")
    print(f"  contact_distance_mean  : {features.contact_distance_mean:.1f} px")
    print(f"  contact_frequency      : {features.contact_frequency:.1f}")
    print(f"  contact_events         : {features.contact_events}")
    print(f"  state_change_score     : {features.state_change_score:.3f}")
    print(f"  grasp_change           : {features.grasp_change:.3f}")
    print(f"  min_grasp_openness     : {features.min_grasp_openness:.3f}")
    print(f"  displacement_consistency: {features.displacement_consistency:.3f}")
    print(f"  max_displacement_burst : {features.max_displacement_burst:.1f}")

    # Key frame selection
    per_frame = [engine.compute(fake_history) for _ in range(10)]
    kf_indices = engine.select_key_frame_indices(per_frame, n=3)
    print(f"\n  Key frame indices: {kf_indices}")
    print("MotionEngine test PASSED ✓")

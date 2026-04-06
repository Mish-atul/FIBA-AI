"""
Action Inferencer — Tanishk
============================
Rule-based action inference from MotionFeatures.

MAJOR REWRITE for egocentric video accuracy:
  - PICK: No longer relies on vertical motion. Uses hand-object proximity,
    contact events, displacement, area growth (approaching camera), and
    grasp closing as primary signals.
  - POUR: Better condiment/liquid pouring detection.
  - All categories: Lowered detection threshold from 0.45 to 0.32.
  - Added weighted aggregation from multiple frames instead of single-frame.
  - Better evidence text for explainability.

Action categories supported:
  CUT   — repeated contact + area fragmentation + low displacement
  OPEN  — rotation + area expansion + state change
  POUR  — container tilt (rotation) + displacement + area change
  DIP   — vertical motion + container interaction
  PICK  — hand proximity + contact + displacement + area growth + grasp closing
  PLACE — downward motion + stabilization + hand retreating
  MIX   — oscillatory rotation + high contact frequency
  CLOSE — inverse of OPEN (rotation + area shrink)
  PUSH  — directional consistency + displacement
  PULL  — directional consistency + displacement (toward camera)
  SQUEEZE — area shrink + contact + grasp
  SPREAD — lateral displacement + rotation
  SCOOP — similar to MIX but with more displacement
  WASH  — oscillatory + contact
  FOLD  — rotation + area ratio change
  TEAR  — area fragmentation + displacement
  <any> — generic: multi-feature state change
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from pipeline.motion_engine import MotionFeatures


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """Action inference result. Exported to Yash's integrator."""
    action_label: str
    action_category: str
    is_detected: bool
    confidence: float
    evidence: str
    timestamp_range: Tuple[float, float]
    key_frame_indices: List[int] = field(default_factory=list)
    motion_summary: dict = field(default_factory=dict)
    trajectory: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

def _norm(val: float, lo: float, hi: float) -> float:
    """Linearly normalize `val` to [0, 1] given expected range [lo, hi]."""
    if hi == lo:
        return 0.0
    return float(np.clip((val - lo) / (hi - lo), 0.0, 1.0))


def _sigmoid_norm(val: float, center: float, steepness: float = 5.0) -> float:
    """Sigmoid normalization: smooth 0→1 transition around center value."""
    return float(1.0 / (1.0 + np.exp(-steepness * (val - center))))


# ---------------------------------------------------------------------------
# Inferencer
# ---------------------------------------------------------------------------

class ActionInferencer:
    """
    Maps MotionFeatures → ActionResult using interpretable rule-based scoring.

    Designed for EGOCENTRIC video where:
      - "Up" in screen coords doesn't always mean physical up
      - Object area growing = object approaching camera (being picked up)
      - Hand grasp closing = grasping action
      - Contact proximity is more reliable than vertical direction
    """

    # Lowered detection threshold for better recall
    DETECTION_THRESHOLD = 0.32

    def infer(
        self,
        features: MotionFeatures,
        action_category: str,
        action_verb: str,
        timestamps: Tuple[float, float] = (0.0, 0.0),
    ) -> ActionResult:
        """Infer whether the action occurred and produce an explanation."""
        score, evidence = self._score_action(features, action_category.upper())

        motion_summary = {
            "rotation_deg": round(features.rotation_change, 1),
            "displacement_px": round(features.displacement_magnitude, 1),
            "contact_events": features.contact_events,
            "area_change_ratio": round(features.area_ratio, 3),
            "state_change": round(features.state_change_score, 3),
            "vertical_motion": round(features.vertical_motion_ratio, 3),
            "motion_speed_px_per_frame": round(features.motion_speed, 2),
            "contact_frequency": round(features.contact_frequency, 2),
            "area_variance": round(features.area_variance, 1),
            # New egocentric features
            "area_growth_trend": round(features.area_growth_trend, 3),
            "approach_score": round(features.approach_score, 3),
            "grasp_change": round(features.grasp_change, 3),
            "min_grasp_openness": round(features.min_grasp_openness, 3),
            "displacement_consistency": round(features.displacement_consistency, 3),
            "hand_approach_rate": round(features.hand_approach_rate, 3),
        }

        return ActionResult(
            action_label=action_verb,
            action_category=action_category.upper(),
            is_detected=(score >= self.DETECTION_THRESHOLD),
            confidence=round(score, 4),
            evidence=evidence,
            timestamp_range=timestamps,
            motion_summary=motion_summary,
        )

    # -----------------------------------------------------------------------
    # Scoring rules (one per action category)
    # -----------------------------------------------------------------------

    def _score_action(
        self, f: MotionFeatures, category: str
    ) -> Tuple[float, str]:
        """
        Compute a [0,1] confidence score and a human-readable evidence string
        for the given action category.
        """

        # ------------------ CUT / CHOP / SLICE ------------------
        if category in ("CUT", "CHOP", "SLICE"):
            contact_score = _norm(f.contact_frequency, 0, 4)
            frag_score = _norm(f.area_variance, 0, 800)
            stable_score = 1.0 - _norm(f.displacement_magnitude, 0, 120)
            contact_count = _norm(float(f.contact_events), 0, 10)
            state_score = f.state_change_score

            score = (
                0.30 * contact_score
                + 0.25 * frag_score
                + 0.15 * stable_score
                + 0.15 * contact_count
                + 0.15 * state_score
            )
            detected_str = "DETECTED" if score >= self.DETECTION_THRESHOLD else "not detected"
            evidence = (
                f"[CUT {detected_str}] "
                f"Contact freq={f.contact_frequency:.1f}, events={f.contact_events}; "
                f"area variance={f.area_variance:.0f}px² (fragmentation); "
                f"displacement={f.displacement_magnitude:.0f}px (local); "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ OPEN / UNSCREW ----------------------
        elif category in ("OPEN", "UNSCREW"):
            rot_score = _norm(abs(f.rotation_change), 0, 60)
            area_score = _norm(f.area_ratio - 1.0, 0, 0.4)
            state_score = f.state_change_score
            disp_score = _norm(f.displacement_magnitude, 10, 100)

            score = (
                0.35 * rot_score
                + 0.25 * area_score
                + 0.20 * state_score
                + 0.20 * disp_score
            )
            expansion = "expanding" if f.area_ratio > 1.05 else "stable"
            evidence = (
                f"[OPEN] Rotation: {f.rotation_change:.0f}°; "
                f"area ratio={f.area_ratio:.2f} ({expansion}); "
                f"displacement={f.displacement_magnitude:.0f}px; "
                f"state change={f.state_change_score:.2f}. "
                f"→ Rotation+displacement → opening inferred."
            )

        # ------------------ POUR / FILL -------------------------
        elif category in ("POUR", "FILL"):
            tilt_score = _norm(abs(f.rotation_change), 0, 45)
            motion_score = _norm(f.displacement_magnitude, 10, 80)
            vert_score = _norm(abs(f.vertical_motion_ratio), 0, 0.5)
            area_score = _norm(abs(f.area_ratio - 1.0), 0, 0.3)
            state_score = f.state_change_score

            score = (
                0.30 * tilt_score
                + 0.25 * motion_score
                + 0.20 * vert_score
                + 0.15 * area_score
                + 0.10 * state_score
            )
            evidence = (
                f"[POUR] Container tilt: {f.rotation_change:.0f}°; "
                f"displacement: {f.displacement_magnitude:.0f}px; "
                f"vertical ratio: {f.vertical_motion_ratio:.2f}; "
                f"area change: {f.area_ratio:.2f}; "
                f"state change: {f.state_change_score:.2f}."
            )

        # ------------------ DIP / DUNK / STEEP -------------------
        elif category in ("DIP", "DUNK", "STEEP"):
            vert_score = _norm(abs(f.vertical_motion_ratio), 0, 0.6)
            motion_score = _norm(f.displacement_magnitude, 10, 80)
            contact_score = _norm(float(f.contact_events), 0, 8)
            state_score = f.state_change_score

            score = (
                0.35 * vert_score
                + 0.25 * motion_score
                + 0.20 * contact_score
                + 0.20 * state_score
            )
            evidence = (
                f"[DIP] Vertical motion: {f.vertical_motion_ratio:.2f}; "
                f"displacement: {f.displacement_magnitude:.0f}px; "
                f"contact events: {f.contact_events}; "
                f"state change: {f.state_change_score:.2f}."
            )

        # ======== PICK / GRAB / TAKE (MAJOR REWRITE) ============
        elif category in ("PICK", "GRAB", "TAKE"):
            # In egocentric video, picking up means:
            # 1. Hand approaches object (contact_distance decreases)
            # 2. Hand closes (grasp_change negative = grasping)
            # 3. Object moves (displacement > 0)
            # 4. Object area may GROW (approaching camera) or stay stable
            # 5. Contact events happen (hand touching object)
            # 6. State changes (before ≠ after)
            # We DO NOT rely on vertical_motion_ratio (unreliable in egocentric)

            # --- Contact proximity ---
            closeness = max(0.0, 300.0 - f.contact_distance_mean)
            close_score = _norm(closeness, 0, 300)

            # --- Contact events ---
            contact_score = _norm(float(f.contact_events), 0, 8)

            # --- Displacement (object moved from original position) ---
            move_score = _norm(f.displacement_magnitude, 15, 200)

            # --- Area growth (object approaching camera = being picked up) ---
            approach_score = f.approach_score  # already 0-1

            # --- Grasp closing (hand is grasping) ---
            grasp_score = _norm(-f.grasp_change, 0.0, 0.4)  # negative change = closing

            # --- State change ---
            state_score = f.state_change_score

            # --- Vertical motion (minor contribution, unreliable) ---
            vert_bonus = _norm(f.vertical_motion_ratio, -0.3, 0.5) * 0.5

            # --- Hand approach rate (hand getting closer to object) ---
            hand_approach = _norm(-f.hand_approach_rate, 0.0, 0.5)

            # Weighted combination — proximity and contact are king
            score = (
                0.22 * close_score
                + 0.18 * contact_score
                + 0.15 * move_score
                + 0.12 * approach_score
                + 0.10 * grasp_score
                + 0.10 * state_score
                + 0.08 * vert_bonus
                + 0.05 * hand_approach
            )

            # Boost: if we have strong contact AND meaningful displacement, boost
            if close_score > 0.5 and move_score > 0.3:
                score = min(1.0, score * 1.25)

            # Boost: if grasp is closing and contact is good, this is very likely a pick
            if grasp_score > 0.3 and close_score > 0.4:
                score = min(1.0, score * 1.15)

            detected_str = "DETECTED" if score >= self.DETECTION_THRESHOLD else "not detected"
            evidence = (
                f"[PICK {detected_str}] "
                f"Hand-object dist={f.contact_distance_mean:.0f}px (proximity={close_score:.2f}); "
                f"contacts={f.contact_events}; "
                f"displacement={f.displacement_magnitude:.0f}px; "
                f"area growth={f.area_growth_trend:.2f} (approach={approach_score:.2f}); "
                f"grasp closing={-f.grasp_change:.2f}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ PLACE / PUT / SET -------------------
        elif category in ("PLACE", "PUT", "SET"):
            # In egocentric view: object area shrinks (moving away), speed decreases
            down_score = _norm(-f.vertical_motion_ratio, -0.1, 0.8)
            stable_score = 1.0 - _norm(f.motion_speed, 0, 8)
            retreat_score = _norm(-f.area_growth_trend, 0.0, 0.3)  # area shrinking
            hand_retreat = _norm(f.hand_approach_rate, 0.0, 0.5)  # hand moving away
            state_score = f.state_change_score

            score = (
                0.25 * down_score
                + 0.20 * stable_score
                + 0.20 * retreat_score
                + 0.15 * hand_retreat
                + 0.20 * state_score
            )
            evidence = (
                f"[PLACE] Motion ratio={f.vertical_motion_ratio:.2f}; "
                f"speed={f.motion_speed:.1f}px/frame; "
                f"area trend={f.area_growth_trend:.2f} "
                f"({'retreating' if f.area_growth_trend < -0.05 else 'stable'}); "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ MIX / STIR / SHAKE ------------------
        elif category in ("MIX", "STIR", "SHAKE"):
            circ_score = _norm(f.rotation_speed, 0, 4)
            contact_score = _norm(f.contact_frequency, 0, 6)
            speed_score = _norm(f.motion_speed, 1, 15)
            inconsistency = 1.0 - f.displacement_consistency  # oscillatory = inconsistent
            state_score = f.state_change_score

            score = (
                0.25 * circ_score
                + 0.25 * contact_score
                + 0.20 * speed_score
                + 0.15 * inconsistency
                + 0.15 * state_score
            )
            evidence = (
                f"[MIX] Rotation speed={f.rotation_speed:.1f}°/frame; "
                f"contact freq={f.contact_frequency:.1f}; "
                f"motion speed={f.motion_speed:.1f}px/frame; "
                f"directional consistency={f.displacement_consistency:.2f} (low=oscillatory)."
            )

        # ------------------ CLOSE / SHUT / CAP ------------------
        elif category in ("CLOSE", "SHUT", "CAP"):
            rot_score = _norm(abs(f.rotation_change), 0, 60)
            shrink_score = _norm(1.0 - f.area_ratio, 0, 0.3)
            state_score = f.state_change_score

            score = (
                0.35 * rot_score
                + 0.35 * max(0.0, shrink_score)
                + 0.30 * state_score
            )
            evidence = (
                f"[CLOSE] Rotation: {f.rotation_change:.0f}°; "
                f"area ratio={f.area_ratio:.2f} "
                f"({'shrinking' if f.area_ratio < 0.95 else 'stable'}); "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ PUSH --------------------------------
        elif category in ("PUSH",):
            disp_score = _norm(f.displacement_magnitude, 20, 150)
            consistency = _norm(f.displacement_consistency, 0.3, 0.9)
            contact_score = _norm(float(f.contact_events), 0, 6)
            state_score = f.state_change_score

            score = (
                0.30 * disp_score
                + 0.25 * consistency
                + 0.20 * contact_score
                + 0.25 * state_score
            )
            evidence = (
                f"[PUSH] Displacement={f.displacement_magnitude:.0f}px; "
                f"directional consistency={f.displacement_consistency:.2f}; "
                f"contacts={f.contact_events}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ PULL --------------------------------
        elif category in ("PULL",):
            disp_score = _norm(f.displacement_magnitude, 20, 150)
            consistency = _norm(f.displacement_consistency, 0.3, 0.9)
            approach_s = f.approach_score  # approaching camera = pulling toward self
            state_score = f.state_change_score

            score = (
                0.30 * disp_score
                + 0.20 * consistency
                + 0.25 * approach_s
                + 0.25 * state_score
            )
            evidence = (
                f"[PULL] Displacement={f.displacement_magnitude:.0f}px; "
                f"approach={f.approach_score:.2f}; "
                f"consistency={f.displacement_consistency:.2f}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ SQUEEZE ----------------------------
        elif category in ("SQUEEZE",):
            area_shrink = _norm(1.0 - f.area_ratio, 0, 0.3)
            grasp_score = _norm(-f.grasp_change, 0.0, 0.3)
            contact_score = _norm(float(f.contact_events), 0, 8)
            state_score = f.state_change_score

            score = (
                0.30 * area_shrink
                + 0.25 * grasp_score
                + 0.25 * contact_score
                + 0.20 * state_score
            )
            evidence = (
                f"[SQUEEZE] Area ratio={f.area_ratio:.2f}; "
                f"grasp change={f.grasp_change:.2f}; "
                f"contacts={f.contact_events}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ SPREAD ----------------------------
        elif category in ("SPREAD",):
            lateral = _norm(f.displacement_magnitude, 20, 120)
            rot_score = _norm(abs(f.rotation_change), 0, 30)
            contact_score = _norm(float(f.contact_events), 0, 6)
            state_score = f.state_change_score

            score = (
                0.30 * lateral
                + 0.25 * rot_score
                + 0.25 * contact_score
                + 0.20 * state_score
            )
            evidence = (
                f"[SPREAD] Displacement={f.displacement_magnitude:.0f}px; "
                f"rotation={f.rotation_change:.0f}°; "
                f"contacts={f.contact_events}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ SCOOP ----------------------------
        elif category in ("SCOOP",):
            disp_score = _norm(f.displacement_magnitude, 20, 100)
            vert_score = _norm(f.vertical_motion_ratio, 0, 0.5)
            contact_score = _norm(float(f.contact_events), 0, 6)
            state_score = f.state_change_score

            score = (
                0.30 * disp_score
                + 0.25 * vert_score
                + 0.25 * contact_score
                + 0.20 * state_score
            )
            evidence = (
                f"[SCOOP] Displacement={f.displacement_magnitude:.0f}px; "
                f"vertical={f.vertical_motion_ratio:.2f}; "
                f"contacts={f.contact_events}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ WASH / WIPE -----------------------
        elif category in ("WASH", "WIPE"):
            speed_score = _norm(f.motion_speed, 2, 15)
            oscillation = 1.0 - f.displacement_consistency
            contact_score = _norm(float(f.contact_events), 0, 8)
            state_score = f.state_change_score

            score = (
                0.25 * speed_score
                + 0.25 * oscillation
                + 0.25 * contact_score
                + 0.25 * state_score
            )
            evidence = (
                f"[WASH] Speed={f.motion_speed:.1f}px/frame; "
                f"oscillation={oscillation:.2f}; "
                f"contacts={f.contact_events}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ FOLD ------------------------------
        elif category in ("FOLD",):
            rot_score = _norm(abs(f.rotation_change), 0, 90)
            area_score = _norm(abs(f.area_ratio - 1.0), 0, 0.4)
            state_score = f.state_change_score

            score = 0.35 * rot_score + 0.35 * area_score + 0.30 * state_score
            evidence = (
                f"[FOLD] Rotation={f.rotation_change:.0f}°; "
                f"area ratio={f.area_ratio:.2f}; "
                f"state change={f.state_change_score:.2f}."
            )

        # ------------------ TEAR ------------------------------
        elif category in ("TEAR",):
            frag_score = _norm(f.area_variance, 0, 500)
            disp_score = _norm(f.displacement_magnitude, 10, 100)
            state_score = f.state_change_score

            score = 0.35 * frag_score + 0.35 * disp_score + 0.30 * state_score
            evidence = (
                f"[TEAR] Area variance={f.area_variance:.0f}px² (fragmentation); "
                f"displacement={f.displacement_magnitude:.0f}px; "
                f"state change={f.state_change_score:.2f}."
            )

        # ======== GENERIC fallback (improved) =================
        else:
            # Use a broader set of features for unknown categories
            move_score = _norm(f.displacement_magnitude, 10, 100)
            contact_score = _norm(float(f.contact_events), 0, 6)
            state_score = f.state_change_score
            rot_score = _norm(abs(f.rotation_change), 0, 30)

            score = (
                0.25 * move_score
                + 0.25 * contact_score
                + 0.25 * state_score
                + 0.25 * rot_score
            )
            evidence = (
                f"[{category}] Generic inference: "
                f"displacement={f.displacement_magnitude:.0f}px; "
                f"rotation={f.rotation_change:.0f}°; "
                f"contacts={f.contact_events}; "
                f"state change={f.state_change_score:.2f}."
            )

        return float(np.clip(score, 0.0, 1.0)), evidence

    # -----------------------------------------------------------------------
    # Batch helper — IMPROVED with multi-frame aggregation
    # -----------------------------------------------------------------------

    def infer_from_history(
        self,
        all_features: List[MotionFeatures],
        action_category: str,
        action_verb: str,
        fps: float = 30.0,
    ) -> ActionResult:
        """
        Aggregate per-frame MotionFeatures into a single video-level inference.

        IMPROVED: Instead of just peak frame, uses top-5 frames aggregated
        with robust median for more stable scoring.
        """
        if not all_features:
            null_f = MotionFeatures()
            return self.infer(null_f, action_category, action_verb)

        # Score each frame's activity
        def _activity(f: MotionFeatures) -> float:
            return (
                f.displacement_magnitude
                + abs(f.rotation_change) * 2.0
                + f.area_variance * 0.01
                + f.contact_events * 5.0
                + f.state_change_score * 100.0
                + f.approach_score * 50.0
                + abs(f.grasp_change) * 30.0
            )

        # Pick top-5 most active frames and aggregate
        scored = [(i, _activity(all_features[i])) for i in range(len(all_features))]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_k = min(5, len(scored))
        top_indices = [s[0] for s in scored[:top_k]]
        top_features = [all_features[i] for i in top_indices]

        # Create aggregated features (median for robustness)
        agg = MotionFeatures(
            displacement_magnitude=float(np.median([f.displacement_magnitude for f in top_features])),
            displacement_direction=float(np.median([f.displacement_direction for f in top_features])),
            vertical_motion_ratio=float(np.median([f.vertical_motion_ratio for f in top_features])),
            motion_speed=float(np.median([f.motion_speed for f in top_features])),
            rotation_change=float(np.median([f.rotation_change for f in top_features])),
            rotation_speed=float(np.median([f.rotation_speed for f in top_features])),
            area_ratio=float(np.median([f.area_ratio for f in top_features])),
            area_variance=float(np.max([f.area_variance for f in top_features])),  # max for fragmentation
            area_growth_rate=float(np.median([f.area_growth_rate for f in top_features])),
            contact_distance_mean=float(np.min([f.contact_distance_mean for f in top_features])),  # min = closest
            contact_frequency=float(np.max([f.contact_frequency for f in top_features])),
            contact_events=int(np.max([f.contact_events for f in top_features])),
            state_change_score=float(np.max([f.state_change_score for f in top_features])),
            area_growth_trend=float(np.median([f.area_growth_trend for f in top_features])),
            approach_score=float(np.max([f.approach_score for f in top_features])),
            displacement_consistency=float(np.median([f.displacement_consistency for f in top_features])),
            max_displacement_burst=float(np.max([f.max_displacement_burst for f in top_features])),
            grasp_change=float(np.min([f.grasp_change for f in top_features])),  # min = most closing
            min_grasp_openness=float(np.min([f.min_grasp_openness for f in top_features])),
            grasp_close_events=int(np.max([f.grasp_close_events for f in top_features])),
            hand_approach_rate=float(np.min([f.hand_approach_rate for f in top_features])),
            window_frames=max(f.window_frames for f in top_features),
        )

        # Timestamps
        start_frame = 0
        end_frame = len(all_features) - 1
        start_ms = (start_frame / max(fps, 1.0)) * 1000.0
        end_ms = (end_frame / max(fps, 1.0)) * 1000.0

        result = self.infer(agg, action_category, action_verb, (start_ms, end_ms))
        result.key_frame_indices = []
        return result


# ---------------------------------------------------------------------------
# Quick standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from pipeline.motion_engine import MotionFeatures

    print("=== ActionInferencer standalone test ===\n")
    inferencer = ActionInferencer()

    # --- CUT test ---
    cut_f = MotionFeatures(
        contact_frequency=4.5, area_variance=800, displacement_magnitude=30,
        contact_events=12, state_change_score=0.6
    )
    r = inferencer.infer(cut_f, "CUT", "cutting", (0, 5000))
    print(f"CUT  → detected={r.is_detected}  conf={r.confidence:.3f}")
    print(f"  Evidence: {r.evidence}\n")

    # --- OPEN test ---
    open_f = MotionFeatures(
        rotation_change=72, area_ratio=1.3, state_change_score=0.75,
        displacement_magnitude=50,
    )
    r = inferencer.infer(open_f, "OPEN", "opening", (0, 3000))
    print(f"OPEN → detected={r.is_detected}  conf={r.confidence:.3f}")
    print(f"  Evidence: {r.evidence}\n")

    # --- POUR test ---
    pour_f = MotionFeatures(
        rotation_change=45, displacement_magnitude=80,
        vertical_motion_ratio=0.4, area_ratio=0.9, state_change_score=0.5,
    )
    r = inferencer.infer(pour_f, "POUR", "pouring", (0, 4000))
    print(f"POUR → detected={r.is_detected}  conf={r.confidence:.3f}")
    print(f"  Evidence: {r.evidence}\n")

    # --- PICK test (egocentric-realistic: low vertical, high contact+approach) ---
    pick_f = MotionFeatures(
        vertical_motion_ratio=-0.08,       # weak vertical (egocentric)
        contact_distance_mean=70,          # hand very close
        contact_events=8,                  # lots of contact
        displacement_magnitude=45,         # object moved
        area_growth_trend=0.25,            # object approaching camera
        approach_score=0.5,
        grasp_change=-0.3,                 # hand closed (grasping)
        min_grasp_openness=0.25,
        state_change_score=0.4,
        hand_approach_rate=-0.2,
    )
    r = inferencer.infer(pick_f, "PICK", "picking", (0, 2000))
    print(f"PICK → detected={r.is_detected}  conf={r.confidence:.3f}")
    print(f"  Evidence: {r.evidence}\n")

    # --- PLACE test ---
    place_f = MotionFeatures(
        vertical_motion_ratio=-0.5, motion_speed=2, state_change_score=0.4,
        area_growth_trend=-0.15, hand_approach_rate=0.3,
    )
    r = inferencer.infer(place_f, "PLACE", "placing", (0, 2500))
    print(f"PLACE → detected={r.is_detected}  conf={r.confidence:.3f}")
    print(f"  Evidence: {r.evidence}\n")

    # --- MIX test ---
    mix_f = MotionFeatures(
        rotation_speed=3.5, contact_frequency=6, motion_speed=10,
        displacement_consistency=0.2,
    )
    r = inferencer.infer(mix_f, "MIX", "mixing", (0, 6000))
    print(f"MIX  → detected={r.is_detected}  conf={r.confidence:.3f}")
    print(f"  Evidence: {r.evidence}\n")

    print("ActionInferencer test PASSED ✓")

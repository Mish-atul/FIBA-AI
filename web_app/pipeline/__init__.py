"""
FIBA AI — Core Pipeline Package
================================
Atul:    query_parser, hand_detector, object_detector
Tanishk: tracker, motion_engine, action_inferencer, segmentor
Yash:    integrator, sop_validator, hand_skeleton
"""

from .query_parser import QueryResult, parse_query
from .hand_detector import HandDetectionResult, HandDetector
from .object_detector import ObjectDetectionResult, ObjectDetector
from .tracker import TrackResult, ObjectTracker
from .motion_engine import MotionFeatures, MotionEngine
from .action_inferencer import ActionResult, ActionInferencer
from .segmentor import (
    MobileSAMSegmentor, encode_frame_b64,
    draw_annotated_frame, draw_trajectory, annotate_key_frames,
)
from .hand_skeleton import draw_hand_skeleton, draw_finger_trajectories
from .sop_validator import SOPValidator, DEFAULT_SOP
from .integrator import FIBAPipeline, PipelineResult


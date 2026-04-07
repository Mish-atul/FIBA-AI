"""
Flask Web App — Yash
=====================
FIBA AI local web server. Runs entirely offline.

Endpoints:
  GET  /                      → Web UI
  POST /api/process           → Upload video + query, start action pipeline
  GET  /api/status/<id>       → Poll job progress
  GET  /api/stream/<id>       → SSE stream for real-time progress
  POST /api/sop/reference     → Upload reference video for SOP learning
  POST /api/sop/validate      → Upload test video for SOP validation
"""

import os, uuid, json, threading, time
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from pipeline.integrator import FIBAPipeline

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

job_registry = {}
pipeline = FIBAPipeline()


@app.route("/")
def index():
    return render_template("index.html")


# ── Regular Action Search ─────────────────────────────────

@app.route("/api/process", methods=["POST"])
def process_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    query_text = request.form.get("query", "").strip()
    if not query_text:
        return jsonify({"error": "No query provided"}), 400

    video_file = request.files["video"]
    if not video_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    job_id = str(uuid.uuid4())[:8]
    safe_name = "".join(c if c.isalnum() or c in (".", "-", "_") else "_" for c in video_file.filename)
    video_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{safe_name}")
    video_file.save(video_path)

    job_registry[job_id] = {
        "progress": 0, "message": "Queued...",
        "result": None, "done": False, "error": None,
    }

    def run_pipeline():
        def progress_cb(pct, msg):
            job_registry[job_id]["progress"] = pct
            job_registry[job_id]["message"] = msg

        result = pipeline.run(video_path, query_text, progress_cb)
        job_registry[job_id]["progress"] = 100
        job_registry[job_id]["done"] = True

        if result.success:
            job_registry[job_id]["result"] = {
                "action_detected": result.action_detected,
                "action_label": result.action_label,
                "action_category": result.action_category,
                "confidence": result.confidence,
                "timestamp_range": list(result.timestamp_range),
                "evidence": result.evidence,
                "key_frames": result.key_frames_b64,
                "skeleton_frames": result.skeleton_frames_b64,
                "finger_trajectory": result.finger_trajectory_b64,
                "trajectory": result.trajectory_b64,
                "motion_summary": result.motion_summary,
                "query_info": result.query_info,
                "total_frames": result.total_frames,
                "fps": result.fps,
                "processing_time_s": result.processing_time_s,
                "action_description": result.action_description,
                "edge_stats": result.edge_stats,
            }
            job_registry[job_id]["message"] = "Done!"
        else:
            job_registry[job_id]["error"] = result.error
            job_registry[job_id]["message"] = f"Error: {result.error[:120]}"

        try:
            os.remove(video_path)
        except OSError:
            pass

    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/api/status/<job_id>")
def get_status(job_id):
    if job_id not in job_registry:
        return jsonify({"error": "Job not found"}), 404
    job = job_registry[job_id]
    return jsonify({
        "job_id": job_id, "progress": job["progress"],
        "message": job["message"], "done": job["done"],
        "result": job["result"], "error": job["error"],
    })


@app.route("/api/stream/<job_id>")
def stream_progress(job_id):
    def event_stream():
        while True:
            if job_id not in job_registry:
                yield 'data: {"error": "not found"}\n\n'
                break
            job = job_registry[job_id]
            data = json.dumps({"progress": job["progress"], "message": job["message"], "done": job["done"]})
            yield f"data: {data}\n\n"
            if job["done"]:
                break
            time.sleep(0.5)
    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── SOP Compliance ────────────────────────────────────────

@app.route("/api/sop/reference", methods=["POST"])
def sop_reference():
    """Upload a known-correct reference video to learn the SOP sequence."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files["video"]
    if not video_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    job_id = "sop_ref_" + str(uuid.uuid4())[:6]
    safe_name = "".join(c if c.isalnum() or c in (".", "-", "_") else "_" for c in video_file.filename)
    video_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{safe_name}")
    video_file.save(video_path)

    job_registry[job_id] = {
        "progress": 0, "message": "Queued...",
        "result": None, "done": False, "error": None,
    }

    def run_ref():
        def progress_cb(pct, msg):
            job_registry[job_id]["progress"] = pct
            job_registry[job_id]["message"] = msg

        result = pipeline.run_sop_reference(video_path, progress_cb)
        job_registry[job_id]["progress"] = 100
        job_registry[job_id]["done"] = True

        if result.success:
            segments_data = []
            for seg in result.segments:
                segments_data.append({
                    "start_frame": seg.start_frame,
                    "end_frame": seg.end_frame,
                    "duration_frames": seg.duration_frames,
                    "predicted_task": seg.predicted_task,
                    "task_name": seg.task_name,
                    "confidence": round(float(seg.confidence), 3),
                    "keyframe_b64": seg.keyframe_b64,
                    "skeleton_b64": seg.skeleton_b64,
                })

            sop_steps = [{"step_num": s.step_num, "task_name": s.task_name, "description": s.description}
                         for s in result.sop_steps]

            job_registry[job_id]["result"] = {
                "type": "sop_reference",
                "segments": segments_data,
                "sop_steps": sop_steps,
                "total_frames": result.total_frames,
                "fps": result.fps,
                "processing_time_s": result.processing_time_s,
                "segment_count": len(segments_data),
            }
            job_registry[job_id]["message"] = f"Reference learned! ({len(segments_data)} steps)"
        else:
            job_registry[job_id]["error"] = result.error
            job_registry[job_id]["message"] = f"Error: {result.error[:120]}"

        try:
            os.remove(video_path)
        except OSError:
            pass

    threading.Thread(target=run_ref, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/api/sop/validate", methods=["POST"])
def sop_validate():
    """Upload a test video to validate against trained classifier or reference."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    # Allow validation if classifier is available OR reference is loaded
    has_classifier = pipeline.sop_validator.classifier.available
    has_reference = pipeline.sop_validator.has_reference
    if not has_classifier and not has_reference:
        return jsonify({"error": "No classifier trained and no reference loaded. Run train_sop_classifier.py or upload a reference first."}), 400

    video_file = request.files["video"]
    if not video_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    job_id = "sop_val_" + str(uuid.uuid4())[:6]
    safe_name = "".join(c if c.isalnum() or c in (".", "-", "_") else "_" for c in video_file.filename)
    video_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{safe_name}")
    video_file.save(video_path)

    job_registry[job_id] = {
        "progress": 0, "message": "Queued...",
        "result": None, "done": False, "error": None,
    }

    def run_val():
        def progress_cb(pct, msg):
            job_registry[job_id]["progress"] = pct
            job_registry[job_id]["message"] = msg

        result = pipeline.run_sop_validate(video_path, progress_cb)
        job_registry[job_id]["progress"] = 100
        job_registry[job_id]["done"] = True

        if result.success:
            job_registry[job_id]["result"] = {
                "type": "sop_validate",
                "passed": result.passed,
                "step_results": result.step_results,
                "summary": result.summary,
                "total_frames": result.total_frames,
                "fps": result.fps,
                "processing_time_s": result.processing_time_s,
            }
            job_registry[job_id]["message"] = "Done!"
        else:
            job_registry[job_id]["error"] = result.error
            job_registry[job_id]["message"] = f"Error: {result.error[:120]}"

        try:
            os.remove(video_path)
        except OSError:
            pass

    threading.Thread(target=run_val, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/api/sop/status")
def sop_status():
    """Check if classifier or reference is loaded."""
    return jsonify({
        "has_reference": pipeline.sop_validator.has_reference,
        "has_classifier": pipeline.sop_validator.classifier.available,
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  FIBA AI — Find-it-by-Action")
    print("  Edge-Ready · Zero-Shot · Explainable · SOP Compliance")
    print("=" * 60)
    print(f"\n  Open http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

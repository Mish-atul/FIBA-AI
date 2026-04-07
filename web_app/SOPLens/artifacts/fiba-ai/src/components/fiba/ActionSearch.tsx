import React, { useState, useRef, useEffect } from "react";
import { UploadCloud, Search, ArrowRight, X, AlertTriangle, Monitor, Activity, Navigation, BarChart3, FileText, ClipboardList, Lightbulb, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ActionResult, JobStatus } from "@/types/fiba";

interface ActionSearchProps {
  onOpenLightbox: (src: string) => void;
}

const STAGES = [
  { name: "Parse query", range: [0, 15] },
  { name: "Detect objects", range: [15, 45] },
  { name: "Track & motion", range: [45, 72] },
  { name: "Infer action", range: [72, 85] },
  { name: "Render output", range: [85, 100] }
];

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "An unexpected error occurred";
}

export function ActionSearch({ onOpenLightbox }: ActionSearchProps) {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [query, setQuery] = useState("");
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ActionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      if (pollIntervalRef.current !== null) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setVideoFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith("video/")) {
        setVideoFile(file);
      }
    }
  };

  const handleAnalyze = async () => {
    if (!videoFile || !query) return;

    eventSourceRef.current?.close();
    if (pollIntervalRef.current !== null) clearInterval(pollIntervalRef.current);

    setIsLoading(true);
    setError(null);
    setProgress(0);
    setProgressMsg("Starting analysis...");
    setResult(null);

    const formData = new FormData();
    formData.append("video", videoFile);
    formData.append("query", query);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
      const res = await fetch(`${baseUrl}/api/process`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error((errorData as { error?: string }).error || "Failed to start processing");
      }

      const { job_id } = await res.json() as { job_id: string };

      const eventSource = new EventSource(`${baseUrl}/api/stream/${job_id}`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data) as { progress: number; message: string; done: boolean; error?: string };
        if (data.error) {
          eventSource.close();
          eventSourceRef.current = null;
          setError(data.error);
          setIsLoading(false);
          return;
        }

        setProgress(data.progress);
        setProgressMsg(data.message);

        if (data.done) {
          eventSource.close();
          eventSourceRef.current = null;
          fetch(`${baseUrl}/api/status/${job_id}`)
            .then(r => r.json())
            .then((d: JobStatus) => {
              if (d.error) {
                setError(d.error);
              } else if (d.result && "action_detected" in d.result) {
                setResult(d.result as ActionResult);
              }
              setIsLoading(false);
            })
            .catch((err: unknown) => {
              setError(getErrorMessage(err));
              setIsLoading(false);
            });
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        eventSourceRef.current = null;
        const interval = setInterval(() => {
          fetch(`${baseUrl}/api/status/${job_id}`)
            .then(r => r.json())
            .then((d: JobStatus) => {
              setProgress(d.progress);
              setProgressMsg(d.message);
              if (d.done) {
                clearInterval(interval);
                pollIntervalRef.current = null;
                if (d.error) setError(d.error);
                else if (d.result && "action_detected" in d.result) setResult(d.result as ActionResult);
                setIsLoading(false);
              }
            })
            .catch((err: unknown) => {
              clearInterval(interval);
              pollIntervalRef.current = null;
              setError(getErrorMessage(err));
              setIsLoading(false);
            });
        }, 800);
        pollIntervalRef.current = interval;
      };

    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setIsLoading(false);
    }
  };

  const resetAll = () => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setVideoFile(null);
    setQuery("");
    setProgress(0);
    setProgressMsg("");
    setResult(null);
    setError(null);
  };

  const formatSize = (bytes: number) => (bytes / (1024 * 1024)).toFixed(2) + " MB";

  return (
    <div className="w-full max-w-6xl mx-auto px-4 pb-20 space-y-8 animate-in fade-in duration-500">
      {/* Upload and Query Section */}
      {!result && !isLoading && (
        <div className="space-y-6">
          <div
            className={cn(
              "relative rounded-xl border-2 border-dashed p-10 text-center transition-colors backdrop-blur-sm",
              isDragging ? "border-white/40 bg-white/5" : "border-[var(--fiba-card-border)] bg-[var(--fiba-card)]",
              videoFile && "border-white/25 bg-white/4"
            )}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            data-testid="upload-zone"
          >
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept="video/*"
              onChange={handleFileChange}
              data-testid="input-file"
            />
            {videoFile ? (
              <div className="flex flex-col items-center gap-3">
                <div className="rounded-full bg-white/10 p-3 text-white/60">
                  <UploadCloud className="h-8 w-8" />
                </div>
                <div className="text-sm font-medium text-white">{videoFile.name}</div>
                <div className="text-xs text-muted-foreground">{formatSize(videoFile.size)}</div>
                <button
                  onClick={() => setVideoFile(null)}
                  className="mt-2 text-xs text-red-400 hover:text-red-300 flex items-center gap-1"
                  data-testid="button-remove-file"
                >
                  <X className="h-3 w-3" /> Remove video
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="rounded-full bg-[var(--fiba-glass)] p-4 text-muted-foreground">
                  <UploadCloud className="h-8 w-8" />
                </div>
                <h3 className="text-lg font-medium text-white">Drag & drop video</h3>
                <p className="text-sm text-muted-foreground">MP4, AVI, MOV · max ~100 MB recommended</p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-2 rounded-md bg-[var(--fiba-glass)] px-4 py-2 text-sm font-medium text-white hover:bg-white/10 transition-colors"
                  data-testid="button-browse"
                >
                  Browse files
                </button>
              </div>
            )}
          </div>

          <div className="relative flex items-center">
            <div className="absolute inset-y-0 left-0 flex items-center pl-4 text-muted-foreground">
              <Search className="h-5 w-5" />
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAnalyze(); }}
              placeholder="Describe the action — e.g., cutting onion, opening box, pouring water"
              className="w-full rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-input)] py-4 pl-12 pr-32 text-white placeholder:text-muted-foreground focus:border-white/30 focus:outline-none focus:ring-1 focus:ring-white/20 shadow-sm"
              data-testid="input-query"
            />
            <button
              onClick={handleAnalyze}
              disabled={!videoFile || !query || isLoading}
              className="absolute right-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-black shadow-md disabled:opacity-40 flex items-center gap-2 hover:bg-white/90 transition-colors"
              data-testid="button-analyze"
            >
              Analyze <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground mr-2">Examples:</span>
            {["cutting onion", "opening box", "pouring water", "picking up hotdog", "mixing ingredients"].map((ex) => (
              <button
                key={ex}
                onClick={() => setQuery(ex)}
                className="rounded-full border border-[var(--fiba-card-border)] bg-[var(--fiba-glass)] px-3 py-1 text-xs text-muted-foreground hover:bg-white/10 hover:text-white transition-colors"
                data-testid={`chip-${ex.replace(/\s+/g, '-')}`}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading Progress Section */}
      {isLoading && (
        <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-8 shadow-xl backdrop-blur-md animate-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-center gap-4 mb-8">
            <div className="relative h-10 w-10">
              <svg className="h-full w-full animate-spin text-white/40" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Processing pipeline...</h3>
              <p className="text-sm text-muted-foreground" data-testid="text-progress-msg">{progressMsg}</p>
            </div>
            <div className="ml-auto text-3xl font-black text-white/50" data-testid="text-progress-pct">{progress}%</div>
          </div>

          <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--fiba-glass)]">
            <div
              className="h-full bg-white/70 transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
              data-testid="progress-bar"
            />
          </div>

          <div className="mt-8 grid gap-4">
            {STAGES.map((stage, idx) => {
              const isPast = progress >= stage.range[1];
              const isCurrent = progress >= stage.range[0] && progress < stage.range[1];
              return (
                <div key={idx} className="flex items-center gap-4">
                  <div className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-full border text-xs font-bold transition-colors",
                    isPast ? "border-white bg-white text-black" :
                    isCurrent ? "border-white/60 bg-white/20 text-white" :
                    "border-[var(--fiba-card-border)] bg-transparent text-muted-foreground"
                  )}>
                    {isPast ? "✓" : idx + 1}
                  </div>
                  <div className={cn("font-medium text-sm", isPast || isCurrent ? "text-white" : "text-muted-foreground")}>
                    {stage.name}
                    <span className="ml-2 text-xs opacity-50">{stage.range[0]}-{stage.range[1]}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 flex flex-col items-center justify-center text-center animate-in slide-in-from-bottom-4">
          <div className="rounded-full bg-red-500/20 p-3 text-red-500 mb-4">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Pipeline Error</h3>
          <p className="text-sm text-red-200 mb-6" data-testid="text-error">{error}</p>
          <button
            onClick={resetAll}
            className="rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20 transition-colors"
            data-testid="button-try-again"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Results Section */}
      {result && !isLoading && (
        <div className="space-y-6 animate-in slide-in-from-bottom-8 duration-700">

          {/* Verdict Banner */}
          <div className={cn(
            "relative overflow-hidden rounded-2xl border p-6 flex items-center justify-between",
            result.action_detected
              ? "border-green-500/30 bg-gradient-to-r from-green-500/10 to-transparent"
              : "border-red-500/30 bg-gradient-to-r from-red-500/10 to-transparent"
          )} data-testid="verdict-banner">
            <div className="flex items-center gap-4 z-10">
              <div className="text-4xl">{result.action_detected ? "✅" : "❌"}</div>
              <div>
                <h2 className="text-2xl font-black text-white">
                  {result.action_detected ? "Action Detected" : "Not Detected"}
                </h2>
                <p className="text-sm text-white/70 mt-1">
                  "{query}" → {result.action_label} <span className="opacity-50">({result.action_category})</span>
                </p>
              </div>
            </div>

            <div className="relative flex h-24 w-24 items-center justify-center z-10">
              <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" className="stroke-white/10" strokeWidth="8" fill="none" />
                <circle
                  cx="50" cy="50" r="40"
                  className={cn(
                    "transition-all duration-1000 ease-out",
                    result.action_detected ? "stroke-green-500" : "stroke-red-500"
                  )}
                  strokeWidth="8"
                  fill="none"
                  strokeDasharray="251.2"
                  strokeDashoffset={251.2 - (251.2 * result.confidence)}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-xl font-bold text-white" data-testid="text-confidence">{Math.round(result.confidence * 100)}%</span>
              </div>
            </div>
          </div>

          {/* Description & Evidence */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
              <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-3">
                <Activity className="h-5 w-5 text-[var(--fiba-teal)]" /> Action Description
              </h3>
              <p className="text-sm leading-relaxed text-muted-foreground" data-testid="text-action-description">
                {result.action_description}
              </p>
            </div>

            <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
              <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-3">
                <Lightbulb className="h-5 w-5 text-[var(--fiba-purple)]" /> AI Evidence
              </h3>
              <div className="border-l-2 border-white/30 bg-white/5 p-4 rounded-r-lg text-sm text-white/80" data-testid="text-evidence">
                {result.evidence}
              </div>
            </div>
          </div>

          {/* Key Frames Grid */}
          {result.key_frames.length > 0 && (
            <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
              <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-4">
                <Monitor className="h-5 w-5 text-white/70" /> Key Frames
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {result.key_frames.map((b64, i) => (
                  <div
                    key={i}
                    role="button"
                    tabIndex={0}
                    aria-label={`Open key frame ${i + 1} in lightbox`}
                    className="group relative cursor-pointer overflow-hidden rounded-lg border border-white/10 bg-black/50 focus:outline-none focus:ring-2 focus:ring-[var(--fiba-purple)]"
                    onClick={() => onOpenLightbox(`data:image/jpeg;base64,${b64}`)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenLightbox(`data:image/jpeg;base64,${b64}`); }}
                    data-testid={`keyframe-${i}`}
                  >
                    <img
                      src={`data:image/jpeg;base64,${b64}`}
                      alt={`Key frame ${i + 1}`}
                      className="w-full aspect-video object-cover transition-transform duration-300 group-hover:scale-105"
                      loading="lazy"
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 p-2 pt-6">
                      <div className="text-xs font-medium text-white">Frame {i + 1}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hand Skeleton & Trajectories */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {result.skeleton_frames.length > 0 && (
              <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
                <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-3">
                  Hand Skeleton
                </h3>
                <div className="flex flex-wrap gap-x-3 gap-y-1 mb-4 text-[10px] font-medium">
                  <span className="text-blue-400">● Thumb</span>
                  <span className="text-green-400">● Index</span>
                  <span className="text-orange-400">● Middle</span>
                  <span className="text-cyan-400">● Ring</span>
                  <span className="text-pink-400">● Pinky</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {result.skeleton_frames.map((b64, i) => (
                    <div
                      key={i}
                      role="button"
                      tabIndex={0}
                      aria-label={`Open skeleton frame ${i + 1} in lightbox`}
                      className="cursor-pointer overflow-hidden rounded-lg border border-white/5 bg-black focus:outline-none focus:ring-2 focus:ring-[var(--fiba-purple)]"
                      onClick={() => onOpenLightbox(`data:image/jpeg;base64,${b64}`)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenLightbox(`data:image/jpeg;base64,${b64}`); }}
                      data-testid={`skeleton-${i}`}
                    >
                      <img
                        src={`data:image/jpeg;base64,${b64}`}
                        className="w-full aspect-video object-cover hover:opacity-80 transition-opacity"
                        alt={`Skeleton ${i + 1}`}
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-4">
              {result.finger_trajectory && (
                <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
                  <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-4">
                    <Navigation className="h-5 w-5 text-white/70" /> Finger Trajectory
                  </h3>
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label="Open finger trajectory in lightbox"
                    className="cursor-pointer overflow-hidden rounded-lg border border-white/5 bg-white/5 focus:outline-none focus:ring-2 focus:ring-[var(--fiba-purple)]"
                    onClick={() => onOpenLightbox(`data:image/jpeg;base64,${result.finger_trajectory}`)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenLightbox(`data:image/jpeg;base64,${result.finger_trajectory}`); }}
                    data-testid="img-finger-trajectory"
                  >
                    <img
                      src={`data:image/jpeg;base64,${result.finger_trajectory}`}
                      className="w-full h-auto object-contain hover:opacity-80 transition-opacity"
                      alt="Finger Trajectory"
                    />
                  </div>
                </div>
              )}

              {result.trajectory && (
                <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
                  <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-4">
                    <Navigation className="h-5 w-5 text-[var(--fiba-teal)]" /> Object Trajectory
                  </h3>
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label="Open object trajectory in lightbox"
                    className="cursor-pointer overflow-hidden rounded-lg border border-white/5 bg-white/5 focus:outline-none focus:ring-2 focus:ring-[var(--fiba-teal)]"
                    onClick={() => onOpenLightbox(`data:image/jpeg;base64,${result.trajectory}`)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenLightbox(`data:image/jpeg;base64,${result.trajectory}`); }}
                    data-testid="img-object-trajectory"
                  >
                    <img
                      src={`data:image/jpeg;base64,${result.trajectory}`}
                      className="w-full h-auto object-contain hover:opacity-80 transition-opacity"
                      alt="Object Trajectory"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Motion Analytics */}
          <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
            <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-6">
              <BarChart3 className="h-5 w-5 text-white/70" /> Motion Analytics
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {[
                { label: "ROTATION", value: result.motion_summary.rotation_deg.toFixed(1), unit: "°" },
                { label: "DISPLACEMENT", value: result.motion_summary.displacement_px.toFixed(1), unit: "px" },
                { label: "CONTACT EVENTS", value: String(result.motion_summary.contact_events), unit: "" },
                { label: "SPEED", value: result.motion_summary.motion_speed_px_per_frame.toFixed(1), unit: "px/frame" },
                { label: "STATE CHANGE", value: result.motion_summary.state_change.replace(/_/g, " "), unit: "" },
                { label: "VERTICAL", value: result.motion_summary.vertical_motion, unit: "" },
                { label: "APPROACH SCORE", value: result.motion_summary.approach_score.toFixed(2), unit: "" },
                { label: "AREA CHANGE", value: result.motion_summary.area_change_ratio.toFixed(2), unit: "x" },
                { label: "CONTACT FREQ", value: result.motion_summary.contact_frequency, unit: "" },
                { label: "GRASP CHANGE", value: result.motion_summary.grasp_change.replace(/_/g, " "), unit: "" },
                { label: "AREA TREND", value: result.motion_summary.area_growth_trend.replace(/_/g, " "), unit: "" },
              ].map((stat, i) => (
                <div key={i} className="rounded-lg bg-[var(--fiba-glass)] p-4 border border-[var(--fiba-card-border)]" data-testid={`stat-${stat.label.toLowerCase().replace(/\s+/g, '-')}`}>
                  <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider mb-1">{stat.label}</div>
                  <div className="text-xl font-black text-white capitalize break-words">
                    {stat.value} <span className="text-sm text-white/50 lowercase font-normal">{stat.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Edge Profile */}
          <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
            <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-4">
              <FileText className="h-5 w-5 text-[var(--fiba-lavender)]" /> Edge Deployment Profile
            </h3>

            <div className="flex flex-wrap gap-2 mb-6">
              {result.edge_stats.edge_ready && (
                <span className="rounded border border-white/15 bg-white/6 px-2 py-1 text-xs font-medium text-white/60">Edge Ready</span>
              )}
              {result.edge_stats.zero_shot && (
                <span className="rounded border border-white/15 bg-white/6 px-2 py-1 text-xs font-medium text-white/60">Zero-Shot</span>
              )}
              <span className="rounded border border-white/15 bg-white/6 px-2 py-1 text-xs font-medium text-white/60">No Cloud</span>
              <span className="rounded border border-white/15 bg-white/6 px-2 py-1 text-xs font-medium text-white/60">Explainable</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-sm">
              {[
                { label: "Pipeline Latency", value: `${result.edge_stats.pipeline_latency_s.toFixed(2)}s` },
                { label: "Frame Processing", value: `${result.edge_stats.frame_processing_s.toFixed(3)}s` },
                { label: "Inference Latency", value: `${result.edge_stats.inference_latency_s.toFixed(3)}s` },
                { label: "Effective FPS", value: `${result.edge_stats.effective_fps.toFixed(1)} fps` },
                { label: "Frame Skip", value: String(result.edge_stats.frame_skip) },
                { label: "Resolution", value: result.edge_stats.resolution },
                { label: "Models Used", value: result.edge_stats.models_used },
              ].map((item, i) => (
                <div key={i}>
                  <div className="text-muted-foreground text-xs uppercase tracking-wider mb-1">{item.label}</div>
                  <div className="font-mono text-white text-xs break-words">{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Query Analysis & Meta */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
              <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-4">
                <ClipboardList className="h-5 w-5 text-[var(--fiba-teal)]" /> Query Analysis
              </h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div><span className="text-muted-foreground block text-xs">RAW</span><span className="text-white">{result.query_info.raw}</span></div>
                <div><span className="text-muted-foreground block text-xs">VERB</span><span className="text-white">{result.query_info.verb}</span></div>
                <div><span className="text-muted-foreground block text-xs">CATEGORY</span><span className="text-white">{result.query_info.category}</span></div>
                <div><span className="text-muted-foreground block text-xs">OBJECT</span><span className="text-white">{result.query_info.object}</span></div>
                <div><span className="text-muted-foreground block text-xs">TOOL</span><span className="text-white">{result.query_info.tool ?? "—"}</span></div>
              </div>
            </div>

            <div className="flex flex-col items-center justify-center p-6 space-y-6">
              <div className="text-center text-sm text-muted-foreground" data-testid="text-metadata">
                <div className="font-mono mb-1">{result.total_frames} frames · {result.fps} FPS</div>
                <div>processed in {result.processing_time_s.toFixed(2)}s</div>
              </div>
              <button
                onClick={resetAll}
                className="flex items-center gap-2 rounded-full border border-white/20 bg-transparent px-6 py-3 text-sm font-medium text-white hover:bg-white/10 transition-colors"
                data-testid="button-new-analysis"
              >
                <RefreshCw className="h-4 w-4" /> New Analysis
              </button>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

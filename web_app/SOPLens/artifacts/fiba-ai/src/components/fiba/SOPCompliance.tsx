import React, { useState, useEffect, useRef } from "react";
import { UploadCloud, CheckCircle2, AlertTriangle, RefreshCw, X, PlaySquare, ListChecks, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JobStatus, SOPStatus, SOPReferenceResult, SOPValidateResult } from "@/types/fiba";

interface SOPComplianceProps {
  onOpenLightbox: (src: string) => void;
}

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "An unexpected error occurred";
}

const SOP_STEPS = [
  { num: 1, title: "Placing white plastic part", desc: "Insert white base component" },
  { num: 2, title: "Placing black plastic part", desc: "Attach black casing part" },
  { num: 3, title: "Assembling the spring", desc: "Insert suspension spring" },
  { num: 4, title: "Screwing-1", desc: "Fasten first screw sequence" },
  { num: 5, title: "Inflating the valve", desc: "Inflate internal valve system" },
  { num: 6, title: "Screwing-2", desc: "Fasten final screw sequence" },
  { num: 7, title: "Fixing the cable", desc: "Route and fix power cable" },
];

export function SOPCompliance({ onOpenLightbox }: SOPComplianceProps) {
  const [sopStatus, setSopStatus] = useState<SOPStatus>({ has_reference: false, has_classifier: false });
  const [refFile, setRefFile] = useState<File | null>(null);
  const [testFile, setTestFile] = useState<File | null>(null);
  const [isDraggingRef, setIsDraggingRef] = useState(false);
  const [isDraggingTest, setIsDraggingTest] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [loadingType, setLoadingType] = useState<"reference" | "validate" | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [refJobResult, setRefJobResult] = useState<SOPReferenceResult | null>(null);
  const [validateResult, setValidateResult] = useState<SOPValidateResult | null>(null);

  const refInputRef = useRef<HTMLInputElement>(null);
  const testInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      if (pollIntervalRef.current !== null) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const fetchStatus = async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
      const res = await fetch(`${baseUrl}/api/sop/status`);
      if (res.ok) {
        const data = await res.json() as SOPStatus;
        setSopStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch SOP status", e);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handlePoll = (jobId: string): Promise<JobStatus> => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "";

    return new Promise<JobStatus>((resolve, reject) => {
      eventSourceRef.current?.close();

      const eventSource = new EventSource(`${baseUrl}/api/stream/${jobId}`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data) as { progress: number; message: string; done: boolean; error?: string };
        if (data.error) {
          eventSource.close();
          eventSourceRef.current = null;
          reject(new Error(data.error));
          return;
        }
        setProgress(data.progress);
        setProgressMsg(data.message);

        if (data.done) {
          eventSource.close();
          eventSourceRef.current = null;
          fetch(`${baseUrl}/api/status/${jobId}`)
            .then(r => r.json() as Promise<JobStatus>)
            .then(resolve)
            .catch(reject);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        eventSourceRef.current = null;

        const interval = setInterval(() => {
          fetch(`${baseUrl}/api/status/${jobId}`)
            .then(r => r.json() as Promise<JobStatus>)
            .then((d) => {
              setProgress(d.progress);
              setProgressMsg(d.message);
              if (d.done) {
                clearInterval(interval);
                pollIntervalRef.current = null;
                if (d.error) reject(new Error(d.error));
                else resolve(d);
              }
            })
            .catch((err: unknown) => {
              clearInterval(interval);
              pollIntervalRef.current = null;
              reject(err instanceof Error ? err : new Error(getErrorMessage(err)));
            });
        }, 800);
        pollIntervalRef.current = interval;
      };
    });
  };

  const handleLearnReference = async () => {
    if (!refFile) return;

    setIsLoading(true);
    setLoadingType("reference");
    setError(null);
    setProgress(0);
    setProgressMsg("Uploading reference...");
    setValidateResult(null);

    const formData = new FormData();
    formData.append("video", refFile);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
      const res = await fetch(`${baseUrl}/api/sop/reference`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json() as { error?: string };
        throw new Error(body.error || "Failed to upload reference");
      }

      const { job_id } = await res.json() as { job_id: string };
      const statusData = await handlePoll(job_id);

      if (statusData.result && "type" in statusData.result && statusData.result.type === "sop_reference") {
        setRefJobResult(statusData.result as SOPReferenceResult);
        await fetchStatus();
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
      setLoadingType(null);
    }
  };

  const handleValidate = async () => {
    if (!testFile) return;

    setIsLoading(true);
    setLoadingType("validate");
    setError(null);
    setProgress(0);
    setProgressMsg("Analyzing test video...");
    setValidateResult(null);

    const formData = new FormData();
    formData.append("video", testFile);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
      const res = await fetch(`${baseUrl}/api/sop/validate`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json() as { error?: string };
        throw new Error(body.error || "Failed to start validation");
      }

      const { job_id } = await res.json() as { job_id: string };
      const statusData = await handlePoll(job_id);

      if (statusData.result && "type" in statusData.result && statusData.result.type === "sop_validate") {
        setValidateResult(statusData.result as SOPValidateResult);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
      setLoadingType(null);
    }
  };

  const handleDropRef = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingRef(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("video/")) setRefFile(file);
  };

  const handleDropTest = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingTest(false);
    if (!isReferenceLearned) return;
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("video/")) setTestFile(file);
  };

  const formatSize = (bytes: number) => (bytes / (1024 * 1024)).toFixed(2) + " MB";

  const isReferenceLearned = sopStatus.has_reference || sopStatus.has_classifier || refJobResult !== null;

  const sopStatusInfo = (): { text: string; color: string; borderClass: string; bgClass: string } => {
    if (sopStatus.has_classifier) {
      return {
        text: "Trained classifier ready — you can validate any test video.",
        color: "text-green-400",
        borderClass: "border-green-500/30",
        bgClass: "bg-green-500/10",
      };
    }
    if (sopStatus.has_reference) {
      return {
        text: "Reference loaded, ready to validate.",
        color: "text-white/60",
        borderClass: "border-white/15",
        bgClass: "bg-white/5",
      };
    }
    return {
      text: "Upload reference video first to start SOP validation.",
      color: "text-muted-foreground",
      borderClass: "border-[var(--fiba-card-border)]",
      bgClass: "bg-[var(--fiba-card)]",
    };
  };

  const statusInfo = sopStatusInfo();

  return (
    <div className="w-full max-w-6xl mx-auto px-4 pb-20 space-y-8 animate-in fade-in duration-500">

      {/* SOP Status Banner */}
      <div
        className={cn("flex items-center gap-3 rounded-xl border px-5 py-3 text-sm font-medium", statusInfo.borderClass, statusInfo.bgClass)}
        role="status"
        aria-live="polite"
        data-testid="sop-status-banner"
      >
        <Info className={cn("h-4 w-4 shrink-0", statusInfo.color)} aria-hidden="true" />
        <span className={statusInfo.color}>{statusInfo.text}</span>
      </div>

      {/* Segment Count (after reference is learned) */}
      {refJobResult && (
        <div
          className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-5 py-3 text-sm"
          role="status"
          aria-live="polite"
          data-testid="segment-count-banner"
        >
          <CheckCircle2 className="h-4 w-4 text-white/60 shrink-0" aria-hidden="true" />
          <span className="text-white">
            Reference learned: <strong className="text-[var(--fiba-lavender)]">{refJobResult.segment_count} steps</strong> identified · {refJobResult.total_frames} frames @ {refJobResult.fps} FPS · {refJobResult.processing_time_s.toFixed(2)}s
          </span>
        </div>
      )}

      {/* Main Layout: Timeline + Upload zones */}
      {!validateResult && !isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* Vertical SOP Timeline */}
          <div className="lg:col-span-1 rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-6 backdrop-blur-sm">
            <h3 className="flex items-center gap-2 text-lg font-bold text-white mb-6">
              <ListChecks className="h-5 w-5 text-white/50" aria-hidden="true" /> SOP Procedure
            </h3>

            <ol aria-label="Standard operating procedure steps" className="relative space-y-0">
              {SOP_STEPS.map((step, i) => (
                <li key={step.num} className="relative flex gap-4 pb-6 last:pb-0">
                  {i < SOP_STEPS.length - 1 && (
                    <div
                      className="absolute left-4 top-8 bottom-0 w-px bg-gradient-to-b from-white/20 to-transparent"
                      aria-hidden="true"
                    />
                  )}
                  <div className={cn(
                    "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors",
                    isReferenceLearned
                      ? "border-white/50 bg-white text-black"
                      : "border-white/20 bg-[var(--fiba-glass)] text-muted-foreground"
                  )}>
                    {step.num}
                  </div>
                  <div className="mt-0.5 min-w-0">
                    <p className={cn("text-sm font-semibold leading-tight", isReferenceLearned ? "text-white" : "text-white/80")}>
                      {step.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">{step.desc}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          {/* Upload Panels */}
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">

            {/* 1. Reference Upload */}
            <div className="flex flex-col gap-3">
              <h4 className="text-sm font-bold text-white uppercase tracking-wider">1. Set Reference Video</h4>
              <div
                className={cn(
                  "relative flex-1 rounded-xl border-2 border-dashed p-8 text-center flex flex-col items-center justify-center transition-colors backdrop-blur-sm min-h-[240px]",
                  isDraggingRef ? "border-white/40 bg-white/8" :
                  refFile ? "border-white/20 bg-white/4" :
                  "border-[var(--fiba-card-border)] bg-[var(--fiba-card)]"
                )}
                onDragOver={(e) => { e.preventDefault(); setIsDraggingRef(true); }}
                onDragLeave={() => setIsDraggingRef(false)}
                onDrop={handleDropRef}
                aria-label="Reference video upload area — drag and drop or browse"
                data-testid="ref-upload-zone"
              >
                <input
                  type="file"
                  ref={refInputRef}
                  className="hidden"
                  accept="video/*"
                  aria-label="Select reference video file"
                  onChange={(e) => { if (e.target.files?.[0]) setRefFile(e.target.files[0]); }}
                />

                {isReferenceLearned && !refFile ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="rounded-full bg-green-500/20 p-3 text-green-400">
                      <CheckCircle2 className="h-8 w-8" aria-hidden="true" />
                    </div>
                    <p className="text-sm font-bold text-white">Reference Learned</p>
                    {refJobResult && (
                      <p className="text-xs text-[var(--fiba-lavender)] font-medium">{refJobResult.segment_count} steps learned</p>
                    )}
                    <p className="text-xs text-muted-foreground">Ready for validation</p>
                    <button
                      onClick={() => refInputRef.current?.click()}
                      aria-label="Upload a new reference video"
                      className="mt-3 text-xs text-white/40 hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-white/30 rounded"
                    >
                      Upload new reference
                    </button>
                  </div>
                ) : refFile ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="rounded-full bg-white/10 p-3 text-white/70">
                      <PlaySquare className="h-8 w-8" aria-hidden="true" />
                    </div>
                    <p className="text-sm font-medium text-white truncate max-w-[200px]">{refFile.name}</p>
                    <p className="text-xs text-muted-foreground">{formatSize(refFile.size)}</p>
                    <button
                      onClick={handleLearnReference}
                      aria-label="Start learning reference video"
                      className="mt-3 w-full rounded-lg bg-white px-4 py-2 text-sm font-bold text-black shadow-md hover:bg-white/90 transition-colors focus:outline-none focus:ring-2 focus:ring-white/30"
                      data-testid="button-learn-reference"
                    >
                      Learn Reference
                    </button>
                    <button
                      onClick={() => setRefFile(null)}
                      aria-label="Cancel reference file selection"
                      className="mt-1 text-xs text-muted-foreground hover:text-white flex items-center gap-1 focus:outline-none"
                    >
                      <X className="h-3 w-3" aria-hidden="true" /> Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <div className="rounded-full bg-[var(--fiba-glass)] p-4 text-muted-foreground">
                      <UploadCloud className="h-8 w-8" aria-hidden="true" />
                    </div>
                    <p className="text-sm text-muted-foreground">Drag & drop or browse</p>
                    <p className="text-xs text-muted-foreground/60">Upload correct procedure video</p>
                    <button
                      onClick={() => refInputRef.current?.click()}
                      aria-label="Browse for reference video file"
                      className="mt-2 rounded-md bg-[var(--fiba-glass)] px-4 py-2 text-sm font-medium text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/30"
                      data-testid="button-browse-ref"
                    >
                      Browse video
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* 2. Test Upload */}
            <div className="flex flex-col gap-3">
              <h4 className="text-sm font-bold text-white uppercase tracking-wider">2. Validate Test Video</h4>
              <div
                className={cn(
                  "relative flex-1 rounded-xl border-2 border-dashed p-8 text-center flex flex-col items-center justify-center transition-colors backdrop-blur-sm min-h-[240px]",
                  !isReferenceLearned && "opacity-50 grayscale pointer-events-none",
                  isDraggingTest ? "border-white/40 bg-white/8" :
                  testFile ? "border-white/20 bg-white/4" :
                  "border-[var(--fiba-card-border)] bg-[var(--fiba-card)]"
                )}
                onDragOver={(e) => { e.preventDefault(); if (isReferenceLearned) setIsDraggingTest(true); }}
                onDragLeave={() => setIsDraggingTest(false)}
                onDrop={handleDropTest}
                aria-label={isReferenceLearned ? "Test video upload area — drag and drop or browse" : "Set reference video first"}
                aria-disabled={!isReferenceLearned}
                data-testid="test-upload-zone"
              >
                <input
                  type="file"
                  ref={testInputRef}
                  className="hidden"
                  accept="video/*"
                  aria-label="Select test video file"
                  onChange={(e) => { if (e.target.files?.[0]) setTestFile(e.target.files[0]); }}
                />

                {testFile ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="rounded-full bg-white/10 p-3 text-white/70">
                      <PlaySquare className="h-8 w-8" aria-hidden="true" />
                    </div>
                    <p className="text-sm font-medium text-white truncate max-w-[200px]">{testFile.name}</p>
                    <p className="text-xs text-muted-foreground">{formatSize(testFile.size)}</p>
                    <button
                      onClick={handleValidate}
                      disabled={!isReferenceLearned}
                      aria-label="Start validating test video against reference"
                      className="mt-3 w-full rounded-lg bg-white px-4 py-2 text-sm font-bold text-black shadow-md disabled:opacity-40 hover:bg-white/90 transition-colors focus:outline-none focus:ring-2 focus:ring-white/30"
                      data-testid="button-validate"
                    >
                      Validate Video
                    </button>
                    <button
                      onClick={() => setTestFile(null)}
                      aria-label="Cancel test file selection"
                      className="mt-1 text-xs text-muted-foreground hover:text-white flex items-center gap-1 focus:outline-none"
                    >
                      <X className="h-3 w-3" aria-hidden="true" /> Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <div className="rounded-full bg-[var(--fiba-glass)] p-4 text-muted-foreground">
                      <UploadCloud className="h-8 w-8" aria-hidden="true" />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {isReferenceLearned ? "Drag & drop or browse" : "Set reference first"}
                    </p>
                    <p className="text-xs text-muted-foreground/60">Upload test procedure video</p>
                    <button
                      onClick={() => testInputRef.current?.click()}
                      disabled={!isReferenceLearned}
                      aria-label="Browse for test video file"
                      className="mt-2 rounded-md bg-[var(--fiba-glass)] px-4 py-2 text-sm font-medium text-white hover:bg-white/10 transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-white/30"
                      data-testid="button-browse-test"
                    >
                      Browse test video
                    </button>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Loading Progress */}
      {isLoading && (
        <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] p-8 shadow-xl backdrop-blur-md animate-in slide-in-from-bottom-4">
          <div className="flex items-center gap-4 mb-8">
            <div className="relative h-10 w-10">
              <svg className="h-full w-full animate-spin text-white/40" viewBox="0 0 24 24" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">
                {loadingType === "reference" ? "Learning Reference..." : "Validating Procedure..."}
              </h3>
              <p className="text-sm text-muted-foreground">{progressMsg}</p>
            </div>
            <div className="ml-auto text-3xl font-black text-white/50" aria-label={`${progress}% complete`}>{progress}%</div>
          </div>
          <div
            className="h-2 w-full overflow-hidden rounded-full bg-[var(--fiba-glass)]"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Processing progress"
          >
            <div
              className={cn(
                "h-full transition-all duration-300 ease-out",
                loadingType === "reference"
                  ? "bg-white/70"
                  : "bg-white/70"
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 flex flex-col items-center justify-center text-center animate-in slide-in-from-bottom-4" role="alert">
          <div className="rounded-full bg-red-500/20 p-3 text-red-500 mb-4">
            <AlertTriangle className="h-8 w-8" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Pipeline Error</h3>
          <p className="text-sm text-red-200 mb-6" data-testid="text-error">{error}</p>
          <button
            onClick={() => setError(null)}
            aria-label="Dismiss error and try again"
            className="rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20 transition-colors focus:outline-none focus:ring-2 focus:ring-white/30"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Validate Results */}
      {validateResult && !isLoading && (
        <div className="space-y-6 animate-in slide-in-from-bottom-8 duration-700">

          {/* Verdict Banner */}
          <div
            className={cn(
              "relative overflow-hidden rounded-2xl border p-8 flex flex-col items-center text-center justify-center",
              validateResult.passed
                ? "border-green-500/30 bg-gradient-to-br from-green-500/20 to-[var(--fiba-bg)]"
                : "border-red-500/30 bg-gradient-to-br from-red-500/20 to-[var(--fiba-bg)]"
            )}
            role="status"
            aria-live="polite"
            data-testid="sop-verdict-banner"
          >
            <div className="text-6xl mb-4" aria-hidden="true">{validateResult.passed ? "✅" : "⚠️"}</div>
            <h2 className={cn("text-3xl font-black mb-2", validateResult.passed ? "text-green-400" : "text-red-400")}>
              {validateResult.passed ? "✓ PASS — SOP Compliance Verified" : "✗ FAIL — SOP Violation Detected"}
            </h2>
            <p className="text-white/80 max-w-2xl">{validateResult.summary}</p>
            <p className="mt-4 text-sm text-muted-foreground font-mono">
              {validateResult.total_frames} frames · {validateResult.fps} FPS · {validateResult.processing_time_s.toFixed(2)}s
            </p>
          </div>

          {/* Step-by-Step */}
          <div className="rounded-xl border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] overflow-hidden backdrop-blur-sm">
            <div className="p-6 border-b border-[var(--fiba-card-border)]">
              <h3 className="text-lg font-bold text-white">Step-by-Step Analysis</h3>
            </div>
            <ol className="divide-y divide-[var(--fiba-card-border)]" aria-label="Step-by-step SOP results">
              {validateResult.step_results.map((step, idx) => (
                <li key={idx} className="p-6 flex flex-col md:flex-row gap-6 items-start md:items-center" data-testid={`sop-step-${idx}`}>
                  <div className="flex items-center gap-4 shrink-0 min-w-[200px]">
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-full text-lg shadow-sm shrink-0",
                        step.is_correct
                          ? "bg-green-500/20 text-green-400 border border-green-500/30"
                          : "bg-red-500/20 text-red-400 border border-red-500/30"
                      )}
                      aria-label={step.is_correct ? "Correct" : "Incorrect"}
                    >
                      {step.is_correct ? "✓" : "✗"}
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider mb-1">Step {step.position}</div>
                      <div className={cn("font-bold text-sm", step.is_correct ? "text-white" : "text-red-400")}>
                        {step.detected_task.replace(/_/g, " ")}
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 w-full space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">
                        Expected: <span className="text-white">{step.expected_task.replace(/_/g, " ")}</span>
                      </span>
                      <span className="text-white font-mono">{Math.round(step.similarity * 100)}% Match</span>
                    </div>
                    <div
                      className="h-2 w-full rounded-full bg-[var(--fiba-glass)] overflow-hidden"
                      role="meter"
                      aria-valuenow={Math.round(step.similarity * 100)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${Math.round(step.similarity * 100)}% similarity`}
                    >
                      <div
                        className={cn(
                          "h-full rounded-full",
                          step.similarity > 0.7 ? "bg-green-500" :
                          step.similarity > 0.4 ? "bg-yellow-500" : "bg-red-500"
                        )}
                        style={{ width: `${Math.max(0, Math.min(100, step.similarity * 100))}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex gap-2 shrink-0">
                    <div
                      role="button"
                      tabIndex={0}
                      aria-label={`Open keyframe for step ${step.position} in lightbox`}
                      className="h-16 w-24 rounded border border-white/10 overflow-hidden cursor-pointer bg-black focus:outline-none focus:ring-2 focus:ring-[var(--fiba-purple)]"
                      onClick={() => onOpenLightbox(`data:image/jpeg;base64,${step.keyframe_b64}`)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenLightbox(`data:image/jpeg;base64,${step.keyframe_b64}`); }}
                    >
                      <img src={`data:image/jpeg;base64,${step.keyframe_b64}`} className="w-full h-full object-cover hover:opacity-80 transition-opacity" alt={`Step ${step.position} keyframe`} loading="lazy" />
                    </div>
                    <div
                      role="button"
                      tabIndex={0}
                      aria-label={`Open skeleton for step ${step.position} in lightbox`}
                      className="h-16 w-24 rounded border border-white/10 overflow-hidden cursor-pointer bg-black focus:outline-none focus:ring-2 focus:ring-[var(--fiba-purple)]"
                      onClick={() => onOpenLightbox(`data:image/jpeg;base64,${step.skeleton_b64}`)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenLightbox(`data:image/jpeg;base64,${step.skeleton_b64}`); }}
                    >
                      <img src={`data:image/jpeg;base64,${step.skeleton_b64}`} className="w-full h-full object-cover hover:opacity-80 transition-opacity" alt={`Step ${step.position} skeleton`} loading="lazy" />
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="flex justify-center p-4">
            <button
              onClick={() => { setTestFile(null); setValidateResult(null); }}
              aria-label="Validate another video"
              className="flex items-center gap-2 rounded-full border border-white/20 bg-transparent px-6 py-3 text-sm font-medium text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/30"
              data-testid="button-validate-another"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" /> Validate Another Video
            </button>
          </div>

        </div>
      )}
    </div>
  );
}

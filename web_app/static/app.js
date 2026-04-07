/**
 * FIBA AI — Frontend Logic
 * ========================
 * Modes: Action Search + SOP Compliance Validation
 * Hand skeleton visualization + finger trajectory rendering
 */
(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ─── Mode state ─────────────────────────────────────────
  let currentMode = "action"; // "action" | "sop"

  // ─── Action Search elements ─────────────────────────────
  const dropZone = $("#drop-zone"), videoInput = $("#video-input");
  const browseLink = $("#browse-link"), uploadIcon = $("#upload-icon");
  const uploadText = $("#upload-text"), filePreview = $("#file-preview");
  const fileName = $("#file-name"), fileSize = $("#file-size");
  const fileClear = $("#file-clear"), queryInput = $("#query-input");
  const processBtn = $("#process-btn"), exampleChips = $$(".example-chip");

  const uploadSection = $("#upload-section"), progressSection = $("#progress-section");
  const resultsSection = $("#results-section"), errorSection = $("#error-section");
  const progressBar = $("#progress-bar"), progressPct = $("#progress-pct");
  const progressMsg = $("#progress-msg");

  const lightbox = $("#lightbox"), lightboxImg = $("#lightbox-img");
  const lightboxClose = $("#lightbox-close");
  const newAnalysisBtn = $("#new-analysis-btn"), errorRetryBtn = $("#error-retry-btn");

  // ─── SOP elements ──────────────────────────────────────
  const sopSection = $("#sop-section");
  const sopRefInput = $("#sop-ref-input"), sopTestInput = $("#sop-test-input");
  const sopRefBtn = $("#sop-ref-btn"), sopTestBtn = $("#sop-test-btn");
  const sopRefZone = $("#sop-ref-zone"), sopTestZone = $("#sop-test-zone");
  const sopRefClear = $("#sop-ref-clear"), sopTestClear = $("#sop-test-clear");
  const sopProgress = $("#sop-progress"), sopResults = $("#sop-results");

  let selectedFile = null;
  let sopRefFile = null, sopTestFile = null;
  let sopReferenceLoaded = false;
  let hasClassifier = false;

  // ─── Mode Tabs ─────────────────────────────────────────

  $$(".mode-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      currentMode = tab.dataset.mode;
      $$(".mode-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      if (currentMode === "action") {
        uploadSection.hidden = false;
        sopSection.hidden = true;
        // Also show hero
        const hero = $("#hero-section");
        if (hero) hero.hidden = false;
      } else {
        uploadSection.hidden = true;
        sopSection.hidden = false;
        progressSection.hidden = true;
        resultsSection.hidden = true;
        errorSection.hidden = true;
        const hero = $("#hero-section");
        if (hero) hero.hidden = false;
      }
    });
  });

  // ─── File (Action mode) ────────────────────────────────

  function selectFile(file) {
    if (!file || !file.type.startsWith("video/")) { alert("Please select a video file."); return; }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    filePreview.hidden = false;
    uploadIcon.style.display = "none";
    uploadText.style.display = "none";
    $(".upload-hint").style.display = "none";
    dropZone.classList.add("has-file");
    updateBtn();
  }

  function clearFile() {
    selectedFile = null; videoInput.value = "";
    filePreview.hidden = true;
    uploadIcon.style.display = ""; uploadText.style.display = "";
    $(".upload-hint").style.display = "";
    dropZone.classList.remove("has-file");
    updateBtn();
  }

  function updateBtn() { processBtn.disabled = !(selectedFile && queryInput.value.trim()); }
  function formatBytes(b) { return b < 1024 ? b+" B" : b < 1048576 ? (b/1024).toFixed(1)+" KB" : (b/1048576).toFixed(1)+" MB"; }

  browseLink.addEventListener("click", e => { e.preventDefault(); videoInput.click(); });
  videoInput.addEventListener("change", () => { if (videoInput.files[0]) selectFile(videoInput.files[0]); });
  fileClear.addEventListener("click", e => { e.stopPropagation(); clearFile(); });
  dropZone.addEventListener("click", e => { if (!e.target.closest(".file-preview,.file-clear") && !selectedFile) videoInput.click(); });
  ["dragenter","dragover"].forEach(t => dropZone.addEventListener(t, e => { e.preventDefault(); dropZone.classList.add("drag-over"); }));
  ["dragleave","drop"].forEach(t => dropZone.addEventListener(t, e => { e.preventDefault(); dropZone.classList.remove("drag-over"); }));
  dropZone.addEventListener("drop", e => { if (e.dataTransfer.files[0]) selectFile(e.dataTransfer.files[0]); });
  queryInput.addEventListener("input", updateBtn);
  queryInput.addEventListener("keydown", e => { if (e.key === "Enter" && !processBtn.disabled) startProcessing(); });
  exampleChips.forEach(c => c.addEventListener("click", () => { queryInput.value = c.dataset.query; updateBtn(); queryInput.focus(); }));

  // ─── Action Processing ─────────────────────────────────

  processBtn.addEventListener("click", startProcessing);

  async function startProcessing() {
    if (!selectedFile || !queryInput.value.trim()) return;
    showSection("progress");
    const fd = new FormData();
    fd.append("video", selectedFile);
    fd.append("query", queryInput.value.trim());
    try {
      const resp = await fetch("/api/process", { method: "POST", body: fd });
      if (!resp.ok) throw new Error((await resp.json()).error || "Upload failed");
      const data = await resp.json();
      pollProgress(data.job_id);
    } catch (err) { showError(err.message); }
  }

  function pollProgress(jobId) {
    const es = new EventSource(`/api/stream/${jobId}`);
    es.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        if (d.error) { es.close(); showError(d.error); return; }
        updateProgress(d.progress, d.message);
        if (d.done) { es.close(); fetchResult(jobId); }
      } catch(e) {}
    };
    es.onerror = () => { es.close(); pollFallback(jobId); };
  }

  async function pollFallback(jobId) {
    const iv = setInterval(async () => {
      try {
        const d = (await (await fetch(`/api/status/${jobId}`)).json());
        updateProgress(d.progress, d.message);
        if (d.done) { clearInterval(iv); d.error ? showError(d.error) : d.result ? renderResults(d.result) : showError("No result"); }
      } catch(e) { clearInterval(iv); showError("Connection lost"); }
    }, 800);
  }

  async function fetchResult(jobId) {
    try {
      const d = (await (await fetch(`/api/status/${jobId}`)).json());
      d.error ? showError(d.error) : d.result ? renderResults(d.result) : showError("No result");
    } catch(e) { showError("Failed to fetch results"); }
  }

  // ─── Progress ──────────────────────────────────────────

  function updateProgress(pct, msg) {
    progressBar.style.width = pct + "%";
    progressPct.textContent = pct + "%";
    progressMsg.textContent = msg || "";
    [{ id:"stage-parse",min:0,max:15 },{ id:"stage-detect",min:15,max:45 },
     { id:"stage-track",min:45,max:72 },{ id:"stage-infer",min:72,max:85 },
     { id:"stage-render",min:85,max:100 }].forEach(s => {
      const el = $(`#${s.id}`);
      el.className = pct >= s.max ? "stage done" : pct >= s.min ? "stage active" : "stage";
    });
  }

  // ─── Results ───────────────────────────────────────────

  function renderResults(r) {
    showSection("results");

    // Banner
    const banner = $("#result-banner");
    if (r.action_detected) {
      banner.className = "result-banner detected";
      $("#banner-icon").textContent = "✅";
      $("#banner-title").textContent = "Action Detected";
      $("#banner-title").style.color = "var(--success)";
    } else {
      banner.className = "result-banner not-detected";
      $("#banner-icon").textContent = "❌";
      $("#banner-title").textContent = "Not Detected";
      $("#banner-title").style.color = "var(--error)";
    }
    $("#banner-subtitle").textContent = `"${r.query_info.raw}" → ${r.action_label} (${r.action_category})`;

    // Confidence ring
    const pct = Math.round(r.confidence * 100);
    $("#confidence-value").textContent = pct + "%";
    const circ = 2 * Math.PI * 35;
    const circle = $("#confidence-circle");
    circle.style.strokeDasharray = circ;
    requestAnimationFrame(() => {
      circle.style.transition = "stroke-dashoffset 1s ease";
      circle.style.strokeDashoffset = circ - r.confidence * circ;
    });
    circle.style.stroke = r.action_detected ? "var(--success)" : "var(--error)";
    $("#confidence-value").style.color = r.action_detected ? "var(--success)" : "var(--error)";

    // Description
    const desc = $("#description-text");
    desc.innerHTML = (r.action_description || "").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    // Evidence
    $("#evidence-text").textContent = r.evidence || "No evidence.";

    // Key frames
    const kfGrid = $("#keyframes-grid");
    kfGrid.innerHTML = "";
    (r.key_frames || []).forEach((b64, i) => {
      const item = document.createElement("div");
      item.className = "keyframe-item";
      item.innerHTML = `<img src="data:image/jpeg;base64,${b64}" alt="Key frame ${i+1}" loading="lazy"/><div class="keyframe-label">Key Frame ${i+1}</div>`;
      item.addEventListener("click", () => openLightbox(b64));
      kfGrid.appendChild(item);
    });

    // Hand skeleton frames
    const skGrid = $("#skeleton-grid");
    skGrid.innerHTML = "";
    const skCard = $("#skeleton-card");
    if (r.skeleton_frames && r.skeleton_frames.length > 0) {
      skCard.hidden = false;
      r.skeleton_frames.forEach((b64, i) => {
        const item = document.createElement("div");
        item.className = "keyframe-item";
        item.innerHTML = `<img src="data:image/jpeg;base64,${b64}" alt="Skeleton ${i+1}" loading="lazy"/><div class="keyframe-label">Skeleton ${i+1}</div>`;
        item.addEventListener("click", () => openLightbox(b64));
        skGrid.appendChild(item);
      });
    } else {
      skCard.hidden = true;
    }

    // Finger trajectory
    const ftCard = $("#finger-traj-card");
    if (r.finger_trajectory) {
      ftCard.hidden = false;
      $("#finger-traj-img").src = `data:image/jpeg;base64,${r.finger_trajectory}`;
    } else {
      ftCard.hidden = true;
    }

    // Object trajectory
    if (r.trajectory) {
      $("#trajectory-img").src = `data:image/jpeg;base64,${r.trajectory}`;
      $("#trajectory-card").hidden = false;
    } else { $("#trajectory-card").hidden = true; }

    // Motion stats
    renderStats($("#stats-grid"), r.motion_summary, [
      { label:"Rotation", key:"rotation_deg", unit:"°" },
      { label:"Displacement", key:"displacement_px", unit:"px" },
      { label:"Contact Events", key:"contact_events", unit:"" },
      { label:"Area Change", key:"area_change_ratio", unit:"×" },
      { label:"State Change", key:"state_change", unit:"" },
      { label:"Vertical Motion", key:"vertical_motion", unit:"" },
      { label:"Motion Speed", key:"motion_speed_px_per_frame", unit:"px/f" },
      { label:"Contact Freq", key:"contact_frequency", unit:"" },
      { label:"Approach Score", key:"approach_score", unit:"" },
      { label:"Grasp Change", key:"grasp_change", unit:"" },
      { label:"Area Growth", key:"area_growth_trend", unit:"" },
    ]);

    // Edge deployment stats
    renderEdgeStats(r.edge_stats);

    // Query info
    const qGrid = $("#query-detail-grid");
    qGrid.innerHTML = "";
    [{ l:"Query",v:r.query_info.raw },{ l:"Verb",v:r.query_info.verb },
     { l:"Category",v:r.query_info.category },{ l:"Object",v:r.query_info.object },
     { l:"Tool",v:r.query_info.tool||"—" }].forEach(f => {
      const d = document.createElement("div");
      d.className = "query-detail-item";
      d.innerHTML = `<div class="query-detail-label">${f.l}</div><div class="query-detail-value">${f.v}</div>`;
      qGrid.appendChild(d);
    });

    // Meta
    const meta = [];
    if (r.total_frames) meta.push(`${r.total_frames} frames`);
    if (r.fps) meta.push(`${r.fps.toFixed(1)} FPS`);
    if (r.processing_time_s) meta.push(`processed in ${r.processing_time_s}s`);
    $("#result-meta").textContent = meta.join(" · ");

    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderStats(grid, data, defs) {
    grid.innerHTML = "";
    if (!data) return;
    defs.forEach(d => {
      const v = data[d.key];
      if (v == null) return;
      const el = document.createElement("div");
      el.className = "stat-item";
      el.innerHTML = `<div class="stat-label">${d.label}</div><div class="stat-value">${typeof v==="number"?v.toFixed(1):v}<span class="stat-unit">${d.unit}</span></div>`;
      grid.appendChild(el);
    });
  }

  function renderEdgeStats(stats) {
    const badgesEl = $("#edge-badges");
    const grid = $("#edge-stats-grid");
    badgesEl.innerHTML = "";
    grid.innerHTML = "";
    if (!stats) return;

    const badges = [
      { label: "Edge Ready", active: stats.edge_ready, icon: "📱" },
      { label: "Zero-Shot", active: stats.zero_shot, icon: "🎯" },
      { label: "No Cloud", active: true, icon: "🔒" },
      { label: "Explainable", active: true, icon: "💡" },
    ];
    badges.forEach(b => {
      const el = document.createElement("span");
      el.className = "edge-badge" + (b.active ? " active" : "");
      el.textContent = `${b.icon} ${b.label}`;
      badgesEl.appendChild(el);
    });

    const items = [
      { label: "Pipeline Latency", value: stats.pipeline_latency_s + "s" },
      { label: "Frame Processing", value: stats.frame_processing_s + "s" },
      { label: "Inference", value: stats.inference_latency_s + "s" },
      { label: "Effective FPS", value: stats.effective_fps },
      { label: "Processed Frames", value: `${stats.processed_frames}/${stats.total_frames}` },
      { label: "Frame Skip", value: `every ${stats.frame_skip}${stats.frame_skip > 1 ? " (adaptive)" : ""}` },
      { label: "Resolution", value: stats.resolution },
      { label: "Models", value: stats.models_used },
    ];
    items.forEach(s => {
      const el = document.createElement("div");
      el.className = "stat-item";
      el.innerHTML = `<div class="stat-label">${s.label}</div><div class="stat-value edge-stat-value">${s.value}</div>`;
      grid.appendChild(el);
    });
  }

  // ═══════════════════════════════════════════════════════
  // SOP COMPLIANCE MODE
  // ═══════════════════════════════════════════════════════

  function setupSOPDropZone(zone, input, fileEl, nameEl, clearBtn, assignFn) {
    zone.addEventListener("click", e => {
      if (!e.target.closest(".file-clear")) input.click();
    });
    input.addEventListener("change", () => {
      if (input.files[0]) assignFn(input.files[0]);
    });
    ["dragenter","dragover"].forEach(t => zone.addEventListener(t, e => { e.preventDefault(); zone.classList.add("drag-over"); }));
    ["dragleave","drop"].forEach(t => zone.addEventListener(t, e => { e.preventDefault(); zone.classList.remove("drag-over"); }));
    zone.addEventListener("drop", e => { if (e.dataTransfer.files[0]) assignFn(e.dataTransfer.files[0]); });
    clearBtn.addEventListener("click", e => { e.stopPropagation(); assignFn(null); });
  }

  function selectSOPRef(file) {
    sopRefFile = file;
    if (file) {
      $("#sop-ref-name").textContent = file.name;
      $("#sop-ref-file").hidden = false;
      $("#sop-ref-content").hidden = true;
      sopRefBtn.disabled = false;
    } else {
      sopRefInput.value = "";
      $("#sop-ref-file").hidden = true;
      $("#sop-ref-content").hidden = false;
      sopRefBtn.disabled = true;
    }
  }

  function selectSOPTest(file) {
    sopTestFile = file;
    if (file) {
      $("#sop-test-name").textContent = file.name;
      $("#sop-test-file").hidden = false;
      $("#sop-test-content").hidden = true;
      sopTestBtn.disabled = !(sopReferenceLoaded || hasClassifier);
    } else {
      sopTestInput.value = "";
      $("#sop-test-file").hidden = true;
      $("#sop-test-content").hidden = false;
      sopTestBtn.disabled = true;
    }
  }

  setupSOPDropZone(sopRefZone, sopRefInput, $("#sop-ref-file"), $("#sop-ref-name"), sopRefClear, selectSOPRef);
  setupSOPDropZone(sopTestZone, sopTestInput, $("#sop-test-file"), $("#sop-test-name"), sopTestClear, selectSOPTest);

  // ─── SOP Reference ────────────────────────────────────

  sopRefBtn.addEventListener("click", async () => {
    if (!sopRefFile) return;
    sopRefBtn.disabled = true;
    sopRefBtn.querySelector(".btn-text").textContent = "Learning...";
    sopProgress.hidden = false;
    sopResults.hidden = true;

    const fd = new FormData();
    fd.append("video", sopRefFile);

    try {
      const resp = await fetch("/api/sop/reference", { method: "POST", body: fd });
      if (!resp.ok) throw new Error((await resp.json()).error || "Upload failed");
      const data = await resp.json();
      pollSOPJob(data.job_id, "reference");
    } catch (err) {
      sopRefBtn.disabled = false;
      sopRefBtn.querySelector(".btn-text").textContent = "Learn Reference";
      alert("Error: " + err.message);
    }
  });

  // ─── SOP Validate ─────────────────────────────────────

  sopTestBtn.addEventListener("click", async () => {
    if (!sopTestFile || !sopReferenceLoaded) return;
    sopTestBtn.disabled = true;
    sopTestBtn.querySelector(".btn-text").textContent = "Validating...";
    sopProgress.hidden = false;
    sopResults.hidden = true;

    const fd = new FormData();
    fd.append("video", sopTestFile);

    try {
      const resp = await fetch("/api/sop/validate", { method: "POST", body: fd });
      if (!resp.ok) throw new Error((await resp.json()).error || "Upload failed");
      const data = await resp.json();
      pollSOPJob(data.job_id, "validate");
    } catch (err) {
      sopTestBtn.disabled = false;
      sopTestBtn.querySelector(".btn-text").textContent = "Validate";
      alert("Error: " + err.message);
    }
  });

  // ─── SOP Poll ──────────────────────────────────────────

  function pollSOPJob(jobId, type) {
    const iv = setInterval(async () => {
      try {
        const d = (await (await fetch(`/api/status/${jobId}`)).json());
        updateSOPProgress(d.progress, d.message);
        if (d.done) {
          clearInterval(iv);
          if (d.error) {
            alert("SOP Error: " + d.error);
            resetSOPButtons();
          } else if (d.result) {
            if (type === "reference") {
              onReferenceResult(d.result);
            } else {
              onValidateResult(d.result);
            }
          }
        }
      } catch(e) { clearInterval(iv); alert("Connection lost"); resetSOPButtons(); }
    }, 800);
  }

  function updateSOPProgress(pct, msg) {
    $("#sop-progress-bar").style.width = pct + "%";
    $("#sop-progress-pct").textContent = pct + "%";
    $("#sop-progress-msg").textContent = msg || "";
  }

  function resetSOPButtons() {
    sopRefBtn.disabled = !sopRefFile;
    sopRefBtn.querySelector(".btn-text").textContent = "Learn Reference";
    sopTestBtn.disabled = !(sopTestFile && sopReferenceLoaded);
    sopTestBtn.querySelector(".btn-text").textContent = "Validate";
  }

  // ─── SOP Reference Result ─────────────────────────────

  function onReferenceResult(result) {
    sopProgress.hidden = true;
    sopReferenceLoaded = true;

    // Update UI
    const status = $("#sop-ref-status");
    status.innerHTML = `
      <div class="sop-ref-success">
        <span class="sop-success-icon">✅</span>
        <span>Reference learned — <strong>${result.segment_count} steps</strong> detected (${result.processing_time_s}s)</span>
      </div>
    `;

    // Update timeline with reference keyframes
    if (result.segments && result.segments.length > 0) {
      const timeline = $("#sop-timeline");
      timeline.innerHTML = "";
      result.segments.forEach((seg, i) => {
        const stepDef = (result.sop_steps && result.sop_steps[i]) || { step_num: i+1, task_name: `Step ${i+1}` };
        const div = document.createElement("div");
        div.className = "sop-step ref-loaded";
        div.dataset.step = i + 1;
        div.innerHTML = `
          <div class="sop-step-num">${i+1}</div>
          <div class="sop-step-info">
            <div class="sop-step-title">${stepDef.task_name}</div>
            ${seg.keyframe_b64 ? `<img src="data:image/jpeg;base64,${seg.keyframe_b64}" class="sop-step-thumb" alt="Step ${i+1}"/>` : ''}
            ${seg.skeleton_b64 ? `<img src="data:image/jpeg;base64,${seg.skeleton_b64}" class="sop-step-thumb skeleton-thumb" alt="Skeleton ${i+1}"/>` : ''}
          </div>
        `;
        timeline.appendChild(div);
      });
    }

    resetSOPButtons();
    sopTestBtn.disabled = !sopTestFile;
  }

  // ─── SOP Validate Result ──────────────────────────────

  function onValidateResult(result) {
    sopProgress.hidden = true;
    sopResults.hidden = false;

    // Verdict banner
    const verdict = $("#sop-verdict");
    if (result.passed) {
      verdict.className = "sop-verdict sop-pass";
      verdict.innerHTML = `
        <div class="sop-verdict-icon">✅</div>
        <div class="sop-verdict-text">
          <h3>SOP COMPLIANCE PASSED</h3>
          <p>All steps completed in correct sequence.</p>
        </div>
      `;
    } else {
      verdict.className = "sop-verdict sop-fail";
      verdict.innerHTML = `
        <div class="sop-verdict-icon">❌</div>
        <div class="sop-verdict-text">
          <h3>SOP VIOLATION DETECTED</h3>
          <p>One or more steps are out of the expected order.</p>
        </div>
      `;
    }

    // Step results
    const container = $("#sop-step-results");
    container.innerHTML = "";
    (result.step_results || []).forEach(step => {
      const card = document.createElement("div");
      card.className = `sop-result-step ${step.is_correct ? "correct" : "violation"}`;
      card.innerHTML = `
        <div class="sop-result-header">
          <span class="sop-result-icon">${step.is_correct ? "✅" : "❌"}</span>
          <span class="sop-result-pos">Position ${step.position}</span>
          <span class="sop-result-sim">${Math.round(step.similarity * 100)}% match</span>
        </div>
        <div class="sop-result-detail">
          <div class="sop-result-expected">
            <span class="sop-detail-label">Expected:</span>
            <span class="sop-detail-value">${step.expected_task}</span>
          </div>
          ${!step.is_correct ? `
          <div class="sop-result-detected">
            <span class="sop-detail-label">Detected:</span>
            <span class="sop-detail-value violation-text">${step.detected_task}</span>
          </div>` : ''}
        </div>
        <div class="sop-result-frames">
          ${step.keyframe_b64 ? `<img src="data:image/jpeg;base64,${step.keyframe_b64}" class="sop-result-thumb" alt="Step ${step.position}"/>` : ''}
          ${step.skeleton_b64 ? `<img src="data:image/jpeg;base64,${step.skeleton_b64}" class="sop-result-thumb skeleton-thumb" alt="Skeleton ${step.position}"/>` : ''}
        </div>
      `;
      container.appendChild(card);
    });

    // Summary
    const summary = $("#sop-summary");
    summary.innerHTML = `
      <div class="sop-summary-text">
        <p>${result.summary}</p>
        <p class="sop-meta">Processed in ${result.processing_time_s}s · ${result.total_frames} frames · ${result.fps?.toFixed(1)} FPS</p>
      </div>
    `;

    resetSOPButtons();
    sopResults.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ─── Lightbox ──────────────────────────────────────────

  function openLightbox(b64) { lightboxImg.src = `data:image/jpeg;base64,${b64}`; lightbox.hidden = false; document.body.style.overflow = "hidden"; }
  function closeLightbox() { lightbox.hidden = true; document.body.style.overflow = ""; }
  lightboxClose.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", e => { if (e.target === lightbox) closeLightbox(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !lightbox.hidden) closeLightbox(); });

  // ─── Sections ──────────────────────────────────────────

  function showSection(name) {
    uploadSection.hidden = name !== "upload";
    progressSection.hidden = name !== "progress";
    resultsSection.hidden = name !== "results";
    errorSection.hidden = name !== "error";
    sopSection.hidden = true; // hide SOP when showing action results
    const hero = $("#hero-section");
    if (hero) hero.hidden = name !== "upload";
  }

  function resetToUpload() {
    clearFile(); queryInput.value = ""; updateBtn();
    showSection("upload");
    // If SOP was active, re-show SOP
    if (currentMode === "sop") {
      sopSection.hidden = false;
    }
    updateProgress(0, "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function showError(msg) { showSection("error"); $("#error-msg").textContent = msg; }

  newAnalysisBtn.addEventListener("click", resetToUpload);
  errorRetryBtn.addEventListener("click", resetToUpload);
  showSection("upload");

  // Check SOP status on load
  (async function checkSOPStatus() {
    try {
      const resp = await fetch("/api/sop/status");
      const data = await resp.json();
      hasClassifier = !!data.has_classifier;
      sopReferenceLoaded = !!data.has_reference;

      if (hasClassifier) {
        // Show classifier badge in SOP section
        const status = $("#sop-ref-status");
        status.innerHTML = `
          <div class="sop-ref-success">
            <span class="sop-success-icon">🤖</span>
            <span>Trained classifier ready — <strong>reference upload optional</strong></span>
          </div>
        `;
        // Enable validate button directly if file selected
        if (sopTestFile) sopTestBtn.disabled = false;
      }
    } catch(e) {}
  })();
})();

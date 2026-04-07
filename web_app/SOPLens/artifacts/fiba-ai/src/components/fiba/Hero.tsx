import React from "react";

export function Hero() {
  return (
    <div className="relative overflow-hidden bg-[var(--fiba-bg)] py-16 sm:py-24">
      <div className="container relative z-10 flex flex-col items-center text-center px-4">
        <p className="mb-4 text-xs font-medium uppercase tracking-[0.2em] text-white/30">
          MIT Bangalore × Hitachi
        </p>
        <h1 className="text-5xl font-bold tracking-tight text-white sm:text-7xl md:text-8xl">
          <span className="font-bold text-white">SOP</span><span className="font-light text-white/50">Lens</span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-base text-white/40 sm:text-lg leading-relaxed">
          Edge-ready SOP compliance validation · Zero-shot action detection · No cloud required
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs text-white/25 font-mono">
          <span>YOLOv8n</span>
          <span className="text-white/10">·</span>
          <span>MediaPipe</span>
          <span className="text-white/10">·</span>
          <span>MobileNet</span>
          <span className="text-white/10">·</span>
          <span>Flask API</span>
        </div>
      </div>
    </div>
  );
}

import React from "react";

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full border-b border-[var(--fiba-card-border)] bg-[var(--fiba-bg)]/90 backdrop-blur supports-[backdrop-filter]:bg-[var(--fiba-bg)]/70">
      <div className="container flex h-14 items-center justify-between px-4 sm:px-8">
        <div className="flex items-center gap-0.5">
          <span className="text-lg font-bold tracking-tight text-white">SOP</span>
          <span className="text-lg font-light tracking-tight text-white/60">Lens</span>
        </div>
        <div className="hidden sm:flex items-center gap-2 rounded-full border border-[var(--fiba-card-border)] bg-[var(--fiba-card)] px-3 py-1 text-xs text-white/40">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/60 opacity-60"></span>
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-white/80"></span>
          </span>
          Edge · Zero-Shot · SOP Compliance
        </div>
      </div>
    </nav>
  );
}

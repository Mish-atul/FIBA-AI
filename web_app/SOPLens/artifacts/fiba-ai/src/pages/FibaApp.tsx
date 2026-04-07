import React, { useState } from "react";
import { Navbar } from "@/components/fiba/Navbar";
import { Hero } from "@/components/fiba/Hero";
import { ModeTabs } from "@/components/fiba/ModeTabs";
import { ActionSearch } from "@/components/fiba/ActionSearch";
import { SOPCompliance } from "@/components/fiba/SOPCompliance";
import { Lightbox } from "@/components/fiba/Lightbox";

export default function FibaApp() {
  const [mode, setMode] = useState<"action" | "sop">("action");
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-[var(--fiba-bg)] text-foreground font-sans selection:bg-[var(--fiba-purple)] selection:text-white flex flex-col">
      <Navbar />
      
      <main className="flex-1 w-full">
        <Hero />
        
        <ModeTabs mode={mode} setMode={setMode} />
        
        <div className="w-full">
          {mode === "action" ? (
            <ActionSearch onOpenLightbox={setLightboxSrc} />
          ) : (
            <SOPCompliance onOpenLightbox={setLightboxSrc} />
          )}
        </div>
      </main>

      <footer className="mt-auto border-t border-[var(--fiba-card-border)] bg-[var(--fiba-bg)] py-8">
        <div className="container px-4 text-center">
          <p className="text-sm font-medium text-muted-foreground">
            FIBA AI · MIT Bangalore Hitachi Hackathon · Team: Atul · Tanishk · Yash
          </p>
          <p className="mt-2 text-xs text-muted-foreground/70">
            Zero-shot · Edge-friendly · Explainable action retrieval · SOP Compliance
          </p>
        </div>
      </footer>

      <Lightbox 
        src={lightboxSrc} 
        onClose={() => setLightboxSrc(null)} 
      />
    </div>
  );
}

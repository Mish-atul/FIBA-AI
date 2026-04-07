import React from "react";
import { Search, ClipboardCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModeTabsProps {
  mode: "action" | "sop";
  setMode: (mode: "action" | "sop") => void;
}

export function ModeTabs({ mode, setMode }: ModeTabsProps) {
  return (
    <div className="flex justify-center w-full my-8 px-4">
      <div
        role="tablist"
        aria-label="Analysis mode"
        className="inline-flex items-center justify-center rounded-lg bg-[var(--fiba-card)] p-1 border border-[var(--fiba-card-border)] w-full max-w-md"
      >
        <button
          role="tab"
          aria-selected={mode === "action"}
          aria-controls="panel-action"
          onClick={() => setMode("action")}
          className={cn(
            "inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2.5 text-sm font-medium transition-all w-1/2 gap-2",
            mode === "action"
              ? "bg-white/10 text-white shadow-sm"
              : "text-muted-foreground hover:text-foreground hover:bg-[var(--fiba-glass)]"
          )}
          data-testid="tab-action"
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          Action Search
        </button>
        <button
          role="tab"
          aria-selected={mode === "sop"}
          aria-controls="panel-sop"
          onClick={() => setMode("sop")}
          className={cn(
            "inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2.5 text-sm font-medium transition-all w-1/2 gap-2",
            mode === "sop"
              ? "bg-white/10 text-white shadow-sm"
              : "text-muted-foreground hover:text-foreground hover:bg-[var(--fiba-glass)]"
          )}
          data-testid="tab-sop"
        >
          <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
          SOP Compliance
        </button>
      </div>
    </div>
  );
}

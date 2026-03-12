"use client";

export type ProcessingState = "idle" | "uploading" | "processing" | "completed" | "error";

type StatusPanelProps = {
  state: ProcessingState;
  progressPercent?: number;
  stepLabel?: string;
  errorMessage?: string | null;
};

export default function StatusPanel({
  state,
  progressPercent = 0,
  stepLabel,
  errorMessage,
}: StatusPanelProps) {
  const labels: Record<ProcessingState, string> = {
    idle: "Idle",
    uploading: "Uploading...",
    processing: "Processing...",
    completed: "Completed",
    error: "Error",
  };

  const showProgress = state === "uploading" || state === "processing";
  const percent = showProgress ? progressPercent : state === "completed" ? 100 : 0;

  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col justify-between">
      <div>
        <h3 className="font-semibold mb-1">Status</h3>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              state === "error"
                ? "bg-red-500"
                : state === "completed"
                  ? "bg-primary"
                  : "bg-primary animate-pulse"
            }`}
          />
          <span className="text-sm text-slate-300">{labels[state]}</span>
        </div>
        {state === "error" && errorMessage && (
          <p className="text-red-400 text-sm mt-2">{errorMessage}</p>
        )}
      </div>
      <div className="flex flex-col gap-3 mt-4">
        {showProgress && stepLabel && (
          <div className="flex items-end justify-between">
            <span className="text-[40px] font-black text-primary leading-none">
              {Math.round(percent)}%
            </span>
            <span className="text-[10px] text-slate-500 font-mono mb-1">
              {stepLabel}
            </span>
          </div>
        )}
        {state === "completed" && (
          <div className="flex items-end justify-between">
            <span className="text-[40px] font-black text-primary leading-none">
              100%
            </span>
          </div>
        )}
        <div className="h-4 liquid-glass rounded-full overflow-hidden relative border border-white/5 p-1">
          <div
            className="h-full bg-primary/40 rounded-full relative transition-all duration-500"
            style={{ width: `${percent}%` }}
          >
            {(state === "uploading" || state === "processing") && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

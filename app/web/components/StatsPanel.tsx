"use client";

type StatsPanelProps = {
  framesProcessed: number | null;
  resolution: { width: number; height: number } | null;
  objectsDetected: number | null;
};

export default function StatsPanel({
  framesProcessed,
  resolution,
  objectsDetected,
}: StatsPanelProps) {
  const formatNumber = (n: number) =>
    n.toLocaleString();

  return (
    <div className="col-span-12 grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="glass-card rounded-2xl p-6 flex items-center gap-6 group hover:border-primary/20 transition-all">
        <div className="p-3 bg-white/5 rounded-xl group-hover:text-primary transition-colors">
          <span className="text-3xl" aria-hidden>🎞</span>
        </div>
        <div>
          <p className="text-xs text-slate-500 uppercase font-bold tracking-widest">
            Frames Processed
          </p>
          <p className="text-2xl font-black">
            {framesProcessed != null ? formatNumber(framesProcessed) : "—"}
          </p>
        </div>
      </div>
      <div className="glass-card rounded-2xl p-6 flex items-center gap-6 group hover:border-primary/20 transition-all">
        <div className="p-3 bg-white/5 rounded-xl group-hover:text-primary transition-colors">
          <span className="text-3xl" aria-hidden>4K</span>
        </div>
        <div>
          <p className="text-xs text-slate-500 uppercase font-bold tracking-widest">
            Resolution
          </p>
          <p className="text-2xl font-black">
            {resolution
              ? `${resolution.width} × ${resolution.height}`
              : "—"}
          </p>
        </div>
      </div>
      <div className="glass-card rounded-2xl p-6 flex items-center gap-6 group hover:border-primary/20 transition-all">
        <div className="p-3 bg-white/5 rounded-xl group-hover:text-primary transition-colors">
          <span className="text-3xl" aria-hidden>{`{}`}</span>
        </div>
        <div>
          <p className="text-xs text-slate-500 uppercase font-bold tracking-widest">
            Objects Detected
          </p>
          <p className="text-2xl font-black">
            {objectsDetected != null ? formatNumber(objectsDetected) : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}

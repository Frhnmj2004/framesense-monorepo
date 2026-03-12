"use client";

import type { SegmentationResult } from "./VideoPlayer";

type ObjectListProps = {
  detections: SegmentationResult | null;
  prompt: string | null;
  highlightedObjectId: number | null;
  onSelectObject: (objectId: number | null) => void;
};

type ObjectSummary = {
  object_id: number;
  label: string;
  confidence: number;
  frameStart: number;
  frameEnd: number;
};

function summarizeObjects(
  detections: SegmentationResult | null,
  prompt: string | null
): ObjectSummary[] {
  if (!detections?.detections?.length) return [];

  const byId = new Map<
    number,
    { scores: number[]; frames: number[] }
  >();

  for (const d of detections.detections) {
    for (const obj of d.objects) {
      const existing = byId.get(obj.object_id);
      if (!existing) {
        byId.set(obj.object_id, {
          scores: [obj.score],
          frames: [d.frame_index],
        });
      } else {
        existing.scores.push(obj.score);
        existing.frames.push(d.frame_index);
      }
    }
  }

  return Array.from(byId.entries()).map(([object_id, { scores, frames }]) => ({
    object_id,
    label: prompt ?? `Object ${object_id}`,
    confidence: Math.max(...scores),
    frameStart: Math.min(...frames),
    frameEnd: Math.max(...frames),
  }));
}

export default function ObjectList({
  detections,
  prompt,
  highlightedObjectId,
  onSelectObject,
}: ObjectListProps) {
  const items = summarizeObjects(detections, prompt);

  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Detected Objects</h3>
        <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full border border-primary/20">
          {detections ? "Live Stream" : "—"}
        </span>
      </div>
      <div className="space-y-3 overflow-y-auto max-h-[400px] pr-2">
        {items.length === 0 && (
          <p className="text-slate-500 text-sm">No detections yet. Run analysis.</p>
        )}
        {items.map((item) => (
          <button
            type="button"
            key={item.object_id}
            onClick={() =>
              onSelectObject(
                highlightedObjectId === item.object_id ? null : item.object_id
              )
            }
            className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all duration-200 cursor-pointer text-left focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background-dark ${
              highlightedObjectId === item.object_id
                ? "bg-primary/10 border-primary/30"
                : "bg-white/5 border-white/5 hover:border-primary/30"
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <span className="text-lg" aria-hidden>◇</span>
              </div>
              <div>
                <p className="text-sm font-medium">{item.label}</p>
                <p className="text-[10px] text-slate-500 uppercase tracking-tighter">
                  Frames {item.frameStart}-{item.frameEnd}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-bold text-primary">
                {(item.confidence * 100).toFixed(1)}%
              </p>
              <p className="text-[10px] text-slate-500">Confidence</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

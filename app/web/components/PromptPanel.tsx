"use client";

import { useState } from "react";

type PromptPanelProps = {
  disabled: boolean;
  onRunAnalysis: (prompt: string) => void;
};

export default function PromptPanel({ disabled, onRunAnalysis }: PromptPanelProps) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !disabled) onRunAnalysis(prompt.trim());
  };

  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <span className="text-primary text-2xl" aria-hidden>🔍</span>
        <h3 className="font-semibold">Detection Prompt</h3>
      </div>
      <form onSubmit={handleSubmit} className="relative flex-1 flex flex-col gap-4">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the object you want to detect (e.g. 'Silver laptop on desk')"
          disabled={disabled}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-4 focus:ring-1 focus:ring-primary focus:border-primary outline-none text-slate-200 placeholder:text-slate-600 disabled:opacity-50"
          aria-label="Detection prompt"
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={disabled || !prompt.trim()}
            className="bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-background-dark font-bold py-2.5 px-8 rounded-full flex items-center gap-2 transition-all duration-200 active:scale-95 shadow-[0_0_20px_rgba(118,168,56,0.2)] focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background-dark"
          >
            <span aria-hidden>▶</span>
            Run Analysis
          </button>
        </div>
      </form>
    </div>
  );
}

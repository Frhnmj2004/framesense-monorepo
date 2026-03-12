"use client";

type UploadPanelProps = {
  fileName: string | null;
  uploadProgress: number;
  isUploading: boolean;
  onFileSelect: (file: File) => void;
};

export default function UploadPanel({
  fileName,
  uploadProgress,
  isUploading,
  onFileSelect,
}: UploadPanelProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelect(file);
  };

  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col justify-between group cursor-pointer hover:bg-white/[0.04] transition-all duration-200">
      <div className="flex flex-col gap-4">
        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
          <span className="text-2xl" aria-hidden>📁</span>
        </div>
        <div>
          <h3 className="font-semibold text-lg">Upload Video</h3>
          <p className="text-slate-400 text-sm">MP4, MOV up to 2GB</p>
        </div>
      </div>
      <div className="mt-8 flex flex-col gap-2">
        <label className="flex flex-col gap-2 cursor-pointer">
          <span className="text-xs text-slate-500 italic">
            {fileName ?? "Choose file"}
          </span>
          <input
            type="file"
            accept="video/mp4,.mp4"
            onChange={handleChange}
            disabled={isUploading}
            className="text-sm file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-primary file:text-background-dark file:font-medium file:cursor-pointer hover:file:bg-primary/90"
            aria-label="Select video file"
          />
        </label>
        {fileName && (
          <>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-500 italic truncate max-w-[180px]">
                {fileName}
              </span>
              <span className="text-primary font-bold">
                {isUploading ? `${uploadProgress}%` : "100%"}
              </span>
            </div>
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${isUploading ? uploadProgress : 100}%` }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

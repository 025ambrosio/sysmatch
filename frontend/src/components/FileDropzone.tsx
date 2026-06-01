import { useRef, useState } from "react";
import { UploadCloud, FileCheck2, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  title: string;
  description: string;
  accept: string;
  acceptedTypes: string[];
  files: File[];
  onFilesChange: (files: File[]) => void;
}

export function FileDropzone({
  title,
  description,
  accept,
  acceptedTypes,
  files,
  onFilesChange,
}: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    onFilesChange([...files, ...Array.from(list)]);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        addFiles(e.dataTransfer.files);
      }}
      className={cn(
        "rounded-xl border-2 border-dashed bg-card p-6 transition-colors",
        dragging ? "border-primary bg-primary/5" : "border-border",
      )}
    >
      <div className="flex flex-col items-center text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <UploadCloud className="h-6 w-6" />
        </div>
        <h3 className="mt-3 text-base font-semibold">{title}</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
        <div className="mt-3 flex flex-wrap justify-center gap-1.5">
          {acceptedTypes.map((t) => (
            <span
              key={t}
              className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
            >
              {t}
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <UploadCloud className="h-4 w-4" />
          Selecionar arquivos
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-5 space-y-1.5">
          {files.map((f, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded-md border bg-background px-3 py-2 text-sm"
            >
              <div className="flex items-center gap-2 truncate">
                <FileCheck2 className="h-4 w-4 text-success" />
                <span className="truncate">{f.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(f.size / 1024).toFixed(0)} KB
                </span>
              </div>
              <button
                type="button"
                onClick={() =>
                  onFilesChange(files.filter((_, idx) => idx !== i))
                }
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

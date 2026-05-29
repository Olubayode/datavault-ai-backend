import { FileSpreadsheet, FileText, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

export default function FileDrop({ title, subtitle, accept, purpose, onUpload }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);

  async function handleFile(file) {
    if (!file) return;
    setBusy(true);
    try {
      await onUpload(file, purpose);
    } finally {
      setBusy(false);
    }
  }

  const Icon = purpose === "prototype_pdf" ? FileText : FileSpreadsheet;

  return (
    <button
      className="dropzone"
      type="button"
      onClick={() => inputRef.current?.click()}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        handleFile(event.dataTransfer.files?.[0]);
      }}
      disabled={busy}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
      <span className="dropzone-icon">
        <Icon size={20} />
      </span>
      <span className="dropzone-copy">
        <strong>{busy ? "Uploading..." : title}</strong>
        <small>{subtitle}</small>
      </span>
      <UploadCloud size={18} />
    </button>
  );
}

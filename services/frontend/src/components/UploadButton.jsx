import { useRef, useState } from "react";
import { uploadStatement } from "../api";

export default function UploadButton({ onUploaded }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null); // { kind: "ok" | "error", text }

  async function handleFile(event) {
    const input = event.target;
    const file = input.files[0];
    if (!file) return;

    setBusy(true);
    setMessage(null);
    try {
      const result = await uploadStatement(file);
      setMessage({
        kind: "ok",
        text: `Imported ${result.imported}, skipped ${result.skipped_duplicates} duplicates.`,
      });
      onUploaded();
    } catch (err) {
      setMessage({ kind: "error", text: err.message });
    } finally {
      setBusy(false);
      input.value = ""; // lets you pick the same file again
    }
  }

  return (
    <div className="upload">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        aria-label="Statement file"
        onChange={handleFile}
        hidden
      />
      <button type="button" className="primary" disabled={busy} onClick={() => inputRef.current.click()}>
        {busy ? "Uploading…" : "Upload statement"}
      </button>
      {message && <span className={`upload-msg ${message.kind}`}>{message.text}</span>}
    </div>
  );
}
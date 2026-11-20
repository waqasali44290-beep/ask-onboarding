// Drag-and-drop area plus a normal file picker, limited to .pdf, .md and .txt.
import { useState, type DragEvent } from "react";
import { UploadIcon } from "./Icons";

const ACCEPTED = ".pdf,.md,.markdown,.txt";

export default function FileDropzone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(event: DragEvent) {
    event.preventDefault(); // stop the browser from opening the file
    setDragging(false);
    onFiles(Array.from(event.dataTransfer.files));
  }

  return (
    // A <label> makes the whole area open the file picker, with keyboard support for free.
    <label
      className={`dropzone${dragging ? " dropzone-active" : ""}`}
      onDragOver={(event) => {
        event.preventDefault(); // required, or the drop event never fires
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept={ACCEPTED}
        multiple
        className="visually-hidden"
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []));
          event.target.value = ""; // allow choosing the same file again
        }}
      />
      <span className="dropzone-icon"><UploadIcon /></span>
      <span className="dropzone-title">Drop files here or click to choose</span>
      <span className="muted">PDF, Markdown or TXT · up to 20 MB each</span>
    </label>
  );
}

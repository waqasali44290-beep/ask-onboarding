// Side panel showing the source document with the cited passage highlighted.
// Uses the native <dialog> element: it traps focus, closes on Escape and
// returns focus to the citation button, without extra code.
import { useEffect, useRef, useState } from "react";
import { api, ApiError, messageOf } from "../api/client";
import type { DocumentDetail, Source } from "../types";
import { ErrorState, LoadingState } from "./States";

interface Props {
  source: Source | null; // null = panel closed
  onClose: () => void;
}

export default function CitationPanel({ source, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const highlightRef = useRef<HTMLElement>(null);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Open/close the dialog to match the `source` prop.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (source && !dialog.open) dialog.showModal();
    if (!source && dialog.open) dialog.close();
  }, [source]);

  useEffect(() => {
    if (!source) return;
    let cancelled = false; // ignore a slow response if another citation was clicked meanwhile
    setDocument(null);
    setError(null);
    api
      .getDocument(source.document_id)
      .then((loaded) => !cancelled && setDocument(loaded))
      .catch((err) => {
        if (cancelled) return;
        const deleted = err instanceof ApiError && err.status === 404;
        setError(deleted ? "This document has been deleted since the answer was written." : messageOf(err));
      });
    return () => {
      cancelled = true;
    };
  }, [source]);

  // Scroll the highlighted passage into the middle of the panel once the text is shown.
  useEffect(() => {
    highlightRef.current?.scrollIntoView({ block: "center" });
  }, [document]);

  return (
    <dialog
      ref={dialogRef}
      className="citation-panel"
      aria-labelledby="citation-title"
      onClose={onClose}
      // A click on the dark backdrop lands on the <dialog> itself, not its content.
      onClick={(event) => event.target === event.currentTarget && dialogRef.current?.close()}
    >
      {source && (
        <div className="citation-content">
          <header className="citation-header">
            <div>
              <h2 id="citation-title">{source.filename}</h2>
              <p className="muted">
                Source {source.n}
                {source.page !== null && ` · page ${source.page}`}
              </p>
            </div>
            <button type="button" className="button button-quiet" onClick={() => dialogRef.current?.close()}>
              Close
            </button>
          </header>
          <div className="citation-body">
            {error && <ErrorState message={error} />}
            {!error && !document && <LoadingState label="Loading document…" />}
            {document && <DocumentText document={document} source={source} highlightRef={highlightRef} />}
          </div>
        </div>
      )}
    </dialog>
  );
}

function DocumentText({
  document,
  source,
  highlightRef,
}: {
  document: DocumentDetail;
  source: Source;
  highlightRef: React.RefObject<HTMLElement>;
}) {
  const text = document.full_text ?? "";
  // If the file was re-uploaded after this answer, the offsets point into the new
  // version. Only highlight when they still match the passage that was cited.
  if (text.slice(source.start_char, source.end_char) !== source.content) {
    return (
      <>
        <p className="notice">This document has changed since the answer was written. The passage used was:</p>
        <mark ref={highlightRef} className="passage">
          {source.content}
        </mark>
      </>
    );
  }
  return (
    <p className="document-text">
      {text.slice(0, source.start_char)}
      <mark ref={highlightRef} className="passage">
        {text.slice(source.start_char, source.end_char)}
      </mark>
      {text.slice(source.end_char)}
    </p>
  );
}

// Upload page: drag-and-drop PDF/MD/TXT + list of documents with status (processing/ready/failed).
import { useState } from "react";
import { api, messageOf } from "../api/client";
import DocumentList from "../components/DocumentList";
import FileDropzone from "../components/FileDropzone";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useDocuments } from "../hooks/useDocuments";
import type { DocumentInfo } from "../types";

interface UploadResult {
  name: string;
  error: string | null;
}

export default function UploadPage() {
  const { documents, error, refresh } = useDocuments();
  const [uploading, setUploading] = useState(0);
  const [results, setResults] = useState<UploadResult[]>([]);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function upload(files: File[]) {
    if (files.length === 0) return;
    setUploading((count) => count + files.length);
    const outcomes = await Promise.all(
      files.map(async (file) => {
        try {
          await api.uploadDocument(file);
          return { name: file.name, error: null };
        } catch (err) {
          return { name: file.name, error: messageOf(err) };
        } finally {
          setUploading((count) => count - 1);
        }
      }),
    );
    setResults(outcomes);
    refresh();
  }

  async function remove(document: DocumentInfo) {
    if (!window.confirm(`Delete "${document.filename}"? The assistant will no longer use it.`)) return;
    try {
      await api.deleteDocument(document.id);
      setDeleteError(null);
    } catch (err) {
      setDeleteError(messageOf(err));
    }
    refresh();
  }

  const failedUploads = results.filter((result) => result.error);

  return (
    <section className="page">
      <h1>Documents</h1>
      <p className="muted">
        Upload company documents for the assistant to answer from. Uploading a file with the same name replaces the
        old version.
      </p>

      <FileDropzone onFiles={upload} />

      <div aria-live="polite">
        {uploading > 0 && <LoadingState label={`Uploading ${uploading} file${uploading === 1 ? "" : "s"}…`} />}
        {failedUploads.map((result) => (
          <p key={result.name} className="error-text" role="alert">
            {result.name}: {result.error}
          </p>
        ))}
        {deleteError && (
          <p className="error-text" role="alert">
            {deleteError}
          </p>
        )}
      </div>

      <h2>Indexed documents</h2>
      {error && <ErrorState message={error} onRetry={refresh} />}
      {!error && documents === null && <LoadingState label="Loading documents…" />}
      {documents?.length === 0 && (
        <EmptyState title="No documents yet">
          <p className="muted">Upload a handbook, wiki page or IT guide to get started.</p>
        </EmptyState>
      )}
      {documents && documents.length > 0 && <DocumentList documents={documents} onDelete={remove} />}
    </section>
  );
}

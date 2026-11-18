// Table of documents with a status badge and delete button.
import type { DocumentInfo } from "../types";
import StatusBadge from "./StatusBadge";

interface Props {
  documents: DocumentInfo[];
  onDelete: (document: DocumentInfo) => void;
}

export default function DocumentList({ documents, onDelete }: Props) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>File</th>
          <th>Status</th>
          <th className="numeric">Chunks</th>
          <th>Updated</th>
          <th>
            <span className="visually-hidden">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {documents.map((document) => (
          <tr key={document.id}>
            <td>
              <span className="filename">{document.filename}</span>
              {document.error && <p className="error-text">{document.error}</p>}
            </td>
            <td>
              <StatusBadge status={document.status} />
            </td>
            <td className="numeric">{document.status === "ready" ? document.chunk_count : "–"}</td>
            <td className="muted">{new Date(document.updated_at).toLocaleString()}</td>
            <td>
              <button
                type="button"
                className="button button-quiet"
                onClick={() => onDelete(document)}
                aria-label={`Delete ${document.filename}`}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Table of documents with a status badge and delete button.
import type { DocumentInfo, Visibility } from "../types";
import StatusBadge from "./StatusBadge";

interface Props {
  documents: DocumentInfo[];
  onDelete: (document: DocumentInfo) => void;
  onVisibilityChange: (document: DocumentInfo, visibility: Visibility) => void;
}

export default function DocumentList({ documents, onDelete, onVisibilityChange }: Props) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>File</th>
          <th>Status</th>
          <th>Visible to</th>
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
            <td>
              <select
                className="input select select-small"
                value={document.visibility}
                onChange={(event) => onVisibilityChange(document, event.target.value as Visibility)}
                aria-label={`Who can see ${document.filename}`}
              >
                <option value="everyone">Everyone</option>
                <option value="managers">Managers only</option>
              </select>
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

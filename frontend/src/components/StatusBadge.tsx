// Coloured badge for processing / ready / failed.
import type { DocumentStatus } from "../types";

const LABELS: Record<DocumentStatus, string> = {
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export default function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span className={`badge badge-${status}`}>
      {status === "processing" && <span className="spinner spinner-small" aria-hidden="true" />}
      {LABELS[status]}
    </span>
  );
}

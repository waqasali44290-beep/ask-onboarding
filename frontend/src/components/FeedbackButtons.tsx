// Thumbs up / down under an answer. Clicking the selected thumb again removes the rating.
import { useState } from "react";
import { api } from "../api/client";
import type { Rating } from "../types";

export default function FeedbackButtons({ messageId, initial }: { messageId: number; initial: Rating | null }) {
  const [rating, setRating] = useState<Rating | null>(initial);
  const [failed, setFailed] = useState(false);

  async function rate(value: Rating) {
    const next = rating === value ? null : value;
    const previous = rating;
    setRating(next); // show it immediately; undo if saving fails
    setFailed(false);
    try {
      await api.rateAnswer(messageId, next ?? 0);
    } catch {
      setRating(previous);
      setFailed(true);
    }
  }

  return (
    <div className="feedback" role="group" aria-label="Rate this answer">
      <button
        type="button"
        className={`feedback-button${rating === 1 ? " feedback-selected" : ""}`}
        aria-pressed={rating === 1}
        aria-label="Helpful"
        title="Helpful"
        onClick={() => rate(1)}
      >
        👍
      </button>
      <button
        type="button"
        className={`feedback-button${rating === -1 ? " feedback-selected" : ""}`}
        aria-pressed={rating === -1}
        aria-label="Not helpful"
        title="Not helpful"
        onClick={() => rate(-1)}
      >
        👎
      </button>
      {failed && <span className="error-text">Couldn't save your rating.</span>}
      {rating !== null && !failed && <span className="muted feedback-thanks">Thanks for the feedback</span>}
    </div>
  );
}

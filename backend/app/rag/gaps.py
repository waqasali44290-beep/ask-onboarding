"""Knowledge-gap radar: group unanswered questions by topic, biggest gaps first.

Each question joins the first group whose first question means nearly the same
thing (cosine similarity of their embeddings >= threshold); otherwise it starts
a new group. Simple and good enough for hundreds of questions.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

# Measured with bge-small: rewordings of one question score 0.69-0.75
# ("Where do I park my car?" / "Is there parking at the office?"), different topics 0.37-0.54.
SAME_TOPIC = 0.65


@dataclass
class Gap:
    topic: str  # the first question asked about it
    questions: list[str] = field(default_factory=list)
    vector: list[float] = field(default_factory=list)


def find_gaps(
    questions: list[str], embed: Callable[[list[str]], list[list[float]]], threshold: float = SAME_TOPIC
) -> list[Gap]:
    if not questions:
        return []
    gaps: list[Gap] = []
    for question, vector in zip(questions, embed(questions)):
        best, best_score = None, threshold
        for gap in gaps:
            score = sum(a * b for a, b in zip(vector, gap.vector))  # vectors are normalised: dot = cosine
            if score >= best_score:
                best, best_score = gap, score
        if best is None:
            gaps.append(Gap(topic=question, questions=[question], vector=vector))
        else:
            best.questions.append(question)
    return sorted(gaps, key=lambda gap: len(gap.questions), reverse=True)

"""Scores retrieval hit-rate and answer quality on eval/questions.jsonl against the running API.

Usage (inside the backend container, which mounts this folder at /eval):
    docker compose exec backend python /eval/run_eval.py --label chunk800
    docker compose exec backend python /eval/run_eval.py --label chunk400 --retrieval-only

Scoring is deliberately simple and transparent:
- retrieval hit: the expected file is among the top-k chunks AND passes the similarity cutoff
- answer correct: every `must_include` item appears (alternatives separated by "|", case-insensitive),
  no `must_not_include` item appears, and the expected file is cited
- no-answer correct: questions with source=null get the no-answer reply
"""
import argparse
import http.cookiejar
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent

# Keeps the session cookie from /api/auth/login for every later request.
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def post(api: str, path: str, body: dict) -> urllib.request.addinfourl:
    request = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    return opener.open(request, timeout=600)


def retrieve(api: str, question: str, top_k: int) -> list[dict]:
    with post(api, "/api/retrieve", {"question": question, "top_k": top_k}) as response:
        return json.load(response)["chunks"]


def chat(api: str, question: str) -> dict:
    """Read the whole SSE stream; return the answer text, cited files and whether it was a no-answer."""
    answer, event, result = "", None, {"no_answer": False, "cited": [], "error": None}
    with post(api, "/api/chat", {"question": question}) as response:
        for raw in response:
            line = raw.decode().rstrip("\n")
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
                if event == "token":
                    answer += data["text"]
                elif event == "no_answer":
                    result["no_answer"] = True
                elif event == "error":
                    result["error"] = data["message"]
                elif event == "done":
                    result["cited"] = sorted({c["filename"] for c in data["citations"]})
    result["answer"] = answer.strip()
    return result


def contains(text: str, alternatives: str) -> bool:
    return any(option.lower() in text.lower() for option in alternatives.split("|"))


def answer_is_correct(case: dict, result: dict) -> bool:
    if case["source"] is None:
        return result["no_answer"]
    return (
        not result["no_answer"]
        and all(contains(result["answer"], item) for item in case.get("must_include", []))
        and not any(contains(result["answer"], item) for item in case.get("must_not_include", []))
        and case["source"] in result["cited"]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--label", default="run", help="name for the results file")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--user", default="admin", help="admins and managers can see every document")
    parser.add_argument("--password", default="onboarding")
    parser.add_argument("--retrieval-only", action="store_true", help="skip the (slow) LLM answers")
    args = parser.parse_args()

    post(args.api, "/api/auth/login", {"username": args.user, "password": args.password}).close()
    cases = [json.loads(line) for line in (HERE / "questions.jsonl").read_text().splitlines() if line.strip()]
    rows = []
    for case in cases:
        chunks = retrieve(args.api, case["question"], args.top_k)
        row = {"id": case["id"], "question": case["question"], "source": case["source"],
               "top_files": [c["filename"] for c in chunks if c["relevant"]]}
        if case["source"]:
            row["retrieval_hit"] = case["source"] in row["top_files"]
        if not args.retrieval_only:
            started = time.time()
            result = chat(args.api, case["question"])
            row.update(result, seconds=round(time.time() - started, 1), correct=answer_is_correct(case, result))
        rows.append(row)
        status = "" if args.retrieval_only else ("✓" if row["correct"] else "✗")
        print(f"{status:1} #{case['id']:<2} hit={row.get('retrieval_hit', '-')!s:5} {case['question']}", flush=True)
        if not args.retrieval_only and not row["correct"]:
            print(f"     answer: {row['answer'][:150] or row['error']!r}  cited: {row['cited']}")

    answerable = [r for r in rows if r["source"]]
    summary = {"label": args.label, "top_k": args.top_k,
               "retrieval_hit_rate": round(sum(r["retrieval_hit"] for r in answerable) / len(answerable), 3)}
    if not args.retrieval_only:
        unanswerable = [r for r in rows if not r["source"]]
        summary.update(
            answer_accuracy=round(sum(r["correct"] for r in answerable) / len(answerable), 3),
            no_answer_accuracy=round(sum(r["correct"] for r in unanswerable) / len(unanswerable), 3),
            injection_resisted=next(r["correct"] for r in rows if r["id"] == 17),
            median_seconds=sorted(r["seconds"] for r in rows)[len(rows) // 2],
        )
    print(json.dumps(summary, indent=2))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"{args.label}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()

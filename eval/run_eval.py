from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from urllib import request

BASE_URL: str = "http://127.0.0.1:8000/chat"
QUESTIONS_PATH: Path = Path("eval") / "questions.json"
SESSION_PREFIX: str = "eval-session"


def execute_post(payload: dict[str, Any]) -> dict[str, Any]:
    encoded_payload: bytes = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        BASE_URL,
        data=encoded_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=120) as http_response:
        body: bytes = http_response.read()
    return json.loads(body.decode("utf-8"))


def execute_eval() -> None:
    questions: list[dict[str, Any]] = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for index, item in enumerate(questions):
        payload: dict[str, Any] = {
            "session_id": f"{SESSION_PREFIX}-{index + 1}",
            "user_query": item["query"],
        }
        response: dict[str, Any] = execute_post(payload)
        actual_action: str = str(response.get("action", ""))
        expected_action: str = str(item["expected_action"])
        is_action_match: bool = actual_action == expected_action
        results.append(
            {
                "id": item["id"],
                "query": item["query"],
                "expected_action": expected_action,
                "actual_action": actual_action,
                "match": is_action_match,
                "confidence": response.get("confidence", 0.0),
            }
        )
    matches: int = len([item for item in results if item["match"]])
    total: int = len(results)
    summary: dict[str, Any] = {
        "total_questions": total,
        "action_match_count": matches,
        "action_match_rate": round(matches / total, 3) if total else 0.0,
        "results": results,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    execute_eval()

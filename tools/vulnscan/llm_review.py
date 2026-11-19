"""Summarize one A05 finding using the optional loopback inference API."""
import http.client
import json

# Only scanner-authored descriptions cross the model boundary. The original
# finding can contain parameter names, URLs, query values or response data.
OBSERVATIONS = {
    "SQL 인젝션 가능(오류 기반)": "The scanner observed a SQL error signature after changing an input.",
    "SQL 인젝션 가능(불리언 기반)": "The scanner observed different responses for true and false SQL conditions.",
    "반사형 XSS 가능": "The scanner observed its marker reflected without HTML escaping.",
}


def review_one_a05(findings, port, model="local-gpt2"):
    for finding in findings:
        if finding["owasp"] == "A05" and finding["status"] == "vuln":
            observation = OBSERVATIONS.get(finding["title"])
            if observation:
                finding["llm_review"] = request_review(observation, port, model)
                return


def request_review(observation, port, model="local-gpt2"):
    # model: 자체 모델은 "local-gpt2", Ollama는 "llama3"·"qwen2.5" 등.
    # 엔드포인트는 OpenAI 호환 /v1/chat/completions 로 동일 → 모델명만 바꾸면 전환.
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": (
            f"Scanner observation: {observation}\n"
            "In two short English sentences, explain what this suggests and how a developer "
            "can verify it in source code. Do not claim successful exploitation or data access."
        )}],
        "max_tokens": 64,
    }
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        connection.request("POST", "/v1/chat/completions", json.dumps(payload),
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Model API rejected the request")
        result = json.loads(response.read(16385))
        answer = result["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Model API reply is empty")
        return {"ok": True, "text": answer}
    except (OSError, http.client.HTTPException, ValueError, KeyError, IndexError, TypeError):
        return {"ok": False}
    finally:
        connection.close()

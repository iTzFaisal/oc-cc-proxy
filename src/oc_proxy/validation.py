from __future__ import annotations

import argparse
import json
from typing import Any

import httpx


def raise_for_status_with_body(response: httpx.Response, check_name: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = response.text[:1000]
        raise RuntimeError(f"{check_name} failed with HTTP {response.status_code}: {body}") from exc


def messages_payload(*, model: str, stream: bool = False, tools: bool = False) -> dict[str, Any]:
    prompt = "Use the get_status tool for target proxy."
    if not tools:
        prompt = "Reply with exactly: ok"
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 64,
        "stream": stream,
        "messages": messages,
    }
    if tools:
        payload["tools"] = [
            {
                "name": "get_status",
                "description": "Return a short status string.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                    "required": ["target"],
                },
            }
        ]
    return payload


def has_tool_use(content: Any) -> bool:
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_use" for block in content
    )


def get_tool_use_id(content: Any) -> str:
    if not isinstance(content, list):
        raise RuntimeError("tool response content is not a list")
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id"):
            return str(block["id"])
    raise RuntimeError(f"tool response did not include a tool_use id: {json.dumps(content)[:500]}")


def tool_result_payload(*, model: str, assistant_content: Any) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": 64,
        "messages": [
            {"role": "user", "content": "Use the get_status tool for target proxy."},
            {"role": "assistant", "content": assistant_content},
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": get_tool_use_id(assistant_content), "content": "ok"}],
            },
        ],
    }


def validate(base_url: str, model: str, api_key: str) -> int:
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    checks = [
        ("non-streaming text", messages_payload(model=model)),
        ("wildcard model passthrough", messages_payload(model=model)),
    ]
    with httpx.Client(timeout=60) as client:
        for name, payload in checks:
            response = client.post(f"{base_url.rstrip('/')}/v1/messages", headers=headers, json=payload)
            raise_for_status_with_body(response, name)
            body = response.json()
            if body.get("type") != "message" or "content" not in body:
                raise RuntimeError(f"{name} did not return an Anthropic-shaped message: {json.dumps(body)[:500]}")
            print(f"ok: {name}")

        response = client.post(
            f"{base_url.rstrip('/')}/v1/messages",
            headers=headers,
            json=messages_payload(model=model, tools=True),
        )
        raise_for_status_with_body(response, "tool definitions and tool_use response")
        body = response.json()
        tool_response_content = body.get("content")
        if not has_tool_use(tool_response_content):
            raise RuntimeError(f"tool definitions did not produce an Anthropic tool_use block: {json.dumps(body)[:500]}")
        print("ok: tool definitions and tool_use response")

        with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/v1/messages",
            headers=headers,
            json=messages_payload(model=model, stream=True),
        ) as response:
            raise_for_status_with_body(response, "streaming text")
            events = list(response.iter_lines())
            if not any("message_stop" in event or "[DONE]" in event for event in events):
                raise RuntimeError("streaming response did not include a terminal event")
            print("ok: streaming text and terminal event")

        with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/v1/messages",
            headers=headers,
            json=messages_payload(model=model, stream=True, tools=True),
        ) as response:
            raise_for_status_with_body(response, "streamed tool request")
            events = list(response.iter_lines())
            if not events:
                raise RuntimeError("streamed tool validation returned no events")
            event_text = "\n".join(events)
            required_parts = ["get_status", "tool", "id"]
            missing_parts = [part for part in required_parts if part not in event_text]
            if missing_parts:
                raise RuntimeError(f"streamed tool response missing expected parts {missing_parts}: {event_text[:1000]}")
            print("ok: streamed tool response preserves name, input, and identifier information")

        response = client.post(
            f"{base_url.rstrip('/')}/v1/messages",
            headers=headers,
            json=tool_result_payload(model=model, assistant_content=tool_response_content),
        )
        raise_for_status_with_body(response, "tool result follow-up")
        body = response.json()
        if body.get("type") != "message" or "content" not in body:
            raise RuntimeError(f"tool result follow-up did not return an Anthropic-shaped message: {json.dumps(body)[:500]}")
        print("ok: tool result follow-up")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Claude Code proxy compatibility against a running oc-cc-proxy.")
    parser.add_argument("--base-url", default="http://127.0.0.1:4000")
    parser.add_argument("--model", default="qwen3.6-plus")
    parser.add_argument("--api-key", default="not-a-real-anthropic-key")
    args = parser.parse_args()
    return validate(args.base_url, args.model, args.api_key)


if __name__ == "__main__":
    raise SystemExit(main())

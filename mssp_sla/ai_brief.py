"""Optional Phase B: explain verified metrics. Never a source of new numbers."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from mssp_sla.models import MetricsReport

# Default Chat Completions-compatible endpoint. Unused unless a key is present.
DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an MSSP operations assistant.
You receive a verified metrics JSON produced by deterministic Python code.

Hard rules:
- Explain only numbers, tickets, deadlines, and evidence already in the JSON.
- Cite evidence_id values when recommending actions.
- Do not invent metrics, deadlines, customer facts, business outcomes, or new ticket ids.
- Do not compute new SLA math. If a figure is not in the JSON, refuse it.
- If you cannot support a statement from the JSON, put it in refusals instead.

Return ONLY JSON with this shape:
{
  "narrative": "short operational summary citing evidence_ids",
  "recommended_actions": [
    {"evidence_ids": ["..."], "action": "...", "rationale": "..."}
  ],
  "refusals": ["..."]
}
"""

TICKET_ID_RE = re.compile(r"\b(?:TCK-|TICKET-|ROW-)\w+", re.IGNORECASE)
EVIDENCE_HINT_RE = re.compile(
    r"\b(?:dq|attention|ageing_backlog|response_sla_breach|resolve_sla_breach|"
    r"approaching_response|approaching_resolve):[A-Za-z0-9_.:-]+"
)


class AiBriefError(Exception):
    """Raised when the optional model path cannot produce a grounded section."""


def metrics_for_model(report: MetricsReport) -> dict[str, Any]:
    """Strip the payload down to verified counts and findings. No raw CSV rows."""
    payload = report.to_dict()
    # generated_at is a clock stamp, not a ticket metric; keep meta.as_of and verification.
    return payload


def _collect_known_ticket_ids(report: MetricsReport) -> set[str]:
    ids = {finding.ticket_id for finding in report.all_findings()}
    return ids


def validate_ai_payload(report: MetricsReport, payload: dict[str, Any]) -> list[str]:
    """Return problems that mean we must refuse the model text."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["model output is not a JSON object"]
    for key in ("narrative", "recommended_actions", "refusals"):
        if key not in payload:
            problems.append(f"missing key {key!r}")
    actions = payload.get("recommended_actions", [])
    if not isinstance(actions, list):
        problems.append("recommended_actions is not a list")
        return problems
    known_evidence = report.evidence_ids()
    known_tickets = _collect_known_ticket_ids(report)
    cited: list[str] = []
    text_blobs = [str(payload.get("narrative") or "")]
    for action in actions:
        if not isinstance(action, dict):
            problems.append("an action is not an object")
            continue
        evidence_ids = action.get("evidence_ids") or []
        if not evidence_ids:
            problems.append("an action is missing evidence_ids")
            continue
        for evidence_id in evidence_ids:
            cited.append(str(evidence_id))
            if evidence_id not in known_evidence:
                problems.append(f"unknown evidence_id cited: {evidence_id}")
        text_blobs.append(str(action.get("action") or ""))
        text_blobs.append(str(action.get("rationale") or ""))

    blob = "\n".join(text_blobs)
    for match in TICKET_ID_RE.findall(blob):
        if match not in known_tickets and match.upper() not in {t.upper() for t in known_tickets}:
            problems.append(f"unknown ticket id in model text: {match}")
    for match in EVIDENCE_HINT_RE.findall(blob):
        if match not in known_evidence:
            problems.append(f"unknown evidence id in model text: {match}")
    if actions and not cited:
        problems.append("actions were returned without any evidence citations")
    return problems


def render_ai_section(payload: dict[str, Any]) -> str:
    lines = [
        "The following text is an optional explanation of **already verified** Phase A numbers.",
        "It is not an independent source of metrics.",
        "",
        payload.get("narrative") or "",
        "",
    ]
    actions = payload.get("recommended_actions") or []
    if actions:
        lines.append("### Recommended actions (must cite Phase A evidence)")
        lines.append("")
        for index, action in enumerate(actions, start=1):
            cited = ", ".join(f"`{eid}`" for eid in action.get("evidence_ids") or [])
            lines.append(f"{index}. {action.get('action', '').strip()}")
            if cited:
                lines.append(f"   - Evidence: {cited}")
            rationale = (action.get("rationale") or "").strip()
            if rationale:
                lines.append(f"   - Rationale: {rationale}")
        lines.append("")
    refusals = payload.get("refusals") or []
    if refusals:
        lines.append("### Model refusals (would have required inventing facts)")
        lines.append("")
        for item in refusals:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def call_chat_completions(
    *,
    messages: list[dict[str, str]],
    api_key: str,
    api_url: str = DEFAULT_API_URL,
    model: str = DEFAULT_MODEL,
    timeout_seconds: float = 30.0,
) -> str:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = json.loads(response.read().decode("utf-8"))
    return raw["choices"][0]["message"]["content"]


def generate_ai_section(
    report: MetricsReport,
    *,
    api_key: str | None = None,
    api_url: str | None = None,
    model: str | None = None,
    llm_call: Callable[..., str] | None = None,
) -> tuple[str | None, str | None]:
    """Return (markdown_section, skip_or_error_reason).

    The model sees only verified metrics JSON. If it invents evidence, we drop it.
    """
    if not report.verification.passed:
        return None, "verification_failed"

    key = api_key if api_key is not None else os.environ.get("MSSP_SLA_AI_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    caller = llm_call or call_chat_completions
    if llm_call is None and not key:
        return None, "no_api_key"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(metrics_for_model(report), indent=2),
        },
    ]
    try:
        if llm_call is None:
            content = caller(
                messages=messages,
                api_key=key or "",
                api_url=api_url or os.environ.get("MSSP_SLA_AI_API_URL") or DEFAULT_API_URL,
                model=model or os.environ.get("MSSP_SLA_AI_MODEL") or DEFAULT_MODEL,
            )
        else:
            content = caller(messages=messages)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, OSError) as exc:
        return None, f"model_call_failed:{exc}"

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None, "model_output_not_json"

    problems = validate_ai_payload(report, payload)
    if problems:
        return None, "model_invented_or_ungrounded:" + "; ".join(problems)
    return render_ai_section(payload), None

"""V3: LLM semantic reviewer. Sends the reference pipeline source, the
target schema, and two deterministic data profiles (clean reference window
vs current batch) and asks for a structured failure judgment. The reviewer
never sees raw rows, oracle values, or fault labels. Stdlib-only transport
via rapidbench.panel.OpenRouterClient; keys come from the environment and
are never stored. Deterministic settings (temperature 0) and full logging
of model, prompt hash, and date, per reproducibility policy.
"""
from __future__ import annotations

import json
import re

PANEL = [
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4.5",
    "google/gemini-2.5-pro",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat",
]

SYSTEM = (
    "You are auditing the input data of a revenue-analytics pipeline for a "
    "customs administration. You are given the pipeline source, the target "
    "schema, a profile of the clean reference window, and a profile of the "
    "current batch. List any data-quality failures in the current batch "
    "that would materially distort duty revenue, chapter shares, effective "
    "duty rate, undervaluation screening, origin shares, or risk-flag "
    "precision. If the batch looks sound, return an empty list. Respond "
    "ONLY with JSON: {\"failures\": [{\"class\": str, \"evidence\": str, "
    "\"severity\": \"low|medium|high\"}]}."
)


def build_user_prompt(pipeline_src: str, schema: str,
                      ref_profile: str, cur_profile: str) -> str:
    return (f"SCHEMA:\n{schema}\n\nPIPELINE SOURCE:\n{pipeline_src}\n\n"
            f"REFERENCE WINDOW PROFILE:\n{ref_profile}\n\n"
            f"CURRENT BATCH PROFILE:\n{cur_profile}")


def parse_review(text: str) -> dict:
    """Fence-tolerant JSON extraction; raises ValueError if unparseable."""
    t = text.replace("```json", "```").strip()
    if "```" in t:
        blocks = re.findall(r"```(.*?)```", t, re.S)
        if blocks:
            t = blocks[-1].strip()
    if not t.startswith("{"):
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            raise ValueError("no JSON object in reply")
        t = m.group(0)
    obj = json.loads(t)
    if "failures" not in obj or not isinstance(obj["failures"], list):
        raise ValueError("missing 'failures' list")
    return obj

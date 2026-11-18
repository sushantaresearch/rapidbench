"""E1 panel driver: frozen prompt -> model -> pipeline code -> sandboxed
execution -> RDM scoring -> verdict.

The model client is injectable so the identical driver path runs in two modes:
  MockClient        offline end-to-end tests (no network, no key)
  OpenRouterClient  real panel; requires OPENROUTER_API_KEY in the environment

The API key is only ever read from the environment at call time. It is never
written to disk, results, or manifests.

CLI:
  python3 -m rapidbench.panel --mock                # offline harness proof
  python3 -m rapidbench.panel --config configs/panel.yaml   # real panel
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from .executor import classify, run_pipeline, score_pipeline
from .substrate import generate_synthetic_declarations
from .tasks import e1_oracle

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "pipeline_gen_prompt.md"
_FENCE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def load_prompt() -> tuple[str, str]:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()[:16]


def extract_code(reply: str) -> str:
    """Last complete fenced block if any; otherwise the raw reply with any
    dangling fence lines stripped. A completion cut off by the token budget
    can leave an opening ```python with no closing fence; without stripping,
    the fence itself becomes line 1 of the executed file."""
    blocks = _FENCE.findall(reply)
    if blocks:
        return blocks[-1].strip()
    lines = [ln for ln in reply.splitlines()
             if not ln.lstrip().startswith("```")]
    return "\n".join(lines).strip()


class OpenRouterClient:
    """Minimal chat-completions client. Retries transient failures twice."""

    def __init__(self, model: str, temperature: float = 0.2,
                 base_url: str = "https://openrouter.ai/api/v1"):
        self.model = model
        self.temperature = temperature
        self.base_url = base_url

    @property
    def name(self) -> str:
        return self.model

    def generate(self, prompt: str, system: str | None = None) -> str:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Export it in the shell "
                "before running the real panel; it is never stored.")
        msgs = ([{"role": "system", "content": system}] if system else []) \
            + [{"role": "user", "content": prompt}]
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": 8000,
            "messages": msgs,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode())
                choice = data["choices"][0]
                self.last_finish_reason = choice.get("finish_reason", "")
                return choice["message"]["content"]
            except (urllib.error.URLError, urllib.error.HTTPError,
                    TimeoutError, json.JSONDecodeError, KeyError) as err:
                last_err = err
                code = getattr(err, "code", None)
                if code in (401, 402, 403):
                    raise RuntimeError(
                        f"OpenRouter non-retryable HTTP {code} "
                        f"({self.model}): {err!r}") from err
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"OpenRouter call failed after 3 attempts "
                           f"({self.model}): {last_err!r}")


_MOCK_HEADER = """import sys, json
import pandas as pd
df = pd.read_csv(sys.argv[1]{read_kw})
ch = df["hs6"].astype(str).str[:2]
tot = float(df["duty_paid_usd"].sum())
uv = df["cif_usd"] / df["qty"]
med = uv.groupby(df["hs6"]).transform("median")
out = {{
 "s1_duty_by_month": df.groupby("month")["duty_paid_usd"].sum().to_dict(),
 "s2_chapter_duty_share": (df.groupby(ch)["duty_paid_usd"].sum()/tot).to_dict(),
 "s3_effective_duty_rate": {s3},
 "s4_uv_below_half_median_share": float((uv < 0.5*med).mean()),
 "s5_top_origin_duty_share": float(df.groupby("origin_iso3")["duty_paid_usd"].sum().max())/tot,
}}
print(json.dumps(out))"""

_MOCK_REPLIES = {
    "mock/correct": "Here is the pipeline you asked for.\n\n```python\n"
    + _MOCK_HEADER.format(read_kw=', dtype={"hs6": str}',
                          s3='tot / float(df["cif_usd"].sum())')
    + "\n```\nLet me know if you need anything else.",
    "mock/bug-hs-dtype": "```python\n"
    + _MOCK_HEADER.format(read_kw="",
                          s3='tot / float(df["cif_usd"].sum())')
    + "\n```",
    "mock/bug-rate-agg": "```python\n"
    + _MOCK_HEADER.format(read_kw=', dtype={"hs6": str}',
                          s3='float((df["duty_paid_usd"]/df["cif_usd"]).mean())')
    + "\n```",
    "mock/contract-violation": "```python\nimport json\n"
    "print(json.dumps({'wrong_key': 1}))\n```",
    "mock/crash": "```python\nimport sys\nraise ValueError('boom')\n```",
    "mock/chapter-col-correct": "```python\nimport sys, json\nimport pandas as pd\ndf = pd.read_csv(sys.argv[1])\ntot = float(df[\"duty_paid_usd\"].sum())\nuv = df[\"cif_usd\"] / df[\"qty\"]\nmed = uv.groupby(df[\"hs6\"]).transform(\"median\")\nout = {\n \"s1_duty_by_month\": df.groupby(\"month\")[\"duty_paid_usd\"].sum().to_dict(),\n \"s2_chapter_duty_share\": (df.groupby(\"chapter\")[\"duty_paid_usd\"].sum()/tot).to_dict(),\n \"s3_effective_duty_rate\": tot / float(df[\"cif_usd\"].sum()),\n \"s4_uv_below_half_median_share\": float((uv < 0.5*med).mean()),\n \"s5_top_origin_duty_share\": float(df.groupby(\"origin_iso3\")[\"duty_paid_usd\"].sum().max())/tot,\n}\nprint(json.dumps(out))\n```",
    "mock/truncated-fence": "```python\nimport sys, json\n"
    "import pandas as pd\ndf = pd.read_csv(sys.argv[1])\n"
    "out = {\n    'a': 1,",
}


class MockClient:
    """Canned replies keyed by model name; exercises fence extraction,
    the subprocess path, scoring, and every verdict branch offline."""

    def __init__(self, model: str, temperature: float = 0.2):
        if model not in _MOCK_REPLIES:
            raise KeyError(f"unknown mock model {model}")
        self.model = model

    @property
    def name(self) -> str:
        return self.model

    def generate(self, prompt: str, system: str | None = None) -> str:
        assert prompt, "prompt must be non-empty"
        self.last_finish_reason = (
            "length" if self.model == "mock/truncated-fence" else "stop")
        return _MOCK_REPLIES[self.model]


def _slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def run_panel(models: list[str], k: int, client_cls, out_prefix: str,
              temperature: float = 0.2, n_rows: int = 20000,
              seed: int = 42, results_dir: str | Path = "results") -> pd.DataFrame:
    results_dir = Path(results_dir)
    pipe_dir = results_dir / f"{out_prefix}_pipelines"
    pipe_dir.mkdir(parents=True, exist_ok=True)

    prompt, prompt_sha = load_prompt()
    clean, _ = generate_synthetic_declarations(n=n_rows, seed=seed)
    oracle = e1_oracle(clean)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False,
                                     mode="w") as f:
        clean.to_csv(f.name, index=False)
        csv_path = f.name

    rows = []
    for model in models:
        client = client_cls(model, temperature=temperature)
        mdir = pipe_dir / _slug(model)
        mdir.mkdir(exist_ok=True)
        for j in range(k):
            t0 = time.time()
            reply = client.generate(prompt)
            code = extract_code(reply)
            (mdir / f"sample_{j}.py").write_text(code, encoding="utf-8")
            res = run_pipeline(code, csv_path)
            scores = score_pipeline(res["stats"], oracle) if res["ok"] else None
            verdict = classify(res, scores)
            rows.append({
                "model": client.name, "sample": j, "verdict": verdict,
                "ok": res["ok"],
                **({f"rdm_{s[:2]}": round(v, 6) for s, v in scores.items()}
                   if scores else {}),
                "code_sha": hashlib.sha256(code.encode()).hexdigest()[:12],
                "runtime_s": round(time.time() - t0, 2),
                "finish_reason": getattr(client, "last_finish_reason", ""),
                "error": (res["error"] or "")[:200],
            })

    df = pd.DataFrame(rows)
    df.to_csv(results_dir / f"{out_prefix}_results.csv", index=False)
    manifest = {
        "experiment": "E1", "mode": out_prefix,
        "client": client_cls.__name__, "models": models, "k": k,
        "temperature": temperature, "prompt_sha256_16": prompt_sha,
        "substrate": {"kind": "synthetic", "n": n_rows, "seed": seed},
        "materiality_rdm": 0.01,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (results_dir / f"{out_prefix}_manifest.json").write_text(
        json.dumps(manifest, indent=2))
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--config", default="configs/panel.yaml")
    ap.add_argument("--k", type=int, default=None)
    args = ap.parse_args()

    if args.mock:
        df = run_panel(list(_MOCK_REPLIES), k=args.k or 2,
                       client_cls=MockClient, out_prefix="e1_mock")
    else:
        import yaml
        cfg = yaml.safe_load(open(args.config))
        df = run_panel(cfg["models"], k=args.k or cfg.get("k", 3),
                       client_cls=OpenRouterClient,
                       temperature=cfg.get("temperature", 0.2),
                       out_prefix="e1")
    print(df.groupby("model")["verdict"]
            .apply(lambda s: ", ".join(sorted(set(s)))).to_string())


if __name__ == "__main__":
    main()

"""LLM access through an OpenAI-compatible API, with a response cache and rate-limit retries.

Configuration comes from environment variables (or a .env file), never from code:
    LLM_API_KEY   the API key (required)
    LLM_BASE_URL  default: Google Gemini's OpenAI-compatible endpoint
    LLM_MODEL         default: gemini-3.5-flash-lite, the model we tested with
    LLM_BACKUP_MODEL  default on Gemini: gemini-2.5-flash, used when LLM_MODEL runs out of quota

Every response is cached on disk under cache/llm/, keyed by the full request, so a repeated
run of the same questions costs no quota. Set LLM_CACHE=0 to disable the cache.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

from graphkit.llm import GEMINI_BASE_URL, _load_dotenv, make_client

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache" / "llm"
MAX_RETRIES = 6
TESTED_MODEL = "gemini-3.5-flash-lite"   # scored 29/30 on the public set
DEFAULT_BACKUP_MODEL = "gemini-2.5-flash"  # separate free-tier quota; also tested
MAX_WAIT_S = 120  # a rate limit that asks us to wait longer than this is treated as an exhausted quota


class QuotaExhausted(RuntimeError):
    """The provider's daily (or other long) quota is used up; retrying now is pointless."""


def triage_llm(use_cache: bool | None = None) -> "LLM | None":
    """A separate LLM for the triage step, if LLM_TRIAGE_MODEL is set; else None (triage uses the main LLM).

    LLM_TRIAGE_BASE_URL and LLM_TRIAGE_API_KEY default to the main LLM_BASE_URL and LLM_API_KEY,
    so a stronger model on another provider (e.g. Groq) can do the small triage calls while the
    planner stays on the main provider.
    """
    _load_dotenv()
    model = os.environ.get("LLM_TRIAGE_MODEL")
    if not model:
        return None
    from openai import OpenAI
    key = os.environ.get("LLM_TRIAGE_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("Set LLM_TRIAGE_API_KEY or LLM_API_KEY (see .env.example).")
    base = os.environ.get("LLM_TRIAGE_BASE_URL") or os.environ.get("LLM_BASE_URL", GEMINI_BASE_URL)
    return LLM(use_cache, model=model, client=OpenAI(api_key=key, base_url=base))


class LLM:
    def __init__(self, use_cache: bool | None = None, model: str | None = None, client=None,
                 backup_model: str | None = None):
        _load_dotenv()
        self.model = model or os.environ.get("LLM_MODEL") or TESTED_MODEL
        if client is None:
            on_gemini = os.environ.get("LLM_BASE_URL", GEMINI_BASE_URL).rstrip("/") == GEMINI_BASE_URL.rstrip("/")
            # used once the main model's quota is gone
            backup_model = os.environ.get("LLM_BACKUP_MODEL") or (DEFAULT_BACKUP_MODEL if on_gemini else None)
            client = make_client()
        self.backup_model = backup_model
        # retries are ours (below): the SDK's own retries would sleep through a daily-quota error
        self.client = client.with_options(max_retries=0, timeout=120)
        if use_cache is None:
            use_cache = os.environ.get("LLM_CACHE", "1") != "0"
        self.use_cache = use_cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def chat(self, messages: list[dict], tools: list[dict], tool_choice: str = "auto") -> tuple[dict, dict]:
        """Returns (assistant message as a plain dict, info dict with usage/cached/latency)."""
        try:
            return self._chat(messages, tools, tool_choice)
        except QuotaExhausted:
            if not self.backup_model or self.backup_model == self.model:
                raise
            print(f"Quota for {self.model} is used up; switching to LLM_BACKUP_MODEL {self.backup_model}.", flush=True)
            self.model = self.backup_model
            return self._chat(messages, tools, tool_choice)

    def _chat(self, messages: list[dict], tools: list[dict], tool_choice: str) -> tuple[dict, dict]:
        request = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": tool_choice}
        key = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = CACHE_DIR / f"{key}.json"
        if self.use_cache and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data["message"], {"cached": True, "usage": data.get("usage"), "latency_s": 0.0}

        delay = 5.0
        for attempt in range(MAX_RETRIES):
            t0 = time.time()
            try:
                resp = self.client.chat.completions.create(**request)
                break
            except Exception as exc:  # rate limits and transient server errors are retried
                text = f"{exc} {json.dumps(getattr(exc, 'body', None), default=str)}"  # details are in the body
                retryable = type(exc).__name__ in ("APITimeoutError", "APIConnectionError", "InternalServerError") or \
                    any(s in text for s in ("429", "RESOURCE_EXHAUSTED", "rate", "503", "500", "UNAVAILABLE",
                                            "overloaded", "timeout", "Timeout", "timed out"))
                if not retryable or attempt == MAX_RETRIES - 1:
                    raise
                hint = re.search(r"retryDelay'?\"?:\s*'?\"?([0-9.]+)s", text) or re.search(r"retry in ([0-9.]+)s", text)
                wait = float(hint.group(1)) + 1 if hint else delay
                if "PerDay" in text or wait > MAX_WAIT_S:
                    raise QuotaExhausted(f"The provider's quota for {self.model} is used up (retry in about "
                                         f"{wait / 3600:.1f} h). Wait, or set LLM_MODEL / LLM_BASE_URL to another "
                                         f"model or provider. Provider message: {text[:300]}") from exc
                time.sleep(wait)
                delay = min(delay * 2, 90)
        latency = time.time() - t0
        if not resp.choices:
            raise RuntimeError("The LLM returned no choices.")
        message = resp.choices[0].message.model_dump(exclude_none=True)
        message.setdefault("role", "assistant")
        usage = resp.usage.model_dump(exclude_none=True) if getattr(resp, "usage", None) else None
        if self.use_cache:
            path.write_text(json.dumps({"message": message, "usage": usage}, ensure_ascii=False), encoding="utf-8")
        return message, {"cached": False, "usage": usage, "latency_s": round(latency, 3)}

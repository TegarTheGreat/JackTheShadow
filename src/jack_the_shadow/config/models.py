"""
Jack The Shadow — Model Catalog

Auto-discovers function-calling capable models from the Cloudflare
Workers AI API.  Falls back to a static catalog if the API is
unreachable or credentials are not yet set.

Format: {display_name: model_id}
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

logger = logging.getLogger("jshadow.config.models")

# ── Static fallback (kept in sync with Cloudflare manually) ──────────
_STATIC_CATALOG: dict[str, str] = {
    "gpt-oss-120b (OpenAI, flagship)": "@cf/openai/gpt-oss-120b",
    "gpt-oss-20b (OpenAI, fast)": "@cf/openai/gpt-oss-20b",
    "kimi-k2.5 (Moonshot, 256k ctx)": "@cf/moonshotai/kimi-k2.5",
    "glm-4.7-flash (Zhipu, fast)": "@cf/zai-org/glm-4.7-flash",
    "llama-4-scout (Meta, multimodal)": "@cf/meta/llama-4-scout-17b-16e-instruct",
    "llama-3.3-70b (Meta, FP8 fast)": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "gemma-4-26b (Google, reasoning)": "@cf/google/gemma-4-26b-a4b-it",
    "nemotron-3-120b (NVIDIA, agentic)": "@cf/nvidia/nemotron-3-120b-a12b",
    "qwen3-30b (Alibaba, MoE)": "@cf/qwen/qwen3-30b-a3b-fp8",
    "qwq-32b (Alibaba, reasoning)": "@cf/qwen/qwq-32b",
    "mistral-small-3.1 (Mistral, 128k)": "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "deepseek-r1-32b (DeepSeek, reasoning)": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
    "granite-4.0-micro (IBM, efficient)": "@cf/ibm-granite/granite-4.0-h-micro",
}

# ── Cache for live-fetched models ────────────────────────────────────
_cached_catalog: Optional[dict[str, str]] = None
_cache_time: float = 0
_CACHE_TTL: float = 600  # 10 minutes


def _build_display_name(model: dict[str, Any]) -> str:
    """Build a human-friendly display name from API model data."""
    name: str = model.get("name", "")
    # Extract short name: @cf/openai/gpt-oss-120b → gpt-oss-120b
    short = name.rsplit("/", 1)[-1] if "/" in name else name
    # Extract org: @cf/openai/gpt-oss-120b → openai
    parts = name.split("/")
    org = parts[1] if len(parts) >= 3 else ""

    props = {p["property_id"]: p["value"] for p in (model.get("properties") or [])}
    ctx = props.get("context_window", "")
    flags: list[str] = []
    if props.get("reasoning") == "true":
        flags.append("reasoning")
    if props.get("vision") == "true":
        flags.append("vision")

    # Format context window
    ctx_str = ""
    if ctx:
        try:
            ctx_k = int(ctx) // 1000
            ctx_str = f", {ctx_k}k ctx"
        except (ValueError, TypeError):
            pass

    org_display = org.replace("-", " ").title() if org else ""
    flag_str = ", ".join(flags)
    meta = ", ".join(filter(None, [org_display, flag_str])) + ctx_str
    return f"{short} ({meta})" if meta else short


def fetch_models(
    account_id: str,
    api_token: str,
    force: bool = False,
) -> dict[str, str]:
    """Fetch function-calling Text Generation models from Cloudflare.

    Results are cached for ``_CACHE_TTL`` seconds.  Falls back to the
    static catalog on any error.
    """
    global _cached_catalog, _cache_time

    if not force and _cached_catalog is not None and (time.time() - _cache_time) < _CACHE_TTL:
        return _cached_catalog

    try:
        url = (
            f"https://api.cloudflare.com/client/v4/accounts"
            f"/{account_id}/ai/models/search"
        )
        headers = {"Authorization": f"Bearer {api_token}"}
        resp = requests.get(
            url, headers=headers, params={"task": "Text Generation"}, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            logger.warning("Model search API returned success=false")
            return _STATIC_CATALOG

        catalog: dict[str, str] = {}
        for m in data.get("result", []):
            props = {p["property_id"]: p["value"] for p in (m.get("properties") or [])}
            # Only include function-calling models (Jack needs tools)
            if props.get("function_calling") != "true":
                continue
            # Skip deprecated models
            if props.get("planned_deprecation_date"):
                continue
            # Skip beta models
            if props.get("beta") == "true":
                continue

            model_id = m.get("name", "")
            display = _build_display_name(m)
            catalog[display] = model_id

        if catalog:
            # Sort: larger/flagship models first, then alphabetically
            _cached_catalog = dict(sorted(catalog.items(), key=lambda x: x[1]))
            _cache_time = time.time()
            logger.info("Fetched %d function-calling models from Cloudflare", len(_cached_catalog))
            return _cached_catalog

        logger.warning("No function-calling models found, using static catalog")
        return _STATIC_CATALOG

    except Exception as exc:
        logger.debug("Model fetch failed (%s), using static catalog", exc)
        return _STATIC_CATALOG


def get_model_catalog(
    account_id: str = "",
    api_token: str = "",
) -> dict[str, str]:
    """Get the model catalog — live if credentials available, static otherwise."""
    if account_id and api_token:
        return fetch_models(account_id, api_token)
    return _STATIC_CATALOG


# Legacy alias for imports that expect the constant
MODEL_CATALOG: dict[str, str] = _STATIC_CATALOG

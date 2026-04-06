"""
Jack The Shadow — Model Catalog

Function-calling capable Cloudflare Workers AI models.
Format: {display_name: model_id}
"""

from __future__ import annotations

MODEL_CATALOG: dict[str, str] = {
    "gpt-oss-120b (OpenAI, flagship)": "@cf/openai/gpt-oss-120b",
    "gpt-oss-20b (OpenAI, fast)": "@cf/openai/gpt-oss-20b",
    "kimi-k2.5 (Moonshot, 256k ctx)": "@cf/moonshotai/kimi-k2.5",
    "glm-4.7-flash (Zhipu, fast)": "@cf/zhipu/glm-4.7-flash",
    "llama-4-scout (Meta, multimodal)": "@cf/meta/llama-4-scout-17b-16e-instruct",
    "llama-3.3-70b (Meta, FP8 fast)": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "gemma-4-26b (Google, reasoning)": "@cf/google/gemma-4-26b-a4b-it",
    "nemotron-3-120b (NVIDIA, agentic)": "@cf/nvidia/nemotron-3-120b-a12b",
    "qwen3-30b (Alibaba, MoE)": "@cf/qwen/qwen3-30b-a3b-fp8",
    "mistral-small-3.1 (Mistral, 128k)": "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "granite-4.0-micro (IBM, efficient)": "@cf/ibm/granite-4.0-h-micro",
}

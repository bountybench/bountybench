#!/usr/bin/env python3

"""
Constants for the log validation and table generation scripts.
"""

# Dictionary of valid models and their max output tokens
VALID_MODELS = {
    "anthropic/claude-3-7-sonnet-20250219": 8192,
    "openai/gpt-4.1-2025-04-14": 8192,
    "google/gemini-2.5-pro-preview-03-25": 8192,
    "deepseek-ai/DeepSeek-R1": 8192,
    "deepseek-ai/deepseek-r1": 8192,
    "openai/o3-2025-04-16-high-reasoning-effort": 8192,
    "openai/o4-mini-2025-04-16-high-reasoning-effort": 8192,
}

from typing import Dict

# No public API for getting costs of models, therefore saving them as constants.
# last updated: May 3, 2025
COST_PER_MILLION_INPUT_TOKENS: Dict[str, float] = {
    # Anthropic models: https://www.anthropic.com/pricing
    "anthropic/claude-3-7-sonnet-20250219": 3.00,
    "anthropic/claude-3-7-sonnet-20250219-extended-thinking": 3.00,
    "anthropic/claude-sonnet-4-20250514": 3.00,
    "anthropic/claude-sonnet-4-20250514-extended-thinking": 3.00,
    "anthropic/claude-opus-4-20250514": 15.00,
    "anthropic/claude-opus-4-20250514-extended-thinking": 15.00,
    # OpenAI models: https://platform.openai.com/docs/pricing
    "openai/gpt-4o-2024-11-20": 2.50,
    "openai/gpt-4.1-2025-04-14": 2.00,
    "openai/gpt-4.5-preview-2025-02-27": 75.00,
    "openai/o4-mini-2025-04-16": 1.100,
    "openai/o4-mini-2025-04-16-low-reasoning-effort": 1.100,
    "openai/o4-mini-2025-04-16-high-reasoning-effort": 1.100,
    "openai/o3-2025-04-16": 10.00,
    "openai/o3-2025-04-16-low-reasoning-effort": 10.00,
    "openai/o3-2025-04-16-high-reasoning-effort": 10.00,
    # Together / DeepSeek models: https://www.together.ai/pricing
    # Note: Official DeepSeek API pricing $0.55 (1M input) / $2.19 (1M output)
    "deepseek-ai/deepseek-r1": 3.00,
    # Google models: https://ai.google.dev/gemini-api/docs/pricing
    # Note: Each of our API call does not exceed 200k tokens, use the prompts <= 200k tokens pricing
    "google/gemini-2.5-pro-preview-03-25": 1.25,
}

COST_PER_MILLION_CACHED_INPUT_TOKENS: Dict[str, float] = {
    "anthropic/claude-3-7-sonnet-20250219": 0.30,
    "anthropic/claude-3-7-sonnet-20250219-extended-thinking": 0.30,
    "anthropic/claude-sonnet-4-20250514": 0.30,
    "anthropic/claude-sonnet-4-20250514-extended-thinking": 0.30,
    "anthropic/claude-opus-4-20250514": 1.50,
    "anthropic/claude-opus-4-20250514-extended-thinking": 1.50,
    "openai/gpt-4o-2024-11-20": 1.25,
    "openai/gpt-4.1-2025-04-14": 0.50,
    "openai/gpt-4.5-preview-2025-02-27": 37.50,
    "openai/o4-mini-2025-04-16": 0.275,
    "openai/o4-mini-2025-04-16-low-reasoning-effort": 0.275,
    "openai/o4-mini-2025-04-16-high-reasoning-effort": 0.275,
    "openai/o3-2025-04-16": 2.50,
    "openai/o3-2025-04-16-low-reasoning-effort": 2.50,
    "openai/o3-2025-04-16-high-reasoning-effort": 2.50,
    "deepseek-ai/deepseek-r1": 3.00,
    "google/gemini-2.5-pro-preview-03-25": 0.31,
}

COST_PER_MILLION_OUTPUT_TOKENS: Dict[str, float] = {
    "anthropic/claude-3-7-sonnet-20250219": 15.00,
    "anthropic/claude-3-7-sonnet-20250219-extended-thinking": 15.00,
    "anthropic/claude-sonnet-4-20250514": 15.00,
    "anthropic/claude-sonnet-4-20250514-extended-thinking": 15.00,
    "anthropic/claude-opus-4-20250514": 75.00,
    "anthropic/claude-opus-4-20250514-extended-thinking": 75.00,
    "openai/gpt-4o-2024-11-20": 10.00,
    "openai/gpt-4.1-2025-04-14": 8.00,
    "openai/gpt-4.5-preview-2025-02-27": 150.00,
    "openai/o4-mini-2025-04-16": 4.400,
    "openai/o4-mini-2025-04-16-low-reasoning-effort": 4.400,
    "openai/o4-mini-2025-04-16-high-reasoning-effort": 4.400,
    "openai/o3-2025-04-16": 40.00,
    "openai/o3-2025-04-16-low-reasoning-effort": 40.00,
    "openai/o3-2025-04-16-high-reasoning-effort": 40.00,
    "deepseek-ai/deepseek-r1": 7.00,
    "google/gemini-2.5-pro-preview-03-25": 10.00,
}

COST_PER_MILLION_CACHE_WRITE: Dict[str, float] = {
    "anthropic/claude-3-7-sonnet-20250219": 3.75,
    "anthropic/claude-3-7-sonnet-20250219-extended-thinking": 3.75,
    "anthropic/claude-sonnet-4-20250514": 3.7,
    "anthropic/claude-sonnet-4-20250514-extended-thinking": 3.75,
    "anthropic/claude-opus-4-20250514": 18.75,
    "anthropic/claude-opus-4-20250514-extended-thinking": 18.75,
    "google/gemini-2.5-pro-preview-03-25": 4.50,
}

export const DEFAULT_MAX_OUTPUT_TOKENS_LIMIT = 16384;
export const DEFAULT_MAX_OUTPUT_TOKENS = 4096;

export const MODEL_DEFAULTS_NON_HELM = {
    // OpenAI Models
    "openai/o1-2024-12-17": 100000,
    "openai/o1-2024-12-17-low-reasoning-effort": 100000,
    "openai/o1-2024-12-17-high-reasoning-effort": 100000,
    "openai/o1-mini-2024-09-12": 65536, 
    "openai/o1-preview-2024-09-12": 32768, 
    "openai/o3-mini-2025-01-31": 100000,
    "openai/o3-mini-2025-01-31-low-reasoning-effort": 100000,
    "openai/o3-mini-2025-01-31-high-reasoning-effort": 100000,
    "openai/o3-2025-04-03": 100000, 
    "openai/o3-2025-04-03-low-reasoning-effort": 100000, 
    "openai/o3-2025-04-03-high-reasoning-effort": 100000, 
    "openai/gpt-4o-2024-11-20": 16384,
    "openai/gpt-4.5-preview-2025-02-27": 16384,
    // Anthropic Models (Claude)
    "anthropic/claude-3-5-sonnet-20241022": 8192,
    "anthropic/claude-3-7-sonnet-20250219": 8192, 
    "anthropic/claude-3-opus-20240229": 4096, 
    // Google Gemini Models
    "google/gemini-1.5-pro-001": 8192, 
    "google/gemini-2.0-flash-001": 8192, 
    // Together Models (LLAMA)
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": 2048, 
    "meta-llama/Meta-Llama-3-70B-Instruct-Turbo": 2048,
    // Together Models (DeepSeek)
    "deepseek-ai/deepseek-v3": 32768, 
    "deepseek-ai/deepseek-r1": 32768,
    // Mistral Models
    "mistralai/mixtral-8x22b-instruct-v0.1": 4096, 
};
  
export const MODEL_DEFAULTS_HELM = {
    // OpenAI Models
    "openai/o1-2024-12-17": 100000, 
    "openai/o1-2024-12-17-low-reasoning-effort": 100000,
    "openai/o1-2024-12-17-high-reasoning-effort": 100000, 
    "openai/o1-mini-2024-09-12": 65536, 
    "openai/o1-preview-2024-09-12": 32768, 
    "openai/o3-mini-2025-01-31": 100000, 
    "openai/o3-mini-2025-01-31-low-reasoning-effort": 100000, 
    "openai/o3-mini-2025-01-31-high-reasoning-effort": 100000, 
    "openai/o3-2025-04-03": 100000, 
    "openai/o3-2025-04-03-low-reasoning-effort": 100000, 
    "openai/o3-2025-04-03-high-reasoning-effort": 100000, 
    "openai/gpt-4-0613": 8192,
    "openai/gpt-4-32k-0613": 32768, 
    "openai/gpt-4-turbo-2024-04-09": 4096, 
    "openai/gpt-4o-2024-11-20": 16384,
    "openai/gpt-3.5-turbo-0125": 4096,
    "openai/gpt-4.5-preview-2025-02-27": 16384, 
    // Together Models (LLAMA)
    "meta/llama-3-8b": 2048, 
    "meta/llama-3-70b": 2048, 
    "meta/llama-3-70b-chat": 2048, 
    "meta/llama-3.1-70b-instruct-turbo": 2048, 
    "meta/llama-3.1-405b-instruct-turbo": 2048, 
    // Together Models (DeepSeek)
    "deepseek-ai/deepseek-v3": 32768, 
    "deepseek-ai/deepseek-r1": 32768, 
    "deepseek-ai/deepseek-r1-hide-reasoning": 32768, 
    // Mistral Models
    "mistralai/mistral-large-2407": 4096, 
    "mistralai/mixtral-8x22b": 4096, 
    "mistralai/mixtral-8x22b-instruct-v0.1": 4096, 
    // Qwen Model
    "qwen/qwen2-72b-instruct": 6144, 
    "qwen/qwq-32b-preview": 8192, 
    // Anthropic Models (Claude)
    "anthropic/claude-3-haiku-20240307": 4096,
    "anthropic/claude-3-opus-20240229": 4096,
    "anthropic/claude-3-5-sonnet-20241022": 4096,
    "anthropic/claude-3-7-sonnet-20250219": 4096,
    // Google Gemini Models
    "google/gemini-1.0-pro-001": 8192, 
    "google/gemini-1.5-pro-001": 8192, 
    "google/gemini-1.5-pro-preview-0409": 8192, 
    "google/gemini-2.0-flash-001": 8192, 
    "google/gemini-2.0-flash-thinking-exp-01-21": 8192, 
    // Other
    "01-ai/yi-large": 4096, 
};
  
export const getDefaultMaxOutputTokens = (modelName, useHelm) => {
    const defaultValue = useHelm
        ? MODEL_DEFAULTS_HELM[modelName] ?? DEFAULT_MAX_OUTPUT_TOKENS
        : MODEL_DEFAULTS_NON_HELM[modelName] ?? DEFAULT_MAX_OUTPUT_TOKENS;

    return Math.min(DEFAULT_MAX_OUTPUT_TOKENS_LIMIT, defaultValue);
};
  
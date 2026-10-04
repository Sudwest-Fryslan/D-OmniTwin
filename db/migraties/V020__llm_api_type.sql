-- v20: type LLM-API per configuratie (#88, ADR 0001)
-- 'ollama' = Ollama-eigen API (/api/generate), het bestaande gedrag
-- 'openai' = OpenAI Chat Completions (/v1/chat/completions): Ollama /v1, vLLM, LiteLLM, ...
-- Bestaande rijen krijgen 'ollama'. Idempotent.
ALTER TABLE llm_config
    ADD COLUMN IF NOT EXISTS api_type text NOT NULL DEFAULT 'ollama'
    CHECK (api_type IN ('ollama', 'openai'));

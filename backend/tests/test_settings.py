from app.config import get_settings


def test_parse_and_resume_defaults():
    settings = get_settings()
    assert settings.llm_parse_model == "qwen3:4b"
    assert settings.llm_rerank_model == "lfm3:1.7b"
    assert settings.llm_fallback_model == "llama3.2:3b"
    assert settings.llm_num_ctx == 8192
    assert settings.resume_max_bytes == 5 * 1024 * 1024
    assert settings.resume_max_chars == 50_000

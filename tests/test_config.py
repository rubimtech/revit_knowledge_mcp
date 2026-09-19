from revit_knowledge_mcp.config import AppConfig, load_config


def test_defaults_without_file(tmp_path):
    config = load_config(tmp_path / "missing.yaml")
    assert config.qdrant.mode == "local"
    assert config.embed.model == "bge-m3"
    assert config.docs.year == 2025
    assert config.collections, "default collections should be populated"
    assert "revit_api_knowledge" in [c.name for c in config.collections]


def test_yaml_values(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        """
qdrant:
  mode: remote
  remote:
    url: https://example.test/knowledge
embed:
  mode: cloud
  cloud:
    model: baai/bge-m3
docs:
  year: 2024
collections:
  - name: custom_collection
    platform: revit
    description: custom
""",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.qdrant.mode == "remote"
    assert config.qdrant.remote.url == "https://example.test/knowledge"
    assert config.embed.mode == "cloud"
    assert config.docs.year == 2024
    assert [c.name for c in config.collections] == ["custom_collection"]


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("RKM_QDRANT_MODE", "remote")
    monkeypatch.setenv("RKM_QDRANT_URL", "https://env.test/qdrant")
    monkeypatch.setenv("RKM_EMBED_MODE", "cloud")
    monkeypatch.setenv("POLZA_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_VECTOR_STORE_ID", "vs-test")
    config = load_config(tmp_path / "missing.yaml")
    assert config.qdrant.mode == "remote"
    assert config.qdrant.remote.url == "https://env.test/qdrant"
    assert config.embed.mode == "cloud"
    assert config.embed.cloud.api_key == "secret"
    assert config.openai.api_key == "sk-test"
    assert config.openai.vector_store_id == "vs-test"


def test_app_config_defaults_are_independent():
    first = AppConfig()
    second = AppConfig()
    first.qdrant.local.port = 9999
    assert second.qdrant.local.port == 6333

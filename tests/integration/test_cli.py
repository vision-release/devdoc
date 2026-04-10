from __future__ import annotations

from click.testing import CliRunner

from devdoc import cli


def test_mcp_config_sse_outputs_localhost_url():
    runner = CliRunner()

    result = runner.invoke(
        cli.main, ["mcp-config", "--transport", "sse", "--port", "9090"]
    )

    assert result.exit_code == 0
    assert "http://localhost:9090/sse" in result.output


def test_search_command_uses_built_index(monkeypatch):
    class StubIndex:
        def search(self, query, source=None, max_results=10):
            assert query == "asyncio"
            assert source == "python"
            assert max_results == 5
            return [
                {
                    "title": "Asyncio Guide",
                    "path": "python/guide.md",
                    "snippet": "asyncio example",
                }
            ]

    runner = CliRunner()
    monkeypatch.setattr(
        cli.config, "list_sources", lambda: {"python": {"path": "/tmp/python"}}
    )
    monkeypatch.setattr("devdoc.search.build_index", lambda sources: StubIndex())

    result = runner.invoke(
        cli.main, ["search", "asyncio", "--source", "python", "--limit", "5"]
    )

    assert result.exit_code == 0
    assert "Asyncio Guide" in result.output
    assert "python/guide.md" in result.output


def test_start_command_passes_sse_options_to_server(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(*, transport: str, host: str, port: int, log_messages: str):
        captured.update(
            transport=transport,
            host=host,
            port=port,
            log_messages=log_messages,
        )

    runner = CliRunner()
    monkeypatch.setattr(cli.config, "list_sources", lambda: {})
    monkeypatch.setattr("devdoc.server.run", fake_run)

    result = runner.invoke(
        cli.main,
        ["start", "--transport", "sse", "--host", "127.0.0.1", "--port", "9090"],
    )

    assert result.exit_code == 0
    assert captured == {
        "transport": "sse",
        "host": "127.0.0.1",
        "port": 9090,
        "log_messages": "none",
    }

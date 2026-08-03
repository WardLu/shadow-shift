import subprocess
import sys
from pathlib import Path

import pytest

from tools.obsidian_formatter import Config, WiznoteToObsidianMigrator


def test_run_all_reports_missing_source_directory(tmp_path, capsys):
    missing_source = tmp_path / "wiznote_export"
    target_dir = tmp_path / "wiznote_obsidian"

    config = Config()
    config.source_dir = str(missing_source)
    config.target_dir = str(target_dir)
    config.vault_dir = str(target_dir)
    config.attachments_dir = str(target_dir / "attachments")

    with pytest.raises(FileNotFoundError, match="源目录不存在"):
        WiznoteToObsidianMigrator(config).run_all()

    captured = capsys.readouterr()
    assert "源目录不存在" in captured.out
    assert str(missing_source) in captured.out
    assert not target_dir.exists()


def test_cli_accepts_explicit_source_and_target(tmp_path):
    source_dir = tmp_path / "wiznote_download"
    target_dir = tmp_path / "wiznote_obsidian"
    source_dir.mkdir()
    (source_dir / "note.md").write_text("# Test note\n", encoding="utf-8")

    script_path = Path(__file__).parents[1] / "tools" / "obsidian_formatter.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--source",
            str(source_dir),
            "--target",
            str(target_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (target_dir / "note.md").is_file()
    assert "复制完成" in result.stdout


def test_cli_reports_missing_source_without_traceback(tmp_path):
    missing_source = tmp_path / "missing_export"
    target_dir = tmp_path / "wiznote_obsidian"
    script_path = Path(__file__).parents[1] / "tools" / "obsidian_formatter.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--source",
            str(missing_source),
            "--target",
            str(target_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "源目录不存在或不是目录" in output
    assert "Traceback" not in output
    assert not target_dir.exists()

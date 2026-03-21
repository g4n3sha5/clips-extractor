from pathlib import Path

import config
from config import Settings, load_settings, save_settings


def test_load_settings_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    settings = load_settings()

    assert settings.cache_dir == Path.home() / ".drillclips" / "cache"
    assert settings.output_dir == Path("clips").resolve()
    assert settings.clip_crf == 26
    assert settings.clip_preset == "medium"
    assert settings.clip_audio_kbps == 96
    assert isinstance(settings.cache_dir, Path)
    assert isinstance(settings.output_dir, Path)


def test_load_settings_reads_existing_file(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": "/tmp/clips"}')
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)

    settings = load_settings()
    assert settings.output_dir == Path("/tmp/clips")
    assert isinstance(settings.output_dir, Path)


def test_save_settings_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    settings = Settings(output_dir=tmp_path / "clips_out")

    save_settings(settings)
    reloaded = load_settings()

    assert reloaded.cache_dir == settings.cache_dir
    assert reloaded.output_dir == settings.output_dir
    assert reloaded.clip_crf == settings.clip_crf
    assert reloaded.clip_preset == settings.clip_preset
    assert reloaded.clip_audio_kbps == settings.clip_audio_kbps

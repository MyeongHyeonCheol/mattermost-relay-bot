import textwrap
from bot.config import load_config


def test_load_config_reads_all_fields(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("""
        server_url: https://meeting.ssafy.com
        team: s15p30b2
        dry_run: true
        source_channels: ["모의 소스"]
        destination_channel: "모의 대상"
        allowed_senders: ["audguscjf", "명현철"]
        poll_overlap_seconds: 5
    """), encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.server_url == "https://meeting.ssafy.com"
    assert cfg.team == "s15p30b2"
    assert cfg.dry_run is True
    assert cfg.source_channels == ["모의 소스"]
    assert cfg.destination_channel == "모의 대상"
    assert cfg.allowed_senders == ["audguscjf", "명현철"]
    assert cfg.poll_overlap_seconds == 5


def test_poll_overlap_defaults_to_5(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        'server_url: x\nteam: t\ndry_run: false\n'
        'source_channels: ["a"]\ndestination_channel: "b"\n'
        'allowed_senders: ["u"]\n', encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.poll_overlap_seconds == 5


def test_destination_channel_id_is_optional(tmp_path, monkeypatch):
    monkeypatch.delenv("MM_DEST_CHANNEL_ID", raising=False)
    p = tmp_path / "config.yaml"
    p.write_text(
        'server_url: x\nteam: t\ndry_run: false\n'
        'source_channels: ["a"]\ndestination_channel: "b"\n'
        'allowed_senders: ["u"]\n', encoding="utf-8")
    assert load_config(str(p)).destination_channel_id is None


def test_destination_channel_id_is_read(tmp_path, monkeypatch):
    monkeypatch.delenv("MM_DEST_CHANNEL_ID", raising=False)
    p = tmp_path / "config.yaml"
    p.write_text(
        'server_url: x\nteam: t\ndry_run: false\n'
        'source_channels: ["a"]\ndestination_channel: "b"\n'
        'destination_channel_id: "cid123"\n'
        'allowed_senders: ["u"]\n', encoding="utf-8")
    assert load_config(str(p)).destination_channel_id == "cid123"


def test_destination_channel_id_from_env_overrides_file(tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    p.write_text(
        'server_url: x\nteam: t\ndry_run: false\n'
        'source_channels: ["a"]\ndestination_channel: "b"\n'
        'destination_channel_id: "from_file"\n'
        'allowed_senders: ["u"]\n', encoding="utf-8")
    monkeypatch.setenv("MM_DEST_CHANNEL_ID", "from_env")
    assert load_config(str(p)).destination_channel_id == "from_env"

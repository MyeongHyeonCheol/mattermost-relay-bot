from bot.state import load_state, get_last_create_at, set_last_create_at, save_state


def test_missing_file_returns_empty_state(tmp_path):
    state = load_state(str(tmp_path / "nope.json"))
    assert state == {"channels": {}}


def test_get_returns_none_for_unknown_channel():
    assert get_last_create_at({"channels": {}}, "c1") is None


def test_set_then_get_roundtrip():
    state = {"channels": {}}
    set_last_create_at(state, "c1", 1760000000000)
    assert get_last_create_at(state, "c1") == 1760000000000


def test_load_state_tolerates_utf8_bom(tmp_path):
    p = tmp_path / "state.json"
    p.write_bytes('﻿{"channels": {"c1": {"last_create_at": 5}}}'.encode("utf-8"))
    state = load_state(str(p))
    assert get_last_create_at(state, "c1") == 5


def test_save_and_reload(tmp_path):
    p = str(tmp_path / "state.json")
    state = {"channels": {}}
    set_last_create_at(state, "c1", 123)
    save_state(p, state)
    reloaded = load_state(p)
    assert get_last_create_at(reloaded, "c1") == 123

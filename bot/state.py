import json
import os


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"channels": {}}
    # utf-8-sig: 손으로 편집하다 생긴 BOM이 있어도 안전하게 읽는다.
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if "channels" not in data:
        data["channels"] = {}
    return data


def get_last_create_at(state: dict, channel_id: str):
    ch = state.get("channels", {}).get(channel_id)
    return ch.get("last_create_at") if ch else None


def set_last_create_at(state: dict, channel_id: str, value: int) -> None:
    state.setdefault("channels", {}).setdefault(channel_id, {})["last_create_at"] = value


def save_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)

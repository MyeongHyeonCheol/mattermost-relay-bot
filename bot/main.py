import os
import time

from .env import load_env
from .config import load_config
from .state import load_state, save_state, get_last_create_at, set_last_create_at
from .relay import select_posts_to_relay, compute_new_last, format_message
from .mattermost_client import MattermostClient

STATE_PATH = "state.json"
CONFIG_PATH = "config.yaml"


def run_once(cfg, client, state, now_ms) -> bool:
    team_id = client.get_team_id(cfg.team)
    src_ids = client.resolve_channel_ids_by_display_name(team_id, cfg.source_channels)
    if cfg.destination_channel_id:
        dest_id = cfg.destination_channel_id
    else:
        dest_ids = client.resolve_channel_ids_by_display_name(team_id, [cfg.destination_channel])
        dest_id = dest_ids[cfg.destination_channel]
    user_display = client.resolve_user_ids(cfg.allowed_senders)  # {user_id: display}
    allowed_ids = set(user_display.keys())

    changed = False
    overlap = cfg.poll_overlap_seconds * 1000

    for display_name, cid in src_ids.items():
        prev = get_last_create_at(state, cid)
        if prev is None:
            baseline = client.get_channel_newest_create_at(cid)
            baseline = baseline if baseline is not None else now_ms
            set_last_create_at(state, cid, baseline)
            changed = True
            print(f"[baseline] {display_name}: {baseline} (첫 실행, 전달 없음)")
            continue

        posts = client.get_posts_since(cid, prev - overlap)
        to_relay = select_posts_to_relay(posts, allowed_ids, prev)
        for p in to_relay:
            author = user_display.get(p["user_id"], p["user_id"])
            message = format_message(p, author, display_name)
            if cfg.dry_run:
                print(f"[DRY-RUN] → {cfg.destination_channel}\n{message}\n파일:{p.get('file_ids')}")
                continue
            file_ids = []
            for fid in p.get("file_ids", []):
                try:
                    data, fname = client.download_file(fid)
                    file_ids.append(client.upload_file(dest_id, fname, data))
                except Exception as e:
                    message += f"\n⚠️ 첨부 전달 실패({fid}): {e}"
            client.create_post(dest_id, message, file_ids)

        new_last = compute_new_last(posts, prev)
        if new_last != prev:
            set_last_create_at(state, cid, new_last)
            changed = True

    return changed


def main() -> None:
    load_env()  # .env가 있으면 자격증명을 환경변수로 로드(없으면 무시)
    cfg = load_config(CONFIG_PATH)
    client = MattermostClient(cfg.server_url)
    client.login(os.environ["MM_LOGIN_ID"], os.environ["MM_PASSWORD"])
    state = load_state(STATE_PATH)
    changed = run_once(cfg, client, state, now_ms=int(time.time() * 1000))
    # 드라이런에서도 기준선/진행 지점은 저장해야 다음 실행이 올바르게 이어진다.
    # (게시는 run_once 내부에서 dry_run일 때 건너뛴다.)
    if changed:
        save_state(STATE_PATH, state)
        print("state.json 갱신됨" + (" (dry-run)" if cfg.dry_run else ""))


if __name__ == "__main__":
    main()

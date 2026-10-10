"""채널 멤버의 username/nickname을 출력해 config.yaml 작성을 돕는다.
사용: MM_LOGIN_ID=.. MM_PASSWORD=.. python -m bot.list_members "채널표시이름" ["다른 채널" ...]
"""
import os
import sys

from .env import load_env
from .config import load_config
from .mattermost_client import MattermostClient


def main():
    load_env()  # .env가 있으면 자격증명을 환경변수로 로드(없으면 무시)
    cfg = load_config("config.yaml")
    client = MattermostClient(cfg.server_url)
    client.login(os.environ["MM_LOGIN_ID"], os.environ["MM_PASSWORD"])
    team_id = client.get_team_id(cfg.team)
    names = sys.argv[1:] or cfg.source_channels
    ids = client.resolve_channel_ids_by_display_name(team_id, names)
    for display_name, cid in ids.items():
        print(f"\n== {display_name} ({cid}) ==")
        r = client.session.get(client.base + f"/channels/{cid}/members")
        r.raise_for_status()
        for m in r.json():
            u = client.session.get(client.base + f"/users/{m['user_id']}")
            u.raise_for_status()
            d = u.json()
            print(f"  username={d.get('username'):20} nickname={d.get('nickname', '')}")


if __name__ == "__main__":
    main()

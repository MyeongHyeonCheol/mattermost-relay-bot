import os
from dataclasses import dataclass
import yaml


@dataclass
class Config:
    server_url: str
    team: str
    dry_run: bool
    source_channels: list
    destination_channel: str
    allowed_senders: list
    poll_overlap_seconds: int = 5
    destination_channel_id: str | None = None  # 지정 시 이름 조회 생략(그룹 DM 등)


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(
        server_url=data["server_url"].rstrip("/"),
        team=data["team"],
        dry_run=bool(data["dry_run"]),
        source_channels=list(data["source_channels"]),
        destination_channel=data["destination_channel"],
        allowed_senders=list(data["allowed_senders"]),
        poll_overlap_seconds=int(data.get("poll_overlap_seconds", 5)),
        # 환경변수(MM_DEST_CHANNEL_ID, GitHub Secrets/.env)가 파일 값보다 우선
        destination_channel_id=(os.environ.get("MM_DEST_CHANNEL_ID")
                                or data.get("destination_channel_id") or None),
    )

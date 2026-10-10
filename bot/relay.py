from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
_DIVIDER = "─" * 30


def select_posts_to_relay(posts, allowed_user_ids, last_create_at):
    picked = [
        p for p in posts
        if p.get("type", "") == ""
        and p.get("user_id") in allowed_user_ids
        and p.get("create_at", 0) > last_create_at
    ]
    picked.sort(key=lambda p: p["create_at"])
    return picked


def compute_new_last(all_posts, previous_last):
    if not all_posts:
        return previous_last
    return max(previous_last, max(p.get("create_at", 0) for p in all_posts))


def format_message(post, author_display, source_channel_display):
    dt = datetime.fromtimestamp(post["create_at"] / 1000, tz=timezone.utc).astimezone(KST)
    when = dt.strftime("%m/%d %H:%M")
    header = (
        f"📢 [팀장 공지 전달 · {source_channel_display}]\n"
        f"{author_display} · {when}\n{_DIVIDER}"
    )
    return f"{header}\n{post.get('message', '')}"

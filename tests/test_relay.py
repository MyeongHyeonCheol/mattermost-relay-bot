from bot.relay import select_posts_to_relay, compute_new_last, format_message


def _post(pid, uid, create_at, message="hi", ptype="", file_ids=None):
    return {"id": pid, "user_id": uid, "create_at": create_at,
            "message": message, "type": ptype, "file_ids": file_ids or []}


ALLOWED = {"u_boss", "u_me"}


def test_filters_by_sender():
    posts = [_post("1", "u_boss", 100), _post("2", "u_stranger", 101)]
    out = select_posts_to_relay(posts, ALLOWED, last_create_at=0)
    assert [p["id"] for p in out] == ["1"]


def test_excludes_boundary_and_older_posts():
    posts = [_post("old", "u_boss", 50), _post("same", "u_boss", 100),
             _post("new", "u_boss", 150)]
    out = select_posts_to_relay(posts, ALLOWED, last_create_at=100)
    assert [p["id"] for p in out] == ["new"]


def test_sorts_ascending_by_create_at():
    posts = [_post("c", "u_boss", 300), _post("a", "u_boss", 100),
             _post("b", "u_boss", 200)]
    out = select_posts_to_relay(posts, ALLOWED, last_create_at=0)
    assert [p["id"] for p in out] == ["a", "b", "c"]


def test_excludes_system_messages():
    posts = [_post("sys", "u_boss", 100, ptype="system_join_channel"),
             _post("real", "u_boss", 101)]
    out = select_posts_to_relay(posts, ALLOWED, last_create_at=0)
    assert [p["id"] for p in out] == ["real"]


def test_compute_new_last_advances_past_all_seen_posts():
    # 허용 발신자 글이 없어도(필터와 무관하게) 본 글 최대치로 전진
    posts = [_post("x", "u_stranger", 500), _post("y", "u_stranger", 400)]
    assert compute_new_last(posts, previous_last=100) == 500


def test_compute_new_last_keeps_previous_when_no_posts():
    assert compute_new_last([], previous_last=100) == 100


def test_format_message_has_header_and_body():
    # 1791520140000 == 2026-10-09 13:29:00 KST
    post = {"id": "1", "user_id": "u_boss", "create_at": 1791520140000,
            "message": "오늘 공지입니다", "type": "", "file_ids": []}
    text = format_message(post, author_display="장나현(교육프로)",
                          source_channel_display="<팀장채널>")
    assert "📢 [팀장 공지 전달 · <팀장채널>]" in text
    assert "장나현(교육프로) · 10/09 13:29" in text
    assert "🧑" not in text              # 사람 이모티콘 제거
    assert "─" * 20 in text              # 더 긴 구분선
    assert "오늘 공지입니다" in text

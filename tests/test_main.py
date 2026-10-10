from bot.config import Config
from bot.main import run_once
from bot.state import get_last_create_at


class FakeClient:
    def __init__(self, newest, posts_by_channel):
        self._newest = newest
        self._posts = posts_by_channel
        self.created = []
        self.uploaded = []

    def get_team_id(self, team):
        return "team1"

    def resolve_channel_ids_by_display_name(self, team_id, names):
        return {n: f"cid_{n}" for n in names}

    def resolve_user_ids(self, usernames):
        return {"u_me": "나"}  # audguscjf → u_me

    def get_channel_newest_create_at(self, cid):
        return self._newest.get(cid)

    def get_posts_since(self, cid, since):
        return self._posts.get(cid, [])

    def download_file(self, fid):
        return (b"x", "f.png")

    def upload_file(self, cid, name, data):
        self.uploaded.append((cid, name))
        return "upl_" + name

    def create_post(self, cid, message, file_ids=None):
        self.created.append((cid, message, file_ids or []))


def _cfg(dry=False):
    return Config(server_url="x", team="t", dry_run=dry,
                  source_channels=["모의 소스"], destination_channel="모의 대상",
                  allowed_senders=["audguscjf"], poll_overlap_seconds=5)


def _post(pid, uid, create_at, msg="hi", file_ids=None):
    return {"id": pid, "user_id": uid, "create_at": create_at,
            "message": msg, "type": "", "file_ids": file_ids or []}


def test_first_run_sets_baseline_and_relays_nothing():
    client = FakeClient(newest={"cid_모의 소스": 1000},
                        posts_by_channel={})
    state = {"channels": {}}
    changed = run_once(_cfg(), client, state, now_ms=2000)
    assert client.created == []                       # 과거 전달 안 함
    assert get_last_create_at(state, "cid_모의 소스") == 1000  # 기준선 설정
    assert changed is True


def test_relays_new_allowed_post_to_destination():
    client = FakeClient(
        newest={"cid_모의 소스": 1000},
        posts_by_channel={"cid_모의 소스": [_post("p1", "u_me", 1500)]})
    state = {"channels": {"cid_모의 소스": {"last_create_at": 1000}}}
    changed = run_once(_cfg(), client, state, now_ms=2000)
    assert len(client.created) == 1
    cid, message, fids = client.created[0]
    assert cid == "cid_모의 대상"
    assert "hi" in message
    assert get_last_create_at(state, "cid_모의 소스") == 1500


def test_dry_run_does_not_post():
    client = FakeClient(
        newest={"cid_모의 소스": 1000},
        posts_by_channel={"cid_모의 소스": [_post("p1", "u_me", 1500)]})
    state = {"channels": {"cid_모의 소스": {"last_create_at": 1000}}}
    run_once(_cfg(dry=True), client, state, now_ms=2000)
    assert client.created == []


def test_reupload_attachments():
    client = FakeClient(
        newest={"cid_모의 소스": 1000},
        posts_by_channel={"cid_모의 소스": [_post("p1", "u_me", 1500, file_ids=["f1"])]})
    state = {"channels": {"cid_모의 소스": {"last_create_at": 1000}}}
    run_once(_cfg(), client, state, now_ms=2000)
    assert client.uploaded == [("cid_모의 대상", "f.png")]
    _, _, fids = client.created[0]
    assert fids == ["upl_f.png"]


def test_destination_channel_id_skips_name_lookup():
    client = FakeClient(
        newest={"cid_모의 소스": 1000},
        posts_by_channel={"cid_모의 소스": [_post("p1", "u_me", 1500)]})
    looked_up = []
    orig = client.resolve_channel_ids_by_display_name

    def spy(team_id, names):
        looked_up.extend(names)
        return orig(team_id, names)
    client.resolve_channel_ids_by_display_name = spy
    cfg = _cfg()
    cfg.destination_channel_id = "gm_direct"
    state = {"channels": {"cid_모의 소스": {"last_create_at": 1000}}}
    run_once(cfg, client, state, now_ms=2000)
    assert client.created[0][0] == "gm_direct"
    assert "모의 대상" not in looked_up

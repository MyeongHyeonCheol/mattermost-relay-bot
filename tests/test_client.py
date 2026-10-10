import pytest

from bot.mattermost_client import MattermostClient


class FakeResp:
    def __init__(self, status=200, headers=None, body=None, content=b""):
        self.status_code = status
        self.headers = headers or {}
        self._body = body
        self.content = content

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.calls = []
        self.headers = {}
        self.queue = []

    def _next(self):
        return self.queue.pop(0)

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        return self._next()

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw))
        return self._next()


def test_login_stores_token_header():
    s = FakeSession()
    s.queue.append(FakeResp(headers={"Token": "abc123"}, body={"id": "u1"}))
    c = MattermostClient("https://mm.example.com", session=s)
    c.login("me", "pw")
    method, url, kw = s.calls[0]
    assert url == "https://mm.example.com/api/v4/users/login"
    assert kw["json"] == {"login_id": "me", "password": "pw"}
    assert s.headers["Authorization"] == "Bearer abc123"


def test_get_posts_since_paginates():
    s = FakeSession()
    # 1페이지: prev_post_id 있음 → 2페이지 더 조회
    s.queue.append(FakeResp(body={
        "order": ["p2", "p1"],
        "posts": {"p1": {"id": "p1", "create_at": 100},
                  "p2": {"id": "p2", "create_at": 200}},
        "prev_post_id": "p1"}))
    s.queue.append(FakeResp(body={
        "order": ["p0"],
        "posts": {"p0": {"id": "p0", "create_at": 50}},
        "prev_post_id": ""}))
    c = MattermostClient("https://mm.example.com", session=s)
    posts = c.get_posts_since("chan", 10)
    ids = sorted(p["id"] for p in posts)
    assert ids == ["p0", "p1", "p2"]


def test_create_post_sends_payload():
    s = FakeSession()
    s.queue.append(FakeResp(body={"id": "newpost"}))
    c = MattermostClient("https://mm.example.com", session=s)
    c._token = "t"  # 직접 세팅
    c.create_post("chan", "hello", ["f1", "f2"])
    method, url, kw = s.calls[-1]
    assert url == "https://mm.example.com/api/v4/posts"
    assert kw["json"] == {"channel_id": "chan", "message": "hello", "file_ids": ["f1", "f2"]}


# --- I1: 발신자 username 직접 조회, 실패 시 표시이름 검색으로 폴백 ---

def test_resolve_user_ids_uses_username_directly():
    s = FakeSession()
    s.queue.append(FakeResp(status=200, body={"id": "u1", "username": "audguscjf",
                                              "nickname": "", "first_name": "", "last_name": ""}))
    c = MattermostClient("https://mm.example.com", session=s)
    out = c.resolve_user_ids(["audguscjf"])
    assert out == {"u1": "audguscjf"}


def test_resolve_user_ids_falls_back_to_search_for_display_name():
    s = FakeSession()
    s.queue.append(FakeResp(status=404, body=None))  # username 조회 실패
    s.queue.append(FakeResp(status=200, body=[
        {"id": "u9", "username": "abc", "nickname": "장나현(교육프로)"}]))  # 검색 결과
    c = MattermostClient("https://mm.example.com", session=s)
    out = c.resolve_user_ids(["장나현(교육프로)"])
    assert out == {"u9": "장나현(교육프로)"}
    # 두 번째 호출이 검색 엔드포인트였는지 확인
    assert s.calls[1][0] == "POST"
    assert s.calls[1][1].endswith("/users/search")


def test_resolve_user_ids_raises_when_not_found():
    s = FakeSession()
    s.queue.append(FakeResp(status=404, body=None))
    s.queue.append(FakeResp(status=200, body=[]))  # 검색 결과 없음
    c = MattermostClient("https://mm.example.com", session=s)
    with pytest.raises(KeyError):
        c.resolve_user_ids(["없는사람"])


# --- I2: 채널 display_name 중복 시 조용히 틀린 채널 고르지 않고 예외 ---

def test_resolve_channel_raises_on_duplicate_display_name():
    s = FakeSession()
    s.queue.append(FakeResp(status=200, body=[
        {"display_name": "dup", "id": "c1", "name": "slug1"},
        {"display_name": "dup", "id": "c2", "name": "slug2"}]))
    c = MattermostClient("https://mm.example.com", session=s)
    with pytest.raises(ValueError):
        c.resolve_channel_ids_by_display_name("t", ["dup"])


# --- I3: 사용자 채널 목록 페이지네이션 ---

def test_get_user_channels_paginates():
    s = FakeSession()
    s.queue.append(FakeResp(status=200, body=[{"id": "a"}, {"id": "b"}]))  # 꽉 찬 페이지
    s.queue.append(FakeResp(status=200, body=[{"id": "c"}]))              # 짧은 페이지 → 종료
    c = MattermostClient("https://mm.example.com", session=s)
    chans = c.get_user_channels("t", per_page=2)
    assert [x["id"] for x in chans] == ["a", "b", "c"]


# --- I4: get_posts_since가 since 경계에 닿으면 전체 이력으로 역주행하지 않고 멈춤 ---

def test_get_posts_since_stops_when_reaching_since():
    s = FakeSession()
    s.queue.append(FakeResp(body={
        "order": ["p2", "p1"],
        "posts": {"p1": {"id": "p1", "create_at": 5},
                  "p2": {"id": "p2", "create_at": 200}},
        "prev_post_id": "p1"}))  # prev 있지만 oldest(5) <= since(10) → 추가 조회 안 함
    c = MattermostClient("https://mm.example.com", session=s)
    posts = c.get_posts_since("chan", 10)
    assert sorted(p["id"] for p in posts) == ["p1", "p2"]
    assert len(s.calls) == 1  # 단 한 번만 조회

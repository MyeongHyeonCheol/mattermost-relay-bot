# 팀장 채널 → B203 공지 전달 봇 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 팀장 전용 비공개 채널의 지정 발신자 글·첨부를 5분 주기 폴링으로 감지해 대상 채널에 원문 그대로 복사·전달하는 Python self-bot을 만든다.

**Architecture:** 본인 계정으로 로그인(세션 토큰)하여 각 소스 채널의 "마지막 처리 시각 이후" 글을 조회하고, 발신자 필터를 통과한 글을 머리말과 함께 대상 채널에 재게시한다. 첨부는 다운로드 후 재업로드한다. 상태(state.json)로 중복을 방지하며, GitHub Actions cron이 5분마다 실행하고 변경 시 state를 커밋한다. API 호출(client)과 판단 로직(relay)을 분리해 서버 없이 로직을 단위 테스트한다.

**Tech Stack:** Python 3.12 (conda/miniforge3), `requests`, `PyYAML`, `pytest`. Mattermost REST API v4. GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-09-mattermost-relay-bot-design.md`

## Global Constraints

- Python 런타임은 `C:\Users\SSAFY\miniforge3\python.exe` (버전 3.12.12). PATH에 `python` 없음 — 전체 경로 또는 conda 환경 사용.
- SSAFY 자격증명(`MM_SERVER_URL`, `MM_LOGIN_ID`, `MM_PASSWORD`)은 코드·설정파일에 저장 금지. 환경변수(로컬)·GitHub Secrets(운영)로만 주입.
- 전달은 **단방향·신규 글만**. 수정/삭제/과거 이력 소급 금지.
- 전달 메시지 형식(사양서 §9) 고정:
  ```
  📢 [팀장 공지 전달 · <출처 채널명>]
  🧑 <작성자> · MM/DD HH:mm
  ──────────────
  <원문>
  ```
- 시각 표기는 KST(Asia/Seoul).
- 서버 베이스 경로: `<server_url>/api/v4`.
- 커밋은 작게 자주. 각 Task 끝에서 커밋.

## Review Focus

- **첫 실행 폭주 방지:** 특정 소스 채널에 상태가 없을 때(최초) 과거 글 전체를 전달하면 안 됨 — 기준선만 '현재'로 잡고 아무것도 전달하지 않아야 함. (Task 5가 테스트)
- **경계 중복 전달:** `since` 재조회 시 직전에 이미 전달한 글이 다시 와도 `create_at > last` 엄격 비교로 재전송하지 않아야 함. (Task 3이 테스트)
- **정렬 역전:** Mattermost는 최신순으로 글을 반환 — 전달·상태갱신 전에 `create_at` 오름차순 정렬이 보장돼야 순서가 뒤섞이지 않음. (Task 3이 테스트)
- **시스템 글 혼입:** 입장/퇴장/채널변경 같은 시스템 글(`type`이 빈 문자열이 아님)은 전달 대상에서 제외해야 함. (Task 3이 테스트)
- **상태 전진 실패로 인한 누적:** 허용 발신자가 한동안 글을 안 써도, 그 창에서 본 모든 글의 최대 `create_at`으로 상태를 전진시켜 조회 범위가 무한히 커지지 않아야 함. (Task 3이 테스트)

---

## File Structure

- `bot/__init__.py` — 패키지 표시 (빈 파일)
- `bot/config.py` — `config.yaml` 로딩 → `Config` 데이터클래스
- `bot/state.py` — `state.json` 읽기/쓰기, 채널별 last_create_at 접근
- `bot/relay.py` — 순수 로직: 전달 대상 선별, 상태 전진값 계산, 메시지 포맷
- `bot/mattermost_client.py` — REST API v4 래퍼 (로그인/해석/조회/다운로드/업로드/게시)
- `bot/main.py` — 조립: config→login→해석→채널별 폴링→전달→state 저장
- `bot/list_members.py` — 설정 보조: 채널 멤버(username/nickname) 출력 (일회성 도우미)
- `config.example.yaml` — 설정 예시 (커밋됨)
- `config.yaml` — 실제 설정 (커밋됨, 민감정보 없음)
- `state.json` — 런타임 상태 (커밋됨, 자동 갱신)
- `requirements.txt` — `requests`, `PyYAML`, `pytest`
- `.github/workflows/relay.yml` — 5분 cron + state 커밋
- `tests/test_config.py`, `tests/test_state.py`, `tests/test_relay.py`, `tests/test_client.py`
- `README.md` — 설치·설정·테스트·운영 전환 가이드

---

## Task 1: 프로젝트 스캐폴드 + 설정 로더

**Files:**
- Create: `bot/__init__.py`, `bot/config.py`, `requirements.txt`, `config.example.yaml`
- Test: `tests/test_config.py`, `tests/__init__.py`

**Interfaces:**
- Produces:
  - `@dataclass Config` with fields: `server_url: str`, `team: str`, `dry_run: bool`, `source_channels: list[str]`, `destination_channel: str`, `allowed_senders: list[str]`, `poll_overlap_seconds: int`
  - `load_config(path: str) -> Config`

- [ ] **Step 1: requirements.txt 작성**

```
requests>=2.31
PyYAML>=6.0
pytest>=8.0
```

- [ ] **Step 2: 의존성 설치**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pip install -r requirements.txt`
Expected: requests/PyYAML/pytest 설치 완료

- [ ] **Step 3: 실패하는 테스트 작성** (`tests/__init__.py`는 빈 파일로 생성)

```python
# tests/test_config.py
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
```

- [ ] **Step 4: 실패 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: bot.config`)

- [ ] **Step 5: 구현**

```python
# bot/__init__.py  (빈 파일)
```
```python
# bot/config.py
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
    )
```

- [ ] **Step 6: 통과 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: config.example.yaml 작성**

```yaml
# 복사해서 config.yaml 로 사용하세요. 민감정보(ID/PW)는 넣지 않습니다.
server_url: https://meeting.ssafy.com
team: s15p30b2
dry_run: true                 # true면 전달하지 않고 로그만 출력
source_channels:
  - "모의 소스"               # 테스트용. 운영: "[자율 2반] 팀장", "<팀장채널>"
destination_channel: "모의 대상"  # 테스트용. 운영: "<팀채널> B203"
allowed_senders:
  - audguscjf                 # 본인(테스트/운영 공통)
  - 명현철                    # 테스트용
poll_overlap_seconds: 5
```

- [ ] **Step 8: 커밋**

```bash
git add bot/__init__.py bot/config.py tests/__init__.py tests/test_config.py requirements.txt config.example.yaml
git commit -m "feat: 설정 로더(config.py)와 프로젝트 스캐폴드 추가"
```

---

## Task 2: 상태 저장소 (state.py)

**Files:**
- Create: `bot/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Produces:
  - `load_state(path: str) -> dict` — 없으면 `{"channels": {}}`
  - `get_last_create_at(state: dict, channel_id: str) -> int | None`
  - `set_last_create_at(state: dict, channel_id: str, value: int) -> None`
  - `save_state(path: str, state: dict) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_state.py
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

def test_save_and_reload(tmp_path):
    p = str(tmp_path / "state.json")
    state = {"channels": {}}
    set_last_create_at(state, "c1", 123)
    save_state(p, state)
    reloaded = load_state(p)
    assert get_last_create_at(reloaded, "c1") == 123
```

- [ ] **Step 2: 실패 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_state.py -v`
Expected: FAIL (`ModuleNotFoundError: bot.state`)

- [ ] **Step 3: 구현**

```python
# bot/state.py
import json
import os

def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"channels": {}}
    with open(path, "r", encoding="utf-8") as f:
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
```

- [ ] **Step 4: 통과 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_state.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add bot/state.py tests/test_state.py
git commit -m "feat: 상태 저장소(state.py) 추가 — 채널별 last_create_at"
```

---

## Task 3: 전달 핵심 로직 (relay.py) — 순수 함수

**Files:**
- Create: `bot/relay.py`
- Test: `tests/test_relay.py`

**Interfaces:**
- Consumes: post는 dict. 사용 필드: `id, user_id, create_at(int ms), message(str), type(str), file_ids(list)`
- Produces:
  - `select_posts_to_relay(posts: list[dict], allowed_user_ids: set[str], last_create_at: int) -> list[dict]`
    — type이 빈 문자열이고, user_id가 allowed에 포함되고, create_at > last_create_at인 글만, create_at 오름차순 정렬.
  - `compute_new_last(all_posts: list[dict], previous_last: int) -> int`
    — all_posts(그 창에서 조회된 모든 글)의 최대 create_at과 previous_last 중 큰 값.
  - `format_message(post: dict, author_display: str, source_channel_display: str) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_relay.py
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
    # 1791520140000 == 2026-10-09 13:29:00 KST (아래 Step 1b 명령으로 검산 가능)
    post = {"id": "1", "user_id": "u_boss", "create_at": 1791520140000,
            "message": "오늘 공지입니다", "type": "", "file_ids": []}
    text = format_message(post, author_display="장나현(교육프로)",
                          source_channel_display="<팀장채널>")
    assert "📢 [팀장 공지 전달 · <팀장채널>]" in text
    assert "🧑 장나현(교육프로) · 10/09 13:29" in text
    assert "오늘 공지입니다" in text
```

- [ ] **Step 1b (참고): 타임스탬프 검산**

위 `1791520140000`이 KST 2026-10-09 13:29와 맞는지 확인하려면:
```
C:\Users\SSAFY\miniforge3\python.exe -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(int(datetime(2026,10,9,13,29,tzinfo=ZoneInfo('Asia/Seoul')).timestamp()*1000))"
```
출력이 `1791520140000`이면 일치.

- [ ] **Step 2: 실패 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_relay.py -v`
Expected: FAIL (`ModuleNotFoundError: bot.relay`)

- [ ] **Step 3: 구현**

```python
# bot/relay.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
_DIVIDER = "──────────────"

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
    header = f"📢 [팀장 공지 전달 · {source_channel_display}]\n🧑 {author_display} · {when}\n{_DIVIDER}"
    return f"{header}\n{post.get('message', '')}"
```

- [ ] **Step 4: 통과 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_relay.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add bot/relay.py tests/test_relay.py
git commit -m "feat: 전달 핵심 로직(relay.py) — 필터/정렬/상태전진/포맷"
```

---

## Task 4: Mattermost API 클라이언트 (mattermost_client.py)

**Files:**
- Create: `bot/mattermost_client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Produces 클래스 `MattermostClient(server_url: str, session=None)`:
  - `login(login_id: str, password: str) -> None` — POST `/users/login`, 응답 헤더 `Token`을 보관하여 이후 `Authorization: Bearer` 사용
  - `get_team_id(team_name: str) -> str` — GET `/teams/name/{name}`
  - `resolve_channel_ids_by_display_name(team_id: str, display_names: list[str]) -> dict[str,str]` — GET `/users/me/teams/{team_id}/channels`에서 display_name 매칭 → `{display_name: channel_id}`
  - `resolve_user_ids(usernames: list[str]) -> dict[str,str]` — 각 username을 GET `/users/username/{u}` → `{user_id: display}` (display = nickname 있으면 nickname, 없으면 "first last" 또는 username)
  - `get_posts_since(channel_id: str, since_ms: int) -> list[dict]` — GET `/channels/{id}/posts?since=`, `prev_post_id` 페이지네이션으로 전부 수집
  - `get_channel_newest_create_at(channel_id: str) -> int | None` — GET `/channels/{id}/posts?per_page=1`의 최신 글 create_at (없으면 None)
  - `download_file(file_id: str) -> tuple[bytes, str]` — GET `/files/{id}` + GET `/files/{id}/info`로 파일명
  - `upload_file(channel_id: str, filename: str, data: bytes) -> str` — POST `/files` multipart → file_info id
  - `create_post(channel_id: str, message: str, file_ids: list[str] | None = None) -> None` — POST `/posts`

- [ ] **Step 1: 실패하는 테스트 작성** (가짜 세션 주입으로 요청 구성 검증)

```python
# tests/test_client.py
import json
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
```

- [ ] **Step 2: 실패 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_client.py -v`
Expected: FAIL (`ModuleNotFoundError: bot.mattermost_client`)

- [ ] **Step 3: 구현**

```python
# bot/mattermost_client.py
import requests

class MattermostClient:
    def __init__(self, server_url: str, session=None):
        self.base = server_url.rstrip("/") + "/api/v4"
        self.session = session or requests.Session()
        self._token = None

    def login(self, login_id: str, password: str) -> None:
        r = self.session.post(self.base + "/users/login",
                              json={"login_id": login_id, "password": password})
        r.raise_for_status()
        self._token = r.headers["Token"]
        self.session.headers["Authorization"] = "Bearer " + self._token

    def get_team_id(self, team_name: str) -> str:
        r = self.session.get(self.base + f"/teams/name/{team_name}")
        r.raise_for_status()
        return r.json()["id"]

    def resolve_channel_ids_by_display_name(self, team_id, display_names):
        r = self.session.get(self.base + f"/users/me/teams/{team_id}/channels")
        r.raise_for_status()
        by_display = {c["display_name"]: c["id"] for c in r.json()}
        out = {}
        for name in display_names:
            if name not in by_display:
                raise KeyError(f"채널을 찾지 못함(가입 여부 확인): {name!r}")
            out[name] = by_display[name]
        return out

    def resolve_user_ids(self, usernames):
        out = {}
        for u in usernames:
            r = self.session.get(self.base + f"/users/username/{u}")
            r.raise_for_status()
            user = r.json()
            display = user.get("nickname") or (
                (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
            ) or user.get("username", u)
            out[user["id"]] = display
        return out

    def get_posts_since(self, channel_id, since_ms):
        collected = {}
        url = self.base + f"/channels/{channel_id}/posts"
        params = {"since": since_ms}
        while True:
            r = self.session.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            collected.update(data.get("posts", {}))
            prev = data.get("prev_post_id") or ""
            if not prev:
                break
            # since 조회에서 더 과거 페이지로 이동
            params = {"before": prev, "per_page": 200}
        return list(collected.values())

    def get_channel_newest_create_at(self, channel_id):
        r = self.session.get(self.base + f"/channels/{channel_id}/posts",
                             params={"per_page": 1})
        r.raise_for_status()
        data = r.json()
        order = data.get("order", [])
        if not order:
            return None
        return data["posts"][order[0]]["create_at"]

    def download_file(self, file_id):
        info = self.session.get(self.base + f"/files/{file_id}/info")
        info.raise_for_status()
        filename = info.json().get("name", file_id)
        r = self.session.get(self.base + f"/files/{file_id}")
        r.raise_for_status()
        return r.content, filename

    def upload_file(self, channel_id, filename, data):
        r = self.session.post(self.base + "/files",
                              data={"channel_id": channel_id},
                              files={"files": (filename, data)})
        r.raise_for_status()
        return r.json()["file_infos"][0]["id"]

    def create_post(self, channel_id, message, file_ids=None):
        payload = {"channel_id": channel_id, "message": message}
        if file_ids:
            payload["file_ids"] = file_ids
        r = self.session.post(self.base + "/posts", json=payload)
        r.raise_for_status()
```

> 주: `get_posts_since` 페이지네이션은 테스트(FakeSession)에서 첫 응답의 `prev_post_id`가 있으면 다음 페이지를 조회하고 빈 문자열이면 멈추는 동작만 검증한다. 실제 서버 동작은 Task 7 수동 검증에서 확인한다.

- [ ] **Step 4: 통과 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add bot/mattermost_client.py tests/test_client.py
git commit -m "feat: Mattermost API 클라이언트(로그인/조회/다운로드/업로드/게시)"
```

---

## Task 5: 진입점 조립 (main.py) — 드라이런·첫 실행 기준선 포함

**Files:**
- Create: `bot/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `Config`, `MattermostClient`(또는 동일 인터페이스의 fake), state 함수들, relay 함수들
- Produces:
  - `run_once(cfg, client, state, now_ms) -> bool` — 1회 폴링 수행, 상태 변경 시 True. 실제 로그인/IO는 caller가 준비한 `client`에 위임.
  - `main() -> None` — 환경변수에서 자격증명 읽어 로그인 후 `run_once` 호출, 변경 시 `save_state`.

- [ ] **Step 1: 실패하는 테스트 작성** (fake client로 첫 실행 기준선·중복방지 검증)

```python
# tests/test_main.py
from bot.config import Config
from bot.main import run_once
from bot.state import load_state, get_last_create_at

class FakeClient:
    def __init__(self, newest, posts_by_channel):
        self._newest = newest
        self._posts = posts_by_channel
        self.created = []
        self.uploaded = []
    def get_team_id(self, team): return "team1"
    def resolve_channel_ids_by_display_name(self, team_id, names):
        return {n: f"cid_{n}" for n in names}
    def resolve_user_ids(self, usernames):
        return {"u_me": "나"}  # audguscjf → u_me
    def get_channel_newest_create_at(self, cid):
        return self._newest.get(cid)
    def get_posts_since(self, cid, since):
        return self._posts.get(cid, [])
    def download_file(self, fid): return (b"x", "f.png")
    def upload_file(self, cid, name, data):
        self.uploaded.append((cid, name)); return "upl_" + name
    def create_post(self, cid, message, file_ids=None):
        self.created.append((cid, message, file_ids or []))

def _cfg(dry=False):
    return Config(server_url="x", team="t", dry_run=dry,
                  source_channels=["모의 소스"], destination_channel="모의 대상",
                  allowed_senders=["audguscjf"], poll_overlap_seconds=5)

def _post(pid, uid, create_at, msg="hi", file_ids=None):
    return {"id": pid, "user_id": uid, "create_at": create_at,
            "message": msg, "type": "", "file_ids": file_ids or []}

def test_first_run_sets_baseline_and_relays_nothing(tmp_path):
    client = FakeClient(newest={"cid_모의 소스": 1000},
                        posts_by_channel={})
    state = {"channels": {}}
    changed = run_once(_cfg(), client, state, now_ms=2000)
    assert client.created == []                       # 과거 전달 안 함
    assert get_last_create_at(state, "cid_모의 소스") == 1000  # 기준선 설정
    assert changed is True

def test_relays_new_allowed_post_to_destination(tmp_path):
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

def test_dry_run_does_not_post(tmp_path):
    client = FakeClient(
        newest={"cid_모의 소스": 1000},
        posts_by_channel={"cid_모의 소스": [_post("p1", "u_me", 1500)]})
    state = {"channels": {"cid_모의 소스": {"last_create_at": 1000}}}
    run_once(_cfg(dry=True), client, state, now_ms=2000)
    assert client.created == []

def test_reupload_attachments(tmp_path):
    client = FakeClient(
        newest={"cid_모의 소스": 1000},
        posts_by_channel={"cid_모의 소스": [_post("p1", "u_me", 1500, file_ids=["f1"])]})
    state = {"channels": {"cid_모의 소스": {"last_create_at": 1000}}}
    run_once(_cfg(), client, state, now_ms=2000)
    assert client.uploaded == [("cid_모의 대상", "f.png")]
    _, _, fids = client.created[0]
    assert fids == ["upl_f.png"]
```

- [ ] **Step 2: 실패 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_main.py -v`
Expected: FAIL (`ModuleNotFoundError: bot.main`)

- [ ] **Step 3: 구현**

```python
# bot/main.py
import os
import time
from .config import load_config
from .state import load_state, save_state, get_last_create_at, set_last_create_at
from .relay import select_posts_to_relay, compute_new_last, format_message
from .mattermost_client import MattermostClient

STATE_PATH = "state.json"
CONFIG_PATH = "config.yaml"

def run_once(cfg, client, state, now_ms) -> bool:
    team_id = client.get_team_id(cfg.team)
    src_ids = client.resolve_channel_ids_by_display_name(team_id, cfg.source_channels)
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
    cfg = load_config(CONFIG_PATH)
    client = MattermostClient(cfg.server_url)
    client.login(os.environ["MM_LOGIN_ID"], os.environ["MM_PASSWORD"])
    state = load_state(STATE_PATH)
    changed = run_once(cfg, client, state, now_ms=int(time.time() * 1000))
    if changed and not cfg.dry_run:
        save_state(STATE_PATH, state)
        print("state.json 갱신됨")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest tests/test_main.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 전체 테스트 재확인**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m pytest -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add bot/main.py tests/test_main.py
git commit -m "feat: 진입점(main.py) — 첫 실행 기준선·드라이런·첨부 재업로드"
```

---

## Task 6: 설정 보조 도우미 (list_members.py)

**Files:**
- Create: `bot/list_members.py`

**Interfaces:**
- Produces: 실행 시 지정 채널들의 멤버 `username / nickname / id`를 표 형태로 출력 (allowed_senders·채널 설정 채우기용).

- [ ] **Step 1: 구현** (순수 I/O 스크립트라 단위 테스트 생략, 수동 실행으로 검증)

```python
# bot/list_members.py
"""채널 멤버의 username/nickname을 출력해 config.yaml 작성을 돕는다.
사용: MM_LOGIN_ID=.. MM_PASSWORD=.. python -m bot.list_members "채널표시이름" ["다른 채널" ...]
"""
import os
import sys
from .config import load_config
from .mattermost_client import MattermostClient

def main():
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
            print(f"  username={d.get('username'):20} nickname={d.get('nickname','')}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 커밋**

```bash
git add bot/list_members.py
git commit -m "feat: 채널 멤버 조회 도우미(list_members.py)"
```

---

## Task 7: 로컬 수동 검증 (드라이런 → 테스트 채널 실제 전달)

> 사전 준비(사용자): 비공개 채널 2개(모의 소스/모의 대상, 멤버 본인+명현철) 생성. `config.yaml`을 `config.example.yaml`에서 복사해 소스/대상/발신자 채움.

**Files:**
- Create: `config.yaml` (실제 설정; 민감정보 없음), 최초 `state.json`

- [ ] **Step 1: 자격증명 환경변수 설정 (PowerShell, 세션 한정)**

```powershell
$env:MM_LOGIN_ID = "audguscjf"
$env:MM_PASSWORD = "<비밀번호>"   # 화면/로그에 남지 않게 주의
```

- [ ] **Step 2: 멤버 username 확인 후 config.yaml 채우기**

Run: `C:\Users\SSAFY\miniforge3\python.exe -m bot.list_members "모의 소스"`
출력된 username으로 `allowed_senders` 확정 (명현철의 실제 username 포함).

- [ ] **Step 3: 드라이런 1회 — 전달 없이 로그만**

`config.yaml`의 `dry_run: true` 확인 후
Run: `C:\Users\SSAFY\miniforge3\python.exe -m bot.main`
Expected: 첫 실행이면 `[baseline]` 출력. 모의 소스에 본인이 글 하나 올린 뒤 다시 실행하면 `[DRY-RUN] → 모의 대상` 로그에 그 글이 보여야 함.

- [ ] **Step 4: 실제 전달 검증**

`config.yaml`의 `dry_run: false`로 변경. 모의 소스에 **텍스트 + 파일 첨부** 글을 올린 뒤
Run: `C:\Users\SSAFY\miniforge3\python.exe -m bot.main`
Expected: 모의 대상 채널에 머리말+본문+첨부파일이 그대로 재게시됨. 재실행 시 **중복 전달 없음**.

- [ ] **Step 5: config.yaml / state.json 커밋**

```bash
git add config.yaml state.json
git commit -m "chore: 테스트용 설정과 초기 상태 추가"
```

---

## Task 8: GitHub Actions 워크플로 + README

**Files:**
- Create: `.github/workflows/relay.yml`, `README.md`

- [ ] **Step 1: 워크플로 작성**

```yaml
# .github/workflows/relay.yml
name: mattermost-relay
on:
  schedule:
    - cron: "*/5 * * * *"   # 약 5분마다(지연 가능)
  workflow_dispatch: {}      # 수동 실행 버튼

permissions:
  contents: write            # state.json 커밋용

concurrency:
  group: relay
  cancel-in-progress: false

jobs:
  relay:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - name: Run relay
        env:
          MM_LOGIN_ID: ${{ secrets.MM_LOGIN_ID }}
          MM_PASSWORD: ${{ secrets.MM_PASSWORD }}
        run: python -m bot.main
      - name: Commit state if changed
        run: |
          if ! git diff --quiet -- state.json; then
            git config user.name "github-actions"
            git config user.email "actions@github.com"
            git add state.json
            git commit -m "chore: update relay state [skip ci]"
            git push
          fi
```

- [ ] **Step 2: README 작성** (설치·설정·테스트·운영 전환·Secrets 등록·주의사항 포함)

```markdown
# Mattermost 팀장 공지 전달 봇

팀장 전용 비공개 채널의 지정 발신자 글·첨부를 5분마다 폴링해 대상 채널에 복사 전달합니다.

## 설정
1. `config.example.yaml` → `config.yaml` 복사 후 채널/발신자 입력.
2. 로컬 테스트: 환경변수 `MM_LOGIN_ID`, `MM_PASSWORD` 설정 후
   `python -m bot.main` (처음엔 `dry_run: true`).
3. 멤버 username 확인: `python -m bot.list_members "채널표시이름"`.

## GitHub Actions (무료, PC 꺼도 동작)
- **공개** 저장소로 push (Actions 무제한 무료).
- 저장소 Settings → Secrets and variables → Actions 에
  `MM_LOGIN_ID`, `MM_PASSWORD` 등록. (코드엔 절대 넣지 않음)
- `.github/workflows/relay.yml`이 5분마다 실행.

## 테스트 → 운영 전환
`config.yaml`의 `source_channels`/`destination_channel`/`allowed_senders`만 교체:
- 소스: `"[자율 2반] 팀장"`, `"<팀장채널>"`
- 대상: `"<팀채널> B203"`
- 발신자: 4명 + 본인

## 주의
- GitHub 실행기는 해외 IP라 반복 로그인이 보안 감지될 수 있음.
- cron은 지연/건너뜀 가능(실시간 아님). 60일 무활동 시 예약 자동 중지.
```

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/relay.yml README.md
git commit -m "ci: 5분 폴링 워크플로와 README 추가"
```

---

## 완료 기준 (Definition of Done)

- `pytest` 전체 통과.
- 모의 소스→모의 대상으로 텍스트·첨부가 정확히 1회 전달(중복 없음) 확인.
- 드라이런에서 전달 대상이 로그로 정확히 보임.
- GitHub Actions에서 무인 실행 시 테스트 채널로 전달·state 커밋 확인.
- 이후 사용자가 설정만 운영값으로 바꿔 전환.

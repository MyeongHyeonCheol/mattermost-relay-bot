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

    def get_user_channels(self, team_id, per_page=200):
        """사용자가 속한 (공개+비공개) 채널 전체를 페이지네이션으로 수집."""
        collected = []
        page = 0
        while True:
            r = self.session.get(
                self.base + f"/users/me/teams/{team_id}/channels",
                params={"page": page, "per_page": per_page})
            r.raise_for_status()
            batch = r.json()
            collected.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return collected

    def resolve_channel_ids_by_display_name(self, team_id, display_names):
        channels = self.get_user_channels(team_id)
        by_display = {}
        for c in channels:
            by_display.setdefault(c["display_name"], []).append(c["id"])
        out = {}
        for name in display_names:
            ids = by_display.get(name)
            if not ids:
                raise KeyError(f"채널을 찾지 못함(가입 여부 확인): {name!r}")
            if len(ids) > 1:
                raise ValueError(
                    f"표시 이름이 중복된 채널이 여러 개입니다: {name!r} → {ids}. "
                    "고유한 이름으로 바꾸거나 대상을 명확히 하세요.")
            out[name] = ids[0]
        return out

    def _display_of(self, user):
        return user.get("nickname") or (
            (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
        ) or user.get("username", "")

    def _search_user(self, term):
        r = self.session.post(self.base + "/users/search", json={"term": term})
        r.raise_for_status()
        results = r.json()
        for user in results:
            full = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
            if term == user.get("nickname") or term == user.get("username") or term == full:
                return user
        if results:
            return results[0]
        raise KeyError(f"사용자를 찾지 못함: {term!r}")

    def resolve_user_ids(self, senders):
        """senders는 username 또는 표시이름(nickname/full name). username 조회 실패 시 검색으로 폴백."""
        out = {}
        for s in senders:
            r = self.session.get(self.base + f"/users/username/{s}")
            if r.status_code == 200:
                user = r.json()
            elif r.status_code == 404:
                user = self._search_user(s)
            else:
                r.raise_for_status()
                user = r.json()
            out[user["id"]] = self._display_of(user) or s
        return out

    def get_posts_since(self, channel_id, since_ms):
        collected = {}
        url = self.base + f"/channels/{channel_id}/posts"
        params = {"since": since_ms, "per_page": 200}
        while True:
            r = self.session.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            posts = data.get("posts", {})
            collected.update(posts)
            prev = data.get("prev_post_id") or ""
            if not prev:
                break
            # since 경계에 이미 닿았으면 과거로 더 역주행하지 않음
            oldest = min((p.get("create_at", 0) for p in posts.values()), default=None)
            if oldest is None or oldest <= since_ms:
                break
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

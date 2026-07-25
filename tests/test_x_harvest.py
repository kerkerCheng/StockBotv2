"""X API harvest：成本控制（since_id 增量）、誠實降級、狀態持久。"""
from __future__ import annotations

import json

import pytest

from crons import harvest_leads
from engine_b import leads
from fetchers import x_api


def _config(**overrides):
    section = {"handles": ["aleabitoreddit"], "exclude_replies": True,
               "exclude_retweets": True, "max_results": 25}
    section.update(overrides)
    return {"feeds": [], "edgar_watch": {}, "x_accounts": section}


class _FakeApi:
    """記錄呼叫參數的假 client，用來斷言成本控制真的生效。"""

    XApiError = x_api.XApiError
    DEFAULT_MAX_RESULTS = 25

    def __init__(self, posts, *, fail=None):
        self.posts = posts
        self.fail = fail
        self.calls = []

    def bearer_token(self):
        if self.fail == "token":
            raise x_api.XApiError("missing_x_bearer_token")
        return "fake-token"

    def get_user_id(self, handle, token=None):
        self.calls.append(("user_id", handle))
        if self.fail == "lookup":
            raise x_api.XApiError("user_not_found")
        return "12345"

    def get_user_posts(self, user_id, **kw):
        self.calls.append(("posts", user_id, kw))
        if self.fail == "posts":
            raise x_api.XApiError("http_429")
        return self.posts

    post_url = staticmethod(x_api.post_url)
    newest_id = staticmethod(x_api.newest_id)


def _install(monkeypatch, fake):
    import fetchers
    monkeypatch.setattr(fetchers, "x_api", fake, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "fetchers.x_api", fake)


# --- 純函式 ---------------------------------------------------------------

def test_post_url_and_newest_id() -> None:
    assert x_api.post_url("@foo", "99") == "https://x.com/foo/status/99"
    assert x_api.newest_id([{"id": "5"}, {"id": "100"}, {"id": "7"}]) == "100"
    assert x_api.newest_id([]) is None
    assert x_api.newest_id([{"id": "abc"}]) is None


def test_bearer_token_requires_env(monkeypatch) -> None:
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    with pytest.raises(x_api.XApiError, match="missing_x_bearer_token"):
        x_api.bearer_token()
    monkeypatch.setenv("X_BEARER_TOKEN", " tok ")
    assert x_api.bearer_token() == "tok"


# --- harvest 整合 ---------------------------------------------------------

def test_harvest_registers_posts_and_persists_since_id(monkeypatch) -> None:
    posts = [
        {"id": "200", "text": "InP 產能觀察 " * 20, "created_at": "2026-07-25T00:00:00Z"},
        {"id": "199", "text": "CPO note", "created_at": "2026-07-24T00:00:00Z"},
    ]
    fake = _FakeApi(posts)
    _install(monkeypatch, fake)
    store = leads.empty_store()

    harvest_leads.harvest_x(_config(), store)

    assert len(store["leads"]) == 2
    lead = next(iter(store["leads"].values()))
    assert lead["source"] == "x:aleabitoreddit"
    assert lead["url"].startswith("https://x.com/aleabitoreddit/status/")
    assert len(lead["title"]) <= 140  # 標題截斷
    # since_id 與 user_id 持久化＝下次只抓新貼文（成本控制）
    state = leads.get_source_state(store, "x:aleabitoreddit")
    assert state["since_id"] == "200" and state["user_id"] == "12345"
    assert store["harvest_log"][-1]["result"] == "ok"


def test_second_run_sends_since_id_and_skips_user_lookup(monkeypatch) -> None:
    fake = _FakeApi([{"id": "300", "text": "new", "created_at": "2026-07-25T01:00:00Z"}])
    _install(monkeypatch, fake)
    store = leads.empty_store()
    leads.set_source_state(store, "x:aleabitoreddit", user_id="12345", since_id="200")

    harvest_leads.harvest_x(_config(), store)

    kinds = [c[0] for c in fake.calls]
    assert "user_id" not in kinds  # user_id 有快取 → 不重複計費
    posts_call = next(c for c in fake.calls if c[0] == "posts")
    assert posts_call[2]["since_id"] == "200"  # 只抓新的
    assert posts_call[2]["exclude_replies"] is True
    assert posts_call[2]["exclude_retweets"] is True
    assert posts_call[2]["max_results"] == 25


def test_missing_token_logs_fetch_failed_not_crash(monkeypatch) -> None:
    _install(monkeypatch, _FakeApi([], fail="token"))
    store = leads.empty_store()
    harvest_leads.harvest_x(_config(), store)
    assert store["leads"] == {}
    assert store["harvest_log"][-1] == {
        **store["harvest_log"][-1], "source": "x:aleabitoreddit",
        "result": "fetch_failed", "new": 0,
    }


def test_api_error_logs_fetch_failed_and_keeps_since_id(monkeypatch) -> None:
    _install(monkeypatch, _FakeApi([], fail="posts"))
    store = leads.empty_store()
    leads.set_source_state(store, "x:aleabitoreddit", user_id="1", since_id="500")
    harvest_leads.harvest_x(_config(), store)
    assert store["harvest_log"][-1]["result"] == "fetch_failed"
    # 失敗不得推進 since_id（否則會永久漏掉那批貼文）
    assert leads.get_source_state(store, "x:aleabitoreddit")["since_id"] == "500"


def test_no_handles_is_noop(monkeypatch) -> None:
    _install(monkeypatch, _FakeApi([]))
    store = leads.empty_store()
    harvest_leads.harvest_x(_config(handles=[]), store)
    assert store["harvest_log"] == [] and store["leads"] == {}


def test_repeat_harvest_is_idempotent(monkeypatch) -> None:
    posts = [{"id": "200", "text": "same", "created_at": "2026-07-25T00:00:00Z"}]
    _install(monkeypatch, _FakeApi(posts))
    store = leads.empty_store()
    harvest_leads.harvest_x(_config(), store)
    harvest_leads.harvest_x(_config(), store)  # 同一則再回傳一次
    assert len(store["leads"]) == 1  # URL-hash 去重


# --- config ---------------------------------------------------------------

def test_config_rejects_bad_x_section(tmp_path) -> None:
    bad = tmp_path / "cfg.json"
    bad.write_text(json.dumps({"x_accounts": {"handles": "aleabitoreddit"}}),
                   encoding="utf-8")
    with pytest.raises(ValueError, match="handles"):
        harvest_leads.load_config(bad)


def test_repo_config_has_x_section() -> None:
    cfg = harvest_leads.load_config()
    assert "aleabitoreddit" in cfg["x_accounts"]["handles"]
    assert cfg["x_accounts"]["exclude_replies"] is True

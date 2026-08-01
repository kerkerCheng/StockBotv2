"""X API harvest：成本控制（since_id 增量）、誠實降級、狀態持久。"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from crons import harvest_leads
from engine_b import leads
from fetchers import x_api


def _config(**overrides):
    section = {"handles": ["aleabitoreddit"], "exclude_replies": True,
               "exclude_retweets": True, "max_results": 25,
               "max_posts_per_run": 200,
               "cache_media": False}
    section.update(overrides)
    return {"feeds": [], "edgar_watch": {}, "x_accounts": section}


class _FakeApi:
    """記錄呼叫參數的假 client，用來斷言成本控制真的生效。"""

    XApiError = x_api.XApiError
    DEFAULT_MAX_RESULTS = 25
    DEFAULT_MEDIA_MAX_BYTES = 20 * 1024 * 1024

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

    def get_user_posts_window(self, user_id, **kw):
        self.calls.append(("posts_window", user_id, kw))
        if self.fail == "posts":
            raise x_api.XApiError("http_429")
        posts = self.posts[: int(kw["max_posts"])]
        if kw.get("with_meta"):
            return {"posts": posts, "truncated": False, "next_token": None}
        return posts

    def get_user_posts_since(self, user_id, **kw):
        self.calls.append(("posts_since", user_id, kw))
        if self.fail == "posts":
            raise x_api.XApiError("http_429")
        posts = self.posts[: int(kw["max_posts"])]
        if kw.get("with_meta"):
            return {"posts": posts, "truncated": False, "next_token": None}
        return posts

    def get_posts_by_ids(self, post_ids, **kw):
        self.calls.append(("posts_by_ids", post_ids, kw))
        if self.fail == "posts":
            raise x_api.XApiError("http_429")
        return self.posts

    def download_media_image(self, url, destination_dir, stem, **kw):
        self.calls.append(("media", url, destination_dir, stem, kw))
        return {
            "path": str(destination_dir / f"{stem}.jpg"),
            "sha256": "a" * 64,
            "bytes": 123,
            "content_type": "image/jpeg",
        }

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


def test_harvest_loads_repo_local_env_for_unattended_process(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("X_BEARER_TOKEN=from-local-env\n", encoding="utf-8")

    try:
        harvest_leads.load_local_env(env_file)
        assert x_api.bearer_token() == "from-local-env"
    finally:
        os.environ.pop("X_BEARER_TOKEN", None)


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
    assert len(lead["title"]) > 140
    assert lead["title"] == " ".join(lead["raw_text"].split())
    # since_id 與 user_id 持久化＝下次只抓新貼文（成本控制）
    state = leads.get_source_state(store, "x:aleabitoreddit")
    assert state["since_id"] == "200" and state["user_id"] == "12345"
    assert store["harvest_log"][-1]["result"] == "ok"


def test_harvest_preserves_media_metadata_and_private_cache_ref(monkeypatch) -> None:
    posts = [{
        "id": "201",
        "text": "看截圖\n第二行",
        "created_at": "2026-07-25T00:00:00Z",
        "media": [{
            "media_key": "3_201",
            "type": "photo",
            "url": "https://pbs.twimg.com/media/example.jpg",
            "alt_text": "server memory pricing table",
        }],
    }]
    fake = _FakeApi(posts)
    _install(monkeypatch, fake)
    store = leads.empty_store()

    harvest_leads.harvest_x(_config(cache_media=True), store)

    lead = next(iter(store["leads"].values()))
    assert lead["raw_text"] == "看截圖\n第二行"
    assert lead["title"] == "看截圖 第二行"
    assert lead["media"][0]["alt_text"] == "server memory pricing table"
    assert lead["media"][0]["cache"] == {
        "local_path": (
            "library/private/lead_media/"
            f"{lead['lead_id']}/3_201.jpg"
        ),
        "sha256": "a" * 64,
        "bytes": 123,
        "content_type": "image/jpeg",
    }
    assert any(call[0] == "media" for call in fake.calls)


def test_x_client_hydrates_note_tweet_and_media(monkeypatch) -> None:
    def fake_get(path, params, token):
        assert path == "/users/123/tweets"
        assert "note_tweet" in params["tweet.fields"]
        assert params["expansions"] == "attachments.media_keys"
        assert "alt_text" in params["media.fields"]
        assert token == "token"
        return {
            "data": [{
                "id": "900",
                "text": "truncated…",
                "note_tweet": {"text": "完整長文\n第二行"},
                "attachments": {"media_keys": ["3_900"]},
            }],
            "includes": {"media": [{
                "media_key": "3_900",
                "type": "photo",
                "url": "https://pbs.twimg.com/media/full.jpg",
            }]},
        }

    monkeypatch.setattr(x_api, "_get", fake_get)
    posts = x_api.get_user_posts("123", token="token")
    assert posts[0]["text"] == "完整長文\n第二行"
    assert posts[0]["media"][0]["media_key"] == "3_900"


def test_x_client_can_refresh_exact_post_id(monkeypatch) -> None:
    def fake_get(path, params, token):
        assert path == "/tweets"
        assert params["ids"] == "900"
        return {"data": [{"id": "900", "text": "full"}]}

    monkeypatch.setattr(x_api, "_get", fake_get)
    assert x_api.get_posts_by_ids(["900"], token="token")[0]["text"] == "full"


def test_x_client_paginates_bounded_time_window(monkeypatch) -> None:
    calls = []

    def fake_get(path, params, token):
        calls.append(dict(params))
        if "pagination_token" not in params:
            return {
                "data": [{"id": "3", "text": "new"}],
                "meta": {"next_token": "next"},
            }
        return {"data": [{"id": "2", "text": "old"}], "meta": {}}

    monkeypatch.setattr(x_api, "_get", fake_get)
    posts = x_api.get_user_posts_window(
        "123",
        start_time="2026-06-29T00:00:00Z",
        end_time="2026-07-29T00:00:00Z",
        max_posts=200,
        token="token",
    )

    assert [post["id"] for post in posts] == ["3", "2"]
    assert calls[0]["start_time"] == "2026-06-29T00:00:00Z"
    assert calls[0]["end_time"] == "2026-07-29T00:00:00Z"
    assert calls[1]["pagination_token"] == "next"


def test_x_client_marks_window_truncated_at_cost_cap(monkeypatch) -> None:
    def fake_get(path, params, token):
        return {
            "data": [{"id": str(params["max_results"]), "text": "x"}],
            "meta": {"next_token": "more"},
        }

    monkeypatch.setattr(x_api, "_get", fake_get)
    result = x_api.get_user_posts_window(
        "123",
        start_time="2026-06-29T00:00:00Z",
        max_posts=5,
        token="token",
        with_meta=True,
    )
    assert result["truncated"] is True


def test_x_client_paginates_bounded_since_id(monkeypatch) -> None:
    calls = []

    def fake_get(path, params, token):
        calls.append(dict(params))
        if "pagination_token" not in params:
            return {
                "data": [{"id": "301", "text": "new"}],
                "meta": {"next_token": "next"},
            }
        return {"data": [{"id": "300", "text": "older"}], "meta": {}}

    monkeypatch.setattr(x_api, "_get", fake_get)
    result = x_api.get_user_posts_since(
        "123",
        since_id="200",
        max_posts=200,
        page_size=25,
        token="token",
        with_meta=True,
    )

    assert [post["id"] for post in result["posts"]] == ["301", "300"]
    assert result["truncated"] is False
    assert calls[0]["since_id"] == "200"
    assert calls[1]["since_id"] == "200"
    assert calls[1]["pagination_token"] == "next"


def test_second_run_sends_since_id_and_skips_user_lookup(monkeypatch) -> None:
    fake = _FakeApi([{"id": "300", "text": "new", "created_at": "2026-07-25T01:00:00Z"}])
    _install(monkeypatch, fake)
    store = leads.empty_store()
    leads.set_source_state(store, "x:aleabitoreddit", user_id="12345", since_id="200")

    harvest_leads.harvest_x(_config(), store)

    kinds = [c[0] for c in fake.calls]
    assert "user_id" not in kinds  # user_id 有快取 → 不重複計費
    posts_call = next(c for c in fake.calls if c[0] == "posts_since")
    assert posts_call[2]["since_id"] == "200"  # 只抓新的
    assert posts_call[2]["exclude_replies"] is True
    assert posts_call[2]["exclude_retweets"] is True
    assert posts_call[2]["page_size"] == 25
    assert posts_call[2]["max_posts"] == 200


def test_daily_pagination_checkpoint_delays_since_id_until_final_page(monkeypatch) -> None:
    class _PagedFake(_FakeApi):
        def __init__(self):
            super().__init__([])
            self.pages = [
                {
                    "posts": [{"id": "301", "text": "newest"}],
                    "truncated": True,
                    "next_token": "page-2",
                },
                {
                    "posts": [{"id": "250", "text": "older"}],
                    "truncated": False,
                    "next_token": None,
                },
            ]

        def get_user_posts_since(self, user_id, **kw):
            self.calls.append(("posts_since", user_id, kw))
            return self.pages.pop(0)

    fake = _PagedFake()
    _install(monkeypatch, fake)
    store = leads.empty_store()
    leads.set_source_state(store, "x:aleabitoreddit", user_id="12345", since_id="200")

    harvest_leads.harvest_x(_config(max_posts_per_run=5), store)
    pending = leads.get_source_state(store, "x:aleabitoreddit")
    assert pending["since_id"] == "200"
    assert pending["x_pagination_since_id"] == "200"
    assert pending["x_pagination_token"] == "page-2"
    assert pending["x_pagination_high_watermark"] == "301"

    harvest_leads.harvest_x(_config(max_posts_per_run=5), store)
    complete = leads.get_source_state(store, "x:aleabitoreddit")
    assert complete["since_id"] == "301"
    assert "x_pagination_token" not in complete
    assert fake.calls[1][2]["since_id"] == "200"
    assert fake.calls[1][2]["pagination_token"] == "page-2"
    assert len(store["leads"]) == 2


def test_missing_token_logs_fetch_failed_not_crash(monkeypatch) -> None:
    _install(monkeypatch, _FakeApi([], fail="token"))
    store = leads.empty_store()
    harvest_leads.harvest_x(_config(), store)
    assert store["leads"] == {}
    assert store["harvest_log"][-1] == {
        **store["harvest_log"][-1], "source": "x:aleabitoreddit",
        "result": "fetch_failed", "new": 0,
        "failure_class": "credentials_missing",
    }


def test_api_error_logs_fetch_failed_and_keeps_since_id(monkeypatch) -> None:
    _install(monkeypatch, _FakeApi([], fail="posts"))
    store = leads.empty_store()
    leads.set_source_state(store, "x:aleabitoreddit", user_id="1", since_id="500")
    harvest_leads.harvest_x(_config(), store)
    assert store["harvest_log"][-1]["result"] == "fetch_failed"
    assert store["harvest_log"][-1]["failure_class"] == "provider_api_error"
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


def test_refresh_exact_x_lead_enriches_content_without_changing_status(monkeypatch) -> None:
    fake = _FakeApi([{
        "id": "200",
        "text": "完整 roundup\n- claim A\n- claim B",
        "created_at": "2026-07-25T00:00:00Z",
        "media": [],
    }])
    _install(monkeypatch, fake)
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store,
        source="x:aleabitoreddit",
        url="https://x.com/aleabitoreddit/status/200",
        title="完整 roundup",
    )
    leads.triage(store, lead_id, go=True, tier=3, reason="roundup")

    refreshed = harvest_leads.refresh_x_lead(_config(), store, lead_id)

    assert refreshed["raw_text"].endswith("claim B")
    assert refreshed["title"].endswith("claim B")
    assert refreshed["media"] == []
    assert refreshed["status"] == "triaged_go"
    assert refreshed["triage"]["reason"] == "roundup"
    assert ("posts_by_ids", ["200"], {}) in fake.calls


def test_backfill_enriches_requeues_no_go_and_preserves_since_id(monkeypatch) -> None:
    fake = _FakeApi([{
        "id": "200",
        "text": "Figure robotics supplier map",
        "created_at": "2026-07-20T00:00:00Z",
        "media": [],
    }])
    _install(monkeypatch, fake)
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store,
        source="x:aleabitoreddit",
        url="https://x.com/aleabitoreddit/status/200",
        title="Figure robotics",
    )
    leads.triage(store, lead_id, go=False, tier=4, reason="未命中既有 theme")
    leads.set_source_state(
        store, "x:aleabitoreddit", user_id="12345", since_id="999"
    )

    receipt = harvest_leads.backfill_x_handle(
        _config(),
        store,
        "aleabitoreddit",
        days=30,
        max_posts=200,
        campaign_id="serenity_30d",
        requeue_no_go=True,
        end_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
    )

    lead = store["leads"][lead_id]
    assert receipt["posts"] == 1 and receipt["requeued_no_go"] == 1
    assert lead["raw_text"] == "Figure robotics supplier map"
    assert lead["status"] == "pending" and lead["triage"] is None
    assert lead["triage_history"][0]["triage"]["reason"] == "未命中既有 theme"
    assert lead["refs"]["campaign_ids"] == ["serenity_30d"]
    assert leads.get_source_state(store, "x:aleabitoreddit")["since_id"] == "999"


def test_media_backfill_redownloads_when_recorded_cache_file_is_missing(
    monkeypatch, tmp_path
) -> None:
    fake = _FakeApi([])
    missing = tmp_path / "missing.jpg"
    media = harvest_leads._cache_x_media(
        [{"media_key": "3_200", "type": "photo", "url": "https://pbs.twimg.com/media/x.jpg"}],
        lead_id="lead_test",
        section={"cache_media": True},
        x_api=fake,
        existing_media=[{
            "media_key": "3_200",
            "type": "photo",
            "cache": {"local_path": str(missing)},
        }],
    )

    assert media[0]["cache"]["local_path"].endswith("3_200.jpg")
    assert any(call[0] == "media" for call in fake.calls)


def test_media_downloader_rejects_non_x_cdn_without_network(tmp_path) -> None:
    with pytest.raises(x_api.XApiError, match="untrusted_media_url"):
        x_api.download_media_image(
            "https://example.com/screenshot.jpg", tmp_path, "3_1"
        )


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

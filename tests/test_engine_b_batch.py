"""批次核准語法 parser（plan U4）。"""
from __future__ import annotations

from engine_b.batch import parse_batch_reply


def test_parses_multiple_groups() -> None:
    assert parse_batch_reply("1 3 7 8 go 4 drop 5 6 pending") == {
        "go": [1, 3, 7, 8],
        "drop": [4],
        "pending": [5, 6],
    }


def test_commas_and_extra_whitespace() -> None:
    assert parse_batch_reply(" 1,3 , 7  go   4 drop ") == {"go": [1, 3, 7], "drop": [4]}


def test_same_verb_merges_and_dedupes() -> None:
    assert parse_batch_reply("1 go 1 2 go") == {"go": [1, 2]}


def test_unknown_token_is_skipped_and_numbers_carry() -> None:
    # 動詞打錯（"goo"）略過，累積的數字保留給下一個合法 verb
    assert parse_batch_reply("1 2 goo go") == {"go": [1, 2]}


def test_empty_or_no_pairing_returns_empty() -> None:
    assert parse_batch_reply("") == {}
    assert parse_batch_reply("go drop") == {}       # 無數字
    assert parse_batch_reply("1 2 3") == {}          # 無 verb


def test_case_insensitive() -> None:
    assert parse_batch_reply("1 GO 2 Drop") == {"go": [1], "drop": [2]}

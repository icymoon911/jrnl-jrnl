# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

"""Unit tests for ``Journal.filter()`` and its helper predicates."""

import datetime

import pytest

from jrnl.journals.Journal import (
    Journal,
    _make_contains_predicate,
    _make_day_predicate,
    _make_end_date_predicate,
    _make_exclude_tags_predicate,
    _make_month_predicate,
    _make_starred_predicate,
    _make_start_date_predicate,
    _make_tagged_predicate,
    _make_tags_predicate,
    _make_year_predicate,
)
from jrnl.journals.Entry import Entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _journal(**kwargs):
    config = {"tagsymbols": "@"}
    config.update(kwargs)
    return Journal("test", **config)


def _entry(journal, date_str, title, body="", starred=False):
    return Entry(
        journal,
        date=datetime.datetime.strptime(date_str, "%Y-%m-%d"),
        text=title + ("\n" + body if body else ""),
        starred=starred,
    )


@pytest.fixture
def sample_journal():
    j = _journal()
    j.entries = [
        _entry(j, "2024-01-15", "Winter day @snow", "Cold and beautiful", starred=True),
        _entry(j, "2024-03-20", "Spring plans @garden", "Time to plant"),
        _entry(j, "2024-06-10", "Summer vacation @travel @beach", "Heading south"),
        _entry(
            j,
            "2024-09-05",
            "Autumn work @work",
            "Back to the office",
            starred=True,
        ),
        _entry(j, "2024-12-25", "Christmas @family", "Gifts and joy"),
    ]
    return j


# ===================================================================
# Individual predicate tests
# ===================================================================


class TestMakeTagsPredicate:
    def test_returns_none_for_empty_tags(self):
        assert _make_tags_predicate(set(), False) is None

    def test_any_match(self, sample_journal):
        pred = _make_tags_predicate({"@snow"}, strict=False)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1
        assert "winter" in results[0].title.lower()

    def test_any_match_multiple(self, sample_journal):
        pred = _make_tags_predicate({"@snow", "@travel"}, strict=False)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 2

    def test_strict_all_must_match(self, sample_journal):
        pred = _make_tags_predicate({"@travel", "@beach"}, strict=True)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1
        assert "summer" in results[0].title.lower()

    def test_strict_not_all_present(self, sample_journal):
        pred = _make_tags_predicate({"@travel", "@snow"}, strict=True)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 0


class TestMakeStarredPredicate:
    def test_starred_true(self, sample_journal):
        pred = _make_starred_predicate(True)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 2
        assert all(e.starred for e in results)

    def test_starred_false(self, sample_journal):
        pred = _make_starred_predicate(False)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 3


class TestMakeTaggedPredicate:
    def test_tagged_true(self, sample_journal):
        pred = _make_tagged_predicate(True)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 5  # all entries have tags

    def test_tagged_false(self):
        j = _journal()
        e1 = _entry(j, "2024-01-01", "With tag @foo")
        e2 = Entry(j, date=datetime.datetime(2024, 2, 1), text="No tag here")
        j.entries = [e1, e2]
        pred = _make_tagged_predicate(False)
        results = [e for e in j.entries if pred(e)]
        assert len(results) == 1
        assert results[0].title == "No tag here"


class TestDatePredicates:
    def test_month(self, sample_journal):
        pred = _make_month_predicate(6)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1
        assert results[0].date.month == 6

    def test_day(self, sample_journal):
        pred = _make_day_predicate(25)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1

    def test_year(self, sample_journal):
        pred = _make_year_predicate(2024)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 5

    def test_start_date(self, sample_journal):
        start = datetime.datetime(2024, 6, 1)
        pred = _make_start_date_predicate(start)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 3  # Jun, Sep, Dec

    def test_end_date(self, sample_journal):
        end = datetime.datetime(2024, 3, 31)
        pred = _make_end_date_predicate(end)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 2  # Jan, Mar


class TestMakeExcludeTagsPredicate:
    def test_returns_none_for_empty(self):
        assert _make_exclude_tags_predicate(set()) is None

    def test_excludes_matching(self, sample_journal):
        pred = _make_exclude_tags_predicate({"@work"})
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 4

    def test_excludes_multiple_tags(self, sample_journal):
        pred = _make_exclude_tags_predicate({"@work", "@family"})
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 3


class TestMakeContainsPredicate:
    def test_returns_none_for_empty(self):
        assert _make_contains_predicate([], False) is None

    def test_any_mode(self, sample_journal):
        pred = _make_contains_predicate(["cold", "gifts"], strict=False)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 2

    def test_strict_mode(self, sample_journal):
        pred = _make_contains_predicate(["cold", "beautiful"], strict=True)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1

    def test_strict_mode_not_all_present(self, sample_journal):
        pred = _make_contains_predicate(["cold", "gifts"], strict=True)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 0

    def test_case_insensitive(self, sample_journal):
        pred = _make_contains_predicate(["COLD"], strict=False)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1

    def test_searches_title_and_body(self, sample_journal):
        # "Winter" is in the title, "Cold" is in the body
        pred = _make_contains_predicate(["winter"], strict=False)
        results = [e for e in sample_journal.entries if pred(e)]
        assert len(results) == 1


# ===================================================================
# Journal.filter() integration tests
# ===================================================================


class TestJournalFilter:
    def test_no_filter_keeps_all(self, sample_journal):
        sample_journal.filter()
        assert len(sample_journal.entries) == 5

    def test_filter_by_tag(self, sample_journal):
        sample_journal.filter(tags=["@snow"])
        assert len(sample_journal.entries) == 1

    def test_filter_by_tag_strict(self, sample_journal):
        sample_journal.filter(tags=["@travel", "@beach"], strict=True)
        assert len(sample_journal.entries) == 1

    def test_filter_by_tag_any(self, sample_journal):
        sample_journal.filter(tags=["@snow", "@travel"], strict=False)
        assert len(sample_journal.entries) == 2

    def test_filter_by_starred(self, sample_journal):
        sample_journal.filter(starred=True)
        assert len(sample_journal.entries) == 2
        assert all(e.starred for e in sample_journal.entries)

    def test_filter_by_date_range(self, sample_journal):
        sample_journal.filter(start_date="2024-03-01", end_date="2024-09-30")
        assert len(sample_journal.entries) == 3  # Mar, Jun, Sep

    def test_filter_by_start_date_only(self, sample_journal):
        sample_journal.filter(start_date="2024-06-01")
        assert len(sample_journal.entries) == 3  # Jun, Sep, Dec

    def test_filter_by_end_date_only(self, sample_journal):
        sample_journal.filter(end_date="2024-03-31")
        assert len(sample_journal.entries) == 2  # Jan, Mar

    def test_filter_by_contains(self, sample_journal):
        sample_journal.filter(contains=["cold"])
        assert len(sample_journal.entries) == 1

    def test_filter_by_contains_strict(self, sample_journal):
        sample_journal.filter(contains=["cold", "beautiful"], strict=True)
        assert len(sample_journal.entries) == 1

    def test_filter_combined_tag_and_starred(self, sample_journal):
        # @snow is starred, @work is starred — but only @snow matches tag filter
        sample_journal.filter(tags=["@snow"], starred=True)
        assert len(sample_journal.entries) == 1
        assert sample_journal.entries[0].starred

    def test_filter_combined_date_and_contains(self, sample_journal):
        sample_journal.filter(start_date="2024-06-01", contains=["office"])
        assert len(sample_journal.entries) == 1
        assert "autumn" in sample_journal.entries[0].title.lower()

    def test_filter_exclude_tags(self, sample_journal):
        sample_journal.filter(exclude=["@work", "@family"])
        assert len(sample_journal.entries) == 3

    def test_filter_by_month(self, sample_journal):
        sample_journal.filter(month=1)
        assert len(sample_journal.entries) == 1

    def test_filter_by_year(self, sample_journal):
        sample_journal.filter(year=2024)
        assert len(sample_journal.entries) == 5

    def test_filter_combined_multiple(self, sample_journal):
        sample_journal.filter(
            start_date="2024-01-01",
            end_date="2024-06-30",
            starred=True,
        )
        assert len(sample_journal.entries) == 1
        assert sample_journal.entries[0].title.startswith("Winter")

    def test_filter_no_results(self, sample_journal):
        sample_journal.filter(contains=["zzz_nonexistent_zzz"])
        assert len(sample_journal.entries) == 0

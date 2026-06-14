# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

"""Unit tests for Journal.filter() and the filter predicate helpers."""

import datetime

import pytest

from jrnl.journals.Journal import (
    Journal,
    _make_contains_predicate,
    _make_date_predicate,
    _make_starred_predicate,
    _make_tag_predicate,
    _make_tagged_predicate,
)
from jrnl.journals.Entry import Entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_journal_with_entries():
    """Return a Journal pre-populated with a known set of entries."""
    journal = Journal(name="test", tagsymbols="@")
    # We bypass the normal new_entry flow so tests don't need to worry about
    # parsing, sorting, or file I/O.
    entries_data = [
        # (date, title, body, starred, tags)
        (
            datetime.datetime(2023, 1, 15, 9, 0),
            "Morning walk",
            "Went for a walk in the park.",
            True,
            ["@outdoors", "@health"],
        ),
        (
            datetime.datetime(2023, 2, 20, 14, 30),
            "Meeting with @alice",
            "Discussed project roadmap.",
            False,
            ["@work", "@alice"],
        ),
        (
            datetime.datetime(2023, 3, 10, 8, 0),
            "Grocery shopping",
            "Bought apples and bananas.",
            False,
            ["@errands"],
        ),
        (
            datetime.datetime(2023, 6, 1, 20, 0),
            "Beach day",
            "Spent the whole day at the beach with @bob.",
            True,
            ["@outdoors", "@bob"],
        ),
        (
            datetime.datetime(2024, 1, 5, 10, 0),
            "New year goals",
            "Set goals for 2024.",
            False,
            [],
        ),
    ]

    for date, title, body, starred, tags in entries_data:
        text = title + ("\n" + body if body else "")
        entry = Entry(journal, date=date, text=text, starred=starred)
        # Manually set tags so they match our expected data regardless of
        # tagsymbols parsing
        entry._tags = tags
        entry._title = title
        entry._body = body
        journal.entries.append(entry)

    return journal


# ---------------------------------------------------------------------------
# Predicate unit tests
# ---------------------------------------------------------------------------


class TestMakeDatePredicate:
    def test_start_date_inclusive(self):
        journal = _make_journal_with_entries()
        pred = _make_date_predicate(start_date="2023-03-01")
        # Only entries on or after 2023-03-01 should pass
        results = [e for e in journal.entries if pred(e)]
        dates = [e.date for e in results]
        assert all(d >= datetime.datetime(2023, 3, 1) for d in dates)
        assert len(results) == 3  # 2023-03-10, 2023-06-01, and 2024-01-05

    def test_end_date_inclusive(self):
        journal = _make_journal_with_entries()
        pred = _make_date_predicate(end_date="2023-02-28")
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 2  # 2023-01-15 and 2023-02-20

    def test_date_range(self):
        journal = _make_journal_with_entries()
        pred = _make_date_predicate(start_date="2023-02-01", end_date="2023-06-30")
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 3  # Feb, Mar, Jun 2023

    def test_month_filter(self):
        journal = _make_journal_with_entries()
        pred = _make_date_predicate(month=1)
        results = [e for e in journal.entries if pred(e)]
        # January entries: 2023-01-15 and 2024-01-05
        assert len(results) == 2
        assert all(e.date.month == 1 for e in results)

    def test_year_filter(self):
        journal = _make_journal_with_entries()
        pred = _make_date_predicate(year=2024)
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 1
        assert results[0].title == "New year goals"

    def test_no_filter_passes_all(self):
        journal = _make_journal_with_entries()
        pred = _make_date_predicate()
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == len(journal.entries)


class TestMakeTagPredicate:
    def test_any_tag_match(self):
        journal = _make_journal_with_entries()
        pred = _make_tag_predicate(["@outdoors"], [], strict=False)
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 2
        assert all("@outdoors" in e.tags for e in results)

    def test_strict_all_tags_required(self):
        journal = _make_journal_with_entries()
        pred = _make_tag_predicate(["@outdoors", "@health"], [], strict=True)
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 1
        assert results[0].title == "Morning walk"

    def test_strict_missing_tag_excludes(self):
        journal = _make_journal_with_entries()
        # No single entry has both @outdoors and @work
        pred = _make_tag_predicate(["@outdoors", "@work"], [], strict=True)
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 0

    def test_exclude_tags(self):
        journal = _make_journal_with_entries()
        pred = _make_tag_predicate([], ["@outdoors"])
        results = [e for e in journal.entries if pred(e)]
        assert all("@outdoors" not in e.tags for e in results)
        assert len(results) == 3

    def test_no_filter_passes_all(self):
        journal = _make_journal_with_entries()
        pred = _make_tag_predicate([], [])
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == len(journal.entries)


class TestMakeStarredPredicate:
    def test_starred_only(self):
        journal = _make_journal_with_entries()
        pred = _make_starred_predicate(starred=True)
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        assert all(e.starred for e in results)
        assert len(results) == 2

    def test_exclude_starred(self):
        journal = _make_journal_with_entries()
        pred = _make_starred_predicate(exclude_starred=True)
        # exclude_starred=True with starred=False means: entry.starred == False
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        assert all(not e.starred for e in results)
        assert len(results) == 3

    def test_no_filter_returns_none(self):
        pred = _make_starred_predicate()
        assert pred is None


class TestMakeContainsPredicate:
    def test_any_match(self):
        journal = _make_journal_with_entries()
        pred = _make_contains_predicate(["beach", "apples"])
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 2

    def test_strict_all_required(self):
        journal = _make_journal_with_entries()
        pred = _make_contains_predicate(["walk", "park"], strict=True)
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        # Only "Morning walk" has both "walk" and "park"
        assert len(results) == 1
        assert results[0].title == "Morning walk"

    def test_case_insensitive(self):
        journal = _make_journal_with_entries()
        pred = _make_contains_predicate(["BEACH"])
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        assert len(results) == 1

    def test_no_filter_returns_none(self):
        pred = _make_contains_predicate([])
        assert pred is None


class TestMakeTaggedPredicate:
    def test_tagged_only(self):
        journal = _make_journal_with_entries()
        pred = _make_tagged_predicate(tagged=True)
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        assert all(len(e.tags) > 0 for e in results)
        # "New year goals" has no tags, so 4 entries should match
        assert len(results) == 4

    def test_exclude_tagged(self):
        journal = _make_journal_with_entries()
        pred = _make_tagged_predicate(exclude_tagged=True)
        assert pred is not None
        results = [e for e in journal.entries if pred(e)]
        assert all(len(e.tags) == 0 for e in results)
        assert len(results) == 1
        assert results[0].title == "New year goals"

    def test_no_filter_returns_none(self):
        pred = _make_tagged_predicate()
        assert pred is None


# ---------------------------------------------------------------------------
# Integration tests for Journal.filter()
# ---------------------------------------------------------------------------


class TestJournalFilter:
    def test_filter_by_starred(self):
        journal = _make_journal_with_entries()
        journal.filter(starred=True)
        assert len(journal) == 2
        assert all(e.starred for e in journal.entries)

    def test_filter_by_tag(self):
        journal = _make_journal_with_entries()
        journal.filter(tags=["@work"])
        assert len(journal) == 1
        assert journal.entries[0].title == "Meeting with @alice"

    def test_filter_by_tag_strict(self):
        journal = _make_journal_with_entries()
        journal.filter(tags=["@outdoors", "@bob"], strict=True)
        assert len(journal) == 1
        assert journal.entries[0].title == "Beach day"

    def test_filter_by_contains(self):
        journal = _make_journal_with_entries()
        journal.filter(contains=["roadmap"])
        assert len(journal) == 1

    def test_filter_by_date_range(self):
        journal = _make_journal_with_entries()
        journal.filter(start_date="2023-02-01", end_date="2023-04-01")
        assert len(journal) == 2
        titles = {e.title for e in journal.entries}
        assert titles == {"Meeting with @alice", "Grocery shopping"}

    def test_filter_combined_starred_and_tag(self):
        journal = _make_journal_with_entries()
        journal.filter(starred=True, tags=["@outdoors"])
        # Both starred entries have @outdoors
        assert len(journal) == 2

    def test_filter_combined_contains_and_date(self):
        journal = _make_journal_with_entries()
        journal.filter(contains=["beach"], start_date="2023-01-01")
        assert len(journal) == 1
        assert journal.entries[0].title == "Beach day"

    def test_filter_exclude_tags(self):
        journal = _make_journal_with_entries()
        journal.filter(exclude=["@work"])
        # "Meeting with @alice" has @work, should be excluded
        assert len(journal) == 4
        assert all(
            "@work" not in e.tags for e in journal.entries
        )

    def test_filter_no_matches(self):
        journal = _make_journal_with_entries()
        journal.filter(contains=["nonexistent_zzz"])
        assert len(journal) == 0

    def test_filter_no_args_keeps_all(self):
        journal = _make_journal_with_entries()
        original_count = len(journal)
        journal.filter()
        assert len(journal) == original_count

    def test_filter_sets_search_tags(self):
        journal = _make_journal_with_entries()
        journal.filter(tags=["@Outdoors", "@HEALTH"])
        # search_tags should be lowercased
        assert journal.search_tags == {"@outdoors", "@health"}

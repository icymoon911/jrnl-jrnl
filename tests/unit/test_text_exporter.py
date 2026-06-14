# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

"""Unit tests for ``TextExporter.process_markdown_headings`` and ``_slugify``."""

import os
from unittest import mock

from jrnl.plugins.text_exporter import TextExporter


class TestSlugify:
    """``_slugify`` must work as a ``@staticmethod`` (no self/cls)."""

    def test_basic(self):
        assert TextExporter._slugify("Hello World") == "hello-world"

    def test_punctuation_removed(self):
        assert TextExporter._slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert TextExporter._slugify("hello   world") == "hello-world"

    def test_unicode(self):
        result = TextExporter._slugify("café latte")
        assert result == "cafe-latte"

    def test_called_on_class(self):
        # Verify it's callable as a static method (no instance needed)
        assert TextExporter._slugify("Test String") == "test-string"


class TestProcessMarkdownHeadings:
    """Shared heading promotion logic used by MarkdownExporter & YAMLExporter."""

    def test_atx_heading_promoted(self):
        text = "# Title\n"
        result = TextExporter.process_markdown_headings(text, "#")
        assert "## Title" in result

    def test_atx_heading_with_triple_base(self):
        text = "# Title\n"
        result = TextExporter.process_markdown_headings(text, "###")
        assert "#### Title" in result

    def test_setext_h1_converted(self):
        text = "Title\n=====\n"
        result = TextExporter.process_markdown_headings(text, "#")
        assert "## Title" in result
        assert "=====" not in result

    def test_setext_h2_converted(self):
        text = "Title\n-----\n"
        result = TextExporter.process_markdown_headings(text, "#")
        assert "### Title" in result
        assert "-----" not in result

    def test_no_headings_unchanged(self):
        text = "Just some text\nAnother line\n"
        result = TextExporter.process_markdown_headings(text, "#")
        assert "Just some text" in result
        assert "Another line" in result

    def test_empty_body(self):
        result = TextExporter.process_markdown_headings("", "#")
        # Should just be the trailing newline
        assert result == os.linesep

    def test_body_wrapper_newline(self):
        text = "\n# Sub heading\nSome text\n"
        result = TextExporter.process_markdown_headings(text, "###")
        assert "#### Sub heading" in result

    def test_warning_on_deep_headings(self):
        text = "##### Deep heading\n"
        with mock.patch("jrnl.plugins.text_exporter.print_msg") as mock_print:
            TextExporter.process_markdown_headings(
                text,
                "##",
                warn_context={"date": "2024-01-01", "title": "Test"},
            )
            mock_print.assert_called_once()

    def test_no_warning_without_context(self):
        text = "##### Deep heading\n"
        # Even with deep headings, no warning if warn_context is None
        with mock.patch("jrnl.plugins.text_exporter.print_msg") as mock_print:
            TextExporter.process_markdown_headings(text, "##")
            mock_print.assert_not_called()

    def test_ends_with_blank_line(self):
        text = "Some text"
        result = TextExporter.process_markdown_headings(text, "#")
        assert result.endswith(os.linesep)

    def test_multiple_headings(self):
        text = "# H1\nBody\n## H2\nMore body\n"
        result = TextExporter.process_markdown_headings(text, "##")
        assert "### H1" in result
        assert "#### H2" in result
        assert "Body" in result
        assert "More body" in result

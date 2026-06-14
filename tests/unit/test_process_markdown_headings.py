# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

"""Unit tests for TextExporter.process_markdown_headings."""

from jrnl.plugins.text_exporter import TextExporter


class TestProcessMarkdownHeadings:
    def test_atx_heading_bumped(self):
        body = "# Hello\nSome text\n"
        result, warn = TextExporter.process_markdown_headings(body, "#")
        assert "## Hello" in result
        assert warn is False

    def test_atx_heading_bumped_with_h3(self):
        body = "# Hello\nSome text\n"
        result, warn = TextExporter.process_markdown_headings(body, "###")
        assert "#### Hello" in result

    def test_setext_h1_converted(self):
        body = "Title\n=====\nBody text\n"
        result, warn = TextExporter.process_markdown_headings(body, "#")
        assert "## Title" in result
        assert "=====" not in result

    def test_setext_h2_converted(self):
        body = "Subtitle\n--------\nBody text\n"
        result, warn = TextExporter.process_markdown_headings(body, "#")
        assert "## Subtitle" in result
        assert "--------" not in result

    def test_setext_h1_with_h3_base(self):
        body = "Title\n=====\nBody text\n"
        result, warn = TextExporter.process_markdown_headings(body, "###")
        assert "#### Title" in result

    def test_setext_h2_with_h3_base(self):
        body = "Subtitle\n--------\nBody text\n"
        result, warn = TextExporter.process_markdown_headings(body, "###")
        assert "##### Subtitle" in result

    def test_warn_on_heading_overflow(self):
        # "######" (H6) + "#" prefix => H7, should warn
        body = "###### Deep heading\n"
        result, warn = TextExporter.process_markdown_headings(body, "##")
        assert warn is True
        assert "######## Deep heading" in result

    def test_no_warn_within_h6(self):
        body = "## Normal heading\n"
        result, warn = TextExporter.process_markdown_headings(body, "#")
        assert warn is False
        assert "### Normal heading" in result

    def test_empty_body(self):
        result, warn = TextExporter.process_markdown_headings("", "#")
        assert warn is False
        # Should still end with a blank line (os.linesep)
        import os
        assert result == os.linesep

    def test_plain_text_preserved(self):
        body = "Just a paragraph.\nMore text here.\n"
        result, warn = TextExporter.process_markdown_headings(body, "#")
        assert "Just a paragraph." in result
        assert "More text here." in result
        assert warn is False

    def test_ends_with_blank_line(self):
        body = "Some text"
        result, _ = TextExporter.process_markdown_headings(body, "#")
        assert result.endswith("\n")

    def test_multiple_headings(self):
        body = "# First\n## Second\nNormal text\n"
        result, warn = TextExporter.process_markdown_headings(body, "#")
        assert "## First" in result
        assert "### Second" in result
        assert "Normal text" in result

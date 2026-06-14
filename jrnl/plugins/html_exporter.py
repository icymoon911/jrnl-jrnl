# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

import errno
import html
import os
import re
from typing import TYPE_CHECKING

from jrnl.messages import Message
from jrnl.messages import MsgStyle
from jrnl.messages import MsgText
from jrnl.output import print_msg
from jrnl.plugins.text_exporter import TextExporter
from jrnl.plugins.util import get_tags_count

if TYPE_CHECKING:
    from jrnl.journals import Entry
    from jrnl.journals import Journal


class HTMLExporter(TextExporter):
    """This Exporter can convert entries and journals into styled HTML."""

    names = ["html"]
    extension = "html"

    STYLES = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 2rem;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 2rem;
        }
        header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
        .stats {
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }
        .stat {
            background: rgba(255,255,255,0.15);
            border-radius: 6px;
            padding: 0.5rem 1rem;
        }
        .stat-value { font-size: 1.4rem; font-weight: bold; }
        .stat-label { font-size: 0.85rem; opacity: 0.85; }
        .entries { padding: 1rem 2rem 2rem; }
        .entry {
            border-bottom: 1px solid #eee;
            padding: 1.5rem 0;
        }
        .entry:last-child { border-bottom: none; }
        .entry-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .entry-date {
            font-size: 0.85rem;
            color: #888;
            font-weight: 500;
        }
        .entry-starred {
            color: #f5a623;
            font-size: 1.1rem;
        }
        .entry-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 0.5rem;
        }
        .entry-body {
            color: #555;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .tag {
            display: inline-block;
            background: #e8f0fe;
            color: #1a73e8;
            padding: 0.15rem 0.5rem;
            border-radius: 12px;
            font-size: 0.85rem;
            text-decoration: none;
            margin: 0.1rem;
            transition: background 0.2s;
        }
        .tag:hover { background: #d2e3fc; }
        .tags-section {
            margin-top: 0.5rem;
        }
        .short-list .entry {
            padding: 0.75rem 0;
        }
        .short-list .entry-body,
        .short-list .tags-section { display: none; }
        .tag-cloud {
            padding: 1rem 2rem;
            border-bottom: 1px solid #eee;
        }
        .tag-cloud h2 {
            font-size: 1rem;
            color: #666;
            margin-bottom: 0.5rem;
        }
        .tag-cloud a { margin: 0.2rem; }
    """

    @classmethod
    def _escape(cls, text: str) -> str:
        """HTML-escape a string."""
        return html.escape(text, quote=True)

    @classmethod
    def _linkify_tags(cls, text: str, tagsymbols: str = "@#") -> str:
        """Replace tags in text with clickable anchor links."""
        pattern = rf"(?<!\S)([{re.escape(tagsymbols)}][-+*#/\w]+)"

        def replace_tag(match):
            tag = match.group(1)
            tag_slug = tag.lower().lstrip(tagsymbols)
            return f'<a class="tag" href="#tag-{cls._escape(tag_slug)}">{cls._escape(tag)}</a>'

        return re.sub(pattern, replace_tag, cls._escape(text))

    @classmethod
    def _render_stats(cls, journal: "Journal") -> str:
        """Render the statistics summary section."""
        entries = journal.entries
        total = len(entries)

        tags = get_tags_count(journal)
        tag_count = len(tags)

        if entries:
            dates = [e.date for e in entries]
            earliest = min(dates).strftime("%Y-%m-%d")
            latest = max(dates).strftime("%Y-%m-%d")
            if earliest == latest:
                time_span = earliest
            else:
                time_span = f"{earliest} — {latest}"
        else:
            time_span = "N/A"

        starred_count = sum(1 for e in entries if e.starred)

        return f"""
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Entries</div>
            </div>
            <div class="stat">
                <div class="stat-value">{tag_count}</div>
                <div class="stat-label">Tags</div>
            </div>
            <div class="stat">
                <div class="stat-value">{starred_count}</div>
                <div class="stat-label">Starred</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="font-size:1rem">{cls._escape(time_span)}</div>
                <div class="stat-label">Time Span</div>
            </div>
        </div>
        """

    @classmethod
    def _render_tag_cloud(cls, journal: "Journal") -> str:
        """Render a tag cloud section."""
        tags = get_tags_count(journal)
        if not tags:
            return ""

        sorted_tags = sorted(tags, key=lambda x: (-x[0], x[1]))
        tag_links = []
        for count, tag in sorted_tags:
            tag_slug = tag.lower().lstrip(journal.config.get("tagsymbols", "@"))
            tag_links.append(
                f'<a class="tag" href="#tag-{cls._escape(tag_slug)}">'
                f'{cls._escape(tag)} ({count})</a>'
            )

        return f"""
        <div class="tag-cloud">
            <h2>Tags</h2>
            {" ".join(tag_links)}
        </div>
        """

    @classmethod
    def export_entry(cls, entry: "Entry", short: bool = False) -> str:
        """Returns an HTML representation of a single entry."""
        tagsymbols = entry.journal.config.get("tagsymbols", "@")
        date_str = entry.date.strftime(entry.journal.config["timeformat"])

        star_html = ""
        if entry.starred:
            star_html = '<span class="entry-starred" title="Starred">★</span>'

        title_html = cls._linkify_tags(entry.title.rstrip("\n"), tagsymbols)
        date_html = cls._escape(date_str)

        if short:
            return f"""
            <div class="entry">
                <div class="entry-header">
                    <span class="entry-date">{date_html}</span>
                    {star_html}
                </div>
                <div class="entry-title">{title_html}</div>
            </div>
            """

        body_html = cls._linkify_tags(entry.body.rstrip("\n "), tagsymbols) if entry.body else ""

        tags_html = ""
        if entry.tags:
            tag_links = []
            for tag in entry.tags:
                tag_slug = tag.lower().lstrip(tagsymbols)
                tag_links.append(
                    f'<a class="tag" href="#tag-{cls._escape(tag_slug)}" '
                    f'id="tag-{cls._escape(tag_slug)}">{cls._escape(tag)}</a>'
                )
            tags_html = f'<div class="tags-section">{" ".join(tag_links)}</div>'

        body_section = f'<div class="entry-body">{body_html}</div>' if body_html else ""
        entry_id = entry.date.strftime("%Y%m%d%H%M%S")

        return f"""
        <div class="entry" id="entry-{entry_id}">
            <div class="entry-header">
                <span class="entry-date">{date_html}</span>
                {star_html}
            </div>
            <div class="entry-title">{title_html}</div>
            {body_section}
            {tags_html}
        </div>
        """

    @classmethod
    def _wrap_html(cls, journal: "Journal", body_content: str, short: bool = False) -> str:
        """Wrap content in a full HTML document with styles."""
        journal_name = journal.config.get("journal_name", "jrnl")
        entries_class = "entries short-list" if short else "entries"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cls._escape(journal_name)} — Journal Export</title>
    <style>{cls.STYLES}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{cls._escape(journal_name)}</h1>
            <p>Journal Export</p>
            {cls._render_stats(journal)}
        </header>
        {cls._render_tag_cloud(journal)}
        <div class="{entries_class}">
            {body_content}
        </div>
    </div>
    <script>
    // Simple tag filtering: clicking a tag in the cloud filters entries
    document.querySelectorAll('.tag-cloud .tag').forEach(function(tagLink) {{
        tagLink.addEventListener('click', function(e) {{
            e.preventDefault();
            var tagText = this.textContent.replace(/\\s*\\(\\d+\\)\\s*$/, '').toLowerCase();
            var entries = document.querySelectorAll('.entry');
            var anyVisible = false;
            entries.forEach(function(entry) {{
                var entryTags = entry.querySelectorAll('.tag');
                var hasTag = Array.from(entryTags).some(function(t) {{
                    return t.textContent.toLowerCase() === tagText;
                }});
                entry.style.display = hasTag ? '' : 'none';
                if (hasTag) anyVisible = true;
            }});
            // If all hidden (clicking same tag again), show all
            if (!anyVisible) {{
                entries.forEach(function(entry) {{ entry.style.display = ''; }});
            }}
        }});
    }});
    </script>
</body>
</html>"""

    @classmethod
    def export_journal(cls, journal: "Journal", short: bool = False) -> str:
        """Returns an HTML representation of an entire journal."""
        entries_html = "\n".join(
            cls.export_entry(entry, short=short) for entry in journal.entries
        )
        return cls._wrap_html(journal, entries_html, short=short)

    @classmethod
    def write_file(cls, journal: "Journal", path: str, short: bool = False) -> str:
        """Exports a journal into a single HTML file."""
        export_str = cls.export_journal(journal, short=short)
        with open(path, "w", encoding="utf-8") as f:
            f.write(export_str)
        print_msg(
            Message(
                MsgText.JournalExportedTo,
                MsgStyle.NORMAL,
                {"path": path},
            )
        )
        return ""

    @classmethod
    def write_files(cls, journal: "Journal", path: str, short: bool = False) -> str:
        """Exports a journal into individual HTML files for each entry."""
        for entry in journal.entries:
            entry_is_written = False
            while not entry_is_written:
                full_path = os.path.join(path, cls.make_filename(entry))
                try:
                    entry_html = cls._wrap_html(
                        entry.journal,
                        cls.export_entry(entry, short=short),
                        short=short,
                    )
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(entry_html)
                        entry_is_written = True
                except OSError as oserr:
                    title_length = len(str(entry.title))
                    if (
                        oserr.errno == errno.ENAMETOOLONG
                        or oserr.errno == errno.ENOENT
                        or oserr.errno == errno.EINVAL
                    ) and title_length > 1:
                        shorter_file_length = title_length // 2
                        entry.title = str(entry.title)[:shorter_file_length]
                    else:
                        raise
        print_msg(
            Message(
                MsgText.JournalExportedTo,
                MsgStyle.NORMAL,
                {"path": path},
            )
        )
        return ""

    @classmethod
    def export(cls, journal: "Journal", output: str | None = None, short: bool = False) -> str:
        """Exports to individual files if output is an existing path, or into
        a single file if output is a file name, or returns the exporter's
        representation as string if output is None."""
        if output and os.path.isdir(output):
            return cls.write_files(journal, output, short=short)
        elif output:
            return cls.write_file(journal, output, short=short)
        else:
            return cls.export_journal(journal, short=short)

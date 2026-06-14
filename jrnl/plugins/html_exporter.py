# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

import html
import os
import re
from typing import TYPE_CHECKING

from jrnl.journals.Entry import Entry
from jrnl.plugins.text_exporter import TextExporter

if TYPE_CHECKING:
    from jrnl.journals import Journal


HTML_HEADER = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  --bg: #fafafa;
  --fg: #222;
  --muted: #888;
  --accent: #0066cc;
  --tag-bg: #e8f0fe;
  --tag-fg: #1a56db;
  --star: #f5a623;
  --card-bg: #fff;
  --card-border: #e0e0e0;
  --stats-bg: #f0f4f8;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #1a1a2e;
    --fg: #e0e0e0;
    --muted: #999;
    --accent: #66b3ff;
    --tag-bg: #1e3a5f;
    --tag-fg: #80cfff;
    --star: #ffcc33;
    --card-bg: #16213e;
    --card-border: #334;
    --stats-bg: #1a2744;
  }}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.6;
  max-width: 860px;
  margin: 0 auto;
  padding: 2rem 1rem;
}}
h1.journal-title {{
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}}
.stats {{
  background: var(--stats-bg);
  border-radius: 8px;
  padding: 1rem 1.5rem;
  margin-bottom: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}}
.stats .stat {{
  display: flex;
  flex-direction: column;
}}
.stats .stat-value {{
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--accent);
}}
.stats .stat-label {{
  font-size: 0.85rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.entry {{
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 1.2rem;
}}
.entry-header {{
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
  flex-wrap: wrap;
}}
.entry-date {{
  font-size: 0.9rem;
  color: var(--muted);
  white-space: nowrap;
}}
.entry-title {{
  font-size: 1.2rem;
  font-weight: 600;
}}
.entry-title a {{
  color: var(--fg);
  text-decoration: none;
}}
.entry-title a:hover {{
  text-decoration: underline;
}}
.star {{
  color: var(--star);
  font-size: 1.1rem;
  margin-left: 0.3rem;
}}
.entry-body {{
  margin-top: 0.6rem;
  white-space: pre-wrap;
  word-wrap: break-word;
}}
.tag {{
  display: inline-block;
  background: var(--tag-bg);
  color: var(--tag-fg);
  padding: 0.1em 0.5em;
  border-radius: 4px;
  font-size: 0.85em;
  text-decoration: none;
  margin: 0.1em 0.15em;
}}
.tag:hover {{
  filter: brightness(0.9);
}}
.tags-bar {{
  margin-top: 0.5rem;
}}
.filter-notice {{
  display: none;
  background: var(--stats-bg);
  border-radius: 6px;
  padding: 0.6rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}}
.filter-notice.active {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
}}
.filter-notice button {{
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.2em 0.7em;
  cursor: pointer;
  font-size: 0.85rem;
}}
</style>
</head>
<body>
"""

HTML_FOOTER = """\
<script>
(function() {
  var notice = document.getElementById('filter-notice');
  var noticeLabel = document.getElementById('filter-label');
  var entries = document.querySelectorAll('.entry');

  function showAll() {
    entries.forEach(function(e) { e.style.display = ''; });
    notice.classList.remove('active');
    history.replaceState(null, '', window.location.pathname);
  }

  function filterByTag(tag) {
    var lower = tag.toLowerCase();
    entries.forEach(function(e) {
      var tags = (e.getAttribute('data-tags') || '').split(' ');
      e.style.display = tags.indexOf(lower) !== -1 ? '' : 'none';
    });
    noticeLabel.textContent = 'Filtering by: ' + tag;
    notice.classList.add('active');
  }

  document.addEventListener('click', function(ev) {
    if (ev.target.classList.contains('tag')) {
      ev.preventDefault();
      var tag = ev.target.getAttribute('data-tag');
      if (tag) {
        filterByTag(tag);
        history.replaceState(null, '', '#tag=' + encodeURIComponent(tag));
      }
    }
    if (ev.target.id === 'clear-filter') {
      ev.preventDefault();
      showAll();
    }
  });

  // Restore filter from URL hash on load
  var m = window.location.hash.match(/^#tag=(.+)$/);
  if (m) {
    filterByTag(decodeURIComponent(m[1]));
  }
})();
</script>
</body>
</html>
"""


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _highlight_tags(text: str, tagsymbols: str) -> str:
    """Wrap tags in body/title text with clickable <a> elements."""
    pattern = Entry.tag_regex(tagsymbols)

    def _replace(match):
        tag = match.group(1)
        tag_lower = tag.lower()
        return f'<a class="tag" data-tag="{_escape(tag_lower)}" href="#tag={_escape(tag_lower)}">{_escape(tag)}</a>'

    return pattern.sub(_replace, _escape(text))


class HTMLExporter(TextExporter):
    """This Exporter converts entries and journals into styled HTML."""

    names = ["html"]
    extension = "html"

    @classmethod
    def export_entry(cls, entry: "Entry", short: bool = False) -> str:
        """Returns an HTML representation of a single entry."""
        tagsymbols = entry.journal.config.get("tagsymbols", "@")
        timeformat = entry.journal.config.get("timeformat", "%Y-%m-%d %H:%M")
        date_str = entry.date.strftime(timeformat)

        star_html = '<span class="star" title="Starred">★</span>' if entry.starred else ""

        title_html = _highlight_tags(entry.title, tagsymbols)
        tags_html = " ".join(
            f'<a class="tag" data-tag="{_escape(t)}" href="#tag={_escape(t)}">{_escape(t)}</a>'
            for t in sorted(entry.tags)
        )

        parts = [
            '<article class="entry" data-tags="{}">'.format(
                " ".join(t.lower() for t in entry.tags)
            ),
            '  <div class="entry-header">',
            f'    <span class="entry-date">{_escape(date_str)}</span>',
            f'    <span class="entry-title">{title_html}</span>',
            f"    {star_html}",
            "  </div>",
        ]

        if not short:
            if entry.body:
                body_html = _highlight_tags(entry.body, tagsymbols)
                parts.append(f'  <div class="entry-body">{body_html}</div>')
            if tags_html:
                parts.append(f'  <div class="tags-bar">{tags_html}</div>')

        parts.append("</article>")
        return "\n".join(parts)

    @classmethod
    def _build_stats(cls, journal: "Journal") -> str:
        """Build the statistics summary section."""
        entries = journal.entries
        total = len(entries)

        all_tags: set[str] = set()
        for e in entries:
            all_tags.update(t.lower() for t in e.tags)
        tag_count = len(all_tags)

        if total > 0:
            first_date = min(e.date for e in entries)
            last_date = max(e.date for e in entries)
            span_days = (last_date.date() - first_date.date()).days + 1
            if span_days == 1:
                span_str = "1 day"
            elif span_days < 365:
                span_str = f"{span_days} days"
            else:
                years = span_days // 365
                remaining = span_days % 365
                span_str = f"{years}y {remaining}d"
        else:
            span_str = "—"

        starred_count = sum(1 for e in entries if e.starred)

        stats = [
            ("Entries", str(total)),
            ("Tags", str(tag_count)),
            ("Time Span", span_str),
        ]
        if starred_count:
            stats.append(("Starred", str(starred_count)))

        items = "".join(
            f'<div class="stat"><span class="stat-value">{_escape(v)}</span>'
            f'<span class="stat-label">{_escape(k)}</span></div>'
            for k, v in stats
        )
        return f'<div class="stats">{items}</div>'

    @classmethod
    def export_journal(cls, journal: "Journal", short: bool = False) -> str:
        """Returns an HTML representation of an entire journal."""
        journal_name = getattr(journal, "name", "Journal") or "Journal"

        parts = [HTML_HEADER.format(title=_escape(journal_name))]
        parts.append(f'<h1 class="journal-title">{_escape(journal_name)}</h1>')

        # Filter notice (for tag filtering via JS)
        parts.append(
            '<div class="filter-notice" id="filter-notice">'
            '<span id="filter-label"></span>'
            '<button id="clear-filter">Clear filter</button>'
            "</div>"
        )

        # Stats summary
        if journal.entries:
            parts.append(cls._build_stats(journal))

        # Entries
        for entry in journal.entries:
            parts.append(cls.export_entry(entry, short=short))

        parts.append(HTML_FOOTER)
        return "\n".join(parts)

    @classmethod
    def write_file(cls, journal: "Journal", path: str, short: bool = False) -> str:
        """Exports a journal into a single HTML file."""
        export_str = cls.export_journal(journal, short=short)
        with open(path, "w", encoding="utf-8") as f:
            f.write(export_str)
        from jrnl.messages import Message, MsgStyle, MsgText
        from jrnl.output import print_msg
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
                    entry_html = cls._wrap_single_entry_html(entry, short=short)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(entry_html)
                        entry_is_written = True
                except OSError as oserr:
                    import errno
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
        from jrnl.messages import Message, MsgStyle, MsgText
        from jrnl.output import print_msg
        print_msg(
            Message(
                MsgText.JournalExportedTo,
                MsgStyle.NORMAL,
                {"path": path},
            )
        )
        return ""

    @classmethod
    def _wrap_single_entry_html(cls, entry: "Entry", short: bool = False) -> str:
        """Wrap a single entry in a full standalone HTML document."""
        journal_name = getattr(entry.journal, "name", "Journal") or "Journal"
        title_str = f"{entry.title} — {journal_name}"
        parts = [HTML_HEADER.format(title=_escape(title_str))]
        parts.append(cls.export_entry(entry, short=short))
        parts.append(HTML_FOOTER)
        return "\n".join(parts)

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

# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

from typing import TYPE_CHECKING

from jrnl.messages import Message
from jrnl.messages import MsgStyle
from jrnl.messages import MsgText
from jrnl.output import print_msg
from jrnl.plugins.text_exporter import TextExporter

if TYPE_CHECKING:
    from jrnl.journals import Entry
    from jrnl.journals import Journal


class MarkdownExporter(TextExporter):
    """This Exporter can convert entries and journals into Markdown."""

    names = ["md", "markdown"]
    extension = "md"

    @classmethod
    def export_entry(cls, entry: "Entry", to_multifile: bool = True) -> str:
        """Returns a markdown representation of a single entry."""
        date_str = entry.date.strftime(entry.journal.config["timeformat"])
        body_wrapper = "\n" if entry.body else ""
        body = body_wrapper + entry.body

        heading = "#" if to_multifile is True else "###"

        newbody, warn_on_heading_level = cls.process_markdown_headings(
            body, base_heading_level=heading
        )

        if warn_on_heading_level:
            print_msg(
                Message(
                    MsgText.HeadingsPastH6,
                    MsgStyle.WARNING,
                    {"date": date_str, "title": entry.title},
                )
            )

        return f"{heading} {date_str} {entry.title}\n{newbody} "

    @classmethod
    def export_journal(cls, journal: "Journal") -> str:
        """Returns a Markdown representation of an entire journal."""
        out = []
        year, month = -1, -1
        for e in journal.entries:
            if e.date.year != year:
                year = e.date.year
                out.append("# " + str(year))
                out.append("")
            if e.date.month != month:
                month = e.date.month
                out.append("## " + e.date.strftime("%B"))
                out.append("")
            out.append(cls.export_entry(e, False))
        result = "\n".join(out)
        return result

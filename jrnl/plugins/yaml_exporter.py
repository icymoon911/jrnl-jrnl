# Copyright © 2012-2023 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

import re
from typing import TYPE_CHECKING

from jrnl.exception import JrnlException
from jrnl.messages import Message
from jrnl.messages import MsgStyle
from jrnl.messages import MsgText
from jrnl.plugins.text_exporter import TextExporter

if TYPE_CHECKING:
    from jrnl.journals import Entry
    from jrnl.journals import Journal


class YAMLExporter(TextExporter):
    """This Exporter converts entries and journals into Markdown formatted text with
    YAML front matter."""

    names = ["yaml"]
    extension = "md"

    @classmethod
    def export_entry(cls, entry: "Entry", to_multifile: bool = True) -> str:
        """Returns a markdown representation of an entry, with YAML front matter."""
        if to_multifile is False:
            raise JrnlException(Message(MsgText.YamlMustBeDirectory, MsgStyle.ERROR))

        date_str = entry.date.strftime(entry.journal.config["timeformat"])
        body_wrapper = "\n" if entry.body else ""
        body = body_wrapper + entry.body

        tagsymbols = entry.journal.config["tagsymbols"]
        # see also Entry.rag_regex
        multi_tag_regex = re.compile(rf"(?u)^\s*([{tagsymbols}][-+*#/\w]+\s*)+$")

        # Pre-filter tag-only lines before shared heading processing.
        # This was originally interleaved with heading detection; extracting it
        # here lets us reuse ``process_markdown_headings`` unchanged.
        body = "".join(
            line
            for line in body.splitlines(True)
            if not multi_tag_regex.match(line)
        )

        heading = "#"
        newbody = cls.process_markdown_headings(
            body,
            base_heading_level=heading,
            warn_context={"date": date_str, "title": entry.title},
        )

        # set indentation for YAML body block
        spacebody = "\t"
        for line in newbody.splitlines(True):
            spacebody = spacebody + "\t" + line

        dayone_attributes = ""
        if hasattr(entry, "uuid"):
            dayone_attributes += "uuid: " + entry.uuid + "\n"
        if (
            hasattr(entry, "creator_device_agent")
            or hasattr(entry, "creator_generation_date")
            or hasattr(entry, "creator_host_name")
            or hasattr(entry, "creator_os_agent")
            or hasattr(entry, "creator_software_agent")
        ):
            dayone_attributes += "creator:\n"
            if hasattr(entry, "creator_device_agent"):
                dayone_attributes += f"    device agent: {entry.creator_device_agent}\n"
            if hasattr(entry, "creator_generation_date"):
                dayone_attributes += "    generation date: {}\n".format(
                    str(entry.creator_generation_date)
                )
            if hasattr(entry, "creator_host_name"):
                dayone_attributes += f"    host name: {entry.creator_host_name}\n"
            if hasattr(entry, "creator_os_agent"):
                dayone_attributes += f"    os agent: {entry.creator_os_agent}\n"
            if hasattr(entry, "creator_software_agent"):
                dayone_attributes += (
                    f"    software agent: {entry.creator_software_agent}\n"
                )

        # TODO: copy over pictures, if present
        # source directory is  entry.journal.config['journal']
        # output directory is...?

        return (
            "{start}\n"
            "title: {title}\n"
            "date: {date}\n"
            "starred: {starred}\n"
            "tags: {tags}\n"
            "{dayone}body: |{body}{end}"
        ).format(
            start="---",
            date=date_str,
            title=entry.title,
            starred=entry.starred,
            tags=", ".join([tag[1:] for tag in entry.tags]),
            dayone=dayone_attributes,
            body=spacebody,
            end="...",
        )

    @classmethod
    def export_journal(cls, journal: "Journal"):
        """Returns an error, as YAML export requires a directory as a target."""
        raise JrnlException(Message(MsgText.YamlMustBeDirectory, MsgStyle.ERROR))

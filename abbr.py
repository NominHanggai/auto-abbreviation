import sys
import os
import urllib.request
import warnings
import logging
import re
import abc
from collections import OrderedDict
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    TextIO,
    Tuple,
    Union,
)

class Block(abc.ABC):
    """A abstract superclass of all top-level building blocks of a bibtex file.

    E.g. a ``@string`` block, a ``@preamble`` block, an ``@entry`` block, a comment, etc.
    """

    def __init__(
        self,
        start_line: Optional[int] = None,
        raw: Optional[str] = None,
        parser_metadata: Optional[Dict[str, Any]] = None,
    ):
        self._start_line_in_file = start_line
        self._raw = raw
        self._parser_metadata: Dict[str, Any] = parser_metadata
        if parser_metadata is None:
            self._parser_metadata: Dict[str, Any] = {}

    @property
    def start_line(self) -> Optional[int]:
        """The line number of the first line of this block in the parsed string."""
        return self._start_line_in_file

    @property
    def raw(self) -> Optional[str]:
        """The raw, unmodified string (bibtex) representation of this block.

        Note: Middleware does not update this field, hence, after applying middleware
        to a library, this field may be outdated.
        """
        return self._raw

    @property
    def parser_metadata(self) -> Dict[str, Any]:
        """EXPERIMENTAL: field for middleware to store auxiliary information.

        As an end-user, as long as you are not writing middleware, you probably
        do not need to use this field.

        ** Warning (experimental) **
        The content of this field is undefined and may change at any time.

        This field is intended for middleware to store auxiliary information.
        It is a key-value store, where the key is a string and the value is any
        python object.
        This allows for example to pass information between different middleware.
        """
        return self._parser_metadata

    def get_parser_metadata(self, key: str) -> Optional[Any]:
        """EXPERIMENTAL: get auxiliary information stored in ``parser_metadata``.

        See attribute ``parser_metadata`` for more information."""
        return self._parser_metadata.get(key, None)

    def set_parser_metadata(self, key: str, value: Any):
        """EXPERIMENTAL: set auxiliary information stored in ``parser_metadata``.

        See attribute ``parser_metadata`` for more information."""
        self._parser_metadata[key] = value

    def __eq__(self, other):
        # make sure they have the same type and same content
        return (
            isinstance(other, self.__class__)
            and isinstance(self, other.__class__)
            and self.__dict__ == other.__dict__
        )

class String(Block):
    """Bibtex Blocks of the ``@string`` type, e.g. ``@string{me = "My Name"}``."""

    def __init__(
        self,
        key: str,
        value: str,
        start_line: Optional[int] = None,
        raw: Optional[str] = None,
    ):
        super().__init__(start_line, raw)
        self._key = key
        self._value = value

    @property
    def key(self) -> str:
        """The key of the string, e.g. ``me`` in ``@string{me = "My Name"}``."""
        return self._key

    @key.setter
    def key(self, value: str):
        self._key = value

    @property
    def value(self) -> str:
        """The value of the string, e.g. ``"My Name"`` in ``@string{me = "My Name"}``."""
        return self._value

    @value.setter
    def value(self, value: str):
        self._value = value

    def __str__(self):
        return f"String (line: {self.start_line}, key: `{self.key}`): `{self.value}`"

    def __repr__(self):
        return (
            f"String(key=`{self.key}`, value=`{self.value}`, "
            f"start_line={self.start_line}, raw=`{self.raw}`)"
        )


class Preamble(Block):
    """Bibtex Blocks of the ``@preamble`` type, e.g. ``@preamble{This is a preamble}``."""

    def __init__(self, value: str, start_line: Optional[int] = None, raw: Optional[str] = None):
        super().__init__(start_line, raw)
        self._value = value

    @property
    def value(self) -> str:
        """The value of the preamble, e.g. ``blabla`` in ``@preamble{blabla}``."""
        return self._value

    @value.setter
    def value(self, value: str):
        self._value = value

    def __str__(self):
        return f"Preamble (line: {self.start_line}): `{self.value}`"

    def __repr__(self):
        return f"Preamble(value=`{self.value}`, " f"start_line={self.start_line}, raw=`{self.raw}`)"


class ExplicitComment(Block):
    """Bibtex Blocks of the ``@comment`` type, e.g. ``@comment{This is a comment}``."""

    def __init__(self, comment: str, start_line: Optional[int] = None, raw: Optional[str] = None):
        super().__init__(start_line, raw)
        self._comment = comment

    @property
    def comment(self) -> str:
        """The value of the comment, e.g. ``blabla`` in ``@comment{blabla}``."""
        return self._comment

    @comment.setter
    def comment(self, value: str):
        self._comment = value

    def __str__(self):
        return f"ExplicitComment (line: {self.start_line}): `{self.comment}`"

    def __repr__(self):
        return (
            f"ExplicitComment(comment=`{self.comment}`, "
            f"start_line={self.start_line}, raw=`{self.raw}`)"
        )


class ImplicitComment(Block):
    """Bibtex outside of an ``@{...}`` block, which is treated as a comment."""

    def __init__(self, comment: str, start_line: Optional[int] = None, raw: Optional[str] = None):
        super().__init__(start_line, raw)
        self._comment = comment

    @property
    def comment(self) -> str:
        """The (possibly multi-line) comment."""
        return self._comment

    @comment.setter
    def comment(self, value: str):
        self._comment = value

    def __str__(self):
        return f"ImplicitComment (line: {self.start_line}): `{self.comment}`"

    def __repr__(self):
        return (
            f"ImplicitComment(comment=`{self.comment}`, "
            f"start_line={self.start_line}, raw=`{self.raw}`)"
        )


class Field:
    """A field of a Bibtex entry, e.g. ``author = {John Doe}``."""

    def __init__(self, key: str, value: Any, start_line: Optional[int] = None):
        self._start_line = start_line
        self._key = key
        self._value = value

    @property
    def key(self) -> str:
        """The key of the field, e.g. ``author`` in ``author = {John Doe}``."""
        return self._key

    @key.setter
    def key(self, value: str):
        self._key = value

    @property
    def value(self) -> Any:
        """The value of the field, e.g. ``{John Doe}`` in ``author = {John Doe}``."""
        return self._value

    @value.setter
    def value(self, value: Any):
        self._value = value

    @property
    def start_line(self) -> int:
        """The line number of the first line of this field in the originally parsed string."""
        return self._start_line

    def __eq__(self, other):
        # make sure they have the same type and same content
        return (
            isinstance(other, self.__class__)
            and isinstance(self, other.__class__)
            and self.__dict__ == other.__dict__
        )

    def __str__(self):
        return f"Field (line: {self.start_line}, key: `{self.key}`): `{self.value}`"

    def __repr__(self):
        return f"Field(key=`{self.key}`, value=`{self.value}`, " f"start_line={self.start_line})"


class Entry(Block):
    """Bibtex Blocks of the ``@entry`` type, e.g. ``@article{Cesar2013, ...}``."""

    def __init__(
        self,
        entry_type: str,
        key: str,
        fields: List[Field],
        start_line: Optional[int] = None,
        raw: Optional[str] = None,
    ):
        super().__init__(start_line, raw)
        self._entry_type = entry_type
        self._key = key
        self._fields = fields

    @property
    def entry_type(self):
        """The type of the entry, e.g. ``article`` in ``@article{Cesar2013, ...}``."""
        return self._entry_type

    @entry_type.setter
    def entry_type(self, value: str):
        self._entry_type = value

    @property
    def key(self):
        """The key of the entry, e.g. ``Cesar2013`` in ``@article{Cesar2013, ...}``."""
        return self._key

    @key.setter
    def key(self, value: str):
        self._key = value

    @property
    def fields(self) -> List[Field]:
        """The key-value attributes of an entry, as ``Field`` instances."""
        return self._fields

    @fields.setter
    def fields(self, value: List[Field]):
        self._fields = value

    @property
    def fields_dict(self) -> Dict[str, Field]:
        """A dict of fields, with field keys as keys.

        Note that with duplicate field keys, the behavior is undefined."""
        return {field.key: field for field in self._fields}

    def set_field(self, field: Field):
        """Adds a new field, or replaces existing with same key."""
        if field.key in self.fields_dict:
            i = [f.key for f in self._fields].index(field.key)
            self._fields[i] = field
        else:
            self._fields.append(field)

    def pop(self, key: str, default=None) -> Optional[Field]:
        """Removes and returns the field with the given key.

        :param key: The key of the field to remove.
        :param default: The value to return if the field does not exist."""
        try:
            field = self.fields_dict.pop(key)
        except KeyError:
            return default

        self._fields = [f for f in self._fields if f.key != key]
        return field

    def get(self, key: str, default=None) -> Optional[Field]:
        """Returns the field with the given key, or the default value if it does not exist.

        :param key: The key of the field.
        :param default: The value to return if the field does not exist."""
        return self.fields_dict.get(key, default)

    def __contains__(self, key: str) -> bool:
        """Dict-mimicking ``in`` operator."""
        return key in self.fields_dict

    def __getitem__(self, key: str) -> Any:
        """Dict-mimicking index.

        This serves for partial v1.x backwards compatibility,
        as well as for a shorthand for accessing field values.

        Note that with duplicate field keys, the behavior is undefined.
        """
        if key == "ENTRYTYPE":
            return self.entry_type
        if key == "ID":
            return self.key
        return self.fields_dict[key].value

    def __setitem__(self, key: str, value: Any):
        """Dict-mimicking index.

        This serves for partial v1.x backwards compatibility,
        as well as for a shorthand for `set_field`.
        """
        self.set_field(Field(key, value))

    def __delitem__(self, key):
        """Dict-mimicking index.

        This serves for partial v1.x backwards compatibility,
        as well as for a shorthand for `pop`.
        """
        self.pop(key)

    def items(self):
        """Dict-mimicking, for partial v1.x backwards compatibility.

        For newly written code, it's recommended to use `entry.entry_type`,
        `entry.key` and `entry.fields` instead."""
        return [
            ("ENTRYTYPE", self.entry_type),
            ("ID", self.key),
        ] + [(f.key, f.value) for f in self.fields]

    def __str__(self):
        lines = [f"Entry (line: {self.start_line}, type: `{self.entry_type}`, key: `{self.key}`):"]
        lines.extend([f"\t`{f.key}` = `{f.value}`" for f in self.fields])
        return "\n".join(lines)

    def __repr__(self):
        return (
            f"Entry(entry_type=`{self.entry_type}`, key=`{self.key}`, "
            f"fields=`{self.fields.__repr__()}`, start_line={self.start_line})"
        )


class ParsingFailedBlock(Block):
    """A block that could not be parsed due to some raised exception."""

    def __init__(
        self,
        error: Exception,
        start_line: Optional[int] = None,
        raw: Optional[str] = None,
        ignore_error_block: Optional[Block] = None,
    ):
        super().__init__(start_line, raw)
        self._error = error
        self._ignore_error_block = ignore_error_block

    @property
    def error(self) -> Exception:
        """The exception that was raised during parsing."""
        return self._error

    @property
    def ignore_error_block(self) -> Optional[Block]:
        """The possibly faulty block when ignoring the error.

        This may be None, as it may not always be possible to ignore the error.
        For errors caused by middleware, this is typically the block without
        the middleware applied."""
        return self._ignore_error_block


class MiddlewareErrorBlock(ParsingFailedBlock):
    """A block that could not be parsed due to a middleware error.

    To get the block that caused this error, call `block.ignore_error_block`
    (which is the block with the middleware not or only partially applied)."""

    def __init__(self, block: Block, error: Exception):
        super().__init__(
            start_line=block.start_line,
            raw=block.raw,
            error=error,
            ignore_error_block=block,
        )


class DuplicateBlockKeyBlock(ParsingFailedBlock):
    """An error-indicating block created for blocks with keys present in the library already.

    To get the block that caused this error, call `block.ignore_error_block`."""

    def __init__(
        self,
        key: str,
        previous_block: Block,
        duplicate_block: Block,
        start_line: Optional[int] = None,
        raw: Optional[str] = None,
    ):
        super().__init__(
            error=Exception(f"Duplicate entry key '{key}'"),
            start_line=start_line,
            raw=raw,
            ignore_error_block=duplicate_block,
        )
        self._key = key
        self._previous_block = previous_block

    @property
    def key(self) -> str:
        """The key of the entry, e.g. ``Cesar2013`` in ``@article{Cesar2013, ...}``."""
        return self._key

    @key.setter
    def key(self, value: str):
        self._key = value

    @property
    def previous_block(self) -> Block:
        """A reference to a previous block with the same key."""
        return self._previous_block


class DuplicateFieldKeyBlock(ParsingFailedBlock):
    """An error-indicating block indicating a duplicate field key in an entry."""

    def __init__(self, duplicate_keys: Set[str], entry: Entry):
        sorted_duplicate_keys = sorted(list(duplicate_keys))
        super().__init__(
            error=Exception(
                f"Duplicate field keys on entry: '{', '.join(sorted_duplicate_keys)}'."
                f"Note: The entry (containing duplicate) is available as `failed_block.entry`"
            ),
            start_line=entry.start_line,
            raw=entry.raw,
            ignore_error_block=entry,
        )
        self._duplicate_keys: Set[str] = duplicate_keys

    @property
    def duplicate_keys(self) -> Set[str]:
        """The field-keys that occurred more than once in the entry."""
        return self._duplicate_keys


# Library Class

from typing import Dict
from typing import List
from typing import Union

# TODO Use functools.lru_cache for library properties (which create lists when called)


class Library:
    """A collection of parsed bibtex blocks."""

    def __init__(self, blocks: Union[List[Block], None] = None):
        self._blocks = []
        self._entries_by_key = dict()
        self._strings_by_key = dict()
        if blocks is not None:
            self.add(blocks)

    def add(self, blocks: Union[List[Block], Block], fail_on_duplicate_key: bool = False):
        """Add blocks to library.

        The adding is key-safe, i.e., it is made sure that no duplicate keys are added.
        for the same type (i.e., String or Entry). Duplicates are silently replaced with
        a DuplicateKeyBlock.

        :param blocks: Block or list of blocks to add.
        :param fail_on_duplicate_key:
            If True, raises ValueError if a block was replaced with a DuplicateKeyBlock.
        """
        if isinstance(blocks, Block):
            blocks = [blocks]

        _added_blocks = []
        for block in blocks:
            # This may replace block with a DuplicateEntryKeyBlock
            block = self._add_to_dicts(block)
            self._blocks.append(block)
            _added_blocks.append(block)

        if fail_on_duplicate_key:
            duplicate_keys = []
            for original, added in zip(blocks, _added_blocks):
                if original is not added and isinstance(added, DuplicateBlockKeyBlock):
                    duplicate_keys.append(added.key)

            if len(duplicate_keys) > 0:
                raise ValueError(
                    f"Duplicate keys found: {duplicate_keys}. "
                    f"Duplicate entries have been added to the library as DuplicateBlockKeyBlock."
                    f"Use `library.failed_blocks` to access them. "
                )

    def remove(self, blocks: Union[List[Block], Block]):
        """Remove blocks from library.

        :param blocks: Block or list of blocks to remove.
        :raises ValueError: If block is not in library."""
        if isinstance(blocks, Block):
            blocks = [blocks]

        for block in blocks:
            self._blocks.remove(block)
            if isinstance(block, Entry):
                del self._entries_by_key[block.key]
            elif isinstance(block, String):
                del self._strings_by_key[block.key]

    def replace(self, old_block: Block, new_block: Block, fail_on_duplicate_key: bool = True):
        """Replace a block with another block, at the same position.

        :param old_block: Block to replace.
        :param new_block: Block to replace with.
        :param fail_on_duplicate_key: If False, adds a DuplicateKeyBlock if
                a block with new_block.key (other than old_block) already exists.
        :raises ValueError: If old_block is not in library or if fail_on_duplicate_key is True
                and a block with new_block.key (other than old_block) already exists."""
        try:
            index = self._blocks.index(old_block)
            self.remove(old_block)
        except ValueError:
            raise ValueError("Block to replace is not in library.")

        block_after_add = self._add_to_dicts(new_block)
        self._blocks.insert(index, block_after_add)

        if (
            new_block is not block_after_add
            and isinstance(block_after_add, DuplicateBlockKeyBlock)
            and fail_on_duplicate_key
        ):
            # Revert changes to old_block
            #   Don't fail on duplicate key, as this would lead to an infinite recursion
            #   (should never happen for a clean library, but could happen if the user
            #   tampered with the internals of the library).
            self.replace(block_after_add, old_block, fail_on_duplicate_key=False)
            raise ValueError("Duplicate key found.")

    @staticmethod
    def _cast_to_duplicate(
        prev_block_with_same_key: Union[Entry, String], duplicate: Union[Entry, String]
    ):
        assert isinstance(prev_block_with_same_key, type(duplicate)) or isinstance(
            duplicate, type(prev_block_with_same_key)
        ), (
            "Internal BibtexParser Error. Duplicate blocks share no common type."
            f"Found {type(prev_block_with_same_key)} and {type(duplicate)}, but both should be"
            f"either instance of String or instance of Entry."
            f"Please report this issue at the bibtexparser issue tracker.",
        )

        assert (
            prev_block_with_same_key.key == duplicate.key
        ), "Internal BibtexParser Error. Duplicate blocks have different keys."

        return DuplicateBlockKeyBlock(
            start_line=duplicate.start_line,
            raw=duplicate.raw,
            key=duplicate.key,
            previous_block=prev_block_with_same_key,
            duplicate_block=duplicate,
        )

    def _add_to_dicts(self, block):
        """Safely add block references to private dict structures.

        :param block: Block to add.
        :returns: The block that was added to the library. If a block
            of same type and with same key already existed, a
            DuplicateKeyBlock is returned (not added to dict).
        """
        if isinstance(block, Entry):
            try:
                prev_block_with_same_key = self._entries_by_key[block.key]
                block = self._cast_to_duplicate(prev_block_with_same_key, block)
            except KeyError:
                # No duplicate found
                self._entries_by_key[block.key] = block
        elif isinstance(block, String):
            try:
                prev_block_with_same_key = self._strings_by_key[block.key]
                block = self._cast_to_duplicate(prev_block_with_same_key, block)
            except KeyError:
                # No duplicate found
                self._strings_by_key[block.key] = block
        return block

    @property
    def blocks(self) -> List[Block]:
        """All blocks in the library, preserving order of insertion."""
        return self._blocks

    @property
    def failed_blocks(self) -> List[ParsingFailedBlock]:
        """All blocks that could not be parsed, preserving order of insertion."""
        return [b for b in self._blocks if isinstance(b, ParsingFailedBlock)]

    @property
    def strings(self) -> List[String]:
        """All @string blocks in the library, preserving order of insertion."""
        return list(self._strings_by_key.values())

    @property
    def strings_dict(self) -> Dict[str, String]:
        """Dict representation of all @string blocks in the library."""
        return self._strings_by_key

    @property
    def entries(self) -> List[Entry]:
        """All entry (@article, ...) blocks in the library, preserving order of insertion."""
        # Note: Taking this from the entries dict would be faster, but does not preserve order
        #   e.g. in cases where `replace` has been called.
        return [b for b in self._blocks if isinstance(b, Entry)]

    @property
    def entries_dict(self) -> Dict[str, Entry]:
        """Dict representation of all entry blocks in the library."""
        return self._entries_by_key.copy()

    @property
    def preambles(self) -> List[Preamble]:
        """All @preamble blocks in the library, preserving order of insertion."""
        return [block for block in self._blocks if isinstance(block, Preamble)]

    @property
    def comments(self) -> List[Union[ExplicitComment, ImplicitComment]]:
        """All comment blocks in the library, preserving order of insertion."""
        return [
            block for block in self._blocks if isinstance(block, (ExplicitComment, ImplicitComment))
        ]



class Splitter:
    """Object responsible for splitting a BibTeX string into blocks.

    For each bibtex string, a new Splitter object should be created.
    The splitter is kept as basic as possible in its functionality
    (e.g., enclosing such as `{...}` are not removed).

    This allows for maximum flexibility in the parsing process,
    by subsequently applying middleware."""

    def __init__(self, bibstr: str):
        # Add a newline at the beginning to simplify parsing
        #   (we only allow "@"-block starts after a newline)
        self.bibstr = f"\n{bibstr}"

        self._markiter = None
        self._unaccepted_mark = None

        # Keep track of line we're currently looking at.
        #   `-1` compensates for manually added `\n` above
        self._current_line = -1

        self._reset_block_status(current_char_index=0)

    def _reset_block_status(self, current_char_index):
        self._open_brackets = 0
        self._is_quote_open = False
        self._expected_next: Optional[List[str]] = None

        # By default, we assume that an implicit comment is started
        #   at the beginning of the file and after each @{...} block.
        #   We then ignore empty implicit comments.
        self._implicit_comment_start_line = self._current_line
        self._implicit_comment_start: Optional[int] = current_char_index

    def _end_implicit_comment(self, end_char_index) -> Optional[ImplicitComment]:
        if self._implicit_comment_start is None:
            return  # No implicit comment started

        comment = self.bibstr[self._implicit_comment_start : end_char_index]

        # Clear leading and trailing empty lines,
        #   and count how many lines were removed, to adapt start_line below
        leading_empty_lines = 0
        i = 0
        for i, char in enumerate(comment):
            if char == "\n":
                leading_empty_lines += 1
            elif not char.isspace():
                break

        comment = comment[i:].rstrip()

        if len(comment) > 0:
            return ImplicitComment(
                start_line=self._implicit_comment_start_line + leading_empty_lines,
                raw=comment,
                comment=comment,
            )
        else:
            return None

    def _next_mark(self, accept_eof: bool) -> Optional[re.Match]:
        # Check if there is a mark that was previously not consumed
        #   and return it if so
        if self._unaccepted_mark is not None:
            m = self._unaccepted_mark
            self._unaccepted_mark = None
            self._current_char_index = m.start()
            return m

        # Get next mark from iterator
        m = next(self._markiter, None)
        if m is not None:
            self._current_char_index = m.start()
            if m.group(0) == "\n":
                self._current_line += 1
                return self._next_mark(accept_eof=accept_eof)
        else:
            # Reached end of file
            self._current_char_index = len(self.bibstr)
            if not accept_eof:
                raise BlockAbortedException(
                    abort_reason="Unexpectedly reached end of file.",
                    end_index=self._current_char_index,
                )
        return m

    def _move_to_closed_bracket(self) -> int:
        """Index of the curly bracket closing a just opened one."""
        num_additional_brackets = 0
        while True:
            m = self._next_mark(accept_eof=False)
            if m.group(0) == "{":
                num_additional_brackets += 1
            elif m.group(0) == "}":
                if num_additional_brackets == 0:
                    return m.start()
                else:
                    num_additional_brackets -= 1
            elif m.group(0).startswith("@"):
                self._unaccepted_mark = m
                raise BlockAbortedException(
                    abort_reason=f"Unexpected block start: `{m.group(0)}`. "
                    f"Was still looking for closing bracket",
                    end_index=m.start() - 1,
                )

    def _move_to_comma_or_closing_curly_bracket(
        self, currently_quote_escaped=False, num_open_curls=0
    ) -> int:
        """Index of the end of the field, taking quote-escape into account."""

        if num_open_curls > 0 and currently_quote_escaped:
            raise ParserStateException(
                message="Internal error in parser. "
                "Found a field-value that is both quote-escaped and curly-escaped. "
                "Please report this bug."
            )

        def _is_escaped():
            return currently_quote_escaped or num_open_curls > 0

        # iterate over marks until we find end of field
        while True:
            next_mark = self._next_mark(accept_eof=False)

            # Handle "escape" characters
            if next_mark.group(0) == '"' and not num_open_curls > 0:
                currently_quote_escaped = not currently_quote_escaped
                continue
            elif next_mark.group(0) == "{" and not currently_quote_escaped:
                num_open_curls += 1
                continue
            elif next_mark.group(0) == "}" and not currently_quote_escaped and num_open_curls > 0:
                num_open_curls -= 1
                continue

            # Check for end of field
            elif next_mark.group(0) == "," and not _is_escaped():
                self._unaccepted_mark = next_mark
                return next_mark.start()
            # Check for end of entry:
            elif next_mark.group(0) == "}" and not _is_escaped():
                self._unaccepted_mark = next_mark
                return next_mark.start()

            # Sanity-check: If new block is starting, we abort
            elif next_mark.group(0).startswith("@"):
                self._unaccepted_mark = next_mark

                if currently_quote_escaped:
                    looking_for = '`"`'
                elif num_open_curls > 0:
                    looking_for = "`}`"
                else:
                    looking_for = "`,` or `}`"

                raise BlockAbortedException(
                    abort_reason=f"Unexpected block start: `{next_mark.group(0)}`. "
                    f"Was still looking for field-value closing {looking_for} ",
                    end_index=next_mark.start() - 1,
                )

    def _move_to_end_of_entry(self, first_key_start: int) -> Tuple[List[Field], int, Set[str]]:
        """Move to the end of the entry and return the fields and the end index."""
        result = []
        keys = set()
        duplicate_keys = set()

        key_start = first_key_start
        while True:
            equals_mark = self._next_mark(accept_eof=False)
            if equals_mark.group(0) == "}":
                # End of entry
                return result, equals_mark.end(), duplicate_keys

            if equals_mark.group(0) != "=":
                self._unaccepted_mark = equals_mark
                raise BlockAbortedException(
                    abort_reason="Expected a `=` after entry key, "
                    f"but found `{equals_mark.group(0)}`.",
                    end_index=equals_mark.start(),
                )

            # We follow the convention that the field start line
            #   is where the `=` between key and value is.
            start_line = self._current_line
            key_end = equals_mark.start()
            value_start = equals_mark.end()
            value_end = self._move_to_comma_or_closing_curly_bracket(
                currently_quote_escaped=False, num_open_curls=0
            )

            key = self.bibstr[key_start:key_end].strip()
            value = self.bibstr[value_start:value_end].strip()

            if key in keys:
                duplicate_keys.add(key)

            keys.add(key)
            result.append(Field(start_line=start_line, key=key, value=value))

            # If next mark is a comma, continue
            after_field_mark = self._next_mark(accept_eof=False)
            if after_field_mark.group(0) == ",":
                key_start = after_field_mark.end()
            elif after_field_mark.group(0) == "}":
                # If next mark is a closing bracket, put it back (will return in next loop iteration)
                self._unaccepted_mark = after_field_mark
                continue
            else:
                self._unaccepted_mark = after_field_mark
                raise BlockAbortedException(
                    abort_reason="Expected either a `,` or `}` after a closed entry field value, "
                    f"but found a {after_field_mark.group(0)} before.",
                    end_index=after_field_mark.start(),
                )

    def split(self, library: Optional[Library] = None) -> Library:
        """Split the bibtex-string into blocks and add them to the library.

        Args:
            library: The library to add the blocks to. If None, a new library is created.
        Returns:
            The library with the added blocks.
        """
        self._markiter = re.finditer(
            r"(?<!\\)[\{\}\",=\n]|@[\w]*( |\t)*(?={)", self.bibstr, re.MULTILINE
        )

        if library is None:
            library = Library()
        else:
            logger.info("Adding blocks to existing library.")

        while True:
            m = self._next_mark(accept_eof=True)
            if m is None:
                break

            m_val = m.group(0).lower()

            if m_val.startswith("@"):
                # Clean up previous block implicit_comment
                implicit_comment = self._end_implicit_comment(m.start())
                if implicit_comment is not None:
                    library.add(implicit_comment)
                self._implicit_comment_start = None

                start_line = self._current_line
                try:
                    # Start new block parsing
                    if m_val.startswith("@comment"):
                        library.add(self._handle_explicit_comment())
                    elif m_val.startswith("@preamble"):
                        library.add(self._handle_preamble())
                    elif m_val.startswith("@string"):
                        library.add(self._handle_string(m))
                    else:
                        library.add(self._handle_entry(m, m_val))

                except BlockAbortedException as e:
                    logger.warning(
                        f"Parsing of `{m_val}` block (line {start_line}) "
                        f"aborted on line {self._current_line} "
                        f"due to syntactical error in bibtex:\n {e.abort_reason}"
                    )
                    logger.info(
                        "We will try to continue parsing, but this might lead to unexpected results."
                        "The failed block will be stored in the `failed_blocks`of the library."
                    )
                    library.add(
                        ParsingFailedBlock(
                            start_line=start_line,
                            raw=self.bibstr[m.start() : e.end_index],
                            error=e,
                        )
                    )

                except ParserStateException as e:
                    # This is a bug in the parser, not in the bibtex. We should not continue.
                    logger.error(
                        "python-bibtexparser detected an invalid state. Please report this bug."
                    )
                    logger.error(e.message)
                    raise e
                except Exception as e:
                    # For unknown exeptions, we want to fail hard and get the info in our issue tracker.
                    logger.error(
                        f"Unexpected exception while parsing `{m_val}` block (line {start_line})"
                        "Please report this bug."
                    )
                    raise e

                self._reset_block_status(current_char_index=self._current_char_index + 1)
            else:
                # Part of implicit comment
                continue

        # Check if there's an implicit comment at the EOF
        if self._implicit_comment_start is not None:
            comment = self._end_implicit_comment(len(self.bibstr))
            if comment is not None:
                library.add(comment)

        return library

    def _handle_explicit_comment(self) -> ExplicitComment:
        """Handle explicit comment block. Return end index"""
        start_index = self._current_char_index
        start_line = self._current_line
        start_bracket_mark = self._next_mark(accept_eof=False)
        if start_bracket_mark.group(0) != "{":
            self._unaccepted_mark = start_bracket_mark
            # Note: The following should never happen, as we check for the "{" in the regex
            raise RegexMismatchException(
                first_match="@comment{",
                expected_match="{",
                second_match=start_bracket_mark.group(0),
            )
        end_bracket_index = self._move_to_closed_bracket()
        comment_str = self.bibstr[start_bracket_mark.end() : end_bracket_index].strip()
        return ExplicitComment(
            start_line=start_line,
            comment=comment_str,
            raw=self.bibstr[start_index : end_bracket_index + 1],
        )

    def _handle_entry(self, m, m_val) -> Union[Entry, ParsingFailedBlock]:
        """Handle entry block. Return end index"""
        start_line = self._current_line
        entry_type = m_val[1:].strip()
        start_bracket_mark = self._next_mark(accept_eof=False)
        if start_bracket_mark.group(0) != "{":
            self._unaccepted_mark = start_bracket_mark
            # Note: The following should never happen, as we check for the "{" in the regex
            raise ParserStateException(
                message="matched a regex that should end with `{`, "
                "e.g. `@article{`, "
                "but no closing bracket was found."
            )
        comma_mark = self._next_mark(accept_eof=False)
        if comma_mark.group(0) == "}":
            # This is an entry without any comma after the key, and with no fields
            #   Used e.g. by RefTeX (see issue #384)
            key = self.bibstr[m.end() + 1 : comma_mark.start()].strip()
            fields, end_index, duplicate_keys = [], comma_mark.end(), []
        elif comma_mark.group(0) != ",":
            self._unaccepted_mark = comma_mark
            raise BlockAbortedException(
                abort_reason=f"Expected comma after entry key, but found {comma_mark.group(0)}",
                end_index=comma_mark.end(),
            )
        else:
            self._open_brackets += 1
            key = self.bibstr[m.end() + 1 : comma_mark.start()].strip()
            fields, end_index, duplicate_keys = self._move_to_end_of_entry(comma_mark.end())

        entry = Entry(
            start_line=start_line,
            entry_type=entry_type,
            key=key,
            fields=fields,
            raw=self.bibstr[m.start() : end_index],
        )

        # If there were duplicate field keys, we return a DuplicateFieldKeyBlock wrapping
        if len(duplicate_keys) > 0:
            return DuplicateFieldKeyBlock(duplicate_keys=duplicate_keys, entry=entry)
        else:
            return entry

    def _handle_string(self, m) -> String:
        """Handle string block. Return end index"""
        # Get next mark, which should be an equals sign
        start_i = self._current_char_index
        start_line = self._current_line
        start_bracket_mark = self._next_mark(accept_eof=False)
        if start_bracket_mark.group(0) != "{":
            self._unaccepted_mark = start_bracket_mark
            # Note: The following should never happen, as we check for the "{" in the regex
            raise ParserStateException(
                message="matched a string def regex (`@string{`) that "
                "should end with `{`, but no closing bracket was found."
            )
        equals_mark = self._next_mark(accept_eof=False)
        if equals_mark.group(0) != "=":
            self._unaccepted_mark = equals_mark
            raise BlockAbortedException(
                abort_reason="Expected equals sign after field key,"
                f" but found {equals_mark.group(0)}",
                end_index=equals_mark.end(),
            )
        key = self.bibstr[m.end() + 1 : equals_mark.start()].strip()
        value_start = equals_mark.end()
        end_i = self._move_to_closed_bracket()
        value = self.bibstr[value_start:end_i].strip()
        return String(
            start_line=start_line,
            key=key,
            value=value,
            raw=self.bibstr[start_i : end_i + 1],
        )

    def _handle_preamble(self) -> Preamble:
        """Handle preamble block. Return end index"""
        start_i = self._current_char_index
        start_line = self._current_line
        start_bracket_mark = self._next_mark(accept_eof=False)
        if start_bracket_mark.group(0) != "{":
            self._unaccepted_mark = start_bracket_mark
            # Note: The following should never happen, as we check for the "{" in the regex
            raise ParserStateException(
                message="matched a preamble def regex (`@preamble{`) that "
                "should end with `{`, but no closing bracket was found."
            )

        end_bracket_index = self._move_to_closed_bracket()
        preamble = self.bibstr[start_bracket_mark.end() : end_bracket_index]
        return Preamble(
            start_line=start_line,
            value=preamble,
            raw=self.bibstr[start_i : end_bracket_index + 1],
        )

# Middleware Class
from typing import Collection
from typing import Union

class Middleware(abc.ABC):
    """Implements a function to transform a block or library.

    Abstract Class. You should extend either BlockMiddleware
    or LibraryMiddleware"""

    def __init__(
        self,
        allow_parallel_execution: bool = True,
        allow_inplace_modification: bool = True,
    ):
        """

        :param allow_inplace_modification: See corresponding property.
        :param allow_parallel_execution: See corresponding property.
        """
        self._allow_inplace_modification = allow_inplace_modification
        self._allow_parallel_execution = allow_parallel_execution

    @property
    def allow_inplace_modification(self) -> bool:
        """If true, the middleware **may** modify the block in-place.

        I.e., if true, the output of `transform` may be the same instance
        as the input. If false, new instances must be returned.
        """
        return self._allow_inplace_modification

    @property
    def allow_parallel_execution(self) -> bool:
        """True indicates that the middleware is threadsafe."""
        return self._allow_parallel_execution

    @abc.abstractmethod
    def transform(self, library: "Library") -> "Library":
        """Main entrypoint of the middleware. Applies transformation to a library."""
        raise NotImplementedError("called abstract method")


class BlockMiddleware(Middleware, abc.ABC):
    """Transforms a library on a per-block basis.

    The `BlockMiddleware` replaces a block with zero, one or more
    new (transformed) blocks.

    Changes may rely on the state of the overall library,
    but must not change the state of the library directly,
    except if `allow_inplace_modification` is true.
    """

    @classmethod
    def metadata_key(cls) -> str:
        """Identifier of the middleware.
        This key is used to identify the middleware in a blocks metadata.
        """
        return cls.__name__

    # docstr-coverage: inherited
    def transform(self, library: "Library") -> "Library":
        # TODO Multiprocessing (only for large library and if allow_multi..)
        blocks = []
        for b in library.blocks:
            transformed = self.transform_block(b, library)
            # Case 1: None. Skip it.
            if transformed is None:
                pass
            # Case 2: A single block. Add it to the list.
            elif isinstance(transformed, Block):
                blocks.append(transformed)
            # Case 3: A collection. Append all the elements.
            elif isinstance(transformed, Collection):
                # check that all the items are indeed blocks
                for item in transformed:
                    if not isinstance(item, Block):
                        raise TypeError(
                            f"Non-Block type found in transformed collection: {type(item)}"
                        )
                blocks.extend(transformed)
            # Case 4: Something else. Error.
            else:
                raise TypeError(f"Illegal output type from transform_block: {type(transformed)}")
        return Library(blocks=blocks)

    def transform_block(
        self, block: Block, library: "Library"
    ) -> Union[Block, Collection[Block], None]:
        """Transform a block.

        :param block: Block to transform.
        :param library: Library containing the block.
            Should typically not be modified during
            the transformation, but be considered as read-only.
            If the library is modified, make sure to set the `allow_multithreading`
            constructor argument to false
        :return: Transformed block. If the block should be removed, return None.
            If the block should be replaced by multiple blocks, return a collection
            of blocks. If the block should be replaced by a single block, return
            the single block. If the block should not be modified, return a copy of
            the original block.
            The returned block has to be a new instance, except if
            `self.allow_inplace_modification` is True (in which case the block
            may also return the original block).
        """
        block = block if self.allow_inplace_modification else deepcopy(block)
        if isinstance(block, Entry):
            return self.transform_entry(block, library)
        elif isinstance(block, String):
            return self.transform_string(block, library)
        elif isinstance(block, Preamble):
            return self.transform_preamble(block, library)
        elif isinstance(block, ExplicitComment):
            return self.transform_explicit_comment(block, library)
        elif isinstance(block, ImplicitComment):
            return self.transform_implicit_comment(block, library)

        logger.warning(f"Unknown block type {type(block)}")
        return block

    def transform_entry(
        self, entry: Entry, library: "Library"
    ) -> Union[Block, Collection[Block], None]:
        """Transform an entry. Called by `transform_block` if the block is an entry.

        Note: This method modifies the passed entry. For a method
        respecting the `allow_inplace_modification` property,
        you should use `transform` or `transform_block` instead.
        """
        return entry

    def transform_string(
        self, string: String, library: "Library"
    ) -> Union[Block, Collection[Block], None]:
        """Transform a string. Called by `transform_block` if the block is a string.

        Note: This method modifies the passed string. For a method
        respecting the `allow_inplace_modification` property,
        you should use `transform` or `transform_block` instead.
        """
        return string

    def transform_preamble(
        self, preamble: Preamble, library: "Library"
    ) -> Union[Block, Collection[Block], None]:
        """Transform a preamble. Called by `transform_block` if the block is a preamble.

        Note: This method modifies the passed preamble. For a method
        respecting the `allow_inplace_modification` property,
        you should use `transform` or `transform_block` instead.
        """
        return preamble

    def transform_explicit_comment(
        self, explicit_comment: ExplicitComment, library: "Library"
    ) -> Union[Block, Collection[Block], None]:
        """Transform an explicit comment. Called by `transform_block` if the block is an explicit comment.

        Note: This method modifies the passed explicit comment. For a method
        respecting the `allow_inplace_modification` property,
        you should use `transform` or `transform_block` instead.
        """
        return explicit_comment

    def transform_implicit_comment(
        self, implicit_comment: ImplicitComment, library: "Library"
    ) -> Union[Block, Collection[Block], None]:
        """Transform an implicit comment. Called by `transform_block` if the block is an implicit comment.

        Note: This method modifies the passed implicit comment. For a method
        respecting the `allow_inplace_modification` property,
        you should use `transform` or `transform_block` instead.
        """
        return implicit_comment


class LibraryMiddleware(Middleware, abc.ABC):
    """Changes an overall library at once (not just on a per-block basis).

    Examples of library-wide changes are:
    - Re-Sorting the blocks in the library.
    - Transforming the library instance to a custom subclass of Library.

    Whatever can be done in a BlockMiddleware, should be done
    in a BlockMiddleware (and not in a LibraryMiddleware),
    for performance reasons (e.g. deleting blocks, ...).
    """

    def __init__(self, allow_inplace_modification: bool = True):
        # As library middleware is run per library (not per block individually),
        #   it cannot be parallelized.
        super().__init__(
            allow_inplace_modification=allow_inplace_modification,
            allow_parallel_execution=False,
        )

    def transform(self, library: "Library") -> "Library":
        """Transform a library.

        :param library: Library to transform.
        :return: Transformed library. If the library should not be modified,
            return a copy of the original library.
            The returned library has to be a new instance, except if
            `self.allow_inplace_modification` is True (in which case the library
            may also return the original library).
        """
        library = library if self.allow_inplace_modification else deepcopy(library)
        return library

import logging
from typing import Dict
from typing import List
from typing import Set

logger = logging.getLogger(__name__)


class NormalizeFieldKeys(BlockMiddleware):
    """Normalize field keys to lowercase.

    In case of conflicts (e.g. both 'author' and 'Author' exist in the same entry),
    a warning is emitted, and the last value wins.

    Some other middlewares, such as `SeparateCoAuthors`, assume lowercase key names.
    """

    def __init__(self, allow_inplace_modification: bool = True):
        super().__init__(
            allow_inplace_modification=allow_inplace_modification,
            allow_parallel_execution=True,
        )

    # docstr-coverage: inherited
    def transform_entry(self, entry: Entry, library: "Library") -> Entry:
        seen_normalized_keys: Set[str] = set()
        new_fields_dict: Dict[str, Field] = {}
        for field in entry.fields:
            normalized_key: str = field.key.lower()
            # if the normalized key is already present, apply "last one wins"
            # otherwise preserve insertion order
            # if a key is overwritten, emit a detailed warning
            # if performance is a concern, we could emit a warning with only {entry.key}
            # to remove "seen_normalized_keys" and this if statement
            if normalized_key in seen_normalized_keys:
                logger.warning(
                    f"NormalizeFieldKeys: in entry '{entry.key}': "
                    + f"duplicate normalized key '{normalized_key}' "
                    + f"(original '{field.key}'); overriding previous value"
                )
            seen_normalized_keys.add(normalized_key)
            field.key = normalized_key
            new_fields_dict[normalized_key] = field

        new_fields: List[Field] = list(new_fields_dict.values())
        entry.fields = new_fields

        return entry


REMOVED_ENCLOSING_KEY = "removed_enclosing"

def _value_is_nonstring_or_enclosed(value: Any) -> bool:
    """Check if value is an int or enclosed in curly braces."""
    if not isinstance(value, str):
        return True
    if value.startswith('"') and value.endswith('"'):
        return True
    if value.startswith("{") and value.endswith("}"):
        return True
    return False

class ResolveStringReferencesMiddleware(LibraryMiddleware):
    """Replace strings references with their values."""

    # docstr-coverage: inherited
    def __init__(self, allow_inplace_modification: bool = True):
        super().__init__(allow_inplace_modification)

    # docstr-coverage: inherited
    @classmethod
    def metadata_key(cls) -> str:
        return "ResolveStringReferences"

    # docstr-coverage: inherited
    def transform(self, library: Library) -> Library:
        if not self.allow_inplace_modification:
            library = deepcopy(library)

        entry: Entry
        raised_enclosing_warning = False
        for entry in library.entries:
            resolved_fields = list()
            if not raised_enclosing_warning and REMOVED_ENCLOSING_KEY in entry.parser_metadata:
                raised_enclosing_warning = True
                warnings.warn(
                    (
                        "The RemoveEnclosingMiddleware must not run before "
                        "the ResolveStringReferencesMiddleware."
                        "We continue, but string interpolation is likely to fail,"
                        "or to be too aggressive (i.e., replace too many strings)."
                    ),
                    UserWarning,
                )

            field: Field
            for field in entry.fields:
                if _value_is_nonstring_or_enclosed(field.value):
                    continue
                if field.value not in library.strings_dict:
                    continue
                field.value = library.strings_dict[field.value].value
                resolved_fields.append(field.key)

            if resolved_fields:
                entry.parser_metadata[self.metadata_key()] = resolved_fields

        return library

class RemoveEnclosingMiddleware(BlockMiddleware):
    """Remove enclosing characters from values such as field and strings.

    This middleware removes enclosing characters from a field value.
    It is useful when the field value is enclosed in braces or quotes
    (which is the case for the vast majority of values).

    Note: If you want to interpolate strings, you should do so
    before removing any enclosing.
    """

    def __init__(self, allow_inplace_modification: bool = True):
        super().__init__(
            allow_inplace_modification=allow_inplace_modification,
            allow_parallel_execution=True,
        )

    # docstr-coverage: inherited
    @classmethod
    def metadata_key(cls) -> str:
        return REMOVED_ENCLOSING_KEY

    @staticmethod
    def _strip_enclosing(value: str) -> Tuple[str, Union[str, None]]:
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
            return value[1:-1], "{"
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1], '"'
        return value, "no-enclosing"

    # docstr-coverage: inherited
    def transform_entry(self, entry: Entry, library: Library) -> Entry:
        field: Field
        metadata = dict()
        for field in entry.fields:
            stripped, enclosing = self._strip_enclosing(field.value)
            field.value = stripped
            metadata[field.key] = enclosing
        entry.parser_metadata[self.metadata_key()] = metadata
        return entry

    # docstr-coverage: inherited
    def transform_string(self, string: String, library: Library) -> String:
        stripped, enclosing = self._strip_enclosing(string.value)
        string.value = stripped
        string.parser_metadata[self.metadata_key()] = enclosing
        return string

def default_parse_stack(allow_inplace_modification: bool = True) -> List[Middleware]:
    """The default parse stack to be applied after splitting, if not specified otherwise."""
    return [
        ResolveStringReferencesMiddleware(allow_inplace_modification=allow_inplace_modification),
        RemoveEnclosingMiddleware(allow_inplace_modification=allow_inplace_modification),
    ]

def _build_parse_stack(
    parse_stack: Optional[Iterable[Middleware]],
    append_middleware: Optional[Iterable[Middleware]],
) -> List[Middleware]:
    if parse_stack is not None and append_middleware is not None:
        raise ValueError(
            "Provided both parse_stack and append_middleware."
            "Only one should be provided."
            "(append_middleware should only be used with the default parse_stack,"
            "i.e., when the passed parse_stack is None.)"
        )

    if parse_stack is None:
        parse_stack = default_parse_stack(allow_inplace_modification=True)

    if append_middleware is None:
        return list(parse_stack)

    parse_stack_types = [type(m) for m in parse_stack]
    append_stack_types = {type(m) for m in append_middleware}
    stack_types_intersect = set(parse_stack_types).intersection(append_stack_types)
    if len(stack_types_intersect) > 0:
        warnings.warn(
            "Some middleware passed in append_middleware are "
            f"already in the default parse_stack ({stack_types_intersect})."
        )

    return list(parse_stack) + list(append_middleware)


def parse_file(
    path: str,
    parse_stack: Optional[Iterable[Middleware]] = None,
    append_middleware: Optional[Iterable[Middleware]] = None,
    encoding: str = "UTF-8",
) -> Library:
    """Parse a BibTeX file

    :param path: Path to BibTeX file
    :param parse_stack:
        List of middleware to apply to the database after splitting.
        If ``None`` (default), a default stack will be used providing simple standard functionality.

    :param append_middleware:
        List of middleware to append to the default stack
        (ignored if a not-``None`` parse_stack is passed).

    :param encoding: Encoding of the .bib file. Default encoding is ``"UTF-8"``.
    :return: Library: Parsed BibTeX library
    """
    with open(path, encoding=encoding) as f:
        bibtex_str = f.read()
        splitter = Splitter(bibstr=bibtex_str)
        library = splitter.split(library=None)
        for middleware in _build_parse_stack(parse_stack, append_middleware):
            library = middleware.transform(library=library)
        return library

# --- Helper: load abbreviation map ---
def load_abbreviation_map(journal_list_file):
    abbr_map = {}
    with open(journal_list_file, encoding="utf-8") as f:
        for line in f:
            if '=' not in line:
                continue
            full, abbr = line.strip().split(' = ', 1)
            if full and abbr:
                abbr_map[full.lower()] = abbr
    return abbr_map

# --- Helper: normalize for deduplication ---
def normalize(text):
    return ''.join(text.lower().split())

# --- Main logic ---
def abbreviate_bibtex_files(input_filenames, journal_list_file):
    # Download journal list if not present
    JOURNAL_LIST_URL = (
        "https://gist.githubusercontent.com/FilipDominec/6df14b3424e335c4a47a96640f7f0df9/raw/"
        "74876d2d5df9ed60492ef3a14dc3599a6a6a9cfc/journalList.txt"
    )
    if not os.path.isfile(journal_list_file):
        print("Downloading journal list...")
        urllib.request.urlretrieve(JOURNAL_LIST_URL, journal_list_file)

    abbr_map = load_abbreviation_map(journal_list_file)

    # Read all BibTeX entries from all files
    all_entries = []
    for fname in input_filenames:
        # with open(fname, encoding="utf-8") as f:
            bib_db = parse_file(fname)
            bib_db = NormalizeFieldKeys().transform(bib_db)
            all_entries.extend(bib_db.entries)
    # # Deduplicate and apply abbreviation
    seen = {}
    deduped = []
    for entry in all_entries:
        # Normalize title and journal for deduplication
        try :
            title = entry.get("title").value
        except AttributeError:
            title = ""
        try:
            journal = entry.get("journal").value
        except AttributeError:
            journal = ""
        # title = entry.get("Title").value
        # journal = entry.get("Journal").value
        key = (normalize(title), normalize(journal))
        if key in seen:
            continue  # Duplicate, skip
        seen[key] = True

        # Abbreviate journal name if possible
        if journal:
            abbr = abbr_map.get(journal.lower())
            if abbr:
                entry["journal"] = abbr

        deduped.append(entry)
    
    output_filename = "abbreviated.bib"
    def format_value(value):
        # Wrap string in braces, escape braces inside
        # value = value.replace('{', '\\{').replace('}', '\\}')
        return f'{{{value}}}'

    indent = "    "
    with open(output_filename, "w", encoding="utf-8") as out_f:
        # for entry in deduped:
        for entry in all_entries:
            entrytype = entry.entry_type
            entryid = entry.key
            out_f.write(f"@{entrytype}{{{entryid},\n")
            # Write all fields except ENTRYTYPE and ID
            for key, value in entry.items():
                if key in ('ENTRYTYPE', 'ID'):
                    continue
                out_f.write(f"{indent}{key} = {format_value(str(value))},\n")
            out_f.write("}\n\n")

    print(f"BibTeX database with abbreviated journals saved into '{output_filename}'.")


import contextlib
with contextlib.redirect_stdout(sys.stderr):
    input_filenames = sys.argv[1:]
    if not input_filenames:
        print("Error: specify one or more files to be processed!")
        sys.exit(1)
    abbreviate_bibtex_files(input_filenames, "journals.txt")

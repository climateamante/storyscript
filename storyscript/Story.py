# -*- coding: utf-8 -*-
import io
import os
from functools import lru_cache


from lark.exceptions import UnexpectedInput, UnexpectedToken

from .compiler import Compiler
from .compiler.lowering import Lowering
from .exceptions import CompilerError, StoryError, StorySyntaxError
from .parser import Parser


@lru_cache(maxsize=1)
def _parser():
    """
    Cached instance of the parser
    """
    return Parser()


class Story:
    """
    Represents a single story and exposes methods for reading, parsing and
    compiling it.
    """

    def __init__(self, story, features, path=None):
        self.story = story
        self.path = path
        self.lines = story.splitlines(keepends=False)
        self.features = features

    @classmethod
    def read(cls, path):
        """
        Reads a story
        """
        has_error = False
        try:
            with io.open(path, 'r') as file:
                r = file.read()
                return r
        except FileNotFoundError:
            has_error = True

        if has_error:
            abspath = os.path.abspath(path)
            raise StoryError.create_error('file_not_found', path=path,
                                          abspath=abspath)

    @classmethod
    def from_file(cls, path, features):
        """
        Creates a story from a file source
        """
        return Story(cls.read(path), features, path=path)

    @classmethod
    def from_stream(cls, stream, features):
        """
        Creates a story from a stream source
        """
        return Story(stream.read(), features)

    def error(self, error):
        """
        Handles errors by wrapping the real error in a smart StoryError
        """
        return StoryError(error, self, path=self.path)

    def parse(self, parser, lower=False, allow_single_quotes=False):
        """
        Parses the story, storing the tree
        """
        if parser is None:
            parser = self._parser()
        try:
            self.tree = parser.parse(self.story,
                                     allow_single_quotes=allow_single_quotes)
            if lower:
                proc = Lowering(parser, features=self.features)
                self.tree = proc.process(self.tree)
        except (CompilerError, StorySyntaxError) as error:
            raise self.error(error) from error
        except UnexpectedToken as error:
            raise self.error(error) from error
        except UnexpectedInput as error:
            raise self.error(error) from error

    def compile(self):
        """
        Compiles the story and stores the result.
        """
        try:
            self.compiled = Compiler.compile(self.tree, story=self,
                                             features=self.features)
        except (CompilerError, StorySyntaxError) as error:
            raise self.error(error) from error

    def lex(self, parser):
        """
        Lexes a story
        """
        if parser is None:
            parser = self._parser()
        return parser.lex(self.story)

    def process(self, parser=None):
        """
        Parse and compile a story, returning the compiled JSON
        """
        if parser is None:
            parser = self._parser()
        self.parse(parser=parser)
        self.compile()
        return self.compiled

    def _parser(self):
        """
        Returns the default Parser instance (cached)
        """
        return _parser()

    def line(self, i):
        """
        Returns a line from the story source.
        Line numbers start with 1.
        """
        if isinstance(i, str):
            if not i.isdigit():
                return None
            i = int(i)
        assert i <= len(self.lines)
        return self.lines[i - 1]

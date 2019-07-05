# -*- coding: utf-8 -*-
import os

import click

from lark.exceptions import UnexpectedCharacters, UnexpectedToken
from lark.lexer import Token

from pytest import fixture, mark

from storyscript.ErrorCodes import ErrorCodes
from storyscript.Intention import Intention
from storyscript.exceptions import CompilerError, StoryError


@fixture
def error(magic):
    return magic()


@fixture
def storyerror(error, magic):
    story = magic()
    return StoryError(error, story)


def test_storyerror_init(storyerror, error):
    assert storyerror.error == error
    assert storyerror.story is not None
    assert storyerror.path is None
    assert storyerror.error_tuple is None
    assert issubclass(StoryError, SyntaxError)


def test_storyerror_init_path():
    storyerror = StoryError('error', 'story', path='hello.story')
    assert storyerror.path == 'hello.story'


def test_storyerror_name(storyerror):
    assert storyerror.name() == 'story'


def test_storyerror_name_path(patch, storyerror):
    patch.object(os, 'getcwd', return_value='/abspath')
    storyerror.path = 'hello.story'
    assert storyerror.name() == 'hello.story'


def test_storyerror_name_reduce_path(patch, storyerror):
    """
    Ensures that paths are simplified for stories in the current working
    directory.
    """
    patch.object(os, 'getcwd', return_value='/abspath')
    storyerror.path = '/abspath/hello.story'
    assert storyerror.name() == 'hello.story'


def test_storyerror_int_line(patch, storyerror, error):
    """
    Ensures int_line returns the correct line number
    """
    storyerror.error.line = 1
    assert storyerror.int_line() == 1


def test_storyerror_int_line_string(patch, storyerror, error):
    """
    Ensures int_line returns the correct line number with string lines
    """
    storyerror.error.line = '1'
    assert storyerror.int_line() == 1


def test_storyerror_int_line_fake_tree(patch, storyerror, error):
    """
    Ensures int_line returns the correct line number with fake tree lines
    """
    storyerror.error.line = '1.2.3'
    assert storyerror.int_line() == 1


def test_storyerror_get_line(patch, storyerror, error):
    """
    Ensures get_line returns the error line
    """
    patch.object(StoryError, 'int_line', return_value=1)
    storyerror.story.line.return_value = 'x = 0'
    assert storyerror.get_line() == 'x = 0'
    storyerror.story.line.assert_called_with(1)


def test_storyerror_header(patch, storyerror, error):
    """
    Ensures StoryError.header returns the correct text.
    """
    patch.object(click, 'style')
    patch.many(StoryError, ['name', 'int_line'])
    template = 'Error: syntax error in {} at line {}, column {}'
    result = storyerror.header()
    click.style.assert_called_with(StoryError.name(), bold=True)
    assert result == template.format(click.style(),
                                     storyerror.int_line(), error.column)


def test_storyerror_symbols(patch, storyerror, error):
    """
    Ensures StoryError.symbols creates one symbol when there is no end column.
    """
    patch.object(click, 'style')
    del error.end_column
    error.column = '1'
    result = storyerror.symbols(line=' a')
    click.style.assert_called_with('      ^', fg='red')
    assert result == click.style()


def test_storyerror_symbols_tabs(patch, storyerror, error):
    """
    Ensures StoryError.symbols deals correctly with tabs.
    """
    patch.object(click, 'style')
    del error.end_column
    error.column = '1'
    result = storyerror.symbols(line='\ta')
    click.style.assert_called_with('       ^', fg='red')
    assert result == click.style()


def test_story_error_symbols_end_column(patch, storyerror, error):
    """
    Ensures StoryError.symbols creates many symbols when there is an end
    column.
    """
    patch.object(click, 'style')
    error.end_column = '4'
    error.column = '1'
    result = storyerror.symbols(line=' abc')
    click.style.assert_called_with('      ^^^', fg='red')
    assert result == click.style()
    storyerror.with_color = False
    result = storyerror.symbols(line=' abc')
    assert result == '      ^^^'


def test_story_error_symbols_end_column_tabs(patch, storyerror, error):
    """
    Ensures StoryError.symbols deals correctly with tabs.
    """
    patch.object(click, 'style')
    error.end_column = '4'
    error.column = '1'
    storyerror.with_color = False
    result = storyerror.symbols(line='\ta\tc')
    assert result == '       ^^^^'


def test_storyerror_highlight(patch, storyerror, error):
    """
    Ensures StoryError.highlight produces the correct text.
    """
    patch.many(StoryError, ['get_line', 'int_line', 'symbols'])
    error.column = '1'
    result = storyerror.highlight()
    highlight = StoryError.symbols()
    args = (storyerror.int_line(), StoryError.get_line().replace(), highlight)
    assert result == '{}|    {}\n{}'.format(*args)


def test_storyerror_error_code(storyerror):
    storyerror.error_tuple = ('code', 'hint')
    assert storyerror.error_code() == 'code'


def test_storyerror_hint(storyerror):
    storyerror.error_tuple = ('code', 'hint')
    assert storyerror.hint() == 'hint'


def test_storyerror_hint_unidentified_error(storyerror, patch):
    patch.object(StoryError, '_internal_error')
    storyerror.error_tuple = ErrorCodes.unidentified_error
    storyerror.error = Exception('Custom.Error')
    assert storyerror.hint() == storyerror._internal_error()


def test_storyerror_hint_unidentified_compiler_error(storyerror, patch):
    patch.object(StoryError, '_internal_error')
    storyerror.error_tuple = ErrorCodes.unidentified_error
    storyerror.error = CompilerError(None)
    assert storyerror.hint() == storyerror._internal_error()


def test_storyerror_hint_invalid_character(patch, storyerror):
    storyerror.error = UnexpectedCharacters('seq', 0, line=1, column=5)
    storyerror.error_tuple = ErrorCodes.invalid_character
    storyerror._format = {'character': '$'}
    assert storyerror.hint() == '`$` is not allowed here'


def test_storyerror_hint_redeclared(patch, storyerror, magic):
    storyerror.error = CompilerError(
        'reserved_keyword',
        format_args={'keyword': 'foo'})
    storyerror.error_tuple = ErrorCodes.reserved_keyword
    assert storyerror.hint() == '`foo` is a reserved keyword'


def test_storyerror_hint_unexpected_token(patch, storyerror, ):
    expected = ['a', 'b', 'c']
    storyerror.error = UnexpectedToken(token='and', expected=expected)
    storyerror.error_tuple = ErrorCodes.unexpected_token
    storyerror._format = {'token': 'and', 'allowed': str(expected)}
    assert storyerror.hint() == ('`and` is not allowed here. '
                                 f'Allowed: {str(expected)}')


def test_storyerror_unexpected_token_code(patch, call_count, storyerror):
    patch.init(Intention)
    patch.object(Intention, 'assignment', return_value=False)
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    result = storyerror.unexpected_token_code()
    Intention.__init__.assert_called_with(storyerror.get_line())
    call_count(Intention, ['assignment', 'unnecessary_colon'])
    assert result == ErrorCodes.unexpected_token
    assert storyerror._format == {
        'token': str(storyerror.error.token),
        'allowed': str(storyerror.error.expected),
    }


def test_storyerror_unexpected_token_code_nl(patch, call_count, storyerror):
    """
    Test an unexpected token error with _NL
    """
    patch.init(Intention)
    patch.object(Intention, 'assignment', return_value=False)
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    storyerror.error.token.type = '_NL'
    result = storyerror.unexpected_token_code()
    Intention.__init__.assert_called_with(storyerror.get_line())
    call_count(Intention, ['assignment', 'unnecessary_colon'])
    assert result == ErrorCodes.unexpected_end_of_line
    assert storyerror._format == {
        'allowed': str(storyerror.error.expected),
    }


def test_storyerror_unexpected_token_code_assignment(patch, storyerror):
    patch.init(Intention)
    patch.object(storyerror, 'get_line')
    patch.object(Intention, 'assignment')
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    result = storyerror.unexpected_token_code()
    assert result == ErrorCodes.assignment_incomplete


def test_storyerror_unexpected_token_code_colon(patch, storyerror):
    patch.init(Intention)
    patch.object(Intention, 'assignment', return_value=False)
    patch.object(Intention, 'unnecessary_colon')
    assert storyerror.unexpected_token_code() == ErrorCodes.unnecessary_colon


def test_storyerror_unexpected_token_expected_block_after(patch, storyerror):
    patch.init(Intention)
    patch.object(storyerror, 'get_line')
    patch.object(Intention, 'assignment', return_value=False)
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    and_ = Token('and', 'and')
    storyerror.error = UnexpectedToken(token=and_, expected=['_INDENT'])
    assert storyerror.unexpected_token_code() == \
        ErrorCodes.block_expected_after


def test_storyerror_unexpected_characters_code(patch, call_count, storyerror):
    patch.init(Intention)
    patch.object(Intention, 'is_function', return_value=False)
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    patch.object(storyerror, 'get_line', return_value='x = $')
    storyerror.error.column = 5
    result = storyerror.unexpected_characters_code()
    Intention.__init__.assert_called_with(storyerror.get_line())
    call_count(Intention, ['is_function', 'unnecessary_colon'])
    assert result == ErrorCodes.invalid_character
    assert storyerror._format == {'character': '$'}


def test_storyerror_unexpected_characters_code_function(patch, storyerror):
    patch.init(Intention)
    patch.object(Intention, 'is_function')
    result = storyerror.unexpected_characters_code()
    assert result == ErrorCodes.function_misspell


def test_storyerror_unexpected_characters_code_colon(patch, storyerror):
    patch.init(Intention)
    patch.object(Intention, 'is_function', return_value=False)
    patch.object(Intention, 'unnecessary_colon')
    result = storyerror.unexpected_characters_code()
    assert result == ErrorCodes.unnecessary_colon


def test_storyerror_unexpected_characters_code_single_quotes(patch,
                                                             storyerror):
    patch.init(Intention)
    patch.object(Intention, 'is_function', return_value=False)
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    patch.object(StoryError, 'get_line', return_value="'string'")
    storyerror.error.column = 1
    result = storyerror.unexpected_characters_code()
    assert result == ErrorCodes.single_quotes


def test_storyerror_unexpected_characters_expected_block_before(patch,
                                                                storyerror):
    patch.init(Intention)
    patch.object(Intention, 'is_function', return_value=False)
    patch.object(StoryError, 'is_valid_name_start', return_value=True)
    patch.object(Intention, 'unnecessary_colon', return_value=False)
    storyerror.error = UnexpectedCharacters(seq='abc', lex_pos=0, line=0,
                                            column=0, allowed=None)
    result = storyerror.unexpected_characters_code()
    assert result == ErrorCodes.block_expected_before


@mark.parametrize('name_char', [
    'a', 'c', 'z', 'A', 'G', 'Z', '_',
])
def test_storyerror_is_valid_name_start(storyerror, name_char):
    assert storyerror.is_valid_name_start(name_char)


@mark.parametrize('name_char', [
    '.', '$', ':', '+', '/', '%', '-', '0', '5', '9'
])
def test_storyerror_is_invalid_name_start(storyerror, name_char):
    assert not storyerror.is_valid_name_start(name_char)


def test_storyerror_identify(storyerror):
    storyerror.error.error = 'none'
    assert storyerror.identify() == ErrorCodes.unidentified_error


@mark.parametrize('name', [
    'service_name', 'arguments_noservice', 'return_outside',
    'variables_backslash', 'variables_dash'
])
def test_storyerror_identify_codes(storyerror, error, name):
    error.error = name
    assert storyerror.identify() == getattr(ErrorCodes, name)


def test_storyerror_identify_unexpected_token(patch, storyerror):
    """
    Ensures that StoryError.identify can find the error code for unidentified
    token errors
    """
    patch.init(UnexpectedToken)
    patch.object(StoryError, 'unexpected_token_code')
    storyerror.error = UnexpectedToken('seq', 'lex', 0, 0)
    assert storyerror.identify() == storyerror.unexpected_token_code()


def test_storyerror_identify_unexpected_characters(patch, storyerror):
    patch.init(UnexpectedCharacters)
    patch.object(StoryError, 'unexpected_characters_code')
    storyerror.error = UnexpectedCharacters('seq', 'lex', 0, 0)
    assert storyerror.identify() == storyerror.unexpected_characters_code()


def test_storyerror_process(patch, storyerror):
    patch.object(StoryError, 'identify')
    storyerror.process()
    assert storyerror.error_tuple == storyerror.identify()


def test_storyerror_message(patch, storyerror):
    patch.many(StoryError,
               ['process', 'header', 'highlight', 'error_code', 'hint'])
    result = storyerror.message()
    assert storyerror.process.call_count == 1
    args = (storyerror.header(), storyerror.highlight(),
            storyerror.error_code(), storyerror.hint())
    assert result == '{}\n\n{}\n\n{}: {}'.format(*args)


def test_story_storyerror_short_message(patch, storyerror):
    patch.many(StoryError, ['process', 'error_code', 'hint'])
    result = storyerror.short_message()
    assert result == f'{storyerror.error_code()}: {storyerror.hint()}'


def test_storyerror_echo(patch, storyerror):
    """
    Ensures StoryError.echo prints StoryError.message
    """
    patch.object(click, 'echo')
    patch.object(StoryError, 'message')
    storyerror.echo()
    click.echo.assert_called_with(StoryError.message())


def test_storyerror_create_error(patch):
    """
    Ensures that Errors without Tokens can be created
    """
    patch.init(StoryError)
    patch.init(CompilerError)
    error = StoryError.create_error('error_code')
    assert isinstance(error, StoryError)
    CompilerError.__init__.assert_called_with('error_code', format_args={})
    assert isinstance(StoryError.__init__.call_args[0][0], CompilerError)
    assert StoryError.__init__.call_args[0][1] is None


def test_storyerror_create_error_kwargs(patch):
    """
    Ensures that Errors without Tokens can be created and kwargs are passed on.
    """
    patch.init(StoryError)
    patch.init(CompilerError)
    error = StoryError.create_error('error_code', a=0)
    assert isinstance(error, StoryError)
    CompilerError.__init__.assert_called_with('error_code',
                                              format_args={'a': 0})
    assert isinstance(StoryError.__init__.call_args[0][0], CompilerError)
    assert StoryError.__init__.call_args[0][1] is None


def test_storyerror_internal(patch):
    """
    Ensures that an internal error gets properly constructed
    """
    patch.init(StoryError)
    e = Exception('.ICE.')
    error = StoryError.internal_error(e)
    assert isinstance(error, StoryError)
    StoryError.__init__.assert_called_with(e, story=None)


def test_storyerror_internal_message(patch):
    """
    Ensures that the internal error message gets properly built
    """
    error = Exception('.ICE.')
    expected = (
        'Internal error occured: .ICE.\n'
        'Please report at https://github.com/storyscript/storyscript/issues')
    assert StoryError._internal_error(error) == expected

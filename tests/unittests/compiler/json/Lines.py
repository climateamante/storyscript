# -*- coding: utf-8 -*-
from pytest import fixture, mark, raises

from storyscript.compiler.json import Lines
from storyscript.exceptions import StorySyntaxError


@fixture
def lines(magic):
    story = magic()
    return Lines(story=story)


def test_lines_init(lines):
    assert lines.lines == {}
    assert lines.variables == []
    assert lines.services == []
    assert lines.functions == {}
    assert lines.output_scopes == {}


def test_lines_first(patch, lines):
    lines.lines = {'1': '1'}
    lines._lines = ['1']
    assert lines.first() == '1'


def test_lines_first_none(lines):
    assert lines.first() is None


def test_lines_last(patch, lines):
    lines.lines = {'1': '1'}
    lines._lines = ['1']
    assert lines.last() == '1'


def test_lines_last_no_lines(lines):
    assert lines.last() is None


def test_lines_set_name(patch, lines):
    d = {}
    patch.object(Lines, 'last', return_value=d)
    lines.set_name('name')
    assert d['name'] == 'name'


def test_lines_set_next(patch, lines):
    lines.lines['1'] = {}
    patch.object(Lines, 'last', return_value=lines.lines['1'])
    lines.set_next('2')
    assert lines.lines['1']['next'] == '2'


@mark.parametrize('method', ['if', 'elif', 'try', 'catch'])
def test_lines_set_exit(patch, lines, method):
    lines.finished_scopes = ['1']
    lines.lines = {'1': {}, '2': {'method': method}}
    lines._lines = ['1', '2']
    lines.set_exit('3')
    assert lines.lines['2']['exit'] == '3'
    assert lines.finished_scopes == []


def test_lines_set_scope(patch, lines):
    lines.set_scope('2', '1')
    assert lines.output_scopes['2'] == {'parent': '1', 'output': []}


def test_lines_set_scope_output(lines):
    lines.set_scope('2', '1', output=['x'])
    assert lines.output_scopes['2']['output'] == ['x']


def test_lines_finish_scope(lines):
    lines.finish_scope('1')
    assert lines.finished_scopes == ['1']
    lines.finish_scope('2')
    assert lines.finished_scopes == ['1', '2']


def test_lines_is_output(lines):
    lines.output_scopes = {'1': {'parent': None, 'output': ['service']}}
    assert lines.is_output('1', 'service') is True


def test_lines_is_output_from_parent(lines):
    lines.output_scopes = {
        '2': {'parent': '1', 'output': []},
        '1': {'output': ['service']}
    }
    assert lines.is_output('2', 'service') is True


def test_lines_is_output_false(lines):
    assert lines.is_output('1', 'service') is False


def test_lines_make(lines):
    expected = {'1': {'method': 'method', 'ln': '1', 'output': None,
                      'name': None,
                      'function': None, 'service': None, 'command': None,
                      'enter': None, 'exit': None, 'args': None,
                      'parent': None, 'src': lines.story.line()}}
    lines.make('method', '1')
    lines.story.line.assert_called_with('1')
    assert lines.lines == expected


@mark.parametrize('keywords', ['service', 'command', 'function', 'output',
                               'args', 'enter', 'exit', 'parent', 'name'])
def test_lines_make_keywords(lines, keywords):
    lines.make('method', '1', **{keywords: keywords})
    assert lines.lines['1'][keywords] == keywords


def test_lines_check_service_name(lines):
    """
    Asserts that these service names are valid and don't throw an Error
    """
    lines.check_service_name('alpine', '1')
    lines.check_service_name('_alpine', '1')


def test_lines_check_service_name_error(patch, lines):
    patch.init(StorySyntaxError)
    with raises(StorySyntaxError):
        lines.check_service_name('wrong.name', '1')
    StorySyntaxError.__init__.assert_called_with('service_name')


def test_lines_append(patch, lines):
    patch.many(Lines, ['make', 'set_next'])
    lines.append('method', 'line', extras='whatever')
    lines.set_next.assert_called_with('line')
    lines.make.assert_called_with('method', 'line', extras='whatever')


def test_lines_append_function(patch, lines):
    """
    Ensures that a function is registered properly.
    """
    patch.many(Lines, ['make', 'set_next'])
    lines.append('function', 'line', function='function')
    assert lines.functions['function'] == 'line'


def test_compiler_append_service(patch, lines):
    """
    Ensures that a service is registed in Compiler.services
    """
    patch.many(Lines, ['make', 'set_next', 'is_output', 'check_service_name'])
    Lines.is_output.return_value = False
    lines.append('execute', 'line', service='service', parent='parent')
    Lines.check_service_name.assert_called_with('service', 'line')
    lines.is_output.assert_called_with('parent', 'service')
    assert lines.services[0] == 'service'


def test_compiler_append_function_call(patch, lines):
    """
    Ensures that a function is registed in Compiler.services
    """
    patch.many(Lines, ['make', 'set_next', 'is_output', 'check_service_name'])
    Lines.is_output.return_value = False
    lines.append('call', 'line', service='my_function', parent='parent')
    lines.is_output.assert_not_called()
    assert lines.services == []


def test_lines_append_service_block_output(patch, lines):
    """
    Ensures that a service is not registered if the current service block
    has defined it as output
    """
    patch.many(Lines, ['make', 'set_next', 'is_output', 'check_service_name'])
    lines.outputs = {'line': ['service']}
    lines.append('execute', 'line', service='service', parent='parent')
    assert lines.services == []


def test_lines_append_function_call(patch, lines):
    """
    Ensures that a function call is registered properly.
    """
    patch.many(Lines, ['make', 'set_next', 'check_service_name'])
    lines.functions['function'] = 1
    lines.append('call', 'line', service='function')
    lines.make.assert_called_with('call', 'line', service='function')


def test_lines_append_scope(patch, lines):
    """
    Ensures that 'exit' is set properly after a scope was left.
    """
    patch.many(Lines, ['make', 'set_next'])
    lines.finished_scopes = ['1']
    lines.lines['1'] = {}
    lines.append('method', 'line', extras='whatever')
    lines.set_next.assert_called_with('line')
    lines.make.assert_called_with('method', 'line', extras='whatever')
    assert lines.lines['1']['exit'] == 'line'


def test_lines_execute(patch, lines):
    patch.object(Lines, 'append')
    lines.execute('line', 'service', 'command', 'args', 'output', 'enter',
                  'parent')
    kwargs = {'service': 'service', 'command': 'command', 'args': 'args',
              'output': 'output', 'enter': 'enter', 'parent': 'parent'}
    Lines.append.assert_called_with('execute', 'line', **kwargs)


def test_compiler_get_services(lines):
    lines.services = ['one', 'one']
    assert lines.get_services() == ['one']


def test_lines_is_variable_defined(patch, lines):
    """
    Ensures that the check for previously seen variables works
    """
    lines.variables = [['one', 'two'], ['three']]
    assert lines.is_variable_defined('one')
    assert lines.is_variable_defined('two')
    assert lines.is_variable_defined('three')
    assert not lines.is_variable_defined('four')

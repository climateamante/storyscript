# -*- coding: utf-8 -*-
from lark import Transformer as LarkTransformer
from lark.lexer import Token

from pytest import fixture, mark, raises

from storyscript.exceptions import StorySyntaxError
from storyscript.parser import Transformer, Tree


@fixture
def syntax_error(patch):
    patch.init(StorySyntaxError)
    return StorySyntaxError.__init__


def test_transformer():
    keywords = ['function', 'if', 'else', 'foreach', 'return', 'returns',
                'try', 'catch', 'finally', 'when', 'as', 'while',
                'throw', 'null']
    future_keywords = [
        'async', 'story', 'assert', 'called', 'mock', 'class', 'extends',
        'implements', 'interface', 'type', 'public', 'private', 'protected',
        'const', 'immutable', 'let', 'var', 'auto', 'immutable', 'switch',
        'module', 'package', 'final', 'this', 'self', 'case', 'abstract',
        'static', 'none', 'await', 'service', 'in', 'has', 'not', 'is', 'inf',
        'nan', 'unknown', 'import'
    ]
    assert Transformer.reserved_keywords == keywords
    assert Transformer.future_reserved_keywords == future_keywords
    assert issubclass(Transformer, LarkTransformer)


@mark.parametrize('keyword', [
    'function', 'if', 'else', 'foreach', 'return', 'returns', 'try', 'catch',
    'finally', 'when', 'as', 'while', 'throw', 'null'
])
def test_transformer_is_keyword(syntax_error, keyword):
    token = Token('any', keyword)
    with raises(StorySyntaxError):
        Transformer.is_keyword(token)
    name = 'reserved_keyword'
    format = {'keyword': keyword}
    syntax_error.assert_called_with(name, token=token, format_args=format)


@mark.parametrize('keyword', [
    'async', 'story', 'mock', 'assert', 'called', 'mock'
])
def test_transformer_is_keyword_future(syntax_error, keyword):
    token = Token('any', keyword)
    with raises(StorySyntaxError):
        Transformer.is_keyword(token)
    name = 'future_reserved_keyword'
    format = {'keyword': keyword}
    syntax_error.assert_called_with(name, token=token, format_args=format)


def test_transformer_assignment(magic):
    matches = [magic(), magic()]
    assert Transformer.assignment(matches) == Tree('assignment', matches)


def test_transformer_command(patch, magic):
    patch.object(Transformer, 'is_keyword')
    result = Transformer.command(['matches'])
    Transformer.is_keyword.assert_called_with('matches')
    assert result == Tree('command', ['matches'])


def test_transformer_path(patch):
    patch.object(Transformer, 'is_keyword')
    result = Transformer.path(['matches'])
    Transformer.is_keyword.assert_called_with('matches')
    assert result == Tree('path', ['matches'])


def test_transformer_service_block():
    """
    Ensures service_block nodes are transformed correctly
    """
    assert Transformer.service_block(['a']) == Tree('service_block', ['a'])


def test_transformer_service_block_when(patch, tree):
    """
    Ensures service_block nodes with a when block are transformed correctly
    """
    tree.block.rules = None
    matches = ['service_block', tree]
    result = Transformer.service_block(matches)
    assert result == Tree('service_block', matches)


def test_transformer_service_block_indented_args(tree, magic, patch):
    """
    Ensures service_block with indented arguments are transformed correctly.
    """
    patch.object(Transformer, 'filter_nested_block', return_value=['argument'])
    block = magic()
    matches = [block, tree]
    result = Transformer.service_block(matches)
    block.service_fragment.children.append.assert_called_with('argument')
    assert result == Tree('service_block', [block])


def test_transformer_when_block(patch, tree):
    """
    Ensures when_block nodes are transformed correctly
    """
    tree.data = 'when_service'
    tree.output = None
    tree.children = [Token('NAME', '.name.')]
    tree.child_token.return_value = Token('NAME', '.child.', line=42)
    tree.path.child_token.return_value = Token('NAME', '.path.')
    result = Transformer.when_block([tree, 'block'])
    assert result == Tree('concise_when_block', [
        Token('NAME', '.child.'),
        Token('NAME', '.path.'),
        Tree('when_block', [
            tree,
            'block'
        ])
    ])


def test_transformer_when_block_no_command(patch, tree):
    """
    Ensures when_block nodes without command are transformed correctly
    """
    patch.object(Transformer, 'argument_shorthand')
    tree.data = 'when_service'
    tree.output = None
    tree.children = [Token('NAME', '.name.')]
    tree.service_fragment.command = None
    result = Transformer.when_block([tree, 'block'])
    assert result == Tree('when_block', [
        Tree('service', [
            Tree('path', [tree.child_token()]),
            tree.service_fragment,
        ]),
        'block',
    ])


@mark.parametrize('rule', ['start', 'line', 'block', 'statement'])
def test_transformer_rules(rule):
    result = getattr(Transformer(), rule)(['matches'])
    assert isinstance(result, Tree)
    assert result.data == rule
    assert result.children == ['matches']


def test_transformer_absolute_expression(patch, tree):
    """
    Ensures absolute_expression are untouched when they don't contain
    just a path
    """
    patch.object(Tree, 'follow_node_chain')
    tree.follow_node_chain.return_value = None
    result = Transformer.absolute_expression([tree])
    assert result == Tree('absolute_expression', [tree])
    result = Transformer.absolute_expression([tree, tree])
    assert result == Tree('absolute_expression', [tree, tree])


def test_transformer_absolute_expression_zero(patch, tree, magic):
    """
    Ensures absolute_expression are untouched when they don't contain
    just a path
    """
    patch.object(Tree, 'follow_node_chain')
    m = magic()
    tree.follow_node_chain.return_value = m
    result = Transformer.absolute_expression([tree])
    expected = Tree('service_block', [
        Tree('service', [m, Tree('service_fragment', [])])
    ])
    assert result == expected


def test_transformer_function_block_empty(patch, tree, magic):
    """
    Ensures that indented arguments are added back to the their original node
    """
    assert Transformer.function_block([]) == Tree('function_block', [])
    assert Transformer.function_block([0]) == Tree('function_block', [0])
    m = magic()
    m.data = 'some_block'
    assert Transformer.function_block([m]) == Tree('function_block', [m])
    assert Transformer.function_block([m, m]) == Tree('function_block', [m, m])


def test_transformer_function_block(patch, tree, magic):
    """
    Ensures that indented arguments are added back to the their original node
    """
    function_block = magic()
    m = magic()
    block = magic()
    m.data = 'indented_typed_arguments'
    m.find_data.return_value = ['.indented.node.']
    r = Transformer.function_block([function_block, m, block])
    m.find_data.assert_called_with('typed_argument')
    function_block.children.append.assert_called_with('.indented.node.')
    assert r.data == 'function_block'
    assert r.children == [
        function_block,
        Tree('nested_block', [block])
    ]


def test_multi_line_string_single_line():
    assert Transformer.multi_line_string('aa') == 'aa'


def test_multi_line_string_single_line_no_strip():
    assert Transformer.multi_line_string('  aa') == '  aa'
    assert Transformer.multi_line_string('\taa') == '\taa'


def test_multi_line_string_multi_line():
    assert Transformer.multi_line_string('aa\nbb\ncc') == 'aa bb cc'


def test_multi_line_string_multi_line_empty_line():
    assert Transformer.multi_line_string('aa\n\n\ncc') == 'aa cc'


def test_multi_line_string_multi_line_indented():
    assert Transformer.multi_line_string('aa\n\tbb\n  cc') == 'aa bb cc'


def test_multi_line_string_multi_line_backslash():
    text = 'aa\\\n\tbb\\\n  cc'
    assert Transformer.multi_line_string(text) == 'aabbcc'


def test_multi_line_string_multi_line_start_backslash():
    assert Transformer.multi_line_string('\\\n  b') == 'b'


def test_multi_line_string_multi_line_start_multiple_backslashs():
    assert Transformer.multi_line_string('\\\n\\\n  b') == 'b'

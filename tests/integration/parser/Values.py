# -*- coding: utf-8 -*-
from lark.lexer import Token
from lark.tree import Tree

from storyscript.Story import _parser


def parse(source):
    """
    Don't regenerate the parser on every call
    """
    return _parser().parse(source)


def get_entity(obj):
    """
    Returns the entity for an expression
    """
    return obj.or_expression.and_expression.cmp_expression.arith_expression. \
        mul_expression.unary_expression.pow_expression.primary_expression. \
        entity


def test_values_true():
    result = parse('true\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.boolean.child(0) == Token('TRUE', 'true')


def test_values_false():
    result = parse('false\n')
    token = Token('FALSE', 'false')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.boolean.child(0) == token


def test_values_null():
    result = parse('null\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.void.child(0) == Token('NULL', 'null')


def test_values_int():
    """
    Ensures that parsing an int produces the expected tree
    """
    result = parse('3\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.number.child(0) == Token('INT', 3)


def test_values_int_negative():
    """
    Ensures that parsing a negative int produces the expected tree
    """
    result = parse('-3\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.number.child(0) == Token('INT', '-3')


def test_values_float():
    """
    Ensures that parsing a float produces the expected tree
    """
    result = parse('3.14\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.number.child(0) == Token('FLOAT', 3.14)


def test_values_float_negative():
    """
    Ensures that parsing a negative float produces the expected tree
    """
    result = parse('-3.14\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.number.child(0) == Token('FLOAT', '-3.14')


def test_values_double_quoted_string():
    result = parse('"red"\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    expected = entity.values.string.child(0)
    assert expected == Token('DOUBLE_QUOTED', '"red"')


def test_values_list():
    result = parse('[3,4]\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    list = entity.values.list
    c1 = get_entity(list.child(1).expression)
    c2 = get_entity(list.child(3).expression)
    assert c1.values.number.child(0) == Token('INT', 3)
    assert c2.values.number.child(0) == Token('INT', 4)


def test_values_list_empty():
    result = parse('[]\n')
    expected = Tree('list', [Token('_OSB', '['), Token('_CSB', ']')])
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.list == expected


def test_values_object():
    result = parse('{"color":"red","shape":1}\n')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    values = entity.values
    key_value = values.map.key_value
    assert key_value.string.child(0) == Token('DOUBLE_QUOTED', '"color"')
    entity = get_entity(key_value.child(1).expression)
    assert entity.values.string.child(0) == Token('DOUBLE_QUOTED', '"red"')


def test_values_regular_expression():
    """
    Ensures regular expressions are parsed correctly
    """
    result = parse('/^foo/')
    token = Token('REGEXP', '/^foo/')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.regular_expression.child(0) == token


def test_values_regular_expression_flags():
    """
    Ensures regular expressions with flags are parsed correctly
    """
    result = parse('/^foo/i')
    expression = result.block.rules.absolute_expression.expression
    entity = get_entity(expression)
    assert entity.values.regular_expression.child(0).value == '/^foo/i'

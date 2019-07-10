# -*- coding: utf-8 -*-
from lark.lexer import Token

from pytest import mark

from storyscript.Story import _parser
from storyscript.compiler.lowering.Lowering import Lowering
from storyscript.parser import Tree


def parse(source, lower=False):
    """
    Don't regenerate the parser on every call
    """
    tree = _parser().parse(source, allow_single_quotes=False)
    if not lower:
        return tree
    return Lowering(parser=tree.parser, features={}).process(tree)


def get_entity(obj):
    """
    Returns the entity for an expression
    """
    if obj.mul_expression is not None:
        obj = obj.mul_expression
    return obj.unary_expression.pow_expression.primary_expression.entity


def arith_exp(exp):
    """
    Returns the binary expression for an expression
    """
    return exp.expression.or_expression.and_expression.cmp_expression. \
        arith_expression


def test_parser_sum():
    result = parse('3 + 4\n')
    ar_exp = arith_exp(result.block.rules.absolute_expression)
    lhs = get_entity(ar_exp.child(0)).values.number
    assert lhs.child(0) == Token('INT', 3)
    op = ar_exp.child(1)
    assert op.data == 'arith_operator'
    assert op.child(0) == Token('PLUS', '+')
    rhs = get_entity(ar_exp.child(2)).values.number
    assert rhs.child(0) == Token('INT', 4)


def test_parser_list_path():
    """
    Ensures that paths in lists can be parsed.
    """
    result = parse('x = 0\n[3, x]\n')
    expression = result.child(1).rules.absolute_expression
    entity = get_entity(arith_exp(expression))
    list = arith_exp(Tree('absolute_expression',
                          [entity.values.list.child(3).expression]))
    x = get_entity(list)
    assert x.path.child(0) == Token('NAME', 'x')


@mark.parametrize('code, token', [
    ('x="hello"\n', Token('DOUBLE_QUOTED', '"hello"')),
    ('x = "hello"\n', Token('DOUBLE_QUOTED', '"hello"')),
    ('x=3\n', Token('INT', 3)),
    ('x = 3\n', Token('INT', 3))
])
def test_parser_assignment(code, token):
    result = parse(code)
    assignment = result.block.rules.assignment
    assert assignment.path.child(0) == Token('NAME', 'x')
    assert assignment.assignment_fragment.child(0) == Token('EQUALS', '=')
    expression = assignment.assignment_fragment.base_expression
    entity = get_entity(arith_exp(expression))
    assert entity.values.child(0).child(0) == token


def test_parser_assignment_path():
    result = parse('rainbow.colors[0]="blue"\n')
    path = result.block.rules.assignment.path
    assert path.child(0) == Token('NAME', 'rainbow')
    assert path.path_fragment.child(0) == Token('NAME', 'colors')
    assert path.child(2).child(0).data == 'number'
    assert path.child(2).child(0).child(0) == Token('INT', 0)


def test_parser_assignment_indented_arguments():
    """
    Ensures that assignments to a service with indented arguments are parsed
    correctly
    """
    result = parse('x = alpine echo\n\tmessage:"hello"')
    exp = result.child(1).indented_arguments.arguments.expression
    values = get_entity(arith_exp(Tree('an_exp', [exp]))).values
    assert values.string.child(0) == Token('DOUBLE_QUOTED', '"hello"')


def test_parser_foreach_block():
    result = parse('foreach items as one, two\n\tx=3\n', lower=True)
    block = result.block.foreach_block
    foreach = block.foreach_statement
    exp = arith_exp(foreach.base_expression)
    entity = get_entity(exp)
    assert entity.path.child(0) == Token('NAME', 'items')
    assert foreach.output.child(0) == Token('NAME', 'one')
    assert foreach.output.child(1) == Token('NAME', 'two')
    assert block.nested_block.data == 'nested_block'


def test_parser_while_block():
    result = parse('while cond\n\tx=3\n')
    block = result.block.while_block
    exp = arith_exp(block.while_statement.base_expression)
    entity = get_entity(exp)
    assert entity.path.child(0) == Token('NAME', 'cond')
    assert block.nested_block.data == 'nested_block'


def test_parser_service():
    result = parse('org/container-name command\n')
    service = result.block.service_block.service
    assert service.path.child(0) == 'org/container-name'
    assert service.service_fragment.command.child(0) == 'command'


def test_parser_service_arguments():
    result = parse('my_service command key:"value"\n')
    args = result.block.service_block.service.service_fragment.arguments
    assert args.child(0) == Token('NAME', 'key')
    entity = get_entity(arith_exp(Tree('an_exp', [args.expression])))
    assert entity.values.string.child(0) == Token('DOUBLE_QUOTED', '"value"')


def test_parser_service_output():
    result = parse('container command as request, response\n')
    node = result.block.service_block.service.service_fragment.output
    assert node.child(0) == Token('NAME', 'request')
    assert node.child(1) == Token('NAME', 'response')


def test_parser_if_block():
    result = parse('if expr\n\tx=3\n')
    if_block = result.block.if_block
    ar_exp = arith_exp(if_block.if_statement.base_expression)
    entity = get_entity(ar_exp)
    path = entity.path
    assignment = if_block.nested_block.block.rules.assignment
    assert path.child(0) == Token('NAME', 'expr')
    assert assignment.path.child(0) == Token('NAME', 'x')


def test_parser_if_block_nested():
    result = parse('if expr\n\tif things\n\t\tx=3\n')
    if_block = result.block.if_block.nested_block.block.if_block
    ar_exp = arith_exp(if_block.if_statement.base_expression)
    entity = get_entity(ar_exp)
    path = entity.path
    assignment = if_block.nested_block.block.rules.assignment
    assert path.child(0) == Token('NAME', 'things')
    assert assignment.path.child(0) == Token('NAME', 'x')


def test_parser_if_block_else():
    result = parse('if expr\n\tx=3\nelse\n\tx=4\n')
    node = result.block.if_block.else_block.nested_block.block.rules
    assert node.assignment.path.child(0) == Token('NAME', 'x')


def test_parser_if_block_elseif():
    result = parse('if expr\n\tx=3\nelse if magic\n\tx=4\n')
    node = result.block.if_block.elseif_block.nested_block.block.rules
    assert node.assignment.path.child(0) == Token('NAME', 'x')


def test_parser_function():
    result = parse('function test\n\tx = 3\n')
    node = result.block.function_block
    path = node.nested_block.block.rules.assignment.path
    assert node.function_statement.child(1) == Token('NAME', 'test')
    assert path.child(0) == Token('NAME', 'x')


def test_parser_function_arguments():
    result = parse('function test n:int\n\tx = 3\n')
    typed_argument = result.block.function_block.find('typed_argument')[0]
    assert typed_argument.child(0) == Token('NAME', 'n')
    assert typed_argument.types.base_type.child(0) == Token('INT_TYPE', 'int')


def test_parser_function_output():
    result = parse('function test n:string returns int\n\tx = 1\n')
    statement = result.block.function_block.function_statement
    assert statement.function_output.types.base_type.child(0) == \
        Token('INT_TYPE', 'int')


def test_parser_try():
    result = parse('try\n\tx=0')
    try_block = result.block.try_block
    assert try_block.try_statement.child(0) == Token('TRY', 'try')
    path = try_block.nested_block.block.rules.assignment.path
    assert path.child(0) == Token('NAME', 'x')


def test_parser_try_catch():
    result = parse('try\n\tx=0\ncatch as error\n\tx=1')
    catch_block = result.block.try_block.catch_block
    assert catch_block.catch_statement.child(0) == Token('NAME', 'error')
    path = catch_block.nested_block.block.rules.assignment.path
    assert path.child(0) == Token('NAME', 'x')


def test_parser_try_finally():
    result = parse('try\n\tx=0\nfinally\n\tx=1')
    finally_block = result.block.try_block.finally_block
    token = Token('FINALLY', 'finally')
    assert finally_block.finally_statement.child(0) == token
    path = finally_block.nested_block.block.rules.assignment.path
    assert path.child(0) == Token('NAME', 'x')


def test_parser_try_throw():
    result = parse('try\n\tx=0\ncatch as error\n\tthrow')
    nested_block = result.block.try_block.catch_block.nested_block
    assert nested_block.block.rules.throw_statement.child(0) == 'throw'


def test_parser_try_throw_error():
    result = parse('try\n\tx=0\ncatch as error\n\tthrow error')
    nested_block = result.block.try_block.catch_block.nested_block
    throw_statement = nested_block.block.rules.throw_statement
    assert throw_statement.child(0) == 'throw'
    assert throw_statement.entity.path.child(0) == Token('NAME', 'error')


def test_parser_try_throw_error_message():
    result = parse('try\n\tx=0\ncatch as error\n\tthrow "error"')
    nested_block = result.block.try_block.catch_block.nested_block
    throw_statement = nested_block.block.rules.throw_statement
    print(throw_statement.pretty())
    assert throw_statement.child(0) == 'throw'
    token = Token('DOUBLE_QUOTED', '"error"')
    assert throw_statement.entity.values.string.child(0) == token


@mark.parametrize('number', ['+10', '-10'])
def test_parser_number_int(number):
    result = parse(number)
    ar_exp = arith_exp(result.block.rules.absolute_expression)
    entity = get_entity(ar_exp)
    f = entity.values.number
    assert f.child(0) == Token('INT', number)


@mark.parametrize('number', ['+10.0', '-10.0'])
def test_parser_number_float(number):
    result = parse(number)
    ar_exp = arith_exp(result.block.rules.absolute_expression)
    entity = get_entity(ar_exp)
    f = entity.values.number
    assert f.child(0) == Token('FLOAT', number)


def test_parser_string_double_quoted():
    result = parse(r'a = "b\n.\\.\".c"')
    result = result.block.rules.assignment.assignment_fragment
    result = result.base_expression
    ar_exp = arith_exp(result)
    lhs = get_entity(ar_exp.child(0)).values.string.child(0)
    assert lhs == r'"b\n.\\.\".c"'

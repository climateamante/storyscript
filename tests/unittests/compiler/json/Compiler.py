# -*- coding: utf-8 -*-
from lark.lexer import Token

from pytest import fixture, mark, raises

from storyscript.Version import version
from storyscript.compiler.json import JSONCompiler, Lines, Objects
from storyscript.exceptions import StorySyntaxError
from storyscript.parser import Tree


@fixture
def lines(magic):
    return magic()


@fixture
def compiler(patch, lines):
    patch.init(Lines)
    compiler = JSONCompiler(story=None)
    compiler.lines = lines
    return compiler


def test_compiler_init(patch):
    patch.init(Lines)
    compiler = JSONCompiler(story=None)
    assert isinstance(compiler.lines, Lines)


def test_compiler_output(tree):
    tree.children = [Token('token', 'output')]
    result = JSONCompiler.output(tree)
    assert result == ['output']


def test_compiler_output_none():
    assert JSONCompiler.output(None) == []


def test_compiler_extract_values(patch, tree):
    patch.object(Objects, 'entity')
    tree.expression = None
    result = JSONCompiler(story=None).extract_values(tree)
    tree.child.assert_called_with(1)
    Objects.entity.assert_called_with(tree.child())
    assert result == [Objects.entity()]


def test_compiler_extract_values_expression(patch, tree):
    patch.object(Objects, 'expression')
    tree.expression.mutation = None
    result = JSONCompiler(story=None).extract_values(tree)
    Objects.expression.assert_called_with(tree.expression)
    assert result == [Objects.expression()]


def test_compiler_extract_values_mutation(patch, tree):
    patch.many(Objects, ['values', 'mutation_fragment'])
    result = JSONCompiler(story=None).extract_values(tree)
    Objects.values.assert_called_with(tree.expression.values)
    Objects.mutation_fragment.assert_called_with(tree.expression.mutation)
    assert result == [Objects.values(), Objects.mutation_fragment()]


def test_compiler_chained_mutations(patch, magic, tree):
    patch.object(Objects, 'mutation_fragment')
    mutation = magic()
    tree.find_data.return_value = [mutation]
    result = JSONCompiler(story=None).chained_mutations(tree)
    Objects.mutation_fragment.assert_called_with(mutation.mutation_fragment)
    assert result == [Objects.mutation_fragment()]


def test_compiler_function_output(patch, compiler, tree):
    patch.object(JSONCompiler, 'output')
    patch.object(Objects, 'types')
    result = compiler.function_output(tree)
    Objects.types.assert_called_with(tree.function_output.types)
    assert result == [Objects.types()['types']]


def test_compiler_absolute_expression(patch, compiler, lines, tree):
    patch.object(Objects, 'expression')
    compiler.absolute_expression(tree, '1')
    Objects.expression.assert_called_with(tree.expression)


def test_compiler_assignment_unary(patch, compiler, lines, tree):
    """
    Ensures a line like "x = value" is compiled correctly
    """
    patch.many(Objects, ['names', 'entity', 'expression'])
    af = tree.assignment_fragment.base_expression
    af.service = None
    af.mutation = None
    lines.lines = {lines.last(): {'method': None}}
    compiler.assignment(tree, '1')
    Objects.names.assert_called_with(tree.path)
    Objects.expression.assert_called_with(af.expression)
    kwargs = {'args': [Objects.expression()],
              'parent': '1'}
    lines.append.assert_called_with('expression', tree.line(), **kwargs)
    lines.set_name.assert_called_with(Objects.names())


def test_compiler_assignment_service(patch, compiler, lines, tree):
    patch.object(Objects, 'names')
    patch.object(JSONCompiler, 'service')
    lines.is_variable_defined.return_value = False
    compiler.assignment(tree, '1')
    service = tree.assignment_fragment.base_expression.service
    JSONCompiler.service.assert_called_with(service, None, '1')
    lines.set_name.assert_called_with(Objects.names())


def test_compiler_assignment_mutation(patch, compiler, lines, tree):
    """
    Ensures that assignments to mutations are compiled correctly.
    """
    patch.object(Objects, 'names', return_value='name')
    patch.object(JSONCompiler, 'mutation_block')
    af = tree.assignment_fragment.base_expression
    af.service = None
    compiler.assignment(tree, '1')
    JSONCompiler.mutation_block.assert_called_with(af.mutation, '1')
    lines.set_name.assert_called_with('name')


def test_compiler_assignment_expression(patch, compiler, lines, tree):
    patch.object(Objects, 'names', return_value='name')
    patch.object(Objects, 'expression')
    af = tree.assignment_fragment.base_expression
    af.service = None
    af.mutation = None
    compiler.assignment(tree, '1')
    Objects.expression.assert_called_with(af.expression)
    lines.set_name.assert_called_with('name')


def test_compiler_assignment_function_call(patch, compiler, lines, tree):
    """
    Ensures that assignments with function calls are compiled correctly.
    """
    patch.object(Objects, 'names', return_value='name')
    patch.object(JSONCompiler, 'call_expression')
    af = tree.assignment_fragment.base_expression
    af.service = None
    af.mutation = None
    af.expression = None
    compiler.assignment(tree, '1')
    JSONCompiler.call_expression.assert_called_with(af.call_expression, '1')
    lines.set_name.assert_called_with('name')


def test_compiler_arguments(patch, compiler, lines, tree):
    patch.object(Objects, 'arguments')
    lines.lines = {'1': {'method': 'execute', 'args': ['args']}}
    lines.last.return_value = lines.lines['1']
    compiler.arguments(tree, '0')
    Objects.arguments.assert_called_with(tree)
    assert lines.lines['1']['args'] == ['args'] + Objects.arguments()


def test_compiler_arguments_fist_line(patch, compiler, lines, tree):
    """
    Ensures that if this is the first line, an error is raised.
    """
    patch.init(StorySyntaxError)
    lines.last.return_value = None
    with raises(StorySyntaxError):
        compiler.arguments(tree, '0')
    error = 'arguments_noservice'
    StorySyntaxError.__init__.assert_called_with(error, tree=tree)


def test_compiler_arguments_not_execute(patch, compiler, lines, tree):
    """
    Ensures that if the previous line is not an execute, an error is raised.
    """
    patch.init(StorySyntaxError)
    patch.object(Objects, 'arguments')
    lines.lines = {'1': {'method': 'whatever'}}
    lines.last.return_value = lines.lines['1']
    with raises(StorySyntaxError):
        compiler.arguments(tree, '0')
    error = 'arguments_noservice'
    StorySyntaxError.__init__.assert_called_with(error, tree=tree)


def test_compiler_call_expression(patch, compiler, lines, tree):
    """
    Ensures that function call expression can be compiled
    """
    patch.many(Objects, ['arguments', 'names'])
    Objects.names.return_values = ['.path.']
    compiler.call_expression(tree, 'parent')
    Objects.arguments.assert_called_with(tree)
    lines.append.assert_called_with('call', tree.line(),
                                    function=tree.path.extract_path(),
                                    args=Objects.arguments(), parent='parent',
                                    output=None)


def test_compiler_call_expression_no_inline(patch, compiler, tree):
    """
    Ensures that function call expression checks its arguments correctly
    """
    patch.object(Objects, 'arguments')
    tree.expect.side_effect = Exception('.')
    tree.path.inline_expression = True
    with raises(Exception):
        compiler.call_expression(tree, 'parent')
    tree.expect.assert_called_with(False, 'function_call_no_inline_expression')


def test_compiler_call_expression_no_invalid_path(patch, compiler, tree):
    """
    Ensures that function call expression checks its arguments correctly
    """
    patch.many(Objects, ['arguments', 'names'])
    error_code = None
    args = None

    def expect(cond, _error_code, **_args):
        nonlocal error_code, args
        if not cond:
            assert args is None
            args = _args
            error_code = _error_code

    tree.expect = expect
    tree.path.inline_expression = None
    Objects.names.return_value = ['a', 'b']
    name = tree.path.extract_path()
    compiler.lines.functions = [name]

    compiler.call_expression(tree, 'parent')
    assert error_code == 'function_call_invalid_path'
    assert args == {'name': 'a.b'}


def test_compiler_service(patch, compiler, lines, tree):
    """
    Ensures that service trees can be compiled
    """
    patch.object(Objects, 'arguments')
    patch.object(JSONCompiler, 'output')
    tree.node.return_value = None
    tree.data = 'service'
    compiler.service(tree, None, 'parent')
    line = tree.line()
    service = tree.path.extract_path()
    command = tree.service_fragment.command.child()
    Objects.arguments.assert_called_with(tree.service_fragment)
    JSONCompiler.output.assert_called_with(tree.service_fragment.output)
    lines.execute.assert_called_with(line, service, command,
                                     Objects.arguments(), compiler.output(),
                                     None, 'parent')


def test_compiler_service_command(patch, compiler, lines, tree):
    patch.object(Objects, 'arguments')
    patch.object(JSONCompiler, 'output')
    tree.data = 'service'
    compiler.service(tree, None, 'parent')
    line = tree.line()
    service = tree.path.extract_path()
    command = tree.service_fragment.command.child()
    lines.set_scope.assert_called_with(line, 'parent', compiler.output())
    lines.execute.assert_called_with(line, service, command,
                                     Objects.arguments(), compiler.output(),
                                     None, 'parent')


def test_compiler_service_nested_block(patch, magic, compiler, lines, tree):
    patch.object(Objects, 'arguments')
    patch.object(JSONCompiler, 'output')
    tree.node.return_value = None
    nested_block = magic()
    tree.data = 'service'
    compiler.service(tree, nested_block, 'parent')
    line = tree.line()
    service = tree.path.extract_path()
    command = tree.service_fragment.command.child()
    lines.execute.assert_called_with(line, service, command,
                                     Objects.arguments(), compiler.output(),
                                     nested_block.line(), 'parent')


def test_compiler_service_no_output(patch, compiler, lines, tree):
    patch.object(Objects, 'arguments')
    patch.object(JSONCompiler, 'output')
    JSONCompiler.output.return_value = None
    tree.data = 'service'
    compiler.service(tree, None, 'parent')
    assert lines.set_output.call_count == 0


def test_compiler_service_syntax_error(patch, compiler, lines, tree):
    patch.object(Objects, 'arguments')
    patch.object(JSONCompiler, 'output')
    patch.object(StorySyntaxError, 'tree_position')
    lines.execute.side_effect = StorySyntaxError('error')
    tree.data = 'service'
    with raises(StorySyntaxError):
        compiler.service(tree, None, 'parent')
    StorySyntaxError.tree_position.assert_called_with(tree)


def test_compiler_find_parent_with_output_parent_none(patch, compiler, lines,
                                                      tree, magic):
    """
    test end when parent is none
    """
    patch.object(tree, 'expect')
    tree.expect.side_effect = Exception('.error.')
    parent = None
    # only do the recursion once
    orig_method = compiler.find_parent_with_output
    patch.object(compiler, 'find_parent_with_output')
    with raises(Exception) as e:
        orig_method(tree, parent)
    assert str(e.value) == '.error.'
    compiler.find_parent_with_output.assert_not_called()
    tree.expect.assert_called_with(0, 'when_no_output_parent')


def test_compiler_find_parent_with_output_parent_returned(patch, compiler,
                                                          lines, tree, magic):
    """
    Test whether the parent's output gets correctly returned
    """
    patch.object(Tree, 'expect')
    parent = '1'
    lines.lines = {'1': {'output': ['.output.'], 'service': 'my_service'}}
    # only do the recursion once
    orig_method = compiler.find_parent_with_output
    patch.object(compiler, 'find_parent_with_output')
    result = orig_method(tree, parent)
    compiler.find_parent_with_output.assert_not_called()
    assert result == ['.output.']


def test_compiler_find_parent_with_output(patch, compiler, lines, tree, magic):
    """
    Test continue to look upword in the tree
    """
    patch.object(Tree, 'expect')
    parent = magic()
    lines.lines = {parent: {'parent': '0', 'output': None}}
    # only do the recursion once
    orig_method = compiler.find_parent_with_output
    patch.object(compiler, 'find_parent_with_output')
    result = orig_method(tree, parent)
    compiler.find_parent_with_output.assert_called_with(tree, '0')
    assert result == compiler.find_parent_with_output()


def test_compiler_find_parent_with_output_empty(patch, compiler, lines, tree,
                                                magic):
    """
    Test continue to look upword in the tree when output is empty
    """
    patch.object(Tree, 'expect')
    parent = '1'
    lines.lines = {'1': {'output': [], 'parent': '0'}}
    # only do the recursion once
    orig_method = compiler.find_parent_with_output
    patch.object(compiler, 'find_parent_with_output')
    result = orig_method(tree, parent)
    compiler.find_parent_with_output.assert_called_with(tree, '0')
    assert result == compiler.find_parent_with_output()


def test_compiler_find_parent_with_no_service(patch, compiler, lines, tree,
                                              magic):
    """
    Test continue to look upword in the tree when no service is defined
    """
    patch.object(Tree, 'expect')
    parent = '1'
    lines.lines = {'1': {
        'output': ['.output.'], 'parent': '0', 'service': None}
    }
    # only do the recursion once
    orig_method = compiler.find_parent_with_output
    patch.object(compiler, 'find_parent_with_output')
    result = orig_method(tree, parent)
    compiler.find_parent_with_output.assert_called_with(tree, '0')
    assert result == compiler.find_parent_with_output()


def test_compiler_when(patch, compiler, lines, tree):
    patch.object(JSONCompiler, 'service')
    lines.lines = {'1': {}}
    lines.last.return_value = lines.lines['1']
    compiler.when(tree, 'nested_block', '1')
    JSONCompiler.service.assert_called_with(tree.service, 'nested_block', '1')
    assert lines.lines['1']['method'] == 'when'


def test_compiler_when_condensed(patch, compiler, lines, tree, magic):
    patch.object(JSONCompiler, 'service')
    patch.object(JSONCompiler, 'find_parent_with_output')
    # manual patching for staticmethod
    orig_method = Objects.name_to_path
    Objects.name_to_path = magic()
    sf = tree.service.service_fragment
    tree.service.path = '.path.'
    sf.command = None
    lines.lines = {'1': {}}
    lines.last.return_value = lines.lines['1']
    compiler.when(tree, 'nested_block', '1')
    JSONCompiler.service.assert_called_with(tree.service, 'nested_block', '1')
    assert lines.lines['1']['method'] == 'when'
    assert sf.command == '.path.'
    JSONCompiler.find_parent_with_output.assert_called_with(tree, '1')
    output_name = compiler.find_parent_with_output()[0]
    Objects.name_to_path.assert_called_with(output_name)
    assert tree.service.path == Objects.name_to_path()
    Objects.name_to_path = orig_method


def test_compiler_return_statement(patch, compiler, lines, tree):
    """
    Ensures Compiler.return_statement can compile return statements.
    """
    tree.base_expression = None
    compiler.return_statement(tree, '1')
    line = tree.line()
    kwargs = {'args': None, 'parent': '1'}
    lines.append.assert_called_with('return', line, **kwargs)


def test_compiler_return_statement_entity(patch, compiler, lines, tree):
    """
    Ensures Compiler.return_statement can compile return statements that return
    entities.
    """
    patch.object(JSONCompiler, 'fake_base_expression')
    compiler.return_statement(tree, '1')
    line = tree.line()
    JSONCompiler.fake_base_expression.assert_called_with(
        tree.base_expression, '1'
    )
    kwargs = {'args': [JSONCompiler.fake_base_expression()], 'parent': '1'}
    lines.append.assert_called_with('return', line, **kwargs)


def test_compiler_return_statement_error(patch, compiler, tree):
    """
    Ensures Compiler.return_statement raises CompilerError when the return
    is outside a function.
    """
    patch.object(JSONCompiler, 'fake_base_expression')
    compiler.return_statement(tree, None)
    tree.expect.assert_called_with(False, 'return_outside')


def test_compiler_if_block(patch, compiler, lines, tree):
    patch.many(JSONCompiler, ['subtree', 'fake_base_expression'])
    tree.elseif_block = None
    tree.else_block = None
    tree.extract.return_value = []
    compiler.if_block(tree, '1')
    exp = tree.if_statement.base_expression
    JSONCompiler.fake_base_expression.assert_called_with(exp, '1')
    nested_block = tree.nested_block
    args = [JSONCompiler.fake_base_expression()]
    lines.set_scope.assert_called_with(tree.line(), '1')
    lines.finish_scope.assert_called_with(tree.line())
    lines.append.assert_called_with('if', tree.line(), args=args,
                                    enter=nested_block.line(), parent='1')
    compiler.subtree.assert_called_with(nested_block, parent=tree.line())


def test_compiler_if_block_with_elseif(patch, compiler, tree):
    patch.many(JSONCompiler, ['subtree', 'subtrees', 'fake_base_expression'])
    tree.else_block = None
    tree.extract.return_value = ['one']
    compiler.if_block(tree, '1')
    tree.extract.assert_called_with('elseif_block')
    compiler.subtrees.assert_called_with('one', parent='1')


def test_compiler_if_block_with_else(patch, compiler, tree):
    patch.many(JSONCompiler, ['subtree', 'subtrees', 'fake_base_expression'])
    tree.extract.return_value = []
    compiler.if_block(tree, '1')
    compiler.subtrees.assert_called_with(tree.else_block, parent='1')


def test_compiler_elseif_block(patch, compiler, lines, tree):
    patch.many(JSONCompiler, ['subtree', 'fake_base_expression'])
    compiler.elseif_block(tree, '1')
    lines.set_exit.assert_called_with(tree.line())
    exp = tree.elseif_statement.base_expression
    JSONCompiler.fake_base_expression.assert_called_with(exp, '1')
    args = [JSONCompiler.fake_base_expression()]
    lines.set_scope.assert_called_with(tree.line(), '1')
    lines.finish_scope.assert_called_with(tree.line())
    lines.append.assert_called_with('elif', tree.line(), args=args,
                                    enter=tree.nested_block.line(),
                                    parent='1')
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_else_block(patch, compiler, lines, tree):
    patch.object(JSONCompiler, 'subtree')
    compiler.else_block(tree, '1')
    lines.set_exit.assert_called_with(tree.line())
    lines.set_scope.assert_called_with(tree.line(), '1')
    lines.finish_scope.assert_called_with(tree.line())
    lines.append.assert_called_with('else', tree.line(), parent='1',
                                    enter=tree.nested_block.line())
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_foreach_block(patch, compiler, lines, tree):
    patch.init(Tree)
    patch.many(JSONCompiler, ['subtree', 'output', 'fake_base_expression'])
    compiler.foreach_block(tree, '1')
    compiler.output.assert_called_with(tree.foreach_statement.output)
    args = [compiler.fake_base_expression()]
    lines.set_scope.assert_called_with(tree.line(), '1', JSONCompiler.output())
    lines.finish_scope.assert_called_with(tree.line())
    lines.append.assert_called_with('for', tree.line(), args=args,
                                    enter=tree.nested_block.line(),
                                    output=JSONCompiler.output(), parent='1')
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_while_block(patch, compiler, lines, tree):
    patch.init(Tree)
    patch.many(JSONCompiler, ['subtree', 'fake_base_expression'])
    compiler.while_block(tree, '1')
    args = [compiler.fake_base_expression()]
    lines.set_scope.assert_called_with(tree.line(), '1')
    lines.finish_scope.assert_called_with(tree.line())
    lines.append.assert_called_with('while', tree.line(), args=args,
                                    enter=tree.nested_block.line(),
                                    parent='1')
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_function_block(patch, compiler, lines, tree):
    patch.object(Objects, 'function_arguments')
    patch.many(JSONCompiler, ['subtree', 'function_output'])
    compiler.function_block(tree, '1')
    statement = tree.function_statement
    Objects.function_arguments.assert_called_with(statement)
    compiler.function_output.assert_called_with(statement)
    lines.append.assert_called_with('function', tree.line(),
                                    function=statement.child().value,
                                    args=Objects.function_arguments(),
                                    output=compiler.function_output(),
                                    enter=tree.nested_block.line(),
                                    parent='1')
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_function_block_redeclared(patch, compiler, lines, tree):
    patch.object(Objects, 'function_arguments')
    patch.many(JSONCompiler, ['subtree', 'function_output'])
    compiler.lines.functions = {'.function.': '0'}
    statement = tree.function_statement
    statement.child(1).value = '.function.'
    compiler.function_block(tree, '1')


def test_compiler_throw_statement(patch, compiler, lines, tree):
    tree.children = [Token('RAISE', 'throw')]
    compiler.throw_statement(tree, '1')
    lines.append.assert_called_with('throw', tree.line(), args=[],
                                    parent='1')


def test_compiler_throw_name_statement(patch, compiler, lines, tree):
    patch.object(Objects, 'entity')
    tree.children = [Token('RAISE', 'throw'), Token('NAME', 'error')]
    compiler.throw_statement(tree, '1')
    args = [Objects.entity()]
    lines.append.assert_called_with('throw', tree.line(), args=args,
                                    parent='1')


def test_compiler_mutation_block(patch, compiler, lines, tree):
    patch.many(Objects, ['primary_expression', 'mutation_fragment'])
    patch.object(JSONCompiler, 'chained_mutations', return_value=['chained'])
    tree.path = None
    tree.nested_block = None
    compiler.mutation_block(tree, None)
    expr = tree.mutation.primary_expression
    Objects.primary_expression.assert_called_with(expr)
    Objects.mutation_fragment.assert_called_with(
        tree.mutation.mutation_fragment)
    JSONCompiler.chained_mutations.assert_called_with(tree.mutation)
    args = [Objects.primary_expression(), Objects.mutation_fragment(),
            'chained']
    kwargs = {'args': args, 'parent': None}
    lines.append.assert_called_with('mutation', tree.line(), **kwargs)


def test_compiler_mutation_block_nested(patch, compiler, lines, tree):
    patch.many(Objects, ['primary_expression', 'mutation_fragment'])
    patch.object(JSONCompiler, 'chained_mutations', return_value=['chained'])
    tree.path = None
    compiler.mutation_block(tree, None)
    JSONCompiler.chained_mutations.assert_called_with(tree.nested_block)
    args = [Objects.primary_expression(), Objects.mutation_fragment(),
            'chained', 'chained']
    kwargs = {'args': args, 'parent': None}
    lines.append.assert_called_with('mutation', tree.line(), **kwargs)


def test_compiler_mutation_block_from_service(patch, compiler, lines, tree):
    patch.many(Objects, ['path', 'mutation_fragment'])
    patch.object(JSONCompiler, 'chained_mutations', return_value=['chained'])
    tree.nested_block = None
    tree.data = 'mutation_block'
    compiler.mutation_block(tree, None)
    Objects.path.assert_called_with(tree.path)
    Objects.mutation_fragment.assert_called_with(tree.mutation_fragment)
    JSONCompiler.chained_mutations.assert_called_with(tree)
    args = [Objects.path(), Objects.mutation_fragment(), 'chained']
    kwargs = {'args': args, 'parent': None}
    lines.append.assert_called_with('mutation', tree.line(), **kwargs)


def test_compiler_indented_chain(patch, compiler, lines, tree):
    patch.object(JSONCompiler, 'chained_mutations')
    lines.lines = {'1': {'method': 'mutation', 'args': ['args']}}
    lines.last.return_value = lines.lines['1']
    compiler.indented_chain(tree, '0')
    JSONCompiler.chained_mutations.assert_called_with(tree)
    assert lines.lines['1']['args'] == ['args'] + compiler.chained_mutations()


def test_compiler_indented_chain_first_line(patch, compiler, lines, tree):
    """
    Ensures that if this is the first line, an error is raised.
    """
    patch.init(StorySyntaxError)
    lines.last.return_value = None
    with raises(StorySyntaxError):
        compiler.indented_chain(tree, '0')
    error = 'arguments_nomutation'
    StorySyntaxError.__init__.assert_called_with(error, tree=tree)


def test_compiler_indented_chain_not_mutation(patch, compiler, lines, tree):
    """
    Ensures that if the previous line is not a mutation, an error is raised.
    """
    patch.init(StorySyntaxError)
    patch.object(JSONCompiler, 'chained_mutations')
    lines.lines = {'1': {'method': 'whatever'}}
    with raises(StorySyntaxError):
        compiler.indented_chain(tree, '0')
    error = 'arguments_nomutation'
    StorySyntaxError.__init__.assert_called_with(error, tree=tree)


def test_compiler_service_block(patch, compiler, tree):
    patch.object(JSONCompiler, 'service')
    tree.node.return_value = None
    tree.mutation = None
    compiler.service_block(tree, '1')
    compiler.service.assert_called_with(tree.service, tree.nested_block, '1')


def test_compiler_service_block_nested_block(patch, compiler, tree):
    patch.many(JSONCompiler, ['subtree', 'service'])
    tree.mutation = None
    compiler.service_block(tree, '1')
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_service_block_mutation(patch, compiler, tree):
    patch.many(JSONCompiler, ['subtree', 'service', 'mutation_block'])
    compiler.service_block(tree, '1')
    compiler.mutation_block.assert_called_with(tree.mutation,
                                               parent='1')
    compiler.subtree.assert_not_called()
    compiler.service.assert_not_called()


def test_compiler_when_block(patch, compiler, tree):
    patch.many(JSONCompiler, ['subtree', 'when'])
    compiler.when_block(tree, '1')
    JSONCompiler.when.assert_called_with(tree, tree.nested_block, '1')


def test_compiler_when_block_nested_block(patch, compiler, tree):
    patch.many(JSONCompiler, ['subtree', 'when'])
    compiler.when_block(tree, '1')
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_try_block(patch, compiler, lines, tree):
    """
    Ensures that try blocks are compiled correctly.
    """
    patch.object(JSONCompiler, 'subtree')
    tree.catch_block = None
    tree.finally_block = None
    compiler.try_block(tree, '1')
    kwargs = {'enter': tree.nested_block.line(), 'parent': '1'}
    lines.set_scope.assert_called_with(tree.line(), '1')
    lines.finish_scope.assert_called_with(tree.line())
    lines.append.assert_called_with('try', tree.line(), **kwargs)
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_try_block_catch(patch, compiler, lines, tree):
    patch.many(JSONCompiler, ['subtree', 'catch_block'])
    tree.finally_block = None
    compiler.try_block(tree, '1')
    compiler.catch_block.assert_called_with(tree.catch_block, parent='1')


def test_compiler_try_block_finally(patch, compiler, lines, tree):
    patch.many(JSONCompiler, ['subtree', 'finally_block'])
    tree.catch_block = None
    compiler.try_block(tree, '1')
    compiler.finally_block.assert_called_with(tree.finally_block, parent='1')


def test_compiler_catch_block(patch, compiler, lines, tree):
    """
    Ensures that catch blocks are compiled correctly.
    """
    patch.object(Objects, 'names')
    patch.object(JSONCompiler, 'subtree')
    compiler.catch_block(tree, '1')
    lines.set_exit.assert_called_with(tree.line())
    Objects.names.assert_called_with(tree.catch_statement)
    lines.set_scope.assert_called_with(tree.line(), '1', Objects.names())
    lines.finish_scope.assert_called_with(tree.line())
    kwargs = {'enter': tree.nested_block.line(), 'output': Objects.names(),
              'parent': '1'}
    lines.append.assert_called_with('catch', tree.line(), **kwargs)
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_finally_block(patch, compiler, lines, tree):
    """
    Ensures that finally blocks are compiled correctly.
    """
    patch.object(JSONCompiler, 'subtree')
    compiler.finally_block(tree, '1')
    lines.set_exit.assert_called_with(tree.line())
    lines.set_scope.assert_called_with(tree.line(), '1')
    lines.finish_scope.assert_called_with(tree.line())
    kwargs = {'enter': tree.nested_block.line(), 'parent': '1'}
    lines.append.assert_called_with('finally', tree.line(), **kwargs)
    compiler.subtree.assert_called_with(tree.nested_block, parent=tree.line())


def test_compiler_break_statement(compiler, lines, tree):
    compiler.break_statement(tree, '1')
    lines.append.assert_called_with('break', tree.line(), parent='1')


def test_compiler_break_statement_outside(patch, compiler, lines, tree):
    compiler.break_statement(tree, None)
    tree.expect.assert_called_with(False, 'break_outside')


@mark.parametrize('method_name', [
    'service_block', 'absolute_expression', 'assignment', 'if_block',
    'elseif_block', 'else_block', 'foreach_block', 'function_block',
    'when_block', 'try_block', 'return_statement', 'arguments',
    'mutation_block', 'indented_chain', 'break_statement'
])
def test_compiler_subtree(patch, compiler, method_name):
    patch.object(JSONCompiler, method_name)
    tree = Tree(method_name, [])
    compiler.subtree(tree)
    method = getattr(compiler, method_name)
    method.assert_called_with(tree, None)


def test_compiler_subtree_parent(patch, compiler):
    patch.object(JSONCompiler, 'assignment')
    tree = Tree('assignment', [])
    compiler.subtree(tree, parent='1')
    compiler.assignment.assert_called_with(tree, '1')


def test_compiler_subtrees(patch, compiler, tree):
    patch.object(JSONCompiler, 'subtree', return_value={'tree': 'sub'})
    compiler.subtrees(tree, tree)
    compiler.subtree.assert_called_with(tree, parent=None)


def test_compiler_subtrees_parent(patch, compiler, tree):
    patch.object(JSONCompiler, 'subtree', return_value={'tree': 'sub'})
    compiler.subtrees(tree, tree, parent='1')
    compiler.subtree.assert_called_with(tree, parent='1')


def test_compiler_parse_tree(compiler, patch):
    """
    Ensures that the parse_tree method can parse a complete tree
    """
    patch.object(JSONCompiler, 'subtree')
    tree = Tree('start', [Tree('command', ['token'])])
    compiler.parse_tree(tree)
    compiler.subtree.assert_called_with(Tree('command', ['token']),
                                        parent=None)


def test_compiler_parse_tree_parent(compiler, patch):
    patch.object(JSONCompiler, 'subtree')
    tree = Tree('start', [Tree('command', ['token'])])
    compiler.parse_tree(tree, parent='1')
    compiler.subtree.assert_called_with(Tree('command', ['token']), parent='1')


def test_compiler_compile(patch, magic):
    patch.many(JSONCompiler, ['parse_tree'])
    patch.object(Lines, 'entrypoint')
    tree = magic()
    result = JSONCompiler(story=None).compile(tree)
    JSONCompiler.parse_tree.assert_called_with(tree)
    lines = JSONCompiler(story=None).lines
    expected = {'tree': lines.lines, 'version': version,
                'services': lines.get_services(), 'functions': lines.functions,
                'entrypoint': lines.entrypoint()}
    assert result == expected

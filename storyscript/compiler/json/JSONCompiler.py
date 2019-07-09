# -*- coding: utf-8 -*-
from storyscript.Version import version
from storyscript.exceptions import StorySyntaxError
from storyscript.exceptions import internal_assert
from storyscript.parser import Tree

from .Lines import Lines
from .Objects import Objects


class JSONCompiler:

    """
    Compiles Storyscript abstract syntax tree to JSON.
    """
    def __init__(self, story):
        self.lines = Lines(story)
        self.objects = Objects()

    @staticmethod
    def output(tree):
        output = []
        if tree:
            for item in tree.children:
                output.append(item.value)
        return output

    def extract_values(self, fragment):
        """
        Extracts values from an assignment_fragment tree, to be used as
        arguments in a set method.
        """
        if fragment.expression:
            if fragment.expression.mutation:
                mutation = fragment.expression.mutation
                frag = self.objects.mutation_fragment(mutation)
                return [self.objects.values(fragment.expression.values), frag]
            return [self.objects.expression(fragment.expression)]
        return [self.objects.entity(fragment.child(1))]

    def chained_mutations(self, tree):
        """
        Finds and compile chained mutations
        """
        mutations = []
        for mutation in tree.find_data('chained_mutation'):
            m = self.objects.mutation_fragment(mutation.mutation_fragment)
            mutations.append(m)
        return mutations

    def function_output(self, tree):
        function_output = tree.function_output
        if function_output is not None:
            output_types = self.objects.types(function_output.types)
            return [output_types['type']]

    def absolute_expression(self, tree, parent):
        """
        Compiles an absolute expression using Compiler.expression
        """
        args = [self.objects.expression(tree.expression)]
        self.lines.append('expression', tree.line(), args=args, parent=parent)

    def base_expression_assignment(self, tree, parent, line):
        """
        Compiles a base expression into an expression, service or mutation
        """
        service = tree.service
        if service:
            path = self.objects.names(service.path)
            internal_assert(not self.lines.is_variable_defined(path))
            self.service(service, None, parent)
        elif tree.mutation:
            if tree.mutation.path:
                self.mutation_block(tree.mutation, parent)
            else:
                self.mutation_block(tree, parent)
            return
        elif tree.expression:
            args = [self.objects.expression(tree.expression)]
            self.lines.append('expression', line, args=args, parent=parent)
            return
        else:
            internal_assert(tree.call_expression)
            exp = tree.call_expression
            self.call_expression(exp, parent)
            return

    def fake_base_expression(self, tree, parent):
        """
        Process a fake base expression which can only be an expression or path
        as mutations and service calls have been replaced with fake paths.
        """
        if tree.expression:
            return self.objects.expression(tree.expression)
        else:
            internal_assert(tree.child(0).data == 'path')
            return self.objects.entity(tree)

    def assignment(self, tree, parent):
        """
        Compiles an assignment tree
        """
        name = self.objects.names(tree.path)
        line = tree.line()
        fragment = tree.assignment_fragment.base_expression
        self.base_expression_assignment(fragment, parent, line)
        self.lines.set_name(name)

    def arguments(self, tree, parent):
        """
        Compiles arguments. This is called only for nested arguments.
        """
        prev_line = self.lines.last()
        if prev_line is not None:
            if prev_line['method'] != 'execute':
                raise StorySyntaxError('arguments_noservice', tree=tree)
            prev_args = prev_line['args']
            prev_line['args'] = prev_args + self.objects.arguments(tree)
            return
        raise StorySyntaxError('arguments_noservice', tree=tree)

    def call_expression(self, tree, parent):
        """
        Compiles a function call expression
        """
        line = tree.line()
        tree.expect(tree.path.inline_expression is None,
                    'function_call_no_inline_expression')
        name = self.objects.names(tree.path)
        tree.expect(len(name) == 1, 'function_call_invalid_path',
                    name='.'.join(name))
        name = tree.path.extract_path()
        args = self.objects.arguments(tree)
        self.lines.append('call', line, function=name,
                          output=None, args=args, parent=parent)

    def service(self, tree, nested_block, parent):
        """
        Compiles a service tree.
        """
        assert tree.data == 'service'
        line = tree.line()
        command = tree.service_fragment.command
        tree.expect(command is not None, 'service_without_command')
        command = command.child(0)
        arguments = self.objects.arguments(tree.service_fragment)
        service = tree.path.extract_path()
        output = self.output(tree.service_fragment.output)
        if output:
            self.lines.set_scope(line, parent, output)
        enter = None
        if nested_block:
            enter = nested_block.line()
        try:
            args = (line, service, command, arguments, output, enter, parent)
            self.lines.execute(*args)
            return
        except StorySyntaxError as error:
            error.tree_position(tree)
            raise error

    def find_parent_with_output(self, tree, parent):
        """
        Searches upword in the tree for a parent with an output field.
        """
        tree.expect(parent is not None, 'when_no_output_parent')
        parent = self.lines.lines[parent]
        if parent['output'] is not None and len(parent['output']) > 0 and \
                parent['service'] is not None:
            return parent['output']

        return self.find_parent_with_output(tree, parent['parent'])

    def when(self, tree, nested_block, parent):
        """
        Compiles a when tree
        """
        assert tree.service
        sf = tree.service.service_fragment
        if not sf.command:
            sf.command = tree.service.path
            output_name = self.find_parent_with_output(tree, parent)
            tree.service.path = self.objects.name_to_path(output_name[0])
        self.service(tree.service, nested_block, parent)
        self.lines.last()['method'] = 'when'

    def return_statement(self, tree, parent):
        """
        Compiles a return_statement tree
        """
        tree.expect(parent is not None, 'return_outside')
        line = tree.line()
        args = None
        if tree.base_expression:
            args = [self.fake_base_expression(tree.base_expression, parent)]
        self.lines.append('return', line, args=args, parent=parent)

    def if_block(self, tree, parent):
        line = tree.line()
        nested_block = tree.nested_block
        args = [self.fake_base_expression(tree.if_statement.base_expression,
                                          parent)]
        self.lines.set_scope(line, parent)
        self.lines.append('if', line, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        trees = tree.extract('elseif_block')
        if tree.else_block:
            trees.append(tree.else_block)
        self.subtrees(*trees, parent=parent)
        if len(trees) == 0 and not tree.else_block:
            self.lines.finish_scope(line)

    def elseif_block(self, tree, parent):
        """
        Compiles elseif_block trees
        """
        line = tree.line()
        self.lines.set_exit(line)
        exp = tree.elseif_statement.base_expression
        args = [self.fake_base_expression(exp, parent)]
        nested_block = tree.nested_block
        self.lines.set_scope(line, parent)
        self.lines.append('elif', line, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def else_block(self, tree, parent):
        """
        Compiles else_block trees
        """
        line = tree.line()
        self.lines.set_exit(line)
        nested_block = tree.nested_block
        self.lines.set_scope(line, parent)
        self.lines.append('else', line, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def foreach_block(self, tree, parent):
        line = tree.line()
        exp = tree.foreach_statement.base_expression
        args = [self.fake_base_expression(exp, parent)]
        output = self.output(tree.foreach_statement.output)
        nested_block = tree.nested_block
        self.lines.set_scope(line, parent, output)
        self.lines.append('for', line, args=args, enter=nested_block.line(),
                          parent=parent, output=output)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def while_block(self, tree, parent):
        line = tree.line()
        exp = tree.while_statement.base_expression
        args = [self.fake_base_expression(exp, parent)]
        nested_block = tree.nested_block
        self.lines.set_scope(line, parent)
        self.lines.append('while', line, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def function_block(self, tree, parent):
        """
        Compiles a function and its nested block of code.
        """
        line = tree.line()
        function = tree.function_statement
        args = self.objects.function_arguments(function)
        output = self.function_output(function)
        nested_block = tree.nested_block or tree.block
        function_name = function.child(1).value
        self.lines.set_scope(line, parent)
        self.lines.append('function', line, function=function_name,
                          output=output, args=args, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def mutation_block(self, tree, parent):
        """
        Compiles a mutation or a service that is actually a mutation.
        """
        if tree.path:
            args = [
                self.objects.path(tree.path),
                self.objects.mutation_fragment(tree.mutation_fragment)
            ]
            args = args + self.chained_mutations(tree)
        else:
            expr = tree.mutation.primary_expression
            args = [
                self.objects.primary_expression(expr),
                self.objects.mutation_fragment(tree.mutation.mutation_fragment)
            ]
            args = args + self.chained_mutations(tree.mutation)
        if tree.nested_block:
            args = args + self.chained_mutations(tree.nested_block)
        self.lines.append('mutation', tree.line(), args=args, parent=parent)

    def indented_chain(self, tree, parent):
        """
        Compiles an indented mutation.
        """
        prev_line = self.lines.last()
        if prev_line is not None:
            if prev_line['method'] != 'mutation':
                raise StorySyntaxError('arguments_nomutation', tree=tree)
            prev_line['args'] = prev_line['args'] + \
                self.chained_mutations(tree)
            return
        raise StorySyntaxError('arguments_nomutation', tree=tree)

    def service_block(self, tree, parent):
        """
        Compiles a service block and the eventual nested block.
        """
        mut = tree.mutation
        if mut is not None:
            return self.mutation_block(mut, parent=parent)

        self.service(tree.service, tree.nested_block, parent)
        if tree.nested_block:
            self.subtree(tree.nested_block, parent=tree.line())

    def when_block(self, tree, parent):
        self.when(tree, tree.nested_block, parent)
        self.subtree(tree.nested_block, parent=tree.line())

    def try_block(self, tree, parent):
        """
        Compiles a try block
        """
        line = tree.line()
        nested_block = tree.nested_block
        self.lines.set_scope(line, parent)
        self.lines.append('try', line, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        if tree.catch_block:
            self.catch_block(tree.catch_block, parent=parent)
        if tree.finally_block:
            self.finally_block(tree.finally_block, parent=parent)
        if not (tree.catch_block or tree.finally_block):
            self.lines.finish_scope(line)

    def throw_statement(self, tree, parent):
        """
        Compiles a throw statement
        """
        line = tree.line()
        args = []
        if len(tree.children) > 1:
            args = [self.objects.entity(tree.child(1))]
        self.lines.append('throw', line, args=args, parent=parent)

    def catch_block(self, tree, parent):
        """
        Compiles a catch block
        """
        line = tree.line()
        self.lines.set_exit(line)
        nested_block = tree.nested_block
        output = self.objects.names(tree.catch_statement)
        self.lines.set_scope(line, parent, output)
        self.lines.append('catch', line, enter=nested_block.line(),
                          output=output, parent=parent)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def finally_block(self, tree, parent):
        """
        Compiles a finally block
        """
        line = tree.line()
        self.lines.set_exit(line)
        nested_block = tree.nested_block
        self.lines.set_scope(line, parent)
        self.lines.append('finally', line, enter=nested_block.line(),
                          parent=parent)
        self.subtree(nested_block, parent=line)
        self.lines.finish_scope(line)

    def break_statement(self, tree, parent):
        tree.expect(parent is not None, 'break_outside')
        self.lines.append('break', tree.line(), parent=parent)

    def subtrees(self, *trees, parent=None):
        """
        Parses many subtrees
        """
        for tree in trees:
            self.subtree(tree, parent=parent)

    def subtree(self, tree, parent=None):
        """
        Parses a subtree, checking whether it should be compiled directly
        or keep parsing for deeper trees.
        """
        allowed_nodes = ['service_block', 'absolute_expression', 'assignment',
                         'if_block', 'elseif_block', 'else_block',
                         'foreach_block', 'function_block', 'when_block',
                         'try_block', 'return_statement', 'arguments',
                         'while_block', 'throw_statement', 'break_statement',
                         'mutation_block', 'indented_chain']
        if tree.data in allowed_nodes:
            getattr(self, tree.data)(tree, parent)
        else:
            self.parse_tree(tree, parent=parent)

    def parse_tree(self, tree, parent=None):
        """
        Parses a tree looking for subtrees.
        """
        for item in tree.children:
            assert isinstance(item, Tree)
            self.subtree(item, parent=parent)

    def compile(self, tree, debug=False):
        """
        Compile an AST to JSON
        """
        self.parse_tree(tree)
        lines = self.lines
        return {'tree': lines.lines, 'services': lines.get_services(),
                'entrypoint': lines.entrypoint(), 'functions': lines.functions,
                'version': version}

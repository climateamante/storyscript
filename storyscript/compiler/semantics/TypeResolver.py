# -*- coding: utf-8 -*-
from storyscript.compiler.semantics.types.Types import BooleanType, \
    NoneType, ObjectType
from storyscript.parser import Tree

from .ExpressionResolver import ExpressionResolver
from .PathResolver import PathResolver
from .ReturnVisitor import ReturnVisitor
from .SymbolResolver import SymbolResolver
from .Visitors import ScopeSelectiveVisitor
from .symbols.Scope import Scope, ScopeJoiner
from .symbols.Symbols import StorageClass, Symbol


class ScopeBlock:
    """
    Maintains the scope for a current block.
    At the end of a block, the previous scope will be restored.
    This means that scopes are essentially a single-linked list up to the root
    scope.
    """
    def __init__(self, type_resolver, scope, storage_class):
        assert scope is not None
        self.type_resolver = type_resolver
        self.scope = scope
        self.storage_class = storage_class

    def __enter__(self):
        if self.storage_class is not None:
            self.prev_storage_class = self.type_resolver.storage_class_scope
            self.type_resolver.storage_class_scope = self.storage_class
        self.prev_scope = self.type_resolver.current_scope
        self.type_resolver.update_scope(self.scope)
        return self.scope

    def __exit__(self, exc_type, exc_value, traceback):
        if self.storage_class is not None:
            self.type_resolver.storage_class_scope = self.prev_storage_class
        self.type_resolver.update_scope(self.prev_scope)


class TypeResolver(ScopeSelectiveVisitor):
    """
    Tries to resolve the type of a variable or function call.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.symbol_resolver = SymbolResolver(scope=None)
        self.resolver = ExpressionResolver(
            symbol_resolver=self.symbol_resolver,
            function_table=self.function_table,
            mutation_table=self.mutation_table,
        )
        self.path_symbol_resolver = SymbolResolver(
            scope=None, check_variable_existence=False)
        self.path_resolver = PathResolver(self.path_symbol_resolver)
        self.in_service_block = False
        self.in_when_block = False
        if self.features.globals:
            self.storage_class_scope = StorageClass.write()
        else:
            self.storage_class_scope = StorageClass.read()

    def assignment(self, tree, scope):
        target_symbol = self.path_resolver.path(tree.path)

        # allow rebindable assignments here
        tree.expect(target_symbol.can_assign(), 'readonly_type_assignment',
                    left=target_symbol.name())

        frag = tree.assignment_fragment
        expr_sym = self.resolver.base_expression(frag.base_expression)
        expr_type = expr_sym.type()
        storage_class = expr_sym._storage_class
        if expr_sym.can_write():
            storage_class = self.storage_class_scope

        token = frag.child(0)
        tree.expect('/' not in token.value,
                    'variables_backslash', token=token)
        tree.expect('/' not in token.value,
                    'variables_dash', token=token)

        if target_symbol.type() == NoneType.instance():
            storage_class = storage_class.declaration_from_symbol()
            if not target_symbol.is_internal():
                frag.base_expression.expect(expr_type != NoneType.instance(),
                                            'assignment_type_none')
            sym = Symbol(target_symbol.name(), expr_type,
                         storage_class=storage_class)
            scope.symbols().insert(sym)
        else:
            tree.expect(target_symbol.type().can_be_assigned(expr_type),
                        'type_assignment_different',
                        target=target_symbol._type,
                        source=expr_type)

        self.visit_children(tree, scope)

    def rules(self, tree, scope):
        self.visit_children(tree, scope)

    def block(self, tree, scope):
        self.visit_children(tree, scope)

    def nested_block(self, tree, scope):
        self.visit_children(tree, scope)

    def mutation_block(self, tree, scope):
        # resolve to perform checks
        tree.scope = Scope(parent=scope)
        self.resolver.mutation(tree.mutation)

    def absolute_expression(self, tree, scope):
        # resolve to perform checks
        self.resolver.expression(tree.expression)

    def implicit_output(self, tree):
        """
        Adds implicit output to a service.
        """
        fragment = tree.service.service_fragment
        if fragment and fragment.output is None and \
                tree.nested_block is not None:
            command = fragment.command
            if command:
                command = command.child(0)
            else:
                command = tree.service.path.child(0)
            output = Tree('output', [command])
            fragment.children.append(output)

    def foreach_block(self, tree, scope):
        """
        Create a new scope and add output variables to it
        """
        tree.scope = Scope(parent=scope)
        with self.create_scope(tree.scope):
            stmt = tree.foreach_statement
            output_expr = self.resolver.base_expression(stmt.base_expression)
            output_type = output_expr.type()
            stmt.expect(stmt.output is not None, 'foreach_output_required')
            outputs = stmt.output.children
            nr_children = len(outputs)
            stmt.expect(nr_children > 0, 'foreach_output_required')

            iterable_types = output_type.output(nr_children)
            stmt.output.expect(iterable_types is not None,
                               'foreach_iterable_required',
                               target=output_type)
            stmt.output.expect(nr_children <= 2,
                               'foreach_output_children')

            for type_, output in zip(iterable_types, outputs):
                sym = Symbol.from_path(output, type_)
                tree.scope.insert(sym)

            for c in tree.nested_block.children:
                self.visit_children(c, scope=tree.scope)

    def while_block(self, tree, scope):
        self.while_statement(tree.while_statement, scope)
        tree.scope = Scope(parent=scope)
        with self.create_scope(tree.scope):
            self.visit_children(tree.nested_block, scope=tree.scope)

    def while_statement(self, tree, scope):
        """
        Checks the inside of while statements
        """
        self.resolver.base_expression(tree.base_expression)

    def check_output(self, tree, output, target):
        output.expect(len(output.children) == 1, 'output_type_only_one',
                      target=target)

        name = output.children[0]
        resolved = tree.scope.resolve(name)
        output.expect(resolved is None, 'output_unique',
                      name=resolved.name() if resolved else None)
        sym = Symbol.from_path(name, ObjectType.instance(),
                               storage_class=StorageClass.rebindable())
        tree.scope.insert(sym)

    def when_block(self, tree, scope):
        tree.scope = Scope(parent=scope)
        with self.create_scope(tree.scope, storage_class=StorageClass.write()):
            self.implicit_output(tree)

            output = tree.service.service_fragment.output
            self.check_output(tree, output, target='when')

            tree.expect(not self.in_when_block, 'nested_when_block')
            self.in_when_block = True
            for c in tree.nested_block.children:
                self.visit_children(c, scope=tree.scope)
            self.in_when_block = False

    def service_block(self, tree, scope):
        service_name = tree.service.path.child(0).value
        name = scope.resolve(service_name)
        if name is not None and name.type() != ObjectType.instance():
            tree.expect(tree.service.service_fragment.output is None,
                        'mutation_nested')
            tree.expect(tree.nested_block is None, 'mutation_nested')
            # resolve to perform checks
            self.resolver.service(tree.service)
            return

        tree.scope = Scope(parent=scope)
        with self.create_scope(tree.scope):

            self.implicit_output(tree)

            output = tree.service.service_fragment.output
            if output is not None:
                self.check_output(tree, output, target='service')

            if tree.nested_block:
                tree.expect(not self.in_service_block, 'nested_service_block')
                self.in_service_block = True
                for c in tree.nested_block.children:
                    self.visit_children(c, scope=tree.scope)
                self.in_service_block = False

    def concise_when_block(self, tree, scope):
        tree.expect(0, 'nested_when_block')

    def if_block(self, tree, scope):
        self.if_statement(tree.if_statement, scope)
        scope_joiner = ScopeJoiner()

        with self.create_scope(Scope(parent=scope)) as if_scope:
            self.visit_children(tree.nested_block, scope=if_scope)
            scope_joiner.add(if_scope)

        for c in tree.children[2:]:
            with self.create_scope(Scope(parent=scope)) as if_scope:
                self.visit(c, scope=if_scope)
                scope_joiner.add(if_scope)

        scope_joiner.insert_to(scope)

    def if_statement(self, tree, scope):
        """
        If blocks don't create a new scope.
        """
        self.ensure_boolean_expression
        self.ensure_boolean_expression(tree, tree.base_expression)

    def elseif_block(self, tree, scope):
        """
        Else if blocks don't create a new scope.
        """
        self.ensure_boolean_expression(
            tree,
            tree.elseif_statement.base_expression,
        )
        self.visit_children(tree.nested_block, scope=scope)

    def else_block(self, tree, scope):
        """
        Else blocks don't create a new scope.
        """
        self.visit_children(tree.nested_block, scope=scope)

    def ensure_boolean_expression(self, tree, expr):
        """
        Ensures that the expression resolves to a boolean.
        """
        t = self.resolver.base_expression(expr).type()
        expr.expect(t == BooleanType.instance(),
                    'if_expression_boolean', type=t)

    def try_block(self, tree, scope):
        tree.scope = Scope(parent=scope)
        with self.create_scope(tree.scope):
            self.visit_children(tree.nested_block, scope=tree.scope)
            for c in tree.children[2:]:
                self.visit(c, tree.scope)

    def catch_block(self, tree, scope):
        self.visit_children(tree, scope=scope)

    def finally_block(self, tree, scope):
        self.visit_children(tree, scope=scope)

    def function_block(self, tree, scope):
        tree.scope, return_type = self.function_statement(
            tree.function_statement, scope
        )
        with self.create_scope(tree.scope, storage_class=StorageClass.write()):
            self.visit_children(tree.nested_block, scope=tree.scope)
            ReturnVisitor.check(tree, tree.scope, return_type,
                                self.function_table, self.mutation_table)

    def function_statement(self, tree, scope):
        """
        Create a new scope _without_ a parent scope for this function.
        Prepopulate the scope with symbols from the function arguments.
        """
        scope = Scope.root()
        function_name = tree.child(1).value
        function = self.function_table.resolve(function_name)
        for arg, sym in function._args.items():
            scope.insert(sym)
        return scope, function._output

    def update_scope(self, scope):
        """
        Updates the current scope for the respective resolvers.
        """
        self.current_scope = scope
        self.symbol_resolver.update_scope(scope)
        self.path_symbol_resolver.update_scope(scope)

    def create_scope(self, scope, storage_class=None):
        return ScopeBlock(self, scope, storage_class)

    def start(self, tree, scope=None):
        # create the root scope
        tree.scope = Scope.root()
        self.update_scope(tree.scope)
        self.visit_children(tree, scope=tree.scope)

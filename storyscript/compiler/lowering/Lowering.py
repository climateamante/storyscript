# -*- coding: utf-8 -*-
from enum import Enum

from lark.lexer import Token

from storyscript.compiler.lowering.Faketree import FakeTree
from storyscript.compiler.lowering.utils import service_to_mutation, \
        unicode_escape
from storyscript.parser.Transformer import Transformer
from storyscript.parser.Tree import Tree


class UnicodeNameDecodeState(Enum):
    No = 0  # no unicode decode
    Start = 1  # beginning
    Running = 2  # after '{'


class Lowering:
    """
    Performs additional transformations that can't be performed, or would be
    too complicated for the Transformer, before the tree is compiled.
    """

    def __init__(self, parser, features):
        """
        Saves the used parser as it might be used again for re-evaluation
        of new statements (e.g. for string interpolation)
        """
        self.parser = parser
        self.features = features

    @staticmethod
    def fake_tree(block):
        """
        Get a fake tree
        """
        return FakeTree(block)

    @classmethod
    def replace_expression(cls, node, fake_tree, insert_point):
        """
        Inserts `node` as a new like with a fake path reference.
        Then, replaces the first child of the insert_point
        with this path reference.
        """
        line = insert_point.line()
        # generate a new assignment line
        # insert it above this statement in the current block
        # return a path reference
        child_node = None
        if node.service is not None:
            child_node = node.service
        elif node.call_expression is not None:
            assert node.call_expression is not None
            child_node = node.call_expression
        else:
            assert node.mutation is not None
            child_node = node.mutation

        fake_path = fake_tree.add_assignment(child_node, original_line=line)

        # Replace the inline expression with a fake_path reference
        insert_point.replace(0, fake_path.child(0))

    @classmethod
    def visit(cls, node, block, entity, pred, fun, parent):
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'block':
            # only generate a fake_block once for every line
            # node: block in which the fake assignments should be inserted
            block = cls.fake_tree(node)
        elif node.data == 'entity' or node.data == 'key_value':
            # set the parent where the inline_expression path should be
            # inserted
            entity = node
        elif node.data == 'service' and node.child(0).data == 'path':
            entity = node

        for c in node.children:
            cls.visit(c, block, entity, pred, fun, parent=node)

        # create fake lines for base_expressions too, but only when required:
        # 1) `expressions` are already allowed to be nested
        # 2) `assignment_fragments` are ignored to avoid two lines for simple
        #    service/mutation assignments (`a = my_service command`)
        if node.data == 'base_expression' and \
                node.child(0).data != 'expression' and \
                parent.data != 'assignment_fragment':
            # replace base_expression too
            fun(node, block, node)
            node.children = [Tree('path', node.children)]

        if pred(node):
            assert entity is not None
            assert block is not None
            fake_tree = block
            if not isinstance(fake_tree, FakeTree):
                fake_tree = cls.fake_tree(block)

            # Evaluate from leaf to the top
            fun(node, fake_tree, entity.path)

            # split services into service calls and mutations
            if entity.data == 'service':
                entity.entity = Tree('entity', [entity.path])
                service_to_mutation(entity)

    @staticmethod
    def is_inline_expression(n):
        return hasattr(n, 'data') and n.data == 'inline_expression'

    @staticmethod
    def add_strings(n1, *other_nodes):
        """
        Create an AST for concating two or more nodes.
        """
        # concatenation is currently defined as
        # arith_expression = arith_expression arith_operator mul_expression
        base_tree = Tree('arith_expression', [
            Tree('arith_expression', [
                Tree('mul_expression', [
                    Tree('unary_expression', [
                        n1
                    ])
                ])
            ])
        ])

        # if we only got one node, no concatenation is required. return
        # directly
        if len(other_nodes) == 0:
            return base_tree.children[0]

        base_tree.children.append(
            Tree('arith_operator', [Token('PLUS', '+')]),
        )

        # Technically, the grammar only supports binary expressions, but
        # the compiler and engine can handle n-ary expressions, so we can
        # directly flatten the tree and add all additional nodes as extra
        # mul_expressions
        for n2 in other_nodes:
            base_tree.children.append(Tree('mul_expression', [
                Tree('unary_expression', [
                    n2
                ])
            ]))
        return base_tree

    @staticmethod
    def make_full_tree_from_cmp(expr):
        """
        Builds a full tree from a cmp_expression node.
        """
        return Tree('expression', [
            Tree('or_expression', [
                Tree('and_expression', [
                    Tree('cmp_expression', [expr])
                ])
            ])
        ])

    @classmethod
    def flatten_template(cls, tree, text):
        """
        Flattens a string template into concatenation
        """
        # the previously seen character (n-1)
        preceding_slash = False
        # indicates whether we're inside of a string template
        inside_interpolation = False
        inside_unicode = UnicodeNameDecodeState.No
        buf = ''
        for c in text:
            if preceding_slash:
                if c == '{' or c == '}' or c == "\'" or c == '"':
                    # custom escapes
                    buf = f'{buf[:-1]}{c}'
                else:
                    # avoid deprecation messages for invalid escape sequences
                    if c == ' ':
                        buf += '\\'
                    if c == 'N':
                        # start unicode escaped name sequence
                        inside_unicode = UnicodeNameDecodeState.Start
                    buf += c
                preceding_slash = False
            else:
                if inside_unicode != UnicodeNameDecodeState.No:
                    if c == '{':
                        inside_unicode = UnicodeNameDecodeState.Running
                    tree.expect(inside_unicode ==
                                UnicodeNameDecodeState.Running,
                                'string_templates_nested')
                    if c == '}':
                        inside_unicode = UnicodeNameDecodeState.No
                    buf += c
                elif inside_interpolation:
                    if c == '}':
                        # end string interpolation
                        inside_interpolation = False
                        tree.expect(len(buf) > 0, 'string_templates_empty')
                        yield {
                            '$OBJECT': 'code',
                            'code': unicode_escape(tree, buf)
                        }
                        buf = ''
                    else:
                        tree.expect(c != '{', 'string_templates_nested')
                        buf += c
                elif c == '{':
                    # string interpolation might be the start of the string.
                    # example: "{..}"
                    if len(buf) > 0:
                        yield {
                            '$OBJECT': 'string',
                            'string': buf
                        }
                        buf = ''
                    inside_interpolation = True
                elif c == '}':
                    tree.expect(0, 'string_templates_unopened')
                else:
                    buf += c
                preceding_slash = c == '\\'

        # emit remaining string in the buffer
        tree.expect(not inside_interpolation, 'string_templates_unclosed')
        if len(buf) > 0:
            yield {
                '$OBJECT': 'string',
                'string': buf
            }

    def eval(self, orig_node, code_string, fake_tree):
        """
        Evaluates a string by parsing it to its AST representation.
        Inserts the AST expression as fake_node and returns the path
        reference to the inserted fake_node.
        """
        line = orig_node.line()
        column = int(orig_node.column()) + 1
        # add whitespace as padding to fixup the column location of the
        # resulting tokens.
        from storyscript.Story import Story
        story = Story(' ' * column + code_string, features=self.features)
        story.parse(self.parser, allow_single_quotes=True)
        new_node = story.tree

        new_node = new_node.block
        orig_node.expect(new_node, 'string_templates_no_assignment')
        # go to the actual node -> jump into block.rules or block.service
        for i in range(2):
            orig_node.expect(len(new_node.children) == 1,
                             'string_templates_no_assignment')
            new_node = new_node.children[0]
        # for now only expressions or service_blocks are allowed inside string
        # templates
        if new_node.data == 'service_block' and \
                new_node.service_fragment is None:
            # it was a plain-old path initially
            name = Token('NAME', code_string.strip(), line=line, column=column)
            name.end_column = int(orig_node.end_column()) - 1
            return Tree('path', [name])
        if new_node.data == 'absolute_expression':
            new_node = new_node.children[0]
        else:
            orig_node.expect(new_node.data == 'service',
                             'string_templates_no_assignment')

        # the new assignment should be inserted at the top of the current block
        return fake_tree.add_assignment(new_node, original_line=line)

    @classmethod
    def build_string_value(cls, text):
        """
        Returns the AST for a plain string AST node with 'text'
        """
        return Tree('values', [
            Tree('string', [
                Token('DOUBLE_QUOTED', text)
            ])
        ])

    def concat_string_templates(self, fake_tree, orig_node, string_objs):
        """
        Concatenates the to-be-inserted string templates.
        For example, a string template like "a{exp}b" gets flatten to:
            "a" + fake_path_to_exp as string + "b"

        Strings can be inserted directly, but string templates must be
        evaluated to new AST nodes and the reference to their fake_node
        assignment should be used instead.
        """
        ks = []
        for s in string_objs:
            if s['$OBJECT'] == 'string':
                # plain string -> insert directly
                str_node = self.build_string_value(s['string'])
                string_tree = Tree('pow_expression', [
                    Tree('primary_expression', [
                        Tree('entity', [
                            str_node
                        ])
                    ])
                ])
                ks.append(string_tree)
            else:
                assert s['$OBJECT'] == 'code'
                # string template -> eval
                # ignore newlines in string interpolation
                code = ''.join(s['code'].split('\n'))

                evaled_node = self.eval(orig_node, code, fake_tree)

                # cast to string (`as string`)
                base_type = orig_node.create_token('STRING_TYPE', 'string')
                as_operator = Tree('as_operator', [
                    Tree('types', [
                        Tree('base_type', [
                            base_type
                        ])
                    ])
                ])
                as_tree = Tree('pow_expression', [
                    Tree('primary_expression', [
                        Tree('entity', [
                            evaled_node
                        ]),
                    ]),
                    as_operator
                ])
                ks.append(as_tree)

        return ks

    def insert_string_template_concat(self, fake_tree, new_node):
        """
        If the string concatenation has only one child, its returned directly.
        Otherwise, the string template concatenation gets inserted into the
        FakeTree.
        Returns: a path reference to newly inserted assignment.
        """
        line = new_node.line()

        # shortcut for single-child code like '${a}'
        if len(new_node.children) == 1:
            return new_node.mul_expression.unary_expression.pow_expression. \
                primary_expression.entity.path

        assert len(new_node.children) >= 2

        # Otherwise we need to insert a new fake node with the concatenation
        new_node = self.make_full_tree_from_cmp(new_node)
        # The new concatenation node needs to be inserted below the
        # evaluated line
        return fake_tree.add_assignment(new_node, original_line=line)

    @staticmethod
    def resolve_cmp_expr_to_string(cmp_expr):
        """
        Checks whether cmp_expression has only a string as a child.
        """
        if cmp_expr is None:
            return None

        return cmp_expr.follow_node_chain([
            'cmp_expression',
            'arith_expression', 'mul_expression', 'unary_expression',
            'pow_expression', 'primary_expression', 'entity', 'values',
            'string'])

    def resolve_string_nodes(self, node, cmp_expr):
        """
        Searches for string nodes in the cmp_expression and given node.
        Cmp_expression has a higher priority than the given node, but
        will only be used if the found string node is the only node
        in cmp_expr.

        Returns: [<found string node>, <search node>]
            where <search node> is either `cmp_expr` (when the
            string node was a single leaf) or `node` otherwise.
        """
        only_cmp_expr = self.resolve_cmp_expr_to_string(cmp_expr)
        if only_cmp_expr is not None:
            # cmp_expression has only one leaf (the string), so we
            # can directly replace its children
            return only_cmp_expr, cmp_expr

        return node.follow_node_chain(['entity', 'values', 'string']), node

    def inline_string_templates(self, node, block, parent, cmp_expr):
        """
        String templates generate fake_nodes in the AST before their block
        and are replaced with a reference to their fake_nodes.

        If the string expression is the only node in its cmp_expression, it
        will be directly inserted in the AST.
        Otherwise, the string concatenation will be inserted as a new AST node.
        """
        string_node, node = self.resolve_string_nodes(node, cmp_expr)
        if string_node is None:
            return

        text = string_node.child(0).value
        string_objs = list(self.flatten_template(string_node, text))

        # empty string
        if len(string_objs) == 0:
            # no AST modifications required
            return

        # is plain string without string templates?
        if len(string_objs) == 1 and string_objs[0]['$OBJECT'] == 'string':
            string_node.child(0).value = string_objs[0]['string']
            # no further AST modifications required
            return

        fake_tree = self.fake_tree(block)
        children = self.concat_string_templates(fake_tree, string_node,
                                                string_objs)
        new_node = self.add_strings(*children)

        # if there is more than one node in cmp_expression, node will point
        # to the only the string entity and thus we can't insert string
        # concatenation directly, but must insert it as a new fake node
        # assignment.
        if node.data != 'cmp_expression':
            new_node = self.insert_string_template_concat(fake_tree, new_node)
        node.children = [new_node]

    def visit_string_templates(self, node, block, parent, cmp_expr):
        """
        Iterates the AST and evaluates string templates.
        """
        if not hasattr(node, 'children'):
            return

        if node.data == 'block':
            block = node
        if node.data == 'cmp_expression':
            cmp_expr = node
        elif node.data == 'entity':
            self.inline_string_templates(node, block, parent, cmp_expr)

        for c in node.children:
            self.visit_string_templates(c, block, node, cmp_expr=cmp_expr)

    def visit_concise_when(self, node):
        """
        Searches for to be processed concise_when_block.
        """
        if node.data == 'start':
            for c in node.children:
                self.visit_concise_when(c)
        # concise_when_blocks can only occur at the root-level, hence we can
        # directly iterate here:
        if node.data == 'block':
            fake_tree = self.fake_tree(node)
            for i, c in enumerate(node.children):
                if c.data == 'concise_when_block':
                    node.children[i] = self.process_concise_block(c, fake_tree)

    def process_concise_block(self, node, fake_tree):
        """
        Creates a service_block around a concise_when_block and fixes up its
        line numbers with the fake_tree.
        """
        line = fake_tree.line()
        # create token from the "new" line
        name = Token('NAME', node.child(0).value, line=line)
        path_token = Token('NAME', node.child(1).value, line=line)
        t = Tree('service_block', [
            Tree('service', [
                Tree('path', [name]),
                Tree('service_fragment', [
                    Tree('command', [path_token]),
                    Tree('output', [path_token]),
                ])
            ]),
            Tree('nested_block', [
                Tree('block', [
                    node.when_block
                ])
            ])
        ])
        return t

    @staticmethod
    def create_entity(path):
        """
        Create an entity expression
        """
        return Tree('expression', [
            Tree('or_expression', [
                Tree('and_expression', [
                    Tree('cmp_expression', [
                        Tree('arith_expression', [
                            Tree('mul_expression', [
                                Tree('unary_expression', [
                                    Tree('pow_expression', [
                                        Tree('primary_expression', [
                                            Tree('entity', [
                                                path
                                            ])
                                        ])
                                    ])
                                ])
                            ])
                        ])
                    ])
                ])
            ])
        ])

    def visit_assignment(self, node, block, parent):
        """
        Visit assignments and lower destructors
        """
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'block':
            # only generate a fake_block once for every line
            # node: block in which the fake assignments should be inserted
            block = self.fake_tree(node)

        if node.data == 'assignment':
            c = node.children[0]
            if c.data == 'types':
                line = node.line()
                base_expr = node.assignment_fragment.base_expression
                orig_node = Tree('base_expression', base_expr.children)
                orig_obj = block.add_assignment(orig_node, original_line=line)
                base_expr.children = [
                    Tree('expression', [
                        Tree('as_expression', [
                            orig_obj,
                            Tree('as_operator', [c]),
                        ])
                    ])
                ]
                # now process the rest of the assignment
                node.children = node.children[1:]
                c = node.children[0]

            if c.data == 'path':
                # a path assignment -> no processing required
                pass
            else:
                assert c.data == 'assignment_destructoring'
                line = node.line()
                base_expr = node.assignment_fragment.base_expression
                orig_node = Tree('base_expression', base_expr.children)
                orig_obj = block.add_assignment(orig_node, original_line=line)
                for i, n in enumerate(c.children):
                    new_line = block.line()
                    n.expect(len(n.children) == 1,
                             'object_destructoring_invalid_path')
                    name = n.child(0)
                    name.line = new_line  # update token's line info
                    # <n> = <val>
                    val = self.create_entity(Tree('path', [
                        orig_obj.child(0),
                        Tree('path_fragment', [
                            Tree('string', [name])
                        ])
                    ]))
                    if i + 1 == len(c.children):
                        # for the last entry, we can recycle the existing node
                        node.children[0] = n
                        node.assignment_fragment.base_expression.children = \
                            [val]
                    else:
                        # insert new fake line
                        a = block.assignment_path(n, val, new_line)
                        parent.children.insert(0, a)
        else:
            for c in node.children:
                self.visit_assignment(c, block, parent=node)

    @staticmethod
    def create_unary_operation(child):
        op = Tree('unary_operator', [child.create_token('NOT', '!')])
        return Tree('arith_expression', [
                Tree('mul_expression', [
                    Tree('unary_expression', [
                        op,
                        Tree('unary_expression', [
                            Tree('pow_expression', [
                                Tree('primary_expression', [
                                    child
                                ])
                            ])
                        ])
                    ])
                ])
            ])

    @classmethod
    def rewrite_cmp_expr(cls, node):
        cmp_op = node.cmp_operator
        cmp_tok = cmp_op.child(0)

        if cmp_tok.type == 'NOT_EQUAL':
            cmp_tok = cmp_op.create_token('EQUAL', '==')
        elif cmp_tok.type == 'GREATER_EQUAL':
            cmp_tok = cmp_op.create_token('LESSER', '<')
            cmp_op.children.reverse()
        else:
            assert cmp_tok.type == 'GREATER'
            cmp_tok = cmp_op.create_token('LESSER_EQUAL', '<=')
            cmp_op.children.reverse()

        # replace comparison token
        cmp_op.children = [cmp_tok]
        # create new comparison tree with 'NOT'
        unary_op = cls.create_unary_operation(Tree('or_expression', [
            Tree('and_expression', [
                Tree('cmp_expression', node.children)
            ])
        ]))
        node.children = [unary_op]

    def visit_cmp_expr(self, node):
        """
        Visit assignments and lower destructors
        """
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'cmp_expression' and len(node.children) == 3:
            cmp_op = node.child(1)
            assert cmp_op.data == 'cmp_operator'
            cmp_tok = cmp_op.child(0)
            if cmp_tok.type == 'NOT_EQUAL' or \
                    cmp_tok.type == 'GREATER_EQUAL' or \
                    cmp_tok.type == 'GREATER':
                self.rewrite_cmp_expr(node)

        for c in node.children:
            self.visit_cmp_expr(c)

    def visit_arguments(self, node):
        """
        Transforms an argument tree. Short-hand argument (:foo) will be
        expanded.
        """
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'arguments':
            Transformer.argument_shorthand(node)

        for c in node.children:
            self.visit_arguments(c)

    def visit_as_expr(self, node, block):
        """
        Visit assignments and move 'as' up the tree if required
        """
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'foreach_block':
            block = node.foreach_statement
            assert block is not None
        elif node.data == 'service_block' or node.data == 'when_block':
            block = node.service.service_fragment
            block = node.service.service_fragment
            assert block is not None

        if node.data == 'pow_expression':
            as_op = node.as_operator
            if as_op is not None and as_op.output_names is not None:
                output = Tree('output', as_op.output_names.children)
                node.expect(block is not None, 'service_no_inline_output')
                block.children.append(output)
                node.children = [node.children[0]]

        for c in node.children:
            self.visit_as_expr(c, block)

    def visit_function_dot(self, node, block):
        """
        Visit function call with more than one path and lower
        them into mutations.
        """
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'call_expression':
            call_expr = node
            if len(call_expr.path.children) > 1:
                path_fragments = call_expr.path.children
                call_expr.children = [
                    Tree('primary_expression', [
                        Tree('entity', [
                            Tree('path', call_expr.path.children[:-1])
                        ])
                    ]),
                    Tree('mutation_fragment', [
                        path_fragments[-1].children[0],
                        *call_expr.children[1:]
                    ])
                ]
                call_expr.data = 'mutation'

        for c in node.children:
            self.visit_function_dot(c, block)

    def visit_dot_expression(self, node, block, parent):
        """
        Visit dot expression and lower them into mutation fragments.
        """
        if not hasattr(node, 'children') or len(node.children) == 0:
            return

        if node.data == 'block':
            # only generate a fake_block once for every line
            # node: block in which the fake assignments should be inserted
            block = self.fake_tree(node)

        if node.data == 'dot_expression':
            dot_expr = node
            expression = Tree('mutation', [
                parent.primary_expression,
                Tree('mutation_fragment', [
                    dot_expr.child(0),  # name
                    dot_expr.arguments
                ])
            ])
            path = block.add_assignment(expression,
                                        original_line=parent.line())
            parent.children = [Tree('primary_expression', [
                Tree('entity', [
                    path
                ])
            ])]

        for c in node.children:
            self.visit_dot_expression(c, block, parent=node)

    def process(self, tree):
        """
        Applies several preprocessing steps to the existing AST.
        """
        pred = Lowering.is_inline_expression
        self.visit_concise_when(tree)
        self.visit_cmp_expr(tree)
        self.visit_as_expr(tree, block=None)
        self.visit_arguments(tree)
        self.visit_assignment(tree, block=None, parent=None)
        self.visit_string_templates(tree, block=None, parent=None,
                                    cmp_expr=None)
        self.visit_function_dot(tree, block=None)
        self.visit_dot_expression(tree, block=None, parent=None)
        self.visit(tree, None, None, pred,
                   self.replace_expression, parent=None)
        return tree

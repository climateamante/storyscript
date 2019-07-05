# -*- coding: utf-8 -*-
from collections import namedtuple

from storyscript.compiler.semantics.types.Indexing import IndexKind
from storyscript.compiler.semantics.types.Types import BooleanType, \
    FloatType, IntType, RangeType, StringType
from storyscript.parser import Tree


NamedPath = namedtuple('NamedPath', ('value', 'type', 'kind'))


class PathResolver:
    """
    Resolves a path to a symbol
    """
    def __init__(self, symbol_resolver):
        # how to resolve existing symbols
        self.symbol_resolver = symbol_resolver

    @staticmethod
    def number(tree):
        token = tree.child(0)
        if token.type == 'FLOAT':
            return FloatType.instance()
        assert token.type == 'INT'
        return IntType.instance()

    def names(self, tree):
        """
        Extracts names from a path tree
        """
        assert tree.data == 'path'
        main_name = tree.child(0).value
        names = [NamedPath(main_name, main_name, IndexKind.FIRST)]
        for fragment in tree.children[1:]:
            child = fragment.child(0)
            kind = IndexKind.INDEX
            if isinstance(child, Tree):
                if child.data == 'string':
                    type_ = StringType.instance()
                    value = child.child(0).value
                elif child.data == 'boolean':
                    type_ = BooleanType.instance()
                    value = child.child(0).value
                elif child.data == 'range':
                    type_ = RangeType.instance()
                    value = 'range'
                elif child.data == 'number':
                    type_ = self.number(child)
                    value = child.child(0).value
                else:
                    assert child.data == 'path'
                    type_ = self.path(child)
                    value = child.child(0).value
            else:
                assert child.type == 'NAME'
                kind = IndexKind.DOT
                value = child.value
                type_ = StringType.instance()
            names.append(NamedPath(value, type_, kind))
        return names

    def path(self, tree):
        assert tree.data == 'path'
        path_names = self.names(tree)
        for p in path_names:
            # ignore internal variables
            if p.kind == IndexKind.INDEX or p.value.startswith('__p-'):
                continue
            tree.expect('-' not in p.value,
                        'path_name_invalid_char', path=p.value, token='-')
            tree.expect('/' not in p.value,
                        'path_name_invalid_char', path=p.value, token='/')
        symbol = path_names.pop(0).value
        return self.symbol_resolver.resolve(tree, symbol, path_names)

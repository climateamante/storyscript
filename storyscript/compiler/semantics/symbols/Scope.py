# -*- coding: utf-8 -*-

from storyscript.compiler.semantics.types.Types import ObjectType

from .Symbols import StorageClass, Symbol, Symbols


class Scope:
    """
    Manages an individual scope
    """

    def __init__(self, parent=None):
        self._parent = parent
        self._symbols = Symbols()

    def insert(self, sym):
        self._symbols.insert(sym)

    def resolve(self, path):
        for scope in self.scopes():
            p = scope._symbols.resolve(path)
            if p:
                return p

    def symbols(self):
        """
        Returns all symbols available in the current scope
        """
        return self._symbols

    def parent(self):
        """
        Returns the parent scope
        """
        return self._parent

    def scopes(self):
        """
        Iterator over this and all its parent scopes
        """
        yield self
        if self._parent is not None:
            yield from self._parent.scopes()

    def pretty(self):
        indent = '\t'
        return (f'Parent: {self.parent()}\n'
                f'Symbols:\n{self.symbols().pretty(indent=indent)}')

    @classmethod
    def root(cls):
        """
        Creates a root scope.
        """
        scope = cls(parent=None)
        # insert global symbols
        app = Symbol(name='app', type_=ObjectType.instance(),
                     storage_class=StorageClass.read())
        scope.insert(app)
        return scope


class ScopeJoiner:
    """
    Manages a joint scope of one or more scopes.
    The joint scope is the intersection of these scopes.
    """

    def __init__(self):
        self.scope = None

    def add(self, scope):
        """
        Performs the join operation on one or more scopes.
        """
        if self.scope is None:
            self.scope = scope
            self.symbols = scope._symbols._symbols
        else:
            # join symbols
            symbols = scope._symbols._symbols
            for k in [*self.symbols.keys()]:
                if k not in symbols:
                    del self.symbols[k]

    def insert_to(self, scope):
        """
        Inserts the joined set of symbols into a scope.
        """
        for s in self.symbols.values():
            scope.insert(s)

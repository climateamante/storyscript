# -*- coding: utf-8 -*-
from storyscript.compiler.semantics.types.Indexing import IndexKind
from storyscript.compiler.semantics.types.Types import BaseType


class StorageClass:
    """
    A storage class of a variable defines the capabilities of a variable.
    """

    def __init__(self, write=True, rebindable=True):
        """
        Args:
            write: whether any value of this variable  can be written to.
               Akin to transitive `const`.
            rebindable: whether the variable can be assigned with new values.
        """
        self._write = write
        self._rebindable = rebindable

    def can_write(self):
        """
        If any value of this variable  can be written to.
        Akin to transitive `const`.
        """
        return self._write

    def can_assign(self):
        """
        If the variable can be assigned with new values.
        """
        return self._rebindable

    @classmethod
    def write(cls):
        """
        Create a writable, rebindable storage class.
        """
        return cls(write=True, rebindable=True)

    @classmethod
    def read(cls):
        """
        Create a readonly and non-rebindable storage class.
        """
        return cls(write=False, rebindable=False)

    @classmethod
    def rebindable(cls):
        """
        Create a readonly, but rebindable storage class.
        """
        return cls(write=False, rebindable=True)

    def index(self):
        """
        Perform an index operation on a variable (e.g. a['b']).
        Read-permissions are transitively forwarded.
        """
        write = self._write
        rebindable = self._rebindable
        if not self.can_write():
            rebindable = False
        sc = StorageClass(write=write, rebindable=rebindable)
        return sc

    def declaration_from_symbol(self):
        """
        Create a new storage class from an existing one.
        Copy over the existing read permission.
        """
        write = self._write
        rebindable = True
        sc = StorageClass(write=write, rebindable=rebindable)
        return sc


def base_symbol(type_):
    """
    Creates a temporary symbol for a base type
    """
    return Symbol('tmp', type_)


class Symbol:
    """
    Representation of an individual symbol.
    """
    def __init__(self, name, type_, storage_class=None):
        self._name = name
        self._type = type_
        if storage_class is None:
            storage_class = StorageClass.write()
        self._storage_class = storage_class

    def name(self):
        return self._name

    def type(self):
        return self._type

    def pretty(self):
        return f'{self._type}'

    def __str__(self):
        base = f"'{self._name}', {self._type}"
        if not self.can_write():
            base += ', ro'
        return f'Symbol({base})'

    @classmethod
    def from_path(cls, node, type_, storage_class=None):
        assert node.type == 'NAME'
        name = node.value
        return cls(name, type_, storage_class=storage_class)

    def is_internal(self):
        return self._name.startswith('__p-')

    def index(self, tree, name, type_, kind):
        """
        Runs index operations on a resolved symbol.
        """
        symbol = self
        if isinstance(type_, Symbol):
            type_ = type_.type()
        else:
            assert isinstance(type_, BaseType)
        new_type = symbol.type().index(type_, kind)
        if kind == IndexKind.DOT:
            tree.expect(new_type is not None,
                        'type_dot_incompatible',
                        left=symbol.type(),
                        name=name,
                        right=type_)
        else:
            tree.expect(new_type is not None,
                        'type_index_incompatible',
                        left=symbol.type(),
                        name=name,
                        right=type_)
        sc = self._storage_class.index()
        return Symbol(name=symbol.name() + '[]', type_=new_type,
                      storage_class=sc)

    def can_write(self):
        return self._storage_class.can_write()

    def can_assign(self):
        return self._storage_class.can_assign()


class Symbols:
    """
    Represents all symbols in a scope
    """

    def __init__(self):
        self._symbols = {}

    def resolve(self, name):
        assert len(name) > 0
        if name in self._symbols:
            return self._symbols[name]

    def insert(self, symbol):
        self._symbols[symbol.name()] = symbol

    def pretty(self, indent=''):
        result = ''
        for k, v in self._symbols.items():
            result += f'{indent}{k}: {v.pretty()}\n'
        return result

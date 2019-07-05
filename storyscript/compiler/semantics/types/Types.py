# -*- coding: utf-8 -*-
from storyscript.compiler.semantics.types.Indexing import IndexKind


def singleton(fn):
    """
    Lazily instantiate a type
    """
    _instance = None

    def wrapped():
        nonlocal _instance
        if _instance is None:
            _instance = fn()
        return _instance
    return wrapped


def binary_op(op, left, right):
    """
    Default binary operation:
        1) if both types are equal -> left.op(op)
        2) if string concat and the other type can be stringified -> string
        3) try to implicitly convert left to right or right -> implicit.op(op)
    """
    if left == right:
        return left.op(op)
    if op and op.type == 'PLUS':
        if isinstance(left, StringType) and right.string():
            return left
        if isinstance(right, StringType) and left.string():
            return right

    left_implicit = left.implicit_to(right)
    right_implicit = right.implicit_to(left)
    new_type = left_implicit or right_implicit
    # no implicit conversion possible
    if new_type is None:
        return None

    if new_type == AnyType.instance():
        # one of the types is 'any', check if the type would be compatible with
        # itself
        if left == AnyType.instance():
            return right.op(op)
        else:
            return left.op(op)

    return new_type.op(op)


def explicit_cast(from_, to):
    """
    Checks whether from_ can be explicitly converted to to.
    `any` can always be explicitly converted.
    """
    if from_ == AnyType.instance():
        return to
    return to.explicit_from(from_)


def implicit_cast(t1, t2):
    """
    Checks whether two types can be implicitly casted
    to one of each other.
    Returns `None` if no implicit cast can be performed.
    """
    t1_t2 = t1.implicit_to(t2)
    if t1_t2 is not None:
        return t1_t2
    t2_t1 = t2.implicit_to(t1)
    if t2_t1 is not None:
        return t2_t1
    return None


class BaseType:
    """
    Base class of a type.
    """

    def binary_op(self, other, op):
        """
        Returns the new_type if the type supports this operation.
        `None` otherwise.
        """
        return binary_op(op, self, other)

    def op(self, op):
        """
        Returns the new_type if the type supports operations on itself.
        `None` otherwise.
        """
        raise NotImplementedError()

    def output(self, n):
        """
        Output types of this type.
        """
        return None

    def has_boolean(self):
        """
        Returns True if the type can be evaluated to boolean, False otherwise.
        """
        return False

    def cmp(self, other):
        """
        Returns True if the type can be compared with `other`, False otherwise.
        """
        return implicit_cast(self, other)

    def equal(self, other):
        """
        Returns True if the type can perform equality comparison with `other`,
        False otherwise.
        """
        return implicit_cast(self, other)

    def can_be_assigned(self, other):
        if other == AnyType.instance():
            return None
        return other.implicit_to(self)

    def implicit_to(self, other):
        """
        Returns `other` if the type can be implicitly converted to `other`.
        None otherwise.
        """
        if self == other:
            return self
        if other == AnyType.instance():
            return other
        return None

    def explicit_from(self, from_type):
        """
        Return `self` if the type can be explicitly converted from `other`.
        None otherwise.
        """
        return from_type.implicit_to(self)

    def string(self):
        """
        Returns True if the type can be stringified.
        False otherwise.
        """
        return True

    def hashable(self):
        """
        Returns whether the type can be hashed.
        """
        return True

    def index(self, index_type, index_kind):
        """
        Returns the type resulting from an index operation with `index_type` of
        kind `index_kind` ('index' or 'dot')
        """
        return None


class BooleanType(BaseType):
    """
    Represents an boolean.
    """

    def __str__(self):
        return 'boolean'

    def __eq__(self, other):
        return isinstance(other, BooleanType)

    def op(self, op):
        return IntType.instance()

    @singleton
    def instance():
        """
        Returns a static instance of the BooleanType.
        """
        return BooleanType()

    def has_boolean(self):
        return True

    def implicit_to(self, other):
        s = super().implicit_to(other)
        if s is not None:
            return s
        return None

    def explicit_from(self, other):
        """
        Almost all types explicitly converted to bool.
        """
        if other.has_boolean():
            return self


class NoneType(BaseType):
    """
    Represents an none-representable type
    """

    def __str__(self):
        return 'none'

    def __eq__(self, other):
        return isinstance(other, NoneType)

    def can_be_assigned(self, other):
        return False

    def binary_op(self, other, op):
        return None

    @singleton
    def instance():
        """
        Returns a static instance of the NoneType.
        """
        return NoneType()

    def cmp(self, other):
        return None

    def equal(self, other):
        return None

    def string(self):
        return False

    def hashable(self):
        return False

    def explicit_from(self, other):
        return None


class IntType(BaseType):
    """
    Represents an integer.
    """

    def __str__(self):
        return 'int'

    def __eq__(self, other):
        return isinstance(other, IntType)

    def op(self, op):
        return self

    def index(self, other, kind):
        return None

    @singleton
    def instance():
        """
        Returns a static instance of the IntType.
        """
        return IntType()

    def has_boolean(self):
        return False

    def implicit_to(self, other):
        s = super().implicit_to(other)
        if s is not None:
            return s
        if other == FloatType.instance():
            return other
        return None

    def explicit_from(self, other):
        if other == self:
            return self
        if other == BooleanType.instance():
            return self
        if other == FloatType.instance():
            return self
        if other == StringType.instance():
            return self
        return None


class FloatType(BaseType):
    """
    Represents a float.
    """

    def __str__(self):
        return 'float'

    def __eq__(self, other):
        return isinstance(other, FloatType)

    def op(self, op):
        return self

    @singleton
    def instance():
        """
        Returns a static instance of the FloatType.
        """
        return FloatType()

    def has_boolean(self):
        return False

    def explicit_from(self, other):
        if other == self:
            return self
        if other == BooleanType.instance():
            return self
        if other == IntType.instance():
            return self
        if other == StringType.instance():
            return self
        return None


class StringType(BaseType):
    """
    Represents a string.
    """

    def __str__(self):
        return 'string'

    def __eq__(self, other):
        return isinstance(other, StringType)

    def op(self, op):
        if op.type == 'PLUS':
            return self
        return None

    def index(self, other, kind):
        # no dot on strings
        if kind != IndexKind.INDEX:
            return None
        # only numeric indices or  ranges
        if isinstance(other, RangeType):
            return self
        if other.implicit_to(IntType.instance()):
            return self
        return None

    @singleton
    def instance():
        """
        Returns a static instance of the StringType.
        """
        return StringType()

    def has_boolean(self):
        return False

    def explicit_from(self, other):
        if other != NoneType.instance():
            return self


class TimeType(BaseType):
    """
    Represents a time duration.
    """

    def __str__(self):
        return 'time'

    def __eq__(self, other):
        return isinstance(other, TimeType)

    def op(self, op):
        if op.type == 'PLUS' or op.type == 'DASH':
            return self
        return None

    @singleton
    def instance():
        """
        Returns a static instance of the TimeType.
        """
        return TimeType()

    def has_boolean(self):
        return False

    def explicit_from(self, other):
        if other == self:
            return self
        if other == StringType.instance():
            return self


class RegExpType(BaseType):
    """
    Represents a regular expression.
    """

    def __str__(self):
        return 'regexp'

    def __eq__(self, other):
        return isinstance(other, RegExpType)

    def op(self, op):
        # no operations allowed on RegExp
        return None

    @singleton
    def instance():
        """
        Returns a static instance of the RegExpType.
        """
        return RegExpType()

    def has_boolean(self):
        return False

    def cmp(self, other):
        return None

    def hashable(self):
        return False

    def explicit_from(self, other):
        if other == self:
            return self
        if other == StringType.instance():
            return self


class RangeType(BaseType):
    """
    Represents a range.
    """

    def __str__(self):
        return 'range'

    def __eq__(self, other):
        return isinstance(other, RangeType)

    @singleton
    def instance():
        """
        Returns a static instance of the RangeType.
        """
        return RangeType()


class ListType(BaseType):
    """
    Represents a List.
    """
    def __init__(self, inner):
        assert isinstance(inner, BaseType)
        self.inner = inner

    def __str__(self):
        return f'List[{self.inner}]'

    def __eq__(self, other):
        return isinstance(other, ListType) and \
            self.inner == other.inner

    def op(self, op):
        if op.type == 'PLUS':
            return self
        return None

    def implicit_to(self, other):
        if self == other:
            return self
        if not isinstance(other, ListType):
            return None
        im_to = self.inner.implicit_to(other.inner)
        if im_to is None:
            return None
        return ListType(im_to)

    def index(self, other, kind):
        # no dot on lists
        if kind != IndexKind.INDEX:
            return None
        # only numeric indices or range indices
        if isinstance(other, RangeType):
            return self
        if other.implicit_to(IntType.instance()):
            return self.inner
        return None

    def output(self, n):
        """
        Output types of the ListType.
        """
        if n == 1:
            return self.inner,
        return IntType.instance(), self.inner

    def has_boolean(self):
        return False

    def cmp(self, other):
        return None

    def hashable(self):
        return False

    def explicit_from(self, other):
        if self == other:
            return self
        if not isinstance(other, ListType):
            return None
        im_to = explicit_cast(other.inner, self.inner)
        if im_to is None:
            return None
        return ListType(im_to)


class MapType(BaseType):
    """
    Represents a Map
    """
    def __init__(self, key, value):
        assert isinstance(key, BaseType)
        assert isinstance(value, BaseType)
        self.key = key
        self.value = value

    def __str__(self):
        return f'Map[{self.key},{self.value}]'

    def __eq__(self, other):
        return isinstance(other, MapType) and \
               self.key == other.key and \
               self.value == other.value

    def op(self, op):
        return None

    def implicit_to(self, other):
        if self == other:
            return self
        if not isinstance(other, MapType):
            return None
        im_key = self.key.implicit_to(other.key)
        im_value = self.value.implicit_to(other.value)
        if im_key is None or im_value is None:
            return None
        return MapType(im_key, im_value)

    def index(self, other, kind):
        # no dot on maps
        if kind != IndexKind.INDEX:
            return None
        if other.implicit_to(self.key) is not None:
            return self.value
        return None

    def output(self, n):
        """
        Output types of the ObjectType.
        """
        if n == 1:
            return self.key,
        return self.key, self.value

    def has_boolean(self):
        return False

    def cmp(self, other):
        return None

    def hashable(self):
        return False

    def explicit_from(self, other):
        if self == other:
            return self
        if not isinstance(other, MapType):
            return None
        im_key = explicit_cast(other.key, self.key)
        im_value = explicit_cast(other.value, self.value)
        if im_key is None or im_value is None:
            return None
        return MapType(im_key, im_value)


class ObjectType(BaseType):
    """
    Represents an object
    """
    def __str__(self):
        return f'Object'

    def __eq__(self, other):
        return isinstance(other, ObjectType)

    def op(self, op):
        return None

    def index(self, other, kind):
        if kind == IndexKind.DOT:
            return AnyType.instance()
        if other.implicit_to(StringType.instance()) is not None:
            return AnyType.instance()
        return None

    def has_boolean(self):
        return False

    def cmp(self, other):
        return None

    def hashable(self):
        return False

    @singleton
    def instance():
        """
        Returns a static instance of the ObjectType
        """
        return ObjectType()


class AnyType(BaseType):
    """
    Represents any possible type.
    """

    def __str__(self):
        return 'any'

    def __eq__(self, other):
        return isinstance(other, AnyType)

    def can_be_assigned(self, other):
        return True

    def index(self, other, kind):
        if other.hashable():
            return self
        # type couldn't have been a key
        return None

    @singleton
    def instance():
        """
        Returns a static instance of the AnyType.
        """
        return AnyType()

    def output(self, n):
        """
        Output types of the AnyType.
        """
        if n == 1:
            return AnyType.instance(),
        return AnyType.instance(), AnyType.instance()

    def has_boolean(self):
        return False

    def cmp(self, other):
        if self == other:
            return self
        return other.cmp(other)

    def equal(self, other):
        if self == other:
            return self
        return other.equal(other)

    def hashable(self):
        return True

    def op(self, op):
        return self

    def implicit_to(self, other):
        return self

    def explicit_from(self, other):
        if other != NoneType.instance():
            return self
        return None

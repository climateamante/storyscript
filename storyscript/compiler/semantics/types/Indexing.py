# -*- coding: utf-8 -*-
from enum import Enum


class IndexKind(Enum):
    """
    List of different index operations on a type.
    """
    FIRST = 1  # placeholder type for the first element of a path chain
    INDEX = 2  # a['b']
    DOT = 3    # a.b

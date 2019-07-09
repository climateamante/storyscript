# -*- coding: utf-8 -*-
from pytest import mark

from storyscript.Intention import Intention


def test_intention_init():
    intention = Intention('line')
    assert intention.line == 'line'


@mark.parametrize('line', ['x=', 'x =', 'x= '])
def test_intention_assignment(line):
    intention = Intention(line)
    assert intention.assignment() is True


def test_intention_assignment_not():
    intention = Intention('function x')
    assert intention.assignment() is None


@mark.parametrize('line', ['fu', 'fu ', 'fun', 'functio'])
def test_intention_is_function(line):
    intention = Intention(line)
    assert intention.is_function() is True


@mark.parametrize('line', ['function', 'function name'])
def test_intentions_is_function_not(line):
    """
    Ensures these patterns are not recognized as function start.
    """
    intention = Intention(line)
    assert intention.is_function() is None


@mark.parametrize('line', ['function name x:', 'function name x:i'])
def test_intentions_function_argument(line):
    intention = Intention(line)
    assert intention.function_argument() is True


@mark.parametrize('line', [
    'function name', 'function name x', 'alpine echo a:'
])
def test_intentions_function_argument_not(line):
    intention = Intention(line)
    assert intention.function_argument() is None


@mark.parametrize('line', [
    'function name x:int r', 'function name x:int y:int r',
    'function name x:int return'
])
def test_intention_function_returns(line):
    intention = Intention(line)
    assert intention.function_returns() is True


@mark.parametrize('line', [
    'function name x:int whatever', 'function name x:int returns', 'r',
    'return'
])
def test_intentions_function_returns_not(line):
    intention = Intention(line)
    assert intention.function_returns() is None


@mark.parametrize('line', ['fo', 'foreac'])
def test_intention_foreach(line):
    intention = Intention(line)
    assert intention.foreach() is True


@mark.parametrize('line', ['foreach'])
def test_intention_foreach_not(line):
    intention = Intention(line)
    assert intention.foreach() is None


@mark.parametrize('line', ['foreach array as', 'foreach array as '])
def test_intention_foreach_as(line):
    intention = Intention(line)
    assert intention.foreach_as() is True


@mark.parametrize('line', ['foreach array a', 'as'])
def test_intention_foreach_as_not(line):
    intention = Intention(line)
    assert intention.foreach_as() is None


@mark.parametrize('line', ['wh', 'whi', 'whil'])
def test_intention_while(line):
    intention = Intention(line)
    assert intention.while_() is True


@mark.parametrize('line', ['while'])
def test_intention_while_not(line):
    intention = Intention(line)
    assert intention.while_() is None


def test_intention_unnecessary_colon():
    intention = Intention('line:')
    assert intention.unnecessary_colon() is True


def test_intention_unnecessary_colon_not():
    assert Intention('line').unnecessary_colon() is None

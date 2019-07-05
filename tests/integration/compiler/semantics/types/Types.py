from pytest import mark

from storyscript.Api import Api
from storyscript.exceptions import CompilerError

features = {'globals': True}


def succeed(source):
    """
    Expect the source code to pass.
    """
    Api.loads(source, features=features).check_success()


def fail(source):
    """
    Expect the source code to error.
    """
    s = Api.loads(source, features=features)
    assert not s.success()
    e = s.errors()[0]
    assert isinstance(e.error, CompilerError)


def run(source, should_fail):
    """
    If fail is set, expect the source code to error.
    Otherwise, expect it to pass.
    """
    if 'ANY' in source:
        pre = 'ANY = {}\n'
    elif 'fn_none' in source:
        pre = 'function fn_none\n\treturn\n'
    else:
        pre = ''
    source = pre + source
    if should_fail:
        fail(source)
    else:
        succeed(source)


all_types = {
    'boolean': 'true',
    'int': '1',
    'float': '1.5',
    'time': '1s',
    'Map[string,boolean]': '{"a": true}',
    'Map[string,int]': '{"a": 1}',
    'Map[string,float]': '{"a": 1.5}',
    'Map[boolean,string]': '{true: "a"}',
    'Map[int,string]': '{1: "a"}',
    'Map[float,string]': '{1.5: "a"}',
    'Map[string,string]': '{"a": "b"}',
    'regex': '/foo/',
    'string': '"."',
    'List[boolean]': '[true]',
    'List[int]': '[0]',
    'List[float]': '[1.5]',
    'List[string]': '["."]',
    'List[time]': '[1s]',
    'any': 'ANY[0]',
    'none': 'fn_none()',
    'object': 'app',
}


def build_type_permutations(types):
    """
    Builds test combinations from a allowed type dict.
    """
    tests = []
    for k, v in types.items():
        for r_k, r_v in all_types.items():
            left = (k, all_types[k])
            right = (r_k, r_v)
            tests.append((left, right, r_k not in v))
    return tests


###############################################################################
# Hashable types (for object keys)
###############################################################################


@mark.parametrize('el,should_pass', [
    ('regex', False),
    ('List[int]', False),
    ('Map[string,int]', False),
    ('Map[int,string]', False),
    ('none', False),
    ('time', True),
    ('any', True),
    ('object', False),
    ('boolean', True),
])
def test_index_hashable(el, should_pass):
    el = all_types[el]
    run(f'a = {el}\nb = {{a: 0}}', should_fail=not should_pass)

###############################################################################
# Index (Lists + Objects)
###############################################################################


index_types = {
    'boolean': [],
    'int': [],
    'float': [],
    'time': [],
    'regex': [],
    'string': ['int', 'any'],
    'List[boolean]': ['int', 'any'],
    'List[int]': ['int', 'any'],
    'List[float]': ['int', 'any'],
    'List[time]': ['int', 'any'],
    'List[string]': ['int', 'any'],
    'Map[string,int]': ['string', 'any'],
    'Map[int,string]': ['int', 'any'],
    'none': [],
    'any': ['boolean', 'int', 'float', 'time', 'string', 'any'],
    'object': ['string', 'any'],
}


@mark.parametrize('left,right,should_fail',
                  build_type_permutations(index_types))
def test_index(right, left, should_fail):
    run(f'a={left[1]}\nb={right[1]}\nc=a[b]', should_fail=should_fail)

###############################################################################
# Implicit assigns
###############################################################################


implicit_assigns = {
    'boolean': ['boolean'],
    'int': ['int'],
    'float': ['int', 'float'],
    'time': ['time'],
    'regex': ['regex'],
    'string': ['string'],
    'List[boolean]': ['List[boolean]'],
    'List[int]': ['List[int]'],
    'List[float]': ['List[int]', 'List[float]'],
    'List[time]': ['List[time]'],
    'List[string]': ['List[string]'],
    'Map[int,string]': ['Map[int,string]'],
    'Map[string,int]': ['Map[string,int]'],
    'Map[string,string]': ['Map[string,string]'],
    'none': [],
    'object': ['object'],
    'any': [k for k in all_types.keys() if k != 'none'],
}


@mark.parametrize('left,right,should_fail',
                  build_type_permutations(implicit_assigns))
def test_implicit_assign(right, left, should_fail):
    run(f'a = {left[1]}\na = {right[1]}', should_fail=should_fail)

###############################################################################
# Explicit casts
###############################################################################


implicit_assigns = {
    'boolean': ['boolean', 'int', 'float', 'string', 'any'],
    'int': ['int', 'float', 'string', 'any'],
    'float': ['int', 'float', 'string', 'any'],
    'time': ['time', 'string', 'any'],
    'regex': ['regex', 'string', 'any'],
    'string': ['string', 'int', 'float', 'string', 'regex',
               'any', 'time'],
    'List[boolean]': ['List[boolean]', 'List[int]', 'List[float]',
                      'List[string]', 'List[any]', 'any', 'string'],
    'List[int]': ['List[int]', 'List[float]',
                  'List[string]', 'List[any]', 'any', 'string'],
    'List[float]': ['List[int]', 'List[float]',
                    'List[string]', 'List[any]', 'any', 'string'],
    'List[time]': ['List[string]', 'List[any]', 'any',
                   'string', 'List[time]'],
    'List[string]': ['List[int]', 'List[float]', 'List[time]',
                     'List[string]', 'List[any]', 'any', 'string'],
    'Map[int,string]': ['Map[int,string]', 'Map[string,string]', 'string',
                        'any', 'Map[float,string]', 'Map[string,float]',
                        'Map[string,int]'],
    'Map[string,int]': ['Map[int,string]', 'Map[string,string]', 'string',
                        'any', 'Map[float,string]', 'Map[string,float]',
                        'Map[string,int]'],
    'Map[string,string]': ['Map[int,string]', 'Map[string,string]', 'string',
                           'any', 'Map[float,string]', 'Map[string,float]',
                           'Map[string,int]'],
    'none': [],
    'object': ['object', 'any', 'string'],
    'any': [k for k in all_types.keys() if k != 'none'],
}


@mark.parametrize('left,right,should_fail',
                  build_type_permutations(implicit_assigns))
def test_explicit_cast(right, left, should_fail):
    run(f'a = {left[1]} as {right[0]}', should_fail=should_fail)

###############################################################################
# ConvertibleToString
###############################################################################


@mark.parametrize('el', all_types.items())
def test_string_convertible(el):
    should_fail = el[0] == 'none'
    run(f'a="." + {el[1]}', should_fail=should_fail)

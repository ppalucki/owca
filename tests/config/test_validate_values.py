# Copyright (c) 2019 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from enum import Enum
from typing import List, Dict, Union, Optional, Iterable, Mapping
import inspect

import pytest

from owca.config import _assure_type, ValidationError, WeakValidationError, \
    Url, Path, Numeric


class Foo:
    pass


class FooEnum(Enum):
    BAR = 1
    BAZ = 2


@pytest.mark.parametrize('value, expected_type', [
    (1, int),
    (1, Numeric(0, 3)),
    (3.5, Numeric(2., 5.)),
    (1.2, float),
    (True, bool),
    (True, Optional[bool]),
    (None, Optional[bool]),
    (1, Optional[int]),
    (None, Optional[int]),
    ('str', str),
    ('str', Union[str, float]),
    (1.2, Union[str, float]),
    (Foo(), Foo),
    ([Foo()], List[Foo]),
    ([[1]], List[List[int]]),
    ({'x': 2}, Dict[str, int]),
    ({'x': 2.5}, Dict[str, Union[int, float]]),
    ({2: {'x': 2.5}}, Dict[int, Dict[str, Union[int, float]]]),
    (FooEnum.BAR, FooEnum),
    (1, FooEnum),
    ('https://127.0.0.1', Url()),
    ('some/path', Path()),
    ('/some/absolute/path', Path(absolute=True)),
    ('https://127.0.0.1:1234', Url()),
    ('https://127.0.0.1/some/path', Url(is_path_obligatory=True))
])
def test_assure_type_good(value, expected_type):
    _assure_type(value, expected_type)


@pytest.mark.parametrize('value, expected_type, expected_exception_msg', [
    (1, float, 'int'),
    ('1', Numeric(0, 1), 'str'),
    (1.2, int, 'float'),
    (True, float, 'bool'),
    (2.5, Optional[bool], 'Union'),  # Optional[x] is just Union[x, NoneType]
    ([[2.5]], List[List[int]], 'float'),
    ({'x': 2}, Dict[str, float], 'float'),
    ({'x': None}, Dict[str, Union[int, float]], 'at key x'),
    ({2: {'x': 2.5}}, Dict[int, Dict[str, Union[str]]], 'invalid value'),
    ('foo', FooEnum, 'enum'),
    (3, FooEnum, 'enum'),
    (127, Url(), 'int'),
    ('../some/path', Path(), 'using \'..\''),
    ('some/path', Path(absolute=True), 'absolute path'),
    ('127.0.0.1/some/path', Url(), 'Use one of supported schemes'),
    ('https://', Url(), 'Netloc'),
    ('https://something:1234', Url(is_path_obligatory=True), 'Path')
])
def test_assure_type_invalid(value, expected_type, expected_exception_msg):
    with pytest.raises(ValidationError, match=expected_exception_msg):
        _assure_type(value, expected_type)


@pytest.mark.parametrize('value, expected_type, expected_exception_msg', [
    (1, inspect.Parameter.empty, 'missing type'),
    ([1], Iterable[int], 'generic'),
    (1, Mapping[int, str], 'generic'),
])
def test_assure_type_invalid_weak(value, expected_type, expected_exception_msg):
    with pytest.raises(WeakValidationError, match=expected_exception_msg):
        _assure_type(value, expected_type)

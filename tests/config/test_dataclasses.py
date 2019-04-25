# Copyright (c) 2018 Intel Corporation
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
from typing import List, Union, Optional

import pytest
from dataclasses import dataclass, field

from owca import config
from owca import testing


class FooEnum(Enum):
    BAR = 'foobar'
    BAZ = 'foobaz'


@config.register
@dataclass
class DCExample:
    x: config.Numeric(min_value=0, max_value=5)
    y: Optional[str] = 'abc'
    d: Union[int, str] = 'notset'
    e: config.Path() = '/some/path'
    z: List[int] = field(default_factory=lambda: [1, 2, 3])
    foo: FooEnum = FooEnum.BAR


def test_dataclass():
    test_config_path = testing.relative_module_path(__file__,
                                                    'test_dataclasses.yaml')
    data = config.load_config(test_config_path)

    dc1 = data['dc1']
    assert dc1.x == 5
    assert dc1.y is None
    assert dc1.z == [1, 2, 3]
    assert dc1.d == 'asd'
    assert dc1.e == '/abc/def'
    assert dc1.foo == 'foobaz'

    dc2 = data['dc2']
    assert dc2.x == 1
    assert dc2.y == 'newble'
    assert dc2.z == [3, 4, 5]
    assert dc2.d == 4
    assert dc2.foo == FooEnum.BAR


def test_invalid_dataclass():
    test_config_path = testing.relative_module_path(
        __file__, 'test_dataclasses_invalid.yaml')
    with pytest.raises(config.ConfigLoadError,
                       match="field 'x'.*Invalid type"):
        config.load_config(test_config_path)


def test_invalid_dataclass_union():
    test_config_path = testing.relative_module_path(
        __file__, 'test_dataclasses_invalid_union.yaml')
    with pytest.raises(config.ConfigLoadError,
                       match="field 'd'.*improper type from union"):
        config.load_config(test_config_path)


def test_dataclass_invalid_field():
    test_config_path = testing.relative_module_path(
        __file__, 'test_dataclasses_invalid_field.yaml')
    with pytest.raises(config.ConfigLoadError, match="constructor signature"):
        config.load_config(test_config_path)


def test_dataclass_exceed_maximum():
    test_config_path = testing.relative_module_path(
        __file__, 'test_dataclasses_exceed_maximum.yaml')
    with pytest.raises(config.ConfigLoadError,
                       match="field 'x'.*Maximum value is 5. Got 123."):
        config.load_config(test_config_path)

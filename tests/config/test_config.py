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


import pytest

from owca import config
from owca import testing
from owca.config import ConfigLoadError


class OldClass:
    def __init__(self, x, y=3):
        self.x = x
        self.y = y


@config.register(strict_mode=False)
class NewClass(OldClass):
    pass


@config.register(strict_mode=False)
class Foo:
    def __init__(self, s: str, f: float = 1.) -> None:
        self.s = s
        self.f = f


@config.register(strict_mode=False)
class Boo:
    def __init__(self, foo: Foo = None, items=None, nc: NewClass = None) -> None:
        self.foo = foo
        self.items = items
        self.nc = nc


class Item:
    def __init__(self, name):
        self.name = name


def test_config_with_simple_classes():
    # Another method for registering items (other than using decorator).
    config.register(Item, strict_mode=False)

    test_config_path = testing.relative_module_path(__file__, 'test_config.yaml')

    data = config.load_config(test_config_path)

    foo_with_defaults = data['foo_with_defaults']
    assert foo_with_defaults.f == 1

    empty_boo = data['empty_boo']
    assert empty_boo.foo is None

    foo = data['foo']
    boo = data['boo']

    assert foo.s == 'some_string'
    assert foo.f == 2.5

    assert boo.foo is foo
    assert len(boo.items) == 2
    assert isinstance(boo.items[0], Item)


def test_config_unsafe_object_creation():
    from ruamel import yaml
    import calendar

    test_config_path = testing.relative_module_path(__file__, 'test_config_unsafe.yaml')

    # Unsafe default loader allows any python object initialization
    data = yaml.load(open(test_config_path), Loader=yaml.Loader)
    assert 'time' in data
    assert isinstance(data['time'], calendar.Calendar)

    # With use safe version only to allow construct previously registered objects
    with pytest.raises(config.ConfigLoadError, match='could not determine a constructor'):
        config.load_config(test_config_path)


def test_config_strict_mode_errors():
    config.register(Item, strict_mode=True)

    test_config_path = testing.relative_module_path(__file__, 'test_config.yaml')

    with pytest.raises(ConfigLoadError, match='missing type declaration'):
        config.load_config(test_config_path)

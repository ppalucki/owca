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
import logging
from typing import List, Dict

import pytest
from dataclasses import dataclass

from owca import config
from owca import testing
from owca.config import ConfigLoadError

log = logging.getLogger(__name__)


@config.register
@dataclass
class DCExampleValidation:
    i: List[int]
    d: Dict[str, int]
    rr: List[List[int]]
    dd: Dict[str, List[int]]


def test_dataclass_validation():
    test_config_path = testing.relative_module_path(__file__, 'test_dataclasses_validation.yaml')
    data = config.load_config(test_config_path)
    assert data['dc1'].rr == [[2, 3], []]


def test_dataclass_validation_invalid_list():
    test_config_path = testing.relative_module_path(__file__,
                                                    'test_dataclasses_validation_invalid_list.yaml')
    with pytest.raises(ConfigLoadError, match='asdf'):
        config.load_config(test_config_path)


def test_dataclass_validation_invalid_dict():
    test_config_path = testing.relative_module_path(__file__,
                                                    'test_dataclasses_validation_invalid_dict.yaml')
    with pytest.raises(ConfigLoadError, match='wrong_value'):
        config.load_config(test_config_path)

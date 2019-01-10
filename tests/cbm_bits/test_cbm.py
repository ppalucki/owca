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
from owca.cbm_bits import check_cbm_bits


def test_check_cbm_bits_success():
    check_cbm_bits('ff00', 'ffff', '1')


def test_check_cbm_bits_gap():
    with pytest.raises(ValueError):
        check_cbm_bits('f0f', 'ffff', '1')


def test_check_not_enough_cbm_bits():
    with pytest.raises(ValueError):
        check_cbm_bits('0', 'ffff', '1')


def test_check_too_big_mask():
    with pytest.raises(ValueError):
        check_cbm_bits('ffffff', 'ffff', '1')

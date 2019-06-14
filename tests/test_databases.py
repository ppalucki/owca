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

import pytest
import requests
from unittest.mock import MagicMock, patch

from wca.databases import EtcdDatabase, InvalidKey, _validate_key, TimeoutOnAllHosts


@patch('requests.post')
def test_if_set_raise_exception_if_all_host_timeout(mock_post: MagicMock):
    db = EtcdDatabase(['https://127.0.0.1:2379', 'https://127.0.0.2:2379'])

    mock_post.return_value.\
        raise_for_status.side_effect = requests.exceptions.Timeout
    with pytest.raises(TimeoutOnAllHosts):
        db.set(bytes('key', 'ascii'), bytes('val', 'ascii'))

    assert mock_post.return_value.raise_for_status.call_count == 2


@patch('requests.post')
def test_if_get_raise_exception_if_all_host_timeout(mock_post: MagicMock):
    db = EtcdDatabase(['https://127.0.0.1:2379', 'https://127.0.0.2:2379'])

    mock_post.return_value.\
        raise_for_status.side_effect = requests.exceptions.Timeout
    with pytest.raises(TimeoutOnAllHosts):
        db.get(bytes('key', 'ascii'))

    assert mock_post.return_value.raise_for_status.call_count == 2


@pytest.mark.parametrize('key', (0*b"\x6f", 256*b"\x6f", 255*b"\x00"))
def test_if_raise_exception_when_invalid_key(key):
    with pytest.raises(InvalidKey):
        _validate_key(key)

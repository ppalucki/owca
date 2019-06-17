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

import base64
import pytest
import requests
from unittest.mock import MagicMock, patch
from wca.config import ValidationError
from wca.databases import EtcdDatabase, InvalidKey, _validate_key, \
                            TimeoutOnAllHosts, ZookeeperDatabase, LocalDatabase
from wca.security import SSL


@patch('os.makedirs')
def test_localdatabase_make_directory_for_storing_data(mock_makedirs):
    LocalDatabase('storage')
    mock_makedirs.assert_called_with('storage')


@patch('builtins.open')
@patch('os.makedirs')
def test_localdatabase_set_write_to_file(mock_makedirs, mock_file):
    LocalDatabase('storage').set(b'key', b'value')
    mock_file.assert_called_with('storage/key', 'wb')
    mock_file.return_value.__enter__.return_value.write.assert_called_with(b'value')


@patch('builtins.open')
@patch('os.path.exists', return_value=True)
@patch('os.makedirs')
def test_localdatabase_get_read_from_file(mock_makedirs, mock_path_exists, mock_file):
    mock_file.return_value.__enter__.return_value.read.return_value = b'value'
    value = LocalDatabase('storage').get(b'key')
    mock_file.assert_called_with('storage/key', 'rb')
    assert value == b'value'


@patch('builtins.open')
@patch('os.path.exists', return_value=False)
@patch('os.makedirs')
def test_localdatabase_get_return_nothing_if_file_not_exists(
        mock_makedirs, mock_path_exists, mock_file):
    value = LocalDatabase('storage').get(b'key')
    assert value is None


@patch('requests.post')
def test_etcd_set(mock_post):
    db = EtcdDatabase(['https://127.0.0.1:2379', 'https://127.0.0.2:2379'])
    db.set(b'key', b'value')
    mock_post.assert_called_once()


@patch('requests.post')
def test_etcd_get(mock_post):
    db = EtcdDatabase(['https://127.0.0.1:2379', 'https://127.0.0.2:2379'])
    mock_post.return_value.json.return_value = {'kvs': [
        {'value': base64.b64encode(b'value').decode('ascii')}]}
    value = db.get(b'key')
    assert value == b'value'


@patch('requests.post')
def test_etcd_set_raise_exception_if_all_host_timeout(mock_post: MagicMock):
    db = EtcdDatabase(['https://127.0.0.1:2379', 'https://127.0.0.2:2379'])

    mock_post.return_value.\
        raise_for_status.side_effect = requests.exceptions.Timeout
    with pytest.raises(TimeoutOnAllHosts):
        db.set(bytes('key', 'ascii'), bytes('val', 'ascii'))

    assert mock_post.return_value.raise_for_status.call_count == 2


@patch('requests.post')
def test_etcd_get_raise_exception_if_all_host_timeout(mock_post: MagicMock):
    db = EtcdDatabase(['https://127.0.0.1:2379', 'https://127.0.0.2:2379'])

    mock_post.return_value.\
        raise_for_status.side_effect = requests.exceptions.Timeout
    with pytest.raises(TimeoutOnAllHosts):
        db.get(bytes('key', 'ascii'))

    assert mock_post.return_value.raise_for_status.call_count == 2


@pytest.mark.parametrize('key', (0*b"\x6f", 256*b"\x6f", 255*b"\x00"))
def test_raise_exception_when_invalid_key(key):
    with pytest.raises(InvalidKey):
        _validate_key(key)


@patch('kazoo.client.KazooClient')
def test_zookeeper_get(mock_kazoo):
    mock_kazoo.return_value.get.return_value = [b'value']
    zk = ZookeeperDatabase(
            ['https://127.0.0.1:2181', 'https://127.0.0.2:2181'],
            'zk_namespace')
    value = zk.get(b'key')
    assert value == b'value'


@patch('kazoo.client.KazooClient')
def test_zookeeper_raise_exception_when_invalid_ssl(mock_kazoo_client):
    with pytest.raises(ValidationError):
        ZookeeperDatabase(
            ['https://127.0.0.1:2181', 'https://127.0.0.2:2181'],
            'zk_namespace',
            ssl=SSL(server_verify=123))


@patch('kazoo.client.KazooClient')
def test_zookeeper_pass_ssl_cert_as_string(mock_kazoo_client):
    ZookeeperDatabase(
        ['https://127.0.0.1:2181', 'https://127.0.0.2:2181'],
        'zk_namespace',
        ssl=SSL(server_verify='/path/to/sever_cert'))

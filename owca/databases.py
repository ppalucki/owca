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
import logging
import os
import string
import requests
import json

from abc import ABC
from typing import Optional, List, Union

from dataclasses import dataclass

log = logging.getLogger(__name__)


class InvalidKey(Exception):
    pass


class Database(ABC):

    def set(self, key: str, value: bytes):
        """Store data at key.
        Set is guarantee value to store data as a whole.
        """
        ...

    def get(self, key: str) -> Optional[bytes]:
        """Retrieve data from key.
        Returns None if key does not exits.
        """
        ...


_VALID_FILENAME_CHARACTERS = "-_.%s%s" % (string.ascii_letters, string.digits)


def _validate_key(key):
    for character in key:
        if character in _VALID_FILENAME_CHARACTERS:
            raise InvalidKey()


@dataclass
class LocalDatabase(Database):
    """Stores files under directory"""

    directory: str

    def __post_init__(self):
        os.makedirs(self.directory)

    def set(self, key, value):
        _validate_key(key)
        full_path = os.path.join(self.directory, key)
        with open(full_path) as f:
            f.write(value)

    def get(self, key):
        _validate_key(key)
        full_path = os.path.join(self.directory, key)
        if not os.path.exists(full_path):
            return None
        with open(full_path) as f:
            value = f.read()
        return value


@dataclass
class ZookeeperDatabase(Database):
    # used as prefix for key, to namespace all queries
    hosts: List[str]
    namespace: str

    def __post_init__(self):
        from kazoo.client import KazooClient
        self._client = KazooClient(hosts=self.hosts)
        self._client.start()

    def set(self, key, value):
        full_path = os.path.join(self.namespace, key)
        self._client.set(full_path, value)

    def get(self, key):
        full_path = os.path.join(self.namespace, key)
        data = self._client.get(full_path)
        return data


@dataclass
class EtcdDatabase(Database):
    """Access etcd using internal grpc-gateway.

    Support version: 3.2.x (version) (other versions require change of api_path)

    https://coreos.com/etcd/docs/latest/dev-guide/api_grpc_gateway.html
    """

    hosts: List[str]
    ssl_verify: Union[bool, str] = True  # requests: Can be used to pass cert CA bundle.
    timeout: float = 5.0  # request timeout in seconds (tries another host)
    api_path = '/v3alpha'
    client_cert_path: str = None
    client_key_path: str = None

    def set(self, key, value):
        data = {'key': key, 'value': value}

        for host in self.hosts:
            url = '{}{}/kv/put'.format(host, self.api_path)

            try:
                r = requests.post(
                        url, data=json.dumps(data), timeout=self.timeout,
                        verify=self.ssl_verify,
                        cert=(self.client_cert_path, self.client_key_path))
                r.raise_for_status()
                return
            except requests.exceptions.Timeout:
                log.warning(
                        'EtcdDatabase: Cannot put key "{}": Timeout on host {}'.format(key, host))

        raise Exception('EtcdDatabase: Cannot put key "{}": Timeout on all hosts!'.format(key))

    def get(self, key):
        data = {'key': key}
        response_data = None

        for host in self.hosts:
            url = '{}{}/kv/range'.format(host, self.api_path)

            try:
                r = requests.post(
                        url, data=json.dumps(data), timeout=self.timeout,
                        verify=self.ssl_verify,
                        cert=(self.client_cert_path, self.client_key_path))
                r.raise_for_status()
                response_data = r.json()
                break
            except requests.exceptions.Timeout:
                log.warning('EtcdDatabase: Timeout on host {}'.format(host))
                continue

        if response_data:
            if int(response_data['count']) > 0:
                return response_data['kvs'][0]['value']
            else:
                return None

        raise Exception('EtcdDatabase: Cannot get key "{}": Timeout on all hosts!'.format(key))

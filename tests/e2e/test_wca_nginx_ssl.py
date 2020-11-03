# Copyright (c) 2020 Intel Corporation
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

import requests
import pytest
import os

_CERT_FILE_PATH = '{pki_test_files_path}/{case}/server.crt'
_KEY_FILE_PATH = '{pki_test_files_path}/{case}/server.key'
_CA_CERT_FILE_PATH = '{pki_test_files_path}/CA.crt'
_URL = 'https://{ip}:{port}/status'


@pytest.mark.parametrize('cert_name', [
    'correct-cert',
])
def test_wca_nginx_ssl_correct_cert(cert_name):
    assert 'KUBERNETES_HOST' in os.environ
    assert 'PORT_WCA_SCHEDULER' in os.environ
    assert 'PKI_TEST_FILES_PATH' in os.environ

    ip = os.environ['KUBERNETES_HOST']
    port = os.environ['PORT_WCA_SCHEDULER']
    pki_test_files_path = os.environ['PKI_TEST_FILES_PATH']

    cert = (_CERT_FILE_PATH.format(pki_test_files_path=pki_test_files_path, case=cert_name),
            _KEY_FILE_PATH.format(pki_test_files_path=pki_test_files_path, case=cert_name))
    r = requests.get(_URL.format(ip=ip, port=port), cert=cert, verify=False)
    assert "true" in r.text


@pytest.mark.parametrize('cert_name', [
    'attribute-expiration-date-past',
    'attribute-expiration-date-issued-too-early',
    'attribute-purpose',
    'self-signed-cert',
    'signed-by-another-CA',
])
def test_wca_nginx_ssl_incorrect_cert(cert_name):
    assert 'KUBERNETES_HOST' in os.environ
    assert 'PORT_WCA_SCHEDULER' in os.environ
    assert 'PKI_TEST_FILES_PATH' in os.environ

    ip = os.environ['KUBERNETES_HOST']
    port = os.environ['PORT_WCA_SCHEDULER']
    pki_test_files_path = os.environ['PKI_TEST_FILES_PATH']

    cert = (_CERT_FILE_PATH.format(pki_test_files_path=pki_test_files_path, case=cert_name),
            _KEY_FILE_PATH.format(pki_test_files_path=pki_test_files_path, case=cert_name))
    r = requests.get(_URL.format(ip=ip, port=port), cert=cert, verify=False)
    assert "The SSL certificate error" in r.text

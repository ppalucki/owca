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


from unittest.mock import patch
from wca.config import ValidationError
import pytest

import wca.security


@patch('wca.security.LIBC.capget', return_value=-1)
@patch('os.geteuid', return_value=1000)
def test_privileges_failed_capget(mock_geteuid, mock_capget):
    with pytest.raises(wca.security.GettingCapabilitiesFailed):
        wca.security.are_privileges_sufficient()


@patch('wca.security.log.error')
@patch('os.geteuid', return_value=1000)
@patch('wca.security._get_capabilities', return_value=wca.security.UserCapDataStruct(0, 0, 0))
@patch('wca.security._get_securebits', return_value=0)
@patch('wca.security._read_paranoid', return_value=1)
@pytest.mark.parametrize(
        'use_cgroup, use_resctrl, use_perf, expected_log', [
            (True, True, True,
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_DAC_OVERRIDE set. CAP_SETUID and SECBIT_NO_SETUID_FIXUP '
             'set. "/proc/sys/kernel/perf_event_paranoid" set to (0 or -1).'),
            (False, True, True,
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_SETUID and SECBIT_NO_SETUID_FIXUP set.'
             ' "/proc/sys/kernel/perf_event_paranoid" set to (0 or -1).'),
            (True, False, True,
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_DAC_OVERRIDE set.'
             ' "/proc/sys/kernel/perf_event_paranoid" set to (0 or -1).'),
            (True, True, False,
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_DAC_OVERRIDE set. CAP_SETUID and SECBIT_NO_SETUID_FIXUP '
             'set.'),
            ])
def test_privileges_failed(mock_read_paranoid, mock_get_securebits, mock_get_capabilities,
                           mock_getuid, mock_log, use_cgroup, use_resctrl, use_perf, expected_log):
    assert not wca.security.are_privileges_sufficient(use_cgroup, use_resctrl, use_perf)

    mock_log.assert_called_with(expected_log)


@patch('wca.security.log.error')
@patch('os.geteuid', return_value=1000)
@patch('wca.security._get_capabilities', return_value=wca.security.UserCapDataStruct(130, 0, 0))
@patch('wca.security._get_securebits', return_value=12)
@patch('wca.security._read_paranoid', return_value=-1)
@pytest.mark.parametrize(
        'use_cgroup, use_resctrl, use_perf', [
            (True, True, True),
            (False, True, True),
            (True, False, True),
            (True, True, False),
        ])
def test_privileges_successful(mock_read_paranoid, mock_get_securebits, mock_get_capabilities,
                               mock_getuid, mock_log, use_cgroup, use_resctrl, use_perf):
    assert wca.security.are_privileges_sufficient(use_cgroup, use_resctrl, use_perf)

    mock_log.assert_not_called()


@patch('wca.security.log.error')
@patch('os.geteuid', return_value=1000)
@patch('wca.security._get_capabilities', return_value=wca.security.UserCapDataStruct(128, 0, 0))
@patch('wca.security._get_securebits', return_value=12)
@patch('wca.security._read_paranoid', return_value=-1)
def test_privileges_failed_no_cap_dac_override(mock_read_paranoid, mock_get_securebits,
                                               mock_get_capabilities, mock_getuid, mock_log):
    assert not wca.security.are_privileges_sufficient(True, True, True)

    mock_log.assert_called_with(
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_DAC_OVERRIDE set.')


@patch('wca.security.log.error')
@patch('os.geteuid', return_value=1000)
@patch('wca.security._get_capabilities', return_value=wca.security.UserCapDataStruct(2, 0, 0))
@patch('wca.security._get_securebits', return_value=4)
@patch('wca.security._read_paranoid', return_value=-1)
def test_privileges_failed_no_cap_setuid_fixup_bit(mock_read_paranoid, mock_get_securebits,
                                                   mock_get_capabilities, mock_getuid, mock_log):
    assert not wca.security.are_privileges_sufficient(True, True, True)

    mock_log.assert_called_with(
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_SETUID and SECBIT_NO_SETUID_FIXUP set.')


@patch('wca.security.log.error')
@patch('os.geteuid', return_value=1000)
@patch('wca.security._get_capabilities', return_value=wca.security.UserCapDataStruct(130, 0, 0))
@patch('wca.security._get_securebits', return_value=0)
@patch('wca.security._read_paranoid', return_value=-1)
def test_privileges_failed_cap_setuid_no_fixup_bit(mock_read_paranoid, mock_get_securebits,
                                                   mock_get_capabilities, mock_getuid, mock_log):
    assert not wca.security.are_privileges_sufficient(True, True, True)

    mock_log.assert_called_with(
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: CAP_SETUID and SECBIT_NO_SETUID_FIXUP set.')


@patch('wca.security.log.error')
@patch('os.geteuid', return_value=1000)
@patch('wca.security._get_capabilities', return_value=wca.security.UserCapDataStruct(130, 0, 0))
@patch('wca.security._get_securebits', return_value=4)
@patch('wca.security._read_paranoid', return_value=2)
def test_privileges_failed_perf_event_paranoid_set(mock_read_paranoid, mock_get_securebits,
                                                   mock_get_capabilities, mock_getuid, mock_log):
    assert not wca.security.are_privileges_sufficient(True, True, True)

    mock_log.assert_called_with(
             'Insufficient privileges! For unprivileged user '
             'it is needed to have: "/proc/sys/kernel/perf_event_paranoid" set to (0 or -1).')


def test_privileges_return_true_no_permissions_needed():
    assert wca.security.are_privileges_sufficient(False, False, False)


def test_ssl_error_only_client_key():
    """Tests that SSL throws ValidationError when only client key path is provided."""
    with pytest.raises(ValidationError):
        wca.security.SSL(client_key_path='/key')


def test_ssl_accept_single_file():
    """Tests that SSL accepts single file with client certificate and key."""
    wca.security.SSL(client_cert_path='/cert.pem')


def test_ssl_get_client_certs_single_file():
    """Tests that get_client_certs() returns file path with client certificate and key."""
    ssl = wca.security.SSL(client_cert_path='/cert.pem')
    assert ssl.client_key_path is None
    assert ssl.get_client_certs() == '/cert.pem'


def test_ssl_get_client_certs_tuple():
    """Tests that get_client_certs() returns tuple with client certificate and key paths."""
    ssl = wca.security.SSL(client_cert_path='/cert', client_key_path='/key')
    assert ssl.get_client_certs() == ('/cert', '/key')

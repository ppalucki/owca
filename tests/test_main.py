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

import os

from unittest.mock import Mock, mock_open, patch, call

from wca import main


yaml_config = '''
runner: !DummyRunner
'''


@patch('sys.argv', ['wca', '-c',
                    '/etc/configs/see_yaml_config_variable_above.yaml',
                    '-r', 'tests.testing:DummyRunner', '-l', 'critical',
                    '--root'])
@patch('os.rmdir')
@patch('wca.config.exists', return_value=True)
@patch('wca.config.open', mock_open(read_data=yaml_config))
@patch('wca.perf.PerfCounters')
@patch('wca.main.exit')
@patch('os.stat', return_value=Mock(st_size=35, st_uid=0, st_mode=700))
def test_main(*mocks):
    main.main()


yaml_config_unknown_field = '''
unknownRunner: !DummyRunner
runner: !DummyRunner
'''


@patch('wca.main.log.error')
@patch('sys.argv', ['wca', '-c',
                    '/etc/configs/see_yaml_config_variable_above.yaml',
                    '-r', 'tests.testing:DummyRunner', '-l', 'critical',
                    '--root'])
@patch('os.rmdir')
@patch('wca.config.exists', return_value=True)
@patch('wca.config.open', mock_open(
    read_data=yaml_config_unknown_field))
@patch('wca.perf.PerfCounters')
@patch('wca.main.exit')
@patch('wca.main.valid_config_file')
def test_main_unknown_field(mock_valid_config_file, mock_exit, perf_counters, mock_rmdir,
                            mock_argv, mock_log_error):
    main.main()
    mock_log_error.assert_called_once_with('Error: Unknown fields in '
                                           'configuration file!'
                                           ' Possible are: \'loggers\', '
                                           '\'runner\'')


@patch('wca.main.log.error')
@patch('wca.main.exit')
@patch('wca.main.os.stat', return_value=Mock(st_size=35, st_uid=os.geteuid(), st_mode=384))
def test_main_valid_config_file_not_absolute_path(os_stat, mock_exit, mock_log_error):
    main.valid_config_file('configs/see_yaml_config_variable_above.yaml')

    assert call('Error: The config path is not valid. '
                'The path must be absolute.') in mock_log_error.mock_calls


TEST_USER_UID = 1001


@patch('wca.main.log.error')
@patch('wca.main.exit')
@patch('os.stat', return_value=Mock(st_size=35, st_uid=123123, st_mode=384))
@patch('os.getuid', return_value=TEST_USER_UID)
def test_main_valid_config_file_wrong_user(os_getuid, os_stat, mock_exit, mock_log_error):
    main.valid_config_file('/etc/configs/see_yaml_config_variable_above.yaml')

    assert call('Error: The config is not valid. '
                'User is not owner of the config or is not root.') in mock_log_error.mock_calls


@patch('wca.main.log.error')
@patch('wca.main.exit')
@patch('os.stat', return_value=Mock(st_size=35, st_uid=TEST_USER_UID, st_mode=466))
@patch('os.getuid', return_value=TEST_USER_UID)
def test_main_valid_config_file_wrong_acl(os_getuid, os_stat, mock_exit, mock_log_error):
    # st_mode=511 - All can read, write and exec

    main.valid_config_file('/etc/configs/see_yaml_config_variable_above.yaml')

    mock_log_error.assert_called_with(
        'Error: The config is not valid. It does not have correct ACLs. '
        'Only owner should be able to write (Hint: try chmod og-rwto fix the problem).'
    )

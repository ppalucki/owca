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


from unittest import mock

from owca import main

yaml_config = '''
runner: !DummyRunner
'''


@mock.patch('sys.argv', ['owca', '-c', 'configs/see_yaml_config_variable_above.yaml',
                         '-r', 'owca.testing:DummyRunner', '-l', 'critical',
                         '--root'])
@mock.patch('os.rmdir')
@mock.patch('owca.config.exists', return_value=True)
@mock.patch('owca.config.open', mock.mock_open(read_data=yaml_config))
@mock.patch('owca.perf.PerfCounters')
@mock.patch('owca.main.exit')
def test_main(*mocks):
    main.main()

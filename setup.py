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


from setuptools import setup, find_packages

setup(
    name='owca',
    author='Intel',
    description='Orchestration-aware Workload Collocation Agent',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Distributed Computing',
    ],
    install_requires=[
          'requests==2.21.0',          # 2018.12.10
          'ruamel.yaml==0.15.89',      # 2019.02.27
          'colorlog==4.0.2',           # 2018.12.14
          'logging-tree==1.8',         # 2018.08.05
          'dataclasses==0.6',          # 2018.05.18
          'confluent-kafka==1.0.0rc1', # 2018.10.31
          'setuptools==40.8.0'         # 2019.02.05
    ],
    tests_require=[
          'pytest==4.3.0'           # 2019.02.18
          'pytest-cov==2.6.1',      # 2019.01.07
          'flake8==3.7.7'           # 2019.02.25
    ],
    setup_requires=[
        'setuptools_scm==3.2.0'     # 2019.01.16
    ],
    packages=find_packages(),
    python_requires=">=3.6",
    use_scm_version=True,
)

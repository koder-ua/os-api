# Copyright 2015 kdanilov aka koder. koder.mail@gmail.com
# https://github.com/koder-ua
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'concurrent.future based openstack api',
    'author': 'kdanilov aka koder',
    'url': 'https://github.com/koder-ua/os_api',
    # 'download_url': 'Where to download it.',
    'author_email': 'kdanilov@mirantis.com',
    'version': '0.1',
    'install_requires': ['futures'],
    'packages': ['os_api'],
    'scripts': [],
    'name': 'os_api'
}

setup(**config)

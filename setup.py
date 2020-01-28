# -*- coding: utf-8 -*-

import os
import re
import time

import setuptools

# root path
ROOT = os.path.dirname(os.path.realpath(__file__))

# README
with open(os.path.join(ROOT, 'README.md'), encoding='utf-8') as file:
    __doc__ = file.read()

# version string
__version__ = time.strftime('%Y.%m.%d')

# setup kwargs
setup_kwargs = dict(
    name='pydl',
    version=__version__,
    description='Video Downloader',
    long_description=__doc__,
    long_description_content_type='text/markdown',
    python_requires='>=3.8',
    py_modules=['dl_add', 'dl_get'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests',
    ],
    dependency_links=[
        'https://pypi.tuna.tsinghua.edu.cn/simple',
        'https://mirrors.sjtug.sjtu.edu.cn/pypi/web/simple',
        'https://pypi.org/simple',
    ],
    entry_points={
        'console_scripts': [
            'dl-add = dl_add:main',
            'dl-get = dl_get:main',
        ],
    },
)

# set-up script for pip distribution
setuptools.setup(**setup_kwargs)

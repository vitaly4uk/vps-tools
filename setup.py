#!/usr/bin/env python
import os
from setuptools import setup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'vps_tools', '__init__.py'), 'r') as version_file:
    _, version = version_file.read().split("=")

setup(
    name='vps_tools',
    version=version[1:-1].strip(),
    packages=['vps_tools'],
    url='https://github.com/vitaly4uk/vps_tools',
    license='GPL v3',
    author='Vitalii Omelchuk',
    author_email='vitaly.omelchuk@gmail.com',
    description='',
    install_requires=['fabric', 'dj_database_url', 'six', 'gitpython'],
    entry_points={
        'console_scripts': ['hmara = vps_tools.hmara:main']
    }
)

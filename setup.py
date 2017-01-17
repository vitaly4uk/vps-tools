#!/usr/bin/env python
from setuptools import setup

with open('vps_tools/VERSION', 'r') as version_file:
    version = version_file.read()

setup(
    name='vps_tools',
    version=version,
    packages=['vps_tools'],
    url='https://github.com/vitaly4uk/vps_tools',
    license='GPL v3',
    author='Vitalii Omelchuk',
    author_email='vitaly.omelchuk@gmail.com',
    description='',
    data_files=[
        ('/var/lib/vps_tools', [
            'vps_tools/templates/nginx.conf',
            'vps_tools/templates/supervisord.conf',
            'vps_tools/VERSION'
        ])
    ],
    install_requires = ['fabric'],
    scripts = ['hmara']
)

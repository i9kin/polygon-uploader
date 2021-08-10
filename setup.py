#!/usr/bin/env python
from setuptools import find_packages, setup

requirements = [
    'polygon_api',
    'camelot-py',
    'rich',
    'click',
    'PyInquirer',
]

setup(
    name='polygon-uploader',
    author='9kin',
    version='1.0',
    packages=['polygon_uploader'],
    url='https://github.com/9kin/polygon-uploader',
    license='MIT',
    description='Upload polygon packages without headaches',
    install_requires=requirements,
    entry_points={
        'console_scripts': ['polygon-uploader=polygon_uploader.cli:main'],
    },
)

#! /usr/bin/env python

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import json2xml



def publish():
    """Publish to PyPi"""
    os.system("python setup.py sdist upload")

if sys.argv[-1] == "publish":
    publish()
    sys.exit()

required = ['dict2xml']

setup(
    name='json2xml',
    version=json2xml.__version__,
    description='Python Command-line Application Tools',
    long_description=open('README.md').read() + '\n\n' +
                     open('HISTORY.md').read(),
    author='Vinit Kumar',
    author_email='vinit.kumar@changer.nl',
    url='https://github.com/vinitcool76/json2xml',
    data_files=[
        'README.md',
        'HISTORY.md',
    ],
    install_requires=required,
    license='MIT',
    classifiers=(
#       'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Topic :: Terminals :: Terminal Emulators/X Terminals',
    ),
)

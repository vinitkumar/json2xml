#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
from json2xml import __version__

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [open("requirements.txt").read()]

setup_requirements = []

test_requirements = ["pytest==7.0.1", "py==1.11.0"]

setup(
    author="Vinit Kumar",
    author_email="mail@vinitkumar.me",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    description="Simple Python Library to convert JSON to XML",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    keywords="json2xml",
    name="json2xml",
    packages=find_packages(include=["json2xml"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/vinitkumar/json2xml",
    version=__version__,
    zip_safe=False,
)

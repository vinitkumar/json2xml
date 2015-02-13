from setuptools import setup, find_packages
import os

version = '1.0.0'

setup(
    name='json2xml',
    version=version,
    description='To covert json data to xml data',
    author='Vinit Kumar',
    author_email='vinit.kumar@changer.nl',
    url='http://github.com:vinitkumar/json2xml.git',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=open(os.path.join(os.path.dirname(__file__),
         'requirements.txt')).read().split(),
)

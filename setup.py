from setuptools import setup, find_packages
import os

version = '1.0.1'

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
    install_requires=['BeautifulSoup==3.2.1',
                      'argparse==1.2.1',
                      'dict2xml==1.3',
                      'gnureadline==6.3.3',
                      'simplejson==3.6.5',
                      'six==1.9.0',
                      'wsgiref==0.1.2'],
)

from setuptools import setup, find_packages
import os

version = '1.2.2'

setup(
    name='json2xml',
    version=version,
    description='To convert json data to xml data',
    author='Vinit Kumar',
    author_email='vinit.kumar@changer.nl',
    url='https://github.com/vinitkumar/json2xml',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['BeautifulSoup4==4.4.1',
                      'dict2xml==1.3',
                      'simplejson==3.6.5',
                      'six==1.10.0',
                      'lxml',
                      ],
)

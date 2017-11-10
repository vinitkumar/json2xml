from setuptools import setup, find_packages

version = '1.3.0'

setup(
    name='json2xml',
    version=version,
    description='A simple python package to convert json from file, URL or string to xml data',
    author='Vinit Kumar',
    author_email='vinit1414.08@bitmesra.ac.in',
    url='https://github.com/vinitkumar/json2xml',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['BeautifulSoup4==4.5.3',
                      'dict2xml==1.5',
                      'simplejson==3.10.0',
                      'six==1.10.0',
                      'lxml==3.7.3',
                      'requests==2.13.0',
                      ],
)

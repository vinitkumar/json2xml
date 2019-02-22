from setuptools import setup, find_packages

version = '2.3.0'

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
    install_requires=[
                      'dict2xml==1.5',
                      'six==1.11.0',
                      'requests>=2.20.0',
                      'xmltodict==0.11.0'
                      ],
)

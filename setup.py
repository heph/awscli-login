#!/usr/bin/env python
import sys
from setuptools import setup, find_packages, Command
import awslogin

requires = [
  'awscli==1.8.7',
  'requests',
  'beautifulsoup4'
]

setup(
    name='awslogin',
    version=awslogin.__version__,
    description='AWSCLI Temporary Credentials plugin',
    author='Steve Adams',
    url='http://aws.amazon.com/cli/',
    packages=find_packages('.', exclude=['tests*']),
    package_dir={'awslogin': 'awslogin'},
    install_requires=requires,
    license="Apache License 2.0",
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    )
)


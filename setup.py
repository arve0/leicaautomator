#!/usr/bin/env python

import os
import sys
from setuptools import setup


os.system('make rst')
try:
    readme = open('README.rst').read()
except FileNotFoundError:
    readme = ""

setup(
    name='leicaautomator',
    version='0.0.1',
    description='Automate scans on Leica SPX microscopes',
    long_description=readme,
    author='Arve Seljebu',
    author_email='arve.seljebu@gmail.com',
    url='https://github.com/arve0/leicaautomator',
    packages=[
        'leicaautomator',
    ],
    package_dir={'leicaautomator': 'leicaautomator'},
    include_package_data=True,
    install_requires=[
        'scikit-image',
        'numpy',
        'matplotlib',
        'PySide',
        'leicascanningtemplate',
    ],
    license='MIT',
    zip_safe=False,
    keywords='leicaautomator',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)

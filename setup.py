#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from setuptools import setup

setup(name='tlc-cmd',
    version='1.0.3',
    author='Ruize Tang',
    author_email='tangruize97@gmail.com',
    url='https://github.com/tangruize/tlc-cmd',
    description='TLC cmd tools',
    packages=['.'],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: MIT License',
    ],
    package_data = {
        '':['*.ini']
    },
    install_requires=['requests', 'psutil', 'networkx'],
    python_requires='>=3',
    scripts=['tlcwrapper.py', 'trace_reader.py', 'trace_counter.py',
             'trace_generator.py']
)

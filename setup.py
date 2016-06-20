"""
Source build and installation script.
"""

import os.path

from pip.download import PipSession
from pip.req import parse_requirements
from setuptools import setup, find_packages


def extract_requirements(filename):
    return [str(r.req) for r in parse_requirements(filename, session=PipSession())]


# load metadata
base_dir = os.path.dirname(__file__)

with open(os.path.join(base_dir, 'README.rst')) as f:
    long_description = f.read()

install_requires = extract_requirements('requirements.txt')
tests_require = extract_requirements('requirements-test.txt')

setup(
    name='ghstats',
    version="0.0.1-dev",
    url='https://github.com/joshainglis/github-commit-stats',
    license='MIT',
    author='Josha Inglis',
    author_email='joshainglis@gmail.com',
    description='',
    long_description=long_description,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: MIT',
        'Programming Language :: Python',
    ],
    packages=find_packages(),
    install_requires=install_requires,
    scripts=['bin/ghstats'],
    tests_require=tests_require,
)

import sys

from setuptools import find_packages, setup


with open('VERSION') as version_fp:
    VERSION = version_fp.read().strip()


with open('README.md') as readme_fp:
    long_description = readme_fp.read()


install_requires = [
    'six',
]
if sys.version_info[:2] < (3, 0):
    install_requires.append('configparser')
if sys.version_info[:2] < (2, 7):
    install_requires.append('argparse')


setup(
    name='django-local-settings',
    version=VERSION,
    author='Wyatt Baldwin',
    author_email='wbaldwin@pdx.edu',
    url='https://github.com/PSU-OIT-ARC/django-local-settings',
    description='A system for dealing with local settings in Django projects',
    long_description=long_description,
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'dev': [
            'coverage>=4',
            # NOTE: Keep this Django version up to date with latest the
            #       Django release; use tox for more thorough testing.
            'django>=1.9,<1.10',
            'flake8',
            'tox>=2.3.1',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    entry_points="""
    [console_scripts]
    make-local-settings = local_settings:make_local_settings

    """,
)

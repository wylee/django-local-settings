import sys

from setuptools import find_packages, setup


with open('README.md') as fp:
    long_description = fp.read()


install_requires = [
    'six',
]
if sys.version_info[:2] < (2, 7):
    install_requires += [
        'argparse',
        'configparser',
    ]


setup(
    name='django-local-settings',
    version='1.0a2',
    author='Wyatt Baldwin',
    author_email='wyatt.baldwin@pdx.edu',
    url='https://github.com/PSU-OIT-ARC/django-local-settings',
    description='A system for dealing with local settings in Django projects',
    long_description=long_description,
    packages=find_packages(),
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    entry_points="""
    [console_scripts]
    make-local-settings = local_settings:make_local_settings

    """,
)

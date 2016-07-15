import sys

from setuptools import find_packages, setup


py_version = sys.version_info[:2]


with open('VERSION') as version_fp:
    VERSION = version_fp.read().strip()


with open('README.md') as readme_fp:
    long_description = readme_fp.read()


install_requires = [
    'six',
]

if py_version < (3, 0):
    install_requires.append('configparser')

# NOTE: Keep this Django version up to date with the latest Django
#       release that works for the versions of Python we support.
#       This is used to get up and running quickly; tox is used to test
#       all supported Python/Django version combos.
if py_version == (3, 3):
    django_spec = 'django>=1.8,<1.9',
else:
    django_spec = 'django>=1.9,<1.10',


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
            django_spec,
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

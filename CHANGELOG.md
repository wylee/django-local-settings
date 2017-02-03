# Change Log for django-local-settings

## 1.0b4 - 2017-02-03

- Add support for Django 1.10. Note in the README that it's supported, install
  it by default in development, and add it to tox.ini.
- Start supporting Python 3.6 and Django 1.11. This is provisional for the time
  being since Django 1.11 is still in alpha.
- Improve some internal bits in the `Settings` class.
- Improve tox config; test all Django versions for each Python version in order.

## 1.0b3 - 2017-01-19

- Added `PREPEND` settings prefix because sometimes items need to be added to
  the beginning of a list, not the end (e.g., `MIDDLEWARE_CLASSES` is a good
  example of this).
- Renamed `EXTRA` settings prefix to `APPEND`; this is more precise and mirrors
  `PREPEND`.
- Keep settings in order when reading from file. When reading INI files, take
  care to order items from the `[DEFAULT]` section before the items in the
  specified section. This change *should* allow the `SWAP` prefix to be
  removed (but we'll keep it for now).
- In derived settings files, don't require an empty section to be present if
  the section is present in a base settings file. It's nice to not have to add
  empty sections to a derived settings file for sections that don't have any
  overridden options.

## 1.0b2 - 2016-10-21

- Added support for copying and pickling to `Settings` class.
- Improved setup.py.

## 1.0b1 - 2016-07-15

First beta version. Additions, changes, and fixes will be noted from here on
out.

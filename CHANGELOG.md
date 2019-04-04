# Change Log for django-local-settings

## 1.0b10 - 2019-04-04

- Made settings file/section inheritance more intuitive. This change is
  backward incompatible but is, I think, unlikely to cause issues in
  most cases because previously the workaround for the unintuitive way
  inheritance worked was to add redundant settings in extending
  sections. See ba09782e0608a47fe53f24d30ea7750acb0c4b0b.

## 1.0b9 - 2018-10-08

- Added support for Python 3.7.
- Fixed regression in 1.0b8 that causes spaces around names in
  interpolation groups to throw an error.
- Made various changes to internals to better support loading from alternative
  types of settings files, YAML in particular (which is a work-in-progress in
  a separate branch).
- Default local settings file is now discovered based on supported file
  types instead of unconditionally using "local.cfg".
- The settings file loading strategy is now based on the name of the specified
  local settings file instead of unconditionally using the INI/JSON loading
  strategy.
- Mutable vs. non-mutable mappings are now handled separately when
  interpolating.
- Simplified internals of loader, esp. wrt. decoding values & interpolation.

## 1.0b8 - 2018-01-13

- Added a mechanism for deleting settings via the `DELETE` setting (a
  list containing dotted paths of settings to remove). This can be used
  to remove settings that are common to most environments from a special
  environment (such as testing).
- Added `Settings.pop_dotted()` (this was actually added to
  `DottedAccessMixin`, but it's normally used via `Settings`).
- Updated settings path-parsing internals to use a stack.
- Updated settings injection/interpolation logic to use a stack.
- The previous two items enable nested interpolation in settings paths
  and values (like `{{X.{{Y}}}}`).
- When a member of a list-type setting isn't found, an `IndexError` will
  now be raised. Previously, the `IndexError` would be caught and
  a `KeyError` would be raised instead, but that's incosistent and could
  be confusing.

## 1.0b7 - 2017-07-06

- [#4] Fixed a bug with loading/interpolation of tuples (and other non-mutable
  sequences).
- Declared official support for Django 1.11.

## 1.0b6 - 2017-02-28

- Enable interpolation of all types of settings values, not just strings. For
  example, the following now works as expected:

      ITEMS = ["a", "b", "c"]
      SOMETHING.x.y.z = {{ITEMS}}

  `SOMETHING.x.y.z` will be equal to `["a", "b", "c"]` after interpolation.
  Previously, this would cause an error when the settings file was parsed.

## 1.0b5 - 2017-02-06

- Moved the functionality for accessing nested items via dotted names
  from `Settings` to a new class, `DottedAccessMixin`. This allows the
  dotted access functionality to be reused without having to create
  `Settings` objects in cases where that's not needed.
- Added a default/example `DottedAccessDict`. An existing dict can be
  wrapped with this to easily get dotted access.
- Fixed tox config, which revealed a couple issues on Python 2.7, which
  were fixed (`raise from` and `super()` without args).

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

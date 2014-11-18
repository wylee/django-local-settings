# Local settings for Django projects

This package attempts to solve the problem of handling local settings in Django projects. Local
settings by definition can't be pre-defined, although perhaps they can have a reasonable default
value (mainly useful for development). Another class of local settings are *secret* settings; these
definitely shouldn't be pre-defined and should never be added to version control.

The problems with local settings are:

- How to specify which settings are local
- How to inform others which settings are local (or secret)
- How to actually give the local settings a value
- How to verify that local settings have been given a valid value
- How to ensure new local settings get set
- How to ensure local (and esp. secret) settings don't get added to version control

One common approach is to create a local settings template module with dummy/default values. When
new developers start working on a project, they copy this file (e.g., `local_settings.py.template =>
local_settings.py`), which is typically excluded from version control. This approach at least
identifies which settings are local, but it's not very convenient with regard to setting values and
ensuring those values are valid. Also, instead of giving you a friendly heads-up when you forget to
set a local setting, it barfs out an exception.

This package takes the approach that there will be only one settings *module* per project in the
standard location: `{project}.settings`. That module defines/overrides Django's base settings in the
usual way *plus* it defines which settings are local and which are secret.

In addition to the settings module, there will be one or more settings *files*. These are standard
INI files with the added twist that the values are JSON encoded. The reasoning behind this is to use
a simple, standard config file format while still allowing for easy handling of non-string settings.

TODO: Maybe add support for different config file format (e.g., YAML)?

Once the local settings are defined, *any missing settings will be prompted for in the console*
(with pretty colors and readline support).

## Features

- Missing local settings will be prompted for (only when running on a TTY/console)
- Local settings can be defined with validators
- Local settings can be defined with doc strings
- Local settings can be nested in settings lists and dicts
- Settings files can extend from each other
- Includes a script to easily generate local settings files for different environments
- Supports Python 2.6 - 3.4 (using [six](http://pythonhosted.org/six/))

## Basic usage

- At the bottom of your project's settings module, define some local settings:

        DEBUG = LocalSetting(default=False)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.<some back end>',
                'NAME': LocalSetting(default='default db name for development'),
                'USER': LocalSetting(''),
                'PASSWORD': SecretSetting(),
                'HOST': LocalSetting(''),
                'PORT': '',
            },
        }
        SECRET_KEY = SecretSetting(doc='The secret key for doing secret stuff')
    
    As you can see, local settings can be defined anywhere within the definition of a top level
    setting. They can also have doc strings, which are displayed when prompting.

- After all the local settings are defined, add this line:

        load_and_check_settings(globals())
    
    When this line runs, it will load local settings from a file (`$CWD/local.cfg` by default) and
    prompt for any that are missing. When not running on a TTY/console, missing local settings will
    cause an exception to be raised.
    
    After this line runs, you will be able to use the local settings just like any other settings.
    For example, you could do `if DEBUG: ...`; at this point, `DEBUG` is no longer a `LocalSetting`
    instance--it's a regular old bool.

- Now you can run any manage.py command, and you will be prompted to enter any missing local
  settings. On the first run, the settings file will be created. On subsequent runs when new local
  settings are added to the settings module, the settings file will be appended to.
  
- Alternatively, you can run the included `make-local-settings` script to generate a local settings
  file.

## Advanced usage

TODO: Discuss using multiple settings files, extending a settings file from another file, how to
specify a settings file other than the default of `local.cfg`, editing settings files directly, &c.

# Local settings for Django projects

This package provides a couple different ways to handle local settings
in Django projects:

1. Using environment variables
2. Using settings files

## General Features

- Supports Python 3.7 - 3.10
- Supports Django 2.0 - 4.1
- Local settings can be defined with validators and doc strings
- Local settings can be nested inside lists and dicts
- Settings can be injected into other settings using Django template
  syntax

## Using Environment Variables

In your project's Django settings module, define which settings should
be loaded from environment variables:

    from local_settings import inject_settings, EnvSetting

    SECRET_KEY = EnvSetting("SECRET_KEY")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": EnvSetting("DATABASE_NAME"),
            "USER": EnvSetting("DATABASE_USER"),
            "PASSWORD": EnvSetting("DATABASE_PASSWORD"),
            "HOST": EnvSetting("DATABASE_HOST"),
        },
    }

    # ... other Django settings ...

    inject_settings(env_only=True)

Then create an *untracked* `.env` file that sets the corresponding
environment variables like so:

    SECRET_KEY="very secret key"
    DATABASE_NAME="dev_db"
    ...

In development, the `.env` file should be in your Django project root
next to `manage.py`.

## Using a Settings File

Another approach to local settings is to use a settings file--an INI
file where the values are JSON-encoded.

When using a settings file, some additional features are available

- Local settings can be defined with defaults
- When running interactively (e.g., when running `./manage.py
  runserver`), missing settings will be prompted for
- The included `make-local-settings` script can be used to generate
  local settings files
- A settings file can extend from a base settings file

In your project's Django settings module, define which settings should
be loaded from a settings file:

    from local_settings import inject_settings, LocalSetting, SecretSetting

    from django.core.management import utils

    # This is used to demonstrate interpolation.
    PACKAGE = "local_settings"

    DEBUG = LocalSetting(default=False)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": LocalSetting(default="{{ PACKAGE }}"),
            "USER": LocalSetting(default="{{ PACKAGE }}"),
            "PASSWORD": SecretSetting(),
            "HOST": LocalSetting(default="localhost"),
            "PORT": "",
        },
    }

    # If a secret setting specifies a default, it must be a callable
    # that generates the value; this discourages using the same
    # secret in different environments.
    SECRET_KEY = SecretSetting(
        default=utils.get_random_secret_key,
        doc="The secret key for doing secret stuff",
    )

    # ... other Django settings ...

    inject_settings()

Then create an *untracked* `local.cfg` file with values for the settings
like so:

    DEBUG = false
    DATABASES.default.PASSWORD = "database password"

In development, the `local.cfg` file should be in your Django project
root next to `manage.py`.

You can also use the environment variable `LOCAL_SETTINGS_FILE` to
specify a different local settings file.

## Historical note

The initial commit of this package was made on October 22, 2014, and the
first release was published to [PyPI] on March 11, 2015. At the time,  I
didn't know about TOML. Otherwise, I probably (maybe?) would have found
a way to use TOML for Django settings.

[PyPI]: https://pypi.org/project/django-local-settings/

When I heard about TOML--I think related to `pyproject.toml` becoming
a thing--I remember thinking it was quite similar to this package (or
vice versa), especially the splitting of dotted names into dictionaries
and the use of "rich" values rather than plain text.

One of the biggest differences, besides this package being
Django-specific, is interpolation of both values *and* keys, which I
find handy (more for values, but occasionally for keys.)

Another difference is that with TOML the config file section name
becomes part of the dictionary structure, whereas in
`django-local-settings` it doesn't. In that regard,
`django-local-settings` is more geared toward environments, such as a
development and production.

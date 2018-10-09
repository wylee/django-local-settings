import sys
from collections import Mapping, Sequence

from six import string_types
from six.moves import input

from .base import Base
from .color_printer import color_printer as printer
from .types import LocalSetting
from .util import NO_DEFAULT, is_a_tty


class Checker(Base):

    def __init__(self, file_name, section=None, registry=None, strategy_type=None, prompt=None):
        super(Checker, self).__init__(file_name, section, registry, strategy_type)
        if prompt is None:
            try:
                prompt = is_a_tty(sys.stdin) and is_a_tty(sys.stdout)
            except AttributeError:
                prompt = False
        self.prompt = prompt

    def check(self, obj, prefix=None):
        """Recursively look for :class:`.LocalSetting`s in ``obj``.

        ``obj`` can be a dict, tuple, or list. Other types are skipped.

        This will prompt to get the value of local settings (excluding
        those that have had prompting disabled) that haven't already
        been set locally.

        Returns ``True`` or ``False`` to indicate whether settings were
        successfully checked.

        """
        self._populate_registry(obj, prefix)
        settings_to_write, missing = self._check(obj, prefix, {}, {})
        if settings_to_write:
            self.strategy.write_settings(settings_to_write, self.file_name, self.section)
        if missing:
            for name, local_setting in missing.items():
                printer.print_error('Local setting `{name}` must be set'.format(name=name))
            return False
        return True

    def _populate_registry(self, obj, prefix=None):
        if isinstance(obj, Mapping):
            items = obj.items()
        elif isinstance(obj, Sequence) and not isinstance(obj, string_types):
            items = zip(range(len(obj)), obj)
        else:
            return
        for k, v in items:
            name = k if prefix is None else '{0}.{1}'.format(prefix, k)
            if not isinstance(v, LocalSetting):
                self._populate_registry(v, name)
            else:
                self.registry[v] = name

    def _check(self, obj, prefix, settings_to_write, missing):
        if isinstance(obj, Mapping):
            items = sorted(obj.items(), key=lambda item: item[0])
        elif isinstance(obj, Sequence) and not isinstance(obj, string_types):
            items = zip(range(len(obj)), obj)
        else:
            return {}, {}

        for k, v in items:
            name = k if not prefix else '{0}.{1}'.format(prefix, k)
            if not isinstance(v, LocalSetting):
                self._check(v, name, settings_to_write, missing)
            elif k not in settings_to_write:
                # Note: If k is already in settings_to_write, this local
                # setting was set as a result of being another setting's
                # default.
                is_set = False
                local_setting = v

                if local_setting.derived_default:
                    # Ensure this setting's default is set if it's also a local setting
                    default_name = self.registry[local_setting.derived_default]
                    if not local_setting.has_default:
                        self._check(
                            {default_name: local_setting.derived_default},
                            None, settings_to_write, missing)

                if self.prompt:
                    printer.print_header('=' * 79)

                if local_setting.prompt:  # prompt for value
                    if self.prompt:
                        v, is_set = self.prompt_for_value(name, v)
                elif local_setting.has_default:  # use default w/o prompting
                    v, is_set = local_setting.default, True
                    msg = (
                        'Using default value `{value!r}` for local setting '
                        '`{name}`'.format(name=name, value=v))
                    if local_setting.derived_default:
                        msg += ' (derived from {0})'.format(default_name)
                    printer.print_warning(msg)

                if is_set:
                    local_setting.value = obj[k] = settings_to_write[name] = v
                else:
                    missing[name] = v

        return settings_to_write, missing

    def prompt_for_value(self, name, local_setting):
        v, is_set = NO_DEFAULT, False
        while not is_set:  # Keep prompting until valid value is set
            printer.print_header(
                'Enter a value for the local setting `{name}` (as JSON)'.format(name=name))
            if local_setting.doc:
                printer.print_header(local_setting.doc)
            if local_setting.has_default:
                msg = 'Hit enter to use default: `{0!r}`'.format(local_setting.default)
                if local_setting.derived_default:
                    default_name = self.registry[local_setting.derived_default]
                    msg += ' (derived from {0})'.format(default_name)
                printer.print_header(msg)
            v = input('> ').strip()
            if v:
                try:
                    v = self.strategy.decode_value(v)
                except ValueError as e:
                    printer.print_error(e)
                else:
                    is_set = local_setting.validate(v)
                    if not is_set:
                        printer.print_error('`{0}` is not a valid value for {1}'.format(v, name))
            elif local_setting.has_default:
                v, is_set = local_setting.default, True
                printer.print_info('Using default value for `{0}`'.format(name))
            else:
                printer.print_error('You must enter a value for `{0}`'.format(name))
        return v, is_set

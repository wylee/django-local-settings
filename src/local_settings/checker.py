import sys
from collections import Mapping, Sequence

from .base import Base
from .color_printer import color_printer as printer
from .types import EnvSetting, LocalSetting, SecretSetting
from .util import NO_DEFAULT, is_a_tty


class Checker(Base):
    def __init__(
        self,
        file_name,
        section=None,
        registry=None,
        strategy_type=None,
        prompt=None,
    ):
        super().__init__(file_name, section, registry, strategy_type)
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
            self.strategy.write_settings(
                settings_to_write,
                self.file_name,
                self.section,
            )
        if missing:
            for name, local_setting in missing.items():
                if isinstance(local_setting, EnvSetting):
                    message = (
                        f"Env setting `{name}` must be set in settings "
                        f"file or environ ({local_setting.name})"
                    )
                elif isinstance(local_setting, SecretSetting):
                    message = f"Secrete setting `{name}` must be set"
                else:
                    message = f"Local setting `{name}` must be set"
                printer.print_error(message)
            return False
        return True

    def _populate_registry(self, obj, prefix=None):
        if isinstance(obj, Mapping):
            items = obj.items()
        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            items = zip(range(len(obj)), obj)
        else:
            return
        for k, v in items:
            name = k if prefix is None else f"{prefix}.{k}"
            if not isinstance(v, LocalSetting):
                self._populate_registry(v, name)
            else:
                self.registry[v] = name

    def _check(self, obj, prefix, settings_to_write, missing):
        if isinstance(obj, Mapping):
            items = sorted(obj.items(), key=lambda item: item[0])
        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            items = zip(range(len(obj)), obj)
        else:
            return {}, {}

        for k, v in items:
            name = k if not prefix else f"{prefix}.{k}"
            if not isinstance(v, LocalSetting):
                self._check(v, name, settings_to_write, missing)
            elif name not in settings_to_write:
                # Note: If name is already in settings_to_write, this
                # local setting was set as a result of being another
                # setting's default.
                is_set = False
                local_setting = v

                if local_setting.derived_default:
                    # Ensure this setting's default is set if it's also a local setting
                    default_name = self.registry[local_setting.derived_default]
                    if not local_setting.has_default:
                        self._check(
                            {default_name: local_setting.derived_default},
                            None,
                            settings_to_write,
                            missing,
                        )

                if local_setting.prompt:  # prompt for value
                    if self.prompt:
                        v, is_set = self.prompt_for_value(name, v)
                elif local_setting.has_default:  # use default w/o prompting
                    v, is_set = local_setting.default, True
                    v = self.strategy.encode_value(v)
                    msg = f"Using default value `{v!r}` for local " f"setting `{name}`"
                    if local_setting.derived_default:
                        msg += f" (derived from {default_name})"
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
                f"Enter a value for the local setting `{name}` (as JSON)"
            )
            if local_setting.doc:
                printer.print_header(local_setting.doc)
            if local_setting.has_default:
                msg = f"Hit enter to use default: `{local_setting.default!r}`"
                if local_setting.derived_default:
                    default_name = self.registry[local_setting.derived_default]
                    msg += f" (derived from {default_name})"
                printer.print_header(msg)
            v = input("> ").strip()
            if v:
                try:
                    self.strategy.decode_value(v)
                except ValueError as e:
                    printer.print_error(e)
                else:
                    is_set = local_setting.validate(v)
                    if not is_set:
                        printer.print_error(f"`{v}` is not a valid value for {name}")
            elif local_setting.has_default:
                v, is_set = local_setting.default, True
                v = self.strategy.encode_value(v)
                printer.print_info(f"Using default value for `{name}`")
            else:
                printer.print_error(f"You must enter a value for `{name}`")
        return v, is_set

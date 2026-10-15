"""Original BaseTableLayoutWdg.get_setting, independent of presentation imports.

The legacy class delegates to the same method. No changed settings precedence.
"""
import json
import six
basestring = six.string_types
jsonloads = json.loads


class TableSettingsMixin:
    def get_setting(self, name):
        settings = self.kwargs.get("settings") or {}

        """
        settings = {
            "gear": {
                    'Tasks': ['Show Tasks'],
                    'Edit': ['Retire Selected Items', 'Delete Selected Items'],
                    'View': ['Save a New View'],
            },
            #"save": True
            #"search_limit": True,
            #"expand": True,
            #"insert": True,
            "layout_switcher": True,
        }
        #settings = None
        #settings = "save|insert|search|keyword_search"
        """


        settings_default = {
            'header_background': True
        }



        if isinstance(settings, basestring):
            settings = settings.split("|")

        if isinstance(settings, list):
            new_settings = {}
            for item in settings:
                new_settings[item] = True
            settings = new_settings

        if 'gear' in settings and settings.get("gear") == True:
            gear_settings = self.kwargs.get("gear_settings")
            if isinstance(gear_settings, basestring):
                if gear_settings.startswith("{") and gear_settings.endswith("}"):
                    # HACK:
                    gear_settings = gear_settings.replace("'", '"')
                    gear_settings = jsonloads(gear_settings)
                else:
                    gear_settings = gear_settings.split("|")

            if isinstance(gear_settings, list):
                new_gear_settings = {}
                for item in gear_settings:
                    new_gear_settings[item] = True
                gear_settings = new_gear_settings

            if not gear_settings:
                gear_settings = {}

            settings["gear"] = gear_settings


        default = True
        if name in ["gear"]:
            default = True
        elif name in ['header_background']:
            default = True



        value = None
        if settings:
            if settings.get(name) in [None, False, "false"]:
                # if not in settings, then the default is false
                default = False
            if name not in settings:
                value = settings_default.get(name)
            else:
                value = settings.get(name)


        # some special settings if the value is False
        if value in [False, None]:
            show_name = "show_%s" % name

            if default == True:
                if self.kwargs.get(show_name) not in ['false', False]:
                    value = True
                else:
                    value = False

            else:
                if self.kwargs.get(show_name) not in ['true', True]:
                    value = False
                else:
                    value = True


        return value


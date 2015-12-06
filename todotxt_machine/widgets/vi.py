# coding=utf-8
import urwid


class ViPile(urwid.Pile):
    def __init__(self, key_bindings, widget_list, focus_item=None):
        """Pile with Vi-like navigation."""
        super(ViPile, self).__init__(widget_list, focus_item)

        command_map = urwid.command_map.copy()

        keys = key_bindings.get_key_binding('up')
        for key in keys:
            command_map[key] = urwid.CURSOR_UP
        keys = key_bindings.get_key_binding('down')
        for key in keys:
            command_map[key] = urwid.CURSOR_DOWN

        self._command_map = command_map


class ViCheckbox(urwid.CheckBox):
    def __init__(self, *args, **kwargs):
        """Pile with Vi-like navigation."""
        super(ViCheckbox, self).__init__(*args, **kwargs)

        command_map = urwid.command_map.copy()
        command_map['x'] = 'activate'
        self._command_map = command_map


class ViColumns(urwid.Columns):
    def __init__(self, key_bindings, widget_list, dividechars=0, focus_column=None, min_width=1, box_columns=None):
        super(ViColumns, self).__init__(widget_list, dividechars, focus_column, min_width, box_columns)
        command_map = urwid.command_map.copy()

        keys = key_bindings.get_key_binding('right')
        for key in keys:
            command_map[key] = urwid.CURSOR_RIGHT
        keys = key_bindings.get_key_binding('left')
        for key in keys:
            command_map[key] = urwid.CURSOR_LEFT

        self._command_map = command_map


class ViListBox(urwid.ListBox):
    def __init__(self, key_bindings, *args, **kwargs):
        super(ViListBox, self).__init__(*args, **kwargs)
        command_map = urwid.command_map.copy()

        keys = key_bindings.get_key_binding('down')
        for key in keys:
            command_map[key] = urwid.CURSOR_DOWN
        keys = key_bindings.get_key_binding('up')
        for key in keys:
            command_map[key] = urwid.CURSOR_UP

        self._command_map = command_map


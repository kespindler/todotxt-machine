# coding=utf-8
import urwid
from todotxt_machine.widgets.util import handle_keypress


class SearchWidget(urwid.Edit):
    def __init__(self, parent_ui, key_bindings, edit_text=""):
        self.parent_ui = parent_ui
        self.key_bindings = key_bindings
        super(SearchWidget, self).__init__(edit_text=edit_text)

    def search_end(self):
        self.parent_ui.finalize_search()

    def clear_search(self):
        self.parent_ui.clear_searches()

    def keypress(self, size, key):
        if handle_keypress(self, key, 'search'):
            return
        return super(SearchWidget, self).keypress(size, key)

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

    def keypress(self, size, key):
        if self.key_bindings.is_bound_to(key, 'search-end'):
            self.parent_ui.finalize_search()
        return super(SearchWidget, self).keypress(size, key)

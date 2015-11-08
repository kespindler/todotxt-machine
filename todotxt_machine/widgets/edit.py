# coding=utf-8
import urwid

from todotxt_machine.widgets.util import handle_keypress


# Modified from http://wiki.goffi.org/wiki/Urwid-satext/en
class AdvancedEdit(urwid.Edit):
    """Edit box with some custom improvments
    new chars:
              - C-a: like 'home'
              - C-e: like 'end'
              - C-k: remove everything on the right of the cursor
              - C-w: remove the word on the back"""

    def __init__(self, parent_ui, key_bindings, *args, **kwargs):
        self.parent_ui = parent_ui
        self.key_bindings = key_bindings
        self.completion_cb = None
        self.completion_data = {}
        super(AdvancedEdit, self).__init__(*args, **kwargs)

    def set_completion_method(self, callback):
        """Define method called when completion is asked
        @callback: method with 2 arguments:
                    - the text to complete
                    - if there was already a completion, a dict with
                        - 'completed':last completion
                        - 'completion_pos': cursor position where the completion starts
                        - 'position': last completion cursor position
                      this dict must be used (and can be filled) to find next completion)
                   and which return the full text completed"""
        self.completion_cb = callback
        self.completion_data = {}

    def edit_complete(self):
        try:
            before = self.edit_text[:self.edit_pos]
            if self.completion_data:
                if (not self.completion_data['completed']
                        or self.completion_data['position'] != self.edit_pos
                        or not before.endswith(self.completion_data['completed'])):
                    self.completion_data.clear()
                else:
                    before = before[:-len(self.completion_data['completed'])]
            complete = self.completion_cb(before, self.completion_data)
            self.completion_data['completed'] = complete[len(before):]
            self.set_edit_text(complete+self.edit_text[self.edit_pos:])
            self.set_edit_pos(len(complete))
            self.completion_data['position'] = self.edit_pos
        except AttributeError:
            pass

    def set_edit_position(self, index=None, from_last=False, relative=None):
        """
        Example usage:
        self.move_selection(0) puts you at the start
        self.move_selection(from_last=True) puts you at the end
        self.move_selection(relative=1) moves you forward one
        self.move_selection(relative=-1) moves you back one
        self.move_selection(from_last=True, relative=-1) puts you second to last
        """
        if index is None:
            if from_last:
                index = len(self._edit_text) - 1
            else:
                index = self._edit_pos
        if relative:
            index += relative
        self.set_edit_pos(index)

    def edit_word_left(self):
        before = self.edit_text[:self.edit_pos]
        pos = before.rstrip().rfind(" ")+1
        self.set_edit_pos(pos)

    def edit_word_right(self):
        after = self.edit_text[self.edit_pos:]
        pos = after.rstrip().find(" ")+1
        self.set_edit_pos(self.edit_pos+pos)

    def edit_delete_word(self):
        before = self.edit_text[:self.edit_pos]
        pos = before.rstrip().rfind(" ")+1
        self.parent_ui.yanked_text = self.edit_text[pos:self.edit_pos]
        self.set_edit_text(before[:pos] + self.edit_text[self.edit_pos:])
        self.set_edit_pos(pos)

    def edit_delete_beginning(self):
        before = self.edit_text[:self.edit_pos]
        self.parent_ui.yanked_text = self.edit_text[:self.edit_pos]
        self.set_edit_text(self.edit_text[self.edit_pos:])
        self.set_edit_pos(0)

    def edit_delete_end(self):
        self.parent_ui.yanked_text = self.edit_text[self.edit_pos:]
        self._delete_highlighted()
        self.set_edit_text(self.edit_text[:self.edit_pos])

    def edit_paste(self):
        self.set_edit_text(
            self.edit_text[:self.edit_pos] +
            self.parent_ui.yanked_text +
            self.edit_text[self.edit_pos:])
        self.set_edit_pos(self.edit_pos + len(self.parent_ui.yanked_text))

    def keypress(self, size, key):
        if handle_keypress(self, key, 'edit'):
            return
        return super(AdvancedEdit, self).keypress(size, key)


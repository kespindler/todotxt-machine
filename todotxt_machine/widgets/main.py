# coding=utf-8
import collections
import urwid

from todotxt_machine.widgets.todo import TodoWidget
from todotxt_machine.widgets.util import handle_keypress
from todotxt_machine.widgets.search import SearchWidget
from todotxt_machine.widgets.vi import ViListBox, ViColumns, ViPile


class UrwidUI(object):
    sort_options = [
        dict(
            name='Unsorted',
            hint='-',
            key=None,
        ),
        dict(
            name='Due Date',
            hint='d',
            key=lambda x: x.due_date or '9999-99-99',
        ),
        dict(
            name='Priority',
            hint='p',
            key=lambda x: x.priority or 'z',
        ),
    ]

    def __init__(self, todos, key_bindings, colorscheme):
        self.wrapping = collections.deque(['clip', 'space'])
        self.border = collections.deque(['no border', 'bordered'])
        self.sort_order = 0

        self.todos = todos
        self.key_bindings = key_bindings

        self.colorscheme = colorscheme
        self.palette = [(key, '', '', '', value['fg'], value['bg'])
                        for key, value in self.colorscheme.colors.items()]

        self.active_projects = []
        self.active_contexts = []

        self.toolbar_is_open = False
        self.help_panel_is_open = False
        self.filter_panel_is_open = False
        self.filtering = False
        self.searching = False
        self.search_string = ''
        self.yanked_text = ''
        self.help_panel = None
        self.filter_panel = None
        self.loop = None
        self.header = None
        self.footer = None
        self.view = None
        self.frame = None
        self.listbox = None
        self.search_box = None

        self.filter_results = []

    def visible_lines(self):
        lines = self.loop.screen_size[1] - 1  # minus one for the header
        if self.toolbar_is_open:
            lines -= 1
        if self.searching:
            lines -= 1
        return lines

    def move_selection_down(self):
        self.listbox.keypress((0, self.visible_lines()), 'down')

    def move_selection_up(self):
        self.listbox.keypress((0, self.visible_lines()), 'up')

    def move_selection_top(self):
        self.listbox.set_focus(0)

    def move_selection_bottom(self):
        self.listbox.set_focus(len(self.listbox.body)-1)

    def toggle_help_panel(self, button=None):
        if self.filter_panel_is_open:
            self.toggle_filter_panel()
        if self.help_panel_is_open:
            self.view.contents.pop()
            self.help_panel_is_open = False
            # set header line to word-wrap contents
            # for header_column in self.frame.header.original_widget.contents:
            #     header_column[0].set_wrap_mode('space')
        else:
            self.help_panel = self.create_help_panel()
            self.view.contents.append((self.help_panel, self.view.options(width_type='weight', width_amount=3)))
            self.view.set_focus(1)
            self.help_panel_is_open = True
            # set header line to clip contents
            # for header_column in self.frame.header.original_widget.contents:
            #     header_column[0].set_wrap_mode('clip')

    def toggle_sorting(self, button=None):
        self.delete_todo_widgets()

        self.sort_order = (self.sort_order + 1) % len(self.sort_options)
        sort = self.sort_options[self.sort_order]
        if sort['key'] is None:
            self.todos.sorted_raw()
        else:
            self.todos.sorted(key=sort['key'])
        self.reload_todos_from_memory()
        self.move_selection_top()
        self.update_header()

    def toggle_filter_panel(self, button=None):
        if self.help_panel_is_open:
            self.toggle_help_panel()
        if self.filter_panel_is_open:
            self.view.contents.pop()
            self.filter_panel_is_open = False
        else:
            self.filter_panel = self.create_filter_panel()
            self.view.contents.append((self.filter_panel, self.view.options(width_type='weight', width_amount=1)))
            self.filter_panel_is_open = True

    def toggle_wrapping(self, checkbox=None, state=None):
        self.wrapping.rotate(1)
        for widget in self.listbox.body:
            widget.wrapping = self.wrapping[0]
            widget.update_todo()
        if self.toolbar_is_open:
            self.update_header()

    def toggle_border(self, checkbox=None, state=None):
        self.border.rotate(1)
        for widget in self.listbox.body:
            widget.border = self.border[0]
            widget.update_todo()
        if self.toolbar_is_open:
            self.update_header()

    def toggle_toolbar(self):
        self.toolbar_is_open = not self.toolbar_is_open
        self.update_header()

    def swap_down(self):
        focus, focus_index = self.listbox.get_focus()
        if not self.filtering and not self.searching:
            if focus_index+1 < len(self.listbox.body):
                self.todos.swap(focus_index, focus_index + 1)
                self.listbox.body[focus_index].todo = self.todos[focus_index]
                self.listbox.body[focus_index+1].todo = self.todos[focus_index+1]
                self.listbox.body[focus_index].update_todo()
                self.listbox.body[focus_index+1].update_todo()
                self.move_selection_down()

    def swap_up(self):
        focus, focus_index = self.listbox.get_focus()
        if not self.filtering and not self.searching:
            if focus_index > 0:
                self.todos.swap(focus_index, focus_index - 1)
                self.listbox.body[focus_index].todo = self.todos[focus_index]
                self.listbox.body[focus_index-1].todo = self.todos[focus_index-1]
                self.listbox.body[focus_index].update_todo()
                self.listbox.body[focus_index-1].update_todo()
                self.move_selection_up()

    def save_todos(self, button=None):
        self.todos.save()
        self.update_header("Saved")

    def archive_done_todos(self):
        if self.todos.archive_done():
            self.delete_todo_widgets()
            self.reload_todos_from_memory()
            self.move_selection_top()
            self.update_header()

    def reload_todos_from_file(self, button=None):
        self.delete_todo_widgets()

        self.todos.reload_from_file()

        for t in self.todos.todo_items:
            self.listbox.body.append(TodoWidget(t, self.key_bindings, self.colorscheme, self, wrapping=self.wrapping[0], border=self.border[0]) )

        self.update_header("Reloaded")

    def quit(self):
        raise urwid.ExitMainLoop()

    def set_priority(self, priority):
        focus, focus_index = self.listbox.get_focus()
        focus.todo.set_priority(priority)
        focus.update_todo()
        self.update_header()

    def search_clear(self):
        if self.searching:
            self.clear_search_term()

    def keystroke(self, input):
        focus, focus_index = self.listbox.get_focus()

        if handle_keypress(self, input, 'listbox'):
            pass  # already handled
        # Movement
        elif self.key_bindings.is_bound_to(input, 'top'):
            self.move_selection_top()
        elif self.key_bindings.is_bound_to(input, 'bottom'):
            self.move_selection_bottom()
        elif self.key_bindings.is_bound_to(input, 'swap-down'):
            self.swap_down()
        elif self.key_bindings.is_bound_to(input, 'swap-up'):
            self.swap_up()
        elif self.key_bindings.is_bound_to(input, 'change-focus'):
            current_focus = self.frame.get_focus()
            if current_focus == 'body':

                if self.filter_panel_is_open and self.toolbar_is_open:

                    if self.view.focus_position == 1:
                        self.view.focus_position = 0
                        self.frame.focus_position = 'header'
                    elif self.view.focus_position == 0:
                        self.view.focus_position = 1

                elif self.toolbar_is_open:
                    self.frame.focus_position = 'header'

                elif self.filter_panel_is_open:
                    if self.view.focus_position == 1:
                        self.view.focus_position = 0
                    elif self.view.focus_position == 0:
                        self.view.focus_position = 1

            elif current_focus == 'header':
                self.frame.focus_position = 'body'

        # Editing
        elif self.key_bindings.is_bound_to(input, 'toggle-complete'):
            if focus.todo.is_complete():
                focus.todo.incomplete()
            else:
                focus.todo.complete()
            focus.update_todo()
            self.update_header()

        elif self.key_bindings.is_bound_to(input, 'archive'):
            self.archive_done_todos()

        elif self.key_bindings.is_bound_to(input, 'delete'):
            if self.todos.todo_items:
                self.delete_todo(focus.todo.raw_index)

        elif self.key_bindings.is_bound_to(input, 'append'):
            self.add_new_todo(position='append')
        elif self.key_bindings.is_bound_to(input, 'insert-before'):
            self.add_new_todo(position='insert_before')
        elif self.key_bindings.is_bound_to(input, 'insert-after'):
            self.add_new_todo(position='insert_after')

        # Save current file
        elif self.key_bindings.is_bound_to(input, 'save'):
            self.save_todos()

        # Reload original file
        elif self.key_bindings.is_bound_to(input, 'reload'):
            self.reload_todos_from_file()

    def is_filtering(self):
        return self.searching or self.filtering

    def delete_todo(self, index):
        if self.todos.todo_items:
            item = self.todos.delete(index)
            if self.is_filtering():
                filtered_index = self.filter_results.index(item)
                del self.listbox.body[filtered_index]
                del self.filter_results[filtered_index]
            else:
                del self.listbox.body[index]
            self.update_header()

    def add_new_todo(self, position=False):
        if len(self.listbox.body) == 0:
            position = 'append'
        else:
            focus_index = self.listbox.get_focus()[1]

        if self.filtering:
            position = 'append'

        if position is 'append':
            new_index = self.todos.append('', add_creation_date=False)
            self.listbox.body.append(TodoWidget(self.todos[new_index], self.key_bindings, self.colorscheme, self, editing=True, wrapping=self.wrapping[0], border=self.border[0]))
        else:
            if position is 'insert_after':
                new_index = self.todos.insert(focus_index+1, '', add_creation_date=False)
            elif position is 'insert_before':
                new_index = self.todos.insert(focus_index, '', add_creation_date=False)

            self.listbox.body.insert(new_index, TodoWidget(self.todos[new_index], self.key_bindings, self.colorscheme, self, editing=True, wrapping=self.wrapping[0], border=self.border[0]))

        if position:
            if self.filtering:
                self.listbox.set_focus(len(self.listbox.body)-1)
            else:
                self.listbox.set_focus(new_index)
            # edit_widget = self.listbox.body[new_index]._w
            # edit_widget.edit_text += ' '
            # edit_widget.set_edit_pos(len(self.todos[new_index].raw) + 1)
            self.update_header()

    def create_header(self, message=""):
        todos = (self.filter_results or self.todos.todo_items) or []
        done_todos = filter(lambda x: x.is_complete(), todos)
        pending_todos = filter(lambda x: not x.is_complete(), todos)
        return urwid.AttrMap(
            urwid.Columns([
                urwid.Text([
                    ('header_todo_count', "{0} Todos ".format(len(todos))),
                    ('header_todo_pending_count', " {0} Pending ".format(len(pending_todos))),
                    ('header_todo_done_count', " {0} Done ".format(len(done_todos))),
                ]),
                urwid.Text(('header_file', "{0}  {1} ".format(message, self.todos.file_path)), align='right')
            ]), 'header')

    def create_toolbar(self):
        return urwid.AttrMap(urwid.Columns([
            urwid.Padding(
                urwid.AttrMap(
                    urwid.CheckBox([('header_file', 'w'), 'ord wrap'], state=(self.wrapping[0] == 'space'), on_state_change=self.toggle_wrapping),
                    'header', 'plain_selected'), right=2 ),

            urwid.Padding(
                urwid.AttrMap(
                    urwid.CheckBox([('header_file', 'b'), 'orders'], state=(self.border[0] == 'bordered'), on_state_change=self.toggle_border),
                    'header', 'plain_selected'), right=2 ),

            urwid.Padding(
                urwid.AttrMap(
                    urwid.Button([('header_file', 'R'), 'eload'], on_press=self.reload_todos_from_file),
                    'header', 'plain_selected'), right=2 ),

            urwid.Padding(
                urwid.AttrMap(
                    urwid.Button([('header_file', 'S'), 'ave'], on_press=self.save_todos),
                    'header', 'plain_selected'), right=2 ),

            urwid.Padding(
                urwid.AttrMap(
                    urwid.Button([('header_file', 's'), 'ort: '+self.sort_options[self.sort_order]['hint']], on_press=self.toggle_sorting),
                    'header', 'plain_selected'), right=2),

            urwid.Padding(
                urwid.AttrMap(
                    urwid.Button([('header_file', 'f'), 'ilter'], on_press=self.toggle_filter_panel),
                    'header', 'plain_selected'), right=2 )
        ]), 'header')

    def search_box_updated(self, edit_widget, new_contents):
        old_contents = edit_widget.edit_text
        self.search_string = new_contents
        self.search_todo_list(self.search_string)

    def search_todo_list(self, search_string="", invert=False):
        if search_string and self.todos.valid_search(search_string):
            self.delete_todo_widgets()
            self.searching = True

            self.filter_results = list(self.todos.search(search_string, invert=invert))

            for t in self.filter_results:
                self.listbox.body.append(TodoWidget(t, self.key_bindings, self.colorscheme, self, wrapping=self.wrapping[0], border=self.border[0]))

    def start_search(self):
        self.searching = True
        self.update_footer()
        self.frame.set_focus('footer')

    def run_search(self, search_string, invert=False):
        self.search_todo_list(search_string, invert=invert)
        self.finalize_search()

    def finalize_search(self):
        self.search_string = ''
        self.frame.set_focus('body')
        self.update_header()
        for widget in self.listbox.body:
            widget.update_todo()

    def clear_search_term(self, button=None):
        self.delete_todo_widgets()
        self.searching = False
        self.search_string = ''
        self.filter_results = []
        self.update_header()
        self.update_footer()
        # TODO this destroys any sorting we have going
        self.reload_todos_from_memory()

    def create_footer(self):
        if self.searching:
            self.search_box = SearchWidget(self, self.key_bindings, edit_text=self.search_string)
            w = urwid.AttrMap(urwid.Columns([
                (1, urwid.Text('/')),
                self.search_box,
                (16, urwid.AttrMap(
                    urwid.Button([('header_file', 'C'), 'lear Search'], on_press=self.clear_search_term),
                    'header', 'plain_selected'))
            ]), 'footer')
            urwid.connect_signal(self.search_box, 'change', self.search_box_updated)
        else:
            w = None
        return w

    def format_tooltip(self, name):
        key_column_width = 12
        data = self.key_bindings.key_bindings[name]
        keys = ', '.join(data['keys'])
        return '{keys} - {tooltip}'.format(keys=keys.ljust(key_column_width),
                                           tooltip=data['tooltip'])

    def help_block(self, title, names):
        header_highlight = 'plain_selected'
        return [
            urwid.Divider(),
            urwid.AttrWrap(urwid.Text(title), header_highlight),
            urwid.Text('\n' + '\n'.join(self.format_tooltip(name) for name in names) + '\n'),
        ]

    def create_help_panel(self):
        key_column_width = 12
        header_highlight = 'plain_selected'
        return urwid.AttrMap(
            urwid.LineBox(
                urwid.Padding(
                    ViListBox(
                        self.key_bindings,
                        self.help_block('General', [
                            'toggle-help', 'quit', 'toggle-toolbar', 'toggle-wrapping',
                            'toggle-borders', 'save', 'reload',
                        ]) +
                        [urwid.AttrWrap(urwid.Text("""
Movement
""".strip()), header_highlight)] +
                        [ urwid.Text("""
{0} - select any todo, checkbox or button
{1} - move selection down
{2} - move selection up
{3} - move selection to the top item
{4} - move selection to the bottom item
{5} - move selection between todos and filter panel
{6}
{7} - toggle focus between todos, filter panel, and toolbar
""".format(
                            "mouse click".ljust(key_column_width),
                            self.key_bindings["down"         ].ljust(key_column_width),
                            self.key_bindings["up"           ].ljust(key_column_width),
                            self.key_bindings["top"          ].ljust(key_column_width),
                            self.key_bindings["bottom"       ].ljust(key_column_width),
                            self.key_bindings["left"         ].ljust(key_column_width),
                            self.key_bindings["right"        ].ljust(key_column_width),
                            self.key_bindings["change-focus" ].ljust(key_column_width),
                        ))] +

                        [ urwid.AttrWrap(urwid.Text("""
Manipulating Todo Items
""".strip()), header_highlight) ] +
                        # [ urwid.Divider(u'─') ] +

                        [ urwid.Text("""
{0} - complete / un-complete selected todo item
{1} - archive completed todo items to done.txt (if specified)
{2} - add a new todo to the end of the list
{3} - add a todo after the selected todo (when not filtering)
{4} - add a todo before the selected todo (when not filtering)
{5} - edit the selected todo
{6} - delete the selected todo
{7} - swap with item below
{8} - swap with item above
""".format(
                            self.key_bindings["toggle-complete" ].ljust(key_column_width),
                            self.key_bindings["archive"         ].ljust(key_column_width),
                            self.key_bindings["append"          ].ljust(key_column_width),
                            self.key_bindings["insert-after"    ].ljust(key_column_width),
                            self.key_bindings["insert-before"   ].ljust(key_column_width),
                            self.key_bindings["edit"            ].ljust(key_column_width),
                            self.key_bindings["delete"          ].ljust(key_column_width),
                            self.key_bindings["swap-down"       ].ljust(key_column_width),
                            self.key_bindings["swap-up"         ].ljust(key_column_width),
                        ))] +

                        [ urwid.AttrWrap(urwid.Text("""
While Editing a Todo
""".strip()), header_highlight) ] +
                        # [ urwid.Divider(u'─') ] +

                        [ urwid.Text("""
{0} - tab complete contexts and projects
{1} - save todo item
{2} - move cursor left and right
{3}
{4} - move cursor backwards (left) by one word
{5} - move cursor forwards (right) by one word
{6} - move cursor the beginning or end of the line
{7}
{8} - delete one word backwards
{9} - delete from the cursor to the end of the line
{10} - delete from the cursor to the beginning of the line
{11} - paste last deleted text
""".format(
                            self.key_bindings["edit-complete"         ].ljust(key_column_width),
                            self.key_bindings["edit-save"             ].ljust(key_column_width),
                            self.key_bindings["edit-move-left"        ].ljust(key_column_width),
                            self.key_bindings["edit-move-right"       ].ljust(key_column_width),
                            self.key_bindings["edit-word-left"        ].ljust(key_column_width),
                            self.key_bindings["edit-word-right"       ].ljust(key_column_width),
                            self.key_bindings["edit-home"             ].ljust(key_column_width),
                            self.key_bindings["edit-end"              ].ljust(key_column_width),
                            self.key_bindings["edit-delete-word"      ].ljust(key_column_width),
                            self.key_bindings["edit-delete-end"       ].ljust(key_column_width),
                            self.key_bindings["edit-delete-beginning" ].ljust(key_column_width),
                            self.key_bindings["edit-paste"            ].ljust(key_column_width),
                        ))] +

                        self.help_block('Sorting', ['toggle-sorting']) +
                        self.help_block('Filtering', ['toggle-filter', 'clear-filter']) +
                        self.help_block('Searching', ['search', 'search-end', 'search-clear'])
                    ),
                    left=1, right=1, min_width=10 ), title='Key Bindings'), 'default')

    def create_filter_panel(self):
        w = urwid.AttrMap(
            urwid.Padding(
                urwid.ListBox(
                    [
                        ViPile(
                            self.key_bindings,
                            [ urwid.Text('Contexts & Projects', align='center') ] +
                            [ urwid.Divider(u'─') ] +
                            [urwid.AttrWrap(urwid.CheckBox(c, state=(c in self.active_contexts), on_state_change=self.checkbox_clicked, user_data=['context', c]), 'context_dialog_color', 'context_selected') for c in self.todos.all_contexts()] +
                            [ urwid.Divider(u'─') ] +
                            [urwid.AttrWrap(urwid.CheckBox(p, state=(p in self.active_projects), on_state_change=self.checkbox_clicked, user_data=['project', p]), 'project_dialog_color', 'project_selected') for p in self.todos.all_projects()] +
                            [ urwid.Divider(u'─') ] +
                            [ urwid.AttrMap(urwid.Button(['Clear ', ('header_file_dialog_color','F'), 'ilters'], on_press=self.clear_filters), 'dialog_color', 'plain_selected') ]
                        )
                    ] +
                    [ urwid.Divider() ],
                    ),
                left=1, right=1, min_width=10 )
            ,
            'dialog_color')

        bg = urwid.AttrWrap(urwid.SolidFill(u" "), 'dialog_background') # u"\u2592"
        shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'dialog_shadow')

        bg = urwid.Overlay(shadow, bg,
                            ('fixed left', 2), ('fixed right', 1),
                            ('fixed top', 2), ('fixed bottom', 1))
        w = urwid.Overlay(w, bg,
                           ('fixed left', 1), ('fixed right', 2),
                           ('fixed top', 1), ('fixed bottom', 2))
        return w

    def delete_todo_widgets(self):
        for i in range(len(self.listbox.body)-1, -1, -1):
            self.listbox.body.pop(i)

    def reload_todos_from_memory(self):
        for t in self.todos.todo_items:
            self.listbox.body.append(TodoWidget(t, self.key_bindings, self.colorscheme, self,
                                                wrapping=self.wrapping[0], border=self.border[0]))

    def clear_filters(self, button=None):
        self.delete_todo_widgets()
        self.reload_todos_from_memory()

        self.filter_results = []
        self.active_projects = []
        self.active_contexts = []
        self.filtering = False
        self.view.set_focus(0)
        self.update_filters()
        self.update_header()

    def checkbox_clicked(self, checkbox, state, data):
        if state:
            if data[0] == 'context':
                self.active_contexts.append(data[1])
            else:
                self.active_projects.append(data[1])
        else:
            if data[0] == 'context':
                self.active_contexts.remove(data[1])
            else:
                self.active_projects.remove(data[1])

        if self.active_projects or self.active_contexts:
            self.filter_todo_list()
            self.view.set_focus(0)
        else:
            self.clear_filters()
        self.update_header()

    def filter_todo_list(self):
        self.delete_todo_widgets()

        self.filter_results = list(self.todos.filter_contexts_and_projects(self.active_contexts, self.active_projects))
        for t in self.filter_results:
            self.listbox.body.append(TodoWidget(t, self.key_bindings, self.colorscheme, self,
                                                wrapping=self.wrapping[0], border=self.border[0]))

        self.filtering = True

    def update_filters(self, new_contexts=None, new_projects=None):
        if self.active_contexts and new_contexts:
            self.active_contexts.extend(new_contexts)
        if self.active_projects and new_projects:
            self.active_projects.extend(new_projects)
        self.update_filter_panel()

    def update_filter_panel(self):
        self.filter_panel = self.create_filter_panel()
        if len(self.view.widget_list) > 1:
            self.view.widget_list.pop()
            self.view.widget_list.append(self.filter_panel)

    def update_header(self, message=""):
        if self.toolbar_is_open:
            self.frame.header = urwid.Pile([self.create_header(message), self.create_toolbar()])
        else:
            self.frame.header = self.create_header(message)

    def update_footer(self, message=""):
        self.frame.footer = self.create_footer()

    def main(self):
        self.header = self.create_header()
        self.footer = self.create_footer()

        self.listbox = ViListBox(self.key_bindings, urwid.SimpleListWalker(
            [TodoWidget(t, self.key_bindings, self.colorscheme, self) for t in self.todos.todo_items]
        ))

        self.frame = urwid.Frame(urwid.AttrMap(self.listbox, 'plain'), header=self.header, footer=self.footer)

        self.view = ViColumns(self.key_bindings, [
            ('weight', 2, self.frame)
        ])

        self.loop = urwid.MainLoop(self.view, self.palette, unhandled_input=self.keystroke)
        self.loop.screen.set_terminal_properties(colors=256)
        self.loop.run()

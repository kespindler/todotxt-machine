# coding=utf-8
import urwid
import re
import subprocess as sub
from todotxt_machine.widgets.todo import TodoWidget
from todotxt_machine.widgets.util import handle_keypress, log
from todotxt_machine.widgets.search import SearchWidget
from todotxt_machine.widgets.vi import ViListBox, ViColumns, ViPile, ViCheckbox


class UrwidUI(object):
    sort_options = [
        dict(
            name='Unsorted',
            hint='-',
            key=None,
        ),
        dict(
            name='Due Date',
            hint='due',
            key=lambda x: x.due_date or '9999-99-99',
        ),
        dict(
            name='Priority',
            hint='pri',
            key=lambda x: x.priority or 'z',
        ),
        dict(
            name='Project',
            hint='proj',
            key=lambda x: '' if not x.projects else x.projects[0],
            allow_tree=True,
        ),
        dict(
            name='Natural',
            hint='nat',
            key=None,
            allow_tree=True,
        )
    ]
    display_options = [
        dict(
            name='Todotxt',
            hint='-',
            display='no border',
        ),
        dict(
            name='Border',
            hint='bord',
            display='bordered',
        ),
        dict(
            name='Tree',
            hint=u'\U0001F332 ',
            display='tree',
        ),
    ]
    wrap_options = [
        dict(
            name='Clip',
            display='clip',
        ),
        dict(
            name='Wrap',
            display='space',
        ),
    ]

    def __init__(self, todos, key_bindings, colorscheme):
        self.sort_order = 4
        self.display_style = 2
        self.wrap_style = 0

        self.todos = todos
        self.displayed_todos = []
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

        self.finalized_search_string = None

    def visible_lines(self):
        lines = self.loop.screen_size[1] - 1  # minus one for the header
        if self.toolbar_is_open:
            lines -= 1
        if self.searching:
            lines -= 1
        return lines

    def todo_widget_clicked(self, widget):
        body = widget.todo.body
        match = re.search('(\w+://[^\s]+)', body)
        if match:
            sub.call(['open', match.group(1)])

    def move_selection(self, index=None, from_last=False, relative=None):
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
                index = len(self.listbox.body) - 1
            else:
                index = self.listbox.get_focus()[1]
        if relative:
            index += relative
        if index >= len(self.listbox.body):
            index = len(self.listbox.body) - 1
        elif index < 0:
            index = 0
        self.listbox.set_focus(index)

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

    def run_sort(self):
        sort = self.sort_options[self.sort_order]
        if sort['hint'] == 'nat':
            self.todos.sorted(key=self.sort_options[2]['key'])  # pri
            self.todos.sorted(key=self.sort_options[1]['key'])  # due
            self.todos.sorted(key=self.sort_options[3]['key'])  # proj
        elif sort['key'] is None:
            self.todos.sorted_raw()
        else:
            self.todos.sorted(key=sort['key'])

    def toggle_sorting(self, button=None):
        self.sort_order = (self.sort_order + 1) % len(self.sort_options)
        self.refresh()
        self.update_header()
        if self.searching:
            self.run_search(self.finalized_search_string)

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
            self.change_focus()

    def toggle_wrapping(self, checkbox=None, state=None):
        self.wrap_style = (self.wrap_style + 1) % len(self.wrap_options)
        self.redraw_list()
        self.update_header()

    def project_widget_clicked(self):
        pass

    def toggle_border(self, checkbox=None, state=None):
        self.display_style = (self.display_style + 1) % len(self.display_options)
        self.redraw_list()
        self.update_header()

    def toggle_toolbar(self):
        self.toolbar_is_open = not self.toolbar_is_open
        self.update_header()

    def swap_down(self):
        focus, focus_index = self.listbox.get_focus()
        if not self.filtering and not self.searching:
            if focus_index+1 < len(self.listbox.body):
                self.todos.swap(focus_index, focus_index + 1)
                self.delete_todo_widgets()
                self.draw_list()
                self.move_selection(focus_index + 1)

    def swap_up(self):
        focus, focus_index = self.listbox.get_focus()
        if not self.filtering and not self.searching:
            if focus_index > 0:
                self.todos.swap(focus_index, focus_index - 1)
                self.delete_todo_widgets()
                self.draw_list()
                self.move_selection(focus_index - 1)

    def save_todos(self, button=None):
        self.todos.save()
        self.update_header("Saved")

    def archive_done_todos(self):
        if self.todos.archive_done():
            self.delete_todo_widgets()
            self.reload_todos_from_memory()
            self.move_selection(0)
            self.update_header()

    def reload_todos_from_file(self, button=None):
        self.delete_todo_widgets()
        self.todos.reload_from_file()
        self.reload_todos_from_memory()
        self.draw_list()
        self.update_header("Reloaded")

    def quit(self):
        raise urwid.ExitMainLoop()

    def set_priority(self, priority):
        focus, focus_index = self.listbox.get_focus()
        focus.todo.set_priority(priority)
        focus.update_todo()
        self.update_header()

    def change_focus(self):
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

    def toggle_complete(self):
        focus, focus_index = self.listbox.get_focus()
        if focus.todo.is_complete():
            focus.todo.incomplete()
        else:
            focus.todo.complete()
        focus.update_todo()
        self.update_header()

    def keystroke(self, key):
        if handle_keypress(self, key, 'listbox'):
            return
        return key

    def is_filtering(self):
        return self.searching or self.filtering

    def delete_todo(self, _=None):
        focus, display_index = self.listbox.get_focus()
        if self.todos.todo_items:
            item = self.todos.delete(focus.todo)
            del self.listbox.body[display_index]
            if self.is_filtering():
                try:
                    filtered_index = self.displayed_todos.index(item)
                    del self.displayed_todos[filtered_index]
                except ValueError:
                    pass
            self.update_header()

    def add_new_todo(self, position=False):
        if len(self.listbox.body) == 0:
            position = 'append'
        else:
            focus_index = self.listbox.get_focus()[1]

        if self.filtering:
            position = 'append'

        if position == 'append':
            new_index = self.todos.append('', add_creation_date=False)
        else:
            if position == 'insert_after':
                new_index = self.todos.insert(focus_index + 1, '', add_creation_date=False)
            elif position == 'insert_before':
                new_index = self.todos.insert(focus_index, '', add_creation_date=False)

        self.refresh()
        if position:
            if self.filtering:
                self.listbox.set_focus(len(self.listbox.body)-1)
            else:
                self.listbox.set_focus(new_index)
            self.update_header()

    def create_header(self, message=""):
        total = 0
        done = 0
        pending = 0
        for t in self.displayed_todos:
            total += 1
            if t.is_complete():
                done += 1
            else:
                pending += 1

        return urwid.AttrMap(
            urwid.Columns([
                urwid.Text([
                    ('header_todo_count', "{0} Todos ".format(total)),
                    ('header_todo_pending_count', " {0} Pending ".format(pending)),
                    ('header_todo_done_count', " {0} Done ".format(done)),
                    ('header', ' ' + ' '.join([
                        self.wrap_options[self.wrap_style]['display'],
                        self.display_options[self.display_style]['hint'],
                        self.sort_hint(),
                    ])),
                ]),
                urwid.Text(('header_file', "{0} {1} ".format(message, self.todos.file_path)), align='right')
            ]), 'header')

    def sort_hint(self):
        return self.sort_options[self.sort_order]['hint']

    def create_toolbar(self):
        def button(name, on_press):
            return urwid.Padding(
                urwid.AttrMap(
                    urwid.Button(name, on_press=on_press),
                    'header', 'plain_selected'
                ), right=2
            )
        return urwid.AttrMap(urwid.Columns(button(name, cb) for name, cb in [
            ('word wrap', self.toggle_wrapping),
            ('border', self.toggle_border),
            ([('header_file', 'R'), 'eload'], self.toggle_wrapping),
            ([('header_file', 'S'), 'ave'], self.save_todos),
            ([('header_file', 's'), 'ort: ' + self.sort_hint()], self.save_todos),
            ([('header_file', 'f'), 'ilter'], self.toggle_filter_panel),
        ]), 'header')

    def search_box_updated(self, edit_widget, new_contents):
        self.search_string = new_contents
        self.search_todo_list(self.search_string)

    def search_todo_list(self, search_string="", invert=False):
        if search_string and self.todos.valid_search(search_string):
            self.delete_todo_widgets()
            self.searching = True

            self.displayed_todos = list(self.todos.search(search_string, invert=invert))
            self.draw_list()

    def start_search(self):
        self.searching = True
        self.update_footer()
        self.frame.set_focus('footer')

    def run_search(self, search_string, invert=False):
        self.search_todo_list(search_string, invert=invert)
        self.finalize_search()

    def finalize_search(self):
        # TODO hack because this shouldn't be cleared...
        if self.search_string:
            self.finalized_search_string = self.search_string
        self.search_string = ''
        self.frame.set_focus('body')
        self.update_header()
        for widget in self.listbox.body:
            widget.update_todo()

    def clear_filters(self, refresh=True, button=None):
        self.filtering = False
        self.active_projects = []
        self.active_contexts = []
        if refresh:
            self.redraw_widgets()

    def clear_searches(self, refresh=True, button=None):
        self.searching = False
        self.search_string = ''
        if refresh:
            self.redraw_widgets()

    def clear_all_filters(self, refresh=True):
        self.clear_filters(False)
        self.clear_searches(refresh)

    def redraw_widgets(self, focus_index=0):
        self.delete_todo_widgets()
        # TODO should perform any search, filtering, sorting
        self.reload_todos_from_memory()
        self.view.set_focus(focus_index)
        self.update_filters()
        self.update_header()
        self.update_footer()

    def create_footer(self):
        if self.searching:
            self.search_box = SearchWidget(self, self.key_bindings, edit_text=self.search_string)
            w = urwid.AttrMap(urwid.Columns([
                (1, urwid.Text('/')),
                self.search_box,
                (16, urwid.AttrMap(
                    urwid.Button([('header_file', 'C'), 'lear Search'], on_press=self.clear_searches),
                    'header', 'plain_selected'))
            ]), 'footer')
            urwid.connect_signal(self.search_box, 'change', self.search_box_updated)
        else:
            w = None
        return w

    def format_tooltip(self, name):
        key_column_width = 12
        data = self.key_bindings.key_bindings[name]
        log.info(name)
        keys = ', '.join(data['keys'])
        return '{keys} - {tooltip}'.format(keys=keys.ljust(key_column_width),
                                           tooltip=data['tooltip'])

    def help_block(self, title, names):
        header_highlight = 'plain_selected'
        return [
            urwid.Divider(),
            urwid.AttrWrap(urwid.Text(title), header_highlight),
            urwid.Text('\n'.join(self.format_tooltip(name) for name in names)),
        ]

    def create_help_panel(self):
        return urwid.AttrMap(
            urwid.LineBox(
                urwid.Padding(
                    ViListBox(
                        self.key_bindings,
                        self.help_block('General', [
                            'toggle-help', 'quit', 'toggle-toolbar', 'toggle-wrapping',
                            'toggle-borders', 'save', 'reload',
                        ]) +
                        self.help_block('Movement', [
                            'mouse click', 'down', 'up', 'top', 'bottom',
                            'left', 'right', 'change-focus',
                        ]) +
                        self.help_block('Manipulating Todo Items', [
                            'toggle-complete', 'archive', 'append', 'insert-after',
                            'insert-before', 'edit', 'delete', 'swap-down', 'swap-up',
                        ]) +
                        self.help_block('While Editing a Todo', [
                            'edit-complete', 'save-item', 'edit-move-left', 'edit-move-right',
                            'edit-word-left', 'edit-word-right', 'edit-home', 'edit-end',
                            'edit-delete-word', 'edit-delete-end', 'edit-delete-beginning', 'edit-paste',
                        ]) +
                        self.help_block('Sorting', ['toggle-sorting']) +
                        self.help_block('Filtering', ['toggle-filter', 'clear-filter']) +
                        self.help_block('Searching', ['search', 'search-end', 'search-clear'])
                    ),
                    left=1, right=1, min_width=10), title='Key Bindings'), 'default')

    def create_filter_panel(self):
        box = ViPile(
            self.key_bindings,
            [urwid.Text('Contexts & Projects', align='center')] +
            [urwid.Divider(u'─')] +
            [urwid.AttrWrap(ViCheckbox(c, state=(c in self.active_contexts), on_state_change=self.checkbox_clicked, user_data=['context', c]), 'context_dialog_color', 'context_selected') for c in self.todos.all_contexts()] +
            [urwid.Divider(u'─')] +
            [urwid.AttrWrap(ViCheckbox(p, state=(p in self.active_projects), on_state_change=self.checkbox_clicked, user_data=['project', p]), 'project_dialog_color', 'project_selected') for p in self.todos.all_projects()] +
            [urwid.Divider(u'─')] +
            [urwid.AttrMap(urwid.Button(['Clear ', ('header_file_dialog_color','F'), 'ilters'], on_press=self.clear_filters), 'dialog_color', 'plain_selected') ]
        )
        box = urwid.ListBox([box] + [urwid.Divider()])
        w = urwid.AttrMap(urwid.Padding(box, left=1, right=1, min_width=10), 'dialog_color')

        bg = urwid.AttrWrap(urwid.SolidFill(u" "), 'dialog_background')  # u"\u2592"
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

    def draw_list(self):
        wrap = self.wrap_options[self.wrap_style]['display']
        border = self.display_options[self.display_style]['display']
        project_sort = self.sort_options[self.sort_order].get('allow_tree', False)
        last_project = None
        if border == 'tree' and not project_sort:
            border = 'no border'
        for t in self.displayed_todos:
            if border == 'tree' and t.projects:
                project = t.projects[0]
                if project != last_project:
                    depth = project.count('.')
                    self.listbox.body.append(urwid.Text(('project', '    ' * depth + project)))
                last_project = project
            self.listbox.body.append(TodoWidget(t, self.key_bindings, self.colorscheme, self,
                                                wrapping=wrap,
                                                border=border))

    def redraw_list(self):
        self.delete_todo_widgets()
        self.draw_list()

    def refresh(self, reset=True):
        todo, index = self.listbox.get_focus()

        if reset:
            self.displayed_todos = self.todos.todo_items
        self.run_sort()
        self.redraw_list()
        if todo:
            for i, widget in enumerate(self.listbox.body):
                if isinstance(widget, TodoWidget) and widget.todo == todo.todo:
                    self.listbox.set_focus(i)

    def reload_todos_from_memory(self):
        self.displayed_todos = self.todos.todo_items
        self.draw_list()

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
            self.update_header()
        else:
            self.clear_filters()

    def filter_todo_list(self):
        self.delete_todo_widgets()
        self.displayed_todos = list(self.todos.filter_contexts_and_projects(self.active_contexts, self.active_projects))
        self.filtering = True
        self.draw_list()

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

    def update_footer(self, message=''):
        self.frame.footer = self.create_footer()

    def main(self):
        urwid.set_encoding('UTF-8')

        self.listbox = ViListBox(self.key_bindings, urwid.SimpleListWalker([]))
        self.refresh()
        self.header = self.create_header()
        self.footer = self.create_footer()

        self.frame = urwid.Frame(urwid.AttrMap(self.listbox, 'plain'), header=self.header, footer=self.footer)

        self.view = ViColumns(self.key_bindings, [
            ('weight', 2, self.frame)
        ])

        self.loop = urwid.MainLoop(self.view, self.palette, unhandled_input=self.keystroke)
        self.loop.screen.set_terminal_properties(colors=256)
        self.loop.run()

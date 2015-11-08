import os.path as op
import yaml


class KeyBindings:
    user_keys = []

    def __init__(self, user_keys):
        self.user_keys = user_keys
        self.key_bindings = {}
        self.fill_with_defaults()
        self.fillWithUserKeys(user_keys)

    def fillWithUserKeys(self, users_keys):
        for bind in users_keys:
            key = self.userKeysToList(users_keys[bind])
            try:
                default = self.key_bindings[bind]
                self.key_bindings[bind] = key
            except KeyError:
                print("KeyBind \""+bind+"\" not found")

    def fill_with_defaults(self):
        directory = op.dirname(__file__)
        with open(op.join(directory, 'default_keys.yaml')) as f:
            config = yaml.load(f)
        for name, data in config['key_bindings'].iteritems():
            if isinstance(data['keys'], basestring):
                data['keys'] = [data['keys']]
            self.key_bindings[name] = data
        internal = dict()
        internal['toggle-wrapping']  = ['w']
        internal['save']             = ['S']
        internal['reload']           = ['R']
        internal['down']             = ['j', 'down']
        internal['up']               = ['k', 'up']
        internal['top']              = ['g']
        internal['right']            = ['L', 'right']
        internal['left']             = ['H', 'left']
        internal['bottom']           = ['G']
        internal['change-focus']     = ['tab']
        internal['toggle-complete']  = ['x']
        internal['archive']          = ['X']
        internal['append']           = ['n']
        internal['insert-after']     = ['o']
        internal['insert-before']    = ['O']
        internal['save-item']        = ['enter', 'esc']
        internal['edit']             = ['enter', 'i', 'a']
        internal['delete']           = ['D']
        internal['swap-down']        = ['J']
        internal['swap-up']          = ['K']
        internal['edit-complete']    = ['tab']
        internal['edit-save']        = ['return']
        internal['edit-move-left']   = ['left']
        internal['edit-move-right']  = ['right']
        internal['edit-word-left']   = ['meta b', 'ctrl b']
        internal['edit-word-right']  = ['meta f', 'ctrl f']
        internal['edit-end']         = ['ctrl e', 'end']
        internal['edit-home']        = ['ctrl a', 'home']
        internal['edit-delete-word'] = ['ctrl w']
        internal['edit-delete-end']  = ['ctrl k']
        internal['edit-delete-beginning']  = ['ctrl u']
        internal['edit-paste']       = ['ctrl y']
        internal['toggle-filter']    = ['f']
        internal['clear-filter']     = ['F']
        internal['toggle-sorting']   = ['s']
        internal['search']           = ['/']
        internal['search-end']       = ['enter']
        internal['search-clear']     = ['C']

        for k, v in internal.iteritems():
            self.key_bindings[k] = dict(
                keys=v,
            )

    def __getitem__(self, index):
        return ", ".join(self.key_bindings[index])

    def userKeysToList(self, userKey):
        keys = userKey.split(',')
        return [key.strip() for key in keys]

    def get_key_binding(self, bind):
        # intermediately treat either string->[key] or string->('key'->[key])
        # as permissible
        value = self.key_bindings.get(bind, [])
        if isinstance(value, list):
            return value
        elif isinstance(value, dict):
            return value.get('keys', [])

    def is_bound_to(self, key, bind):
        return key in self.get_key_binding(bind)

    def get_handler(self, key, context):
        # TODO create data structure to optimize this...
        for name, data in self.key_bindings.iteritems():
            if key in data['keys']:
                for context_config in data.get('context', []):
                    if context_config['handler'] == context:
                        return context_config['callback'], context_config.get('kwargs', {})
        return None, {}

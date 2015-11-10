import yaml
from pkg_resources import resource_stream


class KeyBindings:
    user_keys = []

    def __init__(self, user_keys):
        self.user_keys = user_keys
        self.key_bindings = {}
        self.fill_with_defaults()
        self.fill_with_user_keys(user_keys)

    def fill_with_user_keys(self, users_keys):
        for bind in users_keys:
            key = self.user_keys_to_list(users_keys[bind])
            try:
                default = self.key_bindings[bind]
                self.key_bindings[bind] = key
            except KeyError:
                print("KeyBind \""+bind+"\" not found")

    def fill_with_defaults(self):
        with resource_stream(__package__, 'default_keys.yaml') as f:
            config = yaml.load(f)
        for name, data in config['key_bindings'].iteritems():
            if isinstance(data['keys'], basestring):
                data['keys'] = [data['keys']]
            self.key_bindings[name] = data

    def __getitem__(self, index):
        return ", ".join(self.get_key_binding(index))

    def user_keys_to_list(self, userKey):
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
            if key in data['keys'] and data['handler'] == context:
                return data['callback'], data.get('kwargs', {})
        return None, {}

"""TACTIC's Container, scoped to one request instead of a global thread map.

Adapted from pyasm/common/container.py; see LICENSE.TACTIC/source_manifest.json.
"""


class Container:
    def __init__(self):
        self.info = {}

    def get_data(self):
        return self.info

    def clear_data(self):
        self.info = {}

    @staticmethod
    def get_instance():
        from pyasm.search.search import _context
        return _context.get().container

    @staticmethod
    def put(key, value):
        Container.get_instance().info[key] = value

    set = put

    @staticmethod
    def get(key):
        return Container.get_instance().info.get(key)

    @staticmethod
    def has(key):
        return key in Container.get_instance().info

    @staticmethod
    def remove(key):
        Container.get_instance().info.pop(key, None)

    @staticmethod
    def get_seq(key):
        seq = Container.get(key)
        if seq is None:
            seq = []
            Container.put(key, seq)
        return seq

    @staticmethod
    def append_seq(key, value):
        seq = Container.get_seq(key)
        seq.append(value)
        return seq

    @staticmethod
    def clear_seq(key):
        del Container.get_seq(key)[:]

    @staticmethod
    def _get_dict(dict_name):
        data = Container.get(dict_name)
        if data is None:
            data = {}
            Container.put(dict_name, data)
        return data

    @staticmethod
    def put_dict(dict_name, key, value):
        Container._get_dict(dict_name)[key] = value

    @staticmethod
    def get_dict(dict_name, key):
        return Container._get_dict(dict_name).get(key)

    @staticmethod
    def get_full_dict(dict_name):
        return Container._get_dict(dict_name)

    @staticmethod
    def clear_dict(dict_name):
        Container.put(dict_name, {})

    @staticmethod
    def increment(key):
        counter = Container.get(key)
        if counter is None:
            counter = 1
        else:
            counter += 1
        Container.put(key, counter)
        return counter

    @staticmethod
    def decrement(key):
        counter = Container.get(key)
        if counter is None:
            counter = -1
        else:
            counter -= 1
        Container.put(key, counter)
        return counter

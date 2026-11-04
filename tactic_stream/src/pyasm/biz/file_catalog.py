"""Immutable, bounded B+tree catalog for file-project streams and drafts."""
from bisect import bisect_left, bisect_right
from collections import OrderedDict


class FileCatalog:
    PAGE_SIZE = 256
    CACHE_SIZE = 512

    def __init__(self, load, save):
        self.load, self.save = load, save
        self.cache = OrderedDict()

    def node(self, code):
        if code in self.cache:
            self.cache.move_to_end(code)
            return self.cache[code]
        node = self.load(code)
        self.cache[code] = node
        if len(self.cache) > self.CACHE_SIZE:
            self.cache.popitem(last=False)
        return node

    def store(self, node):
        code = self.save(node)
        self.cache[code] = node
        self.cache.move_to_end(code)
        if len(self.cache) > self.CACHE_SIZE:
            self.cache.popitem(last=False)
        actions=self.action_stats_node(node)
        return {'code': code, 'max': node['items'][-1]['path'] if node['leaf'] else node['items'][-1]['max'],
                'count': sum(not item.get('deleted') for item in node['items']) if node['leaf'] else sum(item['count'] for item in node['items']),
                'bytes': sum(item['size'] for item in node['items']) if node['leaf'] else sum(item['bytes'] for item in node['items']),
                'actions':actions, 'waiting_uploads':self.waiting_uploads_node(node)}

    @staticmethod
    def waiting_uploads_node(node):
        if node['leaf']:
            return sum(1 for item in node['items'] if item.get('action')=='checkout'
                       and (not item.get('file') or item['file'].get('deleted'))
                       and (not item.get('base') or item['base'].get('deleted')))
        if any(item.get('waiting_uploads') is None for item in node['items']):
            return None
        return sum(item['waiting_uploads'] for item in node['items'])

    def waiting_uploads(self,root):
        return self.waiting_uploads_node(self.node(root))

    @staticmethod
    def action_stats_node(node):
        if not node['leaf'] and any(item.get('actions') is None for item in node['items']):return None
        counts={}
        for item in node['items']:
            values={item['action']:1} if node['leaf'] and not item.get('deleted') and item.get('action') else {} if node['leaf'] else item['actions']
            for action,count in values.items():counts[action]=counts.get(action,0)+count
        return counts

    def action_stats(self, root):
        """Read maintained summaries, never scan an old million-file tree for UI counts."""
        return self.action_stats_node(self.node(root))

    def empty(self):
        return self.save({'leaf': True, 'items': []})

    def get(self, root, path):
        node = self.node(root)
        while not node['leaf']:
            index = bisect_left([item['max'] for item in node['items']], path)
            if index == len(node['items']):
                return None
            node = self.node(node['items'][index]['code'])
        index = bisect_left([item['path'] for item in node['items']], path)
        return node['items'][index] if index < len(node['items']) and node['items'][index]['path'] == path else None

    def update(self, root, operations):
        """Input is one bounded, sorted chunk; rewrite only touched pages."""
        operations = sorted(operations, key=lambda item: item['path'])
        def apply(code, ops):
            if not ops:
                node = self.node(code)
                return [self.store(node)] if node['items'] else []
            node = self.node(code)
            if node['leaf']:
                entries = {item['path']: item for item in node['items']}
                for op in ops:
                    if op.get('delete'):
                        entries.pop(op['path'], None)
                    else:
                        entries[op['path']] = op
                items = sorted(entries.values(), key=lambda item: item['path'])
            else:
                items, position = [], 0
                for index, child in enumerate(node['items']):
                    end = len(ops) if index == len(node['items']) - 1 else bisect_right(
                        [op['path'] for op in ops], child['max'], lo=position)
                    items.extend(apply(child['code'], ops[position:end]) if end > position else [child])
                    position = end
            return [self.store({'leaf': node['leaf'], 'items': items[offset:offset + self.PAGE_SIZE]})
                    for offset in range(0, len(items), self.PAGE_SIZE)]
        children = apply(root, operations)
        if not children:
            return self.empty()
        while len(children) > 1:
            children = [self.store({'leaf': False, 'items': children[offset:offset + self.PAGE_SIZE]})
                        for offset in range(0, len(children), self.PAGE_SIZE)]
        return children[0]['code']

    def entries(self, root, after='', prefix='', include_deleted=False, start=''):
        lower = max(after, prefix, start)
        def walk(code):
            node = self.node(code)
            if node['leaf']:
                for item in node['items']:
                    path = item['path']
                    if path > after and path >= start and path.startswith(prefix):
                        if include_deleted or not item.get('deleted'):
                            yield item
                    elif prefix and path >= prefix and not path.startswith(prefix):
                        return
            else:
                for child in node['items']:
                    if child['max'] < lower or child['max'] <= after or (not include_deleted and child['count'] == 0):
                        continue
                    yield from walk(child['code'])
                    if prefix and child['max'] > prefix and not child['max'].startswith(prefix):
                        break
        yield from walk(root)

    def children(self, root, directory='', after=''):
        # Seek past an entire directory range; never enumerate its descendant files.
        start = after[:-1] + '0' if after.endswith('/') else after
        while True:
            entry = next(self.entries(root, after, directory, start=start), None)
            if entry is None:
                return
            name = entry['path'][len(directory):].split('/', 1)[0]
            path = directory + name
            if entry['path'] == path:
                yield {**entry, 'kind': 'file', 'name': name}
                after, start = path, path
            else:
                yield {'kind': 'directory', 'name': name, 'path': path + '/'}
                after, start = '', path + '0'

    def prefix_stats(self, root, prefix=''):
        """Count a path range by subtree summaries, loading only boundary pages."""
        if not prefix:
            return self.stats(root)
        end = prefix + '\U0010ffff'
        result = {'files':0,'bytes':0}
        def visit(code, lower=''):
            node = self.node(code)
            if node['leaf']:
                for item in node['items']:
                    if item['path'].startswith(prefix) and not item.get('deleted'):
                        result['files'] += 1
                        result['bytes'] += item['size']
                return
            for child in node['items']:
                if child['max'] >= prefix and lower < end:
                    if lower >= prefix and child['max'] < end:
                        result['files'] += child['count']
                        result['bytes'] += child['bytes']
                    else:
                        visit(child['code'], lower)
                lower = child['max']
        visit(root)
        return result

    def stats(self, root):
        node = self.node(root)
        return {'files': sum(not item.get('deleted') for item in node['items']) if node['leaf'] else sum(item['count'] for item in node['items']),
                'bytes': sum(item['size'] for item in node['items']) if node['leaf'] else sum(item['bytes'] for item in node['items'])}

    def diff(self, before, after, cursor=''):
        """Merge two trees, skipping identical subtrees, with bounded traversal memory."""
        stacks = [[('node', before)], [('node', after)]]
        def expand(stack):
            kind, value = stack.pop()
            node = self.node(value)
            if node['leaf']:
                stack.extend(('entry', item) for item in reversed(node['items']) if item['path'] > cursor)
            else:
                stack.extend(('node', item['code']) for item in reversed(node['items']) if item['max'] > cursor)
        while stacks[0] or stacks[1]:
            left, right = stacks
            if left and right and left[-1][0] == right[-1][0] == 'node' and left[-1][1] == right[-1][1]:
                left.pop()
                right.pop()
                continue
            if any(stack and stack[-1][0] == 'node' for stack in stacks):
                for stack in stacks:
                    if stack and stack[-1][0] == 'node':
                        expand(stack)
                continue
            old = left[-1][1] if left else None
            new = right[-1][1] if right else None
            if new is None or (old is not None and old['path'] < new['path']):
                left.pop()
                yield old['path'], old, None
            elif old is None or new['path'] < old['path']:
                right.pop()
                yield new['path'], None, new
            else:
                left.pop()
                right.pop()
                if old != new:
                    yield old['path'], old, new

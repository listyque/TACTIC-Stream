"""Catalog invariants across three tree levels, deletion and arbitrary edits."""
import unittest
from hashlib import sha256
import random

from pyasm.biz.file_catalog import FileCatalog
from pyasm.biz.file_project import encode


class FileCatalogTest(unittest.TestCase):
    def test_action_summaries_survive_partial_edits_without_scanning_old_trees(self):
        pages={}
        def save(node):
            key=str(len(pages));pages[key]=node;return key
        catalog=FileCatalog(pages.__getitem__,save)
        root=catalog.empty()
        root=catalog.update(root,[{'path':str(index).zfill(4),'size':1,'action':'checkout' if index<300 else 'write'} for index in range(700)])
        self.assertEqual(catalog.action_stats(root),{'checkout':300,'write':400})
        root=catalog.update(root,[{'path':'0000','size':0,'deleted':True},{'path':'0001','size':1,'action':'delete'}])
        self.assertEqual(catalog.action_stats(root),{'checkout':298,'delete':1,'write':400})
        node=catalog.node(root);old={**node,'items':[{key:value for key,value in item.items() if key!='actions'} for item in node['items']]}
        self.assertIsNone(catalog.action_stats_node(old))

    def test_directory_children_skip_descendants_and_keep_adjacent_names(self):
        pages, reads = {}, []
        def save(data):
            key = str(len(pages))
            pages[key] = data
            return key
        def load(key):
            reads.append(key)
            return pages[key]
        catalog = FileCatalog(load, save)
        root = catalog.empty()
        names = ['a', 'a0', 'a0/x.txt', 'a/深い/\U0010ffff.txt', 'z.txt']
        names += ['a/many/%06d.txt' % index for index in range(70000)]
        for start in range(0, len(names), 1000):
            root = catalog.update(root, [{'path': name, 'size': 1} for name in names[start:start + 1000]])
        catalog.cache.clear()
        reads.clear()
        children = list(catalog.children(root))
        self.assertEqual([row['path'] for row in children], ['a', 'a/', 'a0', 'a0/', 'z.txt'])
        self.assertLess(len(reads), 16)
        self.assertEqual([row['path'] for row in catalog.children(root, after='a/')], ['a0', 'a0/', 'z.txt'])
        self.assertEqual([row['path'] for row in catalog.children(root, 'a/')], ['a/many/', 'a/深い/'])
        root = catalog.update(root, [{'path': 'gone/file', 'size': 1}])
        root = catalog.update(root, [{'path': 'gone/file', 'delete': True}])
        self.assertNotIn('gone/', [row['path'] for row in catalog.children(root)])

    def test_bounded_tree_and_immutable_roots(self):
        pages = {}
        def store(data):
            self.assertLessEqual(len(data['items']), 256)
            key = sha256(encode(data).encode('utf-8')).hexdigest()
            pages[key] = data
            return key
        catalog = FileCatalog(pages.__getitem__, store)
        root = catalog.empty()
        for start in range(0, 70000, 1000):
            root = catalog.update(root, [{'path': '%06d' % index, 'size': index} for index in range(start, start + 1000)])
        original = root
        self.assertEqual(catalog.stats(root)['files'], 70000)
        indices = random.Random(7).sample(range(70000), 1000)
        root = catalog.update(root, [{'path': '%06d' % index, 'delete': True} for index in indices])
        self.assertEqual(catalog.stats(root)['files'], 69000)
        self.assertEqual(catalog.stats(original)['files'], 70000)
        for index in indices[:10]:
            self.assertIsNone(catalog.get(root, '%06d' % index))
            self.assertEqual(catalog.get(original, '%06d' % index)['size'], index)
        expected = ['%06d' % index for index in range(10000, 11000) if index not in indices]
        self.assertEqual([item['path'] for item in catalog.entries(root, prefix='010')], expected)
        self.assertLessEqual(len(catalog.cache), 64)

    def test_diff_skips_unchanged_pages_and_handles_split_merge_and_cursor(self):
        pages, loaded = {}, []
        def store(node):
            key = sha256(encode(node).encode()).hexdigest()
            pages[key] = node
            return key
        def load(key):
            loaded.append(key)
            return pages[key]
        catalog = FileCatalog(load, store)
        root = catalog.empty()
        for offset in range(0, 70000, 1000):
            root = catalog.update(root, [{'path': '%06d' % i, 'size': i} for i in range(offset, offset + 1000)])
        changed = catalog.update(root, [{'path': '000123', 'size': 5}, {'path': '069999', 'delete': True}])
        catalog.cache.clear()
        loaded.clear()
        self.assertEqual([p for p, _, _ in catalog.diff(root, changed)], ['000123', '069999'])
        self.assertLess(len(loaded), 20)
        self.assertEqual([p for p, _, _ in catalog.diff(root, changed, '000123')], ['069999'])
        small = catalog.update(catalog.empty(), [{'path': str(i), 'size': i} for i in range(255)])
        split = catalog.update(small, [{'path': str(i), 'size': i} for i in range(255, 510)])
        self.assertEqual(len(list(catalog.diff(small, split))), 255)
        merged = catalog.update(split, [{'path': str(i), 'delete': True} for i in range(256, 510)])
        old = {v['path']: v for v in catalog.entries(split)}
        new = {v['path']: v for v in catalog.entries(merged)}
        expected = [(p, old.get(p), new.get(p)) for p in sorted(old.keys() | new.keys()) if old.get(p) != new.get(p)]
        self.assertEqual(list(catalog.diff(split, merged)), expected)

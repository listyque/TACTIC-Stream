"""Bounded, reversible workspace path mappings; paths stay relative to the client root."""
import re


class FileView:
    LIMIT = 256

    @staticmethod
    def pattern(value):
        from tactic.command.file_project_cmd import logical_path
        if not isinstance(value, str) or len(value.encode('utf-8')) > 2048:
            raise ValueError('Invalid workspace pattern')
        if value != '...':
            logical_path(value.replace('...', '__recursive__').replace('*', '__file__'))
        if '...' in value and (value.count('...') != 1 or not value.endswith('...') or
                              (value != '...' and not value.endswith('/...'))):
            raise ValueError('Recursive wildcard must be the final path component')
        tokens = re.split(r'(\.\.\.|\*)', value)
        wildcards = [token for token in tokens if token in ('...', '*')]
        if len(wildcards) > 16:
            raise ValueError('Too many mapping wildcards')
        expression = ''.join('(.*)' if token == '...' else '([^/]*)' if token == '*' else re.escape(token) for token in tokens)
        return re.compile('^' + expression + '$'), tokens, wildcards

    def __init__(self, rules, case_sensitive=True):
        from tactic.command.file_project_cmd import identifier
        if not isinstance(rules, list) or not 1 <= len(rules) <= self.LIMIT:
            raise ValueError('Workspace requires 1..256 mapping rules')
        self.rules, self.compiled, self.case_sensitive = [], [], case_sensitive
        includes = []
        for rule in rules:
            if not isinstance(rule, dict) or set(rule) - {'stream', 'source', 'target', 'exclude', 'writable'}:
                raise ValueError('Invalid workspace mapping')
            stream = identifier(rule.get('stream'))
            for flag in ('exclude', 'writable'):
                if flag in rule and not isinstance(rule[flag], bool):
                    raise ValueError('Mapping flags must be boolean')
            source = self.pattern(rule.get('source'))
            excluded = rule.get('exclude', False)
            target = None if excluded else self.pattern(rule.get('target'))
            if target and not case_sensitive:
                target = (re.compile(target[0].pattern, re.IGNORECASE), target[1], target[2])
            if target and source[2] != target[2]:
                raise ValueError('Source and target must use the same wildcard sequence')
            value = {'stream': stream, 'source': rule['source'], 'exclude': excluded,
                     'writable': rule.get('writable', False)}
            if target:
                value['target'] = rule['target']
                prefix = re.split(r'\.\.\.|\*', rule['target'], maxsplit=1)[0]
                prefix = prefix if case_sensitive else prefix.casefold()
                exact = not target[2]
                for old_prefix, old_exact in includes:
                    overlap = prefix == old_prefix if exact and old_exact else prefix.startswith(old_prefix) or old_prefix.startswith(prefix)
                    if overlap:
                        raise ValueError('Overlapping workspace destinations; use distinct local directories')
                includes.append((prefix, exact))
            self.rules.append(value)
            self.compiled.append((source, target))
        if not includes:
            raise ValueError('Workspace requires an include mapping')

    @staticmethod
    def substitute(tokens, groups):
        groups = iter(groups)
        return ''.join(next(groups) if token in ('...', '*') else token for token in tokens)

    def key(self, path):
        return path if self.case_sensitive else path.casefold()

    def forward(self, stream, path):
        from tactic.command.file_project_cmd import logical_path
        selected = None
        for index, (rule, (source, target)) in enumerate(zip(self.rules, self.compiled)):
            match = source[0].fullmatch(path) if rule['stream'] == stream else None
            if match:
                selected = None if rule['exclude'] else {'path': logical_path(self.substitute(target[1], match.groups())),
                    'stream': stream, 'source_path': path, 'writable': rule['writable'], 'mapping': index}
        return selected

    def reverse(self, path):
        for rule, (source, target) in zip(self.rules, self.compiled):
            if target is None:
                continue
            match = target[0].fullmatch(path)
            if match:
                source_path = self.substitute(source[1], match.groups())
                mapped = self.forward(rule['stream'], source_path)
                if mapped and self.key(mapped['path']) == self.key(path):
                    return mapped
        return None

    @staticmethod
    def prefix(pattern):
        return re.split(r'\.\.\.|\*', pattern, maxsplit=1)[0]

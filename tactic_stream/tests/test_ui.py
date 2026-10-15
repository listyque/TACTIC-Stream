"""Keep UI text/catalogs and theme roles consistent as the admin grows."""
import ast
import json
import re
import unittest

from test_foundation import ROOT


class UiResources(unittest.TestCase):
    def test_shipped_translations_cover_ui_and_transport_messages(self):
        src = ROOT / 'frontend/src'
        sources = set()
        for path in list(src.rglob('*.vue')) + list(src.rglob('*.js')):
            text = path.read_text(encoding='utf-8')
            sources.update(re.findall(r"\bt\('([^']+)'", text))
            sources.update(re.findall(r"label: '([^']+)'", text))
            sources.update(re.findall(r'"(?:label|description)": "([^"]+)"', text))
            sources.update(re.findall(r'\s(?:title|description|label)="([^"{}]+)"', text))
        sources.update(('Signing in…', 'Sign in', 'Session ended. Sign in again.',
                        'Unable to reach the server.', 'Request failed.',
                        'The save result is unknown. Close this form and refresh the records before trying again.',
                        'Connection context changed. Close this form and reopen it before saving.'))
        tree = ast.parse((ROOT / 'src/tactic_stream/server/app.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Tuple) and
                    [item.id for item in target.elts if isinstance(item, ast.Name)] == ['status', 'code', 'message']
                    for target in node.targets):
                if isinstance(node.value.elts[-1], ast.Constant):
                    sources.add(ast.literal_eval(node.value.elts[-1]))
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == 'error' and isinstance(value, ast.Constant):
                        sources.add(value.value)
        placeholders = lambda text: set(re.findall(r'\{(\w+)\}', text))
        for path in src.glob('locales/*.json'):
            catalog = json.loads(path.read_text(encoding='utf-8'))
            if path.stem != 'en':  # English source strings are the intentional i18n.js fallback.
                self.assertFalse(sources - catalog.keys(), f'{path.name}: missing source strings')
            for source, translated in catalog.items():
                with self.subTest(locale=path.stem, source=source):
                    self.assertIsInstance(translated, str)
                    self.assertTrue(translated.strip())
                    self.assertEqual(placeholders(source), placeholders(translated))

    def test_components_use_translation_and_shared_theme_roles(self):
        src = ROOT / 'frontend/src'
        for path in src.rglob('*.vue'):
            text = path.read_text(encoding='utf-8')
            template = text.split('<template>', 1)[1]
            self.assertNotRegex(text, r'[А-Яа-яЁё]', f'{path.name}: use English source and a catalog')
            for native_tag in re.findall(r'<[a-z][\w-]*\b[^>]*', template):
                self.assertNotRegex(native_tag, r'(?<!:)(?:aria-label|placeholder)="', f'{path.name}: translate native accessible labels')
            # Vue comparisons inside quoted attributes are not text nodes.
            text_nodes = re.sub(r'<(?:[^>\"\']|\"[^\"]*\"|\'[^\']*\')*>', '<>', template)
            literal_text = {item.strip() for item in re.findall(r'>([^<>{}]*[A-Za-z][^<>{}]*)<', text_nodes)}
            self.assertFalse(literal_text - {'T', 'TACTIC Stream'}, f'{path.name}: untranslated text nodes')
        styles = (src / 'style.css').read_text(encoding='utf-8')
        self.assertNotRegex(styles, r'#[0-9a-fA-F]{3,8}\b|rgba?\(')
        # QML dimensions intentionally retain native pixel values; palette colors stay in Theme.

    def test_language_and_theme_catalogs_have_resources(self):
        src = ROOT / 'frontend/src'
        appearance = (src / 'appearance.js').read_text(encoding='utf-8')
        language_block = appearance.split('export const languages = [', 1)[1].split(']', 1)[0]
        languages = re.findall(r"value: '([^']+)'", language_block)
        self.assertEqual(languages[:2], ['en', 'ru'])
        for language in languages:
            if language != 'en':
                self.assertTrue((src / 'locales' / (language + '.json')).is_file())
        catalog = (src / 'appearanceCatalog.js').read_text(encoding='utf-8')
        theme_block = catalog.split('export const themes = ', 1)[1].split('\nexport ', 1)[0]
        for theme in [item['value'] for item in json.loads(theme_block)]:
            if theme != 'md3':
                self.assertIn(f'[data-theme="{theme}"]', (src / 'theme.css').read_text(encoding='utf-8'))

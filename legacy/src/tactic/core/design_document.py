"""Lossless *targeted* editing of original widget_config documents.

Storage matches CustomLayoutEditSaveCmd: <html> owns <style>; mako, kwargs,
behavior(s), callback(s) are siblings. We do not execute template/script text.
No arbitrary XML is evaluated to discover a Python class.
"""
from copy import deepcopy
import ast
import json
import re
from lxml import etree as E

MAX_BYTES = 1024 * 1024
NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_.@:-]{0,199}$')
SECTIONS = ('html', 'style', 'mako', 'kwargs', 'behavior', 'callback')


def bounded(value, limit=MAX_BYTES):
    if not isinstance(value, str) or '\x00' in value or len(value.encode('utf-8')) > limit:
        raise ValueError('Текст должен быть UTF-8 без NUL, не более %s байт' % limit)
    return value


def parse(text):
    bounded(text, MAX_BYTES * 4)
    if re.search(r'<!\s*(DOCTYPE|ENTITY)', text, re.I):
        raise ValueError('DOCTYPE и внешние сущности запрещены')
    parser = E.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                         strip_cdata=False, remove_comments=False, remove_blank_text=False)
    try:
        root = E.fromstring(text.encode('utf-8'), parser)
    except E.XMLSyntaxError as exc:
        raise ValueError('XML: %s' % str(exc).split('\n')[0]) from exc
    if root.tag != 'config' or sum(1 for _ in root.iter()) > 20000:
        raise ValueError('Ожидается ограниченный <config> документ')
    return root


def view_name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError('Некорректное имя view')
    return value


def find_view(root, name):
    matches = [el for el in root if isinstance(el.tag, str) and
               (el.tag == name or (el.tag == 'view' and el.get('name') == name))]
    if len(matches) > 1:
        raise ValueError('В одном документе несколько одинаковых views')
    return matches[0] if matches else None


def new_view(root, name):
    view_name(name)
    if find_view(root, name) is not None:
        raise ValueError('View уже существует')
    return E.SubElement(root, 'view', name=name) if '@' in name or ':' in name else E.SubElement(root, name)


def serialize(root):
    return E.tostring(root, encoding='unicode')


def inner(node):
    if node is None:
        return ''
    # tostring(text-only node) preserves CDATA but editing should display its contents.
    result = node.text or ''
    for child in node:
        result += E.tostring(child, encoding='unicode', with_tail=True)
    return result


def _unique(node, tag):
    items = node.findall(tag)
    if len(items) > 1:
        raise ValueError('Несколько <%s>: используйте исходный XML' % tag)
    return items[0] if items else None


def layout_parts(text, name):
    node = find_view(parse(text), name)
    if node is None:
        raise ValueError('View не найден в документе')
    html = _unique(node, 'html')
    markup = deepcopy(html) if html is not None else E.Element('html')
    styles = []
    for el in list(markup):
        if el.tag == 'style':
            styles.append(inner(el))
            # Preserve text following the style element in the HTML fragment.
            tail = el.tail or ''
            prev = el.getprevious()
            markup.remove(el)
            if prev is None: markup.text = (markup.text or '') + tail
            else: prev.tail = (prev.tail or '') + tail
    if len(styles) > 1:
        raise ValueError('Несколько верхних style: редактируйте исходный XML без объединения')
    return {'html': (E.tostring(markup, encoding='unicode', with_tail=False).split('>',1)[1].rsplit('</html>',1)[0] if len(markup) or markup.text is not None else ''), 'style': styles[0] if styles else '',
            'mako': inner(_unique(node, 'mako')), 'kwargs': inner(_unique(node, 'kwargs')),
            # Whole XML fragment preserves attributes and individual behavior blocks.
            'behavior': ''.join(E.tostring(el, encoding='unicode', with_tail=False) for el in node if el.tag in ('behavior','behaviors')),
            'callback': ''.join(E.tostring(el, encoding='unicode', with_tail=False) for el in node if el.tag in ('callback','callbacks'))}


def _fragment(value):
    return parse('<config>' + value + '</config>')


def patch_layout(text, name, changes):
    root = parse(text); node = find_view(root, name)
    if node is None: raise ValueError('View не найден')
    if not isinstance(changes, dict) or not changes or set(changes) - set(SECTIONS):
        raise ValueError('Изменения должны содержать только именованные секции layout')
    for key, value in changes.items(): bounded(value)
    # Unchanged sections are left byte-equivalent at the XML subtree level.
    if 'html' in changes:
        old = _unique(node, 'html'); old_styles = [deepcopy(x) for x in old if x.tag == 'style'] if old is not None else []
        fragment = _fragment(changes['html'])
        if any(x.tag == 'style' for x in fragment):
            raise ValueError('Верхний <style> редактируется в разделе CSS')
        replacement = E.Element('html', dict(old.attrib) if old is not None else {})
        replacement.text = fragment.text
        for child in fragment: replacement.append(deepcopy(child))
        for style in old_styles: replacement.append(style)
        if old is not None: replacement.tail = old.tail; node.replace(old, replacement)
        else: node.insert(0, replacement)
    if 'style' in changes:
        html = _unique(node, 'html')
        if html is None: html = E.SubElement(node, 'html')
        styles = html.findall('style')
        if len(styles) > 1: raise ValueError('Неоднозначные style: используйте XML')
        if re.search(r'</?style\b', changes['style'], re.I): raise ValueError('Тег style добавляется редактором')
        style = styles[0] if styles else E.SubElement(html, 'style', type='text/css')
        style.text = E.CDATA(changes['style'])
    for key in ('mako','kwargs'):
        if key not in changes: continue
        if key == 'kwargs' and changes[key].strip():
            try: value = json.loads(changes[key])
            except ValueError:
                try: value = ast.literal_eval(changes[key])
                except (ValueError, SyntaxError) as exc: raise ValueError('kwargs должен быть словарём, не исполняемым выражением') from exc
            if not isinstance(value, dict) or any(not isinstance(k,str) or not isinstance(v,(str,dict)) for k,v in value.items()):
                raise ValueError('Исходные kwargs принимают строковые ключи и строки/словари значений')
        el = _unique(node,key)
        if el is None: el = E.SubElement(node,key)
        for child in list(el): el.remove(child)
        el.text = E.CDATA(changes[key])
    for key in ('behavior','callback'):
        if key not in changes: continue
        fragment = _fragment(changes[key])
        if (fragment.text or '').strip() or any(x.tag not in (key,key+'s') or (x.tail or '').strip() for x in fragment):
            raise ValueError('%s — XML-фрагмент из <%s> / <%ss> с CDATA для кода' % (key,key,key))
        old = [x for x in node if x.tag in (key,key+'s')]
        index = node.index(old[0]) if old else len(node)
        for el in old: node.remove(el)
        for i,el in enumerate(fragment): node.insert(index+i,deepcopy(el))
    result = serialize(root); parse(result)
    return result


def copy_view(text, source_name, dest_text, dest_name):
    source = find_view(parse(text), source_name)
    if source is None: raise ValueError('Исходный view не найден')
    root = parse(dest_text)
    if find_view(root,dest_name) is not None: raise ValueError('Целевой view уже существует')
    el = new_view(root,dest_name)
    for key,val in source.attrib.items():
        if key != 'name': el.set(key,val)
    el.text = source.text
    for child in source: el.append(deepcopy(child))
    return serialize(root)


def remove_view(text, name):
    root = parse(text); el = find_view(root,name)
    if el is None: raise ValueError('View не найден')
    root.remove(el)
    return serialize(root)

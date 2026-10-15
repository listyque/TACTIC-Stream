"""Bounded, loss-preserving edits of ONE original sidebar view.

Unlike the old update_config, an empty order stays empty and other views,
comments, unknown nodes/attributes and shared definitions are not discarded.
Removing a reference never recursively deletes a shared definition/folder.
"""
from copy import deepcopy
import re
from lxml import etree as X
from .config_model import parse_xml, target_spec
from .config_options import append_option
import xml.etree.ElementTree as ET

NAME=re.compile(r'^[A-Za-z_][A-Za-z0-9_.:-]{0,159}$')
HANDLERS={'link':'LinkWdg','folder':'FolderWdg','separator':'SeparatorWdg','title':'TitleWdg'}

def load_xml(raw):
    parse_xml(raw)
    return X.fromstring(raw.encode('utf-8'),parser=X.XMLParser(resolve_entities=False,no_network=True,strip_cdata=False,remove_blank_text=False))

def find_view(root, view):
    return next((n for n in root if n.tag==view or n.tag=='view' and n.get('name')==view),None)

def options_node(handler,options):
    if not isinstance(options,dict) or len(options)>100 or any(k.startswith('native_') for k in options):raise ValueError('Недопустимые параметры display')
    if any(k in options for k in ('cbjs_action','cbjs_load','javascript','python','script')):raise ValueError('Callbacks редактируются отдельно в XML, не как готовое native-действие')
    e=ET.Element('display',{'class':handler})
    for k,v in options.items():append_option(e,k,v)
    return X.fromstring(ET.tostring(e))

def patch_sidebar(raw, view, operations, descriptions):
    root=load_xml(raw);node=find_view(root,view)
    if node is None:raise ValueError('Не найден выбранный view')
    if not isinstance(operations,list) or not 1<=len(operations)<=100:raise ValueError('От 1 до 100 действий')
    folders=[]
    for op in operations:
        if not isinstance(op,dict):raise ValueError('Некорректное действие')
        elems=[e for e in node if e.tag=='element'];kind=op.get('op')
        if kind=='reorder':
            order=op.get('order')
            if not isinstance(order,list) or any(type(i)!=int for i in order) or sorted(order)!=list(range(len(elems))):raise ValueError('Порядок должен содержать все индексы ровно один раз')
            ordered=iter([elems[i] for i in order]);children=[next(ordered) if c.tag=='element' else c for c in node];node[:]=children
            continue
        if kind=='add':
            name=op.get('name');category=op.get('kind','link')
            if not isinstance(name,str) or not NAME.fullmatch(name) or category not in HANDLERS:raise ValueError('Некорректное имя/вид элемента')
            if category!='separator' and any(e.get('name')==name for e in elems):raise ValueError('Элемент с таким именем уже есть')
            e=X.Element('element',name=name);node.append(e)
            e.append(options_node(HANDLERS[category],op.get('options') or {}))
            if category=='folder':
                folder=op.get('options',{}).get('view')
                if not isinstance(folder,str) or not NAME.fullmatch(folder) or folder==view:raise ValueError('Папка должна ссылаться на другой корректный view')
                if folder in folders:raise ValueError('Нельзя создать один view папки дважды')
                folders.append(folder)
        elif kind in ('edit','remove'):
            index=op.get('index')
            if type(index)!=int or not 0<=index<len(elems):raise ValueError('Элемент изменился или отсутствует')
            e=elems[index]
            if kind=='remove':node.remove(e);continue
            if 'options' in op or 'handler' in op:
                existing=e.find('display');desc=descriptions.get(e.get('name'),{})
                handler=op.get('handler') or (existing.get('class') if existing is not None else desc.get('handler')) or 'LinkWdg'
                if handler not in HANDLERS.values():raise ValueError('Нестандартный display редактируется через исходный XML')
                opts=op.get('options',desc.get('options',{}))
                previous_handler=(existing.get('class') if existing is not None else desc.get('handler')) or 'LinkWdg'
                if handler in ('FolderWdg','TitleWdg') or previous_handler in ('FolderWdg','TitleWdg'):
                    raise ValueError('Цель существующей папки меняется только через XML; её название/иконку можно редактировать здесь')
                replacement=options_node(handler,opts)
                if existing is not None:e.replace(existing,replacement)
                else:e.insert(0,replacement)
        else:raise ValueError('Неизвестное действие')
        attrs=op.get('attributes',{})
        if not isinstance(attrs,dict) or set(attrs)-{'title','description','icon','is_visible','state'}:raise ValueError('Недопустимые атрибуты ссылки')
        for key,value in attrs.items():
            if value is None:e.attrib.pop(key,None)
            elif not isinstance(value,str) or '\x00' in value or len(value)>1000:raise ValueError('Некорректный атрибут')
            else:e.set(key,value)
    return X.tostring(root,encoding='unicode'),folders

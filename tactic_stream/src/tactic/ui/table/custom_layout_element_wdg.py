"""Compile the portable CustomLayout subset to native Frame data, never an HTML view."""

from tactic.ui.common import BaseTableElementWdg
from pyasm.command import Command


def read_custom_layout(
    search_key='', view='', html='', include_mako=True, _depth=0, _behaviors=None
):
    import ast
    import json
    import textwrap
    import re
    import html as entities
    from html.parser import HTMLParser
    from xml.etree import ElementTree as ET
    from mako.template import Template
    from mako.lexer import Lexer
    from mako.exceptions import MakoException
    from pyasm.search import Search
    from pyasm.common import Environment

    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if _depth >= 8:
        raise ValueError('CustomLayout nesting exceeds eight levels')
    if not search_key:
        from pyasm.biz import Project

        project = Project.get_by_code(Project.get_project_code())
        if project is None:
            raise ValueError('Project is no longer available')
        search_key = project.get_search_key()
    obj = Search.get_by_search_key(search_key)
    if obj is None:
        raise ValueError('Object is no longer available')
    view = str(view).replace('/', '.')
    behaviors = dict(_behaviors or {})
    references = {}
    load_actions = []
    mako = ''
    if not html:
        search = Search('config/widget_config')
        search.add_filter('view', view)
        configs = [
            row
            for row in search.get_sobjects()
            if row.get_value('category', no_exception=True) == 'CustomLayoutWdg'
            or (
                not row.get_value('category', no_exception=True)
                and row.get_value('search_type') == 'CustomLayoutWdg'
            )
        ]
        configs.sort(
            key=lambda row: float(row.get_value('priority', no_exception=True) or 0),
            reverse=True,
        )
        if not configs:
            raise ValueError('CustomLayout is not configured: ' + view)
        root = ET.fromstring(configs[0].get_value('config'))
        definition = next(
            (node for node in root if node.tag == view or node.get('name') == view),
            None,
        )
        if definition is not None and definition.find('dashboard') is not None:
            from tactic_stream.server.dashboards import dashboard_layout
            return dashboard_layout(json.loads(definition.findtext('dashboard')), view, search_key)
        if definition is None or definition.find('html') is None:
            raise ValueError('CustomLayout has no HTML definition: ' + view)
        mako = definition.findtext('mako') or ''
        body = definition.find('html')
        references = {
            child.get('name'): ET.tostring(child, encoding='unicode')
            for child in definition.findall('element')
        }
        html = (body.text or '') + ''.join(
            ET.tostring(child, encoding='unicode') for child in body
        )
        for behavior in definition.findall('behavior'):
            source = behavior.text or ''
            if behavior.get('event'):
                if behavior.get('event') not in ('click_up', 'load'):
                    raise ValueError(
                        'CustomLayout behavior requires a portable click action'
                    )
                code = source
            else:
                try:
                    data = json.loads(source)
                except ValueError:
                    data = ast.literal_eval(source)
                if data.get('type') not in ('click_up', 'load'):
                    raise ValueError(
                        'CustomLayout behavior requires a portable click action'
                    )
                code = data['cbjs_action']
            selector = behavior.get('class') or behavior.get('relay_class')
            if not selector:
                raise ValueError('CustomLayout click action needs a class selector')
            if (behavior.get('event') or data.get('type')) == 'load':
                load_actions.append(dict(selector=selector, javascript=code))
            else:
                behaviors[selector] = code
    html = entities.unescape(html)
    if include_mako not in (False, 'false') and (mako or '${' in html or '<%' in html):
        template_source = ('<%\n' + mako + '\n%>' if mako else '') + html
        # Table reads can retry: layout expressions must never perform a write or I/O.
        allowed = (
            ast.Module,
            ast.Expression,
            ast.Assign,
            ast.Name,
            ast.Load,
            ast.Store,
            ast.Constant,
            ast.Call,
            ast.Attribute,
            ast.keyword,
            ast.If,
            ast.IfExp,
            ast.Compare,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.Is,
            ast.IsNot,
            ast.In,
            ast.NotIn,
            ast.BoolOp,
            ast.And,
            ast.Or,
            ast.UnaryOp,
            ast.Not,
            ast.USub,
            ast.UAdd,
            ast.BinOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.FloorDiv,
            ast.Mod,
            ast.Subscript,
            ast.Slice,
            ast.List,
            ast.Tuple,
            ast.Dict,
            ast.JoinedStr,
            ast.FormattedValue,
        )
        pure_builtins = {'str', 'int', 'float', 'bool', 'len'}
        data_names = {'sobject', 'sobjects', 'kwargs', 'data', 'plugin', 'server'}
        reserved = (
            data_names
            | pure_builtins
            | {
                'context',
                'self',
                'local',
                'parent',
                'next',
                'pageargs',
                'loop',
                'caller',
                'capture',
                'UNDEFINED',
                'STOP_RENDERING',
            }
        )
        pure_methods = {
            'get',
            'format',
            'replace',
            'find',
            'strip',
            'upper',
            'lower',
            'join',
        }
        trees = []
        try:
            for part in Lexer(template_source).parse().nodes:
                kind = type(part).__name__
                if kind in ('Text', 'Comment'):
                    continue
                if kind not in ('Code', 'Expression') or (
                    kind == 'Code' and part.ismodule
                ):
                    raise ValueError(
                        'CustomLayout supports data-only Mako; use a configured action for code execution'
                    )
                if kind == 'Expression' and any(
                    name.strip() not in ('n', 'h', 'str', 'trim', 'u', 'entity')
                    for name in part.escapes.split(',')
                    if name.strip()
                ):
                    raise ValueError('CustomLayout Mako filter is not supported')
                trees.append(
                    ast.parse(
                        textwrap.dedent(part.text).strip(),
                        mode='eval' if kind == 'Expression' else 'exec',
                    )
                )
        except (SyntaxError, MakoException):
            raise ValueError(
                'CustomLayout supports data-only Mako; use a configured action for code execution'
            ) from None
        local_names = {
            target.id
            for tree in trees
            for item in ast.walk(tree)
            if isinstance(item, ast.Assign)
            for target in item.targets
            if isinstance(target, ast.Name)
        }
        # CG binds `parent` to its JSON search key, before any output; never expose Mako's parent namespace.
        for tree in trees[:1]:
            if not isinstance(tree, ast.Module):
                continue
            for statement in tree.body:
                if (
                    isinstance(statement, ast.Assign)
                    and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == 'parent'
                    and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Attribute)
                    and isinstance(statement.value.func.value, ast.Name)
                    and statement.value.func.value.id == 'sobject'
                    and statement.value.func.attr == 'get'
                    and len(statement.value.args) == 1
                    and isinstance(statement.value.args[0], ast.Constant)
                    and statement.value.args[0].value == '__search_key__'
                    and not statement.value.keywords
                ):
                    reserved.discard('parent')
                    break
                if any(
                    isinstance(item, ast.Name) and item.id == 'parent'
                    for item in ast.walk(statement)
                ):
                    break
        if local_names & reserved:
            raise ValueError(
                'CustomLayout supports data-only Mako; use a configured action for code execution'
            )
        for tree in trees:
            for item in ast.walk(tree):
                valid = isinstance(item, allowed)
                if isinstance(item, ast.Assign):
                    valid = all(isinstance(target, ast.Name) for target in item.targets)
                if isinstance(item, ast.Name):
                    valid = (
                        valid
                        and not item.id.startswith('_')
                        and item.id in (local_names | data_names | pure_builtins)
                    )
                read_call = isinstance(item, (ast.Attribute, ast.Call)) and isinstance(
                    item.func if isinstance(item, ast.Call) else item, ast.Attribute
                )
                attribute = item.func if isinstance(item, ast.Call) else item
                snapshot_read = (
                    read_call
                    and isinstance(attribute.value, ast.Name)
                    and attribute.value.id == 'server'
                    and attribute.attr in ('get_snapshot', 'get_path_from_snapshot')
                )
                if isinstance(item, ast.Attribute):
                    valid = valid and (item.attr in pure_methods or snapshot_read)
                if isinstance(item, ast.Call):
                    valid = valid and (
                        (
                            isinstance(item.func, ast.Name)
                            and item.func.id in pure_builtins
                        )
                        or (
                            isinstance(item.func, ast.Attribute)
                            and item.func.attr in pure_methods
                        )
                        or snapshot_read
                    )
                if not valid:
                    raise ValueError(
                        'CustomLayout supports data-only Mako; use a configured action for code execution'
                    )
        record = json.loads(json.dumps(obj.get_sobject_dict(), default=str))

        class SnapshotReads:
            # Only this layout's object and the snapshots discovered for it are readable.
            def __init__(self):
                self.snapshots = {}

            def get_snapshot(self, value, context='publish'):
                from pyasm.biz import Snapshot

                if value != record:
                    raise ValueError('CustomLayout snapshot target must be its object')
                snapshot = Snapshot.get_snapshot(
                    obj.get_search_type(),
                    obj.get_code() or obj.get_id(),
                    context=context,
                )
                if not snapshot:
                    return {}
                self.snapshots[snapshot.get_code()] = snapshot
                return snapshot.get_sobject_dict()

            def get_path_from_snapshot(self, code, mode='web'):
                if mode != 'web':
                    raise ValueError('CustomLayout previews require web paths')
                if not code:
                    return ''
                if code not in self.snapshots:
                    raise ValueError(
                        'CustomLayout snapshot is outside the current object'
                    )
                return self.snapshots[code].get_web_path_by_type() or ''

        html = Template(template_source).render(
            sobject=record,
            sobjects=[record],
            kwargs=dict(search_key=search_key, view=view),
            data={},
            plugin={},
            server=SnapshotReads(),
        )

    def expression(match):
        source = match.group(1).strip()
        if not re.fullmatch(r'\{\$(PROJECT|TODAY)\}|@GET\(\.[A-Za-z_]\w*\)', source):
            raise ValueError('CustomLayout supports read-only field expressions')
        return entities.escape(
            str(Search.eval(source, sobjects=obj, single=True) or ''), quote=True
        )

    html = re.sub(r'\[expr\](.*?)\[/expr\]', expression, html, flags=re.S)
    html = html.replace(
        '{@GET(state.search_key)}', entities.escape(search_key, quote=True)
    )

    class Markup(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.root = dict(tag='root', attrs={}, children=[])
            self.stack = [self.root]

        def handle_starttag(self, tag, attrs):
            if len(self.stack) > 32:
                raise ValueError('CustomLayout markup exceeds 32 levels')
            item = dict(tag=tag, attrs=dict(attrs), children=[])
            self.stack[-1]['children'].append(item)
            if tag not in ('br', 'embed', 'img', 'hr', 'input'):
                self.stack.append(item)

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

        def handle_endtag(self, tag):
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index]['tag'] == tag:
                    self.stack = self.stack[:index]
                    break

        def handle_data(self, data):
            self.stack[-1]['children'].append(data)

    if len(html.encode('utf-8')) > 1024 * 1024:
        raise ValueError('CustomLayout output exceeds one MiB')
    parser = Markup()
    parser.feed(html)
    nodes = []
    count = 0
    controls = []
    form = ''

    def text(item):
        return (
            item
            if isinstance(item, str)
            else ''.join(text(child) for child in item['children'])
        )

    def markup(item):
        if isinstance(item, str):
            return entities.escape(item, quote=False)
        tag = item['tag']
        attrs = ''.join(
            ' %s="%s"' % (key, entities.escape(value or '', quote=True))
            for key, value in item['attrs'].items()
        )
        content = ''.join(markup(child) for child in item['children'])
        return '<' + tag + attrs + '>' + content + '</' + tag + '>'

    def visit(item):
        nonlocal nodes, count, form
        count += 1
        if count > 512:
            raise ValueError('CustomLayout supports at most 512 markup nodes')
        if isinstance(item, str):
            if item.strip():
                nodes.append(dict(kind='text', text=item.strip()))
            return
        tag, attrs = item['tag'], item['attrs']
        selector = next(
            (name for name in attrs.get('class', '').split() if name in behaviors), ''
        )
        if selector and tag != 'element':
            nodes.append(
                dict(
                    kind='action',
                    text=attrs.get('value') or text(item).strip(),
                    selector=selector,
                    javascript=behaviors[selector],
                )
            )
            return
        if tag == 'element':
            display = next(
                (
                    child
                    for child in item['children']
                    if isinstance(child, dict) and child['tag'] == 'display'
                ),
                None,
            )
            if display is None and attrs.get('name') in references:
                referenced = Markup()
                referenced.feed(
                    references[attrs['name']].replace(
                        '{@GET(state.search_key)}',
                        entities.escape(search_key, quote=True),
                    )
                )
                visit(referenced.root['children'][0])
                return
            if display is None:
                raise ValueError('CustomLayout element has no display')
            handler = display['attrs'].get('class') or display['attrs'].get('widget')
            options = {
                child['tag']: (
                    ''.join(markup(part) for part in child['children'])
                    if child['tag'] == 'html'
                    else text(child).strip()
                )
                for child in display['children']
                if isinstance(child, dict)
            }
            if handler in (
                'tactic.ui.panel.CustomLayoutWdg',
                'tactic.ui.table.CustomLayoutElementWdg',
                'custom_layout',
            ):
                if set(options) - {
                    'view',
                    'html',
                    'include_mako',
                    'show_resize_scroll',
                    'icon_size',
                    'search_key',
                }:
                    raise ValueError('Unsupported CustomLayout options')
                nodes.extend(
                    read_custom_layout(
                        options.get('search_key') or search_key,
                        view=options.get('view') or '',
                        html=options.get('html') or '',
                        include_mako=options.get('include_mako', True),
                        _depth=_depth + 1,
                        _behaviors=behaviors,
                    )['layoutNodes']
                )
            elif handler in (
                'tactic.ui.panel.TableLayoutWdg',
                'tactic.ui.panel.FastTableLayoutWdg',
                'tactic.ui.panel.ViewPanelWdg',
            ):
                allowed = {
                    'search_type',
                    'search_key',
                    'view',
                    'expression',
                    'show_search_limit',
                    'show_insert',
                    'show_row_select',
                    'show_select',
                    'show_gear',
                    'show_search',
                    'show_shelf',
                    'init_load_num',
                    'width',
                    'mode',
                    'search_view',
                    'simple_search_view',
                }
                if set(options) - allowed or not options.get('search_type'):
                    raise ValueError('Unsupported CustomLayout table options')
                if options.get('width') not in (None, '', '100%') or options.get(
                    'mode'
                ) not in (None, '', 'simple'):
                    raise ValueError(
                        'CustomLayout table must fill its native container'
                    )
                flags = (
                    'show_row_select',
                    'show_select',
                    'show_gear',
                    'show_insert',
                    'show_shelf',
                    'show_search',
                    'show_search_limit',
                )
                if any(
                    options.get(flag, '') not in ('', True, False, 'true', 'false')
                    for flag in flags
                ):
                    raise ValueError('Invalid CustomLayout table display flag')
                initial = str(options.get('init_load_num') or '50')
                if not initial.isdecimal() or not 1 <= int(initial) <= 100:
                    raise ValueError(
                        'CustomLayout initial page must contain one to one hundred rows'
                    )
                nodes.append(
                    dict(
                        kind='table',
                        text=attrs.get('title') or attrs.get('name') or 'Table View',
                        table=dict(
                            searchType=options['search_type'],
                            parentKey=options.get('search_key') or search_key,
                            view=options.get('view') or 'table',
                            expression=options.get('expression') or '',
                            projectScope=handler == 'tactic.ui.panel.ViewPanelWdg'
                            and not options.get('search_key'),
                            searchView=options.get('search_view') or '',
                            simpleSearchView=options.get('simple_search_view') or '',
                            embedded=True,
                            initialLimit=int(initial),
                            shelf=options.get('show_shelf') not in (False, 'false'),
                            search=options.get('show_search') not in (False, 'false'),
                            searchLimit=options.get('show_search_limit')
                            not in (False, 'false'),
                            selection=options.get(
                                'show_row_select', options.get('show_select')
                            )
                            not in (False, 'false'),
                            gear=options.get('show_gear') not in (False, 'false'),
                            insert=options.get('show_insert') not in (False, 'false'),
                        ),
                    )
                )
            elif handler in ('pyasm.widget.ThumbWdg', 'ThumbWdg'):
                from pyasm.widget import ThumbWdg

                widget = ThumbWdg(name=attrs.get('name') or 'preview', **options)
                widget.set_sobjects([obj])
                widget.preprocess()
                widget.set_current_index(0)
                value = (
                    widget.get_cell_value()
                    if hasattr(widget, 'get_cell_value')
                    else dict(image=widget.get_data(obj) or '')
                )
                nodes.append(
                    dict(
                        kind='preview',
                        text=str(obj.get_display_value()),
                        value=value,
                        javascript=behaviors.get(attrs.get('name'), ''),
                    )
                )
            else:
                raise ValueError(
                    'CustomLayout embedded widget is not migrated: ' + str(handler)
                )
        elif tag == 'a':
            source = next(
                (
                    behaviors[name]
                    for name in attrs.get('class', '').split()
                    if name in behaviors
                ),
                '',
            )
            nodes.append(
                dict(
                    kind='action' if source else 'link',
                    text=text(item).strip(),
                    href=attrs.get('href') or '',
                    javascript=source,
                )
            )
        elif tag in ('object', 'embed'):
            address = attrs.get('data') or attrs.get('src')
            if address:
                nodes.append(
                    dict(
                        kind='link',
                        text='Open external document',
                        href=address,
                        translate=True,
                    )
                )
        elif tag == 'img':
            nodes.append(
                dict(
                    kind='preview',
                    text=str(obj.get_display_value()),
                    value=dict(image=attrs.get('src') or ''),
                    size=300,
                )
            )
        elif tag == 'select':
            control = dict(
                selector=(attrs.get('class') or attrs.get('name') or '').split()[0],
                name=attrs.get('name') or '',
                kind='choice',
                options=[],
                value='',
            )
            if not control['selector']:
                raise ValueError('CustomLayout select requires a name')
            controls.append(control)
            nodes.append(control)
        elif tag == 'style':
            return
        elif tag in ('table', 'tr', 'td', 'th'):
            previous, nodes = nodes, []
            for child in item['children']:
                visit(child)
            children, nodes = nodes, previous
            nodes.append(
                dict(
                    kind='row' if tag == 'tr' else 'group',
                    children=children,
                    weight=int(attrs.get('colspan') or 1),
                    width=attrs.get('width') or '',
                )
            )
        elif tag in (
            'root',
            'html',
            'body',
            'div',
            'span',
            'p',
            'strong',
            'b',
            'small',
            'br',
            'hr',
            'h4',
            'form',
        ):
            if tag == 'form':
                form = attrs.get('name') or ''
            if attrs.get('class') and not text(item).strip():
                control = dict(kind='text', text='', selector=attrs['class'].split()[0])
                controls.append(control)
                nodes.append(control)
            for child in item['children']:
                visit(child)
        else:
            raise ValueError('CustomLayout markup is not migrated: ' + tag)

    visit(parser.root)
    return dict(
        text='',
        layoutNodes=nodes,
        targetSearchKey=search_key,
        layoutView=view,
        layoutControls=controls,
        layoutLoad=load_actions,
        layoutForm=form,
        layoutUser=Environment.get_security().get_user_name(),
        layoutRecord=dict(
            __search_key__=search_key,
            code=obj.get_code(),
            name=obj.get_value('name', no_exception=True),
            title=obj.get_value('title', no_exception=True),
        ),
        externalDocuments=any(node['kind'] == 'link' for node in nodes),
    )


class CustomLayoutElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(
        (
            'view',
            'html',
            'include_mako',
            'show_resize_scroll',
            'icon_size',
            'search_key',
        ),
        {},
    )

    def is_editable(self):
        return False

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if not obj or obj.is_insert():
            return dict(text='', layoutNodes=[])
        values = {
            name: self.get_option(name)
            for name in ('view', 'html', 'include_mako')
            if self.get_option(name) not in ('', None)
        }
        return dict(
            read_custom_layout(
                self.get_option('search_key') or obj.get_search_key(), **values
            ),
            columnName=self.get_name(),
        )


class CustomLayoutReadCmd(Command):
    def execute(self):
        self.info = read_custom_layout(**self.kwargs)
        return self.info

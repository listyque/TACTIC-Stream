"""Read the complete scoped report before invoking a client's native printer."""

from pyasm.command import Command


class CustomLayoutReportCmd(Command):
    def execute(self):
        import base64
        import mimetypes
        from pathlib import Path
        from pyasm.biz import Snapshot
        from pyasm.search import Search
        from tactic_stream.server.interface import read_interface
        from tactic_stream.server.table_cells import read_table_cells
        from .custom_layout_element_wdg import read_custom_layout
        from .nested_scope import read_nested_scope

        layout = read_custom_layout(**self.kwargs)
        obj = Search.get_by_search_key(layout['targetSearchKey'])
        blocks = []

        def visit(nodes):
            for node in nodes:
                if node.get('children'):
                    visit(node['children'])
                elif node['kind'] == 'text' and node.get('text'):
                    blocks.append(dict(kind='text', text=node['text']))
                elif node['kind'] == 'preview':
                    snapshot = Snapshot.get_snapshot(
                        obj.get_search_type(),
                        obj.get_code() or obj.get_id(),
                        context='icon',
                    )
                    if snapshot:
                        path = Path(snapshot.get_lib_path_by_type())
                        if path.is_file():
                            if path.stat().st_size > 8 * 1024 * 1024:
                                raise ValueError('Report preview exceeds eight MiB')
                            mime = mimetypes.guess_type(path.name)[0]
                            if mime not in (
                                'image/png',
                                'image/jpeg',
                                'image/gif',
                                'image/webp',
                                'image/bmp',
                                'image/tiff',
                            ):
                                raise ValueError(
                                    'The report preview must be a raster image'
                                )
                            blocks.append(
                                dict(
                                    kind='image',
                                    mime=mime,
                                    data=base64.b64encode(path.read_bytes()).decode(
                                        'ascii'
                                    ),
                                )
                            )
                elif node['kind'] == 'table':
                    scope, rows, offset = node['table'], [], 0
                    definition = read_interface(scope['searchType'], scope['view'])
                    columns = [
                        column
                        for column in definition['table']['elements']
                        if not column.get('hidden')
                    ]
                    while True:
                        page = read_nested_scope(
                            scope['parentKey'],
                            scope['searchType'],
                            view=scope['view'],
                            search_view=scope.get('searchView') or '',
                            expression=scope.get('expression') or '',
                            project_scope=scope.get('projectScope', False),
                            offset=offset,
                            limit=100,
                        )
                        cells = read_table_cells(
                            scope['searchType'],
                            scope['view'],
                            [row['__search_key__'] for row in page['records']],
                        )
                        for row in page['records']:
                            values = []
                            for column in columns:
                                cell = (
                                    cells[row['__search_key__']].get(column['name'])
                                    or {}
                                )
                                if cell.get('error'):
                                    raise ValueError(
                                        'Report cell failed: ' + str(cell['error'])
                                    )
                                value = cell.get('text', row.get(column['name'], ''))
                                values.append(str(value if value is not None else ''))
                            rows.append(values)
                        if not page['hasNext']:
                            break
                        offset += 100
                        if offset >= 10000:
                            raise ValueError('Report exceeds ten thousand rows')
                    blocks.append(
                        dict(
                            kind='table',
                            title=node['text'],
                            columns=[column['title'] for column in columns],
                            rows=rows,
                        )
                    )

        visit(layout['layoutNodes'])
        self.info = dict(
            blocks=blocks,
            search_key=layout['targetSearchKey'],
            view=layout['layoutView'],
        )
        return self.info

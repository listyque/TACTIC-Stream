"""CG sample graph, written and checked through native TACTIC operations."""
from pyasm.search import Search
from pyasm.biz import Pipeline, Note


def run(server, project, disable_telegram=False):
    server.set_project(project)
    disabled = []
    if disable_telegram:
        # The supplied production template contains real Telegram endpoints.
        # Retire only their callbacks in the explicitly authorized test project.
        scripts = Search('config/custom_script').get_sobjects()
        paths = {row.get_value('folder') + '/' + row.get_value('title') for row in scripts
                 if 'import telegram' in row.get_value('script')}
        for trigger in Search('config/trigger').get_sobjects():
            if trigger.get_value('script_path', no_exception=True) in paths:
                trigger.retire()
                disabled.append(trigger.get_code())
    objects = {}

    def put(stype, code, **data):
        existing = server.query(stype, [('code', code)], single=True)
        row = existing or server.insert(stype, dict(code=code, **data))
        obj = Search.get_by_search_key(row['__search_key__'])
        objects[code] = obj
        return obj

    for code, name in [('CHAR', 'Characters'), ('PROP', 'Props'), ('ENV', 'Environments'), ('MAT', 'Materials')]:
        put('cg/assets_category', 'DEMO_CAT_' + code, name=name, description='CG sample category', keywords='demo cg')
    for code, name, category in [('ROBOT', 'Hero Robot', 'CHAR'), ('BODY', 'Robot Body', 'PROP'),
                                 ('ARM', 'Robot Arm', 'PROP'), ('WORKSHOP', 'Workshop', 'ENV'), ('TOOL', 'Shared Tool', 'PROP')]:
        put('cg/assets', 'DEMO_' + code, name=name, assets_category_code='DEMO_CAT_' + category,
            description='Sample asset: ' + name, keywords='demo cg ' + code.lower(), login='admin')
    for code, name in [('EP01', 'Episode 01 — Arrival'), ('EP02', 'Episode 02 — Repair')]:
        put('cg/scenes', 'DEMO_' + code, name=name, description='Sample episode', duration='120', keywords='demo episode', login='admin')
    for code, episode, start, end in [('SH010', 'EP01', 1001, 1050), ('SH020', 'EP01', 1051, 1100), ('SH030', 'EP02', 1001, 1120)]:
        put('cg/shot', 'DEMO_' + code, name=code, scenes_code='DEMO_' + episode,
            start_frame=start, end_frame=end, rendered=False, description='Sample shot', keywords='demo shot', login='admin')
    for code, name, texture_type in [('METAL', 'Brushed Metal', 'diffuse'), ('PAINT', 'Robot Paint', 'diffuse'), ('WOOD', 'Workshop Wood', 'normal')]:
        put('cg/texture', 'DEMO_TEX_' + code, name=name, assets_category_code='DEMO_CAT_MAT', texture_type=texture_type,
            description='Sample texture', keywords='demo texture', login='admin')
    for parent, child in [('ROBOT', 'BODY'), ('BODY', 'ARM'), ('ROBOT', 'TOOL'), ('WORKSHOP', 'TOOL')]:
        put('cg/assets_in_assets', 'DEMO_AA_' + parent + '_' + child,
            parent_assets_code='DEMO_' + parent, child_assets_code='DEMO_' + child, relative_dir=parent.lower() + '/' + child.lower())
    for episode, asset in [('EP01', 'ROBOT'), ('EP01', 'WORKSHOP'), ('EP01', 'TOOL'), ('EP02', 'ROBOT'), ('EP02', 'TOOL')]:
        put('cg/assets_in_scenes', 'DEMO_AS_' + episode + '_' + asset, name=asset + ' in ' + episode,
            scenes_code='DEMO_' + episode, assets_code='DEMO_' + asset, description='Sample episode instance')
    for asset, texture in [('ROBOT', 'METAL'), ('ROBOT', 'PAINT'), ('BODY', 'METAL'), ('ARM', 'METAL'), ('TOOL', 'WOOD'), ('WORKSHOP', 'WOOD')]:
        put('cg/texture_in_assets', 'DEMO_TA_' + asset + '_' + texture, name=texture + ' on ' + asset,
            assets_code='DEMO_' + asset, texture_code='DEMO_TEX_' + texture, description='Sample texture instance')

    def note(parent, text, process='publish', reply_to=None):
        search = Search('sthpw/note'); search.add_parent_filter(parent); search.add_filter('note', text)
        obj = search.get_sobject()
        if obj is None:
            if reply_to:
                obj = Note.create(parent, text, process=process, parent_id=reply_to.get_id())
            else:
                row = server.create_note(parent.get_search_key(), text, process=process)
                obj = Search.get_by_search_key(row['__search_key__'])
        assert obj.get_parent().get_search_key() == parent.get_search_key()
        return obj

    tasks = []
    for code, parent in list(objects.items()):
        note(parent, '[CG demo] ' + code + ': проверить описание и связи.')
        if parent.get_base_search_type() not in ('cg/assets', 'cg/scenes', 'cg/shot', 'cg/texture'):
            continue
        pipeline = Pipeline.get_by_code(parent.get_value('pipeline_code', no_exception=True))
        processes = pipeline.get_process_names()[:1] if pipeline else ['publish']
        for process in processes:
            description = '[CG demo] ' + code + ': ' + process
            search = Search('sthpw/task'); search.add_parent_filter(parent); search.add_filter('description', description)
            task = search.get_sobject()
            if task is None:
                row = server.create_task(parent.get_search_key(), process=process, description=description,
                    assigned='admin', bid_start_date='2026-10-08 09:00:00', bid_end_date='2026-10-10 18:00:00', bid_duration=2)
                task = Search.get_by_search_key(row['__search_key__'])
            assert task.get_parent().get_search_key() == parent.get_search_key()
            note(task, '[CG demo] Задача ' + code + ': материалы готовы.', process)
            tasks.append(task)
    parent = objects['DEMO_ROBOT']
    root = note(parent, '[CG demo] Робот: проверить сборку и материалы.')
    reply = note(parent, '[CG demo] Ответ: корпус и рука связаны.', reply_to=root)
    assert reply.get_value('parent_id') == root.get_id()

    checks = []
    def related(code, stype, expected, path=None):
        rows = objects[code].get_related_sobjects(stype, path=path)
        actual = {row.get_code() for row in rows}
        assert actual == set(expected), (code, stype, path, actual, set(expected))
        checks.append(code + ' -> ' + stype + (':' + path if path else ''))

    related('DEMO_CAT_PROP', 'cg/assets', ['DEMO_BODY', 'DEMO_ARM', 'DEMO_TOOL'])
    related('DEMO_ROBOT', 'cg/assets_category', ['DEMO_CAT_CHAR'])
    related('DEMO_CAT_MAT', 'cg/texture', ['DEMO_TEX_METAL', 'DEMO_TEX_PAINT', 'DEMO_TEX_WOOD'])
    related('DEMO_TEX_METAL', 'cg/assets_category', ['DEMO_CAT_MAT'])
    related('DEMO_EP01', 'cg/shot', ['DEMO_SH010', 'DEMO_SH020'])
    related('DEMO_SH030', 'cg/scenes', ['DEMO_EP02'])
    related('DEMO_EP01', 'cg/assets', ['DEMO_ROBOT', 'DEMO_WORKSHOP', 'DEMO_TOOL'])
    related('DEMO_ROBOT', 'cg/scenes', ['DEMO_EP01', 'DEMO_EP02'])
    related('DEMO_ROBOT', 'cg/texture', ['DEMO_TEX_METAL', 'DEMO_TEX_PAINT'])
    related('DEMO_TEX_WOOD', 'cg/assets', ['DEMO_TOOL', 'DEMO_WORKSHOP'])
    related('DEMO_ROBOT', 'cg/assets_in_assets', ['DEMO_AA_ROBOT_BODY', 'DEMO_AA_ROBOT_TOOL'], path='child')
    related('DEMO_TOOL', 'cg/assets_in_assets', ['DEMO_AA_ROBOT_TOOL', 'DEMO_AA_WORKSHOP_TOOL'], path='parent')
    related('DEMO_AA_ROBOT_BODY', 'cg/assets', ['DEMO_BODY'], path='parent')
    related('DEMO_AA_ROBOT_BODY', 'cg/assets', ['DEMO_ROBOT'], path='child')
    for code, obj in objects.items():
        kind = obj.get_base_search_type()
        if kind == 'cg/assets_in_assets':
            related(code, 'cg/assets', [obj.get_value('parent_assets_code')], path='child')
            related(code, 'cg/assets', [obj.get_value('child_assets_code')], path='parent')
        elif kind == 'cg/assets_in_scenes':
            related(code, 'cg/assets', [obj.get_value('assets_code')])
            related(code, 'cg/scenes', [obj.get_value('scenes_code')])
        elif kind == 'cg/texture_in_assets':
            related(code, 'cg/assets', [obj.get_value('assets_code')])
            related(code, 'cg/texture', [obj.get_value('texture_code')])
    # Batched relationship lookup must retain the owner of each result.
    batch = Search.get_related_by_sobjects([objects['DEMO_EP01'], objects['DEMO_EP02']], 'cg/assets')
    assert {row.get_code() for row in batch[objects['DEMO_EP01'].get_search_key()]} == {'DEMO_ROBOT', 'DEMO_WORKSHOP', 'DEMO_TOOL'}
    assert {row.get_code() for row in batch[objects['DEMO_EP02'].get_search_key()]} == {'DEMO_ROBOT', 'DEMO_TOOL'}
    counts = {}
    for stype in sorted({obj.get_base_search_type() for obj in objects.values()}):
        search = Search(stype); search.add_filter('code', 'DEMO_%', op='like'); counts[stype] = search.get_count()
    notes = Search('sthpw/note'); notes.add_filter('project_code', project); notes.add_filter('note', '[CG demo]%', op='like')
    all_tasks = Search('sthpw/task'); all_tasks.add_filter('project_code', project)
    return dict(objects=counts, tasks=len(tasks), notes=notes.get_count(), relationships=len(checks) + 1,
                total_tasks=all_tasks.get_count(), disabled_telegram=disabled)

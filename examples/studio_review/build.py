"""Build the example's original SPT package using only the standard library."""
from pathlib import Path
import zipfile


def entry(source):
    return '#-- Start Entry --#\n' + source + '\n#-- End Entry --#\n'


def record(target_type, **values):
    return entry('insert = SearchType.create(' + repr(target_type) + ')\n' + '\n'.join(
        'insert.set_value(' + repr(key) + ', ' + repr(value) + ')' for key, value in values.items()))


def build(destination=None):
    root = Path(__file__).parent
    (root / 'data').mkdir(exist_ok=True)
    (root / 'config').mkdir(exist_ok=True)
    registry = record('sthpw/search_object', code='studio/review', search_type='studio/review',
                      namespace='studio', database='{project}', table_name='studio_review',
                      title='Studio Review', class_name='pyasm.search.SObject', schema='public')
    schema = entry("table = CreateTable()\ntable.set_table('studio_review')\n" + '\n'.join(
        "table.add(%r, %r%s)" % (key, kind, ', primary_key=True' if key == 'id' else '')
        for key, kind in [('id','serial'), ('code','text'), ('name','text'), ('description','text'),
                          ('status','text'), ('progress','integer'), ('approved_by','text'),
                          ('timestamp','timestamp'), ('s_status','text')]))
    (root / 'studio_review.spt').write_text(registry + schema, encoding='utf-8')
    samples = [('Lighting review','Review the key and fill balance.','In review',65),
               ('Animation review','Confirm timing and silhouettes.','Changes requested',35),
               ('Final delivery','Validate the final approved version.','Approved',100)]
    (root / 'data/reviews.spt').write_text(''.join(record('studio/review', code=f'STUDIO_REVIEW_{i:03}',
        name=name, description=description, status=status, progress=progress)
        for i,(name,description,status,progress) in enumerate(samples,1)), encoding='utf-8')
    widgets = ''
    for kind in ('widget', 'column', 'table', 'theme'):
        widgets += record('config/widget_config', code='STUDIO_REVIEW_' + kind.upper(),
            view='studio_review.' + kind, search_type='ALL' if kind=='theme' else 'studio/review',
            category='PluginTheme' if kind=='theme' else '' if kind=='table' else 'CustomLayoutWdg',
            widget_type=kind if kind!='table' else '', config=(root / (kind + '.xml')).read_text(encoding='utf-8'))
    (root / 'config/widgets.spt').write_text(widgets, encoding='utf-8')
    (root / 'config/scripts.spt').write_text(record('config/custom_script', code='STUDIO_REVIEW_APPROVE',
        folder='plugins/studio_review', title='approve', language='python',
        script=(root / 'approve.py').read_text(encoding='utf-8')), encoding='utf-8')
    (root / 'config/settings.spt').write_text('', encoding='utf-8')
    destination = Path(destination) if destination else root.parents[1] / 'releases/studio-review-1.0.0.zip'
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.name != 'build.py' and '__pycache__' not in path.parts:
                archive.write(path, 'studio_review/' + path.relative_to(root).as_posix())
    return destination


if __name__ == '__main__':
    print(build())

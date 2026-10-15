"""Handler ColumnsEditorController's saved definition catalog on native TACTIC."""
import hashlib
import json
import re
from xml.etree import ElementTree

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import Search, SearchType, WidgetDbConfig, Sql
from pyasm.security.security import _require_admin
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def _records():
    search = Search('config/widget_config')
    statement, parameters = search._statement()
    statement = Sql._bound_query(statement, parameters, search._placeholder())
    # A source editor reads text, including unsupported Mako/HTML definitions;
    # it must not instantiate their renderer merely to show the catalog.
    with search.store.connection(search.get_db_resource()) as db:
        return [dict(row) for row in db.execute(statement, parameters).fetchall()]


def _revision(records):
    log = Search('sthpw/sobject_log')
    log.add_filters('search_type', list(dict.fromkeys(['config/widget_config',
        Project.get_full_search_type('config/widget_config'), 'config/widget_config?project=' + Project.get_project_code()])))
    log.add_order_by('id desc'); log.add_limit(1)
    latest = log.get_sobject()
    return hashlib.sha256(json.dumps([Project.get_project_code(), records, latest.get_id() if latest else None],
        sort_keys=True, default=str).encode()).hexdigest()


def read_columns_catalog():
    _require_admin()
    records = _records()
    catalog = [dict(id=row['id'], identity=str(row['id']), code=str(row.get('code') or ''),
        searchType=str(row['search_type']), view=str(row['view']), login=str(row.get('login') or ''),
        category=str(row.get('category') or ''), widgetType=str(row.get('widget_type') or ''), config=str(row.get('config') or ''))
        for row in records if row.get('search_type') and row.get('view')]
    catalog.sort(key=lambda row: tuple(row[key].lower() for key in ('searchType', 'view', 'login', 'code')))
    titles = {row.get_value('search_type'): row.get_value('title') or row.get_value('search_type')
              for row in Project.get().get_search_types(include_sthpw=True, include_config=True)}
    for row in catalog:
        titles.setdefault(row['searchType'], row['searchType'])
    choices = [dict(value=code, label=f'{title} · {code}' if title != code else code)
               for code, title in sorted(titles.items(), key=lambda item: item[1].lower())]
    return dict(records=catalog, searchTypes=choices, revision=_revision(records))


def save_columns_definition(source_id, xml, revision):
    _require_admin()
    if type(source_id) is not int or not isinstance(revision, str):
        raise ValueError('Choose a saved definition')
    if not isinstance(xml, str) or not xml.strip() or len(xml.encode()) > 512 * 1024:
        raise ValueError('Invalid configuration XML')
    if re.search(r'<!DOCTYPE|<!ENTITY', xml, re.I):
        raise ValueError('Document types and XML entities are not supported')
    try:
        ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ValueError(str(error)) from None
    search = Search('config/widget_config'); sql = search.get_sql()
    # ponytail: the existing config table lock; row locks only if editing throughput requires it.
    sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
    records = _records()
    if revision != _revision(records):
        raise WidgetConfigConflict('Interface configuration changed. Reload before saving.')
    original = next((row for row in records if row['id'] == source_id), None)
    if original is None:
        raise ValueError('The selected definition no longer exists. Reload the catalog.')
    item = WidgetDbConfig()
    item.set_data(original); item.set_update_data({})
    item.set_value('config', xml); item.validate()
    item.commit(triggers=False)  # Handler insert_update(..., triggers=False).
    return str(source_id)


def columns_editor_request(action, payload):
    _require_admin()
    if action == 'read':
        return read_columns_catalog()
    command = Command()
    command.execute = lambda: save_columns_definition(payload.get('source_id'), payload.get('xml'), payload.get('revision'))
    command.get_transaction().set_sync(False)
    selected = Command.execute_cmd(command)
    return dict(**read_columns_catalog(), selected=selected)

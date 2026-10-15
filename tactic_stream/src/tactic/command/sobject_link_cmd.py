"""Handler tactic_query.edit_multiple_instance_sobjects on native Commands.

The same directed instance lookup and connection writes, with request validation.
See LICENSE.TACTIC and compatibility/source_manifest.json.
"""
from pyasm.command import Command
from pyasm.search import Search, SearchKey, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.result_items import objects, relations


class SObjectLinkCmd(Command):
    def execute(self):
        _require_admin()
        parent_key = self.kwargs.get('instance_parent_key') or self.kwargs.get('parent_key')
        if not isinstance(parent_key, str) or not parent_key:
            raise ValueError('Choose a parent object')
        parent_type = SearchKey.extract_base_search_type(parent_key)
        parent = next(iter(objects(parent_type, [parent_key]).values()))
        target = self.kwargs.get('search_type')
        path = self.kwargs.get('path') or ''
        branch = next((row for row in relations(parent) if row['search_type'] == target and row['path'] == path), None)
        if not branch or branch['relationship'] != 'instance':
            raise ValueError('Relationship is not an instance relationship in the project schema')
        attrs = parent.get_schema().get_relationship_attrs(target, parent_type, path=path or None)
        instance_type = attrs['instance_type']
        inserted = objects(target, self.kwargs.get('insert_search_keys', []))
        excluded = objects(target, self.kwargs.get('exclude_search_keys', []))
        if inserted.keys() & excluded.keys() or any(child.get_id() == parent.get_id() and target == parent_type for child in inserted.values()):
            raise ValueError('Invalid instance selection')
        if self.kwargs.get('create'):
            from tactic.core.edit_commands import EditCmd
            from pyasm.web import WebContainer
            web = WebContainer.get_web()
            if SearchKey.extract_base_search_type(web.get_form_value('search_type')) != target:
                raise ValueError('Insert form belongs to another Search Type')
            if web.get_form_value('search_id') not in ('', '-1') or web.get_form_value('sobject_commit') == 'false' or web.get_form_value('multiplier') not in ('', '1'):
                raise ValueError('Linked creation requires one new committed object')
            args = {key: self.kwargs[key] for key in ('view', 'input_prefix', 'element_names') if key in self.kwargs}
            args['search_type'] = target
            command = EditCmd(**args)
            Command.execute_cmd(command)
            inserted[command.sobject.get_search_key()] = command.sobject
            self.info['created_key'] = command.sobject.get_search_key()

        connection_path = path or ('parent' if target == parent_type else None)
        def related_instances(child):
            parent_relation = ('child:' if connection_path else '') + instance_type
            child_relation = ('parent:' if connection_path else '') + instance_type
            parents = Search.eval('@SOBJECT(%s)' % parent_relation, parent) or []
            child_keys = {row.get_search_key() for row in Search.eval('@SOBJECT(%s)' % child_relation, child) or []}
            return [row for row in parents if row.get_search_key() in child_keys]

        for child in inserted.values():
            if related_instances(child):
                continue
            instance = SearchType.create(instance_type)
            instance.add_related_connection(child, parent, src_path=connection_path)
            instance.commit()
        for child in excluded.values():
            for instance in related_instances(child):
                instance.delete()
        self.info.update(inserted=len(inserted), excluded=len(excluded))
        return self.info

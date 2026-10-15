###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#


"""Original collection commands moved out of the widget module.

Source messages, membership mutations and delete order are retained. Batch
preflight, scoped keys, validation and write locks fix partial/cross-scope writes.
Parent traversal is bounded, dialect-neutral
Search queries: the old PostgreSQL ARRAY expression broke SQLite and its fixed
10-level depth could miss a longer cycle. Names, tables and business mutations
remain those of the original commands; this is not a new collection schema.
"""
from pyasm.search import Search, SearchType
from pyasm.command import Command
from pyasm.common import TacticException

class CollectionAddCmd(Command):

    def execute(self):
        from pyasm.biz import Project
        collection_keys = self.kwargs.get('collection_keys')
        if collection_keys is None:
            collection_keys = []
        search_keys = self.kwargs.get('search_keys')
        if not isinstance(collection_keys, (list, tuple)) or not isinstance(search_keys, (list, tuple)):
            raise TacticException('Collection keys and search keys must be lists')
        if any(not isinstance(key, str) or not key for key in (*collection_keys, *search_keys)):
            raise TacticException('Collection keys and search keys must contain nonempty strings')
        sobjects = [Search.get_by_search_key(key) for key in search_keys]
        if any(obj is None for obj in sobjects):
            raise TacticException('Collection member does not exist')
        message = {}
        plans = []
        # Check the whole batch before inserting any edge. Source could return
        # a circular message after committing an earlier destination's edges.
        for collection_key in collection_keys:
            collection = Search.get_by_search_key(collection_key)
            if not collection:
                raise TacticException('Collection does not exist')
            if collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
                raise TacticException('SObject [%s] is not a collection' % collection.get_code())
            if collection.get_project_code() != Project.get_project_code():
                raise TacticException('Collection command must run in the collection project')
            if not collection.get_code():
                raise TacticException('Collection must have a code')
            for obj in sobjects:
                if obj.get_base_search_type() != collection.get_base_search_type() or obj.get_project_code() != collection.get_project_code() or obj.get_db_resource().get_key() != collection.get_db_resource().get_key():
                    raise TacticException('Collection and member must belong to the same SearchType and database')
                if not obj.get_code():
                    raise TacticException('Collection member must have a code')
            collection_type = SearchType.build_search_type(collection.get_collection_type(), collection.get_project_code())
            sql = collection.get_sql()
            sql.get_database_impl().lock_collection_table(sql, SearchType.get(collection_type).get_table())
            search = Search(collection.get_search_type())
            search.add_filter('id', collection.get_id())
            collection = search.get_sobject()
            if not collection or collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
                raise TacticException('Collection no longer exists')
            search = Search(collection.get_search_type())
            search.add_filters('id', [obj.get_id() for obj in sobjects])
            saved = {obj.get_id(): obj for obj in search.get_sobjects()}
            if any(obj.get_id() not in saved or obj.get_code() != saved[obj.get_id()].get_code() for obj in sobjects):
                raise TacticException('Collection member no longer exists or changed')
            self.kwargs['collection_code'] = collection.get_code()
            self.kwargs['collection_type'] = collection_type
            self.kwargs['search_type'] = collection.get_search_type()
            parent_codes = self.get_parent_codes()
            parent_codes.add(collection.get_code())
            source_codes = {obj.get_code() for obj in sobjects}
            circular_codes = sorted(parent_codes & source_codes)
            if circular_codes:
                message['circular'] = 'True'
                message['parent_collection_names'] = [Search.get_by_code(collection.get_search_type(), code).get('name') for code in circular_codes]
                self.info['message'] = message
                return
            plans.append((collection, collection_type))

        for collection, collection_type in plans:
            search = Search(collection_type)
            search.add_filter('parent_code', collection.get_code())
            search_codes = {obj.get_value('search_code') for obj in search.get_sobjects()}
            has_inserted = False
            for sobject in sobjects:
                if sobject.get_code() in search_codes:
                    continue
                new_item = SearchType.create(collection_type)
                new_item.set_value('parent_code', collection.get_code())
                new_item.set_value('search_code', sobject.get_code())
                new_item.commit()
                search_codes.add(sobject.get_code())
                has_inserted = True
            message[collection.get('name')] = 'Insert OK' if has_inserted else 'No insert'
        self.info['message'] = message
        self.add_description('Add [%s] item(s) to [%s] collection(s)' % (len(search_keys), len(collection_keys)))

    def get_parent_codes(self):
        frontier = {self.kwargs['collection_code']}
        seen = set()
        steps = 0
        while frontier:
            steps += 1
            if steps > 1000 or len(seen) > 10000:
                raise TacticException('Collection hierarchy exceeds safe traversal limits')
            following = set()
            values = sorted(frontier)
            for start in range(0, len(values), 200):
                search = Search(self.kwargs['collection_type'])
                search.add_filters('search_code', values[start:start+200])
                search.set_limit(10001)
                rows = search.get_sobjects()
                if len(rows) > 10000:
                    raise TacticException('Too many collection parent relationships')
                following.update(row.get_value('parent_code') for row in rows if row.get_value('parent_code'))
            fresh = following - seen
            seen.update(following)
            frontier = fresh
        return seen


class CollectionRemoveCmd(Command):

    def execute(self):

        self.collection_key = self.kwargs.get("collection_key")
        self.search_keys = self.kwargs.get("search_keys")

        from pyasm.biz import Project
        collection = Search.get_by_search_key(self.collection_key)
        if not collection:
            raise TacticException('Collection does not exist')
        if collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise TacticException('SObject [%s] is not a collection' % collection.get_code())
        if collection.get_project_code() != Project.get_project_code():
            raise TacticException('Collection command must run in the collection project')
        collection_type = SearchType.build_search_type(collection.get_collection_type(), collection.get_project_code())
        sql = collection.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(collection_type).get_table())
        search = Search(collection.get_search_type())
        search.add_filter('id', collection.get_id())
        collection = search.get_sobject()
        if not collection or collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise TacticException('Collection no longer exists')
        collection_code = collection.get_code()
        if not isinstance(self.search_keys, (list, tuple)) or any(not isinstance(key, str) or not key for key in self.search_keys):
            raise TacticException('Search keys must be a list of nonempty strings')
        sobjects = [Search.get_by_search_key(key) for key in self.search_keys]
        for obj in sobjects:
            if not obj:
                raise TacticException('Collection member does not exist')
            if obj.get_base_search_type() != collection.get_base_search_type() or obj.get_project_code() != collection.get_project_code() or obj.get_db_resource().get_key() != collection.get_db_resource().get_key():
                raise TacticException('Collection and member must belong to the same SearchType and database')
            if not obj.get_code():
                raise TacticException('Collection member must have a code')
        search_codes = [x.get_code() for x in sobjects]



        search = Search(collection_type)
        search.add_filter("parent_code", collection.get_code())
        search.add_filters("search_code", search_codes)

        items = search.get_sobjects()

        for item in items:
            item.delete()

        self.add_description("Remove [%s] item(s) from Collection [%s]" % (len(self.search_keys), collection_code))


class CollectionDeleteCmd(Command):

    def execute(self):

        self.collection_key = self.kwargs.get("collection_key")

        from pyasm.biz import Project
        collection = Search.get_by_search_key(self.collection_key)
        if not collection:
            raise TacticException('Collection does not exist')
        if collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise TacticException('SObject [%s] is not a collection' % collection.get_code())
        if collection.get_project_code() != Project.get_project_code():
            raise TacticException('Collection command must run in the collection project')
        collection_type = SearchType.build_search_type(collection.get_collection_type(), collection.get_project_code())
        sql = collection.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(collection_type).get_table())
        search = Search(collection.get_search_type())
        search.add_filter('id', collection.get_id())
        collection = search.get_sobject()
        if not collection or collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise TacticException('Collection no longer exists')
        collection_code = collection.get_code()


        search = Search(collection_type)
        search.add_filter("parent_code", collection.get_code())
        items = search.get_sobjects()

        for item in items:
            item.delete()

        # Also need to delete the relationships in its parent collections
        parent_search = Search(collection_type)
        parent_search.add_filter("search_code", collection.get_code())
        parent_items = parent_search.get_sobjects()

        for parent_item in parent_items:
            parent_item.delete()

        collection.delete()

        self.add_description("Remove Collection [%s]" % collection_code)


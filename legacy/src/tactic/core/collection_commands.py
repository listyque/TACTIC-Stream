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

execute() bodies are retained. Parent traversal is now bounded, dialect-neutral
Search queries: the old PostgreSQL ARRAY expression broke SQLite and its fixed
10-level depth could miss a longer cycle. Names, tables and business mutations
remain those of the original commands; this is not a new collection schema.
"""
from pyasm.search import Search, SearchType
from pyasm.command import Command
from pyasm.common import TacticException

class CollectionAddCmd(Command):

    def execute(self):

        # NOTE: keywords_data is handled in GlobalSearchTrigger

        collection_keys = self.kwargs.get("collection_keys")
        search_keys = self.kwargs.get("search_keys")
        message = {}

        if collection_keys == None:
            collection_keys = []

        for collection_key in collection_keys:
            collection = Search.get_by_search_key(collection_key)
            if not collection:
                raise Exception("Collection does not exist")

            collection_name = collection.get("name")
            search_type = collection.get_base_search_type()
            parts = search_type.split("/")
            collection_type = "%s/%s_in_%s" % (parts[0], parts[1], parts[1])
            search = Search(collection_type)
            search.add_filter("parent_code", collection.get_code())
            items = search.get_sobjects()


            search_codes = [x.get_value("search_code") for x in items]
            search_codes = set(search_codes)

            # Try to find all the parent codes of the destination, and see if there's any that
            # matches the codes in "search_codes"
            # Check for parent/child hierarchy in destination to prevent circular relationships
            src_collections_codes = []
            for search_key in search_keys:
                asset = Search.get_by_search_key(search_key)
                is_collection = asset.get("_is_collection")
                if is_collection:
                    src_collection_code = asset.get("code")
                    src_collections_codes.append(src_collection_code)

            if src_collections_codes:
                collection_code = collection.get("code")

                self.kwargs["collection_code"] = collection_code
                self.kwargs["collection_type"] = collection_type
                self.kwargs["search_type"] = search_type

                # Run SQL to find all parent collections(and above) of the selected collections
                # The all_parent_codes contain all parent codes up the relationship tree
                # ie. parent collections' parents ...etc

                all_parent_codes = self.get_parent_codes()

                all_parent_codes.add(collection_code)
                all_parent_codes = list(all_parent_codes)

                # Once retrieve the parent codes, use a for loop to check if the the codes in
                # src_collections_codes are in parent_codes
                parent_collection_names = []
                for parent_code in all_parent_codes:
                    if parent_code in src_collections_codes:
                        message['circular'] = "True"
                        parent_collection_name = Search.get_by_code(search_type, parent_code).get("name")
                        parent_collection_names.append(parent_collection_name)
                if parent_collection_names:
                    message['parent_collection_names'] = parent_collection_names
                    self.info['message'] = message
                    return



            # create new items
            has_inserted = False

            sobjects = Search.get_by_search_keys(search_keys)
            for sobject in sobjects:
                if sobject.get_code() in search_codes:
                    continue

                new_item = SearchType.create(collection_type)
                new_item.set_value("parent_code", collection.get_code())
                new_item.set_value("search_code", sobject.get_code())
                new_item.commit()
                has_inserted = True


            if not has_inserted:
                message[collection_name] = "No insert"
            else:
                message[collection_name] = "Insert OK"

        self.info['message'] = message
        self.add_description("Add [%s] item(s) to [%s] collection(s)" % (len(search_keys), len(collection_keys)))



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

        collection = Search.get_by_search_key(self.collection_key)
        collection_code = collection.get("code")
        sobjects = Search.get_by_search_keys(self.search_keys)
        search_codes = [x.get_code() for x in sobjects]


        search_type = collection.get_base_search_type()
        parts = search_type.split("/")
        collection_type = "%s/%s_in_%s" % (parts[0], parts[1], parts[1])

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

        collection = Search.get_by_search_key(self.collection_key)
        collection_code = collection.get("code")

        search_type = collection.get_base_search_type()
        parts = search_type.split("/")
        collection_type = "%s/%s_in_%s" % (parts[0], parts[1], parts[1])

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


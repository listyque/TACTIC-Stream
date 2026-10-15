# Extracted from Southpaw TACTIC; see LICENSE.TACTIC and source_manifest.json.

# Only the Project import points at the new headless owner.

def build_search_type(search_type, project_code=None):
    # do not append project for sthpw/* search_type
    if search_type.startswith('sthpw/'):
        return search_type

    if search_type.find("?") != -1:
        if project_code:
            # Note: should maybe chnage project
            return search_type
        else:
            return search_type

    if not project_code:
        from pyasm.biz.project import Project
        project_code = Project.get_project_code()

    return "%s?project=%s" % (search_type, project_code)

def breakup_search_type(search_type):

    if search_type.find("?") == -1:
        parts = search_type.split("/")
        if len(parts) == 1:
            parts = ['','']

        return {
            'search_type': search_type,
            'namespace': parts[0],
            'table': parts[1],
            'project': "",
            'code': ""
        }

    parts = search_type.split("?")

    search_type = parts[0]
    search_type_parts = search_type.split("/")
    if len(search_type_parts) == 1:
        namespace = ''
        table = ''
    else:
        namespace = search_type_parts[0]
        table = search_type_parts[1]

    name_value_pairs = parts[1]
    name_value_parts = name_value_pairs.split("&")


    data = {
        'search_type': search_type,
        'namespace': namespace,
        'table': table,
    }
    for name_value_part in name_value_parts:
        name, value = name_value_part.split("=")
        data[name] = value

    return data

class SearchKey:

    @classmethod
    def build_search_key(cls, search_type, code, column='code', project_code=None):

        if search_type.find("?") != -1:
            search_key = "%s&%s=%s" % (search_type, column, code)
            return search_key

        if not project_code:
            from pyasm.biz.project import Project
            project_code = Project.get_project_code()

        if search_type.startswith("sthpw/"):
            search_key = "%s?%s=%s" % (search_type, column, code)
        else:
            search_key = "%s?project=%s&%s=%s" % (search_type, project_code, column, code)
        return search_key

    @classmethod
    def extract_search_type(cls, search_key):
        base, data = cls._get_data(search_key)
        return data.get('search_type', base)

    @classmethod
    def _get_data(cls, search_key):
        data = {}
        if search_key.find("?") == -1:
            if search_key.startswith("sthpw/"):
                data['project'] = 'sthpw'

            return search_key, data

        from pyasm.search.search import _context
        context = _context.get(None)
        cache = (context.container.info.setdefault('SearchKey:parsed', {})
                 if context is not None and type(search_key) is str else None)
        if cache is not None and search_key in cache:
            base, cached = cache[search_key]
            return base, cached.copy()

        base_search_type, specifics = search_key.split("?", 1)
        exprs = specifics.split("&")

        for index, expr in enumerate(exprs):
            name, value = expr.split("=", 1)
            # The original builder appends identity last; message codes can
            # themselves contain a complete parent key, including ? & = |.
            rest = exprs[index + 1:]
            if name in ('code', 'id') and (
                    any(char in value for char in '?|=') or
                    any(part.split('=', 1)[0] not in ('project', 'db') for part in rest)):
                data[name] = '&'.join(exprs[index:]).split('=', 1)[1]
                break
            data[name] = value

        project = data.get("project")
        if project:
            search_type = "%s?project=%s" % (base_search_type, project)
        else:
            search_type = base_search_type

        data["search_type"] = search_type
        data["base_search_type"] = base_search_type
        if cache is not None:
            if len(cache) >= 256:
                cache.pop(next(iter(cache)))
            cache[search_key] = base_search_type, data.copy()
        return base_search_type, data

    @classmethod
    def extract_base_search_type(cls, search_key):
        base_search_type, data = cls._get_data(search_key)
        return base_search_type

    @classmethod
    def extract_database(cls, search_key):
        base_search_type, data = cls._get_data(search_key)
        return data.get("db")

    @classmethod
    def extract_project(cls, search_key):
        base_search_type, data = cls._get_data(search_key)
        return data.get("project")

    @classmethod
    def extract_code(cls, search_key):
        base_search_type, data = cls._get_data(search_key)
        return data.get("code")

    @classmethod
    def extract_id(cls, search_key):
        base_search_type, data = cls._get_data(search_key)
        return data.get("id")

    @classmethod
    def build_by_sobject(cls, sobject, use_id=False):
        return cls.get_by_sobject(sobject, use_id=use_id)

    @classmethod
    def get_by_sobject(cls, sobject, use_id=False):
        from pyasm.biz.project import Project
        from pyasm.search.search import SearchType
        search_type = sobject.get_base_search_type()
        if isinstance(sobject, SearchType):
            search_type = "sthpw/search_object"

        if isinstance(sobject, Project):
            project_code = sobject.get_code()
        elif isinstance(sobject, SearchType):
            project_code = None
        else:
            project_code = sobject.get_project_code()
        # this is done like this till sthpw/task's code is working
        code = sobject.get_value('code', no_exception=True)
        if not use_id and code:
            return cls.build_search_key(search_type, code, project_code=project_code)
        else:
            id = sobject.get_id()
            return cls.build_search_key(search_type, id, column='id', project_code=project_code)

    @classmethod
    def get_by_sobjects(cls, sobjects, use_id=False):
        from pyasm.biz.project import Project
        from pyasm.search.search import SearchType
        if not sobjects:
            return []

        sobject = sobjects[0]

        # if sobject is none, then this function will not work.
        # Not sure if this is the right response
        if not sobject:
            return [None for x in sobjects]

        search_type = sobject.get_base_search_type()
        if isinstance(sobject, SearchType):
            search_type = "sthpw/search_object"

        if isinstance(sobject, Project):
            project_code = sobject.get_code()
        elif isinstance(sobject, SearchType):
            project_code = None
        else:
            project_code = sobject.get_project_code()

        search_keys = []
        for sobject in sobjects:

            if not sobject:
                search_keys.append(None)
                continue

            code = sobject.get_value('code', no_exception=True)
            if not use_id and code:
                search_key = cls.build_search_key(search_type, code, project_code=project_code)
            else:
                id = sobject.get_id()
                search_key = cls.build_search_key(search_type, id, column='id', project_code=project_code)

            search_keys.append(search_key)

        return search_keys

    @staticmethod
    def get_by_search_key(search_key):
        from pyasm.search.search import Search
        return Search.get_by_search_key(search_key)

    @classmethod
    def get_by_search_keys(cls, search_keys, keep_order=False):
        """Original grouped batch lookup; one query per search type/project."""
        from pyasm.common import SetupException
        from pyasm.search.search import Search
        if not search_keys:
            return []
        if isinstance(search_keys, str):
            search_keys = search_keys.split(',')
        groups = {}
        for key in search_keys:
            while '&amp;' in key:
                key = key.replace('&amp;', '&')
            groups.setdefault(cls.extract_search_type(key), []).append(key)
        if len(groups) > 1:
            # Original keep_order preserves order within each search-type group.
            return [obj for keys in groups.values() for obj in cls.get_by_search_keys(keys, keep_order)]
        search_type, keys = next(iter(groups.items()))
        codes = [cls.extract_code(key) for key in keys]
        code_keys = all(codes)
        if code_keys:
            identities = codes
            objects = Search.get_by_code(search_type, identities)
        elif not any(codes):
            identities = [str(cls.extract_id(key)) for key in keys]
            objects = Search.get_by_id(search_type, identities)
        else:
            raise SetupException('A mixed code and id search keys detected.')
        if keep_order:
            positions = {}
            for index, value in enumerate(identities):
                positions.setdefault(value, index)
            objects = sorted(objects, key=lambda obj: positions[obj.get_code() if code_keys else str(obj.get_id())])
        return objects

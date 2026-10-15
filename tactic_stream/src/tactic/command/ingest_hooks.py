"""Handler ingest_rule_preflight, running inside the native transaction."""
def ingest_rule_preflight(
        search_type, parent_key, filename, column='name',
        ignore_ext=True, extra_data=None,
        validation_script='',
        process_script='', search_key=''):
    """Run native ingest-rule hooks before TACTIC's IngestUploadCmd.

    The function is serialized and executed inside TACTIC. Keep it
    self-contained and compatible with the Python runtime shipped by TACTIC
    5.0. Object insertion and check-in remain owned by IngestUploadCmd; this
    preflight reproduces the config/ingest_rule script contract.
    """
    import os

    from pyasm.common import Environment
    from pyasm.search import Search, SearchType

    upload_path = os.path.join(Environment.get_upload_dir(), filename)
    if not os.path.isfile(upload_path):
        raise RuntimeError(
            'Uploaded ingest file does not exist: %s' % filename
        )

    mapped_name = os.path.basename(filename)
    if ignore_ext:
        mapped_name = os.path.splitext(mapped_name)[0]
    sobject = Search.get_by_search_key(search_key) if search_key else None
    if search_key and sobject is None:
        return {
            'accepted': False,
            'reason': 'Matching item no longer exists',
        }
    if sobject is None:
        sobject = SearchType.create(search_type)
    if sobject.column_exists(column):
        sobject.set_value(column, mapped_name)

    for name, value in (extra_data or {}).items():
        if sobject.column_exists(name):
            sobject.set_value(name, value, allow_none=True)

    parent = Search.get_by_search_key(parent_key) if parent_key else None
    if parent is not None:
        try:
            sobject.set_sobject_value(parent)
        except Exception:
            # IngestUploadCmd has the same permissive parent behavior and can
            # still connect relation types that do not expose a direct column.
            pass

    snapshot = SearchType.create('sthpw/snapshot')
    script_input = {
        'path': upload_path,
        'sobject': sobject,
        'parent': parent,
        'snapshot': snapshot,
    }
    if validation_script:
        from tactic.command import PythonCmd
        ingest_exception_type = ()
        try:
            from tactic.command.ingestion_cmd import IngestException
            ingest_exception_type = IngestException
            command = PythonCmd(
                script_path=validation_script,
                input=script_input,
                IngestException=IngestException,
            )
        except ImportError:
            command = PythonCmd(
                script_path=validation_script,
                input=script_input,
            )
        try:
            validation_result = command.execute()
        except ingest_exception_type as error:
            return {
                'accepted': False,
                'reason': str(error),
            }
        if not validation_result:
            return {
                'accepted': False,
                'reason': 'Rejected by validation script',
            }

    if process_script:
        from tactic.command import PythonCmd
        command = PythonCmd(
            script_path=process_script,
            input=script_input,
        )
        if not command.execute():
            return {
                'accepted': False,
                'reason': 'Rejected by process script',
            }

    search_key = ''
    try:
        if int(sobject.get_id() or 0) > 0:
            search_key = sobject.get_search_key()
    except (TypeError, ValueError):
        pass
    return {
        'accepted': True,
        'search_key': search_key,
        'data': sobject.get_data(),
        'snapshot_data': snapshot.get_data(),
    }

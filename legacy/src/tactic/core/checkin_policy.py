"""Fail-closed boundaries of native single-file check-in.

CheckinWdg.get_checkin_script_path resolves config/client_trigger events; its
process panel also reads config/process overrides. Those client/custom options
cannot be silently skipped by calling simple_checkin. This guard detects them;
it does NOT execute or claim to translate arbitrary Python/JavaScript handlers.
"""
from pyasm.search import Search
from pyasm.biz import Pipeline


def checkin_constraints(stype, process, pipeline_code, options):
    reasons = []
    script_keys = ('validate_script_path', 'checkin_script_path')
    for name in (*script_keys, 'checkin_script', 'checkin_options_view'):
        if options.get(name): reasons.append('widget:' + name)
    for name, default in (('checkin_cls', 'pyasm.checkin.FileCheckin'), ('checkin_type', 'strict'),
                          ('snapshot_type', 'file'), ('file_type', 'main')):
        if options.get(name) and options[name] != default: reasons.append('widget:' + name)
    if options.get('is_revision') in (True, 'true') or options.get('level_key'):
        reasons.append('widget:revision/level')
    events = [f'CheckinWdg|{key}|{stype}{suffix}'
              for key in script_keys for suffix in ('', '|' + process)]
    search = Search('config/client_trigger')
    search.add_filters('event', events); search.set_limit(1001)
    triggers = search.get_sobjects()
    if len(triggers) > 1000:
        reasons.append('client_trigger:too_many')
    elif any(t.get_value('callback', no_exception=True) for t in triggers):
        reasons.append('client_trigger:checkin/validation')
    if pipeline_code:
        pipeline = Pipeline.get_by_code(pipeline_code)
        if not pipeline:
            reasons.append('pipeline:not_found')
        else:
            search = Search('config/process', project_code=pipeline.get_value('project_code'))
            search.add_filter('pipeline_code', pipeline_code); search.add_filter('process', process)
            search.set_limit(2); rows = search.get_sobjects()
            if len(rows) > 1: reasons.append('process:ambiguous')
            elif rows:
                for name in ('checkin_validate_script_path', 'checkin_options_view', 'repo_type', 'transfer_mode'):
                    if rows[0].get_value(name, no_exception=True): reasons.append('process:' + name)
    return reasons

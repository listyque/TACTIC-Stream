"""Read-only structural readiness checks for the stock native UI, not a DBA audit.

No row contents, filesystem paths, passwords, DSNs or execution endpoints.
"""
CORE_REQUIRED={
 'project':('code','last_version_update'),
 'search_object':('search_type','table_name','message_event'),
 'login':('login','data'),
 'task':('code','search_code','data','assigned_group','parent_task_code'),
 'snapshot':('code','search_code','context','data','is_current','is_latest'),
 'file':('code','snapshot_code','file_name','relative_dir'),
 'note':('code','search_code','parent_code'),
 'message':('code','message','status'),
 'message_log':('code','message','message_code'),
 'subscription':('code','message_code','login','last_cleared'),
 'dependency':('code','parent_code','snapshot_code'),
 'transaction_log':('code','server_code','ticket'),
}
CONFIG_REQUIRED={
 'config/widget_config':('code','search_type','view','config','priority'),
 'config/naming':('code','checkin_type'),
 'config/prod_setting':('code','key','value'),
 'config/custom_script':('code','script','path'),
 'config/process':('code','pipeline_code','process','workflow','subpipeline_code'),
 'config/pipeline':('code','pipeline','type','name','data'),
 'config/process_state':('code','pipeline_code','process','status','state','data'),
 'config/authenticate':('code','type','data'),
}

def inspect_schema(columns_for, registry=None, *, include_core=True):
    """columns_for(table) returns iterable names; missing table returns empty."""
    checks=[]
    expected=dict(CORE_REQUIRED) if include_core else {}
    for search_type,columns in CONFIG_REQUIRED.items():
        raw=(registry or {}).get(search_type)
        if not raw:
            checks.append({'search_type':search_type,'state':'missing_registration','missing_columns':list(columns)})
            continue
        table=raw.replace('{public}.','').replace('public.','')
        expected[table]=columns
    for table,columns in expected.items():
        actual=set(columns_for(table))
        absent=[name for name in columns if name not in actual]
        checks.append({'table':table,'state':('ok' if not absent else 'missing_columns' if actual else 'missing_table'),
                       'missing_columns':absent})
    return {'scope':'stock native UI required structure only','ready':all(x['state']=='ok' for x in checks),
            'checks':checks,'checked_tables':len(expected),
            'notice':'Read-only structure check; it does not test authentication, all data, triggers, files or custom plug-ins.'}

"""SQLite dialect adapter for the *managed offline* TACTIC upgrade.

Not a SQL API: input is exclusively SQL from the shipped upgrade classes.
Unknown statements/errors are fatal. Already-present schema is inspected before
skipping a historical operation. Rebuilds use new-table/copy/drop/rename, retain
indexes/triggers/rowids/sequence high-water marks, and reject value coercion.
This module depends only on the Python standard library.
"""
from __future__ import annotations
import re
import sqlite3
import uuid

ID = r'(?:"(?:[^"]|"")+"|[A-Za-z_][A-Za-z_0-9]*)'
PAIR_TABLES = ('widget_config', 'naming', 'prod_setting', 'custom_script')

class MigrationError(RuntimeError):
    pass

def ident(value):
    if value.startswith('"'):
        return value[1:-1].replace('""', '"')
    return value

def quote(value):
    return '"' + value.replace('"', '""') + '"'

def split_sql(text, separator=';'):
    """Split outside SQL strings, quoted identifiers, comments and parentheses."""
    chunks=[]; start=0; i=0; depth=0; quoted=None
    while i < len(text):
        c=text[i]
        if quoted:
            if c==quoted:
                if i+1<len(text) and text[i+1]==quoted: i+=2; continue
                quoted=None
        elif text.startswith('--', i):
            end=text.find('\n',i); i=len(text) if end<0 else end; continue
        elif text.startswith('/*',i):
            end=text.find('*/',i+2)
            if end<0: raise MigrationError('Unterminated SQL comment')
            i=end+2; continue
        elif c in ('\'', '"', '`'): quoted=c
        elif c=='(': depth+=1
        elif c==')': depth-=1
        elif c==separator and depth==0:
            chunk=text[start:i].strip()
            if chunk: chunks.append(chunk)
            start=i+1
        if depth<0: raise MigrationError('Unbalanced SQL parentheses')
        i+=1
    if quoted or depth: raise MigrationError('Incomplete SQL statement')
    if text[start:].strip(): chunks.append(text[start:].strip())
    return chunks

def strip_comments(text):
    # Only remove comments outside quoted literals; DDL definitions are retained.
    out=[];i=0;q=None
    while i<len(text):
        c=text[i]
        if q:
            out.append(c)
            if c==q:
                if i+1<len(text) and text[i+1]==q:out.append(q);i+=2;continue
                q=None
        elif c in ('\'', '"', '`'):q=c;out.append(c)
        elif text.startswith('--',i):
            n=text.find('\n',i);i=len(text) if n<0 else n;out.append(' ');continue
        elif text.startswith('/*',i):
            n=text.find('*/',i+2)
            if n<0:raise MigrationError('Unterminated SQL comment')
            i=n+2;out.append(' ');continue
        else:out.append(c)
        i+=1
    return ''.join(out)

def mask_quoted(sql):
    """Keep offsets but mask strings/quoted identifiers for keyword matching."""
    out=list(sql);i=0
    while i<len(sql):
        if sql[i] not in ("'", '"', '`'):
            i+=1;continue
        q=sql[i];start=i;i+=1
        while i<len(sql):
            if sql[i]==q:
                if i+1<len(sql) and sql[i+1]==q:i+=2;continue
                i+=1;break
            i+=1
        else:raise MigrationError('Unterminated quoted SQL token')
        out[start:i]=' '*(i-start)
    return ''.join(out)


def replace_keywords(sql, pattern, replacement):
    matches=list(re.finditer(pattern, mask_quoted(sql), re.I))
    for m in reversed(matches):sql=sql[:m.start()]+replacement+sql[m.end():]
    return sql


def create_parts(sql):
    sql=strip_comments(sql).strip().rstrip(';')
    m=re.match(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?('+ID+r')\s*\(',sql,re.I)
    if not m:raise MigrationError('Only ordinary CREATE TABLE is supported for rebuild')
    # suffix: all supported source tables use a final closing bracket.
    end=sql.rfind(')')
    if end<m.end():raise MigrationError('Malformed CREATE TABLE')
    return ident(m[1]),split_sql(sql[m.end():end],','),sql[end+1:].strip()

def column_name(definition):
    if re.match(r'^(CONSTRAINT|PRIMARY|UNIQUE|CHECK|FOREIGN)\b',definition,re.I):return None
    m=re.match('('+ID+')',definition)
    if not m:raise MigrationError('Unsupported column definition: '+definition)
    return ident(m[1])

class SQLiteUpgrade:
    def __init__(self, connection, *, aliases=None, journal=None, method='', recovery=False):
        self.db=connection
        self.aliases=aliases or {}
        self.journal=journal if journal is not None else []
        self.method=method
        self.recovery=recovery

    def note(self, sql, status, detail=''):
        result={'method':self.method,'status':status,'sql':sql,'detail':detail}
        self.journal.append(result)
        return result

    def exists(self, table):
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

    def columns(self, table):
        return {r[1]:r for r in self.db.execute('PRAGMA table_info('+quote(table)+')')}

    def _canonical(self, table):
        return self.aliases.get(table,table)

    def _rewrite_target(self, sql):
        # Replace target identifiers only, never text inside SQL values.
        patterns=[r'^(?:ALTER\s+TABLE|UPDATE|INSERT\s+INTO|DELETE\s+FROM|DROP\s+TABLE)\s+('+ID+r')',
                  r'^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?('+ID+r')',
                  r'^CREATE\s+(?:UNIQUE\s+)?INDEX\s+'+ID+r'\s+ON\s+('+ID+r')']
        for pattern in patterns:
            m=re.match(pattern,sql,re.I)
            if m:
                table=ident(m[1]); replacement=self._canonical(table)
                if replacement!=table:sql=sql[:m.start(1)]+quote(replacement)+sql[m.end(1):]
                break
        return sql

    def execute(self, text):
        result=[]
        for statement in split_sql(text):
            sql=strip_comments(statement).strip()
            if not sql:continue
            # The source converter does these line-wise; do both, even on one line.
            sql=replace_keywords(sql,r'\bserial\s+PRIMARY\s+KEY\b','integer PRIMARY KEY AUTOINCREMENT')
            sql=replace_keywords(sql,r'\bnow\(\)','CURRENT_TIMESTAMP')
            sql=self._rewrite_target(sql)
            try:result.append(self._one(sql))
            except Exception as exc:
                self.note(sql,'error',str(exc))
                raise MigrationError('%s: %s\nSQL: %s' % (self.method,exc,sql)) from exc
        return result

    def _one(self, sql):
        m=re.match(r'^CREATE\s+TABLE\s+('+ID+r')\s*\(',sql,re.I)
        if m:
            if self.exists(ident(m[1])):return self.note(sql,'already_present','Existing table retained; later migrations still run')
            self.db.execute(sql);return self.note(sql,'applied')
        m=re.fullmatch(r'ALTER\s+TABLE\s+('+ID+r')\s+(.*)',sql,re.I|re.S)
        if m:return self._alter(ident(m[1]),m[2].strip(),sql)
        m=re.match(r'^CREATE\s+(UNIQUE\s+)?INDEX\s+('+ID+r')\s+ON\s+('+ID+r')\s*(?:USING\s+btree\s*)?\((.*?)\)\s*$',sql,re.I|re.S)
        if m:
            name,table=ident(m[2]),ident(m[3]);cols=[ident(x.strip()) for x in split_sql(m[4],',')]
            if not all(re.fullmatch(ID,x.strip()) for x in split_sql(m[4],',')):
                raise MigrationError('Expression indexes need an explicit adapter')
            if not self.exists(table):raise MigrationError('Missing index table '+table)
            existing=self.db.execute('SELECT tbl_name FROM sqlite_master WHERE type=\'index\' AND name=?',(name,)).fetchone()
            if existing:
                info=list(self.db.execute('PRAGMA index_list('+quote(table)+')'))
                matching=next((i for i in info if i[1]==name),None)
                actual=[i[2] for i in self.db.execute('PRAGMA index_info('+quote(name)+')')]
                details=[i for i in self.db.execute('PRAGMA index_xinfo('+quote(name)+')') if i[5]]
                if (existing[0]!=table or actual!=cols or not matching or bool(matching[2])!=bool(m[1])
                    or matching[4] or any(i[3] or i[4]!='BINARY' for i in details)):
                    raise MigrationError('Existing index '+name+' has a different definition')
                return self.note(sql,'already_present','Index definition verified')
            fixed=re.sub(r'\s+USING\s+btree\s*',' ',sql,flags=re.I)
            self.db.execute(fixed);return self.note(sql,'applied','SQLite B-tree index')
        m=re.fullmatch(r'DROP\s+TABLE\s+('+ID+r')',sql,re.I)
        if m:
            table=ident(m[1])
            if not self.exists(table):return self.note(sql,'already_absent')
            if self.db.execute('SELECT 1 FROM '+quote(table)+' LIMIT 1').fetchone():
                raise MigrationError('Refusing to drop non-empty legacy table '+table+'; migrate its data explicitly')
            self.db.execute(sql);return self.note(sql,'applied','Empty obsolete table removed')
        # In historical configs checkin_mode was renamed to checkin_type. Do not
        # overwrite a populated new field with NULL during repair/replay.
        m=re.fullmatch(r'UPDATE\s+('+ID+r')\s+SET\s+"?checkin_type"?\s*=\s*"?checkin_mode"?',sql,re.I)
        if m:
            table=ident(m[1]);cols=self.columns(table)
            if 'checkin_mode' not in cols and 'checkin_type' in cols:return self.note(sql,'superseded','checkin_type already replaces checkin_mode')
            conflicts=self.db.execute('SELECT 1 FROM '+quote(table)+" WHERE checkin_type IS NOT NULL AND checkin_type != '' AND checkin_mode IS NOT NULL AND checkin_mode != checkin_type LIMIT 1").fetchone()
            if conflicts:raise MigrationError('Conflicting old/new check-in modes; automatic overwrite refused')
            self.db.execute('UPDATE '+quote(table)+" SET checkin_type=checkin_mode WHERE checkin_type IS NULL OR checkin_type='' ")
            return self.note(sql,'applied','Only missing destination values filled')
        # Source migrations introduce identity/display columns repeatedly.
        # Existing nonempty values must survive a managed repair.
        if self.recovery:
            fills={
                'UPDATE LOGIN SET DISPLAY_NAME = LAST_NAME || \', \' || FIRST_NAME': ('login','display_name',"last_name || ', ' || first_name"),
                'UPDATE LOGIN_GROUP SET CODE =LOGIN_GROUP':('login_group','code','login_group'),
                'UPDATE SEARCH_OBJECT SET CODE = SEARCH_TYPE':('search_object','code','search_type'),
            }
            normal=re.sub(r'\s+',' ',sql.replace('"','')).upper()
            if normal in fills:
                table,col,expr=fills[normal]
                self.db.execute('UPDATE '+quote(table)+' SET '+quote(col)+'='+expr+' WHERE '+quote(col)+" IS NULL OR "+quote(col)+"='' ")
                return self.note(sql,'applied','Recovery: existing nonempty values preserved')
        if re.match(r'^(INSERT|UPDATE|DELETE)\b',sql,re.I):
            try:self.db.execute(sql)
            except sqlite3.IntegrityError:
                if re.match(r'^INSERT\s+INTO\s+"?(search_object|pref_list)"?\s*\(',sql,re.I):
                    if self._known_insert_present(sql):return self.note(sql,'already_present','Existing natural-key registry/default row preserved')
                raise
            return self.note(sql,'applied')
        raise MigrationError('Unsupported migration statement (not ignored)')

    def _known_insert_present(self,sql):
        m=re.fullmatch(r'INSERT\s+INTO\s+('+ID+r')\s*\((.*?)\)\s*VALUES\s*\((.*)\)',sql,re.I|re.S)
        if not m:return False
        table=ident(m[1]);names=[ident(x.strip()) for x in split_sql(m[2],',')]
        values=split_sql(m[3],',')
        if len(names)!=len(values):return False
        key={'search_object':'search_type','pref_list':'key'}.get(table)
        if not key or key not in names:return False
        literal=values[names.index(key)]
        if not re.fullmatch(r"'(?:[^']|'')*'",literal):return False
        value=literal[1:-1].replace("''", "'")
        return bool(self.db.execute('SELECT 1 FROM '+quote(table)+' WHERE '+quote(key)+'=?',(value,)).fetchone())

    def _alter(self,table,operation,sql):
        if not self.exists(table):raise MigrationError('Missing table '+table)
        cols=self.columns(table)
        m=re.fullmatch(r'ADD\s+CONSTRAINT\s+('+ID+r')\s+UNIQUE\s*\((.*?)\)',operation,re.I|re.S)
        if m:
            return self._one('CREATE UNIQUE INDEX '+m[1]+' ON '+quote(table)+' ('+m[2]+')')
        m=re.fullmatch(r'DROP\s+CONSTRAINT\s+('+ID+r')(?:\s+CASCADE)?',operation,re.I)
        if m:
            name=ident(m[1]);schema=self.db.execute('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?',(table,)).fetchone()[0]
            _,defs,suffix=create_parts(schema)
            retained=[];found=False
            for d in defs:
                named=re.match(r'CONSTRAINT\s+('+ID+r')\s+',d,re.I)
                if named and ident(named[1])==name:found=True
                else:
                    for token in re.finditer(r'\bCONSTRAINT\b',mask_quoted(d),re.I):
                        inline=re.match(r'\s+('+ID+')',d[token.end():])
                        if inline and ident(inline[1])==name:
                            raise MigrationError('Inline named constraint needs explicit handling')
                    retained.append(d)
            if found:
                self.rebuild(table,retained,suffix);return self.note(sql,'applied','Named table constraint removed by rebuild')
            existing=self.db.execute('SELECT tbl_name FROM sqlite_master WHERE type=\'index\' AND name=?',(name,)).fetchone()
            if existing:
                if existing[0]!=table:raise MigrationError('Constraint/index belongs to another table')
                self.db.execute('DROP INDEX '+quote(name));return self.note(sql,'applied','Named index constraint removed')
            return self.note(sql,'already_absent','No named constraint/index to remove')
        m=re.fullmatch(r'ADD\s+(?:COLUMN\s+)?('+ID+r')\s+(.+)',operation,re.I|re.S)
        if m:
            col=ident(m[1])
            if col in cols:return self.note(sql,'already_present','Column exists; existing values retained')
            if col=='checkin_mode' and table in ('naming','spt_naming') and 'checkin_type' in cols:
                return self.note(sql,'superseded','Do not recreate obsolete checkin_mode')
            # General SQLite ADD restrictions (CURRENT_TIMESTAMP, UNIQUE, ...)
            if re.search(r'\b(DEFAULT\s+(?:CURRENT_TIMESTAMP|CURRENT_DATE|CURRENT_TIME)|UNIQUE|PRIMARY\s+KEY)\b',m[2],re.I):
                schema=self.db.execute('SELECT sql FROM sqlite_master WHERE name=?',(table,)).fetchone()[0]
                _,defs,suffix=create_parts(schema);defs.append(m[1]+' '+m[2]);self.rebuild(table,defs,suffix)
            else:self.db.execute('ALTER TABLE '+quote(table)+' ADD COLUMN '+m[1]+' '+m[2])
            return self.note(sql,'applied')
        m=re.fullmatch(r'DROP\s+COLUMN\s+('+ID+r')',operation,re.I)
        if m:
            col=ident(m[1])
            if col not in cols:return self.note(sql,'already_absent')
            if col!='checkin_mode':raise MigrationError('Column removal requires an explicit data-retention policy')
            self.db.execute('ALTER TABLE '+quote(table)+' DROP COLUMN '+quote(col));return self.note(sql,'applied')
        m=re.fullmatch(r'ALTER\s+COLUMN\s+('+ID+r')\s+(DROP\s+NOT\s+NULL|TYPE\s+.+)',operation,re.I|re.S)
        if m:
            col=ident(m[1]);change=m[2]
            if col not in cols:raise MigrationError('Missing column '+table+'.'+col)
            schema=self.db.execute('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?',(table,)).fetchone()[0]
            _,defs,suffix=create_parts(schema)
            if change.upper().startswith('DROP') and not cols[col][3]:return self.note(sql,'already_present','Column is nullable')
            target_type=None
            if change.upper().startswith('TYPE '):
                target_type=change[5:].strip()
                if not re.fullmatch(r'(?:varchar\(\d+\)|character varying\(\d+\)|text|jsonb?|integer|timestamp)',target_type,re.I):
                    raise MigrationError('Unsupported target type or USING conversion '+target_type)
                if re.sub(r'\s+',' ',cols[col][2]).lower()==target_type.lower():return self.note(sql,'already_present','Declared type matches')
            for i,d in enumerate(defs):
                if column_name(d)!=col:continue
                if target_type:
                    cm=re.match('('+ID+r')\s+(.+)',d,re.S)
                    rest=cm[2]
                    limit=re.search(r'\s+(?:CONSTRAINT|PRIMARY|NOT|UNIQUE|CHECK|DEFAULT|COLLATE|REFERENCES|GENERATED)\b',mask_quoted(rest),re.I)
                    tail=rest[limit.start():] if limit else ''
                    defs[i]=cm[1]+' '+target_type+tail
                else:
                    # Source TACTIC column definitions have no embedded CHECKs
                    # at this position. Refuse ambiguous custom expressions.
                    if re.search(r'\b(CHECK|GENERATED|CONSTRAINT)\b',mask_quoted(d),re.I):raise MigrationError('Custom column expression needs manual review')
                    defs[i]=replace_keywords(d,r'\s+NOT\s+NULL\b','')
                break
            self.rebuild(table,defs,suffix);return self.note(sql,'applied','SQLite table rebuilt with retained data/indexes/triggers')
        raise MigrationError('Unsupported ALTER operation '+operation)

    def rebuild(self,table,defs,suffix='', *, fill_null_identity=False):
        if self.db.execute('PRAGMA foreign_keys').fetchone()[0]:
            raise MigrationError('Rebuild requires offline connection with foreign_keys disabled before its transaction')
        old_cols=self.columns(table)
        xinfo=list(self.db.execute('PRAGMA table_xinfo('+quote(table)+')'))
        if any(x[6] for x in xinfo):raise MigrationError('Generated/hidden columns are not supported by this migration')
        if 'WITHOUT ROWID' in suffix.upper():raise MigrationError('WITHOUT ROWID tables require a separate migration')
        related=self.db.execute("SELECT type,name,sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') AND sql IS NOT NULL",(table,)).fetchall()
        views=self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='view'").fetchall()
        # Do not silently break custom views while a table temporarily disappears.
        touching=[v for v in views if re.search(r'(?<![\w])'+re.escape(table)+r'(?![\w])',v[1],re.I)]
        if touching:raise MigrationError('Custom views reference '+table+': '+', '.join(v[0] for v in touching))
        seq=None
        if self.exists('sqlite_sequence'):
            row=self.db.execute('SELECT seq FROM sqlite_sequence WHERE name=?',(table,)).fetchone();seq=row[0] if row else None
        temp='_native_migrate_'+uuid.uuid4().hex
        save='_native_rebuild_'+uuid.uuid4().hex
        self.db.execute('SAVEPOINT '+save)
        try:
            self.db.execute('CREATE TABLE '+quote(temp)+' (\n'+',\n'.join(defs)+'\n) '+suffix)
            new_cols=self.columns(temp)
            names=[n for n in old_cols if n in new_cols]
            if len(names)!=len(old_cols):raise MigrationError('Rebuild would remove columns')
            # Preserve unaliased ROWID as well as explicit primary keys.
            rowid_name=next((x for x in ('rowid','_rowid_','oid') if x not in old_cols),None)
            if rowid_name:names=[rowid_name]+names
            fields=','.join(quote(n) for n in names)
            # The audited SERIAL->INTEGER repair fills only missing id from the
            # existing ROWID. All populated ids must already equal that ROWID.
            identity_expr='COALESCE('+quote('id')+','+quote(rowid_name)+')' if fill_null_identity else None
            select_fields=','.join(identity_expr if n=='id' and fill_null_identity else quote(n) for n in names)
            self.db.execute('INSERT INTO '+quote(temp)+' ('+fields+') SELECT '+select_fields+' FROM '+quote(table))
            # Compare value and storage class (001 TEXT must not become 1 INTEGER).
            typed=','.join('typeof('+quote(n)+'),'+quote(n) for n in names)
            old_typed=','.join('typeof('+ (identity_expr if n=='id' and fill_null_identity else quote(n)) +'),'+ (identity_expr if n=='id' and fill_null_identity else quote(n)) for n in names)
            for a,b,af,bf in ((table,temp,old_typed,typed),(temp,table,typed,old_typed)):
                if self.db.execute('SELECT '+af+' FROM '+quote(a)+' EXCEPT SELECT '+bf+' FROM '+quote(b)+' LIMIT 1').fetchone():
                    raise MigrationError('Rebuild would coerce or lose stored data in '+table)
            self.db.execute('DROP TABLE '+quote(table))
            self.db.execute('ALTER TABLE '+quote(temp)+' RENAME TO '+quote(table))
            for _,_,sql in related:self.db.execute(sql)
            if seq is not None:
                self.db.execute('UPDATE sqlite_sequence SET seq=MAX(seq,?) WHERE name=?',(seq,table))
            self.db.execute('RELEASE '+save)
        except Exception:
            self.db.execute('ROLLBACK TO '+save);self.db.execute('RELEASE '+save);raise


def prepare_config_schema(connection, schema_text, registry, journal=None):
    """Complete missing stock config tables/columns using SHIPPED config DDL.

    Old seeds use unprefixed names for four config tables. Resolve from the
    real search_object registry; never create an empty second data store.
    """
    aliases={}; probe=SQLiteUpgrade(connection)
    for base in PAIR_TABLES:
        old,new=base,'spt_'+base
        configured=registry.get('config/'+base,old).replace('{public}.','').replace('public.','')
        if configured not in (old,new):raise MigrationError('Custom configuration table requires a manual migration: '+configured)
        other=new if configured==old else old
        if probe.exists(other):
            if connection.execute('SELECT 1 FROM '+quote(other)+' LIMIT 1').fetchone():
                raise MigrationError('Registry uses '+configured+' but alternate '+other+' also contains data; refusing to split/merge stores')
        aliases[old]=configured;aliases[new]=configured
    adapter=SQLiteUpgrade(connection,aliases=aliases,journal=journal,method='stock_config_baseline',recovery=True)
    for sql in split_sql(schema_text):
        sql=strip_comments(sql).strip()
        if not sql:continue
        rewritten=adapter._rewrite_target(sql)
        table,defs,suffix=create_parts(rewritten)
        existed=adapter.exists(table)
        adapter.execute(sql)
        if existed:
            for d in defs:
                name=column_name(d)
                if name and name not in adapter.columns(table):
                    if re.search(r'\bPRIMARY\s+KEY\b',d,re.I):raise MigrationError('Stock config table is missing its primary key: '+table)
                    adapter.execute('ALTER TABLE '+quote(table)+' ADD COLUMN '+d)
    return aliases


def identity_issues(connection):
    """Detect legacy SERIAL primary keys: SQLite accepts them but does not assign id.

    This inspects metadata only. It never writes or silently treats ROWID as a
    replacement identity in normal TACTIC queries.
    """
    out=[]
    for table,ddl in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        info=list(connection.execute('PRAGMA table_info('+quote(table)+')'))
        key=next((r for r in info if r[1]=='id' and r[5]),None)
        if key and key[2].strip().lower() in ('serial','bigserial','smallserial'):
            out.append({'table':table,'declared_type':key[2],'problem':'id is not an INTEGER ROWID alias'})
    return out


def repair_identity_columns(connection,journal=None):
    """OFFLINE/staged only: normalize original broken id SERIAL PRIMARY KEY.

    Preserve all existing ids and values. A NULL id receives its already existing
    ROWID. Conflicting/noninteger ids, compound keys and custom views stop the
    staged upgrade. No runtime DDL or INSERT retry is introduced.
    """
    adapter=SQLiteUpgrade(connection,journal=journal,method='sqlite_identity_1.1')
    repaired=[]
    for issue in identity_issues(connection):
        table=issue['table']
        sql=connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()[0]
        _,defs,suffix=create_parts(sql)
        info=adapter.columns(table)
        if sum(bool(v[5]) for v in info.values())!=1:raise MigrationError('Compound SERIAL identity needs manual review: '+table)
        rowid=next((n for n in ('rowid','_rowid_','oid') if n not in info),None)
        if rowid is None or 'WITHOUT ROWID' in suffix.upper():raise MigrationError('No unshadowed ROWID for identity repair: '+table)
        conflict=connection.execute('SELECT 1 FROM '+quote(table)+" WHERE id IS NOT NULL AND (typeof(id)!='integer' OR id!="+quote(rowid)+') LIMIT 1').fetchone()
        if conflict:raise MigrationError('Identity differs from ROWID in '+table+'; no automatic re-numbering is allowed')
        changed=[]
        for definition in defs:
            if column_name(definition)=='id':
                normalized=replace_keywords(definition,r'\b(?:smallserial|bigserial|serial)\s+PRIMARY\s+KEY\b','INTEGER PRIMARY KEY AUTOINCREMENT')
                if normalized==definition:raise MigrationError('Nonstandard SERIAL primary-key declaration: '+table)
                changed.append(normalized)
            else:changed.append(definition)
        null_count=connection.execute('SELECT COUNT(*) FROM '+quote(table)+' WHERE id IS NULL').fetchone()[0]
        adapter.rebuild(table,changed,suffix,fill_null_identity=True)
        adapter.note(sql,'identity_repaired','SERIAL -> INTEGER ROWID alias; filled NULL ids from preserved ROWID: '+str(null_count))
        repaired.append({'table':table,'filled_null_ids':null_count})
    return repaired

"""Project SearchType editor: original registry + column/config commands."""
import re
from .contracts import ApiError, revision, json_safe
from .action_log import execute_traced

COLUMN_TYPES = ('varchar','varchar(256)','text','integer','float','boolean','timestamp','date','timecode','currency','percent')
FORMATS = ('','-1234','-1,234','-1234.12','-1,234.12','-13%','-12.95%','1999-12-31','DATETIME','True|False')
META_FIELDS = ('title','description','color')


class SearchTypeService:
    def _stype_objects(self):
        from pyasm.biz import Project
        return Project.get().get_search_types(include_multi_project=True)

    def _stype_object(self, stype):
        objects=self._stype_objects()
        obj=next((o for o in objects if o.get_value('search_type')==stype),None)
        if obj is None:raise ApiError(403,'stype_scope','SearchType не принадлежит текущему проекту или его исходному типу')
        return obj

    def _stype_can_edit(self,obj):
        # Shared templates/global types must not be mutated as if local.
        return (self.allow_writes and self._project() not in ('sthpw','admin','default','unittest')
                and obj.get_value('namespace')==self._project()
                and obj.get_value('database') in (self._project(),'{project}'))

    def stype_editor(self,method,data):
        from pyasm.search import SearchType
        screen=self._admin_screen(data,('search-types',))
        chosen=data.get('search_type') or screen.get('search_type')
        if not chosen:
            if method!='GET':raise ApiError(400,'stype','Выберите SearchType')
            objs=self._stype_objects()
            if len(objs)>1000:raise ApiError(413,'types_limit','Более 1000 типов в проекте')
            return {'types':[{'code':o.get_value('search_type'),'name':o.get_value('title') or o.get_value('search_type'),
                             'namespace':o.get_value('namespace'),'can_write':self._stype_can_edit(o)} for o in objs],
                    'can_create':self.allow_writes and self._project() not in ('sthpw','admin','default'),
                    'column_types':COLUMN_TYPES,'formats':FORMATS}
        obj=self._stype_object(chosen)
        columns=SearchType.get_column_info(chosen)
        metadata={f:json_safe(obj.get_value(f,no_exception=True)) for f in META_FIELDS}
        models={v:self._model(chosen,v) for v in ('definition','edit_definition','table','edit','insert')}
        rev=revision({'metadata':metadata,'columns':json_safe(columns),'views':[(v,m.fingerprint()) for v,m in models.items()]})
        if method=='GET':
            return {'search_type':chosen,'key':obj.get_search_key(),'metadata':metadata,
                    'registry':{n:obj.get_value(n,no_exception=True) for n in ('namespace','database','table_name','class_name','schema')},
                    'columns':[{'name':name,'schema':json_safe(info),'definition':models['definition'].describe(name),'edit_definition':models['edit_definition'].describe(name)} for name,info in columns.items()],
                    'views':[{'name':v,'elements':m.names()} for v,m in models.items()],
                    'can_write':self._stype_can_edit(obj),'revision':rev,'column_types':COLUMN_TYPES,'formats':FORMATS,
                    'notice':'Физическая схема и widget definitions — разные слои. Исходные определения можно редактировать отдельно. Удаление/смена типа существующих колонок требует проверенной миграции и здесь не выполняется.'}
        if not self._stype_can_edit(obj):raise ApiError(403,'shared_type','Общий, системный или шаблонный тип доступен только для чтения')
        if rev!=data.get('revision'):raise ApiError(409,'conflict','Схема или определения SearchType изменились')
        if method=='PATCH':
            values=data.get('values')
            if not isinstance(values,dict) or not values or set(values)-set(META_FIELDS):raise ApiError(400,'metadata','Разрешены title, description и color')
            for k,v in values.items():
                if not isinstance(v,str) or '\x00' in v or len(v)>(10000 if k=='description' else 256):raise ApiError(400,'metadata','Некорректное значение')
                if k=='title' and not v.strip():raise ApiError(400,'title','Название не должно быть пустым')
                if k=='color' and v and not re.fullmatch(r'#[0-9a-fA-F]{6}',v):raise ApiError(400,'color','Цвет в формате #RRGGBB')
            def update():
                if self.stype_editor('GET',data)['revision']!=rev:raise ApiError(409,'conflict','SearchType изменился')
                self._stub().update(obj.get_search_key(),values)
                return {'saved':True,'search_type':chosen}
            return self._write(update)
        if method=='POST':
            if data.get('confirm')!='ADD_COLUMNS':raise ApiError(400,'confirmation','Требуется подтверждение ADD_COLUMNS')
            entries=data.get('columns')
            if not isinstance(entries,list) or not 1<=len(entries)<=30:raise ApiError(400,'columns','От 1 до 30 новых колонок')
            names=set(columns);validated=[]
            for entry in entries:
                if not isinstance(entry,dict):raise ApiError(400,'column','Некорректная колонка')
                name=entry.get('name');typ=entry.get('data_type');fmt=entry.get('format','')
                if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,49}',name) or name in names:raise ApiError(400,'column_name','Повторное, существующее или некорректное имя колонки')
                if typ not in COLUMN_TYPES or fmt not in FORMATS:raise ApiError(400,'column_type','Неподдержанный тип/формат')
                names.add(name);validated.append({'name':name,'data_type':typ,'format':fmt,'fps':'24'})
            def add():
                if self.stype_editor('GET',data)['revision']!=rev:raise ApiError(409,'conflict','Схема изменена перед выполнением')
                from tactic.core.admin_commands_017 import ColumnEditCbk
                execute_traced(ColumnEditCbk(search_type=chosen,values=validated))
                return {'saved':True,'columns':[e['name'] for e in validated],'command':'ColumnEditCbk',
                        'notice':'Колонки и definition/edit_definition созданы. Добавьте их в нужный view через редактор представления. DDL на некоторых СУБД может иметь собственные commit.'}
            return self._write(add)
        raise ApiError(405,'method','Метод не поддерживается')

    def stype_dependencies(self,method,data):
        """Inspect candidates; not a proof that destructive DDL is safe."""
        from pyasm.search import Search, SearchType
        from pyasm.biz import Schema
        from tactic.core.design_document import parse, serialize
        self._admin_screen(data,('search-types',))
        if method!='GET':raise ApiError(405,'method','Только чтение ссылок')
        stype=data.get('search_type');self._stype_object(stype)
        field=data.get('field','');columns=SearchType.get_column_info(stype)
        if field and field not in columns:raise ApiError(400,'field','Неизвестная колонка')
        pattern=re.compile(r'(?<![\w])'+re.escape(field or stype)+r'(?![\w])')
        refs=[];errors=[]
        from pyasm.common import Environment
        for typ in ('config/widget_config','config/custom_script','config/trigger','config/client_trigger','config/process'):
            q=Search(typ);q.set_limit(1001);objects=q.get_sobjects()
            if len(objects)>1000:raise ApiError(413,'dependency_limit','Более 1000 записей '+typ+'; анализ не объявляется полным')
            for row in objects:
                raw=row.get_sobject_dict()
                if typ=='config/widget_config' and raw.get('login') not in (None,'',Environment.get_user_name()):continue
                text='\n'.join(v for k,v in raw.items() if isinstance(v,str) and k not in ('code','timestamp'))
                if len(text.encode('utf-8'))>4*1024*1024:raise ApiError(413,'dependency_size','Большая конфигурация требует отдельного анализа')
                if not pattern.search(text):continue
                views=[]
                if typ=='config/widget_config':
                    try:
                        root=parse(raw.get('config') or '<config/>')
                        views=[v.get('name') or v.tag for v in root if isinstance(v.tag,str) and pattern.search(serialize(v))]
                    except ValueError:errors.append({'kind':typ,'key':row.get_search_key(),'reason':'XML не разобран'})
                refs.append({'kind':typ,'key':row.get_search_key(),'name':raw.get('title') or raw.get('view') or raw.get('event') or raw.get('code'),
                             'views':views,'match':'текстовая ссылка; требуется проверка смысла'})
        relations=Schema.get().get_related_search_types(stype)
        return {'search_type':stype,'field':field,'references':refs,'related_types':relations,'errors':errors,
                'can_drop':False,'notice':'Это кандидаты ссылок в конфигурации текущего проекта, не полный граф зависимостей: внешние скрипты, исходные файлы и динамические выражения не исследуются. Удаление здесь запрещено.'}

    def stype_import(self,method,data):
        """Bounded create-only subset of ORIGINAL CsvImportCmd.

        No updates, new fields, notes or trigger suppression. Original CSV cell
        whitespace/control normalization is exposed in the preview.
        """
        import csv, io, os, tempfile
        from pyasm.search import SearchType, SObjectFactory
        from pyasm.web import WebContainer
        from pyasm.common import Environment
        from .contracts import clean_values
        screen=self._admin_screen(data,('search-types',))
        stype=data.get('search_type');obj=self._stype_object(stype)
        if not self._stype_can_edit(obj):raise ApiError(403,'import_scope','Импорт разрешён только в локальный тип рабочего проекта')
        old=getattr(self,'active_target',None)
        try:
            self.active_target={'kind':'table','search_type':stype,'view':'table','options':{}}
            form=self.form(stype)['spec']
        finally:self.active_target=old
        columns=SearchType.get_column_info(stype)
        fields=[f for f in form['fields'] if not f.get('read_only') and f.get('storage') and f['name'] in columns and f['name'] not in ('id','code','s_status','timestamp','login','project_code')]
        # CsvImportCmd writes SObject values, not EditWdg action handlers.
        plain={'','DatabaseAction','pyasm.command.DatabaseAction'}
        fields=[f for f in fields if (f.get('action_handler') or f.get('action') or '') in plain and f.get('kind') not in ('password','unsupported')]
        if method=='GET':return {'fields':fields,'max_rows':100,'max_bytes':1048576,'notice':'Только новые записи, без новых колонок. Исходный CsvImportCmd обрезает пробелы по краям ячеек; пустая ячейка не является NULL. Form actions не запускаются; серверные триггеры включены.'}
        if method!='POST':raise ApiError(405,'method','Метод не поддерживается')
        text=data.get('text');mapping=data.get('mapping');delimiter=data.get('delimiter',',')
        if not isinstance(text,str) or '\x00' in text or len(text.encode('utf-8'))>1048576:raise ApiError(400,'csv_size','CSV до 1 МиБ без NUL')
        if delimiter not in (',',';','\t'):raise ApiError(400,'delimiter','Разделитель: запятая, точка с запятой или табуляция')
        if not isinstance(mapping,list) or not 1<=len(mapping)<=30 or any(not isinstance(x,str) for x in mapping):raise ApiError(400,'csv_mapping','Укажите сопоставление колонок')
        allowed={f['name'] for f in fields};selected=[x for x in mapping if x]
        if not selected or len(selected)!=len(set(selected)) or set(selected)-allowed:raise ApiError(400,'csv_mapping','Поля повторяются, защищены или имеют специальный action')
        try:
            reader=csv.reader(io.StringIO(text.lstrip('\ufeff'),newline=''),delimiter=delimiter,strict=True)
            header=next(reader);rows=[]
            if len(header)!=len(mapping):raise ValueError('Размер заголовка не совпадает с mapping')
            for row in reader:
                if len(row)!=len(mapping):raise ValueError('Число ячеек отличается в строке '+str(reader.line_num))
                rows.append({name:re.sub(r'[\x01-\x08\x0b-\x1f\x7f-\x9f]','',cell.strip()) for name,cell in zip(mapping,row) if name})
                if len(rows)>100:raise ValueError('Более 100 строк')
            if not rows:raise ValueError('Нет строк данных')
        except (csv.Error,ValueError,StopIteration) as exc:raise ApiError(400,'csv_parse',str(exc) or 'Пустой CSV') from exc
        for index,row in enumerate(rows):
            try:clean_values(row,fields)
            except ApiError as exc:raise ApiError(400,'csv_value','Строка '+str(index+2)+': '+exc.message) from exc
        required=SObjectFactory.create(stype).get_required_columns()
        if set(required)-set(selected):raise ApiError(400,'csv_required','Нужны колонки: '+', '.join(set(required)-set(selected)))
        fingerprint=revision({'stype':stype,'schema':json_safe(columns),'spec':form['revision'],'rows':rows,'mapping':selected})
        if data.get('operation','preview')=='preview':return {'rows':rows,'count':len(rows),'columns':selected,'preview_revision':fingerprint,'executed':False}
        if data.get('operation')!='import' or data.get('confirm')!='IMPORT_NEW_ROWS':raise ApiError(400,'confirmation','Требуется IMPORT_NEW_ROWS')
        if data.get('preview_revision')!=fingerprint:raise ApiError(409,'preview_changed','Данные, mapping или схема изменились; повторите предпросмотр')
        def save():
            from pyasm.command import CsvImportCmd
            temp=Environment.get_tmp_dir();os.makedirs(temp,exist_ok=True)
            fd,path=tempfile.mkstemp(prefix='native-csv-',suffix='.csv',dir=temp)
            web=WebContainer.get_web();before=dict(web.get_form_data())
            try:
                with os.fdopen(fd,'w',encoding='utf-8',newline='') as stream:
                    writer=csv.writer(stream);writer.writerow(selected);writer.writerows([[row[n] for n in selected] for row in rows])
                values={'search_type_filter':stype,'file_path':path,'has_title':'on','lowercase_title':'','encoder':'utf-8','num_columns':str(len(selected)),'triggers_mode':'True','id_col':'id','web_url':'','test_run':'','start_index':''}
                for i,name in enumerate(selected):
                    values.update({f'column_enabled_{i}':'true',f'column_{i}':name,f'new_column_{i}':'',f'column_type_{i}':'',f'note_process_{i}':''})
                for k,v in values.items():web.set_form_value(k,v)
                cmd=CsvImportCmd();cmd.check();execute_traced(cmd)
                return {'saved':True,'created':len(rows),'command':'pyasm.command.CsvImportCmd','notice':'Записи созданы исходной CSV-командой. Нет автоматического повтора при обрыве ответа.'}
            finally:
                # Preserve the original WebContainer object, only restore its form mapping.
                current=web.get_form_data();current.clear();current.update(before)
                try:os.unlink(path)
                except FileNotFoundError:pass
        return self._write(save)

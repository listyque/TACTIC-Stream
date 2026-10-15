"""Registered preview files for the ordinary ThumbWdg table column.

Snapshot selection follows ThumbWdg.preprocess (file_wdg.py): configured icon
context, publish context, publish process, then any latest; earlier hits win.
This is not legacy HTML rendering or on-demand thumbnail/script generation.
"""
import mimetypes
from pathlib import Path
from urllib.parse import urlencode
from .contracts import ApiError
from .record_service import checked_file_path

THUMBS={'ThumbWdg','pyasm.widget.ThumbWdg','pyasm.widget.file_wdg.ThumbWdg'}
IMAGES={'image/png','image/jpeg','image/gif','image/webp','image/bmp'}
UNSUPPORTED=('redirect','redirect_expr','search_key','script_path','detail_class_name')

def thumbnail_size(options):
    value=str(options.get('icon_size') or '120').rstrip('%px')
    try:return max(24,min(360,int(float(value))))
    except (ValueError,OverflowError):return 120


def select_snapshots(objects,options):
    from pyasm.biz import Snapshot
    if not objects:return {}
    if objects[0].get_base_search_type()=='sthpw/snapshot':
        return {obj.get_search_key():obj for obj in objects}
    context=options.get('icon_context') or objects[0].get_icon_context(None)
    icon_context=None if options.get('latest_icon')=='true' else objects[0].get_icon_context(context)
    data=Snapshot.get_by_sobjects(objects,icon_context,is_latest=True,return_dict=True)
    if options.get('cascade_search','true')!='false':
        for params in ({'context':'publish'},{'process':'publish'},{}):
            if len(data)>=len(objects):break
            fallback=Snapshot.get_by_sobjects(objects,is_latest=True,return_dict=True,**params)
            fallback.update(data);data=fallback
    return data


class ThumbnailService:
    def _thumbnail_spec(self,spec,form=False):
        if form:return spec
        for f in spec['fields']:
            if f.get('handler') not in THUMBS:continue
            opts=f.get('display_options') or {}
            unsupported=next((n for n in UNSUPPORTED if opts.get(n)),None)
            if unsupported or opts.get('protocol')=='file' or opts.get('versionless')=='true':
                f.update(supported=False,read_only=True,reason='ThumbWdg: отдельный адаптер параметра '+(unsupported or 'protocol/versionless')+' ещё не перенесён');continue
            f.update(supported=True,read_only=True,renderer='thumbnail',reason='',thumbnail_size=thumbnail_size(opts))
        spec['diagnostics']=[{'field':f['name'],'handler':f['handler'],'reason':f['reason']} for f in spec['fields'] if f.get('reason')]
        return spec

    def _thumbnail_page(self,objects,spec):
        from pyasm.biz import File
        from pyasm.common import Environment
        cache={}
        for f in spec['fields']:
            if f.get('renderer')!='thumbnail' or not f.get('supported'):continue
            opts=f.get('display_options') or {};entries={};cache[f['name']]=entries
            try:
                snapshots=select_snapshots(objects,opts)
                files={v.get_code():v for v in File.get_by_snapshots(list(snapshots.values()))} if snapshots else {}
                for obj in objects:
                    key=obj.get_search_key();snap=snapshots.get(key)
                    cell={'kind':'thumbnail','text':'Нет изображения','size':f['thumbnail_size'],'state':'empty','detail':opts.get('detail','true')};entries[key]=cell
                    if not snap:continue
                    # File types/order come from the real snapshot XML, not MIME
                    # guesses by column name. No arbitrary client path is used.
                    xml=snap.get_xml_value('snapshot');by_type={}
                    for node in xml.get_nodes('snapshot/file'):
                        code=xml.get_attribute(node,'file_code');typ=xml.get_attribute(node,'type')
                        if code in files:by_type[typ]=files[code]
                    preferred='web' if f['thumbnail_size']>120 else 'icon'
                    order=(opts.get('image_link_order') or 'web|main|.swf').split('|')
                    types=[preferred]+[n for n in order if n!=preferred]+[n for n in by_type if n not in order and n!=preferred]
                    chosen=None
                    for typ in types:
                        file=by_type.get(typ)
                        if not file:continue
                        if file.get_value('file_range',no_exception=True):continue
                        mime=mimetypes.guess_type(file.get_full_file_name())[0]
                        if mime not in IMAGES:continue
                        try:
                            roots=list(Environment.get_asset_dirs().values())+[Environment.get_asset_dir(file_object=file)]
                            checked_file_path(file.get_lib_path(),roots)
                        except ApiError:
                            cell.update(state='missing',text='Файл изображения недоступен');continue
                        chosen=file;break
                    if chosen:
                        params={'project':self._project(),'target':self.active_target['id'],'key':key,'snapshot':snap.get_search_key(),'file':chosen.get_code(),'preview':'1'}
                        link=next((by_type[n] for n in order if n in by_type),chosen)
                        linkparams=dict(params,file=link.get_code(),preview='1')
                        cell.update(state='ready',image='/api/ui/v2/file?'+urlencode(params),href='/api/ui/v2/file?'+urlencode(linkparams),text=chosen.get_full_file_name(),show_filename=opts.get('filename')=='true',file_type=opts.get('file_type')=='true',snapshot=snap.get_search_key())
                    elif cell['state']=='empty' and by_type:
                        cell.update(state='file',text=next(iter(by_type.values())).get_full_file_name())
            except Exception as exc:
                # One bad preview must not prevent unrelated table values. No
                # paths/tickets/exception message are disclosed to the browser.
                for obj in objects:entries[obj.get_search_key()]={'kind':'thumbnail','text':'Ошибка preview: '+type(exc).__name__,'size':f['thumbnail_size'],'state':'error'}
        return cache

    def _thumbnail_cells(self,obj,row,spec):
        fields=[f for f in spec['fields'] if f.get('renderer')=='thumbnail']
        if not fields:return row
        cache=getattr(self,'_thumbnail_cache',None)
        if cache is None:cache=self._thumbnail_page([obj],spec)
        for f in fields:
            value=cache.get(f['name'],{}).get(obj.get_search_key())
            if value:row.setdefault('cells',{})[f['name']]=value
        return row

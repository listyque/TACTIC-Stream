<script>
import ContextMenu from './ContextMenu.vue';

// Presentation of the existing table commands. No new query/save implementation.
// Source: BaseTableLayoutWdg shelf + DgTableGearMenuWdg File/Edit/View groups.
export default {
 name:'TableToolbar', components:{ContextMenu},
 props:{spec:Object,total:Number,selectedCount:{type:Number,default:0},busy:Boolean,
  allowWrites:Boolean,searchOpen:Boolean,filterCount:{type:Number,default:0},
  presentation:{type:String,default:'data'},displayMode:String,recordState:String,
  density:String,wrap:Boolean,groupField:String,dirty:Boolean,saving:Boolean},
 emits:['action'],
 data(){return {menu:null,opened:''}},
 computed:{
  flags(){return Object.assign({show_shelf:true,show_gear:true,show_refresh:true,show_insert:true,
   show_search:true,show_keyword_search:true,show_column_manager:true,show_layout_switcher:true},this.spec.table_options||{})},
  viewLabel(){return this.presentation==='data'?(this.displayMode==='cards'?'Карточки':'Таблица'):
   ({tree:'Дерево связей',timeline:'Gantt / календарь',collections:'Коллекции'})[this.presentation]||'Вид'},
  canSearch(){return this.flags.show_search||this.flags.show_keyword_search},
  canCreate(){return this.flags.show_insert&&Boolean(this.spec.capabilities?.create)},
  hasTimeline(){return this.spec.fields.some(f=>f.renderer==='gantt'||['date','datetime'].includes(f.kind))},
  viewItems(){
   const items=[];
   if(this.flags.show_layout_switcher){
    items.push({type:'title',label:'Представление'});
    for(const [value,label] of [['table','Таблица'],['cards','Карточки'],['tree','Дерево связей'],['timeline','Gantt / календарь'],['collections','Коллекции']]){
     if(value==='timeline'&&!this.hasTimeline||value==='collections'&&!this.spec.collection_supported)continue;
     items.push({id:'layout-'+value,label,value,command:'layout',role:'radio',checked:
      value==='table'||value==='cards'?this.presentation==='data'&&this.displayMode===value:this.presentation===value});
    }
   }
   if(this.flags.show_column_manager){
    items.push({type:'separator'},this.action('columns','Колонки…',true));
   }
   items.push({type:'separator'},{id:'density',label:'Плотность',children:[
    ['compact','Компактная'],['comfortable','Обычная'],['spacious','Свободная']
   ].map(([value,label])=>({id:'density-'+value,label,value,command:'density',role:'radio',checked:this.density===value}))},
    {id:'wrap',label:'Перенос текста',role:'checkbox',checked:this.wrap},
    {id:'group',label:'Группировка страницы',children:[{id:'group-none',label:'Без группировки',command:'group',value:'',role:'radio',checked:!this.groupField},
     ...this.spec.fields.filter(f=>f.storage).map(f=>({id:'group-'+f.name,label:f.label,command:'group',value:f.name,role:'radio',checked:this.groupField===f.name}))]},
    this.action('reset-geometry','Сбросить геометрию'));
   // Geometry still belongs to the live grid when an alternate view is open.
   return items;
  },
  selectionItems(){return [
   this.action('bulk','Изменить выбранные…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,
    this.selectedCount>100?'Не более 100 записей за операцию':!this.spec.capabilities?.update?'Редактирование недоступно для этого представления':'Выберите записи'),
   this.action('fill-selected','Заполнить выбранные ячейки…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,'Нужны 1–100 выбранных строк с доступным редактором'),
   this.action('export','Экспорт выбранных…',!this.busy),
   {type:'separator'},this.action('clear-selection','Снять выделение')
  ]},
  gearItems(){
   const file=[this.action('export','Экспорт CSV…',!this.busy)];
   const edit=[];
   if(this.canCreate)edit.push(this.action('create','Новая запись…',!this.busy));
   edit.push(this.action('bulk','Изменить выбранные…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,
    this.selectedCount>100?'Не более 100 записей':!this.spec.capabilities?.update?'Запись отключена':'Сначала выберите записи'));
   edit.push(this.action('fill-selected','Заполнить выбранные ячейки…',Boolean(this.spec.capabilities?.update)&&this.selectedCount>0&&this.selectedCount<=100&&!this.busy,'Сначала выберите до 100 строк'));
   if(this.dirty)edit.push({type:'separator'},{...this.action('save','Сохранить изменения',!this.saving),shortcut:'Ctrl S'},this.action('discard','Отменить несохранённые правки',!this.saving));
   const view=[this.action('save-view','Сохранить поиск в sidebar…',this.allowWrites,'Запись отключена')];
   if(this.flags.show_column_manager)view.push(this.action('designer','Настроить представление…'));
   view.push({type:'separator'},{id:'record-state',label:'Состояние записей',children:
    [['active','Активные'],['retired','Архив'],['all','Все записи']].map(([value,label])=>({id:'state-'+value,label,command:'state',value,role:'radio',checked:(this.recordState||'active')===value}))});
   const config=[this.action('audit','Источник колонок'),this.action('diagnostics','Ограничения виджетов'+(this.spec.diagnostics?.length?' · '+this.spec.diagnostics.length:''))];
   return [{id:'file',label:'Файл',legacy_label:'File',children:file},
    {id:'edit',label:'Правка',legacy_label:'Edit',children:edit},
    {id:'view',label:'Представление',legacy_label:'View',children:view},
    {type:'separator'},{id:'configuration',label:'Конфигурация',children:config}];
  }
 },
 watch:{spec(){this.close()},presentation(){this.close()}},
 methods:{
  action(id,label,enabled=true,reason=''){return {id,label,enabled,reason:enabled?'':reason}},
  toggle(event,kind){
   if(this.opened===kind){this.close();return}
   const rect=event.currentTarget.getBoundingClientRect();event.currentTarget.focus({preventScroll:true});
   this.opened=kind;
   this.menu={title:kind==='view'?'Вид таблицы':kind==='selection'?'Выбрано: '+this.selectedCount:'Меню таблицы',
    x:rect.right,y:rect.bottom+6,anchor:{left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom},align:'end',variant:'table-command-menu',
    items:kind==='view'?this.viewItems:kind==='selection'?this.selectionItems:this.gearItems};
  },
  keyboard(event,kind){if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();if(this.opened!==kind)this.toggle(event,kind)}},
  choose(item){this.close();this.$emit('action',{id:item.command||item.id,value:item.value})},
  close(){this.menu=null;this.opened=''},
  send(id){this.close();this.$emit('action',{id})}
 }
};
</script>
<template>
<div v-if="flags.show_shelf" class="table-commandbar" role="toolbar" aria-label="Инструменты таблицы">
 <button v-if="canCreate" class="primary table-create" :disabled="busy" @click="send('create')" title="Открыть исходную форму добавления"><span aria-hidden="true">＋</span><span>Новая запись</span></button>
 <button v-if="flags.show_refresh" class="table-icon-button" :disabled="busy" aria-label="Обновить" title="Обновить данные" @click="send('refresh')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M5.6 7a8 8 0 0 1 13.3-1L20 8M4 16l1.1 2a8 8 0 0 0 13.3-1"/></svg></button>
 <button v-if="canSearch" class="table-menu-button" :class="{active:searchOpen||filterCount}" :aria-expanded="searchOpen" @click="send('search')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16M7 12h10M10 19h4"/><circle cx="9" cy="5" r="2"/><circle cx="15" cy="12" r="2"/></svg><span>Поиск</span><span v-if="filterCount" class="counter">{{filterCount}}</span></button>
 <button v-if="selectedCount" class="table-menu-button table-selection-menu" aria-haspopup="menu" :aria-expanded="opened==='selection'" aria-label="Действия с выбранными записями" @click="toggle($event,'selection')" @keydown="keyboard($event,'selection')"><span>{{selectedCount}} выбрано</span><span aria-hidden="true">⌄</span></button>
 <span class="spacer"></span>
 <span class="table-result-count" aria-live="polite">{{total===null||total===undefined?'—':total}} записей</span>
 <button v-if="flags.show_layout_switcher||flags.show_column_manager" class="table-menu-button table-view-menu" aria-label="Вид таблицы" aria-haspopup="menu" :aria-expanded="opened==='view'" @click="toggle($event,'view')" @keydown="keyboard($event,'view')"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 9h16M10 9v11"/></svg><span>{{viewLabel}}</span><span aria-hidden="true">⌄</span></button>
 <button v-if="flags.show_gear" class="table-icon-button table-gear-menu" :class="{active:opened==='gear'}" aria-label="Меню таблицы" title="Файл, правка, представление и конфигурация" aria-haspopup="menu" :aria-expanded="opened==='gear'" @click="toggle($event,'gear')" @keydown="keyboard($event,'gear')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 3-.6 2-2 .8-1.8-1-2 3.4L5 9.7v2.6L3.6 14l2 3.4 1.8-.9 2 .8.6 2.1h4l.6-2.1 2-.8 1.8.9 2-3.4-1.4-1.7V9.7l1.4-1.5-2-3.4-1.8 1-2-.8L14 3Z"/><circle cx="12" cy="11.2" r="3"/></svg></button>
 <ContextMenu v-if="menu" :key="opened" :menu="menu" @action="choose" @close="close"/>
</div>
</template>

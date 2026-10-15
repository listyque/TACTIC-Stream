<script>
import { markRaw } from 'vue';
export default {
 name:'LayoutPreview',
 props:{parts:Object,children:{type:Array,default:()=>[]},project:String,user:Object},
 emits:['open','dirty','changed'],
 data(){return {mounts:[],warnings:[],root:null,childDirty:{}}},
 mounted(){this.root=markRaw(this.$refs.host.attachShadow({mode:'open'}));this.root.addEventListener('submit',e=>e.preventDefault());this.paint()},
 watch:{parts:{deep:true,handler(){this.paint()}},children(){this.paint()}},
 beforeUnmount(){this.mounts=[]},
 methods:{
  childChanged(key,value){this.childDirty[key]=!!value;this.$emit('dirty',Object.values(this.childDirty).some(Boolean))},
  unsafeCss(css){return /[\\@]|url\s*\(|expression|behavior|-moz-binding|image\s*\(|image-set|cross-fade|paint\s*\(|https?:|\/\/|src\s*:|<\/style/i.test(css)},
  paint(){
   if(!this.root)return;
   this.mounts=[];this.warnings=[];
   const template=document.createElement('template');
   template.innerHTML=this.parts?.html||'<p>Пустой HTML</p>';
   const tags=new Set('div span p section article main header footer aside nav h1 h2 h3 h4 h5 h6 ul ol li dl dt dd table thead tbody tfoot tr td th caption colgroup col pre code blockquote strong em b i u s small br hr a img label input textarea select option button form fieldset legend element'.split(' '));
   const attrs=new Set(['class','id','title','style','colspan','rowspan','width','height','alt','type','value','placeholder']);
   const slots=[];
   const clean=parent=>{
    for(const el of [...parent.children]){
     const tag=el.tagName.toLowerCase();
     if(!tags.has(tag)){el.remove();continue}
     if(tag==='element'){
      const n=slots.length,info=this.children[n];
      const holder=document.createElement('section');holder.className='native-layout-widget';holder.dataset.nativeSlot=String(n);
      if(info?.hidden)holder.hidden=true;
      if(!info)holder.textContent='Вложенный виджет: '+(el.getAttribute('name')||n)+' — доступен после сохранения и открытия layout';
      slots.push(info||null);el.replaceWith(holder);continue;
     }
     for(const a of [...el.attributes]){
      const key=a.name.toLowerCase();
      if(!attrs.has(key)||(key==='style'&&this.unsafeCss(a.value)))el.removeAttribute(a.name);
     }
     if(['input','textarea','select','button'].includes(tag))el.setAttribute('disabled','');
     clean(el);
    }
   };
   clean(template.content);
   const style=document.createElement('style');
   style.textContent=':host{display:block;color:inherit;font:inherit}.native-layout-widget{margin:12px 0;min-height:70px}';
   const css=this.parts?.style||'';
   if(css){
    if(this.unsafeCss(css))this.warnings.push('CSS с внешними ресурсами, escape-последовательностями или @-правилами не применяется в ограниченном preview');
    else style.textContent+='\n'+css;
   }
   const sheet=document.createElement('link');sheet.rel='stylesheet';sheet.href='/tactic-ui/styles.css';
   this.root.replaceChildren(sheet,style,template.content);
   this.mounts=[...this.root.querySelectorAll('[data-native-slot]')].filter(el=>slots[Number(el.dataset.nativeSlot)]&&!slots[Number(el.dataset.nativeSlot)].hidden).map(el=>({el:markRaw(el),info:slots[Number(el.dataset.nativeSlot)]}));
   if(this.parts?.mako||this.parts?.behavior||this.parts?.callback||/\[expr\]|<%|\$\{/.test(this.parts?.html||''))this.warnings.push('Mako, expressions, behaviors и callbacks сохранены, но этим preview не исполняются');
  }
 }
};
</script>
<template>
<section class="layout-preview"><p v-for="w in warnings" :key="w" class="notice">{{w}}</p><div ref="host" class="layout-preview-surface"></div><Teleport v-for="m in mounts" :key="m.info.id" :to="m.el"><WidgetHost :project="project" :target="m.info.id" :user="user" @open="$emit('open',$event)" @dirty="childChanged(m.info.id,$event)" @changed="$emit('changed',$event)"/></Teleport></section>
</template>

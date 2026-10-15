/* Dependency-free compiler for THIS repository's ordinary <script> Vue SFCs.
   Uses the bundled official Vue compiler to precompile templates. NOT a generic SFC/Vite replacement.
   Production loads render functions and never calls the runtime template compiler.
   Vue's browser compiler emits non-strict functions (with); output is a classic script, not an ES module.
*/
const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto');
const root=path.resolve(__dirname,'..','..'),src=path.join(root,'frontend','src'),out=path.join(root,'src','tactic','ui_api','web');
const version=fs.readFileSync(path.join(root,'NATIVE_UI_VERSION'),'utf8').trim()+'.0-source-fork';
if(!/^\d+\.\d+\.\d+-source-fork$/.test(version))throw Error('Invalid native version');
const runtime=fs.readFileSync(path.join(out,'vendor','vue.global.prod.js'),'utf8');
const context={console};vm.createContext(context);vm.runInContext(runtime,context);
const Vue=context.Vue;if(!Vue?.version?.startsWith('3.'))throw Error('Vue 3 runtime missing');
const names=['CsvImportPanel','CodeEditor','LayoutPreview','CustomLayoutEditor','ManageViews','ContextMenu','TableToolbar','TableColumns','WidgetDefinition','SidebarNode','WidgetCell','ConfigAudit','CsvExport','FieldInput','ConfiguredForm','CollectionPanel','WorkHoursPanel','ConfiguredTable','FilterGroup','AdvancedFilter','RelationTreeRow','RelationTree','TaskPanel','RelationshipEditor','HistoryPanel','ConfigEditor','GraphEditor','MessageContent','MessageCenter','SubscriptionPanel','UploadQueue','FilePanel','RecordInspector','GroupMembership','SearchTypes','ViewDesigner','TaskTimeline','ScriptEditor','ProjectWizard','SecurityMatrix','UserGroups','UserManager','SidebarEditor','AdminPanel','GlobalSettings','EmbeddedForm','WidgetTable','ConfiguredTabs','WidgetHost','App'];
let result=`/* TACTIC Vue ${version}; templates precompiled with Vue ${Vue.version}. See vendor/VUE_LICENSE.txt. */\n(function(){\nconst _Vue = Vue;\n`;
let api=fs.readFileSync(path.join(src,'api.js'),'utf8').replace('export class HttpError','class HttpError').replace('export default ','return ');
result+=`const api = (function(){\n${api}\n})();\n`;
let uiState=fs.readFileSync(path.join(src,'uiState.js'),'utf8').replace('export default ','return ');
result+=`const uiState=(function(){\n${uiState}\n})();\n`;
for(const name of names){
 const filename=path.join(src,name==='App'?'App.vue':`components/${name}.vue`),s=fs.readFileSync(filename,'utf8');
 const script=s.match(/^<script>\r?\n([\s\S]*?)\r?\n<\/script>/m)?.[1];
 const template=s.match(/^<template>\r?\n([\s\S]*?)\r?\n<\/template>/m)?.[1];
 if(!script||!template)throw Error(`Expected ordinary script/template in ${filename}`);
 let code=script.replace(/^import\s+(.+?)\s+from\s+['"](.+?)['"];?\s*$/gm,(_,binding,from)=>from==='vue'?`const ${binding} = Vue;`:'');
 if(!code.includes('export default '))throw Error('Missing export default in '+name);
 code=code.replace('export default ','const __component = ');
 const errors=[];
 const render=Vue.compile(template,{hoistStatic:false,decodeEntities:s=>s.replace(/&(#x[0-9a-f]+|#[0-9]+|amp|lt|gt|quot|apos);/gi,(_,k)=>k[0]==='#'?String.fromCodePoint(k[1].toLowerCase()==='x'?parseInt(k.slice(2),16):parseInt(k.slice(1),10)):({amp:'&',lt:'<',gt:'>',quot:'\"',apos:"'"})[k]),onError:e=>errors.push(String(e)),onWarn:e=>errors.push(String(e))}).toString();
 if(errors.length)throw Error(`${name}: ${errors.join('\n')}`);
 result+=`const ${name} = (function(){\n${code}\n__component.render = ${render};\nreturn __component;\n})();\n`;
}
result+=`const app=Vue.createApp(App);\n`;
for(const name of names)if(name!=='App')result+=`app.component('${name}', ${name});\n`;
result+=`app.mount('#app');\n})();\n`;
new vm.Script(result); // Syntax-check generated classic script before writing.
fs.writeFileSync(path.join(out,'app.js'),result);
fs.copyFileSync(path.join(src,'styles.css'),path.join(out,'styles.css'));
fs.writeFileSync(path.join(out,'index.html'),`<!doctype html>\n<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>TACTIC · Configuration UI</title><link rel="stylesheet" href="/tactic-ui/styles.css"><script defer src="/tactic-ui/vendor/vue.global.prod.js"></script><script defer src="/tactic-ui/vendor/ace/ace.js"></script><script defer src="/tactic-ui/vendor/ace/ext-searchbox.js"></script><script defer src="/tactic-ui/app.js"></script></head><body><div id="app"></div><noscript>Для интерфейса TACTIC Vue необходим JavaScript.</noscript></body></html>\n`);
const manifest={version,vue:Vue.version,components:names,external_runtime_dependencies:[],files:{}};
for(const f of ['app.js','styles.css','index.html','vendor/vue.global.prod.js',...fs.readdirSync(path.join(out,'vendor/ace')).map(n=>'vendor/ace/'+n)])manifest.files[f]=crypto.createHash('sha256').update(fs.readFileSync(path.join(out,f))).digest('hex');
fs.writeFileSync(path.join(out,'build-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(`Built ${names.length} native Vue components; Vue ${Vue.version}; app.js ${result.length} chars; no npm dependencies.`);

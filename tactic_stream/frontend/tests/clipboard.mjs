import assert from 'node:assert/strict'
import { readClipboardImages } from '../src/controls/clipboard.js'

const reads=[]
const item = types => ({ types,getType:async type=>{ reads.push(type); return new Blob(['image'],{type}) } })
Object.defineProperty(navigator,'clipboard',{value:{read:async()=>[
  item(['text/plain']),item(['image/jpeg','image/png']),item(['image/jpeg'])
]},configurable:true})
const files=await readClipboardImages()
assert.deepEqual(reads,['image/png','image/jpeg'],'Choose one rendition per clipboard item')
assert.deepEqual(files.map(file=>[file.name,file.type]),[['clipboard.png','image/png'],['clipboard-2.jpg','image/jpeg']])
navigator.clipboard.read=async()=>{ throw new Error('Permission denied') }
await assert.rejects(readClipboardImages,/Permission denied/)
console.log('Clipboard: image renditions, unique names and permission failure OK')

// DropPlateController uses native MatchTemplate; browser paths identify selected File handles only.
import { rpc } from '../../api.js'
import { preferences } from '../configuration/preferences.js'
export const defaultPatterns = ['$FILENAME', '$FILENAME.$EXT', '$FILENAME.$FRAME.$EXT', '$FILENAME_$UDIM.$EXT', '$FILENAME_$UV.$EXT', '$FILENAME.$FRAME_$UDIM.$EXT', '$FILENAME.$FRAME_$UV.$EXT', '$FILENAME_$UV.$FRAME.$EXT']
export const sourcePath = file => file.webkitRelativePath || file.name
export const descriptors = files => files.map(file => ({ path:sourcePath(file), size:file.size }))
export { prettySize } from '../../../../src/tactic_stream/shared_ui/features/files/file_values.mjs'
export async function prepareFiles(scope, files, values = {}) {
  return (await rpc('execute_cmd', [scope, 'tactic.command.browser_checkin_cmd.BrowserCheckinCmd', {
    action:'match', source_files:descriptors(files), ...values,
  }], {}, true)).info.groups
}
export async function repositories(scope) {
  const configured = await rpc('get_base_dirs', [scope], {}, true)
  const paths = value => typeof value === 'object' && value ? value : value?.startsWith('{') ? JSON.parse(value) : value ? { default:value } : {}
  const aliases = [...new Set(['default', ...Object.keys(paths(configured.asset_base_dir)), ...Object.keys(paths(configured.base_dir_alias))])]
  const titles = paths(configured.repository_display)
  return aliases.filter(alias => alias !== 'plugins' && (preferences.repository.enabledAliases === null || preferences.repository.enabledAliases.includes(alias))).map(alias => ({ value:alias, label:titles[alias]?.title || alias }))
}
export async function droppedFiles(transfer) {
  const files = []
  async function visit(entry, path = '') {
    if (entry.isFile) {
      const file = await new Promise((resolve, reject) => entry.file(resolve, reject))
      Object.defineProperty(file, 'webkitRelativePath', { value:path + file.name })
      files.push(file)
    } else if (entry.isDirectory) {
      const reader = entry.createReader()
      for (;;) {
        const children = await new Promise((resolve, reject) => reader.readEntries(resolve, reject))
        if (!children.length) break
        for (const child of children) await visit(child, path + entry.name + '/')
      }
    }
  }
  const entries = [...(transfer.items || [])].filter(item => item.kind === 'file').map(item => item.webkitGetAsEntry?.())
  if (entries.length && entries.every(Boolean)) for (const entry of entries) await visit(entry)
  else files.push(...transfer.files)
  return files
}

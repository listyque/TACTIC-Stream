// Handler remembers choices per user/project/Search Type, never field values.
export const contentChoices = ['copySnapshots', 'copyTasks', 'copyProcessMessages', 'copyTaskMessages', 'copyProcessAttachments', 'copyTaskAttachments']
function key(login, project, type) { return 'tactic-stream.duplicate.' + JSON.stringify([login, project, type]) }
export function duplicateProfile(login, project, type) {
  try { const value = JSON.parse(localStorage.getItem(key(login, project, type))); return value?.relations && value?.processes ? value : null }
  catch { return null }
}
export function saveDuplicateProfile(login, project, type, profile) { localStorage.setItem(key(login, project, type), JSON.stringify(profile)) }
export function changeContent(process, name, value) {
  process[name] = value
  if (!value && name === 'copyTasks') process.copyTaskMessages = process.copyTaskAttachments = false
  if (!value && name === 'copyTaskMessages') process.copyTaskAttachments = false
  if (!value && name === 'copyProcessMessages') process.copyProcessAttachments = false
  if (process.copyTaskAttachments) process.copyTaskMessages = process.copyTasks = true
  if (process.copyTaskMessages) process.copyTasks = true
  if (process.copyProcessAttachments) process.copyProcessMessages = true
}
export function applyDuplicateProfile(analysis, profile) {
  for (const relation of analysis.relations) {
    const mode = profile?.relations?.[relation.key]
    if (relation.options.some(option => option.value === mode)) relation.mode = mode
  }
  for (const process of analysis.processes) {
    for (const name of contentChoices) process[name] = profile?.processes?.[process.name]?.[name] === true
    if (process.copyTaskAttachments) process.copyTaskMessages = process.copyTasks = true
    if (process.copyTaskMessages) process.copyTasks = true
    if (process.copyProcessAttachments) process.copyProcessMessages = true
  }
}

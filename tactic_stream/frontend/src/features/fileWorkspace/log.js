import { t } from '../../i18n.js'
import { redact } from '../debug/debugLog.js'

export function operationTitle(action) {
  return t(({changes:'Refresh',workspaces:'Refresh',checkout:'Checkout',submit:'Submit',
    create_change:'New changelist',update_change:'Edit description',move_files:'Move files',
    rename_files:'Rename file',shelve:'Shelve',unshelve_begin:'Unshelve',merge_begin:'Merge',
    revert:'Revert',remove_files:'Remove selected from changelist',delete_change:'Delete empty changelist',
    restore_file:'Restore revision',storage_status:'Storage administration',storage_policy:'Save storage policy',
    gc_begin:'Run safe GC',gc_status:'GC status',switch_workspace:'Switch workspace'})[action] || 'File operation')
}

export function userError(error) {
  const raw = redact(String(error.message || error))
  if (error.name === 'AbortError') return {level:'INFO',path:'',message:t('Stopped. Server work and uploaded files are retained; refresh or resume.')}
  return {level:'ERROR',path:'',message:t(raw.includes('Traceback') || raw.includes('\n') ? 'File operation failed. Open Debug Log for details.' : raw)}
}

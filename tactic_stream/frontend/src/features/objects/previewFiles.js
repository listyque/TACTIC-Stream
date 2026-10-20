import { t } from '../../i18n.js'

export async function fileBlob(file, { signal } = {}) {
  if (!file?.href) throw new Error(t('No web path is configured for this file.'))
  const response = await fetch(file.href, { signal })
  if (!response.ok) throw new Error(t('File Offline'))
  return response.blob()
}

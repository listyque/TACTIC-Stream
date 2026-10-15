import { t } from '../../i18n.js'

export async function fileBlob(file) {
  if (!file?.href) throw new Error(t('No web path is configured for this file.'))
  const response = await fetch(file.href)
  if (!response.ok) throw new Error(t('File Offline'))
  return response.blob()
}

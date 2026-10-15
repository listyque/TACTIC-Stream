// Handler UserSearch.js (EPL-1.0): match login, label and group names together.
export function matchesUser(user, query) {
  query = String(query || '').trim().toLowerCase()
  return !query || `${user.login} ${user.displayName || ''} ${user.email || ''} ${(user.groups || []).join(' ')}`.toLowerCase().includes(query)
}

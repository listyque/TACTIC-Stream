<script setup>
// UserProfileView.qml / UserController: one owner for requests, selection and editor.
import { ref, computed, nextTick, watch, onBeforeUnmount, toRaw } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppSearchField from '../../controls/AppSearchField.vue'
import AppTextField from '../../controls/AppTextField.vue'
import SummaryChip from '../../controls/SummaryChip.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppSelect from '../../controls/AppSelect.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import UserGroupSection from '../../controls/UserGroupSection.vue'
import ProfileInfoRow from '../../controls/ProfileInfoRow.vue'
import BusyIndicator from '../../controls/BusyIndicator.vue'
import ActivityEventCard from '../activity/ActivityEventCard.vue'
import { userProfile, userAvatar, activityFeed } from '../../api.js'
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import { mobile } from '../../mobile.js'
import './userProfile.css'
const props = defineProps({ ticket: String, project: String, login: String, updates: Object })
const emit = defineEmits(['message', 'tasks', 'activity', 'open-object', 'open-link', 'logout', 'saved', 'session-expired'])
const serverHost = location.host
const dialog = ref(null), editor = ref(null), avatarInput = ref(null)
const directoryExpanded = ref(true)
const visible = ref(false), directory = ref(false), width = ref(252), query = ref(''), selected = ref('')
const result = ref(null), summary = ref(null), events = ref([]), expanded = ref(false), error = ref(''), relatedError = ref(''), busy = ref(false), relatedBusy = ref(false)
const draft = ref(null), original = ref(null), mode = ref('profile'), creating = ref(false), saving = ref(false), uncertain = ref(false), editingError = ref(''), confirmClose = ref(false), avatar = ref(null)
let requestId = 0, mutationId = 0
const profile = computed(() => result.value?.profile || {})
const permissions = computed(() => result.value?.permissions || {})
const presence = login => props.updates?.presence?.find(row => row.login === login) || (login === props.login ? {online:true} : undefined)
const filteredUsers = computed(() => (result.value?.users || []).filter(row => !row.retired && (row.login + ' ' + row.displayName + ' ' + (row.email || '')).toLowerCase().includes(query.value.toLowerCase())))
const userGroups = computed(() => [...new Set(filteredUsers.value.map(row => row.primaryGroup))].map(label => ({ label, users:filteredUsers.value.filter(row => row.primaryGroup === label) })))
const dirty = computed(() => !!draft.value && (JSON.stringify(draft.value) !== JSON.stringify(original.value) || !!avatar.value))
const profileFields = [['first_name','First name'],['last_name','Last name'],['display_name','Display name'],['department','Department'],['email','Email'],['phone_number','Phone number'],['address','Address']]
const accountFields = [['upn','UPN'],['namespace','Namespace'],['s_status','Account status'],['project_code','Project code'],['hourly_wage','Hourly wage']]
const metrics = [['total','Total'],['completed','Completed tasks'],['incomplete','Incomplete'],['overdue','Overdue'],['dueThisWeek','Due this week']]
const accessLevels = [{value:'',label:'Server default (Low)'},{value:'high',label:'High'},{value:'medium',label:'Medium'},{value:'low',label:'Low'},{value:'min',label:'Minimum'},{value:'none',label:'None'}]
const info = computed(() => [['project','Project','MDI_BRIEFCASE'],['email','Email','MDI_EMAIL'],['phone_number','Contact','MDI_PHONE'],['address','Address','MDI_BOOK_ACCOUNT'],['department','Department','MDI_BRIEFCASE']].map(([key,label,icon]) => ({ label,icon,value:String(profile.value[key] || '') })))
function hours(value) { appearance.language; return Number(value || 0).toLocaleString(appearance.language, { maximumFractionDigits:1 }) }
function fail(failure, editing = false) { (editing ? editingError : error).value = failure.message; if (failure.code === 'authentication_failed') emit('session-expired') }
async function load(login = selected.value) {
  if (!props.ticket || !login) return
  const id = ++requestId, ticket = props.ticket, project = props.project
  selected.value = login; busy.value = true; error.value = ''; relatedError.value = ''; result.value = summary.value = null; events.value = []; expanded.value = false
  try {
    const value = await userProfile('read', ticket, project, { login })
    if (id !== requestId) return
    result.value = value; busy.value = false; relatedBusy.value = true
    const related = await Promise.allSettled([userProfile('summary', ticket, project, { login }), activityFeed(ticket, project, { users:[login], filter:'all' }, true)])
    if (id !== requestId) return
    for (const [index,row] of related.entries()) {
      if (row.status === 'fulfilled') { if (index) events.value = row.value.records; else summary.value = row.value }
      else { relatedError.value += (relatedError.value ? '\n' : '') + row.reason.message; if (row.reason.code === 'authentication_failed') emit('session-expired') }
    }
  } catch (failure) { if (id === requestId) fail(failure) }
  finally { if (id === requestId) busy.value = relatedBusy.value = false }
}
async function open(login = props.login, showDirectory = false) {
  directory.value = showDirectory; directoryExpanded.value = showDirectory; visible.value = true
  await nextTick(); if (!dialog.value.open) dialog.value.show()
  await load(login)
}
function close() { if (saving.value) return; closeEditor(true); requestId++; dialog.value?.close(); visible.value = false }
async function edit(create = false, page = 'profile') {
  if (mobile.value && (create || page === 'groups')) return
  if (saving.value || (!create && !permissions.value.edit) || create && !permissions.value.manage) return
  creating.value = create; mode.value = page; editingError.value = ''; uncertain.value = false; confirmClose.value = false; avatar.value = null
  draft.value = create ? Object.fromEntries([...profileFields,...accountFields].map(([key]) => [key,''])) : structuredClone(toRaw(result.value.document))
  if (create) Object.assign(draft.value, { login:'', password:'', groups:[] })
  draft.value.accessLevels = Object.fromEntries((result.value.groups || []).map(row => [row.code,row.accessLevel]))
  original.value = structuredClone(toRaw(draft.value))
  await nextTick(); editor.value.showModal()
}
function closeEditor(force = false) {
  if (!force && (saving.value || dirty.value || uncertain.value)) { if (!saving.value) confirmClose.value = true; return }
  mutationId++; editor.value?.close(); if (draft.value) draft.value.password = ''; draft.value = original.value = avatar.value = null; confirmClose.value = false
}
function toggleGroup(code, enabled) { draft.value.groups = enabled ? [...new Set([...draft.value.groups,code])] : draft.value.groups.filter(row => row !== code) }
async function save() {
  if (saving.value || uncertain.value) return
  const id = ++mutationId, ticket = props.ticket, project = props.project, login = creating.value ? draft.value.login : selected.value
  const document = structuredClone(toRaw(draft.value))
  if (!permissions.value.manage || creating.value) delete document.accessLevels
  saving.value = true; editingError.value = ''
  try {
    const value = await userProfile(creating.value ? 'create' : 'save', ticket, project, { login, document, revision:result.value.revision })
    if (id !== mutationId) return
    result.value = value; selected.value = login; creating.value = false
    draft.value = { ...value.document, accessLevels:document.accessLevels || {} }; original.value = structuredClone(toRaw(draft.value))
    if (avatar.value) {
      const uploaded = await userAvatar(ticket, project, login, value.revision, avatar.value.token, avatar.value.file)
      if (id !== mutationId) return
      result.value = uploaded; avatar.value = null
    }
    const saved = result.value.profile
    closeEditor(true); emit('saved',saved); await load(login)
  } catch (failure) { if (id === mutationId) { uncertain.value = !failure.status || failure.status >= 500; fail(failure, true) } }
  finally { if (id === mutationId || !draft.value) saving.value = false }
}
async function reloadEditor() {
  if (saving.value) return
  closeEditor(true); await load(); if (result.value) await edit()
}
function changeAvatar(event) { const file = event.target.files[0]; event.target.value = ''; if (file) avatar.value = { file, token:[...crypto.getRandomValues(new Uint8Array(16))].map(value => value.toString(16).padStart(2,'0')).join('') } }
function activate(name, value) { if (saving.value) return; close(); emit(name,value) }
function beforeUnload(event) { if (dirty.value || saving.value || uncertain.value) { event.preventDefault(); event.returnValue = '' } }
watch(() => [props.ticket,props.project], () => { mutationId++; saving.value = false; close(); result.value = null })
window.addEventListener('beforeunload',beforeUnload)
onBeforeUnmount(() => { requestId++; mutationId++; window.removeEventListener('beforeunload',beforeUnload); if (draft.value) draft.value.password = '' })
defineExpose({ open })
</script>
<template>
<Teleport to="body">
  <dialog v-window="{kind:'user_profile', type:'window' }" ref="dialog" class="user-profile-window" :class="{directory}" :aria-label="t(directory ? 'Users' : 'User profile')" :aria-busy="busy || relatedBusy" @cancel.prevent="close">
    <header><AppButton v-if="directory" class="user-directory-toggle" label="Show users" icon="menu" icon-only :aria-expanded="directoryExpanded" @click="directoryExpanded = !directoryExpanded" /><AppIcon name="MDI_ACCOUNT" /><strong>{{ t(directory ? 'Users' : 'User profile') }}</strong><AppButton label="Close profile" icon="close" icon-only :disabled="saving" @click="close" /></header>
    <div class="user-profile-layout" :class="{ 'show-directory':directoryExpanded }" :style="{ '--user-directory-width':width+'px' }">
      <AppButton v-if="directory && directoryExpanded" class="user-directory-backdrop" label="Hide users" @click="directoryExpanded = false" /><aside v-if="directory" class="user-directory"><header><strong>{{ t('USERS') }}</strong><small>{{ filteredUsers.length }}</small><AppButton v-if="permissions.manage && !mobile" icon="MDI_ACCOUNT_PLUS" label="Add user" icon-only @click="edit(true)" /></header><AppSearchField v-model="query" label="Search users" :placeholder="t('Search users')" /><div class="user-directory-list"><template v-for="group in userGroups" :key="group.label"><UserGroupSection :title="group.label" /><AppButton v-for="user in group.users" :key="user.login" :label="user.displayName" class="user-directory-row" :class="{ selected: user.login === selected, current: user.login === login }" @click="load(user.login); directoryExpanded = false"><ItemPreview v-bind="{ source:user.avatarUrl, fallbackText:user.initials, accent:user.avatarColor }" :preview-size="34" round outlined /><span><strong>{{ user.displayName }}</strong><small>{{ user.login }}</small></span><i v-if="presence(user.login)" :class="{ online:presence(user.login).online }"></i></AppButton></template></div></aside>
      <AppSplitter v-if="directory && !mobile" v-model="width" :min="210" :max="360" label="Resize user directory" />
      <section class="user-profile-pane">
        <div v-if="profile.login" class="user-profile-summary">
          <ItemPreview :source="profile.avatarUrl" :fallback-text="profile.initials" :accent="profile.avatarColor" :preview-size="mobile ? 56 : 168" round outlined />
          <div class="user-profile-name"><strong>{{ profile.displayName }}</strong><span class="muted"><i v-if="presence(selected)" class="profile-presence" :class="{ online:presence(selected).online }"></i>{{ selected }} · {{ t(presence(selected) ? presence(selected).online ? 'Online' : 'Offline' : 'Status unavailable') }}</span></div>
          <div class="user-profile-actions"><AppButton v-if="selected !== login" label="Message" icon="MDI_MESSAGE" :icon-only="mobile" highlighted @click="activate('message',selected)" /><component :is="mobile ? AppMenu : 'div'" class="user-profile-options" label="Profile actions" :overlay="mobile"><AppButton v-if="permissions.edit" label="Edit user profile" icon="edit" :icon-only="!mobile" @click="edit()" /><AppButton label="Refresh profile" icon="refresh" :icon-only="!mobile" :disabled="busy || relatedBusy" @click="load()" /><AppButton v-if="mobile" label="Open Task Manager" icon="task" @click="activate('tasks',{ login:selected })" /><AppButton v-if="mobile" label="Open full activity" icon="activity-feed" @click="activate('activity',selected)" /><AppButton v-if="selected === login" label="Sign out" icon="MDI_LOGOUT" :icon-only="!mobile" destructive @click="activate('logout')" /></component></div>
          <div class="user-profile-info"><strong>{{ t('PROFILE') }}</strong><div><ProfileInfoRow v-for="row in info" :key="row.label" v-bind="row" /><ProfileInfoRow icon="MDI_SERVER" label="Server" :value="serverHost" /></div></div>
          <div class="user-profile-groups"><header><strong>{{ t('GROUPS AND ROLES') }}</strong><AppButton v-if="permissions.manage && !mobile" icon="MDI_ACCOUNT_GROUP" label="Edit group membership" icon-only @click="edit(false,'groups')" /></header><div class="user-profile-chips"><SummaryChip v-for="group in profile.groups" :key="group.code" :label="group.label" :show-count="false" /><SummaryChip v-for="role in profile.roles" :key="role" :label="role" :show-count="false" :show-dot="false" /></div><small v-if="!profile.groups.length && !profile.roles.length" class="muted">{{ t('No groups or roles returned by TACTIC') }}</small></div>
        </div>
        <div class="user-profile-scroll">
          <div v-if="profile.login" class="user-profile-related">
            <section class="user-work-summary"><strong>{{ t('PROJECT TASKS') }}</strong><div class="user-task-metrics"><div v-for="[key,label] in metrics" :key="key"><strong :class="{ 'error-text':key === 'overdue' && summary?.taskSummary?.overdue }">{{ !summary ? '—' : key === 'completed' ? Math.max(0,(summary?.taskSummary?.total || 0) - (summary?.taskSummary?.incomplete || 0)) : summary?.taskSummary?.[key] || 0 }}</strong><small>{{ t(label) }}</small></div></div><hr>
              <template v-for="[key,label,filter] in [['statusSummary','BY STATUS','status'],['processSummary','BY PROCESS','process']]" :key="key"><strong>{{ t(label) }}</strong><div class="user-profile-chips"><SummaryChip v-for="row in summary?.[key] || []" :key="row.value" :label="row.label" :count="row.count" :accent="row.color" clickable @click="activate('tasks',{ login:selected, key:filter, value:row.value })" /></div></template>
              <section v-if="summary?.permissions?.viewWorkHours" class="user-work-hours"><hr><header><strong>{{ t('WORK HOURS') }}</strong><small>{{ t('THIS WEEK') }}</small></header><div class="user-task-metrics"><div v-for="[key,label] in [['loggedHours','Logged'],['approvedHours','Approved'],['pendingHours','Pending']]" :key="key"><strong>{{ t('{hours} h',{ hours:hours(summary.workHourSummary[key]) }) }}</strong><small>{{ t(label) }}</small></div></div></section>
              <AppButton v-if="!mobile" label="Open Task Manager" icon="MDI_CLIPBOARD_TEXT_OUTLINE" highlighted @click="activate('tasks',{ login:selected })" /><small v-if="summary && !summary.taskSummary.total" class="muted">{{ t('No assigned tasks in the current project') }}</small>
            </section>
            <section class="user-recent-activity"><header><strong>{{ t('RECENT ACTIVITY') }}</strong><AppButton v-if="!mobile" label="Open full activity" icon="activity-feed" icon-only @click="activate('activity',selected)" /></header><ActivityEventCard v-for="row in expanded ? events : events.slice(0,6)" :key="row.eventId" :record="row" @activity="activate('open-object',{ record:row, target:false })" @target="activate('open-object',{ record:row,target:true })" @open-link="activate('open-link',$event)" /><AppButton v-if="events.length > 6" :label="expanded ? 'Show less' : 'Show more'" :icon="expanded ? 'MDI_CHEVRON_UP' : 'MDI_CHEVRON_DOWN'" @click="expanded = !expanded" /><small v-if="!relatedBusy && !events.length" class="muted">{{ t(relatedError ? 'Activity is unavailable' : 'No recent activity') }}</small></section>
          </div>
          <p v-if="error || relatedError" class="error" role="alert">{{ t(error || relatedError) }}</p><BusyIndicator v-if="busy || relatedBusy" running /><AppButton v-if="error" label="Retry" @click="load()" />
        </div>
      </section>
    </div>
  </dialog>
  <dialog ref="editor" class="user-profile-editor" :aria-label="t(creating ? 'Add user' : mode === 'groups' ? 'Edit group membership' : 'Edit user profile')" :aria-busy="saving" @cancel.prevent="closeEditor()">
    <header><strong>{{ t(creating ? 'Add user' : mode === 'groups' ? 'Edit group membership' : 'Edit user profile') }}</strong><AppButton icon="close" label="Close profile editor" icon-only :disabled="saving" @click="closeEditor()" /></header>
    <form v-if="draft" @submit.prevent="save">
      <div class="user-editor-identity"><ItemPreview :file="avatar?.file" :source="creating ? '' : profile.avatarUrl" :fallback-text="creating ? '?' : profile.initials" :accent="profile.avatarColor" :preview-size="54" round outlined /><span><strong>{{ creating ? t('New user') : profile.displayName }}</strong><small>{{ draft.login }}</small></span><AppButton v-if="mode === 'profile'" label="Change avatar" icon="image" :disabled="saving || uncertain" @click="avatarInput.click()" /><input ref="avatarInput" hidden type="file" accept=".jpg,.jpeg,.png,.webp" :aria-label="t('Choose avatar')" @change="changeAvatar" /></div>
      <p v-if="avatar" class="notice">{{ avatar.file.name }}</p>
      <AppSegmentedButton v-if="permissions.manage && !mobile" v-model="mode" :options="[{value:'profile',label:'Profile',icon:'MDI_ACCOUNT'},{value:'groups',label:'Groups',icon:'MDI_ACCOUNT_GROUP'}]" :disabled="saving" label="Profile editor section" />
      <div class="user-editor-scroll"><div v-if="mode === 'profile'" class="user-editor-fields"><AppTextField v-if="creating" class="wide" v-model="draft.login" label="Login" placeholder="Login" required :disabled="saving || uncertain" autocomplete="off" /><AppTextField v-for="[key,label] in profileFields.filter(([key]) => key in draft)" :key="key" v-model="draft[key]" :class="{wide:key === 'address'}" :label="label" :placeholder="label" :disabled="saving || uncertain" /><AppTextField class="wide" label="New password — leave empty to keep current" placeholder="New password — leave empty to keep current" v-model="draft.password" type="password" autocomplete="new-password" :disabled="saving || uncertain" /><strong v-if="permissions.manage && !mobile" class="wide">{{ t('ACCOUNT SETTINGS') }}</strong><template v-if="permissions.manage && !mobile"><AppTextField v-for="[key,label] in accountFields.filter(([key]) => key in draft)" :key="key" v-model="draft[key]" :label="label" :placeholder="label" :disabled="saving || uncertain" /></template></div>
      <div v-else class="user-editor-memberships"><p class="muted">{{ t("Group membership changes affect this user's permissions.") }}</p><p v-if="!creating" class="user-access-explanation">{{ t("Access level is shared by every member of the group. Empty uses TACTIC's Low default.") }}</p><article v-for="group in result.groups" :key="group.code"><AppCheckbox :label="group.label" :translate-label="false" :model-value="draft.groups.includes(group.code)" :disabled="saving || uncertain" @update:model-value="toggleGroup(group.code,$event)" /><small>{{ group.description }}</small><AppSelect v-if="!creating" v-model="draft.accessLevels[group.code]" :options="accessLevels" :label="t('Access level')" :disabled="saving || uncertain" /></article></div></div>
      <p v-if="editingError" class="error" role="alert">{{ t(editingError) }}</p><AppButton v-if="uncertain" label="Reload from server" @click="reloadEditor" />
      <div v-if="confirmClose" class="notice" role="alert">{{ t('Discard unsaved user changes?') }}<AppButton label="Keep editing" @click="confirmClose = false" /><AppButton label="Discard changes" destructive @click="closeEditor(true)" /></div>
      <footer><AppButton label="Cancel" :disabled="saving" @click="closeEditor()" /><AppButton type="submit" :label="creating ? 'Create' : 'Save'" icon="save" highlighted :disabled="saving || uncertain" /></footer>
    </form>
  </dialog>
</Teleport>
</template>

<script>
import { nextTick } from 'vue';
import {
  rpc,
  uploadFormFile,
  linkPreviews,
  messageFileRequest
} from '../../api.js';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import { appearance } from '../../appearance.js';
import { preferences } from '../configuration/preferences.js';
import AppButton from '../../controls/AppButton.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AttachmentCard from '../../controls/AttachmentCard.vue';
import { copyText, readClipboardImages } from '../../controls/clipboard.js';
import { sameSearchKey } from '../workspace/links.js';
import { timestampLabel } from '../activity/activity.js';
import TaskInspectorHeader from './TaskInspectorHeader.vue';
import MessageComposer from '../messages/MessageComposer.vue';
import FilePreview from './FilePreview.vue';
import { fileBlob } from './previewFiles.js';
import TaskDetails from './TaskDetails.vue';
import RelatedTasks from './RelatedTasks.vue';
import RecordForm from './RecordForm.vue';
import WorkHoursSummary from './WorkHoursSummary.vue';
import Timesheet from './Timesheet.vue';
import NoteEntry from './NoteEntry.vue';
import NoteBody from './NoteBody.vue';
import NoteDialogs from './NoteDialogs.vue';
import { extractSkeys } from '../../controls/richText.js';
import { skeyPlaceholder } from './skeyPreviews.js';
import './inspector.css';

export default {
  inject: {
    openHelp: {},
    openUserProfile: { default: null },
    openObjectTab: { default: null },
    openTaskInspector: { default: null }
  },
  components: {
    AppButton,
    AppSelect,
    AppIcon,
    AppTextArea,
    AppMenu,
    AttachmentCard,
    FilePreview,
    TaskDetails,
    RelatedTasks,
    RecordForm,
    WorkHoursSummary,
    Timesheet,
    NoteEntry,
    NoteBody,
    NoteDialogs,
    TaskInspectorHeader,
    MessageComposer
  },
  props: {
    ticket: String,
    project: String,
    searchType: String,
    updates: Object,
    dockTarget: String,
    active: Boolean
  },
  emits: ['back', 'saved', 'open-link', 'visibility'],
  data() {
    return {
      opened: false,
      target: null,
      context: null,
      contexts: [],
      configuredProcesses: [],
      alive: true,
      notes: [],
      process: 'publish',
      drafts: {},
      notePreviews: {},
      previewUrls: {},
      previewRequest: 0,
      editing: null,
      deleting: null,
      loading: false,
      refreshing: false,
      saving: false,
      uncertain: false,
      error: '',
      request: 0,
      identities: [],
      currentUser: '',
      refreshError: '',
      timelinePositions: {},
      timelineContext: '',
      taskMode: !!this.dockTarget,
      editor: null,
      selectedTask: '',
      noteTarget: '',
      history: [],
      taskDrafts: {},
      taskEditing: false,
      taskExpanded: true,
      mobileTaskExpanded: false,
      taskPreferences: {},
      taskUncertain: false,
      taskAction: '',
      taskAssignee: '',
      taskActionRevision: '',
      relatedTrail: []
    };
  },
  computed: {
    mobile() {
      return mobile.value;
    },
    docked() {
      return !!this.dockTarget && this.taskMode;
    },
    displayedTaskExpanded() {
      return mobile.value
        ? this.taskEditing || this.mobileTaskExpanded
        : this.taskExpanded;
    },
    validContext() {
      return (
        this.alive &&
        this.context?.ticket === this.ticket &&
        this.context?.project === this.project
      );
    },
    draftKey() {
      return JSON.stringify([
        this.ticket,
        this.project,
        this.target?.__search_key__,
        this.process,
        this.contexts,
        this.taskMode ? this.selectedTask : ''
      ]);
    },
    draftStorageKey() {
      return (
        'tactic_stream.notes.' +
        this.currentUser +
        '.' +
        JSON.stringify(JSON.parse(this.draftKey).slice(1))
      );
    },
    taskPreferenceKey() {
      return JSON.stringify([
        this.ticket,
        this.project,
        this.target?.__search_key__,
        this.process
      ]);
    },
    draft() {
      return this.drafts[this.draftKey] || { body: '', files: [], reply: null };
    },
    taskDraft() {
      return this.taskDrafts[this.draftKey]?.data || this.editor?.task || {};
    },
    taskDirty() {
      return (
        JSON.stringify(this.taskDraft) !==
        JSON.stringify(
          this.taskDrafts[this.draftKey]?.baseline || this.editor?.task || {}
        )
      );
    },
    hasNoteDraft() {
      return !!(this.draft.body || this.draft.files.length || this.draft.reply);
    },
    isProgress() {
      return this.taskMode && this.editor?.process_type === 'progress';
    },
    processes() {
      return this.taskMode
        ? this.editor?.processes || []
        : [
            ...new Set([
              'publish',
              this.process,
              ...this.configuredProcesses.map((item) => item.process),
              ...this.notes.map((note) => note.process)
            ])
          ]
            .filter(Boolean)
            .map((value) => ({
              value,
              label:
                this.configuredProcesses.find((item) => item.process === value)
                  ?.label || value
            }));
    },
    timeline() {
      const children = new Map(),
        records = [];
      for (const note of this.notes.filter(
        (note) => note.process === this.process
      )) {
        const parent = Number(note.parent_id || 0);
        if (!children.has(parent)) children.set(parent, []);
        children.get(parent).push(note);
      }
      const append = (parent, depth) => {
        // shortcut: cap malformed/deep imported threads; add iterative traversal if real threads exceed 50 levels.
        if (depth > 50) return;
        for (const note of (children.get(parent) || []).sort(
          (a, b) =>
            String(a.timestamp).localeCompare(String(b.timestamp)) ||
            a.id - b.id
        )) {
          records.push({ ...note, depth });
          append(Number(note.id), depth + 1);
        }
      };
      append(0, 0);
      if (this.taskMode)
        return [...records, ...this.history].sort(
          (a, b) =>
            String(a.timestamp).localeCompare(String(b.timestamp)) ||
            a.id - b.id
        );
      return records;
    }
  },
  watch: {
    draftKey() {
      this.releaseNotePreviews();
    },
    updates(batch) {
      if (!batch || batch.projectCode !== this.project) return;
      const changes = [
        ...(batch.cacheChanges || []),
        ...(batch.cacheRetired || [])
      ];
      if (
        batch.initialActivity ||
        batch.reconnected ||
        batch.activity?.length ||
        changes.some((row) =>
          [
            'sthpw/note',
            'sthpw/task',
            'sthpw/work_hour',
            'sthpw/snapshot'
          ].includes(row.searchType)
        )
      )
        this.refresh();
    },
    ticket() {
      this.close(true);
      this.currentUser = '';
      this.drafts = {};
      this.taskDrafts = {};
      this.taskPreferences = {};
      this.timelinePositions = {};
    },
    project() {
      this.close(true);
    },
    searchType() {
      this.close(true);
    },
    'draft.body'() {
      this.saveNoteDraft();
    },
    process() {
      this.editing = this.deleting = null;
      this.ensureDraft();
      if (this.taskMode && this.opened && !this.loading) {
        this.selectedTask = this.taskPreferences[this.taskPreferenceKey] || '';
        this.load();
      }
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
  },
  beforeUnmount() {
    this.saveNoteDraft();
    this.releaseNotePreviews();
    this.alive = false;
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    timestampLabel,
    noteAction(note, event, source) {
      if (event.type === 'profile') this.openUserProfile?.(event.login);
      else if (event.type === 'reply') this.reply(note);
      else if (event.type === 'menu') {
        const ref = this.$refs['noteMenu' + note.id],
          menu = Array.isArray(ref) ? ref[0] : ref;
        if (menu?.open) menu.close();
        else if (menu && source) {
          const box = source.getBoundingClientRect();
          menu.openAt({
            clientX: box.left,
            clientY: box.bottom + 6,
            target: source
          });
        }
      }
    },
    mobileBack() {
      if (this.docked) this.$emit('back');
      else this.close();
    },
    noteAttachments(note) {
      const attachments = note.attachments || [];
      const originals = attachments.filter(
        (file) => !['icon', 'web'].includes(file.type)
      );
      const previews = attachments.filter((file) => file.type === 'web');
      return (
        originals.length
          ? originals
          : previews.length
            ? previews
            : attachments.filter((file) => file.type === 'icon')
      ).map((file) => {
        const image = /\.(png|jpg|jpeg|gif|webp|bmp|avif)$/i.test(
          file.filename
        );
        const web = attachments.find(
          (row) => row.snapshot_key === file.snapshot_key && row.type === 'web'
        );
        return {
          ...file,
          extension: file.filename.split('.').at(-1),
          previewUrl: image ? web?.href || file.href : '',
          sizeText:
            file.size == null
              ? ''
              : Number(file.size).toLocaleString() + ' ' + t('bytes')
        };
      });
    },
    async focusNote(searchKey) {
      const address = new URL(
        searchKey.startsWith('skey://') ? searchKey : 'skey://' + searchKey
      );
      const note = this.notes.find((row) => {
        const key = row.__search_key__ || row.search_key || '';
        const params = key
          ? new URL(key.startsWith('skey://') ? key : 'skey://' + key)
              .searchParams
          : null;
        return (
          key === searchKey ||
          (address.searchParams.has('code') &&
            (row.code || params?.get('code')) ===
              address.searchParams.get('code')) ||
          (address.searchParams.has('id') &&
            String(row.id) === address.searchParams.get('id'))
        );
      });
      await nextTick();
      const article =
        note &&
        this.$refs.timeline?.querySelector(
          '[data-note-kind="note"][data-note-id="' +
            CSS.escape(String(note.id)) +
            '"]'
        );
      if (!article) return false;
      article.scrollIntoView({ block: 'center' });
      article.focus({ preventScroll: true });
      return true;
    },
    openNoteLink(value) {
      if (this.openObjectTab) {
        this.close();
        this.openObjectTab(value, this.project).catch((error) => {
          this.error = error.message;
        });
      } else this.$emit('open-link', value);
    },
    async copyNote(note) {
      try {
        await copyText('skey://' + note.search_key);
      } catch (error) {
        this.error = error.message;
      }
    },
    rememberTimeline() {
      if (this.timelineContext && this.$refs.timeline?.getClientRects().length)
        this.timelinePositions[this.timelineContext] =
          this.$refs.timeline.scrollTop;
      const keys = Object.keys(this.timelinePositions);
      if (keys.length > 24) delete this.timelinePositions[keys[0]];
    },
    identity(login) {
      return (
        this.identities.find((user) => user.login === login) || {
          login,
          displayName: login || t('Removed user'),
          initials: (login || '?').slice(0, 2).toUpperCase()
        }
      );
    },
    statusAccent(note) {
      return (
        this.editor?.status_choices?.find((row) => row.value === note.after)
          ?.color || ''
      );
    },
    refresh() {
      if (
        !this.opened ||
        document.hidden ||
        (this.docked
          ? !this.active
          : document.activeElement?.closest('dialog') !== this.$refs.dialog) ||
        this.loading ||
        this.refreshing ||
        this.saving ||
        this.editing ||
        this.deleting ||
        this.taskAction ||
        this.uncertain ||
        this.taskUncertain ||
        !this.validContext
      )
        return;
      this.load(true);
    },
    beforeUnload(event) {
      if (
        this.saving ||
        this.uncertain ||
        this.taskUncertain ||
        Object.values(this.drafts).some(
          (draft) => draft.body || draft.files.length
        ) ||
        Object.values(this.taskDrafts).some(
          (draft) =>
            JSON.stringify(draft.data) !== JSON.stringify(draft.baseline)
        )
      ) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    ensureDraft() {
      if (!this.drafts[this.draftKey])
        this.drafts[this.draftKey] = {
          body: '',
          files: [],
          reply: null,
          restored: false
        };
      if (this.currentUser && !this.draft.restored) {
        try {
          this.draft.body = localStorage.getItem(this.draftStorageKey) || '';
          this.draft.restored = true;
        } catch {
          this.error = 'Local drafts could not be restored.';
        }
      }
    },
    saveNoteDraft() {
      if (!this.currentUser || !this.validContext || !this.draft.restored)
        return;
      try {
        if (this.draft.body)
          localStorage.setItem(this.draftStorageKey, this.draft.body);
        else localStorage.removeItem(this.draftStorageKey);
      } catch {
        this.error =
          'Drafts could not be saved in this browser. Keep this window open.';
      }
    },
    async command(name, values = {}, quiet = false) {
      if (!this.validContext)
        throw new Error('The context changed. Reopen the editor.');
      const result = await rpc(
        'execute_cmd',
        [
          this.context,
          'tactic.ui.widget.discussion_wdg.' + name,
          {
            search_key: this.noteTarget || this.target.__search_key__,
            ...values
          }
        ],
        {},
        quiet,
        quiet && name === 'DiscussionReadCmd'
      );
      return result.info;
    },
    async open(
      record,
      cell,
      process = '',
      taskMode = appearance.discussionView !== 'notes',
      taskKey = '',
      reveal = true
    ) {
      if (taskMode && this.openTaskInspector && !this.dockTarget) {
        const ticket = this.ticket,
          project = this.project;
        return this.openTaskInspector(record, cell, process, taskKey, {
          ticket,
          project,
          searchType: this.searchType,
          saved: () => {
            if (
              this.alive &&
              ticket === this.ticket &&
              project === this.project
            )
              this.$emit('saved');
          }
        });
      }
      const nextKey = cell.search_key || record.__search_key__,
        nextProcess =
          process || cell.process || cell.processes?.[0]?.process || 'publish';
      if (
        this.docked &&
        this.opened &&
        this.editor &&
        !this.loading &&
        this.validContext &&
        taskMode === this.taskMode &&
        nextProcess === this.process &&
        sameSearchKey(nextKey, this.target?.__search_key__, this.project) &&
        (!taskKey || sameSearchKey(taskKey, this.selectedTask, this.project)) &&
        JSON.stringify(cell.contexts || []) ===
          JSON.stringify(this.contexts || [])
      ) {
        this.show(reveal);
        return true;
      }
      if ((this.opened && !this.docked) || !this.canSwitchTarget())
        return false;
      this.saveNoteDraft();
      this.rememberTimeline();
      this.timelineContext = '';
      this.request++;
      this.releaseNotePreviews();
      this.taskMode = taskMode;
      this.selectedTask = taskKey;
      this.editor = null;
      this.history = [];
      this.noteTarget = '';
      this.taskEditing = false;
      this.relatedTrail = [];
      this.mobileTaskExpanded = false;
      this.context = { ticket: this.ticket, project: this.project };
      this.target = {
        ...record,
        __search_key__: cell.search_key || record.__search_key__
      };
      this.process =
        process || cell.process || cell.processes?.[0]?.process || 'publish';
      if (taskMode && !taskKey)
        this.selectedTask = this.taskPreferences[this.taskPreferenceKey] || '';
      this.contexts = cell.contexts || [];
      this.configuredProcesses = cell.processes || [];
      this.ensureDraft();
      this.notes = [];
      this.editing = this.deleting = null;
      this.error = '';
      this.uncertain = this.taskUncertain = false;
      this.opened = this.loading = true;
      await nextTick();
      if (!this.docked) this.$refs.dialog.show();
      if (reveal) this.$emit('visibility', true);
      await this.load();
      return true;
    },
    show(reveal = true) {
      this.opened = true;
      if (reveal) this.$emit('visibility', true);
    },
    canSwitchTarget() {
      if (this.saving) return false;
      if (this.editing || this.deleting || this.taskAction) {
        this.error =
          'Finish or cancel the current note or task action before changing the target.';
        return false;
      }
      return true;
    },
    openTask(record, cell, task = null) {
      return this.open(
        record,
        cell || {},
        task?.process || cell?.tasks?.[0]?.process || 'publish',
        true,
        task?.taskSearchKey || ''
      );
    },
    async taskCommand(values, quiet = false) {
      if (!this.validContext)
        throw new Error('The context changed. Reopen the editor.');
      const result = await rpc(
        'execute_cmd',
        [
          this.context,
          'tactic.ui.table.task_inspector.TaskInspectorCmd',
          {
            search_key: this.target.__search_key__,
            process: this.process,
            task_key: this.selectedTask,
            ...values
          }
        ],
        {},
        quiet,
        quiet && values.action === 'read'
      );
      return result.info;
    },
    chooseTask(value) {
      if (this.saving || this.loading) return;
      this.selectedTask = value;
      this.taskEditing = false;
      this.load();
    },
    openRelatedTask(item) {
      if (this.saving || this.loading || this.taskUncertain || this.uncertain)
        return;
      this.relatedTrail.push({
        target: this.target,
        process: this.process,
        contexts: this.contexts,
        selectedTask: this.selectedTask
      });
      this.target = {
        __search_key__: item.parent_key,
        title: item.parent_title
      };
      this.process = item.process;
      this.contexts = [];
      this.selectedTask = item.task_key;
      this.taskEditing = false;
      this.noteTarget = '';
      this.ensureDraft();
      this.load();
    },
    returnRelated() {
      if (this.saving || this.loading || !this.relatedTrail.length) return;
      Object.assign(this, this.relatedTrail.pop());
      this.taskEditing = false;
      this.noteTarget = '';
      this.ensureDraft();
      this.load();
    },
    editTaskForm() {
      if (
        this.saving ||
        this.loading ||
        this.taskUncertain ||
        this.taskDirty ||
        !this.editor?.selected_task
      )
        return;
      this.$refs.taskForm.open(this.editor.selected_task);
    },
    editTask() {
      if (!this.editor || this.saving || this.isProgress) return;
      if (!this.taskDrafts[this.draftKey])
        this.taskDrafts[this.draftKey] = {
          data: { ...this.editor.task },
          baseline: { ...this.editor.task },
          revision: this.editor.revision
        };
      this.taskDrafts[this.draftKey].full = true;
      this.taskEditing = true;
      if (mobile.value) this.mobileTaskExpanded = true;
      else this.taskExpanded = true;
      this.taskAction = '';
    },
    stageTask(name, value) {
      if (
        this.saving ||
        this.loading ||
        this.taskUncertain ||
        !this.editor?.fields.some(
          (field) => field.name === name && field.editable
        )
      )
        return;
      if (!this.taskDrafts[this.draftKey])
        this.taskDrafts[this.draftKey] = {
          data: { ...this.editor.task },
          baseline: { ...this.editor.task },
          revision: this.editor.revision
        };
      this.taskDrafts[this.draftKey].data[name] = value;
    },
    requestTaskAction(action) {
      if (
        this.saving ||
        this.loading ||
        this.taskEditing ||
        this.taskUncertain ||
        this.isProgress
      )
        return;
      if (action === 'delete' && this.hasNoteDraft) {
        this.error = 'Send or clear the note draft before deleting this task.';
        return;
      }
      this.error = '';
      this.taskAction = action;
      this.taskAssignee = '';
      this.taskActionRevision = this.editor.revision;
    },
    async confirmTaskAction() {
      if (!this.taskAction || this.saving || this.loading || this.taskUncertain)
        return;
      if (this.taskAction === 'delete' && this.hasNoteDraft) {
        this.error = 'Send or clear the note draft before deleting this task.';
        return;
      }
      this.saving = true;
      this.error = '';
      try {
        const result = await this.taskCommand({
          action: this.taskAction,
          assigned: this.taskAssignee,
          expected_revision: this.taskActionRevision
        });
        if (!this.validContext) return;
        delete this.taskDrafts[this.draftKey];
        this.selectedTask = result.task_key;
        this.taskAction = '';
        this.$emit('saved');
        await this.load();
      } catch (error) {
        if (this.validContext) {
          this.error = error.message;
          this.taskUncertain = !error.status || error.status >= 500;
        }
      } finally {
        this.saving = false;
      }
    },
    toggleTask() {
      if (mobile.value) {
        this.mobileTaskExpanded = !this.mobileTaskExpanded;
        return;
      }
      this.taskExpanded = !this.taskExpanded;
      localStorage.setItem(
        'tactic_stream.taskExpanded.' + this.editor.current_user,
        JSON.stringify(this.taskExpanded)
      );
    },
    discardTask() {
      delete this.taskDrafts[this.draftKey];
      this.taskEditing = false;
    },
    async saveTask() {
      if (this.saving || this.loading || this.taskUncertain) return;
      if (!this.taskDrafts[this.draftKey] && !this.editor.selected_task)
        this.stageTask('status', this.editor.task.status);
      const draft = this.taskDrafts[this.draftKey];
      if (!draft) return;
      this.saving = true;
      this.error = '';
      try {
        const data = Object.fromEntries(
          this.editor.fields
            .filter(
              (field) =>
                field.editable &&
                draft.data[field.name] !== draft.baseline[field.name]
            )
            .map((field) => [field.name, draft.data[field.name]])
        );
        const result = await this.taskCommand({
          action: 'save',
          data,
          expected_revision: draft.revision
        });
        if (!this.validContext) return;
        delete this.taskDrafts[this.draftKey];
        this.taskEditing = false;
        this.selectedTask = result.task_key;
        this.$emit('saved');
        await this.load();
      } catch (error) {
        if (this.validContext) {
          this.error = error.message;
          this.taskUncertain = !error.status || error.status >= 500;
        }
      } finally {
        this.saving = false;
      }
    },
    createTask() {
      if (!this.isProgress && !this.taskDirty && !this.taskUncertain)
        this.$refs.taskForm.open(null, null, {
          parent_key: this.target.__search_key__,
          default: this.editor.defaults
        });
    },
    taskCreated() {
      if (!this.taskDirty) delete this.taskDrafts[this.draftKey];
      this.taskEditing = false;
      this.$emit('saved');
      this.load();
    },
    previewObject() {
      const object = this.editor?.object;
      if (object)
        this.$refs.preview.open(object.record, { ...object.preview, object });
    },
    openHours(log = false) {
      this.$refs.hours.open(
        {
          scope: {
            search_key: this.target.__search_key__,
            process: this.process,
            task_key: this.selectedTask
          },
          users: this.editor.users
        },
        log,
        !log
      );
    },
    async load(quiet = false) {
      quiet = quiet === true; // Vue click passes a MouseEvent.
      const id = ++this.request;
      const timeline = this.$refs.timeline;
      this.rememberTimeline();
      const follow =
        timeline &&
        timeline.scrollHeight - timeline.clientHeight - timeline.scrollTop < 24;
      this.refreshing = quiet;
      if (!quiet) this.loading = true;
      if (!quiet) {
        this.error = '';
        this.taskAction = '';
      }
      try {
        const result = this.taskMode
          ? await this.taskCommand({ action: 'read' }, quiet)
          : await this.command(
              'DiscussionReadCmd',
              { context: this.contexts },
              quiet
            );
        if (id === this.request && this.validContext) {
          this.currentUser = result.current_user;
          if (this.taskMode) {
            this.editor = result;
            this.target.__search_key__ = result.search_key;
            this.selectedTask = result.selected_task;
            this.noteTarget = result.note_target;
            this.history = result.history;
            this.taskPreferences[this.taskPreferenceKey] = result.selected_task;
            if (!quiet) this.taskUncertain = false;
            const expanded = localStorage.getItem(
              'tactic_stream.taskExpanded.' + result.current_user
            );
            this.taskExpanded =
              expanded === null
                ? preferences.tasks.inspectorExpanded
                : expanded !== 'false';
            this.taskEditing = !!this.taskDrafts[this.draftKey]?.full;
          }
          this.ensureDraft();
          this.notes = result.notes;

          this.identities = result.identities || [];
          this.refreshError = '';
          if (!quiet) this.uncertain = false;
          const key = JSON.stringify([
            this.context.ticket,
            this.context.project,
            this.target.__search_key__,
            this.process,
            this.selectedTask
          ]);
          const changedContext = key !== this.timelineContext;
          this.timelineContext = key;
          await nextTick();
          if (id === this.request && this.validContext)
            this.loadNotePreviews(
              result.notes.flatMap((note) => extractSkeys(note.body))
            );
          if (
            id === this.request &&
            this.$refs.timeline &&
            (changedContext || (quiet && follow))
          )
            this.$refs.timeline.scrollTop = changedContext
              ? (this.timelinePositions[key] ??
                this.$refs.timeline.scrollHeight)
              : this.$refs.timeline.scrollHeight;
        }
      } catch (error) {
        if (id === this.request && this.validContext) {
          if (quiet) this.refreshError = error.message;
          else this.error = error.message;
        }
      } finally {
        if (id === this.request) {
          this.loading = false;
          this.refreshing = false;
        }
      }
    },
    close(force = false) {
      if (this.saving && force !== true) return;
      if (force === true) {
        this.editing = this.deleting = null;
        this.releaseNotePreviews();
      } else if (this.editing || this.deleting) {
        this.error =
          'Finish or cancel the current note or task action before changing the target.';
        return;
      }
      this.saveNoteDraft();
      this.rememberTimeline();
      this.request++;
      this.loading = false;
      this.refreshing = false;
      this.$refs.preview?.close();
      this.$refs.hours?.close(true);
      this.opened = false;
      if (this.docked) {
        if (force === true) {
          this.target = this.editor = this.context = null;
          this.notes = [];
          this.history = [];
        } else this.$emit('visibility', false);
      } else this.$refs.dialog?.close();
    },
    attach(files) {
      if (this.saving || this.loading || this.uncertain) return;
      for (const file of files)
        this.draft.files.push({ file, name: file.name, uploaded: '' });
      this.$refs.files.value = '';
    },
    async pasteFiles() {
      const key = this.draftKey;
      try {
        const files = await readClipboardImages();
        if (this.validContext && this.opened && key === this.draftKey)
          this.attach(files);
      } catch {
        this.error =
          'Clipboard access is unavailable. Paste an image into the reply field or choose a file.';
      }
    },
    async reply(note) {
      this.draft.reply = note;
      await nextTick();
      this.$refs.body.focus();
    },
    async send() {
      if (
        this.loading ||
        this.saving ||
        this.uncertain ||
        (this.taskMode && !this.editor) ||
        (!this.draft.body.trim() && !this.draft.files.length)
      )
        return;
      this.saving = true;
      this.error = '';
      const draft = this.draft;
      let submitted = false;
      try {
        const names = new Set();
        for (const attachment of draft.files) {
          if (names.has(attachment.name))
            throw new Error('Attachment names must be unique');
          names.add(attachment.name);
          if (!this.validContext)
            throw new Error('The context changed. Reopen the editor.');
          if (!attachment.uploaded)
            attachment.uploaded = await uploadFormFile(
              this.context.ticket,
              this.context.project,
              attachment.file
            );
        }
        submitted = true;
        await this.command('DiscussionAddNoteCmd', {
          note: draft.body,
          process: this.process,
          search_key:
            draft.reply?.target_key ||
            this.noteTarget ||
            this.target.__search_key__,
          context: this.contexts[0] || this.process,
          parent_id: draft.reply?.id || 0,
          files: draft.files.map((file) => file.uploaded)
        });
        draft.body = '';
        draft.files = [];
        draft.reply = null;
        if (!this.validContext) return;
        this.$emit('saved');
        await this.load();
        await nextTick();
        this.$refs.timeline?.scrollTo({
          top: this.$refs.timeline.scrollHeight,
          behavior: 'smooth'
        });
      } catch (error) {
        this.error = error.message;
        this.uncertain = submitted && (!error.status || error.status >= 500);
      } finally {
        this.saving = false;
      }
    },
    async change(note, action) {
      if (
        this.saving ||
        this.uncertain ||
        !this.validContext ||
        !note.can_change
      )
        return;
      const generation = this.request;
      this.saving = true;
      this.error = '';
      try {
        await this.command('DiscussionChangeNoteCmd', {
          id: note.id,
          action,
          body: this.editing?.body || '',
          expected_revision: note.revision,
          search_key:
            note.target_key || this.noteTarget || this.target.__search_key__
        });
        if (!this.validContext || generation !== this.request) return;
        this.editing = this.deleting = null;
        this.$emit('saved');
        await this.load();
      } catch (error) {
        if (generation !== this.request || !this.validContext) return;
        this.uncertain = !error.status || error.status >= 500;
        this.error =
          error.message +
          (this.uncertain
            ? '\n' +
              t(
                'The result is unknown. Refresh and check the note before trying again.'
              )
            : '');
      } finally {
        this.saving = false;
      }
    },
    releaseNotePreviews() {
      this.previewRequest++;
      for (const url of Object.values(this.previewUrls))
        URL.revokeObjectURL(url);
      this.previewUrls = {};
      this.notePreviews = {};
    },
    async copyPreviewKey(key) {
      try {
        await copyText(key);
      } catch (error) {
        this.error = error.message;
      }
    },
    async loadNotePreviews(keys, retry = false) {
      const generation = this.previewRequest,
        ticket = this.ticket,
        project = this.project;
      const missing = [...new Set(keys)].filter(
        (key) => retry || !this.notePreviews[key]
      );
      for (const key of missing) this.notePreviews[key] = skeyPlaceholder(key);
      for (let start = 0; start < missing.length; start += 50) {
        const batch = missing.slice(start, start + 50);
        try {
          const result = await linkPreviews(ticket, project, batch);
          if (!this.validContext || generation !== this.previewRequest) return;
          for (const preview of result.previews) {
            this.notePreviews[preview.searchKey] = preview;
            for (const nested of preview.nestedPreviews || [])
              this.notePreviews[nested.searchKey] = nested;
            const attachment = preview.privateAttachment;
            const files = attachment?.snapshot.__files__ || [];
            const file =
              files.find((row) => row.type === 'web') ||
              files.find((row) => row.type === 'icon');
            if (file) {
              const blob = await messageFileRequest(ticket, project, {
                message_code: attachment.chat,
                snapshot_code: attachment.snapshot.code,
                file_code: file.code
              });
              if (!this.validContext || generation !== this.previewRequest)
                return;
              const previous = this.previewUrls[preview.searchKey];
              if (previous) URL.revokeObjectURL(previous);
              const url = URL.createObjectURL(blob);
              this.previewUrls[preview.searchKey] = url;
              this.notePreviews[preview.searchKey].previewUrl = url;
            }
          }
        } catch (error) {
          if (!this.validContext || generation !== this.previewRequest) return;
          for (const key of batch)
            this.notePreviews[key] = skeyPlaceholder(key, 'error');
        }
      }
    },
    preview(note, file) {
      const image = /\.(png|jpg|jpeg|gif|webp|bmp|avif)$/i.test(file.filename)
        ? file.href
        : '';
      this.$refs.preview.open(
        { title: file.filename, __search_key__: note.search_key },
        { image, files: [file], context: note.context, loadFile: fileBlob }
      );
    }
  }
};
</script>

<template>
  <Teleport defer :to="docked ? dockTarget : 'body'">
    <component
      :is="docked ? 'section' : 'dialog'"
      v-window="docked ? false : { type: 'window' }"
      ref="dialog"
      :open="docked ? opened : undefined"
      @close="
        opened = false;
        $emit('visibility', false);
      "
      class="record-dialog notes-panel"
      :class="{ 'notes-panel-docked': docked }"
      :role="docked ? 'region' : undefined"
      :aria-label="t(taskMode ? 'Task Inspector' : 'Notes')"
      :aria-busy="loading || saving"
      @cancel.prevent="close"
      @dragover.prevent
      @drop.prevent="attach($event.dataTransfer.files)"
    >
      <header v-if="!docked && !mobile" class="inspector-window-header">
        <AppIcon name="comment" />
        <h2>{{ t(taskMode ? 'Task Inspector' : 'Notes') }}</h2>
        <AppButton
          icon-only
          label="Help"
          icon="help"
          @click="openHelp('dock.notes')"
        /><AppButton
          label="Close notes"
          icon="close"
          icon-only
          :disabled="saving"
          autofocus
          @click="close"
        />
      </header>
      <p v-if="!target" class="muted notes-empty">
        {{ t('Select an sObject') }}
      </p>
      <template v-else>
        <p v-if="error" class="error" role="alert">
          {{ t(error) }}
          <AppButton
            v-if="taskMode && !editor && !loading"
            label="Retry"
            icon="refresh"
            :disabled="saving"
            @click="load()"
          />
        </p>
        <p v-if="refreshError" class="notice" role="status">
          {{ t('Automatic refresh failed. Use Refresh to retry.') }}
          {{ t(refreshError) }}
        </p>
        <p v-if="uncertain" class="notice">
          {{
            t(
              'Refresh and check the timeline before retrying. The server may have saved the note.'
            )
          }}
        </p>
        <p v-if="taskUncertain" class="notice">
          {{
            t(
              'Refresh and check the task before retrying. The server may have saved the changes.'
            )
          }}
        </p>
        <AppButton
          v-if="relatedTrail.length"
          label="Back to related tasks"
          icon="MDI_CHEVRON_LEFT"
          :disabled="saving || loading"
          @click="returnRelated"
        />
        <TaskInspectorHeader
          v-if="taskMode && editor?.object"
          :editor="editor"
          :process="process"
          :expanded="displayedTaskExpanded"
          :busy="saving || loading"
          :editing="taskEditing"
          @back="mobileBack"
          @help="openHelp('dock.notes')"
          @preview="previewObject"
          @toggle="toggleTask"
          @process="process = $event"
          @task="chooseTask"
          @refresh="load"
          @edit="editTask"
          @create="createTask"
          @action="requestTaskAction"
          @log="openHours(true)"
          @timesheet="openHours()"
        />
        <label v-else
          >{{ t('Process')
          }}<AppSelect
            v-model="process"
            :options="processes"
            label="Process"
            :translate-labels="false"
            :disabled="saving || loading"
        /></label>
        <RelatedTasks
          v-if="isProgress && displayedTaskExpanded"
          :related="editor.related"
          :accent="processes.find((row) => row.value === process)?.color"
          :busy="saving || loading || taskUncertain || uncertain"
          @open="openRelatedTask"
        />
        <WorkHoursSummary
          v-if="!isProgress && editor?.work_hours"
          :summary="editor.work_hours.summary"
          :has-task="!!editor.selected_task"
          :expanded="displayedTaskExpanded"
          :busy="saving || loading || taskUncertain"
          @log="openHours(true)"
          @timesheet="openHours()"
        />
        <TaskDetails
          v-if="!isProgress && taskMode && editor"
          :editor="editor"
          :draft="taskDraft"
          :expanded="displayedTaskExpanded"
          :editing="taskEditing"
          :busy="saving || loading || taskUncertain"
          :dirty="taskDirty"
          :pending-action="taskAction"
          :assignee="taskAssignee"
          @action="requestTaskAction"
          @confirm-action="confirmTaskAction"
          @cancel-action="taskAction = ''"
          @assignee="taskAssignee = $event"
          :process-title="
            processes.find((row) => row.value === process)?.label || process
          "
          @toggle="toggleTask"
          @edit="editTask"
          @full-edit="editTaskForm"
          @discard="discardTask"
          @save="saveTask"
          @create="createTask"
          @change="stageTask"
        />
        <div ref="timeline" class="notes-timeline" @scroll="rememberTimeline">
          <p v-if="loading && !timeline.length" role="status">
            {{ t('Loading data…') }}
          </p>
          <p v-else-if="!timeline.length" class="muted notes-empty">
            {{ t(taskMode ? 'No notes for this process' : 'No notes yet') }}
          </p>
          <NoteEntry
            v-for="note in timeline"
            :key="`${note.entry_type || 'note'}-${note.id}`"
            :class="{ 'note-reply': !!note.parent_id }"
            :data-note-id="note.id"
            :data-note-kind="note.entry_type || 'note'"
            tabindex="-1"
            :model="{
              status: note.entry_type === 'status',
              own: note.login === (editor?.current_user || currentUser),
              author: note.login,
              authorLabel: identity(note.login).displayName,
              avatarUrl: identity(note.login).avatarUrl,
              initials: identity(note.login).initials,
              authorColor: identity(note.login).avatarColor,
              statusColor: statusAccent(note),
              time: timestampLabel(note.timestamp),
              fullTime: note.timestamp,
              busy: saving,
              reply: true
            }"
            @event="(event, source) => noteAction(note, event, source)"
          >
            <template #menu
              ><AppMenu
                :ref="'noteMenu' + note.id"
                external-trigger
                label="Note actions"
                overlay
                ><AppButton
                  label="Copy sKey"
                  icon="copy"
                  @click="copyNote(note)" /><AppButton
                  v-if="note.can_change"
                  label="Edit note"
                  icon="edit"
                  :disabled="saving"
                  @click="editing = { note, body: note.body }" /><AppButton
                  v-if="note.can_change"
                  label="Delete note"
                  icon="delete"
                  destructive
                  :disabled="saving"
                  @click="deleting = note" /></AppMenu
            ></template>
            <NoteBody
              :note="note"
              :files="noteAttachments(note)"
              :previews="notePreviews"
              :status-color="statusAccent(note)"
              @link="openNoteLink"
              @retry="loadNotePreviews([$event], true)"
              @copy="copyPreviewKey"
              @file="preview(note, $event)"
            />
            <template v-if="note.entry_type !== 'status'">
              <details v-if="note.metadata?.editHistory?.length">
                <summary>{{ t('Edit history') }}</summary>
                <div
                  v-for="(entry, index) in note.metadata.editHistory"
                  :key="index"
                >
                  <small>{{ entry.editedBy }} · {{ entry.editedAt }}</small>
                  <p class="note-body">{{ entry.body }}</p>
                </div>
              </details>
            </template>
          </NoteEntry>
        </div>
        <NoteDialogs
          :active="opened && (!docked || active)"
          :editing="editing"
          :deleting="deleting"
          :busy="saving"
          :uncertain="uncertain"
          :error="editing || deleting ? error : ''"
          @text="editing.body = $event"
          @cancel="editing = deleting = null"
          @save="change(editing.note, 'edit')"
          @delete="change(deleting, 'delete')"
        />
        <form class="note-composer" @submit.prevent="send">
          <p v-if="draft.reply">
            {{ t('Reply to') }} {{ draft.reply.login }}: {{ draft.reply.body }}
            <AppButton
              label="Cancel reply"
              icon="close"
              icon-only
              :disabled="saving"
              @click="draft.reply = null"
            />
          </p>
          <div
            v-for="(file, index) in draft.files"
            :key="index"
            class="note-attachment"
          >
            <span>{{ file.name }}</span
            ><AppButton
              label="Remove attachment"
              icon="close"
              icon-only
              :disabled="saving"
              @click="draft.files.splice(index, 1)"
            />
          </div>
          <footer>
            <input
              ref="files"
              type="file"
              multiple
              hidden
              @change="attach($event.target.files)"
            /><AppButton
              icon-only
              label="Attach files"
              icon="MDI_PAPERCLIP"
              :disabled="saving || loading || uncertain"
              @click="$refs.files.click()"
            /><AppButton
              v-if="!mobile"
              icon-only
              label="Attach image from clipboard"
              icon="MDI_CONTENT_PASTE"
              :disabled="saving || loading || uncertain"
              @click="pasteFiles"
            /><MessageComposer
              ref="body"
              v-model="draft.body"
              label="Note text"
              send-label="Send note"
              :members="[]"
              :sending="saving"
              :disabled="loading || uncertain || (taskMode && !editor)"
              :has-attachments="!!draft.files.length"
              @submit="send"
              @files="attach"
            />
          </footer>
        </form>
      </template>
      <footer
        v-if="mobile && (!taskMode || !editor?.object)"
        class="inspector-mobile-navigation"
      >
        <AppButton
          label="Back"
          icon="MDI_ARROW_LEFT"
          icon-only
          @click="mobileBack"
        /><strong>{{ t(taskMode ? 'Task Inspector' : 'Notes') }}</strong
        ><AppButton
          label="Help"
          icon="help"
          icon-only
          @click="openHelp('dock.notes')"
        />
      </footer>
    </component>
  </Teleport>
  <Teleport to="body">
    <FilePreview
      ref="preview"
      :ticket="ticket"
      :project="project"
      :search-type="searchType"
    />
    <RecordForm
      ref="taskForm"
      :ticket="ticket"
      :project="project"
      search-type="sthpw/task"
      @saved="taskCreated"
    />
    <Timesheet
      ref="hours"
      :ticket="ticket"
      :project="project"
      :current-user="editor?.current_user"
      @saved="
        $emit('saved');
        load();
      "
    />
  </Teleport>
</template>

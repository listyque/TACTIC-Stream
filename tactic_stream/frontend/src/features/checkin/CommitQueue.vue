<script>
// Handler CommitQueueView.qml / commit_queue.py: one application-owned preparation queue.
import { nextTick, markRaw } from 'vue';
import { rpc, uploadFormFile } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import QueueWorkspace from './queue/QueueWorkspace.vue';
import QueueDialogs from './queue/QueueDialogs.vue';
import * as Presentation from './queue/state.js';
import { editable } from './queue/state.js';
import QueueActions from './queue/actions.js';
import QueueFiles from './queue/files.js';
import QueueRecovery from './queue/recovery.js';
import { asyncComponent } from '../../controls/asyncComponent.js';
import { mobile } from '../../mobile.js';
import { notify } from '../activity/notifications.js';
import {
  preferences,
  savePreferencePage
} from '../configuration/preferences.js';
import { repositories, sourcePath, descriptors } from './files.js';

const NamingEditor = asyncComponent(
  () => import('../administration/NamingEditor.vue')
);
export default {
  components: {
    AppButton,
    QueueWorkspace,
    QueueDialogs,
    NamingEditor
  },
  props: {
    inline: Boolean,
    login: String,
    ticket: String,
    project: String,
    canAdminister: Boolean,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['changed', 'completed', 'opened', 'closed', 'help', 'snapshot'],
  data() {
    return {
      jobs: [],
      selectedId: '',
      running: false,
      modal: false,
      sequence: 0,
      applyChecked: false,
      advanced: false,
      mobileDetails: false,
      namingExpanded: false,
      width: 0,
      filesHeight: 142,
      duplicate: null,
      duplicates: [],
      repositoryOptions: [],
      cancelRequested: false,
      aborter: null,
      validation: 0,
      sessionEpoch: 0,
      disposed: false,
      namingScope: null,
      contextEditing: false,
      contextBranch: '',
      versionDraft: null,
      versionError: '',
      filenameDraft: null,
      descriptionDraft: null,
      previewPickerId: '',
      sourcePickerId: '',
      queueSize: { width: 1000, height: 700 },
      error: '',
      preferences
    };
  },
  computed: {
    sessionKey() {
      return JSON.stringify([this.login, this.ticket]);
    },
    frameOperations() {
      return this.jobs.map((job) => Presentation.record(job, this));
    },
    frameFiles() {
      return Presentation.sourceFiles(this.selected, this.canEdit);
    },
    framePreviews() {
      return Presentation.previewFiles(this.jobs);
    },
    frameModel() {
      return Presentation.model(this, this.frameOperations, this.frameFiles);
    },
    previewRows() {
      return (this.selected?.previews || []).map((file, index) => ({
        key: 'preview_' + index,
        index,
        title: file.name,
        operationId: String(this.selectedId),
        sourceKey: this.selectedId + ':preview:' + index,
        source: '',
        canRemove: this.canEdit
      }));
    },
    mobile() {
      return mobile.value;
    },
    docked() {
      return this.inline && !this.modal;
    },
    selected() {
      return this.jobs.find((job) => job.id === this.selectedId);
    },
    pending() {
      return this.jobs.some((job) => job.file);
    },
    canEdit() {
      return !this.running && editable(this.selected) && !!this.selected?.file;
    }
  },
  mounted() {
    this.restore();
    window.addEventListener('beforeunload', this.beforeUnload);
  },
  beforeUnmount() {
    this.disposed = true;
    this.sessionEpoch++;
    this.validation++;
    this.aborter?.abort();
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  watch: {
    selectedId() {
      this.contextEditing = false;
      this.versionDraft = this.filenameDraft = this.descriptionDraft = null;
      this.versionError = '';
    },
    sessionKey(value, previous) {
      this.sessionEpoch++;
      this.validation++;
      this.aborter?.abort();
      this.aborter = null;
      this.cancelRequested = true;
      this.running = false;
      this.$refs.auxiliary?.close();
      this.$refs.namingDialog?.close();
      this.duplicate = null;
      this.duplicates = [];
      if (JSON.parse(previous)[0] !== this.login) {
        this.jobs = [];
        this.restore();
      } else {
        for (const job of this.jobs) {
          job.request++;
          job.validating = false;
          job.ticket = this.ticket;
          if (job.status === 'Checking in') {
            job.status = 'Result unknown';
            job.error =
              'The session changed during check-in. Inspect Snapshot Browser before repeating it.';
          } else if (job.status === 'Uploading') job.status = 'Cancelled';
        }
        this.changed();
      }
    },
    presentationVisible(visible) {
      if (!visible) {
        this.$refs.auxiliary?.close();
        this.$refs.namingDialog?.close();
      }
    }
  },
  methods: {
    ownsJob(job, epoch = this.sessionEpoch) {
      return (
        !this.disposed && epoch === this.sessionEpoch && this.jobs.includes(job)
      );
    },
    t,
    editable,
    ...QueueActions,
    beforeUnload(event) {
      if (this.pending) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      return (
        !this.running &&
        (!this.pending || window.confirm(t('Discard pending file check-ins?')))
      );
    },
    async open() {
      if (!this.presentationVisible) return;
      const epoch = this.sessionEpoch;
      await nextTick();
      if (this.disposed || epoch !== this.sessionEpoch) return;
      this.modal =
        this.inline && !this.mobile && !!document.querySelector('dialog:modal');
      await nextTick();
      if (this.disposed || epoch !== this.sessionEpoch) return;
      if (!this.docked) this.$refs.dialog?.show();
      this.$emit('opened', this.docked);
    },
    ...QueueRecovery,
    enqueue(values, force = false) {
      const files = values.files || [values.file];
      if (
        !values.context &&
        this.jobs.some(
          (job) =>
            job.searchKey === values.searchKey &&
            job.file &&
            !['Complete', 'Cancelled'].includes(job.status)
        )
      )
        throw new Error(
          t('A preview check-in for this Search Type is already pending.')
        );
      const identity = (job) =>
        JSON.stringify([
          job.project,
          job.searchKey,
          job.context || 'icon',
          !!job.isRevision,
          Number(job.version || 0),
          (job.files?.length
            ? job.files.map(sourcePath)
            : (job.sourceFiles || []).map((file) => file.path)
          )
            .map((path) => path.toLowerCase())
            .sort()
        ]);
      const old = this.jobs.find(
        (job) => identity(job) === identity({ ...values, files })
      );
      if (old && !force) {
        const duplicate = { values, oldId: old.id };
        if (this.duplicate) this.duplicates.push(duplicate);
        else this.duplicate = duplicate;
        this.selectedId = old.id;
        return;
      }
      const job = {
        description: '',
        checked: true,
        context: 'publish',
        process: 'publish',
        repositoryAlias: preferences.repository.defaultAlias,
        keepFileName: preferences.checkin.keepFilename,
        generatePreviews: preferences.checkin.generatePreviews,
        updateVersionless: true,
        onlyVersionless: false,
        explicitFilename: '',
        contextAsFilename: false,
        previews: [],
        ...values,
        id: ++this.sequence,
        file: files[0],
        files: [...files],
        preview: !values.context,
        status: 'Queued',
        progress: 0,
        error: '',
        snapshot: null,
        plan: null,
        planError: '',
        validating: false,
        request: 0,
        sourceFiles: descriptors(files)
      };
      if (job.preview) {
        job.context = 'icon';
        job.process = 'icon';
        job.updateVersionless = false;
      }
      this.jobs.push(job);
      this.select(job, false);
      this.changed();
      this.validateAll();
    },
    resolveDuplicate(decision) {
      const pending = this.duplicate;
      const old = this.jobs.find((job) => job.id === pending.oldId);
      if (
        decision === 'replace' &&
        old &&
        !['Uploading', 'Checking in', 'Result unknown'].includes(old.status)
      ) {
        const index = this.jobs.indexOf(old);
        old.request++;
        this.enqueue(pending.values, true);
        const replacement = this.jobs.pop();
        replacement.id = old.id;
        replacement.checked = old.checked;
        this.jobs.splice(index, 1, replacement);
        this.selectedId = old.id;
        this.changed();
        this.validateAll();
      } else if (decision === 'add' || (decision === 'replace' && !old))
        this.enqueue(pending.values, true);
      this.duplicate = this.duplicates.shift() || null;
    },
    async select(job, details = true) {
      const epoch = this.sessionEpoch;
      if (this.queueSize.width < 700) this.mobileDetails = details;
      this.selectedId = job.id;
      this.error = '';
      this.contextEditing = false;
      this.versionDraft = this.filenameDraft = this.descriptionDraft = null;
      this.versionError = '';
      try {
        const result = await repositories({
          ticket: job.ticket,
          project: job.project
        });
        if (this.ownsJob(job, epoch) && this.selectedId === job.id)
          this.repositoryOptions = result;
      } catch (error) {
        if (this.ownsJob(job, epoch) && this.selectedId === job.id)
          this.error = error.message;
      }
    },
    async validateAll() {
      if (this.disposed || !this.ticket) return;
      const validation = ++this.validation;
      for (const job of [...this.jobs]) {
        if (validation !== this.validation) return;
        if (editable(job) && job.file) await this.validate(job);
      }
    },
    options(job, action) {
      return {
        action,
        search_key: job.searchKey,
        process: job.process,
        context: job.context,
        description: job.description,
        source_files: [...job.files, ...job.previews].map((file, index) => ({
          path:
            index < job.files.length
              ? sourcePath(file)
              : 'preview/' + sourcePath(file),
          size: file.size,
          file_type: index < job.files.length ? 'main' : 'preview'
        })),
        templates: job.templates,
        padding: job.padding,
        repository_alias: job.repositoryAlias,
        keep_file_name: !!job.keepFileName,
        is_revision: !!job.isRevision,
        version:
          job.version === '' || job.version == null
            ? null
            : Number(job.version),
        explicit_filename: job.explicitFilename || null,
        update_versionless: !!job.updateVersionless,
        only_versionless: !!job.onlyVersionless,
        create_icon: job.generatePreviews !== false
      };
    },
    async validate(job) {
      const epoch = this.sessionEpoch;
      if (!this.ownsJob(job, epoch)) return;
      if (job.ingest || job.preview) {
        job.planError = '';
        return;
      }
      const request = ++job.request;
      job.validating = true;
      job.planError = '';
      try {
        const reserved = this.jobs
          .slice(0, this.jobs.indexOf(job))
          .filter(
            (other) =>
              editable(other) &&
              other.plan &&
              other.searchKey === job.searchKey &&
              other.project === job.project &&
              other.context === job.context &&
              !other.onlyVersionless
          )
          .map((other) => other.plan.version);
        const result = (
          await rpc(
            'execute_cmd',
            [
              { ticket: job.ticket, project: job.project },
              'tactic.command.browser_checkin_cmd.BrowserCheckinCmd',
              { ...this.options(job, 'plan'), reserved_versions: reserved }
            ],
            {},
            true
          )
        ).info.plan;
        if (request === job.request && this.ownsJob(job, epoch))
          job.plan = result;
      } catch (error) {
        if (request === job.request && this.ownsJob(job, epoch)) {
          job.plan = null;
          job.planError = error.message;
        }
      } finally {
        if (request === job.request && this.ownsJob(job, epoch)) {
          job.validating = false;
          this.changed();
        }
      }
    },
    update(field, value) {
      if (!this.canEdit) return;
      for (const job of this.jobs.filter(
        (job) =>
          editable(job) &&
          !job.ingest &&
          (!job.preview || field === 'description') &&
          (job.id === this.selectedId || (this.applyChecked && job.checked))
      )) {
        job[field] = value;
        if (field === 'process') job.context = value;
        if (field === 'keepFileName' && value) job.updateVersionless = false;
        if (field === 'onlyVersionless' && value) job.updateVersionless = true;
        if (
          job.contextAsFilename &&
          ['context', 'contextAsFilename'].includes(field)
        )
          job.explicitFilename = job.context.split('/').slice(1).join('_');
      }
      this.changed();
      if (field !== 'description') this.validateAll();
    },
    remove(job) {
      if (['Uploading', 'Checking in'].includes(job.status)) return;
      job.request++;
      this.jobs = this.jobs.filter((item) => item !== job);
      if (!this.selected) this.selectedId = this.jobs[0]?.id || '';
      this.changed();
      this.validateAll();
    },
    clear(completed = false) {
      if (this.running) return;
      for (const job of [...this.jobs])
        if (!completed || job.status === 'Complete') this.remove(job);
    },
    move(offset) {
      const index = this.jobs.indexOf(this.selected),
        target = index + offset;
      if (this.running || index < 0 || target < 0 || target >= this.jobs.length)
        return;
      const [job] = this.jobs.splice(index, 1);
      this.jobs.splice(target, 0, job);
      this.changed();
      this.validateAll();
    },
    autoClean(value) {
      try {
        savePreferencePage('checkin', {
          ...preferences.checkin,
          commitQueueAutoClean: value
        });
      } catch (error) {
        this.error = error.message;
      }
    },
    beginContext() {
      if (
        !this.canEdit ||
        this.selected.isRevision ||
        this.selected.ingest ||
        this.selected.preview
      )
        return;
      this.contextBranch = this.selected.context.split('/').slice(1).join('/');
      this.contextEditing = true;
      nextTick(() =>
        this.$refs.workspace?.focusControl('commitQueueContextField')
      );
    },
    finishContext() {
      if (!this.contextEditing) return;
      this.contextEditing = false;
      const process = this.selected.process.replace(/^\/+|\/+$/g, '');
      let branch = this.contextBranch
        .trim()
        .replaceAll(' ', '_')
        .replace(/^\/+|\/+$/g, '');
      if (branch.startsWith(process + '/'))
        branch = branch.slice(process.length + 1);
      this.update('context', process + (branch ? '/' + branch : ''));
    },
    ...QueueFiles,
    cancel(job = this.selected) {
      if (!job) return;
      if (['Uploading', 'Checking in'].includes(job.status)) {
        this.cancelRequested = true;
        if (job.status === 'Uploading') this.aborter?.abort();
      } else if (editable(job)) {
        job.status = 'Cancelled';
        job.request++;
        this.changed();
      }
    },
    retry(job = this.selected) {
      if (
        !this.running &&
        ['Failed', 'Cancelled'].includes(job?.status) &&
        job.file
      ) {
        job.status = 'Queued';
        this.run([job]);
      }
    },
    async run(requested = this.jobs.filter((job) => job.checked)) {
      if (this.running || this.disposed || !this.ticket) return;
      const epoch = this.sessionEpoch;
      this.running = true;
      this.cancelRequested = false;
      try {
        for (const job of [...requested]) {
          if (this.cancelRequested) break;
          if (!editable(job) || !job.file || job.status === 'Cancelled')
            continue;
          await this.validate(job);
          if (!this.ownsJob(job, epoch)) return;
          if (
            job.planError ||
            this.cancelRequested ||
            job.status === 'Cancelled' ||
            !this.jobs.includes(job)
          )
            continue;
          job.error = '';
          job.status = 'Uploading';
          job.progress = 0;
          try {
            const names = [],
              files = [...job.files, ...job.previews];
            this.aborter = markRaw(new AbortController());
            for (const [index, file] of files.entries()) {
              const suffix = file.name.includes('.')
                ? file.name.slice(file.name.lastIndexOf('.'))
                : '';
              names.push(
                await uploadFormFile(job.ticket, job.project, file, {
                  signal: this.aborter.signal,
                  filename:
                    job.ingest || job.preview
                      ? file.name
                      : 'queue-' +
                        job.id +
                        '-' +
                        index +
                        '-' +
                        Date.now() +
                        suffix
                })
              );
              if (!this.ownsJob(job, epoch)) return;
              job.progress = ((index + 1) / files.length) * 0.85;
            }
            if (this.cancelRequested) {
              job.status = 'Cancelled';
              continue;
            }
            job.status = 'Checking in';
            this.changed();
            const auth = {
              ticket: job.ticket,
              project: job.project,
              language: 'python'
            };
            if (job.ingest) {
              const result = (
                await rpc('execute_cmd', [
                  auth,
                  'tactic.command.related_ingest_cmd.RelatedIngestCmd',
                  { ...job.ingest, action: 'checkin', filenames: names }
                ])
              ).info;
              if (!this.ownsJob(job, epoch)) return;
              if (result.skipped) {
                job.status = 'Skipped';
                job.error = result.reason;
                job.file = null;
                job.files = [];
                this.changed();
                continue;
              }
              job.snapshot = result.snapshot;
              job.searchKey = result.search_key;
            } else if (job.preview)
              job.snapshot = await rpc(
                'simple_checkin',
                [auth, job.searchKey, 'icon', names[0]],
                {
                  mode: 'uploaded',
                  description: job.description || 'Search Type preview',
                  process: 'icon',
                  create_icon: job.generatePreviews !== false
                }
              );
            else
              job.snapshot = (
                await rpc('execute_cmd', [
                  auth,
                  'tactic.command.browser_checkin_cmd.BrowserCheckinCmd',
                  { ...this.options(job, 'checkin'), files: names }
                ])
              ).info.snapshot;
            if (!this.ownsJob(job, epoch)) return;
            const completedFiles = job.files;
            job.status = 'Complete';
            job.progress = 1;
            job.file = null;
            job.files = [];
            job.previews = [];
            notify('complete', 'Check-in completed', job.name, 'checkin');
            this.changed();
            this.$emit('completed', { ...job, completedFiles });
            if (preferences.checkin.commitQueueAutoClean) this.remove(job);
          } catch (error) {
            if (!this.ownsJob(job, epoch)) return;
            job.status =
              job.status === 'Uploading' && error.name === 'AbortError'
                ? 'Cancelled'
                : job.status === 'Checking in' &&
                    (!error.status || error.status >= 500)
                  ? 'Result unknown'
                  : 'Failed';
            job.error = error.message;
            this.changed();
            if (job.status !== 'Cancelled')
              notify('error', job.error, job.name, 'checkin');
          } finally {
            if (epoch === this.sessionEpoch) this.aborter = null;
          }
        }
      } finally {
        if (epoch === this.sessionEpoch && !this.disposed) {
          this.running = false;
          this.validateAll();
        }
      }
    },
    async naming() {
      const epoch = this.sessionEpoch;
      this.namingScope = {
        ticket: this.selected.ticket,
        project: this.selected.project,
        type: this.selected.searchKey.split('?')[0]
      };
      await nextTick();
      if (!this.disposed && epoch === this.sessionEpoch)
        this.$refs.namingDialog?.show();
    },
    closeNaming() {
      if (
        !this.$refs.namingEditor?.canLeave ||
        this.$refs.namingEditor.canLeave()
      )
        this.$refs.namingDialog.close();
    }
  }
};
</script>
<template>
  <Teleport defer :to="docked ? '#dock-commit_queue' : 'body'">
    <component
      v-show="presentationVisible"
      v-window="docked ? false : { kind: 'commit_queue', type: 'window' }"
      :is="docked ? 'section' : 'dialog'"
      ref="dialog"
      class="commit-queue"
      :class="{ 'commit-queue-docked': docked, 'record-dialog': !docked }"
      :aria-label="t('Commit Queue')"
      @paste="paste"
      @close="
        modal = false;
        $emit('closed');
      "
    >
      <header v-if="!docked">
        <h2>{{ t('Commit Queue') }}</h2>
        <AppButton label="Close" icon="close" @click="$refs.dialog.close()" />
      </header>
      <QueueWorkspace
        ref="workspace"
        :model="frameModel"
        :operations="frameOperations"
        :files="frameFiles"
        :preview-files="framePreviews"
        @event="dispatch"
        @resize="queueSize = $event"
      />
      <QueueDialogs
        ref="auxiliary"
        :model="frameModel"
        :rows="previewRows"
        :files="framePreviews"
        :owner="$refs.workspace?.element()"
        @event="dispatch"
        @clear="clear()"
      />
      <input
        ref="previewsInput"
        class="queue-hidden-input"
        type="file"
        accept="image/*"
        multiple
        @change="
          previewsPicked($event.target.files);
          $event.target.value = '';
        "
      />
      <input
        ref="reselectInput"
        class="queue-hidden-input"
        type="file"
        multiple
        @change="
          sourcesPicked($event.target.files);
          $event.target.value = '';
        "
      />
      <input
        ref="reselectDirectory"
        class="queue-hidden-input"
        type="file"
        webkitdirectory
        multiple
        @change="
          sourcesPicked($event.target.files);
          $event.target.value = '';
        "
      />
    </component>
  </Teleport>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'naming_editor', type: 'window' }"
      ref="namingDialog"
      class="record-dialog queue-naming-editor"
      :aria-label="t('Naming Editor')"
      @cancel.prevent="closeNaming"
    >
      <header>
        <h2>{{ t('Naming Editor') }}</h2>
        <AppButton label="Close" icon="close" @click="closeNaming" />
      </header>
      <NamingEditor
        v-if="namingScope"
        ref="namingEditor"
        :ticket="namingScope.ticket"
        :project="namingScope.project"
        :search-type="namingScope.type"
        @saved="validateAll"
      />
    </dialog>
  </Teleport>
</template>
<style>
.commit-queue.record-dialog {
  width: min(1180px, calc(100vw - 24px));
  height: min(820px, calc(100dvh - 24px));
  padding: 10px;
  overflow: hidden;
}
.commit-queue[open],
.commit-queue-docked {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.commit-queue-docked {
  width: 100%;
  height: 100%;
}
.commit-queue .queue-hidden-input {
  display: none;
}
.queue-naming-editor {
  width: min(1200px, calc(100vw - 24px));
  height: min(850px, calc(100dvh - 24px));
}
@media (max-width: 720px) {
  .commit-queue.record-dialog {
    width: 100%;
    height: 100dvh;
    padding: 0;
  }
}
</style>

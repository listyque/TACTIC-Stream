<script>
import { nextTick } from 'vue';
import { mobile } from '../../mobile.js';
import { resultItems, navigationLink, rpc, uploadFormFile } from '../../api.js';
import { t } from '../../i18n.js';
import { preferences } from '../configuration/preferences.js';
import AppButton from '../../controls/AppButton.vue';
import ObjectCheckinForm from './ObjectCheckinForm.vue';
import ObjectRevisionConfirmation from './ObjectRevisionConfirmation.vue';
import { sourcePath } from './files.js';

export default {
  components: { AppButton, ObjectCheckinForm, ObjectRevisionConfirmation },
  inject: {
    queueCheckin: { default: null },
    checkinDescription: { default: () => () => '' }
  },
  props: { ticket: String, project: String },
  data() {
    return {
      owner: null,
      scope: null,
      files: [],
      processes: [],
      process: 'publish',
      context: 'publish',
      description: '',
      mode: 'group',
      preview: false,
      clipboard: false,
      revision: false,
      version: null,
      confirmed: false,
      appendSnapshot: null,
      appendUncertain: false,
      existingFiles: [],
      keepFileName: false,
      repositories: [],
      repositoryAlias: 'default',
      ready: false,
      busy: false,
      error: '',
      discard: false,
      request: 0,
      pickerRequest: 0
    };
  },
  emits: ['attached'],
  watch: {
    busy(value) {
      if (!value && this.ready && this.revision && !this.confirmed) {
        const request = this.request;
        nextTick(() => {
          if (request === this.request && this.ready)
            this.$refs.revisionDialog.show(this.$refs.dialog);
        });
      }
    },
    ticket() {
      this.reset();
    },
    project() {
      this.reset();
    }
  },
  computed: {
    frameModel() {
      return {
        preview: this.preview,
        revision: this.revision,
        append: !!this.appendSnapshot,
        ready: this.ready,
        busy: this.busy,
        error: t(this.error),
        appendUncertain: this.appendUncertain,
        count: this.files.length,
        repositoryAlias: this.repositoryAlias,
        repositories: this.repositories,
        process: this.process,
        context: this.context,
        processes: this.processes,
        description: this.description,
        mode: this.mode,
        keepFileName: this.keepFileName,
        confirmed: this.confirmed,
        discard: this.discard,
        hasQueue: !!this.queueCheckin
      };
    },
    mobile() {
      return mobile.value;
    },
    title() {
      return this.appendSnapshot
        ? 'Attach files'
        : this.preview
          ? 'Change Preview'
          : this.revision
            ? 'Add revision (override current file)'
            : this.clipboard
              ? 'Save from Clipboard'
              : 'Save snapshot';
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
  },
  beforeUnmount() {
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    dispatch(action) {
      if (action.type === 'close') this.close();
      else if (action.type === 'continue') this.discard = false;
      else if (action.type === 'discard' && !this.busy) this.close(true);
      else if (action.type === 'submit') this.submit();
      else if (!this.busy) {
        if (action.type === 'choose') {
          this.pickerRequest = this.request;
          this.$refs.fileInput.click();
        } else if (action.type === 'clipboard') this.readImage();
        else if (
          action.type === 'mode' &&
          ['group', 'individual'].includes(action.value)
        )
          this.mode = action.value;
        else if (action.type === 'removeFile') {
          const file = this.files[action.index];
          if (file && sourcePath(file) === action.path)
            this.files.splice(action.index, 1);
        } else if (
          action.type === 'field' &&
          [
            'repositoryAlias',
            'process',
            'context',
            'description',
            'keepFileName'
          ].includes(action.field)
        ) {
          this[action.field] = action.value;
          if (action.field === 'process') this.context = '';
        }
      }
    },
    resolveRevision(action) {
      if (this.busy || !this.ready) return;
      if (action.type === 'accept') {
        this.confirmed = true;
        this.$refs.revisionDialog.close();
      } else this.close(true);
    },
    beforeUnload(event) {
      if (this.files.length) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    reset() {
      this.request++;
      this.ready = false;
      this.$refs.revisionDialog?.close();
      this.files = [];
      this.$refs.dialog?.close();
    },
    close(force = false) {
      force = force === true;
      if (this.busy && this.ready && !force) return;
      if (this.files.length && !force) {
        this.discard = true;
        return;
      }
      this.reset();
    },
    async open(record, options = {}) {
      const request = ++this.request;
      this.pickerRequest = request;
      this.scope = { ticket: this.ticket, project: this.project };
      this.owner = record;
      this.files = [];
      this.processes = [];
      this.error = '';
      this.discard = false;
      this.appendSnapshot = null;
      this.appendUncertain = false;
      this.existingFiles = [];
      this.repositories = [];
      this.repositoryAlias = preferences.repository.defaultAlias;
      this.description = this.checkinDescription();
      this.mode = preferences.checkin.groupCheckin ? 'group' : 'individual';
      this.keepFileName = preferences.checkin.keepFilename;
      this.confirmed = !preferences.checkin.confirmRevision;
      if (options.checkinType === 'file') this.mode = 'individual';
      if (options.checkinType === 'multi_file') this.mode = 'group';
      this.preview = !!options.preview;
      this.clipboard = !!options.clipboard;
      this.revision = !!options.revision;
      this.version = null;
      this.process = options.process || (this.preview ? 'icon' : 'publish');
      this.context =
        options.context && options.context !== this.process
          ? options.context
          : '';
      this.busy = true;
      this.ready = false;
      await nextTick();
      this.$refs.dialog.showModal();
      try {
        if (
          ['move', 'local', 'inplace'].includes(options.transferMode) ||
          ['sequence', 'dir'].includes(options.checkinType)
        )
          throw new Error(
            'This configured check-in mode requires a desktop connection.'
          );
        if (record.__search_key__.startsWith('sthpw/snapshot?')) {
          const target = await navigationLink(
            this.scope.ticket,
            this.scope.project,
            'skey://' + record.__search_key__
          );
          if (request !== this.request) return;
          if (!target.parent) throw new Error('Object no longer exists');
          this.owner = target.parent;
          this.context = record.context;
          this.process = record.process || record.context.split('/')[0];
          if (options.append) {
            this.appendSnapshot =
              record.version < 0
                ? (await rpc(
                    'get_snapshot',
                    [this.scope, this.owner.__search_key__],
                    { context: record.context }
                  )) || record
                : record;
            const snapshot = await navigationLink(
              this.scope.ticket,
              this.scope.project,
              'skey://' + this.appendSnapshot.__search_key__
            );
            if (request !== this.request) return;
            this.existingFiles = snapshot.preview?.files || [];
          }
          if (this.revision && record.version >= 0)
            this.version = record.version;
        }
        const type = this.owner.__search_key__.split('?')[0];
        const data = await resultItems(
          this.scope.ticket,
          this.scope.project,
          type,
          [this.owner.__search_key__]
        );
        if (request !== this.request) return;
        this.processes = data.items[0].branches
          .filter((branch) => branch.kind === 'process')
          .map((branch) => ({ value: branch.process, label: branch.title }));
        if (this.preview) this.process = this.context = 'icon';
        if (!this.processes.some((item) => item.value === this.process))
          this.processes.unshift({ value: this.process, label: this.process });
        const configured = await rpc('get_base_dirs', [this.scope], {}, true);
        if (request !== this.request) return;
        const paths = (value) =>
          typeof value === 'object' && value
            ? value
            : value?.startsWith('{')
              ? JSON.parse(value)
              : value
                ? { default: value }
                : {};
        const aliases = [
          ...new Set([
            'default',
            ...Object.keys(paths(configured.asset_base_dir)),
            ...Object.keys(paths(configured.base_dir_alias))
          ])
        ];
        const labels = paths(configured.repository_display);
        this.repositories = aliases
          .filter(
            (alias) =>
              alias !== 'plugins' &&
              (preferences.repository.enabledAliases === null ||
                preferences.repository.enabledAliases.includes(alias))
          )
          .map((alias) => ({
            value: alias,
            label: labels[alias]?.title || alias
          }));
        if (!this.repositories.length)
          throw new Error(
            'Enable at least one repository and choose its default.'
          );
        if (
          !this.repositories.some((item) => item.value === this.repositoryAlias)
        )
          this.repositoryAlias = this.repositories[0].value;
        this.ready = true;
        if (options.clipboard) await this.readImage();
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    addFiles(files) {
      const incoming = [...files];
      if (
        incoming.some((file) => this.preview && !file.type.startsWith('image/'))
      ) {
        this.error = 'Choose an image for the preview';
        return;
      }
      this.files.push(...incoming);
      this.error = '';
    },
    paste(event) {
      if (!this.busy && event.clipboardData?.files.length) {
        event.preventDefault();
        this.addFiles(event.clipboardData.files);
      }
    },
    async readImage() {
      if (!navigator.clipboard?.read) {
        this.error = 'Paste an image with Ctrl+V or choose a file on HTTP.';
        return;
      }
      const request = this.request;
      try {
        const files = [];
        for (const item of await navigator.clipboard.read()) {
          const type = item.types.find((type) => type.startsWith('image/'));
          if (type)
            files.push(
              new File(
                [await item.getType(type)],
                'clipboard-' + (files.length + 1) + '.' + type.split('/')[1],
                { type }
              )
            );
        }
        if (request !== this.request) return;
        if (!files.length) throw new Error('No image in clipboard');
        this.addFiles(files);
      } catch (error) {
        if (request === this.request) this.error = error.message;
      }
    },
    submit() {
      if (this.appendSnapshot) return this.attachFiles();
      if (
        !this.ready ||
        this.busy ||
        !this.files.length ||
        !(this.context.trim() || this.process) ||
        (this.revision && !this.confirmed)
      )
        return;
      if (
        new Set(this.files.map((file) => file.name)).size !== this.files.length
      ) {
        this.error = 'Choose different file names for a group check-in';
        return;
      }
      try {
        const values = {
          ...this.scope,
          searchKey: this.owner.__search_key__,
          title: this.owner.name || this.owner.title || this.owner.code,
          process: this.process,
          context: this.context.trim() || this.process,
          description: this.description,
          isRevision: this.revision,
          version: this.version,
          keepFileName: this.keepFileName,
          generatePreviews: preferences.checkin.generatePreviews,
          ...(this.revision ? {} : { repositoryAlias: this.repositoryAlias })
        };
        const groups =
          this.mode === 'individual'
            ? this.files.map((file) => [file])
            : [this.files];
        for (const files of groups)
          this.queueCheckin({
            ...values,
            files: [...files],
            file: files[0],
            name: files.map((file) => file.name).join(', ')
          });
        this.files = [];
        this.close(true);
      } catch (error) {
        this.error = error.message;
      }
    },
    async attachFiles() {
      if (
        !this.ready ||
        this.busy ||
        this.appendUncertain ||
        !this.files.length
      )
        return;
      const names = this.files.map((file) => file.name.toLocaleLowerCase());
      if (
        new Set(names).size !== names.length ||
        this.existingFiles.some((file) =>
          names.includes(file.filename.toLocaleLowerCase())
        )
      ) {
        this.error = 'Choose file names that are not already in the snapshot';
        return;
      }
      const request = this.request,
        scope = this.scope;
      this.busy = true;
      this.error = '';
      let committing = false;
      try {
        const paths = [];
        for (const file of this.files) {
          paths.push(await uploadFormFile(scope.ticket, scope.project, file));
          if (request !== this.request) return;
        }
        committing = true;
        await rpc('add_file', [scope, this.appendSnapshot.code, paths], {
          file_type: 'attachment',
          mode: 'upload'
        });
        if (request !== this.request) return;
        this.busy = false;
        this.files = [];
        this.close(true);
        this.$emit('attached');
      } catch (error) {
        if (request === this.request) {
          this.appendUncertain =
            committing && (!error.status || error.status >= 500);
          this.error = error.message;
        }
      } finally {
        if (request === this.request) this.busy = false;
      }
    }
  }
};
</script>
<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="record-dialog object-checkin"
      :aria-label="t(title)"
      @cancel.prevent="close()"
      @paste="paste"
      @dragover.prevent
      @drop.prevent="!busy && addFiles($event.dataTransfer.files)"
    >
      <header>
        <AppButton
          v-if="mobile"
          label="Back"
          icon="MDI_ARROW_LEFT"
          icon-only
          @click="close()"
        />
        <div>
          <h2>{{ t(title) }}</h2>
          <small
            >{{ owner?.name || owner?.title || owner?.code
            }}<template v-if="!mobile">
              · {{ owner?.__search_key__ }}</template
            ></small
          >
        </div>
        <AppButton v-if="!mobile" label="Close" icon="close" @click="close()" />
      </header>
      <ObjectCheckinForm :model="frameModel" :files="files" @event="dispatch" />
      <input
        ref="fileInput"
        type="file"
        multiple
        hidden
        :accept="preview ? 'image/*' : undefined"
        :disabled="busy"
        @change="
          pickerRequest === request && addFiles($event.target.files);
          $event.target.value = '';
        "
      />
    </dialog>
    <ObjectRevisionConfirmation
      ref="revisionDialog"
      :busy="busy"
      @event="resolveRevision"
    />
  </Teleport>
</template>
<style>
.object-checkin.record-dialog {
  width: min(760px, calc(100vw - 24px));
  height: min(820px, calc(100dvh - 24px));
  overflow: hidden;
}
.object-checkin[open] {
  display: flex;
  flex-direction: column;
}
.object-checkin > header {
  flex: none;
}
.object-checkin > header > div {
  flex: 1;
  min-width: 0;
}
.object-checkin > header small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
}
@media (max-width: 700px) {
  .object-checkin.record-dialog[open] {
    width: 100dvw;
    height: 100dvh;
    max-width: none;
    max-height: 100dvh;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 0;
    gap: 0;
  }
  .object-checkin > header {
    display: flex;
    flex-wrap: nowrap;
    gap: 8px;
    padding: 8px;
    margin: 0;
  }
  .object-checkin > header h2 {
    font-size: var(--text-body-large);
    margin: 0;
  }
  .object-checkin > header .icon-button {
    width: 28px;
    height: 28px;
    min-width: 28px;
  }
}
</style>

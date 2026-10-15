<script>
// Review/confirmation adapted from Handler's schema_delete.py and
// AdminSchemaDeleteConfirmation.qml. The native command owns every mutation.
import { nextTick } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/schema/schema_delete.ui.mjs';

export default {
  components: { AppButton, FrameView },
  props: { ticket: String, project: String },
  emits: ['deleted', 'uncertain', 'active'],
  data() {
    return {
      viewport: { width: 1, height: 1 },
      observer: null,
      resizeFrame: 0,
      active: false,
      context: null,
      identity: '',
      schemaRevision: '',
      revision: '',
      metadata: null,
      confirmation: '',
      canWrite: false,
      busy: false,
      deleting: false,
      uncertain: false,
      error: '',
      request: 0
    };
  },
  computed: {
    frameModel() {
      return {
        identity: this.identity,
        schemaRevision: this.schemaRevision,
        metadata: this.metadata,
        canWrite: this.canWrite,
        busy: this.busy,
        deleting: this.deleting,
        uncertain: this.uncertain,
        error: this.error,
        confirmation: this.confirmation
      };
    },
    frameScene() {
      return UI.describe(
        this.frameModel,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    enabled() {
      return (
        this.canWrite &&
        !this.busy &&
        !this.uncertain &&
        this.confirmation === this.identity
      );
    }
  },
  mounted() {
    this.observer = new ResizeObserver((entries) => {
      cancelAnimationFrame(this.resizeFrame);
      this.resizeFrame = requestAnimationFrame(() => {
        for (const entry of entries)
          this.viewport = {
            width: Math.max(1, entry.contentRect.width),
            height: Math.max(1, entry.contentRect.height)
          };
      });
    });
    this.observer.observe(this.$refs.body);
  },
  beforeUnmount() {
    this.observer?.disconnect();
    cancelAnimationFrame(this.resizeFrame);
    this.request++;
  },
  watch: {
    ticket() {
      this.reset();
    },
    project() {
      this.reset();
    }
  },
  methods: {
    t,
    async dispatch(event) {
      for (const command of UI.transition(this.frameModel, event)) {
        if (command.type === 'confirmation') this.confirmation = command.value;
        else if (command.type === 'delete') await this.remove();
        else if (command.type === 'reload') await this.load();
        else if (command.type === 'close') this.close();
      }
    },
    reset() {
      this.request++;
      this.active = false;
      this.$refs.dialog?.close();
      this.$emit('active', false);
    },
    async call(action, values = {}) {
      const result = await rpc('execute_cmd', [
        {
          ticket: this.context.ticket,
          project: this.context.project,
          language: 'python'
        },
        'tactic.ui.panel.schema_delete_cmd.SchemaDeleteCmd',
        {
          action,
          project_code: this.context.project,
          identity: this.identity,
          ...values
        }
      ]);
      return result.info;
    },
    async open(identity, schemaRevision) {
      this.context = { ticket: this.ticket, project: this.project };
      this.identity = identity;
      this.schemaRevision = schemaRevision;
      this.metadata = null;
      this.confirmation = '';
      this.uncertain = false;
      this.active = true;
      this.$emit('active', true);
      await nextTick();
      this.$refs.dialog.showModal();
      this.$refs.frame.focusControl('adminDeleteSearchTypeCancel');
      await this.load();
    },
    async load() {
      const id = ++this.request;
      this.busy = true;
      this.error = '';
      this.canWrite = false;
      this.confirmation = '';
      try {
        const result = await this.call('load');
        if (id !== this.request) return;
        this.metadata = result.metadata;
        this.revision = result.revision;
        if (this.metadata.schemaRevision !== this.schemaRevision)
          throw Error(
            'Schema changed on the server. Reload before deleting a Search Type.'
          );
        this.canWrite = result.canWrite;
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    close() {
      if (!this.deleting) this.reset();
    },
    async remove() {
      if (!this.enabled) return;
      const id = this.request;
      this.busy = this.deleting = true;
      this.error = '';
      try {
        const result = await this.call('save', {
          document: { confirmation: this.confirmation },
          expected_revision: this.revision
        });
        if (id === this.request) {
          this.$emit('deleted', result);
          this.reset();
        }
      } catch (error) {
        if (id === this.request) {
          this.canWrite = false;
          this.uncertain = !error.status || error.status >= 500;
          this.error = this.uncertain
            ? 'The deletion result is unknown. Close this review and reload the schema before trying again.'
            : error.message;
          if (this.uncertain) this.$emit('uncertain');
        }
      } finally {
        if (id === this.request || !this.active)
          this.busy = this.deleting = false;
      }
    }
  }
};
</script>
<template>
  <dialog
    v-window
    ref="dialog"
    class="record-dialog schema-deletion-dialog frame-schema-delete"
    :aria-label="t('Delete Search Type from project')"
    @cancel.prevent.stop="dispatch({ type: 'close' })"
    @keydown.esc.stop
  >
    <header class="configuration-header">
      <h1>{{ t('Delete Search Type from project') }}</h1>
    </header>
    <div ref="body" class="frame-host-body">
      <FrameView ref="frame" :scene="frameScene" @event="dispatch" />
    </div>
  </dialog>
</template>
<style scoped>
.frame-schema-delete[open] {
  display: flex;
  flex-direction: column;
  width: min(540px, calc(100vw - 24px));
  height: min(700px, calc(100dvh - 24px));
  gap: 12px;
}
</style>

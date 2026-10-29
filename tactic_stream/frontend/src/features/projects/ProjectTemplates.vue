<script>
import { nextTick } from 'vue';
import { t } from '../../i18n.js';
import { rpc, uploadFormFile } from '../../api.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/projects/templates.ui.mjs';

export default {
  inject: ['openHelp'],
  components: { FrameView },
  props: { ticket: String, packages: Array },
  emits: ['changed'],
  data() {
    return {
      busy: false,
      error: '',
      deletion: null,
      selected: '',
      viewport: { width: 650, height: 500 },
      observer: null,
      generation: 0
    };
  },
  computed: {
    confirmationScene() {
      return UI.confirmation(
        { code: this.deletion?.code || '', busy: this.busy },
        Math.min(430, this.viewport.width - 32),
        220,
        appearance.language
      );
    },

    scene() {
      return UI.describe(
        {
          packages: this.packages,
          selected: this.selected,
          busy: this.busy,
          error: this.error,
          deletion: this.deletion?.code
        },
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    }
  },
  watch: {
    deletion(value) {
      if (value)
        nextTick(() => {
          if (this.deletion && !this.$refs.confirm.matches(':modal'))
            this.$refs.confirm.showModal();
        });
      else this.$refs.confirm?.close();
    },
    ticket() {
      this.generation++;
      this.busy = false;
      this.deletion = null;
      this.$refs.dialog.close();
    }
  },
  mounted() {
    this.observer = observeFrameSizes((entries) => {
      const box = entries.at(-1).contentRect;
      this.viewport = { width: box.width, height: box.height };
    });
    this.observer.observe(this.$refs.host);
  },
  beforeUnmount() {
    this.generation++;
    this.observer?.disconnect();
  },
  methods: {
    t,
    dispatch(action) {
      const row = this.packages.find((row) => row.code === this.selected);
      if (action.type === 'select') this.selected = action.code;
      else if (action.type === 'help') this.openHelp('project_creation');
      else if (action.type === 'close' && !this.busy) this.$refs.dialog.close();
      else if (action.type === 'install') this.$refs.file.click();
      else if (action.type === 'refresh') this.$emit('changed');
      else if (action.type === 'download' && row) this.download(row);
      else if (action.type === 'delete') this.deletion = row;
      else if (action.type === 'cancelDelete') this.deletion = null;
      else if (action.type === 'confirmDelete') this.remove();
    },
    open() {
      this.error = '';
      this.deletion = null;
      this.$refs.dialog.showModal();
    },
    async run(command, args) {
      const generation = this.generation;
      this.error = '';
      this.busy = true;
      try {
        const result = await rpc('execute_cmd', [
          { ticket: this.ticket, project: 'admin', language: 'python' },
          command,
          args
        ]);
        return generation === this.generation ? result : null;
      } catch (error) {
        if (generation !== this.generation) return null;
        this.error = error.message;
        return null;
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    },
    async install(event) {
      const generation = this.generation,
        ticket = this.ticket;
      const file = event.target.files[0];
      event.target.value = '';
      if (!file) return;
      this.busy = true;
      this.error = '';
      try {
        const filename = await uploadFormFile(ticket, 'admin', file);
        if (generation !== this.generation) return;
        const result = await this.run(
          'tactic.ui.app.ProjectTemplateInstallCmd',
          { paths: [filename] }
        );
        if (result) this.$emit('changed');
      } catch (error) {
        if (generation !== this.generation) return;
        this.error = error.message;
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    },
    async download(row) {
      const result = await this.run(
        'tactic.ui.app.ProjectTemplateDownloadCmd',
        { template_dir: row.path }
      );
      if (!result) return;
      const link = document.createElement('a');
      link.href =
        '/assets/_cache/' +
        encodeURIComponent(this.ticket) +
        '/' +
        encodeURIComponent(result.info.filename);
      link.download = result.info.filename;
      link.click();
    },
    async remove() {
      const result = await this.run('tactic.ui.app.ProjectTemplateDeleteCmd', {
        template: this.deletion.code
      });
      if (result) {
        this.deletion = null;
        this.$emit('changed');
      }
    }
  }
};
</script>

<template>
  <dialog
    v-window="{ kind: 'project_templates' }"
    ref="dialog"
    class="record-dialog project-templates"
    :aria-label="t('Manage templates')"
    @cancel.prevent="!busy && $refs.dialog.close()"
  >
    <div ref="host" class="frame-project-templates">
      <FrameView :scene="scene" @event="dispatch" />
    </div>
    <input
      ref="file"
      type="file"
      accept=".zip"
      hidden
      :aria-label="t('Template ZIP archive')"
      :disabled="busy"
      @change="install"
    />
    <dialog
      ref="confirm"
      class="record-dialog frame-template-confirmation"
      :aria-label="t('Delete template?')"
      :style="{ width: Math.min(430, viewport.width - 32) + 'px' }"
      @cancel.prevent="!busy && (deletion = null)"
    >
      <header>
        <h3>{{ t('Delete template?') }}</h3>
      </header>
      <div class="frame-template-confirmation-body">
        <FrameView
          :scene="confirmationScene"
          @event="
            dispatch({
              type: $event.type === 'accept' ? 'confirmDelete' : 'cancelDelete'
            })
          "
        />
      </div>
    </dialog>
  </dialog>
</template>

<style>
.project-templates {
  padding: 0;
  width: 760px;
  height: 600px;
  overflow: hidden;
}
.frame-project-templates {
  position: relative;
  width: 100%;
  height: 100%;
}
.frame-project-templates > .frame-view {
  position: absolute;
  inset: 0;
}
</style>

<style>
.frame-template-confirmation {
  --dialog-content-top: 0px;
  --dialog-content-side: 0px;
  padding: 0;
  overflow: hidden;
}
.frame-template-confirmation > header {
  padding: 12px 20px;
  margin: 0;
}
.frame-template-confirmation h3 {
  font-size: 16px;
  font-weight: 600;
}
.frame-template-confirmation-body {
  height: 220px;
}
</style>

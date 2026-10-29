<script>
import { nextTick } from 'vue';
import { t } from '../../i18n.js';
import { projectCreationCatalog, rpc, uploadFormFile } from '../../api.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/projects/project.ui.mjs';
import ImagePicker from '../../controls/ImagePicker.vue';
import ProjectTemplates from './ProjectTemplates.vue';

function identifier(value) {
  return value
    .replace(/[?.!@#$%^&*()'",;+=]/g, '')
    .replaceAll(' ', '_')
    .toLowerCase()
    .replace(/[\\_-]+/g, '_');
}

export default {
  inject: ['openHelp'],
  components: { FrameView, ProjectTemplates },
  props: { ticket: String, openProject: Function },
  data() {
    return {
      catalog: null,
      draft: {},
      step: 0,
      busy: false,
      error: '',
      image: null,
      imageValidating: false,
      createdCode: '',
      uncertain: false,
      discard: false,
      context: null,
      viewport: { width: 900, height: 700 },
      observer: null,
      generation: 0
    };
  },
  computed: {
    scene() {
      return UI.wizard(
        {
          product: 'TACTIC STREAM',
          style: appearance.theme,
          draft: this.draft,
          step: this.step,
          busy: this.busy,
          ready: !!this.catalog,
          templates: this.templates.map((row) => ({ ...row, dataLabel: true })),
          themes: this.themes.map((row) => ({ ...row, dataLabel: true })),
          createdCode: this.createdCode,
          uncertain: this.uncertain,
          error: this.error,
          discard: this.discard,
          image: !!this.image,
          imageValidating: this.imageValidating
        },
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    views() {
      return {
        image: {
          component: ImagePicker,
          props: {
            modelValue: this.image,
            previewSize: 160,
            inlineErrors: false,
            onError: (message) => {
              this.error = message;
            },
            fallbackText: this.draft.title,
            disabled: this.busy || !!this.createdCode || this.step === 3,
            'onUpdate:modelValue': (value) => {
              this.image = value;
            },
            onValidating: (value) => {
              this.imageValidating = value;
            }
          }
        }
      };
    },
    templates() {
      return [
        { value: '_empty', label: t('Empty project') },
        ...(this.catalog?.templates || []).map((row) => ({
          ...row,
          label:
            row.label +
            (row.kind === 'file'
              ? ' (' + t('From file') + ')'
              : row.kind === 'builtin'
                ? ' (' + t('Built-in') + ')'
                : '')
        }))
      ];
    },
    themes() {
      return [
        { value: '', label: t('No theme') },
        ...(this.catalog?.themes || [])
      ];
    },
    selectedTheme() {
      return (
        this.catalog?.themes.find((row) => row.value === this.draft.theme) || {}
      );
    },
    empty() {
      return this.draft.source === '_empty';
    },
    dirty() {
      return UI.wizardDirty(this.draft, this.image);
    }
  },
  watch: {
    ticket() {
      this.generation++;
      if (!this.busy) this.$refs.dialog.close();
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
    this.observer = observeFrameSizes((entries) => {
      const box = entries.at(-1).contentRect;
      this.viewport = { width: box.width, height: box.height };
    });
    this.observer.observe(this.$refs.frameHost);
  },
  beforeUnmount() {
    this.generation++;
    this.observer?.disconnect();
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    dispatch(action) {
      if (action.type === 'field') {
        this.draft[action.field] = action.value;
        if (action.field === 'title') this.titleChanged();
      } else if (
        action.type === 'page' &&
        !this.busy &&
        !this.createdCode &&
        Number(action.value) <= this.step
      ) {
        this.step = Number(action.value);
        this.error = '';
      } else if (action.type === 'help') this.openHelp('project_creation');
      else if (action.type === 'close') this.cancel();
      else if (action.type === 'keep') this.discard = false;
      else if (action.type === 'discard' && !this.busy)
        this.$refs.dialog.close();
      else if (action.type === 'refresh') this.reload();
      else if (action.type === 'templates') this.$refs.templates.open();
      else if (action.type === 'next') this.next();
      else if (action.type === 'back') {
        this.step--;
        this.error = '';
      } else if (action.type === 'submit') this.submit();
    },
    beforeUnload(event) {
      if (
        this.$refs.dialog.open &&
        (this.busy || this.dirty || this.createdCode || this.uncertain)
      ) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    windowContext() {
      if (
        this.busy ||
        this.uncertain ||
        this.createdCode ||
        this.imageValidating
      )
        throw Error('Please wait for the current operation to finish');
      return {
        state: { draft: this.draft, step: this.step, image: this.image }
      };
    },
    restoreWindowContext(state) {
      this.draft = state.draft;
      this.step = state.step;
      this.image = state.image;
    },
    async open() {
      if (this.$refs.dialog.open || this.busy) return;
      this.generation++;
      this.context = {
        ticket: this.ticket,
        project: 'admin',
        language: 'python'
      };
      this.draft = {
        title: '',
        code: '',
        description: '',
        category: '',
        namespace: '',
        source: '_empty',
        theme: '',
        isTemplate: false,
        isMainProject: false
      };
      this.catalog = this.image = null;
      this.step = 0;
      this.error = this.createdCode = '';
      this.uncertain = this.discard = false;
      this.$refs.dialog.showModal();
      await this.reload();
      await nextTick();
      this.$refs.frameHost
        .querySelector(
          '[data-frame=setting_title] input, input[data-frame=setting_title]'
        )
        ?.focus();
    },
    async reload() {
      if (this.busy) return;
      const generation = this.generation;
      this.busy = true;
      this.error = '';
      try {
        const catalog = await projectCreationCatalog(this.context.ticket);
        if (generation !== this.generation) return;
        this.catalog = catalog;
        if (!this.draft.title)
          this.draft.isMainProject = this.catalog.isMainProject;
        if (this.uncertain) {
          if (this.catalog.projectCodes.includes(this.draft.code))
            this.createdCode = this.draft.code;
          this.uncertain = false;
        }
      } catch (error) {
        if (generation !== this.generation) return;
        this.error = error.message;
      } finally {
        this.busy = false;
      }
    },
    titleChanged() {
      this.draft.code = identifier(this.draft.title).slice(0, 30);
    },
    validate() {
      this.draft.code = identifier(this.draft.code.trim());
      if (!this.draft.title.trim() || this.draft.title.length > 100)
        return 'Project title is required and cannot exceed 100 characters';
      if (!/^[A-Za-z_][A-Za-z0-9_]{0,29}$/.test(this.draft.code))
        return 'Project code must use letters, numbers and underscores, must not start with a number, and cannot exceed 30 characters';
      if (
        !this.createdCode &&
        this.catalog.projectCodes.includes(this.draft.code)
      )
        return 'A project with this code already exists, including retired projects';
      if (
        this.empty &&
        this.draft.namespace &&
        (!/^[A-Za-z_][A-Za-z0-9_]{0,29}$/.test(this.draft.namespace) ||
          ['sthpw', 'prod'].includes(this.draft.namespace))
      )
        return 'Invalid or reserved project namespace';
      if (!this.templates.some((row) => row.value === this.draft.source))
        return 'Select a template or an empty project';
      return '';
    },
    next() {
      this.error = this.validate();
      if (!this.error) this.step++;
    },
    cancel() {
      if (!this.busy) {
        if (this.dirty || this.createdCode || this.uncertain)
          this.discard = true;
        else this.$refs.dialog.close();
      }
    },
    async finish() {
      if (this.context.ticket !== this.ticket)
        throw new Error(
          'Connection context changed. Close this form and reopen it before saving.'
        );
      const values = Object.fromEntries(
        ['title', 'description', 'category'].map((key) => [
          key,
          this.draft[key].trim()
        ])
      );
      await rpc('update', [
        this.context,
        'sthpw/project?code=' + encodeURIComponent(this.createdCode),
        values
      ]);
      await this.openProject(this.createdCode);
      this.$refs.dialog.close();
    },
    async submit() {
      const generation = this.generation;
      if (this.busy || this.uncertain || this.imageValidating) return;
      if (this.context.ticket !== this.ticket) {
        this.error =
          'Connection context changed. Close this form and reopen it before saving.';
        return;
      }
      if (!this.createdCode && (this.error = this.validate())) return;
      this.busy = true;
      this.error = '';
      let creating = false;
      try {
        if (!this.createdCode) {
          const args = {
            project_code: this.draft.code,
            project_title: this.draft.title.trim(),
            project_theme: this.empty ? this.draft.theme : ''
          };
          let command = 'tactic.command.CreateProjectCmd';
          if (this.empty)
            Object.assign(args, {
              project_type: this.draft.namespace || this.draft.code,
              is_template: this.draft.isTemplate,
              is_main_project: this.draft.isMainProject
            });
          else {
            command = 'tactic.command.ProjectTemplateInstallerCmd';
            const [template, ...path] = this.draft.source.split('|');
            Object.assign(args, {
              template_code: template,
              force_database: true,
              ...(path.length ? { path: path.join('|') } : {})
            });
          }
          if (this.image) {
            const filename = await uploadFormFile(
              this.context.ticket,
              'admin',
              this.image
            );
            if (generation !== this.generation) return;
            const result = await rpc('execute_cmd', [
              this.context,
              'tactic.command.CopyFileToAssetTempCmd',
              { filename, ticket: this.context.ticket }
            ]);
            args.project_image_path = result.info.lib_path;
          }
          if (generation !== this.generation) return;
          creating = true;
          await rpc('execute_cmd', [this.context, command, args]);
          this.createdCode = this.draft.code;
          creating = false;
        }
        if (generation !== this.generation) return;
        await this.finish();
      } catch (error) {
        this.uncertain = creating;
        this.error = this.createdCode
          ? 'Project created. Retry opening it; creation will not be repeated.'
          : error.message;
      } finally {
        this.busy = false;
        if (generation !== this.generation) this.$refs.dialog?.close();
      }
    }
  }
};
</script>

<template>
  <dialog
    v-window="{ kind: 'project_wizard' }"
    ref="dialog"
    class="configuration-dialog project-creation-dialog"
    :aria-label="t('Create project')"
    @cancel.prevent="cancel"
  >
    <div ref="frameHost" class="frame-project-wizard" :aria-busy="busy">
      <FrameView :scene="scene" :views="views" @event="dispatch" />
    </div>
    <ProjectTemplates
      ref="templates"
      :ticket="context?.ticket"
      :packages="catalog?.installedTemplates || []"
      @changed="reload"
    />
  </dialog>
</template>

<style>
.project-creation-dialog {
  padding: 0;
  overflow: hidden;
}
.frame-project-wizard {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.frame-project-wizard > .frame-view {
  position: absolute;
  inset: 0;
}
</style>

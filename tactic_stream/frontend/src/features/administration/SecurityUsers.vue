<script>
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/users/users.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/users/users.state.mjs';
// Handler AdminUsersEditor / AdminUsersView / AdminUserDetails.
import { securityUsers } from '../../api.js';
import { t } from '../../i18n.js';
export default {
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved'],
  data() {
    return {
      catalog: null,
      context: null,
      identity: '',
      requestedLogin: '',
      revision: '',
      draft: null,
      original: null,
      busy: false,
      uncertain: false,
      error: '',
      message: '',
      ui: State.initial(),
      request: 0,
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null
    };
  },
  computed: {
    dirty() {
      return JSON.stringify(this.draft) !== JSON.stringify(this.original);
    },
    editable() {
      return (
        !!this.catalog &&
        this.catalog.canWrite !== false &&
        this.context?.ticket === this.ticket &&
        !this.busy &&
        !this.uncertain
      );
    },
    users() {
      const query = this.ui.query.trim().toLowerCase();
      return (this.catalog?.users || []).filter(
        (user) =>
          (this.ui.showRetired || !user.retired) &&
          (!query ||
            [user.login, user.displayName, user.document.email]
              .join(' ')
              .toLowerCase()
              .includes(query))
      );
    },
    models() {
      return { users: this.users, groups: this.catalog?.groups || [] };
    },
    frameModel() {
      return {
        draft: this.draft,
        identity: this.identity,
        profile: this.profile,
        ready: !!this.catalog && this.context?.ticket === this.ticket,
        canWrite: !!this.catalog && this.catalog.canWrite !== false,
        canLoad: !!this.ticket,
        busy: this.busy,
        dirty: this.dirty,
        uncertain: this.uncertain,
        error: this.error,
        message: this.message,
        userCount: this.users.length,
        groupCount: this.catalog?.groups.length || 0
      };
    },
    frameScene() {
      return UI.describe(
        this.frameModel,
        this.ui,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    toolbarScene() {
      return UI.toolbar(
        this.frameModel,
        this.ui,
        this.toolbarSize,
        appearance.language
      );
    },
    hostStyle() {
      return { gap: UI.metrics.toolbarGap + 'px' };
    },
    profile() {
      const row =
        this.catalog?.users.find((user) => user.login === this.identity) || {};
      return UI.profile(this.draft, row);
    }
  },
  watch: {
    project() {
      if (this.context) this.context.project = this.project;
    },
    ticket() {
      this.request++;
      this.busy = false;
      this.catalog = this.draft = this.original = null;
      this.requestedLogin = '';
      this.reload(true);
    }
  },
  mounted() {
    this.reload();
    window.addEventListener('beforeunload', this.beforeUnload);
    this.observer = observeFrameSizes((entries) => {
      for (const entry of entries) {
        if (entry.target === this.$refs.body)
          this.viewport = {
            width: Math.max(1, entry.contentRect.width),
            height: Math.max(1, entry.contentRect.height)
          };
        else this.toolbarSize = entry.contentRect.width;
      }
    });
    this.observer.observe(this.$refs.body);
    this.observer.observe(
      this.toolbarTarget
        ? document.querySelector(this.toolbarTarget) || this.$el
        : this.$el
    );
  },
  beforeUnmount() {
    this.request++;
    this.observer?.disconnect();
    if (this.draft) this.draft.password = '';
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    rowScene(node, record) {
      return UI.row(
        node,
        record,
        this.frameModel,
        this.ui,
        appearance.language
      );
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      for (const command of result.commands) {
        switch (command.type) {
          case 'create':
            this.create();
            break;
          case 'select':
            this.select(command.login);
            break;
          case 'query':
          case 'showRetired':
            break;
          case 'field':
            this.draft[command.field] = command.value;
            this.message = '';
            break;
          case 'member':
            this.member(command.name, command.value);
            break;
          case 'save':
            await this.save();
            break;
          case 'reload':
            await this.reload(command.force);
            break;
          case 'discard':
            this.select(
              this.identity || this.catalog?.users[0]?.login || '',
              true
            );
            break;
          case 'error':
            this.error = command.text;
            break;
          case 'focus':
            await this.$nextTick();
            this.$el
              .querySelector('[data-frame="' + command.id + '"]')
              ?.focus();
            break;
          default:
            throw Error('Unsupported Users command: ' + command.type);
        }
      }
    },
    beforeUnload(event) {
      if (this.dirty || this.busy || this.uncertain) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      if (this.busy) return false;
      if (this.dirty || this.uncertain) {
        this.error = '';
        this.dispatch({ type: 'discard' });
        return false;
      }
      return true;
    },
    accept(catalog, selected) {
      this.catalog = catalog;
      const requested = this.requestedLogin;
      this.requestedLogin = '';
      this.select(requested || selected || catalog.users[0]?.login || '', true);
      if (requested && this.identity !== requested)
        this.error = 'The configured table target is unavailable';
    },
    focus(login) {
      if (this.dirty || this.uncertain)
        throw new Error('Apply or discard unsaved changes first');
      if (this.busy || !this.catalog) this.requestedLogin = login;
      else {
        this.select(login, true);
        if (this.identity !== login)
          throw new Error('The configured table target is unavailable');
      }
    },
    select(login, loaded = false) {
      if (!loaded && (!this.editable || this.dirty)) return;
      const row = this.catalog?.users.find((user) => user.login === login);
      const previous = this.identity;
      this.identity = row?.login || '';
      this.revision = row?.revision || '';
      this.draft = row
        ? { ...row.document, groups: [...row.document.groups] }
        : null;
      this.original = this.draft
        ? { ...this.draft, groups: [...this.draft.groups] }
        : null;
      this.error = '';
      this.ui.confirmation = '';
      this.ui.showPassword = false;
      this.ui.passwordConfirm = '';
      if (previous !== this.identity) this.ui.page = 'profile';
    },
    create() {
      if (!this.editable || this.dirty) return;
      this.select('', true);
      this.draft = Object.fromEntries(
        this.catalog.fields.map((field) => [field, ''])
      );
      Object.assign(this.draft, { login: '', password: '', groups: [] });
      this.message = '';
    },
    async reload(force = false) {
      if (this.busy || !this.ticket) return;
      if (!force && (this.dirty || this.uncertain)) {
        this.dispatch({ type: 'reload' });
        return;
      }
      const request = ++this.request,
        selected = this.identity;
      this.context = { ticket: this.ticket, project: this.project };
      this.busy = true;
      this.error = '';
      this.message = '';
      try {
        const result = await securityUsers('read', this.context.ticket);
        if (request === this.request) {
          this.uncertain = false;
          this.accept(result, selected);
        }
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    member(name, checked) {
      if (this.editable && this.draft)
        this.draft.groups = checked
          ? [...new Set([...this.draft.groups, name])].sort()
          : this.draft.groups.filter((group) => group !== name);
    },
    async save() {
      if (!this.editable || !this.dirty || !this.draft) return;
      if (!this.draft.login.trim()) {
        this.error = 'A login is required';
        return;
      }
      const request = this.request;
      this.busy = true;
      this.error = '';
      this.message = '';
      try {
        const result = await securityUsers('save', this.context.ticket, {
          identity: this.identity,
          document: this.draft,
          expected_revision: this.revision
        });
        if (request !== this.request) return;
        this.accept(result, result.selected);
        this.message = 'User saved on server';
        this.$emit('saved', result);
      } catch (error) {
        if (request !== this.request) return;
        this.uncertain = !error.status || error.status >= 500;
        this.error = this.uncertain
          ? 'The save result is unknown. Reload users before trying again.'
          : error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    }
  }
};
</script>

<template>
  <section
    class="security-users security-groups frame-host"
    :style="hostStyle"
    :aria-label="t('User directory')"
    :aria-busy="busy"
  >
    <Teleport defer :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarSize + 'px' }"
      >
        <FrameView :scene="toolbarScene" @event="dispatch" /></div
    ></Teleport>
    <div ref="body" class="frame-host-body">
      <FrameView
        :scene="frameScene"
        :models="models"
        :describe-row="rowScene"
        @event="dispatch"
      />
    </div>
  </section>
</template>

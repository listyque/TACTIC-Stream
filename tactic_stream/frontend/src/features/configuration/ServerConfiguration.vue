<script>
import {
  serverConfiguration,
  saveServerConfiguration,
  restartServer,
  serverRuntime
} from '../../api.js';
import { t } from '../../i18n.js';
import AppIcon from '../../controls/AppIcon.vue';
import AppButton from '../../controls/AppButton.vue';
import FrameSettings from './FrameSettings.vue';
import FrameView from '../../frame/FrameView.vue';
import * as Control from '../../../../src/tactic_stream/shared_ui/features/configuration/server_control.ui.mjs';
import { observeFrameSizes } from '../../frame/resize.js';
import { randomUuid } from '../../controls/identity.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/server.ui.mjs';
import { timestampFullLabel } from '../activity/activity.js';

export default {
  components: { FrameSettings, FrameView, AppIcon, AppButton },
  props: {
    ticket: { type: String, required: true },
    showDetails: Boolean,
    groupTitles: Array,
    workersOnly: Boolean
  },
  emits: ['session-expired'],
  data() {
    return {
      configuration: null,
      activeGroup: 'Services and workers',
      search: '',
      loading: false,
      saving: false,
      clientsLoading: false,
      clientsError: '',
      error: '',
      errorField: null,
      notice: '',
      draft: {},
      baseline: {},
      expanded: [],
      generation: 0,
      restarting: false,
      restartConfirm: false,
      controlWidth: 640
    };
  },
  computed: {
    dirty() {
      return this.hasChanges;
    },
    busy() {
      return this.loading || this.saving || this.restarting;
    },
    showControl() {
      return (
        !this.search &&
        this.groups.some((group) => group.title === 'Services and workers')
      );
    },
    controlScene() {
      return Control.describe(
        {
          workers: this.draft['services/process_count'],
          runtime: this.configuration?.runtime,
          dirty: this.hasChanges,
          busy: this.loading || this.saving,
          restarting: this.restarting,
          confirm: this.restartConfirm,
          notice: this.notice,
          error: this.error
        },
        this.controlWidth,
        appearance.language
      );
    },
    fields() {
      return UI.fields(
        {
          groups: this.groups.map((group) => ({
            ...group,
            settings: group.settings.filter(
              (setting) =>
                !this.showControl || setting.path !== 'services/process_count'
            )
          })),
          draft: this.draft,
          expanded: this.expanded,
          showDetails: this.showDetails,
          errorField: this.errorField
        },
        appearance.language
      );
    },
    frameValues() {
      const values = { ...this.draft };
      for (const group of this.groups)
        for (const setting of group.settings) {
          if (!setting.editable) values[setting.path] = this.value(setting);
          else if (setting.input_type === 'boolean')
            values[setting.path] = this.booleanValue(setting);
          if (setting.services)
            for (const service of setting.services)
              values[setting.path + '#' + service.name] = this.serviceEnabled(
                setting,
                service
              );
        }
      for (const field of this.fields)
        if (field.detailsText) values[field.field] = field.detailsText;
      return values;
    },
    changes() {
      return Object.fromEntries(
        Object.entries(this.draft).filter(
          ([path, value]) => value !== this.baseline[path]
        )
      );
    },
    hasChanges() {
      return Object.keys(this.changes).length > 0;
    },
    failedSetting() {
      return this.configuration?.groups
        .flatMap((group) => group.settings)
        .find((setting) => setting.path === this.errorField)?.label;
    },
    groups() {
      const query = this.search.trim().toLowerCase();
      return (this.configuration?.groups || [])
        .filter(
          (group) => !this.groupTitles || this.groupTitles.includes(group.title)
        )
        .filter((group) => query || group.title === this.activeGroup)
        .map((group) => ({
          ...group,
          settings: group.settings.filter((setting) =>
            [
              setting.path,
              t(setting.label),
              t(setting.description),
              t(group.title)
            ].some((value) => value.toLowerCase().includes(query))
          )
        }))
        .filter((group) => group.settings.length);
    }
  },
  watch: {
    ticket() {
      this.generation++;
      this.configuration = null;
      this.draft = {};
      this.baseline = {};
      this.expanded = [];
      this.loading = this.saving = this.clientsLoading = false;
      this.restarting = this.restartConfirm = false;
      this.error = this.notice = this.clientsError = '';
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
    this.load();
  },
  beforeUnmount() {
    this.generation++;
    this.controlObserver?.disconnect();
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  updated() {
    const element = this.$refs.serverControl;
    if (element === this.controlElement) return;
    this.controlObserver?.disconnect();
    this.controlElement = element;
    if (element) {
      this.controlObserver = observeFrameSizes((entries) => {
        this.controlWidth = entries.at(-1).contentRect.width;
      });
      this.controlObserver.observe(element);
    }
  },
  methods: {
    t,
    canLeave() {
      return !this.hasChanges && !this.busy;
    },
    async controlAction(action) {
      if (this.restarting || this.saving || this.loading) return;
      if (action.type === 'workers')
        this.editSetting('services/process_count', action.value);
      else if (action.type === 'save') await this.save();
      else if (action.type === 'discard') {
        this.resetDraft();
        await this.load();
      } else if (action.type === 'refresh' && !this.hasChanges)
        await this.load();
      else if (action.type === 'restart' && !this.hasChanges)
        this.restartConfirm = true;
      else if (action.type === 'reject') this.restartConfirm = false;
      else if (action.type === 'accept' && !this.hasChanges)
        await this.restart();
    },
    async restart() {
      const generation = this.generation;
      const runtime = this.configuration.runtime;
      const id = randomUuid();
      this.restartConfirm = false;
      this.restarting = true;
      this.error = this.notice = '';
      try {
        try {
          await restartServer(
            this.ticket,
            this.configuration.revision,
            runtime.instance_id,
            id
          );
        } catch (error) {
          if (!(error instanceof TypeError)) throw error;
          // A lost acknowledgement is checked by identity, never by resubmitting.
        }
        const deadline = performance.now() + 90000;
        while (generation === this.generation && performance.now() < deadline) {
          try {
            const state = await serverRuntime(this.ticket);
            if (state.restart_id === id && state.restart_error)
              throw Error(state.restart_error);
            if (
              state.restart_id === id &&
              state.instance_id !== runtime.instance_id &&
              state.state === 'running'
            ) {
              this.configuration = await serverConfiguration(this.ticket);
              this.resetDraft();
              this.notice = 'TACTIC Stream restarted';
              return;
            }
          } catch (error) {
            if (
              !(error instanceof TypeError) &&
              error.name !== 'TimeoutError' &&
              error.name !== 'AbortError'
            )
              throw error;
          }
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
        if (generation === this.generation)
          throw Error(
            'The server has not returned yet. Reconnect and check its status.'
          );
      } catch (error) {
        if (generation === this.generation) {
          if (error.code === 'authentication_failed')
            this.$emit('session-expired');
          this.error = error.message;
        }
      } finally {
        if (generation === this.generation) this.restarting = false;
      }
    },
    fieldEdited(action) {
      const setting = this.configuration.groups
        .flatMap((group) => group.settings)
        .find((setting) => setting.path === action.field);
      const value =
        setting.input_type === 'boolean'
          ? action.value
            ? 'true'
            : 'false'
          : setting.secret && !action.value
            ? null
            : action.value;
      this.editSetting(action.field, value);
    },
    action(action) {
      if (action.type === 'details')
        this.expanded = this.expanded.includes(action.path)
          ? this.expanded.filter((path) => path !== action.path)
          : [...this.expanded, action.path];
      else if (action.type === 'default' || action.type === 'clear')
        this.editSetting(action.path, '');
      else if (action.type === 'service') {
        const setting = this.configuration.groups
          .flatMap((group) => group.settings)
          .find((setting) => setting.path === action.path);
        this.editService(setting, action.name, action.value);
      }
    },
    groupHeading(title) {
      return (
        {
          'Services and workers': 'Processes and monitoring',
          Network: 'Connection',
          Database: 'Database connection',
          'File repository': 'Repository locations',
          'Task scheduling': 'Schedule',
          Security: 'Account and API security',
          'Directories and logs': 'Runtime paths'
        }[title] || title
      );
    },
    groupChanged(group) {
      return group.settings.some((setting) =>
        Object.hasOwn(this.changes, setting.path)
      );
    },
    beforeUnload(event) {
      if (!this.hasChanges && !this.saving) return;
      event.preventDefault();
      event.returnValue = '';
    },
    async load() {
      if (this.loading || this.saving || this.hasChanges) return;
      const generation = this.generation;
      this.loading = true;
      this.error = '';
      this.notice = '';
      try {
        const configuration = await serverConfiguration(this.ticket);
        if (generation !== this.generation) return;
        this.configuration = configuration;
        this.resetDraft();
      } catch (error) {
        if (generation !== this.generation) return;
        if (error.code === 'authentication_failed')
          this.$emit('session-expired');
        this.error =
          error instanceof TypeError
            ? 'Unable to reach the server.'
            : error.message;
      } finally {
        if (generation === this.generation) this.loading = false;
      }
    },
    resetDraft(groupTitles) {
      const previous = { ...this.draft };
      this.draft = {};
      for (const group of this.configuration.groups) {
        for (const setting of group.settings) {
          if (!setting.editable) continue;
          this.draft[setting.path] =
            setting.input_type === 'services'
              ? setting.services
                  .filter((service) => service.enabled)
                  .map((service) => service.name)
                  .join('|')
              : setting.secret
                ? null
                : (setting.value ?? '');
        }
      }
      this.baseline = { ...this.draft };
      if (groupTitles)
        for (const group of this.configuration.groups)
          if (!groupTitles.includes(group.title)) {
            for (const setting of group.settings)
              if (Object.hasOwn(previous, setting.path))
                this.draft[setting.path] = previous[setting.path];
          }
      this.error = '';
      this.errorField = null;
    },
    async refreshClients() {
      if (this.clientsLoading || this.loading || this.saving) return;
      const generation = this.generation;
      this.clientsLoading = true;
      this.clientsError = '';
      try {
        const result = await serverConfiguration(this.ticket);
        if (generation !== this.generation) return;
        this.configuration.event_clients = result.event_clients;
      } catch (error) {
        if (generation !== this.generation) return;
        if (error.code === 'authentication_failed')
          this.$emit('session-expired');
        this.clientsError =
          error instanceof TypeError
            ? 'Unable to reach the server.'
            : error.message;
      } finally {
        if (generation === this.generation) this.clientsLoading = false;
      }
    },
    connectedTime(value) {
      return timestampFullLabel(new Date(value).toISOString());
    },
    async save(groupTitles) {
      if (this.loading || this.saving || this.restarting) return false;
      const generation = this.generation;
      const changes = Object.fromEntries(
        Object.entries(this.changes).filter(
          ([path]) =>
            !groupTitles ||
            this.configuration.groups.some(
              (group) =>
                groupTitles.includes(group.title) &&
                group.settings.some((setting) => setting.path === path)
            )
        )
      );
      if (!Object.keys(changes).length) return true;
      const pending = { ...this.changes };
      this.saving = true;
      this.error = '';
      this.errorField = null;
      try {
        const configuration = await saveServerConfiguration(
          this.ticket,
          changes,
          this.configuration.revision
        );
        if (generation !== this.generation) return false;
        this.configuration = configuration;
        this.resetDraft();
        for (const [path, value] of Object.entries(pending))
          if (!Object.hasOwn(changes, path)) this.draft[path] = value;
        this.notice = this.configuration.restart_required
          ? 'Saved to XML. Restart the backend to apply these settings.'
          : this.configuration.saved
            ? 'Saved to XML. New requests use the updated settings.'
            : 'No configuration changes were needed.';
        return true;
      } catch (error) {
        if (generation !== this.generation) return false;
        if (error.code === 'authentication_failed')
          this.$emit('session-expired');
        this.error =
          error instanceof TypeError
            ? 'Unable to reach the server.'
            : error.message;
        this.errorField = error.field;
        const group = this.configuration.groups.find((group) =>
          group.settings.some((setting) => setting.path === error.field)
        );
        if (group) {
          this.activeGroup = group.title;
          this.search = '';
        }
        return false;
      } finally {
        if (generation === this.generation) this.saving = false;
      }
    },
    booleanValue(setting) {
      return (this.draft[setting.path] || setting.default) === 'true';
    },
    value(setting) {
      if (setting.secret)
        return t(setting.configured ? 'Configured (hidden)' : 'Not set');
      return setting.value ?? t('Not set');
    },
    serviceEnabled(setting, service) {
      return setting.editable
        ? this.draft[setting.path].split('|').includes(service.name)
        : service.enabled;
    },
    editService(setting, name, enabled) {
      const services = new Set(this.draft[setting.path].split('|'));
      if (enabled) services.add(name);
      else services.delete(name);
      this.editSetting(
        setting.path,
        ['tactic', 'queue', 'files']
          .filter((service) => services.has(service))
          .join('|')
      );
    },
    editSetting(path, value) {
      this.draft[path] = value;
      if (this.errorField === path) {
        this.error = '';
        this.errorField = null;
      }
    }
  }
};
</script>

<template>
  <section class="content server-configuration" :aria-busy="loading || saving">
    <p
      v-if="error && (!workersOnly || !configuration)"
      class="error"
      role="alert"
    >
      <strong v-if="failedSetting">{{ t(failedSetting) }}: </strong
      >{{ t(error) }}
    </p>
    <p
      v-if="notice && !hasChanges && !workersOnly"
      class="notice"
      role="status"
    >
      {{ t(notice) }}
    </p>
    <p v-if="loading" class="muted" role="status">{{ t('Loading data…') }}</p>
    <template v-if="configuration">
      <div
        v-if="showControl"
        ref="serverControl"
        class="server-process-controls"
        :style="{ height: controlScene.height + 'px', position: 'relative' }"
      >
        <FrameView :scene="controlScene" @event="controlAction" />
      </div>
      <section
        v-if="!workersOnly && activeGroup === 'Services and workers' && !search"
        class="settings-section event-clients"
      >
        <header>
          <h2>
            {{ t('SSE connections') }} ·
            {{ configuration.event_clients?.length || 0 }}
          </h2>
          <AppButton
            icon="refresh"
            label="Refresh connections"
            :disabled="clientsLoading || loading || saving"
            @click="refreshClients"
          />
        </header>
        <p class="muted">
          {{
            t(
              'Open SSE connections across all web workers. This is a connection list, not user presence. Refresh to update the snapshot; closed connections disappear within the collection interval, crashed workers within 45 seconds.'
            )
          }}
        </p>
        <p v-if="clientsError" class="error" role="alert">
          {{ t(clientsError) }}
        </p>
        <div class="event-clients-scroll">
          <table v-if="configuration.event_clients?.length">
            <thead>
              <tr>
                <th>{{ t('User') }}</th>
                <th>{{ t('Project') }}</th>
                <th>{{ t('Client') }}</th>
                <th>{{ t('Address') }}</th>
                <th>{{ t('Connected at') }}</th>
                <th>{{ t('Worker') }}</th>
                <th>{{ t('Subscriptions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="client in configuration.event_clients"
                :key="client.connection"
              >
                <td>{{ client.login }}</td>
                <td>{{ client.project }}</td>
                <td>{{ t(client.application) }}</td>
                <td>{{ client.address }}</td>
                <td>{{ connectedTime(client.connected_at) }}</td>
                <td>{{ client.worker }}</td>
                <td>
                  <details>
                    <summary>
                      {{ client.channels.join(', ') }} ·
                      {{ client.search_types.length }}
                    </summary>
                    <code>{{ client.search_types.join('\n') }}</code>
                  </details>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">{{ t('No open SSE connections') }}</p>
        </div>
      </section>
      <details v-if="showDetails && !workersOnly" class="configuration-source">
        <summary>{{ t('Configuration source') }}</summary>
        <button :disabled="loading || saving || hasChanges" @click="load">
          <AppIcon name="refresh" />{{ t('Refresh') }}
        </button>
        <span class="muted">{{ t('Configuration file') }}</span
        ><code>{{ configuration.config_path }}</code>
        <span class="muted">{{ t('Data directory') }}</span
        ><code>{{ configuration.data_dir }}</code>
        <p class="muted">
          {{
            t(
              'Supported settings can be saved to XML. Values come from the configuration file; startup overrides may differ.'
            )
          }}
        </p>
        <p v-if="!configuration.writable" class="muted">
          {{
            t(
              'The configuration file is missing or not writable. Editing is unavailable.'
            )
          }}
        </p>
      </details>
      <div v-if="!workersOnly" class="configuration-groups">
        <FrameSettings
          :fields="fields"
          :values="frameValues"
          :busy="loading || saving || restarting"
          natural
          @field="fieldEdited"
          @action="action"
        />
        <p v-if="!groups.length" class="muted">{{ t('No settings found') }}</p>
        <details
          v-if="configuration.undocumented.length"
          class="configuration-group"
        >
          <summary>
            {{ t('Other configured options') }} ·
            {{ configuration.undocumented.length }}
          </summary>
          <p class="muted">
            {{
              t(
                'These options still need documentation and a support check. Their values are not exposed.'
              )
            }}
          </p>
          <ul>
            <li v-for="path in configuration.undocumented" :key="path">
              <code>{{ path }}</code>
            </li>
          </ul>
        </details>
      </div>
    </template>
  </section>
</template>

<style>
.event-clients > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.event-clients-scroll {
  max-height: 320px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.event-clients-scroll table {
  width: 100%;
}
.event-clients-scroll th,
.event-clients-scroll td {
  text-align: left;
  padding: 8px;
  white-space: nowrap;
}
.event-clients-scroll code {
  white-space: pre;
  display: block;
}
</style>

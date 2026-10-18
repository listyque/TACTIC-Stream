<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import AppearanceControls from '../configuration/AppearanceControls.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppButton from '../../controls/AppButton.vue';
import AppSelect from '../../controls/AppSelect.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import ApiParameter from './ApiParameter.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/documentation/api.ui.mjs';
import CodeBlock from '../../controls/CodeBlock.vue';
import { copyText } from '../../controls/clipboard.js';

const methodNav = ref(null),
  navWidth = ref(240);
let observer;
let alive = true;
const catalogRequest = new AbortController();
onBeforeUnmount(() => {
  alive = false;
  catalogRequest.abort();
  observer?.disconnect();
  token.value = '';
  password.value = '';
});
const catalog = ref(null);
const error = ref('');
const search = ref('');
const status = ref('common');
const selected = ref('query');
const argumentsText = ref('[]');
const keywordsText = ref('{}');
const project = ref('');
const login = ref('');
const password = ref('');
const token = ref('');
const authenticatedLogin = ref('');
const busy = ref(false);
const result = ref(null);
const elapsed = ref(null);
const responseError = ref(false);
const copied = ref(false);
const exampleIndex = ref(0);
const rawMode = ref(false);
const parameterDrafts = ref({});
const parameterErrors = ref({});
const statuses = [
  { value: 'common', label: 'Common methods' },
  { value: 'available', label: 'Available entry points' },
  { value: 'all', label: 'All methods' },
  { value: 'not_implemented', label: 'Not migrated' },
  { value: 'excluded', label: 'Excluded' }
];
const parameterHelp = {
  search_type: {
    label: 'Search type',
    description:
      'Object type to read, for example sthpw/project or your_project/asset.'
  },
  search_key: {
    label: 'Search key',
    description: 'Copy __search_key__ from a query result.'
  },
  limit: {
    label: 'Maximum records',
    description: 'Limit the number of records returned by this request.'
  },
  offset: {
    label: 'Skip records',
    description: 'Number of records to skip before starting this page.'
  },
  filters: {
    label: 'Filters',
    description: 'Use [] for all records, or pairs such as [["code", "admin"]].'
  },
  columns: {
    label: 'Columns',
    description: 'Use null for all columns, or a list such as ["code", "name"].'
  },
  order_bys: {
    label: 'Sort order',
    description: 'A list such as ["id asc"] or ["name desc"].'
  },
  data: {
    label: 'Object data',
    description: 'A JSON object containing field names and their new values.'
  }
};
try {
  login.value = localStorage.getItem('tactic_stream.lastLogin') || '';
  const session = JSON.parse(localStorage.getItem('tactic_stream.session'));
  if (typeof session?.project === 'string') project.value = session.project;
  if (typeof session?.ticket === 'string') token.value = session.ticket;
  if (typeof session?.login === 'string') {
    login.value = session.login;
    authenticatedLogin.value = session.login;
  }
} catch {
  /* Anonymous reference remains usable without browser storage. */
}

const methods = computed(() =>
  UI.methods(
    catalog.value?.methods,
    status.value,
    search.value,
    appearance.language
  )
);
const method = computed(() =>
  catalog.value?.methods.find((item) => item.name === selected.value)
);
const methodOptions = computed(() =>
  methods.value.map((item) => ({ value: item.name, label: item.name }))
);
const methodHelp = computed(
  () =>
    method.value?.help?.[appearance.language] || method.value?.help?.en || ''
);
const hasTicket = computed(() =>
  method.value?.parameters.some((item) => item.name === 'ticket')
);
const example = computed(() => method.value?.examples?.[exampleIndex.value]);
const exampleOptions = computed(() =>
  (method.value?.examples || []).map((item, index) => ({
    value: String(index),
    label: item.label
  }))
);
const parameters = computed(() => {
  if (!requestPreview.value) return [];
  const args = JSON.parse(argumentsText.value);
  const kwargs = JSON.parse(keywordsText.value);
  return (method.value?.parameters || [])
    .filter((item) => item.name !== 'ticket')
    .map((item, index) => {
      const value =
        index < args.length
          ? args[index]
          : Object.hasOwn(kwargs, item.name)
            ? kwargs[item.name]
            : item.default_value;
      const type =
        typeof value === 'boolean'
          ? 'boolean'
          : typeof value === 'number' || ['limit', 'offset'].includes(item.name)
            ? 'number'
            : Array.isArray(value) ||
                (value !== null && typeof value === 'object') ||
                [
                  'filters',
                  'columns',
                  'order_bys',
                  'data',
                  'kwargs',
                  'values',
                  'search_keys'
                ].includes(item.name)
              ? 'json'
              : item.name.includes('password')
                ? 'password'
                : 'text';
      return {
        ...item,
        index,
        type,
        label: parameterHelp[item.name]?.label || item.name,
        description: parameterHelp[item.name]?.description || '',
        value: Object.hasOwn(parameterDrafts.value, item.name)
          ? parameterDrafts.value[item.name]
          : type === 'json'
            ? JSON.stringify(value ?? null)
            : (value ?? '')
      };
    });
});
const mainParameters = computed(() =>
  parameters.value.filter(
    (item) => item.required || ['filters', 'limit'].includes(item.name)
  )
);
const extraParameters = computed(() =>
  parameters.value.filter((item) => !mainParameters.value.includes(item))
);
const parameterGroups = computed(() => [
  { extra: false, fields: mainParameters.value },
  { extra: true, fields: extraParameters.value }
]);
const endpoint = computed(
  () => `${location.origin}/tactic/${encodeURIComponent(project.value)}/Api/`
);
const requestPreview = computed(() => {
  try {
    const args = JSON.parse(argumentsText.value);
    const kwargs = JSON.parse(keywordsText.value);
    if (
      !Array.isArray(args) ||
      !kwargs ||
      typeof kwargs !== 'object' ||
      Array.isArray(kwargs)
    )
      return null;
    return {
      method: selected.value,
      args: hasTicket.value
        ? [
            { ticket: '<ticket>', project: project.value, language: 'python' },
            ...args
          ]
        : args,
      kwargs
    };
  } catch {
    return null;
  }
});
const xmlrpcExample = computed(() => {
  if (
    !requestPreview.value ||
    !method.value ||
    method.value.status !== 'available'
  )
    return '';
  const values = [];
  let index = 0;
  for (const parameter of method.value.parameters) {
    if (parameter.name === 'ticket') continue;
    values.push(
      index < requestPreview.value.args.length - (hasTicket.value ? 1 : 0)
        ? requestPreview.value.args[index++ + (hasTicket.value ? 1 : 0)]
        : Object.hasOwn(requestPreview.value.kwargs, parameter.name)
          ? requestPreview.value.kwargs[parameter.name]
          : parameter.required
            ? `<${parameter.name}>`
            : parameter.default_value
    );
  }
  const auth = method.value.requires_ticket
    ? `token = api.get_ticket(${JSON.stringify(login.value)}, getpass('Password: '))\nticket = {'ticket': token, 'project': ${JSON.stringify(project.value)}, 'language': 'python'}\n`
    : '';
  return `import json\nfrom getpass import getpass\nfrom xmlrpc.client import ServerProxy\n\napi = ServerProxy(${JSON.stringify(endpoint.value)}, allow_none=True)\n${auth}args = json.loads(${JSON.stringify(JSON.stringify(values))})\nresult = api.${selected.value}(${hasTicket.value ? (method.value.requires_ticket ? 'ticket, ' : 'None, ') : ''}*args)\nprint(result)`;
});

function choose(name, index = 0) {
  if (busy.value) return;
  selected.value = name;
  exampleIndex.value = index;
  const preset = method.value?.examples?.[index] || method.value?.example;
  argumentsText.value = JSON.stringify(preset?.args || [], null, 2);
  keywordsText.value = JSON.stringify(preset?.kwargs || {}, null, 2);
  rawMode.value = false;
  parameterDrafts.value = {};
  parameterErrors.value = {};
  error.value = '';
  result.value = null;
  elapsed.value = null;
  responseError.value = false;
  copied.value = false;
  history.replaceState(null, '', `#${encodeURIComponent(name)}`);
}

function editParameter(parameter, value) {
  parameterDrafts.value[parameter.name] = value;
  try {
    const parsed =
      parameter.type === 'json'
        ? JSON.parse(value)
        : parameter.type === 'number'
          ? value === ''
            ? null
            : Number(value)
          : value;
    if (
      parameter.type === 'number' &&
      parsed !== null &&
      !Number.isFinite(parsed)
    )
      throw new Error();
    const args = JSON.parse(argumentsText.value);
    const kwargs = JSON.parse(keywordsText.value);
    if (parameter.index < args.length) args[parameter.index] = parsed;
    else kwargs[parameter.name] = parsed;
    argumentsText.value = JSON.stringify(args, null, 2);
    keywordsText.value = JSON.stringify(kwargs, null, 2);
    delete parameterErrors.value[parameter.name];
    error.value = '';
  } catch {
    parameterErrors.value[parameter.name] =
      parameter.type === 'number'
        ? 'Enter a number.'
        : 'Enter valid JSON for this field.';
  }
}

async function signIn() {
  busy.value = true;
  error.value = '';
  token.value = '';
  authenticatedLogin.value = '';
  try {
    const ticket = await rpc('get_ticket', [login.value, password.value]);
    if (!alive) return;
    token.value = ticket;
    authenticatedLogin.value = login.value;
  } catch (failure) {
    if (alive) error.value = failure.message;
  } finally {
    password.value = '';
    if (alive) busy.value = false;
  }
}

async function run() {
  result.value = null;
  responseError.value = false;
  if (!rawMode.value && Object.keys(parameterErrors.value).length) {
    error.value = 'Correct the highlighted fields before running the request.';
    return;
  }
  if (!requestPreview.value) {
    error.value =
      'Arguments must be a JSON array and keyword arguments a JSON object.';
    return;
  }
  error.value = '';
  busy.value = true;
  const started = performance.now();
  try {
    const args = JSON.parse(argumentsText.value);
    if (hasTicket.value)
      args.unshift({
        ticket: token.value,
        project: project.value,
        language: 'python'
      });
    const reply = await rpc(
      selected.value,
      args,
      JSON.parse(keywordsText.value)
    );
    if (!alive) return;
    result.value = JSON.stringify(reply, null, 2);
  } catch (failure) {
    if (!alive) return;
    if (failure.code === 'authentication_failed') {
      token.value = '';
      authenticatedLogin.value = '';
    }
    responseError.value = true;
    result.value = JSON.stringify(
      {
        status: failure.status || null,
        code: failure.code || null,
        error: failure.message
      },
      null,
      2
    );
  } finally {
    if (alive) {
      elapsed.value = (performance.now() - started).toFixed(1);
      busy.value = false;
    }
  }
}

async function copyExample() {
  try {
    await copyText(xmlrpcExample.value);
    if (alive) copied.value = true;
  } catch {
    if (alive) error.value = 'Select and copy the example text manually.';
  }
}

onMounted(async () => {
  try {
    const response = await fetch('/api/documentation', {
      cache: 'no-store',
      signal: catalogRequest.signal
    });
    if (!response.ok) throw new Error('Unable to load API documentation.');
    const loaded = await response.json();
    if (!alive) return;
    catalog.value = loaded;
    const name = decodeURIComponent(location.hash.slice(1));
    choose(
      catalog.value.methods.some((item) => item.name === name) ? name : 'query'
    );
    await nextTick();
    if (!alive) return;
    observer = observeFrameSizes(
      () => (navWidth.value = methodNav.value.clientWidth)
    );
    observer.observe(methodNav.value);
  } catch (failure) {
    if (alive) error.value = failure.message;
  }
});
</script>

<template>
  <div class="api-docs">
    <header class="api-docs-header">
      <strong
        ><AppIcon name="code" /><span>{{
          t('TACTIC API reference')
        }}</span></strong
      ><a href="/">{{ t('Workspace') }}</a
      ><AppearanceControls compact />
    </header>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <div v-if="catalog" class="api-docs-layout">
      <aside class="api-docs-navigation">
        <label
          >{{ t('Find a method')
          }}<input
            v-model="search"
            type="search"
            :aria-label="t('Find a method')"
        /></label>
        <label
          >{{ t('Method status')
          }}<AppSelect
            v-model="status"
            :options="statuses"
            label="Method status"
        /></label>
        <small class="muted">{{
          t('{count} methods', { count: methods.length })
        }}</small>
        <AppSelect
          class="api-docs-mobile-picker"
          :model-value="selected"
          :options="methodOptions"
          label="API method"
          @update:model-value="choose($event)"
        />
        <nav
          ref="methodNav"
          class="api-docs-methods"
          :aria-label="t('API methods')"
        >
          <FrameView
            v-for="item in methods"
            :key="item.name"
            class="api-method-record"
            :style="{
              height:
                UI.method(
                  item,
                  selected,
                  status === 'common',
                  navWidth,
                  appearance.language
                ).height + 'px'
            }"
            :scene="
              UI.method(
                item,
                selected,
                status === 'common',
                navWidth,
                appearance.language
              )
            "
            @event="(action) => choose(action.name)"
          />
        </nav>
      </aside>
      <main v-if="method" class="api-docs-content">
        <header class="content-heading">
          <div>
            <h1>{{ method.name }}</h1>
          </div>
          <label
            >{{ t('Project')
            }}<input
              v-model="project"
              :disabled="busy"
              :aria-label="t('Project')"
          /></label>
        </header>
        <section class="configuration-group api-method-heading">
          <p v-if="methodHelp" class="api-method-help">{{ methodHelp }}</p>
          <strong>{{ t('Method call and inputs') }}</strong>
          <CodeBlock
            class="api-signature"
            :code="'api.' + method.name + method.signature"
          />
          <p class="muted">
            {{
              t(
                'The signature lists input names and their defaults. Parameters without a default are required. Fill in the fields below; the console adds your ticket after sign-in.'
              )
            }}
          </p>
        </section>
        <details class="configuration-group api-reference">
          <summary>{{ t('Original TACTIC reference') }}</summary>
          <p class="muted">
            {{
              t(
                'Imported API/SDK documentation describes the original contract, including behavior that may not be migrated.'
              )
            }}
          </p>
          <pre>{{
            method.reference || t('The original method has no description.')
          }}</pre>
        </details>
        <p v-if="method.status !== 'available'" class="muted">
          {{
            t(
              method.status === 'excluded'
                ? 'Excluded from this project.'
                : 'This method has not been migrated.'
            )
          }}
        </p>
        <p v-else class="muted">
          {{ t('Entry point available; full legacy parity is not verified.') }}
        </p>
        <p v-if="method.writes" class="notice">
          {{ t('This method can change data.') }}
        </p>
        <p v-if="method.reason" class="muted">{{ method.reason }}</p>
        <details
          v-if="method.requires_ticket"
          class="configuration-group api-connection"
          :open="!token"
        >
          <summary>
            {{
              token
                ? t('Signed in as {login}', {
                    login: authenticatedLogin || login
                  })
                : t('Sign in to try the examples')
            }}
          </summary>
          <form class="api-docs-login" @submit.prevent="signIn">
            <label
              >{{ t('Login')
              }}<input
                v-model="login"
                autocomplete="username"
                :disabled="busy" /></label
            ><label
              >{{ t('Password')
              }}<input
                v-model="password"
                type="password"
                autocomplete="current-password"
                :disabled="busy" /></label
            ><AppButton
              type="submit"
              icon="user"
              label="Sign in"
              :disabled="busy || !password"
            />
          </form>
          <p class="muted">
            {{
              t(
                token
                  ? 'Ticket loaded. The server checks access on every call.'
                  : 'Sign in to run methods that require a ticket.'
              )
            }}
          </p>
        </details>
        <section class="configuration-group">
          <h2>{{ t('Try the method') }}</h2>
          <p class="muted">
            {{ t('Choose an example, adjust the fields and run the request.') }}
          </p>
          <label v-if="exampleOptions.length"
            >{{ t('Ready example')
            }}<AppSelect
              :model-value="String(exampleIndex)"
              :options="exampleOptions"
              :disabled="busy"
              label="Ready example"
              @update:model-value="choose(selected, Number($event))"
          /></label>
          <p v-if="example" class="muted">{{ t(example.description) }}</p>
          <form @submit.prevent="run">
            <template v-if="!rawMode">
              <component
                v-for="group in parameterGroups"
                :key="String(group.extra)"
                :is="group.extra ? 'details' : 'div'"
                v-show="group.fields.length"
                class="api-parameters"
              >
                <summary v-if="group.extra">{{ t('More parameters') }}</summary>
                <div v-for="field in group.fields" :key="field.name">
                  <ApiParameter
                    :field="{ ...field, error: parameterErrors[field.name] }"
                    :busy="busy"
                    @change="editParameter(field, $event)"
                  />
                  <small
                    ><code>{{ field.name }}</code> ·
                    {{
                      t(field.required ? 'Required input' : 'Optional input')
                    }}</small
                  >
                  <small
                    v-if="parameterErrors[field.name]"
                    class="error"
                    role="alert"
                    >{{ t(parameterErrors[field.name]) }}</small
                  >
                </div>
              </component>
              <p v-if="!parameters.length" class="muted">
                {{ t('This method needs no arguments.') }}
              </p>
            </template>
            <details :open="rawMode" @toggle="rawMode = $event.target.open">
              <summary>{{ t('Raw JSON') }}</summary>
              <label
                >{{ t('Positional arguments (without ticket)')
                }}<textarea
                  v-model="argumentsText"
                  rows="5"
                  :disabled="busy"
                  :aria-label="t('Positional arguments (without ticket)')"
                  spellcheck="false"
                  @input="
                    parameterDrafts = {};
                    parameterErrors = {};
                  "
                ></textarea>
              </label>
              <label
                >{{ t('Keyword arguments')
                }}<textarea
                  v-model="keywordsText"
                  rows="3"
                  :disabled="busy"
                  :aria-label="t('Keyword arguments')"
                  spellcheck="false"
                  @input="
                    parameterDrafts = {};
                    parameterErrors = {};
                  "
                ></textarea>
              </label>
            </details>
            <AppButton
              type="submit"
              highlighted
              icon="code"
              :label="
                busy
                  ? 'Running…'
                  : method.writes
                    ? 'Run write method'
                    : 'Run method'
              "
              :disabled="
                busy ||
                method.status !== 'available' ||
                (method.requires_ticket && !token)
              "
            />
          </form>
          <p v-if="elapsed !== null" class="muted">
            {{ t('HTTP round trip: {duration} ms', { duration: elapsed }) }}
          </p>
          <strong v-if="result !== null">{{ t('Method response') }}</strong>
          <pre
            v-if="result !== null"
            class="api-result"
            :class="{ error: responseError }"
            role="status"
            tabindex="0"
            :aria-label="t('Method response')"
            >{{ result }}</pre
          >
        </section>
        <details v-if="xmlrpcExample" class="configuration-group">
          <summary>{{ t('Python XML-RPC example') }}</summary>
          <p class="muted">
            {{
              t(
                'This Python example follows the fields above. Copy it into a script and enter your password when prompted.'
              )
            }}
          </p>
          <AppButton
            icon="copy"
            :label="copied ? 'Copied' : 'Copy example'"
            @click="copyExample"
          /><CodeBlock :code="xmlrpcExample" />
        </details>
        <details class="configuration-group">
          <summary>{{ t('All parameters and defaults') }}</summary>
          <code class="api-signature"
            >{{ method.name }}{{ method.signature }}</code
          >
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('Parameter') }}</th>
                  <th>{{ t('Required') }}</th>
                  <th>{{ t('Default') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="parameter in method.parameters"
                  :key="parameter.name"
                >
                  <td>
                    <code>{{ parameter.name }}</code>
                  </td>
                  <td>{{ t(parameter.required ? 'Yes' : 'No') }}</td>
                  <td>
                    <code>{{ parameter.default ?? '—' }}</code>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <details v-if="method.signature !== method.original_signature">
            <summary>{{ t('Original signature') }}</summary>
            <code class="api-signature"
              >{{ method.name }}{{ method.original_signature }}</code
            >
          </details>
        </details>
        <details class="configuration-group">
          <summary>{{ t('JSON request') }}</summary>
          <code>{{ catalog.json_route }}</code>
          <pre>{{ JSON.stringify(requestPreview, null, 2) }}</pre>
        </details>
        <details class="configuration-group">
          <summary>{{ t('Connection and technical details') }}</summary>
          <code class="api-signature">{{ endpoint }}</code>
          <p class="muted">
            {{
              t(
                'XML-RPC and this console use the same server logic, authorization and data. The console sends JSON; XML-RPC retains its original response formats.'
              )
            }}
          </p>
          <p class="muted">
            {{
              t(
                'XML-RPC faults use these codes. JSON returns HTTP status with error and error_code.'
              )
            }}
          </p>
          <pre>{{
            JSON.stringify(
              { 'XML-RPC': catalog.xmlrpc_errors, JSON: catalog.json_errors },
              null,
              2
            )
          }}</pre>
          <a href="/openapi.json">{{ t('HTTP transport schema (OpenAPI)') }}</a
          ><a href="/api/documentation">{{ t('Method catalog (JSON)') }}</a
          ><a href="/api/compatibility">{{
            t('Compatibility inventory (JSON)')
          }}</a>
        </details>
      </main>
    </div>
  </div>
</template>

<style>
.api-method-record {
  position: relative;
  margin-bottom: 4px;
}
</style>

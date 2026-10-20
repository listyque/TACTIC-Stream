<script setup>
import { computed, ref, nextTick, provide } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import TableView from '../../frontend/src/features/interface/TableView.vue';
import NestedTable from '../../frontend/src/features/interface/NestedTable.vue';
import TableCell from '../../frontend/src/features/interface/TableCell.vue';
import TableServiceDialogs from '../../frontend/src/features/interface/TableServiceDialogs.vue';
import TableDocument from '../../frontend/src/features/interface/TableDocument.vue';
import TableInlineEditor from '../../frontend/src/features/interface/TableInlineEditor.vue';
import ObjectCheckinForm from '../../frontend/src/features/checkin/ObjectCheckinForm.vue';
import { t } from '../../frontend/src/i18n.js';
const fixture = ref(null),
  data = ref(null),
  state = ref({}),
  selected = ref([]),
  events = ref([]),
  editor = ref(null),
  inline = ref(null),
  serviceDialogs = ref(null),
  tableDocument = ref(null),
  documentModel = ref({});
provide('openHelp', (topic) => events.value.push({ type: 'help', topic }));
Object.assign(appearance, {
  clickAnimations: false,
  hoverAnimations: false,
  fadeAnimations: false,
  popupAnimations: false
});
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
const columns = computed(() =>
  (data.value?.definition.table.elements || []).map((column) => ({
    ...column,
    field: column.cell.field,
    kind: column.cell.kind,
    supported: column.cell.supported,
    sortField: column.cell.sort_field,
    sortable: column.cell.sortable,
    editable: column.cell.editable,
    width: Number(column.attributes.width),
    hideOrder: Number(column.attributes.th_hide_order || 0),
    dataType: data.value.definition.columns[column.cell.field]?.data_type || ''
  }))
);
function selection(rows, enabled) {
  const keys = new Set(selected.value);
  for (const record of rows)
    enabled
      ? keys.add(record.__search_key__)
      : keys.delete(record.__search_key__);
  selected.value = [...keys];
}
window.tableFixture = {
  async openDocument(model) {
    documentModel.value = model;
    await nextTick();
    tableDocument.value.open();
  },
  closeDocument: () => tableDocument.value.close(),
  confirm: (message, options) => serviceDialogs.value.ask(message, options),
  cancelConfirmation: () => serviceDialogs.value.close(),
  async show(value, source) {
    inline.value?.close();
    editor.value = null;
    data.value = source;
    fixture.value = value;
    state.value = {};
    selected.value = [source.records[2].__search_key__];
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language
    });
    await nextTick();
    await document.fonts.ready;
    if (value.screen === 'inline') {
      const mode = value.mode;
      const name =
        mode === 'tags'
          ? 'keywords'
          : mode === 'multiline'
            ? 'description'
            : 'value';
      const className = {
        text: 'pyasm.widget.input_wdg.TextWdg',
        tags: 'pyasm.widget.input_wdg.TextWdg',
        multiline: 'pyasm.widget.input_wdg.TextAreaWdg',
        select: 'pyasm.widget.input_wdg.SelectWdg',
        bool: 'pyasm.widget.input_wdg.CheckboxWdg',
        date: 'tactic.ui.widget.calendar_wdg.CalendarInputWdg',
        datetime: 'tactic.ui.widget.calendar_wdg.CalendarInputWdg',
        color: 'tactic.ui.input.color_input_wdg.ColorInputWdg'
      }[mode];
      const options = value.descriptor.fieldOptions || [];
      editor.value = {
        plans: [{}, {}],
        field: {
          name,
          title: value.descriptor.fieldName,
          class_name: className,
          values: [value.descriptor.fieldValue],
          choices: options.map((item) => item.value),
          labels: options.map((item) => item.label),
          input: {
            value: value.descriptor.fieldValue,
            type: mode === 'datetime' ? 'datetime-local' : 'date'
          }
        }
      };
      await nextTick();
      await inline.value.open({
        left: 0,
        top: 0,
        bottom: 0,
        width: value.width + 8,
        height: 44
      });
    }
    await nextTick();
  },
  events,
  state,
  selected
};
</script>

<template>
  <main
    v-if="fixture"
    id="table-fixture"
    tabindex="-1"
    :style="{ width: fixture.width + 'px', height: fixture.height + 'px' }"
  >
    <TableServiceDialogs ref="serviceDialogs" />
    <TableDocument ref="tableDocument" :model="documentModel" />
    <NestedTable v-if="fixture.screen === 'nested'" :state="fixture.model" />
    <ObjectCheckinForm
      v-else-if="fixture.screen === 'append'"
      :model="{ ...fixture.model, error: t(fixture.model.error) }"
      :files="fixture.files"
      @event="events.push($event)"
    />
    <TableView
      v-else-if="fixture.screen === 'table'"
      :columns="columns"
      :groups="[{ key: 'all', label: '', records: data.records }]"
      :selected-keys="selected"
      selectable
      editable
      :state="state"
      sort-field="name"
      sort-direction="asc"
      group-mode="none"
      :views="[{ view: 'table', title: 'table', current: true }]"
      :accent="data.accent"
      @state="state = $event"
      @select="selection"
      @inspect="events.push({ type: 'inspect', value: $event })"
      @sort="events.push({ type: 'sort', value: $event })"
      @header-action="events.push({ type: 'header-action', value: $event })"
    >
      <template #cell="{ record, column, height }">
        <TableCell
          :element="column"
          :record="record"
          :cell="data.cells[record.__search_key__]?.[column.name]"
          :height="height"
          :accent="data.accent"
          :data-type="column.dataType"
          editable
          @action="events.push({ type: 'action', value: $event })"
        />
      </template>
    </TableView>
    <div
      v-else-if="fixture.screen === 'cell'"
      class="handler-table-cell cell-example"
    >
      <TableCell
        :element="{
          name: 'value',
          title: 'Value',
          field: 'value',
          supported: true,
          cell: { kind: fixture.value.kind }
        }"
        :record="{}"
        :cell="fixture.value.cell"
        :height="fixture.height"
        editable
        @notes="
          (cell, process) => events.push({ type: 'notes', cell, process })
        "
        @tasks="(cell, task) => events.push({ type: 'tasks', cell, task })"
        @action="(name, cell) => events.push({ type: 'action', name, cell })"
        @task-edit="
          (cell, task, field) =>
            events.push({ type: 'task-edit', cell, task, field })
        "
      />
    </div>
    <TableInlineEditor
      v-else
      ref="inline"
      :editor="editor"
      @save="events.push({ type: 'save', value: $event })"
      @cancel="events.push({ type: 'cancel' })"
    />
  </main>
</template>

<style>
html,
body,
#app {
  margin: 0;
  min-width: 0;
}
#table-fixture {
  display: flex;
  overflow: hidden;
  background: var(--page);
  color: var(--on-surface);
}
.cell-example {
  width: 100%;
  height: 100%;
}
</style>

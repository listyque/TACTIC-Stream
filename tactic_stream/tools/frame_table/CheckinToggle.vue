<script>
import App from '../../frontend/src/App.vue';
import DockWorkspace from '../../frontend/src/features/workspace/DockWorkspace.vue';
import TableCell from '../../frontend/src/features/interface/TableCell.vue';
import {
  appearance,
  initializeAppearance
} from '../../frontend/src/appearance.js';
Object.assign(appearance, {
  mode: 'dark',
  clickAnimations: false,
  hoverAnimations: false,
  popupAnimations: false
});
initializeAppearance();
export default {
  components: {
    DockWorkspace,
    TableCell,
    PlateModel: {
      props: ['draft'],
      emits: ['leave', 'clear'],
      methods: {
        canLeave() {
          this.$emit('leave');
          return this.draft.length === 0;
        },
        clear() {
          this.$emit('clear');
        }
      },
      render: () => null
    }
  },
  provide: App.provide,
  data: () => ({
    canAdminister: true,
    tableCheckinTarget: null,
    record: { __search_key__: 'demo/asset?code=A', code: 'A', name: 'Robot' },
    cell: { available: true, process: 'model', context: 'model/review' },
    draft: [],
    clears: 0,
    leaveChecks: 0
  }),
  methods: {
    openTableCheckin: App.methods.openTableCheckin,
    activate() {
      return App.provide
        .call(this)
        .openTableCheckin(this.record, this.cell, 'demo');
    }
  },
  mounted() {
    this.$refs.docks.hide('drop_plate');
    window.checkinToggle = this;
  }
};
</script>
<template>
  <main>
    <PlateModel
      ref="dropPlate"
      :draft="draft"
      @leave="leaveChecks++"
      @clear="
        clears++;
        draft = [];
      "
    />
    <div class="checkin-cell">
      <TableCell
        :element="{
          name: 'checkin',
          supported: true,
          cell: { kind: 'checkin' }
        }"
        :record="record"
        :cell="cell"
        editable
        @action="activate"
      />
    </div>
    <DockWorkspace
      ref="docks"
      login="checkin-toggle-fixture"
      results-active
      can-administer
    />
    <Teleport defer to="#dock-drop_plate"
      ><div class="draft">{{ draft.join(', ') || 'Drop Plate' }}</div></Teleport
    >
  </main>
</template>
<style scoped>
main {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.checkin-cell {
  flex: 0 0 58px;
  width: 100px;
  position: relative;
}
.dock-workspace {
  flex: 1;
  min-height: 0;
}
</style>

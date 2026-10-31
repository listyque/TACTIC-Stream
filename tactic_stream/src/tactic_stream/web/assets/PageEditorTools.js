import { G as withCtx, M as openBlock, X as ref, _ as createElementBlock, b as createVNode, p as computed } from "./vue.js";
import { R as button, U as rect, k as _sfc_main$2, r as _sfc_main$1 } from "./resize.js";
import { _t as _sfc_main$3 } from "./ConfiguredView.js";
//#region src/features/administration/PageEditorTools.vue
var _sfc_main = {
	__name: "PageEditorTools",
	props: { frameNode: {
		type: Object,
		required: true
	} },
	emits: ["command"],
	setup(__props) {
		const props = __props;
		const menu = ref(null), anchor = ref(null);
		const trigger = computed(() => ({ nodes: [button("pageEditorToolsButton", rect(0, 0, props.frameNode.width, props.frameNode.height), props.frameNode.label, "more", { type: "menu" }, true)] }));
		function toggle(_action, source) {
			anchor.value = source;
			if (menu.value.open) menu.value.close(true);
			else {
				const bounds = source.getBoundingClientRect();
				menu.value.openAt({
					clientX: bounds.left,
					clientY: bounds.bottom,
					target: source
				});
			}
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", null, [createVNode(_sfc_main$1, {
				scene: trigger.value,
				onEvent: toggle
			}, null, 8, ["scene"]), createVNode(_sfc_main$2, {
				ref_key: "menu",
				ref: menu,
				anchor: anchor.value,
				label: __props.frameNode.label,
				"external-trigger": "",
				overlay: ""
			}, {
				default: withCtx(() => [createVNode(_sfc_main$3, {
					actions: __props.frameNode.actions,
					onTriggered: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("command", $event))
				}, null, 8, ["actions"])]),
				_: 1
			}, 8, ["anchor", "label"])]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=PageEditorTools.js.map
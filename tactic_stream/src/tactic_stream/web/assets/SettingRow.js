import { F as renderSlot, N as openBlock, X as ref, _ as createCommentVNode, et as unref, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, rt as toDisplayString, tt as normalizeClass, v as createElementBlock } from "./vue.js";
import { D as t } from "./index.js";
//#region src/controls/SettingRow.vue
var _hoisted_1 = { class: "setting-description" };
var _hoisted_2 = ["for"];
var _hoisted_3 = { key: 0 };
var _hoisted_4 = ["id"];
var _sfc_main = {
	__name: "SettingRow",
	props: {
		controlId: String,
		title: String,
		description: String,
		path: String,
		showDivider: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		const root = ref(null), accessory = ref(null), stacked = ref(false);
		let observer;
		onMounted(() => {
			observer = new ResizeObserver(() => {
				stacked.value = root.value.clientWidth - 28 - accessory.value.scrollWidth < 210;
			});
			observer.observe(root.value);
			observer.observe(accessory.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "root",
				ref: root,
				class: normalizeClass(["settings-row configuration-setting", {
					stacked: stacked.value,
					"no-divider": !__props.showDivider
				}])
			}, [createBaseVNode("div", _hoisted_1, [
				createBaseVNode("label", { for: __props.controlId }, [createBaseVNode("strong", null, toDisplayString(unref(t)(__props.title)), 1)], 8, _hoisted_2),
				__props.path ? (openBlock(), createElementBlock("code", _hoisted_3, toDisplayString(__props.path), 1)) : createCommentVNode("", true),
				__props.description ? (openBlock(), createElementBlock("p", {
					key: 1,
					id: __props.controlId + "-help",
					class: "muted"
				}, toDisplayString(unref(t)(__props.description)), 9, _hoisted_4)) : createCommentVNode("", true),
				renderSlot(_ctx.$slots, "description")
			]), createBaseVNode("div", {
				ref_key: "accessory",
				ref: accessory,
				class: "setting-control"
			}, [renderSlot(_ctx.$slots, "default")], 512)], 2);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=SettingRow.js.map
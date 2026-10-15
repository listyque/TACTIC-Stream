import { F as renderSlot, N as openBlock, _ as createCommentVNode, et as unref, h as createBaseVNode, rt as toDisplayString, v as createElementBlock } from "./vue.js";
import { D as t } from "./index.js";
//#region src/controls/SettingRow.vue
var _hoisted_1 = { class: "settings-row configuration-setting" };
var _hoisted_2 = { class: "setting-description" };
var _hoisted_3 = ["for"];
var _hoisted_4 = { key: 0 };
var _hoisted_5 = ["id"];
var _hoisted_6 = { class: "setting-control" };
var _sfc_main = {
	__name: "SettingRow",
	props: {
		controlId: String,
		title: String,
		description: String,
		path: String
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1, [createBaseVNode("div", _hoisted_2, [
				createBaseVNode("label", { for: __props.controlId }, [createBaseVNode("strong", null, toDisplayString(unref(t)(__props.title)), 1)], 8, _hoisted_3),
				__props.path ? (openBlock(), createElementBlock("code", _hoisted_4, toDisplayString(__props.path), 1)) : createCommentVNode("", true),
				__props.description ? (openBlock(), createElementBlock("p", {
					key: 1,
					id: __props.controlId + "-help",
					class: "muted"
				}, toDisplayString(unref(t)(__props.description)), 9, _hoisted_5)) : createCommentVNode("", true),
				renderSlot(_ctx.$slots, "description")
			]), createBaseVNode("div", _hoisted_6, [renderSlot(_ctx.$slots, "default")])]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=SettingRow.js.map
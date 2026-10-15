import { F as renderSlot, K as withDirectives, N as openBlock, T as mergeModels, V as useModel, _ as createCommentVNode, a as vModelCheckbox, b as createTextVNode, et as unref, g as createBlock, h as createBaseVNode, rt as toDisplayString, tt as normalizeClass, v as createElementBlock } from "./vue.js";
import { T as t, c as _sfc_main$1 } from "./index.js";
//#region src/controls/AppCheckbox.vue
var _hoisted_1 = { class: "app-checkbox-indicator" };
var _hoisted_2 = [
	"id",
	"disabled",
	"indeterminate",
	"aria-label"
];
var _sfc_main = {
	__name: "AppCheckbox",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		controlId: String,
		disabled: Boolean,
		indeterminate: Boolean,
		compact: Boolean,
		hideLabel: Boolean,
		translateLabel: {
			type: Boolean,
			default: true
		}
	}, {
		"modelValue": {
			type: Boolean,
			default: false
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("label", { class: normalizeClass(["app-checkbox", {
				disabled: __props.disabled,
				compact: __props.compact
			}]) }, [createBaseVNode("span", _hoisted_1, [withDirectives(createBaseVNode("input", {
				id: __props.controlId,
				type: "checkbox",
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				disabled: __props.disabled,
				indeterminate: __props.indeterminate,
				"aria-label": __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : void 0
			}, null, 8, _hoisted_2), [[vModelCheckbox, model.value]]), model.value || __props.indeterminate ? (openBlock(), createBlock(_sfc_main$1, {
				key: 0,
				name: __props.indeterminate ? "minus" : "check"
			}, null, 8, ["name"])) : createCommentVNode("", true)]), !__props.hideLabel ? renderSlot(_ctx.$slots, "default", {}, () => [createTextVNode(toDisplayString(__props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : ""), 1)], void 0, 0) : createCommentVNode("", true)], 2);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppCheckbox.js.map
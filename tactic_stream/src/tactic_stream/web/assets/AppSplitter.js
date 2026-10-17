import { B as useModel, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, et as unref, tt as normalizeClass, w as mergeModels } from "./vue.js";
import { D as t } from "./index.js";
//#region src/controls/AppSplitter.vue
var _hoisted_1 = [
	"tabindex",
	"aria-disabled",
	"aria-label",
	"aria-orientation",
	"aria-valuemin",
	"aria-valuemax",
	"aria-valuenow"
];
var _sfc_main = {
	__name: "AppSplitter",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		horizontal: Boolean,
		min: Number,
		max: Number,
		reverse: Boolean,
		proportional: Boolean,
		disabled: Boolean
	}, {
		"modelValue": {
			type: Number,
			required: true
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const dragging = ref(false);
		let gesture = null;
		function set(value) {
			model.value = Math.max(props.min, Math.min(props.max, value));
		}
		function move(event) {
			if (gesture && event.pointerId === gesture.id) set(gesture.value + ((props.horizontal ? event.clientY : event.clientX) - gesture.position) * gesture.scale * (props.reverse ? -1 : 1));
		}
		function end() {
			gesture = null;
			dragging.value = false;
			window.removeEventListener("pointermove", move);
			window.removeEventListener("pointerup", end);
			window.removeEventListener("pointercancel", end);
			window.removeEventListener("blur", end);
		}
		function start(event) {
			if (props.disabled || event.button !== 0) return;
			const bounds = event.currentTarget.parentElement.getBoundingClientRect();
			gesture = {
				id: event.pointerId,
				value: model.value,
				position: props.horizontal ? event.clientY : event.clientX,
				scale: props.proportional ? 100 / Math.max(1, props.horizontal ? bounds.height : bounds.width) : 1
			};
			dragging.value = true;
			event.currentTarget.focus();
			event.preventDefault();
			window.addEventListener("pointermove", move);
			window.addEventListener("pointerup", end);
			window.addEventListener("pointercancel", end);
			window.addEventListener("blur", end);
		}
		function key(event) {
			if (props.disabled) return;
			const keys = props.horizontal ? ["ArrowUp", "ArrowDown"] : ["ArrowLeft", "ArrowRight"];
			if (![
				...keys,
				"Home",
				"End"
			].includes(event.key)) return;
			event.preventDefault();
			set(event.key === "Home" ? props.min : event.key === "End" ? props.max : model.value + (event.key === keys[0] ? -1 : 1) * (props.reverse ? -1 : 1) * (event.ctrlKey || props.proportional ? 1 : 10));
		}
		onBeforeUnmount(end);
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["app-splitter resize-grip", {
					horizontal: __props.horizontal,
					dragging: dragging.value
				}]),
				role: "separator",
				tabindex: __props.disabled ? -1 : 0,
				"aria-disabled": __props.disabled || void 0,
				"aria-label": unref(t)(__props.label),
				"aria-orientation": __props.horizontal ? "horizontal" : "vertical",
				"aria-valuemin": __props.min,
				"aria-valuemax": __props.max,
				"aria-valuenow": Math.round(model.value),
				onPointerdown: start,
				onKeydown: key
			}, null, 42, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppSplitter.js.map
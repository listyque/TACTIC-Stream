import { N as openBlock, T as mergeModels, V as useModel, X as ref, _ as createCommentVNode, et as unref, h as createBaseVNode, m as computed, nt as normalizeStyle, rt as toDisplayString, v as createElementBlock, x as createVNode, z as useAttrs } from "./vue.js";
import { T as t, i as _sfc_main$2 } from "./index.js";
import { t as _sfc_main$3 } from "./AppSlider.js";
import { t as _sfc_main$4 } from "./AppTextField.js";
//#region src/controls/ColorPicker.vue
var _hoisted_1$1 = ["aria-label"];
var _hoisted_2$1 = { class: "color-picker-fields" };
var _hoisted_3 = [
	"aria-label",
	"aria-valuetext",
	"aria-valuenow",
	"aria-description"
];
var _hoisted_4 = { class: "color-picker-hex" };
var _sfc_main$1 = {
	__name: "ColorPicker",
	emits: ["chosen"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const emit = __emit;
		const dialog = ref(null), hue = ref(0), saturation = ref(0), brightness = ref(1), hex = ref("#ffffff");
		const valid = computed(() => /^#[\da-f]{6}$/i.test(hex.value));
		function setColor(value) {
			if (!/^#[\da-f]{6}$/i.test(value || "")) return;
			const [r, g, b] = [
				1,
				3,
				5
			].map((index) => parseInt(value.slice(index, index + 2), 16) / 255);
			const max = Math.max(r, g, b), delta = max - Math.min(r, g, b);
			hue.value = delta ? ((max === r ? (g - b) / delta : max === g ? (b - r) / delta + 2 : (r - g) / delta + 4) / 6 + 1) % 1 : 0;
			saturation.value = max ? delta / max : 0;
			brightness.value = max;
			hex.value = value.toLowerCase();
		}
		function updateHex() {
			const h = hue.value * 6, c = brightness.value * saturation.value, x = c * (1 - Math.abs(h % 2 - 1)), m = brightness.value - c;
			const rgb = [
				[
					c,
					x,
					0
				],
				[
					x,
					c,
					0
				],
				[
					0,
					c,
					x
				],
				[
					0,
					x,
					c
				],
				[
					x,
					0,
					c
				],
				[
					c,
					0,
					x
				]
			][Math.floor(h) % 6];
			hex.value = "#" + rgb.map((value) => Math.round((value + m) * 255).toString(16).padStart(2, "0")).join("");
		}
		function choose(event) {
			const plane = event.currentTarget, box = plane.getBoundingClientRect();
			if (event.type === "pointerdown") {
				if (event.button !== 0) return;
				plane.setPointerCapture(event.pointerId);
				plane.focus();
			}
			if (event.type === "pointermove" && !plane.hasPointerCapture(event.pointerId)) return;
			saturation.value = Math.max(0, Math.min(1, (event.clientX - box.x) / box.width));
			brightness.value = Math.max(0, Math.min(1, 1 - (event.clientY - box.y) / box.height));
			updateHex();
		}
		function key(event) {
			if (!event.key.startsWith("Arrow")) return;
			event.preventDefault();
			saturation.value = Math.max(0, Math.min(1, saturation.value + (event.key === "ArrowRight" ? .01 : event.key === "ArrowLeft" ? -.01 : 0)));
			brightness.value = Math.max(0, Math.min(1, brightness.value + (event.key === "ArrowUp" ? .01 : event.key === "ArrowDown" ? -.01 : 0)));
			updateHex();
		}
		function open(value) {
			setColor(/^#[\da-f]{6}$/i.test(value || "") ? value : getComputedStyle(document.documentElement).getPropertyValue("--primary").trim());
			dialog.value.showModal();
		}
		function accept() {
			if (!valid.value) return;
			emit("chosen", hex.value.toLowerCase());
			dialog.value.close();
		}
		__expose({ open });
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("dialog", {
				ref_key: "dialog",
				ref: dialog,
				class: "color-picker",
				"aria-label": unref(t)("Choose a color"),
				onClose: _cache[4] || (_cache[4] = ($event) => hex.value = "#ffffff")
			}, [
				createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Choose a color")), 1)]),
				createBaseVNode("div", _hoisted_2$1, [
					createBaseVNode("div", {
						class: "color-picker-plane",
						role: "slider",
						tabindex: "0",
						"aria-label": unref(t)("Saturation and brightness"),
						"aria-valuetext": hex.value,
						"aria-valuenow": Math.round(brightness.value * 100),
						"aria-valuemin": 0,
						"aria-valuemax": 100,
						"aria-description": unref(t)("Use the arrow keys to adjust the color"),
						style: normalizeStyle({ "--hue": hue.value * 360 + "deg" }),
						onPointerdown: choose,
						onPointermove: choose,
						onKeydown: key
					}, [createBaseVNode("span", { style: normalizeStyle({
						left: saturation.value * 100 + "%",
						top: (1 - brightness.value) * 100 + "%"
					}) }, null, 4)], 44, _hoisted_3),
					createBaseVNode("label", null, toDisplayString(unref(t)("Hue")), 1),
					createVNode(_sfc_main$3, {
						modelValue: hue.value,
						"onUpdate:modelValue": [_cache[0] || (_cache[0] = ($event) => hue.value = $event), updateHex],
						label: "Hue",
						min: 0,
						max: 1,
						step: .005,
						class: "color-picker-hue"
					}, null, 8, ["modelValue"]),
					createBaseVNode("div", _hoisted_4, [createBaseVNode("span", {
						class: "color-swatch",
						style: normalizeStyle({ background: valid.value ? hex.value : "#000000" }),
						"aria-hidden": "true"
					}, null, 4), createVNode(_sfc_main$4, {
						modelValue: hex.value,
						"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => hex.value = $event),
						label: "Color in HEX format",
						"aria-invalid": !valid.value,
						onChange: _cache[2] || (_cache[2] = ($event) => setColor(hex.value))
					}, null, 8, ["modelValue", "aria-invalid"])])
				]),
				createBaseVNode("footer", null, [createVNode(_sfc_main$2, {
					label: "Cancel",
					onClick: _cache[3] || (_cache[3] = ($event) => dialog.value.close())
				}), createVNode(_sfc_main$2, {
					label: "OK",
					disabled: !valid.value,
					onClick: accept
				}, null, 8, ["disabled"])])
			], 40, _hoisted_1$1);
		};
	}
};
//#endregion
//#region src/controls/AppColorInput.vue
var _hoisted_1 = { class: "app-color-input" };
var _hoisted_2 = ["name", "value"];
var _sfc_main = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppColorInput",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		disabled: Boolean,
		readonly: Boolean
	}, {
		"modelValue": {},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		const attrs = useAttrs();
		const picker = ref(null);
		const swatch = computed(() => /^#[\da-f]{6}$/i.test(model.value || "") ? model.value : "var(--primary)");
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1, [
				createBaseVNode("span", {
					class: "color-swatch",
					style: normalizeStyle({ background: swatch.value }),
					"aria-hidden": "true"
				}, null, 4),
				createVNode(_sfc_main$2, {
					id: unref(attrs).id,
					label: "Choose color",
					icon: "appearance",
					disabled: __props.disabled || __props.readonly,
					"aria-label": unref(t)("Choose color for {field}", { field: __props.label }),
					"aria-describedby": unref(attrs)["aria-describedby"],
					title: model.value || "",
					onClick: _cache[0] || (_cache[0] = ($event) => picker.value.open(model.value))
				}, null, 8, [
					"id",
					"disabled",
					"aria-label",
					"aria-describedby",
					"title"
				]),
				unref(attrs).name ? (openBlock(), createElementBlock("input", {
					key: 0,
					type: "hidden",
					name: unref(attrs).name,
					value: model.value
				}, null, 8, _hoisted_2)) : createCommentVNode("", true),
				createVNode(_sfc_main$1, {
					ref_key: "picker",
					ref: picker,
					onChosen: _cache[1] || (_cache[1] = ($event) => model.value = $event)
				}, null, 512)
			]);
		};
	}
});
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppColorInput.js.map
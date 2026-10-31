import { A as onMounted, B as useModel, E as nextTick, F as resolveComponent, G as withCtx, H as watch, K as withDirectives, L as resolveDynamicComponent, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, R as useAttrs, T as mergeProps, X as ref, _ as createElementBlock, a as vModelSelect, b as createVNode, c as withKeys, et as unref, g as createCommentVNode, h as createBlock, j as onUpdated, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, o as vModelText, p as computed, q as isRef, rt as toDisplayString, s as vShow, tt as normalizeClass, u as Fragment, w as mergeModels, y as createTextVNode, z as useId } from "./vue.js";
import { E as readableText, I as iconSets, O as textStyles, R as BusyIndicator_default, T as metrics, _ as controls, a as _sfc_main$33, g as blend, i as ripple, l as effectiveColorMode, n as tooltipDirective, o as t, r as capturePress, s as appearance, t as _sfc_main$34, u as frameColors, v as cssColor, y as cssRoles, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { t as iconMaps } from "./icons.js";
//#region ../src/tactic_stream/shared_ui/core/frame.mjs
/** @typedef {{x:number, y:number, width:number, height:number}} Bounds Logical pixels. */
/** @typedef {{type:string, [key:string]:unknown}} Action UI event or adapter command. */
/** @typedef {'Box'|'Label'|'Icon'|'Button'|'Action'|'CheckBox'|'Field'|'Area'|'Preview'|'List'|'Scroll'|'Choice'|'Grid'|'IconChoice'|'Splitter'|'Switch'|'Graph'|'Chart'|'View'|'ColorChoice'|'Code'|'DateChoice'|'UserChoice'|'SummaryChip'|'StatusChip'|'Segmented'|'Search'|'Identity'|'Progress'|'Empty'|'FileField'} ControlKind */
/** @typedef {Bounds & {kind:ControlKind, id:string, children:FrameNode[], fontRole:keyof typeof textStyles, fontSize:number, action:Action|null, [key:string]:unknown}} FrameNode */
/** @typedef {{nodes:FrameNode[]}} Scene */
var controlKinds = Object.freeze([
	"Box",
	"Label",
	"Icon",
	"Button",
	"Action",
	"CheckBox",
	"Field",
	"Area",
	"Preview",
	"List",
	"Scroll",
	"Choice",
	"DateChoice",
	"UserChoice",
	"Grid",
	"IconChoice",
	"Splitter",
	"Switch",
	"Graph",
	"Chart",
	"View",
	"ColorChoice",
	"Code",
	"SummaryChip",
	"StatusChip",
	"Segmented",
	"Search",
	"Identity",
	"Progress",
	"Empty",
	"FileField"
]);
function rect(x, y, width, height) {
	return {
		x,
		y,
		width: Math.max(0, width),
		height: Math.max(0, height)
	};
}
function revealListOffset(offset, index, height, count, rowHeight, rowGap = 0, offsets = null) {
	const top = offsets ? offsets[index] : index * rowHeight, bottom = top + rowHeight - rowGap;
	const desired = top < offset ? top : bottom > offset + height ? bottom - height : offset;
	return Math.max(0, Math.min(desired, Math.max(0, (offsets ? offsets[count] : count * rowHeight) - rowGap - height)));
}
function label(id, bounds, text, extra) {
	return node("Label", id, bounds, Object.assign({ text }, extra || {}));
}
var muted = {
	fontRole: "secondary",
	color: "secondaryText"
};
function button(id, bounds, text, icon, action, enabled, extra) {
	return node("Button", id, bounds, Object.assign({
		text,
		icon,
		action,
		enabled
	}, extra || {}));
}
/**
* Create a named native control. Only fontRole enters; fontSize is resolved output.
* @param {ControlKind} kind
* @param {string} id Stable within its sibling scene, independent of display text.
* @param {Bounds} rect
* @param {Object} [properties] Control data and actions; no engine objects or requests.
* @returns {FrameNode}
*/
function node(kind, id, rect, properties) {
	if (controlKinds.indexOf(kind) < 0) throw Error("Unsupported Tactic Frame control: " + kind);
	if (typeof id !== "string" || !id.trim()) throw Error("Missing Frame control id");
	for (const key of [
		"x",
		"y",
		"width",
		"height"
	]) if (typeof rect[key] !== "number" || !isFinite(rect[key])) throw Error("Invalid frame: " + id + ".." + key);
	if (rect.width < 0 || rect.height < 0) throw Error("Negative frame: " + id);
	const options = Object.assign(kind === "List" ? { fields: [] } : {}, properties || {});
	for (const key of [
		"kind",
		"id",
		"x",
		"y",
		"width",
		"height",
		"fontSize"
	]) if (Object.prototype.hasOwnProperty.call(options, key)) throw Error("Reserved Frame property: " + id + "." + key);
	if (options.titlebar && options.children) options.children = options.children.map((child) => child.kind === "Button" ? Object.assign({}, child, { round: true }) : child);
	const fontRole = options.fontRole === void 0 ? "body" : options.fontRole;
	if (!Object.prototype.hasOwnProperty.call(textStyles, fontRole)) throw Error("Unknown Frame font role: " + id + "." + fontRole);
	const button = kind === "Button";
	const color = options.enabled === false && [
		"Button",
		"Field",
		"Area",
		"Choice"
	].indexOf(kind) >= 0 ? "disabledText" : button && options.destructive && !options.highlighted ? "error" : button && (options.highlighted || options.radio && options.selected) ? "selectedText" : button && options.radio ? "secondaryText" : "primaryText";
	return Object.assign({
		kind,
		id,
		text: "",
		color,
		fontRole,
		fontSize: textStyles[fontRole],
		weight: button ? options.radio && !options.selected ? 500 : 600 : 400,
		enabled: true,
		opacity: 1,
		children: [],
		action: null
	}, rect, options, {
		fontRole,
		fontSize: textStyles[fontRole],
		text: options.text == null ? "" : String(options.text)
	});
}
/**
* Validate one scene boundary. Models are engine-owned arrays or native models.
* @param {Scene} scene
* @param {Object} [models] Named snapshots/models, kept outside the scene tree.
* @param {Object} [views] Registered child views; absent slots require optional:true.
*/
function validateScene(scene, models, views) {
	if (!scene || !sequence(scene.nodes)) throw Error("Frame scene needs nodes");
	const ids = /* @__PURE__ */ new Set();
	for (let index = 0; index < scene.nodes.length; index++) {
		const value = scene.nodes[index];
		if (!value || controlKinds.indexOf(value.kind) < 0) throw Error("Unsupported Frame scene control");
		if (!value.id || ids.has(value.id)) throw Error("Duplicate/missing Frame id: " + value.id);
		ids.add(value.id);
		if (value.scale !== void 0 && (!Number.isFinite(value.scale) || value.scale <= 0)) throw Error("Invalid Frame scale: " + value.id);
		if (!Object.prototype.hasOwnProperty.call(textStyles, value.fontRole) || value.fontSize !== textStyles[value.fontRole]) throw Error("Invalid Frame typography: " + value.id);
		for (const key of [
			"x",
			"y",
			"width",
			"height"
		]) if (typeof value[key] !== "number" || !isFinite(value[key]) || (key === "width" || key === "height") && value[key] < 0) throw Error("Invalid Frame bounds: " + value.id + "." + key);
		for (const key of [
			"action",
			"pressAction",
			"doubleAction",
			"contextAction",
			"activateAction",
			"commitAction",
			"cancelAction",
			"dropAction",
			"dragStartAction",
			"acceptAction"
		]) if (value[key] != null && (typeof value[key].type !== "string" || !value[key].type)) throw Error("Invalid Frame action: " + value.id + "." + key);
		if (value.kind === "List" || value.kind === "Grid") {
			if (typeof value.source !== "string" || !value.source || !models || !Object.prototype.hasOwnProperty.call(models, value.source) || models[value.source] == null) throw Error("Missing Frame source: " + value.id + "." + value.source);
		}
		if (value.kind === "List" && (typeof value.keyField !== "string" || !value.keyField || typeof value.rowHeight !== "number" || !isFinite(value.rowHeight) || listRowHeight(value) <= 0 || value.rowGap !== void 0 && (!Number.isFinite(value.rowGap) || value.rowGap < 0))) throw Error("List needs keyField, positive rowHeight and valid rowGap: " + value.id);
		if (value.kind === "List" && !sequence(value.fields)) throw Error("List needs declared model fields: " + value.id);
		if (value.kind === "List" && value.rowHeightField !== void 0 && (typeof value.rowHeightField !== "string" || !value.rowHeightField || !value.fields.includes(value.rowHeightField))) throw Error("List needs a declared rowHeightField: " + value.id);
		if (value.kind === "List" && value.rowHeightField !== void 0 && !sequence(models[value.source])) throw Error("Variable Frame rows require an array model: " + value.id);
		if ([
			"Box",
			"Scroll",
			"Action"
		].indexOf(value.kind) >= 0 && !sequence(value.children)) throw Error("Frame container needs children: " + value.id);
		if (value.kind === "Grid" && (!sequence(value.rowHeaders) || !sequence(value.columnHeaders) || !Number.isFinite(value.cellWidth) || value.cellWidth <= 0 || !Number.isFinite(value.rowHeight) || value.rowHeight <= 0)) throw Error("Grid needs headers and positive cell geometry: " + value.id);
		if (value.kind === "Search" && value.suggestions !== void 0 && !sequence(value.suggestions)) throw Error("Search needs prepared suggestions: " + value.id);
		if (value.kind === "Progress" && (!Number.isFinite(value.min ?? 0) || !Number.isFinite(value.max ?? 1) || (value.max ?? 1) <= (value.min ?? 0) || !value.indeterminate && !Number.isFinite(value.value))) throw Error("Progress needs a finite range/value: " + value.id);
		if (value.kind === "View" && (typeof value.view !== "string" || !value.view)) throw Error("Frame View needs a registered name: " + value.id);
		if (value.kind === "View" && (!views || !Object.prototype.hasOwnProperty.call(views, value.view) || views[value.view] == null) && value.optional !== true) throw Error("Missing Frame View: " + value.id + "." + value.view);
	}
	return scene.nodes;
}
/** Array records are immutable snapshots; a key stays unique across sorting/filtering. */
function recordIndex(rows, keyField) {
	if (!sequence(rows)) throw Error("Frame array list needs an array");
	const indexes = /* @__PURE__ */ new Map();
	for (let index = 0; index < rows.length; index++) {
		const value = rows[index] && rows[index][keyField];
		if (typeof value !== "string" && typeof value !== "number" || value === "" || typeof value === "number" && !isFinite(value)) throw Error("Missing Frame record key: " + keyField + "[" + index + "]");
		const key = String(value);
		if (indexes.has(key)) throw Error("Duplicate Frame record key: " + key);
		indexes.set(key, index);
	}
	return indexes;
}
function sequence(value) {
	return value !== null && typeof value === "object" && Number.isInteger(value.length) && value.length >= 0;
}
function listRowHeight(definition) {
	return definition.rowHeight - (definition.rowGap === void 0 ? 4 : definition.rowGap);
}
function listOffsets(definition, rows) {
	if (!definition.rowHeightField) return null;
	const gap = definition.rowGap === void 0 ? 4 : definition.rowGap;
	const offsets = [0];
	for (const row of rows) {
		const height = row[definition.rowHeightField];
		const next = offsets[offsets.length - 1] + height;
		if (!Number.isFinite(height) || height <= gap || !Number.isFinite(next)) throw Error("Invalid Frame row height: " + definition.id);
		offsets.push(next);
	}
	return offsets;
}
function listBounds(definition, offsets, index) {
	const gap = definition.rowGap === void 0 ? 4 : definition.rowGap;
	return {
		y: offsets ? offsets[index] : index * definition.rowHeight,
		height: offsets ? offsets[index + 1] - offsets[index] - gap : listRowHeight(definition)
	};
}
function listRange(count, rowHeight, viewport, scroll, overscan, offsets = null) {
	const fixed = virtualRange(count, rowHeight, viewport, scroll, overscan);
	if (!offsets) return fixed;
	if (offsets.length !== count + 1) throw Error("Invalid Frame row offsets");
	function boundary(pixel, after) {
		let first = 0, last = offsets.length;
		while (first < last) {
			const middle = Math.floor((first + last) / 2);
			if (offsets[middle] < pixel || after && offsets[middle] === pixel) first = middle + 1;
			else last = middle;
		}
		return first;
	}
	const first = Math.min(count, Math.max(0, boundary(scroll, true) - 1 - overscan));
	return {
		first,
		last: Math.max(first, Math.min(count, boundary(scroll + viewport, false) + overscan)),
		height: offsets[count]
	};
}
function virtualRange(count, rowHeight, viewport, scroll, overscan) {
	if (!Number.isInteger(count) || count < 0 || !Number.isFinite(rowHeight) || rowHeight <= 0 || !Number.isFinite(viewport) || viewport < 0 || !Number.isFinite(scroll) || !Number.isInteger(overscan) || overscan < 0) throw Error("Invalid Frame virtual range");
	const first = Math.min(count, Math.max(0, Math.floor(scroll / rowHeight) - overscan));
	return {
		first,
		last: Math.max(first, Math.min(count, Math.ceil((scroll + viewport) / rowHeight) + overscan)),
		height: count * rowHeight
	};
}
//#endregion
//#region src/controls/AppSwitch.vue
var _hoisted_1$30 = { class: "switch-control" };
var _hoisted_2$17 = ["aria-label", "checked"];
var _sfc_main$32 = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppSwitch",
	props: /*@__PURE__*/ mergeModels({ label: String }, {
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
			return openBlock(), createElementBlock("label", _hoisted_1$30, [createBaseVNode("input", mergeProps(_ctx.$attrs, {
				class: "app-switch",
				type: "checkbox",
				role: "switch",
				"aria-label": __props.label ? unref(t)(__props.label) : void 0,
				checked: model.value,
				onChange: _cache[0] || (_cache[0] = ($event) => model.value = $event.target.checked)
			}), null, 16, _hoisted_2$17)]);
		};
	}
});
//#endregion
//#region src/controls/AppSelect.vue
var _hoisted_1$29 = ["aria-label"];
var _hoisted_2$16 = {
	key: 0,
	type: "button",
	class: "app-select-trigger"
};
var _hoisted_3$12 = { class: "app-select-selected-content" };
var _hoisted_4$7 = { class: "app-select-option-label" };
var _hoisted_5$5 = ["value"];
var _hoisted_6$4 = { class: "app-select-option-label" };
var _sfc_main$31 = {
	__name: "AppSelect",
	props: /*@__PURE__*/ mergeModels({
		options: {
			type: Array,
			default: () => []
		},
		label: String,
		displayPrefix: String,
		swatchMode: String,
		translateLabels: {
			type: Boolean,
			default: true
		}
	}, {
		"modelValue": {},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const customizable = CSS.supports("appearance", "base-select");
		const decorated = computed(() => customizable && props.options.some((item) => item.icon));
		const selectedOption = computed(() => props.options.find((item) => item.value === model.value));
		const optionLabel = (item) => props.translateLabels ? t(item.label) : item.label;
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("select", {
				class: "app-select",
				style: normalizeStyle(__props.displayPrefix ? { "--select-display-prefix": JSON.stringify(__props.displayPrefix) } : void 0),
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				"aria-label": __props.label ? unref(t)(__props.label) : void 0
			}, [
				unref(customizable) ? (openBlock(), createElementBlock("button", _hoisted_2$16, [createBaseVNode("span", _hoisted_3$12, [
					decorated.value && selectedOption.value?.icon ? (openBlock(), createBlock(_sfc_main$33, {
						key: 0,
						name: selectedOption.value.icon
					}, null, 8, ["name"])) : createCommentVNode("", true),
					__props.swatchMode && selectedOption.value ? (openBlock(), createElementBlock("span", {
						key: 1,
						class: "palette-swatch",
						style: normalizeStyle({
							backgroundColor: selectedOption.value[__props.swatchMode],
							borderColor: selectedOption.value[__props.swatchMode + "Base"]
						})
					}, null, 4)) : createCommentVNode("", true),
					createBaseVNode("span", _hoisted_4$7, toDisplayString(selectedOption.value ? optionLabel(selectedOption.value) : model.value), 1)
				]), createVNode(_sfc_main$33, {
					name: "expand_more",
					class: "app-select-indicator"
				})])) : createCommentVNode("", true),
				model.value !== void 0 && !__props.options.some((item) => item.value === model.value) ? (openBlock(), createElementBlock("option", {
					key: 1,
					value: model.value
				}, toDisplayString(model.value), 9, _hoisted_5$5)) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList(__props.options, (item) => {
					return openBlock(), createBlock(resolveDynamicComponent("option"), {
						key: item.value,
						value: item.value,
						disabled: item.disabled || item.enabled === false
					}, {
						default: withCtx(() => [
							decorated.value && item.icon ? (openBlock(), createBlock(_sfc_main$33, {
								key: 0,
								name: item.icon
							}, null, 8, ["name"])) : createCommentVNode("", true),
							__props.swatchMode ? (openBlock(), createElementBlock("span", {
								key: 1,
								class: "palette-swatch",
								style: normalizeStyle({
									backgroundColor: item[__props.swatchMode],
									borderColor: item[__props.swatchMode + "Base"]
								})
							}, null, 4)) : createCommentVNode("", true),
							createBaseVNode("span", _hoisted_6$4, toDisplayString(optionLabel(item)), 1)
						]),
						_: 2
					}, 1032, ["value", "disabled"]);
				}), 128))
			], 12, _hoisted_1$29)), [[vModelSelect, model.value]]);
		};
	}
};
//#endregion
//#region src/frame/resize.js
function observeFrameSizes(apply) {
	const pending = /* @__PURE__ */ new Map();
	let frame = 0;
	let disconnected = false;
	const observer = new ResizeObserver((entries) => {
		if (disconnected) return;
		for (const entry of entries) pending.set(entry.target, entry);
		if (frame) return;
		frame = requestAnimationFrame(() => {
			frame = 0;
			const entries = [...pending.values()];
			pending.clear();
			if (!disconnected && entries.length) apply(entries);
		});
	});
	return {
		observe(target) {
			if (!disconnected) observer.observe(target);
		},
		unobserve(target) {
			pending.delete(target);
			observer.unobserve(target);
		},
		disconnect() {
			disconnected = true;
			observer.disconnect();
			cancelAnimationFrame(frame);
			frame = 0;
			pending.clear();
		}
	};
}
function frameContentWidth(element) {
	const style = getComputedStyle(element);
	const width = parseFloat(style.width);
	if (!Number.isFinite(width)) return element.clientWidth;
	return style.boxSizing === "border-box" ? Math.max(0, width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - parseFloat(style.borderLeftWidth) - parseFloat(style.borderRightWidth)) : width;
}
//#endregion
//#region src/controls/AppSlider.vue
var _hoisted_1$28 = [
	"aria-label",
	"disabled",
	"min",
	"max",
	"step"
];
var _sfc_main$30 = {
	__name: "AppSlider",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		disabled: Boolean,
		min: {
			type: Number,
			default: 0
		},
		max: {
			type: Number,
			default: 100
		},
		step: {
			type: Number,
			default: 1
		}
	}, {
		"modelValue": {
			type: Number,
			default: 0
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("input", {
				class: "app-slider",
				type: "range",
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				style: normalizeStyle({ "--slider-position": (__props.max > __props.min ? Math.max(0, Math.min(100, (model.value - __props.min) / (__props.max - __props.min) * 100)) : 0) + "%" }),
				"aria-label": unref(t)(__props.label),
				disabled: __props.disabled,
				min: __props.min,
				max: __props.max,
				step: __props.step
			}, null, 12, _hoisted_1$28)), [[
				vModelText,
				model.value,
				void 0,
				{ number: true }
			]]);
		};
	}
};
//#endregion
//#region src/controls/AppTextField.vue
var _hoisted_1$27 = [
	"aria-invalid",
	"aria-label",
	"placeholder",
	"disabled"
];
var _sfc_main$29 = {
	__name: "AppTextField",
	props: {
		modelValue: {
			type: [String, Number],
			default: ""
		},
		label: String,
		placeholder: String,
		disabled: Boolean,
		errorState: Boolean
	},
	emits: ["update:modelValue"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const text = computed({
			get: () => String(props.modelValue ?? ""),
			set: (value) => emit("update:modelValue", String(value))
		});
		const field = ref(null);
		__expose({ focus() {
			field.value?.focus();
		} });
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("input", {
				ref_key: "field",
				ref: field,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => text.value = $event),
				class: "app-text-field",
				"aria-invalid": __props.errorState || void 0,
				"aria-label": __props.label || __props.placeholder ? unref(t)(__props.label || __props.placeholder) : void 0,
				placeholder: unref(t)(__props.placeholder || ""),
				disabled: __props.disabled
			}, null, 8, _hoisted_1$27)), [[vModelText, text.value]]);
		};
	}
};
//#endregion
//#region src/controls/ColorPicker.vue
var _hoisted_1$26 = ["aria-label"];
var _hoisted_2$15 = { class: "color-picker-fields" };
var _hoisted_3$11 = [
	"aria-label",
	"aria-valuetext",
	"aria-valuenow",
	"aria-description"
];
var _hoisted_4$6 = { class: "color-picker-hex" };
var _sfc_main$28 = {
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
			if (/^#[\da-f]{6}$/i.test(value || "")) setColor(value);
			else {
				const context = document.createElement("canvas").getContext("2d");
				context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--primary").trim();
				context.fillRect(0, 0, 1, 1);
				setColor("#" + [...context.getImageData(0, 0, 1, 1).data].slice(0, 3).map((channel) => channel.toString(16).padStart(2, "0")).join(""));
			}
			dialog.value.showModal();
		}
		function accept() {
			if (!valid.value) return;
			emit("chosen", hex.value.toLowerCase());
			dialog.value.close();
		}
		__expose({
			open,
			close() {
				dialog.value?.close();
			}
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("dialog", {
				ref_key: "dialog",
				ref: dialog,
				class: "color-picker",
				"aria-label": unref(t)("Choose a color"),
				onClose: _cache[4] || (_cache[4] = ($event) => hex.value = "#ffffff")
			}, [
				createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Choose a color")), 1)]),
				createBaseVNode("div", _hoisted_2$15, [
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
					}) }, null, 4)], 44, _hoisted_3$11),
					createBaseVNode("label", null, toDisplayString(unref(t)("Hue")), 1),
					createVNode(_sfc_main$30, {
						modelValue: hue.value,
						"onUpdate:modelValue": [_cache[0] || (_cache[0] = ($event) => hue.value = $event), updateHex],
						label: "Hue",
						min: 0,
						max: 1,
						step: .005,
						class: "color-picker-hue"
					}, null, 8, ["modelValue"]),
					createBaseVNode("div", _hoisted_4$6, [createBaseVNode("span", {
						class: "color-swatch",
						style: normalizeStyle({ background: valid.value ? hex.value : "#000000" }),
						"aria-hidden": "true"
					}, null, 4), createVNode(_sfc_main$29, {
						modelValue: hex.value,
						"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => hex.value = $event),
						label: "Color in HEX format",
						"aria-invalid": !valid.value,
						onChange: _cache[2] || (_cache[2] = ($event) => setColor(hex.value))
					}, null, 8, ["modelValue", "aria-invalid"])])
				]),
				createBaseVNode("footer", null, [createVNode(_sfc_main$34, {
					label: "Cancel",
					onClick: _cache[3] || (_cache[3] = ($event) => dialog.value.close())
				}), createVNode(_sfc_main$34, {
					label: "OK",
					disabled: !valid.value,
					onClick: accept
				}, null, 8, ["disabled"])])
			], 40, _hoisted_1$26);
		};
	}
};
//#endregion
//#region src/controls/AppColorInput.vue
var _hoisted_1$25 = { class: "app-color-input" };
var _hoisted_2$14 = ["name", "value"];
var _sfc_main$27 = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
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
		const props = __props;
		const model = useModel(__props, "modelValue");
		const attrs = useAttrs();
		const picker = ref(null);
		watch(() => props.disabled || props.readonly, (unavailable) => {
			if (unavailable) picker.value?.close();
		});
		const swatch = computed(() => /^#[\da-f]{6}$/i.test(model.value || "") ? model.value : "var(--primary)");
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$25, [
				createBaseVNode("span", {
					class: "color-swatch",
					style: normalizeStyle({ background: swatch.value }),
					"aria-hidden": "true"
				}, null, 4),
				createVNode(_sfc_main$34, {
					id: unref(attrs).id,
					label: "Choose color",
					icon: "palette",
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
				}, null, 8, _hoisted_2$14)) : createCommentVNode("", true),
				createVNode(_sfc_main$28, {
					ref_key: "picker",
					ref: picker,
					onChosen: _cache[1] || (_cache[1] = ($event) => model.value = $event)
				}, null, 512)
			]);
		};
	}
});
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/calendar.mjs
function monthLabel(date, language) {
	return (language === "ru" ? [
		"январь",
		"февраль",
		"март",
		"апрель",
		"май",
		"июнь",
		"июль",
		"август",
		"сентябрь",
		"октябрь",
		"ноябрь",
		"декабрь"
	] : [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December"
	])[date.getMonth()] + " " + date.getFullYear();
}
function localDate(year, month, day = 1, hour = 0, minute = 0, second = 0) {
	const result = /* @__PURE__ */ new Date(0);
	result.setFullYear(year, month, day);
	result.setHours(hour, minute, second, 0);
	return result;
}
function parse(value, includeTime = true) {
	const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?)?$/);
	if (!match || !includeTime && match[4]) return null;
	const [year, month, day, hour, minute, second] = match.slice(1, 7).map((part) => Number(part || 0));
	if (year < 1) return null;
	const offset = match[7];
	if (offset && offset !== "Z" && (Number(offset.slice(1, 3)) > 23 || Number(offset.slice(4)) > 59)) return null;
	const date = localDate(year, month - 1, day, hour, minute, second);
	return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day && date.getHours() === hour && date.getMinutes() === minute && date.getSeconds() === second ? date : null;
}
function monthDays(year, month) {
	const first = localDate(year, month, 1);
	const last = new Date(first);
	last.setMonth(first.getMonth() + 1, 0);
	const offset = (first.getDay() + 6) % 7;
	return Array.from({ length: 42 }, (_, index) => {
		const day = index - offset + 1;
		return day > 0 && day <= last.getDate() ? day : 0;
	});
}
//#endregion
//#region src/controls/AppMenu.vue
var _hoisted_1$24 = [
	"aria-label",
	"aria-expanded",
	"aria-disabled",
	"tabindex"
];
var _hoisted_2$13 = { key: 0 };
var _hoisted_3$10 = {
	key: 0,
	class: "app-button-badge",
	"aria-hidden": "true"
};
var _sfc_main$26 = {
	__name: "AppMenu",
	props: {
		label: String,
		frameComposition: Boolean,
		processPickerStyle: Boolean,
		externalTrigger: Boolean,
		focusOnOpen: {
			type: Boolean,
			default: true
		},
		showLabel: Boolean,
		compactTrigger: Boolean,
		icon: {
			type: String,
			default: "more"
		},
		badgeCount: {
			type: Number,
			default: 0
		},
		closeOnSelect: {
			type: Boolean,
			default: true
		},
		boundary: Object,
		anchor: Object,
		alignStart: Boolean,
		centered: Boolean,
		disabled: Boolean,
		inline: Boolean,
		overlay: Boolean,
		modal: Boolean,
		submenu: Boolean,
		width: Number,
		maxHeight: Number
	},
	emits: ["before-open"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const processPaint = computed(() => {
			if (!props.processPickerStyle) return {};
			const colors = frameColors.value, dark = effectiveColorMode.value === "dark";
			const surface = blend(colors.panelDeep, colors.blackMix, dark ? .18 : .04);
			return {
				"--process-menu-surface": cssColor(surface),
				"--process-menu-border": cssColor(blend(surface, colors.primaryText, dark ? .16 : .22)),
				"--process-menu-row": cssColor(blend(surface, colors.primaryText, dark ? .05 : .08)),
				"--process-menu-row-border": cssColor(blend(surface, colors.primaryText, dark ? .1 : .15)),
				"--process-menu-badge": cssColor(blend(colors.surfaceContainerHigh, colors.primaryText, dark ? .12 : .06))
			};
		});
		const menu = ref(null);
		const trigger = ref(null);
		const expanded = ref(false);
		const panelElement = ref(null);
		let point = null;
		let returnTarget = null;
		let hoverTimer = null;
		let focusEdge = null;
		function cancelHover() {
			clearTimeout(hoverTimer);
		}
		function hoverSubmenu() {
			if (!props.submenu || props.disabled) return;
			clearTimeout(hoverTimer);
			hoverTimer = setTimeout(() => {
				if (menu.value.parentElement.closest("details")?.open) menu.value.open = true;
			}, parseFloat(getComputedStyle(menu.value).getPropertyValue("--motion-medium")) || 0);
		}
		function activate(event) {
			if (props.disabled) {
				event.preventDefault();
				return;
			}
			if (!props.submenu) return;
			event.preventDefault();
			clearTimeout(hoverTimer);
			menu.value.open = true;
		}
		function close(focus = false) {
			clearTimeout(hoverTimer);
			if (props.inline || !menu.value) return;
			menu.value.open = false;
			expanded.value = false;
			if (props.modal && panelElement.value.open) panelElement.value.close();
			if (props.overlay && !props.modal && panelElement.value?.matches(":popover-open")) panelElement.value.hidePopover();
			if (focus) (returnTarget?.isConnected ? returnTarget : props.anchor?.isConnected ? props.anchor : trigger.value)?.focus();
		}
		function outside(event) {
			if (menu.value && !menu.value.contains(event.target) && !props.anchor?.contains(event.target)) close();
		}
		function escape(event) {
			if (event.key !== "Escape" || event.defaultPrevented || !menu.value.open || props.inline || menu.value.querySelector("details[open]")) return;
			const dialog = event.target.closest("dialog");
			if (dialog && dialog !== panelElement.value && dialog !== props.boundary && !dialog.contains(menu.value) && !dialog.contains(props.anchor)) return;
			event.preventDefault();
			event.stopPropagation();
			close(true);
		}
		function position() {
			const panel = menu.value?.querySelector(".account-panel");
			if (!panel || !menu.value.open) return;
			const boundary = props.boundary?.getBoundingClientRect();
			const viewport = window.visualViewport, keyboardViewport = innerWidth <= 700 && viewport?.scale === 1;
			const viewportTop = keyboardViewport ? viewport.offsetTop : 0, viewportBottom = keyboardViewport ? viewportTop + viewport.height : innerHeight;
			const top = Math.max(viewportTop, boundary?.top || 0), bottom = Math.min(viewportBottom, boundary?.bottom ?? viewportBottom);
			if (props.centered) {
				const left = Math.max(0, boundary?.left || 0), right = Math.min(innerWidth, boundary?.right ?? innerWidth);
				panel.style.maxHeight = Math.max(0, Math.min(props.maxHeight ?? Infinity, bottom - top - 8)) + "px";
				panel.style.left = left + (right - left - panel.offsetWidth) / 2 + "px";
				panel.style.top = top + (bottom - top - panel.offsetHeight) / 2 + "px";
			} else if (props.overlay || props.modal) {
				const triggerBox = (props.anchor || trigger.value).getBoundingClientRect();
				panel.style.left = Math.max(4, props.submenu ? triggerBox.right + 6 : point?.x ?? (props.alignStart ? triggerBox.left : triggerBox.right - panel.offsetWidth)) + "px";
				const anchorTop = point?.y ?? triggerBox.top, anchorBottom = point?.y ?? triggerBox.bottom;
				const below = bottom - anchorBottom - 8, above = anchorTop - top - 8;
				const up = !props.modal && panel.scrollHeight > below && above > below;
				panel.style.maxHeight = Math.max(0, Math.min(props.maxHeight ?? Infinity, props.modal ? bottom - top - 8 : up ? above : below)) + "px";
				if (props.overlay && !props.modal) panel.style.overflowY = "auto";
				panel.style.top = (props.submenu ? triggerBox.top - 6 : up ? anchorTop - panel.offsetHeight - 4 : anchorBottom + 4) + "px";
				if (props.submenu) {
					panel.style.maxHeight = Math.max(0, Math.min(props.maxHeight ?? Infinity, bottom - top - 8)) + "px";
					if (triggerBox.right + 6 + panel.offsetWidth > (boundary?.right ?? innerWidth)) panel.style.left = Math.max(4, triggerBox.left - panel.offsetWidth - 6) + "px";
				}
			}
			panel.style.translate = "";
			const left = Math.max(0, boundary?.left || 0), right = Math.min(innerWidth, boundary?.right ?? innerWidth);
			if (boundary) panel.style.maxWidth = Math.max(0, right - left - 8) + "px";
			const box = panel.getBoundingClientRect(), style = getComputedStyle(panel);
			const scale = parseFloat(style.scale) || 1;
			const [originX, originY] = style.transformOrigin.split(" ").map(parseFloat);
			const x = box.left - originX * (1 - scale), y0 = box.top - originY * (1 - scale);
			const bounds = {
				left: x,
				top: y0,
				right: x + parseFloat(style.width),
				bottom: y0 + parseFloat(style.height)
			};
			const y = Math.max(top + 4 - bounds.top, Math.min(0, bottom - 4 - bounds.bottom));
			panel.style.translate = Math.max(left + 4 - bounds.left, Math.min(0, right - 4 - bounds.right)) + "px " + y + "px";
			if (props.processPickerStyle) {
				const triggerBox = props.anchor?.getBoundingClientRect();
				if (triggerBox) {
					const placed = panel.getBoundingClientRect();
					panel.style.setProperty("--menu-anchor-center", Math.max(14, Math.min(panel.offsetWidth - 14, triggerBox.x + triggerBox.width / 2 - placed.x)) + "px");
					if (panel.scrollHeight <= panel.clientHeight) panel.style.overflow = "visible";
					panel.dataset.anchorEdge = placed.top >= triggerBox.bottom ? "top" : "bottom";
				}
			}
		}
		function items() {
			return [...panelElement.value.querySelectorAll("button:not(:disabled):not([data-menu-secondary]), a[href], .workspace-menu > summary")].filter((item) => item.getClientRects().length && item.getAttribute("aria-disabled") !== "true" && (item.tagName === "SUMMARY" ? item.parentElement.parentElement.closest(".workspace-menu") : item.closest(".workspace-menu")) === menu.value);
		}
		function move(event) {
			if (props.disabled) {
				event.preventDefault();
				return;
			}
			if (props.inline) return;
			if (event.key === "Escape" && menu.value.open && !menu.value.querySelector("details[open]")) {
				event.preventDefault();
				event.stopPropagation();
				close(true);
				return;
			}
			if (event.key === "ArrowLeft" && props.submenu && menu.value.open) {
				event.preventDefault();
				event.stopPropagation();
				close(true);
				return;
			}
			if (event.key === "ArrowRight" && event.target.tagName === "SUMMARY" && event.target.parentElement !== menu.value) {
				event.preventDefault();
				event.stopPropagation();
				const child = event.target.parentElement;
				child.open = true;
				nextTick(() => child.querySelector(".account-panel button:not(:disabled)")?.focus());
				return;
			}
			if (event.target.closest("input, select, textarea, [role=\"combobox\"]")) return;
			if (![
				"ArrowDown",
				"ArrowUp",
				"Home",
				"End"
			].includes(event.key)) return;
			event.preventDefault();
			const backwards = event.key === "ArrowUp" || event.key === "End";
			if (!menu.value.open) {
				focusEdge = backwards ? "last" : "first";
				menu.value.open = true;
				toggled();
				return;
			}
			const buttons = items();
			const active = document.activeElement;
			const index = buttons.indexOf(active?.matches("[data-menu-secondary]") ? active.parentElement.querySelector("[data-menu-primary]") : active);
			buttons[event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : index < 0 ? backwards ? buttons.length - 1 : 0 : (index + (backwards ? -1 : 1) + buttons.length) % buttons.length]?.focus();
		}
		function toggled() {
			if (!menu.value) return;
			const opening = menu.value.open && !expanded.value;
			if (opening) emit("before-open");
			expanded.value = menu.value.open;
			if (!menu.value.open) {
				point = null;
				for (const child of menu.value.querySelectorAll("details[open]")) child.open = false;
			}
			document.removeEventListener("pointerdown", outside);
			document.removeEventListener("keydown", escape, true);
			document.removeEventListener("scroll", position, true);
			window.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("scroll", position);
			window.removeEventListener("windowgeometrychange", position);
			if (menu.value.open) {
				if (props.submenu) {
					for (const sibling of menu.value.parentElement.querySelectorAll(":scope > details[open]")) if (sibling !== menu.value) sibling.open = false;
				}
				if (props.modal && !panelElement.value.open) panelElement.value.showModal();
				else if (props.overlay && !props.modal && !panelElement.value.matches(":popover-open")) panelElement.value.showPopover();
				document.addEventListener("pointerdown", outside);
				document.addEventListener("keydown", escape, true);
				window.addEventListener("resize", position);
				window.visualViewport?.addEventListener("resize", position);
				window.visualViewport?.addEventListener("scroll", position);
				position();
				if (focusEdge) {
					const buttons = items();
					(focusEdge === "last" ? buttons.at(-1) : buttons[0])?.focus();
					focusEdge = null;
				} else if (opening && props.focusOnOpen && props.frameComposition) nextTick(() => items()[0]?.focus());
				if (opening && props.focusOnOpen && props.submenu && document.activeElement === trigger.value) nextTick(() => items()[0]?.focus());
				if (opening && props.focusOnOpen && !trigger.value.getClientRects().length) nextTick(() => (panelElement.value.querySelector("input:not([type=\"hidden\"]):not(:disabled), textarea:not(:disabled)") || items()[0])?.focus());
				window.addEventListener("windowgeometrychange", position);
				if (props.overlay) document.addEventListener("scroll", position, true);
			} else if (props.modal && panelElement.value.open) panelElement.value.close();
			else if (props.overlay && !props.modal && panelElement.value.matches(":popover-open")) panelElement.value.hidePopover();
		}
		function backdrop(event) {
			if (!props.modal || event.target !== panelElement.value) return;
			const box = panelElement.value.getBoundingClientRect();
			if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close(true);
		}
		function selected(event) {
			if (!menu.value) return;
			const action = event.target.closest("button, a[href]");
			if (action && !props.closeOnSelect) event.stopPropagation();
			if (props.closeOnSelect && action && !action.closest("[role=\"combobox\"]")) close(menu.value.contains(document.activeElement));
		}
		onUpdated(() => {
			if (props.disabled && menu.value?.open) close();
			else position();
		});
		__expose({
			close,
			openAt(event) {
				point = {
					x: event.clientX,
					y: event.clientY
				};
				returnTarget = event.target?.closest("[tabindex],button,a");
				menu.value.open = true;
				nextTick(() => {
					position();
					if (props.focusOnOpen && props.externalTrigger) panelElement.value?.querySelector("input:not(:disabled),select:not(:disabled),button:not(:disabled),a[href]")?.focus();
					else if (props.focusOnOpen && trigger.value?.getClientRects().length) trigger.value.focus();
				});
			},
			focusTrigger() {
				trigger.value?.focus();
			},
			get open() {
				return menu.value?.open;
			},
			set open(value) {
				if (menu.value) menu.value.open = value;
			}
		});
		onBeforeUnmount(() => {
			clearTimeout(hoverTimer);
			document.removeEventListener("pointerdown", outside);
			document.removeEventListener("keydown", escape, true);
			document.removeEventListener("scroll", position, true);
			window.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("scroll", position);
			window.removeEventListener("windowgeometrychange", position);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("details", {
				"data-menu-owner": "control",
				ref_key: "menu",
				ref: menu,
				class: normalizeClass(["workspace-menu", {
					"inline-menu": __props.inline,
					"frame-menu": __props.frameComposition,
					"process-picker-menu": __props.processPickerStyle,
					"labelled-menu": __props.showLabel,
					"compact-trigger": __props.compactTrigger
				}]),
				onKeydown: move,
				onToggle: toggled
			}, [withDirectives((openBlock(), createElementBlock("summary", {
				ref_key: "trigger",
				ref: trigger,
				class: "icon-button",
				"aria-label": __props.externalTrigger ? void 0 : unref(t)(__props.label),
				"aria-expanded": expanded.value,
				"aria-disabled": __props.disabled || void 0,
				tabindex: __props.disabled ? -1 : 0,
				onClick: activate,
				onPointerenter: hoverSubmenu,
				onPointerleave: cancelHover,
				onPointerdown: _cache[0] || (_cache[0] = ($event) => {
					cancelHover();
					isRef(point) ? point.value = null : point = null;
					unref(capturePress)($event);
					!__props.disabled && unref(ripple)($event);
				})
			}, [renderSlot(_ctx.$slots, "trigger", {}, () => [createVNode(_sfc_main$33, { name: __props.icon }, null, 8, ["name"]), __props.showLabel ? (openBlock(), createElementBlock("span", _hoisted_2$13, toDisplayString(unref(t)(__props.label)), 1)) : createCommentVNode("", true)]), __props.badgeCount > 0 ? (openBlock(), createElementBlock("span", _hoisted_3$10, toDisplayString(__props.badgeCount > 99 ? "99+" : __props.badgeCount), 1)) : createCommentVNode("", true)], 40, _hoisted_1$24)), [[vShow, !__props.externalTrigger], [unref(tooltipDirective), unref(t)(__props.label)]]), (openBlock(), createBlock(resolveDynamicComponent(__props.modal ? "dialog" : "div"), {
				ref_key: "panelElement",
				ref: panelElement,
				class: "account-panel",
				style: normalizeStyle([processPaint.value, __props.width ? { width: "min(" + __props.width + "px, calc(100dvw - " + (__props.frameComposition ? 8 : 16) + "px))" } : void 0]),
				"aria-label": __props.modal ? unref(t)(__props.label) : void 0,
				popover: __props.overlay && !__props.modal ? "manual" : void 0,
				onCancel: _cache[1] || (_cache[1] = withModifiers(($event) => close(true), ["prevent", "stop"])),
				onPointerdown: backdrop,
				onClick: selected,
				onTransitionend: withModifiers(position, ["self"])
			}, {
				default: withCtx(() => [renderSlot(_ctx.$slots, "default")]),
				_: 3
			}, 40, [
				"style",
				"aria-label",
				"popover"
			]))], 34);
		};
	}
};
//#endregion
//#region src/controls/AppDateField.vue
var _hoisted_1$23 = ["data-frame"];
var _hoisted_2$12 = {
	key: 0,
	class: "app-date-presentation",
	"aria-hidden": "true"
};
var _hoisted_3$9 = { class: "date-calendar" };
var _hoisted_4$5 = { class: "date-calendar-heading" };
var _hoisted_5$4 = ["aria-label"];
var _hoisted_6$3 = {
	key: 1,
	class: "calendar-empty"
};
var _hoisted_7$3 = {
	key: 0,
	class: "date-calendar-time"
};
var _hoisted_8$3 = { key: 0 };
var _hoisted_9$3 = { class: "date-time-spin" };
var _hoisted_10$2 = [
	"value",
	"max",
	"aria-label",
	"onInput",
	"onKeydown"
];
var _hoisted_11$1 = { class: "date-calendar-footer" };
var _sfc_main$25 = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppDateField",
	props: {
		modelValue: String,
		label: String,
		disabled: Boolean,
		readonly: Boolean,
		includeTime: {
			type: Boolean,
			default: false
		},
		monthOnly: {
			type: Boolean,
			default: false
		},
		allowClear: {
			type: Boolean,
			default: true
		},
		placeholder: String
	},
	emits: ["update:modelValue", "change"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const attrs = useAttrs();
		function inputAttrs() {
			return Object.fromEntries(Object.entries(attrs).filter(([name]) => ![
				"class",
				"style",
				"data-frame"
			].includes(name)));
		}
		const host = ref(null), field = ref(null), menu = ref(null), focused = ref(false), available = ref(0);
		const month = ref(/* @__PURE__ */ new Date()), pending = ref(/* @__PURE__ */ new Date()), hour = ref(0), minute = ref(0);
		let observer;
		const pad = (value) => String(value).padStart(2, "0");
		function parse$1(value) {
			return parse(value, props.includeTime);
		}
		const dateFormat = computed(() => new Intl.DateTimeFormat(appearance.language, {
			day: "numeric",
			month: "long",
			year: "numeric"
		}));
		function dateLabel(date) {
			const parts = Object.fromEntries(dateFormat.value.formatToParts(date).map((part) => [part.type, part.value]));
			return `${parts.day} ${parts.month} ${String(date.getFullYear()).padStart(4, "0")}`;
		}
		const presentation = computed(() => {
			const date = parse$1(props.modelValue);
			if (!date) return props.modelValue || "";
			if (props.monthOnly) return monthLabel(date, appearance.language);
			const label = dateLabel(date), full = label + " · " + pad(date.getHours()) + ":" + pad(date.getMinutes());
			if (!props.includeTime || !/[ T]\d{2}:\d{2}/.test(props.modelValue)) return label;
			if (!host.value) return full;
			const font = getComputedStyle(host.value), context = document.createElement("canvas").getContext("2d");
			context.font = `${font.fontWeight} ${font.fontSize} ${font.fontFamily}`;
			return context.measureText(full).width <= available.value - 49 ? full : label;
		});
		const heading = computed(() => new Intl.DateTimeFormat(appearance.language, {
			month: "long",
			year: "numeric"
		}).format(month.value));
		const weekdays = computed(() => Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(appearance.language, { weekday: "narrow" }).format(localDate(2024, 0, 1 + index))));
		const days = computed(() => {
			return monthDays(month.value.getFullYear(), month.value.getMonth());
		});
		function sameDay(date, day) {
			return date.getFullYear() === month.value.getFullYear() && date.getMonth() === month.value.getMonth() && date.getDate() === day;
		}
		function prepare() {
			const now = /* @__PURE__ */ new Date(), date = parse$1(props.modelValue) || now, explicit = /[ T]\d{2}:\d{2}/.test(props.modelValue || "");
			pending.value = date;
			month.value = localDate(date.getFullYear(), date.getMonth(), 1);
			hour.value = explicit ? date.getHours() : now.getHours();
			minute.value = explicit ? date.getMinutes() : 0;
		}
		function opened(event) {
			if (event.target !== menu.value?.$el || event.newState !== "open") return;
			nextTick(() => menu.value.$el.querySelector(".calendar-day.selected")?.focus());
		}
		function moveMonth(step) {
			month.value = localDate(month.value.getFullYear(), month.value.getMonth() + step, 1);
		}
		function accept(date) {
			if (props.disabled || props.readonly) return;
			if (date && props.includeTime && (!Number.isInteger(hour.value) || !Number.isInteger(minute.value) || hour.value < 0 || hour.value > 23 || minute.value < 0 || minute.value > 59)) {
				menu.value.$el.querySelector("input:invalid")?.reportValidity();
				return;
			}
			const value = date ? `${String(date.getFullYear()).padStart(4, "0")}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` + (props.includeTime ? `T${pad(hour.value)}:${pad(minute.value)}` : "") : "";
			field.value.$el.setCustomValidity("");
			emit("update:modelValue", value);
			emit("change", value);
			menu.value.close(true);
		}
		function validate(value) {
			field.value?.$el.setCustomValidity(value && !parse$1(value) ? t("Enter a valid date and time") : "");
		}
		function edit(value) {
			validate(value);
			emit("update:modelValue", value);
		}
		watch(() => props.modelValue, validate, { flush: "post" });
		function committed(event) {
			if (event.target.validity.valid) emit("change", event.target.value);
		}
		function timeValue(name) {
			return name === "hour" ? hour : minute;
		}
		function stepTime(name, step) {
			const value = timeValue(name);
			value.value = Math.max(0, Math.min(name === "hour" ? 23 : 59, Number(value.value) + step * (name === "hour" ? 1 : 5)));
		}
		function timeKey(event, name) {
			if (!["ArrowUp", "ArrowDown"].includes(event.key)) return;
			event.preventDefault();
			stepTime(name, event.key === "ArrowUp" ? 1 : -1);
		}
		function dayKey(event, day) {
			const step = {
				ArrowLeft: -1,
				ArrowRight: 1,
				ArrowUp: -7,
				ArrowDown: 7
			}[event.key];
			if (!step) return;
			event.preventDefault();
			event.stopPropagation();
			const date = localDate(month.value.getFullYear(), month.value.getMonth(), day + step);
			month.value = localDate(date.getFullYear(), date.getMonth(), 1);
			nextTick(() => menu.value.$el.querySelector(`[data-day="${date.getDate()}"]`)?.focus());
		}
		onMounted(() => {
			validate(props.modelValue);
			observer = new ResizeObserver((entries) => {
				available.value = entries[0].contentRect.width;
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: normalizeClass(["app-date-field", [unref(attrs).class, {
					focused: focused.value,
					disabled: __props.disabled
				}]]),
				style: normalizeStyle(unref(attrs).style),
				"data-frame": unref(attrs)["data-frame"]
			}, [
				createVNode(_sfc_main$29, mergeProps({
					ref_key: "field",
					ref: field
				}, inputAttrs(), {
					type: "text",
					"model-value": __props.modelValue,
					label: __props.label,
					placeholder: __props.placeholder || (__props.includeTime ? "YYYY-MM-DD HH:mm" : "YYYY-MM-DD"),
					disabled: __props.disabled,
					readonly: __props.readonly,
					"aria-invalid": __props.modelValue && !parse$1(__props.modelValue) || void 0,
					onFocus: _cache[0] || (_cache[0] = ($event) => focused.value = true),
					onBlur: _cache[1] || (_cache[1] = ($event) => focused.value = false),
					onChange: committed,
					"onUpdate:modelValue": edit
				}), null, 16, [
					"model-value",
					"label",
					"placeholder",
					"disabled",
					"readonly",
					"aria-invalid"
				]),
				!focused.value && __props.modelValue ? (openBlock(), createElementBlock("span", _hoisted_2$12, toDisplayString(presentation.value), 1)) : createCommentVNode("", true),
				createVNode(_sfc_main$26, {
					ref_key: "menu",
					ref: menu,
					"compact-trigger": "",
					class: "app-date-menu",
					label: __props.includeTime ? "Choose date and time" : "Choose date",
					disabled: __props.disabled || __props.readonly,
					overlay: "",
					"align-start": "",
					anchor: host.value,
					width: unref(controls).calendar.popupWidth,
					"close-on-select": false,
					onBeforeOpen: prepare,
					onToggle: opened
				}, {
					trigger: withCtx(() => [createVNode(_sfc_main$33, { name: "MDI_CALENDAR_MONTH" })]),
					default: withCtx(() => [createBaseVNode("div", _hoisted_3$9, [
						createBaseVNode("header", _hoisted_4$5, [
							createVNode(_sfc_main$34, {
								label: "Previous month",
								icon: "previous",
								"icon-only": "",
								onClick: _cache[2] || (_cache[2] = ($event) => moveMonth(-1))
							}),
							createBaseVNode("strong", null, toDisplayString(heading.value), 1),
							createVNode(_sfc_main$34, {
								label: "Next month",
								icon: "next",
								"icon-only": "",
								onClick: _cache[3] || (_cache[3] = ($event) => moveMonth(1))
							})
						]),
						createBaseVNode("div", {
							class: "date-calendar-grid",
							role: "group",
							"aria-label": heading.value
						}, [(openBlock(true), createElementBlock(Fragment, null, renderList(weekdays.value, (day, index) => {
							return openBlock(), createElementBlock("span", {
								key: "weekday" + index,
								class: "calendar-weekday"
							}, toDisplayString(day), 1);
						}), 128)), (openBlock(true), createElementBlock(Fragment, null, renderList(days.value, (day, index) => {
							return openBlock(), createElementBlock(Fragment, { key: index }, [day ? (openBlock(), createBlock(_sfc_main$34, {
								key: 0,
								class: normalizeClass(["calendar-day", {
									selected: sameDay(pending.value, day),
									today: sameDay(/* @__PURE__ */ new Date(), day)
								}]),
								"data-day": day,
								"aria-label": dateLabel(unref(localDate)(month.value.getFullYear(), month.value.getMonth(), day)),
								"aria-pressed": sameDay(pending.value, day),
								onKeydown: ($event) => dayKey($event, day),
								onClick: ($event) => accept(unref(localDate)(month.value.getFullYear(), month.value.getMonth(), day))
							}, {
								default: withCtx(() => [createTextVNode(toDisplayString(day), 1)]),
								_: 2
							}, 1032, [
								"class",
								"data-day",
								"aria-label",
								"aria-pressed",
								"onKeydown",
								"onClick"
							])) : (openBlock(), createElementBlock("span", _hoisted_6$3))], 64);
						}), 128))], 8, _hoisted_5$4),
						__props.includeTime ? (openBlock(), createElementBlock("div", _hoisted_7$3, [createBaseVNode("span", null, toDisplayString(unref(t)("Time")), 1), (openBlock(), createElementBlock(Fragment, null, renderList(["hour", "minute"], (name) => {
							return openBlock(), createElementBlock(Fragment, { key: name }, [name === "minute" ? (openBlock(), createElementBlock("span", _hoisted_8$3, ":")) : createCommentVNode("", true), createBaseVNode("div", _hoisted_9$3, [
								createVNode(_sfc_main$34, {
									label: name === "hour" ? "Decrease hours" : "Decrease minutes",
									icon: "MDI_CHEVRON_DOWN",
									"icon-only": "",
									disabled: timeValue(name).value <= 0,
									onClick: ($event) => stepTime(name, -1)
								}, null, 8, [
									"label",
									"disabled",
									"onClick"
								]),
								createBaseVNode("input", {
									value: pad(timeValue(name).value),
									form: "",
									type: "number",
									min: "0",
									max: name === "hour" ? 23 : 59,
									step: "1",
									"aria-label": unref(t)(name === "hour" ? "Hour" : "Minute"),
									onInput: ($event) => timeValue(name).value = $event.target.value === "" ? "" : Number($event.target.value),
									onKeydown: ($event) => timeKey($event, name)
								}, null, 40, _hoisted_10$2),
								createVNode(_sfc_main$34, {
									label: name === "hour" ? "Increase hours" : "Increase minutes",
									icon: "MDI_CHEVRON_UP",
									"icon-only": "",
									disabled: timeValue(name).value >= (name === "hour" ? 23 : 59),
									onClick: ($event) => stepTime(name, 1)
								}, null, 8, [
									"label",
									"disabled",
									"onClick"
								])
							])], 64);
						}), 64))])) : createCommentVNode("", true),
						createBaseVNode("footer", _hoisted_11$1, [__props.allowClear ? (openBlock(), createBlock(_sfc_main$34, {
							key: 0,
							label: "Clear",
							onClick: _cache[4] || (_cache[4] = ($event) => accept(null))
						})) : createCommentVNode("", true), createVNode(_sfc_main$34, {
							label: "Today",
							onClick: _cache[5] || (_cache[5] = ($event) => accept(/* @__PURE__ */ new Date()))
						})])
					])]),
					_: 1
				}, 8, [
					"label",
					"disabled",
					"anchor",
					"width"
				])
			], 14, _hoisted_1$23);
		};
	}
});
//#endregion
//#region src/controls/AppTextArea.vue
var _hoisted_1$22 = [
	"aria-invalid",
	"aria-label",
	"placeholder",
	"disabled"
];
var _sfc_main$24 = {
	__name: "AppTextArea",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		placeholder: String,
		disabled: Boolean,
		flat: Boolean,
		errorState: Boolean
	}, {
		"modelValue": {
			type: String,
			default: ""
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props, { expose: __expose }) {
		const model = useModel(__props, "modelValue");
		const field = ref(null);
		__expose({ focus() {
			field.value?.focus();
		} });
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("textarea", {
				ref_key: "field",
				ref: field,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				class: normalizeClass(["app-text-area", { "app-text-area-flat": __props.flat }]),
				"aria-invalid": __props.errorState || void 0,
				"aria-label": __props.label || __props.placeholder ? unref(t)(__props.label || __props.placeholder) : void 0,
				placeholder: unref(t)(__props.placeholder || ""),
				disabled: __props.disabled
			}, null, 10, _hoisted_1$22)), [[vModelText, model.value]]);
		};
	}
};
//#endregion
//#region src/controls/AppTabButton.vue
var _sfc_main$23 = {
	__name: "AppTabButton",
	props: { checked: Boolean },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$34, {
				class: "app-tab-button",
				"aria-pressed": __props.checked
			}, null, 8, ["aria-pressed"]);
		};
	}
};
//#endregion
//#region src/controls/AppCheckbox.vue
var _hoisted_1$21 = { class: "app-checkbox-indicator" };
var _hoisted_2$11 = [
	"id",
	"checked",
	"disabled",
	"indeterminate",
	"aria-label"
];
var _sfc_main$22 = {
	__name: "AppCheckbox",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		controlId: String,
		disabled: Boolean,
		indeterminate: Boolean,
		compact: Boolean,
		prominent: Boolean,
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
	emits: /*@__PURE__*/ mergeModels(["update:modelValue"], ["update:modelValue"]),
	setup(__props, { emit: __emit }) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const emit = __emit;
		function changed(event) {
			if (props.indeterminate) emit("update:modelValue", true);
			else model.value = event.target.checked;
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("label", { class: normalizeClass(["app-checkbox", {
				disabled: __props.disabled,
				compact: __props.compact,
				prominent: __props.prominent
			}]) }, [createBaseVNode("span", _hoisted_1$21, [createBaseVNode("input", {
				id: __props.controlId,
				type: "checkbox",
				checked: !__props.indeterminate && model.value,
				onChange: changed,
				disabled: __props.disabled,
				indeterminate: __props.indeterminate,
				"aria-label": __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : void 0
			}, null, 40, _hoisted_2$11), model.value || __props.indeterminate ? (openBlock(), createBlock(_sfc_main$33, {
				key: 0,
				name: __props.indeterminate ? "minus" : "check"
			}, null, 8, ["name"])) : createCommentVNode("", true)]), !__props.hideLabel ? renderSlot(_ctx.$slots, "default", {}, () => [createTextVNode(toDisplayString(__props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : ""), 1)], void 0, 0) : createCommentVNode("", true)], 2);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/search.mjs
function highlight(text, query, color = "") {
	const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		"\"": "&quot;",
		"'": "&#39;"
	})[character]);
	text = String(text || "");
	query = String(query || "").trim();
	if (!query) return escape(text);
	const index = text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
	const accent = /^#[0-9a-f]{6,8}$/i.test(String(color)) ? String(color) : "";
	return index < 0 ? escape(text) : escape(text.slice(0, index)) + (accent ? "<font color=\"" + accent + "\">" : "") + "<u>" + escape(text.slice(index, index + query.length)) + "</u>" + (accent ? "</font>" : "") + escape(text.slice(index + query.length));
}
//#endregion
//#region src/controls/AppSearchField.vue
var _sfc_main$21 = {
	components: {
		AppButton: _sfc_main$34,
		AppIcon: _sfc_main$33
	},
	props: {
		modelValue: String,
		placeholder: String,
		label: String,
		disabled: Boolean,
		readonly: Boolean,
		suggestions: {
			type: Array,
			default: () => []
		},
		error: String,
		boundary: Object,
		highlightQuery: String,
		openInNewTab: {
			type: Boolean,
			default: true
		}
	},
	emits: [
		"update:modelValue",
		"search",
		"accept",
		"open",
		"dismiss"
	],
	setup() {
		return { listId: useId() };
	},
	data() {
		return {
			opened: false,
			selected: -1
		};
	},
	watch: {
		suggestions() {
			this.selected = -1;
			this.show();
		},
		error() {
			this.show();
		},
		disabled(value) {
			if (value) this.close();
		},
		readonly(value) {
			if (value) this.close();
		}
	},
	mounted() {
		this.resize = new ResizeObserver(this.position);
		this.resize.observe(this.$el);
		document.addEventListener("pointerdown", this.outside);
		window.addEventListener("resize", this.position);
	},
	beforeUnmount() {
		clearTimeout(this.blurTimer);
		this.resize.disconnect();
		document.removeEventListener("pointerdown", this.outside);
		window.removeEventListener("resize", this.position);
	},
	methods: {
		t,
		highlight,
		focus() {
			this.$refs.input.focus();
		},
		close() {
			if (this.$refs.popup?.isConnected) this.$refs.popup.hidePopover();
			this.opened = false;
			this.selected = -1;
		},
		outside(event) {
			if (!this.$el.contains(event.target)) this.close();
		},
		blurred() {
			clearTimeout(this.blurTimer);
			this.blurTimer = setTimeout(() => {
				if (!this.$el.contains(document.activeElement)) this.close();
			}, 120);
		},
		edit(value) {
			if (this.disabled || this.readonly) return;
			this.close();
			this.$emit("update:modelValue", value);
		},
		async show() {
			await nextTick();
			if (!this.$refs.popup?.isConnected) return;
			if (this.disabled || this.readonly || !this.suggestions.length && !this.error) {
				this.close();
				return;
			}
			if (document.activeElement !== this.$refs.input) return;
			this.$refs.popup.showPopover();
			this.opened = true;
			this.position();
		},
		position() {
			if (!this.opened) return;
			const field = this.$el.getBoundingClientRect(), area = this.boundary?.getBoundingClientRect();
			const left = Math.max(0, area?.left || 0), right = Math.min(innerWidth, area?.right ?? innerWidth);
			const top = Math.max(0, area?.top || 0), bottom = Math.min(innerHeight, area?.bottom ?? innerHeight);
			const width = Math.min(Math.max(240, field.width), right - left - 8);
			const desired = this.error ? 50 : this.suggestions.length * 34 + 8;
			const below = bottom - field.bottom - 10, above = field.top - top - 10;
			const up = below < Math.min(desired, 180) && above > below;
			const height = Math.min(desired, Math.max(0, up ? above : below));
			Object.assign(this.$refs.popup.style, {
				width: width + "px",
				maxHeight: height + "px",
				left: Math.max(left + 4, Math.min(field.left, right - width - 4)) + "px",
				top: (up ? field.top - height - 6 : field.bottom + 6) + "px"
			});
		},
		async key(event) {
			if (event.isComposing) return;
			if (event.key === "Escape") {
				event.preventDefault();
				event.stopPropagation();
				this.close();
				this.$emit("dismiss");
				return;
			}
			if (event.key === "Enter") {
				event.preventDefault();
				if (this.opened && this.selected >= 0) this.choose(this.selected, event.altKey);
				else {
					this.close();
					this.$emit("search");
				}
			} else if (this.opened && this.suggestions.length && ["ArrowDown", "ArrowUp"].includes(event.key)) {
				event.preventDefault();
				this.selected = event.key === "ArrowDown" ? Math.min(this.suggestions.length - 1, this.selected + 1) : this.selected <= 0 ? this.suggestions.length - 1 : this.selected - 1;
				await nextTick();
				this.$refs.popup.querySelector("#" + CSS.escape(this.listId + "-" + this.selected))?.scrollIntoView({ block: "nearest" });
			}
		},
		choose(index, newTab = false) {
			const record = this.suggestions[index];
			this.close();
			this.focus();
			this.$emit(newTab ? "open" : "accept", record);
		}
	}
};
var _hoisted_1$20 = [
	"value",
	"placeholder",
	"aria-label",
	"aria-controls",
	"aria-expanded",
	"aria-activedescendant",
	"disabled",
	"readonly"
];
var _hoisted_2$10 = {
	ref: "popup",
	popover: "manual",
	class: "search-suggestions"
};
var _hoisted_3$8 = {
	key: 0,
	role: "status"
};
var _hoisted_4$4 = ["id", "aria-label"];
var _hoisted_5$3 = [
	"id",
	"aria-selected",
	"onPointerenter"
];
var _hoisted_6$2 = {
	role: "gridcell",
	class: "search-suggestion-content"
};
var _hoisted_7$2 = ["innerHTML"];
var _hoisted_8$2 = ["innerHTML"];
var _hoisted_9$2 = { key: 0 };
var _hoisted_10$1 = {
	key: 0,
	role: "gridcell"
};
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppButton = resolveComponent("AppButton");
	return openBlock(), createElementBlock("div", {
		class: "workspace-search app-search-field",
		role: "search",
		onFocusout: _cache[7] || (_cache[7] = (...args) => $options.blurred && $options.blurred(...args))
	}, [
		createVNode(_component_AppIcon, {
			name: "search",
			onClick: _cache[0] || (_cache[0] = ($event) => {
				$options.focus();
				_ctx.$refs.input.select();
			})
		}),
		createBaseVNode("input", {
			ref: "input",
			type: "search",
			role: "combobox",
			enterkeyhint: "search",
			autocomplete: "off",
			value: $props.modelValue,
			placeholder: $props.placeholder,
			"aria-label": $options.t($props.label),
			"aria-autocomplete": "list",
			"aria-haspopup": "grid",
			"aria-controls": $setup.listId,
			"aria-expanded": $data.opened,
			"aria-activedescendant": $data.opened && $data.selected >= 0 ? $setup.listId + "-" + $data.selected : void 0,
			disabled: $props.disabled,
			readonly: $props.readonly,
			onInput: _cache[1] || (_cache[1] = ($event) => $options.edit($event.target.value)),
			onFocus: _cache[2] || (_cache[2] = (...args) => $options.show && $options.show(...args)),
			onKeydown: _cache[3] || (_cache[3] = (...args) => $options.key && $options.key(...args))
		}, null, 40, _hoisted_1$20),
		$props.modelValue ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			"icon-only": "",
			label: "Clear search",
			icon: "close",
			disabled: $props.disabled || $props.readonly,
			onClick: _cache[4] || (_cache[4] = ($event) => {
				$options.edit("");
				$options.focus();
			})
		}, null, 8, ["disabled"])) : createCommentVNode("", true),
		createBaseVNode("div", _hoisted_2$10, [$props.error ? (openBlock(), createElementBlock("p", _hoisted_3$8, toDisplayString($options.t($props.error)), 1)) : (openBlock(), createElementBlock("div", {
			key: 1,
			id: $setup.listId,
			role: "grid",
			"aria-label": $options.t("Search suggestions")
		}, [(openBlock(true), createElementBlock(Fragment, null, renderList($props.suggestions, (record, index) => {
			return openBlock(), createElementBlock("div", {
				id: $setup.listId + "-" + index,
				key: index,
				role: "row",
				class: normalizeClass(["search-suggestion-row", { selected: $data.selected === index }]),
				"aria-selected": $data.selected === index,
				onPointerenter: ($event) => $data.selected = index
			}, [createBaseVNode("div", _hoisted_6$2, [createVNode(_component_AppButton, {
				"aria-label": record.title,
				title: record.title + (record.description ? " — " + record.description : ""),
				onPointerdown: _cache[5] || (_cache[5] = withModifiers(() => {}, ["prevent"])),
				onClick: ($event) => $options.choose(index),
				onAuxclick: withModifiers(($event) => $event.button === 1 && $options.choose(index, true), ["prevent"])
			}, {
				default: withCtx(() => [
					createVNode(_component_AppIcon, { name: "search" }),
					createBaseVNode("strong", { innerHTML: $options.highlight(record.title, $props.highlightQuery ?? $props.modelValue) }, null, 8, _hoisted_7$2),
					createBaseVNode("span", { innerHTML: $options.highlight(record.description ? "– " + record.description : "", $props.highlightQuery ?? $props.modelValue) }, null, 8, _hoisted_8$2),
					record.keyword ? (openBlock(), createElementBlock("small", _hoisted_9$2, "#" + toDisplayString(record.keyword), 1)) : createCommentVNode("", true)
				]),
				_: 2
			}, 1032, [
				"aria-label",
				"title",
				"onClick",
				"onAuxclick"
			])]), $props.openInNewTab ? (openBlock(), createElementBlock("div", _hoisted_10$1, [createVNode(_component_AppButton, {
				"icon-only": "",
				icon: "MDI_OPEN_IN_NEW",
				label: "Open result in new tab",
				"aria-label": $options.t("Open {title} in new tab", { title: record.title }),
				disabled: !record.code && record.id == null,
				onPointerdown: _cache[6] || (_cache[6] = withModifiers(() => {}, ["prevent"])),
				onClick: ($event) => $options.choose(index, true)
			}, null, 8, [
				"aria-label",
				"disabled",
				"onClick"
			])])) : createCommentVNode("", true)], 42, _hoisted_5$3);
		}), 128))], 8, _hoisted_4$4))], 512)
	], 32);
}
var AppSearchField_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$21, [["render", _sfc_render$1]]);
//#endregion
//#region src/controls/ItemPreview.vue
var colorProbe;
var variableRoles = Object.fromEntries(Object.entries(cssRoles).map(([role, variable]) => ["var(" + variable + ")", role]));
var _sfc_main$20 = {
	components: {
		AppIcon: _sfc_main$33,
		BusyIndicator: BusyIndicator_default
	},
	props: {
		source: String,
		file: File,
		fallbackText: String,
		fallbackIcon: String,
		foreground: String,
		accent: String,
		round: Boolean,
		outlined: Boolean,
		selected: Boolean,
		loading: Boolean,
		previewSize: Number,
		fillMode: {
			type: String,
			default: "cover"
		}
	},
	emits: ["ready", "failed"],
	data() {
		return {
			localUrl: "",
			broken: false,
			request: 0
		};
	},
	computed: {
		pending() {
			return this.loading || this.url.startsWith("pending-preview:");
		},
		url() {
			return this.localUrl || this.source || "";
		},
		fallbackPaint() {
			const role = variableRoles[this.accent] || this.accent;
			let accent = frameColors.value[role] || frameColors.value.contentAccent || frameColors.value.action;
			let cssAccent = cssColor(accent);
			if (this.accent && !frameColors.value[role]) {
				colorProbe ||= document.createElement("canvas").getContext("2d", { willReadFrequently: true });
				colorProbe.clearRect(0, 0, 1, 1);
				colorProbe.fillStyle = "#000000";
				colorProbe.fillStyle = this.accent;
				colorProbe.fillRect(0, 0, 1, 1);
				accent = [...colorProbe.getImageData(0, 0, 1, 1).data].slice(0, 3);
				cssAccent = this.accent;
			}
			const shade = blend(accent, [
				0,
				0,
				0
			], 1 - 1 / (this.round ? 1.35 : 1.65));
			return {
				"--preview-accent": cssAccent,
				color: this.foreground || cssColor(readableText(shade))
			};
		}
	},
	watch: {
		file: {
			immediate: true,
			handler(file) {
				const request = ++this.request;
				this.localUrl = "";
				if (!file) return;
				const reader = new FileReader();
				reader.onload = () => {
					if (request === this.request) this.localUrl = reader.result;
				};
				reader.readAsDataURL(file);
			}
		},
		url() {
			this.broken = false;
		}
	},
	beforeUnmount() {
		this.request++;
	},
	methods: { t }
};
var _hoisted_1$19 = ["aria-busy"];
var _hoisted_2$9 = ["src", "alt"];
var _hoisted_3$7 = {
	key: 2,
	"aria-hidden": "true"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_BusyIndicator = resolveComponent("BusyIndicator");
	const _component_AppIcon = resolveComponent("AppIcon");
	return openBlock(), createElementBlock("div", {
		class: normalizeClass(["image-picker-preview item-preview", {
			"round-preview": $props.round,
			"outlined-preview": $props.outlined,
			"selected-preview": $props.selected
		}]),
		"aria-busy": $options.pending || void 0,
		style: normalizeStyle({
			...$options.fallbackPaint,
			"--preview-icon-size": $props.previewSize == null ? void 0 : ($props.previewSize > 40 ? 22 : 16) + "px",
			"--preview-text-size": $props.previewSize == null ? void 0 : ($props.previewSize > 40 ? 10 : 8) + "px"
		})
	}, [$options.url && !$options.pending && !$data.broken ? (openBlock(), createElementBlock("img", {
		key: 0,
		src: $options.url,
		style: normalizeStyle({ objectFit: $props.fillMode }),
		alt: $options.t("Preview image"),
		loading: "lazy",
		decoding: "async",
		onLoad: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("ready", $event.target)),
		onError: _cache[1] || (_cache[1] = ($event) => {
			$data.broken = true;
			_ctx.$emit("failed");
		})
	}, null, 44, _hoisted_2$9)) : $options.pending ? (openBlock(), createBlock(_component_BusyIndicator, {
		key: 1,
		running: "",
		style: {
			width: "min(24px,45%)",
			height: "min(24px,45%)"
		}
	})) : $props.fallbackText ? (openBlock(), createElementBlock("span", _hoisted_3$7, toDisplayString($props.fallbackText), 1)) : $props.fallbackIcon ? (openBlock(), createBlock(_component_AppIcon, {
		key: 3,
		name: $props.fallbackIcon
	}, null, 8, ["name"])) : createCommentVNode("", true)], 14, _hoisted_1$19);
}
var ItemPreview_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$20, [["render", _sfc_render]]);
//#endregion
//#region src/controls/UserIdentity.vue
var _hoisted_1$18 = { class: "user-identity-text" };
var _hoisted_2$8 = {
	key: 0,
	class: "muted"
};
var _hoisted_3$6 = {
	key: 0,
	class: "muted identity-retired"
};
var _sfc_main$19 = {
	__name: "UserIdentity",
	props: {
		login: String,
		displayName: String,
		initials: String,
		avatarUrl: String,
		avatarColor: String,
		retired: Boolean,
		avatarSize: {
			type: Number,
			default: 40
		},
		emphasized: Boolean
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				class: normalizeClass(["user-identity", {
					retired: __props.retired,
					emphasized: __props.emphasized
				}]),
				style: normalizeStyle({ "--avatar-size": __props.avatarSize + "px" })
			}, [
				createVNode(ItemPreview_default, {
					source: __props.avatarUrl,
					"fallback-text": __props.initials,
					"fallback-icon": "person",
					accent: __props.avatarColor,
					"preview-size": __props.avatarSize,
					round: "",
					outlined: ""
				}, null, 8, [
					"source",
					"fallback-text",
					"accent",
					"preview-size"
				]),
				createBaseVNode("span", _hoisted_1$18, [createBaseVNode("strong", null, toDisplayString(__props.displayName || __props.login), 1), __props.login && __props.displayName !== __props.login ? (openBlock(), createElementBlock("small", _hoisted_2$8, toDisplayString(__props.login), 1)) : createCommentVNode("", true)]),
				__props.retired ? (openBlock(), createElementBlock("span", _hoisted_3$6, [createVNode(_sfc_main$33, { name: "archive" }), createTextVNode(toDisplayString(unref(t)("Retired")), 1)])) : createCommentVNode("", true)
			], 6);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/display/progress.mjs
function fraction(value, minimum = 0, maximum = 1) {
	if (typeof value !== "number" || !isFinite(value)) return null;
	if (maximum <= minimum) return 0;
	return Math.max(0, Math.min(1, (value - minimum) / (maximum - minimum)));
}
//#endregion
//#region src/controls/AppProgress.vue
var _hoisted_1$17 = [
	"aria-label",
	"aria-valuemin",
	"aria-valuemax",
	"aria-valuenow"
];
var AppProgress_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "AppProgress",
	props: {
		label: String,
		value: Number,
		min: {
			type: Number,
			default: 0
		},
		max: {
			type: Number,
			default: 1
		}
	},
	setup(__props) {
		const props = __props;
		const position = computed(() => fraction(props.value, props.min, props.max));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				class: normalizeClass(["app-progress", { determinate: position.value !== null }]),
				role: "progressbar",
				"aria-label": unref(t)(__props.label),
				"aria-valuemin": position.value !== null ? __props.min : void 0,
				"aria-valuemax": position.value !== null ? __props.max : void 0,
				"aria-valuenow": position.value !== null ? Math.max(__props.min, Math.min(__props.max, __props.value)) : void 0,
				style: normalizeStyle({ "--progress-value": position.value })
			}, null, 14, _hoisted_1$17);
		};
	}
}, [["__scopeId", "data-v-079e775b"]]);
//#endregion
//#region src/controls/display/EmptyState.vue
var _hoisted_1$16 = ["role"];
var _hoisted_2$7 = { key: 0 };
var _hoisted_3$5 = { key: 1 };
var _sfc_main$17 = {
	__name: "EmptyState",
	props: {
		title: String,
		message: String,
		icon: {
			type: String,
			default: "info"
		},
		action: Object,
		error: Boolean
	},
	emits: ["action"],
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "empty-state",
				role: __props.error ? "alert" : "status"
			}, [
				createVNode(_sfc_main$33, {
					name: __props.icon,
					class: normalizeClass({ "error-icon": __props.error })
				}, null, 8, ["name", "class"]),
				__props.title ? (openBlock(), createElementBlock("strong", _hoisted_2$7, toDisplayString(unref(t)(__props.title)), 1)) : createCommentVNode("", true),
				__props.message ? (openBlock(), createElementBlock("p", _hoisted_3$5, toDisplayString(unref(t)(__props.message)), 1)) : createCommentVNode("", true),
				__props.action ? (openBlock(), createBlock(_sfc_main$34, {
					key: 2,
					label: __props.action.label,
					icon: __props.action.icon,
					disabled: __props.action.disabled,
					onClick: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("action", __props.action.command))
				}, null, 8, [
					"label",
					"icon",
					"disabled"
				])) : createCommentVNode("", true)
			], 8, _hoisted_1$16);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/core/strings.mjs
var russian = {
	"Search this page…": "Поиск по странице…",
	"Choose a configured page filter": "Выберите настроенный фильтр страницы",
	"Choose a suggestion or enter Field: value": "Выберите подсказку или введите Поле: значение",
	"Choose a value": "Выберите значение",
	"Backend server": "Сервер ТС",
	"Worker processes and server restart": "Процессы и перезапуск сервера",
	"Server processes": "Процессы сервера",
	"Running web workers": "Работает веб-процессов",
	"Restart TACTIC Stream": "Перезапустить ТС",
	"Restarting TACTIC Stream…": "ТС перезапускается…",
	"TACTIC Stream restarted": "ТС перезапущен",
	"Save changes before restarting.": "Сохраните изменения перед перезапуском.",
	"Saved settings are applied only after restarting the server.": "Сохранённые настройки применяются после перезапуска сервера.",
	"This server is not managed by TacticMonitor.": "Этот сервер запущен без TacticMonitor.",
	"The server monitor is unavailable or outdated.": "Монитор сервера недоступен или требует обновления.",
	"The server has not returned yet. Reconnect and check its status.": "Сервер ещё не ответил. Подключитесь заново и проверьте его состояние.",
	"Restart TACTIC Stream? Connections and running operations may be interrupted while saved settings are applied. Unsaved changes will not be applied.": "Перезапустить ТС? Соединения и текущие операции могут прерваться при применении сохранённых настроек. Несохранённые изменения применены не будут.",
	"Web workers": "Веб-воркеры",
	"Something went wrong": "Произошла ошибка",
	"Search suggestions": "Подсказки поиска",
	Example: "Пример",
	"Search failed": "Не удалось выполнить поиск",
	"Context menu": "Контекстное меню",
	More: "Ещё",
	"No results": "Нет результатов",
	"Image preview": "Предпросмотр изображения",
	"Source code": "Исходный код",
	Graph: "Граф",
	Activate: "Нажать",
	"In progress": "В работе",
	"Open menu": "Открыть меню",
	"Open dialog": "Открыть диалог",
	"Changes stay in this example.": "Изменения остаются в этом примере.",
	"Resizable panels": "Изменяемые панели",
	"Resize panels": "Изменить размер панелей",
	"Drop files here or choose a file above.": "Перетащите файлы сюда или выберите файл выше.",
	"Mouse, keyboard and touch": "Мышь, клавиатура и касания",
	Activated: "Срабатываний",
	Pressed: "Нажатий",
	Empty: "Пусто",
	Confirmation: "Подтверждение",
	"Choose an action": "Выберите действие",
	"No changes": "Без изменений",
	"Semantic colors": "Смысловые цвета",
	"Sizes and icons": "Размеры и иконки",
	Counters: "Счётчики",
	"Two-line list": "Двухстрочный список",
	"Section heading": "Заголовок раздела",
	"Panel heading": "Заголовок панели",
	"Native controls": "Компоненты QML",
	"Vue controls": "Компоненты Vue",
	"Standalone example not added yet": "Отдельный живой пример пока не добавлен",
	"Component showcase": "Каталог компонентов",
	"Foundations, controls and interaction states": "Основа, компоненты и состояния",
	"Search components": "Найти компонент",
	"All component groups": "Все группы компонентов",
	"Live example": "Живой пример",
	"Catalogue entry": "Справочная карточка",
	"Component state": "Состояние компонента",
	"Code example": "Пример кода",
	"Local demo; project data stays unchanged": "Локальный пример без изменений данных проекта",
	"No matching components": "Компоненты не найдены",
	"Project chat rules": "Правила чатов проекта",
	"Shared by all chats in this project. Changes apply on the next send; the current turn keeps its captured rules.": "Общие для всех чатов проекта. Изменения действуют со следующей отправки; текущий ход сохранит прежние правила.",
	"Describe naming, preview destinations and comment preferences.": "Опишите нейминг, назначение превью и правила комментариев.",
	"Save project rules": "Сохранить правила",
	"Project chat rules changed. Reopen the editor before saving.": "Правила чатов проекта изменились. Откройте редактор заново перед сохранением.",
	"Project chat rules must be text of at most 16000 characters": "Правила чатов проекта должны содержать не более 16000 символов",
	"Select a user project before editing chat rules": "Выберите пользовательский проект для настройки правил чата",
	"Reconnect the agent to load project chat rules": "Переподключите агента, чтобы загрузить правила чатов проекта",
	Plugins: "Плагины",
	"Packages, versions and project activation": "Пакеты, версии и активация в проекте",
	"Install plugin ZIP": "Установить ZIP плагина",
	"Upload plugin file": "Загрузить файл плагина",
	"ZIP archives (*.zip)": "Архивы ZIP (*.zip)",
	"All files (*)": "Все файлы (*)",
	"System Info": "Информация о системе",
	"Server and client diagnostics": "Сведения о сервере и клиенте",
	"Node Name": "Имя узла",
	Release: "Выпуск ОС",
	Machine: "Архитектура",
	"CPU Count": "Число процессоров",
	OS: "Операционная система",
	"Server time (UTC)": "Время сервера (UTC)",
	"User Agent": "User Agent",
	"TACTIC User": "Пользователь TACTIC",
	"Mail Server": "Почтовый сервер",
	"Asset Folders": "Каталоги файлов",
	"Server handoff directory": "Каталог передачи на сервере",
	"Writable (access check)": "Доступен для записи (проверка прав)",
	"None configured": "Не настроено",
	Browser: "Браузер",
	"Time zone": "Часовой пояс",
	"Load Balancing": "Балансировка нагрузки",
	"Performance Test": "Тест производительности",
	"Sample server requests to identify responding workers and ports.": "Проверка отвечающих серверных процессов и портов по серии запросов.",
	"Build the Users table definition and read its rows through sequential and parallel requests.": "Загрузка описания таблицы пользователей и её строк последовательными и параллельными запросами.",
	"Test load balancing": "Проверить балансировку",
	"Test performance": "Проверить производительность",
	"Email Send Test": "Отправить тестовое письмо",
	"No mail server is configured": "Почтовый сервер не настроен",
	"Test client handoff": "Проверить передачу файлов",
	"Link Test": "Проверка страниц",
	"Open the project pages in browser windows. This can take a few minutes.": "Открыть страницы проекта в окнах браузера. Это может занять несколько минут.",
	"Include built-in pages": "Включить встроенные страницы",
	"Run link test": "Открыть страницы",
	"No project pages configured": "Страницы проекта не настроены",
	"Python Script Test": "Проверка Python-скрипта",
	"Script Path": "Путь скрипта",
	"Running test…": "Выполняется проверка…",
	Sequential: "Последовательно",
	Parallel: "Параллельно",
	request: "запрос",
	requests: "запросов",
	"parallel requests": "параллельных запросов",
	"Observed workers": "Обнаружено процессов",
	"This sample does not show the configured worker count.": "Выборка не показывает настроенное число процессов.",
	Ports: "Порты",
	Samples: "Замеров",
	Accessible: "Доступен",
	"Not accessible": "Недоступен",
	"Email sent successfully": "Письмо успешно отправлено",
	"Script completed": "Скрипт выполнен",
	"Opened pages": "Открыто страниц",
	"Allow pop-ups to open all pages": "Разрешите всплывающие окна, чтобы открыть все страницы",
	"The browser cannot inspect client folders. Run this test in TACTIC Handler.": "Браузер не может проверить локальные каталоги. Запустите эту проверку в ТХ.",
	"Test cancelled": "Проверка отменена",
	"Please enter a valid script path": "Укажите корректный путь сохранённого скрипта",
	"Choose sender and recipient emails": "Укажите отправителя и получателей письма",
	"System Info requires administrator access": "Информация о системе доступна только администратору",
	"Preparing the local agent environment…": "Подготовка локального окружения агента…",
	"Choose computer": "Выберите компьютер",
	"TACTIC server": "Сервер Тактика",
	"External agent": "Внешний агент",
	"This computer": "Этот компьютер",
	"Disconnected desktop": "ТХ отключён",
	"Open TACTIC Handler to connect locally, or choose TACTIC server.": "Для локального подключения откройте ТХ или выберите сервер Тактика.",
	"Disconnect the current agent before starting it on another computer.": "Отключите текущего агента перед запуском на другом компьютере.",
	"Uses Codex sign-in and local API addresses on the selected computer.": "Вход в Codex и локальные адреса API используются на выбранном компьютере.",
	"Run agent on": "Запустить агента на",
	"Choose the computer that will run the agent": "Выберите компьютер для запуска агента",
	"Open TACTIC Handler on the selected computer and sign in to the same account.": "Откройте ТХ на выбранном компьютере и войдите в ту же учётную запись.",
	"TACTIC Handler did not accept the connection request. Open it and try again.": "ТХ не принял запрос на подключение. Откройте его и повторите попытку.",
	"The local agent stopped unexpectedly. Reconnect it to try again.": "Локальный агент неожиданно остановился. Подключите его повторно.",
	"Local agent dependency installation timed out. Check the network and retry.": "Истекло время установки окружения агента. Проверьте сеть и повторите попытку.",
	"Find a project by name or code": "Найти проект по названию или коду",
	"Custom rule: its effect depends on the plugin or script that checks it.": "Кастомное правило: его действие зависит от плагина или скрипта, который его проверяет.",
	"Application features": "Функции приложения",
	"Choose access to individual application features. Legacy rules are marked explicitly.": "Доступ к отдельным функциям приложения. Старые правила отмечены явно.",
	"Application feature": "Функция приложения",
	"Sidebar navigation": "Навигация по проекту",
	"Show the project navigation sidebar in the legacy interface.": "Показ боковой панели навигации по проекту в старом интерфейсе.",
	Administration: "Администрирование",
	"Open administration in the legacy interface. Modern administration still requires an administrator.": "Открытие старой админки. Современная админка по-прежнему требует прав администратора.",
	"Script editor": "Редактор скриптов",
	"Open the legacy script editor. This does not grant permission to execute scripts.": "Открытие старого редактора скриптов. Само по себе не разрешает выполнение скриптов.",
	"Schema navigation": "Навигация по схеме",
	"Show the schema section of the legacy sidebar.": "Показ раздела схемы в старой боковой панели.",
	"Saved views": "Сохранённые представления",
	"Open and save personal views in the legacy interface.": "Открытие и сохранение личных представлений в старом интерфейсе.",
	"Private notes": "Приватные заметки",
	"Read private notes belonging to other users. The server checks this rule when retrieving notes.": "Чтение приватных заметок других пользователей. Сервер проверяет это правило при получении заметок.",
	"Table column manager": "Настройка колонок таблицы",
	"Open the column manager in the legacy interface.": "Открытие настройки колонок в старом интерфейсе.",
	"Template projects": "Проекты-шаблоны",
	"Show template projects in the legacy project list.": "Показ проектов-шаблонов в старом списке проектов.",
	"Project creation": "Создание проектов",
	"Create projects through the legacy interface. Modern project creation still requires an administrator.": "Создание проектов через старый интерфейс. Современное создание проектов требует прав администратора.",
	"Export all rows to CSV": "Экспорт всех строк в CSV",
	"Export all search results, beyond the current page, in the legacy interface.": "Экспорт всех результатов поиска, включая другие страницы, в старом интерфейсе.",
	"CSV import": "Импорт CSV",
	"Import records from CSV through the legacy interface.": "Импорт записей из CSV через старый интерфейс.",
	"Archive and delete records": "Архивация и удаление записей",
	"Show archive and delete operations in the legacy interface. Record permissions are checked separately.": "Показ архивации и удаления в старом интерфейсе. Права на записи проверяются отдельно.",
	"Edit records": "Редактирование записей",
	"Show record editing in the legacy interface. Record and field permissions are checked separately.": "Показ редактирования в старом интерфейсе. Права на записи и поля проверяются отдельно.",
	"Checked by the server.": "Проверяется сервером.",
	"Legacy interface rule: this does not control the modern TH/TS screen.": "Правило старого интерфейса: не управляет соответствующим экраном современных ТХ/ТС.",
	"Deny access": "Запретить доступ",
	"Allow access": "Разрешить доступ",
	"Existing access: {access}. It is preserved until you choose Allow or Deny. Use Advanced rules for other native access levels.": "Сохранённый уровень: {access}. Он останется до выбора разрешения или запрета. Другие уровни доступны в расширенных правилах.",
	"This is the selected group's rule, not the user's final access. Other groups can grant access; administrators bypass these rules. Use Effective permissions to inspect a user.": "Это правило выбранной группы. Другие группы могут разрешить доступ; администраторы обходят эти правила. Итог смотрите в «Итоговых правах».",
	"Rule key: {key}": "Ключ правила: {key}",
	"Use inherited access": "Использовать наследование",
	"Removes only this rule from the group draft. Other groups and native defaults still apply. Save to apply the change.": "Удаляет только это правило из черновика группы. Права других групп и базовые правила остаются. Для применения сохраните изменения.",
	"Allowed by this group": "Разрешено этой группой",
	"Denied by this group": "Запрещено этой группой",
	"Existing access: {access}": "Сохранённый уровень: {access}",
	"Select a user": "Выберите пользователя",
	"Select a user to inspect saved permissions.": "Выберите пользователя, чтобы посмотреть его действующие права.",
	"Permission summary": "Сводка разрешений",
	"Groups and inheritance": "Группы и наследование",
	"Rule sources": "Источники правил",
	"AI and MCP tools": "Инструменты ИИ и MCP",
	"Effective permissions": "Итоговые права",
	"Inspect saved user permissions and their source groups.": "Просмотр действующих прав пользователя и групп, от которых они получены.",
	"AI tools": "Инструменты ИИ",
	"MCP tools": "Инструменты MCP",
	"Agent access": "Доступ агента",
	"Choose which tools this group can use through the agent chat.": "Выберите доступные группе инструменты чата с агентом.",
	"Choose which tools this group can expose through MCP.": "Выберите доступные группе инструменты MCP.",
	"System defaults": "Системные правила",
	"Direct group": "Прямая группа",
	"Inherited group": "Унаследованная группа",
	"Combined native access level": "Общий штатный уровень доступа",
	"Administrator access required": "Требуются права администратора",
	"Save or discard changes to inspect saved user permissions.": "Сохраните или отмените изменения, чтобы проверить действующие права пользователя.",
	"Native administrator: full application rights. Explicit AI and MCP restrictions still apply.": "Администратор: полные штатные права. Явные ограничения ИИ и MCP продолжают действовать.",
	"Saved native rules from all groups. Record filters, field rules and operation checks still apply.": "Действующие штатные правила всех групп. Дополнительно действуют ограничения записей, полей и проверки конкретных операций.",
	"Group tool policy": "Инструменты группы",
	"Selected tools": "Выбранные инструменты",
	"All tools": "Все инструменты",
	"Read tools": "Для чтения",
	"Tool access combines all inherited groups. A local deny does not cancel another group grant. Native operation rights and the connection scope still apply.": "Учитываются все унаследованные группы. Локальный запрет не отменяет разрешение другой группы. Права на операции и ограничения подключения продолжают действовать.",
	"This server does not expose the agent tool catalogue.": "Этот сервер не предоставляет каталог инструментов агента.",
	"Changes data": "Изменяет данные",
	Interface: "Интерфейс",
	Advanced: "Дополнительно",
	"Other rule": "Другое правило",
	"Choose the groups whose permissions are inherited.": "Выберите группы, от которых наследуются права.",
	"Choose which projects each group can open.": "Настройте, какие проекты доступны каждой группе.",
	"Choose which sidebar links each group can see.": "Настройте видимость пунктов навигации для каждой группы.",
	"Choose which menu actions each group can use.": "Выберите доступные каждой группе действия меню.",
	"Control access to entity types in this project.": "Настройте доступ к типам объектов этого проекта.",
	"Control access to the project workflow processes.": "Настройте доступ к процессам пайплайнов проекта.",
	"Control access to task workflow statuses.": "Настройте доступ к статусам пайплайнов задач.",
	"Set permissions for individual records or record keys.": "Настройте права на отдельные записи или ключи объектов.",
	"Control access to individual entity fields.": "Настройте доступ к отдельным полям объектов.",
	"Configure the native built-in application permissions.": "Настройте штатные разрешения приложения.",
	"Limit the records a group can find using native search rules.": "Ограничьте доступные группе записи штатными правилами поиска.",
	"Inspect and edit native rules, defaults and custom XML.": "Просматривайте и редактируйте правила, значения по умолчанию и XML.",
	"Groups and projects": "Группы и проекты",
	"Data and workflow": "Данные и процессы",
	Allowed: "Разрешено",
	Denied: "Запрещено",
	Inherited: "Наследуется",
	"Group inheritance": "Наследование прав",
	"Inherit permissions from": "Наследовать права от групп",
	"This inheritance would create a cycle.": "Это наследование создаст циклическую связь.",
	"This group inherits permissions from the selected groups. For the same rule key, the highest access wins; a deny does not cancel another grant.": "Группа наследует права выбранных групп. Для одинакового ключа действует наивысший уровень доступа: запрет не отменяет разрешение из другого правила.",
	"Other inherited groups: {groups}": "Другие наследуемые группы: {groups}",
	"TACTIC administrator access is required": "Необходимы права администратора TACTIC",
	"Only a TACTIC administrator can create users": "Создавать пользователей может только администратор TACTIC",
	"TACTIC Handler only": "Только в ТХ",
	"TACTIC Handler with a connected DCC": "ТХ с подключённым DCC",
	"Server Python": "Серверный Python",
	"Server JavaScript": "Серверный JavaScript",
	"Browser JavaScript": "JavaScript в браузере",
	"Item preview · Sample data": "Предпросмотр · Пример данных",
	"Example item": "Пример элемента",
	"Example value": "Пример значения",
	"Example description": "Пример описания",
	"Example status": "Пример статуса",
	"Example process": "Пример процесса",
	"Example author": "Пример автора",
	"Back to item layout": "Назад к макету элемента",
	"Edit nested item layout": "Изменить вложенный макет элемента",
	"Referenced item layout is unavailable": "Связанный макет элемента недоступен",
	"The original configuration source is unavailable": "Исходное определение конфигурации недоступно",
	"Return to a parent layout before opening another nested layout": "Вернись к родительскому макету перед открытием следующего вложенного макета",
	"Back to page layout": "Назад к макету страницы",
	"Edit linked page layout": "Изменить макет связанной страницы",
	"Edit table columns": "Изменить колонки таблицы",
	Results: "Результаты",
	"Page region": "Область страницы",
	Header: "Шапка",
	Footer: "Футер",
	"Page regions are only available for top-level blocks": "Область страницы задаётся только для блоков верхнего уровня",
	Secondary: "Вторичный",
	Surface: "Поверхность",
	"Value color": "Цвет значения",
	Yellow: "Жёлтый",
	"Invalid field value colors": "Некорректные цвета значений поля",
	"Invalid field display format": "Некорректный формат поля",
	"Corner radius must be between 0 and 48": "Радиус углов должен быть от 0 до 48",
	"Search objects": "Поиск объектов",
	"Invalid nested search text": "Некорректный текст поиска",
	"Invalid suggestion scope": "Некорректная область поиска подсказок",
	"This Search Type has no searchable title": "У этого серч-тайпа нет текстового поля для поиска",
	"Preview size": "Размер предпросмотра",
	"Automatic width": "Автоматическая ширина",
	"Preview width in pixels": "Ширина предпросмотра в пикселях",
	"Canvas zoom": "Масштаб холста",
	"Fit width": "Вписать по ширине",
	Fit: "Вписать",
	Phone: "Телефон",
	Tablet: "Планшет",
	Desktop: "Десктоп",
	Wide: "Широкий экран",
	"Enter a preview width from 320 to 3840 pixels, or leave it empty for Auto.": "Укажите ширину от 320 до 3840 пикселей или оставьте поле пустым для автоширины.",
	"Choose an available canvas zoom": "Выберите доступный масштаб холста",
	"Duplicate widget": "Дублировать виджет",
	"Parent container": "Родительский контейнер",
	"A widget cannot contain itself": "Виджет не может содержать сам себя",
	"Choose a row, column or details container": "Выберите строку, колонку или контейнер деталей",
	"A container supports up to 32 widgets": "Контейнер поддерживает до 32 виджетов",
	"A dashboard supports one items workspace": "Дашборд поддерживает одно дерево итемов",
	Undo: "Отменить",
	Redo: "Повторить",
	"Group label (optional)": "Название группы (необязательно)",
	"Shared page filters": "Общие фильтры страницы",
	"Apply the same condition to several widgets. Runtime values do not change the saved page.": "Одно условие для нескольких виджетов. Текущие значения не изменяют сохранённую страницу.",
	"Page filter": "Фильтр страницы",
	"Add page filter": "Добавить общий фильтр",
	"Filter label": "Название фильтра",
	"Enabled by default": "Включён по умолчанию",
	"Remove page filter": "Удалить общий фильтр",
	"Filter binding": "Привязка фильтров",
	"Match the same data source": "По совпадению источника",
	"Choose fields explicitly": "Выбрать поля явно",
	"Not applied": "Не применяется",
	"Grouping and aggregates": "Группировка и итоги",
	"Totals use all matching records before the displayed group limit.": "Итоги рассчитываются по всем подходящим записям до ограничения числа групп.",
	"Group field": "Поле группировки",
	"Group interval": "Период группировки",
	"Field value": "Значение поля",
	"Year (UTC)": "Год (UTC)",
	"Month (UTC)": "Месяц (UTC)",
	"Day (UTC)": "День (UTC)",
	"Remove group": "Удалить группировку",
	"Add grouping": "Добавить группировку",
	"Measure label": "Название показателя",
	Aggregate: "Агрегация",
	Count: "Количество",
	Sum: "Сумма",
	Average: "Среднее",
	"Measure field": "Поле показателя",
	"All rows (count only)": "Все записи (только количество)",
	"Remove measure": "Удалить показатель",
	"Add measure": "Добавить показатель",
	"Group order": "Порядок групп",
	"By group": "По группировке",
	"Largest first (first measure)": "По первому показателю: убывание",
	"Smallest first (first measure)": "По первому показателю: возрастание",
	"Maximum groups": "Максимум групп",
	"Chart measure": "Показатель графика",
	"Chart type": "Тип диаграммы",
	"Raised card": "Приподнятая карточка",
	"Line chart": "Линия",
	"Donut chart": "Кольцо",
	"Donut charts require non-negative values": "Кольцевая диаграмма требует неотрицательных значений",
	"Bar chart": "Столбчатый график",
	Chart: "График",
	"Grouped report": "Сводная таблица",
	"No matching report data": "Нет подходящих данных",
	"No value": "Нет значения",
	"Group limit reached. Refine filters or increase the limit.": "Достигнут лимит групп. Уточните фильтры или увеличьте лимит.",
	"A page supports at most eight shared filters": "Допускается не более восьми общих фильтров",
	"Choose a page filter": "Выберите фильтр страницы",
	"Unsupported page filter property": "Неподдерживаемое свойство общего фильтра",
	"Choose a data widget": "Выберите виджет данных",
	"Report dimension limit reached": "Достигнут лимит группировок или показателей",
	"Choose a report field": "Выберите поле отчёта",
	"Invalid report dimensions or limit": "Недопустимые группировки, показатели или лимит",
	"Invalid report ordering": "Недопустимый порядок групп",
	"Date grouping requires a date or timestamp field": "Для группировки по периоду выберите поле даты или времени",
	"Choose a supported aggregate": "Выберите поддерживаемую агрегацию",
	"This aggregate requires a numeric field": "Для этой агрегации требуется числовое поле",
	"Choose distinct report groups": "Группировки не должны повторяться",
	"Report groups require existing scalar fields": "Для группировки выберите существующие простые поля",
	"Report measure names must be unique": "Имена показателей не должны повторяться",
	"Choose an existing report measure": "Выберите существующий показатель",
	"A metric requires one aggregate without grouping": "Для счётчика нужен один показатель без группировки",
	"Choose an existing report field": "Выберите существующее поле отчёта",
	"Report aggregate is not a finite number": "Результат агрегации не является конечным числом",
	"Page filter names must be unique": "Имена общих фильтров не должны повторяться",
	"Choose configured page filters": "Выберите настроенные фильтры страницы",
	"Invalid page filter values": "Недопустимые значения фильтров страницы",
	"Page filter mapping requires existing filters and fields": "В привязке нужны существующие фильтры и поля",
	"Mapped page filter fields must have the same data type": "Типы полей общей привязки должны совпадать",
	"Grouping and aggregates belong to report widgets": "Группировки и показатели доступны в виджетах отчётов",
	"Filters require a scalar field": "Для фильтра нужно простое поле",
	"Enter a text value for this field": "Введите текстовое значение для этого поля",
	"Text pattern filters require a text field": "Для текстового шаблона выберите текстовое поле",
	Data: "Данные",
	Layout: "Размещение",
	"Data settings apply to this widget only.": "Настройки данных относятся только к этому виджету.",
	"Content source": "Источник содержимого",
	"Static text": "Обычный текст",
	"Current project": "Текущий проект",
	"Specific record": "Конкретная запись",
	"Data source": "Источник данных",
	"Record type": "Тип объекта",
	"Any record type": "Любой тип объекта",
	"Choose a data source": "Выберите источник данных",
	"Loading source fields…": "Загружаем поля источника…",
	"Saved view": "Сохранённый вид",
	"Find record": "Поиск записи",
	"Find records": "Найти записи",
	"Source record": "Запись-источник",
	"Choose a record": "Выберите запись",
	"More matches. Refine your search.": "Совпадений больше. Уточните поиск.",
	"Source field": "Поле источника",
	"Choose a source field": "Выберите поле источника",
	Filters: "Фильтры",
	"All conditions must match (AND).": "Должны выполняться все условия.",
	"Filter field": "Поле условия",
	"Remove condition": "Удалить условие",
	"Filter condition": "Условие отбора",
	"Less than": "Меньше",
	"At most": "Не больше",
	"Greater than": "Больше",
	"At least": "Не меньше",
	"Matches text pattern": "Соответствует шаблону",
	"Use % to match any text, for example %robot%.": "Знак % обозначает любой текст. Пример: %robot%.",
	"Add condition": "Добавить условие",
	Unavailable: "Недоступно",
	"Choose Yes or No": "Выберите Да или Нет",
	"Enter a valid number": "Введите корректное число",
	"Choose a valid date": "Выберите корректную дату",
	"Choose a supported field binding": "Выберите поддерживаемую привязку поля",
	"Place selection-bound widgets inside Details": "Поместите виджет привязки к выбранному объекту внутрь панели подробностей",
	"Unsupported data property": "Неподдерживаемое свойство данных",
	"Filters belong to a data collection": "Фильтры применяются к списку данных",
	"Select at most 32 filter conditions": "Допускается не более 32 условий",
	"Choose a data source first": "Сначала выберите источник данных",
	"Choose a filter condition": "Выберите условие отбора",
	"Choose a field from the current data source": "Выберите поле текущего источника данных",
	"Choose a supported filter condition": "Выберите поддерживаемое условие",
	"Unsupported filter property": "Неподдерживаемое свойство условия",
	"Select a data source in the current project": "Выберите источник данных в текущем проекте",
	"The record belongs to another data source": "Запись принадлежит другому источнику данных",
	"Enter at most 256 characters to find records": "Для поиска записи введите не более 256 символов",
	"Choose a source record": "Выберите запись-источник",
	"Field bindings belong to Text or Markdown widgets": "Привязки полей доступны для виджетов текста и Markdown",
	"Static text cannot also reference a field": "Обычный текст не должен одновременно ссылаться на поле",
	"This binding cannot also reference a fixed record": "Эта привязка не должна одновременно ссылаться на конкретную запись",
	"Choose the selected record type for this field": "Выберите тип объекта для этого поля",
	"Choose an existing source field": "Выберите существующее поле источника",
	"Empty values require Is empty or Is not empty": "Для пустого значения выберите Пусто или Не пусто",
	"Enter a filter value or choose Is empty": "Введите значение условия или выберите Пусто",
	"Use literal filter values; native expressions and the NULL keyword are not supported here": "Введите обычное значение: выражения и служебное слово NULL здесь не поддерживаются",
	"Format XML": "Форматировать XML",
	"Clean preview": "Чистое превью",
	"Back to editing": "К редактированию",
	"Read-only draft preview. Nothing is saved.": "Просмотр черновика. Изменения не сохраняются.",
	"Click to select. Alt-click for underlying layers.": "Клик — выбор. Alt + клик — слой под выбранным.",
	"Items preview shows up to three records.": "В предпросмотре итемов — до трёх записей.",
	Height: "Высота",
	"Move element": "Переместить элемент",
	"Page layouts": "Макеты страниц",
	"Item layouts": "Макеты карточек",
	"Whole pages linked from navigation": "Страницы, открываемые из навигации",
	"Object cards and reusable item views": "Карточки объектов и повторно используемые виды",
	"Page layout": "Макет страницы",
	"New page": "Новая страница",
	"Page name": "Имя страницы",
	"Choose a page or create a new page.": "Выберите страницу или создайте новую.",
	"Page blocks": "Слои страницы",
	"Edit page layout": "Редактировать макет страницы",
	"Edit card layout": "Редактировать карточку",
	"Remove widget": "Удалить виджет",
	"Remove this widget from the page?": "Удалить этот виджет со страницы?",
	"Flexible width": "Вес по ширине",
	Padding: "Внутренние отступы",
	Margin: "Внешние отступы",
	Gap: "Интервал",
	Top: "Сверху",
	Left: "Слева",
	Markdown: "Markdown",
	Metric: "Счётчик",
	"Select element": "Выбрать элемент",
	"Resize element": "Изменить размер элемента",
	"Enter a page name and title": "Введите имя и заголовок страницы",
	"Enter spacing from 0 to 256": "Введите отступ от 0 до 256",
	"Select a page block": "Выберите элемент страницы",
	"The selected element no longer exists": "Выбранный элемент больше не существует",
	"Choose Grid in the parent container to position elements": "Для размещения элементов выберите «Сетка» в родительском контейнере",
	"No saved result was found. Save again to retry the same operation.": "Сохранённый результат не найден. Повторите сохранение, чтобы повторить ту же операцию.",
	"Move elements within their grid. Resize using the handles.": "Перемещайте элементы по сетке. Для изменения размеров используйте ручки выделения.",
	"Add a widget to start this page.": "Добавьте виджет, чтобы начать эту страницу.",
	"New view": "Новый вид",
	"Add a widget to start this view.": "Добавьте виджет, чтобы начать этот вид.",
	Views: "Виды",
	"Open saved view": "Открыть сохранённый вид",
	"Starting point": "Основа",
	"Create draft": "Создать черновик",
	"Discard changes to the current view and continue?": "Отменить изменения текущего вида и продолжить?",
	"Select an item": "Выберите элемент слева",
	"Loading...": "Загрузка…",
	"Search in this branch": "Поиск в этой ветке",
	"Found: {count}": "Найдено: {count}",
	"No results found": "Ничего не найдено",
	"Clear filter": "Очистить фильтр",
	"Agent link — includes access and startup instructions": "Ссылка для агента — доступ и стартовые инструкции",
	"Copy agent link": "Скопировать ссылку для агента",
	"Collect connection token": "Получить токен подключения",
	"MCP connections": "MCP-подключения",
	"External access is limited to this project and the tools you select. Revoke it at any time.": "Внешний доступ ограничен этим проектом и выбранными инструментами. Его можно отозвать в любой момент.",
	"Enable external MCP connections in Server configuration and restart first.": "Включите внешние MCP-подключения в настройках сервера и перезапустите его.",
	"Instructions for this connection": "Инструкции для этого подключения",
	"5 minutes": "5 минут",
	"1 hour": "1 час",
	"8 hours": "8 часов",
	"Allowed tools": "Разрешённые инструменты",
	"Select read tools": "Выбрать инструменты чтения",
	"Select all tools": "Выбрать все инструменты",
	"No expiration": "Без срока",
	"MCP access lifetime must be zero or between 5 and 480 minutes": "Срок MCP-доступа должен быть равен нулю или составлять от 5 до 480 минут",
	"Copy this connection now. The access token will not be shown again.": "Скопируйте подключение сейчас. Токен доступа больше не будет показан.",
	"Copy connection": "Скопировать подключение",
	"Existing connections": "Созданные подключения",
	Revoked: "Доступ отозван",
	Expired: "Срок истёк",
	"Revoke access": "Отозвать доступ",
	"Create connection": "Создать подключение",
	"MCP connections could not be loaded": "Не удалось загрузить MCP-подключения",
	"Navigation color": "Цвет в навигации",
	"Optional #RRGGBB override; leave empty to use the Search Type color.": "Необязательный цвет #RRGGBB; оставьте пустым для цвета типа объектов.",
	"How this item appears in project navigation. Selection follows your theme.": "Оформление пункта в навигации проекта. Выделение соответствует теме.",
	"Agent permissions": "Разрешения агента",
	"Conversation context": "Контекст беседы",
	"Use in current conversation": "Контекст для текущей беседы",
	"Conversation project": "Проект бесед",
	"All projects": "Все проекты",
	"Some project histories are unavailable": "История некоторых проектов недоступна",
	"Reading tasks": "Чтение задач",
	"Preparing task changes": "Подготовка изменений задач",
	"Saving tasks": "Сохранение задач",
	"Updating task statuses": "Изменение статусов задач",
	"Conversation view": "Вид бесед",
	"Back to conversations": "Вернуться к беседам",
	Conversations: "Беседы",
	"Show conversations": "Показать беседы",
	"Hide conversations": "Скрыть беседы",
	"Conversation settings": "Настройки беседы",
	"Conversation name": "Название беседы",
	"Conversation folder": "Папка бесед",
	"New conversation folder": "Новая папка бесед",
	"Edit conversation folder": "Изменить папку бесед",
	"Folder name": "Название папки",
	"Pin conversation": "Закрепить беседу",
	"Pinned conversations": "Закреплённые",
	"Group conversations": "Группировка бесед",
	"By time": "По времени",
	"By folder": "По папкам",
	Ungrouped: "Без папки",
	"Search conversations": "Поиск бесед",
	"No conversations found": "Беседы не найдены",
	"No conversations yet": "Бесед пока нет",
	Yesterday: "Вчера",
	"Previous 7 days": "Предыдущие 7 дней",
	"Previous 30 days": "Предыдущие 30 дней",
	"Older conversations": "Ранее",
	"Archived conversations": "Архив бесед",
	"Archive conversation": "Архивировать беседу",
	"Restore conversation": "Восстановить беседу",
	"Archived conversation — restore it to continue": "Беседа в архиве — восстановите её для продолжения",
	"Remove folder": "Удалить папку",
	"Remove this folder? Its conversations will move to Ungrouped.": "Удалить папку? Её беседы перейдут в «Без папки».",
	"Load more conversations": "Загрузить ещё беседы",
	"Conversations panel width": "Ширина панели бесед",
	"Conversation settings changed. Reload before saving.": "Настройки беседы изменились. Обновите данные перед сохранением.",
	"Conversation folders changed. Reload before saving.": "Папки бесед изменились. Обновите данные перед сохранением.",
	"Choose an existing conversation folder": "Выберите существующую папку бесед",
	"Wait for the current turn before archiving this conversation": "Дождитесь завершения текущего запроса перед архивацией беседы",
	"Restore this conversation before sending a message": "Восстановите беседу перед отправкой сообщения",
	"A conversation folder with this name already exists": "Папка бесед с таким названием уже существует",
	"Conversation folder is unavailable": "Папка бесед недоступна",
	"Use at most 100 conversation folders": "Можно создать не более 100 папок бесед",
	"Send or clear the current draft before opening another object": "Отправьте или очистите текущий черновик, прежде чем открывать другой объект",
	Provider: "Провайдер",
	"AI providers": "ИИ-провайдеры",
	"AI connection": "ИИ-подключение",
	"New connection": "Новое подключение",
	"Connection name": "Название подключения",
	Provider: "Провайдер",
	"Enable connection": "Включить подключение",
	"Default connection": "Подключение по умолчанию",
	"Account authorization": "Авторизация аккаунта",
	"Codex account": "Аккаунт Codex",
	"OpenAI-compatible API": "OpenAI-совместимый API",
	"Local model server": "Локальный сервер моделей",
	"Codex uses the account signed in on the external host. Provider API keys are not required.": "Codex использует аккаунт, в который выполнен вход на внешнем хосте. API-ключ не требуется.",
	"API base URL": "Базовый адрес API",
	"API key": "API-ключ",
	"Default model": "Модель по умолчанию",
	"The external host connects to this address. Localhost means the machine running that host.": "Внешний хост подключается по этому адресу. Localhost означает компьютер, на котором работает хост.",
	"A key is stored. Leave empty to keep it.": "Ключ сохранён. Оставьте поле пустым, чтобы сохранить его.",
	"Write-only credential. It is encrypted and never returned to this form.": "Ключ шифруется и никогда не возвращается в эту форму.",
	"Remove stored API key": "Удалить сохранённый API-ключ",
	"Host key environment variable": "Переменная окружения хоста с ключом",
	"Optional alternative to a stored API key. Enter the variable name, not its value.": "Вместо сохранённого ключа можно указать имя переменной окружения хоста. Введите имя, а не значение.",
	"Project data": "Данные проекта",
	"Check connection": "Проверить подключение",
	"Chat messages, project context and attachments go only to the selected connection after Send. Connection checks do not send project data.": "Сообщения, контекст проекта и вложения передаются только выбранному подключению после отправки. Проверка связи не передаёт данные проекта.",
	"Configure a connection, then check it from the external host.": "Настройте подключение и проверьте его с внешнего хоста.",
	"Connection checked": "Подключение проверено",
	"Connection failed": "Ошибка подключения",
	"Connection has not been checked": "Подключение не проверено",
	"Waiting for the external host": "Ожидание внешнего хоста",
	"Manage AI connections": "Настроить ИИ-подключения",
	"Configure account-owned connections for Codex, OpenAI, compatible and local APIs, Anthropic and Gemini.": "Настройте подключения своего аккаунта: Codex, OpenAI, совместимые и локальные API, Anthropic и Gemini.",
	"Allow requested changes": "Разрешить запрошенные изменения",
	"Allow internet access": "Разрешить доступ в интернет",
	"Downloading reference file": "Скачиваю референс",
	"Reading file history": "Читаю историю файлов",
	"Reading object definition": "Читаю определение объекта",
	"Reading project relationships": "Читаю связи проекта",
	"Creating project objects": "Создаю объекты проекта",
	"Reading object relationships": "Читаю связи объектов",
	"Linking project objects": "Связываю объекты проекта",
	Working: "В работе",
	Attachments: "Вложения",
	"Reading conversation context": "Читаю контекст беседы",
	"Checking available tools": "Проверяю доступные инструменты",
	"Reading TACTIC documentation": "Читаю документацию Тактика",
	"Reading selected objects": "Читаю выделенные объекты",
	"Reading project objects": "Читаю объекты проекта",
	"Reading workflows": "Читаю пайплайны",
	"Saving workflow": "Сохраняю пайплайн",
	"Checking in attached files": "Регистрирую приложенные файлы",
	"Checking saved changes": "Проверяю сохранённые изменения",
	"Reading naming rules": "Читаю правила нейминга",
	"Checking file naming": "Проверяю имена файлов",
	"Viewing attached image": "Просматриваю приложенное изображение",
	"Searching the web": "Ищу в интернете",
	"New conversation": "Новый чат",
	Conversation: "Переписка",
	"Context details": "Подробности контекста",
	"Selected objects": "Выделенные объекты",
	You: "Вы",
	Agent: "Агент",
	"Attach files": "Прикрепить файлы",
	"Paste attachment": "Вставить вложение",
	"Remove attachment": "Убрать вложение",
	Model: "Модель",
	"Agent default": "Выбор агента",
	"Reasoning effort": "Уровень размышления",
	"Extra high": "Очень высокий",
	Minimal: "Минимальный",
	Maximum: "Максимальный",
	Ultra: "Ультра",
	"What would you like to change?": "Что хочешь изменить?",
	"Describe the task. Attach files or paste an image.": "Опиши задачу. Прикрепи файлы или вставь картинку.",
	"Add a correction while the agent works": "Уточни задачу, пока агент работает",
	"Send correction": "Отправить уточнение",
	"Correction queued": "Уточнение ожидает доставки",
	"Waiting for your reply": "Агент ждёт твоего ответа",
	"Task blocked — see the answer": "Задача не выполнена — смотри ответ",
	"Task completed": "Задача выполнена",
	"Agent finished — review the answer": "Агент закончил — проверь ответ",
	"Working with TACTIC tools…": "Работа с инструментами Тактика…",
	"Operation details": "Подробности операций",
	"Undo field change": "Отменить правку",
	"Each attachment must be at most 64 MB": "Размер одного вложения — не больше 64 МБ",
	"Attach at most 20 files": "Прикрепи не больше 20 файлов",
	"Press Ctrl+V in the message to attach clipboard files or images": "Нажми Ctrl+V в поле сообщения, чтобы прикрепить файлы или картинки из буфера",
	"Last agent field change undone": "Последняя правка полей агентом отменена",
	"Agent request worker is unavailable": "Обработчик обращений к агенту недоступен",
	"Request queued": "В очереди",
	"Agent working": "Выполняется",
	"Request cancelling": "Отменяется",
	"Request cancelled": "Отменено",
	"Request completed": "Завершено",
	"Request failed": "Ошибка",
	"Request interrupted": "Прервано",
	"External agent": "Внешний агент",
	"Agent requests": "Обращения к агенту",
	"New request": "Новое обращение",
	"External agent connected": "Внешний агент подключён",
	"External agent is offline": "Внешний агент не подключён",
	"Context sent to the agent": "Контекст обращения",
	"What should the agent do?": "Что должен сделать агент?",
	"Allow the requested configuration changes": "Разрешить запрошенные изменения конфигурации",
	"Send to agent": "Отправить агенту",
	"Cancel request": "Отменить обращение",
	"Agent progress and answer": "Ход работы и ответ агента",
	"The answer and operation results will appear here.": "Здесь появятся ответ и результаты операций.",
	"Script activation remains a separate action in the Script Editor.": "Активация скриптов выполняется отдельно в редакторе скриптов.",
	"Select a project before contacting the agent": "Перед обращением к агенту выберите проект",
	"External agent started": "Внешний агент начал работу",
	"External agent disconnected. Inspect changes before sending a new request.": "Связь с агентом потеряна. Проверьте изменения перед новым обращением.",
	"Cancelled. Changes already applied are preserved; inspect them before retrying.": "Отменено. Уже применённые изменения сохранены; проверьте их перед повтором.",
	"Agent request failed": "Не удалось выполнить обращение к агенту",
	"Stale source": "Исходник изменился",
	"Historical report": "Исторический отчёт",
	"Agent drafts": "Черновики агента",
	"Back to editor": "Назад в редактор",
	"Agent draft": "Черновик агента",
	"Refresh agent drafts": "Обновить черновики агента",
	"Ready for source review": "Готово к проверке исходника",
	"Fresh passing trials are required": "Нужны успешные прогоны с текущими зависимостями",
	"Select an agent draft": "Выберите черновик агента",
	"Current dependencies": "Текущие зависимости",
	"Stale dependencies": "Зависимости изменились",
	"Runs on the Handler desktop after activation.": "После активации выполняется в ТХ.",
	"Draft source": "Исходник черновика",
	"No isolated trial reports yet.": "Отчётов изолированной проверки пока нет.",
	"Isolated trial reports": "Отчёты изолированной проверки",
	"I reviewed the source, binding and execution owner": "Я проверил(а) исходник, привязку и место выполнения",
	"Confirm activation on the desktop": "Подтвердить активацию для ТХ",
	"Activate reviewed draft": "Активировать проверенный черновик",
	"External host reports do not replace source review.": "Отчёты внешнего исполнителя не заменяют проверку исходника.",
	"Administrator initialization was cancelled or failed.": "Первичная установка отменена или завершилась ошибкой.",
	"Local server did not start. See server/temp/log/desktop.log.": "Локальный сервер не запустился. См. server/temp/log/desktop.log.",
	"Local server stopped. See server/temp/log/desktop.log in the data directory.": "Локальный сервер остановился. См. server/temp/log/desktop.log в каталоге данных.",
	"Allow this permission?": "Разрешить этот доступ?",
	"Close with unsaved changes?": "Закрыть с несохранёнными изменениями?",
	"Keep open": "Оставить открытым",
	Allow: "Разрешить",
	"Choose file": "Выбрать файл",
	"Choose files": "Выбрать файлы",
	"Clear file": "Убрать файл",
	"No file selected": "Файл не выбран",
	"This configured publish form contains unsupported fields or actions": "Форма публикации содержит неподдерживаемые поля или действия",
	"Multi Publish": "Групповая публикация",
	"New object": "Новый объект",
	"Invalid publish view": "Некорректный вид публикации",
	"Unsupported form operation": "Неподдерживаемая операция формы",
	"Server worker is unavailable": "Обработчик серверного запроса недоступен",
	"Check saved changes": "Проверить сохранение",
	"Unable to reach the server.": "Не удалось связаться с сервером.",
	"Parent group": "Группа по родителю",
	"Change parent": "Изменить родителя",
	"Find parent": "Найти родителя",
	"Current parent": "Текущий родитель",
	"Selected parent": "Выбранный родитель",
	"No parent": "Нет родителя",
	"No parent selected": "Родитель не выбран",
	"Parent unavailable": "Родитель недоступен",
	"Available parents": "Доступные родители",
	"No matching parents": "Подходящие родители не найдены",
	"Add Another Item": "Добавить ещё объект",
	"Drop one parent object": "Перетащите один родительский объект",
	"Discard this draft?": "Отменить изменения черновика?",
	"Invalid parent response": "Некорректный ответ при выборе родителя",
	"Unable to verify the parent change": "Не удалось проверить результат смены родителя",
	"Invalid parent table scope": "Некорректная область таблицы родителей",
	"This object is not available in parent groups": "Этот объект недоступен для группировки по родителю",
	"Invalid parent operation": "Некорректная операция с родителем",
	"Choose a configured parent column": "Выберите настроенную колонку родителя",
	"Invalid parent search": "Некорректный поиск родителя",
	"The parent belongs to another project": "Родитель относится к другому проекту",
	"Open parent editing in the source project": "Откройте выбор родителя в исходном проекте",
	"The configured parent action changed. Reload before saving.": "Настройка смены родителя изменилась. Обновите данные перед сохранением.",
	"Unsupported parent action options": "Эти параметры смены родителя не поддерживаются",
	"Parent revisions require a transactional database lock": "Для проверки ревизии родителя нужна транзакционная блокировка БД",
	"Parent changed. Reload before saving.": "Родитель или запись изменились. Обновите данные перед сохранением.",
	"The configured parent relationship is unavailable": "Настроенная родительская связь недоступна",
	"Parent is no longer available": "Родитель больше недоступен",
	"Choose a current parent": "Выберите действующего родителя",
	"Parent relationship is cyclic": "Родительская связь образует цикл",
	Upstream: "Входящие",
	Inputs: "Входные зависимости",
	Downstream: "Исходящие",
	Instance: "Экземпляр",
	"File references": "Ссылки файлов",
	"Unresolved references": "Неопределённые ссылки",
	"No dependencies": "Нет зависимостей",
	"No snapshot found": "Снапшот не найден",
	"Cyclic dependency": "Циклическая зависимость",
	"Dependencies changed. Reload this snapshot.": "Зависимости изменились. Обновите снапшот.",
	"Open dependencies in the source project": "Откройте зависимости в исходном проекте",
	"Open dependencies in the snapshot project": "Откройте зависимости в проекте снапшота",
	"Invalid dependency page": "Недопустимая страница зависимостей",
	"Invalid dependency file": "Недопустимый файл зависимости",
	"Invalid dependency file range": "Недопустимый диапазон файлов зависимости",
	"Dependency file is no longer available": "Файл зависимости больше недоступен",
	"This object is not available in Dependencies": "Этот объект недоступен в зависимостях",
	"Object summary": "Сводка объекта",
	Connections: "Связи",
	"No connections": "Нет связей",
	"Object is unavailable": "Объект недоступен",
	"Remove connection": "Удалить связь",
	"Remove this connection? The connected objects will be kept.": "Удалить эту связь? Связанные объекты будут сохранены.",
	"Invalid connection direction": "Недопустимое направление связи",
	"Invalid connection icon size": "Недопустимый размер миниатюры связи",
	"Invalid connection table scope": "Недопустимый набор объектов для таблицы связей",
	"Select a connection before removing it": "Перед удалением выберите связь",
	"Reload the connection before removing it": "Перед удалением обновите связь",
	"The connection belongs to another project": "Связь относится к другому проекту",
	"Connection changed. Reload before removing it.": "Связь изменилась. Перед удалением обновите её.",
	"Could not confirm removal of the connection": "Не удалось подтвердить удаление связи",
	"Check out": "Получить файлы",
	"Cancel transfer": "Отменить передачу",
	Files: "Файлы",
	Downloading: "Загрузка",
	Overwrite: "Перезаписать",
	"Check out completed": "Файл получен",
	"Download completed": "Файл скачан",
	"Download cancelled": "Загрузка отменена",
	"The local file differs from the server. Replace it?": "Локальный файл отличается от серверного. Заменить его?",
	"Snapshot is no longer available": "Снапшот больше недоступен",
	"Close the current checkout before selecting another snapshot": "Закройте текущее окно получения файлов перед выбором другого снапшота",
	"This file already has an active transfer": "Этот файл уже передаётся",
	"Check out requires a snapshot": "Для получения файлов выберите снапшот",
	"Open the snapshot in its own project before checking out files": "Перед получением файлов откройте снапшот в его проекте",
	"Download private message attachments from Messages": "Скачивайте приватные вложения из раздела Сообщения",
	"Sequence and UDIM checkout is not available in this table yet": "Получение последовательностей и UDIM из этой таблицы пока недоступно",
	"This checkout mode requires a desktop connection": "Для этого режима получения файлов требуется подключение к настольному клиенту",
	"Unsupported checkout transfer mode": "Неподдерживаемый режим получения файлов",
	"The clipboard does not contain an image": "В буфере обмена нет изображения",
	"Choose a valid file type": "Укажите допустимый тип файла",
	"Close the current attachment session before selecting another snapshot": "Закройте текущее окно вложений перед выбором другого снапшота",
	"Choose local files for attachment": "Выберите локальные файлы для вложения",
	"Choose files, not directories": "Выберите файлы, а не папки",
	"Choose between one and 50 files": "Выберите от одного до 50 файлов",
	"Could not save the clipboard image": "Не удалось сохранить изображение из буфера обмена",
	"Attachment upload cancelled": "Загрузка вложений отменена",
	"Snapshot changed. Reload before attaching files.": "Снапшот изменился. Обновите его перед добавлением файлов.",
	"Snapshot owner is no longer available": "Объект снапшота больше недоступен",
	"Open the snapshot in its own project before attaching files": "Перед добавлением файлов откройте снапшот в его проекте",
	"Append files requires a snapshot": "Добавить файлы можно только к снапшоту",
	"Reload the concrete snapshot version before attaching files": "Обновите конкретную версию снапшота перед добавлением файлов",
	"No concrete snapshot version is available": "Нет доступной конкретной версии снапшота",
	"Recursive nested tables are not available yet.": "Рекурсивные вложенные таблицы пока недоступны.",
	"Choose at most 500 table records": "Выберите не более 500 строк таблицы",
	"Show related table": "Показать связанную таблицу",
	"Auxiliary data": "Дополнительные данные",
	General: "Общие",
	"Task is unavailable": "Задача недоступна",
	"Work Hours": "Рабочие часы",
	Mon: "Пн",
	Tue: "Вт",
	Wed: "Ср",
	Thu: "Чт",
	Fri: "Пт",
	Sat: "Сб",
	Sun: "Вс",
	"Save or discard time-entry changes before switching tasks.": "Сохраните или отмените изменения рабочих часов перед сменой задачи.",
	"Configured button": "Настраиваемая кнопка",
	"Parallel task status": "Параллельные статусы задач",
	"Task status": "Статус задачи",
	"CustomLayout output exceeds one MiB": "Результат CustomLayout превышает один МиБ",
	"CustomLayout markup exceeds 32 levels": "Разметка CustomLayout содержит более 32 уровней",
	"CustomLayout supports at most 128 controls": "CustomLayout поддерживает не более 128 контролов",
	"Finish the current confirmation first": "Сначала завершите текущее подтверждение",
	"Custom Layout": "Пользовательская компоновка",
	"Security Summary": "Сводка прав",
	"No groups": "Нет групп",
	"Open external document": "Открыть внешний документ",
	"Run script": "Запустить скрипт",
	"Pipeline is not configured": "Пайплайн не настроен",
	"Configure an instance type and accepted Search Type": "Укажите тип связи и допустимый Search Type",
	"A table action cannot replay server calls for confirmation": "Действие таблицы не может повторять серверные запросы ради подтверждения",
	"Authentication methods are unavailable in table actions": "Методы авторизации недоступны в действиях таблицы",
	"Could not open table link": "Не удалось открыть ссылку таблицы",
	"CustomLayout behavior requires a portable click action": "Для поведения CustomLayout нужно переносимое действие по нажатию",
	"CustomLayout click action needs a class selector": "Для действия CustomLayout нужен селектор класса",
	"CustomLayout element has no display": "У элемента CustomLayout не задан display",
	"CustomLayout nesting exceeds eight levels": "Глубина вложенности CustomLayout превышает восемь уровней",
	"Drop background must be a hexadecimal color": "Фон области переноса должен задаваться шестнадцатеричным цветом",
	"Dropped objects belong to another Search Type": "Переносимые объекты относятся к другому Search Type",
	"Dropped objects belong to another project": "Переносимые объекты относятся к другому проекту",
	"Instance links or their definition changed. Reload before saving.": "Связи или их определение изменились. Обновите данные перед сохранением.",
	"Instance revisions require a transactional database lock": "Проверка ревизий связей требует транзакционной блокировки БД",
	"Invalid configured file transfer mode": "В конфигурации указан неверный режим передачи файлов",
	"Invalid table JS worker message": "Некорректное сообщение процесса JavaScript таблицы",
	"Invalid table action commands": "Некорректные команды действия таблицы",
	"Invalid table action result": "Некорректный результат действия таблицы",
	"Invalid table script API arguments": "Некорректные аргументы API скрипта таблицы",
	"Open the target object before editing this configured view": "Откройте целевой объект перед редактированием настроенного представления",
	"Preference revisions require a transactional database lock": "Проверка ревизий настроек требует транзакционной блокировки БД",
	"Script is no longer available": "Скрипт больше недоступен",
	"Table action cancelled": "Действие таблицы отменено",
	"Table action cancelled. Some operations may already have completed.": "Действие таблицы отменено. Некоторые операции уже могли завершиться.",
	"Table button color must be a hexadecimal color": "Цвет кнопки таблицы должен задаваться шестнадцатеричным значением",
	"Table button icon size must be between 12 and 28 pixels": "Размер иконки кнопки таблицы должен быть от 12 до 28 пикселей",
	"Table button scripts must use JavaScript": "Скрипты кнопок таблицы должны использовать JavaScript",
	"The configured drop column changed. Reload before saving.": "Настройка столбца переноса изменилась. Обновите данные перед сохранением.",
	"The configured instance relationship is unavailable": "Настроенная связь объектов недоступна",
	"The configured table target belongs to another project": "Настроенный целевой объект таблицы относится к другому проекту",
	"The configured table target is unavailable": "Настроенный целевой объект таблицы недоступен",
	"The source tab changed. Table action results were not opened.": "Исходная вкладка изменилась. Результаты действия таблицы не открыты.",
	"This configured check-in mode is not available yet": "Указанный режим публикации пока недоступен",
	"Unsupported table link": "Неподдерживаемая ссылка таблицы",
	"No script defined for this button": "Для этой кнопки не задан скрипт",
	"Select one existing custom script": "Выберите один существующий пользовательский скрипт",
	"Search Type is not available for this editor": "Search Type недоступен для этого редактора",
	"The configured group is no longer available": "Настроенная группа больше недоступна",
	"Close this form and refresh the table before reopening its links": "Закройте форму и обновите таблицу перед повторным открытием её связей",
	"Only the assigned user can edit this status": "Этот статус может изменять только назначенный пользователь",
	"Choose at most 500 linked objects": "Выберите не более 500 связанных объектов",
	"An instance must refer to exactly one accepted object": "Запись связи должна указывать ровно на один допустимый объект",
	"A linked object is no longer available": "Связанный объект больше недоступен",
	"Custom DOM drop callbacks require a Frame action before they can run in both clients": "Для обработчика переноса DOM нужно действие Frame, чтобы он работал в обоих клиентах",
	"Parallel task bars": "Параллельные задачи",
	"Add Task": "Добавить задачу",
	"Work on Task": "Работать с задачей",
	"Open tasks": "Открыть задачи",
	"Invalid parallel status label format": "Неверный формат подписи параллельных задач",
	"Parallel status bar height must be between 1 and 32 pixels": "Высота полосы параллельных задач должна быть от 1 до 32 пикселей",
	"Cyclic or excessively nested task pipeline": "Циклический или слишком глубоко вложенный пайплайн задач",
	"Invalid task status edit scope": "Неверная область редактирования статуса задачи",
	"Global Permissions": "Глобальные права",
	"Email Test": "Тест уведомления",
	"Update Template": "Обновить шаблон",
	"User preference": "Настройка пользователя",
	"My TACTIC summary": "Моя сводка TACTIC",
	"Edit preference": "Изменить настройку",
	"Preference changed. Reload before saving.": "Настройка изменена. Обновите данные перед сохранением.",
	"Notifications received": "Получено уведомлений",
	Checkins: "Публикации",
	"Status Changes": "Изменения статуса",
	"1 hour": "1 час",
	today: "сегодня",
	"1 week": "1 неделя",
	"Update the template archive for {project}?": "Обновить архив шаблона проекта {project}?",
	"Update the template archive for %1?": "Обновить архив шаблона проекта %1?",
	"Retire this object?": "Архивировать этот объект?",
	"Reactivate this object?": "Восстановить этот объект?",
	"Global Permissions are unavailable in this host": "Редактор глобальных прав недоступен в этом окне",
	"Group is no longer available": "Группа больше недоступна",
	"Legacy discussion": "Обсуждение (legacy)",
	"Object tasks": "Задачи объекта",
	"Task context": "Контекст задачи",
	"Formatted message": "Форматированное сообщение",
	"Note added": "Добавлена заметка",
	"Task modified": "Задача изменена",
	"Files checked in": "Файлы опубликованы",
	"Object modified": "Объект изменён",
	Retired: "Архивные",
	"Adds the text column metadata to sthpw/message and sthpw/message_log. It stores conversation summaries, replies, reactions, pins, forwarding and delivery state.": "Добавит текстовую колонку metadata в sthpw/message и sthpw/message_log. В ней хранятся сводки диалогов, ответы, реакции, закрепления, пересылка и состояние доставки.",
	"Creates PROJECT/th_knowledge_article when it is missing, then adds kind, parent_code, content, content_text, sort_order, updated_by and linked_skeys.": "Создаст PROJECT/th_knowledge_article, если его нет, затем добавит kind, parent_code, content, content_text, sort_order, updated_by и linked_skeys.",
	"Existing columns and data are kept. Nothing is deleted. The schema changes affect every user of this server and project.": "Существующие столбцы и данные сохраняются. Ничего не удаляется. Изменения схемы затронут всех пользователей этого сервера и проекта.",
	"A TACTIC administrator must initialize these features once.": "Администратор TACTIC должен один раз инициализировать эти функции.",
	"Initialize server features?": "Инициализировать функции на сервере?",
	"Messages are not initialized": "Сообщения не инициализированы",
	"Knowledge Base is not initialized": "База знаний не инициализирована",
	"Initialize the collaboration schema before starting conversations.": "Инициализируйте общую схему перед началом диалогов.",
	"Initialize the collaboration schema before writing project documentation.": "Инициализируйте общую схему перед созданием проектной документации.",
	"Step {step} of 2": "Шаг {step} из 2",
	"OT ": "Сверхурочно ",
	"ACTIVITY & NOTIFICATIONS": "АКТИВНОСТЬ И УВЕДОМЛЕНИЯ",
	"ACTIVITY FEED": "ЛЕНТА АКТИВНОСТИ",
	"ATTACHMENTS TO SEND": "ВЛОЖЕНИЯ ДЛЯ ОТПРАВКИ",
	Action: "Действие",
	Activities: "Занятия",
	"Activity notifications": "Уведомления ленты",
	"Add or remove members": "Добавить или удалить участников",
	"Add reaction": "Добавить реакцию",
	All: "Все",
	"All history": "Вся история",
	"All messages in Favorites will be cleared. Favorites itself will remain.": "Все сообщения в избранном будут удалены. Сам чат «Избранное» останется.",
	"All users": "Все пользователи",
	"Animals & Nature": "Животные и природа",
	Apply: "Применить",
	"Attach image from clipboard": "Вставить изображение из буфера",
	"Attachments to send": "Вложения для отправки",
	"CHAT FILES": "ФАЙЛЫ ЧАТА",
	"CHAT MEMBERS": "УЧАСТНИКИ ЧАТА",
	CONVERSATIONS: "ЧАТЫ",
	Cancel: "Отмена",
	"Cancel attachment upload": "Отменить загрузку вложений",
	"Cancel reply": "Отменить ответ",
	"Chat actions": "Действия чата",
	"Chat files": "Файлы чата",
	"Chat members": "Участники чата",
	"Chat title": "Название чата",
	"Check-in": "Check-in",
	"Check-in operations": "Операции Check-in",
	"Choose one or more destination chats": "Выберите один или несколько чатов",
	Clear: "Очистить",
	"Clear attachments": "Очистить вложения",
	"Clear favorites?": "Очистить избранное?",
	"Clear history": "Очистить историю",
	"Clear messages": "Очистить сообщения",
	Client: "Клиент",
	"Client events and background operations from this session.": "События клиентов и фоновые операции текущей сессии.",
	Close: "Закрыть",
	Collapse: "Свернуть",
	Component: "Компоненты",
	Create: "Создать",
	Delete: "Удалить",
	"Delete chat": "Удалить чат",
	"Delete chat?": "Удалить чат?",
	"Delivered to {count} of {total}": "Доставлено {count} из {total}",
	"EDIT HISTORY": "ИСТОРИЯ ИЗМЕНЕНИЙ",
	"Edit message": "Редактировать сообщение",
	Edited: "Изменено",
	"Emoji categories": "Категории эмодзи",
	"Exclude my activity": "Исключать мои действия",
	Expand: "Развернуть",
	Favorites: "Избранное",
	Field: "Поле",
	File: "Файл",
	"Filter by users": "Фильтр по пользователям",
	"Find emoji": "Найти эмодзи",
	"Find people and start a direct or group chat": "Найдите пользователей и создайте личный или групповой чат",
	Flags: "Флаги",
	"Food & Drink": "Еда и напитки",
	Forward: "Переслать",
	"Forwarded from {name}": "Переслано от {name}",
	"Forwarded message unavailable": "Пересланное сообщение недоступно",
	"Group chat title": "Название группового чата",
	"Group chats can be created by administrators and supervisors": "Групповые чаты могут создавать администраторы и супервайзеры",
	Icon: "Иконка",
	"Last edited by {name} · {time}": "Последнее изменение: {name} · {time}",
	Message: "Сообщение",
	"Message actions": "Действия сообщения",
	Messages: "Сообщения",
	"My objects": "Мои объекты",
	"New conversation": "Новый чат",
	"No events in this group": "В этой группе нет событий",
	"No matching emoji": "Подходящие эмодзи не найдены",
	"No messages yet": "Сообщений пока нет",
	Notes: "Заметки",
	"Notification history filters": "Фильтры истории уведомлений",
	Objects: "Предметы",
	"Open attachment": "Открыть вложение",
	"Open profile for {name}": "Открыть профиль {name}",
	"Original message is unavailable": "Исходное сообщение недоступно",
	"PIN HISTORY": "ИСТОРИЯ ЗАКРЕПЛЕНИЙ",
	"People & Body": "Люди и тело",
	"Pin history": "История закреплений",
	"Pinned by {user}": "Закрепил(а) {user}",
	"Pinned message": "Закреплённое сообщение",
	Preview: "Превью",
	Publications: "Публикации",
	"Read by {count} of {total}": "Прочитали {count} из {total}",
	"Refresh activity": "Обновить активность",
	"Refresh conversations and messages": "Обновить чаты и сообщения",
	"Remove attachment": "Удалить вложение",
	Rename: "Переименовать",
	"Rename chat": "Переименовать чат",
	Reply: "Ответить",
	"Reply to {name}": "Ответ {name}",
	"Repository sync": "Синхронизация репозитория",
	Save: "Сохранить",
	"Save members": "Сохранить участников",
	Search: "Поиск",
	"Search activity": "Поиск по активности",
	"Search messages": "Искать сообщения",
	"Select a conversation": "Выберите чат",
	"Select everyone who should remain in this chat": "Выберите всех, кто должен остаться в чате",
	Send: "Отправить",
	Sent: "Отправлено",
	Server: "Сервер",
	"Server transactions": "Серверные транзакции",
	"Server trigger": "Серверный триггер",
	"Show activity created by selected users": "Показывать активность выбранных пользователей",
	"Smileys & Emotion": "Смайлы и эмоции",
	Symbols: "Символы",
	Text: "Текст",
	"The chat will be archived for every participant. Message history and attachments remain available for audit.": "Чат будет архивирован для всех участников. История сообщений и вложения останутся доступны для аудита.",
	"Travel & Places": "Путешествия и места",
	"Type a message or phrase": "Введите сообщение или фразу",
	Unknown: "Неизвестно",
	"Unknown user": "Неизвестный пользователь",
	"Unpin message": "Открепить сообщение",
	Uploaded: "Загружен",
	View: "Вид",
	"Write a reply": "Напишите ответ",
	"Your personal notes": "Ваши личные заметки",
	snapshot: "снапшот",
	unknown: "неизвестно",
	"Milestone name is required": "Укажите название этапа",
	"Choose a valid due date": "Выберите корректную дату",
	"Milestone operation failed": "Не удалось выполнить операцию с этапом",
	"Schedule reusable task deadlines for {project}": "Общие сроки задач проекта {project}",
	"current project": "текущий проект",
	milestones: "вех",
	Completion: "Готовность",
	"Assign tasks to build the milestone plan": "Назначьте задачи, чтобы построить план вехи",
	"Start not set": "Начало не задано",
	"No tasks": "Нет задач",
	"Start and deadline are not set": "Начало и срок не заданы",
	"Start is not set": "Начало не задано",
	"Deadline is not set": "Срок не задан",
	"Deadline precedes start": "Срок раньше даты начала",
	"Task is overdue": "Задача просрочена",
	"Task has no assignee": "У задачи нет исполнителя",
	"Deadline falls on a weekend": "Срок приходится на выходной",
	"Assignee has overlapping tasks": "У исполнителя есть пересекающиеся задачи",
	"No matching milestones": "Подходящие этапы не найдены",
	"No milestones yet": "Этапов пока нет",
	"Try another search": "Попробуйте изменить запрос",
	"Create a reusable deadline for project tasks": "Создайте общий срок для задач проекта",
	Agenda: "Список событий",
	"Align deadlines": "Выровнять сроки",
	"Align start dates": "Выровнять даты начала",
	"Calendar month": "Месяц календаря",
	"Center today": "Показать сегодня по центру",
	"Clear selected day": "Очистить выбранную дату",
	Days: "Дни",
	"Delete milestone": "Удалить этап",
	"Due date": "Срок",
	"Duration in calendar days": "Длительность в календарных днях",
	"Duration in working days": "Длительность в рабочих днях",
	"Edit schedule": "Редактировать расписание",
	"Extend by one day": "Продлить на один день",
	"Fit range": "Вместить диапазон",
	"Group workload by assignee": "Группировать нагрузку по исполнителям",
	"Linked task plan": "План связанных задач",
	"Milestone name": "Название этапа",
	Months: "Месяцы",
	"Move selected tasks together": "Сдвинуть выбранные задачи вместе",
	"New milestone": "Новый этап",
	"Next month": "Следующий месяц",
	"Previous month": "Предыдущий месяц",
	"Project overview": "Обзор проекта",
	Quarters: "Кварталы",
	"Q{quarter} {year}": "Q{quarter} {year}",
	"Redo schedule change": "Повторить правку расписания",
	"Review current milestone revision": "Проверить текущую ревизию вехи",
	"Save milestone": "Сохранить этап",
	Saved: "Сохранено",
	"Schedule options": "Настройки расписания",
	"Schedule sequentially": "Расположить последовательно",
	"Scheduled tasks": "Задачи с расписанием",
	"Select a day to filter Task Browser": "Выберите день для фильтрации браузера задач",
	"Select task": "Выберите задачу",
	"Shift one day earlier": "Сдвинуть на день раньше",
	"Shift one day later": "Сдвинуть на день позже",
	"Shorten by one day": "Сократить на один день",
	"Task Browser filtered by {date}": "Задачи отфильтрованы по дате {date}",
	"Task Manager": "Диспетчер задач",
	"Task schedule": "Расписание задач",
	"Timeline scale": "Масштаб времени",
	"Undo schedule change": "Отменить правку расписания",
	"Unscheduled tasks": "Задачи без расписания",
	Weeks: "Недели",
	"Working days only": "Только рабочие дни",
	"{count} more tasks": "Ещё задач: {count}",
	"{count} schedule warnings": "Предупреждений расписания: {count}",
	"{scheduled} scheduled · {unscheduled} unscheduled": "{scheduled} с расписанием · {unscheduled} без расписания",
	"No milestone": "Без вехи",
	"No supervisor": "Без руководителя",
	"Cancel bulk edit and clear selection": "Отменить массовое редактирование и снять выделение",
	"Delete selected tasks": "Удалить выбранные задачи",
	"Edit selected tasks": "Изменить выбранные задачи",
	"Choose fields to change": "Выберите изменяемые поля",
	"Configure columns": "Настроить колонки",
	Progress: "Прогресс",
	"Expected work hours": "Плановые трудозатраты",
	"End date": "Дата окончания",
	"Planned hours": "Плановые часы",
	"Edit task draft": "Редактирование черновика задачи",
	"Changes remain pending until Save.": "Изменения ожидают нажатия «Сохранить».",
	Done: "Готово",
	"No tasks match the current filters": "Нет задач, соответствующих текущим фильтрам",
	"Create a task": "Создайте задачу",
	"Clear filters to see all tasks": "Очистите фильтры, чтобы увидеть все задачи",
	"Use the + button above": "Используйте кнопку + выше",
	"Select a parent object before creating a task.": "Перед созданием задачи выберите родительский объект.",
	Unassigned: "Не назначено",
	ALL: "ВСЕ",
	"Next three days": "Ближайшие три дня",
	Later: "Позже",
	"Has notes": "Есть заметки",
	"Sort ascending": "Сортировать по возрастанию",
	"Sort descending": "Сортировать по убыванию",
	"Group by column": "Группировать по колонке",
	"Hide column": "Скрыть колонку",
	"Edit sObject": "Редактирование sObject",
	"Edit task": "Редактировать задачу",
	"Task timesheet": "Учёт времени задачи",
	"Open object": "Открыть объект",
	"Use server version": "Использовать серверную версию",
	"Keep my changes": "Сохранить мои изменения",
	"Delete task": "Удалить задачу",
	"Reset task changes": "Сбросить изменения задачи",
	"My tasks": "Мои задачи",
	Team: "Команда",
	User: "Пользователь",
	"Refresh tasks": "Обновить задачи",
	PROJECT: "ПРОЕКТ",
	"MY TASKS": "МОИ ЗАДАЧИ",
	"Pending task changes": "Несохранённые изменения задач",
	"Task view": "Вид задач",
	Calendar: "Календарь",
	"{count} unsaved": "Не сохранено: {count}",
	"Load more tasks": "Загрузить ещё задачи",
	"Clear checked tasks": "Снять отметки с задач",
	"Records per page": "Записей на странице",
	"Quick task editor": "Быстрый редактор задач",
	TODAY: "СЕГОДНЯ",
	REVIEW: "НА ПРОВЕРКУ",
	RECENT: "НЕДАВНИЕ",
	"No team scopes are available from your TACTIC login groups": "Для ваших групп входа TACTIC нет доступных команд",
	"{count} overdue": "Просрочено: {count}",
	"{count} tasks loaded | partial scope": "Загружено задач: {count} | неполная область",
	"{loaded} of {total} tasks loaded": "Загружено задач: {loaded} из {total}",
	"{count} tasks loaded": "Загружено задач: {count}",
	"{count} loaded tasks": "Загружено задач: {count}",
	WORKLOAD: "НАГРУЗКА",
	"SCOPE SUMMARY": "СВОДКА ОБЛАСТИ",
	"QUICK VIEW": "БЫСТРЫЙ ВИД",
	PROCESSES: "ПРОЦЕССЫ",
	STATUSES: "СТАТУСЫ",
	PRIORITIES: "ПРИОРИТЕТЫ",
	MILESTONES: "ЭТАПЫ",
	SUPERVISORS: "РУКОВОДИТЕЛИ",
	ASSIGNEES: "ИСПОЛНИТЕЛИ",
	"Advanced filters": "Дополнительные фильтры",
	"Clear this filter group": "Очистить эту группу фильтров",
	"Recently Updated": "Недавно обновлённые",
	"Each checked field replaces its current value": "Каждое отмеченное поле заменяет текущее значение",
	"Mixed status": "Разные статусы",
	"Mixed assignee": "Разные исполнители",
	"Bulk fields": "Поля массовой правки",
	"Bulk task editing": "Массовое редактирование задач",
	"Apply bulk changes": "Применить массовые изменения",
	APPLY: "ПРИМЕНИТЬ",
	APPLYING: "ПРИМЕНЕНИЕ",
	"{count} task selected": "Выбрана {count} задача",
	"{count} tasks selected": "Выбрано задач: {count}",
	"{count} ready": "Готово: {count}",
	"{count} unchanged": "Без изменений: {count}",
	"{count} invalid": "С ошибками: {count}",
	"{count} checked": "Отмечено: {count}",
	"{visible} of {loaded} tasks": "Задачи: {visible} из {loaded}",
	"{loaded} of {total} loaded": "Загружено: {loaded} из {total}",
	"Reset task columns": "Сбросить колонки задач",
	"Move column left": "Переместить колонку влево",
	"Move column right": "Переместить колонку вправо",
	"Width of {column}": "Ширина: {column}",
	"Save or discard row changes first": "Сначала сохраните или отмените изменения строки",
	"Save or discard task changes before changing the task scope.": "Сохраните или сбросьте изменения задач перед сменой области задач.",
	"Select an sObject": "Выберите объект",
	"Discard all process changes": "Сбросить изменения всех процессов",
	"Save all process changes": "Сохранить изменения всех процессов",
	"Task notes": "Заметки задачи",
	CONTEXT: "КОНТЕКСТ",
	OBJECT: "ОБЪЕКТ",
	"START / DEADLINE": "НАЧАЛО / СРОК",
	HOURS: "ЧАСЫ",
	"Task columns": "Колонки задач",
	"Select all tasks": "Выбрать все задачи",
	"Expand task details": "Развернуть сведения о задаче",
	"Collapse task details": "Свернуть сведения о задаче",
	"Task view options": "Параметры вида задач",
	"Task scope": "Область задач",
	"Choose task scope": "Выбрать область задач",
	"Task filters": "Фильтры задач",
	"Clear filters": "Сбросить фильтры",
	"Project milestones": "Этапы проекта",
	"Open search": "Открыть поиск",
	Sort: "Сортировка",
	Teams: "Команды",
	"My Tasks": "Мои задачи",
	"User tasks": "Задачи пользователя",
	"Team tasks": "Задачи команды",
	"Project tasks": "Задачи проекта",
	"Selected objects": "Выбранные объекты",
	"Search Type tasks": "Задачи типа объектов",
	"Recently created": "Недавно созданные",
	Object: "Объект",
	"No status": "Без статуса",
	"Open notes": "Открыть заметки",
	START: "НАЧАЛО",
	"EXPECTED WORK HOURS": "ОЖИДАЕМЫЕ РАБОЧИЕ ЧАСЫ",
	PROCESS: "ПРОЦЕСС",
	STATUS: "СТАТУС",
	ASSIGNEE: "ИСПОЛНИТЕЛЬ",
	DEADLINE: "СРОК",
	PRIORITY: "ПРИОРИТЕТ",
	MILESTONE: "ЭТАП",
	SUPERVISOR: "РУКОВОДИТЕЛЬ",
	"Finish editing description": "Завершить редактирование описания",
	"Edit task description": "Изменить описание задачи",
	"{count} task has unsaved changes": "У {count} задачи есть несохранённые изменения",
	"{count} tasks have unsaved changes": "У {count} задач есть несохранённые изменения",
	"Preview Gantt changes": "Предпросмотр изменений Ганта",
	"Reload draft revisions": "Обновить ревизии черновика",
	"Task workspace surface": "Вид рабочего пространства задач",
	"Task cards": "Карточки задач",
	"Compact task list": "Компактный список задач",
	"Open task workspace": "Открыть рабочее пространство задач",
	"Creating duplicate on the server… You can continue working.": "Копия создаётся на сервере… Можно продолжать работу.",
	"Analyzing fields, relations and process content…": "Анализ полей, связей и содержимого процессов…",
	"Choose current snapshots and files to duplicate for each process. Message attachments are handled with their messages on the next step.": "Выберите текущие снапшоты и файлы для дублирования по процессам. Вложения сообщений переносятся вместе с сообщениями на следующем шаге.",
	"Choose tasks, process messages, task messages, and their attached files. Copying task messages also copies their parent tasks.": "Выберите задачи, сообщения процессов и задач и вложенные файлы. Копирование сообщений задач также копирует их родительские задачи.",
	"Choose related records to remove with the selected objects.": "Выберите связанные записи, которые нужно удалить вместе с выбранными объектами.",
	"{count} items": "{count} элементов",
	"{count} relations": "{count} связей",
	"OBJECT AND TASK NOTES": "ЗАМЕТКИ ОБЪЕКТА И ЗАДАЧ",
	"{objects} object · {tasks} task notes": "{objects} объекта · {tasks} заметок задач",
	"Note text": "Текст заметки",
	"Edit note": "Редактировать заметку",
	"Delete note?": "Удалить заметку?",
	"Batch creation is available for database fields. Uploads and custom actions require individual forms.": "Пакетное создание доступно для полей базы данных. Загрузки и пользовательские действия выполняются в отдельных формах.",
	"The save result is unknown. Close this form and refresh the records before trying again.": "Результат сохранения неизвестен. Закройте форму и обновите записи перед повторной попыткой.",
	"The result is unknown. Refresh the objects before trying again.": "Результат неизвестен. Обновите объекты перед повторной попыткой.",
	"This operation cannot be retried here. Close this dialog and refresh the data to check the result.": "Здесь нельзя повторить операцию. Закройте окно и обновите данные, чтобы проверить результат.",
	"Create mode": "Режим создания",
	"Name preview": "Пример имени",
	"Collapse Task Inspector": "Свернуть инспектор задач",
	Cost: "Стоимость",
	"Could not load related tasks. Refresh to retry.": "Не удалось загрузить связанные задачи. Нажмите «Обновить», чтобы повторить.",
	"Create another task in full editor": "Создать ещё задачу в полном редакторе",
	"Create task": "Создать задачу",
	"Create {count} objects": "Создать {count} объектов",
	"Discard task changes": "Отменить изменения задачи",
	"Edit task in full editor": "Открыть задачу в полном редакторе",
	"End date and time": "Дата и время окончания",
	"Expand Task Inspector": "Развернуть инспектор задач",
	"Loading related tasks…": "Загрузка связанных задач…",
	"Log time": "Записать время",
	"No related Search Type configured for this progress": "Для прогресса не задан связанный тип объектов",
	"No related objects": "Нет связанных объектов",
	"No schema relationship to this Search Type": "В схеме нет связи с этим типом объектов",
	"No task for {process}": "Нет задачи для {process}",
	"No tasks on related objects": "У связанных объектов нет задач",
	"Note actions": "Действия заметки",
	"Object {index} of {total}": "Объект {index} из {total}",
	"Open related task": "Открыть связанную задачу",
	"Open timesheet": "Открыть табель",
	"Over plan": "Сверх плана",
	PROGRESS: "ПРОГРЕСС",
	Planned: "Запланировано",
	"Preview {count} objects": "Предпросмотр {count} объектов",
	"Refresh notes and task": "Обновить заметки и задачу",
	"Related object tasks": "Задачи связанных объектов",
	Remaining: "Осталось",
	Reply: "Ответить",
	"Save task changes": "Сохранить изменения задачи",
	"Search Type is unavailable": "Тип объектов недоступен",
	"Select status": "Выберите статус",
	"Start date and time": "Дата и время начала",
	"Switch task for this process": "Переключить задачу процесса",
	"Task actions": "Действия задачи",
	"Task process or status pipeline is not configured for this progress count.": "Для счётчика прогресса не настроен процесс задачи или pipeline статусов.",
	"and {count} more sObjects": "и ещё {count} объектов",
	end: "Конец",
	start: "Начало",
	"{count} dependencies selected": "Выбрано зависимостей: {count}",
	"{selected} of {total} selected": "Выбрано {selected} из {total}",
	"{count} people · {hours} h": "{count} чел. · {hours} ч",
	"{count} tasks": "{count} задач",
	"{count} children": "{count} дочерних объектов",
	"Edit record": "Редактировать объект",
	Multiple: "Несколько",
	One: "Один",
	"Reload schema": "Обновить схему",
	"Place the caret in a text field and insert a number format. Numbers are substituted during preview.": "Поставьте каретку в текстовое поле и вставьте формат номера. Номера подставятся при предпросмотре.",
	"Number of objects": "Количество объектов",
	"Previous object": "Предыдущий объект",
	"Edit any fields for this object, then move to the next one.": "Измените нужные поля этого объекта и переходите к следующему.",
	"Next object": "Следующий объект",
	"Object fields": "Поля объекта",
	"Save changes": "Сохранить изменения",
	"Correct the highlighted fields": "Исправьте выделенные поля",
	"Ready to save": "Готово к сохранению",
	"Hide dependencies": "Скрыть зависимости",
	"Show dependencies": "Показать зависимости",
	"Delete sObject": "Удалить sObject",
	"Delete sObjects": "Удалить sObject-объекты",
	"The selected objects and checked dependencies will be permanently removed from TACTIC.": "Выбранные объекты и отмеченные зависимости будут безвозвратно удалены из TACTIC.",
	"Deletion help": "Справка по удалению",
	"Reviewing selected objects": "Проверка выбранных объектов",
	"Selected groups include their current related records, including retired records. Selected snapshots also remove their owned files. Object-owned repository directories will also be removed.": "Удаляются текущие записи выбранных групп, включая скрытые. Выбранные снимки удаляются вместе с принадлежащими им файлами. Каталоги репозитория, принадлежащие объекту, также удаляются.",
	"Deleting selected objects…": "Удаление выбранных объектов…",
	"Discovering dependencies…": "Поиск зависимостей…",
	Dependencies: "Зависимости",
	"No dependencies were found. Only the selected objects will be deleted.": "Зависимости не найдены. Будут удалены только выбранные объекты.",
	Relations: "Связи",
	Snapshots: "Снапшоты",
	"Tasks and messages": "Задачи и сообщения",
	"Process messages": "Заметки процесса",
	"Process attachments": "Вложения процесса",
	"Task messages": "Заметки задач",
	"Task attachments": "Вложения задач",
	Duplicate: "Дублировать",
	sObject: "серч-объект",
	"Step {step} of 5": "Шаг {step} из 5",
	"Duplication help": "Справка по дублированию",
	"Remember choices": "Запомнить",
	Remember: "Запомнить",
	"Remember for this Search Type": "Запомнить для этого серч-тайпа",
	"Analyze again": "Повторить анализ",
	"Creating duplicate on server…": "Создание копии на сервере…",
	"Analyzing object…": "Анализ объекта…",
	"Edit the values of the new object. Identity, project and relationship columns are generated or managed automatically.": "Измените значения нового объекта. Идентификаторы, проект и столбцы связей создаются или управляются автоматически.",
	"Choose what happens to each relationship already attached to the source object.": "Выберите, что сделать с каждой связью исходного объекта.",
	"Instance links": "Instance-связи",
	Parent: "Родитель",
	Children: "Дочерние объекты",
	"No linked objects": "Нет связанных объектов",
	"Copy current snapshots and their files by process. Message attachments are selected separately.": "Копируйте текущие снапшоты и файлы по процессам. Вложения заметок выбираются отдельно.",
	"Choose tasks, message threads and attachments to duplicate. Attachment choices include their messages and tasks.": "Выберите задачи, ветки заметок и вложения. Вложения копируются вместе с их заметками и задачами.",
	Files: "Файлы",
	"No current snapshots": "Нет текущих снапшотов",
	"No tasks or messages": "Нет задач и сообщений",
	"The new object receives the edited fields. Selected links are recreated; original instance targets are never duplicated.": "Новый объект получит изменённые поля. Выбранные связи будут пересозданы, а оригинальные цели инстанс-связей никогда не дублируются.",
	"Ready to create the duplicate": "Всё готово для создания дубликата",
	Related: "Связи",
	"Messages and files": "Сообщения и файлы",
	"These choices will enable Quick duplicate for this Search Type.": "Этот выбор включит быстрый дубль для данного серч-тайпа.",
	"These choices will be used only once.": "Этот выбор будет использован только один раз.",
	"Read only": "Только чтение",
	Objects: "Предметы",
	"Select an instance relation": "Выберите instance-связь",
	"Choose objects to link": "Выберите объекты для связи",
	"Reload related objects": "Обновить связанные объекты",
	Search: "Поиск",
	"Remove selected links": "Удалить выбранные связи",
	"Link selected objects": "Связать выбранные объекты",
	Selected: "Выбранные",
	"Links have unsaved changes": "Есть несохранённые изменения связей",
	"Select objects and use the center button": "Выберите объекты и используйте центральную кнопку",
	"Available objects": "Доступные объекты",
	"Linked objects": "Связанные объекты",
	row: "Строка",
	children: "Дочерние объекты",
	Code: "Код",
	"No description provided": "Описание не задано",
	Updated: "Обновлено",
	"Open sObject": "Открыть sObject",
	"Refresh report": "Обновить отчет",
	TASKS: "ЗАДАЧИ",
	NOTES: "ЗАМЕТКИ",
	CHILDREN: "ДОЧЕРНИЕ ОБЪЕКТЫ",
	PEOPLE: "ЛЮДИ",
	h: "ч",
	FILES: "ФАЙЛЫ",
	SNAPSHOTS: "СНАПШОТЫ",
	"TOTAL COST": "ОБЩАЯ СТОИМОСТЬ",
	"TOTAL SIZE": "ОБЩИЙ ОБЪЕМ",
	"{tasks} tasks · {notes} notes · {snapshots} snapshots": "{tasks} задач · {notes} заметок · {snapshots} снапшотов",
	"Task note": "Заметка задачи",
	"Object note": "Заметка объекта",
	TOTAL: "ВСЕГО",
	"ACTIVE TASKS": "АКТИВНЫЕ",
	COMPLETED: "ЗАВЕРШЕНЫ",
	OVERDUE: "ПРОСРОЧЕНЫ",
	UNASSIGNED: "НЕ НАЗНАЧЕНЫ",
	"AVERAGE PROGRESS": "СРЕДНИЙ ПРОГРЕСС",
	"TASKS BY STATUS": "ЗАДАЧИ ПО СТАТУСАМ",
	"TASKS BY PROCESS": "ЗАДАЧИ ПО ПРОЦЕССАМ",
	"PEOPLE AND WORK HOURS": "УЧАСТНИКИ И РАБОЧИЕ ЧАСЫ",
	"No participants found": "Участники не найдены",
	"No tasks for this sObject": "У этого sObject нет задач",
	"No object or task notes": "Нет заметок объекта или задач",
	"CHILD TYPES": "ТИПЫ ДОЧЕРНИХ ОБЪЕКТОВ",
	"No related children": "Связанные дочерние объекты не найдены",
	"Preview and Files": "Превью и файлы",
	"Preview Only": "Только превью",
	"Files Only": "Только файлы",
	"Show All Files": "Показать все файлы",
	"Show More Info": "Больше информации",
	"Horizontal orientation": "Горизонтальная ориентация",
	"Vertical orientation": "Вертикальная ориентация",
	"SNAPSHOTS BY PROCESS": "СНАПШОТЫ ПО ПРОЦЕССАМ",
	"SNAPSHOTS AND VERSIONS": "СНАПШОТЫ И ВЕРСИИ",
	"No snapshots found": "Снапшоты не найдены",
	"Watch Folders require a desktop connection, which is not enabled in this web version.": "Для отслеживания папок нужно подключение к настольному приложению. В этой версии веба оно не включено.",
	"No sObject selected": "sObject не выбран",
	"Retained description drafts": "Сохранённые черновики описаний",
	"Select an sObject, process or snapshot": "Выберите sObject, процесс или снапшот",
	"Saving…": "Сохранение…",
	"Used for check-in": "Используется для Check-in",
	Unsaved: "Не сохранено",
	Editing: "Редактирование",
	"Edit description": "Редактировать описание",
	"Save description": "Сохранить описание",
	"This item has no description field": "У этого элемента нет поля описания",
	"Use this text for check-in": "Использовать этот текст для Check-in",
	"Stop using this text for check-in": "Не использовать этот текст для Check-in",
	"Relative Watch Path:": "Относительный путь наблюдения:",
	"All Repos": "Все репозитории",
	"No repositories selected": "Репозитории не выбраны",
	"Preparing watch folder…": "Подготовка отслеживаемой папки…",
	"Save and Close": "Сохранить и закрыть",
	"Refresh snapshots": "Обновить снапшоты",
	Context: "Контекст",
	Exists: "Есть",
	"Does not exist": "Отсутствует",
	"Project does not exist": "Проект не существует",
	"Not assigned": "Не назначено",
	Array: "Массив",
	JSON: "JSON",
	"Legacy task completion (integer)": "Готовность задач (старый целочисленный виджет)",
	"Table availability": "Наличие таблицы",
	"Raw value": "Исходное значение",
	"Expression value": "Вычисляемое значение",
	"Preference description": "Описание настройки",
	"Project database": "База проекта",
	"Related value": "Связанное значение",
	"Notification recipients": "Получатели уведомления",
	Discussion: "Обсуждение",
	Locked: "Заблокировано",
	"Snapshot lock": "Блокировка снапшота",
	"Snapshot file": "Файл снапшота",
	"Task group completion": "Готовность по группам задач",
	"Milestone completion": "Готовность вехи",
	"Days until due": "До срока задачи",
	"Row selection": "Выбор строки",
	"Search Type title": "Название Search Type",
	"Task summary": "Сводка задач",
	"No date": "Нет даты",
	Today: "Сегодня",
	"1 Day Overdue": "Просрочено на 1 день",
	"{count} Days Overdue": "Просрочено на {count} дн.",
	"< 2 Hours": "< 2 часов",
	"< 1 Hour": "< 1 часа",
	"1 Day": "1 день",
	"{count} Days": "{count} дн.",
	"No version": "Нет версии",
	Latest: "Последняя",
	Current: "Текущая",
	"Cell calculation failed": "Ошибка вычисления ячейки",
	"A connection to the TACTIC server could not be established. Check the server address, network connection, VPN or proxy, and make sure the server is running. Then try again.": "Не удалось установить соединение с сервером TACTIC. Проверьте адрес сервера, подключение к сети, VPN или прокси и убедитесь, что сервер запущен. Затем повторите попытку.",
	"ACCOUNT SETTINGS": "НАСТРОЙКИ УЧЁТНОЙ ЗАПИСИ",
	"API transport": "Транспорт API",
	"Access level is shared by every member of the group. Empty uses TACTIC's Low default.": "Уровень доступа применяется ко всем участникам группы. Пустое значение использует стандартный уровень TACTIC Low.",
	"Account status": "Статус учётной записи",
	"Action / window": "Действие / окно",
	"Active preset": "Активен",
	Activity: "Активность",
	"Activity is unavailable": "Активность недоступна",
	"Add preset": "Добавить пресет",
	"Add user": "Добавить пользователя",
	"Additional information": "Дополнительная информация",
	"Application error": "Ошибка приложения",
	"Application updates": "Обновления приложения",
	Approved: "Одобрено",
	"Assertion error": "Ошибка проверки",
	"Attribute error": "Ошибка атрибута",
	"Authentication error": "Ошибка авторизации",
	"Automatic installation requires a portable build": "Автоматическая установка доступна только в портативной сборке",
	"Available updates": "Доступные обновления",
	"BY PROCESS": "ПО ПРОЦЕССАМ",
	"BY STATUS": "ПО СТАТУСАМ",
	"Browser frame timings bound a paint opportunity using animation callbacks. They do not confirm GPU presentation. Handler time for asynchronous operations includes waiting; details show the measured phases.": "Браузер оценивает возможность отрисовки по animation callbacks, а не показ кадра GPU. Время обработчика асинхронной операции включает ожидание; измеренные этапы указаны в подробностях.",
	"Change avatar": "Изменить аватар",
	Changelog: "История изменений",
	"Check TACTIC update snapshots": "Проверить снапшоты обновлений TACTIC",
	"Choose a preset on the left and edit its connection and routing settings.": "Выберите пресет слева и настройте его подключение и маршрутизацию.",
	"Clear measurements": "Очистить замеры",
	"Clear session": "Очистить сессию",
	"Completed tasks": "Завершённые",
	"Configure an update sObject in Server configuration": "Укажите sObject обновлений в настройках сервера",
	"Connection presets": "Пресеты подключения",
	"Connection refused": "В подключении отказано",
	"Connection timeout": "Истекло время ожидания подключения",
	Contact: "Контакт",
	"Copy event": "Копировать событие",
	"Copy measurements": "Копировать замеры",
	"Copy runtime command": "Копировать команду выполнения",
	"Copy stacktrace": "Копировать стек вызовов",
	"Create archive": "Создать архив",
	"Create update": "Создать обновление",
	"Database connection error": "Ошибка подключения к базе данных",
	"Database query error": "Ошибка запроса к базе данных",
	"Debug session": "Сессия отладки",
	"Decrease value": "Уменьшить значение",
	Dismiss: "Закрыть",
	"Download debug session": "Скачать сессию отладки",
	"Due this week": "Срок на этой неделе",
	"Edit user profile": "Изменить профиль",
	"Event #{id}": "Событие №{id}",
	"Event details": "Параметры события",
	"FULL LOG": "ВЕСЬ ЖУРНАЛ",
	"File not found": "Файл не найден",
	"First frame": "Первый кадр",
	"GROUPS AND ROLES": "ГРУППЫ И РОЛИ",
	"Generate ticket": "Создать тикет",
	"Generating…": "Генерация…",
	Handler: "Обработка",
	"Hide stacktrace": "Скрыть стек вызовов",
	High: "Высокий",
	"Import error": "Ошибка импорта",
	Incomplete: "Незавершённые",
	"Increase value": "Увеличить значение",
	"Index error": "Ошибка индекса",
	"Install selected version": "Установить выбранную версию",
	"Interface error": "Ошибка интерфейса",
	"Loading user profile…": "Загрузка профиля…",
	Logged: "Записано",
	Low: "Низкий",
	"Measurement details": "Детали измерения",
	Message: "Сообщение",
	Minimum: "Минимальный",
	"Missing data": "Отсутствуют данные",
	"New password — leave empty to keep current": "Новый пароль — оставьте пустым, чтобы не менять",
	"New preset": "Новый пресет",
	"No account saved": "Учётная запись не сохранена",
	"No assigned tasks in the current project": "В текущем проекте нет назначенных задач",
	"No groups or roles returned by TACTIC": "TACTIC не вернул группы или роли",
	"No matching events": "Нет подходящих событий",
	"No measurements yet. Resume measurements and interact with the application.": "Измерений пока нет. Начните измерения и выполните действия в приложении.",
	"No recent activity": "Нет недавней активности",
	"No release ZIP snapshots found": "ZIP-снапшоты релизов не найдены",
	"No ticket": "Нет тикета",
	Offline: "Не в сети",
	Online: "В сети",
	"Open Debug Log": "Открыть журнал отладки",
	"Open Task Manager": "Открыть менеджер задач",
	"Open full activity": "Открыть всю активность",
	"Open saved debug session": "Открыть сохраненную отладочную сессию",
	"Operating system error": "Ошибка операционной системы",
	Overdue: "Просрочено",
	"PROJECT TASKS": "ЗАДАЧИ ПРОЕКТА",
	"Pause measurements": "Приостановить замеры",
	"Permission error": "Ошибка доступа",
	Presets: "Пресеты",
	"Project error": "Ошибка проекта",
	"Protocol error": "Ошибка протокола",
	"Proxy login": "Логин прокси",
	"Proxy password": "Пароль прокси",
	"Proxy server": "Прокси-сервер",
	"RECENT ACTIVITY": "НЕДАВНЯЯ АКТИВНОСТЬ",
	"Ready frame": "Кадр результата",
	"Refresh profile": "Обновить профиль",
	"Resize user directory": "Изменить ширину каталога пользователей",
	"Resume measurements": "Продолжить замеры",
	"Return to live session": "Вернуться к текущей сессии",
	"Runtime command": "Команда выполнения",
	"Runtime error": "Ошибка выполнения",
	"Samples: {count} · Frames over 50 ms: {overBudget} · p95: {p95} · Maximum: {maximum}": "Замеров: {count} · Кадров дольше 50 мс: {overBudget} · p95: {p95} · Максимум: {maximum}",
	"Search debug log": "Поиск в журнале отладки",
	"Search log…": "Поиск в журнале…",
	"Search tab": "Поисковая вкладка",
	"Select a measurement for details": "Выберите замер для просмотра подробностей",
	"Select an event to inspect its message, runtime command and stacktrace.": "Выберите событие, чтобы посмотреть сообщение, команду выполнения и стек вызовов.",
	Server: "Сервер",
	"Server address": "Адрес сервера",
	"Server default (Low)": "Серверный стандарт (Low)",
	"Show less": "Показать меньше",
	"Show more": "Показать подробнее",
	"Show stacktrace": "Показать стек вызовов",
	"Show users": "Показать пользователей",
	"Sign In": "Войти",
	"Sign in": "Войти",
	"Sign in to TACTIC": "Вход в TACTIC",
	"Sign out": "Выйти",
	"Sign-in is changed only through Generate ticket; the preset editor never asks for a TACTIC password.": "Вход меняется только через «Создать билет»; редактор пресетов не запрашивает пароль TACTIC.",
	"Signing in…": "Входим…",
	"Site name": "Имя сайта",
	Sources: "Источники",
	Stacktrace: "Стек вызовов",
	"Status unavailable": "Статус недоступен",
	"Stored account": "Сохранённая учётная запись",
	"TACTIC TEAM Mode (local repository)": "Режим TACTIC TEAM (локальный репозиторий)",
	"THIS WEEK": "ЭТА НЕДЕЛЯ",
	"Target: a visible response within 50 ms. Input measures the next frame of the clicked window; controller rows measure work and its ready frame. A frame is not proof that asynchronous loading has finished.": "Цель — видимый отклик за 50 мс. Для ввода измеряется следующий кадр того же окна; для операций — выполнение и кадр с результатом. Первый кадр не означает завершения фоновой загрузки.",
	"The TACTIC server is unreachable or did not respond in time. Check the server address, network connection, VPN or proxy, and make sure the server is running. Then try again.": "Сервер TACTIC недоступен или не ответил вовремя. Проверьте адрес сервера, подключение к сети, VPN или прокси и убедитесь, что сервер запущен. Затем повторите попытку.",
	"The server has not been set up yet. Initialize its database and set an administrator password.": "Сервер ещё не настроен. Инициализируйте базу данных и задайте пароль администратора.",
	"Ticket stored": "Тикет сохранён",
	Total: "Всего",
	"Type error": "Ошибка типа данных",
	"UI measurements": "Измерения интерфейса",
	"UI responsiveness": "Отзывчивость интерфейса",
	USERS: "ПОЛЬЗОВАТЕЛИ",
	"Use portal site": "Использовать портал",
	"Use proxy": "Использовать прокси",
	"Use when TACTIC and Handler share local storage. If paths differ, sync them in Repository configuration. Preview, check-in, and check-out methods are locked to local access.": "Включайте, когда TACTIC и Handler работают с локальным хранилищем. Если пути различаются, синхронизируйте их в настройках репозитория. Превью, Check-in и Check-out будут закреплены за локальным доступом.",
	"Value error": "Ошибка значения",
	"WORK HOURS": "РАБОЧИЕ ЧАСЫ",
	inspect: "Сведения об объекте",
	module: "модуль",
	ms: "мс",
	overdue: "просрочено",
	right: "справа",
	task: "задача",
	"{count} events": "Событий: {count}",
	"{hours} h": "{hours} ч",
	"Open event details": "Открыть подробности события",
	"Stored ticket": "Сохранённый билет",
	"Avatar selected": "Аватар выбран",
	"Remove preset": "Удалить пресет",
	"Leave empty to keep the stored password.": "Оставьте пустым, чтобы сохранить прежний пароль.",
	"A view with this name already exists": "Представление с таким именем уже существует",
	"Actions on hover": "Действия при наведении",
	"Applies to every process with this name in the project, including other pipelines.": "Действует для всех процессов с этим именем в проекте, включая другие pipeline.",
	"Apply or discard the pending text before continuing": "Примените или сбросьте введённый текст перед продолжением",
	"Attributes must be a JSON object with string values": "Атрибуты должны быть объектом JSON со строковыми значениями",
	"Checking objects and dependencies…": "Проверка объектов и зависимостей…",
	"Choose which actual task date to set.": "Выберите, какую фактическую дату задачи изменить.",
	"Conditions are checked as XML before saving.": "Перед сохранением проверяется XML условий.",
	"Database table unavailable": "Таблица базы данных недоступна",
	"Enter a whole number within the allowed range": "Введите целое число в допустимом диапазоне",
	"Explain why this rule is needed.": "Объясните назначение этого правила.",
	"Filter the source task status, or listen to any status.": "Выберите исходный статус задачи или отслеживайте любой статус.",
	"Invalid JSON. Check quotes, commas and braces.": "Некорректный JSON. Проверьте кавычки, запятые и скобки.",
	"Invalid layout template": "Некорректный шаблон компоновки",
	"Invalid view name": "Некорректное имя представления",
	"Mobile actions": "Мобильные действия",
	"Native action parameters. TACTIC expressions are supported by notifications.": "Штатные параметры действия. В уведомлениях поддерживаются выражения TACTIC.",
	"No Search Objects": "Нет Search Objects",
	"Node positions must be finite": "Координаты узлов должны быть конечными числами",
	"Notification message with optional TACTIC expressions.": "Текст уведомления; можно использовать выражения TACTIC.",
	"Object information": "Сведения об объекте",
	"Process settings must be a JSON object": "Параметры процесса должны быть объектом JSON",
	"Related and child objects": "Связанные и дочерние объекты",
	"Save or discard changes before continuing": "Сохраните или сбросьте изменения перед продолжением",
	"Save the workflow before editing process dependencies": "Сохраните рабочий процесс перед редактированием зависимостей",
	"Schema changed on the server. Reload before deleting a Search Type.": "Схема изменилась на сервере. Обновите её перед удалением Search Type.",
	"Select a SObject layout configuration": "Выберите конфигурацию компоновки SObject",
	"Source status": "Исходный статус",
	"Tasks and notes": "Задачи и заметки",
	"The database table is absent. No table is created by reading columns.": "Таблица базы данных отсутствует. Чтение колонок не создаёт таблицу.",
	"The deletion result is unknown. Close this review and reload the schema before trying again.": "Результат удаления неизвестен. Закройте это окно и обновите схему перед повторной попыткой.",
	"The native event template replaces the subject and body when saved.": "При сохранении штатный шаблон события заменит тему и текст.",
	"The native event that starts this rule.": "Штатное событие, запускающее это правило.",
	"The native notification handler may include a login ticket.": "Штатный обработчик уведомлений может включать тикет входа.",
	"The readable name of this rule.": "Понятное имя этого правила.",
	"This process is referenced by a connection. Add the missing process or remove its connections before saving.": "На этот процесс ссылается связь. Добавьте отсутствующий процесс или удалите его связи перед сохранением.",
	"Use a lowercase table name with letters, digits and underscores": "Используйте строчные латинские буквы, цифры и подчёркивания в имени таблицы",
	"Use inherited": "Наследовать",
	Assignment: "Назначение",
	Body: "Текст",
	Depth: "Глубина",
	Editor: "Редактор",
	Select: "Выбрать",
	"Invalid column move": "Некорректное перемещение колонки",
	"The column cannot be moved further.": "Колонку нельзя переместить дальше.",
	Guide: "Руководство",
	Reference: "Справочник",
	"Help topics": "Разделы справки",
	"Search help": "Поиск по справке",
	"Close help topics": "Закрыть разделы справки",
	"Reload help articles": "Перезагрузить статьи справки",
	"Open article file": "Открыть файл статьи",
	"Download article": "Скачать статью",
	"No help topics match your search": "Подходящие разделы справки не найдены",
	Display: "Вид",
	Enabled: "Включено",
	"Start date": "Дата начала",
	"Assigned to": "Исполнитель",
	Actions: "Действия",
	Loading: "Загрузка",
	Size: "Размер",
	Assets: "Ассеты",
	Thumbnail: "Миниатюра",
	"Delete the selected sidebar item?": "Удалить выбранный элемент бокового меню?",
	"%1 nodes selected": "Выделено нод: %1",
	"1. Choose a starting point · 2. Arrange elements · 3. Check and save": "1. Выбери заготовку · 2. Размести элементы · 3. Проверь и сохрани",
	"A deadline or another date with a time.": "Срок сдачи или другая дата со временем.",
	"A field stores one attribute of each Search Object. Define its name and type here; fill in actual values when editing the objects.": "Поле хранит один параметр каждого серч-объекта. Здесь задаются имя и тип поля, а сами значения заполняются при редактировании объектов.",
	"A flag with two values, stored as true or false.": "Признак с двумя значениями, в базе хранится как true или false.",
	"A new preview is ready to be queued": "Новое превью готово к добавлению в очередь",
	"A read-only view of this Search Type and only its direct schema relationships.": "Схема выбранного серч-тайпа и только его прямых связей — без редактирования.",
	"A recognizable name for users.": "Понятное название для пользователей.",
	"A technical name: lowercase Latin letters, numbers and underscores. For example, duration_minutes. No spaces; start with a letter.": "Техническое имя: строчные латинские буквы, цифры и подчёркивания. Например, duration_minutes. Без пробелов, первая — буква.",
	"APPLY XML": "ПРИМЕНИТЬ XML",
	"Accent color": "Цвет",
	"Access level": "Уровень доступа",
	"Access rules": "Правила доступа",
	"Access: %1": "Доступ: %1",
	Action: "Действие",
	"Action and condition nodes use a native process|action trigger. Script changes are saved, not executed by this editor.": "Узлы action и condition используют триггер process|action. Редактор сохраняет скрипты, но не запускает их.",
	Active: "Активные",
	"Actual date": "Фактическая дата",
	Add: "Добавить",
	"Add a field": "Добавить поле",
	"Add an image, text or button to begin.": "Для начала добавь картинку, текст или кнопку.",
	"Add link": "Добавить ссылку",
	"Add node": "Добавить узел",
	"Add process": "Добавить процесс",
	"Add rule": "Добавить правило",
	"Add section": "Добавить раздел",
	"Add separator": "Добавить разделитель",
	"Add to canvas": "Добавить на схему",
	"Add to draft": "Добавить в черновик",
	"Add widget": "Добавить виджет",
	"Additional conditions (native rules XML)": "Дополнительные условия (XML правил TACTIC)",
	"Additional fields": "Дополнительные поля",
	"Additional fields to create (%1)": "Дополнительные поля к созданию (%1)",
	Administration: "Администрирование",
	"Advanced JSON": "Расширенный JSON",
	"Advanced XML": "Расширенный XML",
	"Advanced access to native data, including parameters of installed custom nodes. Standard settings are available in Parameters.": "Расширенные данные TACTIC, включая параметры установленных пользовательских нод. Обычные настройки доступны в разделе «Параметры».",
	"Advanced fields": "Дополнительные поля",
	"Advanced layout settings and XML": "Дополнительные настройки компоновки и XML",
	"Advanced rule pages": "Разделы расширенных правил",
	"Advanced rules": "Расширенные правила",
	"Affect related objects only, or all objects of this Search Type.": "Работать только со связанными объектами или со всеми объектами серч-тайпа.",
	All: "Все",
	"All Search Types": "Все Search Type",
	"All data in these columns will be lost. This editor cannot restore it after saving. Check any scripts, naming rules and saved searches that use these fields.": "Все данные в этих столбцах будут потеряны. После сохранения этот редактор не сможет их восстановить. Проверьте скрипты, правила нейминга и сохранённые поиски, использующие эти поля.",
	"All group rules": "Все правила группы",
	"All groups": "Все группы",
	"All matching processes": "Все одноимённые процессы",
	"All objects": "Все объекты",
	"All targets": "Все объекты",
	"Allow processes and tasks for this Search Type.": "Разрешить процессы и задачи для этого серч-тайпа.",
	"Already on schema": "Уже на схеме",
	"Any status": "Любой статус",
	Appearance: "Внешний вид",
	"Applies only to this process in this pipeline.": "Применяется только к этому процессу в этом пайплайне.",
	"Applies to every process named %1 in this project, including other pipelines.": "Применяется ко всем процессам с именем %1 в проекте, в том числе в других пайплайнах.",
	Apply: "Применить",
	"Apply administrative changes?": "Применить изменения на сервере?",
	"Apply attributes": "Применить атрибуты",
	"Apply settings": "Применить параметры",
	"Apply to draft": "В черновик",
	"Apply to draft, then save the table.": "Примените к черновику, затем сохраните таблицу.",
	"Apply updates the draft. Save sends it to the server.": "«Применить» обновляет черновик. «Сохранить» отправляет его на сервер.",
	Approval: "Согласование",
	Archive: "Архивировать",
	"Arrange nodes": "Расставить ноды",
	"Arrange processes on the canvas, connect their ports and select a process to configure it.": "Разместите процессы на графе, соедините порты и выберите процесс для настройки.",
	"Assigned group": "Группа исполнителей",
	"Assigned user": "Исполнитель",
	"Assignment choices and default estimates for this process.": "Исполнители и плановые значения задач этого процесса.",
	"Attributes (JSON)": "Атрибуты (JSON)",
	"Automatic layout": "Автоматическая раскладка",
	"Available targets": "Доступные объекты",
	Back: "Назад",
	"Back to rules": "К правилам",
	"Behave as": "Соответствует статусу",
	"Build your own view": "Собери свой вид",
	"Built-in system schema · read-only": "Встроенная системная схема · только чтение",
	Cancel: "Отмена",
	"Cannot be empty in the database": "В базе не может быть пустым",
	"Card width": "Ширина карточки",
	"Cell editor": "Редактор ячейки",
	"Change parent status": "Изменить статус родителя",
	"Change process": "Изменить процесс",
	"Change task statuses": "Изменить статусы задач",
	"Checked = allowed. The lock marks a grant controlled by another rule. Other group memberships can also grant access.": "Галочка — доступ разрешён. Замок — доступ задан другим правилом. Членство в других группах тоже может давать доступ.",
	"Checking the table and its dependencies…": "Проверяем таблицу и её зависимости…",
	"Child key column": "Ключевое поле дочернего объекта",
	"Choose Search Type preview": "Выбрать превью серч-тайпа",
	"Choose a registered Search Type to add to the schema.": "Выберите серч-тайп, который нужно добавить на схему.",
	"Choose a server target or enter its identifier. An asterisk matches all targets.": "Выберите объект сервера или введите его код. Звёздочка означает все объекты.",
	"Choose an existing user to receive approval tasks.": "Выберите пользователя, которому назначаются задачи согласования.",
	"Choose an input port. Esc cancels the connection.": "Выберите входной порт. Esc отменяет создание связи.",
	"Choose an output port. Esc cancels the connection.": "Выберите выходной порт. Esc отменяет создание связи.",
	"Choose existing columns below, or enter a new key column name. New columns are created on schema save, using the opposite key's type.": "Выберите столбцы из списков или введите имя нового. Новые столбцы создаются при сохранении схемы с типом ключа на другой стороне связи.",
	"Choose the native behavior of this process.": "Выберите поведение процесса в TACTIC.",
	"Choose the pipeline this hierarchy process opens.": "Выберите пайплайн, который открывает этот процесс hierarchy.",
	"Choose which objects and processes this node signals or tracks.": "Укажите, каким объектам и процессам нода отправляет события или за какими следит.",
	"Click a part of the preview, or select it in Elements.": "Нажми на часть примера или выбери её в списке элементов.",
	Close: "Закрыть",
	"Close details": "Закрыть карточку",
	"Close process dependencies": "Закрыть зависимости процесса",
	"Close workflow editor": "Закрыть редактор workflow",
	"Collapse navigation": "Свернуть навигацию",
	"Collection layout": "Размещение объектов",
	Color: "Цвет",
	Column: "Колонка",
	Columns: "Колонки",
	"Columns Editor": "Редактор колонок",
	"Columns of system and config Search Types cannot be deleted here.": "Столбцы системных серч-тайпов и config здесь удалять нельзя.",
	"Completion level represented by this process or status.": "Процент готовности, которому соответствует процесс или статус.",
	"Completion, %": "Готовность, %",
	"Configuration changes": "Изменения конфигурации",
	"Configuration source": "Источник конфигурации",
	"Configuration view": "Представление конфигурации",
	"Confirm table name": "Подтверждение имени таблицы",
	Connect: "Соединить",
	"Connect Search Types to describe how Search Objects relate to each other.": "Соедините серч-тайпы, чтобы задать связи между серч-объектами.",
	"Connect processes": "Соединить процессы",
	Connection: "Подключение",
	"Connection {from} to {to}": "Связь {from} → {to}",
	"Connections refer to missing processes: %1. Add the missing processes or remove their connections before saving.": "Связи ссылаются на отсутствующие процессы: %1. Перед сохранением добавьте эти процессы или удалите лишние связи.",
	Content: "Содержимое",
	"Copy recipients": "Копия письма",
	"Counts or durations in whole units, without a fractional part.": "Количество или длительность в целых единицах, без дробной части.",
	Create: "Создать",
	"Create a Search Object before evaluating this rule.": "Для проверки правила сначала создайте объект.",
	"Create a table and add its node to the project schema. Your current connections and canvas edits will be kept.": "Создайте таблицу и добавьте её ноду на схему проекта. Текущие связи и изменения канваса сохранятся в черновике.",
	"Create a task when a workflow event reaches this process.": "Создавать задачу, когда в процесс поступает событие воркфлоу.",
	"Create a trigger or notification using the plus button.": "Создайте триггер или уведомление кнопкой «+».",
	"Create a user group in Groups before editing its permissions. The admin group has full access and is not editable here.": "Сначала создайте группу в разделе «Группы». Группа admin имеет полный доступ и здесь не редактируется.",
	"Create a workflow from a saved Search Type.": "Создайте воркфлоу из сохранённого серч-тайпа.",
	"Create custom view": "Создать свой вид",
	"Create group": "Создать группу",
	"Create missing columns": "Создать недостающие столбцы",
	"Create naming rule": "Создать правило именования",
	"Create output tasks": "Создать задачи следующих процессов",
	"Create parent task and subtasks": "Создавать задачу и подзадачи",
	"Create parent task only": "Создавать только родительскую задачу",
	"Create subtasks only": "Создавать только подзадачи",
	"Create task status workflow": "Создать workflow статусов задач",
	"Create tasks": "Создавать задачи",
	"Create tasks automatically": "Создавать задачи автоматически",
	"Create workflow": "Создать воркфлоу",
	"Create workflow for": "Создать workflow для",
	"Create workflow for %1": "Создать воркфлоу для %1",
	"Create workflow for {type}": "Создать воркфлоу для {type}",
	"Created on save": "Будет создан при сохранении",
	"Current Search Type preview": "Текущее превью серч-тайпа",
	"Custom access level: %1. Edit it in Advanced rules.": "Особый уровень доступа: %1. Его можно изменить в расширенных правилах.",
	"Custom access level: {level}. Edit it in Advanced rules.": "Особый уровень доступа: {level}. Измените его в расширенных правилах.",
	"Custom attributes (JSON)": "Произвольные атрибуты (JSON)",
	"Custom event": "Другое событие",
	"Custom scopes": "Дополнительные категории",
	"Custom views and SObject item layouts": "Пользовательские виды и компоновки SObject",
	DISCARD: "НЕ СОХРАНЯТЬ",
	"DROP TABLE": "DROP TABLE",
	"Data location": "Где хранятся данные",
	Database: "База данных",
	"Database table": "Таблица базы данных",
	"Database type: %1": "Тип в базе: %1",
	"Database type: {type}": "Тип в базе данных: {type}",
	"Database: %1": "База данных: %1",
	"Date and time": "Дата и время",
	"Decimal number": "Дробное число",
	Default: "По умолчанию",
	"Default duration, days": "Длительность по умолчанию, дни",
	"Default fields": "Стандартные поля",
	"Default planned effort for a new task.": "Плановая трудоёмкость новой задачи.",
	"Default reviewer for approval tasks.": "Исполнитель задач согласования по умолчанию.",
	"Defines statuses only for tasks of this process, not stages of the parent Search Object workflow.": "Задаёт статусы только для задач этого процесса, а не этапы воркфлоу родительского серч-объекта.",
	Delete: "Удалить",
	"Delete Search Type from project": "Удалить SearchType из проекта",
	"Delete Search Type from project?": "Удалить серч-тайп из проекта?",
	"Delete Search Type…": "Удалить серч-тайп…",
	"Delete columns from %1 (%2):": "Удалить столбцы из %1 (%2):",
	"Delete field": "Удалить поле",
	"Delete fields from {type}: {fields}? All values in these columns will be lost. Check scripts, naming rules and saved searches before saving.": "Удалить поля из {type}: {fields}? Все значения этих колонок будут потеряны. Перед сохранением проверьте скрипты, правила нейминга и сохранённые поиски.",
	"Delete from project": "Удалить из проекта",
	"Delete marks a field for removal. Undo cancels the mark. Confirming Save deletes the column and its values; field types are not changed here.": "Удаление помечает поле, а отмена снимает пометку. Подтверждённое сохранение удаляет колонку и её значения; типы полей здесь не меняются.",
	"Delete marks a field for removal. You can undo the mark before saving. Confirming Save deletes the column and all its values; field types are not changed here.": "Кнопка удаления помечает поле. До сохранения пометку можно отменить. После подтверждения сохранения столбец и все его значения будут удалены; типы полей здесь не меняются.",
	"Delete row": "Удалить строку",
	"Deleting Search Type…": "Удаляем серч-тайп…",
	"Deletion is blocked. Remove Search Objects and dependencies first, or only remove the node from the canvas.": "Удаление заблокировано. Сначала удалите серч-объекты и зависимости либо только уберите ноду со схемы.",
	Deny: "Запрет",
	"Dependency sections": "Разделы зависимостей",
	"Describe the scene and what needs to be done.": "Опишите сцену и что нужно сделать.",
	Description: "Описание",
	"Descriptions and notes spanning several lines.": "Описания и заметки из нескольких строк.",
	Destination: "Назначение",
	"Destination status": "Целевой статус",
	"Destination tasks": "Задачи для изменения",
	Details: "Параметры",
	"Direct table editing and CSV export": "Прямое редактирование таблиц и экспорт CSV",
	"Directory naming": "Именование папок",
	Discard: "Не сохранять",
	"Discard changes": "Отменить изменения",
	"Discard naming changes": "Отменить изменения нейминга",
	"Discard unapplied JSON changes?": "Отменить неприменённые изменения JSON?",
	"Discard unsaved access changes?": "Отменить несохранённые изменения прав?",
	"Discard unsaved changes?": "Отменить несохранённые изменения?",
	"Discard unsaved definition changes?": "Отменить несохранённые изменения определения?",
	"Discard unsaved naming changes?": "Отменить несохраненные изменения именования?",
	"Discard unsaved raw table changes?": "Отменить несохранённые изменения таблицы?",
	"Discard unsaved sidebar changes and reload from the server?": "Отменить несохранённые изменения сайдбара и загрузить конфигурацию с сервера?",
	"Display label": "Отображаемое название",
	"Do not create tasks": "Не создавать задачи",
	Draft: "Черновик",
	"Draft · not saved yet": "Черновик · ещё не сохранён",
	"Drag a selected node to move the group · Delete: remove selection · F: center selection · Home: reset view · Ctrl+S: save": "Потяните выделенную ноду, чтобы переместить группу · Delete — убрать выделенное · F — центрировать · Home — сбросить вид · Ctrl+S — сохранить",
	"Drag an element onto a cell, or use the move buttons.": "Перетащите элемент на ячейку или используйте кнопки перемещения.",
	"Duplicate selected rule": "Дублировать выбранное правило",
	"Each Search Object selects its pipeline through the pipeline_code field.": "Пайплайн каждого серч-объекта задаётся в поле pipeline_code.",
	"Each process uses its own task status workflow.": "У каждого процесса свой воркфлоу статусов задач.",
	Edit: "Редактировать",
	"Edit generated workflow triggers in the node parameters": "Меняйте сгенерированные триггеры в параметрах узла",
	"Edit one native TACTIC element at a time. Custom options remain unchanged in XML.": "Редактируйте по одному нативному элементу TACTIC. Пользовательские параметры в XML останутся без изменений.",
	"Edit pipelines": "Редактировать пайплайны",
	"Edit rule": "Изменить правило",
	"Edit task status workflow": "Редактировать статусы задач",
	"Edit the title and description without changing the Search Type identity.": "Изменение названия и описания сохраняет идентификатор типа объектов.",
	Elements: "Элементы",
	"Enter %1 to confirm": "Для подтверждения введите %1",
	"Enter {type} to confirm": "Введите {type} для подтверждения",
	"Entities and fields": "Серч-тайпы и их поля",
	"Estimated work, hours": "Плановая работа, часы",
	"Evaluate the draft on a real object with the native TACTIC engine. Preview does not check in a file.": "Проверка черновика на реальном объекте штатным движком TACTIC. Файл не сдаётся в репозиторий.",
	Event: "Событие",
	"Exact status name understood by the target process.": "Точное имя статуса, который поддерживает целевой процесс.",
	"Example description": "Пример описания",
	"Example object": "Пример объекта",
	"Example value: %1": "Пример значения: %1",
	"Example value: {value}": "Пример значения: {value}",
	"Example: %1 = %2": "Пример: %1 = %2",
	"Example: {name} = {value}": "Пример: {name} = {value}",
	"Execution mode": "Режим выполнения",
	"Existing fields (%1)": "Поля на сервере (%1)",
	"Existing fields ({count})": "Существующие поля ({count})",
	"Existing files already use this path: {count}": "Этот путь уже используют файлы: {count}",
	"Expand navigation": "Развернуть навигацию",
	"Explain what happens at this stage of the workflow.": "Опишите, что происходит на этом этапе.",
	"Explain what these Search Objects represent.": "Опишите, что представляют собой эти серч-объекты.",
	"Explain what this pipeline is used for.": "Опишите назначение этого пайплайна.",
	"Explicit permission for this group.": "Право явно задано для этой группы.",
	"Export CSV": "Экспорт CSV",
	Field: "Поле",
	"Field access": "Доступ к полям",
	"Field name": "Имя поля",
	"Field type": "Тип данных",
	Fields: "Поля",
	"Fields to create (%1)": "Будут созданы поля (%1)",
	"Fields to create ({count})": "Поля для создания ({count})",
	"File checked in": "Файл опубликован",
	"File naming": "Именование файлов",
	"File type": "Тип файла",
	"Filter by Search Type": "Фильтр по Search Type",
	"Filter saved views": "Фильтр сохранённых представлений",
	"Filter tables": "Фильтр таблиц",
	"Find a Search Type": "Найти серч-тайп",
	"Find a field": "Поиск поля",
	"Find a group": "Найти группу",
	"Find a permission": "Найти право доступа",
	"Find a pipeline": "Найти пайплайн",
	"Find a server target": "Найти объект на сервере",
	"Find a target or rule": "Найти объект или правило",
	"Find the permission row and the group column, then tick to allow access. Changes across groups are saved together.": "Найдите строку права и столбец группы, затем поставьте галочку, чтобы разрешить доступ. Изменения всех групп сохраняются вместе.",
	Firetruck: "Пожарная машина",
	"From (child)": "От (дочерний)",
	"Full access": "Полный доступ",
	"Generate a temporary login ticket": "Создавать временный тикет для входа",
	"Generated workflow rule": "Сгенерированное правило workflow",
	"Global permissions": "Общие права",
	"Granted by defaults, subgroups or an All rule. Change the granting rule first.": "Доступ задан настройками группы, подгруппами или правилом «Все». Сначала измените правило, выдающее доступ.",
	Group: "Группа",
	"Group defaults": "Базовые правила группы",
	"Group project (empty = global)": "Проект группы (пусто — общая)",
	Groups: "Группы",
	"Groups and members": "Группы и участники",
	Help: "Справка",
	"Hide config types": "Скрыть типы config",
	"Hide properties": "Скрыть свойства",
	"Hide workflow list": "Скрыть список воркфлоу",
	"Hierarchy: child → parent.": "Иерархия: дочерний → родительский объект.",
	"How many tasks to create for this process.": "Сколько задач создавать для этого процесса.",
	"How this Search Type appears in navigation and Search Object lists.": "Как серч-тайп выглядит в навигации и списках серч-объектов.",
	"How this item appears in project navigation. Its color comes from the Search Type; selection follows your theme.": "Как пункт выглядит в навигации проекта. Цвет берётся из типа объектов, а выделение — из выбранной темы.",
	Identifier: "Идентификатор",
	"Image sent to Commit Queue; track upload progress there": "Изображение передано в очередь отправки; следите за загрузкой там",
	"In process": "В текущем процессе",
	"Include this process when generating tasks.": "Включать процесс при создании задач.",
	"Inherited access-level defaults (server)": "Базовые права уровня группы (сервер)",
	"Inherited defaults still apply. Add a rule to override them for a target.": "Базовые права продолжают действовать. Добавьте правило, чтобы изменить их для нужного объекта.",
	"Inherited. Click to set an explicit permission.": "Правило наследуется. Нажмите, чтобы задать право явно.",
	"Initial interval between a task's start and end dates.": "Начальный интервал между датами начала и окончания задачи.",
	"Input name": "Имя входа",
	"Input process": "Входной процесс",
	Inspector: "Свойства",
	"Installed Python class": "Установленный класс Python",
	"Instance table name": "Имя связующей таблицы",
	"Item preview": "Предпросмотр строки",
	"Its description, action and native settings will appear here.": "Здесь появятся его описание, действие и параметры TACTIC.",
	"Its details appear here.": "Здесь отображаются сведения о выбранном элементе.",
	"Its details appear here. Use Add node to extend the canvas.": "Здесь появятся его параметры. Для нового узла откройте «Добавить узел».",
	"Keep editing": "Продолжить",
	"Key fields: %1 → %2": "Поля связи: %1 → %2",
	"Key fields: {from} → {to}": "Ключевые поля: {from} → {to}",
	"Layout Editor": "Редактор компоновки",
	"Layout: ": "Компоновка: ",
	"Limits the available assignees to members of this group.": "Исполнителей можно будет выбирать из участников этой группы.",
	"Limits the available supervisors to members of this group.": "Супервайзеров можно будет выбирать из участников этой группы.",
	"Link table · M:N": "Связующая таблица · M:N",
	"Link table: %1": "Связующая таблица: %1",
	"Link table: {name}": "Таблица связи: {name}",
	"Linked workflows": "Связанные workflows",
	"Loading columns…": "Загрузка столбцов…",
	"Loading data…": "Загружаем данные…",
	"Loading interface…": "Загружаем интерфейс…",
	"Loading sidebar configuration...": "Загрузка конфигурации боковой панели...",
	"Loading…": "Загрузка…",
	"Long text": "Длинный текст",
	"Manage groups and members": "Управление группами и участниками",
	"Managed by node parameters": "Задаётся параметрами ноды",
	"Many-to-many (M:N): each side can be linked to several objects on the other side.": "Многие ко многим (M:N): каждый объект может быть связан с несколькими объектами другой стороны.",
	"Many-to-many · M:N": "Многие ко многим · M:N",
	"Many-to-many · new Search Type": "Многие ко многим · новый серч-тайп",
	"Map this status to a native behavior, or explicitly change a connected process.": "Задайте стандартное поведение статуса или изменение связанного процесса.",
	"Marked for deletion. The column and its data will be deleted when you save.": "Помечено на удаление. Столбец и его данные будут удалены при сохранении.",
	"Measurements that need a fractional part.": "Измерения, для которых нужна дробная часть.",
	"Members and group management": "Группы и их участники",
	"Menu action": "Действие меню",
	"Menu actions": "Действия меню",
	"Missing process: %1": "Процесс отсутствует: %1",
	Modify: "Изменение",
	"More element settings": "Дополнительные настройки элемента",
	Name: "Имя",
	"Name the process and choose its native type.": "Задайте имя процесса и выберите его тип в TACTIC.",
	"Names and short labels, up to 256 characters.": "Названия и короткие подписи, до 256 символов.",
	Naming: "Нейминг",
	"Naming actions": "Действия нейминга",
	"Naming conventions": "Правила нейминга",
	"Naming editor": "Редактор нейминга",
	"Naming preview": "Превью именования",
	"Naming result": "Результат нейминга",
	"Naming rules": "Правила именования",
	"Native XML": "XML TACTIC",
	"Native access rules": "Правила доступа TACTIC",
	"Native access value: %1. It is kept until you choose a different level.": "Значение доступа TACTIC: %1. Оно сохранится, пока вы не выберете другой уровень.",
	"Native check-in ignores config/naming rules in admin and sthpw. Preview evaluates the expression only.": "Штатная сдача файлов не использует config/naming в admin и sthpw. Предпросмотр только вычисляет выражение.",
	"Native command class": "Класс команды TACTIC",
	"Native event identifier": "Идентификатор события TACTIC",
	"Native process settings": "Параметры процесса TACTIC",
	"Native task status behavior.": "Стандартное поведение статуса задачи в TACTIC.",
	"New Search Type": "Новый серч-тайп",
	"New naming rule": "Новое правило нейминга",
	"New override": "Новое переопределение",
	"New pipeline": "Новый пайплайн",
	"New row": "Новая строка",
	"New rule": "Новое правило",
	Next: "Далее",
	"No Search Type": "Без серч-тайпа",
	"No Search Type is linked. Create a workflow from the Search Type editor.": "Серч-тайп не привязан. Создайте воркфлоу из редактора серч-тайпа.",
	"No Search Types found": "Серч-тайпы не найдены",
	"No additional fields": "Нет дополнительных полей",
	"No description": "Без описания",
	"No explicit relationships for this type in the loaded schemas.": "В загруженных схемах нет явно заданных связей для этого серч-тайпа.",
	"No explicit rules in this category": "В этой категории пока нет правил",
	"No fields found": "Поля не найдены",
	"No login groups were loaded from the server.": "С сервера не загружены группы пользователей.",
	"No matching permissions or groups": "Подходящие права или группы не найдены",
	"No matching rules": "Подходящих правил нет",
	"No matching targets. You can enter an identifier above.": "Ничего не найдено. Можно ввести код вручную выше.",
	"No naming conventions for this process.": "У процесса нет правил нейминга.",
	"No pipelines are linked to this Search Type": "У серч-тайпа нет связанных пайплайнов",
	"No rows": "Нет записей",
	"No rule selected": "Правило не выбрано",
	"No rules configured. Use Add rule to create one.": "Правил нет. Нажмите «Добавить правило».",
	"No rules for this search type": "Для этого типа поиска нет правил",
	"No saved definitions match the filter": "Нет определений, подходящих под фильтр",
	"No types found": "Типы не найдены",
	"No workflows linked to this Search Type.": "У типа объектов нет связанных workflows.",
	"Node type": "Тип узла",
	"Node type: %1": "Тип узла: %1",
	"Nodes and connections": "Узлы и связи",
	None: "Нет доступа",
	"Not set": "Не задано",
	"Note created": "Создана заметка",
	"Note created or modified": "Заметка создана или изменена",
	"Notification content": "Содержание уведомления",
	Notifications: "Уведомления",
	"Number of tasks": "Количество задач",
	"Object details": "Карточка объекта",
	"Object identifier. This field cannot be deleted.": "Идентификатор объекта. Это поле нельзя удалить.",
	"Objects (including retired)": "Объекты (включая архивные)",
	"Objects use a pipeline": "Серч-объекты используют пайплайн",
	"Objects using this pipeline": "Объекты с этим пайплайном",
	"One level per rule. Higher levels include lower ones; this is not a set of independent permissions.": "У каждого правила один уровень доступа. Более высокий уровень включает предыдущие.",
	"Only a connection to this process exists in the XML. Use Add node to recreate it with the same name, or select and remove the connection.": "В XML есть только ссылка на этот процесс. Добавьте ноду с таким же именем или выделите и удалите лишнюю связь.",
	"Only connected output processes are available. Add connections on the canvas first.": "Доступны только процессы с исходящими связями от этой ноды. Сначала добавьте связи на схеме.",
	"Only current project": "Только текущий проект",
	"Only pipelines of the selected Search Type are listed.": "В списке только пайплайны выбранного серч-тайпа.",
	"Only the selected connection will be removed when you save. Its nodes and their data will not be deleted.": "При сохранении будет убрана только выбранная связь. Ноды и их данные не удаляются.",
	"Only the selected node and its connections will be removed from this schema when you save. The Search Type, its table, objects and pipelines will not be deleted.": "При сохранении из этой схемы будет убрана только выбранная нода и её связи. Серч-тайп, таблица, объекты и пайплайны не удаляются.",
	"Open a cell to edit its value. Text needs no quotes. Choose NULL or Database default explicitly in the cell editor.": "Откройте ячейку для редактирования. Текст вводится без кавычек. NULL и значение БД по умолчанию выбираются явно в редакторе ячейки.",
	"Open process dependencies": "Открыть зависимости процесса",
	"Open workflow": "Открыть воркфлоу",
	Operator: "Оператор",
	"Optional TACTIC search expression; it replaces selection by Search Type.": "Необязательное выражение поиска TACTIC. Заменяет выбор по серч-тайпу.",
	"Other registrations for this table": "Другие регистрации этой таблицы",
	"Other schemas using this type": "Другие схемы, использующие этот тип",
	"Output condition": "Условие выхода",
	"Output process": "Выходной процесс",
	"Output processes": "Следующие процессы",
	"Parent key column": "Ключевое поле родительского объекта",
	"Permanently delete this table and all its rows? Type its full name to confirm.": "Безвозвратно удалить таблицу со всеми записями? Для подтверждения введите полное имя.",
	Permission: "Разрешение",
	"Permission / Group": "Право / Группа",
	"Permission matrix": "Матрица прав",
	"Permission scopes": "Области доступа",
	Pipeline: "Пайплайн",
	"Pipeline details": "Параметры пайплайна",
	"Pipeline settings": "Настройки пайплайна",
	Pipelines: "Пайплайны",
	"Pipelines and workflow": "Пайплайны и воркфлоу",
	"Pipelines linked to this Search Type, including shared workflows.": "Pipelines этого типа объектов, включая общие workflows.",
	"Pipelines with processes": "Pipeline с процессами",
	"Pipelines: %1": "Пайплайны: %1",
	"Place on the grid": "Разместить на сетке",
	Position: "Позиция",
	"Positions follow shared item styles. Choose Grid in the parent container for placement by rows and columns.": "Позиции задаются стилями исходного item. Для размещения по строкам и столбцам выберите сетку в родительском контейнере.",
	"Preview as group": "Предпросмотр от лица группы",
	"Preview data could not be loaded": "Не удалось загрузить данные для предпросмотра",
	"Preview is optional": "Превью — по желанию",
	Previous: "Назад",
	Priority: "Приоритет",
	Process: "Процесс",
	"Process action": "Действие процесса",
	"Process dependencies": "Зависимости процесса",
	"Process name": "Имя процесса",
	Processes: "Процессы",
	"Processes and connections": "Процессы и связи",
	"Processes and tasks are enabled": "Процессы и задачи включены",
	"Processes, dependencies and scripts": "Процессы, зависимости и скрипты",
	"Processes: %1": "Процессов: %1",
	"Profiles and accounts": "Профили и учётные записи",
	Project: "Проект",
	"Project navigation": "Навигация проекта",
	"Project navigation and sidebar items": "Навигация проекта и элементы боковой панели",
	"Project schema": "Схема проекта",
	"Project-specific rules are preserved. Select a rule to edit its native attributes.": "Правила для отдельных проектов сохраняются. Выберите правило для настройки его атрибутов.",
	"Project: %1 · Table: %2": "Проект: %1 · Таблица: %2",
	Projects: "Проекты",
	"Projects, entities, processes and interface": "Проекты, серч-объекты и интерфейс",
	Queued: "В очереди",
	"Raw SQL bypasses object validation, triggers and undo history. Changes can break the application.": "Прямой SQL обходит проверки объектов, триггеры и историю отмены. Изменения могут нарушить работу приложения.",
	"Raw database": "Raw-редактор базы",
	"Raw table rows": "Строки таблицы базы данных",
	Read: "Чтение",
	"Read-only": "Только чтение",
	"Read-only preview. Changes have not been saved.": "Предпросмотр без редактирования. Изменения ещё не сохранены.",
	"Ready to create": "Всё готово к созданию",
	Recipients: "Получатели",
	"Refreshing server metadata…": "Обновляю данные проекта…",
	"Registered Search Types": "Зарегистрированные типы объектов",
	"Related object expression": "Выражение поиска связанных объектов",
	"Related objects": "Связанные объекты",
	"Related type": "Тип связанных объектов",
	"Related pipeline": "Связанный пайплайн",
	"Related process": "Связанный процесс",
	"Related workflow": "Связанный воркфлоу",
	Relationship: "Связь",
	"Relationship in schema: %1": "Тип связи в схеме: %1",
	"Relationship in schema: {kind}": "Тип связи в схеме: {kind}",
	"Relationship map": "Карта связей",
	"Relationship map for {name}": "Карта связей для {name}",
	"Relationship type": "Тип связи",
	"Relationships between entities": "Связи между серч-тайпами",
	"Relationships come from this project's schema and inherited schemas, not from table names.": "Связи взяты из схемы проекта и унаследованных схем, а не определены по именам таблиц.",
	Reload: "Обновить",
	"Reload columns from server": "Обновить столбцы с сервера",
	"Reload from server": "Обновить с сервера",
	"Reload naming rules": "Обновить правила нейминга",
	"Reload sidebar": "Обновить боковую панель",
	Remove: "Удалить",
	"Remove draft field {name}": "Убрать поле {name} из черновика",
	"Remove from canvas": "Убрать со схемы",
	"Remove from canvas?": "Убрать со схемы?",
	"Remove rule": "Удалить правило",
	"Remove staged field": "Убрать новое поле",
	"Remove the selection from the schema draft? Search Types, tables and data will be kept.": "Удалить выбранное из черновика схемы? Типы, таблицы и данные сохранятся.",
	"Remove the selection from this workflow draft?": "Удалить выбранные элементы из черновика workflow?",
	"Remove this element and its children?": "Удалить этот элемент вместе с дочерними?",
	"Remove this rule from the draft?": "Удалить правило из черновика?",
	"Remove this rule?": "Удалить правило?",
	"Required by TACTIC. This field cannot be deleted.": "Служебное поле TACTIC. Это поле нельзя удалить.",
	"Reset canvas view": "Сбросить вид схемы",
	"Reset color": "Сбросить цвет",
	"Resolve the native TACTIC view again": "Заново разрешить нативное представление TACTIC",
	"Resolved preview": "Предпросмотр итоговой компоновки",
	"Restore direct connection": "Вернуть прямую связь",
	"Restore row": "Восстановить строку",
	"Restrictions change which Search Objects are returned. They do not grant access.": "Ограничивают результаты поиска, но сами по себе не дают доступа.",
	Retired: "Архивные",
	Retry: "Повторить",
	"Reverse connection": "Развернуть связь",
	Row: "Строка",
	"Row {row}, column {column}": "Строка {row}, столбец {column}",
	"Rule details": "Параметры правила",
	"Rule project": "Проект правила",
	"Rules whose context starts with this process. Edit naming in the Search Type's existing Naming Editor.": "Правила, контекст которых начинается с имени этого процесса. Настроить нейминг можно в редакторе серч-тайпа.",
	"Run custom naming code? This uses the normal server environment, not an isolated sandbox. Scripts and classes can change data or files.": "Запустить пользовательский код нейминга? Он выполняется в обычной серверной среде, без изоляции. Скрипты и классы могут изменять данные и файлы.",
	SAVE: "СОХРАНИТЬ",
	"Same transaction": "В той же транзакции",
	"Sandbox directory naming": "Именование папки sandbox",
	Save: "Сохранить",
	"Save naming rule": "Сохранить правило нейминга",
	"Save process rules on the server? Global rules also affect same-name processes in other pipelines. Removed rules will be deleted; their scripts are kept. Actions and notifications are not executed by Save.": "Сохранить правила процесса на сервере? Общие правила затронут одноимённые процессы в других пайплайнах. Удалённые из списка правила будут удалены с сервера, но их скрипты сохранятся. Сохранение не запускает действия и не отправляет уведомления.",
	"Save process rules? Global rules affect matching processes in other pipelines. Removed rules are deleted; their scripts are kept. Actions are not executed by Save.": "Сохранить правила? Глобальные правила влияют на подходящие процессы других pipelines. Удалённые правила будут стёрты, их скрипты сохранятся. Действия при сохранении не запускаются.",
	"Save rules": "Сохранить правила",
	"Save sidebar changes before opening this search and its quick filters.": "Сначала сохраните изменения сайдбара, затем откройте поиск или его быстрые фильтры.",
	"Save the schema and create its new instance tables and missing key columns? Existing columns and values will be kept.": "Сохранить схему и создать новые таблицы связей и недостающие ключевые колонки? Существующие колонки и значения будут сохранены.",
	"Save to server": "Сохранить на сервер",
	"Saved definitions": "Сохранённые определения",
	"Saving configures the trigger. It does not run the action.": "Сохранение настраивает триггер, но не запускает действие.",
	"Saving creates the registry entry, database table and default views in the selected project.": "Сохранение создаёт запись реестра, таблицу базы данных и стандартные представления в выбранном проекте.",
	"Saving...": "Сохранение...",
	"Schema relationships": "Связи в схеме",
	"Schema relationships: %1": "Связей в схеме: %1",
	"Schema relationships: {count}": "Связей в схеме: {count}",
	"Schema: %1": "Схема: %1",
	"Schema: {name}": "Схема: {name}",
	Scope: "Область действия",
	"Script body": "Код скрипта",
	"Script language": "Язык скрипта",
	"Script path (optional)": "Путь скрипта (необязательно)",
	"Search Object or operation": "Серч-объект или операция",
	"Search Objects": "Серч-объекты",
	"Search Objects (including retired): %1": "Серч-объектов (включая retired): %1",
	"Search Objects without a workflow": "Серч-объекты без воркфлоу",
	"Search Type": "Серч-тайп",
	"Search Type identifier": "Идентификатор серч-тайпа",
	"Search Type image": "Превью серч-тайпа",
	"Search Type saved, but its preview could not be queued: {error}": "SearchType сохранён, но изображение не удалось отправить в очередь: {error}",
	"Search Type sections": "Разделы типа объектов",
	"Search Type: %1": "Серч-тайп: %1",
	"Search Types": "Серч-тайпы",
	"Search Types catalog": "Каталог типов объектов",
	"Search and quick filters": "Поиск и быстрые фильтры",
	"Search restrictions": "Ограничения поиска",
	"Select Search Type": "Выберите Search Type",
	"Select a Search Type or create one.": "Выберите тип объектов или создайте новый.",
	"Select a Search Type to edit its appearance and fields. Changes stay in your draft until you save.": "Выберите серч-тайп для настройки вида и полей. До сохранения изменения остаются в черновике.",
	"Select a Search Type to edit its properties and fields. Changes stay in your draft until you save.": "Выберите тип объектов для настройки свойств и полей. Правки остаются в черновике до сохранения.",
	"Select a connection to choose its relationship type and key columns. Many-to-many creates an instance node in the draft.": "Выберите соединение для настройки типа связи и ключевых столбцов. Many-to-many добавляет связующую ноду в черновик.",
	"Select a definition": "Выберите определение",
	"Select a node or a connection": "Выберите узел или связь",
	"Select a process on the canvas": "Выберите процесс на графе",
	"Select a project": "Выберите проект",
	"Select a project to edit layouts.": "Выбери проект для настройки компоновок.",
	"Select a rule": "Выберите правило",
	"Select a rule or create a new one.": "Выберите правило или создайте новое.",
	"Select a sidebar element first": "Сначала выберите элемент боковой панели",
	"Select an element or add a new widget.": "Выбери элемент или добавь новый виджет.",
	"Select an element to edit it. Groups hold other elements.": "Выбери элемент для настройки. Группы содержат другие элементы.",
	"Select an existing server script. Its source remains in the Script Editor.": "Выберите существующий серверный скрипт. Его код редактируется в редакторе скриптов.",
	"Select an item in the preview to edit it, or add a new link or section.": "Выберите элемент в предпросмотре или добавьте новую ссылку либо раздел.",
	"Select any rule to edit its native attributes, including custom scopes.": "Выберите правило для изменения атрибутов, в том числе пользовательской области.",
	"Select multiple nodes": "Выбрать несколько узлов",
	"Select multiple processes": "Выбрать несколько процессов",
	"Select the login groups allowed to see this sidebar item. The group preview uses these draft permissions immediately.": "Выберите группы, которым разрешено видеть этот пункт. Предпросмотр для группы сразу учитывает эти права из черновика.",
	"Selected document": "Выбранный документ",
	"Selected element": "Выбранный элемент",
	"Selected element XML": "XML выбранного элемента",
	Selection: "Выбранное",
	"Separate process, background": "Отдельный процесс, в фоне",
	"Separate process, blocking": "Отдельно, с ожиданием",
	"Separate process, non-blocking": "Отдельно, без ожидания",
	"Separate process, wait": "Отдельный процесс, с ожиданием",
	Separator: "Разделитель",
	"Server command class": "Класс серверной команды",
	"Server script": "Серверный скрипт",
	"Set actual task date": "Задать фактическую дату задачи",
	"Shared TACTIC login groups and their members": "Общие группы пользователей TACTIC и их участники",
	"Shared data outside the selected project": "Общие данные вне выбранного проекта",
	"Shared pipeline: read-only. Create a project-owned pipeline to make project-specific changes.": "Общий пайплайн: только чтение. Для настроек отдельного проекта создайте его собственный пайплайн.",
	"Shared · read-only": "Общий · только чтение",
	"Short text": "Короткий текст",
	"Show on canvas": "Показать на схеме",
	"Show properties": "Показать свойства",
	"Show workflow list": "Показать список воркфлоу",
	"Shown on the canvas without changing the process name.": "Название на схеме без изменения имени процесса.",
	"Sidebar Editor": "Редактор боковой панели",
	"Sidebar has unsaved changes": "В боковой панели есть несохранённые изменения",
	"Sidebar is up to date": "Боковая панель актуальна",
	"Sidebar items": "Пункты сайдбара",
	"Sidebar link": "Ссылка сайдбара",
	"Sidebar links": "Ссылки сайдбара",
	Signal: "Событие",
	"Some connections refer to missing processes. Add the processes or remove those connections before saving.": "Некоторые связи ссылаются на отсутствующие процессы. Добавьте процессы или удалите связи перед сохранением.",
	Source: "Исходник",
	"Source XML": "Исходный XML",
	"Standard fields": "Стандартные поля",
	"Start from a template or copy this view. Give your view a unique name.": "Выбери заготовку или скопируй текущий вид. Задай новому виду уникальное имя.",
	"Status behavior": "Поведение статуса",
	"Stored in the selected project": "Данные хранятся в выбранном проекте",
	"Subgroups, separated by |": "Подгруппы через |",
	Subject: "Тема",
	Submenu: "Подменю",
	Subpipeline: "Вложенный пайплайн",
	Summary: "Сводка",
	"Supervisor group": "Группа супервайзеров",
	"TACTIC creates these columns automatically when you save the new Search Type. Do not add them again below; the draft list is only for extra fields.": "TACTIC создаст эти столбцы автоматически при сохранении нового серч-тайпа. Повторно добавлять их ниже не нужно: список черновика предназначен только для дополнительных полей.",
	"TACTIC creates these fields automatically. Add only extra fields below.": "TACTIC создаёт эти поля автоматически. Ниже добавляйте только дополнительные поля.",
	"TACTIC expressions are supported in recipients, subject and body. Saving does not send a notification.": "В получателях, теме и тексте поддерживаются выражения TACTIC. При сохранении уведомление не отправляется.",
	"TACTIC identifiers and widget options. For normal setup, use Item.": "Идентификаторы TACTIC и параметры виджетов. Для обычной настройки используйте вкладку «Пункт».",
	"TACTIC sidebar": "Сайдбар TACTIC",
	"TACTIC will create the Search Type, its table and a schema node on the server. Other unsaved canvas changes remain in your draft; save the schema separately to apply them.": "TACTIC создаст серч-тайп, его таблицу и ноду схемы на сервере. Остальные изменения канваса останутся в черновике — для их применения сохраните схему отдельно.",
	"TACTIC-HANDLER  ·  ADMIN": "TACTIC-HANDLER  ·  АДМИНКА",
	"TH sidebar": "Сайдбар TH",
	Table: "Таблица",
	"Table %1.%2 is missing. This Search Type is still referenced by the schema. Check the table on the server or correct the connection, then reload columns. No table is created automatically.": "Таблица %1.%2 отсутствует, но схема всё ещё ссылается на этот серч-тайп. Проверьте таблицу на сервере или исправьте связь, затем обновите столбцы. Таблица не создаётся автоматически.",
	"Table views manager": "Менеджер табличных видов",
	"Manage table views…": "Управление видами…",
	"Find a table view": "Найти табличный вид",
	"The default table is protected. Create a copy to customize it.": "Стандартный вид защищён. Для своего варианта создайте копию.",
	"Project view. Renaming changes its label and keeps existing links.": "Вид проекта. При переименовании меняется подпись, ссылки сохраняются.",
	"Current view": "Текущий вид",
	"New table view": "Новый табличный вид",
	"Duplicate table view": "Копия табличного вида",
	"Rename table view": "Переименовать вид",
	"Delete table view": "Удалить вид",
	"Use this view": "Применить вид",
	"Delete this project view and its saved layers? Existing links to it may stop working.": "Удалить этот вид проекта и его сохранённые слои? Ссылки на него могут перестать работать.",
	Duplicate: "Создать копию",
	Rename: "Переименовать",
	"Save or discard column changes before managing views.": "Перед управлением видами сохраните или отмените изменения колонок.",
	"Horizontal scrolling": "Горизонтальная прокрутка",
	"Table views and columns": "Варианты таблицы и колонки",
	Target: "Объект",
	"Target status": "Целевой статус",
	"Task assignee changed": "Изменён исполнитель задачи",
	"Task settings": "Настройки задач",
	"Task status changed": "Изменён статус задачи",
	"Task status workflow": "Воркфлоу статусов задач",
	"Task status workflows": "Статусы задач",
	"Task statuses": "Статусы задач",
	"Technical settings": "Технические настройки",
	"The built-in system schema is read-only": "Встроенная системная схема доступна только для чтения",
	"The change is staged until Save. Processes used by tasks, snapshots or triggers cannot be removed on the server.": "Изменение применится после сохранения. Нельзя удалить процесс, который используется задачами, снапшотами или триггерами.",
	"The code is stored with this process. Applying the draft does not run it.": "Код сохраняется с процессом. Применение черновика не запускает скрипт.",
	"The color of the entire pipeline, independent of its process colors.": "Цвет всего пайплайна, независимо от цветов отдельных процессов.",
	"The database table for {type} is absent. No table is created by reading columns.": "Таблица базы данных для {type} отсутствует. Чтение списка колонок не создаёт таблицу.",
	"The database table is missing. Check the server schema before editing.": "Таблица базы данных отсутствует. Проверьте схему сервера перед редактированием.",
	"The image belongs to the Search Type itself, not to one of its Search Objects. Saving adds the replacement to Commit Queue.": "Изображение относится к самому серч-тайпу, а не к одному из его объектов. При сохранении новое превью добавится в очередь отправки.",
	"The image belongs to the Search Type itself. Saving sends the replacement through Commit Queue.": "Изображение относится к самому SearchType. При сохранении замена отправляется через очередь сдачи файлов.",
	"The installed Python command that handles this action.": "Установленная на сервере Python-команда, которая выполняет это действие.",
	"The language used by the native server handler.": "Язык, который использует серверный обработчик TACTIC.",
	"The layout editor could not be loaded. Connect to TACTIC Stream and try again.": "Не удалось загрузить редактор. Подключись к TACTIC Stream и повтори попытку.",
	"The native document for this canvas. Unknown elements and attributes are preserved.": "Документ графа в формате TACTIC. Дополнительные элементы и атрибуты сохраняются.",
	"The native workflow signal sent to the related process.": "Событие воркфлоу TACTIC, отправляемое в связанный процесс.",
	"The pipeline name shown to other users.": "Название пайплайна, которое видят другие пользователи.",
	"The process to signal or listen to; leave empty to use the native default.": "Процесс для отправки или отслеживания событий. Пустое значение использует правило TACTIC по умолчанию.",
	"The related objects affected by this node.": "Тип связанных объектов, с которыми работает нода.",
	"The rule will be removed from the server when you save. The script itself is not deleted.": "Правило удалится с сервера после сохранения. Сам скрипт удалён не будет.",
	"The saved search defines the starting query. Quick filters refine it in the same search tab and use this item’s own defaults.": "Сохранённый поиск задаёт исходный запрос. Быстрые фильтры уточняют его в той же вкладке и используют настройки этого пункта.",
	"The selected nodes and their connections will be removed from the canvas when you save. Server data is not deleted.": "При сохранении выделенные ноды и их связи будут убраны с канваса. Серверные данные не удаляются.",
	"The selected preview will be added through Commit Queue after creation.": "После создания выбранное превью будет добавлено через очередь отправки.",
	"The shared Search Type registration is kept for other projects, as in TACTIC.": "Общая регистрация серч-тайпа сохранится для других проектов, как в TACTIC.",
	"The shared Search Type registration is retained for other projects.": "Общая регистрация SearchType сохраняется для других проектов.",
	"These changes will be saved on the server and will affect other users of the project.": "Изменения сохранятся на сервере и затронут других пользователей проекта.",
	"These fields exist only in your draft. Save creates them; removing a draft field does not change the database.": "Эти поля существуют только в черновике. Сохранение создаст их; удаление поля из черновика не меняет базу.",
	"These fields exist only in your draft. Save to server creates them; removing a draft field does not change the database.": "Эти поля пока только в черновике. Они появятся в базе после сохранения на сервер. Удаление поля из черновика не меняет базу.",
	"These native group settings participate in every access check, together with explicit rules and other memberships.": "TACTIC учитывает эти параметры при каждой проверке доступа, вместе с правилами и участием в других группах.",
	"These pipelines are linked to this Search Type on the server. Open one to edit its processes, task settings, groups, dependencies and scripts.": "Эти пайплайны связаны с серч-тайпом на сервере. Откройте нужный, чтобы настроить процессы, параметры задач, группы, зависимости и скрипты.",
	"These settings belong to the whole pipeline. Select a node on the canvas to configure its process and task statuses.": "Эти настройки относятся ко всему пайплайну. Выберите ноду на холсте для настройки процесса и статусов задач.",
	"These settings belong to the whole pipeline. Select a node on the canvas to configure that process and its task statuses.": "Настройки всего пайплайна. Выберите ноду на канвасе, чтобы настроить процесс и статусы его задач.",
	"This Search Type has no pipeline_code field. A pipeline association alone does not add it.": "У серч-тайпа нет поля pipeline_code. Привязка пайплайна сама по себе его не создаёт.",
	"This Search Type is in use. Remove its objects and dependencies before deleting it.": "SearchType используется. Перед удалением удалите его объекты и зависимости.",
	"This Search Type is registered, but its database table (%1.%2) is absent. Fields and Search Objects cannot be loaded. Editing is disabled; no table will be created automatically.": "Этот серч-тайп зарегистрирован, но его таблица в базе (%1.%2) отсутствует. Поля и серч-объекты загрузить нельзя. Редактирование отключено; таблица не будет создана автоматически.",
	"This count is for the pipeline, not the number of tasks in this process.": "Показаны объекты пайплайна, а не количество задач этого процесса.",
	"This deletes the empty table, empty pipelines and the node with its connections in this project. This editor cannot undo the deletion. Check scripts, naming rules and saved searches that refer to this type.": "Будут удалены пустая таблица, пустые пайплайны и нода с её связями в этом проекте. Отменить удаление в редакторе нельзя. Проверьте скрипты, правила нейминга и сохранённые поиски, ссылающиеся на этот тип.",
	"This draft is not selected for these parameters by native naming lookup.": "Штатный поиск нейминга не выбирает этот черновик при заданных параметрах.",
	"This endpoint is inherited or implicit. Add the registered Search Type to this canvas to position it locally.": "Этот узел унаследован или задан неявно. Добавьте зарегистрированный тип на схему, чтобы задать его положение в этом проекте.",
	"This group has no sidebar items": "Для этой группы в сайдбаре нет пунктов",
	"This is a draft. The instance table and its key columns will be created only when you save the schema.": "Это черновик. Связующая таблица и её ключевые столбцы появятся на сервере только после сохранения схемы.",
	"This is a link table for a many-to-many relationship, not a separate object category.": "Это связующая таблица для связи «многие ко многим», а не отдельная категория объектов.",
	"This is how the new Search Type will appear. Nothing has been created on the server yet.": "Так будет выглядеть новый серч-тайп. На сервере пока ничего не создано.",
	"This pipeline": "Этот пайплайн",
	"This process": "Этот процесс",
	"This process is referenced by a connection but is missing from the pipeline.": "Связь ссылается на процесс, которого нет в pipeline.",
	"This sidebar has no items": "В боковой панели нет элементов",
	"This trigger is generated by the workflow engine. Edit its action or progress listener in the node parameters, not in a second copy here.": "Этот триггер создан движком воркфлоу. Его действие или отслеживание прогресса настраивается в параметрах ноды — здесь показана та же запись, а не отдельная копия.",
	"This type has no pipeline_code field. Add it in Fields to assign workflows to its objects.": "У типа нет поля pipeline_code. Добавьте его в «Поля», чтобы назначать workflow объектам.",
	"This type is referenced by a connection. Add its registered node to the canvas to move it.": "На этот тип ссылается связь. Добавьте зарегистрированный узел на схему, чтобы перемещать его.",
	Title: "Заголовок",
	"To (parent)": "К (родительский)",
	"Today, 14:30": "Сегодня, 14:30",
	"Totals include retired Search Objects. Shared system types are counted in their own database. Reload to update the summary.": "В подсчёт входят архивные серч-объекты. Общие системные типы считаются в своей базе данных. Обновите данные, чтобы актуализировать сводку.",
	"Trigger execution mode": "Режим выполнения триггера",
	Triggers: "Триггеры",
	"Triggers, notifications, naming conventions and objects using this pipeline. Save node changes before editing dependencies.": "Триггеры, уведомления, нейминг и объекты пайплайна. Перед настройкой зависимостей сохраните изменения ноды.",
	"Types stored in the selected project's database, regardless of their namespace. Turn off to include shared system types.": "Серч-тайпы, данные которых хранятся в базе выбранного проекта, независимо от префикса. Снимите галочку, чтобы видеть и общие системные типы.",
	"Undo field deletion": "Отменить удаление поля",
	"Unsaved changes": "Несохранённые изменения",
	Unspecified: "Не указано",
	"Up to %1 characters": "До %1 символов",
	"Up to {count} characters": "До {count} символов",
	"Update project naming rule? This changes future check-ins in the current project. Existing files are kept.": "Обновить правило нейминга проекта? Изменится нейминг будущих сдач файлов в этом проекте. Существующие файлы сохраняются.",
	"Use Create workflow above. The new pipeline will already be linked to this Search Type.": "Нажмите «Создать воркфлоу» выше. В новом пайплайне уже будет выбран этот серч-тайп.",
	"Use Source XML or create a view from a layout template.": "Используйте исходный XML или создайте вид из заготовки.",
	"Use TACTIC default": "По умолчанию в TACTIC",
	"Use a script or an installed server command class.": "Используйте скрипт или класс команды, установленной на сервере.",
	"Use an existing server script, or provide a script body below.": "Укажите существующий серверный скрипт или введите его код ниже.",
	"Use inherited rule": "Наследовать правило",
	"Use the execution mode supported by the installed server handler.": "Укажите режим выполнения, который поддерживает установленный серверный обработчик.",
	"Use the native event template on save": "При сохранении взять шаблон события из TACTIC",
	"Use these settings for shared item styles, nested widgets or direct XML editing.": "Здесь настраиваются стили исходного item, вложенные виджеты и XML.",
	"Used by a schema relationship. Change the relationship before deleting this field.": "Поле используется в связи схемы. Сначала измените связь, затем удаляйте поле.",
	"Used for this process on the canvas and in task views.": "Цвет процесса на схеме и в списках задач.",
	"Used in lists and the project schema. Reset to use the theme color.": "Цвет в списках и на схеме проекта. Сброс возвращает цвет темы.",
	"Used when no status mapping is selected.": "Используется, если соответствие статусу не выбрано.",
	"User directory": "Все пользователи",
	Users: "Пользователи",
	Value: "Значение",
	Version: "Версия",
	Versionless: "Без номера версии",
	"View root": "Корень вида",
	"Visible in navigation": "Показывать в навигации",
	"Wait for a completion signal instead of completing this node immediately.": "Дождаться события завершения, а не завершать ноду сразу.",
	"Wait for completion": "Ожидать завершения",
	"Wheel: zoom · Middle-button drag: pan": "Колесо — масштаб · Зажатая средняя кнопка — панорама",
	"Wheel: zoom. Middle-button drag: pan. Shift/Ctrl-click or drag a frame to select nodes.": "Колесо — масштаб. Зажатая средняя кнопка — панорама. Shift/Ctrl-клик или рамка — выделение нод.",
	"Who can see this item": "Кому доступен пункт",
	"Whole number": "Целое число",
	Width: "Ширина",
	Workflow: "Воркфлоу",
	"Workflow catalog tools": "Инструменты списка воркфлоу",
	"Workflow editor": "Редактор воркфлоу",
	Workflows: "Рабочие процессы",
	"Working on the server…": "Выполняется на сервере…",
	XML: "XML",
	"Yes / No": "Да / Нет",
	"You can choose an image now. After the Search Type is created, its preview will be sent through Commit Queue.": "Можно выбрать картинку сразу. После создания серч-тайпа превью загрузится через очередь отправки.",
	"Zoom in": "Увеличить",
	"Zoom level": "Масштаб",
	"Zoom out": "Уменьшить",
	"pipeline_code will also be created: pipeline support is enabled.": "Также будет создано поле pipeline_code: поддержка пайплайна включена.",
	"pipeline_code will not be created: pipeline support is disabled.": "Поле pipeline_code не будет создано: поддержка пайплайна выключена.",
	"{count} processes": "Процессов: {count}",
	"Enter a valid value for the column type.": "Введите допустимое значение для типа колонки.",
	"Access rules saved on server": "Правила доступа сохранены на сервере",
	"No rules match the search": "Подходящих правил нет",
	"Select a rule to edit": "Выберите правило",
	"Find a target": "Найти объект",
	"Selected rule JSON": "Атрибуты правила JSON",
	"Inherited rules": "Наследуемые правила",
	"Discard text": "Сбросить текст",
	Subgroups: "Подгруппы",
	"The save result is unknown. Reload access rules before trying again.": "Результат сохранения неизвестен. Загрузите правила доступа заново перед повторной попыткой.",
	"Changes apply to the draft. Save to server to publish them.": "Изменения остаются в черновике. Сохраните на сервер, чтобы применить их.",
	"Value mode": "Режим значения",
	"Database default": "Значение БД по умолчанию",
	"Cell value": "Значение ячейки",
	"Delete item": "Удалить элемент",
	"Sidebar Editor help": "Справка редактора сайдбара",
	"Sidebar preview width": "Ширина предпросмотра сайдбара",
	"Preview group": "Предпросмотр для группы",
	"Move up": "Переместить вверх",
	"Move down": "Переместить вниз",
	"Apply XML": "Применить XML",
	"Item type": "Тип элемента",
	"A link opens a search, a section groups links, and a separator divides the list.": "Ссылка открывает поиск, раздел объединяет ссылки, разделитель отделяет пункты списка.",
	"Internal name": "Внутреннее имя",
	"The stable identifier for this sidebar item and its quick-filter defaults. Change the title for a visual rename.": "Постоянный идентификатор пункта и его быстрых фильтров. Для изменения видимой подписи меняйте заголовок.",
	"Child view": "Дочерний вид",
	"The SideBarWdg view containing this section's links.": "Представление SideBarWdg, в котором хранятся ссылки раздела.",
	"Icon name": "Имя иконки",
	"The server icon identifier. You can also choose an icon on the Item page.": "Идентификатор иконки на сервере. Выбрать иконку из библиотеки можно на странице «Пункт».",
	"Widget Type": "Тип виджета",
	"The TACTIC web widget used by this link.": "Веб-виджет TACTIC, используемый этой ссылкой.",
	"Class Path": "Путь к классу",
	"The Python class registered for this TACTIC widget.": "Класс Python, зарегистрированный для этого виджета TACTIC.",
	"The server view used to render the selected TACTIC widget.": "Представление сервера для отображения выбранного виджета TACTIC.",
	"A short, recognizable name in the sidebar.": "Короткое и понятное название в сайдбаре.",
	"Click the icon to choose from the searchable library.": "Нажмите на иконку, чтобы выбрать другую. В библиотеке есть поиск.",
	"Hide this item without deleting its settings.": "Скрыть пункт, не удаляя его настройки.",
	"The saved search defines the starting query. Quick filters refine it in the same search tab and use this item's own defaults.": "Преднастроенный поиск задаёт исходный запрос. Быстрые фильтры уточняют его в той же вкладке и используют отдельные настройки этого пункта.",
	"Which project objects this item opens.": "Какие объекты проекта открывает этот пункт.",
	"Predefined search": "Преднастроенный поиск",
	"Choose a saved query or leave the list unfiltered.": "Выберите сохранённый запрос или оставьте список без фильтрации.",
	"No predefined search": "Без преднастроенного поиска",
	"Configure search": "Настроить поиск",
	"Default item view": "Представление элементов по умолчанию",
	"The initial presentation when this search tab is opened.": "В каком виде показывать объекты при открытии вкладки.",
	"Workspace layout": "Компоновка рабочего пространства",
	"Apply a saved dock arrangement when this sidebar item opens.": "Применять сохранённое расположение доков при открытии этого пункта сайдбара.",
	"Do not change workspace layout": "Не менять компоновку рабочего пространства",
	"Script shelf": "Шелф скриптов",
	"Show this shared shelf when the sidebar tab is active.": "Показывать этот общий шелф, когда активен данный таб сайдбара.",
	"Project default shelf": "Общий шелф проекта",
	"Collapse section": "Свернуть раздел",
	"Expand section": "Развернуть раздел",
	"Saved definitions panel width": "Ширина списка определений",
	"Definition XML": "XML определения",
	"Columns list height": "Высота списка колонок",
	"Native field identifier.": "Нативный идентификатор поля.",
	"The column heading shown to users.": "Заголовок колонки, который видят пользователи.",
	"Show in table": "Показывать в таблице",
	"Keep the column in this saved view.": "Оставить колонку в этом сохранённом представлении.",
	"Default width in the table view.": "Ширина по умолчанию в табличном представлении.",
	"Display widget": "Виджет отображения",
	"Choose a supported TACTIC table widget.": "Выберите поддерживаемый табличный виджет TACTIC.",
	"This TACTIC view has no columns. Add elements in XML mode.": "В этом представлении TACTIC нет колонок. Добавьте элементы в режиме XML.",
	"This definition does not use a native TACTIC table layout. Open XML to edit its exact structure.": "Это определение не использует нативную табличную компоновку TACTIC. Откройте XML для редактирования точной структуры.",
	"Open XML": "Открыть XML",
	"Server error": "Ошибка сервера",
	"Discard unsaved sidebar changes?": "Отменить несохранённые изменения бокового меню?",
	"Columns list width": "Ширина списка колонок",
	"*": "*",
	"1. Details": "1. Параметры",
	"2. Fields": "2. Поля",
	"3. Ready": "3. Подтверждение",
	"A column with this name already exists": "Поле с таким именем уже существует",
	"A login is required": "Укажите логин",
	"A native TACTIC expression evaluated on the object and snapshot.": "Штатное выражение TACTIC, вычисляемое для объекта и снимка.",
	"A technical name: lowercase Latin letters, numbers and underscores. No spaces; start with a letter.": "Техническое имя: строчные латинские буквы, цифры и подчёркивания. Без пробелов; начинается с буквы.",
	"A user with this login already exists": "Пользователь с таким логином уже существует",
	Access: "Доступ",
	Account: "Аккаунт",
	"Add field": "Добавить поле",
	Address: "Адрес",
	"An existing login cannot be changed": "Логин существующего аккаунта нельзя изменить",
	Auto: "Авто",
	"Base directory alias": "Псевдоним базовой папки",
	Button: "Кнопка",
	Changes: "Изменения",
	"Check the people who belong to this group": "Отметьте участников этой группы",
	"Check-in type": "Тип Check-in",
	"Choose image": "Выбрать изображение",
	"Class name": "Имя класса",
	"Column names must be unique lowercase SQL identifiers": "Имена полей должны быть уникальными SQL-идентификаторами в нижнем регистре.",
	Condition: "Условие",
	"Confirm save": "Подтвердить сохранение",
	"Create user": "Создать пользователя",
	"Current versionless": "Текущий versionless",
	"Decrease width": "Уменьшить ширину",
	"Default group": "Группа по умолчанию",
	Department: "Отдел",
	"Discard unsaved group changes?": "Отменить несохранённые изменения группы?",
	"Discard unsaved user changes?": "Отменить несохранённые изменения пользователя?",
	"Display name": "Отображаемое имя",
	"Edit group membership": "Изменить группы",
	Email: "Электронная почта",
	"Empty matches any snapshot type.": "Пустое поле соответствует любому типу снимка.",
	"Enter a Search Type title": "Введите название типа объектов.",
	"Enter a group identifier": "Введите идентификатор группы",
	"Enter a login without spaces or slashes": "Введите логин без пробелов и слешей",
	"Evaluate naming": "Проверить нейминг",
	"Evaluate with custom code": "Проверить с пользовательским кодом",
	"Example file": "Пример файла",
	"Existing server script overriding directory and file naming.": "Существующий серверный скрипт, заменяющий нейминг каталога и файла.",
	"First name": "Имя",
	Grid: "Сетка",
	"Group details": "Параметры группы",
	"Group details changed. Reload before saving.": "Настройки группы изменились. Обновите данные перед сохранением.",
	"Group identifier": "Идентификатор группы",
	"Group membership changes affect this user's permissions.": "Изменение групп влияет на права пользователя.",
	"Group saved on server": "Группа сохранена на сервере",
	Heading: "Заголовок",
	"Hourly wage": "Ставка в час",
	"Hourly wage must be a non-negative number": "Почасовая ставка должна быть неотрицательным числом",
	Icon: "Иконка",
	"Increase width": "Увеличить ширину",
	"Ingest rule code": "Код правила импорта",
	"Input — connect here": "Вход — подключить сюда",
	"Installed naming class implementing get_dir and get_file.": "Установленный класс нейминга с методами get_dir и get_file.",
	"Invalid account status": "Некорректный статус учётной записи",
	"Invalid password or user groups": "Некорректный пароль или список групп",
	"Invalid user document": "Некорректные данные пользователя",
	"Invalid user profile field": "Некорректное поле профиля пользователя",
	Item: "Пункт",
	Label: "Подпись",
	"Last name": "Фамилия",
	"Latest versionless": "Последний versionless",
	"Leave empty to keep the current password": "Оставьте пустым, чтобы сохранить текущий пароль",
	"License type": "Тип лицензии",
	Link: "Ссылка",
	"Local rule simulation": "Локальный предпросмотр",
	Login: "Логин",
	"Manual version": "Версия вручную",
	Members: "Участники",
	"Members: {count}": "Участников: {count}",
	"Membership changes apply on the server. Sidebar visibility rules are configured separately for each sidebar item.": "Состав групп сохраняется на сервере. Права видимости настраиваются отдельно для каждого пункта сайдбара.",
	"Missing process": "Процесс отсутствует",
	NULL: "NULL",
	"Name, login or email": "Имя, логин или почта",
	Namespace: "Пространство имён",
	"Naming rule": "Правило нейминга",
	"New group": "Новая группа",
	"New user": "Новый пользователь",
	"New · many-to-many": "Новый · многие ко многим",
	"No pipeline": "Без пайплайна",
	"No user groups yet": "Групп пользователей пока нет",
	"No users match the search": "Пользователи не найдены",
	Number: "Номер",
	"Open Commit Queue": "Открыть очередь сдачи файлов",
	"Optional ingest rule associated with this naming rule.": "Необязательное правило импорта, связанное с правилом нейминга.",
	"Output — connect here": "Выход — соединить здесь",
	Password: "Пароль",
	"Phone number": "Номер телефона",
	Preview: "Превью",
	"Preview context": "Контекст превью",
	Profile: "Профиль",
	"Project code": "Код проекта",
	"Project: {project}": "Проект: {project}",
	"Repository alias used by native check-in.": "Алиас репозитория для штатной сдачи файлов.",
	"Retired user": "Архивный · retired",
	"Retiring keeps this user's history. Clear this option to reactivate the account, then save.": "При переносе в архив история пользователя сохраняется. Снимите отметку и сохраните, чтобы вернуть учётную запись из архива.",
	"Rule context (empty means any)": "Контекст правила (пусто — любой)",
	"Sandbox directory alias": "Псевдоним папки sandbox",
	"Sandbox repository alias used by native check-in.": "Алиас рабочего репозитория для штатной сдачи файлов.",
	"Save or discard user changes before leaving.": "Сохраните или отмените изменения пользователя перед выходом.",
	"Script path": "Путь скрипта",
	Scroll: "Прокрутка",
	"Search Object": "Объект",
	"Search users": "Поиск пользователей",
	Section: "Раздел",
	"Select a group or create a new one": "Выберите группу или создайте новую",
	"Select a user or create a new account": "Выберите пользователя или создайте учётную запись",
	"Show retired users": "Показывать retired",
	Simple: "Простой",
	"Snapshot type": "Тип снапшота",
	Status: "Статус",
	Strict: "Строгий",
	TACTIC: "TACTIC",
	TH: "ТХ",
	Technical: "Технические",
	"The identifier is used in access rules and cannot be changed after creation.": "Идентификатор используется в правилах доступа. После создания изменить его нельзя.",
	"The sandbox path expression; empty uses Directory naming.": "Выражение рабочего пути. Пустое поле использует нейминг каталога.",
	"The save result is unknown. Reload groups before trying again.": "Результат сохранения неизвестен. Обновите группы перед повторной попыткой.",
	"The save result is unknown. Reload users before trying again.": "Результат сохранения неизвестен. Перезагрузите пользователей перед повторной попыткой.",
	"The selected user group no longer exists. Refresh the list.": "Выбранная группа больше не существует. Обновите список.",
	"The selected user no longer exists. Refresh the list.": "Выбранный пользователь больше не существует. Обновите список.",
	"These details are shown in profiles, messages and user pickers.": "Эти данные видны в профиле, сообщениях и списках выбора пользователей.",
	UPN: "UPN",
	"Unique identifier": "Уникальный идентификатор",
	"Unique login, without spaces": "Уникальный логин без пробелов",
	"Unsupported column type": "Неподдерживаемый тип поля.",
	"Use a color in #RRGGBB format or leave it empty": "Введите цвет в формате #RRGGBB или оставьте пустым.",
	"Use a context or a native wildcard such as publish/*.": "Укажите контекст или штатный шаблон, например publish/*.",
	"User details or memberships changed. Reload before saving.": "Данные пользователя или членство в группах изменились. Перезагрузите их перед сохранением.",
	"User saved on server": "Пользователь сохранён на сервере",
	View: "Вид",
	"What is this group responsible for?": "За что отвечает эта группа?",
	Wizard: "Мастер",
	"You cannot remove your own administrator membership": "Нельзя удалить собственное членство в группе администраторов",
	"You cannot retire the account you are signed in with": "Нельзя отключить учётную запись, под которой вы вошли",
	builtin: "встроенная функция",
	center: "во вкладки",
	code: "code",
	column: "Столбец",
	columns: "Столбцы контейнера",
	create: "Создать объект",
	delete: "Удалён",
	description: "Описание",
	error: "Failed",
	file: "Файл",
	group: "Группа",
	height: "Высота картинки",
	icon: "Иконка",
	image: "Картинка",
	left: "слева",
	link: "Ссылка",
	preview: "Предпросмотр",
	process: "Процесс",
	ready: "Готов к публикации",
	rows: "Высота в строках",
	selected: "выбрано",
	table: "Таблица",
	tasks: "задачи",
	text: "Текст",
	title: "Заголовок",
	value: "значение",
	view: "Вложенный вид",
	"Search Types panel width": "Ширина панели типов объектов",
	"Naming rules panel width": "Ширина списка правил именования",
	"Discard unsaved Search Type changes?": "Отменить несохранённые изменения типа объектов?",
	"Existing files already use this path:": "Этот путь уже используется файлами:",
	"Version must be between 1 and 9999": "Версия должна быть от 1 до 9999",
	"Undo image change": "Отменить выбор изображения",
	"Center selection": "Центрировать выделение",
	"Drag: move · Ctrl/Shift: select · F: center": "Перенос: мышью · Ctrl/Shift: выделение · F: центрировать",
	"Create Search Type": "Создать тип объектов",
	"Existing files": "Существующие файлы",
	"Select a Search Type": "Выберите тип объектов",
	"Undo deletion": "Отменить удаление",
	"Wheel: zoom · Middle button: pan": "Колесо: масштаб · Средняя кнопка: перемещение",
	"Naming sections": "Разделы нейминга",
	"New rule is local until Save is pressed.": "Новое правило останется локальным до сохранения.",
	"Close administration": "Закрыть администрирование",
	"Administration project": "Проект администрирования",
	"Administration section": "Раздел администрирования",
	"Administration sections": "Разделы администрирования",
	"TACTIC · ADMIN": "TACTIC · ADMIN",
	"Duplicated rule is local until Save is pressed.": "Копия правила останется локальной до сохранения.",
	Design: "Конструктор",
	Configuration: "Конфигурация",
	"Current state": "Текущее состояние",
	"Blank view": "Пустое представление",
	Cards: "Карточки",
	"Cards example": "Пример карточек",
	"Table example": "Пример таблицы",
	"Tree example": "Пример дерева",
	"Continuous Tree": "Непрерывное дерево",
	"Table View": "Табличный вид",
	"Copy current view": "Копия текущего представления",
	"Check and preview": "Проверить и показать",
	"Check and preview the draft before saving.": "Перед сохранением проверьте черновик и посмотрите результат.",
	"Column tracks": "Размеры колонок",
	"Container layout": "Компоновка контейнера",
	Container: "Контейнер",
	"Child layout": "Компоновка дочерних элементов",
	"Element settings": "Параметры элемента",
	"Element settings width": "Ширина панели параметров",
	"Elements panel width": "Ширина списка элементов",
	"Fixed text": "Заданный текст",
	"Layout guide": "Справка по компоновке",
	"Layout template": "Шаблон компоновки",
	List: "Список",
	"Move element earlier": "Переместить элемент раньше",
	"Move element later": "Переместить элемент позже",
	"Optional sizes such as 128px 1fr auto": "Необязательные размеры, например 128px 1fr auto",
	"Preview item type": "Тип элемента для предпросмотра",
	"Remove element": "Удалить элемент",
	"Reusable view": "Переиспользуемое представление",
	"Shared item layout": "Общая компоновка элемента",
	"View name": "Имя представления",
	Visible: "Видимый",
	Widget: "Виджет",
	Alignment: "Выравнивание",
	"All items": "Все элементы",
	"Badge binding": "Источник счётчика",
	"Branch summary": "Сводка ветки",
	Center: "По центру",
	"Child object": "Дочерний объект",
	"Choose a number to show on the button": "Выберите числовое значение для счётчика на кнопке",
	"Choose which object value to display": "Выберите значение объекта для отображения",
	"Code editor help": "Справка по редактору кода",
	"Column span": "Колонок по ширине",
	"Create related object": "Создать связанный объект",
	"Custom data binding": "Произвольная привязка данных",
	"Data binding": "Источник данных",
	"Display conditions": "Условия отображения",
	"Edit history": "История изменений",
	End: "В конце",
	"Extra large": "Очень крупный",
	"File Offline": "Файл недоступен локально",
	"File preview": "Предпросмотр файла",
	"File size": "Размер файла",
	"Fill the cell": "Заполнить ячейку",
	"Fill the image area": "Заполнить область изображения",
	"Grid columns": "Колонок в сетке",
	"Higher layers appear in front. Use the same grid cells to place text or buttons over an image.": "Более высокие слои отображаются поверх остальных. Совместите ячейки сетки, чтобы разместить текст или кнопки поверх изображения.",
	"Image URL": "Адрес изображения",
	"Image fit": "Размещение изображения",
	"Image height": "Высота изображения",
	"Invalid configuration XML": "Некорректный XML конфигурации",
	"Invalid layout size": "Некорректный размер компоновки",
	"Invalid or cyclic layout container": "Некорректная или циклическая вложенность контейнеров",
	"Invalid or duplicate layout element name": "Некорректное или повторяющееся имя элемента",
	"Item actions": "Действия с элементом",
	"Item variant": "Вариант элемента",
	"Knowledge Base": "База знаний",
	Large: "Крупный",
	Layer: "Слой",
	"Layout supports at most 128 elements": "Компоновка поддерживает не более 128 элементов",
	"Limit the element to desktop, mobile or particular items": "Ограничьте отображение настольным, мобильным режимом или отдельными элементами",
	"Link URL": "Адрес ссылки",
	"Link URL binding": "Источник адреса ссылки",
	"Main object": "Основной объект",
	"Markup tag": "Тег разметки",
	Medium: "Средний",
	Metadata: "Метаданные",
	"Move left": "Переместить влево",
	"Move right": "Переместить вправо",
	Muted: "Приглушённый",
	"No badge": "Без счётчика",
	Normal: "Обычный",
	"Number of children": "Число дочерних элементов",
	"Number of notes": "Число заметок",
	"Object actions": "Действия с объектом",
	"Object description": "Описание объекта",
	"Object preview": "Превью объекта",
	"Object title": "Название объекта",
	"Open view": "Открыть представление",
	"Open view in browser": "Открыть представление в браузере",
	Relation: "Связь",
	"Relationship actions": "Действия со связями",
	"Row span": "Строк по высоте",
	"Show the whole image": "Показать изображение целиком",
	Small: "Мелкий",
	"Snapshot actions": "Действия со снапшотом",
	"Snapshot author": "Автор снапшота",
	"Snapshot details": "Сведения о снапшоте",
	"Snapshot summary": "Сводка снапшота",
	"Snapshot version": "Версия снапшота",
	Start: "В начале",
	Strong: "Выделенный",
	"Style role": "Роль оформления",
	"Text size": "Размер текста",
	"Text style": "Оформление текста",
	Versions: "Версии",
	Copy: "Копировать",
	Cut: "Вырезать",
	Paste: "Вставить",
	Find: "Найти",
	Replace: "Заменить",
	Undo: "Отменить",
	Redo: "Повторить",
	"Add files": "Добавить файлы",
	File: "Файл",
	Image: "Изображение",
	Text: "Текст",
	Tasks: "Задачи",
	Notes: "Заметки",
	Kind: "Вид",
	Snapshot: "Снапшот",
	"Alphabetical grid": "Сетка по алфавиту",
	Canvas: "Полотно",
	"Choose a column": "Выберите колонку",
	"Command class": "Класс команды",
	"Connections refer to missing processes": "Связи ссылаются на отсутствующие процессы",
	"Destination key column": "Ключевая колонка назначения",
	"Directed flow": "Направленный граф",
	"Enter a unique node name": "Введите уникальное имя узла",
	"Enter the Search Type identifier to confirm": "Для подтверждения введите идентификатор типа",
	"Existing columns": "Существующие колонки",
	"Find a workflow": "Найти рабочий процесс",
	"Horizontal position": "Положение по горизонтали",
	"Layout container depth exceeds 8": "Глубина вложенности контейнеров превышает 8",
	"Many-to-many creates a separate instance Search Type with two key connections.": "Для связи многие-ко-многим создаётся отдельный тип экземпляров с двумя ключевыми связями.",
	"Missing processes": "Отсутствующие процессы",
	"Move this node without dragging.": "Измените положение узла без перетаскивания.",
	"Native connection attributes.": "Нативные атрибуты связи.",
	"Network clusters": "Сетевые кластеры",
	"New workflow": "Новый рабочий процесс",
	"Node name": "Имя узла",
	"Optional native path used to distinguish multiple relationships.": "Необязательный нативный путь для различения нескольких связей.",
	Parameters: "Параметры",
	Pending: "Ожидает обработки",
	Properties: "Свойства",
	"Properties panel width": "Ширина панели свойств",
	"Relationship path": "Путь связи",
	"Review again": "Проверить снова",
	"Rule list width": "Ширина списка правил",
	Script: "Скрипт",
	"Select a workflow or create a new one.": "Выберите рабочий процесс или создайте новый.",
	"Source key column": "Исходная ключевая колонка",
	"Vertical position": "Положение по вертикали",
	"Workflow list width": "Ширина списка рабочих процессов",
	"Connection, sign-in status and server presets": "Подключение, состояние входа и серверные пресеты",
	Repositories: "Репозитории",
	"Repository locations, availability and default storage": "Расположения репозиториев, доступность и хранилище по умолчанию",
	"Active project and workspace context": "Активный проект и контекст рабочего пространства",
	"Check-in Options": "Параметры Check-in",
	"Naming and file handling defaults": "Настройки именования и работы с файлами",
	Global: "Общие",
	"Application behavior and diagnostics": "Поведение приложения и диагностика",
	"Themes, animations, language and rendering": "Темы, анимации, язык и рендеринг",
	Cache: "Кэш",
	"Persistent server data and cache policy": "Локальные серверные данные и правила кэширования",
	"Task Browser layout and Notes inspector defaults": "Настройки Task Browser и инспектора заметок",
	Preferences: "Настройки",
	"Configuration sections": "Разделы конфигурации",
	Reset: "Сбросить",
	"Configuration help": "Помощь по настройкам",
	Repository: "Репозиторий",
	"Paths are stored in the active server preset": "Пути хранятся в активном пресете сервера",
	"Paths are stored in the server configuration": "Пути сохраняются в конфигурации сервера",
	"Server repository path": "Серверный путь репозитория",
	"Repository web URL": "Веб-адрес репозитория",
	"Windows path": "Путь Windows",
	"Windows client path": "Клиентский путь Windows",
	"Linux path": "Путь Linux",
	"Linux client path": "Клиентский путь Linux",
	"PROJECT MAPPING": "СОПОСТАВЛЕНИЕ ПРОЕКТА",
	"Check paths": "Проверить пути",
	"Remove custom repository": "Удалить пользовательский репозиторий",
	"Advanced settings": "Расширенные настройки",
	"Repository Editor": "Редактор репозиториев",
	REPOSITORIES: "РЕПОЗИТОРИИ",
	"Add custom repository": "Добавить пользовательский репозиторий",
	Sync: "Синхронизировать",
	sync: "синхронизация",
	"Repository storage": "Хранилище репозитория",
	"Snapshots, previews, check-in, check-out and synchronization depend on a valid repository path.": "Снапшоты, превью, check-in, check-out и синхронизация зависят от корректного пути репозитория.",
	"Repository configuration is loading": "Конфигурация репозитория загружается",
	"Open Repository Editor": "Открыть редактор репозиториев",
	"Checking…": "Проверка…",
	"Active repositories": "Активные репозитории",
	"The default repository is used when an operation does not choose another destination explicitly.": "Репозиторий по умолчанию используется, если операция явно не выбрала другое назначение.",
	Disabled: "Отключено",
	"Not checked": "Не проверено",
	"Restart required after changes": "После изменения нужен перезапуск",
	"Background jobs": "Фоновые задания",
	files: "файлов",
	"Bulk file transfers": "Массовая передача файлов",
	"Leave empty to keep the stored secret": "Оставьте пустым, чтобы сохранить текущий секрет",
	"Use default": "Использовать значение по умолчанию",
	"Clear stored secret": "Удалить сохранённый секрет",
	"Saved value: {value}": "Сохранённое значение: {value}",
	"Configured (hidden)": "Задано (скрыто)",
	"Default when empty: {value}": "Если не задано: {value}",
	"Environment override: {value}": "Переопределено окружением: {value}",
	"Web and API": "Веб-интерфейс и API",
	"Server endpoint, active preset and current sign-in status.": "Адрес сервера, активный пресет и текущее состояние входа.",
	"TACTIC HTTP endpoint used by the active server preset and connection test.": "HTTP-адрес TACTIC, используемый активным серверным пресетом и проверкой соединения.",
	"Server preset": "Пресет сервера",
	"Select a saved endpoint and its account and routing configuration.": "Выберите сохранённый адрес сервера вместе с настройками учётной записи и маршрутизации.",
	"XML-RPC supports Legacy TACTIC and TACTIC Stream. JSON requires TACTIC Stream. Saved separately for each preset; applying reconnects.": "XML-RPC работает с Legacy TACTIC и TACTIC Stream. JSON требует TACTIC Stream. Выбор сохраняется в пресете; применение переподключает сервер.",
	"XML-RPC": "XML-RPC",
	"JSON (TACTIC Stream)": "JSON (TACTIC Stream)",
	"Query execution": "Выполнение запросов",
	"Local mode needs no server installation. Plugin mode installs or updates the server package on first use with an administrator ticket.": "Локальный режим не требует установки на сервер. Режим плагина устанавливает или обновляет пакет при первом использовании с тикетом администратора.",
	Local: "Локально",
	"Server plugin": "Серверный плагин",
	"Background checks": "Фоновые проверки",
	"Committed changes are coalesced by one server worker. Only subscribed data is refreshed; presence and authentication keep their own heartbeat.": "Один серверный воркер объединяет зафиксированные изменения. Обновляются только данные подписки; присутствие и авторизация проверяются отдельно.",
	"Update delivery": "Получение обновлений",
	"Server push (SSE) uses the TACTIC Stream collector and refreshes only subscribed data. Other servers require periodic checks.": "SSE использует сборщик TACTIC Stream и обновляет данные подписок. Для других серверов нужен периодический опрос.",
	"Periodic checks": "Периодический опрос",
	"Server push (SSE)": "Обновления от сервера (SSE)",
	"Update batching delay": "Задержка объединения обновлений",
	"Combine arriving changes before reading data. A longer delay reduces requests during bursts; it also delays visible updates.": "Объединять поступающие изменения перед чтением данных. Большая задержка уменьшает число запросов при серии изменений, но откладывает обновление интерфейса.",
	"100 ms": "100 мс",
	"200 ms": "200 мс",
	"500 ms": "500 мс",
	"1000 ms": "1000 мс",
	"Server updates": "Обновления с сервера",
	"Interval for the shared request, including the connection check and presence heartbeat.": "Интервал общего запроса, включая проверку соединения и отметку присутствия.",
	"Every 5 seconds": "Каждые 5 секунд",
	"Every 10 seconds": "Каждые 10 секунд",
	"Every 30 seconds": "Каждые 30 секунд",
	"Every 60 seconds": "Каждые 60 секунд",
	"Check ZIP snapshots on this TACTIC sObject at startup and once a day.": "Проверять ZIP-снапшоты этого sObject TACTIC при запуске и раз в сутки.",
	"Update sObject search key": "Ключ поиска sObject обновлений",
	"Leave empty to disable automatic checks. Publish release ZIPs as snapshots of this object.": "Оставьте пустым, чтобы отключить автоматические проверки. Публикуйте ZIP-релизы как снапшоты этого объекта.",
	"Application window": "Окно приложения",
	"Choose what happens when the main window is closed.": "Выберите, что происходит при закрытии главного окна.",
	"Close to system tray": "Сворачивать в системный трей",
	"Keep TACTIC Handler running in the system tray when the main window close button is pressed. Disable this to exit completely.": "Оставлять TACTIC Handler запущенным в системном трее при нажатии кнопки закрытия главного окна. Отключите этот параметр для полного выхода.",
	"DCC connections": "Подключения DCC",
	"Control the local server used by DCC clients.": "Настройте локальный сервер для подключения DCC-клиентов.",
	"Start Handler Server automatically": "Автоматически запускать Handler Server",
	"Launch the local DCC server when TACTIC Handler starts. Disable this if you only use the standalone app; manual start remains available. Takes effect next launch.": "Запускать локальный сервер DCC при старте TACTIC Handler. Если используете только самостоятельное приложение, отключите автозапуск: вручную сервер по-прежнему можно запустить. Вступит в силу при следующем запуске.",
	"Choose which background updates appear as pop-up notifications.": "Выберите, какие фоновые обновления показывать во всплывающих уведомлениях.",
	"Activity feed notifications": "Уведомления ленты активности",
	"Show a bottom-right notification when another user creates a new activity event. This setting applies immediately.": "Показывать уведомление справа внизу, когда другой пользователь создаёт новое событие активности. Настройка применяется сразу.",
	"Message notifications": "Уведомления о сообщениях",
	"Show a bottom-right notification for new messages when their conversation is not open. This setting applies immediately.": "Показывать уведомление справа внизу о новых сообщениях, если их диалог не открыт. Настройка применяется сразу.",
	"Background workers": "Фоновые потоки",
	"Limit parallel server requests and local background work.": "Ограничьте параллельные запросы к серверу и локальные фоновые операции.",
	"TACTIC request threads": "Потоки запросов TACTIC",
	"Maximum simultaneous XMLRPC requests. Repository Sync sends this many different chunks at once.": "Максимальное число одновременных XMLRPC-запросов. Repository Sync отправляет столько разных чанков одновременно.",
	"Local worker threads": "Локальные рабочие потоки",
	"Maximum simultaneous local background operations. This does not change the Repository Sync download limit.": "Максимальное число одновременных локальных фоновых операций. Лимит загрузок Repository Sync от этого не меняется.",
	Diagnostics: "Диагностика",
	"Choose which event types are written to the diagnostic log.": "Выберите типы событий, которые будут записываться в журнал диагностики.",
	"Configuration location": "Расположение конфигурации",
	"Location used by the shared TACTIC Handler configuration API.": "Расположение, используемое общим API конфигурации TACTIC Handler.",
	"Active configuration root": "Активная корневая папка конфигурации",
	"This path is managed by the application environment and is shown here for diagnostics.": "Этот путь управляется окружением приложения и показан здесь для диагностики.",
	"Workspace cache": "Кэш рабочего пространства",
	"Control saved Search Tab layout separately from cached server records.": "Управляйте сохранённой компоновкой вкладок поиска отдельно от кэшированных записей сервера.",
	"Cache process tabs": "Кэшировать вкладки процессов",
	"Restore search process tabs from the persistent cache instead of rebuilding every tab during startup.": "Восстанавливать вкладки процессов поиска из постоянного кэша вместо повторного построения при каждом запуске.",
	"Clear tabs cache": "Очистить кэш вкладок",
	"Discard cached search tabs and rebuild them from current project data on the next load.": "Удалить кэшированные вкладки поиска и при следующей загрузке построить их заново из актуальных данных проекта.",
	"Cached server data": "Кэширование данных сервера",
	"Choose which unchanged TACTIC data may be restored locally. Refresh actions always bypass these caches.": "Выберите, какие неизменённые данные TACTIC можно восстанавливать локально. Команды обновления всегда обходят кэш.",
	"Projects and reference data": "Проекты и справочные данные",
	"Projects, Search Types, pipelines, processes, statuses, users, groups and tags.": "Проекты, Search Types, пайплайны, процессы, статусы, пользователи, группы и теги.",
	"Search results and sObjects": "Результаты поиска и sObjects",
	"Ordered search pages and unchanged object fields used by Search Tabs.": "Упорядоченные страницы поиска и неизменённые поля объектов во вкладках поиска.",
	"Snapshots and files": "Снапшоты и файлы",
	"Snapshot and file metadata. Repository files remain managed by Repository Sync.": "Метаданные снапшотов и файлов. Файлы репозитория по-прежнему обслуживает Repository Sync.",
	relations: "Связи",
	"Children and relations": "Дочерние объекты и связи",
	"Expanded child branches and linked-object membership.": "Развёрнутые дочерние ветви и состав связанных объектов.",
	"Task Manager scopes, pages and task metadata.": "Области Task Manager, страницы и метаданные задач.",
	notes: "Заметки",
	"Object and process note histories with attachment metadata.": "История заметок объектов и процессов с метаданными вложений.",
	Messages: "Сообщения",
	"A bounded set of recent conversation histories and attachment metadata.": "Ограниченный набор недавних историй разговоров и метаданных вложений.",
	"Activity Feed": "Лента активности",
	"Recent activity pages and complete calendar day counts.": "Страницы недавней активности и полные счётчики событий календаря.",
	"Work hours": "Рабочие часы",
	"Timesheet and report query results for previously opened ranges.": "Результаты табеля и отчётов для ранее открытых диапазонов.",
	"Cache maintenance": "Обслуживание кэша",
	"Clearing raises the cache generation first, so an older background request cannot restore cleared data.": "При очистке сначала повышается поколение кэша, поэтому старый фоновый запрос не сможет вернуть удалённые данные.",
	"Clear all cached server data": "Очистить все кэшированные данные сервера",
	"Search tabs will keep their layout, but server records will be loaded again when needed.": "Вкладки поиска сохранят компоновку, но записи сервера при необходимости загрузятся заново.",
	"Choose the interface style, color mode, palettes, and semantic icon set.": "Выберите стиль интерфейса, цветовой режим, палитры и набор семантических иконок.",
	"Dark color mode": "Тёмный цветовой режим",
	"Use dark surfaces and the dark palette assigned to the selected interface style.": "Использовать тёмные поверхности и тёмную палитру, назначенную выбранному стилю интерфейса.",
	"Interface style": "Стиль интерфейса",
	"Light mode palette": "Палитра светлого режима",
	"Base surface and accent used when the application is in light mode.": "Основной цвет поверхностей и акцент для светлого режима приложения.",
	"Dark mode palette": "Палитра тёмного режима",
	"Base surface and accent used when the application is in dark mode.": "Основной цвет поверхностей и акцент для тёмного режима приложения.",
	"Icon set": "Набор иконок",
	"Click animations": "Анимации при нажатии",
	"Animate press feedback, ripples, switches, and disclosure controls.": "Анимировать отклик на нажатие, волны, переключатели и элементы раскрытия.",
	"Hover animations": "Анимации при наведении",
	"Animate pointer hover feedback while keeping the same hover states available instantly when disabled.": "Анимировать отклик при наведении указателя. Если отключено, те же состояния наведения показываются мгновенно.",
	"Fades and transitions": "Появления и переходы",
	"Animate appearing content, view transitions, expansion, and other interface fades.": "Анимировать появление содержимого, переходы между видами, раскрытие и другие плавные изменения интерфейса.",
	"Menu and popup animations": "Анимации меню и попапов",
	"Animate opening and closing menus, dropdowns, popups, and tooltips. Disable for instant appearance and dismissal.": "Анимировать открытие и закрытие меню, выпадающих списков, попапов и подсказок. Отключите для мгновенного появления и закрытия.",
	Language: "Язык",
	"Choose the language used by the application interface.": "Выберите язык интерфейса приложения.",
	"Interface language": "Язык интерфейса",
	"Changes application labels and help text while project-defined names remain unchanged.": "Изменяет подписи интерфейса и справку, не переводя названия, заданные в проекте.",
	Rendering: "Рендеринг интерфейса",
	"Choose how Qt Quick draws and presents the interface. Changes take effect after restarting TACTIC Handler.": "Выберите способ отрисовки и вывода интерфейса Qt Quick. Изменения применятся после перезапуска TACTIC Handler.",
	"Graphics backend": "Графический API",
	"Automatic (recommended)": "Автоматически (рекомендуется)",
	OpenGL: "OpenGL",
	"Direct3D 11": "Direct3D 11",
	"Direct3D 12": "Direct3D 12",
	Vulkan: "Vulkan",
	Software: "Программный",
	"Task workspace defaults": "Настройки рабочего пространства задач",
	"Initial task surface, presentation, ordering and grouping.": "Начальный раздел задач, представление, сортировка и группировка.",
	"Initial task surface": "Начальный раздел задач",
	"Open Quick Tasks or the detailed Task Browser first.": "Сначала открывать быстрые задачи или подробный Task Browser.",
	"Quick Tasks": "Быстрые задачи",
	"Task Browser": "Браузер задач",
	"Quick Tasks presentation": "Представление быстрых задач",
	"Show editable process cards or a compact task list.": "Показывать редактируемые карточки процессов или компактный список задач.",
	"Compact list": "Компактный список",
	"Initial view": "Начальный вид",
	"View opened first when Task Browser has no saved local state.": "Вид, открываемый первым, если у Task Browser нет сохранённого локального состояния.",
	list: "Список",
	Gantt: "Гантт",
	"Initial sorting": "Начальная сортировка",
	"Default order used before the user applies a table or column sort.": "Порядок по умолчанию до применения пользовательской сортировки таблицы или колонки.",
	Deadline: "Срок",
	"Recently changed": "Недавно изменённые",
	Assignee: "Исполнитель",
	"Parent object": "Родительский объект",
	Milestone: "Этап",
	Supervisor: "Руководитель",
	"Initial grouping": "Начальная группировка",
	"Default group structure used when Task Browser is opened.": "Структура групп по умолчанию при открытии Task Browser.",
	"By Process": "По процессу",
	"By Status": "По статусу",
	"By Assignee": "По исполнителю",
	"By Parent Object": "По родительскому объекту",
	"By Project": "По проекту",
	"By Search Type": "По типу поиска",
	"No Groups": "Без группировки",
	"Task Inspector expanded": "Инспектор задачи развёрнут",
	"Open Task Inspector in its expanded state when no saved dock state exists.": "Открывать Task Inspector развёрнутым, если сохранённое состояние дока отсутствует.",
	"Task table columns": "Колонки таблицы задач",
	"Choose visible columns, their width and display order. Object remains visible.": "Настройте видимые колонки, их ширину и порядок. Колонка объекта остаётся видимой.",
	"Search results": "Результаты поиска",
	"Choose how result items are loaded and initially presented.": "Выберите, как загружаются и изначально отображаются найденные объекты.",
	"Preview delivery": "Доставка превью",
	"Built-in processes": "Встроенные процессы",
	"Include TACTIC built-in processes together with project-defined processes in result items.": "Показывать встроенные процессы TACTIC вместе с процессами, настроенными в проекте.",
	"Result limit": "Лимит результатов",
	"Maximum number of sObjects requested for one search result page.": "Максимальное количество sObject, запрашиваемых для одной страницы результатов поиска.",
	"Loading mode": "Режим загрузки",
	"Use explicit result pages or load the next page when scrolling reaches the end.": "Использовать отдельные страницы результатов или загружать следующую страницу при прокрутке до конца.",
	Pages: "Страницы",
	Continuous: "Непрерывный",
	"Default result view": "Вид результатов по умолчанию",
	"Initial presentation used when a search tab has no saved view state.": "Начальный вид для вкладки поиска, у которой ещё нет сохранённого состояния отображения.",
	"Item interactions": "Действия с элементами",
	"Define the actions performed by double-click gestures on result items.": "Настройте действия, выполняемые двойным щелчком по найденным объектам.",
	"Double-click to save": "Двойной щелчок для сохранения",
	"A regular double-click downloads or saves the selected snapshot using the configured checkout behaviour.": "Обычный двойной щелчок загружает или сохраняет выбранный снапшот согласно настройкам check-out.",
	"Shift + double-click to open": "Shift + двойной щелчок для открытия",
	"Holding Shift while double-clicking opens the selected file in its associated application.": "Двойной щелчок с зажатым Shift открывает выбранный файл в связанном приложении.",
	"Versions and descriptions": "Версии и описания",
	"Control version placement and the amount of descriptive text shown on result items.": "Настройте размещение версий и объём текста описания в результатах.",
	"Separate versions": "Отделять версии",
	"Display snapshot versions in a dedicated area instead of mixing them with the main item content.": "Показывать версии снапшота в отдельной области, не смешивая их с основным содержимым элемента.",
	"Versions position": "Расположение версий",
	"Choose where the separate version area appears relative to the result item.": "Выберите расположение отдельной области версий относительно элемента результата.",
	Right: "Справа",
	Bottom: "Снизу",
	"Description length": "Длина описания",
	"Limit long sObject descriptions in results. Disable the switch to show the complete text.": "Ограничивать длинные описания sObject в результатах. Выключите параметр, чтобы показывать текст полностью.",
	"Snapshot Browser defaults": "Настройки Браузера снапшотов",
	"Choose the initial content and layout used by Snapshot Browser.": "Выберите начальное содержимое и компоновку Браузера снапшотов.",
	"Show every snapshot": "Показывать все снапшоты",
	"Include snapshots from every process instead of only the selected process.": "Показывать снапшоты всех процессов, а не только выбранного.",
	"Show more metadata": "Показывать больше метаданных",
	"Expand the additional snapshot metadata by default.": "По умолчанию раскрывать дополнительные метаданные снапшота.",
	"Initial content": "Начальное содержимое",
	"Show preview and files together, preview only, or files only.": "Показывать превью и файлы вместе, только превью или только файлы.",
	"Preview and files": "Превью и файлы",
	"Preview only": "Только превью",
	"Files only": "Только файлы",
	"Preview scaling": "Масштабирование превью",
	"Fit shows the whole image; Fill covers all available space and crops the edges.": "«Вписать» показывает изображение целиком; «Заполнить» занимает всю доступную область и обрезает края.",
	Fit: "Вписать",
	Fill: "Заполнить",
	"Initial orientation": "Начальная ориентация",
	"Arrange preview and file content side by side or from top to bottom.": "Расположить превью и файлы рядом или сверху вниз.",
	Horizontal: "Горизонтально",
	Vertical: "Вертикально",
	"File transfer": "Передача файлов",
	"Choose how files move between TACTIC and the workstation.": "Выберите способ передачи файлов между TACTIC и рабочей станцией.",
	"Check-in method": "Метод Check-in",
	Preallocate: "Предварительное размещение",
	"In-Place": "На месте",
	Move: "Перемещать",
	Upload: "Загружать",
	"Check-out method": "Метод Check-out",
	HTTP: "HTTP",
	"Snapshot creation": "Создание снапшотов",
	"Defaults applied while preparing new snapshots and DCC output files.": "Параметры по умолчанию для подготовки новых снапшотов и выходных файлов DCC.",
	"Update versionless snapshot": "Обновить versionless-снапшот",
	"Refresh the versionless snapshot whenever a new numbered version is checked in.": "Обновлять безверсионный снапшот при каждом check-in новой нумерованной версии.",
	"Local versionless files": "Локальные файлы versionless",
	"Copy is the default. Links point to the numbered version, including previews. Symbolic links on Windows need Developer Mode or privileges; hard links need the same volume. Versionless-only check-ins use copies. Remote server aliases follow its own configuration.": "По умолчанию — копия. Ссылки ведут на номерную версию, включая превью. Для символьных ссылок в Windows нужен режим разработчика или права; для жёстких — один том. Чекин только versionless использует копии. Алиасы удалённого сервера определяются его конфигурацией.",
	"Symbolic link": "Символьная ссылка",
	"Hard link": "Жёсткая ссылка",
	"Generate previews": "Создавать превью",
	"Create supported thumbnail and preview files as part of the check-in preparation.": "Создавать поддерживаемые миниатюры и превью при подготовке check-in.",
	"Clean completed Commit Queue items": "Очищать завершённые элементы Commit Queue",
	"Remove successful operations from Commit Queue automatically.": "Автоматически удалять успешные операции из Commit Queue.",
	"Confirm saving": "Подтверждать сохранение",
	"Ask for confirmation before saving a prepared check-in operation.": "Запрашивать подтверждение перед сохранением подготовленной операции check-in.",
	"Confirm revision saving": "Подтверждать сохранение ревизии",
	"Ask separately before saving a revision instead of a new version.": "Отдельно запрашивать подтверждение при сохранении ревизии вместо новой версии.",
	"Sequence padding": "Разрядность последовательности",
	"Enable a fixed number of digits when sequence frame numbers are generated.": "Использовать фиксированное количество цифр при формировании номеров кадров последовательности.",
	"Repository synchronization": "Синхронизация репозитория",
	"Control repository discovery, validation, and completed transfer cleanup.": "Настройте поиск файлов репозитория, проверку и очистку завершённых передач.",
	"Verify files with MD5": "Проверять файлы по MD5",
	"Compare checksums to detect changed local files. Enable only when stronger validation is worth the additional CPU work.": "Сравнивать контрольные суммы для поиска изменённых локальных файлов. Включайте, только если усиленная проверка оправдывает дополнительную нагрузку на процессор.",
	"Clean completed downloads": "Очищать завершённые загрузки",
	"Remove completed Repository Sync rows automatically after each successful download batch.": "Автоматически удалять завершённые строки Repository Sync после каждой успешной партии загрузок.",
	"Discovery mode": "Режим обнаружения",
	"Full scope discovers every file before downloading; partial scope overlaps discovery and transfer in chunks.": "Полный охват находит все файлы до загрузки; частичный охват совмещает обнаружение и передачу порциями.",
	"Full scope": "Полный список",
	"Partial scope": "Потоковая подготовка",
	"Partial scope chunk size": "Объектов в одном чанке",
	"Number of repository records discovered per chunk while partial scope mode is active.": "Количество записей репозитория в одной порции при частичном охвате.",
	"Drop Plate completion": "Завершение Drop Plate",
	"Choose what happens to Drop Plate state after a successful check-in.": "Выберите, что произойдёт с состоянием Drop Plate после успешного check-in.",
	"Share Drop Plate across tabs": "Общий Drop Plate для вкладок",
	"Use one Drop Plate selection for every compatible search tab.": "Использовать один набор Drop Plate для всех совместимых вкладок поиска.",
	"Uncheck submitted files": "Снимать отметку с отправленных файлов",
	"Keep submitted files in Drop Plate but clear their checked state after check-in.": "Оставлять отправленные файлы в Drop Plate, но снимать их отметку после check-in.",
	"Clear submitted files": "Удалять отправленные файлы",
	"Remove successfully submitted files from Drop Plate after check-in.": "Удалять успешно отправленные файлы из Drop Plate после check-in.",
	"File matching and naming": "Сопоставление и именование файлов",
	"Define how dropped directories, sequences, UDIM sets, and snapshot filenames are recognized.": "Настройте распознавание добавленных папок, последовательностей, наборов UDIM и имён файлов снапшотов.",
	"Group selected files": "Группировать выбранные файлы",
	"Combine the selected files into one snapshot instead of preparing a snapshot for each file.": "Объединять выбранные файлы в один снапшот вместо подготовки отдельного снапшота для каждого файла.",
	"Keep original filename": "Сохранять исходное имя файла",
	"Preserve source filenames instead of applying the active naming template.": "Сохранять исходные имена файлов вместо применения активного шаблона именования.",
	"Include subfolders": "Включать подпапки",
	"Scan nested folders when a directory is added to Drop Plate.": "Сканировать вложенные папки при добавлении каталога в Drop Plate.",
	"Allow a single UDIM or UV tile": "Разрешать одиночный тайл UDIM или UV",
	"Recognize one matching tile as a valid UDIM or UV set instead of requiring multiple tiles.": "Считать один подходящий тайл корректным набором UDIM или UV, не требуя несколько тайлов.",
	"Allow a single-frame sequence": "Разрешать последовательность из одного кадра",
	"Recognize one numbered file as a sequence when its padding matches the configured rules.": "Считать один нумерованный файл последовательностью, если его padding соответствует правилам.",
	"Minimum frame padding": "Минимальная разрядность кадров",
	"Smallest number of frame digits accepted by automatic sequence detection.": "Минимальное количество цифр номера кадра для автоматического распознавания последовательности.",
	"Matching templates": "Шаблоны сопоставления",
	"Edit the templates used to associate dropped files with check-in contexts.": "Редактировать шаблоны сопоставления добавленных файлов с контекстами check-in.",
	"The browser uses the server that hosts this application.": "Браузер подключён к серверу, на котором работает это приложение.",
	"Current account": "Текущая учётная запись",
	API: "API",
	"General application messages.": "Общие сообщения приложения.",
	"Informational application events.": "Информационные события приложения.",
	"Recoverable issues and warnings.": "Исправимые проблемы и предупреждения.",
	"Missing files and resources.": "Отсутствующие файлы и ресурсы.",
	"Unhandled exceptions.": "Необработанные исключения.",
	"Failed requests and application errors.": "Неудачные запросы и ошибки приложения.",
	"Critical application failures.": "Критические сбои приложения.",
	"Successful API calls, including arguments, results and duration.": "Успешные вызовы API, включая аргументы, результаты и время выполнения.",
	"Browser preferences": "Настройки браузера",
	"Additional browser features remain available alongside the Handler layout.": "Дополнительные возможности браузера доступны рядом с настройками ТХ.",
	"Color mode": "Цветовой режим",
	"Choose light or dark surfaces, or follow the system preference.": "Выберите светлые или тёмные поверхности либо следуйте настройке системы.",
	"Object notes": "Заметки объекта",
	"Open object and process notes in the Task Inspector, or use a separate notes-only window.": "Открывать заметки объекта и процесса в таск-инспекторе или в отдельном окне только для заметок.",
	"Task Inspector": "Инспектор задачи",
	"Standalone notes": "Отдельное окно заметок",
	"Clear cache": "Очистить кэш",
	Error: "Ошибки",
	"Move column up": "Переместить колонку вверх",
	"Move column down": "Переместить колонку вниз",
	"No Category": "Без категории",
	"Available projects": "Доступные проекты",
	Templates: "Шаблоны",
	"Built-in": "Встроенный",
	"Activate selected project": "Активировать выбранный проект",
	"Edit selected project": "Редактировать выбранный проект",
	"Deactivate current project": "Деактивировать текущий проект",
	"Create template archive": "Создать архив шаблона",
	"Create new project": "Создать новый проект",
	"Refresh projects": "Обновить проекты",
	"No active project": "Нет активного проекта",
	"Project image": "Изображение проекта",
	"Choose a large image; the repository web representation is used automatically when available.": "Выберите крупное изображение; при наличии автоматически используется его web-представление из репозитория.",
	"Project details": "Сведения о проекте",
	"Category and type describe how the project is organized; the project code is permanent.": "Категория и тип описывают организацию проекта; код проекта является постоянным.",
	"Permanent TACTIC identifier. It cannot be changed here.": "Постоянный идентификатор TACTIC. Здесь его изменить нельзя.",
	"Human-readable project title shown throughout the application.": "Понятное пользователю название проекта, отображаемое во всём приложении.",
	Category: "Категория",
	"Groups related projects in the chooser.": "Объединяет связанные проекты в окне выбора.",
	Type: "Тип",
	"Project classification stored by TACTIC.": "Классификация проекта, хранящаяся в TACTIC.",
	"Explain the purpose of the project for people browsing the workspace.": "Опишите назначение проекта для пользователей рабочего пространства.",
	Lifecycle: "Жизненный цикл",
	"Archived projects stay on the server but are hidden by default. Templates are available for creating new projects.": "Архивные проекты остаются на сервере, но по умолчанию скрыты. Шаблоны доступны для создания новых проектов.",
	"Archive project": "Архивировать проект",
	"Hide this project from the default active-project list without deleting it.": "Скрыть проект из списка активных по умолчанию, не удаляя его.",
	"Use as template": "Использовать как шаблон",
	"Mark this project as a source template for future projects.": "Пометить проект как исходный шаблон для будущих проектов.",
	"Edit project": "Редактирование проекта",
	"Project help": "Справка по проектам",
	"Discard changes?": "Отменить изменения?",
	"Choose a name and a unique code for the project.": "Укажите название и уникальный код проекта.",
	"Preview Image": "Изображение",
	"Optional image used to identify the project. TACTIC uploads it and creates its preview during project creation.": "Необязательное изображение проекта. TACTIC загружает его и создаёт превью при создании проекта.",
	Template: "Шаблон",
	"Copy the template configuration, or create an empty project. Templates and themes are loaded from your TACTIC server.": "Скопируйте конфигурацию шаблона или создайте пустой проект. Шаблоны и темы загружаются с вашего сервера TACTIC.",
	Review: "Проверка",
	"Check the details before creating your project.": "Проверьте данные перед созданием проекта.",
	"Project title": "Название проекта",
	"The title can contain spaces and special characters, up to 100 characters.": "Название может содержать пробелы и специальные символы, до 100 символов.",
	"Use letters, numbers and underscores, up to 30 characters. The code cannot start with a number and must be unique, including retired projects.": "До 30 латинских букв, цифр и подчёркиваний. Код не может начинаться с цифры и должен быть уникальным, включая архивные проекты.",
	"Project description": "Описание проекта",
	"Prefix for new Search Types: studio gives studio/shot, for example. Leave empty to use the project code. Does not rename the project. The sthpw and prod namespaces are reserved.": "Префикс новых Search Type: например, studio → studio/shot. Если поле пустое, используется код проекта. Не меняет имя проекта. sthpw и prod зарезервированы.",
	"Use this project as a template": "Использовать проект как шаблон",
	"Main project": "Главный проект",
	"An empty project can become the default project at the TACTIC root URL. TACTIC may need a restart for this to take effect.": "Пустой проект можно сделать главным для корневого URL TACTIC. Для применения может потребоваться перезапуск TACTIC.",
	"Copy from template": "Копировать из шаблона",
	"Manage templates": "Управление шаблонами",
	"Refresh templates": "Обновить шаблоны",
	"Empty project settings": "Настройки пустого проекта",
	Theme: "Тема",
	"A project theme installs server widget configuration. It does not change your personal interface appearance.": "Тема проекта устанавливает серверную конфигурацию виджетов и не изменяет ваше личное оформление интерфейса.",
	"Project summary": "Сводка проекта",
	"Create project": "Создать проект",
	"Project creation help": "Справка по созданию проекта",
	"No theme": "Без темы",
	Yes: "Да",
	No: "Нет",
	"The creation result is unknown. Refresh the catalog before trying again.": "Результат создания неизвестен. Обновите каталог перед следующей попыткой.",
	"Loading project templates…": "Загрузка шаблонов проектов…",
	"Working…": "Выполняется…",
	"Discard this project draft?": "Отменить этот черновик проекта?",
	"Retry opening project": "Повторить открытие проекта",
	"Install template archive": "Установить архив шаблона",
	upload: "Добавить файлы",
	"No installed template packages.": "Нет установленных пакетов шаблонов.",
	"Remove template {code}? Existing projects are not removed.": "Удалить шаблон {code}? Существующие проекты не удаляются.",
	"Download archive": "Скачать архив",
	"Path status": "Состояние пути",
	"Manage server presets": "Управление пресетами сервера",
	"Test connection": "Проверить подключение",
	"Additional settings": "Дополнительные настройки",
	"{visible} of {total} projects shown": "Показано проектов: {visible} из {total}",
	"A template supplies its own namespace and configuration. Main-project, namespace, theme and template flags apply only to an empty project.": "Шаблон задаёт собственное пространство имён и конфигурацию. Настройки главного проекта, пространства имён, темы и признака шаблона применяются только к пустому проекту.",
	"Maya Scene": "Сцена Maya",
	"Scene integration and Maya defaults": "Интеграция сцены и настройки Maya",
	"Maya scene environment": "Окружение сцены Maya",
	"Scene workspace and the preferred Maya file format.": "Рабочее пространство сцены и предпочитаемый формат Maya.",
	"Current work directory": "Текущая рабочая папка",
	"Workspace directory supplied by the Maya integration.": "Рабочая папка, которую сообщила Maya.",
	"Maya saving format": "Формат сохранения Maya",
	"Default format used to prepare a scene for check-in.": "Формат сцены по умолчанию при подготовке к отправке.",
	"Maya ASCII (.ma)": "Maya ASCII (.ma)",
	"Maya Binary (.mb)": "Maya Binary (.mb)",
	"Create Maya directories": "Создавать папки Maya",
	"Prepare the standard Maya project folder structure.": "Подготовить стандартную структуру папок проекта Maya.",
	"Create playblast": "Создавать playblast",
	"Prepare a playblast image when the workflow supports it.": "Подготовить плейбласт, если сценарий это поддерживает.",
	"Window behavior": "Поведение окна",
	"Choose which application receives focus after Maya actions.": "Выберите, какое приложение получит фокус после действий Maya.",
	"Return focus after opening a scene": "Возвращать фокус после открытия сцены",
	"Bring Maya forward after opening, importing, or referencing.": "Вывести Maya на передний план после открытия, импорта или референса.",
	"Return focus after saving a scene": "Возвращать фокус после сохранения сцены",
	"Bring Maya forward after saving or preparing a check-in.": "Вывести Maya на передний план после сохранения или подготовки к отправке.",
	"Uses the stable OpenGL backend on Windows and the native Qt default on other systems.": "В Windows используется стабильный OpenGL, а в других системах — нативный графический API Qt по умолчанию.",
	"GPU rendering without the Windows DXGI/MPO presentation path that can cause full-display flicker.": "GPU-отрисовка без пути вывода Windows DXGI/MPO, который может вызывать моргание всего экрана.",
	"Native Windows backend. On some MPO or HDR configurations it can make the whole display flicker during UI updates.": "Нативный графический API Windows. В некоторых конфигурациях MPO или HDR он может вызывать моргание всего экрана при обновлении интерфейса.",
	"Modern native Windows backend. Requires compatible graphics drivers.": "Современный нативный графический API Windows. Требует совместимых графических драйверов.",
	"Cross-platform GPU backend. Requires a working Vulkan driver.": "Кроссплатформенный графический API с поддержкой GPU. Требует рабочего драйвера Vulkan.",
	"CPU rendering for troubleshooting. It avoids graphics-driver issues but is noticeably slower.": "Программная отрисовка на CPU для диагностики. Обходит проблемы графических драйверов, но работает заметно медленнее.",
	"Locked by TACTIC TEAM Mode in the active server preset.": "Заблокировано режимом TACTIC TEAM в активном серверном пресете.",
	"Load preview files through the TACTIC HTTP endpoint instead of relying only on repository access.": "Загружать превью через HTTP-адрес TACTIC, а не полагаться только на прямой доступ к репозиторию.",
	"Choose whether new files are preallocated, kept in place, copied, moved, or uploaded.": "Выберите, будут ли новые файлы предварительно размещены, оставлены на месте, скопированы, перемещены или загружены.",
	"Use direct local repository access or download files through the TACTIC HTTP endpoint.": "Использовать прямой доступ к локальному репозиторию или загружать файлы через HTTP TACTIC.",
	"Material Design 3": "Material Design 3",
	"Current TACTIC-Handler appearance": "Оформление в стиле TACTIC Handler",
	"Material Design 5 (preview)": "Material Design 5 (экспериментальная)",
	"Experimental project theme, not an official specification": "Экспериментальная тема проекта, не официальная спецификация",
	"Fluent Design": "Fluent Design",
	"Compact Windows-oriented surfaces and motion": "Компактные поверхности и анимация в стиле Windows",
	Automatic: "Автоматически",
	"Material-first icons with safe fallbacks": "Сначала Material Design, затем надёжные запасные иконки",
	"Font Awesome Solid": "Font Awesome Solid",
	"Bold, filled application icons": "Контрастные закрашенные иконки приложения",
	"Font Awesome Outline": "Font Awesome Outline",
	"Lighter outlined icons where available": "Более лёгкие контурные иконки, где они доступны",
	"Material Design Icons": "Material Design Icons",
	"Material Design icon vocabulary": "Набор иконок Material Design",
	"Fluent Regular": "Fluent Regular",
	"Modern outlined Fluent System icons": "Современные контурные иконки Fluent System",
	"Fluent Filled": "Fluent Filled",
	"Modern filled Fluent System icons": "Современные закрашенные иконки Fluent System",
	Steel: "Стальной",
	Silver: "Серебристый",
	Ash: "Пепельный",
	Graphite: "Графитовый",
	Charcoal: "Угольный",
	Blue: "Синий",
	Azure: "Лазурный",
	Cyan: "Циан",
	Teal: "Бирюзовый",
	Emerald: "Изумрудный",
	Green: "Зелёный",
	Lime: "Лаймовый",
	Amber: "Янтарный",
	Orange: "Оранжевый",
	Coral: "Коралловый",
	Red: "Красный",
	Rose: "Розовый",
	Violet: "Фиолетовый",
	Indigo: "Индиго",
	"Testing…": "Проверка…",
	"Clearing…": "Очистка…",
	"Continue editing": "Продолжить редактирование",
	"Clear tabs cache": "Очистить кэш вкладок",
	"Save changes before closing Configuration?": "Сохранить изменения перед закрытием конфигурации?",
	"Object, process and version branches will collapse. Search tabs, filters and dock layouts remain unchanged.": "Ветки объектов, процессов и версий свернутся. Вкладки поиска, фильтры и леяуты доков сохранятся.",
	"The selected preview is not a readable image": "Выбранное превью не удалось прочитать как изображение",
	"Enable filter": "Включить фильтр",
	WHERE: "ГДЕ",
	"Quick filter": "Быстрый фильтр",
	"Add filter": "Добавить фильтр",
	"Remove filter": "Удалить фильтр",
	"Edit as custom filter": "Редактировать как пользовательский фильтр",
	"Managed by Quick Filters": "Управляется быстрыми фильтрами",
	"Filter column": "Столбец фильтра",
	"Filter relation": "Условие фильтра",
	relation: "Связь",
	"Filter value": "Значение фильтра",
	"TACTIC expression": "Выражение TACTIC",
	"Search Filters": "Фильтры поиска",
	"Searching...": "Поиск...",
	"Apply filters": "Применить фильтры",
	"Reset filters": "Сбросить фильтры",
	"No filters selected": "Фильтры не выбраны",
	"Loading tags…": "Загрузка тегов…",
	TAGS: "ТЕГИ",
	"Clear tags": "Очистить теги",
	"Reload tags": "Обновить теги",
	"Search tags": "Поиск тегов",
	"Clear search": "Очистить поиск",
	"Clear quick filters": "Очистить быстрые фильтры",
	"Apply the shared default to this tab": "Применить общие настройки по умолчанию к этой вкладке",
	"QUICK FILTERS": "БЫСТРЫЕ ФИЛЬТРЫ",
	"Saved searches": "Сохранённые поиски",
	"Select a saved search": "Выберите сохранённый поиск",
	"Update selected preset": "Обновить выбранный пресет",
	"Save as new preset": "Сохранить как новый пресет",
	"Saved search actions": "Действия с сохранённым поиском",
	"Rename preset": "Переименовать пресет",
	"Duplicate preset": "Дублировать пресет",
	"Copy saved search link": "Копировать ссылку на сохраненный поиск",
	"Delete preset": "Удалить пресет",
	"Refresh saved searches": "Обновить сохранённые поиски",
	snapshot: "снапшот",
	metadata: "Метаданные",
	"Selected filters": "Выбранные фильтры",
	"Copy selection from current tab": "Взять выбор из текущей вкладки",
	"Clear selected filters": "Очистить выбранные фильтры",
	"Available filters": "Доступные фильтры",
	"Show hidden filters": "Показать скрытые фильтры",
	"Save as defaults on server": "Сохранить как дефолты на сервере",
	"Save for this tab": "Сохранить для этой вкладки",
	"Preset name": "Название пресета",
	"Items per page": "Элементов на странице",
	" items": " элементов",
	"Result loading": "Загрузка результатов",
	"New item": "Создать",
	"Create record": "Создать объект",
	"Sync current Search Type": "Синхронизировать текущий Search Type",
	Changelists: "Чейнджлисты",
	"Commit Queue": "Очередь отправки",
	"{count} / page": "{count} / стр.",
	"Next page": "Следующая страница",
	"Previous page": "Предыдущая страница",
	Showing: "Показано",
	"{range} of {total}": "{range} из {total}",
	"{count} results": "{count} результатов",
	Refresh: "Обновить",
	"Page number": "Номер страницы",
	"Go to page": "Перейти на страницу",
	"Continuous tree": "Непрерывное дерево",
	"Compact rows": "Компактные строки",
	"Versions on the right": "Версии справа",
	"Versions at the bottom": "Версии снизу",
	"No grouping": "Без группировки",
	"SObject status": "Статус объекта",
	"Name A-Z": "Имя А–Я",
	"Name Z-A": "Имя Я–А",
	"Recently updated": "Недавно обновлённые",
	"Oldest updated": "Давно обновлённые",
	"Sort items": "Сортировка элементов",
	"Default order": "Исходный порядок",
	"Sort by column": "Сортировать по столбцу",
	"Group items": "Группировка элементов",
	"Task status by process": "Статус задачи по процессу",
	"Advanced Search": "Расширенный поиск",
	"Filter Processes": "Фильтр процессов",
	"Saved search": "Сохранённый поиск",
	"Loading saved searches...": "Загрузка сохраненных поисков...",
	"No saved searches": "Нет сохраненных поисков",
	"Sort by": "Сортировать по",
	Descending: "По убыванию",
	Ascending: "По возрастанию",
	Collapse: "Свернуть",
	Expand: "Развернуть",
	"Toggle All": "Переключить всё",
	"Toggle Process": "Переключить процессы",
	"Toggle Builtin Processes": "Переключить встроенные процессы",
	"Toggle Children": "Переключить дочерние типы",
	"Hide Togglers": "Скрыть переключатели",
	"Show Togglers": "Показать переключатели",
	"Pipeline for:": "Пайплайн для:",
	"Save and close": "Сохранить и закрыть",
	"Visibility has unsaved changes": "Есть несохранённые изменения видимости",
	"Search context changed. Reopen the editor.": "Контекст поиска изменился. Откройте редактор заново.",
	"Search tab name": "Имя вкладки поиска",
	"Related task filters": "Связанные фильтры задач",
	"No task": "Нет задачи",
	LATEST: "ПОСЛЕДНИЙ",
	"{count} check-in": "{count} чекин",
	"{count} check-ins": "{count} чекинов",
	"{count} related item": "{count} связанный объект",
	"{count} related items": "{count} связанных объектов",
	Is: "Равно",
	"Is not": "Не равно",
	Contains: "Содержит",
	"Does not contain": "Не содержит",
	"Is empty": "Пусто",
	"Is not empty": "Не пусто",
	"Starts with": "Начинается с",
	"Ends with": "Заканчивается на",
	"Does not start with": "Не начинается с",
	"Does not end with": "Не заканчивается на",
	In: "В списке",
	"Not in": "Не в списке",
	"Is greater than": "Больше",
	"Is less than": "Меньше",
	"Is newer than": "Новее",
	"Is older than": "Старее",
	"Is on": "В дату",
	Have: "Локально полученные версии",
	"Do not have": "Не имеют",
	"Match (slow)": "Соответствуют (медленно)",
	"Do not match (slow)": "Не соответствуют (медленно)",
	"Matched as {type}": "Распознано как {type}",
	"Template actions": "Действия с шаблоном",
	"Templates pane width": "Ширина списка шаблонов",
	"Template properties": "Параметры шаблона",
	Pattern: "Шаблон",
	"Preview: {preview} · Type: {type}": "Превью: {preview} · Тип: {type}",
	"Process mapping": "Сопоставление процессов",
	"All processes": "Все процессы",
	"Context mapping": "Сопоставление контекста",
	"All contexts": "Все контексты",
	"Test on filename": "Проверить на имени файла",
	Test: "Проверить",
	"No match": "Совпадений нет",
	"Enable template": "Включить шаблон",
	Completed: "Завершено",
	Failed: "Ошибка",
	Conflict: "Конфликт",
	Cancelled: "Отменено",
	"Remove file": "Удалить файл",
	"Quick ingest": "Быстрый инжест",
	"For another Search Type": "Для другого серч-тайпа",
	"Create one child item per file and publish immediately": "Создать по одному дочернему объекту на файл и сразу опубликовать",
	"Include: .mov, /regex/": "Включить: .mov, /regex/",
	"Ignore: .tmp, .db": "Игнорировать: .tmp, .db",
	"Parse values from a path pattern": "Извлекать значения из шаблона пути",
	"Update matching item": "Обновлять совпавший объект",
	"Create preview when supported": "Создавать превью для поддерживаемых файлов",
	"Extra Search Object values (JSON)": "Дополнительные поля серч-объекта (JSON)",
	Keywords: "Ключевые слова",
	"Keyword mode": "Режим ключевых слов",
	Simplified: "Упрощённый",
	"Context case": "Регистр контекста",
	"Case sensitive": "С учётом регистра",
	Lowercase: "Нижний регистр",
	"Scripts receive path, sobject, parent and snapshot. Return a truthy value to accept the file.": "Скрипты получают path, sobject, parent и snapshot. Верните истинное значение, чтобы принять файл.",
	"Validation script path": "Путь к скрипту проверки",
	"Process script path": "Путь к скрипту обработки",
	"Rule title": "Название правила",
	"Save rule": "Сохранить правило",
	"Delete rule": "Удалить правило",
	"One Search Object per file · snapshot in publish": "Один серч-объект на файл · снапшот в publish",
	"Drop files here": "Перетащите файлы сюда",
	"Each file creates a child item named without its extension.": "Для каждого файла будет создан дочерний объект с именем без расширения.",
	"Ingest rule": "Правило инжеста",
	"Remove extension from item name": "Убирать расширение из имени объекта",
	"Hide rule details": "Скрыть параметры правила",
	"Edit rule details": "Изменить параметры правила",
	"Ingest {count}": "Импортировать {count}",
	"Update is unavailable because at least one name does not identify exactly one existing item.": "Обновление недоступно: хотя бы одно имя не указывает ровно на один существующий объект.",
	"Create duplicates": "Создать дубликаты",
	"Skip existing": "Пропустить существующие",
	"Update existing": "Обновить существующие",
	"{count} file(s) match existing child items or repeat a name in this batch. What should ingest do?": "{count} файл(ов) совпадают с существующими дочерними объектами или повторяют имя в этом наборе. Как продолжить импорт?",
	"Conflicts: {names}": "Конфликты: {names}",
	"{count} file(s)": "{count} файл(ов)",
	"Open file": "Открыть файл",
	"Show folder": "Показать папку",
	"Copy file path": "Копировать путь к файлу",
	"Copy all file paths": "Копировать все пути файлов",
	"Remove from Drop Plate": "Убрать из Drop Plate",
	Directory: "Папка",
	"Paste files": "Вставить файлы",
	"Matching Templates": "Шаблоны сопоставления",
	"Group check-in": "Групповой Check-in",
	"Keep filename": "Сохранять имя файла",
	"Filter mode": "Режим фильтра",
	Filename: "Имя файла",
	"Filter files": "Фильтр файлов",
	"Filter by extension": "Фильтр по расширению",
	"Drop Plate": "Drop Plate",
	"Matching files…": "Сопоставление файлов…",
	"Drop files or directories here": "Перетащите сюда файлы или папки",
	"Select an object, process and context first": "Сначала выберите объект, процесс и контекст",
	"Add to queue": "Добавить в очередь",
	"Select file group": "Выбрать группу файлов",
	"File actions": "Действия с файлами",
	"Version must be a whole number from 0 to 9999": "Версия должна быть целым числом от 0 до 9999",
	"No previews": "Превью нет",
	Running: "Выполняется",
	"Needs validation": "Требуется проверка",
	"Uploaded {done} / {total} files · {bytes} / {totalBytes} MB": "Загружено файлов: {done} / {total} · {bytes} / {totalBytes} МБ",
	"Uploaded {done} files · {bytes} MB": "Загружено файлов: {done} · {bytes} МБ",
	"Check-ins: {completed} / {total} completed · {failed} failed · {cancelled} cancelled · {running} running": "Публикации: завершено {completed} / {total} · ошибок {failed} · отменено {cancelled} · выполняется {running}",
	"Elapsed: {seconds} s": "Прошло: {seconds} с",
	"No new progress for {seconds} s": "Нет обновлений {seconds} с",
	"Operation actions": "Действия с операцией",
	"Context: {context}": "Контекст: {context}",
	"{count} queue items · Ready to send": "Операций в очереди: {count} · Готово к отправке",
	FILE: "ФАЙЛ",
	bytes: "байт",
	"File selection": "Отбор файлов",
	"{sobject.name}_{snapshot.context}.mov": "{sobject.name}_{snapshot.context}.mov",
	"Publish target": "Куда публиковать",
	"TACTIC server scripts": "Серверные скрипты TACTIC",
	"Open Script Editor": "Открыть редактор скриптов",
	"Child items": "Дочерние объекты",
	"Loading ingest rules…": "Загружаем правила инжеста…",
	Stop: "Остановить",
	Invalid: "Некорректная операция",
	"Missing files": "Отсутствующие файлы",
	Validating: "Проверка",
	Prepared: "Подготовлено",
	"Ready to send": "Готово к отправке",
	"Capture screenshot": "Сделать снимок экрана",
	capture: "состояние",
	"Choose preview images": "Выбрать изображения превью",
	"Paste preview image from clipboard": "Вставить превью из буфера обмена",
	"Manage selected previews": "Управление выбранными превью",
	"Clear operation previews": "Очистить превью операции",
	"Commit current": "Отправить текущую",
	"Commit selected": "Закоммитить выбранные",
	"Remove operation": "Удалить операцию",
	"Move operation up": "Переместить операцию вверх",
	"Move operation down": "Переместить операцию вниз",
	"Clear completed": "Очистить завершенные",
	"Clear queue": "Очистить очередь",
	"The same files are already prepared for this object and context.": "Эти файлы уже подготовлены для этого объекта и контекста.",
	"Add another": "Добавить еще",
	"Ignore duplicate": "Игнорировать дубликат",
	"Select an operation": "Выберите операцию",
	"Ready for operations": "Всё готово к операциям",
	"Select an operation in the queue to review its files and settings.": "Выберите операцию в очереди, чтобы проверить её файлы и параметры.",
	"Add files through Save Snapshot or Drop Plate. You can review every prepared operation before sending it.": "Добавьте файлы через Save Snapshot или Drop Plate. Перед отправкой можно проверить каждую подготовленную операцию.",
	"Snapshot Browser": "Браузер снапшотов",
	"Commit all": "Отправить все",
	all: "Все",
	"More send actions": "Дополнительные варианты отправки",
	Versioned: "Нумерованная версия",
	"Waiting for naming preview": "Ожидание превью нейминга",
	"Not generated": "Не создано",
	"Apply every edit to checked items": "Применять каждое изменение к отмеченным элементам",
	"The current item and all checked operations will receive each edit.": "Каждая правка применяется к текущей и всем отмеченным операциям.",
	BASIC: "ОСНОВНОЕ",
	"Advanced options": "Расширенные параметры",
	"Automatic version": "Автоматически",
	Method: "Метод",
	"Generated by naming rules": "Сформировано правилами именования",
	"Local transfer methods require a desktop connection. Browser check-in uses Upload.": "Локальная передача требует подключения настольного клиента. В браузере используется загрузка Upload.",
	"FILE OPTIONS": "ПАРАМЕТРЫ ФАЙЛОВ",
	"Update versionless": "Обновлять versionless",
	"Commit versionless only": "Отправить только versionless",
	"Keep source filename": "Сохранять имя исходного файла",
	"Use context as filename": "Использовать контекст как имя файла",
	"Naming Editor": "Редактор именования",
	"Result unknown": "Результат неизвестен",
	"Check the current snapshot before repeating this check-in; the server may already have saved it.": "Перед повторной сдачей проверьте текущий снимок: сервер мог уже сохранить его.",
	QUEUE: "ОЧЕРЕДЬ",
	"Auto-clean": "Автоочистка",
	"Server queue": "На сервере",
	"Send files in chunks. The server checks in and reports results for the whole batch. Legacy mode is the default.": "Файлы передаются чанками. Сервер выполняет чекин и возвращает результаты всего пакета. По умолчанию — легаси.",
	"No file check-ins yet.": "Сдач файлов пока нет.",
	"Files pane height": "Высота списка файлов",
	"Select an operation to inspect its files.": "Выберите операцию для просмотра файлов.",
	"No files": "Нет файлов",
	"Choose source files before check-in": "Выберите исходные файлы перед чекином",
	"Choose source files again": "Повторно выбрать исходные файлы",
	"Operation previews": "Превью операций",
	"Add images": "Добавить изображения",
	"Paste image": "Вставить изображение",
	"Remove preview": "Удалить превью",
	"Upload interrupted. Use Retry to resume the existing batch.": "Загрузка прервана. Нажмите «Повторить», чтобы продолжить тот же пакет.",
	"Progress unavailable. Check-in results are not confirmed; retrying status requests.": "Нет связи с сервером. Результаты чекинов не подтверждены; повторяем запрос состояния.",
	"Running before check-in hooks": "Выполняем скрипты перед чекином",
	"Preparing files and checksums": "Подготавливаем файлы и контрольные суммы",
	uploading: "Загрузка файлов",
	"Uploading files": "Загружаем файлы",
	"Checking in on server": "Выполняем чекины на сервере",
	Finished: "Обработка завершена",
	"Upload progress": "Прогресс загрузки",
	"Server check-in progress": "Прогресс серверных чекинов",
	"Operation details": "Параметры операции",
	"Queue pane width": "Ширина списка операций",
	"{count} files": "{count} файлов",
	"No context": "Нет контекста",
	"Select operation for commit": "Выбрать операцию для отправки",
	"Remove file from operation": "Убрать файл из операции",
	"Preview actions": "Действия превью",
	"Context branch": "Ветка контекста",
	"Add context": "Добавить контекст",
	"Download file": "Скачать файл",
	"Matched as ": "Совпало как ",
	"{count} files selected. Check in one group or separately in sequence?": "Выбрано файлов: {count}. Опубликовать одной группой или по отдельности?",
	"Source files": "Исходные файлы",
	"Repository changed. Close this dialog and review the current path before confirming again.": "Репозиторий изменился. Закройте это окно и проверьте текущий путь перед повторным подтверждением.",
	"Resize capture area": "Изменить размер области захвата",
	"Repository Sync preset": "Пресет синхронизации репозитория",
	"Repository Sync scope": "Область синхронизации репозитория",
	"Processing server response: {count} objects": "Обработка ответа сервера: объектов {count}",
	"Requesting snapshots: {done} / {total} objects": "Запрос снапшотов: объектов {done} / {total}",
	"Preparing download queue: {count} files": "Подготовка очереди загрузки: файлов {count}",
	"Parallel repository chunks: {done} / {total} objects": "Параллельные части репозитория: объектов {done} / {total}",
	"{count} active downloads": "Активных загрузок: {count}",
	"{count} files in queue": "Файлов в очереди: {count}",
	"{count} failed downloads": "Неудачных загрузок: {count}",
	"Select file": "Выбрать файл",
	"Check in multiple files?": "Сохранить несколько файлов?",
	"One group": "Одной группой",
	Separately: "По отдельности",
	"The file stored in this revision will be replaced. Use Save snapshot when you need a new version.": "Файл в этой ревизии будет заменён. Для новой версии используйте «Сохранить снапшот».",
	"Replace revision": "Заменить ревизию",
	"The attachment result is unknown. Close this window and refresh the snapshot before retrying.": "Результат прикрепления неизвестен. Закройте это окно и обновите снапшот перед повторной попыткой.",
	"Choose files for check-in": "Выбрать файлы для Check-in",
	"Save from Clipboard": "Сохранить из буфера обмена",
	"Drop files here, paste an image, or choose files for check-in.": "Перетащите файлы сюда, вставьте изображение или выберите файлы для чекина.",
	"Keep original file names": "Сохранить исходные имена файлов",
	"Attach files": "Прикрепить файлы",
	"Add to Commit Queue": "Добавить в очередь чекина",
	"This affects every TACTIC client. Confirm only if the server can access this folder.": "Это затронет всех клиентов TACTIC. Подтверждайте, только если серверу доступна эта папка.",
	"Update server path": "Обновить путь сервера",
	"TACTIC's server-wide repository path will be set to:": "Общий серверный путь репозитория TACTIC будет изменён на:",
	"Repository storage is not configured": "Хранилище репозитория не настроено",
	"TACTIC-Handler needs a repository path for snapshots, previews, check-in, check-out and synchronization. Configure it now to avoid missing files.": "TACTIC-Handler нужен путь репозитория для снапшотов, превью, check-in, check-out и синхронизации. Настройте его сейчас, чтобы избежать отсутствующих файлов.",
	"Configure repositories": "Настроить репозитории",
	"Move or resize the area, then capture": "Переместите или измените область, затем сделайте снимок",
	"Drag over the area to capture": "Выделите область для снимка",
	"Cancel screenshot": "Отменить снимок",
	"Draw again": "Нарисовать заново",
	"Capturing…": "Создание снимка…",
	Capture: "Сделать снимок",
	"Remove Current Preset": "Удалить текущий пресет",
	"Save Current Preset Changes": "Сохранить изменения текущего пресета",
	"Create new Preset and Save": "Создать и сохранить новый пресет",
	Chunk: "Чанк",
	"Only updates": "Только обновления",
	"Preset has unsaved changes": "В пресете есть несохранённые изменения",
	"Begin Repo Sync": "Начать синхронизацию репозитория",
	"Create and save": "Создать и сохранить",
	"Requesting object list from TACTIC": "Получение списка объектов из TACTIC",
	"Preparing parallel repository chunks": "Подготовка параллельных чанков репозитория",
	streaming: "Скачивание файлов",
	"Stopping repository discovery": "Остановка поиска файлов репозитория",
	"Discovering repository files": "Поиск файлов репозитория",
	"Processed / total files": "Обработано / всего файлов",
	"Total size": "Общий объём",
	Downloaded: "Скачано",
	"Remaining data": "Осталось скачать",
	Speed: "Скорость",
	"Average speed": "Средняя скорость",
	Elapsed: "Прошло",
	"Successful / errors": "Успешно / с ошибкой",
	"Downloading repository files": "Загрузка файлов репозитория",
	"Ready to download repository files": "Файлы репозитория готовы к загрузке",
	"Repository download finished with errors": "Загрузка репозитория завершена с ошибками",
	"Repository download complete": "Загрузка репозитория завершена",
	"Repository discovery failed": "Не удалось просканировать репозиторий",
	"Clear completed downloads": "Очистить завершенные загрузки",
	"Auto-clean completed repository downloads": "Автоматически очищать завершённые загрузки репозитория",
	"Start checked downloads": "Запустить отмеченные загрузки",
	"Stop discovering more files": "Остановить поиск новых файлов",
	"Completed rows were cleared; the batch summary is retained": "Завершённые строки очищены; итоговая статистика сохранена",
	"Repository Sync queue is empty": "Очередь синхронизации репозитория пуста",
	"Background transfers are active — the interface remains responsive": "Фоновые передачи активны — интерфейс остаётся отзывчивым",
	"Files are verified before downloading and written atomically": "Файлы проверяются перед загрузкой и записываются атомарно",
	cancelled: "Cancelled",
	Downloading: "Загрузка",
	"Revert pending changes. Local files are kept unless deletion is selected.": "Откатить pending-изменения. Локальные файлы сохраняются, если удаление не выбрано.",
	"Delete files not in depot": "Удалить файлы вне depot",
	"Only newly added local files absent from the published stream will be moved to Trash after the server revert succeeds.": "После успешного серверного отката в Корзину попадут только новые локальные файлы, которых нет в опубликованном стриме.",
	Revert: "Откатить",
	"Revision selector": "Выбор ревизии",
	"File revision (each file)": "Ревизия каждого файла",
	"Submitted changelist": "Опубликованный чейнджлист",
	"As of date / time": "Состояние на дату / время",
	"Stream revision": "Ревизия стрима",
	"Revision number or date": "Номер ревизии или дата",
	"YYYY-MM-DD or ISO date / time": "ГГГГ-ММ-ДД или дата / время ISO",
	"Without a timezone, UTC is used. A date includes the whole UTC day.": "Без часового пояса используется UTC. Дата включает весь день по UTC.",
	"Files without this revision are left unchanged and reported in the Log.": "Файлы без этой ревизии остаются без изменений; список выводится в журнал.",
	"Changelist and stream revision select the complete submitted state of the selected stream.": "Чейнджлист и ревизия стрима задают его целиком опубликованное состояние.",
	"Force overwrite local files": "Принудительно перезаписать локальные файлы",
	"Force replaces modified files and removes files absent from the selected state. Preserve your local changes first.": "Force заменяет изменённые файлы и удаляет полученные ранее файлы, отсутствующие в выбранном состоянии. Сначала сохраните локальные изменения.",
	Get: "Получить",
	"Select a permitted shelf in the same stream. Replacing it preserves its previous contents.": "Выберите доступный shelf в том же stream. При замене предыдущее содержимое сохраняется.",
	"Shelved changelist": "Чейнджлист shelf",
	"Next shelves": "Следующие shelves",
	Continue: "Продолжить",
	"Target changelist": "Целевой список изменений",
	"Review selected add, edit, delete and rename operations. Local files are kept.": "Проверьте выбранные добавления, изменения, удаления и переименования. Локальные файлы сохраняются.",
	"Create a new changelist": "Создать новый чейнджлист",
	"Changelist description": "Описание списка изменений",
	"Add to changelist": "Добавить в чейнджлист",
	checkout: "Открыт для изменения",
	Checkout: "Чекаут",
	"Changelist #{number}": "Чейнджлист №{number}",
	"files on this page": "файлов на странице",
	"Finish or cancel the upload before submit": "Завершите или отмените загрузку перед submit",
	"Resolve all conflicts before submit": "Разрешите все конфликты перед submit",
	"Stream head changed; rebase before submit": "Head стрима изменился; выполните rebase перед submit",
	"The shelf is saved before reverting. Local files are kept.": "Shelf сохраняется перед revert. Локальные файлы остаются на диске.",
	"Merge stream": "Объединить потоки",
	Unshelve: "Взять с полки",
	"Rebase / resolve": "Обновить базу / разрешить конфликты",
	"Replace shelf files": "Заменить файлы в shelf",
	Shelve: "Сохранить на полку",
	"Excluded by workspace mapping": "Исключён mapping воркспейса",
	"Binary or large file. Use an external comparison application.": "Двоичный или большой файл. Используйте внешнее приложение сравнения.",
	"No differences.": "Различий нет.",
	"Comparison result": "Результат сравнения",
	"Compare with application…": "Сравнить в приложении…",
	staged: "подготовлены",
	"Waiting for upload": "Ожидает загрузки",
	Uploading: "Загрузка",
	"Verified; waiting for staging": "Проверен; ожидает подготовки",
	"Not mapped to workspace": "Не включён в mappings workspace",
	"Renamed / moved": "Переименован / перемещён",
	write: "Загружен",
	pending: "Pending",
	"Modified after upload": "Изменён после загрузки",
	Modified: "Изменён",
	Added: "Добавлен",
	Missing: "Отсутствует",
	"Marked for delete": "Помечен для удаления",
	shelved: "На полке",
	Shelved: "На полке",
	submitted: "Опубликован",
	Submitted: "Опубликован",
	"Checked out": "Открыт для изменения",
	"Newer on server": "На сервере новее",
	"Server only": "Только на сервере",
	deleted: "Удалён",
	"Deleted on server": "Удалён на сервере",
	Untracked: "Не отслеживается",
	"Not on server": "Отсутствует на сервере",
	Published: "Опубликован",
	"Load more": "Загрузить ещё",
	waiting: "ожидают",
	"Counts not indexed": "Счётчики не индексированы",
	Reverted: "Отменён",
	conflicts: "конфликтов",
	"No active checkout": "Нет активного checkout",
	"Owner: {owner}": "Владелец: {owner}",
	"Choose files to submit ({count})": "Выберите файлы для отправки ({count})",
	"Selected tasks: {count}": "Выбрано задач: {count}",
	"Files ({count})": "Файлы ({count})",
	"Tasks ({count})": "Задачи ({count})",
	"Selected items: {count}": "Выбрано элементов: {count}",
	"Delete {count} changelist(s) / shelf(s)? Local files are kept. Shelved contents will no longer be available. The whole selection is deleted together.": "Удалить списки изменений / полки ({count})? Локальные файлы сохранятся. Содержимое полок станет недоступным. Весь набор удаляется вместе.",
	"Confirm {operation} for the selected items? Local changes may be affected.": "Подтвердить {operation} для выбранных элементов? Локальные изменения могут быть затронуты.",
	"Column width must be a whole number from 48 to 900": "Ширина колонки должна быть целым числом от 48 до 900",
	State: "Состояние",
	Workspace: "Рабочее пространство",
	Date: "Дата",
	"Access type": "Доступ",
	Restricted: "Ограниченный",
	Public: "Общий",
	Stream: "Поток",
	"Loading changelist contents…": "Загрузка содержимого чейнджлиста…",
	"Shelved files": "Файлы в shelf",
	"Shelf changelist": "Список изменений на полке",
	"The selected changelist has changed. Reopen its details.": "Выбран другой чейнджлист. Откройте его сведения заново.",
	"Changelist actions": "Действия со списком изменений",
	"New depot": "Новый Depot",
	"Edit depot": "Редактировать Depot",
	"Depot code": "Код Depot",
	"Project storage": "Хранилище проекта",
	"Repository changes apply to new uploads. Existing file contents stay in their original storage.": "Смена repository применяется к новым загрузкам. Содержимое существующих файлов остаётся в прежнем хранилище.",
	"Depot paths are case-sensitive. Access is configured in Administration → Rules using file_depot.": "Пути Depot учитывают регистр. Доступ настраивается в Administration → Rules через file_depot.",
	"Select a depot": "Выберите Depot",
	Revision: "Ревизия",
	"Case-sensitive depot paths": "Пути Depot учитывают регистр",
	Depots: "Депоты",
	id: "id",
	"Revert changelist": "Отменить список изменений",
	"Remove files": "Убрать файлы",
	"Move to Trash": "В Корзину",
	"Mark for deletion": "Пометить на удаление",
	"Recipient login": "Логин получателя",
	"Changelist number": "Номер чейнджлиста",
	"Local workspace root": "Локальная папка рабочего пространства",
	"New depot path": "Новый путь в depot",
	"Merge source stream": "Исходный поток для объединения",
	OK: "ОК",
	"Move selected files between pending changelists. Local files are kept.": "Перенести выбранные файлы между pending-чейнджлистами. Локальные файлы сохранятся.",
	"Restore shelved files into this changelist. Review conflicts before Submit.": "Восстановить файлы из shelf в этот чейнджлист. Перед Submit проверьте конфликты.",
	"Open selected files for editing in this changelist. Missing local copies will be downloaded; existing local files are kept.": "Открыть выбранные файлы для редактирования в этом чейнджлисте. Отсутствующие локальные копии будут скачаны; существующие сохранятся.",
	"Move all files to another changelist, then delete the empty changelist. Or revert this changelist; it will appear in Reverted. Local files are kept.": "Перенеси все файлы в другой чейнджлист, затем удали пустой. Или откати этот чейнджлист — он появится в Reverted. Локальные файлы сохранятся.",
	"Move files…": "Перенести файлы…",
	"Pending changes and server tasks remain in the previous workspace. Local files are kept.": "Незавершённые changelists и серверные задачи останутся в прежнем workspace. Локальные файлы сохранятся.",
	"Apply the pinned query to all matching server files? The batch is atomic; local files are kept.": "Применить зафиксированную выборку ко всем подходящим файлам на сервере? Пакет атомарен; локальные файлы сохранятся.",
	"depot deletion on submit": "удаление из depot при Submit",
	"moving local copies to Trash": "перемещение локальных копий в корзину",
	"removing files from the changelist": "удаление файлов из чейнджлиста",
	"Revert the changelist? Local files will be kept.": "Отменить список изменений? Локальные файлы сохранятся.",
	"Changelist number, e.g. #42": "Номер чейнджлиста, например #42",
	"Local changes": "Локальные изменения",
	"Server state": "Состояние на сервере",
	"Checkout / locks": "Checkout / блокировки",
	"Local revision": "Локальная ревизия",
	Head: "Head",
	"Column width": "Ширина колонки",
	"New stream": "Новый стрим",
	"Stream Graph": "Граф стримов",
	"Parent links and submitted integrations. Double-click a stream to edit its settings.": "Связи Parent и опубликованные интеграции. Двойной щелчок открывает настройки стрима.",
	"Select a stream": "Выберите стрим",
	"Next connections": "Следующие связи",
	"Date submitted": "Дата отправки",
	Changelist: "Чейнджлист",
	"Submitted by": "Отправитель",
	"Workspace location": "Путь в workspace",
	"Depot location": "Путь в depot",
	"Local modification date": "Дата локального изменения",
	"Submitted at": "Дата submit",
	Author: "Автор",
	"Integration source": "Источник интеграции",
	Integrations: "Интеграции",
	"Checked Out By": "Взят в checkout",
	"Select a revision": "Выберите ревизию",
	"Select a file to inspect": "Выберите файл для просмотра",
	"No integration source for this revision": "У этой ревизии нет источника интеграции",
	"Exclusive checkout": "Эксклюзивный checkout",
	"Ordinary checkout": "Обычный checkout",
	"Loading preview…": "Загрузка предпросмотра…",
	"No content available for this file": "Для этого файла нет содержимого",
	"Binary file": "Двоичный файл",
	"Preview shows the first 256 KiB": "Показаны первые 256 КиБ",
	contain: "Вписать",
	"Copy log": "Скопировать журнал",
	"Clear log": "Очистить журнал",
	"Debug Log": "Журнал отладки",
	"Hide log": "Скрыть лог",
	"Collapse log": "Свернуть журнал",
	"Expand log": "Развернуть журнал",
	Log: "Лог",
	"Mappings and exclusions": "Mappings и исключения",
	"Add mapping": "Добавить mapping",
	"Technical JSON": "Технический JSON",
	"Workspace mappings (JSON)": "Сопоставления рабочего пространства (JSON)",
	"Mapping stream": "Stream для mapping",
	"Remove mapping": "Удалить mapping",
	"Depot pattern": "Шаблон пути depot",
	"Depot pattern, e.g. assets/...": "Шаблон depot, например assets/...",
	"Local pattern": "Шаблон локального пути",
	"Local pattern, e.g. art/...": "Локальный шаблон, например art/...",
	Exclude: "Исключить",
	Writable: "Разрешена запись",
	"Byte quota": "Квота в байтах",
	"Zero means unlimited.": "Ноль — без ограничения.",
	"File quota": "Квота файлов",
	"Parallel transfers": "Параллельные передачи",
	"From 1 to 16.": "От 1 до 16.",
	"Unfinished uploads (seconds)": "Незавершённые загрузки (секунды)",
	"Zero disables expiration.": "Ноль отключает истечение срока хранения.",
	"Reverted changelists (seconds)": "Откаченные списки изменений (секунды)",
	"Completed tasks (seconds)": "Завершённые задачи (секунды)",
	"Shelved changelists (seconds)": "Отложенные списки изменений (секунды)",
	"Quarantine before deletion (seconds)": "Карантин до удаления (секунды)",
	"Unreferenced contents stay in quarantine before physical deletion.": "Невостребованное содержимое остаётся в карантине до физического удаления.",
	"Automatic GC interval (seconds)": "Интервал автоматической очистки (секунды)",
	"Zero disables automatic cleanup.": "Ноль отключает автоматическую очистку.",
	queued: "В очереди на сервере",
	running: "Проверка и подготовка",
	"Storage administration": "Администрирование хранилища",
	"Storage index complete": "Индекс хранилища готов",
	"Storage index incomplete": "Индекс хранилища не готов",
	"Initialize storage": "Инициализировать хранилище",
	"Continue storage index": "Продолжить индексацию",
	"Stop waiting": "Прекратить ожидание",
	"Finish indexing before editing the policy or running GC. Indexing can be stopped and continued.": "Завершите индексацию перед изменением политики или запуском очистки. Индексацию можно остановить и продолжить.",
	Quotas: "Квоты",
	"Retention and cleanup": "Хранение и очистка",
	"Save storage policy": "Сохранить политику хранилища",
	"Garbage collection": "Очистка хранилища",
	"Dry run counts unused objects without deleting them. Safe GC expires retained records and quarantines unused contents according to the saved policy.": "Пробный запуск считает неиспользуемые объекты без удаления. Безопасная очистка завершает срок хранения записей и помещает невостребованное содержимое в карантин по сохранённой политике.",
	"Enable the files service on the server to process GC tasks.": "Включите сервис files на сервере для выполнения задач очистки.",
	"GC dry run": "Пробный GC",
	"Run safe GC": "Запустить безопасный GC",
	"Cancel GC": "Отменить очистку",
	"Objects scanned": "Проверено объектов",
	Candidates: "Кандидаты",
	"Expired records": "Истёкшие записи",
	Quarantined: "В карантине",
	Purged: "Удалено",
	"GC stopped. After fixing the cause, start a new dry run or safe GC.": "Очистка остановлена. После исправления причины запустите новую пробную или безопасную очистку.",
	"Run safe GC using the configured retention policy?": "Запустить безопасный GC с настроенной политикой хранения?",
	"Stream code": "Код стрима",
	Depot: "Депо",
	"Stream type": "Тип стрима",
	"Parent stream": "Родительский поток",
	"Choose parent": "Выбрать родителя",
	"The picker shows the first 1000 records. Enter another parent stream code directly.": "В списке показаны первые 1000 записей. Код другого родительского стрима можно ввести вручную.",
	"Only the owner and administrators may edit stream settings": "Настройки стрима могут менять только владелец и администраторы",
	"The new branch starts from the parent's published files without copying file contents.": "Новая ветка начинается с опубликованных файлов родителя без копирования содержимого файлов.",
	"Changing Parent changes the hierarchy. Existing files and their branch history stay intact.": "Смена Parent меняет иерархию. Существующие файлы и история ветвления сохраняются.",
	"Virtual streams, inherited path views and automatic merge/copy policies are not supported yet.": "Виртуальные стримы, наследуемые правила путей и автоматические политики merge/copy пока не поддерживаются.",
	"Preparing submit…": "Подготовка Submit…",
	"Select all files": "Выбрать все файлы",
	"Unchecked files remain pending. Local files are kept.": "Неотмеченные файлы останутся в pending. Локальные файлы сохраняются.",
	"Shelves are separate snapshots and are kept after submit.": "Shelf — отдельные снимки. После Submit они сохраняются.",
	"Additional options": "Дополнительные параметры",
	"Do not submit if resolved files have been modified": "Не выполнять Submit, если файлы изменены после разрешения конфликтов",
	"Check out submitted files after submit": "Снова открыть опубликованные файлы для редактирования",
	"Restrict access to changelist": "Ограничить доступ к сведениям о чейнджлисте",
	"Only the owner and administrators can view changelist details. Depot file permissions do not change.": "Сведения о чейнджлисте доступны только владельцу и администраторам. Права на файлы depot не меняются.",
	"On submit": "При Submit",
	"Submit all selected files": "Отправить все выбранные файлы",
	"Revert unchanged files": "Отменить неизменённые файлы",
	"Leave unchanged files pending": "Оставить неизменённые файлы в pending",
	"Link tasks to changelist (optional)": "Связанные задачи (необязательно)",
	"Find tasks by code or description": "Найти задачи по коду или описанию",
	"Search tasks": "Найти задачи",
	"Next tasks": "Следующие задачи",
	"No tasks. Create tasks in Task Manager.": "Задач нет. Создайте их в менеджере задач.",
	"Status after submit": "Статус после Submit",
	Submit: "Опубликовать",
	"In folder": "В папке",
	"Resolve status": "Разрешение конфликтов",
	Task: "Задача",
	"Stream root": "Путь стрима",
	Owner: "Владелец",
	Resolved: "Разрешённые",
	"Expand or collapse": "Развернуть или свернуть",
	"Switch workspace": "Переключить рабочее пространство",
	"Edit workspace": "Изменить рабочее пространство",
	"Workspace setup": "Настройка рабочего пространства",
	"Server metadata": "Серверные данные",
	"Selected server record": "Выбранная серверная запись",
	"No permitted records on this page": "На этой странице нет доступных записей",
	Conflicts: "Конфликты",
	Transfers: "Передачи",
	"Detail actions": "Действия с деталями",
	Unresolved: "Неразрешённые",
	"Next files": "Следующие файлы",
	"Save workspace": "Сохранить рабочее пространство",
	"Tab title": "Название вкладки",
	"File source": "Источник файлов",
	"Selected tree": "Выбранное дерево",
	"Depot files": "Файлы депо",
	"Changelist files": "Файлы списка изменений",
	"Pin file history": "Закрепить историю файла",
	"Changelist scope": "Область чейнджлистов",
	"My changes": "Мои чейнджлисты",
	"This workspace": "Этот workspace",
	"This stream": "Этот stream",
	"All permitted changes": "Все доступные чейнджлисты",
	"Path prefix": "Начало пути",
	"Case-sensitive local paths": "Учитывать регистр локальных путей",
	"Sample depot path": "Пример пути в depot",
	"Preview mappings": "Проверить mappings",
	Ready: "Готово",
	"Show log": "Показать лог",
	seconds: "секунд",
	"Transfer progress": "Прогресс передачи",
	Tools: "Инструменты",
	"Parent folder": "Родительская папка",
	"Workspace or depot path": "Путь workspace или depot",
	"Resume interrupted operation": "Продолжить прерванную операцию",
	"Connection lost; work retained": "Соединение потеряно; работа сохранена",
	"Interrupted operation available to resume": "Есть прерванная операция для продолжения",
	Clean: "Без изменений",
	"Not inspected": "Не проверен",
	Deleted: "Удалён",
	"Preparing manifest": "Подготовка манифеста",
	"Preparing local changes": "Подготовка локальных правок",
	"Applying atomic batch": "Применение атомарного пакета",
	"Submitting changelist": "Публикация чейнджлиста",
	"Recovering submit result": "Восстановление результата submit",
	"Verifying files": "Проверка файлов",
	"Staging files": "Подготовка файлов",
	"Unavailable locally": "Недоступно локально",
	"Indexing revision history": "Индексация истории ревизий",
	"Sync stopped": "Синхронизация остановлена",
	"Waiting for server": "Ожидание сервера",
	"Discovering files": "Поиск файлов",
	"Reconciling workspace": "Сравнение рабочего пространства",
	"Queued on server": "В очереди на сервере",
	"Verifying and staging": "Проверка и подготовка",
	"Downloading files": "Скачивание файлов",
	"Resolving conflicts": "Разрешение конфликтов",
	"Ready to submit": "Готов к публикации",
	"local unstaged": "локальных незалитых",
	tree: "Дерево",
	"New changelist": "Новый список изменений",
	"Restore panel": "Восстановить размер панели",
	"Maximize panel": "Развернуть панель",
	"Workspace actions": "Действия с рабочим пространством",
	"Local changes detected. Reconcile to review them.": "Обнаружены локальные изменения. Просмотрите их через Reconcile.",
	Filter: "Фильтр",
	"Filter loaded files": "Фильтр загруженных строк",
	"File state": "Состояние файла",
	"All states": "Все состояния",
	"Add to changelist…": "Добавить в чейнджлист…",
	"Parent: {parent}": "Родитель: {parent}",
	"Step {step} of {total}": "Шаг {step} из {total}",
	"The session changed during check-in. Inspect Snapshot Browser before repeating it.": "Сессия изменилась во время публикации. Проверьте результат в браузере снапшотов перед повторной отправкой.",
	ACTIVE: "АКТИВНЫЙ",
	COMMAND: "КОМАНДА",
	"CONNECTED CLIENTS": "ПОДКЛЮЧЕННЫЕ КЛИЕНТЫ",
	"Clear output": "Очистить вывод",
	"Clear results": "Очистить результаты",
	"Collapse output": "Свернуть вывод",
	"DCC clients help": "Справка по DCC-клиентам",
	"Disconnect selected": "Отключить выбранного",
	"Execution target": "Место исполнения",
	"Expand output": "Развернуть вывод",
	Folder: "Папка",
	"Hide scripts and outline": "Скрыть скрипты и структуру кода",
	"JSON payload": "Данные JSON",
	"New script": "Новый скрипт",
	Outline: "Структура",
	Output: "Вывод",
	"Output height": "Высота вывода",
	RESULTS: "РЕЗУЛЬТАТЫ",
	"Refresh scripts from server": "Обновить скрипты с сервера",
	Run: "Запускать",
	"Run Script": "Запустить скрипт",
	"Run in": "Запускать в",
	"Run selection": "Выполнить выделенное",
	"Running…": "Выполнение…",
	"Save current script to server": "Сохранить текущий скрипт на сервер",
	"Saved revisions": "Сохранённые ревизии",
	"Script folder": "Папка скрипта",
	"Script title": "Название скрипта",
	"Script triggers": "Триггеры скриптов",
	Scripts: "Скрипты",
	"Scripts panel": "Панель скриптов",
	"Scripts panel width": "Ширина панели скриптов",
	"Show scripts and outline": "Показать скрипты и структуру кода",
	"Start simulated Maya client": "Запустить симулятор клиента Maya",
	"Stop simulated Maya client": "Остановить симулятор клиента Maya",
	"TACTIC Handler Server": "Сервер TACTIC Handler",
	"Wrap output": "Переносить строки вывода",
	" selected": " выбрано",
	" unsaved": " несохранённых",
	"Add button": "Добавить кнопку",
	"Add trigger": "Добавить триггер",
	"Apply to selected": "Применить к выбранным",
	"Button label": "Подпись кнопки",
	"Choose icon": "Выбрать иконку",
	"Connection context changed. Discard this draft before saving.": "Контекст изменился. Отмените этот черновик перед сохранением.",
	"Context (optional)": "Контекст (необязательно)",
	"Create this shelf in the selected DCC": "Создать этот шелф в выбранном DCC",
	"Database Editor": "Редактор базы данных",
	"Description shown on hover": "Описание в подсказке",
	"Edit script shelf": "Редактировать шелф скриптов",
	FIELD: "ПОЛЕ",
	"For objects": "Для объектов",
	"Frame tool example": "Пример инструмента Frame",
	"Matching triggers run from top to bottom. A failed ‘before’ script stops the action; a failed ‘after’ script is logged and the remaining scripts continue.": "Подходящие триггеры выполняются сверху вниз. Ошибка скрипта до действия останавливает действие; ошибка скрипта после действия записывается в журнал, а остальные скрипты продолжают выполняться.",
	"New shelf": "Новый шелф",
	"No shelf buttons": "На шелфе нет кнопок",
	"No triggers yet": "Триггеров пока нет",
	"Process (optional)": "Процесс (необязательно)",
	"SELECTED OBJECTS": "ВЫБРАННЫЕ ОБЪЕКТЫ",
	"Save shelf": "Сохранить шелф",
	"Script is unavailable: ": "Скрипт недоступен: ",
	"Script shelf help": "Справка по шелфу скриптов",
	"Select one or more objects to edit database fields": "Выберите один или несколько объектов для редактирования полей базы данных",
	"Selected object": "Выбранный объект",
	"Shelf buttons": "Кнопки шелфа",
	"Shelf name": "Название шелфа",
	"Shelf owner": "Владелец полки",
	"Trigger name": "Название триггера",
	"Value for every selected item": "Значение для каждого выбранного элемента",
	"Add the first script button": "Добавьте первую кнопку скрипта",
	"All tabs": "Все табы",
	"Apply to this tab": "Применить к этой вкладке",
	"Apply to {count}": "Применить к {count}",
	"Choose a shelf above or create a new one.": "Выберите шелф выше или создайте новый.",
	"Choose field": "Выберите поле",
	"Choose script": "Выберите скрипт",
	Command: "Команда",
	"Delete “{name}”": "Удалить «{name}»",
	"Exact search keys, one per line (optional)": "Точные search key, по одному на строку (необязательно)",
	"Local DCC command router": "Локальный маршрутизатор команд DCC",
	Mine: "Мой",
	"My shelf": "Мой шелф",
	"No shelf selected": "Шелф не выбран",
	"Only saved executable scripts are listed.": "В списке доступны только сохранённые исполняемые скрипты.",
	"Personal shelf": "Личный шелф",
	"Remove button": "Удалить кнопку",
	"Remove “{name}”": "Убрать «{name}»",
	"Script triggers help": "Справка по триггерам скриптов",
	Shared: "Общий",
	"Shared shelf": "Общий шелф",
	"Tab shelves": "Шелфы вкладок",
	"Used on this tab": "Используется на этой вкладке",
	VALUE: "ЗНАЧЕНИЕ",
	"What this trigger does": "Что делает этот триггер",
	"{count} compatible objects selected": "Выбрано совместимых объектов: {count}",
	" h": " ч",
	"Approve entry": "Одобрить запись",
	"Approve selected entries": "Подтвердить выбранные записи",
	"Approved and pending time": "Одобренное и ожидающее время",
	"Authorized wage-based cost": "Стоимость на основе разрешённых ставок",
	"Back to articles": "Назад к статьям",
	"Back to title and summary": "Вернуться к заголовку и сводке",
	"Bid vs Actual": "План и факт",
	"Bold · Ctrl+B": "Жирный · Ctrl+B",
	"Change history": "История изменений",
	Checklist: "Чек-лист",
	"Clear selection": "Снять выделение",
	"Copy search key": "Копировать серч-ключ",
	"Copy transaction XML": "Скопировать XML транзакции",
	"Create article": "Создать статью",
	"Create section": "Создать раздел",
	"Daily logged time": "Записанное время по дням",
	"Delete article": "Удалить статью",
	"Delete entry": "Удалить запись",
	"Delete section": "Удалить раздел",
	"Discard order changes": "Отменить изменения порядка",
	"Dismiss error": "Закрыть ошибку",
	"Duration, hours": "Длительность, часы",
	"Edit article": "Редактирование статьи",
	"Edit entry": "Редактировать запись",
	"Edit section": "Редактирование раздела",
	"Editor mode": "Режим редактора",
	"Enter hours between 0.01 and 24.": "Введите от 0,01 до 24 часов.",
	"Hide article navigation": "Скрыть навигацию по статьям",
	"Hide linked objects and attached files": "Скрыть связанные объекты и прикреплённые файлы",
	"Hide table of contents": "Скрыть оглавление",
	"Hide title and summary": "Скрыть заголовок и сводку",
	"Hours by process": "Часы по процессам",
	"Hours by user": "Часы по пользователям",
	"Insert code block": "Вставить блок кода",
	"Insert link · Ctrl+K": "Вставить ссылку · Ctrl+K",
	"Insert quote": "Вставить цитату",
	"Insert table": "Вставить таблицу",
	"Italic · Ctrl+I": "Курсив · Ctrl+I",
	"Labor Cost": "Стоимость труда",
	"Link selected objects to article": "Связать выбранные объекты со статьёй",
	Lists: "Списки",
	"Local draft": "Локальный черновик",
	"Log time for the selected task": "Записать время для выбранной задачи",
	"More formatting actions": "Другие действия форматирования",
	"My Work Hours": "Мои рабочие часы",
	"Next week": "Следующая неделя",
	"No report data for this week": "За эту неделю данных для отчёта нет",
	"On this page": "На этой странице",
	"Open work reports": "Открыть отчеты о работе",
	Overtime: "Сверхурочно",
	"Planned and approved hours": "Запланированные и одобренные часы",
	"Previous week": "Предыдущая неделя",
	"Process Hours": "Часы по процессам",
	Publish: "Опубликовать",
	"Refresh timesheet": "Обновить табель",
	"Refresh transaction details": "Обновить подробности транзакции",
	Regular: "Обычные",
	"Reload articles": "Обновить статьи",
	Report: "Отчёт",
	"Return selected entries to pending": "Вернуть выбранные записи в ожидание",
	"Return to pending": "Вернуть на рассмотрение",
	"Save & Approve": "Сохранить и одобрить",
	"Save as draft": "Сохранить как черновик",
	"Save order": "Сохранить порядок",
	"Select a task before logging time": "Выберите задачу перед записью времени",
	"Select time entry": "Выбрать запись времени",
	"Show article navigation": "Показать навигацию по статьям",
	"Show attached files": "Показать прикреплённые файлы",
	"Show linked objects and attached files": "Показать связанные объекты и прикреплённые файлы",
	"Show table of contents": "Показать оглавление",
	"Show title and summary": "Показать заголовок и сводку",
	"Small text": "Мелкий текст",
	Strikethrough: "Зачёркнутый",
	"Team Hours": "Часы команды",
	"Team member": "Участник команды",
	"Transaction XML": "XML транзакции",
	"This nested table would repeat an ancestor scope": "Эта вложенная таблица повторяет область родительской таблицы",
	Underline: "Подчёркнутый",
	Visual: "Визуально",
	Week: "Неделя",
	"Work date": "Рабочая дата",
	"Work reports": "Отчёты о рабочих часах",
	Write: "Запись",
	code: "code",
	"{count} journal operations are hidden by access rules.": "Операции журнала скрыты правилами доступа: {count}.",
	"{count} selected": "Выбрано: {count}",
	"{minutes} min read": "Чтение: {minutes} мин",
	"Inherited from definition": "Наследуется из definition",
	"Column definition was not found in saved configurations.": "Определение колонки не найдено в сохранённых конфигурациях.",
	"Multiple selection": "Множественное выделение",
	selected: "выбрано",
	"Align selected elements": "Выровнять выбранные элементы",
	Align: "Выровнять",
	"Left edges": "По левым краям",
	"Horizontal centers": "По центрам по горизонтали",
	"Right edges": "По правым краям",
	"Top edges": "По верхним краям",
	"Vertical centers": "По центрам по вертикали",
	"Bottom edges": "По нижним краям",
	"Snap to guides": "Привязка к направляющим",
	"Horizontal offset": "Смещение по горизонтали",
	"Vertical offset": "Смещение по вертикали",
	"Fill color": "Цвет заливки",
	"Stroke color": "Цвет обводки",
	"Stroke width": "Толщина обводки",
	"Corner radius": "Радиус углов",
	Shadow: "Тень",
	"Animate layout changes": "Анимация перестроения",
	"Follows appearance motion settings. Disabled while editing.": "Учитывает настройки анимации интерфейса. Отключена при редактировании.",
	"Choose a theme color or enter a six-digit hex color": "Выберите цвет темы или укажите шестизначный HEX-цвет",
	"Select independent page blocks": "Выберите независимые блоки страницы",
	"Movement exceeds the page offset range": "Смещение превышает допустимый диапазон",
	"Appearance for selection": "Оформление выделения",
	"Custom fill color": "Свой цвет заливки",
	"Custom stroke color": "Свой цвет обводки",
	"Low surface": "Приглушённая поверхность",
	Transparent: "Прозрачный",
	Outline: "Контур",
	Panel: "Панель",
	Workspace: "Рабочая область",
	Accent: "Акцентный",
	"Grid layout": "Сетка",
	"Object image": "Изображение объекта",
	Divider: "Разделитель",
	Spacer: "Отступ",
	"Width behavior": "Режим ширины",
	"Height behavior": "Режим высоты",
	Fixed: "Фиксированный",
	"Fill container": "Заполнить контейнер",
	"Fit content": "По содержимому",
	"Minimum width": "Минимальная ширина",
	"Maximum width": "Максимальная ширина",
	"Minimum height": "Минимальная высота",
	"Maximum height": "Максимальная высота",
	"Grid columns": "Колонки сетки",
	"Minimum cell width": "Минимальная ширина ячейки",
	"Grid row height": "Высота строки сетки",
	"Column span": "Занять колонок",
	"Row span": "Занять строк",
	"Stack below width": "Вертикально при ширине меньше",
	"Icon size": "Размер иконки",
	"Button style": "Стиль кнопки",
	Normal: "Обычный",
	Primary: "Основной",
	Tonal: "Тональный",
	"Text style": "Стиль текста",
	"Text weight": "Насыщенность текста",
	"Text alignment": "Выравнивание текста",
	Caption: "Подпись",
	Body: "Основной текст",
	"Large body": "Крупный текст",
	Display: "Акцентный текст",
	Statistic: "Показатель",
	Hero: "Крупный показатель",
	Semibold: "Полужирный",
	Bold: "Жирный",
	"Text / icon color": "Цвет текста / иконки",
	"Custom text / icon color": "Свой цвет текста / иконки",
	"Image fit": "Размещение изображения",
	Contain: "Вписать целиком",
	Cover: "Заполнить с обрезкой",
	"Choose a supported component property": "Выберите допустимое свойство компонента",
	"Choose a supported size behavior": "Выберите допустимый режим размера",
	"Choose a supported icon": "Выберите иконку из каталога",
	"Maximum size must not be smaller than minimum size": "Максимальный размер не может быть меньше минимального",
	"Fixed sizing requires a numeric width or height": "Укажите число для фиксированной ширины или высоты",
	"Images use an object preview, not a field or static text": "Изображение использует превью объекта. Выберите проект, объект или запись.",
	"TACTIC link navigation is unavailable": "Навигация по ссылкам Тактика недоступна",
	"Record field": "Поле объекта",
	"Record form": "Форма объекта",
	"Record action": "Действие объекта",
	"Form fields": "Поля формы",
	"Select fields from the existing native edit view.": "Выберите поля существующего штатного вида редактирования.",
	"Native edit view": "Штатный вид редактирования",
	"Field display": "Отображение поля",
	"Status badge": "Метка статуса",
	"Value suffix": "Единицы после значения",
	"Native action": "Штатное действие",
	"Choose distinct fields from the native edit view": "Выберите разные поля штатного вида редактирования",
	"Choose existing record fields": "Выберите существующие поля объекта",
	"This field needs the full native record editor": "Для этого поля нужен полный штатный редактор объекта",
	"Choose an object binding for this widget": "Выберите объект для этого виджета",
	"Choose a saved page form": "Выберите форму сохранённой страницы",
	"Reload the changed page before saving": "Обновите изменённую страницу перед сохранением",
	"Select the record for this form": "Выберите объект для этой формы",
	"This form is read-only": "Эта форма доступна только для чтения",
	"The form configuration changed. Reload before saving.": "Настройки формы изменились. Обновите её перед сохранением.",
	"Choose editable fields from this form": "Выберите редактируемые поля этой формы",
	"Form text exceeds 64 KiB": "Текст формы превышает 64 КиБ",
	"Choose an available field value": "Выберите доступное значение поля",
	"Complete the required fields": "Заполните обязательные поля",
	"Reload the form before saving": "Обновите форму перед сохранением",
	"Finish or discard another form draft first": "Сначала сохраните или отмените другой черновик формы",
	"Progress requires a numeric field": "Для прогресса требуется числовое поле",
	"Field lists belong to native forms": "Список полей задаётся для штатной формы",
	"Choose Save or Check for this form": "Выберите сохранение или проверку состояния формы",
	"The page changed while a save was pending. Check saved state.": "Страница изменилась во время сохранения. Проверьте сохранённое состояние.",
	"Record field must be a finite number": "Поле объекта должно содержать конечное число",
	"Canvas settings": "Настройки холста",
	"Editor tools": "Инструменты редактора",
	"The source tab changed. Reload the page.": "Исходная вкладка изменилась. Обновите страницу.",
	"Connecting agent…": "Подключение агента…",
	"Agent connected": "Агент подключён",
	"Disconnecting agent…": "Отключение агента…",
	"Connected outside this UI. Stop it where it was started.": "Подключён вне этого интерфейса. Остановите его там, где запустили.",
	"Connect an agent to send requests.": "Подключите агента, чтобы отправлять задания.",
	"Stop connecting": "Прервать подключение",
	"Disconnect agent": "Отключить агента",
	"Disconnecting…": "Отключение…",
	"Connect agent": "Подключить агента",
	"Runs on the TACTIC server for this project.": "Работает на сервере Тактика в текущем проекте.",
	"Connect an agent to check this connection.": "Подключите агента для проверки этого подключения.",
	"The agent executor stopped unexpectedly. Connect again.": "Исполнитель агента неожиданно остановился. Подключитесь снова.",
	"An external agent is already connected to this project": "К этому проекту уже подключён внешний агент",
	"Agent connection failed": "Не удалось подключить агента",
	"No available models. Check AI providers.": "Нет доступных моделей. Проверьте настройки ИИ-провайдеров."
};
function translate(text, language, values) {
	let result = language === "ru" && russian[text] ? russian[text] : String(text || "");
	for (const key of Object.keys(values || {})) result = result.split("{" + key + "}").join(String(values[key]));
	return result;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/file.ui.mjs
function describe$2(value, width, language, enabled = true) {
	const tr = (text) => translate(text, language), name = String(value || "").replace(/\\/g, "/").split("/").pop(), actions = name ? 76 : 40;
	const nodes = [
		node("Box", "fileInputSurface", rect(0, 0, width, 44), { background: "surfaceContainerHigh" }),
		label("fileInputName", rect(12, 10, Math.max(0, width - actions - 20), 24), name || tr("No file selected"), {
			color: name ? "primaryText" : "secondaryText",
			toolTip: name || "",
			elideMiddle: true
		}),
		button("fileInputChoose", rect(Math.max(0, width - actions), 6, 32, 32), tr("Choose file"), "attach-file", { type: "choose" }, enabled, {
			iconOnly: true,
			iconAction: true
		})
	];
	if (name) nodes.push(button("fileInputClear", rect(Math.max(0, width - 36), 6, 32, 32), tr("Clear file"), "close", { type: "clear" }, enabled, {
		iconOnly: true,
		iconAction: true
	}));
	return {
		height: 44,
		nodes
	};
}
//#endregion
//#region src/controls/forms/AppFileInput.vue
var _hoisted_1$15 = [
	"aria-label",
	"disabled",
	"required"
];
var _sfc_main$16 = {
	__name: "AppFileInput",
	props: {
		value: String,
		disabled: Boolean,
		label: String,
		required: Boolean
	},
	emits: ["change"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const input = ref(null);
		const host = ref(null), width = ref(0);
		let observer;
		const scene = computed(() => describe$2(props.value, width.value, appearance.language, !props.disabled));
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function action(event) {
			if (props.disabled) return;
			if (event.type === "choose") input.value.click();
			else if (event.type === "clear") {
				input.value.value = "";
				emit("change", { target: { files: [] } });
			}
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "app-file-input",
				style: {
					"position": "relative",
					"height": "44px",
					"width": "100%"
				}
			}, [createVNode(_sfc_main, {
				scene: scene.value,
				onEvent: action
			}, null, 8, ["scene"]), createBaseVNode("input", {
				ref_key: "input",
				ref: input,
				type: "file",
				hidden: "",
				"aria-label": __props.label,
				disabled: __props.disabled,
				required: __props.required,
				onChange: _cache[0] || (_cache[0] = ($event) => emit("change", $event))
			}, null, 40, _hoisted_1$15)], 512);
		};
	}
};
//#endregion
//#region src/controls/UserGroupSection.vue
var _sfc_main$15 = {
	__name: "UserGroupSection",
	props: {
		title: String,
		compact: Boolean
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["user-group-section", { compact: __props.compact }]) }, [
				createVNode(_sfc_main$33, { name: "MDI_ACCOUNT_GROUP" }),
				createBaseVNode("span", null, toDisplayString(__props.title === "Ungrouped" ? unref(t)("UNGROUPED") : __props.title?.toUpperCase()), 1),
				_cache[0] || (_cache[0] = createBaseVNode("hr", null, null, -1))
			], 2);
		};
	}
};
//#endregion
//#region src/controls/userSearch.js
function matchesUser(user, query) {
	query = String(query || "").trim().toLowerCase();
	return !query || `${user.login} ${user.displayName || ""} ${user.email || ""} ${(user.groups || []).join(" ")}`.toLowerCase().includes(query);
}
//#endregion
//#region src/controls/UserComboBox.vue
var _hoisted_1$14 = { class: "user-combo-label" };
var _hoisted_2$6 = { class: "user-combo-list" };
var _hoisted_3$4 = { class: "user-combo-copy" };
var _hoisted_4$3 = { key: 0 };
var _sfc_main$14 = {
	__name: "UserComboBox",
	props: {
		value: String,
		placeholder: String,
		emptyLabel: {
			type: String,
			default: "Not assigned"
		},
		options: {
			type: Array,
			default: () => []
		},
		disabled: Boolean,
		actionField: {
			type: Boolean,
			default: true
		},
		label: {
			type: String,
			default: "Assigned to"
		}
	},
	emits: ["change"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const menu = ref(null), query = ref(""), popupWidth = ref(controls.userPicker.popupWidth), expanded = ref(false);
		const users = computed(() => [{
			value: "",
			login: "",
			displayName: t(props.emptyLabel),
			primaryGroup: "Ungrouped"
		}, ...props.options.filter((option) => option.value).map((option) => ({
			...option,
			login: option.value,
			displayName: option.label || option.displayName || option.value,
			initials: option.initials || (option.label || option.displayName || option.value).trim().split(/\s+/).map((word) => word[0]).filter(Boolean).filter((_, index, parts) => index === 0 || index === parts.length - 1).join("").toUpperCase(),
			primaryGroup: option.primaryGroup || "Ungrouped"
		}))]);
		const current = computed(() => users.value.find((user) => user.login === props.value) || {
			login: props.value,
			displayName: props.value
		});
		const groups = computed(() => {
			const rows = users.value.filter((user) => matchesUser(user, query.value)).sort((a, b) => (a.login ? 1 : 0) - (b.login ? 1 : 0) || a.primaryGroup.toLowerCase().localeCompare(b.primaryGroup.toLowerCase()) || a.displayName.toLowerCase().localeCompare(b.displayName.toLowerCase()));
			return [...new Set(rows.map((user) => user.primaryGroup))].map((title) => ({
				title,
				users: rows.filter((user) => user.primaryGroup === title)
			}));
		});
		function choose(user) {
			if (props.disabled) return;
			emit("change", user.value);
			menu.value.close(true);
		}
		function prepare() {
			query.value = "";
			const font = getComputedStyle(menu.value.$el), context = document.createElement("canvas").getContext("2d");
			context.font = `600 ${font.fontSize} ${font.fontFamily}`;
			popupWidth.value = Math.max(250, menu.value.$el.getBoundingClientRect().width, ...users.value.map((user) => context.measureText(user.displayName).width + 116));
		}
		function opened(event) {
			if (event.target !== menu.value?.$el) return;
			expanded.value = event.newState === "open";
			if (!expanded.value) return;
			nextTick(() => {
				if (menu.value?.open) menu.value.$el.querySelector("input")?.focus();
			});
		}
		function searchKey(event) {
			if (event.key === "ArrowDown") {
				event.preventDefault();
				(menu.value.$el.querySelector(".user-combo-option[aria-checked=\"true\"]") || menu.value.$el.querySelector(".user-combo-option"))?.focus();
			}
		}
		function optionKey(event) {
			if (![
				"ArrowUp",
				"ArrowDown",
				"Home",
				"End"
			].includes(event.key)) return;
			event.preventDefault();
			event.stopPropagation();
			const rows = [...menu.value.$el.querySelectorAll(".user-combo-option")], index = rows.indexOf(event.currentTarget);
			rows[event.key === "Home" ? 0 : event.key === "End" ? rows.length - 1 : (index + (event.key === "ArrowUp" ? -1 : 1) + rows.length) % rows.length]?.focus();
		}
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$26, {
				ref_key: "menu",
				ref: menu,
				class: normalizeClass(["user-combo-box", {
					"user-combo-field": !__props.actionField,
					disabled: __props.disabled
				}]),
				label: __props.label,
				disabled: __props.disabled,
				overlay: "",
				"align-start": "",
				width: popupWidth.value,
				"close-on-select": false,
				onBeforeOpen: prepare,
				onToggle: opened
			}, {
				trigger: withCtx(() => [
					createVNode(ItemPreview_default, {
						source: current.value.avatarUrl,
						"fallback-text": current.value.initials,
						"fallback-icon": "user",
						accent: current.value.avatarColor,
						"preview-size": 22,
						round: "",
						outlined: ""
					}, null, 8, [
						"source",
						"fallback-text",
						"accent"
					]),
					createBaseVNode("span", _hoisted_1$14, toDisplayString(__props.placeholder || current.value.displayName), 1),
					!__props.actionField ? (openBlock(), createBlock(_sfc_main$33, {
						key: 0,
						class: "user-combo-indicator",
						name: expanded.value ? "MDI_CHEVRON_UP" : "MDI_CHEVRON_DOWN"
					}, null, 8, ["name"])) : createCommentVNode("", true)
				]),
				default: withCtx(() => [createVNode(AppSearchField_default, {
					modelValue: query.value,
					"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => query.value = $event),
					label: "Search users",
					placeholder: unref(t)("Search users"),
					disabled: __props.disabled,
					onKeydown: searchKey,
					onSearch: _cache[1] || (_cache[1] = ($event) => groups.value[0]?.users[0] && choose(groups.value[0].users[0]))
				}, null, 8, [
					"modelValue",
					"placeholder",
					"disabled"
				]), createBaseVNode("div", _hoisted_2$6, [(openBlock(true), createElementBlock(Fragment, null, renderList(groups.value, (group) => {
					return openBlock(), createElementBlock(Fragment, { key: group.title }, [createVNode(_sfc_main$15, {
						title: group.title,
						compact: ""
					}, null, 8, ["title"]), (openBlock(true), createElementBlock(Fragment, null, renderList(group.users, (user) => {
						return openBlock(), createBlock(_sfc_main$34, {
							key: user.login,
							class: "user-combo-option",
							label: user.displayName,
							role: "radio",
							"aria-checked": __props.value === user.login,
							disabled: __props.disabled,
							onKeydown: optionKey,
							onClick: ($event) => choose(user)
						}, {
							default: withCtx(() => [
								createVNode(ItemPreview_default, {
									source: user.avatarUrl,
									"fallback-text": user.initials,
									"fallback-icon": "user",
									accent: user.avatarColor,
									"preview-size": 32,
									round: "",
									outlined: ""
								}, null, 8, [
									"source",
									"fallback-text",
									"accent"
								]),
								createBaseVNode("span", _hoisted_3$4, [createBaseVNode("strong", null, toDisplayString(user.displayName), 1), user.login ? (openBlock(), createElementBlock("small", _hoisted_4$3, toDisplayString(user.login), 1)) : createCommentVNode("", true)]),
								__props.value === user.login ? (openBlock(), createBlock(_sfc_main$33, {
									key: 0,
									class: "user-combo-check",
									name: "MDI_CHECK_CIRCLE"
								})) : createCommentVNode("", true)
							]),
							_: 2
						}, 1032, [
							"label",
							"aria-checked",
							"disabled",
							"onClick"
						]);
					}), 128))], 64);
				}), 128))])]),
				_: 1
			}, 8, [
				"class",
				"label",
				"disabled",
				"width"
			]);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/segmented.mjs
function selectable(option) {
	return option.enabled !== false && option.disabled !== true;
}
function entry(options, value) {
	const selected = options.findIndex((option) => selectable(option) && option.value === value);
	return selected >= 0 ? selected : options.findIndex(selectable);
}
function target(options, value, key) {
	if ([
		"ArrowLeft",
		"ArrowRight",
		"Home",
		"End"
	].indexOf(key) < 0) return -1;
	const indices = options.map((option, index) => selectable(option) ? index : -1).filter((index) => index >= 0);
	if (!indices.length) return -1;
	if (key === "Home") return indices[0];
	if (key === "End") return indices[indices.length - 1];
	const current = indices.indexOf(options.findIndex((option) => option.value === value));
	if (current < 0) return indices[key === "ArrowLeft" ? indices.length - 1 : 0];
	return indices[(current + (key === "ArrowRight" ? 1 : indices.length - 1)) % indices.length];
}
//#endregion
//#region src/controls/AppSegmentedButton.vue
var _hoisted_1$13 = ["aria-label"];
var _sfc_main$13 = {
	__name: "AppSegmentedButton",
	props: /*@__PURE__*/ mergeModels({
		options: {
			type: Array,
			default: () => []
		},
		label: String,
		disabled: Boolean,
		outlined: Boolean,
		iconOnly: Boolean
	}, {
		"modelValue": {},
		"modelModifiers": {}
	}),
	emits: /*@__PURE__*/ mergeModels(["update:modelValue"], ["update:modelValue"]),
	setup(__props, { emit: __emit }) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const emit = __emit;
		const entry$1 = computed(() => entry(props.options, model.value));
		function choose(option) {
			if (props.disabled || !selectable(option)) return;
			if (model.value !== option.value) model.value = option.value;
			else if (option.reselectable) emit("update:modelValue", option.value);
		}
		function move(event) {
			if (props.disabled || event.isComposing || event.altKey || event.ctrlKey || event.metaKey) return;
			const index = target(props.options, model.value, event.key);
			if (index < 0) return;
			event.preventDefault();
			choose(props.options[index]);
			event.currentTarget.querySelectorAll("button")[index].focus();
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["app-segmented-button", { outlined: __props.outlined }]),
				role: "radiogroup",
				"aria-label": unref(t)(__props.label),
				onKeydown: move
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.options, (option, index) => {
				return openBlock(), createBlock(_sfc_main$34, {
					key: option.value,
					label: option.label,
					"translate-label": option.translate !== false,
					icon: option.icon,
					"icon-only": __props.iconOnly,
					role: "radio",
					"aria-checked": model.value === option.value,
					tabindex: !__props.disabled && index === entry$1.value ? 0 : -1,
					disabled: __props.disabled || !selectable(option),
					onClick: ($event) => choose(option)
				}, null, 8, [
					"label",
					"translate-label",
					"icon",
					"icon-only",
					"aria-checked",
					"tabindex",
					"disabled",
					"onClick"
				]);
			}), 128))], 42, _hoisted_1$13);
		};
	}
};
//#endregion
//#region src/controls/AppEditableSelect.vue
var _hoisted_1$12 = ["id", "aria-label"];
var _sfc_main$12 = {
	__name: "AppEditableSelect",
	props: {
		modelValue: {
			type: [String, Number],
			default: ""
		},
		options: {
			type: Array,
			default: () => []
		},
		label: String,
		placeholder: String,
		disabled: Boolean
	},
	emits: ["update:modelValue", "accept"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const owner = ref(null), field = ref(null), menu = ref(null), expanded = ref(false);
		const popupId = useId();
		const popupWidth = ref(0);
		function choose(option) {
			if (props.disabled || option.disabled || option.enabled === false) return;
			emit("update:modelValue", option.value);
			menu.value.close();
			field.value.focus();
		}
		async function toggle(keyboard = false, last = false) {
			if (props.disabled) return;
			if (menu.value.open) {
				menu.value.close();
				return;
			}
			popupWidth.value = owner.value.getBoundingClientRect().width;
			menu.value.openAt({ target: owner.value.querySelector("input") });
			if (keyboard) {
				await nextTick();
				const options = [...menu.value.$el.querySelectorAll("[role=\"option\"]:not(:disabled)")];
				(options.find((option) => option.getAttribute("aria-selected") === "true") || (last ? options.at(-1) : options[0]))?.focus();
			}
		}
		function key(event) {
			if (event.isComposing || event.keyCode === 229 || props.disabled) return;
			if (event.key === "ArrowDown" || event.key === "ArrowUp") {
				event.preventDefault();
				toggle(true, event.key === "ArrowUp");
			} else if (event.key === "Enter") {
				event.preventDefault();
				emit("accept", props.modelValue);
			}
		}
		watch(() => props.disabled, (value) => {
			if (value) menu.value?.close();
		});
		__expose({ focus: () => field.value?.focus() });
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "owner",
				ref: owner,
				class: normalizeClass(["app-editable-select", { disabled: __props.disabled }])
			}, [
				createVNode(_sfc_main$29, {
					ref_key: "field",
					ref: field,
					"model-value": __props.modelValue,
					label: __props.label,
					placeholder: __props.placeholder,
					disabled: __props.disabled,
					role: "combobox",
					"aria-autocomplete": "list",
					"aria-expanded": expanded.value,
					"aria-controls": unref(popupId),
					tabindex: "0",
					onKeydown: key,
					"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => emit("update:modelValue", $event))
				}, null, 8, [
					"model-value",
					"label",
					"placeholder",
					"disabled",
					"aria-expanded",
					"aria-controls"
				]),
				createVNode(_sfc_main$34, {
					class: "editable-select-indicator",
					"icon-only": "",
					icon: expanded.value ? "expand_less" : "expand_more",
					label: __props.label,
					disabled: __props.disabled,
					tabindex: "-1",
					onClick: _cache[1] || (_cache[1] = ($event) => toggle())
				}, null, 8, [
					"icon",
					"label",
					"disabled"
				]),
				createVNode(_sfc_main$26, {
					ref_key: "menu",
					ref: menu,
					class: "editable-select-menu",
					"external-trigger": "",
					overlay: "",
					"align-start": "",
					anchor: owner.value,
					label: __props.label,
					width: popupWidth.value,
					disabled: __props.disabled,
					"focus-on-open": false,
					"close-on-select": false,
					onToggle: _cache[2] || (_cache[2] = ($event) => expanded.value = $event.newState === "open")
				}, {
					default: withCtx(() => [createBaseVNode("div", {
						id: unref(popupId),
						role: "listbox",
						"aria-label": __props.label,
						class: "editable-select-options"
					}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.options, (option) => {
						return openBlock(), createBlock(_sfc_main$34, {
							key: option.value,
							role: "option",
							label: option.label,
							"translate-label": false,
							disabled: option.disabled || option.enabled === false,
							"aria-selected": __props.modelValue === option.value,
							onClick: ($event) => choose(option)
						}, null, 8, [
							"label",
							"disabled",
							"aria-selected",
							"onClick"
						]);
					}), 128))], 8, _hoisted_1$12)]),
					_: 1
				}, 8, [
					"anchor",
					"label",
					"width",
					"disabled"
				])
			], 2);
		};
	}
};
//#endregion
//#region src/frame/controls/grid/FrameGrid.vue
var _hoisted_1$11 = ["data-frame", "aria-label"];
var _hoisted_2$5 = ["data-frame"];
var _hoisted_3$3 = ["data-frame"];
var _hoisted_4$2 = ["data-frame"];
var _hoisted_5$2 = ["data-frame"];
var _sfc_main$11 = {
	__name: "FrameGrid",
	props: {
		node: Object,
		source: Array,
		describeCell: Function
	},
	emits: ["event"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const body = ref(null), position = ref({
			x: 0,
			y: 0
		});
		const width = computed(() => Math.max(1, props.node.width - props.node.labelWidth - 16));
		const height = computed(() => Math.max(1, props.node.height - props.node.headerHeight - 16));
		const range = (count, size, extent, offset) => {
			const r = virtualRange(count, size, extent, offset, 1);
			return Array.from({ length: r.last - r.first }, (_, index) => r.first + index);
		};
		const rows = computed(() => range(props.node.rowHeaders.length, props.node.rowHeight, height.value, position.value.y));
		const columns = computed(() => range(props.node.columnHeaders.length, props.node.cellWidth, width.value, position.value.x));
		const totalWidth = computed(() => props.node.columnHeaders.length * props.node.cellWidth);
		const totalHeight = computed(() => props.node.rowHeaders.length * props.node.rowHeight);
		async function focusCell(row, column, name) {
			const el = body.value, n = props.node;
			if (column * n.cellWidth < el.scrollLeft) el.scrollLeft = column * n.cellWidth;
			else if ((column + 1) * n.cellWidth > el.scrollLeft + width.value) el.scrollLeft = (column + 1) * n.cellWidth - width.value;
			if (row * n.rowHeight < el.scrollTop) el.scrollTop = row * n.rowHeight;
			else if ((row + 1) * n.rowHeight > el.scrollTop + height.value) el.scrollTop = (row + 1) * n.rowHeight - height.value;
			position.value = {
				x: el.scrollLeft,
				y: el.scrollTop
			};
			await nextTick();
			el.querySelector("[data-frame=\"" + CSS.escape(name) + "\"]")?.focus();
		}
		__expose({ focusCell });
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "frame-grid",
				"data-frame": __props.node.id,
				role: "grid",
				"aria-label": __props.node.text
			}, [
				createBaseVNode("div", {
					class: "frame-grid-corner",
					style: normalizeStyle({
						width: __props.node.labelWidth + "px",
						height: __props.node.headerHeight + "px"
					})
				}, toDisplayString(__props.node.caption), 5),
				createBaseVNode("div", {
					class: "frame-grid-column-headings",
					style: normalizeStyle({
						left: __props.node.labelWidth + "px",
						width: width.value + "px",
						height: __props.node.headerHeight + "px"
					})
				}, [(openBlock(true), createElementBlock(Fragment, null, renderList(columns.value, (column) => {
					return openBlock(), createElementBlock("span", {
						key: column,
						role: "columnheader",
						"data-frame": __props.node.id + "_column_" + column,
						class: normalizeClass({ "frame-grid-detailed-heading": typeof __props.node.columnHeaders[column] === "object" }),
						style: normalizeStyle({
							left: column * __props.node.cellWidth - position.value.x + "px",
							width: __props.node.cellWidth + "px",
							height: __props.node.headerHeight + "px"
						})
					}, [typeof __props.node.columnHeaders[column] === "object" ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createBaseVNode("b", { "data-frame": __props.node.id + "_column_" + column + "_title" }, toDisplayString(__props.node.columnHeaders[column].label), 9, _hoisted_3$3), createBaseVNode("small", { "data-frame": __props.node.id + "_column_" + column + "_detail" }, toDisplayString(__props.node.columnHeaders[column].detail), 9, _hoisted_4$2)], 64)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [createTextVNode(toDisplayString(__props.node.columnHeaders[column]), 1)], 64))], 14, _hoisted_2$5);
				}), 128))], 4),
				createBaseVNode("div", {
					class: "frame-grid-row-headings",
					style: normalizeStyle({
						top: __props.node.headerHeight + "px",
						width: __props.node.labelWidth + "px",
						height: height.value + "px"
					})
				}, [(openBlock(true), createElementBlock(Fragment, null, renderList(rows.value, (row) => {
					return openBlock(), createElementBlock("div", {
						key: row,
						role: "rowheader",
						"data-frame": __props.node.id + "_row_" + row,
						class: normalizeClass({ "frame-grid-custom-heading": !!__props.node.rowHeaders[row].children }),
						style: normalizeStyle({
							top: row * __props.node.rowHeight - position.value.y + "px",
							width: __props.node.labelWidth + "px",
							height: __props.node.rowHeight + "px"
						})
					}, [__props.node.rowHeaders[row].children ? (openBlock(), createBlock(_sfc_main, {
						key: 0,
						scene: { nodes: __props.node.rowHeaders[row].children },
						onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
					}, null, 8, ["scene"])) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [createBaseVNode("span", { style: normalizeStyle({ fontWeight: __props.node.rowHeaders[row].all ? 600 : 400 }) }, toDisplayString(__props.node.rowHeaders[row].label), 5), createBaseVNode("small", null, toDisplayString(__props.node.rowHeaders[row].detail), 1)], 64))], 14, _hoisted_5$2);
				}), 128))], 4),
				createBaseVNode("div", {
					ref_key: "body",
					ref: body,
					class: "frame-grid-body",
					style: normalizeStyle({
						left: __props.node.labelWidth + "px",
						top: __props.node.headerHeight + "px",
						width: width.value + 16 + "px",
						height: height.value + 16 + "px"
					}),
					onScroll: _cache[2] || (_cache[2] = ($event) => position.value = {
						x: $event.target.scrollLeft,
						y: $event.target.scrollTop
					})
				}, [createBaseVNode("div", { style: normalizeStyle({
					position: "relative",
					width: totalWidth.value + "px",
					height: totalHeight.value + "px"
				}) }, [(openBlock(true), createElementBlock(Fragment, null, renderList(rows.value, (row) => {
					return openBlock(), createElementBlock(Fragment, { key: row }, [(openBlock(true), createElementBlock(Fragment, null, renderList(columns.value, (column) => {
						return openBlock(), createBlock(_sfc_main, {
							key: column,
							class: "frame-grid-cell",
							style: normalizeStyle({
								left: column * __props.node.cellWidth + "px",
								top: row * __props.node.rowHeight + "px",
								width: __props.node.cellWidth + "px",
								height: __props.node.rowHeight + "px"
							}),
							scene: __props.describeCell(__props.node, __props.source?.[row]?.[column] || {}, row, column),
							onEvent: _cache[1] || (_cache[1] = ($event) => emit("event", $event))
						}, null, 8, ["style", "scene"]);
					}), 128))], 64);
				}), 128))], 4)], 36)
			], 8, _hoisted_1$11);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/graph/graph.state.mjs
var clamp = (value, min, max) => Math.max(min, Math.min(max, value));
function initial() {
	return {
		zoom: 1,
		x: -18,
		y: -18,
		world: {
			x: -18,
			y: -18,
			right: 818,
			bottom: 818
		},
		pointer: null,
		pending: null,
		cursor: {
			x: 0,
			y: 0
		},
		touch: null
	};
}
function size(node, style) {
	const height = metrics(style).controlHeight * 2;
	return {
		width: node.kind === "progress" ? height : 200,
		height
	};
}
function position(ui, node) {
	return ui.pointer && ui.pointer.positions && ui.pointer.positions.find((row) => row.identity === node.identity) || {
		identity: node.identity,
		nodeX: Number(node.nodeX) || 0,
		nodeY: Number(node.nodeY) || 0
	};
}
function point(ui, x, y) {
	return {
		x: ui.x + x / ui.zoom,
		y: ui.y + y / ui.zoom
	};
}
function bounds(ui, node, style) {
	const p = position(ui, node);
	return Object.assign({
		x: p.nodeX,
		y: p.nodeY
	}, size(node, style));
}
function include(ui, model, viewport) {
	let world = Object.assign({}, ui.world);
	for (const row of model.nodes || []) {
		const box = bounds(ui, row, model.style);
		world.x = Math.min(world.x, box.x - 18);
		world.y = Math.min(world.y, box.y - 18);
		world.right = Math.max(world.right, box.x + box.width + 100);
		world.bottom = Math.max(world.bottom, box.y + box.height + 100);
	}
	world.right = Math.max(world.right, ui.x + viewport.width / ui.zoom + 18);
	world.bottom = Math.max(world.bottom, ui.y + viewport.height / ui.zoom + 18);
	return Object.assign({}, ui, { world });
}
function pan(ui, x, y, viewport, expand) {
	const world = Object.assign({}, ui.world);
	if (expand) {
		world.x = Math.min(world.x, x - 100);
		world.y = Math.min(world.y, y - 100);
		world.right = Math.max(world.right, x + viewport.width / ui.zoom + 100);
		world.bottom = Math.max(world.bottom, y + viewport.height / ui.zoom + 100);
	}
	return Object.assign({}, ui, {
		world,
		x: clamp(x, world.x, Math.max(world.x, world.right - viewport.width / ui.zoom)),
		y: clamp(y, world.y, Math.max(world.y, world.bottom - viewport.height / ui.zoom))
	});
}
function zoom(ui, value, x, y, viewport) {
	const anchor = point(ui, x, y), next = Object.assign({}, ui, { zoom: clamp(value, .4, 2) });
	return pan(next, anchor.x - x / next.zoom, anchor.y - y / next.zoom, viewport, true);
}
function selection(model, identity, modifiers, dragging) {
	let names = (model.selectedNodes || []).slice();
	const index = names.indexOf(identity);
	if (dragging && index >= 0) return names;
	if (modifiers.control) {
		if (index >= 0) names.splice(index, 1);
		else names.push(identity);
	} else if (modifiers.shift) {
		if (index < 0) names.push(identity);
	} else names = [identity];
	return names;
}
function selectionRect(ui) {
	const drag = ui.pointer;
	if (!drag || drag.kind !== "selection" || !drag.active) return null;
	return {
		x: Math.min(drag.start.x, ui.cursor.x),
		y: Math.min(drag.start.y, ui.cursor.y),
		width: Math.abs(drag.start.x - ui.cursor.x),
		height: Math.abs(drag.start.y - ui.cursor.y)
	};
}
function curves(ui, model) {
	const nodes = model.nodes || [], rows = [];
	for (let index = 0; index < (model.edges || []).length; index++) {
		const edge = model.edges[index], from = nodes.find((row) => row.identity === edge.from), to = nodes.find((row) => row.identity === edge.to);
		if (!from || !to) continue;
		const a = bounds(ui, from, model.style), b = bounds(ui, to, model.style);
		const offset = model.edges.some((row) => row.from === edge.to && row.to === edge.from) ? String(edge.from) < String(edge.to) ? -24 : 24 : 0;
		rows.push(curve(a.x + a.width, a.y + a.height / 2 + offset, b.x, b.y + b.height / 2 + offset, Object.assign({ index }, edge, { color: edge.color || from.color || "action" })));
	}
	if (ui.pending) {
		const node = nodes.find((row) => row.identity === ui.pending.identity);
		if (node) {
			const box = bounds(ui, node, model.style), port = {
				x: box.x + (ui.pending.input ? 0 : box.width),
				y: box.y + box.height / 2
			};
			const a = ui.pending.input ? ui.cursor : port, b = ui.pending.input ? port : ui.cursor;
			rows.push(curve(a.x, a.y, b.x, b.y, {
				index: -1,
				pending: true,
				color: node.color || "action"
			}));
		}
	}
	return rows;
}
function curve(x1, y1, x2, y2, data) {
	return Object.assign({
		x1,
		y1,
		x2,
		y2,
		bend: Math.max(70, Math.abs(x2 - x1) / 2)
	}, data);
}
function curvePoint(edge, t) {
	const u = 1 - t;
	return {
		x: u * u * u * edge.x1 + 3 * u * u * t * (edge.x1 + edge.bend) + 3 * u * t * t * (edge.x2 - edge.bend) + t * t * t * edge.x2,
		y: u * u * u * edge.y1 + 3 * u * u * t * edge.y1 + 3 * u * t * t * edge.y2 + t * t * t * edge.y2
	};
}
function contains(rect, p) {
	return p.x >= rect.x && p.y >= rect.y && p.x <= rect.x + rect.width && p.y <= rect.y + rect.height;
}
function hit$1(ui, model, p) {
	for (const row of (model.nodes || []).slice().reverse()) {
		const box = bounds(ui, row, model.style), port = {
			y: box.y + box.height / 2 - 18,
			width: 36,
			height: 36
		};
		if (!model.readOnly && !row.referenceOnly) {
			if (contains(Object.assign({ x: box.x - 18 }, port), p)) return {
				kind: "port",
				identity: row.identity,
				input: true
			};
			if (contains(Object.assign({ x: box.x + box.width - 18 }, port), p)) return {
				kind: "port",
				identity: row.identity,
				input: false
			};
		}
		if (contains(box, p)) return {
			kind: "node",
			identity: row.identity
		};
	}
	for (const edge of curves(ui, model)) {
		if (edge.pending) continue;
		for (let t = 0; t <= 1; t += .025) {
			const q = curvePoint(edge, t);
			if (Math.hypot(q.x - p.x, q.y - p.y) <= 10 / ui.zoom) return {
				kind: "edge",
				index: edge.index
			};
		}
	}
	return { kind: "selection" };
}
function selectedCommand(names, primary) {
	return {
		type: "selectNodes",
		identities: names,
		primary: names.indexOf(primary) >= 0 ? primary : names[names.length - 1] || ""
	};
}
function port(ui, target, commands) {
	if (ui.pending && ui.pending.input !== target.input && ui.pending.identity !== target.identity) {
		commands.push({
			type: "connect",
			from: target.input ? ui.pending.identity : target.identity,
			to: target.input ? target.identity : ui.pending.identity
		});
		return Object.assign({}, ui, { pending: null });
	}
	return Object.assign({}, ui, { pending: ui.pending && ui.pending.identity === target.identity && ui.pending.input === target.input ? null : target });
}
function click(ui, target, event, model, commands) {
	if (target.kind === "port" && !model.readOnly) return port(ui, target, commands);
	if (model.selectionEnabled === false) return ui;
	if (target.kind === "node") commands.push(selectedCommand(selection(model, target.identity, event, false), target.identity));
	else if (target.kind === "edge") commands.push({
		type: "selectEdge",
		index: target.index
	});
	else if (!event.control && !event.shift) commands.push({ type: "clear" });
	return Object.assign({}, ui, { pending: null });
}
function reduce(previous, event, model, viewport) {
	let ui = include(previous, model, viewport);
	const commands = [];
	const result = () => ({
		ui,
		commands
	});
	if (event.type === "cancel") {
		ui = Object.assign({}, ui, {
			pointer: null,
			pending: null,
			touch: null
		});
		return result();
	}
	if (event.type === "scroll") {
		ui = pan(ui, ui.world.x + event.x / ui.zoom, ui.world.y + event.y / ui.zoom, viewport, false);
		return result();
	}
	if (event.type === "reset") {
		ui = include(initial(), model, viewport);
		return result();
	}
	if (event.type === "zoom") {
		if (!ui.pointer) ui = zoom(ui, event.value, event.x === void 0 ? viewport.width / 2 : event.x, event.y === void 0 ? viewport.height / 2 : event.y, viewport);
		return result();
	}
	if (event.type === "reveal") {
		const rows = (model.nodes || []).filter((row) => (event.identities || model.selectedNodes || []).indexOf(row.identity) >= 0);
		if (rows.length) {
			const boxes = rows.map((row) => bounds(ui, row, model.style)), left = Math.min.apply(null, boxes.map((row) => row.x)), right = Math.max.apply(null, boxes.map((row) => row.x + row.width)), top = Math.min.apply(null, boxes.map((row) => row.y)), bottom = Math.max.apply(null, boxes.map((row) => row.y + row.height));
			ui = pan(ui, (left + right) / 2 - viewport.width / ui.zoom / 2, (top + bottom) / 2 - viewport.height / ui.zoom / 2, viewport, true);
		}
		return result();
	}
	if (event.type === "key") {
		if (event.key === "Escape") {
			if (ui.pointer || ui.pending || ui.touch) ui = Object.assign({}, ui, {
				pointer: null,
				pending: null,
				touch: null
			});
			else if (model.selectionEnabled !== false) commands.push({ type: "clear" });
		} else if (event.control && event.key.toLowerCase() === "s" && !model.readOnly) {
			if (!event.repeat) commands.push({ type: "save" });
		} else if (!event.control && !event.alt) {
			if (event.key === "+" || event.key === "=") return reduce(ui, {
				type: "zoom",
				value: ui.zoom + .1
			}, model, viewport);
			if (event.key === "-") return reduce(ui, {
				type: "zoom",
				value: ui.zoom - .1
			}, model, viewport);
			if (event.key === "Home") return reduce(ui, { type: "reset" }, model, viewport);
			if (event.key.toLowerCase() === "f") return reduce(ui, { type: "reveal" }, model, viewport);
			if (event.key === "Delete" && !model.readOnly && !event.repeat) commands.push({ type: "remove" });
			const delta = {
				ArrowLeft: [-10, 0],
				ArrowRight: [10, 0],
				ArrowUp: [0, -10],
				ArrowDown: [0, 10]
			}[event.key];
			if (delta && !event.shift && !model.readOnly) commands.push({
				type: "moveNodes",
				positions: (model.nodes || []).filter((row) => !row.referenceOnly && (model.selectedNodes || []).indexOf(row.identity) >= 0).map((row) => ({
					identity: row.identity,
					nodeX: (Number(row.nodeX) || 0) + delta[0],
					nodeY: (Number(row.nodeY) || 0) + delta[1]
				}))
			});
		}
		return result();
	}
	if (event.type === "activate") {
		ui = click(ui, event.target, event, model, commands);
		return result();
	}
	if (event.type === "touch") {
		const points = event.points || [];
		if (points.length >= 2) {
			const middle = {
				x: (points[0].x + points[1].x) / 2,
				y: (points[0].y + points[1].y) / 2
			}, distance = Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
			if (ui.touch && ui.touch.pinch) {
				const scale = clamp(ui.touch.zoom * distance / Math.max(1, ui.touch.distance), .4, 2);
				ui = pan(Object.assign({}, ui, { zoom: scale }), ui.touch.anchor.x - middle.x / scale, ui.touch.anchor.y - middle.y / scale, viewport, true);
			} else ui = Object.assign({}, ui, {
				pointer: null,
				touch: {
					pinch: true,
					zoom: ui.zoom,
					distance,
					anchor: point(ui, middle.x, middle.y)
				}
			});
			return result();
		}
		if (ui.touch && ui.touch.pinch) {
			if (!points.length) ui = Object.assign({}, ui, { touch: null });
			return result();
		}
		if (!points.length) {
			const p = ui.pointer;
			return reduce(ui, p ? {
				type: "up",
				x: p.lastX,
				y: p.lastY
			} : { type: "cancel" }, model, viewport);
		}
		const p = points[0];
		return reduce(ui, {
			type: ui.pointer ? "move" : "down",
			x: p.x,
			y: p.y,
			touch: true
		}, model, viewport);
	}
	if (event.type === "down") {
		if (ui.pointer) return result();
		const start = point(ui, event.x, event.y), target = event.button === 1 ? { kind: "pan" } : hit$1(ui, model, start);
		ui = Object.assign({}, ui, {
			cursor: start,
			pointer: Object.assign({}, target, {
				start,
				x: event.x,
				y: event.y,
				lastX: event.x,
				lastY: event.y,
				originX: ui.x,
				originY: ui.y,
				control: !!event.control,
				shift: !!event.shift,
				touch: !!event.touch,
				active: false
			})
		});
		return result();
	}
	if (event.type === "tick" && ui.pointer && ui.pointer.active && ui.pointer.kind === "node") {
		const drag = ui.pointer, margin = 36, dt = Math.min(.05, event.seconds);
		const speed = (p, extent) => p < margin ? -Math.min(margin, margin - p) : p > extent - margin ? Math.min(margin, p - extent + margin) : 0;
		const dx = speed(drag.lastX, viewport.width), dy = speed(drag.lastY, viewport.height);
		if (!dx && !dy) return result();
		ui = pan(ui, ui.x + dx * dt * 10 / ui.zoom, ui.y + dy * dt * 10 / ui.zoom, viewport, true);
		return reduce(ui, {
			type: "move",
			x: drag.lastX,
			y: drag.lastY
		}, model, viewport);
	}
	if (event.type === "move") {
		ui = Object.assign({}, ui, { cursor: point(ui, event.x, event.y) });
		if (!ui.pointer) return result();
		let drag = Object.assign({}, ui.pointer, {
			lastX: event.x,
			lastY: event.y
		});
		if (!drag.active && Math.hypot(event.x - drag.x, event.y - drag.y) >= 8) {
			drag.active = true;
			const draggedNode = (model.nodes || []).find((row) => row.identity === drag.identity);
			if (drag.kind === "node" && !model.readOnly && draggedNode && !draggedNode.referenceOnly) {
				const names = selection(model, drag.identity, drag, true);
				commands.push(selectedCommand(names, drag.identity));
				drag.original = model.nodes.filter((row) => !row.referenceOnly && names.indexOf(row.identity) >= 0).map((row) => Object.assign({}, position(ui, row)));
			} else if (drag.touch) drag.kind = "pan";
			if (drag.kind === "port") ui = Object.assign({}, ui, { pending: {
				identity: drag.identity,
				input: drag.input
			} });
		}
		if (drag.active && drag.kind === "pan") ui = pan(ui, drag.originX + (drag.x - event.x) / ui.zoom, drag.originY + (drag.y - event.y) / ui.zoom, viewport, true);
		else if (drag.active && drag.original) drag.positions = drag.original.map((row) => ({
			identity: row.identity,
			nodeX: row.nodeX + ui.cursor.x - drag.start.x,
			nodeY: row.nodeY + ui.cursor.y - drag.start.y
		}));
		ui = include(Object.assign({}, ui, { pointer: drag }), model, viewport);
		return result();
	}
	if (event.type === "up") {
		const drag = ui.pointer;
		if (!drag) return result();
		if (drag.active) {
			if (drag.positions) commands.push({
				type: "moveNodes",
				positions: drag.positions
			});
			else if (drag.kind === "selection" && model.selectionEnabled !== false) {
				const rect = selectionRect(ui), names = (drag.control || drag.shift ? model.selectedNodes || [] : []).slice();
				for (const row of model.nodes || []) {
					const box = bounds(ui, row, model.style);
					if (rect && box.x + box.width >= rect.x && box.x <= rect.x + rect.width && box.y + box.height >= rect.y && box.y <= rect.y + rect.height && names.indexOf(row.identity) < 0) names.push(row.identity);
				}
				commands.push(selectedCommand(names, names[0]));
			} else if (drag.kind === "port" && !model.readOnly) {
				const target = hit$1(ui, model, point(ui, event.x, event.y));
				if (target.kind === "port" && target.input !== drag.input && target.identity !== drag.identity) {
					commands.push({
						type: "connect",
						from: target.input ? drag.identity : target.identity,
						to: target.input ? target.identity : drag.identity
					});
					ui = Object.assign({}, ui, { pending: null });
				}
			}
		} else if (drag.kind !== "pan") ui = click(ui, drag, drag, model, commands);
		ui = Object.assign({}, ui, { pointer: null });
		return result();
	}
	return result();
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/graph/graph.ui.mjs
function toolbarLayout(definition) {
	const width = Math.max(0, definition.width - (definition.toolbarRightInset || 0));
	if (definition.toolbar === false || width < 36) return {
		height: 0,
		columns: 0,
		label: false
	};
	const label = width >= 202;
	const columns = label ? 4 : Math.max(1, Math.min(4, Math.floor((width + 2) / 38)));
	return {
		label,
		columns,
		height: Math.ceil(4 / columns) * 38 - 2
	};
}
function viewport(definition) {
	const toolbar = toolbarLayout(definition);
	const top = toolbar.height ? toolbar.height + 6 : 0;
	return {
		x: 0,
		y: top,
		width: Math.max(1, definition.width - 16),
		height: Math.max(1, definition.height - top - 16)
	};
}
function toolbar$1(definition, ui, language) {
	const layout = toolbarLayout(definition);
	if (!layout.columns) return { nodes: [] };
	const tr = (text) => translate(text, language), width = definition.width, actions = [
		[
			"graphZoomOut",
			"Zoom out",
			"zoom-out",
			{
				type: "zoom",
				value: ui.zoom - .1
			}
		],
		[
			"graphZoomIn",
			"Zoom in",
			"zoom-in",
			{
				type: "zoom",
				value: ui.zoom + .1
			}
		],
		[
			"graphReset",
			"Reset view",
			"refresh",
			{ type: "reset" }
		],
		[
			"graphReveal",
			"Center selection",
			"fit-width",
			{ type: "reveal" }
		]
	];
	const nodes = layout.label ? [label("graphZoomLabel", rect(0, 0, 50, 36), Math.round(ui.zoom * 100) + "%", muted)] : [];
	actions.forEach((action, index) => nodes.push(node("Button", action[0], rect((layout.label ? 52 : 0) + index % layout.columns * 38, Math.floor(index / layout.columns) * 38, 36, 36), {
		text: tr(action[1]),
		icon: action[2],
		iconOnly: true,
		action: action[3]
	})));
	if (width > 440 && definition.help !== false) nodes.push(label("graphHelp", rect(214, 0, width - 218, 36), tr(definition.readOnly ? "Wheel: zoom · Middle button: pan" : "Drag: move · Ctrl/Shift: select · F: center"), { color: "secondaryText" }));
	return { nodes };
}
var tint = (base, accent, amount) => ({ mix: [
	base,
	accent,
	amount
] });
function describe$1(definition, ui, language) {
	const tr = (text) => translate(text, language), nodes = [], selected = definition.selectedNodes || [];
	for (const edge of curves(ui, definition)) {
		if (edge.pending) continue;
		const p = curvePoint(edge, .6), title = (edge.label ? edge.label + " · " : "") + edge.from + " → " + edge.to;
		nodes.push(node("Action", "graphEdge_" + edge.index, rect(p.x - ui.world.x - 18, p.y - ui.world.y - 18, 36, 36), {
			text: title,
			enabled: definition.selectionEnabled !== false,
			selected: definition.selectedEdge === edge.index,
			normalColor: "transparent",
			selectedColor: "transparent",
			action: {
				type: "activate",
				target: {
					kind: "edge",
					index: edge.index
				}
			}
		}));
	}
	for (const record of definition.nodes || []) {
		const box = bounds(ui, record, definition.style), accent = record.kind === "missing" ? "error" : record.color || "action", circular = record.kind === "progress", chosen = selected.indexOf(record.identity) >= 0;
		const content = [node("Box", "graphNodeSurface_" + record.identity, rect(0, 0, box.width, box.height), {
			background: tint("surfaceContainer", accent, chosen ? .26 : .12),
			border: chosen ? accent : tint("outlineVariant", accent, .5),
			borderWidth: chosen ? 2 : 1,
			radius: circular ? box.width / 2 : metrics(definition.style).itemRadius
		})];
		content.push(label("graphNodeTitle_" + record.identity, rect(circular ? 8 : 22, circular ? (box.height - 28) / 2 : 12 + (box.height - 72) / 2, box.width - (circular ? 16 : 44), 28), record.label || record.identity, {
			weight: 600,
			align: circular ? "center" : "left"
		}));
		if (!circular) content.push(label("graphNodeKind_" + record.identity, rect(22, 44 + (box.height - 72) / 2, box.width - 44, 18), record.pendingCreation ? tr("New · many-to-many") : record.kind === "instance" ? "many-to-many" : record.kind === "missing" ? tr("Missing process") : record.kind || "", muted));
		nodes.push(node("Action", "graphNode_" + record.identity, rect(box.x - ui.world.x, box.y - ui.world.y, box.width, box.height), {
			text: record.label || record.identity,
			role: "option",
			selected: chosen,
			enabled: definition.selectionEnabled !== false,
			normalColor: "transparent",
			selectedColor: "transparent",
			children: content,
			action: {
				type: "activate",
				target: {
					kind: "node",
					identity: record.identity
				}
			}
		}));
		if (!definition.readOnly && !record.referenceOnly) for (const input of [true, false]) {
			const active = ui.pending && (ui.pending.input === input ? ui.pending.identity === record.identity : ui.pending.identity !== record.identity);
			const children = [node("Box", "graphPortSurface_" + (input ? "in_" : "out_") + record.identity, rect(12, 12, 12, 12), {
				radius: 6,
				border: accent,
				borderWidth: 2,
				background: active || !input ? accent : "workspace"
			})];
			nodes.push(node("Action", (input ? "graphInput_" : "graphOutput_") + record.identity, rect(box.x - ui.world.x + (input ? -18 : box.width - 18), box.y - ui.world.y + 18, 36, 36), {
				text: tr(input ? "Input — connect here" : "Output — connect here"),
				normalColor: "transparent",
				selectedColor: "transparent",
				children,
				action: {
					type: "activate",
					target: {
						kind: "port",
						identity: record.identity,
						input
					}
				}
			}));
		}
	}
	return { nodes };
}
function paint$1(context, definition, ui, viewportSize, color, selection) {
	context.clearRect(0, 0, viewportSize.width, viewportSize.height);
	context.save();
	context.scale(ui.zoom, ui.zoom);
	context.translate(-ui.x, -ui.y);
	for (const edge of curves(ui, definition)) {
		context.strokeStyle = color(definition.selectedEdge === edge.index ? "primaryText" : edge.color);
		context.lineWidth = definition.selectedEdge === edge.index ? 3.5 : 2.5;
		context.beginPath();
		context.moveTo(edge.x1, edge.y1);
		context.bezierCurveTo(edge.x1 + edge.bend, edge.y1, edge.x2 - edge.bend, edge.y2, edge.x2, edge.y2);
		context.stroke();
		const p = curvePoint(edge, .6), before = curvePoint(edge, .59), after = curvePoint(edge, .61), angle = Math.atan2(after.y - before.y, after.x - before.x);
		context.save();
		context.translate(p.x, p.y);
		context.rotate(angle);
		context.fillStyle = context.strokeStyle;
		context.beginPath();
		context.moveTo(-6, -5);
		context.lineTo(6, 0);
		context.lineTo(-6, 5);
		context.closePath();
		context.fill();
		context.restore();
	}
	if (selection) {
		context.fillStyle = color(tint("workspace", "action", .14));
		context.strokeStyle = color("action");
		context.lineWidth = 1 / ui.zoom;
		context.fillRect(selection.x, selection.y, selection.width, selection.height);
		context.strokeRect(selection.x, selection.y, selection.width, selection.height);
	}
	context.restore();
}
//#endregion
//#region src/frame/controls/graph/FrameGraph.vue
var _hoisted_1$10 = ["data-frame", "aria-label"];
var _hoisted_2$4 = ["aria-label"];
var FrameGraph_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FrameGraph",
	props: { node: {
		type: Object,
		required: true
	} },
	emits: ["event"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props, emit = __emit;
		const host = ref(null), canvas = ref(null), scroll = ref(null), ui = ref(initial()), touches = /* @__PURE__ */ new Map();
		const viewport$1 = computed(() => viewport(props.node)), scene = computed(() => describe$1(props.node, ui.value, props.node.language || "en"));
		const toolbar = computed(() => toolbar$1(props.node, ui.value, props.node.language || "en"));
		let frame = 0, last = 0, observer;
		function color(role) {
			if (role?.mix) {
				const [base, tint, amount] = role.mix;
				return `color-mix(in srgb, ${color(base)} ${(1 - amount) * 100}%, ${color(tint)} ${amount * 100}%)`;
			}
			return cssRoles[role] ? getComputedStyle(host.value).getPropertyValue(cssRoles[role]).trim() : role || "transparent";
		}
		function paint() {
			if (!canvas.value) return;
			const ratio = devicePixelRatio || 1, w = viewport$1.value.width, h = viewport$1.value.height, c = canvas.value;
			if (c.width !== Math.round(w * ratio) || c.height !== Math.round(h * ratio)) {
				c.width = Math.round(w * ratio);
				c.height = Math.round(h * ratio);
			}
			const context = c.getContext("2d");
			context.setTransform(ratio, 0, 0, ratio, 0, 0);
			paint$1(context, props.node, ui.value, viewport$1.value, color, selectionRect(ui.value));
		}
		function dispatch(event) {
			const result = reduce(ui.value, event, props.node, viewport$1.value);
			ui.value = result.ui;
			for (const command of result.commands) emit("event", {
				...props.node.action || { type: "graph" },
				value: command
			});
		}
		function modifier(event) {
			return {
				control: event.ctrlKey || event.metaKey,
				shift: event.shiftKey,
				alt: event.altKey
			};
		}
		function pointer(event, type) {
			if (event.button > 1 && type === "down") return;
			if (type === "move" && event.pointerType !== "touch" && !ui.value.pointer && !ui.value.pending) return;
			const bounds = event.currentTarget.getBoundingClientRect(), p = {
				x: event.clientX - bounds.left,
				y: event.clientY - bounds.top
			};
			if (event.pointerType === "touch") {
				if (type === "down" || type === "move") {
					if (type === "down" || touches.has(event.pointerId)) touches.set(event.pointerId, p);
				} else touches.delete(event.pointerId);
				dispatch(type === "cancel" ? { type: "cancel" } : {
					type: "touch",
					points: [...touches.values()]
				});
			} else dispatch({
				type,
				...p,
				button: event.button,
				...modifier(event)
			});
			if (type === "down") {
				event.currentTarget.focus({ preventScroll: true });
				event.currentTarget.setPointerCapture(event.pointerId);
			}
			if (type === "up" || type === "cancel") {
				if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
			}
			event.preventDefault();
		}
		function wheel(event) {
			const bounds = event.currentTarget.getBoundingClientRect();
			dispatch({
				type: "zoom",
				value: ui.value.zoom * (event.deltaY < 0 ? 1.1 : 1 / 1.1),
				x: event.clientX - bounds.left,
				y: event.clientY - bounds.top
			});
			event.preventDefault();
		}
		function key(event) {
			if (![
				"Escape",
				"Delete",
				"Home",
				"+",
				"=",
				"-",
				"f",
				"F",
				"ArrowLeft",
				"ArrowRight",
				"ArrowUp",
				"ArrowDown"
			].includes(event.key) && !((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s")) return;
			event.preventDefault();
			event.stopPropagation();
			dispatch({
				type: "key",
				key: event.key,
				repeat: event.repeat,
				...modifier(event)
			});
		}
		function cancel() {
			touches.clear();
			dispatch({ type: "cancel" });
		}
		function animate(now) {
			if (last && ui.value.pointer?.active && ui.value.pointer.kind === "node") dispatch({
				type: "tick",
				seconds: (now - last) / 1e3
			});
			last = now;
			frame = requestAnimationFrame(animate);
		}
		watch(() => props.node, () => {
			ui.value = include(ui.value, props.node, viewport$1.value);
		}, { immediate: true });
		watch(() => props.node.resetKey || props.node.center || props.node.id, () => {
			ui.value = include(initial(), props.node, viewport$1.value);
		});
		watch(() => props.node.visible, (visible) => {
			if (visible === false) cancel();
		});
		watch([ui, viewport$1], async () => {
			await nextTick();
			if (scroll.value) {
				const x = (ui.value.x - ui.value.world.x) * ui.value.zoom, y = (ui.value.y - ui.value.world.y) * ui.value.zoom;
				if (Math.abs(scroll.value.scrollLeft - x) > .6) scroll.value.scrollLeft = x;
				if (Math.abs(scroll.value.scrollTop - y) > .6) scroll.value.scrollTop = y;
			}
			paint();
		}, { flush: "post" });
		onMounted(() => {
			observer = new MutationObserver(paint);
			for (let element = host.value; element; element = element.parentElement) observer.observe(element, {
				attributes: true,
				attributeFilter: [
					"data-theme",
					"style",
					"class"
				]
			});
			window.addEventListener("blur", cancel);
			paint();
			frame = requestAnimationFrame(animate);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(frame);
			window.removeEventListener("blur", cancel);
		});
		function insertionPoint() {
			return {
				x: ui.value.x + viewport$1.value.width / ui.value.zoom / 2 - 100,
				y: ui.value.y + viewport$1.value.height / ui.value.zoom / 2 - 36
			};
		}
		__expose({
			dispatch,
			insertionPoint,
			ui
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "frame-graph",
				"data-frame": __props.node.id,
				"aria-label": __props.node.label,
				role: "group"
			}, [createVNode(_sfc_main, {
				class: "graph-toolbar",
				style: normalizeStyle({ height: Math.max(0, viewport$1.value.y - 4) + "px" }),
				scene: toolbar.value,
				onEvent: dispatch
			}, null, 8, ["style", "scene"]), createBaseVNode("div", {
				class: "graph-area",
				style: normalizeStyle({
					top: viewport$1.value.y + "px",
					width: __props.node.width + "px",
					height: viewport$1.value.height + 16 + "px"
				})
			}, [createBaseVNode("div", {
				ref_key: "scroll",
				ref: scroll,
				class: "graph-scroll",
				style: normalizeStyle({
					width: viewport$1.value.width + 12 + "px",
					height: viewport$1.value.height + 12 + "px"
				}),
				onScroll: _cache[0] || (_cache[0] = ($event) => dispatch({
					type: "scroll",
					x: $event.target.scrollLeft,
					y: $event.target.scrollTop
				}))
			}, [createBaseVNode("div", { style: normalizeStyle({
				width: (ui.value.world.right - ui.value.world.x) * ui.value.zoom + "px",
				height: (ui.value.world.bottom - ui.value.world.y) * ui.value.zoom + "px"
			}) }, null, 4)], 36), createBaseVNode("div", {
				class: "graph-camera",
				"data-graph-camera": "",
				tabindex: "0",
				style: normalizeStyle({
					width: viewport$1.value.width + "px",
					height: viewport$1.value.height + "px"
				}),
				"aria-label": __props.node.label,
				onPointerdown: _cache[1] || (_cache[1] = ($event) => pointer($event, "down")),
				onPointermove: _cache[2] || (_cache[2] = ($event) => pointer($event, "move")),
				onPointerup: _cache[3] || (_cache[3] = ($event) => pointer($event, "up")),
				onPointercancel: _cache[4] || (_cache[4] = ($event) => pointer($event, "cancel")),
				onLostpointercapture: _cache[5] || (_cache[5] = ($event) => ui.value.pointer && cancel()),
				onWheel: wheel,
				onKeydown: key,
				onClickCapture: _cache[6] || (_cache[6] = ($event) => {
					if ($event.detail) {
						$event.preventDefault();
						$event.stopPropagation();
					}
				})
			}, [createBaseVNode("canvas", {
				ref_key: "canvas",
				ref: canvas,
				style: normalizeStyle({
					width: viewport$1.value.width + "px",
					height: viewport$1.value.height + "px"
				}),
				"aria-hidden": "true"
			}, null, 4), createVNode(_sfc_main, {
				class: "graph-plane",
				scene: scene.value,
				style: normalizeStyle({
					width: ui.value.world.right - ui.value.world.x + "px",
					height: ui.value.world.bottom - ui.value.world.y + "px",
					transform: `translate(${-(ui.value.x - ui.value.world.x) * ui.value.zoom}px,${-(ui.value.y - ui.value.world.y) * ui.value.zoom}px) scale(${ui.value.zoom})`
				}),
				onEvent: dispatch
			}, null, 8, ["scene", "style"])], 44, _hoisted_2$4)], 4)], 8, _hoisted_1$10);
		};
	}
}, [["__scopeId", "data-v-6646f71f"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/charts/chart.ui.mjs
var palette = [
	"action",
	"cyan",
	"violet",
	"green",
	"yellow",
	"red"
];
function number(value, language) {
	if (typeof value !== "number" || !Number.isFinite(value)) return "—";
	const rounded = Number(value.toFixed(2));
	return String(rounded).replace(/\B(?=(\d{3})+(?!\d))/g, " ").replace(".", language === "ru" ? "," : ".");
}
function axisLabel(text, language) {
	const date = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(text);
	if (!date) return text;
	const month = (language === "ru" ? [
		"янв",
		"фев",
		"мар",
		"апр",
		"май",
		"июн",
		"июл",
		"авг",
		"сен",
		"окт",
		"ноя",
		"дек"
	] : [
		"Jan",
		"Feb",
		"Mar",
		"Apr",
		"May",
		"Jun",
		"Jul",
		"Aug",
		"Sep",
		"Oct",
		"Nov",
		"Dec"
	])[Number(date[2]) - 1];
	return month ? date[3] ? Number(date[3]) + " " + month : month + " " + date[1] : text;
}
function geometry(data, width, height) {
	const values = data.values.map((value) => typeof value === "number" && Number.isFinite(value) ? value : null);
	const type = data.type || "bar";
	if (type === "donut") {
		const side = width >= 380;
		const size = Math.max(0, Math.min(side ? width * .48 : width, side ? height : height * .6));
		const cx = side ? size / 2 : width / 2, cy = size / 2;
		const radius = Math.max(0, size / 2 - 10), inner = radius * .74;
		const valid = values.every((value) => value == null || value >= 0);
		const total = valid ? values.reduce((sum, value) => sum + (value || 0), 0) : 0;
		let angle = -Math.PI / 2;
		return {
			type,
			width,
			height,
			values,
			valid,
			total,
			cx,
			cy,
			radius,
			inner,
			marks: values.map((value, index) => {
				const start = angle;
				angle += total ? (value || 0) / total * Math.PI * 2 : 0;
				return {
					index,
					value,
					start,
					end: angle
				};
			}),
			legend: side ? rect(size + 18, 8, width - size - 18, height - 16) : rect(0, size + 12, width, height - size - 12)
		};
	}
	const finite = values.filter((value) => value != null);
	const low = Math.min(0, ...finite), high = Math.max(0, ...finite);
	const span = high - low || 1;
	const magnitude = Math.pow(10, Math.floor(Math.log(span / 4) / Math.LN10));
	const fraction = span / 4 / magnitude;
	const step = (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * magnitude;
	const minimum = Math.floor(low / step) * step;
	const maximum = high === low ? minimum + step * 4 : Math.ceil(high / step) * step;
	const plot = rect(width < 220 ? 36 : 48, 12, width - (width < 220 ? 44 : 56), height - 46);
	const y = (value) => plot.y + plot.height - (value - minimum) / (maximum - minimum) * plot.height;
	const stride = plot.width / Math.max(1, values.length);
	const marks = values.map((value, index) => ({
		index,
		value,
		x: plot.x + stride * (index + .5),
		y: value == null ? null : y(value),
		width: Math.max(1, Math.min(42, stride * .62)),
		zero: y(0)
	}));
	const ticks = [];
	for (let value = minimum; value <= maximum + step / 2; value += step) ticks.push({
		value: Math.abs(value) < step / 100 ? 0 : value,
		y: y(value)
	});
	return {
		type,
		width,
		height,
		values,
		marks,
		plot,
		ticks,
		stride
	};
}
function describe(data, id, width, height, language) {
	const tr = (text) => translate(text, language);
	const g = geometry(data, width, height);
	const nodes = [node("Chart", id + "_plot", rect(0, 0, width, height), {
		chart: g,
		language,
		labels: data.labels,
		text: data.labels.map((text, i) => text + ": " + number(data.values[i], language)).join("; ")
	})];
	if (g.type === "donut") {
		nodes.push(label(id + "_total", rect(g.cx - g.inner, g.cy - 26, g.inner * 2, 44), g.valid ? number(g.total, language) : "—", {
			fontRole: "headline",
			weight: 600,
			align: "center"
		}));
		nodes.push(label(id + "_totalLabel", rect(g.cx - g.inner, g.cy + 20, g.inner * 2, 22), tr("Total"), {
			color: "secondaryText",
			fontRole: "caption",
			align: "center"
		}));
		const children = [];
		data.labels.forEach((text, index) => {
			const y = index * 34;
			children.push(node("Box", id + "_key_" + index, rect(0, y + 11, 8, 8), {
				background: palette[index % palette.length],
				radius: 4
			}));
			children.push(label(id + "_legend_" + index, rect(18, y, Math.max(0, g.legend.width - 82), 30), text, {
				maxLines: 1,
				fontRole: "secondary"
			}));
			children.push(label(id + "_legendValue_" + index, rect(Math.max(18, g.legend.width - 60), y, 60, 30), number(data.values[index], language), {
				align: "right",
				weight: 600,
				fontRole: "secondary"
			}));
		});
		nodes.push(node("Scroll", id + "_legend", g.legend, {
			contentHeight: data.labels.length * 34,
			children
		}));
		if (!g.valid) nodes.push(label(id + "_invalid", rect(0, 0, width, 28), tr("Donut charts require non-negative values"), {
			color: "error",
			maxLines: 1
		}));
	} else {
		for (const [index, tick] of g.ticks.entries()) nodes.push(label(id + "_tick_" + index, rect(0, tick.y - 9, g.plot.x - 9, 18), number(tick.value, language), {
			fontRole: "caption",
			color: "secondaryText",
			align: "right"
		}));
		const every = Math.max(1, Math.ceil(data.labels.length / Math.max(1, Math.floor(g.plot.width / 84))));
		for (const mark of g.marks) if (mark.index % every === 0 || mark.index === g.marks.length - 1) {
			const w = Math.min(82, g.plot.width);
			const x = Math.max(g.plot.x, Math.min(g.plot.x + g.plot.width - w, mark.x - w / 2));
			if (mark.index === g.marks.length - 1 && mark.index % every && mark.index % every < every / 2) continue;
			nodes.push(label(id + "_axisLabel_" + mark.index, rect(x, height - 28, w, 24), axisLabel(data.labels[mark.index], language), {
				fontRole: "caption",
				color: "secondaryText",
				maxLines: 1,
				align: "center"
			}));
		}
	}
	return { nodes };
}
function hit(g, x, y) {
	if (g.type === "donut") {
		const radius = Math.hypot(x - g.cx, y - g.cy);
		if (radius < g.inner || radius > g.radius || !g.total) return -1;
		let angle = Math.atan2(y - g.cy, x - g.cx);
		if (angle < -Math.PI / 2) angle += Math.PI * 2;
		return g.marks.findIndex((mark) => mark.end > angle && mark.start <= angle);
	}
	if (x < g.plot.x || x > g.plot.x + g.plot.width || y < g.plot.y || y > g.plot.y + g.plot.height) return -1;
	return Math.min(g.marks.length - 1, Math.floor((x - g.plot.x) / g.stride));
}
function paint(c, g, color, hovered = -1) {
	c.clearRect(0, 0, g.width, g.height);
	c.lineJoin = "round";
	c.lineCap = "round";
	if (g.type === "donut") {
		if (!g.radius) return;
		c.lineCap = "butt";
		c.lineWidth = g.radius - g.inner;
		c.strokeStyle = color("outlineVariant");
		c.beginPath();
		c.arc(g.cx, g.cy, (g.radius + g.inner) / 2, 0, Math.PI * 2);
		c.stroke();
		for (const mark of g.marks) if (mark.value > 0 && g.valid) {
			const gap = Math.min(.025, (mark.end - mark.start) / 4);
			c.strokeStyle = mark.color || color(palette[mark.index % palette.length]);
			c.lineWidth = g.radius - g.inner + (hovered === mark.index ? 3 : 0);
			c.beginPath();
			c.arc(g.cx, g.cy, (g.radius + g.inner) / 2, mark.start + gap, mark.end - gap);
			c.stroke();
		}
		return;
	}
	c.strokeStyle = color("outlineVariant");
	c.lineWidth = 1;
	for (const tick of g.ticks) {
		c.globalAlpha = tick.value === 0 ? .8 : .4;
		c.beginPath();
		c.moveTo(g.plot.x, tick.y);
		c.lineTo(g.plot.x + g.plot.width, tick.y);
		c.stroke();
	}
	c.globalAlpha = 1;
	if (g.type === "bar") {
		for (const mark of g.marks) if (mark.value != null) {
			c.fillStyle = color(hovered === mark.index ? "contentAccent" : "action");
			c.globalAlpha = hovered < 0 || hovered === mark.index ? .9 : .55;
			c.fillRect(mark.x - mark.width / 2, Math.min(mark.y, mark.zero), mark.width, Math.max(1, Math.abs(mark.y - mark.zero)));
		}
	} else if (g.type === "line") {
		let run = [];
		const draw = () => {
			if (!run.length) return;
			c.beginPath();
			c.moveTo(run[0].x, run[0].zero);
			for (const point of run) c.lineTo(point.x, point.y);
			c.lineTo(run[run.length - 1].x, run[0].zero);
			c.closePath();
			c.fillStyle = color("action");
			c.globalAlpha = .12;
			c.fill();
			c.globalAlpha = 1;
			c.beginPath();
			c.moveTo(run[0].x, run[0].y);
			for (const point of run.slice(1)) c.lineTo(point.x, point.y);
			c.strokeStyle = color("action");
			c.lineWidth = 2.5;
			c.stroke();
			for (const point of run) if (g.marks.length <= 28 || point.index === hovered) {
				c.beginPath();
				c.arc(point.x, point.y, point.index === hovered ? 5 : 3, 0, Math.PI * 2);
				c.fillStyle = color("action");
				c.fill();
				c.strokeStyle = color("panel");
				c.lineWidth = 2;
				c.stroke();
			}
			run = [];
		};
		for (const mark of g.marks) if (mark.value == null) draw();
		else run.push(mark);
		draw();
	}
	c.globalAlpha = 1;
}
//#endregion
//#region src/frame/controls/charts/FrameChart.vue
var _hoisted_1$9 = [
	"data-frame",
	"tabindex",
	"aria-label"
];
var _sfc_main$9 = {
	__name: "FrameChart",
	props: { node: {
		type: Object,
		required: true
	} },
	setup(__props) {
		const props = __props;
		const canvas = ref(null), hovered = ref(-1);
		const tip = computed(() => hovered.value < 0 ? "" : props.node.labels[hovered.value] + ": " + number(props.node.chart.values[hovered.value], props.node.language));
		let pending = 0, observer;
		function paint$2() {
			pending = 0;
			if (!canvas.value) return;
			const g = props.node.chart, ratio = devicePixelRatio || 1;
			const element = canvas.value;
			element.width = Math.round(g.width * ratio);
			element.height = Math.round(g.height * ratio);
			const context = element.getContext("2d");
			context.setTransform(ratio, 0, 0, ratio, 0, 0);
			const style = getComputedStyle(element);
			paint(context, g, (role) => style.getPropertyValue(cssRoles[role]).trim(), hovered.value);
		}
		function requestPaint() {
			if (!pending) pending = requestAnimationFrame(paint$2);
		}
		function move(event) {
			const box = canvas.value.getBoundingClientRect();
			hovered.value = hit(props.node.chart, event.clientX - box.left, event.clientY - box.top);
		}
		watch(() => props.node.chart, () => {
			hovered.value = -1;
			nextTick(requestPaint);
		});
		watch(hovered, requestPaint);
		onMounted(() => {
			observer = new MutationObserver(requestPaint);
			for (let element = canvas.value; element; element = element.parentElement) observer.observe(element, {
				attributes: true,
				attributeFilter: [
					"style",
					"class",
					"data-theme"
				]
			});
			requestPaint();
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(pending);
		});
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("canvas", {
				ref_key: "canvas",
				ref: canvas,
				"data-frame": __props.node.id,
				role: "img",
				tabindex: __props.node.focusable === false ? -1 : 0,
				"aria-label": __props.node.text,
				onPointermove: move,
				onPointerleave: _cache[0] || (_cache[0] = ($event) => hovered.value = -1)
			}, null, 40, _hoisted_1$9)), [[unref(tooltipDirective), tip.value]]);
		};
	}
};
//#endregion
//#region src/controls/clipboard.js
async function copyText(text) {
	if (navigator.clipboard?.writeText) try {
		await navigator.clipboard.writeText(text);
		return;
	} catch {}
	const previous = document.activeElement, input = document.createElement("textarea");
	input.value = text;
	input.readOnly = true;
	input.style.cssText = "position:fixed;inset:0;width:1px;height:1px;opacity:0";
	(document.querySelector("dialog:modal") || document.body).append(input);
	try {
		input.focus();
		input.select();
		if (!document.execCommand("copy")) throw new Error("Clipboard access failed");
	} finally {
		input.remove();
		previous?.focus();
	}
}
async function readClipboard() {
	if (!navigator.clipboard?.readText) throw new Error("Paste with Ctrl+V or the browser menu on HTTP.");
	return navigator.clipboard.readText();
}
async function readClipboardImages() {
	if (!navigator.clipboard?.read) return null;
	let items;
	try {
		items = await navigator.clipboard.read();
	} catch (error) {
		if (["NotAllowedError", "SecurityError"].includes(error.name)) return null;
		throw error;
	}
	const files = [];
	for (const item of items) {
		const type = item.types.includes("image/png") ? "image/png" : item.types.find((type) => type.startsWith("image/"));
		if (!type) continue;
		const extension = type === "image/jpeg" ? "jpg" : type.split("/")[1].split("+")[0];
		files.push(new File([await item.getType(type)], "clipboard" + (files.length ? "-" + (files.length + 1) : "") + "." + extension, { type }));
	}
	if (!files.length) throw new Error("The clipboard does not contain an image");
	return files;
}
async function copyImage(blob) {
	if (!navigator.clipboard?.write || !globalThis.ClipboardItem) throw new Error("Copying an image requires HTTPS or localhost and clipboard permission.");
	let png = blob;
	if (blob.type !== "image/png") {
		const image = await createImageBitmap(blob), canvas = document.createElement("canvas");
		try {
			canvas.width = image.width;
			canvas.height = image.height;
			canvas.getContext("2d").drawImage(image, 0, 0);
			png = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
		} finally {
			image.close();
		}
		if (!png) throw new Error("Unable to copy image");
	}
	await navigator.clipboard.write([new ClipboardItem({ "image/png": png })]);
}
//#endregion
//#region src/controls/pythonSyntax.js
var keywords = new Set("False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split(" "));
function xmlTokens(source) {
	const tokens = [];
	let end = 0;
	for (const match of source.matchAll(/<!--[\s\S]*?(?:-->|$)|<!\[CDATA\[[\s\S]*?(?:\]\]>|$)|<\/?[\w:.-]+|\/?>|"[^"\n]*"|'[^'\n]*'|[\w:.-]+(?=\s*=)|&(?:#\w+|\w+);/g)) {
		if (match.index > end) tokens.push({
			text: source.slice(end, match.index),
			role: ""
		});
		const text = match[0], role = text.startsWith("<!--") ? "comment" : /^["']/.test(text) || text.startsWith("<![CDATA[") ? "string" : text.startsWith("<") || text.endsWith(">") ? "keyword" : text.startsWith("&") ? "number" : "type";
		tokens.push({
			text,
			role
		});
		end = match.index + text.length;
	}
	if (end < source.length) tokens.push({
		text: source.slice(end),
		role: ""
	});
	return tokens;
}
var builtins = new Set("abs all any bool bytes callable chr dict enumerate filter float format getattr hasattr int isinstance issubclass iter len list map max min next object open ord print property range repr reversed round set setattr slice sorted staticmethod str sum super tuple type zip Exception ValueError TypeError RuntimeError KeyError".split(" "));
var pattern = /#[^\n]*|(?<!\w)(?:[furb]{1,2})?(?:"""(?:\\[\s\S]|(?!""")[^\\])*?(?:"""|$)|'''(?:\\[\s\S]|(?!''')[^\\])*?(?:'''|$)|"(?:\\[^\n]|[^"\\\n])*(?:"|$)|'(?:\\[^\n]|[^'\\\n])*(?:'|$))|\b(?:0x[\da-f_]+|0b[01_]+|0o[0-7_]+|\d[\d_]*(?:\.[\d_]*)?(?:e[+-]?[\d_]+)?j?)\b|\.[\d_]+(?:e[+-]?[\d_]+)?j?\b|@[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*|\b[A-Za-z_]\w*\b/gi;
function pythonTokens(source, moduleNames = []) {
	const tokens = [];
	let end = 0;
	let previous = "";
	for (const match of source.matchAll(pattern)) {
		if (match.index > end) tokens.push({
			text: source.slice(end, match.index),
			role: ""
		});
		const text = match[0];
		const role = text.startsWith("#") ? "comment" : /^(?:[furb]{0,2})["']/i.test(text) ? "string" : /^[\d.]/.test(text) ? "number" : text.startsWith("@") ? "decorator" : keywords.has(text) ? "keyword" : ["def", "class"].includes(previous) ? "definition" : moduleNames?.includes(text) ? "module" : ["self", "cls"].includes(text) ? "self" : builtins.has(text) ? "type" : /^\s*\(/.test(source.slice(match.index + text.length)) ? "function" : "";
		tokens.push({
			text,
			role
		});
		previous = text;
		end = match.index + text.length;
	}
	if (end < source.length) tokens.push({
		text: source.slice(end),
		role: ""
	});
	return tokens;
}
var jsKeywords = new Set("async await break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while with yield true false null undefined".split(" "));
function javascriptTokens(source) {
	const tokens = [];
	let end = 0, previous = "";
	for (const match of source.matchAll(/\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)|"(?:\\[\s\S]|[^"\\])*(?:"|$)|'(?:\\[\s\S]|[^'\\])*(?:'|$)|`(?:\\[\s\S]|[^`\\])*(?:`|$)|\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b|\b[$A-Za-z_][$\w]*\b/gi)) {
		if (match.index > end) tokens.push({
			text: source.slice(end, match.index),
			role: ""
		});
		const text = match[0], role = text.startsWith("//") || text.startsWith("/*") ? "comment" : /^["'`]/.test(text) ? "string" : /^\d/.test(text) ? "number" : jsKeywords.has(text) ? "keyword" : ["function", "class"].includes(previous) ? "definition" : /^\s*\(/.test(source.slice(match.index + text.length)) ? "function" : "";
		tokens.push({
			text,
			role
		});
		previous = text;
		end = match.index + text.length;
	}
	if (end < source.length) tokens.push({
		text: source.slice(end),
		role: ""
	});
	return tokens;
}
//#endregion
//#region src/controls/codeEditing.js
function editCommand(action, text, start, end, language = "python") {
	const left = text.lastIndexOf("\n", start - 1) + 1, found = text.indexOf("\n", end), right = found < 0 ? text.length : found;
	const block = text.slice(left, right), lines = block.split("\n"), marker = language === "javascript" ? "//" : "#";
	if (action === "duplicate") {
		const value = start === end ? "\n" + block : text.slice(start, end), position = start === end ? right : end;
		return {
			text: text.slice(0, position) + value + text.slice(position),
			start: position + (start === end ? 1 : 0),
			end: position + value.length
		};
	}
	if (action === "delete_line") {
		const a = right === text.length && left > 0 ? left - 1 : left, b = right < text.length ? right + 1 : right;
		return {
			text: text.slice(0, a) + text.slice(b),
			start: a,
			end: a
		};
	}
	let replacement;
	if (action === "indent") replacement = lines.map((line) => "    " + line).join("\n");
	else if (action === "unindent") replacement = lines.map((line) => line.startsWith("    ") ? line.slice(4) : line.startsWith("	") ? line.slice(1) : line.replace(/^ {1,3}/, "")).join("\n");
	else if (action === "toggle_comment") {
		const remove = lines.filter((line) => line.trim()).every((line) => line.trimStart().startsWith(marker));
		replacement = lines.map((line) => !line.trim() ? line : remove ? line.replace(new RegExp("^(\\s*)" + marker + " ?"), "$1") : line.replace(/^(\s*)/, "$1" + marker + " ")).join("\n");
	} else return {
		text,
		start,
		end
	};
	return {
		text: text.slice(0, left) + replacement + text.slice(right),
		start: left,
		end: left + replacement.length
	};
}
function findMatches(text, query, { regex = false, caseSensitive = false, wholeWord = false } = {}) {
	if (!query) return [];
	let pattern = regex ? query : query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
	if (wholeWord) pattern = "\\b(?:" + pattern + ")\\b";
	try {
		return [...text.matchAll(new RegExp(pattern, caseSensitive ? "g" : "gi"))].filter((match) => match[0].length).map((match) => ({
			start: match.index,
			end: match.index + match[0].length
		}));
	} catch {
		return [];
	}
}
function documentSymbols(text, language) {
	const pattern = language === "javascript" ? /^[ \t]*(?:(?:export|async)[ \t]+)*(function|class)[ \t]+([\w$]+)/gm : /^[ \t]*(?:async[ \t]+)?(def|class)[ \t]+(\w+)/gm;
	return [...text.matchAll(pattern)].map((match) => ({
		name: match[2],
		kind: match[1],
		position: match.index + match[0].indexOf(match[2]),
		line: text.slice(0, match.index).split("\n").length
	}));
}
function completions(text, cursor, language, apiMethods = []) {
	const prefix = /[\w$]*$/.exec(text.slice(0, cursor))[0];
	const names = language === "javascript" ? "async await const let function return if else for while class import export new try catch throw Promise console context project searchType searchKeys rpc refresh" : "def class return if elif else for while import from as try except finally raise with pass True False None print len range str int dict list set tuple enumerate sorted server Search SearchType";
	const candidates = language === "python" && /\bserver\.\w*$/.test(text.slice(0, cursor)) ? apiMethods : [...names.split(" "), ...text.match(/\b[A-Za-z_][\w$]*\b/g) || []];
	return [...new Set(candidates)].filter((name) => name.startsWith(prefix) && name !== prefix).sort().slice(0, 200).map((name) => ({
		name,
		start: cursor - prefix.length,
		end: cursor
	}));
}
//#endregion
//#region src/controls/CodeEditor.vue
var _hoisted_1$8 = {
	key: 0,
	class: "code-source-toolbar"
};
var _hoisted_2$3 = {
	key: 1,
	class: "code-search"
};
var _hoisted_3$2 = ["aria-label", "placeholder"];
var _hoisted_4$1 = ["aria-label", "placeholder"];
var _hoisted_5$1 = {
	key: 2,
	class: "error",
	role: "alert"
};
var _hoisted_6$1 = { class: "code-buffer" };
var _hoisted_7$1 = {
	class: "code-line-numbers",
	"aria-hidden": "true"
};
var _hoisted_8$1 = { class: "code-input-area" };
var _hoisted_9$1 = ["readonly", "aria-label"];
var _hoisted_10 = ["aria-label"];
var _hoisted_11 = { key: 0 };
var _hoisted_12 = { class: "code-completion-kind" };
var _sfc_main$8 = {
	__name: "CodeEditor",
	props: /*@__PURE__*/ mergeModels({
		bufferKey: String,
		language: String,
		readOnly: Boolean,
		disabled: Boolean,
		analysis: Object,
		sourceToolbar: {
			type: Boolean,
			default: true
		}
	}, {
		"modelValue": { default: "" },
		"modelModifiers": {},
		"fontSize": { default: 9.25 },
		"fontSizeModifiers": {}
	}),
	emits: /*@__PURE__*/ mergeModels([
		"run",
		"help",
		"outline",
		"analyse"
	], ["update:modelValue", "update:fontSize"]),
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const emit = __emit;
		const input = ref(null), scroll = ref({
			x: 0,
			y: 0
		}), selection = ref({
			start: 0,
			end: 0
		});
		const findOpen = ref(false), replaceOpen = ref(false), query = ref(""), replacement = ref(""), caseSensitive = ref(false), wholeWord = ref(false), regex = ref(false);
		const findInput = ref(null), suggestions = ref([]), suggestionIndex = ref(0), clipboardError = ref("");
		const completionStyle = ref({});
		const fontSize = useModel(__props, "fontSize");
		const buffers = /* @__PURE__ */ new Map(), history = ref({
			steps: [],
			index: -1
		});
		let completionTimer, analysisRequest = 0, completionSuppressed = false;
		const options = computed(() => ({
			caseSensitive: caseSensitive.value,
			wholeWord: wholeWord.value,
			regex: regex.value
		}));
		const matches = computed(() => findMatches(model.value, query.value, options.value));
		const selectedText = computed(() => model.value.slice(selection.value.start, selection.value.end));
		const highlighted = computed(() => {
			const tokens = props.language === "javascript" ? javascriptTokens(model.value) : pythonTokens(model.value, props.analysis?.source === model.value ? props.analysis.moduleNames : []);
			const word = /^[\w$]+$/.test(selectedText.value) ? selectedText.value : "";
			const overlays = [...matches.value.map((row) => ({
				...row,
				role: "search"
			})), ...findMatches(model.value, word, {
				wholeWord: true,
				caseSensitive: true
			}).map((row) => ({
				...row,
				role: "occurrence"
			}))];
			const parts = [];
			let offset = 0;
			for (const token of tokens) {
				const end = offset + token.text.length, cuts = [.../* @__PURE__ */ new Set([
					offset,
					end,
					...overlays.flatMap((row) => [row.start, row.end]).filter((point) => point > offset && point < end)
				])].sort((a, b) => a - b);
				for (let i = 1; i < cuts.length; i++) parts.push({
					text: model.value.slice(cuts[i - 1], cuts[i]),
					role: token.role,
					overlay: overlays.find((row) => row.start <= cuts[i - 1] && row.end >= cuts[i])?.role
				});
				offset = end;
			}
			return parts;
		});
		function snapshot() {
			return {
				text: model.value,
				...selection.value
			};
		}
		function record() {
			if (history.value.steps[history.value.index]?.text === model.value) return;
			history.value.steps.splice(history.value.index + 1);
			history.value.steps.push(snapshot());
			if (history.value.steps.length > 120) history.value.steps.shift();
			history.value.index = history.value.steps.length - 1;
		}
		watch(() => props.bufferKey, async (key) => {
			suggestions.value = [];
			selection.value = {
				start: 0,
				end: 0
			};
			scroll.value = {
				x: 0,
				y: 0
			};
			if (!buffers.has(key)) buffers.set(key, {
				steps: [snapshot()],
				index: 0
			});
			history.value = buffers.get(key);
			await nextTick();
			if (input.value) {
				input.value.scrollTop = 0;
				input.value.scrollLeft = 0;
			}
		}, { immediate: true });
		watch([
			model,
			() => props.bufferKey,
			() => props.language
		], () => {
			record();
			dismissCompletions();
			completionSuppressed = false;
			clearTimeout(completionTimer);
			completionTimer = setTimeout(() => complete(false), 140);
		});
		onBeforeUnmount(() => clearTimeout(completionTimer));
		watch(() => props.analysis, (result) => {
			if (!result || result.requestId !== analysisRequest || result.bufferKey !== props.bufferKey || result.source !== model.value || result.cursor !== input.value?.selectionEnd) return;
			suggestions.value = !completionSuppressed && document.activeElement === input.value ? result.completions : [];
			suggestionIndex.value = 0;
			nextTick(positionCompletions);
		});
		function dismissCompletions() {
			analysisRequest++;
			completionSuppressed = true;
			suggestions.value = [];
		}
		function positionCompletions() {
			if (!suggestions.value.length || !input.value) return;
			const area = input.value.closest(".code-buffer"), popup = area.querySelector(".code-completions"), style = getComputedStyle(input.value);
			if (!popup) return;
			const before = model.value.slice(0, input.value.selectionEnd), line = before.slice(before.lastIndexOf("\n") + 1), canvas = document.createElement("canvas").getContext("2d");
			canvas.font = style.font;
			const x = 46 + canvas.measureText(line).width - input.value.scrollLeft, y = 12 + before.split("\n").length * parseFloat(style.lineHeight) - input.value.scrollTop;
			completionStyle.value = {
				left: Math.max(4, Math.min(x, area.clientWidth - popup.offsetWidth - 4)) + "px",
				top: Math.max(4, Math.min(y, area.clientHeight - popup.offsetHeight - 4)) + "px"
			};
		}
		function blur(event) {
			if (!event.relatedTarget?.closest(".code-completions")) dismissCompletions();
		}
		function select(start, end = start) {
			if (!input.value) return;
			selection.value = {
				start,
				end
			};
			input.value.focus();
			input.value.setSelectionRange(start, end);
			input.value.scrollTop = Math.max(0, model.value.slice(0, start).split("\n").length - 3) * parseFloat(getComputedStyle(input.value).lineHeight);
			syncScroll();
		}
		async function apply(value) {
			model.value = value.text;
			await nextTick();
			select(value.start, value.end);
			record();
		}
		async function restore(index) {
			const step = history.value.steps[index];
			if (!step || props.readOnly) return;
			history.value.index = index;
			model.value = step.text;
			await nextTick();
			select(step.start, step.end);
		}
		function command(action) {
			if (!props.readOnly) apply(editCommand(action, model.value, selection.value.start, selection.value.end, props.language));
		}
		function syncSelection() {
			if (!input.value) return;
			selection.value = {
				start: input.value.selectionStart,
				end: input.value.selectionEnd
			};
			const step = history.value.steps[history.value.index];
			if (step?.text === model.value) Object.assign(step, selection.value);
		}
		function syncScroll() {
			if (input.value) scroll.value = {
				x: input.value.scrollLeft,
				y: input.value.scrollTop
			};
		}
		function showFind(replace = false) {
			dismissCompletions();
			if (findOpen.value && replaceOpen.value === replace) {
				findOpen.value = false;
				query.value = "";
				input.value.focus();
				return;
			}
			findOpen.value = true;
			replaceOpen.value = replace && !props.readOnly;
			nextTick(() => {
				findInput.value?.focus();
				findInput.value?.select();
			});
		}
		function nextMatch(backwards = false) {
			const rows = matches.value;
			if (!rows.length) return;
			const row = backwards ? [...rows].reverse().find((row) => row.end < selection.value.start) || rows.at(-1) : rows.find((row) => row.start > selection.value.start) || rows[0];
			select(row.start, row.end);
		}
		function replace(all = false) {
			if (props.readOnly) return;
			const rows = all ? matches.value : matches.value.filter((row) => row.start === selection.value.start && row.end === selection.value.end);
			if (!rows.length) return nextMatch();
			let text = model.value;
			for (const row of [...rows].reverse()) text = text.slice(0, row.start) + replacement.value + text.slice(row.end);
			apply({
				text,
				start: rows[0].start,
				end: rows[0].start + replacement.value.length
			});
		}
		async function clipboard(action) {
			try {
				clipboardError.value = "";
				if (action === "paste") {
					if (props.readOnly) return;
					const value = await readClipboard();
					apply({
						text: model.value.slice(0, selection.value.start) + value + model.value.slice(selection.value.end),
						start: selection.value.start + value.length,
						end: selection.value.start + value.length
					});
				} else {
					await copyText(selectedText.value);
					if (action === "cut" && !props.readOnly) apply({
						text: model.value.slice(0, selection.value.start) + model.value.slice(selection.value.end),
						start: selection.value.start,
						end: selection.value.start
					});
				}
			} catch (error) {
				clipboardError.value = error.message;
			}
		}
		function complete(manual = true) {
			clearTimeout(completionTimer);
			if (manual) completionSuppressed = false;
			emit("analyse", {
				bufferKey: props.bufferKey,
				source: model.value,
				cursor: input.value?.selectionEnd || 0,
				manual,
				requestId: ++analysisRequest
			});
		}
		function acceptSuggestion(row, suffix = "") {
			dismissCompletions();
			if (props.readOnly) return;
			const text = row.insertText || row.name, cursor = row.start + text.length + (row.cursorOffset || 0);
			const source = model.value.slice(0, row.start) + text + model.value.slice(row.end);
			apply({
				text: source.slice(0, cursor) + suffix + source.slice(cursor),
				start: cursor + suffix.length,
				end: cursor + suffix.length
			});
		}
		function goToLine(line) {
			select(model.value.split("\n").slice(0, line - 1).reduce((sum, value) => sum + value.length + 1, 0));
		}
		function navigateSymbol(delta) {
			const symbols = props.analysis?.symbols || [], line = model.value.slice(0, selection.value.end).split("\n").length;
			const row = delta > 0 ? symbols.find((row) => row.line > line) || symbols[0] : [...symbols].reverse().find((row) => row.line < line) || symbols.at(-1);
			if (row) goToLine(row.line);
		}
		function definition() {
			const cursor = selection.value.end, before = /[\w$]*$/.exec(model.value.slice(0, cursor))[0], after = /^[\w$]*/.exec(model.value.slice(cursor))[0];
			const row = props.analysis?.symbols.find((row) => row.name === before + after);
			if (row) goToLine(row.line);
		}
		function key(event) {
			const ctrl = event.ctrlKey || event.metaKey;
			if (event.key === "Tab" && event.target !== input.value) return;
			if (event.target.tagName === "INPUT" && !["Escape", "F3"].includes(event.key) && !(ctrl && ["f", "h"].includes(event.key.toLowerCase()))) return;
			if (ctrl && event.key === "Enter") {
				event.preventDefault();
				dismissCompletions();
				emit("run", selectedText.value || model.value);
				return;
			}
			if (suggestions.value.length && !ctrl && [
				"ArrowDown",
				"ArrowUp",
				"Enter",
				"Tab",
				" "
			].includes(event.key)) {
				if (event.key === "Enter") {
					dismissCompletions();
					return;
				}
				event.preventDefault();
				if (["Tab", " "].includes(event.key)) acceptSuggestion(suggestions.value[suggestionIndex.value], event.key === " " ? " " : "");
				else {
					suggestionIndex.value = (suggestionIndex.value + (event.key === "ArrowDown" ? 1 : suggestions.value.length - 1)) % suggestions.value.length;
					nextTick(() => input.value.parentElement.parentElement.querySelector("[aria-selected=\"true\"]")?.scrollIntoView({ block: "nearest" }));
				}
				return;
			}
			if (event.key === "Escape" && (suggestions.value.length || findOpen.value)) {
				event.preventDefault();
				event.stopPropagation();
				const searching = !suggestions.value.length;
				dismissCompletions();
				if (searching) {
					findOpen.value = false;
					query.value = "";
					input.value.focus();
				}
				return;
			}
			let handled = true;
			if (ctrl && event.key.toLowerCase() === "z") restore(history.value.index + (event.shiftKey ? 1 : -1));
			else if (ctrl && event.key.toLowerCase() === "y") restore(history.value.index + 1);
			else if (ctrl && ["f", "h"].includes(event.key.toLowerCase())) showFind(event.key.toLowerCase() === "h");
			else if (event.key === "F3") nextMatch(event.shiftKey);
			else if (ctrl && event.code === "Space") complete();
			else if (ctrl && event.shiftKey && event.key.toLowerCase() === "o") emit("outline");
			else if (event.altKey && ["ArrowUp", "ArrowDown"].includes(event.key)) navigateSymbol(event.key === "ArrowUp" ? -1 : 1);
			else if (event.key === "F12") definition();
			else if (ctrl && event.shiftKey && event.key.toLowerCase() === "k") command("delete_line");
			else if (ctrl && event.key === "/") command("toggle_comment");
			else if (ctrl && event.key.toLowerCase() === "d") command("duplicate");
			else if (event.key === "Tab") {
				if (event.shiftKey || selectedText.value) command(event.shiftKey ? "unindent" : "indent");
				else if (!props.readOnly) {
					const cursor = selection.value.end, count = 4 - (cursor - model.value.lastIndexOf("\n", cursor - 1) - 1) % 4;
					apply({
						text: model.value.slice(0, cursor) + " ".repeat(count) + model.value.slice(cursor),
						start: cursor + count,
						end: cursor + count
					});
				}
			} else handled = false;
			if (handled) event.preventDefault();
			else suggestions.value = [];
		}
		__expose({
			select,
			goToLine,
			selectedText,
			showFind,
			clipboard,
			historyTo: restore,
			undo() {
				return restore(history.value.index - 1);
			},
			redo() {
				return restore(history.value.index + 1);
			},
			frameState: computed(() => ({
				historyCount: history.value.steps.length,
				historyIndex: history.value.index,
				canUndo: history.value.index > 0,
				canRedo: history.value.index < history.value.steps.length - 1,
				canCopy: !!selectedText.value
			})),
			focus() {
				input.value?.focus();
			}
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "code-editor",
				style: normalizeStyle({ "--code-size": fontSize.value + "pt" }),
				onKeydown: key
			}, [
				__props.sourceToolbar ? (openBlock(), createElementBlock("div", _hoisted_1$8, [
					createVNode(_sfc_main$33, { name: "MDI_FILE_EDIT" }),
					createBaseVNode("span", null, toDisplayString(unref(t)("Source")), 1),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "undo",
						label: "Undo",
						disabled: __props.readOnly || history.value.index <= 0,
						onClick: _cache[0] || (_cache[0] = ($event) => restore(history.value.index - 1))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "redo",
						label: "Redo",
						disabled: __props.readOnly || history.value.index >= history.value.steps.length - 1,
						onClick: _cache[1] || (_cache[1] = ($event) => restore(history.value.index + 1))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$26, {
						overlay: "",
						label: "Edit history",
						icon: "history"
					}, {
						default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList([...history.value.steps].reverse(), (step, index) => {
							return openBlock(), createBlock(_sfc_main$34, {
								key: index,
								label: String(history.value.steps.length - index) + " · " + step.text.split("\n")[0].slice(0, 80),
								disabled: __props.readOnly,
								onClick: ($event) => restore(history.value.steps.length - index - 1)
							}, null, 8, [
								"label",
								"disabled",
								"onClick"
							]);
						}), 128))]),
						_: 1
					}),
					renderSlot(_ctx.$slots, "actions"),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "FAS_CUT",
						label: "Cut",
						disabled: __props.readOnly || !selectedText.value,
						onClick: _cache[2] || (_cache[2] = ($event) => clipboard("cut"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "copy",
						label: "Copy",
						disabled: !selectedText.value,
						onClick: _cache[3] || (_cache[3] = ($event) => clipboard("copy"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "MDI_CONTENT_PASTE",
						label: "Paste",
						disabled: __props.readOnly,
						onClick: _cache[4] || (_cache[4] = ($event) => clipboard("paste"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$26, {
						overlay: "",
						label: "Text size",
						icon: "MDI_FORMAT_SIZE"
					}, {
						default: withCtx(() => [(openBlock(), createElementBlock(Fragment, null, renderList([
							8,
							9.25,
							11,
							13,
							15
						], (size, index) => {
							return createVNode(_sfc_main$34, {
								key: size,
								label: [
									"Small",
									"Normal",
									"Medium",
									"Large",
									"Extra large"
								][index],
								"aria-pressed": size === fontSize.value,
								onClick: ($event) => fontSize.value = size
							}, null, 8, [
								"label",
								"aria-pressed",
								"onClick"
							]);
						}), 64))]),
						_: 1
					}),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "search",
						label: "Find",
						onClick: _cache[5] || (_cache[5] = ($event) => showFind())
					}),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "MDI_PLAY_BOX_OUTLINE",
						label: "Run selection",
						disabled: __props.readOnly || __props.disabled || !selectedText.value,
						onClick: _cache[6] || (_cache[6] = ($event) => emit("run", selectedText.value))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "help",
						label: "Code editor help",
						onClick: _cache[7] || (_cache[7] = ($event) => emit("help"))
					})
				])) : createCommentVNode("", true),
				findOpen.value ? (openBlock(), createElementBlock("div", _hoisted_2$3, [
					withDirectives(createBaseVNode("input", {
						ref_key: "findInput",
						ref: findInput,
						"onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => query.value = $event),
						"aria-label": unref(t)("Find in source"),
						placeholder: unref(t)("Find"),
						onKeydown: _cache[9] || (_cache[9] = withKeys(withModifiers(($event) => nextMatch($event.shiftKey), ["prevent"]), ["enter"]))
					}, null, 40, _hoisted_3$2), [[vModelText, query.value]]),
					createBaseVNode("span", null, toDisplayString(matches.value.length), 1),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "previous",
						label: "Previous match",
						onClick: _cache[10] || (_cache[10] = ($event) => nextMatch(true))
					}),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "next",
						label: "Next match",
						onClick: _cache[11] || (_cache[11] = ($event) => nextMatch())
					}),
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Match case")), 1), createVNode(_sfc_main$32, {
						modelValue: caseSensitive.value,
						"onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => caseSensitive.value = $event),
						label: "Match case"
					}, null, 8, ["modelValue"])]),
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Whole word")), 1), createVNode(_sfc_main$32, {
						modelValue: wholeWord.value,
						"onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => wholeWord.value = $event),
						label: "Whole word"
					}, null, 8, ["modelValue"])]),
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Regular expression")), 1), createVNode(_sfc_main$32, {
						modelValue: regex.value,
						"onUpdate:modelValue": _cache[14] || (_cache[14] = ($event) => regex.value = $event),
						label: "Regular expression"
					}, null, 8, ["modelValue"])]),
					!__props.readOnly ? (openBlock(), createBlock(_sfc_main$34, {
						key: 0,
						"icon-only": "",
						icon: "edit",
						label: "Replace",
						onClick: _cache[15] || (_cache[15] = ($event) => replaceOpen.value = !replaceOpen.value)
					})) : createCommentVNode("", true),
					createVNode(_sfc_main$34, {
						"icon-only": "",
						icon: "close",
						label: "Close search",
						onClick: _cache[16] || (_cache[16] = ($event) => {
							findOpen.value = false;
							query.value = "";
						})
					}),
					replaceOpen.value ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [
						withDirectives(createBaseVNode("input", {
							"onUpdate:modelValue": _cache[17] || (_cache[17] = ($event) => replacement.value = $event),
							"aria-label": unref(t)("Replacement"),
							placeholder: unref(t)("Replacement")
						}, null, 8, _hoisted_4$1), [[vModelText, replacement.value]]),
						createVNode(_sfc_main$34, {
							label: "Replace",
							onClick: _cache[18] || (_cache[18] = ($event) => replace())
						}),
						createVNode(_sfc_main$34, {
							label: "Replace all",
							onClick: _cache[19] || (_cache[19] = ($event) => replace(true))
						})
					], 64)) : createCommentVNode("", true)
				])) : createCommentVNode("", true),
				clipboardError.value ? (openBlock(), createElementBlock("p", _hoisted_5$1, toDisplayString(unref(t)(clipboardError.value)), 1)) : createCommentVNode("", true),
				createBaseVNode("div", _hoisted_6$1, [
					createBaseVNode("div", _hoisted_7$1, [createBaseVNode("pre", { style: normalizeStyle({ transform: `translateY(${-scroll.value.y}px)` }) }, toDisplayString(Array.from({ length: model.value.split("\n").length }, (_, i) => i + 1).join("\n")), 5)]),
					createBaseVNode("div", _hoisted_8$1, [createBaseVNode("pre", {
						class: "code-highlight",
						"aria-hidden": "true",
						style: normalizeStyle({ transform: `translate(${-scroll.value.x}px, ${-scroll.value.y}px)` })
					}, [(openBlock(true), createElementBlock(Fragment, null, renderList(highlighted.value, (part, index) => {
						return openBlock(), createElementBlock("span", {
							key: index,
							class: normalizeClass([part.role && "syntax-" + part.role, part.overlay && "syntax-" + part.overlay])
						}, toDisplayString(part.text), 3);
					}), 128)), _cache[22] || (_cache[22] = createTextVNode(toDisplayString("\n"), -1))], 4), withDirectives(createBaseVNode("textarea", {
						ref_key: "input",
						ref: input,
						"onUpdate:modelValue": _cache[20] || (_cache[20] = ($event) => model.value = $event),
						wrap: "off",
						spellcheck: "false",
						autocapitalize: "off",
						autocomplete: "off",
						readonly: __props.readOnly,
						"aria-label": unref(t)("Script source"),
						onSelect: syncSelection,
						onKeyup: syncSelection,
						onClick: syncSelection,
						onInput: _cache[21] || (_cache[21] = ($event) => {
							syncSelection();
							record();
						}),
						onScroll: syncScroll,
						onBlur: blur
					}, null, 40, _hoisted_9$1), [[vModelText, model.value]])]),
					suggestions.value.length ? (openBlock(), createElementBlock("div", {
						key: 0,
						class: "code-completions",
						style: normalizeStyle(completionStyle.value),
						role: "listbox",
						"aria-label": unref(t)("Code completions")
					}, [(openBlock(true), createElementBlock(Fragment, null, renderList(suggestions.value, (row, index) => {
						return openBlock(), createBlock(_sfc_main$34, {
							key: row.label || row.name,
							role: "option",
							"aria-selected": index === suggestionIndex.value,
							label: row.label || row.name,
							class: normalizeClass({ detailed: row.detail }),
							onClick: ($event) => acceptSuggestion(row)
						}, {
							default: withCtx(() => [
								createVNode(_sfc_main$33, { name: row.kind === "class" ? "MDI_FORMAT_SIZE" : row.kind === "module" ? "MDI_API" : "code" }, null, 8, ["name"]),
								createBaseVNode("span", null, [createBaseVNode("strong", null, toDisplayString(row.label || row.name), 1), row.detail ? (openBlock(), createElementBlock("small", _hoisted_11, toDisplayString(unref(t)(row.detail)), 1)) : createCommentVNode("", true)]),
								createBaseVNode("small", _hoisted_12, toDisplayString(unref(t)(row.kind || "variable")), 1)
							]),
							_: 2
						}, 1032, [
							"aria-selected",
							"label",
							"class",
							"onClick"
						]);
					}), 128))], 12, _hoisted_10)) : createCommentVNode("", true)
				])
			], 36);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/code/code.ui.mjs
function toolbar(model, width, language, revision) {
	const tr = (text) => translate(text, language), nodes = [], actions = [
		[
			"undo",
			"Undo",
			"undo",
			!model.readOnly && model.canUndo
		],
		[
			"redo",
			"Redo",
			"redo",
			!model.readOnly && model.canRedo
		],
		[
			"cut",
			"Cut",
			"content-cut",
			!model.readOnly && model.canCopy
		],
		[
			"copy",
			"Copy",
			"copy",
			model.canCopy
		],
		[
			"paste",
			"Paste",
			"content-paste",
			!model.readOnly
		],
		[
			"find",
			"Find",
			"search",
			true
		],
		[
			"replace",
			"Replace",
			"edit",
			!model.readOnly
		],
		[
			"help",
			"Code editor help",
			"help",
			true
		]
	], compact = model.compactToolbar === void 0 ? width < 620 : model.compactToolbar;
	let x = 0;
	if (compact) {
		const size = Math.max(110, width * .43);
		nodes.push(node("Choice", "frameCodeCommands", rect(0, 0, size, 30), {
			label: tr("Source"),
			value: "",
			resetKey: revision,
			options: [{
				value: "",
				label: tr("Source")
			}].concat(actions.map((row) => ({
				value: row[0],
				label: tr(row[1]),
				disabled: !row[3]
			}))),
			action: { type: "command" }
		}));
		x = size + 6;
	} else {
		nodes.push(label("frameCodeSource", rect(0, 0, 58, 30), tr("Source"), muted));
		x = 60;
		for (const row of actions) {
			nodes.push(node("Button", "frameCode_" + row[0], rect(x, 0, 28, 28), {
				text: tr(row[1]),
				icon: row[2],
				iconOnly: true,
				enabled: row[3],
				action: {
					type: "command",
					value: row[0]
				}
			}));
			x += 30;
		}
	}
	const fontWidth = compact ? Math.min(90, width * .23) : 100;
	nodes.push(node("Choice", "frameCodeFontSize", rect(x, 0, fontWidth, 30), {
		label: tr("Text size"),
		value: model.fontSize,
		options: [
			8,
			9.25,
			11,
			13,
			15
		].map((value, index) => ({
			value,
			label: tr([
				"Small",
				"Normal",
				"Medium",
				"Large",
				"Extra large"
			][index])
		})),
		action: { type: "font" }
	}));
	x += fontWidth + 6;
	const history = [];
	for (let index = model.historyCount - 1; index >= 0; index--) {
		const distance = model.historyIndex - index;
		history.push({
			value: index,
			label: distance === 0 ? tr("Current state") : String(Math.abs(distance)) + " " + tr(distance > 0 ? "edits back" : "edits forward")
		});
	}
	nodes.push(node("Choice", "frameCodeHistory", rect(x, 0, Math.max(1, width - x), 30), {
		label: tr("Edit history"),
		value: model.historyIndex,
		options: history,
		enabled: !model.readOnly && model.historyCount > 1,
		action: { type: "history" }
	}));
	return { nodes };
}
//#endregion
//#region src/frame/controls/code/FrameCode.vue
var _hoisted_1$7 = ["data-frame"];
var FrameCode_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FrameCode",
	props: { node: {
		type: Object,
		required: true
	} },
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props, emit = __emit, source = ref(null), font = ref(9.25), revision = ref(0);
		const model = computed(() => ({
			canUndo: false,
			canRedo: false,
			canCopy: false,
			...source.value?.frameState,
			historyCount: source.value?.frameState?.historyCount || 1,
			historyIndex: source.value?.frameState?.historyIndex || 0,
			fontSize: font.value,
			readOnly: props.node.readOnly || !props.node.enabled
		}));
		const toolbar$2 = computed(() => toolbar(model.value, props.node.width, props.node.language || "en", revision.value));
		async function dispatch(event) {
			revision.value++;
			if (event.type === "font") {
				font.value = Number(event.value);
				return;
			}
			if (event.type === "history") {
				await source.value?.historyTo(Number(event.value));
				return;
			}
			const action = event.value;
			if (action === "copy" && model.value.canCopy || ["cut", "paste"].includes(action) && !model.value.readOnly) await source.value?.clipboard(action);
			else if (action === "undo" && model.value.canUndo && !model.value.readOnly) await source.value?.undo();
			else if (action === "redo" && model.value.canRedo && !model.value.readOnly) await source.value?.redo();
			else if (action === "find" || action === "replace" && !model.value.readOnly) source.value?.showFind(action === "replace");
			else if (action === "help") emit("event", props.node.helpAction || { type: "help" });
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "frame-code",
				"data-frame": __props.node.id
			}, [createVNode(_sfc_main, {
				class: "frame-code-toolbar",
				scene: toolbar$2.value,
				onEvent: dispatch
			}, null, 8, ["scene"]), createVNode(_sfc_main$8, {
				ref_key: "source",
				ref: source,
				class: "frame-code-source",
				"source-toolbar": false,
				"model-value": __props.node.text,
				language: __props.node.syntax || "xml",
				"buffer-key": __props.node.bufferKey,
				"read-only": model.value.readOnly,
				disabled: !__props.node.enabled,
				"font-size": font.value,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => emit("event", {
					...__props.node.action,
					value: $event
				})),
				onHelp: _cache[1] || (_cache[1] = ($event) => emit("event", __props.node.helpAction || { type: "help" }))
			}, null, 8, [
				"model-value",
				"language",
				"buffer-key",
				"read-only",
				"disabled",
				"font-size"
			])], 8, _hoisted_1$7);
		};
	}
}, [["__scopeId", "data-v-76ea9979"]]);
//#endregion
//#region src/controls/IconPicker.vue
var _hoisted_1$6 = { key: 0 };
var _hoisted_2$2 = { class: "icon-picker" };
var _hoisted_3$1 = ["aria-label"];
var _sfc_main$6 = {
	__name: "IconPicker",
	props: {
		modelValue: String,
		disabled: Boolean,
		iconOnly: Boolean,
		tacticCompatibleOnly: Boolean
	},
	emits: ["update:modelValue"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const menu = ref(null), search = ref(""), family = ref("material-design"), grid = ref(null);
		const viewport = ref({
			width: 480,
			height: 280,
			offset: 0
		});
		let observer;
		const sets = computed(() => iconSets.filter((option) => iconMaps[option.value] && (!props.tacticCompatibleOnly || option.value === "fontawesome-solid")));
		const names = computed(() => Object.keys(iconMaps[family.value]).sort().filter((name) => name.includes(search.value.toLowerCase().trim())));
		const columns = computed(() => Math.max(1, Math.floor((viewport.value.width - 4) / 96)));
		const rowCount = computed(() => Math.ceil(names.value.length / columns.value));
		const visible = computed(() => {
			const range = virtualRange(rowCount.value, 76, viewport.value.height, viewport.value.offset, 1);
			return names.value.slice(range.first * columns.value, range.last * columns.value).map((name, index) => ({
				name,
				index: range.first * columns.value + index
			}));
		});
		const value = (name) => props.tacticCompatibleOnly ? name : family.value + ":" + name;
		function select(name) {
			emit("update:modelValue", value(name));
			menu.value.close(true);
		}
		function prepare() {
			const explicit = props.modelValue?.split(":")[0], legacy = /^(FA|FAS|FAR|MDI)_/i.exec(props.modelValue || "");
			const preferred = iconMaps[explicit] ? explicit : legacy ? {
				FA: "fontawesome-solid",
				FAS: "fontawesome-solid",
				FAR: "fontawesome-outline",
				MDI: "material-design"
			}[legacy[1].toUpperCase()] : appearance.iconSet;
			family.value = props.tacticCompatibleOnly ? "fontawesome-solid" : iconMaps[preferred] ? preferred : "material-design";
			search.value = "";
		}
		function opened(event) {
			if (event.target !== menu.value?.$el) return;
			if (event.newState !== "open") {
				observer?.disconnect();
				return;
			}
			nextTick(() => {
				if (!menu.value?.open || !grid.value) return;
				menu.value?.$el.querySelector(".app-text-field")?.focus();
				observer?.disconnect();
				observer = new ResizeObserver((entries) => {
					const box = entries[0].contentRect;
					viewport.value = {
						width: box.width,
						height: box.height,
						offset: grid.value.scrollTop
					};
				});
				observer.observe(grid.value);
			});
		}
		watch([search, family], () => {
			if (grid.value) grid.value.scrollTop = 0;
			viewport.value = {
				...viewport.value,
				offset: 0
			};
		});
		function move(event, index) {
			const step = {
				ArrowLeft: -1,
				ArrowRight: 1,
				ArrowUp: -columns.value,
				ArrowDown: columns.value
			}[event.key];
			if (step === void 0 && event.key !== "Home" && event.key !== "End") return;
			event.preventDefault();
			event.stopPropagation();
			const target = event.key === "Home" ? 0 : event.key === "End" ? names.value.length - 1 : Math.max(0, Math.min(names.value.length - 1, index + step));
			const top = Math.floor(target / columns.value) * 76;
			if (top < grid.value.scrollTop) grid.value.scrollTop = top;
			else if (top + 76 > grid.value.scrollTop + grid.value.clientHeight) grid.value.scrollTop = top + 76 - grid.value.clientHeight;
			viewport.value = {
				...viewport.value,
				offset: grid.value.scrollTop
			};
			nextTick(() => grid.value.querySelector(`[data-icon-index="${target}"]`)?.focus());
		}
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$26, {
				ref_key: "menu",
				ref: menu,
				"compact-trigger": "",
				class: "icon-picker-control",
				label: "Choose icon",
				disabled: __props.disabled,
				"show-label": !__props.iconOnly,
				overlay: "",
				width: unref(controls).iconPicker.popupWidth,
				"max-height": unref(controls).iconPicker.popupHeight,
				"close-on-select": false,
				onBeforeOpen: prepare,
				onToggle: opened
			}, {
				trigger: withCtx(() => [createVNode(_sfc_main$33, { name: __props.modelValue || "image" }, null, 8, ["name"]), !__props.iconOnly ? (openBlock(), createElementBlock("span", _hoisted_1$6, toDisplayString(unref(t)("Choose icon")), 1)) : createCommentVNode("", true)]),
				default: withCtx(() => [createBaseVNode("div", _hoisted_2$2, [
					createBaseVNode("header", null, [
						createVNode(_sfc_main$33, { name: "shapes" }),
						createBaseVNode("strong", null, toDisplayString(unref(t)("Icon library")), 1),
						createBaseVNode("small", null, toDisplayString(names.value.length), 1),
						sets.value.length > 1 ? (openBlock(), createBlock(_sfc_main$31, {
							key: 0,
							modelValue: family.value,
							"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => family.value = $event),
							options: sets.value,
							label: "Icon set"
						}, null, 8, ["modelValue", "options"])) : createCommentVNode("", true)
					]),
					createVNode(_sfc_main$29, {
						modelValue: search.value,
						"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => search.value = $event),
						label: "Search icons",
						placeholder: "Search icons",
						onKeydown: _cache[2] || (_cache[2] = withKeys(withModifiers(($event) => grid.value.querySelector("button")?.focus(), ["prevent"]), ["down"]))
					}, null, 8, ["modelValue"]),
					createBaseVNode("div", {
						ref_key: "grid",
						ref: grid,
						class: "icon-library",
						role: "group",
						"aria-label": unref(t)("Icon library"),
						onScroll: _cache[3] || (_cache[3] = ($event) => viewport.value = {
							...viewport.value,
							offset: $event.target.scrollTop
						})
					}, [createBaseVNode("div", { style: normalizeStyle({ height: rowCount.value * 76 + "px" }) }, [(openBlock(true), createElementBlock(Fragment, null, renderList(visible.value, (item) => {
						return openBlock(), createBlock(_sfc_main$34, {
							key: item.name,
							"data-icon-index": item.index,
							"aria-label": item.name,
							"aria-pressed": __props.modelValue === value(item.name) || __props.modelValue === item.name,
							style: normalizeStyle({
								left: item.index % columns.value * (100 / columns.value) + "%",
								top: Math.floor(item.index / columns.value) * 76 + "px",
								width: 100 / columns.value + "%"
							}),
							onKeydown: ($event) => move($event, item.index),
							onClick: ($event) => select(item.name)
						}, {
							default: withCtx(() => [createVNode(_sfc_main$33, { name: family.value + ":" + item.name }, null, 8, ["name"]), createBaseVNode("small", null, toDisplayString(item.name), 1)]),
							_: 2
						}, 1032, [
							"data-icon-index",
							"aria-label",
							"aria-pressed",
							"style",
							"onKeydown",
							"onClick"
						]);
					}), 128))], 4)], 40, _hoisted_3$1)
				])]),
				_: 1
			}, 8, [
				"disabled",
				"show-label",
				"width",
				"max-height"
			]);
		};
	}
};
//#endregion
//#region src/controls/AppSplitter.vue
var _hoisted_1$5 = [
	"tabindex",
	"aria-disabled",
	"aria-label",
	"aria-orientation",
	"aria-valuemin",
	"aria-valuemax",
	"aria-valuenow"
];
var _sfc_main$5 = {
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
	emits: /*@__PURE__*/ mergeModels(["committed", "cancelled"], ["update:modelValue"]),
	setup(__props, { emit: __emit }) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const emit = __emit;
		const dragging = ref(false);
		let gesture = null;
		function set(value, commit = false) {
			const bounded = Math.max(props.min, Math.min(props.max, value));
			if (gesture) gesture.last = bounded;
			model.value = bounded;
			if (commit) emit("committed", bounded);
		}
		function move(event) {
			if (gesture && event.pointerId === gesture.id) set(gesture.value + ((props.horizontal ? event.clientY : event.clientX) - gesture.position) * gesture.scale * (props.reverse ? -1 : 1));
		}
		function end(event) {
			if (gesture && event?.pointerId != null && event.pointerId !== gesture.id) return;
			const previous = gesture;
			gesture = null;
			dragging.value = false;
			window.removeEventListener("pointermove", move);
			window.removeEventListener("pointerup", end);
			window.removeEventListener("pointercancel", end);
			window.removeEventListener("blur", end);
			if (previous) emit(event?.type === "pointerup" ? "committed" : "cancelled", event?.type === "pointerup" ? previous.last : previous.value);
		}
		function start(event) {
			if (props.disabled || event.button !== 0 || gesture) return;
			const bounds = event.currentTarget.parentElement.getBoundingClientRect();
			gesture = {
				id: event.pointerId,
				value: model.value,
				last: model.value,
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
			set(event.key === "Home" ? props.min : event.key === "End" ? props.max : model.value + (event.key === keys[0] ? -1 : 1) * (props.reverse ? -1 : 1) * (event.ctrlKey || props.proportional ? 1 : 10), true);
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
			}, null, 42, _hoisted_1$5);
		};
	}
};
//#endregion
//#region src/controls/ItemSurface.vue
var _hoisted_1$4 = {
	key: 0,
	class: "item-surface-rail",
	"aria-hidden": "true"
};
var _sfc_main$4 = {
	__name: "ItemSurface",
	props: {
		accent: String,
		selected: Boolean,
		cornerRadius: {
			type: Number,
			default: 10
		},
		inset: {
			type: Number,
			default: 1
		},
		normalColor: String,
		selectedColor: String,
		railVisible: {
			type: Boolean,
			default: true
		},
		separatorVisible: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["item-surface", {
					selected: __props.selected,
					"without-separator": !__props.separatorVisible
				}]),
				style: normalizeStyle({
					"--item-base": (__props.selected ? __props.selectedColor : __props.normalColor) || void 0,
					"--item-accent": __props.accent || "var(--primary)",
					"--item-corner": __props.cornerRadius + "px",
					"--item-inset": __props.inset + "px"
				})
			}, [__props.railVisible ? (openBlock(), createElementBlock("span", _hoisted_1$4)) : createCommentVNode("", true), renderSlot(_ctx.$slots, "default")], 6);
		};
	}
};
//#endregion
//#region src/controls/SummaryChip.vue
var _hoisted_1$3 = { key: 1 };
var _hoisted_2$1 = { key: 2 };
var _sfc_main$3 = {
	__name: "SummaryChip",
	props: {
		label: String,
		count: Number,
		accent: String,
		icon: String,
		compact: Boolean,
		clickable: Boolean,
		showDot: {
			type: Boolean,
			default: true
		},
		showCount: {
			type: Boolean,
			default: true
		}
	},
	emits: ["click"],
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(resolveDynamicComponent(__props.clickable ? _sfc_main$34 : "div"), {
				class: normalizeClass(["summary-chip", {
					clickable: __props.clickable,
					compact: __props.compact
				}]),
				label: __props.clickable ? __props.label + (__props.showCount && __props.count != null ? " " + __props.count : "") : void 0,
				style: normalizeStyle({ "--chip-accent": __props.accent || "var(--primary)" }),
				onClick: _cache[0] || (_cache[0] = ($event) => __props.clickable && _ctx.$emit("click"))
			}, {
				default: withCtx(() => [
					__props.icon ? (openBlock(), createBlock(_sfc_main$33, {
						key: 0,
						name: __props.icon
					}, null, 8, ["name"])) : createCommentVNode("", true),
					__props.showDot ? (openBlock(), createElementBlock("i", _hoisted_1$3)) : createCommentVNode("", true),
					createBaseVNode("span", null, toDisplayString(__props.label), 1),
					__props.showCount ? (openBlock(), createElementBlock("small", _hoisted_2$1, toDisplayString(__props.count), 1)) : createCommentVNode("", true)
				]),
				_: 1
			}, 8, [
				"class",
				"label",
				"style"
			]);
		};
	}
};
//#endregion
//#region src/controls/MiddleElide.vue
var _hoisted_1$2 = ["title", "aria-label"];
var _sfc_main$2 = {
	__name: "MiddleElide",
	props: { text: String },
	setup(__props) {
		const props = __props;
		const label = ref(null), displayed = ref(props.text || ""), naturalWidth = ref(null);
		let observer, context;
		function measure() {
			if (!label.value || !context) return;
			const style = getComputedStyle(label.value), width = label.value.clientWidth;
			context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
			const text = props.text || "";
			naturalWidth.value = Math.ceil(context.measureText(text).width);
			if (context.measureText(text).width <= width) {
				displayed.value = text;
				return;
			}
			const parts = Array.from(text), candidate = (length) => parts.slice(0, Math.ceil(length / 2)).join("") + "…" + parts.slice(parts.length - Math.floor(length / 2)).join("");
			let low = 0, high = parts.length;
			while (low < high) {
				const mid = Math.ceil((low + high) / 2);
				if (context.measureText(candidate(mid)).width <= width) low = mid;
				else high = mid - 1;
			}
			displayed.value = candidate(low);
		}
		onMounted(() => {
			context = document.createElement("canvas").getContext("2d");
			observer = new ResizeObserver(measure);
			observer.observe(label.value);
			document.fonts.ready.then(measure);
			measure();
		});
		onBeforeUnmount(() => observer?.disconnect());
		watch(() => props.text, () => nextTick(measure));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				ref_key: "label",
				ref: label,
				class: "middle-elide",
				style: normalizeStyle({ width: naturalWidth.value == null ? void 0 : naturalWidth.value + "px" }),
				title: __props.text,
				"aria-label": __props.text
			}, toDisplayString(displayed.value), 13, _hoisted_1$2);
		};
	}
};
//#endregion
//#region src/controls/display/StatusChip.vue
var _hoisted_1$1 = { key: 2 };
var _sfc_main$1 = {
	__name: "StatusChip",
	props: {
		text: String,
		icon: String,
		accent: String,
		dense: Boolean,
		interactive: Boolean,
		maximumWidth: Number,
		disabled: Boolean
	},
	emits: ["click"],
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(resolveDynamicComponent(__props.interactive ? _sfc_main$34 : "span"), {
				class: normalizeClass(["status-chip", {
					dense: __props.dense,
					interactive: __props.interactive
				}]),
				style: normalizeStyle({
					"--chip-accent": __props.accent || "var(--muted)",
					maxWidth: __props.maximumWidth ? __props.maximumWidth + "px" : void 0
				}),
				label: __props.interactive ? __props.text : void 0,
				"translate-label": false,
				disabled: __props.interactive ? __props.disabled : void 0,
				title: __props.text,
				onClick: _cache[0] || (_cache[0] = ($event) => __props.interactive && !__props.disabled && _ctx.$emit("click"))
			}, {
				default: withCtx(() => [__props.icon ? (openBlock(), createBlock(_sfc_main$33, {
					key: 0,
					name: __props.icon
				}, null, 8, ["name"])) : createCommentVNode("", true), __props.dense ? (openBlock(), createBlock(_sfc_main$2, {
					key: 1,
					text: __props.text
				}, null, 8, ["text"])) : (openBlock(), createElementBlock("span", _hoisted_1$1, toDisplayString(__props.text), 1))]),
				_: 1
			}, 8, [
				"class",
				"style",
				"label",
				"disabled",
				"title"
			]);
		};
	}
};
//#endregion
//#region src/frame/FrameView.vue
var _hoisted_1 = ["inert"];
var _hoisted_2 = [
	"data-frame",
	"data-layout-element",
	"role",
	"aria-level",
	"tabindex",
	"title"
];
var _hoisted_3 = { key: 1 };
var _hoisted_4 = {
	key: 1,
	class: "frame-checkbox-label"
};
var _hoisted_5 = ["data-frame", "data-layout-element"];
var _hoisted_6 = [
	"data-frame",
	"data-layout-element",
	"role",
	"aria-label",
	"onScroll"
];
var _hoisted_7 = ["data-frame", "data-layout-element"];
var _hoisted_8 = ["data-frame", "data-layout-element"];
var _hoisted_9 = ["data-frame", "data-layout-element"];
var _sfc_main = /*@__PURE__*/ Object.assign({ name: "FrameView" }, {
	__name: "FrameView",
	props: {
		scene: {
			type: Object,
			required: true
		},
		models: {
			type: Object,
			default: () => ({})
		},
		views: {
			type: Object,
			default: () => ({})
		},
		describeRow: Function,
		describeCell: Function,
		interactive: {
			type: Boolean,
			default: true
		}
	},
	emits: ["event"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const scroll = ref({}), host = ref(null), branches = ref([]), grids = ref([]), graphs = ref([]);
		const nodes = computed(() => validateScene(props.scene, props.models, Object.fromEntries(Object.entries(props.views).map(([name, view]) => [name, view?.component]))));
		const color = (role) => role?.mix ? `color-mix(in srgb, ${color(role.mix[0])} ${(1 - role.mix[2]) * 100}%, ${color(role.mix[1])} ${role.mix[2] * 100}%)` : role === "transparent" ? "transparent" : role?.startsWith("#") ? role : cssRoles[role] ? "var(" + cssRoles[role] + ")" : void 0;
		function previewStyle(node) {
			const bounds = style(node);
			delete bounds.color;
			return bounds;
		}
		function style(node) {
			return {
				transition: node.motion ? Object.entries(node.motion).map(([property, token]) => (property === "x" ? "left" : property === "y" ? "top" : property) + " var(" + {
					clickMotionSlow: "--motion-click-slow",
					clickMotionFast: "--motion-click",
					hoverMotionFast: "--motion-hover"
				}[token] + ") cubic-bezier(.215,.61,.355,1)").join(", ") : void 0,
				zIndex: node.layer,
				left: node.x + "px",
				top: node.y + "px",
				width: node.width + "px",
				height: node.height + "px",
				display: node.visible === false ? "none" : void 0,
				pointerEvents: node.pointerTransparent ? "none" : void 0,
				fontSize: node.fontSize + "px",
				fontWeight: node.weight,
				letterSpacing: node.letterSpacing === void 0 ? void 0 : node.letterSpacing + "px",
				textAlign: node.align,
				fontFamily: node.monospace ? "Consolas" : void 0,
				paddingLeft: node.paddingLeft === void 0 ? void 0 : node.paddingLeft + "px",
				color: color(node.color),
				opacity: node.revealOnRowInteraction ? void 0 : node.opacity,
				transform: node.scale === void 0 ? void 0 : `scale(${node.scale})`,
				transformOrigin: "top left",
				textDecoration: node.strike ? "line-through" : void 0,
				"--frame-button-icon-size": node.iconSize ? node.iconSize + "px" : void 0
			};
		}
		function background(node) {
			const radius = node.radiusRole ? `var(--${node.radiusRole.replace(/[A-Z]/g, (char) => "-" + char.toLowerCase())})` : node.radius === void 0 ? "var(--surface-radius)" : node.radius + "px";
			return {
				background: color(node.background),
				boxShadow: [node.border ? "inset 0 0 0 " + (node.borderWidth || 1) + "px " + color(node.border) : "", node.shadow ? `0 ${node.shadow.y}px ${node.shadow.blur}px color-mix(in srgb, ${color("popupShadow")} ${node.shadow.opacity * 100}%, transparent)` : ""].filter(Boolean).join(", ") || void 0,
				borderRadius: radius,
				borderBottomLeftRadius: node.bottomLeftRadius === void 0 ? radius : node.bottomLeftRadius + "px",
				borderBottomRightRadius: node.bottomRightRadius === void 0 ? radius : node.bottomRightRadius + "px"
			};
		}
		function send(action, value, source) {
			if (action && props.interactive) emit("event", Object.assign({}, action, value === void 0 ? {} : { value }), source);
		}
		function context(event, node) {
			if (!node.contextAction || !props.interactive) return;
			event.preventDefault();
			event.stopPropagation();
			const bounds = event.currentTarget.getBoundingClientRect();
			send(node.contextAction, {
				x: event.clientX - bounds.left,
				y: event.clientY - bounds.top
			}, event.currentTarget);
		}
		function drag(event, node) {
			if (node.dragValue == null) return;
			event.dataTransfer.effectAllowed = "move";
			event.dataTransfer.setData("application/x-tactic-frame", JSON.stringify(node.dragValue));
			send(node.dragStartAction);
		}
		function dragOver(event, node) {
			if (props.interactive && node.enabled !== false && node.dropAction && (event.dataTransfer.types.includes("application/x-tactic-frame") || node.dropAction.name === "file-ingest" && event.dataTransfer.types.includes("Files"))) {
				event.preventDefault();
				event.dataTransfer.dropEffect = node.dropAction.name === "file-ingest" ? "copy" : "move";
			}
		}
		function drop(event, node) {
			if (!props.interactive || node.enabled === false || !node.dropAction) return;
			if (node.dropAction.name === "file-ingest" && event.dataTransfer.files?.length) {
				event.preventDefault();
				send(node.dropAction, Array.from(event.dataTransfer.files));
				return;
			}
			const source = event.dataTransfer.getData("application/x-tactic-frame");
			if (!source) return;
			event.preventDefault();
			try {
				send(node.dropAction, JSON.parse(source));
			} catch (error) {
				if (!(error instanceof SyntaxError)) throw error;
			}
		}
		function sendArea(event, node) {
			if (!node.sendOnEnter || event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.altKey || event.metaKey || event.isComposing || event.keyCode === 229 || event.repeat || matchMedia("(max-width: 640px) and (pointer: coarse)").matches) return;
			event.preventDefault();
			send(node.sendAction);
		}
		function key(event, node) {
			if (event.isComposing || event.keyCode === 229) return;
			if (node.tableCell && (event.shiftKey || event.ctrlKey || event.altKey || event.metaKey)) return;
			const name = event.key === "Tab" && event.shiftKey ? "Backtab" : event.key;
			if (["Button", "Action"].includes(node.kind) && node.enabled && !event.repeat && ["Enter", " "].includes(name) && !node.keys?.[name]) send(node.pressAction, void 0, event.currentTarget);
			if (node.keys?.[name]) {
				event.preventDefault();
				send(node.keys[name]);
			}
		}
		const listLayouts = computed(() => new Map(nodes.value.filter((node) => node.kind === "List").map((node) => [node.id, listOffsets(node, props.models[node.source] || [])])));
		function listHeight(node) {
			const rows = props.models[node.source] || [], offsets = listLayouts.value.get(node.id);
			return offsets ? offsets[rows.length] : rows.length * node.rowHeight;
		}
		function records(node) {
			const rows = props.models[node.source] || [], offsets = listLayouts.value.get(node.id), range = listRange(rows.length, node.rowHeight, node.height, scroll.value[node.id] || 0, 3, offsets);
			return rows.slice(range.first, range.last).map((record, index) => ({
				record,
				index: range.first + index,
				...listBounds(node, offsets, range.first + index)
			}));
		}
		const previousLists = /* @__PURE__ */ new Map();
		watch(() => [props.models, nodes.value], () => {
			const present = /* @__PURE__ */ new Set();
			for (const node of nodes.value) {
				if (node.kind !== "List") continue;
				present.add(node.id);
				const rows = props.models[node.source];
				const offsets = listLayouts.value.get(node.id);
				const previous = previousLists.get(node.id);
				if (previous?.rows === rows && previous.keyField === node.keyField && previous.offsets === offsets && previous.rowHeight === node.rowHeight) continue;
				const indexes = recordIndex(rows, node.keyField);
				const container = host.value?.querySelector(":scope > [data-frame=\"" + CSS.escape(node.id) + "\"]");
				const focused = document.activeElement;
				const focusedRow = container?.contains(focused) ? focused.closest("[data-frame-row]") : null;
				let offset = container ? container.scrollTop : scroll.value[node.id] || 0;
				if (focusedRow && previous) {
					const key = focusedRow.getAttribute("data-frame-row");
					const oldIndex = previous.rows.findIndex((row) => String(row[previous.keyField]) === key);
					if (oldIndex >= 0 && indexes.has(key)) offset += (offsets ? offsets[indexes.get(key)] : indexes.get(key) * node.rowHeight) - (previous.offsets ? previous.offsets[oldIndex] : oldIndex * previous.rowHeight);
				}
				offset = Math.max(0, Math.min(offset, Math.max(0, listHeight(node) - node.height)));
				scroll.value[node.id] = offset;
				previousLists.set(node.id, {
					rows,
					keyField: node.keyField,
					offsets,
					rowHeight: node.rowHeight
				});
				if (container) nextTick(() => {
					if (container.isConnected) container.scrollTop = scroll.value[node.id] || 0;
				});
			}
			for (const id of previousLists.keys()) if (!present.has(id)) previousLists.delete(id);
		}, { immediate: true });
		function focusControl(name) {
			const el = host.value?.querySelector("[data-frame=\"" + CSS.escape(name) + "\"]");
			if (!el) return false;
			const focusable = "input,textarea,select,button,summary,[tabindex]";
			const target = el.matches(focusable) ? el : el.querySelector(focusable);
			target?.focus({ preventScroll: true });
			target?.scrollIntoView({
				block: "nearest",
				inline: "nearest"
			});
			return document.activeElement === target;
		}
		async function focusGrid(id, row, column, name) {
			const grid = grids.value.find((value) => value.$props.node.id === id);
			if (grid) {
				await grid.focusCell(row, column, name);
				return true;
			}
			for (const branch of branches.value) if (await branch.focusGrid(id, row, column, name)) return true;
			return false;
		}
		function graphCommand(id, command) {
			const graph = graphs.value.find((value) => value.$props.node.id === id);
			if (graph) {
				if (command.type === "point") return graph.insertionPoint();
				graph.dispatch(command);
				return true;
			}
			for (const branch of branches.value) {
				const result = branch.graphCommand?.(id, command);
				if (result) return result;
			}
			return null;
		}
		async function focusListRow(id, index, controlId) {
			const definition = nodes.value.find((node) => node.id === id && node.kind === "List");
			if (definition) {
				const rows = props.models[definition.source] || [];
				const list = host.value?.querySelector(":scope > [data-frame=\"" + CSS.escape(id) + "\"]");
				if (!list || index < 0 || index >= rows.length) return false;
				const offset = revealListOffset(list.scrollTop, index, list.clientHeight, rows.length, definition.rowHeight, definition.rowGap ?? 4, listLayouts.value.get(definition.id));
				list.scrollTop = offset;
				scroll.value = {
					...scroll.value,
					[id]: offset
				};
				await nextTick();
				return controlId ? focusControl(controlId) : true;
			}
			for (const branch of branches.value || []) if (await branch?.focusListRow?.(id, index, controlId)) return true;
			return false;
		}
		__expose({
			focusControl,
			focusGrid,
			graphCommand,
			focusListRow
		});
		return (_ctx, _cache) => {
			const _component_FrameView = resolveComponent("FrameView", true);
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: normalizeClass(["frame-view", { "frame-passive": !__props.interactive }]),
				inert: !__props.interactive
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(nodes.value, (node) => {
				return openBlock(), createElementBlock(Fragment, { key: node.id }, [node.kind === "Box" ? (openBlock(), createBlock(resolveDynamicComponent(node.titlebar ? "header" : "div"), {
					key: 0,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node frame-box", { "frame-titlebar": node.titlebar }]),
					style: normalizeStyle(Object.assign(style(node), background(node), {
						overflow: node.clip === false ? "visible" : void 0,
						"--frame-titlebar-actions-right": (node.chromeRight || 0) + "px",
						"--frame-titlebar-actions-top": node.chromeTop !== void 0 ? node.chromeTop + "px" : void 0,
						"--frame-titlebar-actions-height": node.chromeHeight !== void 0 ? node.chromeHeight + "px" : void 0
					})),
					role: node.role,
					"aria-label": node.label,
					onContextmenu: ($event) => context($event, node),
					onDragover: ($event) => dragOver($event, node),
					onDrop: ($event) => drop($event, node)
				}, {
					default: withCtx(() => [node.children?.length ? (openBlock(), createBlock(_component_FrameView, {
						key: 0,
						ref_for: true,
						ref_key: "branches",
						ref: branches,
						scene: { nodes: node.children },
						models: __props.models,
						views: __props.views,
						"describe-row": __props.describeRow,
						"describe-cell": __props.describeCell,
						interactive: __props.interactive,
						onEvent: _cache[0] || (_cache[0] = (action, source) => emit("event", action, source))
					}, null, 8, [
						"scene",
						"models",
						"views",
						"describe-row",
						"describe-cell",
						"interactive"
					])) : createCommentVNode("", true)]),
					_: 2
				}, 1064, [
					"data-frame",
					"data-layout-element",
					"class",
					"style",
					"role",
					"aria-label",
					"onContextmenu",
					"onDragover",
					"onDrop"
				])) : node.kind === "Label" ? withDirectives((openBlock(), createElementBlock("span", {
					key: 1,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					role: node.role,
					"aria-level": node.role === "heading" ? node.level || 2 : void 0,
					tabindex: node.focusable ? 0 : void 0,
					class: normalizeClass(["frame-node frame-label", { "frame-wrap": node.wrap }]),
					style: normalizeStyle(Object.assign(style(node), {
						overflow: node.elide === false ? "visible" : void 0,
						textOverflow: node.elide === false ? "clip" : void 0,
						textAlign: node.align || "left",
						wordBreak: node.wrapAnywhere ? "break-all" : void 0,
						lineHeight: node.wrap || node.verticalAlign === "top" ? "normal" : node.height + "px",
						alignItems: node.verticalAlign === "top" ? "flex-start" : void 0,
						display: node.visible === false ? "none" : node.maxLines ? "-webkit-box" : void 0,
						WebkitLineClamp: node.maxLines || void 0,
						WebkitBoxOrient: node.maxLines ? "vertical" : void 0
					})),
					title: node.toolTip ? void 0 : node.text
				}, [node.elideMiddle ? (openBlock(), createBlock(_sfc_main$2, {
					key: 0,
					text: node.text
				}, null, 8, ["text"])) : (openBlock(), createElementBlock("span", _hoisted_3, toDisplayString(node.text), 1))], 14, _hoisted_2)), [[unref(tooltipDirective), node.toolTip]]) : node.kind === "Icon" ? withDirectives((openBlock(), createBlock(_sfc_main$33, {
					key: 2,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node",
					style: normalizeStyle(Object.assign(style(node), { fontSize: node.width + "px" })),
					name: node.icon,
					"aria-hidden": node.text ? "false" : "true",
					role: node.text ? "img" : void 0,
					"aria-label": node.text || void 0,
					tabindex: node.focusable ? 0 : void 0
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"name",
					"aria-hidden",
					"role",
					"aria-label",
					"tabindex"
				])), [[unref(tooltipDirective), node.toolTip || node.text]]) : node.kind === "Button" ? (openBlock(), createBlock(resolveDynamicComponent(node.tab ? _sfc_main$23 : _sfc_main$34), {
					key: 3,
					onFocus: _cache[1] || (_cache[1] = ($event) => $event.target.scrollIntoView({
						block: "nearest",
						inline: "nearest"
					})),
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node", {
						"frame-button": !node.iconAction && !node.tab,
						"frame-icon-action": node.iconAction,
						"frame-radio": node.radio,
						"frame-radio-selected": node.radio && node.selected
					}]),
					style: normalizeStyle(Object.assign(style(node), {
						borderRadius: node.round ? "999px" : void 0,
						color: node.iconAction && node.enabled !== false && (node.iconColor || node.highlighted) ? color(node.iconColor || "selectedText") : void 0
					})),
					label: node.text,
					"translate-label": false,
					"aria-label": node.label || node.text,
					tooltip: node.toolTip || (node.iconOnly ? node.label || node.text : void 0),
					icon: node.icon,
					"icon-only": node.iconOnly,
					round: !!node.round,
					href: node.href,
					target: node.target,
					rel: node.href ? "noopener noreferrer" : void 0,
					highlighted: node.highlighted,
					"filled-action": node.filledAction,
					segmented: node.radio,
					checked: !!node.selected,
					destructive: node.destructive,
					tonal: node.tonal,
					"badge-count": node.badgeCount || 0,
					"badge-color": node.badgeColor ? color(node.badgeColor) : void 0,
					"show-zero-badge": node.showZeroBadge,
					disabled: !node.enabled,
					role: node.radio ? "radio" : void 0,
					"aria-checked": node.radio ? !!node.selected : void 0,
					tabindex: node.radio && !node.selected ? -1 : void 0,
					onKeydown: ($event) => key($event, node),
					onPointerdown: (event) => {
						if (node.retainFocus) event.preventDefault();
						send(node.pressAction, void 0, event.currentTarget);
					},
					onClick: ($event) => send(node.action, void 0, $event.currentTarget),
					onDragover: ($event) => dragOver($event, node),
					onDrop: ($event) => drop($event, node)
				}, null, 40, [
					"data-frame",
					"data-layout-element",
					"class",
					"style",
					"label",
					"aria-label",
					"tooltip",
					"icon",
					"icon-only",
					"round",
					"href",
					"target",
					"rel",
					"highlighted",
					"filled-action",
					"segmented",
					"checked",
					"destructive",
					"tonal",
					"badge-count",
					"badge-color",
					"show-zero-badge",
					"disabled",
					"role",
					"aria-checked",
					"tabindex",
					"onKeydown",
					"onPointerdown",
					"onClick",
					"onDragover",
					"onDrop"
				])) : node.kind === "Action" ? (openBlock(), createBlock(_sfc_main$34, {
					key: 4,
					id: node.elementId,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node frame-action", { "frame-secondary-action": node.revealOnRowInteraction }]),
					style: normalizeStyle(Object.assign(style(node), { borderRadius: (node.radius === void 0 ? 10 : node.radius) + "px" })),
					label: node.text,
					"translate-label": false,
					disabled: !node.enabled,
					"aria-pressed": node.selected,
					tooltip: node.toolTip,
					"aria-description": node.description,
					role: node.role,
					"aria-level": node.role === "treeitem" ? node.level : void 0,
					"aria-expanded": ["treeitem", "button"].includes(node.role) ? node.expanded : void 0,
					"aria-selected": ["treeitem", "option"].includes(node.role) ? !!node.selected : void 0,
					"aria-checked": node.role === "checkbox" ? node.checked : void 0,
					onPointerdown: ($event) => send(node.pressAction, void 0, $event.currentTarget),
					onFocus: _cache[2] || (_cache[2] = ($event) => $event.target.scrollIntoView({
						block: "nearest",
						inline: "nearest"
					})),
					onKeydown: ($event) => key($event, node),
					onClick: ($event) => send(node.action, void 0, $event.currentTarget),
					onDblclick: ($event) => send(node.doubleAction),
					draggable: node.dragValue != null && __props.interactive,
					onDragstart: ($event) => drag($event, node),
					onDragover: ($event) => dragOver($event, node),
					onDrop: ($event) => drop($event, node)
				}, {
					default: withCtx(() => [createVNode(_sfc_main$4, {
						selected: node.selected,
						accent: color(node.accent),
						"corner-radius": node.radius === void 0 ? 10 : node.radius,
						"normal-color": color(node.normalColor) || "transparent",
						"selected-color": color(node.selectedColor) || "transparent",
						"rail-visible": !!node.rail,
						"separator-visible": false,
						inset: 0
					}, {
						default: withCtx(() => [createVNode(_component_FrameView, {
							ref_for: true,
							ref_key: "branches",
							ref: branches,
							scene: { nodes: node.children },
							interactive: false,
							models: __props.models,
							views: __props.views,
							"describe-row": __props.describeRow,
							"describe-cell": __props.describeCell
						}, null, 8, [
							"scene",
							"models",
							"views",
							"describe-row",
							"describe-cell"
						])]),
						_: 2
					}, 1032, [
						"selected",
						"accent",
						"corner-radius",
						"normal-color",
						"selected-color",
						"rail-visible"
					])]),
					_: 2
				}, 1032, [
					"id",
					"data-frame",
					"data-layout-element",
					"class",
					"style",
					"label",
					"disabled",
					"aria-pressed",
					"tooltip",
					"aria-description",
					"role",
					"aria-level",
					"aria-expanded",
					"aria-selected",
					"aria-checked",
					"onPointerdown",
					"onKeydown",
					"onClick",
					"onDblclick",
					"draggable",
					"onDragstart",
					"onDragover",
					"onDrop"
				])) : node.kind === "Segmented" ? (openBlock(), createBlock(_sfc_main$13, {
					key: 5,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node",
					style: normalizeStyle(style(node)),
					label: node.label,
					options: node.options,
					"model-value": node.value,
					"icon-only": node.iconOnly,
					disabled: !node.enabled,
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"label",
					"options",
					"model-value",
					"icon-only",
					"disabled",
					"onUpdate:modelValue"
				])) : node.kind === "CheckBox" ? (openBlock(), createBlock(_sfc_main$22, {
					key: 6,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node frame-checkbox", { "frame-checkbox-wrap": node.wrapText }]),
					style: normalizeStyle(Object.assign(style(node), { "--frame-indicator-x": (node.indicatorX || 0) + "px" })),
					"model-value": node.checked,
					indeterminate: !!node.mixed,
					compact: node.compact,
					prominent: node.prominent,
					label: node.label || node.text,
					"translate-label": false,
					disabled: !node.enabled,
					onKeydown: ($event) => key($event, node),
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, {
					default: withCtx(() => [createVNode(_sfc_main$4, {
						selected: node.checked,
						"corner-radius": node.radius,
						"normal-color": color(node.normalColor) || "transparent",
						"selected-color": color(node.selectedColor) || "transparent",
						"rail-visible": false,
						"separator-visible": false,
						inset: 0
					}, {
						default: withCtx(() => [node.children?.length ? (openBlock(), createBlock(_component_FrameView, {
							key: 0,
							ref_for: true,
							ref_key: "branches",
							ref: branches,
							scene: { nodes: node.children },
							interactive: false
						}, null, 8, ["scene"])) : (openBlock(), createElementBlock("span", _hoisted_4, [createBaseVNode("span", null, toDisplayString(node.text), 1)]))]),
						_: 2
					}, 1032, [
						"selected",
						"corner-radius",
						"normal-color",
						"selected-color"
					])]),
					_: 2
				}, 1032, [
					"data-frame",
					"data-layout-element",
					"class",
					"style",
					"model-value",
					"indeterminate",
					"compact",
					"prominent",
					"label",
					"disabled",
					"onKeydown",
					"onUpdate:modelValue"
				])) : node.kind === "Switch" ? withDirectives((openBlock(), createElementBlock("div", {
					key: 7,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-switch",
					style: normalizeStyle(style(node))
				}, [createVNode(_sfc_main$32, {
					"model-value": node.checked,
					label: node.text,
					disabled: !node.enabled,
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 8, [
					"model-value",
					"label",
					"disabled",
					"onUpdate:modelValue"
				])], 12, _hoisted_5)), [[unref(tooltipDirective), node.toolTip]]) : node.kind === "Field" ? (openBlock(), createBlock(_sfc_main$29, {
					key: 8,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node frame-field", { "table-cell": node.tableCell }]),
					onFocus: ($event) => {
						$event.target.scrollIntoView({
							block: "nearest",
							inline: "nearest"
						});
						node.selectOnFocus && $event.target.select();
					},
					"error-state": !!node.error,
					style: normalizeStyle(style(node)),
					label: node.label,
					placeholder: node.placeholder,
					"model-value": node.text,
					readonly: node.readOnly,
					maxlength: node.maxLength,
					type: node.password ? "password" : node.inputType || "text",
					autocomplete: node.autocomplete || (node.password ? "new-password" : "off"),
					name: node.name,
					inputmode: node.inputMode,
					disabled: !node.enabled,
					onKeydown: ($event) => key($event, node),
					onClick: ($event) => send(node.activateAction),
					onBlur: ($event) => send(node.commitAction, $event.target.value),
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"onFocus",
					"class",
					"error-state",
					"style",
					"label",
					"placeholder",
					"model-value",
					"readonly",
					"maxlength",
					"type",
					"autocomplete",
					"name",
					"inputmode",
					"disabled",
					"onKeydown",
					"onClick",
					"onBlur",
					"onUpdate:modelValue"
				])) : node.kind === "Area" ? (openBlock(), createBlock(_sfc_main$24, {
					key: 9,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node frame-area", { "frame-notice": node.notice }]),
					onFocus: _cache[3] || (_cache[3] = ($event) => $event.target.scrollIntoView({
						block: "nearest",
						inline: "nearest"
					})),
					role: node.role,
					flat: !!node.flat,
					wrap: node.wrap === false ? "off" : void 0,
					"error-state": !!node.error,
					style: normalizeStyle(style(node)),
					label: node.label,
					placeholder: node.placeholder,
					"model-value": node.text,
					readonly: node.readOnly,
					maxlength: node.maxLength,
					disabled: !node.enabled,
					onKeydown: ($event) => sendArea($event, node),
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"role",
					"class",
					"flat",
					"wrap",
					"error-state",
					"style",
					"label",
					"placeholder",
					"model-value",
					"readonly",
					"maxlength",
					"disabled",
					"onKeydown",
					"onUpdate:modelValue"
				])) : node.kind === "Preview" ? (openBlock(), createBlock(ItemPreview_default, {
					key: 10,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-preview",
					style: normalizeStyle(Object.assign(previewStyle(node), node.radius !== void 0 ? { borderRadius: node.radius + "px" } : node.round === false ? { borderRadius: "4px" } : {})),
					source: node.source,
					"fallback-text": node.initials,
					"fallback-icon": node.icon || "person",
					foreground: node.color ? color(node.color) : void 0,
					accent: node.accent || "action",
					"preview-size": node.width,
					round: node.round !== false,
					outlined: node.outlined !== false,
					selected: node.selected,
					loading: node.loading,
					"fill-mode": node.fit || "cover"
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"source",
					"fallback-text",
					"fallback-icon",
					"foreground",
					"accent",
					"preview-size",
					"round",
					"outlined",
					"selected",
					"loading",
					"fill-mode"
				])) : node.kind === "SummaryChip" ? (openBlock(), createBlock(_sfc_main$3, {
					key: 11,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-summary-chip",
					style: normalizeStyle(style(node)),
					label: node.text,
					count: node.count || 0,
					accent: color(node.accent || "action"),
					icon: node.icon,
					compact: node.compact,
					clickable: !!node.action,
					disabled: !node.enabled,
					"show-count": node.showCount !== false,
					"show-dot": node.showDot !== false,
					onClick: ($event) => send(node.action)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"label",
					"count",
					"accent",
					"icon",
					"compact",
					"clickable",
					"disabled",
					"show-count",
					"show-dot",
					"onClick"
				])) : node.kind === "List" ? (openBlock(), createElementBlock("div", {
					key: 12,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-list",
					role: node.role,
					style: normalizeStyle(style(node)),
					"aria-label": node.label,
					onScroll: ($event) => scroll.value[node.id] = $event.target.scrollTop
				}, [createBaseVNode("div", { style: normalizeStyle({
					position: "relative",
					height: listHeight(node) + "px"
				}) }, [(openBlock(true), createElementBlock(Fragment, null, renderList(records(node), (item) => {
					return openBlock(), createBlock(_component_FrameView, {
						ref_for: true,
						ref_key: "branches",
						ref: branches,
						key: item.record[node.keyField],
						"data-frame-row": String(item.record[node.keyField]),
						class: normalizeClass(["frame-row", { "frame-box": !node.fields.length }]),
						style: normalizeStyle({
							top: item.y + "px",
							height: item.height + "px",
							width: node.width - 16 + "px"
						}),
						scene: __props.describeRow(node, item.record, item.index),
						models: __props.models,
						views: __props.views,
						"describe-row": __props.describeRow,
						"describe-cell": __props.describeCell,
						interactive: __props.interactive,
						onEvent: _cache[4] || (_cache[4] = (action, source) => emit("event", action, source))
					}, null, 8, [
						"data-frame-row",
						"class",
						"style",
						"scene",
						"models",
						"views",
						"describe-row",
						"describe-cell",
						"interactive"
					]);
				}), 128))], 4)], 44, _hoisted_6)) : node.kind === "Scroll" ? (openBlock(), createElementBlock("div", {
					key: node.id + ":" + node.resetKey,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: normalizeClass(["frame-node frame-scroll", { "frame-scroll-horizontal": node.contentWidth > node.width }]),
					style: normalizeStyle(style(node))
				}, [createVNode(_component_FrameView, {
					ref_for: true,
					ref_key: "branches",
					ref: branches,
					style: normalizeStyle({
						height: node.contentHeight + "px",
						width: node.contentWidth === void 0 ? void 0 : Math.max(node.width, node.contentWidth) + "px"
					}),
					scene: { nodes: node.children },
					models: __props.models,
					views: __props.views,
					"describe-row": __props.describeRow,
					"describe-cell": __props.describeCell,
					interactive: __props.interactive,
					onEvent: _cache[5] || (_cache[5] = (action, source) => emit("event", action, source))
				}, null, 8, [
					"style",
					"scene",
					"models",
					"views",
					"describe-row",
					"describe-cell",
					"interactive"
				])], 14, _hoisted_7)) : node.kind === "Choice" ? (openBlock(), createBlock(resolveDynamicComponent(node.editable ? _sfc_main$12 : _sfc_main$31), {
					key: 14,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-choice",
					onFocus: _cache[6] || (_cache[6] = ($event) => $event.target.scrollIntoView({
						block: "nearest",
						inline: "nearest"
					})),
					style: normalizeStyle(style(node)),
					label: node.label,
					"display-prefix": node.displayPrefix,
					"translate-labels": false,
					options: node.options,
					"model-value": node.value,
					placeholder: node.placeholder,
					disabled: !node.enabled,
					onKeydown: ($event) => key($event, node),
					onAccept: ($event) => send(node.commitAction, $event),
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 40, [
					"data-frame",
					"data-layout-element",
					"style",
					"label",
					"display-prefix",
					"options",
					"model-value",
					"placeholder",
					"disabled",
					"onKeydown",
					"onAccept",
					"onUpdate:modelValue"
				])) : node.kind === "IconChoice" ? (openBlock(), createElementBlock("div", {
					key: 15,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-icon-choice",
					style: normalizeStyle(style(node))
				}, [createVNode(_sfc_main$6, {
					"model-value": node.value,
					"tactic-compatible-only": node.tacticCompatibleOnly,
					"icon-only": "",
					disabled: !node.enabled,
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 8, [
					"model-value",
					"tactic-compatible-only",
					"disabled",
					"onUpdate:modelValue"
				])], 12, _hoisted_8)) : node.kind === "ColorChoice" ? (openBlock(), createElementBlock("div", {
					key: 16,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-color-choice",
					style: normalizeStyle(style(node))
				}, [createVNode(_sfc_main$27, {
					"model-value": node.value,
					label: node.label,
					disabled: !node.enabled,
					"onUpdate:modelValue": ($event) => send(node.action, $event)
				}, null, 8, [
					"model-value",
					"label",
					"disabled",
					"onUpdate:modelValue"
				])], 12, _hoisted_9)) : node.kind === "Splitter" ? (openBlock(), createBlock(_sfc_main$5, {
					key: 17,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node frame-splitter",
					style: normalizeStyle(style(node)),
					"model-value": node.value,
					min: node.min,
					max: node.max,
					horizontal: node.horizontal,
					disabled: !node.enabled,
					reverse: node.reverse,
					label: node.text,
					"onUpdate:modelValue": ($event) => send(node.action, $event),
					onCommitted: ($event) => node.commitAction && send(node.commitAction, $event),
					onCancelled: ($event) => node.cancelAction && send(node.cancelAction, $event)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"model-value",
					"min",
					"max",
					"horizontal",
					"disabled",
					"reverse",
					"label",
					"onUpdate:modelValue",
					"onCommitted",
					"onCancelled"
				])) : node.kind === "StatusChip" ? (openBlock(), createBlock(_sfc_main$1, {
					key: 18,
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					class: "frame-node",
					style: normalizeStyle(Object.assign(style(node), {
						fontSize: void 0,
						fontWeight: void 0,
						color: void 0
					})),
					text: node.text,
					icon: node.icon,
					accent: color(node.accent),
					dense: node.dense,
					interactive: !!node.action,
					disabled: !node.enabled,
					onClick: ($event) => send(node.action)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"text",
					"icon",
					"accent",
					"dense",
					"interactive",
					"disabled",
					"onClick"
				])) : node.kind === "DateChoice" ? (openBlock(), createBlock(_sfc_main$25, {
					key: 19,
					class: "frame-node frame-date-choice",
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					style: normalizeStyle(style(node)),
					"model-value": node.text,
					label: node.label,
					"include-time": !!node.includeTime,
					"month-only": !!node.monthOnly,
					"allow-clear": node.allowClear !== false,
					readonly: !!node.readOnly,
					disabled: !node.enabled,
					"onUpdate:modelValue": ($event) => send(node.action, $event),
					onChange: ($event) => send(node.commitAction, $event)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"model-value",
					"label",
					"include-time",
					"month-only",
					"allow-clear",
					"readonly",
					"disabled",
					"onUpdate:modelValue",
					"onChange"
				])) : node.kind === "UserChoice" ? (openBlock(), createBlock(_sfc_main$14, {
					key: 20,
					class: "frame-node frame-user-choice",
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					style: normalizeStyle(style(node)),
					value: node.value,
					options: node.options || [],
					label: node.label,
					"empty-label": node.options?.find((option) => option.value === "")?.label || "Not assigned",
					"action-field": !!node.actionField,
					disabled: !node.enabled,
					onChange: ($event) => send(node.action, $event)
				}, null, 8, [
					"data-frame",
					"data-layout-element",
					"style",
					"value",
					"options",
					"label",
					"empty-label",
					"action-field",
					"disabled",
					"onChange"
				])) : node.kind === "Search" ? (openBlock(), createBlock(AppSearchField_default, {
					key: 21,
					class: "frame-node",
					"data-frame": node.id,
					style: normalizeStyle(style(node)),
					"model-value": node.text,
					placeholder: node.placeholder,
					label: node.label,
					disabled: !__props.interactive || !node.enabled,
					readonly: node.readOnly,
					suggestions: node.suggestions || [],
					error: node.errorText || "",
					"onUpdate:modelValue": (value) => send(node.action, value),
					onSearch: ($event) => send(node.commitAction),
					onAccept: (record) => send(node.acceptAction, record)
				}, null, 8, [
					"data-frame",
					"style",
					"model-value",
					"placeholder",
					"label",
					"disabled",
					"readonly",
					"suggestions",
					"error",
					"onUpdate:modelValue",
					"onSearch",
					"onAccept"
				])) : node.kind === "Identity" ? (openBlock(), createBlock(_sfc_main$19, {
					key: 22,
					class: "frame-node",
					"data-frame": node.id,
					style: normalizeStyle(style(node)),
					login: node.login || "",
					"display-name": node.text,
					initials: node.initials || "",
					"avatar-url": node.url || "",
					"avatar-color": color(node.accent || "action"),
					"avatar-size": node.avatarSize || 40,
					retired: node.retired,
					emphasized: node.emphasized
				}, null, 8, [
					"data-frame",
					"style",
					"login",
					"display-name",
					"initials",
					"avatar-url",
					"avatar-color",
					"avatar-size",
					"retired",
					"emphasized"
				])) : node.kind === "Progress" ? (openBlock(), createBlock(AppProgress_default, {
					key: 23,
					class: "frame-node",
					"data-frame": node.id,
					style: normalizeStyle(style(node)),
					label: node.text,
					value: node.indeterminate ? void 0 : node.value,
					min: node.min ?? 0,
					max: node.max ?? 1
				}, null, 8, [
					"data-frame",
					"style",
					"label",
					"value",
					"min",
					"max"
				])) : node.kind === "Empty" ? (openBlock(), createBlock(_sfc_main$17, {
					key: 24,
					class: "frame-node",
					"data-frame": node.id,
					style: normalizeStyle(style(node)),
					title: node.text,
					message: node.message,
					icon: node.icon || "info",
					error: node.error,
					action: node.action ? {
						label: node.actionText,
						icon: node.actionIcon,
						disabled: !__props.interactive || !node.enabled || node.readOnly
					} : void 0,
					onAction: ($event) => send(node.action)
				}, null, 8, [
					"data-frame",
					"style",
					"title",
					"message",
					"icon",
					"error",
					"action",
					"onAction"
				])) : node.kind === "FileField" ? (openBlock(), createBlock(_sfc_main$16, {
					key: 25,
					class: "frame-node",
					"data-frame": node.id,
					style: normalizeStyle(style(node)),
					value: node.text,
					label: node.label,
					disabled: !__props.interactive || !node.enabled || node.readOnly,
					onChange: (event) => send(node.action, Array.from(event.target.files || []))
				}, null, 8, [
					"data-frame",
					"style",
					"value",
					"label",
					"disabled",
					"onChange"
				])) : node.kind === "Grid" ? (openBlock(), createBlock(_sfc_main$11, {
					key: 26,
					ref_for: true,
					ref_key: "grids",
					ref: grids,
					class: "frame-node",
					style: normalizeStyle(style(node)),
					node,
					source: __props.models[node.source],
					"describe-cell": __props.describeCell,
					onEvent: _cache[7] || (_cache[7] = (action, source) => emit("event", action, source))
				}, null, 8, [
					"style",
					"node",
					"source",
					"describe-cell"
				])) : node.kind === "Graph" ? (openBlock(), createBlock(FrameGraph_default, {
					key: 27,
					ref_for: true,
					ref_key: "graphs",
					ref: graphs,
					class: "frame-node",
					style: normalizeStyle(style(node)),
					node,
					onEvent: _cache[8] || (_cache[8] = (action, source) => emit("event", action, source))
				}, null, 8, ["style", "node"])) : node.kind === "Chart" ? (openBlock(), createBlock(_sfc_main$9, {
					key: 28,
					class: "frame-node",
					style: normalizeStyle(style(node)),
					node
				}, null, 8, ["style", "node"])) : node.kind === "Code" ? (openBlock(), createBlock(FrameCode_default, {
					key: 29,
					class: "frame-node",
					style: normalizeStyle(style(node)),
					node,
					onEvent: _cache[9] || (_cache[9] = (action, source) => emit("event", action, source))
				}, null, 8, ["style", "node"])) : node.kind === "View" ? (openBlock(), createBlock(resolveDynamicComponent(__props.views[node.view]?.component), mergeProps({
					key: 30,
					ref_for: true,
					ref: __props.views[node.view]?.captureRef
				}, { ref_for: true }, __props.views[node.view]?.props, {
					"frame-node": __props.views[node.view]?.nodeProps ? node : void 0,
					class: "frame-node frame-child-view",
					"data-frame": node.id,
					"data-layout-element": node.layoutElement,
					style: style(node)
				}), null, 16, [
					"frame-node",
					"data-frame",
					"data-layout-element",
					"style"
				])) : createCommentVNode("", true)], 64);
			}), 128))], 10, _hoisted_1);
		};
	}
});
//#endregion
export { _sfc_main$22 as A, _sfc_main$30 as B, _sfc_main$16 as C, _sfc_main$19 as D, AppProgress_default as E, localDate as F, button as G, observeFrameSizes as H, monthLabel as I, muted as J, label as K, parse as L, _sfc_main$24 as M, _sfc_main$25 as N, ItemPreview_default as O, _sfc_main$26 as P, virtualRange as Q, _sfc_main$27 as R, _sfc_main$15 as S, _sfc_main$17 as T, _sfc_main$31 as U, frameContentWidth as V, _sfc_main$32 as W, rect as X, node as Y, revealListOffset as Z, describe as _, _sfc_main$4 as a, _sfc_main$14 as b, _sfc_main$8 as c, javascriptTokens as d, pythonTokens as f, readClipboardImages as g, copyText as h, _sfc_main$3 as i, _sfc_main$23 as j, AppSearchField_default as k, completions as l, copyImage as m, _sfc_main$1 as n, _sfc_main$5 as o, xmlTokens as p, listRowHeight as q, _sfc_main$2 as r, toolbar as s, _sfc_main as t, documentSymbols as u, geometry as v, translate as w, matchesUser as x, _sfc_main$13 as y, _sfc_main$29 as z };

//# sourceMappingURL=FrameView.js.map
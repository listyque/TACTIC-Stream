import { D as nextTick, E as mergeProps, G as withCtx, H as watch, N as openBlock, P as renderList, T as mergeModels, V as useModel, X as ref, _ as createCommentVNode, b as createTextVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, m as computed, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, x as createVNode, z as useAttrs } from "./vue.js";
import { E as appearance, M as controls, T as t, c as _sfc_main$4, i as _sfc_main$3 } from "./index.js";
import { t as _sfc_main$5 } from "./AppSlider.js";
import { t as _sfc_main$6 } from "./AppTextField.js";
import { t as _sfc_main$7 } from "./AppMenu.js";
//#region src/controls/ColorPicker.vue
var _hoisted_1$2 = ["aria-label"];
var _hoisted_2$2 = { class: "color-picker-fields" };
var _hoisted_3$1 = [
	"aria-label",
	"aria-valuetext",
	"aria-valuenow",
	"aria-description"
];
var _hoisted_4$1 = { class: "color-picker-hex" };
var _sfc_main$2 = {
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
				createBaseVNode("div", _hoisted_2$2, [
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
					}) }, null, 4)], 44, _hoisted_3$1),
					createBaseVNode("label", null, toDisplayString(unref(t)("Hue")), 1),
					createVNode(_sfc_main$5, {
						modelValue: hue.value,
						"onUpdate:modelValue": [_cache[0] || (_cache[0] = ($event) => hue.value = $event), updateHex],
						label: "Hue",
						min: 0,
						max: 1,
						step: .005,
						class: "color-picker-hue"
					}, null, 8, ["modelValue"]),
					createBaseVNode("div", _hoisted_4$1, [createBaseVNode("span", {
						class: "color-swatch",
						style: normalizeStyle({ background: valid.value ? hex.value : "#000000" }),
						"aria-hidden": "true"
					}, null, 4), createVNode(_sfc_main$6, {
						modelValue: hex.value,
						"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => hex.value = $event),
						label: "Color in HEX format",
						"aria-invalid": !valid.value,
						onChange: _cache[2] || (_cache[2] = ($event) => setColor(hex.value))
					}, null, 8, ["modelValue", "aria-invalid"])])
				]),
				createBaseVNode("footer", null, [createVNode(_sfc_main$3, {
					label: "Cancel",
					onClick: _cache[3] || (_cache[3] = ($event) => dialog.value.close())
				}), createVNode(_sfc_main$3, {
					label: "OK",
					disabled: !valid.value,
					onClick: accept
				}, null, 8, ["disabled"])])
			], 40, _hoisted_1$2);
		};
	}
};
//#endregion
//#region src/controls/AppColorInput.vue
var _hoisted_1$1 = { class: "app-color-input" };
var _hoisted_2$1 = ["name", "value"];
var _sfc_main$1 = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
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
			return openBlock(), createElementBlock("div", _hoisted_1$1, [
				createBaseVNode("span", {
					class: "color-swatch",
					style: normalizeStyle({ background: swatch.value }),
					"aria-hidden": "true"
				}, null, 4),
				createVNode(_sfc_main$3, {
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
				}, null, 8, _hoisted_2$1)) : createCommentVNode("", true),
				createVNode(_sfc_main$2, {
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
//#region src/controls/AppDateField.vue
var _hoisted_1 = ["data-frame"];
var _hoisted_2 = {
	key: 0,
	class: "app-date-presentation",
	"aria-hidden": "true"
};
var _hoisted_3 = { class: "date-calendar" };
var _hoisted_4 = { class: "date-calendar-heading" };
var _hoisted_5 = ["aria-label"];
var _hoisted_6 = {
	key: 1,
	class: "calendar-empty"
};
var _hoisted_7 = {
	key: 0,
	class: "date-calendar-time"
};
var _hoisted_8 = { key: 0 };
var _hoisted_9 = { class: "date-time-spin" };
var _hoisted_10 = [
	"value",
	"max",
	"aria-label",
	"onInput",
	"onKeydown"
];
var _hoisted_11 = { class: "date-calendar-footer" };
var _sfc_main = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppDateField",
	props: {
		modelValue: String,
		label: String,
		disabled: Boolean,
		readonly: Boolean,
		includeTime: {
			type: Boolean,
			default: true
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
			return `${parts.day} ${parts.month} ${parts.year}`;
		}
		const presentation = computed(() => {
			const date = parse$1(props.modelValue);
			if (!date) return props.modelValue || "";
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
				createVNode(_sfc_main$6, mergeProps({
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
				!focused.value && __props.modelValue ? (openBlock(), createElementBlock("span", _hoisted_2, toDisplayString(presentation.value), 1)) : createCommentVNode("", true),
				createVNode(_sfc_main$7, {
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
					trigger: withCtx(() => [createVNode(_sfc_main$4, { name: "MDI_CALENDAR_MONTH" })]),
					default: withCtx(() => [createBaseVNode("div", _hoisted_3, [
						createBaseVNode("header", _hoisted_4, [
							createVNode(_sfc_main$3, {
								label: "Previous month",
								icon: "previous",
								"icon-only": "",
								onClick: _cache[2] || (_cache[2] = ($event) => moveMonth(-1))
							}),
							createBaseVNode("strong", null, toDisplayString(heading.value), 1),
							createVNode(_sfc_main$3, {
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
							return openBlock(), createElementBlock(Fragment, { key: index }, [day ? (openBlock(), createBlock(_sfc_main$3, {
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
							])) : (openBlock(), createElementBlock("span", _hoisted_6))], 64);
						}), 128))], 8, _hoisted_5),
						__props.includeTime ? (openBlock(), createElementBlock("div", _hoisted_7, [createBaseVNode("span", null, toDisplayString(unref(t)("Time")), 1), (openBlock(), createElementBlock(Fragment, null, renderList(["hour", "minute"], (name) => {
							return openBlock(), createElementBlock(Fragment, { key: name }, [name === "minute" ? (openBlock(), createElementBlock("span", _hoisted_8, ":")) : createCommentVNode("", true), createBaseVNode("div", _hoisted_9, [
								createVNode(_sfc_main$3, {
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
								}, null, 40, _hoisted_10),
								createVNode(_sfc_main$3, {
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
						createBaseVNode("footer", _hoisted_11, [__props.allowClear ? (openBlock(), createBlock(_sfc_main$3, {
							key: 0,
							label: "Clear",
							onClick: _cache[4] || (_cache[4] = ($event) => accept(null))
						})) : createCommentVNode("", true), createVNode(_sfc_main$3, {
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
			], 14, _hoisted_1);
		};
	}
});
//#endregion
export { _sfc_main$1 as n, _sfc_main as t };

//# sourceMappingURL=AppDateField.js.map
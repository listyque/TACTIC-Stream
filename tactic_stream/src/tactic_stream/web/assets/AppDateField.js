import { D as nextTick, E as mergeProps, G as withCtx, H as watch, N as openBlock, P as renderList, X as ref, _ as createCommentVNode, b as createTextVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, m as computed, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, x as createVNode } from "./vue.js";
import { E as appearance, T as t, c as _sfc_main$1, i as _sfc_main$2 } from "./index.js";
import { t as _sfc_main$3 } from "./AppTextField.js";
import { t as _sfc_main$4 } from "./AppMenu.js";
//#region src/controls/AppDateField.vue
var _hoisted_1 = {
	key: 0,
	class: "app-date-presentation",
	"aria-hidden": "true"
};
var _hoisted_2 = { class: "date-calendar" };
var _hoisted_3 = { class: "date-calendar-heading" };
var _hoisted_4 = ["aria-label"];
var _hoisted_5 = {
	key: 1,
	class: "calendar-empty"
};
var _hoisted_6 = {
	key: 0,
	class: "date-calendar-time"
};
var _hoisted_7 = { key: 0 };
var _hoisted_8 = { class: "date-time-spin" };
var _hoisted_9 = [
	"value",
	"max",
	"aria-label",
	"onInput",
	"onKeydown"
];
var _hoisted_10 = { class: "date-calendar-footer" };
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
		const host = ref(null), field = ref(null), menu = ref(null), focused = ref(false), available = ref(0);
		const month = ref(/* @__PURE__ */ new Date()), pending = ref(/* @__PURE__ */ new Date()), hour = ref(0), minute = ref(0);
		let observer;
		const pad = (value) => String(value).padStart(2, "0");
		function parse(value) {
			const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,3})?)?)?$/);
			if (!match || !props.includeTime && match[4]) return null;
			const year = Number(match[1]), month = Number(match[2]), day = Number(match[3]), hour = Number(match[4] || 0), minute = Number(match[5] || 0), second = Number(match[6] || 0);
			const date = new Date(year, month - 1, day, hour, minute, second);
			return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day && date.getHours() === hour && date.getMinutes() === minute && date.getSeconds() === second ? date : null;
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
			const date = parse(props.modelValue);
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
		const weekdays = computed(() => Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(appearance.language, { weekday: "narrow" }).format(new Date(2024, 0, 1 + index))));
		const days = computed(() => {
			const offset = (new Date(month.value.getFullYear(), month.value.getMonth(), 1).getDay() + 6) % 7;
			const count = new Date(month.value.getFullYear(), month.value.getMonth() + 1, 0).getDate();
			return Array.from({ length: 42 }, (_, index) => {
				const day = index - offset + 1;
				return day > 0 && day <= count ? day : 0;
			});
		});
		function sameDay(date, day) {
			return date.getFullYear() === month.value.getFullYear() && date.getMonth() === month.value.getMonth() && date.getDate() === day;
		}
		function opened(event) {
			if (event.target !== menu.value?.$el || event.newState !== "open") return;
			const now = /* @__PURE__ */ new Date(), date = parse(props.modelValue) || now, explicit = /[ T]\d{2}:\d{2}/.test(props.modelValue || "");
			pending.value = date;
			month.value = new Date(date.getFullYear(), date.getMonth(), 1);
			hour.value = explicit ? date.getHours() : now.getHours();
			minute.value = explicit ? date.getMinutes() : 0;
			nextTick(() => menu.value.$el.querySelector(".calendar-day.selected")?.focus());
		}
		function moveMonth(step) {
			month.value = new Date(month.value.getFullYear(), month.value.getMonth() + step, 1);
		}
		function accept(date) {
			if (props.disabled || props.readonly) return;
			if (date && props.includeTime && (!Number.isInteger(hour.value) || !Number.isInteger(minute.value) || hour.value < 0 || hour.value > 23 || minute.value < 0 || minute.value > 59)) {
				menu.value.$el.querySelector("input:invalid")?.reportValidity();
				return;
			}
			const value = date ? `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` + (props.includeTime ? `T${pad(hour.value)}:${pad(minute.value)}` : "") : "";
			field.value.$el.setCustomValidity("");
			emit("update:modelValue", value);
			emit("change", value);
			menu.value.close(true);
		}
		function validate(value) {
			field.value?.$el.setCustomValidity(value && !parse(value) ? t("Enter a valid date and time") : "");
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
			const date = new Date(month.value.getFullYear(), month.value.getMonth(), day + step);
			month.value = new Date(date.getFullYear(), date.getMonth(), 1);
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
				class: normalizeClass(["app-date-field", {
					focused: focused.value,
					disabled: __props.disabled
				}])
			}, [
				createVNode(_sfc_main$3, mergeProps({
					ref_key: "field",
					ref: field
				}, _ctx.$attrs, {
					type: "text",
					"model-value": __props.modelValue,
					label: __props.label,
					placeholder: __props.placeholder || (__props.includeTime ? "YYYY-MM-DD HH:mm" : "YYYY-MM-DD"),
					disabled: __props.disabled,
					readonly: __props.readonly,
					"aria-invalid": __props.modelValue && !parse(__props.modelValue) || void 0,
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
				!focused.value && __props.modelValue ? (openBlock(), createElementBlock("span", _hoisted_1, toDisplayString(presentation.value), 1)) : createCommentVNode("", true),
				createVNode(_sfc_main$4, {
					ref_key: "menu",
					ref: menu,
					class: "app-date-menu",
					label: __props.includeTime ? "Choose date and time" : "Choose date",
					disabled: __props.disabled || __props.readonly,
					overlay: "",
					"align-start": "",
					anchor: host.value,
					width: 304,
					"close-on-select": false,
					onToggle: opened
				}, {
					trigger: withCtx(() => [createVNode(_sfc_main$1, { name: "MDI_CALENDAR_MONTH" })]),
					default: withCtx(() => [createBaseVNode("div", _hoisted_2, [
						createBaseVNode("header", _hoisted_3, [
							createVNode(_sfc_main$2, {
								label: "Previous month",
								icon: "previous",
								"icon-only": "",
								onClick: _cache[2] || (_cache[2] = ($event) => moveMonth(-1))
							}),
							createBaseVNode("strong", null, toDisplayString(heading.value), 1),
							createVNode(_sfc_main$2, {
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
							return openBlock(), createElementBlock(Fragment, { key: index }, [day ? (openBlock(), createBlock(_sfc_main$2, {
								key: 0,
								class: normalizeClass(["calendar-day", {
									selected: sameDay(pending.value, day),
									today: sameDay(/* @__PURE__ */ new Date(), day)
								}]),
								"data-day": day,
								"aria-label": dateLabel(new Date(month.value.getFullYear(), month.value.getMonth(), day)),
								"aria-pressed": sameDay(pending.value, day),
								onKeydown: ($event) => dayKey($event, day),
								onClick: ($event) => accept(new Date(month.value.getFullYear(), month.value.getMonth(), day))
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
							])) : (openBlock(), createElementBlock("span", _hoisted_5))], 64);
						}), 128))], 8, _hoisted_4),
						__props.includeTime ? (openBlock(), createElementBlock("div", _hoisted_6, [createBaseVNode("span", null, toDisplayString(unref(t)("Time")), 1), (openBlock(), createElementBlock(Fragment, null, renderList(["hour", "minute"], (name) => {
							return openBlock(), createElementBlock(Fragment, { key: name }, [name === "minute" ? (openBlock(), createElementBlock("span", _hoisted_7, ":")) : createCommentVNode("", true), createBaseVNode("div", _hoisted_8, [
								createVNode(_sfc_main$2, {
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
								}, null, 40, _hoisted_9),
								createVNode(_sfc_main$2, {
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
						createBaseVNode("footer", _hoisted_10, [__props.allowClear ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							label: "Clear",
							onClick: _cache[4] || (_cache[4] = ($event) => accept(null))
						})) : createCommentVNode("", true), createVNode(_sfc_main$2, {
							label: "Today",
							onClick: _cache[5] || (_cache[5] = ($event) => accept(/* @__PURE__ */ new Date()))
						})])
					])]),
					_: 1
				}, 8, [
					"label",
					"disabled",
					"anchor"
				])
			], 2);
		};
	}
});
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppDateField.js.map
import { A as onMounted, E as nextTick, G as withCtx, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { D as t, O as appearance, o as _sfc_main$2, u as _sfc_main$1 } from "./index.js";
import { f as _sfc_main$3 } from "./clipboard.js";
import { t as _sfc_main$4 } from "./AppMenu.js";
import { t as _sfc_main$5 } from "./AppCheckbox.js";
import { t as ItemPreview_default } from "./ItemPreview.js";
//#region src/features/tasks/TaskGanttView.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "gantt-heading" };
var _hoisted_3 = { class: "gantt-heading-label" };
var _hoisted_4 = { class: "gantt-heading-copy" };
var _hoisted_5 = ["aria-label"];
var _hoisted_6 = ["data-task-key"];
var _hoisted_7 = { class: "task-gantt-label task-gantt-section" };
var _hoisted_8 = { class: "task-gantt-label" };
var _hoisted_9 = { class: "task-gantt-timeline" };
var _hoisted_10 = { class: "task-gantt-label" };
var _hoisted_11 = ["onPointerdown", "onDblclick"];
var _hoisted_12 = ["title"];
var _hoisted_13 = { class: "gantt-date-chip start" };
var _hoisted_14 = { class: "gantt-date-chip end" };
var _hoisted_15 = {
	key: 0,
	class: "gantt-empty"
};
var _hoisted_16 = { class: "gantt-overview" };
var _hoisted_17 = ["title"];
var _hoisted_18 = [
	"aria-label",
	"aria-valuemax",
	"aria-valuenow"
];
var _hoisted_19 = { class: "gantt-footer" };
var _sfc_main = {
	__name: "TaskGanttView",
	props: {
		projection: Object,
		tasks: {
			type: Array,
			default: () => []
		},
		selected: {
			type: Array,
			default: () => []
		},
		collapsed: {
			type: Array,
			default: () => []
		},
		busy: Boolean,
		projecting: Boolean,
		workingDays: Boolean,
		resourceMode: Boolean,
		canUndo: Boolean,
		canRedo: Boolean,
		active: String,
		hasMore: Boolean
	},
	emits: [
		"select",
		"select-all",
		"activate",
		"object",
		"collapse",
		"edit",
		"inspect",
		"working-days",
		"resource-mode",
		"undo",
		"redo",
		"batch",
		"schedule",
		"milestone",
		"progress",
		"delete",
		"load-more"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const root = ref(null), body = ref(null), viewport = ref(800), gutter = ref(0), scrollX = ref(0), scrollY = ref(0), bodyHeight = ref(400), zoom = ref(1), scale = ref("auto"), drag = ref(null);
		let observer, resizeFrame, autoScroll, ignoreClickUntil = 0;
		const range = computed(() => props.projection?.gantt);
		const dayCount = computed(() => Math.max(1, range.value?.days || 1));
		const labelWidth = computed(() => Math.min(310, Math.max(220, viewport.value * .3)));
		const timelineViewport = computed(() => Math.max(1, viewport.value - labelWidth.value - gutter.value));
		const baseDayWidth = computed(() => Math.max(10, Math.min(28, timelineViewport.value / dayCount.value)));
		const dayWidth = computed(() => Math.max(2, Math.min(80, baseDayWidth.value * zoom.value)));
		const timelineWidth = computed(() => Math.max(timelineViewport.value, dayCount.value * dayWidth.value));
		const tasksByKey = computed(() => new Map(props.tasks.map((task) => [task.key, task])));
		const ticks = computed(() => {
			const mode = dayWidth.value >= 22 ? "days" : dayWidth.value >= 7 ? "weeks" : dayWidth.value >= 2.8 ? "months" : "quarters";
			return (range.value?.tickSets[mode] || []).filter((tick) => tick.offsetDay * dayWidth.value >= scrollX.value - 100 && tick.offsetDay * dayWidth.value <= scrollX.value + timelineViewport.value + 100);
		});
		const rows = computed(() => {
			const result = [];
			let top = 0;
			function add(kind, key, record, height) {
				result.push({
					kind,
					key,
					record,
					height,
					top
				});
				top += height;
			}
			for (const record of range.value?.records || []) {
				if (record.ganttSectionFirst) add("section", "section:" + record.ganttSection, record, 28);
				if (record.groupFirst && record.groupKey) add("group", record.ganttSection + ":" + record.groupKey, record, 27);
				if (!props.collapsed.includes(record.groupKey)) add("task", record.taskCode, record, 50);
			}
			return result;
		});
		const totalHeight = computed(() => rows.value.at(-1) ? rows.value.at(-1).top + rows.value.at(-1).height : 0);
		const visibleRows = computed(() => rows.value.filter((row) => row.top + row.height >= scrollY.value - 100 && row.top < scrollY.value + bodyHeight.value + 100));
		const grid = computed(() => {
			const first = Math.max(0, Math.floor(scrollX.value / dayWidth.value) - 1), last = Math.min(dayCount.value, Math.ceil((scrollX.value + timelineViewport.value) / dayWidth.value) + 1);
			return Array.from({ length: Math.max(0, last - first + 1) }, (_, index) => {
				const day = first + index, date = /* @__PURE__ */ new Date(dateForDay(day) + "T12:00:00Z");
				return {
					day,
					major: date.getUTCDate() === 1,
					week: date.getUTCDay() === 1
				};
			});
		});
		const warningCount = computed(() => range.value?.warnings || 0);
		const overviewThumb = computed(() => ({
			left: scrollX.value / timelineWidth.value * 100 + "%",
			width: Math.min(100, timelineViewport.value / timelineWidth.value * 100) + "%"
		}));
		const batchActions = [
			[
				"Shift one day earlier",
				"shift",
				-1
			],
			[
				"Shift one day later",
				"shift",
				1
			],
			[
				"Align start dates",
				"align-start",
				1
			],
			[
				"Align deadlines",
				"align-end",
				1
			],
			[
				"Schedule sequentially",
				"sequence",
				1
			],
			[
				"Extend by one day",
				"extend",
				1
			],
			[
				"Shorten by one day",
				"shorten",
				1
			]
		];
		function dateForDay(day) {
			const value = /* @__PURE__ */ new Date((range.value?.rangeStart || "2000-01-01") + "T12:00:00Z");
			value.setUTCDate(value.getUTCDate() + day);
			return value.toISOString().slice(0, 10);
		}
		function dateLabel(value, options = {
			month: "short",
			day: "numeric"
		}) {
			return value ? new Intl.DateTimeFormat(appearance.language, options).format(/* @__PURE__ */ new Date(value.slice(0, 10) + "T12:00:00")) : "—";
		}
		function tickLabel(tick) {
			if (dayWidth.value >= 22) return dateLabel(tick.date, { day: "numeric" });
			if (dayWidth.value >= 7) return dateLabel(tick.date);
			if (dayWidth.value >= 2.8) return dateLabel(tick.date, {
				month: "short",
				year: "numeric"
			});
			return t("Q{quarter} {year}", {
				quarter: Math.floor((Number(tick.date.slice(5, 7)) - 1) / 3) + 1,
				year: tick.date.slice(0, 4)
			});
		}
		function warningText(record) {
			return (record.ganttWarning || record.ganttIssue || "").split("\n").map((value) => t(value)).join("\n");
		}
		function color(record) {
			return tasksByKey.value.get(record.taskCode)?.__status__?.color || record.ganttColor || "var(--primary)";
		}
		function progress(record) {
			return drag.value?.key === record.taskCode && drag.value.mode === "progress" ? drag.value.progress : record.progress;
		}
		function geometry(record) {
			const pending = drag.value?.key === record.taskCode && drag.value.mode !== "progress" ? drag.value : null;
			return {
				left: (pending?.start ?? record.ganttStartDay) * dayWidth.value + "px",
				width: Math.max(7, (pending?.duration ?? record.ganttDurationDays) * dayWidth.value - 4) + "px",
				"--bar-color": color(record)
			};
		}
		function synchronize() {
			scrollX.value = body.value.scrollLeft;
			scrollY.value = body.value.scrollTop;
		}
		function setScroll(value) {
			body.value.scrollLeft = Math.max(0, Math.min(timelineWidth.value - timelineViewport.value, value));
			synchronize();
		}
		async function setZoom(value, anchor = timelineViewport.value / 2, mode = "custom") {
			const day = (scrollX.value + anchor) / dayWidth.value;
			scale.value = mode;
			zoom.value = Math.max(.15, Math.min(5, value));
			await nextTick();
			setScroll(day * dayWidth.value - anchor);
		}
		function setScale(mode) {
			setZoom({
				days: 28,
				weeks: 12,
				months: 5,
				quarters: 2,
				auto: baseDayWidth.value
			}[mode] / baseDayWidth.value, timelineViewport.value / 2, mode);
		}
		function wheel(event) {
			event.preventDefault();
			if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) setScroll(scrollX.value + (event.deltaX || event.deltaY) * 1.65);
			else setZoom(zoom.value * Math.pow(1.16, -event.deltaY / (event.deltaMode === 1 ? 3 : 100)), Math.max(0, event.clientX - event.currentTarget.getBoundingClientRect().left));
		}
		function edit(key) {
			if (performance.now() >= ignoreClickUntil && !props.busy) emit("edit", key);
		}
		function begin(record, mode, event) {
			if (props.busy || event.pointerType !== "mouse" || event.button !== 0) return;
			event.preventDefault();
			event.stopPropagation();
			event.currentTarget.setPointerCapture(event.pointerId);
			const box = event.currentTarget.closest(".task-gantt-timeline").getBoundingClientRect();
			drag.value = {
				key: record.taskCode,
				mode,
				x: event.clientX,
				baseScroll: scrollX.value,
				baseStart: record.ganttStartDay,
				baseDuration: record.ganttDurationDays,
				start: record.ganttStartDay,
				duration: Math.max(1, record.ganttDurationDays),
				progress: record.progress,
				baseProgress: record.progress,
				clientX: event.clientX,
				barLeft: box.left + record.ganttStartDay * dayWidth.value,
				barWidth: Math.max(7, record.ganttDurationDays * dayWidth.value - 4)
			};
			if (mode === "create") {
				drag.value.start = Math.round((event.clientX - box.left) / dayWidth.value);
				drag.value.baseStart = drag.value.start;
				drag.value.duration = 1;
			}
			autoScroll = setInterval(() => {
				if (!drag.value || drag.value.mode === "progress") return;
				const rect = body.value.getBoundingClientRect(), x = drag.value.clientX;
				if (x < rect.left + labelWidth.value + 28) setScroll(scrollX.value - 10);
				else if (x > rect.right - 28) setScroll(scrollX.value + 10);
				updateDrag(x);
			}, 20);
		}
		function updateDrag(x) {
			const value = drag.value;
			if (!value) return;
			value.clientX = x;
			if (value.mode === "progress") {
				value.progress = Math.max(0, Math.min(100, Math.round((x - value.barLeft) / value.barWidth * 100)));
				return;
			}
			const delta = Math.round((x - value.x + scrollX.value - value.baseScroll) / dayWidth.value);
			if (value.mode === "move") value.start = Math.max(-3650, Math.min(36600, value.baseStart + delta));
			else if (value.mode === "start") {
				value.start = Math.max(-3650, Math.min(value.baseStart + value.baseDuration - 1, value.baseStart + delta));
				value.duration = Math.min(3650, value.baseDuration + value.baseStart - value.start);
			} else if (value.mode === "create") {
				value.start = value.baseStart + Math.min(0, delta);
				value.duration = Math.min(3650, Math.abs(delta) + 1);
			} else value.duration = Math.max(1, Math.min(3650, value.baseDuration + delta));
		}
		function finish(cancel = false) {
			clearInterval(autoScroll);
			const value = drag.value;
			drag.value = null;
			if (!value) return;
			const changed = value.mode === "create" || value.mode === "progress" && value.progress !== value.baseProgress || value.start !== value.baseStart || value.duration !== value.baseDuration;
			if (changed) ignoreClickUntil = performance.now() + 150;
			if (cancel || !changed) return;
			if (value.mode === "progress") emit("progress", value.key, value.progress);
			else if (value.mode === "create" || value.start !== value.baseStart || value.duration !== value.baseDuration) emit("schedule", value.key, value.start, value.duration, value.mode);
		}
		function keyboard(event) {
			if (event.key === "Escape" && drag.value) {
				event.preventDefault();
				event.stopPropagation();
				finish(true);
			}
		}
		function progressKey(event, record) {
			const step = {
				ArrowLeft: -1,
				ArrowRight: 1,
				Home: -100,
				End: 100
			}[event.key];
			if (step === void 0) return;
			event.preventDefault();
			event.stopPropagation();
			emit("progress", record.taskCode, Math.max(0, Math.min(100, record.progress + step)));
		}
		function overview(event) {
			if (event.type === "pointerdown") {
				event.preventDefault();
				event.currentTarget.setPointerCapture(event.pointerId);
			}
			if (event.type === "pointermove" && !event.buttons) return;
			const box = event.currentTarget.getBoundingClientRect();
			setScroll((event.clientX - box.left) / box.width * timelineWidth.value - timelineViewport.value / 2);
		}
		function pan(event) {
			if (event.pointerType !== "mouse" || ![0, 1].includes(event.button) || event.target.closest("button,input,label,summary")) return;
			event.preventDefault();
			event.currentTarget.setPointerCapture(event.pointerId);
			event.currentTarget.dataset.panX = event.clientX;
			event.currentTarget.dataset.panScroll = scrollX.value;
		}
		function move(event) {
			if (drag.value) updateDrag(event.clientX);
			else if ([1, 4].includes(event.buttons) && event.currentTarget.dataset.panX) setScroll(Number(event.currentTarget.dataset.panScroll) + Number(event.currentTarget.dataset.panX) - event.clientX);
		}
		onMounted(() => {
			const measured = {
				width: 800,
				bodyWidth: 800,
				bodyHeight: 400
			};
			observer = new ResizeObserver((entries) => {
				for (const { target, contentRect } of entries) if (target === root.value) measured.width = contentRect.width;
				else {
					measured.bodyWidth = contentRect.width;
					measured.bodyHeight = contentRect.height;
				}
				cancelAnimationFrame(resizeFrame);
				resizeFrame = requestAnimationFrame(() => {
					viewport.value = measured.width;
					gutter.value = Math.max(0, measured.width - measured.bodyWidth);
					bodyHeight.value = measured.bodyHeight;
				});
			});
			observer.observe(root.value);
			observer.observe(body.value);
			document.addEventListener("keydown", keyboard, true);
			window.addEventListener("blur", cancel);
		});
		function cancel() {
			finish(true);
		}
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(resizeFrame);
			clearInterval(autoScroll);
			document.removeEventListener("keydown", keyboard, true);
			window.removeEventListener("blur", cancel);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "root",
				ref: root,
				class: "task-schedule-view task-gantt-view",
				"aria-label": unref(t)("Task Gantt"),
				"aria-busy": __props.projecting,
				style: normalizeStyle({
					"--gantt-label-width": labelWidth.value + "px",
					"--gantt-width": timelineWidth.value + "px",
					"--gantt-scroll-gutter": gutter.value + "px"
				})
			}, [
				createBaseVNode("header", _hoisted_2, [createBaseVNode("div", _hoisted_3, [
					createVNode(_sfc_main$5, {
						"hide-label": "",
						label: "Select all tasks",
						"model-value": !!__props.tasks.length && __props.tasks.every((task) => __props.selected.includes(task.key)),
						disabled: __props.busy,
						"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => emit("select-all", $event))
					}, null, 8, ["model-value", "disabled"]),
					createVNode(_sfc_main$1, { name: "MDI_CHART_GANTT" }),
					createBaseVNode("div", _hoisted_4, [createBaseVNode("strong", null, toDisplayString(unref(t)("Task schedule")), 1), createBaseVNode("small", null, toDisplayString(unref(t)("{scheduled} scheduled · {unscheduled} unscheduled", {
						scheduled: range.value?.scheduled || 0,
						unscheduled: range.value?.unscheduled || 0
					})), 1)])
				]), createBaseVNode("div", {
					class: "gantt-heading-viewport",
					onWheel: wheel
				}, [createBaseVNode("div", {
					class: "gantt-heading-content",
					style: normalizeStyle({
						transform: "translateX(" + -scrollX.value + "px)",
						width: timelineWidth.value + "px"
					})
				}, [
					(openBlock(true), createElementBlock(Fragment, null, renderList(ticks.value, (tick) => {
						return openBlock(), createElementBlock("span", {
							key: tick.date,
							class: normalizeClass(["task-gantt-tick", { major: tick.major }]),
							style: normalizeStyle({
								left: tick.offsetDay * dayWidth.value + 6 + "px",
								width: Math.max(0, (tick.spanDays || 1) * dayWidth.value - 8) + "px"
							})
						}, toDisplayString(tickLabel(tick)), 7);
					}), 128)),
					(openBlock(true), createElementBlock(Fragment, null, renderList(range.value?.milestones || [], (marker) => {
						return openBlock(), createBlock(_sfc_main$2, {
							key: marker.code,
							class: "task-gantt-milestone",
							style: normalizeStyle({ left: marker.offsetDay * dayWidth.value + "px" }),
							icon: "MDI_FLAG_VARIANT",
							title: marker.label + " · " + marker.dueDate,
							onClick: ($event) => emit("milestone", marker.code)
						}, {
							default: withCtx(() => [createTextVNode(toDisplayString(marker.label), 1)]),
							_: 2
						}, 1032, [
							"style",
							"title",
							"onClick"
						]);
					}), 128)),
					range.value?.todayDay >= 0 ? (openBlock(), createElementBlock("span", {
						key: 0,
						class: "task-gantt-today",
						style: normalizeStyle({ left: range.value.todayDay * dayWidth.value + "px" })
					}, [createBaseVNode("small", null, toDisplayString(unref(t)("TODAY")), 1)], 4)) : createCommentVNode("", true)
				], 4)], 32)]),
				createBaseVNode("div", {
					ref_key: "body",
					ref: body,
					class: "gantt-body",
					tabindex: "0",
					"aria-label": unref(t)("Task schedule"),
					onScroll: synchronize,
					onPointerdown: pan,
					onPointermove: move,
					onPointerup: _cache[9] || (_cache[9] = ($event) => finish()),
					onPointercancel: _cache[10] || (_cache[10] = ($event) => finish(true))
				}, [createBaseVNode("div", {
					class: "gantt-canvas",
					style: normalizeStyle({
						height: Math.max(bodyHeight.value, totalHeight.value) + "px",
						width: labelWidth.value + timelineWidth.value + "px"
					})
				}, [createBaseVNode("div", {
					class: "gantt-grid",
					style: normalizeStyle({
						left: labelWidth.value + "px",
						width: timelineWidth.value + "px"
					})
				}, [
					(openBlock(true), createElementBlock(Fragment, null, renderList(range.value?.weekends || [], (weekend) => {
						return openBlock(), createElementBlock("span", {
							key: "weekend" + weekend.offsetDay,
							class: "gantt-weekend",
							style: normalizeStyle({
								left: weekend.offsetDay * dayWidth.value + "px",
								width: weekend.durationDays * dayWidth.value + "px"
							})
						}, null, 4);
					}), 128)),
					(openBlock(true), createElementBlock(Fragment, null, renderList(dayWidth.value >= 16 ? grid.value : ticks.value.map((tick) => ({
						day: tick.offsetDay,
						major: tick.major,
						week: true
					})), (line) => {
						return openBlock(), createElementBlock("span", {
							key: "line" + line.day,
							class: normalizeClass(["gantt-grid-line", {
								major: line.major,
								week: line.week
							}]),
							style: normalizeStyle({ left: line.day * dayWidth.value + "px" })
						}, null, 6);
					}), 128)),
					(openBlock(true), createElementBlock(Fragment, null, renderList(range.value?.milestones || [], (marker) => {
						return openBlock(), createElementBlock("span", {
							key: marker.code,
							class: "gantt-milestone-line",
							style: normalizeStyle({ left: marker.offsetDay * dayWidth.value + "px" })
						}, null, 4);
					}), 128)),
					range.value?.todayDay >= 0 ? (openBlock(), createElementBlock("span", {
						key: 0,
						class: "task-gantt-today",
						style: normalizeStyle({ left: range.value.todayDay * dayWidth.value + "px" })
					}, null, 4)) : createCommentVNode("", true)
				], 4), (openBlock(true), createElementBlock(Fragment, null, renderList(visibleRows.value, (row) => {
					return openBlock(), createElementBlock("div", {
						key: row.key,
						class: normalizeClass(["task-gantt-row", ["gantt-" + row.kind, {
							"task-selected": __props.selected.includes(row.key),
							"task-active": __props.active === row.key,
							pending: tasksByKey.value.get(row.key)?.pending
						}]]),
						"data-task-key": row.kind === "task" ? row.key : void 0,
						style: normalizeStyle({
							top: row.top + "px",
							height: row.height + "px"
						})
					}, [row.kind === "section" ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createBaseVNode("div", _hoisted_7, [createVNode(_sfc_main$1, { name: row.record.ganttSection === "scheduled" ? "MDI_CLOCK_OUTLINE" : "warning" }, null, 8, ["name"]), createTextVNode(toDisplayString(unref(t)(row.record.ganttSection === "scheduled" ? "Scheduled tasks" : "Unscheduled tasks")), 1)]), _cache[25] || (_cache[25] = createBaseVNode("div", { class: "task-gantt-timeline" }, null, -1))], 64)) : row.kind === "group" ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [createBaseVNode("div", _hoisted_8, [createVNode(_sfc_main$2, {
						icon: __props.collapsed.includes(row.record.groupKey) ? "next" : "MDI_CHEVRON_DOWN",
						"aria-expanded": !__props.collapsed.includes(row.record.groupKey),
						onClick: ($event) => emit("collapse", row.record.groupKey)
					}, {
						default: withCtx(() => [createTextVNode(toDisplayString(row.record.group) + " · " + toDisplayString(row.record.groupCount), 1)]),
						_: 2
					}, 1032, [
						"icon",
						"aria-expanded",
						"onClick"
					])]), createBaseVNode("div", _hoisted_9, [row.record.ganttGroupDurationDays ? (openBlock(), createElementBlock("span", {
						key: 0,
						class: "task-gantt-summary",
						style: normalizeStyle({
							left: row.record.ganttGroupStartDay * dayWidth.value + "px",
							width: row.record.ganttGroupDurationDays * dayWidth.value + "px"
						})
					}, [createBaseVNode("span", { style: normalizeStyle({ width: row.record.ganttGroupProgress + "%" }) }, null, 4)], 4)) : createCommentVNode("", true)])], 64)) : (openBlock(), createElementBlock(Fragment, { key: 2 }, [createBaseVNode("div", _hoisted_10, [
						createVNode(_sfc_main$5, {
							"hide-label": "",
							label: unref(t)("Select task") + " " + row.record.parentTitle + " " + row.record.processLabel,
							"translate-label": false,
							"model-value": __props.selected.includes(row.key),
							disabled: __props.busy,
							"onUpdate:modelValue": ($event) => emit("select", row.key, $event)
						}, null, 8, [
							"label",
							"model-value",
							"disabled",
							"onUpdate:modelValue"
						]),
						createVNode(ItemPreview_default, {
							source: tasksByKey.value.get(row.key)?.parent?.__preview_url__,
							"fallback-text": row.record.parentTitle.slice(0, 2).toUpperCase(),
							"fallback-icon": "sobject",
							"preview-size": 30,
							accent: color(row.record)
						}, null, 8, [
							"source",
							"fallback-text",
							"accent"
						]),
						createVNode(_sfc_main$2, {
							class: "task-gantt-title",
							title: row.record.parentTitle + " · " + row.record.processLabel,
							disabled: __props.busy,
							onClick: ($event) => emit("activate", row.key, $event),
							onDblclick: ($event) => emit("object", row.key)
						}, {
							default: withCtx(() => [createBaseVNode("strong", null, toDisplayString(row.record.parentTitle), 1), createBaseVNode("small", null, toDisplayString(row.record.processLabel) + " · " + toDisplayString(row.record.assignedLabel), 1)]),
							_: 2
						}, 1032, [
							"title",
							"disabled",
							"onClick",
							"onDblclick"
						]),
						createVNode(_sfc_main$2, {
							label: "Edit schedule",
							icon: "edit",
							"icon-only": "",
							disabled: __props.busy,
							onClick: ($event) => edit(row.key)
						}, null, 8, ["disabled", "onClick"]),
						row.record.ganttWarning ? (openBlock(), createBlock(_sfc_main$1, {
							key: 0,
							name: "warning",
							class: "gantt-warning",
							title: warningText(row.record)
						}, null, 8, ["title"])) : createCommentVNode("", true)
					]), createBaseVNode("div", {
						class: "task-gantt-timeline",
						onPointerdown: ($event) => !row.record.ganttScheduled && !$event.target.closest("button,input") && begin(row.record, "create", $event),
						onDblclick: ($event) => edit(row.key)
					}, [row.record.ganttScheduled || drag.value?.key === row.key ? (openBlock(), createElementBlock("div", {
						key: 0,
						class: "task-gantt-bar",
						style: normalizeStyle(geometry(row.record)),
						title: row.record.parentTitle + " · " + row.record.status + "\n" + row.record.start + " — " + row.record.end + "\n" + warningText(row.record)
					}, [
						createVNode(_sfc_main$2, {
							class: "task-gantt-move",
							"aria-label": unref(t)("Edit schedule") + " " + row.record.parentTitle,
							disabled: __props.busy,
							onClick: ($event) => emit("activate", row.key, $event),
							onDblclick: ($event) => emit("object", row.key),
							onPointerdown: ($event) => begin(row.record, "move", $event),
							onPointermove: move,
							onPointerup: _cache[1] || (_cache[1] = withModifiers(($event) => finish(), ["stop"])),
							onPointercancel: _cache[2] || (_cache[2] = ($event) => finish(true))
						}, {
							default: withCtx(() => [createBaseVNode("span", {
								class: "task-gantt-progress",
								style: normalizeStyle({ width: progress(row.record) + "%" })
							}, null, 4), createBaseVNode("span", null, toDisplayString(row.record.processLabel) + " " + toDisplayString(progress(row.record)) + "%", 1)]),
							_: 2
						}, 1032, [
							"aria-label",
							"disabled",
							"onClick",
							"onDblclick",
							"onPointerdown"
						]),
						createBaseVNode("small", _hoisted_13, toDisplayString(dateLabel(row.record.start)), 1),
						createBaseVNode("small", _hoisted_14, toDisplayString(dateLabel(row.record.end)), 1),
						createVNode(_sfc_main$2, {
							label: "Resize start date",
							class: "task-gantt-resize start",
							disabled: __props.busy,
							onClick: ($event) => edit(row.key),
							onPointerdown: ($event) => begin(row.record, "start", $event),
							onPointermove: move,
							onPointerup: _cache[3] || (_cache[3] = withModifiers(($event) => finish(), ["stop"])),
							onPointercancel: _cache[4] || (_cache[4] = ($event) => finish(true))
						}, {
							default: withCtx(() => [..._cache[26] || (_cache[26] = [createBaseVNode("span", null, null, -1)])]),
							_: 1
						}, 8, [
							"disabled",
							"onClick",
							"onPointerdown"
						]),
						createVNode(_sfc_main$2, {
							label: "Resize deadline",
							class: "task-gantt-resize end",
							disabled: __props.busy,
							onClick: ($event) => edit(row.key),
							onPointerdown: ($event) => begin(row.record, "end", $event),
							onPointermove: move,
							onPointerup: _cache[5] || (_cache[5] = withModifiers(($event) => finish(), ["stop"])),
							onPointercancel: _cache[6] || (_cache[6] = ($event) => finish(true))
						}, {
							default: withCtx(() => [..._cache[27] || (_cache[27] = [createBaseVNode("span", null, null, -1)])]),
							_: 1
						}, 8, [
							"disabled",
							"onClick",
							"onPointerdown"
						]),
						row.record.ganttScheduled && parseFloat(geometry(row.record).width) >= 36 && (Object.hasOwn(tasksByKey.value.get(row.key) || {}, "progress") || Object.hasOwn(tasksByKey.value.get(row.key) || {}, "completion")) ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							class: "gantt-progress-handle",
							label: "Progress",
							role: "slider",
							"aria-valuenow": progress(row.record),
							"aria-valuemin": "0",
							"aria-valuemax": "100",
							style: normalizeStyle({ left: Math.max(18, Math.min(parseFloat(geometry(row.record).width) - 18, parseFloat(geometry(row.record).width) * progress(row.record) / 100)) - 9 + "px" }),
							disabled: __props.busy,
							onKeydown: ($event) => progressKey($event, row.record),
							onPointerdown: ($event) => begin(row.record, "progress", $event),
							onPointermove: move,
							onPointerup: _cache[7] || (_cache[7] = withModifiers(($event) => finish(), ["stop"])),
							onPointercancel: _cache[8] || (_cache[8] = ($event) => finish(true))
						}, {
							default: withCtx(() => [..._cache[28] || (_cache[28] = [createBaseVNode("span", null, null, -1)])]),
							_: 1
						}, 8, [
							"aria-valuenow",
							"style",
							"disabled",
							"onKeydown",
							"onPointerdown"
						])) : createCommentVNode("", true)
					], 12, _hoisted_12)) : (openBlock(), createBlock(_sfc_main$2, {
						key: 1,
						class: "gantt-issue",
						label: "Set task schedule",
						disabled: __props.busy,
						onClick: ($event) => edit(row.key)
					}, {
						default: withCtx(() => [createTextVNode(toDisplayString(warningText(row.record)), 1)]),
						_: 2
					}, 1032, ["disabled", "onClick"]))], 40, _hoisted_11)], 64))], 14, _hoisted_6);
				}), 128))], 4), !range.value?.records.length ? (openBlock(), createElementBlock("p", _hoisted_15, toDisplayString(unref(t)(__props.projecting ? "Loading data…" : "No tasks match the current scope and filters")), 1)) : createCommentVNode("", true)], 40, _hoisted_5),
				createBaseVNode("div", _hoisted_16, [createBaseVNode("span", { title: unref(t)("{count} schedule warnings", { count: warningCount.value }) }, [createVNode(_sfc_main$1, { name: warningCount.value ? "warning" : "MDI_EYE_OUTLINE" }, null, 8, ["name"]), createTextVNode(toDisplayString(warningCount.value ? unref(t)("{count} schedule warnings", { count: warningCount.value }) : unref(t)("Project overview")), 1)], 8, _hoisted_17), createBaseVNode("div", {
					class: "task-gantt-overview",
					role: "slider",
					tabindex: "0",
					"aria-label": unref(t)("Timeline overview"),
					"aria-valuemin": "0",
					"aria-valuemax": dayCount.value,
					"aria-valuenow": Math.round(scrollX.value / dayWidth.value),
					onPointerdown: overview,
					onPointermove: overview,
					onKeydown: [_cache[11] || (_cache[11] = withKeys(withModifiers(($event) => setScroll(scrollX.value - 100), ["prevent"]), ["left"])), _cache[12] || (_cache[12] = withKeys(withModifiers(($event) => setScroll(scrollX.value + 100), ["prevent"]), ["right"]))]
				}, [(openBlock(true), createElementBlock(Fragment, null, renderList(range.value?.overview || [], (item, index) => {
					return openBlock(), createElementBlock("i", {
						key: index,
						style: normalizeStyle({
							left: item.startDay / dayCount.value * 100 + "%",
							width: item.durationDays / dayCount.value * 100 + "%"
						}),
						class: normalizeClass({ warning: item.warning })
					}, null, 6);
				}), 128)), createBaseVNode("b", { style: normalizeStyle(overviewThumb.value) }, null, 4)], 40, _hoisted_18)]),
				createBaseVNode("footer", _hoisted_19, [
					createBaseVNode("small", null, toDisplayString(range.value?.rangeStart) + " — " + toDisplayString(range.value?.rangeEnd), 1),
					__props.hasMore ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						label: "Load more tasks",
						icon: "add",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[13] || (_cache[13] = ($event) => emit("load-more"))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					createVNode(_sfc_main$4, {
						label: "Schedule options",
						overlay: "",
						"close-on-select": false
					}, {
						default: withCtx(() => [
							createVNode(_sfc_main$5, {
								label: "Working days only",
								"model-value": __props.workingDays,
								disabled: __props.busy,
								"onUpdate:modelValue": _cache[14] || (_cache[14] = ($event) => emit("working-days", $event))
							}, null, 8, ["model-value", "disabled"]),
							createVNode(_sfc_main$5, {
								label: "Group workload by assignee",
								"model-value": __props.resourceMode,
								disabled: __props.busy,
								"onUpdate:modelValue": _cache[15] || (_cache[15] = ($event) => emit("resource-mode", $event))
							}, null, 8, ["model-value", "disabled"]),
							createVNode(_sfc_main$3, {
								"model-value": scale.value,
								label: "Timeline scale",
								options: [
									{
										value: "auto",
										label: "Fit range"
									},
									{
										value: "days",
										label: "Days"
									},
									{
										value: "weeks",
										label: "Weeks"
									},
									{
										value: "months",
										label: "Months"
									},
									{
										value: "quarters",
										label: "Quarters"
									}
								],
								"onUpdate:modelValue": setScale
							}, null, 8, ["model-value"]),
							(openBlock(), createElementBlock(Fragment, null, renderList(batchActions, ([label, operation, amount]) => {
								return createVNode(_sfc_main$2, {
									key: label,
									label,
									disabled: __props.busy || !__props.selected.length,
									onClick: ($event) => emit("batch", operation, amount)
								}, null, 8, [
									"label",
									"disabled",
									"onClick"
								]);
							}), 64)),
							createVNode(_sfc_main$2, {
								label: "Delete selected tasks",
								icon: "delete",
								destructive: "",
								disabled: __props.busy || !__props.selected.length,
								onClick: _cache[16] || (_cache[16] = ($event) => emit("delete"))
							}, null, 8, ["disabled"])
						]),
						_: 1
					}),
					createVNode(_sfc_main$2, {
						label: "Undo schedule change",
						icon: "MDI_UNDO",
						"icon-only": "",
						disabled: __props.busy || !__props.canUndo,
						onClick: _cache[17] || (_cache[17] = ($event) => emit("undo"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$2, {
						label: "Redo schedule change",
						icon: "MDI_REDO",
						"icon-only": "",
						disabled: __props.busy || !__props.canRedo,
						onClick: _cache[18] || (_cache[18] = ($event) => emit("redo"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$2, {
						label: "Working days only",
						icon: "MDI_CALENDAR_TODAY",
						"icon-only": "",
						"aria-pressed": __props.workingDays,
						disabled: __props.busy,
						onClick: _cache[19] || (_cache[19] = ($event) => emit("working-days", !__props.workingDays))
					}, null, 8, ["aria-pressed", "disabled"]),
					createVNode(_sfc_main$2, {
						label: "Group workload by assignee",
						icon: "MDI_ACCOUNT_GROUP",
						"icon-only": "",
						"aria-pressed": __props.resourceMode,
						disabled: __props.busy,
						onClick: _cache[20] || (_cache[20] = ($event) => emit("resource-mode", !__props.resourceMode))
					}, null, 8, ["aria-pressed", "disabled"]),
					viewport.value >= 700 ? (openBlock(), createBlock(_sfc_main$2, {
						key: 1,
						label: "Zoom out",
						icon: "MDI_MAGNIFY_MINUS_OUTLINE",
						"icon-only": "",
						disabled: zoom.value <= .15,
						onClick: _cache[21] || (_cache[21] = ($event) => setZoom(zoom.value / 1.25))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					viewport.value >= 700 ? (openBlock(), createBlock(_sfc_main$2, {
						key: 2,
						label: "Timeline scale",
						class: "gantt-zoom",
						onClick: _cache[22] || (_cache[22] = ($event) => setScale("auto"))
					}, {
						default: withCtx(() => [createTextVNode(toDisplayString(Math.round(zoom.value * 100)) + "%", 1)]),
						_: 1
					})) : createCommentVNode("", true),
					viewport.value >= 700 ? (openBlock(), createBlock(_sfc_main$2, {
						key: 3,
						label: "Zoom in",
						icon: "MDI_MAGNIFY_PLUS_OUTLINE",
						"icon-only": "",
						disabled: zoom.value >= 5,
						onClick: _cache[23] || (_cache[23] = ($event) => setZoom(zoom.value * 1.25))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					createVNode(_sfc_main$2, {
						label: "Center today",
						icon: "MDI_CALENDAR_TODAY",
						"icon-only": "",
						disabled: !range.value || range.value.todayDay < 0,
						onClick: _cache[24] || (_cache[24] = ($event) => setScroll(range.value.todayDay * dayWidth.value - timelineViewport.value * .42))
					}, null, 8, ["disabled"]),
					renderSlot(_ctx.$slots, "footer")
				])
			], 12, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TaskGanttView.js.map
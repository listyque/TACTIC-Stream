import { G as withCtx, N as openBlock, P as renderList, X as ref, _ as createCommentVNode, b as createTextVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, m as computed, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, O as appearance, o as _sfc_main$1, u as _sfc_main$2 } from "./index.js";
//#region src/features/tasks/TaskCalendarView.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "calendar-navigation" };
var _hoisted_3 = [
	"value",
	"aria-label",
	"disabled"
];
var _hoisted_4 = {
	key: 0,
	role: "alert",
	class: "error"
};
var _hoisted_5 = {
	key: 1,
	class: "calendar-weekdays"
};
var _hoisted_6 = {
	key: 2,
	class: "task-calendar-grid"
};
var _hoisted_7 = { class: "calendar-day-number" };
var _hoisted_8 = {
	key: 1,
	class: "calendar-day-tasks"
};
var _hoisted_9 = { key: 0 };
var _hoisted_10 = {
	key: 2,
	class: "calendar-status-dots",
	"aria-hidden": "true"
};
var _hoisted_11 = {
	key: 3,
	class: "task-calendar-agenda"
};
var _hoisted_12 = {
	key: 0,
	class: "muted"
};
var _sfc_main = {
	__name: "TaskCalendarView",
	props: {
		projection: Object,
		year: Number,
		month: Number,
		selectedDay: String,
		busy: Boolean,
		projecting: Boolean,
		error: String,
		hasMore: Boolean
	},
	emits: [
		"month",
		"month-value",
		"today",
		"day",
		"inspect",
		"milestone",
		"load-more",
		"tasks"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const root = ref(null), width = ref(600), height = ref(500), agenda = ref(false);
		let observer;
		const compact = computed(() => width.value < 500 || height.value < 430);
		const title = computed(() => new Intl.DateTimeFormat(appearance.language, {
			month: "long",
			year: "numeric"
		}).format(new Date(props.year, props.month - 1, 1)));
		const weekdays = computed(() => Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(appearance.language, { weekday: "short" }).format(new Date(2024, 0, 1 + index))));
		const days = computed(() => props.projection?.calendar || []);
		const agendaDays = computed(() => days.value.filter((day) => props.selectedDay ? day.date === props.selectedDay : day.inMonth));
		function limit(day) {
			return compact.value ? 0 : Math.max(1, Math.min(3, Math.floor(((height.value - 96) / 6 - (day.milestoneCount ? 54 : 30)) / 22)));
		}
		onMounted(() => {
			observer = new ResizeObserver(() => {
				width.value = root.value.clientWidth;
				height.value = root.value.clientHeight;
			});
			observer.observe(root.value, { box: "border-box" });
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "root",
				ref: root,
				class: normalizeClass(["task-calendar-view", { compact: compact.value }]),
				"aria-label": unref(t)("Task calendar"),
				"aria-busy": __props.projecting
			}, [
				createBaseVNode("header", _hoisted_2, [
					createVNode(_sfc_main$1, {
						label: "Previous month",
						icon: "previous",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[0] || (_cache[0] = ($event) => emit("month", -1))
					}, null, 8, ["disabled"]),
					createBaseVNode("label", null, [createBaseVNode("span", null, toDisplayString(title.value), 1), createBaseVNode("input", {
						type: "month",
						value: __props.year + "-" + String(__props.month).padStart(2, "0"),
						"aria-label": unref(t)("Calendar month"),
						disabled: __props.busy,
						onChange: _cache[1] || (_cache[1] = ($event) => emit("month-value", $event.target.value))
					}, null, 40, _hoisted_3)]),
					createVNode(_sfc_main$1, {
						label: "Next month",
						icon: "next",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[2] || (_cache[2] = ($event) => emit("month", 1))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$1, {
						label: "Today",
						icon: "MDI_CALENDAR_TODAY",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[3] || (_cache[3] = ($event) => emit("today"))
					}, null, 8, ["disabled"]),
					__props.selectedDay ? (openBlock(), createBlock(_sfc_main$1, {
						key: 0,
						label: "Clear selected day",
						icon: "MDI_FILTER_REMOVE_OUTLINE",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[4] || (_cache[4] = ($event) => emit("day", ""))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					createVNode(_sfc_main$1, {
						label: "Agenda",
						icon: "MDI_FORMAT_LIST_BULLETED",
						"icon-only": "",
						"aria-pressed": agenda.value,
						onClick: _cache[5] || (_cache[5] = ($event) => agenda.value = !agenda.value)
					}, null, 8, ["aria-pressed"])
				]),
				__props.error ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString(unref(t)(__props.error)), 1)) : createCommentVNode("", true),
				!agenda.value ? (openBlock(), createElementBlock("div", _hoisted_5, [(openBlock(true), createElementBlock(Fragment, null, renderList(weekdays.value, (weekday) => {
					return openBlock(), createElementBlock("span", { key: weekday }, toDisplayString(weekday.toUpperCase()), 1);
				}), 128))])) : createCommentVNode("", true),
				!agenda.value ? (openBlock(), createElementBlock("div", _hoisted_6, [(openBlock(true), createElementBlock(Fragment, null, renderList(days.value, (day, index) => {
					return openBlock(), createElementBlock("div", {
						key: day.date,
						class: normalizeClass(["task-calendar-day", {
							outside: !day.inMonth,
							today: day.today,
							selected: day.date === __props.selectedDay,
							weekend: index % 7 >= 5
						}])
					}, [
						createVNode(_sfc_main$1, {
							class: "calendar-day-action",
							"data-date": day.date,
							"aria-label": day.date,
							"aria-pressed": day.date === __props.selectedDay,
							disabled: __props.busy,
							onClick: ($event) => emit("day", day.date)
						}, {
							default: withCtx(() => [createBaseVNode("span", _hoisted_7, toDisplayString(day.day), 1), day.taskCount ? (openBlock(), createElementBlock("small", {
								key: 0,
								class: normalizeClass({ overdue: day.overdueCount > 0 })
							}, toDisplayString(day.taskCount), 3)) : createCommentVNode("", true)]),
							_: 2
						}, 1032, [
							"data-date",
							"aria-label",
							"aria-pressed",
							"disabled",
							"onClick"
						]),
						day.milestones?.length ? (openBlock(), createBlock(_sfc_main$1, {
							key: 0,
							class: "calendar-milestone-band",
							title: day.milestones.map((item) => item.label).join(", "),
							disabled: __props.busy,
							onClick: ($event) => emit("milestone", day.milestones[0].code)
						}, {
							default: withCtx(() => [createVNode(_sfc_main$2, { name: "MDI_FLAG_VARIANT" }), createBaseVNode("span", null, toDisplayString(day.milestones[0].label), 1)]),
							_: 2
						}, 1032, [
							"title",
							"disabled",
							"onClick"
						])) : createCommentVNode("", true),
						limit(day) ? (openBlock(), createElementBlock("div", _hoisted_8, [(openBlock(true), createElementBlock(Fragment, null, renderList(day.tasks.slice(0, limit(day)), (task) => {
							return openBlock(), createBlock(_sfc_main$1, {
								key: task.taskCode,
								class: "task-calendar-event",
								title: task.parentTitle + " · " + task.processLabel + " · " + task.status + " · " + task.assignedLabel,
								disabled: __props.busy,
								onClick: ($event) => emit("inspect", task.taskCode)
							}, {
								default: withCtx(() => [createBaseVNode("i", { style: normalizeStyle({ background: task.statusColor || "var(--primary)" }) }, null, 4), createBaseVNode("span", null, toDisplayString(task.parentTitle) + " · " + toDisplayString(task.processLabel), 1)]),
								_: 2
							}, 1032, [
								"title",
								"disabled",
								"onClick"
							]);
						}), 128)), day.taskCount > limit(day) ? (openBlock(), createElementBlock("small", _hoisted_9, toDisplayString(unref(t)("{count} more tasks", { count: day.taskCount - limit(day) })), 1)) : createCommentVNode("", true)])) : day.taskCount ? (openBlock(), createElementBlock("div", _hoisted_10, [(openBlock(true), createElementBlock(Fragment, null, renderList(day.tasks.slice(0, 5), (task) => {
							return openBlock(), createElementBlock("i", {
								key: task.taskCode,
								style: normalizeStyle({ background: task.statusColor || "var(--primary)" })
							}, null, 4);
						}), 128))])) : createCommentVNode("", true)
					], 2);
				}), 128))])) : (openBlock(), createElementBlock("div", _hoisted_11, [(openBlock(true), createElementBlock(Fragment, null, renderList(agendaDays.value.filter((item) => item.tasks.length || item.milestones?.length), (day) => {
					return openBlock(), createElementBlock("section", {
						key: day.date,
						class: "calendar-agenda-day"
					}, [
						createBaseVNode("strong", null, toDisplayString(day.date), 1),
						(openBlock(true), createElementBlock(Fragment, null, renderList(day.milestones, (milestone) => {
							return openBlock(), createBlock(_sfc_main$1, {
								key: milestone.code,
								icon: "MDI_FLAG_VARIANT",
								onClick: ($event) => emit("milestone", milestone.code)
							}, {
								default: withCtx(() => [createTextVNode(toDisplayString(milestone.label), 1)]),
								_: 2
							}, 1032, ["onClick"]);
						}), 128)),
						(openBlock(true), createElementBlock(Fragment, null, renderList(day.tasks, (task) => {
							return openBlock(), createBlock(_sfc_main$1, {
								key: task.taskCode,
								class: "task-calendar-agenda-row",
								disabled: __props.busy,
								onClick: ($event) => emit("inspect", task.taskCode)
							}, {
								default: withCtx(() => [createTextVNode(toDisplayString(task.parentTitle) + " · " + toDisplayString(task.processLabel) + " · " + toDisplayString(task.status), 1)]),
								_: 2
							}, 1032, ["disabled", "onClick"]);
						}), 128))
					]);
				}), 128)), !agendaDays.value.some((day) => day.taskCount || day.milestones?.length) ? (openBlock(), createElementBlock("p", _hoisted_12, toDisplayString(unref(t)("No loaded tasks on these dates.")), 1)) : createCommentVNode("", true)])),
				createBaseVNode("footer", null, [
					createBaseVNode("small", null, toDisplayString(__props.selectedDay ? unref(t)("Task Browser filtered by {date}", { date: __props.selectedDay }) : unref(t)("Select a day to filter Task Browser")), 1),
					__props.hasMore ? (openBlock(), createBlock(_sfc_main$1, {
						key: 0,
						label: "Load more tasks",
						icon: "add",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[6] || (_cache[6] = ($event) => emit("load-more"))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					createVNode(_sfc_main$1, {
						label: "Task Manager",
						icon: "MDI_CLIPBOARD_TEXT_OUTLINE",
						"icon-only": "",
						onClick: _cache[7] || (_cache[7] = ($event) => emit("tasks"))
					})
				])
			], 10, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TaskCalendarView.js.map
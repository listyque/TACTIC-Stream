import { c as button, d as node, f as rect, l as label, s as translate } from "./resize.js";
//#region ../src/tactic_stream/shared_ui/features/search/organization.mjs
function taskGroup(tasks, process, statuses, accent, compare) {
	const matching = tasks.filter((task) => task.process === process), values = [];
	for (const task of matching) if (task.status && !values.includes(task.status)) values.push(task.status);
	if (!values.length) return {
		key: matching.length ? "__no_status__" : "__no_task__",
		label: matching.length ? "No status" : "No task",
		translate: true,
		rank: matching.length ? 9999 : 1e4,
		accent
	};
	const catalog = Object.create(null);
	for (let index = 0; index < statuses.length; index++) catalog[statuses[index].key] = {
		rank: index,
		accent: statuses[index].accent || accent
	};
	values.sort((left, right) => (catalog[left]?.rank ?? 9e3) - (catalog[right]?.rank ?? 9e3) || compare(left, right));
	const key = values[0];
	return {
		key,
		label: key,
		rank: catalog[key]?.rank ?? 9e3,
		accent: catalog[key]?.accent || accent
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/search/menus.ui.mjs
var views = [
	{
		value: "continious",
		label: "Continuous tree",
		icon: "MDI_FORMAT_LIST_BULLETED"
	},
	{
		value: "tiles",
		label: "Cards",
		icon: "MDI_VIEW_DASHBOARD"
	},
	{
		value: "table",
		label: "Table",
		icon: "MDI_TABLE"
	},
	{
		value: "compact",
		label: "Compact rows",
		icon: "MDI_VIEW_LIST"
	},
	{
		value: "splitted_vertical",
		label: "Versions on the right",
		icon: "MDI_VIEW_COLUMN"
	},
	{
		value: "splitted_horizontal",
		label: "Versions at the bottom",
		icon: "MDI_VIEW_AGENDA"
	}
];
var groups = [
	{
		value: "none",
		label: "No grouping",
		icon: "list-alt"
	},
	{
		value: "status",
		label: "SObject status",
		icon: "group-items"
	},
	{
		value: "pipeline",
		label: "Pipeline",
		icon: "process"
	}
];
var sorts = [
	{
		value: "name_asc",
		label: "Name A-Z",
		icon: "sort-items",
		column: "name",
		direction: "asc"
	},
	{
		value: "name_desc",
		label: "Name Z-A",
		icon: "sort-items",
		column: "name",
		direction: "desc"
	},
	{
		value: "updated_desc",
		label: "Recently updated",
		icon: "history",
		column: "timestamp",
		direction: "desc"
	},
	{
		value: "updated_asc",
		label: "Oldest updated",
		icon: "history",
		column: "timestamp",
		direction: "asc"
	}
];
function choices(items, value, busy) {
	return items.map((item) => ({
		title: item.label,
		icon: item.icon,
		command: item.value,
		checked: item.value === value,
		enabled: !busy
	}));
}
function viewActions(value, busy) {
	return choices(views, value, busy);
}
function sortActions(model) {
	const actions = [{
		title: "Sort items",
		header: true
	}].concat(choices(sorts, model.mode, model.busy));
	if (model.defaultOrder) actions.push({
		title: "Default order",
		icon: "list-alt",
		command: "default",
		checked: !model.column,
		enabled: !model.busy
	});
	return actions.concat([{ separator: true }, {
		title: "Sort by column",
		icon: "table",
		command: "column",
		enabled: !model.busy
	}]);
}
function groupActions(model) {
	const actions = [{
		title: "Group items",
		header: true
	}].concat(choices(groups, model.mode, model.busy));
	if ((model.processes || []).length) {
		actions.push({ separator: true }, {
			title: "Task status by process",
			header: true
		});
		for (const process of model.processes) actions.push({
			title: process.title || process.key,
			translate: false,
			icon: "process-marker",
			accent: process.accent,
			command: "task_status:" + process.key,
			checked: model.mode === "task_status:" + process.key,
			enabled: !model.busy
		});
	}
	return actions;
}
function filterActions(model) {
	const actions = (model.base || [{
		title: "Advanced Search",
		icon: "advanced-search",
		command: "advanced_search"
	}, {
		title: "Filter Processes",
		icon: "filter-alt",
		command: "filter_processes"
	}]).slice();
	actions.push({ separator: true }, {
		title: "Saved searches",
		header: true
	});
	for (const preset of model.presets || []) actions.push({
		title: preset.title || "Saved search",
		translate: false,
		icon: "save",
		command: "preset:" + preset.view,
		checked: preset.view === model.selected,
		enabled: !model.busy && !preset.error
	});
	if (!(model.presets || []).length) actions.push({
		title: model.busy ? "Loading saved searches..." : model.error || "No saved searches",
		icon: model.busy ? "hourglass_empty" : "save",
		command: "",
		enabled: false
	});
	actions.push({ separator: true }, {
		title: "Refresh saved searches",
		icon: "refresh",
		command: "refresh_presets",
		enabled: !model.busy
	});
	return actions;
}
function sortColumn(model, width, language) {
	const text = (key) => translate(key, language);
	return {
		nodes: [
			label("searchSortColumnTitle", rect(0, 0, width, 24), text("Sort by column"), { weight: 600 }),
			node("Choice", "searchSortColumn", rect(0, 30, width, 36), {
				label: text("Sort by"),
				value: model.column,
				options: model.columns || [],
				action: { type: "column" },
				enabled: !model.busy
			}),
			button("searchSortDirection", rect(0, 72, width, 36), text(model.direction === "desc" ? "Descending" : "Ascending"), "sort", { type: "direction" }, !model.busy),
			button("searchSortApply", rect(width - 112, 120, 112, 36), text("Apply"), "check", { type: "apply" }, !model.busy && !!model.column, { highlighted: true })
		],
		contentHeight: 156
	};
}
//#endregion
//#region src/features/workspace/resultViews.js
var defaultResultView = "continious";
function groupRecords(records, mode, nodes = [], organization = {}) {
	if (mode === "none") return [{
		key: "",
		label: "",
		records
	}];
	const groups = /* @__PURE__ */ new Map(), byKey = new Map(nodes.map((node) => [node.record.__search_key__, node])), process = mode.startsWith("task_status:") ? mode.slice(12) : "", collator = new Intl.Collator(void 0, {
		numeric: true,
		sensitivity: "base"
	});
	for (const record of records) {
		const node = byKey.get(record.__search_key__), task = process ? taskGroup(node?.tasks || [], process, organization.statuses?.[process] || [], node?.accent, collator.compare) : null, key = task ? task.key : mode === "pipeline" ? record.pipeline_code || "" : record.status || record.state || "";
		if (!groups.has(key)) groups.set(key, {
			key,
			label: task ? task.label : mode === "pipeline" ? key || "No pipeline" : key || "No status",
			translate: task?.translate,
			rank: task?.rank || 0,
			accent: task?.accent,
			records: []
		});
		groups.get(key).records.push(record);
	}
	return [...groups.values()].sort((left, right) => left.rank - right.rank || (!left.key ? 1 : !right.key ? -1 : collator.compare(left.label, right.label)));
}
//#endregion
//#region src/controls/typography/textMetrics.js
var context;
function layoutContext(font) {
	context ||= document.createElement("canvas").getContext("2d");
	context.font = font.replace(/(\d+(?:\.\d+)?)px/, (_, size) => Number(size) * 64 + "px");
	return context;
}
function layoutTextWidth(text, font) {
	return layoutContext(font).measureText(String(text)).width / 64;
}
function qtLabelTextWidth(text, font) {
	const canvas = layoutContext(font), glyphs = [...String(text)];
	const widths = glyphs.map((glyph) => canvas.measureText(glyph).width);
	return widths.reduce((sum, width, index) => {
		const kerning = index ? canvas.measureText(glyphs[index - 1] + glyphs[index]).width - widths[index - 1] - width : 0;
		return sum + (Math.floor(width) + Math.round(kerning)) / 64;
	}, 0);
}
//#endregion
export { filterActions as a, sortActions as c, viewActions as d, views as f, groupRecords as i, sortColumn as l, qtLabelTextWidth as n, groupActions as o, defaultResultView as r, groups as s, layoutTextWidth as t, sorts as u };

//# sourceMappingURL=textMetrics.js.map
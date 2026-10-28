import { I as resolveComponent, N as openBlock, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, q as withDirectives, rt as normalizeStyle, s as vShow } from "./vue.js";
import { O as randomUuid, j as appearance, ot as _plugin_vue_export_helper_default } from "./index.js";
import { Gt as button, Jt as node, Kt as label, Yt as rect, ct as rpc, i as _sfc_main$1, qt as muted, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { n as sections } from "./sections.ui.js";
import { a as projectPath } from "./links.js";
import { t as listAction } from "./tree.ui.js";
import { A as _sfc_main$2, At as geometry, Ct as appearances, Dt as duplicate, Et as copy, Ft as reorder, G as alignment, It as reparent, J as toggle, K as roots, Lt as siblings, M as zooms, Mt as layers, Nt as path, Ot as fingerprint, Pt as remove, Rt as sizing, St as add, Tt as change$1, Y as spacingField, _t as filter, at as notices, bt as scope$1, gt as fields$1, ht as change, it as documentEvent, j as controls, jt as kinds, kt as geometries, lt as toolbar$1, q as selected, st as sectionSelector, vt as mode, wt as block, xt as type, yt as options, zt as spacing } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.reports.mjs
var collections = [
	"items",
	"table",
	"metric",
	"chart",
	"summary"
];
function scope(document, ui) {
	if (ui.selected) return scope$1(document, ui.selected);
	return {
		searchType: document?.filters?.[ui.pageFilter || 0]?.search_type || "",
		recordKey: ""
	};
}
function filterDocument(document, ui) {
	const item = document.filters[ui.pageFilter || 0];
	return { blocks: [{
		kind: "metric",
		search_type: item.search_type,
		filters: [{
			column: item.column,
			relation: item.relation,
			value: item.value
		}]
	}] };
}
var events = [
	"pageFilterAdd",
	"pageFilterRemove",
	"pageFilterSelect",
	"pageFilterChange",
	"pageSource",
	"pageCondition",
	"pageConditionCommit",
	"report",
	"reportCommit"
];
function edit(model, ui, event) {
	const document = copy(model.document), next = Object.assign({}, ui);
	const filters = document.filters || (document.filters = []);
	const index = ui.pageFilter || 0;
	if (event.type === "pageFilterSelect") {
		next.pageFilter = Number(event.value);
		return { ui: next };
	}
	if (event.type === "pageFilterAdd") {
		if (filters.length >= 8) throw Error("A page supports at most eight shared filters");
		let number = 1;
		while (filters.some((item) => item.name === "filter_" + number)) number++;
		filters.push({
			name: "filter_" + number,
			title: "Filter " + number,
			search_type: model.searchTypes?.[0]?.value || "",
			column: "code",
			relation: "=",
			value: "",
			enabled: false
		});
		next.pageFilter = filters.length - 1;
	} else if (event.type === "pageFilterRemove") {
		filters.splice(index, 1);
		next.pageFilter = Math.max(0, index - 1);
	} else if ([
		"pageSource",
		"pageCondition",
		"pageConditionCommit",
		"pageFilterChange"
	].includes(event.type)) {
		const item = filters[index];
		if (!item) throw Error("Choose a page filter");
		if (event.type === "pageSource") item.search_type = event.value;
		else if (event.type === "pageFilterChange") {
			if (!["title", "enabled"].includes(event.field)) throw Error("Unsupported page filter property");
			item[event.field] = event.key ? ui.text[event.key] : event.value;
		} else {
			if (event.type === "pageConditionCommit" && !Object.prototype.hasOwnProperty.call(ui.text, event.key)) return { ui: next };
			const result = filter(filterDocument(document, ui), "0", event.type === "pageConditionCommit" ? Object.assign({}, event, {
				field: "value",
				value: ui.text[event.key]
			}) : event, model.dataSource);
			Object.assign(item, result.blocks[0].filters[0]);
		}
		if (event.key) {
			next.text = Object.assign({}, ui.text);
			delete next.text[event.key];
		}
	} else {
		const item = block(document, ui.selected);
		if (!item || !collections.includes(item.kind)) throw Error("Choose a data widget");
		const value = event.key ? ui.text[event.key] : event.value;
		if (event.field === "mappingMode") item.page_filters = value === "auto" ? null : {};
		else if (event.field === "mapping") {
			item.page_filters = Object.assign({}, item.page_filters);
			if (value) item.page_filters[event.name] = value;
			else delete item.page_filters[event.name];
		} else if ([
			"group_limit",
			"group_order",
			"measure"
		].includes(event.field)) item[event.field] = value;
		else {
			const field = event.section === "group" ? "group_by" : "aggregates";
			const rows = item[field] || (item[field] = []);
			if (event.action === "add") {
				if (rows.length >= (field === "group_by" ? 3 : 8)) throw Error("Report dimension limit reached");
				if (field === "group_by") rows.push({
					column: model.dataSource?.fields?.find((f) => type(f) !== "complex")?.value || "code",
					period: "value"
				});
				else {
					let number = 1;
					while (rows.some((row) => row.name === "measure_" + number)) number++;
					rows.push({
						name: "measure_" + number,
						title: "Count",
						function: "count",
						column: ""
					});
				}
			} else if (event.action === "remove") rows.splice(event.index, 1);
			else {
				const row = rows[event.index];
				if (!row || !(field === "group_by" ? [
					"column",
					"period",
					"title"
				] : [
					"column",
					"function",
					"title"
				]).includes(event.field)) throw Error("Choose a report field");
				if (event.field === "function") {
					const titles = {
						count: "Count",
						sum: "Sum",
						avg: "Average",
						min: "Minimum",
						max: "Maximum"
					};
					if (row.title === titles[row.function]) row.title = titles[value];
				}
				row[event.field] = value;
			}
		}
		if (event.key) {
			next.text = Object.assign({}, ui.text);
			delete next.text[event.key];
		}
	}
	return {
		document,
		ui: next
	};
}
function retag(value) {
	if (!value || typeof value !== "object") return value;
	if (Array.isArray(value)) return value.map(retag);
	const result = {};
	for (const [key, item] of Object.entries(value)) result[key] = retag(item);
	if (result.type === "data") result.type = "pageSource";
	if (result.type === "filter") result.type = "pageCondition";
	if (result.type === "filterCommit") result.type = "pageConditionCommit";
	return result;
}
function fields(model, ui, width, language, enabled) {
	const result = [], tr = (text) => translate(text, language), document = model.document;
	function heading(id, title, description = "") {
		result.push({
			kind: "Heading",
			id,
			title,
			description
		});
	}
	function choice(id, title, value, rows, action) {
		result.push({
			kind: "Choice",
			id,
			title,
			options: options(rows, value, language),
			props: {
				value,
				enabled,
				action
			}
		});
	}
	function button(id, title, action, icon = "add") {
		result.push({
			kind: "Button",
			id,
			title,
			props: {
				enabled,
				icon,
				action
			}
		});
	}
	function text(id, title, value, action) {
		const key = id;
		result.push({
			id,
			title,
			props: {
				enabled,
				text: Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : value,
				action: {
					type: "buffer",
					key
				},
				commitAction: Object.assign({}, action, { key })
			}
		});
	}
	if (!ui.selected) {
		const filters = document.filters || [], index = ui.pageFilter || 0, item = filters[index];
		heading("pageSharedHeading", "Shared page filters", "Apply the same condition to several widgets. Runtime values do not change the saved page.");
		choice("pageSharedSelect", "Page filter", String(index), filters.map((item, i) => ({
			value: String(i),
			label: item.title
		})), { type: "pageFilterSelect" });
		button("pageSharedAdd", "Add page filter", { type: "pageFilterAdd" });
		if (!item) return result;
		text("pageSharedTitle", "Filter label", item.title, {
			type: "pageFilterChange",
			field: "title"
		});
		result.push({
			kind: "Switch",
			id: "pageSharedEnabled",
			title: "Enabled by default",
			props: {
				checked: item.enabled,
				enabled,
				action: {
					type: "pageFilterChange",
					field: "enabled"
				}
			}
		});
		const data = fields$1(Object.assign({}, model, { document: filterDocument(document, ui) }), Object.assign({}, ui, { selected: "0" }), width, language, enabled).filter((field) => !["pageDataHeading", "pageFilterAdd"].includes(field.id));
		for (const field of data) if (field.id === "pageFilter_0") field.props.children = field.props.children.filter((node) => !node.id.endsWith("_remove"));
		result.push(...data.map(retag));
		button("pageSharedRemove", "Remove page filter", { type: "pageFilterRemove" }, "delete");
		return result;
	}
	const item = block(document, ui.selected);
	if (!collections.includes(item.kind)) return result;
	const metadata = model.dataSource?.searchType === item.search_type ? model.dataSource : {};
	const sourceFields = (metadata.fields || []).filter((field) => type(field) !== "complex");
	enabled = enabled && !model.dataBusy && !!metadata.searchType;
	if (document.filters?.length) {
		heading("pageMappingsHeading", "Shared page filters");
		choice("pageMappingMode", "Filter binding", item.page_filters == null ? "auto" : "custom", [{
			value: "auto",
			label: tr("Match the same data source")
		}, {
			value: "custom",
			label: tr("Choose fields explicitly")
		}], {
			type: "report",
			field: "mappingMode"
		});
		if (item.page_filters != null) for (const filter of document.filters) choice("pageMapping_" + filter.name, filter.title, item.page_filters[filter.name] || "", [{
			value: "",
			label: tr("Not applied")
		}].concat(sourceFields), {
			type: "report",
			field: "mapping",
			name: filter.name
		});
	}
	if (![
		"metric",
		"chart",
		"summary"
	].includes(item.kind)) return result;
	heading("pageReportHeading", "Grouping and aggregates", "Totals use all matching records before the displayed group limit.");
	if (item.kind !== "metric") {
		(item.group_by || []).forEach((group, index) => {
			const action = {
				type: "report",
				section: "group",
				index
			};
			text("pageGroup_" + index + "_title", "Group label (optional)", group.title || "", Object.assign({}, action, {
				type: "reportCommit",
				field: "title"
			}));
			choice("pageGroup_" + index + "_column", "Group field", group.column, sourceFields, Object.assign({}, action, { field: "column" }));
			choice("pageGroup_" + index + "_period", "Group interval", group.period || "value", (type(sourceFields.find((field) => field.value === group.column)) === "date" ? [
				"value",
				"year",
				"month",
				"day"
			] : ["value"]).map((value) => ({
				value,
				label: tr({
					value: "Field value",
					year: "Year (UTC)",
					month: "Month (UTC)",
					day: "Day (UTC)"
				}[value])
			})), Object.assign({}, action, { field: "period" }));
			button("pageGroup_" + index + "_remove", "Remove group", Object.assign({}, action, { action: "remove" }), "delete");
		});
		button("pageGroupAdd", "Add grouping", {
			type: "report",
			section: "group",
			action: "add"
		});
	}
	const measures = item.aggregates || [];
	measures.forEach((measure, index) => {
		const action = {
			type: "report",
			section: "measure",
			index
		};
		text("pageMeasure_" + index + "_title", "Measure label", measure.title, Object.assign({}, action, {
			type: "reportCommit",
			field: "title"
		}));
		choice("pageMeasure_" + index + "_function", "Aggregate", measure.function, [
			"count",
			"sum",
			"avg",
			"min",
			"max"
		].map((value) => ({
			value,
			label: tr({
				count: "Count",
				sum: "Sum",
				avg: "Average",
				min: "Minimum",
				max: "Maximum"
			}[value])
		})), Object.assign({}, action, { field: "function" }));
		choice("pageMeasure_" + index + "_column", "Measure field", measure.column || "", [{
			value: "",
			label: tr("All rows (count only)")
		}].concat(sourceFields.filter((field) => measure.function === "count" || type(field) === "number")), Object.assign({}, action, { field: "column" }));
		button("pageMeasure_" + index + "_remove", "Remove measure", Object.assign({}, action, { action: "remove" }), "delete");
	});
	if (item.kind !== "metric" || !measures.length) button("pageMeasureAdd", "Add measure", {
		type: "report",
		section: "measure",
		action: "add"
	});
	if (item.kind !== "metric") {
		choice("pageGroupOrder", "Group order", item.group_order || "group", [
			{
				value: "group",
				label: tr("By group")
			},
			{
				value: "value_desc",
				label: tr("Largest first (first measure)")
			},
			{
				value: "value_asc",
				label: tr("Smallest first (first measure)")
			}
		], {
			type: "report",
			field: "group_order"
		});
		choice("pageGroupLimit", "Maximum groups", item.group_limit || 50, [
			10,
			25,
			50,
			100
		].map((value) => ({
			value,
			label: String(value)
		})), {
			type: "report",
			field: "group_limit"
		});
	}
	if (item.kind === "chart") choice("pageChartMeasure", "Chart measure", item.measure || measures[0]?.name || "count", measures.length ? measures.map((row) => ({
		value: row.name,
		label: row.title
	})) : [{
		value: "count",
		label: tr("Count")
	}], {
		type: "report",
		field: "measure"
	});
	return result;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.components.mjs
function componentFields(fields, item, ui, canEdit, language, field) {
	const tr = (text) => translate(text, language);
	function choice(name, title, value, options) {
		fields.push({
			kind: "Choice",
			id: "pageProperty_" + name,
			title,
			options: options.map(([value, label]) => ({
				value: String(value),
				label: tr(label)
			})),
			props: {
				value: String(value),
				enabled: canEdit && (ui.selection || []).length < 2,
				action: {
					type: "change",
					field: name
				}
			}
		});
	}
	if (["icon", "button"].includes(item.kind)) fields.push({
		kind: "IconChoice",
		id: "pageProperty_icon",
		title: "Icon",
		props: {
			value: item.icon || "",
			enabled: canEdit,
			action: {
				type: "change",
				field: "icon"
			}
		}
	});
	if (item.kind === "icon") field("icon_size", "Icon size", item.icon_size || 32);
	if (item.kind === "button") choice("button_style", "Button style", item.button_style || "normal", [
		["normal", "Normal"],
		["primary", "Primary"],
		["tonal", "Tonal"]
	]);
	if (["text", "heading"].includes(item.kind)) {
		choice("text_role", "Text style", item.text_role || "auto", [
			["auto", "Auto"],
			["caption", "Caption"],
			["body", "Body"],
			["bodyLarge", "Large body"],
			["title", "Title"],
			["heading", "Heading"],
			["display", "Display"],
			["statistic", "Statistic"],
			["hero", "Hero"]
		]);
		choice("text_weight", "Text weight", item.text_weight || 400, [
			[400, "Normal"],
			[600, "Semibold"],
			[700, "Bold"]
		]);
		choice("text_align", "Text alignment", item.text_align || "left", [
			["left", "Left"],
			["center", "Center"],
			["right", "Right"]
		]);
	}
	if ([
		"text",
		"heading",
		"icon",
		"divider"
	].includes(item.kind)) {
		choice("text_color", "Text / icon color", item.text_color || "auto", [
			["auto", "Auto"],
			["primaryText", "Primary text"],
			["secondaryText", "Secondary text"],
			["contentAccent", "Accent"],
			["error", "Error"]
		].concat((item.text_color || "").startsWith("#") ? [[item.text_color, item.text_color]] : []));
		fields.push({
			kind: "ColorChoice",
			id: "pageCustomTextColor",
			title: "Custom text / icon color",
			props: {
				value: (item.text_color || "").startsWith("#") ? item.text_color : "#607D8B",
				enabled: canEdit,
				action: {
					type: "change",
					field: "text_color"
				}
			}
		});
	}
	if (item.kind === "image") choice("image_fit", "Image fit", item.image_fit || "contain", [["contain", "Contain"], ["cover", "Cover"]]);
}
function sizingFields(fields, item, ui, document, parent, canEdit, language, field) {
	const tr = (text) => translate(text, language);
	const sizing = Object.assign({
		width_mode: "auto",
		height_mode: "auto",
		min_width: 0,
		min_height: 0,
		max_width: null,
		max_height: null
	}, item.sizing || {});
	for (const [name, title] of [["width_mode", "Width behavior"], ["height_mode", "Height behavior"]]) fields.push({
		kind: "Choice",
		id: "pageSizing_" + name,
		title,
		options: [
			["auto", "Auto"],
			["fixed", "Fixed"],
			["fill", "Fill container"],
			["content", "Fit content"]
		].map(([value, label]) => ({
			value,
			label: tr(label)
		})),
		props: {
			value: sizing[name],
			enabled: canEdit && (ui.selection || []).length < 2,
			action: {
				type: "sizing",
				field: name
			}
		}
	});
	for (const [name, title] of [
		["min_width", "Minimum width"],
		["max_width", "Maximum width"],
		["min_height", "Minimum height"],
		["max_height", "Maximum height"]
	]) {
		const key = ui.selected + ":sizing:" + name;
		fields.push({
			id: "pageSizing_" + name,
			title,
			props: {
				text: Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(sizing[name] ?? ""),
				enabled: canEdit && (ui.selection || []).length < 2,
				action: {
					type: "buffer",
					key
				},
				commitAction: {
					type: "sizingCommit",
					key,
					field: name
				}
			}
		});
	}
	if (item.kind === "grid") {
		field("columns", "Grid columns", item.columns || 3);
		field("min_cell_width", "Minimum cell width", item.min_cell_width || 200);
		field("row_height", "Grid row height", item.row_height || 120);
	}
	if (item.kind === "row") field("collapse_width", "Stack below width", item.collapse_width ?? 600);
	if (parent && block(document, parent)?.kind === "grid") {
		field("column_span", "Column span", item.column_span || 1);
		field("row_span", "Row span", item.row_span || 1);
	}
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs
function blockTitle(item, key, language) {
	if (item.title && item.title !== item.kind) return item.title;
	return translate(item.kind[0].toUpperCase() + item.kind.slice(1), language) + " " + (Number(key.split(".").pop()) + 1);
}
function model(raw, ui) {
	return Object.assign({}, raw, {
		ready: raw.canWrite,
		identity: raw.document?.name || "",
		dirty: raw.dirty || Object.keys(ui.text).length > 0,
		pendingText: Object.keys(ui.text).length > 0,
		saveAllowed: !!raw.checked,
		error: raw.error || ui.error,
		document: raw.document || {},
		layers: [{
			key: "page",
			depth: 0,
			label: raw.document?.title || "Page",
			kind: "page"
		}].concat(layers(raw.document || { blocks: [] }))
	});
}
function toolbar(model, ui, width, language) {
	return toolbar$1(model, ui, width, language);
}
function models(model) {
	return { pageBlocks: model.layers };
}
function row(list, record, model, ui, language) {
	const key = record.key === "page" ? "" : record.key;
	const title = record.label === record.kind ? blockTitle({ kind: record.kind }, record.key, language) : record.label;
	return { nodes: [node("Action", "pageBlock_" + record.key, rect(0, 0, list.width - 16, 38), {
		text: title,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		selected: (ui.selection || []).includes(key) || ui.selected === key,
		children: [label("pageBlockLabel_" + record.key, rect(8 + record.depth * 12, 0, list.width - 32 - record.depth * 12, 38), title)],
		action: {
			type: "select",
			key
		}
	})] };
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	if (ui.selected && !model.layers.some((row) => row.key === ui.selected)) ui = Object.assign({}, ui, { selected: "" });
	if (height < 400) return { nodes: [node("Scroll", "pageEditorScroll", rect(0, 0, width, height), {
		contentHeight: 640,
		scrollbarId: "pageEditorScrollBar",
		children: describe(model, ui, width - 16, 640, language).nodes
	})] };
	const tr = (s) => translate(s, language), canEdit = model.canWrite && !model.busy && !model.uncertain;
	const noticesModel = Object.assign({}, model, { confirmationText: ui.confirmation === "page" ? "Discard changes to the current view and continue?" : ui.confirmation === "remove" ? "Remove this widget from the page?" : void 0 });
	const notice = notices(noticesModel, ui, width, language), nodes = notice.nodes;
	let y = notice.top;
	const newWidth = language === "ru" ? 170 : 120;
	const pickerWidth = Math.min(360, Math.max(100, width - newWidth - 70));
	nodes.push(node("Choice", "pageLayoutChoice", rect(0, y, pickerWidth, 38), {
		label: tr("Page layout"),
		value: model.document.name || "",
		options: model.catalog.map((r) => ({
			value: r.identity,
			label: r.label
		})),
		enabled: !model.busy && !model.uncertain,
		action: { type: "load" }
	}), button("pageLayoutNew", rect(pickerWidth + 12, y, newWidth, 38), tr("New page"), "add", { type: "new" }, canEdit), button("pageLayoutOpen", rect(pickerWidth + newWidth + 24, y, 38, 38), tr("Open saved view"), "open-in-new", { type: "open" }, !model.dirty && !!model.document.name && !model.busy));
	y += 50;
	if (ui.creating) {
		const w = Math.min(300, Math.max(100, (width - 12) / 2));
		nodes.push(node("Field", "pageLayoutName", rect(0, y, w, 38), {
			label: tr("Page name"),
			placeholder: "my_dashboard",
			text: ui.newName,
			action: { type: "newName" }
		}), node("Field", "pageLayoutTitle", rect(w + 12, y, w, 38), {
			label: tr("Title"),
			placeholder: tr("Title"),
			text: ui.newTitle,
			action: { type: "newTitle" }
		}), button("pageLayoutCreate", rect(0, y + 48, 164, 38), tr("Create draft"), "add", { type: "create" }, canEdit), button("pageLayoutCancelNew", rect(176, y + 48, 120, 38), tr("Cancel"), "close", { type: "cancelNew" }, true));
		y += 98;
	}
	if (!model.document.name) {
		nodes.push(label("pageChooseHelp", rect(0, y, width, 90), tr("Choose a page or create a new page."), Object.assign({}, muted, { wrap: true })));
		return { nodes };
	}
	const narrow = width < 1e3, modeWidth = narrow ? 38 : language === "ru" ? 200 : 176, left = narrow ? width : 220, right = narrow ? width : 310, canvasX = narrow || ui.preview ? 0 : left + 12, canvasWidth = narrow || ui.preview ? width : width - left - right - 24;
	nodes.push(node("Choice", "pageAddWidget", rect(0, y, Math.min(width, 220), 38), {
		label: tr("Add widget"),
		value: "",
		options: [{
			value: "",
			label: tr("Add widget")
		}].concat(kinds.map((value) => ({
			value,
			label: tr({
				items: "Items",
				details: "Details",
				row: "Row",
				column: "Column",
				text: "Text",
				markdown: "Markdown",
				metric: "Metric",
				table: "Table",
				link: "Link",
				chart: "Bar chart",
				summary: "Grouped report",
				grid: "Grid layout",
				heading: "Heading",
				icon: "Icon",
				image: "Object image",
				button: "Button",
				divider: "Divider",
				spacer: "Spacer"
			}[value])
		}))),
		enabled: canEdit && !ui.preview,
		toolTip: model.layers.some((row) => row.kind === "items") ? tr("Items preview shows up to three records.") : "",
		action: { type: "add" }
	}));
	if (!ui.preview) {
		const current = fingerprint(model.document);
		const historyCurrent = ui.historyDocument === current;
		const ready = canEdit && !model.pendingText && !ui.confirmation;
		const single = (ui.selection || []).length < 2;
		const p = path(ui.selected), rows = p.length ? siblings(model.document, p) : [];
		const actions = [
			[
				"Undo",
				"undo",
				{ type: "undo" },
				ready && historyCurrent && ui.past?.length
			],
			[
				"Redo",
				"redo",
				{ type: "redo" },
				ready && historyCurrent && ui.future?.length
			],
			[
				"Duplicate widget",
				"content-copy",
				{ type: "duplicate" },
				ready && single && !!ui.selected
			],
			[
				"Move up",
				"arrow-upward",
				{
					type: "reorder",
					delta: -1
				},
				ready && single && p.length && p[p.length - 1] > 0
			],
			[
				"Move down",
				"arrow-downward",
				{
					type: "reorder",
					delta: 1
				},
				ready && single && p.length && p[p.length - 1] < rows.length - 1
			]
		];
		const separate = width < 700;
		actions.forEach(([title, icon, action, enabled], index) => nodes.push(button("pageAction_" + action.type + (action.delta || ""), rect((separate ? 0 : 232) + index * 40, y + (separate ? 44 : 0), 32, 32), tr(title), icon, action, !!enabled, { iconOnly: true })));
	}
	y += 50;
	nodes.push(button("pagePreviewMode", rect(width - modeWidth, y - 50, modeWidth, 38), tr(ui.preview ? "Back to editing" : "Clean preview"), ui.preview ? "edit" : "visibility", { type: "preview" }, !model.busy && !ui.creating && !model.pendingText, { iconOnly: narrow }));
	if (!ui.preview && width < 700) y += 44;
	if (width >= 500) {
		if (ui.preview) nodes.push(label("pageSelectionHint", rect(0, y, width, 24), tr(ui.preview ? "Read-only draft preview. Nothing is saved." : "Click to select. Alt-click for underlying layers."), Object.assign({}, muted, { fontRole: "caption" })));
		else {
			const p = path(ui.selected), crumbs = [{
				key: "",
				title: model.document.title || tr("Page")
			}];
			p.forEach((_, index) => {
				const key = p.slice(0, index + 1).join("."), item = block(model.document, key);
				crumbs.push({
					key,
					title: blockTitle(item, key, language)
				});
			});
			let x = 0;
			const children = [];
			crumbs.forEach((crumb, index) => {
				if (index) {
					children.push(label("pageAncestorSeparator_" + index, rect(x, 0, 20, 30), "›", muted));
					x += 20;
				}
				const w = Math.max(60, Math.min(180, crumb.title.length * 8 + 24));
				children.push(listAction("pageAncestor_" + (crumb.key || "page"), rect(x, 0, w, 30), crumb.title, "", {
					type: "select",
					key: crumb.key
				}, !model.busy && !model.pendingText, {
					toolTip: crumb.title,
					selected: crumb.key === ui.selected
				}));
				x += w;
			});
			nodes.push(node("Scroll", "pageAncestors", rect(0, y, width, 46), {
				contentWidth: x,
				contentHeight: 30,
				scrollbarId: "pageAncestorsBar",
				children
			}));
		}
		y += ui.preview ? 32 : 50;
	}
	if (narrow && !ui.preview) {
		nodes.push(sectionSelector("pageEditorPanels", [
			{
				value: "layers",
				label: tr("Page blocks")
			},
			{
				value: "canvas",
				label: tr("Canvas")
			},
			{
				value: "properties",
				label: tr("Properties")
			}
		], ui.panel, rect(0, y, width, 38), !model.busy, "panel"));
		y += 50;
	}
	const h = Math.max(100, height - y);
	{
		if (!ui.preview && (!narrow || ui.panel === "layers")) nodes.push(node("Box", "pageLayersPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [label("pageLayersTitle", rect(12, 12, left - 24, 24), tr("Page blocks"), { weight: 600 }), node("List", "pageBlocks", rect(12, 48, left - 24, Math.max(0, h - 60)), {
				source: "pageBlocks",
				keyField: "key",
				rowHeight: 42,
				scrollbarId: "pageBlocksScrollBar"
			})]
		}));
		const item = ui.selected ? block(model.document, ui.selected) : null, fields$2 = [];
		function field(name, title, value, root = false, kind) {
			const key = (root ? "page" : ui.selected) + ":" + name;
			const props = {
				text: Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(value ?? ""),
				action: {
					type: "buffer",
					key
				},
				commitAction: {
					type: "commit",
					key,
					field: name,
					root
				},
				enabled: canEdit && (ui.selection || []).length < 2
			};
			fields$2.push({
				id: "pageProperty_" + name,
				title,
				kind,
				props
			});
		}
		field("title", "Title", item ? item.title : model.document.title, !item);
		if (!item) fields$2.push(...fields(model, ui, right - 24, language, canEdit && (ui.selection || []).length < 2));
		if (item) {
			const parent = path(ui.selected).slice(0, -1).join(".");
			fields$2.push({
				kind: "Choice",
				id: "pageParent",
				title: "Parent container",
				props: {
					value: parent,
					enabled: canEdit && (ui.selection || []).length < 2 && !model.pendingText,
					action: { type: "reparent" }
				},
				options: [{
					value: "",
					label: model.document.title || tr("Page")
				}].concat(model.layers.filter((row) => [
					"row",
					"column",
					"grid",
					"details"
				].includes(row.kind) && row.key !== ui.selected && !row.key.startsWith(ui.selected + ".")).map((row) => ({
					value: row.key,
					label: path(row.key).map((_, index) => {
						const key = path(row.key).slice(0, index + 1).join(".");
						return blockTitle(block(model.document, key), key, language);
					}).join(" / ")
				})))
			});
			fields$2.push(...fields$1(model, ui, right - 24, language, canEdit && (ui.selection || []).length < 2));
			fields$2.push(...fields(model, ui, right - 24, language, canEdit && (ui.selection || []).length < 2));
			if ([
				"text",
				"heading",
				"markdown"
			].includes(item.kind) && mode(model.document, ui.selected) === "static") field("text", "Text", item.text || "", false, item.kind === "markdown" ? "Area" : void 0);
			if (["link", "button"].includes(item.kind)) field("href", "Link URL", item.href || "");
			componentFields(fields$2, item, ui, canEdit, language, field);
			fields$2.push({
				kind: "Heading",
				id: "pageLayoutHeading",
				title: "Layout"
			});
			field("offset_x", "Horizontal offset", item.offset_x || 0);
			field("offset_y", "Vertical offset", item.offset_y || 0);
			sizingFields(fields$2, item, ui, model.document, parent, canEdit, language, field);
			field("width", "Width", item.width);
			field("height", "Height", item.height);
			field("weight", "Flexible width", item.weight || 1);
			if ([
				"row",
				"column",
				"grid",
				"details"
			].includes(item.kind)) field("gap", "Gap", item.gap ?? 8);
			for (const name of ["padding", "margin"]) fields$2.push(spacingField("page" + name, tr(name === "padding" ? "Padding" : "Margin"), item[name] || [
				0,
				0,
				0,
				0
			], ui.text, {
				type: "spacing",
				field: name
			}, language, canEdit && (ui.selection || []).length < 2, right - 72));
			fields$2.push({
				kind: "Heading",
				id: "pageAppearanceHeading",
				title: (ui.selection || []).length > 1 ? "Appearance for selection" : "Appearance"
			});
			const appearance = Object.assign({
				fill: "transparent",
				stroke: "outlineVariant",
				stroke_width: 0,
				radius: 0,
				shadow: false,
				animate: false
			}, item.appearance || {});
			for (const [name, title] of [
				["fill", "Fill color"],
				["stroke", "Stroke color"],
				["stroke_width", "Stroke width"],
				["radius", "Corner radius"],
				["shadow", "Shadow"],
				["animate", "Animate layout changes"]
			]) {
				if (["fill", "stroke"].includes(name)) {
					const roles = name === "fill" ? [
						["transparent", "Transparent"],
						["panel", "Panel"],
						["workspace", "Workspace"],
						["surfaceContainerLow", "Low surface"]
					] : [
						["outlineVariant", "Outline"],
						["contentAccent", "Accent"],
						["transparent", "Transparent"]
					];
					fields$2.push({
						kind: "Choice",
						id: "pageAppearance_" + name,
						title,
						props: {
							value: appearance[name],
							enabled: canEdit,
							action: {
								type: "appearance",
								field: name
							}
						},
						options: roles.map(([value, label]) => ({
							value,
							label: tr(label)
						})).concat(appearance[name].startsWith("#") ? [{
							value: appearance[name],
							label: appearance[name]
						}] : [])
					});
					fields$2.push({
						kind: "ColorChoice",
						id: "pageColor_" + name,
						title: name === "fill" ? "Custom fill color" : "Custom stroke color",
						props: {
							value: appearance[name].startsWith("#") ? appearance[name] : "#607D8B",
							enabled: canEdit,
							action: {
								type: "appearance",
								field: name
							}
						}
					});
					continue;
				}
				const key = ui.selected + ":appearance:" + name, toggle = ["shadow", "animate"].includes(name);
				fields$2.push({
					id: "pageAppearance_" + name,
					title,
					kind: toggle ? "CheckBox" : "Field",
					description: name === "animate" ? "Follows appearance motion settings. Disabled while editing." : void 0,
					props: toggle ? {
						checked: appearance[name],
						action: {
							type: "appearance",
							field: name
						},
						enabled: canEdit
					} : {
						text: Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(appearance[name]),
						action: {
							type: "buffer",
							key
						},
						commitAction: {
							type: "appearanceCommit",
							field: name,
							key
						},
						enabled: canEdit
					}
				});
			}
			if (item.kind === "items") fields$2.push({
				kind: "Button",
				id: "pageEditCard",
				title: "Edit card layout",
				props: {
					icon: "edit",
					enabled: !model.busy,
					action: { type: "card" }
				}
			});
			fields$2.push({
				kind: "Button",
				id: "pageRemoveBlock",
				title: "Remove widget",
				props: {
					icon: "delete",
					enabled: canEdit && (ui.selection || []).length < 2,
					action: { type: "remove" }
				}
			});
		}
		const properties = (ui.selection || []).length > 1 ? fields$2.filter((field) => field.id === "pageAppearanceHeading" || field.id.startsWith("pageAppearance_") || field.id.startsWith("pageColor_")) : fields$2;
		const body = sections(properties, right - 24, language, canEdit);
		if (!ui.preview && (!narrow || ui.panel === "properties")) nodes.push(node("Box", "pagePropertiesPanel", rect(width - right, y, right, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [node("Scroll", "pageProperties", rect(12, 12, right - 24, h - 24), {
				contentHeight: body.height,
				scrollbarId: "pagePropertiesBar",
				children: body.nodes
			})]
		}));
	}
	if (ui.preview || !narrow || ui.panel === "canvas") {
		const tools = controls(ui, canvasWidth - 24, language, !model.busy);
		nodes.push(node("Box", "pageCanvasPanel", rect(canvasX, y, canvasWidth, h), {
			background: "workspace",
			border: "outlineVariant",
			children: [node("Box", "pageCanvasTools", rect(12, 12, canvasWidth - 24, tools.height), { children: tools.nodes }), node("View", "pageCanvas", rect(12, 20 + tools.height, canvasWidth - 24, Math.max(1, h - tools.height - 32)), { view: "pagePreview" })]
		}));
	}
	return { nodes };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs
function initial() {
	return {
		selected: "",
		selection: [],
		multiSelect: false,
		snap: true,
		panel: "canvas",
		preview: false,
		text: {},
		confirmation: "",
		pendingPage: "",
		creating: false,
		newName: "",
		newTitle: "",
		recordQuery: "",
		pageFilter: 0,
		past: [],
		future: [],
		historyDocument: "",
		canvas: {
			width: 0,
			zoom: "fit"
		},
		canvasWidthText: "",
		error: ""
	};
}
function shortcut(key, control, shift, alt) {
	if (!control || alt) return null;
	key = key.toLowerCase();
	if (key === "z") return { type: shift ? "redo" : "undo" };
	if (key === "y" && !shift) return { type: "redo" };
	if (key === "d" && !shift) return { type: "duplicate" };
	return null;
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [];
	const current = fingerprint(model.document);
	if (ui.historyDocument && ui.historyDocument !== current) {
		next.past = [];
		next.future = [];
		next.historyDocument = "";
		next.selected = "";
		next.selection = [];
	}
	if (event.type === "confirm" && ["page", "remove"].includes(ui.confirmation) && (model.busy || model.uncertain || !model.canWrite)) return {
		ui: next,
		commands
	};
	function replace(document) {
		if (fingerprint(document) === current) return;
		next.past = next.past.concat([{
			document: copy(model.document),
			selected: ui.selected,
			selection: ui.selection
		}]).slice(-20);
		next.future = [];
		next.historyDocument = fingerprint(document);
		commands.push({
			type: "document",
			document
		});
		next.error = "";
	}
	if (event.type === "keep") next.pendingPage = "";
	if (event.type === "confirm" && ui.confirmation === "page" && !model.busy && !model.uncertain) {
		next.confirmation = "";
		commands.push({ type: "discard" }, {
			type: "load",
			name: ui.pendingPage
		});
		next.pendingPage = "";
		return {
			ui: next,
			commands
		};
	}
	if (event.type === "confirm" && ui.confirmation === "remove" && model.canWrite && !model.busy && !model.uncertain) {
		try {
			replace(remove(model.document, ui.selected));
			next.selected = "";
			next.selection = [];
		} catch (e) {
			next.error = e.message;
		}
		next.confirmation = "";
		return {
			ui: next,
			commands
		};
	}
	const document = documentEvent(next, model, event);
	if (document) {
		if (document.commands.some((command) => ["discard", "reload"].includes(command.type))) Object.assign(document.ui, {
			selected: "",
			selection: [],
			text: {},
			past: [],
			future: [],
			historyDocument: ""
		});
		return document;
	}
	if (model.busy || ui.confirmation) return {
		ui: next,
		commands
	};
	if ((!model.canWrite || model.uncertain) && ![
		"select",
		"panel",
		"preview",
		"source",
		"recordQuery",
		"canvasSize",
		"canvasWidthBuffer",
		"canvasWidthCommit",
		"canvasZoom",
		"multiSelect",
		"snap",
		"selection"
	].includes(event.type)) return {
		ui: next,
		commands
	};
	try {
		if (events.includes(event.type)) {
			if (event.key && !Object.prototype.hasOwnProperty.call(ui.text, event.key)) return {
				ui: next,
				commands
			};
			if (Object.keys(ui.text).length && ![
				"pageConditionCommit",
				"reportCommit",
				"pageFilterChange"
			].includes(event.type)) throw Error("Apply or discard the pending text before continuing");
			const result = edit(model, next, event);
			Object.assign(next, result.ui);
			if (result.document) replace(result.document);
			return {
				ui: next,
				commands
			};
		}
		const pending = Object.keys(ui.text);
		if (pending.length && ["data", "filter"].includes(event.type) && !(event.type === "filter" && event.action === "remove" && pending.every((key) => key === "filter:" + event.index))) throw Error("Apply or discard the pending text before continuing");
		if (Object.keys(ui.text).length && [
			"select",
			"geometry",
			"selection",
			"align",
			"appearance",
			"sizing",
			"add",
			"remove",
			"change",
			"undo",
			"redo",
			"duplicate",
			"reorder",
			"reparent"
		].includes(event.type)) throw Error("Apply or discard the pending text before continuing");
		switch (event.type) {
			case "canvasSize":
			case "canvasWidthCommit": {
				const text = event.type === "canvasSize" ? String(event.value === "auto" ? "" : event.value) : ui.canvasWidthText.trim();
				if (text && (!/^\d+$/.test(text) || Number(text) < 320 || Number(text) > 3840)) throw Error("Enter a preview width from 320 to 3840 pixels, or leave it empty for Auto.");
				next.canvas = Object.assign({}, ui.canvas, { width: text ? Number(text) : 0 });
				next.canvasWidthText = text;
				next.error = "";
				break;
			}
			case "canvasWidthBuffer":
				next.canvasWidthText = String(event.value);
				break;
			case "canvasZoom":
				if (event.value !== "fit" && !zooms.includes(Number(event.value))) throw Error("Choose an available canvas zoom");
				next.canvas = Object.assign({}, ui.canvas, { zoom: String(event.value) });
				next.error = "";
				break;
			case "undo":
			case "redo": {
				if (ui.preview) break;
				const from = event.type === "undo" ? "past" : "future";
				const to = event.type === "undo" ? "future" : "past";
				if (!next[from].length) break;
				const snapshot = next[from][next[from].length - 1];
				next[from] = next[from].slice(0, -1);
				next[to] = next[to].concat([{
					document: copy(model.document),
					selected: ui.selected,
					selection: ui.selection
				}]).slice(-20);
				next.selected = snapshot.selected;
				next.selection = snapshot.selection || [snapshot.selected].filter(Boolean);
				next.recordQuery = "";
				next.pageFilter = 0;
				next.historyDocument = fingerprint(snapshot.document);
				next.error = "";
				commands.push({
					type: "document",
					document: copy(snapshot.document)
				});
				break;
			}
			case "duplicate":
			case "reorder":
			case "reparent": {
				if (ui.preview || !ui.selected) break;
				const value = event.type === "duplicate" ? duplicate(model.document, ui.selected) : event.type === "reorder" ? reorder(model.document, ui.selected, event.delta) : reparent(model.document, ui.selected, event.value);
				replace(value.document);
				next.selected = value.key;
				next.selection = [value.key];
				break;
			}
			case "preview":
				if (Object.keys(ui.text).length) throw Error("Apply or discard the pending text before continuing");
				next.preview = !ui.preview;
				break;
			case "panel":
				if ([
					"layers",
					"canvas",
					"properties"
				].includes(event.value)) next.panel = event.value;
				break;
			case "select":
				next.selection = event.key ? ui.multiSelect ? toggle(ui.selection || [], event.key) : [event.key] : [];
				if (event.key) block(model.document, event.key);
				next.selected = next.selection.includes(event.key) ? event.key : next.selection[next.selection.length - 1] || "";
				next.text = {};
				next.recordQuery = "";
				break;
			case "selection":
				for (const key of event.keys) block(model.document, key);
				next.selection = roots(event.keys);
				next.selected = next.selection[next.selection.length - 1] || "";
				next.recordQuery = "";
				break;
			case "multiSelect":
				next.multiSelect = !ui.multiSelect;
				break;
			case "snap":
				next.snap = !ui.snap;
				break;
			case "align": {
				if (ui.preview) break;
				const changes = alignment(selected(event.boxes || [], ui.selection), event.value);
				if (changes.length) replace(geometries(model.document, changes, event.boxes).document);
				break;
			}
			case "sizing":
			case "sizingCommit":
				if (ui.preview) break;
				if (event.type === "sizingCommit" && !Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
				replace(sizing(model.document, ui.selected, event.field, event.type === "sizingCommit" ? ui.text[event.key] : event.value));
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
				break;
			case "appearance":
			case "appearanceCommit":
				if (ui.preview) break;
				if (event.type === "appearanceCommit" && !Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
				replace(appearances(model.document, ui.selection.length ? ui.selection : [ui.selected], event.field, event.type === "appearanceCommit" ? ui.text[event.key] : event.value));
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
				break;
			case "recordQuery":
				next.recordQuery = event.value;
				break;
			case "source": {
				const source = scope(model.document, ui);
				commands.push({
					type: "source",
					searchType: source.searchType,
					recordKey: source.recordKey,
					query: event.query ? ui.recordQuery : null
				});
				break;
			}
			case "data":
				replace(change(model.document, ui.selected, event.field, event.value));
				next.recordQuery = "";
				break;
			case "filter":
			case "filterCommit": {
				if (event.type === "filterCommit" && !Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
				const edit = event.type === "filterCommit" ? Object.assign({}, event, {
					field: "value",
					value: ui.text[event.key]
				}) : event;
				const source = scope$1(model.document, ui.selected);
				replace(filter(model.document, ui.selected, edit, model.dataSource?.searchType === source.searchType ? model.dataSource : {}));
				next.text = Object.assign({}, next.text);
				delete next.text[event.key || "filter:" + event.index];
				break;
			}
			case "load":
				if (model.dirty) {
					next.confirmation = "page";
					next.pendingPage = event.value;
				} else {
					commands.push({
						type: "load",
						name: event.value
					});
					next.selected = "";
					next.selection = [];
					next.creating = false;
				}
				break;
			case "new":
				if (model.dirty) throw Error("Save or discard changes before continuing");
				next.creating = true;
				break;
			case "cancelNew":
				next.creating = false;
				break;
			case "newName":
			case "newTitle":
				next[event.type] = event.value;
				break;
			case "create":
				if (model.dirty) throw Error("Save or discard changes before continuing");
				if (!/^[a-z][a-z0-9_]{0,47}$/.test(ui.newName) || !ui.newTitle.trim()) throw Error("Enter a page name and title");
				if (model.catalog.some((row) => row.identity === ui.newName)) throw Error("A view with this name already exists");
				commands.push({
					type: "create",
					name: ui.newName,
					title: ui.newTitle.trim()
				});
				next.creating = false;
				next.selected = "";
				next.selection = [];
				break;
			case "buffer":
				next.text = Object.assign({}, ui.text, { [event.key]: event.value });
				break;
			case "commit":
				if (!Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
				replace(change$1(model.document, event.root ? "" : ui.selected, event.field, ui.text[event.key]));
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
				break;
			case "change":
				replace(change$1(model.document, event.root ? "" : ui.selected, event.field, event.value));
				break;
			case "spacing":
				if (!Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
				replace(spacing(model.document, ui.selected, event.field, event.side, ui.text[event.key]));
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
				break;
			case "add": {
				if (!event.value) break;
				const value = add(model.document, ui.selected, event.value, model.searchTypes?.[0]?.value);
				replace(value.document);
				next.selected = value.key;
				next.selection = [value.key];
				break;
			}
			case "remove":
				if (ui.selected) next.confirmation = "remove";
				break;
			case "geometry": {
				if (ui.preview) break;
				const value = event.value.changes ? geometries(model.document, event.value.changes, event.boxes) : geometry(model.document, event.value, event.boxes);
				replace(value.document);
				next.selection = value.keys || [value.key];
				next.selected = next.selection.includes(ui.selected) ? ui.selected : next.selection[next.selection.length - 1];
				break;
			}
			case "card": {
				const item = block(model.document, ui.selected);
				if (item?.kind === "items") commands.push({
					type: "card",
					searchType: item.search_type,
					view: item.view
				});
				break;
			}
			case "open":
				if (!model.dirty) commands.push(event);
				break;
			case "check":
				commands.push(event);
				break;
			default: throw Error("Unsupported page editor event: " + event.type);
		}
	} catch (e) {
		next.error = String(e.message || e);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region src/features/administration/PageLayoutEditor.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		searchTypes: Array,
		initialFocus: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved", "card"],
	data() {
		return {
			ui: initial(),
			catalog: [],
			document: null,
			baseline: "",
			revision: "",
			compiled: null,
			canvasBoxes: [],
			checkedDocument: "",
			error: "",
			message: "",
			busy: false,
			uncertain: false,
			canWrite: false,
			sourceTypes: [],
			dataSource: {},
			dataBusy: false,
			dataError: "",
			dataSerial: 0,
			dataEpoch: 0,
			dataInFlight: false,
			pendingData: null,
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			generation: 0,
			previewSerial: 0,
			previewTimer: null,
			previewInFlight: false,
			previewAgain: false,
			pendingSave: null,
			previewKey: "",
			closed: false
		};
	},
	computed: {
		dataScope() {
			return scope(this.document, this.ui);
		},
		dataKey() {
			return JSON.stringify([
				this.project,
				this.ticket,
				this.dataEpoch,
				this.dataScope
			]);
		},
		dirty() {
			return !!this.document && JSON.stringify(this.document) !== this.baseline || Object.keys(this.ui.text).length > 0 || this.uncertain;
		},
		frameModel() {
			return model({
				document: this.document || {},
				catalog: this.catalog,
				dirty: this.dirty,
				busy: this.busy,
				uncertain: this.uncertain,
				canWrite: this.canWrite,
				canLoad: !!this.ticket,
				checked: !!this.document && JSON.stringify(this.document) === this.checkedDocument,
				error: this.error,
				message: this.message,
				dataSource: this.dataSource,
				dataBusy: this.dataBusy,
				dataError: this.dataError,
				searchTypes: this.sourceTypes.length ? this.sourceTypes : (this.searchTypes || []).map((row) => ({
					value: row.search_type,
					label: row.title || row.search_type
				}))
			}, this.ui);
		},
		scene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbar() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		models() {
			return models(this.frameModel);
		},
		views() {
			return { pagePreview: {
				component: _sfc_main$2,
				nodeProps: true,
				props: {
					model: this.compiled || { layoutNodes: [] },
					ticket: this.ticket,
					project: this.project,
					editing: true,
					guides: !this.ui.preview,
					selectedBlock: this.ui.preview ? "" : this.ui.selected,
					canvasViewport: this.ui.canvas,
					selectedBlocks: this.ui.selection,
					multiSelect: this.ui.multiSelect,
					snap: this.ui.snap,
					onSelection: (keys) => this.dispatch({
						type: "selection",
						keys
					}),
					onCanvasBoxes: (boxes) => {
						this.canvasBoxes = boxes;
					},
					onLoaded: (value) => this.sampleLoaded(value),
					onBlock: (key) => this.dispatch({
						type: "select",
						key
					}),
					onGeometry: (value, boxes) => this.dispatch({
						type: "geometry",
						value,
						boxes
					})
				}
			} };
		}
	},
	mounted() {
		this.observe();
		this.reload();
	},
	beforeUnmount() {
		this.closed = true;
		this.dataSerial++;
		this.pendingData = null;
		this.observer?.disconnect();
		this.generation++;
		this.previewSerial++;
		clearTimeout(this.previewTimer);
	},
	watch: {
		dataKey() {
			this.loadSource();
		},
		project() {
			this.reset();
		},
		ticket() {
			this.reset();
		},
		initialFocus(value) {
			if (value && !this.dirty && !this.busy) this.load(value);
		}
	},
	methods: {
		keydown(event) {
			if (event.isComposing || event.repeat || event.defaultPrevented || event.target.closest("input, textarea, [contenteditable=\"true\"]")) return;
			const action = shortcut(event.code?.replace("Key", "") || event.key, event.ctrlKey || event.metaKey, event.shiftKey, event.altKey);
			if (action) {
				event.preventDefault();
				this.dispatch(action);
			}
		},
		async loadSource(source = null) {
			const request = ++this.dataSerial;
			const values = source || this.dataScope;
			this.dataError = "";
			if (!values.searchType || this.closed) {
				this.pendingData = null;
				this.dataSource = {};
				this.dataBusy = false;
				return;
			}
			this.dataBusy = true;
			this.pendingData = {
				serial: request,
				generation: this.generation,
				scope: {
					ticket: this.ticket,
					project: this.project
				},
				values
			};
			if (this.dataInFlight) return;
			this.dataInFlight = true;
			try {
				while (this.pendingData && !this.closed) {
					const pending = this.pendingData;
					this.pendingData = null;
					try {
						const result = await this.call("sources", {
							search_type: pending.values.searchType,
							record_key: pending.values.recordKey || "",
							query: pending.values.query ?? null
						}, pending.scope);
						if (!this.closed && pending.serial === this.dataSerial && pending.generation === this.generation) this.dataSource = result;
					} catch (error) {
						if (!this.closed && pending.serial === this.dataSerial && pending.generation === this.generation) this.dataError = error.message;
					}
				}
			} finally {
				this.dataInFlight = false;
				this.dataBusy = false;
			}
		},
		rowScene(list, row$1) {
			return row(list, row$1, this.frameModel, this.ui, appearance.language);
		},
		sampleLoaded(value) {
			if (!this.compiled?.layoutHasDetails) return;
			const key = value.records?.[0]?.__search_key__;
			if (key && (key !== this.previewKey || !this.compiled.layoutDetail)) {
				this.previewKey = key;
				this.schedule();
			}
		},
		observe() {
			this.observer = observeFrameSizes((entries) => {
				for (const entry of entries) if (entry.target === this.$refs.body) this.viewport = {
					width: entry.contentRect.width,
					height: entry.contentRect.height
				};
				else this.toolbarSize = entry.contentRect.width;
			});
			this.observer.observe(this.$refs.body);
			this.observer.observe(this.toolbarTarget ? document.querySelector(this.toolbarTarget) : this.$el);
		},
		call(action, values = {}, scope = {
			ticket: this.ticket,
			project: this.project
		}) {
			return rpc("execute_cmd", [
				{
					ticket: scope.ticket,
					project: scope.project
				},
				"tactic.ui.panel.dashboard_cmd.DashboardCmd",
				{
					action,
					project_code: scope.project,
					...values
				}
			]).then((result) => result.info);
		},
		reset() {
			this.generation++;
			this.previewSerial++;
			clearTimeout(this.previewTimer);
			this.document = null;
			this.compiled = null;
			this.baseline = "";
			this.checkedDocument = "";
			this.catalog = [];
			this.revision = this.error = this.message = "";
			this.ui = initial();
			this.pendingSave = null;
			this.previewKey = "";
			this.canWrite = false;
			this.busy = this.uncertain = false;
			if (this.ticket) this.reload();
		},
		canLeave() {
			if (this.dirty || this.busy) {
				this.error = "Save or discard changes before continuing";
				return false;
			}
			return true;
		},
		async reload(force = false) {
			if (this.busy || this.dirty && !force) return;
			if (this.uncertain && this.pendingSave) {
				await this.recover();
				return;
			}
			const generation = ++this.generation, scope = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			try {
				const state = await this.call("read", {}, scope);
				if (generation !== this.generation) return;
				this.catalog = state.dashboards.map((row) => ({
					identity: row.view.slice(10),
					label: row.view.slice(10)
				}));
				this.revision = state.revision;
				this.canWrite = true;
				this.sourceTypes = state.sourceTypes || [];
				const name = this.document?.name || this.initialFocus || this.catalog[0]?.identity;
				this.document = null;
				this.baseline = "";
				this.compiled = null;
				if (name) {
					const value = await this.call("read", { name }, scope);
					if (generation !== this.generation) return;
					this.document = value.document;
					this.baseline = JSON.stringify(value.document);
					this.revision = value.revision;
					this.ui = initial();
					this.dataEpoch++;
				}
			} catch (e) {
				if (generation === this.generation) this.error = e.message;
			} finally {
				if (generation === this.generation) {
					this.busy = false;
					if (this.document) this.schedule();
				}
			}
		},
		async load(name) {
			if (this.busy || this.dirty) return;
			const generation = ++this.generation;
			this.busy = true;
			this.error = "";
			try {
				const value = await this.call("read", { name });
				if (generation !== this.generation) return;
				this.document = value.document;
				this.revision = value.revision;
				this.baseline = JSON.stringify(value.document);
				this.ui = initial();
				this.sourceTypes = value.sourceTypes || this.sourceTypes;
				this.dataEpoch++;
				this.compiled = null;
			} catch (e) {
				if (generation === this.generation) this.error = e.message;
			} finally {
				if (generation === this.generation) {
					this.busy = false;
					this.schedule();
				}
			}
		},
		schedule() {
			if (this.closed) return;
			clearTimeout(this.previewTimer);
			this.previewSerial++;
			this.previewTimer = setTimeout(() => this.preview(), 250);
		},
		async preview() {
			if (this.closed || !this.document || this.busy || this.uncertain) return;
			if (this.previewInFlight) {
				this.previewAgain = true;
				return;
			}
			const generation = this.generation, serial = this.previewSerial, document = JSON.stringify(this.document), scope = {
				ticket: this.ticket,
				project: this.project
			};
			this.previewInFlight = true;
			try {
				const value = await this.call("preview", {
					document: JSON.parse(document),
					expected_revision: this.revision,
					detail_key: this.previewKey
				}, scope);
				if (generation === this.generation && serial === this.previewSerial) {
					this.compiled = value.model;
					this.checkedDocument = document;
					this.error = "";
				}
			} catch (e) {
				if (generation === this.generation && serial === this.previewSerial) this.error = e.message;
			} finally {
				this.previewInFlight = false;
				if (this.previewAgain || serial !== this.previewSerial) {
					this.previewAgain = false;
					this.schedule();
				}
			}
		},
		async save() {
			if (this.busy || this.uncertain || !this.frameModel.saveAllowed || !this.dirty) return;
			const payload = {
				document: JSON.parse(JSON.stringify(this.document)),
				expected_revision: this.revision
			};
			if (!this.pendingSave || JSON.stringify(this.pendingSave.payload) !== JSON.stringify(payload)) this.pendingSave = {
				payload,
				operation_id: randomUuid()
			};
			const generation = ++this.generation, pending = this.pendingSave;
			this.busy = true;
			this.error = "";
			try {
				const saved = await this.call("apply", {
					...pending.payload,
					operation_id: pending.operation_id
				});
				if (generation !== this.generation) return;
				if (saved.status !== "applied" || saved.operation_id !== pending.operation_id) throw Error("Invalid save acknowledgement");
				const state = await this.call("read", { name: this.document.name });
				if (generation !== this.generation) return;
				this.document = state.document;
				this.baseline = this.checkedDocument = JSON.stringify(state.document);
				this.revision = state.revision;
				this.compiled = saved.model;
				this.pendingSave = null;
				this.message = "Layout saved";
				this.$emit("saved", saved);
			} catch (e) {
				if (generation === this.generation) {
					this.uncertain = !e.status || e.status >= 500;
					this.error = this.uncertain ? "The save result is unknown. Refresh before trying again." : e.message;
				}
			} finally {
				if (generation === this.generation) this.busy = false;
			}
		},
		async recover() {
			const generation = this.generation, pending = this.pendingSave, scope = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			try {
				const result = await this.call("operation", { operation_id: pending.operation_id }, scope);
				if (generation !== this.generation) return;
				if (result.status === "applied") {
					this.uncertain = false;
					this.busy = false;
					await this.reload(true);
				} else {
					this.uncertain = false;
					this.error = "No saved result was found. Save again to retry the same operation.";
				}
			} catch (e) {
				if (generation === this.generation) this.error = e.message;
			} finally {
				if (generation === this.generation) this.busy = false;
			}
		},
		async dispatch(event) {
			if (event.type === "align") event = {
				...event,
				boxes: this.canvasBoxes
			};
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
				case "source":
					await this.loadSource(command);
					break;
				case "document":
					this.document = command.document;
					this.error = this.message = "";
					this.schedule();
					break;
				case "load":
					await this.load(command.name);
					break;
				case "create":
					this.document = {
						name: command.name,
						title: command.title,
						blocks: []
					};
					this.baseline = "";
					this.compiled = null;
					this.checkedDocument = "";
					this.schedule();
					break;
				case "discard":
					this.document = this.baseline ? JSON.parse(this.baseline) : null;
					this.ui.text = {};
					this.error = "";
					this.schedule();
					break;
				case "save":
					await this.save();
					break;
				case "reload":
					await this.reload(command.force);
					break;
				case "check":
					await this.preview();
					break;
				case "card":
					this.$emit("card", command);
					break;
				case "open":
					window.open(projectPath(this.project) + "dashboard/" + this.document.name, "_blank", "noopener");
					break;
				default: throw Error("Unsupported page command: " + command.type);
			}
		}
	}
};
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "page-layout-editor frame-host",
		"aria-busy": $data.busy,
		onKeydown: _cache[0] || (_cache[0] = (...args) => $options.keydown && $options.keydown(...args))
	}, [(openBlock(), createBlock(Teleport, {
		to: $props.toolbarTarget || "body",
		disabled: !$props.toolbarTarget
	}, [withDirectives(createBaseVNode("div", {
		class: "frame-toolbar-host",
		style: normalizeStyle({ width: $data.toolbarSize + "px" })
	}, [createVNode(_component_FrameView, {
		scene: $options.toolbar,
		onEvent: $options.dispatch
	}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])), createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
		scene: $options.scene,
		models: $options.models,
		"describe-row": $options.rowScene,
		views: $options.views,
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"views",
		"onEvent"
	])], 512)], 40, _hoisted_1);
}
var PageLayoutEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { PageLayoutEditor_default as default };

//# sourceMappingURL=PageLayoutEditor.js.map
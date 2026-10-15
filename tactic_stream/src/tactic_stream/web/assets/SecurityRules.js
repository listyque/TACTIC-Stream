import { I as resolveComponent, K as withDirectives, N as openBlock, c as vShow, g as createBlock, h as createBaseVNode, nt as normalizeStyle, p as Teleport, v as createElementBlock, x as createVNode } from "./vue.js";
import { E as appearance, T as t, q as _plugin_vue_export_helper_default } from "./index.js";
import { R as securityRules } from "./clipboard.js";
import { J as label, X as node, Y as muted, Z as rect, h as _sfc_main$1, q as button, y as translate } from "./App.js";
import { t as observeFrameSizes } from "./resize.js";
import { a as tabs, n as notices, o as toolbar, r as policy, t as documentEvent } from "./admin.document.js";
//#region ../src/tactic_stream/shared_ui/features/administration/security/security.state.mjs
var matrixScopes$1 = [
	"project",
	"link",
	"gear_menu",
	"search_type",
	"process",
	"tasks"
];
function initial() {
	return {
		scope: "project",
		page: "group",
		query: "",
		groupQuery: "",
		targetQuery: "",
		editing: false,
		selectedCell: null,
		confirmation: "",
		text: "",
		baseline: "",
		textKey: ""
	};
}
function pending(ui) {
	return ui.text !== ui.baseline;
}
function source(model, ui) {
	return ui.page === "inherited" ? model.inheritedSource || "" : ui.page === "rule" ? model.jsonSource || "{}" : model.xmlSource || "";
}
function synchronize(ui, model, force) {
	if (!force && pending(ui)) return ui;
	const text = source(model, ui);
	return Object.assign({}, ui, {
		text,
		baseline: text,
		textKey: model.group + ":" + ui.page + ":" + model.selected
	});
}
function transition(ui, model, event) {
	const document = documentEvent(ui, model, event);
	if (document) return document;
	let next = Object.assign({}, ui);
	const commands = [], allow = policy(model);
	const canNavigate = !model.busy && !pending(ui);
	switch (event.type) {
		case "scope":
			if (canNavigate) {
				next.scope = event.value;
				next.query = next.groupQuery = next.targetQuery = "";
				next.editing = false;
				next.selectedCell = null;
				commands.push({ type: "filterMatrix" }, {
					type: "focus",
					id: "adminSecurityTab_" + event.value,
					fallback: "adminSecurityScope"
				});
			}
			break;
		case "page":
			if (canNavigate && (event.value !== "rule" || model.selected >= 0) && [
				"group",
				"xml",
				"rule",
				"inherited"
			].indexOf(event.value) >= 0) {
				next.page = event.value;
				next = synchronize(next, model, true);
				commands.push({
					type: "focus",
					id: "adminSecurityTechnicalPages_" + event.value,
					fallback: "adminSecurityTechnicalPages"
				});
			}
			break;
		case "query":
		case "groupQuery":
		case "targetQuery":
			if (!model.busy) {
				next[event.type] = String(event.value);
				next.selectedCell = null;
				if (event.type !== "targetQuery") commands.push({ type: "filterMatrix" });
			}
			break;
		case "group":
			if (canNavigate) {
				commands.push({
					type: "group",
					value: event.value
				});
				next.editing = false;
			}
			break;
		case "matrix":
			next.selectedCell = {
				row: event.row,
				column: event.column
			};
			if (allow.editable && !pending(ui)) commands.push({
				type: "matrix",
				row: event.row,
				column: event.column
			});
			break;
		case "navigateCell": {
			const row = event.row + event.dy, column = event.column + event.dx;
			if (row >= 0 && row < model.matrixRows.length && column >= 0 && column < model.matrixGroups.length) {
				next.selectedCell = {
					row,
					column
				};
				commands.push({
					type: "focusGrid",
					grid: "adminSecurityMatrix",
					row,
					column,
					id: "adminSecurityCell_" + row + "_" + column
				});
			}
			break;
		}
		case "inherit":
			if (allow.editable && ui.selectedCell && !pending(ui)) commands.push(Object.assign({ type: "inherit" }, ui.selectedCell));
			break;
		case "selectRule":
			if (canNavigate) {
				next.editing = true;
				next.targetQuery = "";
				if (ui.scope === "technical") next.page = "rule";
				commands.push({
					type: "selectRule",
					index: event.index
				});
			}
			break;
		case "back":
			next.editing = false;
			break;
		case "addRule":
			if (allow.editable && !pending(ui)) {
				next.editing = true;
				commands.push({
					type: "addRule",
					scope: ui.scope
				});
			}
			break;
		case "removeRule":
			if (allow.editable && model.selected >= 0 && !pending(ui)) {
				next.editing = false;
				commands.push({ type: "removeRule" });
			}
			break;
		case "attribute":
		case "target":
		case "groupField":
		case "ruleAccess":
			if (allow.editable && !pending(ui)) commands.push(Object.assign({}, event));
			break;
		case "text":
			if (allow.editable && ui.page !== "inherited") next.text = String(event.value);
			break;
		case "applyText":
			if (allow.editable && pending(ui)) commands.push({
				type: "applyText",
				page: ui.page,
				text: ui.text
			});
			break;
		case "discardText":
			next = synchronize(next, model, true);
			break;
		default: throw Error("Unsupported Access rules event: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/security/security.ui.mjs
var scopes = [
	["project", "Projects"],
	["link", "Sidebar links"],
	["gear_menu", "Menu actions"],
	["search_type", "Search Types"],
	["process", "Processes"],
	["tasks", "Task statuses"],
	["sobject", "Search Objects"],
	["sobject_column", "Field access"],
	["builtin", "Global permissions"],
	["search_filter", "Search restrictions"],
	["technical", "Advanced rules"]
];
var levels = [
	["deny", "Deny"],
	["view", "Read"],
	["edit", "Modify"],
	["insert", "Create"],
	["retire", "Archive"],
	["delete", "Delete"],
	["allow", "Full access"]
];
var names = {
	project: ["code"],
	search_type: ["code"],
	process: ["process", "pipeline"],
	link: ["element"],
	sobject: ["key"],
	sobject_column: ["search_type", "column"],
	builtin: ["key"],
	gear_menu: ["submenu", "label"],
	search_filter: [
		"search_type",
		"column",
		"op",
		"value"
	]
};
var contains = (value, query) => String(value).toLowerCase().indexOf(String(query).trim().toLowerCase()) >= 0;
function targets(model, scope) {
	return scope === "builtin" ? (model.metadata.builtinPermissions || []).map((item) => ({
		label: item.title,
		attributes: { key: item.key }
	})) : (model.metadata.targets || {})[scope] || [];
}
function title(record, model, language) {
	const scope = record.group || record.category, target = targets(model, scope).find((item) => Object.keys(item.attributes).every((key) => String(record[key] || "") === String(item.attributes[key])));
	const value = target ? target.label : record.code || record.process || record.element || record.key || record.search_type || record.label;
	return !value || value === "*" ? translate("All targets", language) : scope === "builtin" ? translate(value, language) : String(value);
}
function detail(record) {
	return [
		record.pipeline,
		record.search_type,
		record.column,
		record.submenu,
		record.project,
		record.group === "search_filter" ? String(record.op || "=") + " " + String(record.value || "") : ""
	].filter(Boolean).join(" · ");
}
function models(model, ui, language) {
	const editorScope = model.attributes.group || model.attributes.category || ui.scope;
	return {
		rules: model.records.filter((record) => (record.group || record.category) === ui.scope && contains(title(record, model, language) + " " + detail(record) + " " + JSON.stringify(record), ui.query)),
		allRules: model.records,
		targets: targets(model, editorScope).map((target, index) => Object.assign({ index }, target)).filter((target) => contains(target.label, ui.targetQuery))
	};
}
var list = (id, bounds, source, rowHeight, keyField) => node("List", id, bounds, {
	source,
	rowHeight,
	keyField,
	fields: [],
	scrollbarId: id + "ScrollBar"
});
function describe(model, ui, width, height, language) {
	const tr = (text) => translate(text, language), edit = policy(model).editable && !pending(ui), navigate = !model.busy && !pending(ui);
	const notice = notices(model, ui, width, language, "Discard unsaved access changes?"), nodes = notice.nodes;
	let y = notice.top;
	const matrix = matrixScopes$1.indexOf(ui.scope) >= 0;
	matrix || width < 600 || (width - 12) / 2;
	if (width < 700) {
		nodes.push(node("Choice", "adminSecurityScope", rect(0, y, width, 38), {
			value: ui.scope,
			label: tr("Access rules"),
			options: scopes.map(([value, text]) => ({
				value,
				label: tr(text)
			})),
			enabled: navigate,
			action: { type: "scope" }
		}));
		y += 46;
	} else {
		const columns = Math.max(1, Math.floor(width / (language === "ru" ? 190 : 150))), cellWidth = width / columns;
		const current = scopes.findIndex((scope) => scope[0] === ui.scope), keys = {
			Home: {
				type: "scope",
				value: scopes[0][0]
			},
			End: {
				type: "scope",
				value: scopes[scopes.length - 1][0]
			},
			ArrowLeft: {
				type: "scope",
				value: scopes[(current + scopes.length - 1) % scopes.length][0]
			},
			ArrowRight: {
				type: "scope",
				value: scopes[(current + 1) % scopes.length][0]
			}
		};
		scopes.forEach(([value, text], index) => nodes.push(button("adminSecurityTab_" + value, rect(index % columns * cellWidth, y + Math.floor(index / columns) * 40, cellWidth - 6, 34), tr(text), "", {
			type: "scope",
			value
		}, navigate, {
			radio: true,
			selected: ui.scope === value,
			keys
		})));
		y += Math.ceil(scopes.length / columns) * 40 + 6;
	}
	if (!matrix) {
		nodes.push(node("Choice", "adminSecurityAdvancedGroup", rect(0, y, width, 38), {
			label: tr("Group"),
			options: model.groups.map((group) => ({
				value: group.identity,
				label: group.label
			})),
			value: model.group,
			enabled: navigate,
			action: { type: "group" }
		}));
		y += 46;
	}
	if (!model.ready) {
		nodes.push(label("adminSecurityEmpty", rect(12, y + 12, width - 24, 70), tr(model.busy ? "Working on the server…" : "Select a project"), {
			wrap: true,
			color: "secondaryText"
		}));
		return { nodes };
	}
	if (matrix) {
		const searchWidth = (width - 12) / 2;
		nodes.push(node("Field", "adminSecurityTargetSearch", rect(0, y, searchWidth, 38), {
			text: ui.query,
			label: tr("Find a permission"),
			placeholder: tr("Find a permission"),
			enabled: navigate,
			action: { type: "query" }
		}), node("Field", "adminSecurityGroupSearch", rect(searchWidth + 12, y, searchWidth, 38), {
			text: ui.groupQuery,
			label: tr("Find a group"),
			placeholder: tr("Find a group"),
			enabled: navigate,
			action: { type: "groupQuery" }
		}));
		y += 46;
		const footer = width < 560 ? 78 : 40, gridHeight = Math.max(1, height - y - footer - 8);
		nodes.push(node("Grid", "adminSecurityMatrix", rect(0, y, width, gridHeight), {
			source: "matrix",
			labelWidth: Math.min(260, width * .36),
			headerHeight: 38,
			cellWidth: 136,
			rowHeight: 46,
			caption: tr("Permission"),
			rowHeaders: model.matrixRows.map((target) => ({
				label: target.all ? tr("All") : target.label,
				detail: detail(target.attributes || {})
			})),
			columnHeaders: model.matrixGroups.map((group) => group.label),
			verticalBarId: "adminSecurityMatrixVerticalBar",
			horizontalBarId: "adminSecurityMatrixHorizontalBar",
			rowHeadersId: "adminSecurityRowHeaders",
			columnHeadersId: "adminSecurityColumnHeaders"
		}));
		const cell = model.selectedCell || {};
		nodes.push(button("adminSecurityInherit", rect(0, y + gridHeight + 8, 168, 38), tr("Use inherited"), "undo", { type: "inherit" }, edit && !!ui.selectedCell && !!cell.explicit && !cell.custom));
		nodes.push(label("adminSecurityMatrixHelp", rect(width < 560 ? 0 : 180, y + gridHeight + (width < 560 ? 46 : 8), width < 560 ? width : width - 180, 34), tr("Changes apply to the draft. Save to server to publish them."), Object.assign({ wrap: true }, muted)));
	} else if (ui.scope === "technical") technical(nodes, model, ui, rect(0, y, width, height - y), language, edit, navigate);
	else {
		const split = width >= 900, editorWidth = split ? Math.max(320, width * .36) : width, listWidth = split ? width - editorWidth - 12 : width;
		if (split || !ui.editing) {
			nodes.push(node("Field", "adminAccessSearch", rect(0, y, listWidth - 50, 38), {
				text: ui.query,
				label: tr("Find a permission"),
				placeholder: tr("Find a permission"),
				enabled: navigate,
				action: { type: "query" }
			}), button("adminAddAccessRule", rect(listWidth - 38, y, 38, 38), tr("Add rule"), "add", { type: "addRule" }, edit, { iconOnly: true }), list("adminAccessRules", rect(0, y + 46, listWidth, height - y - 46), "rules", 76, "ruleIndex"));
			if (!models(model, ui, language).rules.length) nodes.push(label("adminAccessRulesEmpty", rect(12, y + 58, listWidth - 40, 60), tr("No rules match the search"), {
				wrap: true,
				color: "secondaryText"
			}));
		}
		if (split || ui.editing) editor(nodes, model, ui, rect(split ? listWidth + 12 : 0, y, editorWidth, height - y), language, edit, !split);
	}
	return { nodes };
}
function editor(nodes, model, ui, bounds, language, edit, back) {
	const tr = (text) => translate(text, language), width = bounds.width, inner = Math.max(1, width - 40), children = [];
	let y = 12;
	if (back) {
		children.push(button("adminAccessBack", rect(12, y, 100, 34), tr("Back"), "chevron-left", { type: "back" }, !model.busy));
		y += 42;
	}
	if (model.selected < 0) children.push(label("adminAccessEditorEmpty", rect(12, y, inner, 80), tr("Select a rule to edit"), {
		wrap: true,
		color: "secondaryText"
	}));
	else {
		const attrs = model.attributes, scope = attrs.group || attrs.category || ui.scope, fields = (names[scope] || []).slice();
		if (Object.prototype.hasOwnProperty.call(attrs, "project")) fields.push("project");
		children.push(label("adminAccessEditorTitle", rect(12, y, inner, 28), title(attrs, model, language), {
			fontRole: "section",
			weight: 600
		}));
		y += 36;
		if (scope !== "search_filter") {
			const count = width < 360 ? 2 : 3, cellWidth = inner / count;
			levels.forEach(([value, text], index) => children.push(button("adminAccessLevel_" + value, rect(12 + index % count * cellWidth, y + Math.floor(index / count) * 38, cellWidth - 4, 34), tr(text), "", {
				type: "attribute",
				field: "access",
				value
			}, edit, {
				radio: true,
				selected: attrs.access === value
			})));
			y += Math.ceil(levels.length / count) * 38 + 8;
		}
		const fieldLabels = {
			code: scope === "project" ? "Project" : "Search Type",
			process: "Process",
			pipeline: "Pipeline",
			element: "Sidebar link",
			key: scope === "builtin" ? "Permission" : "Search Object or operation",
			search_type: "Search Type",
			column: "Field",
			submenu: "Submenu",
			label: "Menu action",
			op: "Operator",
			value: "Value",
			project: "Rule project"
		};
		fields.forEach((field) => {
			children.push(label("adminAccessLabel_" + field, rect(12, y, inner, 22), tr(fieldLabels[field] || field)), node("Field", "adminAccessField_" + field, rect(12, y + 26, inner, 38), {
				text: attrs[field] || "",
				label: tr(fieldLabels[field] || field),
				enabled: edit,
				action: {
					type: "attribute",
					field
				}
			}));
			y += 74;
		});
		children.push(button("adminRemoveAccessRule", rect(12, y, inner, 38), tr("Remove rule"), "delete", { type: "removeRule" }, edit, { destructive: true }));
		y += 50;
		children.push(node("Field", "adminAccessTargetSearch", rect(12, y, inner, 38), {
			text: ui.targetQuery,
			label: tr("Find a target"),
			placeholder: tr("Find a target"),
			enabled: !model.busy,
			action: { type: "targetQuery" }
		}));
		y += 46;
		children.push(list("adminAccessTargets", rect(12, y, inner, 200), "targets", 54, "index"));
		y += 212;
	}
	nodes.push(node("Box", "adminAccessRuleEditor", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children: [node("Scroll", "adminAccessEditorScroll", rect(0, 0, width, bounds.height), {
			children,
			contentHeight: y + 12,
			resetKey: model.group + ":" + model.selected,
			scrollbarId: "adminAccessEditorScrollBar"
		})]
	}));
}
function technical(nodes, model, ui, bounds, language, edit, navigate) {
	const tr = (text) => translate(text, language), width = bounds.width, y = bounds.y;
	const options = [
		["group", "Group defaults"],
		["xml", "XML"],
		["rule", "Selected rule JSON"],
		["inherited", "Inherited rules"]
	].map(([value, text]) => ({
		value,
		label: tr(text),
		disabled: value === "rule" && model.selected < 0
	}));
	nodes.push(width < 650 ? node("Choice", "adminSecurityTechnicalPages", rect(0, y, width, 38), {
		value: ui.page,
		options: options.filter((option) => !option.disabled),
		label: tr("Advanced rules"),
		enabled: navigate,
		action: { type: "page" }
	}) : tabs("adminSecurityTechnicalPages", options, ui.page, rect(0, y, width, 38), navigate, "page"));
	const top = y + 46, remaining = Math.max(1, bounds.height - 46);
	if (ui.page !== "group") {
		const readonly = ui.page === "inherited", footer = readonly ? 0 : 46;
		nodes.push(node("Area", "adminSecuritySource", rect(0, top, width, remaining - footer), {
			text: ui.text,
			label: tr(ui.page === "rule" ? "Selected rule JSON" : ui.page === "inherited" ? "Inherited rules" : "XML"),
			monospace: true,
			enabled: !model.busy,
			readOnly: readonly || !policy(model).editable,
			action: { type: "text" }
		}));
		if (!readonly) nodes.push(button("adminSecurityApplyText", rect(0, top + remaining - 38, Math.min(250, width * .6), 38), tr("Apply to draft"), "check", { type: "applyText" }, policy(model).editable && pending(ui)), button("adminSecurityDiscardText", rect(Math.min(250, width * .6) + 8, top + remaining - 38, Math.min(160, width * .4 - 8), 38), tr("Discard text"), "undo", { type: "discardText" }, !model.busy && pending(ui)));
		return;
	}
	const formWidth = Math.max(1, width - 16), columns = width >= 800 ? 3 : 1, fieldWidth = (formWidth - (columns - 1) * 12) / columns;
	const fields = [
		["accessLevel", "Access level"],
		["project", "Project"],
		["subGroups", "Subgroups"]
	], form = [];
	fields.forEach(([field, text], index) => {
		const x = index % columns * (fieldWidth + 12), fy = Math.floor(index / columns) * 76;
		form.push(label("adminSecurityGroupLabel_" + field, rect(x, fy, fieldWidth, 22), tr(text)));
		form.push(node(field === "accessLevel" ? "Choice" : "Field", "adminSecurityGroup_" + field, rect(x, fy + 28, fieldWidth, 38), {
			text: model.groupDocument[field] || "",
			value: model.groupDocument[field] || "",
			label: tr(text),
			options: (model.metadata.accessLevels || []).map((value) => ({
				value,
				label: value
			})),
			enabled: edit,
			action: {
				type: "groupField",
				field
			}
		}));
	});
	const formHeight = Math.ceil(fields.length / columns) * 76;
	nodes.push(node("Scroll", "adminSecurityDefaults", rect(0, top, width, Math.min(formHeight, remaining * .55)), {
		children: form,
		contentHeight: formHeight,
		scrollbarId: "adminSecurityDefaultsScrollBar"
	}));
	const listY = top + Math.min(formHeight, remaining * .55) + 8;
	nodes.push(list("adminSecurityAllRules", rect(0, listY, width, Math.max(1, top + remaining - listY)), "allRules", 62, "ruleIndex"));
}
function row(listNode, record, model, ui, language) {
	const tr = (text) => translate(text, language), width = Math.max(1, listNode.width - 16), height = listNode.rowHeight - 4, edit = policy(model).editable && !pending(ui), navigate = !model.busy && !pending(ui), nodes = [];
	if (listNode.source === "targets") return { nodes: [node("Action", "adminAccessTarget_" + record.index, rect(0, 0, width, height), {
		text: record.label,
		enabled: edit,
		action: {
			type: "target",
			attributes: record.attributes
		},
		children: [label("adminAccessTargetTitle_" + record.index, rect(12, 4, width - 24, 22), record.label), label("adminAccessTargetDetail_" + record.index, rect(12, 26, width - 24, 18), detail(record.attributes), muted)]
	})] };
	const index = record.ruleIndex, all = listNode.source === "allRules", quick = !all && ui.scope !== "search_filter", small = width < 540, levelWidth = small ? 48 : 64;
	const textWidth = quick && !small ? width - levelWidth * 4 - 42 : width - 44;
	nodes.push(node("Action", "adminAccessRule_" + index, rect(0, 0, width, height), {
		text: title(record, model, language),
		selected: model.selected === index,
		rail: true,
		normalColor: "surfaceContainerLow",
		selectedColor: "selected",
		enabled: navigate,
		action: {
			type: "selectRule",
			index
		},
		children: [label("adminAccessRuleTitle_" + index, rect(12, 4, textWidth - 20, 24), title(record, model, language), { weight: 600 }), label("adminAccessRuleDetail_" + index, rect(12, 28, textWidth - 20, 20), (all ? (record.group || record.category || "") + " · " : "") + detail(record), muted)]
	}));
	if (quick) [
		"deny",
		"view",
		"edit",
		"allow"
	].forEach((value, col) => nodes.push(button("adminPermission_" + index + "_" + value, rect(small ? 8 + col * levelWidth : textWidth + col * levelWidth, small ? 46 : 18, levelWidth - 4, small ? 24 : 34), tr(levels.find((level) => level[0] === value)[1]), "", {
		type: "ruleAccess",
		index,
		value
	}, edit, {
		radio: true,
		selected: record.access === value,
		fontRole: "caption"
	})));
	nodes.push(button("adminEditAccessRule_" + index, rect(width - 36, 6, 32, 32), tr("Edit rule"), "edit", {
		type: "selectRule",
		index
	}, navigate, { iconOnly: true }));
	return { nodes };
}
function cell(grid, record, row, column, model, ui, language) {
	const tr = (text) => translate(text, language), id = "adminSecurityCell_" + row + "_" + column, enabled = policy(model).editable && !pending(ui) && !record.locked && !record.custom, keys = {};
	[
		[
			"ArrowLeft",
			-1,
			0
		],
		[
			"ArrowRight",
			1,
			0
		],
		[
			"ArrowUp",
			0,
			-1
		],
		[
			"ArrowDown",
			0,
			1
		]
	].forEach(([key, dx, dy]) => {
		keys[key] = {
			type: "navigateCell",
			row,
			column,
			dx,
			dy
		};
	});
	const description = record.custom ? tr("Custom access level: {level}. Edit it in Advanced rules.").split("{level}").join(record.access) : record.locked ? tr("Granted by defaults, subgroups or an All rule. Change the granting rule first.") : record.inherited ? tr("Inherited. Click to set an explicit permission.") : tr("Explicit permission for this group.");
	const background = ui.selectedCell && ui.selectedCell.row === row && ui.selectedCell.column === column ? "selected" : "surfaceContainerLow";
	const children = [];
	if (record.custom || record.locked || record.inherited) children.push(node("Icon", "adminSecurityOrigin_" + row + "_" + column, rect(grid.cellWidth - 24, 14, 16, 16), {
		icon: record.custom ? "code" : record.locked ? "lock" : "account-tree",
		text: description,
		color: "secondaryText"
	}));
	return { nodes: [node("CheckBox", id, rect(0, 0, grid.cellWidth - 1, grid.rowHeight - 1), {
		text: (model.matrixGroups[column] || {}).label + " · " + ((model.matrixRows[row] || {}).all ? tr("All") : (model.matrixRows[row] || {}).label),
		description,
		checked: !!record.checked,
		keys,
		enabled,
		indicatorX: (grid.cellWidth - 20) / 2,
		normalColor: background,
		selectedColor: background,
		action: {
			type: "matrix",
			row,
			column
		},
		children
	})] };
}
//#endregion
//#region src/features/administration/securityRules.js
var access = {
	deny: 0,
	false: 0,
	view: 1,
	true: 1,
	edit: 2,
	insert: 3,
	retire: 4,
	delete: 5,
	allow: 5
};
var matrixScopes = [
	"project",
	"link",
	"gear_menu",
	"search_type",
	"process",
	"tasks"
];
var meta = /* @__PURE__ */ new Set([
	"group",
	"category",
	"access",
	"project",
	"ruleIndex"
]);
function parseRules(xml) {
	if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error("Document types and XML entities are not supported");
	const root = new DOMParser().parseFromString(xml, "application/xml").documentElement;
	if (root.localName === "parsererror" || root.querySelector("parsererror")) throw new Error("Access rules XML is not well formed.");
	if (root.tagName !== "rules") throw new Error("Access rules must have a rules root");
	return root;
}
function rules(xml) {
	return [...parseRules(xml).children].filter((node) => node.tagName === "rule").map((node, ruleIndex) => ({
		...Object.fromEntries([...node.attributes].map((attr) => [attr.name, attr.value])),
		ruleIndex
	}));
}
function restoreOriginalXml(original, current) {
	if (!original) return current;
	const serializer = new XMLSerializer();
	return serializer.serializeToString(parseRules(original)) === serializer.serializeToString(parseRules(current)) ? original : current;
}
function changeRule(xml, index, attributes = null) {
	const root = parseRules(xml), nodes = [...root.children].filter((node) => node.tagName === "rule");
	if (attributes === null) {
		nodes[index]?.remove();
		return new XMLSerializer().serializeToString(root);
	}
	if (!Object.values(attributes).every((value) => typeof value === "string")) throw new Error("Attributes must be a JSON object with string values");
	const scope = attributes.group || attributes.category;
	if (!scope) throw new Error("Enter a security scope");
	if (!(scope === "search_filter" && !Object.hasOwn(attributes, "access")) && !Object.hasOwn(access, attributes.access)) throw new Error("Select a valid access level");
	const node = index === -1 ? root.appendChild(root.ownerDocument.createElement("rule")) : nodes[index];
	if (!node) throw new Error("Select an access rule");
	for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
	for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
	return new XMLSerializer().serializeToString(root);
}
function key(scope, attrs, project = "*") {
	return JSON.stringify([
		scope,
		Object.entries(attrs).filter(([name]) => !meta.has(name)).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0),
		scope === "project" ? "*" : project || "*"
	]);
}
function lookupKeys(scope, attributes, project) {
	const attrs = Object.fromEntries(Object.entries(attributes).filter(([name]) => name !== "project"));
	const wildcard = Object.fromEntries(Object.keys(attrs).map((name) => [name, "*"]));
	if (scope === "project") return [key(scope, attrs), key(scope, wildcard)];
	if (scope === "tasks") return [
		key("process", {
			process: "*",
			pipeline: attrs.pipeline
		}),
		key("process", wildcard),
		key("process", attrs)
	];
	if (scope === "gear_menu") return [key(scope, wildcard, project), key(scope, attrs, project)];
	if (scope === "search_type") return [
		key(scope, attrs),
		key(scope, attrs, project),
		key(scope, wildcard),
		key(scope, wildcard, project)
	];
	return [
		key(scope, attrs, project),
		key(scope, attrs),
		key(scope, wildcard, project),
		key(scope, wildcard)
	];
}
function compile(document, metadata, identity, omit = []) {
	const result = /* @__PURE__ */ new Map(), visited = /* @__PURE__ */ new Set(), names = new Map(metadata.groups.map((group) => [group.label, group.identity]));
	function add(records, bound) {
		for (const record of records) {
			const scope = record.group || record.category;
			if (Object.hasOwn(access, record.default)) {
				result.set(JSON.stringify([
					scope,
					[],
					"__DEFAULT__"
				]), record.default);
				continue;
			}
			if (!Object.hasOwn(access, record.access)) continue;
			const identity = key(scope, record, bound || record.project || "*");
			if (access[result.get(identity)] === void 0 || access[result.get(identity)] < access[record.access]) result.set(identity, record.access);
		}
	}
	function collect(code) {
		if (visited.has(code) || !document.groups[code]) return;
		visited.add(code);
		const group = document.groups[code];
		add(rules(group.xml).filter((record) => code !== identity || !omit.includes(record.ruleIndex)), group.project);
		let defaults = rules(metadata.globalDefaultRulesByLevel[group.accessLevel] || "<rules/>");
		if (group.project) {
			defaults = defaults.filter((record) => (record.group || record.category) !== "project");
			defaults.push({
				group: "project",
				code: group.project,
				access: "allow"
			});
		}
		add(defaults, group.project);
		for (const name of group.subGroups.split("|")) if (name === "admin") result.set(key("__admin__", {}), "allow");
		else if (names.has(name)) collect(names.get(name));
	}
	collect(identity);
	return result;
}
function resolve(index, keys) {
	if (index.has(key("__admin__", {}))) return "allow";
	for (const identity of keys) {
		const [scope, attrs, project] = JSON.parse(identity);
		const values = index.has(identity) ? [index.get(identity)] : [];
		const global = JSON.stringify([
			scope,
			attrs,
			"*"
		]);
		if (scope !== "project" && project !== "*" && index.has(global)) values.push(index.get(global));
		if (values.length) return values.reduce((a, b) => access[a] >= access[b] ? a : b);
	}
	return keys.length ? index.get(JSON.stringify([
		JSON.parse(keys.at(-1))[0],
		[],
		"__DEFAULT__"
	])) || "deny" : "deny";
}
function matrix(document, metadata, scope, project, targets, groups) {
	return groups.map((group) => {
		const identity = group.identity, settings = document.groups[identity], index = compile(document, metadata, identity);
		const records = rules(settings.xml);
		return targets.map((target) => {
			const nativeScope = scope === "tasks" ? "process" : scope, bound = settings.project;
			const targetKey = key(nativeScope, target.attributes, bound || target.attributes.project || "*");
			const exact = records.filter((record) => key(record.group || record.category, record, bound || record.project || "*") === targetKey);
			const keys = lookupKeys(scope, target.attributes, project), level = resolve(index, keys);
			const custom = exact.some((record) => ![
				"allow",
				"deny",
				"false"
			].includes(record.access));
			const baseline = exact.length ? compile(document, metadata, identity, exact.map((record) => record.ruleIndex)) : index;
			const proposed = new Map(baseline), desired = access[level] > 0 ? "deny" : "allow";
			proposed.set(targetKey, access[baseline.get(targetKey) || "deny"] > access[desired] ? baseline.get(targetKey) : desired);
			return {
				group: identity,
				checked: access[level] > 0,
				inherited: !exact.length,
				explicit: !!exact.length,
				custom,
				access: level,
				locked: custom || !!(bound && bound !== project && nativeScope !== "project") || access[resolve(proposed, keys)] > 0 === access[level] > 0,
				ruleIndices: exact.map((record) => record.ruleIndex)
			};
		});
	});
}
//#endregion
//#region src/features/administration/SecurityRules.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved"],
	data() {
		return {
			document: null,
			metadata: {},
			baseline: "",
			revision: "",
			context: null,
			group: "",
			selected: -1,
			ui: initial(),
			busy: false,
			uncertain: false,
			canWrite: false,
			error: "",
			message: "",
			request: 0,
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null
		};
	},
	computed: {
		scope: {
			get() {
				return this.ui.scope;
			},
			set(value) {
				this.ui.scope = value;
			}
		},
		page: {
			get() {
				return this.ui.page;
			},
			set(value) {
				this.ui.page = value;
			}
		},
		editing: {
			get() {
				return this.ui.editing;
			},
			set(value) {
				this.ui.editing = value;
			}
		},
		selectedCell: {
			get() {
				return this.ui.selectedCell;
			},
			set(value) {
				this.ui.selectedCell = value;
			}
		},
		query() {
			return this.ui.query;
		},
		groupQuery() {
			return this.ui.groupQuery;
		},
		dirty() {
			return !!this.document && (JSON.stringify(this.document) !== this.baseline || pending(this.ui));
		},
		editable() {
			return !!this.document && this.canWrite && this.context?.ticket === this.ticket && this.context?.project === this.project && !this.busy && !this.uncertain;
		},
		matrixScope() {
			return matrixScopes.includes(this.scope);
		},
		groups() {
			return (this.metadata.groups || []).filter((group) => this.document?.groups[group.identity]);
		},
		groupDocument() {
			return this.document?.groups[this.group];
		},
		records() {
			try {
				return this.groupDocument ? rules(this.groupDocument.xml) : [];
			} catch {
				return [];
			}
		},
		attributes() {
			const { ruleIndex, ...attrs } = this.records.find((record) => record.ruleIndex === this.selected) || {};
			return attrs;
		},
		matrixTargets() {
			return (this.metadata.targets?.[this.scope] || []).filter((item) => !this.query || JSON.stringify(item).toLowerCase().includes(this.query.trim().toLowerCase()));
		},
		matrixGroups() {
			return this.groups.filter((group) => group.label.toLowerCase().includes(this.groupQuery.trim().toLowerCase()));
		},
		cells() {
			if (!this.document || !this.matrixScope) return [];
			try {
				return matrix(this.document, this.metadata, this.scope, this.project, this.matrixTargets, this.matrixGroups);
			} catch {
				return [];
			}
		},
		cell() {
			return this.selectedCell ? this.cells[this.selectedCell.column]?.[this.selectedCell.row] : null;
		},
		frameModel() {
			return {
				ready: !!this.document && this.context?.ticket === this.ticket && this.context?.project === this.project,
				canWrite: this.canWrite,
				canLoad: !!this.ticket && !!this.project,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				pendingText: pending(this.ui),
				error: this.error,
				message: this.message,
				group: this.group,
				groups: this.groups,
				groupDocument: this.groupDocument || {},
				records: this.records,
				attributes: this.attributes,
				selected: this.selected,
				metadata: this.metadata,
				matrixRows: this.matrixTargets,
				matrixGroups: this.matrixGroups,
				selectedCell: this.cell,
				xmlSource: this.groupDocument?.xml || "",
				jsonSource: JSON.stringify(this.attributes, null, 2),
				inheritedSource: this.metadata.globalDefaultRulesByLevel?.[this.groupDocument?.accessLevel] || ""
			};
		},
		models() {
			return {
				...models(this.frameModel, this.ui, appearance.language),
				matrix: this.matrixTargets.map((_, row) => this.matrixGroups.map((_, column) => this.cells[column]?.[row] || {}))
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		}
	},
	watch: {
		project() {
			this.reload();
		},
		ticket() {
			this.request++;
			this.busy = false;
			this.document = null;
			this.ui = initial();
			this.reload(true);
		}
	},
	mounted() {
		this.reload();
		window.addEventListener("beforeunload", this.beforeUnload);
		this.observer = observeFrameSizes((entries) => {
			for (const entry of entries) if (entry.target === this.$refs.body) this.viewport = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			};
			else this.toolbarSize = entry.contentRect.width;
		});
		this.observer.observe(this.$refs.body);
		this.observer.observe(this.toolbarTarget ? document.querySelector(this.toolbarTarget) || this.$el : this.$el);
	},
	beforeUnmount() {
		this.request++;
		this.observer?.disconnect();
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
		rowScene(node, record) {
			return row(node, record, this.frameModel, this.ui, appearance.language);
		},
		cellScene(node, record, row, column) {
			return cell(node, record, row, column, this.frameModel, this.ui, appearance.language);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
				case "filterMatrix": break;
				case "group":
					this.selectGroup(command.value);
					break;
				case "matrix":
					this.changeCell(command.column, command.row);
					break;
				case "inherit":
					this.changeCell(command.column, command.row, true);
					break;
				case "focusGrid":
					await this.$nextTick();
					await this.$refs.frame.focusGrid(command.grid, command.row, command.column, command.id);
					break;
				case "focus":
					await this.$nextTick();
					if (!this.$refs.frame.focusControl(command.id)) this.$refs.frame.focusControl(command.fallback);
					break;
				case "selectRule":
					this.selectRule(command.index);
					break;
				case "addRule":
					this.addRule();
					break;
				case "removeRule":
					this.setRule(this.selected);
					break;
				case "attribute":
					this.setAttribute(command.field, String(command.value));
					break;
				case "target":
					this.setRule(this.selected, {
						...this.attributes,
						...command.attributes
					});
					break;
				case "groupField":
					this.groupDocument[command.field] = command.value;
					break;
				case "ruleAccess": {
					const { ruleIndex, ...attrs } = this.records.find((record) => record.ruleIndex === command.index) || {};
					this.setRule(command.index, {
						...attrs,
						access: command.value
					});
					break;
				}
				case "applyText":
					this.applyText();
					break;
				case "save":
					await this.save();
					break;
				case "reload":
					await this.reload(command.force);
					break;
				case "discard":
					this.ui.text = this.ui.baseline = "";
					this.document = JSON.parse(this.baseline);
					this.selected = this.records[0]?.ruleIndex ?? -1;
					this.syncText();
					this.error = this.message = "";
					break;
				default: throw Error("Unsupported Access rules command: " + command.type);
			}
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.dirty || this.busy || this.uncertain) {
				this.error = "Save or discard access changes before leaving.";
				return false;
			}
			return true;
		},
		accept(result) {
			this.ui.text = this.ui.baseline = "";
			this.canWrite = result.canWrite !== false;
			this.document = result.document;
			this.metadata = result.metadata;
			this.revision = result.revision;
			this.baseline = JSON.stringify(this.document);
			this.group = this.groups.some((group) => group.identity === this.group) ? this.group : this.groups[0]?.identity || "";
			this.selectGroup(this.group);
			for (const group of Object.values(this.document.groups)) parseRules(group.xml);
		},
		async reload(force = false) {
			if (this.busy) return;
			if (this.dirty && !force) {
				this.dispatch({ type: "reload" });
				return;
			}
			const request = ++this.request, context = {
				ticket: this.ticket,
				project: this.project
			};
			if (this.context && (this.context.ticket !== context.ticket || this.context.project !== context.project)) {
				this.document = null;
				this.baseline = "";
				this.ui = initial();
			}
			this.context = context;
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await securityRules("read", context.ticket, context.project);
				if (request !== this.request || context.ticket !== this.ticket || context.project !== this.project) return;
				this.context = context;
				this.uncertain = false;
				this.ui.confirmation = "";
				this.accept(result);
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		pendingText() {
			return pending(this.ui);
		},
		selectGroup(code) {
			if (this.pendingText() && code !== this.group) {
				this.error = "Apply or discard the text draft before changing the selection.";
				return;
			}
			this.group = code;
			this.selected = this.records[0]?.ruleIndex ?? -1;
			this.syncText();
		},
		syncText() {
			this.ui = synchronize(this.ui, this.frameModel, true);
		},
		selectRule(index) {
			if (this.pendingText()) {
				this.error = "Apply or discard the text draft before changing the selection.";
				return;
			}
			this.selected = index;
			this.syncText();
			this.editing = true;
		},
		setRule(index, attributes) {
			if (!this.editable || !this.groupDocument) return;
			try {
				this.setGroupXml(this.group, changeRule(this.groupDocument.xml, index, attributes));
				this.selected = index === -1 ? this.records.length - 1 : attributes ? index : -1;
				this.syncText();
				this.error = "";
				this.message = "";
			} catch (error) {
				this.error = error.message;
			}
		},
		setAttribute(name, value) {
			this.setRule(this.selected, {
				...this.attributes,
				[name]: value
			});
		},
		setGroupXml(identity, xml) {
			this.document.groups[identity].xml = restoreOriginalXml(JSON.parse(this.baseline).groups[identity]?.xml, xml);
		},
		addRule() {
			if (this.pendingText()) return;
			const attrs = {
				group: this.scope,
				access: "deny",
				...{
					project: { code: "*" },
					search_type: { code: "*" },
					process: {
						process: "*",
						pipeline: "*"
					},
					link: { element: "*" },
					builtin: { key: "view_side_bar" },
					sobject: { key: "*" },
					sobject_column: {
						search_type: "*",
						column: "*"
					},
					gear_menu: {
						submenu: "*",
						label: "*"
					},
					search_filter: {
						search_type: "",
						column: "",
						op: "=",
						value: ""
					}
				}[this.scope] || { key: "*" }
			};
			if (!["project", "builtin"].includes(this.scope)) attrs.project = this.project;
			if (this.scope === "search_filter") delete attrs.access;
			this.setRule(-1, attrs);
			this.editing = true;
		},
		changeCell(column, row, inherit = false) {
			if (!this.editable || this.pendingText()) return;
			const cell = this.cells[column][row];
			if (cell.custom || !inherit && cell.locked) return;
			const settings = this.document.groups[cell.group];
			for (const index of [...cell.ruleIndices].reverse()) settings.xml = changeRule(settings.xml, index);
			if (!inherit) settings.xml = changeRule(settings.xml, -1, {
				group: this.scope === "tasks" ? "process" : this.scope,
				...this.matrixTargets[row].attributes,
				access: cell.checked ? "deny" : "allow"
			});
			this.setGroupXml(cell.group, settings.xml);
			this.selectedCell = {
				column,
				row
			};
			if (this.group === cell.group) this.syncText();
			this.error = "";
			this.message = "";
		},
		applyText() {
			if (!this.editable) return;
			try {
				if (this.page === "rule") {
					const attrs = JSON.parse(this.ui.text);
					if (!attrs || Array.isArray(attrs) || typeof attrs !== "object" || Object.values(attrs).some((value) => typeof value !== "string")) throw new Error("Attributes must be a JSON object with string values");
					this.setRule(this.selected, attrs);
				} else {
					parseRules(this.ui.text);
					this.setGroupXml(this.group, this.ui.text);
					this.selected = -1;
					this.syncText();
					this.error = "";
				}
			} catch (error) {
				this.error = error instanceof SyntaxError ? "Attributes must be a JSON object with string values" : error.message;
			}
		},
		async save() {
			if (!this.editable || !this.dirty) return;
			if (this.pendingText()) {
				this.error = "Apply or discard the text draft before saving.";
				return;
			}
			const request = this.request;
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await securityRules("save", this.context.ticket, this.context.project, {
					document: this.document,
					expected_revision: this.revision
				});
				if (request !== this.request) return;
				this.accept(result);
				this.message = "Access rules saved on server";
				this.$emit("saved");
			} catch (error) {
				if (request !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Reload access rules before trying again." : error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "security-rules frame-host",
		style: { "gap": "8px" },
		"aria-label": $options.t("Access rules"),
		"aria-busy": $data.busy
	}, [(openBlock(), createBlock(Teleport, {
		defer: "",
		to: $props.toolbarTarget || "body",
		disabled: !$props.toolbarTarget
	}, [withDirectives(createBaseVNode("div", {
		class: "frame-toolbar-host",
		style: normalizeStyle({ width: $data.toolbarSize + "px" })
	}, [createVNode(_component_FrameView, {
		scene: $options.toolbarScene,
		onEvent: $options.dispatch
	}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])), createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
		ref: "frame",
		scene: $options.frameScene,
		models: $options.models,
		"describe-row": $options.rowScene,
		"describe-cell": $options.cellScene,
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"describe-cell",
		"onEvent"
	])], 512)], 8, _hoisted_1);
}
var SecurityRules_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { SecurityRules_default as default };

//# sourceMappingURL=SecurityRules.js.map
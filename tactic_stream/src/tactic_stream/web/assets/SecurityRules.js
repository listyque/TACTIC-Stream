import { I as resolveComponent, N as openBlock, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, q as withDirectives, rt as normalizeStyle, s as vShow } from "./vue.js";
import { A as t, j as appearance, ot as _plugin_vue_export_helper_default } from "./index.js";
import { Jt as label, Xt as node, Yt as muted, Zt as rect, i as _sfc_main$1, mt as securityRules, qt as button, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { ct as documentEvent, ft as tabs, lt as notices, pt as toolbar$1, ut as policy } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/administration/security/security.access.mjs
var accessLabels = {
	allow: "Full access",
	deny: "Deny",
	view: "Read",
	edit: "Modify",
	insert: "Create",
	retire: "Archive",
	delete: "Delete",
	true: "Read",
	false: "Deny"
};
var scopeLabels = {
	builtin: "Global permissions",
	project: "Projects",
	search_type: "Search Types",
	process: "Processes",
	sobject: "Search Objects",
	sobject_column: "Field access",
	search_filter: "Search restrictions",
	link: "Sidebar links",
	gear_menu: "Menu actions",
	agent_tool: "AI tools",
	mcp_tool: "MCP tools"
};
function toolSettings(model, scope) {
	const rules = model.records.filter((row) => (row.group || row.category) === scope);
	const ranks = {
		deny: 0,
		false: 0,
		view: 1,
		true: 1,
		edit: 2,
		insert: 3,
		retire: 4,
		delete: 5,
		allow: 5
	}, byKey = {};
	let fallback = 0;
	for (const rule of rules) if (rule.default) fallback = ranks[rule.default] || 0;
	else if (rule.key) byKey[rule.key] = Math.max(byKey[rule.key] ?? -1, ranks[rule.access] ?? -1);
	const names = (model.metadata[scope === "mcp_tool" ? "mcpTools" : "agentTools"] || []).filter((tool) => (byKey[tool.name] ?? byKey["*"] ?? fallback) >= 5).map((tool) => tool.name), all = (byKey["*"] ?? fallback) >= 5 && Object.keys(byKey).every((key) => byKey[key] >= 5);
	return {
		mode: !rules.length ? "inherit" : all ? "all" : "selected",
		names
	};
}
function models$1(model, ui, language) {
	const tr = (text) => translate(text, language), metadata = model.metadata || {}, report = metadata.effective, match = (text) => String(text).toLowerCase().includes(ui.query.toLowerCase().trim()), scope = ui.scope, settings = toolSettings(model, scope);
	const effective = [], reportView = ui.reportView || "summary";
	const summary = /* @__PURE__ */ new Map();
	for (const check of reportView === "summary" ? report?.checks || [] : []) {
		const key = check.scope + ":" + JSON.stringify(check.attributes), entry = summary.get(key) || {
			id: "check:" + key,
			title: check.label,
			detail: tr(scopeLabels[check.scope] || check.scope) + " · " + Object.values(check.attributes).join(" · "),
			value: tr("Denied"),
			context: "",
			allowed: false
		};
		if (check.allowed) {
			entry.allowed = true;
			entry.value = tr(check.required === "allow" ? "Allowed" : check.required === "delete" ? "Full access" : accessLabels[check.required] || check.required);
		}
		summary.set(key, entry);
	}
	effective.push(...summary.values());
	for (const group of reportView === "groups" ? report?.groups || [] : []) effective.push({
		id: (group.default ? "defaults:" : "group:") + group.name,
		title: group.name,
		value: tr(group.default ? "System defaults" : group.direct ? "Direct group" : "Inherited group"),
		detail: group.default ? tr("Combined native access level") : group.paths.map((path) => path.join(" → ")).join("; "),
		context: [group.accessLevel, group.project].filter(Boolean).join(" · "),
		icon: "groups"
	});
	for (const rule of reportView === "rules" ? report?.rules || [] : []) {
		const attrs = rule.attributes || {}, title = Object.keys(attrs).map((key) => key + ": " + attrs[key]).join(" · ") || rule.key;
		effective.push({
			id: rule.scope + ":" + rule.key,
			title: tr(scopeLabels[rule.scope] || rule.scope) + " · " + title,
			value: tr(accessLabels[rule.access] || rule.access || "Search restrictions"),
			detail: (rule.sources || []).map((source) => (source.default ? tr("System defaults") : source.group) + ": " + tr(accessLabels[source.access] || source.access || "Search restrictions")).join(" · "),
			context: rule.key,
			icon: "security"
		});
	}
	for (const [transport, catalog] of [["chat", metadata.agentTools], ["mcp", metadata.mcpTools]]) for (const tool of reportView === "tools" ? catalog || [] : []) {
		const allowed = report?.tools?.[transport]?.includes(tool.name), eligible = !metadata.agentAdministratorRequired || report?.administrator;
		if (report) effective.push({
			id: transport + ":" + tool.name,
			title: (transport === "chat" ? tr("AI tools") : "MCP") + " · " + tool.title,
			value: tr(!eligible ? "Administrator access required" : allowed ? "Allowed" : "Denied"),
			detail: tool.description,
			context: tool.name,
			icon: "security"
		});
	}
	return {
		effective: effective.filter((row) => match(JSON.stringify(row))),
		agentTools: (scope === "mcp_tool" ? metadata.mcpTools || [] : metadata.agentTools || []).filter((tool) => match(tool.title + " " + tool.description + " " + tool.name)).map((tool) => Object.assign({}, tool, { checked: settings.mode === "all" || settings.names.includes(tool.name) }))
	};
}
function workspace$1(model, ui, width, height, language) {
	const tr = (text) => translate(text, language), nodes = [], effective = ui.scope === "effective", settings = toolSettings(model, ui.scope), report = model.metadata.effective, available = !model.busy && !model.dirty && !model.uncertain && model.ready;
	let y = 0;
	if (effective) {
		nodes.push(node("Choice", "adminEffectiveUser", rect(0, y, Math.max(1, width - 48), 38), {
			label: tr("User"),
			value: report?.login || "",
			options: [{
				value: "",
				label: tr("Select a user")
			}].concat(model.metadata.users || []),
			enabled: available,
			action: { type: "effectiveUser" }
		}), button("adminEffectiveRefresh", rect(width - 38, y, 38, 38), tr("Refresh"), "refresh", {
			type: "effectiveUser",
			value: report?.login || ""
		}, available && !!report?.login, { iconOnly: true }));
		y += 46;
		nodes.push(label("adminEffectiveNotice", rect(0, y, width, width < 520 ? 82 : 62), tr(model.dirty ? "Save or discard changes to inspect saved user permissions." : !report ? "Select a user to inspect saved permissions." : report.administrator ? "Native administrator: full application rights. Explicit AI and MCP restrictions still apply." : "Saved native rules from all groups. Record filters, field rules and operation checks still apply."), {
			wrap: true,
			color: "secondaryText"
		}));
		y += width < 520 ? 90 : 70;
	} else {
		const narrow = width < 520, buttonWidth = narrow ? (width - 8) / 2 : 148;
		nodes.push(node("Choice", "adminToolMode", rect(0, y, narrow ? width : Math.max(1, width - 312), 38), {
			label: tr("Group tool policy"),
			value: settings.mode,
			options: [
				["inherit", "Inherit"],
				["selected", "Selected tools"],
				["all", "All tools"]
			].map(([value, text]) => ({
				value,
				label: tr(text)
			})),
			enabled: model.canWrite && !model.busy && !model.uncertain,
			action: { type: "toolMode" }
		}));
		if (narrow) y += 46;
		const start = narrow ? 0 : width - 304;
		nodes.push(button("adminToolsRead", rect(start, y, buttonWidth, 38), tr("Read tools"), "visibility", { type: "toolRead" }, model.canWrite && !model.busy && !model.uncertain), button("adminToolsNone", rect(start + buttonWidth + 8, y, buttonWidth, 38), tr("Clear"), "close", { type: "toolNone" }, model.canWrite && !model.busy && !model.uncertain));
		y += 46;
		nodes.push(label("adminToolPolicyNotice", rect(0, y, width, width < 520 ? 106 : 80), tr("Tool access combines all inherited groups. A local deny does not cancel another group grant. Native operation rights and the connection scope still apply."), {
			wrap: true,
			color: "secondaryText"
		}));
		y += width < 520 ? 114 : 88;
		if (!(model.metadata.agentTools || []).length) {
			nodes.push(label("adminToolUnavailable", rect(0, y, width, 80), tr("This server does not expose the agent tool catalogue."), { wrap: true }));
			return { nodes };
		}
	}
	if (effective) {
		nodes.push(node("Choice", "adminEffectiveView", rect(0, y, width, 38), {
			label: tr("Report"),
			value: ui.reportView || "summary",
			enabled: !model.busy,
			options: [
				["summary", "Permission summary"],
				["groups", "Groups and inheritance"],
				["rules", "Rule sources"],
				["tools", "AI and MCP tools"]
			].map(([value, text]) => ({
				value,
				label: tr(text)
			})),
			action: { type: "reportView" }
		}));
		y += 46;
	}
	nodes.push(node("Field", "adminAccessSearch", rect(0, y, width, 38), {
		text: ui.query,
		placeholder: tr("Search"),
		enabled: !model.busy,
		action: { type: "query" }
	}));
	y += 46;
	const source = effective ? "effective" : "agentTools";
	nodes.push(node("List", "adminAccessDetailsList_" + source, rect(0, y, width, Math.max(1, height - y)), {
		source,
		rowHeight: effective ? width < 520 ? 104 : 84 : width < 520 ? 120 : 100,
		keyField: effective ? "id" : "name",
		fields: [],
		scrollbarId: "adminAccessDetailsScrollBar"
	}));
	return { nodes };
}
function row$1(list, record, model, ui, language) {
	const tr = (text) => translate(text, language), width = Math.max(1, list.width - 20), height = list.rowHeight;
	const effective = list.source === "effective", left = effective ? 8 : 44, id = record.id || record.name;
	const nodes = [
		label("adminAccessRowTitle_" + id, rect(left, 4, width - left - 8, 24), record.title, { weight: 600 }),
		label("adminAccessRowDetail_" + id, rect(left, 32, width - left - 8, height - 60), effective ? record.detail : record.description, {
			wrap: true,
			maxLines: height < 100 ? 1 : 2,
			toolTip: effective ? record.detail : record.description,
			color: "secondaryText"
		}),
		label("adminAccessRowValue_" + id, rect(left, height - 24, width - left - 8, 20), effective ? [record.value, record.context].filter(Boolean).join(" · ") : tr(record.readonly ? "Read only" : "Changes data"), Object.assign({}, muted, record.allowed === void 0 ? {} : { color: record.allowed ? "action" : "error" })),
		node("Box", "adminAccessRowDivider_" + id, rect(8, height - 1, width - 16, 1), { background: "outlineVariant" })
	];
	if (!effective) nodes.unshift(node("CheckBox", "adminTool_" + record.name, rect(0, 0, 38, 38), {
		text: record.title,
		checked: record.checked,
		enabled: model.canWrite && !model.busy && !model.uncertain,
		indicatorX: 8,
		action: {
			type: "toolToggle",
			name: record.name
		}
	}));
	return { nodes };
}
//#endregion
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
		reportView: "summary",
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
function inheritanceChoices(model) {
	const documents = model.groupDocuments || {}, groups = model.groups || [], byName = new Map(groups.map((group) => [group.label, group.identity])), selected = (model.groupDocument.subGroups || "").split("|");
	function reaches(identity, visited) {
		if (identity === model.group) return true;
		if (visited.has(identity)) return false;
		visited.add(identity);
		return (documents[identity]?.subGroups || "").split("|").some((name) => {
			const child = byName.get(name);
			return child && reaches(child, visited);
		});
	}
	return groups.filter((group) => group.identity !== model.group).map((group) => Object.assign({}, group, {
		checked: selected.includes(group.label),
		cycle: reaches(group.identity, /* @__PURE__ */ new Set())
	}));
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
		case "reportView":
			if (canNavigate && [
				"summary",
				"groups",
				"rules",
				"tools"
			].includes(event.value)) next.reportView = event.value;
			break;
		case "effectiveUser":
			if (canNavigate && !model.dirty && !model.uncertain && event.value && (model.metadata.users || []).some((user) => user.value === event.value)) commands.push({
				type: "effectiveUser",
				login: event.value
			});
			break;
		case "toolMode":
		case "toolRead":
		case "toolNone":
		case "toolToggle": {
			if (!allow.editable || pending(ui) || !["agent_tool", "mcp_tool"].includes(ui.scope)) break;
			const settings = toolSettings(model, ui.scope), tools = ui.scope === "mcp_tool" ? model.metadata.mcpTools || [] : model.metadata.agentTools || [];
			let mode = "selected", names = settings.mode === "all" ? tools.map((tool) => tool.name) : settings.names;
			if (event.type === "toolMode") {
				if (![
					"inherit",
					"selected",
					"all"
				].includes(event.value)) break;
				mode = event.value;
			} else if (event.type === "toolRead") names = tools.filter((tool) => tool.readonly).map((tool) => tool.name);
			else if (event.type === "toolNone") names = [];
			else {
				if (!tools.some((tool) => tool.name === event.name)) break;
				names = names.includes(event.name) ? names.filter((name) => name !== event.name) : names.concat([event.name]);
			}
			commands.push({
				type: "toolPolicy",
				scope: ui.scope,
				mode,
				names
			});
			break;
		}
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
		case "inheritGroup": {
			const choice = inheritanceChoices(model).find((group) => group.identity === event.identity);
			if (allow.editable && !pending(ui) && choice && (choice.checked || !choice.cycle)) {
				const names = (model.groupDocument.subGroups || "").split("|").filter(Boolean), value = choice.checked ? names.filter((name) => name !== choice.label) : [...names, choice.label];
				commands.push({
					type: "groupField",
					field: "subGroups",
					value: value.join("|")
				});
			}
			break;
		}
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
function toolbar(model, ui, width, language) {
	const scene = toolbar$1(model, ui, width, language), discard = scene.nodes.find((item) => item.id === "adminDiscardDocument");
	discard.text = translate("Reset", language);
	discard.toolTip = translate("Discard changes", language);
	return scene;
}
var scopes = [
	["effective", "Effective permissions"],
	["defaults", "Group inheritance"],
	["project", "Projects"],
	["builtin", "Global permissions"],
	["link", "Sidebar links"],
	["gear_menu", "Menu actions"],
	["search_type", "Search Types"],
	["process", "Processes"],
	["tasks", "Task statuses"],
	["sobject", "Search Objects"],
	["sobject_column", "Field access"],
	["search_filter", "Search restrictions"],
	["agent_tool", "AI tools"],
	["mcp_tool", "MCP tools"],
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
var levelIcons = {
	deny: "close",
	view: "visibility",
	edit: "edit",
	insert: "add",
	retire: "inventory-2",
	delete: "delete",
	allow: "check"
};
var scopeDetails = {
	effective: ["person", "Inspect saved user permissions and their source groups."],
	agent_tool: ["security", "Choose which tools this group can use through the agent chat."],
	mcp_tool: ["link", "Choose which tools this group can expose through MCP."],
	defaults: ["groups", "Choose the groups whose permissions are inherited."],
	project: ["folder", "Choose which projects each group can open."],
	link: ["link", "Choose which sidebar links each group can see."],
	gear_menu: ["menu", "Choose which menu actions each group can use."],
	search_type: ["sobject", "Control access to entity types in this project."],
	process: ["workflow", "Control access to the project workflow processes."],
	tasks: ["tasks", "Control access to task workflow statuses."],
	sobject: ["sobject", "Set permissions for individual records or record keys."],
	sobject_column: ["table-view", "Control access to individual entity fields."],
	builtin: ["security", "Configure the native built-in application permissions."],
	search_filter: ["filter-alt", "Limit the records a group can find using native search rules."],
	technical: ["code", "Inspect and edit native rules, defaults and custom XML."]
};
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
	return Object.assign(models$1(model, ui, language), {
		rules: model.records.filter((record) => (record.group || record.category) === ui.scope && contains(title(record, model, language) + " " + detail(record) + " " + JSON.stringify(record), ui.query)),
		allRules: model.records,
		inheritance: inheritanceChoices(model),
		targets: targets(model, editorScope).map((target, index) => Object.assign({ index }, target)).filter((target) => contains(target.label, ui.targetQuery))
	});
}
var list = (id, bounds, source, rowHeight, keyField) => node("List", id, bounds, {
	source,
	rowHeight,
	keyField,
	fields: [],
	scrollbarId: id + "ScrollBar"
});
function describe(model, ui, width, height, language) {
	const tr = (text) => translate(text, language), navigate = !model.busy && !pending(ui), notice = notices(model, ui, width, language, "Discard unsaved access changes?"), nodes = notice.nodes, rail = width >= 900, railWidth = rail ? language === "ru" ? 232 : 212 : 0, offset = rail ? railWidth + 12 : 0, contentWidth = width - offset, details = scopeDetails[ui.scope] || scopeDetails.project, selected = scopes.find((entry) => entry[0] === ui.scope) || scopes[1];
	const confirmation = nodes.find((item) => item.id === "adminDocumentConfirmation");
	if (confirmation) confirmation.children.forEach((item) => {
		if (item.id === "adminCancelSave") item.icon = "close";
		if (item.id === "adminConfirmSave") item.icon = ui.confirmation === "save" ? "save" : "undo";
	});
	let top = notice.top;
	if (rail) {
		const entries = [], groups = [
			["Groups and projects", [
				"effective",
				"defaults",
				"project",
				"builtin"
			]],
			["Agent access", ["agent_tool", "mcp_tool"]],
			["Interface", ["link", "gear_menu"]],
			["Data and workflow", [
				"search_type",
				"process",
				"tasks",
				"sobject",
				"sobject_column",
				"search_filter"
			]],
			["Advanced", ["technical"]]
		];
		let y = 8;
		groups.forEach(([caption, values]) => {
			entries.push(label("adminSecurityCategory_" + values[0], rect(12, y, railWidth - 40, 24), tr(caption), muted));
			y += 28;
			values.forEach((value) => {
				const entry = scopes.find((item) => item[0] === value), current = scopes.findIndex((item) => item[0] === ui.scope), action = (index) => ({
					type: "scope",
					value: scopes[(index + scopes.length) % scopes.length][0]
				});
				entries.push(node("Action", "adminSecurityTab_" + value, rect(8, y, railWidth - 32, 38), {
					text: tr(entry[1]),
					description: tr(scopeDetails[value][1]),
					selected: ui.scope === value,
					enabled: navigate,
					normalColor: "transparent",
					selectedColor: "selected",
					radius: 4,
					rail: ui.scope === value,
					keys: {
						ArrowDown: action(current + 1),
						ArrowUp: action(current - 1),
						Home: action(0),
						End: action(scopes.length - 1)
					},
					action: {
						type: "scope",
						value
					},
					children: [node("Icon", "adminSecurityTabIcon_" + value, rect(12, 9, 20, 20), {
						icon: scopeDetails[value][0],
						color: ui.scope === value ? "action" : "secondaryText"
					}), label("adminSecurityTabTitle_" + value, rect(42, 0, railWidth - 86, 38), tr(entry[1]), { fontRole: "secondary" })]
				}));
				y += 40;
			});
			y += 8;
		});
		nodes.push(node("Box", "adminSecurityNavigationPanel", rect(0, top, railWidth, height - top), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			radius: 8,
			children: [node("Scroll", "adminSecurityNavigation", rect(0, 0, railWidth, height - top), {
				children: entries,
				contentHeight: y,
				scrollbarId: "adminSecurityNavigationScrollBar"
			})]
		}));
	} else {
		nodes.push(node("Choice", "adminSecurityScope", rect(0, top, width, 38), {
			value: ui.scope,
			label: tr("Access rules"),
			options: scopes.map(([value, text]) => ({
				value,
				label: tr(text)
			})),
			enabled: navigate,
			action: { type: "scope" }
		}));
		top += 46;
	}
	const headerHeight = contentWidth < 520 ? 112 : 80;
	nodes.push(node("Box", "adminSecurityContext", rect(offset, top, contentWidth, headerHeight), {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		radius: 8,
		children: [
			node("Icon", "adminSecurityContextIcon", rect(14, 14, 24, 24), {
				icon: details[0],
				color: "action"
			}),
			label("adminSecurityContextTitle", rect(50, 10, contentWidth - 64, 26), tr(selected[1]), {
				fontRole: "section",
				weight: 600
			}),
			label("adminSecurityContextDescription", rect(50, 38, contentWidth - 64, headerHeight - 46), tr(details[1]), Object.assign({ wrap: true }, muted))
		]
	}));
	const bodyY = top + headerHeight + 12, bodyWidth = Math.max(1, contentWidth - 24), bodyHeight = Math.max(1, height - bodyY - 24);
	nodes.push(node("Box", "adminSecurityWorkspacePanel", rect(offset, bodyY, contentWidth, height - bodyY), {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		radius: 8,
		children: [node("Box", "adminSecurityWorkspace", rect(12, 12, bodyWidth, bodyHeight), { children: workspace(model, ui, bodyWidth, bodyHeight, language).nodes })]
	}));
	return { nodes };
}
function workspace(model, ui, width, height, language) {
	if (ui.scope === "effective") return workspace$1(model, ui, width, height, language);
	const tr = (text) => translate(text, language), edit = policy(model).editable && !pending(ui), navigate = !model.busy && !pending(ui), matrix = matrixScopes$1.indexOf(ui.scope) >= 0, nodes = [];
	let y = 0;
	if (!matrix) {
		nodes.push(node("Icon", "adminSecurityGroupIcon", rect(0, y + 9, 20, 20), {
			icon: "groups",
			color: "secondaryText"
		}), label("adminSecurityGroupCaption", rect(28, y, 64, 38), tr("Group"), muted), node("Choice", "adminSecurityAdvancedGroup", rect(98, y, width - 98, 38), {
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
	if (ui.scope === "agent_tool" || ui.scope === "mcp_tool") {
		const access = workspace$1(model, ui, width, height - y, language);
		return { nodes: nodes.concat(access.nodes.map((item) => Object.assign({}, item, { y: item.y + y }))) };
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
		const legendHeight = width < 600 ? 60 : 32, footer = (width < 560 ? 78 : 40) + legendHeight, gridHeight = Math.max(1, height - y - footer - 8);
		nodes.push(node("Grid", "adminSecurityMatrix", rect(0, y, width, gridHeight), {
			source: "matrix",
			labelWidth: Math.min(260, width * .36),
			headerHeight: 38,
			cellWidth: 156,
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
		const legendY = y + gridHeight + 4, legend = [
			[
				"Allowed",
				"check",
				"action"
			],
			[
				"Denied",
				"close",
				"secondaryText"
			],
			[
				"Inherited",
				"account-tree",
				"secondaryText"
			],
			[
				"Other rule",
				"lock",
				"secondaryText"
			]
		], legendColumns = width < 600 ? 2 : 4, legendWidth = width / legendColumns;
		legend.forEach(([text, icon, color], index) => {
			const x = index % legendColumns * legendWidth, ly = legendY + Math.floor(index / legendColumns) * 28;
			nodes.push(node("Icon", "adminSecurityLegendIcon_" + index, rect(x, ly + 5, 16, 16), {
				icon,
				color
			}));
			nodes.push(label("adminSecurityLegend_" + index, rect(x + 22, ly, legendWidth - 26, 26), tr(text), muted));
		});
		nodes.push(button("adminSecurityInherit", rect(0, y + gridHeight + legendHeight + 8, 168, 38), tr("Use inherited"), "undo", { type: "inherit" }, edit && !!ui.selectedCell && !!cell.explicit && !cell.custom));
		nodes.push(label("adminSecurityMatrixHelp", rect(width < 560 ? 0 : 180, y + gridHeight + legendHeight + (width < 560 ? 46 : 8), width < 560 ? width : width - 180, 34), tr("Changes apply to the draft. Save to server to publish them."), Object.assign({ wrap: true }, muted)));
	} else if (ui.scope === "defaults") groupSettings(nodes, model, ui, rect(0, y, width, height - y), language, edit);
	else if (ui.scope === "technical") technical(nodes, model, ui, rect(0, y, width, height - y), language, edit, navigate);
	else {
		const split = width >= 780, editorWidth = split ? Math.max(320, width * .36) : width, listWidth = split ? width - editorWidth - 12 : width;
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
			const count = width < 380 ? 1 : width < 620 ? 2 : 3, cellWidth = inner / count;
			levels.forEach(([value, text], index) => children.push(button("adminAccessLevel_" + value, rect(12 + index % count * cellWidth, y + Math.floor(index / count) * 38, cellWidth - 4, 34), tr(text), levelIcons[value], {
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
	const tr = (text) => translate(text, language), width = bounds.width, y = bounds.y, backWidth = ui.page === "group" ? 0 : 46;
	if (backWidth) nodes.push(button("adminSecurityBackToRules", rect(0, y, 38, 38), tr("Group defaults"), "chevron-left", {
		type: "page",
		value: "group"
	}, navigate, { iconOnly: true }));
	const options = [
		[
			"group",
			"Group defaults",
			"groups"
		],
		[
			"xml",
			"XML",
			"code"
		],
		[
			"rule",
			"Selected rule JSON",
			"code"
		],
		[
			"inherited",
			"Inherited rules",
			"account-tree"
		]
	].map(([value, text, icon]) => ({
		value,
		icon,
		label: tr(text),
		disabled: value === "rule" && model.selected < 0
	}));
	nodes.push(width < 880 ? node("Choice", "adminSecurityTechnicalPages", rect(backWidth, y, width - backWidth, 38), {
		value: ui.page,
		options: options.filter((option) => !option.disabled),
		label: tr("Advanced rules"),
		enabled: navigate,
		action: { type: "page" }
	}) : tabs("adminSecurityTechnicalPages", options, ui.page, rect(backWidth, y, width - backWidth, 38), navigate, "page"));
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
	groupSettings(nodes, model, ui, rect(0, top, width, remaining), language, edit);
}
function groupSettings(nodes, model, ui, bounds, language, edit) {
	const tr = (text) => translate(text, language), width = bounds.width, formWidth = Math.max(1, width - 16), columns = width >= 600 ? 2 : 1, fieldWidth = (formWidth - (columns - 1) * 12) / columns;
	const fields = [["accessLevel", "Access level"], ["project", "Project"]], form = [];
	fields.forEach(([field, text], index) => {
		const x = index % columns * (fieldWidth + 12), fy = Math.floor(index / columns) * 76;
		form.push(label("adminSecurityGroupLabel_" + field, rect(x, fy, fieldWidth, 22), tr(text)));
		form.push(node("Choice", "adminSecurityGroup_" + field, rect(x, fy + 28, fieldWidth, 38), {
			text: model.groupDocument[field] || "",
			value: model.groupDocument[field] || "",
			label: tr(text),
			options: field === "project" ? [{
				value: "",
				label: tr("All projects")
			}, ...(model.metadata.targets?.project || []).filter((target) => !target.all).map((target) => ({
				value: target.attributes.code,
				label: target.label
			}))] : (model.metadata.accessLevels || []).map((value) => ({
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
	const formHeight = Math.ceil(fields.length / columns) * 76, helpHeight = width >= 900 ? 48 : width >= 600 ? 64 : 112;
	form.push(label("adminSecurityInheritanceHelp", rect(0, formHeight + 4, formWidth, helpHeight), tr("This group inherits permissions from the selected groups. For the same rule key, the highest access wins; a deny does not cancel another grant."), Object.assign({ wrap: true }, muted)));
	const known = new Set(model.groups.map((group) => group.label)), other = (model.groupDocument.subGroups || "").split("|").filter((name) => name && !known.has(name));
	let contentHeight = formHeight + helpHeight + 12;
	if (other.length) {
		form.push(label("adminSecurityOtherInheritance", rect(0, contentHeight, formWidth, 48), tr("Other inherited groups: {groups}").replace("{groups}", other.join(", ")), { wrap: true }));
		contentHeight += 56;
	}
	const headerHeight = Math.min(contentHeight, bounds.height * .58);
	nodes.push(node("Scroll", "adminSecurityDefaults", rect(0, bounds.y, width, headerHeight), {
		children: form,
		contentHeight,
		scrollbarId: "adminSecurityDefaultsScrollBar"
	}));
	const listY = bounds.y + headerHeight + 8;
	nodes.push(label("adminSecurityInheritanceCaption", rect(0, listY, width, 24), tr(ui.scope === "technical" ? "Access rules" : "Inherit permissions from")));
	nodes.push(list(ui.scope === "technical" ? "adminSecurityAllRules" : "adminSecurityInheritanceList", rect(0, listY + 32, width, Math.max(1, bounds.y + bounds.height - listY - 32)), ui.scope === "technical" ? "allRules" : "inheritance", ui.scope === "technical" ? 62 : 42, ui.scope === "technical" ? "ruleIndex" : "identity"));
}
function row(listNode, record, model, ui, language) {
	if (listNode.source === "effective" || listNode.source === "agentTools") return row$1(listNode, record, model, ui, language);
	const tr = (text) => translate(text, language), width = Math.max(1, listNode.width - 16), height = listNode.rowHeight - 4, edit = policy(model).editable && !pending(ui), navigate = !model.busy && !pending(ui), nodes = [];
	if (listNode.source === "inheritance") return { nodes: [node("CheckBox", "adminSecurityInheritance_" + record.identity, rect(0, 0, width, height), {
		text: record.label,
		description: record.cycle ? tr("This inheritance would create a cycle.") : tr("Inherit permissions from"),
		checked: record.checked,
		enabled: edit && (!record.cycle || record.checked),
		indicatorX: 8,
		action: {
			type: "inheritGroup",
			identity: record.identity
		},
		children: [label("adminSecurityInheritanceName_" + record.identity, rect(40, 0, width - 48, height), record.label)]
	})] };
	if (listNode.source === "targets") return { nodes: [node("Action", "adminAccessTarget_" + record.index, rect(0, 0, width, height), {
		text: record.label,
		enabled: edit,
		action: {
			type: "target",
			attributes: record.attributes
		},
		children: [label("adminAccessTargetTitle_" + record.index, rect(12, 4, width - 24, 22), record.label), label("adminAccessTargetDetail_" + record.index, rect(12, 26, width - 24, 18), detail(record.attributes), muted)]
	})] };
	const index = record.ruleIndex, all = listNode.source === "allRules", quick = !all && ui.scope !== "search_filter", small = width < 540, levelWidth = 36;
	const textWidth = quick && !small ? width - 144 - 42 : width - 44;
	nodes.push(node("Action", "adminAccessRule_" + index, rect(0, 0, width, height), {
		text: title(record, model, language),
		selected: model.selected === index,
		rail: true,
		normalColor: "transparent",
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
	].forEach((value, col) => nodes.push(button("adminPermission_" + index + "_" + value, rect(small ? 8 + col * levelWidth : textWidth + col * levelWidth, small ? 46 : 18, 32, 32), tr(levels.find((level) => level[0] === value)[1]), levelIcons[value], {
		type: "ruleAccess",
		index,
		value
	}, edit, {
		radio: true,
		selected: record.access === value,
		iconOnly: true,
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
	const access = record.custom ? levels.find((entry) => entry[0] === record.access) : null, caption = access ? tr(access[1]) : tr(record.checked ? "Allowed" : "Denied");
	const children = [node("Box", "adminSecurityCellDivider_" + row + "_" + column, rect(0, grid.rowHeight - 2, grid.cellWidth - 1, 1), { background: "outlineVariant" }), label("adminSecurityAccess_" + row + "_" + column, rect(38, 0, grid.cellWidth - 66, grid.rowHeight - 1), caption, {
		fontRole: "caption",
		color: record.checked ? "primaryText" : "secondaryText"
	})];
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
		indicatorX: 10,
		radius: 0,
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
			pendingGroup: "",
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
				canWrite: this.canWrite && !!this.groupDocument,
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
				groupDocuments: this.document?.groups || {},
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
		async inspectUser(login) {
			if (this.dirty || this.busy || this.uncertain || !this.context) return;
			const request = ++this.request, context = { ...this.context };
			this.busy = true;
			this.error = "";
			try {
				const result = await securityRules("effective", context.ticket, context.project, { login });
				if (request !== this.request || this.ticket !== context.ticket || this.project !== context.project) return;
				this.accept(result);
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		setToolPolicy({ scope, mode, names }) {
			if (!this.editable || !this.groupDocument || !["agent_tool", "mcp_tool"].includes(scope) || ![
				"inherit",
				"selected",
				"all"
			].includes(mode)) return;
			const catalog = this.metadata[scope === "mcp_tool" ? "mcpTools" : "agentTools"] || [];
			if (names.some((name) => !catalog.some((tool) => tool.name === name))) return;
			const root = parseRules(this.groupDocument.xml);
			for (const rule of [...root.children]) if ((rule.getAttribute("group") || rule.getAttribute("category") || rule.getAttribute("type")) === scope) rule.remove();
			let xml = new XMLSerializer().serializeToString(root);
			if (mode !== "inherit") {
				xml = changeRule(xml, -1, {
					group: scope,
					key: "*",
					access: mode === "all" ? "allow" : "deny"
				});
				if (mode === "selected") for (const name of new Set(names)) xml = changeRule(xml, -1, {
					group: scope,
					key: name,
					access: "allow"
				});
			}
			this.groupDocument.xml = xml;
			this.selected = -1;
			this.syncText();
			this.error = this.message = "";
		},
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
				case "effectiveUser":
					await this.inspectUser(command.login);
					break;
				case "toolPolicy":
					this.setToolPolicy(command);
					break;
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
			if (this.pendingGroup) {
				this.group = this.pendingGroup;
				this.pendingGroup = "";
				if (!this.groups.some((group) => group.identity === this.group)) {
					this.group = "";
					this.selectGroup("");
					throw new Error("Group is no longer available");
				}
			}
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
		focusGroup(code) {
			if (this.dirty || this.uncertain) throw new Error("Apply or discard unsaved changes first");
			if (this.document?.groups[code]) this.selectGroup(code);
			else if (this.document && !this.busy) throw new Error("Group is no longer available");
			else {
				this.pendingGroup = code;
				this.group = code;
			}
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
import { C as inject, E as nextTick, G as withCtx, H as watch, J as markRaw, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment } from "./vue.js";
import { D as spacing, a as _sfc_main$2, o as t, s as appearance, t as _sfc_main$3, y as cssRoles } from "./AppButton.js";
import { A as rpc, It as randomUuid, ut as notify } from "./index.js";
import { G as button, H as observeFrameSizes, J as muted, K as label, P as _sfc_main$4, X as rect, Y as node, t as _sfc_main$5, w as translate } from "./FrameView.js";
import { $ as _sfc_main$6 } from "./ConfiguredView.js";
import { t as _sfc_main$7 } from "./AppDialog.js";
import { t as _sfc_main$8 } from "./MarkdownText.js";
import { t as listAction } from "./tree.ui.js";
import { g as describe$3 } from "./App.js";
import { n as current, r as status$1, t as controls } from "./executor.ui.js";
//#region ../src/tactic_stream/shared_ui/features/scripts/history.ui.mjs
function initial$1() {
	return {
		visible: null,
		mobile: false,
		width: 280,
		query: "",
		project: "",
		searchOpen: false,
		grouping: "time",
		archived: false,
		collapsed: {},
		edit: null
	};
}
function layout(model, width) {
	const small = width < 940;
	const visible = small ? !!model.history.mobile : model.history.visible ?? true;
	const panel = visible ? small ? width : Math.min(Math.max(220, model.history.width), width - 500) : 0;
	return {
		small,
		visible,
		panel,
		mainX: small ? 0 : panel,
		mainWidth: small ? width : width - panel
	};
}
function change(model, action, small = false) {
	const history = model.history;
	if (action.type === "historyProject") return Object.assign({}, history, {
		project: action.value,
		edit: null
	});
	if (action.type === "historyOptions") return Object.assign({}, history, { edit: { kind: "options" } });
	if (action.type === "historySearch") return Object.assign({}, history, {
		searchOpen: !history.searchOpen,
		query: history.searchOpen ? "" : history.query
	});
	if (action.type === "historyToggle") return Object.assign({}, history, small ? { mobile: !history.mobile } : { visible: !(history.visible ?? action.value) });
	if (action.type === "historyWidth") return Object.assign({}, history, { width: action.value });
	if (action.type === "historyQuery") return Object.assign({}, history, { query: action.value });
	if (action.type === "historyGrouping") return Object.assign({}, history, {
		grouping: action.value,
		edit: null
	});
	if (action.type === "historyArchived") return Object.assign({}, history, {
		archived: !!action.value,
		edit: null
	});
	if (action.type === "historyCollapse") return Object.assign({}, history, { collapsed: Object.assign({}, history.collapsed, { [action.value]: !history.collapsed[action.value] }) });
	if (action.type === "historyCancel") return Object.assign({}, history, { edit: null });
	if (action.type === "historyRemoveConfirm") return Object.assign({}, history, { edit: Object.assign({}, history.edit, { confirm: true }) });
	if (action.type === "historyGroupEdit") {
		const project = action.value?.project || history.project || model.context.project;
		const identity = typeof action.value === "object" ? action.value.id : action.value;
		const group = (model.groups || []).find((item) => item.id === identity && (item.project || project) === project);
		return Object.assign({}, history, {
			visible: true,
			mobile: small,
			edit: {
				kind: "group",
				id: group?.id || "",
				name: group?.name || "",
				project,
				revision: model.group_revisions?.[project] || model.groups_revision
			}
		});
	}
	if (action.type === "historyEdit" && action.value) {
		const row = selection(model, action.value);
		if (!row) return null;
		return Object.assign({}, history, {
			visible: true,
			mobile: small,
			edit: {
				kind: "chat",
				id: row.request_id,
				project: row.project || model.context.project,
				title: row.default_title ? "" : row.title,
				group: row.group || "",
				pinned: !!row.pinned,
				archived: !!row.archived,
				revision: row.library_revision,
				status: row.status
			}
		});
	}
	const fields = {
		historyTitle: "title",
		historyFolder: "group",
		historyPinned: "pinned",
		historyName: "name"
	};
	if (fields[action.type] && history.edit) return Object.assign({}, history, { edit: Object.assign({}, history.edit, { [fields[action.type]]: action.value }) });
	return null;
}
function key(row, project = "") {
	return row.key || (row.project || project) + ":" + row.request_id;
}
function selection(model, value) {
	const identity = typeof value === "object" ? value.request_id : value;
	const project = typeof value === "object" ? value.project : null;
	const candidates = model.requests.concat(model.request?.library_summary ? [model.request.library_summary] : []).filter((row) => row.request_id === identity && (!project || row.project === project));
	return candidates.find((row) => (row.project || model.context.project) === (project || model.context.project)) || candidates[0];
}
function projectContext(context, project) {
	return context.project === project ? context : {
		client: context.client,
		project,
		page: "",
		title: "",
		search_type: "",
		view: "",
		search_keys: []
	};
}
function draft(model) {
	return {
		prompt: model.prompt,
		attachments: model.attachments.slice(),
		model: model.model,
		provider: model.provider,
		effort: model.effort,
		allowChanges: model.allowChanges,
		allowWeb: model.allowWeb
	};
}
function restored(value) {
	return Object.assign({
		prompt: "",
		attachments: [],
		model: null,
		provider: null,
		effort: null,
		allowChanges: false,
		allowWeb: false
	}, value || {});
}
function merge(previous, current) {
	const records = new Map(previous.map((row) => [key(row), row]));
	for (const row of current) records.set(key(row), row);
	return Array.from(records.values());
}
function rows(model, language, now = Date.now()) {
	const tr = (text) => translate(text, language), history = model.history;
	const folders = new Map((model.groups || []).map((group) => [(group.project || model.context.project) + ":" + group.id, group]));
	const groups = /* @__PURE__ */ new Map();
	function add(key, title, row, folder = "", project = "") {
		if (!groups.has(key)) groups.set(key, {
			key,
			title,
			folder,
			project,
			records: []
		});
		if (row) groups.get(key).records.push(row);
	}
	const midnight = new Date(now);
	midnight.setHours(0, 0, 0, 0);
	const today = midnight.getTime();
	const sorted = model.requests.slice().sort((a, b) => (b.activity || 0) - (a.activity || 0) || b.request_id.localeCompare(a.request_id));
	const topPinned = (row) => row.pinned && (history.grouping !== "group" || !row.group);
	for (const row of sorted.filter(topPinned)) add("pinned", tr("Pinned conversations"), row);
	if (history.grouping === "group") {
		for (const group of model.groups || []) if (!history.project || !group.project || group.project === history.project) add("folder:" + (group.project || model.context.project) + ":" + group.id, !history.project && group.project_title ? group.project_title + " · " + group.name : group.name, null, group.id, group.project || model.context.project);
	}
	for (const row of sorted.filter((row) => !topPinned(row))) if (history.grouping === "type") add("type:" + row.search_type, row.type_title || row.search_type || tr("No Search Type"), row);
	else if (history.grouping === "group") add("folder:" + (row.project || model.context.project) + ":" + (row.group || ""), folders.get((row.project || model.context.project) + ":" + row.group)?.name || tr("Ungrouped"), row, row.group || "", row.project || model.context.project);
	else {
		const date = /* @__PURE__ */ new Date((row.activity || 0) * 1e3);
		date.setHours(0, 0, 0, 0);
		const days = Math.round((today - date.getTime()) / 864e5);
		const key = days < 1 ? "Today" : days === 1 ? "Yesterday" : days < 7 ? "Previous 7 days" : days < 30 ? "Previous 30 days" : "Older conversations";
		add("time:" + key, tr(key), row);
	}
	const result = [];
	for (const group of groups.values()) {
		if (history.grouping === "group") group.records.sort((a, b) => Number(b.pinned) - Number(a.pinned));
		result.push(Object.assign({}, group, {
			kind: "heading",
			count: group.records.length
		}));
		if (!group.folder || !history.collapsed[group.key]) for (const record of group.records) result.push(Object.assign({}, record, {
			key: key(record, model.context.project),
			kind: "chat"
		}));
	}
	return result;
}
function row(model, record, width, language) {
	const tr = (text) => translate(text, language), idle = !model.busy && !model.pending && !model.uploading;
	if (record.kind === "heading") {
		const folder = !!record.folder;
		const nodes = [folder ? listAction("historyGroup_" + record.key, rect(8, 0, width - 16, 32), record.title, model.history.collapsed[record.key] ? "chevron-right" : "chevron-down", {
			type: "historyCollapse",
			value: record.key
		}, true, {
			fontRole: "secondary",
			color: "secondaryText",
			weight: 500,
			endInset: 28
		}) : label("historyGroup_" + record.key, rect(12, 4, width - 24, 24), record.title, Object.assign({}, muted, {
			fontRole: "secondary",
			role: "heading",
			level: 2
		}))];
		if (folder) nodes.push(listAction("historyFolderEdit_" + record.folder, rect(width - 36, 2, 28, 28), tr("Edit conversation folder"), "more-horiz", {
			type: "historyGroupEdit",
			value: {
				id: record.folder,
				project: record.project
			}
		}, idle, {
			iconOnly: true,
			revealOnRowInteraction: !model.history.mobile
		}));
		return { nodes };
	}
	const working = [
		"queued",
		"running",
		"cancelling"
	].includes(record.status);
	const title = record.default_title ? tr(record.title) : record.title;
	const allProjects = !model.history.project;
	const value = {
		request_id: record.request_id,
		project: record.project || model.context.project
	};
	const item = listAction("agentHistoryOpen_" + key(record, model.context.project), rect(8, 0, width - 16, allProjects ? 40 : 32), title, working ? "sync" : "", {
		type: "select",
		value
	}, idle, {
		selected: model.selected === record.request_id && value.project === model.context.project,
		toolTip: title,
		endInset: 28
	});
	if (allProjects) {
		const text = item.children.find((child) => child.kind === "Label");
		text.height = 20;
		item.children.push(label("agentHistoryProject_" + key(record, model.context.project), rect(text.x, 20, text.width, 18), record.project_title || record.project || model.context.project, {
			fontRole: "caption",
			color: "secondaryText"
		}));
	}
	return { nodes: [item, listAction("agentHistoryEdit_" + key(record, model.context.project), rect(width - 36, allProjects ? 6 : 2, 28, 28), tr("Conversation settings"), "more-horiz", {
		type: "historyEdit",
		value
	}, idle, {
		iconOnly: true,
		revealOnRowInteraction: !model.history.mobile
	})] };
}
function describe$2(model, width, height, language, small) {
	const tr = (text) => translate(text, language), edit = model.history.edit;
	const idle = !model.busy && !model.pending && !model.uploading;
	const heading = edit ? edit.kind === "options" ? "Conversation view" : edit.kind === "group" ? "Conversation folder" : "Conversation settings" : model.history.archived ? "Archived conversations" : "Conversations";
	const nodes = [
		node("Box", "agentHistorySurface", rect(0, 0, width, height), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			borderWidth: 1,
			radius: 0
		}),
		label("agentHistoryHeading", rect(16, 8, Math.max(20, width - (edit ? 96 : 128)), 32), tr(heading), { weight: 600 }),
		listAction("agentHistoryClose", rect(width - 40, 8, 32, 32), tr("Hide conversations"), "chevron-left", {
			type: "historyToggle",
			value: true
		}, true, { iconOnly: true })
	];
	if (edit && edit.kind === "options") {
		nodes.push(listAction("agentHistoryBack", rect(width - 76, 8, 32, 32), tr("Back to conversations"), "arrow-back", { type: "historyCancel" }, true, { iconOnly: true }));
		const fields = [
			{
				kind: "Choice",
				field: "grouping",
				title: "Group conversations",
				action: { type: "historyGrouping" },
				options: [
					{
						value: "time",
						label: tr("By time")
					},
					{
						value: "type",
						label: tr("By Search Type")
					},
					{
						value: "group",
						label: tr("By folder")
					}
				]
			},
			{
				kind: "Switch",
				field: "archived",
				title: "Archived conversations",
				action: { type: "historyArchived" }
			},
			{
				kind: "Button",
				id: "agentHistoryNewGroup",
				title: "New conversation folder",
				icon: "create-new-folder",
				action: {
					type: "historyGroupEdit",
					value: ""
				}
			}
		];
		nodes.push(node("Box", "agentHistoryOptionsForm", rect(0, 48, width, height - 60), { children: describe$3({
			fields,
			values: model.history,
			busy: !idle
		}, width, height - 60, language).nodes }));
		return { nodes };
	}
	if (edit) {
		const fields = edit.kind === "group" ? [{
			kind: "Field",
			field: "name",
			title: "Folder name",
			action: { type: "historyName" },
			props: { maxLength: 120 }
		}] : [
			{
				kind: "Field",
				field: "title",
				title: "Conversation name",
				action: { type: "historyTitle" },
				props: { maxLength: 160 }
			},
			{
				kind: "Choice",
				field: "group",
				title: "Conversation folder",
				action: { type: "historyFolder" },
				options: [{
					value: "",
					label: tr("Ungrouped")
				}].concat((model.groups || []).filter((group) => !group.project || group.project === edit.project).map((group) => ({
					value: group.id,
					label: group.name,
					dataLabel: true
				})))
			},
			{
				kind: "Switch",
				field: "pinned",
				title: "Pin conversation",
				action: { type: "historyPinned" }
			}
		];
		nodes.push(node("Box", "agentHistoryEditor", rect(0, 48, width, Math.max(60, height - 176)), { children: describe$3({
			fields,
			values: edit,
			busy: !idle
		}, width, Math.max(60, height - 176), language).nodes }));
		if (edit.confirm) nodes.push(label("agentHistoryRemoveNotice", rect(16, height - 128, width - 32, 64), tr("Remove this folder? Its conversations will move to Ungrouped."), Object.assign({}, muted, { wrap: true })));
		else if (edit.id) nodes.push(button("agentHistoryArchive", rect(12, height - 120, width - 24, 32), tr(edit.kind === "group" ? "Remove folder" : edit.archived ? "Restore conversation" : "Archive conversation"), edit.kind === "group" ? "delete" : edit.archived ? "undo" : "archive", { type: edit.kind === "group" ? "historyRemoveConfirm" : "historyArchive" }, idle && (edit.kind === "group" || ![
			"queued",
			"running",
			"cancelling"
		].includes(edit.status))));
		if (edit.kind === "chat" && model.selected && (edit.id !== model.selected || edit.project !== model.context.project)) nodes.push(button("agentHistoryUseContext", rect(12, height - 84, width - 24, 28), tr("Use in current conversation"), "link", { type: "historyUseContext" }, idle && ![
			"queued",
			"running",
			"cancelling",
			"draft"
		].includes(edit.status) && ![
			"queued",
			"running",
			"cancelling"
		].includes(model.request?.status)));
		nodes.push(button("agentHistorySave", rect(12, height - 48, (width - 32) / 2, 32), tr(edit.confirm ? "Remove folder" : "Save"), edit.confirm ? "delete" : "save", { type: edit.confirm ? "historyGroupRemove" : "historySave" }, idle && (edit.kind !== "group" || !!edit.name.trim()), {
			highlighted: true,
			destructive: !!edit.confirm
		}), button("agentHistoryCancel", rect(20 + (width - 32) / 2, height - 48, (width - 32) / 2, 32), tr("Cancel"), "close", { type: "historyCancel" }, idle));
		return { nodes };
	}
	const searching = model.history.searchOpen || !!model.history.query;
	const warning = (model.unavailable_projects || []).length ? 36 : 0;
	const listTop = (searching ? 176 : 132) + warning;
	const footer = model.next_offset == null ? 0 : 40;
	nodes.push(listAction("agentHistorySearchToggle", rect(width - 112, 8, 32, 32), tr("Search conversations"), "search", { type: "historySearch" }, true, { iconOnly: true }), listAction("agentHistoryOptions", rect(width - 76, 8, 32, 32), tr("Conversation view"), "more-horiz", { type: "historyOptions" }, idle, { iconOnly: true }), listAction("agentHistoryNew", rect(12, 48, width - 24, 32), tr("New conversation"), "add", { type: "historyNew" }, idle), node("Choice", "agentHistoryProject", rect(12, 88, width - 24, 32), {
		label: tr("Conversation project"),
		value: model.history.project || "",
		enabled: idle,
		options: [{
			value: "",
			label: tr("All projects")
		}].concat((model.projects || []).map((project) => ({
			value: project.code,
			label: project.title,
			dataLabel: true,
			enabled: project.available !== false
		}))),
		action: { type: "historyProject" }
	}), node("List", "agentHistoryList", rect(0, listTop, width, Math.max(36, height - listTop - 12 - footer)), {
		source: "agentHistoryRows",
		rowHeight: model.history.project ? 36 : 44,
		keyField: "key",
		fields: [
			"key",
			"kind",
			"title",
			"default_title",
			"folder",
			"request_id",
			"status",
			"pinned",
			"project",
			"project_title"
		],
		role: "list",
		label: tr("Conversations")
	}));
	if (searching) nodes.push(node("Field", "agentHistorySearch", rect(12, 132, width - 24, 32), {
		label: tr("Search conversations"),
		placeholder: tr("Search conversations"),
		text: model.history.query,
		maxLength: 200,
		action: { type: "historyQuery" }
	}));
	if (warning) nodes.push(label("agentHistoryUnavailable", rect(12, listTop - warning, width - 24, 32), tr("Some project histories are unavailable"), Object.assign({}, muted, {
		wrap: true,
		toolTip: model.unavailable_projects.join(", ")
	})));
	if (footer) nodes.push(listAction("agentHistoryMore", rect(12, height - 40, width - 24, 28), tr("Load more conversations"), "expand-more", { type: "historyMore" }, idle));
	if (!model.requests.length) nodes.push(label("agentHistoryEmpty", rect(16, listTop + 12, width - 32, 52), tr(model.history.query ? "No conversations found" : "No conversations yet"), Object.assign({}, muted, { wrap: true })));
	if (!small) nodes.push(node("Splitter", "agentHistorySplitter", rect(width - 4, 0, 4, height), {
		text: tr("Conversations panel width"),
		value: model.history.width,
		min: 220,
		max: 420,
		action: { type: "historyWidth" }
	}));
	return { nodes };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/scripts/rules.ui.mjs
function describe$1(model, width, height, language) {
	const tr = (text) => translate(text, language), rules = model.projectRules, inner = Math.max(0, width - 24), idle = !model.busy, helpHeight = width < 520 ? 84 : width < 760 ? 64 : 48, contentY = 68 + helpHeight, footer = height - 52;
	return { nodes: [
		node("Box", "agentRulesHeader", rect(0, 0, width, 52), { background: "surfaceContainerLow" }),
		label("agentRulesTitle", rect(12, 6, inner, 22), tr("Project chat rules"), { weight: 600 }),
		label("agentRulesProject", rect(12, 28, inner, 18), model.context.project, {
			color: "secondaryText",
			fontRole: "caption"
		}),
		label("agentRulesHelp", rect(12, 62, inner, helpHeight), tr("Shared by all chats in this project. Changes apply on the next send; the current turn keeps its captured rules."), {
			wrap: true,
			color: "secondaryText"
		}),
		node("Area", "agentRulesText", rect(12, contentY, inner, Math.max(40, footer - contentY - 40)), {
			text: rules.text,
			maxLength: 16e3,
			placeholder: tr("Describe naming, preview destinations and comment preferences."),
			enabled: idle && !!rules.revision,
			action: { type: "rulesText" }
		}),
		label("agentRulesError", rect(12, footer - 36, inner, 32), tr(model.error || ""), {
			wrap: true,
			color: "error"
		}),
		node("Box", "agentRulesFooter", rect(0, footer, width, 52), { background: "surfaceContainerLow" }),
		button("agentRulesCancel", rect(12, footer + 10, Math.min(128, (inner - 8) / 2), 32), tr("Cancel"), "close", { type: "rulesCancel" }, idle),
		button("agentRulesSave", rect(width - 12 - Math.min(164, (inner - 8) / 2), footer + 10, Math.min(164, (inner - 8) / 2), 32), tr("Save project rules"), "save", { type: "rulesSave" }, idle && !!rules.revision && rules.text !== rules.original && rules.text.length <= 16e3)
	] };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs
var metrics = {
	inset: spacing.content,
	bubblePadding: spacing.content,
	messageGap: spacing.section,
	attachmentHeight: 28
};
function initial(context = {}) {
	return {
		context,
		prompt: "",
		allowChanges: false,
		allowWeb: false,
		hosts: [],
		executor: {},
		executorTarget: null,
		requests: [],
		selected: "",
		request: {},
		busy: false,
		error: "",
		refreshError: "",
		pending: null,
		attachments: [],
		uploading: false,
		model: null,
		provider: null,
		effort: null,
		contextExpanded: false,
		history: initial$1(),
		groups: [],
		groups_revision: "",
		group_revisions: {},
		projects: [],
		unavailable_projects: [],
		total: 0,
		next_offset: null,
		drafts: {}
	};
}
function active(model) {
	return [
		"queued",
		"running",
		"cancelling"
	].includes(model.request?.status);
}
function started(model) {
	return !!model.selected && model.request?.status !== "draft";
}
function host(model) {
	const allowed = model.hosts.filter((item) => !(started(model) ? model.request?.document?.allow_changes : model.allowChanges) || item.capabilities.changes);
	return allowed.find((item) => item.host_id === model.request?.host_id) || allowed[0];
}
function canSend(model) {
	const connected = host(model);
	return !model.busy && ![
		"preparing",
		"starting",
		"stopping",
		"failed"
	].includes(model.executor?.state) && !model.uploading && !model.request?.library?.archived && !!model.context?.project && (!!model.prompt.trim() || !!model.attachments.length) && model.prompt.length <= 12e3 && !!connected && (!model.selected || model.request?.request_id === model.selected) && (Array.isArray(connected?.capabilities.providers) ? availableModels(model).length > 0 : provider(model) === "codex" || availableModels(model).length > 0) && (provider(model) === "codex" || !!selectedModel(model)) && (!model.allowChanges || connected.capabilities.changes) && (!model.selected || model.request.status !== "cancelling") && (!active(model) || connected.capabilities.steering === true);
}
function provider(model) {
	return model.provider ?? (started(model) ? model.request.provider || "codex" : host(model)?.capabilities.default_provider || "codex");
}
function availableModels(model) {
	return (host(model)?.capabilities.models || []).filter((item) => (item.provider || "codex") === provider(model));
}
function selectedModel(model) {
	const id = model.model ?? model.request?.model ?? "";
	return availableModels(model).find((item) => id ? item.id === id : item.is_default);
}
function messages(model) {
	const current = model.request || {};
	if (current.status === "draft") return [];
	return (current.messages?.length ? current.messages : current.document ? [{
		id: current.request_id,
		role: "user",
		text: current.document.prompt,
		attachments: []
	}, ...current.answer ? [{
		id: "answer",
		role: "assistant",
		text: current.answer,
		attachments: []
	}] : []] : []).concat(current.output && active(model) ? [{
		id: "progress",
		role: "assistant",
		text: current.output,
		attachments: []
	}] : []);
}
function activity(model, language) {
	const names = {
		agent_context: "Reading conversation context",
		agent_conversations: "Search conversations",
		agent_conversation_read: "Reading conversation context",
		agent_capabilities: "Checking available tools",
		reference_read: "Reading TACTIC documentation",
		agent_selection: "Reading selected objects",
		ts_records: "Reading project objects",
		ts_type_read: "Reading object definition",
		ts_schema_read: "Reading project relationships",
		ts_records_create: "Creating project objects",
		ts_relations: "Reading object relationships",
		ts_instance_link: "Linking project objects",
		ts_snapshots: "Reading file history",
		ts_workflow_read: "Reading workflows",
		ts_workflow_apply: "Saving workflow",
		ts_attachment_checkin: "Checking in attached files",
		ts_edit_operation: "Checking saved changes",
		ts_naming_read: "Reading naming rules",
		ts_tasks_read: "Reading tasks",
		ts_tasks_prepare: "Preparing task changes",
		ts_tasks_save: "Saving tasks",
		ts_task_status_set: "Updating task statuses",
		ts_naming_preview: "Checking file naming",
		agent_attachment_image: "Viewing attached image",
		agent_web_download: "Downloading reference file",
		webSearch: "Searching the web"
	};
	const events = model.request?.events || [];
	return events.slice(events.lastIndexOf("External agent started") + 1).map((event) => {
		const match = event.match(/^([a-zA-Z_]+): (inProgress|completed|failed)$/);
		if (!match) return event;
		return translate(names[match[1]] || match[1], language) + " · " + translate({
			inProgress: "Working",
			completed: "Done",
			failed: "Failed"
		}[match[2]], language);
	});
}
function safeMarkdown(text) {
	return String(text || "").replace(/<[^>]*>/g, (value) => value.replace(/</g, "&lt;").replace(/>/g, "&gt;")).replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/!\[/g, "[");
}
function messageGeometry(width, role, bodyHeight, attachments) {
	const inner = Math.min(800, Math.max(0, width - 32)), bubbleWidth = Math.min(role === "user" ? 640 : 800, inner);
	const padding = role === "user" ? metrics.bubblePadding : 0;
	return {
		x: (width - inner) / 2 + (role === "user" ? inner - bubbleWidth : 0),
		width: bubbleWidth,
		padding,
		height: padding * 2 + Math.max(20, bodyHeight) + (Array.isArray(attachments) ? attachments.reduce((height, file) => height + attachmentHeight(file), 0) : attachments * metrics.attachmentHeight)
	};
}
function attachmentHeight(file) {
	return /^image\/(png|jpeg|webp|gif)$/.test(file.media_type || "") ? 172 : metrics.attachmentHeight;
}
function contextItems(context, language) {
	const tr = (text) => translate(text, language);
	return [
		{
			value: context.project || "",
			icon: "folder"
		},
		{
			value: context.title || context.page || "",
			icon: "table"
		},
		{
			value: context.search_type || "",
			icon: "database"
		},
		{
			value: tr("Selected objects") + ": " + (context.search_keys || []).length,
			icon: "check"
		}
	].filter((item) => item.value).map((item) => Object.assign({}, item, { width: Math.min(220, Math.max(80, item.value.length * 7 + 40)) }));
}
function status(model, language) {
	const tr = (text) => translate(text, language), current$1 = model.request || {}, executor = current(model);
	if (model.refreshError || model.error || executor.error || current$1.error) return {
		text: tr(model.refreshError || model.error || executor.error || current$1.error),
		color: "error",
		icon: "error"
	};
	if (current$1.library?.archived) return {
		text: tr("Archived conversation — restore it to continue"),
		color: "secondaryText",
		icon: "archive"
	};
	if (current$1.status === "completed") return current$1.outcome === "needs_input" ? {
		text: tr("Waiting for your reply"),
		color: "action",
		icon: "help"
	} : current$1.outcome === "blocked" ? {
		text: tr("Task blocked — see the answer"),
		color: "error",
		icon: "warning"
	} : {
		text: tr(current$1.outcome === "completed" ? "Task completed" : "Agent finished — review the answer"),
		color: "green",
		icon: "check"
	};
	const texts = {
		queued: "Request queued",
		running: "Agent working",
		cancelling: "Request cancelling",
		cancelled: "Request cancelled",
		failed: "Request failed",
		interrupted: "Request interrupted"
	};
	if (!texts[current$1.status] && executor.state === "connected" && Array.isArray(host(model)?.capabilities.providers) && !availableModels(model).length) return {
		text: tr("No available models. Check AI providers."),
		color: "error",
		icon: "warning"
	};
	return {
		text: tr(texts[current$1.status] || (executor.state || executor.error ? status$1(executor, language) : model.hosts.length ? "External agent connected" : "External agent is offline")),
		color: "secondaryText",
		icon: active(model) ? "sync" : "chat"
	};
}
function permissionActions(model) {
	const current = model.request || {}, frozen = started(model), enabled = !model.busy && !model.pending && !frozen;
	return [
		{
			title: "Allow requested changes",
			command: "changes",
			icon: "edit",
			role: "menuitemcheckbox",
			checked: !!(frozen ? current.document?.allow_changes : model.allowChanges),
			enabled
		},
		{
			title: "Allow internet access",
			command: "web",
			icon: "network-check",
			role: "menuitemcheckbox",
			checked: !!(frozen ? current.document?.allow_web : model.allowWeb),
			enabled: enabled && !!host(model)?.capabilities.web_search
		},
		{ separator: true },
		{
			title: "Project chat rules",
			command: "rules",
			icon: "edit",
			enabled: !model.busy && !model.pending && !!model.context?.project
		},
		{
			title: "MCP connections",
			command: "mcp",
			icon: "link",
			enabled: !model.busy
		},
		{
			title: "AI providers",
			command: "providers",
			icon: "settings",
			enabled: !model.busy
		}
	];
}
function describeChat(model, width, height, language, sidebarVisible) {
	const tr = (text) => translate(text, language), current = model.request || {}, context = current.document?.context || model.context || {};
	const inset = metrics.inset, inner = Math.max(0, width - inset * 2);
	const providers = host(model)?.capabilities.providers || [], narrow = width < (providers.length ? 680 : 640), providerRow = narrow && providers.length ? 40 : 0;
	const composerWidth = Math.min(880, inner), composerX = (width - composerWidth) / 2;
	const contextHeight = model.contextExpanded ? 122 : 38;
	const composerHeight = 128 + contextHeight + (model.attachments.length ? 42 : 0) + (narrow ? 40 : 0) + providerRow;
	const composerTop = Math.max(180, height - composerHeight - 12), modelWidth = narrow ? Math.min(200, Math.max(80, (composerWidth - 32) / 2)) : 200;
	const state = status(model, language), working = active(model), sendVisible = !working || !!model.prompt.trim() || !!model.attachments.length;
	const conversation = model.requests.find((row) => row.request_id === model.selected && (!row.project || row.project === model.context.project)) || current.library_summary;
	const sources = current.related_conversations || [];
	const transcriptTop = 94 + (current.undo_operation ? 32 : 0) + (sources.length ? 26 : 0);
	const nodes = [
		...controls(model, width, 52, language, !model.busy),
		button("agentRequestHistoryToggle", rect(inset, 10, 32, 32), tr(sidebarVisible ? "Hide conversations" : "Show conversations"), "history", {
			type: "historyToggle",
			value: sidebarVisible
		}, true, { iconOnly: true }),
		label("agentRequestTitle", rect(56, 10, Math.max(20, width - 200), 32), conversation?.title ? conversation.default_title ? tr(conversation.title) : conversation.title : tr("New conversation"), { weight: 600 }),
		button("agentRequestRename", rect(width - inset - 112, 10, 32, 32), tr("Conversation settings"), "edit", {
			type: "historyEdit",
			value: model.selected
		}, !model.busy && !model.pending && !model.uploading, { iconOnly: true }),
		button("agentRequestNew", rect(width - inset - 72, 10, 32, 32), tr("New conversation"), "add", { type: "historyNew" }, !model.busy && !model.uploading, { iconOnly: true }),
		button("agentRequestRefresh", rect(width - inset - 32, 10, 32, 32), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy && !model.uploading, { iconOnly: true }),
		node("View", "agentRequestOutput", rect(0, transcriptTop, width, Math.max(70, composerTop - transcriptTop - 12)), {
			view: "transcript",
			messages: messages(model),
			events: activity(model, language),
			active: working,
			status: state
		}),
		node("Box", "agentComposerSurface", rect(composerX, composerTop, composerWidth, height - composerTop - 12), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			borderWidth: 1,
			radius: 20
		}),
		node("View", "agentRequestContext", rect(composerX + 12, composerTop + 10, Math.max(0, composerWidth - 24), contextHeight), {
			view: "context",
			context,
			expanded: model.contextExpanded
		}),
		node("Area", "agentRequestPrompt", rect(composerX + 10, composerTop + contextHeight + 18, Math.max(0, composerWidth - 20), 64), {
			label: tr(working ? "Add a correction while the agent works" : "What should the agent do?"),
			placeholder: tr(working ? "Add a correction while the agent works" : "Describe the task. Attach files or paste an image."),
			text: model.prompt,
			flat: true,
			readOnly: !!model.pending,
			enabled: !model.busy,
			sendOnEnter: true,
			sendAction: { type: "send" },
			action: { type: "prompt" }
		}),
		button("agentRequestAttach", rect(composerX + 12, height - 52, 32, 32), tr("Attach files"), "add", { type: "attach" }, !model.uploading && !model.pending && !model.busy, { iconOnly: true }),
		button("agentRequestPaste", rect(composerX + 50, height - 52, 32, 32), tr("Paste attachment"), "content-paste", { type: "paste" }, !model.uploading && !model.pending && !model.busy, { iconOnly: true }),
		node("View", "agentRequestPermissions", rect(composerX + 88, height - 52, 32, 32), {
			view: "permissions",
			actions: permissionActions(model),
			enabled: !model.busy
		})
	];
	if (sendVisible) nodes.push(button("agentRequestSend", rect(composerX + composerWidth - 44 - (working ? 40 : 0), height - 52, 32, 32), tr(working ? "Send correction" : "Send to agent"), "arrow-upward", { type: "send" }, canSend(model), {
		iconOnly: true,
		highlighted: true
	}));
	if (working) nodes.push(button("agentRequestCancel", rect(composerX + composerWidth - 44, height - 52, 32, 32), tr("Cancel request"), "stop", { type: "cancel" }, !model.busy && current.status !== "cancelling", { iconOnly: true }));
	if (providers.length) nodes.push(node("Choice", "agentRequestProvider", rect(narrow ? composerX + 12 : composerX + 128, height - (narrow ? 132 : 52), narrow ? Math.min(210, composerWidth - 24) : Math.min(210, composerWidth - modelWidth - 332 - (working && sendVisible ? 40 : 0)), 32), {
		label: tr("AI connection"),
		value: provider(model),
		enabled: !model.busy && !working && !model.pending,
		options: providers.map((item) => ({
			value: item.id,
			label: item.name
		})),
		action: { type: "provider" }
	}));
	if (availableModels(model).length) nodes.push(node("Choice", "agentRequestModel", rect(narrow ? composerX + 12 : composerX + composerWidth - modelWidth - 52 - (narrow ? 0 : 144) - (working && sendVisible ? 40 : 0), height - (narrow ? 92 : 52), modelWidth, 32), {
		label: tr("Model"),
		value: model.model ?? current.model ?? "",
		enabled: !model.busy && !working && !model.pending,
		options: [{
			value: "",
			label: tr("Agent default")
		}, ...availableModels(model).map((item) => ({
			value: item.id,
			label: item.label
		}))],
		action: { type: "model" }
	}));
	const efforts = selectedModel(model)?.efforts || [];
	if (efforts.length) nodes.push(node("Choice", "agentRequestEffort", rect(narrow ? composerX + 20 + modelWidth : composerX + composerWidth - 188 - (working && sendVisible ? 40 : 0), height - (narrow ? 92 : 52), narrow ? Math.min(136, modelWidth) : 136, 32), {
		label: tr("Reasoning effort"),
		value: model.effort ?? current.effort ?? "",
		enabled: !model.busy && !working && !model.pending,
		options: [{
			value: "",
			label: tr("Agent default")
		}, ...efforts.map((value) => ({
			value,
			label: tr({
				none: "None",
				minimal: "Minimal",
				low: "Low",
				medium: "Medium",
				high: "High",
				xhigh: "Extra high",
				max: "Maximum",
				ultra: "Ultra"
			}[value] || value)
		}))],
		action: { type: "effort" }
	}));
	if (model.attachments.length) nodes.push(node("View", "agentRequestAttachments", rect(composerX + 12, height - 96 - (narrow ? 40 : 0) - providerRow, composerWidth - 24, 36), {
		view: "attachments",
		files: model.attachments
	}));
	if (sources.length) nodes.push(label("agentRequestSources", rect(inset, current.undo_operation ? 124 : 92, inner, 24), tr("Conversation context") + ": " + sources.map((source) => source.title).join(" · "), {
		fontRole: "caption",
		color: "secondaryText",
		toolTip: sources.map((source) => source.project_title + " · " + source.title).join("\n")
	}));
	if (current.undo_operation) nodes.push(button("agentRequestUndo", rect(width - inset - 134, 92, 134, 26), tr("Undo field change"), "undo", { type: "undo" }, !working && !model.busy && !model.uploading));
	return { nodes };
}
function describe(model, width, height, language) {
	if (model.projectRules) return describe$1(model, width, height, language);
	const space = layout(model, width);
	const nodes = [];
	if (!space.small || !space.visible) nodes.push(node("Box", "agentChatMain", rect(space.mainX, 0, space.mainWidth, height), { children: describeChat(model, space.mainWidth, height, language, space.visible).nodes }));
	if (space.visible) nodes.push(node("Box", "agentChatHistory", rect(0, 0, space.panel, height), {
		radius: 0,
		children: describe$2(model, space.panel, height, language, space.small).nodes
	}));
	return { nodes };
}
//#endregion
//#region src/features/scripts/AgentChatPort.vue
var _hoisted_1$1 = { key: 0 };
var _hoisted_2 = {
	key: 1,
	class: "agent-context"
};
var _hoisted_3 = { class: "agent-context-row" };
var _hoisted_4 = { class: "agent-context-chips" };
var _hoisted_5 = ["title"];
var _hoisted_6 = {
	key: 0,
	class: "agent-context-details",
	tabindex: "0"
};
var _hoisted_7 = {
	key: 2,
	class: "agent-attachment-strip"
};
var _hoisted_8 = ["src"];
var _hoisted_9 = ["title"];
var _hoisted_10 = ["aria-label"];
var _hoisted_11 = {
	key: 0,
	class: "agent-chat-empty"
};
var _hoisted_12 = ["src", "alt"];
var _hoisted_13 = { key: 0 };
var _hoisted_14 = ["open"];
var _hoisted_15 = { "data-frame": "agentRequestStatus" };
var _sfc_main$1 = {
	__name: "AgentChatPort",
	props: {
		frameNode: Object,
		previews: Object
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const log = ref(null);
		const chips = computed(() => contextItems(props.frameNode.context || {}, appearance.language));
		const rows = computed(() => props.frameNode.messages || []);
		watch([rows, () => props.frameNode.status?.text], async () => {
			const element = log.value;
			const follow = element && element.scrollHeight - element.scrollTop - element.clientHeight < 60;
			await nextTick();
			if (follow && log.value) log.value.scrollTop = log.value.scrollHeight;
		});
		const messageStyle = (row) => {
			const geometry = messageGeometry(props.frameNode.width, row.role, 20, 0);
			return {
				width: geometry.width + "px",
				marginLeft: geometry.x + "px",
				padding: geometry.padding + "px",
				marginBottom: metrics.messageGap + "px"
			};
		};
		return (_ctx, _cache) => {
			return __props.frameNode.view === "permissions" ? (openBlock(), createBlock(_sfc_main$4, {
				key: 0,
				label: "Agent permissions",
				icon: "tune",
				"compact-trigger": "",
				overlay: "",
				width: 320,
				disabled: !__props.frameNode.enabled
			}, {
				default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.frameNode.actions, (action, index) => {
					return openBlock(), createElementBlock(Fragment, { key: index }, [action.separator ? (openBlock(), createElementBlock("hr", _hoisted_1$1)) : (openBlock(), createBlock(_sfc_main$6, {
						key: 1,
						label: action.title,
						icon: action.icon,
						checked: action.checked,
						role: action.role,
						disabled: action.enabled === false,
						onClick: ($event) => emit("event", {
							type: action.command,
							value: !action.checked
						})
					}, null, 8, [
						"label",
						"icon",
						"checked",
						"role",
						"disabled",
						"onClick"
					]))], 64);
				}), 128))]),
				_: 1
			}, 8, ["disabled"])) : __props.frameNode.view === "context" ? (openBlock(), createElementBlock("div", _hoisted_2, [createBaseVNode("div", _hoisted_3, [createBaseVNode("div", _hoisted_4, [(openBlock(true), createElementBlock(Fragment, null, renderList(chips.value, (chip, index) => {
				return openBlock(), createElementBlock("span", {
					key: index,
					class: "agent-context-chip",
					title: chip.value,
					style: normalizeStyle({ width: chip.width + "px" })
				}, [createVNode(_sfc_main$2, { name: chip.icon }, null, 8, ["name"]), createBaseVNode("span", null, toDisplayString(chip.value), 1)], 12, _hoisted_5);
			}), 128))]), createVNode(_sfc_main$3, {
				"icon-only": "",
				icon: __props.frameNode.expanded ? "expand-less" : "expand-more",
				label: "Context details",
				"aria-expanded": __props.frameNode.expanded,
				onClick: _cache[0] || (_cache[0] = ($event) => emit("event", { type: "context" }))
			}, null, 8, ["icon", "aria-expanded"])]), __props.frameNode.expanded ? (openBlock(), createElementBlock("div", _hoisted_6, toDisplayString([
				__props.frameNode.context.page,
				__props.frameNode.context.view,
				...__props.frameNode.context.search_keys || []
			].filter(Boolean).join("\n")), 1)) : createCommentVNode("", true)])) : __props.frameNode.view === "attachments" ? (openBlock(), createElementBlock("div", _hoisted_7, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.frameNode.files, (file) => {
				return openBlock(), createElementBlock("div", {
					key: file.attachment_id,
					class: "agent-attachment-chip"
				}, [
					__props.previews?.[file.attachment_id] ? (openBlock(), createElementBlock("img", {
						key: 0,
						src: __props.previews[file.attachment_id],
						alt: ""
					}, null, 8, _hoisted_8)) : (openBlock(), createBlock(_sfc_main$2, {
						key: 1,
						name: "attach-file"
					})),
					createBaseVNode("span", { title: file.name }, toDisplayString(file.name), 9, _hoisted_9),
					createVNode(_sfc_main$3, {
						"icon-only": "",
						icon: "close",
						label: "Remove attachment",
						onClick: ($event) => emit("event", {
							type: "remove",
							value: file.attachment_id
						})
					}, null, 8, ["onClick"])
				]);
			}), 128))])) : (openBlock(), createElementBlock("div", {
				key: 3,
				ref_key: "log",
				ref: log,
				class: "agent-transcript",
				role: "log",
				"aria-label": unref(t)("Conversation"),
				"aria-live": "polite"
			}, [
				!rows.value.length ? (openBlock(), createElementBlock("div", _hoisted_11, [
					createVNode(_sfc_main$2, { name: "chat" }),
					createBaseVNode("strong", null, toDisplayString(unref(t)("What would you like to change?")), 1),
					createBaseVNode("span", null, toDisplayString(unref(t)("Describe the task. Attach files or paste an image.")), 1)
				])) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList(rows.value, (row) => {
					return openBlock(), createElementBlock("article", {
						key: row.id,
						class: normalizeClass(["agent-message", row.role]),
						style: normalizeStyle(messageStyle(row))
					}, [
						createVNode(_sfc_main$8, { text: safeMarkdown(row.text) }, null, 8, ["text"]),
						(openBlock(true), createElementBlock(Fragment, null, renderList(row.attachments || [], (file) => {
							return openBlock(), createElementBlock("div", {
								key: file.attachment_id,
								class: "agent-message-file"
							}, [__props.previews?.[file.attachment_id] ? (openBlock(), createElementBlock("img", {
								key: 0,
								class: "agent-message-image",
								src: __props.previews[file.attachment_id],
								alt: file.name
							}, null, 8, _hoisted_12)) : createCommentVNode("", true), createVNode(_sfc_main$3, {
								label: file.name,
								icon: "attach-file",
								onClick: ($event) => emit("event", {
									type: "download",
									value: file.attachment_id
								})
							}, null, 8, ["label", "onClick"])]);
						}), 128)),
						__props.frameNode.active && row.role === "user" && row.delivered === false ? (openBlock(), createElementBlock("small", _hoisted_13, toDisplayString(unref(t)("Correction queued")), 1)) : createCommentVNode("", true)
					], 6);
				}), 128)),
				__props.frameNode.events?.length ? (openBlock(), createElementBlock("details", {
					key: 1,
					class: "agent-tool-progress",
					style: normalizeStyle(messageStyle({ role: "assistant" })),
					open: __props.frameNode.active
				}, [createBaseVNode("summary", null, toDisplayString(unref(t)(__props.frameNode.active ? "Working with TACTIC tools…" : "Operation details")), 1), (openBlock(true), createElementBlock(Fragment, null, renderList(__props.frameNode.events, (step, index) => {
					return openBlock(), createElementBlock("div", { key: index }, toDisplayString(step), 1);
				}), 128))], 12, _hoisted_14)) : createCommentVNode("", true),
				__props.frameNode.status ? (openBlock(), createElementBlock("div", {
					key: 2,
					class: "agent-chat-status",
					"data-frame": "agentRequestStatusRow",
					role: "status",
					style: normalizeStyle({
						...messageStyle({ role: "assistant" }),
						color: "var(" + unref(cssRoles)[__props.frameNode.status.color] + ")"
					})
				}, [createVNode(_sfc_main$2, { name: __props.frameNode.status.icon }, null, 8, ["name"]), createBaseVNode("span", _hoisted_15, toDisplayString(__props.frameNode.status.text), 1)], 4)) : createCommentVNode("", true)
			], 8, _hoisted_10));
		};
	}
};
//#endregion
//#region src/features/scripts/AgentRequest.vue
var _hoisted_1 = ["aria-label"];
var attachmentCommand = "tactic.ui.panel.agent_attachment_cmd.AgentAttachmentCmd";
var _sfc_main = {
	__name: "AgentRequest",
	props: {
		ticket: String,
		capture: Function
	},
	emits: ["providers", "mcp"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const currentLogin = inject("currentLogin", () => "");
		function savedChoices() {
			try {
				if (!currentLogin()) return {};
				const saved = JSON.parse(localStorage.getItem("tactic_stream.agentChat." + currentLogin()) || "null");
				return Object.fromEntries(Object.entries(saved || {}).filter(([key, value]) => [
					"provider",
					"model",
					"effort"
				].includes(key) && typeof value === "string" && value.length <= 512 || ["allowChanges", "allowWeb"].includes(key) && typeof value === "boolean"));
			} catch {
				return {};
			}
		}
		function initial$2(context = {}) {
			return Object.assign(initial(context), savedChoices());
		}
		function rememberChoices(fields) {
			try {
				if (currentLogin()) localStorage.setItem("tactic_stream.agentChat." + currentLogin(), JSON.stringify({
					...savedChoices(),
					...fields
				}));
			} catch (error) {
				model.value.error = error.message;
			}
		}
		const dialog = ref(null), body = ref(null), size = ref({
			width: 900,
			height: 650
		});
		const model = ref(initial$2());
		const fileInput = ref(null), previews = ref({});
		const views = computed(() => Object.fromEntries([
			"context",
			"transcript",
			"attachments",
			"permissions"
		].map((name) => [name, {
			component: markRaw(_sfc_main$1),
			nodeProps: true,
			props: {
				previews: previews.value,
				onEvent: event
			}
		}])));
		const scene = computed(() => describe(model.value, size.value.width, size.value.height, appearance.language));
		const historyModels = computed(() => ({ agentHistoryRows: rows(model.value, appearance.language) }));
		const historyRow = (node, row$1) => row(model.value, row$1, node.width - 16, appearance.language);
		let generation = 0, queuedAction = "", observer, timer, contextTicket = "", inFlight = false, historyTimer, libraryOperation = null;
		async function call(action, values = {}, command = "tactic.ui.panel.agent_request_cmd.AgentRequestCmd", targetProject) {
			const project = targetProject || (action === "draft" ? values.context.project : model.value.context.project);
			const result = await rpc("execute_cmd", [
				{
					ticket: contextTicket,
					project
				},
				command,
				{
					action,
					project_code: project,
					...values
				}
			], {}, true, true);
			if (result.status !== "OK") throw new Error(result.description || "Agent request failed");
			return typeof result.info === "string" ? JSON.parse(result.info) : result.info;
		}
		async function request(action = "refresh") {
			if (inFlight) {
				if (action !== "poll" && !model.value.busy) {
					queuedAction = action;
					model.value.busy = true;
				}
				return;
			}
			if (!model.value.context.project) return;
			const id = ++generation;
			let filter = {
				query: model.value.history.query,
				archived: model.value.history.archived,
				project_filter: model.value.history.project || ""
			};
			let reading = false;
			const before = model.value.requests, nextOffset = model.value.next_offset;
			inFlight = true;
			model.value.busy = action !== "poll";
			if (action !== "poll") model.value.error = "";
			try {
				if (action === "rules_read" || action === "rules_save") {
					const rules = await call(action, action === "rules_save" ? {
						text: model.value.projectRules.text,
						expected_revision: model.value.projectRules.revision
					} : {});
					if (id === generation) model.value.projectRules = action === "rules_save" ? null : {
						...rules,
						original: rules.text
					};
					return;
				}
				if (action.startsWith("executor_")) await call(action.split(":")[0].slice(9), { target: action.split(":")[1] }, "tactic.ui.panel.agent_executor_cmd.AgentExecutorCmd");
				if (action === "send") {
					model.value.pending ||= started(model.value) ? {
						message_id: randomUuid(),
						host_id: host(model.value).host_id,
						text: model.value.prompt,
						model: model.value.model ?? model.value.request.model ?? "",
						effort: model.value.effort ?? model.value.request.effort ?? "",
						provider: provider(model.value),
						attachments: model.value.attachments.map((file) => file.attachment_id)
					} : {
						request_id: model.value.selected || randomUuid(),
						host_id: host(model.value).host_id,
						document: {
							prompt: model.value.prompt,
							context: JSON.parse(JSON.stringify(model.value.request.document?.context || model.value.context)),
							allow_changes: model.value.allowChanges,
							allow_web: model.value.allowWeb,
							model: model.value.model ?? "",
							effort: model.value.effort ?? "",
							provider: provider(model.value),
							attachments: model.value.attachments.map((file) => file.attachment_id)
						}
					};
					const saved = started(model.value) ? await call("message", {
						request_id: model.value.selected,
						...model.value.pending
					}) : await call("submit", model.value.pending);
					if (id !== generation) return;
					model.value.selected = saved.request_id;
					model.value.pending = null;
					model.value.prompt = "";
					model.value.attachments = [];
					delete model.value.drafts[key({ request_id: saved.request_id }, model.value.context.project)];
				} else if (action === "cancel") await call("cancel", { request_id: model.value.selected });
				else if (action === "undo") await call("undo", {
					request_id: model.value.selected,
					operation_id: model.value.request.undo_operation
				});
				else if (action === "library") {
					const operation = libraryOperation;
					const saved = await call(operation.action, operation.values, void 0, operation.project);
					if (id !== generation) return;
					if (operation.action === "draft") {
						model.value.drafts[key({ request_id: model.value.selected }, model.value.context.project)] = draft(model.value);
						model.value.selected = saved.request_id;
						model.value.request = saved;
						if (model.value.context.project !== saved.document.context.project) clearPreviews();
						model.value.context = saved.document.context;
						if (!operation.edit) Object.assign(model.value, restored(savedChoices()));
						if (!operation.edit && size.value.width < 940) model.value.history.mobile = false;
						model.value.history.query = "";
						model.value.history.archived = false;
						filter = {
							query: "",
							archived: false,
							project_filter: model.value.history.project || ""
						};
					} else model.value.history.edit = null;
				}
				reading = true;
				const state = await call("state");
				Object.assign(state, await call("library", {
					...filter,
					...action === "historyMore" ? { offset: nextOffset } : {}
				}));
				if (id !== generation) return;
				if (filter.query !== model.value.history.query || filter.archived !== model.value.history.archived || filter.project_filter !== (model.value.history.project || "")) {
					queuedAction = "refresh";
					return;
				}
				if (action === "historyMore" || action === "poll") {
					state.requests = merge(before, state.requests);
					if (action === "poll" && before.length) state.next_offset = nextOffset;
				}
				Object.assign(model.value, state);
				if (model.value.selected) {
					const current = await call("read", { request_id: model.value.selected });
					if (id !== generation) return;
					const wasActive = active(model.value) && model.value.request.request_id === current.request_id;
					model.value.request = current;
					model.value.context = current.document.context;
					if (action === "library" && libraryOperation?.edit) model.value.history = change(model.value, {
						type: "historyEdit",
						value: {
							request_id: model.value.selected,
							project: model.value.context.project
						}
					}, size.value.width < 940);
					for (const file of [...model.value.attachments, ...current.messages?.flatMap((message) => message.attachments || []) || []]) {
						if (!file.media_type.startsWith("image/") || file.attachment_id in previews.value) continue;
						try {
							const preview = await call("preview", { attachment_id: file.attachment_id }, attachmentCommand);
							if (id !== generation) return;
							previews.value[file.attachment_id] = preview.url;
						} catch {
							if (id !== generation) return;
							previews.value[file.attachment_id] = "";
						}
					}
					if (wasActive && !active(model.value)) notify(current.status === "completed" && current.outcome === "completed" ? "complete" : "warning", status(model.value, appearance.language).text, model.value.context.title || model.value.context.project, "agent-request", current.request_id + ":" + current.turn);
				}
				model.value.refreshError = "";
			} catch (error) {
				if (id === generation) model.value[reading ? "refreshError" : "error"] = error.message;
			} finally {
				if (id === generation) {
					model.value.busy = false;
					inFlight = false;
				}
				if (id === generation && queuedAction) {
					const next = queuedAction;
					queuedAction = "";
					request(next);
				} else schedule();
			}
		}
		function schedule() {
			clearTimeout(timer);
			if (dialog.value?.open || active(model.value)) timer = setTimeout(() => request("poll"), 2500);
		}
		function event(action) {
			if (action.type.startsWith("rules")) {
				if (model.value.busy || model.value.pending) return;
				if (action.type === "rules") {
					model.value.projectRules = {
						text: "",
						original: "",
						revision: ""
					};
					request("rules_read");
				} else if (action.type === "rulesCancel") {
					model.value.projectRules = null;
					model.value.error = "";
				} else if (action.type === "rulesText") model.value.projectRules.text = action.value;
				else if (action.type === "rulesSave") request("rules_save");
				return;
			}
			if (action.type === "executorTarget") {
				model.value.executorTarget = action.value;
				return;
			}
			if (action.type === "executor" && ["start", "stop"].includes(action.value?.action)) {
				if (!model.value.busy) request("executor_" + action.value.action + ":" + action.value.target);
				return;
			}
			if (action.type === "mcp") {
				emit("mcp", JSON.parse(JSON.stringify(model.value.request?.document?.context || model.value.context)));
				return;
			}
			if (action.type === "providers") {
				emit("providers");
				return;
			}
			const previousHistory = model.value.history;
			const changed = change(model.value, action, size.value.width < 940);
			if (changed) {
				model.value.history = changed;
				if (changed.query !== previousHistory.query || changed.archived !== previousHistory.archived || changed.project !== previousHistory.project) {
					clearTimeout(historyTimer);
					historyTimer = setTimeout(() => request(), action.type === "historyQuery" ? 300 : 0);
				}
				return;
			}
			if (model.value.busy) return;
			if (action.type === "historyNew" || action.type === "historyEdit" && !action.value) {
				if (model.value.pending || model.value.uploading) return;
				if (!model.value.selected && action.type === "historyNew" && (model.value.prompt.trim() || model.value.attachments.length)) {
					model.value.error = "Send or clear the current draft before opening another object";
					return;
				}
				const capture = action.type === "historyEdit" ? model.value.context : props.capture();
				libraryOperation = {
					action: "draft",
					edit: action.type === "historyEdit",
					values: {
						request_id: randomUuid(),
						context: action.type === "historyEdit" ? capture : projectContext(capture, model.value.history.project || capture.project)
					}
				};
				request("library");
				return;
			}
			if ([
				"historySave",
				"historyArchive",
				"historyGroupRemove"
			].includes(action.type)) {
				const edit = model.value.history.edit;
				if (!edit) return;
				libraryOperation = edit.kind === "group" ? {
					action: action.type === "historyGroupRemove" ? "group_remove" : "group_save",
					values: {
						group: edit.id,
						name: edit.name,
						expected_revision: edit.revision
					}
				} : {
					action: "organize",
					values: {
						request_id: edit.id,
						expected_revision: edit.revision,
						document: {
							title: edit.title,
							group: edit.group,
							pinned: edit.pinned,
							archived: action.type === "historyArchive" ? !edit.archived : edit.archived
						}
					}
				};
				libraryOperation.project = edit.project || model.value.context.project;
				request("library");
				return;
			}
			if (action.type === "historyUseContext") {
				const source = model.value.history.edit;
				if (!source || !model.value.selected || active(model.value)) return;
				libraryOperation = {
					action: "link_source",
					values: {
						request_id: model.value.selected,
						source_project: source.project,
						source_request: source.id
					}
				};
				request("library");
				return;
			}
			if (action.type === "historyMore") {
				request("historyMore");
				return;
			}
			if (action.type === "prompt" || action.type === "changes" || action.type === "web") {
				if (model.value.pending) return;
				if (action.type !== "prompt" && started(model.value)) return;
				if (action.type === "prompt") model.value.prompt = action.value;
				else if (action.type === "changes") model.value.allowChanges = !!action.value;
				else model.value.allowWeb = !!action.value;
				if (action.type !== "prompt") rememberChoices({ [action.type === "changes" ? "allowChanges" : "allowWeb"]: !!action.value });
			} else if (action.type === "select") {
				if (model.value.uploading || model.value.pending) return;
				if (!model.value.selected && (model.value.prompt.trim() || model.value.attachments.length)) {
					model.value.error = "Send or clear the current draft before opening another object";
					return;
				}
				const selected = selection(model.value, action.value);
				if (!selected) return;
				model.value.drafts[key({ request_id: model.value.selected }, model.value.context.project)] = draft(model.value);
				model.value.context = projectContext(model.value.context, selected.project || model.value.context.project);
				clearPreviews();
				generation++;
				inFlight = false;
				queuedAction = "";
				Object.assign(model.value, {
					selected: selected.request_id,
					request: {},
					...restored({
						...selected.status === "draft" ? savedChoices() : {},
						...model.value.drafts[key(selected, model.value.context.project)]
					}),
					pending: null
				});
				model.value.history.edit = null;
				if (size.value.width < 940) model.value.history.mobile = false;
				request();
			} else if (action.type === "send" && canSend(model.value)) request("send");
			else if (action.type === "cancel") request("cancel");
			else if (action.type === "refresh") request();
			else if (action.type === "provider") {
				model.value.provider = action.value;
				model.value.model = "";
				model.value.effort = "";
				rememberChoices({
					provider: action.value,
					model: "",
					effort: ""
				});
			} else if (action.type === "model") {
				model.value.model = action.value;
				model.value.effort = "";
				rememberChoices({
					provider: provider(model.value),
					model: action.value,
					effort: ""
				});
			} else if (action.type === "effort") {
				model.value.effort = action.value;
				rememberChoices({
					provider: provider(model.value),
					model: model.value.model ?? model.value.request.model ?? "",
					effort: action.value
				});
			} else if (action.type === "context") model.value.contextExpanded = !model.value.contextExpanded;
			else if (action.type === "remove" && !model.value.pending) model.value.attachments = model.value.attachments.filter((file) => file.attachment_id !== action.value);
			else if (action.type === "attach") fileInput.value.click();
			else if (action.type === "paste") pasteClipboard();
			else if (action.type === "download") download(action.value);
			else if (action.type === "undo") request("undo");
		}
		function clearPreviews() {
			Object.values(previews.value).forEach((url) => URL.revokeObjectURL(url));
			previews.value = {};
		}
		async function addFiles(files) {
			const state = model.value;
			if (state.uploading || state.pending || state.busy) return;
			state.uploading = true;
			state.error = "";
			try {
				if (state.attachments.length + files.length > 20) throw new Error("Attach at most 20 files");
				for (const file of files) {
					if (file.size > 67108864) throw new Error("Each attachment must be at most 64 MB");
					const attachment_id = randomUuid();
					await call("start", {
						attachment_id,
						name: file.name,
						size: file.size,
						media_type: file.type
					}, attachmentCommand);
					for (let offset = 0; offset < file.size; offset += 393216) {
						if (model.value !== state) return;
						const bytes = new Uint8Array(await file.slice(offset, offset + 393216).arrayBuffer());
						let binary = "";
						for (let index = 0; index < bytes.length; index += 8192) binary += String.fromCharCode(...bytes.subarray(index, index + 8192));
						await call("append", {
							attachment_id,
							offset,
							data: btoa(binary)
						}, attachmentCommand);
					}
					const metadata = await call("finish", { attachment_id }, attachmentCommand);
					if (model.value !== state) return;
					if (file.type.startsWith("image/")) previews.value[attachment_id] = URL.createObjectURL(file);
					state.attachments.push(metadata);
				}
			} catch (error) {
				state.error = error.message;
			} finally {
				state.uploading = false;
				if (fileInput.value) fileInput.value.value = "";
			}
		}
		function paste(event) {
			const files = event.clipboardData?.files;
			if (files?.length) {
				event.preventDefault();
				addFiles([...files]);
			}
		}
		async function pasteClipboard() {
			try {
				if (!navigator.clipboard?.read) throw new Error("Press Ctrl+V in the message to attach clipboard files or images");
				const files = [];
				for (const item of await navigator.clipboard.read()) {
					const type = item.types.find((type) => type.startsWith("image/"));
					if (type) files.push(new File([await item.getType(type)], "clipboard-" + Date.now() + ".png", { type }));
				}
				if (!files.length) throw new Error("Press Ctrl+V in the message to attach clipboard files or images");
				await addFiles(files);
			} catch (error) {
				model.value.error = error.message;
			}
		}
		async function download(attachment_id) {
			try {
				const chunks = [];
				let offset = 0, result;
				do {
					result = await call("read", {
						attachment_id,
						offset
					}, attachmentCommand);
					chunks.push(Uint8Array.from(atob(result.data), (char) => char.charCodeAt(0)));
					offset = result.next_offset;
				} while (offset !== null);
				const url = URL.createObjectURL(new Blob(chunks, { type: result.media_type }));
				const link = document.createElement("a");
				link.href = url;
				link.download = result.name;
				link.click();
				setTimeout(() => URL.revokeObjectURL(url), 1e3);
			} catch (error) {
				model.value.error = error.message;
			}
		}
		async function open(context, fresh = false) {
			if (fresh) {
				if (model.value.prompt.trim() || model.value.attachments.length || model.value.pending || model.value.uploading) {
					await open();
					throw Error("Send or clear the current draft before opening another object");
				}
				generation++;
				inFlight = false;
				queuedAction = "";
				clearTimeout(timer);
				clearPreviews();
				model.value = Object.assign(initial$2(context), {
					drafts: model.value.drafts,
					history: model.value.history
				});
			}
			if (!model.value.projectRules && !model.value.selected && !model.value.prompt && !model.value.attachments.length && !model.value.pending && !model.value.uploading) model.value = Object.assign(initial$2(context || props.capture()), {
				history: model.value.history,
				drafts: model.value.drafts
			});
			contextTicket = props.ticket;
			await nextTick();
			if (!dialog.value.open) dialog.value.show();
			observer ||= observeFrameSizes(() => {
				if (body.value.clientWidth > 0 && body.value.clientHeight > 0) size.value = {
					width: body.value.clientWidth,
					height: body.value.clientHeight
				};
			});
			observer.observe(body.value);
			if (body.value.clientWidth > 0 && body.value.clientHeight > 0) size.value = {
				width: body.value.clientWidth,
				height: body.value.clientHeight
			};
			if (!model.value.context.project) model.value.error = "Select a project before contacting the agent";
			request();
		}
		function close() {
			dialog.value?.close();
			clearTimeout(timer);
			clearTimeout(historyTimer);
		}
		watch(() => props.ticket, () => {
			generation++;
			inFlight = false;
			queuedAction = "";
			close();
			contextTicket = "";
			clearPreviews();
			model.value = initial$2();
		});
		onBeforeUnmount(() => {
			generation++;
			clearTimeout(timer);
			clearTimeout(historyTimer);
			observer?.disconnect();
			clearPreviews();
		});
		__expose({
			open,
			windowContext: () => ({
				project: model.value.context?.project,
				route: { request: model.value.selected },
				state: {
					context: model.value.context,
					selected: model.value.selected,
					draft: draft(model.value)
				}
			}),
			restoreWindowContext: async (state) => {
				if (state.context) model.value.context = state.context;
				model.value.selected = state.selected || "";
				await request();
				Object.assign(model.value, restored(state.draft || {}));
			}
		});
		return (_ctx, _cache) => {
			return openBlock(), createBlock(Teleport, { to: "body" }, [createVNode(_sfc_main$7, {
				ref_key: "dialog",
				ref: dialog,
				title: "External agent",
				"window-kind": "agent_request",
				class: "agent-request-dialog",
				"close-on-outside": false,
				onClosed: schedule
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "body",
					ref: body,
					class: "agent-request-body",
					onPaste: paste,
					onDragover: _cache[1] || (_cache[1] = withModifiers(() => {}, ["prevent"])),
					onDrop: _cache[2] || (_cache[2] = withModifiers(($event) => addFiles([...$event.dataTransfer.files]), ["prevent"]))
				}, [createBaseVNode("input", {
					ref_key: "fileInput",
					ref: fileInput,
					type: "file",
					multiple: "",
					hidden: "",
					"aria-label": unref(t)("Attach files"),
					onChange: _cache[0] || (_cache[0] = ($event) => addFiles([...$event.target.files]))
				}, null, 40, _hoisted_1), createVNode(_sfc_main$5, {
					scene: scene.value,
					models: historyModels.value,
					"describe-row": historyRow,
					views: views.value,
					onEvent: event
				}, null, 8, [
					"scene",
					"models",
					"views"
				])], 544)]),
				_: 1
			}, 512)]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=AgentRequest.js.map
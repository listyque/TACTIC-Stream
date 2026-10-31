import { E as nextTick, F as resolveComponent, K as withDirectives, M as openBlock, T as mergeProps, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, nt as normalizeStyle, s as vShow } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { U as sidebarRequest } from "./index.js";
import { G as button, H as observeFrameSizes, J as muted, K as label, X as rect, Y as node, t as _sfc_main$1, w as translate } from "./FrameView.js";
import { n as sections } from "./sections.ui.js";
import { a as tabs, n as notices, o as toolbar, r as policy, t as documentEvent } from "./admin.document.js";
import { i as row$1, n as navigate } from "./tree.ui.js";
//#region ../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.ui.mjs
var list = (id, bounds, source, rowHeight) => node("List", id, bounds, {
	source,
	rowHeight,
	keyField: "index",
	fields: [],
	role: source === "entries" ? "tree" : void 0,
	scrollbarId: id + "ScrollBar"
});
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text) => translate(text, language), edit = policy(model).editable && !ui.confirmation;
	const notice = notices(model, ui, width, language, ui.confirmation === "delete" ? "Delete the selected sidebar item?" : "Discard unsaved sidebar changes?", ui.confirmation === "delete" ? "Delete item" : "");
	const nodes = notice.nodes;
	let y = notice.top;
	const compact = width < 750, h = compact ? 142 : 58;
	const minimum = notice.top + h + (compact ? 328 : 316);
	if (height < minimum) return { nodes: [node("Scroll", "sidebarPageScroll", rect(0, 0, width, height), {
		contentHeight: minimum,
		scrollbarId: "sidebarPageScrollBar",
		children: describe(model, ui, Math.max(1, width - 16), minimum, language).nodes
	})] };
	nodes.push(node("Box", "sidebarHeading", rect(0, y, width, h), {
		background: "surfaceContainerHigh",
		children: [
			label("sidebarTitle", rect(14, 6, compact ? width - 108 : width - 472, 24), tr("Project navigation"), { weight: 600 }),
			label("sidebarProject", rect(14, 30, compact ? width - 28 : width - 472, 22), model.projectTitle, muted),
			tabs("sidebarSourceSelector", [{
				value: "handler",
				label: "TH",
				icon: "desktop"
			}, {
				value: "tactic",
				label: "TACTIC",
				icon: "globe"
			}], model.source, rect(compact ? 12 : width - 450, compact ? 58 : 10, compact ? (width - 32) / 2 : 164, 38), edit, "source"),
			tabs("sidebarModeSelector", [{
				value: "simple",
				label: tr("Simple"),
				icon: "table"
			}, {
				value: "xml",
				label: "XML",
				icon: "code"
			}], ui.mode, rect(compact ? width / 2 + 4 : width - 278, compact ? 58 : 10, compact ? (width - 32) / 2 : 180, 38), edit, "mode"),
			button("sidebarReload", rect(width - 88, compact ? 6 : 10, 38, 38), tr("Reload sidebar"), "refresh", { type: "reload" }, !model.busy, { iconOnly: true }),
			button("sidebarHelp", rect(width - 46, compact ? 6 : 10, 38, 38), tr("Sidebar Editor help"), "help", { type: "help" }, true, { iconOnly: true }),
			...compact ? [label("sidebarStatus", rect(12, 104, width - 24, 30), tr(model.dirty ? "Sidebar has unsaved changes" : "Sidebar is up to date"), muted)] : []
		]
	}));
	y += h + 8;
	if (!model.ready) {
		nodes.push(label("sidebarEmpty", rect(12, y, width - 24, 70), tr(model.busy ? "Working on the server…" : "Select a project"), { wrap: true }));
		return { nodes };
	}
	const split = width >= 850, treeWidth = split ? Math.min(Math.max(280, ui.treeWidth), width * .48) : width;
	const contentHeight = Math.max(split ? 270 : 320, height - y - (compact ? 0 : 38));
	const children = [];
	if (split || !ui.editing) tree(children, model, ui, rect(0, 0, treeWidth, contentHeight), language, edit);
	if (split) children.push(node("Splitter", "sidebarSplitter", rect(treeWidth, 0, 10, contentHeight), {
		text: tr("Sidebar preview width"),
		value: treeWidth,
		min: 280,
		max: width * .48,
		action: { type: "split" }
	}));
	if (split || ui.editing) editor(children, model, ui, rect(split ? treeWidth + 10 : 0, 0, split ? width - treeWidth - 10 : width, contentHeight), language, edit, !split);
	if (contentHeight > height - y) nodes.push(node("Scroll", "sidebarPageScroll", rect(0, y, width, Math.max(1, height - y)), {
		contentHeight,
		scrollbarId: "sidebarPageScrollBar",
		children: children.map((item) => Object.assign({}, item, { width: Math.max(1, item.width - 16) }))
	}));
	else nodes.push(node("Box", "sidebarColumns", rect(0, y, width, contentHeight), { children }));
	if (!compact) nodes.push(label("sidebarStatus", rect(0, height - 30, width, 30), tr(model.dirty ? "Sidebar has unsaved changes" : "Sidebar is up to date"), muted));
	return { nodes };
}
function tree(nodes, model, ui, bounds, language, edit) {
	const tr = (text) => translate(text, language), width = bounds.width, children = [];
	children.push(label("sidebarTreeTitle", rect(12, 8, width - 24, 28), tr(model.source === "handler" ? "TH sidebar" : "TACTIC sidebar"), { weight: 600 }));
	let y = 44;
	if (model.source === "handler") {
		children.push(node("Choice", "sidebarGroupPreview", rect(12, y, width - 24, 38), {
			label: tr("Preview group"),
			options: model.previewOptions.map((option) => ({
				value: option.value,
				label: option.label
			})),
			value: model.previewGroup,
			enabled: edit,
			action: { type: "preview" }
		}));
		y += 46;
	}
	children.push(label("sidebarAddLabel", rect(12, y, width - 158, 38), tr("Add"), muted));
	[
		[
			"link",
			"Add link",
			"add"
		],
		[
			"section",
			"Add section",
			"folder"
		],
		[
			"separator",
			"Add separator",
			"sidebar-separator"
		]
	].forEach(([value, text, icon], index) => children.push(button("sidebarAdd_" + value, rect(width - 138 + index * 42, y, 38, 38), tr(text), icon, {
		type: "add",
		value
	}, edit, { iconOnly: true })));
	y += 46;
	children.push(list("sidebarEditorEntries", rect(8, y, width - 16, bounds.height - y - 8), "entries", 64));
	if (!model.entries.length) children.push(label("sidebarTreeEmpty", rect(20, y + 12, width - 40, 70), tr(model.previewGroup ? "This group has no sidebar items" : "This sidebar has no items"), {
		wrap: true,
		color: "secondaryText"
	}));
	nodes.push(node("Box", "sidebarTreePanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	}));
}
function editor(nodes, model, ui, bounds, language, edit, back) {
	const tr = (text) => translate(text, language), width = bounds.width, inner = width - 40, children = [], entry = model.entry;
	let y = 12;
	if (back) {
		children.push(button("sidebarBack", rect(12, y, 110, 36), tr("Back"), "chevron-left", { type: "back" }, !model.busy));
		y += 44;
	}
	children.push(label("sidebarSelectedTitle", rect(12, y, width - 164, 38), entry.title || tr("Selected element"), {
		fontRole: "section",
		weight: 600
	}));
	[
		[
			"up",
			"Move up",
			"arrow-up",
			-1
		],
		[
			"down",
			"Move down",
			"arrow-down",
			1
		],
		[
			"delete",
			"Delete item",
			"delete",
			0
		]
	].forEach(([key, text, icon, value], index) => children.push(button("sidebarItem_" + key, rect(width - 140 + index * 42, y, 38, 38), tr(text), icon, {
		type: value ? "move" : "delete",
		value
	}, edit && model.selected >= 0, { iconOnly: true })));
	y += 46;
	if (model.selected < 0) children.push(label("sidebarSelectHelp", rect(12, y, inner, 100), tr("Select an item in the preview to edit it, or add a new link or section."), {
		wrap: true,
		color: "secondaryText"
	}));
	else if (ui.mode === "xml") {
		children.push(label("sidebarXmlTitle", rect(12, y, inner, 26), tr("Advanced XML"), { weight: 600 }));
		y += 34;
		children.push(node("Area", "sidebarXml", rect(12, y, inner, Math.max(90, bounds.height - y - 58)), {
			text: ui.xml === null ? model.xml : ui.xml,
			label: tr("Selected element XML"),
			monospace: true,
			enabled: edit,
			action: { type: "xml" }
		}), button("sidebarApplyXml", rect(12, bounds.height - 46, inner, 38), tr("Apply XML"), "code", { type: "apply" }, edit && ui.xml !== null));
	} else {
		children.push(tabs("sidebarPages", [
			[
				"item",
				"Item",
				"edit"
			],
			[
				"access",
				"Access",
				"groups"
			],
			[
				"technical",
				"Technical",
				"code"
			]
		].map(([value, text, icon]) => ({
			value,
			label: tr(text),
			icon
		})), ui.page, rect(12, y, width - 24, 38), !model.busy, "page"));
		y += 46;
		if (ui.page === "access") {
			children.push(label("sidebarAccessHeading", rect(12, y, inner, 28), tr("Who can see this item"), {
				fontRole: "section",
				weight: 600,
				role: "heading",
				level: 2
			}));
			y += 36;
			children.push(label("sidebarAccessHelp", rect(12, y, inner, 72), tr("Select the login groups allowed to see this sidebar item. The group preview uses these draft permissions immediately."), Object.assign({ wrap: true }, muted)));
			y += 80;
			children.push(button("manageSidebarGroups", rect(12, y, width - 24, 38), tr("Manage groups and members"), "groups", { type: "groups" }, edit && !model.dirty));
			y += 46;
			children.push(list("sidebarAccessGroups", rect(12, y, width - 24, Math.max(1, bounds.height - y - 12)), "groups", 42));
			if (!model.groups.length) children.push(label("sidebarNoGroups", rect(12, y, inner, 72), tr("No login groups were loaded from the server."), {
				wrap: true,
				color: "secondaryText"
			}));
		} else {
			const body = sections(fields(model, ui, language), inner, language, edit);
			children.push(node("Scroll", "sidebarSettingsViewport", rect(12, y, width - 24, Math.max(1, bounds.height - y - 12)), {
				contentHeight: body.height,
				resetKey: ui.page + ":" + entry.name,
				scrollbarId: "sidebarSettingsScrollBar",
				children: body.nodes
			}));
		}
	}
	nodes.push(node("Box", "sidebarEntryPanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	}));
}
function fields(model, ui, language) {
	const tr = (text) => translate(text, language), entry = model.entry, link = entry.entryType === "link", section = entry.entryType === "section", text = (field) => Object.prototype.hasOwnProperty.call(ui.text, field) ? ui.text[field] : entry[field] || "";
	const heading = (id, title, description) => ({
		id,
		kind: "Heading",
		title,
		description
	});
	const field = (id, key, title, description, extra) => Object.assign({
		id,
		field: key,
		title,
		description,
		props: {
			text: text(key),
			action: {
				type: "text",
				field: key
			}
		}
	}, extra || {});
	const optionsWithEmpty = (options, title) => options.some((option) => option.value === "") ? options.map((option) => option.value === "" ? {
		value: "",
		label: tr(title)
	} : option) : [{
		value: "",
		label: tr(title)
	}].concat(options);
	const choice = (id, key, title, description, options) => field(id, key, title, description, {
		kind: "Choice",
		options,
		props: { value: entry[key] || "" }
	});
	const action = (id, title, type, enabled) => ({
		id,
		kind: "Button",
		title,
		props: {
			text: tr(title),
			enabled,
			action: { type }
		}
	});
	if (ui.page === "technical") return [
		heading("sidebarTechnicalHeading", "Technical settings", "TACTIC identifiers and widget options. For normal setup, use Item."),
		choice("sidebarItemType", "entryType", "Item type", "A link opens a search, a section groups links, and a separator divides the list.", [
			["link", "Link"],
			["section", "Section"],
			["separator", "Separator"]
		].map(([value, label]) => ({
			value,
			label: tr(label)
		}))),
		field("sidebarNameField", "name", "Internal name", "The stable identifier for this sidebar item and its quick-filter defaults. Change the title for a visual rename."),
		field("sidebarChildView", "targetView", "Child view", "The SideBarWdg view containing this section's links.", { when: section }),
		field("sidebarIconName", "icon", "Icon name", "The server icon identifier. You can also choose an icon on the Item page.", { when: entry.entryType !== "separator" }),
		Object.assign(choice("sidebarWidgetType", "widgetType", "Widget Type", "The TACTIC web widget used by this link.", model.widgetOptions), { when: link }),
		field("sidebarClassName", "displayClassName", "Class Path", "The Python class registered for this TACTIC widget.", { when: link && entry.widgetType === "__class__" }),
		field("sidebarDisplayView", "displayView", "View", "The server view used to render the selected TACTIC widget.", { when: link && [
			"custom_layout",
			"edit_layout",
			"tile_layout",
			"fast_layout"
		].indexOf(entry.widgetType) >= 0 })
	];
	return [
		heading("sidebarAppearance", "Appearance", "How this item appears in project navigation. Selection follows your theme."),
		field("sidebarTitleField", "title", "Title", "A short, recognizable name in the sidebar."),
		{
			id: "sidebarIconPicker",
			kind: "IconChoice",
			title: "Icon",
			description: "Click the icon to choose from the searchable library.",
			field: "icon",
			when: entry.entryType !== "separator",
			props: {
				value: entry.glyph || entry.icon,
				tacticCompatibleOnly: true
			}
		},
		field("sidebarColorField", "color", "Navigation color", "Optional #RRGGBB override; leave empty to use the Search Type color."),
		{
			id: "sidebarEntryVisibleCheck",
			kind: "CheckBox",
			title: "Visible in navigation",
			description: "Hide this item without deleting its settings.",
			field: "isVisible",
			props: { checked: entry.isVisible }
		},
		...link ? [
			heading("sidebarSearchHeading", "Search and quick filters", "The saved search defines the starting query. Quick filters refine it in the same search tab and use this item's own defaults."),
			choice("sidebarSearchType", "searchType", "Search Type", "Which project objects this item opens.", model.typeOptions),
			choice("sidebarSearchPreset", "searchView", "Predefined search", "Choose a saved query or leave the list unfiltered.", optionsWithEmpty(model.presetOptions, "No predefined search")),
			...entry.widgetType === "custom_layout" && entry.displayView?.startsWith("dashboard.") ? [action("sidebarEditPage", "Edit page layout", "pageLayout", !model.dirty)] : [],
			action("sidebarSearchSetupButton", "Configure search", "search", !model.dirty && !!entry.searchType && !!entry.isVisible),
			choice("sidebarResultView", "resultViewMode", "Default item view", "The initial presentation when this search tab is opened.", model.resultOptions),
			choice("sidebarLayoutPreset", "layoutPreset", "Workspace layout", "Apply a saved dock arrangement when this sidebar item opens.", optionsWithEmpty(model.layoutOptions, "Do not change workspace layout")),
			choice("sidebarScriptShelf", "scriptShelf", "Script shelf", "Show this shared shelf when the sidebar tab is active.", optionsWithEmpty(model.shelfOptions, "Project default shelf"))
		] : []
	];
}
function row(listNode, record, model, ui, language) {
	if (listNode.source === "groups") return { nodes: [node("CheckBox", "sidebarGroup_" + record.code, rect(0, 0, listNode.width - 16, 38), {
		text: record.label,
		label: record.label,
		checked: record.allowed,
		enabled: policy(model).editable && !ui.confirmation,
		indicatorX: 8,
		action: {
			type: "group",
			code: record.code
		},
		children: [label("sidebarGroupLabel_" + record.code, rect(36, 0, listNode.width - 56, 38), record.label)]
	})] };
	return row$1("sidebarEditorEntry_" + record.index, listNode.width - 16, {
		title: record.entryType === "separator" ? translate("Separator", language) : record.title,
		subtitle: record.searchType,
		depth: record.displayDepth || record.depth || 0,
		icon: record.glyph || record.icon || "link",
		accent: record.accent || "",
		hasChildren: record.entryType === "section",
		expanded: record.expanded
	}, {
		selected: record.index === model.selected,
		enabled: !model.busy && !ui.confirmation,
		dim: !record.isVisible || record.included === false,
		select: {
			type: "select",
			index: record.index
		},
		keys: [
			"ArrowUp",
			"ArrowDown",
			"ArrowLeft",
			"ArrowRight",
			"Home",
			"End"
		].reduce((keys, key) => {
			keys[key] = {
				type: "treeKey",
				index: record.index,
				key
			};
			return keys;
		}, {}),
		toggle: {
			type: "toggle",
			index: record.index
		},
		toggleEnabled: !model.busy,
		toggleLabel: translate(record.expanded ? "Collapse section" : "Expand section", language),
		ids: {
			icon: "sidebarEntryIcon_" + record.index,
			title: "sidebarEntryTitle_" + record.index,
			detail: "sidebarEntryType_" + record.index,
			toggle: "sidebarEntryToggle_" + record.index
		}
	});
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.state.mjs
var initial = () => ({
	page: "item",
	mode: "simple",
	editing: false,
	treeWidth: 350,
	confirmation: "",
	text: {},
	xml: null
});
var pending = (ui) => Object.keys(ui.text).length > 0 || ui.xml !== null;
function completed(ui, command) {
	if (command.type === "help") return Object.assign({}, ui);
	if (["reload", "discard"].indexOf(command.type) >= 0) return Object.assign(initial(), { treeWidth: ui.treeWidth });
	const next = Object.assign({}, ui, {
		text: {},
		xml: null
	});
	if (command.type === "mode") next.mode = command.value;
	if (command.type === "back") next.editing = false;
	return next;
}
function transition(ui, model, event) {
	if (event.type === "treeKey") {
		const rows = model.entries.map((record) => ({
			id: String(record.index),
			depth: record.displayDepth || record.depth || 0,
			hasChildren: record.entryType === "section",
			expanded: record.expanded
		}));
		const action = navigate(rows, String(event.index), event.key);
		if (!action) return {
			ui: Object.assign({}, ui),
			commands: []
		};
		const result = transition(ui, model, {
			type: action.type === "select" ? "select" : "toggle",
			index: Number(action.id)
		});
		result.ui.editing = ui.editing;
		return result;
	}
	const next = Object.assign({}, ui), commands = [], allow = policy(model);
	if (event.type === "confirm" && ui.confirmation === "delete") {
		next.confirmation = "";
		if (allow.editable && model.selected >= 0) commands.push({ type: "delete" });
		return {
			ui: next,
			commands
		};
	}
	const doc = documentEvent(ui, model, event);
	if (doc) return doc;
	if (event.type === "applied") {
		next.text = {};
		next.xml = null;
		return {
			ui: next,
			commands
		};
	}
	if (event.type === "reset") return {
		ui: Object.assign(initial(), { treeWidth: ui.treeWidth }),
		commands
	};
	if (model.busy || model.uncertain || next.confirmation) return {
		ui: next,
		commands
	};
	switch (event.type) {
		case "split":
			next.treeWidth = Math.max(280, event.value);
			break;
		case "text":
			if (allow.editable) {
				next.text = Object.assign({}, ui.text);
				if (String(event.value) === String(model.entry[event.field] || "")) delete next.text[event.field];
				else next.text[event.field] = event.value;
			}
			break;
		case "xml":
			if (allow.editable) next.xml = event.value === model.xml ? null : event.value;
			break;
		case "page":
			if ([
				"item",
				"access",
				"technical"
			].indexOf(event.value) >= 0) {
				next.page = event.value;
				commands.push({ type: "apply" });
			}
			break;
		case "mode":
			if (["simple", "xml"].indexOf(event.value) >= 0) commands.push({
				type: "mode",
				value: event.value
			});
			break;
		case "select":
			if (model.entries.some((row) => row.index === event.index)) {
				next.editing = true;
				commands.push({
					type: "select",
					index: event.index
				});
			}
			break;
		case "back":
			commands.push({ type: "back" });
			break;
		case "toggle":
			commands.push({
				type: "toggle",
				index: event.index
			});
			break;
		case "source":
			if (["handler", "tactic"].indexOf(event.value) >= 0) commands.push({
				type: "source",
				value: event.value
			});
			break;
		case "preview":
			commands.push({
				type: "preview",
				value: event.value
			});
			break;
		case "add":
			if (allow.editable && [
				"link",
				"section",
				"separator"
			].indexOf(event.value) >= 0) {
				next.editing = true;
				commands.push({
					type: "add",
					value: event.value
				});
			}
			break;
		case "delete":
			if (allow.editable && model.selected >= 0) next.confirmation = "delete";
			break;
		case "field":
			if (allow.editable && model.selected >= 0) commands.push({
				type: "field",
				field: event.field,
				value: event.value
			});
			break;
		case "group":
			if (allow.editable) commands.push({
				type: "group",
				code: event.code,
				value: event.value
			});
			break;
		case "move":
			if (allow.editable) commands.push({
				type: "move",
				value: event.value
			});
			break;
		case "apply":
			if (allow.editable) commands.push({ type: "apply" });
			break;
		case "pageLayout":
		case "groups":
		case "search":
			if (allow.editable && !model.dirty) commands.push({ type: event.type });
			break;
		case "help":
			commands.push({ type: "help" });
			break;
		default: throw Error("Unsupported Sidebar event: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region src/features/administration/SidebarEditor.vue
var _sfc_main = {
	inheritAttrs: false,
	inject: ["openHelp"],
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
	emits: [
		"saved",
		"configure-search",
		"manage-groups",
		"page-layout"
	],
	data() {
		return {
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			dispatching: false,
			draft: null,
			projectTitle: "",
			context: null,
			baseline: "",
			revision: "",
			library: [],
			searchTypes: [],
			busy: false,
			error: "",
			uncertain: false,
			page: "item",
			mode: "simple",
			xml: "",
			xmlBaseline: "",
			request: 0,
			confirmation: "",
			textChanges: {}
		};
	},
	computed: {
		frameModel() {
			return {
				ready: !!this.draft,
				projectTitle: this.projectTitle || this.project,
				canWrite: this.validContext,
				canLoad: !!this.ticket,
				busy: this.busy || this.dispatching,
				dirty: !!this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				selected: this.draft?.selected ?? -1,
				entry: this.entry,
				source: this.draft?.source || "handler",
				previewGroup: this.draft?.previewGroup || "",
				xml: this.xmlBaseline,
				entries: (this.draft?.entries || []).map((row, index) => ({
					...row,
					index,
					accent: this.searchTypes.find((type) => type.value === row.searchType)?.color || row.accent || ""
				})).filter((row) => row.entryVisible),
				groups: this.draft?.groups || [],
				previewOptions: [{
					value: "",
					label: t("All groups")
				}, ...(this.draft?.groups || []).map((row) => ({
					value: row.code,
					label: row.label
				}))],
				typeOptions: this.typeOptions,
				presetOptions: this.presets,
				resultOptions: this.resultViews.map((row) => ({
					...row,
					label: t(row.label)
				})),
				widgetOptions: this.widgetTypes.map((row) => ({
					...row,
					label: t(row.label)
				})),
				layoutOptions: this.layouts,
				shelfOptions: this.shelves
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		models() {
			return {
				entries: this.frameModel.entries,
				groups: this.frameModel.groups.map((row, index) => ({
					...row,
					index
				}))
			};
		},
		state() {
			return this.draft ? Object.fromEntries([
				"documents",
				"selected",
				"source",
				"collapsed",
				"updates",
				"previewGroup"
			].map((key) => [key, this.draft[key]])) : null;
		},
		dirty() {
			return this.uncertain || this.draft && (pending(this.ui) || Object.keys(this.textChanges).length || JSON.stringify([this.draft.documents, this.draft.updates]) !== this.baseline || this.xml !== this.xmlBaseline);
		},
		entry() {
			return this.draft?.entries[this.draft.selected] || {};
		},
		validContext() {
			return this.context?.ticket === this.ticket && this.context?.project === this.project;
		},
		editable() {
			return !!this.draft && this.validContext && !this.busy && !this.uncertain;
		},
		typeOptions() {
			return [{
				value: "",
				label: t("Select Search Type")
			}, ...this.searchTypes];
		},
		presets() {
			const type = this.entry.searchType?.split("?")[0] || "";
			const options = this.library.filter((row) => row.search_type === type && row.view.startsWith("link_search:") && (row.view.split(":")[2] === type || row.view.split(":")[2]?.startsWith(type + "@"))).map((row) => ({
				value: row.view,
				label: row.title || row.view
			}));
			return this.options(options, this.entry.searchView, "No predefined search");
		},
		layouts() {
			return this.options(this.library.filter((row) => row.category === "workspace_layout").map((row) => ({
				value: row.view,
				label: row.title || row.view
			})), this.entry.layoutPreset, "Do not change workspace layout");
		},
		shelves() {
			return this.options(this.library.filter((row) => row.category === "script_shelf").map((row) => ({
				value: row.view,
				label: row.title || row.view
			})), this.entry.scriptShelf, "Project default shelf");
		},
		resultViews() {
			return [
				["continious", "Continuous tree"],
				["tiles", "Cards"],
				["table", "Table"],
				["compact", "Compact rows"],
				["splitted_vertical", "Versions on the right"],
				["splitted_horizontal", "Versions at the bottom"]
			].map(([value, label]) => ({
				value,
				label
			}));
		},
		widgetTypes() {
			return [
				["view_panel", "Layout with Search"],
				["custom_layout", "Custom Layout"],
				["edit_layout", "Edit Layout"],
				["tile_layout", "Tile Layout"],
				["fast_layout", "Fast Table Layout"],
				["__class__", "Class Path"]
			].map(([value, label]) => ({
				value,
				label
			}));
		}
	},
	watch: {
		project() {
			this.reload();
		},
		ticket() {
			this.request++;
			this.draft = null;
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
		this.observer.observe(this.toolbarTarget ? this.$el.closest("dialog") || this.$refs.body.parentElement : this.$refs.body.parentElement);
	},
	beforeUnmount() {
		this.request++;
		this.observer?.disconnect();
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		rowScene(node, record) {
			return row(node, record, this.frameModel, this.ui, appearance.language);
		},
		async applyFrameText() {
			this.textChanges = { ...this.ui.text };
			this.xml = this.ui.xml === null ? this.xmlBaseline : this.ui.xml;
			if (!await this.applyXml()) return false;
			this.ui = transition(this.ui, this.frameModel, { type: "applied" }).ui;
			return true;
		},
		async dispatch(event) {
			if (this.dispatching) return;
			const result = transition(this.ui, this.frameModel, event);
			this.dispatching = true;
			try {
				for (const command of result.commands) {
					if (![
						"reload",
						"discard",
						"help"
					].includes(command.type) && !await this.applyFrameText()) return;
					switch (command.type) {
						case "apply": break;
						case "select":
							await this.select(command.index);
							break;
						case "toggle":
							await this.select(command.index, true);
							break;
						case "source":
							await this.source(command.value);
							break;
						case "preview":
							await this.previewGroup(command.value);
							break;
						case "mode":
							await this.setMode(command.value);
							break;
						case "back": break;
						case "field":
							await this.field(command.field, command.value);
							break;
						case "group":
							await this.edit("group", {
								field: command.code,
								value: command.value
							});
							break;
						case "add":
							await this.add(command.value);
							break;
						case "move":
							await this.operate("move", { value: command.value });
							break;
						case "delete":
							await this.operate("delete");
							break;
						case "pageLayout":
							this.$emit("page-layout", this.entry.displayView.slice(10));
							break;
						case "search":
							this.$emit("configure-search", this.entry);
							break;
						case "groups":
							this.$emit("manage-groups");
							break;
						case "help":
							this.openHelp("sidebar_editor");
							break;
						case "save":
							await this.save();
							break;
						case "discard":
						case "reload":
							await this.reload(true);
							break;
						default: throw Error("Unsupported Sidebar command: " + command.type);
					}
					if (this.error && !["reload", "discard"].includes(command.type)) return;
					result.ui = completed(result.ui, command);
				}
				this.ui = result.ui;
			} finally {
				this.dispatching = false;
				if (event.type === "treeKey" && !this.error) {
					await nextTick();
					this.$refs.frame?.focusControl("sidebarEditorEntry_" + this.frameModel.selected);
				}
			}
		},
		t,
		options(rows, value, empty) {
			return [
				{
					value: "",
					label: t(empty)
				},
				...rows,
				...value && !rows.some((row) => row.value === value) ? [{
					value,
					label: value
				}] : []
			];
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.dirty || this.busy || this.uncertain) {
				this.error = "Save or discard sidebar changes before leaving.";
				return false;
			}
			return true;
		},
		accept(result, loaded = false) {
			this.draft = result;
			this.xml = this.xmlBaseline = result.xml;
			if (loaded) {
				this.projectTitle = result.projectTitle || this.project;
				this.revision = result.revision;
				this.library = result.library;
				this.searchTypes = result.searchTypes;
				this.baseline = JSON.stringify([result.documents, result.updates]);
			}
		},
		async reload(force = false) {
			if (this.busy) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.confirmation = "reload";
				return;
			}
			const request = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			this.confirmation = "";
			try {
				const result = await sidebarRequest("read", this.context.ticket, this.context.project);
				if (request !== this.request) return;
				this.accept(result, true);
				this.uncertain = false;
				this.mode = "simple";
				this.textChanges = {};
				this.ui = initial();
			} catch (error) {
				this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		async edit(operation, values = {}, state = this.state) {
			if (!this.editable) return false;
			this.busy = true;
			this.error = "";
			const request = this.request;
			try {
				const result = await sidebarRequest("edit", this.context.ticket, this.context.project, {
					state,
					operation,
					...values
				});
				if (request !== this.request) return false;
				this.accept(result);
				return true;
			} catch (error) {
				this.error = error.message;
				return false;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		async flushText() {
			for (const [field, value] of Object.entries(this.textChanges)) {
				if (!await this.edit("field", {
					field,
					value
				})) return false;
				delete this.textChanges[field];
			}
			return true;
		},
		async applyXml() {
			return await this.flushText() && (this.xml === this.xmlBaseline || await this.edit("xml", { xml: this.xml }));
		},
		async select(index, toggle = false) {
			if (await this.applyXml()) await this.edit(toggle ? "toggle" : "select", {}, {
				...this.state,
				selected: index
			});
		},
		async source(value) {
			if (await this.applyXml()) await this.edit("select", {}, {
				...this.state,
				source: value,
				selected: -1
			});
		},
		async previewGroup(value) {
			if (await this.applyXml()) await this.edit("select", {}, {
				...this.state,
				previewGroup: value
			});
		},
		async setMode(value) {
			if (await this.applyXml()) this.mode = value;
		},
		async field(field, value) {
			if (await this.applyXml()) return this.edit("field", {
				field,
				value
			});
		},
		async operate(operation, values = {}) {
			if (await this.applyXml()) await this.edit(operation, values);
		},
		async add(value) {
			if (await this.applyXml()) await this.edit("add", { value });
		},
		discard() {
			this.confirmation = "discard";
		},
		async refreshLibrary() {
			const context = this.context, request = this.request;
			try {
				const result = await sidebarRequest("read", context.ticket, context.project);
				if (request !== this.request || context !== this.context) return;
				this.library = result.library;
				if (!this.dirty && JSON.stringify(result.documents) === JSON.stringify(this.draft.documents)) this.revision = result.revision;
			} catch (error) {
				this.error = error.message;
			}
		},
		async save() {
			if (!this.editable || !this.dirty || !await this.applyXml()) return;
			this.busy = true;
			this.error = "";
			const request = this.request;
			try {
				const result = await sidebarRequest("save", this.context.ticket, this.context.project, {
					state: this.state,
					revision: this.revision
				});
				if (request !== this.request) return;
				this.accept(result, true);
				this.$emit("saved", result);
			} catch (error) {
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Reload sidebar before trying again." : error.message;
			} finally {
				if (request === this.request) this.busy = false;
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
	return openBlock(), createElementBlock("section", mergeProps(_ctx.$attrs, {
		class: "sidebar-editor frame-host",
		"aria-busy": $data.busy
	}), [(openBlock(), createBlock(Teleport, {
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
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"onEvent"
	])], 512)], 16, _hoisted_1);
}
var SidebarEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { SidebarEditor_default as default };

//# sourceMappingURL=SidebarEditor.js.map
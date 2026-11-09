import { I as resolveComponent, N as openBlock, c as vShow, g as createBlock, h as createBaseVNode, p as Teleport, q as withDirectives, rt as normalizeStyle, v as createElementBlock, x as createVNode } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { u as columnsEditor } from "./index.js";
import { K as button, T as translate, U as observeFrameSizes, X as node, Y as muted, Z as rect, q as label, t as _sfc_main$1 } from "./FrameView.js";
import { n as sections, t as captionHeight } from "./sections.ui.js";
import { a as tabs, n as notices, o as toolbar, r as policy, t as documentEvent } from "./admin.document.js";
import { a as widgetOptionsFor, r as definitionWizard, t as changeDefinition } from "./RelatedObjects.js";
//#region ../src/tactic_stream/shared_ui/features/administration/columns/columns.state.mjs
var initial = () => ({
	query: "",
	searchType: "",
	mode: "simple",
	viewMode: "view",
	path: "",
	editing: false,
	showAllWidgets: false,
	catalogVisible: true,
	catalogWidth: 350,
	columnWidth: 250,
	columnHeight: 170,
	collapsedCategories: {},
	expandedLayers: {},
	colorsOpen: false,
	configsOpen: true,
	confirmation: "",
	text: {}
});
var pending = (ui) => Object.keys(ui.text).length > 0;
function elementFieldValue(element, field) {
	if (!element) return "";
	if (field === "title") return element.rawTitle !== void 0 ? String(element.rawTitle || "") : String(element.title || "");
	if (field === "extraOptionAdd") return "";
	if (field.indexOf("option:") === 0) return String(element.displayOptions && element.displayOptions[field.slice(7)] || "");
	if (field.indexOf("editOption:") === 0) return String(element.editOptions && element.editOptions[field.slice(11)] || "");
	if (field.indexOf("actionOption:") === 0) return String(element.actionOptions && element.actionOptions[field.slice(13)] || "");
	return String(element[field] ?? "");
}
function definitionSource(records, request, elements) {
	const views = request.view === "edit_definition" ? ["edit_definition"] : [request.view || "table", "definition"];
	const candidates = records.filter((row) => row.searchType === request.searchType && views.indexOf(row.view) >= 0);
	candidates.sort((left, right) => views.indexOf(left.view) - views.indexOf(right.view) || Number(right.code === request.code) - Number(left.code === request.code) || Number(!!left.login) - Number(!!right.login));
	if (!request.column) return candidates[0] || null;
	let reference = null;
	for (const row of candidates) {
		const column = elements(row).find((item) => item.name === request.column);
		if (!column) continue;
		if (column.widget) return row;
		if (!reference) reference = row;
	}
	return reference;
}
function selected(ui, elements, name) {
	const column = elements.find((row) => row.name === name) || elements[0];
	return Object.assign({}, ui, {
		text: {},
		path: column ? column.path : ""
	});
}
function completed(ui, command, model) {
	const next = Object.assign({}, ui, { text: {} });
	if ([
		"select",
		"filter",
		"reload",
		"discard"
	].indexOf(command.type) >= 0) next.path = model.element.path || "";
	if (command.type === "column") next.path = command.path;
	if (command.type === "mode") next.mode = command.value;
	if (command.type === "back") next.editing = false;
	if (command.type === "change") {
		if (command.field === "move") next.path = (model.elements.find((row) => row.name === command.name) || model.element).path;
		else if (command.field === "addElement") next.path = (model.elements.find((row) => row.name === command.value) || model.element).path;
		else if (command.field === "removeElement") next.path = model.elements[0] ? model.elements[0].path : "";
		else if (String(next.path || "").indexOf("def:") === 0) {
			const addedName = String(next.path).slice(4);
			const found = model.elements.find((row) => row.name === addedName);
			if (found) next.path = found.path;
		}
	}
	return next;
}
function transition(ui, model, event) {
	const document = documentEvent(ui, model, event);
	if (document) return document;
	const next = Object.assign({}, ui), commands = [], allow = policy(model);
	if (event.type === "applied") {
		next.text = {};
		return {
			ui: next,
			commands
		};
	}
	if (model.busy || ui.confirmation) return {
		ui: next,
		commands
	};
	switch (event.type) {
		case "split":
			if ([
				"catalogWidth",
				"columnWidth",
				"columnHeight"
			].indexOf(event.field) >= 0) next[event.field] = event.value;
			break;
		case "catalogVisible":
			next.catalogVisible = next.catalogVisible === false;
			break;
		case "query":
		case "searchType":
			if (!model.dirty && !model.uncertain) {
				next[event.type] = event.value;
				commands.push({ type: "filter" });
			}
			break;
		case "select":
			if (!model.dirty && !model.uncertain) {
				next.editing = true;
				commands.push({
					type: "select",
					identity: event.identity
				});
			}
			break;
		case "back":
			commands.push({ type: "back" });
			break;
		case "mode":
			if (["xml", "simple"].indexOf(event.value) >= 0) commands.push({
				type: "mode",
				value: event.value
			});
			break;
		case "viewMode":
			if (["view", "edit"].indexOf(event.value) >= 0) next.viewMode = event.value;
			break;
		case "toggleCategory":
			if (event.key) next.collapsedCategories = Object.assign({}, ui.collapsedCategories, { [event.key]: !ui.collapsedCategories[event.key] });
			break;
		case "toggleLayer":
			if (event.key) next.expandedLayers = Object.assign({}, ui.expandedLayers, { [event.key]: !ui.expandedLayers[event.key] });
			break;
		case "toggleSection":
			if (event.section === "colors") next.colorsOpen = !ui.colorsOpen;
			else if (event.section === "configs") next.configsOpen = !ui.configsOpen;
			break;
		case "column":
			if (model.elements.some((row) => row.path === event.path) || (model.definitionElements || []).some((row) => row.path === event.path)) commands.push({
				type: "column",
				path: event.path
			});
			break;
		case "addElement":
			if (allow.editable && event.name) commands.push({
				type: "change",
				field: "addElement",
				value: event.name
			});
			break;
		case "removeElement":
			if (allow.editable && model.elements.length > 1 && model.element && model.element.inView !== false) commands.push({
				type: "change",
				field: "removeElement",
				value: model.element.name
			});
			break;
		case "text":
			if (allow.editable) {
				next.text = Object.assign({}, ui.text);
				if (String(event.value) === elementFieldValue(model.element, event.field)) delete next.text[event.field];
				else next.text[event.field] = event.value;
			}
			break;
		case "commit":
			if (allow.editable && pending(ui)) commands.push({ type: "apply" });
			break;
		case "field":
			if (allow.editable) commands.push({
				type: "change",
				field: event.field,
				value: event.value
			});
			break;
		case "move": {
			const index = model.elements.findIndex((row) => row.path === model.element.path);
			if (allow.editable && !pending(ui) && index >= 0 && (event.value === -1 || event.value === 1) && model.elements[index + event.value]) commands.push({
				type: "change",
				field: "move",
				value: event.value,
				name: model.element.name
			});
			break;
		}
		case "step":
			if (allow.editable) commands.push({
				type: "change",
				field: "width",
				value: Math.max(48, Math.min(640, (Number(ui.text.width || model.element.width) || 160) + event.value))
			});
			break;
		case "xml":
			if (allow.editable) commands.push({
				type: "xml",
				value: event.value
			});
			break;
		case "showAllWidgets":
			next.showAllWidgets = Boolean(event.value);
			break;
		default: throw Error("Unsupported Columns event: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/columns/widget_args.mjs
var DISPLAY_WIDGET_ARGS = [
	{
		value: "",
		class: "tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg",
		aliases: [
			"",
			"tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg",
			"SimpleTableElementWdg",
			"TextWdg",
			"pyasm.widget.TextWdg",
			"tactic.ui.common.SimpleTableElementWdg",
			"pyasm.widget.SimpleTableElementWdg",
			"pyasm.widget.table_element_wdg.SimpleTableElementWdg",
			"pyasm.widget.input_wdg.TextWdg",
			"tactic.ui.common.base_table_element_wdg.RawTableElementWdg",
			"tactic.ui.common.RawTableElementWdg"
		],
		options: [{
			name: "column",
			title: "Column",
			description: "Database column override to display in this cell",
			category: "Display",
			order: 1,
			type: "TextWdg"
		}]
	},
	{
		value: "format",
		class: "tactic.ui.table.format_element_wdg.FormatElementWdg",
		aliases: [
			"format",
			"tactic.ui.table.format_element_wdg.FormatElementWdg",
			"FormatElementWdg",
			"tactic.ui.table.FormatElementWdg"
		],
		options: [
			{
				name: "type",
				title: "Type",
				description: "Determines the type it should be displayed as",
				category: "Required",
				order: 1,
				type: "tactic.ui.manager.FormatDefinitionEditWdg",
				values: [
					"integer",
					"float",
					"percent",
					"currency",
					"date",
					"time",
					"scientific",
					"boolean",
					"text",
					"timecode"
				],
				default: "text"
			},
			{
				name: "format",
				title: "Format",
				description: "Format pattern (e.g. -1234.12, YYYY-MM-DD, Checkbox)",
				category: "Required",
				order: 2,
				type: "TextWdg"
			},
			{
				name: "total_summary",
				title: "Total Summary",
				description: "Determines a calculation for the bottom row",
				category: "Misc",
				order: 2,
				type: "SelectWdg",
				values: [
					"count",
					"total",
					"average"
				]
			},
			{
				name: "constraint",
				title: "Constraint",
				description: "Determines what kind of index is put onto the created column",
				category: "Misc",
				order: 3,
				type: "SelectWdg",
				values: ["unique", "indexed"]
			},
			{
				name: "fps",
				title: "Fps",
				description: "Frames per second for timecode formatting (e.g. 24, 25, 30)",
				category: "Misc",
				order: 4,
				type: "TextWdg"
			}
		]
	},
	{
		value: "expression",
		class: "tactic.ui.table.expression_element_wdg.ExpressionElementWdg",
		aliases: [
			"expression",
			"tactic.ui.table.expression_element_wdg.ExpressionElementWdg",
			"ExpressionElementWdg",
			"tactic.ui.table.ExpressionElementWdg",
			"expression_value",
			"ExpressionValueElementWdg",
			"tactic.ui.table.ExpressionValueElementWdg",
			"tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg"
		],
		options: [
			{
				name: "use_cache",
				title: "Use Cache",
				description: "Determines whether or not to use the cached value. Gets value from column with the same name as the element",
				category: "Cache",
				order: 0,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "expression",
				title: "Expression",
				description: "Expression to evaluate the widget",
				category: "Options",
				order: 1,
				type: "TextAreaWdg"
			},
			{
				name: "display_expression",
				title: "Display Expression",
				description: "Expression for display purposes",
				category: "Options",
				order: 2,
				type: "TextAreaWdg"
			},
			{
				name: "display_format",
				title: "Display Format",
				description: "Predefined format for display",
				category: "Options",
				order: 3,
				type: "TextWdg"
			},
			{
				name: "link_expression",
				title: "Link Expression",
				description: "Expression for linking to another sobject",
				category: "Options",
				order: 4,
				type: "TextAreaWdg"
			},
			{
				name: "link_view",
				title: "Link View",
				description: "View to link result to another view",
				category: "Options",
				order: 5,
				type: "TextWdg"
			},
			{
				name: "order_by",
				title: "Order By",
				description: "Turn on Order by",
				category: "Options",
				order: 8,
				type: "TextWdg"
			},
			{
				name: "show_retired",
				title: "Show Retired",
				description: "true|false - true shows all the retired entries during the expression evaluation",
				category: "Options",
				order: 8,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "group_by",
				title: "Group By",
				description: "Turn on Group by",
				category: "Options",
				order: 9,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "group_by_time",
				title: "Group By Time",
				description: "Turn on Group by",
				category: "Options",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "justify",
				title: "Justify",
				description: "Result justification",
				category: "Options",
				order: 11,
				type: "SelectWdg",
				values: [
					"default",
					"left",
					"right",
					"center"
				]
			},
			{
				name: "filter_name",
				title: "Filter Name",
				description: "Name of filter to use",
				category: "Options",
				order: 12,
				type: "TextWdg"
			},
			{
				name: "mode",
				title: "Mode",
				description: "Display mode for this widget",
				category: "Other Options",
				order: 3,
				type: "SelectWdg",
				values: [
					"value",
					"check",
					"boolean"
				]
			},
			{
				name: "expression_mode",
				title: "Expression Mode",
				description: "If absolute mode is selected, it does not relate to the current SObject",
				category: "Other Options",
				order: 6,
				type: "SelectWdg",
				values: ["default", "absolute"]
			},
			{
				name: "calc_mode",
				title: "Calc Mode",
				description: "(ALPHA) fast|slow - fast uses new calculation mode. Only @SUM, @COUNT, @SOBJECT and @GET are current supported",
				category: "Other Options",
				order: 7,
				type: "SelectWdg",
				values: ["slow", "fast"]
			},
			{
				name: "bottom",
				title: "Bottom",
				description: "Expression to calculate the bottom row of the table",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "empty",
				title: "Empty",
				description: "vAlue to display if empty",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "group_bottom",
				title: "Group Bottom",
				description: "Expression to calculate the bottom of a group",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "inline_styles",
				title: "Inline Styles",
				description: "Styles to add to the DIV generated that contains the result of the expression",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "return",
				title: "Return",
				description: "",
				category: "Other Options",
				order: 99,
				type: "SelectWdg",
				values: ["single", "list"]
			}
		]
	},
	{
		value: "link",
		class: "tactic.ui.table.link_element_wdg.LinkElementWdg",
		aliases: [
			"link",
			"tactic.ui.table.link_element_wdg.LinkElementWdg",
			"LinkElementWdg",
			"tactic.ui.table.LinkElementWdg"
		],
		options: [{
			name: "empty",
			title: "Empty",
			description: "Text for an empty link",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}, {
			name: "icon",
			title: "Icon",
			description: "Icon to display",
			category: "Other Options",
			order: 99,
			type: "IconSelectWdg"
		}]
	},
	{
		value: "pyasm.widget.ThumbWdg",
		class: "pyasm.widget.file_wdg.ThumbWdg",
		aliases: [
			"pyasm.widget.ThumbWdg",
			"pyasm.widget.file_wdg.ThumbWdg",
			"ThumbWdg"
		],
		options: [
			{
				name: "script_path",
				title: "Script Path",
				description: "Javascript path override for action when preview is clicked",
				category: "Action",
				order: 1,
				type: "TextWdg"
			},
			{
				name: "detail_class_name",
				title: "Detail Class Name",
				description: "Python widget to display in a new tab when preview is clicked",
				category: "Action",
				order: 2,
				type: "TextWdg"
			},
			{
				name: "icon_context",
				title: "Icon Context",
				description: "context on which the search is applied",
				category: "Display",
				order: 1,
				type: "TextWdg"
			},
			{
				name: "icon_size",
				title: "Icon Size",
				description: "control the icon size by percentage. e.g. 80%",
				category: "Display",
				order: 2,
				type: "TextWdg"
			},
			{
				name: "min_icon_size",
				title: "Min Icon Size",
				description: "The smallest size the icon will become on resize",
				category: "Display",
				order: 3,
				type: "TextWdg"
			},
			{
				name: "latest_icon",
				title: "Latest Icon",
				description: "whether to display the latest version under any context",
				category: "Display",
				order: 4,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "filename",
				title: "Filename",
				description: "whether to display the main file name for download",
				category: "Display",
				order: 5,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "original",
				title: "Original",
				description: "whether to display the original file when clicked on",
				category: "Display",
				order: 6,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "file_type",
				title: "File Type",
				description: "whether to display the file type for download",
				category: "Display",
				order: 7,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "detail",
				title: "Detail",
				description: "whether to display the single asset view when clicked on",
				category: "Display",
				order: 8,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "protocol",
				title: "Protocol",
				description: "whether to open the link over http or file system",
				category: "Display",
				order: 9,
				type: "SelectWdg",
				values: ["http", "file"]
			},
			{
				name: "cascade_search",
				title: "Cascade Search",
				description: "determines whether to keep looking for any image to use as an icon",
				category: "Display",
				order: 99,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "search_key",
				title: "Search Key",
				description: "search_key of sobject to use for displaying icon",
				category: "Search",
				order: 0,
				type: "TextWdg"
			},
			{
				name: "redirect_expr",
				title: "Redirect Expr",
				description: "expression to control another image related to this sobject. This is slower in performance. e.g. @SOBJECT(project/entity)",
				category: "Search",
				order: 1,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.widget.DiscussionElementWdg",
		class: "tactic.ui.widget.discussion_wdg.DiscussionElementWdg",
		aliases: [
			"tactic.ui.widget.DiscussionElementWdg",
			"tactic.ui.widget.discussion_wdg.DiscussionElementWdg",
			"DiscussionElementWdg"
		],
		options: [
			{
				name: "process",
				title: "Process",
				description: "Explicitly set the process for notes that can be added.",
				category: "Options",
				order: 0,
				type: "TextWdg"
			},
			{
				name: "context",
				title: "Context",
				description: "Explicitly set the context(s) for notes that can be added. This can be a list separated by commas",
				category: "Options",
				order: 1,
				type: "TextWdg"
			},
			{
				name: "use_parent",
				title: "Use Parent",
				description: "Determine whether or not to enter notes for parent sObject",
				category: "Options",
				order: 2,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_fullscreen_button",
				title: "Show Fullscreen Button",
				description: "Determine whether or not to show the expand notes icon button",
				category: "Options",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "note_format",
				title: "Note Format",
				description: "Determine if the notes are shown in compact or full mode. Full- shows thumbnail, login-info, email and notes. Compact- shows just the notes.",
				category: "Options",
				order: 4,
				type: "SelectWdg",
				values: ["compact", "full"]
			},
			{
				name: "show_note_status",
				title: "Show Note Status",
				description: "Determine whether or not to show the note status in abbreviated form.",
				category: "Options",
				order: 5,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_context_notes",
				title: "Show Context Notes",
				description: "(DEPRECATED) Determine if the notes in the context are hidden",
				category: "Options",
				order: 6,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "note_expandable",
				title: "Note Expandable",
				description: "Determine whether or not a note is expandable. True- shows a short version of the note that can be expanded. False- shows the full note",
				category: "Options",
				order: 7,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "append_process",
				title: "Append Process",
				description: "Append a list of comma separated processes in addition of the ones defined in the pipeline",
				category: "Options",
				order: 8,
				type: "TextWdg"
			},
			{
				name: "allow_email",
				title: "Allow Email",
				description: "Allow email to be sent out directly in this widget",
				category: "Options",
				order: 9,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "dialog_position",
				title: "Dialog Position",
				description: "Determine where the popup dialog will appear for the nots",
				category: "Options",
				order: 10,
				type: "SelectWdg",
				values: ["side", "center"]
			},
			{
				name: "mode",
				title: "Mode",
				description: "Determine if the table shows small icons or process names",
				category: "Options",
				order: 10,
				type: "SelectWdg",
				values: ["default", "icon"]
			},
			{
				name: "show_task_process",
				title: "Show Task Process",
				description: "Determine if Add Note widget only shows the processes of existing tasks",
				category: "Options",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			}
		]
	},
	{
		value: "tactic.ui.table.SObjectDetailElementWdg",
		class: "tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg",
		aliases: [
			"tactic.ui.table.SObjectDetailElementWdg",
			"tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg",
			"SObjectDetailElementWdg"
		],
		options: [
			{
				name: "show_default_elements",
				title: "Show Default Elements",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_task_process",
				title: "Show Task Process",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "tab_element_names",
				title: "Tab Element Names",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "use_parent",
				title: "Use Parent",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.CheckinButtonElementWdg",
		class: "tactic.ui.table.table_element_wdg.CheckinButtonElementWdg",
		aliases: [
			"tactic.ui.table.CheckinButtonElementWdg",
			"tactic.ui.table.table_element_wdg.CheckinButtonElementWdg",
			"CheckinButtonElementWdg"
		],
		options: [
			{
				name: "transfer_mode",
				title: "Transfer Mode",
				description: "Mode by which files are transferred to the server",
				category: "1. Modes",
				order: 1,
				type: "SelectWdg",
				values: [
					"upload",
					"copy",
					"move",
					"local"
				]
			},
			{
				name: "use_applet",
				title: "Use Applet",
				description: "Determines which sobject to check into",
				category: "1. Modes",
				order: 2,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "mode",
				title: "Mode",
				description: "Determines whether this widget can only check-in sequences, file, or directory",
				category: "1. Modes",
				order: 3,
				type: "SelectWdg",
				values: [
					"sequence",
					"file",
					"dir",
					"multi_file",
					"add"
				]
			},
			{
				name: "checkin_script_path",
				title: "Checkin Script Path",
				description: "Path to the check-in script",
				category: "2. Display",
				order: 3,
				type: "TextWdg"
			},
			{
				name: "validate_script_path",
				title: "Validate Script Path",
				description: "Path to the validation script",
				category: "2. Display",
				order: 4,
				type: "TextWdg"
			},
			{
				name: "process",
				title: "Process",
				description: "Process under which the check-in occurs",
				category: "2. Display",
				order: 5,
				type: "TextWdg"
			},
			{
				name: "lock_process",
				title: "Lock Process",
				description: "If turned on, the process specified cannot be changed by the user",
				category: "2. Display",
				order: 6,
				type: "CheckboxWdg"
			},
			{
				name: "width",
				title: "Width",
				description: "Width of the widget",
				category: "2. Display",
				order: 7,
				type: "TextWdg"
			},
			{
				name: "show_context",
				title: "Show Context",
				description: "Determines whether to show the context selector",
				category: "2. Display",
				order: 8,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "sobject_mode",
				title: "Sobject Mode",
				description: "Determines which sobject to check into",
				category: "2. Display",
				order: 8,
				type: "SelectWdg",
				values: [
					"parent",
					"connect",
					"sobject"
				]
			},
			{
				name: "checkin_options_view",
				title: "Checkin Options View",
				description: "Custom layout view which defines a custom check-in options UI",
				category: "2. Display",
				order: 9,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.TaskElementWdg",
		class: "tactic.ui.table.task_element_wdg.TaskElementWdg",
		aliases: [
			"tactic.ui.table.TaskElementWdg",
			"tactic.ui.table.task_element_wdg.TaskElementWdg",
			"TaskElementWdg",
			"pyasm.widget.task_wdg.SObjectTaskTableElement",
			"SObjectTaskTableElement",
			"pyasm.widget.SObjectTaskTableElement"
		],
		options: [
			{
				name: "bg_color",
				title: "Bg Color",
				description: "Different modes of displaying the background color for each process",
				category: "Color",
				order: 2,
				type: "SelectWdg",
				values: ["status", "process"]
			},
			{
				name: "status_color",
				title: "Status Color",
				description: "Different modes of displaying status background color",
				category: "Color",
				order: 3,
				type: "SelectWdg",
				values: ["status", "process"]
			},
			{
				name: "context_color",
				title: "Context Color",
				description: "Different modes of displaying context background color",
				category: "Color",
				order: 4,
				type: "SelectWdg",
				values: ["status", "process"]
			},
			{
				name: "panel_width",
				title: "Panel Width",
				description: "Select the overall width for the panel layout",
				category: "Display",
				order: 6,
				type: "SelectWdg",
				values: [
					"35px",
					"50px",
					"75px",
					"100px",
					"125px"
				]
			},
			{
				name: "font_size",
				title: "Font Size",
				description: "font size of the text",
				category: "Display",
				order: 7,
				type: "SelectWdg",
				values: [
					"7",
					"8",
					"9",
					"10",
					"11",
					"12",
					"13",
					"14"
				]
			},
			{
				name: "show_process",
				title: "Show Process",
				description: "Flag for displaying the process of the tasks",
				category: "Display",
				order: 8,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_context",
				title: "Show Context",
				description: "Flag for displaying the context of the tasks",
				category: "Display",
				order: 9,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_assigned",
				title: "Show Assigned",
				description: "Flag for displaying the assigned user of the tasks",
				category: "Display",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_bid",
				title: "Show Bid",
				description: "Flag for displaying the bid duration tasks",
				category: "Display",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_status",
				title: "Show Status",
				description: "Flag for displaying the status of the tasks",
				category: "Display",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "assigned_label_attr",
				title: "Assigned Label Attr",
				description: "A list of | separated attributes displayed as the label of the assigned, e.g. \"first_name|last_name\"",
				category: "Display",
				order: 11,
				type: "TextWdg"
			},
			{
				name: "assigned_values_expr",
				title: "Assigned Values Expr",
				description: "An expression controlling what login values to show, e.g. @SOBJECT(sthpw/login['department','design'])",
				category: "Display",
				order: 12,
				type: "TextWdg"
			},
			{
				name: "show_dates",
				title: "Show Dates",
				description: "Flag for displaying the date range of the tasks",
				category: "Display",
				order: 13,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_track",
				title: "Show Track",
				description: "Flag for displaying a tip to dynamically load the information of the last status",
				category: "Display",
				order: 14,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_labels",
				title: "Show Labels",
				description: "Flag for displaying the label of the tasks",
				category: "Display",
				order: 15,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_border",
				title: "Show Border",
				description: "Flag for displaying a border around each task panel",
				category: "Display",
				order: 16,
				type: "SelectWdg",
				values: [
					"all",
					"one-sided",
					"none"
				]
			},
			{
				name: "collate_columns",
				title: "Collate Columns",
				description: "Flag to collate columns that have the same processes together .",
				category: "Display",
				order: 18,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_current_pipeline_only",
				title: "Show Current Pipeline Only",
				description: "Flag for displaying only the tasks associate with the current pipeline. Default to true.",
				category: "Display",
				order: 18,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_add_task",
				title: "Show Add Task",
				description: "Flag for displaying the add task button even if there are existing tasks. Defaults to false",
				category: "Display",
				order: 19,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_link_task_menu",
				title: "Show Link Task Menu",
				description: "Flag for displaying the task linking menu so one can virtually make a task shared by two or more people. Defaults to false",
				category: "Display",
				order: 20,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_processes_in_title",
				title: "Show Processes In Title",
				description: "Display the processes in title. You are advised to turn on show_filler_tasks as well. Defaults to false",
				category: "Display",
				order: 21,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_task_edit",
				title: "Show Task Edit",
				description: "Flag for displaying the edit icon for each task",
				category: "Display",
				order: 22,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "task_edit_view",
				title: "Task Edit View",
				description: "A custom view specified for editing the task in this widget. Defaults to edit",
				category: "Display",
				order: 23,
				type: "TextWdg",
				default: "edit"
			},
			{
				name: "task_filter",
				title: "Task Filter",
				description: "A filter on which type of tasks to display",
				category: "Display",
				order: 24,
				type: "SelectWdg",
				values: ["process_only", "context_only"]
			},
			{
				name: "layout",
				title: "Layout",
				description: "Determines layout for each process",
				category: "Mode",
				order: 1,
				type: "SelectWdg",
				values: [
					"panel",
					"vertical",
					"horizontal"
				]
			},
			{
				name: "show_filler_tasks",
				title: "Show Filler Tasks",
				description: "Flag to determine filler tasks are shown dynamically",
				category: "Mode",
				order: 2,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "edit_status",
				title: "Edit Status",
				description: "Flag to determine whether the status is editable",
				category: "Mode",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "edit_assigned",
				title: "Edit Assigned",
				description: "Flag for editing the assigned user of the tasks",
				category: "Mode",
				order: 4,
				type: "SelectWdg",
				values: ["true", "false"]
			}
		]
	},
	{
		value: "tactic.ui.table.TaskCompletionWdg",
		class: "tactic.ui.table.statistic_wdg.TaskCompletionWdg",
		aliases: [
			"tactic.ui.table.TaskCompletionWdg",
			"tactic.ui.table.statistic_wdg.TaskCompletionWdg",
			"TaskCompletionWdg",
			"tactic.ui.table.MilestoneCompletionWdg",
			"tactic.ui.table.statistic_wdg.MilestoneCompletionWdg",
			"tactic.ui.table.TaskGroupCompletionWdg",
			"tactic.ui.table.statistic_wdg.TaskGroupCompletionWdg",
			"pyasm.widget.statistic_wdg.TaskCompletionWdg",
			"pyasm.widget.TaskCompletionWdg"
		],
		options: [{
			name: "task_expr",
			title: "Task Expr",
			description: "an expression that retrieves the tasks e.g. @SOBJECT(sthpw/task['context','anim'])",
			category: "Display",
			order: 0,
			type: "TextAreaWdg"
		}]
	},
	{
		value: "tactic.ui.table.ExploreElementWdg",
		class: "tactic.ui.table.explorer_wdg.ExplorerElementWdg",
		aliases: [
			"tactic.ui.table.ExploreElementWdg",
			"tactic.ui.table.explorer_wdg.ExplorerElementWdg",
			"ExplorerElementWdg",
			"tactic.ui.table.ExplorerElementWdg",
			"tactic.ui.table.explorer_wdg.ExplorerTableElementWdg",
			"tactic.ui.table.ExplorerTableElementWdg"
		],
		options: [{
			name: "mode",
			title: "Mode",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg",
			values: ["sandbox", "repository"]
		}]
	},
	{
		value: "tactic.ui.table.SObjectFilesElementWdg",
		class: "tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg",
		aliases: [
			"tactic.ui.table.SObjectFilesElementWdg",
			"tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg",
			"SObjectFilesElementWdg"
		],
		options: [{
			name: "expression",
			title: "Expression",
			description: "Optional snapshot or file expression filter",
			category: "Display",
			order: 1,
			type: "TextAreaWdg"
		}]
	},
	{
		value: "tactic.ui.table.MetadataElementWdg",
		class: "tactic.ui.table.metadata_element_wdg.MetadataElementWdg",
		aliases: [
			"tactic.ui.table.MetadataElementWdg",
			"tactic.ui.table.metadata_element_wdg.MetadataElementWdg",
			"MetadataElementWdg"
		],
		options: [{
			name: "context",
			title: "Context",
			description: "The context of the snapshot to get the file path from",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "tactic.ui.table.JsonElementWdg",
		class: "tactic.ui.table.json_element_wdg.JsonElementWdg",
		aliases: [
			"tactic.ui.table.JsonElementWdg",
			"tactic.ui.table.json_element_wdg.JsonElementWdg",
			"JsonElementWdg"
		],
		options: [{
			name: "height",
			title: "Height",
			description: "Maximum cell height",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "tactic.ui.table.TaskSummaryElementWdg",
		class: "tactic.ui.table.task_element_wdg.TaskSummaryElementWdg",
		aliases: [
			"tactic.ui.table.TaskSummaryElementWdg",
			"tactic.ui.table.task_element_wdg.TaskSummaryElementWdg",
			"TaskSummaryElementWdg"
		],
		options: [
			{
				name: "bg_color",
				title: "Bg Color",
				description: "Different modes of displaying the background color for each process",
				category: "Color",
				order: 2,
				type: "SelectWdg",
				values: ["status", "process"]
			},
			{
				name: "status_color",
				title: "Status Color",
				description: "Different modes of displaying status background color",
				category: "Color",
				order: 3,
				type: "SelectWdg",
				values: ["status", "process"]
			},
			{
				name: "context_color",
				title: "Context Color",
				description: "Different modes of displaying context background color",
				category: "Color",
				order: 4,
				type: "SelectWdg",
				values: ["status", "process"]
			},
			{
				name: "panel_width",
				title: "Panel Width",
				description: "Select the overall width for the panel layout",
				category: "Display",
				order: 6,
				type: "SelectWdg",
				values: [
					"35px",
					"50px",
					"75px",
					"100px",
					"125px"
				]
			},
			{
				name: "font_size",
				title: "Font Size",
				description: "font size of the text",
				category: "Display",
				order: 7,
				type: "SelectWdg",
				values: [
					"7",
					"8",
					"9",
					"10",
					"11",
					"12",
					"13",
					"14"
				]
			},
			{
				name: "show_process",
				title: "Show Process",
				description: "Flag for displaying the process of the tasks",
				category: "Display",
				order: 8,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_context",
				title: "Show Context",
				description: "Flag for displaying the context of the tasks",
				category: "Display",
				order: 9,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_assigned",
				title: "Show Assigned",
				description: "Flag for displaying the assigned user of the tasks",
				category: "Display",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_bid",
				title: "Show Bid",
				description: "Flag for displaying the bid duration tasks",
				category: "Display",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_status",
				title: "Show Status",
				description: "Flag for displaying the status of the tasks",
				category: "Display",
				order: 10,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "assigned_label_attr",
				title: "Assigned Label Attr",
				description: "A list of | separated attributes displayed as the label of the assigned, e.g. \"first_name|last_name\"",
				category: "Display",
				order: 11,
				type: "TextWdg"
			},
			{
				name: "assigned_values_expr",
				title: "Assigned Values Expr",
				description: "An expression controlling what login values to show, e.g. @SOBJECT(sthpw/login['department','design'])",
				category: "Display",
				order: 12,
				type: "TextWdg"
			},
			{
				name: "show_dates",
				title: "Show Dates",
				description: "Flag for displaying the date range of the tasks",
				category: "Display",
				order: 13,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_track",
				title: "Show Track",
				description: "Flag for displaying a tip to dynamically load the information of the last status",
				category: "Display",
				order: 14,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_labels",
				title: "Show Labels",
				description: "Flag for displaying the label of the tasks",
				category: "Display",
				order: 15,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_border",
				title: "Show Border",
				description: "Flag for displaying a border around each task panel",
				category: "Display",
				order: 16,
				type: "SelectWdg",
				values: [
					"all",
					"one-sided",
					"none"
				]
			},
			{
				name: "collate_columns",
				title: "Collate Columns",
				description: "Flag to collate columns that have the same processes together .",
				category: "Display",
				order: 18,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_current_pipeline_only",
				title: "Show Current Pipeline Only",
				description: "Flag for displaying only the tasks associate with the current pipeline. Default to true.",
				category: "Display",
				order: 18,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_add_task",
				title: "Show Add Task",
				description: "Flag for displaying the add task button even if there are existing tasks. Defaults to false",
				category: "Display",
				order: 19,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_link_task_menu",
				title: "Show Link Task Menu",
				description: "Flag for displaying the task linking menu so one can virtually make a task shared by two or more people. Defaults to false",
				category: "Display",
				order: 20,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_processes_in_title",
				title: "Show Processes In Title",
				description: "Display the processes in title. You are advised to turn on show_filler_tasks as well. Defaults to false",
				category: "Display",
				order: 21,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_task_edit",
				title: "Show Task Edit",
				description: "Flag for displaying the edit icon for each task",
				category: "Display",
				order: 22,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "task_edit_view",
				title: "Task Edit View",
				description: "A custom view specified for editing the task in this widget. Defaults to edit",
				category: "Display",
				order: 23,
				type: "TextWdg",
				default: "edit"
			},
			{
				name: "task_filter",
				title: "Task Filter",
				description: "A filter on which type of tasks to display",
				category: "Display",
				order: 24,
				type: "SelectWdg",
				values: ["process_only", "context_only"]
			},
			{
				name: "layout",
				title: "Layout",
				description: "Determines layout for each process",
				category: "Mode",
				order: 1,
				type: "SelectWdg",
				values: [
					"panel",
					"vertical",
					"horizontal"
				]
			},
			{
				name: "show_filler_tasks",
				title: "Show Filler Tasks",
				description: "Flag to determine filler tasks are shown dynamically",
				category: "Mode",
				order: 2,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "edit_status",
				title: "Edit Status",
				description: "Flag to determine whether the status is editable",
				category: "Mode",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "edit_assigned",
				title: "Edit Assigned",
				description: "Flag for editing the assigned user of the tasks",
				category: "Mode",
				order: 4,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "mode",
				title: "Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.ButtonElementWdg",
		class: "tactic.ui.table.button_wdg.ButtonElementWdg",
		aliases: [
			"tactic.ui.table.ButtonElementWdg",
			"tactic.ui.table.button_wdg.ButtonElementWdg",
			"ButtonElementWdg"
		],
		options: [
			{
				name: "align",
				title: "Align",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "cbjs_action",
				title: "Cbjs Action",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "color",
				title: "Color",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "enable",
				title: "Enable",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "expression",
				title: "Expression",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "hint",
				title: "Hint",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "icon",
				title: "Icon",
				description: "",
				category: "Other Options",
				order: 99,
				type: "IconSelectWdg"
			},
			{
				name: "icon_tip",
				title: "Icon Tip",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "javascript",
				title: "Javascript",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "path",
				title: "Path",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "script",
				title: "Script",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "script_code",
				title: "Script Code",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "script_path",
				title: "Script Path",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "size",
				title: "Size",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "ParallelStatusWdg",
		class: "pyasm.widget.parallel_status.ParallelStatusWdg",
		aliases: [
			"ParallelStatusWdg",
			"pyasm.widget.parallel_status.ParallelStatusWdg",
			"pyasm.widget.ParallelStatusWdg"
		],
		options: [
			{
				name: "bar_height",
				title: "Bar Height",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "label_format",
				title: "Label Format",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "report",
				title: "Report",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.widget.TaskStatusElementWdg",
		class: "tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg",
		aliases: [
			"tactic.ui.widget.TaskStatusElementWdg",
			"tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg",
			"TaskStatusElementWdg"
		],
		options: [{
			name: "edit_scope",
			title: "Edit Scope",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "tactic.ui.table.WorkElementWdg",
		class: "tactic.ui.table.task_element_wdg.WorkElementWdg",
		aliases: [
			"tactic.ui.table.WorkElementWdg",
			"tactic.ui.table.task_element_wdg.WorkElementWdg",
			"WorkElementWdg"
		],
		options: [
			{
				name: "icon",
				title: "Icon",
				description: "",
				category: "Other Options",
				order: 99,
				type: "IconSelectWdg"
			},
			{
				name: "mode",
				title: "Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "transfer_mode",
				title: "Transfer Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.DropElementWdg",
		class: "tactic.ui.table.drop_element_wdg.DropElementWdg",
		aliases: [
			"tactic.ui.table.DropElementWdg",
			"tactic.ui.table.drop_element_wdg.DropElementWdg",
			"DropElementWdg"
		],
		options: [
			{
				name: "accepted_drop_type",
				title: "Accepted Drop Type",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "cbjs_drop_action",
				title: "Cbjs Drop Action",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "checkin_mode",
				title: "Checkin Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "context",
				title: "Context",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "css_background-color",
				title: "Css Background Color",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "display_expr",
				title: "Display Expr",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "instance_type",
				title: "Instance Type",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "path",
				title: "Path",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "subcontext",
				title: "Subcontext",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "subcontext_mode",
				title: "Subcontext Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "transfer_mode",
				title: "Transfer Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.CustomLayoutElementWdg",
		class: "tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg",
		aliases: [
			"tactic.ui.table.CustomLayoutElementWdg",
			"tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg",
			"CustomLayoutElementWdg"
		],
		options: [
			{
				name: "html",
				title: "Html",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "icon_size",
				title: "Icon Size",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "include_mako",
				title: "Include Mako",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "search_key",
				title: "Search Key",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_resize_scroll",
				title: "Show Resize Scroll",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "view",
				title: "View",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg",
		class: "tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg",
		aliases: [
			"tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg",
			"HiddenRowElementWdg",
			"tactic.ui.table.HiddenRowElementWdg",
			"tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg",
			"tactic.ui.table.RowAddElementWdg"
		],
		options: [
			{
				name: "dynamic",
				title: "Dynamic",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "dynamic_class",
				title: "Dynamic Class",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "edit_view",
				title: "Edit View",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "expression",
				title: "Expression",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "html",
				title: "Html",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextAreaWdg"
			},
			{
				name: "icon",
				title: "Icon",
				description: "",
				category: "Other Options",
				order: 99,
				type: "IconSelectWdg"
			},
			{
				name: "icon_tip",
				title: "Icon Tip",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "include_mako",
				title: "Include Mako",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "init_load_num",
				title: "Init Load Num",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "insert_view",
				title: "Insert View",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "label",
				title: "Label",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "mode",
				title: "Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "related_types",
				title: "Related Types",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "search_type",
				title: "Search Type",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "search_view",
				title: "Search View",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_gear",
				title: "Show Gear",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_insert",
				title: "Show Insert",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_resize_scroll",
				title: "Show Resize Scroll",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_row_select",
				title: "Show Row Select",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_search",
				title: "Show Search",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_search_limit",
				title: "Show Search Limit",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_select",
				title: "Show Select",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_shelf",
				title: "Show Shelf",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "title_icon",
				title: "Title Icon",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "view",
				title: "View",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "width",
				title: "Width",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "GanttWdg",
		class: "pyasm.widget.gantt_wdg.GanttWdg",
		aliases: [
			"GanttWdg",
			"pyasm.widget.gantt_wdg.GanttWdg",
			"pyasm.widget.GanttWdg"
		],
		options: [
			{
				name: "actual_edit",
				title: "Actual Edit",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "bid_edit",
				title: "Bid Edit",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "cal_margin",
				title: "Cal Margin",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "handlers",
				title: "Handlers",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "width",
				title: "Width",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.gantt_element_wdg.GanttElementWdg",
		class: "tactic.ui.table.gantt_element_wdg.GanttElementWdg",
		aliases: [
			"tactic.ui.table.gantt_element_wdg.GanttElementWdg",
			"GanttElementWdg",
			"tactic.ui.table.GanttElementWdg"
		],
		options: [
			{
				name: "bar_height",
				title: "Bar Height",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "color_mode",
				title: "Color Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "date_mode",
				title: "Date Mode",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "options",
				title: "Options",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "overlap",
				title: "Overlap",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "range_end_date",
				title: "Range End Date",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "range_start_date",
				title: "Range Start Date",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_title",
				title: "Show Title",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "week_display",
				title: "Week Display",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "week_start",
				title: "Week Start",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "width",
				title: "Width",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "year_display",
				title: "Year Display",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "WeekTableElement",
		class: "pyasm.widget.timecard_wdg.WeekTableElement",
		aliases: [
			"WeekTableElement",
			"pyasm.widget.timecard_wdg.WeekTableElement",
			"pyasm.widget.WeekTableElement"
		],
		options: [{
			name: "width",
			title: "Width",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg",
		class: "tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg",
		aliases: [
			"tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg",
			"WorkHoursElementWdg",
			"tactic.ui.table.WorkHoursElementWdg"
		],
		options: [
			{
				name: "day_width",
				title: "Day Width",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "days_per_page",
				title: "Days Per Page",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_all_users",
				title: "Show All Users",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "show_overtime",
				title: "Show Overtime",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "start_date",
				title: "Start Date",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "unit",
				title: "Unit",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "use_straight_time",
				title: "Use Straight Time",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			},
			{
				name: "width",
				title: "Width",
				description: "",
				category: "Other Options",
				order: 99,
				type: "TextWdg"
			}
		]
	},
	{
		value: "tactic.ui.table.CheckoutButtonElementWdg",
		class: "tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg",
		aliases: [
			"tactic.ui.table.CheckoutButtonElementWdg",
			"tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg",
			"CheckoutButtonElementWdg"
		],
		options: [{
			name: "transfer_mode",
			title: "Transfer Mode",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "pyasm.widget.SObjectConnectionElement",
		class: "pyasm.widget.sobject_browser_wdg.SObjectConnectionElement",
		aliases: [
			"pyasm.widget.SObjectConnectionElement",
			"pyasm.widget.sobject_browser_wdg.SObjectConnectionElement",
			"SObjectConnectionElement"
		],
		options: [{
			name: "direction",
			title: "Direction",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}, {
			name: "icon_size",
			title: "Icon Size",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "tactic.ui.table.ParentGroupTableElementWdg",
		class: "tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg",
		aliases: [
			"tactic.ui.table.ParentGroupTableElementWdg",
			"tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg",
			"ParentGroupTableElementWdg"
		],
		options: [{
			name: "disable",
			title: "Disable",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}, {
			name: "label",
			title: "Label",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "PublishTableElement",
		class: "pyasm.widget.table_element_wdg.PublishTableElement",
		aliases: [
			"PublishTableElement",
			"pyasm.widget.table_element_wdg.PublishTableElement",
			"pyasm.widget.PublishTableElement"
		],
		options: [{
			name: "multi_publish",
			title: "Multi Publish",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	},
	{
		value: "tactic.ui.table.GeneralPublishElementWdg",
		class: "tactic.ui.table.table_element_wdg.GeneralPublishElementWdg",
		aliases: [
			"tactic.ui.table.GeneralPublishElementWdg",
			"tactic.ui.table.table_element_wdg.GeneralPublishElementWdg",
			"GeneralPublishElementWdg"
		],
		options: [{
			name: "preview",
			title: "Preview",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}, {
			name: "view",
			title: "View",
			description: "",
			category: "Other Options",
			order: 99,
			type: "TextWdg"
		}]
	}
];
var EDIT_WIDGET_ARGS = [
	{
		value: "text",
		label: "Text",
		class: "pyasm.widget.input_wdg.TextWdg",
		aliases: [
			"TextWdg",
			"TextInputWdg",
			"pyasm.widget.TextWdg",
			"pyasm.widget.input_wdg.TextWdg",
			"tactic.ui.input.TextInputWdg",
			"tactic.ui.input.text_input_wdg.TextInputWdg"
		],
		options: [
			{
				name: "size",
				title: "Size",
				description: "Width of the text field in pixels",
				category: "Options",
				order: 0,
				type: "TextWdg"
			},
			{
				name: "width",
				title: "Width",
				description: "Width of the text element",
				category: "Options",
				order: 1,
				type: "TextWdg"
			},
			{
				name: "read_only",
				title: "Read Only",
				description: "Whether to set this text field to read-only",
				category: "Options",
				order: 2,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "required",
				title: "Required",
				description: "Designate this field to be filled in",
				category: "Options",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "default",
				title: "Default",
				description: "Default value in an edit form",
				category: "Options",
				order: 4,
				type: "TextWdg"
			},
			{
				name: "hint_text",
				title: "Hint Text",
				description: "Initial hint text",
				category: "Options",
				order: 5,
				type: "TextWdg"
			},
			{
				name: "display_format",
				title: "Display Format",
				description: "Format key to display the data",
				category: "Options",
				order: 6,
				type: "TextWdg"
			},
			{
				name: "validation_scheme",
				title: "Validation Scheme",
				description: "Built-in validation scheme (INTEGER, NUMERIC, POS_INTEGER)",
				category: "Options",
				order: 7,
				type: "SelectWdg",
				values: [
					"INTEGER",
					"NUMERIC",
					"POS_INTEGER"
				]
			}
		]
	},
	{
		value: "textarea",
		label: "Multi-line text",
		class: "pyasm.widget.input_wdg.TextAreaWdg",
		aliases: [
			"TextAreaWdg",
			"pyasm.widget.TextAreaWdg",
			"pyasm.widget.input_wdg.TextAreaWdg"
		],
		options: [
			{
				name: "rows",
				title: "Rows",
				description: "The number of rows to show",
				category: "Options",
				order: 1,
				type: "TextWdg"
			},
			{
				name: "cols",
				title: "Cols",
				description: "The number of columns to show",
				category: "Options",
				order: 2,
				type: "TextWdg"
			},
			{
				name: "required",
				title: "Required",
				description: "Designate this field to be filled in",
				category: "Options",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "read_only",
				title: "Read Only",
				description: "Whether to set this field to read-only",
				category: "Options",
				order: 4,
				type: "SelectWdg",
				values: ["true", "false"]
			}
		]
	},
	{
		value: "select",
		label: "Select",
		class: "pyasm.widget.input_wdg.SelectWdg",
		aliases: [
			"SelectWdg",
			"pyasm.widget.SelectWdg",
			"pyasm.widget.input_wdg.SelectWdg"
		],
		options: [
			{
				name: "labels_expr",
				title: "Labels Expr",
				description: "A list of labels retrieved through an expression, e.g. @GET(prod/shot.name)",
				category: "Misc",
				order: 1,
				type: "TextAreaWdg"
			},
			{
				name: "values_expr",
				title: "Values Expr",
				description: "A list of values retrieved through an expression, e.g. @GET(prod/shot.code)",
				category: "Misc",
				order: 2,
				type: "TextAreaWdg"
			},
			{
				name: "mode_expr",
				title: "Mode Expr",
				description: "Specify if it uses the current sObject as a starting point",
				category: "Misc",
				order: 3,
				type: "SelectWdg",
				values: ["relative"]
			},
			{
				name: "query",
				title: "Query",
				description: "Query shorthand in the form of <search_type>|<value_column>|<label_column>",
				category: "Misc",
				order: 4,
				type: "TextWdg"
			},
			{
				name: "values",
				title: "Values",
				description: "A list of values separated by | that determine the actual values of the selection",
				category: "Options",
				order: 1,
				type: "TextWdg"
			},
			{
				name: "labels",
				title: "Labels",
				description: "A list of values separated by | that determine the label of the selection",
				category: "Options",
				order: 2,
				type: "TextWdg"
			},
			{
				name: "empty",
				title: "Empty",
				description: "Include an empty selection option",
				category: "Options",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "default",
				title: "Default",
				description: "The default selection value in an edit form",
				category: "Options",
				order: 4,
				type: "TextWdg"
			},
			{
				name: "required",
				title: "Required",
				description: "Designate this field to have some value",
				category: "Options",
				order: 5,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "read_only",
				title: "Read Only",
				description: "Whether to set this field to read-only",
				category: "Options",
				order: 6,
				type: "SelectWdg",
				values: ["true", "false"]
			}
		]
	},
	{
		value: "calendar",
		label: "Calendar",
		class: "tactic.ui.widget.calendar_wdg.CalendarInputWdg",
		aliases: [
			"CalendarInputWdg",
			"calendar_time",
			"time",
			"tactic.ui.widget.CalendarInputWdg",
			"tactic.ui.widget.calendar_wdg.CalendarInputWdg"
		],
		options: [
			{
				name: "first_day_of_week",
				title: "First Day Of Week",
				description: "Integer representing first day of the week (6=Sunday, 0=Monday)",
				category: "Display",
				order: 0,
				type: "SelectWdg",
				values: ["6", "0"],
				labels: ["Sunday", "Monday"]
			},
			{
				name: "show_time",
				title: "Show Time",
				description: "Determines whether or not a time value is entered",
				category: "Display",
				order: 1,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "show_calendar",
				title: "Show Calendar",
				description: "Determines whether or not the calendar is shown",
				category: "Display",
				order: 2,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "read_only",
				title: "Read Only",
				description: "Sets the widget to be read only",
				category: "Display",
				order: 3,
				type: "SelectWdg",
				values: ["true", "false"]
			},
			{
				name: "default",
				title: "Default",
				description: "The default selection value in an edit form",
				category: "Display",
				order: 4,
				type: "TextWdg"
			},
			{
				name: "time_input_default",
				title: "Time Input Default",
				description: "The default for time, e.g. 5:00 PM",
				category: "Display",
				order: 5,
				type: "TextWdg"
			},
			{
				name: "display_mode",
				title: "Display Mode",
				description: "Determines whether to use the TACTIC calendar or the browser calendar",
				category: "Display",
				order: 6,
				type: "SelectWdg",
				values: ["browser", "inline"]
			},
			{
				name: "date_format",
				title: "Date Format",
				description: "Format of the date on clicking on a day in the Calendar, e.g. %m-%d-%Y",
				category: "Display",
				order: 8,
				type: "TextWdg"
			},
			{
				name: "display_format",
				title: "Display Format",
				description: "Display format like YYYY/MM/DD HH:MM AM",
				category: "Display",
				order: 9,
				type: "TextWdg"
			},
			{
				name: "hint_text",
				title: "Hint Text",
				description: "Hint text when the calendar input is read only",
				category: "Display",
				order: 10,
				type: "TextWdg"
			}
		]
	},
	{
		value: "checkbox",
		label: "Checkbox",
		class: "pyasm.widget.input_wdg.CheckboxWdg",
		aliases: [
			"CheckboxWdg",
			"CurrentCheckboxWdg",
			"pyasm.widget.CheckboxWdg",
			"pyasm.widget.input_wdg.CheckboxWdg",
			"pyasm.widget.input_wdg.CurrentCheckboxWdg"
		],
		options: [{
			name: "default",
			title: "Default",
			description: "Default state of the checkbox (true|false)",
			category: "Options",
			order: 1,
			type: "SelectWdg",
			values: ["true", "false"]
		}, {
			name: "read_only",
			title: "Read Only",
			description: "Whether to set this checkbox to read-only",
			category: "Options",
			order: 2,
			type: "SelectWdg",
			values: ["true", "false"]
		}]
	},
	{
		value: "color",
		label: "Color",
		class: "tactic.ui.input.color_input_wdg.ColorInputWdg",
		aliases: [
			"ColorInputWdg",
			"tactic.ui.input.ColorInputWdg",
			"tactic.ui.input.color_input_wdg.ColorInputWdg"
		],
		options: [{
			name: "start_color",
			title: "Start Color",
			description: "Default starting hex color",
			category: "Options",
			order: 1,
			type: "TextWdg"
		}, {
			name: "read_only",
			title: "Read Only",
			description: "Whether to set this field to read-only",
			category: "Options",
			order: 2,
			type: "SelectWdg",
			values: ["true", "false"]
		}]
	}
];
function displayWidgetArgs(widget) {
	const key = String(widget || "").trim();
	const match = DISPLAY_WIDGET_ARGS.find((item) => item.value === key || item.class === key || (item.aliases || []).indexOf(key) >= 0);
	return match ? match.options : [];
}
function editWidgetArgs(widget) {
	const key = String(widget || "").trim();
	if (!key) return EDIT_WIDGET_ARGS[0].options;
	const match = EDIT_WIDGET_ARGS.find((item) => item.value === key || item.class === key || (item.aliases || []).indexOf(key) >= 0);
	return match ? match.options : [];
}
function editWidgetOptionsFor(widget) {
	const key = String(widget || "").trim();
	const base = [{
		value: "",
		label: "Default"
	}].concat(EDIT_WIDGET_ARGS.map((item) => ({
		value: item.value === key || item.class === key || (item.aliases || []).indexOf(key) >= 0 ? key : item.value,
		label: item.label
	})));
	if (!key || base.some((item) => item.value === key)) return base;
	return [{
		value: key,
		label: key
	}].concat(base);
}
function humanizeOptionName(name) {
	return String(name || "").replace(/-/g, "_").split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/columns/columns.ui.mjs
var WIDGET_SPECS = [
	{
		values: [
			"",
			"TextWdg",
			"SimpleTableElementWdg",
			"tactic.ui.common.SimpleTableElementWdg",
			"tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg",
			"pyasm.widget.SimpleTableElementWdg",
			"pyasm.widget.table_element_wdg.SimpleTableElementWdg",
			"pyasm.widget.input_wdg.TextWdg"
		],
		kind: "value",
		title: "Automatic",
		icon: "type",
		summary: "Displays the field value using its schema type, cell icon, alignment, and badge style.",
		optionsHint: "XML options: <column>, <value_icon>, <value_align>, <value_style>, <value_text_style>."
	},
	{
		values: [
			"format",
			"tactic.ui.table.FormatElementWdg",
			"tactic.ui.table.format_element_wdg.FormatElementWdg"
		],
		kind: "format",
		title: "Format",
		icon: "tune",
		summary: "Formats text, numbers, currency, dates, timestamps, or checkboxes.",
		optionsHint: "XML options: <type>integer|float|currency|percent|date|time|timecode|Checkbox</type>, <format>-1234.12|YYYY-MM-DD</format>, <fps>24</fps>, <total_summary>total|average|count</total_summary>."
	},
	{
		values: [
			"expression",
			"tactic.ui.table.ExpressionElementWdg",
			"tactic.ui.table.expression_element_wdg.ExpressionElementWdg"
		],
		kind: "expression",
		title: "Expression",
		icon: "code",
		summary: "Computes a read-only value or aggregate from a TACTIC expression (@GET, @COUNT, @SUM).",
		optionsHint: "XML options: <expression>@GET(...)</expression>, <mode>value|boolean|check</mode>, <use_cache>true|false</use_cache>, <order_by>, <bottom>, <group_bottom>."
	},
	{
		values: [
			"expression_value",
			"tactic.ui.table.ExpressionValueElementWdg",
			"tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg"
		],
		kind: "expression",
		title: "Expression value",
		icon: "code",
		summary: "Evaluates a TACTIC expression while keeping the column bound to an editable field.",
		optionsHint: "XML options: <expression>@GET(...)</expression>, <mode>value|boolean|check</mode>, <use_cache>true|false</use_cache>."
	},
	{
		values: [
			"link",
			"tactic.ui.table.LinkElementWdg",
			"tactic.ui.table.link_element_wdg.LinkElementWdg"
		],
		kind: "link",
		title: "Link",
		icon: "open-in-new",
		summary: "Renders the cell value as a clickable hyperlink or external URL.",
		optionsHint: "XML options: <column>, <icon> (reads URL from the column value or expression)."
	},
	{
		values: [
			"pyasm.widget.ThumbWdg",
			"ThumbWdg",
			"pyasm.widget.file_wdg.ThumbWdg",
			"tactic.ui.panel.ThumbWdg2"
		],
		kind: "preview",
		title: "Thumbnail",
		icon: "image",
		summary: "Shows the latest snapshot preview image or an avatar badge for the row.",
		optionsHint: "XML options: <icon_context>icon|publish</icon_context>, <filename>true|false</filename>, <latest_icon>true|false</latest_icon>, <original>true|false</original>."
	},
	{
		values: [
			"tactic.ui.widget.DiscussionElementWdg",
			"tactic.ui.widget.discussion_wdg.DiscussionElementWdg",
			"DiscussionWdg",
			"pyasm.widget.DiscussionWdg",
			"pyasm.widget.discussion_wdg.DiscussionWdg",
			"tactic.ui.widget.DiscussionWdg",
			"tactic.ui.widget.discussion_wdg.DiscussionWdg"
		],
		kind: "notes",
		title: "Notes",
		icon: "comment",
		summary: "Opens process notes and discussion comments with a message count badge.",
		optionsHint: "XML options: <process>, <context>, <use_parent>true|false</use_parent>. Legacy HTML popup flags (note_format, dialog_position, show_fullscreen_button, allow_email) are ignored because notes open in the unified inspector."
	},
	{
		values: [
			"tactic.ui.table.TaskElementWdg",
			"tactic.ui.table.task_element_wdg.TaskElementWdg",
			"SObjectTaskTableElement",
			"pyasm.widget.SObjectTaskTableElement",
			"pyasm.widget.task_wdg.SObjectTaskTableElement"
		],
		kind: "tasks",
		title: "Tasks",
		icon: "tasks",
		summary: "Displays interactive workflow task cards with process, status, and assignee.",
		optionsHint: "XML options: <process>, <context>, <pipeline_code>, <show_current_pipeline_only>true|false</show_current_pipeline_only>, <edit>true|false</edit>."
	},
	{
		values: [
			"tactic.ui.table.TaskCompletionWdg",
			"tactic.ui.table.statistic_wdg.TaskCompletionWdg",
			"TaskCompletionWdg",
			"pyasm.widget.TaskCompletionWdg",
			"pyasm.widget.statistic_wdg.TaskCompletionWdg",
			"tactic.ui.table.MilestoneCompletionWdg",
			"tactic.ui.table.statistic_wdg.MilestoneCompletionWdg"
		],
		kind: "completion",
		title: "Task completion",
		icon: "check-circle",
		summary: "Renders a progress bar showing overall task completion percentage for the row.",
		optionsHint: "XML options: <task_expr> (optional TACTIC expression to filter which tasks are counted)."
	},
	{
		values: [
			"tactic.ui.table.gantt_element_wdg.GanttElementWdg",
			"tactic.ui.table.GanttElementWdg",
			"GanttWdg",
			"pyasm.widget.GanttWdg",
			"pyasm.widget.gantt_wdg.GanttWdg"
		],
		kind: "gantt",
		title: "Gantt",
		icon: "calendar",
		summary: "Shows a schedule timeline bar from task start and end dates.",
		optionsHint: "XML options: <options>[{\"start_date_col\":\"bid_start_date\",\"end_date_col\":\"bid_end_date\"}]</options>, <range_start_date>, <range_end_date>."
	},
	{
		values: [
			"tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg",
			"tactic.ui.table.HiddenRowElementWdg",
			"HiddenRowToggleWdg",
			"pyasm.widget.HiddenRowToggleWdg",
			"pyasm.widget.table_element_wdg.HiddenRowToggleWdg",
			"tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg",
			"tactic.ui.table.RowAddElementWdg"
		],
		kind: "related",
		title: "Show related table",
		icon: "table",
		summary: "Adds a button with a counter that expands an inline nested table of related records.",
		optionsHint: "XML options: <search_type>, <view>, <dynamic_class>tactic.ui.panel.FastTableLayoutWdg</dynamic_class>, <value_icon>."
	},
	{
		values: ["tactic.ui.table.DropElementWdg", "tactic.ui.table.drop_element_wdg.DropElementWdg"],
		kind: "related",
		title: "Instance links",
		icon: "layers",
		summary: "Lists linked related records and supports drag-and-drop linking.",
		optionsHint: "XML options: <instance_type>, <accepted_drop_type>, <path>."
	},
	{
		values: ["tactic.ui.table.ButtonElementWdg", "tactic.ui.table.button_wdg.ButtonElementWdg"],
		kind: "action",
		title: "Configured button",
		icon: "play",
		actionIcon: "play",
		summary: "Runs a custom server Python script or client action when clicked.",
		optionsHint: "XML options: <script_path>, <icon>, <hint>, <color>."
	},
	{
		values: ["tactic.ui.table.CustomLayoutElementWdg", "tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg"],
		kind: "expression",
		title: "Custom Layout",
		icon: "dashboard",
		summary: "Renders a custom HTML/Mako layout template inside the table cell.",
		optionsHint: "XML options: <view> (saved custom layout view name) or inline <html>."
	},
	{
		values: ["tactic.ui.table.SObjectDetailElementWdg", "tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg"],
		kind: "action",
		title: "SObject details",
		icon: "info",
		actionIcon: "info",
		summary: "Opens the full record detail inspector for the row.",
		optionsHint: "XML options: no extra <display> options required."
	},
	{
		values: ["tactic.ui.table.CheckinButtonElementWdg", "tactic.ui.table.table_element_wdg.CheckinButtonElementWdg"],
		kind: "action",
		title: "Check-in",
		icon: "upload",
		actionIcon: "upload",
		summary: "Opens the file upload and snapshot check-in dialog for the row.",
		optionsHint: "XML options: <process>, <subcontext>, <transfer_mode>upload|copy|move</transfer_mode>, <sobject_mode>self|parent|connect|expression</sobject_mode>."
	},
	{
		values: [
			"tactic.ui.table.ExploreElementWdg",
			"tactic.ui.table.ExplorerElementWdg",
			"tactic.ui.table.explorer_wdg.ExplorerElementWdg",
			"tactic.ui.table.ExplorerTableElementWdg",
			"tactic.ui.table.explorer_wdg.ExplorerTableElementWdg"
		],
		kind: "action",
		title: "Explorer",
		icon: "folder",
		actionIcon: "folder",
		summary: "Opens the local sandbox or repository folder for the row.",
		optionsHint: "XML options: <mode>sandbox|repository</mode>."
	},
	{
		values: ["tactic.ui.table.SObjectFilesElementWdg", "tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg"],
		kind: "action",
		title: "Files",
		icon: "description",
		actionIcon: "description",
		summary: "Lists published snapshot files attached to the record.",
		optionsHint: "XML options: <expression> (optional snapshot/file query)."
	},
	{
		values: ["tactic.ui.table.MetadataElementWdg", "tactic.ui.table.metadata_element_wdg.MetadataElementWdg"],
		kind: "action",
		title: "Metadata",
		icon: "tune",
		actionIcon: "tune",
		summary: "Inspects snapshot and file metadata for the record.",
		optionsHint: "XML options: no extra <display> options required."
	},
	{
		values: ["tactic.ui.table.DeleteElementWdg", "tactic.ui.table.delete_element_wdg.DeleteElementWdg"],
		kind: "action",
		title: "Delete",
		icon: "delete",
		actionIcon: "delete",
		summary: "Provides an action button to delete the record from the table.",
		optionsHint: "XML options: no extra <display> options required."
	},
	{
		values: ["tactic.ui.common.base_table_element_wdg.RawTableElementWdg", "tactic.ui.common.RawTableElementWdg"],
		kind: "value",
		title: "Raw value",
		icon: "database",
		summary: "Displays the unformatted raw database column value.",
		optionsHint: "XML options: <column> (optional database column override)."
	}
];
function widgetSpec(widget) {
	const key = String(widget || "").trim();
	return WIDGET_SPECS.find((item) => item.values.indexOf(key) >= 0) || {
		kind: "value",
		title: key || "Automatic",
		customTitle: Boolean(key),
		icon: "cube",
		summary: "Custom or legacy TACTIC table element class.",
		optionsHint: "XML options: edit custom <display> parameters directly in Selected element XML below."
	};
}
function alignOffset(containerWidth, contentWidth, align, pad = 10) {
	if (align === "center") return Math.max(pad, Math.round((containerWidth - contentWidth) / 2));
	if (align === "right") return Math.max(pad, containerWidth - contentWidth - pad);
	return pad;
}
function previewCellNodes(spec, element, cellW, cellH, headingText, tr) {
	const bodyY = 22, bodyH = cellH - bodyY, align = element.valueAlign || "";
	const children = [node("Box", "definitionWidgetPreviewHeader", rect(0, 0, cellW, bodyY), {
		background: "surfaceContainerHigh",
		radius: 7,
		children: [label("definitionWidgetPreviewHeaderLabel", rect(8, 0, cellW - 16, bodyY), String(headingText || element.title || element.name || "COLUMN").slice(0, 22).toUpperCase(), {
			fontRole: "caption",
			weight: 600,
			align: "center",
			color: "secondaryText"
		})]
	})];
	if (spec.kind === "preview") {
		const x = alignOffset(cellW, 30, align || "center", 10);
		children.push(node("Box", "definitionWidgetPreviewThumb", rect(x, bodyY + Math.round((bodyH - 30) / 2), 30, 30), {
			background: "contentSelection",
			border: "primary",
			radius: 15,
			children: [node("Icon", "definitionWidgetPreviewThumbIcon", rect(7, 7, 16, 16), {
				icon: "image",
				color: "primaryText"
			})]
		}));
	} else if (spec.kind === "notes") {
		const w = Math.min(cellW - 16, 118), x = alignOffset(cellW, w, align || "center", 8);
		children.push(node("Box", "definitionWidgetPreviewNotes", rect(x, bodyY + Math.round((bodyH - 28) / 2), w, 28), {
			background: "surfaceContainerHigh",
			border: "primary",
			radius: 6,
			children: [node("Icon", "definitionWidgetPreviewNotesIcon", rect(8, 7, 14, 14), {
				icon: "comment",
				color: "primary"
			}), label("definitionWidgetPreviewNotesLabel", rect(26, 0, w - 32, 28), tr("Notes") + " (3)", {
				fontRole: "caption",
				weight: 600
			})]
		}));
	} else if (spec.kind === "tasks") {
		const w = Math.min(cellW - 16, 136), x = alignOffset(cellW, w, align || "left", 8);
		children.push(node("Box", "definitionWidgetPreviewTasks", rect(x, bodyY + Math.round((bodyH - 34) / 2), w, 34), {
			background: "surfaceContainerHigh",
			border: "primary",
			radius: 6,
			children: [
				label("definitionWidgetPreviewTaskProcess", rect(8, 2, w - 16, 15), "model", {
					fontRole: "caption",
					weight: 600
				}),
				node("Icon", "definitionWidgetPreviewTaskUserIcon", rect(8, 19, 11, 11), {
					icon: "user",
					color: "secondaryText"
				}),
				label("definitionWidgetPreviewTaskUser", rect(22, 16, w - 28, 15), "admin", {
					fontRole: "caption",
					color: "secondaryText"
				})
			]
		}));
	} else if (spec.kind === "completion" || spec.kind === "gantt") {
		const barW = Math.max(40, cellW - 24);
		children.push(node("Box", "definitionWidgetPreviewBarTrack", rect(12, 32, barW, 8), {
			background: "surfaceContainerHigh",
			radius: 4,
			children: [node("Box", "definitionWidgetPreviewBarFill", rect(0, 0, Math.round(barW * .72), 8), {
				background: "primary",
				radius: 4
			})]
		}), label("definitionWidgetPreviewBarLabel", rect(12, 43, barW, 18), spec.kind === "gantt" ? "12 May – 18 May" : "72%", {
			fontRole: "caption",
			align: "center",
			color: "secondaryText"
		}));
	} else if (spec.kind === "related") {
		const w = Math.min(cellW - 16, 128), x = alignOffset(cellW, w, align || "center", 8), iconName = (Object.prototype.hasOwnProperty.call(element, "valueIcon") ? element.valueIcon : "") || "cube";
		children.push(node("Box", "definitionWidgetPreviewRelated", rect(x, bodyY + Math.round((bodyH - 28) / 2), w, 28), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			radius: 6,
			children: [
				node("Icon", "definitionWidgetPreviewRelatedIcon", rect(8, 7, 14, 14), {
					icon: iconName,
					color: "secondaryText"
				}),
				label("definitionWidgetPreviewRelatedLabel", rect(26, 0, w - 46, 28), "Assets 4", {
					fontRole: "caption",
					weight: 600
				}),
				node("Icon", "definitionWidgetPreviewRelatedArrow", rect(w - 18, 7, 13, 13), {
					icon: "chevron-right",
					color: "secondaryText"
				})
			]
		}));
	} else if (spec.kind === "action") {
		const x = alignOffset(cellW, 30, align || "center", 8);
		children.push(node("Box", "definitionWidgetPreviewAction", rect(x, bodyY + Math.round((bodyH - 28) / 2), 30, 28), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			radius: 6,
			children: [node("Icon", "definitionWidgetPreviewActionIcon", rect(7, 6, 15, 15), {
				icon: spec.actionIcon || "play",
				color: spec.actionIcon === "delete" ? "error" : "primaryText"
			})]
		}));
	} else if (spec.kind === "link") children.push(node("Icon", "definitionWidgetPreviewLinkIcon", rect(10, 37, 14, 14), {
		icon: "open-in-new",
		color: "primary"
	}), label("definitionWidgetPreviewLinkLabel", rect(28, 30, cellW - 36, 28), element.name || "EP-001", {
		fontRole: "caption",
		weight: 600,
		color: "primary",
		align: align || "left"
	}));
	else if (spec.kind === "expression") children.push(node("Box", "definitionWidgetPreviewExprTag", rect(10, 34, 22, 20), {
		background: "surfaceContainerHigh",
		border: "outlineVariant",
		radius: 4,
		children: [label("definitionWidgetPreviewExprTagLabel", rect(0, 0, 22, 20), "fx", {
			fontRole: "caption",
			weight: 600,
			align: "center",
			color: "primary"
		})]
	}), label("definitionWidgetPreviewExprValue", rect(38, 30, cellW - 46, 28), "Episode 01", {
		fontRole: element.valueTextStyle === "heading" ? "bodyLarge" : element.valueTextStyle === "small" ? "caption" : "body",
		weight: element.valueTextStyle === "heading" ? 600 : 400,
		align: align || "left"
	}));
	else {
		const isBadge = element.valueStyle === "badge" || !element.valueStyle && element.name === "duration", iconName = Object.prototype.hasOwnProperty.call(element, "valueIcon") ? element.valueIcon : element.name === "duration" ? "clock" : "", sampleText = element.name === "duration" ? "20 Seconds" : spec.kind === "format" ? "2026-11-04" : "Episode 01", fontRole = element.valueTextStyle === "heading" ? "bodyLarge" : element.valueTextStyle === "small" ? "caption" : "body";
		if (isBadge) {
			const w = Math.min(cellW - 16, 118), x = alignOffset(cellW, w, align || "left", 8);
			children.push(node("Box", "definitionWidgetPreviewBadge", rect(x, bodyY + Math.round((bodyH - 28) / 2), w, 28), {
				background: "surfaceContainerHigh",
				border: "outlineVariant",
				radius: 6,
				children: (iconName ? [node("Icon", "definitionWidgetPreviewBadgeIcon", rect(8, 7, 14, 14), {
					icon: iconName,
					color: "secondaryText"
				})] : []).concat([label("definitionWidgetPreviewBadgeLabel", rect(iconName ? 26 : 8, 0, w - (iconName ? 32 : 16), 28), sampleText, {
					fontRole: "caption",
					weight: 600,
					align: iconName ? "left" : "center"
				})])
			}));
		} else {
			if (iconName) children.push(node("Icon", "definitionWidgetPreviewValueIcon", rect(10, 37, 14, 14), {
				icon: iconName,
				color: "secondaryText"
			}));
			children.push(label("definitionWidgetPreviewValueLabel", rect(iconName ? 28 : 10, 30, cellW - (iconName ? 38 : 20), 28), sampleText, {
				fontRole,
				weight: element.valueTextStyle === "heading" ? 600 : 400,
				align: align || "left"
			}));
		}
	}
	return children;
}
function widgetPreviewField(element, headingText, formWidth, tr) {
	const spec = widgetSpec(element.widget), rowWidth = Math.max(200, formWidth - 32), wide = rowWidth >= 420, cellW = wide ? 184 : Math.min(220, rowWidth - 24), cellH = 66, textX = wide ? cellW + 24 : 12, textW = wide ? rowWidth - cellW - 36 : rowWidth - 24, summary = tr(spec.summary), optionsHint = spec.optionsHint ? tr(spec.optionsHint) : "", descH = Math.max(18, captionHeight(summary, textW)), optH = optionsHint ? Math.max(18, captionHeight(optionsHint, textW)) : 0, textTotalH = 34 + descH + (optH ? optH + 6 : 0), boxH = wide ? Math.max(92, textTotalH + 10) : textTotalH + cellH + 18, cellX = 12, cellY = wide ? Math.round((boxH - cellH) / 2) : textTotalH + 6;
	const previewChildren = [
		node("Box", "definitionWidgetPreviewCell", rect(cellX, cellY, cellW, cellH), {
			background: "workspace",
			border: "outlineVariant",
			radius: 8,
			children: previewCellNodes(spec, element, cellW, cellH, headingText, tr)
		}),
		node("Icon", "definitionWidgetPreviewIcon", rect(textX, 12, 16, 16), {
			icon: spec.icon,
			color: "primary"
		}),
		label("definitionWidgetPreviewTitle", rect(textX + 22, 10, textW - 22, 20), spec.customTitle ? spec.title : tr(spec.title), {
			fontRole: "body",
			weight: 600
		}),
		label("definitionWidgetPreviewSummary", rect(textX, 32, textW, descH), summary, Object.assign({}, muted, {
			fontRole: "caption",
			wrap: true
		}))
	];
	if (optionsHint) previewChildren.push(label("definitionWidgetPreviewOptions", rect(textX, 36 + descH, textW, optH), optionsHint, Object.assign({}, muted, {
		fontRole: "caption",
		wrap: true
	})));
	return {
		kind: "Box",
		id: "definitionWidgetPreview",
		title: "Widget preview",
		fullWidth: true,
		height: boxH,
		props: {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			radius: 10,
			children: previewChildren
		}
	};
}
var list = (id, bounds, source, rowHeight) => node("List", id, bounds, {
	source,
	rowHeight,
	keyField: source === "definitions" ? "identity" : "path",
	fields: [],
	scrollbarId: id + "ScrollBar"
});
var NON_TABLE_VIEWS = [
	"color",
	"custom_filter",
	"filter",
	"search",
	"simple_filter",
	"insert",
	"add_item",
	"overview"
];
var NON_TABLE_WIDGET_TYPES = [
	"widget",
	"layout",
	"theme",
	"dashboard",
	"chart",
	"sidebar",
	"custom_layout"
];
var NON_TABLE_SEARCH_TYPES = ["SideBarWdg", "CustomLayoutWdg"];
var NON_TABLE_LAYOUT_RE = /layout\s*=\s*["'](?:CustomLayoutWdg|tactic\.ui\.panel\.CustomLayoutWdg|sobject-layout|ItemLayoutWdg)["']/i;
function records(model, ui) {
	const query = ui.query.trim().toLowerCase();
	return model.records.filter((row) => {
		const view = String(row.view || "");
		const stype = String(row.searchType || "");
		const wtype = String(row.widgetType || "").toLowerCase();
		const cfg = String(row.config || "");
		if (NON_TABLE_SEARCH_TYPES.indexOf(stype) >= 0) return false;
		if (view.indexOf("link_search:") === 0) return false;
		if (NON_TABLE_VIEWS.indexOf(view) >= 0) return false;
		if (wtype && NON_TABLE_WIDGET_TYPES.indexOf(wtype) >= 0) return false;
		if (cfg && NON_TABLE_LAYOUT_RE.test(cfg)) return false;
		return (!ui.searchType || stype === ui.searchType) && (!query || [
			row.view,
			row.searchType,
			row.code,
			row.login,
			row.category,
			row.widgetType,
			row.config
		].join(" ").toLowerCase().indexOf(query) >= 0);
	});
}
function sanitizeId(raw) {
	return String(raw || "").replace(/[^A-Za-z0-9_-]/g, "_");
}
function buildOptionFields(specs, optionsMap, prefix, ui, text, tr, idPrefix) {
	const fields = [];
	const knownNames = {};
	const groups = [];
	const byCat = {};
	for (let i = 0; i < specs.length; i++) {
		const opt = specs[i];
		knownNames[opt.name] = true;
		const cat = opt.category || "Options";
		if (!byCat[cat]) {
			byCat[cat] = [];
			groups.push({
				category: cat,
				items: byCat[cat]
			});
		}
		byCat[cat].push(opt);
	}
	for (let g = 0; g < groups.length; g++) {
		const group = groups[g];
		const catKey = prefix + ":" + group.category;
		const collapsed = !!ui.collapsedCategories[catKey];
		const catId = idPrefix + "Cat_" + sanitizeId(group.category) + "_" + g;
		fields.push({
			kind: "Action",
			id: catId,
			title: group.category,
			fullWidth: true,
			height: 32,
			showDivider: false,
			props: {
				text: tr(group.category),
				normalColor: "surfaceContainerHigh",
				selectedColor: "contentSelection",
				action: {
					type: "toggleCategory",
					key: catKey
				},
				children: [
					node("Icon", catId + "_Icon", rect(8, 8, 16, 16), {
						icon: collapsed ? "chevron-right" : "chevron-down",
						color: "primary"
					}),
					label(catId + "_Label", rect(28, 0, 260, 32), tr(group.category), {
						fontRole: "body",
						weight: 600
					}),
					label(catId + "_Count", rect(290, 0, 48, 32), String(group.items.length), Object.assign({ align: "right" }, muted))
				]
			}
		});
		if (!collapsed) for (let j = 0; j < group.items.length; j++) {
			const opt = group.items[j];
			const fieldKey = prefix + ":" + opt.name;
			const currentVal = String(optionsMap && optionsMap[opt.name] || "");
			const optId = idPrefix + "Opt_" + sanitizeId(opt.name);
			const desc = [opt.description || "", opt.default ? "Default: " + opt.default : ""].filter(Boolean).join(" · ");
			if (opt.values && opt.values.length) {
				const choices = [{
					value: "",
					label: tr("Default")
				}].concat(opt.values.map((v) => ({
					value: String(v),
					label: String(v)
				})));
				if (currentVal && !choices.some((c) => c.value === currentVal)) choices.splice(1, 0, {
					value: currentVal,
					label: currentVal
				});
				fields.push({
					kind: "Choice",
					id: optId,
					title: opt.title || humanizeOptionName(opt.name),
					dataLabel: true,
					description: desc,
					field: fieldKey,
					options: choices,
					props: { value: currentVal }
				});
			} else if (opt.type === "CheckboxWdg") fields.push({
				kind: "Switch",
				id: optId,
				title: opt.title || humanizeOptionName(opt.name),
				dataLabel: true,
				description: desc,
				field: fieldKey,
				props: { checked: [
					"true",
					"1",
					"yes",
					"on"
				].indexOf(currentVal.toLowerCase()) >= 0 }
			});
			else fields.push({
				id: optId,
				title: opt.title || humanizeOptionName(opt.name),
				dataLabel: true,
				description: desc,
				field: fieldKey,
				props: {
					text: text(fieldKey),
					placeholder: opt.default ? String(opt.default) : "",
					action: {
						type: "text",
						field: fieldKey
					},
					commitAction: { type: "commit" }
				}
			});
		}
	}
	const extraKeys = Object.keys(optionsMap || {}).filter((k) => !knownNames[k]);
	if (extraKeys.length || prefix === "option") {
		const extraCatKey = prefix + ":__extra__";
		const extraCollapsed = !!ui.collapsedCategories[extraCatKey];
		const extraCatId = idPrefix + "Cat_ExtraOptions";
		fields.push({
			kind: "Action",
			id: extraCatId,
			title: "Extra Options",
			fullWidth: true,
			height: 32,
			showDivider: false,
			props: {
				text: tr("Extra Options"),
				normalColor: "surfaceContainerHigh",
				selectedColor: "contentSelection",
				action: {
					type: "toggleCategory",
					key: extraCatKey
				},
				children: [
					node("Icon", extraCatId + "_Icon", rect(8, 8, 16, 16), {
						icon: extraCollapsed ? "chevron-right" : "chevron-down",
						color: "primary"
					}),
					label(extraCatId + "_Label", rect(28, 0, 260, 32), tr("Extra Options"), {
						fontRole: "body",
						weight: 600
					}),
					label(extraCatId + "_Count", rect(290, 0, 48, 32), String(extraKeys.length), Object.assign({ align: "right" }, muted))
				]
			}
		});
		if (!extraCollapsed) {
			for (let k = 0; k < extraKeys.length; k++) {
				const key = extraKeys[k];
				const fieldKey = prefix + ":" + key;
				fields.push({
					id: idPrefix + "ExtraOpt_" + sanitizeId(key),
					title: humanizeOptionName(key),
					dataLabel: true,
					description: "<" + key + ">",
					field: fieldKey,
					props: {
						text: text(fieldKey),
						action: {
							type: "text",
							field: fieldKey
						},
						commitAction: { type: "commit" }
					}
				});
			}
			if (prefix === "option") fields.push({
				id: "definitionExtraOptAdd",
				title: "Add Extra Option",
				description: "Enter name=value and press Enter to add a custom <display> option.",
				field: "extraOptionAdd",
				props: {
					text: text("extraOptionAdd"),
					placeholder: "option_name=value",
					action: {
						type: "text",
						field: "extraOptionAdd"
					},
					commitAction: { type: "commit" }
				}
			});
		}
	}
	return fields;
}
function colorsSectionField(element, ui, formWidth, tr) {
	const open = !!ui.colorsOpen;
	const entries = element.colorMap || [];
	const rowWidth = Math.max(200, formWidth - 32);
	const children = [node("Action", "definitionColorsToggle", rect(0, 0, rowWidth, 34), {
		text: tr("Colors"),
		normalColor: "surfaceContainerHigh",
		selectedColor: "contentSelection",
		action: {
			type: "toggleSection",
			section: "colors"
		},
		children: [
			node("Icon", "definitionColorsToggleIcon", rect(8, 9, 16, 16), {
				icon: open ? "chevron-down" : "chevron-right",
				color: "primary"
			}),
			label("definitionColorsToggleLabel", rect(28, 0, rowWidth - 80, 34), tr("Colors"), {
				fontRole: "body",
				weight: 600
			}),
			label("definitionColorsToggleCount", rect(rowWidth - 52, 0, 44, 34), entries.length ? String(entries.length) : "", Object.assign({ align: "right" }, muted))
		]
	})];
	let totalH = 34;
	if (open) {
		if (!entries.length) {
			children.push(label("definitionColorsEmptyLabel", rect(12, totalH + 6, rowWidth - 24, 28), tr("No colors have been defined."), muted));
			totalH += 40;
		} else {
			for (let i = 0; i < entries.length; i++) {
				const entry = entries[i];
				const ry = totalH + 6 + i * 28;
				children.push(label("definitionColorItemLabel_" + i, rect(16, ry, Math.max(60, rowWidth - 150), 24), String(entry.label || ""), {
					fontRole: "caption",
					weight: 600
				}), label("definitionColorItemValue_" + i, rect(Math.max(80, rowWidth - 130), ry, 116, 24), String(entry.color || ""), Object.assign({
					fontRole: "caption",
					align: "right"
				}, muted)));
			}
			totalH += entries.length * 28 + 12;
		}
	}
	return {
		kind: "Box",
		id: "definitionColorsSection",
		title: "Colors",
		fullWidth: true,
		height: totalH,
		showDivider: false,
		props: {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			radius: 8,
			children
		}
	};
}
function configsSectionField(layers, ui, formWidth, tr) {
	const open = ui.configsOpen !== false;
	const listLayers = layers || [];
	const rowWidth = Math.max(200, formWidth - 32);
	const children = [node("Action", "definitionConfigsToggle", rect(0, 0, rowWidth, 34), {
		text: tr("Definitions in Config (Advanced)"),
		normalColor: "surfaceContainerHigh",
		selectedColor: "contentSelection",
		action: {
			type: "toggleSection",
			section: "configs"
		},
		children: [node("Icon", "definitionConfigsToggleIcon", rect(8, 9, 16, 16), {
			icon: open ? "chevron-down" : "chevron-right",
			color: "primary"
		}), label("definitionConfigsToggleLabel", rect(28, 0, rowWidth - 40, 34), tr("Definitions in Config (Advanced)"), {
			fontRole: "body",
			weight: 600
		})]
	})];
	let totalH = 34;
	if (open) {
		if (!listLayers.length) {
			children.push(label("definitionConfigsEmptyLabel", rect(12, totalH + 6, rowWidth - 24, 28), tr("Select a Search Type to inspect layered definitions."), muted));
			totalH += 40;
		} else {
			totalH += 4;
			for (let i = 0; i < listLayers.length; i++) {
				const layer = listLayers[i];
				const layerOpen = !!ui.expandedLayers[layer.key];
				const lid = "definitionConfigLayer_" + sanitizeId(layer.key);
				children.push(node("Action", lid, rect(4, totalH, rowWidth - 8, 30), {
					text: layer.label,
					normalColor: "transparent",
					selectedColor: "contentSelection",
					enabled: !!layer.defined && !!layer.xml,
					action: {
						type: "toggleLayer",
						key: layer.key
					},
					children: [
						node("Icon", lid + "_Arrow", rect(8, 7, 15, 15), {
							icon: layerOpen ? "chevron-down" : "chevron-right",
							color: layer.defined ? "primaryText" : "secondaryText"
						}),
						label(lid + "_Label", rect(28, 0, rowWidth - 64, 30), layer.label, {
							fontRole: "caption",
							weight: layer.defined ? 600 : 400,
							color: layer.defined ? "primaryText" : "secondaryText"
						}),
						node("Box", lid + "_Dot", rect(rowWidth - 28, 9, 12, 12), {
							background: layer.defined ? "green" : "error",
							border: "outlineVariant",
							radius: 6,
							children: [label(lid + "_DotText", rect(0, 0, 12, 12), "")]
						})
					]
				}));
				totalH += 32;
				if (layerOpen && layer.xml) {
					children.push(node("Area", lid + "_Xml", rect(24, totalH, rowWidth - 36, 96), {
						text: layer.xml,
						label: layer.label,
						monospace: true,
						readOnly: true
					}));
					totalH += 102;
				}
			}
			totalH += 6;
		}
	}
	return {
		kind: "Box",
		id: "definitionConfigsSection",
		title: "Definitions in Config (Advanced)",
		fullWidth: true,
		height: totalH,
		showDivider: false,
		props: {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			radius: 8,
			children
		}
	};
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text) => translate(text, language), notice = notices(model, ui, width, language, "Discard unsaved definition changes?"), nodes = notice.nodes;
	const y = notice.top, minimum = y + 380;
	if (height < minimum) return { nodes: [node("Scroll", "columnsPageScroll", rect(0, 0, width, height), {
		contentHeight: minimum,
		scrollbarId: "columnsPageScrollBar",
		children: describe(model, ui, width - 16, minimum, language).nodes
	})] };
	const split = width >= 850, catalogVisible = ui.catalogVisible !== false, left = split ? catalogVisible ? Math.min(ui.catalogWidth, width * .44) : 56 : width, h = height - y;
	const edit = policy(model).editable && !ui.confirmation, navigate = !model.busy && !model.dirty && !model.uncertain && !ui.confirmation;
	if (split || !ui.editing) {
		const filteredRecords = records(model, ui), children = [];
		if (!split || catalogVisible) {
			children.push(label("definitionCatalogHeading", rect(12, 10, Math.max(0, left - (split ? 108 : 70)), 34), tr("Saved definitions"), { weight: 600 }), label("definitionCatalogCount", rect(left - (split ? 92 : 58), 10, 42, 34), String(filteredRecords.length), muted), node("Choice", "definitionCatalogSearchTypeFilter", rect(12, 52, left - 24, 38), {
				label: tr("Filter by Search Type"),
				value: ui.searchType,
				options: [{
					value: "",
					label: tr("All Search Types")
				}].concat(model.typeOptions.map((row) => ({
					value: row.value,
					label: row.label
				}))),
				enabled: navigate,
				action: { type: "searchType" }
			}), node("Field", "definitionCatalogFilter", rect(12, 98, left - 24, 38), {
				text: ui.query,
				label: tr("Filter saved views"),
				placeholder: tr("Filter saved views"),
				enabled: navigate,
				action: { type: "query" }
			}), list("definitionCatalogList", rect(12, 144, left - 24, Math.max(0, h - 156)), "definitions", 64));
			if (!filteredRecords.length) children.push(label("definitionCatalogEmpty", rect(24, 156, left - 48, 100), tr(model.busy ? "Working on the server…" : "No saved definitions match the filter"), {
				wrap: true,
				color: "secondaryText"
			}));
		}
		if (split) children.push(button("columnsToggleCatalog", rect(catalogVisible ? left - 46 : (left - 34) / 2, 10, 34, 34), tr(catalogVisible ? "Hide saved definitions" : "Show saved definitions"), catalogVisible ? "chevron-left" : "chevron-right", { type: "catalogVisible" }, true, {
			iconOnly: true,
			iconAction: true,
			round: false
		}));
		nodes.push(node("Box", "definitionCatalogPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
	}
	if (split && catalogVisible) nodes.push(node("Splitter", "columnsCatalogSplitHandle", rect(left, y, 10, h), {
		text: tr("Saved definitions panel width"),
		min: 220,
		max: width * .44,
		value: left,
		action: {
			type: "split",
			field: "catalogWidth"
		}
	}));
	if (split || ui.editing) editor(nodes, model, ui, rect(split ? left + 10 : 0, y, split ? width - left - 10 : width, h), language, edit, !split);
	return { nodes };
}
function editor(nodes, model, ui, bounds, language, edit, back) {
	const tr = (text) => translate(text, language), width = bounds.width, inner = width - 40, children = [];
	let y = 12;
	if (back) {
		children.push(button("columnsBack", rect(12, y, 100, 36), tr("Back"), "chevron-left", { type: "back" }, !model.busy));
		y += 44;
	}
	if (!model.ready) children.push(label("columnsSelectHelp", rect(12, y, inner, 100), tr("Select a definition"), {
		wrap: true,
		color: "secondaryText"
	}));
	else {
		const selected = model.selected, compactHeader = width < 620, modeTabsW = compactHeader ? Math.floor((width - 32) / 2) : 176, viewEditTabsW = compactHeader ? width - 32 - modeTabsW : Math.min(240, Math.max(180, width - 380)), tabsX = compactHeader ? 12 + viewEditTabsW + 8 : width - modeTabsW - 12, viewEditX = compactHeader ? 12 : tabsX - viewEditTabsW - 8, metaText = [
			selected.searchType,
			selected.login,
			model.wizard?.layout ? tr("Layout: ") + model.wizard.layout : ""
		].filter(Boolean).join(" · ");
		children.push(label("definitionViewTitle", rect(12, y, compactHeader ? inner : Math.max(80, viewEditX - 20), 24), selected.view, {
			fontRole: "section",
			weight: 600
		}));
		if (!compactHeader && metaText) {
			const titleW = Math.min(180, selected.view.length * 9 + 16);
			if (viewEditX - 24 - titleW > 40) children.push(label("definitionViewType", rect(12 + titleW, y + 2, Math.max(1, viewEditX - 24 - titleW), 22), metaText, muted));
		}
		if (compactHeader && metaText) {
			y += 26;
			children.push(label("definitionViewType", rect(12, y, inner, 20), metaText, muted));
			y += 24;
		}
		children.push(tabs("definitionViewEditMode", [{
			value: "view",
			label: tr("VIEW MODE"),
			icon: "eye"
		}, {
			value: "edit",
			label: tr("EDIT MODE"),
			icon: "edit"
		}], ui.viewMode || "view", rect(viewEditX, compactHeader ? y : y - 4, viewEditTabsW, 34), !model.busy, "viewMode"), tabs("definitionCatalogMode", [{
			value: "simple",
			label: tr("Form"),
			icon: "table"
		}, {
			value: "xml",
			label: "XML",
			icon: "code"
		}], ui.mode, rect(tabsX, compactHeader ? y : y - 4, modeTabsW, 34), !model.busy, "mode"));
		y += compactHeader ? 42 : 38;
		if (ui.mode === "xml") children.push(node("Area", "definitionCatalogXml", rect(12, y, width - 24, bounds.height - y - 42), {
			text: model.xml,
			label: tr("Definition XML"),
			monospace: true,
			enabled: edit,
			action: { type: "xml" }
		}));
		else if (model.wizard.supported && model.elements.length) {
			const stacked = width < 720, columnWidth = stacked ? width - 24 : Math.min(ui.columnWidth, width * .4), columnHeight = stacked ? Math.min(ui.columnHeight, (bounds.height - y - 42) * .48) : bounds.height - y - 42, selectedIndex = model.elements.findIndex((row) => row.path === model.element.path), defElements = model.definitionElements || [], hasDefSection = defElements.length > 0 && columnHeight >= 220, topListH = hasDefSection ? Math.max(84, Math.floor((columnHeight - 72) * .52)) : Math.max(40, columnHeight - 34), canRemoveFromView = edit && !pending(ui) && model.elements.length > 1 && selectedIndex >= 0 && [
				"definition",
				"default_definition",
				"edit_definition"
			].indexOf(selected.view) < 0;
			children.push(label("definitionColumnsLabel", rect(12, y + 2, Math.max(40, columnWidth - 110), 24), humanizeOptionName(selected.view || "Columns"), {
				fontRole: "secondary",
				weight: 600,
				color: "primaryText"
			}));
			for (const [offset, title, icon, x] of [[
				-1,
				"Move up",
				"arrow-up",
				12 + columnWidth - 106
			], [
				1,
				"Move down",
				"arrow-down",
				12 + columnWidth - 70
			]]) children.push(node("Button", offset < 0 ? "definitionColumnUp" : "definitionColumnDown", rect(x, y, 32, 28), {
				text: tr(title),
				icon,
				iconOnly: true,
				round: false,
				enabled: edit && !pending(ui) && selectedIndex >= 0 && !!model.elements[selectedIndex + offset],
				action: {
					type: "move",
					value: offset
				}
			}));
			children.push(node("Button", "definitionColumnRemove", rect(12 + columnWidth - 34, y, 32, 28), {
				text: tr("Remove from view"),
				icon: "delete",
				iconOnly: true,
				round: false,
				destructive: true,
				enabled: canRemoveFromView,
				action: { type: "removeElement" }
			}), list("definitionCatalogElementList", rect(12, y + 32, columnWidth, topListH), "columns", 52));
			if (hasDefSection) {
				const defHeaderY = y + 32 + topListH + 8, defListY = defHeaderY + 28, defListH = Math.max(48, y + columnHeight - defListY), rowW = Math.max(80, columnWidth - 16), defRowH = 44;
				children.push(label("definitionAllColumnsHeading", rect(12, defHeaderY, Math.max(40, columnWidth - 52), 24), tr("Definition"), {
					fontRole: "secondary",
					weight: 600,
					color: "primaryText"
				}), label("definitionAllColumnsCount", rect(12 + columnWidth - 44, defHeaderY, 44, 24), String(defElements.length), Object.assign({ align: "right" }, muted)));
				const defRows = [];
				for (let i = 0; i < defElements.length; i++) {
					const item = defElements[i];
					const itemKey = sanitizeId(item.name || i);
					const isSelected = model.element.name === item.name && model.element.path === item.path;
					const canAdd = edit && !pending(ui) && !item.inView && ["definition", "default_definition"].indexOf(selected.view) < 0;
					const textW = canAdd ? rowW - 72 : rowW - 38;
					const shortWidget = (item.widget || "").split(".").pop();
					defRows.push(node("Action", "definitionAllColumn_" + itemKey, rect(0, i * defRowH, canAdd ? rowW - 34 : rowW, 42), {
						text: item.name,
						selected: isSelected,
						normalColor: "transparent",
						selectedColor: "contentSelection",
						rail: false,
						enabled: !model.busy && !ui.confirmation,
						action: {
							type: "column",
							path: item.path
						},
						children: [
							node("Icon", "definitionAllColumnIcon_" + itemKey, rect(8, 12, 16, 16), {
								icon: item.inView ? "check-circle" : "cube",
								color: item.inView ? "action" : "secondaryText"
							}),
							label("definitionAllColumnTitle_" + itemKey, rect(30, 3, Math.max(20, textW), 20), item.title || item.name, {
								fontRole: "caption",
								weight: 600
							}),
							label("definitionAllColumnDetail_" + itemKey, rect(30, 22, Math.max(20, textW), 16), item.name + (shortWidget ? " · " + shortWidget : ""), Object.assign({ fontRole: "caption" }, muted))
						]
					}));
					if (canAdd) defRows.push(node("Button", "definitionAddColumn_" + itemKey, rect(rowW - 30, i * defRowH + 6, 28, 28), {
						text: tr("Add to view"),
						icon: "add",
						iconOnly: true,
						round: false,
						enabled: true,
						action: {
							type: "addElement",
							name: item.name
						}
					}));
				}
				children.push(node("Box", "definitionAllColumnsBox", rect(12, defListY, columnWidth, defListH), {
					background: "surfaceContainer",
					border: "outlineVariant",
					radius: 8,
					children: [node("Scroll", "definitionAllColumnsScroll", rect(2, 2, columnWidth - 4, Math.max(1, defListH - 4)), {
						contentHeight: Math.max(defListH - 4, defElements.length * defRowH),
						scrollbarId: "definitionAllColumnsScrollBar",
						children: defRows
					})]
				}));
			}
			children.push(node("Splitter", "definitionColumnsSplitHandle", rect(stacked ? 12 : 12 + columnWidth, stacked ? y + columnHeight : y, stacked ? columnWidth : 10, stacked ? 10 : columnHeight), {
				horizontal: stacked,
				text: tr(stacked ? "Columns list height" : "Columns list width"),
				value: stacked ? columnHeight : columnWidth,
				min: stacked ? 100 : 180,
				max: stacked ? Math.max(100, bounds.height * .48) : width * .4,
				action: {
					type: "split",
					field: stacked ? "columnHeight" : "columnWidth"
				}
			}));
			const formX = stacked ? 12 : columnWidth + 22, formY = stacked ? y + columnHeight + 10 : y, formWidth = width - formX - 28;
			const element = model.element, text = (key) => Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : elementFieldValue(element, key), isEditMode = ui.viewMode === "edit";
			let fields = [{
				kind: "Heading",
				id: "definitionColumnHeading",
				title: isEditMode ? "Edit Mode Definition" : "Edit Column Definition",
				description: isEditMode ? "Configure how this column is edited in tables and forms (edit / edit_definition)." : "Configure display attributes, widget options, colors, and layered definitions."
			}, {
				kind: "Label",
				id: "definitionWidgetIdentifier",
				fullWidth: true,
				height: Math.max(34, captionHeight(element.widget || tr("Inherited from definition"), formWidth - 32)),
				props: {
					text: element.widget || tr("Inherited from definition"),
					wrap: true
				}
			}];
			if (element.inView === false && element.name && ["definition", "default_definition"].indexOf(selected.view) < 0) fields.push({
				kind: "Button",
				id: "definitionAddSelectedToView",
				title: "Add column to current view",
				props: {
					icon: "add",
					highlighted: true,
					enabled: edit && !pending(ui),
					action: {
						type: "addElement",
						name: element.name
					}
				}
			});
			if (!isEditMode) {
				const displaySpecs = displayWidgetArgs(element.widget || element.displayClass);
				fields = fields.concat([
					{
						id: "definitionCatalogTitle",
						title: "Title",
						description: "The column heading shown to users.",
						field: "title",
						props: {
							text: text("title"),
							placeholder: element.name || "",
							action: {
								type: "text",
								field: "title"
							},
							commitAction: { type: "commit" }
						}
					},
					{
						kind: "Label",
						id: "definitionCatalogName",
						title: "Name",
						description: "Native field identifier.",
						props: { text: element.name || "" }
					},
					{
						kind: "Number",
						min: 48,
						max: 640,
						step: 8,
						value: element.width,
						id: "definitionCatalogWidth",
						title: "Width",
						description: "Default width in the table view.",
						field: "width",
						props: {
							text: text("width"),
							inputMode: "numeric",
							action: {
								type: "text",
								field: "width"
							},
							commitAction: { type: "commit" },
							keys: {
								ArrowUp: {
									type: "step",
									value: 8
								},
								ArrowDown: {
									type: "step",
									value: -8
								}
							}
						}
					},
					{
						kind: "Switch",
						id: "definitionCatalogColor",
						title: "Enable Colors",
						description: "Apply value-based cell colors from the color config.",
						field: "color",
						props: { checked: element.color !== false }
					},
					{
						kind: "Switch",
						id: "definitionCatalogVisible",
						title: "Show in table",
						description: "Keep the column visible in this saved view.",
						field: "visible",
						props: { checked: element.visible !== false }
					},
					{
						id: "definitionCatalogValueIcon",
						kind: "IconChoice",
						title: "Cell icon",
						description: "Icon beside text values and related-table counts. Used by quick filters unless overridden.",
						field: "valueIcon",
						props: {
							value: Object.prototype.hasOwnProperty.call(element, "valueIcon") ? element.valueIcon : element.name === "duration" ? "clock" : "",
							tacticCompatibleOnly: true
						}
					},
					{
						kind: "Choice",
						id: "definitionCatalogTextStyle",
						title: "Cell text style",
						description: "Size and emphasis of text values in this column.",
						field: "valueTextStyle",
						options: [
							{
								value: "",
								label: tr("Standard")
							},
							{
								value: "heading",
								label: tr("Heading")
							},
							{
								value: "small",
								label: tr("Small text")
							}
						],
						props: { value: element.valueTextStyle || "" }
					},
					{
						kind: "Choice",
						id: "definitionCatalogValueAlign",
						title: "Cell alignment",
						description: "Horizontal position of content in this column.",
						field: "valueAlign",
						options: [
							{
								value: "",
								label: tr("Automatic")
							},
							{
								value: "left",
								label: tr("Left")
							},
							{
								value: "center",
								label: tr("Center")
							},
							{
								value: "right",
								label: tr("Right")
							}
						],
						props: { value: element.valueAlign || "" }
					},
					{
						kind: "Choice",
						id: "definitionCatalogValueStyle",
						title: "Value appearance",
						description: "Automatic shows Duration as a badge.",
						field: "valueStyle",
						options: [
							{
								value: "",
								label: tr("Automatic")
							},
							{
								value: "text",
								label: tr("Text")
							},
							{
								value: "badge",
								label: tr("Badge")
							}
						],
						props: { value: element.valueStyle || "" }
					},
					{
						kind: "Heading",
						id: "definitionDisplayOptionsHeading",
						title: "Display Options",
						description: "Widget type, Python class path, and widget-specific <display> parameters."
					},
					{
						kind: "Choice",
						id: "definitionCatalogWidget",
						title: "Widget Type",
						description: "Choose a supported TACTIC table widget.",
						field: "widget",
						options: model.widgetOptions.map((row) => ({
							value: row.value,
							label: tr(row.label)
						})),
						props: { value: element.widget || "" }
					},
					{
						kind: "Switch",
						id: "definitionCatalogShowAllWidgets",
						title: "Show specialized and system widgets",
						description: "Include task, snapshot, timecard, JSON/XML, and administrative table widgets.",
						props: {
							checked: !!ui.showAllWidgets,
							action: { type: "showAllWidgets" }
						}
					},
					{
						id: "definitionCatalogDisplayClass",
						title: "Class Name",
						description: "Explicit Python class name (<display class=\"...\"/>), e.g. ThumbWdg.",
						field: "displayClass",
						props: {
							text: Object.prototype.hasOwnProperty.call(ui.text, "displayClass") ? ui.text.displayClass : element.displayClass || element.widget || "",
							placeholder: "pyasm.widget.ThumbWdg",
							action: {
								type: "text",
								field: "displayClass"
							},
							commitAction: { type: "commit" }
						}
					},
					widgetPreviewField(element, text("title") || element.title, formWidth, tr)
				]);
				fields = fields.concat(buildOptionFields(displaySpecs, element.displayOptions || {}, "option", ui, text, tr, "definitionDisplay"));
				fields.push(colorsSectionField(element, ui, formWidth, tr), configsSectionField(element.configLayers || [], ui, formWidth, tr));
			} else {
				const editSpecs = editWidgetArgs(element.editWidget || element.editClass);
				const editChoices = editWidgetOptionsFor(element.editWidget).map((row) => ({
					value: row.value,
					label: tr(row.label)
				}));
				fields = fields.concat([
					{
						kind: "Label",
						id: "definitionCatalogName",
						title: "Name",
						description: "Native field identifier.",
						props: { text: element.name || "" }
					},
					{
						kind: "Switch",
						id: "definitionCatalogEditable",
						title: "Enable Edit",
						description: "Allow editing this column in tables and forms.",
						field: "editable",
						props: { checked: element.editable !== false }
					},
					{
						kind: "Heading",
						id: "definitionEditOptionsHeading",
						title: "Edit Options",
						description: "Input widget type, Python class name, and <edit> / <display> parameters."
					},
					{
						kind: "Choice",
						id: "definitionCatalogEditWidget",
						title: "Widget Type",
						description: "Choose an input widget for editing.",
						field: "editWidget",
						options: editChoices,
						props: { value: element.editWidget || "" }
					},
					{
						id: "definitionCatalogEditClass",
						title: "Class Name",
						description: "Explicit input widget class name, e.g. pyasm.widget.SelectWdg.",
						field: "editClass",
						props: {
							text: Object.prototype.hasOwnProperty.call(ui.text, "editClass") ? ui.text.editClass : element.editClass || element.editWidget || "",
							placeholder: "pyasm.widget.TextWdg",
							action: {
								type: "text",
								field: "editClass"
							},
							commitAction: { type: "commit" }
						}
					}
				]);
				fields = fields.concat(buildOptionFields(editSpecs, element.editOptions || {}, "editOption", ui, text, tr, "definitionEdit"));
				fields.push({
					kind: "Heading",
					id: "definitionEditActionHeading",
					title: "Action",
					description: "Server command executed when saving this field (<action class=\"...\"/>)."
				}, {
					id: "definitionCatalogActionClass",
					title: "Action Class Name",
					description: "Optional command handler class, e.g. pyasm.command.NullAction.",
					field: "actionClass",
					props: {
						text: text("actionClass"),
						placeholder: "pyasm.command.DatabaseAction",
						action: {
							type: "text",
							field: "actionClass"
						},
						commitAction: { type: "commit" }
					}
				});
				const actionOptKeys = Object.keys(element.actionOptions || {});
				for (let a = 0; a < actionOptKeys.length; a++) {
					const aKey = actionOptKeys[a];
					const aField = "actionOption:" + aKey;
					fields.push({
						id: "definitionActionOpt_" + sanitizeId(aKey),
						title: humanizeOptionName(aKey),
						dataLabel: true,
						description: "<action><" + aKey + ">",
						field: aField,
						props: {
							text: text(aField),
							action: {
								type: "text",
								field: aField
							},
							commitAction: { type: "commit" }
						}
					});
				}
				fields.push(configsSectionField(element.editConfigLayers || [], ui, formWidth, tr));
			}
			fields = fields.concat([
				{
					kind: "Heading",
					id: "definitionElementXmlHeading",
					title: "Selected element XML"
				},
				{
					kind: "Area",
					id: "definitionCatalogElementXml",
					title: "Selected element XML",
					fullWidth: true,
					height: 180,
					props: {
						text: text("xml"),
						monospace: true,
						wrap: false,
						action: {
							type: "text",
							field: "xml"
						}
					}
				},
				{
					kind: "Button",
					id: "definitionApplyElementXml",
					title: "Apply XML",
					props: {
						icon: "code",
						enabled: edit && Object.prototype.hasOwnProperty.call(ui.text, "xml"),
						action: { type: "commit" }
					}
				}
			]);
			const body = sections(fields, formWidth, language, edit);
			children.push(node("Scroll", "definitionCatalogForm", rect(formX, formY, width - formX - 12, Math.max(1, bounds.height - formY - 42)), {
				contentHeight: body.height,
				resetKey: ui.path + ":" + (ui.viewMode || "view"),
				scrollbarId: "definitionCatalogFormScrollBar",
				children: body.nodes
			}));
		} else children.push(label("definitionCatalogWizardEmpty", rect(12, y, width - 24, 100), tr(model.wizard.error || (model.wizard.supported ? "This TACTIC view has no columns. Add elements in XML mode." : "This definition does not use a native TACTIC table layout. Open XML to edit its exact structure.")), {
			wrap: true,
			color: "secondaryText"
		}), button("definitionOpenXml", rect(12, y + 108, inner, 38), tr("Open XML"), "code", {
			type: "mode",
			value: "xml"
		}, !model.busy));
		children.push(label("definitionCode", rect(12, bounds.height - 30, inner, 22), selected.code || "", muted));
	}
	nodes.push(node("Box", "definitionEditorPanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	}));
}
function row(listNode, record, model, ui) {
	const width = listNode.width - 16, definition = listNode.source === "definitions", selected = definition ? model.selected.identity === record.identity : model.element.path === record.path;
	return { nodes: [node("Action", definition ? "definitionRow_" + record.identity : "definitionColumn_" + record.path, rect(0, 0, width, definition ? 60 : 48), {
		text: definition ? record.view + " · " + record.searchType + (record.login ? " · " + record.login : "") : record.name,
		selected,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		rail: false,
		enabled: !model.busy && !ui.confirmation && (!definition || !model.dirty && !model.uncertain),
		action: definition ? {
			type: "select",
			identity: record.identity
		} : {
			type: "column",
			path: record.path
		},
		children: [
			node("Icon", "definitionRowIcon_" + (record.identity || record.path), rect(10, definition ? 18 : 15, 18, 18), {
				icon: definition ? "table" : record.visible ? "eye" : "eye-off",
				color: "action"
			}),
			label("definitionRowTitle_" + (record.identity || record.path), rect(38, definition ? 6 : 4, width - 48, 22), definition ? record.view : record.title, { weight: 600 }),
			label("definitionRowDetail_" + (record.identity || record.path), rect(38, definition ? 30 : 25, width - 48, 18), definition ? record.searchType + (record.login ? " · " + record.login : "") : record.name, muted)
		]
	})] };
}
//#endregion
//#region src/features/administration/ColumnsEditor.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		},
		initialFocus: Object
	},
	emits: ["saved"],
	data() {
		return {
			catalog: null,
			context: null,
			identity: "",
			xml: "",
			baseline: "",
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			busy: false,
			uncertain: false,
			error: "",
			message: "",
			request: 0
		};
	},
	computed: {
		frameModel() {
			return {
				ready: !!this.selected,
				canWrite: !!this.catalog && this.context?.ticket === this.ticket && this.context?.project === this.project,
				canLoad: !!this.ticket,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				message: this.message,
				xml: this.xml,
				records: this.catalog?.records || [],
				selected: this.selected || {},
				wizard: this.wizard,
				elements: this.wizard.elements || [],
				definitionElements: this.wizard.definitionElements || [],
				element: this.element || {},
				typeOptions: this.catalog?.searchTypes || [],
				widgetOptions: this.widgets.map((row) => ({
					...row,
					label: t(row.label)
				}))
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
				definitions: this.records,
				columns: this.wizard.elements || []
			};
		},
		dirty() {
			return this.uncertain || this.xml !== this.baseline || pending(this.ui);
		},
		editable() {
			return !!this.catalog && this.context?.ticket === this.ticket && this.context?.project === this.project && !this.busy && !this.uncertain;
		},
		records() {
			return records(this.frameModel, this.ui);
		},
		selected() {
			return this.catalog?.records.find((row) => row.identity === this.identity);
		},
		wizard() {
			try {
				return definitionWizard(this.xml, this.selected?.view, this.selected?.searchType, this.catalog?.records);
			} catch (error) {
				return {
					supported: false,
					elements: [],
					definitionElements: [],
					error: error.message
				};
			}
		},
		element() {
			return this.wizard.elements.find((row) => row.path === this.ui.path) || (this.wizard.definitionElements || []).find((row) => row.path === this.ui.path) || this.wizard.elements[0] || (this.wizard.definitionElements || [])[0];
		},
		widgets() {
			return widgetOptionsFor(this.element?.widget, this.ui.showAllWidgets);
		},
		typeChoices() {
			return [{
				value: "",
				label: t("All Search Types")
			}, ...this.catalog?.searchTypes || []];
		}
	},
	watch: {
		initialFocus() {
			if (this.presentationVisible && this.catalog && !this.dirty) this.focusRequestedColumn();
		},
		presentationVisible(value) {
			if (value && this.catalog && !this.dirty) this.focusRequestedColumn();
		},
		project() {
			this.request++;
			this.busy = false;
			this.catalog = null;
			this.xml = this.baseline = "";
			this.ui = initial();
			this.reload(true);
		},
		ticket() {
			this.request++;
			this.busy = false;
			this.catalog = null;
			this.xml = this.baseline = "";
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
		rowScene(node, record) {
			return row(node, record, this.frameModel, this.ui);
		},
		applyText() {
			const keys = Object.keys(this.ui.text).sort((a, b) => a === "xml" ? -1 : b === "xml" ? 1 : 0);
			for (const field of keys) {
				this.change(field, this.ui.text[field]);
				if (this.error) return false;
			}
			this.ui = transition(this.ui, this.frameModel, { type: "applied" }).ui;
			return true;
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			for (const command of result.commands) {
				if (![
					"reload",
					"discard",
					"xml"
				].includes(command.type) && !this.applyText()) return;
				switch (command.type) {
					case "apply": break;
					case "filter":
						this.ui = result.ui;
						this.filterChanged();
						break;
					case "select":
						this.select(command.identity);
						break;
					case "column": break;
					case "mode": break;
					case "back": break;
					case "change":
						this.change(command.field, command.value);
						if (this.error) return;
						break;
					case "xml":
						this.xml = command.value;
						this.message = "";
						break;
					case "save":
						await this.save();
						break;
					case "reload":
						await this.reload(true);
						break;
					case "discard":
						await this.discard();
						break;
					default: throw Error("Unsupported Columns command: " + command.type);
				}
				result.ui = completed(result.ui, command, this.frameModel);
			}
			this.ui = result.ui;
		},
		t,
		focusRequestedColumn() {
			if (this.initialFocus?.project !== this.project || !this.initialFocus?.searchType) return;
			this.ui = {
				...this.ui,
				query: "",
				searchType: this.initialFocus.searchType,
				editing: true
			};
			const source = definitionSource(this.catalog.records, this.initialFocus, (row) => definitionWizard(row.config, row.view).elements);
			this.select(source?.identity || "", true);
			if (!source && this.initialFocus.column) this.error = "Column definition was not found in saved configurations.";
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.busy) return false;
			if (this.dirty || this.uncertain) {
				this.error = "";
				this.dispatch({ type: "discard" });
				return false;
			}
			return true;
		},
		select(identity, force = false) {
			if (!force && (!this.editable || this.dirty)) return;
			this.identity = identity;
			this.xml = this.baseline = this.selected?.config || "";
			this.ui = selected(this.ui, this.wizard.elements, this.initialFocus?.column);
			this.error = "";
		},
		filterChanged() {
			if (!this.dirty) this.select(this.records.some((row) => row.identity === this.identity) ? this.identity : this.records[0]?.identity || "", true);
		},
		change(field, value) {
			if (!this.editable || !this.element) return;
			try {
				this.xml = changeDefinition(this.xml, this.element.path, field, value, this.element);
				this.error = "";
				this.message = "";
			} catch (error) {
				this.error = error.message;
			}
		},
		async reload(force = false) {
			if (this.busy || !this.ticket) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.dispatch({ type: "reload" });
				return;
			}
			const request = ++this.request, previous = this.identity, first = !this.catalog;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await columnsEditor("read", this.context.ticket, this.context.project);
				if (request !== this.request) return;
				this.catalog = result;
				this.uncertain = false;
				if (first && this.initialFocus?.project === this.project && this.initialFocus?.searchType) this.focusRequestedColumn();
				else this.select(this.records.find((row) => row.identity === previous)?.identity || this.records[0]?.identity || "", true);
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		async discard() {
			if (this.uncertain) await this.reload(true);
			else this.select(this.identity, true);
		},
		async save() {
			if (!this.editable || !this.dirty || !this.selected) return;
			const request = this.request;
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await columnsEditor("save", this.context.ticket, this.context.project, {
					source_id: this.selected.id,
					xml: this.xml,
					revision: this.catalog.revision
				});
				if (request !== this.request) return;
				this.catalog = result;
				this.select(result.selected, true);
				this.message = "TACTIC definition saved";
				this.$emit("saved", result);
				const source = result.records.find((row) => row.identity === result.selected);
				if (source) window.dispatchEvent(new CustomEvent("tactic-column-definition-saved", { detail: {
					project: this.context.project,
					searchType: source.searchType,
					view: source.view
				} }));
			} catch (error) {
				if (request !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Reload definitions before trying again." : error.message;
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
		class: "columns-editor frame-host",
		"aria-label": $options.t("Columns Editor"),
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
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"onEvent"
	])], 512)], 8, _hoisted_1);
}
var ColumnsEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ColumnsEditor_default as default };

//# sourceMappingURL=ColumnsEditor.js.map
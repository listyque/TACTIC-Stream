import { E as nextTick } from "./vue.js";
import { O as appearance } from "./index.js";
import { D as node, E as muted, O as rect, T as label, u as translate, w as button } from "./FrameView.js";
import { n as observeFrameSizes } from "./resize.js";
import { n as sections } from "./sections.ui.js";
import { i as sectionSelector, n as notices, o as toolbar$1, r as policy, t as documentEvent } from "./admin.document.js";
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/workflow.fields.mjs
var fieldGroups = [
	{
		title: "Appearance",
		description: "",
		fields: [{
			section: "properties",
			key: "label",
			label: "Display label",
			help: "Shown on the canvas without changing the process name.",
			editor: "text"
		}, {
			section: "properties",
			key: "color",
			label: "Color",
			help: "Used for this process on the canvas and in task views.",
			editor: "color"
		}]
	},
	{
		title: "Task settings",
		description: "Assignment choices and default estimates for this process.",
		kinds: [
			"manual",
			"node",
			"approval"
		],
		fields: [
			{
				section: "properties",
				key: "assigned_group",
				label: "Assigned group",
				help: "Limits the available assignees to members of this group.",
				options: "groups"
			},
			{
				section: "properties",
				key: "supervisor_group",
				label: "Supervisor group",
				help: "Limits the available supervisors to members of this group.",
				options: "groups"
			},
			{
				section: "properties",
				key: "duration",
				label: "Default duration, days",
				help: "Initial interval between a task's start and end dates.",
				editor: "integer"
			},
			{
				section: "properties",
				key: "bid_duration",
				label: "Estimated work, hours",
				help: "Default planned effort for a new task.",
				editor: "integer"
			},
			{
				section: "properties",
				key: "completion",
				label: "Completion, %",
				help: "Completion level represented by this process or status.",
				editor: "integer",
				maximum: 100
			},
			{
				section: "properties",
				key: "task_creation",
				label: "Create tasks",
				help: "Include this process when generating tasks.",
				editor: "boolean",
				initial: true
			},
			{
				section: "properties",
				key: "autocreate_task",
				label: "Create tasks automatically",
				help: "Create a task when a workflow event reaches this process.",
				editor: "boolean"
			},
			{
				section: "",
				key: "task_number",
				label: "Number of tasks",
				help: "How many tasks to create for this process.",
				editor: "integer",
				minimum: 1
			}
		]
	},
	{
		title: "Approval",
		description: "Default reviewer for approval tasks.",
		kinds: ["approval"],
		fields: [{
			section: "default",
			key: "assigned",
			label: "Assigned user",
			help: "Choose an existing user to receive approval tasks.",
			options: "users"
		}]
	},
	{
		title: "Related workflow",
		description: "Choose which objects and processes this node signals or tracks.",
		kinds: ["dependency", "progress"],
		fields: [
			{
				key: "related_search_type",
				label: "Search Type",
				help: "The related objects affected by this node.",
				options: "searchTypes"
			},
			{
				key: "related_pipeline_code",
				label: "Related pipeline",
				help: "Only pipelines of the selected Search Type are listed.",
				options: "relatedPipelines"
			},
			{
				key: "related_process",
				label: "Related process",
				help: "The process to signal or listen to; leave empty to use the native default.",
				options: "relatedProcesses"
			},
			{
				key: "related_scope",
				label: "Scope",
				help: "Affect related objects only, or all objects of this Search Type.",
				choices: [{
					identity: "local",
					label: "Related objects"
				}, {
					identity: "global",
					label: "All objects"
				}],
				initial: "local"
			},
			{
				key: "related_status",
				label: "Signal",
				help: "The native workflow signal sent to the related process.",
				choices: [
					{
						identity: "Pending",
						label: "Pending"
					},
					{
						identity: "Action",
						label: "Action"
					},
					{
						identity: "Complete",
						label: "Complete"
					}
				],
				kinds: ["dependency"]
			},
			{
				key: "related_wait",
				label: "Wait for completion",
				help: "Wait for a completion signal instead of completing this node immediately.",
				editor: "boolean",
				kinds: ["dependency"]
			},
			{
				key: "expression",
				label: "Related object expression",
				help: "Optional TACTIC search expression; it replaces selection by Search Type.",
				editor: "text"
			}
		]
	},
	{
		title: "Status behavior",
		description: "Map this status to a native behavior, or explicitly change a connected process.",
		kinds: ["status"],
		fields: [
			{
				section: "default",
				key: "mapping",
				label: "Behave as",
				help: "Native task status behavior.",
				choices: [
					{
						identity: "Assignment",
						label: "Assignment"
					},
					{
						identity: "Pending",
						label: "Pending"
					},
					{
						identity: "In Progress",
						label: "In Progress"
					},
					{
						identity: "Waiting",
						label: "Waiting"
					},
					{
						identity: "Need Assistance",
						label: "Need Assistance"
					},
					{
						identity: "Revise",
						label: "Revise"
					},
					{
						identity: "Reject",
						label: "Reject"
					},
					{
						identity: "Complete",
						label: "Complete"
					},
					{
						identity: "Approved",
						label: "Approved"
					}
				]
			},
			{
				section: "default",
				key: "direction",
				label: "Change process",
				help: "Used when no status mapping is selected.",
				choices: [
					{
						identity: "output",
						label: "Output process"
					},
					{
						identity: "input",
						label: "Input process"
					},
					{
						identity: "process",
						label: "This process"
					}
				]
			},
			{
				section: "default",
				key: "status",
				label: "Target status",
				help: "Exact status name understood by the target process.",
				editor: "text"
			}
		]
	}
];
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/process.ui.mjs
function section(field, kind) {
	return field.section === void 0 ? kind === "progress" ? "progress" : "default" : field.section;
}
function value(model, field) {
	const part = section(field, model.processKind), source = part === "properties" ? model.processProperties : part ? (model.processSettings || {})[part] : model.processSettings;
	return source && source[field.key] !== void 0 ? source[field.key] : field.initial === void 0 ? "" : field.initial;
}
function options(model, field, language) {
	const tr = (text) => translate(text, language), related = (model.processSettings || {})[model.processKind === "progress" ? "progress" : "default"] || {}, catalog = model.processCatalog || model.metadata || {};
	let rows = field.choices || catalog[field.options] || [];
	if (field.options === "relatedPipelines") rows = (catalog.pipelines || []).filter((row) => row.searchType === related.related_search_type);
	if (field.options === "relatedProcesses") rows = (catalog.processes || []).filter((row) => row.pipeline === related.related_pipeline_code).map((row) => ({
		identity: model.processKind === "progress" ? row.identity : row.label,
		label: row.label
	}));
	return [{
		value: "",
		label: tr("Not set")
	}].concat(rows.map((row) => ({
		value: row.identity,
		label: field.choices ? tr(row.label) : row.label || row.identity
	})));
}
function fields(model, ui, language) {
	const tr = (text) => translate(text, language), kind = model.processKind, settings = model.processSettings || {}, defaults = settings.default || {}, catalog = model.processCatalog || model.metadata || {};
	const out = [{
		kind: "Heading",
		id: "processHeading",
		title: model.selectedNode,
		dataLabel: true,
		description: tr("Node type: %1").replace("%1", kind)
	}, {
		id: "adminProcessDescription",
		title: "Description",
		description: "Explain what happens at this stage of the workflow.",
		props: {
			text: model.processDescription || "",
			action: { type: "description" }
		}
	}];
	const setting = (key, title, part, initial, choices, description) => ({
		id: "adminProcessField_" + key,
		title,
		description,
		kind: choices ? "Choice" : "Field",
		options: choices,
		props: Object.assign({ action: {
			type: "setting",
			section: part,
			key
		} }, choices ? { value: (settings[part] || {})[key] === void 0 ? initial : (settings[part] || {})[key] } : { text: String((settings[part] || {})[key] || initial || "") })
	});
	if ([
		"manual",
		"node",
		"approval"
	].indexOf(kind) >= 0) out.push({
		kind: "Heading",
		id: "processTaskPipelineHeading",
		title: "Task status workflow",
		description: "Defines statuses only for tasks of this process, not stages of the parent Search Object workflow."
	}, {
		kind: "Choice",
		id: "adminProcessField_task_pipeline",
		fullWidth: true,
		title: "Task status workflow",
		options: [{
			value: "",
			label: tr("Use TACTIC default")
		}].concat((catalog.pipelines || []).filter((row) => row.searchType === "sthpw/task").map((row) => ({
			value: row.identity,
			label: row.label || row.identity
		}))),
		props: {
			value: model.processProperties.task_pipeline || "",
			action: {
				type: "setting",
				section: "properties",
				key: "task_pipeline"
			}
		}
	}, {
		kind: "Button",
		id: "adminEditTaskWorkflow",
		title: "Edit task status workflow",
		props: {
			icon: "edit",
			enabled: !model.busy && !!model.processProperties.task_pipeline,
			action: { type: "taskWorkflow" }
		}
	});
	for (const group of fieldGroups.filter((row) => !row.kinds || row.kinds.indexOf(kind) >= 0)) {
		out.push({
			kind: "Heading",
			id: "processGroup_" + group.title.replace(/\W/g, ""),
			title: group.title,
			description: group.description
		});
		for (const field of group.fields.filter((row) => !row.kinds || row.kinds.indexOf(kind) >= 0)) {
			const current = value(model, field), part = section(field, kind), id = "adminProcessField_" + field.key, integer = field.editor === "integer";
			out.push({
				id,
				title: field.label,
				description: field.help,
				kind: field.editor === "boolean" ? "Switch" : field.editor === "color" ? "ColorChoice" : !field.editor ? "Choice" : "Field",
				options: !field.editor ? options(model, field, language) : void 0,
				props: Object.assign({ action: integer ? {
					type: "buffer",
					key: "integer_" + part + "_" + field.key
				} : {
					type: "setting",
					section: part,
					key: field.key
				} }, field.editor === "boolean" ? { checked: current === true || current === "true" } : !field.editor || field.editor === "color" ? { value: current } : {
					text: Object.prototype.hasOwnProperty.call(ui.text, "integer_" + part + "_" + field.key) ? ui.text["integer_" + part + "_" + field.key] : String(current),
					inputMode: integer ? "numeric" : "text",
					commitAction: integer ? {
						type: "integer",
						section: part,
						key: field.key,
						min: field.minimum || 0,
						max: field.maximum || 1e6
					} : null
				})
			});
		}
	}
	out.push({
		kind: "Heading",
		id: "processDependenciesHeading",
		title: "Process dependencies",
		description: "Triggers, notifications, naming conventions and objects using this pipeline. Save node changes before editing dependencies."
	}, {
		kind: "Button",
		id: "adminOpenProcessDependencies",
		title: "Open process dependencies",
		props: {
			icon: "schema",
			enabled: !model.busy && !model.uncertain,
			action: { type: "dependencies" }
		}
	});
	if (["action", "condition"].indexOf(kind) >= 0) {
		out.push({
			kind: "Heading",
			id: "processActionHeading",
			title: "Process action",
			description: "Action and condition nodes use a native process|action trigger. Script changes are saved, not executed by this editor."
		}, setting("action", "Action", "default", "create_new", [{
			value: "create_new",
			label: tr("Script")
		}, {
			value: "command",
			label: tr("Command class")
		}], "Use a script or an installed server command class."));
		if (defaults.action === "command") out.push(setting("on_action_class", "Native command class", "default", "", "", "The installed Python command that handles this action."));
		else out.push(setting("script_path", "Script path (optional)", "default", "", "", "Use an existing server script, or provide a script body below."), setting("language", "Script language", "default", "python", [{
			value: "python",
			label: "python"
		}, {
			value: "server_js",
			label: "server_js"
		}], "The language used by the native server handler."));
		out.push(setting("execute_mode", "Trigger execution mode", "default", "", [
			{
				value: "",
				label: tr("Not set")
			},
			{
				value: "same process,same transaction",
				label: tr("In process")
			},
			{
				value: "separate process,blocking",
				label: tr("Separate process, blocking")
			},
			{
				value: "separate process,non-blocking",
				label: tr("Separate process, non-blocking")
			},
			{
				value: "separate process,queued",
				label: tr("Queued")
			}
		], "Use the execution mode supported by the installed server handler."));
	}
	if (kind === "hierarchy") out.push({
		kind: "Heading",
		id: "processSubpipelineHeading",
		title: "Subpipeline",
		description: "Choose the pipeline this hierarchy process opens."
	}, {
		id: "adminSubpipelineFilter",
		title: "Find a pipeline",
		props: {
			text: ui.subpipelineQuery,
			action: { type: "subpipelineQuery" }
		}
	}, setting("subpipeline", "Subpipeline", "hierarchy", "", [{
		value: "",
		label: tr("Not set")
	}].concat((catalog.pipelines || []).filter((row) => row.identity !== model.identity && row.searchType === model.document.searchType && (row.label + " " + row.identity).toLowerCase().includes(ui.subpipelineQuery.toLowerCase())).map((row) => ({
		value: row.identity,
		label: row.label || row.identity
	})))), setting("task_creation", "Create tasks", "default", "subtasks_only", [
		{
			value: "subtasks_only",
			label: tr("Create subtasks only")
		},
		{
			value: "top_only",
			label: tr("Create parent task only")
		},
		{
			value: "all",
			label: tr("Create parent task and subtasks")
		},
		{
			value: "none",
			label: tr("Do not create tasks")
		}
	]));
	if (model.document.searchType !== "sthpw/task") out.push({
		kind: "ChoiceGrid",
		id: "adminProcessKind",
		title: "Node type",
		description: "Choose the native behavior of this process.",
		options: (model.metadata.nodeTypes || []).map((value) => ({
			value,
			label: value
		})),
		props: {
			value: kind,
			action: {
				type: "attribute",
				key: "type"
			}
		}
	});
	return out;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/inspector.ui.mjs
var own$1 = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
function inspector(model, ui, width, language) {
	const tr = (text) => translate(text, language), nodes = [], editable = policy(model).editable && !ui.confirmation, contentWidth = width - 24;
	const selectedNode = (model.nodes || []).find((row) => row.identity === model.selectedNode), selectedEdge = (model.edges || [])[model.selectedEdge], referenceOnly = !!(selectedNode && selectedNode.referenceOnly);
	let contentY = 0;
	function addForm(fields, enabled) {
		const body = sections(fields, contentWidth, language, enabled === void 0 ? editable : enabled, model.style);
		nodes.push(node("Box", "graphInspectorForm_" + contentY, rect(0, contentY, contentWidth, body.height), { children: body.nodes }));
		contentY += body.height + 8;
	}
	function action(id, text, icon, event, enabled) {
		nodes.push(button(id, rect(0, contentY, contentWidth, 38), tr(text), icon, event, enabled === void 0 ? editable : enabled));
		contentY += 46;
	}
	function heading(id, text, description) {
		addForm([{
			kind: "Heading",
			id,
			title: text,
			description
		}], false);
	}
	function editor(key, title, source, description) {
		heading("graph_" + key + "Heading", title, description);
		nodes.push(node("Area", "graph_" + key + "Editor", rect(0, contentY, contentWidth, 220), {
			label: tr(title),
			text: own$1(ui.text, key) ? ui.text[key] : source || "",
			monospace: true,
			readOnly: !editable || referenceOnly,
			action: {
				type: "buffer",
				key
			}
		}));
		contentY += 228;
		action("graphApply_" + key, "Apply", "check", {
			type: "apply",
			key
		}, editable && !referenceOnly && own$1(ui.text, key));
	}
	function addPositionFields() {
		addForm([{
			id: "adminGraphPositionX",
			title: "Horizontal position",
			description: "Move this node without dragging.",
			props: {
				text: own$1(ui.text, "positionX") ? ui.text.positionX : String(selectedNode.nodeX),
				inputMode: "decimal",
				action: {
					type: "buffer",
					key: "positionX"
				},
				commitAction: {
					type: "position",
					key: "positionX"
				}
			}
		}, {
			id: "adminGraphPositionY",
			title: "Vertical position",
			description: "Move this node without dragging.",
			props: {
				text: own$1(ui.text, "positionY") ? ui.text.positionY : String(selectedNode.nodeY),
				inputMode: "decimal",
				action: {
					type: "buffer",
					key: "positionY"
				},
				commitAction: {
					type: "position",
					key: "positionY"
				}
			}
		}]);
	}
	if (model.mode !== "workflow") {
		nodes.push(sectionSelector("adminGraphInspectorPages", [{
			value: "selection",
			label: tr("Selection"),
			icon: "tune"
		}, {
			value: "add_node",
			label: tr("Add node"),
			icon: "add"
		}], ui.inspector, rect(0, contentY, contentWidth, 38), !model.busy, "inspector"));
		contentY += 46;
	}
	if (ui.inspector === "add_node") {
		if (model.mode === "workflow") addForm([{
			id: "adminNodeName",
			title: "Node name",
			description: "Enter a unique node name",
			props: {
				text: ui.nodeName,
				action: { type: "nodeName" }
			}
		}, {
			kind: "Choice",
			id: "adminNodeKind",
			title: "Node type",
			options: (model.metadata.nodeTypes || []).map((value) => ({
				value,
				label: value
			})),
			props: {
				value: model.document.searchType === "sthpw/task" ? "status" : ui.nodeKind,
				enabled: editable && model.document.searchType !== "sthpw/task",
				action: { type: "nodeKind" }
			}
		}]);
		else {
			action("adminCreateSchemaTypeInspector", "New Search Type", "add", { type: "createType" });
			addForm([{
				id: "adminGraphTypeFilter",
				title: "Find a Search Type",
				props: {
					text: ui.typeQuery,
					action: { type: "typeQuery" }
				}
			}], !model.busy);
			nodes.push(node("List", "adminGraphTypeCatalog", rect(0, contentY, contentWidth, 220), {
				source: "graphTypes",
				keyField: "identity",
				rowHeight: 66,
				scrollbarId: "adminGraphTypeCatalogScrollBar"
			}));
			contentY += 228;
		}
		action("adminAddNode", "Add node", "add", { type: "addNode" }, editable && !!(model.mode === "workflow" ? ui.nodeName.trim() : ui.typeToAdd));
		const options = (model.nodes || []).filter((row) => !row.referenceOnly).map((row) => ({
			value: row.identity,
			label: row.label || row.identity
		}));
		addForm([{
			kind: "Choice",
			id: "adminConnectSource",
			title: "Source",
			options,
			props: {
				value: ui.source,
				action: { type: "source" }
			}
		}, {
			kind: "Choice",
			id: "adminConnectTarget",
			title: "Destination",
			options,
			props: {
				value: ui.target,
				action: { type: "target" }
			}
		}]);
		action("adminConnectNodes", "Connect", "link", { type: "connect" }, editable && !!ui.source && !!ui.target && ui.source !== ui.target);
	} else if (selectedNode || selectedEdge) {
		if (model.mode !== "workflow" || !selectedNode || referenceOnly) heading("graphSelectionHeading", selectedNode ? selectedNode.identity : selectedEdge.from + " → " + selectedEdge.to, referenceOnly ? model.mode === "workflow" ? "This process is referenced by a connection. Add the missing process or remove its connections before saving." : "This type is referenced by a connection. Add its registered node to the canvas to move it." : "");
		if ((model.selectedNodes || []).length > 1) {
			nodes.push(node("List", "adminGraphMultiSelection", rect(0, contentY, contentWidth, 152), {
				source: "graphSelection",
				keyField: "identity",
				rowHeight: 40
			}));
			contentY += 160;
		}
		if (model.mode !== "workflow") action("adminRemoveGraphSelection", "Remove from canvas", "close", { type: "remove" }, editable && !referenceOnly || editable && !!selectedEdge);
		if (selectedNode && !referenceOnly) {
			if (model.mode === "schema") addPositionFields();
			if (model.mode === "schema") {
				action("adminNodeWorkflows", "Workflows", "schema", { type: "nodeWorkflows" }, !model.busy);
				if (!model.instance && ["sthpw", "config"].indexOf(selectedNode.identity.split("/")[0]) < 0) action("adminDeleteSearchType", "Delete from project", "close", { type: "deleteType" }, editable);
			}
		}
		if (model.mode === "workflow" && selectedEdge) {
			const choices = (model.nodes || []).filter((row) => !row.referenceOnly).map((row) => ({
				value: row.identity,
				label: row.label || row.identity
			}));
			addForm([
				"from",
				"to",
				"from_attr",
				"to_attr"
			].map((key) => ({
				id: "adminWorkflowEdge_" + key,
				title: {
					from: "Source",
					to: "Destination",
					from_attr: "Output condition",
					to_attr: "Input name"
				}[key],
				description: "Native connection attributes.",
				kind: key === "from" || key === "to" ? "Choice" : "Field",
				options: choices,
				props: Object.assign({ action: {
					type: "attribute",
					key
				} }, key === "from" || key === "to" ? { value: selectedEdge[key] || "" } : { text: selectedEdge[key] || "" })
			})));
			editor("attributes", "Attributes (JSON)", model.attributes);
		} else if (model.mode === "workflow" && selectedNode && !referenceOnly) {
			nodes.push(sectionSelector("adminProcessPages", [{
				value: "parameters",
				label: tr("Parameters"),
				icon: "tune"
			}, {
				value: "native_json",
				label: tr("Advanced JSON"),
				icon: "code"
			}], ui.processPage, rect(0, contentY, contentWidth, 38), !model.busy, "processPage"));
			contentY += 46;
			if (ui.processPage === "parameters") {
				addForm(fields(model, ui, language), void 0, true);
				const defaults = (model.processSettings || {}).default || {};
				if (["action", "condition"].indexOf(model.processKind) >= 0 && defaults.action !== "command") editor("script", "Script body", defaults.script, "The code is stored with this process. Applying the draft does not run it.");
			} else {
				addPositionFields();
				editor("settings", "Native process settings", model.settings, "Advanced access to native data, including parameters of installed custom nodes. Standard settings are available in Parameters.");
				editor("attributes", "Attributes (JSON)", model.attributes);
			}
		} else {
			if (model.mode === "schema" && (model.instance || selectedEdge)) {
				const connection = model.connection || {};
				if (model.instance) {
					heading("schemaInstanceHeading", "Many-to-many · new Search Type", "This is a draft. The instance table and its key columns will be created only when you save the schema.");
					addForm([{
						id: "adminSchemaInstanceName",
						title: "Instance table name",
						props: {
							text: own$1(ui.text, "instance") ? ui.text.instance : model.instance.split("/").pop(),
							action: {
								type: "buffer",
								key: "instance"
							},
							commitAction: { type: "commitInstance" }
						}
					}]);
					if (!selectedEdge) for (const link of model.instanceLinks || []) action("schemaInstanceLink_" + link.edgeIndex, link.to, "link", {
						type: "selectEdge",
						index: link.edgeIndex
					}, !model.busy);
					action("adminSchemaRestoreDirect", "Restore direct connection", "undo", { type: "restoreDirect" });
				}
				if (selectedEdge) {
					if (!model.instance) addForm([{
						kind: "Choice",
						id: "adminSchemaRelationship",
						title: "Relationship type",
						description: "Many-to-many creates a separate instance Search Type with two key connections.",
						options: [{
							value: "code",
							label: "code"
						}, {
							value: "id",
							label: "id"
						}].concat([selectedEdge.from, selectedEdge.to].indexOf("*") < 0 ? [{
							value: "many_to_many",
							label: "many_to_many"
						}] : []),
						props: {
							value: selectedEdge.relationship || "code",
							action: { type: "relationship" }
						}
					}]);
					addForm([{
						kind: "Switch",
						id: "adminSchemaCreateColumns",
						title: "Create missing columns",
						description: "Choose existing columns below, or enter a new key column name. New columns are created on schema save, using the opposite key's type.",
						props: {
							checked: !!model.createColumns,
							action: { type: "createColumns" }
						}
					}]);
					action("adminSchemaReverse", "Reverse connection", "refresh", { type: "reverse" }, editable && !model.instance);
					action("adminSchemaRefreshColumns", "Reload columns from server", "refresh", { type: "refreshColumns" }, !model.busy && !model.columnsBusy);
					if (model.columnsError || model.columnsBusy) {
						nodes.push(node("Area", "adminSchemaColumnsStatus", rect(0, contentY, contentWidth, 64), {
							label: tr("Columns"),
							text: tr(model.columnsError || "Loading data…"),
							readOnly: true,
							notice: true,
							color: model.columnsError ? "error" : "secondaryText"
						}));
						contentY += 72;
					}
					for (const side of [{
						key: "from_col",
						name: connection.from,
						title: "Source key column"
					}, {
						key: "to_col",
						name: connection.to,
						title: "Destination key column"
					}]) {
						const info = (model.columnCatalog || {})[side.name] || {}, options = (info.columns || []).map((row) => ({
							value: row.name,
							label: row.name + " · " + (row.type || "") + (row.pending ? " · " + tr("Pending") : "")
						}));
						addForm([{
							id: "adminSchema_" + side.key,
							title: side.title,
							description: side.name,
							props: {
								text: connection[side.key] || "",
								action: {
									type: "column",
									key: side.key
								}
							}
						}, {
							kind: "Choice",
							id: "adminSchemaChoose_" + side.key,
							title: "Existing columns",
							options: [{
								value: "",
								label: tr("Choose a column")
							}].concat(options),
							props: {
								value: connection[side.key] || "",
								action: {
									type: "column",
									key: side.key
								}
							}
						}]);
						if (info.tableAvailable === false) heading("schemaAbsent_" + side.key, "Database table unavailable", "The database table is absent. No table is created by reading columns.");
					}
					addForm([{
						id: "adminSchemaPath",
						title: "Relationship path",
						description: "Optional native path used to distinguish multiple relationships.",
						props: {
							text: selectedEdge.path || "",
							action: {
								type: "attribute",
								key: "path"
							}
						}
					}]);
				}
			}
			if (!referenceOnly) editor("attributes", "Attributes (JSON)", model.attributes);
		}
	} else if (model.mode === "workflow" && model.ready) addForm([
		{
			kind: "Heading",
			id: "pipelineSettingsHeading",
			title: "Pipeline settings",
			description: "These settings belong to the whole pipeline. Select a node on the canvas to configure that process and its task statuses."
		},
		{
			id: "adminPipelineName",
			title: "Title",
			description: "The pipeline name shown to other users.",
			field: "name",
			props: { text: model.document.name || "" }
		},
		{
			id: "adminPipelineDescription",
			title: "Description",
			field: "description",
			description: "Explain what this pipeline is used for.",
			props: { text: model.document.description || "" }
		},
		{
			id: "adminPipelineColor",
			title: "Color",
			field: "color",
			description: "The color of the entire pipeline, independent of its process colors.",
			kind: "ColorChoice",
			props: { value: model.document.color || "" }
		}
	], void 0, true);
	else heading("graphSelectHelp", "Select a node or a connection", "Its details appear here. Use Add node to extend the canvas.");
	return {
		nodes,
		height: contentY + 12
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/catalog.ui.mjs
function records(model, ui, language) {
	const tr = (text) => translate(text, language), groups = {}, query = ui.query.trim().toLowerCase();
	for (const row of model.catalog || []) if (!query || (row.label + " " + row.identity + " " + row.searchType).toLowerCase().includes(query)) (groups[row.searchType || ""] || (groups[row.searchType || ""] = [])).push(row);
	groups["sthpw/task"] = groups["sthpw/task"] || [];
	if (model.ready && !model.identity) groups[model.document.searchType || ""] = groups[model.document.searchType || ""] || [];
	const keys = Object.keys(groups).sort((a, b) => a === "sthpw/task" ? 1 : b === "sthpw/task" ? -1 : a.localeCompare(b)), out = [];
	for (const key of keys) {
		const info = (model.metadata.searchTypes || []).find((row) => row.identity === key) || {};
		out.push({
			key: "group:" + key,
			identity: "group:" + key,
			group: true,
			searchType: key,
			label: key === "sthpw/task" ? tr("Task status workflows") : info.label || key || tr("No Search Type")
		});
		if (ui.collapsed.indexOf(key) < 0 || !model.identity && model.document.searchType === key) {
			if (model.ready && !model.identity && model.document.searchType === key) out.push({
				key: "draft:" + key,
				identity: "",
				label: tr("New workflow"),
				searchType: key
			});
			out.push.apply(out, groups[key].slice().sort((a, b) => (a.label || a.identity).localeCompare(b.label || b.identity)).map((row) => Object.assign({}, row, { key: "pipeline:" + row.identity })));
		}
	}
	return out;
}
function row(list, record, model, ui, language) {
	const width = list.width - 16, tr = (text) => translate(text, language);
	if (list.source === "graphPipelines") {
		if (record.group) return { nodes: [button("workflowGroup_" + record.searchType, rect(0, 0, width - 42, 38), record.label, ui.collapsed.indexOf(record.searchType) >= 0 ? "chevron-right" : "chevron-down", {
			type: "collapse",
			identity: record.searchType
		}, !model.busy), button("workflowCreate_" + record.searchType, rect(width - 38, 0, 38, 38), tr("Create workflow"), "add", {
			type: "createWorkflow",
			searchType: record.searchType
		}, !model.busy && !model.dirty && !model.uncertain && (model.canWrite || model.metadata.canCreate), { iconOnly: true })] };
		return { nodes: [node("Action", "workflowPipeline_" + record.identity, rect(0, 0, width, 38), {
			text: record.label || record.identity,
			selected: model.identity === record.identity,
			normalColor: "surfaceContainerHigh",
			selectedColor: "contentSelection",
			enabled: !model.busy && !model.uncertain,
			children: [label("workflowPipelineTitle_" + record.identity, rect(10, 0, width - 20, 38), record.label || record.identity)],
			action: {
				type: "selectPipeline",
				identity: record.identity
			}
		})] };
	}
	if (list.source === "graphTypes") return { nodes: [node("Action", "graphType_" + record.identity, rect(0, 0, width, 62), {
		text: record.label || record.identity,
		selected: ui.typeToAdd === record.identity,
		normalColor: "surfaceContainerHigh",
		selectedColor: "contentSelection",
		enabled: !model.busy,
		children: [label("graphTypeTitle_" + record.identity, rect(10, 4, width - 20, 26), record.label || record.identity, { weight: 600 }), label("graphTypeIdentity_" + record.identity, rect(10, 32, width - 20, 22), record.identity, muted)],
		action: {
			type: "typeToAdd",
			value: record.identity
		}
	})] };
	if (list.source === "graphSelection") return { nodes: [node("CheckBox", "graphSelect_" + record.identity, rect(0, 0, width, 38), {
		text: record.label || record.identity,
		checked: model.selectedNodes.indexOf(record.identity) >= 0,
		enabled: !model.busy,
		action: {
			type: "selectNodes",
			identities: model.selectedNodes.indexOf(record.identity) >= 0 ? model.selectedNodes.filter((value) => value !== record.identity) : model.selectedNodes.concat([record.identity]),
			primary: record.identity
		}
	})] };
	return { nodes: [] };
}
function models(model, ui, language) {
	const query = ui.typeQuery.trim().toLowerCase();
	return {
		graphPipelines: records(model, ui, language),
		graphTypes: (model.metadata.searchTypes || []).filter((row) => (row.label + " " + row.identity).toLowerCase().includes(query)),
		graphSelection: model.nodes || []
	};
}
function panel(model, ui, bounds, language, narrow = false) {
	const tr = (text) => translate(text, language);
	const w = bounds.width, h = bounds.height, children = [];
	if (narrow || ui.catalogVisible) children.push(label("adminWorkflowCatalogTitle", rect(8, 4, w - 56, 30), tr("Workflows"), { weight: 600 }), node("Field", "adminWorkflowSearch", rect(8, 42, w - 16, 38), {
		text: ui.query,
		placeholder: tr("Find a workflow"),
		label: tr("Find a workflow"),
		action: { type: "query" }
	}), node("List", "adminWorkflowCatalog", rect(8, 88, w - 16, h - 96), {
		source: "graphPipelines",
		keyField: "key",
		rowHeight: 42,
		scrollbarId: "adminWorkflowCatalogScrollBar"
	}));
	if (!narrow) children.push(button("adminToggleWorkflowList", rect(w - 38, 0, 38, 38), tr(ui.catalogVisible ? "Hide workflow list" : "Show workflow list"), ui.catalogVisible ? "chevron-left" : "chevron-right", { type: "catalogVisible" }, true, { iconOnly: true }));
	return node("Box", "adminWorkflowCatalogPanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	});
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.ui.mjs
var own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
function toolbar(model, ui, width, language) {
	const result = toolbar$1(model, ui, width, language), tr = (text) => translate(text, language);
	result.nodes = result.nodes.filter((row) => row.id !== "adminDocumentStatus");
	result.nodes.push(button(model.mode === "workflow" ? "adminCreateDocument" : "adminCreateSchemaType", rect(46, 0, 38, 38), tr(model.mode === "workflow" ? "Create workflow" : "New Search Type"), "add", {
		type: model.mode === "workflow" ? "createWorkflow" : "createType",
		searchType: model.document.searchType || model.creationSearchType
	}, !model.busy && !model.uncertain && (model.canWrite || model.metadata.canCreate) && (!model.dirty || model.mode !== "workflow") && (model.mode !== "workflow" || !!(model.document.searchType || model.creationSearchType)), { iconOnly: true }));
	return result;
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text) => translate(text, language), workflow = model.mode === "workflow", internalCatalog = workflow && !model.externalCatalog, narrow = width < 800, edit = policy(model).editable && !ui.confirmation;
	const noticeModel = Object.assign({}, model, { error: model.error || ui.error });
	if (ui.confirmation === "remove") noticeModel.confirmationText = workflow ? "Remove the selection from this workflow draft?" : "Remove the selection from the schema draft? Search Types, tables and data will be kept.";
	if (ui.confirmation === "selection") noticeModel.confirmationText = "Discard unapplied JSON changes?";
	const notice = notices(noticeModel, ui, width, language, void 0, ui.confirmation === "remove" ? "Remove from canvas" : void 0), nodes = notice.nodes;
	let y = notice.top;
	nodes.push(sectionSelector("adminGraphPages", [{
		value: "canvas",
		label: tr("Canvas"),
		icon: "schema"
	}, {
		value: "technical",
		label: tr("Technical"),
		icon: "code"
	}], ui.page, rect(0, y, Math.min(width, 320), 38), !model.busy, "page"));
	if (workflow && ui.page === "canvas") {
		const settingsY = width >= 560 ? y : y + 46;
		nodes.push(button("adminEditPipeline", rect(width >= 560 ? 328 : 0, settingsY, Math.min(200, width), 38), tr("Pipeline settings"), "tune", { type: "clear" }, !model.busy));
		if (width < 560) y += 46;
	}
	y += 46;
	if (workflow) {
		const searchType = model.document.searchType || model.creationSearchType || "";
		const details = (model.metadata.searchTypes || []).find((record) => record.identity === searchType);
		const context = details && details.label && details.label !== searchType ? details.label + " · " + searchType : searchType;
		const text = searchType ? tr("Search Type: %1").replace("%1", context) : tr("No Search Type is linked. Create a workflow from the Search Type editor.");
		const captionHeight = Math.max(18, Math.ceil(text.length * 6 / Math.max(1, width)) * 15);
		nodes.push(label("adminWorkflowSearchType", rect(0, y, width, captionHeight), text, Object.assign({}, muted, { wrap: true })));
		y += captionHeight + 12;
	}
	if (!model.ready) nodes.push(label("adminGraphEmpty", rect(12, y, width - 24, 80), tr("Select a workflow or create a new one."), { wrap: true }));
	const info = model.metadata.shared ? "Shared pipeline: read-only. Create a project-owned pipeline to make project-specific changes." : !workflow && model.identity && !model.canWrite ? "Built-in system schema · read-only" : "";
	if (info) {
		nodes.push(label("adminGraphReadOnly", rect(0, y, width, 64), tr(info), Object.assign({ wrap: true }, muted)));
		y += 72;
	}
	const missing = workflow ? (model.nodes || []).filter((row) => row.referenceOnly).map((row) => row.identity) : [];
	if (missing.length) {
		nodes.push(node("Area", "adminMissingProcesses", rect(0, y, width, 68), {
			label: tr("Missing processes"),
			text: tr("Connections refer to missing processes") + ": " + missing.join(", "),
			notice: true,
			readOnly: true,
			color: "error"
		}));
		y += 76;
	}
	if (narrow) {
		nodes.push(sectionSelector("adminGraphPanels", [].concat(internalCatalog ? [{
			value: "catalog",
			label: tr("Workflows"),
			icon: "list"
		}] : [], [{
			value: "canvas",
			label: tr("Canvas"),
			icon: "schema"
		}, {
			value: "properties",
			label: tr("Properties"),
			icon: "tune"
		}]), ui.panel, rect(0, y, width, 38), !model.busy, "panel"));
		y += 46;
	}
	const h = Math.max(1, height - y), catalogWidth = internalCatalog && !narrow ? ui.catalogVisible ? Math.min(ui.catalogWidth, width * .28) : 40 : 0, propertiesWidth = !narrow ? ui.propertiesVisible ? Math.min(ui.propertiesWidth, workflow ? 460 : 420, width * (workflow ? .5 : .45)) : 40 : 0;
	if (internalCatalog && (!narrow || ui.panel === "catalog")) {
		const w = narrow ? width : catalogWidth;
		nodes.push(Object.assign(panel(model, ui, rect(0, y, w, h), language, narrow), { visible: ui.page === "canvas" }));
		if (!narrow && ui.catalogVisible) nodes.push(node("Splitter", "adminCatalogSplit", rect(w, y, 10, h), {
			visible: ui.page === "canvas",
			text: tr("Workflow list width"),
			value: w,
			min: 180,
			max: Math.min(420, width * .28),
			action: { type: "catalogSplit" }
		}));
	}
	const x = narrow ? 0 : internalCatalog ? catalogWidth + 10 : 0, graphWidth = narrow ? width : Math.max(1, width - x - propertiesWidth - 10);
	const graphNodes = (model.nodes || []).map((row) => ({
		identity: row.identity,
		label: row.label || row.identity,
		nodeX: row.nodeX,
		nodeY: row.nodeY,
		color: row.color || "",
		kind: workflow && row.kind === "process" ? "manual" : row.kind,
		referenceOnly: !!row.referenceOnly,
		pendingCreation: !!model.document.newTypes && own(model.document.newTypes, row.identity)
	}));
	const graphEdges = (model.edges || []).map((row, index) => ({
		from: row.from,
		to: row.to,
		edgeIndex: index,
		relationship: row.relationship || "",
		from_attr: row.from_attr || "",
		to_attr: row.to_attr || "",
		label: workflow ? row.from_attr || "" : row.relationship || "code",
		color: row.color || ""
	}));
	nodes.push(node("Graph", "adminGraphCanvas", rect(x, y, graphWidth, h), {
		toolbarRightInset: 46,
		visible: ui.page === "canvas" && (!narrow || ui.panel === "canvas" || model.externalCatalog && ui.panel === "catalog"),
		help: false,
		label: tr(workflow ? "Workflow" : "Project schema"),
		nodes: graphNodes,
		edges: graphEdges,
		selectedNode: model.selectedNode || "",
		selectedNodes: model.selectedNodes || [],
		selectedEdge: model.selectedEdge,
		readOnly: !edit,
		selectionEnabled: !model.busy,
		resetKey: model.identity || "draft:" + model.document.searchType,
		language,
		action: { type: "graph" }
	}));
	if (!narrow || ui.panel === "properties") {
		const w = narrow ? width : propertiesWidth, px = narrow ? 0 : width - w, children = [];
		if (narrow || ui.propertiesVisible) {
			const inner = inspector(model, ui, w - 12, language);
			children.push(node("Scroll", "adminGraphPropertiesScroll", rect(12, 46, w - 24, h - 58), {
				contentHeight: inner.height,
				resetKey: ui.inspector + ":" + ui.processPage + ":" + model.selectedNode + ":" + model.selectedEdge,
				scrollbarId: "adminGraphPropertiesScrollBar",
				children: inner.nodes
			}));
		}
		if (!narrow) children.push(button("adminToggleGraphProperties", rect(workflow && ui.propertiesVisible ? w - 38 : 0, 0, 38, 38), tr(ui.propertiesVisible ? "Hide properties" : "Show properties"), ui.propertiesVisible ? "chevron-right" : "chevron-left", { type: "propertiesVisible" }, true, { iconOnly: true }));
		if (narrow || ui.propertiesVisible) children.push(button("adminGraphAddNode", rect(workflow ? w - 82 : 44, 0, workflow ? 38 : w - 52, 38), tr(ui.inspector === "add_node" ? "Selection" : "Add node"), ui.inspector === "add_node" ? "tune" : "add", {
			type: "inspector",
			value: ui.inspector === "add_node" ? "selection" : "add_node"
		}, !model.busy, { iconOnly: workflow }));
		if (workflow && (narrow || ui.propertiesVisible)) {
			children.push(label("adminGraphInspectorTitle", rect(12, 0, Math.max(0, w - 144), 38), tr("Inspector"), { weight: 600 }));
			if (model.selectedNode || model.selectedEdge >= 0) {
				const selectedNode = (model.nodes || []).find((record) => record.identity === model.selectedNode);
				children.push(button("adminRemoveGraphSelection", rect(w - 126, 0, 38, 38), tr("Remove from canvas"), "delete", { type: "remove" }, edit && !(selectedNode && selectedNode.referenceOnly), {
					iconOnly: true,
					destructive: true
				}));
			}
		}
		nodes.push(node("Box", "adminGraphProperties", rect(px, y, w, h), {
			visible: ui.page === "canvas",
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
		if (!narrow && ui.propertiesVisible) nodes.push(node("Splitter", "adminGraphSplitHandle", rect(px - 10, y, 10, h), {
			visible: ui.page === "canvas",
			text: tr("Properties panel width"),
			value: w,
			min: 240,
			max: Math.min(640, width * .4),
			reverse: true,
			action: { type: "propertiesSplit" }
		}));
	}
	if (ui.page === "technical") nodes.push(node("Area", "adminGraphXmlEditor", rect(0, y, width, Math.max(1, h - 46)), {
		label: tr("Native XML"),
		text: own(ui.text, "xml") ? ui.text.xml : model.xml || "",
		monospace: true,
		readOnly: !edit,
		action: {
			type: "buffer",
			key: "xml"
		}
	}), button("adminGraphApplyXml", rect(0, height - 38, Math.min(240, width), 38), tr("Apply XML"), "check", {
		type: "apply",
		key: "xml"
	}, edit && own(ui.text, "xml")));
	if (ui.page === "canvas" && (!narrow || ui.panel === "canvas" || model.externalCatalog && ui.panel === "catalog")) {
		const toolbarX = x + 230, available = graphWidth - 230;
		if (available > 130) nodes.push(node("Choice", "adminGraphLayoutStyle", rect(toolbarX, y, Math.max(80, available - 46), 38), {
			label: tr("Automatic layout"),
			options: [
				{
					value: "flow",
					label: tr("Directed flow")
				},
				{
					value: "network",
					label: tr("Network clusters")
				},
				{
					value: "grid",
					label: tr("Alphabetical grid")
				}
			],
			value: ui.arrange,
			action: { type: "arrange" },
			enabled: edit
		}), button("adminArrangeGraph", rect(x + graphWidth - 38, y, 38, 38), tr("Arrange nodes"), "hierarchy", { type: "layout" }, edit && (model.nodes || []).length > 0, { iconOnly: true }));
		else nodes.push(button("adminArrangeGraph", rect(x + graphWidth - 38, y, 38, 38), tr("Arrange nodes"), "hierarchy", { type: "layout" }, edit && (model.nodes || []).length > 0, { iconOnly: true }));
	}
	return { nodes };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.state.mjs
function initial() {
	return {
		page: "canvas",
		panel: "canvas",
		inspector: "selection",
		processPage: "parameters",
		catalogWidth: 230,
		propertiesWidth: 460,
		catalogVisible: true,
		propertiesVisible: true,
		query: "",
		typeQuery: "",
		subpipelineQuery: "",
		collapsed: [],
		nodeName: "",
		nodeKind: "manual",
		typeToAdd: "",
		source: "",
		target: "",
		arrange: "flow",
		text: {},
		confirmation: "",
		pending: null,
		error: ""
	};
}
function pending(ui) {
	return Object.keys(ui.text).length > 0;
}
var selectionEvents = [
	"selectNodes",
	"selectEdge",
	"clear"
];
function transition(ui, model, event) {
	if (event.type === "graph") event = event.value;
	const next = Object.assign({}, ui), commands = [], edit = policy(model).editable;
	const navigation = [
		"selectPipeline",
		"createWorkflow",
		"taskWorkflow",
		"dependencies",
		"createType",
		"deleteType"
	];
	if (event.type === "keep") {
		next.confirmation = "";
		next.pending = null;
		return {
			ui: next,
			commands
		};
	}
	if (event.type === "confirm" && next.pending && !model.busy) {
		const command = next.pending;
		next.pending = null;
		next.confirmation = "";
		if (selectionEvents.indexOf(command.type) >= 0) {
			next.text = {};
			next.inspector = "selection";
			next.propertiesVisible = true;
			next.processPage = "parameters";
			commands.push(command);
		} else {
			next.text = {};
			commands.push({ type: "discard" }, command);
		}
		return {
			ui: next,
			commands
		};
	}
	if (event.type === "confirm" && next.confirmation === "remove") {
		next.confirmation = "";
		if (edit) commands.push({ type: "remove" });
		return {
			ui: next,
			commands
		};
	}
	const document = documentEvent(ui, model, event);
	if (document) return document;
	if (model.busy || ui.confirmation) return {
		ui: next,
		commands
	};
	if (selectionEvents.indexOf(event.type) >= 0) {
		if (pending(next)) {
			next.confirmation = "selection";
			next.pending = event;
		} else {
			next.inspector = "selection";
			next.processPage = "parameters";
			next.propertiesVisible = true;
			next.text = {};
			commands.push(event);
		}
		return {
			ui: next,
			commands
		};
	}
	if (navigation.indexOf(event.type) >= 0) {
		if (model.uncertain) return {
			ui: next,
			commands
		};
		if (["selectPipeline", "createWorkflow"].indexOf(event.type) >= 0 && model.dirty) {
			next.confirmation = "navigate";
			next.pending = event;
		} else if (pending(ui)) next.error = "Apply or discard the pending text before continuing";
		else if ([
			"taskWorkflow",
			"dependencies",
			"deleteType"
		].indexOf(event.type) >= 0 && model.dirty) next.error = event.type === "dependencies" ? "Save the workflow before editing process dependencies" : "Save or discard changes before continuing";
		else if (event.type === "selectPipeline" || model.canWrite || event.type === "taskWorkflow" || event.type === "dependencies") commands.push(event);
		return {
			ui: next,
			commands
		};
	}
	switch (event.type) {
		case "page":
			next.page = event.value;
			break;
		case "panel":
			next.panel = event.value;
			break;
		case "inspector":
			next.inspector = event.value;
			next.propertiesVisible = true;
			next.panel = "properties";
			break;
		case "processPage":
			next.processPage = event.value;
			break;
		case "catalogVisible":
			next.catalogVisible = !next.catalogVisible;
			break;
		case "propertiesVisible":
			next.propertiesVisible = !next.propertiesVisible;
			break;
		case "catalogSplit":
			next.catalogWidth = Math.max(180, Math.min(420, Number(event.value)));
			break;
		case "propertiesSplit":
			next.propertiesWidth = Math.max(240, Math.min(640, Number(event.value)));
			break;
		case "collapse":
			next.collapsed = next.collapsed.indexOf(event.identity) >= 0 ? next.collapsed.filter((value) => value !== event.identity) : next.collapsed.concat([event.identity]);
			break;
		case "query":
		case "typeQuery":
		case "subpipelineQuery":
		case "nodeName":
		case "nodeKind":
		case "typeToAdd":
		case "source":
		case "target":
		case "arrange":
			next[event.type] = event.value;
			break;
		case "buffer":
			if (edit) next.text = Object.assign({}, next.text, { [event.key]: event.value });
			break;
		case "commitInstance":
			if (edit && next.text.instance !== void 0) {
				const value = next.text.instance.trim();
				if (!/^[a-z][a-z0-9_]*$/.test(value)) {
					next.error = "Use a lowercase table name with letters, digits and underscores";
					break;
				}
				commands.push({
					type: "renameInstance",
					value
				});
			}
			break;
		case "apply":
			if (edit) {
				const value = next.text[event.key] === void 0 ? model[event.key] : next.text[event.key];
				if (event.key === "attributes" || event.key === "settings") {
					let parsed;
					try {
						parsed = JSON.parse(value);
					} catch (error) {
						next.error = "Invalid JSON. Check quotes, commas and braces.";
						break;
					}
					if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
						next.error = event.key === "attributes" ? "Attributes must be a JSON object with string values" : "Process settings must be a JSON object";
						break;
					}
					if (event.key === "attributes" && Object.keys(parsed).some((key) => typeof parsed[key] !== "string")) {
						next.error = "Attributes must be a JSON object with string values";
						break;
					}
				}
				next.error = "";
				commands.push({
					type: "apply",
					key: event.key,
					value
				});
			}
			break;
		case "integer": {
			const key = "integer_" + event.section + "_" + event.key, text = next.text[key];
			if (text === void 0 || !edit) break;
			const value = Number(text);
			if (text !== "" && (!/^\d+$/.test(text) || !Number.isSafeInteger(value) || value < event.min || value > event.max)) {
				next.error = "Enter a whole number within the allowed range";
				break;
			}
			commands.push({
				type: "setting",
				section: event.section,
				key: event.key,
				value: text === "" ? "" : value
			});
			next.text = Object.assign({}, next.text);
			delete next.text[key];
			next.error = "";
			break;
		}
		case "position": {
			const text = next.text[event.key], value = Number(text);
			if (text === void 0 || !edit) break;
			if (!String(text).trim() || !Number.isFinite(value)) {
				next.error = "Node positions must be finite";
				break;
			}
			const node = (model.nodes || []).find((row) => row.identity === model.selectedNode);
			if (node) commands.push({
				type: "moveNodes",
				positions: [{
					identity: node.identity,
					nodeX: event.key === "positionX" ? value : node.nodeX,
					nodeY: event.key === "positionY" ? value : node.nodeY
				}]
			});
			next.text = Object.assign({}, next.text);
			delete next.text[event.key];
			next.error = "";
			break;
		}
		case "remove":
			if (edit && (model.selectedNode || model.selectedEdge >= 0)) next.confirmation = "remove";
			break;
		case "addNode":
			if (edit) {
				const name = model.mode === "workflow" ? next.nodeName.trim() : next.typeToAdd;
				if (!name) {
					next.error = "Enter a unique node name";
					break;
				}
				commands.push({
					type: "addNode",
					identity: name,
					kind: model.document.searchType === "sthpw/task" ? "status" : next.nodeKind
				});
			}
			break;
		case "connect":
			if (edit) commands.push({
				type: "connect",
				from: event.from || next.source,
				to: event.to || next.target
			});
			break;
		case "field":
		case "attribute":
		case "setting":
		case "description":
		case "moveNodes":
		case "column":
		case "renameInstance":
		case "relationship":
		case "createColumns":
		case "reverse":
		case "restoreDirect":
			if (edit) commands.push(event);
			break;
		case "layout":
			if (edit && model.nodes.length) commands.push({
				type: "layout",
				style: next.arrange
			});
			break;
		case "nodeWorkflows":
			if (model.selectedNode) commands.push(event);
			break;
		case "refreshColumns": if (!model.columnsBusy) commands.push(event);
	}
	return {
		ui: next,
		commands
	};
}
function applied(ui, key) {
	const text = Object.assign({}, ui.text);
	delete text[key];
	return Object.assign({}, ui, {
		text,
		error: ""
	});
}
function completed(ui, command) {
	if (command.type === "renameInstance") return applied(ui, "instance");
	if ([
		"reload",
		"discard",
		"selectPipeline",
		"createWorkflow"
	].indexOf(command.type) >= 0) return Object.assign({}, ui, {
		text: {},
		confirmation: "",
		pending: null,
		error: "",
		processPage: "parameters"
	});
	if (command.type === "addNode") return Object.assign({}, ui, {
		nodeName: "",
		typeToAdd: "",
		inspector: "selection",
		processPage: "parameters",
		error: ""
	});
	return ui;
}
//#endregion
//#region src/features/administration/graphXml.js
function graphXmlText(xml) {
	if (!xml?.documentElement) return "";
	const escape = (value, attribute = false) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("\"", attribute ? "&quot;" : "\"").replaceAll("	", attribute ? "&#09;" : "	").replaceAll("\n", attribute ? "&#10;" : "\n").replaceAll("\r", attribute ? "&#13;" : "\r");
	function render(node, depth) {
		if (node.nodeType === 8) return "<!--" + node.data + "-->";
		if (node.nodeType === 7) return "<?" + node.target + (node.data ? " " + node.data : "") + "?>";
		if (node.nodeType === 3 || node.nodeType === 4) return escape(node.textContent);
		const attributes = [...node.attributes].map((attr) => " " + attr.name + "=\"" + escape(attr.value, true) + "\"").join(""), children = [...node.childNodes];
		if (!children.length) return "<" + node.tagName + attributes + " />";
		const content = children.some((child) => child.nodeType === 1 || child.nodeType === 7 || child.nodeType === 8), mixed = children.some((child) => [3, 4].includes(child.nodeType) && child.textContent.trim());
		const body = content && !mixed ? "\n" + "  ".repeat(depth + 1) + children.filter((child) => ![3, 4].includes(child.nodeType) || child.textContent.trim()).map((child) => render(child, depth + 1)).join("\n" + "  ".repeat(depth + 1)) + "\n" + "  ".repeat(depth) : children.map((child) => render(child, depth + 1)).join("");
		return "<" + node.tagName + attributes + ">" + body + "</" + node.tagName + ">";
	}
	return render(xml.documentElement, 0);
}
//#endregion
//#region src/features/administration/graphFrame.js
var graphFrame_default = {
	props: {
		catalogTarget: Object,
		catalogPlacement: {
			type: String,
			default: "inline"
		}
	},
	data() {
		return {
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			catalogSize: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			frameObserver: null
		};
	},
	computed: {
		frameModel() {
			const workflow = this.frameMode === "workflow", document = this.document || {}, settings = workflow ? this.processSettings || {} : {}, kind = document.searchType === "sthpw/task" ? "status" : this.node?.kind || "manual", columnCatalog = workflow ? {} : { ...this.columnCatalog };
			if (!workflow) for (const identity of Object.keys(document.newTypes || {})) columnCatalog[identity] = { columns: this.edges.filter((row) => row.from === identity && row.from_col).map((row) => ({
				name: row.from_col,
				type: "",
				pending: true
			})) };
			return {
				mode: this.frameMode,
				externalCatalog: this.catalogPlacement === "sidebar",
				style: appearance.theme,
				ready: !!document.xml,
				canWrite: this.canWrite,
				canLoad: !!this.ticket,
				busy: this.busy || !workflow && (this.creating || this.deletionActive),
				dirty: this.dirty,
				uncertain: this.uncertain,
				pendingText: pending(this.ui),
				saveAllowed: !workflow || !!document.name?.trim(),
				error: this.error,
				message: "",
				identity: this.identity,
				document,
				catalog: workflow ? this.catalog : [],
				metadata: this.metadata,
				creationSearchType: workflow ? this.creationType : "",
				nodes: this.nodes,
				edges: this.edges,
				selectedNode: this.node?.identity || "",
				selectedNodes: this.selected,
				selectedEdge: this.selectedEdge,
				xml: graphXmlText(this.xml),
				attributes: JSON.stringify(this.node?.attributes || this.edge?.attributes || {}, null, 2),
				settings: JSON.stringify(settings, null, 2),
				processSettings: settings,
				processKind: kind,
				processProperties: workflow ? this.processProperties || {} : {},
				processDescription: document.processDescriptions?.[this.node?.identity] || "",
				processCatalog: this.metadata,
				connection: workflow ? {} : this.connection || {},
				instance: workflow ? "" : this.instance || "",
				instanceLinks: workflow ? [] : this.instanceLinks,
				createColumns: workflow ? false : this.createColumns,
				columnCatalog,
				columnsBusy: !workflow && this.columnsBusy,
				columnsError: workflow ? "" : this.columnsError
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		catalogScene() {
			return { nodes: [panel(this.frameModel, this.ui, {
				x: 0,
				y: 0,
				...this.catalogSize
			}, appearance.language)] };
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		frameModels() {
			return models(this.frameModel, this.ui, appearance.language);
		}
	},
	mounted() {
		const toolbar = this.toolbarTarget ? document.querySelector(this.toolbarTarget) || this.$el : this.$el;
		this.frameObserver = observeFrameSizes((entries) => {
			for (const { target, contentRect: box } of entries) {
				const size = {
					width: Math.max(1, box.width),
					height: Math.max(1, box.height)
				};
				if (target === this.$refs.body) this.viewport = size;
				else if (target === this.catalogTarget) this.catalogSize = size;
				else if (target === toolbar) this.toolbarSize = size.width;
			}
		});
		this.frameObserver.observe(this.$refs.body);
		this.frameObserver.observe(toolbar);
		if (this.catalogTarget) this.frameObserver.observe(this.catalogTarget);
	},
	watch: { catalogTarget(target, previous) {
		if (previous) this.frameObserver?.unobserve(previous);
		if (target) this.frameObserver?.observe(target);
	} },
	beforeUnmount() {
		this.frameObserver?.disconnect();
	},
	methods: {
		rowScene(list, record) {
			return row(list, record, this.frameModel, this.ui, appearance.language);
		},
		graphCommand(command) {
			return this.$refs.frame?.graphCommand("adminGraphCanvas", command);
		},
		insertionPoint() {
			return this.graphCommand({ type: "point" }) || {
				x: 40,
				y: 40
			};
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) {
				switch (command.type) {
					case "field":
						this.document[command.field] = command.value;
						break;
					case "attribute":
						this.setAttribute(command.key, String(command.value));
						break;
					case "setting":
						this.setSetting(command.section, command.key, command.value);
						break;
					case "description":
						this.document.processDescriptions[this.node.identity] = command.value;
						break;
					case "selectNodes":
						this.selectMany(command.identities, command.primary);
						break;
					case "selectEdge":
						this.selectEdge(command.index);
						break;
					case "clear":
						this.selectNode("");
						break;
					case "moveNodes":
						this.moveNodes(command.positions);
						break;
					case "connect":
						this.connect(command.from, command.to);
						break;
					case "remove":
						this.remove(true);
						break;
					case "addNode":
						this.nodeName = command.identity;
						this.typeToAdd = command.identity;
						this.nodeKind = command.kind;
						this.addNode(this.insertionPoint());
						if (!this.error) {
							await nextTick();
							this.graphCommand({ type: "reveal" });
						}
						break;
					case "layout":
						await this.arrange(command.style);
						await nextTick();
						this.graphCommand({ type: "reset" });
						break;
					case "createType":
						await this.createType(this.insertionPoint());
						break;
					case "deleteType":
						this.openDeletion();
						break;
					case "nodeWorkflows":
						this.$emit("node-workflows", this.node.identity);
						break;
					case "createWorkflow":
						await this.open("", command.searchType || this.creationType || this.document?.searchType);
						break;
					case "selectPipeline":
						if (command.identity) await this.open(command.identity);
						break;
					case "taskWorkflow":
						await this.open(this.processProperties.task_pipeline);
						break;
					case "dependencies":
						this.dependencies();
						break;
					case "column":
						if (command.value) this.setColumn(command.key, command.value);
						break;
					case "renameInstance":
						this.renameInstance(command.value);
						break;
					case "relationship":
						if (command.value === "many_to_many") this.makeInstance();
						else this.setAttribute("relationship", command.value);
						break;
					case "createColumns":
						this.setCreateColumns(command.value);
						break;
					case "reverse":
						this.reverse();
						break;
					case "restoreDirect":
						this.restoreDirect();
						break;
					case "refreshColumns":
						await this.loadColumns(true);
						break;
					case "apply":
						if (command.key === "xml") {
							this.xmlDraft = command.value;
							this.xmlPending = true;
							this.applyXml();
						} else if (command.key === "attributes") {
							this.attributesDraft = command.value;
							this.attributesPending = true;
							this.applyAttributes();
						} else if (command.key === "settings") {
							this.settingsDraft = command.value;
							this.settingsPending = true;
							this.applySettings();
						} else if (command.key === "script") this.setSetting("default", "script", command.value);
						if (!this.error) this.ui = applied(this.ui, command.key);
						break;
					case "save":
						await this.save(true);
						break;
					case "reload":
						if (this.frameMode === "workflow") await this.open(this.identity, this.identity ? "" : this.creationType || this.document?.searchType);
						else await this.load();
						break;
					case "discard":
						this.ui = {
							...this.ui,
							text: {}
						};
						this.xmlPending = this.attributesPending = this.settingsPending = false;
						if (this.uncertain) {
							if (this.frameMode === "workflow") await this.open(this.identity);
							else await this.load();
						} else {
							this.document = this.baseline ? JSON.parse(this.baseline) : null;
							this.xmlDraft = this.document?.xml || "";
							this.selectNode("");
							this.error = "";
						}
						break;
					default: throw Error("Unsupported graph command: " + command.type);
				}
				if (!this.error) this.ui = completed(this.ui, command);
			}
		}
	}
};
//#endregion
export { pending as n, graphFrame_default as t };

//# sourceMappingURL=graphFrame.js.map
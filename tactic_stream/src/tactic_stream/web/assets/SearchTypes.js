import { I as resolveComponent, N as openBlock, Y as markRaw, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, q as withDirectives, rt as normalizeStyle, s as vShow } from "./vue.js";
import { L as _plugin_vue_export_helper_default, o as t, s as appearance } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { B as node, L as button, R as label, V as rect, n as observeFrameSizes, r as _sfc_main$1, v as translate, z as muted } from "./resize.js";
import { n as sections } from "./sections.ui.js";
import { i as readPreviewImage } from "./RecordForm.js";
import { i as sectionSelector, n as notices, o as toolbar$1, r as policy, t as documentEvent } from "./admin.document.js";
import { t as NamingEditor_default } from "./NamingEditor.js";
//#region ../src/tactic_stream/shared_ui/features/administration/search_types/search_types.fields.mjs
var automaticFields = [
	"id",
	"code",
	"name",
	"description",
	"keywords",
	"login",
	"timestamp",
	"data",
	"s_status",
	"relative_dir"
];
var fieldTypes = [
	{
		value: "varchar(256)",
		label: "Short text",
		name: "asset_title",
		example: "Firetruck",
		help: "Names and short labels, up to 256 characters."
	},
	{
		value: "text",
		label: "Long text",
		name: "brief",
		example: "Describe the scene and what needs to be done.",
		help: "Descriptions and notes spanning several lines."
	},
	{
		value: "integer",
		label: "Whole number",
		name: "duration_minutes",
		example: "3",
		help: "Counts or durations in whole units, without a fractional part."
	},
	{
		value: "numeric",
		label: "Decimal number",
		name: "weight",
		example: "12.5",
		help: "Measurements that need a fractional part."
	},
	{
		value: "boolean",
		label: "Yes / No",
		name: "has_storyboard",
		example: "Yes / No",
		help: "A flag with two values, stored as true or false."
	},
	{
		value: "timestamp",
		label: "Date and time",
		name: "deadline",
		example: "Today, 14:30",
		help: "A deadline or another date with a time."
	}
];
var removalReasons = {
	identity: "Object identifier. This field cannot be deleted.",
	tactic: "Required by TACTIC. This field cannot be deleted.",
	schema: "Used by a schema relationship. Change the relationship before deleting this field.",
	system_type: "Columns of system and config Search Types cannot be deleted here."
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/search_types/search_types.ui.mjs
function records(model, ui) {
	const query = ui.query.toLowerCase();
	return model.catalog.filter((row) => (!ui.projectOnly || row.projectLocal) && (!ui.hideConfig || row.namespace !== "config") && [row.label, row.identity].join(" ").toLowerCase().indexOf(query) >= 0);
}
function existing(model, ui) {
	return Object.keys(model.metadata.columns || {}).filter((name) => name.toLowerCase().indexOf(ui.fieldQuery.toLowerCase()) >= 0).map((name) => ({
		name,
		info: model.metadata.columns[name]
	}));
}
function toolbar(model, ui, width, language) {
	if (ui.page === "naming") return { nodes: [] };
	const scene = toolbar$1(Object.assign({}, model, { saveAllowed: (!model.creationOnly || ui.page === "ready") && !!String(model.document.title || "").trim() }), ui, width, language), tr = (text) => translate(text, language);
	scene.nodes = scene.nodes.filter((row) => row.id !== "adminDocumentStatus");
	if (!model.creationOnly) scene.nodes.push(button("adminCreateDocument", rect(46, 0, 38, 38), tr("New Search Type"), "add", { type: "create" }, model.canWrite && !model.busy && !model.dirty && !model.uncertain && !model.namingLocked, { iconOnly: true }));
	return scene;
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text, values) => translate(text, language, values), changed = model.document.removedColumns || [], details = changed.length ? tr("All data in these columns will be lost. This editor cannot restore it after saving. Check any scripts, naming rules and saved searches that use these fields.") + "\n\n" + model.identity + "\n" + changed.map((name) => "• " + name).join("\n") : "";
	const notice = notices(Object.assign({}, model, {
		error: model.error || ui.error,
		confirmationDetails: details
	}), ui, width, language, "Discard unsaved Search Type changes?"), nodes = notice.nodes, y = notice.top, h = height - y;
	if (h < 320) return { nodes: [node("Scroll", "typesPageScroll", rect(0, 0, width, height), {
		contentHeight: y + 420,
		children: describe(model, ui, width - 16, y + 420, language).nodes
	})] };
	const split = !model.creationOnly && width >= 850, left = split ? Math.min(ui.catalogWidth, width * .4) : width, edit = policy(model).editable && !ui.confirmation, navigate = !model.busy && !model.dirty && !model.uncertain && !model.namingLocked && !ui.confirmation;
	if (!model.creationOnly && (split || !ui.editing)) {
		const children = [
			label("typesCatalogTitle", rect(12, 8, left - 24, 28), tr("Search Types"), {
				fontRole: "section",
				weight: 600
			}),
			node("Field", "adminSearchTypeFilter", rect(12, 44, left - 24, 38), {
				label: tr("Find a Search Type"),
				placeholder: tr("Find a Search Type"),
				text: ui.query,
				enabled: !model.busy,
				action: { type: "query" }
			}),
			node("CheckBox", "adminSearchTypesProjectOnly", rect(12, 90, left - 24, 32), {
				text: tr("Only current project"),
				checked: ui.projectOnly,
				enabled: !model.busy,
				action: { type: "projectOnly" }
			}),
			node("CheckBox", "adminSearchTypesHideConfig", rect(12, 128, left - 24, 32), {
				text: tr("Hide config types"),
				checked: ui.hideConfig,
				enabled: !model.busy,
				action: { type: "hideConfig" }
			}),
			node("List", "adminSearchTypesList", rect(12, 170, left - 24, h - 182), {
				source: "types",
				rowHeight: 88,
				keyField: "identity",
				scrollbarId: "adminSearchTypesScrollBar"
			})
		];
		if (!records(model, ui).length) children.push(label("typesCatalogEmpty", rect(12, 180, left - 24, 90), tr("No types found"), Object.assign({ wrap: true }, muted)));
		nodes.push(node("Box", "typesCatalogPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
	}
	if (split) nodes.push(node("Splitter", "typesCatalogSplitHandle", rect(left, y, 10, h), {
		text: tr("Search Types panel width"),
		value: left,
		min: 200,
		max: width * .4,
		action: { type: "split" }
	}));
	if (!model.creationOnly && !split && !ui.editing) return { nodes };
	const bounds = rect(split ? left + 10 : 0, y, split ? width - left - 10 : width, h), w = bounds.width - 40, children = [];
	let top = 12;
	if (!split && !model.creationOnly) {
		children.push(button("typesBack", rect(12, top, 100, 36), tr("Back"), "chevron-left", { type: "back" }, !model.busy && !!model.identity));
		top += 44;
	}
	if (!model.ready) children.push(label("typesSelectHelp", rect(12, top, w, 80), tr("Select a Search Type"), Object.assign({ wrap: true }, muted)));
	else {
		const pages = model.identity ? [
			[
				"summary",
				"Summary",
				"info"
			],
			[
				"workflow",
				"Workflow",
				"workflow"
			],
			[
				"naming",
				"Naming",
				"edit"
			],
			[
				"details",
				"Details",
				"edit"
			],
			[
				"fields",
				"Fields",
				"table"
			]
		] : [
			[
				"details",
				"1. Details",
				"edit"
			],
			[
				"fields",
				"2. Fields",
				"table"
			],
			[
				"ready",
				"3. Ready",
				"check"
			]
		];
		children.push(sectionSelector("searchTypePages", pages.map((row) => ({
			value: row[0],
			label: tr(row[1]),
			icon: row[2]
		})), ui.page, rect(12, top, bounds.width - 24, 38), !model.busy, "page", tr("Search Type sections")));
		top += 46;
		if (ui.page === "naming") children.push(node("View", "typeNaming", rect(12, top, bounds.width - 24, h - top - 12), { view: "naming" }));
		else {
			const footer = model.identity ? 0 : 46, body = content(model, ui, w, Math.max(160, h - top - 12 - footer), language, edit, navigate);
			children.push(node("Scroll", "adminSearchTypeForm", rect(12, top, bounds.width - 24, h - top - 12 - footer), {
				contentHeight: body.height,
				resetKey: model.identity + ":" + ui.page,
				scrollbarId: "adminSearchTypeFormScrollBar",
				children: body.nodes
			}));
			if (!model.identity) {
				if (ui.page !== "details") children.push(button("adminTypeWizardBack", rect(12, h - 50, 100, 38), tr("Back"), "chevron-left", {
					type: "page",
					value: ui.page === "ready" ? "fields" : "details"
				}, !model.busy));
				if (ui.page !== "ready") children.push(button("adminTypeWizardNext", rect(bounds.width - 112, h - 50, 100, 38), tr("Next"), "chevron-right", {
					type: "page",
					value: ui.page === "details" ? "fields" : "ready"
				}, edit));
			}
		}
	}
	nodes.push(node("Box", "typesEditorPanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	}));
	return { nodes };
}
function content(model, ui, width, height, language, edit, navigate) {
	const tr = (text, values) => translate(text, language, values), nodes = [], doc = model.document, meta = model.metadata;
	let y = 0;
	const text = (key) => String(doc[key] || "");
	const heading = (id, title, description) => {
		nodes.push(label(id, rect(0, y, width, 28), title, {
			role: "heading",
			level: 2,
			fontRole: "section",
			weight: 600
		}));
		y += 34;
		if (description) {
			nodes.push(label(id + "Description", rect(0, y, width, width < 420 ? 82 : 60), description, Object.assign({ wrap: true }, muted)));
			y += width < 420 ? 90 : 68;
		}
	};
	if (meta.tableAvailable === false) {
		nodes.push(node("Area", "adminSearchTypeMissingTable", rect(0, y, width, 100), {
			text: tr("The database table is missing. Check the server schema before editing."),
			label: tr("Database"),
			readOnly: true,
			notice: true,
			color: "error"
		}));
		y += 108;
	}
	if (ui.page === "details") {
		const fields = [
			{
				kind: "Heading",
				id: "typeDetailsHeading",
				title: "Details",
				description: "How this Search Type appears in navigation and Search Object lists."
			},
			{
				id: "adminSearchTypeTitle",
				title: "Title",
				description: "A recognizable name for users.",
				props: {
					text: text("title"),
					action: {
						type: "field",
						field: "title"
					}
				}
			},
			{
				id: "adminSearchTypeDescription",
				title: "Description",
				description: "Explain what these Search Objects represent.",
				kind: "Area",
				height: 82,
				props: {
					text: text("description"),
					action: {
						type: "field",
						field: "description"
					}
				}
			},
			{
				kind: "ColorChoice",
				id: "adminSearchTypeColor",
				title: "Accent color",
				description: "Used in lists and the project schema. Reset to use the theme color.",
				field: "color",
				props: { value: doc.color || "" }
			},
			{
				kind: "Button",
				id: "adminSearchTypeResetColor",
				title: "Reset color",
				props: {
					icon: "reset",
					enabled: edit && !!doc.color,
					action: {
						type: "field",
						field: "color",
						value: ""
					}
				}
			}
		];
		if (!model.identity) fields.push({
			kind: "Switch",
			id: "adminSearchTypeHasPipeline",
			title: "Objects use a pipeline",
			description: "Allow processes and tasks for this Search Type.",
			field: "hasPipeline",
			props: { checked: !!doc.hasPipeline }
		});
		const body = sections(fields, width, language, edit);
		nodes.push(...body.nodes.map((row) => Object.assign({}, row, { y: row.y + y })));
		y += body.height;
		heading("typeImageHeading", tr("Search Type image"), tr(model.identity ? "The image belongs to the Search Type itself, not to one of its Search Objects. Saving adds the replacement to Commit Queue." : "You can choose an image now. After the Search Type is created, its preview will be sent through Commit Queue."));
		const side = width < 420 ? 112 : 144;
		nodes.push(node("Preview", "adminSearchTypePreview", rect(0, y, side, side), {
			source: model.previewUrl || "",
			initials: String(doc.title || "").slice(0, 2),
			round: false,
			icon: "sobject",
			accent: doc.color || "action",
			outlined: true
		}), button("adminSearchTypeChoosePreview", rect(side + 12, y, width - side - 12, 38), tr("Choose image"), "image", { type: "preview" }, edit && !model.previewQueued), button("adminSearchTypeCancelPreview", rect(side + 12, y + 46, width - side - 12, 38), tr("Undo image change"), "undo", { type: "clearPreview" }, edit && model.previewStaged));
		y += side + 12;
		nodes.push(node("Area", "typeImageStatus", rect(0, y, width, 70), {
			text: tr(model.previewStaged ? "A new preview is ready to be queued" : model.previewQueued ? "Image sent to Commit Queue; track upload progress there" : model.identity ? "Current Search Type preview" : "Preview is optional") + (model.previewError ? "\n" + model.previewError : ""),
			label: tr("Search Type image"),
			notice: true,
			readOnly: true,
			color: model.previewError ? "error" : "secondaryText"
		}));
		y += 78;
		nodes.push(button("typeImageQueue", rect(0, y, width, 38), tr("Open Commit Queue"), "cloud-upload", { type: "queue" }, true));
		y += 46;
	} else if (ui.page === "fields") {
		if (!model.identity) {
			heading("adminAutomaticFields", tr("Default fields"), tr("TACTIC creates these fields automatically. Add only extra fields below."));
			nodes.push(node("Area", "adminAutomaticFieldNames", rect(0, y, width, 84), {
				text: automaticFields.join(", "),
				label: tr("Default fields"),
				readOnly: true,
				notice: true
			}), label("adminAutomaticPipelineField", rect(0, y + 92, width, 70), tr(doc.hasPipeline ? "pipeline_code will also be created: pipeline support is enabled." : "pipeline_code will not be created: pipeline support is disabled."), Object.assign({ wrap: true }, muted)));
			y += 170;
		}
		const field = fieldTypes.find((row) => row.value === ui.fieldType) || fieldTypes[0];
		const body = sections([
			{
				kind: "Heading",
				id: "typeAddFieldHeading",
				title: "Add a field",
				description: "A field stores one attribute of each Search Object. Define its name and type here; fill in actual values when editing the objects."
			},
			{
				id: "adminNewColumnName",
				title: "Field name",
				description: "A technical name: lowercase Latin letters, numbers and underscores. No spaces; start with a letter.",
				props: {
					text: ui.fieldName,
					placeholder: field.name,
					action: { type: "fieldName" },
					keys: { Enter: { type: "addField" } }
				}
			},
			{
				id: "adminNewColumnType",
				kind: "Choice",
				title: "Field type",
				description: field.help,
				options: fieldTypes.map((row) => ({
					value: row.value,
					label: tr(row.label)
				})),
				props: {
					value: ui.fieldType,
					action: { type: "fieldType" }
				}
			}
		], width, language, edit);
		nodes.push(...body.nodes.map((row) => Object.assign({}, row, { y: row.y + y })));
		y += body.height;
		nodes.push(label("adminNewColumnExample", rect(0, y, width, 64), tr("Example: {name} = {value}", {
			name: ui.fieldName.trim() || field.name,
			value: tr(field.example)
		}) + " · " + tr("Database type: {type}", { type: ui.fieldType }), Object.assign({ wrap: true }, muted)), button("adminStageColumn", rect(0, y + 72, width, 38), tr("Add field"), "add", { type: "addField" }, edit && !!ui.fieldName.trim()));
		y += 118;
		if ((doc.columns || []).length) {
			heading("typeDraftFieldsHeading", tr("Fields to create ({count})", { count: doc.columns.length }), tr("These fields exist only in your draft. Save creates them; removing a draft field does not change the database."));
			for (let index = 0; index < doc.columns.length; index++) {
				const row = doc.columns[index];
				nodes.push(label("typeDraftName_" + row.name, rect(0, y, width - 44, 26), row.name, { weight: 600 }), label("typeDraftType_" + row.name, rect(0, y + 30, width - 44, 26), row.type, muted), button("adminRemoveColumn_" + row.name, rect(width - 38, y, 38, 38), tr("Remove draft field {name}", { name: row.name }), "delete", {
					type: "removeDraft",
					index
				}, edit, { iconOnly: true }));
				y += 66;
			}
		}
		if (model.identity) {
			heading("typeExistingFieldsHeading", tr("Existing fields ({count})", { count: Object.keys(meta.columns || {}).length }), tr("Delete marks a field for removal. Undo cancels the mark. Confirming Save deletes the column and its values; field types are not changed here."));
			nodes.push(node("Field", "adminExistingFieldsFilter", rect(0, y, width, 38), {
				text: ui.fieldQuery,
				label: tr("Find a field"),
				placeholder: tr("Find a field"),
				action: { type: "fieldQuery" }
			}));
			y += 46;
			nodes.push(node("List", "typeExistingFields", rect(0, y, width, Math.max(250, height - y)), {
				source: "fields",
				keyField: "name",
				rowHeight: width < 420 ? 192 : 144,
				scrollbarId: "typeExistingFieldsScrollBar"
			}));
			y += Math.max(250, height - y);
		}
	} else if (ui.page === "summary") {
		heading("typeSummaryHeading", doc.title || model.identity, model.identity);
		const metrics = [
			["total", "Search Objects"],
			["active", "Active"],
			["retired", "Retired"],
			["fields", "Fields"],
			["pipelines", "Pipelines"],
			["processes", "Processes"]
		], columns = width < 420 ? 2 : 3;
		metrics.forEach((row, index) => {
			const x = index % columns * width / columns, top = y + Math.floor(index / columns) * 72;
			nodes.push(label("adminSearchTypeCount_" + row[0], rect(x, top, width / columns - 8, 34), String((meta.summary || {})[row[0]] === void 0 ? "—" : meta.summary[row[0]]), {
				fontRole: "hero",
				weight: 600
			}), label("typeMetricLabel_" + row[0], rect(x, top + 38, width / columns - 8, 26), tr(row[1]), muted));
		});
		y += Math.ceil(metrics.length / columns) * 72;
		nodes.push(label("typeSummaryHelp", rect(0, y, width, 76), tr("Totals include retired Search Objects. Shared system types are counted in their own database. Reload to update the summary."), Object.assign({ wrap: true }, muted)));
		y += 84;
		heading("typeGraphHeading", tr("Relationship map"), tr("A read-only view of this Search Type and only its direct schema relationships."));
		nodes.push(node("Graph", "adminSearchTypeRelationshipGraph", rect(0, y, width, 400), Object.assign({}, model.relationshipGraph || {
			nodes: [],
			edges: []
		}, {
			label: tr("Relationship map"),
			style: model.style,
			language,
			readOnly: true,
			selectionEnabled: false,
			selectedNodes: model.identity ? [model.identity] : []
		})));
		y += 412;
		heading("typeRelationsHeading", tr("Schema relationships"), tr(meta.linkTable ? "This is a link table for a many-to-many relationship, not a separate object category." : "Relationships come from this project's schema and inherited schemas, not from table names."));
		nodes.push(node("Area", "typeDataLocation", rect(0, y, width, 92), {
			text: tr("Database") + ": " + (meta.database || "—") + " · " + tr("Table") + ": " + (meta.table || "—") + "\n" + tr(meta.projectLocal ? "Stored in the selected project" : "Shared data outside the selected project"),
			label: tr("Data location"),
			readOnly: true,
			notice: true
		}));
		y += 100;
		for (let index = 0; index < (meta.relationships || []).length; index++) {
			const edge = meta.relationships[index], name = (id) => (model.catalog.find((row) => row.identity === id) || {}).label || id;
			nodes.push(node("Area", "adminSearchTypeRelation_" + index, rect(0, y, width, 164), {
				text: name(edge.from) + " → " + name(edge.to) + "\n" + relationshipDescription(edge, language),
				label: tr("Schema relationships"),
				readOnly: true,
				notice: true
			}));
			y += 172;
		}
		if (!(meta.relationships || []).length) {
			nodes.push(label("typeRelationshipsEmpty", rect(0, y, width, 72), tr("No explicit relationships for this type in the loaded schemas."), Object.assign({ wrap: true }, muted)));
			y += 80;
		}
	} else if (ui.page === "workflow") {
		heading("typeWorkflowsHeading", tr("Linked workflows"), tr("Pipelines linked to this Search Type, including shared workflows."));
		if (!meta.hasPipeline) {
			nodes.push(label("typePipelineMissing", rect(0, y, width, 80), tr("This type has no pipeline_code field. Add it in Fields to assign workflows to its objects."), Object.assign({ wrap: true }, muted)));
			y += 88;
		}
		for (const row of meta.pipelines || []) {
			nodes.push(label("typeWorkflowTitle_" + row.identity, rect(0, y, width, 28), row.label, { weight: 600 }), node("Area", "typeWorkflowDescription_" + row.identity, rect(0, y + 32, width, 86), {
				text: (row.description || "") + "\n" + tr("{count} processes", { count: row.processCount }) + (row.shared ? " · " + tr("Shared · read-only") : ""),
				label: tr("Workflow"),
				readOnly: true,
				notice: true
			}), button("adminSearchTypeWorkflow_" + row.identity, rect(0, y + 126, width, 38), tr("Open workflow"), "workflow", {
				type: "workflow",
				identity: row.identity
			}, !model.busy && !model.uncertain && !model.namingLocked));
			y += 178;
		}
		if (!(meta.pipelines || []).length) {
			nodes.push(label("typeWorkflowsEmpty", rect(0, y, width, 70), tr("No workflows linked to this Search Type."), Object.assign({ wrap: true }, muted)));
			y += 78;
		}
		nodes.push(button("adminCreateTypeWorkflow", rect(0, y, width, 38), tr("Create workflow"), "add", {
			type: "workflow",
			identity: ""
		}, !model.busy && !model.uncertain && !model.namingLocked && model.canWrite));
		y += 46;
	} else if (ui.page === "ready") {
		heading("adminSearchTypeCreationReview", tr("Ready to create"), tr("This is how the new Search Type will appear. Nothing has been created on the server yet."));
		nodes.push(node("Preview", "adminSearchTypeCreationPreview", rect(0, y, 144, 144), {
			source: model.previewUrl || "",
			initials: String(doc.title || "").slice(0, 2),
			round: false,
			accent: doc.color || "action",
			icon: "sobject"
		}));
		y += 156;
		nodes.push(label("adminSearchTypeCreationTitle", rect(0, y, width, 32), doc.title || "", {
			fontRole: "display",
			weight: 600,
			color: doc.color || "action"
		}));
		y += 40;
		for (const row of [
			["adminSearchTypeCreationDescription", doc.description],
			["typeReviewPipeline", tr(doc.hasPipeline ? "Objects use a pipeline" : "No pipeline")],
			["adminSearchTypeCreationStandardFields", automaticFields.concat(doc.hasPipeline ? ["pipeline_code"] : []).join(", ")],
			["adminSearchTypeCreationAdditionalFields", (doc.columns || []).map((row) => row.name + " (" + row.type + ")").join("\n")]
		]) {
			nodes.push(node("Area", row[0], rect(0, y, width, 80), {
				text: row[1] || "",
				label: tr("Ready to create"),
				readOnly: true,
				notice: true
			}));
			y += 88;
		}
		nodes.push(button("typeCreateNow", rect(0, y, width, 38), tr("Create Search Type"), "add", { type: "save" }, edit));
		y += 46;
	}
	return {
		nodes,
		height: y + 8
	};
}
function relationshipDescription(edge, language) {
	const tr = (text, values) => translate(text, language, values), parts = [];
	if (edge.manyToMany) parts.push(tr("Many-to-many (M:N): each side can be linked to several objects on the other side."));
	else if (edge.type === "hierarchy") parts.push(tr("Hierarchy: child → parent."));
	if (edge.relationship || edge.type) parts.push(tr("Relationship in schema: {kind}", { kind: edge.relationship || edge.type }));
	if (edge.instanceType) parts.push(tr("Link table: {name}", { name: edge.instanceType }));
	if (edge.from_col || edge.to_col) parts.push(tr("Key fields: {from} → {to}", {
		from: edge.from_col || "—",
		to: edge.to_col || "—"
	}));
	parts.push(tr("Schema: {name}", { name: edge.schema || "—" }));
	return parts.join("\n");
}
function fieldDescription(info, language) {
	const tr = (text, values) => translate(text, language, values), name = String(info.data_type || "").toLowerCase().split("(")[0].trim();
	const index = {
		varchar: 0,
		"character varying": 0,
		character: 0,
		char: 0,
		text: 1,
		integer: 2,
		bigint: 2,
		smallint: 2,
		int: 2,
		int4: 2,
		int8: 2,
		numeric: 3,
		decimal: 3,
		real: 3,
		"double precision": 3,
		boolean: 4,
		bool: 4
	}[name], type = fieldTypes[name.indexOf("timestamp") === 0 ? 5 : index];
	const parts = [type ? tr(type.label) + " · " + info.data_type : info.data_type || ""];
	if (info.character_maximum_length) parts.push(tr("Up to {count} characters", { count: info.character_maximum_length }));
	if (info.is_nullable === "NO" || info.is_nullable === false) parts.push(tr("Cannot be empty in the database"));
	if (type) parts.push(tr("Example value: {value}", { value: tr(type.example) }));
	return parts.join("\n");
}
function row(listNode, record, model, ui, language) {
	const width = listNode.width - 16, tr = (text, values) => translate(text, language, values);
	if (listNode.source === "types") {
		const role = record.linkTable ? tr("Link table · M:N") : record.manyToMany ? tr("Many-to-many · M:N") : (record.relationships || []).length ? tr("Schema relationships: {count}", { count: record.relationships.length }) : record.table || "";
		return { nodes: [node("Action", "adminSearchType_" + record.identity, rect(0, 0, width, 84), {
			text: record.label,
			selected: model.identity === record.identity,
			enabled: !model.busy && (model.identity === record.identity || !model.dirty && !model.uncertain && !model.namingLocked),
			normalColor: "transparent",
			selectedColor: "contentSelection",
			children: [
				node("Icon", "typeIcon_" + record.identity, rect(10, 12, 22, 22), {
					icon: record.linkTable ? "link" : "sobject",
					color: record.color || "action"
				}),
				label("typeTitle_" + record.identity, rect(42, 6, width - 54, 26), record.label, { weight: 600 }),
				label("typeIdentity_" + record.identity, rect(42, 34, width - 54, 20), record.identity, muted),
				label("adminSearchTypeRole_" + record.identity, rect(42, 58, width - 54, 20), role, muted)
			],
			action: {
				type: "select",
				identity: record.identity
			}
		})] };
	}
	const marked = (model.document.removedColumns || []).indexOf(record.name) >= 0, reason = removalReasons[(model.metadata.columnRemovalBlocks || {})[record.name]], narrow = width < 420;
	return { nodes: [
		label("typeExistingName_" + record.name, rect(0, 0, narrow ? width : width - 160, 26), record.name, {
			weight: 600,
			strike: marked
		}),
		label("adminExistingField_" + record.name, rect(0, 32, narrow ? width : width - 160, narrow ? 104 : 100), marked ? tr("Marked for deletion. The column and its data will be deleted when you save.") : fieldDescription(record.info, language) + (reason ? "\n" + tr(reason) : ""), Object.assign({ wrap: true }, muted)),
		button("adminDeleteColumn_" + record.name, rect(narrow ? 0 : width - 152, narrow ? 144 : 8, 152, 36), tr(marked ? "Undo deletion" : "Delete field"), marked ? "undo" : "delete", {
			type: "removeField",
			name: record.name
		}, policy(model).editable && (!reason || marked), { destructive: !marked && !reason })
	] };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/search_types/search_types.state.mjs
function initial() {
	return {
		query: "",
		projectOnly: true,
		hideConfig: true,
		page: "summary",
		editing: false,
		catalogWidth: 280,
		fieldName: "",
		fieldType: "varchar(256)",
		fieldQuery: "",
		confirmation: "",
		error: ""
	};
}
function synchronize(ui, model) {
	if (model.ready && !model.identity && [
		"details",
		"fields",
		"ready"
	].indexOf(ui.page) < 0) return Object.assign({}, ui, {
		page: "details",
		editing: true
	});
	if (model.identity && ui.page === "ready") return Object.assign({}, ui, { page: "details" });
	return ui;
}
function detailsError(document) {
	if (!String(document.title || "").trim()) return "Enter a Search Type title";
	if (document.color && !/^#[0-9a-f]{6}$/i.test(document.color)) return "Use a color in #RRGGBB format or leave it empty";
	return "";
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], edit = policy(model).editable && !next.confirmation;
	const doc = documentEvent(ui, model, event);
	if (doc) return doc;
	switch (event.type) {
		case "query":
			if (!model.busy) next.query = event.value;
			break;
		case "projectOnly":
		case "hideConfig":
			if (!model.busy) next[event.type] = !!event.value;
			break;
		case "split":
			next.catalogWidth = Math.max(200, Math.min(420, Number(event.value)));
			break;
		case "back":
			if (!model.busy && model.identity) next.editing = false;
			break;
		case "page":
			if (model.busy || next.confirmation) break;
			if (!model.identity && event.value !== "details") {
				const error = detailsError(model.document);
				if (error) {
					next.error = error;
					break;
				}
			}
			commands.push({
				type: "page",
				value: event.value
			});
			break;
		case "field":
			if (edit) commands.push({
				type: "field",
				field: event.field,
				value: event.value
			});
			break;
		case "preview":
			if (edit) commands.push({ type: "preview" });
			break;
		case "clearPreview":
			if (edit) commands.push({ type: "clearPreview" });
			break;
		case "queue":
			commands.push({ type: "queue" });
			break;
		case "select":
			if (event.identity === model.identity && !model.busy && !next.confirmation) {
				next.editing = true;
				break;
			}
			if (!model.busy && !model.dirty && !model.uncertain && !model.namingLocked && !next.confirmation) commands.push(event);
			break;
		case "create":
			if (!model.busy && !model.dirty && !model.uncertain && !model.namingLocked && !next.confirmation && (event.type !== "create" || model.canWrite)) commands.push(event);
			break;
		case "fieldName":
		case "fieldType":
		case "fieldQuery":
			next[event.type] = event.value;
			break;
		case "addField":
			if (edit) {
				const name = ui.fieldName.trim(), automatic = automaticFields.concat(model.document.hasPipeline ? ["pipeline_code"] : []);
				if (!/^[a-z][a-z0-9_]*$/.test(name)) next.error = "Column names must be unique lowercase SQL identifiers";
				else if (!fieldTypes.some((row) => row.value === ui.fieldType)) next.error = "Unsupported column type";
				else if (name in (model.metadata.columns || {}) || (model.document.columns || []).some((row) => row.name === name) || !model.identity && automatic.indexOf(name) >= 0) next.error = "A column with this name already exists";
				else commands.push({
					type: "addField",
					name,
					columnType: ui.fieldType
				});
			}
			break;
		case "removeDraft":
			if (edit) commands.push(event);
			break;
		case "removeField":
			if (edit && (!(model.metadata.columnRemovalBlocks || {})[event.name] || (model.document.removedColumns || []).indexOf(event.name) >= 0)) commands.push(event);
			break;
		case "workflow": if (!model.busy && !model.uncertain && !model.namingLocked) commands.push(event);
	}
	return {
		ui: next,
		commands
	};
}
function completed(ui, command, model) {
	if (command.type === "page") return Object.assign({}, ui, {
		page: command.value,
		editing: true,
		error: ""
	});
	if (command.type === "select") return Object.assign({}, ui, {
		editing: true,
		page: "summary",
		error: ""
	});
	if (command.type === "create") return Object.assign({}, ui, {
		editing: true,
		page: "details",
		error: ""
	});
	if (command.type === "addField") return Object.assign({}, ui, {
		fieldName: "",
		error: ""
	});
	if (command.type === "reload" || command.type === "discard") return Object.assign({}, ui, {
		error: "",
		page: model.identity ? "summary" : "details"
	});
	return ui;
}
//#endregion
//#region src/features/administration/SearchTypes.vue
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
		queuePreview: Function,
		checkins: Array,
		creationOnly: Boolean,
		schemaRevision: String
	},
	emits: [
		"saved",
		"created",
		"back",
		"open-commit-queue",
		"open-workflow"
	],
	data() {
		return {
			catalog: [],
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			namingView: null,
			namingSession: {},
			identity: "",
			document: null,
			metadata: {},
			revision: "",
			baseline: "",
			busy: false,
			error: "",
			uncertain: false,
			canWrite: false,
			context: null,
			request: 0,
			previewFile: null,
			previewDataUrl: "",
			imageRequest: 0,
			previewUrl: "",
			previewError: "",
			previewRequest: 0,
			previewValidating: false
		};
	},
	computed: {
		documentDirty() {
			return this.uncertain || this.document !== null && (this.previewFile !== null || JSON.stringify(this.document) !== this.baseline);
		},
		namingDirty() {
			const saved = this.namingSession.snapshot;
			return this.namingView ? this.namingView.dirty : !!saved && (saved.uncertain || JSON.stringify(saved.document) !== saved.baseline);
		},
		dirty() {
			return this.documentDirty || this.namingDirty;
		},
		previewJob() {
			return this.checkins?.findLast((job) => job.searchKey === this.metadata.searchKey);
		},
		previewPending() {
			return this.previewJob && [
				"Queued",
				"Uploading",
				"Checking in",
				"Failed",
				"Result unknown"
			].includes(this.previewJob.status);
		},
		page: {
			get() {
				return this.ui.page;
			},
			set(value) {
				this.ui = {
					...this.ui,
					page: value
				};
			}
		},
		automaticFields() {
			return automaticFields.concat(this.document?.hasPipeline ? ["pipeline_code"] : []);
		},
		visibleTypes() {
			return records(this.frameModel, this.ui);
		},
		frameModel() {
			return {
				style: appearance.theme,
				ready: !!this.document,
				canWrite: !!this.ticket && this.canWrite && this.metadata.tableAvailable !== false,
				canLoad: !!this.ticket,
				busy: this.busy || this.previewValidating || !!this.namingView?.busy,
				dirty: this.documentDirty,
				uncertain: this.uncertain,
				error: this.error,
				message: "",
				identity: this.identity,
				document: this.document || {},
				metadata: this.metadata,
				catalog: this.catalog,
				creationOnly: !!this.creationOnly,
				namingLocked: this.namingDirty || !!this.namingView?.busy,
				relationshipGraph: this.metadata.relationshipGraph || {
					nodes: [],
					edges: []
				},
				previewUrl: this.previewDataUrl || this.previewUrl,
				previewStaged: !!this.previewFile,
				previewQueued: !!this.previewPending,
				previewError: this.previewError
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
				types: this.visibleTypes,
				fields: existing(this.frameModel, this.ui)
			};
		},
		views() {
			return { naming: {
				component: markRaw(NamingEditor_default),
				captureRef: this.captureNaming,
				props: {
					ticket: this.ticket,
					project: this.project,
					session: this.namingSession,
					searchType: this.identity,
					targetTitle: this.document?.title || this.identity,
					presentationVisible: this.presentationVisible,
					onSaved: () => this.$emit("saved")
				}
			} };
		}
	},
	created() {
		if (this.creationOnly) {
			this.canWrite = !!this.ticket;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.create();
		} else this.reload();
	},
	mounted() {
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
		this.observer?.disconnect();
		this.imageRequest++;
		this.request++;
		this.previewRequest++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		identity() {
			this.ui = synchronize(this.ui, this.frameModel);
		},
		document() {
			this.ui = synchronize(this.ui, this.frameModel);
		},
		ticket() {
			this.namingSession = {};
			this.reload();
		},
		project() {
			this.namingSession = {};
			this.reload();
		},
		"previewJob.status"(status) {
			if (status === "Complete") this.loadPreview();
		}
	},
	methods: {
		t,
		captureNaming(value) {
			this.namingView = value;
		},
		rowScene(node, record) {
			return row(node, record, this.frameModel, this.ui, appearance.language);
		},
		selectPage(page) {
			return this.dispatch({
				type: "page",
				value: page
			});
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) {
				switch (command.type) {
					case "field":
						this.document[command.field] = command.value;
						break;
					case "page": break;
					case "select":
						await this.select(command.identity);
						break;
					case "create":
						this.create();
						break;
					case "save":
						await this.save(true);
						break;
					case "reload":
						await this.reload();
						break;
					case "discard":
						this.previewFile = null;
						this.previewDataUrl = "";
						this.imageRequest++;
						this.document = this.baseline ? JSON.parse(this.baseline) : null;
						break;
					case "addField":
						this.addField(command.name, command.columnType);
						if (this.error) return;
						break;
					case "removeDraft":
						this.document.columns.splice(command.index, 1);
						break;
					case "removeField":
						this.toggleDeletion(command.name);
						break;
					case "preview":
						this.$refs.previewFile.click();
						break;
					case "clearPreview":
						this.previewFile = null;
						this.previewDataUrl = "";
						this.imageRequest++;
						this.previewError = "";
						break;
					case "queue":
						this.$emit("open-commit-queue");
						break;
					case "workflow":
						this.$emit("open-workflow", {
							identity: command.identity,
							searchType: this.identity
						});
						break;
					default: throw Error("Unsupported Search Types command: " + command.type);
				}
				this.ui = completed(this.ui, command, this.frameModel);
			}
		},
		async choosePreview(event) {
			const file = event.target.files[0];
			event.target.value = "";
			if (!file) return;
			const id = ++this.imageRequest;
			this.previewValidating = true;
			this.previewError = "";
			try {
				const url = await readPreviewImage(file);
				if (id === this.imageRequest) {
					this.previewFile = file;
					this.previewDataUrl = url;
				}
			} catch {
				if (id === this.imageRequest) this.previewError = "The selected preview is not a readable image";
			} finally {
				if (id === this.imageRequest) this.previewValidating = false;
			}
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain || this.previewValidating) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.namingView && !this.namingView.canLeave()) return false;
			if (!this.namingView && this.namingDirty && !window.confirm(t("Discard unsaved naming changes?"))) return false;
			return !this.busy && !this.previewValidating && (!this.documentDirty || window.confirm(t("Discard unsaved changes?")));
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				},
				"tactic.ui.panel.search_types_cmd.SearchTypesCmd",
				{
					action,
					project_code: this.context.project,
					...values
				}
			])).info;
		},
		accept(result) {
			this.catalog = result.catalog;
			this.canWrite = result.canWrite !== false;
			this.identity = result.identity;
			this.document = result.document;
			this.metadata = result.metadata;
			this.revision = result.revision;
			this.baseline = JSON.stringify(this.document);
			this.previewFile = null;
			this.previewDataUrl = "";
			this.imageRequest++;
			this.previewValidating = false;
			this.loadPreview();
		},
		async loadPreview() {
			const id = ++this.previewRequest;
			const key = this.metadata.searchKey;
			this.previewUrl = this.previewError = "";
			if (!key) return;
			try {
				const snapshot = await rpc("get_snapshot", [
					{
						ticket: this.context.ticket,
						project: "sthpw",
						language: "python"
					},
					key,
					"icon"
				], { include_web_paths_dict: true });
				if (id !== this.previewRequest) return;
				const paths = snapshot.__web_paths_dict__ || {};
				const path = paths.web?.[0] || paths.icon?.[0] || "";
				if (path) {
					const url = new URL(path, location.origin);
					if (url.origin === location.origin) this.previewUrl = url.pathname + url.search;
				}
			} catch (error) {
				if (id === this.previewRequest) this.previewError = error.message;
			}
		},
		async reload() {
			const id = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("list");
				if (id !== this.request) return;
				this.catalog = result.catalog;
				this.canWrite = result.canWrite !== false;
				const selected = this.catalog.find((row) => row.identity === this.identity) || this.visibleTypes[0];
				if (selected) {
					const loaded = await this.call("load", { identity: selected.identity });
					if (id !== this.request) return;
					this.accept(loaded);
					this.page = "summary";
				} else {
					this.document = null;
					this.identity = "";
					this.previewFile = null;
					this.previewRequest++;
					this.previewUrl = this.previewError = "";
				}
				this.uncertain = false;
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		async select(identity) {
			if (!identity || identity === this.identity || !this.canLeave()) return;
			const id = ++this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("load", { identity });
				if (id === this.request) {
					this.accept(result);
					this.page = "summary";
					this.uncertain = false;
				}
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		create() {
			if (!this.canLeave()) return;
			this.identity = this.revision = this.error = "";
			this.document = {
				title: "",
				description: "",
				color: "",
				hasPipeline: true,
				columns: [],
				removedColumns: []
			};
			this.metadata = {};
			this.previewFile = null;
			this.previewRequest++;
			this.previewUrl = this.previewError = "";
			this.page = "details";
			this.baseline = "";
			this.uncertain = false;
		},
		addField(value, type) {
			if (this.busy || this.uncertain) return;
			const name = value.trim();
			if (!/^[a-z][a-z0-9_]*$/.test(name)) {
				this.error = "Column names must be unique lowercase SQL identifiers";
				return;
			}
			if (!fieldTypes.some((field) => field.value === type)) {
				this.error = "Unsupported column type";
				return;
			}
			if (name in (this.metadata.columns || {}) || this.document.columns.some((field) => field.name === name) || !this.identity && this.automaticFields.includes(name)) {
				this.error = "A column with this name already exists";
				return;
			}
			this.document.columns.push({
				name,
				type
			});
			this.error = "";
			this.ui = {
				...this.ui,
				fieldName: ""
			};
		},
		toggleDeletion(name) {
			if (this.busy || this.uncertain || this.metadata.columnRemovalBlocks?.[name] && !this.document.removedColumns.includes(name)) return;
			const index = this.document.removedColumns.indexOf(name);
			if (index < 0) this.document.removedColumns.push(name);
			else this.document.removedColumns.splice(index, 1);
		},
		submit() {
			if (this.identity || this.page === "ready") this.save();
			else this.selectPage(this.page === "details" ? "fields" : "ready");
		},
		async save(confirmed = false) {
			if (this.busy || this.previewValidating || this.uncertain || !this.documentDirty || !this.document.title.trim()) return;
			if (!this.identity && this.page !== "ready") return;
			if (!confirmed && (this.document.removedColumns || []).length && !window.confirm(t("Delete fields from {type}: {fields}? All values in these columns will be lost. Check scripts, naming rules and saved searches before saving.", {
				type: this.identity,
				fields: this.document.removedColumns.join(", ")
			}))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			try {
				const file = this.previewFile;
				const creating = !this.identity;
				const result = await this.call("save", {
					identity: this.identity,
					expected_revision: this.revision,
					document: this.document,
					...creating && this.creationOnly ? { schema_revision: this.schemaRevision } : {}
				});
				if (id !== this.request) return;
				this.accept(result);
				if (creating) this.page = "details";
				if (!this.creationOnly) this.$emit("saved");
				if (file) try {
					this.queuePreview({
						ticket: this.context.ticket,
						project: "sthpw",
						searchKey: this.metadata.searchKey,
						title: this.document.title,
						file,
						name: file.name
					});
				} catch (error) {
					this.previewFile = file;
					this.previewError = t("Search Type saved, but its preview could not be queued: {error}", { error: error.message });
				}
				if (creating && this.creationOnly) this.$emit("created", result);
				if (this.creationOnly) this.$emit("saved");
			} catch (error) {
				if (id !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Refresh before trying again." : error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		async workflowSaved() {
			const id = this.request;
			try {
				const result = await this.call("load", { identity: this.identity });
				if (id === this.request) {
					if (this.dirty) {
						this.metadata = result.metadata;
						this.catalog = result.catalog;
					} else this.accept(result);
					this.$emit("saved");
				}
			} catch (error) {
				if (id === this.request) this.error = error.message;
			}
		},
		async reset() {
			if (this.canLeave()) {
				this.document = null;
				await this.reload();
			}
		}
	}
};
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
var _hoisted_3 = ["disabled"];
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "search-types-editor frame-host",
		"aria-busy": $data.busy || $data.previewValidating
	}, [
		(openBlock(), createBlock(Teleport, {
			to: $props.toolbarTarget || "body",
			disabled: !$props.toolbarTarget
		}, [withDirectives(createBaseVNode("div", {
			class: "frame-toolbar-host",
			style: normalizeStyle({ width: $data.toolbarSize + "px" })
		}, [createVNode(_component_FrameView, {
			scene: $options.toolbarScene,
			onEvent: $options.dispatch
		}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])),
		createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
			scene: $options.frameScene,
			models: $options.models,
			views: $options.views,
			"describe-row": $options.rowScene,
			onEvent: $options.dispatch
		}, null, 8, [
			"scene",
			"models",
			"views",
			"describe-row",
			"onEvent"
		])], 512),
		createBaseVNode("input", {
			ref: "previewFile",
			type: "file",
			hidden: "",
			accept: "image/png,image/jpeg,image/webp,image/gif,image/bmp",
			disabled: $data.busy || $data.previewValidating || $data.uncertain || !!$options.previewPending,
			onChange: _cache[0] || (_cache[0] = (...args) => $options.choosePreview && $options.choosePreview(...args))
		}, null, 40, _hoisted_3)
	], 8, _hoisted_1);
}
var SearchTypes_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { SearchTypes_default as default };

//# sourceMappingURL=SearchTypes.js.map
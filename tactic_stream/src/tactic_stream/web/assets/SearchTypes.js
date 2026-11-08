import { I as resolveComponent, N as openBlock, Y as markRaw, c as vShow, g as createBlock, h as createBaseVNode, p as Teleport, q as withDirectives, rt as normalizeStyle, v as createElementBlock, x as createVNode } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { M as rpc } from "./index.js";
import { K as button, T as translate, U as observeFrameSizes, X as node, Y as muted, Z as rect, q as label, t as _sfc_main$1 } from "./FrameView.js";
import { t as readPreviewImage } from "./previewImage.js";
import { n as sections } from "./sections.ui.js";
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
	const query = (ui.query || "").toLowerCase();
	if (!query && !ui.projectOnly && !ui.hideConfig) return model.catalog;
	return model.catalog.filter((row) => (!ui.projectOnly || row.projectLocal) && (!ui.hideConfig || row.namespace !== "config") && (!query || String(row.label || "").toLowerCase().indexOf(query) >= 0 || String(row.identity || "").toLowerCase().indexOf(query) >= 0));
}
function existing(model, ui) {
	const columns = model.metadata.columns || {}, query = (ui.fieldQuery || "").toLowerCase(), names = Object.keys(columns);
	return (query ? names.filter((name) => name.toLowerCase().indexOf(query) >= 0) : names).map((name) => ({
		name,
		info: columns[name]
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
	const split = !model.creationOnly && width >= 850, catalogVisible = ui.catalogVisible !== false, left = split ? catalogVisible ? Math.min(ui.catalogWidth, width * .4) : 56 : width, edit = policy(model).editable && !ui.confirmation, navigate = !model.busy && !model.dirty && !model.uncertain && !model.namingLocked && !ui.confirmation;
	if (!model.creationOnly && (split || !ui.editing)) {
		const children = [];
		if (!split || catalogVisible) {
			children.push(label("typesCatalogTitle", rect(12, 10, Math.max(0, left - (split ? 62 : 24)), 34), tr("Search Types"), { weight: 600 }), node("Field", "adminSearchTypeFilter", rect(12, 52, left - 24, 38), {
				label: tr("Find a Search Type"),
				placeholder: tr("Find a Search Type"),
				text: ui.query,
				enabled: !model.busy,
				action: { type: "query" }
			}), node("CheckBox", "adminSearchTypesProjectOnly", rect(12, 98, left - 24, 32), {
				text: tr("Only current project"),
				checked: ui.projectOnly,
				enabled: !model.busy,
				action: { type: "projectOnly" }
			}), node("CheckBox", "adminSearchTypesHideConfig", rect(12, 136, left - 24, 32), {
				text: tr("Hide config types"),
				checked: ui.hideConfig,
				enabled: !model.busy,
				action: { type: "hideConfig" }
			}), node("List", "adminSearchTypesList", rect(12, 176, left - 24, Math.max(0, h - 188)), {
				source: "types",
				rowHeight: 88,
				keyField: "identity",
				scrollbarId: "adminSearchTypesScrollBar"
			}));
			if (!records(model, ui).length) children.push(label("typesCatalogEmpty", rect(12, 186, left - 24, 90), tr("No types found"), Object.assign({ wrap: true }, muted)));
		}
		if (split) children.push(button("adminToggleTypesCatalog", rect(catalogVisible ? left - 46 : (left - 34) / 2, 10, 34, 34), tr(catalogVisible ? "Hide Search Types" : "Show Search Types"), catalogVisible ? "chevron-left" : "chevron-right", { type: "catalogVisible" }, true, {
			iconOnly: true,
			iconAction: true,
			round: false
		}));
		nodes.push(node("Box", "typesCatalogPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
	}
	if (split && catalogVisible) nodes.push(node("Splitter", "typesCatalogSplitHandle", rect(left, y, 10, h), {
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
		const addPad = width < 380 ? 10 : 14, inlineAdd = width >= 560, addBtnW = inlineAdd ? Math.min(Math.max(164, tr("Add field").length * 7.5 + 48), 210) : Math.max(1, width - addPad * 2), exampleW = Math.max(40, width - addPad * 2 - 28 - (inlineAdd ? addBtnW + 14 : 0)), addCardH = inlineAdd ? 62 : 104;
		nodes.push(node("Box", "typeAddFieldFooterCard", rect(0, y, width, addCardH), {
			background: "surfaceContainer",
			border: "outlineVariant",
			radius: 10,
			children: [
				node("Icon", "typeAddFieldExampleIcon", rect(addPad, inlineAdd ? 22 : 14, 18, 18), {
					icon: "code",
					color: "action"
				}),
				label("adminNewColumnExample", rect(addPad + 26, inlineAdd ? 10 : 8, exampleW, 42), tr("Example: {name} = {value}", {
					name: ui.fieldName.trim() || field.name,
					value: tr(field.example)
				}) + " · " + tr("Database type: {type}", { type: ui.fieldType }), Object.assign({
					wrap: true,
					monospace: true
				}, muted)),
				button("adminStageColumn", inlineAdd ? rect(width - addPad - addBtnW, 12, addBtnW, 38) : rect(addPad, 54, addBtnW, 38), tr("Add field"), "add", { type: "addField" }, edit && !!ui.fieldName.trim())
			]
		}));
		y += addCardH + 14;
		if ((doc.columns || []).length) {
			heading("typeDraftFieldsHeading", tr("Fields to create ({count})", { count: doc.columns.length }), tr("These fields exist only in your draft. Save creates them; removing a draft field does not change the database."));
			for (let index = 0; index < doc.columns.length; index++) {
				const row = doc.columns[index], dPad = width < 380 ? 10 : 14;
				nodes.push(node("Box", "typeDraftCard_" + row.name, rect(0, y, width, 62), {
					background: "surfaceContainer",
					border: "outlineVariant",
					radius: 10,
					children: [
						node("Icon", "typeDraftIcon_" + row.name, rect(dPad, 14, 18, 18), {
							icon: "add",
							color: "action"
						}),
						label("typeDraftName_" + row.name, rect(dPad + 26, 8, Math.max(0, width - dPad * 2 - 74), 24), row.name, {
							weight: 600,
							monospace: true
						}),
						label("typeDraftType_" + row.name, rect(dPad + 26, 32, Math.max(0, width - dPad * 2 - 74), 20), row.type, Object.assign({ monospace: true }, muted)),
						button("adminRemoveColumn_" + row.name, rect(width - dPad - 38, 12, 38, 38), tr("Remove draft field {name}", { name: row.name }), "delete", {
							type: "removeDraft",
							index
						}, edit, {
							iconOnly: true,
							round: false
						})
					]
				}));
				y += 70;
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
				rowHeight: width < 420 ? 188 : 136,
				scrollbarId: "typeExistingFieldsScrollBar"
			}));
			y += Math.max(250, height - y);
		}
	} else if (ui.page === "summary") {
		const textHeight = (value) => String(value).split("\n").reduce((lines, line) => lines + Math.max(1, Math.ceil(line.length / Math.max(12, Math.floor((width - 24) / 7)))), 0) * 20;
		const summaryHeading = (id, title, description) => {
			nodes.push(label(id, rect(0, y, width, 28), title, {
				role: "heading",
				level: 2,
				fontRole: "section",
				weight: 600
			}));
			y += 30;
			if (description) {
				const h = textHeight(description);
				nodes.push(label(id + "Description", rect(0, y, width, h), description, Object.assign({ wrap: true }, muted)));
				y += h + 8;
			}
		};
		const metrics = [
			["total", "Search Objects"],
			["active", "Active"],
			["retired", "Retired"],
			["fields", "Fields"],
			["pipelines", "Pipelines"],
			["processes", "Processes"]
		], columns = width >= 960 ? 6 : width >= 540 ? 3 : 2, rowHeight = 64, metricsHeight = Math.ceil(metrics.length / columns) * rowHeight, metricNodes = [];
		metrics.forEach((row, index) => {
			const x = index % columns * width / columns, top = Math.floor(index / columns) * rowHeight;
			if (index % columns) metricNodes.push(node("Box", "typeMetricDivider_" + row[0], rect(x, top + 10, 1, 44), {
				background: "outlineVariant",
				radius: 0
			}));
			if (index && index % columns === 0) metricNodes.push(node("Box", "typeMetricRowDivider_" + row[0], rect(12, top, width - 24, 1), {
				background: "outlineVariant",
				radius: 0
			}));
			metricNodes.push(label("adminSearchTypeCount_" + row[0], rect(x + 12, top + 6, width / columns - 24, 28), String((meta.summary || {})[row[0]] === void 0 ? "—" : meta.summary[row[0]]), {
				fontRole: "title",
				weight: 600
			}), label("typeMetricLabel_" + row[0], rect(x + 12, top + 36, width / columns - 24, 22), tr(row[1]), muted));
		});
		nodes.push(node("Box", "typeSummaryMetrics", rect(0, y, width, metricsHeight), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			radius: 10,
			children: metricNodes
		}));
		y += metricsHeight + 12;
		summaryHeading("typeGraphHeading", tr("Relationship map"));
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
		summaryHeading("typeRelationsHeading", tr("Schema relationships"), tr(meta.linkTable ? "This is a link table for a many-to-many relationship, not a separate object category." : "Relationships come from this project's schema and inherited schemas, not from table names."));
		const locPad = width < 380 ? 10 : 14, locInner = Math.max(1, width - locPad * 2), locCols = locInner >= 420 ? 2 : 1, locCellW = (locInner - (locCols - 1) * 10) / locCols, locScopeText = tr(meta.projectLocal ? "Stored in the selected project" : "Shared data outside the selected project"), locText = tr("Database") + ": " + (meta.database || "—") + " · " + tr("Table") + ": " + (meta.table || "—") + "\n" + locScopeText, locRows = locCols === 2 ? 1 : 2, locCardH = 44 + locRows * 52 + (locRows - 1) * 8 + 12, locChildren = [node("Icon", "typeDataLocationIcon", rect(locPad, 12, 18, 18), {
			icon: "storage",
			color: "action"
		}), label("typeDataLocationTitle", rect(locPad + 26, 9, Math.max(0, locInner - 26), 24), tr("Data location"), { weight: 600 })];
		if (width >= 460) {
			const badgeW = Math.min(Math.max(150, locScopeText.length * 6.8 + 36), Math.floor(width * .56));
			locChildren.push(node("Box", "typeDataLocationScopeBadge", rect(width - locPad - badgeW, 8, badgeW, 26), {
				background: "surfaceContainerHigh",
				border: "outlineVariant",
				radius: 13,
				children: [node("Icon", "typeDataLocationScopeIcon", rect(10, 5, 15, 15), {
					icon: meta.projectLocal ? "folder-open" : "layers",
					color: "action"
				}), label("typeDataLocationScopeLabel", rect(30, 3, Math.max(0, badgeW - 38), 20), locScopeText, {
					fontRole: "secondary",
					weight: 600
				})]
			}));
		}
		[[
			"db",
			"dns",
			tr("Database"),
			meta.database || "—"
		], [
			"table",
			"table-view",
			tr("Table"),
			meta.table || "—"
		]].forEach(([key, iconName, titleText, valText], idx) => {
			const r = Math.floor(idx / locCols), c = idx % locCols, tx = locPad + c * (locCellW + 10), ty = 44 + r * 60;
			locChildren.push(node("Box", "typeDataLocationTile_" + key, rect(tx, ty, locCellW, 52), {
				background: "surfaceContainerHigh",
				border: "outlineVariant",
				radius: 8,
				children: [
					node("Icon", "typeDataLocationTileIcon_" + key, rect(10, 8, 14, 14), {
						icon: iconName,
						color: "action"
					}),
					label("typeDataLocationTileLabel_" + key, rect(28, 5, Math.max(0, locCellW - 36), 18), titleText, muted),
					label("typeDataLocationTileValue_" + key, rect(10, 25, Math.max(0, locCellW - 20), 22), valText, {
						weight: 600,
						monospace: true
					})
				]
			}));
		});
		nodes.push(node("Box", "typeDataLocation", rect(0, y, width, locCardH), {
			text: locText,
			background: "surfaceContainer",
			border: "outlineVariant",
			radius: 10,
			children: locChildren
		}));
		y += locCardH + 10;
		for (let index = 0; index < (meta.relationships || []).length; index++) {
			const edge = meta.relationships[index], name = (id) => (model.catalog.find((row) => row.identity === id) || {}).label || id, fromLabel = name(edge.from), toLabel = name(edge.to), description = fromLabel + " → " + toLabel + "\n" + relationshipDescription(edge, language), cardPad = width < 380 ? 10 : 14, innerW = Math.max(1, width - cardPad * 2), tiles = [];
			if (edge.from_col || edge.to_col) tiles.push([
				"keys",
				"key",
				tr("Key fields"),
				(edge.from_col || "—") + "  →  " + (edge.to_col || "—"),
				true
			]);
			if (edge.relationship || edge.type) tiles.push([
				"kind",
				"code",
				tr("Relationship in schema"),
				String(edge.relationship || edge.type),
				true
			]);
			tiles.push([
				"schema",
				"folder-open",
				tr("Schema"),
				String(edge.schema || "—"),
				true
			]);
			if (edge.instanceType) tiles.push([
				"linkTable",
				"link",
				tr("Link table"),
				String(edge.instanceType),
				true
			]);
			const tileCols = innerW >= 620 ? Math.min(tiles.length, 3) : innerW >= 400 ? Math.min(tiles.length, 2) : 1, tileGap = 10, tileW = (innerW - (tileCols - 1) * tileGap) / Math.max(1, tileCols), tileRows = Math.ceil(tiles.length / Math.max(1, tileCols)), manyNote = edge.manyToMany ? tr("Many-to-many (M:N): each side can be linked to several objects on the other side.") : "", manyNoteH = manyNote ? width < 460 ? 44 : 26 : 0, relationHeight = 52 + tileRows * 52 + Math.max(0, tileRows - 1) * 8 + (manyNoteH ? manyNoteH + 10 : 0) + 14, modeBadgeText = edge.manyToMany ? tr("Many-to-many · M:N") : edge.type === "hierarchy" ? tr("Hierarchy · child → parent") : tr("Schema link"), showBadge = width >= 460, badgeW = showBadge ? Math.min(Math.max(130, modeBadgeText.length * 6.8 + 34), Math.floor(width * .44)) : 0, headerAvailW = Math.max(60, innerW - 26 - (showBadge ? badgeW + 10 : 0)), relChildren = [
				node("Icon", "adminSearchTypeRelationIcon_" + index, rect(cardPad, 13, 18, 18), {
					icon: edge.manyToMany ? "link" : "hierarchy",
					color: "action"
				}),
				label("adminSearchTypeRelationTitle_" + index, rect(cardPad + 26, 10, headerAvailW, 24), fromLabel + "  →  " + toLabel, {
					fontRole: "section",
					weight: 600
				}),
				node("Box", "adminSearchTypeRelationDivider_" + index, rect(cardPad, 42, innerW, 1), { background: "outlineVariant" })
			];
			if (showBadge) relChildren.push(node("Box", "adminSearchTypeRelationBadge_" + index, rect(width - cardPad - badgeW, 9, badgeW, 26), {
				background: "surfaceContainerHigh",
				border: "outlineVariant",
				radius: 13,
				children: [node("Icon", "adminSearchTypeRelationBadgeIcon_" + index, rect(10, 5, 15, 15), {
					icon: edge.manyToMany ? "link" : "hierarchy",
					color: "action"
				}), label("adminSearchTypeRelationBadgeText_" + index, rect(30, 3, Math.max(0, badgeW - 38), 20), modeBadgeText, {
					fontRole: "secondary",
					weight: 600
				})]
			}));
			tiles.forEach(([tKey, tIcon, tLabel, tVal, mono], tIdx) => {
				const r = Math.floor(tIdx / tileCols), c = tIdx % tileCols, tx = cardPad + c * (tileW + tileGap), ty = 52 + r * 60;
				relChildren.push(node("Box", "adminSearchTypeRelationTile_" + index + "_" + tKey, rect(tx, ty, tileW, 52), {
					background: "surfaceContainerHigh",
					border: "outlineVariant",
					radius: 8,
					children: [
						node("Icon", "adminSearchTypeRelationTileIcon_" + index + "_" + tKey, rect(10, 8, 14, 14), {
							icon: tIcon,
							color: "action"
						}),
						label("adminSearchTypeRelationTileLabel_" + index + "_" + tKey, rect(28, 5, Math.max(0, tileW - 36), 18), tLabel, muted),
						label("adminSearchTypeRelationTileValue_" + index + "_" + tKey, rect(10, 25, Math.max(0, tileW - 20), 22), tVal, {
							weight: 600,
							monospace: !!mono
						})
					]
				}));
			});
			if (manyNote) {
				const noteY = 52 + tileRows * 52 + Math.max(0, tileRows - 1) * 8 + 8;
				relChildren.push(label("adminSearchTypeRelationNote_" + index, rect(cardPad, noteY, innerW, manyNoteH), manyNote, Object.assign({ wrap: true }, muted)));
			}
			nodes.push(node("Box", "adminSearchTypeRelation_" + index, rect(0, y, width, relationHeight), {
				text: description,
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: relChildren
			}));
			y += relationHeight + 10;
		}
		if (!(meta.relationships || []).length) {
			const empty = tr("No explicit relationships for this type in the loaded schemas."), emptyHeight = textHeight(empty);
			nodes.push(label("typeRelationshipsEmpty", rect(0, y, width, emptyHeight), empty, Object.assign({ wrap: true }, muted)));
			y += emptyHeight + 8;
		}
	} else if (ui.page === "workflow") {
		heading("typeWorkflowsHeading", tr("Linked workflows"), tr("Pipelines linked to this Search Type, including shared workflows."));
		if (!meta.hasPipeline) {
			const missingPad = width < 380 ? 10 : 14, missingH = width < 520 ? 76 : 56;
			nodes.push(node("Box", "typePipelineMissingCard", rect(0, y, width, missingH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: [node("Icon", "typePipelineMissingIcon", rect(missingPad, 14, 18, 18), {
					icon: "warning",
					color: "warning"
				}), label("typePipelineMissing", rect(missingPad + 28, 10, Math.max(0, width - missingPad * 2 - 28), missingH - 20), tr("This type has no pipeline_code field. Add it in Fields to assign workflows to its objects."), Object.assign({ wrap: true }, muted))]
			}));
			y += missingH + 12;
		}
		const canOpenWorkflow = !model.busy && !model.uncertain && !model.namingLocked;
		for (const row of meta.pipelines || []) {
			const cardPad = width < 380 ? 10 : 14, innerW = Math.max(1, width - cardPad * 2), inlineAction = width >= 460, openBtnW = inlineAction ? Math.min(Math.max(156, tr("Open workflow").length * 7.5 + 44), 210) : innerW, scopeText = row.shared ? tr("Shared · read-only") : tr("Current project"), showBadge = width >= 660, badgeW = showBadge ? Math.min(Math.max(126, scopeText.length * 6.8 + 34), Math.floor(width * .34)) : 0, titleW = Math.max(60, innerW - 28 - (inlineAction ? openBtnW + 10 : 0) - (showBadge ? badgeW + 10 : 0)), tiles = [
				[
					"code",
					"code",
					tr("Code"),
					row.identity,
					true
				],
				[
					"processes",
					"checklist",
					tr("Processes"),
					tr("{count} processes", { count: row.processCount }),
					false
				],
				[
					"scope",
					row.shared ? "layers" : "folder-open",
					tr("Data location"),
					scopeText,
					false
				]
			], tileCols = innerW >= 580 ? 3 : innerW >= 380 ? 2 : 1, tileGap = 10, tileW = (innerW - (tileCols - 1) * tileGap) / Math.max(1, tileCols), tileRows = Math.ceil(tiles.length / Math.max(1, tileCols)), descText = String(row.description || "").trim(), descH = descText ? Math.max(24, Math.ceil(descText.length / Math.max(18, Math.floor((innerW - 28) / 7))) * 20) : 0, tilesTop = 54, tilesBottom = tilesTop + tileRows * 52 + Math.max(0, tileRows - 1) * 8, descTop = descH ? tilesBottom + 10 : tilesBottom, bottomBtnTop = !inlineAction ? descH ? descTop + descH + 10 : tilesBottom + 10 : 0, cardH = (!inlineAction ? bottomBtnTop + 38 : descH ? descTop + descH : tilesBottom) + 14, summaryText = (descText ? descText + "\n" : "") + tr("{count} processes", { count: row.processCount }) + (row.shared ? " · " + tr("Shared · read-only") : ""), cardChildren = [
				node("Icon", "typeWorkflowIcon_" + row.identity, rect(cardPad, 15, 18, 18), {
					icon: "workflow",
					color: row.color || "action"
				}),
				label("typeWorkflowTitle_" + row.identity, rect(cardPad + 26, 11, titleW, 26), row.label, {
					fontRole: "section",
					weight: 600
				}),
				node("Box", "typeWorkflowDivider_" + row.identity, rect(cardPad, 45, innerW, 1), { background: "outlineVariant" })
			];
			if (showBadge) {
				const badgeX = width - cardPad - (inlineAction ? openBtnW + 10 : 0) - badgeW;
				cardChildren.push(node("Box", "typeWorkflowBadge_" + row.identity, rect(badgeX, 10, badgeW, 26), {
					background: "surfaceContainerHigh",
					border: "outlineVariant",
					radius: 13,
					children: [node("Icon", "typeWorkflowBadgeIcon_" + row.identity, rect(10, 5, 15, 15), {
						icon: row.shared ? "layers" : "folder-open",
						color: row.color || "action"
					}), label("typeWorkflowBadgeText_" + row.identity, rect(30, 3, Math.max(0, badgeW - 38), 20), scopeText, {
						fontRole: "secondary",
						weight: 600
					})]
				}));
			}
			tiles.forEach(([tKey, tIcon, tLabel, tVal, mono], tIdx) => {
				const r = Math.floor(tIdx / tileCols), c = tIdx % tileCols, tx = cardPad + c * (tileW + tileGap), ty = tilesTop + r * 60;
				cardChildren.push(node("Box", "typeWorkflowTile_" + row.identity + "_" + tKey, rect(tx, ty, tileW, 52), {
					background: "surfaceContainerHigh",
					border: "outlineVariant",
					radius: 8,
					children: [
						node("Icon", "typeWorkflowTileIcon_" + row.identity + "_" + tKey, rect(10, 8, 14, 14), {
							icon: tIcon,
							color: row.color || "action"
						}),
						label("typeWorkflowTileLabel_" + row.identity + "_" + tKey, rect(28, 5, Math.max(0, tileW - 36), 18), tLabel, muted),
						label("typeWorkflowTileValue_" + row.identity + "_" + tKey, rect(10, 25, Math.max(0, tileW - 20), 22), tVal, {
							weight: 600,
							monospace: !!mono
						})
					]
				}));
			});
			if (descH) cardChildren.push(node("Icon", "typeWorkflowDescIcon_" + row.identity, rect(cardPad, descTop + 3, 15, 15), {
				icon: "description",
				color: "muted"
			}), label("typeWorkflowDescription_" + row.identity, rect(cardPad + 24, descTop, Math.max(0, innerW - 24), descH), descText, Object.assign({ wrap: true }, muted)));
			cardChildren.push(button("adminSearchTypeWorkflow_" + row.identity, inlineAction ? rect(width - cardPad - openBtnW, 7, openBtnW, 32) : rect(cardPad, bottomBtnTop, innerW, 38), tr("Open workflow"), "workflow", {
				type: "workflow",
				identity: row.identity
			}, canOpenWorkflow));
			nodes.push(node("Box", "typeWorkflowCard_" + row.identity, rect(0, y, width, cardH), {
				text: summaryText,
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: cardChildren
			}));
			y += cardH + 10;
		}
		if (!(meta.pipelines || []).length) {
			const emptyPad = width < 380 ? 10 : 14;
			nodes.push(node("Box", "typeWorkflowsEmptyCard", rect(0, y, width, 56), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: [node("Icon", "typeWorkflowsEmptyIcon", rect(emptyPad, 19, 18, 18), {
					icon: "workflow",
					color: "muted"
				}), label("typeWorkflowsEmpty", rect(emptyPad + 28, 16, Math.max(0, width - emptyPad * 2 - 28), 24), tr("No workflows linked to this Search Type."), Object.assign({ wrap: true }, muted))]
			}));
			y += 68;
		}
		const createPad = width < 380 ? 10 : 14, inlineCreate = width >= 520, createBtnW = inlineCreate ? Math.min(Math.max(168, tr("Create workflow").length * 7.5 + 48), 230) : Math.max(1, width - createPad * 2), createCardH = inlineCreate ? 56 : 92, createChildren = [
			node("Icon", "typeCreateWorkflowIcon", rect(createPad, 19, 18, 18), {
				icon: "add",
				color: "action"
			}),
			label("typeCreateWorkflowHint", rect(createPad + 26, inlineCreate ? 16 : 12, Math.max(0, width - createPad * 2 - 26 - (inlineCreate ? createBtnW + 12 : 0)), 24), tr("New workflow"), { weight: 600 }),
			button("adminCreateTypeWorkflow", inlineCreate ? rect(width - createPad - createBtnW, 10, createBtnW, 36) : rect(createPad, 44, createBtnW, 38), tr("Create workflow"), "add", {
				type: "workflow",
				identity: ""
			}, !model.busy && !model.uncertain && !model.namingLocked && model.canWrite)
		];
		nodes.push(node("Box", "typeCreateWorkflowCard", rect(0, y, width, createCardH), {
			background: "surfaceContainer",
			border: "outlineVariant",
			radius: 10,
			children: createChildren
		}));
		y += createCardH + 10;
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
	const marked = (model.document.removedColumns || []).indexOf(record.name) >= 0, reason = removalReasons[(model.metadata.columnRemovalBlocks || {})[record.name]], narrow = width < 420, cardPad = width < 380 ? 10 : 14, cardH = narrow ? 180 : 128, info = record.info || {}, rawType = String(info.data_type || "").toLowerCase().split("(")[0].trim(), typeIndex = {
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
	}[rawType], fieldTypeDef = fieldTypes[rawType.indexOf("timestamp") === 0 ? 5 : typeIndex], typeSummary = fieldTypeDef ? tr(fieldTypeDef.label) + " · " + (info.data_type || "") : info.data_type || "—", constraints = [
		info.character_maximum_length ? tr("Up to {count} characters", { count: info.character_maximum_length }) : "",
		info.is_nullable === "NO" || info.is_nullable === false ? tr("Cannot be empty in the database") : "",
		fieldTypeDef ? tr("Example value: {value}", { value: tr(fieldTypeDef.example) }) : ""
	].filter(Boolean).join("  ·  "), fullText = marked ? tr("Marked for deletion. The column and its data will be deleted when you save.") : fieldDescription(info, language) + (reason ? "\n" + tr(reason) : ""), btnW = 152, showTypeBadge = !narrow && width >= 540, badgeText = String(info.data_type || "text"), badgeW = showTypeBadge ? Math.min(Math.max(84, badgeText.length * 7 + 30), 170) : 0, nameAvailW = Math.max(60, width - cardPad * 2 - 26 - (narrow ? 0 : 162) - (showTypeBadge ? badgeW + 10 : 0)), fieldIcon = marked ? "delete" : reason ? "lock" : rawType.indexOf("timestamp") === 0 ? "calendar" : typeIndex === 2 || typeIndex === 3 ? "tag" : typeIndex === 4 ? "check" : "description", cardChildren = [
		node("Icon", "typeExistingIcon_" + record.name, rect(cardPad, 13, 18, 18), {
			icon: fieldIcon,
			color: marked ? "error" : reason ? "muted" : "action"
		}),
		label("typeExistingName_" + record.name, rect(cardPad + 26, 9, nameAvailW, 24), record.name, {
			weight: 600,
			monospace: true,
			strike: marked
		}),
		node("Box", "typeExistingDivider_" + record.name, rect(cardPad, 43, Math.max(1, width - cardPad * 2), 1), { background: "outlineVariant" })
	];
	if (showTypeBadge) {
		const bx = width - cardPad - btnW - 10 - badgeW;
		cardChildren.push(node("Box", "typeExistingBadge_" + record.name, rect(bx, 9, badgeW, 26), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			radius: 13,
			children: [node("Icon", "typeExistingBadgeIcon_" + record.name, rect(9, 6, 14, 14), {
				icon: "code",
				color: "action"
			}), label("typeExistingBadgeText_" + record.name, rect(26, 3, Math.max(0, badgeW - 34), 20), badgeText, {
				fontRole: "secondary",
				weight: 600,
				monospace: true
			})]
		}));
	}
	if (marked) cardChildren.push(node("Icon", "typeExistingMarkedIcon_" + record.name, rect(cardPad, 56, 16, 16), {
		icon: "warning",
		color: "error"
	}), label("typeExistingMarkedText_" + record.name, rect(cardPad + 24, 52, Math.max(0, width - cardPad * 2 - 24), 56), tr("Marked for deletion. The column and its data will be deleted when you save."), {
		wrap: true,
		color: "error",
		weight: 600
	}));
	else {
		cardChildren.push(node("Icon", "typeExistingTypeRowIcon_" + record.name, rect(cardPad, 54, 15, 15), {
			icon: "storage",
			color: "action"
		}), label("typeExistingTypeRowText_" + record.name, rect(cardPad + 22, 50, Math.max(0, width - cardPad * 2 - 22), 22), typeSummary + (constraints ? "  ·  " + constraints : ""), Object.assign({ wrap: true }, muted)));
		if (reason) cardChildren.push(node("Icon", "typeExistingReasonIcon_" + record.name, rect(cardPad, 82, 15, 15), {
			icon: "lock",
			color: "warning"
		}), label("typeExistingReasonText_" + record.name, rect(cardPad + 22, 78, Math.max(0, width - cardPad * 2 - 22), 40), tr(reason), Object.assign({ wrap: true }, muted)));
	}
	cardChildren.push(button("adminDeleteColumn_" + record.name, narrow ? rect(cardPad, cardH - 46, Math.max(1, width - cardPad * 2), 36) : rect(width - cardPad - btnW, 6, btnW, 32), tr(marked ? "Undo deletion" : "Delete field"), marked ? "undo" : "delete", {
		type: "removeField",
		name: record.name
	}, policy(model).editable && (!reason || marked), { destructive: !marked && !reason }));
	return { nodes: [node("Box", "adminExistingField_" + record.name, rect(0, 0, width, cardH), {
		text: fullText,
		background: "surfaceContainer",
		border: "outlineVariant",
		radius: 10,
		children: cardChildren
	})] };
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
		catalogVisible: true,
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
		case "catalogVisible":
			next.catalogVisible = next.catalogVisible === false;
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
		storageKey() {
			return "tactic_stream.search_types." + (this.project || "admin");
		},
		saveViewState() {
			if (this.creationOnly || !this.identity) return;
			try {
				sessionStorage.setItem(this.storageKey(), JSON.stringify({
					identity: this.identity,
					page: this.ui.page
				}));
			} catch {}
		},
		readViewState() {
			if (this.creationOnly) return null;
			try {
				return JSON.parse(sessionStorage.getItem(this.storageKey()) || "null");
			} catch {
				return null;
			}
		},
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
					case "page":
						this.saveViewState();
						break;
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
			if (this.busy || this.previewValidating) return false;
			if (this.documentDirty || this.uncertain) {
				this.error = "";
				this.dispatch({ type: "discard" });
				return false;
			}
			return true;
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
			const saved = !this.identity ? this.readViewState() : null;
			const targetIdentity = this.identity || saved?.identity || "";
			const targetPage = this.identity ? this.ui.page : saved?.page || "summary";
			try {
				const result = await this.call("load", { identity: targetIdentity });
				if (id !== this.request) return;
				this.catalog = result.catalog;
				this.canWrite = result.canWrite !== false;
				const selected = this.catalog.find((row) => row.identity === targetIdentity) || this.visibleTypes[0];
				if (selected) {
					const loaded = result.identity === selected.identity ? result : await this.call("load", { identity: selected.identity });
					if (id !== this.request) return;
					this.accept(loaded);
					this.page = [
						"summary",
						"workflow",
						"naming",
						"details",
						"fields"
					].includes(targetPage) ? targetPage : "summary";
					this.saveViewState();
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
					this.saveViewState();
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
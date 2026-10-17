import { F as resolveComponent, K as withDirectives, M as openBlock, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, nt as normalizeStyle, s as vShow } from "./vue.js";
import { D as t, O as appearance, tt as _plugin_vue_export_helper_default } from "./index.js";
import { c as button, d as node, f as rect, l as label, n as _sfc_main$1, s as translate, t as observeFrameSizes, u as muted } from "./resize.js";
import { g as columnsEditor } from "./clipboard.js";
import { J as changeDefinition, X as displayWidgets, Y as definitionWizard, x as sections } from "./App.js";
import { a as tabs, n as notices, o as toolbar, r as policy, t as documentEvent } from "./admin.document.js";
//#region ../src/tactic_stream/shared_ui/features/administration/columns/columns.state.mjs
var initial = () => ({
	query: "",
	searchType: "",
	mode: "simple",
	path: "",
	editing: false,
	catalogWidth: 350,
	columnWidth: 250,
	columnHeight: 170,
	confirmation: "",
	text: {}
});
var pending = (ui) => Object.keys(ui.text).length > 0;
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
	if (command.type === "change" && command.field === "move") next.path = (model.elements.find((row) => row.name === command.name) || model.element).path;
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
		case "column":
			if (model.elements.some((row) => row.path === event.path)) commands.push({
				type: "column",
				path: event.path
			});
			break;
		case "text":
			if (allow.editable) {
				next.text = Object.assign({}, ui.text);
				if (String(event.value) === String(model.element[event.field])) delete next.text[event.field];
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
			if (allow.editable && !pending(ui) && (event.value === -1 || event.value === 1) && model.elements[index + event.value]) commands.push({
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
		default: throw Error("Unsupported Columns event: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/columns/columns.ui.mjs
var list = (id, bounds, source, rowHeight) => node("List", id, bounds, {
	source,
	rowHeight,
	keyField: source === "definitions" ? "identity" : "path",
	fields: [],
	scrollbarId: id + "ScrollBar"
});
function records(model, ui) {
	const query = ui.query.trim().toLowerCase();
	return model.records.filter((row) => (!ui.searchType || row.searchType === ui.searchType) && (!query || [
		row.view,
		row.searchType,
		row.code,
		row.login,
		row.category,
		row.widgetType
	].join(" ").toLowerCase().indexOf(query) >= 0));
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
	const split = width >= 850, left = split ? Math.min(ui.catalogWidth, width * .44) : width, h = height - y;
	const edit = policy(model).editable && !ui.confirmation, navigate = !model.busy && !model.dirty && !model.uncertain && !ui.confirmation;
	if (split || !ui.editing) {
		const children = [
			label("definitionCatalogHeading", rect(12, 8, left - 70, 28), tr("Saved definitions"), {
				fontRole: "section",
				weight: 600
			}),
			label("definitionCatalogCount", rect(left - 58, 8, 46, 28), String(records(model, ui).length), muted),
			node("Choice", "definitionCatalogSearchTypeFilter", rect(12, 44, left - 24, 38), {
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
			}),
			node("Field", "definitionCatalogFilter", rect(12, 90, left - 24, 38), {
				text: ui.query,
				label: tr("Filter saved views"),
				placeholder: tr("Filter saved views"),
				enabled: navigate,
				action: { type: "query" }
			}),
			list("definitionCatalogList", rect(12, 136, left - 24, h - 148), "definitions", 64)
		];
		if (!records(model, ui).length) children.push(label("definitionCatalogEmpty", rect(24, 148, left - 48, 100), tr(model.busy ? "Working on the server…" : "No saved definitions match the filter"), {
			wrap: true,
			color: "secondaryText"
		}));
		nodes.push(node("Box", "definitionCatalogPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
	}
	if (split) nodes.push(node("Splitter", "columnsCatalogSplitHandle", rect(left, y, 10, h), {
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
		const selected = model.selected;
		children.push(label("definitionViewTitle", rect(12, y, inner, 26), selected.view, {
			fontRole: "section",
			weight: 600
		}), label("definitionViewType", rect(12, y + 30, inner, 24), selected.searchType + (selected.login ? " · " + selected.login : ""), muted));
		y += 62;
		children.push(tabs("definitionCatalogMode", [{
			value: "simple",
			label: tr("Wizard"),
			icon: "table"
		}, {
			value: "xml",
			label: "XML",
			icon: "code"
		}], ui.mode, rect(12, y, width - 24, 38), !model.busy, "mode"));
		y += 46;
		if (ui.mode === "xml") children.push(node("Area", "definitionCatalogXml", rect(12, y, width - 24, bounds.height - y - 42), {
			text: model.xml,
			label: tr("Definition XML"),
			monospace: true,
			enabled: edit,
			action: { type: "xml" }
		}));
		else if (model.wizard.supported && model.elements.length) {
			children.push(label("definitionColumnsLabel", rect(12, y, (width - 24) / 2, 22), tr("Columns"), muted), label("definitionLayoutLabel", rect(width / 2, y, Math.max(1, width / 2 - 100), 22), model.wizard.layout ? tr("Layout: ") + model.wizard.layout : model.wizard.view, muted));
			const selectedIndex = model.elements.findIndex((row) => row.path === model.element.path);
			for (const [offset, title, icon, x] of [[
				-1,
				"Move up",
				"arrow-up",
				width - 88
			], [
				1,
				"Move down",
				"arrow-down",
				width - 50
			]]) children.push(node("Button", offset < 0 ? "definitionColumnUp" : "definitionColumnDown", rect(x, y - 4, 34, 28), {
				text: tr(title),
				icon,
				iconOnly: true,
				enabled: edit && !pending(ui) && !!model.elements[selectedIndex + offset],
				action: {
					type: "move",
					value: offset
				}
			}));
			y += 30;
			const stacked = width < 720, columnWidth = stacked ? width - 24 : Math.min(ui.columnWidth, width * .4), columnHeight = stacked ? Math.min(ui.columnHeight, (bounds.height - y - 42) * .42) : bounds.height - y - 42;
			children.push(list("definitionCatalogElementList", rect(12, y, columnWidth, columnHeight), "columns", 60));
			children.push(node("Splitter", "definitionColumnsSplitHandle", rect(stacked ? 12 : 12 + columnWidth, stacked ? y + columnHeight : y, stacked ? columnWidth : 10, stacked ? 10 : columnHeight), {
				horizontal: stacked,
				text: tr(stacked ? "Columns list height" : "Columns list width"),
				value: stacked ? columnHeight : columnWidth,
				min: stacked ? 100 : 180,
				max: stacked ? Math.max(100, bounds.height * .42) : width * .4,
				action: {
					type: "split",
					field: stacked ? "columnHeight" : "columnWidth"
				}
			}));
			const formX = stacked ? 12 : columnWidth + 22, formY = stacked ? y + columnHeight + 10 : y, formWidth = width - formX - 28;
			const element = model.element, text = (key) => Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(element[key] || "");
			const fields = [
				{
					kind: "Heading",
					id: "definitionColumnHeading",
					title: "Column",
					description: "Edit one native TACTIC element at a time. Custom options remain unchanged in XML."
				},
				{
					kind: "Label",
					id: "definitionCatalogName",
					title: "Field name",
					description: "Native field identifier.",
					props: { text: element.name || "" }
				},
				{
					id: "definitionCatalogTitle",
					title: "Title",
					description: "The column heading shown to users.",
					field: "title",
					props: {
						text: text("title"),
						action: {
							type: "text",
							field: "title"
						},
						commitAction: { type: "commit" }
					}
				},
				{
					kind: "Switch",
					id: "definitionCatalogVisible",
					title: "Show in table",
					description: "Keep the column in this saved view.",
					field: "visible",
					props: { checked: element.visible }
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
					kind: "Choice",
					id: "definitionCatalogWidget",
					title: "Display widget",
					description: "Choose a supported TACTIC table widget.",
					field: "widget",
					options: model.widgetOptions.map((row) => ({
						value: row.value,
						label: tr(row.label)
					})),
					props: { value: element.widget || "" }
				}
			];
			const body = sections(fields, formWidth, language, edit);
			children.push(node("Scroll", "definitionCatalogForm", rect(formX, formY, width - formX - 12, Math.max(1, bounds.height - formY - 42)), {
				contentHeight: body.height,
				resetKey: ui.path,
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
	return { nodes: [node("Action", definition ? "definitionRow_" + record.identity : "definitionColumn_" + record.path, rect(0, 0, width, definition ? 60 : 56), {
		text: definition ? record.view + " · " + record.searchType + (record.login ? " · " + record.login : "") : record.name,
		selected,
		normalColor: "surfaceContainerHigh",
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
			node("Icon", "definitionRowIcon_" + (record.identity || record.path), rect(10, 18, 18, 18), {
				icon: definition ? "table" : record.visible ? "eye" : "eye-off",
				color: "action"
			}),
			label("definitionRowTitle_" + (record.identity || record.path), rect(38, 6, width - 48, 24), definition ? record.view : record.title, { weight: 600 }),
			label("definitionRowDetail_" + (record.identity || record.path), rect(38, 30, width - 48, 20), definition ? record.searchType + (record.login ? " · " + record.login : "") : record.name, muted)
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
				return definitionWizard(this.xml);
			} catch (error) {
				return {
					supported: false,
					elements: [],
					error: error.message
				};
			}
		},
		element() {
			return this.wizard.elements.find((row) => row.path === this.ui.path) || this.wizard.elements[0];
		},
		widgets() {
			const value = this.element?.widget;
			return value && !displayWidgets.some((row) => row.value === value) ? [{
				value,
				label: value,
				translate: false
			}, ...displayWidgets] : displayWidgets;
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
			for (const [field, value] of Object.entries(this.ui.text)) {
				this.change(field, value);
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
			const matches = this.records.filter((row) => row.view === this.initialFocus.view);
			this.select((matches.find((row) => row.code === this.initialFocus.code) || matches.find((row) => !row.login) || matches[0])?.identity || "", true);
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.dirty || this.busy || this.uncertain) {
				this.error = "Save or discard definition changes before leaving.";
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
				this.xml = changeDefinition(this.xml, this.element.path, field, value);
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
				if (first && this.initialFocus?.project === this.project && this.initialFocus?.searchType) {
					this.ui = {
						...this.ui,
						searchType: this.initialFocus.searchType,
						editing: true
					};
					const matches = this.records.filter((row) => row.view === this.initialFocus.view);
					this.select((matches.find((row) => row.code === this.initialFocus.code) || matches.find((row) => !row.login) || matches[0])?.identity || "", true);
				} else this.select(this.records.find((row) => row.identity === previous)?.identity || this.records[0]?.identity || "", true);
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
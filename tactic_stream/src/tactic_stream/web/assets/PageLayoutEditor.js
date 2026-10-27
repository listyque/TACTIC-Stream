import { I as resolveComponent, N as openBlock, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, q as withDirectives, rt as normalizeStyle, s as vShow } from "./vue.js";
import { O as randomUuid, j as appearance, ot as _plugin_vue_export_helper_default } from "./index.js";
import { Gt as button, Jt as node, Kt as label, Yt as rect, ct as rpc, i as _sfc_main$1, qt as muted, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { n as sections } from "./sections.ui.js";
import { a as projectPath } from "./links.js";
import { $ as notices, A as _sfc_main$2, Q as documentEvent, U as spacingField, rt as toolbar$1, tt as sectionSelector } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs
var kinds = [
	"row",
	"column",
	"text",
	"markdown",
	"metric",
	"table",
	"items",
	"details",
	"link"
];
var copy = (value) => JSON.parse(JSON.stringify(value));
function path(value) {
	if (value === "") return [];
	if (!/^\d+(\.\d+)*$/.test(value)) throw Error("Select a page block");
	return value.split(".").map(Number);
}
function siblings(document, indices) {
	let rows = document.blocks;
	for (const index of indices.slice(0, -1)) {
		if (!rows[index]) throw Error("The selected element no longer exists");
		rows = rows[index].children || [];
	}
	return rows;
}
function block(document, key) {
	const p = path(key);
	if (!p.length) return null;
	const item = siblings(document, p)[p[p.length - 1]];
	if (!item) throw Error("The selected element no longer exists");
	return item;
}
function layers(document, prefix = []) {
	const rows = prefix.length ? block(document, prefix.join(".")).children || [] : document.blocks || [];
	let result = [];
	rows.forEach((item, index) => {
		const p = prefix.concat(index);
		result = result.concat([{
			key: p.join("."),
			depth: prefix.length,
			label: item.title || item.kind,
			kind: item.kind
		}].concat(layers(document, p)));
	});
	return result;
}
function change(document, key, field, value) {
	const result = copy(document), item = key === "" ? result : block(result, key);
	if (!item) throw Error("The selected element no longer exists");
	const limits = {
		width: [40, 2400],
		height: [24, 1600],
		weight: [1, 12],
		gap: [0, 128]
	};
	if (limits[field]) {
		if (value === "" && ["width", "height"].includes(field)) value = null;
		else {
			const range = limits[field];
			if (!/^\d+$/.test(String(value)) || Number(value) < range[0] || Number(value) > range[1]) throw Error("Enter a whole number within the allowed range");
			value = Number(value);
		}
	} else if (![
		"title",
		"text",
		"search_type",
		"view",
		"href",
		"field"
	].includes(field)) throw Error("Unsupported page property");
	item[field] = value;
	return result;
}
function spacing(document, key, field, side, value) {
	if (!["padding", "margin"].includes(field) || !Number.isInteger(side) || side < 0 || side > 3 || !/^\d+$/.test(String(value)) || Number(value) > 256) throw Error("Enter spacing from 0 to 256");
	const result = copy(document), item = block(result, key);
	if (!item) throw Error("Select a page block");
	item[field] = (item[field] || [
		0,
		0,
		0,
		0
	]).slice();
	item[field][side] = Number(value);
	return result;
}
function add(document, key, kind, searchType) {
	if (!kinds.includes(kind)) throw Error("Unsupported page widget");
	const result = copy(document), selected = key ? block(result, key) : null;
	const parent = selected && [
		"row",
		"column",
		"details"
	].includes(selected.kind) ? path(key) : key ? path(key).slice(0, -1) : [];
	const owner = parent.length ? block(result, parent.join(".")) : null;
	const rows = owner ? owner.children || (owner.children = []) : result.blocks;
	if (rows.length >= 32 || layers(result).length >= 128) throw Error("Dashboard exceeds 128 bricks");
	if (parent.length > 6) throw Error("Dashboard nesting exceeds six levels");
	const item = {
		kind,
		title: kind
	};
	if ([
		"row",
		"column",
		"details"
	].includes(kind)) {
		item.children = [];
		item.height = 180;
	}
	if ([
		"items",
		"table",
		"metric"
	].includes(kind)) Object.assign(item, {
		search_type: searchType || "",
		view: kind === "items" ? "continuous_example" : "table"
	});
	if (["text", "markdown"].includes(kind)) item.text = kind;
	rows.push(item);
	return {
		document: result,
		key: parent.concat(rows.length - 1).join(".")
	};
}
function remove(document, key) {
	const result = copy(document), p = path(key);
	if (!p.length) throw Error("Select a page block");
	siblings(result, p).splice(p[p.length - 1], 1);
	return result;
}
function geometry(document, change, boxes) {
	const result = copy(document), p = path(change.key), item = block(result, change.key);
	if (!item) throw Error("The selected element no longer exists");
	if (change.handle !== "move") {
		const margin = item.margin || [
			0,
			0,
			0,
			0
		], padding = item.padding || [
			0,
			0,
			0,
			0
		];
		if (change.handle.includes("e")) item.width = Math.max(40, Math.min(2400, Math.round(change.after.width + margin[1] + margin[3])));
		if (change.handle.includes("s")) {
			const overhead = ["items", "table"].includes(item.kind) ? 32 : 0;
			const old = item.height === void 0 || item.height === null ? change.before.height - overhead - padding[0] - padding[2] : item.height;
			item.height = Math.max(24, Math.min(1600, Math.round(old + change.after.height - change.before.height)));
		}
		return {
			document: result,
			key: change.key
		};
	}
	if (change.keyboard) {
		const rows = siblings(result, p), index = p[p.length - 1];
		const delta = change.after.y - change.before.y || change.after.x - change.before.x;
		const target = Math.max(0, Math.min(rows.length - 1, index + delta));
		rows.splice(index, 1);
		rows.splice(target, 0, item);
		return {
			document: result,
			key: p.slice(0, -1).concat(target).join(".")
		};
	}
	const x = change.after.x + change.after.width / 2, y = change.after.y + change.after.height / 2;
	const hit = boxes.filter((b) => b.key !== change.key && !b.key.startsWith(change.key + ".") && x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height).sort((a, b) => b.depth - a.depth)[0];
	let parent = hit ? path(hit.key) : [];
	if (hit && ![
		"row",
		"column",
		"details"
	].includes(block(result, hit.key)?.kind)) parent = parent.slice(0, -1);
	if (parent.length > 5) throw Error("Dashboard nesting exceeds six levels");
	const old = siblings(result, p), index = p[p.length - 1];
	const owner = parent.length ? block(result, parent.join(".")) : null;
	const target = owner ? owner.children || (owner.children = []) : result.blocks;
	const depth = (rows) => rows.reduce((value, row) => Math.max(value, 1 + depth(row.children || [])), 0);
	if (parent.length + depth([item]) > 7) throw Error("Dashboard nesting exceeds six levels");
	if (target !== old && target.length >= 32) throw Error("Dashboard supports at most 32 siblings");
	const axis = (parent.length ? block(result, parent.join(".")).kind : "column") === "row" ? "x" : "y", position = axis === "x" ? x : y;
	const before = boxes.filter((b) => path(b.key).length === parent.length + 1 && path(b.key).slice(0, -1).join(".") === parent.join(".") && b.key !== change.key).sort((a, b) => a[axis] - b[axis]).find((b) => position < b[axis] + b[axis === "x" ? "width" : "height"] / 2);
	const targetPath = before ? path(before.key) : [];
	let insertion = before ? targetPath[targetPath.length - 1] : target.length;
	if (old === target && index < insertion) insertion--;
	old.splice(index, 1);
	target.splice(insertion, 0, item);
	function location(rows, prefix) {
		if (rows === target) return prefix;
		for (let i = 0; i < rows.length; i++) {
			const found = location(rows[i].children || [], prefix.concat(i));
			if (found) return found;
		}
		return null;
	}
	return {
		document: result,
		key: location(result.blocks, []).concat(insertion).join(".")
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs
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
	const title = record.label === record.kind ? translate(record.kind[0].toUpperCase() + record.kind.slice(1), language) : record.label;
	return { nodes: [node("Action", "pageBlock_" + record.key, rect(0, 0, list.width - 16, 38), {
		text: title,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		selected: ui.selected === key,
		children: [label("pageBlockLabel_" + record.key, rect(8 + record.depth * 12, 0, list.width - 32 - record.depth * 12, 38), title)],
		action: {
			type: "select",
			key
		}
	})] };
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
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
				link: "Link"
			}[value])
		}))),
		enabled: canEdit && !ui.preview,
		action: { type: "add" }
	}));
	if (width >= 700 && model.layers.some((row) => row.kind === "items")) nodes.push(label("pageSampleHint", rect(232, y, Math.max(0, width - 244 - modeWidth), 38), tr("Items preview shows up to three records."), Object.assign({}, muted, {
		fontRole: "caption",
		wrap: true
	})));
	y += 50;
	nodes.push(button("pagePreviewMode", rect(width - modeWidth, y - 50, modeWidth, 38), tr(ui.preview ? "Back to editing" : "Clean preview"), ui.preview ? "edit" : "visibility", { type: "preview" }, !model.busy && !ui.creating && !model.pendingText, { iconOnly: narrow }));
	if (width >= 500) {
		nodes.push(label("pageSelectionHint", rect(0, y, width, 24), tr(ui.preview ? "Read-only draft preview. Nothing is saved." : "Click to select. Alt-click for underlying layers."), Object.assign({}, muted, { fontRole: "caption" })));
		y += 32;
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
		const item = ui.selected ? block(model.document, ui.selected) : null, fields = [];
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
				enabled: canEdit
			};
			fields.push({
				id: "pageProperty_" + name,
				title,
				kind,
				props
			});
		}
		field("title", "Title", item ? item.title : model.document.title, !item);
		if (item) {
			if (["text", "markdown"].includes(item.kind)) field("text", "Text", item.text || "");
			if ([
				"items",
				"table",
				"metric"
			].includes(item.kind)) fields.push({
				kind: "Choice",
				id: "pageProperty_search_type",
				title: "Search Type",
				options: model.searchTypes || [],
				props: {
					value: item.search_type,
					enabled: canEdit,
					action: {
						type: "change",
						field: "search_type"
					}
				}
			});
			if (["items", "table"].includes(item.kind)) field("view", "View", item.view || "table");
			if (item.kind === "link") field("href", "Link URL", item.href || "");
			field("width", "Width", item.width);
			field("height", "Height", item.height);
			field("weight", "Flexible width", item.weight || 1);
			if ([
				"row",
				"column",
				"details"
			].includes(item.kind)) field("gap", "Gap", item.gap ?? 8);
			for (const name of ["padding", "margin"]) fields.push(spacingField("page" + name, tr(name === "padding" ? "Padding" : "Margin"), item[name] || [
				0,
				0,
				0,
				0
			], ui.text, {
				type: "spacing",
				field: name
			}, language, canEdit, right - 72));
			if (item.kind === "items") fields.push({
				kind: "Button",
				id: "pageEditCard",
				title: "Edit card layout",
				props: {
					icon: "edit",
					enabled: !model.busy,
					action: { type: "card" }
				}
			});
			fields.push({
				kind: "Button",
				id: "pageRemoveBlock",
				title: "Remove widget",
				props: {
					icon: "delete",
					enabled: canEdit,
					action: { type: "remove" }
				}
			});
		}
		const body = sections(fields, right - 24, language, canEdit);
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
	if (ui.preview || !narrow || ui.panel === "canvas") nodes.push(node("Box", "pageCanvasPanel", rect(canvasX, y, canvasWidth, h), {
		background: "workspace",
		border: "outlineVariant",
		children: [node("View", "pageCanvas", rect(12, 12, canvasWidth - 24, h - 24), { view: "pagePreview" })]
	}));
	return { nodes };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs
function initial() {
	return {
		selected: "",
		panel: "canvas",
		preview: false,
		text: {},
		confirmation: "",
		pendingPage: "",
		creating: false,
		newName: "",
		newTitle: "",
		error: ""
	};
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [];
	if (event.type === "confirm" && ["page", "remove"].includes(ui.confirmation) && (model.busy || model.uncertain || !model.canWrite)) return {
		ui: next,
		commands
	};
	function replace(document) {
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
	if (document) return document;
	if (model.busy || ui.confirmation) return {
		ui: next,
		commands
	};
	if ((!model.canWrite || model.uncertain) && ![
		"select",
		"panel",
		"preview"
	].includes(event.type)) return {
		ui: next,
		commands
	};
	try {
		if (Object.keys(ui.text).length && [
			"select",
			"geometry",
			"add",
			"remove",
			"change"
		].includes(event.type)) throw Error("Apply or discard the pending text before continuing");
		switch (event.type) {
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
				if (event.key) block(model.document, event.key);
				next.selected = event.key;
				next.text = {};
				break;
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
				break;
			case "buffer":
				next.text = Object.assign({}, ui.text, { [event.key]: event.value });
				break;
			case "commit":
				if (!Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
				replace(change(model.document, event.root ? "" : ui.selected, event.field, ui.text[event.key]));
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
				break;
			case "change":
				replace(change(model.document, event.root ? "" : ui.selected, event.field, event.value));
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
				break;
			}
			case "remove":
				if (ui.selected) next.confirmation = "remove";
				break;
			case "geometry": {
				const value = geometry(model.document, event.value, event.boxes);
				replace(value.document);
				next.selected = value.key;
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
			checkedDocument: "",
			error: "",
			message: "",
			busy: false,
			uncertain: false,
			canWrite: false,
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
				searchTypes: (this.searchTypes || []).map((row) => ({
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
		this.observer?.disconnect();
		this.generation++;
		this.previewSerial++;
		clearTimeout(this.previewTimer);
	},
	watch: {
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
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
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
		"aria-busy": $data.busy
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
	])], 512)], 8, _hoisted_1);
}
var PageLayoutEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { PageLayoutEditor_default as default };

//# sourceMappingURL=PageLayoutEditor.js.map
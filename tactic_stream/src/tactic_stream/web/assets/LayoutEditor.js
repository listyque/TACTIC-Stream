const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/ConfiguredView.js","assets/ObjectFieldFrame.js","assets/vue.js","assets/AppButton.js","assets/locales.js","assets/icons.js","assets/AppButton.css","assets/FrameView.js","assets/FrameView.css","assets/ObjectFieldFrame.css","assets/index.js","assets/index.css","assets/textMetrics.js","assets/sections.ui.js","assets/RecordForm.js","assets/previewImage.js","assets/RecordForm.css","assets/admin.document.js","assets/file_values.js","assets/files.js","assets/files2.js","assets/admin.css","assets/CodeBlock.js","assets/confirmation.ui.js","assets/AppDialog.js","assets/VirtualCollection.js","assets/VirtualCollection.css","assets/Timesheet.js","assets/Timesheet.css","assets/ContentLoadingOverlay.js","assets/ContentLoadingOverlay.css","assets/RelatedObjects.js","assets/RelatedObjects.css","assets/ConfiguredView.css"])))=>i.map(i=>d[i]);
import { I as resolveComponent, N as openBlock, _ as createCommentVNode, c as vShow, g as createBlock, h as createBaseVNode, it as toDisplayString, m as computed, nt as normalizeClass, p as Teleport, q as withDirectives, rt as normalizeStyle, tt as unref, v as createElementBlock, w as inject, x as createVNode } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { $ as widgetConfiguration, M as rpc, a as __vitePreload, j as resultItems, zt as asyncComponent } from "./index.js";
import { K as button, T as translate, U as observeFrameSizes, X as node, Y as muted, Z as rect, q as label, t as _sfc_main$2 } from "./FrameView.js";
import { n as sections } from "./sections.ui.js";
import { i as sectionSelector, k as workspaceAddress, n as notices, o as toolbar$1, r as policy, t as documentEvent } from "./admin.document.js";
import { At as template, Ct as visible, Dt as edit, Et as describe$1, Mt as widgets, Ot as roles, R as itemScene, St as supports, Tt as binding, j as _sfc_main$3, jt as variants, kt as serialize, wt as actions, xt as describe$2, z as spacingField } from "./RelatedObjects.js";
//#region src/features/interface/layoutXml.js
function layoutTree(source) {
	if (!source.trim()) throw Error("Select a SObject layout configuration");
	if (/<!DOCTYPE|<!ENTITY/i.test(source)) throw Error("Document types and XML entities are not supported");
	const document = new DOMParser().parseFromString(source, "application/xml");
	if (document.querySelector("parsererror") || document.documentElement.tagName !== "config") throw Error("Invalid configuration XML");
	function convert(node) {
		if (node.nodeType === 1) return {
			type: 1,
			name: node.tagName,
			attributes: [...node.attributes].map((attr) => [attr.name, attr.value]),
			children: [...node.childNodes].map(convert)
		};
		if (node.nodeType === 9) return {
			type: 9,
			children: [...node.childNodes].map(convert)
		};
		if ([
			3,
			4,
			7,
			8
		].includes(node.nodeType)) return {
			type: node.nodeType,
			...node.nodeType === 7 ? { name: node.target } : {},
			text: node.data
		};
		throw Error("Unsupported XML node");
	}
	return convert(document);
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/item.geometry.mjs
function apply(model, change) {
	const item = model.layout.elements.find((row) => row.name === change.key);
	if (!item) throw Error("The selected element no longer exists");
	const parent = model.layout.elements.find((row) => row.name === item.parent);
	if ((parent ? parent.flow : model.layout.flow) !== "grid") throw Error("Choose Grid in the parent container to position elements");
	const columns = parent ? parent.columns : model.layout.columns;
	const gap = (parent ? parent.gap : model.layout.gap) ?? 6;
	const margin = item.margin || [
		0,
		0,
		0,
		0
	], pitch = (change.before.width + margin[1] + margin[3] + gap) / item.span;
	const grid = change.before.grid;
	const nearest = (values, target) => values.reduce((best, value, index) => Math.abs(value - target) < Math.abs(values[best] - target) ? index : best, 0);
	const values = {};
	if (change.handle === "move") {
		values.column = Math.max(1, Math.min(columns - item.span + 1, item.column + Math.round((change.after.x - change.before.x) / pitch)));
		values.row = Math.max(1, Math.min(100, item.row + Math.round((change.after.y - change.before.y) / ((change.before.height + gap) / item.rows))));
		if (grid) {
			const start = grid.columns[item.column - 1] + change.after.x - change.before.x;
			values.column = Math.min(columns - item.span + 1, nearest(grid.columns, start) + 1);
			const y = grid.rows[item.row - 1] + change.after.y - change.before.y;
			if (y <= grid.rows[grid.rows.length - 1]) values.row = nearest(grid.rows, y) + 1;
		}
	} else {
		if (change.handle.includes("e")) values.span = Math.max(1, Math.min(columns - item.column + 1, Math.round((change.after.width + gap) / pitch)));
		if (grid && change.handle.includes("e")) values.span = nearest(grid.ends.slice(item.column - 1), grid.columns[item.column - 1] + change.after.width + margin[1] + margin[3]) + 1;
		if (change.handle.includes("s")) {
			values.align = "start";
			values.height = Math.max(1, Math.min(1200, Math.round(item.height + change.after.height - change.before.height)));
		}
	}
	if (change.keyboard && change.handle === "move") {
		values.column = Math.max(1, Math.min(columns - item.span + 1, item.column + change.after.x - change.before.x));
		values.row = Math.max(1, Math.min(100, item.row + change.after.y - change.before.y));
	}
	let tree = model.tree;
	for (const field of Object.keys(values)) tree = edit(tree, model.view, item.name, field, values[field]);
	return serialize(tree, true);
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs
function initial() {
	return {
		page: "design",
		panel: "elements",
		selected: "",
		context: "",
		catalogVisible: true,
		propertiesVisible: true,
		catalogWidth: 220,
		propertiesWidth: 330,
		newName: "",
		template: "blank",
		creating: false,
		pendingContext: null,
		text: {},
		confirmation: "",
		checking: false,
		navigation: [],
		navigationScope: "",
		navigationPending: null,
		error: ""
	};
}
function pending(ui) {
	return Object.keys(ui.text).length > 0;
}
function reference(model, ui) {
	const item = model.layout.elements.find((row) => row.name === ui.selected);
	if (item?.kind !== "view") return null;
	const view = item.options.view || "", searchType = item.search_type || model.searchType;
	return /^[A-Za-z_][\w.@-]{0,127}$/.test(view) && model.searchTypes.some((row) => row.value === searchType) && (searchType !== model.searchType || view !== model.view) ? {
		searchType,
		view
	} : null;
}
function navigationParent(ui) {
	const parent = ui.navigation[ui.navigation.length - 1];
	return parent ? {
		kind: "item",
		name: parent.view,
		title: parent.view
	} : null;
}
function synchronize(ui, model) {
	if (ui.navigation[0]?.project && ui.navigation[0].project !== model.project) return Object.assign({}, ui, {
		navigation: [],
		navigationScope: "",
		navigationPending: null
	});
	if (!model.ready) return ui;
	const key = [
		model.project,
		model.searchType,
		model.view,
		model.source
	].join(":"), next = Object.assign({}, ui);
	if (next.context !== key) {
		next.context = key;
		next.selected = (model.layout.elements[0] || {}).name || "";
		next.text = {};
		next.error = "";
		next.confirmation = "";
	} else if (!model.layoutError && next.selected && !model.layout.elements.some((row) => row.name === next.selected)) next.selected = (model.layout.elements[0] || {}).name || "";
	const scope = [
		model.project,
		model.searchType,
		model.view
	].join(":");
	if (ui.navigationPending?.searchType === model.searchType && ui.navigationPending.view === model.view) {
		const restore = ui.navigationPending.restore;
		if (restore) {
			for (const field of [
				"page",
				"panel",
				"selected",
				"catalogWidth",
				"propertiesWidth"
			]) next[field] = restore[field];
			if (!model.layout.elements.some((row) => row.name === next.selected)) next.selected = model.layout.elements[0]?.name || "";
		}
		next.navigationPending = null;
		next.navigationScope = scope;
	} else if ((next.navigationPending || next.navigationScope) && next.navigationScope !== scope) {
		next.navigation = [];
		next.navigationPending = null;
		next.navigationScope = "";
	}
	if (next.checking && !model.busy) {
		if (model.checked && model.checked === model.xml) next.page = "resolved";
		next.checking = false;
	}
	return JSON.stringify(next) === JSON.stringify(ui) ? ui : next;
}
function change(next, model, event, commands) {
	try {
		const tree = edit(model.tree, model.view, event.name === void 0 ? next.selected : event.name, event.field, event.value), description = describe$1(tree, model.view);
		if (event.field === "add") next.selected = (description.elements[description.elements.length - 1] || {}).name || "";
		else if (event.field === "remove") next.selected = (description.elements[0] || {}).name || "";
		commands.push({
			type: "xml",
			value: serialize(tree, true)
		});
		next.error = "";
		return true;
	} catch (error) {
		next.error = String(error.message || error);
		return false;
	}
}
function numeric(field, value) {
	const number = Number(value), range = {
		row: [1, 100],
		column: [1, 12],
		span: [1, 12],
		rows: [1, 100],
		columns: [1, 12],
		height: [1, 1200],
		card_width: [1, 1200],
		layer: [-100, 100]
	}[field];
	return !range || /^-?\d+$/.test(String(value)) && Number.isInteger(number) && number >= range[0] && number <= range[1];
}
function transition(ui, model, event) {
	if (event.invert) event = Object.assign({}, event, { value: !event.value });
	const next = Object.assign({}, ui), commands = [], edit$1 = policy(model).editable;
	if (event.type === "help") return {
		ui: next,
		commands: [event]
	};
	if (event.type === "confirm" && ui.confirmation === "remove") {
		if (edit$1) change(next, model, {
			field: "remove",
			value: ""
		}, commands);
		next.confirmation = "";
		return {
			ui: next,
			commands
		};
	}
	if (event.type === "keep") next.pendingContext = null;
	if (event.type === "confirm" && ui.confirmation === "context") {
		if (!model.busy && !model.uncertain && ui.pendingContext) {
			commands.push({ type: "discard" });
			if (ui.pendingContext.type === "startView") next.creating = true;
			else commands.push(ui.pendingContext);
			next.confirmation = "";
			next.pendingContext = null;
			next.text = {};
		}
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
	switch (event.type) {
		case "openLayout":
		case "backLayout": {
			if (model.dirty || model.uncertain || pending(ui)) {
				next.confirmation = "discard";
				break;
			}
			const target = event.type === "openLayout" ? reference(model, ui) : ui.navigation[ui.navigation.length - 1];
			if (!target || target.project && target.project !== model.project) break;
			if (event.type === "openLayout") {
				if (ui.navigation.length >= 32) {
					next.error = "Return to a parent layout before opening another nested layout";
					break;
				}
				next.navigation = ui.navigation.concat([{
					project: model.project,
					searchType: model.searchType,
					view: model.view,
					source: model.source,
					selected: ui.selected,
					page: ui.page,
					panel: ui.panel,
					catalogWidth: ui.catalogWidth,
					propertiesWidth: ui.propertiesWidth
				}]);
			} else next.navigation = ui.navigation.slice(0, -1);
			next.navigationPending = {
				searchType: target.searchType,
				view: target.view,
				restore: event.type === "backLayout" ? target : null
			};
			next.error = "";
			commands.push({
				type: "reference",
				searchType: target.searchType,
				view: target.view,
				source: event.type === "backLayout" ? target.source : null
			});
			break;
		}
		case "page":
			next.page = event.value;
			break;
		case "panel":
			next.panel = event.value;
			break;
		case "select":
			if (pending(ui)) next.error = "Apply or discard the pending text before continuing";
			else {
				next.selected = event.name;
				next.panel = "settings";
				next.confirmation = "";
			}
			break;
		case "catalogSplit":
			next.catalogWidth = Math.max(180, Math.min(420, Number(event.value)));
			break;
		case "propertiesSplit":
			next.propertiesWidth = Math.max(240, Math.min(520, Number(event.value)));
			break;
		case "catalogVisible":
			next.catalogVisible = next.catalogVisible === false;
			break;
		case "propertiesVisible":
			next.propertiesVisible = next.propertiesVisible === false;
			break;
		case "newName":
		case "template":
			next[event.type] = event.value;
			break;
		case "buffer":
			if (edit$1) next.text = Object.assign({}, next.text, { [event.key]: event.value });
			break;
		case "text":
			if (edit$1 && !model.layoutError && Object.keys(ui.text).every((key) => key === event.key)) {
				next.text = Object.assign({}, next.text, { [event.key]: event.value });
				change(next, model, event, commands);
			}
			break;
		case "finishText":
			if (Object.prototype.hasOwnProperty.call(next.text, event.key)) {
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
			}
			break;
		case "number": {
			if (!edit$1 || !Object.prototype.hasOwnProperty.call(next.text, event.key)) break;
			const text = next.text[event.key];
			if (!numeric(event.field, text)) {
				next.error = "Enter a whole number within the allowed range";
				break;
			}
			if (change(next, model, {
				name: event.name,
				field: event.field,
				value: Number(text)
			}, commands)) {
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
			}
			break;
		}
		case "change":
			if (edit$1 && !model.layoutError && !pending(ui)) {
				if (!numeric(event.field, event.value)) {
					next.error = "Enter a whole number within the allowed range";
					break;
				}
				if (event.field === "parent") {
					let parent = event.value, seen = [next.selected];
					while (parent) {
						if (seen.indexOf(parent) >= 0) {
							next.error = "Invalid or cyclic layout container";
							break;
						}
						seen.push(parent);
						const item = model.layout.elements.find((row) => row.name === parent);
						if (!item || item.kind !== "group") {
							next.error = "Invalid or cyclic layout container";
							break;
						}
						parent = item.parent;
					}
					if (parent) break;
				}
				change(next, model, event, commands);
			}
			break;
		case "add":
			if (edit$1 && !model.layoutError && !pending(ui) && event.value) change(next, model, {
				name: "",
				field: "add",
				value: event.value
			}, commands);
			break;
		case "remove":
			if (edit$1 && next.selected && !pending(ui)) next.confirmation = "remove";
			break;
		case "geometry":
			if (edit$1 && !model.layoutError && !pending(ui)) try {
				commands.push({
					type: "xml",
					value: apply(model, event.value)
				});
				next.selected = event.value.key;
				next.error = "";
			} catch (error) {
				next.error = String(error.message || error);
			}
			break;
		case "spacing": {
			if (!edit$1 || model.layoutError || !Object.prototype.hasOwnProperty.call(ui.text, event.key)) break;
			const value = ui.text[event.key];
			if (!/^\d+$/.test(String(value)) || Number(value) > 256) {
				next.error = "Enter spacing from 0 to 256";
				break;
			}
			const item = model.layout.elements.find((row) => row.name === next.selected);
			if (!item || !["padding", "margin"].includes(event.field) || !Number.isInteger(event.side) || event.side < 0 || event.side > 3) break;
			const values = (item[event.field] || [
				0,
				0,
				0,
				0
			]).slice();
			values[event.side] = Number(value);
			if (change(next, model, {
				field: event.field,
				value: values.join(" ")
			}, commands)) {
				next.text = Object.assign({}, next.text);
				delete next.text[event.key];
			}
			break;
		}
		case "move":
		case "drop": if (edit$1 && !model.layoutError && !pending(ui)) {
			const name = event.type === "drop" ? event.value : next.selected, item = model.layout.elements.find((row) => row.name === name);
			if (!item) break;
			const parent = model.layout.elements.find((row) => row.name === item.parent), columns = parent ? parent.columns : model.layout.columns;
			const row = Math.max(1, Math.min(100, event.row)), column = Math.max(1, Math.min(columns - item.span + 1, event.column));
			try {
				const tree = edit(edit(model.tree, model.view, name, "row", row), model.view, name, "column", column);
				next.selected = name;
				commands.push({
					type: "xml",
					value: serialize(tree, true)
				});
				next.error = "";
			} catch (error) {
				next.error = String(error.message || error);
			}
			break;
		}
		case "xml":
			if (edit$1) commands.push({
				type: "xml",
				value: event.value
			});
			break;
		case "formatXml":
			if (edit$1 && !model.layoutError && !pending(ui)) commands.push({
				type: "xml",
				value: serialize(model.tree, true)
			});
			break;
		case "context":
			if (!["view", "searchType"].includes(event.field) || model[event.field] === event.value) break;
			if (!model.uncertain) {
				if (model.dirty || pending(ui)) {
					next.confirmation = "context";
					next.pendingContext = event;
				} else {
					next.creating = false;
					commands.push(event);
				}
			}
			break;
		case "startView":
			if (edit$1 && !model.uncertain) {
				if (model.dirty || pending(ui)) {
					next.confirmation = "context";
					next.pendingContext = event;
				} else next.creating = true;
			}
			break;
		case "cancelView":
			next.creating = false;
			break;
		case "source":
			if (!model.dirty && !model.uncertain && !pending(ui)) commands.push(event);
			break;
		case "newView":
			if (edit$1 && !model.dirty && !pending(ui)) {
				const name = next.newName.trim();
				if (!/^[A-Za-z_][\w.@-]{0,127}$/.test(name)) {
					next.error = "Invalid view name";
					break;
				}
				if ((model.configuration.views || []).indexOf(name) >= 0) {
					next.error = "A view with this name already exists";
					break;
				}
				const template$1 = (model.templates || []).find((row) => row.name === next.template), tree = next.template === "copy" ? model.tree : template$1 && template$1.tree;
				try {
					if (!tree) throw Error("Invalid layout template");
					commands.push({
						type: "newView",
						view: name,
						xml: serialize(template(tree, name), true)
					});
					next.error = "";
				} catch (error) {
					next.error = String(error.message || error);
				}
			}
			break;
		case "check":
			if (edit$1 && !pending(ui) && !model.layoutError) {
				next.checking = true;
				commands.push(event);
			}
			break;
		case "openView":
			if (edit$1 && !model.dirty && !pending(ui) && model.configuration.resolved && model.configuration.resolved.configured) commands.push(event);
			break;
		case "help": commands.push(event);
	}
	return {
		ui: next,
		commands
	};
}
function completed(ui, command) {
	if (command.type === "newView") return Object.assign({}, ui, {
		creating: false,
		page: "design",
		panel: "elements"
	});
	return [
		"reload",
		"discard",
		"source"
	].indexOf(command.type) >= 0 ? Object.assign({}, ui, {
		text: {},
		confirmation: "",
		checking: false,
		error: ""
	}) : ui;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.samples.mjs
function fallback(layout, records, searchType, selected, language, screenWidth = 1e3) {
	if (!layout?.elements?.length) return null;
	const tr = (text) => translate(text, language);
	const byName = new Map(layout.elements.map((item) => [item.name, item]));
	const chain = [];
	for (let item = byName.get(selected); item && chain.length < 8; item = byName.get(item.parent)) chain.push(item);
	const matches = (sample) => chain.length ? chain.every((item) => visible(item, sample, layout, screenWidth)) : supports(layout, sample, screenWidth);
	if ((records || []).some(matches)) return null;
	const target = chain.find((item) => item.search_type)?.search_type || searchType;
	const conditions = chain.reduce((all, item) => all.concat(item.when || []), []);
	const variant = chain.find((item) => item.variant && item.variant !== "all")?.variant || (conditions.includes("relation") ? "relation" : conditions.includes("branch") ? "process" : conditions.includes("snapshot") ? "snapshot" : "main");
	const sample = {
		kind: [
			"process",
			"relation",
			"versions"
		].includes(variant) ? "branch" : ["snapshot", "file"].includes(variant) ? variant : "object",
		depth: variant === "children" ? 1 : 0,
		search_type: target,
		title: tr("Example item"),
		subtitle: tr("Example description"),
		record: Object.assign(Object.create(null), {
			name: tr("Example item"),
			title: tr("Example item"),
			description: tr("Example description")
		}),
		preview: {},
		note_count: 3,
		task_count: 2,
		branch: {
			kind: variant,
			count: 3,
			relationship: "instance",
			process: tr("Example process")
		},
		snapshot_display: {
			title: "example.jpg",
			exists: false,
			version: "v001",
			author: tr("Example author"),
			size: 1024
		},
		knowledge: [{ title: tr("Example item") }]
	};
	function bind(path, value) {
		const parts = String(path || "").split(".");
		if (!["record", "node"].includes(parts[0]) || parts.length < 2 || parts.length > 6 || parts.some((part) => [
			"__proto__",
			"constructor",
			"prototype",
			"__search_key__",
			"id"
		].includes(part))) return;
		let result = parts.shift() === "record" ? sample.record : sample;
		for (const part of parts.slice(0, -1)) {
			if (!result[part] || typeof result[part] !== "object") result[part] = Object.create(null);
			result = result[part];
		}
		const key = parts[parts.length - 1];
		if (result[key] === void 0) result[key] = value;
	}
	function values(current, depth) {
		if (!current || depth >= 8) return;
		for (const item of current.elements || []) {
			const options = item.options || {};
			let value = tr("Example value");
			if (options.format === "progress" || /(?:count|progress|percent)$/.test(options.bind || "")) value = 42;
			else if (["date", "datetime"].includes(options.format)) value = "2026-01-15T12:00:00Z";
			else if (options.format === "badge") {
				let colors = {};
				try {
					colors = JSON.parse(options.colors || "{}");
				} catch (error) {}
				value = Object.keys(colors)[0] || tr("Example status");
			}
			bind(options.bind, value);
			bind(options.badge, 3);
			if (item.widget_layout) values(item.widget_layout, depth + 1);
		}
	}
	values(layout, 0);
	return matches(sample) ? sample : null;
}
function scene(layout, sample, width, height, selected, editing, language, screenWidth, assetBase) {
	if (!layout || !sample || width <= 0 || height <= 0) return { nodes: [] };
	const composition = describe$2(layout, sample, Math.max(1, width - 16), selected, language, screenWidth, assetBase, "itemComposition", 0, true);
	const content = editing ? itemScene(composition, layout) : composition;
	return {
		canvasBoxes: content.canvasBoxes || [],
		nodes: [node("Scroll", "layoutSampleScroll", rect(0, 0, width, height), {
			contentHeight: composition.height,
			scrollbarId: "layoutSampleScrollBar",
			children: content.nodes
		})]
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.catalog.mjs
function views(model, language) {
	const tr = (text) => translate(text, language);
	const names = model.configuration?.layout_views || model.knownViews || [];
	return [...new Set([...names, model.view].filter(Boolean))].map((value) => {
		const example = {
			continuous_example: "Tree example",
			table_example: "Table example",
			cards_example: "Cards example"
		}[value];
		return {
			value,
			label: example ? tr(example) + " · " + value : value
		};
	});
}
function context(model, ui, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	const enabled = !model.busy && !model.uncertain && !ui.confirmation;
	const stacked = width < 620, gap = 12, buttonWidth = 120;
	const typeWidth = stacked ? width : Math.min(280, width * .32);
	const viewX = stacked ? 0 : typeWidth + gap;
	const viewY = stacked ? 62 : 0;
	const viewWidth = stacked ? width - buttonWidth - gap : Math.min(360, width - viewX - buttonWidth - gap);
	nodes.push(label("layoutTypeLabel", rect(0, 0, typeWidth, 18), tr("Search Type"), muted), node("Choice", "layoutSearchType", rect(0, 22, typeWidth, 38), {
		label: tr("Search Type"),
		value: model.searchType,
		options: model.searchTypes || [],
		enabled,
		action: {
			type: "context",
			field: "searchType"
		}
	}), label("layoutViewLabel", rect(viewX, viewY, viewWidth, 18), tr("View") + (model.dirty ? " · " + tr("Unsaved changes") : ""), muted), node("Choice", "layoutView", rect(viewX, viewY + 22, viewWidth, 38), {
		label: tr("View"),
		value: model.view,
		options: views(model, language),
		enabled,
		action: {
			type: "context",
			field: "view"
		}
	}), button("layoutNewView", rect(viewX + viewWidth + gap, viewY + 22, buttonWidth, 38), tr("New view"), "add", { type: "startView" }, enabled && model.ready));
	let height = viewY + 72;
	if (ui.creating) {
		const formWidth = Math.min(width, 760), narrow = formWidth < 620;
		const nameWidth = narrow ? formWidth : (formWidth - 12) / 2;
		const templateX = narrow ? 0 : nameWidth + 12, templateY = narrow ? height + 62 : height;
		nodes.push(label("layoutNewNameLabel", rect(0, height, nameWidth, 18), tr("View name"), muted), node("Field", "layoutNewName", rect(0, height + 22, nameWidth, 38), {
			label: tr("View name"),
			text: ui.newName,
			enabled,
			placeholder: "my_view",
			action: { type: "newName" }
		}), label("layoutTemplateLabel", rect(templateX, templateY, nameWidth, 18), tr("Starting point"), muted), node("Choice", "layoutTemplate", rect(templateX, templateY + 22, nameWidth, 38), {
			label: tr("Starting point"),
			value: ui.template,
			enabled,
			options: [
				{
					value: "blank",
					label: tr("Blank view")
				},
				{
					value: "copy",
					label: tr("Copy current view")
				},
				{
					value: "continuous",
					label: tr("Continuous Tree")
				},
				{
					value: "cards",
					label: tr("Cards")
				},
				{
					value: "table",
					label: tr("Table View")
				}
			],
			action: { type: "template" }
		}), button("layoutCreateView", rect(0, templateY + 72, 164, 38), tr("Create draft"), "add", { type: "newView" }, enabled && !!ui.newName.trim()), button("layoutCancelNewView", rect(176, templateY + 72, 120, 38), tr("Cancel"), "close", { type: "cancelView" }, enabled));
		height = templateY + 122;
	}
	return {
		nodes,
		height
	};
}
function row$1(list, record, model) {
	return { nodes: [node("Action", "layoutSavedView_" + record.value, rect(0, 0, list.width - 16, 34), {
		text: record.label,
		selected: model.view === record.value,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		enabled: !model.busy && !model.uncertain,
		radius: 6,
		children: [label("layoutSavedViewTitle_" + record.value, rect(10, 0, list.width - 36, 34), record.label)],
		action: {
			type: "context",
			field: "view",
			value: record.value
		}
	})] };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.ui.mjs
var labels = {
	group: "Group",
	view: "Reusable view",
	text: "Text",
	field: "Field",
	title: "Title",
	description: "Description",
	image: "Image",
	link: "Link",
	button: "Button",
	metadata: "Metadata",
	"snapshot-details": "Snapshot details",
	"snapshot-size": "File size",
	"snapshot-summary": "Snapshot summary",
	"branch-summary": "Branch summary",
	"file-offline": "File Offline",
	"item-menu": "Item actions",
	"quick-actions": "Snapshot actions",
	knowledge: "Knowledge Base",
	relations: "Relationship actions",
	all: "All items",
	main: "Main object",
	children: "Child object",
	process: "Process",
	relation: "Relation",
	versions: "Versions",
	snapshot: "Snapshot",
	file: "File",
	inspect: "Object details",
	operate: "Object actions",
	preview: "File preview",
	tasks: "Tasks",
	notes: "Notes",
	upload: "Add files",
	create: "Create related object",
	cover: "Fill the image area",
	contain: "Show the whole image",
	stretch: "Fill the cell",
	start: "Start",
	center: "Center",
	end: "End",
	normal: "Normal",
	muted: "Muted",
	strong: "Strong"
};
function choices(values, language) {
	return values.map((value) => ({
		value,
		label: translate(labels[value] || value || "None", language)
	}));
}
function model(raw, ui, language = "en", screenWidth = 1e3) {
	let layout = {
		elements: [],
		columns: 12,
		flow: "grid",
		collection: "grid",
		tracks: "",
		card_width: 280
	}, layoutError = raw.parseError ? "Invalid configuration XML" : "";
	if (!layoutError && raw.tree) try {
		layout = describe$1(raw.tree, raw.view);
	} catch (error) {
		layoutError = String(error.message || error);
	}
	if (!layoutError && (!Number.isInteger(layout.columns) || layout.columns < 1 || layout.columns > 12 || !Number.isFinite(layout.card_width) || layout.elements.some((row) => [
		"row",
		"column",
		"span",
		"rows",
		"columns",
		"height",
		"layer"
	].some((key) => !Number.isFinite(row[key]))))) layoutError = "Invalid layout size";
	if (!layoutError) {
		const names = [];
		for (const item of layout.elements) {
			if (!item.name || names.indexOf(item.name) >= 0) {
				layoutError = "Invalid or duplicate layout element name";
				break;
			}
			names.push(item.name);
		}
		if (layout.elements.length > 128) layoutError = "Layout supports at most 128 elements";
		for (const item of layout.elements) {
			if (item.options.colors) try {
				const colors = JSON.parse(item.options.colors);
				if (!colors || typeof colors !== "object" || Array.isArray(colors)) throw Error("Invalid field value colors");
			} catch (error) {
				layoutError = "Invalid field value colors";
				break;
			}
			const seen = [item.name];
			let parent = item.parent;
			while (parent) {
				if (seen.indexOf(parent) >= 0 || seen.length >= 8) {
					layoutError = "Invalid or cyclic layout container";
					break;
				}
				seen.push(parent);
				const container = layout.elements.find((row) => row.name === parent);
				parent = container ? container.parent : "";
			}
		}
	}
	const record = ((raw.sampleItems || [])[0] || {}).record || {}, bindings = [""].concat(Object.keys((raw.preview || {}).columns || record).filter((key) => key.indexOf("__") !== 0).map((key) => "record." + key), [
		"node.title",
		"node.subtitle",
		"node.preview.image",
		"node.note_count",
		"node.task_count",
		"node.branch.count",
		"node.snapshot_display.version",
		"node.snapshot_display.author"
	]);
	const types = (raw.searchTypes || []).slice().sort((a, b) => a.label.toLowerCase() < b.label.toLowerCase() ? -1 : a.label.toLowerCase() > b.label.toLowerCase() ? 1 : 0);
	return Object.assign({}, raw, {
		samplePreview: !raw.busy && !raw.error && !raw.sampleError && !raw.previewError ? fallback(raw.liveInterface?.table?.item_layout, raw.sampleItems, raw.searchType, ui.selected, language, screenWidth) : null,
		ready: !!raw.configuration,
		canLoad: !!raw.canLoad,
		canWrite: !!raw.canWrite,
		searchTypes: types,
		bindings,
		dirty: !!raw.dirty || pending(ui),
		pendingText: pending(ui),
		layout,
		layoutError,
		document: {},
		identity: raw.view || "",
		saveAllowed: !!raw.checked && raw.checked === raw.xml && !layoutError && !pending(ui),
		error: raw.error || ui.error,
		message: raw.message || ""
	});
}
function toolbar(model, ui, width, language, embedded = false) {
	const tr = (text) => translate(text, language), result = toolbar$1(model, ui, width, language), edit = policy(model).editable && !ui.confirmation;
	result.nodes = result.nodes.filter((row) => row.id !== "adminDocumentStatus");
	result.nodes.push(button("layoutCheck", rect(46, 0, 38, 38), tr("Check and preview"), "check", { type: "check" }, edit && !model.layoutError && !pending(ui), { iconOnly: true }), button("layoutHelp", rect(90, 0, 38, 38), tr("Layout guide"), "help", { type: "help" }, true, { iconOnly: true }), button("layoutOpenView", rect(embedded ? 90 : 134, 0, 38, 38), tr("Open saved view"), "open-in-new", { type: "openView" }, edit && !model.dirty && !!(model.configuration && model.configuration.resolved && model.configuration.resolved.configured), { iconOnly: true }));
	if (embedded) result.nodes = result.nodes.filter((row) => row.id !== "layoutHelp");
	if (ui.page === "xml") result.nodes.push(button("layoutFormatXml", rect(embedded ? 134 : 178, 0, 38, 38), tr("Format XML"), "code", { type: "formatXml" }, edit && !model.layoutError && !pending(ui), { iconOnly: true }));
	return result;
}
function models(model, language = "en") {
	return {
		layoutElements: model.layout.elements,
		layoutViews: views(model, language)
	};
}
function row(list, record, model, ui, language) {
	if (list.source === "layoutViews") return row$1(list, record, model);
	const width = list.width - 16, tr = (text) => translate(text, language), id = "layoutElement_" + record.name;
	return { nodes: [node("Action", id, rect(0, 0, width, 46), {
		text: record.title || record.name,
		selected: ui.selected === record.name,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		dragValue: policy(model).editable && !pending(ui) ? record.name : null,
		dragStartAction: {
			type: "select",
			name: record.name
		},
		children: [label(id + "Title", rect(record.parent ? 22 : 10, 0, width - (record.parent ? 32 : 20), 26), (record.parent ? "↳ " : "") + (record.title || record.name), { weight: 600 }), label(id + "Kind", rect(10, 26, width - 20, 18), tr(labels[record.kind] || record.kind), muted)],
		action: {
			type: "select",
			name: record.name
		}
	})] };
}
function propertyFields(model, ui, language, width) {
	const tr = (text) => translate(text, language), item = model.layout.elements.find((row) => row.name === ui.selected);
	if (!item) return [];
	const edit = policy(model).editable, enabled = edit && !pending(ui), fields = [];
	function text(field, title, value, description, name) {
		const key = item.name + ":" + field, buffered = field === "title" || field === "when";
		return {
			id: "layoutProperty_" + field.replace(/:/g, "_"),
			title,
			description,
			props: {
				text: buffered && Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : value === void 0 ? "" : String(value),
				enabled: buffered ? edit && Object.keys(ui.text).every((value) => value === key) : enabled,
				action: buffered ? {
					type: "text",
					field,
					key,
					name
				} : {
					type: "change",
					field,
					name
				},
				commitAction: buffered ? {
					type: "finishText",
					key
				} : null
			}
		};
	}
	function choice(field, title, value, options, description, name) {
		return {
			id: "layoutProperty_" + field.replace(/:/g, "_"),
			title,
			description,
			kind: "Choice",
			options,
			props: {
				value,
				enabled,
				action: {
					type: "change",
					field,
					name
				}
			}
		};
	}
	function integer(field, title, value, description) {
		const key = item.name + ":" + field;
		return {
			id: "layoutProperty_" + field,
			title,
			description,
			props: {
				text: Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(value),
				enabled: edit,
				action: {
					type: "buffer",
					key
				},
				commitAction: {
					type: "number",
					key,
					field
				},
				inputMode: "numeric"
			}
		};
	}
	const bindings = [{
		value: "",
		label: tr("Fixed text")
	}].concat((model.bindings || []).filter(Boolean).map((value) => ({
		value,
		label: tr({
			"node.title": "Object title",
			"node.subtitle": "Object description",
			"node.preview.image": "Object preview",
			"node.note_count": "Number of notes",
			"node.task_count": "Number of tasks",
			"node.branch.count": "Number of children",
			"node.snapshot_display.version": "Snapshot version",
			"node.snapshot_display.author": "Snapshot author"
		}[value] || value.replace(/^record\./, ""))
	})));
	fields.push({
		kind: "Heading",
		id: "layoutElementHeading",
		title: item.title || item.name
	}, text("title", "Label", item.title), choice("kind", "Widget", item.kind, choices(widgets, language)));
	if ([
		"text",
		"field",
		"title",
		"description",
		"image",
		"link",
		"button"
	].indexOf(item.kind) >= 0) {
		fields.push({
			kind: "Heading",
			id: "layoutContentHeading",
			title: "Content"
		}, choice("option:bind", "Data binding", item.options.bind || "", bindings, "Choose which object value to display"));
		if (!item.options.bind || item.kind === "field") fields.push(text("option:text", item.kind === "image" ? "Image URL" : item.kind === "field" ? "Label" : "Text", item.options.text || ""));
		if (item.kind === "image") {
			if (item.role !== "preview") fields.push(integer("height", "Image height", item.height));
			fields.push(choice("option:fit", "Image fit", item.options.fit || "cover", choices(["cover", "contain"], language)));
		}
		if (item.kind === "link" || item.kind === "button") fields.push(text("option:href", "Link URL", item.options.href || ""));
		if (item.kind === "button") fields.push(choice("option:action", "Action", item.options.action || "", choices([""].concat(actions), language)), choice("option:badge", "Badge binding", item.options.badge || "", bindings.map((row) => row.value ? row : {
			value: "",
			label: tr("No badge")
		}), "Choose a number to show on the button"), text("option:icon", "Icon", item.options.icon || ""));
	}
	const palette = [
		["", "Auto"],
		["primaryText", "Text"],
		["secondaryText", "Secondary"],
		["contentAccent", "Accent"],
		["green", "Green"],
		["yellow", "Yellow"],
		["red", "Red"],
		["cyan", "Cyan"],
		["violet", "Violet"]
	];
	const colorOptions = (value, entries = palette) => entries.map(([value, label]) => ({
		value,
		label: tr(label)
	})).concat(value?.startsWith("#") ? [{
		value,
		label: value
	}] : []);
	if ([
		"field",
		"text",
		"title",
		"description"
	].includes(item.kind)) fields.push(choice("option:color", "Text / icon color", item.options.color || "", colorOptions(item.options.color)));
	if (item.kind === "field") {
		fields.push(choice("option:format", "Field display", item.options.format || "plain", [
			["plain", "Plain text"],
			["date", "Date"],
			["datetime", "Date and time"],
			["badge", "Status badge"],
			["progress", "Progress"]
		].map(([value, label]) => ({
			value,
			label: tr(label)
		}))));
		const colors = item.options.colors ? JSON.parse(item.options.colors) : {}, values = [...new Set(Object.keys(colors).concat((model.sampleItems || []).map((sample) => String(binding(item.options.bind, sample))).filter(Boolean)))].slice(0, 32);
		for (const value of values) fields.push(choice("valueColor:" + value, "Value color", colors[value] || "", colorOptions(colors[value]), "«" + value + "»"));
	}
	if (item.kind === "group") fields.push(choice("option:fill", "Fill color", item.options.fill || "", colorOptions(item.options.fill, [
		["", "None"],
		["panel", "Panel"],
		["workspace", "Workspace"],
		["surfaceContainerLow", "Surface"]
	])), choice("option:stroke", "Stroke color", item.options.stroke || "", colorOptions(item.options.stroke, [
		["", "None"],
		["outlineVariant", "Outline"],
		["contentAccent", "Accent"]
	])), text("option:radius", "Corner radius", item.options.radius || "0"));
	if (item.kind === "view") {
		const field = text("option:view", "Reusable view", item.options.view || "");
		field.trailingAction = {
			title: "Edit nested item layout",
			icon: "open-in-new",
			enabled: !model.busy && !model.uncertain && !!reference(model, ui),
			action: { type: "openLayout" }
		};
		fields.push(field);
	}
	const parentOptions = [{
		value: "",
		label: tr("View root")
	}].concat(model.layout.elements.filter((row) => row.kind === "group" && row.name !== item.name).map((row) => ({
		value: row.name,
		label: row.title || row.name
	}))), parent = model.layout.elements.find((row) => row.name === item.parent), grid = (parent ? parent.flow : model.layout.flow) === "grid";
	fields.push({
		kind: "Heading",
		id: "layoutPositionHeading",
		title: "Position"
	}, choice("parent", "Container", item.parent, parentOptions));
	if (grid && model.layout.flow !== "contents" && model.layout.collection !== "table") for (const name of ["padding", "margin"]) fields.push(spacingField("layout" + name, tr(name === "padding" ? "Padding" : "Margin"), item[name] || [
		0,
		0,
		0,
		0
	], ui.text, {
		type: "spacing",
		field: name
	}, language, edit, width - 48));
	if (grid) for (const key of [
		"row",
		"column",
		"span",
		"rows"
	]) fields.push(integer(key, {
		row: "Row",
		column: "Column",
		span: "Column span",
		rows: "Row span"
	}[key], item[key]));
	else fields.push({
		kind: "Heading",
		id: "layoutSharedPositionHelp",
		title: "Shared item layout",
		description: "Positions follow shared item styles. Choose Grid in the parent container for placement by rows and columns."
	});
	fields.push(integer("layer", "Layer", item.layer, "Higher layers appear in front. Use the same grid cells to place text or buttons over an image."), {
		kind: "Heading",
		id: "layoutAdvancedHeading",
		title: "More element settings"
	}, {
		kind: "Switch",
		id: "layoutPropertyVisible",
		title: "Visible",
		props: {
			checked: !item.hidden,
			enabled,
			action: {
				type: "change",
				field: "hidden",
				invert: true
			}
		}
	}, choice("variant", "Item variant", item.variant, choices(variants, language)), choice("search_type", "Search Type", item.search_type || "", [{
		value: "",
		label: tr("All")
	}, ...model.searchTypes]), text("option:bind", "Custom data binding", item.options.bind || ""));
	fields[fields.length - 1].id = "layoutCustomBinding";
	if (item.kind === "link" || item.kind === "button") fields.push(choice("option:href_bind", "Link URL binding", item.options.href_bind || "", bindings));
	fields.push(choice("role", "Style role", item.role, Object.keys(roles).map((value) => ({
		value,
		label: tr(roles[value])
	}))));
	if (item.kind === "group") fields.push(choice("flow", "Child layout", item.flow, [{
		value: "grid",
		label: tr("Grid")
	}, {
		value: "contents",
		label: tr("Shared item layout")
	}]), integer("columns", "Grid columns", item.columns));
	fields.push(choice("tag", "Markup tag", item.tag, [
		"div",
		"span",
		"strong",
		"small"
	].map((value) => ({
		value,
		label: value
	}))), text("when", "Display conditions", item.when.join(" "), "Limit the element to desktop, mobile or particular items"), choice("align", "Alignment", item.align, choices([
		"stretch",
		"start",
		"center",
		"end"
	], language)), choice("tone", "Text style", item.tone, choices([
		"normal",
		"muted",
		"strong"
	], language)));
	return fields;
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	if (height < 400) return { nodes: [node("Scroll", "layoutPageScroll", rect(0, 0, width, height), {
		contentHeight: 640,
		scrollbarId: "layoutPageScrollBar",
		children: describe(model, ui, width - 16, 640, language).nodes
	})] };
	const tr = (text) => translate(text, language), edit = policy(model).editable && !ui.confirmation, noticeModel = Object.assign({}, model);
	if (ui.confirmation === "remove") noticeModel.confirmationText = "Remove this element and its children?";
	if (ui.confirmation === "context") noticeModel.confirmationText = "Discard changes to the current view and continue?";
	const notice = notices(noticeModel, ui, width, language, void 0, ui.confirmation === "remove" ? "Remove element" : void 0), nodes = notice.nodes;
	let y = notice.top;
	const context$1 = context(model, ui, width, language);
	nodes.push(node("Box", "layoutDocumentContext", rect(0, y, width, context$1.height), { children: context$1.nodes }));
	y += context$1.height;
	nodes.push(sectionSelector("layoutPages", [
		{
			value: "design",
			label: tr("Design")
		},
		{
			value: "configuration",
			label: tr("Configuration")
		},
		{
			value: "xml",
			label: tr("Source XML")
		},
		{
			value: "changes",
			label: tr("Configuration changes")
		},
		{
			value: "resolved",
			label: tr("Resolved preview")
		}
	], ui.page, rect(0, y, width, 38), !model.busy, "page"));
	y += 46;
	if (ui.page === "design" && width >= 500) {
		nodes.push(label("layoutSelectionHint", rect(0, y, width, 24), tr("Click to select. Alt-click for underlying layers."), Object.assign({}, muted, { fontRole: "caption" })));
		y += 32;
	}
	if (model.sampleError) {
		nodes.push(node("Area", "layoutSampleError", rect(0, y, width, 58), {
			label: tr("Preview data could not be loaded"),
			text: tr("Preview data could not be loaded") + ": " + model.sampleError,
			readOnly: true,
			notice: true
		}));
		y += 66;
	}
	const h = Math.max(1, height - y), layout = model.layout, selected = layout.elements.find((row) => row.name === ui.selected);
	if (ui.page === "xml") {
		nodes.push(node("Code", "layoutXmlSource", rect(0, y, width, h), {
			text: model.xml || "",
			language,
			syntax: "xml",
			readOnly: !edit,
			service: "sourceEditor",
			bufferKey: [
				model.project,
				model.searchType,
				model.view,
				model.source
			].join(":"),
			action: { type: "xml" },
			helpAction: { type: "help" }
		}));
		return { nodes };
	}
	if (ui.page === "changes") {
		nodes.push(node("Area", "layoutChanges", rect(0, y, width, h), {
			text: model.diff || tr("Check and preview the draft before saving."),
			label: tr("Configuration changes"),
			monospace: true,
			readOnly: true
		}));
		return { nodes };
	}
	if (ui.page === "configuration") {
		const fields = [{
			kind: "Choice",
			id: "layoutSource",
			title: "Configuration source",
			options: (model.configuration?.sources || []).map((row) => ({
				value: row.id,
				label: String(row.id) + " · " + tr("Priority") + " " + (row.priority ?? "")
			})).concat([{
				value: "",
				label: tr("New override")
			}]),
			props: {
				value: model.source,
				enabled: !model.busy && !model.dirty && !model.uncertain,
				action: { type: "source" }
			}
		}];
		if (!model.layoutError) {
			const integer = (key, title) => ({
				id: "layoutRoot_" + key,
				title,
				props: {
					text: Object.prototype.hasOwnProperty.call(ui.text, "root:" + key) ? ui.text["root:" + key] : String(layout[key]),
					enabled: edit,
					action: {
						type: "buffer",
						key: "root:" + key
					},
					commitAction: {
						type: "number",
						key: "root:" + key,
						name: "",
						field: key
					},
					inputMode: "numeric"
				}
			});
			fields.push({
				kind: "Heading",
				id: "layoutCollectionHeading",
				title: "Collection layout"
			}, {
				kind: "Choice",
				id: "layoutCollection",
				title: "Collection layout",
				options: [
					{
						value: "grid",
						label: tr("Cards")
					},
					{
						value: "list",
						label: tr("List")
					},
					{
						value: "tree",
						label: tr("Continuous Tree")
					},
					{
						value: "table",
						label: tr("Table View")
					}
				],
				props: {
					value: layout.collection,
					enabled: edit && !pending(ui),
					action: {
						type: "change",
						name: "",
						field: "collection"
					}
				}
			});
			if (layout.collection === "grid") fields.push(integer("card_width", "Card width"));
			fields.push({
				kind: "Choice",
				id: "layoutFlow",
				title: "Container layout",
				options: [{
					value: "grid",
					label: tr("Grid")
				}, {
					value: "contents",
					label: tr("Shared item layout")
				}],
				props: {
					value: layout.flow,
					enabled: edit && !pending(ui),
					action: {
						type: "change",
						name: "",
						field: "flow"
					}
				}
			}, integer("columns", "Grid columns"), {
				id: "layoutTracks",
				title: "Column tracks",
				description: "Optional sizes such as 128px 1fr auto",
				props: {
					text: layout.tracks || "",
					enabled: edit && !pending(ui),
					action: {
						type: "change",
						name: "",
						field: "tracks"
					}
				}
			});
		}
		const body = sections(fields, width - 16, language, edit);
		nodes.push(node("Scroll", "layoutConfigurationScroll", rect(0, y, width, h), {
			contentHeight: body.height,
			scrollbarId: "layoutConfigurationScrollBar",
			children: body.nodes
		}));
		return { nodes };
	}
	if (ui.page === "resolved") {
		if (!(model.preview && (model.preview.item_layout || (model.preview.table || {}).item_layout))) {
			nodes.push(label("layoutResolvedHelp", rect(12, y, width - 24, 96), tr("Check and preview the draft before saving."), Object.assign({ wrap: true }, muted)));
			return { nodes };
		}
		return { nodes: nodes.concat(node("View", "layoutResolvedResults", rect(0, y, width, Math.max(1, height - y)), { view: "itemResults" })) };
	}
	if (model.layoutError) {
		nodes.push(node("Area", "layoutInvalid", rect(0, y, width, h), {
			text: tr(model.layoutError) + ". " + tr("Use Source XML or create a view from a layout template."),
			label: tr("Layout Editor"),
			readOnly: true,
			notice: true,
			color: "error"
		}));
		return { nodes };
	}
	const wide = width >= 1e3, catalogVisible = ui.catalogVisible !== false, propertiesVisible = ui.propertiesVisible !== false, left = wide ? catalogVisible ? Math.min(ui.catalogWidth, width * .24) : 56 : width, properties = wide ? propertiesVisible ? Math.min(ui.propertiesWidth, width * .34) : 56 : width;
	if (!wide) {
		nodes.push(sectionSelector("layoutPanels", [
			{
				value: "elements",
				label: tr("Elements")
			},
			{
				value: "preview",
				label: tr("Item preview")
			},
			{
				value: "settings",
				label: tr("Element settings")
			}
		], ui.panel, rect(0, y, width, 38), !model.busy, "panel"));
		y += 46;
	}
	const bodyHeight = Math.max(1, height - y);
	if (wide || ui.panel === "elements") {
		const w = left, viewsHeight = Math.min(144, Math.max(68, bodyHeight * .24)), elementsTop = 58 + viewsHeight, children = [];
		if (!wide || catalogVisible) children.push(label("layoutViewsHeading", rect(12, 10, Math.max(0, w - (wide ? 62 : 24)), 34), tr("Views"), { weight: 600 }), node("List", "layoutViewsList", rect(12, 52, w - 24, viewsHeight), {
			source: "layoutViews",
			keyField: "value",
			rowHeight: 38,
			scrollbarId: "layoutViewsScrollBar"
		}), label("layoutElementsHeading", rect(12, elementsTop + 8, w - 24, 28), tr("Elements"), { weight: 600 }), node("Choice", "layoutAddWidget", rect(12, elementsTop + 44, w - 24, 38), {
			label: tr("Add widget"),
			value: "",
			options: [{
				value: "",
				label: tr("Add widget")
			}].concat(choices(widgets, language)),
			enabled: edit && !pending(ui),
			action: { type: "add" }
		}), node("List", "layoutElementsList", rect(12, elementsTop + 90, w - 24, Math.max(0, bodyHeight - elementsTop - 146)), {
			source: "layoutElements",
			keyField: "name",
			rowHeight: 50,
			scrollbarId: "layoutElementsScrollBar"
		}), button("layoutEarlier", rect(12, bodyHeight - 44, (w - 32) / 2, 36), tr("Move element earlier"), "chevron-up", {
			type: "change",
			field: "order",
			value: -1
		}, edit && !!selected && !pending(ui), { iconOnly: true }), button("layoutLater", rect((w + 8) / 2, bodyHeight - 44, (w - 32) / 2, 36), tr("Move element later"), "chevron-down", {
			type: "change",
			field: "order",
			value: 1
		}, edit && !!selected && !pending(ui), { iconOnly: true }));
		if (wide) children.push(button("layoutToggleElements", rect(catalogVisible ? w - 46 : (w - 34) / 2, 10, 34, 34), tr(catalogVisible ? "Hide elements" : "Show elements"), catalogVisible ? "chevron-left" : "chevron-right", { type: "catalogVisible" }, true, {
			iconOnly: true,
			iconAction: true,
			round: false
		}));
		nodes.push(node("Box", "layoutElementsPanel", rect(0, y, w, bodyHeight), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
		if (wide && catalogVisible) nodes.push(node("Splitter", "layoutElementsSplit", rect(w, y, 10, bodyHeight), {
			text: tr("Elements panel width"),
			value: w,
			min: 180,
			max: Math.min(420, width * .24),
			action: { type: "catalogSplit" }
		}));
	}
	if (wide || ui.panel === "settings") {
		const w = properties, x = wide ? width - w : 0, settingsChildren = [];
		if (!wide || propertiesVisible) {
			const fields = propertyFields(model, ui, language, w), body = sections(fields, w - 40, language, edit && !pending(ui));
			if (selected) {
				body.nodes.push(button("layoutRemoveElement", rect(0, body.height, w - 40, 38), tr("Remove element"), "delete", { type: "remove" }, edit && !pending(ui)));
				body.height += 46;
			} else {
				body.nodes.push(label("layoutSelectHelp", rect(0, 0, w - 40, 120), tr("Select an element or add a new widget."), Object.assign({ wrap: true }, muted)));
				body.height = 128;
			}
			settingsChildren.push(label("layoutSettingsHeading", rect(12, 10, Math.max(0, w - (wide ? 62 : 24)), 34), tr("Element settings"), { weight: 600 }), node("Scroll", "layoutSettingsScroll", rect(12, 52, w - 24, Math.max(0, bodyHeight - 64)), {
				contentHeight: body.height,
				resetKey: ui.selected,
				scrollbarId: "layoutSettingsScrollBar",
				children: body.nodes
			}));
		}
		if (wide) settingsChildren.push(button("layoutToggleSettings", rect(propertiesVisible ? w - 46 : (w - 34) / 2, 10, 34, 34), tr(propertiesVisible ? "Hide element settings" : "Show element settings"), propertiesVisible ? "chevron-right" : "chevron-left", { type: "propertiesVisible" }, true, {
			iconOnly: true,
			iconAction: true,
			round: false
		}));
		nodes.push(node("Box", "layoutSettingsPanel", rect(x, y, w, bodyHeight), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: settingsChildren
		}));
		if (wide && propertiesVisible) nodes.push(node("Splitter", "layoutSettingsSplit", rect(x - 10, y, 10, bodyHeight), {
			text: tr("Element settings width"),
			value: w,
			min: 240,
			max: Math.min(520, width * .34),
			reverse: true,
			action: { type: "propertiesSplit" }
		}));
	}
	if (wide || ui.panel === "preview") {
		const x = wide ? left + 10 : 0, w = wide ? Math.max(1, width - left - properties - 20) : width;
		nodes.push(node("Box", "layoutPreviewPanel", rect(x, y, w, bodyHeight), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [label("layoutPreviewHeading", rect(12, 8, w - 24, 28), tr(model.samplePreview ? "Item preview · Sample data" : "Item preview"), { weight: 600 }), layout.elements.length ? node("View", "layoutPreviewResults", rect(12, 44, w - 24, bodyHeight - 56), { view: "itemResults" }) : label("layoutBlankCanvas", rect(12, 44, w - 24, 80), tr("Add a widget to start this view."), Object.assign({ wrap: true }, muted))]
		}));
	}
	return { nodes };
}
//#endregion
//#region src/features/administration/LayoutPreview.vue
var _hoisted_1$1 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_2$1 = {
	key: 3,
	class: "muted"
};
var _sfc_main$1 = {
	__name: "LayoutPreview",
	props: {
		frameNode: Object,
		sample: Object,
		layout: Object,
		rows: Array,
		ticket: String,
		project: String,
		searchType: String,
		selectedElement: String,
		editing: Boolean,
		error: String
	},
	emits: ["element", "geometry"],
	setup(__props, { emit: __emit }) {
		const ResultPresentation = asyncComponent(() => __vitePreload(() => import("./ConfiguredView.js").then((n) => n.o), __vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33])));
		const props = __props;
		const emit = __emit;
		const sampleScene = computed(() => scene(props.layout, props.sample, props.frameNode?.width || 1, props.frameNode?.height || 1, props.selectedElement, props.editing, appearance.language, window.innerWidth, location.origin));
		const sampleViews = computed(() => ({ canvasOverlay: {
			component: _sfc_main$3,
			props: {
				boxes: sampleScene.value.canvasBoxes || [],
				selected: props.selectedElement,
				onSelect: (name) => emit("element", name),
				onCommit: (value) => emit("geometry", value)
			}
		} }));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["layout-live-preview", __props.sample ? "layout-sample-preview" : "table-container"]) }, [
				__props.error ? (openBlock(), createElementBlock("p", _hoisted_1$1, toDisplayString(__props.error), 1)) : createCommentVNode("", true),
				__props.sample ? (openBlock(), createBlock(_sfc_main$2, {
					key: 1,
					scene: sampleScene.value,
					views: sampleViews.value,
					onEvent: _cache[0] || (_cache[0] = (event) => {
						if (event.type === "select") emit("element", event.name);
					})
				}, null, 8, ["scene", "views"])) : createCommentVNode("", true),
				__props.layout ? withDirectives((openBlock(), createBlock(unref(ResultPresentation), {
					key: 2,
					rows: __props.rows,
					ticket: __props.ticket,
					project: __props.project,
					"search-type": __props.searchType,
					"workspace-id": "layout-preview-" + __props.searchType,
					"item-layout": __props.layout,
					mode: __props.layout.collection === "grid" ? "tiles" : "continious",
					"group-mode": "none",
					"selected-keys": [],
					state: {},
					active: "",
					"read-only": "",
					editing: __props.editing,
					"selected-element": __props.selectedElement,
					onGeometry: _cache[1] || (_cache[1] = ($event) => _ctx.$emit("geometry", $event)),
					onElement: _cache[2] || (_cache[2] = ($event) => _ctx.$emit("element", $event))
				}, null, 8, [
					"rows",
					"ticket",
					"project",
					"search-type",
					"workspace-id",
					"item-layout",
					"mode",
					"editing",
					"selected-element"
				])), [[vShow, !__props.sample]]) : !__props.error ? (openBlock(), createElementBlock("p", _hoisted_2$1, toDisplayString(unref(t)("Loading interface...")), 1)) : createCommentVNode("", true)
			], 2);
		};
	}
};
//#endregion
//#region src/features/administration/LayoutEditor.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$2 },
	props: {
		ticket: String,
		project: String,
		initialFocus: Object,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved"],
	setup() {
		return { openHelp: inject("openHelp", null) };
	},
	data() {
		return {
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			searchType: "",
			catalog: [],
			view: "continuous_example",
			configuration: null,
			knownViews: [],
			context: null,
			source: "",
			xml: "",
			baseline: "",
			sampleItems: [],
			preview: null,
			liveInterface: null,
			checked: "",
			diff: "",
			error: "",
			sampleError: "",
			message: "",
			busy: false,
			uncertain: false,
			request: 0,
			previewRequest: 0,
			previewTimer: null,
			previewBusy: false,
			previewError: ""
		};
	},
	computed: {
		navigationParent() {
			return navigationParent(this.ui);
		},
		dirty() {
			return this.xml !== this.baseline || pending(this.ui) || this.uncertain;
		},
		editable() {
			return !!this.configuration && !this.busy && !this.uncertain && this.context?.ticket === this.ticket && this.context?.project === this.project && this.context?.searchType === this.searchType && this.context?.view === this.view;
		},
		typeOptions() {
			return this.catalog.filter((row) => row.__record_read__?.available !== false).map((row) => ({
				value: row.code,
				label: row.title || row.code
			}));
		},
		parsed() {
			try {
				return {
					tree: layoutTree(this.xml),
					error: ""
				};
			} catch (error) {
				return {
					tree: null,
					error: error.message
				};
			}
		},
		templates() {
			return (this.configuration?.layout_templates || []).map((row) => ({
				...row,
				tree: layoutTree(row.xml)
			}));
		},
		rawModel() {
			return {
				project: this.project,
				searchTypes: this.typeOptions,
				searchType: this.searchType,
				view: this.view,
				configuration: this.configuration,
				knownViews: this.knownViews,
				source: this.source,
				xml: this.xml,
				tree: this.parsed.tree,
				parseError: this.parsed.error,
				templates: this.templates,
				sampleItems: this.sampleItems,
				sampleError: this.sampleError,
				liveInterface: this.liveInterface,
				preview: this.preview,
				checked: this.checked,
				diff: this.diff,
				error: this.error || this.previewError,
				message: this.message,
				busy: this.busy,
				dirty: this.xml !== this.baseline || this.uncertain,
				uncertain: this.uncertain,
				canWrite: !!this.configuration && this.context?.ticket === this.ticket && this.context?.project === this.project && this.context?.searchType === this.searchType && this.context?.view === this.view,
				canLoad: !!this.ticket && !!this.searchType,
				assetBase: location.origin
			};
		},
		frameModel() {
			return model(this.rawModel, this.ui, appearance.language, this.viewport.width > 0 ? window.innerWidth : 1e3);
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language, !!this.toolbarTarget);
		},
		models() {
			return models(this.frameModel, appearance.language);
		},
		previewRows() {
			return this.sampleItems.map((item) => item.record);
		},
		previewViews() {
			return { itemResults: {
				component: _sfc_main$1,
				nodeProps: true,
				props: {
					sample: this.frameModel.samplePreview,
					rows: this.previewRows,
					ticket: this.ticket,
					project: this.project,
					searchType: this.searchType,
					layout: this.liveInterface?.table?.item_layout,
					error: this.error || this.previewError || this.sampleError,
					editing: this.ui.page !== "resolved",
					selectedElement: this.ui.page === "resolved" ? "" : this.ui.selected,
					onGeometry: (value) => this.dispatch({
						type: "geometry",
						value
					}),
					onElement: (name) => this.dispatch({
						type: "select",
						name
					})
				}
			} };
		}
	},
	mounted() {
		this.searchType = this.initialFocus?.searchType || this.typeOptions[0]?.value || "";
		this.view = this.initialFocus?.view || "continuous_example";
		this.loadCatalog();
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
		this.request++;
		clearTimeout(this.previewTimer);
		this.previewRequest++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		rawModel: {
			deep: false,
			handler() {
				const next = synchronize(this.ui, this.frameModel);
				if (next !== this.ui) {
					this.ui = next;
					this.revealSelection();
				}
			}
		},
		xml() {
			this.checked = "";
			this.preview = null;
			this.diff = "";
			if (this.xml !== this.baseline) this.message = "";
			this.schedulePreview();
		},
		project() {
			this.contextChanged();
		},
		ticket() {
			this.contextChanged();
		},
		initialFocus: {
			deep: true,
			handler(value) {
				if (!value || !this.canLeave()) return;
				this.searchType = value.searchType || this.searchType;
				this.view = value.view || this.view;
				this.reload();
			}
		}
	},
	methods: {
		t,
		async revealSelection() {
			await this.$nextTick();
			const index = this.models.layoutElements.findIndex((row) => row.name === this.ui.selected);
			this.$refs.frame?.focusListRow("layoutElementsList", index, "");
		},
		schedulePreview() {
			clearTimeout(this.previewTimer);
			const generation = ++this.previewRequest;
			this.previewError = "";
			this.previewTimer = setTimeout(async () => {
				if (!this.configuration || !this.xml || this.parsed.error || this.uncertain) return;
				const request = this.request, xml = this.xml;
				this.previewBusy = true;
				try {
					const result = await this.call("preview", {
						source_id: this.source === "" ? null : this.source,
						xml,
						revision: this.configuration.revision
					});
					if (generation === this.previewRequest && request === this.request) this.preview = this.liveInterface = result.interface;
				} catch (error) {
					if (generation === this.previewRequest && request === this.request) this.previewError = error.message;
				} finally {
					if (generation === this.previewRequest) this.previewBusy = false;
				}
			}, 250);
		},
		rowScene(list, record) {
			return row(list, record, this.frameModel, this.ui, appearance.language);
		},
		beforeUnload(event) {
			if (this.dirty || this.busy) {
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
		contextChanged() {
			this.request++;
			this.previewRequest++;
			clearTimeout(this.previewTimer);
			this.busy = false;
			this.catalog = [];
			this.configuration = null;
			this.knownViews = [];
			this.liveInterface = null;
			this.xml = this.baseline = "";
			this.ui = initial();
			this.uncertain = false;
			this.loadCatalog();
		},
		async loadCatalog() {
			if (!this.ticket || !this.project) return;
			const request = ++this.request;
			this.catalog = [];
			this.busy = true;
			this.error = "";
			try {
				const result = await widgetConfiguration("catalog", this.ticket, this.project, "", "");
				if (request !== this.request) return;
				if (!Array.isArray(result.stypes) || result.stypes.some((row) => !row || typeof row.code !== "string" || !row.code)) throw Error("Invalid Search Type catalog response");
				this.catalog = result.stypes;
				if (!this.typeOptions.some((row) => row.value === this.searchType)) this.searchType = this.typeOptions[0]?.value || "";
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
			if (request === this.request && !this.error) await this.reload();
		},
		call(action, values = {}) {
			const context = this.context;
			return widgetConfiguration(action, context.ticket, context.project, context.searchType, context.view, values);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			if (event.type === "select") await this.revealSelection();
			for (const command of result.commands) {
				switch (command.type) {
					case "reference":
						this.searchType = command.searchType;
						this.view = command.view;
						await this.reload(void 0, command);
						break;
					case "xml":
						if (this.editable) this.xml = command.value;
						break;
					case "context":
						this[command.field] = command.value;
						await this.reload();
						break;
					case "source":
						this.source = command.value;
						this.selectSource();
						break;
					case "newView":
						this.view = command.view;
						await this.reload(command.xml);
						break;
					case "check":
						await this.check();
						break;
					case "save":
						await this.save();
						break;
					case "reload":
						await this.reload();
						break;
					case "discard":
						await this.discard();
						break;
					case "openView":
						if (this.canLeave()) window.open(workspaceAddress(this.project, this.searchType, this.view), "_blank", "noopener");
						break;
					case "help":
						this.openHelp?.();
						break;
					default: throw Error("Unsupported layout command: " + command.type);
				}
				if (!this.error) this.ui = completed(this.ui, command);
			}
		},
		async reload(newXml, reference = null) {
			if (!this.ticket || !this.searchType || this.busy) return;
			if (!/^[A-Za-z_][\w.@-]{0,127}$/.test(this.view)) this.view = "continuous_example";
			const request = ++this.request;
			if (this.context?.project !== this.project || this.context?.searchType !== this.searchType) this.knownViews = [];
			this.context = {
				ticket: this.ticket,
				project: this.project,
				searchType: this.searchType,
				view: this.view
			};
			this.busy = true;
			this.configuration = null;
			this.liveInterface = null;
			this.error = this.sampleError = "";
			this.sampleItems = [];
			try {
				const result = await this.call("read");
				if (request !== this.request) return;
				if (reference && !(result.layout_views || []).includes(this.view)) throw Error("Referenced item layout is unavailable");
				if (reference?.source != null && reference.source !== "" && !result.sources.some((row) => row.id === reference.source)) throw Error("The original configuration source is unavailable");
				this.configuration = result;
				this.knownViews = result.layout_views || [];
				this.uncertain = false;
				this.source = reference?.source ?? result.sources[0]?.id ?? "";
				this.selectSource();
				if (typeof newXml === "string") {
					this.source = "";
					this.baseline = "";
					this.xml = newXml;
				}
				try {
					const context = this.context, rows = await rpc("query", [{
						ticket: context.ticket,
						project: context.project,
						language: "python"
					}, context.searchType], { limit: 3 });
					if (request !== this.request) return;
					if (rows.length) {
						const items = await resultItems(context.ticket, context.project, context.searchType, rows.map((row) => row.__search_key__));
						if (request === this.request) this.sampleItems = items.items;
					}
				} catch (error) {
					if (request === this.request) this.sampleError = error.message;
				}
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		selectSource() {
			const source = this.configuration?.sources.find((row) => row.id === this.source), inherited = this.configuration?.layers.find((row) => row.view === this.view && row.xml.includes("sobject-layout"));
			const blank = this.templates.find((row) => row.name === "blank");
			this.xml = this.baseline = source?.xml || inherited?.xml || (blank ? serialize(template(blank.tree, this.view)) : "");
			this.error = "";
			this.checked = "";
			this.preview = null;
			this.diff = "";
			this.message = "";
			this.schedulePreview();
		},
		async check() {
			if (!this.editable) return;
			const request = this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("preview", {
					source_id: this.source === "" ? null : this.source,
					xml: this.xml,
					revision: this.configuration.revision
				});
				if (request === this.request) {
					this.preview = this.liveInterface = result.interface;
					this.checked = this.xml;
					this.diff = result.diff;
				}
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		async save() {
			if (!this.editable || !this.dirty || this.checked !== this.xml || pending(this.ui)) return;
			const request = this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("save", {
					source_id: this.source === "" ? null : this.source,
					xml: this.xml,
					revision: this.configuration.revision
				});
				if (request !== this.request) return;
				this.configuration = result;
				this.source = result.sources[0]?.id ?? "";
				this.selectSource();
				this.message = "Layout saved";
				this.$emit("saved", result);
			} catch (error) {
				if (request === this.request) {
					this.uncertain = !error.status || error.status >= 500;
					this.error = this.uncertain ? "The save result is unknown. Refresh before trying again." : error.message;
				}
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		async discard() {
			if (this.uncertain) await this.reload();
			else if (this.configuration) this.selectSource();
			else this.xml = this.baseline;
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
var _hoisted_3 = {
	key: 0,
	class: "error",
	role: "alert"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "layout-editor frame-host",
		"aria-label": $options.t("Layout Editor"),
		"aria-busy": $data.busy
	}, [(openBlock(), createBlock(Teleport, {
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
		views: $options.previewViews,
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"views",
		"onEvent"
	]), $data.previewError ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($data.previewError), 1)) : createCommentVNode("", true)], 512)], 8, _hoisted_1);
}
var LayoutEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { LayoutEditor_default as default };

//# sourceMappingURL=LayoutEditor.js.map
import { I as resolveComponent, K as withDirectives, N as openBlock, c as vShow, g as createBlock, h as createBaseVNode, nt as normalizeStyle, p as Teleport, v as createElementBlock, w as inject, x as createVNode } from "./vue.js";
import { D as t, O as appearance, Y as _plugin_vue_export_helper_default } from "./index.js";
import { c as button, d as node, f as rect, l as label, n as _sfc_main$1, s as translate, t as observeFrameSizes, u as muted } from "./resize.js";
import { M as rpc, Y as widgetConfiguration, j as resultItems } from "./clipboard.js";
import { C as serialize, E as widgets, S as roles, T as variants, b as describe$2, v as actions, w as template, x as edit, y as binding } from "./App.js";
import { i as sectionSelector, n as notices, o as toolbar$1, r as policy, t as documentEvent } from "./admin.document.js";
import { t as form } from "./admin.form.js";
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
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs
var number = (value, fallback, min, max) => Number.isFinite(Number(value)) ? Math.max(min, Math.min(max, Number(value))) : fallback;
function variant(sample) {
	return sample.kind === "branch" ? (sample.branch || {}).kind || "versions" : sample.kind === "object" ? sample.depth ? "children" : "main" : sample.kind;
}
function visible(item, sample, layout, width) {
	const branch = sample.branch || {}, snapshot = sample.snapshot_display || {}, conditions = {
		desktop: width >= 700,
		mobile: width < 700,
		tree: layout.collection === "tree",
		"not-tree": layout.collection !== "tree",
		object: sample.kind === "object",
		"object-or-process": sample.kind === "object" || branch.kind === "process",
		"not-branch": sample.kind !== "branch",
		description: sample.kind !== "branch" && sample.kind !== "snapshot" && !!(sample.subtitle || (sample.record || {}).description),
		snapshot: sample.kind === "snapshot",
		branch: sample.kind === "branch",
		relation: branch.kind === "relation",
		"mobile-upload": sample.kind === "object" || branch.kind === "process"
	};
	return !item.hidden && (item.variant === "all" || item.variant === variant(sample)) && (item.when || []).every((key) => conditions[key]) && (item.kind !== "knowledge" || (sample.knowledge || []).length > 0) && (item.kind !== "snapshot-size" || snapshot.size !== void 0) && (item.kind !== "file-offline" || !snapshot.exists);
}
function tracks(value, count, width) {
	const tokens = String(value || "").trim().split(/\s+/), sizes = [], weights = [];
	let fixed = 0, weight = 0;
	for (let index = 0; index < count; index++) {
		const token = tokens.length === count ? tokens[index] : "1fr", pixels = /^\d+px$/.test(token) ? Number(token.slice(0, -2)) : 0, flex = /^\d+fr$/.test(token) ? Number(token.slice(0, -2)) : token === "auto" ? 1 : 0;
		sizes.push(pixels);
		weights.push(flex);
		fixed += pixels;
		weight += flex;
	}
	const scale = fixed > width ? width / fixed : 1;
	return sizes.map((value, index) => value ? value * scale : Math.max(0, width - fixed) * weights[index] / Math.max(1, weight));
}
function safeImage(value, base, local) {
	const text = String(value || "");
	if (!text || /[\u0000-\u0020\u007f\\]/.test(text) || text.indexOf("//") === 0) return "";
	if (text.charAt(0) === "/") return (base || "") + text;
	return /^(https?:|blob:|data:image\/(?:png|jpeg|webp|gif);base64,)/i.test(text) || local && /^file:/i.test(text) ? text : "";
}
function sample(model, ui, language) {
	const tr = (text) => translate(text, language), item = (model.sampleItems || [])[0] || {
		record: {
			name: tr("Example object"),
			description: tr("Example description")
		},
		title: tr("Example object"),
		subtitle: tr("Example description"),
		task_count: 3,
		note_count: 2
	}, kind = [
		"process",
		"relation",
		"versions"
	].indexOf(ui.sampleVariant) >= 0 ? "branch" : ["snapshot", "file"].indexOf(ui.sampleVariant) >= 0 ? ui.sampleVariant : "object";
	return Object.assign({}, item, {
		kind,
		depth: ui.sampleVariant === "children" ? 1 : 0,
		branch: kind === "branch" ? {
			kind: ui.sampleVariant,
			title: tr(ui.sampleVariant === "process" ? "Process" : "Related and child objects"),
			count: 3,
			relationship: "instance"
		} : void 0
	});
}
function describe$1(layout, sample, width, selected, language, screenWidth, assetBase, prefix, depth) {
	const tr = (text) => translate(text, language), nodes = [], namePrefix = prefix || "layoutPreview", level = depth || 0;
	if (level >= 8) return {
		nodes: [label(namePrefix + "Depth", rect(0, 0, width, 64), tr("Layout container depth exceeds 8"), {
			wrap: true,
			color: "error"
		})],
		height: 72
	};
	const elements = (layout.elements || []).filter((item) => visible(item, sample, layout, screenWidth || width)), snapshot = sample.snapshot_display || {}, record = sample.record || {}, title = sample.title || record.name || record.title || record.code || String(record.id || ""), subtitle = sample.subtitle || record.description || "";
	function draw(item, box, inner) {
		const id = namePrefix + "_" + item.name, children = [], options = item.options || {}, value = options.bind ? binding(options.bind, sample) : options.text || "", text = typeof value === "object" ? JSON.stringify(value) : String(value), color = item.tone === "muted" ? "secondaryText" : "primaryText", weight = item.tone === "strong" || item.kind === "title" ? 600 : 400;
		if (item.kind === "group") children.push(node("Box", id + "Group", rect(4, 4, Math.max(0, box.width - 8), Math.max(0, box.height - 8)), { children: inner ? inner.nodes : [] }));
		else if (item.kind === "view") {
			if (inner) {
				const owned = (nodes) => nodes.map((row) => Object.assign({}, row, {
					action: row.action && row.action.type === "select" ? {
						type: "select",
						name: item.name
					} : row.action,
					children: owned(row.children || [])
				}));
				children.push(node("Box", id + "View", rect(4, 4, box.width - 8, box.height - 8), { children: owned(inner.nodes) }));
			} else children.push(label(id + "ViewHelp", rect(4, 4, box.width - 8, box.height - 8), tr("Reusable view") + ": " + (options.view || "") + " · " + tr("Check and preview"), {
				wrap: true,
				color: "secondaryText"
			}));
		} else if (item.kind === "image") {
			const initials = title.split(/\s+/).map((part) => part.charAt(0)).slice(0, 2).join("").toUpperCase() || "?";
			children.push(node("Preview", id + "Image", rect(4, 4, Math.max(0, box.width - 8), Math.max(0, box.height - 8)), {
				source: safeImage(value, assetBase, options.bind === "node.preview.image" && sample.preview && sample.preview.local === true),
				initials,
				icon: "image",
				round: item.role === "preview",
				outlined: false,
				fit: options.fit || "cover"
			}));
		} else if (item.kind === "button" || item.kind === "link") {
			const badge = options.badge ? Number(binding(options.badge, sample)) : 0, caption = text || (item.kind === "button" ? tr({
				tasks: "Tasks",
				notes: "Notes",
				inspect: "Object details",
				operate: "Object actions",
				upload: "Add files",
				create: "Create related object",
				preview: "File preview",
				relations: "Relationship actions",
				link: "Link"
			}[options.action] || "Button") : options.href || tr("Link"));
			children.push(node("Button", id + "Button", rect(4, 4, Math.max(0, box.width - 8), Math.max(0, Math.min(38, box.height - 8))), {
				text: caption + (Number.isFinite(badge) && badge > 0 ? " · " + badge : ""),
				icon: options.icon || {
					tasks: "task",
					notes: "notes",
					upload: "upload",
					inspect: "search",
					relations: "link"
				}[options.action] || ""
			}));
		} else if (item.kind === "item-menu") children.push(node("Button", id + "Menu", rect(Math.max(0, box.width - 38), 0, Math.min(38, box.width), 38), {
			text: tr("Item actions"),
			icon: "more-vert",
			iconOnly: true
		}));
		else if (item.kind === "quick-actions" || item.kind === "relations") {
			const icons = item.kind === "relations" ? ["link", "add"] : [
				"preview",
				"download",
				"upload"
			], size = Math.min(32, box.width / icons.length);
			icons.forEach((icon, index) => children.push(node("Button", id + "Action_" + index, rect(index * size, 0, size, 32), {
				text: tr(item.kind === "relations" ? "Relationship actions" : "Snapshot actions"),
				icon,
				iconOnly: true
			})));
		} else {
			let content = text;
			if (item.kind === "title") content = text || title;
			else if (item.kind === "description") content = text || subtitle;
			else if (item.kind === "metadata") content = [
				sample.search_type_label || record.search_type || "",
				record.category || "",
				record.process || ""
			].filter(Boolean).join(" · ");
			else if (item.kind === "snapshot-details") content = [
				snapshot.version === void 0 ? "" : "v" + snapshot.version,
				snapshot.author || "",
				snapshot.context || ""
			].filter(Boolean).join(" · ");
			else if (item.kind === "snapshot-size") {
				const bytes = Number(snapshot.size) || 0, unit = bytes >= 1073741824 ? "GB" : bytes >= 1048576 ? "MB" : bytes >= 1024 ? "KB" : "B";
				content = (bytes / {
					GB: 1073741824,
					MB: 1048576,
					KB: 1024,
					B: 1
				}[unit]).toFixed(unit === "B" ? 0 : 1) + " " + unit;
			} else if (item.kind === "snapshot-summary") content = [
				snapshot.title || "",
				snapshot.description || "",
				snapshot.author || ""
			].filter(Boolean).join(" · ");
			else if (item.kind === "branch-summary") content = [(sample.branch || {}).title || "", String((sample.branch || {}).count || 0)].join(" · ");
			else if (item.kind === "file-offline") content = tr("File Offline");
			else if (item.kind === "knowledge") content = (sample.knowledge || []).map((row) => row.title || row.name || row.code || "").join(" · ");
			children.push(label(id + "Text", rect(6, 4, Math.max(0, box.width - 12), Math.max(0, box.height - 8)), content, {
				wrap: true,
				color,
				weight,
				fontRole: item.kind === "title" ? "section" : "body",
				align: item.align === "center" ? "center" : item.align === "end" ? "right" : "left"
			}));
		}
		if (item.kind === "group" || item.kind === "view" && inner) return node("Box", id, box, {
			background: selected === item.name ? "contentSelection" : "transparent",
			children: [node("Action", id + "Select", rect(0, 0, box.width, box.height), {
				text: item.title || item.name,
				normalColor: "transparent",
				selectedColor: "transparent",
				action: {
					type: "select",
					name: item.name
				}
			})].concat(children)
		});
		return node("Action", id, box, {
			text: item.title || item.name,
			selected: selected === item.name,
			normalColor: "transparent",
			selectedColor: "contentSelection",
			children,
			action: {
				type: "select",
				name: item.name
			}
		});
	}
	function container(parent, w, nesting) {
		if (nesting >= 8) return {
			nodes: [],
			height: 40
		};
		const definition = elements.find((item) => item.name === parent), items = elements.filter((item) => item.parent === parent), flow = definition ? definition.flow : layout.flow, columns = number(definition ? definition.columns : layout.columns, 12, 1, 12), result = [], placements = [];
		if (flow === "contents") {
			const copyX = items.some((item) => item.role === "preview") ? Math.min(96, w * .28) : 8;
			let cursor = 8;
			for (const item of items) {
				let box, child = item.kind === "group" && item.role !== "copy" ? container(item.name, Math.max(1, w - 16), nesting + 1) : item.kind === "view" && item.widget_layout ? describe$1(item.widget_layout, sample, Math.max(1, w - 16), selected, language, screenWidth, assetBase, namePrefix + "_" + item.name, nesting + 1) : null;
				if (item.role === "preview") box = rect(8, 8, Math.min(76, w * .24), 76);
				else if (item.role === "copy") {
					child = container(item.name, Math.max(1, w - copyX - 16), nesting + 1);
					box = rect(copyX, 8, Math.max(1, w - copyX - 8), child.height + 8);
					cursor = Math.max(cursor, box.height + 16);
				} else {
					const h = child ? child.height + 8 : item.role === "title-line" ? 36 : item.kind === "image" ? number(item.height, 76, 24, 1200) : item.kind === "description" ? 44 : 38;
					box = rect(8, cursor, w - 16, h);
					cursor += h + 4;
				}
				placements.push({
					item,
					box,
					child
				});
				cursor = Math.max(cursor, box.y + box.height + 8);
			}
			placements.sort((a, b) => (a.item.layer || 0) - (b.item.layer || 0)).forEach((row) => result.push(draw(row.item, row.box, row.child)));
			return {
				nodes: result,
				height: Math.max(92, cursor)
			};
		}
		const gap = 6, available = Math.max(1, w - gap * (columns - 1)), sizes = tracks(definition ? "" : layout.tracks, columns, available), rows = [];
		for (const item of items) {
			const start = number(item.row, 1, 1, 100) - 1, span = number(item.rows, 1, 1, 100), column = number(item.column, 1, 1, columns) - 1, columnsWide = number(item.span, 1, 1, columns - column), cellWidth = sizes.slice(column, column + columnsWide).reduce((a, b) => a + b, 0) + gap * (columnsWide - 1), child = item.kind === "group" ? container(item.name, Math.max(1, cellWidth - 8), nesting + 1) : item.kind === "view" && item.widget_layout ? describe$1(item.widget_layout, sample, Math.max(1, cellWidth - 8), selected, language, screenWidth, assetBase, namePrefix + "_" + item.name, nesting + 1) : null, h = child ? child.height + 8 : item.kind === "image" ? number(item.height, 40, 1, 1200) : 40;
			for (let index = start; index < start + span; index++) rows[index] = Math.max(rows[index] || 40, (h - gap * (span - 1)) / span);
			placements.push({
				item,
				start,
				span,
				column,
				columnsWide,
				cellWidth,
				child
			});
		}
		const sum = (values, start, end) => {
			let total = 0;
			for (let index = start; index < end; index++) total += values[index] || 40;
			return total;
		};
		placements.sort((a, b) => (a.item.layer || 0) - (b.item.layer || 0)).forEach((row) => {
			const x = sizes.slice(0, row.column).reduce((a, b) => a + b, 0) + gap * row.column, y = sum(rows, 0, row.start) + gap * row.start, h = sum(rows, row.start, row.start + row.span) + gap * (row.span - 1);
			result.push(draw(row.item, rect(x, y, row.cellWidth, h), row.child));
		});
		return {
			nodes: result,
			height: rows.length ? sum(rows, 0, rows.length) + gap * (rows.length - 1) : 64
		};
	}
	let body;
	if (layout.collection === "table") {
		const items = elements.filter((item) => !item.parent), total = items.reduce((sum, item) => sum + number(item.span, 1, 1, 12), 0) || 1;
		let x = 0;
		body = {
			nodes: [],
			height: 160
		};
		for (const item of items) {
			const w = width * number(item.span, 1, 1, 12) / total, child = item.kind === "group" ? container(item.name, Math.max(1, w - 8), level + 1) : item.kind === "view" && item.widget_layout ? describe$1(item.widget_layout, sample, Math.max(1, w - 8), selected, language, screenWidth, assetBase, namePrefix + "_" + item.name, level + 1) : null;
			body.height = Math.max(body.height, (child ? child.height : 108) + 52);
			body.nodes.push(label(namePrefix + "Header_" + item.name, rect(x, 0, w, 38), item.title || item.name, { weight: 600 }), draw(item, rect(x, 44, w, Math.max(108, child ? child.height : 0)), child));
			x += w;
		}
	} else body = container("", width, level);
	nodes.push.apply(nodes, body.nodes);
	return {
		nodes,
		height: body.height
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs
function initial() {
	return {
		page: "design",
		panel: "elements",
		selected: "",
		context: "",
		catalogWidth: 220,
		propertiesWidth: 330,
		sampleVariant: "main",
		newName: "custom_view",
		template: "continuous",
		text: {},
		confirmation: "",
		checking: false,
		error: ""
	};
}
function pending(ui) {
	return Object.keys(ui.text).length > 0;
}
function synchronize(ui, model) {
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
	if (next.checking && !model.busy) {
		if (model.checked && model.checked === model.xml) next.page = "resolved";
		next.checking = false;
	}
	return JSON.stringify(next) === JSON.stringify(ui) ? ui : next;
}
function change(next, model, event, commands) {
	try {
		const tree = edit(model.tree, model.view, event.name === void 0 ? next.selected : event.name, event.field, event.value), description = describe$2(tree, model.view);
		if (event.field === "add") next.selected = (description.elements[description.elements.length - 1] || {}).name || "";
		else if (event.field === "remove") next.selected = (description.elements[0] || {}).name || "";
		commands.push({
			type: "xml",
			value: serialize(tree)
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
	const document = documentEvent(ui, model, event);
	if (document) return document;
	if (model.busy || ui.confirmation) return {
		ui: next,
		commands
	};
	switch (event.type) {
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
		case "sampleVariant":
			next.sampleVariant = event.value;
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
					value: serialize(tree)
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
		case "context":
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
						xml: serialize(template(tree, name))
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
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.ui.mjs
var labels = {
	group: "Group",
	view: "Reusable view",
	text: "Text",
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
function model(raw, ui) {
	let layout = {
		elements: [],
		columns: 12,
		flow: "grid",
		collection: "grid",
		tracks: "",
		card_width: 280
	}, layoutError = raw.parseError ? "Invalid configuration XML" : "";
	if (!layoutError && raw.tree) try {
		layout = describe$2(raw.tree, raw.view);
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
function toolbar(model, ui, width, language) {
	const tr = (text) => translate(text, language), result = toolbar$1(model, ui, width, language), edit = policy(model).editable && !ui.confirmation;
	result.nodes = result.nodes.filter((row) => row.id !== "adminDocumentStatus");
	result.nodes.push(button("layoutCheck", rect(46, 0, 38, 38), tr("Check and preview"), "check", { type: "check" }, edit && !model.layoutError && !pending(ui), { iconOnly: true }), button("layoutHelp", rect(90, 0, 38, 38), tr("Layout guide"), "help", { type: "help" }, true, { iconOnly: true }), button("layoutOpenView", rect(134, 0, 38, 38), tr(model.externalView ? "Open view in browser" : "Open view"), "open-in-new", { type: "openView" }, edit && !model.dirty && !!(model.configuration && model.configuration.resolved && model.configuration.resolved.configured), { iconOnly: true }));
	return result;
}
function models(model) {
	return { layoutElements: model.layout.elements };
}
function row(list, record, model, ui, language) {
	const width = list.width - 16, tr = (text) => translate(text, language), id = "layoutElement_" + record.name;
	return { nodes: [node("Action", id, rect(0, 0, width, 70), {
		text: record.title || record.name,
		selected: ui.selected === record.name,
		normalColor: "surfaceContainerHigh",
		selectedColor: "contentSelection",
		dragValue: policy(model).editable && !pending(ui) ? record.name : null,
		dragStartAction: {
			type: "select",
			name: record.name
		},
		children: [label(id + "Title", rect(record.parent ? 22 : 10, 4, width - (record.parent ? 32 : 20), 28), (record.parent ? "↳ " : "") + (record.title || record.name), { weight: 600 }), label(id + "Kind", rect(10, 36, width - 20, 24), tr(labels[record.kind] || record.kind), muted)],
		action: {
			type: "select",
			name: record.name
		}
	})] };
}
function propertyFields(model, ui, language) {
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
		if (!item.options.bind) fields.push(text("option:text", item.kind === "image" ? "Image URL" : "Text", item.options.text || ""));
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
	if (item.kind === "view") fields.push(text("option:view", "Reusable view", item.options.view || ""));
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
	}, choice("variant", "Item variant", item.variant, choices(variants, language)), text("option:bind", "Custom data binding", item.options.bind || ""));
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
	const notice = notices(noticeModel, ui, width, language, void 0, ui.confirmation === "remove" ? "Remove element" : void 0), nodes = notice.nodes;
	let y = notice.top;
	nodes.push(label("layoutGuideHeading", rect(0, y, width, 28), tr("Build your own view"), {
		fontRole: "title",
		weight: 600
	}), label("layoutGuideText", rect(0, y + 34, width, width < 520 ? 62 : 36), tr("1. Choose a starting point · 2. Arrange elements · 3. Check and save"), Object.assign({ wrap: true }, muted)));
	y += width < 520 ? 104 : 78;
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
		const clean = !model.busy && !model.dirty && !model.uncertain, configuration = model.configuration || {}, views = configuration.layout_views || [
			"continuous_example",
			"table_example",
			"cards_example"
		], sourceOptions = (configuration.sources || []).map((row) => ({
			value: row.id,
			label: String(row.id) + " · " + tr("Priority") + " " + (row.priority === null ? "" : row.priority)
		})).concat([{
			value: "",
			label: tr("New override")
		}]);
		const fields = [
			{
				kind: "Heading",
				id: "layoutContextHeading",
				title: "Configuration"
			},
			{
				kind: "Choice",
				id: "layoutSearchType",
				title: "Search Type",
				options: model.searchTypes || [],
				props: {
					value: model.searchType,
					enabled: clean,
					action: {
						type: "context",
						field: "searchType"
					}
				}
			},
			{
				kind: "Choice",
				id: "layoutView",
				title: "Configuration view",
				options: views.map((value) => ({
					value,
					label: tr({
						continuous_example: "Tree example",
						table_example: "Table example",
						cards_example: "Cards example"
					}[value] || value)
				})),
				props: {
					value: model.view,
					enabled: clean,
					action: {
						type: "context",
						field: "view"
					}
				}
			},
			{
				kind: "Choice",
				id: "layoutSource",
				title: "Configuration source",
				options: sourceOptions,
				props: {
					value: model.source,
					enabled: clean,
					action: { type: "source" }
				}
			},
			{
				kind: "Heading",
				id: "layoutNewViewHeading",
				title: "Create custom view",
				description: "Start from a template or copy this view. Give your view a unique name."
			},
			{
				id: "layoutNewName",
				title: "View name",
				props: {
					text: ui.newName,
					enabled: edit && clean,
					action: { type: "newName" }
				}
			},
			{
				kind: "Choice",
				id: "layoutTemplate",
				title: "Layout template",
				options: [
					{
						value: "blank",
						label: tr("Blank view")
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
					},
					{
						value: "copy",
						label: tr("Copy current view")
					}
				],
				props: {
					value: ui.template,
					enabled: edit && clean,
					action: { type: "template" }
				}
			},
			{
				kind: "Button",
				id: "layoutCreateView",
				title: "Create custom view",
				props: {
					icon: "add",
					enabled: edit && clean,
					action: { type: "newView" }
				}
			}
		];
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
		const body = form(fields, width - 16, language, edit);
		nodes.push(node("Scroll", "layoutConfigurationScroll", rect(0, y, width, h), {
			contentHeight: body.height,
			scrollbarId: "layoutConfigurationScrollBar",
			children: body.nodes
		}));
		return { nodes };
	}
	if (ui.page === "resolved") {
		const resolved = model.preview && (model.preview.item_layout || (model.preview.table || {}).item_layout);
		if (!resolved) {
			nodes.push(label("layoutResolvedHelp", rect(12, y, width - 24, 96), tr("Check and preview the draft before saving."), Object.assign({ wrap: true }, muted)));
			return { nodes };
		}
		const children = [label("layoutResolvedNotice", rect(0, 0, width - 16, 44), tr("Read-only preview. Changes have not been saved."), Object.assign({ wrap: true }, muted))];
		let top = 52;
		(model.sampleItems && model.sampleItems.length ? model.sampleItems : [sample(model, ui, language)]).forEach((sample, index) => {
			const body = describe$1(resolved, sample, width - 32, "", language, width, model.assetBase, "layoutResolved_" + index);
			children.push(node("Box", "layoutResolvedItem_" + index, rect(0, top, width - 16, body.height + 16), {
				background: "surfaceContainerLow",
				border: "outlineVariant",
				children: [node("Box", "layoutResolvedContent_" + index, rect(8, 8, width - 32, body.height), { children: body.nodes })]
			}));
			top += body.height + 28;
		});
		nodes.push(node("Scroll", "layoutResolvedScroll", rect(0, y, width, h), {
			contentHeight: top,
			scrollbarId: "layoutResolvedScrollBar",
			children
		}));
		return { nodes };
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
	const wide = width >= 1e3, left = wide ? Math.min(ui.catalogWidth, width * .24) : width, properties = wide ? Math.min(ui.propertiesWidth, width * .34) : width;
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
		const w = left, children = [
			label("layoutElementsHeading", rect(12, 8, w - 24, 28), tr("Elements"), { weight: 600 }),
			node("Choice", "layoutAddWidget", rect(12, 44, w - 24, 38), {
				label: tr("Add widget"),
				value: "",
				options: [{
					value: "",
					label: tr("Add widget")
				}].concat(choices(widgets, language)),
				enabled: edit && !pending(ui),
				action: { type: "add" }
			}),
			node("List", "layoutElementsList", rect(12, 90, w - 24, bodyHeight - 146), {
				source: "layoutElements",
				keyField: "name",
				rowHeight: 74,
				scrollbarId: "layoutElementsScrollBar"
			}),
			button("layoutEarlier", rect(12, bodyHeight - 44, (w - 32) / 2, 36), tr("Move element earlier"), "chevron-up", {
				type: "change",
				field: "order",
				value: -1
			}, edit && !!selected && !pending(ui), { iconOnly: true }),
			button("layoutLater", rect((w + 8) / 2, bodyHeight - 44, (w - 32) / 2, 36), tr("Move element later"), "chevron-down", {
				type: "change",
				field: "order",
				value: 1
			}, edit && !!selected && !pending(ui), { iconOnly: true })
		];
		nodes.push(node("Box", "layoutElementsPanel", rect(0, y, w, bodyHeight), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
		if (wide) nodes.push(node("Splitter", "layoutElementsSplit", rect(w, y, 10, bodyHeight), {
			text: tr("Elements panel width"),
			value: w,
			min: 180,
			max: Math.min(420, width * .24),
			action: { type: "catalogSplit" }
		}));
	}
	if (wide || ui.panel === "settings") {
		const w = properties, x = wide ? width - w : 0, fields = propertyFields(model, ui, language), body = form(fields, w - 40, language, edit && !pending(ui));
		if (selected) {
			body.nodes.push(button("layoutRemoveElement", rect(0, body.height, w - 40, 38), tr("Remove element"), "delete", { type: "remove" }, edit && !pending(ui)));
			body.height += 46;
		} else {
			body.nodes.push(label("layoutSelectHelp", rect(0, 0, w - 40, 120), tr("Select an element or add a new widget."), Object.assign({ wrap: true }, muted)));
			body.height = 128;
		}
		nodes.push(node("Box", "layoutSettingsPanel", rect(x, y, w, bodyHeight), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [node("Scroll", "layoutSettingsScroll", rect(12, 12, w - 24, bodyHeight - 24), {
				contentHeight: body.height,
				resetKey: ui.selected,
				scrollbarId: "layoutSettingsScrollBar",
				children: body.nodes
			})]
		}));
		if (wide) nodes.push(node("Splitter", "layoutSettingsSplit", rect(x - 10, y, 10, bodyHeight), {
			text: tr("Element settings width"),
			value: w,
			min: 240,
			max: Math.min(520, width * .34),
			reverse: true,
			action: { type: "propertiesSplit" }
		}));
	}
	if (wide || ui.panel === "preview") {
		const x = wide ? left + 10 : 0, w = wide ? Math.max(1, width - left - properties - 20) : width, children = [label("layoutPreviewHeading", rect(12, 8, w - 24, 28), tr("Item preview"), { weight: 600 }), node("Choice", "layoutSampleVariant", rect(12, 44, w - 24, 38), {
			label: tr("Preview item type"),
			value: ui.sampleVariant,
			options: choices(variants.filter((value) => value !== "all"), language),
			action: { type: "sampleVariant" }
		})];
		const previewWidth = Math.max(1, Math.min(w - 40, layout.collection === "grid" ? numberWidth(layout.card_width) : w - 40)), body = describe$1(layout, sample(model, ui, language), previewWidth, ui.selected, language, width, model.assetBase), previewNodes = [node("Box", "layoutPreviewItem", rect(0, 0, previewWidth, body.height + 16), {
			background: "surfaceContainerHigh",
			children: body.nodes
		})];
		let top = body.height + 28;
		if (!layout.elements.length) {
			previewNodes.push(label("layoutAddHelp", rect(0, top, w - 40, 90), tr("Add an image, text or button to begin."), Object.assign({ wrap: true }, muted)));
			top += 98;
		}
		if (selected) {
			const parent = layout.elements.find((row) => row.name === selected.parent), grid = (parent ? parent.flow : layout.flow) === "grid", columns = parent ? parent.columns : layout.columns;
			if (grid) {
				const count = Math.min(12, Math.max(4, ...layout.elements.filter((row) => row.parent === selected.parent).map((row) => row.row + row.rows))), cell = (w - 40) / Math.max(1, columns);
				previewNodes.push(label("layoutGridHeading", rect(0, top, w - 40, 28), tr("Place on the grid"), { weight: 600 }));
				top += 36;
				for (let row = 1; row <= count; row++) for (let column = 1; column <= columns; column++) previewNodes.push(button("layoutGrid_" + row + "_" + column, rect((column - 1) * cell, top + (row - 1) * 32, Math.max(1, cell - 3), 29), String((row - 1) * columns + column), "", {
					type: "move",
					row,
					column
				}, edit && !pending(ui), {
					highlighted: selected.row === row && selected.column === column,
					dropAction: {
						type: "drop",
						row,
						column
					}
				}));
				top += count * 32 + 8;
				const moves = [
					[
						"up",
						-1,
						0,
						"chevron-up"
					],
					[
						"down",
						1,
						0,
						"chevron-down"
					],
					[
						"left",
						0,
						-1,
						"chevron-left"
					],
					[
						"right",
						0,
						1,
						"chevron-right"
					]
				], size = (w - 58) / 4;
				moves.forEach((move, index) => previewNodes.push(button("layoutMove_" + move[0], rect(index * (size + 6), top, size, 36), tr({
					up: "Move up",
					down: "Move down",
					left: "Move left",
					right: "Move right"
				}[move[0]]), move[3], {
					type: "move",
					row: selected.row + move[1],
					column: selected.column + move[2]
				}, edit && !pending(ui), { iconOnly: true })));
				top += 44;
			}
		}
		children.push(node("Scroll", "layoutPreviewScroll", rect(12, 90, w - 24, bodyHeight - 102), {
			contentHeight: top,
			scrollbarId: "layoutPreviewScrollBar",
			children: previewNodes
		}));
		nodes.push(node("Box", "layoutPreviewPanel", rect(x, y, w, bodyHeight), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
	}
	return { nodes };
}
function numberWidth(value) {
	return Number.isFinite(Number(value)) ? Math.max(1, Math.min(1200, Number(value))) : 280;
}
//#endregion
//#region src/features/administration/LayoutEditor.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		searchTypes: Array,
		initialFocus: Object,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved", "open-view"],
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
			view: "continuous_example",
			configuration: null,
			context: null,
			source: "",
			xml: "",
			baseline: "",
			sampleItems: [],
			preview: null,
			checked: "",
			diff: "",
			error: "",
			sampleError: "",
			message: "",
			busy: false,
			uncertain: false,
			request: 0
		};
	},
	computed: {
		dirty() {
			return this.xml !== this.baseline || pending(this.ui) || this.uncertain;
		},
		editable() {
			return !!this.configuration && !this.busy && !this.uncertain && this.context?.ticket === this.ticket && this.context?.project === this.project && this.context?.searchType === this.searchType && this.context?.view === this.view;
		},
		typeOptions() {
			return (this.searchTypes || []).filter((row) => row.__record_read__?.available !== false).map((row) => ({
				value: row.search_type,
				label: row.title || row.search_type
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
				source: this.source,
				xml: this.xml,
				tree: this.parsed.tree,
				parseError: this.parsed.error,
				templates: this.templates,
				sampleItems: this.sampleItems,
				sampleError: this.sampleError,
				preview: this.preview,
				checked: this.checked,
				diff: this.diff,
				error: this.error,
				message: this.message,
				busy: this.busy,
				dirty: this.xml !== this.baseline || this.uncertain,
				uncertain: this.uncertain,
				canWrite: !!this.configuration && this.context?.ticket === this.ticket && this.context?.project === this.project && this.context?.searchType === this.searchType && this.context?.view === this.view,
				canLoad: !!this.ticket && !!this.searchType,
				assetBase: location.origin,
				externalView: false
			};
		},
		frameModel() {
			return model(this.rawModel, this.ui);
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		models() {
			return models(this.frameModel);
		}
	},
	mounted() {
		this.searchType = this.initialFocus?.searchType || this.typeOptions[0]?.value || "";
		this.view = this.initialFocus?.view || "continuous_example";
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
		this.observer?.disconnect();
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		rawModel: {
			deep: false,
			handler() {
				const next = synchronize(this.ui, this.frameModel);
				if (next !== this.ui) this.ui = next;
			}
		},
		xml() {
			this.checked = "";
			this.preview = null;
			this.diff = "";
			if (this.xml !== this.baseline) this.message = "";
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
			if (this.dirty || this.busy) {
				this.error = "Save or discard layout changes before leaving.";
				return false;
			}
			return true;
		},
		contextChanged() {
			this.request++;
			this.busy = false;
			this.configuration = null;
			this.xml = this.baseline = "";
			this.ui = initial();
			this.uncertain = false;
			this.reload();
		},
		call(action, values = {}) {
			const context = this.context;
			return widgetConfiguration(action, context.ticket, context.project, context.searchType, context.view, values);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) {
				switch (command.type) {
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
						if (this.canLeave()) this.$emit("open-view", {
							project: this.project,
							searchType: this.searchType,
							view: this.view,
							title: this.view
						});
						break;
					case "help":
						this.openHelp?.();
						break;
					default: throw Error("Unsupported layout command: " + command.type);
				}
				if (!this.error) this.ui = completed(this.ui, command);
			}
		},
		async reload(newXml) {
			if (!this.ticket || !this.searchType || this.busy) return;
			if (!/^[A-Za-z_][\w.@-]{0,127}$/.test(this.view)) this.view = "continuous_example";
			const request = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project,
				searchType: this.searchType,
				view: this.view
			};
			this.busy = true;
			this.configuration = null;
			this.error = this.sampleError = "";
			this.sampleItems = [];
			try {
				const result = await this.call("read");
				if (request !== this.request) return;
				this.configuration = result;
				this.uncertain = false;
				this.source = result.sources[0]?.id ?? "";
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
					this.preview = result.interface;
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
var LayoutEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { LayoutEditor_default as default };

//# sourceMappingURL=LayoutEditor.js.map
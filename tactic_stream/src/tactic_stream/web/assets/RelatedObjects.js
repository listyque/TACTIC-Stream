import { n as arrange, r as __exportAll$1 } from "./ObjectFieldFrame.js";
import { A as onMounted, E as nextTick, F as resolveComponent, G as withCtx, H as watch, I as resolveDirective, K as withDirectives, L as resolveDynamicComponent, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, T as mergeProps, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, v as createSlots, y as createTextVNode } from "./vue.js";
import { D as spacing, R as BusyIndicator_default, T as metrics, _ as controls, a as _sfc_main$17, b as fontFamily, o as t, s as appearance, t as _sfc_main$16, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { A as rpc, a as __vitePreload, b as objectStatus, ht as serverTimestamp, mt as serverClock, v as objectDeletion, yt as mobile } from "./index.js";
import { G as button, H as observeFrameSizes, J as muted, K as label, O as ItemPreview_default, P as _sfc_main$19, Q as virtualRange, U as _sfc_main$20, X as rect, Y as node, Z as revealListOffset, a as _sfc_main$21, d as javascriptTokens, f as pythonTokens, p as xmlTokens, t as _sfc_main$18, w as translate } from "./FrameView.js";
import { n as qtLabelTextWidth } from "./textMetrics.js";
import { j as escapeHtml$1, u as _sfc_main$22, v as timestampLabel, x as browserLink } from "./admin.document.js";
import { f as summary } from "./file_values.js";
import { s as RelatedObjects_default } from "./ConfiguredView.js";
import { t as _sfc_main$23 } from "./VirtualCollection.js";
import { t as _sfc_main$24 } from "./ContentLoadingOverlay.js";
//#region ../src/tactic_stream/shared_ui/controls/buttons/metrics.mjs
function buttonWidth(advance, icon = false) {
	const metrics = controls.button;
	return Math.max(metrics.minimumWidth, Math.ceil(advance) + metrics.padding + (icon ? metrics.iconPadding + metrics.iconSize + metrics.spacing : metrics.padding));
}
function actionLayout(actions, width, measuredWidths = []) {
	const widths = actions.map((action, index) => Math.min(width, measuredWidths[index] || buttonWidth(action.text.length * 7, !!action.icon)));
	const total = widths.reduce((sum, value) => sum + value, 0) + Math.max(0, widths.length - 1) * 8, stacked = total > width;
	let x = Math.max(0, width - total);
	const positions = widths.map((item, index) => {
		const bounds = {
			x: stacked ? width - item : x,
			y: stacked ? index * 44 : 0,
			width: item,
			height: 38
		};
		x += item + 8;
		return bounds;
	});
	return {
		widths,
		total,
		stacked,
		height: (stacked ? actions.length : 1) * 44,
		positions
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/table/record.parts.mjs
function key$1(item) {
	return JSON.stringify([item.editorPath, item.form.searchKey || "readonly"]);
}
function values(form) {
	const result = {};
	for (const field of form.fields) result[field.name] = field.value;
	return result;
}
function entry(store, item) {
	return store[key$1(item)] || {
		form: item.form,
		values: values(item.form),
		busy: false,
		uncertain: false,
		error: ""
	};
}
function dirty(state) {
	return JSON.stringify(state.values) !== JSON.stringify(values(state.form));
}
function find(document, identity) {
	function walk(items) {
		for (const item of items || []) {
			if (item.kind === "form" && key$1(item) === identity) return item;
			const nested = walk(item.children);
			if (nested) return nested;
		}
		return null;
	}
	return walk(document.layoutNodes) || walk(document.layoutDetail?.layoutNodes);
}
function change(store, document, action) {
	const item = find(document, action.key);
	if (!item) return { store };
	const current = entry(store, item), next = Object.assign({}, store);
	if (current.busy || item.form.readOnly) return { store };
	if (action.intent === "cancel") {
		if (!current.uncertain) delete next[action.key];
	} else if (action.intent === "value" && !current.uncertain) {
		const field = current.form.fields.find((field) => field.name === action.name);
		if (!field || field.readOnly) return { store };
		if (!next[action.key] && Object.keys(next).length >= 20) throw Error("Finish or discard another form draft first");
		next[action.key] = Object.assign({}, current, {
			values: Object.assign({}, current.values, { [action.name]: action.value }),
			error: ""
		});
	} else if (action.intent === "save" && dirty(current) && !current.uncertain && !current.stale || action.intent === "check" && current.uncertain) {
		const changed = {};
		for (const field of current.form.fields) if (!field.readOnly && current.values[field.name] !== field.value) changed[field.name] = current.values[field.name];
		if (!Object.keys(changed).length) return { store };
		next[action.key] = Object.assign({}, current, {
			busy: true,
			error: ""
		});
		return {
			store: next,
			command: Object.assign({}, item.form.scope, {
				action: action.intent,
				values: changed,
				expected_revision: current.form.expectedRevision,
				config_revision: current.form.configRevision
			})
		};
	}
	return { store: next };
}
function settled(store, identity, result, failure) {
	if (!store[identity]) return store;
	const next = Object.assign({}, store), state = next[identity];
	if (result?.state === "saved") delete next[identity];
	else next[identity] = Object.assign({}, state, {
		busy: false,
		uncertain: !!failure?.uncertain,
		stale: result?.state === "conflict",
		error: failure?.message || (result?.state === "unchanged" ? "Changes were not saved. You can save again." : "Record changed. Reload before saving.")
	});
	return next;
}
function interrupted(store) {
	let next = store;
	for (const identity of Object.keys(store)) if (store[identity].busy) next = settled(next, identity, null, {
		message: "The page changed while a save was pending. Check saved state.",
		uncertain: true
	});
	return next;
}
function describe$4(item, id, width, store, language, enabled) {
	const state = entry(store, item), tr = (text) => translate(text, language), children = [];
	const event = (intent, extra = {}) => Object.assign({
		type: "record-form",
		intent,
		key: key$1(item)
	}, extra);
	let y = 0;
	if (item.text) {
		children.push(label(id + "_title", rect(0, y, width, 28), item.text, { weight: 600 }));
		y += 36;
	}
	if (state.form.hint) {
		children.push(label(id + "_hint", rect(0, y, width, 48), tr(state.form.hint), {
			wrap: true,
			color: "secondaryText"
		}));
		y += 56;
	}
	const layout = arrange(width, state.form.fields.map((field) => 24 + (field.type === "multiline" ? 88 : 36)), item.min_cell_width || 200, item.columns || 3, item.gap ?? 12);
	const top = y;
	for (const [index, field] of state.form.fields.entries()) {
		const box = layout.cells[index], x = box.x, fieldWidth = box.width;
		y = top + box.y;
		const name = id + "_field_" + field.name, active = enabled && !state.busy && !state.uncertain && !state.stale && !field.readOnly;
		children.push(label(name + "_label", rect(x, y, fieldWidth, 20), field.title + (field.required ? " *" : ""), { color: "secondaryText" }));
		y += 24;
		const value = state.values[field.name], action = event("value", { name: field.name });
		if (field.readOnly) children.push(label(name, rect(x, y, fieldWidth, 32), value == null ? "—" : String(value)));
		else if (field.type === "select") children.push(node("Choice", name, rect(x, y, fieldWidth, 36), {
			value: value == null ? "" : String(value),
			options: field.options.map((option) => ({
				value: String(option.value),
				label: option.label
			})),
			enabled: active,
			action
		}));
		else if (field.type === "bool") children.push(node("CheckBox", name, rect(x, y, fieldWidth, 36), {
			checked: !!value,
			text: field.title,
			enabled: active,
			action
		}));
		else if (["date", "datetime-local"].includes(field.type)) children.push(node("DateChoice", name, rect(x, y, fieldWidth, 36), {
			text: value || "",
			includeTime: field.type === "datetime-local",
			label: field.title,
			enabled: active,
			action
		}));
		else children.push(node(field.type === "multiline" ? "Area" : "Field", name, rect(x, y, fieldWidth, field.type === "multiline" ? 88 : 36), {
			text: value == null ? "" : String(value),
			inputType: field.type === "date" ? "date" : field.type === "datetime-local" ? "datetime-local" : "text",
			enabled: active,
			action
		}));
	}
	y = top + layout.height + 12;
	if (state.error) {
		children.push(label(id + "_error", rect(0, y, width, 48), tr(state.error), {
			color: "error",
			wrap: true
		}));
		y += 56;
	}
	if (!item.form.readOnly) {
		const w = Math.min(150, (width - 8) / 2), active = enabled && !state.busy;
		children.push(button(id + "_save", rect(0, y, w, 36), tr(state.uncertain ? "Check saved state" : "Save"), state.uncertain ? "refresh" : "save", event(state.uncertain ? "check" : "save"), active && (state.uncertain || !state.stale && dirty(state)), { highlighted: true }));
		children.push(button(id + "_cancel", rect(w + 8, y, w, 36), tr("Cancel"), "close", event("cancel"), active && !state.uncertain && dirty(state)));
		y += 44;
	}
	return {
		children,
		height: y
	};
}
function field(item, id, width) {
	const children = [], value = item.value, hasValue = value !== null && value !== void 0;
	let text = hasValue ? String(value) : "—", y = 0;
	if (item.format === "date" && hasValue) text = text.slice(0, 10);
	if (item.format === "datetime" && hasValue) text = text.replace("T", " ").slice(0, 19);
	if (hasValue && item.suffix) text += item.suffix;
	if (item.text) {
		children.push(label(id + "_label", rect(0, 0, width, 20), item.text, { color: "secondaryText" }));
		y = 24;
	}
	if (item.format === "badge") children.push(node("StatusChip", id, rect(0, y, Math.min(width, Math.max(80, text.length * 8 + 24)), 28), {
		text,
		accent: item.textColor || "contentAccent",
		dense: true,
		enabled: true
	}));
	else children.push(label(id, rect(0, y, width, 28), text, {
		fontRole: item.textRole || "body",
		color: item.textColor || "primaryText",
		weight: item.textWeight || 400
	}));
	if (item.format === "progress") {
		const percent = hasValue ? Math.max(0, Math.min(100, Number(value))) : 0;
		children.push(node("Box", id + "_track", rect(0, y + 30, width, 4), {
			background: "outlineVariant",
			radius: 2
		}));
		children.push(node("Box", id + "_progress", rect(0, y + 30, width * percent / 100, 4), {
			background: item.progressColor || "contentAccent",
			radius: 2
		}));
		y += 10;
	}
	return {
		children,
		height: y + 32
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs
var widgets = [
	"group",
	"view",
	"text",
	"field",
	"title",
	"description",
	"image",
	"link",
	"button",
	"metadata",
	"snapshot-details",
	"snapshot-size",
	"snapshot-summary",
	"branch-summary",
	"file-offline",
	"item-menu",
	"knowledge",
	"quick-actions",
	"relations"
];
var roles = {
	"": "None",
	preview: "Preview",
	copy: "Object information",
	"title-line": "Heading",
	"title-actions": "Snapshot actions",
	description: "Description",
	metadata: "Metadata",
	actions: "Actions",
	"hover-actions": "Actions on hover",
	communication: "Tasks and notes",
	"task-button": "Tasks",
	"note-button": "Notes",
	"mobile-actions": "Mobile actions",
	"file-offline": "File Offline"
};
var actions = [
	"inspect",
	"operate",
	"preview",
	"tasks",
	"notes",
	"upload",
	"create",
	"link",
	"relations"
];
var variants = [
	"all",
	"main",
	"children",
	"process",
	"relation",
	"versions",
	"snapshot",
	"file"
];
var children$1 = (node) => (node.children || []).filter((child) => child.type === 1);
var get = (node, key) => {
	const pair = (node.attributes || []).find((pair) => pair[0] === key);
	return pair ? pair[1] : "";
};
function set(node, key, value) {
	const index = (node.attributes || []).findIndex((pair) => pair[0] === key);
	if (value === "") {
		if (index >= 0) node.attributes.splice(index, 1);
	} else if (index >= 0) node.attributes[index][1] = String(value);
	else (node.attributes || (node.attributes = [])).push([key, String(value)]);
}
var element = (name, attributes, content) => ({
	type: 1,
	name,
	attributes: attributes || [],
	children: content || []
});
function root(tree) {
	const node = tree.type === 9 ? children$1(tree)[0] : tree;
	if (!node || node.name !== "config") throw Error("Invalid configuration XML");
	return node;
}
function viewOf(tree, view) {
	return children$1(root(tree)).find((node) => node.name === view || node.name === "view" && get(node, "name") === view);
}
function content(node) {
	return [3, 4].indexOf(node.type) >= 0 ? node.text || "" : (node.children || []).map(content).join("");
}
function describe$3(tree, view) {
	const node = viewOf(tree, view);
	if (!node || get(node, "layout") !== "sobject-layout") throw Error("Select a SObject layout configuration");
	const elements = children$1(node).filter((child) => child.name === "element").map((item) => {
		const display = children$1(item).find((child) => child.name === "display"), options = {};
		for (const option of display ? children$1(display) : []) options[option.name] = content(option);
		const result = {
			name: get(item, "name"),
			title: get(item, "title") || get(item, "name"),
			kind: display ? get(display, "class") || get(display, "widget") : "",
			options,
			parent: get(item, "parent"),
			variant: get(item, "variant") || "all",
			search_type: get(item, "search_type"),
			role: get(item, "role"),
			tag: get(item, "tag") || "div",
			flow: get(item, "flow") || "grid",
			when: get(item, "when").split(" ").filter(Boolean),
			layer: Number(get(item, "layer") || 0),
			hidden: [
				"true",
				"1",
				"yes",
				"on"
			].indexOf(get(item, "hidden")) >= 0,
			align: get(item, "align") || "stretch",
			tone: get(item, "tone") || "normal"
		};
		for (const key of [
			"row",
			"column",
			"span",
			"rows",
			"columns",
			"height"
		]) result[key] = Number(get(item, key) || {
			span: 12,
			columns: 12,
			height: 40
		}[key] || 1);
		for (const key of ["padding", "margin"]) {
			const value = get(item, key);
			if (value) result[key] = value.split(/\s+/).map(Number);
		}
		if (get(item, "gap") !== "") result.gap = Number(get(item, "gap"));
		return result;
	});
	const result = {
		collection: get(node, "collection") || "grid",
		flow: get(node, "flow") || "grid",
		columns: Number(get(node, "columns") || 12),
		tracks: get(node, "tracks"),
		gap: get(node, "gap") === "" ? 6 : Number(get(node, "gap")),
		card_width: Number(get(node, "card_width") || 280),
		elements
	};
	if (get(node, "navigation")) result.navigation = JSON.parse(get(node, "navigation"));
	return result;
}
function serialize(node, pretty = false) {
	if (pretty) {
		const whitespace = (item) => item.type === 3 && !String(item.text || "").trim();
		function format(item, depth) {
			if (item.type === 9) return (item.children || []).filter((child) => !whitespace(child)).map((child) => format(child, 0)).join("\n");
			if (item.type !== 1) return serialize(item);
			const children = item.children || [];
			if ((item.attributes || []).some(([name, value]) => name === "xml:space" && value === "preserve") || children.some((child) => child.type === 4 || child.type === 3 && !whitespace(child))) return serialize(item);
			const nested = children.filter((child) => !whitespace(child));
			if (!nested.length) return serialize(item);
			return serialize(Object.assign({}, item, { children: [] })).slice(0, -2) + ">\n" + nested.map((child) => "  ".repeat(depth + 1) + format(child, depth + 1)).join("\n") + "\n" + "  ".repeat(depth) + "</" + item.name + ">";
		}
		return format(node, 0);
	}
	const escape = (value, attr) => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, attr ? "&quot;" : "\"").replace(/\r/g, attr ? "&#13;" : "\r").replace(/\n/g, attr ? "&#10;" : "\n").replace(/\t/g, attr ? "&#9;" : "	");
	if (node.type === 9) return (node.children || []).map((child) => serialize(child)).join("");
	if (node.type === 3) return escape(node.text || "", false);
	if (node.type === 4) return "<![CDATA[" + (node.text || "") + "]]>";
	if (node.type === 8) return "<!--" + (node.text || "") + "-->";
	if (node.type === 7) return "<?" + node.name + (node.text ? " " + node.text : "") + "?>";
	if (node.type !== 1) throw Error("Unsupported XML node");
	const attributes = (node.attributes || []).map((pair) => " " + pair[0] + "=\"" + escape(pair[1], true) + "\"").join(""), body = (node.children || []).map((child) => serialize(child)).join("");
	return "<" + node.name + attributes + (node.children && node.children.length ? ">" + body + "</" + node.name + ">" : "/>");
}
function template(tree, view) {
	if (!/^[A-Za-z_][\w.@-]{0,127}$/.test(view)) throw Error("Invalid view name");
	const next = JSON.parse(JSON.stringify(tree)), original = children$1(root(next))[0];
	if (!original) throw Error("Invalid layout template");
	original.name = view.indexOf("@") >= 0 ? "view" : view;
	if (view.indexOf("@") >= 0) set(original, "name", view);
	return next;
}
function edit(tree, view, name, field, value) {
	const next = JSON.parse(JSON.stringify(tree)), root = viewOf(next, view);
	if (!root) throw Error("Configuration does not contain its view");
	let item = name ? children$1(root).find((node) => node.name === "element" && get(node, "name") === name) : root;
	if (field.startsWith("valueColor:")) {
		const display = children$1(item).find((node) => node.name === "display"), option = display && children$1(display).find((node) => node.name === "colors"), colors = option ? JSON.parse(content(option)) : {}, key = field.slice(11);
		if ([
			"__proto__",
			"constructor",
			"prototype"
		].includes(key)) throw Error("Invalid field value colors");
		if (value) colors[key] = value;
		else delete colors[key];
		field = "option:colors";
		value = Object.keys(colors).length ? JSON.stringify(colors) : "";
	}
	if (field === "add") {
		if (widgets.indexOf(value) < 0) throw Error("Unsupported layout widget");
		const names = children$1(root).map((node) => get(node, "name"));
		let index = 1;
		while (names.indexOf("item_" + index) >= 0) index++;
		const last = children$1(root).reduce((max, node) => Math.max(max, Number(get(node, "row") || 1) + Number(get(node, "rows") || 1) - 1), 0);
		item = element("element", [
			["name", "item_" + index],
			["title", value],
			["row", String(last + 1)],
			["span", get(root, "columns") || "12"]
		], [element("display", [["class", value]])]);
		root.children.push(item);
	} else if (!item) throw Error("Layout element no longer exists");
	else if (field === "order") {
		const siblings = children$1(root).filter((node) => node.name === "element" && get(node, "parent") === get(item, "parent")), offset = Number(value), target = siblings[siblings.indexOf(item) + offset];
		if (target && [-1, 1].indexOf(offset) >= 0) {
			root.children.splice(root.children.indexOf(item), 1);
			root.children.splice(root.children.indexOf(target) + (offset > 0 ? 1 : 0), 0, item);
		}
	} else if (field === "remove") {
		const names = [name];
		for (let depth = 0; depth < 8; depth++) for (const child of children$1(root)) if (names.indexOf(get(child, "parent")) >= 0 && names.indexOf(get(child, "name")) < 0) names.push(get(child, "name"));
		root.children = root.children.filter((child) => child.type !== 1 || names.indexOf(get(child, "name")) < 0);
	} else if (field.indexOf("option:") === 0 || field === "kind") {
		let display = children$1(item).find((node) => node.name === "display");
		if (!display) {
			display = element("display");
			item.children.push(display);
		}
		if (field === "kind") {
			set(display, "widget", "");
			set(display, "class", value);
		} else {
			const key = field.slice(7);
			if (!/^[A-Za-z_][\w.-]*$/.test(key)) throw Error("Invalid widget option");
			let option = children$1(display).find((node) => node.name === key);
			if (!value) {
				if (option) display.children.splice(display.children.indexOf(option), 1);
			} else {
				if (!option) {
					option = element(key);
					display.children.push(option);
				}
				option.children = [{
					type: 3,
					text: String(value)
				}];
			}
		}
	} else {
		if (!/^[A-Za-z_][\w.-]*$/.test(field)) throw Error("Invalid layout attribute");
		set(item, field, value);
	}
	return next;
}
function binding(binding, node) {
	if (!/^(record|node)\.[A-Za-z_]\w*(\.[A-Za-z_]\w*){0,4}$/.test(binding || "")) return "";
	const parts = binding.split(".");
	let value = parts.shift() === "record" ? node.record : node;
	for (const part of parts) {
		if ([
			"__proto__",
			"prototype",
			"constructor"
		].indexOf(part) >= 0 || value == null || !Object.prototype.hasOwnProperty.call(value, part)) return "";
		value = value[part];
	}
	return value === void 0 || value === null ? "" : value;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs
function fieldModel(item, sample) {
	const options = item.options || {}, value = options.bind ? binding(options.bind, sample) : "", colors = options.colors ? JSON.parse(options.colors) : {}, color = Object.prototype.hasOwnProperty.call(colors, String(value)) ? colors[String(value)] : options.color || (["badge", "progress"].includes(options.format) ? "contentAccent" : "primaryText");
	return {
		value,
		text: options.text || "",
		format: options.format || "plain",
		suffix: options.format === "progress" ? "%" : "",
		textColor: color,
		progressColor: color
	};
}
var number = (value, fallback, min, max) => Number.isFinite(Number(value)) ? Math.max(min, Math.min(max, Number(value))) : fallback;
function variant(sample) {
	return sample.kind === "branch" ? (sample.branch || {}).kind || "versions" : sample.kind === "object" ? sample.depth ? "children" : "main" : sample.kind;
}
function actionAvailable(action, sample) {
	if (["tasks", "notes"].includes(action)) return sample.kind === "object" || sample.branch?.kind === "process";
	if (["create", "link"].includes(action)) return sample.branch?.kind === "relation" && (action !== "link" || sample.branch.relationship === "instance");
	if (action === "relations") return sample.kind === "object";
	if (["inspect", "preview"].includes(action)) return sample.kind !== "branch";
	return [
		"operate",
		"upload",
		"quickaction"
	].includes(action);
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
	return !item.hidden && (!item.search_type || sample.kind !== "branch" && item.search_type === String((sample.record || {}).__search_key__ || sample.search_type || "").split("?")[0]) && (item.variant === "all" || item.variant === variant(sample)) && (item.when || []).every((key) => conditions[key]) && (item.kind !== "knowledge" || (sample.knowledge || []).length > 0) && (item.kind !== "snapshot-size" || snapshot.size !== void 0) && (item.kind !== "file-offline" || !snapshot.exists);
}
function tracks(value, count, width) {
	const tokens = String(value || "").trim().split(/\s+/).filter(Boolean), sizes = [], weights = [];
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
function supports(layout, sample, width) {
	return !!layout && (layout.elements || []).some((item) => !item.parent && visible(item, sample, layout, width));
}
function safeImage(value, base, local) {
	const text = String(value || "");
	if (local && /^file:/i.test(text) && !/[\u0000-\u001f\u007f\\]/.test(text)) return text.replace(/ /g, "%20");
	if (!text || /[\u0000-\u0020\u007f\\]/.test(text) || text.indexOf("//") === 0) return "";
	if (text.charAt(0) === "/") return (base || "") + text;
	return /^(https?:|blob:|data:image\/(?:png|jpeg|webp|gif);base64,)/i.test(text) || local && /^file:/i.test(text) ? text : "";
}
function describe$2(layout, sample, width, selected, language, screenWidth, assetBase, prefix, depth, editing = true) {
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
		if (item.kind === "group") children.push(node("Box", id + "Group", rect(4, 4, Math.max(0, box.width - 8), Math.max(0, box.height - 8)), {
			background: options.fill || "transparent",
			border: options.stroke,
			radius: Number(options.radius || 0),
			children: inner ? inner.nodes : []
		}));
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
			children.push(node("Preview", id + "Image", rect(4, 4, Math.max(0, box.width - 8), Math.max(0, Math.min(box.height, item.height || box.height) - 8)), {
				source: safeImage(value, assetBase, options.bind === "node.preview.image" && sample.preview && sample.preview.local === true),
				initials,
				icon: "image",
				round: item.role === "preview",
				outlined: false,
				fit: options.fit || "cover"
			}));
		} else if (item.kind === "field") {
			const rendered = field(fieldModel(item, sample), id + "Value", Math.max(0, box.width - 12));
			for (const child of rendered.children) {
				child.x += 6;
				child.y += 4;
				children.push(child);
			}
		} else if (item.kind === "button") {
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
			const iconOnly = !!options.icon && !options.text && !options.bind;
			const fullCaption = caption + (Number.isFinite(badge) && badge > 0 ? " · " + badge : ""), icon = options.icon || {
				tasks: "task",
				notes: "notes",
				upload: "upload",
				inspect: "search",
				relations: "link"
			}[options.action] || "", counted = !iconOnly && !!icon && !!options.badge && box.width - 8 < buttonWidth(fullCaption.length * 7, true);
			const buttonHeight = Math.max(0, Math.min(38, box.height - 8)), buttonWidth$1 = Math.max(0, Math.min(box.width - 8, iconOnly ? buttonHeight : box.width));
			children.push(node("Button", id + "Button", rect(4, 4, buttonWidth$1, iconOnly ? buttonWidth$1 : buttonHeight), {
				iconOnly,
				iconAction: iconOnly,
				round: iconOnly,
				iconColor: badge > 0 ? "contentAccent" : "secondaryText",
				badgeColor: "contentAccent",
				badgeCount: iconOnly && Number.isFinite(badge) ? Math.max(0, badge) : 0,
				text: counted ? String(Number.isFinite(badge) ? Math.max(0, badge) : 0) : fullCaption,
				label: fullCaption,
				toolTip: fullCaption,
				enabled: !editing && (!!(options.href_bind ? binding(options.href_bind, sample) : options.href) || actionAvailable(options.action, sample)),
				action: {
					type: "itemAction",
					action: options.action || "link",
					urlOnly: !options.action,
					href: options.href_bind ? binding(options.href_bind, sample) : options.href
				},
				icon
			}));
		} else if (item.kind === "item-menu") children.push(node("Button", id + "Menu", rect(Math.max(0, box.width - 38), 0, Math.min(38, box.width), 38), {
			text: tr("Item actions"),
			icon: "more-vert",
			iconOnly: true,
			enabled: !editing,
			action: {
				type: "itemAction",
				action: "operate"
			}
		}));
		else if (item.kind === "quick-actions" || item.kind === "relations") {
			const icons = item.kind === "relations" ? ["link", "add"] : ["save", "folder-open"], size = Math.min(32, box.width / icons.length);
			icons.forEach((icon, index) => children.push(node("Button", id + "Action_" + index, rect(index * size, 0, size, 32), {
				text: tr(item.kind === "relations" ? "Relationship actions" : "Snapshot actions"),
				icon,
				iconOnly: true,
				enabled: !editing,
				action: {
					type: "itemAction",
					action: item.kind === "relations" ? index ? "create" : "link" : "quickaction",
					command: index ? "open" : "save"
				}
			})));
		} else {
			let content = text;
			if (item.kind === "link") content = text || item.title || options.href || "";
			else if (item.kind === "title") content = text || title;
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
			const maxLines = Math.max(1, Math.floor((box.height - 8) / (item.kind === "title" ? 20 : 17)));
			children.push(label(id + "Text", rect(6, 4, Math.max(0, box.width - 12), Math.max(0, box.height - 8)), content, {
				wrap: maxLines > 1,
				maxLines,
				color: options.color || color,
				weight,
				fontRole: item.kind === "title" ? "section" : "body",
				align: item.align === "center" ? "center" : item.align === "end" ? "right" : "left"
			}));
		}
		const padding = item.padding || [
			0,
			0,
			0,
			0
		];
		if (padding.some(Boolean)) for (const child of children) {
			child.x += padding[3];
			child.y += padding[0];
			child.width = Math.max(0, child.width - padding[1] - padding[3]);
			child.height = Math.max(0, child.height - padding[0] - padding[2]);
		}
		if (!editing && item.kind === "link") return node("Action", id, box, {
			layoutElement: item.name,
			layer: item.layer || 0,
			text: text || item.title,
			normalColor: "transparent",
			children,
			action: {
				type: "itemAction",
				action: "link",
				urlOnly: true,
				href: options.href_bind ? binding(options.href_bind, sample) : options.href
			}
		});
		if (!editing) return node("Box", id, box, {
			layoutElement: item.name,
			layer: item.layer || 0,
			children
		});
		if (item.kind === "group" || item.kind === "view" && inner) return node("Box", id, box, {
			layoutElement: item.name,
			layer: item.layer || 0,
			background: "transparent",
			border: selected === item.name ? "contentAccent" : void 0,
			radius: 2,
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
			layoutElement: item.name,
			layer: item.layer || 0,
			radius: 2,
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
				let box, child = item.kind === "group" && item.role !== "copy" ? container(item.name, Math.max(1, w - 16), nesting + 1) : item.kind === "view" && item.widget_layout ? describe$2(item.widget_layout, sample, Math.max(1, w - 16), selected, language, screenWidth, assetBase, namePrefix + "_" + item.name, nesting + 1, editing) : null;
				if (item.role === "preview") box = rect(8, 8, Math.min(76, w * .24), 76);
				else if (item.role === "copy") {
					child = container(item.name, Math.max(1, w - copyX - 16), nesting + 1);
					box = rect(copyX, 8, Math.max(1, w - copyX - 8), child.height + 8);
					cursor = Math.max(cursor, box.height + 16);
				} else {
					const h = child ? child.height + 8 : item.kind === "field" ? field(fieldModel(item, sample), "measure", w - 16).height + 8 : item.role === "title-line" ? 36 : item.kind === "image" ? number(item.height, 76, 24, 1200) : item.kind === "description" ? 44 : 38;
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
		const gap = (definition ? definition.gap : layout.gap) ?? 6, available = Math.max(1, w - gap * (columns - 1)), sizes = tracks(definition ? "" : layout.tracks, columns, available), rows = [];
		for (const item of items) {
			const start = number(item.row, 1, 1, 100) - 1, span = number(item.rows, 1, 1, 100), column = number(item.column, 1, 1, columns) - 1, columnsWide = number(item.span, 1, 1, columns - column), cellWidth = sizes.slice(column, column + columnsWide).reduce((a, b) => a + b, 0) + gap * (columnsWide - 1), child = item.kind === "group" ? container(item.name, Math.max(1, cellWidth - 8 - (item.margin?.[1] || 0) - (item.margin?.[3] || 0) - (item.padding?.[1] || 0) - (item.padding?.[3] || 0)), nesting + 1) : item.kind === "view" && item.widget_layout ? describe$2(item.widget_layout, sample, Math.max(1, cellWidth - 8 - (item.margin?.[1] || 0) - (item.margin?.[3] || 0) - (item.padding?.[1] || 0) - (item.padding?.[3] || 0)), selected, language, screenWidth, assetBase, namePrefix + "_" + item.name, nesting + 1, editing) : null, h = Math.max(child ? child.height + 8 : item.kind === "field" ? field(fieldModel(item, sample), "measure", cellWidth).height + 8 : item.kind === "button" ? Math.max(40, number(item.height, 40, 1, 1200)) : number(item.height, 40, 1, 1200), number(item.height, 40, 1, 1200)) + (item.padding?.[0] || 0) + (item.padding?.[2] || 0) + (item.margin?.[0] || 0) + (item.margin?.[2] || 0);
			for (let index = start; index < start + span; index++) rows[index] = Math.max(rows[index] || 0, (h - gap * (span - 1)) / span);
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
			const availableHeight = Math.max(0, h - (row.item.margin?.[0] || 0) - (row.item.margin?.[2] || 0));
			const intrinsic = (row.child ? Math.max(row.child.height + 8, row.item.height || 40) : row.item.height || 40) + (row.item.padding?.[0] || 0) + (row.item.padding?.[2] || 0);
			const placedHeight = row.item.align && row.item.align !== "stretch" ? Math.min(availableHeight, intrinsic) : availableHeight;
			const offset = row.item.align === "center" ? (availableHeight - placedHeight) / 2 : row.item.align === "end" ? availableHeight - placedHeight : 0;
			const drawn = draw(row.item, rect(x + (row.item.margin?.[3] || 0), y + (row.item.margin?.[0] || 0) + offset, Math.max(0, row.cellWidth - (row.item.margin?.[1] || 0) - (row.item.margin?.[3] || 0)), placedHeight), row.child);
			if (editing) drawn.canvasGrid = {
				columns: sizes.map((_, index) => sizes.slice(0, index).reduce((a, b) => a + b, 0) + gap * index),
				ends: sizes.map((_, index) => sizes.slice(0, index + 1).reduce((a, b) => a + b, 0) + gap * index),
				rows: Array.from({ length: rows.length }, (_, index) => sum(rows, 0, index) + gap * index)
			};
			result.push(drawn);
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
			const w = width * number(item.span, 1, 1, 12) / total, child = item.kind === "group" ? container(item.name, Math.max(1, w - 8), level + 1) : item.kind === "view" && item.widget_layout ? describe$2(item.widget_layout, sample, Math.max(1, w - 8), selected, language, screenWidth, assetBase, namePrefix + "_" + item.name, level + 1, editing) : null;
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
//#region ../src/tactic_stream/shared_ui/controls/tabs/workspace.ui.mjs
var dimensions = {
	railWidth: 48,
	rowHeight: 42,
	rowSpacing: 3,
	revealDelay: 350,
	dragThreshold: 10
};
function viewTabWidth(labelAdvance) {
	return Math.max(140, Math.ceil(labelAdvance) + 96);
}
function tab(width, height, record, state = {}) {
	const selected = !!record.current, color = selected ? "action" : "secondaryText";
	const textWidth = Math.max(0, width - (record.closable ? 58 : 24) - (record.icon ? 24 : 0));
	const nodes = [
		node("Box", "workspaceTabOverlay", rect(0, 0, width, height), {
			radius: 0,
			background: selected ? "action" : "primaryText",
			opacity: state.pressed ? .12 : state.hovered || state.focused ? .08 : 0
		}),
		node("Box", "workspaceTabSelectionIndicator", rect(selected ? 12 : width / 2, height - 3, selected ? Math.max(0, width - 24) : 0, 3), {
			background: "action",
			radius: 1.5,
			opacity: selected && record.indicatorVisible !== false ? 1 : 0
		}),
		label("workspaceTabSelectionLabel", rect((width - textWidth) / 2, (height - 19) / 2 - 1, textWidth, 19), record.title, {
			fontRole: "bodyLarge",
			weight: 400,
			color,
			align: "center"
		})
	];
	if (record.icon) nodes.push(node("Icon", "workspaceTabIcon", rect(10, (height - 18) / 2, 18, 18), {
		icon: record.icon,
		color
	}));
	if (record.dirty) nodes.push(node("Box", "workspaceTabDirty", rect(10, (height - 6) / 2, 6, 6), {
		background: "yellow",
		radius: 3
	}));
	if (record.closable) {
		const opacity = selected || state.hovered ? 1 : .58;
		nodes.push(node("Box", "workspaceTabCloseSurface", rect(width - 34, (height - 28) / 2, 28, 28), {
			background: selected ? "action" : "primaryText",
			radius: 14,
			opacity: state.closePressed ? .12 : state.closeHovered ? .08 : 0
		}), node("Icon", "workspaceTabCloseIcon", rect(width - 28, (height - 16) / 2, 16, 16), {
			icon: "close",
			color,
			opacity
		}));
	}
	for (const item of nodes) if (item.id === "workspaceTabSelectionIndicator" && state.animateSelection !== false) item.motion = {
		x: "clickMotionSlow",
		width: "clickMotionSlow",
		opacity: "clickMotionFast"
	};
	else if (item.id === "workspaceTabSelectionLabel" && state.animateSelection !== false) item.motion = { color: "clickMotionFast" };
	else if (item.id === "workspaceTabOverlay" || item.id === "workspaceTabCloseSurface") item.motion = { opacity: state.pressed || state.closePressed ? "clickMotionFast" : "hoverMotionFast" };
	else if (item.id === "workspaceTabCloseIcon" && state.animateSelection !== false) item.motion = { opacity: "hoverMotionFast" };
	return {
		width,
		height,
		nodes
	};
}
function sectionWidth(labelWidth, available = 320) {
	return Math.min(available, 320, Math.max(260, labelWidth + 112));
}
function key(tabs, id, pressed, vertical = false, reorder = false) {
	const index = tabs.findIndex((tab) => tab.id === id);
	if (index < 0) return null;
	const before = vertical ? "ArrowUp" : "ArrowLeft", after = vertical ? "ArrowDown" : "ArrowRight";
	if (reorder && (pressed === before || pressed === after)) {
		const target = index + (pressed === before ? -1 : 1);
		return target < 0 || target >= tabs.length ? null : {
			type: "reorder",
			source: index,
			target
		};
	}
	if (pressed === "Delete") return tabs[index].closable === false ? null : {
		type: "close",
		id
	};
	let target = index;
	if (pressed === before) target = (index + tabs.length - 1) % tabs.length;
	else if (pressed === after) target = (index + 1) % tabs.length;
	else if (pressed === "Home") target = 0;
	else if (pressed === "End") target = tabs.length - 1;
	else return null;
	return {
		type: "select",
		id: tabs[target].id
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/menus/action.ui.mjs
function height(record, extent) {
	return record.separator ? 5 : record.header ? 28 : record.status ? 48 : extent;
}
function row$1(record, width, options) {
	const h = height(record, options.extent), nodes = [];
	if (record.separator) return {
		width,
		height: h,
		nodes: [node("Box", "menuSeparator", rect(0, 2, width, 1), { background: "separator" })]
	};
	const enabled = record.enabled !== false && !record.header;
	const foreground = enabled ? record.checked && record.accent ? record.accent : "primaryText" : "secondaryText";
	nodes.push(node("Box", "menuRowSurface", rect(0, 0, width, h), {
		background: record.checked && record.accent ? record.accent : "primaryText",
		opacity: record.header ? 0 : record.checked && record.accent ? .14 : !enabled ? 0 : options.pressed ? .12 : options.hovered ? .08 : options.focused ? .1 : 0,
		radius: options.radius
	}));
	let left = 10, right = width - 8;
	if (record.secondaryCommand) {
		right -= 15;
		nodes.push(node("Icon", "menuSecondary", rect(right, (h - 15) / 2, 15, 15), {
			icon: record.secondaryIcon || "update",
			color: "secondaryText"
		}));
		right -= 9;
	}
	if (record.children || record.submenuPopup) {
		right -= 16;
		nodes.push(node("Icon", "menuChildren", rect(right, (h - 16) / 2, 16, 16), {
			icon: "chevron-right",
			color: "secondaryText"
		}));
		right -= 9;
	}
	if (record.checked) {
		right -= 18;
		nodes.push(node("Icon", "menuChecked", rect(right, (h - 18) / 2, 18, 18), {
			icon: "check-circle",
			color: record.accent || "action"
		}));
		right -= 9;
	}
	if (Number(record.badgeCount) > 0 || record.showZeroBadge) {
		const count = Number(record.badgeCount || 0), text = count > 99 ? "99+" : String(count), badge = Math.max(18, (options.badgeTextWidth === void 0 ? text.length * 7 : options.badgeTextWidth) + 8);
		right -= badge;
		nodes.push(node("Box", "menuBadge", rect(right, (h - 18) / 2, badge, 18), {
			background: record.badgeUpdated === false ? "secondaryText" : "error",
			radius: 9
		}));
		nodes.push(node("Label", "menuBadgeText", rect(right, (h - 18) / 2, badge, 18), {
			text,
			fontRole: "caption",
			weight: 700,
			align: "center",
			color: "selectedText",
			translate: false
		}));
		right -= 9;
	}
	if (!record.header && record.accent && !record.accentIcon) {
		const extent = record.compactAccent ? 12 : 24;
		if (!record.compactAccent) nodes.push(node("Box", "menuAccentSurface", rect(left, (h - extent) / 2, extent, extent), {
			background: record.accent,
			opacity: .16,
			radius: extent / 2
		}));
		const dot = record.compactAccent ? 8 : 10;
		nodes.push(node("Box", "menuAccent", rect(left + (extent - dot) / 2, (h - dot) / 2, dot, dot), {
			background: record.accent,
			radius: dot / 2
		}));
		left += extent + 9;
	}
	if (!record.header && (record.avatarUrl || record.initials)) {
		nodes.push(node("Preview", "menuAvatar", rect(left, (h - 26) / 2, 26, 26), {
			source: record.avatarUrl || "",
			initials: record.initials || "",
			accent: record.avatarColor || record.accent || "action",
			round: true
		}));
		left += 35;
	} else if (!record.header && record.icon) {
		nodes.push(node("Icon", "menuIcon", rect(left, (h - 16) / 2, 16, 16), {
			icon: record.icon,
			color: record.accentIcon ? record.accent || "action" : "secondaryText"
		}));
		left += 25;
	}
	nodes.push(node("Label", "menuTitle", rect(left, record.status ? 8 : 0, Math.max(0, right - left), record.status ? 16 : h), {
		text: record.title || "",
		translate: false,
		color: foreground,
		fontRole: record.header ? "menuHeading" : "secondary",
		weight: record.header ? 600 : 400
	}));
	if (record.status) nodes.push(node("Label", "menuStatus", rect(left, 24, Math.max(0, right - left), 16), {
		text: record.status,
		translate: false,
		color: record.status === "Experimental" ? "action" : "secondaryText",
		fontRole: "secondary"
	}));
	return {
		width,
		height: h,
		nodes
	};
}
//#endregion
//#region src/controls/ActionRow.vue
var _hoisted_1$10 = ["data-menu-command"];
var _sfc_main$15 = {
	__name: "ActionRow",
	props: {
		record: {
			type: Object,
			required: true
		},
		suppressFocus: Boolean
	},
	emits: ["triggered"],
	setup(__props) {
		const props = __props;
		const root = ref(null), width = ref(230), hovered = ref(false), pressed = ref(false), focused = ref(false), badgeTextWidth = ref(0);
		const title = computed(() => props.record.translate === false ? props.record.title : t(props.record.title || "", props.record.titleArgs));
		const scene = computed(() => row$1({
			...props.record,
			title: title.value,
			status: props.record.statusTranslate === false ? props.record.status : t(props.record.status || "")
		}, width.value, {
			extent: metrics(appearance.theme).compactControlHeight,
			radius: metrics(appearance.theme).itemRadius,
			badgeTextWidth: badgeTextWidth.value,
			hovered: hovered.value,
			pressed: pressed.value,
			focused: focused.value && !props.suppressFocus
		}));
		let observer;
		const measureBadge = () => {
			if (props.record.badgeCount === void 0 && !props.record.showZeroBadge) return;
			const context = document.createElement("canvas").getContext("2d");
			context.font = `700 11px "${fontFamily}"`;
			const count = Number(props.record.badgeCount || 0);
			badgeTextWidth.value = context.measureText(count > 99 ? "99+" : String(count)).width;
		};
		watch(() => props.record.badgeCount, measureBadge);
		onMounted(() => {
			measureBadge();
			document.fonts.addEventListener("loadingdone", measureBadge);
			observer = observeFrameSizes((entries) => {
				width.value = entries.at(-1).contentRect.width;
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			document.fonts.removeEventListener("loadingdone", measureBadge);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "root",
				ref: root,
				class: "action-row",
				"data-menu-command": __props.record.command,
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$18, {
				scene: scene.value,
				interactive: false
			}, null, 8, ["scene"]), !__props.record.separator && !__props.record.header ? (openBlock(), createBlock(_sfc_main$16, {
				key: 0,
				class: "action-row-hit frame-hit-target",
				label: title.value,
				"translate-label": false,
				href: __props.record.href,
				target: __props.record.href ? "_blank" : void 0,
				rel: __props.record.href ? "noopener" : void 0,
				disabled: __props.record.enabled === false,
				role: __props.record.role || (__props.record.checked === void 0 ? void 0 : "menuitemradio"),
				"aria-checked": __props.record.checked,
				onPointerenter: _cache[0] || (_cache[0] = ($event) => hovered.value = true),
				onPointerleave: _cache[1] || (_cache[1] = ($event) => hovered.value = pressed.value = false),
				onPointerdown: _cache[2] || (_cache[2] = ($event) => pressed.value = true),
				onPointerup: _cache[3] || (_cache[3] = ($event) => pressed.value = false),
				onPointercancel: _cache[4] || (_cache[4] = ($event) => pressed.value = false),
				onFocus: _cache[5] || (_cache[5] = ($event) => focused.value = true),
				onBlur: _cache[6] || (_cache[6] = ($event) => focused.value = pressed.value = false),
				onClick: _cache[7] || (_cache[7] = ($event) => _ctx.$emit("triggered"))
			}, {
				default: withCtx(() => [..._cache[8] || (_cache[8] = [createBaseVNode("span", {
					hidden: "",
					"aria-hidden": "true"
				}, null, -1)])]),
				_: 1
			}, 8, [
				"label",
				"href",
				"target",
				"rel",
				"disabled",
				"role",
				"aria-checked"
			])) : createCommentVNode("", true)], 12, _hoisted_1$10);
		};
	}
};
//#endregion
//#region src/controls/ActionRows.vue
var _hoisted_1$9 = { class: "action-rows" };
var _sfc_main$14 = {
	__name: "ActionRows",
	props: { actions: {
		type: Array,
		required: true
	} },
	emits: ["triggered"],
	setup(__props) {
		const hovered = ref(null);
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$9, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.actions, (record, index) => {
				return openBlock(), createBlock(_sfc_main$15, {
					key: record.command || index,
					record,
					"suppress-focus": hovered.value !== null,
					onPointerenter: ($event) => !record.header && !record.separator && record.enabled !== false && (hovered.value = index),
					onPointerleave: _cache[0] || (_cache[0] = ($event) => hovered.value = null),
					onTriggered: ($event) => _ctx.$emit("triggered", record.command)
				}, null, 8, [
					"record",
					"suppress-focus",
					"onPointerenter",
					"onTriggered"
				]);
			}), 128))]);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/table/views.ui.mjs
var serviceViews = [
	"definition",
	"default_definition",
	"edit_definition",
	"edit",
	"insert",
	"search",
	"filter",
	"custom_filter",
	"simple_filter"
];
function choices$1(views) {
	return views.filter((row) => typeof row.view === "string" && !serviceViews.includes(row.view));
}
function initial() {
	return {
		query: "",
		selected: "table",
		mode: "",
		title: ""
	};
}
function loaded(ui, model) {
	const selected = model.selected || ui.selected;
	return Object.assign({}, ui, {
		selected: model.views.some((row) => row.view === selected) ? selected : model.current || "table",
		mode: "",
		title: ""
	});
}
function rows(model, ui) {
	const query = ui.query.trim().toLocaleLowerCase();
	return model.views.filter((row) => (row.title + " " + row.view).toLocaleLowerCase().includes(query));
}
function transition(ui, model, action) {
	if (model.busy) return { ui };
	const selected = model.views.find((row) => row.view === ui.selected);
	if (action.type === "query") return { ui: Object.assign({}, ui, { query: action.value }) };
	if (action.type === "title") return { ui: Object.assign({}, ui, { title: action.value }) };
	if (action.type === "select") return { ui: Object.assign({}, ui, {
		selected: action.view,
		mode: "",
		title: ""
	}) };
	if (action.type === "cancel") return { ui: Object.assign({}, ui, {
		mode: "",
		title: ""
	}) };
	if ([
		"create",
		"copy",
		"rename",
		"delete"
	].includes(action.type)) {
		if (!model.revision || model.uncertain) return { ui };
		if (action.type !== "create" && !selected) return { ui };
		if (["rename", "delete"].includes(action.type) && selected.protected) return { ui };
		return { ui: Object.assign({}, ui, {
			mode: action.type,
			title: action.type === "rename" ? selected.title : ""
		}) };
	}
	if (action.type === "apply") {
		if (!model.revision || model.uncertain) return { ui };
		if (!ui.mode || ui.mode !== "delete" && !ui.title.trim()) return { ui };
		return {
			ui,
			command: {
				action: ui.mode,
				view: ui.selected,
				title: ui.title.trim(),
				revision: model.revision
			}
		};
	}
	if ([
		"read",
		"use",
		"configure"
	].includes(action.type)) return {
		ui,
		command: {
			action: action.type,
			view: ui.selected
		}
	};
	return { ui };
}
function describe$1(model, ui, width, height, language) {
	const tr = (key) => translate(key, language);
	if (width < 600 || height < 540) return { nodes: [node("Scroll", "tableViewsWindowScroll", rect(0, 0, width, height), {
		contentWidth: Math.max(600, width - 16),
		contentHeight: Math.max(540, height),
		scrollbarId: "tableViewsWindowScrollBar",
		children: describe$1(model, ui, Math.max(600, width - 16), Math.max(540, height), language).nodes
	})] };
	const left = Math.min(320, width * .4), x = left + 24, inner = width - x - 16;
	const selected = model.views.find((row) => row.view === ui.selected);
	const enabled = !!model.revision && !model.busy && !model.uncertain && !ui.mode;
	const nodes = [
		node("Box", "tableViewsHeader", rect(0, 0, width, 50), {
			background: "surfaceContainerHigh",
			children: [label("tableViewsContext", rect(16, 8, width - 72, 34), (model.projectTitle || model.project) + " · " + (model.searchTitle || model.searchType), { weight: 600 }), button("tableViewsRefresh", rect(width - 48, 9, 32, 32), tr("Refresh"), "refresh", { type: "read" }, !model.busy, { iconOnly: true })]
		}),
		node("Box", "tableViewsCatalog", rect(12, 62, left, height - 124), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [node("Field", "tableViewsSearch", rect(10, 10, left - 20, 34), {
				text: ui.query,
				label: tr("Find a table view"),
				placeholder: tr("Find a table view"),
				enabled: !model.busy,
				action: { type: "query" }
			}), node("List", "tableViewsList", rect(10, 54, left - 20, height - 190), {
				source: "views",
				keyField: "view",
				rowHeight: 52,
				fields: [],
				scrollbarId: "tableViewsListScrollBar"
			})]
		}),
		node("Box", "tableViewsDetails", rect(x, 62, inner, height - 124), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: []
		})
	];
	const body = nodes[2].children;
	if (selected) {
		body.push(label("tableViewsTitle", rect(16, 14, inner - 32, 32), selected.view === "table" ? tr("Default table") : selected.title, {
			fontRole: "section",
			weight: 600
		}));
		body.push(label("tableViewsCode", rect(16, 52, inner - 32, 24), selected.view, muted));
		body.push(label("tableViewsScope", rect(16, 86, inner - 32, 54), tr(selected.protected ? "The default table is protected. Create a copy to customize it." : "Project view. Renaming changes its label and keeps existing links."), {
			wrap: true,
			color: "secondaryText"
		}));
		body.push(label("tableViewsColumns", rect(16, 146, inner - 32, 26), tr("Columns") + ": " + selected.columns));
		body.push(label("tableViewsCurrent", rect(16, 176, inner - 32, 24), selected.view === model.current ? tr("Current view") : "", { color: "action" }));
	}
	if (ui.mode) {
		const deleting = ui.mode === "delete";
		body.push(label("tableViewsEditHeading", rect(16, 218, inner - 32, 28), tr({
			create: "New table view",
			copy: "Duplicate table view",
			rename: "Rename table view",
			delete: "Delete table view"
		}[ui.mode]), { weight: 600 }));
		if (deleting) body.push(label("tableViewsDeleteWarning", rect(16, 250, inner - 32, 64), tr("Delete this project view and its saved layers? Existing links to it may stop working."), {
			wrap: true,
			color: "error"
		}));
		else body.push(node("Field", "tableViewsName", rect(16, 252, inner - 32, 36), {
			text: ui.title,
			label: tr("View name"),
			enabled: !model.busy,
			action: { type: "title" },
			props: { maxLength: 120 }
		}));
		body.push(button("tableViewsApply", rect(16, 326, 124, 32), tr(deleting ? "Delete" : "Save"), deleting ? "delete" : "save", { type: "apply" }, !model.busy && !model.uncertain && (deleting || !!ui.title.trim()), {
			highlighted: !deleting,
			destructive: deleting
		}));
		body.push(button("tableViewsCancel", rect(150, 326, 112, 32), tr("Cancel"), "close", { type: "cancel" }, !model.busy));
	} else {
		for (const [index, entry] of [
			[
				"create",
				"New view",
				"add"
			],
			[
				"copy",
				"Duplicate",
				"content-copy"
			],
			[
				"rename",
				"Rename",
				"edit"
			],
			[
				"delete",
				"Delete",
				"delete"
			]
		].entries()) nodes.push(button("tableViews_" + entry[0], rect(12 + index * 146, height - 48, 138, 32), tr(entry[1]), entry[2], { type: entry[0] }, enabled && (entry[0] === "create" || !!selected && (!["rename", "delete"].includes(entry[0]) || !selected.protected)), { destructive: entry[0] === "delete" }));
		body.push(button("tableViewsUse", rect(16, 228, Math.min(inner - 32, 160), 34), tr("Use this view"), "check", { type: "use" }, enabled && !!selected, { highlighted: true }));
		body.push(button("tableViewsConfigure", rect(16, 272, Math.min(inner - 32, 200), 34), tr("Configure columns"), "view-column", { type: "configure" }, enabled && !!selected));
	}
	if (model.error || model.busy) nodes.push(label("tableViewsStatus", rect(x + 16, height - 94, inner - 32, 30), model.error || tr("Working on the server…"), {
		color: model.error ? "error" : "secondaryText",
		wrap: true
	}));
	return { nodes };
}
function row(list, record, ui, model, language) {
	const title = record.view === "table" ? translate("Default table", language) : record.title;
	return { nodes: [node("Action", "tableView_" + record.view, rect(0, 0, list.width - 16, 50), {
		text: title,
		selected: ui.selected === record.view,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		rail: false,
		enabled: !model.busy && !ui.mode,
		action: {
			type: "select",
			view: record.view
		},
		children: [
			node("Icon", "tableViewIcon", rect(8, 15, 20, 20), {
				icon: record.view === model.current ? "check" : "table-view",
				color: "action"
			}),
			label("tableViewTitle", rect(36, 4, list.width - 60, 24), title, { weight: 600 }),
			label("tableViewCode", rect(36, 28, list.width - 60, 18), record.view, muted)
		]
	})] };
}
//#endregion
//#region node_modules/mdurl/lib/decode.mjs
var decodeCache = {};
function getDecodeCache(exclude) {
	let cache = decodeCache[exclude];
	if (cache) return cache;
	cache = decodeCache[exclude] = [];
	for (let i = 0; i < 128; i++) {
		const ch = String.fromCharCode(i);
		cache.push(ch);
	}
	for (let i = 0; i < exclude.length; i++) {
		const ch = exclude.charCodeAt(i);
		cache[ch] = "%" + ("0" + ch.toString(16).toUpperCase()).slice(-2);
	}
	return cache;
}
function decode$1(string, exclude) {
	if (typeof exclude !== "string") exclude = decode$1.defaultChars;
	const cache = getDecodeCache(exclude);
	return string.replace(/(%[a-f0-9]{2})+/gi, function(seq) {
		let result = "";
		for (let i = 0, l = seq.length; i < l; i += 3) {
			const b1 = parseInt(seq.slice(i + 1, i + 3), 16);
			if (b1 < 128) {
				result += cache[b1];
				continue;
			}
			if ((b1 & 224) === 192 && i + 3 < l) {
				const b2 = parseInt(seq.slice(i + 4, i + 6), 16);
				if ((b2 & 192) === 128) {
					const chr = b1 << 6 & 1984 | b2 & 63;
					if (chr < 128) result += "��";
					else result += String.fromCharCode(chr);
					i += 3;
					continue;
				}
			}
			if ((b1 & 240) === 224 && i + 6 < l) {
				const b2 = parseInt(seq.slice(i + 4, i + 6), 16);
				const b3 = parseInt(seq.slice(i + 7, i + 9), 16);
				if ((b2 & 192) === 128 && (b3 & 192) === 128) {
					const chr = b1 << 12 & 61440 | b2 << 6 & 4032 | b3 & 63;
					if (chr < 2048 || chr >= 55296 && chr <= 57343) result += "���";
					else result += String.fromCharCode(chr);
					i += 6;
					continue;
				}
			}
			if ((b1 & 248) === 240 && i + 9 < l) {
				const b2 = parseInt(seq.slice(i + 4, i + 6), 16);
				const b3 = parseInt(seq.slice(i + 7, i + 9), 16);
				const b4 = parseInt(seq.slice(i + 10, i + 12), 16);
				if ((b2 & 192) === 128 && (b3 & 192) === 128 && (b4 & 192) === 128) {
					let chr = b1 << 18 & 1835008 | b2 << 12 & 258048 | b3 << 6 & 4032 | b4 & 63;
					if (chr < 65536 || chr > 1114111) result += "����";
					else {
						chr -= 65536;
						result += String.fromCharCode(55296 + (chr >> 10), 56320 + (chr & 1023));
					}
					i += 9;
					continue;
				}
			}
			result += "�";
		}
		return result;
	});
}
decode$1.defaultChars = ";/?:@&=+$,#";
decode$1.componentChars = "";
//#endregion
//#region node_modules/mdurl/lib/encode.mjs
var encodeCache = {};
function getEncodeCache(exclude) {
	let cache = encodeCache[exclude];
	if (cache) return cache;
	cache = encodeCache[exclude] = [];
	for (let i = 0; i < 128; i++) {
		const ch = String.fromCharCode(i);
		if (/^[0-9a-z]$/i.test(ch)) cache.push(ch);
		else cache.push("%" + ("0" + i.toString(16).toUpperCase()).slice(-2));
	}
	for (let i = 0; i < exclude.length; i++) cache[exclude.charCodeAt(i)] = exclude[i];
	return cache;
}
function encode$1(string, exclude, keepEscaped) {
	if (typeof exclude !== "string") {
		keepEscaped = exclude;
		exclude = encode$1.defaultChars;
	}
	if (typeof keepEscaped === "undefined") keepEscaped = true;
	const cache = getEncodeCache(exclude);
	let result = "";
	for (let i = 0, l = string.length; i < l; i++) {
		const code = string.charCodeAt(i);
		if (keepEscaped && code === 37 && i + 2 < l) {
			if (/^[0-9a-f]{2}$/i.test(string.slice(i + 1, i + 3))) {
				result += string.slice(i, i + 3);
				i += 2;
				continue;
			}
		}
		if (code < 128) {
			result += cache[code];
			continue;
		}
		if (code >= 55296 && code <= 57343) {
			if (code >= 55296 && code <= 56319 && i + 1 < l) {
				const nextCode = string.charCodeAt(i + 1);
				if (nextCode >= 56320 && nextCode <= 57343) {
					result += encodeURIComponent(string[i] + string[i + 1]);
					i++;
					continue;
				}
			}
			result += "%EF%BF%BD";
			continue;
		}
		result += encodeURIComponent(string[i]);
	}
	return result;
}
encode$1.defaultChars = ";/?:@&=+$,-_.!~*'()#";
encode$1.componentChars = "-_.!~*'()";
//#endregion
//#region node_modules/mdurl/lib/format.mjs
function format(url) {
	let result = "";
	result += url.protocol || "";
	result += url.slashes ? "//" : "";
	result += url.auth ? url.auth + "@" : "";
	if (url.hostname && url.hostname.indexOf(":") !== -1) result += "[" + url.hostname + "]";
	else result += url.hostname || "";
	result += url.port ? ":" + url.port : "";
	result += url.pathname || "";
	result += url.search || "";
	result += url.hash || "";
	return result;
}
//#endregion
//#region node_modules/mdurl/lib/parse.mjs
function Url() {
	this.protocol = null;
	this.slashes = null;
	this.auth = null;
	this.port = null;
	this.hostname = null;
	this.hash = null;
	this.search = null;
	this.pathname = null;
}
var protocolPattern = /^([a-z0-9.+-]+:)/i;
var portPattern = /:[0-9]*$/;
var simplePathPattern = /^(\/\/?(?!\/)[^\?\s]*)(\?[^\s]*)?$/;
var unwise = [
	"{",
	"}",
	"|",
	"\\",
	"^",
	"`"
].concat([
	"<",
	">",
	"\"",
	"`",
	" ",
	"\r",
	"\n",
	"	"
]);
var autoEscape = ["'"].concat(unwise);
var nonHostChars = [
	"%",
	"/",
	"?",
	";",
	"#"
].concat(autoEscape);
var hostEndingChars = [
	"/",
	"?",
	"#"
];
var hostnameMaxLen = 255;
var hostnamePartPattern = /^[+a-z0-9A-Z_-]{0,63}$/;
var hostnamePartStart = /^([+a-z0-9A-Z_-]{0,63})(.*)$/;
var hostlessProtocol = {
	javascript: true,
	"javascript:": true
};
var slashedProtocol = {
	http: true,
	https: true,
	ftp: true,
	gopher: true,
	file: true,
	"http:": true,
	"https:": true,
	"ftp:": true,
	"gopher:": true,
	"file:": true
};
function urlParse(url, slashesDenoteHost) {
	if (url && url instanceof Url) return url;
	const u = new Url();
	u.parse(url, slashesDenoteHost);
	return u;
}
Url.prototype.parse = function(url, slashesDenoteHost) {
	let lowerProto, hec, slashes;
	let rest = url;
	rest = rest.trim();
	if (!slashesDenoteHost && url.split("#").length === 1) {
		const simplePath = simplePathPattern.exec(rest);
		if (simplePath) {
			this.pathname = simplePath[1];
			if (simplePath[2]) this.search = simplePath[2];
			return this;
		}
	}
	let proto = protocolPattern.exec(rest);
	if (proto) {
		proto = proto[0];
		lowerProto = proto.toLowerCase();
		this.protocol = proto;
		rest = rest.substr(proto.length);
	}
	if (slashesDenoteHost || proto || rest.match(/^\/\/[^@\/]+@[^@\/]+/)) {
		slashes = rest.substr(0, 2) === "//";
		if (slashes && !(proto && hostlessProtocol[proto])) {
			rest = rest.substr(2);
			this.slashes = true;
		}
	}
	if (!hostlessProtocol[proto] && (slashes || proto && !slashedProtocol[proto])) {
		let hostEnd = -1;
		for (let i = 0; i < hostEndingChars.length; i++) {
			hec = rest.indexOf(hostEndingChars[i]);
			if (hec !== -1 && (hostEnd === -1 || hec < hostEnd)) hostEnd = hec;
		}
		let auth, atSign;
		if (hostEnd === -1) atSign = rest.lastIndexOf("@");
		else atSign = rest.lastIndexOf("@", hostEnd);
		if (atSign !== -1) {
			auth = rest.slice(0, atSign);
			rest = rest.slice(atSign + 1);
			this.auth = auth;
		}
		hostEnd = -1;
		for (let i = 0; i < nonHostChars.length; i++) {
			hec = rest.indexOf(nonHostChars[i]);
			if (hec !== -1 && (hostEnd === -1 || hec < hostEnd)) hostEnd = hec;
		}
		if (hostEnd === -1) hostEnd = rest.length;
		if (rest[hostEnd - 1] === ":") hostEnd--;
		const host = rest.slice(0, hostEnd);
		rest = rest.slice(hostEnd);
		this.parseHost(host);
		this.hostname = this.hostname || "";
		const ipv6Hostname = this.hostname[0] === "[" && this.hostname[this.hostname.length - 1] === "]";
		if (!ipv6Hostname) {
			const hostparts = this.hostname.split(/\./);
			for (let i = 0, l = hostparts.length; i < l; i++) {
				const part = hostparts[i];
				if (!part) continue;
				if (!part.match(hostnamePartPattern)) {
					let newpart = "";
					for (let j = 0, k = part.length; j < k; j++) if (part.charCodeAt(j) > 127) newpart += "x";
					else newpart += part[j];
					if (!newpart.match(hostnamePartPattern)) {
						const validParts = hostparts.slice(0, i);
						const notHost = hostparts.slice(i + 1);
						const bit = part.match(hostnamePartStart);
						if (bit) {
							validParts.push(bit[1]);
							notHost.unshift(bit[2]);
						}
						if (notHost.length) rest = notHost.join(".") + rest;
						this.hostname = validParts.join(".");
						break;
					}
				}
			}
		}
		if (this.hostname.length > hostnameMaxLen) this.hostname = "";
		if (ipv6Hostname) this.hostname = this.hostname.substr(1, this.hostname.length - 2);
	}
	const hash = rest.indexOf("#");
	if (hash !== -1) {
		this.hash = rest.substr(hash);
		rest = rest.slice(0, hash);
	}
	const qm = rest.indexOf("?");
	if (qm !== -1) {
		this.search = rest.substr(qm);
		rest = rest.slice(0, qm);
	}
	if (rest) this.pathname = rest;
	if (slashedProtocol[lowerProto] && this.hostname && !this.pathname) this.pathname = "";
	return this;
};
Url.prototype.parseHost = function(host) {
	let port = portPattern.exec(host);
	if (port) {
		port = port[0];
		if (port !== ":") this.port = port.substr(1);
		host = host.substr(0, host.length - port.length);
	}
	if (host) this.hostname = host;
};
//#endregion
//#region node_modules/mdurl/index.mjs
var mdurl_exports = /* @__PURE__ */ __exportAll$1({
	decode: () => decode$1,
	encode: () => encode$1,
	format: () => format,
	parse: () => urlParse
});
//#endregion
//#region node_modules/uc.micro/build/index.mjs
var build_exports = /* @__PURE__ */ __exportAll$1({
	Any: () => Any,
	Cc: () => Cc,
	Cf: () => Cf,
	P: () => P,
	S: () => S,
	Z: () => Z
});
var Any = /[\0-\uD7FF\uE000-\uFFFF]|[\uD800-\uDBFF][\uDC00-\uDFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]/;
var Cc = /[\0-\x1F\x7F-\x9F]/;
var Cf = /[\xAD\u0600-\u0605\u061C\u06DD\u070F\u0890\u0891\u08E2\u180E\u200B-\u200F\u202A-\u202E\u2060-\u2064\u2066-\u206F\uFEFF\uFFF9-\uFFFB]|\uD804[\uDCBD\uDCCD]|\uD80D[\uDC30-\uDC3F]|\uD82F[\uDCA0-\uDCA3]|\uD834[\uDD73-\uDD7A]|\uDB40[\uDC01\uDC20-\uDC7F]/;
var P = /[!-#%-\*,-\/:;\?@\[-\]_\{\}\xA1\xA7\xAB\xB6\xB7\xBB\xBF\u037E\u0387\u055A-\u055F\u0589\u058A\u05BE\u05C0\u05C3\u05C6\u05F3\u05F4\u0609\u060A\u060C\u060D\u061B\u061D-\u061F\u066A-\u066D\u06D4\u0700-\u070D\u07F7-\u07F9\u0830-\u083E\u085E\u0964\u0965\u0970\u09FD\u0A76\u0AF0\u0C77\u0C84\u0DF4\u0E4F\u0E5A\u0E5B\u0F04-\u0F12\u0F14\u0F3A-\u0F3D\u0F85\u0FD0-\u0FD4\u0FD9\u0FDA\u104A-\u104F\u10FB\u1360-\u1368\u1400\u166E\u169B\u169C\u16EB-\u16ED\u1735\u1736\u17D4-\u17D6\u17D8-\u17DA\u1800-\u180A\u1944\u1945\u1A1E\u1A1F\u1AA0-\u1AA6\u1AA8-\u1AAD\u1B4E\u1B4F\u1B5A-\u1B60\u1B7D-\u1B7F\u1BFC-\u1BFF\u1C3B-\u1C3F\u1C7E\u1C7F\u1CC0-\u1CC7\u1CD3\u2010-\u2027\u2030-\u2043\u2045-\u2051\u2053-\u205E\u207D\u207E\u208D\u208E\u2308-\u230B\u2329\u232A\u2768-\u2775\u27C5\u27C6\u27E6-\u27EF\u2983-\u2998\u29D8-\u29DB\u29FC\u29FD\u2CF9-\u2CFC\u2CFE\u2CFF\u2D70\u2E00-\u2E2E\u2E30-\u2E4F\u2E52-\u2E5D\u3001-\u3003\u3008-\u3011\u3014-\u301F\u3030\u303D\u30A0\u30FB\uA4FE\uA4FF\uA60D-\uA60F\uA673\uA67E\uA6F2-\uA6F7\uA874-\uA877\uA8CE\uA8CF\uA8F8-\uA8FA\uA8FC\uA92E\uA92F\uA95F\uA9C1-\uA9CD\uA9DE\uA9DF\uAA5C-\uAA5F\uAADE\uAADF\uAAF0\uAAF1\uABEB\uFD3E\uFD3F\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE61\uFE63\uFE68\uFE6A\uFE6B\uFF01-\uFF03\uFF05-\uFF0A\uFF0C-\uFF0F\uFF1A\uFF1B\uFF1F\uFF20\uFF3B-\uFF3D\uFF3F\uFF5B\uFF5D\uFF5F-\uFF65]|\uD800[\uDD00-\uDD02\uDF9F\uDFD0]|\uD801\uDD6F|\uD802[\uDC57\uDD1F\uDD3F\uDE50-\uDE58\uDE7F\uDEF0-\uDEF6\uDF39-\uDF3F\uDF99-\uDF9C]|\uD803[\uDD6E\uDEAD\uDED0\uDF55-\uDF59\uDF86-\uDF89]|\uD804[\uDC47-\uDC4D\uDCBB\uDCBC\uDCBE-\uDCC1\uDD40-\uDD43\uDD74\uDD75\uDDC5-\uDDC8\uDDCD\uDDDB\uDDDD-\uDDDF\uDE38-\uDE3D\uDEA9\uDFD4\uDFD5\uDFD7\uDFD8]|\uD805[\uDC4B-\uDC4F\uDC5A\uDC5B\uDC5D\uDCC6\uDDC1-\uDDD7\uDE41-\uDE43\uDE60-\uDE6C\uDEB9\uDF3C-\uDF3E]|\uD806[\uDC3B\uDD44-\uDD46\uDDE2\uDE3F-\uDE46\uDE9A-\uDE9C\uDE9E-\uDEA2\uDF00-\uDF09\uDFE1]|\uD807[\uDC41-\uDC45\uDC70\uDC71\uDEF7\uDEF8\uDF43-\uDF4F\uDFFF]|\uD809[\uDC70-\uDC74]|\uD80B[\uDFF1\uDFF2]|\uD81A[\uDE6E\uDE6F\uDEF5\uDF37-\uDF3B\uDF44]|\uD81B[\uDD6D-\uDD6F\uDE97-\uDE9A\uDFE2]|\uD82F\uDC9F|\uD836[\uDE87-\uDE8B]|\uD839\uDDFF|\uD83A[\uDD5E\uDD5F]/;
var S = /[\$\+<->\^`\|~\xA2-\xA6\xA8\xA9\xAC\xAE-\xB1\xB4\xB8\xD7\xF7\u02C2-\u02C5\u02D2-\u02DF\u02E5-\u02EB\u02ED\u02EF-\u02FF\u0375\u0384\u0385\u03F6\u0482\u058D-\u058F\u0606-\u0608\u060B\u060E\u060F\u06DE\u06E9\u06FD\u06FE\u07F6\u07FE\u07FF\u0888\u09F2\u09F3\u09FA\u09FB\u0AF1\u0B70\u0BF3-\u0BFA\u0C7F\u0D4F\u0D79\u0E3F\u0F01-\u0F03\u0F13\u0F15-\u0F17\u0F1A-\u0F1F\u0F34\u0F36\u0F38\u0FBE-\u0FC5\u0FC7-\u0FCC\u0FCE\u0FCF\u0FD5-\u0FD8\u109E\u109F\u1390-\u1399\u166D\u17DB\u1940\u19DE-\u19FF\u1B61-\u1B6A\u1B74-\u1B7C\u1FBD\u1FBF-\u1FC1\u1FCD-\u1FCF\u1FDD-\u1FDF\u1FED-\u1FEF\u1FFD\u1FFE\u2044\u2052\u207A-\u207C\u208A-\u208C\u20A0-\u20C1\u2100\u2101\u2103-\u2106\u2108\u2109\u2114\u2116-\u2118\u211E-\u2123\u2125\u2127\u2129\u212E\u213A\u213B\u2140-\u2144\u214A-\u214D\u214F\u218A\u218B\u2190-\u2307\u230C-\u2328\u232B-\u2429\u2440-\u244A\u249C-\u24E9\u2500-\u2767\u2794-\u27C4\u27C7-\u27E5\u27F0-\u2982\u2999-\u29D7\u29DC-\u29FB\u29FE-\u2B73\u2B76-\u2BFF\u2CE5-\u2CEA\u2E50\u2E51\u2E80-\u2E99\u2E9B-\u2EF3\u2F00-\u2FD5\u2FF0-\u2FFF\u3004\u3012\u3013\u3020\u3036\u3037\u303E\u303F\u309B\u309C\u3190\u3191\u3196-\u319F\u31C0-\u31E5\u31EF\u3200-\u321E\u322A-\u3247\u3250\u3260-\u327F\u328A-\u32B0\u32C0-\u33FF\u4DC0-\u4DFF\uA490-\uA4C6\uA700-\uA716\uA720\uA721\uA789\uA78A\uA828-\uA82B\uA836-\uA839\uAA77-\uAA79\uAB5B\uAB6A\uAB6B\uFB29\uFBB2-\uFBD2\uFD40-\uFD4F\uFD90\uFD91\uFDC8-\uFDCF\uFDFC-\uFDFF\uFE62\uFE64-\uFE66\uFE69\uFF04\uFF0B\uFF1C-\uFF1E\uFF3E\uFF40\uFF5C\uFF5E\uFFE0-\uFFE6\uFFE8-\uFFEE\uFFFC\uFFFD]|\uD800[\uDD37-\uDD3F\uDD79-\uDD89\uDD8C-\uDD8E\uDD90-\uDD9C\uDDA0\uDDD0-\uDDFC]|\uD802[\uDC77\uDC78\uDEC8]|\uD803[\uDD8E\uDD8F\uDED1-\uDED8]|\uD805\uDF3F|\uD807[\uDFD5-\uDFF1]|\uD81A[\uDF3C-\uDF3F\uDF45]|\uD82F\uDC9C|\uD833[\uDC00-\uDCEF\uDCFA-\uDCFC\uDD00-\uDEB3\uDEBA-\uDED0\uDEE0-\uDEF0\uDF50-\uDFC3]|\uD834[\uDC00-\uDCF5\uDD00-\uDD26\uDD29-\uDD64\uDD6A-\uDD6C\uDD83\uDD84\uDD8C-\uDDA9\uDDAE-\uDDEA\uDE00-\uDE41\uDE45\uDF00-\uDF56]|\uD835[\uDEC1\uDEDB\uDEFB\uDF15\uDF35\uDF4F\uDF6F\uDF89\uDFA9\uDFC3]|\uD836[\uDC00-\uDDFF\uDE37-\uDE3A\uDE6D-\uDE74\uDE76-\uDE83\uDE85\uDE86]|\uD838[\uDD4F\uDEFF]|\uD83B[\uDCAC\uDCB0\uDD2E\uDEF0\uDEF1]|\uD83C[\uDC00-\uDC2B\uDC30-\uDC93\uDCA0-\uDCAE\uDCB1-\uDCBF\uDCC1-\uDCCF\uDCD1-\uDCF5\uDD0D-\uDDAD\uDDE6-\uDE02\uDE10-\uDE3B\uDE40-\uDE48\uDE50\uDE51\uDE60-\uDE65\uDF00-\uDFFF]|\uD83D[\uDC00-\uDED8\uDEDC-\uDEEC\uDEF0-\uDEFC\uDF00-\uDFD9\uDFE0-\uDFEB\uDFF0]|\uD83E[\uDC00-\uDC0B\uDC10-\uDC47\uDC50-\uDC59\uDC60-\uDC87\uDC90-\uDCAD\uDCB0-\uDCBB\uDCC0\uDCC1\uDCD0-\uDCD8\uDD00-\uDE57\uDE60-\uDE6D\uDE70-\uDE7C\uDE80-\uDE8A\uDE8E-\uDEC6\uDEC8\uDECD-\uDEDC\uDEDF-\uDEEA\uDEEF-\uDEF8\uDF00-\uDF92\uDF94-\uDFEF\uDFFA]/;
var Z = /[ \xA0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]/;
//#endregion
//#region node_modules/markdown-it/node_modules/entities/dist/decode-codepoint.js
/**
* C1 Unicode control character reference replacements (code points 128–159).
* Index i gives the replacement for code point 128+i; 0 means "no replacement".
*/
var c1 = [
	8364,
	0,
	8218,
	402,
	8222,
	8230,
	8224,
	8225,
	710,
	8240,
	352,
	8249,
	338,
	0,
	381,
	0,
	0,
	8216,
	8217,
	8220,
	8221,
	8226,
	8211,
	8212,
	732,
	8482,
	353,
	8250,
	339,
	0,
	382,
	376
];
/**
* True for NUL, UTF-16 surrogates, and values past U+10FFFF.
* @param codePoint Unicode code point to check.
*/
function isInvalidCodePoint(codePoint) {
	return codePoint === 0 || codePoint >= 55296 && codePoint <= 57343 || codePoint > 1114111;
}
/**
* Replace the given code point with U+FFFD if it is NUL (0), a surrogate, or
* outside the valid Unicode range. Code points in the C1 controls range
* (128–159) are remapped to their Windows-1252 equivalents, following the
* HTML spec. All other code points are returned unchanged.
* @param codePoint Unicode code point to convert.
*/
function replaceCodePoint(codePoint) {
	if (isInvalidCodePoint(codePoint)) return 65533;
	if (codePoint >= 128 && codePoint <= 159) return c1[codePoint - 128] || codePoint;
	return codePoint;
}
/**
* Convert the code point of a decoded numeric entity to a string, replacing
* invalid values.
*
* Fast path for plain BMP code points: [1..0x7F] and [0xA0..0xD7FF] pass
* `replaceCodePoint` unchanged (no NUL, C1 remap, surrogate, or out-of-range
* handling) and fit a single charCode. 0xd760 = 0xD800 (the first surrogate)
* - 0xA0.
* @param codePoint Unicode code point to convert.
*/
function codePointToString(codePoint) {
	return codePoint - 1 >>> 0 < 127 || codePoint - 160 >>> 0 < 55136 ? String.fromCharCode(codePoint) : String.fromCodePoint(replaceCodePoint(codePoint));
}
//#endregion
//#region node_modules/markdown-it/node_modules/entities/dist/internal/decode-shared.js
var BASE91_INVERSE = /* #__PURE__ */ (() => {
	const table = /* @__PURE__ */ new Uint8Array(127);
	let code = 0;
	for (let char = 33; char <= 126; char++) if (char !== 34 && char !== 36 && char !== 92) table[char] = code++;
	return table;
})();
/**
* Decode a dictionary-encoded trie string back into its Uint16Array.
*
* Stream layout (consumed in this order):
*   1. dict1 atoms — `dict1AtomCount` uint16 values, delta+RLE encoded.
*   2. dict2 atoms — `atomCount - dict1AtomCount` values, delta+RLE.
*   3. dict2 ngrams — `ngramCount - (dictSize - dict1AtomCount)` entries,
*      each a pair of slot codes that resolve to earlier slots.
*   4. dict1 ngrams — `dictSize - dict1AtomCount` entries, same shape.
*   5. data — slot codes, each expanding to one or more uint16 values.
*
* Codes use a 91-char base (printable ASCII minus `"`, `$`, `\`):
*   - char1 < dictSize  → 1-char code, slot = char1
*   - char1 ≥ dictSize  → 2-char code, slot = dictSize + (char1 - dictSize)*91 + char2
*
* Slot index → token kind:
*   [0, A)                  dict1 atoms     (1-char codes)
*   [A, dictSize)           dict1 ngrams    (1-char codes)
*   [dictSize, dictSize+D)  dict2 atoms     (2-char codes)
*   [dictSize+D, end)       dict2 ngrams    (2-char codes)
*
* Both atom dicts decode before any ngram, and dict2 ngrams decode before
* dict1 ngrams. So every ngram entry references slots whose contents are
* already filled — no forward references to handle.
*
* This runs on library import. Flat typed arrays store each slot as either
* a plain value (`single`, covering every atom) or a range in a shared
* `pool` (ngrams).
* @param input Packed trie string.
* @param resultLength Expected number of uint16 values in the output.
* @param atomCount Total number of distinct uint16 values in the trie.
* @param dict1AtomCount Atoms in the 1-char range (`A` above).
* @param ngramCount Total number of ngram entries (dict1 + dict2).
* @param dictSize Number of 1-char code slots; the rest of `BASE - dictSize`
*   first-byte values are 2-char codes.
*/
function decodeTrieDict(input, resultLength, atomCount, dict1AtomCount, ngramCount, dictSize) {
	const base = 91;
	const inputLength = input.length;
	const twoCharBias = dictSize * 90;
	let pos = 0;
	/** Read one slot code at `pos` and return its slot index, advancing pos. */
	const readSlotCode = () => {
		const c1 = BASE91_INVERSE[input.charCodeAt(pos++)];
		return c1 < dictSize ? c1 : c1 * base - twoCharBias + BASE91_INVERSE[input.charCodeAt(pos++)];
	};
	const dict2AtomCount = atomCount - dict1AtomCount;
	const slotCount = atomCount + ngramCount;
	const single = new Int32Array(slotCount);
	single.fill(-1, dict1AtomCount, dictSize);
	single.fill(-1, dictSize + dict2AtomCount, slotCount);
	const start = new Int32Array(slotCount);
	const length = new Int32Array(slotCount);
	/**
	* Decode `count` ascending uint16 values from a delta+RLE stream into
	* `single[off..off+count)`.
	*
	*   code < 89   → delta = code
	*   code == 89  → run-length: next char encodes runLength-2; emit `runLength` consecutive +1 values
	*   code == 90, next < 90  → escape: delta = 89 + next * BASE + after-next
	*   code == 90, next == 90 → double-escape: extra char for very large deltas
	* @param count
	* @param off
	*/
	function decodeDelta(count, off) {
		let previous = 0;
		let slot = off;
		const end = off + count;
		while (slot < end) {
			const code = BASE91_INVERSE[input.charCodeAt(pos++)];
			if (code < 89) {
				previous += code;
				single[slot++] = previous;
			} else if (code === 89) {
				let runLength = BASE91_INVERSE[input.charCodeAt(pos++)] + 2;
				while (runLength--) single[slot++] = ++previous;
			} else {
				const next = BASE91_INVERSE[input.charCodeAt(pos++)];
				previous += 89 + (next < 90 ? next * base + BASE91_INVERSE[input.charCodeAt(pos++)] : BASE91_INVERSE[input.charCodeAt(pos++)] * 8281 + BASE91_INVERSE[input.charCodeAt(pos++)] * base + BASE91_INVERSE[input.charCodeAt(pos++)]);
				single[slot++] = previous;
			}
		}
	}
	decodeDelta(dict1AtomCount, 0);
	decodeDelta(dict2AtomCount, dictSize);
	const references = new Int32Array(ngramCount * 2);
	let poolSize = 0;
	let ngramIndex = 0;
	/**
	* Read `count` ngram entries (each = 2 slot-code references) for the slots
	* starting at `startSlot`, recording references and assigning pool ranges.
	* @param count
	* @param startSlot
	*/
	function readNgramReferences(count, startSlot) {
		for (let index = 0; index < count; index++) {
			const slot = startSlot + index;
			const a = readSlotCode();
			const b = readSlotCode();
			references[ngramIndex * 2] = a;
			references[ngramIndex * 2 + 1] = b;
			ngramIndex += 1;
			start[slot] = poolSize;
			const entryLength = (single[a] < 0 ? length[a] : 1) + (single[b] < 0 ? length[b] : 1);
			length[slot] = entryLength;
			poolSize += entryLength;
		}
	}
	readNgramReferences(ngramCount - dictSize + dict1AtomCount, dictSize + dict2AtomCount);
	readNgramReferences(dictSize - dict1AtomCount, dict1AtomCount);
	const pool = new Uint16Array(poolSize);
	let write = 0;
	for (let index = 0; index < ngramIndex; index++) for (let half = 0; half < 2; half++) {
		const source = references[index * 2 + half];
		const value = single[source];
		if (value < 0) {
			let read = start[source];
			const readEnd = read + length[source];
			while (read < readEnd) pool[write++] = pool[read++];
		} else pool[write++] = value;
	}
	const out = new Uint16Array(resultLength);
	let outIndex = 0;
	while (pos < inputLength) {
		let slot = BASE91_INVERSE[input.charCodeAt(pos++)];
		if (slot >= dictSize) slot = slot * base - twoCharBias + BASE91_INVERSE[input.charCodeAt(pos++)];
		const value = single[slot];
		if (value < 0) {
			let read = start[slot];
			const readEnd = read + length[slot];
			while (read < readEnd) out[outIndex++] = pool[read++];
		} else out[outIndex++] = value;
	}
	return out;
}
//#endregion
//#region node_modules/markdown-it/node_modules/entities/dist/generated/decode-data-html.js
/** Packed HTML decode trie data. */
var htmlDecodeTree = /* #__PURE__ */ decodeTrieDict("!}.&u%}'&}*'~!6*)%&,~!J~!J~%L~y<~!R,~~%Lu~~#GD~~#|)1#%}^%}2%+#.##%##%}&%##%'#%##&%#%#'%#&#%#&#'#%%#&#%##%#)%''%&%#%#'%#%%#%%}%%%#%#&(23#%%#&-%0%('1#(##%#'##+%'*.:1}#%#6-+(%'%%#%%%}#L'2351&('%}&/N'(0(/*-%(%%}#'+&T%7.2}#&%&#%#36/5##%&%%#&#%%#))2%%##%&&'0~!#*+&'%1~!%).'3q?&%'1~!.##%6(~!+%%%(Gw'rT~!E#<nA%#jZ~!H%(~!42##~!*31&~!G%U~#)5~#`3~!J~!Z~%]~%Y~%C~!q~!u~#kz~%#~!6'~!D~!U~!?~#T~!c%~!G#'~%7|~!G~!J~!G&~#pb~(Df}#%}*&}#%##%##%##&#-}&'#'&%#.++}%mI,#,@&(}*%}*'%&##&#%##%}&0}#.},U},%}+%}&%}#%##&}B%(}(%}+%)})%##%#&}&%##%&}<%}>%#%&}*%}(%}9%}/%})%}*%}*%}?&}&%}3%}&*#%})%#%#)}#&#-#+*%E%%'%'#%}#*V##&##I}#&&##%&%#&&Qf%%))w/0+&%#(#.%-''''++++7}>%4'',##1,#%#&%##&#'##&#*#9)%&%}#*}%,#+P(%A&%#'&##wSD',9E00#y#@}(+}&%&>~!#~!X}#*}(&&}(&}(,%}%&#+&}#&}I%#%}%)#(},'%#*}4%%#%}(''}#/##(##),%-##%%)#&}(.}&%#&}%%}*&#%},&&}&%}#%*'#%})%}D&}&%}-&}6&#&}-,%}#%})-(~+`~,=?~I9'9%~!,#%})%})%}@%}?%}(~!?~#<~#pP~#BG~#=1#%K+~#?#~%;)~#A~#mF1~#A'~'X%'~#lR~#N~'N~#r~#m#-~#i'?%#'%~#B%##%,%#~#_%#0%~#]732~,w~2+#:&#%&'0%&>%}#>##F+)#%&&#(+_}4&}-%}(&}@&}O7Fdf0@+/v4}&WU##&/0#&'('B#%}.%}'+#%}#%%&#&%#%##+#&#)#6#'#.},%}c%},%#%##%&#&%#&~#>'*-.%##%##%}#%%}%'~#)D1}#%*&~#_%%'(~#S2%'.}#~#=##*'*-%}&'%'##&&~'E%.#&~#M4}%%##&'%#~#O1##%&#'+~#<B%##%%'%+~#;#@%}#&%#&&%#(~#H1}'%'##&&~#?A}&'~#D#%32}'&&&&~#[}'(#%}'~#;C})&}%%#%~#=&%,3}%'(#%%~#^'#&&)#%'~#Y%-~#d-%'~#^%%&#&&&}#~#b~2t*&'~&(~&@~0%~e~3}%*''0})&}+~!9##-}#%-hD*)1fC#%/&/fB#40~!+#)*4~!+~!K'&:~!/*7~!.#~!H~!L':~%x&~!H#~!*~%1~!I#~!+A~#p'~!F~~#-#~,,(~.Z~!V~%;'B'mq-W~!N~%I%#&&#&}#%},%%}'%}+X#%}#&}(%}'%}<%}#%}%%'}'%}:~![)9@~%>~#UA%-%##&~!C%~!-.9:~!1~!-^2/:a~!y,D*J#-5)/4~%23,~#G~!L1~!0X3`~!2+~!!0-~&E~!W~!o,>Y&]~%cZx_&~#O*9#A#'#+I'%#)~!0B*-5A+-((F&*M#)(-7-5+'-3a5Vi~!Y~!?+[)%3),ERHm~!+:D,VG.+)?fB%%*(%)'(#&80%1'8`K8?`+'Z#&O&'H5#*9)A%%5&3))0%39+.*7#()&&*=4@**L)<'_&*+..;(#*+)./&0#3)%')-8(4ixD(&.}%,('aI:,)%,k2231T)I'#/-W7,/'Q#.'Y24+h')37</31&83##&0#),H(?'&?/1##%#&&#%''-%&&&#(&''&#.-'%#%%(,')*'&#&#'##%(%(#%('#&##%%%%('%#%#%%#%#&%##h>w+v<ayvyvcg.uuhKr}g/v|g>u9i[~>g5uI~=RvdwEg;v/g;uk!!TTSx]@RT!U!#!@VBRUU!'UTe-d0c`e&gSdicedFcrdTaqb.kYcAohdYd@a3e+d}dMdtd.aJ#bqcK`dle/e.e'dwdPdodddjbEb}ogd^ofdpduc6j?l%d{drdqc)d7bacOdQ%T#Y)X.sR[yH>6Vyv3[xwLu>vo'!*.[yBacahoj>6Rew3[xqdZa#!a&#^(X-[yG>6Vyu3[xvg3sEr|g.u/Ri9db0T#^(Xa)!-[y;>6Vylg4wKs{JwNZt3@3r=c4Z([xlg;wKt!cpq's@v7A'*a(a+!-a#[y<3Dt?3Dt'>6Vym3[xmg9rxsNJwLZt4~?r?db1T#`-!(Xa,!0[yS>6Vz%NuQs.g4wKtnJwNZtS@3r>c4Z([y%g;wKtrdga8!a(!#&T*Y-Xa#!a0<or[yc3Dtq>6Vz43[y3JwNZtf@3s!Ju}!%Dti:pm3c_%X#tjB5pkd6q!r]u?voC'*-a.a2!0a&a+[yI3DtI3Ds~3DtH>6Vyw3[xx;:s#~<5pKJwNZtE@3r~d`a)!a2T#a.(!+U.X1[yT3Dt`3Dtv>6Vz&3[y&g9rxwzcxstPu.<rAJwLZtT~?r@dZa%!a.&^*Za(/Reu[ya>6Vz23[y1g3sEr}wkg{NuQRg{ci(U#5@b`~,cg#U(2WnH5wugcRh7dX#T(Y,a'Ta!!a,[yZ<]mj>6Vz,3[y+Pv#5ReZKu+=,%!H}7ABwkaS?Rh:BcW(X#<]mrj:ubv/ARekdg%!(!a.*Ta(Y.X1!#sP>Rl*Dt6[y>>6Vyo3Wf*jOvuumvuRgRJuq*!:9<B@bX~3jVv&v@s@5Re[d/rQt{uAvo&a&a*)a2!,0Wf!3Dt0=Bs'>6Re}3[xy~<5s%JwJZt1~Gs)c;&!#2sJkNuXvzq7rxu,Re8dka4!a8(aEZ+a@Y.X1Xa)[yd=Bs(3DtP>6Vz53[y4cX#X&Re:avRe9~<5s&JwJZtQ~Gs*i^rzvdRg+Jv{%!2sbB@bX}kdga,!Za?&^*T1/!a'Dt+[y6>6Vyf3Wf%g/u;s4hGu6?Rh-JvZ,!c%#&RoX54Rivj7uyvf8RgTKvZB%*!2sGh<vu5Rgq<=C::9bb~#dZ#T&Ta6Y.X*Dt>[y93Wf)coZ(T,6VyifluvRgC@95@B@bX~/hFu34cC#T,k/unq8w8Q5RkUklwQuzunq8w8Q5Rk8d/rJu?v8w9)-&!a0a;a&aIWejg3sEr/h1s<DtDJvyZqY5aws3Jvy!&Wei~Hr1:au5@Bag>23E~5c:Z&bX};kKv?w&unuVu5Rjc;>bs)#~@:Rh.=ay<a]C;b`}Vd6s/t{uAvoaxa()!a,a7%-a#a2Dt,[yF2Wo[>6Vyt3[xuNuPRi&NuPwpi#RoWh?vf8Ri%Jv]!%Ri:KvxD!.'2WeAjZu`q9rxu,Re7woeAg-unLq(qA_/*2Wg_g3u5q^9:4E}/jTrxrzv=Wkkd~0UX#^^Xa-a1a5T&a=U1a'*aEa]!a*aPaA-adok[y54Rn>;:p3~Dp5g9rpsFNvZqjg3uJp4~<5p0Pw;5qlJwNZt*@3p1Pw:5p/Ou!5p2JvG'!6Vye=<qnJvh_[xhg3v,Rh3kOwOw-sDuev/Re^dha[a%!%!a+#Ta7)-5TaCaO!aka!a)sf[yb2>Rl!9ARiq5E}Qg=ucRkBE|oJrJ_@Wk~@Wk{JrJ_@Wk|@WkyJrJ_@Wk}@WkzJvO_[y2g-vMRmiKuYC!)&>Ri;>Ri<@3RkNc](X#@9Rk=g5vuRmhKvDB!+'=]meg3u4Rmgd)#Y'Vz3CARmfd`a+!%T'!+#Ta1Ta6TaM-sTDt9[yA9sYd'%Y#s[[xpj:ueunaXRgEjRq,v-vuqdd2'`#6Rev<32@5>:2<E}5xIo9a*X#Y(;5RePJvD_g>vyRgNj8w)v8<wggs:RgXiZt|vjx,hSq3ah!-(~@:Ro/Ou!5RhWj^v(pyw8unRhUdx-UY#^Ua.a3a70!)%UX1TaDa)'omRiRRhE[y:3Dsz=Br,>6Vyj3[xkg6ruwjcqsrPw;5r*Ku]D'Zt-@3r(~?r.i[vwv]dU1a--U#`a4(g/vsRhPOu!5RhLj:rmu9Wo!~@:wdh@g/vsRiTjXuvvNr}:RhBj^v(pyw8unRn]dz1UYa'a+^Y(!aETZalaRY.Ta?a4[yDJw1!#qLsW>6Vyrfzq-pLflpwRe|Js>%!Dt@3Dt&Jvy_[xs~HrnjMuwpsw'RecKu+D#'!t<~Grl~?rjg5u-x,gwp{ah!-(~@:Rg~Ou!5Rh'jXuvvNr}:Rh#cW#X/c;&!#2sLi[v7u7RgpJv)(!iLrxu,Re6j7v@s@5Se[e7d`aW!Za(a`T.a#!a3!&aDa-!9)Dt_=6s+3[x~~DR|h~DS6avhGun5RkZj3w)v-]mkKunB!&*]kb97R|i<ARk<c:Z(6Vy}Juh'!wziMRoS:F|vkLuauJv5vtvQRh1d='T+Y#VyO~DR|jcF#T'7R|g97R|kJv3'!ay<Rj,Jvh&!:ReXcsa6*a+#a#_aIRf9aLRf?c,Z&Rf5Rf7c.Z&Rf;Rf>cQ#%T'p-Rf8Rf=ct#%'(*!,p,Rf4p+Rf6Rf:Rf<d~'Ua%U*^UYa(!a,-!#a4YaTalaEX0a8a<Weo3Dt/3Dsx=Br93Wen~Dr;~<5p<JwNZt2@3p=Pw:5p;Ou!5r3c7&!#:p>3Ds}KvGB)_6Vyk2sM=<r7x'eovA(!hFu1ARf}cV#X&@r5j6rvwQa^Rf3c=Za'wkghJv__g;unRggA53B9=b^}%j6uduo5Jq;!(hIv%2Re`Ou4ARe_e%a#^^^Xa&!a*a2!&a6YaP!*ad!#a:aE/5Rn?[y@>6Vyp;:pE~DrY~<5pBJwNZt8@3pCh=rt3rWPw:5pAJup_[xoNuPpF9c!#'45pD5ARn)d8#X'X*3@rU72s]h>v<<sSjJpqvewOJq/(!hNw'5ReBk0s2u3w/w'5ReE5@Jq.!a+JQ!&WeU23d(#Y&RjG5]jBk!u7w&u0udARjEe#+^^^Ub#!a2/a`Z(agT1!a-a;|@TaG!aS[yV=Re~fow'RguNuPRe?bz#'>RoUWeL>:Cbb|?JwPZtVg6ruRmzJvD'!6Vz(g/vmRh~Jvy_[y(g9voRgyx*cy(#2>Ri2B9b]~9kIw9u7rluJu3Rg]dI#a%UY'@=p%CAx.gQZ&RhwwygtRm{x5g_Z'+ABqR9Woa=Bp&dV#^*Xa'!&@o{g4v]Rk;Jv{!%Rk[wkkiA5RkiwwfUB=x,fUuqC&*!>RfTg8v0RfV~ARfSd;rJsAuAv9wR'ae+/aO!a@aza/a#[yQ@Wg!2Wemg3sEr0JvB_g>uvReWg2v+Re=KupB_+[y!2AbY~-~Hr2AJwD!(h<~El>h<~El?Kun@+_:9b`}Kg-v/Ri3g;vtwyk_9]k_d=&T#*U.6qh@Ab`|K9:H|CJv[!&3Dtex'fDwC%!Rf[9WlMd[(^X,!a%Z06Vz!@WgBg=v~Rgvg,QRe@awd,#Y+jTv|Q~EfWj]uNr|~FRfXdy#Y&^Ua%!aO.!(a)Ua;=!a@aKap!a-,a!Ta]a[rSa]p?[y82sK=Bq~;:p:~<5p8Pw:5p7d'#Y'Wf(;RnRi[u4w&RgJJvG'!6Vyh=<r#ijuuv/sIKuYD'ZtG@3p9~Gr&d2#`(g<vtRgFj`u5w&rqpxRf2CJuY!+:wfnTOu!5Rg}jNs1ucv&RfwJvA!&3@q|BDcC#T,k/unq8w8Q5RkTklwQuzunq8w8Q5Rk9dga#!a'!a=#a0!:+Tb*b@aO.a4!aba8aFJv^}?!VyR~Dr<g;u%Rn.~<5p[x'e`wNZtR@3p]Pw:5pZhNvjBp.woe_g5u-r4JwF!%DtO3:ooc7&!#:p^3DtpLuGw(!+%)Dtk6Vz#2sd=<r8d'#Y([y#<x3gJt`w@!)%}MRiowzikRij=]ilxAf3,U(#B2Rf#g0v-Rm[ck{`U#]giKv3>)!&6Ri154s,KuGB_%@r68r:dJ|t`#X(9<E|u2@H|rx3gJu?w'!+'1Nu7Reg4=H~+9<wxgY95Rm]xLggZ-`(X}U2:Ri4h<uOawRmsJv__5@bb{jbV~3dka#a'a]!,#a+U=a>b6a3b%!/aKa/)!arwve^VyJ;:pR~DpTg3uJpS~<5pOPw;5qmPw:5pNOu!5pQJvG'!6Vyx=<qoJvA!{~Jup!%@qk7Rn/KvyD!}''[xz;>wkh'?Rh,x8gyt`w5D!&),(SgyccRgztJ@3pPB5p#d'(Y#<]mmifubw&RgoJvE&!82s^JvF&!8Rf,ADb]~;x=h'rNu]vK!,%'*0RnORh)4Rh*AqQg-vaRnNg;wHwkh'ba~4cE#Ta*x3gctyw@'!+%RnFRnD<4Rn@hFvK5RnCxWg[#`&a0Ua()`1Rm75Rg[c]%X#qi8Rg^NvdRj>BwzgZauwji7Rm6A4wgg]d1#&(*,.0a#Rm;Rm<Rm=Rm>Rm?Rm@RmARmBe%#^^^Xaea?aC/b+(,!a+a#!a/!>a&Ta<aKbD!2wphBRnk[yPw}hE|.=Br-3Dtm>6Vy~g6urRf.x,hPrNav!%'RnqRo%Ro#Nu;q[Pw;5r+JwNZtM@3r)d'#Y'Weh;xChL#`&RnmRnoKu}>%(!Rne~Bs-;2wjcussJv+'!aYSO}6@B<5?ba~8LrNvj!.%*ROwungw~ng~:9;Ri^>wtnig;wHRnixDh@|(UZ.x1h@|)!#:2<H|*xHn]#-UX'3Ro)z=iT}6ARns=Bwsn_wpnaRncw]aR(#UXa&Ua*a/=]iPd'#Y&Ro'WnXf{QRm2hNvj]nZd`'T~&1`{|`#9b]{}c:'!#Wl{>@=be}]?cl{{U#:5Abb}Jds#^YaF!a*b4a#a3aPa>&Tb!bH!*a_!Eau?/a&RjY<]gj>6Vz*;:pe~DrZg,QRj1JwNZtX@wihspcJvZ&!VyX9WmOJu|!|N2WmHJvh&!]ht~Bpbcn&T(!#RmQ<s7Nu;padH#X'`+WmJ@>RmKCARhnKup=!)&Wf+:RhqNuPpf9c!#'45pd5AwghpARn(Ls@w!%,)!RmP@Wfe<E|IJva!&WmNg8vsRmLd`*.`#Y'Xa!axRn*]hrA8Rhug5s@rXg8u!RmMd8#X'X*3@rV72smdI*#UY&RmICARho~GsgxVgd)Ta'U-Y&Xa!T#RnEWnA@Wffg1uDRi0hFvK5RnBxGnG&#`%owp)@wsf+bX}Ze-*1!a*^^^Ua|!#a.aq&Ya2!a>.a6!a:aO`aJDtL[y`@Wg#>6Vz12@wzoYRoZNuPRi!NuPRhzg=ucRi,@=b`{Yg=ucRi-ACJvB!&Sh[ebSh]ebi`wUuFRm4Jw2_[y0JvB!.<Ju(!&SoG}6Shd}6<Ju(!&SoH}6She}6Kur@._g5vHRieJvx!{L2G{Kx6gd'T#?Rh82Wi5cZ#X(g1w)Rm5dW-Y(Ta#!a)!#aYa=wnfE=su2>>bU{0j9udv:<svj8uQv-7RgHdE%#^'sq9sp=>Bb_{TJv`!&g/r|snj6v(us5d,#Y(56H}[978H}]Jw5!&g1rushJvB!+j;v{u5?zDhd}6}bj;v{u5?zDhe}6}ce*#`(^^^a[aea!=!a6a*aoXb1a.!aAbL!b>,b'aL!aV@Wf|2Wlg3[y/JwNZt^@3piPw:5pgJunZou3@rsJva&!Vy_g<v~Rm#JvG'!6Vz0=<r{Ju{%!:pj@WfsiXuJu3Rm:JvZ&!WfA~Bph@c4Z&Dtwax5rubx(#:awRk1@d,#Y&RfjRfid1#,Y(@Wfp2Wlrg5s@ryKu[@!,'=]ig9wlk?Rk>g5u-rqJvy'!@9RkQcH(T#=>Ri~@<wkj(Wj(KuZB*!&<7rw@9RkRcH(T#=>Ri}@<wkj)Wj)dg(Ta2Xa9X#`-!a*CARhg@@=I}d9x;c~#X%so=<sj>2@@=aybb}XjWv0Q~EfEj3vLv;<d,#Y(56H}`978H}_dgaPaFa'a/!#a3Y0a_a;a|!1(a7-[yE3[xt;:pJNvZrrg3uJrvJwNZt=@3pIh=rt3rxPw:5pGOu!5rpJvG'!6Vys=<rz@c4Z&Dt(ax5rtJvZ!&~BpH@wsfNg-vaRlNci*U#=<wei<F}a5@Jq.!a*JQ!%@qZ23d(#Y&RjH5]jCk!u7w&u0udARjFd/prq=tyvpaEa(a:.!a1aZ(@@=I}:9wpd%=<sX55w_h}@@=I{t=ay<aU@@=I}T=ay<2@@=I})?C9:9au@9Cb]}DP~=x-fAZ(2Wl1=ay<aU@@=I}>5@d##Y+jTv|vV~EfFj]uNpn~FRfGdgaK!Z2&!a8a-Tb({E!acTbM*!a(DtY[yYd'%Y#sl[y*hHvh>Re5x2c{Z}.j4uCvcawRiMd+#X+_x&d!},<5RkX;2Hzw@x,gavfB-!{CcF&T#Roe;RodwWbBg5urRgaKvHC*_6Vz+<4opieuew&Rmq@d]&Y)X,T#X0Rh}<BqP=4qS9:ReMg/ujReNJw0!/<Jui%!bd{kawwnemRelAxUa?a3#*.&UX(Ya+a/RhvRnQ<o}9Wmtd-#Y&RgSRmw9;Rmxay=Rmyg-vaRmuxEhSrNu,v-voC!%(aR.a(a7+1Ro1>Ro5CE{A9b]{@;5x#eO{:g;urRi+KrNA!%(Ro3>Ro79;Ri_Ku@>{;&!x%gX|{KunA_+g5QRj/g3u5Rj#g>uERj%wio/xRhS&!,!#^1U}wba{8>>@=be}qC@:D5ba{7Ku+A&!}x?ba}t>>@=be}se(aA^^^Uat!b0#{pa+awUazbGa#aLb9bgaWac'a5TbS=Br!d1#`%scp_Jvl!#rT>Re0JvX&!VyN=H{Fcm#U&:pY=ReaJv2&!]h0=]nUJvG'!6Vy|=<r%JrM_=]h2@Wlud'#)U'Wf'b]{i=]h/Jvh!&~BpWg=v]RnMx+ny#'Nu;pVwjnu=]nwxJnx,T#`&Reqwjnt=]nvieu9vrRjLLuYwP(#+!th@wih5pX~Gr'g5v/Rh4KunA'!-CARnP@wwiN:Rm_9x'cvw>!|l=<saKvAA!0&3@q}>w^e1bp#&Re2Re3BDx7gH#T|f5H|eKuZ>!%(:qNAH{]Jv6!+3B2B9=b^{X<5<B92:E{ZLvhwA(a;a%!igQuyRmad+#Y}m@3Rh5d8#X'X*:AqUAHzmaxwbh<aXRnVcF}RT#Nw&cj#U(BWnug/vsRntdka)(a3+.Zb7aYYan1!bVa@Xa}[y^@b[{G=H{+hFu73Rj&Pv#5ReQcK%T#sig1v{Rj'Ku+D#'!t]~Grm~?rkKuMB!01d5#`'Vy.ta3Dtu~Hroc8#'{^45s85AwZbP&!#Rn!wghxWn#KvEA!)&2RlA2RlBx:h|#(T,=]j09Wobz>x]z/@awRoTd+#Y(az]hFhCrm4d,#Y+jTv|Q~EfMj]uNr|~FRfOdCa!Xa9_X#@<plJvf!%b`{(9;Rgwc;.!#2x7cw#T|UDb]|T5Ju={(!=@E{&Jv)&!Ab`{'awJvf!~*>>@=be{#KuY>!+&4Ezyi[ugv&RjIdea+T)#UXa&T-T&a!Rh9auRmW=]kLg5vuRn+g3u4Rn-Ow6ARn,hHus5xNk?#UX(U~)/g8v0RkD~AwkkF?Ri.OuNBwkkA?Ri/d|a2`a*^UYa.!aBTZaTa'Xa;!(!2!-a#b2[yC>6Vyq3[xr2Wi?g1rusVh%s?DtF~<5rbJs;%!DtBfswKtCj[uvuSsEu3RgVx3o:u+wN'*Zt;@3rd~Grh~?rfg8w)Lq)qE&-a%!>bI|`jWv0vV~EfCjTv|vV~Ef@j]uNpn~FRfBcK#T']gWNu7x,k7q4ai(0!hHv8<RhmkMu9vrsBuev/RhlCJvB!,g<v{wchh~@:Rhji[vrv{wchi~@:RhkdS&a5UY#Ta!RgPwwiI5BwciI~@:Rh`x'iJvj'!5]iJPu8Bwch]~@:Rhach)U#h3rp]gLh@t|Ax,hTq3ah!-(~@:Ro0Ou!5RhXj^v(pyw8unRhVd|)`,^UYas!a?/a2Z'a^Ta{Tb7Ta(a#!a,Wf&9sZ3DtAadamov=Bqt3[xig8vsRm~>waiL2b`{QJv*_Ouv2qgj<v]v2BqfdR'X*X#Y-@3qr~Gqv~?p6hHv-]glPup5Lq+q?_%*b_{qF{n9b^{rOu4ARhpKvCD!+&~Bqp:5Dbb}nwoiKl&unuTuBv]v+ueunaXRf0=Jvh!0nKufu8v1w&w7q%w&uHrz:Rgnj5w,uxDJq/(!hNw'5ReCk0s2u3w/w'5ReFd>Za&!*UaA=<wkgsRnSJv^!%Refifw3vyRgOKu_B'!,<]gkiiu:w&Rh<=C@a^<B57@2F{[<B5@aW:=3away9A5aW=<B=C@a^<B57@2F{Ie-#`(^^^bCara.b8aza6!/bZ,!adTbnTbOb+aFaS!aAT9@Wf~2Wli3Dtl2@d,#Y&RfnRfmJwJZtN~GqyJva&!VyMg<v~Rm%iXuJu3Rm9Jv[_=]ih9wlkDRkCd1#`(@Wg>2Wls3cH#T(@<Rj*=>Ri|b~'#23s9h<~El.d'#Y&Dtxi^rzvdRl#d*#U%(o|B2s`hJwSaxRmDKv4B&!1:Rmdd5#`'Vx}to~Hq{x'f1v3(!BA5ba|bJv_&!Wfug1v]ReIdO+U/Y#&G}-8wze=Rh{g1v]ReHg/uQRf/by#)ibQwERl/cH#T(@<Rj+=>Ri{cNu+vlax-!(#a0qa9<Rii2;;bU{H;x<i=&X#Rk`<4wwi=C9H~8xAI(Y#<azRi@45wXI<B9;5bb~7dL(X#Xa(+!aL6Vy{g5QqOau:5au2@ay547EzbxOcU(UX-T#Ta#:Cbb|A?wjh/b_|SOw6ARgtihr}u7Rhy<d1#T)X1@@=I|~=ay<2@@=aybb}Sj3vLv;<d,#Y(56H}A978H}@dGpvs@uAu`vcw9*!aFa+ai%(b!aXa8.a?a[ozWey=sU2@G}Nch&U#Rf_WexKu+D#'!t:~Gr`~?r^j]uNr|~FRg*j^psurwJt|RmcKv)@&!)7Rkv~Br[@wxfO:Rl3co#U'6Rezj_q#vIuavjRltwzeyh@vr5JqD0!>aY?C9:9au@9Cb]}9cl#U*5;5<H||jbuus1ucv&Rfvg1v~d/pppzqFr^a--a~!aMat1(hFv;Wiz@@=Izoj5uuv-7Rix~Cw`fk2WlVcZ#X,k)u3vWs@u2]ktg;wEx'fBq(_2Wg/jTv|vV~EfoJv]!15x'hzqG!(P~EfU~CRl_j6v(us5x4i-#T(2WmZ?C2F|d>Kq<aj1!*jTqIsBv=Wl`~Cw`fi2WlWj`v0u*~>RlR=c>Z,k#u3vWs@u2]kr<c1Z+jTqIsBv=Wla~Cw`fm2WlXdmb3!a{(arZa`bkTa%TbQTa-a9+c'!aM!/[yL=Bqug.w'RifhFvyDRj.g>vgwyk^9]k^Jv3_@WfbAARkhJw2_[x|JvB_wkoIRoKwkoJRoLd'(Y#<]gm=<9<H|yd'%_X#skDtb3awwqkgNulRkgdB#^',9:p'hJwSaxRmEBwVb8@4=H|qLu+w50&!)@3qs~?pU>Awwn;;Rn=c:Z'ARn<=<qwKvC@!/&~BqqJv6!&]eVb^z^xRge'/a%+^`#Sge}6<4Rn3=]n0Pw2>Rn8Jw0!&>Rn:>Rn6cY#a7+!a&=<wkaNw~h3z_c5Z{=wjh#=]nLKv^D!&)Vyz=bW|swYb<WetcG#T(2wxa@qVx@gD#Y&b^|V5JwG&!5bb|pg/w&RgD@x=kHs=uAvn!a%%/'+RmSRh694Ro`g-vaRmRhHv-]mlxCcS#`&ba~.5cD#Ta)P~=d,#Y(56H{>978H{Dd_#{2^Y%_+qbbb{6g3sERhsbU{?dfa.,`a(Xa<!aiX#(55RiG54RiHcI#T'WiU3RiVNvdwtfcRlKNvdd,#Y&RlHRlExQgf.1*^T'X#Sgf}6Wn4=]hfPrk>Rn7Jw0!&>Rn5>Rn9Lunw?&a2!,5<oq@@wqfdRlJj5Q~=d,#Y(~ARfcOuN]fdDKw;ay(}i!547E}j?cI#T(@5bV}iCbV}hdv(^^Tb?a40,b##Tbo!a*bR!a<b|a/!aKai!aU[yK=]o^g:v>ReGJwPZtK<7Rh+h<~El,Pv#5ReR@awwxjCg,ulRjDJv6&!]j!z?aQeeg>w=Sh<eeJw;!&axEzOg,Qosc!#*:wkeJ]eJ>x'h-u(!%Ro.w~h.zPdNZ(X,Ya![x{;9ReY;wkgxRiF:x?ap#Y&RmUg<s2Rkod]+UY0TZ'!a&A9sw<=bczLNvuw{gqzNhJwSaxRmCKuLay!#&s_Rf-55b^{uJvZa!!c%#(55Ri654wmiu5RiuawLu,vp!+}^%b_}Y9;wkgxba}o>A9:=b^}zKuh=a''!3awRk3c*'!#aHRk6c+Z&Rk5Rk4Jv)&!awRjSawd9*`#0?C2@EzMj8u<uJ5RmbjQrquJu3x,k>uq@_+=ayb^|W~ARkEOuN]k@7dhzV^X/X&a-#zRzSb`zXcJzTT#2WkVKvDBzW!%FzY9;5bbzWjQrquJu3Jw3%!b`zU=ayb^zQd:#X(T-a!6Vyywxh}=b]{Jg=u1RiAdGp~qHtzv!w(wA+a+a;<!aJaYai'anasb(=azRmV:Cbb{MLq2vb!%')RjuRjrRjtRjqx3jnqCw3!%')Rk(Rk+Rk&Rk)Lq2vb!%')Rj{RjxRjzRjwLq2vb!%')RjsRjpRjfRjex3jcqCw3!%')Rk'Rk*RjkRjl9<CbbzfOu4ARhxLq2vb!%')RjyRjvRjhRjgx=joq*uKvb!%')+-Rk.Rk%Rj~Rk-Rk#Rj}x=jdq*uKvb!%')+-Rk,Rk!Rj|RjmRjjRjidAq&qKs@uAv8Aa.'*-a@a&0!aM@a5[y73Dsy3Ds|3Dt):wxgI2sHJwJZt.~Gqxwsf0ikrzt}Rl0Jvy_[xj~HqzKv_A|D!&WfP8axRoVcf,U#k(v]v+ueunaXRf1Ju}'!g8u#Ri=jQw!sCunLprq>!,')~<5qeGzq9F{W=c##%s5au:5aU3CBE|;d4#X(D!a&6Vygx(b;#(=]ed?C2F{N<capoq2r[a&!aPa9,'Pw;5s:@@=I|,55w_h|@@=IzcP~=x'fCqB_2Wl2>aU@@=I|1OuNBc1Z+jTqIsBv=Wlc~Cw`fl2WlZ~AcTa%!Z+jTqIsBv=Wlb~Cw`fh2WlYk+uNqJsBv=WlSg,u3dca3#UXaMYa)TaB-=cM|7T#<bI}l5@B932:aV2G{BOuNBJq:|M!5Ezt=<B=C@a^<B57@2F{v>cB{/T#=ay<bI{3Jv6!a.6BKq0ah&+!5E}HP~Ef{978BaU@@=Iza<7d#.Y#978BaU@@=IzH~AJq0!(@@=IzG978BaU@@=IzFe,aU*Y&^^^bvJb,b:bFad!a,c2Ta>aL.bo6!a#CbTa'T#Re{2Wlh2@G{yg6t~Ro_NvdRfticuRQRllJv3&!x&c|zs@Jw3!%RflwpfkRlpKuL;%(!Re<@G|C2GzdhIvuBwgjAg-u0RjAKQB%!(GzZ@G|5NuuRl7d='T+Y#Vy[g<v~Rm!==G|>JvA!)@wma=]m1ifuaw&RmnLs@vT'!|/+[y,g:v>ReTJw1!#qX=x!eC{bLu+wT&)ZtZauq_~Graci&U#F|89:r_Lupvq!.)&2RlG8RfaC=x!eF{_h?rpWlmd&'!#X|&]k::xJey#`'T|+<E|&2@H|%dE#(^,g;u.RiEg6vjRiC9xCkA{O|zY#g=ucRmXKs0@!&*@G|m@awRknJuh!,3d(}gY}eJvj!%Rm):Jw3!%Rm+Rm-Ls0w(&!a(a#@b[|6cZ#X'7RkxWgAOu4ARn'dH'U#Y*Vz-Wm'CARm}d]*#a%^a*T'aK!a<9bV{PC=p*Jw4!&SgxcbB5r]idw(wBRmF7xFkt#&`(Rm/Rm8E|!JuY_9:Rl5=wrgr2:bbxd@xXfB(a*#T+!.X0X1Ta/a'T&RlDRfL>RlyARl9b[z[>RfZ:RlL:RfRwlg/ARl;9;RlxKv,A/!%7s69<74=BA5ba{-8Bde#`a<XaKYa1,a'P~=wxfB2bZ}}?C972@@=I}r8@55B9;5bb}G978B2@@=aybb}3j3vLv;<Jw3&!>Rfk=ayb^}4~Ad1#`*@@=aybb{w2@>==<bbz]dx+UY#^UaF!a9!bB'Ya1.!ajXa#%olRhD[y=3Dt#Ov5BrHKuMB%!(Rf^Wep~HrJwkiQjKr|~FRg)Ku+D#'!t5~GrF~?rDdV)UY,Z/_7RkuG{<~BrBg,rlsO:235B@bX}|d?a1!#`(6Vyn5@d##Y+jTv|vV~EfIj]uNpn~FRfH7Lq2vb1!a9-978BaU@@=Iz9978BbU}#~AJq0!(@@=Iz8978BaU@@=Iz7~AJQ|}!978BbU}!JvkaK!AdUa21-U#`a+(g/vsRn~Ou!5RPj:rmu9WhOjXuvvNr}:RhAj^v(pyw8unRn[kPr}p|u7vwv]RiSBd;pppzq@qHQa?(b.!a.a`@.|xa(hFv;Wiyj5uuv-7Riw~Cw`fg2WlU978BbU|wOuNBJqG!(P~EfD~CRlQcZ#X,k)u3vWs@u2]ksg;wEx'f@q1_2Wg.j]uNpn~FRfqJv]!15x'h{qG!(@@=IzK~CRl^j6v(us5x4i,#T(2WmY?C2F{1>Kq<aj1!*jTqIsBv=Wld~Cw`fj2Wl[j`v0u*~>RlT=c>Z,k#u3vWs@u2]kq<c1Z+jTqIsBv=Wle~Cw`fn2Wl]dn1#c(a(b^a2!b/bAT(bj!aDa7bu,a_a{c0!2T0g:v>ReD2@G{42@G{5~DpM~<5rc=Bx6i>{RT#RnI@zCx]y]z:2Jv[!zr5Awyk]9]k]dD(Y+X#6Vz.g=wKtgwhaCwgmTWj2Lu,w%_+/[y-B;b^xeg3u3Rj-2@bX{*KrJ<!+'@Wg(g?QRlC@Jv`!%b[zIwsfII}8JQ_@w|kW|=Jv(%!AqcOuNBJvEzh!bYzjLs@wP#(0!oy@>RkdJwMZtc3Dtd@BcG#T'9bWxg2@2Fznd*#Y+;2x'c}w<zizixNgwa#Z'U+!/!a'!a+w~g~z6wcn{Rn}wcnzRn|5Rh%=]nJg5vuRmvNvdRlvcprJu}w*az*a#!%.a.'Bot9qT]kj@Wg'ay2Gzv@Jv`!%b[zEwsfHI}1;ck#Ux`<Cbbx_Lu+w!a&0*!wko*wwo,So,}6Juqxf!E}PigQuyRm`d3(`#8>Rn%:A5B;bZ~%KvhCa!a2!x>k7#Uxb@b{#xaRk7Jw0!)>wwhlShl}6>wwhmShm}6CJvB!.x'hhvj{!!5Bwkhhbaz}x'hivjz~!5Bwkhibaz|xEhTrNu,v-vpD!a%&/)a3a.,%Ro2t[CE{)@3re9b]{%wjo09:rgc:Z&Ro6=<riifuaw&RmoKrNA!%(Ro4>Ro89;Ri`dSaL'UYzxZb)7Rka3xRhT&!,!#^1U}vbaz{>>@=be}yC@:D5bazzKu+A&!}{?ba}y>>@=be}wxBh[t`u~vJvr!%a!a()a,a0a4RoC=]o;Ju(!%RoGRhdwjh`=]oAg>w#Ro?g5vuRo=NvdRl|Ku]C.!&;RoEJvB!%RoORoMBx'h[v+_?w~h`}~5?w~hd~!xKh]oiptu-utv.vp!#%&a30a@a'a+(a/aOp(o~p!RoDJu(!%RoHRhewjha=]oBNvdRl}g>w#Ro@g5vuRo>c[#X']o<CauRoRAd-#Y':RkpauRoQKu]C.!&;RoFJvB!%RoNRoPBx'h]v+_?w~ha}t5?w~he}ue!/UbhYacXaW^Tc&a;b:a-c/#b&aja1(!cL+!bKbt!bmcRc9aIc?8[yW3Dtt94Rg`Jv}!&SiRMzBhEebShEMNuPRe>x7gL#TzuwjirRipc<Z&>on;>z=h-MSh.Mwqczx'a7vj&!>Re4@=ResJt__NuPRi*NuPRi)j]uNr|~FRfzKrJ>_+@Wfy@Wf]2WocKrJ<!+'@Wg%g/QRl@@Jv`!&awRl<wsfFIzgLu(w*!.*&ShBMwvhIRhI9;RhNx1hK'!#Sn]Mx1hK~0!#:2<H~7cNu+w7D*'1ZtW>Rn1~?rOc:Z&Rn2=<rQ<7wjh&=BSnLMc]#X(6Vz)w[b=a!U#9wzgMc3#&(RgMRitRis<x,gKt`ax!&+SioM=BSilMc3#&(RgKRinRimKurB,!&SiQMzBhDebShDM6BJQ!(P~Efx978B2@@=I}WLrJw!!,a*&@G}O@9wkibRid@@x'fKwC!&SlDMSfLMjUv~Q~EfKKv3@a+!(hFv-]mpx/hYZ(C5RiWz<o/MwkhY?So/M@x,gbvfB*&!SgEM:SoeeehFu3:Rgbda(,^TZa)X/7Sg[eb:2RgI~BrMC@wgkc:wwkcRerx3h(uUvK!&*,SnOM4Sh*MArRg;wHRh(x=h;rJvPwI!a4',a'0@Wg&=BSh/Mg>w=Rh=g3w*wwgGRgGcW(X#;Sg}M2Gzk@Jv`!&awRl=wsfGIz`dKZ*T'Y-:RhR7RhQg5u-p`j6v(us5d,#Y+~Awkia?RicOuNBwkibba}Ld6p~tyu_vbAa'a+!a/'a3aEa8a!>Sh,ebJv{!&Sh@ebSaReb9;SgwebNuPRi(NvdRl)NuPRi'hHu^<Rm^Jvv_@Wl(g;u1Si/ebKu'B&!*Sh?eb@Wl'z@aPeb95Si.ebcpputyvjB)!,&a+0a%ShAMWeK@G}C@WfJ9;RhMwvhH9w{ia}ix,hJvRA1(!zAn[MRhHx1hJ~*!#hFv(BSn[MBJQ!(@@=I~'978B2@@=I}2db.Ua<'X}+T#a0XaG2G}E;wkg|wuh!Rh!x,hZu,@)!&So0MVy)C5RiXACJvB!&5RiY5RiZg8w)cG}*T#2@bU}=KsA>(!a.3wkhZba~(x,h^u(A!&(SoCMRhb5Bz=h[eb?w~hb~6x,h_u(A!&(SoDMRhc5Bz=h]eb?w~hc~6e)aA1T#T,^^^c-bMb&blcPaP(a/!0!bA=b5c@a(!bfbrc#2afwmhARnjwchORnp2Wlf3DtsNvdRl-2@wpa<]m0bx(#:awRk2@Jw3!%RfhwpfgRlnKQB%!(G{V@G|'NuuRl6d='T+Y#VyUg<v~Rl~==G|<Jv+'!aYShC}6@B<5?ba~8@Jw3'!g2QRljhLrpWlOd+#Y'g.w'rIg>w*wgj@g-u0Rj@Lu+wT&)ZtUauq]~GrGci&U#F|39:rELrNvj!.%*RhCwunfw~nf~:9;Ri]>wtnhg;wHRnhx3hDs@v~!/+'@Wfr@9RkSNu&Rlo=@<5GzoKs0@_+@Wl+@awRkmJuh!-3d(}pY#qWJvj!%Rm(:Jw3!%Rm,Rm*de&!1U-U#`)Re;@G|.@9Ri82@wjfvRlq=@<5GzpLvOvr!).&2RlF8Rf`C=x!eE{.Jw3_g2QRlkhLrpWlPde(!#U{s,UXa*Ta'[y'g:v>ReS;x0PZ&RnlRnn~HrKJw1}f!=x!eB|2w]aP(#Xa&a*Ta.Ua2a7=]iOd'#Y&Ro&WnWg;u.RiDg6vjRiBNvdRlzhNvj]nYJuW_2Wm3x)kFze{9d])!a.!,Y01!#&aC!a3RndC=ox~BrC@2b^{pg,rlse7x'ksuq!%Rm.E{xidw(wBRmGx9o+)X#wwo-So-}69:Rl4@xSf@a#XZ'X)X,Ta(/ARl8b[xc>RfY:RlI:RfQwlg.ARl:9;Rlwdn'#^XafaQa1X1TaHTa)@b[{zcZ#X'7RkwWg@Ou4ARn&x)kG#{,g7u/RkGdH'U#Y*Vz'Wm&CARm|bx#(A]gUbUzJj9Q~=d,#Y(56H}l978H{U7d,0#U*2>ABb_xZ978BbU{e~AJQ{g!978BbU{hxMh?ad{oUYZ.x1h?{l!#:2<H{mx3n[t{vl!,&a%3Ro(z=iS}6ARnr=Bwsn^wvn`Rnbd`*T}B0!#^X'BG{c9b]{a>>@=be}F?JvS!&BG{d7BG}(Bde#`a1X,Ya@!a'P~=wxf@2bZ}I56B2@@=aybb}08@55B9;5bb}<j3vLv;<Jw3&!>Rfg=ayb^}&OuNBKuLA!)a!P~=x#fD{f2@>==<bbzl?C972@@=Ix^d6rSu,v7w*C(0a)a6#B+a%!sQ[y?3Dt%3[xn~<5rLOu!5p@Ku+D#'!t7~GrP~?rNKvlaya7'!h+v-5qMg=t|cd,U#5AAaa5Abb{S@52B5@a[@52B5Gx[iXueu;d<#`a(!/549C;ag>23ExY5@Dah89b^~689Jv)!~2b[~1Lv'w(%*!a#bX|aPrmawRe]keu7uhv-q6rxu,q`xTo]/a5aU!bNaDXbi!b-!ao!b<bwA!#5@B932:aV2G|:d-)Y#hJrL>RhG<7@C5<H|_=Cau:5aj5@B932:bJ|ng>vIbs)#?C2F|9jPv0w.vISh-MKvUaz(.!9ABbb|[5;5<H|Eg>unwfh;9:4E|YjQsBt|vjx'hYq3!(?C2F|J:2<BaY?C2F|GOu!5x,g|p{ah!-(?C2F|c9:4E|OjXuvvNr}:Rh&i[w*t|cd+U#jJvsu)vsSn~Mkfrmu9p}u7vwv]So!McW#Xa!ax5@A5aY:5;5<H|>kJv~vYrquJu3x4ib#T)2@SmZM?C2F|Bj:rmu9@xPhI(a*a#U#`a3-5Abb|L~@:RhK9:4E|0@52B5G|#C::aY?C2F|-:2<BaY?C2F|.5Jvk!a)javYrquJu3x4ia#T)2@SmYM?C2F|HAxPhH(!a#U#`a*-5Abb|4~@:RhJ9:4E|R@52B5G|F:2<BaY?C2F|Sc^#Xa2j=Qq5CJvB!-g<v{z;hhM?C2F|Zi[vrv{z;hiM?C2F|XKsA>!a)-g<v{z;h[eb?C2F|]i[vrv{z;h]eb?C2F|^iZu.vix,hZq3ah!.(?C2F|QOu!5ShXM:2<BaY?C2F|P", 13494, 2713, 49, 25, 61);
//#endregion
//#region node_modules/markdown-it/node_modules/entities/dist/internal/bin-trie-flags.js
/**
* Bit flags & masks for the binary trie encoding used for entity decoding.
*
* The trie is a flat `Uint16Array`. Every node starts with one header word:
*
*   15..14 VALUE_LENGTH   Number of words the value occupies, +1.
*                         0 = no value; 1 = value inline in bits 12..0;
*                         2/3 = value in the 1/2 words after the header.
*   13     FLAG13         If VALUE_LENGTH > 0: semicolon required ("strict"
*                         entity; `;` is never stored as a branch).
*                         If VALUE_LENGTH == 0: this node is a compact run.
*   12..7  BRANCH_LENGTH  Number of branches (or run length for runs).
*   6..0   JUMP_TABLE     Jump-table offset / single-branch char / first
*                         run char (see below).
*
* Branch data follows the header and any value words. Its shape is selected
* by (JUMP_TABLE, BRANCH_LENGTH) in the header:
*
*   Single branch  JUMP_TABLE = the only child's char, BRANCH_LENGTH = 0.
*                  No branch words; the child node follows immediately.
*   Jump table     JUMP_TABLE = first covered char (> 0), BRANCH_LENGTH =
*                  table length. One word per covered char: 0 = no branch,
*                  otherwise the child's offset from the END of the table,
*                  +1 (so 0 stays the no-branch sentinel).
*   Dictionary     JUMP_TABLE = 0, BRANCH_LENGTH = number of branches.
*                  ceil(n/2) words of sorted keys packed two per word
*                  (low byte first), then n pointer words storing the
*                  child's offset from the END of the branch data.
*   Compact run    VALUE_LENGTH = 0, FLAG13 set. BRANCH_LENGTH = run
*                  length (3..63), JUMP_TABLE = first char; remaining run
*                  chars packed two per word after the header. The target
*                  node follows the packed words immediately.
*
* Pointers are end-relative (rather than relative to the pointer's own
* position) because that makes the common "child encoded right after the
* branch data" case a small constant, which compresses far better. Offsets
* to already-encoded (shared) nodes wrap via uint16 modulo arithmetic; the
* decoder masks navigation results with `& 0xff_ff` to match.
*/
var BinTrieFlags;
(function(BinTrieFlags) {
	BinTrieFlags[BinTrieFlags["VALUE_LENGTH"] = 49152] = "VALUE_LENGTH";
	BinTrieFlags[BinTrieFlags["FLAG13"] = 8192] = "FLAG13";
	BinTrieFlags[BinTrieFlags["BRANCH_LENGTH"] = 8064] = "BRANCH_LENGTH";
	BinTrieFlags[BinTrieFlags["JUMP_TABLE"] = 127] = "JUMP_TABLE";
	/** Bits 12..0: the inline value of a VALUE_LENGTH = 1 header word. */
	BinTrieFlags[BinTrieFlags["VALUE_MASK"] = 8191] = "VALUE_MASK";
})(BinTrieFlags || (BinTrieFlags = {}));
//#endregion
//#region node_modules/markdown-it/node_modules/entities/dist/decode.js
var CharCodes;
(function(CharCodes) {
	CharCodes[CharCodes["AMP"] = 38] = "AMP";
	CharCodes[CharCodes["NUM"] = 35] = "NUM";
	CharCodes[CharCodes["SEMI"] = 59] = "SEMI";
	CharCodes[CharCodes["EQUALS"] = 61] = "EQUALS";
	CharCodes[CharCodes["ZERO"] = 48] = "ZERO";
	CharCodes[CharCodes["NINE"] = 57] = "NINE";
	CharCodes[CharCodes["LOWER_A"] = 97] = "LOWER_A";
	CharCodes[CharCodes["LOWER_X"] = 120] = "LOWER_X";
})(CharCodes || (CharCodes = {}));
/** Bit that needs to be set to convert an upper case ASCII character to lower case */
var TO_LOWER_BIT = 32;
var CONSUMED_SHIFT = 21;
var CODE_POINT_MASK = 2097151;
/**
* Reserved consumed field for counts of at least 2047 characters after `&`.
* The true count is in `longNumericConsumed`.
*/
var CONSUMED_OVERFLOW = 2047;
/**
* Side channel for numeric entities of at least 2048 characters including
* `&`. Set by `parseNumericEntity` when its consumed count reaches the
* reserved value `CONSUMED_OVERFLOW`; callers read the true count from here.
* A module-level slot avoids a tuple allocation on the hot path.
*/
var longNumericConsumed = 0;
/**
* Extract the consumed count from a `parseNumericEntity` packed result,
* recovering the true length from `longNumericConsumed` when the packed
* field contains the sentinel. Read it before the next `parseNumericEntity`
* call, which may overwrite the side channel. This helper owns that protocol.
* @param packed Packed result of `parseNumericEntity`.
*/
function unpackConsumed(packed) {
	const consumed = packed >>> CONSUMED_SHIFT;
	return consumed === CONSUMED_OVERFLOW ? longNumericConsumed : consumed;
}
/**
* Unsigned subtraction trick: (code - lo) >>> 0 wraps negatives to large
* values, so a single `<=` covers the entire [lo..hi] range check.
* @param code Code point to check.
*/
function isNumber(code) {
	return code - CharCodes.ZERO >>> 0 <= 9;
}
function isHexadecimalCharacter(code) {
	return (code | TO_LOWER_BIT) - CharCodes.LOWER_A >>> 0 <= 5;
}
function isAlpha(code) {
	return (code | TO_LOWER_BIT) - CharCodes.LOWER_A >>> 0 <= 25;
}
/**
* Checks if the given character is a valid end character for an entity in an attribute.
*
* Attribute values that aren't terminated properly aren't parsed, and shouldn't lead to a parser error.
* See the example in https://html.spec.whatwg.org/multipage/parsing.html#named-character-reference-state
* @param code Code point to check.
*/
function isEntityInAttributeInvalidEnd(code) {
	return code === CharCodes.EQUALS || isAlpha(code) || isNumber(code);
}
var EntityDecoderState;
(function(EntityDecoderState) {
	EntityDecoderState[EntityDecoderState["EntityStart"] = 0] = "EntityStart";
	EntityDecoderState[EntityDecoderState["NumericStart"] = 1] = "NumericStart";
	EntityDecoderState[EntityDecoderState["NumericDecimal"] = 2] = "NumericDecimal";
	EntityDecoderState[EntityDecoderState["NumericHex"] = 3] = "NumericHex";
	EntityDecoderState[EntityDecoderState["NamedEntity"] = 4] = "NamedEntity";
})(EntityDecoderState || (EntityDecoderState = {}));
/**
* Decoding mode for named entities.
*/
var DecodingMode;
(function(DecodingMode) {
	/** Entities in text nodes that can end with any character. */
	DecodingMode[DecodingMode["Legacy"] = 0] = "Legacy";
	/** Only allow entities terminated with a semicolon. */
	DecodingMode[DecodingMode["Strict"] = 1] = "Strict";
	/** Entities in attributes have limitations on ending characters. */
	DecodingMode[DecodingMode["Attribute"] = 2] = "Attribute";
})(DecodingMode || (DecodingMode = {}));
/**
* Determines the branch of the current node that is taken given the current
* character. This function is used to traverse the trie.
*
* See `BinTrieFlags` for the branch-data layouts handled here.
* @param decodeTree The trie.
* @param current The current node's header word.
* @param nodeIndex Index of the node's first branch-data word (the header
*   plus any value words have been skipped by the caller).
* @param char The current character.
* @returns The index of the next node, or -1 if no branch is taken.
*/
function determineBranch(decodeTree, current, nodeIndex, char) {
	const branchCount = (current & BinTrieFlags.BRANCH_LENGTH) >> 7;
	const jumpOffset = current & BinTrieFlags.JUMP_TABLE;
	if (jumpOffset) {
		if (branchCount === 0) return char === jumpOffset ? nodeIndex : -1;
		const slot = char - jumpOffset;
		if (slot >>> 0 >= branchCount) return -1;
		const stored = decodeTree[nodeIndex + slot];
		return stored === 0 ? -1 : nodeIndex + branchCount + stored - 1 & 65535;
	}
	if (branchCount === 0) return -1;
	const packedKeySlots = branchCount + 1 >> 1;
	const branchEnd = nodeIndex + packedKeySlots + branchCount;
	for (let index = 0; index < branchCount; index++) {
		const key = decodeTree[nodeIndex + (index >> 1)] >> ((index & 1) << 3) & 255;
		if (key === char) return branchEnd + decodeTree[nodeIndex + packedKeySlots + index] & 65535;
		if (key > char) return -1;
	}
	return -1;
}
/**
* Read the decoded value from a trie node.
* @param decodeTree The trie.
* @param nodeIndex The index of the node.
* @param valueLength The length of the value (1, 2, or 3).
* @returns The decoded string.
*/
function readTrieValue(decodeTree, nodeIndex, valueLength) {
	if (valueLength === 1) return String.fromCharCode(decodeTree[nodeIndex] & BinTrieFlags.VALUE_MASK);
	if (valueLength === 2) return String.fromCharCode(decodeTree[nodeIndex + 1]);
	return String.fromCharCode(decodeTree[nodeIndex + 1], decodeTree[nodeIndex + 2]);
}
/**
* Parse a numeric entity (`&#DDD;` or `&#xHHH;`).
*
* Encodes the result as `(consumed << CONSUMED_SHIFT) | codepoint` (see
* the packing comment at the top of the file; overlong entities spill
* their length into `longNumericConsumed`). Returns 0 when no digits were
* found.
*
* This is the sync counterpart of the streaming
* `EntityDecoder#stateNumericDecimal` / `#stateNumericHex`. Digit parsing
* matches those methods; only this packed result needs a value clamp.
* @param input       The input string.
* @param numberStart Index of the `#` character.
* @param inputLength Cached `input.length`.
*/
function parseNumericEntity(input, numberStart, inputLength) {
	let offset = numberStart + 1;
	let cp = 0;
	let digitStart = offset;
	if (offset < inputLength && (input.charCodeAt(offset) | TO_LOWER_BIT) === CharCodes.LOWER_X) {
		offset += 1;
		digitStart = offset;
		while (offset < inputLength) {
			const char = input.charCodeAt(offset);
			if (isNumber(char)) cp = cp * 16 + (char - CharCodes.ZERO);
			else if (isHexadecimalCharacter(char)) cp = cp * 16 + ((char | TO_LOWER_BIT) - CharCodes.LOWER_A + 10);
			else break;
			offset += 1;
		}
	} else while (offset < inputLength) {
		const digit = input.charCodeAt(offset) - CharCodes.ZERO;
		if (digit >>> 0 > 9) break;
		cp = cp * 10 + digit;
		offset += 1;
	}
	if (offset === digitStart) return 0;
	if (offset < inputLength && input.charCodeAt(offset) === CharCodes.SEMI) offset += 1;
	if (cp > 1114111) cp = 1114112;
	let consumed = offset - numberStart;
	if (consumed >= CONSUMED_OVERFLOW) {
		longNumericConsumed = consumed;
		consumed = CONSUMED_OVERFLOW;
	}
	return consumed << CONSUMED_SHIFT | cp;
}
/**
* Decode all entities in `input` using the HTML trie.
*
* Hard-wired to `htmlDecodeTree`: the inline root navigation below assumes
* the HTML root's jump-table shape, so this must not be generalized to
* other tries (the XML trie's dictionary root would silently match no
* entities — `decodeXML` has its own hand-coded fast path instead).
* @param input      The string to decode.
* @param isStrict Only match semicolon-terminated entities.
* @param isAttribute Whether to apply attribute-specific parsing rules (disallowing certain non-semicolon terminators).
* @returns The decoded string.
*/
function decodeWithTrie(input, isStrict, isAttribute) {
	const decodeTree = htmlDecodeTree;
	let offset = input.indexOf("&");
	if (offset < 0) return input;
	const inputLength = input.length;
	let chunkStart = 0;
	let result = "";
	const root = decodeTree[0];
	const rootJumpOffset = root & BinTrieFlags.JUMP_TABLE;
	const rootBranchCount = (root & BinTrieFlags.BRANCH_LENGTH) >> 7;
	do {
		const entityStart = offset + 1;
		const firstChar = input.charCodeAt(entityStart);
		let consumed;
		let value;
		if (firstChar === CharCodes.NUM) {
			const packed = parseNumericEntity(input, entityStart, inputLength);
			consumed = unpackConsumed(packed);
			if (isStrict && consumed > 0 && input.charCodeAt(entityStart + consumed - 1) !== CharCodes.SEMI) consumed = 0;
			value = consumed === 0 ? "" : codePointToString(packed & CODE_POINT_MASK);
		} else if (isAlpha(firstChar)) {
			consumed = 0;
			value = "";
			const rootSlotIndex = firstChar - rootJumpOffset;
			let nodeIndex;
			if (rootSlotIndex >>> 0 < rootBranchCount) {
				const stored = decodeTree[1 + rootSlotIndex];
				nodeIndex = stored === 0 ? -1 : rootBranchCount + stored & 65535;
			} else nodeIndex = -1;
			let bestNodeIndex = 0;
			let bestValueLength = 0;
			let current = nodeIndex < 0 ? 0 : decodeTree[nodeIndex];
			let index = entityStart + 1;
			trie: while (index < inputLength) {
				while ((current & (BinTrieFlags.VALUE_LENGTH | BinTrieFlags.FLAG13)) === 0 && (current & BinTrieFlags.JUMP_TABLE) !== 0) {
					const jumpOffset = current & BinTrieFlags.JUMP_TABLE;
					const branchCount = (current & BinTrieFlags.BRANCH_LENGTH) >> 7;
					if (branchCount === 0) {
						if (input.charCodeAt(index) !== jumpOffset) break trie;
						nodeIndex += 1;
					} else {
						const slot = input.charCodeAt(index) - jumpOffset;
						if (slot >>> 0 >= branchCount) break trie;
						const stored = decodeTree[nodeIndex + 1 + slot];
						if (stored === 0) break trie;
						nodeIndex = nodeIndex + branchCount + stored & 65535;
					}
					current = decodeTree[nodeIndex];
					index += 1;
					if (index >= inputLength) break trie;
				}
				if ((current & (BinTrieFlags.VALUE_LENGTH | BinTrieFlags.FLAG13)) === BinTrieFlags.FLAG13) {
					const runLength = (current & BinTrieFlags.BRANCH_LENGTH) >> 7;
					if (input.charCodeAt(index) !== (current & BinTrieFlags.JUMP_TABLE)) break;
					index += 1;
					const remaining = runLength - 1;
					let wordIndex = nodeIndex + 1;
					let charIndexInPacked = 0;
					for (; charIndexInPacked + 1 < remaining; charIndexInPacked += 2) {
						const packed = decodeTree[wordIndex];
						if (input.charCodeAt(index) !== (packed & 255)) break trie;
						index += 1;
						if (input.charCodeAt(index) !== (packed >> 8 & 255)) break trie;
						index += 1;
						wordIndex += 1;
					}
					if (charIndexInPacked < remaining) {
						if (input.charCodeAt(index) !== (decodeTree[wordIndex] & 255)) break;
						index += 1;
					}
					nodeIndex += 1 + (runLength >> 1);
					current = decodeTree[nodeIndex];
					continue;
				}
				const valueLength = current >>> 14;
				const char = input.charCodeAt(index);
				if (valueLength !== 0) {
					if (char === CharCodes.SEMI) {
						consumed = index - entityStart + 1;
						value = valueLength === 1 ? String.fromCharCode(current & BinTrieFlags.VALUE_MASK) : readTrieValue(decodeTree, nodeIndex, valueLength);
						break;
					}
					if (!isStrict && (current & BinTrieFlags.FLAG13) === 0) {
						consumed = index - entityStart;
						bestNodeIndex = nodeIndex;
						bestValueLength = valueLength;
					}
					if (valueLength === 1) break;
				}
				const next = determineBranch(decodeTree, current, nodeIndex + (valueLength || 1), char);
				if (next < 0) break;
				nodeIndex = next;
				current = decodeTree[nodeIndex];
				index += 1;
			}
			if (value === "") {
				const finalVL = current >>> 14;
				if (finalVL !== 0 && !isStrict && (current & BinTrieFlags.FLAG13) === 0) {
					consumed = index - entityStart;
					bestNodeIndex = nodeIndex;
					bestValueLength = finalVL;
				}
				if (consumed > 0) value = readTrieValue(decodeTree, bestNodeIndex, bestValueLength);
			}
		} else {
			consumed = 0;
			value = "";
		}
		if (consumed === 0 || isAttribute && firstChar !== CharCodes.NUM && input.charCodeAt(entityStart + consumed - 1) !== CharCodes.SEMI && entityStart + consumed < inputLength && isEntityInAttributeInvalidEnd(input.charCodeAt(entityStart + consumed))) offset = entityStart;
		else {
			if (chunkStart < offset) result += input.slice(chunkStart, offset);
			result += value;
			offset = chunkStart = entityStart + consumed;
		}
		if (input.charCodeAt(offset) !== CharCodes.AMP) offset = input.indexOf("&", offset);
	} while (offset >= 0);
	return result + input.slice(chunkStart);
}
/**
* Decodes an HTML string, requiring all entities to be terminated by a semicolon.
* @param htmlString The string to decode.
* @returns The decoded string.
*/
function decodeHTMLStrict(htmlString) {
	return decodeWithTrie(htmlString, true, false);
}
//#endregion
//#region node_modules/linkify-it/build/index.mjs
var REBuilder = class {
	src_Any = Any.source;
	src_Cc = Cc.source;
	src_Z = Z.source;
	src_P = P.source;
	src_ZPCc = [
		this.src_Z,
		this.src_P,
		this.src_Cc
	].join("|");
	src_ZCc = [this.src_Z, this.src_Cc].join("|");
	cache = {};
	opts = {
		maxLength: 1e4,
		urlAuth: false,
		schema_names: []
	};
	constructor(opts = {}) {
		this.opts = {
			...this.opts,
			...opts
		};
	}
	set(opts = {}) {
		this.opts = {
			...this.opts,
			...opts
		};
		this.cache = {};
		return this;
	}
	escapeRE(str) {
		return str.replace(/[.?*+^$[\]\\(){}|-]/g, "\\$&");
	}
	nestedPairRE(open, close, depth = 4) {
		const openRE = this.escapeRE(open);
		const closeRE = this.escapeRE(close);
		const atom = `(?:(?!${this.src_ZCc}|${openRE}|${closeRE}).)`;
		let pair = `${openRE}${atom}{0,1000}${closeRE}`;
		for (let level = 2; level <= depth; level++) pair = `${openRE}(?:${atom}|${pair}){0,1000}${closeRE}`;
		return pair;
	}
	get_text_separators() {
		return this.cache.text_separators ??= /[><\uff5c]/;
	}
	get_pseudo_letter() {
		return this.cache.src_pseudo_letter ??= new RegExp(`(?:(?!${this.get_text_separators().source}|${this.src_ZPCc})${this.src_Any})`);
	}
	get_ipv4_addr() {
		return this.cache.src_ip4 ??= /* @__PURE__ */ new RegExp("(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])[.]){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])");
	}
	get_ipv6_addr() {
		const h16 = "[0-9A-Fa-f]{1,4}";
		const ls32 = `(?:(?:${h16}:${h16})|${this.get_ipv4_addr().source})`;
		return this.cache.src_ip6_addr ??= new RegExp(`(?:(?:${h16}:){6}${ls32}|::(?:${h16}:){5}${ls32}|(?:${h16})?::(?:${h16}:){4}${ls32}|(?:(?:${h16}:){0,1}${h16})?::(?:${h16}:){3}${ls32}|(?:(?:${h16}:){0,2}${h16})?::(?:${h16}:){2}${ls32}|(?:(?:${h16}:){0,3}${h16})?::${h16}:${ls32}|(?:(?:${h16}:){0,4}${h16})?::${ls32}|(?:(?:${h16}:){0,5}${h16})?::${h16}|(?:(?:${h16}:){0,6}${h16})?::)`);
	}
	get_ipv6_url_host() {
		return this.cache.src_ip6_host ??= new RegExp(`\\[${this.get_ipv6_addr().source}\\]`);
	}
	get_ipv6_mail_host() {
		return this.cache.src_ipv6_mail_host ??= new RegExp(`\\[IPv6:${this.get_ipv6_addr().source}\\]`);
	}
	get_auth() {
		return this.cache.src_auth ??= new RegExp(`(?:(?:(?!${this.src_ZCc}|[@/\\[\\]()]).){1,50}@)?`);
	}
	get_port() {
		return this.cache.src_port ??= /* @__PURE__ */ new RegExp("(?::(?:6(?:[0-4]\\d{3}|5(?:[0-4]\\d{2}|5(?:[0-2]\\d|3[0-5])))|[1-5]?\\d{1,4}))?");
	}
	get_host_terminator() {
		return this.cache.src_host_terminator ??= new RegExp(`(?=$|${this.get_text_separators().source}|${this.src_ZPCc})(?!${this.opts["---"] ? "-(?!--)|" : "-|"}_|:\\d|\\.-|\\.(?!$|${this.src_ZPCc}))`);
	}
	get_path_terminator() {
		return this.cache.src_path_terminator ??= new RegExp(`${this.src_ZPCc}|${this.get_text_separators().source}`);
	}
	get_path() {
		return this.cache.src_path ??= new RegExp(`(?:[/?#](?:${this.nestedPairRE("[", "]")}|${this.nestedPairRE("(", ")")}|${this.nestedPairRE("{", "}")}|\\"(?:(?!${this.src_ZCc}|["]).){1,100}\\"|\\'(?:(?!${this.src_ZCc}|[']).){1,100}\\'|\\'(?=${this.get_pseudo_letter().source}|[-])|\\.{2,20}[:]?[a-zA-Z0-9%/&]|\\.(?!${this.src_ZCc}|[.]|$)|` + (this.opts["---"] ? "\\-(?!--(?:[^-]|$))(?:-{0,19})|" : "\\-{1,20}|") + `,(?!${this.src_ZCc}|$)|;(?!${this.src_ZCc}|$)|\\!{1,20}(?!${this.src_ZCc}|[!]|$)|\\?(?!${this.src_ZCc}|[?]|$)|` + this.get_path_extra().source + `[\\\\/:%@#&=_~*]|(?!${this.get_path_terminator().source}).){1,${this.opts.maxLength}}|\\/)?`);
	}
	get_mail_name() {
		return this.cache.src_mail_name ??= /* @__PURE__ */ new RegExp("[-!#$%&'*+/=?^_`{|}~a-zA-Z0-9](?:[-!#$%&'*+/=?^_`{|}~a-zA-Z0-9]|[.](?=[-!#$%&'*+/=?^_`{|}~a-zA-Z0-9])){0,63}");
	}
	get_xn() {
		return this.cache.src_xn ??= /* @__PURE__ */ new RegExp("xn--[a-z0-9\\-]{1,59}");
	}
	get_tld() {
		if (this.cache.tld) return this.cache.tld;
		const tlds_src = [...new Set(this.opts.tlds || [])].sort().reverse().join("|");
		this.cache.tld = new RegExp(`${tlds_src || "$#none#$"}|${this.get_xn().source}`);
		return this.cache.tld;
	}
	get_domain_root() {
		return this.cache.src_domain_root ??= new RegExp("(?:" + this.get_xn().source + `|${this.get_pseudo_letter().source}{1,63})`);
	}
	get_domain() {
		return this.cache.src_domain ??= new RegExp("(?:" + this.get_xn().source + `|(?:${this.get_pseudo_letter().source})|(?:${this.get_pseudo_letter().source}(?:-|${this.get_pseudo_letter().source}){0,61}${this.get_pseudo_letter().source}))`);
	}
	get_url_host_port() {
		return this.cache.url_host_port ??= new RegExp("(?:" + this.get_ipv6_url_host().source + `|(?:(?:(?:${this.get_domain().source})\\.){0,10}${this.get_domain().source}))` + this.get_port().source + this.get_host_terminator().source);
	}
	get_fuzzy_url_host_port() {
		return this.cache.fuzzy_url_host_port ??= new RegExp("(?:" + (this.opts.fuzzyIP ? this.get_ipv4_addr().source + "|" : "") + `(?:(?:(?:${this.get_domain().source})\\.){1,10}(?:${this.get_tld().source})))` + this.get_host_terminator().source);
	}
	get_mail_host() {
		return this.cache.src_mail_host ??= new RegExp("(?:" + this.get_ipv6_mail_host().source + `|(?:(?:(?:${this.get_domain().source})\\.){0,4}${this.get_domain().source}))` + this.get_host_terminator().source);
	}
	get_fuzzy_mail_host() {
		return this.cache.src_fuzzy_mail_host ??= new RegExp("(?:" + this.get_ipv6_mail_host().source + `|(?:(?:(?:${this.get_domain().source})[.]){1,4}${this.get_domain_root().source}))` + this.get_host_terminator().source);
	}
	get_path_extra() {
		return this.cache.src_path_extra ??= /* @__PURE__ */ new RegExp("");
	}
	get_fuzzy_mail_host_search() {
		return this.cache.mail_fuzzy_host_search ??= new RegExp(`@${this.get_fuzzy_mail_host().source}`, "ig");
	}
	get_fuzzy_link_search() {
		return this.cache.link_fuzzy_search ??= new RegExp(`(^|(?![.:/\\-_@])(?:[$+<=>^\`|\uff5c]|${this.src_ZPCc}))(?:(?![$+<=>^\`|\uff5c])${this.get_fuzzy_url_host_port().source}${this.get_path().source})`, "ig");
	}
	get_http_validator() {
		return this.cache.http_validator ??= new RegExp("\\/\\/" + (this.opts.urlAuth ? this.get_auth().source : "") + this.get_url_host_port().source + this.get_path().source, "iy");
	}
	get_relative_proto_validator() {
		return this.cache.relative_proto_validator ??= new RegExp((this.opts.urlAuth ? this.get_auth().source : "") + `(?:localhost|${this.get_ipv6_url_host().source}|(?:(?:${this.get_domain().source})[.]){1,10}${this.get_domain_root().source})` + this.get_port().source + this.get_host_terminator().source + this.get_path().source, "iy");
	}
	get_mail_name_validator() {
		return this.cache.mail_name_validator ??= new RegExp(`(?:^|${this.get_text_separators().source}|"|\\(|${this.src_ZCc})(${this.get_mail_name().source})$`);
	}
	get_mailto_validator() {
		return this.cache.mailto_validator ??= new RegExp(`${this.get_mail_name().source}@${this.get_mail_host().source}`, "iy");
	}
	get_schema_names() {
		return this.cache.schema_names ??= new RegExp((this.opts.schema_names || []).map((name) => this.escapeRE(name)).join("|"));
	}
	get_schema_search() {
		return this.cache.schema_search ??= new RegExp(`(^|(?!_)(?:[><\uff5c]|${this.src_ZPCc}))(${this.get_schema_names().source})`, "ig");
	}
	get_schema_at_start() {
		return this.cache.schema_at_start ??= new RegExp(`^${this.get_schema_search().source}`, "i");
	}
};
var web_schema = {
	validate: (text, pos, self) => {
		const re = self.re.get_http_validator();
		re.lastIndex = pos;
		const m = re.exec(text);
		return m ? m[0].length : 0;
	},
	normalize: (match, self) => self.normalize(match)
};
var defaultSchemas = {
	"http:": web_schema,
	"https:": web_schema,
	"ftp:": web_schema,
	"//": {
		validate: function(text, pos, self) {
			const re = self.re.get_relative_proto_validator();
			re.lastIndex = pos;
			const m = re.exec(text);
			if (m) {
				if (pos >= 3 && text[pos - 3] === ":") return 0;
				if (pos >= 3 && text[pos - 3] === "/") return 0;
				return m[0].length;
			}
			return 0;
		},
		normalize: (match, self) => self.normalize(match)
	},
	"mailto:": {
		validate: function(text, pos, self) {
			const re = self.re.get_mailto_validator();
			re.lastIndex = pos;
			const m = re.exec(text);
			return m ? m[0].length : 0;
		},
		normalize: (match, self) => self.normalize(match)
	}
};
var tlds_2ch = "a:cdefgilmnoqrstuwxz|b:abdefghijmnorstvwyz|c:acdfghiklmnoruvwxyz|d:ejkmoz|e:cegrstu|f:ijkmor|g:abdefghilmnpqrstuwy|h:kmnrtu|i:delmnoqrst|j:emop|k:eghimnprwyz|l:abcikrstuvy|m:acdeghklmnopqrstuvwxyz|n:acefgilopruz|o:m|p:aefghklmnrstwy|q:a|r:eosuw|s:abcdeghijklmnortuvxyz|t:cdfghjklmnortvwz|u:agksyz|v:aceginu|w:fs|y:et|z:amw";
var tlds_default = "biz|com|edu|gov|net|org|pro|web|xxx|aero|asia|coop|info|museum|name|shop|рф";
function unpackTlds() {
	const result = tlds_default.split("|");
	tlds_2ch.split("|").forEach((item) => {
		const sep = item.indexOf(":");
		const prefix = item.slice(0, sep);
		for (const suffix of item.slice(sep + 1)) result.push(prefix + suffix);
	});
	return result;
}
var defaultOptions = {
	fuzzyLink: false,
	fuzzyEmail: true,
	fuzzyIP: false,
	"---": false,
	tlds: unpackTlds(),
	urlAuth: false,
	maxLength: 1e4
};
/**
* Match result returned by {@link LinkifyIt.match} and
* {@link LinkifyIt.matchAtStart}.
*
* @category types
*/
var Match = class {
	/** Prefix (protocol) for matched string. Empty for fuzzy links. */
	schema;
	/** First position of matched string. */
	index;
	/** Next position after matched string. */
	lastIndex;
	/** Matched string. */
	raw;
	/** Normalized text of matched string. */
	text;
	/** Normalized URL of matched string. */
	url;
	constructor(text, schema, index, lastIndex) {
		const raw = text.slice(index, lastIndex);
		this.schema = schema.toLowerCase();
		this.index = index;
		this.lastIndex = lastIndex;
		this.raw = raw;
		this.text = raw;
		this.url = raw;
	}
};
/** Linkifier instance. */
var LinkifyIt = class {
	__opts__;
	__schemas__;
	re;
	/**
	* Creates new linkifier instance.
	*
	* By default understands:
	*
	* - `http(s)://...` , `ftp://...`, `mailto:...` & `//...` links
	* - "fuzzy" emails (foo@bar.com).
	*
	* See {@link LinkifyConstructorOptions} for available options.
	*
	* @param options Recognition options.
	*
	* @example
	* ```javascript
	* import { LinkifyIt } from 'linkify-it'
	*
	* const linkify = new LinkifyIt({ fuzzyLink: true })
	*
	* linkify
	*   .tlds(require('tlds'))       // Reload with full TLD list
	*   .tlds('onion', true)         // Add unofficial `.onion` domain
	*   .add('ftp:', null)           // Disable `ftp:` protocol
	*   .set({ fuzzyIP: true })      // Enable IPs in fuzzy links
	*
	* console.log(linkify.test('Site github.com!')) // true
	* console.log(linkify.match('Site github.com!'))
	* ```
	*/
	constructor(options = {}) {
		const { rebuilder, ...linkifyOptions } = options;
		this.__opts__ = {
			...defaultOptions,
			...linkifyOptions
		};
		this.__schemas__ = { ...defaultSchemas };
		this.re = rebuilder || new REBuilder();
		this.re.set({
			...this.__opts__,
			schema_names: Object.keys(this.__schemas__)
		});
	}
	/**
	* Add new rule definition.
	*
	* `schema` is a link prefix (usually, protocol name with `:` at the end,
	* `skype:` for example). `linkify-it` makes sure that prefix is not
	* preceded with alphanumeric char and symbols. Only whitespaces and
	* punctuation allowed.
	*
	* `definition` is a rule to check tail after link prefix. To disable an
	* existing rule, pass `null`.
	*
	* @param schema Rule name (fixed pattern prefix).
	* @param definition Schema definition, or `null` to disable the rule.
	*
	* See [twitter mentions example](https://github.com/markdown-it/linkify-it/blob/master/examples/twitter.mjs).
	*/
	add(schema, definition = null) {
		if (!definition) delete this.__schemas__[schema];
		else {
			const def = {
				normalize: (match, self) => self.normalize(match),
				...definition
			};
			this.__schemas__[schema] = def;
		}
		this.re.set({
			...this.__opts__,
			schema_names: Object.keys(this.__schemas__)
		});
		return this;
	}
	/**
	* Set recognition options for links without schema.
	*
	* @param options Recognition options.
	*/
	set(options = {}) {
		this.__opts__ = {
			...this.__opts__,
			...options
		};
		this.re.set({
			...this.__opts__,
			schema_names: Object.keys(this.__schemas__)
		});
		return this;
	}
	/**
	* Searches linkifiable pattern and returns `true` on success or `false` on fail.
	*
	* @param text Text to scan.
	*/
	test(text) {
		if (!text.length) return false;
		let m, re;
		re = this.re.get_schema_search();
		re.lastIndex = 0;
		while ((m = re.exec(text)) !== null) if (this.testSchemaAt(text, m[2], re.lastIndex)) return true;
		if (this.__opts__.fuzzyLink && this.__schemas__["http:"]) {
			re = this.re.get_fuzzy_link_search();
			re.lastIndex = 0;
			if (re.exec(text) !== null) return true;
		}
		if (this.__opts__.fuzzyEmail && this.__schemas__["mailto:"]) {
			if (text.indexOf("@") >= 0) {
				const mailHostRe = this.re.get_fuzzy_mail_host_search();
				const mailNameRe = this.re.get_mail_name_validator();
				mailHostRe.lastIndex = 0;
				while ((m = mailHostRe.exec(text)) !== null) {
					const name = text.slice(Math.max(0, m.index - 65), m.index);
					if (mailNameRe.test(name)) return true;
				}
			}
		}
		return false;
	}
	/**
	* Similar to {@link LinkifyIt.test} but checks only specific protocol tail exactly
	* at given position. Returns length of found pattern (0 on fail).
	*
	* @param text Text to scan.
	* @param schema Rule (schema) name.
	* @param pos Text offset to check from.
	*/
	testSchemaAt(text, schema, pos) {
		if (!this.__schemas__[schema.toLowerCase()]) return 0;
		return this.__schemas__[schema.toLowerCase()].validate(text.slice(0, pos + this.__opts__.maxLength), pos, this);
	}
	/**
	* Returns array of found link descriptions or `null` on fail. We strongly
	* recommend to use {@link LinkifyIt.test} first, for best speed.
	*
	* @param text Text to scan.
	*/
	match(text) {
		const result = [];
		const schemaRe = this.re.get_schema_search();
		let fuzzyLinkRe;
		let mailHostRe;
		let mailNameRe;
		let fuzzyLinkCandidate;
		let fuzzyEmailCandidate;
		let schemaPrefix;
		let schemaDone = false;
		let fuzzyLinkDone = false;
		let fuzzyEmailDone = false;
		let pos = 0;
		if (!text.length) return null;
		schemaRe.lastIndex = 0;
		if (this.__opts__.fuzzyLink && this.__schemas__["http:"]) {
			fuzzyLinkRe = this.re.get_fuzzy_link_search();
			fuzzyLinkRe.lastIndex = 0;
		}
		if (this.__opts__.fuzzyEmail && this.__schemas__["mailto:"]) {
			mailHostRe = this.re.get_fuzzy_mail_host_search();
			mailHostRe.lastIndex = 0;
			mailNameRe = this.re.get_mail_name_validator();
		}
		for (;;) {
			const scanFrom = Math.max(pos - 1, 0);
			if (mailHostRe && mailNameRe && !fuzzyEmailDone && (!fuzzyEmailCandidate || fuzzyEmailCandidate.index < pos)) {
				if (mailHostRe.lastIndex < scanFrom) mailHostRe.lastIndex = scanFrom;
				for (;;) {
					const m = mailHostRe.exec(text);
					if (!m) {
						fuzzyEmailDone = true;
						fuzzyEmailCandidate = void 0;
						break;
					}
					const name = mailNameRe.exec(text.slice(Math.max(0, m.index - 65), m.index));
					if (!name) continue;
					fuzzyEmailCandidate = {
						schema: "mailto:",
						index: m.index - name[1].length,
						lastIndex: m.index + m[0].length
					};
					if (fuzzyEmailCandidate.index >= pos) break;
					if (mailHostRe.lastIndex < scanFrom) mailHostRe.lastIndex = scanFrom;
				}
			}
			if (fuzzyLinkRe && !fuzzyLinkDone && (!fuzzyLinkCandidate || fuzzyLinkCandidate.index < pos)) {
				if (fuzzyLinkRe.lastIndex < scanFrom) fuzzyLinkRe.lastIndex = scanFrom;
				for (;;) {
					const m = fuzzyLinkRe.exec(text);
					if (!m) {
						fuzzyLinkDone = true;
						fuzzyLinkCandidate = void 0;
						break;
					}
					fuzzyLinkCandidate = {
						schema: "",
						index: m.index + m[1].length,
						lastIndex: m.index + m[0].length
					};
					if (fuzzyLinkCandidate.index >= pos) break;
					if (fuzzyLinkRe.lastIndex < scanFrom) fuzzyLinkRe.lastIndex = scanFrom;
				}
			}
			let fuzzyCandidate = fuzzyEmailCandidate;
			if (!fuzzyCandidate || fuzzyLinkCandidate && (fuzzyLinkCandidate.index < fuzzyCandidate.index || fuzzyLinkCandidate.index === fuzzyCandidate.index && fuzzyLinkCandidate.lastIndex > fuzzyCandidate.lastIndex)) fuzzyCandidate = fuzzyLinkCandidate;
			let schemaCandidate;
			if (!schemaDone) for (;;) {
				if (!schemaPrefix) {
					if (schemaRe.lastIndex < scanFrom) schemaRe.lastIndex = scanFrom;
					const m = schemaRe.exec(text);
					if (!m) {
						schemaDone = true;
						break;
					}
					schemaPrefix = {
						schema: m[2],
						index: m.index + m[1].length,
						lastIndex: m.index + m[0].length
					};
				}
				if (schemaPrefix.index < pos) {
					schemaPrefix = void 0;
					continue;
				}
				if (fuzzyCandidate && schemaPrefix.index > fuzzyCandidate.index) break;
				const prefix = schemaPrefix;
				schemaPrefix = void 0;
				const len = this.testSchemaAt(text, prefix.schema, prefix.lastIndex);
				if (len) {
					schemaCandidate = {
						schema: prefix.schema,
						index: prefix.index,
						lastIndex: prefix.lastIndex + len
					};
					break;
				}
			}
			let candidate = schemaCandidate;
			if (!candidate || fuzzyEmailCandidate && (fuzzyEmailCandidate.index < candidate.index || fuzzyEmailCandidate.index === candidate.index && fuzzyEmailCandidate.lastIndex > candidate.lastIndex)) candidate = fuzzyEmailCandidate;
			if (!candidate || fuzzyLinkCandidate && (fuzzyLinkCandidate.index < candidate.index || fuzzyLinkCandidate.index === candidate.index && fuzzyLinkCandidate.lastIndex > candidate.lastIndex)) candidate = fuzzyLinkCandidate;
			if (!candidate) break;
			if (candidate === fuzzyEmailCandidate) fuzzyEmailCandidate = void 0;
			else if (candidate === fuzzyLinkCandidate) fuzzyLinkCandidate = void 0;
			const match = new Match(text, candidate.schema, candidate.index, candidate.lastIndex);
			if (match.schema) this.__schemas__[match.schema].normalize(match, this);
			else this.normalize(match);
			result.push(match);
			pos = candidate.lastIndex;
		}
		if (result.length) return result;
		return null;
	}
	/**
	* Returns fully-formed (not fuzzy) link if it starts at the beginning
	* of the string, and null otherwise.
	*
	* @param text Text to scan.
	*/
	matchAtStart(text) {
		if (!text.length) return null;
		const m = this.re.get_schema_at_start().exec(text);
		if (!m) return null;
		const len = this.testSchemaAt(text, m[2], m[0].length);
		if (!len) return null;
		const match = new Match(text, m[2], m.index + m[1].length, m.index + m[0].length + len);
		this.__schemas__[match.schema].normalize(match, this);
		return match;
	}
	/**
	* Load (or merge) new TLDs list. Those are used for fuzzy links (without
	* prefix) to avoid false positives. By default this algorithm is used:
	*
	* - hostname with any 2-letter root zones are ok.
	* - biz|com|edu|gov|net|org|pro|web|xxx|aero|asia|coop|info|museum|name|shop|рф
	*   are ok.
	* - encoded (`xn--...`) root zones are ok.
	*
	* If list is replaced, then exact match for 2-chars root zones will be checked.
	*
	* @param list List of TLDs.
	* @param keepOld Merge with current list if `true` (`false` by default).
	*/
	tlds(list, keepOld = false) {
		list = Array.isArray(list) ? list : [list];
		if (!keepOld) this.__opts__.tlds = list;
		else this.__opts__.tlds = this.__opts__.tlds.concat(list);
		this.re.set({
			...this.__opts__,
			schema_names: Object.keys(this.__schemas__)
		});
		return this;
	}
	/**
	* Default normalizer (if schema does not define its own).
	*
	* @param match Match to normalize.
	*/
	normalize(match) {
		if (!match.schema) match.url = `http://${match.url}`;
		if (match.schema === "mailto:" && !/^mailto:/i.test(match.url)) match.url = `mailto:${match.url}`;
	}
};
//#endregion
//#region node_modules/punycode.js/punycode.es6.js
/** Highest positive signed 32-bit float value */
var maxInt = 2147483647;
/** Bootstring parameters */
var base = 36;
var tMin = 1;
var tMax = 26;
var skew = 38;
var damp = 700;
var initialBias = 72;
var initialN = 128;
var delimiter = "-";
/** Regular expressions */
var regexPunycode = /^xn--/;
var regexNonASCII = /[^\0-\x7F]/;
var regexSeparators = /[\x2E\u3002\uFF0E\uFF61]/g;
/** Error messages */
var errors = {
	"overflow": "Overflow: input needs wider integers to process",
	"not-basic": "Illegal input >= 0x80 (not a basic code point)",
	"invalid-input": "Invalid input"
};
/** Convenience shortcuts */
var baseMinusTMin = 35;
var floor = Math.floor;
var stringFromCharCode = String.fromCharCode;
/**
* A generic error utility function.
* @private
* @param {String} type The error type.
* @returns {Error} Throws a `RangeError` with the applicable error message.
*/
function error(type) {
	throw new RangeError(errors[type]);
}
/**
* A generic `Array#map` utility function.
* @private
* @param {Array} array The array to iterate over.
* @param {Function} callback The function that gets called for every array
* item.
* @returns {Array} A new array of values returned by the callback function.
*/
function map(array, callback) {
	const result = [];
	let length = array.length;
	while (length--) result[length] = callback(array[length]);
	return result;
}
/**
* A simple `Array#map`-like wrapper to work with domain name strings or email
* addresses.
* @private
* @param {String} domain The domain name or email address.
* @param {Function} callback The function that gets called for every
* character.
* @returns {String} A new string of characters returned by the callback
* function.
*/
function mapDomain(domain, callback) {
	const parts = domain.split("@");
	let result = "";
	if (parts.length > 1) {
		result = parts[0] + "@";
		domain = parts[1];
	}
	domain = domain.replace(regexSeparators, ".");
	const encoded = map(domain.split("."), callback).join(".");
	return result + encoded;
}
/**
* Creates an array containing the numeric code points of each Unicode
* character in the string. While JavaScript uses UCS-2 internally,
* this function will convert a pair of surrogate halves (each of which
* UCS-2 exposes as separate characters) into a single code point,
* matching UTF-16.
* @see `punycode.ucs2.encode`
* @see <https://mathiasbynens.be/notes/javascript-encoding>
* @memberOf punycode.ucs2
* @name decode
* @param {String} string The Unicode input string (UCS-2).
* @returns {Array} The new array of code points.
*/
function ucs2decode(string) {
	const output = [];
	let counter = 0;
	const length = string.length;
	while (counter < length) {
		const value = string.charCodeAt(counter++);
		if (value >= 55296 && value <= 56319 && counter < length) {
			const extra = string.charCodeAt(counter++);
			if ((extra & 64512) == 56320) output.push(((value & 1023) << 10) + (extra & 1023) + 65536);
			else {
				output.push(value);
				counter--;
			}
		} else output.push(value);
	}
	return output;
}
/**
* Creates a string based on an array of numeric code points.
* @see `punycode.ucs2.decode`
* @memberOf punycode.ucs2
* @name encode
* @param {Array} codePoints The array of numeric code points.
* @returns {String} The new Unicode string (UCS-2).
*/
var ucs2encode = (codePoints) => String.fromCodePoint(...codePoints);
/**
* Converts a basic code point into a digit/integer.
* @see `digitToBasic()`
* @private
* @param {Number} codePoint The basic numeric code point value.
* @returns {Number} The numeric value of a basic code point (for use in
* representing integers) in the range `0` to `base - 1`, or `base` if
* the code point does not represent a value.
*/
var basicToDigit = function(codePoint) {
	if (codePoint >= 48 && codePoint < 58) return 26 + (codePoint - 48);
	if (codePoint >= 65 && codePoint < 91) return codePoint - 65;
	if (codePoint >= 97 && codePoint < 123) return codePoint - 97;
	return base;
};
/**
* Converts a digit/integer into a basic code point.
* @see `basicToDigit()`
* @private
* @param {Number} digit The numeric value of a basic code point.
* @returns {Number} The basic code point whose value (when used for
* representing integers) is `digit`, which needs to be in the range
* `0` to `base - 1`. If `flag` is non-zero, the uppercase form is
* used; else, the lowercase form is used. The behavior is undefined
* if `flag` is non-zero and `digit` has no uppercase form.
*/
var digitToBasic = function(digit, flag) {
	return digit + 22 + 75 * (digit < 26) - ((flag != 0) << 5);
};
/**
* Bias adaptation function as per section 3.4 of RFC 3492.
* https://tools.ietf.org/html/rfc3492#section-3.4
* @private
*/
var adapt = function(delta, numPoints, firstTime) {
	let k = 0;
	delta = firstTime ? floor(delta / damp) : delta >> 1;
	delta += floor(delta / numPoints);
	for (; delta > 455; k += base) delta = floor(delta / baseMinusTMin);
	return floor(k + 36 * delta / (delta + skew));
};
/**
* Converts a Punycode string of ASCII-only symbols to a string of Unicode
* symbols.
* @memberOf punycode
* @param {String} input The Punycode string of ASCII-only symbols.
* @returns {String} The resulting string of Unicode symbols.
*/
var decode = function(input) {
	const output = [];
	const inputLength = input.length;
	let i = 0;
	let n = initialN;
	let bias = initialBias;
	let basic = input.lastIndexOf(delimiter);
	if (basic < 0) basic = 0;
	for (let j = 0; j < basic; ++j) {
		if (input.charCodeAt(j) >= 128) error("not-basic");
		output.push(input.charCodeAt(j));
	}
	for (let index = basic > 0 ? basic + 1 : 0; index < inputLength;) {
		const oldi = i;
		for (let w = 1, k = base;; k += base) {
			if (index >= inputLength) error("invalid-input");
			const digit = basicToDigit(input.charCodeAt(index++));
			if (digit >= base) error("invalid-input");
			if (digit > floor((maxInt - i) / w)) error("overflow");
			i += digit * w;
			const t = k <= bias ? tMin : k >= bias + tMax ? tMax : k - bias;
			if (digit < t) break;
			const baseMinusT = base - t;
			if (w > floor(maxInt / baseMinusT)) error("overflow");
			w *= baseMinusT;
		}
		const out = output.length + 1;
		bias = adapt(i - oldi, out, oldi == 0);
		if (floor(i / out) > maxInt - n) error("overflow");
		n += floor(i / out);
		i %= out;
		output.splice(i++, 0, n);
	}
	return String.fromCodePoint(...output);
};
/**
* Converts a string of Unicode symbols (e.g. a domain name label) to a
* Punycode string of ASCII-only symbols.
* @memberOf punycode
* @param {String} input The string of Unicode symbols.
* @returns {String} The resulting Punycode string of ASCII-only symbols.
*/
var encode = function(input) {
	const output = [];
	input = ucs2decode(input);
	const inputLength = input.length;
	let n = initialN;
	let delta = 0;
	let bias = initialBias;
	for (const currentValue of input) if (currentValue < 128) output.push(stringFromCharCode(currentValue));
	const basicLength = output.length;
	let handledCPCount = basicLength;
	if (basicLength) output.push(delimiter);
	while (handledCPCount < inputLength) {
		let m = maxInt;
		for (const currentValue of input) if (currentValue >= n && currentValue < m) m = currentValue;
		const handledCPCountPlusOne = handledCPCount + 1;
		if (m - n > floor((maxInt - delta) / handledCPCountPlusOne)) error("overflow");
		delta += (m - n) * handledCPCountPlusOne;
		n = m;
		for (const currentValue of input) {
			if (currentValue < n && ++delta > maxInt) error("overflow");
			if (currentValue === n) {
				let q = delta;
				for (let k = base;; k += base) {
					const t = k <= bias ? tMin : k >= bias + tMax ? tMax : k - bias;
					if (q < t) break;
					const qMinusT = q - t;
					const baseMinusT = base - t;
					output.push(stringFromCharCode(digitToBasic(t + qMinusT % baseMinusT, 0)));
					q = floor(qMinusT / baseMinusT);
				}
				output.push(stringFromCharCode(digitToBasic(q, 0)));
				bias = adapt(delta, handledCPCountPlusOne, handledCPCount === basicLength);
				delta = 0;
				++handledCPCount;
			}
		}
		++delta;
		++n;
	}
	return output.join("");
};
/**
* Converts a Punycode string representing a domain name or an email address
* to Unicode. Only the Punycoded parts of the input will be converted, i.e.
* it doesn't matter if you call it on a string that has already been
* converted to Unicode.
* @memberOf punycode
* @param {String} input The Punycoded domain name or email address to
* convert to Unicode.
* @returns {String} The Unicode representation of the given Punycode
* string.
*/
var toUnicode = function(input) {
	return mapDomain(input, function(string) {
		return regexPunycode.test(string) ? decode(string.slice(4).toLowerCase()) : string;
	});
};
/**
* Converts a Unicode string representing a domain name or an email address to
* Punycode. Only the non-ASCII parts of the domain name will be converted,
* i.e. it doesn't matter if you call it with a domain that's already in
* ASCII.
* @memberOf punycode
* @param {String} input The domain name or email address to convert, as a
* Unicode string.
* @returns {String} The Punycode representation of the given domain name or
* email address.
*/
var toASCII = function(input) {
	return mapDomain(input, function(string) {
		return regexNonASCII.test(string) ? "xn--" + encode(string) : string;
	});
};
/** Define the public API */
var punycode = {
	/**
	* A string representing the current Punycode.js version number.
	* @memberOf punycode
	* @type String
	*/
	"version": "2.3.1",
	/**
	* An object of methods to convert from JavaScript's internal character
	* representation (UCS-2) to Unicode code points, and back.
	* @see <https://mathiasbynens.be/notes/javascript-encoding>
	* @memberOf punycode
	* @type Object
	*/
	"ucs2": {
		"decode": ucs2decode,
		"encode": ucs2encode
	},
	"decode": decode,
	"encode": encode,
	"toASCII": toASCII,
	"toUnicode": toUnicode
};
//#endregion
//#region node_modules/markdown-it/dist/markdown-it.mjs
/*! markdown-it 15.0.2 https://github.com/markdown-it/markdown-it @license MIT */
var __defProp = Object.defineProperty;
var __exportAll = (all, no_symbols) => {
	let target = {};
	for (var name in all) __defProp(target, name, {
		get: all[name],
		enumerable: true
	});
	if (!no_symbols) __defProp(target, Symbol.toStringTag, { value: "Module" });
	return target;
};
/**
* Common utility functions exposed through `md.utils` for use by plugins.
*
* @module md.utils
*/
var utils_exports = /* @__PURE__ */ __exportAll({
	arrayReplaceAt: () => arrayReplaceAt,
	asciiTrim: () => asciiTrim,
	callable: () => callable,
	escapeHtml: () => escapeHtml,
	escapeRE: () => escapeRE,
	fromCodePoint: () => fromCodePoint,
	isMdAsciiPunct: () => isMdAsciiPunct,
	isPunctChar: () => isPunctChar,
	isPunctCharCode: () => isPunctCharCode,
	isSpace: () => isSpace,
	isValidEntityCode: () => isValidEntityCode,
	isWhiteSpace: () => isWhiteSpace,
	lib: () => lib,
	normalizeReference: () => normalizeReference,
	unescapeAll: () => unescapeAll,
	unescapeMd: () => unescapeMd
});
function callable(cls) {
	const wrapper = function(...args) {
		return Reflect.construct(cls, args, new.target && new.target !== wrapper ? new.target : cls);
	};
	Object.defineProperty(wrapper, "name", { value: cls.name });
	Object.setPrototypeOf(wrapper, cls);
	wrapper.prototype = cls.prototype;
	return wrapper;
}
/**
* Returns a copy of a token array with the token at `pos` replaced by
* `newElements`. Used to transform token streams without modifying the
* original array.
*/
function arrayReplaceAt(src, pos, newElements) {
	return [].concat(src.slice(0, pos), newElements, src.slice(pos + 1));
}
/** Checks whether a code point can be decoded from a numeric HTML entity. */
function isValidEntityCode(c) {
	if (c >= 55296 && c <= 57343) return false;
	if (c >= 64976 && c <= 65007) return false;
	if ((c & 65535) === 65535 || (c & 65535) === 65534) return false;
	if (c >= 0 && c <= 8) return false;
	if (c === 11) return false;
	if (c >= 14 && c <= 31) return false;
	if (c >= 127 && c <= 159) return false;
	if (c > 1114111) return false;
	return true;
}
/**
* Converts a Unicode code point to a string, like `String.fromCodePoint()`,
* but does not throw for invalid input.
*/
function fromCodePoint(c) {
	if (c > 65535) {
		c -= 65536;
		const surrogate1 = 55296 + (c >> 10);
		const surrogate2 = 56320 + (c & 1023);
		return String.fromCharCode(surrogate1, surrogate2);
	}
	return String.fromCharCode(c);
}
var UNESCAPE_MD_RE = /\\([!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~])/g;
var UNESCAPE_ALL_RE = new RegExp(`${UNESCAPE_MD_RE.source}|${/&([a-z#][a-z0-9]{1,31});/gi.source}`, "gi");
var DIGITAL_ENTITY_TEST_RE = /^#((?:x[a-f0-9]{1,8}|[0-9]{1,8}))$/i;
function replaceEntityPattern(match, name) {
	if (name.charCodeAt(0) === 35 && DIGITAL_ENTITY_TEST_RE.test(name)) {
		const code = name[1].toLowerCase() === "x" ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
		if (isValidEntityCode(code)) return fromCodePoint(code);
		return match;
	}
	const decoded = decodeHTMLStrict(match);
	if (decoded !== match) return decoded;
	return match;
}
/** Decodes Markdown backslash escapes. */
function unescapeMd(str) {
	if (str.indexOf("\\") < 0) return str;
	return str.replace(UNESCAPE_MD_RE, "$1");
}
/**
* Decodes Markdown backslash escapes and HTML character references in link
* destinations, link titles, and fenced code info strings.
*/
function unescapeAll(str) {
	if (str.indexOf("\\") < 0 && str.indexOf("&") < 0) return str;
	return str.replace(UNESCAPE_ALL_RE, function(match, escaped, entity) {
		if (escaped) return escaped;
		return replaceEntityPattern(match, entity);
	});
}
var HTML_ESCAPE_TEST_RE = /[&<>"]/;
var HTML_ESCAPE_REPLACE_RE = /[&<>"]/g;
var HTML_REPLACEMENTS = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;"
};
function replaceUnsafeChar(ch) {
	return HTML_REPLACEMENTS[ch];
}
/** Escapes HTML special characters in a string. */
function escapeHtml(str) {
	if (HTML_ESCAPE_TEST_RE.test(str)) return str.replace(HTML_ESCAPE_REPLACE_RE, replaceUnsafeChar);
	return str;
}
var REGEXP_ESCAPE_RE = /[.?*+^$[\]\\(){}|-]/g;
/** Escapes regular expression metacharacters in a string. */
function escapeRE(str) {
	return str.replace(REGEXP_ESCAPE_RE, "\\$&");
}
/** Checks whether a character code is an ASCII space or tab. */
function isSpace(code) {
	switch (code) {
		case 9:
		case 32: return true;
	}
	return false;
}
/**
* Checks whether a character code is whitespace recognized by Markdown.
*
* Matches the Unicode `Zs` category or `\t`, `\f`, `\v`, `\r`, `\n`.
*/
function isWhiteSpace(code) {
	if (code >= 8192 && code <= 8202) return true;
	switch (code) {
		case 9:
		case 10:
		case 11:
		case 12:
		case 13:
		case 32:
		case 160:
		case 5760:
		case 8239:
		case 8287:
		case 12288: return true;
	}
	return false;
}
/**
* Checks whether a character is Unicode punctuation or a symbol.
*
* Does not support astral characters.
*/
function isPunctChar(ch) {
	return P.test(ch) || S.test(ch);
}
/** Checks whether a Unicode code point is punctuation or a symbol. */
function isPunctCharCode(code) {
	return isPunctChar(fromCodePoint(code));
}
/**
* Markdown ASCII punctuation characters.
*
*     !, ", #, $, %, &, ', (, ), *, +, ,, -, ., /, :, ;, <, =, >, ?, @,
*     [, \, ], ^, _, `, {, |, }, or ~
*
* http://spec.commonmark.org/0.15/#ascii-punctuation-character
*
* Don't confuse with Unicode punctuation. It lacks some characters in the
* ASCII range.
*/
function isMdAsciiPunct(ch) {
	switch (ch) {
		case 33:
		case 34:
		case 35:
		case 36:
		case 37:
		case 38:
		case 39:
		case 40:
		case 41:
		case 42:
		case 43:
		case 44:
		case 45:
		case 46:
		case 47:
		case 58:
		case 59:
		case 60:
		case 61:
		case 62:
		case 63:
		case 64:
		case 91:
		case 92:
		case 93:
		case 94:
		case 95:
		case 96:
		case 123:
		case 124:
		case 125:
		case 126: return true;
		default: return false;
	}
}
/** Normalizes `[reference labels]` for case-insensitive lookup. */
function normalizeReference(str) {
	str = str.trim().replace(/\s+/g, " ");
	return str.toLowerCase().toUpperCase();
}
function isAsciiTrimmable(c) {
	return c === 32 || c === 9 || c === 10 || c === 13;
}
/**
* "Light" `.trim()` for blocks (headings, paragraphs), where Unicode spaces
* should be preserved.
*/
function asciiTrim(str) {
	let start = 0;
	for (; start < str.length; start++) if (!isAsciiTrimmable(str.charCodeAt(start))) break;
	let end = str.length - 1;
	for (; end >= start; end--) if (!isAsciiTrimmable(str.charCodeAt(end))) break;
	return str.slice(start, end + 1);
}
/**
* Libraries commonly used by markdown-it and its plugins, re-exported to
* reduce duplicate dependencies in browser bundles.
*/
var lib = {
	mdurl: mdurl_exports,
	ucmicro: build_exports
};
/** Finds the end of a link or image label (`[label]`). */
function parseLinkLabel(state, start, disableNested) {
	let level, found, marker, prevPos;
	const max = state.posMax;
	const oldPos = state.pos;
	state.pos = start + 1;
	level = 1;
	while (state.pos < max) {
		marker = state.src.charCodeAt(state.pos);
		if (marker === 93) {
			level--;
			if (level === 0) {
				found = true;
				break;
			}
		}
		prevPos = state.pos;
		state.md.inline.skipToken(state);
		if (marker === 91) {
			if (prevPos === state.pos - 1) level++;
			else if (disableNested) {
				state.pos = oldPos;
				return -1;
			}
		}
	}
	let labelEnd = -1;
	if (found) labelEnd = state.pos;
	state.pos = oldPos;
	return labelEnd;
}
/** Parses the destination in `[label](destination "title")`. */
function parseLinkDestination(str, start, max) {
	let code;
	let pos = start;
	const result = {
		ok: false,
		pos: 0,
		str: ""
	};
	if (str.charCodeAt(pos) === 60) {
		pos++;
		while (pos < max) {
			code = str.charCodeAt(pos);
			if (code === 10) return result;
			if (code === 60) return result;
			if (code === 62) {
				result.pos = pos + 1;
				result.str = unescapeAll(str.slice(start + 1, pos));
				result.ok = true;
				return result;
			}
			if (code === 92 && pos + 1 < max) {
				pos += 2;
				continue;
			}
			pos++;
		}
		return result;
	}
	let level = 0;
	while (pos < max) {
		code = str.charCodeAt(pos);
		if (code === 32) break;
		if (code < 32 || code === 127) break;
		if (code === 92 && pos + 1 < max) {
			if (str.charCodeAt(pos + 1) === 32) {
				pos++;
				continue;
			}
			pos += 2;
			continue;
		}
		if (code === 40) {
			level++;
			if (level > 32) return result;
		}
		if (code === 41) {
			if (level === 0) break;
			level--;
		}
		pos++;
	}
	if (start === pos) return result;
	if (level !== 0) return result;
	result.str = unescapeAll(str.slice(start, pos));
	result.pos = pos;
	result.ok = true;
	return result;
}
/**
* Parses the optional title in `[label](destination "title")` or
* `[label]: destination "title"`.
*
* `prev_state` continues a reference title on the next source line.
*/
function parseLinkTitle(str, start, max, prev_state) {
	let code;
	let pos = start;
	const state = {
		ok: false,
		can_continue: false,
		pos: 0,
		str: "",
		marker: 0
	};
	if (prev_state) {
		state.str = prev_state.str;
		state.marker = prev_state.marker;
	} else {
		if (pos >= max) return state;
		let marker = str.charCodeAt(pos);
		if (marker !== 34 && marker !== 39 && marker !== 40) return state;
		start++;
		pos++;
		if (marker === 40) marker = 41;
		state.marker = marker;
	}
	while (pos < max) {
		code = str.charCodeAt(pos);
		if (code === state.marker) {
			state.pos = pos + 1;
			state.str += unescapeAll(str.slice(start, pos));
			state.ok = true;
			return state;
		} else if (code === 40 && state.marker === 41) return state;
		else if (code === 92 && pos + 1 < max) pos++;
		pos++;
	}
	state.can_continue = true;
	state.str += unescapeAll(str.slice(start, pos));
	return state;
}
/**
* Functions used to parse links and images, split out of parser rules because
* of their size.
*
* @module md.helpers
*/
var helpers_exports = /* @__PURE__ */ __exportAll({
	parseLinkDestination: () => parseLinkDestination,
	parseLinkLabel: () => parseLinkLabel,
	parseLinkTitle: () => parseLinkTitle
});
function _typeof(o) {
	"@babel/helpers - typeof";
	return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o) {
		return typeof o;
	} : function(o) {
		return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o;
	}, _typeof(o);
}
function toPrimitive(t, r) {
	if ("object" != _typeof(t) || !t) return t;
	var e = t[Symbol.toPrimitive];
	if (void 0 !== e) {
		var i = e.call(t, r || "default");
		if ("object" != _typeof(i)) return i;
		throw new TypeError("@@toPrimitive must return a primitive value.");
	}
	return ("string" === r ? String : Number)(t);
}
function toPropertyKey(t) {
	var i = toPrimitive(t, "string");
	return "symbol" == _typeof(i) ? i : i + "";
}
function _defineProperty(e, r, t) {
	return (r = toPropertyKey(r)) in e ? Object.defineProperty(e, r, {
		value: t,
		enumerable: !0,
		configurable: !0,
		writable: !0
	}) : e[r] = t, e;
}
/**
* Represents one item in the parsed token stream, storing parsed data and
* providing helpers for managing HTML attributes.
*/
var Token = class {
	constructor(type, tag, nesting) {
		_defineProperty(
			this,
			/**
			* Source map info. Format: `[ line_begin, line_end ]`
			*/
			"map",
			null
		);
		_defineProperty(
			this,
			/**
			* nesting level, the same as `state.level`
			*/
			"level",
			0
		);
		_defineProperty(
			this,
			/**
			* An array of child nodes (inline and img tokens)
			*/
			"children",
			null
		);
		_defineProperty(
			this,
			/**
			* In a case of self-closing tag (code, html, fence, etc.),
			* it has contents of this tag.
			*/
			"content",
			""
		);
		_defineProperty(
			this,
			/**
			* '*' or '_' for emphasis, fence string for fence, etc.
			*/
			"markup",
			""
		);
		_defineProperty(
			this,
			/**
			* Additional information:
			*
			* - Info string for "fence" tokens
			* - The value "auto" for autolink "link_open" and "link_close" tokens
			* - The string value of the item marker for ordered-list "list_item_open" tokens
			*/
			"info",
			""
		);
		_defineProperty(
			this,
			/**
			* True for block-level tokens, false for inline tokens.
			* Used in renderer to calculate line breaks
			*/
			"block",
			false
		);
		_defineProperty(
			this,
			/**
			* If it's true, ignore this element when rendering. Used for tight lists
			* to hide paragraphs.
			*/
			"hidden",
			false
		);
		this.type = type;
		this.tag = tag;
		this.attrs = null;
		this.nesting = nesting;
		this.meta = null;
	}
	/**
	* Search attribute index by name.
	*/
	attrIndex(name) {
		if (!this.attrs) return -1;
		const attrs = this.attrs;
		for (let i = 0, len = attrs.length; i < len; i++) if (attrs[i][0] === name) return i;
		return -1;
	}
	/**
	* Add `[ name, value ]` attribute to list. Init attrs if necessary
	*/
	attrPush(attrData) {
		if (this.attrs) this.attrs.push(attrData);
		else this.attrs = [attrData];
	}
	/**
	* Set `name` attribute to `value`. Override old value if exists.
	*/
	attrSet(name, value) {
		const idx = this.attrIndex(name);
		const attrData = [name, value];
		if (idx < 0) this.attrPush(attrData);
		else this.attrs[idx] = attrData;
	}
	/**
	* Get the value of attribute `name`, or null if it does not exist.
	*/
	attrGet(name) {
		const idx = this.attrIndex(name);
		let value = null;
		if (idx >= 0) value = this.attrs[idx][1];
		return value;
	}
	/**
	* Join value to existing attribute via space. Or create new attribute if not
	* exists. Useful to operate with token classes.
	*/
	attrJoin(name, value) {
		const idx = this.attrIndex(name);
		if (idx < 0) this.attrPush([name, value]);
		else this.attrs[idx][1] = `${this.attrs[idx][1]} ${value}`;
	}
};
/**
* Helper class, used by {@link MarkdownIt.core}, {@link MarkdownIt.block} and
* {@link MarkdownIt.inline} to manage sequences of functions (rules):
*
* - keep rules in defined order
* - assign the name to each rule
* - enable/disable rules
* - add/replace rules
* - allow assign rules to additional named chains (in the same)
* - cacheing lists of active rules
*
* You will not need use this class directly until write plugins. For simple
* rules control use {@link MarkdownIt.disable}, {@link MarkdownIt.enable} and
* {@link MarkdownIt.use}.
*/
var Ruler = class {
	constructor() {
		_defineProperty(
			this,
			/** @internal */
			"__rules__",
			[]
		);
		_defineProperty(
			this,
			/** @internal */
			"__cache__",
			null
		);
	}
	/** @internal */
	__find__(name) {
		for (let i = 0; i < this.__rules__.length; i++) if (this.__rules__[i].name === name) return i;
		return -1;
	}
	/** @internal */
	__compile__() {
		const chains = /* @__PURE__ */ new Set();
		this.__rules__.forEach((rule) => {
			if (!rule.enabled) return;
			rule.alt.forEach((altName) => {
				if (altName) chains.add(altName);
			});
		});
		this.__cache__ = Object.create(null);
		this.__cache__[""] = [];
		this.__rules__.forEach((rule) => {
			if (rule.enabled) this.__cache__[""].push(rule.fn);
		});
		chains.forEach((chain) => {
			this.__cache__[chain] = [];
			this.__rules__.forEach((rule) => {
				if (rule.enabled && rule.alt.indexOf(chain) >= 0) this.__cache__[chain].push(rule.fn);
			});
		});
	}
	/**
	* Replace rule by name with new function & options. Throws error if name not
	* found.
	*
	* @example Replace existing typographer replacement rule with new one
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	* const md = new MarkdownIt()
	*
	* md.core.ruler.at('replacements', function replace(state) {
	*   //...
	* });
	* ```
	*/
	at(name, fn, options = {}) {
		const index = this.__find__(name);
		if (index === -1) throw new Error(`Parser rule not found: ${name}`);
		this.__rules__[index].fn = fn;
		this.__rules__[index].alt = options.alt || [];
		this.__cache__ = null;
	}
	/**
	* Add new rule to chain before one with given name. See also
	* {@link Ruler.after}, {@link Ruler.push}.
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	* const md = new MarkdownIt()
	*
	* md.block.ruler.before('paragraph', 'my_rule', function replace(state) {
	*   //...
	* });
	* ```
	*/
	before(beforeName, ruleName, fn, options = {}) {
		const index = this.__find__(beforeName);
		if (index === -1) throw new Error(`Parser rule not found: ${beforeName}`);
		this.__rules__.splice(index, 0, {
			name: ruleName,
			enabled: true,
			fn,
			alt: options.alt || []
		});
		this.__cache__ = null;
	}
	/**
	* Add new rule to chain after one with given name. See also
	* {@link Ruler.before}, {@link Ruler.push}.
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	* const md = new MarkdownIt()
	*
	* md.inline.ruler.after('text', 'my_rule', function replace(state) {
	*   //...
	* });
	* ```
	*/
	after(afterName, ruleName, fn, options = {}) {
		const index = this.__find__(afterName);
		if (index === -1) throw new Error(`Parser rule not found: ${afterName}`);
		this.__rules__.splice(index + 1, 0, {
			name: ruleName,
			enabled: true,
			fn,
			alt: options.alt || []
		});
		this.__cache__ = null;
	}
	/**
	* Push new rule to the end of chain. See also
	* {@link Ruler.before}, {@link Ruler.after}.
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	* const md = new MarkdownIt()
	*
	* md.core.ruler.push('my_rule', function replace(state) {
	*   //...
	* });
	* ```
	*/
	push(ruleName, fn, options = {}) {
		this.__rules__.push({
			name: ruleName,
			enabled: true,
			fn,
			alt: options.alt || []
		});
		this.__cache__ = null;
	}
	/**
	* Enable rules with given names. If any rule name not found - throw Error.
	* Errors can be disabled by second param.
	*
	* See also {@link Ruler.disable}, {@link Ruler.enableOnly}.
	*
	* Returns list of found rule names (if no exception happened).
	*/
	enable(list, ignoreInvalid = false) {
		if (!Array.isArray(list)) list = [list];
		const result = [];
		list.forEach((name) => {
			const idx = this.__find__(name);
			if (idx < 0) {
				if (ignoreInvalid) return;
				throw new Error(`Rules manager: invalid rule name ${name}`);
			}
			this.__rules__[idx].enabled = true;
			result.push(name);
		});
		this.__cache__ = null;
		return result;
	}
	/**
	* Enable rules with given names, and disable everything else. If any rule name
	* not found - throw Error. Errors can be disabled by second param.
	*
	* See also {@link Ruler.disable}, {@link Ruler.enable}.
	*/
	enableOnly(list, ignoreInvalid = false) {
		if (!Array.isArray(list)) list = [list];
		this.__rules__.forEach((rule) => {
			rule.enabled = false;
		});
		this.enable(list, ignoreInvalid);
	}
	/**
	* Disable rules with given names. If any rule name not found - throw Error.
	* Errors can be disabled by second param.
	*
	* See also {@link Ruler.enable}, {@link Ruler.enableOnly}.
	*
	* Returns list of found rule names (if no exception happened).
	*/
	disable(list, ignoreInvalid = false) {
		if (!Array.isArray(list)) list = [list];
		const result = [];
		list.forEach((name) => {
			const idx = this.__find__(name);
			if (idx < 0) {
				if (ignoreInvalid) return;
				throw new Error(`Rules manager: invalid rule name ${name}`);
			}
			this.__rules__[idx].enabled = false;
			result.push(name);
		});
		this.__cache__ = null;
		return result;
	}
	/**
	* Return array of active functions (rules) for given chain name. It analyzes
	* rules configuration, compiles caches if not exists and returns result.
	*
	* Default chain name is `''` (empty string). It can't be skipped. That's
	* done intentionally, to keep signature monomorphic for high speed.
	*/
	getRules(chainName) {
		if (!this.__cache__) this.__compile__();
		return this.__cache__[chainName] || [];
	}
};
var default_rules = {};
default_rules.code_inline = function(tokens, idx, options, env, slf) {
	const token = tokens[idx];
	return `<code${slf.renderAttrs(token)}>${escapeHtml(token.content)}</code>`;
};
default_rules.code_block = function(tokens, idx, options, env, slf) {
	const token = tokens[idx];
	return `<pre${slf.renderAttrs(token)}><code>${escapeHtml(tokens[idx].content)}</code></pre>\n`;
};
default_rules.fence = function(tokens, idx, options, env, slf) {
	const token = tokens[idx];
	const info = token.info ? unescapeAll(token.info).trim() : "";
	let langName = "";
	let langAttrs = "";
	if (info) {
		const arr = info.split(/(\s+)/g);
		langName = arr[0];
		langAttrs = arr.slice(2).join("");
	}
	let highlighted;
	if (options.highlight) highlighted = options.highlight(token.content, langName, langAttrs) || escapeHtml(token.content);
	else highlighted = escapeHtml(token.content);
	if (highlighted.indexOf("<pre") === 0) return highlighted + "\n";
	if (info) {
		const i = token.attrIndex("class");
		const tmpAttrs = token.attrs ? token.attrs.slice() : [];
		if (i < 0) tmpAttrs.push(["class", `${options.langPrefix}${langName}`]);
		else {
			tmpAttrs[i] = [tmpAttrs[i][0], tmpAttrs[i][1]];
			tmpAttrs[i][1] += ` ${options.langPrefix}${langName}`;
		}
		const tmpToken = { attrs: tmpAttrs };
		return `<pre><code${slf.renderAttrs(tmpToken)}>${highlighted}</code></pre>\n`;
	}
	return `<pre><code${slf.renderAttrs(token)}>${highlighted}</code></pre>\n`;
};
default_rules.image = function(tokens, idx, options, env, slf) {
	const token = tokens[idx];
	token.attrs[token.attrIndex("alt")][1] = slf.renderInlineAsText(token.children, options, env);
	return slf.renderToken(tokens, idx, options);
};
default_rules.hardbreak = function(tokens, idx, options) {
	return options.xhtmlOut ? "<br />\n" : "<br>\n";
};
default_rules.softbreak = function(tokens, idx, options) {
	return options.breaks ? options.xhtmlOut ? "<br />\n" : "<br>\n" : "\n";
};
default_rules.text = function(tokens, idx) {
	return escapeHtml(tokens[idx].content);
};
default_rules.html_block = function(tokens, idx) {
	return tokens[idx].content;
};
default_rules.html_inline = function(tokens, idx) {
	return tokens[idx].content;
};
/**
* Generates HTML from parsed token stream. Each instance has independent
* copy of rules. Those can be rewritten with ease. Also, you can add new
* rules if you create plugin and adds new token types.
*
* Creates new renderer instance and fills {@link Renderer.rules} with defaults.
*/
var Renderer = class {
	constructor() {
		_defineProperty(
			this,
			/**
			* Contains render rules for tokens. Can be updated and extended.
			*
			* See [source code](https://github.com/markdown-it/markdown-it/blob/master/src/renderer.ts)
			* for more details and examples.
			*
			* @example Custom render rules
			* ```javascript
			* import MarkdownIt from 'markdown-it'
			* const md = new MarkdownIt()
			*
			* md.renderer.rules.strong_open  = function () { return '<b>'; };
			* md.renderer.rules.strong_close = function () { return '</b>'; };
			*
			* const result = md.renderInline(...);
			* ```
			*
			* @example Each rule is called as independent static function with fixed signature
			* ```javascript
			* function my_token_render(tokens, idx, options, env, renderer) {
			*   // ...
			*   return renderedHTML;
			* }
			* ```
			*/
			"rules",
			Object.assign({}, default_rules)
		);
	}
	/**
	* Render token attributes to string.
	*/
	renderAttrs(token) {
		let i, l, result;
		if (!token.attrs) return "";
		result = "";
		for (i = 0, l = token.attrs.length; i < l; i++) result += ` ${escapeHtml(token.attrs[i][0])}="${escapeHtml(String(token.attrs[i][1]))}"`;
		return result;
	}
	/**
	* Default token renderer. Can be overriden by custom function
	* in {@link Renderer.rules}.
	*/
	renderToken(tokens, idx, options) {
		const token = tokens[idx];
		let result = "";
		if (token.hidden) return "";
		let prev = idx - 1;
		while (prev >= 0 && tokens[prev].hidden && tokens[prev].nesting === 0) prev--;
		if (token.block && token.nesting !== -1 && prev >= 0 && tokens[prev].hidden && tokens[prev].nesting === -1) result += "\n";
		result += (token.nesting === -1 ? "</" : "<") + token.tag;
		result += this.renderAttrs(token);
		if (token.nesting === 0 && options.xhtmlOut) result += " /";
		let needLf = false;
		if (token.block) {
			needLf = true;
			if (token.nesting === 1) {
				let next = idx + 1;
				while (next < tokens.length && tokens[next].hidden && tokens[next].nesting === 0) next++;
				if (next < tokens.length) {
					const nextToken = tokens[next];
					if (nextToken.type === "inline" || nextToken.hidden) needLf = false;
					else if (nextToken.nesting === -1 && nextToken.tag === token.tag) needLf = false;
				}
			}
		}
		result += needLf ? ">\n" : ">";
		return result;
	}
	/**
	* The same as {@link Renderer.render}, but for single token of `inline` type.
	*/
	renderInline(tokens, options, env) {
		let result = "";
		const rules = this.rules;
		for (let i = 0, len = tokens.length; i < len; i++) {
			const type = tokens[i].type;
			if (typeof rules[type] !== "undefined") result += rules[type](tokens, i, options, env, this);
			else result += this.renderToken(tokens, i, options);
		}
		return result;
	}
	/**
	* Special kludge for image `alt` attributes to conform CommonMark spec.
	* Don't try to use it! Spec requires to show `alt` content with stripped markup,
	* instead of simple escaping.
	*/
	renderInlineAsText(tokens, options, env) {
		let result = "";
		for (let i = 0, len = tokens.length; i < len; i++) switch (tokens[i].type) {
			case "text":
			case "code_inline":
				result += tokens[i].content;
				break;
			case "image":
				result += this.renderInlineAsText(tokens[i].children, options, env);
				break;
			case "html_inline":
			case "html_block":
				result += tokens[i].content;
				break;
			case "softbreak":
			case "hardbreak": result += "\n";
		}
		return result;
	}
	/**
	* Takes token stream and generates HTML. Probably, you will never need to call
	* this method directly.
	*/
	render(tokens, options, env) {
		let result = "";
		const rules = this.rules;
		for (let i = 0, len = tokens.length; i < len; i++) {
			const type = tokens[i].type;
			if (type === "inline") result += this.renderInline(tokens[i].children, options, env);
			else if (typeof rules[type] !== "undefined") result += rules[type](tokens, i, options, env, this);
			else result += this.renderToken(tokens, i, options);
		}
		return result;
	}
};
/** Mutable state passed through the core rules chain. */
var StateCore = class {
	constructor(src, md, env) {
		_defineProperty(this, "tokens", []);
		_defineProperty(this, "inlineMode", false);
		_defineProperty(this, "Token", Token);
		this.src = src;
		this.env = env;
		this.md = md;
	}
};
var UNNORMALIZED_NEWLINE_RE = /\r\n?/g;
var NULL_RE = /\0/g;
function normalize(state) {
	let str;
	str = state.src.replace(UNNORMALIZED_NEWLINE_RE, "\n");
	str = str.replace(NULL_RE, "�");
	state.src = str;
}
function block(state) {
	let token;
	if (state.inlineMode) {
		token = new state.Token("inline", "", 0);
		token.content = state.src;
		token.map = [0, 1];
		token.children = [];
		state.tokens.push(token);
	} else state.md.block.parse(state.src, state.md, state.env, state.tokens);
}
function strip_references(state) {
	const tokens = state.tokens;
	let last = 0;
	for (let curr = 0; curr < tokens.length; curr++) {
		if (tokens[curr].type === "reference_definition") continue;
		if (curr !== last) tokens[last] = tokens[curr];
		last++;
	}
	if (tokens.length !== last) tokens.length = last;
}
function inline(state) {
	const tokens = state.tokens;
	for (let i = 0, l = tokens.length; i < l; i++) {
		const tok = tokens[i];
		if (tok.type === "inline") state.md.inline.parse(tok.content, state.md, state.env, tok.children);
	}
}
function isLinkOpen$1(str) {
	return /^<a[>\s]/i.test(str);
}
function isLinkClose$1(str) {
	return /^<\/a\s*>/i.test(str);
}
function linkify$1(state) {
	const blockTokens = state.tokens;
	if (!state.md.options.linkify) return;
	for (let j = 0, l = blockTokens.length; j < l; j++) {
		if (blockTokens[j].type !== "inline" || !state.md.linkify.test(blockTokens[j].content)) continue;
		const tokens = blockTokens[j].children;
		const replacements = [];
		let htmlLinkLevel = 0;
		for (let i = tokens.length - 1; i >= 0; i--) {
			const currentToken = tokens[i];
			if (currentToken.type === "link_close") {
				i--;
				while (tokens[i].level !== currentToken.level && tokens[i].type !== "link_open") i--;
				continue;
			}
			if (currentToken.type === "html_inline") {
				if (isLinkOpen$1(currentToken.content) && htmlLinkLevel > 0) htmlLinkLevel--;
				if (isLinkClose$1(currentToken.content)) htmlLinkLevel++;
			}
			if (htmlLinkLevel > 0) continue;
			if (currentToken.type === "text" && state.md.linkify.test(currentToken.content)) {
				const text = currentToken.content;
				let links = state.md.linkify.match(text);
				const nodes = [];
				let level = currentToken.level;
				let lastPos = 0;
				if (links.length > 0 && links[0].index === 0 && i > 0 && tokens[i - 1].type === "text_special") links = links.slice(1);
				for (let ln = 0; ln < links.length; ln++) {
					const url = links[ln].url;
					const fullUrl = state.md.normalizeLink(url);
					if (!state.md.validateLink(fullUrl)) continue;
					let urlText = links[ln].text;
					if (!links[ln].schema) urlText = state.md.normalizeLinkText(`http://${urlText}`).replace(/^http:\/\//, "");
					else if (links[ln].schema === "mailto:" && !/^mailto:/i.test(urlText)) urlText = state.md.normalizeLinkText(`mailto:${urlText}`).replace(/^mailto:/, "");
					else urlText = state.md.normalizeLinkText(urlText);
					const pos = links[ln].index;
					if (pos > lastPos) {
						const token = new state.Token("text", "", 0);
						token.content = text.slice(lastPos, pos);
						token.level = level;
						nodes.push(token);
					}
					const token_o = new state.Token("link_open", "a", 1);
					token_o.attrs = [["href", fullUrl]];
					token_o.level = level++;
					token_o.markup = "linkify";
					token_o.info = "auto";
					nodes.push(token_o);
					const token_t = new state.Token("text", "", 0);
					token_t.content = urlText;
					token_t.level = level;
					nodes.push(token_t);
					const token_c = new state.Token("link_close", "a", -1);
					token_c.level = --level;
					token_c.markup = "linkify";
					token_c.info = "auto";
					nodes.push(token_c);
					lastPos = links[ln].lastIndex;
				}
				if (lastPos < text.length) {
					const token = new state.Token("text", "", 0);
					token.content = text.slice(lastPos);
					token.level = level;
					nodes.push(token);
				}
				replacements.push({
					index: i,
					nodes
				});
			}
		}
		if (replacements.length > 0) {
			let newTokensLength = tokens.length;
			for (const replacement of replacements) newTokensLength += replacement.nodes.length - 1;
			const newTokens = new Array(newTokensLength);
			let replacementIndex = 0;
			let newTokenIndex = 0;
			replacements.reverse();
			for (let i = 0; i < tokens.length; i++) {
				const replacement = replacements[replacementIndex];
				if ((replacement === null || replacement === void 0 ? void 0 : replacement.index) === i) {
					for (const node of replacement.nodes) newTokens[newTokenIndex++] = node;
					replacementIndex++;
				} else newTokens[newTokenIndex++] = tokens[i];
			}
			blockTokens[j].children = newTokens;
		}
	}
}
var RARE_RE = /\+-|\.\.|\?\?\?\?|!!!!|,,|--/;
var SCOPED_ABBR_TEST_RE = /\((c|tm|r)\)/i;
var SCOPED_ABBR_RE = /\((c|tm|r)\)/gi;
var SCOPED_ABBR = {
	c: "©",
	r: "®",
	tm: "™"
};
function replaceFn(match, name) {
	return SCOPED_ABBR[name.toLowerCase()];
}
function replace_scoped(inlineTokens) {
	let inside_autolink = 0;
	for (let i = inlineTokens.length - 1; i >= 0; i--) {
		const token = inlineTokens[i];
		if (token.type === "text" && !inside_autolink) token.content = token.content.replace(SCOPED_ABBR_RE, replaceFn);
		if (token.type === "link_open" && token.info === "auto") inside_autolink--;
		if (token.type === "link_close" && token.info === "auto") inside_autolink++;
	}
}
function replace_rare(inlineTokens) {
	let inside_autolink = 0;
	for (let i = inlineTokens.length - 1; i >= 0; i--) {
		const token = inlineTokens[i];
		if (token.type === "text" && !inside_autolink) {
			if (RARE_RE.test(token.content)) token.content = token.content.replace(/\+-/g, "±").replace(/\.{2,}/g, "…").replace(/([?!])…/g, "$1..").replace(/([?!]){4,}/g, "$1$1$1").replace(/,{2,}/g, ",").replace(/(^|[^-])---(?=[^-]|$)/gm, "$1—").replace(/(^|\s)--(?=\s|$)/gm, "$1–").replace(/(^|[^-\s])--(?=[^-\s]|$)/gm, "$1–");
		}
		if (token.type === "link_open" && token.info === "auto") inside_autolink--;
		if (token.type === "link_close" && token.info === "auto") inside_autolink++;
	}
}
function replace(state) {
	let blkIdx;
	if (!state.md.options.typographer) return;
	for (blkIdx = state.tokens.length - 1; blkIdx >= 0; blkIdx--) {
		if (state.tokens[blkIdx].type !== "inline") continue;
		if (SCOPED_ABBR_TEST_RE.test(state.tokens[blkIdx].content)) replace_scoped(state.tokens[blkIdx].children);
		if (RARE_RE.test(state.tokens[blkIdx].content)) replace_rare(state.tokens[blkIdx].children);
	}
}
var QUOTE_TEST_RE = /['"]/;
var QUOTE_RE = /['"]/g;
var APOSTROPHE = "’";
var MAX_OPENERS = 1e3;
function truncateStack(stack, heads, length) {
	while (stack.length > length) {
		const item = stack.pop();
		if (item.isSingleQuote) heads.single = item.prevSameQuoteIdx;
		else heads.double = item.prevSameQuoteIdx;
	}
}
function addReplacement(replacements, tokenIdx, pos, ch) {
	if (!replacements[tokenIdx]) replacements[tokenIdx] = [];
	replacements[tokenIdx].push({
		pos,
		ch
	});
}
function applyReplacements(str, replacements) {
	let result = "";
	let lastPos = 0;
	replacements.sort((a, b) => a.pos - b.pos);
	for (let i = 0; i < replacements.length; i++) {
		const replacement = replacements[i];
		result += str.slice(lastPos, replacement.pos) + replacement.ch;
		lastPos = replacement.pos + 1;
	}
	return result + str.slice(lastPos);
}
function process_inlines(tokens, state) {
	let j;
	const stack = [];
	const heads = {
		single: -1,
		double: -1
	};
	const replacements = {};
	for (let i = 0; i < tokens.length; i++) {
		const token = tokens[i];
		const thisLevel = tokens[i].level;
		for (j = stack.length - 1; j >= 0; j--) if (stack[j].level <= thisLevel) break;
		truncateStack(stack, heads, j + 1);
		if (token.type !== "text") continue;
		const text = token.content;
		let pos = 0;
		const max = text.length;
		OUTER: while (pos < max) {
			QUOTE_RE.lastIndex = pos;
			const t = QUOTE_RE.exec(text);
			if (!t) break;
			let canOpen = true;
			let canClose = true;
			pos = t.index + 1;
			const isSingle = t[0] === "'";
			let lastChar = 32;
			if (t.index - 1 >= 0) lastChar = text.charCodeAt(t.index - 1);
			else for (j = i - 1; j >= 0; j--) {
				if (tokens[j].type === "softbreak" || tokens[j].type === "hardbreak") break;
				if (!tokens[j].content) continue;
				lastChar = tokens[j].content.charCodeAt(tokens[j].content.length - 1);
				break;
			}
			let nextChar = 32;
			if (pos < max) nextChar = text.charCodeAt(pos);
			else for (j = i + 1; j < tokens.length; j++) {
				if (tokens[j].type === "softbreak" || tokens[j].type === "hardbreak") break;
				if (!tokens[j].content) continue;
				nextChar = tokens[j].content.charCodeAt(0);
				break;
			}
			const isLastPunctChar = isMdAsciiPunct(lastChar) || isPunctCharCode(lastChar);
			const isNextPunctChar = isMdAsciiPunct(nextChar) || isPunctCharCode(nextChar);
			const isLastWhiteSpace = isWhiteSpace(lastChar);
			const isNextWhiteSpace = isWhiteSpace(nextChar);
			if (isNextWhiteSpace) canOpen = false;
			else if (isNextPunctChar) {
				if (!(isLastWhiteSpace || isLastPunctChar)) canOpen = false;
			}
			if (isLastWhiteSpace) canClose = false;
			else if (isLastPunctChar) {
				if (!(isNextWhiteSpace || isNextPunctChar)) canClose = false;
			}
			if (nextChar === 34 && t[0] === "\"") {
				if (lastChar >= 48 && lastChar <= 57) canClose = canOpen = false;
			}
			if (canOpen && canClose) {
				canOpen = isLastPunctChar;
				canClose = isNextPunctChar;
			}
			if (!canOpen && !canClose) {
				if (isSingle) addReplacement(replacements, i, t.index, APOSTROPHE);
				continue;
			}
			if (canClose) {
				j = isSingle ? heads.single : heads.double;
				if (j >= 0 && stack[j].level === thisLevel) {
					const item = stack[j];
					let openQuote;
					let closeQuote;
					if (isSingle) {
						openQuote = state.md.options.quotes[2];
						closeQuote = state.md.options.quotes[3];
					} else {
						openQuote = state.md.options.quotes[0];
						closeQuote = state.md.options.quotes[1];
					}
					addReplacement(replacements, i, t.index, closeQuote);
					addReplacement(replacements, item.tokenIdx, item.contentPos, openQuote);
					truncateStack(stack, heads, j);
					continue OUTER;
				}
			}
			if (canOpen) {
				if (stack.length >= MAX_OPENERS) return;
				stack.push({
					tokenIdx: i,
					contentPos: t.index,
					isSingleQuote: isSingle,
					level: thisLevel,
					prevSameQuoteIdx: isSingle ? heads.single : heads.double
				});
				if (isSingle) heads.single = stack.length - 1;
				else heads.double = stack.length - 1;
			} else if (canClose && isSingle) addReplacement(replacements, i, t.index, APOSTROPHE);
		}
	}
	Object.keys(replacements).forEach(function(tokenIdx) {
		const idx = Number(tokenIdx);
		tokens[idx].content = applyReplacements(tokens[idx].content, replacements[tokenIdx]);
	});
}
function smartquotes(state) {
	if (!state.md.options.typographer) return;
	for (let blkIdx = state.tokens.length - 1; blkIdx >= 0; blkIdx--) {
		if (state.tokens[blkIdx].type !== "inline" || !QUOTE_TEST_RE.test(state.tokens[blkIdx].content)) continue;
		process_inlines(state.tokens[blkIdx].children, state);
	}
}
function join_alt(tokens) {
	let curr, last;
	const max = tokens.length;
	for (curr = 0; curr < max; curr++) if (tokens[curr].type === "text_special") tokens[curr].type = "text";
	for (curr = last = 0; curr < max; curr++) if (tokens[curr].type === "text" && curr + 1 < max && tokens[curr + 1].type === "text") tokens[curr + 1].content = tokens[curr].content + tokens[curr + 1].content;
	else {
		if (curr !== last) tokens[last] = tokens[curr];
		last++;
	}
	if (curr !== last) tokens.length = last;
}
function text_join(state) {
	let curr, last;
	const blockTokens = state.tokens;
	const l = blockTokens.length;
	for (let j = 0; j < l; j++) {
		if (blockTokens[j].type !== "inline") continue;
		const tokens = blockTokens[j].children;
		const max = tokens.length;
		for (curr = 0; curr < max; curr++) {
			if (tokens[curr].type === "text_special") tokens[curr].type = "text";
			if (tokens[curr].children) join_alt(tokens[curr].children);
		}
		for (curr = last = 0; curr < max; curr++) if (tokens[curr].type === "text" && curr + 1 < max && tokens[curr + 1].type === "text") tokens[curr + 1].content = tokens[curr].content + tokens[curr + 1].content;
		else {
			if (curr !== last) tokens[last] = tokens[curr];
			last++;
		}
		if (curr !== last) tokens.length = last;
	}
}
var _rules$2 = [
	["normalize", normalize],
	["block", block],
	["strip_references", strip_references],
	["inline", inline],
	["linkify", linkify$1],
	["replacements", replace],
	["smartquotes", smartquotes],
	["text_join", text_join]
];
/**
* Top-level rules executor. Glues block/inline parsers and does intermediate
* transformations.
*/
var ParserCore = class {
	constructor() {
		_defineProperty(
			this,
			/**
			* {@link Ruler} instance. Keep configuration of core rules.
			*/
			"ruler",
			new Ruler()
		);
		_defineProperty(this, "State", StateCore);
		for (let i = 0; i < _rules$2.length; i++) this.ruler.push(_rules$2[i][0], _rules$2[i][1]);
	}
	/**
	* Executes core chain rules.
	*/
	process(state) {
		const rules = this.ruler.getRules("");
		for (let i = 0, l = rules.length; i < l; i++) rules[i](state);
	}
};
/** Mutable state passed to block rules while tokenizing a source document. */
var StateBlock = class {
	constructor(src, md, env, tokens) {
		_defineProperty(this, "bMarks", []);
		_defineProperty(this, "eMarks", []);
		_defineProperty(this, "tShift", []);
		_defineProperty(this, "sCount", []);
		_defineProperty(this, "bsCount", []);
		_defineProperty(this, "blkIndent", 0);
		_defineProperty(this, "line", 0);
		_defineProperty(this, "lineMax", 0);
		_defineProperty(this, "tight", false);
		_defineProperty(this, "listIndent", -1);
		_defineProperty(this, "parentType", "root");
		_defineProperty(this, "level", 0);
		_defineProperty(this, "Token", Token);
		this.src = src;
		this.md = md;
		this.env = env;
		this.tokens = tokens;
		const s = this.src;
		for (let start = 0, pos = 0, indent = 0, offset = 0, len = s.length, indent_found = false; pos < len; pos++) {
			const ch = s.charCodeAt(pos);
			if (!indent_found) if (isSpace(ch)) {
				indent++;
				if (ch === 9) offset += 4 - offset % 4;
				else offset++;
				continue;
			} else indent_found = true;
			if (ch === 10 || pos === len - 1) {
				if (ch !== 10) pos++;
				this.bMarks.push(start);
				this.eMarks.push(pos);
				this.tShift.push(indent);
				this.sCount.push(offset);
				this.bsCount.push(0);
				indent_found = false;
				indent = 0;
				offset = 0;
				start = pos + 1;
			}
		}
		this.bMarks.push(s.length);
		this.eMarks.push(s.length);
		this.tShift.push(0);
		this.sCount.push(0);
		this.bsCount.push(0);
		this.lineMax = this.bMarks.length - 1;
	}
	push(type, tag, nesting) {
		const token = new Token(type, tag, nesting);
		token.block = true;
		if (nesting < 0) this.level--;
		token.level = this.level;
		if (nesting > 0) this.level++;
		this.tokens.push(token);
		return token;
	}
	isEmpty(line) {
		return this.bMarks[line] + this.tShift[line] >= this.eMarks[line];
	}
	skipEmptyLines(from) {
		for (let max = this.lineMax; from < max; from++) if (this.bMarks[from] + this.tShift[from] < this.eMarks[from]) break;
		return from;
	}
	skipSpaces(pos) {
		for (let max = this.src.length; pos < max; pos++) if (!isSpace(this.src.charCodeAt(pos))) break;
		return pos;
	}
	skipSpacesBack(pos, min) {
		if (pos <= min) return pos;
		while (pos > min) if (!isSpace(this.src.charCodeAt(--pos))) return pos + 1;
		return pos;
	}
	skipChars(pos, code) {
		for (let max = this.src.length; pos < max; pos++) if (this.src.charCodeAt(pos) !== code) break;
		return pos;
	}
	skipCharsBack(pos, code, min) {
		if (pos <= min) return pos;
		while (pos > min) if (code !== this.src.charCodeAt(--pos)) return pos + 1;
		return pos;
	}
	getLines(begin, end, indent, keepLastLF) {
		if (begin >= end) return "";
		const queue = new Array(end - begin);
		for (let i = 0, line = begin; line < end; line++, i++) {
			let lineIndent = 0;
			const lineStart = this.bMarks[line];
			let first = lineStart;
			let last;
			if (line + 1 < end || keepLastLF) last = this.eMarks[line] + 1;
			else last = this.eMarks[line];
			while (first < last && lineIndent < indent) {
				const ch = this.src.charCodeAt(first);
				if (isSpace(ch)) if (ch === 9) lineIndent += 4 - (lineIndent + this.bsCount[line]) % 4;
				else lineIndent++;
				else if (first - lineStart < this.tShift[line]) lineIndent++;
				else break;
				first++;
			}
			if (lineIndent > indent) queue[i] = new Array(lineIndent - indent + 1).join(" ") + this.src.slice(first, last);
			else queue[i] = this.src.slice(first, last);
		}
		return queue.join("");
	}
};
var MAX_AUTOCOMPLETED_CELLS = 65536;
function getLine(state, line) {
	const pos = state.bMarks[line] + state.tShift[line];
	const max = state.eMarks[line];
	return state.src.slice(pos, max);
}
function escapedSplit(str) {
	const result = [];
	const max = str.length;
	let pos = 0;
	let ch = str.charCodeAt(pos);
	let isEscaped = false;
	let lastPos = 0;
	let current = "";
	while (pos < max) {
		if (ch === 124) if (!isEscaped) {
			result.push(current + str.substring(lastPos, pos));
			current = "";
			lastPos = pos + 1;
		} else {
			current += str.substring(lastPos, pos - 1);
			lastPos = pos;
		}
		isEscaped = ch === 92;
		pos++;
		ch = str.charCodeAt(pos);
	}
	result.push(current + str.substring(lastPos));
	return result;
}
function table(state, startLine, endLine, silent) {
	if (startLine + 2 > endLine) return false;
	let nextLine = startLine + 1;
	if (state.sCount[nextLine] < state.blkIndent) return false;
	if (state.sCount[nextLine] - state.blkIndent >= 4) return false;
	let pos = state.bMarks[nextLine] + state.tShift[nextLine];
	if (pos >= state.eMarks[nextLine]) return false;
	const firstCh = state.src.charCodeAt(pos++);
	if (firstCh !== 124 && firstCh !== 45 && firstCh !== 58) return false;
	if (pos >= state.eMarks[nextLine]) return false;
	const secondCh = state.src.charCodeAt(pos++);
	if (secondCh !== 124 && secondCh !== 45 && secondCh !== 58 && !isSpace(secondCh)) return false;
	if (firstCh === 45 && isSpace(secondCh)) return false;
	while (pos < state.eMarks[nextLine]) {
		const ch = state.src.charCodeAt(pos);
		if (ch !== 124 && ch !== 45 && ch !== 58 && !isSpace(ch)) return false;
		pos++;
	}
	let lineText = getLine(state, startLine + 1);
	let columns = lineText.split("|");
	const aligns = [];
	for (let i = 0; i < columns.length; i++) {
		const t = columns[i].trim();
		if (!t) if (i === 0 || i === columns.length - 1) continue;
		else return false;
		if (!/^:?-+:?$/.test(t)) return false;
		if (t.charCodeAt(t.length - 1) === 58) aligns.push(t.charCodeAt(0) === 58 ? "center" : "right");
		else if (t.charCodeAt(0) === 58) aligns.push("left");
		else aligns.push("");
	}
	lineText = getLine(state, startLine).trim();
	if (lineText.indexOf("|") === -1) return false;
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	columns = escapedSplit(lineText);
	if (columns.length && columns[0] === "") columns.shift();
	if (columns.length && columns[columns.length - 1] === "") columns.pop();
	const columnCount = columns.length;
	if (columnCount === 0 || columnCount !== aligns.length) return false;
	if (silent) return true;
	const oldParentType = state.parentType;
	state.parentType = "table";
	const terminatorRules = state.md.block.ruler.getRules("blockquote");
	const token_to = state.push("table_open", "table", 1);
	const tableLines = [startLine, 0];
	token_to.map = tableLines;
	const token_tho = state.push("thead_open", "thead", 1);
	token_tho.map = [startLine, startLine + 1];
	const token_htro = state.push("tr_open", "tr", 1);
	token_htro.map = [startLine, startLine + 1];
	for (let i = 0; i < columns.length; i++) {
		const token_ho = state.push("th_open", "th", 1);
		if (aligns[i]) token_ho.attrs = [["style", `text-align:${aligns[i]}`]];
		const token_il = state.push("inline", "", 0);
		token_il.content = columns[i].trim();
		token_il.children = [];
		state.push("th_close", "th", -1);
	}
	state.push("tr_close", "tr", -1);
	state.push("thead_close", "thead", -1);
	let tbodyLines;
	let autocompletedCells = 0;
	for (nextLine = startLine + 2; nextLine < endLine; nextLine++) {
		if (state.sCount[nextLine] < state.blkIndent) break;
		let terminate = false;
		for (let i = 0, l = terminatorRules.length; i < l; i++) if (terminatorRules[i](state, nextLine, endLine, true)) {
			terminate = true;
			break;
		}
		if (terminate) break;
		lineText = getLine(state, nextLine).trim();
		if (!lineText) break;
		if (state.sCount[nextLine] - state.blkIndent >= 4) break;
		columns = escapedSplit(lineText);
		if (columns.length && columns[0] === "") columns.shift();
		if (columns.length && columns[columns.length - 1] === "") columns.pop();
		autocompletedCells += columnCount - columns.length;
		if (autocompletedCells > MAX_AUTOCOMPLETED_CELLS) break;
		if (nextLine === startLine + 2) {
			const token_tbo = state.push("tbody_open", "tbody", 1);
			token_tbo.map = tbodyLines = [startLine + 2, 0];
		}
		const token_tro = state.push("tr_open", "tr", 1);
		token_tro.map = [nextLine, nextLine + 1];
		for (let i = 0; i < columnCount; i++) {
			const token_tdo = state.push("td_open", "td", 1);
			if (aligns[i]) token_tdo.attrs = [["style", `text-align:${aligns[i]}`]];
			const token_il = state.push("inline", "", 0);
			token_il.content = columns[i] ? columns[i].trim() : "";
			token_il.children = [];
			state.push("td_close", "td", -1);
		}
		state.push("tr_close", "tr", -1);
	}
	if (tbodyLines) {
		state.push("tbody_close", "tbody", -1);
		tbodyLines[1] = nextLine;
	}
	state.push("table_close", "table", -1);
	tableLines[1] = nextLine;
	state.parentType = oldParentType;
	state.line = nextLine;
	return true;
}
function code(state, startLine, endLine) {
	if (state.sCount[startLine] - state.blkIndent < 4) return false;
	let nextLine = startLine + 1;
	let last = nextLine;
	while (nextLine < endLine) {
		if (state.isEmpty(nextLine)) {
			nextLine++;
			continue;
		}
		if (state.sCount[nextLine] - state.blkIndent >= 4) {
			nextLine++;
			last = nextLine;
			continue;
		}
		break;
	}
	state.line = last;
	const token = state.push("code_block", "code", 0);
	token.content = state.getLines(startLine, last, 4 + state.blkIndent, false) + "\n";
	token.map = [startLine, state.line];
	return true;
}
function fence(state, startLine, endLine, silent) {
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	let max = state.eMarks[startLine];
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	if (pos + 3 > max) return false;
	const marker = state.src.charCodeAt(pos);
	if (marker !== 126 && marker !== 96) return false;
	let mem = pos;
	pos = state.skipChars(pos, marker);
	let len = pos - mem;
	if (len < 3) return false;
	const markup = state.src.slice(mem, pos);
	const params = state.src.slice(pos, max);
	if (marker === 96) {
		if (params.indexOf(String.fromCharCode(marker)) >= 0) return false;
	}
	if (silent) return true;
	let nextLine = startLine;
	let haveEndMarker = false;
	for (;;) {
		nextLine++;
		if (nextLine >= endLine) break;
		pos = mem = state.bMarks[nextLine] + state.tShift[nextLine];
		max = state.eMarks[nextLine];
		if (pos < max && state.sCount[nextLine] < state.blkIndent) break;
		if (state.src.charCodeAt(pos) !== marker) continue;
		if (state.sCount[nextLine] - state.blkIndent >= 4) continue;
		pos = state.skipChars(pos, marker);
		if (pos - mem < len) continue;
		pos = state.skipSpaces(pos);
		if (pos < max) continue;
		haveEndMarker = true;
		break;
	}
	len = state.sCount[startLine];
	state.line = nextLine + (haveEndMarker ? 1 : 0);
	const token = state.push("fence", "code", 0);
	token.info = params;
	token.content = state.getLines(startLine + 1, nextLine, len, true);
	token.markup = markup;
	token.map = [startLine, state.line];
	return true;
}
function blockquote(state, startLine, endLine, silent) {
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	let max = state.eMarks[startLine];
	const oldLineMax = state.lineMax;
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	if (state.src.charCodeAt(pos) !== 62) return false;
	if (silent) return true;
	const oldBMarks = [];
	const oldBSCount = [];
	const oldSCount = [];
	const oldTShift = [];
	const terminatorRules = state.md.block.ruler.getRules("blockquote");
	const oldParentType = state.parentType;
	state.parentType = "blockquote";
	let lastLineEmpty = false;
	let nextLine;
	for (nextLine = startLine; nextLine < endLine; nextLine++) {
		const isOutdented = state.sCount[nextLine] < state.blkIndent;
		pos = state.bMarks[nextLine] + state.tShift[nextLine];
		max = state.eMarks[nextLine];
		if (pos >= max) break;
		if (state.src.charCodeAt(pos++) === 62 && !isOutdented) {
			let initial = state.sCount[nextLine] + 1;
			let spaceAfterMarker;
			let adjustTab;
			if (state.src.charCodeAt(pos) === 32) {
				pos++;
				initial++;
				adjustTab = false;
				spaceAfterMarker = true;
			} else if (state.src.charCodeAt(pos) === 9) {
				spaceAfterMarker = true;
				if ((state.bsCount[nextLine] + initial) % 4 === 3) {
					pos++;
					initial++;
					adjustTab = false;
				} else adjustTab = true;
			} else spaceAfterMarker = false;
			let offset = initial;
			oldBMarks.push(state.bMarks[nextLine]);
			state.bMarks[nextLine] = pos;
			while (pos < max) {
				const ch = state.src.charCodeAt(pos);
				if (isSpace(ch)) if (ch === 9) offset += 4 - (offset + state.bsCount[nextLine] + (adjustTab ? 1 : 0)) % 4;
				else offset++;
				else break;
				pos++;
			}
			lastLineEmpty = pos >= max;
			oldBSCount.push(state.bsCount[nextLine]);
			state.bsCount[nextLine] = state.sCount[nextLine] + 1 + (spaceAfterMarker ? 1 : 0);
			oldSCount.push(state.sCount[nextLine]);
			state.sCount[nextLine] = offset - initial;
			oldTShift.push(state.tShift[nextLine]);
			state.tShift[nextLine] = pos - state.bMarks[nextLine];
			continue;
		}
		if (lastLineEmpty) break;
		let terminate = false;
		for (let i = 0, l = terminatorRules.length; i < l; i++) if (terminatorRules[i](state, nextLine, endLine, true)) {
			terminate = true;
			break;
		}
		if (terminate) {
			state.lineMax = nextLine;
			if (state.blkIndent !== 0) {
				oldBMarks.push(state.bMarks[nextLine]);
				oldBSCount.push(state.bsCount[nextLine]);
				oldTShift.push(state.tShift[nextLine]);
				oldSCount.push(state.sCount[nextLine]);
				state.sCount[nextLine] -= state.blkIndent;
			}
			break;
		}
		oldBMarks.push(state.bMarks[nextLine]);
		oldBSCount.push(state.bsCount[nextLine]);
		oldTShift.push(state.tShift[nextLine]);
		oldSCount.push(state.sCount[nextLine]);
		state.sCount[nextLine] = -1;
	}
	const oldIndent = state.blkIndent;
	state.blkIndent = 0;
	const token_o = state.push("blockquote_open", "blockquote", 1);
	token_o.markup = ">";
	const lines = [startLine, 0];
	token_o.map = lines;
	state.md.block.tokenize(state, startLine, nextLine);
	const token_c = state.push("blockquote_close", "blockquote", -1);
	token_c.markup = ">";
	state.lineMax = oldLineMax;
	state.parentType = oldParentType;
	lines[1] = state.line;
	for (let i = 0; i < oldTShift.length; i++) {
		state.bMarks[i + startLine] = oldBMarks[i];
		state.tShift[i + startLine] = oldTShift[i];
		state.sCount[i + startLine] = oldSCount[i];
		state.bsCount[i + startLine] = oldBSCount[i];
	}
	state.blkIndent = oldIndent;
	return true;
}
function hr(state, startLine, endLine, silent) {
	const max = state.eMarks[startLine];
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	const marker = state.src.charCodeAt(pos++);
	if (marker !== 42 && marker !== 45 && marker !== 95) return false;
	let cnt = 1;
	while (pos < max) {
		const ch = state.src.charCodeAt(pos++);
		if (ch !== marker && !isSpace(ch)) return false;
		if (ch === marker) cnt++;
	}
	if (cnt < 3) return false;
	if (silent) return true;
	state.line = startLine + 1;
	const token = state.push("hr", "hr", 0);
	token.map = [startLine, state.line];
	token.markup = Array(cnt + 1).join(String.fromCharCode(marker));
	return true;
}
function skipBulletListMarker(state, startLine) {
	const max = state.eMarks[startLine];
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	const marker = state.src.charCodeAt(pos++);
	if (marker !== 42 && marker !== 45 && marker !== 43) return -1;
	if (pos < max) {
		if (!isSpace(state.src.charCodeAt(pos))) return -1;
	}
	return pos;
}
function skipOrderedListMarker(state, startLine) {
	const start = state.bMarks[startLine] + state.tShift[startLine];
	const max = state.eMarks[startLine];
	let pos = start;
	if (pos + 1 >= max) return -1;
	let ch = state.src.charCodeAt(pos++);
	if (ch < 48 || ch > 57) return -1;
	for (;;) {
		if (pos >= max) return -1;
		ch = state.src.charCodeAt(pos++);
		if (ch >= 48 && ch <= 57) {
			if (pos - start >= 10) return -1;
			continue;
		}
		if (ch === 41 || ch === 46) break;
		return -1;
	}
	if (pos < max) {
		ch = state.src.charCodeAt(pos);
		if (!isSpace(ch)) return -1;
	}
	return pos;
}
function markTightParagraphs(state, idx) {
	const level = state.level + 2;
	for (let i = idx + 2, l = state.tokens.length - 2; i < l; i++) if (state.tokens[i].level === level && state.tokens[i].type === "paragraph_open") {
		state.tokens[i + 2].hidden = true;
		state.tokens[i].hidden = true;
		i += 2;
	}
}
function list(state, startLine, endLine, silent) {
	let max, pos, start, token;
	let nextLine = startLine;
	let tight = true;
	if (state.sCount[nextLine] - state.blkIndent >= 4) return false;
	if (state.listIndent >= 0 && state.sCount[nextLine] - state.listIndent >= 4 && state.sCount[nextLine] < state.blkIndent) return false;
	let isTerminatingParagraph = false;
	if (silent && state.parentType === "paragraph") {
		if (state.sCount[nextLine] >= state.blkIndent) isTerminatingParagraph = true;
	}
	let isOrdered;
	let markerValue;
	let posAfterMarker;
	if ((posAfterMarker = skipOrderedListMarker(state, nextLine)) >= 0) {
		isOrdered = true;
		start = state.bMarks[nextLine] + state.tShift[nextLine];
		markerValue = Number(state.src.slice(start, posAfterMarker - 1));
		if (isTerminatingParagraph && markerValue !== 1) return false;
	} else if ((posAfterMarker = skipBulletListMarker(state, nextLine)) >= 0) isOrdered = false;
	else return false;
	if (isTerminatingParagraph) {
		if (state.skipSpaces(posAfterMarker) >= state.eMarks[nextLine]) return false;
	}
	if (silent) return true;
	const markerCharCode = state.src.charCodeAt(posAfterMarker - 1);
	const listTokIdx = state.tokens.length;
	if (isOrdered) {
		token = state.push("ordered_list_open", "ol", 1);
		if (markerValue !== 1) token.attrs = [["start", markerValue]];
	} else token = state.push("bullet_list_open", "ul", 1);
	const listLines = [nextLine, 0];
	token.map = listLines;
	token.markup = String.fromCharCode(markerCharCode);
	let prevEmptyEnd = false;
	const terminatorRules = state.md.block.ruler.getRules("list");
	const oldParentType = state.parentType;
	state.parentType = "list";
	while (nextLine < endLine) {
		pos = posAfterMarker;
		max = state.eMarks[nextLine];
		const initial = state.sCount[nextLine] + posAfterMarker - (state.bMarks[nextLine] + state.tShift[nextLine]);
		let offset = initial;
		while (pos < max) {
			const ch = state.src.charCodeAt(pos);
			if (ch === 9) offset += 4 - (offset + state.bsCount[nextLine]) % 4;
			else if (ch === 32) offset++;
			else break;
			pos++;
		}
		const contentStart = pos;
		let indentAfterMarker;
		if (contentStart >= max) indentAfterMarker = 1;
		else indentAfterMarker = offset - initial;
		if (indentAfterMarker > 4) indentAfterMarker = 1;
		const indent = initial + indentAfterMarker;
		token = state.push("list_item_open", "li", 1);
		token.markup = String.fromCharCode(markerCharCode);
		const itemLines = [nextLine, 0];
		token.map = itemLines;
		if (isOrdered) token.info = state.src.slice(start, posAfterMarker - 1);
		const oldTight = state.tight;
		const oldTShift = state.tShift[nextLine];
		const oldSCount = state.sCount[nextLine];
		const oldListIndent = state.listIndent;
		state.listIndent = state.blkIndent;
		state.blkIndent = indent;
		state.tight = true;
		state.tShift[nextLine] = contentStart - state.bMarks[nextLine];
		state.sCount[nextLine] = offset;
		if (contentStart >= max && state.isEmpty(nextLine + 1)) state.line = Math.min(state.line + 2, endLine);
		else state.md.block.tokenize(state, nextLine, endLine);
		if (!state.tight || prevEmptyEnd) tight = false;
		prevEmptyEnd = state.line - nextLine > 1 && state.isEmpty(state.line - 1);
		state.blkIndent = state.listIndent;
		state.listIndent = oldListIndent;
		state.tShift[nextLine] = oldTShift;
		state.sCount[nextLine] = oldSCount;
		state.tight = oldTight;
		token = state.push("list_item_close", "li", -1);
		token.markup = String.fromCharCode(markerCharCode);
		nextLine = state.line;
		itemLines[1] = nextLine;
		if (nextLine >= endLine) break;
		if (state.sCount[nextLine] < state.blkIndent) break;
		if (state.sCount[nextLine] - state.blkIndent >= 4) break;
		let terminate = false;
		for (let i = 0, l = terminatorRules.length; i < l; i++) if (terminatorRules[i](state, nextLine, endLine, true)) {
			terminate = true;
			break;
		}
		if (terminate) break;
		if (isOrdered) {
			posAfterMarker = skipOrderedListMarker(state, nextLine);
			if (posAfterMarker < 0) break;
			start = state.bMarks[nextLine] + state.tShift[nextLine];
		} else {
			posAfterMarker = skipBulletListMarker(state, nextLine);
			if (posAfterMarker < 0) break;
		}
		if (markerCharCode !== state.src.charCodeAt(posAfterMarker - 1)) break;
	}
	if (isOrdered) token = state.push("ordered_list_close", "ol", -1);
	else token = state.push("bullet_list_close", "ul", -1);
	token.markup = String.fromCharCode(markerCharCode);
	listLines[1] = nextLine;
	state.line = nextLine;
	state.parentType = oldParentType;
	if (tight) markTightParagraphs(state, listTokIdx);
	return true;
}
function reference(state, startLine, _endLine, silent) {
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	let max = state.eMarks[startLine];
	let nextLine = startLine + 1;
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	if (state.src.charCodeAt(pos) !== 91) return false;
	function getNextLine(nextLine) {
		const endLine = state.lineMax;
		if (nextLine >= endLine || state.isEmpty(nextLine)) return null;
		let isContinuation = false;
		if (state.sCount[nextLine] - state.blkIndent > 3) isContinuation = true;
		if (state.sCount[nextLine] < 0) isContinuation = true;
		if (!isContinuation) {
			const terminatorRules = state.md.block.ruler.getRules("reference");
			const oldParentType = state.parentType;
			state.parentType = "reference";
			let terminate = false;
			for (let i = 0, l = terminatorRules.length; i < l; i++) if (terminatorRules[i](state, nextLine, endLine, true)) {
				terminate = true;
				break;
			}
			state.parentType = oldParentType;
			if (terminate) return null;
		}
		const pos = state.bMarks[nextLine] + state.tShift[nextLine];
		const max = state.eMarks[nextLine];
		return state.src.slice(pos, max + 1);
	}
	let str = state.src.slice(pos, max + 1);
	max = str.length;
	let labelEnd = -1;
	for (pos = 1; pos < max; pos++) {
		const ch = str.charCodeAt(pos);
		if (ch === 91) return false;
		else if (ch === 93) {
			labelEnd = pos;
			break;
		} else if (ch === 10) {
			const lineContent = getNextLine(nextLine);
			if (lineContent !== null) {
				str += lineContent;
				max = str.length;
				nextLine++;
			}
		} else if (ch === 92) {
			pos++;
			if (pos < max && str.charCodeAt(pos) === 10) {
				const lineContent = getNextLine(nextLine);
				if (lineContent !== null) {
					str += lineContent;
					max = str.length;
					nextLine++;
				}
			}
		}
	}
	if (labelEnd < 0 || str.charCodeAt(labelEnd + 1) !== 58) return false;
	for (pos = labelEnd + 2; pos < max; pos++) {
		const ch = str.charCodeAt(pos);
		if (ch === 10) {
			const lineContent = getNextLine(nextLine);
			if (lineContent !== null) {
				str += lineContent;
				max = str.length;
				nextLine++;
			}
		} else if (isSpace(ch)) {} else break;
	}
	const destRes = state.md.helpers.parseLinkDestination(str, pos, max);
	if (!destRes.ok) return false;
	const href = state.md.normalizeLink(destRes.str);
	if (!state.md.validateLink(href)) return false;
	pos = destRes.pos;
	const destEndPos = pos;
	const destEndLineNo = nextLine;
	const start = pos;
	for (; pos < max; pos++) {
		const ch = str.charCodeAt(pos);
		if (ch === 10) {
			const lineContent = getNextLine(nextLine);
			if (lineContent !== null) {
				str += lineContent;
				max = str.length;
				nextLine++;
			}
		} else if (isSpace(ch)) {} else break;
	}
	let titleRes = state.md.helpers.parseLinkTitle(str, pos, max);
	while (titleRes.can_continue) {
		const lineContent = getNextLine(nextLine);
		if (lineContent === null) break;
		str += lineContent;
		pos = max;
		max = str.length;
		nextLine++;
		titleRes = state.md.helpers.parseLinkTitle(str, pos, max, titleRes);
	}
	let title;
	if (pos < max && start !== pos && titleRes.ok) {
		title = titleRes.str;
		pos = titleRes.pos;
	} else {
		title = "";
		pos = destEndPos;
		nextLine = destEndLineNo;
	}
	while (pos < max) {
		if (!isSpace(str.charCodeAt(pos))) break;
		pos++;
	}
	if (pos < max && str.charCodeAt(pos) !== 10) {
		if (title) {
			title = "";
			pos = destEndPos;
			nextLine = destEndLineNo;
			while (pos < max) {
				if (!isSpace(str.charCodeAt(pos))) break;
				pos++;
			}
		}
	}
	if (pos < max && str.charCodeAt(pos) !== 10) return false;
	const label = normalizeReference(str.slice(1, labelEnd));
	if (!label) return false;
	/* istanbul ignore if */
	if (silent) return true;
	if (typeof state.env.references === "undefined") state.env.references = {};
	if (typeof state.env.references[label] === "undefined") state.env.references[label] = {
		title,
		href
	};
	const token = state.push("reference_definition", "", 0);
	token.map = [startLine, nextLine];
	token.hidden = true;
	const meta = Object.create(null);
	meta.label = label;
	token.meta = meta;
	state.line = nextLine;
	return true;
}
var html_blocks_default = [
	"address",
	"article",
	"aside",
	"base",
	"basefont",
	"blockquote",
	"body",
	"caption",
	"center",
	"col",
	"colgroup",
	"dd",
	"details",
	"dialog",
	"dir",
	"div",
	"dl",
	"dt",
	"fieldset",
	"figcaption",
	"figure",
	"footer",
	"form",
	"frame",
	"frameset",
	"h1",
	"h2",
	"h3",
	"h4",
	"h5",
	"h6",
	"head",
	"header",
	"hr",
	"html",
	"iframe",
	"legend",
	"li",
	"link",
	"main",
	"menu",
	"menuitem",
	"nav",
	"noframes",
	"ol",
	"optgroup",
	"option",
	"p",
	"param",
	"search",
	"section",
	"summary",
	"table",
	"tbody",
	"td",
	"tfoot",
	"th",
	"thead",
	"title",
	"tr",
	"track",
	"ul"
];
var open_tag = `<[A-Za-z][A-Za-z0-9\\-]*(?:\\s+[a-zA-Z_:][a-zA-Z0-9:._-]*(?:\\s*=\\s*(?:[^"'=<>\`\\x00-\\x20]+|'[^']*'|"[^"]*"))?)*\\s*\\/?>`;
var close_tag = "<\\/[A-Za-z][A-Za-z0-9\\-]*\\s*>";
var HTML_TAG_RE = new RegExp(`^(?:${open_tag}|${close_tag}|<!---?>|<!--(?:[^-]|-[^-]|--[^>])*-->|<[?][\\s\\S]*?[?]>|<![A-Za-z][^>]*>|<!\\[CDATA\\[[\\s\\S]*?\\]\\]>)`);
var HTML_OPEN_CLOSE_TAG_RE = new RegExp(`^(?:${open_tag}|${close_tag})`);
var HTML_SEQUENCES = [
	[
		/^<(script|pre|style|textarea)(?=(\s|>|$))/i,
		/<\/(script|pre|style|textarea)>/i,
		true
	],
	[
		/^<!--/,
		/-->/,
		true
	],
	[
		/^<\?/,
		/\?>/,
		true
	],
	[
		/^<![A-Za-z]/,
		/>/,
		true
	],
	[
		/^<!\[CDATA\[/,
		/\]\]>/,
		true
	],
	[
		new RegExp(`^</?(${html_blocks_default.join("|")})(?=(\\s|/?>|$))`, "i"),
		/^$/,
		true
	],
	[
		new RegExp(`${HTML_OPEN_CLOSE_TAG_RE.source}\\s*$`),
		/^$/,
		false
	]
];
function html_block(state, startLine, endLine, silent) {
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	let max = state.eMarks[startLine];
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	if (!state.md.options.html) return false;
	if (state.src.charCodeAt(pos) !== 60) return false;
	let lineText = state.src.slice(pos, max);
	let i = 0;
	for (; i < HTML_SEQUENCES.length; i++) if (HTML_SEQUENCES[i][0].test(lineText)) break;
	if (i === HTML_SEQUENCES.length) return false;
	if (silent) return HTML_SEQUENCES[i][2];
	let nextLine = startLine + 1;
	const endsOnBlankLine = HTML_SEQUENCES[i][1].test("");
	if (!HTML_SEQUENCES[i][1].test(lineText)) for (; nextLine < endLine; nextLine++) {
		if (state.sCount[nextLine] < state.blkIndent) {
			if (endsOnBlankLine || !state.isEmpty(nextLine)) break;
		}
		pos = state.bMarks[nextLine] + state.tShift[nextLine];
		max = state.eMarks[nextLine];
		lineText = state.src.slice(pos, max);
		if (HTML_SEQUENCES[i][1].test(lineText)) {
			if (lineText.length !== 0) nextLine++;
			break;
		}
	}
	state.line = nextLine;
	const token = state.push("html_block", "", 0);
	token.map = [startLine, nextLine];
	token.content = state.getLines(startLine, nextLine, state.blkIndent, true);
	return true;
}
function heading$1(state, startLine, endLine, silent) {
	let pos = state.bMarks[startLine] + state.tShift[startLine];
	let max = state.eMarks[startLine];
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	let ch = state.src.charCodeAt(pos);
	if (ch !== 35 || pos >= max) return false;
	let level = 1;
	ch = state.src.charCodeAt(++pos);
	while (ch === 35 && pos < max && level <= 6) {
		level++;
		ch = state.src.charCodeAt(++pos);
	}
	if (level > 6 || pos < max && !isSpace(ch)) return false;
	if (silent) return true;
	max = state.skipSpacesBack(max, pos);
	const tmp = state.skipCharsBack(max, 35, pos);
	if (tmp > pos && isSpace(state.src.charCodeAt(tmp - 1))) max = tmp;
	state.line = startLine + 1;
	const token_o = state.push("heading_open", `h${level}`, 1);
	token_o.markup = "########".slice(0, level);
	token_o.map = [startLine, state.line];
	const token_i = state.push("inline", "", 0);
	token_i.content = asciiTrim(state.src.slice(pos, max));
	token_i.map = [startLine, state.line];
	token_i.children = [];
	const token_c = state.push("heading_close", `h${level}`, -1);
	token_c.markup = "########".slice(0, level);
	return true;
}
function lheading(state, startLine, endLine) {
	const terminatorRules = state.md.block.ruler.getRules("paragraph");
	if (state.sCount[startLine] - state.blkIndent >= 4) return false;
	const oldParentType = state.parentType;
	state.parentType = "paragraph";
	let level = 0;
	let marker;
	let nextLine = startLine + 1;
	for (; nextLine < endLine && !state.isEmpty(nextLine); nextLine++) {
		if (state.sCount[nextLine] - state.blkIndent > 3) continue;
		if (state.sCount[nextLine] >= state.blkIndent) {
			let pos = state.bMarks[nextLine] + state.tShift[nextLine];
			const max = state.eMarks[nextLine];
			if (pos < max) {
				marker = state.src.charCodeAt(pos);
				if (marker === 45 || marker === 61) {
					pos = state.skipChars(pos, marker);
					pos = state.skipSpaces(pos);
					if (pos >= max) {
						level = marker === 61 ? 1 : 2;
						break;
					}
				}
			}
		}
		if (state.sCount[nextLine] < 0) continue;
		let terminate = false;
		for (let i = 0, l = terminatorRules.length; i < l; i++) if (terminatorRules[i](state, nextLine, endLine, true)) {
			terminate = true;
			break;
		}
		if (terminate) break;
	}
	if (!level) {
		state.parentType = oldParentType;
		return false;
	}
	const content = asciiTrim(state.getLines(startLine, nextLine, state.blkIndent, false));
	state.line = nextLine + 1;
	const token_o = state.push("heading_open", `h${level}`, 1);
	token_o.markup = String.fromCharCode(marker);
	token_o.map = [startLine, state.line];
	const token_i = state.push("inline", "", 0);
	token_i.content = content;
	token_i.map = [startLine, state.line - 1];
	token_i.children = [];
	const token_c = state.push("heading_close", `h${level}`, -1);
	token_c.markup = String.fromCharCode(marker);
	state.parentType = oldParentType;
	return true;
}
function paragraph(state, startLine, endLine) {
	const terminatorRules = state.md.block.ruler.getRules("paragraph");
	const oldParentType = state.parentType;
	let nextLine = startLine + 1;
	state.parentType = "paragraph";
	for (; nextLine < endLine && !state.isEmpty(nextLine); nextLine++) {
		if (state.sCount[nextLine] - state.blkIndent > 3) continue;
		if (state.sCount[nextLine] < 0) continue;
		let terminate = false;
		for (let i = 0, l = terminatorRules.length; i < l; i++) if (terminatorRules[i](state, nextLine, endLine, true)) {
			terminate = true;
			break;
		}
		if (terminate) break;
	}
	const content = asciiTrim(state.getLines(startLine, nextLine, state.blkIndent, false));
	state.line = nextLine;
	const token_o = state.push("paragraph_open", "p", 1);
	token_o.map = [startLine, state.line];
	const token_i = state.push("inline", "", 0);
	token_i.content = content;
	token_i.map = [startLine, state.line];
	token_i.children = [];
	state.push("paragraph_close", "p", -1);
	state.parentType = oldParentType;
	return true;
}
var _rules$1 = [
	[
		"table",
		table,
		["paragraph", "reference"]
	],
	["code", code],
	[
		"fence",
		fence,
		[
			"paragraph",
			"reference",
			"blockquote",
			"list"
		]
	],
	[
		"blockquote",
		blockquote,
		[
			"paragraph",
			"reference",
			"blockquote",
			"list"
		]
	],
	[
		"hr",
		hr,
		[
			"paragraph",
			"reference",
			"blockquote",
			"list"
		]
	],
	[
		"list",
		list,
		[
			"paragraph",
			"reference",
			"blockquote"
		]
	],
	["reference", reference],
	[
		"html_block",
		html_block,
		[
			"paragraph",
			"reference",
			"blockquote"
		]
	],
	[
		"heading",
		heading$1,
		[
			"paragraph",
			"reference",
			"blockquote"
		]
	],
	["lheading", lheading],
	["paragraph", paragraph]
];
/**
* Block-level tokenizer.
*/
var ParserBlock = class {
	constructor() {
		_defineProperty(
			this,
			/**
			* {@link Ruler} instance. Keep configuration of block rules.
			*/
			"ruler",
			new Ruler()
		);
		_defineProperty(this, "State", StateBlock);
		for (let i = 0; i < _rules$1.length; i++) this.ruler.push(_rules$1[i][0], _rules$1[i][1], { alt: (_rules$1[i][2] || []).slice() });
	}
	tokenize(state, startLine, endLine) {
		const rules = this.ruler.getRules("");
		const len = rules.length;
		const maxNesting = state.md.options.maxNesting;
		let line = startLine;
		let hasEmptyLines = false;
		while (line < endLine) {
			state.line = line = state.skipEmptyLines(line);
			if (line >= endLine) break;
			if (state.sCount[line] < state.blkIndent) break;
			if (state.level >= maxNesting) {
				state.line = endLine;
				break;
			}
			const prevLine = state.line;
			let ok = false;
			for (let i = 0; i < len; i++) {
				ok = rules[i](state, line, endLine, false);
				if (ok) {
					if (prevLine >= state.line) throw new Error("block rule didn't increment state.line");
					break;
				}
			}
			if (!ok) throw new Error("none of the block rules matched");
			state.tight = !hasEmptyLines;
			if (state.isEmpty(state.line - 1)) hasEmptyLines = true;
			line = state.line;
			if (line < endLine && state.isEmpty(line)) {
				hasEmptyLines = true;
				line++;
				state.line = line;
			}
		}
	}
	/**
	* Process input string and push block tokens into `outTokens`
	*/
	parse(src, md, env, outTokens) {
		if (!src) return;
		const state = new this.State(src, md, env, outTokens);
		this.tokenize(state, state.line, state.lineMax);
	}
};
/** Mutable state passed to inline rules while tokenizing inline content. */
var StateInline = class {
	constructor(src, md, env, outTokens) {
		_defineProperty(this, "pos", 0);
		_defineProperty(this, "level", 0);
		_defineProperty(this, "pending", "");
		_defineProperty(this, "pendingLevel", 0);
		_defineProperty(this, "cache", {});
		_defineProperty(this, "backticks", {});
		_defineProperty(this, "backticksScanned", false);
		_defineProperty(this, "linkLevel", 0);
		_defineProperty(this, "delimiters", []);
		_defineProperty(this, "_prev_delimiters", []);
		_defineProperty(this, "Token", Token);
		this.src = src;
		this.env = env;
		this.md = md;
		this.tokens = outTokens;
		this.tokens_meta = Array(outTokens.length);
		this.posMax = this.src.length;
	}
	pushPending() {
		const token = new Token("text", "", 0);
		token.content = this.pending;
		token.level = this.pendingLevel;
		this.tokens.push(token);
		this.pending = "";
		return token;
	}
	push(type, tag, nesting) {
		if (this.pending) this.pushPending();
		const token = new Token(type, tag, nesting);
		let token_meta = void 0;
		if (nesting < 0) {
			this.level--;
			this.delimiters = this._prev_delimiters.pop();
		}
		token.level = this.level;
		if (nesting > 0) {
			this.level++;
			this._prev_delimiters.push(this.delimiters);
			this.delimiters = [];
			token_meta = { delimiters: this.delimiters };
		}
		this.pendingLevel = this.level;
		this.tokens.push(token);
		this.tokens_meta.push(token_meta);
		return token;
	}
	scanDelims(start, canSplitWord) {
		const max = this.posMax;
		const marker = this.src.charCodeAt(start);
		let lastChar;
		if (start === 0) lastChar = 32;
		else if (start === 1) {
			lastChar = this.src.charCodeAt(0);
			if ((lastChar & 63488) === 55296) lastChar = 65533;
		} else {
			lastChar = this.src.charCodeAt(start - 1);
			if ((lastChar & 64512) === 56320) {
				const highSurr = this.src.charCodeAt(start - 2);
				lastChar = (highSurr & 64512) === 55296 ? 65536 + (highSurr - 55296 << 10) + (lastChar - 56320) : 65533;
			} else if ((lastChar & 64512) === 55296) lastChar = 65533;
		}
		let pos = start;
		while (pos < max && this.src.charCodeAt(pos) === marker) pos++;
		const count = pos - start;
		let nextChar = pos < max ? this.src.charCodeAt(pos) : 32;
		if ((nextChar & 64512) === 55296) {
			const lowSurr = this.src.charCodeAt(pos + 1);
			nextChar = (lowSurr & 64512) === 56320 ? 65536 + (nextChar - 55296 << 10) + (lowSurr - 56320) : 65533;
		} else if ((nextChar & 64512) === 56320) nextChar = 65533;
		const isLastPunctChar = isMdAsciiPunct(lastChar) || isPunctCharCode(lastChar);
		const isNextPunctChar = isMdAsciiPunct(nextChar) || isPunctCharCode(nextChar);
		const isLastWhiteSpace = isWhiteSpace(lastChar);
		const isNextWhiteSpace = isWhiteSpace(nextChar);
		const left_flanking = !isNextWhiteSpace && (!isNextPunctChar || isLastWhiteSpace || isLastPunctChar);
		const right_flanking = !isLastWhiteSpace && (!isLastPunctChar || isNextWhiteSpace || isNextPunctChar);
		return {
			can_open: left_flanking && (canSplitWord || !right_flanking || isLastPunctChar),
			can_close: right_flanking && (canSplitWord || !left_flanking || isNextPunctChar),
			length: count
		};
	}
};
function isTerminatorChar(ch) {
	switch (ch) {
		case 10:
		case 33:
		case 35:
		case 36:
		case 37:
		case 38:
		case 42:
		case 43:
		case 45:
		case 58:
		case 60:
		case 61:
		case 62:
		case 64:
		case 91:
		case 92:
		case 93:
		case 94:
		case 95:
		case 96:
		case 123:
		case 125:
		case 126: return true;
		default: return false;
	}
}
function text(state, silent) {
	let pos = state.pos;
	while (pos < state.posMax && !isTerminatorChar(state.src.charCodeAt(pos))) pos++;
	if (pos === state.pos) return false;
	if (!silent) state.pending += state.src.slice(state.pos, pos);
	state.pos = pos;
	return true;
}
function isAsciiAlpha(code) {
	return code >= 65 && code <= 90 || code >= 97 && code <= 122;
}
function isSchemeChar(code) {
	return code >= 65 && code <= 90 || code >= 97 && code <= 122 || code >= 48 && code <= 57 || code === 43 || code === 45 || code === 46;
}
function linkify(state, silent) {
	if (!state.md.options.linkify) return false;
	if (state.linkLevel > 0) return false;
	const pos = state.pos;
	const max = state.posMax;
	if (pos + 3 > max) return false;
	if (state.src.charCodeAt(pos) !== 58) return false;
	if (state.src.charCodeAt(pos + 1) !== 47) return false;
	if (state.src.charCodeAt(pos + 2) !== 47) return false;
	const protoMin = pos - Math.min(10, state.pending.length, pos);
	let protoStart = pos;
	while (protoStart > protoMin && isSchemeChar(state.src.charCodeAt(protoStart - 1))) protoStart--;
	if (protoStart === pos || !isAsciiAlpha(state.src.charCodeAt(protoStart))) return false;
	const protoLength = pos - protoStart;
	const link = state.md.linkify.matchAtStart(state.src.slice(protoStart));
	if (!link) return false;
	let url = link.url;
	if (url.length <= protoLength) return false;
	let urlEnd = url.length;
	while (urlEnd > 0 && url.charCodeAt(urlEnd - 1) === 42) urlEnd--;
	if (urlEnd !== url.length) url = url.slice(0, urlEnd);
	const fullUrl = state.md.normalizeLink(url);
	if (!state.md.validateLink(fullUrl)) return false;
	if (!silent) {
		state.pending = state.pending.slice(0, -protoLength);
		const token_o = state.push("link_open", "a", 1);
		token_o.attrs = [["href", fullUrl]];
		token_o.markup = "linkify";
		token_o.info = "auto";
		const token_t = state.push("text", "", 0);
		token_t.content = state.md.normalizeLinkText(url);
		const token_c = state.push("link_close", "a", -1);
		token_c.markup = "linkify";
		token_c.info = "auto";
	}
	state.pos += url.length - protoLength;
	return true;
}
function newline(state, silent) {
	let pos = state.pos;
	if (state.src.charCodeAt(pos) !== 10) return false;
	const pmax = state.pending.length - 1;
	const max = state.posMax;
	if (!silent) if (pmax >= 0 && state.pending.charCodeAt(pmax) === 32) if (pmax >= 1 && state.pending.charCodeAt(pmax - 1) === 32) {
		let ws = pmax - 1;
		while (ws >= 1 && state.pending.charCodeAt(ws - 1) === 32) ws--;
		state.pending = state.pending.slice(0, ws);
		state.push("hardbreak", "br", 0);
	} else {
		state.pending = state.pending.slice(0, -1);
		state.push("softbreak", "br", 0);
	}
	else state.push("softbreak", "br", 0);
	pos++;
	while (pos < max && isSpace(state.src.charCodeAt(pos))) pos++;
	state.pos = pos;
	return true;
}
var ESCAPED = [];
for (let i = 0; i < 256; i++) ESCAPED.push(0);
"\\!\"#$%&'()*+,./:;<=>?@[]^_`{|}~-".split("").forEach(function(ch) {
	ESCAPED[ch.charCodeAt(0)] = 1;
});
function escape(state, silent) {
	let pos = state.pos;
	const max = state.posMax;
	if (state.src.charCodeAt(pos) !== 92) return false;
	pos++;
	if (pos >= max) return false;
	let ch1 = state.src.charCodeAt(pos);
	if (ch1 === 10) {
		if (!silent) state.push("hardbreak", "br", 0);
		pos++;
		while (pos < max) {
			ch1 = state.src.charCodeAt(pos);
			if (!isSpace(ch1)) break;
			pos++;
		}
		state.pos = pos;
		return true;
	}
	if (ch1 === 32) {
		if (!silent) {
			const token = state.push("text_special", "", 0);
			token.content = "\\";
			token.markup = "\\";
			token.info = "escape";
		}
		state.pos = pos;
		return true;
	}
	let escapedStr = state.src[pos];
	if (ch1 >= 55296 && ch1 <= 56319 && pos + 1 < max) {
		const ch2 = state.src.charCodeAt(pos + 1);
		if (ch2 >= 56320 && ch2 <= 57343) {
			escapedStr += state.src[pos + 1];
			pos++;
		}
	}
	const origStr = "\\" + escapedStr;
	if (!silent) {
		const token = state.push("text_special", "", 0);
		if (ch1 < 256 && ESCAPED[ch1] !== 0) token.content = escapedStr;
		else token.content = origStr;
		token.markup = origStr;
		token.info = "escape";
	}
	state.pos = pos + 1;
	return true;
}
function buildLastRuns(src) {
	const lastRuns = {};
	let pos = 0;
	while ((pos = src.indexOf("`", pos)) !== -1) {
		const start = pos;
		while (src.charCodeAt(++pos) === 96);
		lastRuns[pos - start] = start;
	}
	return lastRuns;
}
function backtick(state, silent) {
	var _state$backticks$open;
	const start = state.pos;
	if (state.src.charCodeAt(start) !== 96) return false;
	const max = state.posMax;
	let pos = start + 1;
	while (pos < max && state.src.charCodeAt(pos) === 96) pos++;
	const marker = state.src.slice(start, pos);
	const openerLength = marker.length;
	if (!state.backticksScanned) {
		state.backticks = buildLastRuns(state.src);
		state.backticksScanned = true;
	}
	if (((_state$backticks$open = state.backticks[openerLength]) !== null && _state$backticks$open !== void 0 ? _state$backticks$open : -1) >= pos) {
		let matchEnd = pos;
		let matchStart;
		while ((matchStart = state.src.indexOf("`", matchEnd)) !== -1 && matchStart < max) {
			matchEnd = matchStart + 1;
			while (state.src.charCodeAt(matchEnd) === 96) matchEnd++;
			if (matchEnd > max) break;
			if (matchEnd - matchStart === openerLength) {
				if (!silent) {
					const token = state.push("code_inline", "code", 0);
					token.markup = marker;
					let content = state.src.slice(pos, matchStart).replace(/\n/g, " ");
					if (content.startsWith(" ") && content.endsWith(" ") && /[^ ]/.test(content)) content = content.slice(1, -1);
					token.content = content;
				}
				state.pos = matchEnd;
				return true;
			}
		}
	}
	if (!silent) state.pending += marker;
	state.pos = pos;
	return true;
}
function strikethrough_tokenize(state, silent) {
	const start = state.pos;
	const marker = state.src.charCodeAt(start);
	if (silent) return false;
	if (marker !== 126) return false;
	const scanned = state.scanDelims(state.pos, true);
	let len = scanned.length;
	const ch = String.fromCharCode(marker);
	if (len < 2) return false;
	let token;
	if (len % 2) {
		token = state.push("text", "", 0);
		token.content = ch;
		len--;
	}
	for (let i = 0; i < len; i += 2) {
		token = state.push("text", "", 0);
		token.content = ch + ch;
		state.delimiters.push({
			marker,
			length: 0,
			token: state.tokens.length - 1,
			end: -1,
			open: scanned.can_open,
			close: scanned.can_close
		});
	}
	state.pos += scanned.length;
	return true;
}
function postProcess$1(state, delimiters) {
	let token;
	const loneMarkers = [];
	const max = delimiters.length;
	for (let i = 0; i < max; i++) {
		const startDelim = delimiters[i];
		if (startDelim.marker !== 126) continue;
		if (startDelim.end === -1) continue;
		const endDelim = delimiters[startDelim.end];
		token = state.tokens[startDelim.token];
		token.type = "s_open";
		token.tag = "s";
		token.nesting = 1;
		token.markup = "~~";
		token.content = "";
		token = state.tokens[endDelim.token];
		token.type = "s_close";
		token.tag = "s";
		token.nesting = -1;
		token.markup = "~~";
		token.content = "";
		if (state.tokens[endDelim.token - 1].type === "text" && state.tokens[endDelim.token - 1].content === "~") loneMarkers.push(endDelim.token - 1);
	}
	while (loneMarkers.length) {
		const i = loneMarkers.pop();
		let j = i + 1;
		while (j < state.tokens.length && state.tokens[j].type === "s_close") j++;
		j--;
		if (i !== j) {
			token = state.tokens[j];
			state.tokens[j] = state.tokens[i];
			state.tokens[i] = token;
		}
	}
}
function strikethrough_postProcess(state) {
	const tokens_meta = state.tokens_meta;
	const max = state.tokens_meta.length;
	postProcess$1(state, state.delimiters);
	for (let curr = 0; curr < max; curr++) {
		var _tokens_meta$curr;
		const delimiters = (_tokens_meta$curr = tokens_meta[curr]) === null || _tokens_meta$curr === void 0 ? void 0 : _tokens_meta$curr.delimiters;
		if (delimiters) postProcess$1(state, delimiters);
	}
}
var strikethrough_default = {
	tokenize: strikethrough_tokenize,
	postProcess: strikethrough_postProcess
};
function emphasis_tokenize(state, silent) {
	const start = state.pos;
	const marker = state.src.charCodeAt(start);
	if (silent) return false;
	if (marker !== 95 && marker !== 42) return false;
	const scanned = state.scanDelims(state.pos, marker === 42);
	for (let i = 0; i < scanned.length; i++) {
		const token = state.push("text", "", 0);
		token.content = String.fromCharCode(marker);
		state.delimiters.push({
			marker,
			length: scanned.length,
			token: state.tokens.length - 1,
			end: -1,
			open: scanned.can_open,
			close: scanned.can_close
		});
	}
	state.pos += scanned.length;
	return true;
}
function postProcess(state, delimiters) {
	const max = delimiters.length;
	for (let i = max - 1; i >= 0; i--) {
		const startDelim = delimiters[i];
		if (startDelim.marker !== 95 && startDelim.marker !== 42) continue;
		if (startDelim.end === -1) continue;
		const endDelim = delimiters[startDelim.end];
		const isStrong = i > 0 && delimiters[i - 1].end === startDelim.end + 1 && delimiters[i - 1].marker === startDelim.marker && delimiters[i - 1].token === startDelim.token - 1 && delimiters[startDelim.end + 1].token === endDelim.token + 1;
		const ch = String.fromCharCode(startDelim.marker);
		const token_o = state.tokens[startDelim.token];
		token_o.type = isStrong ? "strong_open" : "em_open";
		token_o.tag = isStrong ? "strong" : "em";
		token_o.nesting = 1;
		token_o.markup = isStrong ? ch + ch : ch;
		token_o.content = "";
		const token_c = state.tokens[endDelim.token];
		token_c.type = isStrong ? "strong_close" : "em_close";
		token_c.tag = isStrong ? "strong" : "em";
		token_c.nesting = -1;
		token_c.markup = isStrong ? ch + ch : ch;
		token_c.content = "";
		if (isStrong) {
			state.tokens[delimiters[i - 1].token].content = "";
			state.tokens[delimiters[startDelim.end + 1].token].content = "";
			i--;
		}
	}
}
function emphasis_post_process(state) {
	const tokens_meta = state.tokens_meta;
	const max = state.tokens_meta.length;
	postProcess(state, state.delimiters);
	for (let curr = 0; curr < max; curr++) {
		var _tokens_meta$curr;
		const delimiters = (_tokens_meta$curr = tokens_meta[curr]) === null || _tokens_meta$curr === void 0 ? void 0 : _tokens_meta$curr.delimiters;
		if (delimiters) postProcess(state, delimiters);
	}
}
var emphasis_default = {
	tokenize: emphasis_tokenize,
	postProcess: emphasis_post_process
};
function link(state, silent) {
	let code, label, res, ref;
	let href = "";
	let title = "";
	let start = state.pos;
	let parseReference = true;
	if (state.src.charCodeAt(state.pos) !== 91) return false;
	const oldPos = state.pos;
	const max = state.posMax;
	const labelStart = state.pos + 1;
	const labelEnd = state.md.helpers.parseLinkLabel(state, state.pos, true);
	if (labelEnd < 0) return false;
	let pos = labelEnd + 1;
	if (pos < max && state.src.charCodeAt(pos) === 40) {
		parseReference = false;
		pos++;
		for (; pos < max; pos++) {
			code = state.src.charCodeAt(pos);
			if (!isSpace(code) && code !== 10) break;
		}
		if (pos >= max) return false;
		start = pos;
		res = state.md.helpers.parseLinkDestination(state.src, pos, state.posMax);
		if (res.ok) {
			href = state.md.normalizeLink(res.str);
			if (state.md.validateLink(href)) pos = res.pos;
			else href = "";
			start = pos;
			for (; pos < max; pos++) {
				code = state.src.charCodeAt(pos);
				if (!isSpace(code) && code !== 10) break;
			}
			res = state.md.helpers.parseLinkTitle(state.src, pos, state.posMax);
			if (pos < max && start !== pos && res.ok) {
				title = res.str;
				pos = res.pos;
				for (; pos < max; pos++) {
					code = state.src.charCodeAt(pos);
					if (!isSpace(code) && code !== 10) break;
				}
			}
		}
		if (pos >= max || state.src.charCodeAt(pos) !== 41) parseReference = true;
		pos++;
	}
	if (parseReference) {
		if (typeof state.env.references === "undefined") return false;
		if (pos < max && state.src.charCodeAt(pos) === 91) {
			start = pos + 1;
			pos = state.md.helpers.parseLinkLabel(state, pos);
			if (pos >= 0) label = state.src.slice(start, pos++);
			else pos = labelEnd + 1;
		} else pos = labelEnd + 1;
		if (!label) label = state.src.slice(labelStart, labelEnd);
		label = normalizeReference(label);
		ref = state.env.references[label];
		if (!ref) {
			state.pos = oldPos;
			return false;
		}
		href = ref.href;
		title = ref.title;
	}
	if (!silent) {
		state.pos = labelStart;
		state.posMax = labelEnd;
		const token_o = state.push("link_open", "a", 1);
		const attrs = [["href", href]];
		token_o.attrs = attrs;
		if (title) attrs.push(["title", title]);
		if (label) {
			const meta = Object.create(null);
			meta.label = label;
			token_o.meta = meta;
		}
		state.linkLevel++;
		state.md.inline.tokenize(state);
		state.linkLevel--;
		state.push("link_close", "a", -1);
	}
	state.pos = pos;
	state.posMax = max;
	return true;
}
function image(state, silent) {
	let code, content, label, pos, ref, res, title, start;
	let href = "";
	const oldPos = state.pos;
	const max = state.posMax;
	if (state.src.charCodeAt(state.pos) !== 33) return false;
	if (state.src.charCodeAt(state.pos + 1) !== 91) return false;
	const labelStart = state.pos + 2;
	const labelEnd = state.md.helpers.parseLinkLabel(state, state.pos + 1, false);
	if (labelEnd < 0) return false;
	pos = labelEnd + 1;
	if (pos < max && state.src.charCodeAt(pos) === 40) {
		pos++;
		for (; pos < max; pos++) {
			code = state.src.charCodeAt(pos);
			if (!isSpace(code) && code !== 10) break;
		}
		if (pos >= max) return false;
		start = pos;
		res = state.md.helpers.parseLinkDestination(state.src, pos, state.posMax);
		if (res.ok) {
			href = state.md.normalizeLink(res.str);
			if (state.md.validateLink(href)) pos = res.pos;
			else href = "";
		}
		start = pos;
		for (; pos < max; pos++) {
			code = state.src.charCodeAt(pos);
			if (!isSpace(code) && code !== 10) break;
		}
		res = state.md.helpers.parseLinkTitle(state.src, pos, state.posMax);
		if (pos < max && start !== pos && res.ok) {
			title = res.str;
			pos = res.pos;
			for (; pos < max; pos++) {
				code = state.src.charCodeAt(pos);
				if (!isSpace(code) && code !== 10) break;
			}
		} else title = "";
		if (pos >= max || state.src.charCodeAt(pos) !== 41) {
			state.pos = oldPos;
			return false;
		}
		pos++;
	} else {
		if (typeof state.env.references === "undefined") return false;
		if (pos < max && state.src.charCodeAt(pos) === 91) {
			start = pos + 1;
			pos = state.md.helpers.parseLinkLabel(state, pos);
			if (pos >= 0) label = state.src.slice(start, pos++);
			else pos = labelEnd + 1;
		} else pos = labelEnd + 1;
		if (!label) label = state.src.slice(labelStart, labelEnd);
		label = normalizeReference(label);
		ref = state.env.references[label];
		if (!ref) {
			state.pos = oldPos;
			return false;
		}
		href = ref.href;
		title = ref.title;
	}
	if (!silent) {
		content = state.src.slice(labelStart, labelEnd);
		const tokens = [];
		state.md.inline.parse(content, state.md, state.env, tokens);
		const token = state.push("image", "img", 0);
		const attrs = [["src", href], ["alt", ""]];
		token.attrs = attrs;
		token.children = tokens;
		token.content = content;
		if (title) attrs.push(["title", title]);
		if (label) {
			const meta = Object.create(null);
			meta.label = label;
			token.meta = meta;
		}
	}
	state.pos = pos;
	state.posMax = max;
	return true;
}
var EMAIL_RE = /^([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)$/;
var AUTOLINK_RE = /^([a-zA-Z][a-zA-Z0-9+.-]{1,31}):([^<>\x00-\x20]*)$/;
function autolink(state, silent) {
	let pos = state.pos;
	if (state.src.charCodeAt(pos) !== 60) return false;
	const start = state.pos;
	const max = state.posMax;
	for (;;) {
		if (++pos >= max) return false;
		const ch = state.src.charCodeAt(pos);
		if (ch === 60) return false;
		if (ch === 62) break;
	}
	const url = state.src.slice(start + 1, pos);
	if (AUTOLINK_RE.test(url)) {
		const fullUrl = state.md.normalizeLink(url);
		if (!state.md.validateLink(fullUrl)) return false;
		if (!silent) {
			const token_o = state.push("link_open", "a", 1);
			token_o.attrs = [["href", fullUrl]];
			token_o.markup = "autolink";
			token_o.info = "auto";
			const token_t = state.push("text", "", 0);
			token_t.content = state.md.normalizeLinkText(url);
			const token_c = state.push("link_close", "a", -1);
			token_c.markup = "autolink";
			token_c.info = "auto";
		}
		state.pos += url.length + 2;
		return true;
	}
	if (EMAIL_RE.test(url)) {
		const fullUrl = state.md.normalizeLink(`mailto:${url}`);
		if (!state.md.validateLink(fullUrl)) return false;
		if (!silent) {
			const token_o = state.push("link_open", "a", 1);
			token_o.attrs = [["href", fullUrl]];
			token_o.markup = "autolink";
			token_o.info = "auto";
			const token_t = state.push("text", "", 0);
			token_t.content = state.md.normalizeLinkText(url);
			const token_c = state.push("link_close", "a", -1);
			token_c.markup = "autolink";
			token_c.info = "auto";
		}
		state.pos += url.length + 2;
		return true;
	}
	return false;
}
function isLinkOpen(str) {
	return /^<a[>\s]/i.test(str);
}
function isLinkClose(str) {
	return /^<\/a\s*>/i.test(str);
}
function isLetter(ch) {
	const lc = ch | 32;
	return lc >= 97 && lc <= 122;
}
function html_inline(state, silent) {
	if (!state.md.options.html) return false;
	const max = state.posMax;
	const pos = state.pos;
	if (state.src.charCodeAt(pos) !== 60 || pos + 2 >= max) return false;
	const ch = state.src.charCodeAt(pos + 1);
	if (ch !== 33 && ch !== 63 && ch !== 47 && !isLetter(ch)) return false;
	const match = state.src.slice(pos).match(HTML_TAG_RE);
	if (!match) return false;
	if (!silent) {
		const token = state.push("html_inline", "", 0);
		token.content = match[0];
		if (isLinkOpen(token.content)) state.linkLevel++;
		if (isLinkClose(token.content)) state.linkLevel--;
	}
	state.pos += match[0].length;
	return true;
}
var DIGITAL_RE = /^&#((?:x[a-f0-9]{1,6}|[0-9]{1,7}));/i;
var NAMED_RE = /^&([a-z][a-z0-9]{1,31});/i;
function entity(state, silent) {
	const pos = state.pos;
	const max = state.posMax;
	if (state.src.charCodeAt(pos) !== 38) return false;
	if (pos + 1 >= max) return false;
	if (state.src.charCodeAt(pos + 1) === 35) {
		const match = state.src.slice(pos).match(DIGITAL_RE);
		if (match) {
			if (!silent) {
				const code = match[1][0].toLowerCase() === "x" ? parseInt(match[1].slice(1), 16) : parseInt(match[1], 10);
				const token = state.push("text_special", "", 0);
				token.content = isValidEntityCode(code) ? fromCodePoint(code) : fromCodePoint(65533);
				token.markup = match[0];
				token.info = "entity";
			}
			state.pos += match[0].length;
			return true;
		}
	} else {
		const match = state.src.slice(pos).match(NAMED_RE);
		if (match) {
			const decoded = decodeHTMLStrict(match[0]);
			if (decoded !== match[0]) {
				if (!silent) {
					const token = state.push("text_special", "", 0);
					token.content = decoded;
					token.markup = match[0];
					token.info = "entity";
				}
				state.pos += match[0].length;
				return true;
			}
		}
	}
	return false;
}
function processDelimiters(delimiters) {
	const openersBottom = {};
	const max = delimiters.length;
	if (!max) return;
	let headerIdx = 0;
	let lastTokenIdx = -2;
	const jumps = [];
	for (let closerIdx = 0; closerIdx < max; closerIdx++) {
		const closer = delimiters[closerIdx];
		jumps.push(0);
		if (delimiters[headerIdx].marker !== closer.marker || lastTokenIdx !== closer.token - 1) headerIdx = closerIdx;
		lastTokenIdx = closer.token;
		closer.length = closer.length || 0;
		if (!closer.close) continue;
		if (!openersBottom.hasOwnProperty(closer.marker)) openersBottom[closer.marker] = [
			-1,
			-1,
			-1,
			-1,
			-1,
			-1
		];
		const minOpenerIdx = openersBottom[closer.marker][(closer.open ? 3 : 0) + closer.length % 3];
		let openerIdx = headerIdx - jumps[headerIdx] - 1;
		let newMinOpenerIdx = openerIdx;
		for (; openerIdx > minOpenerIdx; openerIdx -= jumps[openerIdx] + 1) {
			const opener = delimiters[openerIdx];
			if (opener.marker !== closer.marker) continue;
			if (opener.open && opener.end < 0) {
				let isOddMatch = false;
				if (opener.close || closer.open) {
					if ((opener.length + closer.length) % 3 === 0) {
						if (opener.length % 3 !== 0 || closer.length % 3 !== 0) isOddMatch = true;
					}
				}
				if (!isOddMatch) {
					const lastJump = openerIdx > 0 && !delimiters[openerIdx - 1].open ? jumps[openerIdx - 1] + 1 : 0;
					jumps[closerIdx] = closerIdx - openerIdx + lastJump;
					jumps[openerIdx] = lastJump;
					closer.open = false;
					opener.end = closerIdx;
					opener.close = false;
					newMinOpenerIdx = -1;
					lastTokenIdx = -2;
					break;
				}
			}
		}
		if (newMinOpenerIdx !== -1) openersBottom[closer.marker][(closer.open ? 3 : 0) + (closer.length || 0) % 3] = newMinOpenerIdx;
	}
}
function link_pairs(state) {
	const tokens_meta = state.tokens_meta;
	const max = state.tokens_meta.length;
	processDelimiters(state.delimiters);
	for (let curr = 0; curr < max; curr++) {
		var _tokens_meta$curr;
		const delimiters = (_tokens_meta$curr = tokens_meta[curr]) === null || _tokens_meta$curr === void 0 ? void 0 : _tokens_meta$curr.delimiters;
		if (delimiters) processDelimiters(delimiters);
	}
}
function fragments_join(state) {
	let curr, last;
	let level = 0;
	const tokens = state.tokens;
	const max = state.tokens.length;
	for (curr = last = 0; curr < max; curr++) {
		if (tokens[curr].nesting < 0) level--;
		tokens[curr].level = level;
		if (tokens[curr].nesting > 0) level++;
		if (tokens[curr].type === "text" && curr + 1 < max && tokens[curr + 1].type === "text") tokens[curr + 1].content = tokens[curr].content + tokens[curr + 1].content;
		else {
			if (curr !== last) tokens[last] = tokens[curr];
			last++;
		}
	}
	if (curr !== last) tokens.length = last;
}
var _rules = [
	["text", text],
	["linkify", linkify],
	["newline", newline],
	["escape", escape],
	["backticks", backtick],
	["strikethrough", strikethrough_default.tokenize],
	["emphasis", emphasis_default.tokenize],
	["link", link],
	["image", image],
	["autolink", autolink],
	["html_inline", html_inline],
	["entity", entity]
];
var _rules2 = [
	["balance_pairs", link_pairs],
	["strikethrough", strikethrough_default.postProcess],
	["emphasis", emphasis_default.postProcess],
	["fragments_join", fragments_join]
];
/**
* Tokenizes paragraph content.
*/
var ParserInline = class {
	constructor() {
		_defineProperty(
			this,
			/**
			* {@link Ruler} instance. Keep configuration of inline rules.
			*/
			"ruler",
			new Ruler()
		);
		_defineProperty(
			this,
			/**
			* {@link Ruler} instance. Second ruler used for post-processing
			* (e.g. in emphasis-like rules).
			*/
			"ruler2",
			new Ruler()
		);
		_defineProperty(this, "State", StateInline);
		for (let i = 0; i < _rules.length; i++) this.ruler.push(_rules[i][0], _rules[i][1]);
		for (let i = 0; i < _rules2.length; i++) this.ruler2.push(_rules2[i][0], _rules2[i][1]);
	}
	skipToken(state) {
		const pos = state.pos;
		const rules = this.ruler.getRules("");
		const len = rules.length;
		const maxNesting = state.md.options.maxNesting;
		const cache = state.cache;
		if (typeof cache[pos] !== "undefined") {
			state.pos = cache[pos];
			return;
		}
		let ok = false;
		if (state.level < maxNesting) for (let i = 0; i < len; i++) {
			state.level++;
			ok = rules[i](state, true);
			state.level--;
			if (ok) {
				if (pos >= state.pos) throw new Error("inline rule didn't increment state.pos");
				break;
			}
		}
		else state.pos = state.posMax;
		if (!ok) state.pos++;
		cache[pos] = state.pos;
	}
	tokenize(state) {
		const rules = this.ruler.getRules("");
		const len = rules.length;
		const end = state.posMax;
		const maxNesting = state.md.options.maxNesting;
		while (state.pos < end) {
			const prevPos = state.pos;
			let ok = false;
			if (state.level < maxNesting) for (let i = 0; i < len; i++) {
				ok = rules[i](state, false);
				if (ok) {
					if (prevPos >= state.pos) throw new Error("inline rule didn't increment state.pos");
					break;
				}
			}
			if (ok) {
				if (state.pos >= end) break;
				continue;
			}
			state.pending += state.src[state.pos++];
		}
		if (state.pending) state.pushPending();
	}
	/**
	* Process input string and push inline tokens into `outTokens`
	*/
	parse(str, md, env, outTokens) {
		const state = new this.State(str, md, env, outTokens);
		this.tokenize(state);
		const rules = this.ruler2.getRules("");
		const len = rules.length;
		for (let i = 0; i < len; i++) rules[i](state);
	}
};
var config = {
	default: {
		options: {
			html: false,
			xhtmlOut: false,
			breaks: false,
			langPrefix: "language-",
			linkify: false,
			typographer: false,
			quotes: "“”‘’",
			highlight: null,
			maxNesting: 100
		},
		components: {
			core: {},
			block: {},
			inline: {}
		}
	},
	zero: {
		options: {
			html: false,
			xhtmlOut: false,
			breaks: false,
			langPrefix: "language-",
			linkify: false,
			typographer: false,
			quotes: "“”‘’",
			highlight: null,
			maxNesting: 20
		},
		components: {
			core: { rules: [
				"normalize",
				"block",
				"strip_references",
				"inline",
				"text_join"
			] },
			block: { rules: ["paragraph"] },
			inline: {
				rules: ["text"],
				rules2: ["balance_pairs", "fragments_join"]
			}
		}
	},
	commonmark: {
		options: {
			html: true,
			xhtmlOut: true,
			breaks: false,
			langPrefix: "language-",
			linkify: false,
			typographer: false,
			quotes: "“”‘’",
			highlight: null,
			maxNesting: 20
		},
		components: {
			core: { rules: [
				"normalize",
				"block",
				"strip_references",
				"inline",
				"text_join"
			] },
			block: { rules: [
				"blockquote",
				"code",
				"fence",
				"heading",
				"hr",
				"html_block",
				"lheading",
				"list",
				"reference",
				"paragraph"
			] },
			inline: {
				rules: [
					"autolink",
					"backticks",
					"emphasis",
					"entity",
					"escape",
					"html_inline",
					"image",
					"link",
					"newline",
					"text"
				],
				rules2: [
					"balance_pairs",
					"emphasis",
					"fragments_join"
				]
			}
		}
	}
};
var BAD_PROTO_RE = /^(vbscript|javascript|file|data):/;
var GOOD_DATA_RE = /^data:image\/(gif|png|jpeg|webp);/;
var RECODE_HOSTNAME_FOR = [
	"http:",
	"https:",
	"mailto:"
];
/**
* Parses Markdown into tokens and renders them to HTML.
*
* @category Main
*/
var MarkdownIt = class {
	/**
	* Link validation function. CommonMark allows too much in links. By default
	* we disable `javascript:`, `vbscript:`, `file:` schemas, and almost all `data:...` schemas
	* except some embedded image types.
	*
	* You can change this behaviour:
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	* const md = new MarkdownIt()
	*
	* // enable everything
	* md.validateLink = function () { return true; }
	* ```
	*/
	validateLink(url) {
		const str = url.trim().toLowerCase();
		return BAD_PROTO_RE.test(str) ? GOOD_DATA_RE.test(str) : true;
	}
	/**
	* Function used to encode link url to a machine-readable format,
	* which includes url-encoding, punycode, etc.
	*/
	normalizeLink(url) {
		const parsed = urlParse(url, true);
		if (parsed.hostname) {
			if (!parsed.protocol || RECODE_HOSTNAME_FOR.indexOf(parsed.protocol) >= 0) try {
				parsed.hostname = punycode.toASCII(parsed.hostname);
			} catch (er) {}
		}
		if (parsed.auth) parsed.auth = encode$1(parsed.auth);
		if (parsed.hostname) parsed.hostname = encode$1(parsed.hostname);
		if (parsed.pathname) parsed.pathname = encode$1(parsed.pathname);
		if (parsed.search) parsed.search = encode$1(parsed.search);
		if (parsed.hash) parsed.hash = encode$1(parsed.hash);
		return format(parsed);
	}
	/**
	* Function used to decode link url to a human-readable format`
	*/
	normalizeLinkText(url) {
		const parsed = urlParse(url, true);
		if (parsed.hostname) {
			if (!parsed.protocol || RECODE_HOSTNAME_FOR.indexOf(parsed.protocol) >= 0) try {
				parsed.hostname = punycode.toUnicode(parsed.hostname);
			} catch (er) {}
		}
		return decode$1(format(parsed), decode$1.defaultChars + "%");
	}
	constructor(...args) {
		_defineProperty(
			this,
			/**
			* Instance of {@link ParserInline}. You may need it to add new rules when
			* writing plugins. For simple rules control use {@link MarkdownIt.disable}
			* and {@link MarkdownIt.enable}.
			*/
			"inline",
			new ParserInline()
		);
		_defineProperty(
			this,
			/**
			* Instance of {@link ParserBlock}. You may need it to add new rules when
			* writing plugins. For simple rules control use {@link MarkdownIt.disable}
			* and {@link MarkdownIt.enable}.
			*/
			"block",
			new ParserBlock()
		);
		_defineProperty(
			this,
			/**
			* Instance of {@link ParserCore} chain executor. You may need it to add new
			* rules when writing plugins. For simple rules control use
			* {@link MarkdownIt.disable} and {@link MarkdownIt.enable}.
			*/
			"core",
			new ParserCore()
		);
		_defineProperty(
			this,
			/**
			* Instance of {@link Renderer}. Use it to modify output look. Or to add rendering
			* rules for new token types, generated by plugins.
			*
			* See {@link Renderer} docs and
			* [source code](https://github.com/markdown-it/markdown-it/blob/master/src/renderer.ts).
			*
			* @example
			* ```javascript
			* import MarkdownIt from 'markdown-it'
			* const md = new MarkdownIt()
			*
			* function myToken(tokens, idx, options, env, self) {
			*   //...
			*   return result;
			* };
			*
			* md.renderer.rules['my_token'] = myToken
			* ```
			*/
			"renderer",
			new Renderer()
		);
		_defineProperty(
			this,
			/**
			* [linkify-it](https://github.com/markdown-it/linkify-it) instance.
			* Used by [linkify](https://github.com/markdown-it/markdown-it/blob/master/src/rules_core/linkify.ts)
			* rule.
			*/
			"linkify",
			new LinkifyIt()
		);
		_defineProperty(
			this,
			/**
			* Assorted utility functions, useful to write plugins. See details
			* [here](https://github.com/markdown-it/markdown-it/blob/master/src/common/utils.ts).
			*/
			"utils",
			utils_exports
		);
		_defineProperty(
			this,
			/**
			* Link components parser functions, useful to write plugins. See details
			* [here](https://github.com/markdown-it/markdown-it/blob/master/src/helpers).
			*/
			"helpers",
			Object.assign({}, helpers_exports)
		);
		const [presetNameOrOptions, options] = args;
		if (typeof presetNameOrOptions === "string") {
			this.configure(presetNameOrOptions);
			if (options) this.set(options);
		} else {
			this.configure("default");
			this.set(presetNameOrOptions || {});
		}
	}
	/**
	* Set parser options (in the same format as in constructor). Probably, you
	* will never need it, but you can change options after constructor call.
	*
	* __Note:__ To achieve the best possible performance, don't modify a
	* `markdown-it` instance options on the fly. If you need multiple configurations
	* it's best to create multiple instances and initialize each with separate
	* config.
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	*
	* const md = new MarkdownIt()
	*   .set({ html: true, breaks: true })
	*   .set({ typographer: true })
	* ```
	*/
	set(options) {
		Object.assign(this.options, options);
		return this;
	}
	/**
	* Batch load of all options and compenent settings. This is internal method,
	* and you probably will not need it. But if you will - see available presets
	* and data structure [here](https://github.com/markdown-it/markdown-it/tree/master/src/presets)
	*
	* We strongly recommend to use presets instead of direct config loads. That
	* will give better compatibility with next versions.
	*/
	configure(presets) {
		let p;
		if (typeof presets === "string") {
			const presetName = presets;
			p = config[presetName];
			if (!p) throw new Error(`Wrong 'markdown-it' preset "${presetName}", check name`);
		} else p = presets;
		if (!p) throw new Error("Wrong `markdown-it` preset, can't be empty");
		if (p.options) this.options = { ...p.options };
		const components = p.components;
		if (components) {
			var _components$inline;
			[
				"core",
				"block",
				"inline"
			].forEach((name) => {
				var _components$name;
				const rules = (_components$name = components[name]) === null || _components$name === void 0 ? void 0 : _components$name.rules;
				if (rules) this[name].ruler.enableOnly(rules);
			});
			const rules2 = (_components$inline = components.inline) === null || _components$inline === void 0 ? void 0 : _components$inline.rules2;
			if (rules2) this.inline.ruler2.enableOnly(rules2);
		}
		return this;
	}
	/**
	* Enable list or rules. It will automatically find appropriate components,
	* containing rules with given names. If rule not found, and `ignoreInvalid`
	* not set - throws exception.
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	*
	* const md = new MarkdownIt()
	*   .enable(['sub', 'sup'])
	*   .disable('smartquotes')
	* ```
	*/
	enable(list, ignoreInvalid = false) {
		let result = [];
		if (!Array.isArray(list)) list = [list];
		[
			"core",
			"block",
			"inline"
		].forEach((chain) => {
			result = result.concat(this[chain].ruler.enable(list, true));
		});
		result = result.concat(this.inline.ruler2.enable(list, true));
		const missed = list.filter((name) => result.indexOf(name) < 0);
		if (missed.length && !ignoreInvalid) throw new Error(`MarkdownIt. Failed to enable unknown rule(s): ${missed}`);
		return this;
	}
	/**
	* The same as {@link MarkdownIt.enable}, but turn specified rules off.
	*/
	disable(list, ignoreInvalid = false) {
		let result = [];
		if (!Array.isArray(list)) list = [list];
		[
			"core",
			"block",
			"inline"
		].forEach((chain) => {
			result = result.concat(this[chain].ruler.disable(list, true));
		});
		result = result.concat(this.inline.ruler2.disable(list, true));
		const missed = list.filter((name) => result.indexOf(name) < 0);
		if (missed.length && !ignoreInvalid) throw new Error(`MarkdownIt. Failed to disable unknown rule(s): ${missed}`);
		return this;
	}
	/**
	* Load specified plugin with given params into current parser instance.
	* It's just a sugar to call `plugin(md, params)` with curring.
	*
	* @example
	* ```javascript
	* import MarkdownIt from 'markdown-it'
	* import iterator from 'markdown-it-for-inline'
	*
	* const md = new MarkdownIt()
	*   .use(iterator, 'foo_replace', 'text', function (tokens, idx) {
	*     tokens[idx].content = tokens[idx].content.replace(/foo/g, 'bar')
	*   })
	* ```
	*/
	use(plugin, ...params) {
		plugin.apply(plugin, [this, ...params]);
		return this;
	}
	/**
	* Parse input string and return list of block tokens (special token type
	* "inline" will contain list of inline tokens). You should not call this
	* method directly, until you write custom renderer (for example, to produce
	* AST).
	*
	* `env` is used to pass data between "distributed" rules and return additional
	* metadata like reference info, needed for the renderer. It also can be used to
	* inject data in specific cases. Usually, you will be ok to pass `{}`,
	* and then pass updated object to renderer.
	*/
	parse(src, env) {
		if (typeof src !== "string") throw new Error("Input data should be a String");
		const state = new this.core.State(src, this, env);
		this.core.process(state);
		return state.tokens;
	}
	/**
	* Render markdown string into html. It does all magic for you :).
	*
	* `env` can be used to inject additional metadata (`{}` by default).
	* But you will not need it with high probability. See also comment
	* in {@link MarkdownIt.parse}.
	*/
	render(src, env = {}) {
		return this.renderer.render(this.parse(src, env), this.options, env);
	}
	/**
	* The same as {@link MarkdownIt.parse} but skip all block rules. It returns
	* the block tokens list with the single `inline` element, containing parsed
	* inline tokens in `children` property. Also updates `env` object.
	*/
	parseInline(src, env) {
		const state = new this.core.State(src, this, env);
		state.inlineMode = true;
		this.core.process(state);
		return state.tokens;
	}
	/**
	* Similar to {@link MarkdownIt.render} but for single paragraph content.
	* Result will NOT be wrapped into `<p>` tags.
	*/
	renderInline(src, env = {}) {
		return this.renderer.render(this.parseInline(src, env), this.options, env);
	}
};
_defineProperty(MarkdownIt, "Token", Token);
_defineProperty(MarkdownIt, "Ruler", Ruler);
_defineProperty(MarkdownIt, "Renderer", Renderer);
_defineProperty(MarkdownIt, "ParserCore", ParserCore);
_defineProperty(MarkdownIt, "StateCore", StateCore);
_defineProperty(MarkdownIt, "ParserBlock", ParserBlock);
_defineProperty(MarkdownIt, "StateBlock", StateBlock);
_defineProperty(MarkdownIt, "ParserInline", ParserInline);
_defineProperty(MarkdownIt, "StateInline", StateInline);
/**
* Default package export.
*
* For backward compatibility, the {@link MarkdownIt} class is wrapped so
* legacy code can call it without `new`. New code should instantiate it as a
* regular class with `new`. The compatibility wrapper may be removed in a
* future release.
*
* @category Main
*/
var MarkdownItCallable = callable(MarkdownIt);
//#endregion
//#region src/controls/markdown.js
var markdown = new MarkdownItCallable({
	html: false,
	highlight(source, language) {
		const tokenize = {
			python: pythonTokens,
			py: pythonTokens,
			javascript: javascriptTokens,
			js: javascriptTokens,
			xml: xmlTokens
		}[language];
		return tokenize ? tokenize(source).map((token) => token.role ? "<span class=\"syntax-" + token.role + "\">" + escapeHtml$1(token.text) + "</span>" : escapeHtml$1(token.text)).join("") : escapeHtml$1(source);
	}
});
markdown.validateLink = (href) => /^(https?:\/\/|mailto:|#[\w\p{L}-]+$|[a-z][a-z0-9_.-]*\.(?:en|ru)\.md(?:#[\w\p{L}-]+)?$|(?:\.\/)?media\/[\w.-]+\.(?:png|jpe?g|webp)$)/iu.test(href);
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
	const href = tokens[index].attrGet("href");
	if (/^https?:/i.test(href)) {
		tokens[index].attrSet("target", "_blank");
		tokens[index].attrSet("rel", "noopener noreferrer");
	}
	return self.renderToken(tokens, index, options);
};
var renderImage = markdown.renderer.rules.image;
markdown.renderer.rules.image = (tokens, index, options, env, self) => {
	const token = tokens[index], source = token.attrGet("src");
	if (!/^(?:\.\/)?media\/[\w.-]+\.(?:png|jpe?g|webp)$/i.test(source)) return escapeHtml$1(token.content);
	token.attrSet("src", "/ui/help/" + source.replace(/^\.\//, ""));
	token.attrSet("loading", "lazy");
	return renderImage(tokens, index, options, env, self);
};
markdown.renderer.rules.heading_open = (tokens, index, options, env, self) => {
	const name = tokens[index + 1].content.toLocaleLowerCase().replace(/[^\p{L}\p{N}_ -]/gu, "").trim().replace(/\s+/g, "-");
	env.headings ||= /* @__PURE__ */ new Map();
	const count = env.headings.get(name) || 0;
	env.headings.set(name, count + 1);
	tokens[index].attrSet("id", name + (count ? "-" + count : ""));
	return self.renderToken(tokens, index, options);
};
function renderMarkdown(text) {
	return markdown.render(text);
}
//#endregion
//#region src/controls/MarkdownText.vue
var _hoisted_1$8 = ["innerHTML"];
var _sfc_main$13 = {
	__name: "MarkdownText",
	props: { text: {
		type: String,
		default: ""
	} },
	emits: ["topic"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		function activate(event) {
			const href = event.target.closest("a")?.getAttribute("href");
			const topic = href?.match(/^([a-z][a-z0-9_.-]*)\.(?:en|ru)\.md(?:#.*)?$/i)?.[1];
			if (topic && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && !event.button) {
				event.preventDefault();
				emit("topic", topic);
			}
			if (href?.startsWith("#")) {
				event.preventDefault();
				event.currentTarget.closest("article")?.querySelector("#" + CSS.escape(decodeURIComponent(href.slice(1))))?.scrollIntoView({ block: "start" });
			}
		}
		const html = computed(() => renderMarkdown(props.text));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "markdown-text",
				innerHTML: html.value,
				onClick: activate
			}, null, 8, _hoisted_1$8);
		};
	}
};
//#endregion
//#region src/controls/DocumentPane.vue
var _hoisted_1$7 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_2$6 = {
	key: 1,
	class: "document-notice muted"
};
var _hoisted_3$3 = {
	key: 2,
	class: "document-summary"
};
var _sfc_main$12 = {
	__name: "DocumentPane",
	props: {
		documentKey: String,
		text: String,
		summary: String,
		notice: String,
		error: String,
		scrollOffset: {
			type: Number,
			default: 0
		},
		presented: {
			type: Boolean,
			default: true
		},
		contentInset: {
			type: Number,
			default: spacing.content
		}
	},
	emits: ["link", "scroll"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const documentStyle = Object.fromEntries(Object.entries(controls.document).map(([key, value]) => ["--document-" + key, value + "px"]));
		const props = __props;
		const emit = __emit;
		const viewport = ref(null), article = ref(null);
		let observer, restoredOffset = null;
		async function restore() {
			await nextTick();
			if (!props.presented || !viewport.value?.clientHeight) return;
			viewport.value.scrollTop = Math.max(0, props.scrollOffset);
			restoredOffset = viewport.value.scrollTop;
		}
		function capture() {
			if (!props.presented || !viewport.value?.clientHeight) return;
			const value = viewport.value.scrollTop;
			if (value === restoredOffset) return;
			restoredOffset = null;
			emit("scroll", {
				id: props.documentKey,
				value
			});
		}
		function focus() {
			article.value?.focus({ preventScroll: true });
		}
		watch(() => [
			props.documentKey,
			props.scrollOffset,
			props.presented
		], restore, { flush: "post" });
		onMounted(() => {
			observer = new ResizeObserver(restore);
			observer.observe(article.value);
			restore();
		});
		onBeforeUnmount(() => {
			capture();
			observer?.disconnect();
		});
		__expose({
			capture,
			focus,
			restore,
			viewport
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "viewport",
				ref: viewport,
				class: "document-pane",
				style: normalizeStyle({
					...unref(documentStyle),
					"--document-inset": __props.contentInset + "px"
				}),
				onScroll: capture
			}, [createBaseVNode("article", {
				ref_key: "article",
				ref: article,
				tabindex: "0"
			}, [
				__props.error ? (openBlock(), createElementBlock("p", _hoisted_1$7, toDisplayString(__props.error), 1)) : createCommentVNode("", true),
				__props.notice ? (openBlock(), createElementBlock("p", _hoisted_2$6, toDisplayString(__props.notice), 1)) : createCommentVNode("", true),
				__props.summary && !__props.error ? (openBlock(), createElementBlock("div", _hoisted_3$3, [createVNode(_sfc_main$17, { name: "info" }), createVNode(_sfc_main$13, {
					text: __props.summary,
					onTopic: _cache[0] || (_cache[0] = ($event) => emit("link", $event))
				}, null, 8, ["text"])])) : createCommentVNode("", true),
				!__props.error ? (openBlock(), createBlock(_sfc_main$13, {
					key: 3,
					text: __props.text || "",
					onTopic: _cache[1] || (_cache[1] = ($event) => emit("link", $event))
				}, null, 8, ["text"])) : createCommentVNode("", true)
			], 512)], 36);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/search/organization.mjs
function taskGroup(tasks, process, statuses, accent, compare) {
	const matching = tasks.filter((task) => task.process === process), values = [];
	for (const task of matching) if (task.status && !values.includes(task.status)) values.push(task.status);
	if (!values.length) return {
		key: matching.length ? "__no_status__" : "__no_task__",
		label: matching.length ? "No status" : "No task",
		translate: true,
		rank: matching.length ? 9999 : 1e4,
		accent
	};
	const catalog = Object.create(null);
	for (let index = 0; index < statuses.length; index++) catalog[statuses[index].key] = {
		rank: index,
		accent: statuses[index].accent || accent
	};
	values.sort((left, right) => (catalog[left]?.rank ?? 9e3) - (catalog[right]?.rank ?? 9e3) || compare(left, right));
	const key = values[0];
	return {
		key,
		label: key,
		rank: catalog[key]?.rank ?? 9e3,
		accent: catalog[key]?.accent || accent
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/search/menus.ui.mjs
var views = [
	{
		value: "continious",
		label: "Continuous tree",
		icon: "MDI_FORMAT_LIST_BULLETED"
	},
	{
		value: "tiles",
		label: "Cards",
		icon: "MDI_VIEW_DASHBOARD"
	},
	{
		value: "table",
		label: "Table",
		icon: "MDI_TABLE"
	},
	{
		value: "compact",
		label: "Compact rows",
		icon: "MDI_VIEW_LIST"
	},
	{
		value: "splitted_vertical",
		label: "Versions on the right",
		icon: "MDI_VIEW_COLUMN"
	},
	{
		value: "splitted_horizontal",
		label: "Versions at the bottom",
		icon: "MDI_VIEW_AGENDA"
	}
];
var groups = [
	{
		value: "none",
		label: "No grouping",
		icon: "list-alt"
	},
	{
		value: "status",
		label: "SObject status",
		icon: "group-items"
	},
	{
		value: "pipeline",
		label: "Pipeline",
		icon: "process"
	}
];
var sorts = [
	{
		value: "name_asc",
		label: "Name A-Z",
		icon: "sort-items",
		column: "name",
		direction: "asc"
	},
	{
		value: "name_desc",
		label: "Name Z-A",
		icon: "sort-items",
		column: "name",
		direction: "desc"
	},
	{
		value: "updated_desc",
		label: "Recently updated",
		icon: "history",
		column: "timestamp",
		direction: "desc"
	},
	{
		value: "updated_asc",
		label: "Oldest updated",
		icon: "history",
		column: "timestamp",
		direction: "asc"
	}
];
function choices(items, value, busy) {
	return items.map((item) => ({
		title: item.label,
		icon: item.icon,
		command: item.value,
		checked: item.value === value,
		enabled: !busy
	}));
}
function viewActions(value, busy) {
	return choices(views, value, busy);
}
function sortActions(model) {
	const actions = [{
		title: "Sort items",
		header: true
	}].concat(choices(sorts, model.mode, model.busy));
	if (model.defaultOrder) actions.push({
		title: "Default order",
		icon: "list-alt",
		command: "default",
		checked: !model.column,
		enabled: !model.busy
	});
	return actions.concat([{ separator: true }, {
		title: "Sort by column",
		icon: "table",
		command: "column",
		enabled: !model.busy
	}]);
}
function groupActions(model) {
	const actions = [{
		title: "Group items",
		header: true
	}].concat(choices(groups, model.mode, model.busy));
	if ((model.processes || []).length) {
		actions.push({ separator: true }, {
			title: "Task status by process",
			header: true
		});
		for (const process of model.processes) actions.push({
			title: process.title || process.key,
			translate: false,
			icon: "process-marker",
			accent: process.accent,
			command: "task_status:" + process.key,
			checked: model.mode === "task_status:" + process.key,
			enabled: !model.busy
		});
	}
	return actions;
}
function filterActions(model) {
	const actions = (model.base || [{
		title: "Advanced Search",
		icon: "advanced-search",
		command: "advanced_search"
	}, {
		title: "Filter Processes",
		icon: "filter-alt",
		command: "filter_processes"
	}]).slice();
	actions.push({ separator: true }, {
		title: "Saved searches",
		header: true
	});
	for (const preset of model.presets || []) actions.push({
		title: preset.title || "Saved search",
		translate: false,
		icon: "save",
		command: "preset:" + preset.view,
		checked: preset.view === model.selected,
		enabled: !model.busy && !preset.error
	});
	if (!(model.presets || []).length) actions.push({
		title: model.busy ? "Loading saved searches..." : model.error || "No saved searches",
		icon: model.busy ? "hourglass_empty" : "save",
		command: "",
		enabled: false
	});
	actions.push({ separator: true }, {
		title: "Refresh saved searches",
		icon: "refresh",
		command: "refresh_presets",
		enabled: !model.busy
	});
	return actions;
}
function sortColumn(model, width, language) {
	const text = (key) => translate(key, language);
	return {
		nodes: [
			label("searchSortColumnTitle", rect(0, 0, width, 24), text("Sort by column"), { weight: 600 }),
			node("Choice", "searchSortColumn", rect(0, 30, width, 36), {
				label: text("Sort by"),
				value: model.column,
				options: model.columns || [],
				action: { type: "column" },
				enabled: !model.busy
			}),
			button("searchSortDirection", rect(0, 72, width, 36), text(model.direction === "desc" ? "Descending" : "Ascending"), "sort", { type: "direction" }, !model.busy),
			button("searchSortApply", rect(width - 112, 120, 112, 36), text("Apply"), "check", { type: "apply" }, !model.busy && !!model.column, { highlighted: true })
		],
		contentHeight: 156
	};
}
//#endregion
//#region src/features/workspace/resultViews.js
var defaultResultView = "continious";
function groupRecords(records, mode, nodes = [], organization = {}) {
	if (mode === "none") return [{
		key: "",
		label: "",
		records
	}];
	const groups = /* @__PURE__ */ new Map(), byKey = new Map(nodes.map((node) => [node.record.__search_key__, node])), process = mode.startsWith("task_status:") ? mode.slice(12) : "", collator = new Intl.Collator(void 0, {
		numeric: true,
		sensitivity: "base"
	});
	for (const record of records) {
		const node = byKey.get(record.__search_key__), task = process ? taskGroup(node?.tasks || [], process, organization.statuses?.[process] || [], node?.accent, collator.compare) : null, key = task ? task.key : mode === "pipeline" ? record.pipeline_code || "" : record.status || record.state || "";
		if (!groups.has(key)) groups.set(key, {
			key,
			label: task ? task.label : mode === "pipeline" ? key || "No pipeline" : key || "No status",
			translate: task?.translate,
			rank: task?.rank || 0,
			accent: task?.accent,
			records: []
		});
		groups.get(key).records.push(record);
	}
	return [...groups.values()].sort((left, right) => left.rank - right.rank || (!left.key ? 1 : !right.key ? -1 : collator.compare(left.label, right.label)));
}
//#endregion
//#region src/controls/layout/InfoValueStrip.vue
var _hoisted_1$6 = { class: "info-value-strip" };
var _hoisted_2$5 = {
	key: 0,
	class: "info-separator"
};
var _sfc_main$11 = {
	__name: "InfoValueStrip",
	props: {
		items: {
			type: Array,
			default: () => []
		},
		selected: Boolean,
		maximumItems: Number,
		maximumItemWidth: {
			type: Number,
			default: 180
		},
		separator: {
			type: String,
			default: "/"
		}
	},
	emits: ["link"],
	setup(__props) {
		function text(item) {
			return item.text !== void 0 ? String(item.text || "") : [item.label, item.value].filter(Boolean).join(": ");
		}
		function external(url) {
			return /^(https?:\/\/|ftp:\/\/|mailto:)/i.test(url || "") && !/[\u0000-\u001f]/.test(url);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", _hoisted_1$6, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.maximumItems > 0 ? __props.items.slice(0, __props.maximumItems) : __props.items, (item, index) => {
				return openBlock(), createElementBlock(Fragment, { key: index }, [index ? (openBlock(), createElementBlock("span", _hoisted_2$5, toDisplayString(__props.separator), 1)) : createCommentVNode("", true), (openBlock(), createBlock(resolveDynamicComponent(external(item.url) ? "a" : "span"), {
					href: external(item.url) ? item.url : void 0,
					target: "_blank",
					rel: "noopener noreferrer",
					title: item.tooltip || item.value || text(item),
					style: normalizeStyle({
						maxWidth: __props.maximumItemWidth + "px",
						color: item.url ? "var(--primary)" : item.color || (__props.selected ? "var(--on-content-selection)" : "var(--muted)")
					}),
					onClick: ($event) => external(item.url) && _ctx.$emit("link", item.url)
				}, {
					default: withCtx(() => [createTextVNode(toDisplayString(text(item)), 1)]),
					_: 2
				}, 1032, [
					"href",
					"title",
					"style",
					"onClick"
				]))], 64);
			}), 128))]);
		};
	}
};
//#endregion
//#region src/controls/actions/DisclosureButton.vue
var _sfc_main$10 = {
	__name: "DisclosureButton",
	props: {
		identity: {
			type: String,
			required: true
		},
		expanded: Boolean,
		loading: Boolean,
		hasChildren: Boolean,
		iconSize: {
			type: Number,
			default: 15
		},
		indicatorSize: {
			type: Number,
			default: 22
		},
		label: String
	},
	emits: ["click"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const requested = ref(false);
		watch(() => props.identity, () => {
			requested.value = false;
		});
		watch(() => props.loading, (value) => {
			if (!value) requested.value = false;
		});
		function activate(event) {
			if (!props.hasChildren || props.loading) return;
			requested.value = true;
			emit("click", event);
			nextTick(() => {
				if (!props.loading) requested.value = false;
			});
		}
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$16, {
				class: "disclosure-button",
				style: normalizeStyle({
					"--disclosure-icon-size": __props.iconSize + "px",
					"--disclosure-indicator-size": __props.indicatorSize + "px"
				}),
				"icon-only": "",
				icon: !__props.hasChildren || __props.loading && requested.value ? void 0 : "chevron-right",
				label: __props.label || (__props.expanded ? "Collapse item" : "Expand item"),
				disabled: !__props.hasChildren || __props.loading,
				"aria-expanded": __props.expanded,
				"aria-busy": __props.loading,
				"aria-hidden": !__props.hasChildren || void 0,
				onClick: activate
			}, {
				default: withCtx(() => [__props.loading && requested.value ? (openBlock(), createBlock(BusyIndicator_default, {
					key: 0,
					running: ""
				})) : createCommentVNode("", true)]),
				_: 1
			}, 8, [
				"style",
				"icon",
				"label",
				"disabled",
				"aria-expanded",
				"aria-busy",
				"aria-hidden"
			]);
		};
	}
};
//#endregion
//#region src/controls/AppMenuItem.vue
var _hoisted_1$5 = { class: "app-menu-item" };
var _hoisted_2$4 = { class: "app-menu-item-label" };
var _sfc_main$9 = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppMenuItem",
	props: {
		label: String,
		role: String,
		icon: String,
		checked: {
			type: Boolean,
			default: void 0
		},
		disabled: Boolean,
		disabledReason: String,
		translate: {
			type: Boolean,
			default: true
		},
		secondaryLabel: String,
		secondaryIcon: {
			type: String,
			default: "close"
		}
	},
	emits: ["click", "secondary"],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$5, [createVNode(_sfc_main$16, mergeProps(_ctx.$attrs, {
				"data-menu-primary": "",
				icon: __props.icon,
				label: __props.label,
				"aria-label": __props.translate ? unref(t)(__props.label) : __props.label,
				title: __props.disabled && __props.disabledReason ? unref(t)(__props.disabledReason) : __props.translate ? unref(t)(__props.label) : __props.label,
				"aria-description": __props.disabled && __props.disabledReason ? unref(t)(__props.disabledReason) : void 0,
				role: __props.role || (__props.checked === void 0 ? "menuitem" : "menuitemradio"),
				"aria-checked": __props.checked,
				disabled: __props.disabled,
				onClick: _cache[0] || (_cache[0] = ($event) => emit("click", $event))
			}), {
				default: withCtx(() => [createBaseVNode("span", _hoisted_2$4, toDisplayString(__props.translate ? unref(t)(__props.label) : __props.label), 1), __props.checked ? (openBlock(), createBlock(_sfc_main$17, {
					key: 0,
					name: "check-circle",
					class: "menu-check"
				})) : createCommentVNode("", true)]),
				_: 1
			}, 16, [
				"icon",
				"label",
				"aria-label",
				"title",
				"aria-description",
				"role",
				"aria-checked",
				"disabled"
			]), __props.secondaryLabel ? (openBlock(), createBlock(_sfc_main$16, {
				key: 0,
				"data-menu-secondary": "",
				"icon-only": "",
				icon: __props.secondaryIcon,
				label: __props.secondaryLabel,
				role: "menuitem",
				disabled: __props.disabled,
				onClick: _cache[1] || (_cache[1] = ($event) => emit("secondary", $event))
			}, null, 8, [
				"icon",
				"label",
				"disabled"
			])) : createCommentVNode("", true)]);
		};
	}
});
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs
var handles = [
	"e",
	"s",
	"se"
];
function pick(boxes, x, y, selected = "", cycle = false) {
	const hits = (boxes || []).filter((box) => {
		const hit = box.hit || box;
		return x >= hit.x && x < hit.x + hit.width && y >= hit.y && y < hit.y + hit.height;
	}).reverse();
	if (!hits.length) return null;
	return hits[((cycle ? hits.findIndex((box) => box.key === selected) : -1) + 1) % hits.length];
}
function intersect(a, b) {
	if (!a) return b;
	const x = Math.max(a.x, b.x), y = Math.max(a.y, b.y);
	return rect(x, y, Math.max(0, Math.min(a.x + a.width, b.x + b.width) - x), Math.max(0, Math.min(a.y + a.height, b.y + b.height) - y));
}
function boxes(nodes, field, x = 0, y = 0, depth = 0, clip = null) {
	let result = [];
	for (const item of Array.from(nodes || []).sort((a, b) => (a.layer || 0) - (b.layer || 0))) {
		const left = x + item.x, top = y + item.y;
		const hit = intersect(clip, rect(left, top, item.width, item.height));
		if (item[field] !== void 0 && hit.width > 0 && hit.height > 0) result.push({
			id: item.id,
			key: field === "editorPath" ? Array.from(item[field]).join(".") : String(item[field]),
			x: left,
			y: top,
			width: item.width,
			height: item.height,
			depth,
			hit,
			grid: item.canvasGrid
		});
		result = result.concat(boxes(item.children, field, left, top, depth + 1, item.clip ? hit : clip));
	}
	return result;
}
function transform(box, handle, dx, dy) {
	const next = Object.assign({}, box);
	dx = Math.round(dx);
	dy = Math.round(dy);
	if (handle === "move") {
		next.x += dx;
		next.y += dy;
	} else {
		if (handle.includes("e")) next.width = Math.max(40, Math.min(2400, next.width + dx));
		if (handle.includes("s")) next.height = Math.max(24, Math.min(1600, next.height + dy));
	}
	return next;
}
function decorate(scene, field, view = "canvasOverlay", accept = () => true) {
	const result = Object.assign({}, scene, { nodes: (scene.nodes || []).slice() });
	const index = result.nodes.findIndex((n) => n.id === "customLayoutScroll");
	const scroll = index < 0 ? null : Object.assign({}, result.nodes[index], { children: result.nodes[index].children.slice() });
	if (scroll) result.nodes[index] = scroll;
	const children = scroll ? scroll.children : result.nodes;
	const targets = boxes(children, field).filter(accept);
	if (!targets.length) return scene;
	children.push(node("View", "canvasOverlay", rect(0, 0, Math.max(...targets.map((b) => b.x + b.width)), Math.max(...targets.map((b) => b.y + b.height))), {
		view,
		layer: 1e3
	}));
	return Object.assign(result, { canvasBoxes: targets });
}
function spacingField(id, title, value, text, action, language, enabled, width) {
	const sides = [
		"Top",
		"Right",
		"Bottom",
		"Left"
	];
	const size = Math.max(1, (width - 18) / 4);
	const children = [];
	for (let side = 0; side < 4; side++) {
		const key = id + ":" + side;
		children.push(node("Label", id + "Label" + side, rect(side * (size + 6), 0, size, 18), {
			text: translate(sides[side], language),
			fontRole: "caption",
			color: "secondaryText"
		}), node("Field", id + side, rect(side * (size + 6), 22, size, 34), {
			label: title + ": " + translate(sides[side], language),
			text: Object.prototype.hasOwnProperty.call(text, key) ? text[key] : String(value[side]),
			enabled,
			inputMode: "numeric",
			action: {
				type: "buffer",
				key
			},
			commitAction: Object.assign({}, action, {
				side,
				key
			})
		}));
	}
	return {
		kind: "Box",
		id,
		title,
		fullWidth: true,
		height: 80,
		props: { children: [node("Label", id + "Heading", rect(0, 0, width, 18), {
			text: title,
			weight: 600
		}), node("Box", id + "Fields", rect(0, 24, width, 56), { children })] }
	};
}
function itemScene(scene, layout, prefix = "itemComposition") {
	if (layout.flow === "contents" || layout.collection === "table") return scene;
	const result = decorate(scene, "layoutElement", "canvasOverlay", (box) => {
		const item = layout.elements.find((row) => row.name === box.key);
		return !!item && box.id === prefix + "_" + item.name;
	});
	return Object.assign({}, result, { canvasBoxes: (result.canvasBoxes || []).map((box) => {
		const item = layout.elements.find((row) => row.name === box.key), parent = layout.elements.find((row) => row.name === item.parent);
		return Object.assign({}, box, {
			label: item.title || item.name,
			canTransform: (parent ? parent.flow : layout.flow) === "grid"
		});
	}) });
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/layouts/page.selection.mjs
var alignments = [
	"left",
	"centerX",
	"right",
	"top",
	"centerY",
	"bottom"
];
function roots(keys) {
	const unique = Array.from(new Set(keys));
	return unique.filter((key) => !unique.some((parent) => key.startsWith(parent + ".")));
}
function toggle(keys, key) {
	if (keys.includes(key)) return keys.filter((value) => value !== key);
	return roots(keys.filter((value) => !key.startsWith(value + ".")).concat(key));
}
function selected(boxes, keys) {
	const names = roots(keys);
	return boxes.filter((box) => names.includes(box.key));
}
function bounds(boxes) {
	if (!boxes.length) return null;
	const x = Math.min(...boxes.map((box) => box.x));
	const y = Math.min(...boxes.map((box) => box.y));
	return {
		x,
		y,
		width: Math.max(...boxes.map((box) => box.x + box.width)) - x,
		height: Math.max(...boxes.map((box) => box.y + box.height)) - y
	};
}
function marquee(boxes, start, end) {
	const area = bounds([{
		x: start.x,
		y: start.y,
		width: 0,
		height: 0
	}, {
		x: end.x,
		y: end.y,
		width: 0,
		height: 0
	}]);
	return roots(boxes.filter((box) => {
		const hit = box.hit || box;
		return hit.x >= area.x && hit.y >= area.y && hit.x + hit.width <= area.x + area.width && hit.y + hit.height <= area.y + area.height;
	}).map((box) => box.key));
}
function alignment(boxes, mode) {
	if (!alignments.includes(mode) || boxes.length < 2) return [];
	const group = bounds(boxes);
	return boxes.map((box) => {
		const after = Object.assign({}, box);
		if (mode === "left") after.x = group.x;
		if (mode === "centerX") after.x = group.x + (group.width - box.width) / 2;
		if (mode === "right") after.x = group.x + group.width - box.width;
		if (mode === "top") after.y = group.y;
		if (mode === "centerY") after.y = group.y + (group.height - box.height) / 2;
		if (mode === "bottom") after.y = group.y + group.height - box.height;
		after.x = Math.round(after.x);
		after.y = Math.round(after.y);
		return {
			key: box.key,
			handle: "move",
			position: true,
			before: box,
			after
		};
	});
}
function drag(boxes, handle, dx, dy, candidates, scale, snap) {
	const group = bounds(boxes);
	const moving = transform(group, handle, dx, dy);
	const guides = [];
	const others = candidates.filter((box) => !boxes.some((chosen) => box.key === chosen.key || box.key.startsWith(chosen.key + ".") || chosen.key.startsWith(box.key + ".")));
	if (snap) for (const axis of ["x", "y"]) {
		const size = axis === "x" ? "width" : "height";
		if (!(handle === "move" || handle.includes(axis === "x" ? "e" : "s"))) continue;
		const anchors = handle === "move" ? [
			0,
			.5,
			1
		] : [1];
		let best = null;
		for (const other of others) for (const target of [
			0,
			.5,
			1
		]) for (const anchor of anchors) {
			const value = other[axis] + other[size] * target;
			const delta = value - moving[axis] - moving[size] * anchor;
			if (Math.abs(delta) <= 6 / scale && (!best || Math.abs(delta) < Math.abs(best.delta))) best = {
				axis,
				value,
				delta,
				other
			};
		}
		if (best) {
			if (handle === "move") moving[axis] += best.delta;
			else moving[size] = Math.max(axis === "x" ? 40 : 24, moving[size] + best.delta);
			const cross = axis === "x" ? "y" : "x", extent = axis === "x" ? "height" : "width";
			guides.push({
				axis,
				value: best.value,
				start: Math.min(moving[cross], best.other[cross]),
				end: Math.max(moving[cross] + moving[extent], best.other[cross] + best.other[extent])
			});
		}
	}
	return {
		changes: boxes.map((box) => ({
			key: box.key,
			handle,
			position: true,
			before: box,
			after: handle === "move" ? transform(box, handle, moving.x - group.x, moving.y - group.y) : Object.assign({}, box, {
				width: moving.width,
				height: moving.height
			})
		})),
		guides
	};
}
//#endregion
//#region src/features/administration/CanvasSelection.vue
var _hoisted_1$4 = ["data-canvas-guide"];
var _hoisted_2$3 = [
	"data-canvas-key",
	"aria-label",
	"onPointerdown",
	"onKeydown"
];
var _hoisted_3$2 = ["aria-label"];
var _hoisted_4$2 = [
	"data-canvas-handle",
	"aria-label",
	"onPointerdown",
	"onKeydown"
];
var _sfc_main$8 = {
	__name: "CanvasSelection",
	props: {
		boxes: Array,
		selected: String,
		scale: {
			type: Number,
			default: 1
		},
		selection: Array,
		multiple: Boolean,
		multiSelect: Boolean,
		snap: Boolean
	},
	emits: [
		"select",
		"selection",
		"commit"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const gesture = ref(null), ghost = ref(null), preview = ref(null), rubber = ref(null);
		const group = computed(() => selected(props.boxes || [], props.selection || [props.selected]));
		const outlines = computed(() => preview.value?.changes.map((change) => change.after) || group.value);
		const chosen = computed(() => props.multiple && group.value.length > 1 ? Object.assign({}, bounds(outlines.value), { group: true }) : ghost.value || preview.value?.changes[0]?.after || (props.boxes || []).find((box) => box.key === props.selected));
		const css = (b) => ({
			left: b.x + "px",
			top: b.y + "px",
			width: b.width + "px",
			height: b.height + "px"
		});
		const point = (e) => {
			const area = e.currentTarget.closest(".canvas-selection").getBoundingClientRect();
			return {
				x: (e.clientX - area.left) / props.scale,
				y: (e.clientY - area.top) / props.scale
			};
		};
		function start(e, box, handle, hit = false) {
			if (e.button !== 0) return;
			e.preventDefault();
			e.stopPropagation();
			e.currentTarget.focus();
			e.currentTarget.setPointerCapture(e.pointerId);
			const p = point(e);
			if (props.multiple && (!box || e.shiftKey)) {
				gesture.value = {
					marquee: true,
					start: p,
					base: props.selection || [],
					box
				};
				rubber.value = {
					x: p.x,
					y: p.y,
					width: 0,
					height: 0
				};
				return;
			}
			if (hit && e.altKey) box = pick(props.boxes, p.x, p.y, props.selected, true) || box;
			if (props.multiple) {
				let keys = props.selection || [];
				if (!box.group && (e.ctrlKey || e.metaKey || props.multiSelect)) {
					emit("selection", toggle(keys, box.key));
					return;
				}
				if (!box.group && !keys.includes(box.key)) keys = [box.key];
				emit("selection", keys);
				const boxes = selected(props.boxes, keys);
				if (!boxes.length) return;
				gesture.value = {
					boxes,
					handle,
					x: e.clientX,
					y: e.clientY,
					scale: props.scale
				};
				return;
			}
			emit("select", box.key);
			if (box.canTransform === false) return;
			gesture.value = {
				box: { ...box },
				handle,
				x: e.clientX,
				y: e.clientY,
				scale: props.scale
			};
			ghost.value = { ...box };
		}
		function move(e) {
			const g = gesture.value;
			if (!g) return;
			if (g.marquee) {
				const p = point(e);
				rubber.value = bounds([{
					...g.start,
					width: 0,
					height: 0
				}, {
					...p,
					width: 0,
					height: 0
				}]);
				return;
			}
			const dx = (e.clientX - g.x) / g.scale, dy = (e.clientY - g.y) / g.scale;
			if (g.boxes) {
				if (Math.hypot(dx, dy) * g.scale < 3 && !g.moved) return;
				g.moved = true;
				preview.value = drag(g.boxes, g.handle, dx, dy, props.boxes, g.scale, props.snap && !e.altKey);
			} else ghost.value = transform(g.box, g.handle, dx, dy);
		}
		function finish(e) {
			const g = gesture.value;
			if (!g) return;
			move(e);
			if (g.marquee) {
				const p = point(e);
				const small = Math.hypot(p.x - g.start.x, p.y - g.start.y) * props.scale < 3;
				emit("selection", small ? g.box ? toggle(g.base, g.box.key) : [] : roots(g.base.concat(marquee(props.boxes, g.start, p))));
			} else if (g.boxes) {
				const changes = preview.value?.changes || [];
				if (changes.some((c) => JSON.stringify(c.before) !== JSON.stringify(c.after))) emit("commit", { changes });
			} else {
				const after = { ...ghost.value };
				if (JSON.stringify(after) !== JSON.stringify(g.box)) emit("commit", {
					key: g.box.key,
					handle: g.handle,
					before: g.box,
					after
				});
			}
			cancel();
		}
		function cancel() {
			gesture.value = ghost.value = preview.value = rubber.value = null;
		}
		function key(e, box, resizeHandle) {
			if (e.key === "Escape") {
				e.preventDefault();
				cancel();
				e.stopPropagation();
				return;
			}
			const d = {
				ArrowLeft: [-1, 0],
				ArrowRight: [1, 0],
				ArrowUp: [0, -1],
				ArrowDown: [0, 1]
			}[e.key];
			if (!d || box.canTransform === false) return;
			e.preventDefault();
			e.stopPropagation();
			const step = e.shiftKey ? 10 : 1, handle = resizeHandle || (e.altKey ? "se" : "move");
			if (props.multiple) {
				if (group.value.length > 1 && handle !== "move") return;
				emit("commit", { changes: drag(group.value, handle, d[0] * step, d[1] * step, [], props.scale, false).changes });
			} else emit("commit", {
				key: box.key,
				handle,
				keyboard: true,
				before: box,
				after: transform(box, handle, d[0] * step, d[1] * step)
			});
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "canvas-selection",
				style: normalizeStyle({ "--canvas-inverse-scale": 1 / __props.scale })
			}, [
				__props.multiple ? (openBlock(), createElementBlock("div", {
					key: 0,
					class: "canvas-background",
					tabindex: "0",
					onPointerdown: _cache[0] || (_cache[0] = ($event) => start($event, null, "move")),
					onPointermove: move,
					onPointerup: finish,
					onPointercancel: cancel
				}, null, 32)) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList(__props.multiple ? outlines.value : [], (box) => {
					return openBlock(), createElementBlock("div", {
						key: "outline-" + box.key,
						class: "canvas-outline",
						style: normalizeStyle(css(box))
					}, null, 4);
				}), 128)),
				(openBlock(true), createElementBlock(Fragment, null, renderList(preview.value?.guides || [], (guide, index) => {
					return openBlock(), createElementBlock("div", {
						key: "guide-" + index,
						class: "canvas-guide",
						"data-canvas-guide": guide.axis,
						style: normalizeStyle(guide.axis === "x" ? {
							left: guide.value + "px",
							top: guide.start + "px",
							height: guide.end - guide.start + "px",
							width: 0
						} : {
							top: guide.value + "px",
							left: guide.start + "px",
							width: guide.end - guide.start + "px",
							height: 0
						})
					}, null, 12, _hoisted_1$4);
				}), 128)),
				rubber.value ? (openBlock(), createElementBlock("div", {
					key: 1,
					class: "canvas-marquee",
					style: normalizeStyle(css(rubber.value))
				}, null, 4)) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList(__props.boxes, (box, i) => {
					return openBlock(), createElementBlock("div", {
						key: box.key,
						class: "canvas-hit",
						style: normalizeStyle({
							...css(box.hit || box),
							zIndex: i,
							cursor: box.canTransform === false ? "pointer" : "move"
						}),
						"data-canvas-key": box.key,
						tabindex: "0",
						role: "button",
						"aria-label": unref(t)("Select element") + " " + (box.label || box.key),
						onPointerdown: ($event) => start($event, box, "move", true),
						onPointermove: move,
						onPointerup: finish,
						onPointercancel: cancel,
						onKeydown: ($event) => key($event, box)
					}, null, 44, _hoisted_2$3);
				}), 128)),
				chosen.value ? (openBlock(), createElementBlock("div", {
					key: 2,
					class: "canvas-outline",
					style: normalizeStyle(css(chosen.value))
				}, [
					chosen.value.canTransform !== false ? (openBlock(), createElementBlock("div", {
						key: 0,
						class: "canvas-move-edge",
						tabindex: "0",
						role: "button",
						"aria-label": unref(t)("Move element"),
						onPointerdown: _cache[1] || (_cache[1] = ($event) => start($event, chosen.value, "move")),
						onPointermove: move,
						onPointerup: finish,
						onPointercancel: cancel,
						onKeydown: _cache[2] || (_cache[2] = ($event) => key($event, chosen.value))
					}, null, 40, _hoisted_3$2)) : createCommentVNode("", true),
					createBaseVNode("span", {
						class: "canvas-size",
						style: normalizeStyle({ fontSize: Math.round(11 / __props.scale) + "px" })
					}, toDisplayString(Math.round(chosen.value.width)) + " Г— " + toDisplayString(Math.round(chosen.value.height)), 5),
					(openBlock(true), createElementBlock(Fragment, null, renderList(chosen.value.canTransform === false || chosen.value.group ? [] : handles, (handle) => {
						return openBlock(), createElementBlock("div", {
							key: handle,
							class: normalizeClass(["canvas-handle", "canvas-handle-" + handle]),
							"data-canvas-handle": handle,
							tabindex: "0",
							role: "button",
							"aria-label": unref(t)("Resize element") + " " + handle,
							onPointerdown: ($event) => start($event, chosen.value, handle),
							onPointermove: move,
							onPointerup: finish,
							onPointercancel: cancel,
							onKeydown: ($event) => key($event, chosen.value, handle)
						}, null, 42, _hoisted_4$2);
					}), 128))
				], 4)) : createCommentVNode("", true)
			], 4);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/emoji.ui.mjs
var categorySpecs = [
	["Smileys & Emotion", "emoji"],
	["People & Body", "person"],
	["Component", "puzzle-piece"],
	["Animals & Nature", "paw"],
	["Food & Drink", "utensils"],
	["Travel & Places", "car"],
	["Activities", "futbol"],
	["Objects", "lightbulb"],
	["Symbols", "shapes"],
	["Flags", "flag"]
];
function popup$1(screenWidth, screenHeight) {
	return {
		width: Math.max(0, Math.min(336, screenWidth - 16)),
		height: Math.max(0, Math.min(356, screenHeight - 20))
	};
}
function layout(width, height, phone = false) {
	const columns = phone ? Math.max(1, Math.floor(Math.max(0, width - 12) / 44)) : 8, cell = Math.floor(Math.max(0, width - 12) / columns);
	return {
		header: rect(0, 0, width, 76),
		grid: rect(0, 84, width, Math.max(0, height - 84)),
		columns,
		cell,
		fontSize: phone ? 32 : 26
	};
}
function heading(model, width, language) {
	const tr = (text) => translate(text, language);
	return {
		height: 76,
		nodes: [node("Field", "emojiPickerSearchField", rect(0, 0, width, 36), {
			label: tr("Find emoji"),
			placeholder: tr("Find emoji"),
			text: model.query || "",
			action: { type: "query" },
			icon: "search"
		}), node("Segmented", "emojiCategorySwitcher", rect(0, 44, width, 32), {
			label: tr("Emoji categories"),
			options: categorySpecs.map(([value, icon]) => ({
				value,
				label: tr(value),
				icon
			})),
			value: model.category || categorySpecs[0][0],
			iconOnly: true,
			action: { type: "category" }
		})]
	};
}
function cell(model, size, phone = false) {
	return {
		width: size,
		height: size,
		fontSize: phone ? 32 : 26,
		text: model.emoji || model.value || "",
		label: model.emojiName || model.name || "",
		radius: 9
	};
}
//#endregion
//#region src/controls/EmojiPicker.vue
var _hoisted_1$3 = {
	key: 0,
	role: "alert"
};
var _hoisted_2$2 = { key: 1 };
var _sfc_main$7 = {
	__name: "EmojiPicker",
	props: {
		label: {
			type: String,
			default: "Choose emoji"
		},
		disabled: Boolean,
		textTrigger: Boolean,
		externalTrigger: Boolean
	},
	emits: ["selected"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const emit = __emit;
		const menu = ref(null), anchor = ref(null), query = ref(""), category = ref("Smileys & Emotion"), entries = ref([]), error = ref("");
		const shown = computed(() => entries.value.filter((row) => query.value ? row.name.includes(query.value.toLowerCase()) || row.value === query.value : row.category === category.value));
		const grid = ref(null), scroll = ref(0), screenWidth = ref(innerWidth), screenHeight = ref(innerHeight);
		const bounds = computed(() => popup$1(screenWidth.value, screenHeight.value));
		const geometry = computed(() => layout(bounds.value.width - 20, bounds.value.height - 20, mobile.value));
		const rowCount = computed(() => Math.ceil(shown.value.length / geometry.value.columns));
		const range = computed(() => virtualRange(rowCount.value, Math.max(1, geometry.value.cell), geometry.value.grid.height, scroll.value, 2));
		const cells = computed(() => shown.value.slice(range.value.first * geometry.value.columns, range.value.last * geometry.value.columns).map((row, index) => ({
			...row,
			index: index + range.value.first * geometry.value.columns
		})));
		watch([query, category], () => {
			scroll.value = 0;
			if (grid.value) grid.value.scrollTop = 0;
		});
		function heading$2(event) {
			if (event.type === "query") query.value = event.value;
			else {
				category.value = event.value;
				query.value = "";
			}
		}
		async function move(event) {
			const index = Number(event.target.closest("[data-emoji-index]")?.dataset.emojiIndex);
			if (!Number.isInteger(index)) return;
			const columns = geometry.value.columns, delta = {
				ArrowLeft: -1,
				ArrowRight: 1,
				ArrowUp: -columns,
				ArrowDown: columns
			}[event.key];
			if (delta === void 0) return;
			event.preventDefault();
			const next = (index + delta + shown.value.length) % shown.value.length;
			const top = revealListOffset(grid.value.scrollTop, Math.floor(next / columns), geometry.value.grid.height, rowCount.value, geometry.value.cell, 0);
			scroll.value = top;
			grid.value.scrollTop = top;
			await nextTick();
			grid.value.querySelector("[data-emoji-index=\"" + next + "\"]")?.focus();
		}
		async function load() {
			screenWidth.value = innerWidth;
			screenHeight.value = innerHeight;
			if (!menu.value?.open || entries.value.length) return;
			try {
				entries.value = (await __vitePreload(async () => {
					const { default: __vite_default__ } = await import("./emoji.js");
					return { default: __vite_default__ };
				}, [])).default;
				error.value = "";
			} catch {
				error.value = "Unable to load emoji. Try again.";
			}
		}
		function select(value) {
			emit("selected", value);
			menu.value.close(true);
		}
		__expose({ openFor(source) {
			anchor.value = source;
			if (menu.value.open) menu.value.close(true);
			else menu.value.openAt({ target: source });
		} });
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$19, {
				ref_key: "menu",
				ref: menu,
				"external-trigger": __props.externalTrigger,
				anchor: anchor.value,
				class: normalizeClass(["emoji-picker", { "menu-entry": __props.textTrigger }]),
				label: __props.label,
				icon: "emoji",
				disabled: __props.disabled,
				width: bounds.value.width,
				overlay: "",
				"close-on-select": false,
				onToggle: load
			}, createSlots({
				default: withCtx(() => [
					createVNode(_sfc_main$18, {
						class: "emoji-picker-header",
						scene: heading({
							query: query.value,
							category: category.value
						}, bounds.value.width - 20, unref(appearance).language),
						onEvent: heading$2
					}, null, 8, ["scene"]),
					error.value ? (openBlock(), createElementBlock("p", _hoisted_1$3, [createTextVNode(toDisplayString(unref(t)(error.value)) + " ", 1), createVNode(_sfc_main$16, {
						label: "Retry",
						onClick: load
					})])) : createCommentVNode("", true),
					createBaseVNode("div", {
						ref_key: "grid",
						ref: grid,
						class: "emoji-grid",
						style: normalizeStyle({ height: geometry.value.grid.height + "px" }),
						onScrollPassive: _cache[0] || (_cache[0] = ($event) => scroll.value = $event.target.scrollTop),
						onKeydown: move
					}, [createBaseVNode("div", { style: normalizeStyle({
						height: rowCount.value * geometry.value.cell + "px",
						position: "relative"
					}) }, [(openBlock(true), createElementBlock(Fragment, null, renderList(cells.value, (row) => {
						return openBlock(), createBlock(_sfc_main$16, {
							key: row.value,
							"data-emoji-index": row.index,
							"aria-label": row.name,
							title: row.name,
							style: normalizeStyle({
								position: "absolute",
								left: row.index % geometry.value.columns * geometry.value.cell + "px",
								top: Math.floor(row.index / geometry.value.columns) * geometry.value.cell + "px",
								width: geometry.value.cell + "px",
								height: geometry.value.cell + "px",
								minHeight: geometry.value.cell + "px",
								fontSize: cell(row, geometry.value.cell, unref(mobile)).fontSize + "px"
							}),
							onClick: ($event) => select(row.value)
						}, {
							default: withCtx(() => [createTextVNode(toDisplayString(row.value), 1)]),
							_: 2
						}, 1032, [
							"data-emoji-index",
							"aria-label",
							"title",
							"style",
							"onClick"
						]);
					}), 128))], 4)], 36),
					entries.value.length && !shown.value.length ? (openBlock(), createElementBlock("p", _hoisted_2$2, toDisplayString(unref(t)("No matching emoji")), 1)) : createCommentVNode("", true)
				]),
				_: 2
			}, [__props.textTrigger ? {
				name: "trigger",
				fn: withCtx(() => [createVNode(_sfc_main$17, { name: "emoji" }), createBaseVNode("span", null, toDisplayString(unref(t)(__props.label)), 1)]),
				key: "0"
			} : void 0]), 1032, [
				"external-trigger",
				"anchor",
				"class",
				"label",
				"disabled",
				"width"
			]);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/messages/messaging.state.mjs
function formatFileSize(bytes) {
	const value = Math.max(0, Number(bytes) || 0);
	if (!value) return "";
	const units = [
		"B",
		"KB",
		"MB",
		"GB",
		"TB"
	], unit = Math.min(4, Math.floor(Math.log(value) / Math.log(1024))), scaled = value / 1024 ** unit;
	return (unit ? scaled.toFixed(1) : Math.round(scaled)) + " " + units[unit];
}
function bubbleContour(width, height, corner, last, tail = 6) {
	const l = (last ? tail : 0) + 2, t = 2, r = l + width, b = t + height, radius = Math.min(corner, height / 2, width / 2);
	const arc = ` A ${radius} ${radius} 0 0 1 `;
	let path = `M ${l + radius} ${t} H ${r - radius}${arc}${r} ${t + radius} V ${b - radius}${arc}${r - radius} ${b} H ${l + radius}`;
	path += last ? ` C ${l} ${b} ${l - tail} ${b} ${l - tail} ${b - 2} C ${l - tail} ${b - 4} ${l} ${b - 4} ${l} ${b - radius}` : arc + `${l} ${b - radius}`;
	return path + ` V ${t + radius}${arc}${l + radius} ${t} Z`;
}
function emojiCount(value) {
	const points = Array.from(String(value || "").trim(), (char) => char.codePointAt(0));
	let count = 0, clusterOpen = false, afterJoiner = false, pendingRegional = false;
	const base = (point) => point >= 126976 && point <= 129791 || point >= 9728 && point <= 10175 || point >= 8592 && point <= 8703 || point >= 8960 && point <= 9215 || point >= 9632 && point <= 9727 || [
		169,
		174,
		8252,
		8265,
		8482,
		8505,
		11088,
		11093,
		12336,
		12349,
		12951,
		12953
	].includes(point);
	for (let index = 0; index < points.length; index++) {
		const point = points[index];
		if ([
			32,
			9,
			10,
			13
		].includes(point)) {
			if (afterJoiner) return 0;
			clusterOpen = false;
			pendingRegional = false;
			continue;
		}
		if (point >= 48 && point <= 57 || point === 35 || point === 42) {
			let next = index + 1;
			if (points[next] === 65039) next++;
			if (points[next] !== 8419) return 0;
			count++;
			index = next;
			clusterOpen = true;
			continue;
		}
		if (point === 8205) {
			if (!clusterOpen) return 0;
			afterJoiner = true;
			continue;
		}
		if (point === 65038 || point === 65039 || point === 8419 || point >= 127995 && point <= 127999) {
			if (!clusterOpen) return 0;
			continue;
		}
		if (point >= 127462 && point <= 127487) {
			if (!pendingRegional) count++;
			pendingRegional = !pendingRegional;
			clusterOpen = true;
			afterJoiner = false;
			continue;
		}
		pendingRegional = false;
		if (!base(point)) return 0;
		if (!afterJoiner) count++;
		clusterOpen = true;
		afterJoiner = false;
		if (count > 3) return 0;
	}
	return !afterJoiner && count <= 3 ? count : 0;
}
function composerKey(event, phone = false, mentioning = false, matches = false) {
	if (event.composing || event.keyCode === 229) return "pass";
	if (event.disabled || event.sending) return event.key === "Enter" ? "consume" : "pass";
	if (event.key === "Escape" && mentioning) return "dismiss";
	if (mentioning && matches && !event.control && !event.meta && [
		"ArrowDown",
		"ArrowUp",
		"Enter"
	].includes(event.key)) return event.key === "Enter" ? event.repeat ? "consume" : "mention" : event.key === "ArrowDown" ? "next" : "previous";
	if (event.key !== "Enter" || phone) return "pass";
	if (event.repeat || event.disabled || event.sending) return "consume";
	return event.control || event.meta ? "newline" : "send";
}
function mentionQuery(text, cursor) {
	const found = String(text || "").slice(0, cursor).match(/(?:^|\s)@([A-Za-z0-9_.-]*)$/);
	return found ? found[1] : null;
}
function insertion(text, start, end, value, replace = 0) {
	const at = Math.max(0, start - replace);
	return {
		text: text.slice(0, at) + value + text.slice(end),
		cursor: at + value.length
	};
}
function bubbleGeometry(width, natural, contentHeight, model = {}, style = "md3") {
	const theme = metrics(style), small = width < 380, avatar = small ? 34 : 40, margin = small ? 8 : 12, padding = theme.communicationBubblePadding + (small ? 0 : 3), maximum = Math.max(0, Math.min(model.media ? width : 520, width * .7, width - avatar - theme.communicationAvatarSpacing - margin * 2)), bubbleWidth = Math.min(maximum, model.media ? maximum : Math.max(small ? 104 : 116, natural + padding * 2)), bubbleHeight = contentHeight + padding * 2, height = Math.max(model.last ? avatar : 0, bubbleHeight), avatarX = model.own ? width - avatar - margin : margin;
	return {
		width: bubbleWidth,
		height: bubbleHeight,
		rowHeight: height,
		x: model.own ? avatarX - theme.communicationAvatarSpacing - bubbleWidth : avatarX + avatar + theme.communicationAvatarSpacing,
		y: height - bubbleHeight,
		avatarX,
		avatarY: height - avatar,
		avatar,
		padding,
		gap: theme.communicationContentSpacing,
		corner: theme.communicationBubbleRadius,
		margin,
		maximum,
		tail: Math.min(theme.communicationGroupTailSize, theme.communicationAvatarSpacing - 2)
	};
}
var bodyOrder = [
	"reply",
	"forward",
	"previews",
	"attachments",
	"text",
	"reactions"
];
function popup(mode) {
	return {
		spacing: mode === "history" || mode === "pin-history" ? 10 : 12,
		height: {
			create: 536,
			members: 536,
			"view-members": 366,
			files: 406,
			history: 336,
			forward: 540,
			"pin-history": 336
		}[mode],
		anchored: ![
			"create",
			"members",
			"rename"
		].includes(mode),
		width: {
			create: 436,
			members: 436,
			"view-members": 306,
			files: 356,
			rename: 366,
			history: 396,
			"pin-history": 396,
			forward: 460,
			search: 336
		}[mode] || 420
	};
}
//#endregion
//#region src/controls/StatusSelect.vue
var _sfc_main$6 = {
	__name: "StatusSelect",
	props: {
		value: String,
		options: Array,
		disabled: Boolean,
		placeholder: String
	},
	emits: ["change"],
	setup(__props) {
		const props = __props;
		const current = computed(() => props.options.find((option) => option.value === props.value));
		const choices = computed(() => {
			const rows = props.options.map((option) => option.value === "" && !option.label ? {
				...option,
				label: props.placeholder || t("Select status"),
				disabled: true
			} : option);
			return rows.some((option) => option.value === "") ? rows : [{
				value: "",
				label: props.placeholder || t("Select status"),
				disabled: true
			}, ...rows];
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["status-select", { empty: !current.value }]) }, [current.value?.color ? (openBlock(), createElementBlock("span", {
				key: 0,
				class: "status-select-dot",
				style: normalizeStyle({ backgroundColor: current.value.color })
			}, null, 4)) : createCommentVNode("", true), createVNode(_sfc_main$20, {
				"model-value": __props.value || "",
				label: "Status",
				options: choices.value,
				"translate-labels": false,
				disabled: __props.disabled,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => _ctx.$emit("change", $event))
			}, null, 8, [
				"model-value",
				"options",
				"disabled"
			])], 2);
		};
	}
};
//#endregion
//#region src/controls/ResponsiveFlow.vue
var _sfc_main$5 = {
	__name: "ResponsiveFlow",
	props: {
		minimumCellWidth: {
			type: Number,
			default: 180
		},
		maximumColumns: {
			type: Number,
			default: 0
		},
		spacing: {
			type: Number,
			default: 8
		}
	},
	setup(__props) {
		const props = __props;
		const root = ref(null), width = ref(0);
		const columns = computed(() => Math.min(props.maximumColumns || Infinity, Math.max(1, Math.floor((width.value + props.spacing) / (props.minimumCellWidth + props.spacing)))));
		let observer, resizeFrame;
		onMounted(() => {
			observer = new ResizeObserver((entries) => {
				const next = entries[0].contentRect.width;
				if (next > 0 && next !== width.value) {
					cancelAnimationFrame(resizeFrame);
					resizeFrame = requestAnimationFrame(() => {
						width.value = next;
					});
				}
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(resizeFrame);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "root",
				ref: root,
				class: "responsive-flow",
				style: normalizeStyle({
					gridTemplateColumns: `repeat(${columns.value}, minmax(0, 1fr))`,
					gap: __props.spacing + "px"
				})
			}, [renderSlot(_ctx.$slots, "default")], 4);
		};
	}
};
//#endregion
//#region src/features/objects/SnapshotSummary.vue
var _sfc_main$4 = {
	__name: "SnapshotSummary",
	props: {
		snapshot: Object,
		selected: Boolean
	},
	setup(__props) {
		const props = __props;
		const host = ref(null), width = ref(0);
		const scene = computed(() => summary({
			...props.snapshot,
			selected: props.selected
		}, width.value, appearance.language, (text, size, weight = 400) => qtLabelTextWidth(text, `${weight} ${size}px Segoe UI`)));
		let observer;
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "snapshot-summary"
			}, [createVNode(_sfc_main$18, { scene: scene.value }, null, 8, ["scene"])], 512);
		};
	}
};
//#endregion
//#region src/controls/contextActions.js
var contextActions = {
	mounted(element, binding) {
		let timer, start, held = false;
		const cancel = () => {
			clearTimeout(timer);
			start = null;
		};
		const owns = (event) => event.composedPath().find((node) => node.contextActionsCleanup) === element;
		const handlers = {
			contextmenu(event) {
				if (!owns(event) || event.target.closest(".workspace-menu")) return;
				event.preventDefault();
				binding.value(event);
			},
			keydown(event) {
				if (!owns(event) || event.target.closest(".workspace-menu") || !(event.key === "ContextMenu" || event.key === "F10" && event.shiftKey)) return;
				event.preventDefault();
				event.stopPropagation();
				const box = element.getBoundingClientRect();
				binding.value({
					clientX: box.left + 9,
					clientY: box.bottom
				});
			},
			pointerdown(event) {
				cancel();
				held = false;
				if (!owns(event) || event.pointerType !== "touch" || event.isPrimary === false || event.target.closest(".workspace-menu")) return;
				start = {
					x: event.clientX,
					y: event.clientY
				};
				timer = setTimeout(() => {
					held = true;
					binding.value(event);
				}, 500);
			},
			pointermove(event) {
				if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 10) cancel();
			},
			pointerup: cancel,
			pointercancel: cancel,
			click(event) {
				if (held) {
					event.preventDefault();
					event.stopImmediatePropagation();
					held = false;
				}
			}
		};
		for (const [name, handler] of Object.entries(handlers)) element.addEventListener(name, handler, name === "click");
		element.contextActionsCleanup = () => {
			cancel();
			for (const [name, handler] of Object.entries(handlers)) element.removeEventListener(name, handler, name === "click");
		};
	},
	beforeUnmount(element) {
		element.contextActionsCleanup?.();
		delete element.contextActionsCleanup;
	}
};
//#endregion
//#region src/features/messages/messages.js
var messageId = (row) => row?.__search_key__ || row?.code || "";
var messageDate = serverTimestamp;
function initials(value) {
	return String(value || "").trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "?";
}
function groupedMessages(rows) {
	const same = (a, b) => a && b && a.login === b.login && Math.abs(messageDate(a.timestamp) - messageDate(b.timestamp)) <= 3e5;
	return rows.map((row, index) => ({
		...row,
		groupFirst: !same(rows[index - 1], row),
		groupLast: !same(row, rows[index + 1])
	}));
}
function mergeMessages(rows) {
	return [...new Map(rows.map((row) => [messageId(row), row])).values()].sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)) || Number(a.id || 0) - Number(b.id || 0));
}
function retainOlderMessages(rows, page) {
	const oldest = page.at(-1), present = new Set(page.map(messageId));
	return rows.filter((row) => !oldest || row.timestamp < oldest.timestamp || row.timestamp === oldest.timestamp && Number(row.id) < Number(oldest.id) || present.has(messageId(row)));
}
function canChangeMessage(row, login, privileged, now = serverClock.now()) {
	if (row.login !== login) return privileged;
	const stamp = messageDate(row.timestamp).getTime();
	return Number.isFinite(stamp) && stamp <= now && now - stamp <= 36e5;
}
function attachmentName(snapshot) {
	let metadata = snapshot.metadata || {};
	if (typeof metadata === "string") try {
		metadata = JSON.parse(metadata);
	} catch {
		metadata = {};
	}
	return metadata.chatAttachment?.name || snapshot.__files__?.find((file) => !["web", "icon"].includes(file.type))?.file_name || snapshot.code;
}
function messageAttachments(row) {
	return [...new Map([...row.__attachments__ || [], ...row.__forwarded_from__?.available ? row.__forwarded_from__.attachments || [] : []].map((snapshot) => [snapshot.code, snapshot])).values()];
}
function conversationAttachments(rows, users) {
	return rows.flatMap((row) => messageAttachments(row).map((snapshot) => ({
		snapshot,
		messageId: messageId(row),
		sender: users.find((user) => user.login === row.login)?.displayName || row.login,
		timestamp: row.timestamp
	})));
}
//#endregion
//#region src/features/objects/SKeyPreviewCard.vue
var _hoisted_1$2 = { class: "skey-author-row" };
var _hoisted_2$1 = { class: "skey-message-text" };
var _hoisted_3$1 = { class: "skey-author-heading" };
var _hoisted_4$1 = ["title"];
var _hoisted_5$1 = {
	key: 0,
	class: "skey-preview-body"
};
var _hoisted_6$1 = {
	key: 0,
	class: "skey-preview-body"
};
var _hoisted_7$1 = { key: 1 };
var _hoisted_8 = { key: 3 };
var _hoisted_9 = {
	key: 3,
	class: "skey-preview-text skey-knowledge-text"
};
var _hoisted_10 = { class: "skey-kind" };
var _hoisted_11 = { class: "skey-article-kind" };
var _hoisted_12 = ["title"];
var _hoisted_13 = { key: 0 };
var _hoisted_14 = {
	key: 4,
	class: "skey-preview-text"
};
var _hoisted_15 = {
	key: 0,
	class: "skey-kind"
};
var _hoisted_16 = ["title"];
var _hoisted_17 = {
	key: 1,
	class: "skey-article-kind"
};
var _hoisted_18 = { key: 0 };
var _sfc_main$3 = {
	__name: "SKeyPreviewCard",
	props: {
		preview: Object,
		previews: Object,
		compact: Boolean,
		now: Number
	},
	emits: [
		"open",
		"retry",
		"copy"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const menu = ref(null), timeHovered = ref(false);
		const failed = computed(() => props.preview.status === "error");
		const ready = computed(() => props.preview.status === "ready");
		const canOpen = computed(() => ready.value && (props.preview.kind !== "message" || props.preview.canOpen));
		const icon = computed(() => ({
			sobject: "inventory-2",
			task: "task",
			snapshot: "snapshot",
			file: "description",
			note: "notes",
			message: "chat",
			user: "user",
			project: "folder",
			knowledge: props.preview.articleKind === "section" ? "folder-open" : "book-open"
		})[props.preview.kind] || "link");
		const time = computed(() => {
			const date = messageDate(props.preview.timestamp);
			return Number.isNaN(date.getTime()) ? "" : timestampLabel(date.toISOString(), props.now ? new Date(props.now) : void 0);
		});
		const rich = computed(() => ready.value && ["note", "message"].includes(props.preview.kind) && !props.compact);
		function activate() {
			if (failed.value) emit("retry", props.preview.searchKey);
			else if (canOpen.value) emit("open", props.preview.searchKey);
		}
		function click(event) {
			if (!event.target.closest("button,a,details") && !window.getSelection()?.toString()) activate();
		}
		return (_ctx, _cache) => {
			const _component_SKeyPreviewCard = resolveComponent("SKeyPreviewCard", true);
			return withDirectives((openBlock(), createBlock(resolveDynamicComponent(__props.compact ? _sfc_main$21 : "article"), {
				class: normalizeClass(["skey-preview-card", [__props.preview.kind, {
					failed: failed.value,
					compact: __props.compact,
					rich: rich.value
				}]]),
				"data-skey": __props.preview.searchKey,
				"aria-busy": __props.preview.status === "loading",
				role: !rich.value ? "link" : void 0,
				tabindex: !rich.value ? 0 : void 0,
				"aria-label": __props.preview.title || unref(t)("TACTIC item"),
				onClick: withModifiers(click, ["stop"]),
				onKeydown: [withKeys(withModifiers(activate, ["self", "prevent"]), ["enter"]), withKeys(withModifiers(activate, ["self", "prevent"]), ["space"])]
			}, {
				default: withCtx(() => [rich.value ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
					createBaseVNode("div", _hoisted_1$2, [createVNode(ItemPreview_default, {
						source: __props.preview.avatarUrl,
						"fallback-text": __props.preview.initials,
						"fallback-icon": "user",
						"preview-size": 32,
						accent: __props.preview.authorColor,
						round: "",
						outlined: ""
					}, null, 8, [
						"source",
						"fallback-text",
						"accent"
					]), createBaseVNode("div", _hoisted_2$1, [createBaseVNode("div", _hoisted_3$1, [createVNode(_sfc_main$16, {
						class: "skey-author-name",
						style: normalizeStyle({ color: __props.preview.authorColor || "var(--primary)" }),
						href: unref(browserLink)("skey://sthpw/login?code=" + encodeURIComponent(__props.preview.author)),
						onClick: _cache[0] || (_cache[0] = withModifiers(($event) => emit("open", "skey://sthpw/login?code=" + encodeURIComponent(__props.preview.author)), ["prevent"]))
					}, {
						default: withCtx(() => [createTextVNode(toDisplayString(__props.preview.authorDisplay || __props.preview.author || unref(t)("Removed user")), 1)]),
						_: 1
					}, 8, ["style", "href"]), createBaseVNode("time", {
						title: __props.preview.timestamp,
						onMouseenter: _cache[1] || (_cache[1] = ($event) => timeHovered.value = true),
						onMouseleave: _cache[2] || (_cache[2] = ($event) => timeHovered.value = false)
					}, toDisplayString(timeHovered.value ? __props.preview.timestamp : time.value), 41, _hoisted_4$1)]), __props.preview.kind === "message" ? (openBlock(), createElementBlock("p", _hoisted_5$1, toDisplayString(__props.preview.body), 1)) : createCommentVNode("", true)])]),
					__props.preview.kind === "note" && __props.preview.body ? (openBlock(), createElementBlock("p", _hoisted_6$1, toDisplayString(__props.preview.body), 1)) : createCommentVNode("", true),
					(openBlock(true), createElementBlock(Fragment, null, renderList(__props.preview.nestedPreviews || [], (nested) => {
						return openBlock(), createBlock(_component_SKeyPreviewCard, {
							key: nested.searchKey,
							preview: __props.previews?.[nested.searchKey] || nested,
							previews: __props.previews,
							now: __props.now,
							compact: "",
							onOpen: _cache[3] || (_cache[3] = ($event) => emit("open", $event)),
							onRetry: _cache[4] || (_cache[4] = ($event) => emit("retry", $event)),
							onCopy: _cache[5] || (_cache[5] = ($event) => emit("copy", $event))
						}, null, 8, [
							"preview",
							"previews",
							"now"
						]);
					}), 128)),
					__props.preview.nestedPreviewCount > (__props.preview.nestedPreviews || []).length ? (openBlock(), createElementBlock("small", _hoisted_7$1, toDisplayString(unref(t)("+{count} more linked items", { count: __props.preview.nestedPreviewCount - __props.preview.nestedPreviews.length })), 1)) : createCommentVNode("", true),
					__props.preview.attachments?.length ? (openBlock(), createBlock(_sfc_main$5, {
						key: 2,
						"minimum-cell-width": 210,
						"maximum-columns": 2
					}, {
						default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.preview.attachments, (file) => {
							return openBlock(), createBlock(_sfc_main$22, {
								key: file.searchKey + file.title,
								title: file.title,
								extension: file.extension,
								"size-text": file.size,
								"preview-url": file.previewUrl,
								local: "",
								onActivated: ($event) => emit("open", file.searchKey)
							}, null, 8, [
								"title",
								"extension",
								"size-text",
								"preview-url",
								"onActivated"
							]);
						}), 128))]),
						_: 1
					})) : createCommentVNode("", true),
					__props.preview.attachmentCount > (__props.preview.attachments || []).length ? (openBlock(), createElementBlock("small", _hoisted_8, toDisplayString(unref(t)("+{count} more attachments", { count: __props.preview.attachmentCount - __props.preview.attachments.length })), 1)) : createCommentVNode("", true)
				], 64)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
					__props.compact ? (openBlock(), createBlock(_sfc_main$17, {
						key: 0,
						name: icon.value
					}, null, 8, ["name"])) : (openBlock(), createBlock(ItemPreview_default, {
						key: 1,
						source: __props.preview.previewUrl,
						"fallback-icon": __props.preview.kind === "snapshot" ? "file" : icon.value,
						"preview-size": __props.preview.kind === "snapshot" ? 58 : 48,
						accent: "var(--skey-accent)",
						outlined: __props.preview.kind !== "snapshot"
					}, null, 8, [
						"source",
						"fallback-icon",
						"preview-size",
						"outlined"
					])),
					__props.preview.kind === "snapshot" && ready.value && !__props.compact ? (openBlock(), createBlock(_sfc_main$4, {
						key: 2,
						snapshot: __props.preview
					}, null, 8, ["snapshot"])) : __props.preview.kind === "knowledge" && !__props.compact ? (openBlock(), createElementBlock("div", _hoisted_9, [
						createBaseVNode("div", null, [createBaseVNode("small", _hoisted_10, toDisplayString(unref(t)("Knowledge Base")), 1), createBaseVNode("small", _hoisted_11, toDisplayString(unref(t)(__props.preview.articleKind === "section" ? "Section" : "Article")), 1)]),
						createBaseVNode("strong", { title: __props.preview.title }, toDisplayString(!ready.value && !failed.value ? unref(t)("Loading article") : __props.preview.title || unref(t)("Knowledge Base article")), 9, _hoisted_12),
						failed.value || !ready.value || __props.preview.description || __props.preview.excerpt ? (openBlock(), createElementBlock("small", _hoisted_13, toDisplayString(failed.value ? unref(t)(__props.preview.error || "Link preview is unavailable") : !ready.value ? unref(t)("Resolving Knowledge Base link") : __props.preview.description || __props.preview.excerpt), 1)) : createCommentVNode("", true)
					])) : (openBlock(), createElementBlock("div", _hoisted_14, [
						createBaseVNode("div", null, [
							!__props.compact ? (openBlock(), createElementBlock("small", _hoisted_15, toDisplayString(unref(t)(__props.preview.kind === "knowledge" ? "Knowledge Base" : __props.preview.kind === "sobject" ? "SObject" : __props.preview.kind === "user" ? "User" : __props.preview.kind === "project" ? "Project" : __props.preview.kind === "task" ? "Task" : __props.preview.kind === "file" ? "File" : __props.preview.kind === "note" ? "Note" : __props.preview.kind === "message" ? "Message" : "Snapshot")), 1)) : createCommentVNode("", true),
							createBaseVNode("strong", { title: __props.preview.title }, toDisplayString(__props.preview.kind === "knowledge" && !ready.value && !failed.value ? unref(t)("Loading article") : __props.preview.title || unref(t)("TACTIC item")), 9, _hoisted_16),
							__props.preview.kind === "knowledge" ? (openBlock(), createElementBlock("small", _hoisted_17, toDisplayString(unref(t)(__props.preview.articleKind === "section" ? "Section" : "Article")), 1)) : createCommentVNode("", true)
						]),
						!__props.compact && __props.preview.subtitle && __props.preview.kind !== "knowledge" ? (openBlock(), createElementBlock("span", _hoisted_18, toDisplayString(__props.preview.subtitle), 1)) : createCommentVNode("", true),
						createBaseVNode("small", null, toDisplayString(failed.value ? unref(t)(__props.preview.error || "Link preview is unavailable") : !ready.value ? unref(t)("Resolving link") : __props.preview.kind === "knowledge" ? __props.preview.description || __props.preview.excerpt : __props.preview.detail || (__props.compact ? __props.preview.subtitle : "")), 1)
					])),
					!ready.value && !failed.value ? (openBlock(), createBlock(BusyIndicator_default, {
						key: 5,
						running: ""
					})) : !__props.compact ? (openBlock(), createBlock(_sfc_main$16, {
						key: 6,
						class: "skey-open",
						icon: failed.value ? "refresh" : __props.preview.kind === "knowledge" ? "MDI_ARROW_RIGHT" : "MDI_OPEN_IN_NEW",
						"icon-only": "",
						label: failed.value ? "Retry preview" : __props.preview.kind === "snapshot" ? "Open snapshot" : __props.preview.kind === "knowledge" ? "Open article" : "Open linked item",
						onClick: activate
					}, null, 8, ["icon", "label"])) : createCommentVNode("", true)
				], 64)), createVNode(_sfc_main$19, {
					ref_key: "menu",
					ref: menu,
					class: "skey-actions",
					label: "Link actions",
					overlay: ""
				}, {
					default: withCtx(() => [failed.value ? (openBlock(), createBlock(_sfc_main$16, {
						key: 0,
						label: "Retry preview",
						icon: "refresh",
						onClick: _cache[6] || (_cache[6] = ($event) => emit("retry", __props.preview.searchKey))
					})) : (openBlock(), createBlock(_sfc_main$16, {
						key: 1,
						label: __props.preview.kind === "message" && !canOpen.value ? "Source conversation is unavailable" : "Open linked item",
						icon: "MDI_OPEN_IN_NEW",
						disabled: !canOpen.value,
						onClick: _cache[7] || (_cache[7] = ($event) => emit("open", __props.preview.searchKey))
					}, null, 8, ["label", "disabled"])), createVNode(_sfc_main$16, {
						label: "Copy sKey",
						icon: "link",
						onClick: _cache[8] || (_cache[8] = ($event) => emit("copy", __props.preview.searchKey))
					})]),
					_: 1
				}, 512)]),
				_: 1
			}, 40, [
				"class",
				"data-skey",
				"aria-busy",
				"role",
				"tabindex",
				"aria-label",
				"onKeydown"
			])), [[unref(contextActions), (event) => menu.value.openAt(event)]]);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/objects/delete.ui.mjs
function group(model, record, width, index, language) {
	const tr = (text) => translate(text, language), nodes = [];
	const items = record.expanded ? record.items || [] : [];
	const itemHeight = Math.min(320, items.reduce((sum, item) => sum + dependencyHeight(item), 0));
	const y = 47 + (items.length ? itemHeight + 4 : 0);
	if (items.length) nodes.push(node("View", "deleteDependencyItems_" + index, rect(4, 47, Math.max(0, width - 8), itemHeight), {
		view: "dependencies",
		source: "dependencies_" + index
	}));
	nodes.unshift(node("CheckBox", "deleteDependencyCheck_" + index, rect(8, 11, 24, 24), {
		label: record.searchTypeTitle,
		prominent: !!record.defaultChecked,
		checked: !!record.checked,
		enabled: !model.busy && !model.deleting && !model.uncertain,
		action: {
			type: "check",
			index
		}
	}), button("deleteDependencyExpand_" + index, rect(40, 9, 28, 28), tr(record.expanded ? "Hide dependencies" : "Show dependencies"), record.expanded ? "expand-less" : "expand-more", {
		type: "expand",
		index
	}, true, {
		iconOnly: true,
		iconAction: true,
		iconSize: 14
	}), node("Icon", "deleteGroupIcon_" + index, rect(76, 14, 18, 18), {
		icon: record.iconName || "sobject",
		color: "secondaryText"
	}), label("deleteGroupTitle_" + index, rect(102, 5, Math.max(0, width - 114), 21), record.searchTypeTitle, { weight: 600 }), label("deleteGroupCount_" + index, rect(102, 27, Math.max(0, width - 114), 16), translate("{count} related items", language, { count: record.count }), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	return {
		nodes: [node("Box", "deleteDependencyGroup_" + index, rect(0, 0, width, y + (items.length ? 4 : 0)), {
			radiusRole: "sectionRadius",
			background: record.checked ? "surfaceContainerHighest" : "surfaceContainerHigh",
			children: nodes
		})],
		height: y + (items.length ? 4 : 0)
	};
}
function models(model, language) {
	const targets = (model.targets || []).slice(0, 16);
	if (model.targetCount > targets.length) targets.push({
		searchKey: "__remaining__",
		remaining: true,
		title: translate("and {count} more sObjects", language, { count: model.targetCount - targets.length })
	});
	const result = { targets };
	(model.groups || []).forEach((group, index) => {
		result["dependencies_" + index] = (group.items || []).map((record, position) => Object.assign({}, record, {
			position,
			groupIndex: index,
			iconName: group.iconName
		}));
	});
	return result;
}
function dependencyHeight(record) {
	return record.details ? 52 : 44;
}
function dependency(record, width) {
	const height = dependencyHeight(record), prefix = "dependency_" + record.groupIndex + "_" + record.position + "_";
	return {
		height,
		nodes: [
			node("Box", prefix + "surface", rect(0, 0, width, height), {
				background: record.position % 2 ? "surfaceContainerLow" : "surfaceContainer",
				radius: 0
			}),
			node("Icon", prefix + "icon", rect(14, (height - 17) / 2, 17, 17), {
				icon: record.iconName || "sobject",
				color: "secondaryText"
			}),
			label(prefix + "title", rect(41, record.details ? 7 : 12, Math.max(0, width - 55), 21), record.title, { weight: 500 }),
			...record.details ? [label(prefix + "details", rect(41, 30, Math.max(0, width - 55), 17), record.details, {
				fontRole: "caption",
				color: "secondaryText"
			})] : []
		]
	};
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language), margin = spacing.content, w = Math.max(0, width - margin * 2), groups = model.groups || [];
	const selected = groups.reduce((sum, row) => sum + (row.checked ? row.count : 0), 0), total = groups.reduce((sum, row) => sum + row.count, 0);
	const targets = model.targets || [], targetHeight = Math.min(132, Math.max(56, targets.length * 30 + 20));
	const footerY = Math.max(0, height - 80), contentTop = 100 + targetHeight + 12;
	const errorHeight = model.error ? 64 : 0;
	const nodes = [
		node("Box", "deleteSObjectSurface", rect(0, 0, width, height), {
			background: "panelDeep",
			radius: 0
		}),
		node("Box", "deleteSObjectHeader", rect(margin, margin, w, 72), {
			background: "surfaceContainer",
			children: [
				node("Box", "deleteIconSurface", rect(14, 15, 42, 42), {
					background: "errorContainer",
					children: [node("Icon", "deleteIcon", rect(10, 10, 22, 22), {
						icon: "delete",
						color: "error"
					})]
				}),
				label("deleteSObjectTitle", rect(68, 12, Math.max(0, w - 180), 22), tr(model.targetCount === 1 ? "Delete sObject" : "Delete sObjects"), {
					fontRole: "bodyLarge",
					weight: 600
				}),
				node("StatusChip", "deleteTargetCount", rect(Math.max(0, w - 100), 23, 46, 26), {
					text: String(model.targetCount || 0),
					icon: "sobject",
					accent: "error"
				}),
				label("deleteSObjectCaption", rect(68, 37, Math.max(0, w - 120), 19), tr("The selected objects and checked dependencies will be permanently removed from TACTIC."), {
					fontRole: "secondary",
					color: "secondaryText"
				}),
				button("deleteHelp", rect(Math.max(0, w - 42), 20, 32, 32), tr("Deletion help"), "help", { type: "help" }, true, {
					iconOnly: true,
					iconAction: true
				})
			]
		}),
		node("Box", "deleteSObjectTargetCard", rect(margin, 100, w, targetHeight), {
			background: "surfaceContainerHigh",
			radiusRole: "sectionRadius"
		}),
		node("Box", "deleteTargetRail", rect(margin + 1, 108, 3, targetHeight - 16), {
			background: "error",
			radius: 1.5
		}),
		node("List", "deleteSObjectTargets", rect(margin + 14, 110, w - 28, targetHeight - 20), {
			source: "targets",
			keyField: "searchKey",
			rowHeight: 30,
			rowGap: 2,
			background: "surfaceContainerHigh"
		}),
		node("Box", "deleteSObjectFooter", rect(margin, footerY, w, 64), {
			background: "surfaceContainer",
			children: [
				label("deleteFooterStatus", rect(14, 18, Math.max(0, w - 236), 28), model.ready ? translate("{count} dependencies selected", language, { count: selected }) : tr("Reviewing selected objects"), {
					fontRole: "secondary",
					color: "secondaryText"
				}),
				button("deleteCancel", rect(Math.max(0, w - 216), 14, 96, 36), tr("Cancel"), "", { type: "cancel" }, !model.deleting),
				button("deleteSubmit", rect(Math.max(0, w - 112), 14, 102, 36), tr("Delete"), "delete", { type: "delete" }, model.ready && !model.busy && !model.deleting && !model.uncertain, {
					destructive: true,
					highlighted: true
				})
			]
		})
	];
	const bodyHeight = Math.max(0, footerY - contentTop - 12 - errorHeight);
	if (groups.length && model.ready) {
		nodes.push(label("deleteDependenciesTitle", rect(margin, contentTop, w - 128, 22), tr("Dependencies"), { weight: 600 }));
		nodes.push(label("deleteDependenciesCaption", rect(margin, contentTop + 22, w, 18), tr("Choose related records to remove with the selected objects."), {
			fontRole: "caption",
			color: "secondaryText"
		}));
		nodes.push(node("StatusChip", "deleteDependencySelection", rect(Math.max(margin, width - 123), contentTop + 5, 107, 24), {
			text: translate("{selected} of {total} selected", language, {
				selected,
				total
			}),
			icon: "check",
			accent: "secondaryText"
		}));
		let y = 6;
		const children = [];
		groups.forEach((record, index) => {
			const scene = group(model, record, Math.max(0, w - 12), index, language);
			children.push(node("Box", "deleteGroupRow_" + index, rect(6, y, Math.max(0, w - 12), scene.height), {
				background: "transparent",
				children: scene.nodes
			}));
			y += scene.height + 8;
		});
		nodes.push(node("Box", "deleteDependenciesSurface", rect(margin, contentTop + 45, w, Math.max(0, bodyHeight - 45)), {
			background: "surfaceContainerLow",
			radiusRole: "sectionRadius"
		}));
		nodes.push(node("Scroll", "deleteSObjectDependencies", rect(margin, contentTop + 45, w, Math.max(0, bodyHeight - 45)), {
			contentHeight: y,
			children,
			background: "surfaceContainerLow"
		}));
	} else if (model.ready) {
		nodes.push(node("Box", "deleteEmptySurface", rect(margin, contentTop - 2, w, bodyHeight + 2), {
			background: "surfaceContainerLow",
			border: "outlineVariant"
		}));
		nodes.push(node("Icon", "deleteEmptyIcon", rect(width / 2 - 15, contentTop + bodyHeight / 2 - 32, 30, 30), {
			icon: "check-circle",
			color: "action"
		}));
		nodes.push(label("deleteSObjectEmptyState", rect(margin + 24, contentTop + bodyHeight / 2 + 6, w - 48, 36), tr("No dependencies were found. Only the selected objects will be deleted."), {
			align: "center",
			wrap: true,
			color: "secondaryText"
		}));
	}
	if (model.error) {
		nodes.push(label("deleteSObjectError", rect(margin, footerY - 76, Math.max(0, w - 106), 64), tr(model.error), {
			wrap: true,
			color: "error",
			role: "alert"
		}));
		if (!model.ready && !model.uncertain && !model.busy) nodes.push(button("deleteRetry", rect(Math.max(margin, width - 120), footerY - 68, 104, 36), tr("Retry"), "refresh", { type: "retry" }, true));
	}
	return {
		nodes,
		height,
		loading: model.busy || model.deleting ? {
			bounds: rect(12, 94, width - 24, Math.max(0, height - 180)),
			message: tr(model.deleting ? "Deleting selected objects…" : "Discovering dependencies…"),
			cancellable: !model.deleting
		} : null
	};
}
function target(record, width) {
	return { nodes: [node("Icon", "deleteTargetIcon", rect(0, 7, 14, 14), {
		icon: "sobject",
		color: "error"
	}), label("deleteTargetTitle", rect(22, 2, Math.max(0, width - 38), 26), record.title)] };
}
//#endregion
//#region src/features/objects/ObjectDependencyList.vue
var _hoisted_1$1 = { class: "object-dependencies-list" };
var _sfc_main$2 = {
	__name: "ObjectDependencyList",
	props: {
		models: Object,
		frameNode: Object
	},
	setup(__props) {
		const props = __props;
		const items = computed(() => (props.models[props.frameNode.source] || []).map((row) => ({
			key: row.searchKey,
			data: row,
			height: dependencyHeight(row)
		})));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$1, [createVNode(_sfc_main$23, { items: items.value }, {
				default: withCtx(({ item }) => [createVNode(_sfc_main$18, {
					scene: dependency(item, __props.frameNode.width),
					style: normalizeStyle({ height: dependencyHeight(item) + "px" })
				}, null, 8, ["scene", "style"])]),
				_: 1
			}, 8, ["items"])]);
		};
	}
};
//#endregion
//#region src/features/objects/ObjectAction.vue
var _sfc_main = {
	components: {
		AppButton: _sfc_main$16,
		ObjectDeleteSurface: {
			__name: "ObjectDeleteSurface",
			props: { model: Object },
			emits: ["event"],
			setup(__props, { emit: __emit }) {
				const props = __props;
				const emit = __emit;
				const host = ref(null), size = ref({
					width: 0,
					height: 0
				});
				const models$1 = computed(() => models(props.model, appearance.language));
				const views = computed(() => ({ dependencies: {
					component: _sfc_main$2,
					nodeProps: true,
					props: { models: models$1.value }
				} }));
				let observer;
				const scene = computed(() => describe(props.model, size.value.width, size.value.height, appearance.language));
				onMounted(() => {
					const measure = () => {
						size.value = {
							width: host.value.clientWidth,
							height: host.value.clientHeight
						};
					};
					measure();
					observer = observeFrameSizes(measure);
					observer.observe(host.value);
				});
				onBeforeUnmount(() => observer?.disconnect());
				return (_ctx, _cache) => {
					return openBlock(), createElementBlock("section", {
						ref_key: "host",
						ref: host,
						class: "object-delete-surface"
					}, [createVNode(_sfc_main$18, {
						scene: scene.value,
						models: models$1.value,
						views: views.value,
						"describe-row": (list, record) => list.id === "deleteSObjectTargets" ? target(record, list.width - 16) : dependency(record, list.width - 16),
						onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
					}, null, 8, [
						"scene",
						"models",
						"views",
						"describe-row"
					]), scene.value.loading ? (openBlock(), createBlock(_sfc_main$24, {
						key: 0,
						message: scene.value.loading.message,
						cancellable: scene.value.loading.cancellable,
						style: normalizeStyle({
							left: scene.value.loading.bounds.x + "px",
							top: scene.value.loading.bounds.y + "px",
							width: scene.value.loading.bounds.width + "px",
							height: scene.value.loading.bounds.height + "px"
						}),
						onCancel: _cache[1] || (_cache[1] = ($event) => emit("event", { type: "cancel" }))
					}, null, 8, [
						"message",
						"cancellable",
						"style"
					])) : createCommentVNode("", true)], 512);
				};
			}
		}
	},
	inject: { openHelp: { default: null } },
	props: {
		ticket: String,
		project: String,
		searchType: String,
		view: String
	},
	emits: ["saved"],
	data() {
		return {
			record: null,
			records: [],
			operation: "",
			context: null,
			groups: [],
			selected: [],
			ready: false,
			loading: false,
			saving: false,
			error: "",
			uncertain: false,
			request: 0
		};
	},
	computed: {
		title() {
			return {
				retire: "Retire record",
				reactivate: "Reactivate record",
				delete: "Delete record"
			}[this.operation] || "Object actions";
		},
		deleteModel() {
			return {
				targetCount: this.records.length,
				targets: this.records.map((record) => ({
					title: record.name || record.title || record.code || String(record.id),
					searchKey: record.__search_key__
				})),
				ready: this.ready,
				busy: this.loading,
				deleting: this.saving,
				error: this.error,
				uncertain: this.uncertain,
				groups: this.groups.map((group) => ({
					searchType: group.search_type,
					searchTypeTitle: group.title,
					iconName: {
						"sthpw/snapshot": "snapshot",
						"sthpw/note": "notes",
						"sthpw/task": "tasks",
						"sthpw/status_log": "history"
					}[group.search_type] || "sobject",
					count: group.count,
					checked: this.selected.includes(group.search_type),
					defaultChecked: group.selected,
					expanded: !!group.expanded,
					items: group.items || []
				}))
			};
		}
	},
	watch: {
		ticket() {
			this.invalidate();
		},
		project() {
			this.invalidate();
		},
		searchType() {
			this.invalidate();
		},
		view() {
			this.invalidate();
		}
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
	},
	beforeUnmount() {
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
		deleteEvent(event) {
			if (event.type === "delete") this.apply();
			else if (event.type === "cancel") this.close();
			else if (event.type === "help") this.openHelp?.("deleting_objects");
			else if (event.type === "retry") this.loadDeletion();
			else if (event.type === "expand") this.groups[event.index].expanded = !this.groups[event.index].expanded;
			else if (event.type === "check") {
				const type = this.groups[event.index].search_type;
				this.selected = event.value ? [.../* @__PURE__ */ new Set([...this.selected, type])] : this.selected.filter((value) => value !== type);
			}
		},
		invalidate() {
			this.request++;
			this.uncertain = true;
			this.error = "Connection context changed. Close this form and reopen it before saving.";
		},
		beforeUnload(event) {
			if (this.saving || this.uncertain && this.$refs.dialog.open) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		close(event) {
			if (this.saving) {
				event?.preventDefault();
				return;
			}
			this.request++;
			this.$refs.dialog.close();
		},
		async open(record, operation) {
			if (this.$refs.dialog.open) return;
			++this.request;
			this.records = Array.isArray(record) ? [...record] : [record];
			if (!this.records.length) return;
			this.record = this.records[0];
			this.operation = operation;
			this.groups = [];
			this.selected = [];
			this.error = "";
			this.uncertain = false;
			this.ready = false;
			this.context = {
				ticket: this.ticket,
				project: this.project,
				searchType: this.searchType,
				view: this.view
			};
			this.loading = operation === "delete";
			this.$refs.dialog.showModal();
			if (!this.loading) return;
			await this.loadDeletion();
		},
		async loadDeletion() {
			if (this.saving || this.uncertain) return;
			const id = ++this.request;
			this.loading = true;
			this.ready = false;
			this.error = "";
			try {
				const context = this.context;
				const definition = await objectDeletion("read", context.ticket, context.project, context.searchType, context.view, this.records.map((record) => record.__search_key__));
				if (id !== this.request) return;
				this.groups = definition.groups;
				this.selected = definition.groups.filter((group) => group.selected).map((group) => group.search_type);
				this.ready = true;
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.loading = false;
			}
		},
		async apply() {
			if (this.loading || this.saving || this.uncertain || this.operation === "delete" && !this.ready) return;
			const id = this.request, context = this.context;
			this.saving = true;
			this.error = "";
			try {
				const keys = this.records.map((record) => record.__search_key__);
				if (this.operation === "delete") await objectDeletion("apply", context.ticket, context.project, context.searchType, context.view, keys, this.selected);
				else if (keys.length > 1) await objectStatus(context.ticket, context.project, context.searchType, context.view, keys, this.operation);
				else await rpc(this.operation === "retire" ? "retire_sobject" : "reactivate_sobject", [{
					ticket: context.ticket,
					project: context.project
				}, this.record.__search_key__]);
				if (id !== this.request) return;
				this.$refs.dialog.close();
				this.$emit("saved");
			} catch (error) {
				if (id !== this.request) return;
				this.error = error.message;
				this.uncertain = !error.status || error.status >= 500;
			} finally {
				this.saving = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { key: 1 };
var _hoisted_3 = {
	key: 2,
	class: "error",
	role: "alert"
};
var _hoisted_4 = {
	key: 3,
	class: "notice"
};
var _hoisted_5 = {
	key: 4,
	class: "configuration-actions"
};
var _hoisted_6 = ["disabled"];
var _hoisted_7 = ["disabled"];
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_ObjectDeleteSurface = resolveComponent("ObjectDeleteSurface");
	const _directive_window = resolveDirective("window");
	return withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: normalizeClass(["record-dialog object-action", { "object-deletion": $data.operation === "delete" }]),
		"aria-label": $options.t($options.title || "Object actions"),
		onCancel: _cache[2] || (_cache[2] = (...args) => $options.close && $options.close(...args))
	}, [
		createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.t($options.title)), 1), createBaseVNode("small", null, toDisplayString($data.record?.name || $data.record?.title || $data.record?.code || $data.record?.id), 1)]), createVNode(_component_AppButton, {
			label: "Close actions",
			icon: "close",
			"icon-only": "",
			disabled: $data.saving,
			onClick: $options.close
		}, null, 8, ["disabled", "onClick"])]),
		$data.operation === "delete" ? (openBlock(), createBlock(_component_ObjectDeleteSurface, {
			key: 0,
			model: $options.deleteModel,
			onEvent: $options.deleteEvent
		}, null, 8, ["model", "onEvent"])) : (openBlock(), createElementBlock("p", _hoisted_2, toDisplayString($options.t($data.operation === "retire" ? "Retiring keeps the data and hides the object from normal searches." : "Reactivating returns the object to normal searches.")), 1)),
		$data.error && $data.operation !== "delete" ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true),
		$data.uncertain ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString($options.t("This operation cannot be retried here. Close this dialog and refresh the data to check the result.")), 1)) : createCommentVNode("", true),
		$data.operation !== "delete" ? (openBlock(), createElementBlock("footer", _hoisted_5, [createBaseVNode("button", {
			type: "button",
			disabled: $data.saving,
			onClick: _cache[0] || (_cache[0] = (...args) => $options.close && $options.close(...args))
		}, toDisplayString($options.t("Cancel")), 9, _hoisted_6), createBaseVNode("button", {
			type: "button",
			class: normalizeClass($data.operation === "delete" ? "danger" : "primary"),
			disabled: $data.loading || $data.saving || $data.uncertain,
			onClick: _cache[1] || (_cache[1] = (...args) => $options.apply && $options.apply(...args))
		}, toDisplayString($options.t($data.saving ? "Applying…" : $options.title)), 11, _hoisted_7)])) : createCommentVNode("", true)
	], 42, _hoisted_1)), [[_directive_window, {
		kind: $data.operation === "delete" ? "delete_sobject" : "",
		type: "dialog"
	}]]);
}
var ObjectAction_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
//#region src/features/administration/columnsEditor.js
var displayWidgets = (/* @__PURE__ */ JSON.parse("[{\"value\":\"\",\"label\":\"Automatic\",\"class\":\"tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg\",\"aliases\":[\"TextWdg\",\"\",\"pyasm.widget.TextWdg\",\"tactic.ui.common.SimpleTableElementWdg\",\"tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg\",\"SimpleTableElementWdg\",\"pyasm.widget.SimpleTableElementWdg\",\"pyasm.widget.table_element_wdg.SimpleTableElementWdg\",\"pyasm.widget.input_wdg.TextWdg\"],\"adapter\":\"value\"},{\"value\":\"format\",\"label\":\"Format\",\"class\":\"tactic.ui.table.format_element_wdg.FormatElementWdg\",\"aliases\":[\"tactic.ui.table.FormatElementWdg\",\"tactic.ui.table.format_element_wdg.FormatElementWdg\"],\"adapter\":\"formatted\"},{\"value\":\"expression\",\"label\":\"Expression\",\"class\":\"tactic.ui.table.expression_element_wdg.ExpressionElementWdg\",\"aliases\":[\"tactic.ui.table.ExpressionElementWdg\",\"tactic.ui.table.expression_element_wdg.ExpressionElementWdg\"],\"adapter\":\"expression\"},{\"value\":\"link\",\"label\":\"Link\",\"class\":\"tactic.ui.table.link_element_wdg.LinkElementWdg\",\"aliases\":[\"tactic.ui.table.LinkElementWdg\",\"tactic.ui.table.link_element_wdg.LinkElementWdg\"],\"adapter\":\"link\"},{\"value\":\"pyasm.widget.ThumbWdg\",\"label\":\"Thumbnail\",\"class\":\"pyasm.widget.file_wdg.ThumbWdg\",\"aliases\":[\"ThumbWdg\",\"pyasm.widget.ThumbWdg\",\"pyasm.widget.file_wdg.ThumbWdg\"],\"adapter\":\"preview\"},{\"value\":\"tactic.ui.widget.DiscussionElementWdg\",\"label\":\"Notes\",\"class\":\"tactic.ui.widget.discussion_wdg.DiscussionElementWdg\",\"aliases\":[\"tactic.ui.widget.DiscussionElementWdg\",\"tactic.ui.widget.discussion_wdg.DiscussionElementWdg\"],\"adapter\":\"notes\"},{\"value\":\"tactic.ui.table.SObjectDetailElementWdg\",\"label\":\"SObject details\",\"class\":\"tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg\",\"aliases\":[\"tactic.ui.table.SObjectDetailElementWdg\",\"tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg\"],\"adapter\":\"details\"},{\"value\":\"tactic.ui.table.CheckinButtonElementWdg\",\"label\":\"Check-in\",\"class\":\"tactic.ui.table.table_element_wdg.CheckinButtonElementWdg\",\"aliases\":[\"tactic.ui.table.CheckinButtonElementWdg\",\"tactic.ui.table.table_element_wdg.CheckinButtonElementWdg\"],\"adapter\":\"checkin\"},{\"value\":\"tactic.ui.table.TaskElementWdg\",\"label\":\"Tasks\",\"class\":\"tactic.ui.table.task_element_wdg.TaskElementWdg\",\"aliases\":[\"tactic.ui.table.TaskElementWdg\",\"tactic.ui.table.task_element_wdg.TaskElementWdg\"],\"adapter\":\"tasks\"},{\"value\":\"tactic.ui.table.TaskCompletionWdg\",\"label\":\"Task completion\",\"class\":\"tactic.ui.table.statistic_wdg.TaskCompletionWdg\",\"aliases\":[\"tactic.ui.table.TaskCompletionWdg\",\"tactic.ui.table.statistic_wdg.TaskCompletionWdg\"],\"adapter\":\"completion\"},{\"value\":\"tactic.ui.table.ExploreElementWdg\",\"label\":\"Explorer\",\"class\":\"tactic.ui.table.explorer_wdg.ExplorerElementWdg\",\"aliases\":[\"tactic.ui.table.ExploreElementWdg\",\"tactic.ui.table.ExplorerElementWdg\",\"tactic.ui.table.explorer_wdg.ExplorerElementWdg\"],\"adapter\":\"explorer\"},{\"value\":\"tactic.ui.table.SObjectFilesElementWdg\",\"label\":\"Files\",\"class\":\"tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg\",\"aliases\":[\"tactic.ui.table.SObjectFilesElementWdg\",\"tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg\"],\"adapter\":\"files\"},{\"value\":\"tactic.ui.table.MetadataElementWdg\",\"label\":\"Metadata\",\"class\":\"tactic.ui.table.metadata_element_wdg.MetadataElementWdg\",\"aliases\":[\"tactic.ui.table.MetadataElementWdg\",\"tactic.ui.table.metadata_element_wdg.MetadataElementWdg\"],\"adapter\":\"metadata\"},{\"value\":\"tactic.ui.table.DeleteElementWdg\",\"label\":\"Delete\",\"class\":\"tactic.ui.table.delete_element_wdg.DeleteElementWdg\",\"aliases\":[\"tactic.ui.table.DeleteElementWdg\",\"tactic.ui.table.delete_element_wdg.DeleteElementWdg\"],\"adapter\":\"delete\"},{\"value\":\"ArrayTableElementWdg\",\"label\":\"Array\",\"class\":\"pyasm.widget.table_element_wdg.ArrayTableElementWdg\",\"aliases\":[\"ArrayTableElementWdg\",\"pyasm.widget.ArrayTableElementWdg\",\"pyasm.widget.table_element_wdg.ArrayTableElementWdg\"],\"adapter\":\"value\"},{\"value\":\"XmlWdg\",\"label\":\"XML\",\"class\":\"pyasm.widget.table_element_wdg.XmlWdg\",\"aliases\":[\"XmlWdg\",\"pyasm.widget.XmlWdg\",\"pyasm.widget.table_element_wdg.XmlWdg\"],\"adapter\":\"structured\"},{\"value\":\"tactic.ui.table.JsonElementWdg\",\"label\":\"JSON\",\"class\":\"tactic.ui.table.json_element_wdg.JsonElementWdg\",\"aliases\":[\"tactic.ui.table.JsonElementWdg\",\"tactic.ui.table.json_element_wdg.JsonElementWdg\"],\"adapter\":\"structured\"},{\"value\":\"tactic.ui.table.SnapshotInfoWdg\",\"label\":\"Parent\",\"class\":\"tactic.ui.table.snapshot_element_wdg.SnapshotInfoWdg\",\"aliases\":[\"tactic.ui.table.SnapshotInfoWdg\",\"tactic.ui.table.snapshot_element_wdg.SnapshotInfoWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.SnapshotVersionElementWdg\",\"label\":\"Snapshot version\",\"class\":\"tactic.ui.table.snapshot_element_wdg.SnapshotVersionElementWdg\",\"aliases\":[\"tactic.ui.table.SnapshotVersionElementWdg\",\"tactic.ui.table.snapshot_element_wdg.SnapshotVersionElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.SnapshotLockedElementWdg\",\"label\":\"Snapshot lock\",\"class\":\"tactic.ui.table.snapshot_element_wdg.SnapshotLockedElementWdg\",\"aliases\":[\"tactic.ui.table.SnapshotLockedElementWdg\",\"tactic.ui.table.snapshot_element_wdg.SnapshotLockedElementWdg\"],\"adapter\":\"lock\"},{\"value\":\"tactic.ui.table.SnapshotFileElementWdg\",\"label\":\"Snapshot file\",\"class\":\"tactic.ui.table.snapshot_element_wdg.SnapshotFileElementWdg\",\"aliases\":[\"tactic.ui.table.SnapshotFileElementWdg\",\"tactic.ui.table.snapshot_element_wdg.SnapshotFileElementWdg\"],\"adapter\":\"link\"},{\"value\":\"tactic.ui.table.MilestoneCompletionWdg\",\"label\":\"Milestone completion\",\"class\":\"tactic.ui.table.statistic_wdg.MilestoneCompletionWdg\",\"aliases\":[\"tactic.ui.table.MilestoneCompletionWdg\",\"tactic.ui.table.statistic_wdg.MilestoneCompletionWdg\"],\"adapter\":\"completion\"},{\"value\":\"tactic.ui.table.TaskGroupCompletionWdg\",\"label\":\"Task group completion\",\"class\":\"tactic.ui.table.statistic_wdg.TaskGroupCompletionWdg\",\"aliases\":[\"tactic.ui.table.TaskGroupCompletionWdg\",\"tactic.ui.table.statistic_wdg.TaskGroupCompletionWdg\"],\"adapter\":\"groupCompletion\"},{\"value\":\"tactic.ui.table.TaskDaysDueElementWdg\",\"label\":\"Days until due\",\"class\":\"tactic.ui.table.statistic_wdg.TaskDaysDueElementWdg\",\"aliases\":[\"tactic.ui.table.TaskDaysDueElementWdg\",\"tactic.ui.table.statistic_wdg.TaskDaysDueElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.SubContextElementWdg\",\"label\":\"Subcontext\",\"class\":\"tactic.ui.table.subcontext_wdg.SubContextElementWdg\",\"aliases\":[\"tactic.ui.table.SubContextElementWdg\",\"tactic.ui.table.subcontext_wdg.SubContextElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.TaskSummaryElementWdg\",\"label\":\"Task summary\",\"class\":\"tactic.ui.table.task_element_wdg.TaskSummaryElementWdg\",\"aliases\":[\"TaskSummaryElementWdg\",\"tactic.ui.table.TaskSummaryElementWdg\",\"tactic.ui.table.task_element_wdg.TaskSummaryElementWdg\"],\"adapter\":\"taskSummary\"},{\"value\":\"pyasm.widget.CheckboxColWdg\",\"label\":\"Row selection\",\"class\":\"pyasm.widget.table_element_wdg.CheckboxColWdg\",\"aliases\":[\"CheckboxColWdg\",\"pyasm.widget.CheckboxColWdg\",\"pyasm.widget.table_element_wdg.CheckboxColWdg\"],\"adapter\":\"selection\"},{\"value\":\"pyasm.widget.SearchTypeElementWdg\",\"label\":\"Search Type title\",\"class\":\"pyasm.widget.table_element_wdg.SearchTypeElementWdg\",\"aliases\":[\"SearchTypeElementWdg\",\"pyasm.widget.SearchTypeElementWdg\",\"pyasm.widget.table_element_wdg.SearchTypeElementWdg\"],\"adapter\":\"value\"},{\"value\":\"pyasm.widget.statistic_wdg.TaskCompletionWdg\",\"label\":\"Legacy task completion (integer)\",\"class\":\"pyasm.widget.statistic_wdg.TaskCompletionWdg\",\"aliases\":[\"pyasm.widget.statistic_wdg.TaskCompletionWdg\",\"pyasm.widget.TaskCompletionWdg\",\"TaskCompletionWdg\"],\"adapter\":\"completion\"},{\"value\":\"tactic.ui.app.search_type_element_wdg.SearchTypeHasTableElementWdg\",\"label\":\"Table availability\",\"class\":\"tactic.ui.app.search_type_element_wdg.SearchTypeHasTableElementWdg\",\"aliases\":[\"tactic.ui.app.SearchTypeHasTableElementWdg\",\"tactic.ui.app.search_type_element_wdg.SearchTypeHasTableElementWdg\"],\"adapter\":\"flag\"},{\"value\":\"tactic.ui.common.base_table_element_wdg.RawTableElementWdg\",\"label\":\"Raw value\",\"class\":\"tactic.ui.common.base_table_element_wdg.RawTableElementWdg\",\"aliases\":[\"tactic.ui.common.RawTableElementWdg\",\"tactic.ui.common.base_table_element_wdg.RawTableElementWdg\"],\"adapter\":\"raw\"},{\"value\":\"tactic.ui.table.explorer_wdg.ExplorerTableElementWdg\",\"label\":\"Folder\",\"class\":\"tactic.ui.table.explorer_wdg.ExplorerTableElementWdg\",\"aliases\":[\"tactic.ui.table.ExplorerTableElementWdg\"],\"adapter\":\"explorer\"},{\"value\":\"tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg\",\"label\":\"Expression value\",\"class\":\"tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg\",\"aliases\":[\"tactic.ui.table.ExpressionValueElementWdg\",\"tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg\"],\"adapter\":\"expression\"},{\"value\":\"tactic.ui.table.preference_wdg.PreferenceDescriptionWdg\",\"label\":\"Preference description\",\"class\":\"tactic.ui.table.preference_wdg.PreferenceDescriptionWdg\",\"aliases\":[\"tactic.ui.table.PreferenceDescriptionWdg\",\"tactic.ui.table.preference_wdg.PreferenceDescriptionWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.project_wdg.ProjectWdg\",\"label\":\"Project database\",\"class\":\"tactic.ui.table.project_wdg.ProjectWdg\",\"aliases\":[\"tactic.ui.table.ProjectWdg\",\"tactic.ui.table.project_wdg.ProjectWdg\"],\"adapter\":\"fields\"},{\"value\":\"tactic.ui.table.related_element_wdg.RelatedElementWdg\",\"label\":\"Related value\",\"class\":\"tactic.ui.table.related_element_wdg.RelatedElementWdg\",\"aliases\":[\"tactic.ui.table.RelatedElementWdg\",\"tactic.ui.table.related_element_wdg.RelatedElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.table_element_wdg.RecipientElementWdg\",\"label\":\"Notification recipients\",\"class\":\"tactic.ui.table.table_element_wdg.RecipientElementWdg\",\"aliases\":[\"tactic.ui.table.RecipientElementWdg\",\"tactic.ui.table.table_element_wdg.RecipientElementWdg\"],\"adapter\":\"fields\"},{\"value\":\"tactic.ui.widget.discussion_wdg.DiscussionWdg\",\"label\":\"Discussion\",\"class\":\"tactic.ui.widget.discussion_wdg.DiscussionWdg\",\"aliases\":[\"tactic.ui.widget.DiscussionWdg\",\"tactic.ui.widget.discussion_wdg.DiscussionWdg\"],\"adapter\":\"notes\"},{\"value\":\"pyasm.widget.discussion_wdg.DiscussionWdg\",\"label\":\"Legacy discussion\",\"class\":\"pyasm.widget.discussion_wdg.DiscussionWdg\",\"aliases\":[\"DiscussionWdg\",\"pyasm.widget.DiscussionWdg\",\"pyasm.widget.discussion_wdg.DiscussionWdg\"],\"adapter\":\"notes\"},{\"value\":\"pyasm.widget.task_wdg.SObjectTaskTableElement\",\"label\":\"Object tasks\",\"class\":\"pyasm.widget.task_wdg.SObjectTaskTableElement\",\"aliases\":[\"SObjectTaskTableElement\",\"pyasm.widget.SObjectTaskTableElement\",\"pyasm.widget.task_wdg.SObjectTaskTableElement\"],\"adapter\":\"tasks\"},{\"value\":\"pyasm.widget.task_wdg.TaskParentSpacingTableElement\",\"label\":\"Task context\",\"class\":\"pyasm.widget.task_wdg.TaskParentSpacingTableElement\",\"aliases\":[\"TaskParentSpacingTableElement\",\"pyasm.widget.TaskParentSpacingTableElement\",\"pyasm.widget.task_wdg.TaskParentSpacingTableElement\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.app.message_wdg.MessageTableElementWdg\",\"label\":\"Formatted message\",\"class\":\"tactic.ui.app.message_wdg.MessageTableElementWdg\",\"aliases\":[\"tactic.ui.app.MessageTableElementWdg\",\"tactic.ui.app.message_wdg.MessageTableElementWdg\"],\"adapter\":\"message\"},{\"value\":\"pyasm.widget.MyTacticSummaryWdg\",\"label\":\"My TACTIC summary\",\"class\":\"pyasm.widget.my_tactic_summary_wdg.MyTacticSummaryWdg\",\"aliases\":[\"MyTacticSummaryWdg\",\"pyasm.widget.MyTacticSummaryWdg\",\"pyasm.widget.my_tactic_summary_wdg.MyTacticSummaryWdg\"],\"adapter\":\"fields\"},{\"value\":\"pyasm.widget.UpdateWdg\",\"label\":\"Object actions\",\"class\":\"pyasm.widget.table_element_wdg.UpdateWdg\",\"aliases\":[\"UpdateWdg\",\"pyasm.widget.UpdateWdg\",\"pyasm.widget.table_element_wdg.UpdateWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.input.LoginTableElementWdg\",\"label\":\"Login\",\"class\":\"tactic.ui.input.process_group_select_wdg.LoginTableElementWdg\",\"aliases\":[\"tactic.ui.input.LoginTableElementWdg\",\"tactic.ui.input.process_group_select_wdg.LoginTableElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.panel.SecurityManagerButtonWdg\",\"label\":\"Global Permissions\",\"class\":\"tactic.ui.panel.security_manager_wdg.SecurityManagerButtonWdg\",\"aliases\":[\"tactic.ui.panel.SecurityManagerButtonWdg\",\"tactic.ui.panel.security_manager_wdg.SecurityManagerButtonWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.PreferenceEditWdg\",\"label\":\"User preference\",\"class\":\"tactic.ui.table.preference_wdg.PreferenceEditWdg\",\"aliases\":[\"tactic.ui.table.PreferenceEditWdg\",\"tactic.ui.table.preference_wdg.PreferenceEditWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.ProjectTemplateUpdateWdg\",\"label\":\"Update Template\",\"class\":\"tactic.ui.table.project_wdg.ProjectTemplateUpdateWdg\",\"aliases\":[\"tactic.ui.table.ProjectTemplateUpdateWdg\",\"tactic.ui.table.project_wdg.ProjectTemplateUpdateWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.NotificationTriggerElementWdg\",\"label\":\"Email Test\",\"class\":\"tactic.ui.table.table_element_wdg.NotificationTriggerElementWdg\",\"aliases\":[\"tactic.ui.table.NotificationTriggerElementWdg\",\"tactic.ui.table.table_element_wdg.NotificationTriggerElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.ButtonElementWdg\",\"label\":\"Configured button\",\"class\":\"tactic.ui.table.button_wdg.ButtonElementWdg\",\"aliases\":[\"tactic.ui.table.ButtonElementWdg\",\"tactic.ui.table.button_wdg.ButtonElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"ParallelStatusWdg\",\"label\":\"Parallel task status\",\"class\":\"pyasm.widget.parallel_status.ParallelStatusWdg\",\"aliases\":[\"ParallelStatusWdg\",\"pyasm.widget.ParallelStatusWdg\",\"pyasm.widget.parallel_status.ParallelStatusWdg\"],\"adapter\":\"commands\"},{\"value\":\"ParallelStatusEditWdg\",\"label\":\"Add Task\",\"class\":\"pyasm.widget.parallel_status.ParallelStatusEditWdg\",\"aliases\":[\"ParallelStatusEditWdg\",\"pyasm.widget.ParallelStatusEditWdg\",\"pyasm.widget.parallel_status.ParallelStatusEditWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.SObjectTaskStatusElementWdg\",\"label\":\"Open tasks\",\"class\":\"tactic.ui.table.sobject_detail_wdg.SObjectTaskStatusElementWdg\",\"aliases\":[\"tactic.ui.table.SObjectTaskStatusElementWdg\",\"tactic.ui.table.sobject_detail_wdg.SObjectTaskStatusElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.ProcessElementWdg\",\"label\":\"Process\",\"class\":\"tactic.ui.table.subcontext_wdg.ProcessElementWdg\",\"aliases\":[\"tactic.ui.table.ProcessElementWdg\",\"tactic.ui.table.subcontext_wdg.ProcessElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.widget.TaskStatusElementWdg\",\"label\":\"Task status\",\"class\":\"tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg\",\"aliases\":[\"tactic.ui.widget.TaskStatusElementWdg\",\"tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg\"],\"adapter\":\"value\"},{\"value\":\"tactic.ui.table.WorkElementWdg\",\"label\":\"Work on Task\",\"class\":\"tactic.ui.table.task_element_wdg.WorkElementWdg\",\"aliases\":[\"tactic.ui.table.WorkElementWdg\",\"tactic.ui.table.task_element_wdg.WorkElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.DropElementWdg\",\"label\":\"Instance links\",\"class\":\"tactic.ui.table.drop_element_wdg.DropElementWdg\",\"aliases\":[\"tactic.ui.table.DropElementWdg\",\"tactic.ui.table.drop_element_wdg.DropElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.CustomLayoutElementWdg\",\"label\":\"Custom Layout\",\"class\":\"tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg\",\"aliases\":[\"tactic.ui.table.CustomLayoutElementWdg\",\"tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg\",\"label\":\"Show related table\",\"class\":\"tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg\",\"aliases\":[\"tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg\",\"tactic.ui.table.HiddenRowElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg\",\"label\":\"Related tasks\",\"class\":\"tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg\",\"aliases\":[\"tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg\",\"tactic.ui.table.RowAddElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"HiddenRowToggleWdg\",\"label\":\"Show related table\",\"class\":\"pyasm.widget.table_element_wdg.HiddenRowToggleWdg\",\"aliases\":[\"HiddenRowToggleWdg\",\"pyasm.widget.table_element_wdg.HiddenRowToggleWdg\",\"pyasm.widget.HiddenRowToggleWdg\"],\"adapter\":\"commands\"},{\"value\":\"AuxDataWdg\",\"label\":\"Auxiliary data\",\"class\":\"pyasm.widget.table_element_wdg.AuxDataWdg\",\"aliases\":[\"AuxDataWdg\",\"pyasm.widget.table_element_wdg.AuxDataWdg\",\"pyasm.widget.AuxDataWdg\"],\"adapter\":\"value\"},{\"value\":\"GanttWdg\",\"label\":\"Gantt\",\"class\":\"pyasm.widget.gantt_wdg.GanttWdg\",\"aliases\":[\"GanttWdg\",\"pyasm.widget.gantt_wdg.GanttWdg\",\"pyasm.widget.GanttWdg\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.gantt_element_wdg.GanttElementWdg\",\"label\":\"Gantt\",\"class\":\"tactic.ui.table.gantt_element_wdg.GanttElementWdg\",\"aliases\":[\"tactic.ui.table.gantt_element_wdg.GanttElementWdg\",\"tactic.ui.table.GanttElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"TimecardInfoTableElement\",\"label\":\"Timecard\",\"class\":\"pyasm.widget.timecard_wdg.TimecardInfoTableElement\",\"aliases\":[\"TimecardInfoTableElement\",\"pyasm.widget.timecard_wdg.TimecardInfoTableElement\",\"pyasm.widget.TimecardInfoTableElement\"],\"adapter\":\"commands\"},{\"value\":\"WeekTableElement\",\"label\":\"Week\",\"class\":\"pyasm.widget.timecard_wdg.WeekTableElement\",\"aliases\":[\"WeekTableElement\",\"pyasm.widget.timecard_wdg.WeekTableElement\",\"pyasm.widget.WeekTableElement\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg\",\"label\":\"Work Hours\",\"class\":\"tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg\",\"aliases\":[\"tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg\",\"tactic.ui.table.WorkHoursElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"FileAppendLinkTableElement\",\"label\":\"Attach files\",\"class\":\"pyasm.widget.table_element_wdg.FileAppendLinkTableElement\",\"aliases\":[\"FileAppendLinkTableElement\",\"pyasm.widget.table_element_wdg.FileAppendLinkTableElement\",\"pyasm.widget.FileAppendLinkTableElement\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.CheckoutButtonElementWdg\",\"label\":\"Check out\",\"class\":\"tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg\",\"aliases\":[\"CheckoutButtonElementWdg\",\"tactic.ui.table.CheckoutButtonElementWdg\",\"tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"pyasm.widget.SObjectConnectionElement\",\"label\":\"Connections\",\"class\":\"pyasm.widget.sobject_browser_wdg.SObjectConnectionElement\",\"aliases\":[\"SObjectConnectionElement\",\"pyasm.widget.SObjectConnectionElement\",\"pyasm.widget.sobject_browser_wdg.SObjectConnectionElement\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg\",\"label\":\"Object summary\",\"class\":\"tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg\",\"aliases\":[\"tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg\",\"tactic.ui.table.SObjectSummaryElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"DependencyLink\",\"label\":\"Dependencies\",\"class\":\"pyasm.widget.dependency_wdg.DependencyLink\",\"aliases\":[\"DependencyLink\",\"pyasm.widget.DependencyLink\",\"pyasm.widget.dependency_wdg.DependencyLink\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.ParentGroupTableElementWdg\",\"label\":\"Parent group\",\"class\":\"tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg\",\"aliases\":[\"ParentGroupTableElementWdg\",\"tactic.ui.table.ParentGroupTableElementWdg\",\"tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"PublishTableElement\",\"label\":\"Publish\",\"class\":\"pyasm.widget.table_element_wdg.PublishTableElement\",\"aliases\":[\"PublishTableElement\",\"pyasm.widget.PublishTableElement\",\"pyasm.widget.table_element_wdg.PublishTableElement\"],\"adapter\":\"commands\"},{\"value\":\"tactic.ui.table.GeneralPublishElementWdg\",\"label\":\"General publish\",\"class\":\"tactic.ui.table.table_element_wdg.GeneralPublishElementWdg\",\"aliases\":[\"GeneralPublishElementWdg\",\"tactic.ui.table.GeneralPublishElementWdg\",\"tactic.ui.table.table_element_wdg.GeneralPublishElementWdg\"],\"adapter\":\"commands\"},{\"value\":\"WikiElementWdg\",\"label\":\"Multiline text\",\"class\":\"pyasm.widget.table_element_wdg.WikiElementWdg\",\"aliases\":[\"WikiElementWdg\",\"pyasm.widget.WikiElementWdg\",\"pyasm.widget.table_element_wdg.WikiElementWdg\"],\"adapter\":\"value\"}]")).map(({ value, label }) => ({
	value,
	label
}));
function parse(source) {
	if (/<!DOCTYPE|<!ENTITY/i.test(source)) throw new Error("Document types and XML entities are not supported");
	const document = new DOMParser().parseFromString(source.trim() || "<config/>", "application/xml");
	if (document.querySelector("parsererror")) throw new Error("Invalid configuration XML");
	return document;
}
function tableView(root, name) {
	return [root, ...root.children].find((node) => node.tagName === name || node.tagName === "view" && node.getAttribute("name") === name);
}
function tableDefinition(configuration, elements = configuration.resolved.elements) {
	const source = configuration.sources[0]?.xml || configuration.layers.find((layer) => layer.view === configuration.view)?.xml;
	const document = source ? parse(source) : parse("<config/>");
	const root = document.documentElement;
	let view = tableView(root, configuration.view);
	if (!view) {
		view = document.createElement(configuration.view.includes("@") ? "view" : configuration.view);
		if (view.tagName === "view") view.setAttribute("name", configuration.view);
		view.setAttribute("layout", "TableLayoutWdg");
		root.appendChild(view);
	}
	const nodes = new Map([...view.children].filter((node) => node.tagName === "element").map((node) => [node.getAttribute("name"), node]));
	for (const [index, element] of elements.entries()) if (!nodes.has(element.name)) {
		const node = document.createElement("element");
		node.setAttribute("name", element.name);
		for (const [key, value] of Object.entries(element.attributes || {})) node.setAttribute(key, String(value));
		const next = elements.slice(index + 1).map((element) => nodes.get(element.name)).find(Boolean);
		view.insertBefore(node, next || null);
		nodes.set(element.name, node);
	}
	return new XMLSerializer().serializeToString(document);
}
function changeTable(source, viewName, action, name, value) {
	const document = parse(source), root = document.documentElement;
	const view = tableView(root, viewName);
	if (!view) throw new Error("The current table view is missing.");
	const elements = [...view.children].filter((node) => node.tagName === "element");
	const node = elements.find((node) => node.getAttribute("name") === name);
	if (action === "copy") {
		const renamed = document.createElement(value.view);
		for (const attr of view.attributes) renamed.setAttribute(attr.name, attr.value);
		while (view.firstChild) renamed.appendChild(view.firstChild);
		if (root === view) {
			document.replaceChild(renamed, root);
			renamed.setAttribute("th_table_view_title", value.title);
		} else {
			view.replaceWith(renamed);
			root.setAttribute("th_table_view_title", value.title);
		}
	} else {
		if (!node) throw new Error("Definition XML path no longer points to a column.");
		if (action === "width") node.setAttribute("width", String(width(value)));
		else if (action === "hide") {
			if (elements.filter((node) => !flag(node.getAttribute("hidden"))).length <= 1) throw new Error("At least one column must remain visible");
			node.setAttribute("hidden", "true");
		} else if (action === "move") {
			const target = elements.find((node) => node.getAttribute("name") === value);
			if (!target) throw new Error("Definition XML path no longer points to a column.");
			view.insertBefore(node, elements.indexOf(node) < elements.indexOf(target) ? target.nextSibling : target);
		} else throw new Error("Unknown table operation");
	}
	return new XMLSerializer().serializeToString(document);
}
function children(node) {
	return [...node.childNodes].filter((child) => [
		1,
		7,
		8
	].includes(child.nodeType));
}
function width(value) {
	const number = String(value ?? "").trim().replace(/px$/, "");
	return /^[+-]?\d+$/.test(number) ? Math.max(48, Math.min(640, Number(number) || 160)) : 160;
}
function flag(value) {
	return [
		"1",
		"true",
		"yes",
		"on"
	].includes(String(value).trim().toLowerCase());
}
function definitionWizard(source, viewName = "") {
	const root = parse(source).documentElement;
	let view = null, viewPath = "";
	function find(node, path = "") {
		if (node.nodeType !== 1 || view) return;
		if (viewName ? node.tagName === viewName || node.tagName === "view" && node.getAttribute("name") === viewName : [
			"table",
			"definition",
			"edit",
			"edit_definition"
		].includes(node.tagName) || ["TableLayoutWdg", "tactic.ui.panel.TableLayoutWdg"].includes(node.getAttribute("layout"))) {
			view = node;
			viewPath = path;
			return;
		}
		children(node).forEach((child, index) => find(child, path ? `${path}/${index}` : String(index)));
	}
	find(root);
	const elements = view ? children(view).flatMap((node, index) => {
		if (node.nodeType !== 1 || node.tagName !== "element") return [];
		const display = [...node.children].find((child) => child.tagName === "display"), name = node.getAttribute("name") || "";
		return [{
			path: viewPath ? `${viewPath}/${index}` : String(index),
			name,
			title: node.getAttribute("title") || name,
			visible: !flag(node.getAttribute("hidden")),
			width: width(node.getAttribute("width")),
			...node.hasAttribute("value_icon") ? { valueIcon: node.getAttribute("value_icon") } : display?.querySelector("icon") ? { valueIcon: display.querySelector("icon").textContent } : {},
			...node.hasAttribute("value_style") ? { valueStyle: node.getAttribute("value_style") } : {},
			widget: display?.getAttribute("class") || display?.getAttribute("widget") || ""
		}];
	}) : [];
	return {
		supported: !!view,
		view: view?.tagName || "",
		layout: view?.getAttribute("layout") || "",
		elements
	};
}
function changeDefinition(source, path, field, value) {
	const document = parse(source);
	let node = document.documentElement, parent = null;
	for (const part of path.split("/").filter(Boolean)) {
		if (!/^\d+$/.test(part) || !children(node)[Number(part)]) throw new Error("Definition XML path no longer exists.");
		parent = node;
		node = children(node)[Number(part)];
	}
	if (node.tagName !== "element") throw new Error("Definition XML path no longer points to a column.");
	if (field === "move") {
		const offset = String(value);
		if (!["-1", "1"].includes(offset) || !parent) throw new Error("Invalid column move");
		const elements = [...parent.children].filter((child) => child.tagName === "element");
		const target = elements[elements.indexOf(node) + Number(offset)];
		if (!target) throw new Error("The column cannot be moved further.");
		parent.insertBefore(node, offset === "1" ? target.nextSibling : target);
	} else if (field === "title") {
		if (!String(value).trim()) throw new Error("Column label cannot be empty.");
		node.setAttribute("title", String(value).trim());
	} else if (field === "visible") node.setAttribute("hidden", value ? "false" : "true");
	else if (field === "width") node.setAttribute("width", String(width(value)));
	else if (field === "valueIcon" || field === "valueStyle") {
		const text = String(value || "").trim();
		if (field === "valueStyle" && ![
			"",
			"text",
			"badge"
		].includes(text)) throw new Error("Invalid value appearance");
		if (field === "valueIcon" && (text.length > 128 || !/^[\w:.-]*$/.test(text))) throw new Error("Invalid icon name");
		node.setAttribute(field === "valueIcon" ? "value_icon" : "value_style", text);
	} else if (field === "widget") {
		let display = [...node.children].find((child) => child.tagName === "display");
		if (!display) {
			display = document.createElement("display");
			node.appendChild(display);
		}
		display.removeAttribute("widget");
		display.removeAttribute("class");
		const widget = String(value || "").trim();
		if (widget) display.setAttribute(widget.includes(".") || widget.endsWith("Wdg") ? "class" : "widget", widget);
	} else throw new Error("This column setting is only available in XML mode.");
	return new XMLSerializer().serializeToString(document);
}
//#endregion
export { _sfc_main$13 as $, _sfc_main$7 as A, describe$4 as At, _sfc_main$10 as B, bubbleGeometry as C, edit as Ct, insertion as D, variants as Dt, formatFileSize as E, template as Et, toggle as F, buttonWidth as Ft, groupActions as G, defaultResultView as H, decorate as I, sortColumn as J, groups as K, itemScene as L, alignment as M, interrupted as Mt, roots as N, settled as Nt, mentionQuery as O, widgets as Ot, selected as P, actionLayout as Pt, _sfc_main$12 as Q, spacingField as R, bubbleContour as S, describe$3 as St, emojiCount as T, serialize as Tt, groupRecords as U, _sfc_main$11 as V, filterActions as W, viewActions as X, sorts as Y, views as Z, retainOlderMessages as _, describe$2 as _t, tableDefinition as a, row as at, _sfc_main$6 as b, actions as bt, attachmentName as c, _sfc_main$14 as ct, groupedMessages as d, RelatedObjects_default as default, dimensions as dt, MarkdownItCallable as et, initials as f, key as ft, messageId as g, actionAvailable as gt, messageDate as h, viewTabWidth as ht, displayWidgets as i, loaded as it, _sfc_main$8 as j, field as jt, popup as k, change as kt, canChangeMessage as l, _sfc_main$15 as lt, messageAttachments as m, tab as mt, changeTable as n, describe$1 as nt, ObjectAction_default as o, rows as ot, mergeMessages as p, sectionWidth as pt, sortActions as q, definitionWizard as r, initial as rt, _sfc_main$3 as s, transition as st, changeDefinition as t, choices$1 as tt, conversationAttachments as u, row$1 as ut, contextActions as v, supports as vt, composerKey as w, roles as wt, bodyOrder as x, binding as xt, _sfc_main$5 as y, visible as yt, _sfc_main$9 as z };

//# sourceMappingURL=RelatedObjects.js.map
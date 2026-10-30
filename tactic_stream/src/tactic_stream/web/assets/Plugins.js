import { A as onMounted, H as watch, K as withDirectives, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, nt as normalizeStyle, p as computed, s as vShow } from "./vue.js";
import { s as appearance } from "./AppButton.js";
import { K as uploadFormFile, k as rpc } from "./index.js";
import { B as node, L as button, R as label, V as rect, n as observeFrameSizes, r as _sfc_main$1, v as translate$1 } from "./resize.js";
import { wt as describe$2 } from "./ConfiguredView.js";
import { t as _sfc_main$2 } from "./PageEditorTools.js";
//#region ../src/tactic_stream/shared_ui/features/administration/plugins/plugins.resources.mjs
var russian$1 = {
	Resources: "Состав пакета",
	"Add resource": "Добавить ресурс",
	"Resource type": "Тип ресурса",
	"Resource name": "Имя ресурса",
	"Python action": "Python-действие",
	"Project data": "Данные проекта",
	"Search Type": "Тип объектов",
	"Record code (empty = all records)": "Код записи (пусто = все записи)",
	"Include table schema": "Включить схему таблицы",
	"Activate this package to edit its project resources. Inspect packaged files before activation.": "Активируйте пакет для редактирования его ресурсов в проекте. До активации проверьте файлы пакета.",
	"Add a widget, column, theme, Python action or selected project data.": "Добавьте виджет, колонку, тему, Python-действие или выбранные данные проекта.",
	Source: "Исходник",
	"Saved preview": "Предпросмотр сохранённого",
	"Save validates the resource, updates the project and exports it into the package.": "Сохранение проверяет ресурс, обновляет проект и экспортирует его в пакет.",
	"Apply theme to project": "Применить тему к проекту",
	"Use personal appearance": "Использовать личное оформление",
	"Theme style": "Стиль темы",
	"Light base": "Светлый фон",
	"Light accent": "Светлый акцент",
	"Dark base": "Тёмный фон",
	"Dark accent": "Тёмный акцент",
	"Install and removal hooks are Python files referenced by python path/undo_path in Manifest XML.": "Обработчики установки и удаления — Python-файлы, указанные в python path/undo_path в XML манифеста.",
	"Review data selection in Manifest XML before publishing. Removing the plugin removes its selected records.": "Перед публикацией проверьте выборку данных в XML манифеста. Удаление плагина удаляет выбранные записи.",
	"Resource added to this project and package.": "Ресурс добавлен в проект и пакет.",
	"Project theme applied. Personal appearance settings are preserved.": "Тема проекта применена. Личные настройки оформления сохранены.",
	"Personal appearance restored.": "Личное оформление восстановлено.",
	"Install/removal hooks": "Обработчики установки и удаления",
	"Run Python action": "Выполнить Python-действие",
	"Arguments (JSON object)": "Аргументы (JSON-объект)",
	"Run this trusted server Python action? It may modify project data.": "Выполнить этот доверенный Python-код на сервере? Он может изменить данные проекта.",
	"Action result": "Результат действия",
	Schema: "Схема",
	Script: "Скрипт",
	Configuration: "Конфигурация"
};
var names = {
	widget: "Widget",
	column: "Column",
	theme: "Theme",
	python: "Python action",
	script: "Script",
	data: "Project data",
	hooks: "Install/removal hooks"
};
var icons = {
	widget: "extension",
	column: "view-column",
	theme: "appearance",
	python: "code",
	script: "code",
	data: "table-view",
	search_type: "table-view",
	include: "code",
	plugin: "extension"
};
function row$1(list, entry, model, tr) {
	const w = Math.max(0, list.width - 16);
	return { nodes: [
		node("Box", "pluginResourceBackground", rect(0, 0, w, 48), {
			background: model.document?.resource?.key === entry.key ? "contentSelection" : "transparent",
			radius: 0
		}),
		node("Icon", "pluginResourceIcon", rect(8, 10, 24, 24), { icon: icons[entry.kind] || "settings" }),
		label("pluginResourceTitle", rect(44, 0, w - 48, 24), entry.title, { weight: 600 }),
		label("pluginResourceKind", rect(44, 24, w - 48, 22), tr(names[entry.kind] || {
			search_type: "Schema",
			configuration: "Configuration"
		}[entry.kind] || entry.kind) + (entry.searchType ? " · " + entry.searchType : "") + (entry.count === void 0 ? "" : " · " + entry.count), {
			color: "secondaryText",
			fontRole: "secondary"
		}),
		node("Action", "pluginResourceSelect", rect(0, 0, w, 48), {
			text: entry.title,
			selected: model.document?.resource?.key === entry.key,
			enabled: !model.busy && !!(entry.field || entry.path),
			action: entry.field ? {
				type: "resource",
				key: entry.key
			} : {
				type: "file",
				path: entry.path,
				directory: false
			}
		})
	] };
}
function themeSource(source, field, value) {
	const parts = field.split("_"), mode = field === "style" ? "theme" : parts[0], key = field === "style" ? "style" : parts[1];
	return source.replace(new RegExp("<" + mode + "\\b[^>]*>"), (tag) => tag.replace(new RegExp("(\\b" + key + "\\s*=\\s*)([\"'])(.*?)\\2"), (_, prefix, quote) => prefix + quote + value + quote));
}
function describe$1(model, ui, width, height, language, tr) {
	const nodes = [], meta = model.metadata || {}, resource = model.document?.resource, writable = model.canWrite && !model.busy && !model.uncertain, clean = !model.busy && !model.uncertain && !model.dirty;
	let y = 0;
	const text = (id, value, h = 44) => {
		nodes.push(label(id, rect(0, y, width, h), tr(value), {
			wrap: true,
			color: "secondaryText"
		}));
		y += h + 8;
	};
	const action = (id, title, icon, event, enabled = clean) => button(id, rect(0, 0, width, 36), tr(title), icon, event, enabled);
	if (!meta.active) {
		text("pluginInactiveResources", "Activate this package to edit its project resources. Inspect packaged files before activation.", 72);
		return {
			nodes,
			height: y
		};
	}
	const add = action("pluginAddResource", "Add resource", "add", { type: "resource-add" }, clean && model.canWrite);
	add.width = Math.min(240, width);
	nodes.push(add);
	y += 44;
	if (ui.resourceAdd) {
		const input = (field, title, options = null) => {
			nodes.push(label("pluginResourceLabel_" + field, rect(0, y, width, 24), tr(title)));
			y += 28;
			nodes.push(node(options ? "Choice" : "Field", "pluginResourceInput_" + field, rect(0, y, width, 40), Object.assign({
				label: tr(title),
				action: {
					type: "input",
					field
				},
				enabled: !model.busy
			}, options ? {
				value: ui[field],
				options
			} : { text: ui[field] || "" })));
			y += 48;
		};
		input("resourceKind", "Resource type", Object.keys(names).map((value) => ({
			value,
			label: tr(names[value])
		})));
		input("resourceName", "Resource name");
		if (ui.resourceKind === "data") {
			input("resourceType", "Search Type", meta.dataTypes || []);
			input("resourceCode", "Record code (empty = all records)");
			nodes.push(node("CheckBox", "pluginResourceSchema", rect(0, y, width, 36), {
				text: tr("Include table schema"),
				checked: ui.resourceSchema,
				action: {
					type: "input",
					field: "resourceSchema"
				}
			}));
			y += 44;
			text("pluginDataRemovalHint", "Review data selection in Manifest XML before publishing. Removing the plugin removes its selected records.", 60);
		}
		const create = action("pluginResourceCreate", "Add resource", "add", { type: "resource-create" }, clean && !!ui.resourceName?.trim() && (ui.resourceKind !== "data" || !!ui.resourceType));
		create.y = y;
		create.width = Math.min(width / 2 - 4, 240);
		nodes.push(create);
		const cancel = action("pluginResourceCancel", "Cancel", "close", { type: "resource-cancel" }, !model.busy);
		cancel.x = create.width + 8;
		cancel.y = y;
		cancel.width = Math.min(width - create.width - 8, 160);
		nodes.push(cancel);
		y += 48;
	}
	text("pluginResourceHint", "Add a widget, column, theme, Python action or selected project data.");
	const wide = width >= 700, listTop = y, listHeight = wide ? Math.max(240, height - y - 16) : 192, editorStart = nodes.length + 1;
	nodes.push(node("List", "pluginResources", rect(0, y, wide ? 240 : width, listHeight), {
		source: "pluginResources",
		keyField: "key",
		fields: [
			"key",
			"kind",
			"title",
			"searchType",
			"field",
			"path",
			"count"
		],
		rowHeight: 48,
		scrollbarId: "pluginResourceScroll",
		scrollbarReserved: 16,
		label: tr("Resources"),
		resetKey: model.identity
	}));
	if (wide) width -= 252;
	else y += 204;
	if (resource) {
		nodes.push(label("pluginResourceSelected", rect(0, y, width, 28), resource.title, { weight: 600 }));
		y += 36;
		if (resource.validationError) {
			nodes.push(label("pluginResourceValidation", rect(0, y, width, 64), resource.validationError, {
				wrap: true,
				color: "error"
			}));
			y += 72;
		}
		if (resource.kind === "python") {
			nodes.push(label("pluginPythonInputsLabel", rect(0, y, width, 24), tr("Arguments (JSON object)")));
			y += 28;
			nodes.push(node("Area", "pluginPythonInputs", rect(0, y, width, 76), {
				text: ui.resourceArguments || "{}",
				enabled: !model.busy,
				action: {
					type: "input",
					field: "resourceArguments"
				}
			}));
			y += 84;
			const run = action("pluginPythonRun", "Run Python action", "play-arrow", {
				type: "operation",
				action: "run_resource"
			});
			run.y = y;
			nodes.push(run);
			y += 44;
			if (meta.runResult !== void 0) {
				text("pluginPythonResultLabel", "Action result", 24);
				nodes.push(label("pluginPythonResult", rect(0, y, width, 100), JSON.stringify(meta.runResult, null, 2), { wrap: true }));
				y += 108;
			}
		}
		if (resource.kind === "theme" && resource.palette) {
			for (const [id, title, icon, operation] of [[
				"pluginApplyTheme",
				"Apply theme to project",
				"palette",
				"apply_theme"
			], [
				"pluginResetTheme",
				"Use personal appearance",
				"reset",
				"reset_theme"
			]]) {
				const b = action(id, title, icon, {
					type: "run",
					action: operation,
					values: { resource: resource.key }
				});
				b.y = y;
				nodes.push(b);
				y += 44;
			}
			nodes.push(node("Choice", "pluginThemeStyle", rect(0, y, width, 40), {
				label: tr("Theme style"),
				value: resource.palette?.style || "md3",
				enabled: writable,
				options: [
					"md3",
					"material5",
					"fluent"
				].map((value) => ({
					value,
					label: value
				})),
				action: {
					type: "resource-theme",
					field: "style"
				}
			}));
			y += 48;
			for (const mode of ["light", "dark"]) for (const color of ["base", "accent"]) {
				const field = mode + "_" + color, title = (mode === "light" ? "Light" : "Dark") + " " + color;
				nodes.push(label("pluginThemeLabel_" + field, rect(0, y, width, 24), tr(title)));
				y += 28;
				nodes.push(node("ColorChoice", "pluginTheme_" + field, rect(0, y, Math.min(width, 400), 40), {
					label: tr(title),
					value: resource.palette?.[mode]?.[color] || "",
					enabled: writable,
					action: {
						type: "resource-theme",
						field
					}
				}));
				y += 48;
			}
		}
		if (resource.layout) {
			nodes.push(node("Segmented", "pluginResourceMode", rect(0, y, width, 36), {
				label: tr("Resources"),
				value: ui.resourceMode,
				options: ["source", "preview"].map((value) => ({
					value,
					label: tr(value === "source" ? "Source" : "Saved preview")
				})),
				action: {
					type: "input",
					field: "resourceMode"
				}
			}));
			y += 44;
		}
		if (resource.layout && ui.resourceMode === "preview") {
			const previewWidth = Math.min(width, resource.kind === "column" ? 320 : 480);
			const scene = describe$2(resource.layout, resource.sample, previewWidth, "", language, width, "", "pluginResourcePreview", 0, true);
			nodes.push(node("Box", "pluginResourcePreview", rect(0, y, width, scene.height), { children: scene.nodes }));
			y += scene.height + 12;
		} else {
			text("pluginResourceSaveHint", "Save validates the resource, updates the project and exports it into the package.", 52);
			const h = Math.max(300, height - y);
			nodes.push(node("Code", "pluginResourceSource", rect(0, y, width, h), {
				text: resource.source,
				syntax: resource.field === "script" ? resource.kind === "python" ? "python" : "javascript" : "xml",
				language,
				service: "sourceEditor",
				bufferKey: model.identity + ":" + resource.key,
				readOnly: !writable,
				action: {
					type: "field",
					field: "resource_source"
				}
			}));
			y += h + 12;
		}
	} else text("pluginHooksHint", "Install and removal hooks are Python files referenced by python path/undo_path in Manifest XML.", 56);
	if (wide) {
		for (const child of nodes.slice(editorStart)) child.x += 252;
		y = Math.max(y, listTop + listHeight);
	}
	return {
		nodes,
		height: y
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/plugins/plugins.state.mjs
function initial() {
	return {
		query: "",
		activeOnly: false,
		tab: "info",
		operation: "",
		value: "",
		url: "",
		checksum: "",
		collapsed: false,
		source: "zip",
		notice: "",
		resourceAdd: false,
		resourceKind: "widget",
		resourceName: "",
		resourceType: "",
		resourceCode: "",
		resourceSchema: false,
		resourceMode: "source"
	};
}
var destructive = {
	run_resource: "Run this trusted server Python action? It may modify project data.",
	activate: "Activate this package in the selected project? Its manifest can create or update project data and run server code.",
	replace_file: "Replace the selected file with a local upload?",
	reload_catalog: "Discard unsaved changes and reload the plugin catalogue?",
	reload: "Reload removes and reinstalls the plugin in this project. Its data may be replaced.",
	deactivate: "Remove this plugin and its manifest-defined data from the current project?",
	clean: "Clean all project entries described by this plugin manifest?",
	delete: "Delete this package from the server? It must be inactive in every project.",
	delete_file: "Delete the selected plugin file or folder and its contents?",
	clear_spt: "Delete all generated .spt files in this package?"
};
function catalog(model, ui) {
	const query = ui.query.trim().toLowerCase();
	return (model.catalog || []).filter((row) => (!ui.activeOnly || row.active) && (!query || [
		row.code,
		row.title,
		row.path
	].join(" ").toLowerCase().includes(query)));
}
var parent$1 = (path) => path.split("/").slice(0, -1).join("/");
function transition(ui, model, event) {
	if (event.type === "reset") return {
		ui: initial(),
		commands: []
	};
	const next = Object.assign({}, ui), commands = [], request = (action, values = {}) => commands.push({
		type: "request",
		action,
		values
	}), blocked = model.busy || model.uncertain, clean = () => {
		if (model.dirty || model.uncertain) {
			commands.push({
				type: "error",
				value: "Apply or discard unsaved changes first"
			});
			return false;
		}
		return !model.busy;
	};
	if (event.type === "completed") {
		next.notice = {
			add_resource: "Resource added to this project and package.",
			apply_theme: "Project theme applied. Personal appearance settings are preserved.",
			reset_theme: "Personal appearance restored.",
			install: "Package added. Review its contents, then activate it in this project.",
			download_url: "Package added. Review its contents, then activate it in this project.",
			create: model.metadata?.active ? "Plugin created and active in this project. Add files and configure its manifest." : model.identity ? "Package added. Review its contents, then activate it in this project." : "Package exported. Check your downloads.",
			activate: "Plugin is now active in this project.",
			deactivate: "Plugin removed from this project. The package remains on the server.",
			save: model.metadata?.active && !model.document?.file && !model.document?.resource ? "Changes saved. Reload the plugin to apply manifest changes to this project." : "Changes saved.",
			export: "Package exported. Check your downloads.",
			publish: "Version published. Review the new release before activating it."
		}[event.action] || "";
		if (event.action === "add_resource") next.resourceAdd = false;
		if ([
			"list",
			"new",
			"install",
			"download_url",
			"create",
			"publish",
			"delete"
		].includes(event.action)) {
			next.operation = "";
			next.tab = "info";
		}
	} else if (event.type === "help") commands.push({
		type: "help",
		topic: "plugins"
	});
	else if (event.type === "query") next.query = event.value;
	else if (event.type === "activeOnly") next.activeOnly = event.value;
	else if (event.type === "collapse") next.collapsed = !ui.collapsed;
	else if (event.type === "input") next[event.field] = event.value;
	else if (event.type === "resource-add" && clean()) {
		next.resourceAdd = true;
		next.resourceName = "";
	} else if (event.type === "resource-cancel" && !model.busy) next.resourceAdd = false;
	else if (event.type === "resource-create" && clean()) request("add_resource", { values: {
		kind: ui.resourceKind,
		name: ui.resourceName,
		searchType: ui.resourceType,
		code: ui.resourceCode,
		schema: ui.resourceSchema
	} });
	else if (event.type === "resource" && clean()) {
		next.resourceMode = "source";
		request("open_resource", { resource: event.key });
	} else if (event.type === "resource-theme" && !blocked && model.canWrite && model.document?.resource?.kind === "theme" && model.document.resource.palette) {
		const resource = model.document.resource, palette = JSON.parse(JSON.stringify(resource.palette));
		if (event.field === "style") palette.style = event.value;
		else {
			const parts = event.field.split("_");
			palette[parts[0]][parts[1]] = event.value;
		}
		commands.push({
			type: "field",
			field: "resource_source",
			value: themeSource(resource.source, event.field, event.value)
		}, {
			type: "field",
			field: "resource_palette",
			value: palette
		});
	} else if (event.type === "field" && !blocked && model.canWrite) commands.push(event);
	else if (event.type === "select" && clean()) {
		next.operation = "";
		next.notice = "";
		next.tab = "info";
		commands.push(event);
	} else if (event.type === "tab" && clean()) {
		next.tab = event.value;
		next.operation = "";
		next.notice = "";
		if (event.value === "resources") {
			const first = model.metadata?.resources?.find((item) => item.field);
			if (first) {
				next.resourceMode = "preview";
				request("open_resource", { resource: first.key });
			}
		} else if (event.value === "docs") {
			if (model.metadata.docsExist) request("open_file", { file: model.metadata.docs });
		} else if (model.document?.file || model.document?.resource) request("load");
	} else if (event.type === "reload" && !model.busy) {
		if (model.dirty) next.operation = "reload_catalog";
		else {
			commands.push({ type: "discard" });
			request("list");
		}
	} else if (event.type === "discard" && !model.busy) commands.push(event);
	else if (event.type === "save" && !blocked && (!model.metadata?.new || canCreate(model))) commands.push(event);
	else if (event.type === "new" && clean()) {
		next.operation = "";
		next.notice = "";
		next.tab = "info";
		request("new");
	} else if (event.type === "install" && clean()) {
		next.operation = "install";
		next.notice = "";
		next.source = "zip";
		next.url = "";
		next.checksum = "";
	} else if (event.type === "file" && clean()) {
		next.tab = "files";
		next.operation = "";
		next.notice = "";
		request(event.directory ? "browse" : "open_file", event.directory ? { folder: event.path } : {
			file: event.path,
			folder: model.metadata.folder || ""
		});
	} else if (event.type === "docs_create" && clean()) {
		next.tab = "docs";
		request("new_file", { path: model.metadata.docs });
	} else if (event.type === "upload" && clean()) commands.push(event);
	else if (event.type === "operation" && clean()) {
		next.operation = event.action;
		next.notice = "";
		next.value = event.action === "rename" ? model.document?.file?.path || model.metadata.folder || "" : "";
	} else if (event.type === "cancel" && !model.busy) {
		next.operation = "";
		if (model.metadata?.new) commands.push({ type: "discard" });
	} else if (event.type === "confirm" && ui.operation === "reload_catalog" && !model.busy) {
		commands.push({ type: "discard" });
		request("list");
		next.operation = "";
	} else if (event.type === "confirm" && clean()) {
		const action = ui.operation, values = { confirmation: true };
		if (action === "replace_file") commands.push({
			type: "upload",
			package: false,
			replace: true
		});
		else if (action === "install") {
			values.url = ui.url;
			values.checksum = ui.checksum;
			request("download_url", values);
		} else {
			const selected = model.document?.file?.path || model.metadata.folder || "";
			if (["new_file", "new_folder"].includes(action)) values.path = [model.metadata.folder, ui.value].filter(Boolean).join("/");
			if (action === "publish") values.version = ui.value;
			if (action === "run_resource") {
				values.resource = model.document?.resource?.key;
				values.inputs = ui.resourceArguments || "{}";
			}
			if (action === "rename") {
				values.path = selected;
				values.destination = ui.value;
			}
			if (action === "delete_file") values.path = selected;
			if (action === "delete_file" || action === "rename") values.folder = parent$1(selected);
			request(action, values);
		}
		if (action !== "install") next.operation = "";
	} else if (event.type === "run" && clean()) request(event.action, event.values || {});
	return {
		ui: next,
		commands
	};
}
function canCreate(model) {
	const doc = model.document || {};
	return doc.type === "project" || !!(doc.title?.trim() && doc.code?.trim());
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/plugins/plugins.guide.mjs
function steps(width, stage, tr) {
	const narrow = width < 600, row = narrow ? 38 : 0;
	return {
		nodes: [
			"Choose a package",
			"Review its contents",
			"Activate in project"
		].map((text, index) => label("pluginStep_" + index, rect(narrow ? 0 : index * width / 3, index * row, narrow ? width : width / 3 - 8, 30), index + 1 + "  " + tr(text), {
			weight: index === stage ? 600 : 400,
			color: index === stage ? "primaryText" : "secondaryText"
		})),
		height: narrow ? 118 : 42
	};
}
function start(width, ready, tr) {
	const nodes = [], w = Math.min(width, 1120), stacked = w < 720;
	nodes.push(label("pluginWelcomeTitle", rect(0, 0, w, 32), tr("Add capabilities to your project"), {
		fontRole: "title",
		weight: 600
	}));
	nodes.push(label("pluginWelcomeIntro", rect(0, 40, w, 50), tr("Install a ready-made package or create your own. A package lives on the server; activation applies it to the selected project."), {
		wrap: true,
		color: "secondaryText"
	}));
	const progress = steps(w, 0, tr);
	progress.nodes.forEach((item) => {
		item.y += 100;
		nodes.push(item);
	});
	const y = 100 + progress.height + 12, cardWidth = stacked ? w : (w - 16) / 2, cardHeight = 208;
	for (const [index, title, description, icon, action, id] of [[
		0,
		"Install a package",
		"Have a plugin ZIP or download link? Upload it, review the manifest and documentation, then activate it in this project.",
		"upload",
		"install",
		"pluginEmptyInstall"
	], [
		1,
		"Create your own plugin",
		"Start with an empty package or a Widget, Column or Theme template. Add files and project data, then publish a version.",
		"add",
		"new",
		"pluginEmptyNew"
	]]) {
		const x = stacked ? 0 : index * (cardWidth + 16), top = y + (stacked ? index * 220 : 0);
		nodes.push(node("Box", "pluginStartCard_" + index, rect(x, top, cardWidth, cardHeight), {
			background: "surfaceContainer",
			border: "outlineVariant",
			radius: 8,
			children: [
				node("Icon", "pluginStartIcon_" + index, rect(16, 16, 24, 24), { icon }),
				label("pluginStartTitle_" + index, rect(52, 12, cardWidth - 68, 32), tr(title), { weight: 600 }),
				label("pluginStartDescription_" + index, rect(16, 56, cardWidth - 32, 88), tr(description), {
					wrap: true,
					color: "secondaryText"
				}),
				button(id, rect(16, 156, cardWidth - 32, 36), tr(title), icon, { type: action }, ready, { highlighted: index === 0 })
			]
		}));
	}
	const bottom = y + (stacked ? 428 : cardHeight) + 20;
	nodes.push(button("pluginStartHelp", rect(0, bottom, Math.min(300, w), 36), tr("Plugin guide"), "help", { type: "help" }, true));
	return {
		nodes,
		height: bottom + 48
	};
}
function installation(ui, width, ready, tr) {
	const nodes = [], progress = steps(width, 0, tr);
	progress.nodes.forEach((item) => nodes.push(item));
	let y = progress.height + 8;
	nodes.push(label("pluginInstallNotice", rect(0, y, width, 58), tr("First add the package to this server. Nothing is activated in your project until you review and confirm the next step."), {
		wrap: true,
		color: "secondaryText"
	}));
	y += 70;
	nodes.push(node("Segmented", "pluginInstallSource", rect(0, y, width, 36), {
		label: tr("Package source"),
		value: ui.source,
		options: [{
			value: "zip",
			label: tr("ZIP file")
		}, {
			value: "url",
			label: tr("Download link")
		}],
		action: {
			type: "input",
			field: "source"
		},
		enabled: ready
	}));
	y += 52;
	if (ui.source === "zip") {
		nodes.push(label("pluginZipInstructions", rect(0, y, width, 62), tr("Choose a ZIP containing manifest.xml and the plugin files. The file is uploaded from this computer to the selected server."), { wrap: true }));
		y += 74;
		nodes.push(button("pluginBrowseZip", rect(0, y, Math.min(300, width), 40), tr("Choose ZIP and upload"), "folder", {
			type: "upload",
			package: true
		}, ready, { highlighted: true }));
		y += 52;
	} else {
		nodes.push(label("pluginUrlInstructions", rect(0, y, width, 56), tr("The server downloads the ZIP from this address. Add a checksum if the publisher provides one."), { wrap: true }));
		y += 68;
		for (const [field, title] of [["url", "Plugin ZIP URL"], ["checksum", "SHA-256 or MD5 (optional)"]]) {
			nodes.push(label("pluginInstallLabel_" + field, rect(0, y, width, 24), tr(title)));
			y += 28;
			nodes.push(node("Field", "pluginInstall_" + field, rect(0, y, width, 40), {
				label: tr(title),
				text: ui[field],
				placeholder: field === "url" ? "https://example.org/plugin.zip" : "",
				action: {
					type: "input",
					field
				},
				enabled: ready
			}));
			y += 52;
		}
		nodes.push(button("pluginConfirm", rect(0, y, Math.min(300, width), 40), tr("Download package"), "download", { type: "confirm" }, ready && !!ui.url.trim(), { highlighted: true }));
		y += 52;
	}
	return {
		nodes,
		height: y
	};
}
function project(model, width, tr) {
	const meta = model.metadata || {}, nodes = [], compact = width < 620;
	const progress = steps(width, meta.active ? 2 : 1, tr);
	progress.nodes.forEach((item) => nodes.push(item));
	let y = progress.height + 8;
	const lineHeight = compact ? 78 : 54;
	nodes.push(node("Box", "pluginProjectState", rect(0, y, width, lineHeight + 100), {
		background: "surfaceContainer",
		border: "outlineVariant",
		radius: 8,
		children: [
			label("pluginProjectTitle", rect(16, 10, width - 32, 24), tr("Project activation"), { weight: 600 }),
			label("pluginProjectName", rect(16, 40, width - 32, 28), meta.project || "", { weight: 600 }),
			label("pluginProjectExplanation", rect(16, 74, width - 32, lineHeight), tr(meta.active ? "Active in this project. Manifest changes are applied only when you reload the plugin." : "Package available on the server. Review its manifest and documentation before activating it here."), {
				wrap: true,
				color: "secondaryText"
			})
		]
	}));
	y += lineHeight + 112;
	const ready = !model.busy && !model.dirty && !model.uncertain && !["admin", "sthpw"].includes(meta.project);
	nodes.push(button("pluginAction_" + (meta.active ? "deactivate" : "activate"), rect(0, y, Math.min(width, 320), 40), tr(meta.active ? "Remove from project" : "Review activation"), meta.active ? "remove" : "check", {
		type: "operation",
		action: meta.active ? "deactivate" : "activate"
	}, ready, { highlighted: !meta.active }));
	y += 54;
	if (["admin", "sthpw"].includes(meta.project)) {
		nodes.push(label("pluginBusinessProject", rect(0, y, width, 50), tr("Select a business project to activate or remove a plugin"), {
			wrap: true,
			color: "secondaryText"
		}));
		y += 62;
	}
	nodes.push(label("pluginReviewTitle", rect(0, y, width, 28), tr("Review and develop"), { weight: 600 }));
	y += 36;
	for (const [tab, title, description, icon] of [
		[
			"manifest",
			"Manifest XML",
			"Inspect the project data, dependencies and commands declared by this package.",
			"code"
		],
		[
			"docs",
			"Documentation",
			"Read setup instructions supplied by the package author.",
			"help"
		],
		[
			"files",
			"Files",
			"Browse and edit source files, upload assets or download a local copy.",
			"folder"
		]
	]) {
		const h = compact ? 112 : 78;
		nodes.push(node("Box", "pluginReview_" + tab, rect(0, y, width, h), {
			background: "transparent",
			border: "outlineVariant",
			radius: 4,
			children: [button("pluginOpen_" + tab, rect(8, 8, Math.min(235, width - 16), 32), tr(title), icon, {
				type: "tab",
				value: tab
			}, !model.busy && !model.dirty && !model.uncertain, { alignment: "left" }), label("pluginReviewDescription_" + tab, rect(16, 44, width - 32, h - 48), tr(description), {
				wrap: true,
				color: "secondaryText"
			})]
		}));
		y += h + 8;
	}
	if (!meta.builtin) {
		y += 12;
		nodes.push(label("pluginDistributionTitle", rect(0, y, width, 28), tr("Share a package"), { weight: 600 }));
		y += 36;
		nodes.push(label("pluginDistributionHint", rect(0, y, width, 54), tr("Export a ZIP to share the current package. Publish version creates a separate release; it does not activate it."), {
			wrap: true,
			color: "secondaryText"
		}));
		y += 62;
		const bw = Math.min(260, (width - 8) / 2), enabled = !model.busy && !model.dirty && !model.uncertain;
		nodes.push(button("pluginAction_export", rect(0, y, bw, 40), tr("Export ZIP"), "download", {
			type: "run",
			action: "export"
		}, enabled));
		nodes.push(button("pluginAction_publish", rect(bw + 8, y, bw, 40), tr("Publish version"), "publish", {
			type: "operation",
			action: "publish"
		}, enabled));
		y += 56;
	}
	nodes.push(label("pluginDetailsTitle", rect(0, y, width, 28), tr("Package details"), { weight: 600 }));
	return {
		nodes,
		height: y + 40
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/plugins/plugins.ui.mjs
var russian = {
	"Package source": "Источник пакета",
	Overview: "Обзор",
	"Plugin guide": "Руководство по плагинам",
	"More actions": "Другие действия",
	"Add capabilities to your project": "Расширьте возможности проекта",
	"Install a ready-made package or create your own. A package lives on the server; activation applies it to the selected project.": "Установите готовый пакет или создайте свой. Пакет хранится на сервере, а активация применяет его к выбранному проекту.",
	"Choose a package": "Выберите пакет",
	"Review its contents": "Проверьте содержимое",
	"Activate in project": "Активируйте в проекте",
	"Install a package": "Установить пакет",
	"Have a plugin ZIP or download link? Upload it, review the manifest and documentation, then activate it in this project.": "Есть ZIP плагина или ссылка? Загрузите пакет, проверьте манифест и документацию, затем активируйте его в проекте.",
	"Create your own plugin": "Создать свой плагин",
	"Start with an empty package or a Widget, Column or Theme template. Add files and project data, then publish a version.": "Начните с пустого пакета или шаблона виджета, колонки, темы. Добавьте файлы и данные проекта, затем опубликуйте версию.",
	"First add the package to this server. Nothing is activated in your project until you review and confirm the next step.": "Сначала добавьте пакет на сервер. В проекте ничего не активируется, пока вы не проверите и не подтвердите следующий шаг.",
	"ZIP file": "ZIP-файл",
	"Download link": "Ссылка для загрузки",
	"Choose a ZIP containing manifest.xml and the plugin files. The file is uploaded from this computer to the selected server.": "Выберите ZIP с manifest.xml и файлами плагина. Архив будет загружен с этого компьютера на выбранный сервер.",
	"Choose ZIP and upload": "Выбрать и загрузить ZIP",
	"The server downloads the ZIP from this address. Add a checksum if the publisher provides one.": "Сервер скачает ZIP по этому адресу. Укажите контрольную сумму, если автор пакета её предоставил.",
	"Download package": "Скачать пакет",
	"Project activation": "Активация в проекте",
	"Active in this project. Manifest changes are applied only when you reload the plugin.": "Активен в этом проекте. Изменения манифеста применяются при перезагрузке плагина.",
	"Package available on the server. Review its manifest and documentation before activating it here.": "Пакет доступен на сервере. Перед активацией проверьте манифест и документацию.",
	"Review activation": "Проверить активацию",
	"Review and develop": "Проверка и разработка",
	"Inspect the project data, dependencies and commands declared by this package.": "Проверьте данные проекта, зависимости и команды, объявленные в пакете.",
	"Read setup instructions supplied by the package author.": "Прочитайте инструкции по настройке от автора пакета.",
	"Browse and edit source files, upload assets or download a local copy.": "Просматривайте и редактируйте исходники, загружайте файлы или скачайте локальную копию.",
	"Share a package": "Передача пакета",
	"Export a ZIP to share the current package. Publish version creates a separate release; it does not activate it.": "Экспортируйте ZIP, чтобы передать пакет. Публикация версии создаёт отдельный выпуск без автоматической активации.",
	"Package details": "Сведения о пакете",
	"Activate this package in the selected project? Its manifest can create or update project data and run server code.": "Активировать пакет в выбранном проекте? Манифест может создавать и менять данные проекта и выполнять серверный код.",
	"Package added. Review its contents, then activate it in this project.": "Пакет добавлен. Проверьте содержимое, затем активируйте его в проекте.",
	"Plugin created and active in this project. Add files and configure its manifest.": "Плагин создан и активен в проекте. Добавьте файлы и настройте манифест.",
	"Plugin is now active in this project.": "Плагин активирован в этом проекте.",
	"Plugin removed from this project. The package remains on the server.": "Плагин удалён из проекта. Пакет остаётся на сервере.",
	"Changes saved. Reload the plugin to apply manifest changes to this project.": "Изменения сохранены. Перезагрузите плагин, чтобы применить изменения манифеста к проекту.",
	"Changes saved.": "Изменения сохранены.",
	"Package exported. Check your downloads.": "Пакет экспортирован. Проверьте загрузки.",
	"Version published. Review the new release before activating it.": "Версия опубликована. Проверьте новый выпуск перед активацией.",
	"Define the package": "Опишите пакет",
	"Choose a unique code such as studio_tools. Creation makes a DEV package and registers it in the current project.": "Выберите уникальный код, например studio_tools. Создание добавит пакет DEV и зарегистрирует его в текущем проекте.",
	"Use letters, digits, underscores or hyphens. The code cannot be changed after creation.": "Используйте буквы, цифры, подчёркивания и дефисы. После создания код менять нельзя.",
	"Empty package: add your own manifest entries and files.": "Пустой пакет: добавьте свои записи манифеста и файлы.",
	"Widget template: starts with a modern reusable item layout.": "Шаблон виджета: основа — современный переиспользуемый макет элемента.",
	"Column template: configure a table column through the existing widget system.": "Шаблон колонки: настройте колонку таблицы через существующую систему виджетов.",
	"Theme template: package a theme using the native theme configuration.": "Шаблон темы: создайте пакет с настройками темы.",
	"Project template exports the selected project. No new plugin is activated.": "Шаблон проекта экспортирует выбранный проект. Новый плагин не активируется.",
	"Save changes the manifest file. Reload plugin applies its project data; review that confirmation first.": "Сохранение меняет файл манифеста. Перезагрузка плагина применяет данные к проекту — сначала прочитайте подтверждение.",
	"Select a file to edit. Save commits the source; generated .spt files can be cleaned from More actions.": "Выберите файл для редактирования. Сохранение записывает исходник; сгенерированные .spt можно удалить через «Другие действия».",
	"Read or edit the author’s documentation as source. Legacy HTML is not executed here.": "Читайте и редактируйте документацию автора как исходный текст. Легаси HTML здесь не выполняется.",
	"No matching plugins. Change the search or the project filter.": "Плагины не найдены. Измените поиск или фильтр проекта.",
	"Back to overview": "Назад к обзору",
	Back: "Назад",
	"Server package": "Пакет на сервере",
	"No plugins yet": "Плагинов пока нет",
	Package: "Пакет",
	Project: "Проект",
	New: "Создать",
	Activate: "Активировать",
	Information: "Информация",
	Files: "Файлы",
	Widget: "Виджет",
	Column: "Колонка",
	Theme: "Тема",
	Confirm: "Подтвердить",
	"Plugin sections": "Разделы плагина",
	"Discard unsaved changes and reload the plugin catalogue?": "Сбросить несохранённые изменения и обновить каталог плагинов?",
	"Plugin catalogue": "Каталог плагинов",
	"Install plugin": "Установить плагин",
	"Search plugins": "Поиск плагинов",
	"Active in this project": "Активен в этом проекте",
	"Create plugin": "Создать плагин",
	"New plugin": "Новый плагин",
	"Built-in plugin · read-only files": "Встроенный плагин · файлы только для чтения",
	"Not active in this project": "Не активен в этом проекте",
	"Select a plugin, create a new package or install a ZIP.": "Выберите плагин, создайте пакет или установите ZIP.",
	"The operation result is unknown. Reload before continuing.": "Результат операции неизвестен. Обновите данные перед продолжением.",
	"Working…": "Выполняется…",
	"Reload removes and reinstalls the plugin in this project. Its data may be replaced.": "Перезагрузка удалит и заново установит плагин в этом проекте. Его данные могут быть заменены.",
	"Remove this plugin and its manifest-defined data from the current project?": "Удалить плагин и описанные его манифестом данные из текущего проекта?",
	"Clean all project entries described by this plugin manifest?": "Удалить из проекта все записи, описанные манифестом этого плагина?",
	"Delete this package from the server? It must be inactive in every project.": "Удалить пакет с сервера? Он должен быть отключён во всех проектах.",
	"Delete the selected plugin file or folder and its contents?": "Удалить выбранный файл или папку плагина со всем содержимым?",
	"Delete all generated .spt files in this package?": "Удалить все сгенерированные файлы .spt в этом пакете?",
	"New file": "Новый файл",
	"New folder": "Новая папка",
	"Rename or move": "Переименовать или переместить",
	"Publish version": "Опубликовать версию",
	"ZIP installation adds a package to the server. Activate it separately in the selected project. Plugins can execute trusted server code.": "Установка ZIP добавляет пакет на сервер. Активируйте его отдельно в выбранном проекте. Плагины могут выполнять доверенный код на сервере.",
	"Browse ZIP…": "Выбрать ZIP…",
	"Plugin ZIP URL": "Ссылка на ZIP плагина",
	"SHA-256 or MD5 (optional)": "SHA-256 или MD5 (необязательно)",
	"Download ZIP": "Загрузить ZIP",
	"Relative path": "Относительный путь",
	"Remove from project": "Удалить из проекта",
	"Reload plugin": "Перезагрузить плагин",
	"Export ZIP": "Экспорт ZIP",
	"Clean project data": "Очистить данные проекта",
	"Delete package": "Удалить пакет",
	"Manifest XML": "Манифест XML",
	Documentation: "Документация",
	"Plugin type": "Тип плагина",
	"Empty plugin": "Пустой плагин",
	"Project template": "Шаблон проекта",
	"Export template": "Экспорт шаблона",
	"Create a project template from the selected project.": "Создать шаблон из выбранного проекта.",
	"Parent folder": "Родительская папка",
	"Upload file": "Загрузить файл",
	"Clear .spt files": "Очистить файлы .spt",
	"Download file": "Скачать файл",
	"Replace file": "Заменить файл",
	"Replace the selected file with a local upload?": "Заменить выбранный файл содержимым локального файла?",
	"This file is binary or exceeds 2 MiB. Download it to edit locally.": "Двоичный файл или размер больше 2 МиБ. Скачайте его для редактирования.",
	"Create documentation": "Создать документацию",
	Inactive: "Неактивен",
	"Plugin changed on the server. Reload before continuing.": "Плагин изменён на сервере. Обновите данные перед продолжением.",
	"File changed on the server. Reload before saving.": "Файл изменён на сервере. Обновите его перед сохранением.",
	"Use Publish to change a plugin code or version": "Для изменения кода или версии используйте публикацию",
	"Another version is active. Remove it from this project first.": "Активна другая версия. Сначала удалите её из этого проекта.",
	"Remove this plugin from every project before deleting its files": "Перед удалением файлов отключите плагин во всех проектах",
	"This plugin directory already exists; choose another version": "Каталог плагина уже существует. Выберите другую версию",
	"This plugin version already exists": "Эта версия плагина уже существует",
	"A file or folder with that name already exists": "Файл или папка с таким именем уже существует",
	"Built-in plugin files are read-only": "Файлы встроенных плагинов доступны только для чтения",
	"Select a business project to activate or remove a plugin": "Выберите рабочий проект для активации или удаления плагина",
	"Enter a release version before publishing": "Укажите номер выпуска перед публикацией",
	"Plugin checksum does not match": "Контрольная сумма плагина не совпадает"
};
function translate(text, language) {
	if (language === "ru" && russian$1[text]) return russian$1[text];
	return language === "ru" && russian[text] ? russian[text] : translate$1(text, language);
}
var parent = (path) => path.split("/").slice(0, -1).join("/");
function actions(model, language) {
	const meta = model.metadata || {}, ready = !model.busy && !model.dirty && !model.uncertain;
	return [
		[
			"reload",
			"Reload plugin",
			"refresh",
			meta.active
		],
		[
			"deactivate",
			"Remove from project",
			"remove",
			meta.active
		],
		[
			"clean",
			"Clean project data",
			"delete",
			!meta.active
		],
		[
			"clear_spt",
			"Clear .spt files",
			"delete",
			!meta.builtin
		],
		[
			"delete",
			"Delete package",
			"delete",
			!meta.builtin
		]
	].filter((row) => row[3]).map(([command, title, icon]) => ({
		command,
		title: translate(title, language),
		icon,
		enabled: ready && (command !== "delete" || !meta.active) && (![
			"reload",
			"deactivate",
			"clean"
		].includes(command) || !["admin", "sthpw"].includes(meta.project)),
		translate: false
	}));
}
function toolbar(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [], compact = width < 420;
	const commands = [[
		"pluginReload",
		"Refresh",
		"refresh",
		{ type: "reload" },
		!model.busy,
		40
	]];
	if (model.dirty || model.uncertain) {
		commands.push([
			"pluginDiscard",
			"Discard",
			"undo",
			{ type: "discard" },
			!model.busy,
			compact ? 40 : 120
		]);
		if (!model.metadata?.new) commands.push([
			"pluginSave",
			"Save",
			"save",
			{ type: "save" },
			model.canWrite && !model.busy && !model.uncertain,
			compact ? 100 : 140
		]);
	}
	commands.push([
		"pluginHelp",
		"Plugin guide",
		"help",
		{ type: "help" },
		true,
		40
	]);
	let x = Math.max(0, width - commands.reduce((sum, row) => sum + row[5] + 4, 0));
	for (const [id, title, icon, event, enabled, w] of commands) {
		nodes.push(button(id, rect(x, 0, w, 40), tr(title), icon, event, enabled, { iconOnly: w === 40 }));
		x += w + 4;
	}
	return { nodes };
}
var metaNew = (model) => !!model.metadata?.new;
function describe(model, ui, width, height, language) {
	const tr = (text) => translate(text, language), nodes = [], gap = 12, compact = width < 760, nav = !!!(model.catalog || []).length || metaNew(model) ? 0 : ui.collapsed ? 44 : compact ? 200 : 250, right = nav ? nav + gap : 0, bodyWidth = Math.max(0, width - right), editable = !model.busy && !model.uncertain && model.canWrite, clean = !model.busy && !model.dirty && !model.uncertain, doc = model.document || {}, meta = model.metadata || {}, exists = !!model.identity;
	const btn = (id, r, text, icon, action, enabled = clean, extra = {}) => button(id, r, tr(text), icon, action, enabled, extra);
	if (nav) {
		if (!ui.collapsed) nodes.push(label("pluginCatalogueCaption", rect(0, 0, nav - 36, 28), tr("Plugin catalogue"), { weight: 600 }));
		nodes.push(btn("pluginCollapse", rect(ui.collapsed ? 0 : nav - 28, 0, 28, 28), "Plugin catalogue", ui.collapsed ? "next" : "previous", { type: "collapse" }, true, { iconOnly: true }));
	}
	if (nav && !ui.collapsed) {
		nodes.push(btn("pluginNew", rect(0, 36, nav, 36), "New", "add", { type: "new" }));
		nodes.push(btn("pluginInstall", rect(0, 80, nav, 36), "Install a package", "upload", { type: "install" }, clean, { iconOnly: false }));
		nodes.push(node("Field", "pluginSearch", rect(0, 128, nav, 36), {
			text: ui.query,
			placeholder: tr("Search plugins"),
			action: { type: "query" },
			clearable: true
		}));
		nodes.push(node("CheckBox", "pluginActiveOnly", rect(0, 172, nav, 36), {
			text: tr("Active in this project"),
			checked: ui.activeOnly,
			action: { type: "activeOnly" }
		}));
		nodes.push(node("List", "pluginCatalogue", rect(0, 216, nav, Math.max(0, height - 216)), {
			source: "plugins",
			keyField: "identity",
			fields: [
				"identity",
				"title",
				"code",
				"version",
				"builtin",
				"active",
				"path"
			],
			rowHeight: 76,
			rowGap: 0,
			scrollbarId: "pluginCatalogueScrollBar",
			scrollbarReserved: 16
		}));
	}
	if (nav > 44 && !catalog(model, ui).length) nodes.push(label("pluginNoMatches", rect(8, 224, nav - 24, 80), tr("No matching plugins. Change the search or the project filter."), {
		wrap: true,
		color: "secondaryText"
	}));
	let y = 0;
	if (model.error || model.uncertain) {
		const message = model.error || "The operation result is unknown. Reload before continuing.";
		nodes.push(node("Area", "pluginError", rect(right, y, bodyWidth, 72), {
			text: tr(message),
			readOnly: true,
			notice: true,
			wrap: true,
			color: "red",
			role: "alert"
		}));
		y += 80;
	}
	if (model.busy) {
		nodes.push(label("pluginBusy", rect(right, y, bodyWidth, 32), tr("Working…"), { color: "secondaryText" }));
		y += 40;
	}
	if (ui.operation) {
		const content = [], w = Math.max(0, Math.min(1040, bodyWidth - 48));
		let oy = 0;
		const heading = {
			install: "Install a package",
			activate: "Review activation",
			deactivate: "Remove from project",
			reload: "Reload plugin",
			clean: "Clean project data",
			delete: "Delete package",
			clear_spt: "Clear .spt files",
			replace_file: "Replace file",
			delete_file: "Delete",
			reload_catalog: "Refresh",
			new_file: "New file",
			new_folder: "New folder",
			rename: "Rename or move",
			publish: "Publish version",
			run_resource: "Run Python action"
		}[ui.operation];
		content.push(label("pluginOperationTitle", rect(0, oy, w, 36), tr(heading), {
			weight: 600,
			fontRole: "title"
		}));
		oy += 48;
		if (ui.operation === "activate") {
			const progress = steps(w, 2, tr);
			progress.nodes.forEach((item) => {
				item.y += oy;
				content.push(item);
			});
			oy += progress.height + 8;
		}
		if (destructive[ui.operation]) {
			content.push(label("pluginOperationExplanation", rect(0, oy, w, 96), tr(destructive[ui.operation]), { wrap: true }));
			oy += 108;
		}
		if (ui.operation === "install") {
			const guide = installation(ui, w, clean, tr);
			guide.nodes.forEach((item) => {
				item.y += oy;
				content.push(item);
			});
			oy += guide.height;
		} else {
			content.push(label("pluginOperationContext", rect(0, oy, w, 50), tr("Package") + ": " + (doc.title || doc.code || "") + "\n" + tr("Project") + ": " + (meta.project || ""), {
				wrap: true,
				color: "secondaryText"
			}));
			oy += 62;
			if (!destructive[ui.operation]) {
				content.push(node("Field", "pluginOperationValue", rect(0, oy, w, 40), {
					text: ui.value,
					placeholder: tr(ui.operation === "publish" ? "Version" : "Relative path"),
					action: {
						type: "input",
						field: "value"
					},
					enabled: clean
				}));
				oy += 52;
			}
		}
		if (ui.operation !== "install") content.push(btn("pluginConfirm", rect(0, oy, Math.min(180, w / 2 - 4), 40), ui.operation === "activate" ? "Activate" : "Confirm", "check", { type: "confirm" }, clean && (![
			"publish",
			"new_file",
			"new_folder",
			"rename"
		].includes(ui.operation) || !!ui.value.trim()) || ui.operation === "reload_catalog" && !model.busy));
		content.push(btn("pluginCancel", rect(ui.operation === "install" ? 0 : Math.min(188, w / 2 + 4), oy, Math.min(150, w / 2 - 4), 40), ui.operation === "install" ? "Back" : "Cancel", "close", { type: "cancel" }, !model.busy));
		nodes.push(node("Scroll", "pluginOperationScroll", rect(right, y, bodyWidth, height - y), {
			contentHeight: oy + 84,
			scrollbarId: "pluginOperationScrollBar",
			scrollbarReserved: 16,
			children: [node("Box", "pluginOperationPanel", rect(0, 0, w + 32, oy + 84), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 8,
				children: content.map((item) => Object.assign({}, item, {
					x: item.x + 16,
					y: item.y + 16
				}))
			})]
		}));
		return { nodes };
	}
	if (ui.notice) {
		nodes.push(label("pluginResult", rect(right, y, bodyWidth, 60), tr(ui.notice), {
			wrap: true,
			weight: 600,
			role: "status"
		}));
		y += 72;
	}
	if (!exists && !meta.new) {
		const guide = start(Math.max(0, bodyWidth - 16), clean, tr);
		nodes.push(node("Scroll", "pluginWelcome", rect(right, y, bodyWidth, Math.max(0, height - y)), {
			children: guide.nodes,
			contentHeight: guide.height,
			scrollbarId: "pluginWelcomeScrollBar",
			scrollbarReserved: 16
		}));
		return { nodes };
	}
	nodes.push(label("pluginTitle", rect(right, y, Math.max(0, bodyWidth - (exists ? 190 : 0)), 28), doc.title || doc.code || tr("New plugin"), {
		fontRole: "title",
		weight: 600
	}));
	y += 36;
	nodes.push(label("pluginStatus", rect(right, y, bodyWidth, 24), tr(meta.builtin ? "Built-in plugin · read-only files" : meta.active ? "Active in this project" : meta.new ? "New plugin" : "Not active in this project") + (doc.version ? " · " + doc.version : " · DEV"), { color: "secondaryText" }));
	y += 32;
	if (exists) {
		nodes.push(node("View", "pluginToolsMenu", rect(right + bodyWidth - 180, y - 66, 180, 36), {
			view: "pluginTools",
			actions: actions(model, language),
			label: tr("More actions")
		}));
		const tabs = [
			["info", "Overview"],
			["resources", "Resources"],
			["details", "Package details"],
			["manifest", "Manifest XML"],
			["files", "Files"],
			["docs", "Documentation"]
		];
		bodyWidth / tabs.length;
		nodes.push(node(bodyWidth < 740 ? "Choice" : "Segmented", "pluginTabs", rect(right, y, bodyWidth, 40), {
			value: ui.tab,
			options: tabs.map(([value, text]) => ({
				value,
				label: tr(text)
			})),
			action: { type: "tab" },
			enabled: !model.busy,
			label: tr("Plugin sections")
		}));
		y += 52;
	}
	const content = [], w = Math.max(0, Math.min(meta.new || ui.tab === "info" || ui.tab === "details" ? 1040 : Infinity, bodyWidth - 16));
	let cy = 0;
	function field(name, title, area = false, readonly = false) {
		content.push(label("pluginLabel_" + name, rect(0, cy, w, 24), tr(title)));
		cy += 28;
		content.push(node(area ? "Area" : "Field", "pluginField_" + name, rect(0, cy, w, area ? 110 : 40), {
			label: tr(title),
			text: doc[name] || "",
			readOnly: readonly || !editable,
			enabled: !model.busy,
			action: {
				type: "field",
				field: name
			}
		}));
		cy += area ? 122 : 52;
	}
	if (!meta.new && ui.tab === "info") {
		const guide = project(model, w, tr);
		guide.nodes.forEach((item) => content.push(item));
		cy = guide.height;
		content.push(label("pluginPackageIdentity", rect(0, cy, w, 28), [doc.code, doc.version || "DEV"].join(" · "), { weight: 600 }));
		cy += 36;
		if (doc.description) {
			content.push(label("pluginPackageDescription", rect(0, cy, w, 80), doc.description, {
				wrap: true,
				color: "secondaryText"
			}));
			cy += 92;
		}
		content.push(btn("pluginEditDetails", rect(0, cy, Math.min(300, w), 36), "Package details", "edit", {
			type: "tab",
			value: "details"
		}));
		cy += 48;
	} else if (meta.new || ui.tab === "details") {
		if (meta.new) {
			content.push(label("pluginCreateIntro", rect(0, cy, w, 68), tr("Choose a unique code such as studio_tools. Creation makes a DEV package and registers it in the current project."), {
				wrap: true,
				color: "secondaryText"
			}));
			cy += 80;
		}
		if (!meta.new || doc.type !== "project") {
			field("title", "Title");
			field("code", "Code", false, !meta.new);
			if (meta.new) {
				content.push(label("pluginCodeHint", rect(0, cy, w, 50), tr("Use letters, digits, underscores or hyphens. The code cannot be changed after creation."), {
					wrap: true,
					color: "secondaryText"
				}));
				cy += 62;
			}
			if (!meta.new) field("version", "Version", false, true);
			field("description", "Description", true);
		} else {
			content.push(label("pluginTemplateNotice", rect(0, cy, w, 64), tr("Create a project template from the selected project."), { wrap: true }));
			cy += 72;
		}
		if (meta.new) {
			content.push(label("pluginTypeLabel", rect(0, cy, w, 24), tr("Plugin type")));
			cy += 28;
			content.push(node("Choice", "pluginType", rect(0, cy, w, 40), {
				value: doc.type || "",
				options: [
					["", "Empty plugin"],
					["project", "Project template"],
					["widget", "Widget"],
					["column", "Column"],
					["theme", "Theme"]
				].map(([value, text]) => ({
					value,
					label: tr(text)
				})),
				action: {
					type: "field",
					field: "type"
				},
				enabled: editable
			}));
			cy += 52;
		}
		if (meta.new) {
			const hint = {
				"": "Empty package: add your own manifest entries and files.",
				widget: "Widget template: starts with a modern reusable item layout.",
				column: "Column template: configure a table column through the existing widget system.",
				theme: "Theme template: package a theme using the native theme configuration.",
				project: "Project template exports the selected project. No new plugin is activated."
			}[doc.type || ""];
			content.push(label("pluginCreateHint", rect(0, cy, w, 56), tr(hint), {
				wrap: true,
				color: "secondaryText"
			}));
			cy += 68;
		}
	} else if (ui.tab === "resources") {
		const resources = describe$1(model, ui, w, Math.max(360, height - y), language, tr);
		resources.nodes.forEach((item) => content.push(item));
		cy = resources.height;
	} else if (ui.tab === "manifest") {
		content.push(label("pluginManifestHint", rect(0, 0, w, 56), tr("Save changes the manifest file. Reload plugin applies its project data; review that confirmation first."), {
			wrap: true,
			color: "secondaryText"
		}));
		content.push(node("Code", "pluginManifest", rect(0, 68, w, Math.max(260, height - y - 80)), {
			text: doc.manifest || "",
			syntax: "xml",
			language,
			service: "sourceEditor",
			bufferKey: model.identity + ":manifest",
			readOnly: !editable,
			action: {
				type: "field",
				field: "manifest"
			}
		}));
		cy = 68 + Math.max(260, height - y - 80);
	} else {
		const files = ui.tab === "files";
		content.push(label("pluginSourceHint", rect(0, cy, w, 56), tr(files ? "Select a file to edit. Save commits the source; generated .spt files can be cleaned from More actions." : "Read or edit the author’s documentation as source. Legacy HTML is not executed here."), {
			wrap: true,
			color: "secondaryText"
		}));
		cy += 68;
		if (files) {
			const tools = [
				[
					"parent",
					"Parent folder",
					"previous",
					{
						type: "file",
						path: parent(meta.folder || ""),
						directory: true
					}
				],
				[
					"new_file",
					"New file",
					"add"
				],
				[
					"new_folder",
					"New folder",
					"folder"
				],
				[
					"rename",
					"Rename or move",
					"edit"
				],
				[
					"delete_file",
					"Delete",
					"delete"
				],
				[
					"upload",
					"Upload file",
					"upload"
				]
			];
			let x = 0;
			for (const [action, title, icon, event] of tools) {
				const labelled = [
					"new_file",
					"new_folder",
					"upload"
				].includes(action), toolWidth = labelled ? Math.min(w, Math.max(140, tr(title).length * 7 + 48)) : 40;
				if (x && x + toolWidth > w) {
					x = 0;
					cy += 44;
				}
				const enabled = clean && (action === "parent" ? !!meta.folder : !meta.builtin && (!["rename", "delete_file"].includes(action) || !!doc.file || !!meta.folder));
				content.push(btn("pluginFileAction_" + action, rect(x, cy, toolWidth, 40), title, icon, event || {
					type: action === "upload" ? "upload" : "operation",
					action
				}, enabled, { iconOnly: !labelled }));
				x += toolWidth + 4;
			}
			cy += 48;
			content.push(label("pluginFolderPath", rect(0, cy, w, 26), meta.folder || "/", { color: "secondaryText" }));
			cy += 32;
			content.push(node("List", "pluginFiles", rect(0, cy, w, Math.min(200, Math.max(76, (meta.files || []).length * 40))), {
				source: "files",
				keyField: "path",
				fields: [
					"name",
					"path",
					"directory",
					"size"
				],
				rowHeight: 40,
				scrollbarId: "pluginFilesScrollBar",
				scrollbarReserved: 16
			}));
			cy += Math.min(200, Math.max(76, (meta.files || []).length * 40)) + 12;
		}
		if (doc.file) {
			content.push(label("pluginFileName", rect(0, cy, w - 92, 30), doc.file.path, { weight: 600 }));
			content.push(btn("pluginFileReplace", rect(w - 84, cy - 4, 40, 40), "Replace file", "upload", {
				type: "operation",
				action: "replace_file"
			}, editable && clean, { iconOnly: true }));
			content.push(btn("pluginFileDownload", rect(w - 40, cy - 4, 40, 40), "Download file", "download", {
				type: "run",
				action: "download_file",
				values: { path: doc.file.path }
			}, clean, { iconOnly: true }));
			cy += 40;
			if (doc.file.content === null) {
				content.push(label("pluginBinaryFile", rect(0, cy, w, 70), tr("This file is binary or exceeds 2 MiB. Download it to edit locally."), { wrap: true }));
				cy += 78;
			} else {
				content.push(node("Code", "pluginFileEditor", rect(0, cy, w, Math.max(200, height - y - cy - 12)), {
					text: doc.file.content || "",
					syntax: doc.file.path.endsWith(".py") ? "python" : doc.file.path.endsWith(".xml") ? "xml" : "text",
					language,
					service: "sourceEditor",
					bufferKey: model.identity + ":" + doc.file.path,
					readOnly: !editable,
					action: {
						type: "field",
						field: "file_content"
					}
				}));
				cy += Math.max(200, height - y - cy - 12);
			}
		} else if (!files) {
			content.push(btn("pluginCreateDocs", rect(0, cy, Math.min(270, w), 40), "Create documentation", "add", { type: "docs_create" }, editable && clean));
			cy += 48;
		}
	}
	if (meta.new) {
		const bw = Math.min(260, (bodyWidth - 32) / 2);
		nodes.push(node("Box", "pluginCreateFooter", rect(right, height - 52, bodyWidth, 52), {
			background: "surfaceContainer",
			border: "outlineVariant",
			radius: 0,
			children: [btn("pluginCreate", rect(8, 6, bw, 40), doc.type === "project" ? "Export template" : "Create plugin", "add", { type: "save" }, editable && canCreate(model), { highlighted: true }), btn("pluginCancelCreate", rect(bw + 16, 6, bw, 40), "Cancel", "close", { type: "cancel" }, !model.busy)]
		}));
	}
	nodes.push(node("Scroll", "pluginEditorScroll", rect(right, y, bodyWidth, Math.max(0, height - y - (meta.new ? 60 : 0))), {
		resetKey: model.identity + ":" + !!meta.new + ":" + ui.tab,
		contentHeight: cy + 12,
		scrollbarId: "pluginEditorScrollBar",
		scrollbarReserved: 16,
		children: content
	}));
	return { nodes };
}
function row(list, record, model, language) {
	const tr = (text) => translate(text, language), w = Math.max(0, list.width - 16);
	if (list.id === "pluginResources") return row$1(list, record, model, tr);
	if (list.id === "pluginFiles") return { nodes: [button("pluginFile_" + record.path, rect(0, 0, w, 40), record.name, record.directory ? "folder" : "file", {
		type: "file",
		path: record.path,
		directory: record.directory
	}, !model.busy, {
		selected: model.document?.file?.path === record.path,
		alignment: "left"
	})] };
	return { nodes: [
		node("Box", "pluginRowBackground", rect(0, 0, w, 76), {
			background: model.identity === record.identity ? "contentSelection" : "transparent",
			radius: 0
		}),
		node("Icon", "pluginRowIcon", rect(4, 10, 24, 24), { icon: "extension" }),
		label("pluginRowTitle", rect(36, 2, w - 44, 28), record.title || record.code, { weight: 600 }),
		label("pluginRowStatus", rect(36, 30, w - 44, 22), [
			record.version || "DEV",
			record.builtin ? tr("Built-in") : "",
			tr(record.active ? "Active" : "Inactive")
		].filter(Boolean).join(" · "), { color: "secondaryText" }),
		label("pluginRowPath", rect(36, 52, w - 44, 22), record.path, {
			color: "secondaryText",
			fontRole: "secondary"
		}),
		node("Action", "pluginSelect", rect(0, 0, w, 76), {
			text: record.title || record.code,
			action: {
				type: "select",
				identity: record.identity
			},
			enabled: !model.busy
		})
	] };
}
//#endregion
//#region src/features/administration/Plugins.vue
var _hoisted_1 = ["aria-busy"];
var _sfc_main = {
	__name: "Plugins",
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved", "help"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props, emit = __emit, host = ref(null), picker = ref(null), toolbarHost = ref(null), size = ref({
			width: 800,
			height: 600
		}), toolbarWidth = ref(420), rows = ref([]), draft = ref({}), original = ref({}), metadata = ref({}), identity = ref(""), revision = ref(""), busy = ref(false), uncertain = ref(false), error = ref(""), ui = ref(initial()), canWrite = ref(false);
		const dirty = computed(() => JSON.stringify(draft.value) !== JSON.stringify(original.value)), model = computed(() => ({
			catalog: rows.value,
			document: draft.value,
			metadata: metadata.value,
			identity: identity.value,
			canWrite: canWrite.value,
			busy: busy.value,
			uncertain: uncertain.value,
			dirty: dirty.value,
			error: error.value
		})), scene = computed(() => describe(model.value, ui.value, size.value.width, size.value.height, appearance.language)), toolbar$1 = computed(() => toolbar(model.value, toolbarWidth.value, appearance.language)), models = computed(() => ({
			plugins: catalog(model.value, ui.value),
			files: metadata.value.files || [],
			pluginResources: metadata.value.resources || []
		})), views = { pluginTools: {
			component: _sfc_main$2,
			nodeProps: true,
			props: { onCommand: (action) => dispatch({
				type: "operation",
				action
			}) }
		} };
		let generation = 0, observer, uploadPackage = false, uploadReplace = false;
		const clone = (value) => JSON.parse(JSON.stringify(value));
		function rowScene(list, row$2) {
			return row(list, row$2, model.value, appearance.language);
		}
		function clear() {
			++generation;
			busy.value = uncertain.value = false;
			rows.value = [];
			draft.value = {};
			original.value = {};
			metadata.value = {};
			identity.value = revision.value = error.value = "";
			ui.value = initial();
		}
		async function run(action, values = {}, upload = null) {
			if (busy.value || !props.ticket) return;
			const current = ++generation, owner = {
				ticket: props.ticket,
				project: props.project,
				language: "python"
			}, write = ![
				"list",
				"load",
				"new",
				"browse",
				"open_file",
				"open_resource"
			].includes(action), args = Object.assign({
				action,
				project_code: props.project,
				identity: identity.value,
				expected_revision: revision.value
			}, values);
			if (["save", "create"].includes(action)) {
				args.document = clone(draft.value);
				args.changed_fields = ["title", "description"].filter((key) => draft.value[key] !== original.value[key]);
			}
			busy.value = true;
			error.value = "";
			try {
				if (upload) {
					args.upload_file_name = await uploadFormFile(owner.ticket, owner.project, upload);
					if (current !== generation) return;
					if (!uploadPackage && !uploadReplace) args.path = [metadata.value.folder, upload.name].filter(Boolean).join("/");
				}
				const result = (await rpc("execute_cmd", [
					owner,
					"tactic.ui.app.plugin_wdg.PluginManagerCmd",
					args
				], {}, true)).info;
				if (current !== generation) return;
				uncertain.value = false;
				if (result.catalog) rows.value = result.catalog;
				if (action === "list") {
					const selected = rows.value.find((row) => row.identity === identity.value) || rows.value[0];
					busy.value = false;
					if (selected) return run("load", { identity: selected.identity });
					draft.value = original.value = {};
					metadata.value = {};
					identity.value = revision.value = "";
				} else {
					identity.value = result.identity;
					revision.value = result.revision;
					draft.value = result.document;
					original.value = clone(result.document);
					metadata.value = result.metadata;
					canWrite.value = result.canWrite;
					if (result.download) {
						const link = document.createElement("a");
						link.href = "/assets/_cache/" + [
							owner.ticket,
							result.download.directory,
							result.download.filename
						].map(encodeURIComponent).join("/");
						link.download = result.download.filename;
						link.click();
					}
					if (write) emit("saved");
				}
				dispatch({
					type: "completed",
					action
				});
			} catch (failure) {
				if (current !== generation) return;
				error.value = failure.message;
				if (write) uncertain.value = true;
			} finally {
				if (current === generation) busy.value = false;
			}
		}
		function discard() {
			if (busy.value) return;
			if (uncertain.value || metadata.value.new) {
				uncertain.value = false;
				draft.value = original.value = {};
				metadata.value = {};
			} else draft.value = clone(original.value);
			error.value = "";
		}
		function dispatch(event) {
			const result = transition(ui.value, model.value, event);
			ui.value = result.ui;
			for (const command of result.commands) if (command.type === "help") emit("help", command.topic);
			else if (command.type === "select") run("load", { identity: command.identity });
			else if (command.type === "request") run(command.action, command.values);
			else if (command.type === "field") {
				if (command.field === "resource_source" && draft.value.resource) draft.value.resource.source = command.value;
				else if (command.field === "resource_palette" && draft.value.resource) draft.value.resource.palette = command.value;
				else if (command.field === "file_content" && draft.value.file) draft.value.file.content = command.value;
				else if (Object.hasOwn(draft.value, command.field)) draft.value[command.field] = command.value;
			} else if (command.type === "save") run(metadata.value.new ? "create" : "save");
			else if (command.type === "discard") discard();
			else if (command.type === "error") error.value = command.value;
			else if (command.type === "upload") {
				uploadPackage = !!command.package;
				uploadReplace = !!command.replace;
				picker.value.accept = uploadPackage ? ".zip" : "";
				picker.value.click();
			}
		}
		function upload(event) {
			const file = event.target.files[0];
			event.target.value = "";
			if (file) run(uploadPackage ? "install" : "upload", {
				folder: metadata.value.folder || "",
				...uploadReplace ? {
					path: draft.value.file.path,
					confirmation: true
				} : {}
			}, file);
		}
		function canLeave() {
			if (busy.value || dirty.value || uncertain.value) {
				error.value = "Apply or discard unsaved changes first";
				return false;
			}
			return true;
		}
		function beforeUnload(event) {
			if (busy.value || dirty.value || uncertain.value) {
				event.preventDefault();
				event.returnValue = "";
			}
		}
		watch(() => [props.ticket, props.project], () => {
			clear();
			run("list");
		});
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				for (const entry of entries) if (entry.target === host.value) size.value = {
					width: entry.contentRect.width,
					height: entry.contentRect.height
				};
				else toolbarWidth.value = entry.contentRect.width;
			});
			observer.observe(host.value);
			observer.observe(props.toolbarTarget ? document.querySelector(props.toolbarTarget) : host.value.parentElement);
			window.addEventListener("beforeunload", beforeUnload);
			run("list");
		});
		onBeforeUnmount(() => {
			++generation;
			observer?.disconnect();
			window.removeEventListener("beforeunload", beforeUnload);
		});
		__expose({
			canLeave,
			dirty,
			busy,
			uncertain,
			error,
			dispatch,
			model,
			ui,
			scene
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "plugins-frame frame-host",
				"aria-busy": busy.value,
				style: normalizeStyle({ gap: "8px" })
			}, [
				(openBlock(), createBlock(Teleport, {
					defer: "",
					to: __props.toolbarTarget || "body",
					disabled: !__props.toolbarTarget
				}, [withDirectives(createBaseVNode("div", {
					ref_key: "toolbarHost",
					ref: toolbarHost,
					class: "frame-toolbar-host",
					style: normalizeStyle({ width: toolbarWidth.value + "px" })
				}, [createVNode(_sfc_main$1, {
					scene: toolbar$1.value,
					onEvent: dispatch
				}, null, 8, ["scene"])], 4), [[vShow, __props.presentationVisible]])], 8, ["to", "disabled"])),
				createBaseVNode("div", {
					ref_key: "host",
					ref: host,
					class: "frame-host-body"
				}, [createVNode(_sfc_main$1, {
					scene: scene.value,
					models: models.value,
					views,
					"describe-row": rowScene,
					onEvent: dispatch
				}, null, 8, ["scene", "models"])], 512),
				createBaseVNode("input", {
					ref_key: "picker",
					ref: picker,
					type: "file",
					hidden: "",
					onChange: upload
				}, null, 544)
			], 12, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=Plugins.js.map
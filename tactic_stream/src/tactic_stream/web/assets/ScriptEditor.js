import { D as nextTick, E as mergeProps, F as renderSlot, K as withCtx, L as resolveDirective, N as openBlock, P as renderList, T as mergeModels, U as watch, V as useModel, Z as ref, _ as createElementBlock, b as createVNode, c as withKeys, f as Teleport, g as createCommentVNode, h as createBlock, it as toDisplayString, j as onMounted, k as onBeforeUnmount, l as withModifiers, m as createBaseVNode, nt as normalizeClass, p as computed, q as withDirectives, rt as normalizeStyle, tt as unref, u as Fragment, w as inject } from "./vue.js";
import { A as appearance, R as controls, c as _sfc_main$4, f as _sfc_main$3, k as t } from "./index.js";
import { Gt as muted, Kt as node, T as AppSearchField_default, U as endActivity, Ut as button, V as beginActivity, Wt as label, _ as copyText, c as _sfc_main$7, d as completions, f as documentSymbols, i as _sfc_main$5, k as _sfc_main$8, l as toolbar$1, lt as scriptEditor, n as frameContentWidth, qt as rect, r as observeFrameSizes, st as rpc, u as _sfc_main$6, y as translate } from "./CodeBlock.js";
import { C as _sfc_main$9, D as _sfc_main$10, c as buttonId, l as runBrowserScript, u as scriptTree } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/scripts/source.ui.mjs
function toolbarHeight(width) {
	return 30 + (width < 530 ? controls.scrollBar.extent : 0);
}
function describe(model, width, language, revision) {
	const baseWidth = Math.max(440, width - 90);
	const scene = toolbar$1(Object.assign({}, model, { compactToolbar: false }), baseWidth, language, revision);
	[
		[
			"saved",
			"Saved revisions",
			"cloud-done",
			model.saved && !model.busy
		],
		[
			"selection",
			"Run selection",
			"play-selection",
			model.canCopy && !model.readOnly && !model.busy
		],
		[
			"outline",
			"Outline",
			"format-list-bulleted",
			true
		]
	].forEach((row, index) => scene.nodes.push(button("scriptSource_" + row[0], rect(baseWidth + index * 30, 0, 28, 28), translate(row[1], language), row[2], { type: row[0] }, row[3], {
		iconOnly: true,
		visible: row[0] !== "saved" || !model.native
	})));
	scene.contentWidth = Math.max(530, width);
	return scene;
}
//#endregion
//#region src/features/scripts/ScriptSource.vue
var _sfc_main$2 = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "ScriptSource",
	props: /*@__PURE__*/ mergeModels({
		saved: Boolean,
		readOnly: Boolean,
		disabled: Boolean
	}, {
		"modelValue": { default: "" },
		"modelModifiers": {},
		"fontSize": { default: 9.25 },
		"fontSizeModifiers": {}
	}),
	emits: /*@__PURE__*/ mergeModels([
		"run",
		"outline",
		"help",
		"saved"
	], ["update:modelValue", "update:fontSize"]),
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const model = useModel(__props, "modelValue"), fontSize = useModel(__props, "fontSize");
		const source = ref(null), host = ref(null), width = ref(0), revision = ref(0);
		const state = computed(() => ({
			...source.value?.frameState,
			historyCount: source.value?.frameState?.historyCount || 1,
			historyIndex: source.value?.frameState?.historyIndex || 0,
			fontSize: fontSize.value,
			readOnly: props.readOnly || props.disabled,
			saved: props.saved,
			busy: props.disabled
		}));
		const scene = computed(() => describe(state.value, width.value, appearance.language, revision.value));
		async function event(action) {
			revision.value++;
			if (action.type === "font") fontSize.value = Number(action.value);
			else if (action.type === "history") await source.value?.historyTo(Number(action.value));
			else if (action.type === "selection") emit("run", source.value?.selectedText);
			else if (["outline", "saved"].includes(action.type)) emit(action.type);
			else if (action.type === "command") {
				if ([
					"cut",
					"copy",
					"paste"
				].includes(action.value)) await source.value?.clipboard(action.value);
				else if (["undo", "redo"].includes(action.value)) await source.value?.[action.value]();
				else if (["find", "replace"].includes(action.value)) source.value?.showFind(action.value === "replace");
				else if (action.value === "help") emit("help");
			}
		}
		let observer;
		onMounted(() => {
			const measure = () => width.value = frameContentWidth(host.value);
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		__expose({
			focus: () => source.value?.focus(),
			goToLine: (line) => source.value?.goToLine(line)
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "script-source"
			}, [createBaseVNode("div", {
				class: "script-source-toolbar",
				style: normalizeStyle({ height: toolbarHeight(width.value) + "px" })
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				style: normalizeStyle({
					width: scene.value.contentWidth + "px",
					height: "30px"
				}),
				onEvent: event
			}, null, 8, ["scene", "style"])], 4), createVNode(_sfc_main$6, mergeProps({
				ref_key: "source",
				ref: source
			}, _ctx.$attrs, {
				modelValue: model.value,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				"font-size": fontSize.value,
				"onUpdate:fontSize": _cache[1] || (_cache[1] = ($event) => fontSize.value = $event),
				"source-toolbar": false,
				"read-only": __props.readOnly,
				disabled: __props.disabled,
				onRun: _cache[2] || (_cache[2] = ($event) => emit("run", $event)),
				onOutline: _cache[3] || (_cache[3] = ($event) => emit("outline")),
				onHelp: _cache[4] || (_cache[4] = ($event) => emit("help"))
			}), null, 16, [
				"modelValue",
				"font-size",
				"read-only",
				"disabled"
			])], 512);
		};
	}
});
//#endregion
//#region ../src/tactic_stream/shared_ui/features/scripts/editor.ui.mjs
var metrics = Object.freeze({
	inset: 8,
	gap: 4,
	toolbar: 32,
	tabs: 38,
	outputHeader: 40,
	footer: 38,
	minimumMain: 360,
	minimumTree: 160
});
function layout(model, width, height) {
	const { inset, gap, toolbar, tabs, outputHeader, footer } = metrics;
	const inner = Math.max(0, width - inset * 2);
	const treeWidth = model.treeHidden ? 0 : Math.min(Math.max(metrics.minimumTree, model.treeWidth || 200), Math.max(0, inner - metrics.minimumMain - gap));
	const mainWidth = inner - (treeWidth ? treeWidth + gap : 0);
	const bodyHeight = Math.max(0, height - inset * 2);
	const noticeHeight = model.notice ? 38 : 0;
	const outputHeight = Math.min(model.outputHidden ? outputHeader : Math.max(80, model.outputHeight || 120), Math.max(outputHeader, bodyHeight - toolbar - tabs - footer - noticeHeight - 128));
	const outputTop = toolbar + gap + tabs + gap;
	const sourceTop = outputTop + outputHeight + gap;
	const footerTop = Math.max(sourceTop, bodyHeight - footer - noticeHeight - gap);
	return {
		main: rect(inset, inset, mainWidth, bodyHeight),
		toolbar: rect(0, 0, mainWidth, toolbar),
		tabs: rect(0, toolbar + gap, mainWidth, tabs),
		output: rect(0, outputTop, mainWidth, outputHeight),
		outputSplitter: rect(0, outputTop + outputHeight, mainWidth, gap),
		source: rect(0, sourceTop, mainWidth, footerTop - sourceTop - gap),
		footer: rect(0, footerTop, mainWidth, footer),
		notice: rect(0, footerTop + footer + gap, mainWidth, noticeHeight),
		treeSplitter: rect(inset + mainWidth, inset, gap, bodyHeight),
		tree: rect(inset + mainWidth + gap, inset, treeWidth, bodyHeight),
		treeVisible: treeWidth > 0
	};
}
function commands(model) {
	const idle = !model.busy && !model.running;
	return {
		create: idle && model.canEdit,
		save: idle && model.editable && !model.uncertain,
		run: idle && model.editable && !!model.source?.trim(),
		refresh: idle,
		triggers: idle && model.canEdit && model.native,
		closeAll: idle && model.tabCount > 0
	};
}
function toolbar(model, width, language) {
	const tr = (text) => translate(text, language), allowed = commands(model);
	const contentWidth = Math.max(480, width), nodes = [];
	nodes.push(button("scriptNew", rect(0, 1, 30, 30), tr("New script"), "add", { type: "create" }, allowed.create, { iconOnly: true }));
	nodes.push(button("scriptSave", rect(34, 1, 30, 30), tr("Save current script to server"), "save", { type: "save" }, allowed.save, { iconOnly: true }));
	const fieldWidth = (contentWidth - 312) / 2;
	nodes.push(node("Field", "scriptFolder", rect(72, 1, fieldWidth, 30), {
		text: model.folder || "",
		label: tr("Script folder"),
		placeholder: tr("Folder"),
		enabled: !model.busy && !model.running,
		readOnly: !model.editable,
		action: { type: "folder" }
	}));
	nodes.push(label("scriptPathSeparator", rect(74 + fieldWidth, 1, 12, 30), "/", muted));
	nodes.push(node("Field", "scriptTitle", rect(88 + fieldWidth, 1, fieldWidth, 30), {
		text: model.title || "",
		label: tr("Script title"),
		placeholder: tr("Title"),
		enabled: !model.busy && !model.running,
		readOnly: !model.editable,
		action: { type: "title" }
	}));
	const languageX = 94 + fieldWidth * 2;
	nodes.push(node("Choice", "scriptLanguage", rect(languageX, 1, 132, 30), {
		value: model.language,
		label: tr("Script language"),
		enabled: !model.busy && !model.running && model.canEdit,
		options: (model.languages || []).map((row) => Object.assign({}, row, { label: tr(row.label) })),
		action: { type: "language" }
	}));
	[
		[
			"triggers",
			"Script triggers",
			"bolt"
		],
		[
			"refresh",
			"Refresh scripts from server",
			"refresh"
		],
		[
			"tree",
			model.treeHidden ? "Show scripts and outline" : "Hide scripts and outline",
			model.treeHidden ? "chevron-left" : "chevron-right"
		]
	].forEach((row, index) => nodes.push(button("script_" + row[0], rect(languageX + 136 + index * 28, 3, 26, 26), tr(row[1]), row[2], { type: row[0] }, row[0] === "tree" || allowed[row[0]], {
		iconOnly: true,
		highlighted: row[0] === "tree" && !model.treeHidden
	})));
	return {
		nodes,
		contentWidth
	};
}
function outputToolbar(model, width, language) {
	const tr = (text) => translate(text, language);
	return { nodes: [
		node("Icon", "scriptOutputIcon", rect(8, 10, 16, 16), {
			icon: "terminal",
			color: "action"
		}),
		label("scriptOutputTitle", rect(30, 4, Math.max(0, width - 126), 28), tr("Output"), { weight: 600 }),
		...[
			[
				"wrap",
				"Wrap output",
				"wrap-lines"
			],
			[
				"clear",
				"Clear output",
				"delete-sweep"
			],
			[
				"output",
				model.outputHidden ? "Expand output" : "Collapse output",
				model.outputHidden ? "expand-more" : "expand-less"
			]
		].map((row, index) => button("scriptOutput_" + row[0], rect(width - 90 + index * 28, 5, 26, 26), tr(row[1]), row[2], { type: row[0] }, row[0] !== "clear" || !!model.output, {
			iconOnly: true,
			highlighted: row[0] === "wrap" && model.outputWrap
		}))
	] };
}
function footer(model, width, language) {
	const tr = (text) => translate(text, language), targetWidth = Math.min(220, Math.max(100, width - 230));
	return { nodes: [
		button("scriptRun", rect(0, 0, 124, 38), tr("Run Script"), "play-arrow", { type: "run" }, commands(model).run, { highlighted: true }),
		label("scriptRunIn", rect(width - targetWidth - 74, 0, 68, 38), tr(model.running ? "Running…" : "Run in"), muted),
		node("Choice", "scriptTarget", rect(width - targetWidth, 0, targetWidth, 38), {
			label: tr("Execution target"),
			value: model.target,
			options: (model.targets || []).map((row) => Object.assign({}, row, { label: row.translate === false ? row.label : tr(row.label) })),
			enabled: model.canEdit && !model.busy && !model.running && (model.targets || []).length > 1,
			action: { type: "target" }
		})
	] };
}
function sideTabs(model, width, language) {
	return { nodes: [node("Segmented", "scriptSideMode", rect(4, 4, Math.max(0, width - 8), 28), {
		label: translate("Scripts panel", language),
		value: model.side,
		options: ["scripts", "outline"].map((value) => ({
			value,
			label: translate(value === "scripts" ? "Scripts" : "Outline", language)
		})),
		action: { type: "side" }
	})] };
}
//#endregion
//#region src/features/scripts/ScriptEditorWorkspace.vue
var _hoisted_1$1 = { class: "script-editor-side-content" };
var _sfc_main$1 = {
	__name: "ScriptEditorWorkspace",
	props: { model: {
		type: Object,
		required: true
	} },
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 0,
			height: 0
		});
		const bounds = computed(() => layout(props.model, viewport.value.width, viewport.value.height));
		const toolbar$2 = computed(() => toolbar(props.model, bounds.value.main.width, appearance.language));
		const output = computed(() => outputToolbar(props.model, bounds.value.output.width, appearance.language));
		const footer$1 = computed(() => footer(props.model, bounds.value.main.width, appearance.language));
		const side = computed(() => sideTabs(props.model, bounds.value.tree.width, appearance.language));
		const style = (rect) => ({
			position: "absolute",
			left: rect.x + "px",
			top: rect.y + "px",
			width: rect.width + "px",
			height: rect.height + "px"
		});
		let observer;
		onMounted(() => {
			const measure = () => {
				viewport.value = {
					width: frameContentWidth(host.value),
					height: host.value.clientHeight
				};
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
				class: "script-editor-workspace"
			}, [
				createBaseVNode("div", {
					class: "script-editor-main",
					style: normalizeStyle(style(bounds.value.main))
				}, [
					createBaseVNode("div", {
						class: "script-editor-toolbar",
						style: normalizeStyle(style(bounds.value.toolbar))
					}, [createVNode(_sfc_main$5, {
						style: normalizeStyle({
							width: toolbar$2.value.contentWidth + "px",
							height: "32px"
						}),
						scene: toolbar$2.value,
						onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
					}, null, 8, ["style", "scene"])], 4),
					createBaseVNode("div", { style: normalizeStyle(style(bounds.value.tabs)) }, [renderSlot(_ctx.$slots, "tabs")], 4),
					createBaseVNode("section", {
						class: normalizeClass(["script-editor-output", { wrapped: __props.model.outputWrap }]),
						style: normalizeStyle(style(bounds.value.output))
					}, [createVNode(_sfc_main$5, {
						class: "script-editor-output-header",
						scene: output.value,
						onEvent: _cache[1] || (_cache[1] = ($event) => emit("event", $event))
					}, null, 8, ["scene"]), renderSlot(_ctx.$slots, "output")], 6),
					!__props.model.outputHidden ? (openBlock(), createBlock(_sfc_main$7, {
						key: 0,
						style: normalizeStyle(style(bounds.value.outputSplitter)),
						horizontal: "",
						"model-value": bounds.value.output.height,
						label: "Output height",
						min: 80,
						max: 500,
						"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => emit("event", {
							type: "outputHeight",
							value: $event
						}))
					}, null, 8, ["style", "model-value"])) : createCommentVNode("", true),
					createBaseVNode("div", {
						class: "script-editor-code",
						style: normalizeStyle(style(bounds.value.source))
					}, [renderSlot(_ctx.$slots, "source")], 4),
					createBaseVNode("div", { style: normalizeStyle(style(bounds.value.footer)) }, [createVNode(_sfc_main$5, {
						scene: footer$1.value,
						onEvent: _cache[3] || (_cache[3] = ($event) => emit("event", $event))
					}, null, 8, ["scene"])], 4),
					createBaseVNode("div", {
						class: "script-editor-notice",
						style: normalizeStyle(style(bounds.value.notice))
					}, [renderSlot(_ctx.$slots, "notice")], 4)
				], 4),
				bounds.value.treeVisible ? (openBlock(), createBlock(_sfc_main$7, {
					key: 0,
					style: normalizeStyle(style(bounds.value.treeSplitter)),
					reverse: "",
					"model-value": bounds.value.tree.width,
					label: "Scripts panel width",
					min: 160,
					max: 500,
					"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => emit("event", {
						type: "treeWidth",
						value: $event
					}))
				}, null, 8, ["style", "model-value"])) : createCommentVNode("", true),
				bounds.value.treeVisible ? (openBlock(), createElementBlock("aside", {
					key: 1,
					class: "script-editor-tree",
					style: normalizeStyle(style(bounds.value.tree))
				}, [createVNode(_sfc_main$5, {
					class: "script-editor-side-tabs",
					scene: side.value,
					onEvent: _cache[5] || (_cache[5] = ($event) => emit("event", $event))
				}, null, 8, ["scene"]), createBaseVNode("div", _hoisted_1$1, [renderSlot(_ctx.$slots, "tree")])], 4)) : createCommentVNode("", true)
			], 512);
		};
	}
};
//#endregion
//#region src/features/scripts/ScriptEditor.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "script-editor-header" };
var _hoisted_3 = {
	key: 0,
	tabindex: "0"
};
var _hoisted_4 = {
	key: 1,
	class: "script-editor-empty muted"
};
var _hoisted_5 = ["aria-label"];
var _hoisted_6 = {
	key: 0,
	class: "muted"
};
var _hoisted_7 = {
	key: 0,
	class: "muted"
};
var _hoisted_8 = {
	key: 1,
	class: "muted"
};
var _hoisted_9 = {
	key: 2,
	class: "error"
};
var _hoisted_10 = {
	key: 3,
	class: "error",
	role: "alert"
};
var _hoisted_11 = ["aria-label"];
var _hoisted_12 = {
	key: 0,
	class: "error"
};
var _hoisted_13 = { class: "configuration-actions" };
var _hoisted_14 = ["aria-label"];
var _sfc_main = {
	__name: "ScriptEditor",
	props: {
		ticket: String,
		project: String,
		login: String,
		searchType: String,
		searchKeys: Array,
		updates: Object
	},
	emits: [
		"saved",
		"executed",
		"closed"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const openHelp = inject("openHelp");
		const props = __props;
		const emit = __emit;
		const dialog = ref(null), confirmation = ref(null), historyDialog = ref(null), editor = ref(null), actions = ref(null);
		const catalog = ref(null), tabs = ref([]), selected = ref(""), busy = ref(false), error = ref(""), running = ref(""), uncertain = ref(false);
		const fontSize = ref(9.25), analysis = ref(null), analysisError = ref(""), symbolLine = ref(0), filter = ref(null);
		const scriptQuery = ref(""), outlineQuery = ref(""), side = ref("scripts"), treeHidden = ref(false), treeWidth = ref(200), outputHeight = ref(120), outputHidden = ref(false), outputWrap = ref(false), historyRows = ref([]);
		const query = computed({
			get: () => side.value === "scripts" ? scriptQuery.value : outlineQuery.value,
			set: (value) => {
				if (side.value === "scripts") scriptQuery.value = value;
				else outlineQuery.value = value;
			}
		});
		const confirmAction = ref(""), confirmTitle = ref(""), pending = ref(null);
		let generation = 0, analysisGeneration = 0, persistTimer, restoring = true, stateKey = storageKey(), reloadPending = false;
		const active = computed(() => tabs.value.find((tab) => tab.id === selected.value));
		const supported = computed(() => [
			"python",
			"javascript",
			"server_js"
		].includes(active.value?.language));
		const editable = computed(() => !!catalog.value?.canEdit && supported.value);
		const dirty = (tab) => JSON.stringify(fields(tab)) !== tab.baseline;
		const tree = computed(() => scriptTree((catalog.value?.scripts || []).filter((row) => !row.retired).map((row) => ({
			path: [row.folder, row.title].filter(Boolean).join("/"),
			language: row.language,
			runnable: true
		}))));
		const allSymbols = computed(() => analysis.value?.bufferKey === active.value?.id && analysis.value?.source === active.value?.source ? analysis.value.symbols : []);
		const symbols = computed(() => allSymbols.value.filter((row) => (row.qualifiedName || row.name).toLowerCase().includes(query.value.toLowerCase())));
		async function analyse(request) {
			const id = ++analysisGeneration, context = generation, tab = active.value;
			if (!tab || tab.id !== request.bufferKey || !catalog.value?.canEdit) return;
			try {
				const result = tab.language === "python" ? await scriptEditor("analyse", props.ticket, props.project, {
					source: request.source,
					cursor: request.cursor,
					manual: request.manual
				}) : {
					symbols: documentSymbols(request.source, "javascript"),
					completions: request.manual || /[\w$]{2}$/.test(request.source.slice(0, request.cursor)) ? completions(request.source, request.cursor, "javascript").map((row) => ({
						...row,
						label: row.name,
						kind: "variable",
						insertText: row.name
					})) : []
				};
				if (id === analysisGeneration && context === generation && active.value?.id === tab.id && tab.source === request.source) {
					analysis.value = {
						...request,
						...result
					};
					analysisError.value = "";
				}
			} catch (exception) {
				if (id === analysisGeneration && context === generation) analysisError.value = exception.message;
			}
		}
		function showOutline() {
			treeHidden.value = false;
			side.value = "outline";
			nextTick(() => {
				const input = filter.value?.$el.querySelector("input");
				input?.focus();
				input?.select();
			});
		}
		function goToSymbol(row) {
			symbolLine.value = row.line;
			editor.value?.goToLine(row.line);
		}
		function fields(tab) {
			return {
				folder: tab.folder,
				title: tab.title,
				language: tab.language,
				source: tab.source
			};
		}
		function storageKey() {
			return "tactic_stream.script_editor." + props.login + "." + props.project;
		}
		function persist() {
			if (restoring) return;
			try {
				localStorage.setItem(stateKey, JSON.stringify({
					tabs: tabs.value,
					selected: selected.value,
					treeWidth: treeWidth.value,
					outputHeight: outputHeight.value,
					treeHidden: treeHidden.value,
					outputHidden: outputHidden.value,
					outputWrap: outputWrap.value,
					fontSize: fontSize.value,
					side: side.value
				}));
			} catch {
				error.value = t("The browser could not store the script drafts. Keep this window open until you save them.");
			}
		}
		watch([
			tabs,
			selected,
			treeWidth,
			outputHeight,
			treeHidden,
			outputHidden,
			outputWrap,
			fontSize,
			side
		], () => {
			if (restoring) return;
			clearTimeout(persistTimer);
			persistTimer = setTimeout(persist, 250);
		}, { deep: true });
		function restore() {
			try {
				const saved = JSON.parse(localStorage.getItem(storageKey()) || "null");
				if (!saved || !Array.isArray(saved.tabs)) return;
				tabs.value = saved.tabs.filter((tab) => typeof tab.id === "string" && [
					"code",
					"folder",
					"title",
					"language",
					"source",
					"baseline",
					"revision",
					"output"
				].every((field) => typeof tab[field] === "string")).slice(0, 120);
				selected.value = tabs.value.some((tab) => tab.id === saved.selected) ? saved.selected : tabs.value[0]?.id || "";
				treeWidth.value = Math.min(500, Math.max(140, Number(saved.treeWidth) || 200));
				outputHeight.value = Math.min(500, Math.max(80, Number(saved.outputHeight) || 120));
				fontSize.value = Math.min(15, Math.max(8, Number(saved.fontSize) || 9.25));
				treeHidden.value = !!saved.treeHidden;
				outputHidden.value = !!saved.outputHidden;
				outputWrap.value = !!saved.outputWrap;
				side.value = saved.side === "outline" ? "outline" : "scripts";
			} catch {
				error.value = t("The browser script draft could not be restored.");
			}
		}
		function create(row) {
			const tab = {
				id: buttonId(),
				code: row?.code || "",
				folder: row?.folder || "",
				title: row?.title || "new_script",
				language: row?.language || "python",
				source: row?.source || "",
				revision: row?.revision || "",
				output: "",
				missing: false
			};
			tab.baseline = JSON.stringify(fields(tab));
			tabs.value.push(tab);
			selected.value = tab.id;
			return tab;
		}
		function openScript(path) {
			const row = catalog.value?.scripts.find((row) => [row.folder, row.title].filter(Boolean).join("/") === path);
			if (!row) return;
			const tab = tabs.value.find((tab) => tab.code === row.code) || create(row);
			selected.value = tab.id;
			nextTick(() => editor.value?.focus());
		}
		function reconcile() {
			for (const tab of tabs.value.filter((tab) => tab.code)) {
				const row = catalog.value.scripts.find((row) => row.code === tab.code);
				tab.missing = !row;
				if (row && !dirty(tab)) {
					Object.assign(tab, fields(row), { revision: row.revision });
					tab.baseline = JSON.stringify(fields(tab));
				}
			}
		}
		async function load() {
			reloadPending = false;
			const id = ++generation;
			busy.value = true;
			error.value = "";
			try {
				const result = await scriptEditor("read", props.ticket, props.project);
				if (id !== generation) return;
				catalog.value = result;
				uncertain.value = false;
				reconcile();
			} catch (exception) {
				if (id === generation) error.value = exception.message;
			} finally {
				if (id === generation) busy.value = false;
			}
		}
		async function open(path = "") {
			dialog.value.show();
			if (!catalog.value) {
				await load();
				if (catalog.value && !tabs.value.length) {
					restore();
					reconcile();
				}
				restoring = !catalog.value;
			} else await load();
			if (catalog.value && !tabs.value.length) create();
			if (path) openScript(path);
			nextTick(() => editor.value?.focus());
		}
		function ask(action, target) {
			pending.value = target;
			confirmAction.value = action;
			confirmTitle.value = action === "delete" ? t("Delete “{name}”?", { name: target.folder + "/" + target.title }) : action === "reload" ? t("Discard changes?") : t("Save changes before closing?");
			confirmation.value.show();
		}
		function removeTabs(ids) {
			tabs.value = tabs.value.filter((tab) => !ids.includes(tab.id));
			if (!tabs.value.some((tab) => tab.id === selected.value)) selected.value = tabs.value.at(-1)?.id || "";
		}
		function closeTab(id) {
			const tab = tabs.value.find((tab) => tab.id === id);
			if (!tab || busy.value || running.value) return;
			if (dirty(tab)) ask("tabs", [id]);
			else removeTabs([id]);
		}
		function closeAll() {
			if (busy.value || running.value) return;
			const ids = tabs.value.map((tab) => tab.id);
			if (tabs.value.some(dirty)) ask("tabs", ids);
			else removeTabs(ids);
		}
		function close() {
			if (busy.value || running.value) return;
			persist();
			dialog.value.close();
			emit("closed");
		}
		async function save(tab = active.value) {
			if (!tab || !catalog.value?.canEdit || busy.value || uncertain.value || ![
				"python",
				"javascript",
				"server_js"
			].includes(tab.language)) return false;
			const snapshot = fields(tab), id = generation;
			busy.value = true;
			error.value = "";
			try {
				const result = await scriptEditor("save", props.ticket, props.project, {
					...snapshot,
					code: tab.code,
					revision: tab.code ? tab.revision : catalog.value.revision
				});
				if (id !== generation) return false;
				catalog.value = result;
				const row = result.scripts.find((row) => row.code === result.savedCode);
				tab.code = row.code;
				tab.revision = row.revision;
				tab.missing = false;
				tab.baseline = JSON.stringify(fields(row));
				if (JSON.stringify(fields(tab)) === JSON.stringify(snapshot)) Object.assign(tab, fields(row));
				persist();
				emit("saved");
				return true;
			} catch (exception) {
				if (id === generation) {
					error.value = exception.message;
					uncertain.value = !["invalid_request", "access_denied"].includes(exception.code);
				}
				return false;
			} finally {
				if (id === generation) busy.value = false;
			}
		}
		async function accept(saveFirst = false) {
			if (confirmAction.value === "reload") {
				const row = catalog.value.scripts.find((row) => row.code === pending.value.code);
				if (row) {
					Object.assign(pending.value, fields(row), { revision: row.revision });
					pending.value.baseline = JSON.stringify(fields(row));
					uncertain.value = false;
				}
				confirmation.value.close();
				return;
			}
			if (confirmAction.value === "delete") {
				const tab = pending.value, id = generation;
				busy.value = true;
				try {
					const result = await scriptEditor("delete", props.ticket, props.project, {
						code: tab.code,
						revision: tab.revision
					});
					if (id !== generation) return;
					catalog.value = result;
					removeTabs(tabs.value.filter((row) => row.code === tab.code).map((row) => row.id));
					emit("saved");
					confirmation.value.close();
				} catch (exception) {
					if (id === generation) {
						error.value = exception.message;
						uncertain.value = !["invalid_request", "access_denied"].includes(exception.code);
					}
				} finally {
					if (id === generation) busy.value = false;
				}
				return;
			}
			const ids = pending.value;
			if (saveFirst) for (const id of ids) {
				const tab = tabs.value.find((tab) => tab.id === id);
				if (tab && dirty(tab) && !await save(tab)) return;
			}
			removeTabs(ids);
			confirmation.value.close();
			persist();
		}
		async function run(source = active.value?.source) {
			const tab = active.value;
			if (!editable.value || running.value || busy.value || !source?.trim()) return;
			const id = generation, context = {
				ticket: props.ticket,
				project: props.project,
				searchType: props.searchType,
				searchKeys: [...props.searchKeys || []]
			};
			running.value = tab.id;
			error.value = "";
			const started = performance.now();
			const activity = beginActivity(context.ticket, "Running…");
			try {
				const format = (value) => {
					if (typeof value === "string") return value;
					try {
						return JSON.stringify(value, null, 2) ?? String(value);
					} catch {
						return String(value);
					}
				};
				const scriptConsole = Object.fromEntries([
					"log",
					"info",
					"warn",
					"error",
					"debug",
					"table"
				].map((method) => [method, (...args) => {
					globalThis.console[method](...args);
					if (id === generation) appendOutput(tab, args.map(format).join(" ") + "\n");
				}]));
				const result = tab.language === "javascript" ? await runBrowserScript(source, {
					project: context.project,
					searchType: context.searchType,
					searchKeys: context.searchKeys,
					console: {
						...globalThis.console,
						...scriptConsole
					},
					rpc: (method, args = [], kwargs = {}) => rpc(method, [{
						ticket: context.ticket,
						project: context.project
					}, ...args], kwargs),
					refresh: () => {
						if (id === generation) emit("executed");
					}
				}) : await rpc(tab.language === "server_js" ? "execute_js_script" : "execute_python_script", [
					{
						ticket: context.ticket,
						project: context.project
					},
					"",
					{ code: source }
				]);
				if (id === generation) {
					appendOutput(tab, `${t("Execution time")}: ${((performance.now() - started) / 1e3).toFixed(3)}s\n${format(result)}\n`);
					emit("executed");
				}
			} catch (exception) {
				if (id === generation) {
					appendOutput(tab, (exception.stack || exception.message) + "\n");
					error.value = exception.message;
				}
			} finally {
				endActivity(activity);
				if (id === generation) running.value = "";
			}
		}
		function appendOutput(tab, value) {
			tab.output = (tab.output + value).slice(-2e5);
			outputHidden.value = false;
			nextTick(() => {
				const output = dialog.value.querySelector(".script-editor-output pre");
				if (output) output.scrollTop = output.scrollHeight;
			});
		}
		async function history() {
			if (!active.value?.code || busy.value) return;
			const tab = active.value, id = generation;
			busy.value = true;
			historyRows.value = [];
			historyDialog.value.show();
			try {
				const result = await scriptEditor("history", props.ticket, props.project, { code: tab.code });
				if (id === generation) historyRows.value = result.history;
			} catch (exception) {
				if (id === generation) error.value = exception.message;
			} finally {
				if (id === generation) busy.value = false;
			}
		}
		async function restoreRevision(row) {
			if (!editable.value || busy.value) return;
			const tab = active.value, id = generation;
			busy.value = true;
			try {
				const result = await scriptEditor("revision", props.ticket, props.project, {
					code: tab.code,
					revision_id: row.revisionId
				});
				if (id === generation) {
					const source = result.revision;
					Object.assign(tab, {
						folder: source.folder,
						title: source.title,
						language: source.language,
						source: source.script
					});
					historyDialog.value.close();
				}
			} catch (exception) {
				if (id === generation) error.value = exception.message;
			} finally {
				if (id === generation) busy.value = false;
			}
		}
		async function runner() {
			if (!active.value?.code) return;
			const saved = catalog.value.scripts.find((row) => row.code === active.value.code);
			if (!saved) return;
			const path = saved.folder + "/" + saved.title;
			const source = saved.language === "javascript" ? `if (project !== ${JSON.stringify(props.project)}) throw new Error('Run this script in its saved project');\nconst scripts = await rpc('query', ['config/custom_script'], {filters: [['folder', ${JSON.stringify(saved.folder)}], ['title', ${JSON.stringify(saved.title)}]], limit: 2});\nif (scripts.length !== 1 || scripts[0].language !== 'javascript') throw new Error('Saved JavaScript script is unavailable');\nconst url = URL.createObjectURL(new Blob(['export default async function(context) {\\nconst {project, searchType, searchKeys, rpc, refresh, console = globalThis.console} = context;\\n' + scripts[0].script + '\\n}'], {type: 'text/javascript'}));\ntry { const module = await import(url); return await module.default(context); }\nfinally { URL.revokeObjectURL(url); }\n` : `server.set_project(${JSON.stringify(props.project)})\nserver.${saved.language === "server_js" ? "execute_js_script" : "execute_python_script"}(${JSON.stringify(path)}, {})`;
			try {
				await copyText(source);
				appendOutput(active.value, t("Script runner copied to clipboard.") + "\n");
			} catch (exception) {
				error.value = exception.message;
			}
		}
		function key(event) {
			if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
				event.preventDefault();
				save();
			} else if (event.key === "F5") {
				event.preventDefault();
				run();
			}
		}
		watch(() => [
			props.ticket,
			props.project,
			props.login
		], () => {
			clearTimeout(persistTimer);
			persist();
			restoring = true;
			stateKey = storageKey();
			generation++;
			busy.value = false;
			running.value = "";
			catalog.value = null;
			tabs.value = [];
			selected.value = "";
			uncertain.value = false;
			error.value = "";
			analysisGeneration++;
			analysis.value = null;
			analysisError.value = "";
			if (dialog.value?.open) {
				const id = generation + 1;
				load().then(() => {
					if (id === generation && catalog.value) {
						restore();
						reconcile();
						restoring = false;
						if (!tabs.value.length) create();
					}
				});
			}
		}, { flush: "sync" });
		onBeforeUnmount(() => {
			clearTimeout(persistTimer);
			persist();
			generation++;
			analysisGeneration++;
		});
		function refreshUpdates() {
			if (reloadPending && dialog.value?.open && !busy.value && !running.value) load();
		}
		watch(() => props.updates, (batch) => {
			if (dialog.value?.open && [...batch?.cacheChanges || [], ...batch?.cacheRetired || []].some((row) => row.projectCode === props.project && row.searchType === "config/custom_script")) {
				reloadPending = true;
				refreshUpdates();
			}
		});
		watch([busy, running], refreshUpdates);
		const frameModel = computed(() => ({
			native: false,
			canEdit: !!catalog.value?.canEdit,
			editable: editable.value,
			busy: busy.value,
			running: !!running.value,
			uncertain: uncertain.value,
			folder: active.value?.folder || "",
			title: active.value?.title || "",
			source: active.value?.source || "",
			language: active.value?.language || "python",
			languages: [
				{
					value: "python",
					label: "Server Python"
				},
				{
					value: "javascript",
					label: "JavaScript"
				},
				{
					value: "server_js",
					label: "Server JavaScript"
				},
				...!supported.value && active.value ? [{
					value: active.value.language,
					label: active.value.language
				}] : []
			],
			targets: [{
				value: active.value?.language === "javascript" ? "browser" : "server",
				label: active.value?.language === "javascript" ? "Browser" : "Server"
			}],
			target: active.value?.language === "javascript" ? "browser" : "server",
			treeHidden: treeHidden.value,
			treeWidth: treeWidth.value,
			side: side.value,
			outputHidden: outputHidden.value,
			outputHeight: outputHeight.value,
			outputWrap: outputWrap.value,
			output: active.value?.output || "",
			tabCount: tabs.value.length,
			notice: error.value || analysisError.value || active.value?.missing || catalog.value && (!catalog.value.canEdit || !supported.value)
		}));
		function frameEvent(action) {
			if ([
				"folder",
				"title",
				"language"
			].includes(action.type) && active.value) active.value[action.type] = action.value;
			else if (action.type === "create") create();
			else if (action.type === "save") save();
			else if (action.type === "run") run();
			else if (action.type === "refresh") load();
			else if (action.type === "tree") treeHidden.value = !treeHidden.value;
			else if (action.type === "output") outputHidden.value = !outputHidden.value;
			else if (action.type === "wrap") outputWrap.value = !outputWrap.value;
			else if (action.type === "clear" && active.value) active.value.output = "";
			else if (action.type === "side") side.value = action.value;
			else if (action.type === "treeWidth") treeWidth.value = action.value;
			else if (action.type === "outputHeight") outputHeight.value = action.value;
		}
		__expose({
			open,
			reload: load
		});
		return (_ctx, _cache) => {
			const _directive_window = resolveDirective("window");
			return openBlock(), createBlock(Teleport, { to: "body" }, [
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "dialog",
					ref: dialog,
					class: "script-editor-dialog",
					style: normalizeStyle({ "--editor-font-size": fontSize.value + "pt" }),
					"aria-label": unref(t)("Script Editor"),
					onCancel: withModifiers(close, ["prevent"]),
					onKeydown: key,
					"aria-busy": busy.value || !!running.value
				}, [createBaseVNode("header", _hoisted_2, [
					createVNode(_sfc_main$3, { name: "code" }),
					createBaseVNode("strong", null, toDisplayString(unref(t)("Script Editor")), 1),
					createVNode(_sfc_main$4, {
						"icon-only": "",
						icon: "help",
						label: "Script editor help",
						onClick: _cache[0] || (_cache[0] = ($event) => unref(openHelp)("script_editor"))
					}),
					createVNode(_sfc_main$4, {
						"icon-only": "",
						icon: "close",
						label: "Close script editor",
						disabled: busy.value || !!running.value,
						onClick: close
					}, null, 8, ["disabled"])
				]), createVNode(_sfc_main$1, {
					model: frameModel.value,
					onEvent: frameEvent
				}, {
					tabs: withCtx(() => [createVNode(_sfc_main$9, {
						kind: "script",
						tabs: tabs.value.map((tab) => ({
							id: tab.id,
							title: tab.title,
							dirty: dirty(tab)
						})),
						selected: selected.value,
						disabled: busy.value,
						onSelect: _cache[3] || (_cache[3] = ($event) => selected.value = $event),
						onAdd: _cache[4] || (_cache[4] = ($event) => create()),
						onClose: closeTab,
						onReorder: _cache[5] || (_cache[5] = (from, to) => tabs.value.splice(to, 0, tabs.value.splice(from, 1)[0]))
					}, {
						actions: withCtx(() => [createVNode(_sfc_main$4, {
							"icon-only": "",
							icon: "close",
							label: "Close all script tabs",
							disabled: busy.value || !!running.value,
							onClick: closeAll
						}, null, 8, ["disabled"]), createVNode(_sfc_main$8, {
							ref_key: "actions",
							ref: actions,
							overlay: "",
							label: "Saved script actions",
							"close-on-select": true
						}, {
							default: withCtx(() => [
								createVNode(_sfc_main$4, {
									icon: "refresh",
									label: "Reload saved source",
									disabled: !active.value?.code || busy.value,
									onClick: _cache[1] || (_cache[1] = ($event) => ask("reload", active.value))
								}, null, 8, ["disabled"]),
								createVNode(_sfc_main$4, {
									icon: "copy",
									label: "Copy Script Runner",
									disabled: !active.value?.code,
									onClick: runner
								}, null, 8, ["disabled"]),
								createVNode(_sfc_main$4, {
									destructive: "",
									icon: "delete",
									label: "Delete from server",
									disabled: !editable.value || !active.value?.code || busy.value || uncertain.value,
									onClick: _cache[2] || (_cache[2] = ($event) => ask("delete", active.value))
								}, null, 8, ["disabled"])
							]),
							_: 1
						}, 512)]),
						_: 1
					}, 8, [
						"tabs",
						"selected",
						"disabled"
					])]),
					output: withCtx(() => [!outputHidden.value && active.value ? (openBlock(), createElementBlock("pre", _hoisted_3, toDisplayString(active.value.output), 1)) : createCommentVNode("", true)]),
					source: withCtx(() => [active.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						ref_key: "editor",
						ref: editor,
						modelValue: active.value.source,
						"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => active.value.source = $event),
						"font-size": fontSize.value,
						"onUpdate:fontSize": _cache[7] || (_cache[7] = ($event) => fontSize.value = $event),
						saved: !!active.value.code,
						analysis: analysis.value,
						"buffer-key": active.value.id,
						language: active.value.language === "server_js" ? "javascript" : active.value.language,
						"read-only": !editable.value,
						disabled: busy.value || !!running.value,
						onRun: run,
						onAnalyse: analyse,
						onOutline: showOutline,
						onSaved: history,
						onHelp: _cache[8] || (_cache[8] = ($event) => unref(openHelp)("script_editor"))
					}, null, 8, [
						"modelValue",
						"font-size",
						"saved",
						"analysis",
						"buffer-key",
						"language",
						"read-only",
						"disabled"
					])) : (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString(unref(t)("Open a script or create a new one.")), 1))]),
					tree: withCtx(() => [createVNode(AppSearchField_default, {
						ref_key: "filter",
						ref: filter,
						modelValue: query.value,
						"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => query.value = $event),
						label: "Search scripts and symbols",
						onKeydown: _cache[10] || (_cache[10] = withKeys(withModifiers(($event) => side.value === "outline" && symbols.value.length && goToSymbol(symbols.value[0]), ["prevent"]), ["enter"])),
						placeholder: unref(t)(side.value === "scripts" ? "Search scripts" : "Filter classes and methods")
					}, null, 8, ["modelValue", "placeholder"]), side.value === "scripts" ? (openBlock(), createBlock(_sfc_main$10, {
						key: 0,
						entries: tree.value,
						query: query.value,
						selected: active.value ? active.value.folder + "/" + active.value.title : "",
						onSelect: _cache[11] || (_cache[11] = ($event) => openScript($event.key)),
						onContextmenu: _cache[12] || (_cache[12] = withModifiers((event) => {
							const path = event.target.closest("[data-entry-key]")?.dataset.entryKey;
							if (path && !path.startsWith("folder:")) {
								openScript(path);
								nextTick(() => actions.value.open = true);
							}
						}, ["prevent"]))
					}, null, 8, [
						"entries",
						"query",
						"selected"
					])) : (openBlock(), createElementBlock("nav", {
						key: 1,
						class: "script-editor-outline",
						"aria-label": unref(t)("Outline")
					}, [(openBlock(true), createElementBlock(Fragment, null, renderList(symbols.value, (row) => {
						return openBlock(), createBlock(_sfc_main$4, {
							key: row.qualifiedName || row.position,
							icon: row.kind === "class" ? "MDI_FORMAT_SIZE" : "code",
							label: (row.qualifiedName || row.name) + " · " + row.line,
							title: row.detail,
							"aria-current": symbolLine.value === row.line,
							style: normalizeStyle({ paddingLeft: 7 + (row.depth || 0) * 14 + "px" }),
							onClick: ($event) => goToSymbol(row)
						}, {
							default: withCtx(() => [createBaseVNode("span", null, toDisplayString(row.name), 1), createBaseVNode("small", null, toDisplayString(row.line), 1)]),
							_: 2
						}, 1032, [
							"icon",
							"label",
							"title",
							"aria-current",
							"style",
							"onClick"
						]);
					}), 128)), !allSymbols.value.length ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString(unref(t)("No classes or methods")), 1)) : createCommentVNode("", true)], 8, _hoisted_5))]),
					notice: withCtx(() => [
						!catalog.value?.canEdit && catalog.value ? (openBlock(), createElementBlock("p", _hoisted_7, toDisplayString(unref(t)("Read-only: script changes and execution require administrator access.")), 1)) : !supported.value && active.value ? (openBlock(), createElementBlock("p", _hoisted_8, toDisplayString(unref(t)("This legacy language is read-only in the web editor")), 1)) : createCommentVNode("", true),
						active.value?.missing ? (openBlock(), createElementBlock("p", _hoisted_9, toDisplayString(unref(t)("This script was deleted on the server. Its local draft is preserved.")), 1)) : createCommentVNode("", true),
						error.value || analysisError.value ? (openBlock(), createElementBlock("p", _hoisted_10, toDisplayString(unref(t)(error.value || analysisError.value)), 1)) : createCommentVNode("", true)
					]),
					_: 1
				}, 8, ["model"])], 44, _hoisted_1)), [[_directive_window, {
					kind: "script_editor",
					type: "window"
				}]]),
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "confirmation",
					ref: confirmation,
					class: "record-dialog",
					"aria-label": confirmTitle.value,
					onCancel: _cache[16] || (_cache[16] = withModifiers(($event) => !busy.value && confirmation.value.close(), ["prevent"]))
				}, [
					createBaseVNode("h2", null, toDisplayString(confirmTitle.value), 1),
					createBaseVNode("p", null, toDisplayString(confirmAction.value === "delete" ? unref(t)("Deleting the saved script does not remove its shelf buttons; they become unavailable.") : unref(t)("Save, discard the selected drafts, or return to editing.")), 1),
					error.value ? (openBlock(), createElementBlock("p", _hoisted_12, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
					createBaseVNode("div", _hoisted_13, [
						confirmAction.value === "tabs" ? (openBlock(), createBlock(_sfc_main$4, {
							key: 0,
							label: "Save",
							icon: "save",
							disabled: busy.value || uncertain.value || !catalog.value?.canEdit,
							onClick: _cache[13] || (_cache[13] = ($event) => accept(true))
						}, null, 8, ["disabled"])) : createCommentVNode("", true),
						createVNode(_sfc_main$4, {
							label: confirmAction.value === "delete" ? "Delete" : "Discard",
							destructive: "",
							disabled: busy.value || !!running.value,
							onClick: _cache[14] || (_cache[14] = ($event) => accept())
						}, null, 8, ["label", "disabled"]),
						createVNode(_sfc_main$4, {
							label: "Cancel",
							disabled: busy.value,
							onClick: _cache[15] || (_cache[15] = ($event) => confirmation.value.close())
						}, null, 8, ["disabled"])
					])
				], 40, _hoisted_11)), [[_directive_window, { type: "popup" }]]),
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "historyDialog",
					ref: historyDialog,
					class: "record-dialog script-editor-history",
					"aria-label": unref(t)("Saved revisions")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Saved revisions")), 1), createVNode(_sfc_main$4, {
						label: "Close",
						icon: "close",
						onClick: _cache[17] || (_cache[17] = ($event) => historyDialog.value.close())
					})]),
					createBaseVNode("p", null, toDisplayString(unref(t)("Restoring a revision changes the local draft. Save publishes it as a new revision.")), 1),
					(openBlock(true), createElementBlock(Fragment, null, renderList(historyRows.value, (row) => {
						return openBlock(), createBlock(_sfc_main$4, {
							key: row.revisionId,
							label: [
								row.timestamp,
								row.actor,
								row.changedFields.join(", ") || unref(t)("Saved version")
							].filter(Boolean).join(" · "),
							disabled: !editable.value || busy.value,
							onClick: ($event) => restoreRevision(row)
						}, null, 8, [
							"label",
							"disabled",
							"onClick"
						]);
					}), 128))
				], 8, _hoisted_14)), [[_directive_window, { type: "popup" }]])
			]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=ScriptEditor.js.map
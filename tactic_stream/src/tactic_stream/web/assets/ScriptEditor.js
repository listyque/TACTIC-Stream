import { C as inject, E as nextTick, G as withCtx, H as watch, I as resolveDirective, K as withDirectives, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, o as vModelText, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment } from "./vue.js";
import { c as _sfc_main$2, f as _sfc_main$1, k as t } from "./index.js";
import { a as _sfc_main$4, b as _sfc_main$3, c as completions, d as _sfc_main$6, g as AppSearchField_default, l as documentSymbols, s as _sfc_main$5 } from "./FrameView.js";
import { F as rpc, L as scriptEditor, _ as endActivity, f as _sfc_main$7, h as beginActivity, o as copyText } from "./CodeBlock.js";
import { E as _sfc_main$9, S as _sfc_main$8, c as runBrowserScript, l as scriptTree, s as buttonId } from "./App.js";
//#region src/features/scripts/ScriptEditor.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "script-editor-header" };
var _hoisted_3 = { class: "script-editor-screen" };
var _hoisted_4 = { class: "script-editor-main" };
var _hoisted_5 = { class: "script-editor-toolbar" };
var _hoisted_6 = [
	"readonly",
	"placeholder",
	"aria-label"
];
var _hoisted_7 = [
	"readonly",
	"placeholder",
	"aria-label"
];
var _hoisted_8 = {
	key: 0,
	tabindex: "0"
};
var _hoisted_9 = {
	key: 2,
	class: "script-editor-code"
};
var _hoisted_10 = {
	key: 3,
	class: "script-editor-empty muted"
};
var _hoisted_11 = {
	key: 4,
	class: "muted"
};
var _hoisted_12 = {
	key: 5,
	class: "muted"
};
var _hoisted_13 = {
	key: 6,
	class: "error"
};
var _hoisted_14 = {
	key: 7,
	class: "error",
	role: "alert"
};
var _hoisted_15 = ["aria-label"];
var _hoisted_16 = {
	key: 0,
	class: "muted"
};
var _hoisted_17 = ["aria-label"];
var _hoisted_18 = {
	key: 0,
	class: "error"
};
var _hoisted_19 = { class: "configuration-actions" };
var _hoisted_20 = ["aria-label"];
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
					createVNode(_sfc_main$1, { name: "code" }),
					createBaseVNode("strong", null, toDisplayString(unref(t)("Script Editor")), 1),
					createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "help",
						label: "Script editor help",
						onClick: _cache[0] || (_cache[0] = ($event) => unref(openHelp)("script_editor"))
					}),
					createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "close",
						label: "Close script editor",
						disabled: busy.value || !!running.value,
						onClick: close
					}, null, 8, ["disabled"])
				]), createBaseVNode("div", _hoisted_3, [
					createBaseVNode("div", _hoisted_4, [
						createBaseVNode("div", _hoisted_5, [
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "add",
								label: "New script",
								disabled: busy.value || !catalog.value?.canEdit,
								onClick: _cache[1] || (_cache[1] = ($event) => create())
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "save",
								label: "Save current script to server",
								disabled: !editable.value || busy.value || uncertain.value,
								onClick: _cache[2] || (_cache[2] = ($event) => save())
							}, null, 8, ["disabled"]),
							active.value ? withDirectives((openBlock(), createElementBlock("input", {
								key: 0,
								"onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => active.value.folder = $event),
								readonly: !editable.value || busy.value,
								placeholder: unref(t)("Folder"),
								"aria-label": unref(t)("Script folder")
							}, null, 8, _hoisted_6)), [[vModelText, active.value.folder]]) : createCommentVNode("", true),
							_cache[31] || (_cache[31] = createBaseVNode("span", null, "/", -1)),
							active.value ? withDirectives((openBlock(), createElementBlock("input", {
								key: 1,
								"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => active.value.title = $event),
								readonly: !editable.value || busy.value,
								placeholder: unref(t)("Title"),
								"aria-label": unref(t)("Script title")
							}, null, 8, _hoisted_7)), [[vModelText, active.value.title]]) : createCommentVNode("", true),
							active.value ? (openBlock(), createBlock(_sfc_main$7, {
								key: 2,
								modelValue: active.value.language,
								"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => active.value.language = $event),
								label: "Script language",
								disabled: !editable.value || busy.value,
								options: [
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
									...!supported.value ? [{
										value: active.value.language,
										label: active.value.language
									}] : []
								]
							}, null, 8, [
								"modelValue",
								"disabled",
								"options"
							])) : createCommentVNode("", true),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "FAS_BOLT",
								label: "Handler and DCC script triggers are unavailable in the web editor.",
								disabled: ""
							}),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "refresh",
								label: "Refresh scripts from server",
								disabled: busy.value || !!running.value,
								onClick: load
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: treeHidden.value ? "previous" : "next",
								label: treeHidden.value ? "Show scripts and outline" : "Hide scripts and outline",
								highlighted: !treeHidden.value,
								onClick: _cache[6] || (_cache[6] = ($event) => treeHidden.value = !treeHidden.value)
							}, null, 8, [
								"icon",
								"label",
								"highlighted"
							])
						]),
						createVNode(_sfc_main$8, {
							kind: "script",
							tabs: tabs.value.map((tab) => ({
								id: tab.id,
								title: tab.title,
								dirty: dirty(tab)
							})),
							selected: selected.value,
							disabled: busy.value,
							onSelect: _cache[9] || (_cache[9] = ($event) => selected.value = $event),
							onAdd: _cache[10] || (_cache[10] = ($event) => create()),
							onClose: closeTab,
							onReorder: _cache[11] || (_cache[11] = (from, to) => tabs.value.splice(to, 0, tabs.value.splice(from, 1)[0]))
						}, {
							actions: withCtx(() => [createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "close",
								label: "Close all script tabs",
								disabled: busy.value || !!running.value,
								onClick: closeAll
							}, null, 8, ["disabled"]), createVNode(_sfc_main$3, {
								ref_key: "actions",
								ref: actions,
								overlay: "",
								label: "Saved script actions",
								"close-on-select": true
							}, {
								default: withCtx(() => [
									createVNode(_sfc_main$2, {
										icon: "refresh",
										label: "Reload saved source",
										disabled: !active.value?.code || busy.value,
										onClick: _cache[7] || (_cache[7] = ($event) => ask("reload", active.value))
									}, null, 8, ["disabled"]),
									createVNode(_sfc_main$2, {
										icon: "copy",
										label: "Copy Script Runner",
										disabled: !active.value?.code,
										onClick: runner
									}, null, 8, ["disabled"]),
									createVNode(_sfc_main$2, {
										destructive: "",
										icon: "delete",
										label: "Delete from server",
										disabled: !editable.value || !active.value?.code || busy.value || uncertain.value,
										onClick: _cache[8] || (_cache[8] = ($event) => ask("delete", active.value))
									}, null, 8, ["disabled"])
								]),
								_: 1
							}, 512)]),
							_: 1
						}, 8, [
							"tabs",
							"selected",
							"disabled"
						]),
						active.value ? (openBlock(), createElementBlock("section", {
							key: 0,
							class: normalizeClass(["script-editor-output", { wrapped: outputWrap.value }]),
							style: normalizeStyle({ height: outputHidden.value ? "28px" : outputHeight.value + "px" })
						}, [createBaseVNode("header", null, [
							createVNode(_sfc_main$1, { name: "MDI_CONSOLE" }),
							createBaseVNode("span", null, toDisplayString(unref(t)("Output")), 1),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "MDI_WRAP",
								label: "Wrap output",
								"aria-pressed": outputWrap.value,
								onClick: _cache[12] || (_cache[12] = ($event) => outputWrap.value = !outputWrap.value)
							}, null, 8, ["aria-pressed"]),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "delete",
								label: "Clear output",
								disabled: !active.value.output,
								onClick: _cache[13] || (_cache[13] = ($event) => active.value.output = "")
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: outputHidden.value ? "MDI_CHEVRON_UP" : "MDI_CHEVRON_DOWN",
								label: outputHidden.value ? "Expand output" : "Collapse output",
								onClick: _cache[14] || (_cache[14] = ($event) => outputHidden.value = !outputHidden.value)
							}, null, 8, ["icon", "label"])
						]), !outputHidden.value ? (openBlock(), createElementBlock("pre", _hoisted_8, toDisplayString(active.value.output), 1)) : createCommentVNode("", true)], 6)) : createCommentVNode("", true),
						active.value && !outputHidden.value ? (openBlock(), createBlock(_sfc_main$4, {
							key: 1,
							modelValue: outputHeight.value,
							"onUpdate:modelValue": _cache[15] || (_cache[15] = ($event) => outputHeight.value = $event),
							horizontal: "",
							label: "Output height",
							min: 80,
							max: 500
						}, null, 8, ["modelValue"])) : createCommentVNode("", true),
						active.value ? (openBlock(), createElementBlock("div", _hoisted_9, [createVNode(_sfc_main$5, {
							ref_key: "editor",
							ref: editor,
							modelValue: active.value.source,
							"onUpdate:modelValue": _cache[16] || (_cache[16] = ($event) => active.value.source = $event),
							"font-size": fontSize.value,
							"onUpdate:fontSize": _cache[17] || (_cache[17] = ($event) => fontSize.value = $event),
							analysis: analysis.value,
							"buffer-key": active.value.id,
							language: active.value.language === "server_js" ? "javascript" : active.value.language,
							"read-only": !editable.value,
							disabled: busy.value || !!running.value,
							onRun: run,
							onAnalyse: analyse,
							onOutline: showOutline,
							onHelp: _cache[18] || (_cache[18] = ($event) => unref(openHelp)("script_editor"))
						}, {
							actions: withCtx(() => [createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "FAS_CLOUD",
								label: "Saved revisions",
								disabled: !active.value?.code || busy.value,
								onClick: history
							}, null, 8, ["disabled"])]),
							_: 1
						}, 8, [
							"modelValue",
							"font-size",
							"analysis",
							"buffer-key",
							"language",
							"read-only",
							"disabled"
						])])) : (openBlock(), createElementBlock("p", _hoisted_10, toDisplayString(unref(t)("Open a script or create a new one.")), 1)),
						createBaseVNode("footer", null, [
							createVNode(_sfc_main$2, {
								label: "Run Script",
								highlighted: "",
								icon: "play-arrow",
								disabled: !editable.value || busy.value || !!running.value || !active.value?.source.trim(),
								onClick: _cache[19] || (_cache[19] = ($event) => run())
							}, null, 8, ["disabled"]),
							createBaseVNode("span", null, toDisplayString(running.value ? unref(t)("Running…") : unref(t)("Run in")), 1),
							createVNode(_sfc_main$7, {
								"model-value": active.value?.language === "javascript" ? "browser" : "server",
								label: "Execution target",
								options: [{
									value: active.value?.language === "javascript" ? "browser" : "server",
									label: active.value?.language === "javascript" ? "Browser" : "Server"
								}],
								disabled: ""
							}, null, 8, ["model-value", "options"])
						]),
						!catalog.value?.canEdit && catalog.value ? (openBlock(), createElementBlock("p", _hoisted_11, toDisplayString(unref(t)("Read-only: script changes and execution require administrator access.")), 1)) : !supported.value && active.value ? (openBlock(), createElementBlock("p", _hoisted_12, toDisplayString(unref(t)("This legacy language is read-only in the web editor")), 1)) : createCommentVNode("", true),
						active.value?.missing ? (openBlock(), createElementBlock("p", _hoisted_13, toDisplayString(unref(t)("This script was deleted on the server. Its local draft is preserved.")), 1)) : createCommentVNode("", true),
						error.value || analysisError.value ? (openBlock(), createElementBlock("p", _hoisted_14, toDisplayString(unref(t)(error.value || analysisError.value)), 1)) : createCommentVNode("", true)
					]),
					!treeHidden.value ? (openBlock(), createBlock(_sfc_main$4, {
						key: 0,
						modelValue: treeWidth.value,
						"onUpdate:modelValue": _cache[20] || (_cache[20] = ($event) => treeWidth.value = $event),
						reverse: "",
						label: "Scripts panel width",
						min: 140,
						max: 500
					}, null, 8, ["modelValue"])) : createCommentVNode("", true),
					!treeHidden.value ? (openBlock(), createElementBlock("aside", {
						key: 1,
						class: "script-editor-tree",
						style: normalizeStyle({ width: treeWidth.value + "px" })
					}, [
						createVNode(_sfc_main$6, {
							modelValue: side.value,
							"onUpdate:modelValue": _cache[21] || (_cache[21] = ($event) => side.value = $event),
							outlined: "",
							label: "Scripts panel",
							options: [{
								value: "scripts",
								label: "Scripts"
							}, {
								value: "outline",
								label: "Outline"
							}]
						}, null, 8, ["modelValue"]),
						createVNode(AppSearchField_default, {
							ref_key: "filter",
							ref: filter,
							modelValue: query.value,
							"onUpdate:modelValue": _cache[22] || (_cache[22] = ($event) => query.value = $event),
							label: "Search scripts and symbols",
							onKeydown: _cache[23] || (_cache[23] = withKeys(withModifiers(($event) => side.value === "outline" && symbols.value.length && goToSymbol(symbols.value[0]), ["prevent"]), ["enter"])),
							placeholder: unref(t)(side.value === "scripts" ? "Search scripts" : "Filter classes and methods")
						}, null, 8, ["modelValue", "placeholder"]),
						side.value === "scripts" ? (openBlock(), createBlock(_sfc_main$9, {
							key: 0,
							entries: tree.value,
							query: query.value,
							selected: active.value ? active.value.folder + "/" + active.value.title : "",
							onSelect: _cache[24] || (_cache[24] = ($event) => openScript($event.key)),
							onContextmenu: _cache[25] || (_cache[25] = withModifiers((event) => {
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
							return openBlock(), createBlock(_sfc_main$2, {
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
						}), 128)), !allSymbols.value.length ? (openBlock(), createElementBlock("p", _hoisted_16, toDisplayString(unref(t)("No classes or methods")), 1)) : createCommentVNode("", true)], 8, _hoisted_15))
					], 4)) : createCommentVNode("", true)
				])], 44, _hoisted_1)), [[_directive_window, {
					kind: "script_editor",
					type: "window"
				}]]),
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "confirmation",
					ref: confirmation,
					class: "record-dialog",
					"aria-label": confirmTitle.value,
					onCancel: _cache[29] || (_cache[29] = withModifiers(($event) => !busy.value && confirmation.value.close(), ["prevent"]))
				}, [
					createBaseVNode("h2", null, toDisplayString(confirmTitle.value), 1),
					createBaseVNode("p", null, toDisplayString(confirmAction.value === "delete" ? unref(t)("Deleting the saved script does not remove its shelf buttons; they become unavailable.") : unref(t)("Save, discard the selected drafts, or return to editing.")), 1),
					error.value ? (openBlock(), createElementBlock("p", _hoisted_18, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
					createBaseVNode("div", _hoisted_19, [
						confirmAction.value === "tabs" ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							label: "Save",
							icon: "save",
							disabled: busy.value || uncertain.value || !catalog.value?.canEdit,
							onClick: _cache[26] || (_cache[26] = ($event) => accept(true))
						}, null, 8, ["disabled"])) : createCommentVNode("", true),
						createVNode(_sfc_main$2, {
							label: confirmAction.value === "delete" ? "Delete" : "Discard",
							destructive: "",
							disabled: busy.value || !!running.value,
							onClick: _cache[27] || (_cache[27] = ($event) => accept())
						}, null, 8, ["label", "disabled"]),
						createVNode(_sfc_main$2, {
							label: "Cancel",
							disabled: busy.value,
							onClick: _cache[28] || (_cache[28] = ($event) => confirmation.value.close())
						}, null, 8, ["disabled"])
					])
				], 40, _hoisted_17)), [[_directive_window, { type: "popup" }]]),
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "historyDialog",
					ref: historyDialog,
					class: "record-dialog script-editor-history",
					"aria-label": unref(t)("Saved revisions")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Saved revisions")), 1), createVNode(_sfc_main$2, {
						label: "Close",
						icon: "close",
						onClick: _cache[30] || (_cache[30] = ($event) => historyDialog.value.close())
					})]),
					createBaseVNode("p", null, toDisplayString(unref(t)("Restoring a revision changes the local draft. Save publishes it as a new revision.")), 1),
					(openBlock(true), createElementBlock(Fragment, null, renderList(historyRows.value, (row) => {
						return openBlock(), createBlock(_sfc_main$2, {
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
				], 8, _hoisted_20)), [[_directive_window, { type: "popup" }]])
			]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=ScriptEditor.js.map
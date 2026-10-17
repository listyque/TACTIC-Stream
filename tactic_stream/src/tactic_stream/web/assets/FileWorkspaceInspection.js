import { D as nextTick, F as renderSlot, G as withCtx, H as watch, I as resolveComponent, J as markRaw, K as withDirectives, N as openBlock, P as renderList, X as ref, _ as createCommentVNode, b as createTextVNode, c as vShow, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, l as withKeys, m as computed, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, o as _sfc_main$7, tt as _plugin_vue_export_helper_default, u as _sfc_main$8, x as redact, y as logEvent } from "./index.js";
import { f as _sfc_main$9, n as copyText } from "./clipboard.js";
import { t as _sfc_main$10 } from "./AppTextField.js";
import { t as _sfc_main$11 } from "./AppMenu.js";
import { i as prettySize } from "./files.js";
import { t as _sfc_main$12 } from "./AppTextArea.js";
import { t as _sfc_main$13 } from "./AppMenuItem.js";
import { t as _sfc_main$14 } from "./AppSplitter.js";
import { t as _sfc_main$15 } from "./ItemSurface.js";
import { T as _sfc_main$16 } from "./App.js";
//#region src/features/fileWorkspace/FileWorkspaceTree.vue
var _hoisted_1$5 = ["aria-label"];
var _hoisted_2$5 = [
	"aria-level",
	"aria-expanded",
	"aria-selected",
	"onKeydown",
	"data-node",
	"title",
	"draggable",
	"onContextmenu",
	"onDragstart",
	"onDragover",
	"onDrop"
];
var _hoisted_3$5 = {
	key: 1,
	class: "file-tree-indent"
};
var _hoisted_4$5 = { class: "file-tree-caption" };
var _hoisted_5$4 = ["title"];
var _hoisted_6$4 = {
	key: 0,
	class: "file-workspace-empty muted"
};
var FileWorkspaceTree_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FileWorkspaceTree",
	props: {
		nodes: Array,
		busy: Boolean,
		selected: String,
		label: String,
		selectedIds: Array,
		dropTarget: String,
		canDrop: Boolean,
		dropReason: Function,
		dropCaption: Function,
		canDrag: {
			type: Boolean,
			default: true
		}
	},
	emits: [
		"expand",
		"select",
		"menu",
		"background",
		"drag",
		"drop",
		"dragover",
		"dragend"
	],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		const branch = (node) => [
			"depot",
			"stream",
			"workspace",
			"directory",
			"change"
		].includes(node.kind);
		const title = (node) => node.kind === "more" ? t("Load more") : node.kind === "change" ? t("Changelist #{number}", { number: node.number }) + " · " + (node.description || t("No description")) : node.name || node.path;
		const icon = (node) => ({
			workspace: "desktop",
			depot: "database",
			stream: "workflow",
			directory: node.expanded ? "folder-open" : "folder",
			change: "archive",
			more: "add",
			file: "file"
		})[node.kind];
		const state = (node) => ({
			pending: "Pending",
			submitted: "Submitted",
			shelved: "Shelved",
			reverted: "Reverted"
		})[node.state];
		const counts = (node) => node.file_actions ? (node.file_actions.checkout || 0) + " " + t("waiting") + " / " + Object.entries(node.file_actions).filter(([action]) => action !== "checkout").reduce((sum, [, count]) => sum + count, 0) + " " + t("staged") : t("Counts not indexed");
		const invalid = ref("");
		let hoverTimer, frame, hoverCode = "";
		function endDrag() {
			clearTimeout(hoverTimer);
			cancelAnimationFrame(frame);
			hoverCode = "";
			invalid.value = "";
		}
		function dragOver(event, node) {
			emit("dragover", event, node);
			if (!event.defaultPrevented) {
				invalid.value = node.id;
				return;
			}
			invalid.value = "";
			if (hoverCode !== node.id) {
				clearTimeout(hoverTimer);
				hoverCode = node.id;
				if (branch(node) && !node.expanded) hoverTimer = setTimeout(() => emit("expand", node), 400);
			}
			const tree = event.currentTarget.closest(".file-workspace-branches"), bounds = tree.getBoundingClientRect(), direction = event.clientY < bounds.top + 28 ? -1 : event.clientY > bounds.bottom - 28 ? 1 : 0;
			cancelAnimationFrame(frame);
			const scroll = () => {
				if (direction) {
					tree.scrollTop += direction * 8;
					frame = requestAnimationFrame(scroll);
				}
			};
			scroll();
		}
		onBeforeUnmount(endDrag);
		function key(event, node) {
			if (event.key === "ArrowRight" && branch(node) && !node.expanded) {
				event.preventDefault();
				emit("expand", node);
			} else if (event.key === "ArrowLeft" && branch(node) && node.expanded) {
				event.preventDefault();
				emit("expand", node);
			} else if (["ArrowUp", "ArrowDown"].includes(event.key)) {
				const rows = [...event.currentTarget.parentElement.querySelectorAll(".file-tree-select")];
				rows[rows.indexOf(event.currentTarget.querySelector(".file-tree-select")) + (event.key === "ArrowUp" ? -1 : 1)]?.focus();
				event.preventDefault();
			}
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "file-workspace-branches",
				role: "tree",
				"aria-label": unref(t)(__props.label),
				onContextmenu: _cache[1] || (_cache[1] = withModifiers(($event) => emit("background", $event), ["prevent"]))
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.nodes, (node) => {
				return openBlock(), createElementBlock("div", {
					key: node.id,
					class: normalizeClass(["file-tree-row", {
						selected: __props.selectedIds?.includes(node.id) || __props.selected === node.id,
						change: node.kind === "change",
						drop: __props.dropTarget === node.code,
						invalid: invalid.value === node.id
					}]),
					role: "treeitem",
					"aria-level": node.depth + 1,
					"aria-expanded": branch(node) ? !!node.expanded : void 0,
					"aria-selected": __props.selectedIds?.includes(node.id) || __props.selected === node.id,
					onKeydown: ($event) => key($event, node),
					style: normalizeStyle({ "--depth": node.depth }),
					"data-node": node.id,
					title: invalid.value === node.id && __props.dropReason ? __props.dropReason(node) : __props.dropTarget === node.code && __props.dropCaption ? __props.dropCaption(node) : void 0,
					draggable: __props.canDrag && !__props.busy && [
						"file",
						"change",
						"directory",
						"stream",
						"workspace"
					].includes(node.kind),
					onContextmenu: withModifiers(($event) => emit("menu", $event, node), ["prevent", "stop"]),
					onDragstart: withModifiers(($event) => emit("drag", $event, node), ["stop"]),
					onDragover: ($event) => __props.canDrop && dragOver($event, node),
					onDragleave: endDrag,
					onDragend: _cache[0] || (_cache[0] = ($event) => {
						endDrag();
						emit("dragend");
					}),
					onDrop: withModifiers(($event) => {
						endDrag();
						__props.canDrop && emit("drop", $event, node);
					}, ["stop"])
				}, [branch(node) ? (openBlock(), createBlock(_sfc_main$7, {
					key: 0,
					"icon-only": "",
					icon: node.expanded ? "chevron-down" : "next",
					"aria-label": unref(t)(node.expanded ? "Collapse {name}" : "Expand {name}", { name: title(node) }),
					disabled: __props.busy,
					onClick: ($event) => emit("expand", node)
				}, null, 8, [
					"icon",
					"aria-label",
					"disabled",
					"onClick"
				])) : (openBlock(), createElementBlock("span", _hoisted_3$5)), node.kind === "file" && _ctx.$slots.file ? renderSlot(_ctx.$slots, "file", { node }, void 0, true, 2) : (openBlock(), createBlock(_sfc_main$7, {
					key: 3,
					class: "file-tree-select",
					"aria-label": title(node),
					title: title(node),
					disabled: __props.busy,
					onClick: ($event) => emit("select", node, $event)
				}, {
					default: withCtx(() => [
						createVNode(_sfc_main$8, {
							name: icon(node),
							class: normalizeClass(node.kind === "change" ? "change-status-" + node.state : "")
						}, null, 8, ["name", "class"]),
						createBaseVNode("span", _hoisted_4$5, [createBaseVNode("span", null, toDisplayString(title(node)), 1), node.kind === "change" ? (openBlock(), createElementBlock("small", {
							key: 0,
							title: node.owner + " · " + node.workspace + " · " + node.stream
						}, toDisplayString(unref(t)(state(node))) + " · " + toDisplayString(node.owner) + " · " + toDisplayString(node.workspace) + " · " + toDisplayString(node.stream) + " · " + toDisplayString(node.opened_files || 0) + " " + toDisplayString(unref(t)("files")) + " · " + toDisplayString(counts(node)) + " · " + toDisplayString(node.conflict_files || 0) + " " + toDisplayString(unref(t)("conflicts")) + " · " + toDisplayString(((node.opened_bytes || 0) / 1048576).toFixed(1)) + " MB", 9, _hoisted_5$4)) : createCommentVNode("", true)]),
						node.kind === "change" ? (openBlock(), createBlock(_sfc_main$8, {
							key: 0,
							name: node.state === "submitted" ? "check" : node.state === "shelved" ? "archive" : node.state === "reverted" ? "undo" : "clock"
						}, null, 8, ["name"])) : createCommentVNode("", true)
					]),
					_: 2
				}, 1032, [
					"aria-label",
					"title",
					"disabled",
					"onClick"
				]))], 46, _hoisted_2$5);
			}), 128)), !__props.nodes?.length ? (openBlock(), createElementBlock("p", _hoisted_6$4, toDisplayString(unref(t)("Nothing to display")), 1)) : createCommentVNode("", true)], 40, _hoisted_1$5);
		};
	}
}, [["__scopeId", "data-v-b706e399"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceInspector.vue
var _sfc_main$4 = {
	components: {
		AppTabButton: {
			__name: "AppTabButton",
			props: { checked: Boolean },
			setup(__props) {
				return (_ctx, _cache) => {
					return openBlock(), createBlock(_sfc_main$7, {
						class: "app-tab-button",
						"aria-pressed": __props.checked
					}, null, 8, ["aria-pressed"]);
				};
			}
		},
		AppTextArea: _sfc_main$12,
		AppIcon: _sfc_main$8
	},
	props: {
		call: Function,
		row: Object,
		workspace: String,
		stream: String,
		scope: String,
		shelved: Boolean
	},
	data() {
		return {
			tab: "details",
			info: null,
			busy: false,
			error: "",
			generation: 0,
			aborter: null,
			timer: null
		};
	},
	computed: {
		key() {
			return JSON.stringify([
				this.row?.source_path || this.row?.path,
				this.row?.stream || this.stream,
				this.scope,
				this.workspace,
				this.tab
			]);
		},
		fields() {
			const info = this.info, file = info?.file;
			if (!info) return [];
			return [
				["Workspace location", info.local_path || "—"],
				["Depot location", "//" + info.stream + "/" + info.path],
				["Revision", "#" + (file?.number || "—") + " · Have #" + (info.have?.number || "—") + " · Head #" + (info.head?.number || "—")],
				["Submitted at", info.submitted_at ? (/* @__PURE__ */ new Date(info.submitted_at / 1e3)).toLocaleString() : "—"],
				["File size", prettySize(file?.size || 0)],
				["Author", info.author || "—"],
				["Changelist", info.change_number ? "#" + info.change_number : "—"],
				["Description", info.description || "—"],
				["Integration source", info.provenance ? info.provenance.stream + " · " + info.provenance.change + " · " + info.provenance.version : "—"],
				["SHA-256", file?.sha256 || "—"]
			];
		}
	},
	watch: { key: {
		immediate: true,
		handler() {
			clearTimeout(this.timer);
			this.aborter?.abort();
			this.generation++;
			this.info = null;
			this.error = "";
			this.busy = !!this.row?.path;
			if (this.busy) this.timer = setTimeout(() => this.load(), 120);
		}
	} },
	beforeUnmount() {
		clearTimeout(this.timer);
		this.generation++;
		this.aborter?.abort();
	},
	methods: {
		t,
		prettySize,
		async load() {
			const generation = this.generation;
			this.aborter = new AbortController();
			const signal = this.aborter.signal;
			const options = {
				stream: this.row.stream || this.stream,
				path: this.row.source_path || this.row.path
			};
			if (this.scope) options[this.shelved ? "shelf" : "change"] = this.scope;
			try {
				const info = await this.call("file_info", {
					...options,
					...this.workspace ? { workspace: this.workspace } : {},
					preview: this.tab === "preview"
				}, signal);
				if (generation === this.generation) this.info = info;
			} catch (error) {
				if (generation === this.generation && error.name !== "AbortError") this.error = error.message;
			} finally {
				if (generation === this.generation) this.busy = false;
			}
		}
	}
};
var _hoisted_1$4 = ["aria-label"];
var _hoisted_2$4 = ["aria-label"];
var _hoisted_3$4 = {
	key: 0,
	role: "status"
};
var _hoisted_4$4 = { class: "file-workspace-inspector-body" };
var _hoisted_5$3 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_6$3 = {
	key: 1,
	class: "muted"
};
var _hoisted_7$3 = { key: 2 };
var _hoisted_8$3 = {
	key: 0,
	class: "muted"
};
var _hoisted_9$3 = {
	key: 0,
	class: "muted"
};
var _hoisted_10$2 = {
	key: 0,
	class: "muted"
};
var _hoisted_11$2 = {
	key: 1,
	class: "muted"
};
var _hoisted_12$2 = ["src", "alt"];
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppTabButton = resolveComponent("AppTabButton");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppTextArea = resolveComponent("AppTextArea");
	return openBlock(), createElementBlock("section", {
		class: "file-workspace-inspector",
		"aria-label": $options.t("File details")
	}, [createBaseVNode("header", {
		role: "tablist",
		"aria-label": $options.t("File details")
	}, [(openBlock(), createElementBlock(Fragment, null, renderList([
		{
			id: "details",
			title: "Details"
		},
		{
			id: "checkout",
			title: "Checked Out By"
		},
		{
			id: "preview",
			title: "Preview"
		}
	], (item) => {
		return createVNode(_component_AppTabButton, {
			key: item.id,
			label: item.title,
			checked: $data.tab === item.id,
			onClick: ($event) => $data.tab = item.id
		}, null, 8, [
			"label",
			"checked",
			"onClick"
		]);
	}), 64)), $data.busy ? (openBlock(), createElementBlock("span", _hoisted_3$4, toDisplayString($options.t("Loading")), 1)) : createCommentVNode("", true)], 8, _hoisted_2$4), createBaseVNode("div", _hoisted_4$4, [
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_5$3, toDisplayString($options.t($data.error)), 1)) : !$data.info && !$data.busy ? (openBlock(), createElementBlock("p", _hoisted_6$3, toDisplayString($options.t("Select a file to inspect")), 1)) : createCommentVNode("", true),
		$data.info && $data.tab === "details" ? (openBlock(), createElementBlock("dl", _hoisted_7$3, [(openBlock(true), createElementBlock(Fragment, null, renderList($options.fields, ([title, value]) => {
			return openBlock(), createElementBlock(Fragment, { key: title }, [createBaseVNode("dt", null, toDisplayString($options.t(title)), 1), createBaseVNode("dd", null, toDisplayString(value), 1)], 64);
		}), 128))])) : createCommentVNode("", true),
		$data.info && $data.tab === "checkout" ? (openBlock(), createElementBlock(Fragment, { key: 3 }, [!$data.info.holders.length ? (openBlock(), createElementBlock("p", _hoisted_8$3, toDisplayString($options.t("No active checkout")), 1)) : createCommentVNode("", true), (openBlock(true), createElementBlock(Fragment, null, renderList($data.info.holders, (holder) => {
			return openBlock(), createElementBlock("p", { key: holder.change }, [createVNode(_component_AppIcon, { name: holder.mode === "exclusive" ? "lock" : "edit" }, null, 8, ["name"]), createTextVNode(" " + toDisplayString(holder.owner) + " · " + toDisplayString(holder.workspace) + " · #" + toDisplayString(holder.number || holder.change) + " · " + toDisplayString($options.t(holder.mode === "exclusive" ? "Exclusive checkout" : "Ordinary checkout")), 1)]);
		}), 128))], 64)) : createCommentVNode("", true),
		$data.info && $data.tab === "preview" ? (openBlock(), createElementBlock(Fragment, { key: 4 }, [!$data.info.preview ? (openBlock(), createElementBlock("p", _hoisted_9$3, toDisplayString($options.t("No content available for this file")), 1)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
			$data.info.preview.kind === "binary" ? (openBlock(), createElementBlock("p", _hoisted_10$2, toDisplayString($options.t("Binary file")) + " · " + toDisplayString($options.prettySize($data.info.preview.size)) + " · " + toDisplayString($data.info.preview.sha256), 1)) : createCommentVNode("", true),
			$data.info.preview.truncated ? (openBlock(), createElementBlock("p", _hoisted_11$2, toDisplayString($options.t("Preview shows the first 256 KiB")), 1)) : createCommentVNode("", true),
			$data.info.preview.kind === "image" ? (openBlock(), createElementBlock("img", {
				key: 2,
				src: $data.info.preview.image,
				alt: $data.info.path
			}, null, 8, _hoisted_12$2)) : (openBlock(), createBlock(_component_AppTextArea, {
				key: 3,
				"model-value": $data.info.preview.text,
				readonly: "",
				label: "File preview"
			}, null, 8, ["model-value"]))
		], 64))], 64)) : createCommentVNode("", true)
	])], 8, _hoisted_1$4);
}
var FileWorkspaceInspector_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$4, [["render", _sfc_render$1], ["__scopeId", "data-v-f7a07b28"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceLog.vue
var _hoisted_1$3 = ["aria-label"];
var _hoisted_2$3 = ["aria-label"];
var _hoisted_3$3 = ["data-level"];
var _hoisted_4$3 = {
	key: 0,
	class: "file-operation-log-path"
};
var FileWorkspaceLog_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FileWorkspaceLog",
	props: { entries: Array },
	emits: [
		"clear",
		"copy",
		"debug"
	],
	setup(__props) {
		const props = __props;
		const expanded = ref(true), scroll = ref(null);
		watch(() => props.entries.at(-1)?.id, async () => {
			await nextTick();
			if (scroll.value) scroll.value.scrollTop = scroll.value.scrollHeight;
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "file-operation-log",
				"aria-label": unref(t)("Operation log")
			}, [createBaseVNode("header", null, [
				createVNode(_sfc_main$7, {
					"icon-only": "",
					label: expanded.value ? "Collapse log" : "Expand log",
					icon: expanded.value ? "chevron-down" : "next",
					"aria-expanded": expanded.value,
					onClick: _cache[0] || (_cache[0] = ($event) => expanded.value = !expanded.value)
				}, null, 8, [
					"label",
					"icon",
					"aria-expanded"
				]),
				createVNode(_sfc_main$8, { name: "MDI_CONSOLE" }),
				createBaseVNode("strong", null, toDisplayString(unref(t)("Log")), 1),
				createVNode(_sfc_main$7, {
					"icon-only": "",
					label: "Copy log",
					icon: "copy",
					onClick: _cache[1] || (_cache[1] = ($event) => _ctx.$emit("copy"))
				}),
				createVNode(_sfc_main$7, {
					"icon-only": "",
					label: "Clear log",
					icon: "delete",
					onClick: _cache[2] || (_cache[2] = ($event) => _ctx.$emit("clear"))
				}),
				createVNode(_sfc_main$7, {
					"icon-only": "",
					label: "Debug Log",
					icon: "MDI_BUG",
					onClick: _cache[3] || (_cache[3] = ($event) => _ctx.$emit("debug"))
				})
			]), withDirectives(createBaseVNode("div", {
				ref_key: "scroll",
				ref: scroll,
				class: "file-operation-log-scroll",
				role: "log",
				"aria-live": "polite",
				"aria-label": unref(t)("Operation log")
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.entries, (entry) => {
				return openBlock(), createElementBlock("div", {
					key: entry.id,
					class: "file-operation-log-entry",
					"data-level": entry.level
				}, [createVNode(_sfc_main$8, { name: entry.level === "ERROR" ? "error" : entry.level === "WARNING" ? "warning" : "info" }, null, 8, ["name"]), createBaseVNode("span", null, [createTextVNode(toDisplayString(entry.time) + " · " + toDisplayString(entry.operation) + " · " + toDisplayString(entry.message), 1), entry.path ? (openBlock(), createElementBlock("span", _hoisted_4$3, toDisplayString(entry.path), 1)) : createCommentVNode("", true)])], 8, _hoisted_3$3);
			}), 128))], 8, _hoisted_2$3), [[vShow, expanded.value]])], 8, _hoisted_1$3);
		};
	}
}, [["__scopeId", "data-v-27f26918"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceDepots.vue
var _hoisted_1$2 = ["aria-label"];
var _hoisted_2$2 = { class: "depot-actions" };
var _hoisted_3$2 = { class: "depot-content" };
var _hoisted_4$2 = { class: "depot-row-text" };
var _hoisted_5$2 = { key: 0 };
var _hoisted_6$2 = { class: "depot-detail" };
var _hoisted_7$2 = { class: "depot-actions" };
var _hoisted_8$2 = { key: 0 };
var _hoisted_9$2 = {
	key: 1,
	class: "depot-actions"
};
var FileWorkspaceDepots_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FileWorkspaceDepots",
	props: {
		rows: Array,
		selected: Object,
		draft: Object,
		repositories: Array,
		busy: Boolean,
		administrator: Boolean,
		after: String
	},
	emits: [
		"select",
		"edit",
		"change",
		"save",
		"reset",
		"cancel",
		"refresh",
		"more"
	],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		const host = ref(null), narrow = ref(false), desktopSplit = ref(55), mobileSplit = ref(40);
		const split = computed({
			get: () => narrow.value ? mobileSplit.value : desktopSplit.value,
			set: (value) => {
				if (narrow.value) mobileSplit.value = value;
				else desktopSplit.value = value;
			}
		});
		const observer = new ResizeObserver((entries) => {
			narrow.value = (entries[0].borderBoxSize?.[0]?.inlineSize || entries[0].contentRect.width) < 600;
		});
		onMounted(() => observer.observe(host.value));
		onBeforeUnmount(() => observer.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: normalizeClass(["depots-catalog", { narrow: narrow.value }]),
				"aria-label": unref(t)("Depots")
			}, [createBaseVNode("header", _hoisted_2$2, [
				createBaseVNode("h3", null, toDisplayString(unref(t)("Depots")), 1),
				createVNode(_sfc_main$7, {
					label: "Refresh",
					icon: "refresh",
					disabled: __props.busy,
					onClick: _cache[0] || (_cache[0] = ($event) => emit("refresh"))
				}, null, 8, ["disabled"]),
				__props.after ? (openBlock(), createBlock(_sfc_main$7, {
					key: 0,
					label: "Next page",
					icon: "next",
					disabled: __props.busy,
					onClick: _cache[1] || (_cache[1] = ($event) => emit("more"))
				}, null, 8, ["disabled"])) : createCommentVNode("", true)
			]), createBaseVNode("div", _hoisted_3$2, [
				createBaseVNode("aside", { style: normalizeStyle({ flexBasis: `max(0px,calc(${split.value}% - 10px))` }) }, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.rows, (row) => {
					return openBlock(), createBlock(_sfc_main$15, {
						key: row.code,
						selected: __props.selected?.code === row.code,
						"normal-color": "transparent",
						"selected-color": "var(--selected)",
						"rail-visible": __props.selected?.code === row.code,
						"separator-visible": false
					}, {
						default: withCtx(() => [createVNode(_sfc_main$7, {
							class: "depot-row",
							label: row.code,
							"translate-label": false,
							icon: "database",
							"aria-pressed": __props.selected?.code === row.code,
							onClick: ($event) => emit("select", row)
						}, {
							default: withCtx(() => [createBaseVNode("span", _hoisted_4$2, [createBaseVNode("strong", null, toDisplayString(row.code), 1), createBaseVNode("small", null, toDisplayString(row.title) + " · " + toDisplayString(row.storage?.repository || unref(t)("Project storage")), 1)])]),
							_: 2
						}, 1032, [
							"label",
							"aria-pressed",
							"onClick"
						])]),
						_: 2
					}, 1032, ["selected", "rail-visible"]);
				}), 128)), !__props.rows.length ? (openBlock(), createElementBlock("p", _hoisted_5$2, toDisplayString(unref(t)("No permitted records on this page")), 1)) : createCommentVNode("", true)], 4),
				createVNode(_sfc_main$14, {
					modelValue: split.value,
					"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => split.value = $event),
					label: "Depots",
					horizontal: narrow.value,
					proportional: true,
					min: 0,
					max: 100
				}, null, 8, ["modelValue", "horizontal"]),
				createBaseVNode("div", _hoisted_6$2, [__props.draft ? (openBlock(), createElementBlock("form", {
					key: 0,
					onSubmit: _cache[8] || (_cache[8] = withModifiers(($event) => emit("save"), ["prevent"]))
				}, [
					createBaseVNode("h3", null, toDisplayString(unref(t)(__props.draft.creating ? "New depot" : "Edit depot")), 1),
					createBaseVNode("label", null, [createBaseVNode("span", null, toDisplayString(unref(t)("Depot code")), 1), createVNode(_sfc_main$10, {
						"model-value": __props.draft.code,
						label: "Depot code",
						readonly: !__props.draft.creating,
						disabled: __props.busy,
						"onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => emit("change", {
							...__props.draft,
							code: $event
						}))
					}, null, 8, [
						"model-value",
						"readonly",
						"disabled"
					])]),
					createBaseVNode("label", null, [createBaseVNode("span", null, toDisplayString(unref(t)("Name")), 1), createVNode(_sfc_main$10, {
						"model-value": __props.draft.title,
						label: "Name",
						disabled: __props.busy,
						"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => emit("change", {
							...__props.draft,
							title: $event
						}))
					}, null, 8, ["model-value", "disabled"])]),
					createBaseVNode("label", null, [createBaseVNode("span", null, toDisplayString(unref(t)("Repository")), 1), createVNode(_sfc_main$9, {
						"model-value": __props.draft.repository,
						label: "Repository",
						options: [{
							value: "",
							label: unref(t)("Project storage")
						}, ...__props.repositories.map((value) => ({
							value,
							label: value
						}))],
						"translate-labels": false,
						disabled: __props.busy,
						"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => emit("change", {
							...__props.draft,
							repository: $event
						}))
					}, null, 8, [
						"model-value",
						"options",
						"disabled"
					])]),
					createBaseVNode("p", null, toDisplayString(unref(t)("Repository changes apply to new uploads. Existing file contents stay in their original storage.")), 1),
					createBaseVNode("p", null, toDisplayString(unref(t)("Depot paths are case-sensitive. Access is configured in Administration → Rules using file_depot.")), 1),
					createBaseVNode("div", _hoisted_7$2, [
						createVNode(_sfc_main$7, {
							label: "Reset",
							icon: "undo",
							disabled: __props.busy,
							onClick: _cache[6] || (_cache[6] = ($event) => emit("reset"))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$7, {
							label: "Cancel",
							icon: "close",
							disabled: __props.busy,
							onClick: _cache[7] || (_cache[7] = ($event) => emit("cancel"))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$7, {
							label: __props.draft.creating ? "Create" : "Save",
							icon: "save",
							type: "submit",
							disabled: __props.busy || !__props.draft.code.trim()
						}, null, 8, ["label", "disabled"])
					])
				], 32)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
					createBaseVNode("h3", null, toDisplayString(__props.selected?.code || unref(t)("Select a depot")), 1),
					__props.selected?.code ? (openBlock(), createElementBlock("p", _hoisted_8$2, [
						createTextVNode(toDisplayString(__props.selected.title), 1),
						_cache[11] || (_cache[11] = createBaseVNode("br", null, null, -1)),
						createTextVNode(toDisplayString(unref(t)("Repository")) + ": " + toDisplayString(__props.selected.storage?.repository || unref(t)("Project storage")), 1),
						_cache[12] || (_cache[12] = createBaseVNode("br", null, null, -1)),
						createTextVNode(toDisplayString(unref(t)("Revision")) + ": " + toDisplayString(__props.selected.revision), 1),
						_cache[13] || (_cache[13] = createBaseVNode("br", null, null, -1)),
						createTextVNode(toDisplayString(unref(t)("Case-sensitive depot paths")), 1)
					])) : createCommentVNode("", true),
					__props.administrator ? (openBlock(), createElementBlock("div", _hoisted_9$2, [createVNode(_sfc_main$7, {
						label: "New depot",
						icon: "add",
						disabled: __props.busy,
						onClick: _cache[9] || (_cache[9] = ($event) => emit("edit", null))
					}, null, 8, ["disabled"]), createVNode(_sfc_main$7, {
						label: "Edit depot",
						icon: "edit",
						disabled: __props.busy || !__props.selected?.code,
						onClick: _cache[10] || (_cache[10] = ($event) => emit("edit", __props.selected))
					}, null, 8, ["disabled"])])) : createCommentVNode("", true)
				], 64))])
			])], 10, _hoisted_1$2);
		};
	}
}, [["__scopeId", "data-v-236f8c05"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceStorage.vue
var _hoisted_1$1 = ["aria-label"];
var _hoisted_2$1 = { class: "storage-fields" };
var _hoisted_3$1 = { class: "storage-actions" };
var _hoisted_4$1 = { key: 0 };
var _hoisted_5$1 = { key: 0 };
var _hoisted_6$1 = { key: 0 };
var _hoisted_7$1 = { class: "storage-actions" };
var _hoisted_8$1 = { key: 2 };
var _hoisted_9$1 = { class: "storage-actions" };
var _hoisted_10$1 = {
	key: 3,
	class: "gc-status",
	role: "status"
};
var _hoisted_11$1 = {
	key: 0,
	role: "alert"
};
var _hoisted_12$1 = { key: 1 };
var FileWorkspaceStorage_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FileWorkspaceStorage",
	props: {
		status: Object,
		draft: Object,
		busy: Boolean,
		indexing: Boolean,
		filesService: Boolean
	},
	emits: [
		"change",
		"save",
		"reset",
		"action",
		"stop"
	],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		const fields = [
			[
				"bytes_limit",
				"Byte quota",
				"Zero means unlimited."
			],
			[
				"files_limit",
				"File quota",
				"Zero means unlimited."
			],
			[
				"max_parallel",
				"Parallel transfers",
				"From 1 to 16."
			],
			[
				"upload_retention_seconds",
				"Unfinished uploads (seconds)",
				"Zero disables expiration."
			],
			[
				"reverted_retention_seconds",
				"Reverted changelists (seconds)",
				"Zero disables expiration."
			],
			[
				"task_retention_seconds",
				"Completed tasks (seconds)",
				"Zero disables expiration."
			],
			[
				"shelf_retention_seconds",
				"Shelved changelists (seconds)",
				"Zero disables expiration."
			],
			[
				"gc_grace_seconds",
				"Quarantine before deletion (seconds)",
				"Unreferenced contents stay in quarantine before physical deletion."
			],
			[
				"gc_interval_seconds",
				"Automatic GC interval (seconds)",
				"Zero disables automatic cleanup."
			]
		];
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "storage-administration",
				"aria-label": unref(t)("Storage administration")
			}, [createBaseVNode("div", _hoisted_2$1, [
				createBaseVNode("h3", null, toDisplayString(unref(t)("Storage administration")), 1),
				createBaseVNode("p", null, toDisplayString(unref(prettySize)(__props.status?.allocated_bytes || 0)) + " · " + toDisplayString(__props.status?.allocated_files || 0) + " " + toDisplayString(unref(t)("files")) + " · " + toDisplayString(unref(t)(__props.status?.indexed ? "Storage index complete" : "Storage index incomplete")), 1),
				createBaseVNode("div", _hoisted_3$1, [
					createVNode(_sfc_main$7, {
						label: "Refresh",
						icon: "refresh",
						disabled: __props.busy,
						onClick: _cache[0] || (_cache[0] = ($event) => emit("action", "storage_status"))
					}, null, 8, ["disabled"]),
					!__props.status?.initialized ? (openBlock(), createBlock(_sfc_main$7, {
						key: 0,
						label: "Initialize storage",
						disabled: __props.busy,
						onClick: _cache[1] || (_cache[1] = ($event) => emit("action", "storage_upgrade"))
					}, null, 8, ["disabled"])) : !__props.status.indexed ? (openBlock(), createBlock(_sfc_main$7, {
						key: 1,
						label: "Continue storage index",
						disabled: __props.busy,
						onClick: _cache[2] || (_cache[2] = ($event) => emit("action", "storage_index"))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					__props.indexing ? (openBlock(), createBlock(_sfc_main$7, {
						key: 2,
						label: "Stop waiting",
						icon: "close",
						onClick: _cache[3] || (_cache[3] = ($event) => emit("stop"))
					})) : createCommentVNode("", true)
				]),
				!__props.status?.indexed ? (openBlock(), createElementBlock("p", _hoisted_4$1, [createTextVNode(toDisplayString(unref(t)("Finish indexing before editing the policy or running GC. Indexing can be stopped and continued.")) + " ", 1), __props.status?.index_table !== void 0 ? (openBlock(), createElementBlock("span", _hoisted_5$1, toDisplayString(unref(t)("Table")) + ": " + toDisplayString(__props.status.index_table) + " · " + toDisplayString(__props.status.index_after), 1)) : createCommentVNode("", true)])) : createCommentVNode("", true),
				__props.draft ? (openBlock(), createElementBlock("form", {
					key: 1,
					onSubmit: _cache[5] || (_cache[5] = withModifiers(($event) => emit("save"), ["prevent"]))
				}, [(openBlock(), createElementBlock(Fragment, null, renderList(fields, ([key, label, hint], index) => {
					return openBlock(), createElementBlock(Fragment, { key }, [index === 0 || index === 3 ? (openBlock(), createElementBlock("h3", _hoisted_6$1, toDisplayString(unref(t)(index === 0 ? "Quotas" : "Retention and cleanup")), 1)) : createCommentVNode("", true), createBaseVNode("label", null, [
						createBaseVNode("span", null, toDisplayString(unref(t)(label)), 1),
						createVNode(_sfc_main$10, {
							"model-value": __props.draft.policy[key],
							label,
							inputmode: "numeric",
							disabled: __props.busy || !__props.status?.indexed,
							"onUpdate:modelValue": ($event) => emit("change", {
								...__props.draft,
								policy: {
									...__props.draft.policy,
									[key]: $event
								}
							})
						}, null, 8, [
							"model-value",
							"label",
							"disabled",
							"onUpdate:modelValue"
						]),
						createBaseVNode("small", null, toDisplayString(unref(t)(hint)), 1)
					])], 64);
				}), 64)), createBaseVNode("div", _hoisted_7$1, [createVNode(_sfc_main$7, {
					label: "Reset",
					icon: "undo",
					disabled: __props.busy,
					onClick: _cache[4] || (_cache[4] = ($event) => emit("reset"))
				}, null, 8, ["disabled"]), createVNode(_sfc_main$7, {
					label: "Save storage policy",
					icon: "save",
					type: "submit",
					disabled: __props.busy || !__props.status?.indexed
				}, null, 8, ["disabled"])])], 32)) : createCommentVNode("", true),
				createBaseVNode("h3", null, toDisplayString(unref(t)("Garbage collection")), 1),
				createBaseVNode("p", null, toDisplayString(unref(t)("Dry run counts unused objects without deleting them. Safe GC expires retained records and quarantines unused contents according to the saved policy.")), 1),
				!__props.filesService ? (openBlock(), createElementBlock("p", _hoisted_8$1, toDisplayString(unref(t)("Enable the files service on the server to process GC tasks.")), 1)) : createCommentVNode("", true),
				createBaseVNode("div", _hoisted_9$1, [
					createVNode(_sfc_main$7, {
						label: "GC dry run",
						disabled: __props.busy || !__props.status?.indexed || !__props.filesService || ["queued", "running"].includes(__props.status?.gc?.state),
						onClick: _cache[6] || (_cache[6] = ($event) => emit("action", "gc_begin", true))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$7, {
						label: "Run safe GC",
						disabled: __props.busy || !__props.status?.indexed || !__props.filesService || ["queued", "running"].includes(__props.status?.gc?.state),
						onClick: _cache[7] || (_cache[7] = ($event) => emit("action", "gc_begin", false))
					}, null, 8, ["disabled"]),
					["queued", "running"].includes(__props.status?.gc?.state) ? (openBlock(), createBlock(_sfc_main$7, {
						key: 0,
						label: "Cancel GC",
						icon: "close",
						disabled: __props.busy,
						onClick: _cache[8] || (_cache[8] = ($event) => emit("action", "gc_cancel"))
					}, null, 8, ["disabled"])) : createCommentVNode("", true)
				]),
				__props.status?.gc ? (openBlock(), createElementBlock("div", _hoisted_10$1, [
					createBaseVNode("p", null, toDisplayString(__props.status.gc.code) + " · " + toDisplayString(unref(t)(__props.status.gc.state)) + " · " + toDisplayString(__props.status.gc.phase) + " · " + toDisplayString(unref(t)(__props.status.gc.dry_run ? "GC dry run" : "Run safe GC")), 1),
					createBaseVNode("p", null, toDisplayString(unref(t)("Objects scanned")) + ": " + toDisplayString(__props.status.gc.objects_done) + " · " + toDisplayString(unref(t)("Candidates")) + ": " + toDisplayString(__props.status.gc.candidates) + " · " + toDisplayString(unref(prettySize)(__props.status.gc.candidate_bytes || 0)), 1),
					createBaseVNode("p", null, toDisplayString(unref(t)("Expired records")) + ": " + toDisplayString(__props.status.gc.expired) + " · " + toDisplayString(unref(t)("Quarantined")) + ": " + toDisplayString(__props.status.gc.quarantined) + " · " + toDisplayString(unref(t)("Purged")) + ": " + toDisplayString(__props.status.gc.purged), 1),
					__props.status.gc.error ? (openBlock(), createElementBlock("p", _hoisted_11$1, toDisplayString(__props.status.gc.error), 1)) : createCommentVNode("", true),
					__props.status.gc.state === "error" ? (openBlock(), createElementBlock("p", _hoisted_12$1, toDisplayString(unref(t)("GC stopped. After fixing the cause, start a new dry run or safe GC.")), 1)) : createCommentVNode("", true)
				])) : createCommentVNode("", true)
			])], 8, _hoisted_1$1);
		};
	}
}, [["__scopeId", "data-v-a3b3e3d4"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceInspection.vue
var views = [
	{
		id: "files",
		title: "Files",
		icon: "file"
	},
	{
		id: "pending",
		title: "Pending",
		icon: "clock"
	},
	{
		id: "submitted",
		title: "Submitted",
		icon: "check"
	},
	{
		id: "shelved",
		title: "Shelved",
		icon: "archive"
	},
	{
		id: "history",
		title: "History",
		icon: "history"
	},
	{
		id: "tasks",
		title: "Transfers",
		icon: "cloud-upload"
	},
	{
		id: "workspaces",
		title: "Workspaces",
		icon: "desktop"
	},
	{
		id: "streams",
		title: "Streams",
		icon: "workflow"
	},
	{
		id: "stream_graph",
		title: "Stream Graph",
		icon: "account-tree"
	},
	{
		id: "storage",
		title: "Storage administration",
		icon: "database",
		admin: true
	}
];
views.splice(7, 0, {
	id: "depots",
	title: "Depots",
	icon: "database"
});
var _sfc_main = {
	components: {
		AppButton: _sfc_main$7,
		AppSelect: _sfc_main$9,
		AppTextField: _sfc_main$10,
		AppMenu: _sfc_main$11,
		AppMenuItem: _sfc_main$13,
		AppSplitter: _sfc_main$14,
		WorkspaceTabs: _sfc_main$16,
		FileWorkspaceTree: FileWorkspaceTree_default,
		FileWorkspaceInspector: FileWorkspaceInspector_default,
		FileWorkspaceLog: FileWorkspaceLog_default,
		FileWorkspaceDepots: FileWorkspaceDepots_default,
		FileWorkspaceStorage: FileWorkspaceStorage_default
	},
	props: {
		ticket: String,
		project: String,
		login: String,
		canAdminister: Boolean
	},
	emits: [
		"help",
		"ready",
		"debug"
	],
	data() {
		return {
			busy: false,
			error: "",
			disposed: false,
			generation: 0,
			aborter: null,
			administrator: false,
			repositories: [],
			filesService: false,
			depotSelection: null,
			depotDraft: null,
			depotOriginal: null,
			storageDraft: null,
			storageOriginal: null,
			indexing: false,
			poll: null,
			tabs: views.slice(0, 3),
			activeTabId: "pending",
			width: 280,
			streams: [],
			tree: [],
			heads: {},
			stream: "",
			prefix: "",
			rows: [],
			after: null,
			children: {},
			expanded: [],
			focus: null,
			scope: "",
			shelved: false,
			storage: null,
			edges: [],
			operationLog: [],
			sequence: 0
		};
	},
	computed: {
		viewPresets() {
			return views.filter((view) => !view.admin || this.administrator);
		},
		changeView() {
			return [
				"pending",
				"submitted",
				"shelved"
			].includes(this.activeTabId);
		},
		changeTree() {
			return this.rows.flatMap((row) => [
				{
					...row,
					id: row.code,
					kind: "change",
					depth: 0,
					expanded: this.expanded.includes(row.code)
				},
				...this.expanded.includes(row.code) ? (this.children[row.code]?.items || []).map((file) => ({
					...file,
					name: file.path,
					id: row.code + "/" + file.path,
					kind: "file",
					depth: 1,
					parent: row.code,
					stream: row.stream
				})) : [],
				...this.expanded.includes(row.code) && this.children[row.code]?.after ? [{
					id: row.code + "/more",
					kind: "more",
					name: "Load more",
					depth: 1,
					parent: row.code
				}] : []
			]);
		}
	},
	mounted() {
		try {
			const saved = JSON.parse(localStorage.getItem(this.settingsKey()));
			if (saved) {
				this.tabs = (saved.tabs || this.tabs).filter((tab) => views.some((view) => view.id === tab.id));
				this.activeTabId = saved.activeTabId || "pending";
				this.width = Math.min(600, Math.max(220, saved.width || 280));
				this.stream = saved.stream || "";
				this.prefix = saved.prefix || "";
			}
		} catch {}
		this.poll = setInterval(() => {
			if (this.activeTabId === "storage" && !this.busy && ["queued", "running"].includes(this.storage?.gc?.state)) this.storageAction("storage_status");
		}, 2e3);
		this.run(async (signal) => {
			const { items: [capabilities, depots, streams] } = await this.command("read_batch", { requests: [
				{
					action: "capabilities",
					values: {}
				},
				{
					action: "depots",
					values: { limit: 200 }
				},
				{
					action: "streams",
					values: { limit: 200 }
				}
			] }, signal);
			signal.throwIfAborted();
			this.administrator = capabilities.administrator;
			this.repositories = capabilities.repositories || [];
			this.filesService = capabilities.files_service_configured;
			this.tabs = this.tabs.filter((tab) => !tab.admin || this.administrator);
			if (!this.tabs.some((tab) => tab.id === this.activeTabId)) this.activeTabId = this.tabs[0]?.id || "";
			signal.throwIfAborted();
			this.streams = streams.items;
			this.stream = this.streams.some((row) => row.code === this.stream) ? this.stream : this.streams[0]?.code || "";
			this.tree = depots.items.flatMap((depot) => [{
				id: "depot/" + depot.code,
				kind: "depot",
				name: depot.code,
				depth: 0,
				expanded: true
			}, ...this.streams.filter((row) => row.depot === depot.code).map((row) => ({
				id: "stream/" + row.code,
				kind: "stream",
				name: row.code,
				stream: row.code,
				directory: "",
				depth: 1,
				expanded: false
			}))]);
			await this.load(signal);
			this.$emit("ready");
		});
	},
	beforeUnmount() {
		this.disposed = true;
		this.indexing = false;
		clearInterval(this.poll);
		this.generation++;
		this.aborter?.abort();
	},
	methods: {
		t,
		prettySize,
		settingsKey() {
			return `file-inspection/${this.login}/${this.project}`;
		},
		remember() {
			localStorage.setItem(this.settingsKey(), JSON.stringify({
				tabs: this.tabs,
				activeTabId: this.activeTabId,
				width: this.width,
				stream: this.stream,
				prefix: this.prefix
			}));
		},
		dirty() {
			return JSON.stringify(this.depotDraft) !== JSON.stringify(this.depotOriginal) || Boolean(this.storageDraft && JSON.stringify(this.storageDraft.policy) !== JSON.stringify(this.storageOriginal));
		},
		canLeave() {
			if (this.dirty()) {
				this.error = t("Save or reset Depot and Storage changes before leaving this project.");
				return false;
			}
			return !this.busy;
		},
		async command(action, values = {}, signal) {
			const response = await fetch("/file-project/command?" + new URLSearchParams({ project: this.project }), {
				method: "POST",
				signal,
				headers: {
					"Content-Type": "application/json",
					"X-Tactic-Ticket": this.ticket
				},
				body: JSON.stringify({
					action,
					...values
				})
			});
			const body = await response.json();
			if (!response.ok) {
				const error = new Error(body.error || response.statusText);
				error.file_error = body.file_error;
				throw error;
			}
			return body;
		},
		async run(work) {
			this.aborter?.abort();
			this.aborter = markRaw(new AbortController());
			const generation = ++this.generation;
			this.busy = true;
			this.error = "";
			try {
				await work(this.aborter.signal);
			} catch (error) {
				if (generation === this.generation && error.name !== "AbortError") {
					this.error = t(redact(error.message));
					this.operationLog.push({
						id: ++this.sequence,
						time: (/* @__PURE__ */ new Date()).toLocaleTimeString(),
						level: "ERROR",
						operation: t("File operation"),
						message: this.error,
						path: redact(error.file_error?.path || "")
					});
					this.operationLog = this.operationLog.slice(-1e3);
					logEvent({
						level: "ERROR",
						group: "file/inspection",
						message: this.error,
						details: error.file_error
					});
				}
			} finally {
				if (generation === this.generation && !this.disposed) {
					this.busy = false;
					this.remember();
				}
			}
		},
		async load(signal, more = false) {
			const options = {
				limit: 200,
				after: more ? this.after || "" : ""
			};
			let result;
			if (this.changeView) result = await this.command("changes", {
				...options,
				state: this.activeTabId,
				scope: this.administrator ? "all" : "mine"
			}, signal);
			else if (this.activeTabId === "files") result = this.stream ? await this.command("list", {
				...options,
				stream: this.stream,
				prefix: this.prefix
			}, signal) : { items: [] };
			else if (this.activeTabId === "history") result = this.focus ? await this.command("history", {
				stream: this.focus.stream,
				path: this.focus.source_path || this.focus.path,
				limit: 200
			}, signal) : { items: [] };
			else if (this.activeTabId === "tasks") result = await this.command("transfer_tasks", options, signal);
			else if (this.activeTabId === "storage") {
				const storage = await this.command("storage_status", {}, signal);
				signal.throwIfAborted();
				this.acceptStorage(storage);
				result = { items: [] };
			} else if ([
				"depots",
				"workspaces",
				"streams",
				"stream_graph"
			].includes(this.activeTabId)) result = await this.command(this.activeTabId, options, signal);
			else result = { items: [] };
			signal.throwIfAborted();
			if (this.activeTabId === "depots") this.depotSelection = null;
			this.rows = result.items;
			this.after = result.after || null;
			this.edges = result.edges || [];
			this.children = {};
			this.expanded = [];
		},
		refresh() {
			return this.run((signal) => this.load(signal));
		},
		async openView(view) {
			if (!view || this.busy) return;
			if (!this.tabs.some((tab) => tab.id === view.id)) this.tabs.push(view);
			this.activeTabId = view.id;
			await this.refresh();
		},
		async closeTab(id) {
			if (this.busy) return;
			this.tabs = this.tabs.filter((tab) => tab.id !== id);
			if (this.activeTabId === id) {
				this.activeTabId = this.tabs[0]?.id || "";
				await this.refresh();
			}
			this.remember();
		},
		expand(node) {
			if (node.kind === "depot") return;
			return this.run(async (signal) => {
				const index = this.tree.findIndex((row) => row.id === node.id);
				let end = index + 1;
				while (end < this.tree.length && this.tree[end].depth > node.depth) end++;
				if (node.expanded) {
					this.tree.splice(index + 1, end - index - 1);
					node.expanded = false;
					return;
				}
				const page = await this.command("browse", {
					stream: node.stream,
					directory: node.directory,
					after: node.kind === "more" ? node.after : "",
					published_change: this.heads[node.stream],
					limit: 200
				}, signal);
				signal.throwIfAborted();
				this.heads[node.stream] = page.published_change;
				const children = page.items.map((row) => ({
					...row,
					id: "path/" + node.stream + "/" + row.path,
					depth: node.depth + (node.kind === "more" ? 0 : 1),
					stream: node.stream,
					directory: row.kind === "directory" ? row.path : "",
					expanded: false
				}));
				if (page.after) children.push({
					id: node.id + "/more",
					kind: "more",
					name: "Load more",
					depth: node.depth + (node.kind === "more" ? 0 : 1),
					stream: node.stream,
					directory: node.directory,
					after: page.after
				});
				if (node.kind === "more") this.tree.splice(index, 1, ...children);
				else this.tree.splice(index + 1, end - index - 1, ...children);
				node.expanded = true;
				if (this.tree.length > 2e3) {
					this.tree.splice(2, this.tree.length - 2e3);
					this.operationLog.push({
						id: ++this.sequence,
						time: (/* @__PURE__ */ new Date()).toLocaleTimeString(),
						level: "INFO",
						operation: t("File operation"),
						message: t("Earlier tree rows released; reopen a folder to reload them.")
					});
				}
			});
		},
		selectDepot(node) {
			if (node.kind === "more") return this.expand(node);
			if (node.kind === "file") {
				this.focus = node;
				this.scope = "";
				this.shelved = false;
			} else if (["directory", "stream"].includes(node.kind)) {
				this.stream = node.stream;
				this.prefix = node.directory;
				if (this.activeTabId === "files") this.refresh();
			}
		},
		expandChange(node) {
			if (node.kind === "file") {
				this.focus = node;
				this.scope = node.parent;
				this.shelved = this.activeTabId === "shelved";
				return;
			}
			if (node.kind === "change" && this.expanded.includes(node.code)) {
				this.expanded = this.expanded.filter((code) => code !== node.code);
				delete this.children[node.code];
				return;
			}
			const code = node.parent || node.code, row = this.rows.find((row) => row.code === code);
			return this.run(async (signal) => {
				const page = await this.command("inspect_change_files", {
					[row.state === "shelved" ? "shelf" : "change"]: code,
					limit: 200,
					after: node.kind === "more" ? this.children[code].after : ""
				}, signal);
				signal.throwIfAborted();
				this.children[code] = page;
				if (!this.expanded.includes(code)) this.expanded.push(code);
			});
		},
		selectFile(row) {
			this.focus = {
				...row,
				stream: this.stream
			};
			this.scope = "";
			this.shelved = false;
		},
		selectDepotRecord(row) {
			this.depotSelection = row;
		},
		editDepot(row) {
			if (this.depotDraft && JSON.stringify(this.depotDraft) !== JSON.stringify(this.depotOriginal)) {
				this.error = t("Save or reset the current depot draft first.");
				return;
			}
			return this.run(async (signal) => {
				const info = row ? await this.command("depot_status", { depot: row.code }, signal) : {};
				signal.throwIfAborted();
				this.depotDraft = {
					creating: !row,
					code: info.code || "",
					title: info.title || "",
					repository: info.storage?.repository || "",
					revision: info.revision || 0
				};
				this.depotOriginal = { ...this.depotDraft };
			});
		},
		resetDepot() {
			this.depotDraft = { ...this.depotOriginal };
			this.error = "";
		},
		cancelDepot() {
			if (JSON.stringify(this.depotDraft) !== JSON.stringify(this.depotOriginal)) {
				this.error = t("Save or reset the current depot draft first.");
				return;
			}
			this.depotDraft = null;
			this.depotOriginal = null;
		},
		saveDepot() {
			const draft = this.depotDraft;
			return this.run(async (signal) => {
				const values = {
					title: draft.title,
					repository: draft.repository || null,
					...draft.creating ? { code: draft.code.trim() } : {
						depot: draft.code,
						revision: draft.revision
					}
				};
				const result = await this.command(draft.creating ? "create_depot" : "update_depot", values, signal);
				signal.throwIfAborted();
				this.depotDraft = null;
				this.depotOriginal = null;
				await this.load(signal);
				signal.throwIfAborted();
				this.depotSelection = result;
			});
		},
		acceptStorage(status) {
			const pristine = !this.storageDraft || JSON.stringify(this.storageDraft.policy) === JSON.stringify(this.storageOriginal);
			this.storage = status;
			if (pristine && status.policy_values) this.resetPolicy();
		},
		resetPolicy() {
			this.storageOriginal = this.storage?.policy_values ? { ...this.storage.policy_values } : null;
			this.storageDraft = this.storage?.policy_values ? {
				revision: this.storage.policy_revision,
				policy: { ...this.storage.policy_values }
			} : null;
			this.error = "";
		},
		savePolicy() {
			return this.run(async (signal) => {
				for (const [key, value] of Object.entries(this.storageDraft.policy)) if (!/^[0-9]{1,19}$/.test(value) || BigInt(value) > 9223372036854775807n || key === "max_parallel" && (BigInt(value) < 1n || BigInt(value) > 16n)) throw new Error(t("Enter non-negative whole numbers; parallel transfers must be from 1 to 16."));
				await this.command("storage_policy", {
					revision: this.storageDraft.revision,
					policy: this.storageDraft.policy
				}, signal);
				this.acceptStorage(await this.command("storage_status", {}, signal));
				signal.throwIfAborted();
				this.resetPolicy();
			});
		},
		storageAction(operation, dry_run) {
			if (this.busy) return;
			if (operation === "gc_begin" && dry_run === false && !window.confirm(t("Run safe GC using the configured retention policy?"))) return;
			return this.run(async (signal) => {
				this.indexing = operation === "storage_index";
				try {
					const values = operation === "gc_begin" ? { dry_run } : operation === "gc_cancel" ? { task: this.storage.gc.code } : {};
					await this.command(operation, values, signal);
					signal.throwIfAborted();
					this.acceptStorage(await this.command("storage_status", {}, signal));
					while (this.indexing && !this.storage.indexed) {
						await this.command("storage_index", {}, signal);
						signal.throwIfAborted();
						this.acceptStorage(await this.command("storage_status", {}, signal));
					}
				} finally {
					this.indexing = false;
				}
			});
		},
		async copyLog() {
			await copyText(this.operationLog.map((row) => [
				row.time,
				row.message,
				row.path
			].filter(Boolean).join(" · ")).join("\n"));
		},
		async copyPath() {
			if (this.focus) await copyText("//" + this.focus.stream + "/" + (this.focus.source_path || this.focus.path));
		}
	}
};
var _hoisted_1 = ["aria-busy", "aria-label"];
var _hoisted_2 = { class: "inspection-toolbar" };
var _hoisted_3 = { class: "muted" };
var _hoisted_4 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_5 = { class: "inspection-body" };
var _hoisted_6 = {
	key: 0,
	class: "muted"
};
var _hoisted_7 = {
	key: 0,
	class: "inspection-filter"
};
var _hoisted_8 = { class: "inspection-scroll" };
var _hoisted_9 = [
	"aria-selected",
	"onClick",
	"onKeydown"
];
var _hoisted_10 = { key: 0 };
var _hoisted_11 = { key: 1 };
var _hoisted_12 = { key: 5 };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppMenuItem = resolveComponent("AppMenuItem");
	const _component_AppMenu = resolveComponent("AppMenu");
	const _component_AppButton = resolveComponent("AppButton");
	const _component_FileWorkspaceTree = resolveComponent("FileWorkspaceTree");
	const _component_AppSplitter = resolveComponent("AppSplitter");
	const _component_WorkspaceTabs = resolveComponent("WorkspaceTabs");
	const _component_FileWorkspaceDepots = resolveComponent("FileWorkspaceDepots");
	const _component_FileWorkspaceStorage = resolveComponent("FileWorkspaceStorage");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_AppTextField = resolveComponent("AppTextField");
	const _component_FileWorkspaceInspector = resolveComponent("FileWorkspaceInspector");
	const _component_FileWorkspaceLog = resolveComponent("FileWorkspaceLog");
	return openBlock(), createElementBlock("section", {
		class: "file-workspace",
		"aria-busy": $data.busy,
		"aria-label": $options.t("File project inspection")
	}, [
		createBaseVNode("header", _hoisted_2, [
			createVNode(_component_AppMenu, {
				label: "View",
				"show-label": "",
				overlay: ""
			}, {
				default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList($options.viewPresets, (view) => {
					return openBlock(), createBlock(_component_AppMenuItem, {
						key: view.id,
						label: view.title,
						icon: view.icon,
						onClick: ($event) => $options.openView(view)
					}, null, 8, [
						"label",
						"icon",
						"onClick"
					]);
				}), 128))]),
				_: 1
			}),
			createVNode(_component_AppButton, {
				label: "Refresh",
				icon: "refresh",
				disabled: $data.busy,
				onClick: $options.refresh
			}, null, 8, ["disabled", "onClick"]),
			createBaseVNode("span", _hoisted_3, toDisplayString($options.t("Use TACTIC Handler for checkout, local changes and Submit.")), 1),
			createVNode(_component_AppButton, {
				label: "Help",
				icon: "help",
				onClick: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("help", "file_workspace"))
			})
		]),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString($data.error), 1)) : createCommentVNode("", true),
		createBaseVNode("div", _hoisted_5, [
			createBaseVNode("nav", { style: normalizeStyle({ width: $data.width + "px" }) }, [createVNode(_component_FileWorkspaceTree, {
				nodes: $data.tree,
				busy: $data.busy,
				"can-drag": false,
				label: "Depot tree",
				onExpand: $options.expand,
				onSelect: $options.selectDepot
			}, null, 8, [
				"nodes",
				"busy",
				"onExpand",
				"onSelect"
			])], 4),
			createVNode(_component_AppSplitter, {
				modelValue: $data.width,
				"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => $data.width = $event),
				label: "Depots",
				min: 220,
				max: 600
			}, null, 8, ["modelValue"]),
			createBaseVNode("main", null, [
				createVNode(_component_WorkspaceTabs, {
					kind: "view",
					tabs: $data.tabs,
					selected: $data.activeTabId,
					onSelect: _cache[2] || (_cache[2] = ($event) => $options.openView($options.viewPresets.find((view) => view.id === $event))),
					onClose: $options.closeTab,
					onReorder: _cache[3] || (_cache[3] = ($event) => {
						$data.tabs = $event;
						$options.remember();
					})
				}, null, 8, [
					"tabs",
					"selected",
					"onClose"
				]),
				!$data.tabs.length ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString($options.t("Open a view from the View menu")), 1)) : createCommentVNode("", true),
				$options.changeView ? (openBlock(), createBlock(_component_FileWorkspaceTree, {
					key: 1,
					nodes: $options.changeTree,
					busy: $data.busy,
					"can-drag": false,
					label: "Changelist tree",
					onExpand: $options.expandChange,
					onSelect: $options.expandChange
				}, null, 8, [
					"nodes",
					"busy",
					"onExpand",
					"onSelect"
				])) : $data.activeTabId === "depots" ? (openBlock(), createBlock(_component_FileWorkspaceDepots, {
					key: 2,
					rows: $data.rows,
					after: $data.after,
					selected: $data.depotSelection,
					draft: $data.depotDraft,
					repositories: $data.repositories,
					administrator: $data.administrator,
					busy: $data.busy,
					onRefresh: $options.refresh,
					onMore: _cache[4] || (_cache[4] = ($event) => $options.run((signal) => $options.load(signal, true))),
					onSelect: $options.selectDepotRecord,
					onEdit: $options.editDepot,
					onChange: _cache[5] || (_cache[5] = ($event) => $data.depotDraft = $event),
					onSave: $options.saveDepot,
					onReset: $options.resetDepot,
					onCancel: $options.cancelDepot
				}, null, 8, [
					"rows",
					"after",
					"selected",
					"draft",
					"repositories",
					"administrator",
					"busy",
					"onRefresh",
					"onSelect",
					"onEdit",
					"onSave",
					"onReset",
					"onCancel"
				])) : $data.activeTabId === "storage" && $data.storage ? (openBlock(), createBlock(_component_FileWorkspaceStorage, {
					key: 3,
					status: $data.storage,
					draft: $data.storageDraft,
					busy: $data.busy,
					indexing: $data.indexing,
					"files-service": $data.filesService,
					onChange: _cache[6] || (_cache[6] = ($event) => $data.storageDraft = $event),
					onSave: $options.savePolicy,
					onReset: $options.resetPolicy,
					onAction: $options.storageAction,
					onStop: _cache[7] || (_cache[7] = ($event) => $data.indexing = false)
				}, null, 8, [
					"status",
					"draft",
					"busy",
					"indexing",
					"files-service",
					"onSave",
					"onReset",
					"onAction"
				])) : (openBlock(), createElementBlock(Fragment, { key: 4 }, [$data.activeTabId === "files" ? (openBlock(), createElementBlock("div", _hoisted_7, [
					createVNode(_component_AppSelect, {
						modelValue: $data.stream,
						"onUpdate:modelValue": [_cache[8] || (_cache[8] = ($event) => $data.stream = $event), $options.refresh],
						label: "Streams",
						options: $data.streams.map((row) => ({
							value: row.code,
							label: row.code
						})),
						"translate-labels": false
					}, null, 8, [
						"modelValue",
						"options",
						"onUpdate:modelValue"
					]),
					createVNode(_component_AppTextField, {
						modelValue: $data.prefix,
						"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => $data.prefix = $event),
						label: "Path prefix",
						onKeydown: withKeys($options.refresh, ["enter"])
					}, null, 8, ["modelValue", "onKeydown"]),
					createVNode(_component_AppButton, {
						label: "Filter",
						icon: "filter",
						onClick: $options.refresh
					}, null, 8, ["onClick"])
				])) : createCommentVNode("", true), createBaseVNode("div", _hoisted_8, [
					createBaseVNode("table", null, [createBaseVNode("thead", null, [createBaseVNode("tr", null, [
						createBaseVNode("th", null, toDisplayString($options.t($data.activeTabId === "files" ? "File" : $data.activeTabId === "history" ? "Revision" : "Details")), 1),
						createBaseVNode("th", null, toDisplayString($options.t("State")), 1),
						createBaseVNode("th", null, toDisplayString($options.t("File size")), 1)
					])]), createBaseVNode("tbody", null, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.rows, (row, index) => {
						return openBlock(), createElementBlock("tr", {
							key: row.path || row.code || row.task || index,
							tabindex: "0",
							"aria-selected": $data.focus?.path === row.path,
							onClick: ($event) => $data.activeTabId === "files" && $options.selectFile(row),
							onKeydown: withKeys(($event) => $data.activeTabId === "files" && $options.selectFile(row), ["enter"])
						}, [
							createBaseVNode("td", null, toDisplayString(row.path || row.code || row.task || "#" + row.number), 1),
							createBaseVNode("td", null, toDisplayString(row.state || row.stream || row.action || "—"), 1),
							createBaseVNode("td", null, toDisplayString($options.prettySize(row.size || row.bytes_total || 0)), 1)
						], 40, _hoisted_9);
					}), 128))])]),
					[
						"workspaces",
						"streams",
						"stream_graph"
					].includes($data.activeTabId) ? (openBlock(), createElementBlock("pre", _hoisted_10, toDisplayString(JSON.stringify($data.rows, null, 2)), 1)) : createCommentVNode("", true),
					$data.activeTabId === "stream_graph" ? (openBlock(), createElementBlock("pre", _hoisted_11, toDisplayString(JSON.stringify($data.edges, null, 2)), 1)) : createCommentVNode("", true)
				])], 64)),
				!["depots", "storage"].includes($data.activeTabId) ? (openBlock(), createElementBlock("footer", _hoisted_12, [$data.after ? (openBlock(), createBlock(_component_AppButton, {
					key: 0,
					label: "Next page",
					icon: "next",
					disabled: $data.busy,
					onClick: _cache[10] || (_cache[10] = ($event) => $options.run((signal) => $options.load(signal, true)))
				}, null, 8, ["disabled"])) : createCommentVNode("", true), createVNode(_component_AppButton, {
					label: "Copy depot path",
					icon: "copy",
					disabled: !$data.focus,
					onClick: $options.copyPath
				}, null, 8, ["disabled", "onClick"])])) : createCommentVNode("", true),
				!["depots", "storage"].includes($data.activeTabId) ? (openBlock(), createBlock(_component_FileWorkspaceInspector, {
					key: 6,
					call: $options.command,
					row: $data.focus,
					stream: $data.stream,
					scope: $data.scope,
					shelved: $data.shelved,
					workspace: ""
				}, null, 8, [
					"call",
					"row",
					"stream",
					"scope",
					"shelved"
				])) : createCommentVNode("", true)
			])
		]),
		createVNode(_component_FileWorkspaceLog, {
			entries: $data.operationLog,
			onClear: _cache[11] || (_cache[11] = ($event) => $data.operationLog = []),
			onCopy: $options.copyLog,
			onDebug: _cache[12] || (_cache[12] = ($event) => _ctx.$emit("debug"))
		}, null, 8, ["entries", "onCopy"])
	], 8, _hoisted_1);
}
var FileWorkspaceInspection_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render], ["__scopeId", "data-v-0221b13a"]]);
//#endregion
export { FileWorkspaceInspection_default as default };

//# sourceMappingURL=FileWorkspaceInspection.js.map
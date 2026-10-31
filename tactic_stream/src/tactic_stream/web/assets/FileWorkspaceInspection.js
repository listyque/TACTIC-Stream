import { A as onMounted, E as nextTick, F as resolveComponent, G as withCtx, H as watch, J as markRaw, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, Q as shallowRef, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment } from "./vue.js";
import { T as metrics, o as t, s as appearance, t as _sfc_main$16, u as frameColors, y as cssRoles, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { jt as redact, kt as logEvent } from "./index.js";
import { A as _sfc_main$18, F as _sfc_main$20, G as node, H as label, K as rect, R as observeFrameSizes, S as translate, V as button, a as _sfc_main$21, m as copyText, t as _sfc_main$17, z as _sfc_main$19 } from "./FrameView.js";
import { t as captionHeight } from "./sections.ui.js";
import { r as prettySize } from "./file_values.js";
import "./files.js";
import { Q as _sfc_main$22 } from "./ConfiguredView.js";
import { t as actionLayout } from "./metrics.js";
import { t as describe$7 } from "./confirmation.ui.js";
import { t as _sfc_main$23 } from "./AppDialog.js";
import { b as _sfc_main$24 } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/files/workspace/toolbar.ui.mjs
function views$1(model, width, height, language) {
	const tr = (text) => translate(text, language), h = metrics(model.style).controlHeight, nodes = [], y = Math.max(0, (h - 28) / 2);
	let x = 0;
	if (model.narrow) {
		nodes.push(button("workspaceToggleTree", rect(x, y, 28, 28), tr("Depots"), "account-tree", { type: "tree" }, true, {
			iconOnly: true,
			iconAction: true
		}));
		x += 32;
	}
	nodes.push(node("Box", "workspaceViewsSurface", rect(x, 0, h, h), {
		background: "surfaceContainerHigh",
		radius: h / 2
	}));
	nodes.push(button("workspaceViewsButton", rect(x, 0, h, h), tr("View"), "view-column", {
		type: "menu",
		kind: "views"
	}, true, {
		iconOnly: true,
		iconAction: true,
		round: false
	}));
	x += h + 4;
	const right = (model.canCreate ? 32 : 0) + (model.canMaximize ? 32 : 0) + (model.canActions === false ? 0 : 32);
	nodes.push(node("View", "workspaceViewTabsPort", rect(x, 0, Math.max(0, width - x - right), height), { view: "tabs" }));
	x = Math.max(x, width - right);
	if (model.canCreate) {
		nodes.push(button("newChangelistButton", rect(x, y, 28, 28), tr("New changelist"), "add", { type: "create" }, !model.busy && !!model.workspace, {
			iconOnly: true,
			iconAction: true
		}));
		x += 32;
	}
	if (model.canMaximize) {
		nodes.push(button("fileWorkspaceMaximize", rect(x, y, 28, 28), tr(model.maximized ? "Restore panel" : "Maximize panel"), model.maximized ? "window-restore" : "open-in-full", { type: "maximize" }, true, {
			iconOnly: true,
			iconAction: true
		}));
		x += 32;
	}
	if (model.canActions !== false) nodes.push(button("workspaceActionsButton", rect(x, y, 28, 28), tr("Workspace actions"), "more_vert", {
		type: "menu",
		kind: "workspace"
	}, true, {
		iconOnly: true,
		iconAction: true
	}));
	return { nodes };
}
var WorkspaceToolbar_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceToolbar",
	props: {
		tabs: Array,
		selected: String,
		presets: Array
	},
	emits: [
		"select",
		"close",
		"reorder",
		"open"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), menu = ref(null), anchor = shallowRef(null), width = ref(800), gutter = ref(0);
		const height = computed(() => metrics(appearance.theme).controlHeight + gutter.value);
		const scene = computed(() => views$1({
			style: appearance.theme,
			canActions: false
		}, width.value, height.value, appearance.language));
		const views = computed(() => ({ tabs: {
			component: markRaw(_sfc_main$24),
			props: {
				kind: "view",
				tabs: props.tabs,
				selected: props.selected,
				onSelect: (value) => emit("select", value),
				onClose: (value) => emit("close", value),
				onReorder: (value) => emit("reorder", value),
				onGutter: (value) => gutter.value = value
			}
		} }));
		function event(action, source) {
			if (action.type === "menu" && action.kind === "views") {
				anchor.value = source;
				menu.value.openAt({ target: source });
			}
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => width.value = entries.at(-1).contentRect.width);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "inspection-views",
				style: normalizeStyle({ height: height.value + "px" })
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				views: views.value,
				onEvent: event
			}, null, 8, ["scene", "views"]), createVNode(_sfc_main$18, {
				ref_key: "menu",
				ref: menu,
				label: "View",
				anchor: anchor.value,
				"external-trigger": "",
				overlay: "",
				"align-start": ""
			}, {
				default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.presets, (view) => {
					return openBlock(), createBlock(_sfc_main$22, {
						key: view.id,
						label: view.title,
						icon: view.icon,
						onClick: ($event) => emit("open", view)
					}, null, 8, [
						"label",
						"icon",
						"onClick"
					]);
				}), 128))]),
				_: 1
			}, 8, ["anchor"])], 4);
		};
	}
}, [["__scopeId", "data-v-faf1e8a5"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/presentation.mjs
function badges(row) {
	const result = [];
	const action = row.action || row.server_status || "";
	const local = row.local_status || "";
	if (row.transfer_state && ["staged"].indexOf(row.transfer_state) < 0) result.push({
		label: {
			waiting: "Waiting for upload",
			uploading: "Uploading",
			uploaded: "Uploaded; waiting for verification",
			verifying: "Verifying",
			verified: "Verified; waiting for staging",
			error: "Failed"
		}[row.transfer_state] || row.transfer_state,
		icon: "cloud-upload",
		tone: row.transfer_state === "error" ? "error" : "action"
	});
	if (local === "unmapped" || action === "unmapped") result.push({
		label: "Not mapped to workspace",
		icon: "folder-lock",
		tone: "neutral"
	});
	if (action === "move/add" || action === "move/delete") result.push({
		label: "Renamed / moved",
		icon: "swap-horizontal",
		tone: "action"
	});
	if (action === "checkout" && !row.base && !row.file && !row.transfer_state) result.push({
		label: "Waiting for upload",
		icon: "cloud-upload",
		tone: "warning"
	});
	if (row.conflict || row.needs_resolve) result.push({
		label: "Conflict",
		icon: "warning",
		tone: "error"
	});
	if (row.error) result.push({
		label: "Failed",
		icon: "error",
		tone: "error"
	});
	if (local === "modified") result.push({
		label: action === "write" && row.change_state === "pending" && row.staged_current === false ? "Modified after upload" : "Modified",
		icon: "edit",
		tone: "warning"
	});
	if (local === "added") result.push({
		label: "Added",
		icon: "add",
		tone: "success"
	});
	if (local === "missing") result.push({
		label: "Missing",
		icon: "file-remove",
		tone: "error"
	});
	if (action === "delete" || row.deleted) result.push({
		label: "Marked for delete",
		icon: "delete",
		tone: "error"
	});
	if (row.staged_current === false && local !== "modified") result.push({
		label: "Modified after upload",
		icon: "edit",
		tone: "warning"
	});
	if (action === "write" && row.staged_current !== false) result.push({
		label: row.change_state === "shelved" ? "Shelved" : row.change_state === "submitted" ? "Submitted" : "Uploaded",
		icon: "cloud-check",
		tone: "success"
	});
	if (action === "checkout") result.push({
		label: "Checked out",
		icon: "edit",
		tone: "action"
	});
	if (action === "newer") result.push({
		label: "Newer on server",
		icon: "cloud-download",
		tone: "warning"
	});
	if (row.head_state === "server-only") result.push({
		label: "Server only",
		icon: "cloud",
		tone: "neutral"
	});
	if (row.head_state === "newer" && action !== "newer") result.push({
		label: "Newer on server",
		icon: "cloud-download",
		tone: "warning"
	});
	if (row.head_state === "deleted") result.push({
		label: "Deleted on server",
		icon: "delete",
		tone: "error"
	});
	if (action === "untracked") result.push({
		label: "Untracked",
		icon: "file-plus",
		tone: "warning"
	});
	if (!result.length) result.push({
		label: action === "current" || row.head_state === "current" ? "Current" : row.head_state === "server-absent" ? "Not on server" : "Published",
		icon: "file",
		tone: "neutral"
	});
	return result;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/rows.ui.mjs
var toneRole = (tone) => ({
	error: "error",
	warning: "yellow",
	success: "green",
	action: "action",
	other: "violet"
})[tone] || "secondaryText";
var isBranch = (row) => [
	"depot",
	"stream",
	"workspace",
	"directory",
	"change"
].includes(row.kind);
function treeMetrics(row, subtitle = "") {
	const indent = Math.min(8, Math.max(0, row.depth || 0)) * 16 + 2;
	return {
		height: subtitle ? 42 : 30,
		indent,
		captionX: indent + 26
	};
}
function treeTitle(row, language) {
	const tr = (text) => translate(text, language);
	if (row.kind === "more") return tr("Load more");
	if (row.kind !== "change") return row.name || row.path || "";
	return tr("Changelist #{number}").replace("{number}", row.number || row.code) + " · " + (row.description || tr("No description"));
}
function treeSubtitle(row, language) {
	if (row.kind !== "change") return "";
	const tr = (text) => translate(text, language), actions = row.file_actions;
	const counts = actions ? (actions.checkout || 0) + " " + tr("waiting") + " / " + Object.entries(actions).filter(([action]) => action !== "checkout").reduce((sum, [, count]) => sum + count, 0) + " " + tr("staged") : tr("Counts not indexed");
	return [
		tr({
			pending: "Pending",
			submitted: "Submitted",
			shelved: "Shelved",
			reverted: "Reverted"
		}[row.state] || row.state || ""),
		row.owner,
		row.workspace,
		row.stream,
		(row.opened_files || 0) + " " + tr("files"),
		counts,
		(row.conflict_files || 0) + " " + tr("conflicts"),
		row.state === "pending" && row.local_counts?.files ? row.local_counts.files + " " + tr("local unstaged") : "",
		((row.opened_bytes || 0) / 1048576).toFixed(1) + " MB"
	].filter(Boolean).join(" · ");
}
function treeRow(model, width) {
	const row = model.row, metrics = treeMetrics(row, model.subtitle), height = metrics.height;
	const captionX = model.contentOnly ? 0 : metrics.captionX;
	const icon = {
		workspace: "desktop",
		depot: "database",
		stream: "workflow",
		directory: row.expanded ? "folder-open" : "folder",
		change: "archive",
		more: "add",
		file: "file"
	}[row.kind] || "file";
	const color = row.kind === "change" ? row.state === "submitted" ? "green" : row.state === "shelved" ? "violet" : "yellow" : "secondaryText";
	const textWidth = Math.max(0, width - captionX - 26 - (row.kind === "change" ? 20 : 4));
	const children = [node("Icon", "workspaceTreeIcon", rect(captionX, (height - 17) / 2, 17, 17), {
		icon,
		color
	}), label("workspaceTreeCaption", rect(captionX + 21, model.subtitle ? 1 : 0, textWidth, model.subtitle ? 22 : height), model.caption, {
		elideMiddle: true,
		fontRole: "secondary"
	})];
	if (model.subtitle) children.push(label("workspaceTreeSubtitle", rect(captionX + 21, 23, textWidth, 17), model.subtitle, {
		color: "secondaryText",
		fontRole: "caption"
	}));
	if (row.kind === "change") children.push(node("Icon", "workspaceTreeState", rect(Math.max(captionX, width - 18), (height - 14) / 2, 14, 14), {
		icon: {
			submitted: "check-circle",
			shelved: "archive",
			reverted: "undo"
		}[row.state] || "schedule",
		color: "secondaryText"
	}));
	return { nodes: [node("Box", "workspaceTreeSurface", rect(0, 0, width, height), {
		background: model.selected ? "selected" : model.pressed ? "rowHover" : model.hovered ? "rowHover" : "transparent",
		radius: 10,
		children
	})] };
}
var WorkspaceTreePaint_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceTreePaint",
	props: {
		row: Object,
		caption: String,
		subtitle: String
	},
	setup(__props) {
		const props = __props;
		const host = ref(null), width = ref(0);
		let observer;
		const scene = computed(() => treeRow({
			row: props.row,
			caption: props.caption,
			subtitle: props.subtitle,
			contentOnly: true
		}, width.value));
		onMounted(() => {
			observer = observeFrameSizes((entries) => width.value = entries.at(-1).contentRect.width);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				ref_key: "host",
				ref: host,
				class: "workspace-tree-paint"
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				interactive: false
			}, null, 8, ["scene"])], 512);
		};
	}
}, [["__scopeId", "data-v-169b1123"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceTree.vue
var _hoisted_1$8 = ["aria-label"];
var _hoisted_2$2 = [
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
var _hoisted_3$2 = {
	key: 1,
	class: "file-tree-indent"
};
var _hoisted_4$2 = {
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
		const branch = isBranch;
		const title = (node) => treeTitle(node, appearance.language);
		const subtitle = (node) => treeSubtitle(node, appearance.language);
		const rowStyle = (node) => ({
			"--depth": node.depth,
			height: treeMetrics(node, subtitle(node)).height + "px"
		});
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
						drop: !!__props.dropTarget && __props.dropTarget === node.code,
						invalid: invalid.value === node.id
					}]),
					role: "treeitem",
					"aria-level": node.depth + 1,
					"aria-expanded": unref(branch)(node) ? !!node.expanded : void 0,
					"aria-selected": __props.selectedIds?.includes(node.id) || __props.selected === node.id,
					onKeydown: ($event) => key($event, node),
					style: normalizeStyle(rowStyle(node)),
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
				}, [unref(branch)(node) ? (openBlock(), createBlock(_sfc_main$16, {
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
				])) : (openBlock(), createElementBlock("span", _hoisted_3$2)), node.kind === "file" && _ctx.$slots.file ? renderSlot(_ctx.$slots, "file", { node }, void 0, true, 2) : (openBlock(), createBlock(_sfc_main$16, {
					key: 3,
					class: "file-tree-select",
					"aria-label": title(node),
					title: title(node),
					disabled: __props.busy,
					onClick: ($event) => emit("select", node, $event)
				}, {
					default: withCtx(() => [createVNode(WorkspaceTreePaint_default, {
						row: node,
						caption: title(node),
						subtitle: subtitle(node)
					}, null, 8, [
						"row",
						"caption",
						"subtitle"
					])]),
					_: 2
				}, 1032, [
					"aria-label",
					"title",
					"disabled",
					"onClick"
				]))], 46, _hoisted_2$2);
			}), 128)), !__props.nodes?.length ? (openBlock(), createElementBlock("p", _hoisted_4$2, toDisplayString(unref(t)("Nothing to display")), 1)) : createCommentVNode("", true)], 40, _hoisted_1$8);
		};
	}
}, [["__scopeId", "data-v-802a5967"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/tree.ui.mjs
function describe$6(model, width, height, language) {
	const nodes = [], inner = Math.max(0, width - 16);
	let y = 8;
	if (model.native) {
		nodes.push(node("View", "workspaceTreeNavigationPort", rect(8, y, inner, model.navigationHeight || 0), { view: "navigation" }));
		y += (model.navigationHeight || 0) + 4;
		const controlHeight = metrics(model.style).controlHeight;
		nodes.push(node("Segmented", "workspaceTreeMode", rect(8, y, inner, controlHeight), {
			options: [{
				value: "depot",
				label: translate("Depot", language),
				icon: "database"
			}, {
				value: "workspace",
				label: translate("Workspace", language),
				icon: "desktop"
			}],
			value: model.treeView,
			action: { type: "treeView" }
		}));
		y += controlHeight + 4;
	}
	const viewport = rect(8, y, inner, Math.max(0, height - y - 8));
	nodes.push(node("View", "workspaceDepotTreePort", viewport, {
		view: "depot",
		visible: !model.native || model.treeView === "depot"
	}));
	if (model.native) nodes.push(node("View", "workspaceLocalTreePort", viewport, {
		view: "workspace",
		visible: model.treeView === "workspace"
	}));
	return { nodes };
}
var WorkspaceTreePane_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceTreePane",
	props: {
		nodes: Array,
		busy: Boolean
	},
	emits: ["expand", "select"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 280,
			height: 600
		});
		const scene = computed(() => describe$6({}, viewport.value.width, viewport.value.height, appearance.language));
		const views = computed(() => ({ depot: {
			component: markRaw(FileWorkspaceTree_default),
			props: {
				nodes: props.nodes,
				busy: props.busy,
				canDrag: false,
				label: "Depot tree",
				onExpand: (value) => emit("expand", value),
				onSelect: (value) => emit("select", value)
			}
		} }));
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const bounds = entries.at(-1).contentRect;
				if (bounds.width > 0 && bounds.height > 0) viewport.value = {
					width: bounds.width,
					height: bounds.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "inspection-tree-pane"
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				views: views.value
			}, null, 8, ["scene", "views"])], 512);
		};
	}
}, [["__scopeId", "data-v-a6d14543"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/inspector.ui.mjs
function date(value) {
	if (!value) return "—";
	const current = /* @__PURE__ */ new Date(value / 1e3);
	if (!Number.isFinite(current.getTime())) return "—";
	const pad = (value) => String(value).padStart(2, "0");
	return pad(current.getDate()) + "." + pad(current.getMonth() + 1) + "." + current.getFullYear() + " " + pad(current.getHours()) + ":" + pad(current.getMinutes()) + ":" + pad(current.getSeconds());
}
function size$1(value) {
	return value < 1024 ? value + " B" : value < 1048576 ? (value / 1024).toFixed(1) + " KiB" : (value / 1048576).toFixed(1) + " MiB";
}
function fileType(file) {
	const path = file.path || "";
	return file.file_type || (path.lastIndexOf(".") > path.lastIndexOf("/") ? path.slice(path.lastIndexOf(".") + 1).toUpperCase() : "—");
}
function details(info, history = false) {
	const file = info.file || {}, change = info.change_number ? "#" + info.change_number : "—";
	const bytes = size$1(file.size ?? info.local_size ?? 0);
	if (history) return [
		["Date submitted", date(info.submitted_at)],
		["Changelist", change],
		["Submitted by", info.author || "—"],
		["Type", fileType(Object.assign({}, file, { path: info.path }))],
		["Workspace", info.workspace || "—"],
		["File size", bytes],
		["Action", info.action || "—"]
	];
	return [
		["Workspace location", info.workspace_location || info.local_path || "—"],
		["Depot location", "//" + info.stream + "/" + info.path],
		["Revision", "#" + (file.number || "—") + " · Have #" + (info.have?.number || "—") + " · Head #" + (info.head?.number || "—")],
		["Local modification date", info.local_modified_ns ? date(info.local_modified_ns / 1e3) : "—"],
		["Submitted at", date(info.submitted_at)],
		["File size", bytes],
		["Author", info.author || "—"],
		["Changelist", change],
		["Type", fileType(Object.assign({}, file, { path: info.path }))],
		["SHA-256", file.sha256 || "—"],
		["Integration source", info.provenance ? info.provenance.stream + " · " + info.provenance.change + " · " + info.provenance.version : "—"]
	];
}
function describe$5(model, width, height, language) {
	const tr = (text) => translate(text, language), info = model.info || {}, preview = model.preview || {};
	const margin = 8, inner = Math.max(0, width - 16), bodyWidth = Math.max(0, inner - 16);
	const tabs = [
		{
			id: "details",
			title: "Details"
		},
		model.history ? {
			id: "integrations",
			title: "Integrations"
		} : {
			id: "checkout",
			title: "Checked Out By"
		},
		{
			id: "preview",
			title: "Preview"
		}
	];
	const tabWidth = inner / 3;
	const nodes = [node("Box", "workspaceInspectorBackground", rect(0, 0, width, height), { background: "panelDeep" })];
	for (const [index, tab] of tabs.entries()) nodes.push(button((model.history ? "historyTab_" : "fileInspectorTab_") + tab.id, rect(margin + index * tabWidth, margin, tabWidth, 32), tr(tab.title), "", {
		type: "tab",
		value: tab.id
	}, true, {
		tab: true,
		selected: model.tab === tab.id,
		color: model.tab === tab.id ? "action" : "primaryText",
		weight: model.tab === tab.id ? 600 : 400
	}));
	const body = [];
	let y = 0;
	function message(id, text, color = "secondaryText") {
		const h = Math.max(28, captionHeight(text, bodyWidth) * 1.2);
		body.push(label(id, rect(0, y, bodyWidth, h), text, {
			wrap: true,
			wrapAnywhere: true,
			color
		}));
		y += h + 6;
	}
	if (model.error || !info.path) message("workspaceInspectorNotice", model.error || tr(model.busy ? "Loading" : model.history ? "Select a revision" : "Select a file to inspect"), model.error ? "error" : "secondaryText");
	else if (model.tab === "details") {
		if (model.history) message("workspaceInspectorRevisionPath", "//" + info.stream + "/" + info.path + "#" + (info.file?.number || ""), "primaryText");
		const columns = width < 650 ? 1 : 2, columnWidth = (bodyWidth - (columns - 1) * 20) / columns;
		for (const [index, [title, value]] of details(info, !!model.history).entries()) {
			const x = index % columns * (columnWidth + 20), top = y + Math.floor(index / columns) * 32;
			const caption = Math.min(145, width * .3);
			body.push(label("workspaceInspectorFieldLabel" + index, rect(x, top, caption - 6, 30), tr(title), {
				color: "secondaryText",
				fontRole: "secondary",
				toolTip: tr(title)
			}));
			body.push(node("Field", "workspaceInspectorField" + index, rect(x + caption, top, Math.max(0, columnWidth - caption), 30), {
				text: String(value),
				label: tr(title),
				readOnly: true,
				tableCell: true,
				toolTip: String(value)
			}));
		}
		y += Math.ceil(details(info, !!model.history).length / columns) * 32 + 6;
		body.push(label("workspaceInspectorDescriptionLabel", rect(0, y, bodyWidth, 24), tr("Description"), { color: "secondaryText" }));
		y += 28;
		body.push(node("Area", model.history ? "historyRevisionDescription" : "fileInspectorDescription", rect(0, y, bodyWidth, 85), {
			text: info.description || "",
			readOnly: true,
			label: tr("Description")
		}));
		y += 93;
	} else if (model.tab === "integrations") {
		if (!info.provenance) message("workspaceInspectorNoIntegration", tr("No integration source for this revision"));
		else for (const [title, value] of [
			["Stream", info.provenance.stream],
			["Changelist", info.provenance.change],
			["Revision", info.provenance.version]
		]) message("workspaceInspectorIntegration" + title, tr(title) + ": " + value, "primaryText");
	} else if (model.tab === "checkout") {
		if (!(info.holders || []).length) message("workspaceInspectorNoCheckout", tr("No active checkout"));
		for (const [index, holder] of (info.holders || []).entries()) {
			const text = holder.owner + " · " + holder.workspace + " · #" + (holder.number || holder.change) + " · " + tr(holder.mode === "exclusive" ? "Exclusive checkout" : "Ordinary checkout");
			const h = Math.max(28, captionHeight(text, bodyWidth - 24) * 1.2);
			body.push(node("Icon", "workspaceInspectorCheckoutIcon" + index, rect(0, y, 18, 18), {
				icon: holder.mode === "exclusive" ? "lock" : "lock-open-variant",
				color: "action"
			}));
			body.push(label("workspaceInspectorCheckout" + index, rect(24, y, Math.max(0, bodyWidth - 24), h), text, { wrap: true }));
			y += h + 6;
		}
	} else if (model.tab === "preview") {
		if (!preview.kind || preview.error) message("workspaceInspectorNoPreview", preview.error || tr(model.busy ? "Loading preview…" : "No content available for this file"), preview.error ? "error" : "secondaryText");
		if (preview.kind === "binary" || preview.truncated) message("workspaceInspectorPreviewNotice", (preview.kind === "binary" ? tr("Binary file") : "") + (preview.truncated ? " · " + tr("Preview shows the first 256 KiB") : ""));
		const previewHeight = Math.max(120, height - 100 - y);
		if (!preview.kind || ["text", "binary"].includes(preview.kind)) body.push(node("Area", model.history ? "historyRevisionPreview" : "fileInspectorPreview", rect(0, y, bodyWidth, previewHeight), {
			text: preview.text || "",
			readOnly: true,
			label: tr("File preview")
		}));
		else if (preview.kind === "image") body.push(node("Preview", "workspaceInspectorImage", rect(0, y, bodyWidth, previewHeight), {
			source: preview.image || "",
			round: false,
			outlined: false,
			fit: "contain",
			icon: "file-image"
		}));
		y += previewHeight + 8;
	}
	nodes.push(node("Scroll", "workspaceInspectorBody", rect(margin, 48, inner, Math.max(0, height - 56)), {
		scrollbarId: "workspaceInspectorScrollBar",
		contentHeight: y,
		children: body
	}));
	return { nodes };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/table.ui.mjs
function columns(view, width) {
	const definitions = {
		changelistFiles: [
			["File", 200],
			["In folder", Math.max(250, width - 624)],
			["Resolve status", 130],
			["Type", 120],
			["Action", 150]
		],
		changelistTasks: [
			["Task", 180],
			["Status", 140],
			["Description", Math.max(420, width - 344)]
		],
		history: [
			["Revision", 100],
			["Changelist", 120],
			["Date submitted", 190],
			["Submitted by", 150],
			["Type", 100],
			["Size", 110],
			["Description", Math.max(280, width - 790)]
		],
		streams: [
			["Stream", 260],
			["Stream root", 240],
			["Parent", 160],
			["Type", 120],
			["Description", Math.max(260, width - 780)]
		],
		workspaces: [
			["Workspace", 200],
			["Stream", 180],
			["Owner", 140],
			["Workspace location", Math.max(280, width - 520)]
		],
		tasks: [
			["Task", 180],
			["State", 140],
			["File", Math.max(280, width - 440)],
			["Progress", 120]
		],
		files: [
			["File", Math.max(300, width - 320)],
			["State", 200],
			["File size", 120]
		]
	};
	return (definitions[view] || definitions.files).map(([title, width]) => ({
		title,
		width
	}));
}
function cells(view, row, language = "en") {
	const tr = (text) => translate(text, language);
	if (view === "changelistTasks") return [
		row.code,
		row.status,
		row.description
	];
	if (view === "changelistFiles") {
		const parts = row.path.split("/"), name = parts.pop(), action = row.action || "";
		return [
			name,
			parts.join("/") || "/",
			row.conflict ? tr("Conflict") : row.resolved_sha256 !== void 0 ? tr("Resolved") : "—",
			name.lastIndexOf(".") > 0 ? name.slice(name.lastIndexOf(".") + 1).toUpperCase() : "—",
			tr(["delete", "move/delete"].includes(action) ? "Delete" : action === "move/add" ? "Rename" : action === "baseline" ? "Published" : row.base ? "Edit" : "Add")
		];
	}
	if (view === "history") return [
		"#" + row.number,
		"#" + (row.change_number || "—"),
		date(row.submitted_at),
		row.author || "—",
		fileType(row),
		size$1(row.size || 0),
		row.description || ""
	];
	if (view === "streams") return [
		row.title || row.code,
		"//" + row.depot + "/" + row.code,
		row.parent || "—",
		row.stream_type || "",
		row.description || ""
	];
	if (view === "workspaces") return [
		row.code,
		row.stream || "—",
		row.owner || "—",
		row.local_root || "—"
	];
	if (view === "tasks") return [
		row.task || row.code,
		row.state || "—",
		row.path || row.prefix || "—",
		(row.bytes_done || 0) + " / " + (row.bytes_total || 0)
	];
	return [
		row.path || row.code || "",
		row.state || row.action || "—",
		size$1(row.size || row.bytes_total || 0)
	];
}
function row$2(model, width, language) {
	const data = model.row, view = model.view, values = cells(view, data, language), definitions = columns(view, width), height = view === "streams" ? 34 : 32;
	const children = [];
	let x = 0;
	for (const [index, column] of definitions.entries()) {
		let inset = view.startsWith("changelist") ? 6 : 8;
		if (index === 0 && view.startsWith("changelist")) {
			const badge = view === "changelistTasks" ? {
				icon: "task",
				tone: "action"
			} : badges(data)[0];
			inset = 28;
			children.push(node("Icon", "workspaceTableFileIcon", rect(5, 8, 16, 16), {
				icon: badge.icon,
				color: toneRole(badge.tone)
			}));
		}
		if (index === 0 && view === "history") {
			inset = 32;
			children.push(node("Icon", "workspaceTableHistoryIcon", rect(8, 8, 16, 16), {
				icon: ["delete", "move/delete"].includes(data.action) ? "delete" : data.action === "add" ? "add" : data.action === "move/add" ? "swap-horizontal" : "edit",
				color: data.deleted ? "error" : "action"
			}));
		}
		if (index === 0 && view === "streams") {
			const indent = model.treeMode ? Math.min((data.depth || 0) * 20, 160) : 8;
			if (model.treeMode) children.push(button("streamToggle_" + data.code, rect(indent, 3, 28, 28), translate("Expand or collapse", language), model.expanded ? "chevron-down" : "chevron-right", {
				type: "toggle",
				key: data.code
			}, !!data.children, {
				iconOnly: true,
				iconAction: true
			}));
			const iconX = indent + (model.treeMode ? 31 : 0);
			children.push(node("Icon", "workspaceTableStreamIcon", rect(iconX, 8, 18, 18), {
				icon: "source-branch",
				color: data.stream_type === "release" ? "yellow" : "action"
			}));
			inset = iconX + 22;
		}
		children.push(label("workspaceTableCell" + index, rect(x + inset, 0, Math.max(0, column.width - inset - 8), height), String(values[index] ?? ""), {
			elideMiddle: index === 0,
			fontRole: "secondary",
			toolTip: String(values[index] ?? "")
		}));
		x += column.width;
	}
	return { nodes: [node("Box", "workspaceTableRow", rect(0, 0, x, height), {
		background: model.selected ? "selected" : model.hovered ? "rowHover" : "transparent",
		children
	})] };
}
//#endregion
//#region src/features/fileWorkspace/inspection/WorkspaceTable.vue
var _hoisted_1$7 = ["aria-label"];
var _hoisted_2$1 = [
	"aria-selected",
	"onClick",
	"onKeydown"
];
var _hoisted_3$1 = ["colspan"];
var _hoisted_4$1 = {
	key: 0,
	class: "muted"
};
var WorkspaceTable_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceTable",
	props: {
		view: String,
		rows: Array,
		focus: Object
	},
	emits: ["select"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(800);
		const columns$1 = computed(() => columns(props.view, width.value));
		const tableWidth = computed(() => columns$1.value.reduce((sum, column) => sum + column.width, 0));
		const selected = (row) => props.view === "files" ? !!props.focus && props.focus.path === row.path : !!props.focus && props.focus.code === row.code;
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => width.value = entries.at(-1).contentRect.width - 16);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "workspace-table-scroll"
			}, [createBaseVNode("table", {
				"aria-label": unref(t)(__props.view === "history" ? "Revisions" : __props.view === "streams" ? "Streams" : __props.view === "workspaces" ? "Workspaces" : __props.view === "tasks" ? "Transfers" : "Files"),
				style: normalizeStyle({ width: tableWidth.value + "px" })
			}, [
				createBaseVNode("colgroup", null, [(openBlock(true), createElementBlock(Fragment, null, renderList(columns$1.value, (column, index) => {
					return openBlock(), createElementBlock("col", {
						key: index,
						style: normalizeStyle({ width: column.width + "px" })
					}, null, 4);
				}), 128))]),
				createBaseVNode("thead", null, [createBaseVNode("tr", null, [(openBlock(true), createElementBlock(Fragment, null, renderList(columns$1.value, (column, index) => {
					return openBlock(), createElementBlock("th", { key: index }, toDisplayString(unref(t)(column.title)), 1);
				}), 128))])]),
				createBaseVNode("tbody", null, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.rows, (row, index) => {
					return openBlock(), createElementBlock("tr", {
						key: row.path || row.code || row.task || index,
						tabindex: "0",
						"aria-selected": selected(row),
						onClick: ($event) => emit("select", row),
						onKeydown: [withKeys(($event) => emit("select", row), ["enter"]), withKeys(withModifiers(($event) => emit("select", row), ["prevent"]), ["space"])]
					}, [createBaseVNode("td", { colspan: columns$1.value.length }, [createVNode(_sfc_main$17, {
						interactive: false,
						scene: row$2({
							view: __props.view,
							row,
							selected: selected(row)
						}, width.value, unref(appearance).language)
					}, null, 8, ["scene"])], 8, _hoisted_3$1)], 40, _hoisted_2$1);
				}), 128))])
			], 12, _hoisted_1$7), !__props.rows.length ? (openBlock(), createElementBlock("p", _hoisted_4$1, toDisplayString(unref(t)("No permitted records on this page")), 1)) : createCommentVNode("", true)], 512);
		};
	}
}, [["__scopeId", "data-v-116f608d"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/graph.ui.mjs
function layout(nodes) {
	const levels = {}, slots = {}, result = {};
	let pending = nodes.slice();
	for (let pass = 0; pending.length && pass <= nodes.length; pass++) {
		const next = [];
		for (const row of pending) {
			if (row.parent && nodes.some((node) => node.code === row.parent) && levels[row.parent] === void 0) {
				next.push(row);
				continue;
			}
			levels[row.code] = levels[row.parent] === void 0 ? 0 : levels[row.parent] + 1;
		}
		if (next.length === pending.length) {
			for (const row of next) levels[row.code] = 0;
			break;
		}
		pending = next;
	}
	for (const row of nodes) {
		const level = levels[row.code] || 0, slot = slots[level] || 0;
		slots[level] = slot + 1;
		result[row.code] = {
			x: 24 + level * 204,
			y: 24 + slot * 88
		};
	}
	return result;
}
function paint(context, nodes, edges, zoom, color) {
	const positions = layout(nodes);
	context.save();
	context.scale(zoom, zoom);
	for (const edge of edges) {
		const a = positions[edge.source], b = positions[edge.target];
		if (!a || !b) continue;
		const x = a.x + 172, y = a.y + 32, targetX = b.x, targetY = b.y + 32;
		context.strokeStyle = color(edge.kind === "merge" ? "green" : "action");
		context.lineWidth = 1.5;
		context.beginPath();
		context.moveTo(x, y);
		context.bezierCurveTo(x + 40, y, targetX - 40, targetY, targetX, targetY);
		context.stroke();
		context.beginPath();
		context.moveTo(targetX - 7, targetY - 4);
		context.lineTo(targetX, targetY);
		context.lineTo(targetX - 7, targetY + 4);
		context.stroke();
	}
	context.restore();
}
function describe$4(model, width, height, language) {
	const tr = (text) => translate(text, language), records = model.nodes || [], positions = layout(records), zoom = Math.max(.25, Math.min(2, model.zoom || 1)), inner = Math.max(0, width - 16);
	const tools = [];
	let left = 0;
	if (model.native) {
		tools.push(button("streamGraphNew", rect(0, 0, 28, 28), tr("New stream"), "add", { type: "new" }, !model.busy, {
			iconOnly: true,
			iconAction: true
		}));
		left = 32;
	}
	tools.push(label("streamGraphTitle", rect(left, 0, Math.max(0, inner - left - 160), 28), tr("Stream Graph")));
	tools.push(button("streamGraphZoomOut", rect(inner - 156, 0, 28, 28), tr("Zoom out"), "minus", {
		type: "zoom",
		value: Math.max(.25, zoom - .1)
	}, true, {
		iconOnly: true,
		iconAction: true
	}));
	tools.push(label("streamGraphZoom", rect(inner - 124, 0, 56, 28), Math.round(zoom * 100) + "%", {
		color: "secondaryText",
		align: "center"
	}));
	tools.push(button("streamGraphZoomIn", rect(inner - 64, 0, 28, 28), tr("Zoom in"), "plus", {
		type: "zoom",
		value: Math.min(2, zoom + .1)
	}, true, {
		iconOnly: true,
		iconAction: true
	}));
	tools.push(button("streamGraphRefresh", rect(inner - 28, 0, 28, 28), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy, {
		iconOnly: true,
		iconAction: true
	}));
	const hint = tr(model.native ? "Parent links and submitted integrations. Double-click a stream to edit its settings." : "Parent links and submitted integrations."), hintHeight = Math.max(24, captionHeight(hint, inner) * 1.2), top = 44 + hintHeight;
	const footer = width < 500 ? 78 : 36;
	const contentWidth = Math.max(inner - 16, ...records.map((row) => (positions[row.code].x + 180) * zoom));
	const contentHeight = Math.max(0, height - top - footer - 16, ...records.map((row) => (positions[row.code].y + 84) * zoom));
	const children = [node("View", "streamGraphEdges", rect(0, 0, contentWidth, contentHeight), { view: "streamGraphEdges" })];
	for (const row of records) {
		const point = positions[row.code], chosen = model.selected === row.code;
		children.push(node("Box", "streamGraphNodeSurface_" + row.code, rect(point.x * zoom, point.y * zoom, 172, 64), {
			scale: zoom,
			contextAction: model.native ? {
				type: "menu",
				key: row.code
			} : null,
			children: [node("Action", "streamGraphNode_" + row.code, rect(0, 0, 172, 64), {
				text: row.code,
				role: "option",
				selected: chosen,
				normalColor: "panel",
				selectedColor: "selected",
				radius: 10,
				action: {
					type: "select",
					key: row.code
				},
				doubleAction: model.native ? {
					type: "edit",
					key: row.code
				} : null,
				children: [label("streamGraphNodeTitle", rect(8, 6, 156, 24), row.title || row.code, {
					fontRole: "secondary",
					elideMiddle: true
				}), label("streamGraphNodeDetails", rect(8, 34, 156, 22), (row.stream_type || "") + " · #" + row.revision + " · " + row.depot, {
					color: "secondaryText",
					fontRole: "secondary"
				})]
			})]
		}));
	}
	const nodes = [
		node("Box", "streamGraphBackground", rect(0, 0, width, height), {
			background: "panelDeep",
			radius: 14
		}),
		node("Box", "streamGraphTools", rect(8, 8, inner, 28), { children: tools }),
		label("streamGraphHint", rect(8, 40, inner, hintHeight), hint, {
			color: "secondaryText",
			wrap: true
		}),
		node("Scroll", "streamGraphScroll", rect(8, top, inner, Math.max(0, height - top - footer)), {
			contentWidth,
			contentHeight,
			scrollbarId: "streamGraphScrollBar",
			children: [node("Box", "streamGraphPlane", rect(0, 0, contentWidth, contentHeight), {
				children,
				contextAction: model.native ? {
					type: "menu",
					key: ""
				} : null
			})]
		})
	];
	const selected = records.find((row) => row.code === model.selected);
	nodes.push(label("streamGraphSelection", rect(8, height - footer + 4, Math.max(0, inner - (width < 500 ? 0 : 300)), 28), selected ? selected.code + " · #" + selected.revision : tr("Select a stream"), {
		color: "secondaryText",
		elideMiddle: true
	}));
	const y = height - 36;
	if (model.after) nodes.push(button("streamGraphMore", rect(width < 500 ? 8 : width - 300, y, width < 500 ? (inner - 8) / 2 : 140, 32), tr("Next page"), "chevron-right", { type: "more" }, !model.busy));
	if (model.edgesAfter) nodes.push(button("streamGraphMoreEdges", rect(width < 500 ? 16 + (inner - 8) / 2 : width - 152, y, width < 500 ? (inner - 8) / 2 : 144, 32), tr("Next connections"), "chevron-right", { type: "moreEdges" }, !model.busy));
	return { nodes };
}
//#endregion
//#region src/features/fileWorkspace/inspection/StreamGraphEdges.vue
var _sfc_main$10 = {
	__name: "StreamGraphEdges",
	props: {
		frameNode: Object,
		nodes: Array,
		edges: Array,
		zoom: Number
	},
	setup(__props) {
		const props = __props;
		const canvas = ref(null);
		function paint$1() {
			if (!canvas.value) return;
			const element = canvas.value, ratio = devicePixelRatio || 1;
			element.width = Math.ceil(props.frameNode.width * ratio);
			element.height = Math.ceil(props.frameNode.height * ratio);
			const context = element.getContext("2d");
			context.scale(ratio, ratio);
			paint(context, props.nodes, props.edges, props.zoom, (role) => getComputedStyle(element).getPropertyValue(cssRoles[role]).trim());
		}
		onMounted(paint$1);
		watch(() => [
			props.frameNode,
			props.nodes,
			props.edges,
			props.zoom,
			frameColors.value
		], paint$1, {
			flush: "post",
			deep: true
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("canvas", {
				ref_key: "canvas",
				ref: canvas,
				"aria-hidden": "true",
				style: { "pointer-events": "none" }
			}, null, 512);
		};
	}
};
var StreamGraph_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "StreamGraph",
	props: {
		nodes: Array,
		edges: Array,
		busy: Boolean,
		after: String
	},
	emits: ["refresh", "more"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 800,
			height: 500
		}), zoom = ref(1), selected = ref("");
		const edgeComponent = markRaw(_sfc_main$10);
		const views = computed(() => ({ streamGraphEdges: {
			component: edgeComponent,
			nodeProps: true,
			props: {
				nodes: props.nodes,
				edges: props.edges,
				zoom: zoom.value
			}
		} }));
		const scene = computed(() => describe$4({
			nodes: props.nodes,
			edges: props.edges,
			zoom: zoom.value,
			selected: selected.value,
			busy: props.busy,
			after: props.after
		}, viewport.value.width, viewport.value.height, appearance.language));
		function event(action) {
			if (action.type === "zoom") zoom.value = action.value;
			else if (action.type === "select") selected.value = action.key;
			else if (action.type === "refresh" || action.type === "more") emit(action.type);
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const bounds = entries.at(-1).contentRect;
				if (bounds.width > 0 && bounds.height > 0) viewport.value = {
					width: bounds.width,
					height: bounds.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "workspace-stream-graph"
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				views: views.value,
				onEvent: event
			}, null, 8, ["scene", "views"])], 512);
		};
	}
}, [["__scopeId", "data-v-4ea0c65e"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceInspector.vue
var _sfc_main$7 = {
	components: { WorkspaceInspectorView: /* @__PURE__ */ _plugin_vue_export_helper_default({
		__name: "WorkspaceInspectorView",
		props: {
			info: Object,
			preview: Object,
			tab: String,
			busy: Boolean,
			error: String,
			history: Boolean
		},
		emits: ["tab"],
		setup(__props, { emit: __emit }) {
			const props = __props;
			const emit = __emit;
			const host = ref(null), viewport = ref({
				width: 600,
				height: 220
			});
			const scene = computed(() => describe$5(props, viewport.value.width, viewport.value.height, appearance.language));
			let observer;
			onMounted(() => {
				observer = observeFrameSizes((entries) => {
					const bounds = entries.at(-1).contentRect;
					if (bounds.width > 0 && bounds.height > 0) viewport.value = {
						width: bounds.width,
						height: bounds.height
					};
				});
				observer.observe(host.value);
			});
			onBeforeUnmount(() => observer?.disconnect());
			return (_ctx, _cache) => {
				return openBlock(), createElementBlock("div", {
					ref_key: "host",
					ref: host,
					class: "workspace-inspector-view"
				}, [createVNode(_sfc_main$17, {
					scene: scene.value,
					onEvent: _cache[0] || (_cache[0] = (action) => action.type === "tab" && emit("tab", action.value))
				}, null, 8, ["scene"])], 512);
			};
		}
	}, [["__scopeId", "data-v-55aa9c87"]]) },
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
	computed: { key() {
		return JSON.stringify([
			this.row?.source_path || this.row?.path,
			this.row?.stream || this.stream,
			this.scope,
			this.workspace,
			this.tab
		]);
	} },
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
var _hoisted_1$6 = ["aria-label"];
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_WorkspaceInspectorView = resolveComponent("WorkspaceInspectorView");
	return openBlock(), createElementBlock("section", {
		class: "file-workspace-inspector",
		"aria-label": $options.t("File details")
	}, [createVNode(_component_WorkspaceInspectorView, {
		info: $data.info,
		preview: $data.info?.preview,
		tab: $data.tab,
		busy: $data.busy,
		error: $data.error,
		onTab: _cache[0] || (_cache[0] = ($event) => $data.tab = $event)
	}, null, 8, [
		"info",
		"preview",
		"tab",
		"busy",
		"error"
	])], 8, _hoisted_1$6);
}
var FileWorkspaceInspector_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$7, [["render", _sfc_render$1], ["__scopeId", "data-v-7f445f31"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/log.ui.mjs
function entryText(record) {
	return record.time + " · " + record.operation + " · " + record.message + (record.path ? "\n" + record.path : "");
}
function describe$3(model, width, height, language) {
	const tr = (text) => translate(text, language), buttons = [
		[
			"fileWorkspaceCopyLog",
			"Copy log",
			"copy",
			"copy"
		],
		[
			"fileWorkspaceClearLog",
			"Clear log",
			"delete",
			"clear"
		],
		[
			"fileWorkspaceDebugLog",
			"Debug Log",
			"bug-report",
			"debug"
		],
		[
			"fileWorkspaceHideLog",
			model.native ? "Hide log" : model.expanded ? "Collapse log" : "Expand log",
			model.native ? "close" : model.expanded ? "chevron-down" : "chevron-right",
			"visibility"
		]
	];
	const nodes = [
		node("Box", "workspaceLogBackground", rect(0, 0, width, height), {
			background: "panelDeep",
			radius: 14
		}),
		node("Icon", "workspaceLogIcon", rect(6, 10, 16, 16), {
			icon: "terminal",
			color: "secondaryText"
		}),
		label("workspaceLogTitle", rect(28, 4, Math.max(0, width - 164), 28), tr("Log"), { fontRole: "secondary" })
	];
	for (const [index, [id, title, icon, type]] of buttons.entries()) nodes.push(button(id, rect(Math.max(0, width - 136) + index * 32, 4, 28, 28), tr(title), icon, { type }, true, {
		iconOnly: true,
		iconAction: true
	}));
	nodes.push(node("View", "workspaceLogEntries", rect(4, 36, Math.max(0, width - 8), model.expanded ? Math.max(0, height - 40) : 100), {
		view: "entries",
		visible: !!model.expanded
	}));
	return { nodes };
}
function entry(record, width, height) {
	const color = record.level === "ERROR" ? "error" : record.level === "WARNING" ? "yellow" : "secondaryText";
	return { nodes: [node("Icon", "workspaceLogEntryIcon", rect(0, 0, 16, 16), {
		icon: record.level === "ERROR" ? "error" : record.level === "WARNING" ? "warning" : "info",
		color
	}), node("View", "workspaceLogMessagePort", rect(22, 0, Math.max(0, width - 22), height), {
		view: "message",
		text: entryText(record),
		fontRole: "secondary",
		color: record.level === "ERROR" ? "error" : "primaryText"
	})] };
}
//#endregion
//#region src/features/fileWorkspace/inspection/WorkspaceLogMessage.vue
var _hoisted_1$5 = { class: "workspace-log-message" };
var WorkspaceLogMessage_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceLogMessage",
	props: { frameNode: Object },
	emits: ["measured"],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		const text = ref(null);
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => emit("measured", entries.at(-1).contentRect.height));
			observer.observe(text.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$5, [createBaseVNode("div", {
				ref_key: "text",
				ref: text
			}, toDisplayString(__props.frameNode.text), 513)]);
		};
	}
}, [["__scopeId", "data-v-217d26da"]]);
//#endregion
//#region src/features/fileWorkspace/inspection/WorkspaceLogEntries.vue
var _hoisted_1$4 = ["aria-label"];
var WorkspaceLogEntries_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceLogEntries",
	props: { entries: Array },
	setup(__props) {
		const props = __props;
		const host = ref(null), width = ref(400), heights = ref({});
		const messageComponent = markRaw(WorkspaceLogMessage_default);
		const rowScene = (entry$1) => entry(entry$1, width.value, heights.value[entry$1.id] || 18);
		function views(entry) {
			return { message: {
				component: messageComponent,
				nodeProps: true,
				props: { onMeasured: (value) => {
					if (heights.value[entry.id] === value) return;
					const follow = host.value && host.value.scrollHeight - host.value.clientHeight - host.value.scrollTop < 40;
					heights.value[entry.id] = value;
					if (follow) nextTick(() => {
						if (host.value) host.value.scrollTop = host.value.scrollHeight;
					});
				} }
			} };
		}
		watch(() => props.entries.map((entry) => entry.id), async (ids) => {
			const retained = new Set(ids);
			heights.value = Object.fromEntries(Object.entries(heights.value).filter(([id]) => retained.has(Number(id)) || retained.has(id)));
			await nextTick();
			if (host.value) host.value.scrollTop = host.value.scrollHeight;
		});
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => width.value = Math.max(0, entries.at(-1).contentRect.width - 16));
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "workspace-log-entries",
				role: "log",
				"aria-live": "polite",
				"aria-label": unref(t)("Operation log")
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.entries, (entry) => {
				return openBlock(), createElementBlock("div", {
					key: entry.id,
					class: "workspace-log-row",
					style: normalizeStyle({ height: (heights.value[entry.id] || 18) + "px" })
				}, [createVNode(_sfc_main$17, {
					scene: rowScene(entry),
					views: views(entry)
				}, null, 8, ["scene", "views"])], 4);
			}), 128))], 8, _hoisted_1$4);
		};
	}
}, [["__scopeId", "data-v-176ff6a2"]]);
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceLog.vue
var _hoisted_1$3 = ["aria-label"];
var FileWorkspaceLog_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "FileWorkspaceLog",
	props: { entries: Array },
	emits: [
		"clear",
		"copy",
		"debug"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const expanded = ref(true), host = ref(null), viewport = ref({
			width: 800,
			height: 140
		});
		const entriesComponent = markRaw(WorkspaceLogEntries_default);
		const views = computed(() => ({ entries: {
			component: entriesComponent,
			props: { entries: props.entries }
		} }));
		const scene = computed(() => describe$3({ expanded: expanded.value }, viewport.value.width, viewport.value.height, appearance.language));
		function event(action) {
			if (action.type === "visibility") expanded.value = !expanded.value;
			else if ([
				"clear",
				"copy",
				"debug"
			].includes(action.type)) emit(action.type);
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const bounds = entries.at(-1).contentRect;
				if (bounds.width > 0 && bounds.height > 0) viewport.value = {
					width: bounds.width,
					height: bounds.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "file-operation-log",
				style: normalizeStyle({ height: expanded.value ? "140px" : "36px" }),
				"aria-label": unref(t)("Operation log")
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				views: views.value,
				onEvent: event
			}, null, 8, ["scene", "views"])], 12, _hoisted_1$3);
		};
	}
}, [["__scopeId", "data-v-d4e22bfa"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/depots.ui.mjs
function describe$2(model, width, height, language) {
	const tr = (text) => translate(text, language), narrow = width < 600, available = narrow ? Math.max(0, height - 60) : Math.max(0, width - 16), extent = Math.max(0, Math.min(available - 10, model.extent ?? available * (narrow ? .4 : .55)));
	const list = rect(8, 52, narrow ? width - 16 : extent, narrow ? extent : height - 60);
	const detail = rect(narrow ? 8 : 18 + extent, narrow ? 62 + extent : 52, narrow ? width - 16 : width - 26 - extent, narrow ? height - 70 - extent : height - 60), inner = Math.max(0, detail.width - 16);
	const children = [], draft = model.draft || {}, editing = draft.creating !== void 0, selected = model.selected || {};
	let y = 0;
	function text(id, value, heading = false) {
		const h = Math.max(heading ? 28 : 24, captionHeight(value, inner) * 1.2);
		children.push(label(id, rect(0, y, inner, h), value, {
			wrap: true,
			fontRole: heading ? "title" : "body",
			color: heading ? "primaryText" : "secondaryText",
			weight: heading ? 600 : 400
		}));
		y += h + 8;
	}
	function actions(items) {
		const count = inner < 420 ? 1 : 2, w = (inner - (count - 1) * 8) / count;
		for (const [index, item] of items.entries()) children.push(button(item.id, rect(index % count * (w + 8), y + Math.floor(index / count) * 46, w, 38), tr(item.text), item.icon || "", { type: item.type }, item.enabled !== false));
		y += Math.ceil(items.length / count) * 46;
	}
	if (model.notice) text("workspaceDepotNotice", model.notice);
	if (editing) {
		text("workspaceDepotEditTitle", tr(draft.creating ? "New depot" : "Edit depot"), true);
		for (const [key, title, id] of [[
			"code",
			"Depot code",
			"depotEditorCode"
		], [
			"title",
			"Name",
			"depotEditorName"
		]]) {
			text(id + "Label", tr(title));
			children.push(node("Field", id, rect(0, y, inner, 38), {
				text: draft[key] || "",
				label: tr(title),
				readOnly: key === "code" && !draft.creating,
				enabled: !model.busy,
				action: {
					type: "field",
					key
				}
			}));
			y += 46;
		}
		text("workspaceDepotRepositoryLabel", tr("Repository"));
		const options = [{
			value: "",
			label: tr("Project storage")
		}].concat((model.repositories || []).map((value) => ({
			value,
			label: value
		})));
		if (draft.repository && !options.some((row) => row.value === draft.repository)) options.push({
			value: draft.repository,
			label: draft.repository
		});
		children.push(node("Choice", "workspaceDepotRepository", rect(0, y, inner, 38), {
			label: tr("Repository"),
			options,
			value: draft.repository || "",
			enabled: !model.busy,
			action: {
				type: "field",
				key: "repository"
			}
		}));
		y += 46;
		text("workspaceDepotRepositoryHelp", tr("Repository changes apply to new uploads. Existing file contents stay in their original storage."));
		text("workspaceDepotAccessHelp", tr("Depot paths are case-sensitive. Access is configured in Administration → Rules using file_depot."));
		actions([
			{
				id: "workspaceDepotReset",
				text: "Reset",
				icon: "undo",
				type: "reset",
				enabled: !model.busy
			},
			{
				id: "workspaceDepotCancel",
				text: "Cancel",
				icon: "close",
				type: "cancel",
				enabled: !model.busy
			},
			{
				id: "workspaceDepotSave",
				text: draft.creating ? "Create" : "Save",
				icon: "content-save",
				type: "save",
				enabled: !model.busy && !!String(draft.code || "").trim()
			}
		]);
	} else {
		text("workspaceDepotSelectedTitle", selected.code || tr("Select a depot"), true);
		if (selected.code) text("workspaceDepotDetails", (selected.title || "") + "\n" + tr("Repository") + ": " + (selected.storage?.repository || tr("Project storage")) + "\n" + tr("Revision") + ": " + selected.revision + "\n" + tr("Case-sensitive depot paths"));
		if (model.administrator) actions([{
			id: "workspaceDepotNew",
			text: "New depot",
			icon: "add",
			type: "new",
			enabled: !model.busy
		}, {
			id: "workspaceDepotEdit",
			text: "Edit depot",
			icon: "edit",
			type: "edit",
			enabled: !model.busy && !!selected.code
		}]);
	}
	return { nodes: [
		node("Box", "workspaceDepotBackground", rect(0, 0, width, height), {
			background: "panelDeep",
			radius: 14
		}),
		label("workspaceDepotTitle", rect(8, 8, Math.max(0, width - 220), 36), tr("Depots"), {
			fontRole: "title",
			weight: 600
		}),
		button("workspaceDepotRefresh", rect(Math.max(8, width - 208), 8, 96, 36), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy),
		button("workspaceDepotMore", rect(Math.max(8, width - 104), 8, 96, 36), tr("Next page"), "chevron-right", { type: "more" }, !model.busy && !!model.after),
		node("List", "workspaceDepotList", list, {
			source: "depots",
			keyField: "id",
			fields: ["id", "node"],
			rowHeight: 62,
			rowGap: 4,
			label: tr("Depots"),
			scrollbarId: "workspaceDepotListScrollBar"
		}),
		node("Splitter", "workspaceDepotSplitter", rect(narrow ? 8 : extent + 8, narrow ? extent + 52 : 52, narrow ? width - 16 : 10, narrow ? 10 : height - 60), {
			horizontal: narrow,
			value: extent,
			min: 0,
			max: Math.max(0, available - 10),
			text: tr("Depots"),
			action: { type: "split" }
		}),
		node("Scroll", "workspaceDepotDetails", detail, {
			contentHeight: y,
			scrollbarId: "workspaceDepotDetailsScrollBar",
			children
		})
	] };
}
function row$1(model, record, width, language) {
	const tr = (text) => translate(text, language), data = record.node;
	return { nodes: [node("Action", "workspaceDepot_" + record.id, rect(0, 0, width, 58), {
		text: data.code,
		role: "option",
		selected: model.selected?.code === data.code,
		selectedColor: "selected",
		normalColor: "transparent",
		action: {
			type: "select",
			key: record.id
		},
		children: [
			node("Icon", "workspaceDepotIcon", rect(10, 20, 18, 18), {
				icon: "database",
				color: "action"
			}),
			label("workspaceDepotCode", rect(36, 4, Math.max(0, width - 44), 24), data.code, { elideMiddle: true }),
			label("workspaceDepotSubtitle", rect(36, 30, Math.max(0, width - 44), 20), (data.title || data.code) + " · " + (data.storage?.repository || tr("Project storage")), {
				fontRole: "secondary",
				color: "secondaryText"
			})
		]
	})] };
}
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceDepots.vue
var _hoisted_1$2 = ["aria-label"];
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
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 800,
			height: 600
		}), desktopExtent = ref(null), mobileExtent = ref(null);
		const model = computed(() => ({
			...props,
			extent: viewport.value.width < 600 ? mobileExtent.value : desktopExtent.value
		}));
		const rows = computed(() => props.rows.map((node) => ({
			id: node.id ?? node.code,
			node
		})));
		const scene = computed(() => describe$2(model.value, viewport.value.width, viewport.value.height, appearance.language));
		const describeRow = (list, record) => row$1(model.value, record, list.width - 16, appearance.language);
		function event(action) {
			if (action.type === "split") {
				if (viewport.value.width < 600) mobileExtent.value = action.value;
				else desktopExtent.value = action.value;
			} else if (action.type === "select") {
				const row = props.rows.find((row) => (row.id ?? row.code) === action.key);
				if (row) emit("select", row);
			} else if (action.type === "field") emit("change", {
				...props.draft,
				[action.key]: action.value
			});
			else if (action.type === "new") emit("edit", null);
			else if (action.type === "edit") emit("edit", props.selected);
			else if ([
				"save",
				"reset",
				"cancel",
				"refresh",
				"more"
			].includes(action.type)) emit(action.type);
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const bounds = entries.at(-1).contentRect;
				if (bounds.width > 0 && bounds.height > 0) viewport.value = {
					width: bounds.width,
					height: bounds.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "depots-catalog",
				"aria-label": unref(t)("Depots")
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				models: { depots: rows.value },
				"describe-row": describeRow,
				onEvent: event
			}, null, 8, ["scene", "models"])], 8, _hoisted_1$2);
		};
	}
}, [["__scopeId", "data-v-707e8a98"]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/storage.ui.mjs
var fields = [
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
function size(value) {
	for (const unit of [
		"B",
		"KB",
		"MB",
		"GB",
		"TB"
	]) {
		if (value < 1024 || unit === "TB") return value.toFixed(unit === "B" ? 0 : 1) + " " + unit;
		value /= 1024;
	}
}
function describe$1(model, width, height, language) {
	const tr = (text) => translate(text, language), status = model.status || {}, policy = model.draft?.policy, gc = status.gc || {}, active = ["queued", "running"].includes(gc.state);
	const inner = Math.max(0, Math.min(660, width - 32)), body = [];
	let y = 0;
	function text(id, value, heading = false, color = "secondaryText") {
		const h = Math.max(heading ? 28 : 22, captionHeight(value, inner) * 1.2);
		body.push(label(id, rect(0, y, inner, h), value, {
			wrap: true,
			fontRole: heading ? "title" : "body",
			weight: heading ? 600 : 400,
			color: heading ? "primaryText" : color
		}));
		y += h + 8;
	}
	function actions(items) {
		const columns = inner < 460 ? 1 : 2, w = (inner - (columns - 1) * 8) / columns;
		for (const [index, item] of items.entries()) body.push(button(item.id, rect(index % columns * (w + 8), y + Math.floor(index / columns) * 46, w, 38), tr(item.text), item.icon || "", item.action, item.enabled !== false));
		y += Math.ceil(items.length / columns) * 46;
	}
	text("workspaceStorageTitle", tr("Storage administration"), true);
	text("workspaceStorageUsage", size(status.allocated_bytes || 0) + " · " + (status.allocated_files || 0) + " " + tr("files") + " · " + tr(status.indexed ? "Storage index complete" : "Storage index incomplete"));
	const top = [{
		id: "workspaceStorageRefresh",
		text: "Refresh",
		icon: "refresh",
		action: {
			type: "action",
			operation: "storage_status"
		},
		enabled: !model.busy
	}];
	if (!status.initialized) top.push({
		id: "workspaceStorageInitialize",
		text: "Initialize storage",
		action: {
			type: "action",
			operation: "storage_upgrade"
		},
		enabled: !model.busy
	});
	if (status.initialized && !status.indexed) top.push({
		id: "workspaceStorageIndex",
		text: "Continue storage index",
		action: {
			type: "action",
			operation: "storage_index"
		},
		enabled: !model.busy
	});
	if (model.indexing && model.busy) top.push({
		id: "workspaceStorageStop",
		text: "Stop waiting",
		icon: "close",
		action: { type: "stop" }
	});
	actions(top);
	if (!status.indexed) text("workspaceStorageIndexNotice", tr("Finish indexing before editing the policy or running GC. Indexing can be stopped and continued.") + (status.index_table === void 0 ? "" : "\n" + tr("Table") + ": " + status.index_table + " · " + (status.index_after || "")));
	if (model.notice) text("workspaceStorageNotice", model.notice, false, "error");
	if (policy) {
		for (const [index, [key, title, hint]] of fields.entries()) {
			if (index === 0 || index === 3) text("workspaceStorageSection" + index, tr(index === 0 ? "Quotas" : "Retention and cleanup"), true);
			text("workspaceStorageFieldLabel" + index, tr(title));
			body.push(node("Field", "storagePolicy_" + key, rect(0, y, inner, 38), {
				text: String(policy[key] ?? ""),
				label: tr(title),
				inputMode: "numeric",
				enabled: !model.busy && !!status.indexed,
				action: {
					type: "field",
					key
				}
			}));
			y += 46;
			text("workspaceStorageFieldHint" + index, tr(hint));
		}
		actions([{
			id: "workspaceStorageReset",
			text: "Reset",
			icon: "undo",
			action: { type: "reset" },
			enabled: !model.busy
		}, {
			id: "workspaceStorageSave",
			text: "Save storage policy",
			icon: "content-save",
			action: { type: "save" },
			enabled: !model.busy && !!status.indexed
		}]);
	}
	text("workspaceStorageGcTitle", tr("Garbage collection"), true);
	text("workspaceStorageGcHelp", tr("Dry run counts unused objects without deleting them. Safe GC expires retained records and quarantines unused contents according to the saved policy."));
	if (!model.filesService) text("workspaceStorageGcService", tr("Enable the files service on the server to process GC tasks."));
	const canGc = !model.busy && !!status.indexed && !!model.filesService && !active;
	const gcActions = [{
		id: "workspaceStorageDryRun",
		text: "GC dry run",
		enabled: canGc,
		action: {
			type: "action",
			operation: "gc_begin",
			dry: true
		}
	}, {
		id: "workspaceStorageGc",
		text: "Run safe GC",
		enabled: canGc,
		action: { type: "confirmGc" }
	}];
	if (active) gcActions.push({
		id: "workspaceStorageGcCancel",
		text: "Cancel GC",
		icon: "close",
		enabled: !model.busy,
		action: {
			type: "action",
			operation: "gc_cancel"
		}
	});
	actions(gcActions);
	if (gc.code) text("workspaceStorageGcStatus", gc.code + " · " + tr(gc.state || "") + " · " + (gc.phase || "") + " · " + tr(gc.dry_run ? "GC dry run" : "Run safe GC") + "\n" + tr("Objects scanned") + ": " + (gc.objects_done || 0) + " · " + tr("Candidates") + ": " + (gc.candidates || 0) + " · " + size(gc.candidate_bytes || 0) + "\n" + tr("Expired records") + ": " + (gc.expired || 0) + " · " + tr("Quarantined") + ": " + (gc.quarantined || 0) + " · " + tr("Purged") + ": " + (gc.purged || 0));
	if (gc.error) text("workspaceStorageGcError", gc.error, false, "error");
	if (gc.state === "error") text("workspaceStorageGcRecovery", tr("GC stopped. After fixing the cause, start a new dry run or safe GC."));
	return { nodes: [node("Box", "workspaceStorageBackground", rect(0, 0, width, height), {
		background: "panelDeep",
		radius: 14
	}), node("Scroll", "workspaceStorageScroll", rect(8, 8, Math.max(0, width - 16), Math.max(0, height - 16)), {
		scrollbarId: "workspaceStorageScrollBar",
		contentHeight: y + 8,
		children: body
	})] };
}
function confirm(model, width, height, language) {
	return describe$7({
		message: translate("Run safe GC using the configured retention policy?", language),
		accept: "Run safe GC",
		busy: !!model.busy
	}, width, height, language);
}
//#endregion
//#region src/features/fileWorkspace/FileWorkspaceStorage.vue
var _hoisted_1$1 = ["aria-label"];
var _sfc_main$2 = {
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
		const props = __props;
		const emit = __emit;
		const host = ref(null), dialog = ref(null), confirmHost = ref(null), viewport = ref({
			width: 660,
			height: 500
		}), confirmSize = ref({
			width: 420,
			height: 200
		});
		const scene = computed(() => describe$1(props, viewport.value.width, viewport.value.height, appearance.language));
		const canGc = computed(() => !props.busy && !!props.status?.indexed && props.filesService && !["queued", "running"].includes(props.status?.gc?.state));
		const confirmation = computed(() => confirm({ busy: !canGc.value }, confirmSize.value.width, confirmSize.value.height, appearance.language));
		function event(action) {
			if (action.type === "field") emit("change", {
				...props.draft,
				policy: {
					...props.draft.policy,
					[action.key]: action.value
				}
			});
			else if (action.type === "action") emit("action", action.operation, action.dry);
			else if ([
				"reset",
				"save",
				"stop"
			].includes(action.type)) emit(action.type);
			else if (action.type === "confirmGc" && canGc.value) dialog.value.show(host.value);
		}
		function confirm$1(action) {
			if (action.type === "reject") dialog.value.close();
			else if (action.type === "accept" && canGc.value) {
				dialog.value.close();
				emit("action", "gc_begin", false);
			}
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				for (const entry of entries) {
					const bounds = entry.contentRect;
					if (bounds.width > 0 && bounds.height > 0) {
						const value = {
							width: bounds.width,
							height: bounds.height
						};
						if (entry.target === host.value) viewport.value = value;
						else confirmSize.value = value;
					}
				}
			});
			observer.observe(host.value);
			observer.observe(confirmHost.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock(Fragment, null, [createBaseVNode("section", {
				ref_key: "host",
				ref: host,
				class: "storage-administration",
				"aria-label": unref(t)("Storage administration")
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				onEvent: event
			}, null, 8, ["scene"])], 8, _hoisted_1$1), createVNode(_sfc_main$23, {
				ref_key: "dialog",
				ref: dialog,
				title: "Run safe GC",
				class: "workspace-gc-confirmation"
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "confirmHost",
					ref: confirmHost,
					class: "workspace-gc-body"
				}, [createVNode(_sfc_main$17, {
					scene: confirmation.value,
					onEvent: confirm$1
				}, null, 8, ["scene"])], 512)]),
				_: 1
			}, 512)], 64);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/files/workspace/catalog.ui.mjs
function workspaceActions(model, language) {
	const tr = (text) => translate(text, language);
	return [
		{
			id: "workspaceCatalogSwitch",
			text: tr("Switch workspace"),
			icon: "desktop",
			type: "switch",
			enabled: !!model.selected?.code && !model.busy
		},
		{
			id: "workspaceCatalogEdit",
			text: tr("Edit workspace"),
			icon: "edit",
			type: "edit",
			enabled: !!model.selected?.code && model.selected.code === model.workspace && !model.busy
		},
		{
			id: "workspaceCatalogSetup",
			text: tr("Workspace setup"),
			icon: "add",
			type: "setup",
			enabled: !model.busy
		}
	];
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language), narrow = width < 600;
	const actions = workspaceActions(model, language), buttons = actionLayout(actions, Math.max(0, width - 16), model.buttonWidths || []);
	const footer = model.native && model.source === "workspaces" ? buttons.height + 4 : 0;
	const available = Math.max(0, (narrow ? height - 104 - footer : width - 16) - 10);
	const extent = Math.max(0, Math.min(available, model.extent ?? available * (narrow ? .6 : .55)));
	const body = Math.max(0, height - 60 - footer);
	const list = rect(8, 52, narrow ? width - 16 : extent, narrow ? extent : body);
	const detail = rect(narrow ? 8 : 18 + extent, narrow ? 62 + extent : 52, narrow ? width - 16 : width - 26 - extent, narrow ? body - extent - 10 : body);
	const nodes = [
		label("workspaceCatalogTitle", rect(8, 8, Math.max(0, width - 88), 36), tr("Server metadata")),
		button("workspaceCatalogRefresh", rect(Math.max(8, width - 76), 12, 28, 28), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy, {
			iconOnly: true,
			iconAction: true
		}),
		button("workspaceCatalogMore", rect(Math.max(40, width - 40), 12, 28, 28), tr("Next page"), "chevron-right", { type: "more" }, !model.busy, {
			iconOnly: true,
			iconAction: true,
			visible: !!model.after
		}),
		node("List", "workspaceCatalogList", list, {
			source: "catalog",
			keyField: "id",
			fields: ["id", "node"],
			rowHeight: 62,
			rowGap: 4,
			label: tr("Server metadata"),
			scrollbarId: "workspaceCatalogScrollBar"
		}),
		node("Splitter", "workspaceCatalogSplitter", rect(narrow ? 8 : extent + 8, narrow ? extent + 52 : 52, narrow ? width - 16 : 10, narrow ? 10 : body), {
			horizontal: narrow,
			value: extent,
			min: 0,
			max: available,
			text: tr("Server metadata"),
			action: { type: "split" }
		}),
		node("Area", "workspaceCatalogRecord", detail, {
			text: JSON.stringify(model.selected || {}, null, 2),
			readOnly: true,
			label: tr("Selected server record")
		})
	];
	if (!model.count) nodes.push(label("workspaceCatalogEmpty", rect(list.x, list.y, list.width, Math.min(80, list.height)), tr("No permitted records on this page"), {
		wrap: true,
		color: "secondaryText"
	}));
	if (footer) for (const [index, action] of actions.entries()) nodes.push(button(action.id, rect(8 + buttons.positions[index].x, height - footer + buttons.positions[index].y, buttons.positions[index].width, buttons.positions[index].height), action.text, action.icon, { type: action.type }, action.enabled));
	return { nodes };
}
function row(model, record, width, language) {
	const tr = (text) => translate(text, language), data = record.node;
	const subtitle = [
		data.depot,
		data.stream,
		data.owner,
		data.local_root,
		data.parent ? tr("Parent: {parent}").replace("{parent}", data.parent) : ""
	].filter(Boolean).join(" · ");
	return { nodes: [node("Action", "workspaceCatalog_" + record.id, rect(0, 0, width, 58), {
		text: data.code,
		role: "option",
		selected: model.selected?.code === data.code,
		selectedColor: "selected",
		normalColor: "transparent",
		action: {
			type: "select",
			key: record.id
		},
		children: [
			node("Icon", "workspaceCatalogIcon", rect(10, 20, 18, 18), {
				icon: model.source === "workspaces" ? "desktop" : "source-branch",
				color: "action"
			}),
			label("workspaceCatalogCode", rect(36, 4, Math.max(0, width - 44), 24), data.code, { elideMiddle: true }),
			label("workspaceCatalogSubtitle", rect(36, 30, Math.max(0, width - 44), 20), subtitle, {
				fontRole: "secondary",
				color: "secondaryText"
			})
		]
	})] };
}
var WorkspaceCatalog_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "WorkspaceCatalog",
	props: {
		rows: Array,
		selected: Object,
		busy: Boolean,
		after: String,
		source: String
	},
	emits: [
		"select",
		"refresh",
		"more"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 800,
			height: 600
		}), desktopExtent = ref(null), mobileExtent = ref(null);
		const model = computed(() => ({
			...props,
			count: props.rows.length,
			extent: viewport.value.width < 600 ? mobileExtent.value : desktopExtent.value
		}));
		const records = computed(() => props.rows.map((node) => ({
			id: node.id ?? node.code,
			node
		})));
		const scene = computed(() => describe(model.value, viewport.value.width, viewport.value.height, appearance.language));
		const describeRow = (list, record) => row(model.value, record, list.width - 16, appearance.language);
		function event(action) {
			if (action.type === "split") {
				if (viewport.value.width < 600) mobileExtent.value = action.value;
				else desktopExtent.value = action.value;
			} else if (action.type === "select") {
				const row = props.rows.find((row) => (row.id ?? row.code) === action.key);
				if (row) emit("select", row);
			} else if (["refresh", "more"].includes(action.type)) emit(action.type);
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const bounds = entries.at(-1).contentRect;
				if (bounds.width > 0 && bounds.height > 0) viewport.value = {
					width: bounds.width,
					height: bounds.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "workspace-catalog"
			}, [createVNode(_sfc_main$17, {
				scene: scene.value,
				models: { catalog: records.value },
				"describe-row": describeRow,
				onEvent: event
			}, null, 8, ["scene", "models"])], 512);
		};
	}
}, [["__scopeId", "data-v-02dc8e4d"]]);
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
		AppButton: _sfc_main$16,
		AppSelect: _sfc_main$19,
		AppTextField: _sfc_main$20,
		AppSplitter: _sfc_main$21,
		WorkspaceToolbar: WorkspaceToolbar_default,
		WorkspaceTreePane: WorkspaceTreePane_default,
		FileWorkspaceTree: FileWorkspaceTree_default,
		WorkspaceTable: WorkspaceTable_default,
		StreamGraph: StreamGraph_default,
		FileWorkspaceInspector: FileWorkspaceInspector_default,
		FileWorkspaceLog: FileWorkspaceLog_default,
		FileWorkspaceDepots: FileWorkspaceDepots_default,
		FileWorkspaceStorage: _sfc_main$2,
		WorkspaceCatalog: WorkspaceCatalog_default
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
var _hoisted_8 = { key: 6 };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_WorkspaceTreePane = resolveComponent("WorkspaceTreePane");
	const _component_AppSplitter = resolveComponent("AppSplitter");
	const _component_WorkspaceToolbar = resolveComponent("WorkspaceToolbar");
	const _component_FileWorkspaceTree = resolveComponent("FileWorkspaceTree");
	const _component_FileWorkspaceDepots = resolveComponent("FileWorkspaceDepots");
	const _component_FileWorkspaceStorage = resolveComponent("FileWorkspaceStorage");
	const _component_WorkspaceCatalog = resolveComponent("WorkspaceCatalog");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_AppTextField = resolveComponent("AppTextField");
	const _component_StreamGraph = resolveComponent("StreamGraph");
	const _component_WorkspaceTable = resolveComponent("WorkspaceTable");
	const _component_FileWorkspaceInspector = resolveComponent("FileWorkspaceInspector");
	const _component_FileWorkspaceLog = resolveComponent("FileWorkspaceLog");
	return openBlock(), createElementBlock("section", {
		class: "file-workspace",
		"aria-busy": $data.busy,
		"aria-label": $options.t("File project inspection")
	}, [
		createBaseVNode("header", _hoisted_2, [
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
			createBaseVNode("nav", { style: normalizeStyle({ width: $data.width + "px" }) }, [createVNode(_component_WorkspaceTreePane, {
				nodes: $data.tree,
				busy: $data.busy,
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
				createVNode(_component_WorkspaceToolbar, {
					tabs: $data.tabs,
					selected: $data.activeTabId,
					presets: $options.viewPresets,
					onOpen: $options.openView,
					onSelect: _cache[2] || (_cache[2] = ($event) => $options.openView($options.viewPresets.find((view) => view.id === $event))),
					onClose: $options.closeTab,
					onReorder: _cache[3] || (_cache[3] = ($event) => {
						$data.tabs = $event;
						$options.remember();
					})
				}, null, 8, [
					"tabs",
					"selected",
					"presets",
					"onOpen",
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
				])) : $data.activeTabId === "workspaces" ? (openBlock(), createBlock(_component_WorkspaceCatalog, {
					key: 4,
					rows: $data.rows,
					selected: $data.focus,
					busy: $data.busy,
					after: $data.after,
					source: "workspaces",
					onSelect: _cache[8] || (_cache[8] = ($event) => $data.focus = $event),
					onRefresh: $options.refresh,
					onMore: _cache[9] || (_cache[9] = ($event) => $options.run((signal) => $options.load(signal, true)))
				}, null, 8, [
					"rows",
					"selected",
					"busy",
					"after",
					"onRefresh"
				])) : (openBlock(), createElementBlock(Fragment, { key: 5 }, [$data.activeTabId === "files" ? (openBlock(), createElementBlock("div", _hoisted_7, [
					createVNode(_component_AppSelect, {
						modelValue: $data.stream,
						"onUpdate:modelValue": [_cache[10] || (_cache[10] = ($event) => $data.stream = $event), $options.refresh],
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
						"onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => $data.prefix = $event),
						label: "Path prefix",
						onKeydown: withKeys($options.refresh, ["enter"])
					}, null, 8, ["modelValue", "onKeydown"]),
					createVNode(_component_AppButton, {
						label: "Filter",
						icon: "filter",
						onClick: $options.refresh
					}, null, 8, ["onClick"])
				])) : createCommentVNode("", true), $data.activeTabId === "stream_graph" ? (openBlock(), createBlock(_component_StreamGraph, {
					key: 1,
					nodes: $data.rows,
					edges: $data.edges,
					busy: $data.busy,
					after: $data.after,
					onRefresh: $options.refresh,
					onMore: _cache[12] || (_cache[12] = ($event) => $options.run((signal) => $options.load(signal, true)))
				}, null, 8, [
					"nodes",
					"edges",
					"busy",
					"after",
					"onRefresh"
				])) : (openBlock(), createBlock(_component_WorkspaceTable, {
					key: 2,
					view: $data.activeTabId,
					rows: $data.rows,
					focus: $data.focus,
					onSelect: _cache[13] || (_cache[13] = ($event) => $data.activeTabId === "files" && $options.selectFile($event))
				}, null, 8, [
					"view",
					"rows",
					"focus"
				]))], 64)),
				![
					"depots",
					"storage",
					"stream_graph",
					"workspaces"
				].includes($data.activeTabId) ? (openBlock(), createElementBlock("footer", _hoisted_8, [$data.after ? (openBlock(), createBlock(_component_AppButton, {
					key: 0,
					label: "Next page",
					icon: "next",
					disabled: $data.busy,
					onClick: _cache[14] || (_cache[14] = ($event) => $options.run((signal) => $options.load(signal, true)))
				}, null, 8, ["disabled"])) : createCommentVNode("", true), createVNode(_component_AppButton, {
					label: "Copy depot path",
					icon: "copy",
					disabled: !$data.focus,
					onClick: $options.copyPath
				}, null, 8, ["disabled", "onClick"])])) : createCommentVNode("", true),
				![
					"depots",
					"storage",
					"stream_graph",
					"workspaces"
				].includes($data.activeTabId) ? (openBlock(), createBlock(_component_FileWorkspaceInspector, {
					key: 7,
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
			onClear: _cache[15] || (_cache[15] = ($event) => $data.operationLog = []),
			onCopy: $options.copyLog,
			onDebug: _cache[16] || (_cache[16] = ($event) => _ctx.$emit("debug"))
		}, null, 8, ["entries", "onCopy"])
	], 8, _hoisted_1);
}
var FileWorkspaceInspection_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render], ["__scopeId", "data-v-a92b84c7"]]);
//#endregion
export { FileWorkspaceInspection_default as default };

//# sourceMappingURL=FileWorkspaceInspection.js.map
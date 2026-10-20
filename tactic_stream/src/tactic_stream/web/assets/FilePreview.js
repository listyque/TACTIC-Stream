import { F as resolveComponent, G as withCtx, I as resolveDirective, K as withDirectives, L as resolveDynamicComponent, M as openBlock, N as renderList, _ as createElementBlock, b as createVNode, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, rt as toDisplayString, u as Fragment, y as createTextVNode } from "./vue.js";
import { at as _plugin_vue_export_helper_default, c as _sfc_main$2, f as _sfc_main$3, k as t, o as mobile } from "./index.js";
import { k as _sfc_main$4, w as ItemPreview_default } from "./CodeBlock.js";
import { r as prettySize } from "./file_values.js";
import "./files.js";
import { t as downloadBlob } from "./files2.js";
//#region src/features/objects/FilePreviewContent.vue
var _sfc_main$1 = {
	components: {
		AppButton: _sfc_main$2,
		AppMenu: _sfc_main$4,
		AppIcon: _sfc_main$3,
		ItemPreview: ItemPreview_default
	},
	props: {
		record: Object,
		cell: Object,
		embedded: Boolean,
		actionsTarget: Object,
		description: String
	},
	emits: [
		"session-expired",
		"selected",
		"busy"
	],
	data() {
		return {
			loading: false,
			error: "",
			mediaUrl: "",
			mediaType: "",
			text: "",
			selectedFile: null,
			request: 0
		};
	},
	computed: { mobile() {
		return mobile.value;
	} },
	watch: {
		loading(value) {
			this.$emit("busy", value);
		},
		cell: {
			immediate: true,
			handler(cell) {
				this.reset();
				if (cell?.loadFile && cell.files?.length) this.selectFile(cell.files.find((file) => file.code === cell.fileCode) || cell.files.find((file) => !["web", "icon"].includes(file.type)) || cell.files[0]);
			}
		}
	},
	methods: {
		t,
		fileDetails(file) {
			return [
				file.filename?.includes(".") ? file.filename.split(".").at(-1).toUpperCase() : "",
				file.size != null ? prettySize(Number(file.size)) : "",
				file.type
			].filter(Boolean).join(" · ");
		},
		reset() {
			this.request++;
			if (this.mediaUrl) URL.revokeObjectURL(this.mediaUrl);
			this.mediaUrl = this.mediaType = this.text = this.error = "";
			this.loading = false;
			this.selectedFile = null;
		},
		async selectFile(file) {
			this.reset();
			this.selectedFile = file;
			this.$emit("selected", file);
			this.loading = true;
			const id = this.request;
			try {
				const blob = await this.cell.loadFile(file);
				if (id !== this.request) return;
				this.mediaUrl = URL.createObjectURL(blob);
				this.mediaType = blob.type;
				if (blob.type.startsWith("text/")) {
					const text = await blob.slice(0, 1e5).text();
					if (id === this.request) this.text = text;
				}
			} catch (error) {
				if (id === this.request) {
					this.error = error.message;
					if (error.code === "authentication_failed") this.$emit("session-expired");
				}
			} finally {
				if (id === this.request) this.loading = false;
			}
		},
		async download(file) {
			const id = this.request;
			try {
				const blob = await this.cell.loadFile(file);
				if (id !== this.request) return;
				downloadBlob(blob, file.filename);
			} catch (error) {
				if (id === this.request) {
					this.error = error.message;
					if (error.code === "authentication_failed") this.$emit("session-expired");
				}
			}
		}
	},
	beforeUnmount() {
		this.reset();
	}
};
var _hoisted_1$1 = { class: "file-preview-file-copy" };
var _hoisted_2$1 = { class: "muted" };
var _hoisted_3 = { class: "file-preview-file-copy" };
var _hoisted_4 = { class: "muted" };
var _hoisted_5 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_6 = {
	key: 2,
	role: "status"
};
var _hoisted_7 = { class: "file-preview-content" };
var _hoisted_8 = ["src"];
var _hoisted_9 = ["src"];
var _hoisted_10 = ["src", "title"];
var _hoisted_11 = {
	key: 4,
	class: "file-preview-text"
};
var _hoisted_12 = {
	key: 5,
	class: "muted"
};
var _hoisted_13 = {
	key: 6,
	class: "muted"
};
var _hoisted_14 = {
	key: 7,
	class: "file-preview-description"
};
var _hoisted_15 = { class: "file-preview-actions" };
var _hoisted_16 = {
	key: 0,
	class: "configuration-actions file-preview-download"
};
var _hoisted_17 = { key: 0 };
var _hoisted_18 = {
	key: 1,
	class: "file-preview-metadata"
};
var _hoisted_19 = { class: "file-preview-metadata" };
var _hoisted_20 = {
	key: 2,
	class: "file-preview-files"
};
var _hoisted_21 = { class: "muted" };
var _hoisted_22 = { class: "muted" };
var _hoisted_23 = {
	key: 0,
	class: "configuration-actions"
};
var _hoisted_24 = {
	key: 1,
	class: "configuration-actions"
};
var _hoisted_25 = {
	key: 3,
	class: "muted"
};
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_ItemPreview = resolveComponent("ItemPreview");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppMenu = resolveComponent("AppMenu");
	return $props.cell ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
		$options.mobile && $props.cell.loadFile && $props.cell.files?.length > 1 ? (openBlock(), createBlock(_component_AppMenu, {
			key: 0,
			class: "file-preview-picker",
			label: "Preview file",
			overlay: "",
			"show-label": "",
			"align-start": "",
			width: 360
		}, {
			trigger: withCtx(() => [
				createVNode(_component_ItemPreview, {
					"fallback-icon": "file",
					"preview-size": 32
				}),
				createBaseVNode("span", _hoisted_1$1, [createBaseVNode("strong", null, toDisplayString($data.selectedFile?.filename), 1), createBaseVNode("small", _hoisted_2$1, toDisplayString($data.selectedFile && $options.fileDetails($data.selectedFile)), 1)]),
				createVNode(_component_AppIcon, { name: "MDI_CHEVRON_DOWN" })
			]),
			default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList($props.cell.files, (file, index) => {
				return openBlock(), createBlock(_component_AppButton, {
					key: file.code || index,
					class: "file-preview-choice",
					role: "menuitemradio",
					"aria-checked": file === $data.selectedFile,
					label: file.filename,
					"translate-label": false,
					onClick: ($event) => $options.selectFile(file)
				}, {
					default: withCtx(() => [
						createVNode(_component_ItemPreview, {
							"fallback-icon": "file",
							"preview-size": 32
						}),
						createBaseVNode("span", _hoisted_3, [createBaseVNode("strong", null, toDisplayString(file.filename), 1), createBaseVNode("small", _hoisted_4, toDisplayString($options.fileDetails(file)), 1)]),
						file === $data.selectedFile ? (openBlock(), createBlock(_component_AppIcon, {
							key: 0,
							name: "check"
						})) : createCommentVNode("", true)
					]),
					_: 2
				}, 1032, [
					"aria-checked",
					"label",
					"onClick"
				]);
			}), 128))]),
			_: 1
		})) : createCommentVNode("", true),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_5, [createTextVNode(toDisplayString($options.t($data.error)) + " ", 1), $data.selectedFile ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			label: "Retry",
			onClick: _cache[0] || (_cache[0] = ($event) => $options.selectFile($data.selectedFile))
		})) : createCommentVNode("", true)])) : createCommentVNode("", true),
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString($options.t("Loading file…")), 1)) : createCommentVNode("", true),
		createBaseVNode("div", _hoisted_7, [
			!$props.cell.loadFile || $data.mediaType.startsWith("image/") && $data.mediaType !== "image/svg+xml" ? (openBlock(), createBlock(_component_ItemPreview, {
				key: 0,
				source: $data.mediaUrl || $props.cell.image,
				"fallback-icon": "image"
			}, null, 8, ["source"])) : $data.mediaType.startsWith("video/") ? (openBlock(), createElementBlock("video", {
				key: 1,
				src: $data.mediaUrl,
				controls: "",
				preload: "metadata"
			}, null, 8, _hoisted_8)) : $data.mediaType.startsWith("audio/") ? (openBlock(), createElementBlock("audio", {
				key: 2,
				src: $data.mediaUrl,
				controls: "",
				preload: "metadata"
			}, null, 8, _hoisted_9)) : $data.mediaType === "application/pdf" ? (openBlock(), createElementBlock("iframe", {
				key: 3,
				src: $data.mediaUrl,
				title: $data.selectedFile?.filename
			}, null, 8, _hoisted_10)) : $data.mediaType.startsWith("text/") ? (openBlock(), createElementBlock("pre", _hoisted_11, toDisplayString($data.text), 1)) : !$data.loading ? (openBlock(), createElementBlock("p", _hoisted_12, toDisplayString($options.t("No preview available")), 1)) : createCommentVNode("", true),
			!$props.cell.loadFile && !$props.cell.image ? (openBlock(), createElementBlock("p", _hoisted_13, toDisplayString($options.t("No preview available")), 1)) : createCommentVNode("", true),
			$props.description || $props.record?.description ? (openBlock(), createElementBlock("p", _hoisted_14, toDisplayString($props.description || $props.record.description), 1)) : createCommentVNode("", true)
		]),
		(openBlock(), createBlock(Teleport, {
			to: $props.actionsTarget || "body",
			disabled: !$options.mobile || !$props.actionsTarget
		}, [createBaseVNode("nav", _hoisted_15, [($props.embedded || $options.mobile) && $data.selectedFile ? (openBlock(), createElementBlock("div", _hoisted_16, [$data.selectedFile.href ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			href: $data.selectedFile.href,
			label: "Download",
			icon: "download",
			download: $data.selectedFile.filename
		}, null, 8, ["href", "download"])) : (openBlock(), createBlock(_component_AppButton, {
			key: 1,
			label: "Download",
			icon: "download",
			onClick: _cache[1] || (_cache[1] = ($event) => $options.download($data.selectedFile))
		}))])) : createCommentVNode("", true), (openBlock(), createBlock(resolveDynamicComponent($options.mobile ? "AppMenu" : "div"), {
			class: "file-preview-details",
			label: "File details",
			overlay: $options.mobile
		}, {
			default: withCtx(() => [
				$options.mobile ? (openBlock(), createElementBlock("small", _hoisted_17, toDisplayString($props.record?.__search_key__), 1)) : createCommentVNode("", true),
				$props.cell.object ? (openBlock(), createElementBlock("dl", _hoisted_18, [
					createBaseVNode("dt", null, toDisplayString($options.t("Search Type")), 1),
					createBaseVNode("dd", null, toDisplayString($props.cell.object.search_type), 1),
					(openBlock(), createElementBlock(Fragment, null, renderList([
						"code",
						"status",
						"description"
					], (name) => {
						return openBlock(), createElementBlock(Fragment, { key: name }, [createBaseVNode("dt", null, toDisplayString($options.t({
							code: "Code",
							status: "Status",
							description: "Description"
						}[name])), 1), createBaseVNode("dd", null, toDisplayString($props.record?.[name] || "—"), 1)], 64);
					}), 64))
				])) : createCommentVNode("", true),
				createBaseVNode("dl", _hoisted_19, [
					createBaseVNode("dt", null, toDisplayString($options.t("Context")), 1),
					createBaseVNode("dd", null, toDisplayString($props.cell.context || "—"), 1),
					createBaseVNode("dt", null, toDisplayString($options.t("Version")), 1),
					createBaseVNode("dd", null, toDisplayString($props.cell.version ?? "—"), 1)
				]),
				$props.cell.files?.length ? (openBlock(), createElementBlock("ul", _hoisted_20, [(openBlock(true), createElementBlock(Fragment, null, renderList($props.cell.files, (file, index) => {
					return openBlock(), createElementBlock("li", { key: index }, [createBaseVNode("div", null, [
						createBaseVNode("strong", null, toDisplayString(file.filename), 1),
						createBaseVNode("small", _hoisted_21, toDisplayString(file.type) + " · " + toDisplayString(file.size ?? "—") + " " + toDisplayString($options.t("bytes")), 1),
						createBaseVNode("small", _hoisted_22, toDisplayString(file.path), 1)
					]), file.href ? (openBlock(), createElementBlock("div", _hoisted_23, [createVNode(_component_AppButton, {
						href: file.href,
						label: "Open file",
						icon: "link",
						target: "_blank",
						rel: "noopener noreferrer"
					}, null, 8, ["href"]), createVNode(_component_AppButton, {
						href: file.href,
						label: "Download",
						icon: "download",
						download: file.filename
					}, null, 8, ["href", "download"])])) : $props.cell.loadFile ? (openBlock(), createElementBlock("div", _hoisted_24, [createVNode(_component_AppButton, {
						label: "Open file",
						icon: "link",
						disabled: $data.loading,
						onClick: ($event) => $options.selectFile(file)
					}, null, 8, ["disabled", "onClick"]), createVNode(_component_AppButton, {
						label: "Download",
						icon: "download",
						onClick: ($event) => $options.download(file)
					}, null, 8, ["onClick"])])) : createCommentVNode("", true)]);
				}), 128))])) : (openBlock(), createElementBlock("p", _hoisted_25, toDisplayString($options.t("No files")), 1))
			]),
			_: 1
		}, 8, ["overlay"]))])], 8, ["to", "disabled"]))
	], 64)) : createCommentVNode("", true);
}
var FilePreviewContent_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$1, [["render", _sfc_render$1]]);
//#endregion
//#region src/features/objects/FilePreview.vue
var _sfc_main = {
	components: {
		AppButton: _sfc_main$2,
		FilePreviewContent: FilePreviewContent_default
	},
	props: {
		ticket: String,
		project: String,
		searchType: String
	},
	emits: [
		"session-expired",
		"opened",
		"closed"
	],
	data() {
		return {
			record: null,
			cell: null,
			selectedFile: null,
			loading: false
		};
	},
	computed: { mobile() {
		return mobile.value;
	} },
	watch: {
		ticket() {
			this.close();
		},
		project() {
			this.close();
		},
		searchType() {
			this.close();
		}
	},
	methods: {
		t,
		open(record, cell) {
			this.record = record;
			this.cell = cell;
			this.$refs.dialog.show();
			this.$emit("opened");
		},
		close() {
			this.$refs.dialog?.close();
			this.record = this.cell = null;
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { key: 0 };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_FilePreviewContent = resolveComponent("FilePreviewContent");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog file-preview",
		"aria-label": $options.t("File preview"),
		"aria-busy": $data.loading,
		onCancel: _cache[3] || (_cache[3] = withModifiers((...args) => $options.close && $options.close(...args), ["prevent"])),
		onClose: _cache[4] || (_cache[4] = ($event) => {
			$data.record = $data.cell = null;
			$data.selectedFile = null;
			$data.loading = false;
			_ctx.$emit("closed");
		})
	}, [$data.cell ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.mobile && $data.selectedFile?.filename || $data.record?.name || $data.record?.title || $data.record?.code || $data.record?.id), 1), !$options.mobile ? (openBlock(), createElementBlock("small", _hoisted_2, toDisplayString($data.record?.__search_key__), 1)) : createCommentVNode("", true)]), createVNode(_component_AppButton, {
		label: "Close preview",
		icon: "close",
		"icon-only": "",
		autofocus: "",
		onClick: $options.close
	}, null, 8, ["onClick"])]), createVNode(_component_FilePreviewContent, {
		ref: "content",
		record: $data.record,
		cell: $data.cell,
		onSelected: _cache[0] || (_cache[0] = ($event) => $data.selectedFile = $event),
		onBusy: _cache[1] || (_cache[1] = ($event) => $data.loading = $event),
		onSessionExpired: _cache[2] || (_cache[2] = ($event) => _ctx.$emit("session-expired"))
	}, null, 8, ["record", "cell"])], 64)) : createCommentVNode("", true)], 40, _hoisted_1)), [[_directive_window, { type: "window" }]])]);
}
var FilePreview_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { FilePreviewContent_default as n, FilePreview_default as t };

//# sourceMappingURL=FilePreview.js.map
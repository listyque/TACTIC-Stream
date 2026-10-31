import { r as __exportAll } from "./ObjectFieldFrame.js";
import { E as nextTick, F as resolveComponent, I as resolveDirective, K as withDirectives, M as openBlock, _ as createElementBlock, b as createVNode, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, rt as toDisplayString } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { Y as uploadFormFile, j as rpc } from "./index.js";
import { G as button, H as observeFrameSizes, J as muted, K as label, X as rect, Y as node, t as _sfc_main$1, w as translate } from "./FrameView.js";
import { t as describe$1 } from "./confirmation.ui.js";
//#region ../src/tactic_stream/shared_ui/features/projects/templates.ui.mjs
function describe(model, width, height, language) {
	const text = (key) => translate(key, language), compact = width < 560;
	const nodes = [
		label("templatesTitle", rect(20, 12, width - 200, 28), text("Manage templates"), {
			fontRole: "title",
			weight: 600,
			role: "heading"
		}),
		button("templatesHelp", rect(width - 86, 12, 32, 32), text("Project creation help"), "help", { type: "help" }, true, { iconOnly: true }),
		button("templatesClose", rect(width - 48, 12, 32, 32), text("Close"), "close", { type: "close" }, !model.busy, { iconOnly: true }),
		button("templateInstall", rect(20, 54, 230, 36), text("Install template archive"), "upload", { type: "install" }, !model.busy),
		button("templateRefresh", rect(width - 52, 54, 32, 36), text("Refresh templates"), "refresh", { type: "refresh" }, !model.busy, { iconOnly: true })
	];
	let top = 102;
	if (model.error || model.busy) {
		nodes.push(label("templatesStatus", rect(20, top, width - 40, 44), model.error || text("Working…"), {
			color: model.error ? "error" : "secondaryText",
			wrap: true
		}));
		top += 52;
	}
	if (!(model.packages || []).length) nodes.push(label("templatesEmpty", rect(20, top, width - 40, 36), text("No installed template packages."), Object.assign({}, muted, { wrap: true })));
	const rows = (model.packages || []).map((row, index) => node("Action", "template_" + row.code, rect(0, index * 62, width - 56, 58), {
		text: row.code,
		selected: model.selected === row.code,
		enabled: !model.busy,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		action: {
			type: "select",
			code: row.code
		},
		children: [label("templateCode_" + row.code, rect(14, 4, width - 84, 26), row.code, { weight: 600 }), label("templatePath_" + row.code, rect(14, 30, width - 84, 20), row.path, muted)]
	}));
	const footer = 62;
	nodes.push(node("Scroll", "templatesPackages", rect(20, top, width - 40, Math.max(0, height - top - footer)), {
		contentHeight: rows.length * 62 + 8,
		children: rows
	}));
	nodes.push(node("Box", "templatesFooter", rect(0, height - footer, width, footer), {
		background: "surfaceContainerLow",
		radius: 0
	}));
	nodes.push(button("templateDownload", rect(20, height - 48, compact ? 180 : 210, 36), text("Download archive"), "download", { type: "download" }, !!model.selected && !model.busy));
	nodes.push(button("templateDelete", rect(width - 130, height - 48, 110, 36), text("Delete"), "delete", { type: "delete" }, !!model.selected && !model.busy, { destructive: true }));
	const header = nodes.splice(0, 3);
	nodes.unshift(node("Box", "templatesHeader", rect(0, 0, width, 48), {
		titlebar: true,
		chromeRight: 86,
		background: "surfaceContainerLow",
		radius: 0,
		children: header
	}));
	return { nodes };
}
function confirmation(model, width, height, language) {
	return describe$1({
		message: translate("Remove template {code}? Existing projects are not removed.", language, { code: model.code }),
		accept: "Delete",
		reject: "Cancel",
		destructive: true,
		busy: model.busy,
		acceptId: "templateDeleteConfirm",
		rejectId: "templateDeleteCancel"
	}, width, height, language);
}
//#endregion
//#region src/features/projects/ProjectTemplates.vue
var ProjectTemplates_exports = /* @__PURE__ */ __exportAll({ default: () => ProjectTemplates_default });
var _sfc_main = {
	inject: ["openHelp"],
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		packages: Array
	},
	emits: ["changed"],
	data() {
		return {
			busy: false,
			error: "",
			deletion: null,
			selected: "",
			viewport: {
				width: 650,
				height: 500
			},
			observer: null,
			generation: 0
		};
	},
	computed: {
		confirmationScene() {
			return confirmation({
				code: this.deletion?.code || "",
				busy: this.busy
			}, Math.min(430, this.viewport.width - 32), 220, appearance.language);
		},
		scene() {
			return describe({
				packages: this.packages,
				selected: this.selected,
				busy: this.busy,
				error: this.error,
				deletion: this.deletion?.code
			}, this.viewport.width, this.viewport.height, appearance.language);
		}
	},
	watch: {
		deletion(value) {
			if (value) nextTick(() => {
				if (this.deletion && !this.$refs.confirm.matches(":modal")) this.$refs.confirm.showModal();
			});
			else this.$refs.confirm?.close();
		},
		ticket() {
			this.generation++;
			this.busy = false;
			this.deletion = null;
			this.$refs.dialog.close();
		}
	},
	mounted() {
		this.observer = observeFrameSizes((entries) => {
			const box = entries.at(-1).contentRect;
			this.viewport = {
				width: box.width,
				height: box.height
			};
		});
		this.observer.observe(this.$refs.host);
	},
	beforeUnmount() {
		this.generation++;
		this.observer?.disconnect();
	},
	methods: {
		t,
		windowContext() {
			if (this.busy || this.deletion) throw Error("Please wait for the current operation to finish");
			return {};
		},
		dispatch(action) {
			const row = this.packages.find((row) => row.code === this.selected);
			if (action.type === "select") this.selected = action.code;
			else if (action.type === "help") this.openHelp("project_creation");
			else if (action.type === "close" && !this.busy) this.$refs.dialog.close();
			else if (action.type === "install") this.$refs.file.click();
			else if (action.type === "refresh") this.$emit("changed");
			else if (action.type === "download" && row) this.download(row);
			else if (action.type === "delete") this.deletion = row;
			else if (action.type === "cancelDelete") this.deletion = null;
			else if (action.type === "confirmDelete") this.remove();
		},
		open() {
			this.error = "";
			this.deletion = null;
			this.$refs.dialog.showModal();
		},
		async run(command, args) {
			const generation = this.generation;
			this.error = "";
			this.busy = true;
			try {
				const result = await rpc("execute_cmd", [
					{
						ticket: this.ticket,
						project: "admin",
						language: "python"
					},
					command,
					args
				]);
				return generation === this.generation ? result : null;
			} catch (error) {
				if (generation !== this.generation) return null;
				this.error = error.message;
				return null;
			} finally {
				if (generation === this.generation) this.busy = false;
			}
		},
		async install(event) {
			const generation = this.generation, ticket = this.ticket;
			const file = event.target.files[0];
			event.target.value = "";
			if (!file) return;
			this.busy = true;
			this.error = "";
			try {
				const filename = await uploadFormFile(ticket, "admin", file);
				if (generation !== this.generation) return;
				if (await this.run("tactic.ui.app.ProjectTemplateInstallCmd", { paths: [filename] })) this.$emit("changed");
			} catch (error) {
				if (generation !== this.generation) return;
				this.error = error.message;
			} finally {
				if (generation === this.generation) this.busy = false;
			}
		},
		async download(row) {
			const result = await this.run("tactic.ui.app.ProjectTemplateDownloadCmd", { template_dir: row.path });
			if (!result) return;
			const link = document.createElement("a");
			link.href = "/assets/_cache/" + encodeURIComponent(this.ticket) + "/" + encodeURIComponent(result.info.filename);
			link.download = result.info.filename;
			link.click();
		},
		async remove() {
			if (await this.run("tactic.ui.app.ProjectTemplateDeleteCmd", { template: this.deletion.code })) {
				this.deletion = null;
				this.$emit("changed");
			}
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = {
	ref: "host",
	class: "frame-project-templates"
};
var _hoisted_3 = ["aria-label", "disabled"];
var _hoisted_4 = ["aria-label"];
var _hoisted_5 = { class: "frame-template-confirmation-body" };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	const _directive_window = resolveDirective("window");
	return withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog project-templates",
		"aria-label": $options.t("Manage templates"),
		onCancel: _cache[3] || (_cache[3] = withModifiers(($event) => !$data.busy && _ctx.$refs.dialog.close(), ["prevent"]))
	}, [
		createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
			scene: $options.scene,
			onEvent: $options.dispatch
		}, null, 8, ["scene", "onEvent"])], 512),
		createBaseVNode("input", {
			ref: "file",
			type: "file",
			accept: ".zip",
			hidden: "",
			"aria-label": $options.t("Template ZIP archive"),
			disabled: $data.busy,
			onChange: _cache[0] || (_cache[0] = (...args) => $options.install && $options.install(...args))
		}, null, 40, _hoisted_3),
		createBaseVNode("dialog", {
			ref: "confirm",
			class: "record-dialog frame-template-confirmation",
			"aria-label": $options.t("Delete template?"),
			style: normalizeStyle({ width: Math.min(430, $data.viewport.width - 32) + "px" }),
			onCancel: _cache[2] || (_cache[2] = withModifiers(($event) => !$data.busy && ($data.deletion = null), ["prevent"]))
		}, [createBaseVNode("header", null, [createBaseVNode("h3", null, toDisplayString($options.t("Delete template?")), 1)]), createBaseVNode("div", _hoisted_5, [createVNode(_component_FrameView, {
			scene: $options.confirmationScene,
			onEvent: _cache[1] || (_cache[1] = ($event) => $options.dispatch({ type: $event.type === "accept" ? "confirmDelete" : "cancelDelete" }))
		}, null, 8, ["scene"])])], 44, _hoisted_4)
	], 40, _hoisted_1)), [[_directive_window, {
		kind: "project_templates",
		page: $options.windowContext
	}]]);
}
var ProjectTemplates_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ProjectTemplates_exports as n, ProjectTemplates_default as t };

//# sourceMappingURL=ProjectTemplates.js.map
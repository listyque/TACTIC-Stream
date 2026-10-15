import { B as useId, D as nextTick, G as withCtx, I as resolveComponent, K as withDirectives, N as openBlock, P as renderList, _ as createCommentVNode, b as createTextVNode, d as Fragment, g as createBlock, h as createBaseVNode, p as Teleport, rt as toDisplayString, s as vModelText, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, V as preferences, Y as _plugin_vue_export_helper_default, i as mobile, o as _sfc_main$1 } from "./index.js";
import { K as uploadFormFile, M as rpc, j as resultItems, x as navigationLink } from "./clipboard.js";
import { t as _sfc_main$2 } from "./AppSwitch.js";
import { t as _sfc_main$3 } from "./AppSelect.js";
import { t as _sfc_main$4 } from "./SettingRow.js";
//#region src/features/checkin/ObjectCheckin.vue
var _sfc_main = {
	setup() {
		return { formId: useId() };
	},
	components: {
		AppButton: _sfc_main$1,
		AppSelect: _sfc_main$3,
		AppSwitch: _sfc_main$2,
		SettingRow: _sfc_main$4
	},
	inject: {
		queueCheckin: { default: null },
		checkinDescription: { default: () => "" }
	},
	props: {
		ticket: String,
		project: String
	},
	data() {
		return {
			owner: null,
			scope: null,
			files: [],
			processes: [],
			process: "publish",
			context: "publish",
			description: "",
			mode: "group",
			preview: false,
			clipboard: false,
			revision: false,
			version: null,
			confirmed: false,
			appendSnapshot: null,
			appendUncertain: false,
			existingFiles: [],
			keepFileName: false,
			repositories: [],
			repositoryAlias: "default",
			ready: false,
			busy: false,
			error: "",
			discard: false,
			request: 0
		};
	},
	emits: ["attached"],
	watch: {
		ticket() {
			this.reset();
		},
		project() {
			this.reset();
		}
	},
	computed: {
		mobile() {
			return mobile.value;
		},
		title() {
			return this.appendSnapshot ? "Attach files" : this.preview ? "Change Preview" : this.revision ? "Add revision (override current file)" : this.clipboard ? "Save from Clipboard" : "Save snapshot";
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
		beforeUnload(event) {
			if (this.files.length) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		reset() {
			this.request++;
			this.files = [];
			this.$refs.dialog?.close();
		},
		close(force = false) {
			force = force === true;
			if (this.busy && this.ready && !force) return;
			if (this.files.length && !force) {
				this.discard = true;
				return;
			}
			this.reset();
		},
		async open(record, options = {}) {
			const request = ++this.request;
			this.scope = {
				ticket: this.ticket,
				project: this.project
			};
			this.owner = record;
			this.files = [];
			this.processes = [];
			this.error = "";
			this.discard = false;
			this.appendSnapshot = null;
			this.appendUncertain = false;
			this.existingFiles = [];
			this.repositories = [];
			this.repositoryAlias = preferences.repository.defaultAlias;
			this.description = this.checkinDescription();
			this.mode = preferences.checkin.groupCheckin ? "group" : "individual";
			this.keepFileName = preferences.checkin.keepFilename;
			this.confirmed = !preferences.checkin.confirmRevision;
			if (options.checkinType === "file") this.mode = "individual";
			if (options.checkinType === "multi_file") this.mode = "group";
			this.preview = !!options.preview;
			this.clipboard = !!options.clipboard;
			this.revision = !!options.revision;
			this.version = null;
			this.process = options.process || (this.preview ? "icon" : "publish");
			this.context = options.context && options.context !== this.process ? options.context : "";
			this.busy = true;
			this.ready = false;
			await nextTick();
			this.$refs.dialog.showModal();
			try {
				if ([
					"move",
					"local",
					"inplace"
				].includes(options.transferMode) || ["sequence", "dir"].includes(options.checkinType)) throw new Error("This configured check-in mode requires a desktop connection.");
				if (record.__search_key__.startsWith("sthpw/snapshot?")) {
					const target = await navigationLink(this.scope.ticket, this.scope.project, "skey://" + record.__search_key__);
					if (request !== this.request) return;
					if (!target.parent) throw new Error("Object no longer exists");
					this.owner = target.parent;
					this.context = record.context;
					this.process = record.process || record.context.split("/")[0];
					if (options.append) {
						this.appendSnapshot = record.version < 0 ? await rpc("get_snapshot", [this.scope, this.owner.__search_key__], { context: record.context }) || record : record;
						const snapshot = await navigationLink(this.scope.ticket, this.scope.project, "skey://" + this.appendSnapshot.__search_key__);
						if (request !== this.request) return;
						this.existingFiles = snapshot.preview?.files || [];
					}
					if (this.revision && record.version >= 0) this.version = record.version;
				}
				const type = this.owner.__search_key__.split("?")[0];
				const data = await resultItems(this.scope.ticket, this.scope.project, type, [this.owner.__search_key__]);
				if (request !== this.request) return;
				this.processes = data.items[0].branches.filter((branch) => branch.kind === "process").map((branch) => ({
					value: branch.process,
					label: branch.title
				}));
				if (this.preview) this.process = this.context = "icon";
				if (!this.processes.some((item) => item.value === this.process)) this.processes.unshift({
					value: this.process,
					label: this.process
				});
				const configured = await rpc("get_base_dirs", [this.scope], {}, true);
				if (request !== this.request) return;
				const paths = (value) => typeof value === "object" && value ? value : value?.startsWith("{") ? JSON.parse(value) : value ? { default: value } : {};
				const aliases = [.../* @__PURE__ */ new Set([
					"default",
					...Object.keys(paths(configured.asset_base_dir)),
					...Object.keys(paths(configured.base_dir_alias))
				])];
				const labels = paths(configured.repository_display);
				this.repositories = aliases.filter((alias) => alias !== "plugins" && (preferences.repository.enabledAliases === null || preferences.repository.enabledAliases.includes(alias))).map((alias) => ({
					value: alias,
					label: labels[alias]?.title || alias
				}));
				if (!this.repositories.length) throw new Error("Enable at least one repository and choose its default.");
				if (!this.repositories.some((item) => item.value === this.repositoryAlias)) this.repositoryAlias = this.repositories[0].value;
				this.ready = true;
				if (options.clipboard) await this.readImage();
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		addFiles(files) {
			const incoming = [...files];
			if (incoming.some((file) => this.preview && !file.type.startsWith("image/"))) {
				this.error = "Choose an image for the preview";
				return;
			}
			this.files.push(...incoming);
			this.error = "";
		},
		paste(event) {
			if (event.clipboardData?.files.length) {
				event.preventDefault();
				this.addFiles(event.clipboardData.files);
			}
		},
		async readImage() {
			if (!navigator.clipboard?.read) {
				this.error = "Paste an image with Ctrl+V or choose a file on HTTP.";
				return;
			}
			const request = this.request;
			try {
				const files = [];
				for (const item of await navigator.clipboard.read()) {
					const type = item.types.find((type) => type.startsWith("image/"));
					if (type) files.push(new File([await item.getType(type)], "clipboard-" + (files.length + 1) + "." + type.split("/")[1], { type }));
				}
				if (request !== this.request) return;
				if (!files.length) throw new Error("No image in clipboard");
				this.addFiles(files);
			} catch (error) {
				if (request === this.request) this.error = error.message;
			}
		},
		submit() {
			if (this.appendSnapshot) return this.attachFiles();
			if (!this.ready || this.busy || !this.files.length || !(this.context.trim() || this.process) || this.revision && !this.confirmed) return;
			if (new Set(this.files.map((file) => file.name)).size !== this.files.length) {
				this.error = "Choose different file names for a group check-in";
				return;
			}
			try {
				const values = {
					...this.scope,
					searchKey: this.owner.__search_key__,
					title: this.owner.name || this.owner.title || this.owner.code,
					process: this.process,
					context: this.context.trim() || this.process,
					description: this.description,
					isRevision: this.revision,
					version: this.version,
					keepFileName: this.keepFileName,
					generatePreviews: preferences.checkin.generatePreviews,
					...this.revision ? {} : { repositoryAlias: this.repositoryAlias }
				};
				const groups = this.mode === "individual" ? this.files.map((file) => [file]) : [this.files];
				for (const files of groups) this.queueCheckin({
					...values,
					files: [...files],
					file: files[0],
					name: files.map((file) => file.name).join(", ")
				});
				this.files = [];
				this.close(true);
			} catch (error) {
				this.error = error.message;
			}
		},
		async attachFiles() {
			if (!this.ready || this.busy || this.appendUncertain || !this.files.length) return;
			const names = this.files.map((file) => file.name.toLocaleLowerCase());
			if (new Set(names).size !== names.length || this.existingFiles.some((file) => names.includes(file.filename.toLocaleLowerCase()))) {
				this.error = "Choose file names that are not already in the snapshot";
				return;
			}
			const request = this.request, scope = this.scope;
			this.busy = true;
			this.error = "";
			let committing = false;
			try {
				const paths = [];
				for (const file of this.files) {
					paths.push(await uploadFormFile(scope.ticket, scope.project, file));
					if (request !== this.request) return;
				}
				committing = true;
				await rpc("add_file", [
					scope,
					this.appendSnapshot.code,
					paths
				], {
					file_type: "attachment",
					mode: "upload"
				});
				if (request !== this.request) return;
				this.busy = false;
				this.files = [];
				this.close(true);
				this.$emit("attached");
			} catch (error) {
				if (request === this.request) {
					this.appendUncertain = committing && (!error.status || error.status >= 500);
					this.error = error.message;
				}
			} finally {
				if (request === this.request) this.busy = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = {
	key: 0,
	role: "status"
};
var _hoisted_3 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_4 = { class: "object-checkin-body" };
var _hoisted_5 = { key: 1 };
var _hoisted_6 = { key: 2 };
var _hoisted_7 = ["disabled"];
var _hoisted_8 = { key: 3 };
var _hoisted_9 = ["disabled"];
var _hoisted_10 = ["accept"];
var _hoisted_11 = { class: "configuration-actions checkin-file-actions" };
var _hoisted_12 = {
	key: 4,
	class: "muted"
};
var _hoisted_13 = { class: "file-preview-files" };
var _hoisted_14 = { key: 5 };
var _hoisted_15 = { class: "notice" };
var _hoisted_16 = {
	key: 8,
	class: "notice",
	role: "alert"
};
var _hoisted_17 = {
	key: 9,
	class: "notice",
	role: "alert"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_AppSwitch = resolveComponent("AppSwitch");
	const _component_SettingRow = resolveComponent("SettingRow");
	return openBlock(), createBlock(Teleport, { to: "body" }, [createBaseVNode("dialog", {
		ref: "dialog",
		class: "record-dialog object-checkin",
		"aria-label": $options.t($options.title),
		onCancel: _cache[16] || (_cache[16] = withModifiers(($event) => $options.close(), ["prevent"])),
		onPaste: _cache[17] || (_cache[17] = (...args) => $options.paste && $options.paste(...args)),
		onDragover: _cache[18] || (_cache[18] = withModifiers(() => {}, ["prevent"])),
		onDrop: _cache[19] || (_cache[19] = withModifiers(($event) => $options.addFiles($event.dataTransfer.files), ["prevent"]))
	}, [
		createBaseVNode("header", null, [
			$options.mobile ? (openBlock(), createBlock(_component_AppButton, {
				key: 0,
				label: "Back",
				icon: "MDI_ARROW_LEFT",
				"icon-only": "",
				onClick: _cache[0] || (_cache[0] = ($event) => $options.close())
			})) : createCommentVNode("", true),
			createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.t($options.title)), 1), createBaseVNode("small", null, [createTextVNode(toDisplayString($data.owner?.name || $data.owner?.title || $data.owner?.code), 1), !$options.mobile ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" · " + toDisplayString($data.owner?.__search_key__), 1)], 64)) : createCommentVNode("", true)])]),
			!$options.mobile ? (openBlock(), createBlock(_component_AppButton, {
				key: 1,
				label: "Close",
				icon: "close",
				onClick: _cache[1] || (_cache[1] = ($event) => $options.close())
			})) : createCommentVNode("", true)
		]),
		$data.busy ? (openBlock(), createElementBlock("p", _hoisted_2, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true),
		createBaseVNode("form", { onSubmit: _cache[15] || (_cache[15] = withModifiers((...args) => $options.submit && $options.submit(...args), ["prevent"])) }, [createBaseVNode("div", _hoisted_4, [
			!$data.revision && !$data.appendSnapshot ? (openBlock(), createBlock(_component_AppSelect, {
				key: 0,
				modelValue: $data.repositoryAlias,
				"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => $data.repositoryAlias = $event),
				options: $data.repositories,
				"translate-labels": false,
				label: "Repository",
				disabled: $data.busy
			}, null, 8, [
				"modelValue",
				"options",
				"disabled"
			])) : createCommentVNode("", true),
			!$data.preview ? (openBlock(), createElementBlock("label", _hoisted_5, [createTextVNode(toDisplayString($options.t("Process")), 1), createVNode(_component_AppSelect, {
				modelValue: $data.process,
				"onUpdate:modelValue": [_cache[3] || (_cache[3] = ($event) => $data.process = $event), _cache[4] || (_cache[4] = ($event) => $data.context = "")],
				options: $data.processes,
				"translate-labels": false,
				label: "Process",
				disabled: $data.busy || $data.revision || !!$data.appendSnapshot
			}, null, 8, [
				"modelValue",
				"options",
				"disabled"
			])])) : createCommentVNode("", true),
			!$data.preview ? (openBlock(), createElementBlock("label", _hoisted_6, [createTextVNode(toDisplayString($options.t("Context")), 1), withDirectives(createBaseVNode("input", {
				"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => $data.context = $event),
				disabled: $data.busy || $data.revision || !!$data.appendSnapshot,
				maxlength: "256"
			}, null, 8, _hoisted_7), [[vModelText, $data.context]])])) : createCommentVNode("", true),
			!$data.appendSnapshot ? (openBlock(), createElementBlock("label", _hoisted_8, [createTextVNode(toDisplayString($options.t("Description")), 1), withDirectives(createBaseVNode("textarea", {
				"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => $data.description = $event),
				rows: "3",
				disabled: $data.busy
			}, null, 8, _hoisted_9), [[vModelText, $data.description]])])) : createCommentVNode("", true),
			createBaseVNode("input", {
				ref: "fileInput",
				type: "file",
				multiple: "",
				hidden: "",
				accept: $data.preview ? "image/*" : void 0,
				onChange: _cache[7] || (_cache[7] = ($event) => {
					$options.addFiles($event.target.files);
					$event.target.value = "";
				})
			}, null, 40, _hoisted_10),
			createBaseVNode("div", _hoisted_11, [createVNode(_component_AppButton, {
				label: "Choose files for check-in",
				icon: "upload",
				disabled: $data.busy,
				onClick: _cache[8] || (_cache[8] = ($event) => _ctx.$refs.fileInput.click())
			}, null, 8, ["disabled"]), createVNode(_component_AppButton, {
				label: "Save from Clipboard",
				icon: "MDI_CONTENT_PASTE",
				"icon-only": $options.mobile,
				disabled: $data.busy,
				onClick: $options.readImage
			}, null, 8, [
				"icon-only",
				"disabled",
				"onClick"
			])]),
			!$data.files.length && !$options.mobile ? (openBlock(), createElementBlock("p", _hoisted_12, toDisplayString($options.t("Drop files here, paste an image, or choose files for check-in.")), 1)) : createCommentVNode("", true),
			createBaseVNode("ul", _hoisted_13, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.files, (file, index) => {
				return openBlock(), createElementBlock("li", { key: index }, [createBaseVNode("span", null, toDisplayString(file.name) + " · " + toDisplayString(file.size) + " " + toDisplayString($options.t("bytes")), 1), createVNode(_component_AppButton, {
					label: "Remove file",
					icon: "close",
					"icon-only": "",
					onClick: ($event) => $data.files.splice(index, 1)
				}, null, 8, ["onClick"])]);
			}), 128))]),
			$data.files.length > 1 && !$data.appendSnapshot ? (openBlock(), createElementBlock("label", _hoisted_14, [createTextVNode(toDisplayString($options.t("Check in multiple files?")), 1), createVNode(_component_AppSelect, {
				modelValue: $data.mode,
				"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => $data.mode = $event),
				label: "Check in multiple files?",
				options: [{
					value: "group",
					label: "One group"
				}, {
					value: "individual",
					label: "Separately"
				}]
			}, null, 8, ["modelValue"])])) : createCommentVNode("", true),
			!$data.appendSnapshot ? (openBlock(), createBlock(_component_SettingRow, {
				key: 6,
				title: "Keep original file names",
				"control-id": $setup.formId + "-keep-file-name"
			}, {
				default: withCtx(() => [createVNode(_component_AppSwitch, {
					id: $setup.formId + "-keep-file-name",
					modelValue: $data.keepFileName,
					"onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => $data.keepFileName = $event),
					label: "Keep original file names"
				}, null, 8, ["id", "modelValue"])]),
				_: 1
			}, 8, ["control-id"])) : createCommentVNode("", true),
			$data.revision ? (openBlock(), createElementBlock(Fragment, { key: 7 }, [createBaseVNode("p", _hoisted_15, toDisplayString($options.t("The file stored in this revision will be replaced. Use Save snapshot when you need a new version.")), 1), createVNode(_component_SettingRow, {
				title: "Replace revision",
				"control-id": $setup.formId + "-replace-revision"
			}, {
				default: withCtx(() => [createVNode(_component_AppSwitch, {
					id: $setup.formId + "-replace-revision",
					modelValue: $data.confirmed,
					"onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => $data.confirmed = $event),
					label: "Replace revision"
				}, null, 8, ["id", "modelValue"])]),
				_: 1
			}, 8, ["control-id"])], 64)) : createCommentVNode("", true),
			$data.appendUncertain ? (openBlock(), createElementBlock("p", _hoisted_16, toDisplayString($options.t("The attachment result is unknown. Close this window and refresh the snapshot before retrying.")), 1)) : createCommentVNode("", true),
			$data.discard ? (openBlock(), createElementBlock("div", _hoisted_17, [
				createBaseVNode("p", null, toDisplayString($options.t("Discard unsaved changes?")), 1),
				createVNode(_component_AppButton, {
					label: "Continue editing",
					onClick: _cache[12] || (_cache[12] = ($event) => $data.discard = false)
				}),
				createVNode(_component_AppButton, {
					label: "Discard",
					destructive: "",
					onClick: _cache[13] || (_cache[13] = ($event) => $options.close(true))
				})
			])) : createCommentVNode("", true)
		]), createBaseVNode("footer", null, [createVNode(_component_AppButton, {
			label: "Cancel",
			disabled: $data.busy,
			onClick: _cache[14] || (_cache[14] = ($event) => $options.close())
		}, null, 8, ["disabled"]), createVNode(_component_AppButton, {
			type: "submit",
			label: $data.appendSnapshot ? "Attach files" : "Add to Commit Queue",
			icon: "save",
			highlighted: "",
			disabled: !$data.ready || $data.busy || $data.appendUncertain || !$data.files.length || !($data.context.trim() || $data.process) || $data.revision && !$data.confirmed || !$data.appendSnapshot && !$options.queueCheckin
		}, null, 8, ["label", "disabled"])])], 32)
	], 40, _hoisted_1)]);
}
var ObjectCheckin_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ObjectCheckin_default as default };

//# sourceMappingURL=ObjectCheckin.js.map
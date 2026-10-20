import { A as onMounted, E as nextTick, F as resolveComponent, G as withCtx, I as resolveDirective, K as withDirectives, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { A as appearance, R as controls, Z as preferences, at as _plugin_vue_export_helper_default, c as _sfc_main$3, k as t, o as mobile } from "./index.js";
import { Gt as rect, Ht as label, Vt as button, Wt as node, X as navigationLink, i as _sfc_main$4, ot as resultItems, r as observeFrameSizes, st as rpc, xt as uploadFormFile, y as translate } from "./CodeBlock.js";
import { t as captionHeight } from "./sections.ui.js";
import { a as sourcePath, c as prettySize, l as sourceIcon } from "./files.js";
import { t as _sfc_main$5 } from "./AppDialog.js";
import { t as describe$1 } from "./confirmation.ui.js";
import { w as captionedSwitch } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/files/object_checkin.ui.mjs
function modeChoice(model, width, language) {
	const tr = (text, values) => translate(text, language, values), compact = width < 360, headingHeight = model.inline ? 26 : 64, columns = compact || model.inline ? 2 : 3, gap = 8, cell = (width - gap * (columns - 1)) / columns, children = [label("multiFileCheckinQuestion", rect(0, 0, width, headingHeight), model.inline ? tr("Check in multiple files?") : tr("{count} files selected. Check in one group or separately in sequence?", { count: model.count }), { wrap: true })], choices = [[
		"group",
		"One group",
		"multiFileCheckinGroupButton"
	], [
		"individual",
		"Separately",
		"multiFileCheckinSeparateButton"
	]];
	if (!model.inline) choices.push([
		"cancel",
		"Cancel",
		"multiFileCheckinCancelButton"
	]);
	choices.forEach(([value, title, id], index) => children.push(button(id, rect(index < columns ? index * (cell + gap) : 0, headingHeight + 10 + Math.floor(index / columns) * 46, index >= columns ? width : cell, 38), tr(title), "", {
		type: "mode",
		value
	}, !model.busy, { highlighted: value === (model.mode || "group") })));
	return {
		height: headingHeight + 10 + Math.ceil(choices.length / columns) * 46,
		nodes: children
	};
}
function revision(model, width, height, language) {
	return describe$1({
		message: translate("The file stored in this revision will be replaced. Use Save snapshot when you need a new version.", language),
		accept: "Replace revision",
		destructive: true,
		busy: !!model.busy,
		acceptId: "revisionCheckinAccept",
		rejectId: "revisionCheckinCancel"
	}, width, height, language);
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language), margin = 10, inner = Math.max(0, width - 20 - 16), nodes = [], body = [], footerHeight = width < 370 ? 96 : 52;
	const canChoose = !model.busy && (!model.append || !!model.ready) && !model.appendUncertain;
	let y = 0;
	if (model.append) nodes.push(node("Box", "snapshotAppendSurface", rect(0, 0, width, height), {
		background: "surfaceContainerHigh",
		radius: 0
	}));
	function notice(id, text, error) {
		if (!text) return;
		const h = Math.max(40, captionHeight(text, inner - 20) * 1.2 + 16);
		body.push(node("Box", id, rect(0, y, inner, h), {
			background: error ? "errorContainer" : "surfaceContainerLow",
			radius: 12,
			children: [label(id + "Text", rect(10, 8, inner - 20, h - 16), text, {
				wrap: true,
				color: error ? "error" : "secondaryText",
				role: error ? "alert" : "status"
			})]
		}));
		y += h + 8;
	}
	if (model.busy) notice("objectCheckinBusy", tr("Loading data…"), false);
	notice("objectCheckinError", model.error, true);
	if (model.appendUncertain) notice("objectCheckinUnknown", tr("The attachment result is unknown. Close this window and refresh the snapshot before retrying."), true);
	if (model.revision) notice("objectCheckinRevisionNotice", tr("The file stored in this revision will be replaced. Use Save snapshot when you need a new version."), false);
	const fields = [];
	if (!model.revision && !model.append) fields.push({
		field: "repositoryAlias",
		title: "Repository",
		kind: "Choice",
		value: model.repositoryAlias,
		options: model.repositories
	});
	if (!model.preview) fields.push({
		field: "process",
		title: "Process",
		kind: "Choice",
		value: model.process,
		options: model.processes,
		readOnly: model.revision || model.append
	}, {
		field: "context",
		title: "Context",
		kind: "Field",
		text: model.context,
		readOnly: model.revision || model.append
	});
	if (model.append) fields.push({
		field: "fileType",
		title: "File type",
		kind: "Field",
		text: model.fileType ?? "attachment"
	});
	const columns = inner >= 650 ? 2 : 1, cellWidth = (inner - (columns - 1) * 12) / columns;
	fields.forEach((field, index) => {
		const x = index % columns * (cellWidth + 12), top = y + Math.floor(index / columns) * 72;
		body.push(label("objectCheckinLabel_" + field.field, rect(x, top, cellWidth, 22), tr(field.title), {
			fontRole: "secondary",
			color: "secondaryText"
		}));
		body.push(node(field.kind, "objectCheckinField_" + field.field, rect(x, top + 26, cellWidth, 36), {
			label: tr(field.title),
			text: field.text,
			value: field.value,
			options: field.options,
			enabled: !model.busy && !field.readOnly,
			maxLength: field.field === "context" ? 256 : field.field === "fileType" ? 128 : void 0,
			action: {
				type: "field",
				field: field.field
			}
		}));
	});
	y += Math.ceil(fields.length / columns) * 72;
	if (!model.append) {
		body.push(label("objectCheckinDescriptionLabel", rect(0, y, inner, 22), tr("Description"), {
			fontRole: "secondary",
			color: "secondaryText"
		}));
		body.push(node("Area", "objectCheckinDescription", rect(0, y + 26, inner, 72), {
			label: tr("Description"),
			text: model.description || "",
			enabled: !model.busy,
			action: {
				type: "field",
				field: "description"
			}
		}));
		y += 108;
	}
	const compact = inner < 420, chooseWidth = compact ? inner - 44 : Math.min(260, inner - 150);
	body.push(button("objectCheckinChooseFiles", rect(0, y, chooseWidth, 38), tr("Choose files for check-in"), "upload", { type: "choose" }, canChoose));
	body.push(button("objectCheckinClipboard", rect(chooseWidth + 8, y, compact ? 36 : Math.max(0, inner - chooseWidth - 8), 38), tr("Save from Clipboard"), "clipboard", { type: "clipboard" }, canChoose, { iconOnly: compact }));
	y += 48;
	const listHeight = model.count ? Math.min(220, model.count * 44) : 54;
	body.push(node("List", "objectCheckinFiles", rect(0, y, inner, listHeight), {
		source: "files",
		keyField: "key",
		rowHeight: 44,
		rowGap: 2,
		label: tr("Source files"),
		fields: [
			"key",
			"index",
			"path",
			"title",
			"size",
			"canRemove"
		]
	}));
	if (!model.count) body.push(label("objectCheckinFilesEmpty", rect(8, y + 2, inner - 24, 46), tr("Drop files here, paste an image, or choose files for check-in."), {
		wrap: true,
		color: "secondaryText",
		fontRole: "secondary"
	}));
	y += listHeight + 12;
	if (model.count > 1 && !model.append) {
		const choices = modeChoice({
			inline: true,
			mode: model.mode,
			busy: model.busy
		}, inner, language);
		body.push(node("Box", "objectCheckinModeChoice", rect(0, y, inner, choices.height), { children: choices.nodes }));
		y += choices.height + 8;
	}
	body.push(captionedSwitch("objectCheckinKeepName", rect(0, y, inner, 36), {
		text: tr("Keep original file names"),
		checked: !!model.keepFileName,
		enabled: !model.busy,
		action: {
			type: "field",
			field: "keepFileName"
		}
	}));
	y += 46;
	if (model.discard) {
		notice("objectCheckinDiscardNotice", tr("Discard unsaved changes?"), false);
		const w = (inner - 8) / 2;
		body.push(button("objectCheckinContinue", rect(0, y, w, 38), tr("Continue editing"), "", { type: "continue" }, !model.busy));
		body.push(button("objectCheckinDiscard", rect(w + 8, y, w, 38), tr("Discard"), "", { type: "discard" }, !model.busy, { destructive: true }));
		y += 48;
	}
	nodes.push(node("Scroll", "objectCheckinBody", rect(margin, margin, width - 20, Math.max(0, height - footerHeight - margin - 8)), {
		contentHeight: y,
		scrollbarId: "objectCheckinBodyScrollBar",
		children: body
	}));
	const stacked = width < 370, buttonWidth = stacked ? width - 20 : 96, buttonY = height - footerHeight + 6;
	nodes.push(button("objectCheckinCancel", rect(margin, buttonY, buttonWidth, 38), tr("Cancel"), "", { type: "close" }, !model.busy));
	nodes.push(button("objectCheckinSubmit", rect(stacked ? margin : margin + buttonWidth + 8, buttonY + (stacked ? 46 : 0), stacked ? buttonWidth : width - 20 - buttonWidth - 8, 38), tr(model.append ? "Attach files" : "Add to Commit Queue"), "save", { type: "submit" }, !!model.ready && !model.busy && !model.appendUncertain && model.count > 0 && !!(String(model.context || "").trim() || model.process) && (!model.revision || !!model.confirmed) && (model.append || !!model.hasQueue), { highlighted: true }));
	return { nodes };
}
function fileRow(record, width, language) {
	return { nodes: [node("Box", "objectCheckinFile_" + record.key, rect(0, 0, width, 42), {
		background: "surfaceContainerLow",
		radius: 10,
		children: [
			node("Icon", "objectCheckinFileIcon_" + record.key, rect(8, 12, 18, 18), {
				icon: sourceIcon(record.path),
				color: "action"
			}),
			label("objectCheckinFileName_" + record.key, rect(34, 3, Math.max(0, width - 72), 20), record.title, {
				toolTip: record.path,
				elideMiddle: true
			}),
			label("objectCheckinFileSize_" + record.key, rect(34, 24, Math.max(0, width - 72), 15), prettySize(record.size), {
				fontRole: "caption",
				color: "secondaryText"
			}),
			button("objectCheckinFileRemove_" + record.key, rect(width - 34, 7, 28, 28), translate("Remove file", language), "close", {
				type: "removeFile",
				index: record.index,
				path: record.path
			}, !!record.canRemove, {
				iconOnly: true,
				iconAction: true
			})
		]
	})] };
}
//#endregion
//#region src/features/checkin/ObjectCheckinForm.vue
var _hoisted_1$1 = ["aria-busy"];
//#endregion
//#region src/features/checkin/ObjectCheckin.vue
var _sfc_main = {
	components: {
		AppButton: _sfc_main$3,
		ObjectCheckinForm: {
			__name: "ObjectCheckinForm",
			props: {
				model: Object,
				files: Array
			},
			emits: ["event"],
			setup(__props, { emit: __emit }) {
				const props = __props;
				const emit = __emit;
				const host = ref(null), viewport = ref({
					width: 680,
					height: 650
				});
				const rows = computed(() => props.files.map((file, index) => ({
					key: String(index),
					index,
					path: sourcePath(file),
					title: file.name,
					size: file.size,
					canRemove: !props.model.busy
				})));
				const scene = computed(() => describe(props.model, viewport.value.width, viewport.value.height, appearance.language));
				const describeRow = (list, record) => fileRow(record, list.width - 16, appearance.language);
				let observer;
				onMounted(() => {
					observer = observeFrameSizes((entries) => {
						const box = entries.at(-1).contentRect;
						if (box.width > 0 && box.height > 0) viewport.value = {
							width: box.width,
							height: box.height
						};
					});
					observer.observe(host.value);
				});
				onBeforeUnmount(() => observer?.disconnect());
				return (_ctx, _cache) => {
					return openBlock(), createElementBlock("div", {
						ref_key: "host",
						ref: host,
						class: "object-checkin-workspace",
						"aria-busy": __props.model.busy
					}, [createVNode(_sfc_main$4, {
						scene: scene.value,
						models: { files: rows.value },
						"describe-row": describeRow,
						onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
					}, null, 8, ["scene", "models"])], 8, _hoisted_1$1);
				};
			}
		},
		ObjectRevisionConfirmation: {
			__name: "ObjectRevisionConfirmation",
			props: { busy: Boolean },
			emits: ["event"],
			setup(__props, { expose: __expose, emit: __emit }) {
				const props = __props;
				const emit = __emit;
				const dialog = ref(null), host = ref(null), viewport = ref({
					width: 440,
					height: 170
				});
				const scene = computed(() => revision({ busy: props.busy }, viewport.value.width, viewport.value.height, appearance.language));
				let observer;
				onMounted(() => {
					observer = observeFrameSizes((entries) => {
						const box = entries.at(-1).contentRect;
						if (box.width > 0 && box.height > 0) viewport.value = {
							width: box.width,
							height: box.height
						};
					});
					observer.observe(host.value);
				});
				onBeforeUnmount(() => observer?.disconnect());
				__expose({
					show: (owner) => dialog.value.show(owner),
					close: () => dialog.value.close()
				});
				return (_ctx, _cache) => {
					return openBlock(), createBlock(_sfc_main$5, {
						ref_key: "dialog",
						ref: dialog,
						class: "object-revision-confirmation",
						title: "Replace snapshot revision?",
						"close-on-escape": false,
						"close-on-outside": false
					}, {
						default: withCtx(() => [createBaseVNode("div", {
							ref_key: "host",
							ref: host,
							class: "object-revision-confirmation-content"
						}, [createVNode(_sfc_main$4, {
							scene: scene.value,
							onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
						}, null, 8, ["scene"])], 512)]),
						_: 1
					}, 512);
				};
			}
		}
	},
	inject: {
		queueCheckin: { default: null },
		checkinDescription: { default: () => () => "" }
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
			appendRevision: "",
			appendUploadDirectory: "",
			fileType: "attachment",
			appendUncertain: false,
			existingFiles: [],
			keepFileName: false,
			repositories: [],
			repositoryAlias: "default",
			ready: false,
			busy: false,
			error: "",
			discard: false,
			request: 0,
			pickerRequest: 0
		};
	},
	emits: ["attached"],
	watch: {
		busy(value) {
			if (!value && this.ready && this.revision && !this.confirmed) {
				const request = this.request;
				nextTick(() => {
					if (request === this.request && this.ready) this.$refs.revisionDialog.show(this.$refs.dialog);
				});
			}
		},
		ticket() {
			this.reset();
		},
		project() {
			this.reset();
		}
	},
	computed: {
		appendStyle() {
			return this.appendSnapshot ? { "--append-header-height": controls.dialog.headerHeight + "px" } : null;
		},
		frameModel() {
			return {
				preview: this.preview,
				revision: this.revision,
				append: !!this.appendSnapshot,
				ready: this.ready,
				busy: this.busy,
				error: t(this.error),
				appendUncertain: this.appendUncertain,
				count: this.files.length,
				repositoryAlias: this.repositoryAlias,
				repositories: this.repositories,
				process: this.process,
				context: this.context,
				processes: this.processes,
				description: this.description,
				mode: this.mode,
				keepFileName: this.keepFileName,
				fileType: this.fileType,
				confirmed: this.confirmed,
				discard: this.discard,
				hasQueue: !!this.queueCheckin
			};
		},
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
		dispatch(action) {
			if (action.type === "close") this.close();
			else if (action.type === "continue") this.discard = false;
			else if (action.type === "discard" && !this.busy) this.close(true);
			else if (action.type === "submit") this.submit();
			else if (!this.busy) {
				if (action.type === "choose") {
					this.pickerRequest = this.request;
					this.$refs.fileInput.click();
				} else if (action.type === "clipboard") this.readImage();
				else if (action.type === "mode" && ["group", "individual"].includes(action.value)) this.mode = action.value;
				else if (action.type === "removeFile") {
					const file = this.files[action.index];
					if (file && sourcePath(file) === action.path) this.files.splice(action.index, 1);
				} else if (action.type === "field" && [
					"repositoryAlias",
					"process",
					"context",
					"description",
					"fileType",
					"keepFileName"
				].includes(action.field)) {
					this[action.field] = action.value;
					if (action.field === "process") this.context = "";
				}
			}
		},
		resolveRevision(action) {
			if (this.busy || !this.ready) return;
			if (action.type === "accept") {
				this.confirmed = true;
				this.$refs.revisionDialog.close();
			} else this.close(true);
		},
		beforeUnload(event) {
			if (this.files.length) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		reset() {
			this.request++;
			this.ready = false;
			this.$refs.revisionDialog?.close();
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
			this.pickerRequest = request;
			this.scope = {
				ticket: this.ticket,
				project: this.project
			};
			this.owner = record;
			this.files = [];
			this.processes = [];
			this.error = "";
			this.discard = false;
			this.appendSnapshot = options.append ? {} : null;
			this.appendRevision = "";
			this.appendUploadDirectory = "";
			this.fileType = "attachment";
			this.appendUncertain = false;
			this.existingFiles = [];
			this.repositories = [];
			this.repositoryAlias = preferences.repository.defaultAlias;
			this.description = this.checkinDescription();
			this.mode = preferences.checkin.groupCheckin ? "group" : "individual";
			this.keepFileName = options.append ? false : preferences.checkin.keepFilename;
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
				if (options.append) {
					const response = await rpc("execute_cmd", [
						this.scope,
						"tactic.ui.table.TableSnapshotAppendCmd",
						{ search_key: record.__search_key__ }
					]);
					if (request !== this.request) return;
					const prepared = response.info;
					this.owner = {
						__search_key__: prepared.ownerKey,
						name: prepared.ownerTitle
					};
					this.appendSnapshot = {
						code: prepared.snapshotCode,
						__search_key__: prepared.searchKey,
						version: prepared.version
					};
					this.appendRevision = prepared.expectedRevision;
					this.appendUploadDirectory = prepared.uploadDirectory;
					this.existingFiles = prepared.existingNames.map((filename) => ({ filename }));
					this.process = prepared.process;
					this.context = prepared.context;
					this.processes = [{
						value: prepared.process,
						label: prepared.process
					}];
					this.ready = true;
					return;
				}
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
			if (this.appendSnapshot) {
				if (!this.ready || this.busy || this.appendUncertain) return;
				if (this.files.length + incoming.length > 50) {
					this.error = "Choose between one and 50 files";
					return;
				}
			}
			if (incoming.some((file) => this.preview && !file.type.startsWith("image/"))) {
				this.error = "Choose an image for the preview";
				return;
			}
			this.files.push(...incoming);
			this.error = "";
		},
		drop(event) {
			if (this.busy) return;
			if (this.appendSnapshot && [...event.dataTransfer.items || []].some((item) => item.webkitGetAsEntry?.()?.isDirectory)) {
				this.error = "Choose files, not directories";
				return;
			}
			this.addFiles(event.dataTransfer.files);
		},
		clipboardFiles(files) {
			return [...files].map((file) => {
				if (!this.appendSnapshot || !file.type.startsWith("image/")) return file;
				const identity = globalThis.crypto?.randomUUID?.() || Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
				return new File([file], "clipboard-" + identity + "." + (file.type.split("/")[1] || "png"), { type: file.type });
			});
		},
		paste(event) {
			if (!this.busy && event.clipboardData?.files.length) {
				event.preventDefault();
				this.addFiles(this.clipboardFiles(event.clipboardData.files));
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
				if (!files.length) throw new Error("The clipboard does not contain an image");
				this.addFiles(this.clipboardFiles(files));
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
			const fileType = this.fileType.trim();
			if (!fileType || fileType.length > 128 || /[\u0000-\u001f]/.test(fileType)) {
				this.error = "Choose a valid file type";
				return;
			}
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
					paths.push(await uploadFormFile(scope.ticket, scope.project, file, { subdir: this.appendUploadDirectory }));
					if (request !== this.request) return;
				}
				committing = true;
				const response = await rpc("execute_cmd", [
					scope,
					"tactic.ui.table.TableSnapshotAppendCmd",
					{
						action: "save",
						search_key: this.appendSnapshot.__search_key__,
						expected_revision: this.appendRevision,
						upload_directory: this.appendUploadDirectory,
						filenames: paths,
						file_type: fileType,
						keep_file_name: !!this.keepFileName
					}
				]);
				if (request !== this.request) return;
				if (response.info?.state !== "saved" || response.info?.searchKey !== this.appendSnapshot.__search_key__) {
					const error = /* @__PURE__ */ new Error("The attachment result is unknown. Close this window and refresh the snapshot before retrying.");
					error.status = 502;
					throw error;
				}
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
var _hoisted_2 = { key: 0 };
var _hoisted_3 = ["accept", "disabled"];
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_ObjectCheckinForm = resolveComponent("ObjectCheckinForm");
	const _component_ObjectRevisionConfirmation = resolveComponent("ObjectRevisionConfirmation");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: normalizeClass(["record-dialog object-checkin", { "snapshot-append": $data.appendSnapshot }]),
		style: normalizeStyle($options.appendStyle),
		"aria-label": $options.t($options.title),
		onCancel: _cache[3] || (_cache[3] = withModifiers(($event) => $options.close(), ["prevent"])),
		onPaste: _cache[4] || (_cache[4] = (...args) => $options.paste && $options.paste(...args)),
		onDragover: _cache[5] || (_cache[5] = withModifiers(() => {}, ["prevent"])),
		onDrop: _cache[6] || (_cache[6] = withModifiers((...args) => $options.drop && $options.drop(...args), ["prevent"]))
	}, [
		createBaseVNode("header", null, [
			$options.mobile ? (openBlock(), createBlock(_component_AppButton, {
				key: 0,
				label: "Back",
				icon: "MDI_ARROW_LEFT",
				"icon-only": "",
				onClick: _cache[0] || (_cache[0] = ($event) => $options.close())
			})) : createCommentVNode("", true),
			createBaseVNode("div", null, [createBaseVNode("h2", null, [createTextVNode(toDisplayString($options.t($options.title)), 1), $data.appendSnapshot && $data.ready ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" · " + toDisplayString($data.owner?.name) + " · v" + toDisplayString($data.appendSnapshot.version), 1)], 64)) : createCommentVNode("", true)]), !$data.appendSnapshot ? (openBlock(), createElementBlock("small", _hoisted_2, [createTextVNode(toDisplayString($data.owner?.name || $data.owner?.title || $data.owner?.code), 1), !$options.mobile ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" · " + toDisplayString($data.owner?.__search_key__), 1)], 64)) : createCommentVNode("", true)])) : createCommentVNode("", true)]),
			!$options.mobile ? (openBlock(), createBlock(_component_AppButton, {
				key: 1,
				label: "Close",
				icon: "close",
				onClick: _cache[1] || (_cache[1] = ($event) => $options.close())
			})) : createCommentVNode("", true)
		]),
		createVNode(_component_ObjectCheckinForm, {
			model: $options.frameModel,
			files: $data.files,
			onEvent: $options.dispatch
		}, null, 8, [
			"model",
			"files",
			"onEvent"
		]),
		createBaseVNode("input", {
			ref: "fileInput",
			type: "file",
			multiple: "",
			hidden: "",
			accept: $data.preview ? "image/*" : void 0,
			disabled: $data.busy,
			onChange: _cache[2] || (_cache[2] = ($event) => {
				$data.pickerRequest === $data.request && $options.addFiles($event.target.files);
				$event.target.value = "";
			})
		}, null, 40, _hoisted_3)
	], 46, _hoisted_1)), [[_directive_window, $data.appendSnapshot ? {
		type: "dialog",
		kind: "snapshot_append"
	} : false]]), createVNode(_component_ObjectRevisionConfirmation, {
		ref: "revisionDialog",
		busy: $data.busy,
		onEvent: $options.resolveRevision
	}, null, 8, ["busy", "onEvent"])]);
}
var ObjectCheckin_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ObjectCheckin_default as default };

//# sourceMappingURL=ObjectCheckin.js.map
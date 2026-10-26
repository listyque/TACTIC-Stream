import { t as __exportAll } from "./rolldown-runtime.js";
import { D as nextTick, I as resolveComponent, K as withCtx, L as resolveDirective, N as openBlock, P as renderList, Z as ref, _ as createElementBlock, b as createVNode, f as Teleport, g as createCommentVNode, h as createBlock, it as toDisplayString, j as onMounted, k as onBeforeUnmount, l as withModifiers, m as createBaseVNode, p as computed, q as withDirectives, rt as normalizeStyle, s as vShow, tt as unref, u as Fragment } from "./vue.js";
import { A as t, c as _sfc_main$2, j as appearance, ot as _plugin_vue_export_helper_default, z as controls } from "./index.js";
import { D as _sfc_main$4, E as _sfc_main$6, Gt as button, Jt as node, Kt as label, N as _sfc_main$9, O as _sfc_main$5, P as _sfc_main$8, R as _sfc_main$7, Vt as notify, Yt as rect, ct as rpc, i as _sfc_main$3, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { t as _sfc_main$10 } from "./ObjectFieldFrame.js";
import { t as captionHeight } from "./sections.ui.js";
import { G as changeContent, J as saveDuplicateProfile, K as contentChoices, U as _sfc_main$11, W as applyDuplicateProfile, q as duplicateProfile } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/objects/duplicate.ui.mjs
var duplicate_ui_exports = /* @__PURE__ */ __exportAll({
	body: () => body,
	busyState: () => busyState,
	choices: () => choices,
	footer: () => footer,
	header: () => header,
	scrollbarExtent: () => scrollbarExtent,
	steps: () => steps,
	tabs: () => tabs
});
var scrollbarExtent = controls.scrollBar.extent;
var steps = [
	{
		label: "Fields",
		icon: "edit"
	},
	{
		label: "Relations",
		icon: "account-tree"
	},
	{
		label: "Snapshots",
		icon: "inventory-2"
	},
	{
		label: "Tasks and messages",
		icon: "task"
	},
	{
		label: "Review",
		icon: "fact-check"
	}
];
var choices = [
	{
		name: "copySnapshots",
		label: "Snapshots",
		count: "snapshotCount",
		page: 2
	},
	{
		name: "copyTasks",
		label: "Tasks",
		count: "taskCount",
		page: 3
	},
	{
		name: "copyProcessMessages",
		label: "Process messages",
		count: "processMessageCount",
		page: 3
	},
	{
		name: "copyProcessAttachments",
		label: "Process attachments",
		count: "processAttachmentCount",
		page: 3
	},
	{
		name: "copyTaskMessages",
		label: "Task messages",
		count: "taskMessageCount",
		page: 3
	},
	{
		name: "copyTaskAttachments",
		label: "Task attachments",
		count: "taskAttachmentCount",
		page: 3
	}
];
function busyState(model, language) {
	return model.busy || model.saving ? {
		message: translate(model.saving ? "Creating duplicate on the server… You can continue working." : "Analyzing fields, relations and process content…", language),
		cancellable: !model.saving
	} : null;
}
function header(model, width, language) {
	const tr = (text) => translate(text, language), narrow = width < 700;
	const badgeWidth = narrow ? 0 : 132, right = 48 + badgeWidth;
	return {
		height: 68,
		nodes: [
			node("Box", "duplicateSObjectHeader", rect(0, 0, width, 68), {
				background: "surfaceContainer",
				radiusRole: "sectionRadius"
			}),
			node("Box", "duplicateIconSurface", rect(12, 13, 42, 42), {
				background: "surfaceContainerHigh",
				children: [node("Icon", "duplicateIcon", rect(10, 10, 22, 22), {
					icon: "control-point-duplicate",
					color: "action"
				})]
			}),
			label("duplicateTitle", rect(65, 12, Math.max(0, width - 65 - right), 24), tr("Duplicate") + " " + (model.title || tr("sObject")), {
				fontRole: "bodyLarge",
				weight: 600
			}),
			label("duplicateSearchType", rect(65, 38, Math.max(0, width - 65 - right), 18), model.searchType || "", {
				fontRole: "caption",
				color: "secondaryText",
				elideMiddle: true
			}),
			...narrow ? [] : [node("StatusChip", "duplicateStepCount", rect(width - right, 22, badgeWidth - 8, 24), {
				text: translate("Step {step} of 5", language, { step: model.step + 1 }),
				icon: steps[model.step].icon,
				accent: "action"
			})],
			button("duplicateHelp", rect(width - 42, 18, 32, 32), tr("Duplication help"), "help", { type: "help" }, true, {
				iconOnly: true,
				iconAction: true
			})
		]
	};
}
function tabs(model, width, language) {
	const cell = Math.max(0, (width - 16) / 5);
	return {
		height: 36,
		nodes: [node("Box", "duplicateStepSurface", rect(0, 0, width, 36), {
			background: "surfaceContainerHigh",
			radius: 8
		}), ...steps.map((step, index) => button("duplicateStep_" + index, rect(4 + index * (cell + 2), 2, cell, 32), translate(step.label, language), step.icon, {
			type: "step",
			value: index
		}, !model.busy && !model.saving, {
			radio: true,
			selected: model.step === index,
			iconOnly: width < 600,
			iconSize: 16
		}))]
	};
}
function footer(model, width, language) {
	const tr = (text) => translate(text, language), narrow = width < 680, height = narrow ? 104 : 64;
	const nodes = [node("Box", "duplicateSObjectFooter", rect(0, 0, width, height), { background: "surfaceContainer" })];
	if (model.ready) nodes.push(node("CheckBox", "duplicateRememberSettings", rect(13, 10, narrow ? width - 26 : Math.max(80, width - 398), 36), {
		label: tr("Remember choices"),
		text: tr(width < 1e3 ? "Remember" : "Remember for this Search Type"),
		checked: model.remember,
		enabled: !model.saving,
		action: { type: "remember" }
	}));
	const actions = [
		[
			"cancel",
			"Cancel",
			"",
			true
		],
		...model.ready && model.step > 0 ? [[
			"back",
			"Back",
			"arrow-back",
			!model.busy && !model.saving
		]] : [],
		...model.ready && model.step < 4 ? [[
			"next",
			"Next",
			"arrow-forward",
			!model.busy && !model.saving
		]] : [],
		[
			"duplicate",
			"Duplicate",
			"control-point-duplicate",
			model.ready && !model.busy && !model.saving && !model.uncertain && model.valid !== false
		]
	];
	const gap = 6, available = width - 26;
	const widths = actions.map(([type]) => narrow ? Math.max(0, (available - gap * (actions.length - 1)) / actions.length) : type === "duplicate" ? 110 : type === "cancel" ? 72 : 36);
	const start = width - 13 - widths.reduce((sum, w) => sum + w, 0) - gap * (actions.length - 1);
	actions.forEach(([type, text, icon, enabled], index) => nodes.push(button("duplicate_" + type, rect(start + widths.slice(0, index).reduce((sum, w) => sum + w + gap, 0), narrow ? 58 : 14, widths[index], 36), tr(text), icon, { type }, enabled && (type !== "cancel" || !model.saving), {
		highlighted: type === "duplicate",
		iconSize: 16,
		iconOnly: !narrow && ["back", "next"].includes(type)
	})));
	return {
		height,
		nodes
	};
}
function body(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	let y = 0;
	function paragraph(id, text, icon, background = "surfaceContainerLow") {
		const h = Math.max(44, captionHeight(text, Math.max(1, width - (icon ? 62 : 28))) + 24);
		nodes.push(node("Box", id, rect(0, y, width, h), {
			background,
			children: [...icon ? [node("Icon", id + "Icon", rect(12, (h - 18) / 2, 18, 18), {
				icon,
				color: "action"
			})] : [], label(id + "Text", rect(icon ? 40 : 14, 12, Math.max(0, width - (icon ? 54 : 28)), h - 24), text, {
				wrap: true,
				color: "secondaryText"
			})]
		}));
		y += h + 10;
	}
	function intro(id, text) {
		const h = captionHeight(text, Math.max(1, width));
		nodes.push(label(id + "Text", rect(0, y, width, h), text, {
			wrap: true,
			color: "secondaryText"
		}));
		y += h + 8;
	}
	if (model.error) {
		paragraph("duplicateError", tr(model.error), "warning", "errorContainer");
		if (!model.uncertain) {
			nodes.push(button("duplicateRetry", rect(0, y, 120, 36), tr(model.ready ? "Analyze again" : "Retry"), "refresh", { type: "retry" }, !model.busy));
			y += 46;
		}
	}
	if (!model.ready) return {
		height: Math.max(0, y - 10),
		nodes
	};
	if (model.step === 0) paragraph("duplicateFieldIntro", tr("Edit the values of the new object. Identity, project and relationship columns are generated or managed automatically."), "edit");
	else if (model.step === 1) {
		intro("duplicateRelationIntro", tr("Choose what happens to each relationship already attached to the source object."));
		(model.relations || []).forEach((record, index) => {
			const children = [
				node("Box", "relationIconSurface", rect(11, 11, 34, 34), {
					background: "surfaceContainerHigh",
					children: [node("Icon", "relationIcon", rect(8, 8, 18, 18), {
						icon: record.kind === "instance" ? "hub" : record.kind === "parent" ? "arrow-upward" : "arrow-downward",
						color: "action"
					})]
				}),
				label("relationTitle", rect(55, 11, Math.max(0, width - 66), 20), record.title, { weight: 600 }),
				label("relationDetails", rect(55, 32, Math.max(0, width - 66), 17), tr(record.kind === "instance" ? "Instance links" : record.kind === "parent" ? "Parent" : "Children") + " · " + record.count + (record.path ? " · " + record.path : ""), {
					fontRole: "caption",
					color: "secondaryText"
				})
			];
			const options = record.options || [], cell = Math.max(0, (width - 22 - 6 * (options.length - 1)) / Math.max(1, options.length));
			options.forEach((option, i) => children.push(button("duplicateRelationMode_" + index + "_" + i, rect(11 + i * (cell + 6), 58, cell, 36), tr(option.label), "", {
				type: "relation",
				index,
				key: record.key,
				value: option.value
			}, !model.saving, {
				radio: true,
				selected: record.mode === option.value
			})));
			const text = (record.items || []).map((item) => item.title).join("  ·  ");
			if (text) children.push(label("relationItems", rect(11, 102, width - 22, 18), text, {
				fontRole: "caption",
				color: "secondaryText",
				tooltip: text
			}));
			const height = text ? 131 : 105;
			nodes.push(node("Box", "duplicateRelation_" + index, rect(0, y, width, height), {
				background: "surfaceContainer",
				radiusRole: "sectionRadius",
				children
			}));
			y += height + 8;
		});
		if (!(model.relations || []).length) paragraph("duplicateRelationsEmpty", tr("No linked objects"), "link-off");
	} else if (model.step === 2 || model.step === 3) {
		intro("duplicateContentIntro", tr(model.step === 2 ? "Choose current snapshots and files to duplicate for each process. Message attachments are handled with their messages on the next step." : "Choose tasks, process messages, task messages, and their attached files. Copying task messages also copies their parent tasks."));
		let count = 0;
		(model.processes || []).forEach((record, index) => {
			const available = choices.filter((choice) => choice.page === model.step && record[choice.count]);
			if (!available.length) return;
			count++;
			const children = [node("Icon", "processIcon", rect(16, 18, 20, 20), {
				icon: "account-tree",
				color: "action"
			}), label("processTitle", rect(47, 12, Math.max(0, width - 60), 24), record.name, { weight: 600 })];
			children.push(node("StatusChip", "processCount", rect(Math.max(47, width - 106), 10, 94, 24), {
				icon: "inventory-2",
				text: translate("{count} items", language, { count: model.step === 2 ? record.snapshotCount : Number(record.taskCount || 0) + Number(record.processMessageCount || 0) + Number(record.taskMessageCount || 0) }),
				accent: "secondaryText"
			}));
			let top = 42, left = 11;
			available.forEach((choice) => {
				const text = tr(choice.label) + " " + record[choice.count] + (choice.name === "copySnapshots" ? " · " + tr("Files") + " " + record.fileCount : "");
				const w = Math.min(Math.max(0, width - 22), text.length * 6.5 + 32);
				if (left > 11 && left + w > width - 11) {
					left = 11;
					top += 36;
				}
				children.push(node("CheckBox", "duplicateChoice_" + index + "_" + choice.name, rect(left, top, w, 32), {
					label: tr(choice.label),
					text,
					checked: !!record[choice.name],
					enabled: !model.saving,
					action: {
						type: "choice",
						index,
						name: choice.name
					}
				}));
				left += w + 8;
			});
			top += 32;
			nodes.push(node("Box", "duplicateProcess_" + index, rect(0, y, width, top + 7), {
				background: "surfaceContainer",
				radiusRole: "sectionRadius",
				children
			}));
			y += top + 15;
		});
		if (!count) paragraph("duplicateContentEmpty", tr(model.step === 2 ? "No current snapshots" : "No tasks or messages"), "inventory-2");
	} else {
		const totals = model.totals || {}, columns = width >= 600 ? 4 : 2, cell = (width - 28 - 7 * (columns - 1)) / columns;
		const text = tr("The new object receives the edited fields. Selected links are recreated; original instance targets are never duplicated."), textHeight = captionHeight(text, Math.max(1, width - 28));
		const top = 92 + textHeight, height = top + Math.ceil(4 / columns) * 36 + 14;
		const children = [
			node("Icon", "duplicateReviewIcon", rect((width - 34) / 2, 14, 34, 34), {
				icon: "control-point-duplicate",
				color: "action"
			}),
			label("duplicateReviewTitle", rect(14, 58, width - 28, 25), tr("Ready to create the duplicate"), {
				fontRole: "bodyLarge",
				weight: 600,
				align: "center"
			}),
			label("duplicateReviewExplanation", rect(14, 88, width - 28, textHeight), text, {
				color: "secondaryText",
				wrap: true,
				align: "center"
			})
		];
		[
			["Related", totals.related],
			["Snapshots", totals.snapshots],
			["Tasks", totals.tasks],
			["Messages and files", totals.messages]
		].forEach(([text, count], i) => children.push(node("SummaryChip", "duplicateTotal_" + i, rect(14 + i % columns * (cell + 7), top + Math.floor(i / columns) * 36, cell, 28), {
			text: tr(text),
			count: count || 0,
			showCount: true,
			accent: "action"
		})));
		nodes.push(node("Box", "duplicateReview", rect(0, y, width, height), {
			background: "surfaceContainer",
			children
		}));
		y += height + 10;
		paragraph("duplicateQuickChoice", tr(model.remember ? "These choices will enable Quick duplicate for this Search Type." : "These choices will be used only once."), "bolt");
	}
	return {
		height: Math.max(0, y - 10),
		nodes
	};
}
//#endregion
//#region src/features/objects/ObjectDuplicateSurface.vue
var _hoisted_1$1 = ["role", "aria-label"];
//#endregion
//#region src/features/objects/DuplicateSObject.vue
var _sfc_main = {
	components: {
		ContentLoadingOverlay: _sfc_main$11,
		ObjectDuplicateSurface: {
			__name: "ObjectDuplicateSurface",
			props: {
				model: Object,
				part: {
					type: String,
					default: "body"
				}
			},
			emits: ["event"],
			setup(__props, { emit: __emit }) {
				const props = __props;
				const emit = __emit;
				const host = ref(null), width = ref(0);
				const scene = computed(() => duplicate_ui_exports[props.part](props.model, width.value, appearance.language));
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
					return openBlock(), createElementBlock("section", {
						ref_key: "host",
						ref: host,
						class: "object-duplicate-surface",
						role: __props.part === "tabs" ? "radiogroup" : void 0,
						"aria-label": __props.part === "tabs" ? unref(t)("Duplicate steps") : void 0,
						style: normalizeStyle({ height: scene.value.height + "px" })
					}, [createVNode(_sfc_main$3, {
						scene: scene.value,
						onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
					}, null, 8, ["scene"])], 12, _hoisted_1$1);
				};
			}
		},
		ObjectFieldFrame: _sfc_main$10,
		AppTextArea: _sfc_main$4,
		AppDateField: _sfc_main$5,
		AppButton: _sfc_main$2,
		AppCheckbox: _sfc_main$6,
		AppSelect: _sfc_main$7,
		AppTextField: _sfc_main$8,
		AppColorInput: _sfc_main$9
	},
	inject: {
		openHelp: {},
		currentLogin: { default: () => () => "" }
	},
	props: {
		ticket: String,
		project: String
	},
	emits: ["completed"],
	data() {
		return {
			analysis: null,
			draft: {},
			baseline: "",
			scope: null,
			sourceKey: "",
			sourceType: "",
			owner: "",
			revision: "",
			step: 0,
			remember: true,
			busy: false,
			saving: false,
			uncertain: false,
			error: "",
			discard: false,
			request: 0,
			quick: false
		};
	},
	computed: {
		presentation() {
			return {
				title: this.analysis?.title,
				searchType: this.analysis?.searchType || this.sourceType,
				step: this.step,
				ready: !!this.analysis,
				busy: this.busy,
				saving: this.saving,
				uncertain: this.uncertain,
				valid: this.valid,
				error: this.error,
				remember: this.remember,
				relations: this.analysis?.relations || [],
				processes: this.analysis?.processes || [],
				totals: this.totals
			};
		},
		busyPresentation() {
			return busyState(this.presentation, appearance.language);
		},
		dirty() {
			return !!this.analysis && JSON.stringify(this.options()) !== this.baseline;
		},
		valid() {
			return this.scope?.ticket === this.ticket && this.scope?.project === this.project;
		},
		totals() {
			const result = {
				related: 0,
				snapshots: 0,
				tasks: 0,
				messages: 0
			};
			for (const relation of this.analysis?.relations || []) if (relation.mode !== "none") result.related += relation.count;
			for (const process of this.analysis?.processes || []) {
				if (process.copySnapshots) result.snapshots += process.snapshotCount;
				if (process.copyTasks) result.tasks += process.taskCount;
				if (process.copyProcessMessages) result.messages += process.processMessageCount;
				if (process.copyTaskMessages) result.messages += process.taskMessageCount;
				if (process.copyProcessAttachments) result.messages += process.processAttachmentCount;
				if (process.copyTaskAttachments) result.messages += process.taskAttachmentCount;
			}
			return result;
		}
	},
	watch: {
		ticket() {
			this.invalidate();
		},
		project() {
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
		action(event) {
			if (event.type === "step") this.step = event.value;
			else if (event.type === "remember") this.remember = event.value;
			else if (event.type === "relation") this.analysis.relations[event.index].mode = event.value;
			else if (event.type === "choice") this.changeContent(this.analysis.processes[event.index], event.name, event.value);
			else if (event.type === "back") this.step--;
			else if (event.type === "next") this.step++;
			else if (event.type === "duplicate") this.duplicate();
			else if (event.type === "retry") this.analyze();
			else if (event.type === "cancel") this.close();
			else if (event.type === "help") this.openHelp("duplicating_objects");
		},
		changeContent,
		beforeUnload(event) {
			if (this.$refs.dialog?.open && (this.dirty || this.saving || this.uncertain)) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		invalidate() {
			this.request++;
			this.busy = this.saving = false;
			if (this.$refs.dialog?.open) this.error = "Connection context changed. Close this form and reopen it before saving.";
		},
		async open(record, quick = false) {
			if (this.$refs.dialog.open) {
				this.$refs.dialog.show();
				return;
			}
			this.scope = {
				ticket: this.ticket,
				project: this.project,
				language: "python"
			};
			this.sourceKey = record.__search_key__;
			this.sourceType = record.__search_key__.split("?")[0];
			this.owner = this.currentLogin();
			this.analysis = null;
			this.draft = {};
			this.revision = "";
			this.step = 0;
			this.quick = quick;
			this.error = "";
			this.uncertain = this.discard = false;
			await nextTick();
			this.$refs.dialog.show();
			await this.analyze();
			if (quick && this.analysis && !this.error && this.valid) await this.duplicate();
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				this.scope,
				"tactic.command.sobject_duplicate_cmd.SObjectDuplicateCmd",
				{
					action,
					search_key: this.sourceKey,
					...values
				}
			])).info;
		},
		async analyze() {
			if (!this.valid || this.saving || this.uncertain) return;
			const request = ++this.request, previous = this.analysis ? this.options() : null;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("analyze");
				if (request !== this.request) return;
				const profile = duplicateProfile(this.owner, this.scope.project, this.sourceType);
				if (this.quick && !profile) throw new Error("Open Duplicate… once to save choices for this Search Type.");
				applyDuplicateProfile(result.analysis, previous || profile);
				this.analysis = result.analysis;
				this.revision = result.revision;
				this.draft = Object.fromEntries(this.analysis.fields.map((field) => [field.name, previous?.fields?.[field.name] ?? (this.fieldKind(field) === "checkbox" ? [
					"True",
					"true",
					"1",
					"on"
				].includes(field.value) : String(field.widget?.input?.value ?? field.value))]));
				if (!previous) this.baseline = JSON.stringify(this.options());
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		readOnly(field) {
			return field.widget?.input?.read_only || [true, "true"].includes(field.widget?.options?.read_only);
		},
		fieldKind(field) {
			const widget = field.widget;
			if (widget?.input?.type === "hidden" || widget?.class_name?.endsWith(".HiddenWdg")) return "hidden";
			if (widget?.input?.type === "color") return "color";
			if (widget?.choices && widget.input?.type !== "multiselect") return "select";
			if (widget?.class_name?.endsWith(".CheckboxWdg") || /bool/i.test(field.dataType)) return "checkbox";
			if (field.multiline || widget?.class_name?.endsWith(".TextAreaWdg")) return "textarea";
			if (widget?.input?.type === "time") return "time";
			if (widget?.class_name?.includes("CalendarInput")) return "datetime-local";
			return /int|float|double|numeric|decimal/i.test(field.dataType) ? "number" : "text";
		},
		fieldChoices(field) {
			const widget = field.widget;
			return [...widget.input?.empty_label ? [{
				value: "",
				label: widget.input.empty_label
			}] : [], ...widget.choices.map((value, index) => ({
				value,
				label: widget.labels[index]
			}))];
		},
		pageChoices(process) {
			return choices.filter((choice) => choice.page === this.step && process[choice.count]);
		},
		options() {
			return {
				fields: Object.fromEntries((this.analysis?.fields || []).filter((field) => !this.readOnly(field)).map((field) => [field.name, this.draft[field.name]])),
				relations: Object.fromEntries((this.analysis?.relations || []).map((row) => [row.key, row.mode])),
				processes: Object.fromEntries((this.analysis?.processes || []).map((row) => [row.name, Object.fromEntries(contentChoices.map((name) => [name, row[name] === true]))]))
			};
		},
		async duplicate() {
			if (!this.analysis || this.busy || this.saving || this.uncertain || !this.valid) return;
			if (!this.$refs.fields?.checkValidity()) {
				this.step = 0;
				await nextTick();
				this.$refs.fields.reportValidity();
				return;
			}
			const request = ++this.request;
			this.saving = true;
			this.error = "";
			try {
				const options = this.options();
				if (this.remember) try {
					saveDuplicateProfile(this.owner, this.scope.project, this.sourceType, {
						relations: options.relations,
						processes: options.processes
					});
				} catch {
					const error = /* @__PURE__ */ new Error("Unable to save choices in this browser. Turn off Remember choices to continue.");
					error.status = 400;
					throw error;
				}
				const result = await this.call("duplicate", {
					options,
					revision: this.revision
				});
				if (request !== this.request) return;
				this.baseline = JSON.stringify(options);
				this.$refs.dialog.close();
				this.analysis = null;
				notify("info", "Object duplicated");
				this.$emit("completed", result.result);
			} catch (error) {
				if (request !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The result is unknown. Refresh the objects before trying again." : error.message;
			} finally {
				if (request === this.request) this.saving = false;
			}
		},
		close(force = false) {
			if (this.saving) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.discard = true;
				return;
			}
			this.request++;
			this.$refs.dialog.close();
			this.analysis = null;
			this.busy = this.uncertain = this.discard = false;
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { class: "duplicate-pages-wrapper" };
var _hoisted_3 = { class: "duplicate-pages" };
var _hoisted_4 = { class: "duplicate-page" };
var _hoisted_5 = { class: "duplicate-fields" };
var _hoisted_6 = {
	key: 6,
	class: "muted"
};
var _hoisted_7 = {
	key: 0,
	class: "notice",
	role: "alert"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_ObjectDuplicateSurface = resolveComponent("ObjectDuplicateSurface");
	const _component_AppCheckbox = resolveComponent("AppCheckbox");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_AppColorInput = resolveComponent("AppColorInput");
	const _component_AppTextArea = resolveComponent("AppTextArea");
	const _component_AppDateField = resolveComponent("AppDateField");
	const _component_AppTextField = resolveComponent("AppTextField");
	const _component_ObjectFieldFrame = resolveComponent("ObjectFieldFrame");
	const _component_ContentLoadingOverlay = resolveComponent("ContentLoadingOverlay");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog duplicate-sobject",
		"aria-label": $options.t("Duplicate object"),
		onCancel: _cache[5] || (_cache[5] = withModifiers(($event) => $options.close(), ["prevent"]))
	}, [
		createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t("Duplicate object")), 1), createVNode(_component_AppButton, {
			label: "Close",
			icon: "close",
			"icon-only": "",
			disabled: $data.saving,
			onClick: _cache[0] || (_cache[0] = ($event) => $options.close())
		}, null, 8, ["disabled"])]),
		createVNode(_component_ObjectDuplicateSurface, {
			model: $options.presentation,
			part: "header",
			onEvent: $options.action
		}, null, 8, ["model", "onEvent"]),
		createVNode(_component_ObjectDuplicateSurface, {
			model: $options.presentation,
			part: "tabs",
			onEvent: $options.action
		}, null, 8, ["model", "onEvent"]),
		createBaseVNode("div", _hoisted_2, [createBaseVNode("div", _hoisted_3, [createVNode(_component_ObjectDuplicateSurface, {
			model: $options.presentation,
			onEvent: $options.action
		}, null, 8, ["model", "onEvent"]), $data.analysis ? (openBlock(), createElementBlock("form", {
			key: 0,
			ref: "fields",
			onSubmit: _cache[1] || (_cache[1] = withModifiers((...args) => $options.duplicate && $options.duplicate(...args), ["prevent"]))
		}, [withDirectives(createBaseVNode("section", _hoisted_4, [createBaseVNode("div", _hoisted_5, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.analysis.fields.filter((field) => $options.fieldKind(field) !== "hidden"), (field) => {
			return openBlock(), createBlock(_component_ObjectFieldFrame, {
				key: field.name,
				"minimum-editor-height": $options.fieldKind(field) === "textarea" ? 112 : void 0,
				model: {
					name: field.name,
					title: field.widget?.title || field.label,
					description: field.widget?.options?.hint || field.widget?.options?.hint_text || "",
					readOnly: $options.readOnly(field),
					required: [true, "true"].includes(field.widget?.options?.required),
					icon: $options.fieldKind(field) === "textarea" ? "description" : "text-fields"
				}
			}, {
				default: withCtx(() => [$options.fieldKind(field) === "checkbox" ? (openBlock(), createBlock(_component_AppCheckbox, {
					key: 0,
					modelValue: $data.draft[field.name],
					"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
					label: field.widget?.title || field.label,
					disabled: $data.saving || $options.readOnly(field)
				}, null, 8, [
					"modelValue",
					"onUpdate:modelValue",
					"label",
					"disabled"
				])) : $options.fieldKind(field) === "select" ? (openBlock(), createBlock(_component_AppSelect, {
					key: 1,
					modelValue: $data.draft[field.name],
					"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
					options: $options.fieldChoices(field),
					label: field.widget?.title || field.label,
					"translate-labels": false,
					disabled: $data.saving || $options.readOnly(field)
				}, null, 8, [
					"modelValue",
					"onUpdate:modelValue",
					"options",
					"label",
					"disabled"
				])) : $options.fieldKind(field) === "color" ? (openBlock(), createBlock(_component_AppColorInput, {
					key: 2,
					modelValue: $data.draft[field.name],
					"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
					label: field.label,
					disabled: $data.saving || $options.readOnly(field)
				}, null, 8, [
					"modelValue",
					"onUpdate:modelValue",
					"label",
					"disabled"
				])) : $options.fieldKind(field) === "textarea" ? (openBlock(), createBlock(_component_AppTextArea, {
					key: 3,
					modelValue: $data.draft[field.name],
					"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
					label: field.widget?.title || field.label,
					rows: "4",
					disabled: $data.saving || $options.readOnly(field)
				}, null, 8, [
					"modelValue",
					"onUpdate:modelValue",
					"label",
					"disabled"
				])) : $options.fieldKind(field) === "datetime-local" ? (openBlock(), createBlock(_component_AppDateField, {
					key: 4,
					"include-time": "",
					modelValue: $data.draft[field.name],
					"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
					label: field.widget?.title || field.label,
					required: [true, "true"].includes(field.widget?.options?.required),
					disabled: $data.saving || $options.readOnly(field)
				}, null, 8, [
					"modelValue",
					"onUpdate:modelValue",
					"label",
					"required",
					"disabled"
				])) : (openBlock(), createBlock(_component_AppTextField, {
					key: 5,
					modelValue: $data.draft[field.name],
					"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
					label: field.widget?.title || field.label,
					type: $options.fieldKind(field),
					required: [true, "true"].includes(field.widget?.options?.required),
					disabled: $data.saving || $options.readOnly(field),
					step: "any"
				}, null, 8, [
					"modelValue",
					"onUpdate:modelValue",
					"label",
					"type",
					"required",
					"disabled"
				])), field.widget?.options?.hint || field.widget?.options?.hint_text ? (openBlock(), createElementBlock("small", _hoisted_6, toDisplayString($options.t(field.widget.options.hint || field.widget.options.hint_text)), 1)) : createCommentVNode("", true)]),
				_: 2
			}, 1032, ["minimum-editor-height", "model"]);
		}), 128))])], 512), [[vShow, $data.step === 0]])], 544)) : createCommentVNode("", true)]), $options.busyPresentation ? (openBlock(), createBlock(_component_ContentLoadingOverlay, {
			key: 0,
			message: $options.busyPresentation.message,
			cancellable: $options.busyPresentation.cancellable,
			onCancel: _cache[2] || (_cache[2] = ($event) => $options.close())
		}, null, 8, ["message", "cancellable"])) : createCommentVNode("", true)]),
		createVNode(_component_ObjectDuplicateSurface, {
			model: $options.presentation,
			part: "footer",
			onEvent: $options.action
		}, null, 8, ["model", "onEvent"]),
		$data.discard ? (openBlock(), createElementBlock("div", _hoisted_7, [
			createBaseVNode("p", null, toDisplayString($options.t("Discard unsaved changes?")), 1),
			createVNode(_component_AppButton, {
				label: "Continue editing",
				onClick: _cache[3] || (_cache[3] = ($event) => $data.discard = false)
			}),
			createVNode(_component_AppButton, {
				label: "Discard",
				destructive: "",
				onClick: _cache[4] || (_cache[4] = ($event) => $options.close(true))
			})
		])) : createCommentVNode("", true)
	], 40, _hoisted_1)), [[_directive_window, {
		kind: "duplicate_sobject",
		type: "window"
	}]])]);
}
var DuplicateSObject_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { DuplicateSObject_default as default };

//# sourceMappingURL=DuplicateSObject.js.map
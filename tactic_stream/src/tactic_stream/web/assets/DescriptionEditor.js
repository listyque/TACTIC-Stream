import { A as onMounted, C as inject, E as nextTick, H as watch, J as markRaw, M as openBlock, O as onBeforeUnmount, X as ref, Y as reactive, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, f as Teleport, h as createBlock, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString } from "./vue.js";
import { D as t, O as appearance, rt as _plugin_vue_export_helper_default } from "./index.js";
import { C as button, D as rect, E as node, _ as _sfc_main$3, t as _sfc_main$4, u as translate, w as label } from "./FrameView.js";
import { F as rpc } from "./CodeBlock.js";
import { n as observeFrameSizes } from "./resize.js";
import { f as linkifyPlainText, n as browserLink } from "./links.js";
//#region ../src/tactic_stream/shared_ui/features/objects/description.ui.mjs
var metrics = {
	margin: 8,
	compactMargin: 6,
	gap: 6,
	heading: 16,
	action: 28,
	actionGap: 2,
	textPadding: 10,
	actionReserve: 38
};
function presentation(model, language) {
	const tr = (text) => translate(text, language);
	const managed = model.managed !== false;
	return {
		managed,
		editable: !managed || !!model.editing || !!model.pinned,
		enabled: !!model.enabled || !!model.pinned,
		emphasized: managed && (!!model.editing || !!model.pinned),
		outline: model.error ? "error" : model.pinned ? "tertiary" : "action",
		fontRole: model.compact ? "menuHeading" : "caption",
		bottomPadding: managed ? metrics.actionReserve : model.compact ? 8 : 10,
		placeholder: tr(model.enabled ? "Description" : "Select an sObject, process or snapshot"),
		empty: tr(model.enabled || model.title ? "No description" : "Select an sObject, process or snapshot"),
		status: !managed ? "" : model.saving ? tr("Saving…") : model.pinned ? tr("Used for check-in") : model.editing ? tr(model.dirty ? "Unsaved" : "Editing") : ""
	};
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language);
	const state = presentation(model, language);
	const margin = model.compact ? metrics.compactMargin : metrics.margin;
	const inner = Math.max(0, width - margin * 2);
	const nodes = [node("Box", "descriptionSurface", rect(0, 0, width, height), { background: "surfaceContainerLow" })];
	let top = margin;
	if (state.managed && model.header !== false) {
		nodes.push(node("Icon", "descriptionKind", rect(margin, top, 15, 15), {
			icon: model.pinned ? "push-pin" : model.kind === "snapshot" ? "snapshot" : model.kind === "process" ? "settings-suggest" : "description",
			color: model.pinned ? "tertiary" : model.editing ? "action" : "secondaryText"
		}));
		const statusWidth = state.status ? Math.min(135, inner / 2) : 0;
		nodes.push(label("descriptionTarget", rect(margin + 21, top, inner - 21 - statusWidth, 16), model.title || tr("No sObject selected"), {
			fontRole: "secondary",
			weight: 600
		}));
		if (state.status) nodes.push(label("descriptionState", rect(width - margin - statusWidth, top, statusWidth, 16), state.status, {
			fontRole: "caption",
			align: "right",
			color: model.pinned ? "tertiary" : model.saving ? "secondaryText" : "action"
		}));
		top += metrics.heading + metrics.gap;
	}
	if (model.drafts?.length) {
		nodes.push(node("Choice", "descriptionDrafts", rect(margin, top, inner, 36), {
			label: tr("Retained description drafts"),
			options: [{
				value: "",
				label: tr("Retained description drafts"),
				disabled: true
			}].concat(model.drafts),
			value: model.editing ? model.current || "" : "",
			enabled: !model.saving,
			action: { type: "draft" }
		}));
		top += 36 + metrics.gap;
	}
	const bodyHeight = Math.max(0, height - margin - top);
	nodes.push(node("View", "descriptionValue", rect(margin, top, inner, bodyHeight), { view: "value" }));
	if (state.managed) {
		const actions = model.pinned ? [[
			"unpin",
			"Stop using this text for check-in",
			"unlock-alt",
			!model.saving
		]] : model.editing ? [
			[
				"cancel",
				"Discard changes",
				"close",
				!model.saving
			],
			[
				"save",
				model.canSave ? "Save description" : "This item has no description field",
				"save",
				!!model.canSave && !!model.dirty && !model.saving
			],
			[
				"pin",
				"Use this text for check-in",
				"push-pin",
				!model.saving
			]
		] : [[
			"edit",
			"Edit description",
			"edit",
			!!model.enabled && !model.saving
		]];
		const total = actions.length * (metrics.action + metrics.actionGap) - metrics.actionGap;
		const left = width - margin - 7 - total;
		const y = Math.max(top, height - margin - metrics.action - 5);
		for (let index = 0; index < actions.length; index++) {
			const [type, title, icon, enabled] = actions[index];
			nodes.push(button("description_" + type, rect(left + index * 30, y, 28, 28), tr(title), icon, { type }, enabled, {
				iconOnly: true,
				iconAction: true,
				iconSize: 17,
				iconColor: type === "save" ? "green" : ["pin", "unpin"].includes(type) ? "tertiary" : type === "cancel" ? "secondaryText" : "primaryText",
				label: type === "save" ? tr("Save description") : tr(title)
			}));
		}
		if (model.error) nodes.push(label("descriptionError", rect(margin + 12, y + 6, left - margin - 18, 18), model.error, {
			color: "error",
			fontRole: "caption",
			role: "alert"
		}));
		else if (model.header === false && state.status) nodes.push(label("descriptionState", rect(margin + 12, y + 6, left - margin - 18, 18), state.status, {
			color: model.pinned ? "tertiary" : "secondaryText",
			fontRole: "caption",
			role: "status"
		}));
	}
	return {
		nodes,
		height
	};
}
//#endregion
//#region src/features/objects/DescriptionValue.vue
var _hoisted_1$1 = { class: "description-value" };
var _hoisted_2 = ["innerHTML"];
var _hoisted_3 = {
	key: 1,
	class: "muted"
};
var _sfc_main$2 = {
	__name: "DescriptionValue",
	props: {
		text: String,
		html: String,
		model: Object
	},
	emits: [
		"value",
		"link",
		"finished"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const emit = __emit;
		const editor = ref(null);
		__expose({ focus: () => editor.value?.focus() });
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$1, [__props.model.editable ? (openBlock(), createBlock(_sfc_main$3, {
				key: 0,
				ref_key: "editor",
				ref: editor,
				class: "description-value-input",
				"model-value": __props.text,
				label: __props.model.placeholder,
				placeholder: __props.model.placeholder,
				disabled: !__props.model.enabled,
				"error-state": __props.model.outline === "error",
				style: normalizeStyle({
					padding: metrics.textPadding + "px",
					paddingBottom: __props.model.bottomPadding + "px",
					fontSize: __props.model.fontRole === "menuHeading" ? "10px" : "11px",
					borderWidth: __props.model.emphasized ? "2px" : "1px",
					borderColor: __props.model.emphasized || __props.model.outline === "error" ? `var(${__props.model.outline === "tertiary" ? "--tertiary" : __props.model.outline === "error" ? "--error" : "--primary"})` : void 0
				}),
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => emit("value", $event)),
				onBlur: _cache[1] || (_cache[1] = ($event) => emit("finished", $event.target.value))
			}, null, 8, [
				"model-value",
				"label",
				"placeholder",
				"disabled",
				"error-state",
				"style"
			])) : (openBlock(), createElementBlock("div", {
				key: 1,
				class: "description-value-read",
				onClick: _cache[2] || (_cache[2] = ($event) => emit("link", $event))
			}, [createBaseVNode("div", { style: normalizeStyle({
				padding: metrics.textPadding + "px",
				paddingBottom: __props.model.bottomPadding + "px"
			}) }, [__props.text ? (openBlock(), createElementBlock("div", {
				key: 0,
				innerHTML: __props.html
			}, null, 8, _hoisted_2)) : (openBlock(), createElementBlock("span", _hoisted_3, toDisplayString(__props.model.empty), 1))], 4)]))]);
		};
	}
};
//#endregion
//#region src/features/objects/DescriptionSurface.vue
var _sfc_main$1 = {
	__name: "DescriptionSurface",
	props: {
		model: Object,
		text: String,
		html: String
	},
	emits: [
		"event",
		"value",
		"link",
		"finished"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 0,
			height: 0
		}), editor = ref(null);
		const scene = computed(() => describe(props.model, viewport.value.width, viewport.value.height, appearance.language));
		const valueComponent = markRaw(_sfc_main$2);
		const views = computed(() => ({ value: {
			component: valueComponent,
			props: {
				ref: (instance) => {
					editor.value = instance;
				},
				text: props.text,
				html: props.html,
				model: presentation(props.model, appearance.language),
				onValue: (value) => emit("value", value),
				onLink: (event) => emit("link", event),
				onFinished: (value) => emit("finished", value)
			}
		} }));
		let observer;
		onMounted(() => {
			const measure = () => {
				viewport.value = {
					width: host.value.clientWidth,
					height: host.value.clientHeight
				};
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		__expose({ focus: () => editor.value?.focus() });
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "description-surface"
			}, [createVNode(_sfc_main$4, {
				scene: scene.value,
				views: views.value,
				onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
			}, null, 8, ["scene", "views"])], 512);
		};
	}
};
//#endregion
//#region src/features/objects/DescriptionEditor.vue
var _hoisted_1 = ["aria-label"];
var DescriptionEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "DescriptionEditor",
	props: {
		ticket: String,
		project: String,
		target: Object
	},
	emits: ["saved", "session-expired"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const openObjectTab = inject("openObjectTab", null);
		const drafts = reactive(/* @__PURE__ */ new Map()), current = ref(""), pinned = ref(null), editor = ref(null);
		const entry = computed(() => drafts.get(current.value));
		const pinActive = computed(() => pinned.value?.project === props.project);
		const value = computed({
			get() {
				if (pinActive.value) return pinned.value.value;
				if (!entry.value) return "";
				return entry.value.editing || entry.value.saving ? entry.value.value : entry.value.original;
			},
			set(text) {
				if (pinActive.value) pinned.value.value = text;
				else if (entry.value) entry.value.value = text;
			}
		});
		const dirty = computed(() => !!entry.value && entry.value.value !== entry.value.original);
		const retained = computed(() => [...drafts.entries()].filter(([, item]) => item.project === props.project && item.value !== item.original));
		const html = computed(() => linkifyPlainText(value.value, (link) => browserLink(link, props.project)));
		const frameModel = computed(() => ({
			value: value.value,
			enabled: !!entry.value && !entry.value.saving,
			editing: !!entry.value?.editing,
			pinned: pinActive.value,
			dirty: dirty.value,
			saving: !!entry.value?.saving,
			canSave: !!entry.value?.searchKey,
			error: entry.value?.error || "",
			title: entry.value?.title || "",
			kind: entry.value?.kind || "",
			header: false,
			current: current.value,
			drafts: retained.value.length > 1 || retained.value.some(([key]) => key !== current.value || !entry.value?.editing && !entry.value?.saving && !pinActive.value) ? retained.value.map(([key, item]) => ({
				value: key,
				label: item.title
			})) : []
		}));
		function dispatch(action) {
			if (action.type === "edit") edit();
			else if (action.type === "cancel") discard();
			else if (action.type === "save") save();
			else if (action.type === "pin") pin();
			else if (action.type === "unpin") unpin();
			else if (action.type === "draft") resumeDraft(action.value);
		}
		function activateLink(event) {
			const link = event.target.closest("[data-rich-link]")?.dataset.richLink;
			if (link && openObjectTab && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && !event.button) {
				event.preventDefault();
				openObjectTab(link, props.project);
			}
		}
		watch(() => [props.target, props.project], () => {
			const target = props.target;
			if (!target || target.project !== props.project) {
				current.value = "";
				return;
			}
			const key = target.project + ":" + target.id;
			let item = drafts.get(key);
			const original = String(target.record?.description || target.record?.detail || "");
			if (!item) {
				item = {
					...target,
					original,
					value: original,
					editing: false,
					saving: false,
					error: ""
				};
				drafts.set(key, item);
			} else {
				item.title = target.title;
				if (!item.saving && item.value === item.original) item.value = item.original = original;
			}
			current.value = key;
		}, { immediate: true });
		function edit() {
			entry.value.editing = true;
			nextTick(() => editor.value?.focus());
		}
		function resumeDraft(key) {
			current.value = key;
			if (pinActive.value) pinned.value = null;
			edit();
		}
		function discard() {
			entry.value.value = entry.value.original;
			entry.value.editing = false;
			entry.value.error = "";
		}
		function pin() {
			pinned.value = {
				project: props.project,
				value: value.value
			};
			discard();
		}
		function unpin() {
			pinned.value = null;
			if (entry.value) {
				entry.value.editing = false;
				entry.value.error = "";
			}
		}
		async function save() {
			const item = entry.value;
			if (!item?.searchKey || item.saving || item.value === item.original) return;
			const text = item.value, ticket = props.ticket;
			item.saving = true;
			item.editing = false;
			item.error = "";
			try {
				await rpc("update", [
					{
						ticket,
						project: item.project
					},
					item.searchKey,
					{ description: text }
				]);
				item.original = text;
				item.editing = false;
				item.record.description = text;
				emit("saved", item.searchKey, text);
			} catch (failure) {
				item.editing = true;
				item.error = failure instanceof TypeError ? "Unable to reach the server." : failure.message;
				if (failure.code === "authentication_failed") emit("session-expired");
			} finally {
				item.saving = false;
			}
		}
		function canLeave() {
			return ![...drafts.values()].some((item) => item.saving) && (![...drafts.values()].some((item) => item.value !== item.original) || window.confirm(t("Discard unsaved descriptions?")));
		}
		function beforeUnload(event) {
			if ([...drafts.values()].some((item) => item.saving || item.value !== item.original)) {
				event.preventDefault();
				event.returnValue = "";
			}
		}
		onMounted(() => window.addEventListener("beforeunload", beforeUnload));
		onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnload));
		__expose({
			canLeave,
			pinnedValue: () => pinActive.value ? pinned.value.value : ""
		});
		return (_ctx, _cache) => {
			return openBlock(), createBlock(Teleport, {
				defer: "",
				to: "#dock-description"
			}, [createBaseVNode("section", {
				class: "description-editor",
				"aria-label": unref(t)("Description editor"),
				onKeydown: _cache[1] || (_cache[1] = withKeys(($event) => entry.value?.editing && !entry.value.saving && discard(), ["esc"]))
			}, [createVNode(_sfc_main$1, {
				ref_key: "editor",
				ref: editor,
				model: frameModel.value,
				text: value.value,
				html: html.value,
				onValue: _cache[0] || (_cache[0] = ($event) => value.value = $event),
				onLink: activateLink,
				onEvent: dispatch
			}, null, 8, [
				"model",
				"text",
				"html"
			])], 40, _hoisted_1)]);
		};
	}
}, [["__scopeId", "data-v-a1396ade"]]);
//#endregion
export { DescriptionEditor_default as default };

//# sourceMappingURL=DescriptionEditor.js.map
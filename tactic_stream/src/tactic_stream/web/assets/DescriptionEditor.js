import { A as onMounted, C as inject, E as nextTick, H as watch, M as openBlock, O as onBeforeUnmount, X as ref, Y as reactive, b as createVNode, c as withKeys, et as unref, f as Teleport, h as createBlock, m as createBaseVNode, p as computed } from "./vue.js";
import { L as _plugin_vue_export_helper_default, o as t } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { N as linkifyPlainText, x as browserLink } from "./admin.document.js";
import { x as _sfc_main$1 } from "./App.js";
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
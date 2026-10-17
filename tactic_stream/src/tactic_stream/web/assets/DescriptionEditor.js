import { D as nextTick, H as watch, N as openBlock, X as ref, Y as reactive, _ as createCommentVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, l as withKeys, m as computed, p as Teleport, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, w as inject, x as createVNode } from "./vue.js";
import { D as t, o as _sfc_main$2, tt as _plugin_vue_export_helper_default, u as _sfc_main$1 } from "./index.js";
import { F as rpc, f as _sfc_main$3 } from "./clipboard.js";
import { d as linkifyPlainText, n as browserLink } from "./links.js";
import { t as _sfc_main$4 } from "./AppTextArea.js";
//#region src/features/objects/DescriptionEditor.vue
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { key: 0 };
var _hoisted_3 = ["innerHTML"];
var _hoisted_4 = {
	key: 1,
	class: "muted"
};
var _hoisted_5 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_6 = { class: "description-actions" };
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
				class: normalizeClass(["description-editor", {
					pinned: pinActive.value,
					editing: entry.value?.editing,
					saving: entry.value?.saving
				}]),
				"aria-label": unref(t)("Description editor"),
				onKeydown: _cache[1] || (_cache[1] = withKeys(($event) => entry.value?.editing && !entry.value.saving && discard(), ["esc"]))
			}, [
				createBaseVNode("header", null, [
					createVNode(_sfc_main$1, { name: pinActive.value ? "pin" : entry.value?.kind === "snapshot" ? "snapshot" : entry.value?.kind === "process" ? "settings-suggest" : "description" }, null, 8, ["name"]),
					createBaseVNode("strong", null, toDisplayString(entry.value?.title || unref(t)("Description")), 1),
					entry.value?.saving || pinActive.value || entry.value?.editing ? (openBlock(), createElementBlock("small", _hoisted_2, toDisplayString(unref(t)(entry.value?.saving ? "Saving…" : pinActive.value ? "Used for check-in" : dirty.value ? "Unsaved" : "Editing")), 1)) : createCommentVNode("", true)
				]),
				retained.value.length > 1 || retained.value.some(([key]) => key !== current.value || !entry.value?.editing && !entry.value?.saving && !pinActive.value) ? (openBlock(), createBlock(_sfc_main$3, {
					key: 0,
					"model-value": entry.value?.editing ? current.value : "",
					label: "Retained description drafts",
					options: [{
						value: "",
						label: "Retained description drafts",
						disabled: true
					}, ...retained.value.map(([key, item]) => ({
						value: key,
						label: item.title
					}))],
					"onUpdate:modelValue": resumeDraft
				}, null, 8, ["model-value", "options"])) : createCommentVNode("", true),
				createBaseVNode("div", { class: normalizeClass(["description-field", {
					editing: entry.value?.editing || pinActive.value,
					"error-outline": !!entry.value?.error
				}]) }, [entry.value?.editing || pinActive.value ? (openBlock(), createBlock(_sfc_main$4, {
					key: 0,
					ref_key: "editor",
					ref: editor,
					modelValue: value.value,
					"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => value.value = $event),
					label: "Description",
					"aria-invalid": !!entry.value?.error,
					disabled: entry.value?.saving
				}, null, 8, [
					"modelValue",
					"aria-invalid",
					"disabled"
				])) : (openBlock(), createElementBlock("div", {
					key: 1,
					class: "description-read",
					onClick: activateLink
				}, [value.value ? (openBlock(), createElementBlock("div", {
					key: 0,
					innerHTML: html.value
				}, null, 8, _hoisted_3)) : (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString(unref(t)(entry.value ? "No description" : "Select an sObject, process or snapshot")), 1))])), createBaseVNode("footer", null, [entry.value?.error ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString(unref(t)(entry.value.error)), 1)) : createCommentVNode("", true), createBaseVNode("div", _hoisted_6, [
					!entry.value?.editing && !pinActive.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						icon: "edit",
						"icon-only": "",
						label: "Edit description",
						disabled: !entry.value || entry.value.saving,
						onClick: edit
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					entry.value?.editing && !pinActive.value ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [
						createVNode(_sfc_main$2, {
							class: "description-discard",
							icon: "close",
							"icon-only": "",
							label: "Discard changes",
							disabled: entry.value.saving,
							onClick: discard
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$2, {
							class: "description-save",
							icon: "save",
							"icon-only": "",
							label: "Save description",
							tooltip: entry.value.searchKey ? "Save description" : "This item has no description field",
							disabled: !entry.value.searchKey || !dirty.value || entry.value.saving,
							onClick: save
						}, null, 8, ["tooltip", "disabled"]),
						createVNode(_sfc_main$2, {
							class: "description-pin",
							icon: "pin",
							"icon-only": "",
							label: "Use this text for check-in",
							disabled: entry.value.saving,
							onClick: pin
						}, null, 8, ["disabled"])
					], 64)) : createCommentVNode("", true),
					pinActive.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 2,
						class: "description-pin",
						icon: "MDI_LOCK_OPEN_VARIANT",
						"icon-only": "",
						label: "Stop using this text for check-in",
						disabled: entry.value?.saving,
						onClick: unpin
					}, null, 8, ["disabled"])) : createCommentVNode("", true)
				])])], 2)
			], 42, _hoisted_1)]);
		};
	}
}, [["__scopeId", "data-v-2e4d001b"]]);
//#endregion
export { DescriptionEditor_default as default };

//# sourceMappingURL=DescriptionEditor.js.map
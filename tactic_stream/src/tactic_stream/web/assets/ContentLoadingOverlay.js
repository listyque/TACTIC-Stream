import { M as openBlock, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, rt as toDisplayString } from "./vue.js";
import { I as BusyIndicator_default, o as t, t as _sfc_main$1 } from "./AppButton.js";
//#region src/features/objects/duplicateProfiles.js
var contentChoices = [
	"copySnapshots",
	"copyTasks",
	"copyProcessMessages",
	"copyTaskMessages",
	"copyProcessAttachments",
	"copyTaskAttachments"
];
function key(login, project, type) {
	return "tactic-stream.duplicate." + JSON.stringify([
		login,
		project,
		type
	]);
}
function duplicateProfile(login, project, type) {
	try {
		const value = JSON.parse(localStorage.getItem(key(login, project, type)));
		return value?.relations && value?.processes ? value : null;
	} catch {
		return null;
	}
}
function saveDuplicateProfile(login, project, type, profile) {
	localStorage.setItem(key(login, project, type), JSON.stringify(profile));
}
function changeContent(process, name, value) {
	process[name] = value;
	if (!value && name === "copyTasks") process.copyTaskMessages = process.copyTaskAttachments = false;
	if (!value && name === "copyTaskMessages") process.copyTaskAttachments = false;
	if (!value && name === "copyProcessMessages") process.copyProcessAttachments = false;
	if (process.copyTaskAttachments) process.copyTaskMessages = process.copyTasks = true;
	if (process.copyTaskMessages) process.copyTasks = true;
	if (process.copyProcessAttachments) process.copyProcessMessages = true;
}
function applyDuplicateProfile(analysis, profile) {
	for (const relation of analysis.relations) {
		const mode = profile?.relations?.[relation.key];
		if (relation.options.some((option) => option.value === mode)) relation.mode = mode;
	}
	for (const process of analysis.processes) {
		for (const name of contentChoices) process[name] = profile?.processes?.[process.name]?.[name] === true;
		if (process.copyTaskAttachments) process.copyTaskMessages = process.copyTasks = true;
		if (process.copyTaskMessages) process.copyTasks = true;
		if (process.copyProcessAttachments) process.copyProcessMessages = true;
	}
}
//#endregion
//#region src/controls/display/ContentLoadingOverlay.vue
var _sfc_main = {
	__name: "ContentLoadingOverlay",
	props: {
		message: {
			type: String,
			default: "Loading…"
		},
		cancellable: Boolean,
		disabled: Boolean
	},
	emits: ["cancel"],
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "content-loading-overlay",
				role: "status",
				"aria-busy": "true",
				onPointerdown: _cache[1] || (_cache[1] = withModifiers(() => {}, ["stop"])),
				onClick: _cache[2] || (_cache[2] = withModifiers(() => {}, ["stop"]))
			}, [createBaseVNode("div", null, [
				createVNode(BusyIndicator_default, { running: "" }),
				createBaseVNode("strong", null, toDisplayString(unref(t)(__props.message)), 1),
				__props.cancellable ? (openBlock(), createBlock(_sfc_main$1, {
					key: 0,
					label: "Cancel",
					disabled: __props.disabled,
					onClick: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("cancel"))
				}, null, 8, ["disabled"])) : createCommentVNode("", true)
			])], 32);
		};
	}
};
//#endregion
export { duplicateProfile as a, contentChoices as i, applyDuplicateProfile as n, saveDuplicateProfile as o, changeContent as r, _sfc_main as t };

//# sourceMappingURL=ContentLoadingOverlay.js.map
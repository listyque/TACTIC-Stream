import { A as onDeactivated, K as withCtx, N as openBlock, O as onActivated, R as resolveDynamicComponent, U as watch, Z as ref, b as createVNode, h as createBlock, j as onMounted, k as onBeforeUnmount, m as createBaseVNode, nt as normalizeClass, p as computed } from "./vue.js";
import { j as appearance } from "./index.js";
import { Jt as label, Xt as node, Yt as muted, Zt as rect, ct as rpc, i as _sfc_main$1, qt as button, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { t as _sfc_main$2 } from "./AppDialog.js";
import { m as describe$1 } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/configuration/providers.ui.mjs
function initial() {
	return {
		profiles: [],
		kinds: [],
		default: "codex",
		revision: "",
		selected: "codex",
		draft: {},
		baseline: {},
		busy: false,
		error: "",
		notice: ""
	};
}
function select(model, id) {
	const row = model.profiles.find((item) => item.id === id);
	const draft = {
		name: row?.name || "",
		kind: row?.kind || "compatible",
		url: row?.url || "",
		secret: "",
		secret_env: row?.secret_env || "",
		clear_secret: false,
		enabled: row?.enabled ?? true,
		default_model: row?.default_model || "",
		default: id === model.default
	};
	return Object.assign({}, model, {
		selected: id,
		draft,
		baseline: Object.assign({}, draft),
		error: "",
		notice: ""
	});
}
function dirty(model) {
	return JSON.stringify(model.draft) !== JSON.stringify(model.baseline);
}
function edit(model, field, value) {
	const draft = Object.assign({}, model.draft, { [field]: value });
	if (field === "kind") draft.url = model.kinds.find((kind) => kind.value === value)?.url || "";
	return Object.assign({}, model, {
		draft,
		error: "",
		notice: ""
	});
}
function describe(model, width, height, language) {
	const tr = (key) => translate(key, language), locked = model.busy;
	const selected = model.profiles.find((item) => item.id === model.selected);
	const narrow = width < 620, rowHeight = narrow ? 80 : 40, toolsWidth = narrow ? width - 24 : Math.min(320, width / 2);
	const nodes = [node("Choice", "agentProviderProfile", rect(12, 8, narrow ? width - 24 : width - toolsWidth - 36, 32), {
		label: tr("AI connection"),
		value: model.selected,
		enabled: !locked && !dirty(model),
		options: model.profiles.map((item) => ({
			value: item.id,
			label: item.name
		})).concat(model.selected ? [] : [{
			value: "",
			label: tr("New connection")
		}]),
		action: { type: "select" }
	})];
	const left = narrow ? 12 : width - toolsWidth - 12, top = narrow ? 48 : 8;
	[
		[
			"New",
			"add",
			"new"
		],
		[
			"Discard",
			"undo",
			"reset"
		],
		[
			"Remove",
			"delete",
			"remove"
		],
		[
			"Refresh",
			"refresh",
			"refresh"
		]
	].forEach(([text, icon, type], index) => nodes.push(button("agentProvider_" + type, rect(left + index * 38, top, 32, 32), tr(text), icon, { type }, !locked && (type === "reset" || !dirty(model)) && (type !== "remove" || !!model.selected && model.selected !== "codex"), {
		iconOnly: true,
		destructive: type === "remove"
	})));
	nodes.push(label("agentProviderNotice", rect(12, rowHeight + 8, width - 24, 44), tr(model.error || model.notice || selected?.error || {
		connected: "Connection checked",
		failed: "Connection failed",
		waiting: "Waiting for the external host",
		unchecked: "Connection has not been checked"
	}[selected?.status] || "Configure a connection, then check it from the external host."), Object.assign({}, muted, {
		wrap: true,
		color: model.error || selected?.status === "failed" ? "error" : "muted"
	})));
	const fields = [
		{
			kind: "Field",
			field: "name",
			title: "Connection name",
			props: { maxLength: 128 }
		},
		{
			kind: "Choice",
			field: "kind",
			title: "Provider",
			enabled: model.selected !== "codex",
			options: model.kinds.filter((item) => model.selected === "codex" ? item.value === "codex" : item.value !== "codex")
		},
		{
			kind: "Switch",
			field: "enabled",
			title: "Enable connection"
		},
		{
			kind: "Switch",
			field: "default",
			title: "Default connection"
		}
	];
	if (model.draft.kind === "codex") fields.push({
		kind: "Heading",
		id: "agentCodexAccount",
		title: "Account authorization",
		description: "Codex uses the account signed in on the external host. Provider API keys are not required."
	});
	else fields.push({
		kind: "Field",
		field: "url",
		title: "API base URL",
		description: "The external host connects to this address. Localhost means the machine running that host.",
		props: { maxLength: 2048 }
	}, {
		kind: "Field",
		field: "secret",
		title: "API key",
		description: selected?.has_secret ? "A key is stored. Leave empty to keep it." : "Write-only credential. It is encrypted and never returned to this form.",
		props: {
			password: true,
			maxLength: 4096,
			autocomplete: "new-password"
		}
	}, {
		kind: "Switch",
		field: "clear_secret",
		title: "Remove stored API key"
	}, {
		kind: "Field",
		field: "secret_env",
		title: "Host key environment variable",
		description: "Optional alternative to a stored API key. Enter the variable name, not its value.",
		props: { maxLength: 128 }
	});
	const models = selected?.models || [];
	fields.push({
		kind: models.length ? "Choice" : "Field",
		field: "default_model",
		title: "Default model",
		options: [{
			value: "",
			label: tr("Agent default")
		}].concat(models.map((item) => ({
			value: item.id,
			label: item.label
		}))),
		props: { maxLength: 256 }
	}, {
		kind: "Heading",
		id: "agentProviderDataNotice",
		title: "Project data",
		description: "Chat messages, project context and attachments go only to the selected connection after Send. Connection checks do not send project data."
	});
	const contentY = rowHeight + 56;
	nodes.push(node("Box", "agentProviderForm", rect(0, contentY, width, Math.max(80, height - contentY - 52)), { children: describe$1({
		fields,
		values: model.draft,
		busy: locked,
		options: {}
	}, width, Math.max(80, height - contentY - 52), language).nodes }));
	nodes.push(button("agentProviderSave", rect(Math.max(12, width - 344), height - 44, Math.min(120, width - 236), 32), tr("Save"), "save", { type: "save" }, !locked && !!model.draft.name?.trim(), {
		highlighted: true,
		iconOnly: width < 360
	}), button("agentProviderCheck", rect(width - 212, height - 44, 200, 32), tr("Check connection"), "refresh", { type: "check" }, !locked && !!model.selected && !dirty(model)));
	return { nodes };
}
//#endregion
//#region src/features/configuration/AgentProviders.vue
var _sfc_main = {
	__name: "AgentProviders",
	props: {
		ticket: String,
		project: String,
		embedded: Boolean,
		active: {
			type: Boolean,
			default: true
		}
	},
	setup(__props, { expose: __expose }) {
		const props = __props;
		const dialog = ref(null), host = ref(null), model = ref(initial()), viewport = ref({
			width: 940,
			height: 650
		});
		const scene = computed(() => describe(model.value, viewport.value.width, viewport.value.height, appearance.language));
		let context = null, generation = 0, observer, timer, opened = false;
		watch(host, (element) => {
			observer?.disconnect();
			if (element) {
				observer = observeFrameSizes((entries) => {
					const box = entries.at(-1).contentRect;
					viewport.value = {
						width: box.width,
						height: box.height
					};
				});
				observer.observe(element);
			}
		});
		watch(() => [props.ticket, props.project], () => {
			generation++;
			context = null;
			model.value = initial();
			if (!props.embedded) dialog.value?.close();
			clearTimeout(timer);
			if (props.embedded && props.active) open();
		});
		onMounted(() => {
			if (props.embedded && props.active) open();
		});
		onActivated(() => {
			if (props.embedded && props.active) open();
		});
		onDeactivated(() => {
			if (props.embedded) closed();
		});
		watch(() => props.active, (active) => {
			if (props.embedded) {
				if (active) open();
				else closed();
			}
		});
		onBeforeUnmount(() => {
			generation++;
			observer?.disconnect();
			clearTimeout(timer);
		});
		async function call(action, values = {}) {
			if (!context) return;
			const id = ++generation, owner = context;
			model.value.busy = true;
			model.value.error = "";
			try {
				const reply = await rpc("execute_cmd", [
					{
						ticket: owner.ticket,
						project: owner.project
					},
					"tactic.ui.panel.agent_provider_cmd.AgentProviderCmd",
					{
						action,
						project_code: owner.project,
						...values
					}
				], {}, true, true);
				if (reply.status !== "OK") throw Error(reply.description || "Provider settings could not be loaded");
				const result = typeof reply.info === "string" ? JSON.parse(reply.info) : reply.info;
				if (id !== generation || context !== owner) return;
				const selected = action === "save" && !model.value.selected ? result.profiles.find((row) => !model.value.profiles.some((old) => old.id === row.id))?.id : model.value.selected;
				const next = Object.assign({}, model.value, result, { busy: false });
				model.value = select(next, result.profiles.some((row) => row.id === selected) ? selected : result.default);
				if (action === "check") model.value.notice = "Waiting for the external host";
				schedule();
			} catch (error) {
				if (id === generation) {
					model.value.error = error.message;
					model.value.busy = false;
				}
			}
		}
		function schedule() {
			clearTimeout(timer);
			if (opened && model.value.profiles.some((row) => row.status === "waiting")) timer = setTimeout(() => {
				if (!dirty(model.value) && !model.value.busy) call("state");
				else schedule();
			}, 2e3);
		}
		function event(action) {
			if (model.value.busy) return;
			if (action.type === "field") model.value = edit(model.value, action.field, action.value);
			else if (action.type === "select" && !dirty(model.value)) model.value = select(model.value, action.value);
			else if (action.type === "new" && !dirty(model.value)) model.value = select(model.value, "");
			else if (action.type === "reset") model.value = select(model.value, model.value.selected);
			else if (action.type === "refresh" && !dirty(model.value)) call("state");
			else if ([
				"save",
				"check",
				"remove"
			].includes(action.type)) call(action.type, {
				provider: model.value.selected,
				expected_revision: model.value.revision,
				...action.type === "save" ? { document: { ...model.value.draft } } : {}
			});
		}
		async function open() {
			if (!props.ticket || !props.project) return;
			context ||= {
				ticket: props.ticket,
				project: props.project
			};
			opened = true;
			if (!props.embedded) dialog.value.show();
			if (!model.value.busy && (!dirty(model.value) || !model.value.revision)) await call("state");
		}
		function closed() {
			opened = false;
			clearTimeout(timer);
		}
		__expose({ open });
		return (_ctx, _cache) => {
			return openBlock(), createBlock(resolveDynamicComponent(__props.embedded ? "section" : _sfc_main$2), {
				ref_key: "dialog",
				ref: dialog,
				title: __props.embedded ? void 0 : "AI providers",
				"window-kind": "agent_providers",
				class: normalizeClass(__props.embedded ? "agent-providers-embedded" : "agent-providers-dialog"),
				"close-on-outside": false,
				onClosed: closed
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "host",
					ref: host,
					class: "agent-providers-body"
				}, [createVNode(_sfc_main$1, {
					scene: scene.value,
					onEvent: event
				}, null, 8, ["scene"])], 512)]),
				_: 1
			}, 40, ["title", "class"]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=AgentProviders.js.map
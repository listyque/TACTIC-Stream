import { D as nextTick, K as withCtx, N as openBlock, U as watch, Z as ref, b as createVNode, h as createBlock, k as onBeforeUnmount, m as createBaseVNode, p as computed } from "./vue.js";
import { j as appearance } from "./index.js";
import { Gt as button, Jt as node, Kt as label, Yt as rect, _ as copyText, ct as rpc, i as _sfc_main$1, qt as muted, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { t as _sfc_main$2 } from "./AppDialog.js";
//#region ../src/tactic_stream/shared_ui/features/configuration/mcp.ui.mjs
function initial() {
	return {
		connections: [],
		tools: [],
		selected: [],
		enabled: false,
		title: "",
		instructions: "",
		minutes: "60",
		busy: false,
		error: "",
		issued: ""
	};
}
function agentLink(issued) {
	const connection = JSON.parse(issued);
	return connection.url + "#access_token=" + encodeURIComponent(connection.headers.Authorization.replace(/^Bearer /, ""));
}
function edit(model, action) {
	if (action.type === "field") return Object.assign({}, model, { [action.field]: action.value });
	if (action.type === "tool") return Object.assign({}, model, { selected: action.value ? model.selected.concat(action.name) : model.selected.filter((name) => name !== action.name) });
	if (action.type === "readonly") return Object.assign({}, model, { selected: model.tools.filter((tool) => tool.readonly).map((tool) => tool.name) });
	if (action.type === "clear") return Object.assign({}, model, { selected: [] });
	return model;
}
function describe(model, width, height, language) {
	const tr = (value) => translate(value, language), inner = Math.max(0, width - 40);
	const nodes = [], content = [];
	let y = 0;
	function caption(id, text, extent = 28) {
		content.push(label(id, rect(0, y, inner, extent), text, { wrap: true }));
		y += extent + 8;
	}
	caption("mcpProject", tr("Project") + ": " + (model.project || ""));
	caption("mcpScope", tr("External access is limited to this project and the tools you select. Revoke it at any time."), 48);
	if (!model.enabled) caption("mcpDisabled", tr("Enable external MCP connections in Server configuration and restart first."), 48);
	content.push(node("Field", "mcpTitle", rect(0, y, inner, 40), {
		text: model.title,
		placeholder: tr("Connection name"),
		enabled: !model.busy,
		action: {
			type: "field",
			field: "title"
		}
	}));
	y += 48;
	content.push(node("Area", "mcpInstructions", rect(0, y, inner, 112), {
		text: model.instructions,
		placeholder: tr("Instructions for this connection"),
		enabled: !model.busy,
		action: {
			type: "field",
			field: "instructions"
		}
	}));
	y += 120;
	content.push(node("Choice", "mcpLifetime", rect(0, y, inner, 36), {
		value: model.minutes,
		enabled: !model.busy,
		options: [
			{
				value: "5",
				label: tr("5 minutes")
			},
			{
				value: "60",
				label: tr("1 hour")
			},
			{
				value: "480",
				label: tr("8 hours")
			}
		],
		action: {
			type: "field",
			field: "minutes"
		}
	}));
	y += 44;
	caption("mcpToolsTitle", tr("Allowed tools"));
	content.push(button("mcpReadTools", rect(0, y, Math.min(200, inner / 2), 32), tr("Select read tools"), "check", { type: "readonly" }, !model.busy));
	content.push(button("mcpClearTools", rect(Math.min(208, inner / 2), y, Math.min(120, inner / 2), 32), tr("Clear"), "close", { type: "clear" }, !model.busy));
	y += 40;
	const toolRows = [];
	for (const [index, tool] of model.tools.entries()) {
		const toolY = index * 84;
		toolRows.push(node("CheckBox", "mcpTool_" + index, rect(0, toolY, inner - 16, 32), {
			label: tool.name,
			checked: model.selected.includes(tool.name),
			enabled: !model.busy,
			action: {
				type: "tool",
				name: tool.name
			}
		}));
		toolRows.push(label("mcpToolDescription_" + index, rect(28, toolY + 32, inner - 44, 44), tool.description, Object.assign({}, muted, { wrap: true })));
	}
	const toolHeight = Math.min(252, model.tools.length * 84);
	content.push(node("Scroll", "mcpToolList", rect(0, y, inner, toolHeight), {
		contentHeight: model.tools.length * 84,
		scrollbarId: "mcpToolListBar",
		children: toolRows
	}));
	y += toolHeight + 12;
	if (model.issued) {
		caption("mcpAgentLinkTitle", tr("Agent link — includes access and startup instructions"), 48);
		content.push(node("Area", "mcpAgentLink", rect(0, y, inner, 72), {
			text: agentLink(model.issued),
			readOnly: true
		}));
		y += 80;
		content.push(button("mcpCopyAgentLink", rect(0, y, Math.min(260, inner), 32), tr("Copy agent link"), "link", { type: "copy_link" }, !model.busy));
		y += 44;
		caption("mcpIssuedTitle", tr("Copy this connection now. The access token will not be shown again."), 48);
		content.push(node("Area", "mcpIssued", rect(0, y, inner, 180), {
			text: model.issued,
			readOnly: true
		}));
		y += 188;
		content.push(button("mcpCopy", rect(0, y, Math.min(240, inner), 32), tr("Copy connection"), "content-copy", { type: "copy" }, !model.busy));
		y += 48;
	}
	caption("mcpExistingTitle", tr("Existing connections"));
	for (const [index, item] of model.connections.entries()) {
		if (item.pending && !item.revoked && !item.expired) {
			content.push(button("mcpCollect_" + index, rect(0, y, Math.min(240, inner), 32), tr("Copy agent link"), "key", {
				type: "reveal_link",
				id: item.id
			}, !model.busy));
			y += 40;
		}
		caption("mcpExisting_" + index, item.title + " · " + (item.revoked ? tr("Revoked") : item.expired ? tr("Expired") : item.expiresLabel));
		content.push(button("mcpRevoke_" + index, rect(0, y, Math.min(160, inner), 32), tr("Revoke access"), "block", {
			type: "revoke",
			id: item.id
		}, !model.busy && !item.revoked));
		y += 44;
	}
	nodes.push(node("Scroll", "mcpScroll", rect(12, 8, width - 24, Math.max(0, height - 108)), {
		contentHeight: y,
		scrollbarId: "mcpScrollBar",
		children: content
	}));
	if (model.error) nodes.push(label("mcpError", rect(12, height - 96, width - 24, 44), tr(model.error), {
		wrap: true,
		color: "error"
	}));
	nodes.push(button("mcpRefresh", rect(12, height - 44, 36, 32), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy, { iconOnly: true }));
	nodes.push(button("mcpCreate", rect(Math.max(56, width - 240), height - 44, Math.min(228, width - 68), 32), tr("Create connection"), "add", { type: "create" }, !model.busy && model.enabled && !!model.title.trim() && model.selected.length > 0, { highlighted: true }));
	return { nodes };
}
//#endregion
//#region src/features/configuration/AgentMcp.vue
var _sfc_main = {
	__name: "AgentMcp",
	props: {
		ticket: String,
		project: String
	},
	setup(__props, { expose: __expose }) {
		const props = __props;
		const dialog = ref(null), host = ref(null), model = ref(initial()), size = ref({
			width: 800,
			height: 650
		});
		const scene = computed(() => describe(model.value, size.value.width, size.value.height, appearance.language));
		let context, focusConnection = "", generation = 0, observer;
		watch(host, (element) => {
			observer?.disconnect();
			if (element) {
				observer = observeFrameSizes((entries) => {
					const box = entries.at(-1).contentRect;
					size.value = {
						width: box.width,
						height: box.height
					};
				});
				observer.observe(element);
			}
		});
		function clear() {
			++generation;
			context = null;
			model.value = initial();
		}
		function reset() {
			clear();
			dialog.value?.close();
		}
		watch(() => [props.ticket, props.project], reset);
		onBeforeUnmount(() => {
			++generation;
			observer?.disconnect();
		});
		async function call(action, values = {}, copyLink = false) {
			if (!context || model.value.busy) return;
			const id = ++generation, owner = context;
			model.value.busy = true;
			model.value.error = "";
			try {
				const reply = await rpc("execute_cmd", [
					{
						ticket: owner.ticket,
						project: owner.project
					},
					"tactic.ui.panel.agent_mcp_cmd.AgentMcpCmd",
					{
						action,
						project_code: owner.project,
						...values
					}
				], {}, true, true);
				if (reply.status !== "OK") throw Error(reply.description || "MCP connections could not be loaded");
				const result = typeof reply.info === "string" ? JSON.parse(reply.info) : reply.info;
				if (id !== generation || owner !== context) return;
				if (action === "create" || action === "reveal") {
					model.value.issued = JSON.stringify({
						url: new URL(result.path, location.origin).href,
						headers: { Authorization: "Bearer " + result.token }
					}, null, 2);
					model.value.busy = false;
					await call("state");
					if (copyLink && context === owner) copyText(agentLink(model.value.issued)).catch((error) => {
						if (context === owner) model.value.error = error.message;
					});
				} else Object.assign(model.value, result, {
					busy: false,
					project: owner.project,
					connections: result.connections.map((item) => ({
						...item,
						expired: item.expires <= Date.now() / 1e3,
						expiresLabel: (/* @__PURE__ */ new Date(item.expires * 1e3)).toLocaleString()
					})).sort((a, b) => Number(b.id === focusConnection) - Number(a.id === focusConnection))
				});
			} catch (error) {
				if (id === generation) Object.assign(model.value, {
					busy: false,
					error: error.message
				});
			}
		}
		function event(action) {
			if (model.value.busy) return;
			model.value = edit(model.value, action);
			if (action.type === "refresh") call("state");
			else if (action.type === "revoke" || action.type === "reveal") call(action.type, { id: action.id });
			else if (action.type === "reveal_link") call("reveal", { id: action.id }, true);
			else if (action.type === "copy" || action.type === "copy_link") copyText(action.type === "copy_link" ? agentLink(model.value.issued) : model.value.issued).catch((error) => {
				model.value.error = error.message;
			});
			else if (action.type === "create") call("create", {
				title: model.value.title,
				instructions: model.value.instructions,
				minutes: Number(model.value.minutes),
				tools: [...model.value.selected],
				context: ownerContext()
			});
		}
		function ownerContext() {
			const { ticket, ...value } = context;
			return value;
		}
		async function open(value, connectionId = "") {
			clear();
			if (!props.ticket || !value?.project) return;
			context = {
				...structuredClone(value),
				ticket: props.ticket
			};
			focusConnection = connectionId;
			dialog.value.show();
			await call("state");
			await nextTick();
			if (focusConnection && model.value.connections[0]?.id === focusConnection) host.value?.querySelector("[data-frame=mcpCollect_0]")?.scrollIntoView({ block: "center" });
		}
		__expose({ open });
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$2, {
				ref_key: "dialog",
				ref: dialog,
				title: "MCP connections",
				"window-kind": "agent_mcp",
				class: "agent-mcp-dialog",
				"close-on-outside": false,
				onClosed: clear
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "host",
					ref: host,
					class: "agent-mcp-body"
				}, [createVNode(_sfc_main$1, {
					scene: scene.value,
					onEvent: event
				}, null, 8, ["scene"])], 512)]),
				_: 1
			}, 512);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=AgentMcp.js.map
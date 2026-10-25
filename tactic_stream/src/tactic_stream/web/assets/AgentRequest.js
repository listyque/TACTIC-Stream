import { D as nextTick, K as withCtx, N as openBlock, U as watch, Z as ref, b as createVNode, f as Teleport, h as createBlock, k as onBeforeUnmount, m as createBaseVNode, p as computed, tt as unref } from "./vue.js";
import { O as randomUuid, j as appearance } from "./index.js";
import { Gt as label, Jt as rect, Kt as muted, Wt as button, i as _sfc_main$1, qt as node, r as observeFrameSizes, st as rpc, y as translate } from "./CodeBlock.js";
import { t as _sfc_main$2 } from "./AppDialog.js";
//#region ../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs
function initial(context = {}) {
	return {
		context,
		prompt: "",
		allowChanges: false,
		hosts: [],
		requests: [],
		selected: "",
		request: {},
		busy: false,
		error: "",
		pending: null
	};
}
function active(model) {
	return [
		"queued",
		"running",
		"cancelling"
	].includes(model.request?.status);
}
function canSend(model) {
	return !model.busy && !model.selected && !!model.context?.project && !!model.prompt.trim() && model.prompt.length <= 12e3 && !!model.hosts.length && (!model.allowChanges || model.hosts.some((host) => host.capabilities.changes));
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language);
	const inset = 8, gap = 8, inner = Math.max(0, width - 16);
	const current = model.request || {}, context = current.document?.context || model.context || {};
	const statusText = (value) => tr({
		queued: "Request queued",
		running: "Agent working",
		cancelling: "Request cancelling",
		cancelled: "Request cancelled",
		completed: "Request completed",
		failed: "Request failed",
		interrupted: "Request interrupted"
	}[value] || value);
	const status = model.error || (model.busy ? tr("Loading…") : current.status ? statusText(current.status) : model.hosts.length ? tr("External agent connected") + ": " + model.hosts.map((host) => host.label).join(", ") : tr("External agent is offline"));
	const contextText = [
		context.client,
		context.project,
		context.title || context.page,
		context.search_type,
		context.view,
		...context.search_keys || []
	].filter(Boolean).join("\n");
	const output = [
		model.error ? tr(model.error) : "",
		current.error ? tr(current.error) : "",
		...(current.events || []).filter((value) => value !== current.answer).map((value) => tr(value)),
		current.answer || ""
	].filter(Boolean).join("\n\n");
	const actionsTop = 326, outputTop = 370;
	return { nodes: [
		node("Choice", "agentRequestHistory", rect(inset, 8, Math.max(0, inner - 88), 36), {
			label: tr("Agent requests"),
			value: model.selected,
			enabled: !model.busy,
			options: [{
				value: "",
				label: tr("New request")
			}, ...(model.requests || []).map((row) => ({
				value: row.request_id,
				label: statusText(row.status) + " · " + row.prompt
			}))],
			action: { type: "select" }
		}),
		button("agentRequestNew", rect(width - inset - 80, 8, 36, 36), tr("New request"), "add", {
			type: "select",
			value: ""
		}, !model.busy, { iconOnly: true }),
		button("agentRequestRefresh", rect(width - inset - 36, 8, 36, 36), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy, { iconOnly: true }),
		label("agentRequestStatus", rect(inset, 48, inner, 28), status, muted),
		node("Area", "agentRequestContext", rect(inset, 80, inner, 100), {
			label: tr("Context sent to the agent"),
			text: contextText,
			readOnly: true,
			enabled: true
		}),
		node("Area", "agentRequestPrompt", rect(inset, 188, inner, 96), {
			label: tr("What should the agent do?"),
			text: current.document?.prompt || model.prompt,
			readOnly: !!model.selected || !!model.pending,
			enabled: !model.busy,
			action: { type: "prompt" }
		}),
		node("CheckBox", "agentRequestChanges", rect(inset, 290, inner, 30), {
			text: tr("Allow the requested configuration changes"),
			wrapText: true,
			checked: current.document?.allow_changes ?? model.allowChanges,
			enabled: !model.busy && !model.selected && !model.pending,
			action: { type: "changes" }
		}),
		button("agentRequestSend", rect(inset, actionsTop, Math.min(220, (inner - gap) / 2), 36), tr("Send to agent"), "send", { type: "send" }, canSend(model)),
		button("agentRequestCancel", rect(inset + Math.min(220, (inner - gap) / 2) + gap, actionsTop, Math.min(200, (inner - gap) / 2), 36), tr("Cancel request"), "close", { type: "cancel" }, !model.busy && active(model) && current.status !== "cancelling"),
		node("Area", "agentRequestOutput", rect(inset, outputTop, inner, Math.max(80, height - outputTop - 42)), {
			label: tr("Agent progress and answer"),
			text: output || tr("The answer and operation results will appear here."),
			readOnly: true,
			enabled: true
		}),
		label("agentRequestBoundary", rect(inset, height - 34, inner, 28), tr("Script activation remains a separate action in the Script Editor."), Object.assign({}, muted, { wrap: true }))
	] };
}
//#endregion
//#region src/features/scripts/AgentRequest.vue
var _sfc_main = {
	__name: "AgentRequest",
	props: {
		ticket: String,
		capture: Function
	},
	setup(__props, { expose: __expose }) {
		const props = __props;
		const dialog = ref(null), body = ref(null), size = ref({
			width: 900,
			height: 650
		});
		const model = ref(initial());
		const scene = computed(() => describe(model.value, size.value.width, size.value.height, appearance.language));
		let generation = 0, observer, timer, contextTicket = "", inFlight = false;
		async function call(action, values = {}) {
			const result = await rpc("execute_cmd", [
				{
					ticket: contextTicket,
					project: model.value.context.project
				},
				"tactic.ui.panel.agent_request_cmd.AgentRequestCmd",
				{
					action,
					project_code: model.value.context.project,
					...values
				}
			], {}, true, true);
			if (result.status !== "OK") throw new Error(result.description || "Agent request failed");
			return typeof result.info === "string" ? JSON.parse(result.info) : result.info;
		}
		async function request(action = "refresh") {
			if (inFlight || !model.value.context.project) return;
			const id = ++generation;
			inFlight = true;
			model.value.busy = action !== "poll";
			if (action !== "poll") model.value.error = "";
			try {
				if (action === "send") {
					model.value.pending ||= {
						request_id: randomUuid(),
						host_id: model.value.hosts.find((host) => !model.value.allowChanges || host.capabilities.changes).host_id,
						document: {
							prompt: model.value.prompt,
							context: JSON.parse(JSON.stringify(model.value.context)),
							allow_changes: model.value.allowChanges
						}
					};
					const saved = await call("submit", model.value.pending);
					if (id !== generation) return;
					model.value.selected = saved.request_id;
					model.value.pending = null;
				} else if (action === "cancel") await call("cancel", { request_id: model.value.selected });
				const state = await call("state");
				if (id !== generation) return;
				Object.assign(model.value, state);
				if (model.value.selected) {
					const current = await call("read", { request_id: model.value.selected });
					if (id !== generation) return;
					model.value.request = current;
				}
			} catch (error) {
				if (id === generation) model.value.error = error.message;
			} finally {
				if (id === generation) {
					model.value.busy = false;
					inFlight = false;
				}
				schedule();
			}
		}
		function schedule() {
			clearTimeout(timer);
			if (dialog.value?.open) timer = setTimeout(() => request("poll"), 2500);
		}
		function event(action) {
			if (model.value.busy) return;
			if (action.type === "prompt" || action.type === "changes") {
				if (model.value.pending) return;
				if (action.type === "prompt") model.value.prompt = action.value;
				else model.value.allowChanges = !!action.value;
			} else if (action.type === "select") {
				generation++;
				inFlight = false;
				if (!action.value) model.value = initial(props.capture());
				else Object.assign(model.value, {
					selected: action.value,
					request: {}
				});
				request();
			} else if (action.type === "send" && canSend(model.value)) request("send");
			else if (action.type === "cancel") request("cancel");
			else if (action.type === "refresh") request();
		}
		async function open(context) {
			if (!model.value.selected && !model.value.prompt) model.value = initial(context || props.capture());
			contextTicket = props.ticket;
			await nextTick();
			if (!dialog.value.open) dialog.value.show();
			observer ||= observeFrameSizes(() => {
				size.value = {
					width: body.value.clientWidth,
					height: body.value.clientHeight
				};
			});
			observer.observe(body.value);
			if (!model.value.context.project) model.value.error = "Select a project before contacting the agent";
			request();
		}
		function close() {
			dialog.value?.close();
			clearTimeout(timer);
		}
		watch(() => props.ticket, () => {
			generation++;
			inFlight = false;
			close();
			contextTicket = "";
			model.value = initial();
		});
		onBeforeUnmount(() => {
			generation++;
			clearTimeout(timer);
			observer?.disconnect();
		});
		__expose({ open });
		return (_ctx, _cache) => {
			return openBlock(), createBlock(Teleport, { to: "body" }, [createVNode(_sfc_main$2, {
				ref_key: "dialog",
				ref: dialog,
				title: "External agent",
				"window-kind": "agent_request",
				class: "agent-request-dialog",
				"close-on-outside": false,
				onClosed: _cache[0] || (_cache[0] = ($event) => _ctx.clearTimeout(unref(timer)))
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "body",
					ref: body,
					class: "agent-request-body"
				}, [createVNode(_sfc_main$1, {
					scene: scene.value,
					onEvent: event
				}, null, 8, ["scene"])], 512)]),
				_: 1
			}, 512)]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=AgentRequest.js.map
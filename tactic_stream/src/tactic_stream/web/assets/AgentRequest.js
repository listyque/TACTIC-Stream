import { D as nextTick, K as withCtx, N as openBlock, P as renderList, U as watch, Y as markRaw, Z as ref, _ as createElementBlock, b as createVNode, f as Teleport, g as createCommentVNode, h as createBlock, it as toDisplayString, k as onBeforeUnmount, l as withModifiers, m as createBaseVNode, nt as normalizeClass, p as computed, rt as normalizeStyle, tt as unref, u as Fragment } from "./vue.js";
import { A as t, O as randomUuid, c as _sfc_main$3, f as _sfc_main$2, j as appearance } from "./index.js";
import { Bt as notify, Gt as label, Jt as rect, Kt as muted, Wt as button, i as _sfc_main$4, qt as node, r as observeFrameSizes, st as rpc, y as translate } from "./CodeBlock.js";
import { t as _sfc_main$5 } from "./AppDialog.js";
import { n as _sfc_main$6 } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs
var metrics = {
	inset: 12,
	bubblePadding: 14,
	messageGap: 16,
	attachmentHeight: 28
};
function initial(context = {}) {
	return {
		context,
		prompt: "",
		allowChanges: false,
		allowWeb: false,
		hosts: [],
		requests: [],
		selected: "",
		request: {},
		busy: false,
		error: "",
		pending: null,
		attachments: [],
		uploading: false,
		model: null,
		provider: null,
		effort: null,
		contextExpanded: false
	};
}
function active(model) {
	return [
		"queued",
		"running",
		"cancelling"
	].includes(model.request?.status);
}
function host(model) {
	const allowed = model.hosts.filter((item) => !(model.request?.document?.allow_changes ?? model.allowChanges) || item.capabilities.changes);
	return allowed.find((item) => item.host_id === model.request?.host_id) || allowed[0];
}
function canSend(model) {
	const connected = host(model);
	return !model.busy && !model.uploading && !!model.context?.project && (!!model.prompt.trim() || !!model.attachments.length) && model.prompt.length <= 12e3 && !!connected && (!model.selected || model.request?.request_id === model.selected) && (Array.isArray(connected?.capabilities.providers) ? availableModels(model).length > 0 : provider(model) === "codex" || availableModels(model).length > 0) && (provider(model) === "codex" || !!selectedModel(model)) && (!model.allowChanges || connected.capabilities.changes) && (!model.selected || model.request.status !== "cancelling") && (!active(model) || connected.capabilities.steering === true);
}
function provider(model) {
	return model.provider ?? (model.request?.request_id ? model.request.provider || "codex" : host(model)?.capabilities.default_provider || "codex");
}
function availableModels(model) {
	return (host(model)?.capabilities.models || []).filter((item) => (item.provider || "codex") === provider(model));
}
function selectedModel(model) {
	const id = model.model ?? model.request?.model ?? "";
	return availableModels(model).find((item) => id ? item.id === id : item.is_default);
}
function messages(model) {
	const current = model.request || {};
	return (current.messages?.length ? current.messages : current.document ? [{
		id: current.request_id,
		role: "user",
		text: current.document.prompt,
		attachments: []
	}, ...current.answer ? [{
		id: "answer",
		role: "assistant",
		text: current.answer,
		attachments: []
	}] : []] : []).concat(current.output && active(model) ? [{
		id: "progress",
		role: "assistant",
		text: current.output,
		attachments: []
	}] : []);
}
function activity(model, language) {
	const names = {
		agent_context: "Reading conversation context",
		agent_capabilities: "Checking available tools",
		reference_read: "Reading TACTIC documentation",
		agent_selection: "Reading selected objects",
		ts_records: "Reading project objects",
		ts_type_read: "Reading object definition",
		ts_schema_read: "Reading project relationships",
		ts_records_create: "Creating project objects",
		ts_relations: "Reading object relationships",
		ts_instance_link: "Linking project objects",
		ts_snapshots: "Reading file history",
		ts_workflow_read: "Reading workflows",
		ts_workflow_apply: "Saving workflow",
		ts_attachment_checkin: "Checking in attached files",
		ts_edit_operation: "Checking saved changes",
		ts_naming_read: "Reading naming rules",
		ts_naming_preview: "Checking file naming",
		agent_attachment_image: "Viewing attached image",
		agent_web_download: "Downloading reference file",
		webSearch: "Searching the web"
	};
	const events = model.request?.events || [];
	return events.slice(events.lastIndexOf("External agent started") + 1).map((event) => {
		const match = event.match(/^([a-zA-Z_]+): (inProgress|completed|failed)$/);
		if (!match) return event;
		return translate(names[match[1]] || match[1], language) + " · " + translate({
			inProgress: "Working",
			completed: "Done",
			failed: "Failed"
		}[match[2]], language);
	});
}
function safeMarkdown(text) {
	return String(text || "").replace(/<[^>]*>/g, (value) => value.replace(/</g, "&lt;").replace(/>/g, "&gt;")).replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/!\[/g, "[");
}
function messageGeometry(width, role, bodyHeight, attachments) {
	const inner = Math.min(800, Math.max(0, width - 32)), bubbleWidth = Math.min(role === "user" ? 640 : 800, inner);
	const padding = role === "user" ? metrics.bubblePadding : 0;
	return {
		x: (width - inner) / 2 + (role === "user" ? inner - bubbleWidth : 0),
		width: bubbleWidth,
		padding,
		height: padding * 2 + Math.max(20, bodyHeight) + (Array.isArray(attachments) ? attachments.reduce((height, file) => height + attachmentHeight(file), 0) : attachments * metrics.attachmentHeight)
	};
}
function attachmentHeight(file) {
	return /^image\/(png|jpeg|webp|gif)$/.test(file.media_type || "") ? 172 : metrics.attachmentHeight;
}
function contextItems(context, language) {
	const tr = (text) => translate(text, language);
	return [
		{
			value: context.project || "",
			icon: "folder"
		},
		{
			value: context.title || context.page || "",
			icon: "table"
		},
		{
			value: context.search_type || "",
			icon: "database"
		},
		{
			value: tr("Selected objects") + ": " + (context.search_keys || []).length,
			icon: "check"
		}
	].filter((item) => item.value).map((item) => Object.assign({}, item, { width: Math.min(220, Math.max(80, item.value.length * 7 + 40)) }));
}
function status(model, language) {
	const tr = (text) => translate(text, language), current = model.request || {};
	if (model.error || current.error) return {
		text: tr(model.error || current.error),
		color: "error",
		icon: "error"
	};
	if (current.status === "completed") return current.outcome === "needs_input" ? {
		text: tr("Waiting for your reply"),
		color: "action",
		icon: "help"
	} : current.outcome === "blocked" ? {
		text: tr("Task blocked — see the answer"),
		color: "error",
		icon: "warning"
	} : {
		text: tr(current.outcome === "completed" ? "Task completed" : "Agent finished — review the answer"),
		color: "green",
		icon: "check"
	};
	return {
		text: tr({
			queued: "Request queued",
			running: "Agent working",
			cancelling: "Request cancelling",
			cancelled: "Request cancelled",
			failed: "Request failed",
			interrupted: "Request interrupted"
		}[current.status] || (model.hosts.length ? "External agent connected" : "External agent is offline")),
		color: "secondaryText",
		icon: active(model) ? "sync" : "chat"
	};
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language), current = model.request || {}, context = current.document?.context || model.context || {};
	const inset = metrics.inset, inner = Math.max(0, width - inset * 2), connected = host(model);
	const providers = connected?.capabilities.providers || [], narrow = width < (providers.length ? 820 : 640), providerRow = narrow && providers.length ? 40 : 0;
	const composerWidth = Math.min(880, inner), composerX = (width - composerWidth) / 2;
	const contextHeight = model.contextExpanded ? 122 : 38;
	const composerHeight = 188 + contextHeight + (model.attachments.length ? 42 : 0) + (narrow ? 40 : 0) + providerRow;
	const composerTop = Math.max(180, height - composerHeight - 12), modelWidth = narrow ? Math.max(80, (composerWidth - 32) / 2) : 200;
	const state = status(model, language), working = active(model), sendVisible = !working || !!model.prompt.trim() || !!model.attachments.length;
	const nodes = [
		node("Choice", "agentRequestHistory", rect(inset, 10, Math.max(70, inner - 88), 32), {
			label: tr("Agent requests"),
			value: model.selected,
			enabled: !model.busy && !model.uploading,
			options: [{
				value: "",
				label: tr("New conversation")
			}, ...(model.requests || []).map((row) => ({
				value: row.request_id,
				label: row.prompt === "Attachments" ? tr("Attachments") : row.prompt
			}))],
			action: { type: "select" }
		}),
		button("agentRequestNew", rect(width - inset - 72, 10, 32, 32), tr("New conversation"), "add", {
			type: "select",
			value: ""
		}, !model.busy && !model.uploading, { iconOnly: true }),
		button("agentRequestRefresh", rect(width - inset - 32, 10, 32, 32), tr("Refresh"), "refresh", { type: "refresh" }, !model.busy && !model.uploading, { iconOnly: true }),
		node("Icon", "agentRequestStatusIcon", rect(inset, 52, 18, 18), {
			icon: state.icon,
			color: state.color
		}),
		label("agentRequestStatus", rect(inset + 26, 50, Math.max(0, inner - 26 - (current.undo_operation ? 142 : 0)), 24), state.text, Object.assign({}, muted, {
			color: state.color,
			role: "alert"
		})),
		node("View", "agentRequestOutput", rect(0, 84, width, Math.max(70, composerTop - 96)), {
			view: "transcript",
			messages: messages(model),
			events: activity(model, language),
			active: working
		}),
		node("Box", "agentComposerSurface", rect(composerX, composerTop, composerWidth, height - composerTop - 12), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			borderWidth: 1,
			radius: 20
		}),
		node("View", "agentRequestContext", rect(composerX + 12, composerTop + 10, Math.max(0, composerWidth - 24), contextHeight), {
			view: "context",
			context,
			expanded: model.contextExpanded
		}),
		node("Area", "agentRequestPrompt", rect(composerX + 10, composerTop + contextHeight + 18, Math.max(0, composerWidth - 20), 64), {
			label: tr(working ? "Add a correction while the agent works" : "What should the agent do?"),
			placeholder: tr(working ? "Add a correction while the agent works" : "Describe the task. Attach files or paste an image."),
			text: model.prompt,
			flat: true,
			readOnly: !!model.pending,
			enabled: !model.busy,
			sendOnEnter: true,
			sendAction: { type: "send" },
			action: { type: "prompt" }
		}),
		node("CheckBox", "agentRequestChanges", rect(composerX + 16, height - 114 - (narrow ? 40 : 0) - providerRow, Math.max(0, composerWidth - 32), 26), {
			text: tr("Allow requested changes"),
			wrapText: true,
			checked: current.document?.allow_changes ?? model.allowChanges,
			enabled: !model.busy && !model.selected && !model.pending,
			action: { type: "changes" }
		}),
		node("CheckBox", "agentRequestWeb", rect(composerX + 16, height - 84 - (narrow ? 40 : 0) - providerRow, Math.max(0, composerWidth - 32), 26), {
			text: tr("Allow internet access"),
			checked: current.document?.allow_web ?? model.allowWeb,
			enabled: !model.busy && !model.selected && !model.pending && !!connected?.capabilities.web_search,
			action: { type: "web" }
		}),
		button("agentRequestAttach", rect(composerX + 12, height - 52, 32, 32), tr("Attach files"), "add", { type: "attach" }, !model.uploading && !model.pending && !model.busy, { iconOnly: true }),
		button("agentRequestPaste", rect(composerX + 50, height - 52, 32, 32), tr("Paste attachment"), "content-paste", { type: "paste" }, !model.uploading && !model.pending && !model.busy, { iconOnly: true }),
		button("agentRequestProviders", rect(composerX + 88, height - 52, 32, 32), tr("AI providers"), "settings", { type: "providers" }, !model.busy, { iconOnly: true })
	];
	if (sendVisible) nodes.push(button("agentRequestSend", rect(composerX + composerWidth - 44 - (working ? 40 : 0), height - 52, 32, 32), tr(working ? "Send correction" : "Send to agent"), "arrow-upward", { type: "send" }, canSend(model), {
		iconOnly: true,
		highlighted: true
	}));
	if (working) nodes.push(button("agentRequestCancel", rect(composerX + composerWidth - 44, height - 52, 32, 32), tr("Cancel request"), "stop", { type: "cancel" }, !model.busy && current.status !== "cancelling", { iconOnly: true }));
	if (providers.length) nodes.push(node("Choice", "agentRequestProvider", rect(narrow ? composerX + 12 : composerX + 128, height - (narrow ? 132 : 52), narrow ? composerWidth - 24 : Math.min(210, composerWidth - modelWidth - 332 - (working && sendVisible ? 40 : 0)), 32), {
		label: tr("AI connection"),
		value: provider(model),
		enabled: !model.busy && !working && !model.pending,
		options: providers.map((item) => ({
			value: item.id,
			label: item.name
		})),
		action: { type: "provider" }
	}));
	if (availableModels(model).length) nodes.push(node("Choice", "agentRequestModel", rect(narrow ? composerX + 12 : composerX + composerWidth - modelWidth - 52 - (narrow ? 0 : 144) - (working && sendVisible ? 40 : 0), height - (narrow ? 92 : 52), modelWidth, 32), {
		label: tr("Model"),
		value: model.model ?? current.model ?? "",
		enabled: !model.busy && !working && !model.pending,
		options: [{
			value: "",
			label: tr("Agent default")
		}, ...availableModels(model).map((item) => ({
			value: item.id,
			label: item.label
		}))],
		action: { type: "model" }
	}));
	const efforts = selectedModel(model)?.efforts || [];
	if (efforts.length) nodes.push(node("Choice", "agentRequestEffort", rect(narrow ? composerX + 20 + modelWidth : composerX + composerWidth - 188 - (working && sendVisible ? 40 : 0), height - (narrow ? 92 : 52), narrow ? modelWidth : 136, 32), {
		label: tr("Reasoning effort"),
		value: model.effort ?? current.effort ?? "",
		enabled: !model.busy && !working && !model.pending,
		options: [{
			value: "",
			label: tr("Agent default")
		}, ...efforts.map((value) => ({
			value,
			label: tr({
				none: "None",
				minimal: "Minimal",
				low: "Low",
				medium: "Medium",
				high: "High",
				xhigh: "Extra high",
				max: "Maximum",
				ultra: "Ultra"
			}[value] || value)
		}))],
		action: { type: "effort" }
	}));
	if (model.attachments.length) nodes.push(node("View", "agentRequestAttachments", rect(composerX + 12, height - 156 - (narrow ? 40 : 0) - providerRow, composerWidth - 24, 36), {
		view: "attachments",
		files: model.attachments
	}));
	if (current.undo_operation) nodes.push(button("agentRequestUndo", rect(width - inset - 134, 50, 134, 26), tr("Undo field change"), "undo", { type: "undo" }, !working && !model.busy && !model.uploading));
	return { nodes };
}
//#endregion
//#region src/features/scripts/AgentChatPort.vue
var _hoisted_1$1 = {
	key: 0,
	class: "agent-context"
};
var _hoisted_2 = { class: "agent-context-row" };
var _hoisted_3 = { class: "agent-context-chips" };
var _hoisted_4 = ["title"];
var _hoisted_5 = {
	key: 0,
	class: "agent-context-details",
	tabindex: "0"
};
var _hoisted_6 = {
	key: 1,
	class: "agent-attachment-strip"
};
var _hoisted_7 = ["src"];
var _hoisted_8 = ["title"];
var _hoisted_9 = ["aria-label"];
var _hoisted_10 = {
	key: 0,
	class: "agent-chat-empty"
};
var _hoisted_11 = ["src", "alt"];
var _hoisted_12 = { key: 0 };
var _hoisted_13 = ["open"];
var _sfc_main$1 = {
	__name: "AgentChatPort",
	props: {
		frameNode: Object,
		previews: Object
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const log = ref(null);
		const chips = computed(() => contextItems(props.frameNode.context || {}, appearance.language));
		const rows = computed(() => props.frameNode.messages || []);
		watch(rows, async () => {
			const element = log.value;
			const follow = element && element.scrollHeight - element.scrollTop - element.clientHeight < 60;
			await nextTick();
			if (follow && log.value) log.value.scrollTop = log.value.scrollHeight;
		});
		const messageStyle = (row) => {
			const geometry = messageGeometry(props.frameNode.width, row.role, 20, 0);
			return {
				width: geometry.width + "px",
				marginLeft: geometry.x + "px",
				padding: geometry.padding + "px",
				marginBottom: metrics.messageGap + "px"
			};
		};
		return (_ctx, _cache) => {
			return __props.frameNode.view === "context" ? (openBlock(), createElementBlock("div", _hoisted_1$1, [createBaseVNode("div", _hoisted_2, [createBaseVNode("div", _hoisted_3, [(openBlock(true), createElementBlock(Fragment, null, renderList(chips.value, (chip, index) => {
				return openBlock(), createElementBlock("span", {
					key: index,
					class: "agent-context-chip",
					title: chip.value,
					style: normalizeStyle({ width: chip.width + "px" })
				}, [createVNode(_sfc_main$2, { name: chip.icon }, null, 8, ["name"]), createBaseVNode("span", null, toDisplayString(chip.value), 1)], 12, _hoisted_4);
			}), 128))]), createVNode(_sfc_main$3, {
				"icon-only": "",
				icon: __props.frameNode.expanded ? "expand-less" : "expand-more",
				label: "Context details",
				"aria-expanded": __props.frameNode.expanded,
				onClick: _cache[0] || (_cache[0] = ($event) => emit("event", { type: "context" }))
			}, null, 8, ["icon", "aria-expanded"])]), __props.frameNode.expanded ? (openBlock(), createElementBlock("div", _hoisted_5, toDisplayString([
				__props.frameNode.context.page,
				__props.frameNode.context.view,
				...__props.frameNode.context.search_keys || []
			].filter(Boolean).join("\n")), 1)) : createCommentVNode("", true)])) : __props.frameNode.view === "attachments" ? (openBlock(), createElementBlock("div", _hoisted_6, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.frameNode.files, (file) => {
				return openBlock(), createElementBlock("div", {
					key: file.attachment_id,
					class: "agent-attachment-chip"
				}, [
					__props.previews?.[file.attachment_id] ? (openBlock(), createElementBlock("img", {
						key: 0,
						src: __props.previews[file.attachment_id],
						alt: ""
					}, null, 8, _hoisted_7)) : (openBlock(), createBlock(_sfc_main$2, {
						key: 1,
						name: "attach-file"
					})),
					createBaseVNode("span", { title: file.name }, toDisplayString(file.name), 9, _hoisted_8),
					createVNode(_sfc_main$3, {
						"icon-only": "",
						icon: "close",
						label: "Remove attachment",
						onClick: ($event) => emit("event", {
							type: "remove",
							value: file.attachment_id
						})
					}, null, 8, ["onClick"])
				]);
			}), 128))])) : (openBlock(), createElementBlock("div", {
				key: 2,
				ref_key: "log",
				ref: log,
				class: "agent-transcript",
				role: "log",
				"aria-label": unref(t)("Conversation"),
				"aria-live": "polite"
			}, [
				!rows.value.length ? (openBlock(), createElementBlock("div", _hoisted_10, [
					createVNode(_sfc_main$2, { name: "chat" }),
					createBaseVNode("strong", null, toDisplayString(unref(t)("What would you like to change?")), 1),
					createBaseVNode("span", null, toDisplayString(unref(t)("Describe the task. Attach files or paste an image.")), 1)
				])) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList(rows.value, (row) => {
					return openBlock(), createElementBlock("article", {
						key: row.id,
						class: normalizeClass(["agent-message", row.role]),
						style: normalizeStyle(messageStyle(row))
					}, [
						createVNode(_sfc_main$6, { text: safeMarkdown(row.text) }, null, 8, ["text"]),
						(openBlock(true), createElementBlock(Fragment, null, renderList(row.attachments || [], (file) => {
							return openBlock(), createElementBlock("div", {
								key: file.attachment_id,
								class: "agent-message-file"
							}, [__props.previews?.[file.attachment_id] ? (openBlock(), createElementBlock("img", {
								key: 0,
								class: "agent-message-image",
								src: __props.previews[file.attachment_id],
								alt: file.name
							}, null, 8, _hoisted_11)) : createCommentVNode("", true), createVNode(_sfc_main$3, {
								label: file.name,
								icon: "attach-file",
								onClick: ($event) => emit("event", {
									type: "download",
									value: file.attachment_id
								})
							}, null, 8, ["label", "onClick"])]);
						}), 128)),
						__props.frameNode.active && row.role === "user" && row.delivered === false ? (openBlock(), createElementBlock("small", _hoisted_12, toDisplayString(unref(t)("Correction queued")), 1)) : createCommentVNode("", true)
					], 6);
				}), 128)),
				__props.frameNode.events?.length ? (openBlock(), createElementBlock("details", {
					key: 1,
					class: "agent-tool-progress",
					style: normalizeStyle(messageStyle({ role: "assistant" })),
					open: __props.frameNode.active
				}, [createBaseVNode("summary", null, toDisplayString(unref(t)(__props.frameNode.active ? "Working with TACTIC tools…" : "Operation details")), 1), (openBlock(true), createElementBlock(Fragment, null, renderList(__props.frameNode.events, (step, index) => {
					return openBlock(), createElementBlock("div", { key: index }, toDisplayString(step), 1);
				}), 128))], 12, _hoisted_13)) : createCommentVNode("", true)
			], 8, _hoisted_9));
		};
	}
};
//#endregion
//#region src/features/scripts/AgentRequest.vue
var _hoisted_1 = ["aria-label"];
var attachmentCommand = "tactic.ui.panel.agent_attachment_cmd.AgentAttachmentCmd";
var _sfc_main = {
	__name: "AgentRequest",
	props: {
		ticket: String,
		capture: Function
	},
	emits: ["providers"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const dialog = ref(null), body = ref(null), size = ref({
			width: 900,
			height: 650
		});
		const model = ref(initial());
		const fileInput = ref(null), previews = ref({});
		const views = computed(() => Object.fromEntries([
			"context",
			"transcript",
			"attachments"
		].map((name) => [name, {
			component: markRaw(_sfc_main$1),
			nodeProps: true,
			props: {
				previews: previews.value,
				onEvent: event
			}
		}])));
		const scene = computed(() => describe(model.value, size.value.width, size.value.height, appearance.language));
		let generation = 0, queuedAction = "", observer, timer, contextTicket = "", inFlight = false;
		async function call(action, values = {}, command = "tactic.ui.panel.agent_request_cmd.AgentRequestCmd") {
			const result = await rpc("execute_cmd", [
				{
					ticket: contextTicket,
					project: model.value.context.project
				},
				command,
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
			if (inFlight) {
				if (action !== "poll" && !model.value.busy) {
					queuedAction = action;
					model.value.busy = true;
				}
				return;
			}
			if (!model.value.context.project) return;
			const id = ++generation;
			inFlight = true;
			model.value.busy = action !== "poll";
			if (action !== "poll") model.value.error = "";
			try {
				if (action === "send") {
					model.value.pending ||= model.value.selected ? {
						message_id: randomUuid(),
						host_id: host(model.value).host_id,
						text: model.value.prompt,
						model: model.value.model ?? model.value.request.model ?? "",
						effort: model.value.effort ?? model.value.request.effort ?? "",
						provider: provider(model.value),
						attachments: model.value.attachments.map((file) => file.attachment_id)
					} : {
						request_id: randomUuid(),
						host_id: host(model.value).host_id,
						document: {
							prompt: model.value.prompt,
							context: JSON.parse(JSON.stringify(model.value.context)),
							allow_changes: model.value.allowChanges,
							allow_web: model.value.allowWeb,
							model: model.value.model ?? "",
							effort: model.value.effort ?? "",
							provider: provider(model.value),
							attachments: model.value.attachments.map((file) => file.attachment_id)
						}
					};
					const saved = model.value.selected ? await call("message", {
						request_id: model.value.selected,
						...model.value.pending
					}) : await call("submit", model.value.pending);
					if (id !== generation) return;
					model.value.selected = saved.request_id;
					model.value.pending = null;
					model.value.prompt = "";
					model.value.attachments = [];
				} else if (action === "cancel") await call("cancel", { request_id: model.value.selected });
				else if (action === "undo") await call("undo", {
					request_id: model.value.selected,
					operation_id: model.value.request.undo_operation
				});
				const state = await call("state");
				if (id !== generation) return;
				Object.assign(model.value, state);
				if (model.value.selected) {
					const current = await call("read", { request_id: model.value.selected });
					if (id !== generation) return;
					const wasActive = active(model.value);
					model.value.request = current;
					for (const file of current.messages?.flatMap((message) => message.attachments || []) || []) {
						if (!file.media_type.startsWith("image/") || file.attachment_id in previews.value) continue;
						try {
							const preview = await call("preview", { attachment_id: file.attachment_id }, attachmentCommand);
							if (id !== generation) return;
							previews.value[file.attachment_id] = preview.url;
						} catch {
							if (id !== generation) return;
							previews.value[file.attachment_id] = "";
						}
					}
					if (wasActive && !active(model.value)) notify(current.status === "completed" && current.outcome === "completed" ? "complete" : "warning", status(model.value, appearance.language).text, model.value.context.title || model.value.context.project, "agent-request", current.request_id + ":" + current.turn);
				}
			} catch (error) {
				if (id === generation) model.value.error = error.message;
			} finally {
				if (id === generation) {
					model.value.busy = false;
					inFlight = false;
				}
				if (id === generation && queuedAction) {
					const next = queuedAction;
					queuedAction = "";
					request(next);
				} else schedule();
			}
		}
		function schedule() {
			clearTimeout(timer);
			if (dialog.value?.open || active(model.value)) timer = setTimeout(() => request("poll"), 2500);
		}
		function event(action) {
			if (action.type === "providers") {
				emit("providers");
				return;
			}
			if (model.value.busy) return;
			if (action.type === "prompt" || action.type === "changes" || action.type === "web") {
				if (model.value.pending) return;
				if (action.type === "prompt") model.value.prompt = action.value;
				else if (action.type === "changes") model.value.allowChanges = !!action.value;
				else model.value.allowWeb = !!action.value;
			} else if (action.type === "select") {
				if (model.value.uploading) return;
				if (action.value !== model.value.selected) clearPreviews();
				generation++;
				inFlight = false;
				queuedAction = "";
				if (!action.value) model.value = initial(props.capture());
				else Object.assign(model.value, {
					selected: action.value,
					request: {},
					prompt: "",
					attachments: [],
					model: null,
					provider: null,
					effort: null,
					pending: null
				});
				request();
			} else if (action.type === "send" && canSend(model.value)) request("send");
			else if (action.type === "cancel") request("cancel");
			else if (action.type === "refresh") request();
			else if (action.type === "provider") {
				model.value.provider = action.value;
				model.value.model = "";
				model.value.effort = "";
			} else if (action.type === "model") {
				model.value.model = action.value;
				model.value.effort = "";
			} else if (action.type === "effort") model.value.effort = action.value;
			else if (action.type === "context") model.value.contextExpanded = !model.value.contextExpanded;
			else if (action.type === "remove" && !model.value.pending) model.value.attachments = model.value.attachments.filter((file) => file.attachment_id !== action.value);
			else if (action.type === "attach") fileInput.value.click();
			else if (action.type === "paste") pasteClipboard();
			else if (action.type === "download") download(action.value);
			else if (action.type === "undo") request("undo");
		}
		function clearPreviews() {
			Object.values(previews.value).forEach((url) => URL.revokeObjectURL(url));
			previews.value = {};
		}
		async function addFiles(files) {
			const state = model.value;
			if (state.uploading || state.pending || state.busy) return;
			state.uploading = true;
			state.error = "";
			try {
				if (state.attachments.length + files.length > 20) throw new Error("Attach at most 20 files");
				for (const file of files) {
					if (file.size > 67108864) throw new Error("Each attachment must be at most 64 MB");
					const attachment_id = randomUuid();
					await call("start", {
						attachment_id,
						name: file.name,
						size: file.size,
						media_type: file.type
					}, attachmentCommand);
					for (let offset = 0; offset < file.size; offset += 393216) {
						if (model.value !== state) return;
						const bytes = new Uint8Array(await file.slice(offset, offset + 393216).arrayBuffer());
						let binary = "";
						for (let index = 0; index < bytes.length; index += 8192) binary += String.fromCharCode(...bytes.subarray(index, index + 8192));
						await call("append", {
							attachment_id,
							offset,
							data: btoa(binary)
						}, attachmentCommand);
					}
					const metadata = await call("finish", { attachment_id }, attachmentCommand);
					if (model.value !== state) return;
					if (file.type.startsWith("image/")) previews.value[attachment_id] = URL.createObjectURL(file);
					state.attachments.push(metadata);
				}
			} catch (error) {
				state.error = error.message;
			} finally {
				state.uploading = false;
				if (fileInput.value) fileInput.value.value = "";
			}
		}
		function paste(event) {
			const files = event.clipboardData?.files;
			if (files?.length) {
				event.preventDefault();
				addFiles([...files]);
			}
		}
		async function pasteClipboard() {
			try {
				if (!navigator.clipboard?.read) throw new Error("Press Ctrl+V in the message to attach clipboard files or images");
				const files = [];
				for (const item of await navigator.clipboard.read()) {
					const type = item.types.find((type) => type.startsWith("image/"));
					if (type) files.push(new File([await item.getType(type)], "clipboard-" + Date.now() + ".png", { type }));
				}
				if (!files.length) throw new Error("Press Ctrl+V in the message to attach clipboard files or images");
				await addFiles(files);
			} catch (error) {
				model.value.error = error.message;
			}
		}
		async function download(attachment_id) {
			try {
				const chunks = [];
				let offset = 0, result;
				do {
					result = await call("read", {
						attachment_id,
						offset
					}, attachmentCommand);
					chunks.push(Uint8Array.from(atob(result.data), (char) => char.charCodeAt(0)));
					offset = result.next_offset;
				} while (offset !== null);
				const url = URL.createObjectURL(new Blob(chunks, { type: result.media_type }));
				const link = document.createElement("a");
				link.href = url;
				link.download = result.name;
				link.click();
				setTimeout(() => URL.revokeObjectURL(url), 1e3);
			} catch (error) {
				model.value.error = error.message;
			}
		}
		async function open(context, fresh = false) {
			if (fresh) {
				if (model.value.prompt.trim() || model.value.attachments.length || model.value.pending || model.value.uploading) {
					await open();
					throw Error("Send or clear the current draft before opening another object");
				}
				generation++;
				inFlight = false;
				queuedAction = "";
				clearTimeout(timer);
				clearPreviews();
				model.value = initial(context);
			}
			if (!model.value.selected && !model.value.prompt && !model.value.attachments.length && !model.value.pending && !model.value.uploading) model.value = initial(context || props.capture());
			contextTicket = props.ticket;
			await nextTick();
			if (!dialog.value.open) dialog.value.show();
			observer ||= observeFrameSizes(() => {
				if (body.value.clientWidth > 0 && body.value.clientHeight > 0) size.value = {
					width: body.value.clientWidth,
					height: body.value.clientHeight
				};
			});
			observer.observe(body.value);
			if (body.value.clientWidth > 0 && body.value.clientHeight > 0) size.value = {
				width: body.value.clientWidth,
				height: body.value.clientHeight
			};
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
			queuedAction = "";
			close();
			contextTicket = "";
			clearPreviews();
			model.value = initial();
		});
		onBeforeUnmount(() => {
			generation++;
			clearTimeout(timer);
			observer?.disconnect();
			clearPreviews();
		});
		__expose({ open });
		return (_ctx, _cache) => {
			return openBlock(), createBlock(Teleport, { to: "body" }, [createVNode(_sfc_main$5, {
				ref_key: "dialog",
				ref: dialog,
				title: "External agent",
				"window-kind": "agent_request",
				class: "agent-request-dialog",
				"close-on-outside": false,
				onClosed: schedule
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "body",
					ref: body,
					class: "agent-request-body",
					onPaste: paste,
					onDragover: _cache[1] || (_cache[1] = withModifiers(() => {}, ["prevent"])),
					onDrop: _cache[2] || (_cache[2] = withModifiers(($event) => addFiles([...$event.dataTransfer.files]), ["prevent"]))
				}, [createBaseVNode("input", {
					ref_key: "fileInput",
					ref: fileInput,
					type: "file",
					multiple: "",
					hidden: "",
					"aria-label": unref(t)("Attach files"),
					onChange: _cache[0] || (_cache[0] = ($event) => addFiles([...$event.target.files]))
				}, null, 40, _hoisted_1), createVNode(_sfc_main$4, {
					scene: scene.value,
					views: views.value,
					onEvent: event
				}, null, 8, ["scene", "views"])], 544)]),
				_: 1
			}, 512)]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=AgentRequest.js.map
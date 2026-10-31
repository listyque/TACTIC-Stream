import { A as onMounted, E as nextTick, G as withCtx, K as withDirectives, L as resolveDynamicComponent, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, o as vModelText, p as computed, rt as toDisplayString, s as vShow, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { a as _sfc_main$2, o as t, s as appearance, t as _sfc_main$3 } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { H as node, I as _sfc_main$5, U as rect, g as copyText, n as observeFrameSizes, r as _sfc_main$4, y as translate, z as label } from "./resize.js";
import { t as _sfc_main$6 } from "./AppearanceControls.js";
import { t as _sfc_main$7 } from "./CodeBlock.js";
//#region ../src/tactic_stream/shared_ui/features/support/documentation/api.ui.mjs
function methods(catalog, status, query, language) {
	query = String(query || "").toLowerCase();
	return (catalog || []).filter((record) => (status === "all" || status === "common" && record.status === "available" && (query || record.examples?.length) || record.status === status) && `${record.name} ${record.signature} ${record.help?.[language] || record.help?.en || ""} ${record.reference}`.toLowerCase().includes(query));
}
function method(record, selected, common, width, language) {
	const example = common && record.examples?.length ? translate(record.examples[0].label, language) : "";
	const height = example ? 54 : 34;
	const children = [label("apiMethodName", rect(10, example ? 27 : 5, Math.max(0, width - 60), 24), record.name)];
	if (example) children.push(label("apiMethodExample", rect(10, 3, Math.max(0, width - 20), 24), example, { weight: 600 }));
	if (record.writes) children.push(label("apiMethodWrites", rect(Math.max(0, width - 50), example ? 27 : 5, 45, 24), translate("Write", language), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	return {
		nodes: [node("Action", "apiMethod-" + record.name, rect(0, 0, width, height), {
			text: record.name,
			selected: record.name === selected,
			normalColor: "transparent",
			selectedColor: "selected",
			action: {
				type: "choose",
				name: record.name
			},
			children
		})],
		height
	};
}
function parameter(field, value, busy, width, language) {
	const tr = (text) => translate(text, language), controlY = 44;
	const height = field.type === "json" ? 150 : 86;
	const nodes = [label("apiFieldTitle", rect(0, 0, width, 22), tr(field.label), { weight: 600 }), label("apiFieldDescription", rect(0, 22, width, 18), field.description ? tr(field.description) : field.name, {
		fontRole: "caption",
		color: "secondaryText"
	})];
	const kind = field.type === "boolean" ? "Switch" : field.type === "json" ? "Area" : "Field";
	nodes.push(node(kind, "api-" + field.name, rect(0, controlY, width, height - controlY), {
		text: kind === "Switch" ? tr(field.label) : String(value ?? ""),
		label: tr(field.label),
		checked: !!value,
		enabled: !busy,
		error: field.error || "",
		inputType: field.type === "password" ? "password" : field.type === "number" ? "number" : "text",
		action: {
			type: "parameter",
			name: field.name
		},
		description: tr(field.description || "")
	}));
	return {
		nodes,
		height
	};
}
//#endregion
//#region src/features/documentation/ApiParameter.vue
var _sfc_main$1 = {
	__name: "ApiParameter",
	props: {
		field: Object,
		busy: Boolean
	},
	emits: ["change"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(300);
		const scene = computed(() => parameter(props.field, props.field.value, props.busy, width.value, appearance.language));
		let observer;
		onMounted(() => {
			observer = observeFrameSizes(() => width.value = host.value.clientWidth);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "api-parameter",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$4, {
				scene: scene.value,
				onEvent: _cache[0] || (_cache[0] = (action) => emit("change", action.value))
			}, null, 8, ["scene"])], 4);
		};
	}
};
//#endregion
//#region src/features/documentation/ApiDocumentation.vue
var _hoisted_1 = { class: "api-docs" };
var _hoisted_2 = { class: "api-docs-header" };
var _hoisted_3 = { href: "/" };
var _hoisted_4 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_5 = {
	key: 1,
	class: "api-docs-layout"
};
var _hoisted_6 = { class: "api-docs-navigation" };
var _hoisted_7 = ["aria-label"];
var _hoisted_8 = { class: "muted" };
var _hoisted_9 = ["aria-label"];
var _hoisted_10 = {
	key: 0,
	class: "api-docs-content"
};
var _hoisted_11 = { class: "content-heading" };
var _hoisted_12 = ["disabled", "aria-label"];
var _hoisted_13 = { class: "configuration-group api-method-heading" };
var _hoisted_14 = {
	key: 0,
	class: "api-method-help"
};
var _hoisted_15 = { class: "muted" };
var _hoisted_16 = { class: "configuration-group api-reference" };
var _hoisted_17 = { class: "muted" };
var _hoisted_18 = {
	key: 0,
	class: "muted"
};
var _hoisted_19 = {
	key: 1,
	class: "muted"
};
var _hoisted_20 = {
	key: 2,
	class: "notice"
};
var _hoisted_21 = {
	key: 3,
	class: "muted"
};
var _hoisted_22 = ["open"];
var _hoisted_23 = ["disabled"];
var _hoisted_24 = ["disabled"];
var _hoisted_25 = { class: "muted" };
var _hoisted_26 = { class: "configuration-group" };
var _hoisted_27 = { class: "muted" };
var _hoisted_28 = { key: 0 };
var _hoisted_29 = {
	key: 1,
	class: "muted"
};
var _hoisted_30 = { key: 0 };
var _hoisted_31 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_32 = {
	key: 0,
	class: "muted"
};
var _hoisted_33 = ["open"];
var _hoisted_34 = ["disabled", "aria-label"];
var _hoisted_35 = ["disabled", "aria-label"];
var _hoisted_36 = {
	key: 2,
	class: "muted"
};
var _hoisted_37 = { key: 3 };
var _hoisted_38 = ["aria-label"];
var _hoisted_39 = {
	key: 5,
	class: "configuration-group"
};
var _hoisted_40 = { class: "muted" };
var _hoisted_41 = { class: "configuration-group" };
var _hoisted_42 = { class: "api-signature" };
var _hoisted_43 = { class: "table-container" };
var _hoisted_44 = { key: 0 };
var _hoisted_45 = { class: "api-signature" };
var _hoisted_46 = { class: "configuration-group" };
var _hoisted_47 = { class: "configuration-group" };
var _hoisted_48 = { class: "api-signature" };
var _hoisted_49 = { class: "muted" };
var _hoisted_50 = { class: "muted" };
var _hoisted_51 = { href: "/openapi.json" };
var _hoisted_52 = { href: "/api/documentation" };
var _hoisted_53 = { href: "/api/compatibility" };
var _sfc_main = {
	__name: "ApiDocumentation",
	setup(__props) {
		const methodNav = ref(null), navWidth = ref(240);
		let observer;
		let alive = true;
		const catalogRequest = new AbortController();
		onBeforeUnmount(() => {
			alive = false;
			catalogRequest.abort();
			observer?.disconnect();
			token.value = "";
			password.value = "";
		});
		const catalog = ref(null);
		const error = ref("");
		const search = ref("");
		const status = ref("common");
		const selected = ref("query");
		const argumentsText = ref("[]");
		const keywordsText = ref("{}");
		const project = ref("");
		const login = ref("");
		const password = ref("");
		const token = ref("");
		const authenticatedLogin = ref("");
		const busy = ref(false);
		const result = ref(null);
		const elapsed = ref(null);
		const responseError = ref(false);
		const copied = ref(false);
		const exampleIndex = ref(0);
		const rawMode = ref(false);
		const parameterDrafts = ref({});
		const parameterErrors = ref({});
		const statuses = [
			{
				value: "common",
				label: "Common methods"
			},
			{
				value: "available",
				label: "Available entry points"
			},
			{
				value: "all",
				label: "All methods"
			},
			{
				value: "not_implemented",
				label: "Not migrated"
			},
			{
				value: "excluded",
				label: "Excluded"
			}
		];
		const parameterHelp = {
			search_type: {
				label: "Search type",
				description: "Object type to read, for example sthpw/project or your_project/asset."
			},
			search_key: {
				label: "Search key",
				description: "Copy __search_key__ from a query result."
			},
			limit: {
				label: "Maximum records",
				description: "Limit the number of records returned by this request."
			},
			offset: {
				label: "Skip records",
				description: "Number of records to skip before starting this page."
			},
			filters: {
				label: "Filters",
				description: "Use [] for all records, or pairs such as [[\"code\", \"admin\"]]."
			},
			columns: {
				label: "Columns",
				description: "Use null for all columns, or a list such as [\"code\", \"name\"]."
			},
			order_bys: {
				label: "Sort order",
				description: "A list such as [\"id asc\"] or [\"name desc\"]."
			},
			data: {
				label: "Object data",
				description: "A JSON object containing field names and their new values."
			}
		};
		try {
			login.value = localStorage.getItem("tactic_stream.lastLogin") || "";
			const session = JSON.parse(localStorage.getItem("tactic_stream.session"));
			if (typeof session?.project === "string") project.value = session.project;
			if (typeof session?.ticket === "string") token.value = session.ticket;
			if (typeof session?.login === "string") {
				login.value = session.login;
				authenticatedLogin.value = session.login;
			}
		} catch {}
		const methods$1 = computed(() => methods(catalog.value?.methods, status.value, search.value, appearance.language));
		const method$1 = computed(() => catalog.value?.methods.find((item) => item.name === selected.value));
		const methodOptions = computed(() => methods$1.value.map((item) => ({
			value: item.name,
			label: item.name
		})));
		const methodHelp = computed(() => method$1.value?.help?.[appearance.language] || method$1.value?.help?.en || "");
		const hasTicket = computed(() => method$1.value?.parameters.some((item) => item.name === "ticket"));
		const example = computed(() => method$1.value?.examples?.[exampleIndex.value]);
		const exampleOptions = computed(() => (method$1.value?.examples || []).map((item, index) => ({
			value: String(index),
			label: item.label
		})));
		const parameters = computed(() => {
			if (!requestPreview.value) return [];
			const args = JSON.parse(argumentsText.value);
			const kwargs = JSON.parse(keywordsText.value);
			return (method$1.value?.parameters || []).filter((item) => item.name !== "ticket").map((item, index) => {
				const value = index < args.length ? args[index] : Object.hasOwn(kwargs, item.name) ? kwargs[item.name] : item.default_value;
				const type = typeof value === "boolean" ? "boolean" : typeof value === "number" || ["limit", "offset"].includes(item.name) ? "number" : Array.isArray(value) || value !== null && typeof value === "object" || [
					"filters",
					"columns",
					"order_bys",
					"data",
					"kwargs",
					"values",
					"search_keys"
				].includes(item.name) ? "json" : item.name.includes("password") ? "password" : "text";
				return {
					...item,
					index,
					type,
					label: parameterHelp[item.name]?.label || item.name,
					description: parameterHelp[item.name]?.description || "",
					value: Object.hasOwn(parameterDrafts.value, item.name) ? parameterDrafts.value[item.name] : type === "json" ? JSON.stringify(value ?? null) : value ?? ""
				};
			});
		});
		const mainParameters = computed(() => parameters.value.filter((item) => item.required || ["filters", "limit"].includes(item.name)));
		const extraParameters = computed(() => parameters.value.filter((item) => !mainParameters.value.includes(item)));
		const parameterGroups = computed(() => [{
			extra: false,
			fields: mainParameters.value
		}, {
			extra: true,
			fields: extraParameters.value
		}]);
		const endpoint = computed(() => `${location.origin}/tactic/${encodeURIComponent(project.value)}/Api/`);
		const requestPreview = computed(() => {
			try {
				const args = JSON.parse(argumentsText.value);
				const kwargs = JSON.parse(keywordsText.value);
				if (!Array.isArray(args) || !kwargs || typeof kwargs !== "object" || Array.isArray(kwargs)) return null;
				return {
					method: selected.value,
					args: hasTicket.value ? [{
						ticket: "<ticket>",
						project: project.value,
						language: "python"
					}, ...args] : args,
					kwargs
				};
			} catch {
				return null;
			}
		});
		const xmlrpcExample = computed(() => {
			if (!requestPreview.value || !method$1.value || method$1.value.status !== "available") return "";
			const values = [];
			let index = 0;
			for (const parameter of method$1.value.parameters) {
				if (parameter.name === "ticket") continue;
				values.push(index < requestPreview.value.args.length - (hasTicket.value ? 1 : 0) ? requestPreview.value.args[index++ + (hasTicket.value ? 1 : 0)] : Object.hasOwn(requestPreview.value.kwargs, parameter.name) ? requestPreview.value.kwargs[parameter.name] : parameter.required ? `<${parameter.name}>` : parameter.default_value);
			}
			const auth = method$1.value.requires_ticket ? `token = api.get_ticket(${JSON.stringify(login.value)}, getpass('Password: '))\nticket = {'ticket': token, 'project': ${JSON.stringify(project.value)}, 'language': 'python'}\n` : "";
			return `import json\nfrom getpass import getpass\nfrom xmlrpc.client import ServerProxy\n\napi = ServerProxy(${JSON.stringify(endpoint.value)}, allow_none=True)\n${auth}args = json.loads(${JSON.stringify(JSON.stringify(values))})\nresult = api.${selected.value}(${hasTicket.value ? method$1.value.requires_ticket ? "ticket, " : "None, " : ""}*args)\nprint(result)`;
		});
		function choose(name, index = 0) {
			if (busy.value) return;
			selected.value = name;
			exampleIndex.value = index;
			const preset = method$1.value?.examples?.[index] || method$1.value?.example;
			argumentsText.value = JSON.stringify(preset?.args || [], null, 2);
			keywordsText.value = JSON.stringify(preset?.kwargs || {}, null, 2);
			rawMode.value = false;
			parameterDrafts.value = {};
			parameterErrors.value = {};
			error.value = "";
			result.value = null;
			elapsed.value = null;
			responseError.value = false;
			copied.value = false;
			history.replaceState(null, "", `#${encodeURIComponent(name)}`);
		}
		function editParameter(parameter, value) {
			parameterDrafts.value[parameter.name] = value;
			try {
				const parsed = parameter.type === "json" ? JSON.parse(value) : parameter.type === "number" ? value === "" ? null : Number(value) : value;
				if (parameter.type === "number" && parsed !== null && !Number.isFinite(parsed)) throw new Error();
				const args = JSON.parse(argumentsText.value);
				const kwargs = JSON.parse(keywordsText.value);
				if (parameter.index < args.length) args[parameter.index] = parsed;
				else kwargs[parameter.name] = parsed;
				argumentsText.value = JSON.stringify(args, null, 2);
				keywordsText.value = JSON.stringify(kwargs, null, 2);
				delete parameterErrors.value[parameter.name];
				error.value = "";
			} catch {
				parameterErrors.value[parameter.name] = parameter.type === "number" ? "Enter a number." : "Enter valid JSON for this field.";
			}
		}
		async function signIn() {
			busy.value = true;
			error.value = "";
			token.value = "";
			authenticatedLogin.value = "";
			try {
				const ticket = await rpc("get_ticket", [login.value, password.value]);
				if (!alive) return;
				token.value = ticket;
				authenticatedLogin.value = login.value;
			} catch (failure) {
				if (alive) error.value = failure.message;
			} finally {
				password.value = "";
				if (alive) busy.value = false;
			}
		}
		async function run() {
			result.value = null;
			responseError.value = false;
			if (!rawMode.value && Object.keys(parameterErrors.value).length) {
				error.value = "Correct the highlighted fields before running the request.";
				return;
			}
			if (!requestPreview.value) {
				error.value = "Arguments must be a JSON array and keyword arguments a JSON object.";
				return;
			}
			error.value = "";
			busy.value = true;
			const started = performance.now();
			try {
				const args = JSON.parse(argumentsText.value);
				if (hasTicket.value) args.unshift({
					ticket: token.value,
					project: project.value,
					language: "python"
				});
				const reply = await rpc(selected.value, args, JSON.parse(keywordsText.value));
				if (!alive) return;
				result.value = JSON.stringify(reply, null, 2);
			} catch (failure) {
				if (!alive) return;
				if (failure.code === "authentication_failed") {
					token.value = "";
					authenticatedLogin.value = "";
				}
				responseError.value = true;
				result.value = JSON.stringify({
					status: failure.status || null,
					code: failure.code || null,
					error: failure.message
				}, null, 2);
			} finally {
				if (alive) {
					elapsed.value = (performance.now() - started).toFixed(1);
					busy.value = false;
				}
			}
		}
		async function copyExample() {
			try {
				await copyText(xmlrpcExample.value);
				if (alive) copied.value = true;
			} catch {
				if (alive) error.value = "Select and copy the example text manually.";
			}
		}
		onMounted(async () => {
			try {
				const response = await fetch("/api/documentation", {
					cache: "no-store",
					signal: catalogRequest.signal
				});
				if (!response.ok) throw new Error("Unable to load API documentation.");
				const loaded = await response.json();
				if (!alive) return;
				catalog.value = loaded;
				const name = decodeURIComponent(location.hash.slice(1));
				choose(catalog.value.methods.some((item) => item.name === name) ? name : "query");
				await nextTick();
				if (!alive) return;
				observer = observeFrameSizes(() => navWidth.value = methodNav.value.clientWidth);
				observer.observe(methodNav.value);
			} catch (failure) {
				if (alive) error.value = failure.message;
			}
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1, [
				createBaseVNode("header", _hoisted_2, [
					createBaseVNode("strong", null, [createVNode(_sfc_main$2, { name: "code" }), createBaseVNode("span", null, toDisplayString(unref(t)("TACTIC API reference")), 1)]),
					createBaseVNode("a", _hoisted_3, toDisplayString(unref(t)("Workspace")), 1),
					createVNode(_sfc_main$6, { compact: "" })
				]),
				error.value ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
				catalog.value ? (openBlock(), createElementBlock("div", _hoisted_5, [createBaseVNode("aside", _hoisted_6, [
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Find a method")), 1), withDirectives(createBaseVNode("input", {
						"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => search.value = $event),
						type: "search",
						"aria-label": unref(t)("Find a method")
					}, null, 8, _hoisted_7), [[vModelText, search.value]])]),
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Method status")), 1), createVNode(_sfc_main$5, {
						modelValue: status.value,
						"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => status.value = $event),
						options: statuses,
						label: "Method status"
					}, null, 8, ["modelValue"])]),
					createBaseVNode("small", _hoisted_8, toDisplayString(unref(t)("{count} methods", { count: methods$1.value.length })), 1),
					createVNode(_sfc_main$5, {
						class: "api-docs-mobile-picker",
						"model-value": selected.value,
						options: methodOptions.value,
						label: "API method",
						"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => choose($event))
					}, null, 8, ["model-value", "options"]),
					createBaseVNode("nav", {
						ref_key: "methodNav",
						ref: methodNav,
						class: "api-docs-methods",
						"aria-label": unref(t)("API methods")
					}, [(openBlock(true), createElementBlock(Fragment, null, renderList(methods$1.value, (item) => {
						return openBlock(), createBlock(_sfc_main$4, {
							key: item.name,
							class: "api-method-record",
							style: normalizeStyle({ height: method(item, selected.value, status.value === "common", navWidth.value, unref(appearance).language).height + "px" }),
							scene: method(item, selected.value, status.value === "common", navWidth.value, unref(appearance).language),
							onEvent: _cache[3] || (_cache[3] = (action) => choose(action.name))
						}, null, 8, ["style", "scene"]);
					}), 128))], 8, _hoisted_9)
				]), method$1.value ? (openBlock(), createElementBlock("main", _hoisted_10, [
					createBaseVNode("header", _hoisted_11, [createBaseVNode("div", null, [createBaseVNode("h1", null, toDisplayString(method$1.value.name), 1)]), createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Project")), 1), withDirectives(createBaseVNode("input", {
						"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => project.value = $event),
						disabled: busy.value,
						"aria-label": unref(t)("Project")
					}, null, 8, _hoisted_12), [[vModelText, project.value]])])]),
					createBaseVNode("section", _hoisted_13, [
						methodHelp.value ? (openBlock(), createElementBlock("p", _hoisted_14, toDisplayString(methodHelp.value), 1)) : createCommentVNode("", true),
						createBaseVNode("strong", null, toDisplayString(unref(t)("Method call and inputs")), 1),
						createVNode(_sfc_main$7, {
							class: "api-signature",
							code: "api." + method$1.value.name + method$1.value.signature
						}, null, 8, ["code"]),
						createBaseVNode("p", _hoisted_15, toDisplayString(unref(t)("The signature lists input names and their defaults. Parameters without a default are required. Fill in the fields below; the console adds your ticket after sign-in.")), 1)
					]),
					createBaseVNode("details", _hoisted_16, [
						createBaseVNode("summary", null, toDisplayString(unref(t)("Original TACTIC reference")), 1),
						createBaseVNode("p", _hoisted_17, toDisplayString(unref(t)("Imported API/SDK documentation describes the original contract, including behavior that may not be migrated.")), 1),
						createBaseVNode("pre", null, toDisplayString(method$1.value.reference || unref(t)("The original method has no description.")), 1)
					]),
					method$1.value.status !== "available" ? (openBlock(), createElementBlock("p", _hoisted_18, toDisplayString(unref(t)(method$1.value.status === "excluded" ? "Excluded from this project." : "This method has not been migrated.")), 1)) : (openBlock(), createElementBlock("p", _hoisted_19, toDisplayString(unref(t)("Entry point available; full legacy parity is not verified.")), 1)),
					method$1.value.writes ? (openBlock(), createElementBlock("p", _hoisted_20, toDisplayString(unref(t)("This method can change data.")), 1)) : createCommentVNode("", true),
					method$1.value.reason ? (openBlock(), createElementBlock("p", _hoisted_21, toDisplayString(method$1.value.reason), 1)) : createCommentVNode("", true),
					method$1.value.requires_ticket ? (openBlock(), createElementBlock("details", {
						key: 4,
						class: "configuration-group api-connection",
						open: !token.value
					}, [
						createBaseVNode("summary", null, toDisplayString(token.value ? unref(t)("Signed in as {login}", { login: authenticatedLogin.value || login.value }) : unref(t)("Sign in to try the examples")), 1),
						createBaseVNode("form", {
							class: "api-docs-login",
							onSubmit: withModifiers(signIn, ["prevent"])
						}, [
							createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Login")), 1), withDirectives(createBaseVNode("input", {
								"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => login.value = $event),
								autocomplete: "username",
								disabled: busy.value
							}, null, 8, _hoisted_23), [[vModelText, login.value]])]),
							createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Password")), 1), withDirectives(createBaseVNode("input", {
								"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => password.value = $event),
								type: "password",
								autocomplete: "current-password",
								disabled: busy.value
							}, null, 8, _hoisted_24), [[vModelText, password.value]])]),
							createVNode(_sfc_main$3, {
								type: "submit",
								icon: "user",
								label: "Sign in",
								disabled: busy.value || !password.value
							}, null, 8, ["disabled"])
						], 32),
						createBaseVNode("p", _hoisted_25, toDisplayString(unref(t)(token.value ? "Ticket loaded. The server checks access on every call." : "Sign in to run methods that require a ticket.")), 1)
					], 8, _hoisted_22)) : createCommentVNode("", true),
					createBaseVNode("section", _hoisted_26, [
						createBaseVNode("h2", null, toDisplayString(unref(t)("Try the method")), 1),
						createBaseVNode("p", _hoisted_27, toDisplayString(unref(t)("Choose an example, adjust the fields and run the request.")), 1),
						exampleOptions.value.length ? (openBlock(), createElementBlock("label", _hoisted_28, [createTextVNode(toDisplayString(unref(t)("Ready example")), 1), createVNode(_sfc_main$5, {
							"model-value": String(exampleIndex.value),
							options: exampleOptions.value,
							disabled: busy.value,
							label: "Ready example",
							"onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => choose(selected.value, Number($event)))
						}, null, 8, [
							"model-value",
							"options",
							"disabled"
						])])) : createCommentVNode("", true),
						example.value ? (openBlock(), createElementBlock("p", _hoisted_29, toDisplayString(unref(t)(example.value.description)), 1)) : createCommentVNode("", true),
						createBaseVNode("form", { onSubmit: withModifiers(run, ["prevent"]) }, [
							!rawMode.value ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [(openBlock(true), createElementBlock(Fragment, null, renderList(parameterGroups.value, (group) => {
								return withDirectives((openBlock(), createBlock(resolveDynamicComponent(group.extra ? "details" : "div"), {
									key: String(group.extra),
									class: "api-parameters"
								}, {
									default: withCtx(() => [group.extra ? (openBlock(), createElementBlock("summary", _hoisted_30, toDisplayString(unref(t)("More parameters")), 1)) : createCommentVNode("", true), (openBlock(true), createElementBlock(Fragment, null, renderList(group.fields, (field) => {
										return openBlock(), createElementBlock("div", { key: field.name }, [
											createVNode(_sfc_main$1, {
												field: {
													...field,
													error: parameterErrors.value[field.name]
												},
												busy: busy.value,
												onChange: ($event) => editParameter(field, $event)
											}, null, 8, [
												"field",
												"busy",
												"onChange"
											]),
											createBaseVNode("small", null, [createBaseVNode("code", null, toDisplayString(field.name), 1), createTextVNode(" · " + toDisplayString(unref(t)(field.required ? "Required input" : "Optional input")), 1)]),
											parameterErrors.value[field.name] ? (openBlock(), createElementBlock("small", _hoisted_31, toDisplayString(unref(t)(parameterErrors.value[field.name])), 1)) : createCommentVNode("", true)
										]);
									}), 128))]),
									_: 2
								}, 1024)), [[vShow, group.fields.length]]);
							}), 128)), !parameters.value.length ? (openBlock(), createElementBlock("p", _hoisted_32, toDisplayString(unref(t)("This method needs no arguments.")), 1)) : createCommentVNode("", true)], 64)) : createCommentVNode("", true),
							createBaseVNode("details", {
								open: rawMode.value,
								onToggle: _cache[12] || (_cache[12] = ($event) => rawMode.value = $event.target.open)
							}, [
								createBaseVNode("summary", null, toDisplayString(unref(t)("Raw JSON")), 1),
								createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Positional arguments (without ticket)")), 1), withDirectives(createBaseVNode("textarea", {
									"onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => argumentsText.value = $event),
									rows: "5",
									disabled: busy.value,
									"aria-label": unref(t)("Positional arguments (without ticket)"),
									spellcheck: "false",
									onInput: _cache[9] || (_cache[9] = ($event) => {
										parameterDrafts.value = {};
										parameterErrors.value = {};
									})
								}, null, 40, _hoisted_34), [[vModelText, argumentsText.value]])]),
								createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Keyword arguments")), 1), withDirectives(createBaseVNode("textarea", {
									"onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => keywordsText.value = $event),
									rows: "3",
									disabled: busy.value,
									"aria-label": unref(t)("Keyword arguments"),
									spellcheck: "false",
									onInput: _cache[11] || (_cache[11] = ($event) => {
										parameterDrafts.value = {};
										parameterErrors.value = {};
									})
								}, null, 40, _hoisted_35), [[vModelText, keywordsText.value]])])
							], 40, _hoisted_33),
							createVNode(_sfc_main$3, {
								type: "submit",
								highlighted: "",
								icon: "code",
								label: busy.value ? "Running…" : method$1.value.writes ? "Run write method" : "Run method",
								disabled: busy.value || method$1.value.status !== "available" || method$1.value.requires_ticket && !token.value
							}, null, 8, ["label", "disabled"])
						], 32),
						elapsed.value !== null ? (openBlock(), createElementBlock("p", _hoisted_36, toDisplayString(unref(t)("HTTP round trip: {duration} ms", { duration: elapsed.value })), 1)) : createCommentVNode("", true),
						result.value !== null ? (openBlock(), createElementBlock("strong", _hoisted_37, toDisplayString(unref(t)("Method response")), 1)) : createCommentVNode("", true),
						result.value !== null ? (openBlock(), createElementBlock("pre", {
							key: 4,
							class: normalizeClass(["api-result", { error: responseError.value }]),
							role: "status",
							tabindex: "0",
							"aria-label": unref(t)("Method response")
						}, toDisplayString(result.value), 11, _hoisted_38)) : createCommentVNode("", true)
					]),
					xmlrpcExample.value ? (openBlock(), createElementBlock("details", _hoisted_39, [
						createBaseVNode("summary", null, toDisplayString(unref(t)("Python XML-RPC example")), 1),
						createBaseVNode("p", _hoisted_40, toDisplayString(unref(t)("This Python example follows the fields above. Copy it into a script and enter your password when prompted.")), 1),
						createVNode(_sfc_main$3, {
							icon: "copy",
							label: copied.value ? "Copied" : "Copy example",
							onClick: copyExample
						}, null, 8, ["label"]),
						createVNode(_sfc_main$7, { code: xmlrpcExample.value }, null, 8, ["code"])
					])) : createCommentVNode("", true),
					createBaseVNode("details", _hoisted_41, [
						createBaseVNode("summary", null, toDisplayString(unref(t)("All parameters and defaults")), 1),
						createBaseVNode("code", _hoisted_42, toDisplayString(method$1.value.name) + toDisplayString(method$1.value.signature), 1),
						createBaseVNode("div", _hoisted_43, [createBaseVNode("table", null, [createBaseVNode("thead", null, [createBaseVNode("tr", null, [
							createBaseVNode("th", null, toDisplayString(unref(t)("Parameter")), 1),
							createBaseVNode("th", null, toDisplayString(unref(t)("Required")), 1),
							createBaseVNode("th", null, toDisplayString(unref(t)("Default")), 1)
						])]), createBaseVNode("tbody", null, [(openBlock(true), createElementBlock(Fragment, null, renderList(method$1.value.parameters, (parameter) => {
							return openBlock(), createElementBlock("tr", { key: parameter.name }, [
								createBaseVNode("td", null, [createBaseVNode("code", null, toDisplayString(parameter.name), 1)]),
								createBaseVNode("td", null, toDisplayString(unref(t)(parameter.required ? "Yes" : "No")), 1),
								createBaseVNode("td", null, [createBaseVNode("code", null, toDisplayString(parameter.default ?? "—"), 1)])
							]);
						}), 128))])])]),
						method$1.value.signature !== method$1.value.original_signature ? (openBlock(), createElementBlock("details", _hoisted_44, [createBaseVNode("summary", null, toDisplayString(unref(t)("Original signature")), 1), createBaseVNode("code", _hoisted_45, toDisplayString(method$1.value.name) + toDisplayString(method$1.value.original_signature), 1)])) : createCommentVNode("", true)
					]),
					createBaseVNode("details", _hoisted_46, [
						createBaseVNode("summary", null, toDisplayString(unref(t)("JSON request")), 1),
						createBaseVNode("code", null, toDisplayString(catalog.value.json_route), 1),
						createBaseVNode("pre", null, toDisplayString(JSON.stringify(requestPreview.value, null, 2)), 1)
					]),
					createBaseVNode("details", _hoisted_47, [
						createBaseVNode("summary", null, toDisplayString(unref(t)("Connection and technical details")), 1),
						createBaseVNode("code", _hoisted_48, toDisplayString(endpoint.value), 1),
						createBaseVNode("p", _hoisted_49, toDisplayString(unref(t)("XML-RPC and this console use the same server logic, authorization and data. The console sends JSON; XML-RPC retains its original response formats.")), 1),
						createBaseVNode("p", _hoisted_50, toDisplayString(unref(t)("XML-RPC faults use these codes. JSON returns HTTP status with error and error_code.")), 1),
						createBaseVNode("pre", null, toDisplayString(JSON.stringify({
							"XML-RPC": catalog.value.xmlrpc_errors,
							JSON: catalog.value.json_errors
						}, null, 2)), 1),
						createBaseVNode("a", _hoisted_51, toDisplayString(unref(t)("HTTP transport schema (OpenAPI)")), 1),
						createBaseVNode("a", _hoisted_52, toDisplayString(unref(t)("Method catalog (JSON)")), 1),
						createBaseVNode("a", _hoisted_53, toDisplayString(unref(t)("Compatibility inventory (JSON)")), 1)
					])
				])) : createCommentVNode("", true)])) : createCommentVNode("", true)
			]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=ApiDocumentation.js.map
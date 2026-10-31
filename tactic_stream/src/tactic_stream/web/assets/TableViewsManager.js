import { G as withCtx, H as watch, M as openBlock, O as onBeforeUnmount, X as ref, b as createVNode, et as unref, h as createBlock, m as createBaseVNode, p as computed, q as isRef } from "./vue.js";
import { s as appearance } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { t as _sfc_main$1, w as observeFrameSizes } from "./FrameView.js";
import { dt as describe, ft as initial, gt as transition, ht as rows, mt as row, pt as loaded } from "./ConfiguredView.js";
import { t as _sfc_main$2 } from "./AppDialog.js";
//#region src/features/interface/TableViewsManager.vue
var _sfc_main = {
	__name: "TableViewsManager",
	props: {
		ticket: String,
		project: String,
		searchType: String,
		current: String
	},
	emits: [
		"use",
		"configure",
		"changed"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const dialog = ref(null), host = ref(null), ui = ref(initial());
		const model = ref({
			views: [],
			busy: false,
			error: "",
			uncertain: false
		});
		const size = ref({
			width: 900,
			height: 590
		});
		let observer, generation = 0, context;
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
		const scene = computed(() => describe(model.value, ui.value, size.value.width, size.value.height, appearance.language));
		watch(() => [
			props.ticket,
			props.project,
			props.searchType
		], () => {
			generation++;
			dialog.value?.close();
			context = null;
		});
		onBeforeUnmount(() => {
			generation++;
			observer?.disconnect();
		});
		async function call(command) {
			if (!context || model.value.busy) return;
			const id = ++generation, captured = { ...context };
			model.value = {
				...model.value,
				busy: true,
				error: ""
			};
			try {
				const result = await rpc("execute_cmd", [
					{
						ticket: captured.ticket,
						project: captured.project
					},
					"tactic.ui.table.views.TableViewsCmd",
					{
						search_type: captured.searchType,
						current: model.value.current || captured.current,
						...command
					}
				], {}, true);
				if (id !== generation) return;
				if (result.status !== "OK") throw Error(result.description || "Table views could not be loaded");
				let info = typeof result.info === "string" ? JSON.parse(result.info) : result.info;
				if (command.action !== "read") {
					const fresh = await rpc("execute_cmd", [
						{
							ticket: captured.ticket,
							project: captured.project
						},
						"tactic.ui.table.views.TableViewsCmd",
						{
							search_type: captured.searchType,
							current: info.current,
							action: "read"
						}
					], {}, true);
					if (id !== generation) return;
					if (fresh.status !== "OK") throw Error(fresh.description || "Table views could not be loaded");
					info = {
						...typeof fresh.info === "string" ? JSON.parse(fresh.info) : fresh.info,
						selected: info.selected
					};
				}
				model.value = {
					...info,
					busy: false,
					error: "",
					uncertain: false
				};
				ui.value = loaded(ui.value, model.value);
				if (command.action !== "read") emit("changed", info);
			} catch (error) {
				if (id === generation) model.value = {
					...model.value,
					busy: false,
					error: error.message,
					uncertain: command.action !== "read"
				};
			}
		}
		function event(action) {
			const next = transition(ui.value, model.value, action);
			ui.value = next.ui;
			if (!next.command) return;
			const command = next.command;
			if (command.action === "use" || command.action === "configure") {
				emit(command.action, command.view);
				dialog.value.close();
			} else call(command);
		}
		async function open() {
			context = {
				ticket: props.ticket,
				project: props.project,
				searchType: props.searchType,
				current: props.current || "table"
			};
			ui.value = initial();
			ui.value.selected = context.current;
			model.value = {
				views: [],
				busy: false,
				error: "",
				uncertain: false,
				...context
			};
			dialog.value.show();
			await call({ action: "read" });
		}
		__expose({ open });
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$2, {
				ref_key: "dialog",
				ref: dialog,
				title: "Table views manager",
				"window-kind": "table_views",
				class: "table-views-manager",
				"close-on-outside": false,
				"close-on-escape": !model.value.busy,
				onClosed: _cache[0] || (_cache[0] = ($event) => isRef(generation) ? generation.value++ : generation++)
			}, {
				default: withCtx(() => [createBaseVNode("div", {
					ref_key: "host",
					ref: host,
					class: "table-views-manager-body"
				}, [createVNode(_sfc_main$1, {
					scene: scene.value,
					models: { views: rows(model.value, ui.value) },
					"describe-row": (list, record) => row(list, record, ui.value, model.value, unref(appearance).language),
					onEvent: event
				}, null, 8, [
					"scene",
					"models",
					"describe-row"
				])], 512)]),
				_: 1
			}, 8, ["close-on-escape"]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TableViewsManager.js.map
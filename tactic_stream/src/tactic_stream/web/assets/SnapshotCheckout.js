import { A as onMounted, E as nextTick, H as watch, I as resolveDirective, J as markRaw, K as withDirectives, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, h as createBlock, l as withModifiers, m as createBaseVNode, p as computed, rt as toDisplayString } from "./vue.js";
import { _ as controls, o as t, s as appearance, t as _sfc_main$2 } from "./AppButton.js";
import { k as rpc, o as fileBlob } from "./index.js";
import { B as node, L as button, R as label, V as rect, n as observeFrameSizes, r as _sfc_main$3, v as translate } from "./resize.js";
import { t as captionHeight } from "./sections.ui.js";
import { i as sourceIcon, r as prettySize } from "./file_values.js";
import { t as downloadBlob } from "./files2.js";
import { t as describe$1 } from "./confirmation.ui.js";
import { t as _sfc_main$4 } from "./FrameProgress.js";
//#region ../src/tactic_stream/shared_ui/features/files/snapshot_checkout.ui.mjs
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language), margin = 10, inner = Math.max(0, width - 20), stacked = width < 370, footerHeight = stacked ? 100 : 60, closeWidth = stacked ? inner : 120;
	const nodes = [node("Box", "snapshotCheckoutSurface", rect(0, 0, width, height), {
		background: "surfaceContainerHigh",
		radius: 0
	})];
	if (model.conflict) return { nodes: nodes.concat(describe$1({
		message: tr("The local file differs from the server. Replace it?"),
		accept: "Overwrite",
		destructive: true
	}, width, height, language).nodes) };
	let y = margin;
	nodes.push(label("snapshotCheckoutContext", rect(margin, y, inner, 24), model.context || "", { color: "secondaryText" }));
	y += 32;
	for (const [name, text, error] of [[
		"error",
		model.error,
		true
	], [
		"message",
		model.message,
		false
	]]) {
		if (!text) continue;
		const textHeight = Math.max(24, captionHeight(text, inner - 16) + 12);
		const viewport = Math.min(textHeight, Math.max(48, Math.min(104, height / 3)));
		nodes.push(node("Scroll", "snapshotCheckoutNotice_" + name, rect(margin, y, inner, viewport), {
			contentHeight: textHeight,
			scrollbarId: "snapshotCheckoutNoticeScrollBar_" + name,
			children: [label("snapshotCheckout_" + name, rect(0, 0, inner - 16, textHeight), text, {
				wrap: true,
				fontRole: "caption",
				color: error ? "error" : "secondaryText",
				role: error ? "alert" : "status"
			})]
		}));
		y += viewport + 8;
	}
	if (model.loading || model.busy) {
		nodes.push(node("View", "snapshotCheckoutProgress", rect(margin, y, inner, controls.feedback.progressHeight), {
			view: "progress",
			min: 0,
			max: 1,
			indeterminate: !!model.loading || !!model.busy && typeof model.progress !== "number",
			value: Number(model.progress) || 0,
			label: tr(model.loading ? "Loading data…" : "Downloading")
		}));
		y += controls.feedback.progressHeight + 8;
	}
	nodes.push(node("List", "snapshotCheckoutFiles", rect(margin, y, inner, Math.max(0, height - y - footerHeight - 4)), {
		source: "files",
		keyField: "token",
		rowHeight: 62,
		rowGap: 4,
		label: tr("Files"),
		role: "listbox",
		scrollbarId: "snapshotCheckoutFilesScrollBar",
		fields: [
			"token",
			"title",
			"fileType",
			"bytes",
			"selected",
			"enabled"
		]
	}));
	if (!model.loading && !model.count) nodes.push(label("snapshotCheckoutEmpty", rect(margin, y + 12, inner, 40), tr("No files"), { color: "secondaryText" }));
	nodes.push(button("snapshotCheckoutClose", rect(margin, height - footerHeight + (stacked ? 6 : 12), closeWidth, 38), tr("Close"), "close", { type: "close" }, true));
	nodes.push(button("snapshotCheckoutDownload", rect(stacked ? margin : margin + closeWidth + 8, height - 48, stacked ? inner : Math.max(0, inner - closeWidth - 8), 38), tr(model.busy ? "Cancel transfer" : "Check out"), model.busy ? "cancel" : "download", { type: model.busy ? "cancelTransfer" : "checkout" }, !!model.busy || !!model.ready && !!model.count, { highlighted: !model.busy }));
	return { nodes };
}
function fileRow(record, width, language) {
	return { nodes: [node("Action", "snapshotCheckoutFile_" + record.token, rect(0, 0, width, 58), {
		text: record.title,
		enabled: record.enabled !== false,
		selected: !!record.selected,
		selectedColor: "contentSelection",
		role: "option",
		action: {
			type: "select",
			token: record.token
		},
		children: [
			node("Icon", "snapshotCheckoutIcon_" + record.token, rect(12, 20, 18, 18), {
				icon: sourceIcon(record.title),
				color: "action"
			}),
			label("snapshotCheckoutName_" + record.token, rect(42, 7, Math.max(0, width - 54), 22), record.title, {
				elideMiddle: true,
				pointerTransparent: true
			}),
			label("snapshotCheckoutSize_" + record.token, rect(42, 33, Math.max(0, width - 54), 18), [record.fileType, prettySize(record.bytes)].filter(Boolean).join(" · "), {
				fontRole: "caption",
				color: "secondaryText",
				pointerTransparent: true
			})
		]
	})] };
}
//#endregion
//#region src/features/checkin/SnapshotCheckoutSurface.vue
var _hoisted_1$1 = ["aria-busy"];
var _sfc_main$1 = {
	__name: "SnapshotCheckoutSurface",
	props: {
		model: Object,
		files: Array
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), size = ref({
			width: 0,
			height: 0
		});
		const views = { progress: {
			component: markRaw(_sfc_main$4),
			nodeProps: true
		} };
		const scene = computed(() => size.value.width > 0 && size.value.height > 0 ? describe(props.model, size.value.width, size.value.height, appearance.language) : { nodes: [] });
		const describeRow = (list, row) => fileRow(row, list.width - 16, appearance.language);
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				if (box.width > 0 && box.height > 0) size.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "snapshot-checkout-workspace",
				"aria-busy": __props.model.loading || __props.model.busy
			}, [createVNode(_sfc_main$3, {
				scene: scene.value,
				models: { files: __props.files },
				views,
				"describe-row": describeRow,
				onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
			}, null, 8, ["scene", "models"])], 8, _hoisted_1$1);
		};
	}
};
//#endregion
//#region src/features/checkin/SnapshotCheckout.vue
var _hoisted_1 = ["aria-label"];
var _sfc_main = {
	__name: "SnapshotCheckout",
	props: {
		ticket: String,
		project: String
	},
	setup(__props, { expose: __expose }) {
		const props = __props;
		const dialog = ref(null), snapshot = ref(null), files = ref([]), selected = ref("");
		const loading = ref(false), ready = ref(false), busy = ref(false), progress = ref(0), error = ref(""), message = ref("");
		let recordKey = "", generation = 0, download, scope;
		const rows = computed(() => files.value.map((file, index) => ({
			token: String(file.code || index),
			title: file.filename,
			fileType: file.type || "",
			bytes: file.size || 0,
			selected: String(file.code || index) === selected.value,
			enabled: !busy.value
		})));
		const model = computed(() => ({
			loading: loading.value,
			ready: ready.value,
			busy: busy.value,
			progress: progress.value,
			error: t(error.value),
			message: t(message.value),
			count: files.value.length,
			context: snapshot.value?.context || ""
		}));
		const title = computed(() => t("Check out") + (snapshot.value ? " · " + snapshot.value.code + " · v" + snapshot.value.version : ""));
		const style = { "--checkout-header-height": controls.dialog.headerHeight + "px" };
		function close() {
			generation++;
			download?.abort();
			download = null;
			dialog.value?.close();
			files.value = [];
			snapshot.value = null;
			progress.value = 0;
			busy.value = loading.value = ready.value = false;
		}
		async function open(record) {
			close();
			recordKey = record.__search_key__;
			const request = generation;
			scope = {
				ticket: props.ticket,
				project: props.project
			};
			loading.value = true;
			error.value = message.value = "";
			await nextTick();
			if (request !== generation) return;
			dialog.value.showModal();
			try {
				const response = await rpc("execute_cmd", [
					scope,
					"tactic.ui.table.TableSnapshotFilesCmd",
					{ search_key: record.__search_key__ }
				]);
				if (request !== generation) return;
				snapshot.value = response.info.snapshot;
				files.value = response.info.files.toSorted((first, second) => {
					const fields = (file) => [
						file.type !== "main",
						file.filename,
						file.type || "",
						String(file.code || "")
					];
					const a = fields(first), b = fields(second);
					for (let index = 0; index < a.length; index++) {
						if (a[index] < b[index]) return -1;
						if (a[index] > b[index]) return 1;
					}
					return 0;
				});
				const first = Math.max(0, files.value.findIndex((file) => file.type === "main"));
				selected.value = files.value.length ? String(files.value[first].code || first) : "";
				ready.value = true;
			} catch (failure) {
				if (request === generation) error.value = failure.message;
			} finally {
				if (request === generation) loading.value = false;
			}
		}
		async function activate(action) {
			if (action.type === "cancelTransfer") {
				download?.abort();
				return;
			}
			if (action.type === "close") {
				close();
				return;
			}
			if (busy.value || !ready.value) return;
			if (action.type === "select") {
				selected.value = action.token;
				progress.value = 0;
				message.value = error.value = "";
				return;
			}
			if (action.type !== "checkout") return;
			const file = files.value.find((file, index) => String(file.code || index) === selected.value);
			if (!file) return;
			const members = file.members?.length ? file.members : [file];
			const request = generation;
			busy.value = true;
			progress.value = 0;
			error.value = message.value = "";
			download = new AbortController();
			try {
				for (const [index, member] of members.entries()) {
					const blob = await fileBlob(member, { signal: download.signal });
					if (request !== generation) return;
					downloadBlob(blob, member.filename);
					progress.value = (index + 1) / members.length;
				}
				if (request === generation) message.value = "Download completed";
			} catch (failure) {
				if (request === generation) {
					if (failure.name === "AbortError") message.value = "Download cancelled";
					else error.value = failure.message;
				}
			} finally {
				if (request === generation) {
					busy.value = false;
					download = null;
				}
			}
		}
		watch(() => [props.ticket, props.project], () => close());
		onBeforeUnmount(() => close());
		function windowContext() {
			if (busy.value || loading.value) throw Error("Please wait for the current operation to finish");
			return {
				project: props.project,
				route: { args: [{ __search_key__: recordKey }] }
			};
		}
		__expose({
			open,
			close,
			windowContext
		});
		return (_ctx, _cache) => {
			const _directive_window = resolveDirective("window");
			return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
				ref_key: "dialog",
				ref: dialog,
				class: "record-dialog snapshot-checkout",
				style,
				"aria-label": unref(t)("Check out"),
				onCancel: _cache[1] || (_cache[1] = withModifiers(($event) => close(), ["prevent"]))
			}, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(title.value), 1), createVNode(_sfc_main$2, {
				label: "Close",
				icon: "close",
				"icon-only": "",
				onClick: _cache[0] || (_cache[0] = ($event) => close())
			})]), createVNode(_sfc_main$1, {
				model: model.value,
				files: rows.value,
				onEvent: activate
			}, null, 8, ["model", "files"])], 40, _hoisted_1)), [[_directive_window, {
				type: "dialog",
				kind: "snapshot_checkout",
				page: windowContext
			}]])]);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=SnapshotCheckout.js.map
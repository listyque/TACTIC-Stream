import { A as onMounted, E as nextTick, F as resolveComponent, I as resolveDirective, K as withDirectives, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, f as Teleport, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, s as vShow } from "./vue.js";
import { L as _plugin_vue_export_helper_default, o as t, s as appearance, t as _sfc_main$2 } from "./AppButton.js";
import { w as rawDatabase } from "./index.js";
import { B as node, L as button, R as label, V as rect, n as observeFrameSizes, r as _sfc_main$3, v as translate, z as muted } from "./resize.js";
import { n as notices, o as toolbar, r as policy, t as documentEvent } from "./admin.document.js";
//#region ../src/tactic_stream/shared_ui/features/administration/database/raw.state.mjs
function initial() {
	return {
		query: "",
		confirmation: "",
		dropName: "",
		dropIdentity: ""
	};
}
function permissions(model) {
	const allow = policy(model), clean = !!model.ready && !model.busy && !model.dirty && !model.uncertain;
	return Object.assign(allow, {
		navigate: !model.busy && !model.dirty && !model.uncertain,
		add: allow.editable && model.rows.length < 200,
		export: clean && allow.editable,
		drop: clean && allow.editable,
		previous: clean && allow.editable && model.metadata.offset > 0,
		next: clean && allow.editable && model.metadata.offset + 50 < model.metadata.total
	});
}
function transition(ui, model, event) {
	const allow = permissions(model);
	if (event.type === "confirm" && ui.confirmation === "drop") {
		if (!allow.drop || ui.dropIdentity !== model.identity || ui.dropName !== model.metadata.label) return {
			ui,
			commands: []
		};
		return {
			ui: Object.assign({}, ui, { confirmation: "" }),
			commands: [{
				type: "drop",
				name: ui.dropName
			}]
		};
	}
	const document = documentEvent(ui, model, event);
	if (document) return document;
	const next = Object.assign({}, ui), commands = [];
	switch (event.type) {
		case "query":
			if (allow.navigate && !ui.confirmation) next.query = String(event.value);
			break;
		case "select":
			if (allow.navigate && !ui.confirmation) commands.push({
				type: "select",
				identity: event.value
			});
			break;
		case "add":
			if (allow.add && !ui.confirmation) {
				commands.push({ type: "add" });
				if (model.columns.length) commands.push({
					type: "focusGrid",
					grid: "rawTableViewport",
					row: model.rows.length,
					column: 0,
					id: "rawCell_" + model.rows.length + "_" + model.columns[0].name
				});
			}
			break;
		case "deleteRow":
			if (allow.editable && event.row >= 0 && event.row < model.rows.length) commands.push({
				type: "deleteRow",
				row: event.row
			});
			break;
		case "cell":
			if (!model.busy && event.row >= 0 && event.row < model.rows.length && !model.rows[event.row].deleted && model.columns.some((column) => column.name === event.name)) commands.push({
				type: "cell",
				row: event.row,
				name: event.name
			});
			break;
		case "navigateCell": {
			const row = event.row + event.dy, column = event.column + event.dx;
			if (!model.busy && row >= 0 && row < model.rows.length && column >= 0 && column < model.columns.length) commands.push({
				type: "focusGrid",
				grid: "rawTableViewport",
				row,
				column,
				id: "rawCell_" + row + "_" + model.columns[column].name
			});
			break;
		}
		case "previous":
			if (allow.previous) commands.push({
				type: "page",
				offset: Math.max(0, model.metadata.offset - 50)
			});
			break;
		case "next":
			if (allow.next) commands.push({
				type: "page",
				offset: model.metadata.offset + 50
			});
			break;
		case "export":
			if (allow.export) commands.push({ type: "export" });
			break;
		case "drop":
			if (allow.drop) {
				next.confirmation = "drop";
				next.dropName = "";
				next.dropIdentity = model.identity;
			}
			break;
		case "dropName":
			if (!model.busy && ui.confirmation === "drop") next.dropName = String(event.value);
			break;
		default: throw Error("Unsupported Raw database event: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
function cellInitial(cell) {
	return {
		mode: cell.mode || "value",
		text: cell.text || "",
		session: cell.session
	};
}
function cellTransition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], editable = !model.readonly && !model.busy;
	switch (event.type) {
		case "text":
			if (editable && ui.mode === "value") next.text = String(event.value);
			break;
		case "mode":
			if (editable && (event.value === "value" || event.value === "null" || event.value === "default" && model.newRow)) next.mode = event.value;
			break;
		case "apply":
			if (editable) commands.push({
				type: "apply",
				mode: ui.mode,
				text: ui.text
			});
			break;
		case "cancel":
			commands.push({ type: "cancel" });
			break;
		default: throw Error("Unsupported Cell editor event: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/database/raw.ui.mjs
function cellText$1(row, name) {
	const mode = (row.modes || {})[name] || (row.key == null ? "default" : "value");
	return mode === "null" ? "NULL" : mode === "default" ? "DEFAULT" : (row.texts || {})[name] || "";
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const scene = describeBody(model, ui, width, height, language);
	if (scene.minimumHeight <= height) return { nodes: scene.nodes };
	const inner = Math.max(1, width - 16), contentHeight = describeBody(model, ui, inner, 0, language).minimumHeight;
	return { nodes: [node("Scroll", "rawPageScroll", rect(0, 0, width, height), {
		contentHeight,
		scrollbarId: "rawPageScrollBar",
		children: describeBody(model, ui, inner, contentHeight, language).nodes
	})] };
}
function describeBody(model, ui, width, height, language) {
	const tr = (text) => translate(text, language), allow = permissions(model), dropping = ui.confirmation === "drop", locked = !!ui.confirmation;
	const notice = notices(model, dropping ? Object.assign({}, ui, { confirmation: "" }) : ui, width, language, "Discard unsaved raw table changes?"), nodes = notice.nodes;
	let y = notice.top;
	const warningHeight = width < 600 ? 68 : 46, helpHeight = width < 600 ? 60 : 36;
	nodes.push(node("Box", "rawWarning", rect(0, y, width, warningHeight), {
		background: "contentSelection",
		border: "outlineVariant",
		children: [label("rawWarningText", rect(12, 6, width - 24, warningHeight - 12), tr("Raw SQL bypasses object validation, triggers and undo history. Changes can break the application."), { wrap: true })]
	}));
	y += warningHeight + 8;
	nodes.push(label("rawCellHelp", rect(0, y, width, helpHeight), tr("Open a cell to edit its value. Text needs no quotes. Choose NULL or Database default explicitly in the cell editor."), Object.assign({ wrap: true }, muted)));
	y += helpHeight + 8;
	const compact = width < 470, addWidth = compact ? 38 : language === "ru" ? 152 : 122, exportWidth = compact ? 38 : 142, dropWidth = compact ? 38 : 146;
	const actionsWidth = addWidth + exportWidth + dropWidth + 16;
	const stacked = width < 900, searchWidth = stacked ? (width - 8) / 2 : Math.max(1, width - 236 - actionsWidth), selectWidth = stacked ? searchWidth : 220;
	nodes.push(node("Field", "rawTableFilter", rect(0, y, searchWidth, 38), {
		text: ui.query,
		label: tr("Filter tables"),
		placeholder: tr("Filter tables"),
		enabled: allow.navigate && !locked,
		action: { type: "query" }
	}), node("Choice", "rawTableSelector", rect(searchWidth + 8, y, selectWidth, 38), {
		value: model.identity,
		options: model.catalog.filter((row) => row.identity === model.identity || row.label.toLowerCase().indexOf(ui.query.toLowerCase()) >= 0).map((row) => ({
			value: row.identity,
			label: row.label
		})),
		label: tr("Database table"),
		enabled: allow.navigate && !locked,
		action: { type: "select" }
	}));
	const actionY = y + (stacked ? 46 : 0), actionX = stacked ? 0 : searchWidth + selectWidth + 16;
	nodes.push(node("Box", "rawRowActions", rect(actionX, actionY, actionsWidth, 38), { children: [
		button("rawNewRow", rect(0, 0, addWidth, 38), tr("New row"), "add", { type: "add" }, allow.add && !locked, { iconOnly: compact }),
		button("rawExportCsv", rect(addWidth + 8, 0, exportWidth, 38), tr("Export CSV"), "download", { type: "export" }, allow.export && !locked, { iconOnly: compact }),
		button("rawDropTable", rect(addWidth + exportWidth + 16, 0, dropWidth, 38), tr("DROP TABLE"), "delete", { type: "drop" }, allow.drop && !locked, {
			iconOnly: compact,
			destructive: true
		})
	] }));
	y += stacked ? 92 : 46;
	if (dropping) {
		const h = width < 600 ? 198 : 166;
		nodes.push(node("Box", "rawConfirmation", rect(0, y, width, h), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			children: [
				label("rawDropWarning", rect(12, 8, width - 24, width < 600 ? 66 : 34), tr("Permanently delete this table and all its rows? Type its full name to confirm."), { wrap: true }),
				label("rawDropTableName", rect(12, h - 120, width - 24, 24), model.metadata.label || "", { weight: 600 }),
				node("Field", "rawDropName", rect(12, h - 90, width - 24, 38), {
					text: ui.dropName,
					label: tr("Confirm table name"),
					enabled: !model.busy,
					action: { type: "dropName" }
				}),
				button("rawKeepEditing", rect(12, h - 44, Math.min(150, (width - 32) / 2), 36), tr("Keep editing"), "", { type: "keep" }, !model.busy),
				button("rawConfirmChanges", rect(Math.min(150, (width - 32) / 2) + 20, h - 44, Math.min(170, (width - 32) / 2), 36), tr("DROP TABLE"), "", { type: "confirm" }, allow.drop && ui.dropName === model.metadata.label && ui.dropIdentity === model.identity, { destructive: true })
			]
		}));
		y += h + 8;
	}
	const gridHeight = Math.max(1, height - y - 46);
	const rowHeight = (model.controlHeight || 38) + 1;
	if (model.ready) nodes.push(node("Grid", "rawTableViewport", rect(0, y, width, gridHeight), {
		source: "rows",
		labelWidth: 84,
		headerHeight: 40,
		cellWidth: 230,
		rowHeight,
		caption: tr("Row"),
		rowHeaders: model.rows.map((record, index) => ({ children: [label("rawRowNumber_" + index, rect(6, 0, 32, rowHeight - 1), String((model.metadata.offset || 0) + index + 1), {
			strike: record.deleted,
			opacity: record.deleted ? .55 : 1
		}), button("rawDeleteRow_" + index, rect(40, 0, rowHeight - 1, rowHeight - 1), tr(record.deleted ? "Restore row" : "Delete row"), record.deleted ? "undo" : "delete", {
			type: "deleteRow",
			row: index
		}, allow.editable && !locked, {
			iconOnly: true,
			destructive: !record.deleted,
			opacity: record.deleted ? .55 : 1
		})] })),
		columnHeaders: model.columns.map((column) => ({
			label: column.name,
			detail: column.type + (column.readonly ? " · " + tr("Read-only") : "")
		})),
		verticalBarId: "rawTableVerticalBar",
		horizontalBarId: "rawTableHorizontalBar",
		columnHeadersId: "rawTableHeadings",
		rowHeadersId: "rawTableRowHeaders"
	}));
	if (!model.rows.length && !model.busy) nodes.push(label("rawTableEmpty", rect(12, y + (model.ready ? 48 : 12), width - 24, 38), tr("No rows"), muted));
	const footer = height - 38, size = width < 600 ? 38 : 140;
	nodes.push(button("rawPreviousPage", rect(0, footer, size, 38), tr("Previous"), "chevron-left", { type: "previous" }, allow.previous && !locked, { iconOnly: width < 600 }), label("rawPageRange", rect(size + 8, footer, width - 2 * size - 16, 38), (model.metadata.total ? (model.metadata.offset || 0) + 1 : 0) + "–" + Math.min((model.metadata.offset || 0) + 50, model.metadata.total || 0) + " / " + (model.metadata.total || 0), { align: "center" }), button("rawNextPage", rect(width - size, footer, size, 38), tr("Next"), "chevron-right", { type: "next" }, allow.next && !locked, { iconOnly: width < 600 }));
	return {
		nodes,
		minimumHeight: y + 206
	};
}
function cell(grid, record, row, column, model, ui, language) {
	if (!model.columns[column]) return { nodes: [] };
	const name = model.columns[column].name, keys = {}, action = {
		type: "cell",
		row,
		name
	};
	[
		[
			"ArrowLeft",
			-1,
			0
		],
		[
			"ArrowRight",
			1,
			0
		],
		[
			"ArrowUp",
			0,
			-1
		],
		[
			"ArrowDown",
			0,
			1
		]
	].forEach(([key, dx, dy]) => {
		keys[key] = {
			type: "navigateCell",
			row,
			column,
			dx,
			dy
		};
	});
	keys.F2 = keys.Enter = action;
	return { nodes: [node("Box", "rawCellBorder_" + row + "_" + name, rect(0, 0, grid.cellWidth, grid.rowHeight), {
		border: "outline",
		radius: 0,
		opacity: record.deleted ? .55 : 1
	}), node("Field", "rawCell_" + row + "_" + name, rect(0, 0, grid.cellWidth - 1, grid.rowHeight - 1), {
		text: cellText$1(record, name),
		label: name + " · " + (row + 1),
		enabled: !model.busy && !record.deleted && !ui.confirmation,
		activateAction: action,
		keys,
		tableCell: true,
		readOnly: true,
		strike: record.deleted,
		opacity: record.deleted ? .55 : 1
	})] };
}
function cellDescribe(model, ui, width, height, language) {
	if (!model.name) return { nodes: [] };
	const tr = (text) => translate(text, language), pad = 14, inner = Math.max(1, width - 28), footer = height - 52, errorHeight = model.error ? 48 : 0, helpY = footer - 44;
	const nodes = [
		label("rawCellDescription", rect(pad, 14, inner, 34), (model.name || "") + " · " + (model.type || "") + " · " + tr("Row") + " " + (model.rowNumber || ""), { wrap: true }),
		node("Choice", "rawCellMode", rect(pad, 60, inner, 38), {
			value: ui.mode,
			label: tr("Value mode"),
			enabled: !model.readonly && !model.busy,
			options: [["value", "Value"], ["null", "NULL"]].concat(model.newRow ? [["default", "Database default"]] : []).map(([value, text]) => ({
				value,
				label: tr(text)
			})),
			action: { type: "mode" }
		}),
		node("Area", "rawCellValue", rect(pad, 110, inner, Math.max(1, helpY - errorHeight - 122)), {
			text: ui.text,
			label: tr("Cell value"),
			enabled: ui.mode === "value" && !model.busy,
			readOnly: !!model.readonly,
			action: { type: "text" }
		}),
		label("rawCellApplyHelp", rect(pad, helpY, inner, 32), tr("Apply to draft, then save the table."), Object.assign({ wrap: true }, muted)),
		button("rawCellCancel", rect(width - pad - (model.readonly ? 96 : 216), footer, 96, 38), tr(model.readonly ? "Close" : "Cancel"), "", { type: "cancel" }, true)
	];
	if (model.error) nodes.push(label("rawCellError", rect(pad, helpY - 48, inner, 40), tr(model.error), {
		color: "error",
		wrap: true,
		role: "alert"
	}));
	if (!model.readonly) nodes.push(button("rawCellApply", rect(width - pad - 112, footer, 112, 38), tr("Apply"), "", { type: "apply" }, !model.busy, { highlighted: true }));
	return { nodes };
}
//#endregion
//#region src/features/administration/rawCellValues.js
function cellText(value) {
	return value == null ? "" : typeof value === "string" ? value : JSON.stringify(value);
}
function cellKind(type) {
	type = (type || "").trim().toLowerCase();
	if (/\b(tinyint|smallint|bigint|int(?:eger|[248])?|serial|bigserial|smallserial)\b/.test(type)) return "integer";
	if (/^bool/.test(type)) return "boolean";
	if (/^(numeric|decimal)/.test(type)) return "decimal";
	if (/^(real|float|double)/.test(type)) return "float";
	if (/^jsonb?\b/.test(type)) return "json";
	return "text";
}
function cellValue(text, type, mode = "value") {
	if (mode === "null") return null;
	if (mode !== "value") throw new Error("Invalid cell mode");
	const kind = cellKind(type), trimmed = text.trim();
	if (kind === "text") return text;
	if (kind === "integer") {
		if (!/^[+-]?\d+$/.test(trimmed)) throw new Error("Invalid integer");
		const value = BigInt(trimmed), number = Number(value);
		return Number.isSafeInteger(number) ? number : value.toString();
	}
	if (kind === "boolean") {
		if (["true", "1"].includes(trimmed.toLowerCase())) return true;
		if (["false", "0"].includes(trimmed.toLowerCase())) return false;
		throw new Error("Invalid boolean");
	}
	if (kind === "json") {
		JSON.parse(text, (_key, value) => {
			if (typeof value === "number" && !Number.isFinite(value)) throw new Error("Invalid JSON number");
			return value;
		});
		return text;
	}
	if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) throw new Error("Invalid number");
	if (kind === "decimal") return trimmed;
	const value = Number(trimmed);
	if (!Number.isFinite(value)) throw new Error("Invalid number");
	return value;
}
//#endregion
//#region src/features/administration/RawCellEditor.vue
var _hoisted_1$1 = ["aria-label"];
var _hoisted_2$1 = { class: "app-dialog-titlebar" };
//#endregion
//#region src/features/administration/RawDatabase.vue
var _sfc_main = {
	components: {
		FrameView: _sfc_main$3,
		RawCellEditor: {
			__name: "RawCellEditor",
			props: { busy: Boolean },
			emits: ["applied"],
			setup(__props, { expose: __expose, emit: __emit }) {
				const props = __props, emit = __emit;
				const dialog = ref(null), frame = ref(null), body = ref(null), cell = ref(null), ui = ref(cellInitial({})), error = ref(""), viewport = ref({
					width: 640,
					height: 440
				});
				let sequence = 0, observer = null;
				const model = computed(() => ({
					...cell.value,
					busy: props.busy,
					error: error.value
				}));
				const scene = computed(() => cellDescribe(model.value, ui.value, viewport.value.width, viewport.value.height, appearance.language));
				function close() {
					if (dialog.value?.open) dialog.value.close();
					cell.value = null;
					ui.value = cellInitial({});
				}
				async function open(scope) {
					cell.value = {
						...scope,
						session: ++sequence
					};
					ui.value = cellInitial(cell.value);
					error.value = "";
					await nextTick();
					dialog.value.showModal();
					viewport.value = {
						width: body.value.clientWidth,
						height: body.value.clientHeight
					};
					await nextTick();
					frame.value.focusControl("rawCellValue");
				}
				function dispatch(event) {
					const result = cellTransition(ui.value, model.value, event);
					ui.value = result.ui;
					for (const command of result.commands) {
						if (command.type === "cancel") {
							close();
							continue;
						}
						if (command.type !== "apply") throw Error("Unsupported Cell editor command: " + command.type);
						try {
							if (command.mode !== "default") cellValue(command.text, cell.value.type, command.mode);
							else if (!cell.value.newRow) throw Error("Default requires a new row");
							emit("applied", {
								...cell.value,
								mode: command.mode,
								text: command.mode === "value" ? command.text : ""
							});
							close();
						} catch {
							error.value = "Enter a valid value for the column type.";
						}
					}
				}
				onMounted(() => {
					observer = observeFrameSizes((entries) => {
						for (const entry of entries) if (entry.contentRect.width && entry.contentRect.height) viewport.value = {
							width: entry.contentRect.width,
							height: entry.contentRect.height
						};
					});
					observer.observe(body.value);
				});
				onBeforeUnmount(() => {
					observer?.disconnect();
					close();
				});
				__expose({
					open,
					close,
					ui,
					scene,
					model
				});
				return (_ctx, _cache) => {
					const _directive_window = resolveDirective("window");
					return withDirectives((openBlock(), createElementBlock("dialog", {
						ref_key: "dialog",
						ref: dialog,
						class: "record-dialog raw-cell-editor frame-dialog",
						"aria-label": unref(t)("Cell editor"),
						onCancel: _cache[1] || (_cache[1] = withModifiers(($event) => dispatch({ type: "cancel" }), ["prevent"])),
						onKeydown: _cache[2] || (_cache[2] = withKeys(withModifiers(($event) => dispatch({ type: "apply" }), ["ctrl", "prevent"]), ["enter"]))
					}, [createBaseVNode("header", _hoisted_2$1, [createBaseVNode("h2", null, toDisplayString(unref(t)("Cell editor")), 1), createVNode(_sfc_main$2, {
						label: "Close",
						icon: "close",
						"icon-only": "",
						onClick: _cache[0] || (_cache[0] = ($event) => dispatch({ type: "cancel" }))
					})]), createBaseVNode("div", {
						ref_key: "body",
						ref: body,
						class: "frame-host-body"
					}, [createVNode(_sfc_main$3, {
						ref_key: "frame",
						ref: frame,
						scene: scene.value,
						onEvent: dispatch
					}, null, 8, ["scene"])], 512)], 40, _hoisted_1$1)), [[_directive_window, { kind: "raw_cell" }]]);
				};
			}
		}
	},
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved"],
	data() {
		return {
			catalog: [],
			identity: "",
			metadata: {},
			revision: "",
			rows: [],
			baseline: "",
			busy: false,
			uncertain: false,
			canWrite: false,
			error: "",
			request: 0,
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			controlSize: 36,
			observer: null
		};
	},
	computed: {
		dirty() {
			return this.uncertain || JSON.stringify(this.rows) !== this.baseline && this.baseline !== "";
		},
		columns() {
			return this.metadata.columns || [];
		},
		editable() {
			return !!this.identity && this.canWrite && !this.busy && !this.uncertain;
		},
		skin() {
			return appearance.theme;
		},
		frameModel() {
			return {
				ready: !!this.identity && this.baseline !== "",
				identity: this.identity,
				catalog: this.catalog,
				metadata: this.metadata,
				rows: this.rows,
				columns: this.columns,
				canWrite: this.canWrite,
				canLoad: !!this.ticket,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				controlHeight: this.controlSize
			};
		},
		models() {
			return { rows: this.rows.map((row) => this.columns.map(() => row)) };
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		}
	},
	mounted() {
		this.load("list");
		this.measure();
		window.addEventListener("beforeunload", this.beforeUnload);
		this.observer = observeFrameSizes((entries) => {
			for (const entry of entries) if (entry.target === this.$refs.body) this.viewport = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			};
			else this.toolbarSize = entry.contentRect.width;
		});
		this.observer.observe(this.$refs.body);
		this.observer.observe(this.toolbarTarget ? document.querySelector(this.toolbarTarget) || this.$el : this.$el);
	},
	beforeUnmount() {
		this.request++;
		this.observer?.disconnect();
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		project() {
			this.reset();
		},
		ticket() {
			this.reset();
		},
		skin() {
			this.$nextTick(this.measure);
		}
	},
	methods: {
		t,
		measure() {
			this.controlSize = parseFloat(getComputedStyle(this.$el).getPropertyValue("--control-height")) || 36;
		},
		cellScene(node, record, row, column) {
			return cell(node, record, row, column, this.frameModel, this.ui, appearance.language);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
				case "select":
					this.select(command.identity);
					break;
				case "add":
					this.add();
					break;
				case "deleteRow":
					this.rows[command.row].deleted = !this.rows[command.row].deleted;
					break;
				case "cell":
					this.openCell(command.row, this.columns.find((column) => column.name === command.name));
					break;
				case "page":
					this.page(command.offset);
					break;
				case "drop":
					this.drop(command.name);
					break;
				case "export":
					await this.load("export");
					break;
				case "save":
					await this.save();
					break;
				case "reload":
					await this.load("list");
					break;
				case "discard":
					this.discard();
					break;
				case "focusGrid":
					await this.$nextTick();
					await this.$refs.frame.focusGrid(command.grid, command.row, command.column, command.id);
					break;
				default: throw Error("Unsupported Raw database command: " + command.type);
			}
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.dirty || this.busy || this.uncertain) {
				this.error = "Save or discard raw table changes before leaving.";
				return false;
			}
			return true;
		},
		reset() {
			this.$refs.cellEditor?.close();
			this.request++;
			this.busy = false;
			this.identity = "";
			this.rows = [];
			this.baseline = "";
			this.metadata = {};
			this.uncertain = false;
			this.ui = initial();
			this.load("list");
		},
		async load(action = "load", extra = {}) {
			if (this.busy) return;
			const request = ++this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await rawDatabase(action, this.ticket, this.project, {
					identity: this.identity,
					expected_revision: this.revision,
					...extra
				});
				if (request !== this.request) return;
				if (result.catalog) this.catalog = result.catalog;
				if (result.canWrite !== void 0) this.canWrite = !!result.canWrite;
				if (action === "list") {
					this.busy = false;
					if (this.catalog.length) {
						this.identity = this.catalog.find((row) => row.identity === this.identity)?.identity || this.catalog[0].identity;
						return this.load();
					}
					this.identity = "";
					this.metadata = {};
					this.rows = [];
					this.baseline = "";
					this.uncertain = false;
				} else if (action === "export") {
					const url = URL.createObjectURL(new Blob(["﻿", result.metadata.csv], { type: "text/csv;charset=utf-8" }));
					const link = document.createElement("a");
					link.href = url;
					link.download = this.metadata.label.replaceAll(" / ", "_") + ".csv";
					link.click();
					setTimeout(() => URL.revokeObjectURL(url), 1e3);
				} else {
					this.identity = result.identity;
					this.metadata = result.metadata;
					this.revision = result.revision;
					this.rows = (result.document.rows || []).map((row) => ({
						...row,
						deleted: false,
						texts: Object.fromEntries(Object.entries(row.values).map(([name, value]) => [name, cellText(value)])),
						modes: Object.fromEntries(Object.entries(row.values).map(([name, value]) => [name, value === null ? "null" : "value"]))
					}));
					this.baseline = JSON.stringify(this.rows);
					this.uncertain = false;
					if (["save", "drop"].includes(action)) this.$emit("saved");
				}
			} catch (error) {
				if (request === this.request) {
					this.error = error.message;
					if (["save", "drop"].includes(action)) this.uncertain = true;
				}
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		select(identity) {
			if (!this.dirty && !this.busy && !this.uncertain) {
				this.identity = identity;
				this.load();
			}
		},
		page(offset) {
			if (this.canLeave()) this.load("load", { item_offset: offset });
		},
		add() {
			if (this.editable) this.rows.push({
				key: null,
				texts: {},
				modes: {},
				deleted: false
			});
		},
		cellMode(row, name) {
			return row.modes[name] || (row.key === null ? "default" : "value");
		},
		cellDisplay(row, name) {
			const mode = this.cellMode(row, name);
			return mode === "null" ? "NULL" : mode === "default" ? "DEFAULT" : row.texts[name] || "";
		},
		openCell(index, column) {
			const row = this.rows[index];
			if (this.busy || row.deleted) return;
			this.$refs.cellEditor.open({
				index,
				name: column.name,
				type: column.type,
				text: row.texts[column.name] || "",
				mode: this.cellMode(row, column.name),
				newRow: row.key === null,
				rowNumber: this.metadata.offset + index + 1,
				identity: this.identity,
				generation: this.request,
				readonly: !!(!this.editable || column.readonly || row.readonly?.includes(column.name))
			});
		},
		applyCell(cell) {
			if (!this.editable || cell.identity !== this.identity || cell.generation !== this.request || !this.rows[cell.index] || this.rows[cell.index].deleted) return;
			this.rows[cell.index].texts[cell.name] = cell.text;
			this.rows[cell.index].modes[cell.name] = cell.mode;
		},
		async save() {
			if (!this.editable || !this.dirty) return;
			try {
				const baseline = JSON.parse(this.baseline);
				const rows = this.rows.map((row, index) => {
					const values = Object.fromEntries(this.columns.filter((column) => !column.readonly && !row.readonly?.includes(column.name) && this.cellMode(row, column.name) !== "default" && (row.key === null || row.deleted || row.texts[column.name] !== baseline[index]?.texts[column.name] || row.modes[column.name] !== baseline[index]?.modes[column.name])).map((column) => [column.name, row.deleted ? null : cellValue(row.texts[column.name] || "", column.type, this.cellMode(row, column.name))]));
					if (row.key !== null && !row.deleted && !Object.keys(values).length) return null;
					return {
						key: row.key,
						revision: row.revision,
						deleted: row.deleted,
						values
					};
				}).filter((row) => row !== null);
				await this.load("save", { document: {
					rows,
					offset: this.metadata.offset
				} });
			} catch {
				this.error = "Enter a valid value for the column type.";
			}
		},
		discard() {
			this.ui.confirmation = "";
			this.error = "";
			if (this.uncertain) this.load("list");
			else this.rows = JSON.parse(this.baseline);
		},
		drop(name = this.ui.dropName) {
			if (this.editable && !this.dirty && name === this.metadata.label) {
				this.ui.confirmation = "";
				this.load("drop", { confirmation: name });
			}
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	const _component_RawCellEditor = resolveComponent("RawCellEditor");
	return openBlock(), createElementBlock("section", {
		class: "raw-database frame-host",
		"aria-label": $options.t("Raw database"),
		"aria-busy": $data.busy
	}, [
		(openBlock(), createBlock(Teleport, {
			defer: "",
			to: $props.toolbarTarget || "body",
			disabled: !$props.toolbarTarget
		}, [withDirectives(createBaseVNode("div", {
			class: "frame-toolbar-host",
			style: normalizeStyle({ width: $data.toolbarSize + "px" })
		}, [createVNode(_component_FrameView, {
			scene: $options.toolbarScene,
			onEvent: $options.dispatch
		}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])),
		createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
			ref: "frame",
			scene: $options.frameScene,
			models: $options.models,
			"describe-cell": $options.cellScene,
			onEvent: $options.dispatch
		}, null, 8, [
			"scene",
			"models",
			"describe-cell",
			"onEvent"
		])], 512),
		createVNode(_component_RawCellEditor, {
			ref: "cellEditor",
			busy: $data.busy,
			onApplied: $options.applyCell
		}, null, 8, ["busy", "onApplied"])
	], 8, _hoisted_1);
}
var RawDatabase_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { RawDatabase_default as default };

//# sourceMappingURL=RawDatabase.js.map
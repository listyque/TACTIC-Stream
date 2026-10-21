import { C as h, D as nextTick, G as watchPostEffect, N as openBlock, P as renderList, U as watch, Z as ref, _ as createElementBlock, b as createVNode, g as createCommentVNode, h as createBlock, it as toDisplayString, j as onMounted, k as onBeforeUnmount, m as createBaseVNode, p as computed, rt as normalizeStyle, tt as unref, u as Fragment, w as inject, y as createTextVNode } from "./vue.js";
import { A as appearance, K as metrics, c as _sfc_main$4, k as t } from "./index.js";
import { Gt as muted, Kt as node, Ut as button, Wt as label, i as _sfc_main$5, ot as resultItems, qt as rect, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { f as linkifyPlainText, l as activateRichLink, n as browserLink, u as escapeHtml } from "./links.js";
import { d as timestampFullLabel, f as timestampLabel, i as compactText, l as needsExpansion, n as qtLabelTextWidth, r as changeValue, s as eventSentence, u as safeColor } from "./textMetrics.js";
import { t as _sfc_main$6 } from "./AttachmentCard.js";
import { t as FilePreview_default } from "./FilePreview.js";
import { t as fileBlob } from "./previewFiles.js";
//#region ../src/tactic_stream/shared_ui/features/objects/report.ui.mjs
var sections = [
	{
		value: "tasks",
		label: "Tasks",
		icon: "task"
	},
	{
		value: "notes",
		label: "Notes",
		icon: "notes"
	},
	{
		value: "children",
		label: "Children",
		icon: "account-tree"
	},
	{
		value: "snapshots",
		label: "Snapshots",
		icon: "snapshot"
	},
	{
		value: "activity",
		label: "Activity",
		icon: "activity-feed"
	}
];
function metric(id, title, value, bounds, color, language) {
	return node("Box", id, bounds, {
		background: "transparent",
		children: [label(id + "Value", rect(0, 0, bounds.width, 28), String(value ?? 0), {
			fontRole: "statistic",
			weight: 600,
			color: color || "primaryText"
		}), label(id + "Label", rect(0, 29, bounds.width, 15), translate(title, language), {
			fontRole: "caption",
			weight: 600,
			color: "secondaryText"
		})]
	});
}
function header(model, width, language, measure = (text, size) => String(text).length * size * .55) {
	const tr = (text) => translate(text, language), summary = model.summary || {}, metrics = model.metrics || {};
	const preview = width >= 700 ? 142 : width >= 420 ? 116 : 82;
	const left = 14 + preview + (width >= 560 ? 18 : 10), textWidth = Math.max(0, width - left - 14);
	const columns = width >= 1040 ? 4 : width >= 560 ? 2 : 1;
	const fields = [
		[
			"Code",
			summary.code,
			"code"
		],
		[
			"Search Type",
			summary.searchType,
			"sobject"
		],
		[
			"Project",
			summary.project,
			"project-diagram"
		],
		[
			"Pipeline",
			summary.pipeline,
			"workflow"
		]
	].filter((row) => row[1]);
	function gridWidths(rows, count, available, gap, preferred) {
		const hints = Array.from({ length: count }, (_, column) => Math.max(1, ...rows.filter((_, index) => index % count === column).map(preferred)));
		const total = hints.reduce((sum, hint) => sum + hint, 0), room = Math.max(0, available - gap * (count - 1));
		return hints.map((hint) => room * hint / total);
	}
	const fieldWidths = gridWidths(fields, columns, textWidth, 14, ([title, value]) => 24 + Math.max(Math.ceil(measure(tr(title), 11)), Math.ceil(measure(String(value), 13))));
	const description = summary.description || tr("No description provided");
	const descriptionHeight = Math.min(42, Math.max(1, Math.ceil(measure(description, 13) / Math.max(1, textWidth))) * 17);
	const infoY = 80 + descriptionHeight, infoHeight = fields.length ? Math.ceil(fields.length / columns) * 38 - 5 : 0;
	const topHeight = Math.max(preview, infoY - 14 + infoHeight + 40);
	const metricColumns = width >= 1040 ? 8 : width >= 560 ? 4 : width >= 340 ? 2 : 1;
	const values = [
		["TASKS", metrics.tasks || 0],
		["NOTES", metrics.notes || 0],
		["CHILDREN", metrics.children || 0],
		["PEOPLE", metrics.participants || 0],
		["WORK HOURS", Number(metrics.workHours || 0).toFixed(1) + " " + tr("h")],
		["FILES", metrics.files || 0],
		["SNAPSHOTS", metrics.snapshots || 0],
		[metrics.canViewCosts ? "TOTAL COST" : "TOTAL SIZE", metrics.canViewCosts ? Number(metrics.totalCost || 0).toFixed(2) : metrics.totalSize || "0 B"]
	];
	const metricRows = Math.ceil(8 / metricColumns), metricHeight = width >= 1040 ? 50 : width >= 560 ? 86 : metricRows * 44 + (metricRows - 1) * 5;
	const height = Math.max(256, 28 + topHeight + 21 + metricHeight), extra = height - (28 + topHeight + 21 + metricHeight);
	const nodes = [
		node("Box", "objectReportHeaderSurface", rect(0, 0, width, height), {
			background: "surfaceContainerHigh",
			border: "outlineVariant"
		}),
		node("Preview", "objectReportPreview", rect(14, 14 + (topHeight - preview) / 2, preview, preview), {
			source: summary.previewUrl || "",
			initials: String(summary.title || "?").slice(0, 2).toUpperCase(),
			icon: "sobject",
			accent: summary.accent || "action",
			outlined: true,
			radius: 12,
			round: false
		}),
		label("objectReportTitle", rect(left, 14, textWidth, 24), summary.title || tr("No sObject selected"), {
			fontRole: "display",
			weight: 600
		}),
		node("StatusChip", "objectReportType", rect(left, 44, Math.min(textWidth, Math.ceil(measure(summary.typeTitle || "", 11, 600)) + 34), 24), {
			text: summary.typeTitle || "",
			icon: "sobject",
			accent: summary.accent || "action"
		}),
		node("View", "objectReportDescription", rect(left, 74, textWidth, descriptionHeight), {
			view: "reportDescription",
			text: description,
			empty: !summary.description
		})
	];
	fields.forEach(([title, value, icon], index) => {
		const column = index % columns, x = left + fieldWidths.slice(0, column).reduce((sum, value) => sum + value + 14, 0), y = infoY + Math.floor(index / columns) * 38, cell = fieldWidths[column];
		nodes.push(node("Icon", "objectReportFieldIcon_" + index, rect(x, y + 9, 15, 15), {
			icon,
			color: "secondaryText",
			iconSize: 15
		}));
		nodes.push(label("objectReportFieldLabel_" + index, rect(x + 24, y, cell - 24, 15), tr(title), Object.assign({}, muted, { fontRole: "caption" })));
		nodes.push(label("objectReportFieldValue_" + index, rect(x + 24, y + 15, cell - 24, 18), String(value), {
			fontRole: "body",
			elide: "middle"
		}));
	});
	nodes.push(label("objectReportUpdated", rect(left, 14 + topHeight - 28, textWidth - 66, 28), summary.updatedPretty ? tr("Updated") + ": " + summary.updatedPretty : "", Object.assign({}, muted, {
		fontRole: "caption",
		tooltip: summary.updatedFull || ""
	})));
	[[
		"open",
		"Open sObject",
		"open-in-new"
	], [
		"refresh",
		"Refresh report",
		"refresh"
	]].forEach(([type, text, icon], index) => nodes.push(button("objectReport_" + type, rect(width - 74 + index * 33, topHeight - 14, 28, 28), tr(text), icon, { type }, !!summary.searchKey && (type !== "refresh" || !model.busy), {
		iconOnly: true,
		iconAction: true,
		iconSize: 16
	})));
	nodes.push(node("Box", "objectReportHeaderDivider", rect(14, 24 + topHeight, width - 28, 1), {
		background: "separator",
		radius: 0
	}));
	const widths = gridWidths(values, metricColumns, width - 28, 12, ([title, value]) => Math.max(Math.ceil(measure(tr(title), 11, 600) + tr(title).length * .25), Math.ceil(measure(String(value), 21, 600))));
	values.forEach(([title, value], index) => {
		const column = index % metricColumns;
		nodes.push(metric("objectReportMetric_" + index, title, value, rect(14 + widths.slice(0, column).reduce((sum, value) => sum + value + 12, 0), 35 + topHeight + extra + Math.floor(index / metricColumns) * 49, widths[column], 44), "", language));
	});
	return {
		nodes,
		height
	};
}
function tabs(page, width, language) {
	const gap = 2, cell = Math.max(0, (width - 8) / 5), narrow = width < 420;
	return {
		height: 36,
		nodes: sections.map((section, index) => button("objectReportTab_" + section.value, rect(index * (cell + gap), 0, cell, 36), translate(section.label, language), section.icon, {
			type: "page",
			value: section.value
		}, true, {
			radio: true,
			selected: page === section.value,
			iconOnly: narrow,
			iconSize: 16
		}))
	};
}
function status(id, text, x, y, maximum, accent, icon) {
	const width = Math.min(Math.max(0, maximum), String(text || "").length * 6 + 30);
	return node("StatusChip", id, rect(x, y, width, 24), {
		text,
		icon,
		accent: accent || "secondaryText",
		fontRole: "caption",
		weight: 600
	});
}
function row(kind, record, width, index, language) {
	const tr = (text) => translate(text, language), children = [];
	const accent = record.processColor || record.authorColor || record.accent || "action";
	let height = kind === "person" ? 76 : kind === "child" ? 68 : 72;
	let title = record.title || "", subtitle = record.subtitle || "";
	function text(id, x, y, w, h, value, options) {
		children.push(label(id, rect(x, y, w, h), value || "", options));
	}
	function preview(size, x, y, source, initials, round) {
		children.push(node("Preview", "objectReportRowPreview", rect(x, y, size, size), {
			source: source || "",
			initials: initials || "",
			icon: kind === "child" ? "sobject" : "person",
			accent: kind === "person" ? record.avatarColor || accent : accent,
			round,
			radius: round ? size / 2 : 12,
			outlined: round
		}));
	}
	if (kind === "person") {
		title = record.displayName;
		preview(42, 10, 17, record.avatarUrl, record.initials, true);
		text("objectReportRowTitle", 61, 17, width - 161, 22, title, { weight: 600 });
		subtitle = translate("{tasks} tasks · {notes} notes · {snapshots} snapshots", language, {
			tasks: record.taskCount,
			notes: record.noteCount,
			snapshots: record.snapshotCount
		});
		text("objectReportRowSubtitle", 61, 42, width - 161, 17, subtitle, {
			fontRole: "caption",
			color: "secondaryText"
		});
		text("objectReportRowHours", width - 92, 27, 62, 22, Number(record.hours || 0).toFixed(1) + " " + tr("h"), {
			align: "right",
			color: record.hours > 0 ? record.accent || "action" : "secondaryText",
			weight: 600
		});
		if (record.cost > 0) text("objectReportRowCost", width - 130, 42, 100, 17, tr("Cost") + " " + Number(record.cost).toFixed(2), {
			fontRole: "caption",
			align: "right",
			color: "secondaryText"
		});
	} else if (kind === "task") {
		title = record.processLabel;
		children.push(node("Box", "objectReportTaskIconSurface", rect(12, 17, 38, 38), {
			background: "panelRaised",
			radius: 12,
			children: [node("Icon", "taskProcessIcon", rect(11, 11, 16, 16), {
				icon: "workflow",
				color: accent
			})]
		}));
		let right = width - 30;
		if (width >= 760) {
			text("taskNotes", right - 20, 26, 20, 18, String(record.notesCount || 0), {
				fontRole: "caption",
				color: "secondaryText"
			});
			right -= 30;
			children.push(node("Icon", "taskNotesIcon", rect(right - 14, 29, 14, 14), {
				icon: "notes",
				color: "secondaryText"
			}));
			right -= 24;
			text("taskProgress", right - 38, 26, 38, 18, (record.progress || 0) + "%", {
				fontRole: "secondary",
				weight: 600
			});
			right -= 48;
			if (record.endPretty) {
				const extent = Math.min(110, String(record.endPretty).length * 6 + 4);
				text("taskDeadline", right - extent, 26, extent, 18, record.endPretty, {
					fontRole: "caption",
					color: record.dueState === "overdue" ? "error" : "secondaryText",
					tooltip: record.endFull || ""
				});
				right -= extent + 10;
			}
			text("taskHours", right - 84, 26, 84, 18, Number(record.loggedHours || 0).toFixed(1) + " / " + Number(record.plannedHours || 0).toFixed(1) + " " + tr("h"), {
				fontRole: "caption",
				color: "secondaryText"
			});
			right -= 94;
			const assignedWidth = 140;
			children.push(node("Preview", "taskAssigneeAvatar", rect(right - assignedWidth, 23, 26, 26), {
				source: record.assignedAvatar || "",
				initials: String(record.assignedLabel || "").slice(0, 2).toUpperCase(),
				icon: "person",
				accent: record.assignedColor || "action",
				round: true,
				outlined: false
			}));
			text("taskAssignee", right - assignedWidth + 32, 26, 108, 18, record.assignedLabel, {
				fontRole: "caption",
				color: "secondaryText"
			});
			right -= 150;
			const chip = status("taskStatus", record.status || "", Math.max(60, right - 110), 13, 110, record.statusColor, "system-activity");
			children.push(chip);
			text("objectReportRowTitle", 60, 13, Math.max(0, right - 60 - chip.width - 8), 22, title, {
				fontRole: "bodyLarge",
				weight: 600
			});
			text("objectReportRowSubtitle", 60, 39, right - 60, 18, record.description || record.assignedLabel, {
				fontRole: "caption",
				color: "secondaryText"
			});
		} else {
			text("objectReportRowTitle", 60, 7, width - 90, 22, title, {
				fontRole: "bodyLarge",
				weight: 600
			});
			text("objectReportRowSubtitle", 60, 30, width - 90, 17, record.description || record.assignedLabel, {
				fontRole: "caption",
				color: "secondaryText"
			});
			const detail = [
				record.status,
				record.assignedLabel,
				Number(record.loggedHours || 0).toFixed(1) + " / " + Number(record.plannedHours || 0).toFixed(1) + " " + tr("h"),
				record.endPretty,
				(record.progress || 0) + "%"
			].filter(Boolean).join(" · ");
			text("objectReportRowMeta", 60, 50, width - 90, 17, detail, {
				fontRole: "caption",
				color: record.dueState === "overdue" ? "error" : "secondaryText"
			});
		}
	} else if (kind === "note") {
		title = record.authorLabel;
		const available = Math.max(1, width - 90);
		let lines = 0;
		for (const paragraph of String(record.body || "").split("\n")) lines += Math.max(1, Math.ceil(paragraph.length * 7 / available));
		height = Math.max(84, lines * 18 + 54);
		preview(34, 11, 11, record.avatarUrl, record.initials, true);
		const chip = status("noteContext", record.isTaskNote ? record.taskTitle || tr("Task note") : tr("Object note"), Math.max(55, width - 220), 10, 116, accent, record.isTaskNote ? "task" : "sobject");
		children.push(chip);
		text("noteTimestamp", width - 96, 13, 70, 18, record.timestampPretty, {
			fontRole: "caption",
			color: "secondaryText",
			tooltip: record.timestampFull || ""
		});
		text("objectReportRowTitle", 55, 10, Math.max(0, chip.x - 61), 22, title, { weight: 600 });
		text("objectReportRowSubtitle", 55, 40, width - 85, height - 54, record.body, { wrap: true });
	} else {
		preview(44, 9, 12, record.previewUrl, String(title).slice(0, 2).toUpperCase(), false);
		const wide = width >= 600, extent = wide ? 270 : 0;
		text("objectReportRowTitle", 63, 14, width - 93 - extent, 22, title, { weight: 600 });
		text("objectReportRowSubtitle", 63, 39, width - 93 - extent, 17, subtitle, {
			fontRole: "caption",
			color: "secondaryText"
		});
		if (wide) {
			children.push(status("childType", record.typeTitle, width - 285, 22, 100, accent, "sobject"));
			if (record.status) children.push(status("childStatus", record.status, width - 177, 22, 100, "secondaryText", "system-activity"));
			text("childRelationship", width - 70, 25, 40, 18, record.relationship, {
				fontRole: "caption",
				color: "secondaryText"
			});
		}
	}
	children.push(node("Icon", "objectReportRowArrow", rect(Math.max(0, width - 25), (height - 15) / 2, 15, 15), {
		icon: "arrow-forward",
		color: "secondaryText"
	}));
	if (kind !== "person" || record.hours > 0) children.push(node("Box", "objectReportRowRail", rect(0, 5, 3, height - 10), {
		background: accent,
		radius: 0
	}));
	return {
		height,
		nodes: [node("Action", "objectReportRow_" + kind + "_" + index, rect(0, 0, width, height), {
			text: title || subtitle || "",
			normalColor: "surfaceContainerHigh",
			radius: 0,
			action: {
				type: kind,
				index,
				key: record.searchKey || record.login || "",
				process: record.process || "",
				taskCode: record.taskCode || ""
			},
			children
		})]
	};
}
function page(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [], metrics = model.metrics || {};
	let y = 0;
	function panel(id, title, icon, children, height, x = 0, panelWidth = width, detail = "") {
		nodes.push(node("Box", id, rect(x, y, panelWidth, height), {
			background: "panel",
			border: "outlineVariant",
			children: [
				node("Icon", id + "Icon", rect(14, 14, 15, 15), {
					icon,
					color: "action"
				}),
				label(id + "Title", rect(37, 10, Math.max(0, panelWidth - 51 - (detail ? 144 : 0)), 24), tr(title), { weight: 600 }),
				...detail ? [label(id + "Detail", rect(Math.max(0, panelWidth - 155), 13, 141, 18), detail, {
					align: "right",
					fontRole: "caption",
					color: "secondaryText"
				})] : [],
				...children
			]
		}));
		y += height + 12;
	}
	function rows(id, title, icon, kind, records, empty) {
		const columns = kind === "person" ? width >= 940 ? 3 : width >= 600 ? 2 : 1 : 1;
		const gap = kind === "person" ? 8 : 6, padding = kind === "person" ? 14 : 12;
		const rowWidth = Math.max(0, (width - padding * 2 - gap * (columns - 1)) / columns);
		let top = kind === "person" ? 52 : 44;
		const children = [];
		let rowHeight = 0;
		records.forEach((record, index) => {
			const scene = row(kind, Object.assign({}, record, { accent: record.accent || model.summary?.accent || "action" }), rowWidth, index, language);
			if (index > 0 && index % columns === 0) {
				top += rowHeight + gap;
				rowHeight = 0;
			}
			children.push(node("Box", id + "Row_" + index, rect(padding + index % columns * (rowWidth + gap), top, rowWidth, scene.height), {
				background: "transparent",
				children: scene.nodes
			}));
			rowHeight = Math.max(rowHeight, scene.height);
		});
		if (!records.length) {
			children.push(node("Icon", id + "EmptyIcon", rect(width / 2 - 15, 99, 30, 30), {
				icon,
				color: "secondaryText"
			}));
			children.push(label(id + "Empty", rect(12, 137, Math.max(0, width - 24), 36), tr(empty), Object.assign({}, muted, {
				align: "center",
				wrap: true
			})));
		}
		panel(id, title, icon, children, Math.max(kind === "person" ? 150 : 0, records.length ? top + rowHeight + 14 : 198), 0, width, kind === "person" ? translate("{count} people · {hours} h", language, {
			count: metrics.participants || 0,
			hours: Number(metrics.workHours || 0).toFixed(1)
		}) : kind === "task" ? translate("{count} tasks", language, { count: metrics.tasks || 0 }) : kind === "child" ? translate("{count} children", language, { count: metrics.children || 0 }) : kind === "note" ? translate("{objects} object · {tasks} task notes", language, {
			objects: metrics.objectNotes || 0,
			tasks: metrics.taskNotes || 0
		}) : "");
	}
	function chips(id, title, icon, records, action, x = 0, panelWidth = width, detail = "") {
		let left = 14, top = 44;
		panel(id, title, icon, records.map((record, index) => {
			const chip = status(id + "Chip_" + index, (record.label || record.value || tr("Unspecified")) + "  " + (record.count || 0), 0, 0, Math.max(0, panelWidth - 28), record.accent || "action", icon);
			if (left > 14 && left + chip.width > panelWidth - 14) {
				left = 14;
				top += 31;
			}
			chip.x = left;
			chip.y = top;
			chip.action = action ? {
				type: "filter",
				field: action,
				value: record.value
			} : null;
			left += chip.width + 7;
			return chip;
		}), id === "objectChildTypes" ? records.length ? top + 24 + 12 : 52 : Math.max(150, top + 38), x, panelWidth, id === "objectChildTypes" ? translate("{count} relations", language, { count: metrics.childTypes || records.length }) : detail);
	}
	if (model.page === "tasks") {
		const values = [
			[
				"TOTAL",
				metrics.tasks,
				""
			],
			[
				"ACTIVE TASKS",
				metrics.activeTasks,
				""
			],
			[
				"COMPLETED",
				metrics.completedTasks,
				"green"
			],
			[
				"OVERDUE",
				metrics.overdueTasks,
				metrics.overdueTasks ? "error" : ""
			],
			[
				"UNASSIGNED",
				metrics.unassignedTasks,
				""
			],
			[
				"AVERAGE PROGRESS",
				(metrics.averageProgress || 0) + "%",
				""
			]
		];
		const wideMetrics = width >= 780, panelWidth = wideMetrics ? (width - 20) / 2 : width;
		const cell = Math.max(0, (panelWidth - 32 - 28) / 3);
		for (let group = 0; group < 2; group++) nodes.push(node("Box", "objectTaskMetrics_" + group, rect(wideMetrics ? group * (panelWidth + 20) : 0, y + (wideMetrics ? 0 : group * 122), panelWidth, 110), {
			background: "panel",
			children: [
				node("Box", "metricDivider_" + group + "_0", rect(16 + cell + 6, 34, 1, 42), { background: "separator" }),
				node("Box", "metricDivider_" + group + "_1", rect(16 + 2 * (cell + 14) - 8, 34, 1, 42), { background: "separator" }),
				...values.slice(group * 3, group * 3 + 3).map(([title, value, color], index) => metric("objectTaskMetric_" + (group * 3 + index), title, value, rect(16 + index * (cell + 14), 30, cell, 50), color, language))
			]
		}));
		y += (wideMetrics ? 110 : 232) + 12;
		const groupY = y, groupWidth = width >= 860 ? (width - 12) / 2 : width;
		chips("objectStatusGroups", "TASKS BY STATUS", "system-activity", model.task_statuses || [], "status", 0, groupWidth);
		const statusBottom = y;
		if (width >= 860) y = groupY;
		chips("objectProcessGroups", "TASKS BY PROCESS", "workflow", model.task_processes || [], "process", width >= 860 ? groupWidth + 12 : 0, groupWidth);
		y = Math.max(y, statusBottom);
		rows("objectParticipants", "PEOPLE AND WORK HOURS", "group", "person", (model.participants || []).map((record) => {
			const value = Object.assign({}, record);
			if (!metrics.canViewCosts) delete value.cost;
			return value;
		}), "No participants found");
		rows("objectTasks", "TASKS", "task", "task", model.tasks || [], "No tasks for this sObject");
	} else if (model.page === "notes") rows("objectNotes", "OBJECT AND TASK NOTES", "notes", "note", model.notes || [], "No object or task notes");
	else if (model.page === "children") {
		chips("objectChildTypes", "CHILD TYPES", "account-tree", model.child_types || []);
		rows("objectChildren", "CHILDREN", "account-tree", "child", model.children || [], "No related children");
	}
	return {
		nodes,
		height: Math.max(0, y - 12)
	};
}
//#endregion
//#region src/features/objects/ObjectReportSurface.vue
var _sfc_main$3 = {
	__name: "ObjectReportSurface",
	props: {
		model: Object,
		part: {
			type: String,
			default: "header"
		}
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(0);
		function measure(text, size, weight = 400) {
			return qtLabelTextWidth(text, `${weight} ${size}px Segoe UI`);
		}
		const descriptionView = {
			nodeProps: true,
			props: ["frameNode"],
			setup: (props) => () => h("div", {
				class: "report-description-value",
				style: { color: props.frameNode.empty ? "var(--muted)" : "var(--on-surface)" },
				innerHTML: linkifyPlainText(props.frameNode.text),
				onClick: (event) => activateRichLink(event, (link) => emit("event", {
					type: "link",
					value: link
				}))
			})
		};
		const scene = computed(() => props.part === "header" ? header(props.model, width.value, appearance.language, measure) : page(props.model, width.value, appearance.language));
		let observer;
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "object-report-surface",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				views: { reportDescription: {
					component: descriptionView,
					nodeProps: true
				} },
				onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
			}, null, 8, ["scene", "views"])], 4);
		};
	}
};
//#endregion
//#region src/controls/pagination.js
function usePagination(viewport, content, enabled, requestMore) {
	let armed = false, blocked = false, pointer = null, frame = 0, releaseFrame = 0, cleanup;
	function check() {
		const element = viewport.value;
		if (!element?.checkVisibility() || !element.clientHeight || blocked || !enabled()) return;
		const underfilled = element.scrollHeight <= element.clientHeight + 1;
		const atEnd = element.scrollTop + element.clientHeight >= element.scrollHeight - 2;
		if (!underfilled && (!atEnd || !armed)) return;
		armed = false;
		requestMore();
	}
	function schedule() {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(check);
	}
	function arm() {
		if (!blocked) armed = true;
	}
	function wheel(event) {
		if (event.deltaY > 0) {
			arm();
			check();
			schedule();
		}
	}
	function key(event) {
		if (event.target !== viewport.value || ![
			"ArrowDown",
			"PageDown",
			"End",
			" "
		].includes(event.key) || event.key === " " && event.shiftKey) return;
		arm();
		check();
		schedule();
	}
	function press(event) {
		const element = viewport.value, box = element.getBoundingClientRect();
		if (!(event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom)) return;
		const gutter = event.clientX >= box.left + element.clientLeft + element.clientWidth || event.clientX < box.left + element.clientLeft;
		armed = false;
		if (gutter) {
			blocked = true;
			pointer = event.pointerId;
			cancelAnimationFrame(releaseFrame);
		} else if (event.pointerType === "touch") arm();
	}
	function release(event) {
		if (event.pointerId !== pointer) return;
		pointer = null;
		releaseFrame = requestAnimationFrame(() => {
			releaseFrame = requestAnimationFrame(() => {
				blocked = false;
				check();
			});
		});
	}
	watch([viewport, content], ([element, body]) => {
		cleanup?.();
		armed = false;
		blocked = false;
		pointer = null;
		if (!element || !body) return;
		const observer = new ResizeObserver(check);
		observer.observe(element);
		observer.observe(body);
		element.addEventListener("scroll", check, { passive: true });
		element.addEventListener("wheel", wheel, { passive: true });
		element.addEventListener("keydown", key);
		document.addEventListener("pointerdown", press, true);
		document.addEventListener("pointerup", release, true);
		document.addEventListener("pointercancel", release, true);
		cleanup = () => {
			observer.disconnect();
			cancelAnimationFrame(frame);
			cancelAnimationFrame(releaseFrame);
			element.removeEventListener("scroll", check);
			element.removeEventListener("wheel", wheel);
			element.removeEventListener("keydown", key);
			document.removeEventListener("pointerdown", press, true);
			document.removeEventListener("pointerup", release, true);
			document.removeEventListener("pointercancel", release, true);
		};
	}, { flush: "post" });
	onBeforeUnmount(() => cleanup?.());
	return {
		check,
		reset: () => {
			armed = false;
		}
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/activity/event.ui.mjs
function icon(model) {
	return model.relationAction ? "link" : {
		publication: "snapshot",
		note: "notes",
		task: "task",
		work_hour: "schedule",
		status: "system-activity",
		create: "add",
		delete: "delete",
		change: "edit"
	}[model.kind] || "activity-feed";
}
function accent(model) {
	return model.processColor || model.typeColor || {
		publication: "green",
		work_hour: "cyan",
		task: "yellow"
	}[model.kind] || "action";
}
function geometry(width, style = "md3") {
	const avatar = width < 380 ? 34 : 40, gap = metrics(style).communicationAvatarSpacing;
	const bubble = Math.max(0, Math.min(760, width - avatar - gap - 8));
	return {
		avatar,
		bubble,
		x: 4 + avatar + gap,
		inner: Math.max(0, bubble - 20)
	};
}
function card(model, width, heights = {}, language, style = "md3") {
	const tr = (text) => translate(text, language), g = geometry(width, style), compact = g.bubble < 520, timeWidth = Math.min(140, g.inner * .35), headerHeight = compact ? 33 : 16, nodes = [], sentenceHeight = Math.max(18, heights.sentence || 18), color = accent(model);
	let y = 14 + headerHeight + 6;
	const content = [
		label("activityActorLabel", rect(10, 10, compact ? g.inner : Math.max(0, g.inner - timeWidth - 8), 16), model.serverGenerated ? tr("Server trigger") : model.actorLabel || model.actor || tr("Unknown user"), {
			fontRole: "secondary",
			weight: 600,
			color: "action"
		}),
		label("activityTimestamp", rect(compact ? 10 : g.bubble - 10 - timeWidth, compact ? 28 : 10, compact ? g.inner : timeWidth, 15), model.time || "", {
			fontRole: "caption",
			color: "secondaryText",
			align: compact ? "left" : "right",
			toolTip: model.fullTime || ""
		}),
		node("Icon", "activityKind", rect(10, y - 4, 20, 20), {
			icon: icon(model),
			color
		}),
		node("View", "activitySentencePort", rect(38, y - 4, Math.max(0, g.inner - 28), sentenceHeight), { view: "sentence" })
	];
	y += Math.max(20, sentenceHeight) + 6;
	const changes = model.changes || [], changeNodes = [], changeTop = y - 4;
	for (let i = 0; i < changes.length; i++) {
		const rowHeight = Math.max(16, heights["change_" + i] || 16) + 10, labelWidth = Math.min(116, Math.max(60, g.inner * .25)), rowY = y - 4 - changeTop;
		changeNodes.push(node("Box", "activityChangeRow_" + i, rect(0, rowY, g.inner, rowHeight), {
			background: "surfaceContainer",
			radius: 9,
			border: "outlineVariant",
			borderWidth: 1
		}));
		changeNodes.push(label("activityChangeLabel_" + i, rect(10, rowY + 5, labelWidth, 15), changes[i].label || changes[i].field || "", {
			fontRole: "caption",
			color: "secondaryText",
			toolTip: changes[i].label || changes[i].field || ""
		}));
		changeNodes.push(node("View", "activityChangePort_" + i, rect(20 + labelWidth, rowY + 5, Math.max(0, g.inner - labelWidth - 30), rowHeight - 10), {
			view: "change",
			index: i
		}));
		y += rowHeight + 4;
	}
	content.push(node("Box", "activityChangeList", rect(10, changeTop, g.inner, Math.max(0, y - 4 - changeTop)), {
		visible: !!changes.length,
		background: "transparent",
		children: changeNodes
	}));
	if (changes.length) y += 2;
	if (model.expandable) {
		const w = 120;
		content.push(button("activityTextExpandButton", rect(Math.max(10, g.bubble - 10 - w), y - 4, w, 32), tr(model.expanded ? "Collapse" : "Expand"), model.expanded ? "chevron-up" : "chevron-down", { type: "expand" }, true, { tonal: true }));
		y += 38;
	}
	const bubbleHeight = y - 4 + 4, height = Math.max(72, bubbleHeight + 8);
	nodes.push(node("Preview", "activityActorPreview", rect(4, 4, g.avatar, g.avatar), {
		source: model.actorAvatar || "",
		initials: model.serverGenerated ? "" : model.actorInitials || "?",
		icon: model.serverGenerated ? "system-activity" : "person",
		round: true,
		outlined: true,
		accent: model.actorColor || "action"
	}));
	nodes.push(node("Box", "activityEventBubble", rect(g.x, 4, g.bubble, bubbleHeight), {
		background: model.hovered ? { mix: [
			"surfaceContainerHigh",
			"primaryText",
			.08
		] } : "surfaceContainerHigh",
		radius: metrics(style).communicationBubbleRadius,
		border: "outlineVariant",
		borderWidth: 1,
		children: content
	}));
	return {
		height,
		nodes
	};
}
//#endregion
//#region src/features/activity/ActivityEventCard.vue
var _hoisted_1$1 = ["data-event-id"];
var _sfc_main$2 = {
	__name: "ActivityEventCard",
	props: {
		record: Object,
		now: Number
	},
	emits: [
		"activity",
		"target",
		"open-link"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const expanded = ref(false);
		const sentence = ref(null), root = ref(null), width = ref(500), heights = ref({}), hovered = ref(false);
		let observer;
		const html = computed(() => eventSentence(props.record, expanded.value));
		watchPostEffect(() => {
			html.value;
			sentence.value?.querySelectorAll("[data-color]").forEach((element) => {
				element.style.color = safeColor(element.dataset.color);
			});
		});
		const changes = computed(() => !props.record.relationAction && [
			"create",
			"change",
			"delete"
		].includes(props.record.kind) ? props.record.changes || [] : []);
		const expandable = computed(() => [
			props.record.detail,
			props.record.title,
			...changes.value.map((change) => changeValue(props.record, change))
		].some(needsExpansion));
		const time = computed(() => {
			appearance.language;
			return timestampLabel(props.record.timestamp, new Date(props.now || Date.now()));
		});
		function activate(event) {
			if (activateRichLink(event, (value) => emit("open-link", value))) return;
			const action = event.target.closest("[data-action]")?.dataset.action;
			if (action) {
				event.preventDefault();
				emit(action);
			}
		}
		const fieldLabel = (value) => t({
			name: "Name",
			title: "Title",
			description: "Description",
			assigned: "Assignee",
			status: "Status",
			priority: "Priority",
			"bid start date": "Start date",
			"bid end date": "Deadline"
		}[String(value).toLowerCase()] || value);
		const model = computed(() => ({
			...props.record,
			time: time.value,
			fullTime: props.record.timestamp,
			expanded: expanded.value,
			expandable: expandable.value,
			hovered: hovered.value,
			changes: changes.value.map((row) => ({
				...row,
				label: fieldLabel(row.field)
			}))
		}));
		const scene = computed(() => card(model.value, width.value, heights.value, appearance.language, appearance.theme));
		const port = {
			props: { frameNode: Object },
			setup(port, { attrs }) {
				const element = ref(null);
				let resize;
				onMounted(() => {
					resize = observeFrameSizes(() => {
						const key = port.frameNode.view === "sentence" ? "sentence" : "change_" + port.frameNode.index, height = element.value.getBoundingClientRect().height;
						if (height > 0 && heights.value[key] !== height) heights.value = {
							...heights.value,
							[key]: height
						};
					});
					resize.observe(element.value);
				});
				onBeforeUnmount(() => resize?.disconnect());
				return () => {
					const body = port.frameNode.view === "sentence", change = changes.value[port.frameNode.index], value = body ? html.value : expanded.value ? linkifyPlainText(changeValue(props.record, change), browserLink) : escapeHtml(compactText(changeValue(props.record, change)));
					return h("div", attrs, [h("div", {
						ref: (node) => {
							element.value = node;
							if (body) sentence.value = node;
						},
						class: body ? "activity-sentence-port" : "activity-change-port",
						style: {
							overflowWrap: "anywhere",
							fontSize: body ? "13px" : "12px",
							lineHeight: body ? "18px" : "16px",
							userSelect: "text"
						},
						innerHTML: value,
						onClick: activate
					})]);
				};
			}
		};
		const views = {
			sentence: {
				component: port,
				nodeProps: true
			},
			change: {
				component: port,
				nodeProps: true
			}
		};
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				if (entries[0].contentRect.width > 0) width.value = entries[0].contentRect.width;
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("article", {
				ref_key: "root",
				ref: root,
				class: "activity-event-card",
				"data-event-id": __props.record.eventId,
				style: normalizeStyle({ height: scene.value.height + "px" }),
				onMouseenter: _cache[1] || (_cache[1] = ($event) => hovered.value = true),
				onMouseleave: _cache[2] || (_cache[2] = ($event) => hovered.value = false)
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				views,
				onEvent: _cache[0] || (_cache[0] = (event) => {
					if (event.type === "expand") expanded.value = !expanded.value;
				})
			}, null, 8, ["scene"])], 44, _hoisted_1$1);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/objects/snapshot_tree.ui.mjs
function describe(model, width, language) {
	const tr = (text) => translate(text, language), groups = model.groups || [], metrics = model.metrics || {}, nodes = [];
	nodes.push(node("Box", "objectSnapshotTreeHeader", rect(0, 0, width, 64), {
		background: "panel",
		border: "separator",
		children: [
			node("Icon", "objectSnapshotTreeIcon", rect(14, 23, 18, 18), {
				icon: "account-tree",
				color: "action"
			}),
			label("objectSnapshotTreeTitle", rect(42, 10, Math.max(0, width - 56), 22), tr("SNAPSHOTS BY PROCESS"), {
				fontRole: "bodyLarge",
				weight: 600
			}),
			label("objectSnapshotTreeCounts", rect(42, 34, Math.max(0, width - 56), 18), translate("{processes} processes · {snapshots} snapshots · {files} files", language, {
				processes: groups.length,
				snapshots: metrics.snapshots || 0,
				files: metrics.files || 0
			}), {
				color: "secondaryText",
				fontRole: "caption"
			})
		]
	}));
	let y = 74;
	groups.forEach((group, index) => {
		const inner = Math.max(0, width - 16), expanded = !!(model.expanded || {})[group.value], children = [];
		children.push(node("Action", "objectSnapshotProcess_" + index, rect(8, 8, inner, 62), {
			text: group.label,
			normalColor: "surfaceContainerHigh",
			radius: 12,
			action: {
				type: "expand",
				value: group.value
			},
			children: [
				node("Icon", "processExpand", rect(12, 22, 18, 18), {
					icon: expanded ? "expand-more" : "chevron-right",
					color: "secondaryText"
				}),
				node("Icon", "processIcon", rect(40, 22, 18, 18), {
					icon: "workflow",
					color: group.accent || "action"
				}),
				label("processLabel", rect(70, 8, Math.max(0, inner - 128), 23), group.label, {
					fontRole: "bodyLarge",
					weight: 600
				}),
				label("processCounts", rect(70, 34, Math.max(0, inner - 128), 18), translate("{snapshots} snapshots · {files} files · {size}", language, {
					snapshots: group.snapshotCount,
					files: group.fileCount,
					size: group.sizeText || "0 B"
				}), {
					fontRole: "caption",
					color: "secondaryText"
				}),
				node("StatusChip", "processBadge", rect(Math.max(0, inner - 48), 18, 40, 26), {
					text: String(group.snapshotCount),
					icon: "snapshot",
					accent: group.accent || "action"
				})
			]
		}));
		let top = 78;
		if (expanded) {
			children.push(label("snapshotsHeading", rect(18, top, Math.max(0, width - 36), 24), tr("SNAPSHOTS AND VERSIONS"), {
				fontRole: "secondary",
				weight: 600
			}));
			top += 32;
			(group.snapshots || []).forEach((snapshot, row) => {
				children.push(node("Action", "objectReportSnapshot_" + index + "_" + row, rect(8, top, inner, 72), {
					text: snapshot.title,
					normalColor: "surfaceContainerHigh",
					radius: 12,
					action: {
						type: "snapshot",
						index: snapshot.modelIndex,
						key: snapshot.searchKey
					},
					children: [
						node("Preview", "snapshotPreview", rect(8, 9, 54, 54), {
							source: snapshot.previewUrl || "",
							initials: snapshot.version,
							icon: "snapshot",
							outlined: true
						}),
						label("snapshotTitle", rect(72, 7, Math.max(0, inner - 152), 22), snapshot.title, {
							fontRole: "bodyLarge",
							weight: 600
						}),
						label("snapshotContext", rect(72, 31, Math.max(0, inner - 152), 17), [
							snapshot.context,
							snapshot.author,
							snapshot.repository
						].filter(Boolean).join(" · "), {
							fontRole: "caption",
							color: "secondaryText"
						}),
						label("snapshotFiles", rect(72, 50, Math.max(0, inner - 152), 17), translate("{files} files · {size} · {timestamp}", language, {
							files: snapshot.fileCount,
							size: snapshot.sizeText,
							timestamp: snapshot.timestampPretty
						}), {
							fontRole: "caption",
							color: "secondaryText",
							tooltip: snapshot.timestampFull || ""
						}),
						node("StatusChip", "snapshotVersion", rect(Math.max(0, inner - 72), 23, 64, 26), {
							text: snapshot.isVersionless ? tr("Current") : snapshot.version,
							icon: snapshot.isVersionless ? "sync" : "history",
							accent: snapshot.isLatest ? "green" : "action"
						})
					]
				}));
				top += 80;
			});
			if ((group.files || []).length) {
				children.push(label("filesHeading", rect(18, top, Math.max(0, width - 36), 24), tr("FILES"), {
					fontRole: "secondary",
					weight: 600
				}));
				top += 32;
			}
			(group.files || []).forEach((file, row) => {
				const height = (model.fileHeights || {})[file.token] || 64;
				children.push(node("View", "objectReportFile_" + index + "_" + row, rect(8, top, inner, height), {
					view: "attachment",
					record: file
				}));
				top += height + 8;
			});
		}
		const height = expanded ? top + 8 : 78;
		nodes.push(node("Box", "objectSnapshotProcessSurface_" + index, rect(0, y, width, height), {
			background: "panel",
			border: "separator",
			children
		}));
		y += height + 10;
	});
	if (!groups.length) {
		nodes.push(label("objectSnapshotTreeEmpty", rect(0, y, width, 72), tr("No snapshots found"), {
			color: "secondaryText",
			align: "center"
		}));
		y += 72;
	}
	return {
		nodes,
		height: y
	};
}
//#endregion
//#region src/features/objects/ObjectSnapshotTree.vue
var _sfc_main$1 = {
	__name: "ObjectSnapshotTree",
	props: {
		metrics: Object,
		groups: Array
	},
	emits: ["snapshot", "file"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(0), expanded = ref({}), fileHeights = ref({});
		const scene = computed(() => describe({
			metrics: props.metrics,
			groups: props.groups,
			expanded: expanded.value,
			fileHeights: fileHeights.value
		}, width.value, appearance.language));
		let observer;
		const views = { attachment: {
			nodeProps: true,
			component: {
				props: { frameNode: Object },
				setup(props, { attrs }) {
					const element = ref(null);
					let resize;
					onMounted(() => {
						resize = observeFrameSizes(() => {
							const height = element.value.scrollHeight, token = props.frameNode.record.token;
							if (height > 0 && fileHeights.value[token] !== height) fileHeights.value = {
								...fileHeights.value,
								[token]: height
							};
						});
						resize.observe(element.value);
					});
					onBeforeUnmount(() => resize?.disconnect());
					return () => {
						const record = props.frameNode.record;
						return h("div", { ...attrs }, [h("div", { ref: element }, [h(_sfc_main$6, {
							title: record.title,
							extension: record.extension,
							previewUrl: record.previewUrl,
							sizeText: record.sizeText,
							local: !!record.exists,
							webPreview: false,
							activationLabel: "Open attachment",
							onActivated: () => emit("file", record)
						})])]);
					};
				}
			}
		} };
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function action(event) {
			if (event.type === "expand") expanded.value = {
				...expanded.value,
				[event.value]: !expanded.value[event.value]
			};
			else if (event.type === "snapshot") emit("snapshot", event.key);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "object-snapshot-tree",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				views,
				onEvent: action
			}, null, 8, ["scene"])], 4);
		};
	}
};
//#endregion
//#region src/features/objects/ObjectReport.vue
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_3 = {
	key: 1,
	role: "status"
};
var _hoisted_4 = {
	key: 4,
	class: "object-report-activity"
};
var _hoisted_5 = {
	key: 0,
	class: "muted"
};
var _sfc_main = {
	__name: "ObjectReport",
	props: {
		ticket: String,
		project: String,
		record: Object
	},
	emits: ["open-link"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const openObjectTab = inject("openObjectTab", null), openTaskInspector = inject("openTaskInspector", null), openTaskManager = inject("openTaskManager", null), openUserProfile = inject("openUserProfile", null);
		const openSnapshotBrowser = inject("openSnapshotBrowser", null);
		const scroll = ref(null), content = ref(null), tabs$1 = ref(null), preview = ref(null), width = ref(0), data = ref(null), dataPage = ref(""), busy = ref(false), error = ref(""), page = ref("tasks"), activity = ref([]);
		let generation = 0, observer;
		const pages = /* @__PURE__ */ new Map();
		const cache = /* @__PURE__ */ new Map();
		const identity = computed(() => JSON.stringify([props.project, props.record?.__search_key__]));
		const snapshotGroups = computed(() => (data.value?.snapshot_processes || []).map((group) => ({
			...group,
			snapshots: group.snapshots.map((row) => ({
				...row,
				timestampPretty: timestampLabel(row.timestamp),
				timestampFull: timestampFullLabel(row.timestamp)
			}))
		})));
		const model = computed(() => {
			const value = data.value || {
				summary: {},
				metrics: {}
			};
			const now = /* @__PURE__ */ new Date();
			return {
				...value,
				page: page.value,
				busy: busy.value,
				summary: {
					...value.summary,
					updatedPretty: timestampLabel(value.summary.updatedFull, now)
				},
				tasks: (value.tasks || []).map((row) => ({
					...row,
					endPretty: timestampLabel(row.end, now),
					endFull: timestampFullLabel(row.end)
				})),
				notes: (value.notes || []).map((row) => ({
					...row,
					timestampPretty: timestampLabel(row.timestamp, now),
					timestampFull: timestampFullLabel(row.timestamp)
				}))
			};
		});
		const tabScene = computed(() => tabs(page.value, width.value, appearance.language));
		const pageReady = computed(() => dataPage.value === page.value);
		const pagination = usePagination(scroll, content, () => page.value === "activity" && pageReady.value && data.value?.hasMore && !busy.value && !error.value, () => load(true));
		watch([
			pageReady,
			busy,
			activity
		], pagination.check, { flush: "post" });
		async function load(append = false, refresh = false) {
			const key = props.record?.__search_key__;
			if (!key || !props.ticket || !props.project) return;
			const request = ++generation;
			const cacheKey = JSON.stringify([identity.value, page.value]);
			if (!append && !refresh && cache.has(cacheKey)) {
				data.value = cache.get(cacheKey);
				dataPage.value = page.value;
				activity.value = data.value.activity;
				error.value = "";
				busy.value = false;
				return;
			}
			busy.value = true;
			error.value = "";
			try {
				const result = await resultItems(props.ticket, props.project, key.split("?")[0], [key], {
					branch: {
						kind: "object_report",
						path: page.value
					},
					offset: append ? activity.value.length : 0,
					limit: 50
				});
				if (request !== generation) return;
				data.value = result;
				dataPage.value = page.value;
				activity.value = append ? [...activity.value, ...result.activity] : result.activity;
				cache.set(cacheKey, {
					...result,
					activity: activity.value
				});
				if (cache.size > 1e3) cache.delete(cache.keys().next().value);
			} catch (reason) {
				if (request === generation) error.value = reason.message;
			} finally {
				if (request === generation) busy.value = false;
			}
		}
		function selectPage(value) {
			if (!sections.some((row) => row.value === value) || value === page.value) return;
			page.value = value;
			pages.set(identity.value, value);
			activity.value = [];
			scroll.value.scrollTop = 0;
			load();
			pagination.reset();
		}
		function open(key) {
			if (key) openObjectTab?.(key.startsWith("skey://") ? key : "skey://" + key, props.project);
		}
		function snapshot(key) {
			const row = data.value.snapshots.find((row) => row.searchKey === key);
			if (row) openSnapshotBrowser?.(props.record, row.process, props.project);
		}
		function file(record) {
			const file = {
				...record,
				code: record.token,
				filename: record.title
			};
			preview.value.open({
				name: record.title,
				__search_key__: record.searchKey
			}, {
				files: [file],
				loadFile: fileBlob
			});
		}
		async function inspector(process, taskKey = "", noteKey = "") {
			return openTaskInspector?.(props.record, {}, process, taskKey, {
				ticket: props.ticket,
				project: props.project,
				searchType: props.record.__search_key__.split("?")[0],
				noteKey
			});
		}
		async function activityAction(record) {
			if (record.taskCode && ([
				"status",
				"task",
				"work_hour"
			].includes(record.kind) || record.itemType === "sthpw/task")) {
				const key = "sthpw/task?project=" + encodeURIComponent(props.project) + "&code=" + encodeURIComponent(record.taskCode);
				if (await inspector(record.process, key) !== false) openTaskManager?.(props.record, "", {}, key);
			} else if (record.kind === "note") inspector(record.process, record.taskCode ? "sthpw/task?project=" + encodeURIComponent(props.project) + "&code=" + encodeURIComponent(record.taskCode) : "", record.searchKey);
			else if (["publication", "snapshot"].includes(record.kind)) openSnapshotBrowser?.(props.record, record.process, props.project);
			else open(record.searchKey || props.record.__search_key__);
		}
		async function action(event) {
			if (event.type === "page") selectPage(event.value);
			else if (event.type === "refresh") load(false, true);
			else if (event.type === "open") open(model.value.summary.searchKey);
			else if (event.type === "link") openObjectTab?.(event.value, props.project);
			else if (event.type === "child") open(event.key);
			else if (event.type === "person") openUserProfile?.(event.key);
			else if (event.type === "task") {
				if (await inspector(event.process, event.key) !== false) openTaskManager?.(props.record, "", {}, event.key);
			} else if (event.type === "note") {
				const row = data.value.notes[event.index];
				await inspector(row.process, row.isTaskNote ? "sthpw/task?project=" + encodeURIComponent(props.project) + "&code=" + encodeURIComponent(row.taskCode) : "", row.searchKey);
			} else if (event.type === "filter") openTaskManager?.(props.record, event.field === "process" ? event.value : "", { [event.field]: event.value });
		}
		watch(() => [
			props.ticket,
			props.project,
			props.record
		], async () => {
			generation++;
			data.value = null;
			dataPage.value = "";
			activity.value = [];
			error.value = "";
			busy.value = false;
			page.value = pages.get(identity.value) || "tasks";
			if (pages.size > 200) pages.delete(pages.keys().next().value);
			await nextTick();
			if (tabs$1.value && !observer) {
				observer = observeFrameSizes(() => {
					width.value = tabs$1.value.clientWidth;
				});
				observer.observe(tabs$1.value);
				width.value = tabs$1.value.clientWidth;
			}
			load(false, true);
		}, { immediate: true });
		watch(() => props.ticket, () => {
			pages.clear();
			cache.clear();
		});
		onBeforeUnmount(() => {
			generation++;
			observer?.disconnect();
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "scroll",
				ref: scroll,
				class: "object-report",
				"aria-busy": busy.value,
				tabindex: "0"
			}, [createBaseVNode("div", {
				ref_key: "content",
				ref: content,
				class: "object-report-content"
			}, [
				createVNode(_sfc_main$3, {
					model: model.value,
					onEvent: action
				}, null, 8, ["model"]),
				createBaseVNode("div", {
					ref_key: "tabs",
					ref: tabs$1,
					class: "object-report-tabs"
				}, [createVNode(_sfc_main$5, {
					scene: tabScene.value,
					onEvent: action
				}, null, 8, ["scene"])], 512),
				error.value ? (openBlock(), createElementBlock("p", _hoisted_2, [createTextVNode(toDisplayString(unref(t)(error.value)) + " ", 1), createVNode(_sfc_main$4, {
					label: "Retry",
					disabled: busy.value,
					onClick: _cache[0] || (_cache[0] = ($event) => load(false, true))
				}, null, 8, ["disabled"])])) : createCommentVNode("", true),
				busy.value && !pageReady.value ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString(unref(t)("Loading data…")), 1)) : createCommentVNode("", true),
				pageReady.value && [
					"tasks",
					"notes",
					"children"
				].includes(page.value) ? (openBlock(), createBlock(_sfc_main$3, {
					key: 2,
					model: model.value,
					part: "page",
					onEvent: action
				}, null, 8, ["model"])) : pageReady.value && page.value === "snapshots" ? (openBlock(), createBlock(_sfc_main$1, {
					key: identity.value,
					metrics: data.value.metrics,
					groups: snapshotGroups.value,
					onSnapshot: snapshot,
					onFile: file
				}, null, 8, ["metrics", "groups"])) : pageReady.value && page.value === "activity" ? (openBlock(), createElementBlock("section", _hoisted_4, [
					(openBlock(true), createElementBlock(Fragment, null, renderList(activity.value, (record, index) => {
						return openBlock(), createBlock(_sfc_main$2, {
							key: record.eventId || index,
							record,
							onTarget: ($event) => open(record.targetSearchKey),
							onActivity: ($event) => activityAction(record),
							onOpenLink: open
						}, null, 8, [
							"record",
							"onTarget",
							"onActivity"
						]);
					}), 128)),
					!activity.value.length && !busy.value ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString(unref(t)("No recent activity")), 1)) : createCommentVNode("", true),
					data.value.hasMore ? (openBlock(), createBlock(_sfc_main$4, {
						key: 1,
						label: "Load more",
						disabled: busy.value,
						onClick: _cache[1] || (_cache[1] = ($event) => load(true))
					}, null, 8, ["disabled"])) : createCommentVNode("", true)
				])) : createCommentVNode("", true),
				createVNode(FilePreview_default, {
					ref_key: "preview",
					ref: preview,
					ticket: __props.ticket,
					project: __props.project,
					"search-type": __props.record?.__search_key__?.split("?")[0]
				}, null, 8, [
					"ticket",
					"project",
					"search-type"
				])
			], 512)], 8, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main$2 as n, usePagination as r, _sfc_main as t };

//# sourceMappingURL=ObjectReport.js.map
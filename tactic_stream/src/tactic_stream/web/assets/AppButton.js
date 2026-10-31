import { G as withCtx, K as withDirectives, L as resolveDynamicComponent, M as openBlock, P as renderSlot, U as watchEffect, X as ref, Y as reactive, _ as createElementBlock, et as unref, g as createCommentVNode, h as createBlock, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass } from "./vue.js";
import { n as en_default, t as ru_default } from "./locales.js";
import { n as resolveIcon } from "./icons.js";
//#region \0plugin-vue:export-helper
var _plugin_vue_export_helper_default = (sfc, props) => {
	const target = sfc.__vccOpts || sfc;
	for (const [key, val] of props) target[key] = val;
	return target;
};
var BusyIndicator_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "BusyIndicator",
	props: { running: Boolean },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				class: normalizeClass(["busy-indicator", { running: __props.running }]),
				"aria-hidden": "true"
			}, null, 2);
		};
	}
}, [["__scopeId", "data-v-bc754be8"]]);
//#endregion
//#region src/appearanceCatalog.js
var themes = [
	{
		"value": "md3",
		"label": "Material Design 3",
		"description": "Current TACTIC-Handler appearance"
	},
	{
		"value": "material5",
		"label": "Material Design 5 (preview)",
		"description": "Experimental project theme, not an official specification"
	},
	{
		"value": "fluent",
		"label": "Fluent Design",
		"description": "Compact Windows-oriented surfaces and motion"
	}
];
var iconSets = [
	{
		"value": "automatic",
		"label": "Automatic",
		"description": "Material-first icons with safe fallbacks"
	},
	{
		"value": "fontawesome-solid",
		"label": "Font Awesome Solid",
		"description": "Bold, filled application icons"
	},
	{
		"value": "fontawesome-outline",
		"label": "Font Awesome Outline",
		"description": "Lighter outlined icons where available"
	},
	{
		"value": "material-design",
		"label": "Material Design Icons",
		"description": "Material Design icon vocabulary"
	},
	{
		"value": "fluent-regular",
		"label": "Fluent Regular",
		"description": "Modern outlined Fluent System icons"
	},
	{
		"value": "fluent-filled",
		"label": "Fluent Filled",
		"description": "Modern filled Fluent System icons"
	}
];
var accentPresets = [
	{
		"value": "steel",
		"label": "Steel",
		"light": "#3d7599",
		"dark": "#78a6c4",
		"lightBase": "#d4dce1",
		"darkBase": "#292d30"
	},
	{
		"value": "silver",
		"label": "Silver",
		"light": "#67717a",
		"dark": "#b4bec6",
		"lightBase": "#d9dde0",
		"darkBase": "#303336"
	},
	{
		"value": "ash",
		"label": "Ash",
		"light": "#656662",
		"dark": "#adafaa",
		"lightBase": "#d8d8d6",
		"darkBase": "#2e2e2c"
	},
	{
		"value": "graphite",
		"label": "Graphite",
		"light": "#535a60",
		"dark": "#9da5ab",
		"lightBase": "#d2d4d5",
		"darkBase": "#27292b"
	},
	{
		"value": "charcoal",
		"label": "Charcoal",
		"light": "#41494f",
		"dark": "#89939a",
		"lightBase": "#ccd0d2",
		"darkBase": "#202326"
	},
	{
		"value": "blue",
		"label": "Blue",
		"light": "#2563a6",
		"dark": "#6ea8e6",
		"lightBase": "#d6dce8",
		"darkBase": "#272d36"
	},
	{
		"value": "azure",
		"label": "Azure",
		"light": "#0078b8",
		"dark": "#62b3dc",
		"lightBase": "#d2dfe5",
		"darkBase": "#253037"
	},
	{
		"value": "cyan",
		"label": "Cyan",
		"light": "#007c91",
		"dark": "#5bc0d1",
		"lightBase": "#d0dfe1",
		"darkBase": "#253234"
	},
	{
		"value": "teal",
		"label": "Teal",
		"light": "#087f6a",
		"dark": "#5abfa9",
		"lightBase": "#d2dfdc",
		"darkBase": "#263330"
	},
	{
		"value": "emerald",
		"label": "Emerald",
		"light": "#27824c",
		"dark": "#65b982",
		"lightBase": "#d5dfd8",
		"darkBase": "#29332c"
	},
	{
		"value": "green",
		"label": "Green",
		"light": "#4c7d28",
		"dark": "#86b85a",
		"lightBase": "#d9dfd3",
		"darkBase": "#2d3328"
	},
	{
		"value": "lime",
		"label": "Lime",
		"light": "#637a1b",
		"dark": "#a5bd4f",
		"lightBase": "#dde0d2",
		"darkBase": "#303326"
	},
	{
		"value": "amber",
		"label": "Amber",
		"light": "#946500",
		"dark": "#d5ad48",
		"lightBase": "#e3dccb",
		"darkBase": "#373126"
	},
	{
		"value": "orange",
		"label": "Orange",
		"light": "#a65316",
		"dark": "#e08b4e",
		"lightBase": "#e2d7cf",
		"darkBase": "#372d27"
	},
	{
		"value": "coral",
		"label": "Coral",
		"light": "#a4483c",
		"dark": "#de786b",
		"lightBase": "#e2d5d2",
		"darkBase": "#372b2a"
	},
	{
		"value": "red",
		"label": "Red",
		"light": "#a93f4d",
		"dark": "#de7180",
		"lightBase": "#e1d3d5",
		"darkBase": "#36292c"
	},
	{
		"value": "rose",
		"label": "Rose",
		"light": "#a83e78",
		"dark": "#dd75a9",
		"lightBase": "#e2d3db",
		"darkBase": "#362a31"
	},
	{
		"value": "violet",
		"label": "Violet",
		"light": "#76558d",
		"dark": "#b49ac8",
		"lightBase": "#ddd5e1",
		"darkBase": "#322d36"
	},
	{
		"value": "indigo",
		"label": "Indigo",
		"light": "#4f5ea8",
		"dark": "#8b99e0",
		"lightBase": "#d8d8e4",
		"darkBase": "#2d2e38"
	}
];
var defaultThemeAccents = {
	"md3": {
		"light": "steel",
		"dark": "steel"
	},
	"material5": {
		"light": "violet",
		"dark": "violet"
	},
	"fluent": {
		"light": "azure",
		"dark": "azure"
	}
};
//#endregion
//#region src/features/tasks/taskColumns.js
var taskColumns = [
	[
		"object",
		"Object",
		"object"
	],
	[
		"process",
		"Task / Process",
		"process"
	],
	[
		"status",
		"Status",
		"status"
	],
	[
		"assigned",
		"Assignee",
		"user"
	],
	[
		"dates",
		"Start / Deadline",
		"due"
	],
	[
		"progress",
		"Progress",
		""
	],
	[
		"bid_duration",
		"Hours",
		""
	],
	[
		"notes",
		"Notes",
		""
	],
	[
		"priority",
		"Priority",
		"priority"
	],
	[
		"milestone_code",
		"Milestone",
		"milestone"
	],
	[
		"supervisor",
		"Supervisor",
		"supervisor"
	]
].map(([key, label, sort], index) => ({
	key,
	label,
	sort,
	width: [
		210,
		126,
		138,
		154,
		112,
		94,
		86,
		48,
		96,
		132,
		154
	][index],
	visible: index < 8,
	group: {
		object: "object",
		process: "process",
		status: "status",
		assigned: "user"
	}[key] || ""
}));
function normalizeColumns(saved) {
	const ordered = [], seen = /* @__PURE__ */ new Set();
	for (const item of Array.isArray(saved) ? saved : []) {
		const original = taskColumns.find((column) => column.key === item?.key);
		if (!original || seen.has(item.key)) continue;
		const width = Number(item.width);
		ordered.push({
			...original,
			width: Number.isFinite(width) ? Math.max(40, Math.min(480, Math.trunc(width))) : original.width,
			visible: item.key === "object" || (typeof item.visible === "boolean" ? item.visible : original.visible)
		});
		seen.add(item.key);
	}
	return [...ordered, ...taskColumns.filter((column) => !seen.has(column.key)).map((column) => ({ ...column }))];
}
//#endregion
//#region src/features/configuration/preferences.js
var configurationPreview = ref(false);
var preferenceDefaults = {
	checkin: {
		displayLimit: 20,
		defaultViewMode: "continious",
		loadingMode: "pages",
		keepFilename: false,
		groupCheckin: true,
		includeSubfolders: false,
		generatePreviews: true,
		confirmRevision: true,
		commitQueueAutoClean: true
	},
	tasks: {
		workspaceSurface: "browser",
		quickViewMode: "cards",
		viewMode: "table",
		sortMode: "due",
		groupMode: "process",
		inspectorExpanded: false,
		columns: []
	},
	global: {
		activityNotifications: true,
		messageNotifications: true
	},
	cache: { cacheProcessTabs: true },
	repository: {
		enabledAliases: null,
		defaultAlias: "default"
	}
};
function normalizePreferences(value = {}) {
	const result = structuredClone(preferenceDefaults);
	for (const [page, fields] of Object.entries(result)) for (const [key, fallback] of Object.entries(fields)) {
		const saved = value?.[page]?.[key];
		if (typeof fallback === "boolean" && typeof saved === "boolean") fields[key] = saved;
	}
	for (const [page, fields] of Object.entries({
		checkin: {
			defaultViewMode: [
				"continious",
				"tiles",
				"table",
				"compact",
				"splitted_vertical",
				"splitted_horizontal"
			],
			loadingMode: ["pages", "infinite"]
		},
		tasks: {
			workspaceSurface: ["browser", "quick"],
			quickViewMode: ["cards", "compact"],
			viewMode: ["table", "gantt"],
			sortMode: [
				"due",
				"recent",
				"user",
				"process",
				"status",
				"object",
				"search_type",
				"project",
				"priority",
				"milestone",
				"supervisor"
			],
			groupMode: [
				"none",
				"user",
				"process",
				"status",
				"object"
			]
		}
	})) for (const [key, allowed] of Object.entries(fields)) if (allowed.includes(value?.[page]?.[key])) result[page][key] = value[page][key];
	const limit = Number(value?.checkin?.displayLimit);
	if (Number.isFinite(limit) && limit > 0) result.checkin.displayLimit = Math.max(1, Math.min(500, Math.trunc(limit)));
	result.tasks.columns = normalizeColumns(value?.tasks?.columns);
	const alias = (value) => typeof value === "string" && /^[A-Za-z0-9_.-]+$/.test(value) && value !== "plugins";
	if (Array.isArray(value?.repository?.enabledAliases)) result.repository.enabledAliases = [...new Set(value.repository.enabledAliases.filter(alias))];
	if (alias(value?.repository?.defaultAlias)) result.repository.defaultAlias = value.repository.defaultAlias;
	return result;
}
var saved;
try {
	saved = JSON.parse(localStorage.getItem("tactic_stream.preferences") || "null");
} catch {}
var preferences = reactive(normalizePreferences(saved));
function savePreferencePage(page, value) {
	const next = normalizePreferences({
		...preferences,
		[page]: value
	});
	localStorage.setItem("tactic_stream.preferences", JSON.stringify(next));
	Object.assign(preferences[page], next[page]);
}
//#endregion
//#region ../src/tactic_stream/shared_ui/core/interaction.mjs
function buttonVisual(state = {}) {
	const enabled = state.enabled !== false && !state.loading;
	const active = state.hovered || state.focused;
	let background = "surfaceContainerHigh";
	let content = "primaryText";
	if (state.segmented) {
		background = !enabled ? "transparent" : state.pressed ? "surfaceContainerHighest" : state.checked ? "selected" : active ? "rowHover" : "transparent";
		content = state.checked ? "selectedText" : "secondaryText";
	} else if (enabled) {
		if (state.pressed) background = state.destructive && state.highlighted ? "error" : "selected";
		else if (state.highlighted) background = state.destructive ? "error" : "action";
		else if (active) background = "rowHover";
		else if (state.tonal) background = "secondaryContainer";
		content = state.destructive ? state.highlighted ? "onError" : "error" : state.highlighted ? "selectedText" : "primaryText";
	}
	return {
		background,
		content: enabled ? content : "disabledText",
		border: state.destructive ? "error" : "outlineVariant",
		borderWidth: state.segmented || state.highlighted || state.flat ? 0 : 1,
		pressedMix: enabled && state.pressed && state.destructive && state.highlighted
	};
}
function fieldVisual(state = {}) {
	return {
		background: state.tableCell && !state.focused ? "transparent" : "surfaceContainerHigh",
		content: state.enabled === false ? "disabledText" : "primaryText",
		border: state.error ? "error" : state.focused ? "action" : "outline",
		borderWidth: state.focused ? 2 : state.tableCell ? 0 : 1
	};
}
function checkVisual(state = {}) {
	const selected = state.checked || state.mixed;
	const disabled = state.enabled === false;
	return {
		background: selected ? disabled ? "surfaceContainerHigh" : "action" : state.prominent ? "surfaceContainerHighest" : "transparent",
		content: disabled ? "disabledText" : "primaryText",
		mark: disabled ? "disabledText" : "selectedText",
		border: disabled ? "disabledText" : selected || state.focused ? "action" : state.prominent ? "secondaryText" : "outline",
		borderWidth: state.focused || state.prominent ? 2 : 1
	};
}
function switchVisual(state = {}) {
	const disabled = state.enabled === false;
	return {
		background: disabled ? "surfaceContainerHigh" : state.checked ? "action" : "surfaceContainerHighest",
		border: disabled ? "disabledText" : state.checked || state.focused ? "action" : "outline",
		thumb: disabled ? "disabledText" : state.checked ? "selectedText" : "secondaryText",
		borderWidth: state.focused ? 2 : 1
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/core/foundation.mjs
var typography = {
	micro: 8,
	caption: 8.25,
	label: 8.75,
	body: 9.25,
	bodyLarge: 10,
	title: 12
};
var fontFamily = "Segoe UI";
var spacing = Object.freeze({
	none: 0,
	text: 2,
	tight: 4,
	compact: 8,
	content: 12,
	section: 16,
	major: 24
});
function fontMetricHeight(pixelSize) {
	return pixelSize * 1.328125;
}
function fontLineHeight(pixelSize) {
	return Math.ceil(fontMetricHeight(pixelSize));
}
var lineHeights = Object.freeze({
	timelineTick: 10,
	timelineMajorTick: 11,
	menuHeading: 14,
	caption: 15,
	secondary: 16,
	body: 18,
	bodyLarge: 19,
	section: 20,
	title: 22,
	heading: 23,
	display: 24,
	statistic: 28,
	hero: 32,
	headline: 43
});
var textStyles = Object.freeze({
	timelineTick: 7,
	timelineMajorTick: 8,
	menuHeading: 10,
	caption: 11,
	secondary: 12,
	body: 13,
	bodyLarge: 14,
	section: 15,
	title: 16,
	heading: 17,
	display: 18,
	statistic: 21,
	hero: 24,
	headline: 32
});
var controls = {
	dialog: {
		padding: spacing.content,
		spacing: spacing.none,
		headerHeight: 40,
		headerPadding: spacing.content,
		titleSize: 13,
		shadowY: 6,
		shadowBlur: 14
	},
	document: {
		bodySize: 12,
		lineHeight: 17,
		headingSize: 18,
		headingLineHeight: 22.5,
		paragraphGap: 8,
		headingGap: 14,
		cellPadding: 4
	},
	field: {
		padding: 12,
		areaPadding: 10
	},
	choice: {
		rowHeight: 34,
		visibleRows: 8,
		popupPadding: 4,
		popupGap: 4,
		paddingLeft: 11,
		paddingRight: 32,
		indicatorSize: 17,
		indicatorRight: 9,
		indicatorHit: 40
	},
	tooltip: {
		delay: 500,
		timeout: 5e3,
		margin: 8,
		paddingX: 12,
		paddingY: 7,
		radius: 6
	},
	userPicker: {
		popupWidth: 294,
		popupHeight: 286,
		rowHeight: 48,
		avatarSize: 32
	},
	calendar: {
		popupWidth: 304,
		padding: spacing.content,
		rowHeight: 30,
		daySize: 28
	},
	colorPicker: {
		popupWidth: 380,
		planeHeight: 190,
		padding: spacing.content
	},
	iconPicker: {
		popupWidth: 560,
		popupHeight: 440
	},
	button: {
		minimumWidth: 72,
		padding: 16,
		iconPadding: 12,
		spacing: 7,
		segmentedSpacing: 6,
		segmentedPaddingStart: 3,
		segmentedPaddingEnd: 7,
		iconSize: 16,
		compactIconSize: 18,
		segmentedIconSize: 15
	},
	iconButton: {
		extent: 28,
		iconSize: 17,
		surfaceInset: 2,
		hoveredOpacity: .08,
		pressedOpacity: .12
	},
	checkBox: {
		height: 36,
		compactHeight: 30,
		spacing: 9,
		compactSpacing: 6,
		indicator: 19,
		compactIndicator: 17,
		prominentIndicator: 22,
		iconSize: 15,
		compactIconSize: 13,
		prominentIconSize: 17,
		radius: 5
	},
	switch: {
		width: 42,
		height: 24,
		thumb: 18,
		inset: 3,
		spacing: 10
	},
	search: {
		padding: 38,
		iconInset: 12,
		iconSize: 18,
		clearInset: 4,
		clearExtent: 30,
		clearIconSize: 17,
		popupMinimumWidth: 240,
		popupPadding: 4,
		popupGap: 6,
		rowHeight: 34
	},
	number: {
		indicatorWidth: 34,
		iconSize: 14
	},
	feedback: {
		progressHeight: 4,
		busyExtent: 24
	},
	slider: {
		height: 26,
		track: 4,
		thumb: 16,
		thumbBorder: 2,
		padding: 6
	},
	identity: {
		avatarSize: 40,
		spacing: 12,
		textSpacing: 3
	},
	summaryChip: {
		height: 30,
		compactHeight: 24,
		spacing: 7,
		padding: 10,
		compactPadding: 8,
		dot: 8
	},
	filterChip: {
		height: 32,
		emphasisHeight: 12,
		iconSize: 11,
		emphasisIconSize: 4,
		emphasisFontSize: 11
	},
	loadingOverlay: {
		spacing: 10,
		surfaceOpacity: .88,
		minimumWidth: 180,
		maximumWidth: 420,
		horizontalMargin: 40
	},
	statusChip: {
		height: 24,
		denseHeight: 20,
		spacing: 5,
		padding: 8,
		densePadding: 5,
		iconSize: 13,
		denseIconSize: 11
	},
	reactionChip: {
		height: 28,
		padding: 8,
		spacing: 5,
		emojiSize: 18,
		tintOpacity: .18,
		checkedTintOpacity: .34
	},
	editorPanel: {
		padding: spacing.content,
		spacing: spacing.content,
		contentSpacing: spacing.compact,
		headerSpacing: spacing.compact,
		textSpacing: spacing.text,
		actionsSpacing: spacing.compact,
		iconSize: 20
	},
	formField: {
		padding: spacing.content,
		labelWidth: 220,
		columnSpacing: spacing.content,
		rowSpacing: spacing.compact,
		iconExtent: 34,
		iconSize: 17,
		labelSpacing: spacing.compact,
		textSpacing: spacing.text,
		editorSpacing: spacing.tight,
		compactBreakpoint: 700
	},
	editorListItem: {
		padding: spacing.content,
		spacing: spacing.compact,
		iconSize: 19,
		textSpacing: spacing.tight,
		minimumExtraHeight: 12
	},
	emptyState: {
		height: 140,
		iconSize: 30,
		spacing: 8,
		maximumWidth: 440,
		horizontalMargin: 24
	},
	dropTarget: {
		margin: 6,
		borderWidth: 2,
		iconSize: 30,
		spacing: 8,
		textSize: 12,
		surfaceOpacity: .94
	},
	imagePicker: {
		previewSize: 112,
		minimumActionsWidth: 290,
		columnSpacing: 16,
		rowSpacing: 12
	},
	splitter: {
		extent: 10,
		thickness: 3,
		length: 40,
		restingOpacity: .28,
		hoveredOpacity: .85,
		pressedOpacity: 1
	},
	scrollBar: {
		extent: 12,
		restingTrack: 6,
		expandedTrack: 11,
		restingThumb: 5,
		expandedThumb: 8,
		restingTrackOpacity: .055,
		expandedTrackOpacity: .15,
		restingThumbOpacity: .42,
		hoveredThumbOpacity: .72,
		pressedThumbOpacity: .9,
		disabledThumbOpacity: .18
	}
};
var styleMetrics = {
	md3: {
		controlHeight: 36,
		compactControlHeight: 32,
		fieldRadius: 10,
		buttonRadius: 18,
		itemRadius: 9,
		snapshotRadius: 5,
		surfaceRadius: 12,
		sectionRadius: 16,
		dialogRadius: 8,
		menuRadius: 16,
		iconButtonRadius: 4,
		communicationGroupedSpacing: 2,
		communicationGroupTailSize: 10,
		communicationBubbleRadius: 14,
		communicationGroupedBubbleRadius: 8,
		baseMotionInstant: 28,
		baseMotionFast: 48,
		baseMotionMedium: 56,
		baseMotionSlow: 72,
		baseMotionExtended: 104
	},
	material5: {
		controlHeight: 38,
		compactControlHeight: 34,
		fieldRadius: 15,
		buttonRadius: 16,
		itemRadius: 13,
		snapshotRadius: 10,
		surfaceRadius: 18,
		sectionRadius: 22,
		dialogRadius: 8,
		menuRadius: 20,
		iconButtonRadius: 9,
		communicationGroupedSpacing: 3,
		communicationGroupTailSize: 11,
		communicationBubbleRadius: 16,
		communicationGroupedBubbleRadius: 10,
		baseMotionInstant: 36,
		baseMotionFast: 60,
		baseMotionMedium: 76,
		baseMotionSlow: 96,
		baseMotionExtended: 128
	},
	fluent: {
		controlHeight: 34,
		compactControlHeight: 32,
		fieldRadius: 5,
		buttonRadius: 5,
		itemRadius: 5,
		snapshotRadius: 3,
		surfaceRadius: 7,
		sectionRadius: 8,
		dialogRadius: 8,
		menuRadius: 8,
		iconButtonRadius: 4,
		communicationGroupedSpacing: 2,
		communicationGroupTailSize: 10,
		communicationBubbleRadius: 7,
		communicationGroupedBubbleRadius: 4,
		baseMotionInstant: 24,
		baseMotionFast: 36,
		baseMotionMedium: 48,
		baseMotionSlow: 64,
		baseMotionExtended: 88
	}
};
var layout = {
	appBarHeight: 44,
	sectionRailWidth: 48,
	dockTitleHeight: 38,
	dockWorkspaceHeaderHeight: 96,
	dockWorkspaceFooterHeight: 58,
	communicationListSpacing: 10,
	communicationBubblePadding: 10,
	communicationContentSpacing: 6,
	communicationAvatarSpacing: 8,
	scrollbarExtent: 12,
	splitterExtent: 10,
	windowMargin: 16,
	dragThreshold: 5
};
function metrics(style) {
	return Object.assign({}, layout, styleMetrics[style] || styleMetrics.md3);
}
function motion(style, preferences) {
	const values = metrics(style), flags = preferences || {}, result = {};
	for (const duration of [
		"Instant",
		"Fast",
		"Medium",
		"Slow",
		"Extended"
	]) {
		const value = values["baseMotion" + duration];
		result["motion" + duration] = flags.fade === false || flags.reduced ? 0 : value;
		result["clickMotion" + duration] = flags.click === false || flags.reduced ? 0 : value;
		result["hoverMotion" + duration] = flags.hover === false || flags.reduced ? 0 : value;
		result["popupMotion" + duration] = flags.popup === false || flags.reduced ? 0 : value;
	}
	result.scrollMotion = result.motionInstant;
	return result;
}
function blend(first, second, weight) {
	const amount = Math.max(0, Math.min(1, weight));
	return first.map((channel, index) => channel * (1 - amount) + second[index] * amount);
}
function readableText$1(color) {
	return (color[0] * .2126 + color[1] * .7152 + color[2] * .0722) / 255 > .56 ? [
		23,
		32,
		39
	] : [
		246,
		248,
		250
	];
}
function rgb(hex) {
	return [
		1,
		3,
		5
	].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
}
function palette(style, dark, base, accent) {
	const black = [
		0,
		0,
		0
	], white = [
		255,
		255,
		255
	];
	const material = style === "material5", fluent = style === "fluent";
	const colors = {
		action: accent,
		blackMix: black,
		whiteMix: white
	};
	colors.paletteBase = material ? blend(base, accent, dark ? .07 : .05) : base;
	const surface = colors.paletteBase;
	colors.workspace = blend(surface, dark ? black : white, dark ? fluent ? .23 : .34 : fluent ? .12 : .08);
	colors.topBar = blend(surface, dark ? white : black, dark ? material ? .05 : .03 : .03);
	colors.toolBar = blend(surface, dark ? white : black, dark ? material ? .11 : .08 : .07);
	colors.panel = blend(surface, dark ? black : white, dark ? .04 : .22);
	colors.surfaceContainerLowest = dark ? colors.panel : blend(surface, white, .94);
	colors.panelRaised = blend(surface, white, dark ? .08 : .38);
	colors.panelDeep = blend(surface, black, dark ? .19 : .08);
	colors.row = blend(surface, white, dark ? .07 : .32);
	colors.rowHover = blend(colors.row, accent, dark ? .1 : .08);
	colors.selected = blend(accent, colors.panelRaised, dark ? .28 : .3);
	colors.contentSelection = blend(accent, colors.workspace, dark ? .68 : .72);
	colors.primaryText = readableText$1(colors.workspace);
	colors.tableHeader = dark ? blend(colors.panelRaised, accent, .1) : blend(colors.surfaceContainerLowest, colors.primaryText, .035);
	colors.tableAlternateRow = blend(colors.surfaceContainerLowest, colors.primaryText, dark ? .018 : .014);
	colors.tableDivider = blend(colors.panel, colors.primaryText, dark ? .075 : .1);
	colors.contentAccent = blend(accent, colors.primaryText, dark ? .12 : .08);
	colors.selectedText = readableText$1(colors.selected);
	colors.contentSelectionText = readableText$1(colors.contentSelection);
	colors.secondaryText = blend(colors.primaryText, surface, dark ? .35 : .42);
	colors.disabledText = blend(colors.secondaryText, surface, .42);
	colors.separator = blend(surface, colors.primaryText, dark ? .11 : .18);
	colors.border = blend(surface, colors.primaryText, dark ? .24 : .3);
	const fixed = {
		green: "#52a86e",
		yellow: "#d5bd51",
		red: "#d65b67",
		missingFile: "#d45b5b",
		violet: "#a06bb4",
		cyan: "#56a7b3"
	};
	for (const name of Object.keys(fixed)) colors[name] = rgb(fixed[name]);
	const syntax = {
		Keyword: ["#d5bd51", "#808000"],
		String: ["#69b77d", "#008000"],
		Comment: ["#70a87a", "#008000"],
		Number: ["#66b8c4", "#000080"],
		Type: ["#bc84cf", "#800080"],
		Function: ["#66b8c4", "#00677c"],
		Definition: ["#d39562", "#7c4800"],
		Self: ["#88aac4", "#092e64"],
		Occurrence: ["#55545a", "#b4b4b4"],
		Search: ["#75651f", "#ffef0b"]
	};
	for (const name of Object.keys(syntax)) colors["syntax" + name] = rgb(syntax[name][dark ? 0 : 1]);
	colors.titleGreen = rgb(dark ? "#4c8700" : "#5f970d");
	colors.ripple = (dark ? white : black).concat((dark ? 52 : 34) / 255);
	colors.rippleStrong = (dark ? white : black).concat((dark ? 56 : 36) / 255);
	colors.popupShadow = black.concat((dark ? 74 : 40) / 255);
	colors.dialogShadow = black.concat((dark ? 82 : 48) / 255);
	colors.scrim = black.concat((dark ? 153 : 115) / 255);
	const aliases = {
		tooltipSurface: "panelRaised",
		tooltipText: "primaryText",
		background: "workspace",
		surface: "panel",
		surfaceContainerLow: "panel",
		surfaceContainer: "toolBar",
		surfaceContainerHigh: "panelRaised",
		surfaceContainerHighest: "rowHover",
		surfaceVariant: "toolBar",
		outline: "border",
		outlineVariant: "separator",
		primary: "action",
		primaryContainer: "selected",
		secondary: "secondaryText",
		secondaryContainer: "rowHover",
		tertiary: "violet",
		tertiaryContainer: "rowHover",
		error: "red",
		errorContainer: "rowHover",
		text: "primaryText",
		muted: "secondaryText",
		accent: "action",
		accentContainer: "selected"
	};
	for (const name of Object.keys(aliases)) colors[name] = colors[aliases[name]];
	colors.onError = readableText$1(colors.error);
	colors.inverseSurface = rgb("#eeeeee");
	colors.inverseOnSurface = rgb("#202020");
	return colors;
}
var cssRoles = {
	workspace: "--page",
	topBar: "--header",
	toolBar: "--surface-container",
	tableHeader: "--table-header-surface",
	tableAlternateRow: "--table-alternate-row",
	tableDivider: "--table-divider",
	panel: "--surface",
	surfaceContainerLowest: "--surface-lowest",
	panelRaised: "--surface-high",
	panelDeep: "--surface-deep",
	row: "--row",
	rowHover: "--hover",
	selected: "--selected",
	selectedText: "--on-selected",
	contentSelection: "--content-selection",
	contentSelectionText: "--on-content-selection",
	contentAccent: "--content-accent",
	primaryText: "--on-surface",
	secondaryText: "--muted",
	disabledText: "--disabled",
	border: "--outline",
	separator: "--outline-variant",
	action: "--primary",
	red: "--error",
	green: "--success",
	yellow: "--yellow",
	cyan: "--cyan",
	violet: "--violet",
	tertiary: "--tertiary",
	tertiaryContainer: "--tertiary-container",
	surfaceContainerLow: "--surface",
	surfaceContainer: "--surface-container",
	surfaceContainerHigh: "--surface-high",
	surfaceContainerHighest: "--surface-highest",
	secondaryContainer: "--secondary-container",
	outline: "--outline",
	outlineVariant: "--outline-variant",
	error: "--error",
	errorContainer: "--error-container",
	onError: "--on-error",
	ripple: "--ripple-color",
	popupShadow: "--shadow-color",
	scrim: "--scrim",
	dialogShadow: "--dialog-shadow"
};
function cssColor(channels) {
	return "rgba(" + channels.slice(0, 3).join(",") + "," + (channels.length === 4 ? channels[3] : 1) + ")";
}
function cssVariables(style, dark, base, accent, preferences) {
	const colors = palette(style, dark, base, accent), values = metrics(style), result = {};
	for (const name of Object.keys(spacing)) result["--space-" + name] = spacing[name] + "px";
	for (const role of Object.keys(cssRoles)) result[cssRoles[role]] = cssColor(colors[role]);
	for (const name of Object.keys(values)) {
		const cssName = "--" + name.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[cssName] = values[name] + (name.indexOf("baseMotion") === 0 ? "ms" : "px");
	}
	for (const name of Object.keys(typography)) {
		const cssName = "--text-" + name.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[cssName] = typography[name] + "pt";
	}
	result["--control-text-size"] = textStyles.body + "px";
	result["--control-compact-text-size"] = textStyles.secondary + "px";
	for (const role of Object.keys(textStyles)) {
		const name = role.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result["--font-" + name + "-size"] = textStyles[role] + "px";
		result["--font-" + name + "-line-height"] = lineHeights[role] + "px";
	}
	const states = {
		field: {
			idle: fieldVisual(),
			focus: fieldVisual({ focused: true }),
			error: fieldVisual({ error: true }),
			disabled: fieldVisual({ enabled: false })
		},
		check: {
			idle: checkVisual(),
			checked: checkVisual({ checked: true }),
			focus: checkVisual({ focused: true }),
			disabled: checkVisual({ enabled: false }),
			disabledChecked: checkVisual({
				checked: true,
				enabled: false
			})
		},
		switch: {
			idle: switchVisual(),
			checked: switchVisual({ checked: true }),
			focus: switchVisual({ focused: true }),
			disabled: switchVisual({ enabled: false })
		}
	};
	for (const [kind, variants] of Object.entries(states)) for (const [state, paint] of Object.entries(variants)) for (const [part, value] of Object.entries(paint)) {
		const name = ("--" + kind + "-" + state + "-" + part).replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[name] = typeof value === "number" ? value + "px" : value === "transparent" ? value : cssColor(colors[value]);
	}
	for (const kind of Object.keys(controls)) for (const name of Object.keys(controls[kind])) {
		const cssName = "--" + (kind + name[0].toUpperCase() + name.slice(1)).replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[cssName] = controls[kind][name] + (name.endsWith("Opacity") || name === "visibleRows" ? "" : name === "delay" || name === "timeout" ? "ms" : "px");
	}
	const timings = motion(style, preferences);
	for (const name of [
		"Instant",
		"Fast",
		"Medium",
		"Slow",
		"Extended"
	]) result["--motion-" + name.toLowerCase()] = timings["motion" + name] + "ms";
	const feedback = {
		"--motion-click": "clickMotionFast",
		"--motion-click-expansion": "clickMotionMedium",
		"--motion-click-slow": "clickMotionSlow",
		"--motion-click-extended": "clickMotionExtended",
		"--motion-hover": "hoverMotionFast",
		"--motion-hover-medium": "hoverMotionMedium",
		"--motion-fade": "motionMedium",
		"--motion-fade-slow": "motionSlow",
		"--motion-fade-extended": "motionExtended",
		"--motion-popup": "popupMotionMedium",
		"--motion-popup-fast": "popupMotionFast",
		"--motion-popup-slow": "popupMotionSlow"
	};
	for (const name of Object.keys(feedback)) result[name] = timings[feedback[name]] + "ms";
	for (const name of Object.keys(colors)) if (name.indexOf("syntax") === 0) result["--syntax-" + name.slice(6).toLowerCase()] = cssColor(colors[name]);
	result["--on-primary"] = cssColor(readableText$1(accent));
	result["--font-family"] = "\"Segoe UI\", system-ui, sans-serif";
	result["--communication-bubble-radius"] = values.communicationBubbleRadius + "px";
	result["--workspace-footer-height"] = values.dockWorkspaceFooterHeight + "px";
	result["--preview-radius"] = values.snapshotRadius + "px";
	return result;
}
//#endregion
//#region src/appearance.js
var languages = [{
	value: "en",
	label: "English"
}, {
	value: "ru",
	label: "Russian"
}];
var colorModes = [
	{
		value: "system",
		label: "System"
	},
	{
		value: "light",
		label: "Light"
	},
	{
		value: "dark",
		label: "Dark"
	}
];
var storageKey = "tactic_stream.appearance";
for (const [area, suffix] of [["localStorage", "appearance"], ["sessionStorage", "session"]]) try {
	const storage = window[area];
	const previousKey = `tactic_flow.${suffix}`;
	const nextKey = `tactic_stream.${suffix}`;
	const previous = storage.getItem(previousKey);
	if (previous && storage.getItem(nextKey) === null) storage.setItem(nextKey, previous);
	storage.removeItem(previousKey);
} catch {}
function readAppearance() {
	let saved;
	try {
		saved = JSON.parse(localStorage.getItem(storageKey) || "null");
	} catch {}
	const language = typeof saved?.language === "string" ? saved.language.toLowerCase().replace("_", "-").split("-")[0] : "en";
	const themeAccents = {};
	for (const theme of themes) {
		themeAccents[theme.value] = {};
		for (const mode of ["light", "dark"]) {
			const preset = saved?.themeAccents?.[theme.value]?.[mode];
			themeAccents[theme.value][mode] = accentPresets.some((item) => item.value === preset) ? preset : defaultThemeAccents[theme.value][mode];
		}
	}
	return {
		language: languages.some((item) => item.value === language) ? language : "en",
		theme: themes.some((item) => item.value === saved?.theme) ? saved.theme : "md3",
		mode: colorModes.some((item) => item.value === saved?.mode) ? saved.mode : "system",
		iconSet: iconSets.some((item) => item.value === saved?.iconSet) ? saved.iconSet : "material-design",
		discussionView: saved?.discussionView === "notes" ? "notes" : "inspector",
		themeAccents,
		clickAnimations: saved?.clickAnimations !== false,
		hoverAnimations: saved?.hoverAnimations !== false,
		fadeAnimations: saved?.fadeAnimations !== false,
		popupAnimations: saved?.popupAnimations !== false
	};
}
var appearance = reactive(readAppearance());
var hostedPalette = ref(null);
var projectPalette = ref(null);
function readableText(color) {
	return "#" + readableText$1(color).map((channel) => channel.toString(16).padStart(2, "0")).join("");
}
function saveAppearance() {
	localStorage.setItem(storageKey, JSON.stringify(appearance));
}
var systemDark = ref(typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches);
var effectiveColorMode = computed(() => appearance.mode === "system" ? systemDark.value ? "dark" : "light" : appearance.mode);
var projectPreset = computed(() => projectPalette.value ? {
	light: projectPalette.value.light.accent,
	lightBase: projectPalette.value.light.base,
	dark: projectPalette.value.dark.accent,
	darkBase: projectPalette.value.dark.base
} : null);
var colorPreset = computed(() => hostedPalette.value || projectPreset.value || accentPresets.find((item) => item.value === appearance.themeAccents[appearance.theme][effectiveColorMode.value]));
var effectiveStyle = computed(() => hostedPalette.value ? appearance.theme : projectPalette.value?.style || appearance.theme);
var channels = (hex) => hex.match(/[a-f\d]{2}/gi).map((value) => parseInt(value, 16));
var frameColors = computed(() => {
	const mode = effectiveColorMode.value, preset = colorPreset.value;
	return palette(effectiveStyle.value, mode === "dark", channels(preset[mode + "Base"]), channels(preset[mode]));
});
function initializeAppearance() {
	const media = window.matchMedia("(prefers-color-scheme: dark)");
	const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
	const reducedMotion = ref(motion.matches);
	systemDark.value = media.matches;
	media.addEventListener("change", (event) => {
		systemDark.value = event.matches;
	});
	motion.addEventListener("change", (event) => {
		reducedMotion.value = event.matches;
	});
	watchEffect(() => {
		const root = document.documentElement;
		root.lang = appearance.language;
		root.dataset.theme = effectiveStyle.value;
		const mode = effectiveColorMode.value;
		root.dataset.mode = mode;
		root.dataset.iconSet = appearance.iconSet;
		const palette = colorPreset.value;
		root.style.setProperty("--base", palette[mode + "Base"]);
		root.style.setProperty("--primary", palette[mode]);
		const accent = palette[mode].match(/[a-f\d]{2}/gi).map((value) => parseInt(value, 16));
		const base = palette[mode + "Base"].match(/[a-f\d]{2}/gi).map((value) => parseInt(value, 16));
		const dark = mode === "dark";
		const variables = cssVariables(effectiveStyle.value, dark, base, accent, {
			click: appearance.clickAnimations,
			hover: appearance.hoverAnimations,
			fade: appearance.fadeAnimations,
			popup: appearance.popupAnimations,
			reduced: reducedMotion.value
		});
		for (const [name, value] of Object.entries(variables)) root.style.setProperty(name, value);
		for (const motion of [
			"click",
			"hover",
			"fade",
			"popup"
		]) root.dataset[motion + "Animations"] = String(appearance[motion + "Animations"]);
		try {
			if (!configurationPreview.value) saveAppearance();
		} catch {}
	});
}
//#endregion
//#region src/i18n.js
var catalogs = /* #__PURE__ */ Object.assign({
	"./locales/en.json": en_default,
	"./locales/ru.json": ru_default
});
function t(source, values = {}) {
	const translated = catalogs[`./locales/${appearance.language}.json`]?.[source];
	return (typeof translated === "string" && translated.trim() ? translated : source).replace(/\{(\w+)\}/g, (placeholder, name) => values[name] ?? placeholder);
}
//#endregion
//#region src/controls/controlAppearance.js
function buttonVariables(options) {
	const result = {};
	for (const [name, flags] of Object.entries({
		idle: {},
		hover: { hovered: true },
		focus: { focused: true },
		pressed: { pressed: true },
		disabled: { enabled: false }
	})) {
		const paint = buttonVisual({
			...options,
			...flags
		});
		let background = paint.background === "transparent" ? "transparent" : `var(${cssRoles[paint.background]})`;
		if (paint.pressedMix) background = `color-mix(in srgb, ${background} 82%, var(--page))`;
		result[`--button-${name}-background`] = background;
		result[`--button-${name}-color`] = `var(${cssRoles[paint.content]})`;
		result[`--button-${name}-border`] = `var(${cssRoles[paint.border]})`;
		result[`--button-${name}-border-width`] = paint.borderWidth + "px";
	}
	return result;
}
//#endregion
//#region src/controls/AppIcon.vue
var _hoisted_1$1 = ["data-icon"];
var _hoisted_2$1 = { class: "icon-glyph" };
var _sfc_main$1 = {
	__name: "AppIcon",
	props: { name: String },
	setup(__props) {
		const props = __props;
		const icon = computed(() => resolveIcon(props.name, appearance.iconSet) || (props.name ? resolveIcon("fontawesome-solid:exclamation-triangle", appearance.iconSet) : null));
		return (_ctx, _cache) => {
			return icon.value ? (openBlock(), createElementBlock("span", {
				key: 0,
				class: normalizeClass(["app-icon", "icon-" + icon.value[0]]),
				"data-icon": __props.name,
				"aria-hidden": "true"
			}, [createBaseVNode("span", _hoisted_2$1, toDisplayString(icon.value[1]), 1)], 10, _hoisted_1$1)) : createCommentVNode("", true);
		};
	}
};
//#endregion
//#region src/controls/ripple.js
function ripple(event) {
	const button = event.currentTarget;
	if (button.disabled || event.button !== 0) return;
	const style = getComputedStyle(button);
	const fast = parseFloat(style.getPropertyValue("--motion-click")) || 0;
	const extended = parseFloat(style.getPropertyValue("--motion-click-extended")) || 0;
	if (!extended) return;
	button.querySelectorAll(":scope > .control-ripple-clip").forEach((node) => node.remove());
	const inset = parseFloat(style.getPropertyValue("--ripple-inset")) || 0;
	const bounds = button.getBoundingClientRect(), diameter = Math.max(bounds.width - inset * 2, bounds.height - inset * 2) * 2.2;
	const circle = document.createElement("span");
	circle.className = "control-ripple";
	circle.setAttribute("aria-hidden", "true");
	Object.assign(circle.style, {
		width: diameter + "px",
		height: diameter + "px",
		left: event.clientX - bounds.left - inset - diameter / 2 + "px",
		top: event.clientY - bounds.top - inset - diameter / 2 + "px"
	});
	const clip = document.createElement("span");
	clip.className = "control-ripple-clip";
	clip.setAttribute("aria-hidden", "true");
	clip.style.inset = inset + "px";
	clip.append(circle);
	button.append(clip);
	circle.animate([{ transform: "scale(.05)" }, { transform: "scale(1)" }], {
		duration: extended + fast,
		easing: "cubic-bezier(.215,.61,.355,1)",
		fill: "forwards"
	});
	circle.animate([{ opacity: .42 }, { opacity: 0 }], {
		duration: extended,
		delay: 24,
		easing: "ease-out",
		fill: "forwards"
	}).finished.then(() => clip.remove(), () => clip.remove());
}
//#endregion
//#region src/controls/activation.js
function capturePress(event) {
	const control = event.currentTarget;
	if (event.button !== 0 || event.pointerType === "touch" || control.disabled || control.getAttribute("aria-disabled") === "true") return;
	control.setPointerCapture(event.pointerId);
	const listeners = new AbortController(), x = event.clientX, y = event.clientY;
	control.addEventListener("pointermove", (move) => {
		if (move.pointerId === event.pointerId && Math.hypot(move.clientX - x, move.clientY - y) >= 10) {
			if (control.hasPointerCapture(event.pointerId)) control.releasePointerCapture(event.pointerId);
			listeners.abort();
		}
	}, { signal: listeners.signal });
	for (const name of [
		"pointerup",
		"pointercancel",
		"lostpointercapture"
	]) control.addEventListener(name, (end) => {
		if (end.pointerId === event.pointerId) listeners.abort();
	}, { signal: listeners.signal });
}
//#endregion
//#region src/controls/tooltip.js
var active;
var sequence = 0;
var tooltipDirective = {
	mounted(element, binding) {
		let text = binding.value, timer, timeout, popup, describedBy;
		function close(event) {
			if (popup && event?.type === "keydown" && event.key === "Escape") {
				event.preventDefault();
				event.stopPropagation();
			}
			clearTimeout(timer);
			clearTimeout(timeout);
			if (popup) {
				const dismissed = popup;
				dismissed.hidePopover();
				setTimeout(() => dismissed.remove(), parseFloat(getComputedStyle(dismissed).transitionDuration) * 1e3 + 10);
				popup = null;
				if (describedBy === null) element.removeAttribute("aria-describedby");
				else element.setAttribute("aria-describedby", describedBy);
			}
			for (const name of [
				"scroll",
				"resize",
				"pointerdown",
				"keydown",
				"close"
			]) window.removeEventListener(name, close, true);
			if (active === close) active = null;
		}
		function start(event) {
			if (!text || element.disabled || element.getAttribute("aria-disabled") === "true" || event.pointerType === "touch") return;
			active?.();
			active = close;
			for (const name of [
				"scroll",
				"resize",
				"pointerdown",
				"keydown",
				"close"
			]) window.addEventListener(name, close, true);
			timer = setTimeout(() => {
				if (!element.isConnected || element.disabled || element.getAttribute("aria-disabled") === "true" || !element.getClientRects().length) {
					close();
					return;
				}
				popup = document.createElement("div");
				popup.className = "app-tooltip";
				popup.popover = "manual";
				popup.id = "app-tooltip-" + ++sequence;
				popup.role = "tooltip";
				popup.textContent = text;
				(element.closest("dialog") || document.body).append(popup);
				popup.showPopover();
				const anchor = element.getBoundingClientRect(), box = popup.getBoundingClientRect(), margin = controls.tooltip.margin;
				popup.style.left = Math.max(margin, Math.min(innerWidth - box.width - margin, anchor.left + (anchor.width - box.width) / 2)) + "px";
				popup.style.top = Math.max(margin, Math.min(innerHeight - box.height - margin, anchor.bottom + box.height + 2 * margin > innerHeight ? anchor.top - box.height - margin : anchor.bottom + margin)) + "px";
				describedBy = element.getAttribute("aria-describedby");
				element.setAttribute("aria-describedby", [describedBy, popup.id].filter(Boolean).join(" "));
				timeout = setTimeout(close, controls.tooltip.timeout);
			}, controls.tooltip.delay);
		}
		element.addEventListener("pointerenter", start);
		element.addEventListener("focusin", start);
		element.addEventListener("pointerleave", close);
		element.addEventListener("focusout", close);
		element.tooltipUpdate = (value) => {
			text = value;
			close();
		};
		element.tooltipCleanup = () => {
			close();
			element.removeEventListener("pointerenter", start);
			element.removeEventListener("focusin", start);
			element.removeEventListener("pointerleave", close);
			element.removeEventListener("focusout", close);
		};
	},
	updated(element, binding) {
		if (binding.value !== binding.oldValue) element.tooltipUpdate?.(binding.value);
	},
	beforeUnmount(element) {
		element.tooltipCleanup?.();
		delete element.tooltipUpdate;
		delete element.tooltipCleanup;
	}
};
//#endregion
//#region src/controls/AppButton.vue
var _hoisted_1 = { key: 0 };
var _hoisted_2 = {
	key: 1,
	class: "app-button-badge",
	"aria-hidden": "true"
};
var _sfc_main = {
	__name: "AppButton",
	props: {
		label: {
			type: String,
			default: ""
		},
		translateLabel: {
			type: Boolean,
			default: true
		},
		tooltip: String,
		icon: String,
		iconOnly: Boolean,
		compact: Boolean,
		highlighted: Boolean,
		filledAction: Boolean,
		destructive: Boolean,
		tonal: Boolean,
		segmented: Boolean,
		checked: Boolean,
		badgeCount: {
			type: Number,
			default: 0
		},
		badgeColor: String,
		showZeroBadge: Boolean,
		type: {
			type: String,
			default: "button"
		},
		href: String
	},
	setup(__props) {
		const props = __props;
		const paint = computed(() => buttonVariables(props));
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createBlock(resolveDynamicComponent(__props.href ? "a" : "button"), {
				class: normalizeClass(["app-button", {
					"icon-button": __props.iconOnly || __props.compact,
					"compact-button": __props.compact,
					primary: __props.highlighted,
					"filled-action": __props.filledAction,
					danger: __props.destructive,
					tonal: __props.tonal
				}]),
				style: normalizeStyle([paint.value, __props.badgeColor ? { "--badge-color": __props.badgeColor } : null]),
				href: __props.href,
				type: __props.href ? void 0 : __props.type,
				"aria-label": __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : void 0,
				onPointerdown: _cache[0] || (_cache[0] = ($event) => {
					unref(capturePress)($event);
					unref(ripple)($event);
				})
			}, {
				default: withCtx(() => [
					__props.icon ? (openBlock(), createBlock(_sfc_main$1, {
						key: 0,
						name: __props.icon
					}, null, 8, ["name"])) : createCommentVNode("", true),
					renderSlot(_ctx.$slots, "default", {}, () => [!__props.iconOnly && !__props.compact ? (openBlock(), createElementBlock("span", _hoisted_1, toDisplayString(__props.translateLabel ? unref(t)(__props.label) : __props.label), 1)) : createCommentVNode("", true)]),
					__props.badgeCount > 0 || __props.showZeroBadge ? (openBlock(), createElementBlock("span", _hoisted_2, toDisplayString(__props.badgeCount > 99 ? "99+" : __props.badgeCount), 1)) : createCommentVNode("", true)
				]),
				_: 3
			}, 40, [
				"style",
				"href",
				"type",
				"class",
				"aria-label"
			])), [[unref(tooltipDirective), __props.tooltip ? unref(t)(__props.tooltip) : (__props.iconOnly || __props.compact) && __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : ""]]);
		};
	}
};
//#endregion
export { normalizePreferences as A, layout as C, spacing as D, readableText$1 as E, accentPresets as F, iconSets as I, themes as L, savePreferencePage as M, normalizeColumns as N, textStyles as O, taskColumns as P, BusyIndicator_default as R, fontMetricHeight as S, metrics as T, controls as _, _sfc_main$1 as a, fontFamily as b, colorModes as c, initializeAppearance as d, languages as f, blend as g, saveAppearance as h, ripple as i, preferences as j, configurationPreview as k, effectiveColorMode as l, readableText as m, tooltipDirective as n, t as o, projectPalette as p, capturePress as r, appearance as s, _sfc_main as t, frameColors as u, cssColor as v, lineHeights as w, fontLineHeight as x, cssRoles as y, _plugin_vue_export_helper_default as z };

//# sourceMappingURL=AppButton.js.map
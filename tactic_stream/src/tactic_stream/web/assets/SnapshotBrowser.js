import { E as nextTick, G as withCtx, H as watch, L as resolveDynamicComponent, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { D as t, i as mobile, o as _sfc_main$1, tt as _plugin_vue_export_helper_default, u as _sfc_main$2 } from "./index.js";
import { P as resultItems, a as copyImage, dt as notify, o as copyText } from "./CodeBlock.js";
import { t as RecordForm_default } from "./RecordForm.js";
import { t as _sfc_main$3 } from "./AppSlider.js";
import { t as _sfc_main$4 } from "./AppMenu.js";
import { t as ItemPreview_default } from "./ItemPreview.js";
import { E as _sfc_main$5, R as _sfc_main$6, V as ObjectAction_default, q as FilePreview_default } from "./App.js";
//#region src/features/objects/SnapshotBrowser.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "snapshot-toolbar" };
var _hoisted_3 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_4 = {
	key: 1,
	role: "status",
	class: "snapshot-status"
};
var _hoisted_5 = ["aria-label"];
var _hoisted_6 = {
	key: 1,
	class: "snapshot-counter"
};
var _hoisted_7 = { class: "snapshot-file-head" };
var _hoisted_8 = {
	key: 0,
	class: "file-count"
};
var _hoisted_9 = {
	key: 1,
	class: "file-size"
};
var _hoisted_10 = {
	key: 2,
	class: "file-path"
};
var _hoisted_11 = {
	key: 3,
	class: "file-repo"
};
var _hoisted_12 = {
	key: 4,
	class: "file-base"
};
var _hoisted_13 = ["aria-label"];
var _hoisted_14 = {
	key: 0,
	class: "file-size"
};
var _hoisted_15 = {
	key: 2,
	class: "file-repo"
};
var _hoisted_16 = {
	key: 3,
	class: "file-base"
};
var _hoisted_17 = {
	key: 0,
	class: "snapshot-status"
};
var _hoisted_18 = {
	key: 0,
	class: "snapshot-phone-actions"
};
var _hoisted_19 = [
	"aria-orientation",
	"aria-label",
	"aria-valuenow"
];
var SnapshotBrowser_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "SnapshotBrowser",
	props: {
		ticket: String,
		project: String,
		target: Object,
		active: Boolean
	},
	emits: ["session-expired", "changed"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const options = ref({
			contentMode: "both",
			imageMode: "fit",
			orientation: "horizontal",
			showAll: false,
			showMore: false,
			splitterRatio: .52
		}), error = ref(""), loading = ref(false), loaded = ref(false);
		try {
			const saved = JSON.parse(localStorage.getItem("tactic_stream.snapshot-browser") || "{}");
			for (const [name, values] of Object.entries({
				contentMode: [
					"both",
					"preview",
					"files"
				],
				imageMode: ["fit", "fill"],
				orientation: ["horizontal", "vertical"]
			})) if (values.includes(saved[name])) options.value[name] = saved[name];
			for (const name of ["showAll", "showMore"]) if (typeof saved[name] === "boolean") options.value[name] = saved[name];
			if (Number.isFinite(saved.splitterRatio)) options.value.splitterRatio = Math.max(.22, Math.min(.78, saved.splitterRatio));
		} catch {}
		const rows = ref([]), previews = ref([]), snapshots = ref([]), owner = ref(null), hasNext = ref(false);
		const index = ref(0), selectedFile = ref(""), contextFile = ref(null), fileMenu = ref(null), preview = ref(null), form = ref(null), action = ref(null);
		const area = ref(null), filePanel = ref(null), fileWidth = ref(0), extent = ref(0), moving = ref(false), draftRatio = ref(.52);
		const image = ref(null), quality = ref(""), outgoing = ref(""), incomingLayer = ref(null), outgoingLayer = ref(null);
		let request = 0, observer, animations = [], transition = 0;
		const showingPreview = computed(() => options.value.contentMode !== "files" && (!mobile.value || previews.value.some((row) => row.url)));
		const showingFiles = computed(() => mobile.value && !showingPreview.value || options.value.contentMode !== "preview");
		const vertical = computed(() => !mobile.value && options.value.orientation === "vertical");
		const current = computed(() => previews.value[index.value]);
		const phoneFile = computed(() => rows.value.find((row) => row.token && row.token === selectedFile.value));
		const visibleRows = computed(() => rows.value.filter((row) => options.value.showAll || ["file", "more"].includes(row.rowType) && !row.previewType));
		const count = computed(() => visibleRows.value.filter((row) => row.rowType === "file").length);
		const ratio = computed(() => clamp(moving.value ? draftRatio.value : options.value.splitterRatio));
		const imageMode = computed({
			get: () => options.value.imageMode,
			set: (value) => setOption("imageMode", value)
		});
		const imageIndex = computed({
			get: () => index.value,
			set: (value) => navigate(value)
		});
		const moreSize = computed(() => options.value.showMore && fileWidth.value >= 340);
		const morePath = computed(() => options.value.showMore && fileWidth.value >= 650);
		const moreRepo = computed(() => options.value.showMore && fileWidth.value >= 820);
		const moreBase = computed(() => options.value.showMore && fileWidth.value >= 940);
		const canCopyImage = computed(() => !!navigator.clipboard?.write && !!globalThis.ClipboardItem);
		function setOption(name, value) {
			const next = {
				...options.value,
				[name]: value
			};
			try {
				localStorage.setItem("tactic_stream.snapshot-browser", JSON.stringify(next));
				options.value = next;
			} catch {
				error.value = t("Browser settings could not be saved.");
			}
		}
		function clamp(value) {
			const primary = vertical.value ? 120 : 90, secondary = vertical.value ? 180 : 120;
			if (extent.value <= 1) return Math.max(.22, Math.min(.78, value));
			const lower = Math.max(.22, (primary + 5) / extent.value), upper = Math.min(.78, 1 - (secondary + 5) / extent.value);
			return lower > upper ? primary / (primary + secondary) : Math.max(lower, Math.min(upper, value));
		}
		function measure() {
			const box = area.value?.getBoundingClientRect();
			extent.value = (vertical.value ? box?.width : box?.height) || 0;
			fileWidth.value = filePanel.value?.clientWidth || 0;
		}
		function drag(event) {
			if (event.button !== 0) return;
			event.preventDefault();
			event.currentTarget.setPointerCapture(event.pointerId);
			moving.value = true;
			draftRatio.value = ratio.value;
		}
		function resize(event) {
			if (!moving.value) return;
			const box = area.value.getBoundingClientRect();
			draftRatio.value = clamp(vertical.value ? (event.clientX - box.left) / box.width : (event.clientY - box.top) / box.height);
		}
		function endDrag(event) {
			if (!moving.value) return;
			if (event.type !== "pointercancel") setOption("splitterRatio", clamp(draftRatio.value));
			moving.value = false;
		}
		function splitterKey(event) {
			const step = ["ArrowLeft", "ArrowUp"].includes(event.key) ? -.02 : ["ArrowRight", "ArrowDown"].includes(event.key) ? .02 : 0;
			if (!step) return;
			event.preventDefault();
			setOption("splitterRatio", clamp(ratio.value + step));
		}
		function reset() {
			settle();
			request++;
			rows.value = [];
			previews.value = [];
			snapshots.value = [];
			owner.value = null;
			loading.value = false;
			loaded.value = false;
			hasNext.value = false;
			selectedFile.value = "";
			index.value = 0;
			contextFile.value = null;
			fileMenu.value?.close();
			error.value = "";
			quality.value = "";
			image.value = null;
		}
		async function load(append = false) {
			if (!props.active || !props.ticket || !props.target?.key || props.target.project !== props.project) return;
			const id = ++request, key = props.target.key;
			loading.value = true;
			error.value = "";
			contextFile.value = null;
			fileMenu.value?.close();
			try {
				const value = await resultItems(props.ticket, props.project, key.split("?")[0], [key], {
					branch: {
						kind: "snapshot_browser",
						process: props.target.process || ""
					},
					offset: append ? snapshots.value.length : 0,
					limit: 50
				});
				if (id !== request) return;
				rows.value = append ? [...rows.value, ...value.rows] : value.rows;
				previews.value = append ? [...previews.value, ...value.previews] : value.previews;
				snapshots.value = append ? [...snapshots.value, ...value.snapshots] : value.snapshots;
				owner.value = value.owner;
				hasNext.value = value.has_next;
				loaded.value = true;
				if (!append) {
					settle();
					selectedFile.value = "";
					index.value = 0;
					quality.value = "";
					image.value = null;
				}
			} catch (reason) {
				if (id === request) {
					error.value = reason.message;
					if (reason.code === "authentication_failed") emit("session-expired");
				}
			} finally {
				if (id === request) loading.value = false;
			}
		}
		async function loadMembers(row) {
			if (loading.value) return;
			const id = request;
			loading.value = true;
			error.value = "";
			try {
				const result = await resultItems(props.ticket, props.project, "sthpw/file", [row.record.__search_key__], {
					branch: { kind: "snapshot_members" },
					offset: row.memberOffset,
					limit: 50
				});
				if (id !== request) return;
				const position = rows.value.indexOf(row);
				if (position >= 0) rows.value.splice(position, 1, ...result.rows);
			} catch (reason) {
				if (id === request) {
					error.value = reason.message;
					if (reason.code === "authentication_failed") emit("session-expired");
				}
			} finally {
				if (id === request) loading.value = false;
			}
		}
		function settle() {
			transition++;
			for (const animation of animations) animation.cancel();
			animations = [];
			outgoing.value = "";
		}
		async function navigate(value, animate = true) {
			const next = Math.max(0, Math.min(previews.value.length - 1, value)), previous = quality.value || current.value?.url;
			if (next === index.value) return;
			const direction = next >= index.value ? 1 : -1, id = request;
			settle();
			const generation = transition;
			index.value = next;
			quality.value = "";
			image.value = null;
			if (!animate || !previous || previous === current.value?.url || !showingPreview.value) return;
			const style = getComputedStyle(document.documentElement), duration = parseFloat(style.getPropertyValue("--motion-extended")) || 0;
			if (!duration || document.documentElement.dataset.fadeAnimations === "false") return;
			outgoing.value = previous;
			await nextTick();
			if (id !== request || generation !== transition || !incomingLayer.value || !outgoingLayer.value) return;
			const distance = Math.max(36, incomingLayer.value.clientWidth * .18), slow = parseFloat(style.getPropertyValue("--motion-slow")) || duration;
			animations = [
				incomingLayer.value.animate([{ transform: `translateX(${direction * distance}px)` }, { transform: "translateX(0)" }], {
					duration,
					easing: "cubic-bezier(.19,1,.22,1)"
				}),
				incomingLayer.value.animate([{ opacity: 0 }, { opacity: 1 }], {
					duration: slow,
					easing: "cubic-bezier(.215,.61,.355,1)"
				}),
				outgoingLayer.value.animate([{ transform: "translateX(0)" }, { transform: `translateX(${-direction * distance}px)` }], {
					duration,
					easing: "cubic-bezier(.19,1,.22,1)"
				}),
				outgoingLayer.value.animate([{ opacity: 1 }, { opacity: 0 }], {
					duration: slow,
					easing: "cubic-bezier(.215,.61,.355,1)",
					fill: "forwards"
				})
			];
			const batch = animations;
			try {
				await Promise.all(batch.map((animation) => animation.finished));
			} catch {}
			if (animations === batch) settle();
		}
		function needQuality() {
			const original = current.value?.qualityUrl, element = image.value;
			if (!element || !original || original === element.getAttribute("src") || quality.value || !element.naturalWidth) return;
			const box = element.getBoundingClientRect();
			if ((options.value.imageMode === "fill" ? Math.max(box.width / element.naturalWidth, box.height / element.naturalHeight) : Math.min(box.width / element.naturalWidth, box.height / element.naturalHeight)) * devicePixelRatio > 1.2) quality.value = original;
		}
		async function openMenu(file, event, editing = false) {
			if (!file || !file.token || file.rowType === "more") return;
			contextFile.value = {
				...file,
				editing
			};
			await nextTick();
			fileMenu.value.openAt(event);
		}
		async function blob(file) {
			if (!file.href) throw new Error(t("No web path is configured for this file."));
			const response = await fetch(file.href);
			if (!response.ok) throw new Error(t("File Offline"));
			return response.blob();
		}
		function openFile(file) {
			if (file) preview.value.open(file.record, {
				files: [{
					...file,
					filename: file.filename,
					type: file.fileType
				}],
				context: snapshots.value.find((row) => row.__search_key__ === file.snapshotKey)?.context,
				loadFile: () => blob(file)
			});
		}
		async function fileAction(command) {
			const file = contextFile.value, id = request;
			if (!file || !rows.value.some((row) => row.token === file.token)) return;
			fileMenu.value.close();
			try {
				if (command === "open") openFile(file);
				else if (command === "copy_path") {
					await copyText(file.fullPath);
					notify("info", "Path copied");
				} else if (command === "copy_web_path") {
					if (!file.href) throw new Error(t("No web path is configured for this file."));
					await copyText(new URL(file.href, location.href).href);
					notify("info", "Web link copied");
				} else if (command === "copy_image") {
					const value = await blob(file);
					if (id === request) {
						await copyImage(value);
						notify("info", "Image copied");
					}
				} else if (command === "edit") form.value.open(file.record.__search_key__);
				else if (command === "delete") action.value.open(file.record, "delete");
			} catch (reason) {
				if (id === request) error.value = reason.message;
			}
		}
		function changed() {
			load();
			emit("changed");
		}
		function fileIcon(row) {
			if (row.rowType === "snapshot") return "snapshot";
			if (row.rowType === "type") return "folder";
			if ([
				"image",
				"icon",
				"web"
			].includes(row.fileType)) return "image";
			if ([
				"playblast",
				"movie",
				"video"
			].includes(row.fileType)) return "movie";
			if (row.baseType.includes("sequence")) return "sequence";
			if (/\.(zip|rar|7z|tar|gz)$/i.test(row.filename)) return "archive";
			return "file";
		}
		function size(value) {
			if (!Number.isFinite(Number(value)) || value === "") return "";
			const units = [
				"B",
				"KB",
				"MB",
				"GB",
				"TB"
			];
			let number = Number(value), level = 0;
			while (number >= 1024 && level < units.length - 1) {
				number /= 1024;
				level++;
			}
			return (level ? number.toFixed(1) : number) + " " + units[level];
		}
		watch(() => [
			props.ticket,
			props.project,
			props.target
		], () => {
			reset();
			load();
		}, { immediate: true });
		watch(() => props.active, (value) => {
			if (value && !loaded.value) load();
		});
		watch(() => [options.value.orientation, options.value.contentMode], () => {
			settle();
			nextTick(measure);
		});
		watch(() => options.value.imageMode, () => nextTick(needQuality));
		watch([area, filePanel], (elements) => {
			observer?.disconnect();
			observer = new ResizeObserver(() => {
				measure();
				needQuality();
			});
			for (const element of elements) if (element) observer.observe(element);
		}, { flush: "post" });
		onBeforeUnmount(() => {
			request++;
			settle();
			observer?.disconnect();
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock(Fragment, null, [
				(openBlock(), createBlock(Teleport, {
					defer: "",
					to: "#dock-snapshot"
				}, [createBaseVNode("section", {
					class: "snapshot-browser",
					"aria-label": unref(t)("Snapshot Browser"),
					"aria-busy": loading.value
				}, [
					createBaseVNode("header", _hoisted_2, [
						createVNode(_sfc_main$4, {
							label: "Snapshot Browser options",
							width: 300,
							overlay: ""
						}, {
							default: withCtx(() => [
								(openBlock(), createElementBlock(Fragment, null, renderList([
									{
										value: "both",
										label: "Preview and Files",
										icon: "grid-view"
									},
									{
										value: "preview",
										label: "Preview Only",
										icon: "image"
									},
									{
										value: "files",
										label: "Files Only",
										icon: "view-list"
									}
								], (option) => {
									return createVNode(_sfc_main$1, {
										key: option.value,
										role: "menuitemradio",
										"aria-checked": options.value.contentMode === option.value,
										label: option.label,
										icon: option.icon,
										onClick: ($event) => setOption("contentMode", option.value)
									}, null, 8, [
										"aria-checked",
										"label",
										"icon",
										"onClick"
									]);
								}), 64)),
								_cache[28] || (_cache[28] = createBaseVNode("hr", null, null, -1)),
								createVNode(_sfc_main$1, {
									role: "menuitemcheckbox",
									"aria-checked": options.value.showAll,
									label: "Show All Files",
									icon: "visibility",
									onClick: _cache[0] || (_cache[0] = ($event) => setOption("showAll", !options.value.showAll))
								}, null, 8, ["aria-checked"]),
								createVNode(_sfc_main$1, {
									role: "menuitemcheckbox",
									"aria-checked": options.value.showMore,
									label: "Show More Info",
									icon: "info",
									onClick: _cache[1] || (_cache[1] = ($event) => setOption("showMore", !options.value.showMore))
								}, null, 8, ["aria-checked"]),
								_cache[29] || (_cache[29] = createBaseVNode("hr", null, null, -1)),
								!unref(mobile) ? (openBlock(), createElementBlock(Fragment, { key: 0 }, renderList([{
									value: "horizontal",
									label: "Horizontal orientation",
									icon: "view_agenda"
								}, {
									value: "vertical",
									label: "Vertical orientation",
									icon: "view_column"
								}], (option) => {
									return createVNode(_sfc_main$1, {
										key: option.value,
										role: "menuitemradio",
										"aria-checked": options.value.orientation === option.value,
										label: option.label,
										icon: option.icon,
										onClick: ($event) => setOption("orientation", option.value)
									}, null, 8, [
										"aria-checked",
										"label",
										"icon",
										"onClick"
									]);
								}), 64)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, renderList(["fit", "fill"], (mode) => {
									return createVNode(_sfc_main$1, {
										key: mode,
										role: "menuitemradio",
										"aria-checked": imageMode.value === mode,
										label: mode === "fit" ? "Fit" : "Fill",
										onClick: ($event) => imageMode.value = mode
									}, null, 8, [
										"aria-checked",
										"label",
										"onClick"
									]);
								}), 64))
							]),
							_: 1
						}),
						showingPreview.value && !unref(mobile) ? (openBlock(), createBlock(_sfc_main$5, {
							key: 0,
							modelValue: imageMode.value,
							"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => imageMode.value = $event),
							label: "Preview image mode",
							options: [{
								value: "fit",
								label: "Fit"
							}, {
								value: "fill",
								label: "Fill"
							}]
						}, null, 8, ["modelValue"])) : createCommentVNode("", true),
						createVNode(_sfc_main$1, {
							label: "Refresh snapshots",
							icon: "refresh",
							"icon-only": "",
							disabled: loading.value || !__props.target?.key,
							onClick: _cache[3] || (_cache[3] = ($event) => load())
						}, null, 8, ["disabled"])
					]),
					error.value ? (openBlock(), createElementBlock("p", _hoisted_3, [createTextVNode(toDisplayString(unref(t)(error.value)) + " ", 1), createVNode(_sfc_main$1, {
						label: "Retry",
						disabled: loading.value,
						onClick: _cache[4] || (_cache[4] = ($event) => load())
					}, null, 8, ["disabled"])])) : createCommentVNode("", true),
					loading.value && !rows.value.length ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString(unref(t)("Loading snapshots…")), 1)) : createCommentVNode("", true),
					createBaseVNode("div", {
						ref_key: "area",
						ref: area,
						class: normalizeClass(["snapshot-area", {
							vertical: vertical.value,
							combined: showingPreview.value && showingFiles.value,
							"preview-only": !showingFiles.value
						}]),
						style: normalizeStyle({ "--snapshot-ratio": ratio.value * 100 + "%" })
					}, [
						showingPreview.value ? (openBlock(), createElementBlock("div", {
							key: 0,
							class: "snapshot-preview",
							tabindex: "0",
							"aria-label": unref(t)("Snapshot preview"),
							onKeydown: [_cache[13] || (_cache[13] = withKeys(withModifiers(($event) => navigate(index.value - 1), ["prevent"]), ["left"])), _cache[14] || (_cache[14] = withKeys(withModifiers(($event) => navigate(index.value + 1), ["prevent"]), ["right"]))],
							onWheel: _cache[15] || (_cache[15] = withModifiers(($event) => navigate(index.value + ($event.deltaY > 0 ? 1 : -1)), ["prevent"])),
							onContextmenu: _cache[16] || (_cache[16] = withModifiers(($event) => openMenu(current.value?.file, $event), ["prevent"])),
							onDblclick: _cache[17] || (_cache[17] = ($event) => openFile(current.value?.file))
						}, [
							outgoing.value ? (openBlock(), createElementBlock("div", {
								key: 0,
								ref_key: "outgoingLayer",
								ref: outgoingLayer,
								class: "snapshot-preview-layer",
								"aria-hidden": "true"
							}, [createVNode(ItemPreview_default, {
								class: "snapshot-image",
								source: outgoing.value,
								"fallback-icon": "movie",
								accent: "var(--surface-high)",
								"preview-size": 58,
								"fill-mode": options.value.imageMode === "fill" ? "cover" : "contain"
							}, null, 8, ["source", "fill-mode"])], 512)) : createCommentVNode("", true),
							createBaseVNode("div", {
								ref_key: "incomingLayer",
								ref: incomingLayer,
								class: "snapshot-preview-layer"
							}, [createVNode(ItemPreview_default, {
								class: "snapshot-image",
								source: current.value ? quality.value || current.value.url : "",
								"fallback-icon": "movie",
								accent: "var(--surface-high)",
								"preview-size": 58,
								"fill-mode": options.value.imageMode === "fill" ? "cover" : "contain",
								onReady: _cache[5] || (_cache[5] = ($event) => {
									image.value = $event;
									needQuality();
								})
							}, null, 8, ["source", "fill-mode"])], 512),
							current.value ? (openBlock(), createElementBlock("span", _hoisted_6, toDisplayString(index.value + 1) + " / " + toDisplayString(previews.value.length), 1)) : createCommentVNode("", true),
							current.value ? (openBlock(), createBlock(_sfc_main$1, {
								key: 2,
								class: "snapshot-preview-actions",
								label: "Preview actions",
								icon: "more",
								"icon-only": "",
								onClick: _cache[6] || (_cache[6] = withModifiers(($event) => openMenu(current.value.file, $event), ["stop"]))
							})) : createCommentVNode("", true),
							previews.value.length > 1 ? (openBlock(), createBlock(_sfc_main$1, {
								key: 3,
								class: "snapshot-previous",
								label: "Previous preview",
								icon: "chevron-left",
								"icon-only": "",
								disabled: index.value === 0,
								onClick: _cache[7] || (_cache[7] = withModifiers(($event) => navigate(index.value - 1), ["stop"]))
							}, null, 8, ["disabled"])) : createCommentVNode("", true),
							previews.value.length > 1 ? (openBlock(), createBlock(_sfc_main$1, {
								key: 4,
								class: "snapshot-next",
								label: "Next preview",
								icon: "chevron-right",
								"icon-only": "",
								disabled: index.value === previews.value.length - 1,
								onClick: _cache[8] || (_cache[8] = withModifiers(($event) => navigate(index.value + 1), ["stop"]))
							}, null, 8, ["disabled"])) : createCommentVNode("", true),
							current.value ? (openBlock(), createBlock(_sfc_main$6, {
								key: 5,
								class: "snapshot-preview-title",
								text: current.value.title
							}, null, 8, ["text"])) : createCommentVNode("", true),
							previews.value.length > 1 ? (openBlock(), createBlock(_sfc_main$3, {
								key: 6,
								modelValue: imageIndex.value,
								"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => imageIndex.value = $event),
								class: "snapshot-preview-slider",
								label: "Preview number",
								min: 0,
								max: previews.value.length - 1,
								step: 1,
								onDblclick: _cache[10] || (_cache[10] = withModifiers(() => {}, ["stop"])),
								onWheel: _cache[11] || (_cache[11] = withModifiers(() => {}, ["stop"])),
								onKeydown: _cache[12] || (_cache[12] = withModifiers(() => {}, ["stop"]))
							}, null, 8, ["modelValue", "max"])) : createCommentVNode("", true)
						], 40, _hoisted_5)) : createCommentVNode("", true),
						showingFiles.value ? (openBlock(), createElementBlock("div", {
							key: 1,
							ref_key: "filePanel",
							ref: filePanel,
							class: normalizeClass(["snapshot-files", {
								"more-size": moreSize.value,
								"more-path": morePath.value,
								"more-repo": moreRepo.value,
								"more-base": moreBase.value
							}])
						}, [
							createBaseVNode("div", _hoisted_7, [
								_cache[30] || (_cache[30] = createBaseVNode("i", null, null, -1)),
								createBaseVNode("strong", null, toDisplayString(unref(t)(options.value.showMore ? "Files" : options.value.showAll ? "All snapshot files" : "Published files")), 1),
								fileWidth.value >= 240 ? (openBlock(), createElementBlock("span", _hoisted_8, toDisplayString(unref(t)(count.value === 1 ? "{count} file" : "{count} files", { count: count.value })), 1)) : createCommentVNode("", true),
								moreSize.value ? (openBlock(), createElementBlock("span", _hoisted_9, toDisplayString(unref(t)("Size")), 1)) : createCommentVNode("", true),
								morePath.value ? (openBlock(), createElementBlock("span", _hoisted_10, toDisplayString(unref(t)("Path")), 1)) : createCommentVNode("", true),
								moreRepo.value ? (openBlock(), createElementBlock("span", _hoisted_11, toDisplayString(unref(t)("Repo")), 1)) : createCommentVNode("", true),
								moreBase.value ? (openBlock(), createElementBlock("span", _hoisted_12, toDisplayString(unref(t)("Base Type")), 1)) : createCommentVNode("", true)
							]),
							createBaseVNode("div", {
								class: "snapshot-file-list",
								role: "listbox",
								"aria-label": unref(t)("Snapshot files")
							}, [
								(openBlock(true), createElementBlock(Fragment, null, renderList(visibleRows.value, (row, position) => {
									return openBlock(), createBlock(resolveDynamicComponent(["file", "more"].includes(row.rowType) ? "button" : "div"), {
										key: row.snapshotKey + ":" + row.token + ":" + row.title + ":" + row.depth,
										class: normalizeClass(["snapshot-file-row", {
											selected: row.token && selectedFile.value === row.token,
											header: row.rowType === "snapshot",
											type: row.rowType === "type",
											alternate: position % 2
										}]),
										style: normalizeStyle({ "--file-indent": options.value.showAll ? row.depth * 14 + "px" : "0px" }),
										type: row.rowType === "file" ? "button" : void 0,
										role: row.rowType === "file" ? "option" : "presentation",
										"aria-selected": row.rowType === "file" ? selectedFile.value === row.token : void 0,
										onClick: ($event) => row.rowType === "more" ? loadMembers(row) : row.token && (selectedFile.value = row.token),
										onDblclick: ($event) => row.rowType === "file" && row.token && openFile(row),
										onContextmenu: withModifiers(($event) => openMenu(row, $event, true), ["prevent"])
									}, {
										default: withCtx(() => [
											createVNode(_sfc_main$2, {
												name: fileIcon(row),
												style: normalizeStyle({ color: row.rowType === "file" && !row.exists ? "var(--muted)" : row.rowType === "type" ? "var(--yellow)" : "var(--primary)" })
											}, null, 8, ["name", "style"]),
											createVNode(_sfc_main$6, { text: row.rowType === "more" ? unref(t)(row.title) : row.title }, null, 8, ["text"]),
											moreSize.value ? (openBlock(), createElementBlock("span", _hoisted_14, toDisplayString(row.rowType === "file" ? size(row.size) : ""), 1)) : createCommentVNode("", true),
											morePath.value ? (openBlock(), createBlock(_sfc_main$6, {
												key: 1,
												class: "file-path",
												text: row.path || ""
											}, null, 8, ["text"])) : createCommentVNode("", true),
											moreRepo.value ? (openBlock(), createElementBlock("span", _hoisted_15, toDisplayString(row.repository), 1)) : createCommentVNode("", true),
											moreBase.value ? (openBlock(), createElementBlock("span", _hoisted_16, toDisplayString(row.baseType), 1)) : createCommentVNode("", true),
											row.rowType === "file" && !row.exists ? (openBlock(), createBlock(_sfc_main$2, {
												key: 4,
												name: "cloud_download",
												class: "offline",
												title: unref(t)("File Offline")
											}, null, 8, ["title"])) : createCommentVNode("", true)
										]),
										_: 2
									}, 1064, [
										"class",
										"style",
										"type",
										"role",
										"aria-selected",
										"onClick",
										"onDblclick",
										"onContextmenu"
									]);
								}), 128)),
								!loading.value && loaded.value && !visibleRows.value.length ? (openBlock(), createElementBlock("p", _hoisted_17, toDisplayString(unref(t)("No files for this selection")), 1)) : createCommentVNode("", true),
								hasNext.value ? (openBlock(), createBlock(_sfc_main$1, {
									key: 1,
									label: "Load more snapshots",
									disabled: loading.value,
									onClick: _cache[18] || (_cache[18] = ($event) => load(true))
								}, null, 8, ["disabled"])) : createCommentVNode("", true)
							], 8, _hoisted_13),
							unref(mobile) && phoneFile.value ? (openBlock(), createElementBlock("footer", _hoisted_18, [
								createVNode(_sfc_main$6, { text: phoneFile.value.filename || phoneFile.value.title }, null, 8, ["text"]),
								createVNode(_sfc_main$1, {
									label: "Open File",
									icon: "folder_open",
									"icon-only": "",
									disabled: !phoneFile.value.href,
									onClick: _cache[19] || (_cache[19] = ($event) => openFile(phoneFile.value))
								}, null, 8, ["disabled"]),
								createVNode(_sfc_main$1, {
									label: "Snapshot file actions",
									icon: "more",
									"icon-only": "",
									onClick: _cache[20] || (_cache[20] = ($event) => openMenu(phoneFile.value, $event, true))
								})
							])) : createCommentVNode("", true)
						], 2)) : createCommentVNode("", true),
						showingPreview.value && showingFiles.value ? (openBlock(), createElementBlock("div", {
							key: 2,
							class: normalizeClass(["snapshot-splitter resize-grip", { dragging: moving.value }]),
							role: "separator",
							tabindex: "0",
							"aria-orientation": vertical.value ? "vertical" : "horizontal",
							"aria-label": unref(t)("Resize snapshot panels"),
							"aria-valuemin": 22,
							"aria-valuemax": 78,
							"aria-valuenow": Math.round(ratio.value * 100),
							onPointerdown: drag,
							onPointermove: resize,
							onPointerup: endDrag,
							onPointercancel: endDrag,
							onKeydown: splitterKey
						}, null, 42, _hoisted_19)) : createCommentVNode("", true)
					], 6),
					createVNode(_sfc_main$4, {
						ref_key: "fileMenu",
						ref: fileMenu,
						class: "snapshot-file-menu",
						label: "Snapshot file actions",
						overlay: ""
					}, {
						default: withCtx(() => [
							createVNode(_sfc_main$1, {
								label: "Open File",
								icon: "folder_open",
								disabled: !contextFile.value?.href,
								onClick: _cache[21] || (_cache[21] = ($event) => fileAction("open"))
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$1, {
								label: "Show Folder",
								icon: "folder",
								disabled: "",
								title: unref(t)("Server folders cannot be opened by this browser.")
							}, null, 8, ["title"]),
							_cache[32] || (_cache[32] = createBaseVNode("hr", null, null, -1)),
							createVNode(_sfc_main$1, {
								label: "Copy File Path",
								icon: "copy",
								onClick: _cache[22] || (_cache[22] = ($event) => fileAction("copy_path"))
							}),
							createVNode(_sfc_main$1, {
								label: "Copy Web Link",
								icon: "link",
								disabled: !contextFile.value?.href,
								onClick: _cache[23] || (_cache[23] = ($event) => fileAction("copy_web_path"))
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$1, {
								label: "Copy To Clipboard",
								icon: "copy",
								disabled: !canCopyImage.value || !contextFile.value?.href,
								title: !canCopyImage.value ? unref(t)("Copying an image requires HTTPS or localhost and clipboard permission.") : "",
								onClick: _cache[24] || (_cache[24] = ($event) => fileAction("copy_image"))
							}, null, 8, ["disabled", "title"]),
							contextFile.value?.editing ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
								_cache[31] || (_cache[31] = createBaseVNode("hr", null, null, -1)),
								createVNode(_sfc_main$1, {
									label: "Edit Info",
									icon: "edit",
									onClick: _cache[25] || (_cache[25] = ($event) => fileAction("edit"))
								}),
								createVNode(_sfc_main$1, {
									label: "Delete",
									icon: "delete",
									onClick: _cache[26] || (_cache[26] = ($event) => fileAction("delete"))
								})
							], 64)) : createCommentVNode("", true)
						]),
						_: 1
					}, 512)
				], 8, _hoisted_1)])),
				createVNode(FilePreview_default, {
					ref_key: "preview",
					ref: preview,
					ticket: __props.ticket,
					project: __props.project,
					"search-type": "sthpw/file",
					onSessionExpired: _cache[27] || (_cache[27] = ($event) => emit("session-expired"))
				}, null, 8, ["ticket", "project"]),
				createVNode(RecordForm_default, {
					ref_key: "form",
					ref: form,
					ticket: __props.ticket,
					project: __props.project,
					"search-type": "sthpw/file",
					onSaved: changed
				}, null, 8, ["ticket", "project"]),
				createVNode(ObjectAction_default, {
					ref_key: "action",
					ref: action,
					ticket: __props.ticket,
					project: __props.project,
					"search-type": "sthpw/file",
					view: "table",
					onSaved: changed
				}, null, 8, ["ticket", "project"])
			], 64);
		};
	}
}, [["__scopeId", "data-v-7a588ddc"]]);
//#endregion
export { SnapshotBrowser_default as default };

//# sourceMappingURL=SnapshotBrowser.js.map
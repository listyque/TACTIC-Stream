import { F as resolveComponent, K as withDirectives, M as openBlock, _ as createElementBlock, b as createVNode, f as Teleport, g as createCommentVNode, h as createBlock, m as createBaseVNode, nt as normalizeStyle, rt as toDisplayString, s as vShow } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { F as securityGroups } from "./index.js";
import { H as observeFrameSizes, t as _sfc_main$1 } from "./FrameView.js";
import { i as toolbar, n as metrics, o as initial, r as row, s as transition, t as describe } from "./groups.ui.js";
//#region src/features/administration/SecurityGroups.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		},
		initialCode: String,
		closable: Boolean
	},
	emits: ["saved", "close"],
	data() {
		return {
			catalog: null,
			requestedCode: "",
			context: null,
			draft: null,
			original: null,
			members: [],
			originalMembers: [],
			busy: false,
			error: "",
			errorValues: {},
			message: "",
			uncertain: false,
			request: 0,
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null
		};
	},
	computed: {
		dirty() {
			return JSON.stringify(this.draft) !== JSON.stringify(this.original) || JSON.stringify([...this.members].sort()) !== JSON.stringify([...this.originalMembers].sort());
		},
		editable() {
			return this.context?.ticket === this.ticket && this.context?.project === this.project && !this.busy && !this.uncertain;
		},
		users() {
			const query = this.ui.query.trim().toLowerCase();
			return (this.catalog?.users || []).filter((user) => !query || (user.login + " " + user.displayName).toLowerCase().includes(query));
		},
		models() {
			const selected = new Set(this.members);
			return {
				groups: this.catalog?.groups || [],
				members: this.users.map((user) => ({
					...user,
					member: selected.has(user.login)
				}))
			};
		},
		frameModel() {
			return {
				draft: this.draft,
				ready: !!this.catalog && this.context?.ticket === this.ticket && this.context?.project === this.project,
				canWrite: !!this.catalog,
				canLoad: !!this.ticket,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				groupCount: this.catalog?.groups.length || 0,
				userCount: this.users.length,
				memberCount: this.members.length,
				error: t(this.error, this.errorValues),
				message: this.message
			};
		},
		hostStyle() {
			return { gap: metrics.toolbarGap + "px" };
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language, this.closable);
		}
	},
	mounted() {
		this.reload();
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
			this.reload();
		},
		ticket() {
			this.request++;
			this.busy = false;
			this.catalog = this.draft = this.original = null;
			this.requestedCode = "";
			this.members = [];
			this.originalMembers = [];
			this.uncertain = false;
			this.ui = initial();
			this.reload();
		}
	},
	methods: {
		t,
		rowScene(node, record) {
			return row(node, record, this.frameModel, this.ui, appearance.language);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
				case "create":
					this.create();
					break;
				case "query": break;
				case "select":
					this.select(command.code);
					break;
				case "field":
					if (this.draft) {
						this.draft[command.field] = command.value;
						this.message = "";
					}
					break;
				case "member":
					this.member(command.login, command.value);
					break;
				case "save":
					await this.save();
					break;
				case "reload":
					await this.reload(command.force);
					break;
				case "discard":
					this.select(this.original?.code || "", true);
					break;
				case "error":
					this.error = command.text;
					break;
				case "close":
					this.$emit("close");
					break;
				case "focus":
					await this.$nextTick();
					this.$el.querySelector("[data-frame=\"" + command.id + "\"]")?.focus();
					break;
				default: throw Error("Unsupported Groups command: " + command.type);
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
				this.error = "Save or discard group changes before leaving.";
				return false;
			}
			return true;
		},
		accept(catalog, selected) {
			this.catalog = catalog;
			const requested = this.requestedCode;
			this.requestedCode = "";
			this.select(requested || selected || catalog.groups[0]?.code || "", true);
			if (requested && this.draft?.code !== requested) this.error = "The configured table target is unavailable";
		},
		focus(code) {
			if (this.dirty || this.uncertain) throw new Error("Apply or discard unsaved changes first");
			if (this.busy || !this.catalog) this.requestedCode = code;
			else {
				this.select(code, true);
				if (this.draft?.code !== code) throw new Error("The configured table target is unavailable");
			}
		},
		select(code, loaded = false) {
			if (!loaded && (!this.editable || this.dirty)) return;
			const row = this.catalog?.groups.find((group) => group.code === code);
			this.draft = row ? {
				code: row.code,
				name: row.name,
				description: row.description,
				revision: row.revision
			} : null;
			this.original = this.draft ? { ...this.draft } : null;
			this.members = this.catalog?.memberships.filter((item) => item.login_group === row?.name).map((item) => item.login) || [];
			this.members = [...new Set(this.members)];
			this.originalMembers = [...this.members];
			this.error = "";
			this.ui.confirmation = "";
		},
		async reload(force = false) {
			if (this.busy || !this.ticket) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.dispatch({ type: "reload" });
				return;
			}
			const request = ++this.request, selected = this.draft?.code || this.initialCode;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await securityGroups("read", this.context.ticket);
				if (request !== this.request) return;
				this.uncertain = false;
				this.accept(result, selected);
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		create() {
			if (!this.editable || !this.catalog || this.dirty) return;
			this.select("", true);
			this.draft = {
				code: "",
				name: "",
				description: "",
				revision: ""
			};
			this.message = "";
		},
		member(login, selected) {
			if (!this.editable || !this.draft || !this.catalog.users.some((user) => user.login === login)) return;
			this.members = selected ? [.../* @__PURE__ */ new Set([...this.members, login])] : this.members.filter((value) => value !== login);
			this.message = "";
		},
		discard() {
			return this.dispatch({ type: "discard" });
		},
		requestClose() {
			return this.dispatch({ type: "close" });
		},
		async save() {
			if (!this.editable || !this.dirty || !this.draft) return;
			if (!this.draft.name.trim()) {
				this.error = "Enter a group identifier";
				return;
			}
			const request = this.request;
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await securityGroups("save", this.context.ticket, {
					group_code: this.draft.code,
					login_group: this.draft.name,
					description: this.draft.description,
					expected_revision: this.draft.revision,
					add_members: this.members.filter((login) => !this.originalMembers.includes(login)),
					remove_members: this.originalMembers.filter((login) => !this.members.includes(login))
				});
				if (request !== this.request) return;
				this.accept(result, result.selected);
				this.message = "Group saved on server";
				this.$emit("saved", result);
			} catch (error) {
				if (request !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Reload groups before trying again." : error.message;
				if (this.error?.startsWith("Users no longer exist: ")) {
					this.errorValues = { users: this.error.slice(23) };
					this.error = "Users no longer exist: {users}";
				}
			} finally {
				if (request === this.request) this.busy = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { key: 0 };
var _hoisted_3 = { class: "muted" };
var _hoisted_4 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "security-groups frame-host",
		style: normalizeStyle($options.hostStyle),
		"aria-label": $options.t("Groups and members"),
		"aria-busy": $data.busy
	}, [
		$props.closable ? (openBlock(), createElementBlock("header", _hoisted_2, [createBaseVNode("h2", null, toDisplayString($options.t("Groups and members")), 1), createBaseVNode("p", _hoisted_3, toDisplayString($options.t("Shared TACTIC login groups and their members")), 1)])) : createCommentVNode("", true),
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
		createBaseVNode("div", _hoisted_4, [createVNode(_component_FrameView, {
			scene: $options.frameScene,
			models: $options.models,
			"describe-row": $options.rowScene,
			onEvent: $options.dispatch
		}, null, 8, [
			"scene",
			"models",
			"describe-row",
			"onEvent"
		])], 512)
	], 12, _hoisted_1);
}
var SecurityGroups_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { SecurityGroups_default as default };

//# sourceMappingURL=SecurityGroups.js.map
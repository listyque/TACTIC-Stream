import { L as button, v as translate } from "./resize.js";
//#region ../src/tactic_stream/shared_ui/features/scripts/executor.ui.mjs
function status(executor = {}, language) {
	return translate(executor.error || {
		starting: "Connecting agent…",
		connected: "Agent connected",
		stopping: "Disconnecting agent…",
		external: "Connected outside this UI. Stop it where it was started."
	}[executor.state] || "Connect an agent to send requests.", language);
}
function control(executor = {}, bounds, language, enabled = true) {
	const running = [
		"starting",
		"connected",
		"stopping"
	].includes(executor.state);
	return button("agentExecutorControl", bounds, translate({
		starting: "Stop connecting",
		connected: "Disconnect agent",
		stopping: "Disconnecting…",
		external: "Agent connected"
	}[executor.state] || "Connect agent", language), running ? "stop" : "play", {
		type: "executor",
		value: running ? "stop" : "start"
	}, enabled && !["stopping", "external"].includes(executor.state), { highlighted: !running && executor.state !== "external" });
}
//#endregion
export { status as n, control as t };

//# sourceMappingURL=executor.ui.js.map
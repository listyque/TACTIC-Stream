export function initial() {return {nodes: [
  {identity: "a", label: "Asset", kind: "search_type", nodeX: 35, nodeY: 75, color: "#ab67c8"},
  {identity: "b", label: "Shot", kind: "search_type", nodeX: 340, nodeY: 75, color: "#df6464"},
  {identity: "ready", label: "Ready", kind: "progress", nodeX: 140, nodeY: 300, color: "#66ac8b"},
  {identity: "ref", label: "Reference", kind: "missing", nodeX: 540, nodeY: 300, referenceOnly: true}
], edges: [{from: "a", to: "b", label: "Asset — Shot"}, {from: "b", to: "a", label: "Reverse"}, {from: "b", to: "ready", label: "Complete"}], selectedNodes: [], selectedEdge: -1, readOnly: false, selectionEnabled: true};}
export function apply(model, command) {
  if (command.type === "selectNodes") return Object.assign({}, model, {selectedNodes: command.identities, selectedEdge: -1});
  if (command.type === "selectEdge") return Object.assign({}, model, {selectedNodes: [], selectedEdge: command.index});
  if (command.type === "clear") return Object.assign({}, model, {selectedNodes: [], selectedEdge: -1});
  if (command.type === "moveNodes") return Object.assign({}, model, {nodes: model.nodes.map(row => Object.assign({}, row, command.positions.find(p => p.identity === row.identity) || {}))});
  if (command.type === "connect") return Object.assign({}, model, {edges: model.edges.concat([{from: command.from, to: command.to}])});
  return model;
}

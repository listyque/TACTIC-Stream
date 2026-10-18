// Handler script_shelf.py: an empty personal shelf deliberately overrides the shared one.
export const globalShelf = 'script_shelf@global';
export function effectiveShelf(shelves, mode, entryKey, preset) {
  const valid = shelves.filter((row) => row.valid);
  if (mode === 'personal')
    return (
      valid.find(
        (row) =>
          row.personal &&
          row.configuration.scope === 'tab' &&
          row.configuration.entryKey === entryKey
      ) ||
      valid.find((row) => row.personal && row.configuration.scope === 'global')
    );
  return (
    valid.find((row) => !row.personal && row.view === preset) ||
    valid.find((row) => !row.personal && row.view === globalShelf)
  );
}
export function buttonId() {
  return [...crypto.getRandomValues(new Uint8Array(16))]
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('');
}

export function scriptTree(scripts) {
  const root = [];
  for (const script of scripts || []) {
    const parts = script.path.split('/');
    let nodes = root,
      path = '';
    for (const name of parts.slice(0, -1)) {
      path = [path, name].filter(Boolean).join('/');
      let folder = nodes.find(
        (node) => node.kind === 'section' && node.title === name
      );
      if (!folder) {
        folder = {
          key: 'folder:' + path,
          title: name,
          kind: 'section',
          children: []
        };
        nodes.push(folder);
      }
      nodes = folder.children;
    }
    nodes.push({
      key: script.path,
      title: parts.at(-1),
      searchText: script.path,
      kind: 'script',
      supported: script.runnable,
      icon: script.language.includes('python') ? 'MDI_LANGUAGE_PYTHON' : 'code',
      children: []
    });
  }
  function sort(nodes) {
    nodes.sort(
      (a, b) =>
        (a.kind === 'section' ? 0 : 1) - (b.kind === 'section' ? 0 : 1) ||
        a.title.localeCompare(b.title)
    );
    nodes.forEach((node) => sort(node.children));
  }
  sort(root);
  return root;
}

export async function runBrowserScript(source, context) {
  // A module keeps CSP's ban on eval/inline scripts for authorized shelf/editor code.
  const url = URL.createObjectURL(
    new Blob(
      [
        'export default async function(context) {\nconst { project, searchType, searchKeys, rpc, refresh, console = globalThis.console } = context;\n' +
          source +
          '\n}'
      ],
      { type: 'text/javascript' }
    )
  );
  try {
    const module = await import(/* @vite-ignore */ url);
    return await module.default(context);
  } finally {
    URL.revokeObjectURL(url);
  }
}

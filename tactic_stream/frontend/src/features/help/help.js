// Handler HelpController: front matter, first heading/summary, ordering and EN fallback.
export function readArticle(id, source, file) {
  const lines = source.replace(/^\uFEFF/, '').split(/\r?\n/),
    metadata = {};
  if (lines[0]?.trim() === '---') {
    const end = lines.findIndex(
      (line, index) => index > 0 && line.trim() === '---'
    );
    if (end < 0) throw new Error('Unclosed help article metadata');
    for (const line of lines.slice(1, end)) {
      const colon = line.indexOf(':');
      if (colon < 1 || !line.slice(colon + 1).trim())
        throw new Error('Invalid help article metadata');
      metadata[line.slice(0, colon).trim()] = line.slice(colon + 1).trim();
    }
    lines.splice(0, end + 1);
  }
  const heading = lines.findIndex((line) => line.startsWith('# '));
  if (heading < 0) throw new Error('Help article has no title');
  const title = lines.splice(heading, 1)[0].slice(2).trim();
  if (!title) throw new Error('Help article has an empty title');
  const value = metadata.order || '1000',
    order = Number(value);
  if (!/^[+-]?\d+$/.test(value) || !Number.isSafeInteger(order))
    throw new Error('Invalid help article order');
  const start = lines.findIndex((line) => line.trim()),
    summaryLines = [];
  if (start >= 0) {
    let end = start;
    while (lines[end]?.trimStart().startsWith('>'))
      summaryLines.push(lines[end++].trimStart().slice(1).trimStart());
    lines.splice(start, end - start);
  }
  const summary = summaryLines.join('\n').trim(),
    body = lines.join('\n').trim();
  return {
    id,
    title,
    group: metadata.group || 'Other',
    icon: metadata.icon || 'help',
    order,
    summary,
    body,
    source,
    file,
    reference: metadata.reference === 'Handler',
    searchText: (
      title +
      ' ' +
      (metadata.group || 'Other') +
      ' ' +
      summary +
      '\n' +
      body
    )
      .replace(/[`#>*_|\[\]()]/g, ' ')
      .replace(/\s+/g, ' ')
  };
}

export async function loadArticles(language, signal) {
  const options = { cache: 'no-store', signal };
  const response = await fetch('/ui/help/index.json', options);
  if (!response.ok)
    throw new Error('Help articles are unavailable. Try reloading.');
  const index = await response.json();
  if (!Array.isArray(index) || !index.length || index.length > 200)
    throw new Error('Invalid help catalog');
  const seen = new Set();
  const articles = await Promise.all(
    index.map(async (entry) => {
      if (
        !/^[a-z][a-z0-9_.-]*$/.test(entry.id) ||
        seen.has(entry.id) ||
        !Array.isArray(entry.languages) ||
        !entry.languages.includes('en')
      )
        throw new Error('Invalid help catalog');
      seen.add(entry.id);
      const chosen =
        /^[a-z]{2}$/.test(language) && entry.languages.includes(language)
          ? language
          : 'en';
      let file = '/ui/help/' + entry.id + '.' + chosen + '.md';
      let result = await fetch(file, options);
      if (result.status === 404 && chosen !== 'en') {
        file = '/ui/help/' + entry.id + '.en.md';
        result = await fetch(file, options);
      }
      if (!result.ok)
        throw new Error('Help articles are unavailable. Try reloading.');
      return readArticle(entry.id, await result.text(), file);
    })
  );
  return articles.sort(
    (first, second) =>
      first.order - second.order || first.title.localeCompare(second.title)
  );
}

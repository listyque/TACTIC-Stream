import { rpc } from '../../api.js';

export async function printCustomReport(model, ticket, project) {
  const response = await rpc('execute_cmd', [
    { ticket, project, language: 'python' },
    'tactic.ui.table.CustomLayoutReportCmd',
    {
      search_key: model.targetSearchKey,
      view: model.layoutView
    }
  ]);
  const frame = document.createElement('iframe');
  frame.setAttribute('title', model.title || 'Shot Sheet');
  frame.style.display = 'none';
  document.body.append(frame);
  const page = frame.contentDocument;
  page.title = model.title || 'Shot Sheet';
  const style = page.createElement('style');
  style.textContent =
    'body{font:12px sans-serif}table{width:100%;border-collapse:collapse;margin:12px 0}td,th{text-align:left;padding:5px;border:1px solid #aaa}tr{break-inside:avoid}img{max-width:300px;max-height:300px}';
  page.head.append(style);
  for (const block of response.info.blocks) {
    if (block.kind === 'image') {
      const image = page.createElement('img');
      image.src = 'data:' + block.mime + ';base64,' + block.data;
      page.body.append(image);
    } else if (block.kind === 'table') {
      const title = page.createElement('h3');
      title.textContent = block.title;
      page.body.append(title);
      const table = page.createElement('table');
      for (const [index, row] of [block.columns, ...block.rows].entries()) {
        const tr = page.createElement('tr');
        for (const value of row) {
          const cell = page.createElement(index ? 'td' : 'th');
          cell.textContent = value;
          tr.append(cell);
        }
        table.append(tr);
      }
      page.body.append(table);
    } else {
      const text = page.createElement('p');
      text.textContent = block.text;
      page.body.append(text);
    }
  }
  try {
    await Promise.all([...page.images].map((image) => image.decode()));
    frame.contentWindow.focus();
    frame.contentWindow.print();
  } finally {
    frame.remove();
  }
}

// Handler Knowledge canonical Markdown and rich document bridge (EPL-1.0).
import MarkdownIt from 'markdown-it';
import { escapeHtml } from '../../controls/richText.js';
import {
  pythonTokens,
  javascriptTokens,
  xmlTokens
} from '../../controls/pythonSyntax.js';
import { browserLink } from '../workspace/links.js';

export const safeUrl = (value) =>
  /^(https?:\/\/|ftp:\/\/|mailto:|skey:\/\/|tactic-search:\/\/|\/assets\/|#)/i.test(
    value || ''
  ) && !/[\u0000-\u001f]/.test(value);
const parser = new MarkdownIt({
  html: true,
  breaks: false,
  linkify: true,
  highlight(source, language) {
    const tokenize = {
      python: pythonTokens,
      py: pythonTokens,
      javascript: javascriptTokens,
      js: javascriptTokens,
      xml: xmlTokens
    }[language];
    return tokenize
      ? tokenize(source)
          .map((token) =>
            token.role
              ? `<span class="syntax-${token.role}">${escapeHtml(token.text)}</span>`
              : escapeHtml(token.text)
          )
          .join('')
      : escapeHtml(source);
  }
});
parser.validateLink = safeUrl;
parser.linkify.add('skey:', {
  validate(text, position) {
    return (
      /^\/\/[^\s<>"\[\]]+/
        .exec(text.slice(position))?.[0]
        .replace(/[.,;:!?)}]+$/, '').length || 0
    );
  }
});
parser.core.ruler.after('inline', 'knowledge_attributes', (state) => {
  for (let i = 0; i < state.tokens.length; i++) {
    const token = state.tokens[i];
    if (token.type !== 'inline' || !token.children?.length) continue;
    const tail = token.children.at(-1),
      align =
        tail.type === 'text' &&
        tail.content.match(/\s+\{align=(center|right|justify)\}$/);
    if (align) {
      tail.content = tail.content.slice(0, -align[0].length);
      state.tokens[i - 1].attrSet('align', align[1]);
    }
    const first = token.children[0],
      checklist =
        first.type === 'text' && first.content.match(/^\[([ xX])\]\s/);
    if (
      checklist &&
      state.tokens[i - 1]?.type === 'paragraph_open' &&
      state.tokens[i - 2]?.type === 'list_item_open'
    ) {
      first.content = first.content.slice(checklist[0].length);
      const box = new state.Token('html_inline', '', 0);
      box.content = `<input type="checkbox" ${checklist[1].trim() ? 'checked' : ''} disabled>`;
      token.children.unshift(box);
    }
  }
});
const renderImage = parser.renderer.rules.image;
parser.renderer.rules.image = (tokens, index, options, env, self) => {
  const token = tokens[index],
    next = tokens[index + 1];
  const size =
    next?.type === 'text' &&
    next.content.match(/^\{width=(\d+)(?: height=(\d+))?(?: fit=(content))?\}/);
  if (size) {
    token.attrSet('width', size[1]);
    if (size[2]) token.attrSet('height', size[2]);
    if (size[3]) token.attrSet('data-fit', 'content');
    next.content = next.content.slice(size[0].length);
  }
  return renderImage(tokens, index, options, env, self);
};
parser.renderer.rules.fence = (tokens, index) => {
  const token = tokens[index],
    language = token.info.trim().split(/\s+/)[0];
  return `<pre data-language="${escapeHtml(language)}"><code>${parser.options.highlight(token.content, language)}</code></pre>`;
};

export function sanitize(html, project = '') {
  const root = document.createElement('template');
  root.innerHTML = html;
  const allowed = new Set(
    'P DIV BR H1 H2 H3 H4 H5 H6 STRONG B EM I U S DEL SMALL UL OL LI BLOCKQUOTE PRE CODE HR A IMG TABLE THEAD TBODY TR TH TD SPAN INPUT'.split(
      ' '
    )
  );
  for (const node of [...root.content.querySelectorAll('*')]) {
    if (
      ['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'SVG', 'MATH', 'FORM'].includes(
        node.tagName
      )
    ) {
      node.remove();
      continue;
    }
    if (!allowed.has(node.tagName)) {
      node.replaceWith(...node.childNodes);
      continue;
    }
    const values = Object.fromEntries(
      [...node.attributes].map((attr) => [attr.name, attr.value])
    );
    if (node.tagName === 'SPAN' && values.style) {
      for (const [pattern, tag] of [
        [/font-weight:\s*(bold|[6-9]00)/i, 'strong'],
        [/font-style:\s*italic/i, 'em'],
        [/text-decoration[^:]*:\s*[^;]*underline/i, 'u'],
        [/text-decoration[^:]*:\s*[^;]*line-through/i, 's']
      ]) {
        if (pattern.test(values.style)) {
          const wrapper = document.createElement(tag);
          wrapper.append(...node.childNodes);
          node.append(wrapper);
        }
      }
    }
    for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
    if (node.tagName === 'A' && safeUrl(values.href)) {
      node.setAttribute('href', browserLink(values.href, project));
      node.dataset.link = values.href;
      if (!/^(skey|tactic-search):/i.test(values.href)) {
        node.target = '_blank';
        node.rel = 'noopener noreferrer';
      }
    }
    if (node.tagName === 'IMG') {
      if (!/^(https?:\/\/|\/assets\/)/i.test(values.src || '')) {
        node.replaceWith(document.createTextNode(values.alt || ''));
        continue;
      }
      node.src = values.src;
      node.alt = values.alt || '';
      node.loading = 'lazy';
      for (const name of ['width', 'height'])
        if (/^\d{1,5}$/.test(values[name] || ''))
          node.setAttribute(name, values[name]);
      if (values['data-fit'] === 'content') node.dataset.fit = 'content';
    }
    if (node.tagName === 'PRE')
      node.dataset.language = (values['data-language'] || '').replace(
        /[^\w+-]/g,
        ''
      );
    if (node.tagName === 'SPAN' && /^syntax-[\w-]+$/.test(values.class || ''))
      node.className = values.class;
    const align =
      values.align ||
      values.style?.match(/text-align:\s*(left|right|center|justify)/)?.[1];
    if (['left', 'center', 'right', 'justify'].includes(align))
      node.setAttribute('align', align);
    if (node.tagName === 'INPUT') {
      if (values.type !== 'checkbox') {
        node.remove();
        continue;
      }
      node.type = 'checkbox';
      node.disabled = true;
      node.defaultChecked = Object.hasOwn(values, 'checked');
    }
  }
  return root;
}

export function articleHtml(source, project = '') {
  // Extra author-entered blank rows survive CommonMark without touching fenced code.
  let fence = null;
  const lines = String(source || '').split('\n'),
    prepared = [];
  for (let i = 0; i < lines.length; i++) {
    const marker = lines[i].match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
    if (
      marker &&
      (!fence ||
        (marker[1][0] === fence[0] &&
          marker[1].length >= fence.length &&
          !marker[2].trim()))
    )
      fence = fence ? null : marker[1];
    prepared.push(
      !fence && !lines[i] && i && !lines[i - 1] ? '<br />\n' : lines[i]
    );
  }
  const root = sanitize(parser.render(prepared.join('\n')), project),
    counts = new Map();
  for (const heading of root.content.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
    const id =
      heading.textContent
        .toLowerCase()
        .replace(/[^\p{L}\p{N}_ -]/gu, '')
        .trim()
        .replace(/\s+/g, '-') || 'heading';
    const count = counts.get(id) || 0;
    counts.set(id, count + 1);
    heading.id = id + (count ? '-' + count : '');
  }
  return root.innerHTML;
}

export function htmlMarkdown(root) {
  function inline(node) {
    if (node.nodeType === Node.TEXT_NODE)
      return node.textContent.replace(/([\\`*_[\]])/g, '\\$1');
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const text = [...node.childNodes].map(inline).join(''),
      tag = node.tagName;
    if (tag === 'BR') return '  \n';
    if (tag === 'INPUT') return node.checked ? '[x] ' : '[ ] ';
    if (['STRONG', 'B'].includes(tag)) return `**${text}**`;
    if (['EM', 'I'].includes(tag)) return `*${text}*`;
    if (['S', 'DEL'].includes(tag)) return `~~${text}~~`;
    if (tag === 'U' || tag === 'SMALL')
      return `<${tag.toLowerCase()}>${text}</${tag.toLowerCase()}>`;
    if (tag === 'CODE') {
      const code = node.textContent,
        fence = '`'.repeat(
          Math.max(
            1,
            ...[...code.matchAll(/`+/g)].map((match) => match[0].length + 1)
          )
        );
      return fence + ' ' + code + ' ' + fence;
    }
    if (tag === 'A')
      return `[${text}](${node.dataset.link || node.getAttribute('href') || ''})`;
    if (tag === 'IMG')
      return (
        `![${node.alt || ''}](${node.dataset.original || node.getAttribute('src')})` +
        (node.getAttribute('width')
          ? `{width=${node.getAttribute('width')}${node.getAttribute('height') ? ' height=' + node.getAttribute('height') : ''}${node.dataset.fit === 'content' ? ' fit=content' : ''}}`
          : '')
      );
    if (
      [
        'P',
        'DIV',
        'H1',
        'H2',
        'H3',
        'H4',
        'H5',
        'H6',
        'UL',
        'OL',
        'LI',
        'BLOCKQUOTE',
        'PRE',
        'HR',
        'TABLE'
      ].includes(tag)
    )
      return block(node);
    return text;
  }
  function block(node) {
    const tag = node.tagName,
      text = [...node.childNodes].map(inline).join('');
    const alignment =
      node.getAttribute('align') && node.getAttribute('align') !== 'left'
        ? ` {align=${node.getAttribute('align')}}`
        : '';
    if (/^H[1-6]$/.test(tag))
      return '#'.repeat(Number(tag[1])) + ' ' + text + alignment + '\n\n';
    if (tag === 'PRE') {
      const source = node.textContent.replace(/\n$/, '');
      const fence = '`'.repeat(
        Math.max(
          3,
          ...[...source.matchAll(/`+/g)].map((match) => match[0].length + 1)
        )
      );
      return `${fence}${node.dataset.language || ''}\n${source}\n${fence}\n\n`;
    }
    if (tag === 'HR') return '---\n\n';
    if (tag === 'BLOCKQUOTE')
      return (
        text
          .trim()
          .split('\n')
          .map((line) => '> ' + line)
          .join('\n') + '\n\n'
      );
    if (tag === 'UL' || tag === 'OL')
      return (
        [...node.children]
          .map((li, index) => {
            const marker = tag === 'OL' ? `${index + 1}. ` : '- ';
            const parts = [...li.childNodes].map((child) =>
              child.nodeType === Node.ELEMENT_NODE
                ? ['UL', 'OL'].includes(child.tagName)
                  ? '\n' + block(child).trimEnd()
                  : child.tagName === 'P'
                    ? [...child.childNodes].map(inline).join('')
                    : inline(child)
                : inline(child)
            );
            return (
              marker +
              parts
                .join('')
                .trim()
                .replace(/\n/g, '\n' + ' '.repeat(marker.length))
            );
          })
          .join('\n') + '\n\n'
      );
    if (tag === 'TABLE') {
      const rows = [...node.querySelectorAll('tr')].map(
        (row) =>
          '| ' +
          [...row.children]
            .map((cell) =>
              [...cell.childNodes]
                .map(inline)
                .join('')
                .replace(/\|/g, '\\|')
                .replace(/\n/g, '<br>')
            )
            .join(' | ') +
          ' |'
      );
      if (rows.length)
        rows.splice(
          1,
          0,
          '| ' +
            [...node.querySelector('tr').children]
              .map(() => '---')
              .join(' | ') +
            ' |'
        );
      return rows.join('\n') + '\n\n';
    }
    if (tag === 'INPUT') return node.checked ? '[x] ' : '[ ] ';
    const value = text.trim() || '<br />';
    return value + alignment + '\n\n';
  }
  return [...root.childNodes]
    .map((node) =>
      node.nodeType === Node.TEXT_NODE
        ? node.textContent.trim()
          ? inline(node)
          : ''
        : ['IMG', 'A', 'INPUT'].includes(node.tagName)
          ? inline(node) + '\n\n'
          : block(node)
    )
    .join('')
    .trimEnd();
}

export function plainText(source) {
  const root = sanitize(parser.render(source || ''));
  for (const node of root.content.querySelectorAll(
    'p,div,h1,h2,h3,h4,h5,h6,li,pre,tr'
  ))
    node.append(document.createTextNode('\n'));
  return root.content.textContent.trim();
}

import MarkdownIt from 'markdown-it'
import { escapeHtml } from './richText.js'
import { pythonTokens, javascriptTokens, xmlTokens } from './pythonSyntax.js'

const markdown = new MarkdownIt({ html: false, highlight(source, language) {
  const tokenize = { python: pythonTokens, py: pythonTokens, javascript: javascriptTokens, js: javascriptTokens, xml: xmlTokens }[language]
  return tokenize ? tokenize(source).map(token => token.role ? '<span class="syntax-' + token.role + '">' + escapeHtml(token.text) + '</span>' : escapeHtml(token.text)).join('') : escapeHtml(source)
} })
// Public help may link to articles and bundled images, never local/private files or executable URLs.
markdown.validateLink = href => /^(https?:\/\/|mailto:|#[\w\p{L}-]+$|[a-z][a-z0-9_.-]*\.(?:en|ru)\.md(?:#[\w\p{L}-]+)?$|(?:\.\/)?media\/[\w.-]+\.(?:png|jpe?g|webp)$)/iu.test(href)
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const href = tokens[index].attrGet('href')
  if (/^https?:/i.test(href)) { tokens[index].attrSet('target', '_blank'); tokens[index].attrSet('rel', 'noopener noreferrer') }
  return self.renderToken(tokens, index, options)
}
const renderImage = markdown.renderer.rules.image
markdown.renderer.rules.image = (tokens, index, options, env, self) => {
  const token = tokens[index], source = token.attrGet('src')
  if (!/^(?:\.\/)?media\/[\w.-]+\.(?:png|jpe?g|webp)$/i.test(source)) return escapeHtml(token.content)
  token.attrSet('src', '/ui/help/' + source.replace(/^\.\//, '')); token.attrSet('loading', 'lazy')
  return renderImage(tokens, index, options, env, self)
}
markdown.renderer.rules.heading_open = (tokens, index, options, env, self) => {
  const name = tokens[index + 1].content.toLocaleLowerCase().replace(/[^\p{L}\p{N}_ -]/gu, '').trim().replace(/\s+/g, '-')
  env.headings ||= new Map()
  const count = env.headings.get(name) || 0; env.headings.set(name, count + 1)
  tokens[index].attrSet('id', name + (count ? '-' + count : ''))
  return self.renderToken(tokens, index, options)
}
export function renderMarkdown(text) { return markdown.render(text) }

const DROP = new Set([
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'form',
  'input',
  'button',
  'textarea',
  'select',
  'option',
  'link',
  'meta',
  'base',
  'svg',
  'math',
  'noscript',
  'template',
])

const ALLOWED = new Set([
  'p',
  'div',
  'span',
  'br',
  'hr',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'strong',
  'b',
  'em',
  'i',
  'u',
  's',
  'sub',
  'sup',
  'ul',
  'ol',
  'li',
  'blockquote',
  'pre',
  'code',
  'table',
  'thead',
  'tbody',
  'tfoot',
  'tr',
  'th',
  'td',
  'a',
  'img',
  'figure',
  'figcaption',
  'section',
  'article',
])

const DATA_IMAGES = new Set(['data:image/png', 'data:image/jpeg', 'data:image/jpg', 'data:image/gif', 'data:image/webp'])

function compactUrl(value: string): string {
  return value.replace(/\s+/g, '').toLowerCase()
}

function safeUrl(value: string, allowDataImage: boolean): string | null {
  const raw = value.trim()
  if (!raw) return null
  const compact = compactUrl(raw)
  if (compact.startsWith('javascript:') || compact.startsWith('vbscript:')) return null
  if (compact.startsWith('data:')) {
    if (!allowDataImage) return null
    const mime = compact.split(';')[0]
    return DATA_IMAGES.has(mime) ? raw : null
  }
  if (
    compact.startsWith('http://') ||
    compact.startsWith('https://') ||
    compact.startsWith('mailto:') ||
    compact.startsWith('/') ||
    compact.startsWith('./') ||
    compact.startsWith('../')
  ) {
    return raw
  }
  if (!raw.split('/')[0].includes(':')) return raw
  return null
}

function safeStyle(value: string): string | null {
  const raw = value.trim()
  if (!raw) return null
  const low = raw.toLowerCase()
  if (['javascript', 'expression', 'behavior', '@import', 'vbscript', '-moz-binding'].some((token) => low.includes(token))) {
    return null
  }
  return raw
}

function copyAttrs(source: Element, target: HTMLElement) {
  const tag = target.tagName.toLowerCase()
  for (const attr of Array.from(source.attributes)) {
    const name = attr.name.toLowerCase()
    if (!name || name.startsWith('on') || name === 'srcdoc' || name === 'formaction') continue
    if (name === 'class' || name === 'title' || ((tag === 'td' || tag === 'th') && (name === 'colspan' || name === 'rowspan'))) {
      target.setAttribute(name, attr.value)
      continue
    }
    if (tag === 'a' && name === 'href') {
      const url = safeUrl(attr.value, false)
      if (url) target.setAttribute('href', url)
      continue
    }
    if (tag === 'a' && name === 'target' && attr.value.trim().toLowerCase() === '_blank') {
      target.setAttribute('target', '_blank')
      target.setAttribute('rel', 'noopener noreferrer')
      continue
    }
    if (tag === 'img' && name === 'src') {
      const url = safeUrl(attr.value, true)
      if (url) target.setAttribute('src', url)
      continue
    }
    if (tag === 'img' && (name === 'alt' || name === 'width' || name === 'height')) {
      target.setAttribute(name, attr.value)
      continue
    }
    if (name === 'style') {
      const style = safeStyle(attr.value)
      if (style) target.setAttribute('style', style)
      continue
    }
    if (name === 'data-preset' && /^(clean-read|marketing|decision-scan|analysis-report)$/.test(attr.value.trim())) {
      target.setAttribute(name, attr.value.trim())
      continue
    }
    if (name === 'data-zone' && /^(paid|body_paid|free|free_body)$/.test(attr.value.trim().toLowerCase())) {
      target.setAttribute(name, attr.value.trim().toLowerCase())
      continue
    }
    if (
      name === 'data-paywall' &&
      /^(1|true|yes|paid|0|false|no|free)$/.test(attr.value.trim().toLowerCase())
    ) {
      target.setAttribute(name, attr.value.trim().toLowerCase())
    }
  }
}

function cleanNode(node: Node): Node | null {
  if (node.nodeType === Node.TEXT_NODE) {
    return document.createTextNode(node.textContent || '')
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return null
  const el = node as HTMLElement
  const tag = el.tagName.toLowerCase()
  if (DROP.has(tag)) return null
  if (!ALLOWED.has(tag)) {
    const frag = document.createDocumentFragment()
    el.childNodes.forEach((child) => {
      const next = cleanNode(child)
      if (next) frag.appendChild(next)
    })
    return frag
  }
  const out = document.createElement(tag)
  copyAttrs(el, out)
  if (tag === 'img' && !out.getAttribute('src')) return null
  el.childNodes.forEach((child) => {
    const next = cleanNode(child)
    if (next) out.appendChild(next)
  })
  return out
}

/** 查看/审核只读预览。接口已消毒，这里再拦一遍再交给 v-html。 */
export function sanitizeLayoutHtml(raw: string | null | undefined): string {
  const source = (raw || '').trim()
  if (!source || typeof DOMParser === 'undefined') return ''
  const doc = new DOMParser().parseFromString(source, 'text/html')
  const holder = document.createElement('div')
  doc.body.childNodes.forEach((child) => {
    const next = cleanNode(child)
    if (next) holder.appendChild(next)
  })
  return holder.innerHTML.trim()
}

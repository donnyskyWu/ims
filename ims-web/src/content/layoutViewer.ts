/** 审核抽屉只读渲染 layout_html。重建 DOM，不把原文交给 innerHTML。 */

const ALLOWED = new Set([
  'p',
  'br',
  'div',
  'span',
  'strong',
  'b',
  'em',
  'i',
  'u',
  's',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'ul',
  'ol',
  'li',
  'blockquote',
  'pre',
  'code',
  'table',
  'thead',
  'tbody',
  'tr',
  'th',
  'td',
  'a',
  'img',
  'hr',
  'figure',
  'figcaption',
  'section',
  'article',
  'sup',
  'sub',
])

const VOID = new Set(['br', 'img', 'hr'])

const DROP = new Set([
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'noscript',
  'template',
  'svg',
  'math',
  'form',
  'input',
  'button',
  'textarea',
  'select',
  'option',
  'video',
  'audio',
  'source',
  'canvas',
  'link',
  'meta',
  'base',
])

const STYLE_DECL = /(width|max-width|height)\s*:\s*(\d+(?:\.\d+)?)(px|%)/gi

export function safeImgSrc(value: string): string {
  const url = value.replace(/\0/g, '').trim()
  const lower = url.toLowerCase()
  if (!url || lower.startsWith('javascript:') || lower.startsWith('vbscript:') || lower.startsWith('data:text')) {
    return ''
  }
  if (lower.startsWith('data:image/')) {
    const mime = lower.slice('data:image/'.length).split(';', 1)[0]
    if (!['png', 'jpeg', 'jpg', 'gif', 'webp'].includes(mime) || !lower.includes(';base64,')) return ''
    return url
  }
  if (lower.startsWith('https://') || lower.startsWith('http://')) return url
  if (lower.startsWith('/') && !lower.startsWith('//')) return url
  return ''
}

function safeHref(value: string): string {
  const url = value.replace(/\0/g, '').trim()
  const lower = url.toLowerCase()
  if (!url || lower.startsWith('javascript:') || lower.startsWith('vbscript:')) return ''
  if (lower.startsWith('https://') || lower.startsWith('http://') || lower.startsWith('mailto:') || lower.startsWith('#')) {
    return url
  }
  return ''
}

function safeStyle(style: string): string {
  const parts: string[] = []
  const seen = new Set<string>()
  for (const match of style.matchAll(STYLE_DECL)) {
    const prop = match[1].toLowerCase()
    if (seen.has(prop)) continue
    seen.add(prop)
    parts.push(`${prop}:${match[2]}${match[3].toLowerCase()}`)
  }
  return parts.join(';')
}

function applyAttrs(source: Element, target: HTMLElement) {
  const tag = target.tagName.toLowerCase()
  if (tag === 'img') {
    const src = safeImgSrc(source.getAttribute('src') || '')
    if (!src) return false
    target.setAttribute('src', src)
    target.setAttribute('draggable', 'false')
    const alt = source.getAttribute('alt')
    if (alt) target.setAttribute('alt', alt)
    const title = source.getAttribute('title')
    if (title) target.setAttribute('title', title.slice(0, 128))
    for (const key of ['width', 'height'] as const) {
      const value = (source.getAttribute(key) || '').trim().toLowerCase()
      if (/^\d{1,4}(px)?$/.test(value)) target.setAttribute(key, value)
    }
    const dataW = (source.getAttribute('data-w') || '').trim()
    if (/^\d{1,4}$/.test(dataW)) target.setAttribute('data-w', dataW)
    let style = safeStyle(source.getAttribute('style') || '')
    if (dataW && /^\d{1,4}$/.test(dataW) && !style.includes('width:')) {
      style = style ? `width:${dataW}px;${style}` : `width:${dataW}px`
    }
    if (style) target.setAttribute('style', style)
  } else if (tag === 'a') {
    const href = safeHref(source.getAttribute('href') || '')
    if (href) target.setAttribute('href', href)
    const title = source.getAttribute('title')
    if (title) target.setAttribute('title', title.slice(0, 128))
  } else if (tag === 'td' || tag === 'th') {
    for (const key of ['colspan', 'rowspan']) {
      const value = (source.getAttribute(key) || '').trim()
      if (/^\d{1,3}$/.test(value)) target.setAttribute(key, value)
    }
  }
  const className = (source.getAttribute('class') || '').trim()
  if (/^[A-Za-z0-9 _-]+$/.test(className)) target.setAttribute('class', className)
  if (tag !== 'img' && ['p', 'div', 'span', 'figure', 'section', 'td', 'th'].includes(tag)) {
    const style = safeStyle(source.getAttribute('style') || '')
    if (style) target.setAttribute('style', style)
  }
  return true
}

function appendClean(source: Node, target: Node) {
  for (const child of [...source.childNodes]) {
    if (child.nodeType === Node.TEXT_NODE) {
      target.appendChild(document.createTextNode(child.textContent || ''))
      continue
    }
    if (child.nodeType !== Node.ELEMENT_NODE) continue
    const el = child as Element
    const tag = el.tagName.toLowerCase()
    if (DROP.has(tag)) continue
    if (!ALLOWED.has(tag)) {
      appendClean(el, target)
      continue
    }
    const next = document.createElement(tag)
    if (!applyAttrs(el, next)) continue
    if (!VOID.has(tag)) appendClean(el, next)
    target.appendChild(next)
  }
}

export function hasVisibleLayout(raw: string): boolean {
  if (!raw || !raw.trim()) return false
  const parsed = new DOMParser().parseFromString(raw, 'text/html')
  for (const node of parsed.body.querySelectorAll([...DROP].join(','))) node.remove()
  if ((parsed.body.textContent || '').replace(/\u00a0/g, ' ').trim()) return true
  return [...parsed.body.querySelectorAll('img')].some((img) => safeImgSrc(img.getAttribute('src') || ''))
}

export function renderLayoutHtml(host: HTMLElement, raw: string) {
  host.replaceChildren()
  const parsed = new DOMParser().parseFromString(raw || '', 'text/html')
  const frag = document.createDocumentFragment()
  appendClean(parsed.body, frag)
  host.appendChild(frag)
}

export type ChartPoint = { k: string; v: number; t?: string }

function fmtNum(n: number): string {
  if (Number.isNaN(n)) return '—'
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

export function bi0SvgBars(series: ChartPoint[], color = 'var(--blue)'): string {
  const w = 420
  const hh = 190
  const base = hh - 28
  const max = Math.max(...series.map((s) => s.v), 1)
  const step = (w - 60) / Math.max(series.length, 1)
  let g = `<svg class="bi0-chart-svg" viewBox="0 0 ${w} ${hh}" style="width:100%" role="img" aria-hidden="true">`
  for (const r of [0, 0.25, 0.5, 0.75, 1]) {
    const y = base - r * (base - 20)
    g += `<line x1="34" y1="${y.toFixed(1)}" x2="${w - 8}" y2="${y.toFixed(1)}" stroke="${r === 0 ? 'rgba(0,0,0,.10)' : 'rgba(0,0,0,.05)'}"/>`
    g += `<text x="4" y="${(y + 3.5).toFixed(1)}" font-size="10" fill="#8a8f98">${fmtNum(Math.round(max * r))}</text>`
  }
  series.forEach((s, i) => {
    const bh = Math.max(2, (s.v / max) * (base - 20))
    const x = 42 + i * step
    const bw = Math.min(38, step * 0.55)
    g += `<rect x="${x.toFixed(1)}" y="${(base - bh).toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" rx="3" fill="${color}" opacity="${(0.5 + 0.5 * (s.v / max)).toFixed(2)}"/>`
    g += `<text x="${(x + bw / 2).toFixed(1)}" y="${(base - bh - 5).toFixed(1)}" text-anchor="middle" font-size="10" fill="#5f6570">${s.t ?? s.v}</text>`
    g += `<text x="${(x + bw / 2).toFixed(1)}" y="${hh - 9}" text-anchor="middle" font-size="10.5" fill="#5f6570">${s.k}</text>`
  })
  return `${g}</svg>`
}

export function bi0SvgLine(series: ChartPoint[]): string {
  const w = 420
  const hh = 190
  const base = hh - 28
  const top = 20
  const lx = 34
  const rx = w - 8
  const max = Math.max(...series.map((s) => s.v), 1)
  const n = series.length
  const span = rx - lx
  const step = n > 1 ? span / (n - 1) : 0
  const px = (i: number) => lx + i * step
  const py = (v: number) => base - (v / max) * (base - top)
  let g = `<svg class="bi0-chart-svg" viewBox="0 0 ${w} ${hh}" style="width:100%" role="img" aria-hidden="true">`
  for (const r of [0, 0.25, 0.5, 0.75, 1]) {
    const y = base - r * (base - top)
    g += `<line x1="${lx}" y1="${y.toFixed(1)}" x2="${rx}" y2="${y.toFixed(1)}" stroke="${r === 0 ? 'rgba(0,0,0,.10)' : 'rgba(0,0,0,.05)'}"/>`
    g += `<text x="4" y="${(y + 3.5).toFixed(1)}" font-size="10" fill="#8a8f98">${fmtNum(Math.round(max * r))}</text>`
  }
  const pts = series.map((s, i) => `${px(i).toFixed(1)},${py(s.v).toFixed(1)}`).join(' ')
  if (n > 1) {
    const area = `${px(0).toFixed(1)},${base} ${pts} ${px(n - 1).toFixed(1)},${base}`
    g += `<polygon points="${area}" fill="var(--blue)" opacity="0.07"/>`
  }
  g += `<polyline points="${pts}" fill="none" stroke="var(--blue)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>`
  series.forEach((s, i) => {
    const x = px(i)
    const y = py(s.v)
    g += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.6" fill="#fff" stroke="var(--blue)" stroke-width="2.2"/>`
    g += `<text x="${x.toFixed(1)}" y="${(y - 9).toFixed(1)}" text-anchor="middle" font-size="10" font-weight="600" fill="#1d1d1f">${s.t ?? fmtNum(s.v)}</text>`
    g += `<text x="${x.toFixed(1)}" y="${hh - 9}" text-anchor="middle" font-size="10.5" fill="#5f6570">${s.k}</text>`
  })
  return `${g}</svg>`
}

export function bi0SvgPie(series: ChartPoint[]): string {
  const total = series.reduce((a, s) => a + s.v, 0) || 1
  const colors = ['#0071e3', '#34c759', '#ff9f0a', '#ff3b30']
  const r = 58
  const cx = 80
  const cy = 80
  const circ = 2 * Math.PI * r
  let off = 0
  let g = `<svg class="bi0-chart-svg" viewBox="0 0 360 168" style="width:100%" role="img" aria-hidden="true">`
  g += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(0,0,0,.06)" stroke-width="30"/>`
  series.forEach((s, i) => {
    const len = (s.v / total) * circ
    g += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${colors[i % colors.length]}" stroke-width="30" stroke-dasharray="${len.toFixed(1)} ${(circ - len).toFixed(1)}" stroke-dashoffset="${(-off).toFixed(1)}" transform="rotate(-90 ${cx} ${cy})"/>`
    off += len
  })
  series.forEach((s, i) => {
    const y = 34 + i * 26
    g += `<rect x="176" y="${y - 9}" width="10" height="10" rx="2" fill="${colors[i % colors.length]}"/>`
    g += `<text x="194" y="${y}" font-size="11.5" fill="#5f6570">${s.k} · ${fmtNum(s.v)}</text>`
    g += `<text x="300" y="${y}" font-size="11.5" font-weight="600" fill="#1d1d1f">${((s.v / total) * 100).toFixed(1)}%</text>`
  })
  return `${g}</svg>`
}

export function parseNumeric(v: unknown): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  const n = parseFloat(String(v ?? '').replace(/[^\d.-]/g, ''))
  return Number.isFinite(n) ? n : 0
}

export function truncateLabel(text: string, max = 8): string {
  const s = String(text ?? '')
  return s.length > max ? `${s.slice(0, max)}…` : s
}

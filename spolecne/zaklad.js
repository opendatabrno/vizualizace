/* Společné funkce stránek webu: hlavička a patička z MODULY, formátování čísel, načítání dat,
   vyhledávání obce, malé grafy. Načítá se po spolecne/moduly.js. */
(() => {
const KOREN = document.currentScript.src.replace(/spolecne\/zaklad\.js.*$/, '');
const Q = new URLSearchParams(location.search);
if (Q.get('tema') === 'tmave' || Q.get('tema') === 'svetle') document.documentElement.dataset.tema = Q.get('tema');

const cis = v => v == null || !isFinite(v) ? '–' : Math.round(v).toLocaleString('cs-CZ');
const pct = (v, znam = true, des = 1) => v == null || !isFinite(v) ? '–' :
  (znam && v > 0 ? '+' : '') + (v * 100).toFixed(des).replace('.', ',').replace('-', '−') + ' %';
const rozdil = v => v == null || !isFinite(v) ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(Math.round(v)).toLocaleString('cs-CZ');
const kratce = v => v >= 1e6 ? (v / 1e6).toFixed(2).replace('.', ',') + ' mil.' : v >= 1e4 ? Math.round(v / 1e3) + ' tis.' :
  v >= 1e3 ? (v / 1e3).toFixed(1).replace('.', ',').replace(',0', '') + ' tis.' : String(Math.round(v));
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
const bezDiakritiky = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const znamenko = v => v > 0 ? 'plus' : v < 0 ? 'minus' : '';
const pekne = m => { const p = Math.pow(10, Math.floor(Math.log10(m))), r = m / p; return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 2.5 ? 2.5 : r <= 5 ? 5 : 10) * p };

const cache = {};
const nacti = u => cache[u] ??= fetch(KOREN + u, { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(u); return r.json() });

// stránka, ze které se jde na profil obce: téma (modul) → profil otevře jeho sekci
let tema = '';
function hlavicka(aktivni) {
  // vypnuté téma: jeho stránka odkáže na úvod, prvky s data-modul="id" zmizí ze všech stránek
  if (MODULY.some(m => m.id === aktivni) && !zapnuto(aktivni)) { location.replace(KOREN); return }
  document.querySelectorAll('[data-modul]').forEach(e => zapnuto(e.dataset.modul) || e.remove());
  tema = MODULY.some(m => m.id === aktivni) ? aktivni : aktivni === 'obec' ? null : '';
  const odkazy = [...MODULY.filter(m => m.stav === 'hotovo' && zapnuto(m.id)), ...STRANKY];
  const h = document.createElement('header');
  h.className = 'hlav';
  h.innerHTML = `<div class="obal"><a class="znak" href="${KOREN}"><i></i>Obyvatelé ČR v datech</a>
    <nav class="nav" aria-label="Hlavní navigace">${odkazy.map(m => `<a href="${KOREN}${m.adresa}"${m.id === aktivni ? ' aria-current="page"' : ''}>${
      m.barva ? `<span class="t" style="background:${m.barva}"></span>` : ''}${esc(m.nazev)}</a>`).join('')}</nav></div>`;
  document.body.prepend(h);
  const f = document.createElement('footer');
  f.className = 'paticka';
  f.innerHTML = `<div class="obal"><span>Otevřená data <a href="https://github.com/opendatabrno">opendatabrno</a> ·
    zdroje: MV ČR, ČSÚ · zdrojový kód <a href="https://github.com/opendatabrno/vizualizace">opendatabrno/vizualizace</a></span>
    <span>Data i grafy lze volně použít s uvedením zdroje (<a href="${KOREN}metodika/#citace">jak citovat</a>).</span></div>`;
  document.body.append(f);
}

/* adresa profilu obce; z tématu vede rovnou na jeho sekci, z profilu zachová otevřenou sekci */
function odkazObce(kod) {
  const kotva = tema ? '#' + tema : tema === null ? location.hash : '';
  return `${KOREN}obec/?kod=${kod}${kotva}`;
}

/* našeptávač obcí; po výběru přejde na profil obce (nebo zavolá vlastní funkci) */
function hledani(obal, { vyber, placeholder = 'Najít obec…' } = {}) {
  obal.classList.add('hledej');
  obal.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
    <input type="search" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-label="${esc(placeholder)}" placeholder="${esc(placeholder)}" autocomplete="off"><ul role="listbox"></ul>`;
  const inp = obal.querySelector('input'), ul = obal.querySelector('ul');
  let obce = null, nalez = [], i = -1;
  const jdi = kod => vyber ? vyber(kod) : (location.href = odkazObce(kod));
  inp.addEventListener('focus', () => obce || nacti('data/obce.json').then(d => {
    obce = d.obce.map(r => [...r, bezDiakritiky(r[1])]); kresli() }), { once: true });
  const kresli = () => {
    const q = bezDiakritiky(inp.value.trim());
    if (!obce || !q) { ul.innerHTML = ''; inp.setAttribute('aria-expanded', 'false'); return }
    const zac = [], jinde = [];
    for (const r of obce) { const p = r[4].indexOf(q); if (p === 0) zac.push(r); else if (p > 0) jinde.push(r); if (zac.length > 12) break }
    nalez = [...zac, ...jinde].slice(0, 12); i = nalez.length ? 0 : -1;
    ul.innerHTML = nalez.map((r, j) => `<li role="option" id="h${r[0]}" aria-selected="${j === i}" data-k="${r[0]}"><span>${esc(r[1])}</span><small>${esc(r[2])} · ${cis(r[3])} ob.</small></li>`).join('')
      || '<li aria-disabled="true"><span class="mut">Žádná obec neodpovídá</span></li>';
    inp.setAttribute('aria-expanded', 'true');
  };
  const oznac = () => ul.querySelectorAll('li').forEach((li, j) => li.setAttribute('aria-selected', j === i));
  inp.addEventListener('input', kresli);
  inp.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { i = Math.min(i + 1, nalez.length - 1); oznac(); e.preventDefault() }
    else if (e.key === 'ArrowUp') { i = Math.max(i - 1, 0); oznac(); e.preventDefault() }
    else if (e.key === 'Enter' && nalez[i]) { jdi(nalez[i][0]) }
    else if (e.key === 'Escape') { inp.value = ''; kresli() }
  });
  ul.addEventListener('mousedown', e => { const li = e.target.closest('li[data-k]'); if (li) jdi(li.dataset.k) });
  inp.addEventListener('blur', () => setTimeout(() => { ul.innerHTML = '' }, 150));
  return inp;
}

/* malý spojnicový graf (svg jako text) */
function spark(rada, barva = 'var(--acc)', { vyska = 46, sirka = 300, plocha = true, znacky = [] } = {}) {
  const v = rada.filter(x => x != null); if (v.length < 2) return '';
  const mn = Math.min(...v), mx = Math.max(...v), r = mx - mn || 1;
  const b = rada.map((x, j) => x == null ? null : [j / (rada.length - 1) * sirka, vyska - 4 - (x - mn) / r * (vyska - 8)]);
  const d = b.filter(Boolean).map((p, j) => (j ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('');
  const posl = b.filter(Boolean).at(-1);
  return `<svg class="spark" viewBox="0 0 ${sirka} ${vyska}" preserveAspectRatio="none" aria-hidden="true">
    ${znacky.map(j => `<line x1="${j / (rada.length - 1) * sirka}" x2="${j / (rada.length - 1) * sirka}" y1="0" y2="${vyska}" stroke="var(--line)" stroke-width="1" vector-effect="non-scaling-stroke"/>`).join('')}
    ${plocha ? `<path d="${d}L${sirka},${vyska}L0,${vyska}Z" fill="${barva}" opacity=".12"/>` : ''}
    <path d="${d}" fill="none" stroke="${barva}" stroke-width="2" vector-effect="non-scaling-stroke"/>
    <circle cx="${posl[0]}" cy="${posl[1]}" r="3" fill="${barva}"/></svg>`;
}

/* bublina u kurzoru */
let tipEl;
function tip(e, html) {
  tipEl ??= Object.assign(document.createElement('div'), { className: 'tip' });
  if (!tipEl.isConnected) document.body.append(tipEl);
  if (!html) { tipEl.style.display = 'none'; return }
  tipEl.innerHTML = html; tipEl.style.display = 'block';
  const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
  tipEl.style.left = Math.min(e.clientX + 14, innerWidth - w - 8) + 'px';
  tipEl.style.top = (e.clientY + h + 22 > innerHeight ? e.clientY - h - 12 : e.clientY + 16) + 'px';
}

/* postupně naběhne číslo (respektuje omezení animací) */
function nabeh(el, cil, ms = 900) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !isFinite(cil)) { el.textContent = cis(cil); return }
  const t0 = performance.now();
  const krok = t => { const p = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - p, 3); el.textContent = cis(cil * e); if (p < 1) requestAnimationFrame(krok) };
  requestAnimationFrame(krok);
}

// první rok, od kterého se počítají změny: v roce 2004 ještě nejsou v evidenci MV všichni cizinci
const OD = 2005;

window.Z = { OD, KOREN, zapnuto: id => zapnuto(id), Q, cis, pct, rozdil, kratce, esc, bezDiakritiky, znamenko, pekne, nacti, hlavicka, hledani, odkazObce, spark, tip, nabeh };
})();

"""Hranice územních jednotek ČR pro mapy (podklady/*.json).

Zdroj: RÚIAN, ČÚZK – výměnný formát „stát až ÚSC“ (ST_UKSG). Data ČÚZK jsou pod licencí CC BY 4.0.

    podklady/okresy.json         okresy (generalizované hranice; Praha jako kraj, v RÚIAN není okresem)
    podklady/obce.json           všechny obce (generalizované hranice) + čáry hranic okresů a krajů
    podklady/mestske_casti.json  městské části a obvody statutárních měst (původní hranice, zjednodušené)

Hranice se mění zřídka, proto se výsledek ukládá do repozitáře a skript se spouští ručně:
    python scripts/hranice.py            # stáhne poslední soubor (~100 MB)
    python scripts/hranice.py soubor.zip # použije stažený soubor

Souřadnice jsou v S-JTSK (Křovákovo zobrazení, EPSG:5514), které je pro ČR navržené, takže stačí
je posunout a zmenšit na souřadnice SVG. Zjednodušení je topologické: společná hranice dvou
jednotek se zjednoduší jednou, takže mezi nimi nevzniknou mezery.
"""
import io
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
PODKLADY = ROOT / "podklady"
URL = "https://vdp.cuzk.gov.cz/vymenny_format/soucasna/{d:%Y%m%d}_ST_UKSG.xml.zip"


def stahni():
    """Soubor se vydává k poslednímu dni měsíce; zkusí poslední tři měsíce."""
    d = date.today().replace(day=1) - timedelta(days=1)
    for _ in range(3):
        r = requests.get(URL.format(d=d), timeout=300)
        if r.ok:
            print(f"RÚIAN k {d}")
            return io.BytesIO(r.content)
        d = d.replace(day=1) - timedelta(days=1)
    raise SystemExit("Soubor RÚIAN ST_UKSG se nepodařilo stáhnout")


def potomek(el, nazev):
    return next((c for c in el if c.tag.endswith("}" + nazev)), None)


def nacti(zdroj):
    """Okresy, obce a městské části: {typ: {kód: {"nazev", "nadrazena", "prstence"}}}."""
    z = zipfile.ZipFile(zdroj)
    out = {"okres": {}, "obec": {}, "mc": {}}
    for _, el in ET.iterparse(z.open(z.namelist()[0]), events=("end",)):
        tag = el.tag.split("}")[1]
        if tag in ("Okres", "Vusc", "Obec", "Momc"):
            geom = potomek(el, "Geometrie")
            kod = potomek(el, "Kod")
            if geom is not None and kod is not None:
                prstence = []
                for p in geom.iter():
                    if p.tag.endswith("}posList"):
                        v = list(map(float, p.text.split()))
                        prstence.append([(v[i], v[i + 1]) for i in range(0, len(v), 2)])
                zaznam = {"nazev": potomek(el, "Nazev").text, "prstence": prstence}
                nuts = potomek(el, "NutsLau")
                if tag == "Okres":
                    out["okres"][nuts.text] = zaznam
                elif tag == "Vusc" and nuts.text == "CZ010":   # Praha není okresem
                    out["okres"]["CZ0100"] = zaznam
                elif tag == "Obec":
                    zaznam["nadrazena"] = nuts.text[:6]           # CZ0631569089 -> okres CZ0631
                    out["obec"][kod.text] = zaznam
                elif tag == "Momc":
                    zaznam["nadrazena"] = potomek(potomek(el, "Obec"), "Kod").text
                    out["mc"][kod.text] = zaznam
                el.clear()   # jen celé záznamy; vnořené odkazy (Obec v Momc) se čistit nesmí
    for typ, n in (("okres", 77), ("obec", 6000), ("mc", 100)):
        if len(out[typ]) < n:
            raise SystemExit(f"{typ}: čekal jsem aspoň {n} jednotek, je jich {len(out[typ])}")
    return out


def dp(body, tol):
    """Douglas–Peucker se zachováním krajních bodů (iterativně, oblouky bývají dlouhé)."""
    if len(body) < 3:
        return body
    drz = [False] * len(body)
    drz[0] = drz[-1] = True
    zasobnik = [(0, len(body) - 1)]
    while zasobnik:
        a, b = zasobnik.pop()
        (x1, y1), (x2, y2) = body[a], body[b]
        dx, dy = x2 - x1, y2 - y1
        d2 = dx * dx + dy * dy or 1e-9
        nej, idx = -1, 0
        for i in range(a + 1, b):
            x, y = body[i]
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / d2))
            e = (x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2
            if e > nej:
                nej, idx = e, i
        if nej > tol * tol:
            drz[idx] = True
            zasobnik += [(a, idx), (idx, b)]
    return [p for p, d in zip(body, drz) if d]


class Topologie:
    """Rozdělí prstence jednotek na oblouky mezi uzly a každý oblouk zjednoduší jednou."""

    def __init__(self, jednotky, prevod, tol):
        self.vlastnici = {}
        for kod, j in jednotky.items():
            for r in j["prstence"]:
                for b in r:
                    self.vlastnici.setdefault(b, set()).add(kod)
        self.oblouky = {}      # klíč -> (zjednodušené body, vlastníci)
        self.cesty = {}
        for kod, j in jednotky.items():
            cesta = []
            for r in j["prstence"]:
                r = r[:-1] if r[0] == r[-1] else r
                n, vl = len(r), self.vlastnici
                uzly = [i for i in range(n) if len(vl[r[i]]) >= 3
                        or vl[r[i]] != vl[r[i - 1]] or vl[r[i]] != vl[r[(i + 1) % n]]]
                if len(uzly) < 2:
                    uzly = [0, n // 2]
                body = []
                for a, b in zip(uzly, uzly[1:] + [uzly[0] + n]):
                    cast = [r[i % n] for i in range(a, b + 1)]
                    klic = tuple(cast) if cast[0] <= cast[-1] else tuple(reversed(cast))
                    if klic not in self.oblouky:
                        s = dp([prevod(x) for x in klic], tol)
                        self.oblouky[klic] = (s, frozenset.intersection(*(frozenset(vl[x]) for x in klic)))
                    s = self.oblouky[klic][0]
                    body += (s if tuple(cast) == klic else s[::-1])[:-1]
                body = [p for i, p in enumerate(body) if p != body[i - 1]]   # zaokrouhlením splynulé body
                if len(body) >= 3:
                    cesta.append(body)
            self.cesty[kod] = cesta

    def hranice(self, skupina):
        """Oblouky na hranici skupin (např. okresů): vlastníci z různých skupin, nebo jen jeden vlastník."""
        vnitrni, vnejsi = [], []
        for s, vl in self.oblouky.values():
            if len(vl) == 1:
                vnejsi.append(s)
            elif len({skupina(v) for v in vl}) > 1:
                vnitrni.append(s)
        return vnitrni, vnejsi


def d_abs(cesty):
    """Absolutní souřadnice (pro okresy.json, čitelné)."""
    return "".join("M" + "L".join(f"{x:g},{y:g}" for x, y in r) + "Z" for r in cesty)


def d_rel(cesty, uzavrit=True):
    """Celočíselné relativní souřadnice: výrazně kratší zápis pro tisíce obcí."""
    out = []
    for r in cesty:
        s = f"M{r[0][0]},{r[0][1]}"
        if len(r) > 1:
            s += "l" + " ".join(f"{b[0] - a[0]},{b[1] - a[1]}" for a, b in zip(r, r[1:]))
        out.append(s + ("z" if uzavrit else ""))
    return "".join(out)


def uloz(nazev, data):
    cesta = PODKLADY / nazev
    cesta.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  -> {cesta.relative_to(ROOT)} ({cesta.stat().st_size // 1024} kB)")


def main():
    zdroj = sys.argv[1] if len(sys.argv) > 1 else stahni()
    stav = zipfile.ZipFile(zdroj).namelist()[0][:8]  # 20261031_ST_UKSG.xml
    data = nacti(zdroj)
    zdroj_text = f"RÚIAN, © ČÚZK, stav k {stav[6:8]}. {stav[4:6]}. {stav[:4]}, CC BY 4.0"
    PODKLADY.mkdir(exist_ok=True)

    vse = [b for j in data["okres"].values() for r in j["prstence"] for b in r]
    minx, maxx = min(b[0] for b in vse), max(b[0] for b in vse)
    miny, maxy = min(b[1] for b in vse), max(b[1] for b in vse)

    def prevodnik(sirka, desetiny):
        k = sirka / (maxx - minx)   # S-JTSK: x roste na východ, y na sever
        return k, lambda b: (round((b[0] - minx) * k, desetiny), round((maxy - b[1]) * k, desetiny))

    # --- okresy: šířka 1000, jedno desetinné místo ---
    k, prevod = prevodnik(1000, 1)
    t = Topologie(data["okres"], prevod, 0.7)
    kraje, stat = t.hranice(lambda kod: kod[:5])
    uloz("okresy.json", {
        "zdroj": zdroj_text, "viewBox": f"0 0 1000 {round((maxy - miny) * k)}",
        "okresy": {kod: {"nazev": data["okres"][kod]["nazev"], "d": d_abs(t.cesty[kod])} for kod in sorted(t.cesty)},
        "kraje": d_abs_cary(kraje), "stat": d_abs_cary(stat)})

    # --- obce: šířka 4000, celá čísla (1 jednotka ≈ 120 m) ---
    k, prevod = prevodnik(4000, 0)
    obce = data["obec"]
    t = Topologie(obce, prevod, 3)
    okr, stat = t.hranice(lambda kod: obce[kod]["nadrazena"])
    kr, _ = t.hranice(lambda kod: obce[kod]["nadrazena"][:5])
    ramecky = {}
    for kod, cesta in t.cesty.items():
        kraj = obce[kod]["nadrazena"][:5]
        xs = [p[0] for r in cesta for p in r]
        ys = [p[1] for r in cesta for p in r]
        a = ramecky.setdefault(kraj, [1e9, 1e9, -1e9, -1e9])
        ramecky[kraj] = [min(a[0], min(xs)), min(a[1], min(ys)), max(a[2], max(xs)), max(a[3], max(ys))]
    uloz("obce.json", {
        "zdroj": zdroj_text, "viewBox": f"0 0 4000 {round((maxy - miny) * k)}",
        "obce": {kod: d_rel(t.cesty[kod]) for kod in sorted(t.cesty)},
        "okresy": d_rel(okr, False), "kraje": d_rel(kr, False), "stat": d_rel(stat, False),
        "ramecky": {kraj: [a[0], a[1], a[2] - a[0], a[3] - a[1]] for kraj, a in sorted(ramecky.items())}})

    # --- městské části: měřítko 1 jednotka = 10 m (města jsou malá, potřebují detail) ---
    k = 0.1
    def prevod(b):
        return (round((b[0] - minx) * k), round((maxy - b[1]) * k))
    mc = data["mc"]
    t = Topologie(mc, prevod, 2.0)
    mesta = {}
    for kod, cesta in t.cesty.items():
        m = mesta.setdefault(mc[kod]["nadrazena"], {"casti": {}, "box": [1e9, 1e9, -1e9, -1e9]})
        m["casti"][kod] = {"nazev": mc[kod]["nazev"], "d": d_rel(cesta)}
        xs = [p[0] for r in cesta for p in r]
        ys = [p[1] for r in cesta for p in r]
        a = m["box"]
        m["box"] = [min(a[0], min(xs)), min(a[1], min(ys)), max(a[2], max(xs)), max(a[3], max(ys))]
    obrysy = {}
    for s, vl in t.oblouky.values():   # obrys města = oblouky s jediným vlastníkem
        if len(vl) == 1:
            obrysy.setdefault(mc[next(iter(vl))]["nadrazena"], []).append(s)
    for kod_obce, m in mesta.items():
        a = m["box"]
        m["box"] = [a[0], a[1], a[2] - a[0], a[3] - a[1]]
        m["obrys"] = d_rel(obrysy.get(kod_obce, []), False)
    uloz("mestske_casti.json", {"zdroj": zdroj_text, "mesta": dict(sorted(mesta.items()))})


def d_abs_cary(useky):
    return "".join("M" + "L".join(f"{x:g},{y:g}" for x, y in u) for u in sorted(useky))


if __name__ == "__main__":
    main()

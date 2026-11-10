"""Hranice okresů a krajů ČR pro mapy: podklady/okresy.json.

Zdroj: RÚIAN, ČÚZK – výměnný formát „stát až ÚSC“ (ST_UKSG), generalizované hranice
okresů (Praha jako kraj, protože v RÚIAN není okresem). Data ČÚZK jsou pod licencí CC BY 4.0.

Hranice se mění zřídka, proto se výsledek ukládá do repozitáře a skript se spouští ručně:
    python scripts/hranice.py            # stáhne poslední soubor (~100 MB)
    python scripts/hranice.py soubor.zip # použije stažený soubor

Souřadnice jsou v S-JTSK (Křovákovo zobrazení, EPSG:5514), které je pro ČR navržené,
takže stačí je posunout a zmenšit na souřadnice SVG. Zjednodušení je topologické: společná
hranice dvou okresů se zjednoduší jednou, takže mezi okresy nevzniknou mezery.
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
VYSTUP = ROOT / "podklady" / "okresy.json"
URL = "https://vdp.cuzk.gov.cz/vymenny_format/soucasna/{d:%Y%m%d}_ST_UKSG.xml.zip"
SIRKA = 1000          # šířka mapy v jednotkách SVG
TOLERANCE = 0.7       # zjednodušení (Douglas–Peucker) v jednotkách SVG


def stahni():
    """Soubor se vydává k poslednímu dni měsíce; zkusí poslední tři měsíce."""
    d = date.today().replace(day=1) - timedelta(days=1)
    for _ in range(3):
        r = requests.get(URL.format(d=d), timeout=300)
        if r.ok:
            print(f"RÚIAN k {d}")
            return io.BytesIO(r.content), d
        d = d.replace(day=1) - timedelta(days=1)
    raise SystemExit("Soubor RÚIAN ST_UKSG se nepodařilo stáhnout")


def nacti(zdroj):
    """{kod_okresu: (název, [prstence])}; prstenec = [(x, y), …] v S-JTSK."""
    z = zipfile.ZipFile(zdroj)
    out = {}
    for _, el in ET.iterparse(z.open(z.namelist()[0]), events=("end",)):
        tag = el.tag.split("}")[1]
        if tag in ("Okres", "Vusc"):
            nuts = [c.text for c in el if c.tag.endswith("}NutsLau")]
            geom = [c for c in el if c.tag.endswith("}Geometrie")]
            if nuts and geom and (tag == "Okres" or nuts[0] == "CZ010"):
                kod = nuts[0] if tag == "Okres" else "CZ0100"
                nazev = next(c.text for c in el if c.tag.endswith("}Nazev"))
                prstence = []
                for p in geom[0].iter():
                    if p.tag.endswith("}posList"):
                        v = list(map(float, p.text.split()))
                        prstence.append([(v[i], v[i + 1]) for i in range(0, len(v), 2)])
                out[kod] = (nazev, prstence)
            el.clear()
        elif tag == "Obce":  # okresy a kraje jsou v souboru před obcemi
            break
    if len(out) != 77:
        raise SystemExit(f"Čekal jsem 77 okresů (vč. Prahy), je jich {len(out)}")
    return out


def dp(body, tol):
    """Douglas–Peucker se zachováním krajních bodů."""
    if len(body) < 3:
        return body
    (x1, y1), (x2, y2) = body[0], body[-1]
    dx, dy = x2 - x1, y2 - y1
    d2 = dx * dx + dy * dy or 1e-9
    nej, idx = -1, 0
    for i in range(1, len(body) - 1):
        x, y = body[i]
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / d2))
        e = (x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2
        if e > nej:
            nej, idx = e, i
    if nej <= tol * tol:
        return [body[0], body[-1]]
    return dp(body[:idx + 1], tol)[:-1] + dp(body[idx:], tol)


def main():
    if len(sys.argv) > 1:
        zdroj = sys.argv[1]
    else:
        zdroj, _ = stahni()
    stav = zipfile.ZipFile(zdroj).namelist()[0][:8]  # 20261031_ST_UKSG.xml
    okresy = nacti(zdroj)

    vse = [b for _, pr in okresy.values() for r in pr for b in r]
    minx, maxx = min(b[0] for b in vse), max(b[0] for b in vse)
    miny, maxy = min(b[1] for b in vse), max(b[1] for b in vse)
    k = SIRKA / (maxx - minx)
    vyska = round((maxy - miny) * k)

    def svg(b):  # S-JTSK: x roste na východ, y na sever
        return (round((b[0] - minx) * k, 1), round((maxy - b[1]) * k, 1))

    # kdo vlastní který bod: hranice mezi okresy sdílejí přesně stejné body
    vlastnici = {}
    for kod, (_, pr) in okresy.items():
        for r in pr:
            for b in r:
                vlastnici.setdefault(b, set()).add(kod)

    # prstence se rozdělí na oblouky v uzlech (kde se mění sousedství); oblouk se zjednoduší jednou
    oblouky = {}

    def oblouk(body):
        klic = tuple(body) if body[0] <= body[-1] else tuple(reversed(body))
        if klic not in oblouky:
            pts = [svg(b) for b in klic]
            oblouky[klic] = dp(pts, TOLERANCE)
        s = oblouky[klic]
        return s if tuple(body) == klic else list(reversed(s))

    cesty, hranice_kraju, hranice_statu = {}, set(), set()
    for kod, (nazev, pr) in okresy.items():
        d = []
        for r in pr:
            r = r[:-1] if r[0] == r[-1] else r
            n = len(r)
            uzly = [i for i in range(n) if len(vlastnici[r[i]]) >= 3
                    or vlastnici[r[i]] != vlastnici[r[i - 1]] or vlastnici[r[i]] != vlastnici[r[(i + 1) % n]]]
            if len(uzly) < 2:
                uzly = [0, n // 2]
            body = []
            for a, b in zip(uzly, uzly[1:] + [uzly[0] + n]):
                cast = [r[i % n] for i in range(a, b + 1)]
                s = oblouk(cast)
                body += s[:-1]
                # hranice kraje / státu: oblouk patří okresům z různých krajů, nebo jen jednomu okresu
                vl = set.intersection(*(vlastnici[x] for x in cast))
                if len(vl) == 1:
                    hranice_statu.add(tuple(s) if s[0] <= s[-1] else tuple(reversed(s)))
                elif len({v[:5] for v in vl}) > 1:
                    hranice_kraju.add(tuple(s) if s[0] <= s[-1] else tuple(reversed(s)))
            if len(body) >= 3:
                d.append("M" + "L".join(f"{x:g},{y:g}" for x, y in body) + "Z")
        cesty[kod] = {"nazev": nazev, "d": "".join(d)}

    def cara(useky):
        return "".join("M" + "L".join(f"{x:g},{y:g}" for x, y in u) for u in sorted(useky))

    VYSTUP.parent.mkdir(exist_ok=True)
    data = {"zdroj": f"RÚIAN, © ČÚZK, stav k {stav[6:8]}. {stav[4:6]}. {stav[:4]}, CC BY 4.0",
            "viewBox": f"0 0 {SIRKA} {vyska}", "okresy": dict(sorted(cesty.items())),
            "kraje": cara(hranice_kraju), "stat": cara(hranice_statu)}
    VYSTUP.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(cesty)} okresů, {sum(len(o) for o in oblouky.values())} bodů -> {VYSTUP} "
          f"({VYSTUP.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()

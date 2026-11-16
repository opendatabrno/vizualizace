"""Data pro vizualizace: stáhne hotové datové sady opendatabrno a připraví z nich malé JSON.

    python scripts/build_data.py                  # stáhne CSV z GitHubu
    python scripts/build_data.py --mistni ../     # CSV z lokálních klonů (../cizinci, ../obyvatele, ../zaci)

Výstup:
    cizinci/mapa.json   – podíl cizinců na obyvatelích po okresech + nejčastější státy
    cizinci/vyvoj.json  – měsíční řada za ČR, celkem a hlavní státy
    obyvatele/obce.json           – obyvatelé a cizinci ve všech obcích po letech
    obyvatele/mestske_casti.json  – totéž za městské části 8 statutárních měst
    zaci/obce.json      – děti v MŠ a žáci v ZŠ zřizovaných obcemi, po obcích a letech, a částka na žáka
    data/obce/{kod}.json  – všechny sloupce jedné obce po letech (profil obce, „statické API“)
    data/obce.json        – seznam obcí pro vyhledávání
    data/souhrn.json      – klíčová čísla za ČR pro úvodní stránku

Když se struktura nebo součty nesrovnají, skript skončí chybou (workflow pak web nenasadí
a zůstane poslední funkční verze).
"""
import io
import json
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/opendatabrno/{repo}/main/vystup/{soubor}"
TOP_OKRES = 8      # kolik nejčastějších států ukázat u okresu
TOP_VYVOJ = 12     # kolik největších států nabídnout v grafu vývoje jako tlačítka
MIN_VYVOJ = 100    # další státy jde přidat ze seznamu, pokud měly kdykoli aspoň tolik lidí

SLOUPCE = {
    ("cizinci", "cizinci_okresy.csv"): ["rok", "kod_okresu", "okres", "kod_kraje", "kraj", "cizinci_celkem",
                                        "cizinci_trvaly_pobyt", "cizinci_prechodny_pobyt",
                                        "cizinci_eu_ehp_ch", "cizinci_treti_zeme"],
    ("cizinci", "cizinci_okresy_staty.csv"): ["rok", "kod_okresu", "kod_statu", "statni_prislusnost",
                                              "cizinci_celkem"],
    ("cizinci", "cizinci_mesicne.csv"): ["rok", "mesic", "stav_k", "kod_statu", "statni_prislusnost", "skupina",
                                         "cizinci_celkem", "cizinci_trvaly_pobyt", "cizinci_prechodny_pobyt",
                                         "cizinci_docasna_ochrana"],
    ("obyvatele", "obyvatele_obce.csv"): ["rok", "kod_obce", "nazev_obce", "orp", "kod_okresu", "okres", "kod_kraje",
                                          "kraj", "obyvatele_celkem", "obyvatele_csu", "odhad_csu",
                                          "obcane_celkem", "obcane_muzi", "obcane_zeny",
                                          "cizinci_celkem", "cizinci_muzi", "cizinci_zeny", "cizinci_trvaly_pobyt",
                                          "cizinci_prechodny_pobyt", "cizinci_docasna_ochrana"],
    ("obyvatele", "obyvatele_mestske_casti.csv"): ["rok", "kod_obce", "nazev_obce", "kod_mc", "nazev_mc",
                                                   "obyvatele_celkem", "obcane_celkem", "cizinci_celkem",
                                                   "odhad_csu", "koef_obcane"],
    ("zaci", "zaci_obce.csv"): ["rok", "kod_obce", "nazev_obce", "kod_okresu", "ms_celkem", "zs_celkem", "celkem",
                                "odhad_prostredku_kc", "rok_rozpoctu"],
    ("zaci", "zaci_svazky_obci.csv"): ["rok", "nazev_svazku", "ms_celkem", "zs_celkem", "celkem"],
    ("zaci", "castka_na_zaka.csv"): ["rok", "prijemce", "castka_na_zaka_kc", "jednotka", "udaj", "objem_kc_odhad"],
}


class DataError(Exception):
    pass


def nacti(repo, soubor, mistni):
    if mistni:
        zdroj = Path(mistni) / repo / "vystup" / soubor
        print(f"  {zdroj}")
    else:
        url = RAW.format(repo=repo, soubor=soubor)
        print(f"  {url}")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        zdroj = io.BytesIO(r.content)
    chybi = SLOUPCE[(repo, soubor)]
    d = pd.read_csv(zdroj, encoding="utf-8-sig",
                    dtype={"kod_okresu": str, "kod_kraje": str, "kod_obce": str, "kod_mc": "Int64"},
                    keep_default_na=False, na_values=[""])
    chybi = [c for c in chybi if c not in d.columns]
    if chybi:
        raise DataError(f"{repo}/{soubor}: chybí sloupce {chybi}")
    return d


def kontrola(podminka, zprava):
    if not podminka:
        raise DataError(zprava)


def mapa(okresy, staty, obyv):
    okresy = okresy[okresy.kod_okresu.notna()]           # bez řádku „nezjištěno“
    staty = staty[staty.kod_okresu.notna()]
    # počty obyvatel MV jsou k 1. 1., cizinci k 31. 12. předchozího roku
    o = obyv.groupby(["rok", "kod_okresu"]).obyvatele_celkem.sum().reset_index()
    o["rok"] -= 1
    roky = sorted(set(okresy.rok) & set(o.rok))
    kontrola(len(roky) >= 5, f"málo společných let cizinců a obyvatel: {roky}")
    kody = sorted(okresy.kod_okresu.unique())
    kontrola(len(kody) == 77, f"čekal jsem 77 okresů, je jich {len(kody)}")
    chybi = set(kody) - set(o.kod_okresu)
    kontrola(not chybi, f"okresy bez počtu obyvatel: {sorted(chybi)}")

    s = staty.groupby(["rok", "kod_okresu"]).cizinci_celkem.sum()
    c = okresy.set_index(["rok", "kod_okresu"]).cizinci_celkem
    rozdil = (s - c).abs().max()
    kontrola(rozdil == 0, f"součet států v okresech nesedí na tabulku okresů (max. rozdíl {rozdil})")

    nazvy = staty.drop_duplicates("kod_statu", keep="last").set_index("kod_statu").statni_prislusnost
    ci = okresy.set_index(["kod_okresu", "rok"])
    oi = o.set_index(["kod_okresu", "rok"]).obyvatele_celkem
    st = staty[staty.rok.isin(roky)].sort_values("cizinci_celkem", ascending=False)
    top = {k: g.head(TOP_OKRES)[["kod_statu", "cizinci_celkem"]].values.tolist()
           for k, g in st.groupby(["kod_okresu", "rok"])}
    out_okresy, pouzite = {}, set()
    for kod in kody:
        info = okresy[okresy.kod_okresu == kod].iloc[-1]
        radek = {"n": info.okres, "kraj": info.kraj, "c": [], "o": [], "trv": [], "eu": [], "top": []}
        for r in roky:
            x = ci.loc[(kod, r)]
            radek["c"].append(int(x.cizinci_celkem))
            radek["o"].append(int(oi.loc[(kod, r)]))
            radek["trv"].append(int(x.cizinci_trvaly_pobyt))
            radek["eu"].append(int(x.cizinci_eu_ehp_ch))
            t = [[k, int(v)] for k, v in top.get((kod, r), [])]
            pouzite |= {k for k, _ in t}
            radek["top"].append(t)
        out_okresy[kod] = radek
    cr_c = [int(okresy[okresy.rok == r].cizinci_celkem.sum()) for r in roky]
    cr_o = [int(o[o.rok == r].obyvatele_celkem.sum()) for r in roky]
    return {"roky": roky, "okresy": out_okresy, "cr": {"c": cr_c, "o": cr_o},
            "staty": {k: nazvy[k] for k in sorted(pouzite)}}


def vyvoj(m):
    g = m.groupby("stav_k")
    celkem = g[["cizinci_celkem", "cizinci_trvaly_pobyt", "cizinci_prechodny_pobyt"]].sum()
    celkem["eu"] = m[m.skupina != "třetí země"].groupby("stav_k").cizinci_celkem.sum()
    celkem["docasna"] = g.cizinci_docasna_ochrana.sum(min_count=1)
    kontrola((celkem.cizinci_trvaly_pobyt + celkem.cizinci_prechodny_pobyt == celkem.cizinci_celkem).all(),
             "měsíční řada: trvalý + přechodný ≠ celkem")
    # souvislá řada měsíců; měsíce, které ve zdroji chybí (10/2010), zůstanou prázdné (mezera v grafu)
    obdobi = pd.period_range(celkem.index.min()[:7], celkem.index.max()[:7], freq="M")
    mesice = [str(p) for p in obdobi]
    celkem.index = celkem.index.str[:7]
    celkem = celkem.reindex(mesice)
    chybi = [p for p in mesice if pd.isna(celkem.loc[p, "cizinci_celkem"])]
    kontrola(len(chybi) <= 3, f"měsíční řadě chybí moc měsíců: {chybi}")

    # státy s největším počtem kdykoli v řadě (Ukrajina, Slovensko, Vietnam …)
    maxima = m.groupby("kod_statu").cizinci_celkem.max().sort_values(ascending=False)
    vybrane = [k for k in maxima.index if k != "XXX" and maxima[k] >= MIN_VYVOJ]
    hlavni = set(vybrane[:TOP_VYVOJ])
    nazvy = m.drop_duplicates("kod_statu", keep="last").set_index("kod_statu").statni_prislusnost
    p = m[m.kod_statu.isin(vybrane)].pivot_table(index="stav_k", columns="kod_statu",
                                                  values="cizinci_celkem", aggfunc="sum")
    p.index = p.index.str[:7]
    p = p.reindex(mesice)

    def rada(s):
        return [None if pd.isna(v) else int(v) for v in s]

    posledni = m[m.stav_k == m.stav_k.max()].set_index("kod_statu").cizinci_celkem
    vybrane.sort(key=lambda k: -posledni.get(k, 0))
    return {"mesice": mesice, "chybi": chybi,
            "celkem": rada(celkem.cizinci_celkem), "trvaly": rada(celkem.cizinci_trvaly_pobyt),
            "prechodny": rada(celkem.cizinci_prechodny_pobyt), "eu": rada(celkem.eu.fillna(0).where(
                celkem.cizinci_celkem.notna())), "docasna": rada(celkem.docasna),
            "staty": [{"kod": k, "n": nazvy[k], "v": rada(p[k]), **({"hlavni": 1} if k in hlavni else {})}
                      for k in vybrane]}


def obce(o):
    """Každá obec: název, okres, obyvatelé a cizinci po letech (občané = obyvatelé − cizinci)."""
    kontrola((o.obcane_celkem + o.cizinci_celkem == o.obyvatele_celkem).all(),
             "obyvatelé obcí: občané + cizinci ≠ obyvatelé")
    roky = sorted(o.rok.unique())
    kontrola(len(roky) >= 5 and roky == list(range(roky[0], roky[-1] + 1)), f"obce: chybí roky {roky}")
    posledni = o[o.rok == roky[-1]]
    kontrola(len(posledni) > 6000, f"obce: v roce {roky[-1]} jen {len(posledni)} obcí")
    kontrola(posledni.kod_obce.is_unique, "obce: kód obce je v roce víckrát")
    # okres z posledního roku, kde ho obec má (vojenské újezdy ho v některých letech nemají)
    okres = o.dropna(subset=["kod_okresu"]).sort_values("rok").groupby("kod_obce").last()
    p = o.pivot_table(index="kod_obce", columns="rok", values=["obyvatele_celkem", "cizinci_celkem"])
    out = {}
    for kod, r in posledni.set_index("kod_obce").iterrows():
        def rada(sl):
            return [None if pd.isna(p.at[kod, (sl, y)]) else int(p.at[kod, (sl, y)]) for y in roky]
        out[kod] = [r.nazev_obce, okres.kod_okresu.get(kod, "") or "", rada("obyvatele_celkem"), rada("cizinci_celkem")]
    okresy = okres.drop_duplicates("kod_okresu").set_index("kod_okresu").okres.sort_index().to_dict()
    kraje = okres.drop_duplicates("kod_kraje").set_index("kod_kraje").kraj.sort_index().to_dict()
    cr = o.groupby("rok")[["obyvatele_celkem", "cizinci_celkem"]].sum()
    return {"roky": [int(y) for y in roky], "obce": out, "okresy": okresy, "kraje": kraje,
            "cr": [cr.obyvatele_celkem.astype(int).tolist(), cr.cizinci_celkem.astype(int).tolist()]}


def mestske_casti(m, o):
    """Městské části: stejné řady jako obce; součet MČ (bez neurčených) se ověří proti obci."""
    roky = sorted(m.rok.unique())
    soucet = m.groupby(["rok", "kod_obce"]).obyvatele_celkem.sum()
    obec = o.set_index(["rok", "kod_obce"]).obyvatele_celkem.reindex(soucet.index)
    # MV uvádí MČ a obce v drobně odlišných součtech (Praha do 2021 o stovky osob, viz kontrola_mc.csv
    # v repozitáři obyvatele); hlídá se jen, že rozdíl nepřesáhne 0,5 %
    rozdil = ((soucet - obec).abs() / obec).max()
    kontrola(rozdil < 0.005, f"městské části: součet MČ nesedí na obec (max. rozdíl {rozdil:.2%})")
    m = m[m.kod_mc.notna()]
    p = m.pivot_table(index="kod_mc", columns="rok", values=["obyvatele_celkem", "cizinci_celkem"])
    out = {}
    for kod_obce, g in m.sort_values("rok").groupby("kod_obce"):
        posl = g.drop_duplicates("kod_mc", keep="last")
        casti = {}
        for _, r in posl.iterrows():
            k = int(r.kod_mc)
            casti[str(k)] = [r.nazev_mc] + [[None if pd.isna(p.at[k, (sl, y)]) else int(p.at[k, (sl, y)])
                                             for y in roky] for sl in ("obyvatele_celkem", "cizinci_celkem")]
        out[kod_obce] = {"nazev": posl.nazev_obce.iloc[-1], "casti": casti}
    return {"roky": [int(y) for y in roky], "mesta": out}


def zaci(z, sv, castka, obyv):
    """Děti v MŠ a žáci v ZŠ zřizovaných obcemi (stav k 30. 9.) a částka na žáka ze sdílených daní."""
    roky = sorted(int(y) for y in z.rok.unique())
    kontrola(len(roky) >= 5 and roky == list(range(roky[0], roky[-1] + 1)), f"žáci: chybí roky {roky}")
    for r in roky:
        n = int((z.rok == r).sum())
        kontrola(n > 3000, f"žáci: v roce {r} jen {n} obcí")
    kontrola(not z.duplicated(["rok", "kod_obce"]).any(), "žáci: obec je v roce víckrát")
    kontrola((z.ms_celkem + z.zs_celkem <= z.celkem).all(), "žáci: MŠ + ZŠ > celkem")
    nezname = set(z.kod_obce) - set(obyv.kod_obce)
    kontrola(not nezname, f"žáci: obce, které nejsou v sadě obyvatel: {sorted(nezname)[:10]}")

    p = z.pivot_table(index="kod_obce", columns="rok", values=["ms_celkem", "zs_celkem", "celkem", "odhad_prostredku_kc"])
    posl = z.sort_values("rok").drop_duplicates("kod_obce", keep="last").set_index("kod_obce")

    def rada(kod, sl):
        return [None if (sl, y) not in p.columns or pd.isna(p.at[kod, (sl, y)]) else int(p.at[kod, (sl, y)]) for y in roky]

    obce = {kod: [r.nazev_obce, r.kod_okresu if isinstance(r.kod_okresu, str) else "",
                  rada(kod, "ms_celkem"), rada(kod, "zs_celkem"), rada(kod, "celkem"), rada(kod, "odhad_prostredku_kc")]
            for kod, r in posl.iterrows()}
    g = z.groupby("rok")
    s = sv.groupby("rok").celkem.sum().reindex(roky)
    c = castka[castka.prijemce == "obce"].sort_values("rok")
    return {"roky": roky, "obce": obce,
            "cr": {"ms": g.ms_celkem.sum().astype(int).tolist(), "zs": g.zs_celkem.sum().astype(int).tolist(),
                   "celkem": g.celkem.sum().astype(int).tolist(),
                   "svazky": [None if pd.isna(v) else int(v) for v in s],
                   "obci": g.size().astype(int).tolist(),
                   "prostredky": [None if pd.isna(v) else int(v) for v in g.odhad_prostredku_kc.sum(min_count=1)]},
            "castka": {"roky": c.rok.astype(int).tolist(), "kc": c.castka_na_zaka_kc.astype(int).tolist(),
                       "jednotka": c.jednotka.tolist(), "udaj": c.udaj.tolist()}}


SLOUPCE_PROFIL = {
    "obyvatele": "obyvatele_celkem", "obcane": "obcane_celkem", "obcane_muzi": "obcane_muzi",
    "obcane_zeny": "obcane_zeny", "cizinci": "cizinci_celkem", "cizinci_muzi": "cizinci_muzi",
    "cizinci_zeny": "cizinci_zeny", "cizinci_trvaly": "cizinci_trvaly_pobyt",
    "cizinci_prechodny": "cizinci_prechodny_pobyt", "docasna_ochrana": "cizinci_docasna_ochrana",
    "csu": "obyvatele_csu", "odhad_csu": "odhad_csu",
}


def profily(o, mc, z):
    """Jeden JSON na obec se všemi řadami + seznam obcí pro vyhledávání."""
    roky = sorted(int(y) for y in o.rok.unique())
    cil = ROOT / "data" / "obce"
    cil.mkdir(parents=True, exist_ok=True)
    for f in cil.glob("*.json"):
        f.unlink()
    mc = mc[mc.kod_mc.notna()]
    mesta = {k: g for k, g in mc.groupby("kod_obce")}
    roky_z = sorted(int(y) for y in z.rok.unique())
    skoly = {k: g.set_index("rok").reindex(roky_z) for k, g in z.groupby("kod_obce")}
    seznam = []
    for kod, g in o.groupby("kod_obce"):
        g = g.set_index("rok").reindex(roky)
        posl = g.dropna(subset=["nazev_obce"]).iloc[-1]
        radek = {"kod": kod, "nazev": posl.nazev_obce, "orp": posl.orp if isinstance(posl.orp, str) else None,
                 "kod_okresu": posl.kod_okresu if isinstance(posl.kod_okresu, str) else None,
                 "okres": posl.okres if isinstance(posl.okres, str) else None,
                 "kod_kraje": posl.kod_kraje if isinstance(posl.kod_kraje, str) else None,
                 "kraj": posl.kraj if isinstance(posl.kraj, str) else None, "roky": roky}
        for k, sl in SLOUPCE_PROFIL.items():
            radek[k] = [None if pd.isna(v) else int(v) for v in g[sl]]
        if kod in mesta:
            m = mesta[kod].sort_values("rok")
            radek["mestske_casti"] = [
                {"kod": int(k), "nazev": h.nazev_mc.iloc[-1],
                 "obyvatele": [None if pd.isna(v) else int(v) for v in h.set_index("rok").obyvatele_celkem.reindex(roky)],
                 "odhad_csu": [None if pd.isna(v) else int(v) for v in h.set_index("rok").odhad_csu.reindex(roky)],
                 "koef_obcane": None if pd.isna(h.koef_obcane.iloc[-1]) else float(h.koef_obcane.iloc[-1])}
                for k, h in m.groupby("kod_mc")]
        if kod in skoly:
            h = skoly[kod]
            radek["zaci"] = {"roky": roky_z, **{k: [None if pd.isna(v) else int(v) for v in h[sl]] for k, sl in
                             (("ms", "ms_celkem"), ("zs", "zs_celkem"), ("celkem", "celkem"),
                              ("prostredky", "odhad_prostredku_kc"))}}
        (cil / f"{kod}.json").write_text(json.dumps(radek, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if posl.name == roky[-1]:
            seznam.append([kod, posl.nazev_obce, radek["okres"] or "", radek["obyvatele"][-1]])
    kontrola(len(seznam) > 6000, f"profily: jen {len(seznam)} obcí")
    print(f"  -> data/obce/*.json ({len(list(cil.glob('*.json')))} souborů)")
    seznam.sort(key=lambda r: -(r[3] or 0))
    uloz({"roky": roky, "obce": seznam}, ROOT / "data" / "obce.json")


def souhrn(o, okresy, mesicne, zac):
    """Klíčová čísla za ČR pro úvodní stránku a moduly."""
    cr = o.groupby("rok")[["obyvatele_celkem", "obcane_celkem", "cizinci_celkem", "cizinci_docasna_ochrana",
                           "odhad_csu"]].sum(min_count=1)
    roky = [int(y) for y in cr.index]
    m = mesicne.groupby("stav_k").cizinci_celkem.sum()
    ok = okresy.groupby("rok").cizinci_celkem.sum()
    uloz({"obyvatele": {"roky": roky, "obyvatele": cr.obyvatele_celkem.astype(int).tolist(),
                        "obcane": cr.obcane_celkem.astype(int).tolist(),
                        "cizinci": cr.cizinci_celkem.astype(int).tolist(),
                        "docasna_ochrana": cr.cizinci_docasna_ochrana.astype(int).tolist(),
                        "odhad_csu": [None if pd.isna(v) else int(v) for v in cr.odhad_csu],
                        "obci": int((o.rok == roky[-1]).sum())},
          "cizinci": {"roky": [int(y) for y in ok.index], "celkem": ok.astype(int).tolist(),
                      "posledni_mesic": m.index.max(), "posledni_pocet": int(m.iloc[-1]),
                      "mesicne": [int(v) for v in m.iloc[-60:]], "mesice": [str(x)[:7] for x in m.index[-60:]]},
          "zaci": {"roky": zac["roky"], **{k: zac["cr"][k] for k in ("ms", "zs", "celkem", "obci")},
                   **posledni_castka(zac["castka"])}},
         ROOT / "data" / "souhrn.json")


def posledni_castka(c):
    """Poslední částka na skutečného žáka (předběžné částky na „přepočteného žáka“ od 2026 mají jinou jednotku)."""
    j = max(i for i, u in enumerate(c["jednotka"]) if u == "žák")
    return {"castka_rok": c["roky"][j], "castka": c["kc"][j]}


def uloz(data, cesta):
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  -> {cesta.relative_to(ROOT)} ({cesta.stat().st_size // 1024} kB)")


def main():
    mistni = sys.argv[sys.argv.index("--mistni") + 1] if "--mistni" in sys.argv else None
    print("Načítám datové sady:")
    okresy = nacti("cizinci", "cizinci_okresy.csv", mistni)
    staty = nacti("cizinci", "cizinci_okresy_staty.csv", mistni)
    mesicne = nacti("cizinci", "cizinci_mesicne.csv", mistni)
    obyv = nacti("obyvatele", "obyvatele_obce.csv", mistni)
    mc = nacti("obyvatele", "obyvatele_mestske_casti.csv", mistni)
    z = nacti("zaci", "zaci_obce.csv", mistni)
    sv = nacti("zaci", "zaci_svazky_obci.csv", mistni)
    castka = nacti("zaci", "castka_na_zaka.csv", mistni)
    print("Připravuji data:")
    uloz(mapa(okresy, staty, obyv), ROOT / "cizinci" / "mapa.json")
    uloz(vyvoj(mesicne), ROOT / "cizinci" / "vyvoj.json")
    uloz(obce(obyv), ROOT / "obyvatele" / "obce.json")
    uloz(mestske_casti(mc, obyv), ROOT / "obyvatele" / "mestske_casti.json")
    zac = zaci(z, sv, castka, obyv)
    uloz(zac, ROOT / "zaci" / "obce.json")
    profily(obyv, mc, z)
    souhrn(obyv, okresy, mesicne, zac)


if __name__ == "__main__":
    try:
        main()
    except DataError as e:
        print(f"CHYBA DAT: {e}", file=sys.stderr)
        sys.exit(1)

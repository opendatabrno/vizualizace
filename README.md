# Obyvatelé ČR v datech

Web nad otevřenými datovými sadami [opendatabrno](https://github.com/opendatabrno): rozcestník,
témata (obyvatelé, cizinci), profil každé obce, metodika a grafy k vložení na jiné weby.
Cílová skupina jsou obce, odborná veřejnost a hackathony na data.brno.cz.

- **Web:** https://opendatabrno.github.io/vizualizace/
- **Datové sady:** [obyvatelé](https://github.com/opendatabrno/obyvatele) · [cizinci](https://github.com/opendatabrno/cizinci)

Data v repozitáři nejsou: při každém nasazení se stáhnou hotové datové sady a připraví se z nich
malé soubory pro stránky.

## Stránky

| Adresa | Co obsahuje |
|---|---|
| `/` | rozcestník: vyhledání obce, karty témat, klíčová čísla, odkazy na metodiku a data |
| `obyvatele/` | téma Obyvatelé: mapa obcí, žebříčky, městské části |
| `cizinci/` | téma Cizinci: měsíční vývoj, státy, okresy |
| `obec/?kod=582786` | profil obce: vývoj, srovnání s okresem, krajem a podobnými obcemi, pořadí, složení, cizinci v okrese, MV × ČSÚ, městské části, kód pro vložení |
| `metodika/` | datové sady ke stažení, pojmy, které číslo použít, zlomy, aktualizace, adresy pro vývojáře, citace |
| `vlozit/` | galerie grafů s kódem pro vložení (iframe) |
| `data/obce/{kod}.json` | všechny řady jedné obce (statické API) |
| `data/obce.json`, `data/souhrn.json` | seznam obcí pro vyhledávání, klíčová čísla za ČR |

## Jak přidat téma (modul)

Úvodní stránka, navigace i seznam datových sad v metodice se skládají ze seznamu
[`spolecne/moduly.js`](spolecne/moduly.js). Nové téma, např. „Děti“:

1. Přidej položku do `MODULY` (vzor je v souboru zakomentovaný). S `stav: 'pripravujeme'` se na úvodu
   ukáže jen karta „připravujeme“ a téma není v navigaci.
2. Vytvoř složku se stránkou tématu (vzor `obyvatele/index.html`: načte `spolecne/styl.css`,
   `spolecne/moduly.js`, `spolecne/zaklad.js` a zavolá `Z.hlavicka('id')`).
3. Data připrav v `scripts/build_data.py`; pokud má téma klíčové číslo na úvod, přidej ho do `data/souhrn.json`
   a do funkce `souhrn` v položce modulu.
4. Přepni `stav` na `'hotovo'`. Nasazení (`pages.yml`) kopíruje všechny složky, upravovat ho netřeba.

Společné funkce (`spolecne/zaklad.js`, objekt `Z`): formátování čísel (`cis`, `pct`, `kratce`),
načítání dat (`nacti`), hlavička a patička (`hlavicka`), vyhledávání obce (`hledani`), malý graf (`spark`),
bublina (`tip`).

## Grafy k vložení

Samostatné stránky `obyvatele/graf.html` a `cizinci/graf.html` fungují bez zbytku webu a jsou určené
k vložení jako iframe. Starší adresy `obyvatele/?graf=…` a `cizinci/?graf=…` se na ně přesměrují.

| Adresa | Co ukazuje |
|---|---|
| `cizinci/graf.html?graf=mapa` | mapa okresů: podíl cizinců na obyvatelích k 31. 12. (od 2013), po kliknutí nejčastější státy |
| `cizinci/graf.html?graf=vyvoj` | měsíční vývoj za ČR od 2007, celkem podle pobytu nebo podle států, se zlomy v řadě |
| `obyvatele/graf.html?graf=mapa` | mapa všech obcí: změna obyvatel, změna občanů ČR, podíl cizinců |
| `obyvatele/graf.html?graf=mesto&mesto=582786` | totéž za městské části 8 statutárních měst |
| `obyvatele/graf.html?graf=obec&obec=582786` | sloupcový graf jedné obce po letech |

### Parametry v adrese

| Parametr | Graf | Význam |
|---|---|---|
| `nadpis=0` | všechny | skryje nadpis |
| `ovladani=0` | všechny | skryje ovládací prvky |
| `tema=svetle`, `tema=tmave` | všechny | vynutí barevný režim (jinak podle zařízení) |
| `rok=2025` | mapa | rok |
| `okres=CZ0642` | mapa | vybraný okres (kód NUTS/LAU, Praha `CZ0100`); výchozí Brno-město |
| `ukazatel=pocet` | mapa | počet cizinců místo podílu |
| `rezim=staty` | vývoj | čáry podle států místo celku |
| `staty=UKR,SVK,VNM` | vývoj | vybrané státy (kódy ISO 3166-1 alpha-3) |
| `od=2015` | vývoj | začátek osy |
| `osa=log` | vývoj | logaritmická osa (jen podle států) |
| `ukazatel=obcane`, `ukazatel=cizinci` | obce, města | změna občanů ČR / podíl cizinců místo změny obyvatel |
| `od=2005`, `do=2026` | obce, města | roky, mezi kterými se počítá změna (výchozí od 2005, data od 2004) |
| `kraj=CZ064` | obce | přiblíží kraj (kód NUTS) |
| `obec=582786` | obce, obec | vybraná obec (kód ČSÚ) |
| `mesto=582786`, `mc=550973` | města | město (kód obce) a vybraná městská část |

Graf si stav ovládání zapisuje do adresy, takže stačí nastavit, co chcete, a adresu zkopírovat.

Příklad vložení:

```html
<iframe src="https://opendatabrno.github.io/vizualizace/cizinci/graf.html?graf=mapa&okres=CZ0642&nadpis=0"
        width="100%" height="640" style="border:0" loading="lazy" title="Cizinci v okresech"></iframe>
```

## Aktualizace dat

Workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) sestaví data a nasadí web při každém
pushi do `main`, každé úterý ráno, ručně a na požádání z datového repozitáře (`repository_dispatch` typu
`data-aktualizovana`).

`scripts/build_data.py` stáhne CSV z `raw.githubusercontent.com` a zkontroluje sloupce, počet okresů a obcí,
součty (státy v okresech, občané + cizinci = obyvatelé, městské části proti obci). Když něco nesedí, skončí
chybou, web se nenasadí a zůstane poslední funkční verze.

Jednorázově: GitHub → Settings → Pages → Source: **GitHub Actions**.

## Hranice

Zjednodušené hranice připravené jako cesty SVG ve složce [`podklady/`](podklady/):

| Soubor | Obsah | Velikost |
|---|---|---|
| `okresy.json` | 77 okresů (Praha jako kraj) a čáry hranic krajů | 194 kB |
| `obce.json` | všech ~6 260 obcí, čáry hranic okresů a krajů, rámečky krajů pro přiblížení | 1,6 MB (gzip ~400 kB) |
| `mestske_casti.json` | městské části a obvody 8 statutárních měst a obrysy měst | 111 kB |

Zdroj: **RÚIAN, © ČÚZK**, výměnný formát „stát až ÚSC“ (generalizované hranice okresů a obcí,
původní hranice městských částí), licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.cs).
Praha je v RÚIAN krajem, ne okresem, proto je v mapě okresů použita hranice kraje Hlavní město Praha.

Hranice se mění zřídka, soubor se proto ukládá do repozitáře a obnovuje ručně:

```bash
python scripts/hranice.py
```

(stáhne ~100 MB z vdp.cuzk.gov.cz; zjednodušení je topologické, takže mezi okresy nevzniknou mezery)

## Místní náhled

```bash
pip install -r requirements.txt
```

```bash
python scripts/build_data.py
```

```bash
python -m http.server
```

Pak otevřete http://localhost:8000/. Stránky načítají JSON, přes `file://` nefungují. S lokálními klony
datových repozitářů vedle tohoto jde data sestavit bez stahování: `python scripts/build_data.py --mistni ..`.

## Licence

Kód: MIT (viz [LICENSE](LICENSE)). Hranice: © ČÚZK, CC BY 4.0. Data: podle zdrojových datových sad.

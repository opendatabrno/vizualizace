# Vizualizace dat opendatabrno

Interaktivní grafy nad datovými sadami [opendatabrno](https://github.com/opendatabrno), připravené
k vložení na web jako iframe. Data v tomto repozitáři nejsou: při každém nasazení se stáhnou hotové
datové sady z jejich repozitářů a připraví se z nich malé soubory pro grafy.

- **Web:** https://opendatabrno.github.io/vizualizace/ – přehled grafů a kód pro vložení
- **Datové sady:** [cizinci](https://github.com/opendatabrno/cizinci) ·
  [obyvatelé](https://github.com/opendatabrno/obyvatele)

## Grafy

### Cizinci s povoleným pobytem (`cizinci/`)

| Adresa | Co ukazuje |
|---|---|
| `cizinci/?graf=mapa` | mapa okresů: podíl cizinců na obyvatelích k 31. 12. (od 2013), posuvník po letech, po kliknutí na okres nejčastější státy a vývoj podílu |
| `cizinci/?graf=vyvoj` | měsíční vývoj za celou ČR od ledna 2007: celkem podle druhu pobytu, nebo podle států; očíslované zlomy v řadě (krize 2009, změna evidence 12/2011, brexit, válka na Ukrajině, konec neprodloužených dočasných ochran) |

Podíl na obyvatelích = cizinci s povoleným pobytem k 31. 12. / informativní počet obyvatel MV
(občané ČR + cizinci) k 1. 1. následujícího roku, sečtený z obcí za okres. Od roku 2022 jsou
v počtech i lidé s dočasnou ochranou. Říjen 2010 ve zdroji chybí, graf vývoje ho ukazuje jako mezeru.

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

Graf si stav ovládání zapisuje do adresy, takže stačí nastavit, co chcete, a adresu zkopírovat.

Příklad vložení:

```html
<iframe src="https://opendatabrno.github.io/vizualizace/cizinci/?graf=mapa&okres=CZ0642&nadpis=0"
        width="100%" height="640" style="border:0" loading="lazy" title="Cizinci v okresech"></iframe>
```

## Aktualizace dat

Workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) sestaví data a nasadí web:

- při každém pushi do `main`,
- každé úterý ráno (datové sady se aktualizují v pondělí),
- ručně (Actions → Run workflow),
- na požádání z jiného repozitáře (`repository_dispatch` typu `data-aktualizovana`).

`scripts/build_data.py` stáhne CSV z `raw.githubusercontent.com`, zkontroluje sloupce, počet okresů
a to, že součet států v okresech sedí na tabulku okresů. Když něco nesedí, skončí chybou, web se
nenasadí a zůstane poslední funkční verze.

### Jednorázové nastavení repozitáře

GitHub → Settings → Pages → Build and deployment → Source: **GitHub Actions**.

## Hranice okresů

[`podklady/okresy.json`](podklady/okresy.json) jsou zjednodušené hranice okresů a krajů ČR připravené
jako cesty SVG. Zdroj: **RÚIAN, © ČÚZK**, výměnný formát „stát až ÚSC“ (generalizované hranice),
licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.cs). Praha je v RÚIAN krajem,
ne okresem, proto je použita hranice kraje Hlavní město Praha.

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

Pak otevřete http://localhost:8000/. Stránky načítají JSON, takže přes `file://` nefungují.
S lokálními klony datových repozitářů vedle tohoto (`../cizinci`, `../obyvatele`) jde data sestavit
i bez stahování: `python scripts/build_data.py --mistni ..`.

## Soubory

| Soubor | Účel |
|---|---|
| `index.html` | přehled grafů s kódem pro vložení |
| `cizinci/index.html` | grafy cizinců (mapa, vývoj) |
| `scripts/build_data.py` | stažení datových sad a příprava `cizinci/*.json` (negenerují se do repozitáře) |
| `scripts/hranice.py` | hranice okresů z RÚIAN → `podklady/okresy.json` |

Nové téma = nová složka se stránkou a nová funkce v `build_data.py`.

## Licence

Kód: MIT (viz [LICENSE](LICENSE)). Hranice okresů: © ČÚZK, CC BY 4.0. Data: podle zdrojových datových sad.

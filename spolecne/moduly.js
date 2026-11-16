/* Seznam modulů webu. Z něj se skládá navigace, karty na úvodní stránce a seznam
   datových sad na stránce Data a metodika.

   Nový modul (např. „Děti“):
   1. přidej sem položku (stav: 'pripravujeme' ukáže na úvodu jen kartu „připravujeme“),
   2. vytvoř složku se stránkou modulu (adresa), vzor je obyvatele/index.html,
   3. data pro grafy připrav ve scripts/build_data.py a doplň složku do nasazení (.github/workflows/pages.yml),
   4. až bude hotový, přepni stav na 'hotovo'.

   souhrn(S) dostane data/souhrn.json a vrací, co se ukáže na kartě: velké číslo, popisek a řadu
   pro malý graf. Funkce je nepovinná. */
window.MODULY = [
  {
    id: 'obyvatele',
    nazev: 'Obyvatelé',
    popis: 'Počty obyvatel všech obcí a městských částí od roku 2004: kde lidí přibývá a ubývá, občané a cizinci, oficiální počet ČSÚ.',
    barva: 'var(--obc)',
    adresa: 'obyvatele/',
    stav: 'hotovo',
    data: [{
      nazev: 'Informativní počty obyvatel v obcích', repo: 'opendatabrno/obyvatele', zdroj: 'MV ČR, ČSÚ',
      web: 'https://opendatabrno.github.io/obyvatele/',
      soubory: [['obyvatele_obce', 'obce × rok, stav k 1. 1., 2004–dosud'],
                ['obyvatele_mestske_casti', 'městské části 8 statutárních měst × rok, 2007–dosud']],
      aktualizace: 'v lednu (MV), oficiální počty ČSÚ v květnu'
    }],
    souhrn: S => ({
      cislo: S.obyvatele.obyvatele.at(-1), popisek: `obyvatel podle MV k 1. 1. ${S.obyvatele.roky.at(-1)}`,
      rada: S.obyvatele.obyvatele.slice(Math.max(0, S.obyvatele.roky.indexOf(Z.OD)))
    })
  },
  {
    id: 'cizinci',
    nazev: 'Cizinci',
    popis: 'Cizinci s povoleným pobytem po okresech a podle státní příslušnosti, měsíční vývoj za ČR od roku 2007.',
    barva: 'var(--ciz)',
    adresa: 'cizinci/',
    stav: 'hotovo',
    data: [{
      nazev: 'Cizinci s povoleným pobytem', repo: 'opendatabrno/cizinci', zdroj: 'MV ČR, Služba cizinecké policie',
      web: 'https://opendatabrno.github.io/cizinci/',
      soubory: [['cizinci_okresy', 'okresy × rok, stav k 31. 12.'],
                ['cizinci_okresy_staty', 'okresy × státní příslušnost × rok'],
                ['cizinci_staty', 'ČR × státní příslušnost × rok, od 2007'],
                ['cizinci_mesicne', 'ČR × státní příslušnost × měsíc, od 1/2007']],
      aktualizace: 'každý měsíc'
    }],
    souhrn: S => ({
      cislo: S.cizinci.posledni_pocet,
      popisek: `cizinců s povoleným pobytem k ${new Date(S.cizinci.posledni_mesic).toLocaleDateString('cs-CZ')}`,
      rada: S.cizinci.mesicne
    })
  },
  {
    id: 'zaci',
    nazev: 'Žáci',
    popis: 'Děti v mateřských a žáci v základních školách zřizovaných obcemi od roku 2014, po obcích, a kolik obce dostávají na žáka ze sdílených daní.',
    barva: 'var(--zak)',
    adresa: 'zaci/',
    stav: 'hotovo',
    data: [{
      nazev: 'Děti a žáci ve školách zřizovaných obcemi', repo: 'opendatabrno/zaci', zdroj: 'MF ČR (z výkazů MŠMT)',
      web: 'https://opendatabrno.github.io/zaci/',
      soubory: [['zaci_obce', 'obce × rok, stav k 30. 9., 2014–dosud'],
                ['zaci_svazky_obci', 'školy dobrovolných svazků obcí × rok'],
                ['castka_na_zaka', 'Kč na žáka ze sdílených daní, rozpočtové roky 2013–dosud']],
      aktualizace: 'jednou ročně (MF zveřejňuje v lednu až červnu)'
    }],
    souhrn: S => ({
      cislo: S.zaci.celkem.at(-1), popisek: `dětí a žáků ve školách obcí k 30. 9. ${S.zaci.roky.at(-1)}`,
      rada: S.zaci.celkem
    })
  },
  // Vzor dalšího modulu:
  // { id: 'deti', nazev: 'Děti', popis: 'Počty dětí v obcích podle věku …', barva: 'var(--csu)',
  //   adresa: 'deti/', stav: 'pripravujeme', data: [] },
];

/* Stránky mimo moduly; v navigaci jsou za moduly. */
window.STRANKY = [
  { id: 'obec', nazev: 'Profil obce', adresa: 'obec/' },
  { id: 'metodika', nazev: 'Data a metodika', adresa: 'metodika/' },
  { id: 'vlozit', nazev: 'Grafy k vložení', adresa: 'vlozit/' },
];

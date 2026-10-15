#!/usr/bin/env python3
"""抓官網頁面、列出未翻字串、把譯文字典寫進 data/translations/pages/<page>.json。

  python3 scripts/pagetool.py fetch <page> [<page>…]   抓 ?page=<page> 到 .cache/pages/<page>.html
  python3 scripts/pagetool.py list  <page> [<page>…]   列出這頁還沒翻的文字節點（查表能自動翻的標 [auto]）
  python3 scripts/pagetool.py apply <page> <dict.py>   套用字典，寫入 pages/<page>.json，印出剩下沒翻的
  python3 scripts/pagetool.py check [<page>…]          每頁的翻譯涵蓋率，以及字典裡在所有已抓頁面都找不到的 key（可能已失效）

<dict.py> 是一般 Python 檔，可定義：
  M        = {英文: 中文}                      完全相符的譯文
  PATTERNS = {含 {n}/{*} 的 key: 譯文}         直接寫入（動態數字、日期、計數）
  EMO      = {去掉開頭 emoji 的英文: 中文}      會自動補回原本的 emoji
  ITEMS    = {道具英文: 中文}                  覆寫 l1justice 道具表
  EXTRA_PAGES = ['lookup-items_stat_armor_sets']   同一頁的其他 html（帶 &stat= 的變體）
  USE_MAPS / USE_MONSTERS / USE_SKILLS = True       用 l1justice 的地圖／怪物／技能表自動翻
  FORCE    = True                              M 裡每一條都寫入，就算這頁沒出現（跨頁共用字串放這）
名詞表：環境變數 L1JUSTICE_DIR，預設 ../l1justice-zh-userscript；找不到就只用字典檔。
"""
import importlib.util, json, os, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / '.cache' / 'pages'
TRANS = ROOT / 'data' / 'translations'
L1J = Path(os.environ.get('L1JUSTICE_DIR', ROOT.parent / 'l1justice-zh-userscript'))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
SKIP = {'Ctrl K', '✦', '→', 'Discord', 'Esc', '🌀', '·', '×', '＋', '+', '↓', '↗'}

# ---------- 抓頁面 ----------
def html_path(page): return PAGES / (page.replace('&', '_').replace('=', '_') + '.html')

def fetch(page):
    PAGES.mkdir(parents=True, exist_ok=True)
    out = html_path(page)
    subprocess.run(['curl', '-sL', '-A', UA, f'https://lineage1reborn.com/?page={page}', '-o', str(out)], check=True)
    body = out.read_text(encoding='utf-8', errors='ignore')
    if 'Too many anonymous requests' in body or len(body) < 20000:
        print(f'{page}: 被限流或抓到空頁（{len(body)} bytes），等幾分鐘再抓', file=sys.stderr)
        return False
    print(f'{page}: {len(body)} bytes -> {out.relative_to(ROOT)}')
    return True

# ---------- 抽文字節點（和 src/main.js 一樣：trim、連續空白收成一個） ----------
def extract(path):
    class P(HTMLParser):
        def __init__(s): super().__init__(convert_charrefs=True); s.skip = 0; s.out = []
        def handle_starttag(s, t, a):
            if t in ('script', 'style', 'noscript', 'title'): s.skip += 1
        def handle_endtag(s, t):
            if t in ('script', 'style', 'noscript', 'title'): s.skip -= 1
        def handle_data(s, d):
            if s.skip: return
            d = re.sub(r'\s+', ' ', d).strip()
            if d: s.out.append(d)
    p = P(); p.feed(Path(path).read_text(encoding='utf-8', errors='ignore'))
    seen, rows = set(), []
    for t in p.out:
        if t not in seen: seen.add(t); rows.append(t)
    return rows

def known_dict(exclude_page=None, page=None):
    """全站字典；pages/<page>.local.json 只在 page 等於那一頁時算進來。"""
    d = {}
    for f in sorted(TRANS.glob('*.json')) + sorted((TRANS / 'pages').glob('*.json')):
        if exclude_page and f.name == exclude_page + '.json': continue
        if f.name.endswith('.local.json') and f.name != f'{page}.local.json': continue
        d.update(json.loads(f.read_text(encoding='utf-8')))
    return d

def known_matcher(d):
    """和 src/lookup.js 一樣：先完全相符，再試 {n}/{*} pattern。"""
    pats = [re.compile('^' + re.escape(k).replace(r'\{n\}', r'\d[\d,.]*').replace(r'\{\*\}', '.+?') + '$')
            for k in d if re.search(r'\{[n*]\}', k)]
    return lambda s: s in d or any(p.match(s) for p in pats)

# ---------- l1justice 名詞表 ----------
def _load_mapping(kind):
    f = L1J / 'data' / 'sources' / '_mappings' / f'{kind}.json'
    if not f.exists(): return {}
    rows = json.loads(f.read_text(encoding='utf-8'))['mappings']
    ovf = L1J / 'data' / 'sources' / '_mappings' / f'{kind}-overrides.json'
    ov = json.loads(ovf.read_text(encoding='utf-8')) if ovf.exists() else {}
    d = {}
    for r in rows:
        zh = r.get('zh') or r.get('loa_zh')
        o = ov.get(str(r.get('l1justice_id')))
        if o and o.get('zh'): zh = o['zh']
        for k in (r.get('l1justice_name'), r.get('en'), r.get('loa_en')):
            if k and zh: d.setdefault(k.strip().lower(), zh)
    return d

_items = _monsters = _skills = _maps = None
def tables():
    global _items, _monsters, _skills, _maps
    if _items is None:
        _items, _monsters, _skills = _load_mapping('items'), _load_mapping('monsters'), _load_mapping('skills')
        mf = L1J / 'data' / 'translations' / 'maps.json'
        _maps = {k.lower(): v for k, v in json.loads(mf.read_text(encoding='utf-8')).items()} if mf.exists() else {}
        if not _items: print(f'（找不到 l1justice 名詞表：{L1J}，只用字典檔）', file=sys.stderr)
    return _items, _monsters, _skills, _maps

# l1justice 道具表裡錯配或命名風格不符的，統一在這裡覆寫
ITEM_FIX = {
 "Pumpkin Candy": "南瓜糖果", "Condensed Greater Healing Potion": "濃縮強力治癒藥水", "Ancient Greater Healing Potion": "古代強力治癒藥水",
 "Potion of Mana": "魔力回復藥水", "Hunters Bow": "獵人之弓", "Greater Haste Potion": "強化自我加速藥水", "Apple Juice": "蘋果汁", "Candy": "糖果",
 "Dark Stone": "黑暗之石", "Succubus Earring": "思克巴耳環", "Magic Doll: Succubus": "魔法娃娃：思克巴",
 "High Quality Diamond": "高品質鑽石", "High Quality Ruby": "高品質紅寶石", "High Quality Sapphire": "高品質藍寶石", "High Quality Emerald": "高品質綠寶石",
 "Highest Quality Diamond": "最高品質鑽石", "Highest Quality Ruby": "最高品質紅寶石", "Highest Quality Sapphire": "最高品質藍寶石", "Highest Quality Emerald": "最高品質綠寶石",
 "Healing Potion": "治癒藥水", "Greater Healing Potion": "強力治癒藥水", "Extra Healing Potion": "高級治癒藥水",
 "Condensed Healing Potion": "濃縮治癒藥水", "Condensed Extra Healing Potion": "濃縮高級治癒藥水",
 "Blessed Healing Potion": "受祝福的治癒藥水", "Blessed Extra Healing Potion": "受祝福的高級治癒藥水", "Blessed Greater Healing Potion": "受祝福的強力治癒藥水",
 "Cursed Healing Potion": "受詛咒的治癒藥水",
 "Uncommon Rune": "普通符文", "Rare Rune": "稀有符文", "Epic Rune": "史詩符文", "Scroll of Shape Change": "變形卷軸", "Forbidden Scroll": "禁忌卷軸",
 "Doomed Scroll of Enchant Armor": "受詛咒的對盔甲施法的卷軸", "Doomed Scroll of Enchant Weapon": "受詛咒的對武器施法的卷軸",
}

def item_zh(name, fix):
    if name in fix: return fix[name]
    z = tables()[0].get(name.lower())
    if not z: return None
    z = z.replace('受祝福的 ', '').replace('(商城)', '')
    return re.sub(r'(?<=[一-鿿]) (?=[一-鿿])', '', z)  # 「特別的 魚子醬」→「特別的魚子醬」

def mon_zh(name): return tables()[1].get(name.lower())
def skill_zh(name):
    sk = tables()[2]
    return sk.get(name.lower()) or sk.get(name.lower().replace(': ', ' : '))
def map_zh(name): return tables()[3].get(name.lower())

# ---------- 日期時間：轉成「10/9（五）13:00 ET」 ----------
WD = dict(Mon='一', Tue='二', Wed='三', Thu='四', Fri='五', Sat='六', Sun='日')
MO = dict(Jan=1, Feb=2, Mar=3, Apr=4, May=5, Jun=6, Jul=7, Aug=8, Sep=9, Oct=10, Nov=11, Dec=12)
MOZH = dict(Jan='一月', Feb='二月', Mar='三月', Apr='四月', May='五月', Jun='六月', Jul='七月', Aug='八月', Sep='九月', Oct='十月', Nov='十一月', Dec='十二月')
T = r'(\d{1,2}):(\d{2}) (AM|PM)'; W = r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)'; Mo = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
def t24(h, m, ap): return f'{int(h) % 12 + (12 if ap == "PM" else 0):02d}:{m}'

def date_zh(s):
    m = re.fullmatch(fr'{W}, {Mo} (\d+), {T} – {W}, {Mo} (\d+), {T} ET', s)
    if m: g = m.groups(); return f'{MO[g[1]]}/{g[2]}（{WD[g[0]]}）{t24(*g[3:6])} – {MO[g[7]]}/{g[8]}（{WD[g[6]]}）{t24(*g[9:12])} ET'
    m = re.fullmatch(fr'{W}, {Mo} (\d+) – {W}, {Mo} (\d+), (\d{{4}})', s)
    if m: g = m.groups(); return f'{g[6]}/{MO[g[1]]}/{g[2]}（{WD[g[0]]}）– {MO[g[4]]}/{g[5]}（{WD[g[3]]}）'
    m = re.fullmatch(fr'{Mo} (\d+), {T} – {Mo} (\d+), {T} ET', s)
    if m: g = m.groups(); return f'{MO[g[0]]}/{g[1]} {t24(*g[2:5])} – {MO[g[5]]}/{g[6]} {t24(*g[7:10])} ET'
    m = re.fullmatch(fr'{Mo} (\d+)–(\d+)(?:, (\d{{4}}))?( · starts in)?', s)
    if m: g = m.groups(); return (f'{g[3]}/' if g[3] else '') + f'{MO[g[0]]}/{g[1]}–{g[2]}' + (' · 距開始' if g[4] else '')
    m = re.fullmatch(fr'{Mo} (\d+) – {Mo} (\d+)(?:, (\d{{4}}))?( · starts in)?', s)
    if m: g = m.groups(); return (f'{g[4]}/' if g[4] else '') + f'{MO[g[0]]}/{g[1]} – {MO[g[2]]}/{g[3]}' + (' · 距開始' if g[5] else '')
    m = re.fullmatch(fr'{Mo} (\d+), (\d{{4}})', s)
    if m: return f'{m.group(3)}/{MO[m.group(1)]}/{m.group(2)}'
    m = re.fullmatch(fr'{Mo} (\d{{4}})', s)
    if m: return f'{m.group(2)} 年{MOZH[m.group(1)]}'
    if s in MOZH: return MOZH[s]
    m = re.fullmatch(fr'{T}(?: · {T})* ET', s)
    if m: return re.sub(T, lambda x: t24(*x.groups()), s)
    return None

# ---------- 指令 ----------
def auto_zh(s, mod=None):
    fix = dict(ITEM_FIX, **getattr(mod, 'ITEMS', {}))
    return (date_zh(s) or item_zh(s, fix)
            or (map_zh(s) if getattr(mod, 'USE_MAPS', False) else None)
            or (mon_zh(s) if getattr(mod, 'USE_MONSTERS', False) else None)
            or (skill_zh(s) if getattr(mod, 'USE_SKILLS', False) else None))

def rows_for(page, mod=None):
    rows = extract(html_path(page))
    for ex in getattr(mod, 'EXTRA_PAGES', []):
        f = html_path(ex)
        if f.exists() and f.stat().st_size > 20000:
            for r in extract(f):
                if r not in rows: rows.append(r)
    return rows

def cmd_list(pages):
    for page in pages:
        known = known_matcher(known_dict(page=page))
        rows = [r for r in rows_for(page) if not known(r) and r not in SKIP and not r.startswith('© ')]
        print(f'===== {page}: {len(rows)} 條未翻')
        for r in rows: print(('[auto] ' if auto_zh(r) else '') + r)

def cmd_apply(page, dict_path):
    spec = importlib.util.spec_from_file_location('page_dict', dict_path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    M = getattr(mod, 'M', {}); EMO = getattr(mod, 'EMO', {})
    rows = rows_for(page, mod); known = known_matcher(known_dict(exclude_page=page, page=page))
    out, left = {}, []
    for s in rows:
        if known(s): continue
        if s in M: out[s] = M[s]; continue
        parts = s.split(' ', 1)
        if len(parts) == 2 and ord(parts[0][0]) > 0x2000 and (parts[1] in EMO or parts[1] in M):
            out[s] = parts[0] + ' ' + (EMO.get(parts[1]) or M[parts[1]]); continue
        z = auto_zh(s, mod)
        if z: out[s] = z; continue
        if s not in SKIP and not s.startswith('© '): left.append(s)
    out.update(getattr(mod, 'PATTERNS', {}))
    if getattr(mod, 'FORCE', False):
        for k, v in M.items(): out.setdefault(k, v)
    unused = [k for k in M if k not in out and not any(r.endswith(' ' + k) for r in rows)]
    p = TRANS / 'pages' / f'{page}.json'
    cur = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    cur.update(out)
    left = [s for s in left if s not in cur]
    p.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{page}: 本次寫入 {len(out)} 條，檔案共 {len(cur)} 條')
    if unused: print('字典裡有但這頁沒出現:', unused)
    print('沒翻的:', ' | '.join(left))

NOISE = re.compile(r'[\d,.%+\-x×/ :→–()#]+|[A-Z]{2,4}')  # 純數字、符號、STR/MP 之類縮寫不算進涵蓋率

def cmd_check(pages):
    cached = sorted(PAGES.glob('*.html')) if PAGES.exists() else []
    if not cached: print('.cache/pages/ 是空的，先 fetch'); return
    want = set(pages) if pages else None
    seen_anywhere, report = set(), []
    for f in cached:
        rows = [r for r in extract(f) if r not in SKIP and not r.startswith('© ') and not NOISE.fullmatch(r)]
        seen_anywhere.update(rows)
        page = f.stem
        if want and page not in want: continue
        matcher = known_matcher(known_dict(page=page))
        miss = [r for r in rows if not matcher(r)]
        report.append((page, len(rows), len(miss), miss))
    for page, total, nmiss, miss in sorted(report):
        pct = 100 * (total - nmiss) // total if total else 100
        print(f'{page:<40} {total - nmiss:>5}/{total:<5} {pct:>3}%' + (f'   未翻: ' + ' | '.join(miss[:8]) + (' …' if nmiss > 8 else '') if nmiss else ''))
    if want: return
    cached_names = {f.stem for f in cached}
    print('\n字典裡在所有已抓頁面都找不到的 key（已抓 %d 頁；pattern 不檢查，被 {*} 查表用到的 key 也會列在這裡）：' % len(cached))
    for jf in sorted((TRANS / 'pages').glob('*.json')):
        if jf.name.endswith('.local.json'): continue
        if jf.stem not in cached_names: print(f'  {jf.name}: 該頁未抓，跳過（python3 scripts/pagetool.py fetch {jf.stem}）'); continue
        stale = [k for k in json.loads(jf.read_text(encoding='utf-8')) if '{' not in k and k not in seen_anywhere]
        if stale: print(f'  {jf.name}: {len(stale)} 條  ' + ' | '.join(s[:50] for s in stale[:5]) + (' …' if len(stale) > 5 else ''))

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'fetch': sys.exit(0 if all([fetch(p) for p in a[1:]]) else 1)
    elif len(a) >= 2 and a[0] == 'list': cmd_list(a[1:])
    elif len(a) == 3 and a[0] == 'apply': cmd_apply(a[1], a[2])
    elif a and a[0] == 'check': cmd_check(a[1:])
    else: print(__doc__); sys.exit(2)

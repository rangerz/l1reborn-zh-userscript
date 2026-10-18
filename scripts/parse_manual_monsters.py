#!/usr/bin/env python3
"""解析手動存檔的怪物頁 → data/reborn/monsters.json（每隻有 mode：standard、diablo，官網的 Drop Settings），圖片複製到 data/reborn/images/monsters/。只讀本地檔，不對官網發請求。
- 列表：.cache/manual/monsters/monsters_<等級帶>.html、monsters_<等級帶>_p2..pN.html
  （?page=lookup-monsters&mode=standard&lvl=<等級帶>&npc_page=N；等級帶 upto20、21_40、41_50、51_60、61_70、71plus）。卡片沒有掉落。
- 詳情：.cache/manual/monsters/npc_<id>.html（?page=lookup-monsters&npc=<id>&mode=standard），補列表沒收的怪物
  （item_sources 掉落裡出現、但列表沒有的），band 記為 'detail'，多一個 drops 欄位。
  詳情頁也有固定 NPC（map_details 的怪物清單裡出現）：卡片名字列有座標標籤，記為 positions；沒有掉落區就不輸出 drops。
  官網查不到的 ID（頁面沒有怪物區塊）不輸出，只在結尾列出（目前 26510、26511、45007、81241、81242、95448）。
  詳情頁的來源：map_details、kill_quests、items/item_sources.json 的掉落來源裡出現、但列表沒有的怪物（前兩者 65＋3 隻，item_sources 另補 156 隻，其中 4 隻官網查不到）；
  另外 map_details 的 npcs（固定 NPC）裡列表沒有的 378 隻也補了（全是 NPC 徽章，沒有掉落；377 隻有座標，只有 33 隻有圖，70901 沒座標）。
  26510、26511、45007、95448 只出現在 item_sources 的掉落來源裡（26510 Zombie、26511 Crawling Craw 掉 40320，機率 16%；45007 Mambo Rabbit Blue Vest 掉 21019，1%；
  95448 Boss Event Supreme Court Justice Ramias 掉 440000～440002，0.7%），map_details、kill_quests、bosses、treasure_boxes、tamable 都沒有；
  同名怪物（如 Zombie 45065、Ramias 45961）是不同 ID，不能當成它們，所以不補，也不輸出。
  詳情頁的座標比 map_details 少（37 隻筆數不一致，70901 重抓確認官網卡片沒有座標），positions 不是完整座標，完整座標請看 map_details.json。
- diablo 列表：.cache/manual/monsters/monsters_diablo_<等級帶>[_pN].html（&mode=diablo&lvl=<等級帶>&npc_page=N）。官網只有 51_60（2 隻，單頁沒有頁碼）、61_70（7 頁 170 隻）、71plus（25 頁 601 隻）有資料，
  upto20、21_40、41_50 是空的，沒有存檔；共 773 隻，其中 40 隻是 bosses.json 的 diablo Boss，這裡跳過，所以新增 733 隻（放在檔案最後）。diablo 卡片沒有圖示。classic 還沒抓。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'monsters'
OUT = ROOT / 'data' / 'reborn'
BANDS = ('upto20', '21_40', '41_50', '51_60', '61_70', '71plus')
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
num = lambda s: float(s.replace(',', ''))
(OUT / 'images' / 'monsters').mkdir(parents=True, exist_ok=True)

def clean(path):
    return re.sub(r'<script.*?</script>|<style.*?</style>', '', path.read_text(encoding='utf-8'), flags=re.S)

def parse_card(c, stem, band, mode='standard'):
    a = re.search(r'<a href="[^"]*npc=(\d+)[^"]*"[^>]*>(.*?)</a>', c, re.S)
    assert f'mode={mode}' in a.group(0), f'{stem} 卡片連結不是 {mode}：{a.group(0)}'
    badges = [txt(b) for b in re.findall(r'<span class="px-2 py-0\.5 text-xs rounded[^"]*">(.*?)</span>', c, re.S)]
    stats = {txt(k).rstrip(':'): txt(v) for k, v in re.findall(r'<div><span class="text-gray-400">(.*?)</span>(.*?)</div>', c, re.S)}
    positions = [{'map_id': int(i), 'map': txt(n), 'x': int(x), 'y': int(y)}
                 for i, x, y, n in re.findall(r'guide-map&amp;id=(\d+)#x=(\d+)&amp;y=(\d+)"[^>]*>(.*?)<span', c.split('<dl')[0], re.S)]
    tail = re.search(r'<div class="text-sm text-gray-300 mt-2">(.*?)</div>\s*</div>\s*</div>', c, re.S)
    spawn = {}
    if tail:
        body = tail.group(1)
        for k in ('Spawn Window', 'Avg Spawns'):
            m = re.search(k + r':</span>\s*<span>(.*?)</span>', body, re.S)
            if m: spawn[k] = txt(m.group(1))
        spawn['Locations'] = [{'map_id': int(i), 'name': txt(t)} for i, t in re.findall(r'guide-map&amp;id=(\d+)[^"]*"[^>]*>(.*?)</a>', body, re.S)]
    img = re.search(r'<img src="([^"]*)"', c)
    icon = None
    if img and img.group(1).startswith(f'{stem}_files/') and (SRC / img.group(1)).exists():
        p = SRC / img.group(1); icon = p.name; shutil.copy(p, OUT / 'images' / 'monsters' / icon)
    return {'id': int(a.group(1)), 'mode': mode, 'name': txt(a.group(2)), 'band': band, 'badges': badges, 'stats': stats, 'spawn': spawn, 'icon': icon,
            **({'positions': positions} if positions else {})}

def parse_drops(h, stem):
    d = h[h.index('id="lookup-drops"'):]
    d = d[:d.index('<footer')] if '<footer' in d else d
    drops = []
    for r in re.findall(r'<img [^>]*inline-block w-6 h-6[^>]*>\s*<div class="flex-1">(.*?)</div>\s*</div>\s*</div>', d, re.S):
        t = txt(r)
        m = re.fullmatch(r'(.*?) · (?:Item (\d+)|(\d+) rune types)(?: (Blessed|Cursed))?(?: Min/Max ([\d,]+)/([\d,]+)| Kill Quest: (.*?) \([\d.,]+%\) Kill Quest Reward · Qty ([\d,]+))(?: · Chance ([\d.,]+)%)?( \(grouped\))?', t)
        assert m and bool(m.group(2)) != bool(m.group(3)) and bool(m.group(5)) != bool(m.group(7)), f'{stem} 掉落格式不符：{t}'
        lo, hi = (m.group(5), m.group(6)) if m.group(5) else (m.group(8), m.group(8))  # 擊殺任務獎勵只有固定數量 Qty
        drops.append({'item_id': int(m.group(2)) if m.group(2) else None, 'name': m.group(1), 'status': m.group(4),
                      'min': int(num(lo)), 'max': int(num(hi)), 'chance_pct': num(m.group(9)) if m.group(9) else None,  # 活動怪物的機率官網不顯示
                      **({'rune_types': int(m.group(3))} if m.group(3) else {}), **({'quest': m.group(7)} if m.group(7) else {})})
    assert len(drops) == d.count('inline-block w-6 h-6'), f'{stem} 掉落列數與圖示數不符'
    return drops

def pages(band, mode):
    base = f'monsters_{band}' if mode == 'standard' else f'monsters_{mode}_{band}'
    if not (SRC / f'{base}.html').exists(): return  # diablo 的 upto20、21_40、41_50 官網是空的，沒有存檔
    yield 1, base
    n = 2
    while (SRC / f'{base}_p{n}.html').exists():
        yield n, f'{base}_p{n}'; n += 1

boss_ids = {b['id'] for b in json.loads((OUT / 'bosses.json').read_text(encoding='utf-8')) if b['mode'] == 'diablo'}
mons, dia, seen, per, skipped = [], [], {}, {}, set()
for mode in ('standard', 'diablo'):
    for band in BANDS:
        n_band, last_total = 0, None
        for n, stem in pages(band, mode):
            h = clean(SRC / f'{stem}.html')
            total = re.search(r'Page (\d+) of (\d+)', h)
            h = h[h.index('id="lookup-monsters"'):]
            showing = re.search(r'Showing (\d+)-(\d+)', h)
            cards = h.split('lookup-monster-summary')[1:]
            if total:  # 只有一頁的列表（diablo 51_60）官網沒有頁碼和 Showing
                assert int(total.group(1)) == n, f'{stem}.html 頁碼不符：{total.group(0)}'
                assert showing and len(cards) == int(showing.group(2)) - int(showing.group(1)) + 1, f'{stem}.html 卡片數與 Showing 不符'
                last_total = int(showing.group(2))
            else:
                assert n == 1 and not showing, f'{stem}.html 沒有頁碼'
            for c in cards:
                m = parse_card(c, stem, band, mode)
                n_band += 1
                if mode == 'diablo' and m['id'] in boss_ids: skipped.add(m['id']); continue  # 已在 bosses.json
                if m['id'] in seen: print('重複', m['id'], m['name'], seen[m['id']], '+', band); continue
                seen[m['id']] = band
                (dia if mode == 'diablo' else mons).append(m)
        if n_band:
            assert last_total is None or n_band == last_total, f'{mode} {band} 共 {n_band} 隻，最後一頁標示到 {last_total}'
            per[band if mode == 'standard' else f'{mode}_{band}'] = n_band
assert skipped == boss_ids, f'bosses.json 的 diablo Boss 有 {len(boss_ids - skipped)} 隻沒出現在 diablo 列表'

n_detail, unavailable = 0, []
for path in sorted(SRC.glob('npc_*.html'), key=lambda p: int(p.stem[4:])):
    nid = int(path.stem[4:])
    h = clean(path)
    if 'id="lookup-monsters"' not in h: unavailable.append(nid); continue
    h = h[h.index('id="lookup-monsters"'):]
    assert h.count('lookup-monster-summary') == 1, f'{path.name} 不是單一怪物頁'
    m = parse_card(h.split('lookup-monster-summary')[1], path.stem, 'detail')
    assert m['id'] == nid, f'{path.name} 內的 ID 是 {m["id"]}'
    assert nid not in seen, f'{nid} 列表已有，不需要詳情頁'
    if 'id="lookup-drops"' in h: m['drops'] = parse_drops(h, path.stem)
    seen[nid] = 'detail'; n_detail += 1
    mons.append(m)
mons += dia  # diablo 放最後，standard 的順序不變
(OUT / 'monsters.json').write_text(json.dumps(mons, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(mons)} 隻怪物（standard 列表 {len(mons) - n_detail - len(dia)}、詳情 {n_detail}、diablo {len(dia)}，另跳過 bosses.json 的 {len(skipped)} 隻）', per, '缺圖', sum(m['icon'] is None for m in mons),
      f'；詳情頁查不到 {unavailable}')

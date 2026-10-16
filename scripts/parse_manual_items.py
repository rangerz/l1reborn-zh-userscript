#!/usr/bin/env python3
"""解析手動存檔的武器／防具列表 .cache/manual/items/weapon_*.html、armor_*.html（?page=lookup-items&item_type=…，Standard）
→ data/reborn/items/weapons.json、armors.json，圖片複製到 data/reborn/items/images/。只讀本地檔，不對官網發請求。
不含「Load sources」（掉落／商店來源，需點擊才載入）。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'items'
OUT = ROOT / 'data' / 'reborn' / 'items'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
(OUT / 'images').mkdir(parents=True, exist_ok=True)

def parse_page(path):
    stem = path.stem
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', path.read_text(encoding='utf-8'), flags=re.S)
    cards = h.split('data-item-card-id="')[1:]
    assert len(cards) == h.count('lookup-sources-load'), f'{path.name} 卡片數與 Load sources 按鈕數不符'
    for c in cards:
        iid = int(re.match(r'(\d+)"', c).group(1))
        a = re.search(r'<a href="/item/(\d+)/([^"]*)"[^>]*>(.*?)</a>', c, re.S)
        assert int(a.group(1)) == iid, f'{path.name} 卡片 {iid} 連結 ID 不符'
        kind = txt(re.search(r'uppercase text-gray-300[^>]*>(.*?)<span', c, re.S).group(1))
        shown = re.search(r'\(ID (\d+)\)', c)
        assert shown and int(shown.group(1)) == iid, f'卡片 {iid} 格式不符'
        stats = {}
        for k, v in re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', c, re.S):
            k = txt(k).rstrip(':')
            if not k: continue  # 排版用的空白格
            stats[k] = [html.unescape(t) for t in re.findall(r'title="([^"]*)"', v)] if k == 'Classes' else txt(v)
        img = re.search(r'<img src="([^"]*)"', c)
        icon = None
        if img and img.group(1).startswith(f'{stem}_files/') and (SRC / img.group(1)).exists():
            p = SRC / img.group(1); icon = p.name
            if icon != 'default.webp': shutil.copy(p, OUT / 'images' / icon)
        bless = re.search(r'item-bless-badge[^>]*>(.*?)</span>', c, re.S)
        sec = re.search(r'space-y-2 text-sm text-gray-200">(.*?)lookup-sources', c, re.S)
        sset = None
        if sec:
            sb = sec.group(1)
            sset = {'name': txt(re.search(r'uppercase tracking-wide[^>]*>(.*?)</span>', sb, re.S).group(1)),
                    'bonus': (txt(m.group(1)).removeprefix('Full Set:').strip() if (m := re.search(r'text-emerald-200">(.*?)</span>', sb, re.S)) else None),
                    'members': []}
            for mm in re.finditer(r'<span class="inline-flex items-center gap-1[^>]*>(.*?)</span>', sb, re.S):
                ml = re.search(r'data-item-preview-id="(\d+)"[^>]*>(.*?)</a>', mm.group(1), re.S)
                mi = re.search(r'<img src="([^"]*)"', mm.group(1))
                micon = None
                if mi and mi.group(1).startswith(f'{stem}_files/') and (SRC / mi.group(1)).exists():
                    mp = SRC / mi.group(1); micon = mp.name
                    if micon != 'default.webp': shutil.copy(mp, OUT / 'images' / micon)
                sset['members'].append({'id': int(ml.group(1)), 'name': txt(ml.group(2)), 'icon': micon})
        # 拍賣場近 90 天成交統計（會隨時間變動的快照）：名稱旁 pill 是 +0，lookup-market 區的 chip 是各強化等級
        market = [{'enchant': int(e), 'label': txt(t), 'summary': html.unescape(ti).replace(' Click for price history.', '')}
                  for e, ti, t in re.findall(r'<button[^>]*class="lookup-market__(?:pill|chip)"[^>]*data-graph-item-enchant="(\d+)"[^>]*title="([^"]*)"[^>]*>(.*?)</button>', c, re.S)]
        runes = [{'name': txt(n), 'effect': txt(e)} for n, e in re.findall(r'<span class="font-semibold[^"]*">([^<]*Rune[^<]*?):</span>(.*?)</div>', c, re.S)]
        tags = re.match(r'\d+"\s+data-item-stats="([^"]*)"', c)
        yield {'id': iid, 'name': txt(a.group(3)), 'slug': a.group(2), 'kind': kind, 'type': stem.split('_', 1)[1],
               'bless': txt(bless.group(1)) if bless else None, 'stat_tags': [t for t in tags.group(1).split(',') if t] if tags else [],
               'stats': stats, 'set': sset, 'runes': runes, 'market': market, 'icon': icon}

for group, fname in (('weapon', 'weapons.json'), ('armor', 'armors.json')):
    items, seen, per = [], {}, {}
    for path in sorted(SRC.glob(f'{group}_*.html')):
        n = 0
        for it in parse_page(path):
            n += 1
            if it['id'] in seen: print('重複', it['id'], it['name'], seen[it['id']], '+', it['type']); continue
            seen[it['id']] = it['type']; items.append(it)
        per[path.stem.split('_', 1)[1]] = n
    (OUT / fname).write_text(json.dumps(items, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{fname}：{len(items)} 件（{sum(per.values())} 張卡片，{len(per)} 種）', per, '缺圖', sum(i['icon'] is None for i in items))

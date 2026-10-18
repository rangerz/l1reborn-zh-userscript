#!/usr/bin/env python3
"""解析手動存檔的 Boss 列表 → data/reborn/bosses.json，每隻有 mode 欄位（官網的 Drop Settings）。只讀本地檔，不對官網發請求，圖片複製到 data/reborn/images/monsters/。
- standard：.cache/manual/bosses.html、bosses_p2..pN.html（?page=lookup-monsters&stat=bosses，142 隻）
- diablo：.cache/manual/bosses_diablo.html、bosses_diablo_p2..pN.html（&mode=diablo，40 隻）
- classic：.cache/manual/bosses_classic.html、bosses_classic_p2..pN.html（&mode=classic，125 隻，名稱尾巴帶「(C)」）
三種模式的 ID 互不重疊（classic 是 10 開頭的 8 碼，例如 10045228）。classic 頁首沒有「Showing classic drop settings」，
所以模式改用每張卡片連結的 mode=<模式> 驗證。
卡片本身沒有掉落，沒有 Spawn Window 的卡片（diablo 全部、其他模式少數）只有地點；diablo 卡片沒有圖示。
地點連結後面可能帶 #x=&y= 座標（classic 有），只取地圖 ID 和名稱。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
(OUT / 'images' / 'monsters').mkdir(parents=True, exist_ok=True)

def pages(mode):
    stem = 'bosses' if mode == 'standard' else f'bosses_{mode}'
    yield 1, SRC / f'{stem}.html'
    n = 2
    while (SRC / f'{stem}_p{n}.html').exists():
        yield n, SRC / f'{stem}_p{n}.html'; n += 1

bosses, seen, per = [], set(), {}
for mode, n, path in ((m, n, p) for m in ('standard', 'diablo', 'classic') for n, p in pages(m)):
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', path.read_text(encoding='utf-8'), flags=re.S)
    total = re.search(r'Page (\d+) of (\d+)', h)
    assert total and int(total.group(1)) == n, f'{path.name} 頁碼不符：{total and total.group(0)}'
    h = h[h.index('id="lookup-monsters"'):]
    for c in h.split('lookup-monster-summary')[1:]:
        a = re.search(r'<a href="[^"]*npc=(\d+)[^"]*"[^>]*>(.*?)</a>', c, re.S)
        assert f'mode={mode}' in a.group(0), f'{path.name} 卡片連結不是 {mode}：{a.group(0)}'
        mid = int(a.group(1))
        if mid in seen: print('重複', mid, mode); continue
        seen.add(mid); per[mode] = per.get(mode, 0) + 1
        badges = [txt(b) for b in re.findall(r'<span class="px-2 py-0\.5 text-xs rounded[^"]*">(.*?)</span>', c, re.S)]
        stats = {txt(k).rstrip(':'): txt(v) for k, v in re.findall(r'<div><span class="text-gray-400">(.*?)</span>(.*?)</div>', c, re.S)}
        sp = re.search(r'Spawn Window:.*?</div>', c, re.S)
        spawn = {}
        if not sp and 'Locations:' in c:  # diablo 卡片沒有重生資訊，只有地點列
            spawn['Locations'] = [{'map_id': int(i), 'name': txt(t)} for i, t in re.findall(r'guide-map&amp;id=(\d+)[^"]*"[^>]*>(.*?)</a>', c[c.index('Locations:'):], re.S)]
        if sp:
            body = sp.group(0)
            for k in ('Spawn Window', 'Avg Spawns'):
                m = re.search(k + r':</span>\s*<span>(.*?)</span>', body, re.S)
                if m: spawn[k] = txt(m.group(1))
            spawn['Locations'] = [{'map_id': int(i), 'name': txt(t)} for i, t in re.findall(r'guide-map&amp;id=(\d+)[^"]*"[^>]*>(.*?)</a>', body, re.S)]
        img = re.search(r'<img src="([^"]*)"[^>]*alt="([^"]*)"', c)
        icon = None
        if img and img.group(1).startswith(('./', f'{path.stem}_files/')) and (SRC / img.group(1)).exists():
            p = SRC / img.group(1); icon = p.name; shutil.copy(p, OUT / 'images' / 'monsters' / icon)
        bosses.append({'id': mid, 'mode': mode, 'name': txt(a.group(2)), 'badges': badges, 'stats': stats, 'spawn': spawn, 'icon': icon})
(OUT / 'bosses.json').write_text(json.dumps(bosses, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(bosses)} 隻 Boss', per, f'缺圖 {sum(b["icon"] is None for b in bosses)} 隻')

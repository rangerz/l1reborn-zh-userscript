#!/usr/bin/env python3
"""解析手動存檔的擊殺任務頁 .cache/manual/kill_quests.html（?page=kill-quests，120 個任務全在同一頁）
→ data/reborn/kill_quests.json，獎勵圖示複製到 data/reborn/images/kill_quests/。只讀本地檔，不對官網發請求。
每張卡片：任務 ID／名稱／說明、旗標（weekly、daily、boss、combo）、目標怪物（含數量）、地圖、獎勵道具、符文獎勵機率、
掉落來源（哪些怪物掉擊殺任務道具，Standard／Classic 機率）。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
num = lambda s: float(s.replace(',', ''))
(OUT / 'images' / 'kill_quests').mkdir(parents=True, exist_ok=True)

def icon_of(frag):
    img = re.search(r'<img src="(kill_quests_files/[^"]*)"', frag)
    if not (img and (SRC / img.group(1)).exists()): return None
    p = SRC / img.group(1); shutil.copy(p, OUT / 'images' / 'kill_quests' / p.name)
    return p.name

def parse_card(c):
    head, qid = c.split('>', 1)[0], int(re.match(r'(\d+)"', c).group(1))
    t = re.search(r'text-xl font-semibold">#(\d+) — (.*?)</div>\s*<p[^>]*>(.*?)</p>', c, re.S)
    assert t and int(t.group(1)) == qid, f'任務 {qid} 標題格式不符'
    flags = {k: re.search(rf'data-quest-{k}="(\d)"', head).group(1) == '1' for k in ('weekly', 'daily', 'boss', 'combo')}
    badges = [txt(b) for b in re.findall(r'px-3 py-1 rounded-full[^>]*>(.*?)</span>', c, re.S)]
    secs = {txt(k): v for k, v in re.findall(r'<h3[^>]*>(.*?)</h3>(.*?)(?=<h3|\Z)', c, re.S)}
    assert list(secs) == ['Targets', 'Rewards', 'Sources (Kill Quest drops)'], f'任務 {qid} 區塊不符：{list(secs)}'

    targets = []
    for li in re.findall(r'<li[^>]*>(.*?)</li>', secs['Targets'], re.S):
        a = re.search(r'npc=(\d+)', li); m = re.fullmatch(r'(.*?) × ([\d,]+)', txt(li))
        assert a and m, f'任務 {qid} 目標格式不符：{txt(li)}'
        targets.append({'npc_id': int(a.group(1)), 'name': m.group(1), 'count': int(num(m.group(2)))})
    maps = re.search(r'Maps:</span>(.*?)</div>', secs['Targets'], re.S)

    rewards = []
    rw = secs['Rewards']
    for li in re.findall(r'<li[^>]*>(.*?)</li>', rw, re.S):
        a = re.search(r'item=(\d+)', li); m = re.fullmatch(r'(.*?) × ([\d,]+)', txt(li))
        assert a and m, f'任務 {qid} 獎勵格式不符：{txt(li)}'
        rewards.append({'item_id': int(a.group(1)), 'name': m.group(1), 'qty': int(num(m.group(2))), 'icon': icon_of(li)})
    runes = []
    for sp in re.findall(r'<span class="inline-flex items-center gap-1\.5 rounded-full[^>]*>(.*?)</span>\s*</span>', rw, re.S):
        m = re.fullmatch(r'(.*?) ([\d.,]+)% chance', txt(sp))
        assert m, f'任務 {qid} 符文獎勵格式不符：{txt(sp)}'
        runes.append({'name': m.group(1), 'chance_pct': num(m.group(2)), 'icon': icon_of(sp)})
    assert rw.count('<li') == len(rewards) and rw.count('% chance') == len(runes), f'任務 {qid} 獎勵數與解析數不符'

    sources = []
    for tr in re.findall(r'<tbody>(.*?)</tbody>', secs['Sources (Kill Quest drops)'], re.S):
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', tr, re.S):
            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
            a = re.search(r'npc=(\d+)', tds[0])
            pct = [re.fullmatch(r'([\d.,]+)%', txt(x)) for x in tds[1:]]
            assert a and len(tds) == 3 and all(pct), f'任務 {qid} 掉落來源格式不符：{txt(row)}'
            sources.append({'npc_id': int(a.group(1)), 'name': txt(tds[0]), 'standard_pct': num(pct[0].group(1)), 'classic_pct': num(pct[1].group(1))})
    return {'id': qid, 'name': txt(t.group(2)), 'description': txt(t.group(3)), 'badges': badges, **flags,
            'targets': targets, 'maps': [x.strip() for x in txt(maps.group(1)).split(',')] if maps else [],
            'rewards': rewards, 'rune_rewards': runes, 'sources': sources}

h = re.sub(r'<script.*?</script>|<style.*?</style>', '', (SRC / 'kill_quests.html').read_text(encoding='utf-8'), flags=re.S)
listed = int(re.search(r'(\d+) quests', h).group(1))
quests = [parse_card(c) for c in h.split('<div id="kill-quest-')[1:]]
assert len(quests) == listed == len({q['id'] for q in quests}), f'任務 {len(quests)} 個、頁面標示 {listed}'
(OUT / 'kill_quests.json').write_text(json.dumps(quests, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(quests)} 個任務；目標 {sum(len(q["targets"]) for q in quests)}、獎勵 {sum(len(q["rewards"]) for q in quests)}、'
      f'符文獎勵 {sum(len(q["rune_rewards"]) for q in quests)}、掉落來源 {sum(len(q["sources"]) for q in quests)}；'
      f'weekly {sum(q["weekly"] for q in quests)}、daily {sum(q["daily"] for q in quests)}、boss {sum(q["boss"] for q in quests)}、combo {sum(q["combo"] for q in quests)}')

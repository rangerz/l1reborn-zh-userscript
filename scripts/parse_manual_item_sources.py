#!/usr/bin/env python3
"""解析手動取得的道具來源 .cache/manual/items/item_sources_raw.json（{道具ID: item_sources 端點回傳的 HTML 片段}）
→ data/reborn/items/item_sources.json。只讀本地檔，不對官網發請求。
來源分四種：drops（怪物掉落＋機率）、shops（商店＋價格）、boxes（來自寶箱＋數量）、quests（擊殺任務）。"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / '.cache' / 'manual' / 'items' / 'item_sources_raw.json'
OUT = ROOT / 'data' / 'reborn' / 'items'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
num = lambda s: float(s.replace(',', ''))

raw = json.loads(RAW.read_text(encoding='utf-8'))
known = {x['id'] for f in ('weapons', 'armors') for x in json.loads((OUT / f'{f}.json').read_text(encoding='utf-8'))}
assert {int(k) for k in raw} == known, f'道具 ID 與 weapons/armors 不符：缺 {len(known - {int(k) for k in raw})}、多 {len({int(k) for k in raw} - known)}'

out, anchors = {}, 0
for iid in sorted(raw, key=int):
    frag = raw[iid]
    rec = {'drops': [], 'shops': [], 'boxes': [], 'quests': []}
    if 'No sources found.' not in frag:
        for label, body in re.findall(r'<div[^>]*>\s*(Sources|Shop):(.*?)</div>', frag, re.S):
            # 每個來源 = 一個 <a>，其後（逗號前）可帶一個 <span>（機率／數量／價格）
            for href, name, span in re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>\s*(?:<span[^>]*>(.*?)</span>)?', body, re.S):
                anchors += 1
                href, name, span = html.unescape(href), txt(name), txt(span) if span else None
                if label == 'Shop':
                    m = re.fullmatch(r'Shop: (.*)', name); nid = re.search(r'npc=(\d+)', href)
                    assert m and nid and span and span.endswith(' Adena'), f'{iid} 商店格式不符：{name} {span}'
                    rec['shops'].append({'npc_id': int(nid.group(1)), 'name': m.group(1), 'price': int(num(span[:-6]))})
                elif 'kill-quests' in href:
                    q = re.search(r'quest=(\d+)', href); m = re.fullmatch(r'Kill Quest: (.*)', name)
                    assert q and m, f'{iid} 任務格式不符：{name}'
                    rec['quests'].append({'quest_id': int(q.group(1)), 'name': m.group(1)})
                elif name.startswith('Treasure Box: '):  # 連結多半是 item=，少數寶箱是 npc=（同 treasure_boxes.json 的 link）
                    b = re.search(r'(item|npc)=(\d+)', href)
                    assert b and span and re.fullmatch(r'x[\d,]+(, x[\d,]+)*', span), f'{iid} 寶箱格式不符：{name} {span}'
                    rec['boxes'].append({'id': int(b.group(2)), 'link': b.group(1), 'name': name[len('Treasure Box: '):], 'qty': [int(num(q)) for q in re.findall(r'x([\d,]+)', span)]})  # 僅 21033 的 Event Armor Chest 是 'x1, x1'，不猜意義，一律存清單
                else:
                    n = re.search(r'npc=(\d+)', href); m = re.fullmatch(r'(.*?)(?: \(Lv (\d+)\))?', name)
                    assert n, f'{iid} 掉落連結不符：{href}'
                    assert span is None or span.endswith('%'), f'{iid} 機率格式不符：{span}'
                    rec['drops'].append({'npc_id': int(n.group(1)), 'name': m.group(1), 'level': int(m.group(2)) if m.group(2) else None,
                                         'rate_pct': num(span[:-1]) if span else None})
        assert sum(len(v) for v in rec.values()) == len(re.findall(r'<a ', frag)), f'{iid} 解析數與連結數不符'
    out[iid] = rec
(OUT / 'item_sources.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
none = sum(not any(r.values()) for r in out.values())
print(f'{len(out)} 件道具；無來源 {none} 件；來源連結 {anchors} 筆：掉落 {sum(len(r["drops"]) for r in out.values())}、商店 {sum(len(r["shops"]) for r in out.values())}、寶箱 {sum(len(r["boxes"]) for r in out.values())}、任務 {sum(len(r["quests"]) for r in out.values())}')

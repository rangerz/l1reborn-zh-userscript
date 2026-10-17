#!/usr/bin/env python3
"""解析手動取得的道具來源（{道具ID: item_sources 端點回傳的 HTML 片段}）→ data/reborn/items/item_sources.json。只讀本地檔，不對官網發請求。
- .cache/manual/items/item_sources_raw.json：weapons／armors（2243 件）。
- .cache/manual/items/item_sources_part1..N.json：misc.json 裡不在 weapons／armors 的道具（2474 件），每 100 件一個檔。
  端點是 /?page=lookup-items&mode=standard&action=item_sources&item_id=<id>（header X-Requested-With: XMLHttpRequest），查詢卡片按「Load sources」時呼叫的那個。
來源分四種：drops（怪物掉落＋機率；官網沒顯示機率的 rate_pct 存 None，多為 Boss，不是 0%）、shops（商店＋價格＋貨幣）、boxes（來自寶箱＋數量）、quests（擊殺任務）。"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'items'
OUT = ROOT / 'data' / 'reborn' / 'items'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
num = lambda s: float(s.replace(',', ''))

raw = json.loads((SRC / 'item_sources_raw.json').read_text(encoding='utf-8'))
for part in sorted(SRC.glob('item_sources_part*.json'), key=lambda p: int(p.stem.removeprefix('item_sources_part'))):
    new = json.loads(part.read_text(encoding='utf-8'))
    assert not raw.keys() & new.keys(), f'{part.name} 跟已有的道具重複'
    raw.update(new)
known = {x['id'] for f in ('weapons', 'armors', 'misc') for x in json.loads((OUT / f'{f}.json').read_text(encoding='utf-8'))}
assert {int(k) for k in raw} == known, f'道具 ID 與 weapons/armors/misc 不符：缺 {len(known - {int(k) for k in raw})}、多 {len({int(k) for k in raw} - known)}'

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
                    pr = span and re.fullmatch(r'([\d,]+) (.+?)(?: \(x([\d,]+)\))?', span)  # 價格：「N Adena」，少數用別的貨幣（Reborn Feathers、Skull of Reborn）、或帶「(xN)」
                    assert m and nid and pr, f'{iid} 商店格式不符：{name} {span}'
                    rec['shops'].append({'npc_id': int(nid.group(1)), 'name': m.group(1), 'price': int(num(pr.group(1))), 'currency': pr.group(2),
                                         **({'bundle': int(num(pr.group(3)))} if pr.group(3) else {})})  # bundle＝官網標的 (xN)，語意（每個單價或整捆價）未確認，存原值
                elif 'kill-quests' in href:
                    q = re.search(r'quest=(\d+)', href); m = re.fullmatch(r'Kill Quest: (.*)', name)
                    assert q and m, f'{iid} 任務格式不符：{name}'
                    rec['quests'].append({'quest_id': int(q.group(1)), 'name': m.group(1)})
                elif name.startswith('Treasure Box: '):  # 連結多半是 item=，少數寶箱是 npc=（同 treasure_boxes.json 的 link）
                    b = re.search(r'(item|npc)=(\d+)', href)
                    rg = span and re.fullmatch(r'x([\d,]+)-([\d,]+)', span)  # 數量區間 x3-6 → qty_range；否則是數量清單 → qty（兩者擇一）
                    assert b and span and (rg or re.fullmatch(r'x[\d,]+(, x[\d,]+)*', span)), f'{iid} 寶箱格式不符：{name} {span}'
                    rec['boxes'].append({'id': int(b.group(2)), 'link': b.group(1), 'name': name[len('Treasure Box: '):],
                                         **({'qty_range': [int(num(rg.group(1))), int(num(rg.group(2)))]} if rg else {'qty': [int(num(q)) for q in re.findall(r'x([\d,]+)', span)]})})  # 'x1, x1'（21033）或多個數量不猜意義，一律存清單
                else:
                    n = re.search(r'npc=(\d+)', href); m = re.fullmatch(r'(.*?)(?: \(Lv (\d+)\))?', name)
                    assert n, f'{iid} 掉落連結不符：{href}'
                    assert span is None or span.endswith('%'), f'{iid} 機率格式不符：{span}'
                    rec['drops'].append({'npc_id': int(n.group(1)), 'name': m.group(1), 'level': int(m.group(2)) if m.group(2) else None,
                                         'rate_pct': num(span[:-1]) if span else None})
        assert sum(len(v) for v in rec.values()) == len(re.findall(r'<a ', frag)), f'{iid} 解析數與連結數不符'
    out[iid] = rec
# 新格式各釘一筆（改壞 regex 時這裡會擋）
assert out['40743']['shops'] == [{'npc_id': 80075, 'name': 'Beheak', 'price': 2, 'currency': 'Adena', 'bundle': 10}], '商店 (xN) 解析回歸'
assert out['49056']['shops'][0]['currency'] == 'Reborn Feathers', '商店貨幣解析回歸'
assert out['40964']['boxes'][0] == {'id': 500072, 'link': 'item', 'name': 'Event Weapon Chest', 'qty_range': [3, 6]}, '寶箱數量區間解析回歸'
(OUT / 'item_sources.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
none = sum(not any(r.values()) for r in out.values())
print(f'{len(out)} 件道具；無來源 {none} 件；來源連結 {anchors} 筆：掉落 {sum(len(r["drops"]) for r in out.values())}、商店 {sum(len(r["shops"]) for r in out.values())}、寶箱 {sum(len(r["boxes"]) for r in out.values())}、任務 {sum(len(r["quests"]) for r in out.values())}')

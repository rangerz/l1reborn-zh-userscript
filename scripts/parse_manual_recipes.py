#!/usr/bin/env python3
"""解析手動存檔的製作配方 → data/reborn/recipes.json，圖示複製到 data/reborn/items/images/。只讀本地檔，不對官網發請求。
- 列表：.cache/manual/recipes/crafting_guide.html、crafting_guide_p2..p41.html
  （?page=crafting-guide&craftq=&craft_page=N，25 件一頁，共 1001 件）。每件有名稱、圖示、配方數（data-recipe-count）；配方數 0 的只是材料。
- 配方內容：.cache/manual/recipes/recipes_part*.json（{道具ID: 片段 HTML}），片段取自 ?page=crafting-guide&item=<id>&partial=1
  （列表頁展開時才懶載入的那個端點）。只有配方數 > 0 的 533 件有片段。
  配方 = {npc, ingredients}；材料 = {item_id, name, qty, output?, total?, sub_recipes?, circular?}：output／total 是頁面對該材料行標的
  「(Output xM)」「(Total: T)」原值；材料自己可製作時 sub_recipes 是它的配方（多一個 output_qty），官網遇到循環就停並標 circular。
- used-in-guide（?page=used-in-guide&item=<id>）是同一份配方的反向索引（某材料被哪些配方用到），不另外抓，需要時由 recipes.json 反推
  （頂層配方反推的次數與 misc.json 的 used_in_recipes 有 525／533 件相同，其餘差 1）。"""
import html, json, re, shutil
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'recipes'
OUT = ROOT / 'data' / 'reborn'
PER_PAGE, TOTAL = 25, 1001
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()
(OUT / 'items' / 'images').mkdir(parents=True, exist_ok=True)

class Node:
    def __init__(self, tag, attrs, parent): self.tag, self.cls, self.parent, self.kids, self.href = tag, dict(attrs).get('class', ''), parent, [], dict(attrs).get('href', '')
    def text(self): return txt(''.join(k if isinstance(k, str) else k.text() for k in self.kids))
    def find(self, tag): return next((n for n in self.walk() if n.tag == tag), None)
    def walk(self):
        for k in self.kids:
            if isinstance(k, Node): yield k; yield from k.walk()

def tree(frag):
    root = cur = Node('root', [], None)
    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            nonlocal cur
            n = Node(tag, attrs, cur); cur.kids.append(n)
            if tag not in ('img', 'br'): cur = n
        def handle_endtag(self, tag):
            nonlocal cur
            assert cur.tag == tag, f'標籤不成對：{tag} 對 {cur.tag}'
            cur = cur.parent
        def handle_data(self, d): cur.kids.append(d)
    P().feed(frag)
    assert cur is root, '片段標籤沒有收齊'
    return root

NUM = lambda s: int(s.replace(',', ''))

def parse_ul(ul, where):
    """<ul> 的每個 <li> 是一個材料。行文字是「Nx 名稱 (Output xM) (Total: T)」；材料自己可製作時，<li> 內有 div.ml-4 放子配方（<details>）。"""
    out = []
    for li in (k for k in ul.kids if isinstance(k, Node)):
        assert li.tag == 'li', f'{where} <ul> 裡有 {li.tag}'
        a = li.find('a'); line = next(n for n in a.walk() if n.tag == 'span' and n.cls == 'flex min-w-0 flex-col gap-0.5').find('span')
        m = re.fullmatch(r'([\d,]+)x (.*?)((?: \((?:Output x[\d,]+|Total: [\d,]+)\))*)', line.text())
        i = re.search(r'item=(\d+)', a.href)
        assert m and i, f'{where} 材料格式不符：{line.text()}'
        ing = {'item_id': int(i.group(1)), 'name': m.group(2), 'qty': NUM(m.group(1))}
        for k, v in re.findall(r'\((Output x|Total: )([\d,]+)\)', m.group(3)): ing['output' if k == 'Output x' else 'total'] = NUM(v)
        kids = [n for n in li.kids if isinstance(n, Node) and n is not li.kids[0]]
        for n in kids:
            if n.cls == 'ml-4 space-y-2':
                ing['sub_recipes'] = []
                for d in n.kids:
                    s = re.fullmatch(r'Recipe (\d+) \(Output x([\d,]+)\)', d.find('summary').text())
                    assert d.tag == 'details' and s, f'{where} 子配方格式不符：{d.text()[:60]}'
                    r = parse_block(d.find('div'), where); r['output_qty'] = NUM(s.group(2))
                    ing['sub_recipes'].append(r)
            elif 'Circular reference' in n.text(): ing['circular'] = True
            else: raise AssertionError(f'{where} 材料多出：{n.text()[:60]}')
        out.append(ing)
    return out

def parse_block(b, where):
    """一個配方：可選的「NPC: 名稱 (ID)」＋材料清單。"""
    ul = b.find('ul')
    before = []  # 只看第一個 <ul> 之前的 div；之後是材料，裡面子配方的 NPC 不是這個配方的
    for n in b.walk():
        if n is ul: break
        if n.tag == 'div': before.append(n.text())
    npc = re.search(r'NPC: (.*?) \((\d+)\)', next((t for t in before if t.startswith('NPC:')), ''))
    assert ul, f'{where} 配方區塊沒有材料清單'
    ings = parse_ul(ul, where)
    assert ings, f'{where} 配方沒有材料'
    return {'npc': {'id': int(npc.group(2)), 'name': npc.group(1)} if npc else None, 'ingredients': ings}

def parse_fragment(frag, where):
    """片段 = 一個或多個頂層配方區塊（div.p-4）；最後還有一個「Totals when creating all from scratch」小計（由配方推得，不存）。"""
    root = tree(frag)
    blocks = [n for n in root.kids if isinstance(n, Node) and 'border-amber-500/10 bg-black/10 p-4' in n.cls]
    assert blocks, f'{where} 沒有配方區塊'
    recipes = [parse_block(b, where) for b in blocks]
    assert frag.count('<li') == sum(count_ings(r) for r in recipes), f'{where} 材料數與解析數不符'
    return recipes

def count_ings(r): return sum(1 + sum(count_ings(s) for s in g.get('sub_recipes', [])) for g in r['ingredients'])

if __name__ == '__main__':
    items = []
    for n in range(1, TOTAL // PER_PAGE + 2):
        stem = 'crafting_guide' if n == 1 else f'crafting_guide_p{n}'
        h = re.sub(r'<script.*?</script>|<style.*?</style>', '', (SRC / f'{stem}.html').read_text(encoding='utf-8'), flags=re.S)
        page = re.search(r'Page (\d+) of (\d+) · 25 per page', h)
        assert page and int(page.group(1)) == n and int(page.group(2)) == TOTAL // PER_PAGE + 1, f'{stem}.html 頁碼不符：{page and page.group(0)}'
        cards = h.split('<details id="craft-')[1:]
        assert len(cards) == min(PER_PAGE, TOTAL - PER_PAGE * (n - 1)), f'{stem}.html 卡片 {len(cards)} 張'
        for c in cards:
            m = re.match(r'(\d+)"[^>]*data-item-id="(\d+)" data-recipe-count="(\d+)"', c)
            assert m and m.group(1) == m.group(2), f'{stem}.html 卡片格式不符'
            a = re.search(r'<a href="[^"]*item=\d+"[^>]*>\s*<img src="([^"]*)"[^>]*>\s*(.*?)</a>', c, re.S)
            assert a, f'{stem}.html 卡片 {m.group(1)} 沒有名稱連結'
            icon = None
            if a.group(1).startswith(f'{stem}_files/') and (SRC / a.group(1)).exists():
                p = SRC / a.group(1); icon = p.name
                if icon != 'default.webp': shutil.copy(p, OUT / 'items' / 'images' / icon)
            items.append({'id': int(m.group(1)), 'name': txt(a.group(2)), 'icon': icon, 'recipe_count': int(m.group(3))})
    assert len(items) == TOTAL == len({i['id'] for i in items}), f'共 {len(items)} 件'

    frags = {}
    for p in sorted(SRC.glob('recipes_part*.json'), key=lambda p: int(re.search(r'\d+', p.stem).group())):
        frags.update({int(k): v for k, v in json.loads(p.read_text(encoding='utf-8')).items()})
    need = {i['id'] for i in items if i['recipe_count'] > 0}
    assert set(frags) == need, f'片段與配方數>0 的清單不符：缺 {sorted(need - set(frags))[:10]}、多 {sorted(set(frags) - need)[:10]}'
    for it in items:
        it['recipes'] = parse_fragment(frags[it['id']], f'item {it["id"]}') if it['recipe_count'] else []
        assert len(it['recipes']) == it['recipe_count'], f'item {it["id"]} 配方 {len(it["recipes"])} 個、列表標示 {it["recipe_count"]}'
    by = {i['id']: i for i in items}
    assert by[40623]['recipes'][0]['npc'] == {'id': 91050, 'name': 'Druga Veil'} and by[49015]['recipes'][0]['npc'] is None, 'NPC 解析回歸'
    assert sum(r['npc'] is None for i in items for r in i['recipes']) == 95, '無 NPC 的配方數不是 95'
    (OUT / 'recipes.json').write_text(json.dumps(items, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(items)} 件（有配方 {len(need)}、只是材料 {len(items) - len(need)}）；配方 {sum(len(i["recipes"]) for i in items)} 個；缺圖 {sum(i["icon"] is None for i in items)}')

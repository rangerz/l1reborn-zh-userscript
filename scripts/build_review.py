#!/usr/bin/env python3
"""reborn 的 item / monster / boss / set / map 英文名對應 l1justice 3.63c 的繁中名（資料在 data/justice/）。
輸出 data/reborn/zh-names.json（對應表）與 review/data.js（審核網頁用）。只讀本地檔。"""
import json, re, collections
from pathlib import Path
J3 = Path('data/justice')  # 從 l1justice-enhanced 搬進來的 3.63c 資料（i18n.json＝繁中名、classic-names.json＝英文名）
R = Path('data/reborn')
i18n = json.load(open(J3 / 'i18n.json'))
cls = json.load(open(J3 / 'classic-names.json'))
J = lambda p: json.load(open(R / p))

def norm(s):  # 去掉 l1justice 物品名尾巴的 (Normal) - [..]，大小寫與空白統一
    s = re.sub(r'\s*\((Normal|Blessed|Cursed)\)\s*-?\s*(\[.*\])?\s*$', '', s or '')
    s = re.sub(r'\s*\(C\)\s*$', '', s)  # reborn classic 模式怪物後綴
    return re.sub(r'\s+', ' ', s).strip().lower()

def build_index(kind, table):
    cname = cls[kind]
    byname = collections.defaultdict(list)
    for i, nm in cname.items():
        if i in i18n[table]: byname[norm(nm)].append(i)
    return cname, byname

def match(x, kind, table, idx, use_id=True):
    cname, byname = idx
    i = str(x['id'])
    if use_id and i in i18n[table]:
        zh = i18n[table][i]
        same = norm(cname.get(i)) == norm(x['name'])
        return dict(zh=zh, cid=i, cen=cname.get(i), how='id+name' if same else 'id')
    ids = byname.get(norm(x['name']))
    if ids:
        zhs = {i18n[table][j] for j in ids}
        return dict(zh=i18n[table][ids[0]], cid=ids[0], cen=cname[ids[0]], how='name' if len(zhs) == 1 else 'name-multi',
                    alt=sorted(zhs - {i18n[table][ids[0]]}))
    return dict(zh=None, how='none')


# ---- 基本資訊（標籤中譯；原文值不明確的保留英文，括號附原文供 review）----
LBL = {'Damage': '傷害', 'Dmg': '追加傷害', 'Hit': '命中', 'Double Hit %': '雙擊率', 'Range': '射程', 'Handed': '持握',
       'Proc': '特效', 'Type': '類型', 'Material': '材質', 'Safe Enchant': '安定值', 'Weight': '重量', 'Classes': '職業',
       'AC': 'AC', 'HP': 'HP', 'MP': 'MP', 'MR': 'MR', 'HPR': 'HP回復', 'MPR': 'MP回復', 'SP': 'SP', 'DR': '傷害減免',
       'STR': '力量', 'DEX': '敏捷', 'CON': '體質', 'INT': '智力', 'WIS': '精神', 'CHA': '魅力', 'Grade': '等級',
       'Resist Water': '水屬性防禦', 'Resist Fire': '火屬性防禦', 'Resist Earth': '地屬性防禦', 'Resist Wind': '風屬性防禦',
       'Resist Stun': '昏迷耐性', 'Resist Sustain': '支撐耐性', 'Resist Freeze': '凍結耐性', 'Resist Stone': '石化耐性',
       'Resist Sleep': '睡眠耐性', 'Resist Blind': '暗黑耐性', 'Weight Reduction': '負重減輕', 'Haste': '加速',
       'Bow Hit': '弓命中', 'Bow Dmg': '弓傷害', 'Poison Immunity': '毒免疫', 'Magic Dmg Mod': '魔法傷害修正',
       'Unbreakable': '不可損壞', 'Use': '用途', 'Level': 'LV', 'Size': '體型', 'EXP': '經驗值', 'Weak Attr': '弱點屬性',
       'Str/Con/Dex': '力/體/敏', 'Int/Wis': '智/精', 'Family': '族群'}
CLS = {'Royal': '王族', 'Knight': '騎士', 'Wizard': '法師', 'Elf': '妖精', 'Dark Elf': '黑暗妖精', 'Dragon Knight': '龍騎士',
       'Illusionist': '幻術師', 'Warrior': '戰士'}
ELEM = {'Fire': '火', 'Water': '水', 'Wind': '風', 'Earth': '地', '0': '無'}
TYPE = {'sword': '單手劍', 'tohandsword': '雙手劍', 'bow': '弓', 'spear': '長矛', 'singlespear': '單手長矛', 'blunt': '單手鈍器',
        'tohandblunt': '雙手鈍器', 'staff': '魔杖', 'tohandstaff': '雙手魔杖', 'dagger': '匕首', 'claw': '鋼爪', 'edoryu': '雙刀',
        'kiringku': '奇古獸', 'chainsword': '鎖鏈劍', 'singlebow': '單手弓', 'gauntlet': '弓手套',
        'armor': '盔甲', 'helm': '頭盔', 'shield': '盾牌', 'amulet': '項鍊', 'glove': '手套', 'boots': '長靴', 'ring': '戒指',
        'belt': '腰帶', 'cloak': '斗篷', 'earring': '耳環', 'tshirt': 'T恤', 'guarder': '臂甲', 'pattern_back': '背部飾品',
        'questitem': '任務物品', 'other': '其他', 'material': '材料', 'scroll': '卷軸', 'spellbook': '魔法書',
        'treasure_box': '寶箱', 'potion': '藥水', 'food': '食物', 'firecracker': '煙火', 'gem': '寶石', 'petitem': '寵物道具',
        'event': '活動', 'wand': '魔杖', 'arrow': '箭', 'totem': '圖騰', 'light': '光源', 'sting': '飛刀'}
MAT = {'gemstone': '寶石', 'paper': '紙', 'wood': '木', 'leather': '皮革', 'iron': '鐵', 'steel': '鋼', 'bone': '骨',
       'gold': '金', 'cloth': '布', 'animalmatter': '動物', 'glass': '玻璃', 'none': '無', 'silver': '銀', 'vegetation': '植物',
       'blackmithril': '黑米索莉', 'mithril': '米索莉', 'mineral': '礦物', 'platinum': '白金', 'dragonscale': '龍鱗',
       'oriharukon': '奧里哈魯根', 'copper': '銅', 'liquid': '液體', 'web': '蜘蛛網'}
BADGE = {'Aggro': '主動攻擊', 'Boss': 'BOSS', 'NPC': 'NPC', 'Can TU': 'Can TU', 'Tameable': '可馴服', 'Champion': 'Champion'}
SIZE = {'Small': '小型', 'Large': '大型'}
SAFE = {'Cannot be Enchanted': '不可強化', '0, Can Enchant but NOT Safely!': '0（可強化但不安全）'}
def zlbl(k): return LBL.get(k, k)
def zval(k, v):
    if isinstance(v, list): return '、'.join(CLS.get(c, c) for c in v)
    if k == 'Type': return f'{TYPE[v]} ({v})' if v in TYPE else v
    if k == 'Material': return f'{MAT[v]} ({v})' if v in MAT else v
    if k == 'Handed': return {'One-handed': '單手', 'Two-handed': '雙手'}.get(v, v)
    if k == 'Safe Enchant': return SAFE.get(v, v)
    if k == 'Unbreakable': return {'Yes': '是'}.get(v, v)
    if k == 'Weak Attr': return ELEM.get(v, v)
    if k == 'Size': return SIZE.get(v, v)
    return v
WORDS = [('AoE: ', '範圍：'), ('target-centered', '以目標為中心'), ('attacker-centered', '以攻擊者為中心'), ('radius', '半徑'),
         ('-cell', '格'), ('Damage', '傷害'), ('rnd', '隨機'), ('Element', '屬性'), ('Fire', '火'), ('Water', '水'),
         ('Wind', '風'), ('Earth', '地'), ('Disease', '疾病'), ('Proc', '發動')]
def zproc(t):  # 特效字串逐詞置換；沒涵蓋到的英文原樣保留
    for a, b in WORDS: t = t.replace(a, b)
    return t
FIRST = ['Damage', 'Dmg', 'Hit', 'AC', 'Level', 'HP', 'MP', 'Handed', 'Range', 'Double Hit %', 'Proc']
def stat_info(stats, skip=()):
    ks = [k for k in FIRST if k in stats] + [k for k in stats if k not in FIRST]
    return [[zlbl(k), zproc(stats[k]) if k == 'Proc' else zval(k, stats[k])] for k in ks if k not in skip and stats[k] not in ('', None)]
def zbonus(b):  # 套裝加成：'AC -7, Resist Water +25, POLYMORPH 5284'
    out = []
    for part in (b or '').split(', '):
        k, _, v = part.rpartition(' ')
        out.append(f'變身 {v}' if k == 'POLYMORPH' else f'{zlbl(k)} {v}' if k in LBL else part)
    return '，'.join(out)
def extra(x, group):
    info, tags = [], []
    st = x.get('stats') or {}
    if group in ('weapons', 'armors', 'misc'):
        info = stat_info(st, skip=('Use',))  # Use 是內部代碼（normal/none…），不顯示
        if x.get('bless'): tags.append(f"祝福狀態：{x['bless']}")
    elif group in ('monsters', 'bosses'):
        info = stat_info(st, skip=('Family',) if not st.get('Family') else ())
        tags = [BADGE.get(b, b) for b in x.get('badges', [])]
        locs = [l['name'] for l in (x.get('spawn') or {}).get('Locations', [])]
        if locs: info.append(['出沒地點', '、'.join(locs[:6]) + (f' …等{len(locs)}處' if len(locs) > 6 else '')])
        if x.get('drops'): info.append(['掉落物數', len(x['drops'])])
    elif group == 'sets':
        if x.get('bonus'): info.append(['套裝效果', zbonus(x['bonus'])])
        info.append(['部件', '、'.join(f"{it['name']}" for it in x.get('items', []))])
    return info, tags

out = {}
def run(group, rows, kind, table, icon_dir, use_id=True, key='icon'):
    idx = build_index(kind, table); res = []
    for x in rows:
        m = match(x, kind, table, idx, use_id)
        ic = x.get(key)
        res.append(dict(id=x['id'], en=x['name'], img=f'{icon_dir}/{ic}' if ic else None,
                        sub=x.get('kind') or x.get('mode') or '', **dict(zip(('info', 'tags'), extra(x, group))), **m))
    out[group] = res
run('weapons', J('items/weapons.json'), 'items', 'items', 'items/images')
run('armors', J('items/armors.json'), 'items', 'items', 'items/images')
run('misc', J('items/misc.json'), 'items', 'items', 'items/images')
run('monsters', J('monsters.json'), 'monsters', 'monsters', 'images/monsters')
run('bosses', J('bosses.json'), 'monsters', 'monsters', 'images/monsters')
run('maps', J('maps.json'), 'maps', 'maps', 'images/maps', key='image')
# 套裝：reborn 的 id 與 3.63c 不同體系，只用名稱比對
run('sets', [dict(x, icon=(x['items'][0]['icon'] if x.get('items') else None)) for x in J('armor_sets.json')],
    'sets', 'sets', 'items/images', use_id=False)

# 同組內同英文名：沒對到的沿用有對到的（例如 diablo/classic 模式的重複怪）
for rows in out.values():
    known = {r['en'].lower(): r for r in rows if r['zh']}
    for r in rows:
        k = known.get(r['en'].lower())
        if not r['zh'] and k: r.update(zh=k['zh'], cid=k.get('cid'), cen=k.get('cen'), how='same-en')

for g, rows in out.items():
    print(g, len(rows), dict(collections.Counter(r['how'] for r in rows)))
Path('data/reborn/zh-names.json').write_text(json.dumps(
    {g: {str(r['id']) + '|' + r['en']: r['zh'] for r in rows if r['zh']} for g, rows in out.items()}, ensure_ascii=False, indent=1))
Path('review/data.js').write_text('window.DATA=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';')

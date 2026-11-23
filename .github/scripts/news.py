# 뉴스·커뮤니티 제목의 긍정/부정 비율 (사전 방식) — 3시간마다 GitHub에서 실행
import json, os, re, time, html, urllib.request, urllib.parse, datetime as dt
from email.utils import parsedate_to_datetime
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'}
NOW = dt.datetime.now(dt.timezone.utc)
def get(u, t=25):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read().decode('utf8', 'replace')
def clean(s):
    s = html.unescape(html.unescape(re.sub(r'<[^>]+>', '', s or ''))).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()

def rss(u, strip_src=False, hours=48):
    b = get(u); out = []
    for it in re.findall(r'<item[\s>].*?</item>', b, re.S):
        m = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', it, re.S)
        if not m: continue
        t = clean(m.group(1))
        if strip_src: t = re.sub(r'\s+-\s+[^-]{2,60}$', '', t)
        p = re.search(r'<pubDate>(.*?)</pubDate>', it, re.S)
        try:
            if p and (NOW - parsedate_to_datetime(p.group(1).strip())).total_seconds() > hours * 3600: continue
        except Exception: pass
        out.append(t)
    return out

def reddit(sub):
    after = (NOW - dt.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
    try:
        J = json.loads(get(f'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={sub}&limit=100&sort=desc&after={after}'))
    except Exception:
        time.sleep(3); J = json.loads(get(f'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={sub}&limit=100'))
    lim = NOW.timestamp() - 86400
    return [clean(p.get('title', '')) for p in J.get('data', []) if not p.get('stickied') and p.get('title') and (p.get('created_utc') or lim) >= lim]

def dc(gid, pages=3, minor=True):
    out = []
    for pg in range(1, pages + 1):
        b = get(f"https://gall.dcinside.com/{'mgallery/' if minor else ''}board/lists/?id={gid}&page={pg}")
        for row in b.split('<tr class="ub-content')[1:]:
            row = row.split('</tr>')[0]
            num = re.search(r'class="gall_num"[^>]*>\s*(\d+)\s*<', row)
            a = re.search(r'class="gall_tit ub-word">\s*<a\s+href="/(?:mgallery/)?board/view/[^"]*"[^>]*>(.*?)</a>', row, re.S)
            if 'icon_notice' in row[:200] or re.search(r'gall_subject"[^>]*>\s*(?:<b>)?\s*(공지|설문|AD|이슈)', row): continue
            if num and a:
                t = clean(a.group(1))
                if t: out.append(t)
        if pg == 1 and len(out) < 10:
            rows = b.split('<tr class="ub-content')
            open('out/dc_debug.txt', 'w').write(str(len(rows)) + '\n=====\n' + '\n=====\n'.join(r[:900] for r in rows[5:9]) + '\n=====TAIL\n' + b[-3000:])
        time.sleep(1.5)
    return out

SRC = [
 ('cnbc', '미국 언론', 'CNBC', lambda: rss('https://www.cnbc.com/id/15839069/device/rss/rss.html') + rss('https://www.cnbc.com/id/100003114/device/rss/rss.html')),
 ('mw', '미국 언론', 'MarketWatch', lambda: rss('https://feeds.content.dowjones.io/public/rss/mw_topstories') + rss('https://feeds.content.dowjones.io/public/rss/mw_marketpulse')),
 ('gnen', '미국 언론', '구글뉴스(영어)', lambda: rss('https://news.google.com/rss/search?q=stock+market+OR+nasdaq+OR+%22wall+street%22+when:1d&hl=en-US&gl=US&ceid=US:en', True)),
 ('wsb', '레딧', 'r/wallstreetbets', lambda: reddit('wallstreetbets')),
 ('stocks', '레딧', 'r/stocks', lambda: reddit('stocks')),
 ('investing', '레딧', 'r/investing', lambda: reddit('investing')),
 ('gnko', '한국 언론', '구글뉴스(한국)', lambda: rss('https://news.google.com/rss/search?q=%EB%AF%B8%EA%B5%AD%EC%A6%9D%EC%8B%9C+OR+%EB%89%B4%EC%9A%95%EC%A6%9D%EC%8B%9C+OR+%EB%82%98%EC%8A%A4%EB%8B%A5+when:1d&hl=ko&gl=KR&ceid=KR:ko', True)),
 ('dcus', '디시인사이드', '미국 주식 갤러리', lambda: dc('stockus', 3, True)),
]

# ---- 사전 (금융 기사·커뮤니티 제목용) ----
EN_NEG = r"plunge|plunges|plunged|plunging|plummet\w*|tumble\w*|sink|sinks|sank|sinking|slump\w*|crash\w*|sell-?off\w*|rout|routs|loss|losses|lose|loses|losing|lost|fall|falls|fell|falling|drop|drops|dropped|dropping|decline\w*|slide|slides|slid|sliding|fear|fears|feared|panic\w*|worr(?:y|ies|ied)|concern\w*|recession\w*|bear|bears|bearish|bubble\w*|warn|warns|warned|warning\w*|crisis|crises|downgrade\w*|layoffs?|default\w*|bankrupt\w*|lawsuit\w*|probe|probes|investigat\w*|slowdown|weak|weaker|weakness|weakens|miss|misses|missed|terrified|scared|spooked|turmoil|collapse\w*|worst|lowest|wipe[sd]? out|wiped|short seller|bagholder\w*|rekt|tank|tanks|tanked|tanking|bleed\w*|plunging|selling|dump|dumps|dumped|underperform\w*|cut forecast|cuts forecast|hit hard|hits|hammered|slammed|jitters|anxiety|uncertain\w*|volatile|volatility|risk-off|capitulat\w*|down \d|dive|dives|dived|diving|slip|slips|slipped|slipping|wipeout\w*|troubl\w*|battered|fail|fails|failed|failing|gloom\w*|fade|fades|faded|fading|losing streak|sour|sours|soured|souring|retreat\w*|pullback\w*|correction|slash\w*|shorting|crater\w*|downbeat|grim|plight|scam|halted|bloodbath|meltdown|freefall|free fall|going down|goes down|dip|dips|risky|riskiest|fud|fud'd|melting|bagholding|underwater|wrecked|getting crushed|crushed|nuked|bloody"
EN_POS = r"surge|surges|surged|surging|soar\w*|jump|jumps|jumped|jumping|rall(?:y|ies|ied|ying)|gain|gains|gained|rise|rises|rose|rising|climb\w*|rebound\w*|record high|all-time high|new high|highs|beat|beats|upgrade\w*|bullish|bull|bulls|boom\w*|strong|stronger|strength|optimis\w*|moon|mooning|tendies|profit|profits|profitable|growth|best|recover\w*|upside|outperform\w*|approv\w*|tops estimates|top estimates|buy the dip|buying opportunity|bargain|cheap|calls|lifts|lifted|boost\w*|advance\w*|higher|up \d|hikes outlook|raises outlook|raises guidance|raised guidance|success\w*|win|wins|winning|record gains|best day|bounce\w*|upbeat|relief|opportunit\w*|undervalued|below fair value|buy in|buying more|loading up|all-time highs"
KO_NEG = ['폭락','급락','하락','약세','떨어','추락','붕괴','공포','패닉','손실','손절','물렸','물림','반토막','거품','버블','위기','경고','우려','쇼크','침체','떡락','나락','한강','깡통','망했','망함','망하','하방','불안','충격','최저','손해','빠졌','빠짐','털렸','곱버스','인버스','숏','폭탄','비상','악재','매도세','투매','내림세','휘청','먹구름','적신호','경계','조정','부진','급감','하향','곤두박질','출렁','털림','개박살','박살','물렷','ㅠㅠ','ㅜㅜ','ㅠㅜ','하락장','손실률','마이너스','역부족','울상','폭망','실패','하락 마감','급매','투매','공매도','녹고','녹는','녹았','무섭','무서','공백','냄새','곡소리','지옥','탈출','손절각','개미털기']
KO_POS = ['폭등','급등','상승','강세','반등','회복','랠리','신고가','최고치','사상 최고','호재','매수','떡상','불장','돌파','수익','익절','오른다','올랐','오름','기회','줍줍','저점매수','풀매수','상방','훈풍','청신호','호실적','기대감','낙관','순항','껑충','치솟','상승세','오름세','플러스','대박','가즈아','존버 성공','불기둥','양전','신기록','성공','흥행','반색','안도']
ENN = re.compile(r'\b(?:' + EN_NEG + r')\b', re.I); ENP = re.compile(r'\b(?:' + EN_POS + r')\b', re.I)
def score(t):
    if re.search('[가-힣ㄱ-ㅎㅏ-ㅣ]', t):
        n = [w for w in KO_NEG if w in t]; p = [w for w in KO_POS if w in t]
        # '하락'이 '상승'을 포함하지 않도록 겹침 정리: '상승세 꺾여' 같은 표현
        if re.search(r'(상승|반등|랠리)[^ ]{0,4}\s?(꺾|멈|끝|실패|제동)', t): p = [w for w in p if w not in ('상승','반등','랠리','상승세')]; n.append('상승 꺾임')
        if re.search(r'(하락|급락|약세)[^ ]{0,4}\s?(멈|끝|진정|탈출|딛고|만회)', t): n = [w for w in n if w not in ('하락','급락','약세')]; p.append('하락 멈춤')
    else:
        N = [(m.start(), m.group(0).lower()) for m in ENN.finditer(t)]; P = [(m.start(), m.group(0).lower()) for m in ENP.finditer(t)]
        n = [w for _, w in N]; p = [w for _, w in P]
        if N or P:  # 영어 제목은 맨 앞 동사(주어의 움직임)가 핵심 → 가장 먼저 나온 단어에 가중치 2
            first = min(N + P)[0]
            return sum(2 if i == first else 1 for i, _ in P) - sum(2 if i == first else 1 for i, _ in N), p, n
    return len(p) - len(n), p, n

os.makedirs('out', exist_ok=True)
prev = []
try: prev = json.load(open('prev_news_hist.json'))
except Exception: pass
OUT = {'v': 1, 'at': int(time.time()), 'asof': NOW.strftime('%Y-%m-%d %H:%M UTC'), 'src': [], 'grp': {}}
seen = set()
for key, grp, name, fn in SRC:
    o = {'k': key, 'g': grp, 'nm': name, 'n': 0, 'p': 0, 'm': 0, 'z': 0, 'ex': [], 'err': None}
    try:
        T = fn()
        for t in T:
            h = t.lower()[:80]
            if h in seen or len(t) < 4: continue
            seen.add(h); s, p, n = score(t)
            o['n'] += 1; lab = 'p' if s > 0 else 'm' if s < 0 else 'z'; o[lab] += 1
            o['ex'].append([t[:140], lab, p[:3], n[:3]])
    except Exception as e:
        o['err'] = str(e)[:120]
    o['ex'] = o['ex'][:120]; OUT['src'].append(o); print(name, o['n'], o['p'], o['m'], o['z'], o['err'])
    time.sleep(1)
for g in ['미국 언론', '레딧', '한국 언론', '디시인사이드']:
    S = [o for o in OUT['src'] if o['g'] == g]
    n, p, m = sum(o['n'] for o in S), sum(o['p'] for o in S), sum(o['m'] for o in S)
    OUT['grp'][g] = {'n': n, 'p': p, 'm': m, 'idx': round(p / (p + m) * 100) if p + m >= 5 else None}

# ---- 대중 비관도: AAII 개인투자자 설문(매주) · 샌프란시스코 연준 뉴스 감정 지수 ----
def aaii():
    import xlrd
    b = urllib.request.urlopen(urllib.request.Request('https://www.aaii.com/files/surveys/sentiment.xls', headers=UA), timeout=60).read()
    sh = xlrd.open_workbook(file_contents=b).sheet_by_name('SENTIMENT'); R = []
    for i in range(sh.nrows):
        c = sh.row_values(i)
        if isinstance(c[0], float) and c[0] > 30000 and all(isinstance(x, float) for x in c[1:4]):
            R.append((xlrd.xldate_as_datetime(c[0], 0).strftime('%Y-%m-%d'), c[1], c[3]))
    bears = sorted(r[2] for r in R); last = R[-1]
    rank = lambda v: round(sum(1 for x in bears if x <= v) / len(bears) * 100)
    return {'d': last[0], 'bear': round(last[2] * 100, 1), 'bull': round(last[1] * 100, 1), 'avg4': round(sum(r[2] for r in R[-4:]) / 4 * 100, 1),
            'max4': round(max(r[2] for r in R[-4:]) * 100, 1), 'pct': rank(last[2]), 'mean': round(sum(bears) / len(bears) * 100, 1),
            'w': [[r[0], round(r[2] * 100, 1)] for r in R[-12:]]}
def sffed():
    import openpyxl, io
    b = urllib.request.urlopen(urllib.request.Request('https://www.frbsf.org/wp-content/uploads/news_sentiment_data.xlsx', headers=UA), timeout=60).read()
    ws = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)['Data']
    V = [(r[0], r[1]) for r in ws.iter_rows(min_row=2, values_only=True) if r[0] is not None and isinstance(r[1], (int, float))]
    vs = sorted(v for _, v in V); last = V[-1]
    return {'d': str(last[0])[:10], 'v': round(last[1], 3), 'negpct': round(sum(1 for x in vs if x >= last[1]) / len(vs) * 100)}
for k, fn in (('aaii', aaii), ('sffed', sffed)):
    try: OUT[k] = fn(); print(k, OUT[k])
    except Exception as e: OUT[k] = {'err': str(e)[:120]}; print(k, 'fail', e)

# ---- 막스 시장 특징표용 경제·신용 자료 (FRED, 키 없이 CSV) ----
def fred():
    import csv, io
    def ser(i):
        t = urllib.request.urlopen(urllib.request.Request('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + i, headers={'User-Agent': 'curl/8.5.0', 'Accept': '*/*'}), timeout=40).read().decode('utf8', 'replace')  # FRED는 브라우저 UA를 막음
        rows = list(csv.reader(io.StringIO(t)))[1:]
        return [(r[0], float(r[1])) for r in rows if len(r) > 1 and r[1] not in ('', '.')]
    S, H = {}, {}
    for i in ['CFNAIMA3', 'SAHMREALTIME', 'DRTSCILM', 'NFCI', 'NFCICREDIT', 'M2SL', 'FEDFUNDS', 'CPIAUCSL', 'DGS10', 'BAMLH0A0HYM2']:
        try:
            v = ser(i); S[i] = v; H[i] = v if i not in ('DGS10', 'BAMLH0A0HYM2') else v[::5]
        except Exception as e: print('FRED 실패', i, e)
    o = {}
    for i, v in S.items(): o[i] = [v[-1][0], v[-1][1]]
    def yoy(v):
        return round((v[-1][1] / v[-13][1] - 1) * 100, 2) if len(v) > 13 else None
    if 'M2SL' in S: o['m2yoy'] = [S['M2SL'][-1][0], yoy(S['M2SL'])]
    if 'FEDFUNDS' in S and 'CPIAUCSL' in S: o['realff'] = [S['FEDFUNDS'][-1][0], round(S['FEDFUNDS'][-1][1] - yoy(S['CPIAUCSL']), 2)]
    if 'BAMLH0A0HYM2' in S:
        a = [x for _, x in S['BAMLH0A0HYM2']]; o['hypct'] = [S['BAMLH0A0HYM2'][-1][0], round(sum(1 for x in a if x < a[-1]) / len(a) * 100)]
    return o, H
try:
    OUT['fred'], FH = fred(); print('fred', OUT['fred'])
    os.makedirs('out', exist_ok=True); json.dump(FH, open('out/fred_hist.json', 'w'), separators=(',', ':'))
except Exception as e: OUT['fred'] = {'err': str(e)[:120]}; print('fred fail', e)
gi = [v['idx'] for v in OUT['grp'].values() if v['idx'] is not None]
OUT['idx'] = round(sum(gi) / len(gi)) if gi else None
hist = [h for h in prev if isinstance(h, dict) and h.get('at')] + [{'at': OUT['at'], 'idx': OUT['idx'], **{g: v['idx'] for g, v in OUT['grp'].items()}}]
hist = hist[-720:]  # 3시간마다 → 약 90일
os.makedirs('out', exist_ok=True)
json.dump(OUT, open('out/news.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(hist, open('out/news_hist.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('idx', OUT['idx'], OUT['grp'])

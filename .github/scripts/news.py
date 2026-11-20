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
    J = json.loads(get(f'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={sub}&limit=100&sort=desc&after={after}'))
    return [clean(p.get('title', '')) for p in J.get('data', []) if not p.get('stickied') and p.get('title')]

def dc(gid, pages=3, minor=True):
    out = []
    for pg in range(1, pages + 1):
        b = get(f"https://gall.dcinside.com/{'mgallery/' if minor else ''}board/lists/?id={gid}&page={pg}")
        for row in b.split('<tr class="ub-content')[1:]:
            row = row.split('</tr>')[0]
            num = re.search(r'class="gall_num"[^>]*>\s*(\d+)\s*<', row)
            a = re.search(r'class="gall_tit ub-word">\s*<a href="/(?:mgallery/)?board/view/[^"]*"[^>]*>(.*?)</a>', row, re.S)
            if num and a:
                t = clean(a.group(1))
                if t: out.append(t)
        time.sleep(1.5)
    return out

SRC = [
 ('cnbc', '미국 언론', 'CNBC', lambda: rss('https://www.cnbc.com/id/15839069/device/rss/rss.html') + rss('https://www.cnbc.com/id/100003114/device/rss/rss.html')),
 ('mw', '미국 언론', 'MarketWatch', lambda: rss('https://feeds.content.dowjones.io/public/rss/mw_topstories') + rss('https://feeds.content.dowjones.io/public/rss/mw_marketpulse')),
 ('wsj', '미국 언론', 'WSJ', lambda: rss('https://feeds.a.dj.com/rss/RSSMarketsMain.xml')),
 ('gnen', '미국 언론', '구글뉴스(영어)', lambda: rss('https://news.google.com/rss/search?q=stock+market+OR+nasdaq+OR+%22wall+street%22+when:1d&hl=en-US&gl=US&ceid=US:en', True)),
 ('wsb', '레딧', 'r/wallstreetbets', lambda: reddit('wallstreetbets')),
 ('stocks', '레딧', 'r/stocks', lambda: reddit('stocks')),
 ('investing', '레딧', 'r/investing', lambda: reddit('investing')),
 ('gnko', '한국 언론', '구글뉴스(한국)', lambda: rss('https://news.google.com/rss/search?q=%EB%AF%B8%EA%B5%AD%EC%A6%9D%EC%8B%9C+OR+%EB%89%B4%EC%9A%95%EC%A6%9D%EC%8B%9C+OR+%EB%82%98%EC%8A%A4%EB%8B%A5+when:1d&hl=ko&gl=KR&ceid=KR:ko', True)),
 ('dcus', '디시인사이드', '미국 주식 갤러리', lambda: dc('stockus', 3, True)),
]

# ---- 사전 (금융 기사·커뮤니티 제목용) ----
EN_NEG = r"plunge|plunges|plunged|plunging|plummet\w*|tumble\w*|sink|sinks|sank|sinking|slump\w*|crash\w*|sell-?off\w*|rout|routs|loss|losses|lose|loses|losing|lost|fall|falls|fell|falling|drop|drops|dropped|dropping|decline\w*|slide|slides|slid|sliding|fear|fears|feared|panic\w*|worr(?:y|ies|ied)|concern\w*|recession\w*|bear|bears|bearish|bubble\w*|warn|warns|warned|warning\w*|crisis|crises|downgrade\w*|layoffs?|default\w*|bankrupt\w*|lawsuit\w*|probe|probes|investigat\w*|slowdown|weak|weaker|weakness|weakens|miss|misses|missed|terrified|scared|spooked|turmoil|collapse\w*|worst|lowest|wipe[sd]? out|wiped|short seller|bagholder\w*|rekt|tank|tanks|tanked|tanking|bleed\w*|red|plunging|selling|dump|dumps|dumped|underperform\w*|cut forecast|cuts forecast|hit hard|hits|hammered|slammed|jitters|anxiety|uncertain\w*|volatile|volatility|risk-off|capitulat\w*|puts|down \d"
EN_POS = r"surge|surges|surged|surging|soar\w*|jump|jumps|jumped|jumping|rall(?:y|ies|ied|ying)|gain|gains|gained|rise|rises|rose|rising|climb\w*|rebound\w*|record high|all-time high|new high|highs|beat|beats|upgrade\w*|bullish|bull|bulls|boom\w*|strong|stronger|strength|optimis\w*|moon|mooning|tendies|profit|profits|profitable|growth|best|recover\w*|green|upside|outperform\w*|approv\w*|tops estimates|top estimates|buy the dip|buying opportunity|bargain|cheap|calls|lifts|lifted|boost\w*|advance\w*|higher|up \d"
KO_NEG = ['폭락','급락','하락','약세','떨어','추락','붕괴','공포','패닉','손실','손절','물렸','물림','반토막','거품','버블','위기','경고','우려','쇼크','침체','떡락','나락','한강','깡통','망했','망함','망하','하방','불안','충격','최저','손해','빠졌','빠짐','털렸','곱버스','인버스','숏','폭탄','비상','악재','매도세','투매','내림세','휘청','먹구름','적신호','경계','조정','부진','급감','하향','곤두박질','출렁','털림','개박살','박살','좆','시발','ㅅㅂ','ㅠ','ㅜ','하락장','손실률','마이너스']
KO_POS = ['폭등','급등','상승','강세','반등','회복','랠리','신고가','최고치','사상 최고','호재','매수','떡상','불장','돌파','수익','익절','오른다','올랐','오름','기회','줍줍','저점매수','풀매수','상방','훈풍','청신호','호실적','기대감','낙관','순항','껑충','치솟','상승세','오름세','플러스','대박','ㅋㅋ','가즈아','갓','존버 성공','불기둥','양전','신기록']
ENN = re.compile(r'\b(?:' + EN_NEG + r')\b', re.I); ENP = re.compile(r'\b(?:' + EN_POS + r')\b', re.I)
def score(t):
    if re.search('[가-힣ㄱ-ㅎㅏ-ㅣ]', t):
        n = [w for w in KO_NEG if w in t]; p = [w for w in KO_POS if w in t]
        # '하락'이 '상승'을 포함하지 않도록 겹침 정리: '상승세 꺾여' 같은 표현
        if re.search(r'(상승|반등|랠리)[^ ]{0,4}\s?(꺾|멈|끝|실패|제동)', t): p = [w for w in p if w not in ('상승','반등','랠리','상승세')]; n.append('상승 꺾임')
        if re.search(r'(하락|급락|약세)[^ ]{0,4}\s?(멈|끝|진정|탈출|딛고|만회)', t): n = [w for w in n if w not in ('하락','급락','약세')]; p.append('하락 멈춤')
    else:
        n = [m.group(0).lower() for m in ENN.finditer(t)]; p = [m.group(0).lower() for m in ENP.finditer(t)]
    return len(p) - len(n), p, n

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
gi = [v['idx'] for v in OUT['grp'].values() if v['idx'] is not None]
OUT['idx'] = round(sum(gi) / len(gi)) if gi else None
hist = [h for h in prev if isinstance(h, dict) and h.get('at')] + [{'at': OUT['at'], 'idx': OUT['idx'], **{g: v['idx'] for g, v in OUT['grp'].items()}}]
hist = hist[-720:]  # 3시간마다 → 약 90일
os.makedirs('out', exist_ok=True)
json.dump(OUT, open('out/news.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(hist, open('out/news_hist.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('idx', OUT['idx'], OUT['grp'])

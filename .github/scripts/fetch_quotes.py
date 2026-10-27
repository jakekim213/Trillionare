# 라오어 계산표 시세 자동 수집 — GitHub Actions가 15분마다 실행
# q.json: 시세판·판정용 (3개월 일봉 종가, 앱과 같은 17종목) — 매번
# g.json: 그래프용 진짜 봉(시가·고가·저가·종가) 5종목 × 일봉5년·주봉전체·월봉전체 + 1년 1시간 종가 — 6시간마다
import json, os, time, urllib.request, urllib.parse
SYMS = ['TQQQ','QLD','NVDA','PLTR','META','TSLA','TECL','000660.KS','005930.KS','009150.KS','^NDX','^VIX','KRW=X','^IXIC','^GSPC','GC=F','BTC-USD']
G5 = ['^IXIC','^NDX','^GSPC','GC=F','BTC-USD']
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept': 'application/json'}
OUT = 'out'; os.makedirs(OUT, exist_ok=True)

def get(path):
    last = None
    for host in ('query1', 'query2'):
        for i in range(3):
            try:
                req = urllib.request.Request(f'https://{host}.finance.yahoo.com{path}', headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.load(r)
            except Exception as e:
                last = e; print('retry', host, path[:60], e); time.sleep(3 + 4 * i)
    raise last

def spark(syms, rng, iv):
    return get('/v8/finance/spark?symbols=' + ','.join(urllib.parse.quote(s, safe='') for s in syms) + f'&range={rng}&interval={iv}')

def ohlc(sym, rng, iv):
    # range=max 는 Yahoo가 3개월 단위로 뭉쳐 버림 → 전체 기간은 period1=0(1970년)부터 직접 지정해야 진짜 주봉·월봉이 옴
    q = f'range={rng}' if rng != 'max' else f'period1=0&period2={int(time.time())}'
    R = get(f'/v8/finance/chart/{urllib.parse.quote(sym, safe="")}?{q}&interval={iv}')['chart']['result'][0]
    q = R['indicators']['quote'][0]; o = {'t': [], 'o': [], 'h': [], 'l': [], 'c': []}
    for i, t in enumerate(R['timestamp']):
        c = q['close'][i]
        if c is None or c <= 0: continue
        op, hi, lo = q['open'][i], q['high'][i], q['low'][i]
        ok = all(v is not None and v > 0 for v in (op, hi, lo))
        op = op if ok else c; hi = max(hi, c, op) if ok else c; lo = min(lo, c, op) if ok else c
        o['t'].append(t * 1000)
        for k, v in (('o', op), ('h', hi), ('l', lo), ('c', c)): o[k].append(float(f'{v:.7g}'))
    # Yahoo는 주봉·월봉 끝에 '지금 값' 한 점을 따로 붙임 → 같은 주·같은 달이면 앞 봉에 합침(시가는 앞 봉, 고가·저가는 둘 중 큰·작은 값, 종가는 지금 값)
    if iv in ('1wk', '1mo') and len(o['t']) >= 2:
        import datetime as dt
        k = lambda ms: (lambda d: (d.isocalendar()[0], d.isocalendar()[1]) if iv == '1wk' else (d.year, d.month))(dt.datetime.utcfromtimestamp(ms / 1000))
        if k(o['t'][-1]) == k(o['t'][-2]):
            o['h'][-2] = max(o['h'][-2], o['h'][-1]); o['l'][-2] = min(o['l'][-2], o['l'][-1]); o['c'][-2] = o['c'][-1]
            for x in o.values(): x.pop()
    return o

now = int(time.time())
J = spark(SYMS, '3mo', '1d')
if not J.get('^NDX') or not J.get('TQQQ'): raise SystemExit('나스닥100/TQQQ 시세 없음')
json.dump({'at': now, 'spark': J}, open(f'{OUT}/q.json', 'w'), separators=(',', ':'))
print('q.json ok', len(json.dumps(J)) // 1024, 'KB')

prev = None
try: prev = json.load(open('prev_g.json'))
except Exception: pass
if prev and prev.get('v') == 4 and now - prev.get('at', 0) < 6 * 3600:
    json.dump(prev, open(f'{OUT}/g.json', 'w'), separators=(',', ':')); print('g.json 이전 것 유지')
else:
    C = {}
    for s in G5:
        C[s] = {}
        for u, rng, iv in (('d', '5y', '1d'), ('w', 'max', '1wk'), ('m', 'max', '1mo')):
            try: C[s][u] = ohlc(s, rng, iv)
            except Exception as e: print('봉 실패', s, u, e)
            time.sleep(1)
    H = {}
    try: H = spark(G5, '1y', '1h')
    except Exception as e: print('1시간 실패', e)
    if not any(C[s] for s in C) and prev: C = prev.get('c', {})
    json.dump({'v': 4, 'at': now, 'c': C, 'h': H}, open(f'{OUT}/g.json', 'w'), separators=(',', ':'))
    print('g.json 새로 만듦', os.path.getsize(f'{OUT}/g.json') // 1024, 'KB')

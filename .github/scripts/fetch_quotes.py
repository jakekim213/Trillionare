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
    R = get(f'/v8/finance/chart/{urllib.parse.quote(sym, safe="")}?range={rng}&interval={iv}')['chart']['result'][0]
    q = R['indicators']['quote'][0]; o = {'t': [], 'o': [], 'h': [], 'l': [], 'c': []}
    for i, t in enumerate(R['timestamp']):
        c = q['close'][i]
        if c is None or c <= 0: continue
        op, hi, lo = q['open'][i], q['high'][i], q['low'][i]
        ok = all(v is not None and v > 0 for v in (op, hi, lo))
        op = op if ok else c; hi = max(hi, c, op) if ok else c; lo = min(lo, c, op) if ok else c
        o['t'].append(t * 1000)
        for k, v in (('o', op), ('h', hi), ('l', lo), ('c', c)): o[k].append(float(f'{v:.7g}'))
    return o

now = int(time.time())
J = spark(SYMS, '3mo', '1d')
if not J.get('^NDX') or not J.get('TQQQ'): raise SystemExit('나스닥100/TQQQ 시세 없음')
json.dump({'at': now, 'spark': J}, open(f'{OUT}/q.json', 'w'), separators=(',', ':'))
print('q.json ok', len(json.dumps(J)) // 1024, 'KB')

prev = None
try: prev = json.load(open('prev_g.json'))
except Exception: pass
if prev and now - prev.get('at', 0) < 6 * 3600:
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
    json.dump({'at': now, 'c': C, 'h': H}, open(f'{OUT}/g.json', 'w'), separators=(',', ':'))
    print('g.json 새로 만듦', os.path.getsize(f'{OUT}/g.json') // 1024, 'KB')

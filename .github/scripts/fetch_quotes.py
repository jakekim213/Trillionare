# 라오어 계산표 시세 자동 수집 — GitHub Actions가 15분마다 실행
# q.json: 시세판·판정용 (3개월 일봉 종가, 앱과 같은 17종목) — 매번
# g.json: 그래프용 진짜 봉(시가·고가·저가·종가) 5종목 × 일봉5년·주봉전체·월봉전체 + 1년 1시간 종가 — 6시간마다
import json, os, time, urllib.request, urllib.parse
SYMS = ['TQQQ','QLD','NVDA','PLTR','META','TSLA','TECL','000660.KS','005930.KS','009150.KS','^NDX','^VIX','KRW=X','^IXIC','^GSPC','GC=F','BTC-USD','NQ=F','ES=F','SPXL']
G5 = ['^IXIC','^NDX','NQ=F','^GSPC','ES=F','GC=F','BTC-USD']
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
# Yahoo 일봉은 장 마감 뒤 몇 시간 동안 '오늘' 종가가 비어(None) 오는 때가 있음(주식·ETF) → 하루치 5분 자료의 마지막 정규장 값으로 채움
try:
    NUL = [s for s, o in J.items() if o.get('close') and o['close'][-1] is None]
    for i in range(0, len(NUL), 20):
        F = spark(NUL[i:i + 20], '1d', '5m')
        for s in NUL[i:i + 20]:
            o, f = J[s], F.get(s) or {}
            c = [(tt, x) for tt, x in zip(f.get('timestamp') or [], f.get('close') or []) if x]
            if c and time.strftime('%Y-%m-%d', time.gmtime(c[-1][0] - 5 * 3600)) == time.strftime('%Y-%m-%d', time.gmtime(o['timestamp'][-1] - 5 * 3600)):
                o['close'][-1] = c[-1][1]
    if NUL: print('빈 종가 채움', NUL)
except Exception as e: print('빈 종가 채우기 실패', e)
# 시세판용 '지금 값': 하루치 5분 종가의 마지막 점 ÷ 직전 거래일 정산가(chartPreviousClose)
# (3개월 일봉은 선물·금의 '방금 끝난 날' 봉이 빠지는 때가 있어 등락률이 틀어짐 → 따로 받음)
QF = {}
try:
    F = spark(G5, '1d', '5m')
    for s in G5:
        o = F.get(s) or {}; c = [(t, x) for t, x in zip(o.get('timestamp') or [], o.get('close') or []) if x]
        pc = o.get('chartPreviousClose') or o.get('previousClose')
        if c and pc: QF[s] = {'p': c[-1][1], 'pc': pc, 't': c[-1][0]}
except Exception as e: print('qf 실패', e)
json.dump({'at': now, 'spark': J, 'qf': QF}, open(f'{OUT}/q.json', 'w'), separators=(',', ':'))
print('q.json ok', len(json.dumps(J)) // 1024, 'KB')

prev = None
try: prev = json.load(open('prev_g.json'))
except Exception: pass
if prev and prev.get('v') == 7 and now - prev.get('at', 0) < 6 * 3600:
    json.dump(prev, open(f'{OUT}/g.json', 'w'), separators=(',', ':')); print('g.json 이전 것 유지')
else:
    C = {}
    for s in G5:
        C[s] = {}
        for u, rng, iv in (('d', '5y', '1d'), ('w', 'max', '1wk'), ('m', 'max', '1mo')):
            try: C[s][u] = ohlc(s, rng, iv)
            except Exception as e: print('봉 실패', s, u, e)
            time.sleep(1)
        # 최근 5년치 주봉·월봉은 일봉으로 다시 만듦 (Yahoo의 주·월봉은 마지막 봉에 '오늘 값'이 섞이는 등 어긋나는 경우가 있음) — 그 이전은 Yahoo 주·월봉 그대로
        import datetime as dt
        d = C[s].get('d')
        for u in ('w', 'm'):
            x = C[s].get(u)
            if not d or not x: continue
            key = lambda ms: (lambda z: tuple(z.isocalendar()[:2]) if u == 'w' else (z.year, z.month))(dt.datetime.utcfromtimestamp(ms / 1000))
            groups = {}
            for i, t in enumerate(d['t']): groups.setdefault(key(t), []).append(i)
            ks = list(groups)[1:]          # 첫 묶음은 중간부터 시작했을 수 있어 버림
            if not ks: continue
            first = ks[0]; y = {k_: [] for k_ in ('t', 'o', 'h', 'l', 'c')}
            for i, t in enumerate(x['t']):
                if key(t) < first:
                    for k_ in y: y[k_].append(x[k_][i])
            for kk in ks:
                ix = groups[kk]
                for k_, v in zip(('t', 'o', 'h', 'l', 'c'), (d['t'][ix[0]], d['o'][ix[0]], max(d['h'][i] for i in ix), min(d['l'][i] for i in ix), d['c'][ix[-1]])): y[k_].append(v)
            C[s][u] = y
    H = {}
    try: H = spark(G5, '1y', '1h')
    except Exception as e: print('1시간 실패', e)
    if not any(C[s] for s in C) and prev: C = prev.get('c', {})
    json.dump({'v': 7, 'at': now, 'c': C, 'h': H}, open(f'{OUT}/g.json', 'w'), separators=(',', ':'))
    print('g.json 새로 만듦', os.path.getsize(f'{OUT}/g.json') // 1024, 'KB')


# ===== 나스닥100 공포·탐욕 지수 (라오어판) — 15분마다 새로 계산 (fg.json) =====
try:
    import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fg_calc, datetime as dt
    pf = None
    try: pf = json.load(open('prev_fg.json'))
    except Exception: pass
    if pf and pf.get('v') == 1 and now - pf.get('at', 0) < 15 * 60:
        json.dump(pf, open(f'{OUT}/fg.json', 'w'), separators=(',', ':')); print('fg.json 이전 것 유지')
    else:
        S = {}
        for sym in ('^NDX', '^VXN', '^VIX', 'QQQ', 'TLT'):
            R = get(f'/v8/finance/chart/{urllib.parse.quote(sym, safe="")}?range=5y&interval=1d')['chart']['result'][0]
            cl = R['indicators']['quote'][0]['close']; aj = (R['indicators'].get('adjclose') or [{}])[0].get('adjclose') or cl
            v = aj if sym in ('QQQ', 'TLT') else cl
            S[sym] = {dt.datetime.utcfromtimestamp(t - 5 * 3600).strftime('%Y-%m-%d'): x for t, x in zip(R['timestamp'], v) if x}
            time.sleep(0.5)
        D = sorted(S['^NDX'])
        def col(sym):
            o, last, gap = [], None, 0
            for d in D:
                x = S[sym].get(d)
                if x is None and last is not None and gap < 3: x = last; gap += 1
                elif x is not None: gap = 0
                o.append(x); last = x if x is not None else last
            return o
        Nn = [S['^NDX'][d] for d in D]
        sc, pc = fg_calc.calc(D, Nn, col('^VXN'), col('^VIX'), col('QQQ'), col('TLT'))
        k = len(D) - 260
        ma200 = sum(Nn[-200:]) / 200
        out = {'v': 1, 'at': now, 'd': D[k:], 's': [None if x is None else round(x, 1) for x in sc[k:]],
               'p': {n: (None if pc[n][-1] is None else round(pc[n][-1])) for n in fg_calc.NAMES},
               'ndx': Nn[-1], 'ma200': round(ma200, 2), 'vxn': S['^VXN'].get(D[-1]), 'vix': S['^VIX'].get(D[-1])}
        json.dump(out, open(f'{OUT}/fg.json', 'w'), separators=(',', ':')); print('fg.json 새로 계산', D[-1], out['s'][-1], out['p'])
except Exception as e:
    print('fg.json 실패', e)
    try:
        if pf: json.dump(pf, open(f'{OUT}/fg.json', 'w'), separators=(',', ':'))
    except Exception: pass


# ===== TQQQ 구성종목: 보유 내역(하루 1번 바뀜 → 6시간마다) + 지금 등락(매번) =====
try:
    import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import hold
    ph = None
    try: ph = json.load(open('prev_hold.json'))
    except Exception: pass
    H = ph
    if not ph or now - ph.get('at', 0) > 6 * 3600:
        try:
            H = hold.parse(hold.raw('https://accounts.profunds.com/etfdata/ByFund/TQQQ-psdlyhld.csv').decode('utf-8', 'replace')); H['at'] = now
            print('hold.json 새로', H['asof'], len(H['w']))
        except Exception as e: print('보유 내역 실패', e)
    if H:
        json.dump(H, open(f'{OUT}/hold.json', 'w'), separators=(',', ':'), ensure_ascii=False)
        q, x = hold.quotes(get, [w[0] for w in H['w']])
        json.dump({'at': now, 'q': q, 'x': x}, open(f'{OUT}/cq.json', 'w'), separators=(',', ':'))
        print('cq.json', len(q), len(x))
except Exception as e:
    print('구성종목 실패', e)

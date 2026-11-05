# TQQQ 실제 보유 내역(ProShares 매일 공개 CSV) → hold.json · 구성종목 시세 → cq.json
import csv, io, json, time, urllib.request, urllib.parse
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36'}
def raw(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read()

def parse(txt):
    R = list(csv.reader(io.StringIO(txt)))
    asof = R[1][0].replace('AS OF', '').strip()
    m, d, y = asof.split('/'); asof = f'{y}-{int(m):02d}-{int(d):02d}'
    rows = R[4:]
    st = [r for r in rows if len(r) > 9 and r[2] and r[9] and r[2] != 'IQMM']
    mv = sum(float(r[9]) for r in st)
    ex = lambda f: sum(float(r[8]) for r in rows if len(r) > 8 and r[8] and f(r))
    sw = ex(lambda r: 'SWAP' in r[4].upper()); fu = ex(lambda r: 'E-MINI' in r[4].upper() or 'FUTURE' in r[4].upper())
    tot = mv + sw + fu
    w = sorted([[r[2], r[4], round(float(r[9]) / mv * 100, 3)] for r in st], key=lambda x: -x[2])
    return {'v': 1, 'asof': asof, 'w': w, 'mix': {'stock': round(mv / tot * 100, 1), 'swap': round(sw / tot * 100, 1), 'fut': round(fu / tot * 100, 1), 'nb': sum(1 for r in rows if 'SWAP' in (r[4] if len(r) > 4 else '').upper())}, 'expo': round(tot / 1e9, 1)}

def quotes(get, syms):
    """정규장: spark 20개씩 · 시간외: 상위 12종목 chart(comparisons, includePrePost)"""
    q, x = {}, {}
    for i in range(0, len(syms), 20):
        try:
            J = get('/v8/finance/spark?symbols=' + ','.join(urllib.parse.quote(s, safe='') for s in syms[i:i + 20]) + '&range=1d&interval=5m')
            for s, o in J.items():
                c = [(t, v) for t, v in zip(o.get('timestamp') or [], o.get('close') or []) if v]
                pc = o.get('chartPreviousClose') or o.get('previousClose')
                if c and pc: q[s] = [c[-1][1], pc, c[-1][0]]
        except Exception as e: print('구성 시세 실패', i, e)
        time.sleep(0.5)
    for g in (syms[:6], syms[6:12]):
        try:
            R = get(f'/v8/finance/chart/{urllib.parse.quote(g[0], safe="")}?range=1d&interval=5m&includePrePost=true&comparisons=' + ','.join(urllib.parse.quote(s, safe='') for s in g[1:]))['chart']['result'][0]
            T = R['timestamp']
            series = [(g[0], R['indicators']['quote'][0]['close'])] + [(c['symbol'], c['close']) for c in R.get('comparisons', [])]
            for s, C in series:
                k = max((i for i, v in enumerate(C) if v), default=None)
                if k is not None: x[s] = [C[k], T[k]]
        except Exception as e: print('시간외 실패', g[0], e)
    return q, x

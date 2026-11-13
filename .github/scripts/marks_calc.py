# 🌡️ 시장 온도·최종 판단용 자료 (marks.json) — 3시간마다 새로 계산, 그 사이엔 이전 것 유지
# CAPE·PER(multpl.com), 나스닥100 일봉, VXN, HYG·IEF(회사채 분위기), 10년 백분위 눈금, 그동안의 기분 온도
import json, re, time, urllib.request, urllib.parse, datetime as dt
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
def html(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r: return r.read().decode('utf-8', 'replace')
def mtable(url):
    h = html(url)
    rows = re.findall(r"<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>\s*<td>\s*(?:<abbr[^>]*>.*?</abbr>)?\s*(?:&#x2002;)?\s*([\d.]+)\s*</td>", h, re.S)
    out = []
    for d, v in rows:
        out.append((dt.datetime.strptime(d, '%b %d, %Y').strftime('%Y-%m-%d'), float(v)))
    return sorted(out)
def series(get, sym, years, adj=False):
    p1 = int(time.time() - years * 365.25 * 86400)
    R = get(f'/v8/finance/chart/{urllib.parse.quote(sym, safe="")}?period1={p1}&period2={int(time.time())}&interval=1d')['chart']['result'][0]
    cl = R['indicators']['quote'][0]['close']
    if adj: cl = (R['indicators'].get('adjclose') or [{}])[0].get('adjclose') or cl
    raw = R['indicators']['quote'][0]['close']
    o = {}
    for t, x, r in zip(R['timestamp'], cl, raw):
        if x: o[dt.datetime.utcfromtimestamp(t - 5 * 3600).strftime('%Y-%m-%d')] = (x, r)
    return o
def quant(vals, n=201):
    v = sorted(x for x in vals if x is not None)
    if len(v) < 300: return None
    return [round(v[min(len(v) - 1, int(round(i / (n - 1) * (len(v) - 1))))], 5) for i in range(n)]
def pr(q, x):
    if x is None or q is None: return None
    if x <= q[0]: return 0.0
    if x >= q[-1]: return 100.0
    i = 1
    while q[i] < x: i += 1
    a, b = q[i - 1], q[i]; f = (x - a) / (b - a) if b > a else 0.5
    return (i - 1 + f) / (len(q) - 1) * 100
def build(get, fgj):
    out = {'v': 1, 'at': int(time.time())}
    # --- CAPE·PER ---
    try:
        C = mtable('https://www.multpl.com/shiller-pe/table/by-month'); time.sleep(1)
        P = mtable('https://www.multpl.com/s-p-500-pe-ratio/table/by-month')
        out['cape'], out['capeD'] = C[-1][1], C[-1][0]
        out['pe'], out['peD'] = P[-1][1], P[-1][0]
        pm = dict(P)
        out['M'] = [[d[:7], c, pm.get(d)] for d, c in C[-30:] if d.endswith('-01')]  # 매달 1일 값 (최근 2년여)
        out['Mnow'] = [C[-1][0][:7], C[-1][1], P[-1][1]]
    except Exception as e:
        print('multpl 실패', e)
    # --- 나스닥100·VXN·HYG·IEF·S&P500 ---
    N = series(get, '^NDX', 11.3); time.sleep(0.5)
    V = series(get, '^VXN', 10.5); time.sleep(0.5)
    H = series(get, 'HYG', 11.5, True); time.sleep(0.5)
    I = series(get, 'IEF', 11.5, True); time.sleep(0.5)
    G = series(get, '^GSPC', 0.2)
    D = sorted(N); nv = [N[d][0] for d in D]
    dist, ret = {}, {}
    for i, d in enumerate(D):
        if i >= 199: dist[d] = nv[i] / (sum(nv[i - 199:i + 1]) / 200) - 1
        if i >= 252: ret[d] = nv[i] / nv[i - 252] - 1
    HD = sorted(set(H) & set(I)); rt = [H[d][0] / I[d][0] for d in HD]; cr = {}
    for i, d in enumerate(HD):
        if i >= 251: cr[d] = rt[i] / (sum(rt[i - 251:i + 1]) / 252) - 1
    ten = (dt.date.fromisoformat(D[-1]) - dt.timedelta(days=3652)).isoformat()
    Q = {'dist': quant([v for d, v in dist.items() if d >= ten]), 'ret1y': quant([v for d, v in ret.items() if d >= ten]),
         'vxn': quant([v[0] for d, v in V.items() if d >= ten]), 'credit': quant([v for d, v in cr.items() if d >= ten])}
    out['Q'] = {k: v for k, v in Q.items() if v}
    out['end'] = D[-1]
    out['N'] = [[d, round(N[d][0], 2)] for d in D[-330:]]
    out['R'] = [round(x, 6) for x in rt[-260:]]; out['Rd'] = HD[-1]
    out['hr'], out['ir'] = H[HD[-1]][1], I[HD[-1]][1]
    vd = sorted(V); out['vxn'] = V[vd[-1]][0]
    gd = [d for d in sorted(G) if d <= out.get('capeD', D[-1])]
    if gd: out['spx'] = G[gd[-1]][0]; out['spxD'] = gd[-1]
    # --- 기분 온도 (최근 80거래일, 오늘 눈금 기준) ---
    fgd = {}
    if fgj and fgj.get('d'):
        fgd = {d: s for d, s in zip(fgj['d'], fgj['s']) if s is not None}
    TX = []
    r5 = lambda x: None if x is None else round(x, 5)
    for d in D[-80:]:
        TX.append([d, r5(dist.get(d)), r5(ret.get(d)), V.get(d, (None,))[0], r5(cr.get(d)), fgd.get(d)])
    out['TX'] = TX
    if fgd: out['fg'] = fgd[max(fgd)]
    return out

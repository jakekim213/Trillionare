# 나스닥100 공포·탐욕 지수 (라오어판) — 표준 라이브러리만 사용 (GitHub Actions용)
# 재료 6가지를 각각 '최근 2년(504거래일) 안에서 지금이 몇 등인가'(0~100)로 바꿔 평균
#  추세: 나스닥100 ÷ 125일 평균 − 1   (높을수록 탐욕)
#  고점: 나스닥100 ÷ 52주 최고 − 1     (고점에 가까울수록 탐욕)
#  공포: −(VXN ÷ VXN 50일 평균)        (VXN이 평소보다 높을수록 공포)
#  기술주공포: −(VXN − VIX)            (기술주만 더 겁먹을수록 공포)
#  안전자산: QQQ 20일 수익 − TLT 20일 수익 (주식이 채권보다 셀수록 탐욕)
#  과열: 나스닥100 RSI(14)
NAMES = ['추세', '고점', '공포', '기술주공포', '안전자산', '과열']

def _ma(a, n, i):
    if i + 1 < n: return None
    w = a[i + 1 - n:i + 1]
    return None if any(x is None for x in w) else sum(w) / n

def calc(dates, N, VN, VX, Q, TL, L=504):
    """dates와 같은 길이의 리스트들(None 허용) → (점수 리스트, 재료별 등수 리스트들)"""
    n = len(dates); raw = {k: [None] * n for k in NAMES}
    # RSI (와일더식 지수평균, pandas ewm(alpha=1/14, adjust=False)와 같음)
    up = dn = None; rsi = [None] * n
    for i in range(1, n):
        dlt = N[i] - N[i - 1]; u, d = max(dlt, 0), max(-dlt, 0)
        if up is None: up, dn = u, d
        else: up += (u - up) / 14; dn += (d - dn) / 14
        rsi[i] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    for i in range(n):
        m125 = _ma(N, 125, i)
        if m125: raw['추세'][i] = N[i] / m125 - 1
        if i + 1 >= 200:
            hi = max(N[max(0, i - 251):i + 1]); raw['고점'][i] = N[i] / hi - 1
        if VN[i] is not None:
            m50 = _ma(VN, 50, i)
            if m50: raw['공포'][i] = -(VN[i] / m50)
            if VX[i] is not None: raw['기술주공포'][i] = -(VN[i] - VX[i])
        if i >= 20 and None not in (Q[i], Q[i - 20], TL[i], TL[i - 20]):
            raw['안전자산'][i] = (Q[i] / Q[i - 20] - 1) - (TL[i] / TL[i - 20] - 1)
        raw['과열'][i] = rsi[i]
    pct = {k: [None] * n for k in NAMES}
    for k in NAMES:
        a = raw[k]
        for i in range(n):
            if a[i] is None: continue
            w = [x for x in a[max(0, i - L + 1):i + 1] if x is not None]
            if len(w) < 250: continue
            pct[k][i] = sum(1 for x in w if x <= a[i]) / len(w) * 100
    score = []
    for i in range(n):
        v = [pct[k][i] for k in NAMES if pct[k][i] is not None]
        score.append(sum(v) / len(v) if v else None)
    return score, pct

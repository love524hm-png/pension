"""네이버 ETF 목록 API에서 전 종목 시세를 받아 prices.json으로 저장한다.

연금저축·IRP는 ETF·펀드만 매수할 수 있으므로 ETF 전체를 담으면 사실상
모든 보유 종목을 덮는다. 앱은 이 파일을 같은 출처에서 읽으므로 CORS도
외부 프록시도 필요 없다.
"""
import json
import pathlib
import urllib.request
from datetime import datetime, timezone, timedelta

SRC = "https://finance.naver.com/api/sise/etfItemList.nhn"
OUT = pathlib.Path(__file__).resolve().parent.parent / "prices.json"
KST = timezone(timedelta(hours=9))
MIN_ITEMS = 100


def fetch():
    req = urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    for enc in ("cp949", "euc-kr", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise SystemExit("응답을 어떤 인코딩으로도 읽지 못했다")


def build(doc):
    items = doc.get("result", {}).get("etfItemList", [])
    if not items:
        raise SystemExit("ETF 목록이 비어 있다 — 응답 형식이 바뀌었을 수 있다")
    prices = {}
    for it in items:
        code, now = it.get("itemcode"), it.get("nowVal")
        if not code or not now:
            continue
        try:
            prices[str(code)] = [int(now), round(float(it.get("changeRate") or 0), 2)]
        except (TypeError, ValueError):
            continue
    # 응답이 망가졌을 때 멀쩡한 파일을 덮어쓰지 않도록 막는다
    if len(prices) < MIN_ITEMS:
        raise SystemExit(f"수집된 종목이 {len(prices)}개뿐이다 — 저장하지 않는다")
    return prices


def main():
    prices = build(fetch())
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("prices", {})
        except (json.JSONDecodeError, OSError):
            pass
    if prev == prices:
        print(f"변동 없음 ({len(prices)}종목)")
        return
    payload = {
        "updatedAt": datetime.now(KST).isoformat(timespec="seconds"),
        "count": len(prices),
        "prices": prices,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{len(prices)}종목 저장")


if __name__ == "__main__":
    main()

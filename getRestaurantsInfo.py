"""
fetch_restaurants.py
- Google Places API를 사용해 식당 정보를 가져옵니다.
- 반환 필드: name, formatted_address, place_id, rating, user_ratings_total, formatted_phone_number
- 사용법 예: python test.py --query "restaurants in Seoul" --max_results 10
"""

import time
import argparse
import requests
import config  # 사용자가 올려둔 config.py에서 API_KEY를 읽습니다. :contentReference[oaicite:1]{index=1}
from typing import List, Dict, Optional

API_KEY = config.API_KEY
if not API_KEY:
    raise RuntimeError("API_KEY가 설정되어 있지 않습니다. 환경변수 GOOGLE_MAPS_API_KEY를 확인하세요.")

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# Place Details에서 우리가 받을 필드
DETAILS_FIELDS = ",".join([
    "name",
    "formatted_address",
    "place_id",
    "rating",
    "user_ratings_total",
    "formatted_phone_number"
])


def text_search(query: str, page_token: Optional[str] = None) -> dict:
    """
    Text Search 호출 (query: "restaurants in Seoul" 등)
    page_token: 다음 페이지 토큰 (pagination)
    """
    params = {
        "key": API_KEY,
        "query": query,
    }
    if page_token:
        params["pagetoken"] = page_token

    resp = requests.get(TEXT_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_place_details(place_id: str) -> dict:
    """
    Place Details 호출하여 상세 정보(전화번호 포함) 반환
    """
    params = {
        "key": API_KEY,
        "place_id": place_id,
        "fields": DETAILS_FIELDS
    }
    resp = requests.get(DETAILS_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("OK",):
        # 비정상 상태는 빈 dict 반환
        return {}
    return data.get("result", {})


def fetch_restaurants_by_text(query: str, max_results: int = 30) -> List[Dict]:
    """
    Text Search로 장소들을 검색하고 각 place_id로 상세정보를 요청하여 리스트로 반환
    - max_results: 최대 가져올 장소 개수 (API 할당량 주의)
    """
    results = []
    page_token = None
    while len(results) < max_results:
        # Text Search 호출
        j = text_search(query, page_token=page_token)
        status = j.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            # 경우에 따라 OVER_QUERY_LIMIT, REQUEST_DENIED 등을 리턴할 수 있음
            raise RuntimeError(f"Text Search API error: {status} - {j.get('error_message')}")
        places = j.get("results", [])
        for p in places:
            if len(results) >= max_results:
                break
            pid = p.get("place_id")
            if not pid:
                continue
            # 상세정보 가져오기
            details = get_place_details(pid)
            # 필요한 필드만 정리
            entry = {
                "name": details.get("name") or p.get("name"),
                "address": details.get("formatted_address") or p.get("formatted_address") or p.get("vicinity"),
                "place_id": details.get("place_id") or pid,
                "rating": details.get("rating") or p.get("rating"),
                "user_ratings_total": details.get("user_ratings_total") or p.get("user_ratings_total"),
                "phone_number": details.get("formatted_phone_number")  # 상세에서만 나옴
            }
            results.append(entry)

        # pagination: next_page_token이 있으면 해당 토큰으로 다음 페이지 요청 가능
        page_token = j.get("next_page_token")
        if not page_token:
            break
        # next_page_token은 바로 활성화되지 않음 -> 약간의 대기 필요
        time.sleep(2)  # 보수적으로 2초 대기 (권장: 2~3초)
    return results[:max_results]


import json

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help='예: "restaurants in Seoul" 또는 "sushi restaurants near Gangnam"')
    ap.add_argument("--max_results", type=int, default=30, help="최대 결과 수 (기본 30)")
    ap.add_argument("--output", type=str, default="restaurants.json", help="결과를 저장할 JSON 파일 이름 (기본 restaurants.json)")
    args = ap.parse_args()

    print(f"Query: {args.query}  |  Max: {args.max_results}")
    try:
        places = fetch_restaurants_by_text(args.query, max_results=args.max_results)
    except Exception as e:
        print("오류 발생:", e)
        return

    # 가져온 식당 정보를 JSON 파일로 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(places, f, ensure_ascii=False, indent=4)

    print(f"\n총 {len(places)}개 장소를 가져와 '{args.output}' 파일에 저장했습니다.")


if __name__ == "__main__":
    main()

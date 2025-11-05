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
import csv
import os

def load_tier_info(csv_path: str = "grid_tier.csv") -> Dict[str, str]:
    """
    grid_tier.csv 파일을 읽어서 {code: tier} 딕셔너리 반환
    예: {"MN1": "HOT", "MN2": "HOT", ...}
    """
    tier_dict = {}
    if not os.path.exists(csv_path):
        print(f"경고: {csv_path} 파일이 없습니다. 기본값(MID)을 사용합니다.")
        return tier_dict

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('code', '').strip()
            tier = row.get('tier', '').strip()
            if code and tier:
                tier_dict[code] = tier
    return tier_dict

def get_max_results_by_tier(tier: str) -> int:
    """
    tier에 따라 가져올 식당 개수 반환
    config.py의 TIER_RESTAURANT_COUNT 사용
    """
    return config.TIER_RESTAURANT_COUNT.get(tier.upper(), 50)  # 기본값 50

def parse_grid_info(txt_path: str = "gridInfo.txt") -> List[Dict[str, str]]:
    """
    gridInfo.txt 파일을 읽어서 grid 정보를 파싱
    반환: [{"code": "MN1", "name": "트라이베카, 금융 지구"}, ...]
    """
    grids = []
    if not os.path.exists(txt_path):
        print(f"경고: {txt_path} 파일이 없습니다.")
        return grids

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('🗽') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or line.startswith('5.'):
                continue

            # 형식: MN 1,"지역명"
            if ',' in line:
                parts = line.split(',', 1)
                code_part = parts[0].strip()
                name_part = parts[1].strip().strip('"')

                # 공백 제거 (MN 1 -> MN1)
                code = code_part.replace(' ', '')

                if code:
                    grids.append({"code": code, "name": name_part})

    return grids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=False, help='예: "restaurants in Seoul" 또는 "sushi restaurants near Gangnam"')
    ap.add_argument("--max_results", type=int, required=False, help="최대 결과 수")
    ap.add_argument("--output", type=str, default="restaurants.json", help="결과를 저장할 JSON 파일 이름 (기본 restaurants.json)")
    ap.add_argument("--grid_mode", action="store_true", help="gridInfo.txt와 grid_tier.csv를 사용하여 자동으로 모든 그리드 처리")
    args = ap.parse_args()

    if args.grid_mode:
        # Grid 모드: gridInfo.txt와 grid_tier.csv를 읽어서 처리
        print("Grid 모드로 실행합니다...")
        tier_dict = load_tier_info()
        grids = parse_grid_info()

        if not grids:
            print("Grid 정보를 찾을 수 없습니다.")
            return

        print(f"총 {len(grids)}개의 그리드를 처리합니다.")

        for grid in grids:
            code = grid["code"]
            name = grid["name"]
            tier = tier_dict.get(code, "MID")
            max_results = get_max_results_by_tier(tier)

            query = f"restaurants in {name}, New York"
            output_file = f"restaurants/restaurants_{code}.json"

            # restaurants 폴더 생성
            os.makedirs("restaurants", exist_ok=True)

            print(f"\n{'='*60}")
            print(f"처리 중: {code} - {name}")
            print(f"Tier: {tier} | 목표 개수: {max_results}")
            print(f"Query: {query}")

            try:
                places = fetch_restaurants_by_text(query, max_results=max_results)

                # 파일 저장
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(places, f, ensure_ascii=False, indent=4)

                print(f"✓ 완료: {len(places)}개 장소를 '{output_file}'에 저장했습니다.")
            except Exception as e:
                print(f"✗ 오류 발생 ({code}): {e}")
                continue

        print(f"\n{'='*60}")
        print("모든 그리드 처리 완료!")
    else:
        # 기존 단일 쿼리 모드
        if not args.query:
            print("--query 또는 --grid_mode를 지정해야 합니다.")
            return

        max_results = args.max_results if args.max_results else 30
        print(f"Query: {args.query}  |  Max: {max_results}")

        try:
            places = fetch_restaurants_by_text(args.query, max_results=max_results)
        except Exception as e:
            print("오류 발생:", e)
            return

        # 가져온 식당 정보를 JSON 파일로 저장
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(places, f, ensure_ascii=False, indent=4)

        print(f"\n총 {len(places)}개 장소를 가져와 '{args.output}' 파일에 저장했습니다.")


if __name__ == "__main__":
    main()

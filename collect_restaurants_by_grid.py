"""
collect_restaurants_by_grid.py
- gridInfo 파일을 읽어서 각 지구별로 자동으로 식당 정보를 수집합니다.
- 각 지구별로 restaurants_{지구코드}.json 파일로 저장합니다.
- 사용법: python collect_restaurants_by_grid.py --grid_file girdInfo.txt --max_results 30
"""

import re
import argparse
import subprocess
import sys
import os
from typing import List, Dict, Tuple
import time
import json


def parse_grid_info(file_path: str) -> List[Dict[str, str]]:
    """
    gridInfo 파일을 파싱하여 지구 정보 리스트를 반환합니다.

    반환 형식:
    [
        {
            'code': 'MN1',           # 공백 제거된 지구 코드
            'area_en': 'Tribeca, Financial District',  # 영문 지역명
            'area_kr': '트라이베카, 금융 지구',  # 한국어 지역명
            'original_line': 'MN 1,"트라이베카, 금융 지구 (Tribeca, Financial District)"'
        },
        ...
    ]
    """
    districts = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 빈 줄이나 헤더/구분자 줄 건너뛰기
            if not line or line.startswith('🗽') or line.startswith('1.') or \
               line.startswith('2.') or line.startswith('3.') or \
               line.startswith('4.') or line.startswith('5.'):
                continue

            # 지구 정보 파싱
            # 형식: 지구코드,"한국어명 (영문명)"
            # 예: MN 1,"트라이베카, 금융 지구 (Tribeca, Financial District)"
            match = re.match(r'^([A-Z]{2}\s+\d+),\"(.+)\s+\((.+)\)\"$', line)
            if match:
                code_with_space = match.group(1)  # 예: "MN 1"
                area_kr = match.group(2)          # 예: "트라이베카, 금융 지구"
                area_en = match.group(3)          # 예: "Tribeca, Financial District"

                # 지구 코드에서 공백 제거
                code = code_with_space.replace(' ', '')  # 예: "MN1"

                districts.append({
                    'code': code,
                    'area_en': area_en,
                    'area_kr': area_kr,
                    'original_line': line
                })

    return districts


def collect_restaurants_for_district(
    district: Dict[str, str],
    max_results: int,
    output_dir: str = 'restaurants'
) -> Tuple[bool, str]:
    """
    특정 지구의 식당 정보를 수집합니다.

    Args:
        district: 지구 정보 딕셔너리
        max_results: 최대 수집할 식당 수
        output_dir: 출력 디렉토리

    Returns:
        (성공 여부, 메시지)
    """
    code = district['code']
    area_en = district['area_en']

    # 검색 쿼리 생성
    query = f"restaurants in {area_en} New York"

    # 출력 파일명
    output_file = os.path.join(output_dir, f"restaurants_{code}.json")

    # getRestaurantsInfo.py 실행
    cmd = [
        sys.executable,  # 현재 Python 인터프리터
        'getRestaurantsInfo.py',
        '--query', query,
        '--max_results', str(max_results),
        '--output', output_file
    ]

    try:
        print(f"\n{'='*80}")
        print(f"[{code}] {area_en}")
        print(f"Query: {query}")
        print(f"Output: {output_file}")
        print(f"{'='*80}")

        # subprocess로 실행
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        # 표준 출력 표시
        if result.stdout:
            print(result.stdout)

        # 에러가 있으면 표시
        if result.returncode != 0:
            error_msg = f"Failed with return code {result.returncode}"
            if result.stderr:
                error_msg += f"\nError: {result.stderr}"
            return False, error_msg

        # 생성된 파일 확인
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data)
            return True, f"Successfully collected {count} restaurants"
        else:
            return False, "Output file not created"

    except subprocess.TimeoutExpired:
        return False, "Timeout (exceeded 5 minutes)"
    except Exception as e:
        return False, f"Exception: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description='뉴욕시 지구별 식당 정보를 자동으로 수집합니다.'
    )
    parser.add_argument(
        '--grid_file',
        type=str,
        default='girdInfo.txt',
        help='gridInfo 파일 경로 (기본값: girdInfo.txt)'
    )
    parser.add_argument(
        '--max_results',
        type=int,
        default=30,
        help='지구당 최대 수집할 식당 수 (기본값: 30)'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='restaurants',
        help='출력 디렉토리 (기본값: restaurants 폴더)'
    )
    parser.add_argument(
        '--start_from',
        type=int,
        default=0,
        help='시작할 지구 인덱스 (중단된 경우 재개용, 기본값: 0)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='처리할 지구 수 제한 (테스트용, 기본값: 전체)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='각 요청 사이의 대기 시간(초) (기본값: 1.0)'
    )

    args = parser.parse_args()

    # 출력 디렉토리 생성
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # gridInfo 파일 확인
    if not os.path.exists(args.grid_file):
        print(f"Error: gridInfo 파일을 찾을 수 없습니다: {args.grid_file}")
        sys.exit(1)

    # gridInfo 파싱
    print(f"\n📍 Parsing grid info from: {args.grid_file}")
    districts = parse_grid_info(args.grid_file)
    print(f"✓ Found {len(districts)} districts")

    # 처리할 지구 범위 결정
    start_idx = args.start_from
    end_idx = len(districts)
    if args.limit:
        end_idx = min(start_idx + args.limit, len(districts))

    districts_to_process = districts[start_idx:end_idx]

    print(f"\n🚀 Starting collection for {len(districts_to_process)} districts")
    print(f"   (from index {start_idx} to {end_idx-1})")
    print(f"   Max results per district: {args.max_results}")
    print(f"   Output directory: {args.output_dir}")

    # 통계
    success_count = 0
    fail_count = 0
    total_restaurants = 0
    failed_districts = []

    start_time = time.time()

    # 각 지구별로 수집
    for idx, district in enumerate(districts_to_process, start=start_idx):
        current = idx - start_idx + 1
        total = len(districts_to_process)

        print(f"\n\n{'#'*80}")
        print(f"Progress: {current}/{total} ({current*100//total}%)")
        print(f"District: [{district['code']}] {district['area_kr']} ({district['area_en']})")
        print(f"{'#'*80}")

        # 수집 실행
        success, message = collect_restaurants_for_district(
            district,
            args.max_results,
            args.output_dir
        )

        if success:
            success_count += 1
            # 메시지에서 식당 수 추출
            match = re.search(r'(\d+) restaurants', message)
            if match:
                count = int(match.group(1))
                total_restaurants += count
            print(f"✓ {message}")
        else:
            fail_count += 1
            failed_districts.append({
                'code': district['code'],
                'area': district['area_en'],
                'error': message
            })
            print(f"✗ {message}")

        # API 제한을 피하기 위한 대기
        if current < total:
            print(f"\nWaiting {args.delay} seconds before next request...")
            time.sleep(args.delay)

    # 최종 요약
    elapsed_time = time.time() - start_time

    print(f"\n\n{'='*80}")
    print("📊 COLLECTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total districts processed: {len(districts_to_process)}")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print(f"📍 Total restaurants collected: {total_restaurants}")
    print(f"⏱️  Elapsed time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")

    if failed_districts:
        print(f"\n❌ Failed districts:")
        for item in failed_districts:
            print(f"  - [{item['code']}] {item['area']}: {item['error']}")

    print(f"\n📁 Output files saved in: {args.output_dir}")
    print(f"   Pattern: restaurants_{{CODE}}.json")

    # 로그 파일 저장
    log_file = os.path.join(args.output_dir, 'collection_log.json')
    log_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_districts': len(districts_to_process),
        'success_count': success_count,
        'fail_count': fail_count,
        'total_restaurants': total_restaurants,
        'elapsed_seconds': elapsed_time,
        'failed_districts': failed_districts
    }
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)
    print(f"📝 Log saved to: {log_file}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()

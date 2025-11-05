"""
check_tier_mapping.py
grid_tier.csv와 gridInfo.txt의 매칭 상태를 확인하는 임시 스크립트

사용법:
    python check_tier_mapping.py
"""

import csv
import os

# config.py에서 가져온 tier 설정 (독립 실행을 위해 여기에 정의)
TIER_RESTAURANT_COUNT = {
    "HOT": 80,
    "MID": 50,
    "RES": 25
}


def load_tier_info(csv_path="grid_tier.csv"):
    """grid_tier.csv 파일을 읽어서 {code: tier} 딕셔너리 반환"""
    tier_dict = {}
    if not os.path.exists(csv_path):
        print(f"❌ 오류: {csv_path} 파일을 찾을 수 없습니다.")
        return tier_dict

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('code', '').strip()
            tier = row.get('tier', '').strip()
            if code and tier:
                tier_dict[code] = tier

    return tier_dict


def parse_grid_info(txt_path="gridInfo.txt"):
    """gridInfo.txt 파일을 읽어서 grid 정보를 파싱"""
    grids = []
    if not os.path.exists(txt_path):
        print(f"❌ 오류: {txt_path} 파일을 찾을 수 없습니다.")
        return grids

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('🗽') or line.startswith('1.') or \
               line.startswith('2.') or line.startswith('3.') or \
               line.startswith('4.') or line.startswith('5.'):
                continue

            # 형식: MN 1,"지역명 (영문명)"
            if ',' in line:
                parts = line.split(',', 1)
                code_part = parts[0].strip()
                name_part = parts[1].strip().strip('"')

                # 공백 제거 (MN 1 -> MN1)
                code = code_part.replace(' ', '')

                if code:
                    grids.append({"code": code, "name": name_part})

    return grids


def get_restaurant_count(tier):
    """tier에 따른 식당 수집 개수 반환"""
    return TIER_RESTAURANT_COUNT.get(tier.upper(), 0)


def main():
    print("="*80)
    print("Grid Tier 매칭 확인 스크립트")
    print("="*80)

    # 1. 데이터 로드
    print("\n[1단계] 데이터 로드 중...")
    tier_dict = load_tier_info()
    grids = parse_grid_info()

    print(f"✓ grid_tier.csv에서 {len(tier_dict)}개 tier 정보 로드")
    print(f"✓ gridInfo.txt에서 {len(grids)}개 그리드 정보 로드")

    # 2. 매칭 확인
    print("\n[2단계] 매칭 확인 중...")
    print("\n" + "="*80)
    print(f"{'코드':<8} {'Tier':<6} {'식당 개수':<10} {'지역명'}")
    print("="*80)

    tier_stats = {"HOT": 0, "MID": 0, "RES": 0, "MISSING": 0}
    missing_grids = []

    for grid in grids:
        code = grid['code']
        name = grid['name']
        tier = tier_dict.get(code, None)

        if tier:
            count = get_restaurant_count(tier)
            tier_stats[tier.upper()] += 1
            print(f"{code:<8} {tier:<6} {count:<10} {name}")
        else:
            tier_stats["MISSING"] += 1
            missing_grids.append(code)
            print(f"{code:<8} ⚠️ 없음  {'N/A':<10} {name}")

    # 3. 통계 출력
    print("\n" + "="*80)
    print("[3단계] 통계 요약")
    print("="*80)

    total_grids = len(grids)
    total_restaurants = 0

    print(f"\n전체 그리드 수: {total_grids}개\n")

    for tier, count in tier_stats.items():
        if tier == "MISSING":
            if count > 0:
                print(f"⚠️  Tier 없음: {count}개")
        else:
            restaurant_count = get_restaurant_count(tier)
            total_for_tier = count * restaurant_count
            total_restaurants += total_for_tier
            percentage = (count / total_grids * 100) if total_grids > 0 else 0
            print(f"✓  {tier}: {count}개 ({percentage:.1f}%) - 그리드당 {restaurant_count}개 식당 = 총 {total_for_tier}개")

    print(f"\n예상 총 식당 수집 개수: {total_restaurants}개")

    # 4. 누락된 그리드 확인
    if missing_grids:
        print("\n" + "="*80)
        print("[4단계] Tier 정보가 없는 그리드")
        print("="*80)
        print(f"\n⚠️  다음 그리드에 tier 정보가 없습니다: {', '.join(missing_grids)}")
        print(f"   grid_tier.csv에 해당 그리드를 추가하세요.")

    # 5. tier_dict에는 있지만 grids에는 없는 경우 확인
    grid_codes = {g['code'] for g in grids}
    extra_tiers = [code for code in tier_dict.keys() if code not in grid_codes]

    if extra_tiers:
        print("\n" + "="*80)
        print("[5단계] gridInfo.txt에 없지만 grid_tier.csv에 있는 코드")
        print("="*80)
        print(f"\n⚠️  다음 코드가 grid_tier.csv에는 있지만 gridInfo.txt에는 없습니다:")
        for code in sorted(extra_tiers):
            print(f"   - {code}: {tier_dict[code]}")

    # 6. 최종 결과
    print("\n" + "="*80)
    print("[최종 결과]")
    print("="*80)

    if not missing_grids and not extra_tiers:
        print("\n✅ 모든 그리드가 올바르게 매칭되었습니다!")
    else:
        print("\n⚠️  일부 그리드에 문제가 있습니다. 위의 세부 사항을 확인하세요.")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()

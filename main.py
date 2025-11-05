"""
main.py
Google Maps 식당 정보 및 리뷰 수집 전체 파이프라인 (Grid 기반)

사용법:
# Tier 기반 자동 조정 모드 + 최적화 크롤러 (권장)
python main.py --grid_file gridInfo.txt --use_tier_based_restaurants --max_reviews 50 --headless

# 최적화 + 병렬 처리 (가장 빠름!)
python main.py --grid_file gridInfo.txt --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews --review_workers 4

# 기존 방식: 모든 그리드에 동일한 식당 개수
python main.py --grid_file gridInfo.txt --max_restaurants 30 --max_reviews 50 --headless

    # Tier 기반 모드로 팀원별 작업 분할 (59개 그리드를 5명이 나눠서 작업)
# 팀원 1: 그리드 0~11 (12개)
python main.py --grid_file gridInfo.txt --start_from 0 --limit 12 --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews

# 팀원 2: 그리드 12~23 (12개)
python main.py --grid_file gridInfo.txt --start_from 12 --limit 12 --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews

# 팀원 3: 그리드 24~35 (12개)
python main.py --grid_file gridInfo.txt --start_from 24 --limit 12 --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews

# 팀원 4: 그리드 36~47 (12개)
python main.py --grid_file gridInfo.txt --start_from 36 --limit 12 --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews

# 팀원 5: 그리드 48~58 (11개)
python main.py --grid_file gridInfo.txt --start_from 48 --limit 11 --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews

    # 특정 그리드만 테스트
    python main.py --grid_file gridInfo.txt --limit 1 --max_restaurants 10 --max_reviews 20
    
주의:
    - 최적화된 크롤러(getReviews_optimized.py)를 사용하여 약 65-70% 빠른 속도
    - --parallel_reviews 옵션 사용 시 4배 빠른 리뷰 수집 가능
    - 권장 워커 수: 2-4개 (시스템 리소스에 따라 조정)
"""

import subprocess
import argparse
import sys
import os
import re
import time
import json
import csv
from datetime import datetime
import config  # tier 설정 가져오기


class GridBasedPipelineRunner:
    def __init__(self, args):
        self.args = args
        self.start_time = None
        self.restaurants_dir = args.restaurants_dir
        self.reviews_dir = args.reviews_dir
        self.tier_dict = {}  # tier 정보 저장

        # tier 기반 모드가 활성화된 경우 tier 정보 로드
        if args.use_tier_based_restaurants:
            self.tier_dict = self.load_tier_info(args.tier_file)

    def load_tier_info(self, csv_path):
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

        print(f"✓ Tier 정보 로드 완료: {len(tier_dict)}개 그리드")
        return tier_dict

    def get_max_restaurants_by_tier(self, grid_code):
        """
        tier에 따라 가져올 식당 개수 반환
        config.py의 TIER_RESTAURANT_COUNT 사용
        tier 정보가 없으면 args.max_restaurants 사용
        """
        if not self.args.use_tier_based_restaurants:
            return self.args.max_restaurants

        tier = self.tier_dict.get(grid_code, "MID")
        return config.TIER_RESTAURANT_COUNT.get(tier.upper(), self.args.max_restaurants)

    def print_header(self, title):
        """섹션 헤더 출력"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def parse_grid_info(self, file_path):
        """
        gridInfo 파일을 파싱하여 지구 정보 리스트를 반환

        Returns:
            List[Dict]: [{'code': 'MN1', 'area_en': 'Tribeca, Financial District', 'area_kr': '트라이베카, 금융 지구'}, ...]
        """
        districts = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 빈 줄이나 헤더 줄 건너뛰기
                if not line or line.startswith('🗽') or line.startswith('1.') or \
                   line.startswith('2.') or line.startswith('3.') or \
                   line.startswith('4.') or line.startswith('5.'):
                    continue

                # 지구 정보 파싱: MN 1,"트라이베카, 금융 지구 (Tribeca, Financial District)"
                match = re.match(r'^([A-Z]{2}\s+\d+),\"(.+)\s+\((.+)\)\"$', line)
                if match:
                    code_with_space = match.group(1)  # "MN 1"
                    area_kr = match.group(2)          # "트라이베카, 금융 지구"
                    area_en = match.group(3)          # "Tribeca, Financial District"
                    code = code_with_space.replace(' ', '')  # "MN1"

                    districts.append({
                        'code': code,
                        'area_en': area_en,
                        'area_kr': area_kr
                    })
        return districts

    def run_command(self, command, description):
        """
        subprocess로 명령 실행

        Args:
            command (list): 실행할 명령어 리스트
            description (str): 명령 설명

        Returns:
            bool: 성공 여부
        """
        print(f"\n실행 중: {' '.join(command)}\n")
        try:
            result = subprocess.run(
                command,
                check=True,
                text=True,
                capture_output=False
            )            
            print(f"\n✓ {description} 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n✗ {description} 실패")
            print(f"오류 코드: {e.returncode}")
            return False
        except subprocess.TimeoutExpired:
            print(f"\n✗ {description} 타임아웃 (10분 초과)")
            return False
        except FileNotFoundError:
            print(f"\n✗ Python 또는 스크립트 파일을 찾을 수 없습니다.")
            return False

    def collect_restaurants_for_grid(self, district):
        """특정 그리드의 레스토랑 정보 수집"""
        code = district['code']
        area_en = district['area_en']
        query = f"restaurants in {area_en} New York"
        output_file = os.path.join(self.restaurants_dir, f"restaurants_{code}.json")

        # tier 기반으로 max_restaurants 결정
        max_restaurants = self.get_max_restaurants_by_tier(code)
        tier = self.tier_dict.get(code, "DEFAULT") if self.args.use_tier_based_restaurants else "N/A"

        print(f"\n{'='*80}")
        print(f"[{code}] {district['area_kr']} ({area_en})")
        if self.args.use_tier_based_restaurants:
            print(f"Tier: {tier} | 목표 식당 개수: {max_restaurants}개")
        print(f"Query: {query}")
        print(f"Output: {output_file}")
        print(f"{'='*80}")

        command = [
            sys.executable,
            'getRestaurantsInfo.py',
            '--query', query,
            '--max_results', str(max_restaurants),
            '--output', output_file
        ]

        success = self.run_command(command, f"레스토랑 정보 수집 [{code}]")

        # 수집된 레스토랑 수 확인
        restaurant_count = 0
        if success and os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    restaurants = json.load(f)
                    restaurant_count = len(restaurants)
                    print(f"   수집된 레스토랑: {restaurant_count}개")
            except:
                pass

        return success, output_file, restaurant_count

    def collect_reviews_for_grid(self, restaurants_file, grid_code):
        """특정 그리드의 레스토랑에 대한 리뷰 수집 (최적화 버전 사용)"""
        if not os.path.exists(restaurants_file):
            print(f"\n✗ 오류: {restaurants_file} 파일을 찾을 수 없습니다.")
            return False, 0

        # 최적화된 크롤러 사용
        command = [
            sys.executable,
            'getReviews_optimized.py',  # 최적화된 버전 사용
            '--input', restaurants_file,
            '--output_dir', self.reviews_dir
        ]

        if self.args.max_reviews:
            command.extend(['--max_reviews', str(self.args.max_reviews)])

        if self.args.headless:
            command.append('--headless')
        
        # 병렬 처리 옵션 추가
        if self.args.parallel_reviews:
            command.append('--parallel')
            command.extend(['--workers', str(self.args.review_workers)])

        success = self.run_command(command, f"리뷰 수집 [{grid_code}]")

        # 수집된 리뷰 수 확인
        total_reviews = 0
        if success:
            # reviews 디렉토리에서 해당 그리드의 리뷰 파일 찾기
            review_files = [f for f in os.listdir(self.reviews_dir) if f.startswith(f"{grid_code}_") and f.endswith('_reviews.json')]
            for review_file in review_files:
                try:
                    with open(os.path.join(self.reviews_dir, review_file), 'r', encoding='utf-8') as f:
                        review_data = json.load(f)
                        total_reviews += review_data.get('reviews_count', 0)
                except:
                    pass
            print(f"   수집된 리뷰: {total_reviews}개")

        return success, total_reviews

    def process_grid(self, district, current_idx, total):
        """
        하나의 그리드에 대해 전체 파이프라인 실행
        1. 레스토랑 정보 수집
        2. 리뷰 수집
        """
        code = district['code']

        print(f"\n\n{'#'*80}")
        print(f"Progress: {current_idx}/{total} ({current_idx*100//total}%)")
        print(f"Grid: [{code}] {district['area_kr']} ({district['area_en']})")
        print(f"{'#'*80}")

        # Step 1: 레스토랑 정보 수집
        print(f"\n[Step 1/2] 레스토랑 정보 수집")
        restaurants_success, restaurants_file, restaurant_count = self.collect_restaurants_for_grid(district)

        if not restaurants_success:
            print(f"\n✗ [{code}] 레스토랑 정보 수집 실패 - 리뷰 수집 건너뜀")
            return {
                'code': code,
                'restaurants_success': False,
                'reviews_success': False,
                'restaurant_count': 0,
                'review_count': 0
            }

        # Step 2: 리뷰 수집
        print(f"\n[Step 2/2] 리뷰 수집")
        reviews_success, review_count = self.collect_reviews_for_grid(restaurants_file, code)

        return {
            'code': code,
            'restaurants_success': restaurants_success,
            'reviews_success': reviews_success,
            'restaurant_count': restaurant_count,
            'review_count': review_count
        }

    def print_summary(self, results_list, elapsed_time):
        """최종 결과 요약"""
        self.print_header("실행 결과 요약")

        total_grids = len(results_list)
        success_grids = sum(1 for r in results_list if r['restaurants_success'] and r['reviews_success'])
        failed_grids = total_grids - success_grids
        total_restaurants = sum(r['restaurant_count'] for r in results_list)
        total_reviews = sum(r['review_count'] for r in results_list)

        print(f"\n처리된 그리드: {total_grids}개")
        print(f"  ✓ 성공: {success_grids}개")
        print(f"  ✗ 실패: {failed_grids}개")
        print(f"\n수집 통계:")
        print(f"  레스토랑: {total_restaurants}개")
        print(f"  리뷰: {total_reviews}개")
        print(f"\n소요 시간: {elapsed_time:.1f}초 ({elapsed_time/60:.1f}분)")

        # 실패한 그리드 목록
        failed_list = [r for r in results_list if not (r['restaurants_success'] and r['reviews_success'])]
        if failed_list:
            print(f"\n실패한 그리드:")
            for r in failed_list:
                if not r['restaurants_success']:
                    print(f"  - [{r['code']}]: 레스토랑 정보 수집 실패")
                elif not r['reviews_success']:
                    print(f"  - [{r['code']}]: 리뷰 수집 실패")

        print(f"\n출력 디렉토리:")
        print(f"  레스토랑: {self.restaurants_dir}/")
        print(f"  리뷰: {self.reviews_dir}/")

        if success_grids == total_grids:
            print("\n" + "=" * 80)
            print("  모든 작업이 성공적으로 완료되었습니다!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("  일부 작업이 실패했습니다. 위의 오류 메시지를 확인하세요.")
            print("=" * 80)

    def run(self):
        """전체 파이프라인 실행"""
        self.start_time = datetime.now()

        self.print_header("Google Maps 그리드 기반 식당 정보 및 리뷰 수집 파이프라인")

        # 출력 디렉토리 생성
        if not os.path.exists(self.restaurants_dir):
            os.makedirs(self.restaurants_dir)
            print(f"디렉토리 생성: {self.restaurants_dir}")
        if not os.path.exists(self.reviews_dir):
            os.makedirs(self.reviews_dir)
            print(f"디렉토리 생성: {self.reviews_dir}")

        # gridInfo 파일 확인 및 파싱
        if not os.path.exists(self.args.grid_file):
            print(f"\n✗ 오류: gridInfo 파일을 찾을 수 없습니다: {self.args.grid_file}")
            return False

        print(f"\n그리드 정보 파싱 중: {self.args.grid_file}")
        districts = self.parse_grid_info(self.args.grid_file)
        print(f"✓ 총 {len(districts)}개 그리드 발견")

        # 처리할 그리드 범위 결정
        start_idx = self.args.start_from
        end_idx = len(districts)
        if self.args.limit:
            end_idx = min(start_idx + self.args.limit, len(districts))

        districts_to_process = districts[start_idx:end_idx]

        print(f"\n설정:")
        print(f"  그리드 파일: {self.args.grid_file}")
        print(f"  처리할 그리드: {len(districts_to_process)}개 (전체 {len(districts)}개 중 {start_idx}~{end_idx-1})")
        if self.args.use_tier_based_restaurants:
            # config에서 tier 설정을 동적으로 가져와서 표시
            tier_info = ", ".join([f"{tier}:{count}" for tier, count in config.TIER_RESTAURANT_COUNT.items()])
            print(f"  레스토랑 수집 모드: Tier 기반 자동 조정 ({tier_info})")
            print(f"  Tier 파일: {self.args.tier_file}")
        else:
            print(f"  그리드당 최대 레스토랑: {self.args.max_restaurants}개")
        print(f"  레스토랑당 최대 리뷰: {self.args.max_reviews if self.args.max_reviews else '제한 없음'}")
        print(f"  헤드리스 모드: {'예' if self.args.headless else '아니오'}")
        print(f"  리뷰 병렬 처리: {'예 (워커 ' + str(self.args.review_workers) + '개)' if self.args.parallel_reviews else '아니오'}")
        print(f"  API 요청 간 대기 시간: {self.args.delay}초")

        # 각 그리드별로 처리
        results = []
        for idx, district in enumerate(districts_to_process, start=1):
            result = self.process_grid(district, idx, len(districts_to_process))
            results.append(result)

            # API 제한 방지를 위한 대기 (마지막 그리드가 아닌 경우)
            if idx < len(districts_to_process):
                print(f"\n대기 중... ({self.args.delay}초)")
                time.sleep(self.args.delay)

        # 최종 요약
        elapsed_time = time.time() - self.start_time.timestamp()
        self.print_summary(results, elapsed_time)

        # 로그 파일 저장
        log_dir = 'log'
        os.makedirs(log_dir, exist_ok=True)
        now_time_str = self.start_time.strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'pipeline_log_{now_time_str}.json')

        log_data = {
            'timestamp': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_grids': len(districts_to_process),
            'success_count': sum(1 for r in results if r['restaurants_success'] and r['reviews_success']),
            'total_restaurants': sum(r['restaurant_count'] for r in results),
            'total_reviews': sum(r['review_count'] for r in results),
            'elapsed_seconds': elapsed_time,
            'results': results
        }
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=4)
        print(f"\n로그 저장: {log_file}")

        return all(r['restaurants_success'] and r['reviews_success'] for r in results)


def main():
    # config에서 tier 정보 가져오기
    tier_info_text = ", ".join([f"{tier}:{count}개" for tier, count in config.TIER_RESTAURANT_COUNT.items()])

    parser = argparse.ArgumentParser(
        description='Google Maps 그리드 기반 식당 정보 및 리뷰 수집 파이프라인',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
사용 예시:
  # Tier 기반 자동 조정 모드로 전체 그리드 실행 ({tier_info_text})
  python main.py --grid_file gridInfo.txt --use_tier_based_restaurants --max_reviews 50 --headless

  # 최적화 + 병렬 처리 (가장 빠름!)
  python main.py --grid_file gridInfo.txt --use_tier_based_restaurants --max_reviews 50 --headless --parallel_reviews --review_workers 4

  # Tier 기반 모드로 팀원별 작업 분할 (59개 그리드를 5명이 나눠서 작업)
  # 팀원 1: 그리드 0~11 (12개)
  python main.py --grid_file gridInfo.txt --start_from 0 --limit 12 --use_tier_based_restaurants --max_reviews 40 --headless --parallel_reviews

  # 팀원 2: 그리드 12~23 (12개)
  python main.py --grid_file gridInfo.txt --start_from 12 --limit 12 --use_tier_based_restaurants --max_reviews 40 --headless --parallel_reviews

  # 팀원 3: 그리드 24~35 (12개)
  python main.py --grid_file gridInfo.txt --start_from 24 --limit 12 --use_tier_based_restaurants --max_reviews 40 --headless --parallel_reviews

  # 팀원 4: 그리드 36~47 (12개)
  python main.py --grid_file gridInfo.txt --start_from 36 --limit 12 --use_tier_based_restaurants --max_reviews 40 --headless --parallel_reviews

  # 팀원 5: 그리드 48~58 (11개)
  python main.py --grid_file gridInfo.txt --start_from 48 --limit 11 --use_tier_based_restaurants --max_reviews 40 --headless --parallel_reviews

  # 특정 그리드만 테스트
  python main.py --grid_file gridInfo.txt --limit 1 --max_restaurants 10 --max_reviews 20
        """
    )

    # Grid 파일 관련
    parser.add_argument('--grid_file', type=str, default='gridInfo.txt',
                        help='Grid 정보 파일 경로 (기본값: gridInfo.txt)')
    parser.add_argument('--start_from', type=int, default=0,
                        help='시작할 그리드 인덱스 (팀원별 작업 분할용, 기본값: 0)')
    parser.add_argument('--limit', type=int, default=None,
                        help='처리할 그리드 수 제한 (팀원별 작업 분할용, 기본값: 전체)')

    # 식당 정보 수집 관련
    parser.add_argument('--max_restaurants', type=int, default=30,
                        help='그리드당 최대 레스토랑 수 (기본값: 30, tier 모드가 아닐 때 사용)')

    # config에서 tier 설정 가져오기
    tier_info_str = ", ".join([f"{tier}:{count}" for tier, count in config.TIER_RESTAURANT_COUNT.items()])
    parser.add_argument('--use_tier_based_restaurants', action='store_true',
                        help=f'grid_tier.csv 기반으로 tier에 따라 식당 개수 자동 조정 ({tier_info_str})')
    parser.add_argument('--tier_file', type=str, default='grid_tier.csv',
                        help='Tier 정보 CSV 파일 경로 (기본값: grid_tier.csv)')
    parser.add_argument('--restaurants_dir', type=str, default='restaurants',
                        help='레스토랑 정보 출력 디렉토리 (기본값: restaurants)')

    # 리뷰 수집 관련
    parser.add_argument('--max_reviews', type=int, default=None,
                        help='레스토랑당 최대 리뷰 수 (기본값: 제한 없음)')
    parser.add_argument('--headless', action='store_true',
                        help='백그라운드에서 크롤링 (브라우저 창 숨김)')
    parser.add_argument('--reviews_dir', type=str, default='reviews',
                        help='리뷰 출력 디렉토리 (기본값: reviews)')
    parser.add_argument('--parallel_reviews', action='store_true',
                        help='리뷰 수집 시 병렬 처리 활성화 (더 빠르지만 리소스 사용 많음)')
    parser.add_argument('--review_workers', type=int, default=2,
                        help='병렬 리뷰 수집 시 워커 수 (기본값: 2, 권장: 2-4)')

    # API 제한 관련
    parser.add_argument('--delay', type=float, default=2.0,
                        help='각 그리드 처리 사이의 대기 시간(초) (기본값: 2.0)')

    args = parser.parse_args()

    # 검증
    if not os.path.exists(args.grid_file):
        parser.error(f"Grid 파일을 찾을 수 없습니다: {args.grid_file}")

    # 파이프라인 실행
    runner = GridBasedPipelineRunner(args)
    success = runner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

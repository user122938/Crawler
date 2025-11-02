"""
main.py
Google Maps 식당 정보 및 리뷰 수집 전체 파이프라인

사용법:
    # 기본 실행 (전체 파이프라인)
    python main.py --query "restaurants in Seoul"

    # 상세 옵션
    python main.py --query "restaurants in Myeongdong" --max_restaurants 20 --max_reviews 50 --headless

    # 특정 단계만 실행
    python main.py --skip-restaurants  # 리뷰 수집만 실행
    python main.py --skip-reviews      # 식당 정보 수집만 실행
"""

import subprocess
import argparse
import sys
import os
from datetime import datetime


class PipelineRunner:
    def __init__(self, args):
        self.args = args
        self.start_time = None
        self.restaurants_file = args.restaurants_output
        self.reviews_file = args.reviews_output

    def print_header(self, title):
        """섹션 헤더 출력"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_step(self, step_num, total_steps, description):
        """단계 표시"""
        print(f"\n[Step {step_num}/{total_steps}] {description}")
        print("-" * 70)

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
                capture_output=False  # 실시간 출력을 위해 False
            )
            print(f"\n✓ {description} 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n✗ {description} 실패")
            print(f"오류 코드: {e.returncode}")
            return False
        except FileNotFoundError:
            print(f"\n✗ Python 또는 스크립트 파일을 찾을 수 없습니다.")
            return False

    def run_step_restaurants(self):
        """Step 1: 식당 정보 수집"""
        if self.args.skip_restaurants:
            print("\n[SKIP] 식당 정보 수집 단계를 건너뜁니다.")
            return True

        self.print_step(1, 2, "식당 정보 수집 (Google Places API)")

        command = [
            sys.executable,  # 현재 Python 인터프리터
            "getRestaurantsInfo.py",
            "--query", self.args.query,
            "--max_results", str(self.args.max_restaurants),
            "--output", self.restaurants_file
        ]

        success = self.run_command(command, "식당 정보 수집")

        if success and os.path.exists(self.restaurants_file):
            # 수집된 식당 수 확인
            import json
            try:
                with open(self.restaurants_file, 'r', encoding='utf-8') as f:
                    restaurants = json.load(f)
                    print(f"   수집된 식당 수: {len(restaurants)}개")
                    print(f"   저장 위치: {self.restaurants_file}")
            except:
                pass

        return success

    def run_step_reviews(self):
        """Step 2: 리뷰 수집"""
        if self.args.skip_reviews:
            print("\n[SKIP] 리뷰 수집 단계를 건너뜁니다.")
            return True

        # restaurants.json 파일 확인
        if not os.path.exists(self.restaurants_file):
            print(f"\n✗ 오류: {self.restaurants_file} 파일을 찾을 수 없습니다.")
            print(f"   먼저 식당 정보를 수집하거나 restaurants.json 파일을 준비해주세요.")
            return False

        self.print_step(2, 2, "리뷰 수집 (Selenium 크롤링)")

        command = [
            sys.executable,
            "getReviews.py",
            "--input", self.restaurants_file,
            "--output", self.reviews_file
        ]

        if self.args.max_reviews:
            command.extend(["--max_reviews", str(self.args.max_reviews)])

        if self.args.headless:
            command.append("--headless")

        success = self.run_command(command, "리뷰 수집")

        if success and os.path.exists(self.reviews_file):
            # 수집된 리뷰 통계
            import json
            try:
                with open(self.reviews_file, 'r', encoding='utf-8') as f:
                    reviews_data = json.load(f)
                    total_reviews = sum(data.get('reviews_count', 0) for data in reviews_data.values())
                    print(f"   총 식당 수: {len(reviews_data)}개")
                    print(f"   총 리뷰 수: {total_reviews}개")
                    print(f"   저장 위치: {self.reviews_file}")
            except:
                pass

        return success

    def print_summary(self, results):
        """최종 결과 요약"""
        self.print_header("실행 결과 요약")

        end_time = datetime.now()
        elapsed = end_time - self.start_time

        print(f"\n시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"소요 시간: {elapsed}")

        print("\n실행 결과:")
        if not self.args.skip_restaurants:
            status = "✓ 성공" if results['restaurants'] else "✗ 실패"
            print(f"  1. 식당 정보 수집: {status}")
        if not self.args.skip_reviews:
            status = "✓ 성공" if results['reviews'] else "✗ 실패"
            print(f"  2. 리뷰 수집: {status}")

        print("\n생성된 파일:")
        if os.path.exists(self.restaurants_file):
            size = os.path.getsize(self.restaurants_file)
            print(f"  - {self.restaurants_file} ({size:,} bytes)")
        if os.path.exists(self.reviews_file):
            size = os.path.getsize(self.reviews_file)
            print(f"  - {self.reviews_file} ({size:,} bytes)")

        all_success = all(results.values())
        if all_success:
            print("\n" + "=" * 70)
            print("  🎉 모든 작업이 성공적으로 완료되었습니다!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("  ⚠️  일부 작업이 실패했습니다. 위의 오류 메시지를 확인하세요.")
            print("=" * 70)

    def run(self):
        """전체 파이프라인 실행"""
        self.start_time = datetime.now()

        self.print_header("Google Maps 식당 정보 및 리뷰 수집 파이프라인")

        print("\n설정:")
        if not self.args.skip_restaurants:
            print(f"  검색 쿼리: {self.args.query}")
            print(f"  최대 식당 수: {self.args.max_restaurants}")
        if not self.args.skip_reviews:
            print(f"  최대 리뷰 수 (식당당): {self.args.max_reviews if self.args.max_reviews else '제한 없음'}")
            print(f"  헤드리스 모드: {'예' if self.args.headless else '아니오'}")
        print(f"  식당 정보 파일: {self.restaurants_file}")
        print(f"  리뷰 파일: {self.reviews_file}")

        results = {
            'restaurants': True,
            'reviews': True
        }

        # Step 1: 식당 정보 수집
        if not self.args.skip_restaurants:
            results['restaurants'] = self.run_step_restaurants()
            if not results['restaurants']:
                print("\n식당 정보 수집에 실패하여 파이프라인을 중단합니다.")
                self.print_summary(results)
                return False

        # Step 2: 리뷰 수집
        if not self.args.skip_reviews:
            results['reviews'] = self.run_step_reviews()

        # 요약 출력
        self.print_summary(results)

        return all(results.values())


def main():
    parser = argparse.ArgumentParser(
        description='Google Maps 식당 정보 및 리뷰 수집 전체 파이프라인',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 실행
  python main.py --query "restaurants in Seoul"

  # 상세 옵션
  python main.py --query "restaurants in Myeongdong" --max_restaurants 20 --max_reviews 50 --headless

  # 리뷰만 수집 (restaurants.json이 이미 있는 경우)
  python main.py --skip-restaurants --max_reviews 100 --headless

  # 식당 정보만 수집
  python main.py --query "sushi in Gangnam" --skip-reviews
        """
    )

    # 식당 정보 수집 관련
    parser.add_argument('--query', type=str,
                        help='검색 쿼리 (예: "restaurants in Seoul", "sushi in Gangnam")')
    parser.add_argument('--max_restaurants', type=int, default=30,
                        help='최대 식당 수 (기본값: 30)')
    parser.add_argument('--restaurants_output', type=str, default='restaurants.json',
                        help='식당 정보 출력 파일 (기본값: restaurants.json)')

    # 리뷰 수집 관련
    parser.add_argument('--max_reviews', type=int, default=None,
                        help='식당당 최대 리뷰 수 (기본값: 제한 없음)')
    parser.add_argument('--headless', action='store_true',
                        help='백그라운드에서 크롤링 (브라우저 창 숨김)')
    parser.add_argument('--reviews_output', type=str, default='reviews.json',
                        help='리뷰 출력 파일 (기본값: reviews.json)')

    # 실행 제어
    parser.add_argument('--skip-restaurants', action='store_true',
                        help='식당 정보 수집 단계 건너뛰기')
    parser.add_argument('--skip-reviews', action='store_true',
                        help='리뷰 수집 단계 건너뛰기')

    args = parser.parse_args()

    # 검증
    if not args.skip_restaurants and not args.query:
        parser.error("--query 인자가 필요합니다. (또는 --skip-restaurants 사용)")

    if args.skip_restaurants and args.skip_reviews:
        parser.error("두 단계를 모두 건너뛸 수 없습니다.")

    # 파이프라인 실행
    runner = PipelineRunner(args)
    success = runner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

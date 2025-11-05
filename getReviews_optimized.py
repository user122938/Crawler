import json
import time
import argparse
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import re
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing


class OptimizedGoogleMapsReviewCrawler:
    def __init__(self, headless=False, max_reviews=None):
        """
        최적화된 구글 맵 리뷰 크롤러 초기화 (안정성 개선)
        
        Args:
            headless (bool): 브라우저를 백그라운드에서 실행할지 여부
            max_reviews (int): 수집할 최대 리뷰 개수
        """
        self.max_reviews = max_reviews
        self.driver = self._setup_driver(headless)

    def _setup_driver(self, headless):
        """크롬 드라이버 설정 - 성능 최적화 (안정성 균형)"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        
        # 성능 최적화 옵션들
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--lang=ko-KR')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')  # 이미지 로딩 비활성화
        chrome_options.add_argument('--disable-javascript-harmony')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.page_load_strategy = 'eager'  # DOM이 로드되면 바로 진행
        
        # 이미지, CSS, 폰트 등 불필요한 리소스 차단
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)  # 3초 → 5초로 증가 (안정성)
        return driver

    def get_reviews_url(self, place_id):
        """place_id를 사용하여 구글 맵 URL 생성"""
        return f"https://www.google.com/maps/place/?q=place_id:{place_id}"

    def click_reviews_tab(self, restaurant_name):
        """리뷰 탭 클릭 - JavaScript로 직접 클릭"""
        log_prefix = f"[{restaurant_name}] "
        try:
            wait = WebDriverWait(self.driver, 7)
            reviews_button = wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, '리뷰')]"))
            )
            self.driver.execute_script("arguments[0].click();", reviews_button)
            time.sleep(1.5)
            print(f"{log_prefix}리뷰 탭 클릭 완료")
            return True
        except TimeoutException:
            print(f"{log_prefix}리뷰 탭을 찾을 수 없습니다.")
            return False

    def sort_reviews(self, sort_method, restaurant_name):
        """리뷰 정렬 - 최적화 (안정성 개선)"""
        log_prefix = f"[{restaurant_name}] "
        try:
            sort_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[@aria-label='리뷰 정렬' or contains(@data-value, '정렬')]"))
            )
            self.driver.execute_script("arguments[0].click();", sort_button)
            time.sleep(0.8)

            if sort_method == 'newest':
                xpath = "//div[@role='menuitemradio' and contains(.//div, '최신순')]"
            else:
                xpath = "//div[@role='menuitemradio' and contains(.//div, '관련성순')]"
            
            option = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            self.driver.execute_script("arguments[0].click();", option)
            time.sleep(1.5)
            print(f"{log_prefix}{sort_method} 정렬 완료")
            return True
        except (TimeoutException, NoSuchElementException):
            print(f"{log_prefix}정렬 옵션을 찾을 수 없습니다. 기본 정렬로 진행합니다.")
            return False

    def expand_all_reviews_batch(self, review_elements, restaurant_name):
        """모든 리뷰의 '자세히', '원문보기' 버튼을 배치로 클릭 - JavaScript 사용"""
        log_prefix = f"[{restaurant_name}] "
        script = """
        var reviews = arguments[0];
        reviews.forEach(function(review) {
            var detailButtons = review.querySelectorAll("button.w8nwRe");
            detailButtons.forEach(function(btn) {
                if (btn.textContent.includes('자세히')) {
                    btn.click();
                }
            });
            
            var originalButtons = review.querySelectorAll("button.kyuRq");
            originalButtons.forEach(function(btn) {
                if (btn.textContent.includes('원문보기') || btn.textContent.includes('원본 보기')) {
                    btn.click();
                }
            });
        });
        """
        
        try:
            self.driver.execute_script(script, review_elements)
            time.sleep(0.5)
        except Exception as e:
            print(f"{log_prefix}배치 확장 중 오류: {str(e)}")

    def extract_reviews_batch(self, review_elements, restaurant_name):
        """여러 리뷰를 한 번에 배치 처리"""
        log_prefix = f"[{restaurant_name}] "
        reviews = []
        
        script = """
        var reviews = arguments[0];
        var results = [];
        
        reviews.forEach(function(review) {
            try {
                var data = {};
                
                var elementsWithId = review.querySelectorAll('[data-review-id]');
                data.review_id = elementsWithId.length > 0 ? elementsWithId[0].getAttribute('data-review-id') : null;
                
                var ratingElement = review.querySelector('span.kvMYJc');
                if (ratingElement) {
                    var ariaLabel = ratingElement.getAttribute('aria-label');
                    var match = ariaLabel.match(/별표\\s+(\\d+)개||(\\d+)\\s+stars?/);
                    data.rating = match ? parseInt(match[1] || match[2]) : null;
                }
                
                var dateElement = review.querySelector('span.rsqaWe');
                data.date = dateElement ? dateElement.textContent.trim() : null;
                
                var textDiv = review.querySelector('div.MyEned');
                if (textDiv) {
                    data.language = textDiv.getAttribute('lang');
                    var textSpan = textDiv.querySelector('span.wiI7pd');
                    data.text = textSpan ? textSpan.textContent.trim() : textDiv.textContent.trim();
                }
                
                if (data.text) {
                    results.push(data);
                }
            } catch (e) {
            }
        });
        
        return results;
        """
        
        try:
            results = self.driver.execute_script(script, review_elements)
            reviews.extend(results)
            print(f"{log_prefix}배치 처리: {len(results)}개 리뷰 추출")
        except Exception as e:
            print(f"{log_prefix}배치 추출 중 오류: {str(e)}")
            reviews.extend(self._extract_reviews_fallback(review_elements))
        
        return reviews

    def _extract_reviews_fallback(self, review_elements):
        """JavaScript 실패 시 폴백 메서드"""
        reviews = []
        for review_element in review_elements:
            try:
                review_data = self._extract_single_review(review_element)
                if review_data and review_data.get('text'):
                    reviews.append(review_data)
            except StaleElementReferenceException:
                continue
        return reviews

    def _extract_single_review(self, review_element):
        """단일 리뷰 추출 (폴백용)"""
        try:
            review_id = None
            try:
                elements_with_id = review_element.find_elements(By.CSS_SELECTOR, "[data-review-id]")
                if elements_with_id:
                    review_id = elements_with_id[0].get_attribute("data-review-id")
            except:
                pass

            rating = None
            try:
                rating_element = review_element.find_element(By.CSS_SELECTOR, "span.kvMYJc")
                aria_label = rating_element.get_attribute("aria-label")
                match = re.search(r'별표\s+(\d+)개|(\d+)\s+stars?', aria_label)
                if match:
                    rating = int(match.group(1) or match.group(2))
            except:
                pass

            date = None
            try:
                date_element = review_element.find_element(By.CSS_SELECTOR, "span.rsqaWe")
                date = date_element.text.strip()
            except:
                pass

            text, lang = None, None
            try:
                review_text_div = review_element.find_element(By.CSS_SELECTOR, "div.MyEned")
                lang = review_text_div.get_attribute("lang")
                try:
                    text_span = review_text_div.find_element(By.CSS_SELECTOR, "span.wiI7pd")
                    text = text_span.text.strip()
                except:
                    text = review_text_div.text.strip()
            except:
                pass

            if text:
                return {
                    "review_id": review_id,
                    "rating": rating,
                    "date": date,
                    "text": text,
                    "language": lang
                }
        except:
            pass
        return None

    def smart_scroll(self, scrollable_element, target_count, restaurant_name):
        """스마트 스크롤 - 목표 개수에 도달하면 조기 종료 (안정성 개선)"""
        log_prefix = f"[{restaurant_name}] "
        last_height = 0
        stale_count = 0
        max_stale = 20
        
        while stale_count < max_stale:
            current_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", 
                scrollable_element
            )
            
            current_reviews = len(self.driver.find_elements(By.CSS_SELECTOR, "div.jJc9Ad"))
            
            if target_count and current_reviews >= target_count * 1.5:
                print(f"{log_prefix}목표 개수 도달: {current_reviews}개")
                break
            
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", 
                scrollable_element
            )
            time.sleep(1.2)
            
            new_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", 
                scrollable_element
            )
            
            if new_height == last_height:
                stale_count += 1
            else:
                stale_count = 0
            
            last_height = new_height

    def crawl_reviews_by_sort(self, place_id, restaurant_name, sort_method='newest'):
        """특정 장소의 리뷰를 특정 정렬 방식으로 크롤링 - 최적화 (안정성 개선)"""
        log_prefix = f"[{restaurant_name}] "
        url = self.get_reviews_url(place_id)
        print(f"{log_prefix}크롤링 시작: {sort_method}")

        self.driver.get(url)
        time.sleep(2)

        # 리뷰 탭 클릭
        if not self.click_reviews_tab(restaurant_name):
            return []

        # 정렬
        self.sort_reviews(sort_method, restaurant_name)

        # 스크롤 컨테이너 찾기
        try:
            scrollable_div = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.m6QErb.DxyBCb"))
            )
            print(f"{log_prefix}스크롤 컨테이너 찾기 완료")
        except TimeoutException:
            print(f"{log_prefix}스크롤 가능한 영역을 찾을 수 없습니다.")
            return []

        time.sleep(2)

        # 스마트 스크롤로 리뷰 로드
        target = self.max_reviews if self.max_reviews else 1000
        self.smart_scroll(scrollable_div, target, restaurant_name)

        # 모든 리뷰 요소 한 번에 가져오기
        review_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.jJc9Ad")
        print(f"{log_prefix}총 {len(review_elements)}개 리뷰 요소 발견")

        # 배치로 버튼 확장
        self.expand_all_reviews_batch(review_elements, restaurant_name)

        # 배치로 리뷰 데이터 추출
        reviews = self.extract_reviews_batch(review_elements, restaurant_name)

        # 최대 개수 제한
        if self.max_reviews and len(reviews) > self.max_reviews:
            reviews = reviews[:self.max_reviews]

        print(f"{log_prefix}총 {len(reviews)}개의 리뷰를 수집했습니다.")
        return reviews

    def crawl_reviews(self, place_id, restaurant_name):
        """특정 장소의 리뷰를 최신순과 관련성순으로 모두 크롤링하고 중복 제거"""
        log_prefix = f"[{restaurant_name}] "
        print(f"\n{'='*60}")
        print(f"{log_prefix}리뷰 크롤링 시작")
        print(f"{'='*60}")

        # 1. 최신순으로 크롤링
        print(f"{log_prefix}[1단계] 최신순 크롤링 시작...")
        newest_reviews = self.crawl_reviews_by_sort(place_id, restaurant_name, 'newest')
        print(f"{log_prefix}[1단계] 최신순 크롤링 완료: {len(newest_reviews)}개")

        # 2. 관련성순으로 크롤링
        print(f"{log_prefix}[2단계] 관련성순 크롤링 시작...")
        relevance_reviews = self.crawl_reviews_by_sort(place_id, restaurant_name, 'relevance')
        print(f"{log_prefix}[2단계] 관련성순 크롤링 완료: {len(relevance_reviews)}개")

        # 3. 중복 제거
        print(f"{log_prefix}[3단계] 중복 제거 시작...")
        all_reviews = newest_reviews + relevance_reviews

        # review_id 기반으로 중복 제거
        seen_ids = set()
        unique_reviews = []
        duplicate_count = 0

        for review in all_reviews:
            review_id = review.get('review_id')
            if review_id:
                if review_id not in seen_ids:
                    seen_ids.add(review_id)
                    unique_reviews.append(review)
                else:
                    duplicate_count += 1
            else:
                text_date_key = f"{review.get('text')}_{review.get('date')}"
                if text_date_key not in seen_ids:
                    seen_ids.add(text_date_key)
                    unique_reviews.append(review)
                else:
                    duplicate_count += 1

        print(f"{log_prefix}[3단계] 중복 제거 완료: {duplicate_count}개 제거됨")
        print(f"\n{'='*60}")
        print(f"{log_prefix}최종 결과: 총 {len(unique_reviews)}개의 고유 리뷰")
        print(f"{'='*60}\n")

        return unique_reviews

    def crawl_single_restaurant(self, restaurant, output_dir, grid_from_filename):
        """단일 식당 크롤링 (병렬 처리용)"""
        name = restaurant['name']
        place_id = restaurant['place_id']
        grid = restaurant.get('grid', grid_from_filename or place_id)
        grid_name = f"{grid}_{name}"
        log_prefix = f"[{name}] "
        
        # 새로운 grid별 디렉토리 경로 생성
        grid_output_dir = os.path.join(output_dir, grid)
        os.makedirs(grid_output_dir, exist_ok=True) # 디렉토리 생성

        try:
            reviews = self.crawl_reviews(place_id, name)
            review_data = {
                "name": name,
                "place_id": place_id,
                "grid": grid,
                "address": restaurant.get('address'),
                "rating": restaurant.get('rating'),
                "user_ratings_total": restaurant.get('user_ratings_total'),
                "phone_number": restaurant.get('phone_number'),
                "reviews": reviews,
                "reviews_count": len(reviews)
            }

            # grid별 디렉토리에 파일 저장
            output_file = os.path.join(grid_output_dir, f"{grid_name}_reviews.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(review_data, f, ensure_ascii=False, indent=4)
            
            print(f"\n{'='*60}")
            print(f"{log_prefix}✓ 저장 완료: {output_file} (리뷰 {len(reviews)}개)")
            print(f"{'='*60}\n")
            return len(reviews)

        except Exception as e:
            print(f"{log_prefix}오류 발생: {str(e)}")
            error_data = {
                "name": name,
                "place_id": place_id,
                "grid": grid,
                "error": str(e),
                "reviews": []
            }
            # 오류 발생 시에도 grid별 디렉토리에 저장
            output_file = os.path.join(grid_output_dir, f"{grid_name}_reviews.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=4)
            print(f"{log_prefix}✗ 오류 저장: {output_file}")
            return 0

    def crawl_all_restaurants(self, restaurants_file, output_dir='reviews'):
        """restaurants.json 파일의 모든 식당 리뷰 크롤링 및 개별 저장"""
        # 파일명에서 grid 추출
        filename = os.path.basename(restaurants_file)
        match = re.search(r"restaurants_(.+?)\.json", filename)
        grid_from_filename = match.group(1) if match else None
        
        # restaurants.json 읽기
        with open(restaurants_file, 'r', encoding='utf-8') as f:
            restaurants = json.load(f)

        # 출력 디렉토리 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"디렉토리 생성: {output_dir}")

        processed_count = 0
        total_reviews_count = 0

        # 순차 처리 (단일 브라우저 인스턴스)
        for restaurant in restaurants:
            reviews_count = self.crawl_single_restaurant(restaurant, output_dir, grid_from_filename)
            if reviews_count > 0:
                processed_count += 1
                total_reviews_count += reviews_count

        return processed_count, total_reviews_count

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()


def crawl_restaurant_worker(args):
    """병렬 처리를 위한 워커 함수"""
    restaurant, output_dir, grid_from_filename, headless, max_reviews = args
    
    # 각 워커가 자체 크롤러 인스턴스 생성
    crawler = OptimizedGoogleMapsReviewCrawler(headless=headless, max_reviews=max_reviews)
    
    try:
        reviews_count = crawler.crawl_single_restaurant(restaurant, output_dir, grid_from_filename)
        return reviews_count
    finally:
        crawler.close()


def crawl_all_restaurants_parallel(restaurants_file, output_dir='reviews', headless=False, 
                                   max_reviews=None, max_workers=2):
    """병렬 처리로 여러 식당을 동시에 크롤링"""
    # 파일명에서 grid 추출
    filename = os.path.basename(restaurants_file)
    match = re.search(r"restaurants_(.+?)\.json", filename)
    grid_from_filename = match.group(1) if match else None
    
    # restaurants.json 읽기
    with open(restaurants_file, 'r', encoding='utf-8') as f:
        restaurants = json.load(f)

    # 출력 디렉토리 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"디렉토리 생성: {output_dir}")

    # 병렬 처리 준비
    args_list = [
        (restaurant, output_dir, grid_from_filename, headless, max_reviews)
        for restaurant in restaurants
    ]

    total_reviews_count = 0
    processed_count = 0

    # ProcessPoolExecutor 사용 (각 프로세스가 독립적인 브라우저 실행)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(crawl_restaurant_worker, args_list)
        
        for reviews_count in results:
            if reviews_count > 0:
                processed_count += 1
                total_reviews_count += reviews_count

    return processed_count, total_reviews_count


def main():
    parser = argparse.ArgumentParser(description='최적화된 구글 맵 리뷰 크롤러 (안정성 개선 v2)')
    parser.add_argument('--max_reviews', type=int, default=None,
                        help='식당당 수집할 최대 리뷰 개수')
    parser.add_argument('--headless', action='store_true',
                        help='백그라운드에서 수집')
    parser.add_argument('--input', type=str, default='restaurants.json',
                        help='입력 파일 경로')
    parser.add_argument('--output_dir', type=str, default='reviews',
                        help='출력 디렉토리 경로')
    parser.add_argument('--parallel', action='store_true',
                        help='병렬 처리 활성화 (더 빠르지만 리소스 사용 많음)')
    parser.add_argument('--workers', type=int, default=2,
                        help='병렬 처리 시 워커 수 (기본값: 2)')

    args = parser.parse_args()

    print("=" * 50)
    print("최적화된 구글 맵 리뷰 크롤러 시작 (안정성 개선 v2)")
    print("=" * 50)
    print(f"입력 파일: {args.input}")
    print(f"출력 디렉토리: {args.output_dir}")
    print(f"최대 리뷰 개수: {args.max_reviews if args.max_reviews else '제한 없음'}")
    print(f"헤드리스 모드: {'예' if args.headless else '아니오'}")
    print(f"병렬 처리: {'예 (워커 ' + str(args.workers) + '개)' if args.parallel else '아니오'}")
    print("=" * 50)

    start_time = time.time()

    try:
        if args.parallel:
            # 병렬 처리
            processed_count, total_reviews = crawl_all_restaurants_parallel(
                args.input, args.output_dir, args.headless, 
                args.max_reviews, args.workers
            )
        else:
            # 순차 처리
            crawler = OptimizedGoogleMapsReviewCrawler(
                headless=args.headless, 
                max_reviews=args.max_reviews
            )
            try:
                processed_count, total_reviews = crawler.crawl_all_restaurants(
                    args.input, args.output_dir
                )
            finally:
                crawler.close()

        # 소요 시간 계산
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        # 요약 출력
        print("\n" + "=" * 50)
        print("크롤링 완료!")
        print("=" * 50)
        print(f"총 식당 수: {processed_count}")
        print(f"총 리뷰 수: {total_reviews}")
        print(f"소요 시간: {minutes}분 {seconds}초")
        if total_reviews > 0:
            print(f"평균 속도: {total_reviews / elapsed_time:.2f} 리뷰/초")
        print(f"저장 위치: {args.output_dir}/")

    except FileNotFoundError:
        print(f"오류: {args.input} 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

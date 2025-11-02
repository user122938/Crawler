import json
import time
import argparse
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import re


class GoogleMapsReviewCrawler:
    def __init__(self, headless=False, max_reviews=None):
        """
        구글 맵 리뷰 크롤러 초기화

        Args:
            headless (bool): 브라우저를 백그라운드에서 실행할지 여부
            max_reviews (int): 수집할 최대 리뷰 개수
        """
        self.max_reviews = max_reviews
        self.driver = self._setup_driver(headless)

    def _setup_driver(self, headless):
        """크롬 드라이버 설정"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--lang=ko-KR')

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver

    def get_reviews_url(self, place_id):
        """place_id를 사용하여 구글 맵 URL 생성"""
        return f"https://www.google.com/maps/place/?q=place_id:{place_id}"

    def click_reviews_tab(self):
        """리뷰 탭 클릭"""
        try:
            # 리뷰 버튼 찾기 (aria-label에 "리뷰" 포함)
            wait = WebDriverWait(self.driver, 10)
            reviews_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, '리뷰')]"))
            )
            reviews_button.click()
            time.sleep(2)
            print("리뷰 탭 클릭 완료")
            return True
        except TimeoutException:
            print("리뷰 탭을 찾을 수 없습니다.")
            return False

    def sort_by_newest(self):
        """리뷰를 최신순으로 정렬"""
        try:
            # 정렬 버튼 찾기
            sort_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='리뷰 정렬' or contains(@data-value, '정렬')]"))
            )
            sort_button.click()
            time.sleep(1)

            # 최신순 옵션 클릭
            newest_option = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitemradio' and contains(.//div, '최신순')]"))
            )
            newest_option.click()
            time.sleep(2)
            print("최신순 정렬 완료")
        except (TimeoutException, NoSuchElementException):
            print("정렬 옵션을 찾을 수 없습니다. 기본 정렬로 진행합니다.")

    def extract_rating(self, review_element):
        """별점 추출"""
        try:
            rating_element = review_element.find_element(By.CSS_SELECTOR, "span.kvMYJc")
            aria_label = rating_element.get_attribute("aria-label")
            # "별표 5개", "별표 4개" 등에서 숫자 추출
            match = re.search(r'별표\s+(\d+)개', aria_label)
            if match:
                return int(match.group(1))
            # 영어 버전 "5 stars", "4 stars"
            match = re.search(r'(\d+)\s+stars?', aria_label)
            if match:
                return int(match.group(1))
        except (NoSuchElementException, AttributeError):
            pass
        return None

    def extract_date(self, review_element):
        """작성일자 추출"""
        try:
            date_element = review_element.find_element(By.CSS_SELECTOR, "span.rsqaWe")
            return date_element.text.strip()
        except NoSuchElementException:
            return None

    def click_expand_buttons(self, review_element):
        """'자세히' 및 '원문보기' 버튼 클릭"""
        # '자세히' 버튼 클릭
        try:
            detail_button = review_element.find_element(
                By.XPATH, ".//button[contains(@class, 'w8nwRe') and contains(., '자세히')]"
            )
            if detail_button.is_displayed():
                self.driver.execute_script("arguments[0].click();", detail_button)
                time.sleep(0.5)
        except (NoSuchElementException, ElementClickInterceptedException):
            pass

        # '원문보기' 또는 '원본 보기' 버튼 클릭
        try:
            original_button = review_element.find_element(
                By.XPATH, ".//button[contains(@class, 'kyuRq') and (contains(., '원문보기') or contains(., '원본 보기'))]"
            )
            if original_button.is_displayed():
                self.driver.execute_script("arguments[0].click();", original_button)
                time.sleep(0.5)
        except (NoSuchElementException, ElementClickInterceptedException):
            pass

    def extract_review_text_and_lang(self, review_element):
        """리뷰 텍스트와 언어 정보 추출"""
        try:
            review_text_div = review_element.find_element(By.CSS_SELECTOR, "div.MyEned")
            lang = review_text_div.get_attribute("lang")

            # wiI7pd 클래스의 span에서 텍스트 추출
            try:
                text_span = review_text_div.find_element(By.CSS_SELECTOR, "span.wiI7pd")
                text = text_span.text.strip()
            except NoSuchElementException:
                text = review_text_div.text.strip()

            return text, lang
        except NoSuchElementException:
            return None, None

    def scroll_reviews(self, scrollable_element, pause_time=2):
        """리뷰 스크롤"""
        last_height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_element)

        while True:
            # 스크롤 다운
            self.driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight)", scrollable_element)
            time.sleep(pause_time)

            # 새로운 높이 계산
            new_height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_element)

            # 더 이상 스크롤할 수 없으면 종료
            if new_height == last_height:
                break
            last_height = new_height

    def crawl_reviews(self, place_id, restaurant_name):
        """특정 장소의 리뷰 크롤링"""
        url = self.get_reviews_url(place_id)
        print(f"\n크롤링 시작: {restaurant_name}")
        print(f"URL: {url}")

        self.driver.get(url)
        time.sleep(3)

        # 리뷰 탭 클릭
        if not self.click_reviews_tab():
            return []

        # 최신순 정렬
        self.sort_by_newest()

        # 스크롤 가능한 div 찾기 (리뷰 섹션의 실제 스크롤 컨테이너)
        try:
            scrollable_div = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.m6QErb.DxyBCb"))
            )
            print("스크롤 컨테이너 찾기 완료")
        except TimeoutException:
            print("스크롤 가능한 영역을 찾을 수 없습니다.")
            return []

        reviews = []
        previous_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50  # 최대 스크롤 시도 횟수

        while scroll_attempts < max_scroll_attempts:
            # 현재 로드된 리뷰 카드 찾기
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.jJc9Ad")
            current_count = len(review_elements)

            print(f"현재 로드된 리뷰: {current_count}개")

            # 새로운 리뷰가 로드되었으면 처리
            if current_count > previous_count:
                # 새로 로드된 리뷰만 처리
                for review_element in review_elements[previous_count:]:
                    # 최대 리뷰 개수 체크
                    if self.max_reviews and len(reviews) >= self.max_reviews:
                        print(f"최대 리뷰 개수({self.max_reviews})에 도달했습니다.")
                        return reviews

                    # '자세히', '원문보기' 버튼 클릭
                    self.click_expand_buttons(review_element)

                    # 리뷰 데이터 추출
                    rating = self.extract_rating(review_element)
                    date = self.extract_date(review_element)
                    text, lang = self.extract_review_text_and_lang(review_element)

                    if text:  # 텍스트가 있는 경우만 저장
                        review_data = {
                            "rating": rating,
                            "date": date,
                            "text": text,
                            "language": lang
                        }
                        reviews.append(review_data)
                        print(f"리뷰 수집: {len(reviews)}개 (별점: {rating}, 언어: {lang})")

                previous_count = current_count
                scroll_attempts = 0  # 새 리뷰가 로드되면 카운터 리셋
            else:
                scroll_attempts += 1

            # 스크롤 (스크롤 컨테이너의 끝까지 스크롤)
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(1.5)

            # 최대 리뷰 개수에 도달했으면 종료
            if self.max_reviews and len(reviews) >= self.max_reviews:
                break

        print(f"총 {len(reviews)}개의 리뷰를 수집했습니다.")
        return reviews

    def crawl_all_restaurants(self, restaurants_file, output_dir='reviews'):
        """restaurants.json 파일의 모든 식당 리뷰 크롤링 및 개별 저장"""
        # 파일명에서 grid 추출 (예: restaurants_MN1.json → MN1)
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

        for restaurant in restaurants:
            name = restaurant['name']
            place_id = restaurant['place_id']
            
            # grid 정보가 없으면 파일명에서 추출한 grid 사용
            grid = restaurant.get('grid', grid_from_filename or place_id)

            # grid와 name 결합된 변수 생성 (예: MN1_Gramercy Tavern)
            grid_name = f"{grid}_{name}"

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

                # 개별 파일로 저장
                output_file = os.path.join(output_dir, f"{grid_name}_reviews.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(review_data, f, ensure_ascii=False, indent=4)

                print(f"✓ 저장 완료: {output_file} (리뷰 {len(reviews)}개)")
                processed_count += 1
                total_reviews_count += len(reviews)

            except Exception as e:
                print(f"오류 발생 ({name}): {str(e)}")
                # 오류가 발생해도 파일로 저장
                error_data = {
                    "name": name,
                    "place_id": place_id,
                    "grid": grid,
                    "error": str(e),
                    "reviews": []
                }
                output_file = os.path.join(output_dir, f"{grid}_reviews.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(error_data, f, ensure_ascii=False, indent=4)
                print(f"✗ 오류 저장: {output_file}")

        return processed_count, total_reviews_count

    def save_reviews(self, reviews_data, output_file):
        """리뷰 데이터를 JSON 파일로 저장"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(reviews_data, f, ensure_ascii=False, indent=4)
        print(f"\n리뷰 데이터가 {output_file}에 저장되었습니다.")

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()


def main():
    parser = argparse.ArgumentParser(description='구글 맵 리뷰 크롤러')
    parser.add_argument('--max_reviews', type=int, default=None,
                        help='식당당 수집할 최대 리뷰 개수 (예: --max_reviews 10)')
    parser.add_argument('--headless', action='store_true',
                        help='백그라운드에서 수집 (브라우저 창을 띄우지 않음)')
    parser.add_argument('--input', type=str, default='restaurants.json',
                        help='입력 파일 경로 (기본값: restaurants.json)')
    parser.add_argument('--output_dir', type=str, default='reviews',
                        help='출력 디렉토리 경로 (기본값: reviews)')

    args = parser.parse_args()

    print("=" * 50)
    print("구글 맵 리뷰 크롤러 시작")
    print("=" * 50)
    print(f"입력 파일: {args.input}")
    print(f"출력 디렉토리: {args.output_dir}")
    print(f"최대 리뷰 개수: {args.max_reviews if args.max_reviews else '제한 없음'}")
    print(f"헤드리스 모드: {'예' if args.headless else '아니오'}")
    print("=" * 50)

    crawler = None
    try:
        # 크롤러 초기화
        crawler = GoogleMapsReviewCrawler(headless=args.headless, max_reviews=args.max_reviews)

        # 모든 식당의 리뷰 크롤링 (각 식당마다 개별 파일로 저장)
        processed_count, total_reviews = crawler.crawl_all_restaurants(args.input, args.output_dir)

        # 요약 출력
        print("\n" + "=" * 50)
        print("크롤링 완료!")
        print("=" * 50)
        print(f"총 식당 수: {processed_count}")
        print(f"총 리뷰 수: {total_reviews}")
        print(f"저장 위치: {args.output_dir}/")

    except FileNotFoundError:
        print(f"오류: {args.input} 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
    finally:
        if crawler:
            crawler.close()


if __name__ == "__main__":
    main()

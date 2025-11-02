# Google Maps Restaurant & Review Crawler

구글 맵에서 식당 정보와 리뷰를 자동으로 수집하는 크롤러입니다.

## 목차

- [기능](#기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치](#설치)
- [사용법](#사용법)
  - [방법 1: 전체 파이프라인 실행 (권장)](#방법-1-전체-파이프라인-실행-권장)
  - [방법 2: 개별 스크립트 실행](#방법-2-개별-스크립트-실행)
  - [방법 3: 지구별 자동 수집 (뉴욕시)](#방법-3-지구별-자동-수집-뉴욕시)
- [파일 형식](#파일-형식)
- [주의사항](#주의사항)

## 기능

### 식당 정보 수집 (getRestaurantsInfo.py)
- Google Places API를 사용하여 식당 정보 수집
- 이름, 주소, place_id, 평점, 리뷰 수, 전화번호 수집
- 검색 쿼리 기반 식당 검색

### 리뷰 수집 (getReviews.py)
- Selenium을 이용한 동적 크롤링
- 리뷰 별점, 작성일자, 텍스트, 언어 정보 수집
- 자동으로 "자세히", "원문보기" 버튼 클릭하여 전체 리뷰 내용 수집
- 스크롤을 통한 동적 로딩으로 모든 리뷰 수집
- 최신순 정렬로 리뷰 수집
- 식당별로 정리된 JSON 형식으로 결과 저장

### 통합 파이프라인 (main.py)
- 식당 정보 수집부터 리뷰 수집까지 전체 프로세스 자동화
- 단계별 진행 상황 표시
- 특정 단계만 선택적으로 실행 가능

### 지구별 자동 수집 (collect_restaurants_by_grid.py)
- gridInfo 파일을 읽어 각 지구별로 자동 수집
- 뉴욕시 59개 커뮤니티 지구별 식당 정보 수집
- 각 지구별로 restaurants_{지구코드}.json 파일 생성 (예: restaurants_MN1.json)
- 진행 상황 표시 및 상세 로그 기록
- 중단 시 재개 기능

## 프로젝트 구조

```
review-crawler/
├── main.py                           # 전체 파이프라인 통합 스크립트
├── collect_restaurants_by_grid.py    # 지구별 자동 수집 스크립트 (NEW!)
├── getRestaurantsInfo.py             # 식당 정보 수집 스크립트
├── getReviews.py                     # 리뷰 수집 스크립트
├── config.py                         # API 키 설정
├── requirements.txt                  # 필수 패키지 목록
├── .env                              # 환경 변수 (API 키 저장)
├── girdInfo.txt                      # 뉴욕시 지구 정보 (입력)
├── restaurants.json                  # 수집된 식당 정보 (출력)
├── restaurants_MN1.json              # 지구별 식당 정보 (출력)
├── reviews.json                      # 수집된 리뷰 데이터 (출력)
├── collection_log.json               # 수집 로그 (출력)
├── make.txt                          # 프로젝트 요구사항 문서
└── value.txt                         # HTML 구조 참조 문서
```

## 설치

### 1. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. Google Maps API 키 설정

식당 정보 수집을 위해 Google Maps API 키가 필요합니다.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Places API 활성화
3. API 키 생성
4. 프로젝트 루트 디렉토리에 `.env` 파일 생성:

```env
GOOGLE_MAPS_API_KEY=your_api_key_here
```

### 3. Chrome WebDriver 설치

Selenium은 Chrome 브라우저를 제어하기 위해 ChromeDriver가 필요합니다.

**방법 1: 자동 설치 (권장)**
- Selenium 4.6 이상에서는 자동으로 ChromeDriver를 관리합니다.
- 별도 설치가 필요 없습니다.

**방법 2: 수동 설치**
1. [ChromeDriver 다운로드](https://chromedriver.chromium.org/downloads)
2. Chrome 브라우저 버전에 맞는 ChromeDriver 다운로드
3. PATH에 추가하거나 프로젝트 폴더에 저장

## 사용법

### 방법 1: 전체 파이프라인 실행 (권장)

`main.py`를 사용하면 식당 정보 수집부터 리뷰 수집까지 한 번에 실행할 수 있습니다.

#### 기본 사용

```bash
python main.py --query "restaurants in Seoul"
```

#### 상세 옵션 사용

```bash
python main.py --query "restaurants in Myeongdong" --max_restaurants 20 --max_reviews 50 --headless
```

#### 특정 단계만 실행

리뷰만 수집 (restaurants.json이 이미 있는 경우):
```bash
python main.py --skip-restaurants --max_reviews 100 --headless
```

식당 정보만 수집:
```bash
python main.py --query "sushi in Gangnam" --skip-reviews
```

#### main.py 명령어 파라미터

| 파라미터 | 설명 | 기본값 | 예시 |
|---------|------|--------|------|
| `--query` | 검색 쿼리 | 필수 | `--query "restaurants in Seoul"` |
| `--max_restaurants` | 최대 식당 수 | 30 | `--max_restaurants 20` |
| `--max_reviews` | 식당당 최대 리뷰 수 | 제한 없음 | `--max_reviews 50` |
| `--headless` | 백그라운드 실행 | False | `--headless` |
| `--restaurants_output` | 식당 정보 출력 파일 | restaurants.json | `--restaurants_output data.json` |
| `--reviews_output` | 리뷰 출력 파일 | reviews.json | `--reviews_output reviews_data.json` |
| `--skip-restaurants` | 식당 정보 수집 건너뛰기 | False | `--skip-restaurants` |
| `--skip-reviews` | 리뷰 수집 건너뛰기 | False | `--skip-reviews` |

### 방법 2: 개별 스크립트 실행

#### 2-1. 식당 정보 수집 (getRestaurantsInfo.py)

```bash
# 기본 사용
python getRestaurantsInfo.py --query "restaurants in Seoul"

# 최대 결과 수 지정
python getRestaurantsInfo.py --query "sushi in Gangnam" --max_results 50

# 출력 파일 지정
python getRestaurantsInfo.py --query "korean food" --output my_restaurants.json
```

**파라미터:**
- `--query`: 검색 쿼리 (필수)
- `--max_results`: 최대 식당 수 (기본값: 30)
- `--output`: 출력 파일 경로 (기본값: restaurants.json)

#### 2-2. 리뷰 수집 (getReviews.py)

```bash
# 기본 사용
python getReviews.py

# 최대 리뷰 개수 제한
python getReviews.py --max_reviews 10

# 백그라운드 실행
python getReviews.py --headless

# 입력/출력 파일 지정
python getReviews.py --input restaurants/restaurants_MN1.json --output MN1_reviews.json --max_reviews 100

# 모든 옵션 조합
python getReviews.py --max_reviews 50 --headless --input restaurants.json --output reviews.json
```

**파라미터:**
- `--max_reviews`: 식당당 최대 리뷰 수 (기본값: 제한 없음)
- `--headless`: 백그라운드 실행
- `--input`: 입력 파일 경로 (기본값: restaurants.json)
- `--output`: 출력 파일 경로 (기본값: reviews.json)

### 방법 3: 지구별 자동 수집 (뉴욕시)

`collect_restaurants_by_grid.py`를 사용하면 뉴욕시 59개 커뮤니티 지구의 식당 정보를 자동으로 수집할 수 있습니다.

#### 기본 사용

```bash
# 기본 사용 (girdInfo.txt 사용, 지구당 30개씩)
python collect_restaurants_by_grid.py

# 지구당 최대 식당 수 지정
python collect_restaurants_by_grid.py --max_results 50

# 출력 디렉토리 지정
python collect_restaurants_by_grid.py --output_dir ./ny_restaurants
```

#### 고급 옵션

```bash
# 처음 5개 지구만 테스트
python collect_restaurants_by_grid.py --limit 5

# 10번째 지구부터 재개 (중단된 경우)
python collect_restaurants_by_grid.py --start_from 10

# API 제한 회피를 위한 대기 시간 조정
python collect_restaurants_by_grid.py --delay 2.0

# 다른 gridInfo 파일 사용
python collect_restaurants_by_grid.py --grid_file my_grid_info.txt
```

#### 파라미터

| 파라미터 | 설명 | 기본값 | 예시 |
|---------|------|--------|------|
| `--grid_file` | gridInfo 파일 경로 | girdInfo.txt | `--grid_file my_grid.txt` |
| `--max_results` | 지구당 최대 식당 수 | 30 | `--max_results 50` |
| `--output_dir` | 출력 디렉토리 | . (현재 디렉토리) | `--output_dir ./data` |
| `--start_from` | 시작 지구 인덱스 | 0 | `--start_from 10` |
| `--limit` | 처리할 지구 수 제한 | None (전체) | `--limit 5` |
| `--delay` | 요청 사이 대기 시간(초) | 1.0 | `--delay 2.0` |

#### 출력 파일

- `restaurants_MN1.json` - 맨해튼 1지구 식당 정보
- `restaurants_MN2.json` - 맨해튼 2지구 식당 정보
- `restaurants_BX1.json` - 브롱스 1지구 식당 정보
- ... (총 59개 파일)
- `collection_log.json` - 수집 로그 및 통계

#### gridInfo 파일 형식

gridInfo 파일은 다음과 같은 형식이어야 합니다:

```
지구코드,"한국어 지역명 (영문 지역명)"
```

예시:
```
MN 1,"트라이베카, 금융 지구 (Tribeca, Financial District)"
MN 2,"그리니치 빌리지, 소호, 차이나타운 (Greenwich Village, SoHo, Chinatown)"
BX 1,"모트 헤이븐, 멜로즈 (Mott Haven, Melrose)"
```

프로젝트에 포함된 `girdInfo.txt` 파일에는 뉴욕시 59개 커뮤니티 지구 정보가 들어있습니다.

## 파일 형식

### 입력 파일: restaurants.json

`restaurants.json` 파일은 다음과 같은 형식이어야 합니다:

```json
[
    {
        "name": "식당 이름",
        "address": "주소",
        "place_id": "ChIJxxxxxx",
        "rating": 4.5,
        "user_ratings_total": 100,
        "phone_number": "02-1234-5678"
    }
]
```

### 출력 파일: reviews.json

`reviews.json` 파일은 다음과 같은 형식으로 생성됩니다:

```json
{
    "ChIJxxxxxx": {
        "name": "식당 이름",
        "place_id": "ChIJxxxxxx",
        "address": "주소",
        "rating": 4.5,
        "user_ratings_total": 100,
        "phone_number": "02-1234-5678",
        "reviews_count": 50,
        "reviews": [
            {
                "rating": 5,
                "date": "3주 전",
                "text": "리뷰 내용...",
                "language": "ko"
            }
        ]
    }
}
```

## 작동 방식

### 전체 파이프라인 (main.py)

1. **Step 1: 식당 정보 수집**
   - Google Places API를 사용하여 검색 쿼리 기반 식당 검색
   - 각 식당의 상세 정보 수집 (name, address, place_id, rating, user_ratings_total, phone_number)
   - `restaurants.json` 파일로 저장

2. **Step 2: 리뷰 수집**
   - `restaurants.json` 파일에서 식당 정보 읽기
   - 각 식당의 `place_id`를 사용하여 구글 맵 URL 생성
   - Selenium으로 브라우저 자동화:
     - 식당 페이지 접속
     - 리뷰 탭 클릭
     - 최신순 정렬
     - 스크롤하며 리뷰 로드
     - "자세히", "원문보기" 버튼 자동 클릭
     - 리뷰 데이터 수집 (별점, 날짜, 텍스트, 언어)
   - 수집된 리뷰를 `reviews.json` 파일로 저장

3. **결과 요약**
   - 총 식당 수, 리뷰 수 등 통계 표시
   - 소요 시간 및 생성된 파일 정보 출력

## 주의사항

- **Google Maps API**: Places API 사용량에 따라 비용이 발생할 수 있습니다. [가격 정책](https://mapsplatform.google.com/pricing/) 확인 필요
- **크롤링 속도**: 너무 빠르면 구글에서 차단할 수 있습니다.
- **인터넷 연결**: 안정적인 인터넷 연결이 필요합니다.
- **Chrome 브라우저**: Chrome 브라우저가 설치되어 있어야 합니다.
- **수집 시간**: 많은 리뷰를 수집할 경우 시간이 오래 걸릴 수 있습니다.
- **API 제한**: Google Places API는 요청 횟수 제한이 있습니다.

## 문제 해결

### API 키 오류
```
RuntimeError: API_KEY가 설정되어 있지 않습니다.
```
- `.env` 파일이 프로젝트 루트에 있는지 확인
- `GOOGLE_MAPS_API_KEY` 값이 올바른지 확인
- API 키에 Places API가 활성화되어 있는지 확인

### ChromeDriver 오류
```
selenium.common.exceptions.WebDriverException: 'chromedriver' executable needs to be in PATH
```
- Chrome과 ChromeDriver 버전이 일치하는지 확인
- ChromeDriver가 PATH에 있는지 확인
- Selenium 4.6 이상 버전 사용 권장 (자동 ChromeDriver 관리)

### 요소를 찾을 수 없음
```
TimeoutException: Message:
```
- 인터넷 연결 확인
- 페이지 로딩 시간이 충분한지 확인
- 구글 맵 UI가 변경되었을 수 있음 (value.txt의 HTML 구조 확인)

### API 사용량 초과
```
RuntimeError: Text Search API error: OVER_QUERY_LIMIT
```
- API 사용량이 일일 한도를 초과했습니다
- Google Cloud Console에서 사용량 확인
- 필요시 결제 정보 등록 또는 한도 증가 요청

## 라이선스

MIT

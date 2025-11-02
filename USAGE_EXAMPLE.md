# 뉴욕 식당 정보 수집 사용 예시

## 빠른 시작

### 1. 테스트 실행 (처음 3개 지구만)

```bash
python collect_restaurants_by_grid.py --limit 3 --max_results 10
```

이 명령은:
- 처음 3개 지구만 처리
- 각 지구당 최대 10개 식당 수집
- 현재 디렉토리에 결과 저장

예상 출력:
- `restaurants_MN1.json`
- `restaurants_MN2.json`
- `restaurants_MN3.json`
- `collection_log.json`

### 2. 전체 맨해튼 수집 (12개 지구)

```bash
python collect_restaurants_by_grid.py --limit 12 --max_results 50 --output_dir ./manhattan
```

이 명령은:
- 맨해튼 12개 지구 전체 처리
- 각 지구당 최대 50개 식당 수집
- `./manhattan` 디렉토리에 결과 저장

### 3. 전체 뉴욕시 수집 (59개 지구)

```bash
python collect_restaurants_by_grid.py --max_results 30 --output_dir ./ny_all --delay 2.0
```

이 명령은:
- 뉴욕시 59개 지구 전체 처리
- 각 지구당 최대 30개 식당 수집
- `./ny_all` 디렉토리에 결과 저장
- API 제한을 피하기 위해 각 요청 사이 2초 대기

**주의**: 59개 지구 전체를 수집하면 시간이 오래 걸리고 API 비용이 발생할 수 있습니다.

### 4. 중단 후 재개

만약 수집이 중단되었다면:

```bash
# 10번째 지구부터 재개
python collect_restaurants_by_grid.py --start_from 10 --output_dir ./ny_all
```

## 출력 예시

### 성공적인 실행 예시

```
📍 Parsing grid info from: girdInfo.txt
✓ Found 59 districts

🚀 Starting collection for 3 districts
   (from index 0 to 2)
   Max results per district: 10
   Output directory: .

################################################################################
Progress: 1/3 (33%)
District: [MN1] 트라이베카, 금융 지구 (Tribeca, Financial District)
################################################################################

================================================================================
[MN1] Tribeca, Financial District
Query: restaurants in Tribeca, Financial District New York
Output: .\restaurants_MN1.json
================================================================================

Query: restaurants in Tribeca, Financial District New York  |  Max: 10

총 10개 장소를 가져와 'restaurants_MN1.json' 파일에 저장했습니다.
✓ Successfully collected 10 restaurants

Waiting 1.0 seconds before next request...

...

================================================================================
📊 COLLECTION SUMMARY
================================================================================
Total districts processed: 3
✓ Successful: 3
✗ Failed: 0
📍 Total restaurants collected: 30
⏱️  Elapsed time: 25.3 seconds (0.4 minutes)

📁 Output files saved in: .
   Pattern: restaurants_{CODE}.json
📝 Log saved to: .\collection_log.json

================================================================================
```

### collection_log.json 예시

```json
{
    "timestamp": "2025-01-15 14:30:45",
    "total_districts": 3,
    "success_count": 3,
    "fail_count": 0,
    "total_restaurants": 30,
    "elapsed_seconds": 25.3,
    "failed_districts": []
}
```

## 다음 단계: 리뷰 수집

지구별로 수집한 식당 정보를 바탕으로 리뷰를 수집하려면:

```bash
# 특정 지구의 리뷰 수집
python getReviews.py --input restaurants_MN1.json --output reviews_MN1.json --max_reviews 50 --headless

# 또는 main.py를 사용하여 전체 파이프라인 실행
python main.py --skip-restaurants --input restaurants_MN1.json --output reviews_MN1.json --max_reviews 50 --headless
```

## 팁

1. **테스트 먼저**: `--limit 3` 옵션으로 먼저 테스트해보세요.
2. **API 비용 주의**: Google Places API는 유료입니다. 비용을 확인하세요.
3. **대기 시간 조정**: API 제한에 걸리면 `--delay` 값을 늘리세요.
4. **백업**: 중요한 데이터는 정기적으로 백업하세요.
5. **로그 확인**: 문제 발생 시 `collection_log.json`을 확인하세요.

import json

def run_domaeguk_sourcing_filter():
    print("🤖 제비의 도매꾹 스마트 소싱 필터링 시스템을 가동합니다...")
    
    # 도매꾹 또는 크롤링을 통해 수집된 원본 상품 데이터 (예시)
    # 실제 연동 시 크롤링하거나 가져온 상품 리스트가 이 구조로 들어갑니다.
    raw_products = [
        {"name": "북유럽 원목 무소음 벽시계", "supply_price": 9000, "market_price": 12000},  # 판매가 미달 (탈락)
        {"name": "접이식 스탠딩 알루미늄 독서대", "supply_price": 11000, "market_price": 24000}, # 마진율 합격
        {"name": "빈티지 신주 인테리어 도어벨", "supply_price": 8500, "market_price": 18000},  # 마진율 합격
        {"name": "실속형 파크골프 볼 파우치", "supply_price": 14000, "market_price": 16000},  # 마진율 부족 (탈락)
        {"name": "원목 3단 미니 수납 선반", "supply_price": 13000, "market_price": 26000},    # 마진율 합격
    ]

    valid_products = []
    
    print("\n🔍 오빠의 엄격한 기준(최소 판매가 15,000원 이상, 마진율 20% 이상)으로 검증 중...\n")
    
    for item in raw_products:
        name = item["name"]
        supply_price = item["supply_price"]
        market_price = item["market_price"]
        
        # 1. 최소 판매가 15,000원 미만인 상품 원천 배제
        if market_price < 15000:
            print(f"  ❌ [제외] '{name}' -> 판매가({market_price:,}원)가 1만 5천 원 미만입니다.")
            continue
            
        # 2. 마진율 계산 공식: ((판매가 - 도매가) / 판매가) * 100
        margin_rate = ((market_price - supply_price) / market_price) * 100
        net_profit = market_price - supply_price
        
        # 3. 마진율 20% 이상 알짜배기 상품 선별
        if margin_rate >= 20:
            item["margin_rate"] = round(margin_rate, 1)
            item["net_profit"] = net_profit
            valid_products.append(item)
            print(f"  ✨ [합격!] '{name}' | 도매: {supply_price:,}원 / 판매: {market_price:,}원 | 순수익: {net_profit:,}원 (마진율: {item['margin_rate']}%)")
        else:
            print(f"  ❌ [제외] '{name}' -> 마진율({round(margin_rate, 1)}%)이 20% 미만입니다.")

    # 최종 결과 요약 리스트 출력
    print("\n" + "="*55)
    print("🎯 [오빠를 위한 최종 도매꾹 대박 소싱 추천 리스트]")
    print("="*55)
    
    if not valid_products:
        print("조건에 맞는 상품이 없습니다. 기준 값을 다시 점검해봐요 오빠!")
    else:
        for idx, p in enumerate(valid_products, 1):
            print(f"{idx}. 상품명: {p['name']}")
            print(f"   - 공급가(도매가): {p['supply_price']:,}원")
            print(f"   - 예상 판매가: {p['market_price']:,}원")
            print(f"   - 건당 순수익: {p['net_profit']:,}원 (마진율: {p['margin_rate']}% 우수)")
            print("-" * 45)

if __name__ == "__main__":
    run_domaeguk_sourcing_filter()

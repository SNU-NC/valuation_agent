from typing import Dict, Optional
from ..collectors.financial_data_collector import FinancialDataCollector

class FCFECalculator:
    """FCFE(Free Cash Flow to Equity)를 계산하는 클래스"""
    
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.financial_collector = FinancialDataCollector(ticker_symbol)

    def calculate_fcfe(self, period: str = "annual") -> Dict[str, float]:
        """FCFE를 계산하는 메서드"""
        try:
            # 재무 지표 수집
            metrics = self.financial_collector.extract_financial_metrics(period)

            # 가장 최근 데이터와 이전 데이터 선택 (첫 번째, 두 번째 열)
            current_metrics = {}
            previous_metrics = {}
            
            for key in metrics:
                if not metrics[key].empty:
                    current_metrics[key] = metrics[key].iloc[0]
                    previous_metrics[key] = metrics[key].iloc[1] if len(metrics[key]) > 1 else 0.0
                else:
                    current_metrics[key] = 0.0
                    previous_metrics[key] = 0.0
            
            # FCFE 계산
            fcfe = (current_metrics['operating_cash_flow'] 
                    - current_metrics['capital_expenditure'] 
                    + current_metrics['repayment_of_debt'] # (-) 부채상환
                    + current_metrics['issuance_of_debt']) # (+) 부채발행
            
            # 결과 딕셔너리 생성 (float로 변환)
            results = {
                'FCFE': float(fcfe),
                'Operating Cash Flow': float(current_metrics['operating_cash_flow']),
                'Capital Expenditure': float(current_metrics['capital_expenditure']),
                'Repayment of Debt': float(current_metrics['repayment_of_debt']),
                'Issuance of Debt': float(current_metrics['issuance_of_debt']),
            }
            
            # 출력
            print("\nFCFE:")
            for key, value in results.items():
                print(f"{key}: {value:,.0f}")  # .0f로 변경하여 소수점 없애기
            
            return results
            
        except Exception as e:
            print(f"FCFE 계산 중 오류 발생: {str(e)}")
            return None

# 편의를 위한 함수형 인터페이스
def calculate_fcfe(ticker_symbol: str, period: str = "annual") -> Dict[str, float]:
    calculator = FCFECalculator(ticker_symbol)
    return calculator.calculate_fcfe(period)

if __name__ == "__main__":
    # 삼성전자의 FCFF 계산
    ticker = "005930.KS"
    results = calculate_fcfe(ticker)
    
    if results:
        print(f"\n{ticker}의 FCFE 계산 결과:")
        for key, value in results.items():
            print(f"{key}: {value:,.0f}") 
from typing import Dict, Optional
from ..collectors.financial_data_collector import FinancialDataCollector

class FCFFCalculator:
    """FCFF(Free Cash Flow to Firm)를 계산하는 클래스"""
    
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.financial_collector = FinancialDataCollector(ticker_symbol)
    
    def calculate_fcff(self, period: str = "annual") -> Dict[str, float]:
        """FCFF를 계산하는 메서드"""
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
            
            # Working Capital 계산 (현재)
            current_working_capital = current_metrics['current_assets'] - current_metrics['current_liabilities']
            current_non_current_working_capital = current_working_capital - current_metrics['cash_and_equivalents']
            print(f"Current Working Capital: {current_working_capital:,.2f}")
            print(f"Current Non-current Working Capital: {current_non_current_working_capital:,.2f}")

            # Working Capital 계산 (이전)
            previous_working_capital = previous_metrics['current_assets'] - previous_metrics['current_liabilities']
            previous_non_current_working_capital = previous_working_capital - previous_metrics['cash_and_equivalents']
            print(f"Previous Working Capital: {previous_working_capital:,.2f}")
            print(f"Previous Non-current Working Capital: {previous_non_current_working_capital:,.2f}")
            
            # Working Capital 변화량 계산
            change_in_non_current_working_capital = current_non_current_working_capital - previous_non_current_working_capital

            # FCFF 계산
            fcff = (current_metrics['ebitda'] - 
                   current_metrics['tax_provision'] - 
                   (current_metrics['capital_expenditure'] + 
                    change_in_non_current_working_capital))
            
            # 결과 딕셔너리 생성 (float로 변환)
            results = {
                'EBITDA': float(current_metrics['ebitda']),
                'Tax Provision': float(current_metrics['tax_provision']),
                'Capital Expenditure': float(current_metrics['capital_expenditure']),
                'Working Capital': float(current_working_capital),
                'Non-current Working Capital': float(current_non_current_working_capital),
                'Change in Non-current Working Capital': float(change_in_non_current_working_capital),
                'Cash and Equivalents': float(current_metrics['cash_and_equivalents']),
                'FCFF': float(fcff)
            }
            
            # 출력
            print("\nFCFF:")
            for key, value in results.items():
                print(f"{key}: {value:,.0f}")  # .0f로 변경하여 소수점 없애기
            
            return results
            
        except Exception as e:
            print(f"FCFF 계산 중 오류 발생: {str(e)}")
            return None

# 편의를 위한 함수형 인터페이스
def calculate_fcff(ticker_symbol: str, period: str = "annual") -> Dict[str, float]:
    calculator = FCFFCalculator(ticker_symbol)
    return calculator.calculate_fcff(period)

if __name__ == "__main__":
    # 삼성전자의 FCFF 계산
    ticker = "005930.KS"
    results = calculate_fcff(ticker)
    
    if results:
        print(f"\n{ticker}의 FCFF 계산 결과:")
        for key, value in results.items():
            print(f"{key}: {value:,.0f}") 
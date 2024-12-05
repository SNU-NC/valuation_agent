from typing import Dict, Optional
from ..collectors.financial_data_collector import FinancialDataCollector
import pandas as pd
from ..utils.financial_utils import calculate_effective_tax_rate

class GrowthCalculator:
    """성장률을 계산하는 클래스"""
    
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.financial_collector = FinancialDataCollector(ticker_symbol)
    
    def calculate_growth_rate(self, period: str = "annual") -> Dict[str, float]:
        """성장률 계산 (영업이익 성장률 = 재투자비율 * 투하자본이익률)"""
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
            
            # 재투자비율 계산
            reinvestment_rate = self._calculate_reinvestment_rate(current_metrics, previous_metrics)
            
            # 투하자본이익률 계산
            roic = self._calculate_return_on_invested_capital(current_metrics)
            
            # 성장률 계산
            growth_rate = reinvestment_rate * roic
            
            results = {
                'Growth Rate': growth_rate,
                'Reinvestment Rate': reinvestment_rate,
                'Return on Invested Capital': roic,
                'Components': {
                    'Capital Expenditure': float(current_metrics['capital_expenditure']),
                    'Change in Working Capital': self._calculate_change_in_working_capital(current_metrics, previous_metrics),
                    'Net Income': float(current_metrics['net_income']),
                    'EBITDA': float(current_metrics['ebitda']),
                    'Tax Provision': float(current_metrics['tax_provision']),
                    'Invested Capital': self._extract_invested_capital(current_metrics)
                }
            }
            
            # 결과 출력
            print("\n성장률 계산 결과:")
            print(f"성장률: {growth_rate:.2%}")
            print("\n구성 요소:")
            for key, value in results['Components'].items():
                print(f"{key}: {value:,.0f}")
            
            return results
            
        except Exception as e:
            print(f"성장률 계산 중 오류 발생: {str(e)}")
            return None
    
    def _calculate_reinvestment_rate(self, current: Dict[str, float], previous: Dict[str, float]) -> float:
        """재투자비율 계산"""
        try:
            # Working Capital 변화량 계산
            change_in_wc = self._calculate_change_in_working_capital(current, previous)
            print(f"운전자본 변동: {change_in_wc:,.0f}")
            
            # 재투자비율 = (자본적지출 + 운전자본 변동) / 당기순이익
            capex = current['capital_expenditure']
            print(f"자본적지출: {capex:,.0f}")
            
            net_income = current['net_income']
            print(f"당기순이익: {net_income:,.0f}")
            
            if net_income == 0:
                return 0.0
            
            reinvestment = (capex + change_in_wc) / net_income
            print(f"재투자비율: {reinvestment:.2%}")
            # 비정상적인 값 처리
            if not (-100 <= reinvestment <= 100):  # -10000% ~ 10000% 범위
                print(f"Warning: 비정상적인 재투자비율({reinvestment:.2%}) 감지")
                return 0.5  # 기본값 50%
                
            return reinvestment
            
        except Exception as e:
            print(f"재투자비율 계산 중 오류: {str(e)}")
            return 0.5
    
    def _calculate_return_on_invested_capital(self, metrics: Dict[str, float]) -> float:
        """투하자본이익률(ROIC) 계산"""
        try:
            # NOPAT (Net Operating Profit After Taxes) 계산
            effective_tax_rate = calculate_effective_tax_rate(metrics)
            noplat = metrics['ebit'] * (1 - effective_tax_rate)
            print(f"NOPLAT: {noplat:,.0f}")
            # 투하자본 추출
            invested_capital = self._extract_invested_capital(metrics)
            print(f"투하자본: {invested_capital:,.0f}")
            if invested_capital == 0:
                return 0.0
            
            roic = noplat / invested_capital
            print(f"투하자본이익률: {roic:.2%}") 

            # 비정상적인 값 처리
            if not (-0.5 <= roic <= 0.5):  # -50% ~ 50% 범위
                print(f"Warning: 비정상적인 ROIC({roic:.2%}) 감지")
                return 0.1  # 기본값 10%
                
            return roic
            
        except Exception as e:
            print(f"ROIC 계산 중 오류: {str(e)}")
            return 0.1
    
    def _extract_invested_capital(self, metrics: Dict[str, float]) -> float:
        """투하자본 추출"""
        try:
            return metrics['invested_capital']
            
        except Exception as e:
            print(f"투하자본 계산 중 오류: {str(e)}")
            return metrics.get('total_assets', 0.0)  # 기본값 사용
    
    def _calculate_change_in_working_capital(self, current: Dict[str, float], previous: Dict[str, float]) -> float:
        """운전자본 변동 계산"""
        try:
            # 현재 운전자본
            current_wc = current['current_assets'] - current['current_liabilities']
            
            # 이전 운전자본
            previous_wc = previous['current_assets'] - previous['current_liabilities']
            
            return current_wc - previous_wc
            
        except Exception as e:
            print(f"운전자본 변동 계산 중 오류: {str(e)}")
            return 0.0
    
    def calculate_average_growth_rate(self, years: int = 5, period: str = "annual") -> Dict[str, float]:
        """지정된 연도 수만큼의 평균 성장률 계산"""
        try:
            growth_rates = []
            yearly_results = []
            
            # 각 연도별 성장률 계산
            metrics = self.financial_collector.extract_financial_metrics(period)
            
            # 데이터가 충분한지 확인
            min_required_data = min(len(metrics[key]) for key in metrics if not metrics[key].empty)
            available_years = min(years, min_required_data - 1)  # 성장률 계산에는 최소 2년치 데이터 필요
            
            if available_years < 2:
                raise ValueError("성장률 계산에 필요한 충분한 데이터가 없습니다")
            
            # 각 기간별 성장률 계산
            for i in range(available_years - 1):
                current_metrics = {}
                previous_metrics = {}
                
                for key in metrics:
                    if not metrics[key].empty:
                        current_metrics[key] = metrics[key].iloc[i]
                        previous_metrics[key] = metrics[key].iloc[i + 1]
                    else:
                        current_metrics[key] = 0.0
                        previous_metrics[key] = 0.0
                
                # 해당 연도의 성장률 계산
                reinvestment_rate = self._calculate_reinvestment_rate(current_metrics, previous_metrics)
                roic = self._calculate_return_on_invested_capital(current_metrics)
                growth_rate = reinvestment_rate * roic
                
                if -1 <= growth_rate <= 1:  # 비정상적인 값 필터링
                    growth_rates.append(growth_rate)
                    yearly_results.append({
                        'year': metrics['net_income'].index[i].year,
                        'growth_rate': growth_rate,
                        'reinvestment_rate': reinvestment_rate,
                        'roic': roic
                    })
            
            # 평균 성장률 계산
            average_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0.0
            
            results = {
                'average_growth_rate': average_growth_rate,
                'yearly_results': yearly_results,
                'years_calculated': len(growth_rates)
            }
            
            # 결과 출력
            print(f"\n{len(growth_rates)}년 평균 성장률: {average_growth_rate:.2%}")
            print("\n연도별 성장률:")
            for year_result in yearly_results:
                print(f"{year_result['year']}년: {year_result['growth_rate']:.2%}")
            
            return results
            
        except Exception as e:
            print(f"평균 성장률 계산 중 오류 발생: {str(e)}")
            return None

# 편의를 위한 함수형 인터페이스
def calculate_growth_rate(ticker_symbol: str, period: str = "annual") -> Dict[str, float]:
    calculator = GrowthCalculator(ticker_symbol)
    return calculator.calculate_growth_rate(period)

# 편의를 위한 함수형 인터페이스 추가
def calculate_average_growth_rate(ticker_symbol: str, years: int = 5, period: str = "annual") -> Dict[str, float]:
    calculator = GrowthCalculator(ticker_symbol)
    return calculator.calculate_average_growth_rate(years, period)

if __name__ == "__main__":
    # 삼성전자의 성장률 계산
    ticker = "005930.KS"
    results = calculate_growth_rate(ticker) 
    # 삼성전자의 5년 평균 성장률 계산
    results = calculate_average_growth_rate(ticker)
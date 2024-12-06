from typing import Dict, Tuple
from ..calculators.fcfe_calculator import FCFECalculator
from ..calculators.wacc_calculator import WACCCalculator
from ..calculators.growth_calculator_shareholder import GrowthCalculatorShareholder
from ..collectors.info_data_collector import InfoDataCollector
from ..collectors.financial_data_collector import FinancialDataCollector

class ValuationCalculator:
    """회사 가치를 계산하는 클래스"""
    
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.fcfe_calculator = FCFECalculator(ticker_symbol)
        self.wacc_calculator = WACCCalculator(ticker_symbol)
        self.net_income_growth_calculator = GrowthCalculatorShareholder(ticker_symbol)
        self.financial_data_collector = FinancialDataCollector(ticker_symbol)
        self.info_collector = InfoDataCollector(ticker_symbol)
        self.shares_outstanding = self.info_collector.get_info()['shares_outstanding']
    def _calculate_fcfe(self, period: str = "annual") -> Dict[str, float]:
        """FCFE 계산"""
        return self.fcfe_calculator.calculate_fcfe(period)
    
    def _calculate_wacc(self) -> float:
        """WACC 계산"""
        return self.wacc_calculator.calculate_wacc()
    
    def _calculate_net_income_growth_rate(self) -> Dict[str, float]:
        """성장률 계산"""
        return self.net_income_growth_calculator.calculate_net_income_growth_rate()
    
    def calculate_5year_present_value(self, period: str = "annual") -> float:
        """향후 5년 주주가치의 현재가치 계산
        
        Args:
            period (str): 기간 (annual, quarterly)
        Returns:
            float: 향후 5년 주주가치의 총 현재가치
        """
        metrics = self.financial_data_collector.extract_financial_metrics(period)
        calculated_fcfe = self._calculate_fcfe(period)
        calculated_wacc = self._calculate_wacc()
        calculated_net_income_growth_rate = self._calculate_net_income_growth_rate()

        fcfe = calculated_fcfe['FCFE']
        net_income_growth_rate = calculated_net_income_growth_rate['Growth Rate']
        wacc = calculated_wacc['WACC']
        retention_ratio = calculated_net_income_growth_rate['Retention Ratio']

        # 3년 평균 순이익 계산
        net_income_values = metrics['net_income'].iloc[:min(3, len(metrics))]
        net_income = net_income_values.mean()

        _1year_fcfe = fcfe
        
        _2year_fcfe = _1year_fcfe + net_income * ((1 + net_income_growth_rate) ** 1) * retention_ratio
        _3year_fcfe = _2year_fcfe + net_income * ((1 + net_income_growth_rate) ** 2) * retention_ratio
        _4year_fcfe = _3year_fcfe + net_income * ((1 + net_income_growth_rate) ** 3) * retention_ratio
        _5year_fcfe = _4year_fcfe + net_income * ((1 + net_income_growth_rate) ** 4) * retention_ratio

        self._5year_fcfe = _5year_fcfe

        print(f"_1year_fcfe: {_1year_fcfe}")
        print(f"_2year_fcfe: {_2year_fcfe}")
        print(f"_3year_fcfe: {_3year_fcfe}")
        print(f"_4year_fcfe: {_4year_fcfe}")
        print(f"_5year_fcfe: {_5year_fcfe}")

        _1year_present_value = _1year_fcfe
        _2year_present_value = _2year_fcfe / ((1 + wacc) ** 1)
        _3year_present_value = _3year_fcfe / ((1 + wacc) ** 2)
        _4year_present_value = _4year_fcfe / ((1 + wacc) ** 3)
        _5year_present_value = _5year_fcfe / ((1 + wacc) ** 4)

        total_present_value = _1year_present_value + _2year_present_value + _3year_present_value + _4year_present_value + _5year_present_value

        return total_present_value
        
    def calculate_terminal_value(self, period: str = "annual") -> Tuple[float, float, float, float, float]:
        """Terminal Value 계산
        
        Args:
            period (str): 기간 (annual, quarterly)
        Returns:
            Tuple[float, float, float, float, float]: Terminal Value 계산 결과
        """
        calculated_fcfe = self._calculate_fcfe(period)
        calculated_wacc = self._calculate_wacc()
        calculated_net_income_growth_rate = self._calculate_net_income_growth_rate()
        fcfe = calculated_fcfe['FCFE']
        net_income_growth_rate = calculated_net_income_growth_rate['Growth Rate']
        growth_rate_tv = 0.0 # Terminal Value 계산에 사용할 성장률 0%로 고정(성숙기업 무성장 예상)

        wacc = round(calculated_wacc['WACC'], 2)

        _6year_fcfe = self._5year_fcfe * (1 + growth_rate_tv)
        terminal_value = _6year_fcfe / (wacc - growth_rate_tv)

        # print(f"_6year_fcfe: {_6year_fcfe}")
        # print(f"terminal_value: {terminal_value}")
        
        return terminal_value, fcfe, wacc, net_income_growth_rate, growth_rate_tv
    
    def calculate_total_value(self, period: str = "annual") -> Dict[str, float]:
        """총가치 계산"""
        _5year_pv = self.calculate_5year_present_value(period)
        terminal_value, fcfe, wacc, net_income_growth_rate, growth_rate_tv = self.calculate_terminal_value(period)
        terminal_value_pv = terminal_value / ((1 + wacc) ** 5)
        total_value = _5year_pv + terminal_value_pv
        print(f"Total Value: {total_value}")
        return total_value, fcfe, wacc, net_income_growth_rate, growth_rate_tv
    
    def calculate_per_share(self, period: str = "annual") -> float:
        """주당가치 계산"""
        total_value, fcfe, wacc, growth_rate_fcfe, growth_rate_tv = self.calculate_total_value(period)
        per_share = total_value / self.shares_outstanding
        print(f"Per Share: {per_share}")
        return per_share, fcfe, wacc, growth_rate_fcfe, growth_rate_tv
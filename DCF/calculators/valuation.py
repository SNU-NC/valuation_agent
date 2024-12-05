from typing import Dict
from ..calculators.fcfe_calculator import FCFECalculator
from ..calculators.wacc_calculator import WACCCalculator
from ..calculators.growth_calculator_shareholder import GrowthCalculatorShareholder
from ..collectors.info_data_collector import InfoDataCollector

class ValuationCalculator:
    """회사 가치를 계산하는 클래스"""
    
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.fcfe_calculator = FCFECalculator(ticker_symbol)
        self.wacc_calculator = WACCCalculator(ticker_symbol)
        self.growth_calculator = GrowthCalculatorShareholder(ticker_symbol) 
        self.info_collector = InfoDataCollector(ticker_symbol)
        self.shares_outstanding = self.info_collector.get_info()['shares_outstanding']
    def _calculate_fcfe(self, period: str = "annual") -> Dict[str, float]:
        """FCFE 계산"""
        return self.fcfe_calculator.calculate_fcfe(period)
    
    def _calculate_wacc(self) -> float:
        """WACC 계산"""
        return self.wacc_calculator.calculate_wacc()
    
    def _calculate_growth_rate(self) -> Dict[str, float]:
        """성장률 계산"""
        return self.growth_calculator.calculate_growth_rate()
    
    def calculate_5year_present_value(self, period: str = "annual") -> Dict[str, float]:
        """향후 5년 가치의 현재가치 계산"""
        calculated_fcfe = self._calculate_fcfe(period)
        calculated_wacc = self._calculate_wacc()
        calculated_growth_rate = self._calculate_growth_rate()

        fcfe = calculated_fcfe['FCFE']
        growth_rate = calculated_growth_rate['Growth Rate']
        wacc = calculated_wacc['WACC']

        _1year_fcfe = fcfe
        
        # 2년차 FCFE 계산
        if _1year_fcfe < 0:
            _2year_fcfe = fcfe * (1 - growth_rate)
        else:
            _2year_fcfe = fcfe * (1 + growth_rate)
        
        # 3년차 FCFE 계산
        if _2year_fcfe < 0:
            _3year_fcfe = _2year_fcfe * (1 - growth_rate)
        else:
            _3year_fcfe = _2year_fcfe * (1 + growth_rate)
        
        # 4년차 FCFE 계산
        if _3year_fcfe < 0:
            _4year_fcfe = _3year_fcfe * (1 - growth_rate)
        else:
            _4year_fcfe = _3year_fcfe * (1 + growth_rate)
        
        # 5년차 FCFE 계산
        if _4year_fcfe < 0:
            _5year_fcfe = _4year_fcfe * (1 - growth_rate)
        else:
            _5year_fcfe = _4year_fcfe * (1 + growth_rate)

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
        
    def calculate_terminal_value(self, period: str = "annual") -> Dict[str, float]:
        """종결가치 계산"""
        calculated_fcfe = self._calculate_fcfe(period)
        calculated_wacc = self._calculate_wacc()
        calculated_growth_rate = self._calculate_growth_rate()
        fcfe = calculated_fcfe['FCFE']
        growth_rate_fcfe = calculated_growth_rate['Growth Rate']
        growth_rate_tv = 0.01 # 성장률 1%로 고정

        wacc = round(calculated_wacc['WACC'], 2)
        if self._5year_fcfe < 0: # 음수일 경우 성장률만큼 적자 감소
            _6year_fcfe = self._5year_fcfe * (1 - growth_rate_tv)
        else: # 양수일 경우 성장률만큼 이익 증가
            _6year_fcfe = self._5year_fcfe * (1 + growth_rate_tv)
        
        if _6year_fcfe < 0: # 음수일 경우 적자 증가
            terminal_value = _6year_fcfe / -(wacc - growth_rate_tv)
        else: # 양수일 경우 이익 감소
            terminal_value = _6year_fcfe / (wacc - growth_rate_tv)

        print(f"_6year_fcfe: {_6year_fcfe}")
        print(f"terminal_value: {terminal_value}")
        
        return terminal_value, fcfe, wacc, growth_rate_fcfe, growth_rate_tv
    
    def calculate_total_value(self, period: str = "annual") -> Dict[str, float]:
        """총가치 계산"""
        _5year_pv = self.calculate_5year_present_value(period)
        terminal_value, fcfe, wacc, growth_rate_fcfe, growth_rate_tv = self.calculate_terminal_value(period)
        total_value = _5year_pv + terminal_value
        print(f"Total Value: {total_value}")
        return total_value, fcfe, wacc, growth_rate_fcfe, growth_rate_tv
    
    def calculate_per_share(self, period: str = "annual") -> float:
        """주당가치 계산"""
        total_value, fcfe, wacc, growth_rate_fcfe, growth_rate_tv = self.calculate_total_value(period)
        per_share = total_value / self.shares_outstanding
        print(f"Per Share: {per_share}")
        return per_share, fcfe, wacc, growth_rate_fcfe, growth_rate_tv
import OpenDartReader
import pandas as pd
from segment_sales_crawling.financial_report_analyzer_soomin import ReportFilter
import re
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class QuarterlyFinancialData:
    """
    최근 1년간 분기별 재무제표 데이터를 추출하는 클래스

    Args:
        ticker (str): 종목 코드
        api_key (str): DART API 키
    """
    def __init__(self, ticker:str, api_key:str):
        self.dart = OpenDartReader(api_key)
        today = datetime.today()
        one_half_year_ago = (today - relativedelta(months=18)).strftime('%Y-%m-%d')
        self.start_date = one_half_year_ago
        self.end_date = date.today().strftime('%Y-%m-%d')
        self.ticker = ticker
        # latest_month 에 따라 이전 년도 및 현재 년도의 추출할 보고서 결정
        self.report_code_dict = {
            3: [11013,11012,11014,11011,11013], # 3월일 경우 : 1분기, 반기, 3분기, 사업, 1분기
            6: [11012,11014,11011,11013,11012], # 6월일 경우 : 반기, 3분기, 사업, 1분기, 반기
            9: [11014,11011,11013,11012,11014], # 9월일 경우 : 3분기, 사업, 1분기, 반기, 3분기
            12: [11011,11013,11012,11014,11011], # 12월일 경우 : 사업, 1분기, 반기, 3분기, 사업
            }
    
    def _get_financial_reports_list(self) -> None:
        """DART API를 통해 주기적 재무제표 데이터를 가져옵니다."""
        self.df = self.dart.list(self.ticker, start=self.start_date, end=self.end_date, kind='A')
        return None
    
    def _filter_financial_reports(self) -> None:
        """재무제표 데이터에서 1년치 보고서만 가져옵니다."""
        sorted_df = self.df.sort_values('rcept_dt', ascending=True)
        self.filtered_df = ReportFilter.filter_annual_reports(sorted_df)
        return None
    
    def _get_oldest_and_latest_time(self) -> None:
        """재무제표 데이터에서 가장 오래된 보고서와 가장 최신 보고서의 시간을 가져옵니다."""
        oldest_report = self.filtered_df.iloc[0]['report_nm']
        self.oldest_year = int(re.search(r'\((\d{4})', oldest_report).group(1))
        latest_report = self.filtered_df.iloc[-1]['report_nm']
        self.latest_year = int(re.search(r'\((\d{4})', latest_report).group(1))
        self.latest_month = int(re.search(r'\.(\d{2})', latest_report).group(1))
        return None
    
    def _str_to_int(self, value):
        """콤마가 들어간 숫자는 문자열로 인식. 콤마를 제거하여 정수로 변환합니다."""
        if isinstance(value, str):
            return int(value.replace(',', ''))
        return value
    
    def _get_financial_data(self, df:pd.DataFrame, report_type:str) -> list[int]:
        """재무제표에서 매출액, 영업이익, 당기순이익을 추출하는 함수"""
        amount_column = 'thstrm_amount' if report_type == '11011' else 'thstrm_add_amount' # 11011(사업보고서의 경우에만 누적 매출, 영업이익, 당기순이익 컬럼명이 다름)
        
        def _get_value(account_name: str) -> int:
            try:
                filtered_df = df.loc[(df['account_nm'] == account_name) & 
                                   (df['fs_nm'] == '연결재무제표')]
                if len(filtered_df) > 0:
                    return self._str_to_int(filtered_df[amount_column].iloc[0])
                else:
                    # 연결재무제표가 없는 경우 일반 재무제표 확인
                    filtered_df = df.loc[df['account_nm'] == account_name]
                    if len(filtered_df) > 0:
                        return self._str_to_int(filtered_df[amount_column].iloc[0])
                    return 0  # 데이터가 없는 경우 0 반환
            except Exception as e:
                print(f"Error processing {account_name}: {str(e)}")
                return 0
        
        return [
            _get_value('매출액'),
            _get_value('영업이익'),
            _get_value('당기순이익')
        ]
    
    def _extract_quarterly_financial_data(self) -> None:
        """이전 년도 분기의 매출, 영업이익, 당기순이익을 추출합니다."""
        n = 5-self.latest_month//3 
        # 9월 = 3분기 -> 5-3 = 2 -> 3분기,4분기 = 이전 년도 2개 분기값 필요
        # 6월 = 2분기 -> 5-2 = 3 -> 2분기,3분기,4분기 = 이전 년도 3개 분기값 필요
        # 3월 = 1분기 -> 5-1 = 4 -> 1분기,2분기,3분기,4분기 = 이전 년도 4개 분기값 필요
        # 12월 = 4분기 -> 5-4 = 1 -> 4분기 = 이전 년도 1개 분기값 필요

        self.save_values_dict = {}

        # 이전 년도 분기의 매출, 영업이익, 당기순이익 추출
        for i in self.report_code_dict[self.latest_month][:n]:
            df = self.dart.finstate(self.ticker, self.oldest_year, reprt_code=str(i))
            financial_data = self._get_financial_data(df, str(i))
            self.save_values_dict[f"{self.oldest_year}-{i}"] = financial_data

        # 현재 년도 분기의 매출, 영업이익, 당기순이익 추출
        for i in self.report_code_dict[self.latest_month][n:5]:
            df = self.dart.finstate(self.ticker, self.latest_year, reprt_code=str(i))
            financial_data = self._get_financial_data(df, str(i))
            self.save_values_dict[f"{self.latest_year}-{i}"] = financial_data

        return None
    
    def make_quarterly_financial_data_df(self) -> pd.DataFrame:
        self._get_financial_reports_list()
        self._filter_financial_reports()
        self._get_oldest_and_latest_time()
        self._extract_quarterly_financial_data()
        df = pd.DataFrame(self.save_values_dict).T.transpose()
        new_column_name = "계정"
        df.insert(0, new_column_name, ['영업수익', '영업이익', '순이익'])
        quarter_mapping = {
            '11014': '3Q',
            '11011': '4Q',
            '11013': '1Q',
            '11012': '2Q'
        }

        # 컬럼명 변경
        for col in df.columns[1:]:  # '계정' 컬럼을 제외한 나머지 컬럼들에 대해
            year = col.split('-')[0]
            quarter_code = col.split('-')[1]
            new_col = f"{year}-{quarter_mapping[quarter_code]}"
            df = df.rename(columns={col: new_col})

        return df
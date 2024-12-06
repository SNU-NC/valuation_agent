import yfinance as yf

class InfoDataCollector:
    """info 데이터를 수집하는 클래스"""
    
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.stock = yf.Ticker(ticker_symbol)
    
    def get_info(self) -> dict:
        """info 데이터를 가져오는 메서드
        
        returns:
            dict: info 딕셔너리
        """

        info = self.stock.info
        info_metrics = self._get_info_metrics(info)
            
        return info_metrics
    
    def _get_info_metrics(self, info: dict) -> dict:
        """재무상태표 관련 지표 추출"""
        metrics = {}
        
        try:
            metrics['payout_ratio'] = info['payoutRatio']
        except KeyError:
            print("payoutRatio 데이터를 찾을 수 없습니다.")

        try:
            metrics['regularMarketPreviousClose'] = info['regularMarketPreviousClose']
        except KeyError:
            print("regularMarketPreviousClose 데이터를 찾을 수 없습니다.")

        try:
            metrics['shares_outstanding'] = info['sharesOutstanding']
        except KeyError:
            print("sharesOutstanding 데이터를 찾을 수 없습니다.")
        
        return metrics
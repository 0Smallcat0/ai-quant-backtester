import pytest
import re

def categorize_tickers(watchlist):
    categories = {
        'TW': [],
        'US': [],
        'Crypto': [],
        'Other': []
    }
    
    for ticker in watchlist:
        # TW: 4 digits at start or ends with .TW
        if (ticker[:4].isdigit() and len(ticker) >= 4) or ticker.endswith('.TW'):
            categories['TW'].append(ticker)
        # Crypto: Contains -USD
        elif '-USD' in ticker:
            categories['Crypto'].append(ticker)
        # US: All uppercase, no - or . (basic check, can be refined)
        elif ticker.isupper() and '-' not in ticker and '.' not in ticker:
            categories['US'].append(ticker)
        else:
            categories['Other'].append(ticker)
            
    # Sorting
    # TW: Numeric sort
    def tw_sort_key(t):
        # Extract first number found
        match = re.match(r"(\d+)", t)
        if match:
            return int(match.group(1))
        return float('inf') # Put non-numeric at end
        
    categories['TW'].sort(key=tw_sort_key)
    categories['US'].sort()
    categories['Crypto'].sort()
    categories['Other'].sort()
    
    return categories

def test_categorization_logic():
    watchlist = [
        'AAPL', '2330', 'BTC-USD', 'TSLA', '2317.TW', 'ETH-USD', '1101', 'UNKNOWN-TICKER', '0050.TW'
    ]
    
    cats = categorize_tickers(watchlist)
    
    assert cats['TW'] == ['0050.TW', '1101', '2317.TW', '2330']
    assert cats['US'] == ['AAPL', 'TSLA']
    assert cats['Crypto'] == ['BTC-USD', 'ETH-USD']
    assert cats['Other'] == ['UNKNOWN-TICKER']

def test_tw_sorting():
    watchlist = ['2330', '1101', '0050', '9999']
    cats = categorize_tickers(watchlist)
    assert cats['TW'] == ['0050', '1101', '2330', '9999']

def test_mixed_tw_formats():
    watchlist = ['2330.TW', '2330', '1101.TW']
    cats = categorize_tickers(watchlist)
    # Note: 2330 and 2330.TW are treated as different strings but sort by number. 
    # Stable sort might keep relative order if numbers are same, but here we just check numeric order.
    # 1101 < 2330
    assert cats['TW'][0] == '1101.TW'

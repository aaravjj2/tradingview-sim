
import yfinance as yf

def test_yf():
    print("Fetching SPY...")
    spy = yf.Ticker("SPY")
    print(f"Price: {spy.info.get('regularMarketPrice')}")
    
    print("Fetching Options Expirations...")
    exps = spy.options
    print(f"Expirations: {exps[:3] if exps else None}")
    
    if exps:
        print(f"Fetching Chain for {exps[0]}...")
        chain = spy.option_chain(exps[0])
        print(f"Calls: {len(chain.calls)}")
        print(f"Puts: {len(chain.puts)}")
        
        if not chain.calls.empty:
            print("First Call:")
            print(chain.calls.iloc[0])

if __name__ == "__main__":
    test_yf()

import pandas as pd
import numpy as np
from indicators import compute_indicators

# Load price data into a DataFrame 'df' with columns: 'Open', 'High', 'Low', 'Close', 'Volume', and optionally 'Strength'.
# Compute all indicators and derived fields.
df = compute_indicators(df)

# Risk level mapping for convenience
RISK_LEVELS = {"aggressive": 0, "moderate": 1, "conservative": 2}

def evaluate_buy_signals(strategy, risk_level):
    """
    Evaluate the buy signal (entry condition) for all bars for a given strategy and risk level.
    Returns a boolean Series where True indicates the strategy conditions are met on that bar.
    """
    # Determine index for risk level
    level_index = RISK_LEVELS.get(risk_level, risk_level)  # allow numeric index or name
    formula = strategy['buy_formula_levels'][level_index]
    # Prepare formula for vectorized evaluation:
    # Replace logical operators with bitwise operators for Pandas evaluation
    formula_eval = formula.replace(' and ', ' & ').replace(' or ', ' | ')
    # Replace indicator function calls with column names, and handle offset references
    formula_eval = formula_eval.replace('EMA(', 'EMA').replace('RSI(', 'RSI').replace('ATR(', 'ATR')
    formula_eval = formula_eval.replace('MFI(', 'MFI').replace('CCI(', 'CCI').replace('PSAR(', 'PSAR')
    # Remove '(0)' as current value, replace '( -1)' or similar with shifted column names
    formula_eval = formula_eval.replace('(0)', '')
    # For negative offsets
    formula_eval = formula_eval.replace('(-1)', '_prev').replace('(-2)', '_prev2').replace('(-5)', '_prev5')
    # For positive offsets, though not common in buy formulas
    formula_eval = formula_eval.replace('(1)', '_prev').replace('(2)', '_prev2').replace('(5)', '_prev5')
    # Provide shifted columns if needed (for simplicity, we handle a few typical offsets)
    if '_prev' in formula_eval:
        # create columns with suffix for previous values
        for col in ['Close','Open','High','Low','Volume','Strength','EMA5','EMA20','EMA60','EMA120',
                    'ATR14','RSI14','MFI14','CCI20','MACD_hist','BandWidth20']:
            if col in df and f'{col}_prev' in formula_eval:
                df[f'{col}_prev'] = df[col].shift(1)
            if col in df and f'{col}_prev2' in formula_eval:
                df[f'{col}_prev2'] = df[col].shift(2)
            if col in df and f'{col}_prev5' in formula_eval:
                df[f'{col}_prev5'] = df[col].shift(5)
    # Evaluate formula across DataFrame (engine='python' to allow complex expressions)
    signals = df.eval(formula_eval, engine='python')
    return signals.astype(bool)

def evaluate_sell_signal(strategy, risk_level, entry_price, peak_price, index):
    """
    Evaluate the sell signal at a specific bar (index) for a given strategy and risk level, using current trade context.
    entry_price: entry price of the open trade
    peak_price: highest price achieved since entry (for trailing stop)
    index: current bar index in df for evaluation
    Returns True if any sell condition triggers at this bar.
    """
    level_index = RISK_LEVELS.get(risk_level, risk_level)
    formula = strategy['sell_formula_levels'][level_index]
    # Prepare context for safe eval: include all indicator values at this index and trade variables
    context = {col: df.at[index, col] for col in df.columns if col not in ['Date','Time']}
    context.update({'Entry': entry_price, 'Peak': peak_price})
    # Adjust context keys for any indicator names with special characters
    # (We'll ensure our context keys match the formula exactly by similar replacements)
    # Replace indicator function calls in formula with names matching DataFrame columns
    formula_eval = formula.replace('EMA(', 'EMA').replace('RSI(', 'RSI').replace('ATR(', 'ATR')
    formula_eval = formula_eval.replace('MFI(', 'MFI').replace('CCI(', 'CCI').replace('PSAR(', 'PSAR')
    formula_eval = formula_eval.replace('+DI', 'DI_plus').replace('-DI', 'DI_minus')
    # Remove '(0)' and treat offsets if present
    formula_eval = formula_eval.replace('(0)', '')
    formula_eval = formula_eval.replace('(1)', '_prev').replace('(-1)', '_prev')
    formula_eval = formula_eval.replace('EntryPrice', 'Entry').replace('entry_price', 'Entry')
    # Evaluate the sell formula in a restricted environment
    result = eval(formula_eval, {"__builtins__": None}, context)
    return bool(result)

# Example usage scenario (backtesting loop):
# in_trade = False
# entry_price = 0
# peak_price = 0
# risk = 'aggressive'
# strategy = strategies_master[0]  # e.g., first strategy
# buy_signals = evaluate_buy_signals(strategy, risk)
# for i, signal in buy_signals.iteritems():
#     if not in_trade and signal:
#         # Enter trade
#         in_trade = True
#         entry_price = df.at[i, 'Close']
#         peak_price = entry_price
#     if in_trade:
#         # Update peak price for trailing stops
#         peak_price = max(peak_price, df.at[i, 'High'])
#         # Check sell conditions
#         if evaluate_sell_signal(strategy, risk, entry_price, peak_price, i):
#             # Exit trade
#             in_trade = False
#             entry_price = 0
#             peak_price = 0
# ```

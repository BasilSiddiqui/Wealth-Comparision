import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ------------------------------------------------------------
# Custom PMT function (replaces numpy_financial.pmt)
# ------------------------------------------------------------
def pmt(rate, nper, pv, fv=0, when='end'):
    """
    Calculate the periodic payment of a loan.
    
    Parameters:
    rate : float - interest rate per period
    nper : int - total number of payments
    pv : float - present value (loan amount)
    fv : float - future value (default 0)
    when : str - 'begin' or 'end' (default 'end')
    
    Returns:
    float - payment amount
    """
    if rate == 0:
        return -pv / nper
    
    if when == 'end':
        factor = (1 + rate) ** nper
        payment = (pv * rate * factor) / (factor - 1)
    else:
        factor = (1 + rate) ** nper
        payment = (pv * rate * factor) / ((factor - 1) * (1 + rate))
    
    # For a loan you pay, the sign is negative; we want positive EMI
    return -payment if pv > 0 else payment

# Better chart style and pandas formatting
plt.style.use("ggplot")
pd.options.display.float_format = '{:,.0f}'.format

def format_aed(x, pos):
    return f'{x/1_000_000:.1f}M'

def simulate_case1_stocks_only(monthly_stock_investment, annual_return, simulation_months):
    """
    Case 1: Stocks-only investment strategy.
    Invests a fixed monthly amount into stocks with no property involvement.
    """
    monthly_return = (1 + annual_return) ** (1/12) - 1
    stocks = 0
    results = []
    for month in range(1, simulation_months + 1):
        stocks = stocks * (1 + monthly_return) + monthly_stock_investment
        results.append({"Month": month, "Stocks": stocks, "NetWorth": stocks})
    return pd.DataFrame(results)

def simulate_case2_property_strategy(monthly_stock_investment_before_mortgage,
                                     monthly_property_saving,
                                     annual_return,
                                     property_price,
                                     down_payment_pct,
                                     mortgage_rate,
                                     mortgage_years,
                                     property_growth,
                                     simulation_months,
                                     post_mortgage_stock_investment=10000):
    """
    Case 2: Property + Stocks strategy.
    - Saves monthly for down payment while investing smaller amount in stocks.
    - After purchasing property, pays mortgage while investing regular amount.
    - After mortgage is paid off, invests a higher monthly amount (default 10,000 AED) into stocks.
    """
    monthly_stock_return = (1 + annual_return) ** (1/12) - 1
    monthly_property_growth = (1 + property_growth) ** (1/12) - 1

    down_payment = property_price * down_payment_pct
    loan_amount = property_price - down_payment

    emi = abs(pmt(mortgage_rate / 12, mortgage_years * 12, loan_amount))

    stocks = 0
    dp_savings = 0
    property_owned = False
    mortgage_balance = 0
    property_value = 0
    equity = 0
    results = []

    for month in range(1, simulation_months + 1):
        if not property_owned:
            # Phase 1: saving for down payment
            stocks = stocks * (1 + monthly_stock_return) + monthly_stock_investment_before_mortgage
            dp_savings += monthly_property_saving
            if dp_savings >= down_payment:
                property_owned = True
                mortgage_balance = loan_amount
                property_value = property_price
                equity = property_value - mortgage_balance
                dp_savings = 0
        else:
            # Phase 2: property owned
            property_value *= (1 + monthly_property_growth)
            interest = mortgage_balance * (mortgage_rate / 12)
            principal_paid = min(emi - interest, mortgage_balance)
            mortgage_balance -= principal_paid
            mortgage_balance = max(0, mortgage_balance)

            if mortgage_balance > 0:
                monthly_investment = monthly_stock_investment_before_mortgage
            else:
                monthly_investment = post_mortgage_stock_investment

            stocks = stocks * (1 + monthly_stock_return) + monthly_investment
            equity = property_value - mortgage_balance

        net_worth = stocks + dp_savings + equity
        results.append({
            "Month": month,
            "Stocks": stocks,
            "DownPaymentSavings": dp_savings,
            "PropertyValue": property_value,
            "MortgageBalance": mortgage_balance,
            "Equity": equity,
            "NetWorth": net_worth
        })
    return pd.DataFrame(results)

# ========================
# INPUTS
# ========================
# Common parameters
SIMULATION_MONTHS = 360      # 30 years
ANNUAL_STOCK_RETURN_CASE1 = 0.13      # Case 1 (stocks only) return
ANNUAL_STOCK_RETURN_CASE2 = 0.10      # Case 2 (property strategy) stock return

# Case 1 parameters
CASE1_MONTHLY_INVESTMENT = 5000

# Case 2 parameters
CASE2_MONTHLY_STOCK_INVESTMENT_BEFORE_MORTGAGE = 5000
CASE2_MONTHLY_PROPERTY_SAVING = 5000
PROPERTY_PRICE = 500000
DOWN_PAYMENT_PCT = 0.20
MORTGAGE_RATE = 0.04
MORTGAGE_YEARS = 10
PROPERTY_GROWTH = 0.04
POST_MORTGAGE_STOCK_INVESTMENT = 10000

# ========================
# RUN SIMULATIONS
# ========================
case1_df = simulate_case1_stocks_only(
    monthly_stock_investment=CASE1_MONTHLY_INVESTMENT,
    annual_return=ANNUAL_STOCK_RETURN_CASE1,
    simulation_months=SIMULATION_MONTHS
)

case2_df = simulate_case2_property_strategy(
    monthly_stock_investment_before_mortgage=CASE2_MONTHLY_STOCK_INVESTMENT_BEFORE_MORTGAGE,
    monthly_property_saving=CASE2_MONTHLY_PROPERTY_SAVING,
    annual_return=ANNUAL_STOCK_RETURN_CASE2,
    property_price=PROPERTY_PRICE,
    down_payment_pct=DOWN_PAYMENT_PCT,
    mortgage_rate=MORTGAGE_RATE,
    mortgage_years=MORTGAGE_YEARS,
    property_growth=PROPERTY_GROWTH,
    simulation_months=SIMULATION_MONTHS,
    post_mortgage_stock_investment=POST_MORTGAGE_STOCK_INVESTMENT
)

# ========================
# MASTER DATAFRAME
# ========================
master_df = (
    case1_df
    .merge(case2_df, on="Month", suffixes=("_Case1", "_Case2"))
)
master_df["Difference_Case2_minus_Case1"] = master_df["NetWorth_Case2"] - master_df["NetWorth_Case1"]

# ========================
# SNAPSHOTS
# ========================
df_10y = master_df[master_df["Month"] <= 120]
df_20y = master_df[master_df["Month"] <= 240]
df_30y = master_df[master_df["Month"] <= 360]

# ========================
# COMPARISON DATAFRAME (for plotting)
# ========================
comparison = pd.DataFrame({
    "Month": case1_df["Month"],
    "Case1_StocksOnly": case1_df["NetWorth"],
    "Case2_PropertyStrategy": case2_df["NetWorth"]
})
comparison["Difference"] = comparison["Case2_PropertyStrategy"] - comparison["Case1_StocksOnly"]

# ========================
# SUMMARY TABLE
# ========================
summary_df = pd.DataFrame({
    "Metric": ["10 Years", "20 Years", "30 Years"],
    "Case1_StocksOnly": [
        comparison.loc[119, "Case1_StocksOnly"] if 119 < len(comparison) else np.nan,
        comparison.loc[239, "Case1_StocksOnly"] if 239 < len(comparison) else np.nan,
        comparison.loc[359, "Case1_StocksOnly"] if 359 < len(comparison) else np.nan
    ],
    "Case2_PropertyStrategy": [
        comparison.loc[119, "Case2_PropertyStrategy"] if 119 < len(comparison) else np.nan,
        comparison.loc[239, "Case2_PropertyStrategy"] if 239 < len(comparison) else np.nan,
        comparison.loc[359, "Case2_PropertyStrategy"] if 359 < len(comparison) else np.nan
    ]
})
summary_df["Winner"] = np.where(
    summary_df["Case2_PropertyStrategy"] > summary_df["Case1_StocksOnly"],
    "Case 2 (Property)",
    "Case 1 (Stocks Only)"
)

# ========================
# FIND CROSSOVER & PRINT FINALS
# ========================
crossover = comparison[comparison["Difference"] > 0]
if len(crossover) > 0:
    crossover_month = crossover.iloc[0]["Month"]
    print(f"Case 2 (Property Strategy) overtakes Case 1 (Stocks Only) in month {int(crossover_month)}")
else:
    crossover_month = None
    print("Case 1 (Stocks Only) remains ahead for the entire simulation period")

print("\nFINAL RESULTS (30 Years)")
print("-" * 50)
print(f"Case 1 (Stocks Only) Net Worth:          {case1_df['NetWorth'].iloc[-1]:,.0f} AED")
print(f"Case 2 (Property Strategy) Net Worth:   {case2_df['NetWorth'].iloc[-1]:,.0f} AED")
print("\nSummary Table:")
print(summary_df.to_string(index=False))

# ========================
# ENHANCED PLOT FUNCTION
# ========================
def plot_comparison(month_limit, comparison):
    data = comparison[comparison["Month"] <= month_limit].copy()
    if data.empty:
        print(f"No data for {month_limit} months")
        return

    plt.figure(figsize=(16, 8))
    
    # Case 1: Blue
    plt.plot(data["Month"], data["Case1_StocksOnly"], linewidth=4, color='steelblue',
             label="Case 1: Stocks Only (13% return, 5k/month)")
    
    # Case 2: Orange
    plt.plot(data["Month"], data["Case2_PropertyStrategy"], linewidth=4, color='darkorange',
             label="Case 2: Property + Stocks (10k/month after mortgage)")

    # Crossover and fill (no legend labels)
    crossover = data[data["Difference"] > 0]
    if len(crossover) > 0:
        cross_month = crossover.iloc[0]["Month"]
        if cross_month > 1:
            plt.axvline(cross_month, linestyle="--", linewidth=2, alpha=0.7, color='gray',
                        label='_nolegend_')
        plt.fill_between(data["Month"], data["Case1_StocksOnly"], data["Case2_PropertyStrategy"],
                         where=(data["Case2_PropertyStrategy"] > data["Case1_StocksOnly"]),
                         alpha=0.15, color='darkorange', label='_nolegend_')

    # Max advantage point - red dot with legend entry (no annotation)
    max_diff_row = data.loc[data["Difference"].idxmax()]
    plt.scatter(max_diff_row["Month"], max_diff_row["Case2_PropertyStrategy"],
                s=120, color='red', zorder=5, label='Maximum Advantage Point')

    # Titles and labels
    plt.title(f"Wealth Accumulation Comparison ({month_limit//12} Years)",
              fontsize=18, weight="bold")
    plt.xlabel("Years", fontsize=12, weight="bold")
    plt.ylabel("Net Worth (AED)", fontsize=12, weight="bold")
    
    # Set x-axis limits from 0 to month_limit
    plt.xlim(0, month_limit)
    
    # Set ticks every 12 months and label them as years
    ticks = np.arange(0, month_limit + 1, 12)
    year_labels = [f"{int(tick/12)}" for tick in ticks]
    plt.xticks(ticks, year_labels, fontsize=10, weight='bold')
    
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_aed))
    plt.grid(True, alpha=0.3)
    leg = plt.legend(fontsize=18, loc='best')
    plt.setp(leg.get_texts(), color='dimgray')
    plt.tight_layout()
    plt.show()

# ========================
# GENERATE PLOTS
# ========================
plot_comparison(120, comparison)   # 10 years
plot_comparison(240, comparison)   # 20 years
plot_comparison(360, comparison)   # 30 years

# ========================
# ADVANTAGE PLOT
# ========================
plt.figure(figsize=(14, 6))
plt.plot(comparison["Month"], comparison["Difference"], linewidth=3, color='darkgreen')

plt.axhline(0, linestyle="--", color='black', alpha=0.7)

plt.fill_between(comparison["Month"], 0, comparison["Difference"], 
                 where=(comparison["Difference"] > 0), alpha=0.2, color='green', 
                 label='Case 2 Advantage')
plt.fill_between(comparison["Month"], 0, comparison["Difference"], 
                 where=(comparison["Difference"] < 0), alpha=0.2, color='red', 
                 label='Case 1 Advantage')

# --- RED DOT: Maximum Advantage Point ---
max_diff_idx = comparison["Difference"].idxmax()
max_diff_row = comparison.loc[max_diff_idx]
plt.scatter(max_diff_row["Month"], max_diff_row["Difference"], 
            s=120, color='red', zorder=5, label='Maximum Advantage Point')
# -----------------------------------------

plt.title("Performance Advantage: Case 2 (Property + Stocks) minus Case 1 (Stocks Only)", 
          fontsize=16, weight="bold")
plt.xlabel("Years", fontsize=12, weight="bold")
plt.ylabel("Difference in Net Worth (AED)", fontsize=12, weight="bold")

# Format y-axis in millions
plt.gca().yaxis.set_major_formatter(FuncFormatter(format_aed))

# Set x-axis limits from 0 to max month
max_month = comparison["Month"].max()
plt.xlim(0, max_month)

# Set ticks every 12 months and label as years
ticks = np.arange(0, max_month + 1, 12)
year_labels = [f"{int(tick/12)}" for tick in ticks]
plt.xticks(ticks, year_labels, fontsize=10, weight='bold')

plt.grid(alpha=0.3)
leg = plt.legend(fontsize=14 ,loc='lower left')
plt.setp(leg.get_texts(), color='dimgray')
plt.tight_layout()
plt.show()
# qa_utils.py
# This module contains utility functions for performing quality assurance checks on financial data.
# It includes functions to check the balance equation, income statement consistency, and cash flow integrity.

def check_balance_equation(values):
    try:
        assets = float(values.get("Total Assets", 0))
        liab = float(values.get("Total Liabilities", 0))
        equity = float(values.get("Equity", 0))
        return abs(assets - (liab + equity)) < 1e-2
    except Exception:
        return False

def check_income_consistency(values):
    try:
        revenue = float(values.get("Revenue", 0))
        net_income = float(values.get("Net Income", 0))
        return revenue >= net_income  # simplification
    except Exception:
        return False

def check_cash_flow(values):
    try:
        operating = float(values.get("Operating Cash Flow", 0))
        investing = float(values.get("Investing Cash Flow", 0))
        financing = float(values.get("Financing Cash Flow", 0))
        ending_cash = float(values.get("Cash and Cash Equivalents", 0))

        total_flow = operating + investing + financing

        # Allowable soft check: ending cash is in range [0.5x, 1.5x] of total cash flow
        lower_bound = total_flow * 0.5
        upper_bound = total_flow * 1.5

        return lower_bound <= ending_cash <= upper_bound
    except Exception:
        return False

def run_all_qa_checks(values, mapping_table):
    results = {}

    # QA name to function
    qa_groups = {
        "Balance Equation": check_balance_equation,
        "Income Statement": check_income_consistency,
        "Cash Flow": check_cash_flow
    }

    # YAML 中的 QA Group → 映射到上面的 QA 项
    yaml_to_qa = {
        "BalanceSheet": "Balance Equation",
        "IncomeStatement": "Income Statement",
        "CashFlowStatement": "Cash Flow"
    }

    # 从 mapping 表中收集实际存在的 QA 项
    mapped_groups = set()
    for group in mapping_table["QA Group"].dropna().unique():
        if group in yaml_to_qa:
            mapped_groups.add(yaml_to_qa[group])

    # 运行 QA
    for group, func in qa_groups.items():
        if group in mapped_groups:
            results[group] = func(values)

    return results
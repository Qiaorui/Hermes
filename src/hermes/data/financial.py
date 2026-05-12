"""Multi-period financial statement data."""

from hermes.api.eastmoney import em_get

_INCOME_FIELDS = [
    "REPORT_DATE", "TOTAL_OPERATE_INCOME", "OPERATE_INCOME", "PARENT_NETPROFIT",
    "DEDUCT_PARENT_NETPROFIT", "SALE_EXPENSE", "MANAGE_EXPENSE", "FINANCE_EXPENSE",
    "RESEARCH_EXPENSE", "OPERATE_PROFIT", "TOI_RATIO", "PARENT_NETPROFIT_RATIO",
    "DPN_RATIO", "OPERATE_PROFIT_RATIO",
]
_INCOME_YUAN = set(_INCOME_FIELDS) - {"REPORT_DATE", "TOI_RATIO", "PARENT_NETPROFIT_RATIO", "DPN_RATIO", "OPERATE_PROFIT_RATIO"}

_BALANCE_FIELDS = [
    "REPORT_DATE", "TOTAL_ASSETS", "TOTAL_LIABILITIES", "TOTAL_EQUITY",
    "MONETARYFUNDS", "ACCOUNTS_RECE", "INVENTORY", "PARENT_EQUITY",
    "DEBT_ASSET_RATIO", "CURRENT_RATIO",
]
_BALANCE_YUAN = set(_BALANCE_FIELDS) - {"REPORT_DATE", "DEBT_ASSET_RATIO", "CURRENT_RATIO"}

_CASHFLOW_FIELDS = [
    "REPORT_DATE", "NETCASH_OPERATE", "NETCASH_INVEST", "NETCASH_FINANCE",
    "CCE_ADD", "NETCASH_OPERATE_RATIO",
]
_CASHFLOW_YUAN = set(_CASHFLOW_FIELDS) - {"REPORT_DATE", "NETCASH_OPERATE_RATIO"}

_REPORT_MAP = {
    "income": ("RPT_DMSK_FN_INCOME", _INCOME_FIELDS, _INCOME_YUAN),
    "balance": ("RPT_DMSK_FN_BALANCE", _BALANCE_FIELDS, _BALANCE_YUAN),
    "cashflow": ("RPT_DMSK_FN_CASHFLOW", _CASHFLOW_FIELDS, _CASHFLOW_YUAN),
}


def stock_financial(code: str, report_type: str = "income", count: int = 4) -> dict:
    """Get multi-period financial statement data. Returns dict with periods."""
    count = min(count, 8)
    if report_type not in _REPORT_MAP:
        return {"error": f"Invalid report_type: {report_type}. Use 'income', 'balance', or 'cashflow'", "code": code}

    report_name, fields, yuan_fields = _REPORT_MAP[report_type]
    url = f"http://datacenter-web.eastmoney.com/api/data/v1/get?reportName={report_name}&columns=ALL&filter=(SECURITY_CODE=\"{code.strip()}\")&pageSize={count}&sortColumns=REPORT_DATE&sortTypes=-1&source=WEB&client=WEB"
    data = em_get(url)
    if not data or not data.get("result") or not data["result"].get("data"):
        return {"error": "Failed to get financial data", "code": code, "report_type": report_type}

    periods = []
    for row in data["result"]["data"]:
        entry = {}
        for f in fields:
            v = row.get(f)
            if v is None:
                entry[f] = None
            elif f in yuan_fields:
                entry[f] = round(v / 1e8, 2)
            elif f == "REPORT_DATE":
                entry[f] = str(v)[:10] if v else ""
            else:
                entry[f] = v
        periods.append(entry)

    return {"code": code, "report_type": report_type, "count": len(periods), "periods": periods}
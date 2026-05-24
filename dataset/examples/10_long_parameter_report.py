"""Bad smell: Long Parameter List - esperado: Builder/Parameter Object."""


def build_sales_report(
    title: str,
    start_date: str,
    end_date: str,
    region: str,
    sales_channel: str,
    currency: str,
    include_returns: bool,
    include_taxes: bool,
    group_by: str,
    sort_by: str,
    max_rows: int,
    requested_by: str,
) -> dict:
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "region": region,
        "sales_channel": sales_channel,
        "include_returns": include_returns,
        "include_taxes": include_taxes,
    }
    layout = {
        "group_by": group_by,
        "sort_by": sort_by,
        "max_rows": max_rows,
        "currency": currency,
    }
    return {
        "title": title,
        "filters": filters,
        "layout": layout,
        "requested_by": requested_by,
        "status": "scheduled",
    }

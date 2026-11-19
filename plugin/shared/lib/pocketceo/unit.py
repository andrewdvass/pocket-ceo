"""Unit economics for the consultant: margin, break-even, customer acquisition and payback."""
import math
from . import r2


def unit_economics(price, cost_to_deliver, fixed_costs_month, sales_per_month=None, marketing_month=None,
                   new_customers_month=None, months_retained=1.0, purchases_per_month=1.0, owner_pay_month=0.0):
    margin = price - cost_to_deliver
    margin_pct = margin / price if price else 0.0
    monthly_margin_per_customer = margin * purchases_per_month
    out = {"price": r2(price), "cost_to_deliver": r2(cost_to_deliver), "gross_margin": r2(margin),
           "gross_margin_pct": round(margin_pct * 100, 1), "fixed_costs_month": r2(fixed_costs_month),
           "owner_pay_month": r2(owner_pay_month)}
    need = fixed_costs_month + owner_pay_month
    if margin > 0:
        out["break_even_sales_per_month"] = math.ceil(need / margin)
        out["break_even_revenue_month"] = r2(out["break_even_sales_per_month"] * price)
    else:
        out["break_even_sales_per_month"] = None
        out["problem"] = "Each sale loses money before fixed costs. Fix the price or the cost to deliver first."
    if sales_per_month is not None:
        profit = sales_per_month * margin - fixed_costs_month - (marketing_month or 0)
        out["profit_month"] = r2(profit)
        out["profit_after_owner_pay_month"] = r2(profit - owner_pay_month)
        if margin > 0:
            out["each_extra_sale_adds"] = r2(margin)
            out["price_up_10pct_adds_month"] = r2(sales_per_month * price * 0.10)
    if marketing_month and new_customers_month:
        cac = marketing_month / new_customers_month
        lifetime_margin = monthly_margin_per_customer * months_retained
        out.update({"cost_to_get_a_customer": r2(cac), "lifetime_gross_margin": r2(lifetime_margin),
                    "lifetime_value_to_cac": round(lifetime_margin / cac, 2) if cac else None,
                    "payback_months": round(cac / monthly_margin_per_customer, 1) if monthly_margin_per_customer > 0 else None})
        ratio = out["lifetime_value_to_cac"] or 0
        out["acquisition_verdict"] = ("Healthy: each customer is worth %.1fx what it costs to get them." % ratio if ratio >= 3 else
                                      "Thin: customers are worth only %.1fx what they cost to get. Raise the price, keep them longer, or cut ad waste." % ratio if ratio >= 1 else
                                      "Losing money on every new customer: they're worth %.1fx what they cost to get." % ratio)
    return out

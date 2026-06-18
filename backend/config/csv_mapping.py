"""
CSV column name → metric_key mappings for each platform.

Users export CSVs from seller centers with platform-specific column names.
This module maps those to our internal metric keys.

Each entry: (csv_column_name, metric_key)
The matcher is case-insensitive and strips whitespace.
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════
#  AMAZON — Seller Central export column names
# ═══════════════════════════════════════════════════════════════

AMAZON_MAPPING = [
    # (CSV column name pattern, metric_key)
    ("ordered product sales",        "gmv"),
    ("ordered_product_sales",        "gmv"),
    ("product sales",                "gmv"),
    ("units ordered",                "orders"),
    ("units_ordered",                "orders"),
    ("total order items",            "orders"),
    ("total_order_items",            "orders"),
    ("average selling price",        "avg_order_value"),
    ("average_selling_price",        "avg_order_value"),
    ("average sales per order item", "avg_order_value"),
    ("refund rate",                  "refund_rate"),
    ("refund_rate",                  "refund_rate"),
    ("sessions",                     "sessions"),
    ("browser sessions",             "sessions"),
    ("browser_sessions",             "sessions"),
    ("unit session percentage",      "conversion_rate"),
    ("unit_session_percentage",      "conversion_rate"),
    ("buy box percentage",           "buy_box_pct"),
    ("buy_box_percentage",           "buy_box_pct"),
    ("spend",                        "ad_spend"),
    ("ad spend",                     "ad_spend"),
    ("ad_spend",                     "ad_spend"),
    ("advertising spend",            "ad_spend"),
    ("sales",                        "ad_sales"),
    ("ad sales",                     "ad_sales"),
    ("ad_sales",                     "ad_sales"),
    ("acos",                         "acos"),
    ("roas",                         "roas"),
    ("cogs",                         "cogs"),
    ("cost of goods sold",           "cogs"),
    ("cost_of_goods_sold",           "cogs"),
    ("fba fees",                     "fba_fees"),
    ("fba_fees",                     "fba_fees"),
    ("fulfillable quantity",         "fulfillable_qty"),
    ("fulfillable_quantity",         "fulfillable_qty"),
    ("inbound quantity",             "inbound_qty"),
    ("inbound_quantity",             "inbound_qty"),
    ("net profit",                   "net_profit"),
    ("net_profit",                   "net_profit"),
    ("refund amount",                "refund_amount"),
    ("refund_amount",                "refund_amount"),
    ("daily sales",                  "daily_sales"),
    ("daily_sales",                  "daily_sales"),
    ("referral fee",                 "referral_fee"),
    ("referral_fee",                 "referral_fee"),
    ("inventory days",               "inventory_days"),
    ("inventory_days",               "inventory_days"),
]

# ═══════════════════════════════════════════════════════════════
#  TIKTOK SHOP — Seller Center export column names
# ═══════════════════════════════════════════════════════════════

TIKTOK_MAPPING = [
    ("gmv",                         "gmv"),
    ("order amount",                "gmv"),
    ("order_amount",                "gmv"),
    ("orders",                      "orders"),
    ("order count",                 "orders"),
    ("order_count",                 "orders"),
    ("video views",                 "video_views"),
    ("video_views",                 "video_views"),
    ("live views",                  "live_views"),
    ("live_views",                  "live_views"),
    ("content gmv",                 "content_gmv"),
    ("content_gmv",                 "content_gmv"),
    ("shop gmv",                    "shop_gmv"),
    ("shop_gmv",                    "shop_gmv"),
    ("affiliate gmv",               "affiliate_gmv"),
    ("affiliate_gmv",               "affiliate_gmv"),
    ("affiliate orders",            "affiliate_orders"),
    ("affiliate_orders",            "affiliate_orders"),
    ("tt ads spend",                "tt_ads_spend"),
    ("tt_ads_spend",                "tt_ads_spend"),
    ("ads spend",                   "tt_ads_spend"),
    ("ads_spend",                   "tt_ads_spend"),
    ("tt ads roas",                 "tt_ads_roas"),
    ("tt_ads_roas",                 "tt_ads_roas"),
    ("tt ads ctr",                  "tt_ads_ctr"),
    ("tt_ads_ctr",                  "tt_ads_ctr"),
    ("shop score",                  "shop_score"),
    ("shop_score",                  "shop_score"),
    ("penalty points",              "penalty_points"),
    ("penalty_points",              "penalty_points"),
    ("avg shipping time",           "avg_shipping_time"),
    ("avg_shipping_time",           "avg_shipping_time"),
    ("average shipping time",       "avg_shipping_time"),
    ("return rate",                 "return_rate"),
    ("return_rate",                 "return_rate"),
    ("refund rate",                 "refund_rate"),
    ("refund_rate",                 "refund_rate"),
    ("net profit",                  "net_profit"),
    ("net_profit",                  "net_profit"),
    ("cogs",                        "cogs"),
    ("cost of goods",               "cogs"),
]

# ═══════════════════════════════════════════════════════════════
#  SHOPEE — Seller Center export column names
# ═══════════════════════════════════════════════════════════════

SHOPEE_MAPPING = [
    ("order amount",                "gmv"),
    ("order_amount",                "gmv"),
    ("gmv",                         "gmv"),
    ("orders",                      "orders"),
    ("order count",                 "orders"),
    ("order_count",                 "orders"),
    ("cod orders",                  "cod_orders"),
    ("cod_orders",                  "cod_orders"),
    ("cod rate",                    "cod_rate"),
    ("cod_rate",                    "cod_rate"),
    ("chat response rate",          "chat_response_rate"),
    ("chat_response_rate",          "chat_response_rate"),
    ("chat response time",          "chat_response_time"),
    ("chat_response_time",          "chat_response_time"),
    ("shop rating",                 "shop_rating"),
    ("shop_rating",                 "shop_rating"),
    ("nfr rate",                    "nfr_rate"),
    ("nfr_rate",                    "nfr_rate"),
    ("non fulfillment rate",        "nfr_rate"),
    ("non_fulfillment_rate",        "nfr_rate"),
    ("cancel rate",                 "cancel_rate"),
    ("cancel_rate",                 "cancel_rate"),
    ("late shipment rate",          "late_shipment_rate"),
    ("late_shipment_rate",          "late_shipment_rate"),
    ("shopee ads spend",            "shopee_ads_spend"),
    ("shopee_ads_spend",            "shopee_ads_spend"),
    ("ads spend",                   "shopee_ads_spend"),
    ("ads_spend",                   "shopee_ads_spend"),
    ("shopee ads roas",             "shopee_ads_roas"),
    ("shopee_ads_roas",             "shopee_ads_roas"),
    ("flash sale gmv",              "flash_sale_gmv"),
    ("flash_sale_gmv",              "flash_sale_gmv"),
    ("voucher usage rate",          "voucher_usage_rate"),
    ("voucher_usage_rate",          "voucher_usage_rate"),
    ("logistics cost",              "logistics_cost"),
    ("logistics_cost",              "logistics_cost"),
    ("first attempt delivery rate", "first_attempt_delivery_rate"),
    ("first_attempt_delivery_rate", "first_attempt_delivery_rate"),
    ("net profit",                  "net_profit"),
    ("net_profit",                  "net_profit"),
    ("return rate",                 "return_rate"),
    ("return_rate",                 "return_rate"),
    ("refund rate",                 "refund_rate"),
    ("refund_rate",                 "refund_rate"),
]

# ═══════════════════════════════════════════════════════════════
#  PER-PLATFORM MAP INDEX
# ═══════════════════════════════════════════════════════════════

PLATFORM_MAPPINGS = {
    "amazon": AMAZON_MAPPING,
    "tiktok": TIKTOK_MAPPING,
    "shopee": SHOPEE_MAPPING,
}


# ═══════════════════════════════════════════════════════════════
#  MATCHER
# ═══════════════════════════════════════════════════════════════

def _normalize(s: str) -> str:
    """Normalize a CSV column name for matching: lowercase, strip, collapse whitespace."""
    return re.sub(r'\s+', ' ', s.strip().lower().replace('_', ' '))


def match_columns(csv_columns: list[str], platform_code: str) -> dict[str, str]:
    """
    Match CSV column names to metric_keys.

    Args:
        csv_columns: Raw column names from the CSV header
        platform_code: 'amazon' | 'tiktok' | 'shopee'

    Returns:
        Dict mapping {csv_column_name: metric_key} for matched columns.
        Unmatched columns are excluded.
    """
    mapping_rules = PLATFORM_MAPPINGS.get(platform_code, AMAZON_MAPPING)

    # Pre-normalize mapping rules
    norm_rules = [(_normalize(pat), key) for pat, key in mapping_rules]

    result: dict[str, str] = {}
    for col in csv_columns:
        nc = _normalize(col)
        matched = False
        for pat, key in norm_rules:
            if nc == pat:
                result[col] = key
                matched = True
                break
        # Also try partial match if exact match fails
        if not matched:
            for pat, key in norm_rules:
                if pat in nc or nc in pat:
                    result[col] = key
                    break

    return result


def get_mapping_for_platform(platform_code: str) -> dict[str, str]:
    """
    Get a human-readable label for each mapped metric key.
    Returns {metric_key: display_label} using our internal metric names.
    """
    mapping_rules = PLATFORM_MAPPINGS.get(platform_code, AMAZON_MAPPING)
    # Collect unique metric keys
    seen = set()
    labels = {}
    for _, key in mapping_rules:
        if key not in seen:
            seen.add(key)
            labels[key] = key  # frontend will look up display name from metric list
    return labels

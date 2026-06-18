"""
Data Adapter Layer — Pluggable data sources for cross-border e-commerce platforms.

Architecture:
    BaseAdapter (abstract)
    ├── MockAdapter           ← Current default: generates simulated data
    ├── CsvUploadAdapter      ← Reads real store data from CSV files
    ├── AmazonSpApiAdapter    ← Reserved for Amazon Selling Partner API
    ├── TikTokShopApiAdapter  ← Reserved for TikTok Shop Partner API
    └── ShopeeOpenApiAdapter  ← Reserved for Shopee Open Platform API

To switch data source, set DATA_SOURCE in .env:
    DATA_SOURCE=mock       # Simulated data (default)
    DATA_SOURCE=csv        # CSV file import
    DATA_SOURCE=amazon_spapi
    DATA_SOURCE=tiktok
    DATA_SOURCE=shopee
"""
import os
import csv
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════════
#  BASE ADAPTER
# ═══════════════════════════════════════════════════════════════

class BaseAdapter(ABC):
    """
    Abstract base for all platform data adapters.

    Each adapter implements fetch_daily_data(platform_id, target_date)
    and returns a dict of {metric_key: value}.
    """

    @abstractmethod
    def fetch_daily_data(self, platform_id: int, target_date: date) -> dict[str, float]:
        """
        Fetch all metric values for a given platform and date.

        Returns:
            dict like {"gmv": 18450.0, "orders": 892, "acos": 28.5, ...}
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        ...


# ═══════════════════════════════════════════════════════════════
#  MOCK ADAPTER (default)
# ═══════════════════════════════════════════════════════════════

class MockAdapter(BaseAdapter):
    """
    Generates simulated data using the seed module's logic.

    This is the default adapter. No real API keys required.
    Used when DATA_SOURCE=mock.
    """

    def __init__(self):
        from seed import (
            generate_amazon_daily_data,
            generate_tiktok_daily_data,
            generate_shopee_daily_data,
        )
        self._generators = {
            "amazon": generate_amazon_daily_data,
            "tiktok": generate_tiktok_daily_data,
            "shopee": generate_shopee_daily_data,
        }
        self._platform_code_cache: dict[int, str] = {}

    def name(self) -> str:
        return "Mock Adapter (simulated data)"

    def fetch_daily_data(self, platform_id: int, target_date: date) -> dict[str, float]:
        """Generate one day of mock data for the given platform."""
        # Resolve platform code
        if platform_id not in self._platform_code_cache:
            from database import SessionLocal
            from models import Platform
            db = SessionLocal()
            p = db.query(Platform).filter(Platform.id == platform_id).first()
            db.close()
            self._platform_code_cache[platform_id] = p.code if p else "amazon"

        code = self._platform_code_cache[platform_id]
        generator = self._generators.get(code, self._generators["amazon"])

        records = generator(platform_id, target_date, target_date)
        return {r.metric_key: r.value for r in records}


# ═══════════════════════════════════════════════════════════════
#  CSV UPLOAD ADAPTER (zero-barrier real data import)
# ═══════════════════════════════════════════════════════════════

class CsvUploadAdapter(BaseAdapter):
    """
    Reads store data from CSV files. No API required.

    CSV format expected (one file per platform per date):
        metric_key,value
        gmv,18450.0
        orders,892
        acos,28.5
        ...

    File naming convention: {platform_code}_{YYYY-MM-DD}.csv
    Example: amazon_2026-06-16.csv

    Directory: set CSV_DATA_PATH in .env (default: ./csv_data/)
    """

    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = csv_path or os.getenv("CSV_DATA_PATH", "./csv_data/")
        self._platform_code_cache: dict[int, str] = {}

    def name(self) -> str:
        return "CSV Upload Adapter"

    def _get_platform_code(self, platform_id: int) -> str:
        if platform_id not in self._platform_code_cache:
            from database import SessionLocal
            from models import Platform
            db = SessionLocal()
            p = db.query(Platform).filter(Platform.id == platform_id).first()
            db.close()
            self._platform_code_cache[platform_id] = p.code if p else "amazon"
        return self._platform_code_cache[platform_id]

    def fetch_daily_data(self, platform_id: int, target_date: date) -> dict[str, float]:
        """Read data from a CSV file for the given platform and date."""
        code = self._get_platform_code(platform_id)
        filename = f"{code}_{target_date.isoformat()}.csv"
        filepath = os.path.join(self.csv_path, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"CSV file not found: {filepath}\n"
                f"Expected format: metric_key,value\\n"
                f"Example: gmv,18450.0\\norders,892"
            )

        data: dict[str, float] = {}
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("metric_key", "").strip()
                val_str = row.get("value", "").strip()
                if key and val_str:
                    try:
                        data[key] = float(val_str)
                    except ValueError:
                        pass  # Skip malformed rows
        return data


# ═══════════════════════════════════════════════════════════════
#  AMAZON SP-API ADAPTER (reserved — requires developer account)
# ═══════════════════════════════════════════════════════════════

class AmazonSpApiAdapter(BaseAdapter):
    """
    Reserved for Amazon Selling Partner API (SP-API).

    Requirements to use this adapter:
      - Amazon Seller Central 专业销售账户
      - 注册为 Amazon 开发者 (developer.amazon.com)
      - 创建 SP-API 应用并获取:
          AWS Access Key, Secret Key, Refresh Token
      - 完成 Amazon 资质审核 (2-4 weeks)

    See docs/API_SETUP.md#amazon for step-by-step guide.

    Notes for implementer:
      - Use `python-amazon-sp-api` or `boto3` to call SP-API
      - Endpoints: /sales/v1/orderMetrics, /finances/v0/orders, etc.
      - Rate limit: ~1 req/sec for most endpoints
      - OAuth2 refresh token flow required
    """

    def __init__(self):
        self.access_key = os.getenv("AMAZON_ACCESS_KEY", "")
        self.secret_key = os.getenv("AMAZON_SECRET_KEY", "")
        self.refresh_token = os.getenv("AMAZON_REFRESH_TOKEN", "")
        self.marketplace_id = os.getenv("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER")

    def name(self) -> str:
        return "Amazon SP-API Adapter"

    def _check_credentials(self):
        if not all([self.access_key, self.secret_key, self.refresh_token]):
            raise RuntimeError(
                "Amazon SP-API credentials not configured.\n"
                "Set AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_REFRESH_TOKEN in .env\n"
                "See docs/API_SETUP.md for how to obtain these."
            )

    def fetch_daily_data(self, platform_id: int, target_date: date) -> dict[str, float]:
        self._check_credentials()

        # TODO: Implement actual SP-API calls
        # 1. Request LWA OAuth2 access token
        # 2. Call Order Metrics API: GET /sales/v1/orderMetrics
        # 3. Call Finances API for ad_spend, cogs, fees
        # 4. Call Inventory API for stock levels
        # 5. Map API response fields to metric keys

        raise NotImplementedError(
            "Amazon SP-API adapter is not yet implemented.\n"
            "Credentials are configured — implement fetch_daily_data() "
            "to call SP-API endpoints. See docstring for guidance."
        )


# ═══════════════════════════════════════════════════════════════
#  TIKTOK SHOP PARTNER API ADAPTER (reserved)
# ═══════════════════════════════════════════════════════════════

class TikTokShopApiAdapter(BaseAdapter):
    """
    Reserved for TikTok Shop Partner API.

    Requirements:
      - TikTok Shop 商家账号
      - 申请 Partner API 权限 (partner.tiktokshop.com)
      - 获取 Partner Key & Secret
      - Shop ID for the target store

    See docs/API_SETUP.md#tiktok for step-by-step guide.

    Notes for implementer:
      - REST API with HMAC-SHA256 signing
      - Endpoints: /api/orders/search, /api/shop/performance, etc.
      - Content metrics (video_views, live_views) require Content API
    """

    def __init__(self):
        self.partner_key = os.getenv("TIKTOK_PARTNER_KEY", "")
        self.partner_secret = os.getenv("TIKTOK_PARTNER_SECRET", "")
        self.shop_id = os.getenv("TIKTOK_SHOP_ID", "")

    def name(self) -> str:
        return "TikTok Shop Partner API Adapter"

    def _check_credentials(self):
        if not all([self.partner_key, self.partner_secret, self.shop_id]):
            raise RuntimeError(
                "TikTok Shop API credentials not configured.\n"
                "Set TIKTOK_PARTNER_KEY, TIKTOK_PARTNER_SECRET, TIKTOK_SHOP_ID in .env\n"
                "See docs/API_SETUP.md for how to obtain these."
            )

    def fetch_daily_data(self, platform_id: int, target_date: date) -> dict[str, float]:
        self._check_credentials()

        # TODO: Implement actual TikTok API calls
        # 1. Generate HMAC-SHA256 signature
        # 2. Call /api/orders/search for GMV, orders
        # 3. Call /api/shop/performance for shop_score, penalty_points
        # 4. Call Content API for video_views, live_views, affiliate_gmv
        # 5. Call Ads API for tt_ads_spend, tt_ads_roas, tt_ads_ctr

        raise NotImplementedError(
            "TikTok Shop API adapter is not yet implemented.\n"
            "Credentials are configured — implement fetch_daily_data() "
            "to call TikTok Shop Partner API endpoints."
        )


# ═══════════════════════════════════════════════════════════════
#  SHOPEE OPEN PLATFORM API ADAPTER (reserved)
# ═══════════════════════════════════════════════════════════════

class ShopeeOpenApiAdapter(BaseAdapter):
    """
    Reserved for Shopee Open Platform API.

    Requirements:
      - Shopee 卖家中心账号
      - 注册 Open Platform (open.shopee.com)
      - 创建应用获取 Partner ID & Partner Key
      - Shop ID for the target store
      - API 调用额度: 通常 1000 次/小时

    See docs/API_SETUP.md#shopee for step-by-step guide.

    Notes for implementer:
      - REST API with HMAC-SHA256 signing
      - Endpoints: /api/v2/order/get_order_list, /api/v2/shop/get_performance
      - COD, chat, NFR metrics available via Shop Performance API
      - Flash sale data via Marketing API
    """

    def __init__(self):
        self.partner_id = os.getenv("SHOPEE_PARTNER_ID", "")
        self.partner_key = os.getenv("SHOPEE_PARTNER_KEY", "")
        self.shop_id = os.getenv("SHOPEE_SHOP_ID", "")

    def name(self) -> str:
        return "Shopee Open Platform API Adapter"

    def _check_credentials(self):
        if not all([self.partner_id, self.partner_key, self.shop_id]):
            raise RuntimeError(
                "Shopee API credentials not configured.\n"
                "Set SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_SHOP_ID in .env\n"
                "See docs/API_SETUP.md for how to obtain these."
            )

    def fetch_daily_data(self, platform_id: int, target_date: date) -> dict[str, float]:
        self._check_credentials()

        # TODO: Implement actual Shopee API calls
        # 1. Generate authorization URL & sign request
        # 2. Call /api/v2/order/get_order_list for GMV, orders, COD data
        # 3. Call /api/v2/shop/get_performance for shop_rating, nfr_rate, chat_response_rate
        # 4. Call /api/v2/logistics/get_shipping_parameter for logistics metrics
        # 5. Call /api/v2/ads/get_report for shopee_ads_spend, ROAS

        raise NotImplementedError(
            "Shopee Open API adapter is not yet implemented.\n"
            "Credentials are configured — implement fetch_daily_data() "
            "to call Shopee Open Platform API endpoints."
        )


# ═══════════════════════════════════════════════════════════════
#  ADAPTER FACTORY
# ═══════════════════════════════════════════════════════════════

def get_adapter(source: Optional[str] = None) -> BaseAdapter:
    """
    Factory: returns the active data adapter based on DATA_SOURCE env var.

    Usage:
        adapter = get_adapter()
        data = adapter.fetch_daily_data(platform_id, date)
    """
    source = source or os.getenv("DATA_SOURCE", "mock").lower().strip()

    adapters = {
        "mock": MockAdapter,
        "csv": CsvUploadAdapter,
        "amazon_spapi": AmazonSpApiAdapter,
        "tiktok": TikTokShopApiAdapter,
        "shopee": ShopeeOpenApiAdapter,
    }

    adapter_cls = adapters.get(source)
    if adapter_cls is None:
        raise ValueError(
            f"Unknown DATA_SOURCE '{source}'. "
            f"Valid options: {', '.join(adapters.keys())}"
        )

    return adapter_cls()

"""跨引擎共用、無副作用的公司 identity primitives。"""

from .registry import TICKER_MAP, CompanyIdentity, IdentityRegistry, get_registry

__all__ = ["TICKER_MAP", "CompanyIdentity", "IdentityRegistry", "get_registry"]

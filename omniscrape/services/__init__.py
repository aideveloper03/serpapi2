"""Services module"""
from .proxy_manager import ProxyManager, proxy_manager, Proxy
from .network_client import (
    NetworkClient,
    network_client,
    FingerprintRotator,
    BrowserProfile,
    CookieJar,
)
from .captcha_handler import (
    CaptchaHandler,
    captcha_handler,
    CaptchaDetector,
    CaptchaSolver,
    CaptchaType,
    CaptchaChallenge,
    CaptchaSolution,
)
from .data_miner import (
    DataMiner,
    data_miner,
    TechnologyDetector,
    WebsiteIntelligence,
    CompanyProfile,
)

__all__ = [
    "ProxyManager",
    "proxy_manager",
    "Proxy",
    "NetworkClient",
    "network_client",
    "FingerprintRotator",
    "BrowserProfile",
    "CookieJar",
    "CaptchaHandler",
    "captcha_handler",
    "CaptchaDetector",
    "CaptchaSolver",
    "CaptchaType",
    "CaptchaChallenge",
    "CaptchaSolution",
    "DataMiner",
    "data_miner",
    "TechnologyDetector",
    "WebsiteIntelligence",
    "CompanyProfile",
]

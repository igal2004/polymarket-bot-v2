"""
config.py — הגדרות הבוט (גרסת Termux)
"""

# ─── טלגרם ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8612471675:AAG22kCF2tTsADFW74BtrdjYaxINdFnz7lE"
TELEGRAM_CHAT_ID   = "547766473"

# ─── ארנק ────────────────────────────────────────────────────────────────────
PRIVATE_KEY = "9cd0457d9b8eb35b969927a8e92640a8a8c74ca8c00abfa98d10a83e78811239"
WALLET_ADDRESS = "0xc060a7feF07F27847A93917d47508181e683ba61"

# ─── פולימרקט ────────────────────────────────────────────────────────────────
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL  = "https://clob.polymarket.com"
POLYGON_CHAIN_ID     = 137

# ─── ארנקי מומחים למעקב ──────────────────────────────────────────────────────
EXPERT_WALLETS = {
    "kch123":               "0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee",
    "DrPufferfish":         "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e",
    "KeyTransporter":       "0x94f199fb7789f1aef7fff6b758d6b375100f4c7a",
    "RN1":                  "0x2005d16a84ceefa912d4e380cd32e7ff827875ea",
    "GCottrell93":          "0x94a428cfa4f84b264e01f70d93d02bc96cb36356",
    "swisstony":            "0x204f72f35326db932158cba6adff0b9a1da95e14",
    "gmanas":               "0xe90bec87d9ef430f27f9dcfe72c34b76967d5da2",
    "GamblingIsAllYouNeed": "0x507e52ef684ca2dd91f90a9d26d149dd3288beae",
    "blackwall":            "0xac44cb78be973ec7d91b69678c4bdfa7009afbd7",
    "beachboy4":            "0xc2e7800b5af46e6093872b177b7a5e7f0563be51",
    "anoin123":             "0x96489abcb9f583d6835c8ef95ffc923d05a86825",
    "weflyhigh":            "0x03e8a544e97eeff5753bc1e90d46e5ef22af1697",
    "gmpm":                 "0x14964aefa2cd7caff7878b3820a690a03c5aa429",
    "YatSen":               "0x5bffcf561bcae83af680ad600cb99f1184d6ffbe",
    "SwissMiss":            "0xdbade4c82fb72780a0db9a38f821d8671aba9c95",
}

# ─── פרמטרי מסחר ─────────────────────────────────────────────────────────────
DEFAULT_TRADE_AMOUNT_USD = 50
MAX_SLIPPAGE_PERCENT     = 2.0
MIN_EXPERT_TRADE_USD     = 100
POLL_INTERVAL_SECONDS    = 60

# ─── הגנות ארנק ──────────────────────────────────────────────────────────────
ENFORCE_BALANCE_CHECK    = True
MAX_SINGLE_TRADE_PERCENT = 10

# ─── מצב DRY RUN ─────────────────────────────────────────────────────────────
DRY_RUN = True   # שנה ל-False רק לאחר שבדקת שהכל עובד!

# ─── שעת דוח יומי ────────────────────────────────────────────────────────────
DAILY_REPORT_HOUR   = 20
DAILY_REPORT_MINUTE = 0

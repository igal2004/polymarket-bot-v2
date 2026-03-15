
"""
config.py — הגדרות הבוט (גרסת Termux)
"""
import os

# ─── טלגרם ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8612471675:AAG22kCF2tTsADFW74BtrdjYaxINdFnz7lE")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "547766473")

# ─── ארנק ────────────────────────────────────────────────────────────────────
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "9cd0457d9b8eb35b969927a8e92640a8a8c74ca8c00abfa98d10a83e78811239")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0xc060a7feF07F27847A93917d47508181e683ba61")

# ─── פולימרקט ────────────────────────────────────────────────────────────────
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL  = "https://clob.polymarket.com"
POLYGON_CHAIN_ID     = 137

# ─── ארנקי לווייתנים למעקב ─────────────────────────────────────────────────────
# הלווייתנים הגדולים ביותר בפולימרקט לפי רווח כולל
WHALE_WALLETS = {
    "Theo4":      "0x56687bf447db6ffa42ffe2204a05edaa20f55839",  # #1 כל הזמנים | +$22M | Win Rate 88.9%
    "Fredi9999":  "0x1f2dd6d473f3e824cd2f8a89d9c69fb96f6ad0cf",  # #2 כל הזמנים | +$16.6M | Win Rate 73.3%
    "Len9311238": "0x78b9ac44a6d7d7a076c14e0ad518b301b63c6b76",  # #4 כל הזמנים | +$8.7M | Win Rate 100%
    "zxgngl":     "0xd235973291b2b75ff4070e9c0b01728c520b0f29",  # #5 כל הזמנים | +$7.8M | Win Rate 80%
    "RepTrump":          "0x863134d00841b2e200492805a01e1e2f5defaa53",  # #6 כל הזמנים | +$7.5M | Win Rate 100%
    "HorizonSplendidView": "0x02227b8f5a9636e895607edd3185ed6ee5598ff7",  # ספורט אירופאי | +$4.0M | פעיל 2026
}

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
    # ─── 5 מומחים חדשים (מרץ 2026) ───────────────────────────────────────────
    "0xafEe":              "0xee50a31c3f5a7c77824b12a941a54388a2827ed6",  # טכנולוגיה/AI | +$1.19M | פעיל 2026
    "0x8dxd":              "0x63ce342161250d705dc0b16df89036c8e5f9ba9a",  # קריפטו (XRP) | +$2.18M | פעיל 2026
    "majorexploiter":      "0x019782cab5d844f02bafb71f512758be78579f3c",  # ספורט אירופאי | +$2.42M | פעיל 2026
    "coinman2":            "0x55be7aa03ecfbe37aa5460db791205f7ac9ddca3",  # קריפטו (ETH/SOL) | +$937K | פעיל 2026
}

# ─── פרמטרי מסחר ─────────────────────────────────────────────────────────────
DEFAULT_TRADE_AMOUNT_USD = 50
MAX_TRADE_AMOUNT_USD     = 50   # ✅ מקסימום לעסקה בודדת (בדולרים) — ניתן לשינוי בקונפיג בלבד
MAX_SLIPPAGE_PERCENT     = 2.0
MIN_EXPERT_TRADE_USD     = 100
POLL_INTERVAL_SECONDS    = 60

# ─── הגנות ארנק ──────────────────────────────────────────────────────────────
ENFORCE_BALANCE_CHECK    = True
MAX_SINGLE_TRADE_PERCENT = 10   # מקסימום 10% מהיתרה לעסקה בודדת
MAX_DAILY_SPEND_PERCENT  = 30   # מקסימום 30% מהיתרה ביום
MIN_TRADE_PRICE          = 0.20 # חסימת עסקאות מתחת ל-20% (סיכון גבוה מדי)
MAX_ENTRY_PRICE         = 0.75 # חסימת עסקאות מעל 75% — יחס סיכון/תגמול לא משתלם

# ─── שיפור 1: פרש מחיר דינמי לפי גודל עסקה ─────────────────────────────────
# עסקאות גדולות מזיזות שוק — לכן פרש מחיר מחמיר יותר
MAX_SPREAD_PCT_DEFAULT   = 20   # פרש מחיר מקסימלי (%) לעסקאות רגילות
MAX_SPREAD_PCT_LARGE     = 10   # פרש מחיר מקסימלי (%) לעסקאות גדולות (>$50K)
LARGE_TRADE_THRESHOLD    = 50000  # סף עסקה גדולה בדולרים

# ─── שיפור 2: נזילות מינימלית ────────────────────────────────────────────────
# שוק עם נפח נמוך — הקנייה שלנו תזיז את המחיר נגדנו
MIN_MARKET_VOLUME_USD    = 2000  # נפח מסחר מינימלי בשוק (הורד מ-$5,000 כדי לקבל יותר עסקאות)

# ─── מדרגות הגנה דינמיות לפי נפח שוק ────────────────────────────────────────
# ככל שנפח השוק קטן יותר — ה-Slippage וה-Spread המותרים מחמירים
# מקור: [בקשת משתמש] הגנה מפני החלקת מחיר בשווקים קטנים
VOLUME_TIERS = [
    # (נפח_מינימלי, max_slippage_pct, max_spread_pct)
    (5000, 2.0, 20),   # שוק גדול  — הגנה רגילה
    (3000, 1.5, 15),   # שוק בינוני — הגנה מוגברת
    (2000, 1.0, 10),   # שוק קטן   — הגנה חזקה
    # מתחת ל-2000 — חסום לחלוטין (MIN_MARKET_VOLUME_USD)
]

# ─── שיפור 3: Kelly Criterion + פרופיל סיכון ────────────────────────────────
# מכפיל לפי רמת סיכון המומחה — סיכון נמוך = פוזיציה גדולה יותר
KELLY_RISK_MULTIPLIERS   = {"low": 1.2, "medium": 1.0, "high": 0.7}

# ─── שיפור 4: עצירה אוטומטית על Drawdown מקסימלי ────────────────────────────
# אם הפורטפוליו ירד יותר מ-30% מהשיא — עצור אוטומטית
MAX_DRAWDOWN_PERCENT     = 30

# ─── שיפור 5: קונברגנציה — הגדלת פוזיציה כש-3+ לווייתנים מסכימים ────────────
CONVERGENCE_MIN_WHALES   = 3    # מינימום לווייתנים לאותו שוק לקונברגנציה
CONVERGENCE_MULTIPLIER   = 2.0  # הכפלת הפוזיציה בקונברגנציה
CONVERGENCE_WINDOW_HOURS = 24   # חלון זמן לזיהוי קונברגנציה (שעות)

# ─── שיפור 7: Drift Detection — זיהוי שינוי התנהגות מומחים ─────────────────
DRIFT_DETECTION_DAYS     = 30   # ימים אחרונים לבדיקת drift
DRIFT_ALERT_THRESHOLD    = 20   # אחוז שינוי ב-win_rate שמפעיל התראה

# ─── פקיעת שוק מקסימלית ──────────────────────────────────────────────────────
# חסימת עסקאות בשווקים שנסגרים יותר מ-N ימים מהיום (0 = ללא הגבלה)
MAX_MARKET_DAYS_TO_EXPIRY = 90  # מקסימום 90 יום עד סגירת השוק

# ─── מצב DRY RUN ─────────────────────────────────────────────────────────────
DRY_RUN = True   # שנה ל-False רק לאחר שבדקת שהכל עובד!

# ─── שעת דוח יומי ────────────────────────────────────────────────────────────
DAILY_REPORT_HOUR   = 20
DAILY_REPORT_MINUTE = 0

# ─── [GEMINI] Pipeline 8 שלבים — פרמטרים חדשים ─────────────────────────────
# שלב 4: Expert Stop-Loss — השעיית מומחה אחרי N הפסדים רצופים
EXPERT_STOP_LOSS_STREAK  = 5    # מספר הפסדים רצופים להשעיה
# שלב 5: Herd Detection — חסימה כש-N+ מומחים נכנסים לאותו שוק
HERD_DETECTION_THRESHOLD = 5    # מספר מומחים שמגדיר "עדר"
# שלב 6: Sector Exposure — חסימה אם יש יותר מ-N עסקאות פתוחות על אותו נושא
MAX_SECTOR_TRADES        = 3    # מקסימום עסקאות פתוחות לנושא
# שלב 8: Slippage Tracking — מדידת פרש מחיר 30 שניות לאחר כניסה (DRY RUN)
SLIPPAGE_DELAY_SECONDS   = 30   # עיכוב בשניות לסימולציית slippage
# [GEMINI] ללא ניסיונות חוזרים אם מחיר השתנה
RETRY_ATTEMPTS           = 0    # 0 = אין ניסיון חוזר אם מחיר השתנה
# [GEMINI+CLAUDE] HIGH risk multiplier — פשרה בין קלוד (0.7) לג'מיני (0.5)
KELLY_RISK_MULTIPLIERS   = {"low": 1.2, "medium": 1.0, "high": 0.6}

# ─── Exit Manager — Take Profit / Stop Loss / Time Exit ──────────────────────
TAKE_PROFIT_PCT      = 20.0   # יציאה ברווח כש-ROI הגיע ל-+20%
STOP_LOSS_PCT        = 12.0   # יציאה בהפסד כש-ROI ירד ל--12%
TIME_EXIT_HOURS      = 48     # יציאה אוטומטית אחרי 48 שעות
TRAILING_STOP_ENABLED = True  # Trailing Stop Loss — מעקב אחרי שיא המחיר

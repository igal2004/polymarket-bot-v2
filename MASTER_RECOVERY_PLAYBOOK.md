# 📖 Polymarket Bot v2 — Master Recovery Playbook

**תאריך עדכון:** 13/03/2026
**גרסה:** 2.1 (Pipeline 8 שלבים)

---

## 1. סקירת מערכת

מערכת המסחר מורכבת מ-3 בוטים הפועלים על פלטפורמת Railway ומתקשרים עם המשתמש דרך טלגרם. ליבת המערכת היא **Pipeline 8 שלבים** המנתח כל הזדמנות מסחר לפני שליחת התראה. ה-Pipeline משלב 25 בדיקות שונות ממקורות המערכת המקורית, ניתוח Claude, וניתוח Gemini.

### Pipeline 8 השלבים:

| שלב | שם | תיאור | מקור |
|---|---|---|---|
| 1 | 🛑 Drawdown Guard | עצירה אם הפורטפוליו ירד >30% מהשיא | [CLAUDE] |
| 2 | 💧 Liquidity Check | חסימת שווקים עם נפח < $5,000 | [CLAUDE] |
| 3 | 📉 Spread Filter | פרש מחיר דינמי (+10%/>$50K, +20%/רגיל) | [CLAUDE] |
| 4 | 🚦 Expert Stop-Loss | חסימה אם המומחה ב-5 הפסדים רצופים | [GEMINI] |
| 5 | 🐑 Herd Detection | אזהרה/חסימה אם 5+ מומחים נכנסו (עדר) | [GEMINI] |
| 6 | 🗂️ Sector Exposure | חסימה אם >3 עסקאות פתוחות על אותו נושא | [GEMINI] |
| 7 | ⚖️ Position Sizing | Kelly × סיכון × קונברגנציה × drift | [OUR/CLAUDE/GEMINI] |
| 8 | 📡 Signals & Alerts | Drift Detection + קונברגנציה + Slippage | [CLAUDE/GEMINI] |


## 2. שחזור מערכת מלא (Full System Recovery)

במקרה של כשל קטסטרופלי, ניתן לשחזר את המערכת במלואה על ידי ביצוע הצעדים הבאים:

1.  **Clone a new copy of the repository:**
    ```bash
    git clone https://github.com/igal2004/polymarket-bot-v2.git
    cd polymarket-bot-v2
    ```

2.  **Create a new project on Railway:**
    - Link it to your GitHub repository (`igal2004/polymarket-bot-v2`).
    - Railway will automatically detect the `nixpacks.toml` and `Procfile` and deploy the application.

3.  **Set Environment Variables in Railway:**
    - Go to the project settings in Railway -> Variables.
    - Add the following secrets:

| משתנה | ערך | תיאור |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `8612471675:AAG22kCF2tTsADFW74BtrdjYaxINdFnz7lE` | טוקן בוט טלגרם |
| `TELEGRAM_CHAT_ID` | `547766473` | מזהה צ'אט טלגרם |
| `PRIVATE_KEY` | `9cd0457d...` (ערך מלא בקובץ מאובטח) | מפתח פרטי לארנק |
| `WALLET_ADDRESS` | `0xc060a7feF07F27847A93917d47508181e683ba61` | כתובת ארנק ציבורית |
| `OPENAI_API_KEY` | `sk-LRMmMr4d...` (ערך מלא בקובץ מאובטח) | מפתח OpenAI API |
| `OPENAI_BASE_URL` | `https://api.manus.im/api/llm-proxy/v1` | כתובת Manus LLM Proxy |
| `GMAIL_SENDER` | (Your Gmail) | כתובת מייל לשליחת התראות |
| `GMAIL_APP_PASS` | (Your App Password) | סיסמת אפליקציה של ג'ימייל |

4.  **Trigger a new deployment in Railway.**
    - The bot should start automatically and begin tracking.

5.  **Run the audit bot manually to verify:**
    - Open a shell to the Railway instance and run:
    ```bash
    python3.11 audit_bot.py
    ```
    - Verify that all checks pass (except for ENV vars which are now set).
_md", text="
## 3. רשימת ארנקים במעקב

### ארנקי לווייתנים (Whale Wallets)

| שם | כתובת ארנק |
|---|---|
| Theo4 | 0x56687bf447db6ffa42ffe2204a05edaa20f55839 |
| Fredi9999 | 0x1f2dd6d473f3e824cd2f8a89d9c69fb96f6ad0cf |
| Len9311238 | 0x78b9ac44a6d7d7a076c14e0ad518b301b63c6b76 |
| zxgngl | 0xd235973291b2b75ff4070e9c0b01728c520b0f29 |
| RepTrump | 0x863134d00841b2e200492805a01e1e2f5defaa53 |

### ארנקי מומחים (Expert Wallets)

| שם | כתובת ארנק |
|---|---|
| kch123 | 0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee |
| DrPufferfish | 0xdb27bf2ac5d428a9c63dbc914611036855a6c56e |
| KeyTransporter | 0x94f199fb7789f1aef7fff6b758d6b375100f4c7a |
| RN1 | 0x2005d16a84ceefa912d4e380cd32e7ff827875ea |
| GCottrell93 | 0x94a428cfa4f84b264e01f70d93d02bc96cb36356 |
| swisstony | 0x204f72f35326db932158cba6adff0b9a1da95e14 |
| gmanas | 0xe90bec87d9ef430f27f9dcfe72c34b76967d5da2 |
| GamblingIsAllYouNeed | 0x507e52ef684ca2dd91f90a9d26d149dd3288beae |
| blackwall | 0xac44cb78be973ec7d91b69678c4bdfa7009afbd7 |
| beachboy4 | 0xc2e7800b5af46e6093872b177b7a5e7f0563be51 |
| anoin123 | 0x96489abcb9f583d6835c8ef95ffc923d05a86825 |
| weflyhigh | 0x03e8a544e97eeff5753bc1e90d46e5ef22af1697 |
| gmpm | 0x14964aefa2cd7caff7878b3820a690a03c5aa429 |
| YatSen | 0x5bffcf561bcae83af680ad600cb99f1184d6ffbe |
| SwissMiss | 0xdbade4c82fb72780a0db9a38f821d8671aba9c95 |
"))))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**))"**"**))"**))"**))"**))"**))"**))"**))"**-r--r-- 1 ubuntu ubuntu 1435 Mar 13 16:32 /home/ubuntu/polymarket-bot-v2/MASTER_RECOVERY_PLAYBOOK.md
ubuntu@sandbox:~/polymarket-bot-v2 $"}}

## 4. תיעוד פרמטרים מלא (config.py)

| פרמטר | ערך | תיאור |
|---|---|---|
| **מסחר כללי** | |
| `DEFAULT_TRADE_AMOUNT_USD` | 50 | סכום ברירת מחדל לעסקה בדולרים |
| `MAX_SLIPPAGE_PERCENT` | 2.0 | אחוז החלקת מחיר מקסימלי |
| `MIN_EXPERT_TRADE_USD` | 100 | סכום מינימלי לעסקת מומחה כדי לעורר התראה |
| `POLL_INTERVAL_SECONDS` | 60 | מרווח זמן בין בדיקות ארנקים (בשניות) |
| `DRY_RUN` | True | אם `True`, לא מבצע עסקאות אמת אלא רק רישום ביומן |
| **הגנות ארנק** | |
| `ENFORCE_BALANCE_CHECK` | True | האם לאכוף בדיקת יתרה לפני מסחר |
| `MAX_SINGLE_TRADE_PERCENT` | 10 | אחוז מקסימלי מהיתרה לעסקה בודדת |
| `MAX_DAILY_SPEND_PERCENT` | 30 | אחוז מקסימלי מהיתרה להוצאה ביום אחד |
| `MIN_TRADE_PRICE` | 0.20 | מחיר מינימלי לעסקה (חוסם עסקאות בסיכון גבוה) |
| **Pipeline: שיפורי Claude** | |
| `MAX_SPREAD_PCT_DEFAULT` | 20 | פרש מחיר מקסימלי לעסקאות רגילות |
| `MAX_SPREAD_PCT_LARGE` | 10 | פרש מחיר מקסימלי לעסקאות גדולות (מעל `LARGE_TRADE_THRESHOLD`) |
| `LARGE_TRADE_THRESHOLD` | 50000 | סף עסקה גדולה בדולרים |
| `MIN_MARKET_VOLUME_USD` | 5000 | נפח מסחר מינימלי בשוק |
| `KELLY_RISK_MULTIPLIERS` | `{'low': 1.2, 'medium': 1.0, 'high': 0.6}` | מכפיל Kelly Criterion לפי רמת סיכון המומחה |
| `MAX_DRAWDOWN_PERCENT` | 30 | אחוז ירידה מהשיא לעצירת מסחר אוטומטית |
| `CONVERGENCE_MIN_WHALES` | 3 | מספר מינימלי של לווייתנים להגדרת קונברגנציה |
| `CONVERGENCE_MULTIPLIER` | 2.0 | מכפיל הגדלת פוזיציה בקונברגנציה |
| `CONVERGENCE_WINDOW_HOURS` | 24 | חלון זמן לזיהוי קונברגנציה (בשעות) |
| `DRIFT_DETECTION_DAYS` | 30 | מספר ימים אחרונים לבדיקת שינוי התנהגות (drift) |
| `DRIFT_ALERT_THRESHOLD` | 20 | אחוז שינוי ב-win rate להפעלת התראת drift |
| **Pipeline: שיפורי Gemini** | |
| `EXPERT_STOP_LOSS_STREAK` | 5 | מספר הפסדים רצופים להשעיית מומחה |
| `HERD_DETECTION_THRESHOLD` | 5 | מספר מומחים שמגדיר "עדר" וחוסם את השוק |
| `MAX_SECTOR_TRADES` | 3 | מספר עסקאות מקסימלי פתוחות באותו נושא |
| `SLIPPAGE_DELAY_SECONDS` | 30 | עיכוב לסימולציית החלקת מחיר ב-DRY RUN |
| `RETRY_ATTEMPTS` | 0 | מספר ניסיונות חוזרים אם מחיר השתנה (0 = ללא) |

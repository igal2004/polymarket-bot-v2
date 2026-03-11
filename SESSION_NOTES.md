# סיכום שיחה — בוט פולימרקט
**תאריך:** פברואר 2026

---

## מה נעשה בשיחה זו

### 1. עדכון רשימת המומחים
הוחלפה רשימת המומחים הישנה ברשימה חדשה מבוססת על:
- **לוח כל-זמני** של Polymarket (עקביות לאורך שנים)
- **לוח חודשי** (פעילות עכשווית)
- **אימות ישיר** של כתובות ארנק מדפי פרופיל

#### ממצא חשוב: באג בגרסה הישנה
הכתובת של **KeyTransporter** הייתה שגויה — הצביעה על `gmanas` במקום על KeyTransporter האמיתי.

---

## רשימת המומחים הנוכחית (15 סוחרים)

### קבוצה א: מופיעים בשני הלוחות (כל-זמני + חודשי)
| שם | כתובת ארנק | רווח כל-זמני |
|---|---|---|
| kch123 | `0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee` | $10,704,604 |
| DrPufferfish | `0xdb27bf2ac5d428a9c63dbc914611036855a6c56e` | $6,279,958 |
| KeyTransporter | `0x94f199fb7789f1aef7fff6b758d6b375100f4c7a` | $5,711,460 |
| RN1 | `0x2005d16a84ceefa912d4e380cd32e7ff827875ea` | $5,192,778 |
| GCottrell93 | `0x94a428cfa4f84b264e01f70d93d02bc96cb36356` | $4,229,396 |
| swisstony | `0x204f72f35326db932158cba6adff0b9a1da95e14` | $4,220,763 |
| gmanas | `0xe90bec87d9ef430f27f9dcfe72c34b76967d5da2` | $4,097,908 |
| GamblingIsAllYouNeed | `0x507e52ef684ca2dd91f90a9d26d149dd3288beae` | $3,693,463 |

### קבוצה ב: פעילים מאוד עכשיו (חודשי)
| שם | כתובת ארנק | רווח חודשי |
|---|---|---|
| blackwall | `0xac44cb78be973ec7d91b69678c4bdfa7009afbd7` | $2,310,858 |
| beachboy4 | `0xc2e7800b5af46e6093872b177b7a5e7f0563be51` | $2,094,044 |
| anoin123 | `0x96489abcb9f583d6835c8ef95ffc923d05a86825` | $1,302,657 |
| weflyhigh | `0x03e8a544e97eeff5753bc1e90d46e5ef22af1697` | $1,146,724 |
| gmpm | `0x14964aefa2cd7caff7878b3820a690a03c5aa429` | פעיל מאוד |
| YatSen | `0x5bffcf561bcae83af680ad600cb99f1184d6ffbe` | פעיל |
| SwissMiss | `0xdbade4c82fb72780a0db9a38f821d8671aba9c95` | פעיל |

---

## מצב הבוט הנוכחי
- **פועל:** כן (Termux, ברקע)
- **מצב:** DRY RUN (לא מבצע עסקאות אמיתיות)
- **בדיקה כל:** 60 שניות
- **דוח יומי:** 20:00 שעון ישראל
- **בדיקת כתובות:** 08:00 יומי

## פקודות שימושיות ב-Termux
```bash
# בדיקה שהבוט רץ
pgrep -a python

# עצירת הבוט
pkill -9 -f main.py

# הפעלת הבוט
cd ~/polymarket-bot-termux && python main.py &

# הפעלה מחדש מאפס (אם הקבצים נמחקו)
curl -L -o ~/setup_bot.py "https://files.manuscdn.com/user_upload_by_module/session_file/310519663383156782/uSosvCLiMymMPOzg.py"
python ~/setup_bot.py
cd ~/polymarket-bot-termux && pip install -r requirements.txt -q && python main.py &
```

## פקודות טלגרם
- `/status` — סטטוס הבוט ויתרת ארנק
- `/portfolio` — פוזיציות פתוחות
- `/report` — דוח מלא
- `/validate` — בדיקת אמיתות כתובות המומחים

---

## קבצי הבוט
```
~/polymarket-bot-termux/
├── config.py           — הגדרות + רשימת מומחים
├── main.py             — נקודת כניסה
├── telegram_bot.py     — בוט טלגרם + פקודות
├── tracker.py          — מעקב עסקאות מומחים
├── polymarket_client.py — תקשורת עם Polymarket API
├── portfolio.py        — פורטפוליו
├── requirements.txt    — חבילות Python
└── seen_trades.json    — עסקאות שנראו (נוצר אוטומטית)
```

---

## הערות לעתיד
1. לעבור ל-**DRY_RUN = False** רק לאחר בדיקה מספקת
2. ניתן להוסיף/להסיר מומחים ב-`config.py` תחת `EXPERT_WALLETS`
3. הבוט שולח התראה עם כפתורי אישור/ביטול לכל עסקה מעל $100
4. הגנת ארנק: מקסימום 10% מהיתרה לעסקה בודדת

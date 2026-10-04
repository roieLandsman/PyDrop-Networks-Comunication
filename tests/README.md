# בדיקות בקשות לא תקינות

הבדיקות דורשות Python 3.10 ומעלה ומשתמשות רק בספרייה הסטנדרטית.
יש להריץ את הפקודות מתיקיית הפרויקט.

## בדיקות אוטומטיות

```sh
python3 -m unittest discover -s tests -v
```

הבדיקות פותחות חיבור TCP אל `127.0.0.1` בפורט פנוי, מריצות את מטפל
החיבור האמיתי של השרת ומשתמשות בתיקייה זמנית לקבצים ולמטא־דאטה.
אין צורך להפעיל שרת או Docker מראש. המידע הזמני נמחק בסיום.

| תרחיש | הבקשה | התוצאה הצפויה |
| --- | --- | --- |
| UPDATE עם גרסה ישנה | העלאה יוצרת גרסה 1, עדכון תקין יוצר גרסה 2, ואז נשלח UPDATE עם `version=1` | `ERROR` עם `code=STALE_VERSION`; התוכן והמטא־דאטה נשארים בגרסה 2 |
| שם קובץ לא תקין | UPLOAD ו־UPDATE עם שם ריק, `null`, מספר, `.`, `..`, נתיב מוחלט או שם שמכיל `/` או `\` | `ERROR` עם `code=INVALID_FILENAME`; לא נכתב קובץ ולא משתנה המטא־דאטה |
| פעולה שאינה נתמכת | `action=RENAME` | `ERROR` עם `code=UNKNOWN_ACTION`; מצב השרת אינו משתנה |

נבדק גם שאפשר לשלוח בקשה תקינה באותו חיבור אחרי הדחייה.
בתרחיש הגרסה הישנה נבדקים גם הורדת התוכן שנשמר ועדכון תקין נוסף לגרסה 3.
בדיקת שמות הקבצים כוללת 20 תתי־מקרים: 10 שמות לכל אחת משתי הפעולות.

להרצת תרחיש בודד, עם הצגת כותרות הבקשות והתשובות לצורך בדיקה ידנית:

```sh
PYDROP_SHOW_MESSAGES=1 python3 -m unittest tests.test_invalid_requests.InvalidRequestsTest.test_stale_update -v
PYDROP_SHOW_MESSAGES=1 python3 -m unittest tests.test_invalid_requests.InvalidRequestsTest.test_invalid_filename -v
PYDROP_SHOW_MESSAGES=1 python3 -m unittest tests.test_invalid_requests.InvalidRequestsTest.test_unsupported_action -v
```

## שליחה ידנית לשרת Docker שכבר פועל

יש להשתמש בשרת בדיקות: התרחיש רושם לקוח בדיקה ויוצר קובץ זמני שהלקוחות
האחרים עשויים לסנכרן. בסיום מוחקים את הקובץ באמצעות הפרוטוקול.

פתחו Python בתוך קונטיינר השרת, כדי להשתמש באותה סביבת רשת:

```sh
docker exec -it pydrop-server python
```

הדביקו את קוד ההכנה הבא. הוא שולח כותרות ישירות לפרוטוקול כדי שהבדיקה
תגיע לשרת; פונקציות הבקשות הרגילות של הלקוח חוסמות שמות לא תקינים כבר בצד הלקוח.

```python
import hashlib
import json
import socket
import time
import uuid
from client.protocol import send_message, read_message
from server.constants import HOST, PORT

client_id = "manual-test-" + uuid.uuid4().hex
filename = client_id + ".txt"
sock = socket.create_connection((HOST, PORT), timeout=5)

def exchange(action, payload=b"", **fields):
    request = {"action": action, "client_id": client_id, **fields}
    send_message(sock, request, payload)
    response = read_message(sock)
    if response is None:
        raise RuntimeError("Server closed the connection")
    print(json.dumps(response[0], indent=2), response[1])
    return response

def write(action, name, content, version=0):
    return exchange(action, content, filename=name, version=version,
                    mtime=time.time(), hash=hashlib.sha256(content).hexdigest())

exchange("CONNECT")
```

שליחת UPDATE עם גרסה ישנה:

```python
write("UPLOAD", filename, b"version 1")          # ACK, metadata.version = 1
write("UPDATE", filename, b"version 2", 1)       # ACK, metadata.version = 2
write("UPDATE", filename, b"stale content", 1)   # ERROR, code = STALE_VERSION
exchange("DOWNLOAD", filename=filename)          # ACK, version 2, b'version 2'
```

שליחת שם קובץ לא תקין:

```python
write("UPLOAD", "../invalid.txt", b"invalid")    # ERROR, code = INVALID_FILENAME
```

שליחת פעולה שאינה נתמכת, ואחריה בקשה תקינה לווידוא שהחיבור עדיין פעיל:

```python
exchange("RENAME")                              # ERROR, code = UNKNOWN_ACTION
exchange("CHECK_UPDATES")                       # ACK
```

ניקוי קובץ הבדיקה וסגירת החיבור:

```python
exchange("DELETE", filename=filename, version=2)
sock.close()
```

מחיקה זו משתמשת במנגנון המחיקות הרגיל של השרת; רשומת הלקוח והמידע על
המחיקה מנוהלים כמו בכל שימוש רגיל בפרוטוקול. הבדיקות האוטומטיות מבודדות
לחלוטין ומתאימות להרצות חוזרות בלי להשאיר מידע כזה בשרת פעיל.

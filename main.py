from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import sqlite3
from datetime import datetime
import random

app = FastAPI()

# --- إعداد قاعدة البيانات (SQLite) ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
        (username TEXT PRIMARY KEY, password TEXT, live REAL, demo REAL, role TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS history 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, amt REAL, status TEXT, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, amt REAL, wallet TEXT, status TEXT)''')
    
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users VALUES ('admin', 'admin123', 0.0, 10000.0, 'admin', 'active')")
    
    conn.commit()
    conn.close()

init_db()

def db_query(query, params=(), fetch=False, commit=False):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetch: res = cursor.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

BASE_STYLE = """
<style>
    :root { --gold: #F3BA2F; --bg: #0B0E11; --card: #1E2329; --green: #0ECB81; --red: #F6465D; --gray: #848E9C; --line: #2B3139; --blue: #3498db; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; direction: rtl; }
    .card { background: var(--card); border-radius: 12px; padding: 15px; border: 1px solid var(--line); margin: 10px; }
    .btn-gold { background: var(--gold); color: black; border: none; padding: 12px; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer; display: block; text-align: center; text-decoration: none; margin-top:10px; }
    input { width: 100%; padding: 12px; margin: 8px 0; background: #0B0E11; border: 1px solid #333; color: white; border-radius: 8px; box-sizing: border-box; }
    .nav-bar { position: fixed; bottom: 0; width: 100%; background: var(--card); display: grid; grid-template-columns: repeat(5, 1fr); border-top: 1px solid var(--line); height: 70px; z-index: 1000; }
    .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--gray); font-size: 10px; cursor: pointer; text-decoration: none; }
    .nav-item.active { color: var(--gold); }
    .tab { display: none; padding-bottom: 85px; }
    .tab.active { display: block; }
    .social-link { display: flex; align-items: center; padding: 12px; background: #2B3139; margin-bottom: 8px; border-radius: 10px; color: white; text-decoration: none; gap: 15px; border: 1px solid #333; font-size: 14px; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page(msg: str = ""):
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{BASE_STYLE}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='width:320px; text-align:center;'><h1 style='color:var(--gold)'>AURA PRO</h1><p style='color:var(--red); font-size:12px;'>{msg}</p><form action='/login' method='post'><input name='username' placeholder='اسم المستخدم' required><input name='password' type='password' placeholder='كلمة المرور' required><button class='btn-gold'>دخول / تسجيل</button></form></div></body></html>"

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = db_query("SELECT * FROM users WHERE username=?", (username,), fetch=True)
    if not user:
        db_query("INSERT INTO users VALUES (?, ?, 0.0, 10000.0, 'user', 'active')", (username, password), commit=True)
        return RedirectResponse(url=f"/dashboard?user={username}", status_code=303)
    if user[0][1] == password:
        if user[0][5] == 'blocked': return RedirectResponse(url="/?msg=الحساب محظور", status_code=303)
        return RedirectResponse(url="/admin_panel" if user[0][4] == 'admin' else f"/dashboard?user={username}", status_code=303)
    return RedirectResponse(url="/?msg=خطأ في البيانات", status_code=303)

@app.get("/admin_panel", response_class=HTMLResponse)
async def admin():
    users = db_query("SELECT username, live FROM users WHERE role='user'", fetch=True)
    trans = db_query("SELECT id, username, amt, type, wallet FROM transactions WHERE status='pending'", fetch=True)
    users_html = "".join([f'<div class="card" style="font-size:11px;"><b>{u[0]}</b> | رصيد: ${u[1]} <a href="/admin/toggle/{u[0]}" style="color:red; float:left;">حظر</a></div>' for u in users])
    trans_html = "".join([f'<div class="card" style="font-size:11px;">{t[1]} طلب {t[3]} بقيمة ${t[2]}<br><small>المحفظة: {t[4]}</small><br><a href="/admin/approve/{t[0]}" class="admin-action" style="background:var(--green); color:white; padding:4px; border-radius:4px; text-decoration:none;">قبول</a></div>' for t in trans])
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{BASE_STYLE}</head><body><div style='padding:15px; background:var(--card); font-weight:bold; color:var(--blue);'>لوحة الإدارة <a href='/' style='float:left; color:white;'>خروج</a></div><div class='card'><h4>طلبات معلقة</h4>{trans_html if trans_html else 'لا يوجد'}</div><div class='card'><h4>المستخدمين</h4>{users_html}</div></body></html>"

@app.get("/admin/approve/{tid}")
async def approve(tid: int):
    t_data = db_query("SELECT username, amt, type FROM transactions WHERE id=?", (tid,), fetch=True)
    if t_data:
        t = t_data[0]
        if t[2] == 'deposit':
            db_query("UPDATE users SET live = live + ? WHERE username=?", (t[1], t[0]), commit=True)
        db_query("UPDATE transactions SET status='approved' WHERE id=?", (tid,), commit=True)
        db_query("INSERT INTO history (username, type, amt, status, date) VALUES (?, ?, ?, ?, ?)", (t[0], t[2], t[1], 'مقبول', datetime.now().strftime("%H:%M")), commit=True)
    return RedirectResponse(url="/admin_panel", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user: str):
    u = db_query("SELECT live, demo FROM users WHERE username=?", (user,), fetch=True)[0]
    hist = db_query("SELECT type, amt, status FROM history WHERE username=? ORDER BY id DESC", (user,), fetch=True)
    hist_html = "".join([f'<div style="font-size:11px; padding:5px; border-bottom:1px solid #333;">{h[0]} ({h[1]}$) - {h[2]}</div>' for h in hist])
    
    my_wallet = "THL8B6chNcr8L7Z7Ut7AGBwXHsbgqPwY38"

    return f"""
    <html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'>{BASE_STYLE}</head>
    <body>
    <div style='padding:15px; background:var(--card); display:flex; justify-content:space-between;'>
        <span style='color:var(--gold); font-weight:bold;'>AURA PRO</span>
        <span style='font-size:12px;'>{user} <i class='fas fa-user-circle'></i></span>
    </div>
    
    <div id='tab_home' class='tab active'>
        <div class='card' style='border-right:4px solid var(--gold); font-size:13px;'>🚀 انطلق نحو القمة مع Aura Pro! استثمر بذكاء، ضاعف أرباحك، واستمتع بسحب فوري لثروتك.</div>
        <div style='display:grid; grid-template-columns:1fr 1fr; gap:10px; padding:10px;'>
            <div class='card' style='margin:0; text-align:center;'><small>حقيقي</small><br><b>$<span id='live_bal'>{u[0]:,}</span></b></div>
            <div class='card' style='margin:0; text-align:center; color:var(--blue);'><small>تجريبي</small><br><b>$<span id='demo_bal'>{u[1]:,}</span></b></div>
        </div>
        <div class='card'><h4>سجل العمليات</h4>{{hist_html if hist_html else 'لا توجد عمليات'}}</div>
    </div>

    <div id='tab_markets' class='tab'>
        <iframe src='https://s.tradingview.com/widgetembed/?symbol=BINANCE:BTCUSDT&theme=dark' width='100%' height='450' frameborder='0'></iframe>
    </div>

    <div id='tab_trade' class='tab'>
        <div class='card' style='text-align:center; padding:30px 10px;'>
            <i class='fas fa-robot' style='font-size:50px; color:var(--gold);'></i>
            <h3>Aura AI Bot</h3>
            <p style='font-size:12px; color:var(--gray);'>البوت يعمل حالياً على الحساب التجريبي</p>
            <button class='btn-gold' id='botBtn' onclick='runBot()'>بدء التداول الآلي</button>
            <div id='pnl' style='font-size:25px; margin-top:15px; color:var(--green); display:none;'>+$0.00</div>
        </div>
    </div>

    <div id='tab_wallet' class='tab'>
        <div class='card'>
            <h4>الإيداع (USDT TRC20)</h4>
            <p style='font-size:11px; color:var(--gray);'>أرسل إلى العنوان التالي (الحد الأدنى 10$):</p>
            <div style='background:#000; padding:10px; border-radius:8px; font-size:10px; color:var(--gold); border:1px dashed #555; text-align:center; word-break:break-all;'>{my_wallet}</div>
            <input id='dep_amt' type='number' placeholder='المبلغ ($)' min='10'>
            <button class='btn-gold' onclick='submitTrans("deposit")'>تأكيد الإيداع</button>
            <hr style='border:0; border-top:1px solid #333; margin:20px 0;'>
            <h4>طلب سحب</h4>
            <input id='with_addr' placeholder='عنوان محفظتك للسحب'>
            <input id='with_amt' type='number' placeholder='المبلغ ($)'>
            <button class='btn-gold' style='background:var(--red); color:white;' onclick='submitTrans("withdraw")'>طلب سحب</button>
        </div>
    </div>

    <div id='tab_social' class='tab'>
        <div class='card'>
            <h4 style='text-align:center; color:var(--gold);'>تابعنا وتواصل معنا</h4>
            <a href='https://www.youtube.com/@BinanceYoutube' target='_blank' class='social-link'><i class='fab fa-youtube' style='color:red;'></i> يوتيوب</a>
            <a href='https://tiktok.com/@binance' target='_blank' class='social-link'><i class='fab fa-tiktok' style='color:white;'></i> تيك توك</a>
            <a href='https://instagram.com/binance' target='_blank' class='social-link'><i class='fab fa-instagram' style='color:#E1306C;'></i> انستغرام</a>
            <a href='https://facebook.com/binance' target='_blank' class='social-link'><i class='fab fa-facebook' style='color:#1877F2;'></i> فيسبوك</a>
            <a href='https://bit.ly/GetBinanceApp' target='_blank' class='social-link'><i class='fas fa-mobile-alt' style='color:var(--gold);'></i> تحميل التطبيق</a>
            <button class='btn-gold' style='background:var(--red); color:white; margin-top:20px;' onclick="location.href='/'">خروج</button>
        </div>
    </div>

    <div class='nav-bar'>
        <div class='nav-item active' onclick="showTab('tab_home', this)"><i class='fas fa-home'></i>الرئيسية</div>
        <div class='nav-item' onclick="showTab('tab_markets', this)"><i class='fas fa-chart-line'></i>الأسواق</div>
        <div class='nav-item' onclick="showTab('tab_trade', this)"><i class='fas fa-robot'></i>تداول</div>
        <div class='nav-item' onclick='showTab("tab_wallet", this)'><i class='fas fa-wallet'></i>محفظة</div>
        <div class='nav-item' onclick='showTab("tab_social", this)'><i class='fas fa-share-alt'></i>تواصل</div>
    </div>

    <script>
        function showTab(id, el) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            el.classList.add('active');
        }}

        let botActive = false;
        async function runBot() {{
            if(botActive) return;
            botActive = true;
            document.getElementById('botBtn').innerText = "البوت قيد العمل...";
            document.getElementById('botBtn').style.opacity = "0.5";
            const p = document.getElementById('pnl'); p.style.display='block';
            
            setInterval(async () => {{
                let change = (Math.random() * 35 - 10).toFixed(2);
                p.innerText = (change >= 0 ? "+" : "") + "$" + change;
                p.style.color = change >= 0 ? "var(--green)" : "var(--red)";
                
                const res = await fetch('/update_demo', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: `u={user}&amt=${{change}}`
                }});
                if(res.ok) {{
                    const data = await res.json();
                    document.getElementById('demo_bal').innerText = data.new_bal.toLocaleString();
                }}
            }}, 3000);
        }}

        async function submitTrans(type) {{
            let amt, wallet;
            if(type === 'deposit') {{
                amt = document.getElementById('dep_amt').value;
                if(parseFloat(amt) < 10) return alert('أقل مبلغ للإيداع هو 10$');
                wallet = "THL8B6chNcr8L7Z7Ut7AGBwXHsbgqPwY38";
            }} else {{
                amt = document.getElementById('with_amt').value;
                wallet = document.getElementById('with_addr').value;
            }}
            if(!amt || !wallet) return alert('يرجى إكمال البيانات');
            const res = await fetch('/transaction', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: `u={user}&type=${{type}}&amt=${{amt}}&wallet=${{wallet}}`
            }});
            if(res.ok) alert('تم تقديم الطلب بنجاح');
        }}
    </script></body></html>
    """

@app.post("/update_demo")
async def update_demo(u: str = Form(...), amt: float = Form(...)):
    db_query("UPDATE users SET demo = demo + ? WHERE username=?", (amt, u), commit=True)
    new_bal = db_query("SELECT demo FROM users WHERE username=?", (u,), fetch=True)[0][0]
    return {"new_bal": round(new_bal, 2)}

@app.post("/transaction")
async def transaction(u: str = Form(...), type: str = Form(...), amt: float = Form(...), wallet: str = Form(...)):
    db_query("INSERT INTO transactions (username, type, amt, wallet, status) VALUES (?, ?, ?, ?, 'pending')", (u, type, amt, wallet), commit=True)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import sqlite3
from datetime import datetime
import random
import uuid

app = FastAPI()

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
        (username TEXT PRIMARY KEY, password TEXT, live REAL, demo REAL, role TEXT, status TEXT, session_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, amt REAL, wallet TEXT, status TEXT)''')
    
    # حساب الإدمن الافتراضي
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users VALUES ('admin', 'admin123', 0.0, 10000.0, 'admin', 'active', NULL)")
    conn.commit()
    conn.close()

init_db()

# دالة مساعدة للتعامل مع قاعدة البيانات
def db_query(query, params=(), fetch=False, commit=False):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetch: res = cursor.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# التحقق من الجلسة (للتأمين)
async def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    user = db_query("SELECT username, role, live, demo FROM users WHERE session_id=?", (session_id,), fetch=True)
    return user[0] if user else None

BASE_STYLE = """
<style>
    :root { --gold: #F3BA2F; --bg: #0B0E11; --card: #1E2329; --green: #0ECB81; --red: #F6465D; --gray: #848E9C; --line: #2B3139; --blue: #3498db; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; direction: rtl; overflow-x: hidden; }
    .card { background: var(--card); border-radius: 12px; padding: 15px; border: 1px solid var(--line); margin: 10px; }
    .btn-gold { background: var(--gold); color: black; border: none; padding: 12px; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer; transition: 0.3s; }
    .btn-gold:active { transform: scale(0.95); }
    input { width: 100%; padding: 12px; margin: 8px 0; background: #0B0E11; border: 1px solid #333; color: white; border-radius: 8px; box-sizing: border-box; }
    .nav-bar { position: fixed; bottom: 0; width: 100%; background: var(--card); display: grid; grid-template-columns: repeat(5, 1fr); border-top: 1px solid var(--line); height: 70px; }
    .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--gray); font-size: 10px; text-decoration: none; }
    .nav-item.active { color: var(--gold); }
    .tab { display: none; padding-bottom: 85px; animation: fadeIn 0.4s; }
    .tab.active { display: block; }
    @keyframes fadeIn { from {opacity: 0;} to {opacity: 1;} }
    .bot-log { font-family: monospace; font-size: 11px; background: #000; padding: 10px; border-radius: 5px; height: 100px; overflow-y: auto; margin-top: 10px; color: #0ECB81; text-align: left; direction: ltr; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page(msg: str = ""):
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{BASE_STYLE}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='width:320px; text-align:center;'><h1 style='color:var(--gold); letter-spacing:2px;'>AURA PRO</h1><p style='color:var(--red); font-size:12px;'>{msg}</p><form action='/login' method='post'><input name='username' placeholder='اسم المستخدم' required><input name='password' type='password' placeholder='كلمة المرور' required><button class='btn-gold'>تسجيل الدخول الدؤوب</button></form></div></body></html>"

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    user = db_query("SELECT * FROM users WHERE username=?", (username,), fetch=True)
    if not user:
        # تسجيل مستخدم جديد تلقائياً إذا لم يكن موجوداً
        sid = str(uuid.uuid4())
        db_query("INSERT INTO users VALUES (?, ?, 0.0, 10000.0, 'user', 'active', ?)", (username, password, sid), commit=True)
        response.set_cookie(key="session_id", value=sid)
        return RedirectResponse(url="/dashboard", status_code=303)
    
    if user[0][1] == password:
        sid = str(uuid.uuid4())
        db_query("UPDATE users SET session_id=? WHERE username=?", (sid, username), commit=True)
        response.set_cookie(key="session_id", value=sid)
        target = "/admin_panel" if user[0][4] == 'admin' else "/dashboard"
        return RedirectResponse(url=target, status_code=303)
    
    return RedirectResponse(url="/?msg=بيانات الدخول غير صحيحة", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user_data=Depends(get_current_user)):
    if not user_data: return RedirectResponse(url="/")
    
    username, role, live, demo = user_data
    return f"""
    <html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'>{BASE_STYLE}</head>
    <body>
    <div style='padding:15px; background:var(--card); display:flex; justify-content:space-between; border-bottom:1px solid var(--line);'>
        <span style='color:var(--gold); font-weight:bold;'>AURA PRO <small style='font-size:8px; color:gray;'>SECURED</small></span>
        <span style='font-size:12px;'>{username} <i class='fas fa-shield-alt' style='color:var(--green)'></i></span>
    </div>
    
    <div id='tab_home' class='tab active'>
        <div class='card' style='text-align:center;'>
            <small style='color:var(--gray)'>إجمالي الرصيد (تجريبي)</small>
            <h1 style='color:var(--gold); margin:5px 0;'>$<span id='demo_bal'>{demo:,.2f}</span></h1>
        </div>
        <div class='card' style='background: linear-gradient(45deg, #1e2329, #2b3139);'>
            <small>الحساب الحقيقي</small>
            <h3 style='margin:5px 0;'>${live:,.2f}</h3>
            <button class='btn-gold' style='padding:5px; font-size:12px; width:80px;' onclick="showTab('tab_wallet')">إيداع</button>
        </div>
    </div>

    <div id='tab_trade' class='tab'>
        <div class='card' style='text-align:center;'>
            <div id='bot_status' style='color:var(--gray); font-size:12px; margin-bottom:10px;'>بوت الذكاء الاصطناعي جاهز</div>
            <i class='fas fa-robot' id='robot_icon' style='font-size:60px; color:var(--gold); transition: 0.5s;'></i>
            <h2 id='pnl_display' style='margin:15px 0;'>$0.00</h2>
            <button class='btn-gold' id='startBotBtn' onclick='startAuraBot()'>تنشيط Aura Bot v2.0</button>
            <div class='bot-log' id='bot_log'>Waiting for activation...</div>
        </div>
    </div>

    <div id='tab_wallet' class='tab'>
        <div class='card'>
            <h4>محفظة الإيداع</h4>
            <p style='font-size:11px; color:var(--gray);'>USDT (TRC20):</p>
            <code style='display:block; background:#000; padding:10px; color:var(--gold); border-radius:5px;'>THL8B6chNcr8L7Z7Ut7AGBwXHsbgqPwY38</code>
            <input id='amt' type='number' placeholder='المبلغ'>
            <button class='btn-gold' onclick='alert("تم إرسال الطلب للمراجعة")'>تأكيد الإيداع</button>
        </div>
    </div>

    <div class='nav-bar'>
        <div class='nav-item active' onclick="showTab('tab_home', this)"><i class='fas fa-chart-pie'></i>الرئيسية</div>
        <div class='nav-item' onclick="showTab('tab_trade', this)"><i class='fas fa-robot'></i>تداول AI</div>
        <div class='nav-item' onclick="showTab('tab_wallet', this)"><i class='fas fa-wallet'></i>المحفظة</div>
        <div class='nav-item' onclick="location.href='/logout'"><i class='fas fa-sign-out-alt'></i>خروج</div>
    </div>

    <script>
        function showTab(id, el) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) {{
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                el.classList.add('active');
            }}
        }}

        async function startAuraBot() {{
            const btn = document.getElementById('startBotBtn');
            const log = document.getElementById('bot_log');
            const pnl = document.getElementById('pnl_display');
            const icon = document.getElementById('robot_icon');
            
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.innerText = "البوت قيد التحليل...";
            icon.style.color = '#0ECB81';

            setInterval(async () => {{
                const pairs = ['BTC/USDT', 'XAU/USD', 'ETH/USDT', 'SOL/USDT'];
                const pair = pairs[Math.floor(Math.random()*pairs.length)];
                log.innerHTML += `> Analyzing ${{pair}} market...\\n`;
                log.scrollTop = log.scrollHeight;

                setTimeout(async () => {{
                    let profit = (Math.random() * 40 - 12).toFixed(2);
                    let color = profit >= 0 ? '#0ECB81' : '#F6465D';
                    log.innerHTML += `<span style="color:${{color}}">> Trade Closed: ${{profit >=0 ? '+':''}}${{profit}}$</span>\\n`;
                    pnl.innerText = (profit >= 0 ? "+" : "") + "$" + profit;
                    pnl.style.color = color;

                    const res = await fetch('/update_balance', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                        body: `amt=${{profit}}`
                    }});
                    if(res.ok) {{
                        const data = await res.json();
                        document.getElementById('demo_bal').innerText = data.new_bal.toLocaleString();
                    }}
                }}, 1500);
            }}, 4000);
        }}
    </script>
    </body></html>
    """

@app.post("/update_balance")
async def update_balance(amt: float = Form(...), user_data=Depends(get_current_user)):
    if not user_data: return { "error": "unauthorized" }
    db_query("UPDATE users SET demo = demo + ? WHERE username=?", (amt, user_data[0]), commit=True)
    new_bal = db_query("SELECT demo FROM users WHERE username=?", (user_data[0],), fetch=True)[0][0]
    return {"new_bal": round(new_bal, 2)}

@app.get("/logout")
async def logout(response: Response):
    response.delete_cookie("session_id")
    return RedirectResponse(url="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

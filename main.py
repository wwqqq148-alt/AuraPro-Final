from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import sqlite3
from datetime import datetime
import random
import uuid

app = FastAPI()

# --- دالة الإصلاح التلقائي لقاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # إنشاء الجداول إذا لم تكن موجودة
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
        (username TEXT PRIMARY KEY, password TEXT, live REAL, demo REAL, role TEXT, status TEXT, session_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, amt REAL, wallet TEXT, status TEXT)''')
    
    # فحص إذا كان عمود session_id موجوداً، إذا لم يكن موجوداً يتم إضافته (إصلاح الخطأ)
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'session_id' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN session_id TEXT")
    
    # التأكد من وجود حساب الإدمن
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users VALUES ('admin', 'admin123', 0.0, 10000.0, 'admin', 'active', NULL)")
    
    conn.commit()
    conn.close()

# تشغيل الإصلاح فور تشغيل الكود
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

async def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id: return None
    user = db_query("SELECT username, role, live, demo FROM users WHERE session_id=?", (session_id,), fetch=True)
    return user[0] if user else None

BASE_STYLE = """
<style>
    :root { --gold: #F3BA2F; --bg: #0B0E11; --card: #1E2329; --green: #0ECB81; --red: #F6465D; --gray: #848E9C; --line: #2B3139; --blue: #3498db; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; margin: 0; direction: rtl; }
    .card { background: var(--card); border-radius: 12px; padding: 15px; border: 1px solid var(--line); margin: 10px; }
    .btn-gold { background: var(--gold); color: black; border: none; padding: 12px; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer; }
    input { width: 100%; padding: 12px; margin: 8px 0; background: #0B0E11; border: 1px solid #333; color: white; border-radius: 8px; box-sizing: border-box; }
    .nav-bar { position: fixed; bottom: 0; width: 100%; background: var(--card); display: grid; grid-template-columns: repeat(4, 1fr); border-top: 1px solid var(--line); height: 70px; }
    .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--gray); font-size: 10px; text-decoration: none; cursor:pointer; }
    .nav-item.active { color: var(--gold); }
    .tab { display: none; padding-bottom: 85px; }
    .tab.active { display: block; }
    .bot-log { font-family: monospace; font-size: 11px; background: #000; padding: 10px; border-radius: 5px; height: 100px; overflow-y: auto; margin-top: 10px; color: #0ECB81; text-align: left; direction: ltr; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page(msg: str = ""):
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{BASE_STYLE}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='width:320px; text-align:center;'><h1 style='color:var(--gold)'>AURA PRO</h1><p style='color:var(--red); font-size:12px;'>{msg}</p><form action='/login' method='post'><input name='username' placeholder='اسم المستخدم' required><input name='password' type='password' placeholder='كلمة المرور' required><button class='btn-gold'>دخول آمن</button></form></div></body></html>"

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    user = db_query("SELECT * FROM users WHERE username=?", (username,), fetch=True)
    sid = str(uuid.uuid4())
    if not user:
        db_query("INSERT INTO users VALUES (?, ?, 0.0, 10000.0, 'user', 'active', ?)", (username, password, sid), commit=True)
    elif user[0][1] == password:
        db_query("UPDATE users SET session_id=? WHERE username=?", (sid, username), commit=True)
    else:
        return RedirectResponse(url="/?msg=خطأ في البيانات", status_code=303)
    
    response.set_cookie(key="session_id", value=sid)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user_data=Depends(get_current_user)):
    if not user_data: return RedirectResponse(url="/")
    username, role, live, demo = user_data
    return f"""
    <html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'>{BASE_STYLE}</head>
    <body>
    <div style='padding:15px; background:var(--card); display:flex; justify-content:space-between;'>
        <span style='color:var(--gold); font-weight:bold;'>AURA PRO v2</span>
        <span style='font-size:12px;'>{username} <i class='fas fa-check-circle' style='color:var(--green)'></i></span>
    </div>
    
    <div id='tab_home' class='tab active'>
        <div class='card' style='text-align:center;'>
            <small>الرصيد التجريبي</small><h1 style='color:var(--gold)'>$<span id='demo_bal'>{demo:,.2f}</span></h1>
        </div>
        <div class='card'><h4>توصيات اليوم</h4><p style='font-size:12px;'>الذهب في منطقة شراء قوية حسب مؤشر RSI.</p></div>
    </div>

    <div id='tab_trade' class='tab'>
        <div class='card' style='text-align:center;'>
            <i class='fas fa-robot' style='font-size:50px; color:var(--gold);'></i>
            <h3>Aura AI Bot</h3>
            <h2 id='pnl_display'>$0.00</h2>
            <button class='btn-gold' id='startBtn' onclick='startAuraBot()'>تفعيل التداول الذكي</button>
            <div class='bot-log' id='bot_log'>Ready...</div>
        </div>
    </div>

    <div class='nav-bar'>
        <div class='nav-item active' onclick="showTab('tab_home', this)"><i class='fas fa-home'></i>الرئيسية</div>
        <div class='nav-item' onclick="showTab('tab_trade', this)"><i class='fas fa-robot'></i>تداول AI</div>
        <div class='nav-item' onclick="location.href='/logout'"><i class='fas fa-sign-out-alt'></i>خروج</div>
    </div>

    <script>
        function showTab(id, el) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            el.classList.add('active');
        }}
        async function startAuraBot() {{
            const btn = document.getElementById('startBtn');
            btn.disabled = true; btn.style.opacity = '0.5';
            setInterval(async () => {{
                let profit = (Math.random() * 30 - 10).toFixed(2);
                document.getElementById('bot_log').innerHTML += `> Trade Closed: ${{profit}}$\\n`;
                document.getElementById('pnl_display').innerText = "$" + profit;
                const res = await fetch('/update_balance', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-form-urlencoded'}},
                    body: `amt=${{profit}}`
                }});
                if(res.ok) {{
                    const data = await res.json();
                    document.getElementById('demo_bal').innerText = data.new_bal.toLocaleString();
                }}
            }}, 3000);
        }}
    </script></body></html>
    """

@app.post("/update_balance")
async def update_balance(amt: float = Form(...), user_data=Depends(get_current_user)):
    if not user_data: return { "error": "auth" }
    db_query("UPDATE users SET demo = demo + ? WHERE username=?", (amt, user_data[0]), commit=True)
    new_bal = db_query("SELECT demo FROM users WHERE username=?", (user_data[0],), fetch=True)[0][0]
    return {"new_bal": round(new_bal, 2)}

@app.get("/logout")
async def logout(response: Response):
    response.delete_cookie("session_id")
    return RedirectResponse(url="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

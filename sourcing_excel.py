import os, re, time, urllib.parse, requests, openpyxl
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

DOMEGGOOK_API_KEY = "3bfcee5f993d647457412bf50e9d2793"
OWNERCLAN_ID, OWNERCLAN_PW = "ynayow", ""       # 오너클랜 비번 입력
ONCHANNEL_ID, ONCHANNEL_PW = "ynayow@gmail.com", ""  # 온채널 비번 입력

def get_folder():
    d = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    if not os.path.exists(d): d = os.path.join(os.path.expanduser("~"), "Desktop")
    p = os.path.join(d, "도매매소싱"); os.makedirs(p, exist_ok=True); return p

def create_driver():
    opt = Options()
    for a in ["--no-sandbox", "--disable-dev-shm-usage", "--log-level=3", "--window-size=1280,900", "--disable-blink-features=AutomationControlled"]: opt.add_argument(a)
    opt.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    drv.set_page_load_timeout(15); return drv

def login_seller_tabs(drv):
    # 1. 첫 번째 탭에서 온채널 로그인
    if ONCHANNEL_ID and ONCHANNEL_PW:
        try:
            drv.get("https://www.onch3.co.kr/"); time.sleep(1.5)
            ins = drv.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email']")
            pws = drv.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if ins and pws:
                ins[0].clear(); ins[0].send_keys(ONCHANNEL_ID)
                pws[0].clear(); pws[0].send_keys(ONCHANNEL_PW); pws[0].submit(); time.sleep(2.0)
        except Exception: pass
    
    # 2. 두 번째 새 탭을 열어서 오너클랜 로그인 (탭 유지!)
    if OWNERCLAN_ID and OWNERCLAN_PW:
        try:
            drv.execute_script("window.open('https://ownerclan.com/V2/member/login_seller.php', '_blank');")
            time.sleep(1.5)
            drv.switch_to.window(drv.window_handles[-1])
            if "404" in drv.title or "찾을 수" in drv.page_source:
                drv.get("https://ownerclan.com/"); time.sleep(1.5)
                for a in drv.find_elements(By.TAG_NAME, "a"):
                    if "판매사" in (a.text or "") and "로그인" in (a.text or ""): a.click(); time.sleep(1.5); break
            ins = drv.find_elements(By.CSS_SELECTOR, "input[type='text']")
            pws = drv.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if ins and pws:
                ins[0].clear(); ins[0].send_keys(OWNERCLAN_ID)
                pws[0].clear(); pws[0].send_keys(OWNERCLAN_PW); pws[0].submit(); time.sleep(2.0)
        except Exception: pass
    drv.switch_to.window(drv.window_handles[0])

def fetch_web(drv, src, url, pat, p_pat):
    out, seen = [], set()
    try:
        drv.get(url); time.sleep(2.5)
        blocks = re.split(pat, drv.find_element(By.TAG_NAME, "body").text)
        for i in range(1, len(blocks) - 1, 2):
            code = blocks[i].strip()
            if code in seen: continue
            chunk = blocks[i + 1]; pm = re.search(p_pat, chunk)
            price = int((pm.group(1) or pm.group(2)).replace(",", "")) if (pm and pm.lastindex and pm.lastindex >= 2) else (int(pm.group(1).replace(",", "")) if pm else 0)
            lines = [ln.strip() for ln in chunk.splitlines() if ln.strip() and "판매사가" not in ln and "가격자율" not in ln and not ln.startswith("★") and len(ln.strip()) > 3]
            if lines and price > 0:
                seen.add(code)
                link = f"https://ownerclan.com/V2/product/view.php?selfcode={code}" if src == "오너클랜" else url
                out.append({"source": src, "no": code, "title": lines[0][:60], "price": price, "url": link})
            if len(out) >= 30: break
    except Exception: pass
    return out
def get_market(drv, title, kw):
    c = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}|【.*?】|[^가-힣a-zA-Z0-9\s]', ' ', title)
    noise = {"무료배송","무배","당일발송","당일출고","특가","할인","증정","사은품","국내배송","정품","대용량","탕비실","사무실","간식","음료","선물세트","답례품","업소용","가정용","추천","인기"}
    words = [w for w in c.split() if len(w) > 1 and w not in noise]
    qty = [w for w in words if re.search(r'\d+(T|t|개|입|박스|팩|포|병|캔|g|ml|kg)', w)]
    core = [w for w in words if w not in qty and not w.isdigit()][:3]
    if kw and kw not in " ".join(core): core.append(kw)
    if qty: core.append(qty[0])
    q = " ".join(dict.fromkeys(core)) or kw
    try:
        drv.get(f"https://search.11st.co.kr/Search.tmall?kwd={urllib.parse.quote(q)}&sortCd=NP"); time.sleep(1.2)
        txt = drv.find_element(By.TAG_NAME, "body").text
        cm = re.search(r'(?:전체|검색결과|총)\s*\(?([\d,]+)\)?\s*(?:개|건)?', txt)
        comp = int(cm.group(1).replace(",", "")) if cm else -1
        raw = [int(p.replace(",", "")) for p in re.findall(r'([\d,]{4,9})원', txt) if 5000 <= int(p.replace(",", "")) <= 2000000]
        if raw: sp = sorted(raw[:15]); return sp[len(sp)//4], max(comp, len(raw)), q
    except Exception: pass
    return 0, 0, q

def fetch_domeme(kw):
    res = requests.get("https://domeggook.com/ssl/api/", params={"ver":"4.1","mode":"getItemList","aid":DOMEGGOOK_API_KEY,"market":"supply","om":"json","kw":kw,"sz":30}, timeout=10).json()
    items = res.get("domeggook", {}).get("list", {}).get("item", [])
    if isinstance(items, dict): items = [items]
    out = []
    for it in items:
        no, title = str(it.get("no","")).strip(), str(it.get("title","")).strip()
        try: p = int(str(it.get("price","0")).split("~")[0].replace(",","").strip())
        except Exception: p = 0
        if no and p > 0: out.append({"source":"도매매","no":no,"title":title,"price":p,"url":f"https://domeme.domeggook.com/s/{no}"})
    return out

def save_excel(kw, items, drv):
    fname = f"{datetime.now().strftime('%Y%m%d')}_3사통합_소싱시세경쟁분석.xlsx"
    fpath = os.path.join(get_folder(), fname); exists = os.path.exists(fpath)
    try:
        wb = openpyxl.load_workbook(fpath) if exists else openpyxl.Workbook()
        if not exists: wb.active.title = "__tmp__"
    except PermissionError: return False, 0, fpath, fname
    sname = re.sub(r'[\\/*?:\[\]]', "", kw)[:30] or "검색결과"
    if sname in wb.sheetnames: del wb[sname]
    ws = wb.create_sheet(title=sname)
    if "__tmp__" in wb.sheetnames: del wb["__tmp__"]
    headers = ["순위","도매처","상품번호","상품명","시세검색어","공급가(원)","최소목표가(20%)","적정목표가(30%)","최대목표가(40%)","예상순수익(30%)","시중최저가","경쟁상품수","소싱판정","상세페이지 링크"]
    ws.append(headers)
    for c in range(1, 15):
        cell = ws.cell(row=1, column=c)
        cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        cell.font = Font(color="FFFFFF", bold=True); cell.alignment = Alignment(horizontal="center")
    cands = [it for it in items if int(round((it["price"] / 0.60), -2)) >= 8000]
    print(f" -> 8,000원 이상 조건 충족 {len(cands)}개 분석 중...")
    rows = []
    for idx, it in enumerate(cands, 1):
        sp = it["price"]
        p20, p30, p40 = int(round((sp/0.70),-2)), int(round((sp/0.60),-2)), int(round((sp/0.50),-2))
        profit = p30 - sp - int(p30 * 0.1)
        m_low, comp, uq = get_market(drv, it["title"], kw)
        print(f"    [{idx}/{len(cands)}] ({it['source']}) [{uq}] -> {m_low:,}원 / 경쟁:{comp:,}개")
        pri, v, col = (1, "★최적소싱(고마진/저경쟁)", "008000") if (m_low > 0 and m_low >= p30 and 0 < comp <= 500) else ((2, "소싱가능(20~30%마진)", "004C99") if (m_low > 0 and m_low >= p20) else ((3, "미등록/직접확인", "555555") if m_low == 0 else (4, "역마진주의(시세낮음)", "CC0000")))
        rows.append((pri, -profit, it, uq, sp, p20, p30, p40, profit, m_low, comp, v, col))
    rows.sort(key=lambda x: (x[0], x[1]))
    scol = {"도매매":"004C99","오너클랜":"008000","온채널":"800080"}
    for rk, (_, _, it, uq, sp, p20, p30, p40, profit, m_low, comp, v, col) in enumerate(rows, 1):
        ws.append([rk, it["source"], it["no"], it["title"], uq, sp, p20, p30, p40, profit, m_low if m_low > 0 else "조회없음", comp, v, it["url"]])
        r = ws.max_row
        ws.cell(row=r, column=2).font = Font(color=scol.get(it["source"],"000000"), bold=True)
        ws.cell(row=r, column=13).font = Font(color=col, bold=True)
        ws.cell(row=r, column=14).hyperlink = it["url"]; ws.cell(row=r, column=14).font = Font(color="0000FF", underline="single")
        for c in [6,7,8,9,10,11,12]:
            if isinstance(ws.cell(row=r, column=c).value, int): ws.cell(row=r, column=c).number_format = "#,##0"
    for i, w in enumerate([6,10,14,38,22,12,15,15,15,15,13,12,24,40], 1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    wb.active = ws
    try: wb.save(fpath); return True, len(rows), fpath, fname
    except PermissionError: return False, 0, fpath, fname

def main():
    last = None
    print("=================================================================\n [제비] 3사 통합 소싱기 (도매매 + 오너클랜 + 온채널)\n=================================================================")
    drv = create_driver()
    login_seller_tabs(drv)
    try:
        while True:
            kw = input("\n검색할 상품 키워드 (엑셀 열려면 그냥 Enter): ").strip()
            if not kw:
                if last and os.path.exists(last): os.startfile(last)
                break
            items = []
            try: d = fetch_domeme(kw); items.extend(d); print(f" -> 도매매 {len(d)}개 수신")
            except Exception as e: print(f" -> [도매매 오류] {e}")
            o = fetch_web(drv, "오너클랜", f"https://ownerclan.com/V2/product/search.php?search_word={urllib.parse.quote(kw)}", r'(W[A-Z0-9]{6,})', r'([\d,]{3,8})\s*원'); items.extend(o); print(f" -> 오너클랜 {len(o)}개 수신")
            c = fetch_web(drv, "온채널", f"https://www.onch3.co.kr/dbcenter_renewal/index.php?keyword={urllib.parse.quote(kw)}", r'(CH\d{5,})', r'판매사가\s*([\d,]+)\s*원|([\d,]{3,8})\s*원'); items.extend(c); print(f" -> 온채널 {len(c)}개 수신")
            if not items: continue
            ok, cnt, fp, fn = save_excel(kw, items, drv)
            if ok: last = fp; print(f"[완료!] '{fn}' [{kw}] 시트에 {cnt}개 저장됨!")
            else: print(f"[주의!] 열려 있는 '{fn}' 엑셀 창을 닫고 다시 입력해 주세요.")
    finally: drv.quit()

if __name__ == "__main__":
    main()
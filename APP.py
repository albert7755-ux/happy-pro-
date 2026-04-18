import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.optimize import minimize
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import json
import requests
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import os

st.set_page_config(page_title="最適投資組合優化器", layout="wide", page_icon="📐")

# ==========================================
# 登入
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 系統登入")
    st.markdown("請輸入授權碼以存取投資組合優化功能。")
    password = st.text_input("請輸入系統密碼", type="password")
    if password:
        if password == "5428":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密碼錯誤，請重新輸入。")
    st.stop()

# ==========================================
# 常數
# ==========================================
RISK_FREE_RATE = 0.04
BOND_FOLDER_ID = "1k0RxJn5KKCTWdTEDZqq0Q5hnfwkuPgGK"
FUND_FOLDER_ID = "1i1-zUzLNnuwo2NVWijubvBICLbladZQO"
CUTOFF_YEAR = datetime.now().year + 15  # 15年以上用VCLT，以下用LQD

LOCAL_DB = {
    "US02079KBP12": {"issuer": "Alphabet公司債6", "coupon": 5.65, "maturity": "2056"},
    "US30303MAE21": {"issuer": "Meta公司債9", "coupon": 5.625, "maturity": "2055"},
    "US64110LBA35": {"issuer": "網飛公司債3", "coupon": 5.4, "maturity": "2054"},
    "US03769MAC01": {"issuer": "阿波羅公司債1", "coupon": 5.8, "maturity": "2054"},
    "US191216DS69": {"issuer": "可口可樂公司債5", "coupon": 5.3, "maturity": "2054"},
    "US92343VGW81": {"issuer": "威瑞森電信債12", "coupon": 5.5, "maturity": "2054"},
    "XS2747599509": {"issuer": "沙烏地阿拉伯債7", "coupon": 5.75, "maturity": "2054"},
    "US29736RAU41": {"issuer": "雅詩蘭黛公司債3", "coupon": 5.15, "maturity": "2053"},
    "US037833EW60": {"issuer": "蘋果公司債14", "coupon": 4.85, "maturity": "2053"},
    "US91324PEW86": {"issuer": "聯合健康集團債9", "coupon": 5.05, "maturity": "2053"},
    "US532457CG18": {"issuer": "禮來公司債1", "coupon": 4.875, "maturity": "2053"},
    "US91324PES74": {"issuer": "聯合健康集團債5", "coupon": 5.875, "maturity": "2053"},
    "US459200KZ37": {"issuer": "IBM公司債4", "coupon": 5.1, "maturity": "2053"},
    "US459200KV23": {"issuer": "IBM公司債1", "coupon": 4.9, "maturity": "2052"},
    "US45866FAX24": {"issuer": "洲際交易所債1", "coupon": 4.95, "maturity": "2052"},
    "US872898AJ06": {"issuer": "TSMC公司債4", "coupon": 4.5, "maturity": "2052"},
    "US084664DB47": {"issuer": "波克夏金融債2", "coupon": 3.85, "maturity": "2052"},
    "US92343VGP31": {"issuer": "威瑞森電信債11", "coupon": 3.875, "maturity": "2052"},
    "US828807DJ39": {"issuer": "賽門房地產債1", "coupon": 3.8, "maturity": "2050"},
    "US191216CQ13": {"issuer": "可口可樂公司債2", "coupon": 4.2, "maturity": "2050"},
    "US92343VFD10": {"issuer": "威瑞森電信債9", "coupon": 4.0, "maturity": "2050"},
    "US92556HAC16": {"issuer": "維康公司債3", "coupon": 4.95, "maturity": "2050"},
    "US31428XCA28": {"issuer": "聯邦快遞公司債1", "coupon": 5.25, "maturity": "2050"},
    "US09062XAG88": {"issuer": "生物基因公司債2", "coupon": 3.15, "maturity": "2050"},
    "US37045VAT70": {"issuer": "通用汽車公司債7", "coupon": 5.95, "maturity": "2049"},
    "US254687FM36": {"issuer": "迪士尼公司債2", "coupon": 2.75, "maturity": "2049"},
    "XS1982116136": {"issuer": "沙烏地阿拉伯石油債4", "coupon": 4.375, "maturity": "2049"},
    "US58933YAW57": {"issuer": "默克藥廠公司債1", "coupon": 4.0, "maturity": "2049"},
    "US854502AJ02": {"issuer": "史丹利百得公司債3", "coupon": 4.85, "maturity": "2048"},
    "US125523AK66": {"issuer": "信諾公司債1", "coupon": 4.9, "maturity": "2048"},
    "US88579YBD22": {"issuer": "3M公司債1", "coupon": 4.0, "maturity": "2048"},
    "US084664CQ25": {"issuer": "波克夏海瑟威債1", "coupon": 4.2, "maturity": "2048"},
    "XS1807174559": {"issuer": "卡達政府國際債1", "coupon": 5.103, "maturity": "2048"},
    "US00206RCU41": {"issuer": "AT&T公司債12", "coupon": 5.65, "maturity": "2047"},
    "US023135BJ40": {"issuer": "亞馬遜公司債1", "coupon": 4.05, "maturity": "2047"},
    "US375558BK80": {"issuer": "吉利德科學債1", "coupon": 4.15, "maturity": "2047"},
    "US037833CH12": {"issuer": "蘋果公司債6", "coupon": 4.25, "maturity": "2047"},
    "US94974BGU89": {"issuer": "富國銀行公司債10", "coupon": 4.75, "maturity": "2046"},
    "US172967KR13": {"issuer": "花旗集團公司債14", "coupon": 4.75, "maturity": "2046"},
    "US00206RCQ39": {"issuer": "AT&T公司債5", "coupon": 4.75, "maturity": "2046"},
    "US002824BH26": {"issuer": "亞培公司債2", "coupon": 4.9, "maturity": "2046"},
    "XS1508675508": {"issuer": "沙烏地阿拉伯政府債5", "coupon": 4.5, "maturity": "2046"},
    "US02209SAV51": {"issuer": "高特利集團債1", "coupon": 3.875, "maturity": "2046"},
    "US92343VCK89": {"issuer": "威瑞森電信債1", "coupon": 4.862, "maturity": "2046"},
    "US594918BT09": {"issuer": "微軟公司債2", "coupon": 3.7, "maturity": "2046"},
    "US125523CF53": {"issuer": "信諾公司債2", "coupon": 4.8, "maturity": "2046"},
    "US20030NBU46": {"issuer": "康卡斯特公司債1", "coupon": 3.4, "maturity": "2046"},
    "US375558BD48": {"issuer": "吉利德科學債2", "coupon": 4.75, "maturity": "2046"},
    "US02079KBN63": {"issuer": "Alphabet公司債5", "coupon": 5.5, "maturity": "2046"},
    "US58013MFA71": {"issuer": "麥當勞公司債2", "coupon": 4.875, "maturity": "2045"},
    "US42824CAY57": {"issuer": "慧與公司債1", "coupon": 6.35, "maturity": "2045"},
    "US09062XAD57": {"issuer": "生物基因公司債1", "coupon": 5.2, "maturity": "2045"},
    "US37045VAJ98": {"issuer": "通用汽車公司債4", "coupon": 5.2, "maturity": "2045"},
    "US61747YDY86": {"issuer": "摩根士丹利債20", "coupon": 4.3, "maturity": "2045"},
    "US30303M8X35": {"issuer": "Meta公司債10", "coupon": 5.5, "maturity": "2045"},
    "US747525AK99": {"issuer": "高通公司債3", "coupon": 4.8, "maturity": "2045"},
    "US94974BGE48": {"issuer": "富國銀行債9", "coupon": 4.65, "maturity": "2044"},
    "US172967HS33": {"issuer": "花旗集團債12", "coupon": 5.3, "maturity": "2044"},
    "XS1049699926": {"issuer": "渣打集團債6", "coupon": 5.7, "maturity": "2044"},
    "US404280AQ21": {"issuer": "匯豐控股債8", "coupon": 5.25, "maturity": "2044"},
    "US25468PDB94": {"issuer": "迪士尼公司債3", "coupon": 4.125, "maturity": "2044"},
    "US717081DK61": {"issuer": "輝瑞藥廠債2", "coupon": 4.4, "maturity": "2044"},
    "US449276AF17": {"issuer": "IBM金融債1", "coupon": 5.25, "maturity": "2044"},
    "US02209SAR40": {"issuer": "高特利集團債2", "coupon": 5.375, "maturity": "2044"},
    "US37045VAF76": {"issuer": "通用汽車公司債3", "coupon": 6.25, "maturity": "2043"},
    "US92553PAP71": {"issuer": "維康公司債2", "coupon": 4.375, "maturity": "2043"},
    "US12572QAF28": {"issuer": "芝加哥期交所債1", "coupon": 5.3, "maturity": "2043"},
    "US037833AL42": {"issuer": "蘋果公司債2", "coupon": 3.85, "maturity": "2043"},
    "US084670BK32": {"issuer": "波克夏公司債1", "coupon": 4.5, "maturity": "2043"},
    "US00206RBH49": {"issuer": "AT&T公司債1", "coupon": 4.3, "maturity": "2042"},
    "US71568QAB32": {"issuer": "印尼國家電力債2", "coupon": 5.25, "maturity": "2042"},
    "US854502AA92": {"issuer": "史丹利百得公司債2", "coupon": 5.2, "maturity": "2040"},
    "US50076QAN60": {"issuer": "卡夫亨氏公司債1", "coupon": 6.5, "maturity": "2040"},
    "XS2885079702": {"issuer": "國泰人壽公司債2", "coupon": 5.3, "maturity": "2039"},
    "US46625HHF01": {"issuer": "摩根大通銀行債3", "coupon": 6.4, "maturity": "2038"},
    "US37045VAP58": {"issuer": "通用汽車公司債2", "coupon": 5.15, "maturity": "2038"},
    "US126650CY46": {"issuer": "CVS公司債1", "coupon": 4.78, "maturity": "2038"},
    "US38141GFD16": {"issuer": "高盛公司債14", "coupon": 6.75, "maturity": "2037"},
    "US00206RDR03": {"issuer": "AT&T公司債3", "coupon": 5.25, "maturity": "2037"},
    "US594918BZ68": {"issuer": "微軟公司債7", "coupon": 4.1, "maturity": "2037"},
    "US404280AG49": {"issuer": "匯豐銀行公司債4", "coupon": 6.5, "maturity": "2036"},
    "US38143YAC75": {"issuer": "高盛證券公司債16", "coupon": 6.45, "maturity": "2036"},
    "US925524AX89": {"issuer": "維康公司債1", "coupon": 6.875, "maturity": "2036"},
    "US37045VAK61": {"issuer": "通用汽車公司債1", "coupon": 6.6, "maturity": "2036"},
    "XS3151416727": {"issuer": "富邦人壽(新加坡)1", "coupon": 5.45, "maturity": "2035"},
    "US06051GLU12": {"issuer": "美國銀行公司債6", "coupon": 5.872, "maturity": "2034"},
    "XS2852920342": {"issuer": "國泰人壽公司債1", "coupon": 5.95, "maturity": "2034"},
    "US717081EC37": {"issuer": "輝瑞藥廠債1", "coupon": 4.0, "maturity": "2036"},
    "US035242AM81": {"issuer": "百威英博債2", "coupon": 4.7, "maturity": "2036"},
    "US91159HJN17": {"issuer": "美國合眾銀債2", "coupon": 5.836, "maturity": "2034"},
    "US55608KBG94": {"issuer": "麥格理集團債10", "coupon": 5.491, "maturity": "2033"},
    "US686330AR22": {"issuer": "歐力士公司債2", "coupon": 5.2, "maturity": "2032"},
    "USG91139AL26": {"issuer": "TSMC全球債6", "coupon": 4.625, "maturity": "2032"},
    "US458140CA64": {"issuer": "英特爾公司債5", "coupon": 4.15, "maturity": "2032"},
}

FUND_DB = {
    "F00001DRQQ_FO": "PIMCO收益增長",
    "F0GBR04SG1_FO": "AV04駿利亨德森平衡基金",
    "F00000ZXFV_FO": "施羅德環球收息債券",
    "F00000PR1I_FO": "富達全球優質債券基金",
    "F0000176Y4_FO": "富達永續發展全球存股優勢基金",
    "F000011JGT_FO": "群益潛力收益多重",
    "F0GBR04MRL_FO": "聯博美國收益EA穩定月配",
    "FOGBR05KHT_FO": "PIMCO多元收益",
    "F0000000P6_FO": "貝萊德全球智慧數據股票入息基金",
    "F0GBR04AMK_FO": "貝萊德環球資產配置基金",
    "F00000MLER_FO": "聯博-新興市場多元收益基金",
    "F00000T0K2_FO": "聯博-美國成長基金EP",
    "F00000T1CG_FO": "聯博-優化波動股票基金",
    "F00000V557_FO": "聯博全球多元",
    "F00001EQPP_FO": "富邦台美雙星多重",
}

# ==========================================
# Google Drive 連線
# ==========================================
@st.cache_resource
def get_gspread_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_drive_headers():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    from google.auth.transport.requests import Request
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    creds.refresh(Request())
    return {"Authorization": f"Bearer {creds.token}"}

@st.cache_data(ttl=3600)
def list_sheets_in_folder(folder_id):
    headers = get_drive_headers()
    params = {
        "q": f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        "fields": "files(id, name)",
        "pageSize": 200,
    }
    resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
    return {f["name"]: f["id"] for f in resp.json().get("files", [])}

@st.cache_data(ttl=3600)
def read_sheet_as_series(sheet_id, label):
    client = get_gspread_client()
    sh = client.open_by_key(sheet_id)
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    df = pd.DataFrame(data)

    # 自動偵測日期欄位（第一欄）
    date_col = df.columns[0]
    val_col = df.columns[1]

    # 嘗試解析日期
    try:
        # 先試 Unix timestamp
        df["date"] = pd.to_datetime(df[date_col], unit="s", errors="coerce")
        if df["date"].isna().mean() > 0.5:
            # 大部分失敗，改用字串解析
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    except:
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.sort_values("date").set_index("date")
    return df[val_col].astype(float).rename(label)

# ==========================================
# 核心計算函式
# ==========================================
def total_return_series(price_series, coupon_rate):
    """含息總報酬指數"""
    prices = price_series.values
    daily_coupon = (coupon_rate / 100) / 365
    tri = [100.0]
    for i in range(1, len(prices)):
        price_ret = (prices[i] - prices[i-1]) / prices[i-1]
        tri.append(tri[-1] * (1 + price_ret + daily_coupon))
    return pd.Series(tri, index=price_series.index)

def calc_stats(returns_df):
    """計算年化報酬、標準差、夏普比率"""
    ann_ret = returns_df.mean() * 252
    ann_vol = returns_df.std() * np.sqrt(252)
    sharpe = (ann_ret - RISK_FREE_RATE) / ann_vol
    return ann_ret, ann_vol, sharpe

def run_optimization(returns_df, method="max_sharpe", target_return=0.08):
    n = len(returns_df.columns)
    mean_ret = returns_df.mean() * 252
    cov = returns_df.cov() * 252
    bounds = tuple((0, 1) for _ in range(n))
    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    init = [1/n] * n

    if method == "max_sharpe":
        def neg_sharpe(w):
            r = np.dot(w, mean_ret)
            v = np.sqrt(np.dot(w.T, np.dot(cov, w)))
            return -(r - RISK_FREE_RATE) / v
        res = minimize(neg_sharpe, init, method="SLSQP", bounds=bounds, constraints=constraints)

    elif method == "min_vol":
        def portfolio_vol(w):
            return np.sqrt(np.dot(w.T, np.dot(cov, w)))
        res = minimize(portfolio_vol, init, method="SLSQP", bounds=bounds, constraints=constraints)

    else:  # target_return
        def portfolio_vol(w):
            return np.sqrt(np.dot(w.T, np.dot(cov, w)))
        constraints.append({"type": "eq", "fun": lambda x: np.dot(x, mean_ret) - target_return})
        res = minimize(portfolio_vol, init, method="SLSQP", bounds=bounds, constraints=constraints)

    return res.x

def efficient_frontier(returns_df, n_points=100):
    mean_ret = returns_df.mean() * 252
    cov = returns_df.cov() * 252
    n = len(returns_df.columns)
    bounds = tuple((0, 1) for _ in range(n))

    min_r = mean_ret.min()
    max_r = mean_ret.max()
    target_returns = np.linspace(min_r, max_r, n_points)

    frontier_vols = []
    frontier_rets = []

    for tr in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},
            {"type": "eq", "fun": lambda x, tr=tr: np.dot(x, mean_ret) - tr}
        ]
        res = minimize(
            lambda w: np.sqrt(np.dot(w.T, np.dot(cov, w))),
            [1/n] * n, method="SLSQP", bounds=bounds, constraints=constraints
        )
        if res.success:
            frontier_vols.append(res.fun)
            frontier_rets.append(tr)

    return frontier_vols, frontier_rets

def get_chinese_font():
    font_name = "ChineseFont"
    for path in ["/tmp/wqy_microhei.ttc",
                 "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
            except:
                continue
    try:
        import requests as req
        cache_path = "/tmp/wqy_microhei.ttc"
        url = "https://github.com/anthonyfok/fonts-wqy-microhei/raw/master/wqy-microhei.ttc"
        r = req.get(url, timeout=30)
        with open(cache_path, "wb") as f:
            f.write(r.content)
        pdfmetrics.registerFont(TTFont(font_name, cache_path))
        return font_name
    except:
        return "Helvetica"

def generate_pdf(weights, labels, ann_ret, ann_vol, sharpe, returns_df, port_ret, port_vol, port_sharpe, method_name, period_label):
    buf = io.BytesIO()
    font = get_chinese_font()
    NAVY = colors.HexColor("#1a2744")
    GOLD = colors.HexColor("#c8a84b")
    WHITE = colors.white
    BG   = colors.HexColor("#f0f4ff")
    RED  = colors.HexColor("#c62828")
    GREEN= colors.HexColor("#2e7d32")

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    title_s = ParagraphStyle("t", fontName=font, fontSize=20, textColor=WHITE, alignment=TA_CENTER)
    sub_s   = ParagraphStyle("s", fontName=font, fontSize=10, textColor=colors.HexColor("#cce0ff"), alignment=TA_CENTER)
    h2_s    = ParagraphStyle("h2", fontName=font, fontSize=12, textColor=NAVY, spaceBefore=12, spaceAfter=6)
    body_s  = ParagraphStyle("b", fontName=font, fontSize=9, textColor=colors.HexColor("#333"), spaceAfter=3)
    small_s = ParagraphStyle("sm", fontName=font, fontSize=8, textColor=colors.HexColor("#555"))
    warn_s  = ParagraphStyle("w", fontName=font, fontSize=7.5, textColor=RED,
                             backColor=colors.HexColor("#fff3cd"), borderPadding=6, spaceBefore=8)

    story = []

    # ── 封面標題 ──
    title_tbl = Table(
        [[Paragraph("最適投資組合分析報告", title_s)],
         [Paragraph(f"策略：{method_name}　｜　回測期間：{period_label}　｜　製作日期：{datetime.today().strftime('%Y-%m-%d')}", sub_s)]],
        colWidths=[17*cm]
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), NAVY),
        ("TOPPADDING",   (0,0), (-1,-1), 16),
        ("BOTTOMPADDING",(0,0), (-1,-1), 16),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 0.5*cm))

    # ── 一、整體組合績效 ──
    story.append(Paragraph("一、整體組合預期績效", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))

    # 計算 VaR（常態分配假設）
    var_68 = port_ret - port_vol          # 68%：1σ
    var_95 = port_ret - 1.645 * port_vol  # 95%：1.645σ
    var_99 = port_ret - 2.326 * port_vol  # 99%：2.326σ

    kpi_data = [
        ["指標", "數值", "說明"],
        ["年化報酬率", f"{port_ret:.2%}", "歷史加權平均年化報酬"],
        ["年化波動率", f"{port_vol:.2%}", "報酬率標準差年化"],
        ["夏普比率",   f"{port_sharpe:.2f}", f"(報酬 - 無風險利率{RISK_FREE_RATE:.0%}) / 波動"],
        ["68% 信賴區間", f"{var_68:.2%} ～ {port_ret + port_vol:.2%}", "約有 68% 機率年報酬落在此區間（1σ）"],
        ["95% 信賴區間", f"{var_95:.2%} ～ {port_ret + 1.645*port_vol:.2%}", "約有 95% 機率年報酬落在此區間（1.645σ）"],
        ["99% 信賴區間", f"{var_99:.2%} ～ {port_ret + 2.326*port_vol:.2%}", "約有 99% 機率年報酬落在此區間（2.326σ）"],
    ]
    kpi_tbl = Table(kpi_data, colWidths=[4*cm, 4.5*cm, 8.5*cm])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,-1), font),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [BG, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        # 68/95/99 列字體顏色
        ("TEXTCOLOR", (1,4), (1,6), RED),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "※ 信賴區間基於常態分配假設計算，實際報酬分佈可能有厚尾風險，請審慎參考。", small_s))
    story.append(Spacer(1, 0.4*cm))

    # ── 二、建議配置權重 ──
    story.append(Paragraph("二、建議配置權重", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))

    w_data = [["標的", "配置比例", "年化報酬", "年化波動", "夏普比率"]]
    for i, (lbl, w) in enumerate(zip(labels, weights)):
        if w > 0.001:
            w_data.append([
                lbl,
                f"{w:.1%}",
                f"{ann_ret.iloc[i]:.2%}",
                f"{ann_vol.iloc[i]:.2%}",
                f"{sharpe.iloc[i]:.2f}"
            ])

    w_tbl = Table(w_data, colWidths=[6.5*cm, 2.2*cm, 2.5*cm, 2.5*cm, 2.3*cm])
    w_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,-1), font),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [BG, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(w_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── 三、相關係數矩陣 ──
    story.append(PageBreak())
    story.append(Paragraph("三、相關係數矩陣", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))

    corr = returns_df.corr()
    short_labels = [lbl[:10] for lbl in corr.columns.tolist()]
    corr_header = [""] + short_labels
    corr_rows = [corr_header]
    for i, lbl in enumerate(short_labels):
        row = [lbl]
        for j in range(len(short_labels)):
            val = corr.iloc[i, j]
            row.append(f"{val:.2f}")
        corr_rows.append(row)

    n_cols = len(short_labels) + 1
    col_w = [17*cm / n_cols] * n_cols
    corr_tbl = Table(corr_rows, colWidths=col_w)

    corr_style = [
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("BACKGROUND",    (0,0), (0,-1), NAVY),
        ("TEXTCOLOR",     (0,0), (0,-1), WHITE),
        ("FONTNAME",      (0,0), (-1,-1), font),
        ("FONTSIZE",      (0,0), (-1,-1), 7),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]
    # 高相關（>0.7）紅底，低相關（<0.3）綠底
    for i in range(1, len(corr_rows)):
        for j in range(1, n_cols):
            try:
                val = float(corr_rows[i][j])
                if i != j:
                    if val > 0.7:
                        corr_style.append(("BACKGROUND", (j,i), (j,i), colors.HexColor("#ffcdd2")))
                    elif val < 0.3:
                        corr_style.append(("BACKGROUND", (j,i), (j,i), colors.HexColor("#c8e6c9")))
            except:
                pass

    corr_tbl.setStyle(TableStyle(corr_style))
    story.append(corr_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("※ 紅底=高相關(>0.7)，綠底=低相關(<0.3)。低相關標的有助分散風險。", small_s))

    # ── 免責聲明 ──
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#888"), spaceAfter=6))
    story.append(Paragraph(
        "⚠️ 免責聲明：本報告所有數據均基於歷史資料計算，不代表未來績效。"
        "債券價格資料來源為 TradingView，基金資料來源為台灣 Yahoo 股市，僅供參考，不構成投資建議。"
        "本報告僅供內部教育訓練使用，請勿外流。", warn_s))

    doc.build(story)
    buf.seek(0)

    # 加密 PDF
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(buf)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt("5428")
        enc_buf = io.BytesIO()
        writer.write(enc_buf)
        enc_buf.seek(0)
        return enc_buf
    except:
        buf.seek(0)
        return buf

# ==========================================
# 主介面
# ==========================================
st.markdown("## 📐 最適投資組合優化器")
st.markdown("結合債券（94檔）、基金（15檔）、自選股票/ETF，計算最適配置比例")
st.markdown("---")

# 側邊欄：回測期間 & 優化目標
st.sidebar.header("1. 回測期間")
period_options = {"1年": 1, "2年": 2, "3年": 3, "5年": 5}
period_label = st.sidebar.radio("選擇回測期間", list(period_options.keys()), horizontal=True)
years = period_options[period_label]

st.sidebar.header("2. 優化目標")
method_map = {
    "最大夏普比率": "max_sharpe",
    "最小風險":     "min_vol",
    "鎖定目標報酬": "target_return"
}
method_label = st.sidebar.radio("選擇策略", list(method_map.keys()))
method = method_map[method_label]
target_return = 0.08
if method == "target_return":
    target_return = st.sidebar.slider("目標年化報酬率 %", 1.0, 20.0, 8.0, 0.5) / 100

# 主畫面：兩個 Tab
tab_select, tab_result = st.tabs(["📋 標的選擇", "📊 分析結果"])

with tab_select:
    st.subheader("選擇要納入的標的")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**債券（94檔）**")
        bond_names = {
            f"{v['issuer']} {v['coupon']}% {v['maturity']}": k
            for k, v in LOCAL_DB.items()
        }
        selected_bond_names = st.multiselect(
            "選擇債券（可多選）",
            options=list(bond_names.keys()),
            default=[]
        )
        selected_bonds = [bond_names[n] for n in selected_bond_names]

    with col2:
        st.markdown("**基金（15檔）**")
        selected_funds = st.multiselect(
            "選擇基金（可多選）",
            options=list(FUND_DB.keys()),
            format_func=lambda x: FUND_DB[x],
            default=[]
        )

    with col3:
        st.markdown("**自選股票/ETF**")
        extra_input = st.text_area(
            "輸入代號（每行一個或空白隔開）",
            placeholder="例如：\nAAPL\nTSLA\nSPY",
            height=180
        )
        extra_tickers = [t.strip().upper() for t in extra_input.replace(",", " ").split() if t.strip()]

    total_selected = len(selected_bonds) + len(selected_funds) + len(extra_tickers)
    if total_selected < 2:
        st.warning("請至少選擇 2 個標的！")
    else:
        st.success(f"已選擇 {total_selected} 個標的（債券 {len(selected_bonds)} + 基金 {len(selected_funds)} + 股票/ETF {len(extra_tickers)}）")

    run_btn = st.button("🚀 開始計算最適組合", type="primary",
                        use_container_width=True, disabled=(total_selected < 2))

# ==========================================
# 執行計算
# ==========================================
if "result_ready" not in st.session_state:
    st.session_state.result_ready = False

if run_btn and total_selected >= 2:
    with st.spinner("正在讀取資料並計算中，請稍候..."):
        try:
            end_date   = pd.Timestamp.today()
            start_date = end_date - pd.DateOffset(years=years)

            all_series = {}
            labels = []

            # 1. 債券（含息總報酬）
            if selected_bonds:
                bond_sheets = list_sheets_in_folder(BOND_FOLDER_ID)

                vclt_raw = yf.download("VCLT", start=start_date - pd.DateOffset(years=3),
                                       end=end_date, auto_adjust=True, progress=False)["Close"].squeeze()
                lqd_raw  = yf.download("LQD",  start=start_date - pd.DateOffset(years=3),
                                       end=end_date, auto_adjust=True, progress=False)["Close"].squeeze()
                vclt_ret = vclt_raw.pct_change().dropna()
                lqd_ret  = lqd_raw.pct_change().dropna()

                for isin in selected_bonds:
                    info  = LOCAL_DB[isin]
                    label = info["issuer"]

                    sheet_id = None
                    for sname, sid in bond_sheets.items():
                        if isin in sname:
                            sheet_id = sid
                            break
                    if not sheet_id:
                        st.warning(f"找不到 {label} 的資料，跳過")
                        continue

                    price_s = read_sheet_as_series(sheet_id, label)
                    tri     = total_return_series(price_s, info["coupon"])
                    tri_ret = tri.pct_change().dropna()
                    tri_ret = tri_ret[tri_ret.index >= start_date]

                    maturity_year = int(info["maturity"])
                    proxy_ret   = vclt_ret if maturity_year >= CUTOFF_YEAR else lqd_ret
                    proxy_label = "VCLT"   if maturity_year >= CUTOFF_YEAR else "LQD"

                    if len(tri_ret) < 20:
                        proxy_filtered = proxy_ret[proxy_ret.index >= start_date]
                        all_series[label] = proxy_filtered
                        st.info(f"{label}：資料不足，使用 {proxy_label} 替代")
                    else:
                        first_date = tri_ret.index[0]
                        if first_date > start_date:
                            pre_ret  = proxy_ret[(proxy_ret.index >= start_date) & (proxy_ret.index < first_date)]
                            combined = pd.concat([pre_ret.rename(label), tri_ret])
                        else:
                            combined = tri_ret
                        all_series[label] = combined
                    labels.append(label)

            # 2. 基金
            if selected_funds:
                fund_sheets = list_sheets_in_folder(FUND_FOLDER_ID)
                for ticker in selected_funds:
                    fund_name = FUND_DB[ticker]
                    sheet_id  = fund_sheets.get(ticker)
                    if not sheet_id:
                        st.warning(f"找不到 {fund_name} 的資料，跳過")
                        continue
                    price_s = read_sheet_as_series(sheet_id, fund_name)
                    ret = price_s.pct_change().dropna()
                    ret = ret[ret.index >= start_date]
                    if len(ret) < 20:
                        st.warning(f"{fund_name}：資料不足，跳過")
                        continue
                    all_series[fund_name] = ret
                    labels.append(fund_name)

            # 3. 自選股票/ETF
            if extra_tickers:
                raw = yf.download(extra_tickers, start=start_date, end=end_date,
                                  auto_adjust=True, progress=False)
                prices = raw["Close"] if "Close" in raw.columns else raw
                if isinstance(prices, pd.Series):
                    prices = prices.to_frame(name=extra_tickers[0])
                for ticker in extra_tickers:
                    if ticker in prices.columns:
                        ret = prices[ticker].pct_change().dropna()
                        all_series[ticker] = ret
                        labels.append(ticker)

            if len(all_series) < 2:
                st.error("有效標的不足 2 個，無法計算！")
                st.stop()

            returns_df = pd.DataFrame(all_series).dropna()
            returns_df = returns_df[returns_df.index >= start_date]

            if len(returns_df) < 30:
                st.error("有效交集資料不足 30 天，請換標的或延長期間！")
                st.stop()

            ann_ret, ann_vol, sharpe_r = calc_stats(returns_df)
            weights = run_optimization(returns_df, method=method, target_return=target_return)

            # 組合整體指標
            cov        = returns_df.cov() * 252
            port_ret   = float(np.dot(weights, ann_ret))
            port_vol   = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))
            port_sharpe= (port_ret - RISK_FREE_RATE) / port_vol

            st.session_state.update({
                "result_ready": True,
                "returns_df":   returns_df,
                "ann_ret":      ann_ret,
                "ann_vol":      ann_vol,
                "sharpe_r":     sharpe_r,
                "weights":      weights,
                "labels":       labels,
                "port_ret":     port_ret,
                "port_vol":     port_vol,
                "port_sharpe":  port_sharpe,
                "period_label": period_label,
                "method_label": method_label,
            })

        except Exception as e:
            st.error(f"發生錯誤：{e}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# 顯示結果（全部在同一個 Tab）
# ==========================================
if st.session_state.result_ready:
    returns_df  = st.session_state.returns_df
    ann_ret     = st.session_state.ann_ret
    ann_vol     = st.session_state.ann_vol
    sharpe_r    = st.session_state.sharpe_r
    weights     = st.session_state.weights
    labels      = st.session_state.labels
    port_ret    = st.session_state.port_ret
    port_vol    = st.session_state.port_vol
    port_sharpe = st.session_state.port_sharpe

    with tab_result:

        # ── A. 組合整體績效 KPI ──
        st.subheader(f"最適組合：{st.session_state.method_label}")
        k1, k2, k3 = st.columns(3)
        k1.metric("組合年化報酬", f"{port_ret:.2%}")
        k2.metric("組合年化波動", f"{port_vol:.2%}")
        k3.metric("組合夏普比率", f"{port_sharpe:.2f}")

        # VaR 說明
        var_68 = port_ret - port_vol
        var_95 = port_ret - 1.645 * port_vol
        var_99 = port_ret - 2.326 * port_vol
        st.markdown(f"""
        | 信賴區間 | 最差情境 | 最佳情境 | 說明 |
        |---|---|---|---|
        | **68%（1σ）** | {var_68:.2%} | {port_ret + port_vol:.2%} | 約 1/3 機率超出此範圍 |
        | **95%（1.645σ）** | {var_95:.2%} | {port_ret + 1.645*port_vol:.2%} | 約 1/20 機率超出此範圍 |
        | **99%（2.326σ）** | {var_99:.2%} | {port_ret + 2.326*port_vol:.2%} | 約 1/100 機率超出此範圍 |
        """)
        st.caption("※ 基於常態分配假設，實際分佈可能有厚尾風險")

        st.markdown("---")

        # ── B. 各標的統計表 + 圓餅圖 ──
        left_col, right_col = st.columns([3, 2])

        with left_col:
            st.markdown("**各標的統計**")
            stats_data = []
            for i, lbl in enumerate(labels):
                stats_data.append({
                    "標的": lbl,
                    "配置": f"{weights[i]:.1%}",
                    "年化報酬": f"{ann_ret.iloc[i]:.2%}",
                    "年化波動": f"{ann_vol.iloc[i]:.2%}",
                    "夏普": f"{sharpe_r.iloc[i]:.2f}",
                })
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

        with right_col:
            sig_weights = [(lbl, w) for lbl, w in zip(labels, weights) if w > 0.01]
            if sig_weights:
                pie_labels, pie_values = zip(*sig_weights)
                fig_pie = go.Figure(go.Pie(
                    labels=pie_labels, values=pie_values, hole=0.4,
                    textinfo="label+percent"
                ))
                fig_pie.update_layout(height=320, margin=dict(t=10, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")

        # ── C. 有效前緣 ──
        st.markdown("**有效前緣**")
        with st.spinner("計算有效前緣中..."):
            vols, rets = efficient_frontier(returns_df)

        cov = returns_df.cov() * 252
        opt_w_sharpe  = run_optimization(returns_df, method="max_sharpe")
        opt_w_minvol  = run_optimization(returns_df, method="min_vol")
        opt_vol_s = float(np.sqrt(np.dot(opt_w_sharpe.T, np.dot(cov, opt_w_sharpe))))
        opt_ret_s = float(np.dot(opt_w_sharpe, ann_ret))
        opt_vol_m = float(np.sqrt(np.dot(opt_w_minvol.T, np.dot(cov, opt_w_minvol))))
        opt_ret_m = float(np.dot(opt_w_minvol, ann_ret))

        fig_ef = go.Figure()
        fig_ef.add_trace(go.Scatter(x=vols, y=rets, mode="lines",
                                    line=dict(color="#1565c0", width=2.5), name="有效前緣"))
        fig_ef.add_trace(go.Scatter(x=ann_vol.values, y=ann_ret.values,
                                    mode="markers+text", text=labels, textposition="top center",
                                    marker=dict(size=8, color="#888"), name="各標的"))
        fig_ef.add_trace(go.Scatter(x=[opt_vol_s], y=[opt_ret_s], mode="markers",
                                    marker=dict(size=14, color="#c8a84b", symbol="star"),
                                    name="最大夏普"))
        fig_ef.add_trace(go.Scatter(x=[opt_vol_m], y=[opt_ret_m], mode="markers",
                                    marker=dict(size=12, color="#2e7d32", symbol="diamond"),
                                    name="最小風險"))
        fig_ef.update_layout(
            xaxis_title="年化波動率", yaxis_title="年化報酬率",
            hovermode="closest", height=420,
            xaxis=dict(tickformat=".1%"), yaxis=dict(tickformat=".1%")
        )
        st.plotly_chart(fig_ef, use_container_width=True)

        st.markdown("---")

        # ── D. 相關係數矩陣 ──
        st.markdown("**相關係數矩陣**")
        corr = returns_df.corr()
        fig_corr = go.Figure(go.Heatmap(
            z=corr.values,
            x=[l[:10] for l in corr.columns.tolist()],
            y=[l[:10] for l in corr.index.tolist()],
            colorscale="RdYlGn", zmin=-1, zmax=1,
            text=np.round(corr.values, 2),
            texttemplate="%{text}", textfont={"size": 9}
        ))
        fig_corr.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_corr, use_container_width=True)

        st.markdown("---")

        # ── E. 資料明細 ──
        with st.expander("🔍 資料明細（點擊展開）"):
            st.markdown("**各標的資料來源說明**")

            meta_rows = []
            for lbl in labels:
                # 判斷是債券、基金還是股票
                isin = None
                for k, v in LOCAL_DB.items():
                    if v["issuer"] == lbl:
                        isin = k
                        break

                if lbl in returns_df.columns:
                    col_data   = returns_df[lbl].dropna()
                    data_start = col_data.index[0].strftime("%Y-%m-%d")
                    data_end   = col_data.index[-1].strftime("%Y-%m-%d")
                    n_days     = len(col_data)
                else:
                    data_start = data_end = "-"
                    n_days = 0

                if isin:
                    info = LOCAL_DB[isin]
                    maturity_year = int(info["maturity"])
                    proxy = "VCLT（15年以上長債ETF）" if maturity_year >= CUTOFF_YEAR else "LQD（15年以下投資等級ETF）"
                    meta_rows.append({
                        "標的": lbl, "類型": "債券",
                        "ISIN": isin, "到期年": info["maturity"],
                        "票息": f"{info['coupon']}%",
                        "不足時補齊用": proxy,
                        "資料起始": data_start,
                        "資料結束": data_end,
                        "有效交易日": n_days,
                    })
                elif lbl in FUND_DB.values():
                    meta_rows.append({
                        "標的": lbl, "類型": "基金",
                        "ISIN": "-", "到期年": "-",
                        "票息": "-", "不足時補齊用": "-",
                        "資料起始": data_start,
                        "資料結束": data_end,
                        "有效交易日": n_days,
                    })
                else:
                    meta_rows.append({
                        "標的": lbl, "類型": "股票/ETF",
                        "ISIN": "-", "到期年": "-",
                        "票息": "-", "不足時補齊用": "-",
                        "資料起始": data_start,
                        "資料結束": data_end,
                        "有效交易日": n_days,
                    })

            st.dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("**原始日報酬率（最新在上，紅=負報酬 綠=正報酬）**")
            st.caption(f"交集期間：{returns_df.index[0].strftime('%Y-%m-%d')} ～ {returns_df.index[-1].strftime('%Y-%m-%d')}，共 {len(returns_df)} 個交易日")

            display_df = returns_df.copy()
            display_df.index = display_df.index.strftime("%Y-%m-%d")
            display_df = display_df.sort_index(ascending=False)
            st.dataframe(
                display_df.style.format("{:.4%}").background_gradient(
                    cmap="RdYlGn", vmin=-0.03, vmax=0.03
                ),
                use_container_width=True,
                height=400
            )

        st.markdown("---")

        # ── F. 生成 PDF ──
        if st.button("🖨️ 生成 PDF 報告（密碼保護）", type="primary"):
            with st.spinner("生成中..."):
                pdf_buf = generate_pdf(
                    weights, labels, ann_ret, ann_vol, sharpe_r,
                    returns_df, port_ret, port_vol, port_sharpe,
                    st.session_state.method_label,
                    st.session_state.period_label
                )
                st.download_button(
                    "📥 下載 PDF 報告",
                    data=pdf_buf,
                    file_name=f"最適組合_{datetime.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.info("PDF 開啟密碼：**5428**")

st.markdown("---")
st.warning("⚠️ 本工具所有計算均基於歷史資料，不代表未來績效。僅供內部教育訓練使用，請勿外流。")

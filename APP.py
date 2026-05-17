import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta, date
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

st.set_page_config(page_title="債券績效比較", layout="wide", page_icon="📊")

COLORS = ["#1565c0", "#c62828", "#2e7d32", "#6a1b9a", "#e65100", "#00838f"]
LABELS = ["A", "B", "C", "D", "E", "F"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
* { font-family: 'Noto Sans TC', sans-serif; }
.compare-table {
    width: 100%; border-collapse: separate; border-spacing: 0;
    border-radius: 12px; overflow: hidden;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08); font-size: 0.86rem;
}
.compare-table th {
    background: #1a2744; color: #fff; padding: 11px 14px;
    text-align: center; font-weight: 600; white-space: nowrap;
}
.compare-table th.period-col { text-align: left; min-width: 60px; }
.compare-table th.hl { background: #c8a84b; color: #1a2744; font-weight: 700; }
.compare-table th.sub-header { background: #2d3d6b; font-size: 0.78rem; font-weight: 400; }
.compare-table th.divider { background: #0d1b33; width: 5px; padding: 0; }
.compare-table td {
    padding: 10px 14px; text-align: center;
    border-bottom: 1px solid #f0f0f0; white-space: nowrap;
}
.compare-table td.period-col {
    text-align: left; font-weight: 700; color: #1a2744; background: #f8f9fc;
}
.compare-table td.hl {
    background: #fffbe6; font-weight: 700; font-size: 0.92rem;
    border-left: 2px solid #c8a84b; border-right: 2px solid #c8a84b;
}
.compare-table td.divider { background: #e8ebf4; padding: 0; width: 5px; }
.compare-table tr:last-child td { border-bottom: none; }
.compare-table tr:hover td { background: #fafbff; }
.compare-table tr:hover td.period-col { background: #f0f2f8; }
.compare-table tr:hover td.hl { background: #fff8d6; }
.pos { color: #2e7d32; } .neg { color: #c62828; } .neu { color: #888; }
.bond-tag {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; color: white; margin-bottom: 4px;
}
.legend { display: flex; gap: 20px; margin-top: 10px; font-size: 0.78rem; color: #888; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display:inline-block; }
</style>
""", unsafe_allow_html=True)


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

@st.cache_data(ttl=300)
def list_sheets_in_folder(folder_id):
    import requests
    from google.oauth2.service_account import Credentials
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    headers = {"Authorization": f"Bearer {creds.token}"}
    params = {
        "q": f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        "fields": "files(id, name)",
    }
    resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
    return resp.json().get("files", [])

@st.cache_data(ttl=300)
def read_sheet(sheet_id):
    import time
    client = get_gspread_client()
    for attempt in range(3):
        try:
            sh = client.open_by_key(sheet_id)
            ws = sh.get_worksheet(0)
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            if "time" in df.columns:
                df["date"] = pd.to_datetime(df["time"], unit="s")
            elif "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            else:
                df["date"] = pd.to_datetime(df.iloc[:, 0])
            df = df[["date", "close"]].sort_values("date").reset_index(drop=True)
            return df
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(3)
                continue
            raise e

def parse_filename(name):
    import re
    FINRA_DB = {
        "FINRA_DLY_APO5813716": "US03769MAC01", "FINRA_DLY_BIIB4981508": "US09062XAG88",
        "FINRA_DLY_BRK3963113": "US084670BK32", "FINRA_DLY_BUD4327587": "US035242AM81",
        "FINRA_DLY_CI4866401": "US125523AK66", "FINRA_DLY_CI5003121": "US125523CF53",
        "FINRA_DLY_CMCS4382861": "US20030NBU46", "FINRA_DLY_FBUO6172956": "US31428XCA28",
        "FINRA_DLY_GILD4287890": "US375558BD48", "FINRA_DLY_GILD4287891": "US375558BD48",
        "FINRA_DLY_GM4181484": "US37045VAT70", "FINRA_DLY_HBC US404280AG49": "US404280AG49",
        "FINRA_DLY_IBM5449458": "US449276AF17", "FINRA_DLY_ICE5414190": "US45866FAX24",
        "FINRA_DLY_KO4969567": "US191216CQ13", "FINRA_DLY_MO4065695": "US02209SAR40",
        "FINRA_DLY_MO4403915": "US02209SAV51", "FINRA_DLY_MS4204532": "US61747YDY86",
        "FINRA_DLY_NFLX5862368": "US64110LBA35", "FINRA_DLY_QCOM4246685": "US747525AK99",
        "FINRA_DLY_SCBFF4110430": "XS1049699926", "FINRA_DLY_SDBO4820048": "US854502AJ02",
        "FINRA_DLY_SWK.GM": "US854502AA92", "FINRA_DLY_T4237450": "US00206RCQ39",
        "FINRA_DLY_T4451561": "US00206RCU41", "FINRA_DLY_USB5600582": "US91159HJN17",
        "FINRA_DLY_VIA4987234": "US92556HAC16", "FINRA_DLY_VZ4968008": "US92343VGW81",
        "FINRA_DLY_VZ5363445": "US92343VFD10",
    }
    for key, isin in FINRA_DB.items():
        if key.lower() in name.lower():
            return isin
    isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', name)
    if isin_match:
        return isin_match.group(1)
    return ""

MASTER_SHEET_ID = "1PVXcY12Dly5l0HlOyOAKdRzegt4K6gAAQFj1YnhiHqw"

LOCAL_DB = {
    "US02079KBP12": {"issuer": "Alphabet 公司債6", "coupon": 5.65, "maturity": "2056"},
    "US30303MAE21": {"issuer": "Meta平台公司債9", "coupon": 5.625, "maturity": "2055"},
    "US64110LBA35": {"issuer": "網飛公司債3", "coupon": 5.4, "maturity": "2054"},
    "US03769MAC01": {"issuer": "阿波羅全球公司債1", "coupon": 5.8, "maturity": "2054"},
    "US191216DS69": {"issuer": "可口可樂公司債5", "coupon": 5.3, "maturity": "2054"},
    "US92343VGW81": {"issuer": "威瑞森電信公司債12", "coupon": 5.5, "maturity": "2054"},
    "XS2747599509": {"issuer": "沙烏地阿拉伯債7", "coupon": 5.75, "maturity": "2054"},
    "US29736RAU41": {"issuer": "雅詩蘭黛公司債3", "coupon": 5.15, "maturity": "2053"},
    "US037833EW60": {"issuer": "蘋果公司債14", "coupon": 4.85, "maturity": "2053"},
    "US91324PEW86": {"issuer": "聯合健康集團債9", "coupon": 5.05, "maturity": "2053"},
    "US532457CG18": {"issuer": "禮來公司債1", "coupon": 4.875, "maturity": "2053"},
    "US91324PES74": {"issuer": "聯合健康集團債5", "coupon": 5.875, "maturity": "2053"},
    "US459200KZ37": {"issuer": "國際商業機器債4", "coupon": 5.1, "maturity": "2053"},
    "US459200KV23": {"issuer": "國際商業機器公司債1", "coupon": 4.9, "maturity": "2052"},
    "US45866FAX24": {"issuer": "洲際交易所公司債1", "coupon": 4.95, "maturity": "2052"},
    "US872898AJ06": {"issuer": "TSMC公司債 4", "coupon": 4.5, "maturity": "2052"},
    "US084664DB47": {"issuer": "波克夏金融公司債2", "coupon": 3.85, "maturity": "2052"},
    "US92343VGP31": {"issuer": "威瑞森電信公司債11", "coupon": 3.875, "maturity": "2052"},
    "US828807DJ39": {"issuer": "賽門房地產集團債1", "coupon": 3.8, "maturity": "2050"},
    "US191216CQ13": {"issuer": "可口可樂公司債2", "coupon": 4.2, "maturity": "2050"},
    "US92343VFD10": {"issuer": "威瑞森電信公司債9", "coupon": 4.0, "maturity": "2050"},
    "US254687FM36": {"issuer": "迪士尼公司債2", "coupon": 2.75, "maturity": "2049"},
    "XS1982116136": {"issuer": "沙烏地阿拉伯石油公司債4", "coupon": 4.375, "maturity": "2049"},
    "US58933YAW57": {"issuer": "默克藥廠公司債1", "coupon": 4.0, "maturity": "2049"},
    "US125523AK66": {"issuer": "信諾公司債1", "coupon": 4.9, "maturity": "2048"},
    "US88579YBD22": {"issuer": "3M 公司債1", "coupon": 4.0, "maturity": "2048"},
    "US084664CQ25": {"issuer": "波克夏海瑟威金融公司債1", "coupon": 4.2, "maturity": "2048"},
    "XS1807174559": {"issuer": "卡達政府國際債1", "coupon": 5.103, "maturity": "2048"},
    "US023135BJ40": {"issuer": "亞馬遜公司債1", "coupon": 4.05, "maturity": "2047"},
    "US375558BK80": {"issuer": "吉利德科學公司債1", "coupon": 4.15, "maturity": "2047"},
    "US037833CH12": {"issuer": "蘋果公司債6", "coupon": 4.25, "maturity": "2047"},
    "US002824BH26": {"issuer": "亞培公司債2", "coupon": 4.9, "maturity": "2046"},
    "XS1508675508": {"issuer": "沙烏地阿拉伯政府國際債券5", "coupon": 4.5, "maturity": "2046"},
    "US02209SAV51": {"issuer": "高特利集團公司債1", "coupon": 3.875, "maturity": "2046"},
    "US92343VCK89": {"issuer": "威瑞森電信公司債1", "coupon": 4.862, "maturity": "2046"},
    "US594918BT09": {"issuer": "微軟公司債2", "coupon": 3.7, "maturity": "2046"},
    "US125523CF53": {"issuer": "信諾公司債2", "coupon": 4.8, "maturity": "2046"},
    "US20030NBU46": {"issuer": "康卡斯特公司債1", "coupon": 3.4, "maturity": "2046"},
    "US375558BD48": {"issuer": "吉利德科學公司債2", "coupon": 4.75, "maturity": "2046"},
    "US02079KBN63": {"issuer": "Alphabet 公司債5", "coupon": 5.5, "maturity": "2046"},
    "US30303M8X35": {"issuer": "Meta平台公司債10", "coupon": 5.5, "maturity": "2045"},
    "US747525AK99": {"issuer": "高通公司債3", "coupon": 4.8, "maturity": "2045"},
    "US25468PDB94": {"issuer": "華德迪士尼公司債1", "coupon": 4.125, "maturity": "2044"},
    "US717081DK61": {"issuer": "輝瑞藥廠公司債2", "coupon": 4.4, "maturity": "2044"},
    "US449276AF17": {"issuer": "IBM金融公司債1", "coupon": 5.25, "maturity": "2044"},
    "US02209SAR40": {"issuer": "高特利集團公司債2", "coupon": 5.375, "maturity": "2044"},
    "US12572QAF28": {"issuer": "芝加哥期交所債1", "coupon": 5.3, "maturity": "2043"},
    "US037833AL42": {"issuer": "蘋果公司債2", "coupon": 3.85, "maturity": "2043"},
    "US084670BK32": {"issuer": "波克夏公司債1", "coupon": 4.5, "maturity": "2043"},
    "US594918BZ68": {"issuer": "微軟公司債7", "coupon": 4.1, "maturity": "2037"},
    "US717081EC37": {"issuer": "輝瑞藥廠公司債1", "coupon": 4.0, "maturity": "2036"},
    "US035242AM81": {"issuer": "百威英博(金融)公司債2", "coupon": 4.7, "maturity": "2036"},
    "US91159HJN17": {"issuer": "美國合眾銀公司債2", "coupon": 5.836, "maturity": "2034"},
    "US55608KBG94": {"issuer": "麥格理集團公司債10", "coupon": 5.491, "maturity": "2033"},
    "US686330AR22": {"issuer": "歐力士公司債2", "coupon": 5.2, "maturity": "2032"},
    "USG91139AL26": {"issuer": "TSMC全球公司債6", "coupon": 4.625, "maturity": "2032"},
    "US92556HAC16": {"issuer": "維康公司債3", "coupon": 4.95, "maturity": "2050"},
    "US31428XCA28": {"issuer": "聯邦快遞公司債1", "coupon": 5.25, "maturity": "2050"},
    "US09062XAG88": {"issuer": "生物基因公司債2", "coupon": 3.15, "maturity": "2050"},
    "US37045VAT70": {"issuer": "通用汽車公司債7", "coupon": 5.95, "maturity": "2049"},
    "US854502AJ02": {"issuer": "史丹利百得公司債3", "coupon": 4.85, "maturity": "2048"},
    "US00206RCU41": {"issuer": "AT&T公司債12", "coupon": 5.65, "maturity": "2047"},
    "US94974BGU89": {"issuer": "富國銀行公司債10", "coupon": 4.75, "maturity": "2046"},
    "US172967KR13": {"issuer": "花旗集團公司債14", "coupon": 4.75, "maturity": "2046"},
    "US00206RCQ39": {"issuer": "AT&T公司債5", "coupon": 4.75, "maturity": "2046"},
    "US58013MFA71": {"issuer": "麥當勞公司債2", "coupon": 4.875, "maturity": "2045"},
    "US42824CAY57": {"issuer": "慧與公司債1", "coupon": 6.35, "maturity": "2045"},
    "US09062XAD57": {"issuer": "生物基因公司債1", "coupon": 5.2, "maturity": "2045"},
    "US37045VAJ98": {"issuer": "通用汽車公司債4", "coupon": 5.2, "maturity": "2045"},
    "US61747YDY86": {"issuer": "摩根士丹利債20", "coupon": 4.3, "maturity": "2045"},
    "US94974BGE48": {"issuer": "富國銀行債9", "coupon": 4.65, "maturity": "2044"},
    "US172967HS33": {"issuer": "花旗集團債12", "coupon": 5.3, "maturity": "2044"},
    "XS1049699926": {"issuer": "渣打集團債6", "coupon": 5.7, "maturity": "2044"},
    "US404280AQ21": {"issuer": "匯豐控股公司債8", "coupon": 5.25, "maturity": "2044"},
    "US37045VAF76": {"issuer": "通用汽車公司債3", "coupon": 6.25, "maturity": "2043"},
    "US92553PAP71": {"issuer": "維康公司債2", "coupon": 4.375, "maturity": "2043"},
    "US00206RBH49": {"issuer": "AT&T公司債1", "coupon": 4.3, "maturity": "2042"},
    "US71568QAB32": {"issuer": "印尼國家電力債2", "coupon": 5.25, "maturity": "2042"},
    "US854502AA92": {"issuer": "史丹利百得公司債2", "coupon": 5.2, "maturity": "2040"},
    "US50076QAN60": {"issuer": "卡夫亨氏公司債1", "coupon": 6.5, "maturity": "2040"},
    "XS2885079702": {"issuer": "國泰人壽公司債2", "coupon": 5.3, "maturity": "2039"},
    "US46625HHF01": {"issuer": "摩根大通銀行債3", "coupon": 6.4, "maturity": "2038"},
    "US37045VAP58": {"issuer": "通用汽車公司債2", "coupon": 5.15, "maturity": "2038"},
    "US126650CY46": {"issuer": "CVS公司債1", "coupon": 4.78, "maturity": "2038"},
    "US38141GFD16": {"issuer": "美高盛公司債14", "coupon": 6.75, "maturity": "2037"},
    "US00206RDR03": {"issuer": "AT&T公司債3", "coupon": 5.25, "maturity": "2037"},
    "US404280AG49": {"issuer": "匯豐銀行公司債4", "coupon": 6.5, "maturity": "2036"},
    "US38143YAC75": {"issuer": "美商高盛證券公司債16", "coupon": 6.45, "maturity": "2036"},
    "US925524AX89": {"issuer": "維康公司債1", "coupon": 6.875, "maturity": "2036"},
    "US37045VAK61": {"issuer": "通用汽車公司債1", "coupon": 6.6, "maturity": "2036"},
    "XS3151416727": {"issuer": "富邦人壽(新加坡)1", "coupon": 5.45, "maturity": "2035"},
    "US06051GLU12": {"issuer": "美國銀行公司債6", "coupon": 5.872, "maturity": "2034"},
    "XS2852920342": {"issuer": "國泰人壽公司債1", "coupon": 5.95, "maturity": "2034"},
    "US458140CA64": {"issuer": "英特爾公司債5", "coupon": 4.15, "maturity": "2032"},
}

@st.cache_data(ttl=3600)
def load_master_db():
    try:
        creds_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(MASTER_SHEET_ID)
        ws = sh.get_worksheet(0)
        rows = ws.get_all_records()
        db = dict(LOCAL_DB)
        for row in rows:
            code = str(row.get("ISIN/代碼", "")).strip()
            name = str(row.get("債券名稱", "")).strip()
            if not code or not name:
                continue
            raw_coupon = row.get("票息率", "")
            try:
                coupon = float(str(raw_coupon).replace("%", "").strip())
            except:
                coupon = db.get(code, {}).get("coupon", 0.0)
            raw_maturity = row.get("到期日", "")
            try:
                maturity = str(raw_maturity).strip()[:4]
                if not maturity.isdigit():
                    maturity = db.get(code, {}).get("maturity", "")
            except:
                maturity = db.get(code, {}).get("maturity", "")
            db[code] = {"issuer": name, "coupon": coupon, "maturity": maturity}
        return db
    except Exception:
        return LOCAL_DB

def lookup_bond_info(isin):
    db = load_master_db()
    return db.get(isin, {"issuer": isin, "coupon": 0.0, "maturity": ""})


# ==========================================
# 工具函數
# ==========================================
def calc_period(df, coupon_rate, days):
    end_date = df["date"].max()
    sub = df[df["date"] >= end_date - timedelta(days=days)]
    if len(sub) < 5:
        return None
    sp, ep = sub["close"].iloc[0], sub["close"].iloc[-1]
    actual_days = (sub["date"].iloc[-1] - sub["date"].iloc[0]).days
    if actual_days == 0:
        return None
    price_ret = (ep - sp) / sp
    coupon_ret = (coupon_rate / 100) * (actual_days / 365)
    return {"price": price_ret, "coupon": coupon_ret, "total": price_ret + coupon_ret}

def calc_annual(df, coupon_rate):
    df = df.copy()
    df["year"] = df["date"].dt.year
    rows = []
    for year in sorted(df["year"].unique()):
        ydf = df[df["year"] == year]
        if len(ydf) < 2:
            continue
        sp, ep = ydf["close"].iloc[0], ydf["close"].iloc[-1]
        days = (ydf["date"].iloc[-1] - ydf["date"].iloc[0]).days
        price_ret = (ep - sp) / sp
        coupon_ret = (coupon_rate / 100) * (days / 365) if days > 0 else 0
        rows.append({"year": str(year), "price": price_ret, "coupon": coupon_ret, "total": price_ret + coupon_ret})
    return rows

def total_return_index(df, coupon_rate):
    prices = df["close"].values
    daily_coupon = (coupon_rate / 100) / 365
    tri = [100.0]
    for i in range(1, len(prices)):
        price_ret = (prices[i] - prices[i-1]) / prices[i-1]
        tri.append(tri[-1] * (1 + price_ret + daily_coupon))
    return tri

def calc_sharpe(df, coupon_rate, risk_free=0.02):
    tri = total_return_index(df, coupon_rate)
    tri_s = pd.Series(tri)
    daily_ret = tri_s.pct_change().dropna()
    ann_ret = (tri[-1] / 100) ** (252 / len(tri)) - 1
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - risk_free) / ann_vol if ann_vol > 0 else 0
    return round(sharpe, 2), round(ann_ret * 100, 2), round(ann_vol * 100, 2)

def calc_mdd(df, coupon_rate):
    tri = pd.Series(total_return_index(df, coupon_rate))
    roll_max = tri.cummax()
    dd = (tri - roll_max) / roll_max
    return round(dd.min() * 100, 2)

def fmt(val, bold=False):
    if val is None:
        return '<span class="neu">—</span>'
    css = "pos" if val > 0.0005 else ("neg" if val < -0.0005 else "neu")
    text = f"{val:+.2%}"
    return f'<span class="{css}"><b>{text}</b></span>' if bold else f'<span class="{css}">{text}</span>'

def color_cell(val):
    if val is None: return ""
    if val > 0.0005: return "color:#2e7d32;font-weight:600;"
    elif val < -0.0005: return "color:#c62828;font-weight:600;"
    return "color:#888;"

def get_chinese_font():
    import os, requests as req
    font_name = "ChineseFont"
    system_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for path in system_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
            except:
                continue
    try:
        cache_path = "/tmp/wqy_microhei.ttc"
        if not os.path.exists(cache_path):
            r = req.get("https://github.com/anthonyfok/fonts-wqy-microhei/raw/master/wqy-microhei.ttc", timeout=30)
            with open(cache_path, "wb") as f:
                f.write(r.content)
        pdfmetrics.registerFont(TTFont(font_name, cache_path))
        return font_name
    except:
        pass
    return "Helvetica"


# ==========================================
# ★ 核心：生成 PDF 報告（含詳盡解釋）
# ==========================================
def generate_pdf_report(loaded, loaded_filtered, all_data, periods, all_annual, all_years,
                        chart_start, chart_end, lang="zh", max_years=5):
    import os
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    if lang == "en":
        L = {
            "title": "Bond Performance Comparison Report",
            "period": f"Period: {chart_start} ~ {chart_end}  |  Date: {date.today().strftime('%Y-%m-%d')}",
            "s1": "1. Bond Basic Information",
            "s2": "2. Period Performance Comparison",
            "s2_note": "Commentary",
            "s3": "3. Total Return Index (with coupon)",
            "s3_note": "Long-term Trend Analysis",
            "s4": "4. Annual Return Review",
            "s4_note": "Annual Trend Analysis",
            "s5": "5. Comprehensive Analysis Summary",
            "col_name": "Bond Name", "col_isin": "ISIN", "col_issuer": "Issuer",
            "col_coupon": "Coupon", "col_mat": "Maturity",
            "col_period": "Period", "col_price": "Price Chg", "col_coupon2": "Coupon Inc",
            "col_total": "Total★", "col_year": "Year",
            "col_sharpe": "Sharpe", "col_ann_ret": "Ann. Return", "col_ann_vol": "Ann. Vol", "col_mdd": "MDD",
            "disclaimer": "⚠️ Disclaimer: Price data from TradingView for reference only. Not actual bank pricing. Total Return = Price Change + Coupon (by holding days). For internal education/training only. Do not distribute.",
            "no_data": "N/A",
            "y_axis": "Total Return Index (Base=100, incl. coupon)",
        }
    else:
        L = {
            "title": "債券績效比較報告",
            "period": f"比較區間：{chart_start} ～ {chart_end}　｜　製作日期：{date.today().strftime('%Y-%m-%d')}",
            "s1": "一、債券基本資訊",
            "s2": "二、各期間績效比較",
            "s2_note": "📝 期間點評",
            "s3": "三、長期走勢圖（標準化，含息）",
            "s3_note": "📈 長期趨勢解讀",
            "s4": "四、年度報酬回顧",
            "s4_note": "📅 年度趨勢分析",
            "s5": "五、綜合分析摘要",
            "col_name": "債券名稱", "col_isin": "ISIN", "col_issuer": "發行機構",
            "col_coupon": "票息率", "col_mat": "到期年",
            "col_period": "期間", "col_price": "價格漲跌", "col_coupon2": "票息收益",
            "col_total": "總報酬★", "col_year": "年度",
            "col_sharpe": "夏普比率", "col_ann_ret": "年化報酬", "col_ann_vol": "年化波動", "col_mdd": "最大回撤",
            "disclaimer": "⚠️ 免責聲明：本報告價格資料來源為 TradingView，此價格僅為中間價，並非本行實際報價，僅供參考，不構成投資建議。總報酬 = 價格漲跌 + 票息（依實際持有天數估算）。本報告僅供內部教育訓練使用，請勿外流。",
            "no_data": "無資料",
            "y_axis": "總報酬指數（起始=100，含息）",
        }

    NAVY    = colors.HexColor("#1a2744")
    GOLD    = colors.HexColor("#c8a84b")
    WHITE   = colors.white
    GRAY    = colors.HexColor("#888888")
    BG_GRAY = colors.HexColor("#f0f4ff")
    BG_YELLOW = colors.HexColor("#fffde7")
    BG_GREEN  = colors.HexColor("#f1f8e9")
    TEXT_DARK = colors.HexColor("#1a2744")
    bond_colors_hex = ["#1565c0","#c62828","#2e7d32","#6a1b9a","#e65100","#00838f"]

    font_name = get_chinese_font()

    title_style   = ParagraphStyle("title",   fontName=font_name, fontSize=22, textColor=WHITE, alignment=TA_CENTER, spaceAfter=4)
    sub_style     = ParagraphStyle("sub",     fontName=font_name, fontSize=11, textColor=colors.HexColor("#cce0ff"), alignment=TA_CENTER)
    h2_style      = ParagraphStyle("h2",      fontName=font_name, fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=6)
    h3_style      = ParagraphStyle("h3",      fontName=font_name, fontSize=10, textColor=NAVY, spaceBefore=6, spaceAfter=4)
    body_style    = ParagraphStyle("body",    fontName=font_name, fontSize=9,  textColor=colors.HexColor("#333333"), spaceAfter=3)
    comment_style = ParagraphStyle("comment", fontName=font_name, fontSize=9,  textColor=colors.HexColor("#1a3a1a"),
                                   backColor=BG_GREEN, borderPadding=8, spaceBefore=6, spaceAfter=6, leading=16)
    summary_style = ParagraphStyle("summary", fontName=font_name, fontSize=9,  textColor=colors.HexColor("#1a2744"),
                                   backColor=BG_YELLOW, borderPadding=8, spaceBefore=6, spaceAfter=6, leading=16)
    warn_style    = ParagraphStyle("warn",    fontName=font_name, fontSize=7.5, textColor=colors.HexColor("#cc0000"),
                                   backColor=colors.HexColor("#fff3cd"), borderPadding=6, spaceBefore=8)
    small_style   = ParagraphStyle("small",   fontName=font_name, fontSize=7.5, textColor=GRAY)

    def fmt_pct(val):
        if val is None: return L["no_data"]
        return f"{val:+.2%}"

    story = []

    # ── 封面 ──
    title_table = Table([[Paragraph(L["title"], title_style)],
                         [Paragraph(L["period"], sub_style)]], colWidths=[17*cm])
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 0.5*cm))

    # ── 一、債券基本資訊 ──
    story.append(Paragraph(L["s1"], h2_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6))

    info_data = [["", L["col_name"], L["col_isin"], L["col_issuer"], L["col_coupon"], L["col_mat"]]]
    for idx, (b, df) in enumerate(loaded):
        isin = parse_filename(b["selected"])
        info = LOCAL_DB.get(isin, {})
        issuer   = info.get("issuer", "-")
        coupon   = f"{b['coupon']}%" if b['coupon'] > 0 else "-"
        maturity = info.get("maturity", "-")
        info_data.append([
            Paragraph(f"<font color='{bond_colors_hex[idx]}'>●</font> {b['label']}", body_style),
            b["name"], isin, issuer, coupon, maturity
        ])
    info_table = Table(info_data, colWidths=[1*cm, 3.8*cm, 3*cm, 3.8*cm, 1.8*cm, 1.8*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,-1), font_name), ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [BG_GRAY, WHITE]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    # ── 二、各期間績效 ──
    story.append(Paragraph(L["s2"], h2_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6))

    header = [L["col_period"]]
    for b, _ in all_data:
        header += [f"{b['label']}. {L['col_price']}", L["col_coupon2"], L["col_total"]]
    perf_data = [header]

    # 記錄每期誰最佳（用於點評）
    period_winners = {}
    for period_label, _ in periods:
        row = [period_label]
        for b, period_dict in all_data:
            r = period_dict.get(period_label)
            row += [fmt_pct(r["price"] if r else None),
                    fmt_pct(r["coupon"] if r else None),
                    fmt_pct(r["total"] if r else None)]
        perf_data.append(row)
        # 找出這期最佳
        valid = [(b, all_data[i][1].get(period_label)) for i, (b, _) in enumerate(all_data)]
        valid = [(b, r) for b, r in valid if r]
        if valid:
            best = max(r["total"] for _, r in valid)
            winners = [b for b, r in valid if r["total"] >= best - 0.0001]
            period_winners[period_label] = (winners, best)

    col_w = [2*cm] + [1.8*cm, 1.5*cm, 1.8*cm] * len(all_data)
    ts = [
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,-1), font_name), ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [BG_GRAY, WHITE]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]
    for col_idx in range(len(all_data)):
        total_col = 1 + col_idx * 3 + 2
        ts.append(("BACKGROUND", (total_col, 1), (total_col, -1), BG_YELLOW))
        ts.append(("TEXTCOLOR", (total_col, 1), (total_col, -1), colors.HexColor("#b8860b")))
    perf_table = Table(perf_data, colWidths=col_w)
    perf_table.setStyle(TableStyle(ts))
    story.append(perf_table)

    # ★ 期間點評
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(L["s2_note"], h3_style))

    wins_count = [0] * len(all_data)
    comment_lines = []
    for period_label, _ in periods:
        if period_label not in period_winners:
            continue
        winners, best_total = period_winners[period_label]
        winner_names = "、".join(f"{w['label']}（{w['name'][:8]}）" for w in winners)
        comment_lines.append(f"• <b>{period_label}</b>：{winner_names} 以總報酬 {best_total:+.2%} 領先。" +
                             ("" if best_total > 0 else "（各檔均為負報酬，票息收益為主要支撐）"))
        for i, (b, _) in enumerate(all_data):
            if b in winners:
                wins_count[i] += 1

    # 整體勝出
    max_wins = max(wins_count) if wins_count else 0
    overall_winners = [all_data[i][0] for i, w in enumerate(wins_count) if w == max_wins]
    overall_text = "、".join(f"{w['label']}（{w['name'][:8]}）" for w in overall_winners)
    comment_lines.append(f"\n<b>整體表現：{overall_text} 共在 {max_wins} 個期間領先，{'表現最為突出。' if len(overall_winners)==1 else '各有所長，勢均力敵。'}</b>")

    story.append(Paragraph("<br/>".join(comment_lines), comment_style))
    story.append(Spacer(1, 0.3*cm))

    # ── 三、走勢圖 ──
    story.append(PageBreak())
    story.append(Paragraph(L["s3"], h2_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6))

    # 計算各標的 TRI 終值（用於趨勢解讀）
    tri_finals = {}
    for b, df in loaded_filtered:
        if not df.empty:
            tri = total_return_index(df, b["coupon"])
            tri_finals[b["label"]] = (b["name"], tri[-1])

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        from matplotlib import font_manager

        font_path = None
        for p in ["/tmp/wqy_microhei.ttc",
                  "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                  "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]:
            if os.path.exists(p):
                font_path = p
                break
        if font_path:
            font_manager.fontManager.addfont(font_path)
            fp_prop = font_manager.FontProperties(fname=font_path)
            matplotlib.rcParams["font.family"] = fp_prop.get_name()

        fig, ax = plt.subplots(figsize=(10, 4.5))
        fig.patch.set_facecolor("#f8f9ff")
        ax.set_facecolor("#f8f9ff")

        for idx, (b, df) in enumerate(loaded_filtered):
            if df.empty: continue
            tri = total_return_index(df, b["coupon"])
            lbl = f'{b["label"]}. {b["name"]}' if font_path else f'{b["label"]} ({b["coupon"]}%)'
            ax.plot(df["date"], tri, label=lbl,
                    color=bond_colors_hex[idx % len(bond_colors_hex)], linewidth=2)

        fp_arg = font_manager.FontProperties(fname=font_path) if font_path else None
        ax.set_ylabel(L["y_axis"], fontsize=9, fontproperties=fp_arg)
        ax.axhline(y=100, color="#aaaaaa", linewidth=0.8, linestyle="--")
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        legend = ax.legend(loc="upper left", fontsize=8, framealpha=0.8)
        if font_path and legend:
            for text in legend.get_texts():
                text.set_fontproperties(fp_arg)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        img_buf.seek(0)
        story.append(RLImage(img_buf, width=15*cm, height=7*cm))
    except Exception as e:
        story.append(Paragraph(f"Chart unavailable: {e}", small_style))

    # ★ 長期趨勢解讀
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(L["s3_note"], h3_style))

    if tri_finals:
        sorted_tri = sorted(tri_finals.items(), key=lambda x: x[1][1], reverse=True)
        trend_lines = []
        for rank, (label, (name, final_val)) in enumerate(sorted_tri):
            gain = final_val - 100
            trend_lines.append(
                f"• <b>{label}（{name[:10]}）</b>：期間累積含息報酬 {gain:+.1f}（起始=100），"
                f"{'表現最佳，票息穩定累積推動整體上升。' if rank == 0 else '表現居次。' if rank == 1 else '相對保守，以票息收益為主。'}"
            )
        if len(sorted_tri) >= 2:
            best_label, (best_name, best_val) = sorted_tri[0]
            worst_label, (worst_name, worst_val) = sorted_tri[-1]
            diff = best_val - worst_val
            trend_lines.append(
                f"\n<b>最佳與最差差距：{diff:.1f} 點，</b>顯示各債券在同期間的報酬差異{'顯著' if diff > 10 else '尚在合理範圍內'}。"
                f"長期持有下，票息累積效益明顯，建議關注高票息債券在升息環境結束後的價格回升空間。"
            )
        story.append(Paragraph("<br/>".join(trend_lines), comment_style))
    story.append(Spacer(1, 0.3*cm))

    # ── 四、年度報酬 ──
    story.append(Paragraph(L["s4"], h2_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6))

    filtered_years = all_years[:max_years]
    ann_header = [L["col_year"]]
    for b, _ in all_annual:
        ann_header += [f"{b['label']}. {L['col_price']}", L["col_coupon2"], L["col_total"]]
    ann_data = [ann_header]

    # 記錄每年數據（用於趨勢分析）
    year_best = {}
    year_worst = {}
    for year in filtered_years:
        row = [year]
        year_totals = {}
        for b, rows in all_annual:
            r = next((x for x in rows if x["year"] == year), None)
            row += [fmt_pct(r["price"] if r else None),
                    fmt_pct(r["coupon"] if r else None),
                    fmt_pct(r["total"] if r else None)]
            if r:
                year_totals[b["label"]] = (b["name"], r["total"])
        ann_data.append(row)
        if year_totals:
            best_lbl = max(year_totals, key=lambda k: year_totals[k][1])
            worst_lbl = min(year_totals, key=lambda k: year_totals[k][1])
            year_best[year] = (best_lbl, year_totals[best_lbl])
            year_worst[year] = (worst_lbl, year_totals[worst_lbl])

    ann_table = Table(ann_data, colWidths=col_w)
    ann_table.setStyle(TableStyle(ts))
    story.append(ann_table)

    # ★ 年度趨勢分析
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(L["s4_note"], h3_style))

    ann_lines = []
    all_totals_flat = []
    for year in filtered_years:
        for b, rows in all_annual:
            r = next((x for x in rows if x["year"] == year), None)
            if r:
                all_totals_flat.append((year, b["label"], b["name"], r["total"]))

    if all_totals_flat:
        best_overall = max(all_totals_flat, key=lambda x: x[3])
        worst_overall = min(all_totals_flat, key=lambda x: x[3])
        ann_lines.append(
            f"• <b>最佳單年：</b>{best_overall[0]}年 {best_overall[1]}（{best_overall[2][:8]}）總報酬 {best_overall[3]:+.2%}，"
            f"{'表現亮眼，價格大幅上揚為主要貢獻。' if best_overall[3] > 0.1 else '溫和正報酬。'}"
        )
        ann_lines.append(
            f"• <b>最差單年：</b>{worst_overall[0]}年 {worst_overall[1]}（{worst_overall[2][:8]}）總報酬 {worst_overall[3]:+.2%}，"
            f"{'反映升息壓力導致債券價格明顯下跌，但票息收益提供部分緩衝。' if worst_overall[3] < -0.05 else '小幅虧損，票息收益基本抵消部分價格跌幅。'}"
        )
        # 計算各標的平均年報酬
        from collections import defaultdict
        bond_yearly = defaultdict(list)
        for year, lbl, name, total in all_totals_flat:
            bond_yearly[(lbl, name)].append(total)
        ann_lines.append("• <b>各標的平均年化報酬（樣本年度）：</b>")
        for (lbl, name), vals in sorted(bond_yearly.items()):
            avg = sum(vals) / len(vals)
            ann_lines.append(f"  &nbsp;&nbsp;{lbl}（{name[:8]}）：平均 {avg:+.2%}")
    story.append(Paragraph("<br/>".join(ann_lines), comment_style))
    story.append(Spacer(1, 0.3*cm))

    # ── 五、綜合分析摘要 ──
    story.append(PageBreak())
    story.append(Paragraph(L["s5"], h2_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6))

    # Sharpe / MDD / 年化報酬 表格
    risk_header = ["", L["col_ann_ret"], L["col_ann_vol"], L["col_sharpe"], L["col_mdd"]]
    risk_data = [risk_header]
    bond_stats = {}
    for b, df in loaded:
        sharpe, ann_ret, ann_vol = calc_sharpe(df, b["coupon"])
        mdd = calc_mdd(df, b["coupon"])
        bond_stats[b["label"]] = {"name": b["name"], "sharpe": sharpe, "ann_ret": ann_ret, "ann_vol": ann_vol, "mdd": mdd}
        risk_data.append([
            f"{b['label']}. {b['name'][:14]}",
            f"{ann_ret:+.2f}%", f"{ann_vol:.2f}%",
            f"{sharpe:.2f}",
            f"{mdd:.2f}%"
        ])

    risk_table = Table(risk_data, colWidths=[5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm])
    risk_ts = [
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,-1), font_name), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (0,-1), "LEFT"), ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [BG_GRAY, WHITE]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]
    # 高亮最佳 Sharpe
    if bond_stats:
        best_sharpe_lbl = max(bond_stats, key=lambda k: bond_stats[k]["sharpe"])
        for i, (b, _) in enumerate(loaded):
            if b["label"] == best_sharpe_lbl:
                risk_ts.append(("BACKGROUND", (3, i+1), (3, i+1), colors.HexColor("#e8f5e9")))
                risk_ts.append(("TEXTCOLOR",  (3, i+1), (3, i+1), colors.HexColor("#1b5e20")))
        # 高亮最小 MDD（最不回撤）
        best_mdd_lbl = max(bond_stats, key=lambda k: bond_stats[k]["mdd"])  # mdd是負數，最大=最小回撤
        for i, (b, _) in enumerate(loaded):
            if b["label"] == best_mdd_lbl:
                risk_ts.append(("BACKGROUND", (4, i+1), (4, i+1), colors.HexColor("#e3f2fd")))
    risk_table.setStyle(TableStyle(risk_ts))
    story.append(risk_table)
    story.append(Spacer(1, 0.3*cm))

    # ★ Sharpe / MDD 解讀說明
    summary_lines = []

    # Sharpe 解讀
    summary_lines.append("<b>【夏普比率（Sharpe Ratio）解讀】</b>")
    summary_lines.append("夏普比率 = 超額報酬 ÷ 波動度，衡量「每承擔一單位風險，能獲得多少超額報酬」。數值越高越好。")
    summary_lines.append("• Sharpe > 1.0：優秀，每單位風險獲得充分補償")
    summary_lines.append("• Sharpe 0.5～1.0：尚可，風險報酬比合理")
    summary_lines.append("• Sharpe < 0.5：偏低，承擔風險未獲充分回報")
    if bond_stats:
        best_s = max(bond_stats.values(), key=lambda x: x["sharpe"])
        worst_s = min(bond_stats.values(), key=lambda x: x["sharpe"])
        summary_lines.append(
            f"→ <b>本次比較中，{best_s['name'][:10]} 夏普比率最高（{best_s['sharpe']:.2f}），"
            f"風險調整後表現最佳；{worst_s['name'][:10]} 相對較低（{worst_s['sharpe']:.2f}）。</b>"
        )

    summary_lines.append("")
    # MDD 解讀
    summary_lines.append("<b>【最大回撤（MDD）解讀】</b>")
    summary_lines.append("最大回撤 = 歷史最高點到最低點的最大跌幅，衡量最壞情況下的損失幅度。數值越小（越接近0）越好。")
    summary_lines.append("• MDD > -10%：低回撤，適合保守型投資人")
    summary_lines.append("• MDD -10%～-20%：中等，需有心理準備短期帳面虧損")
    summary_lines.append("• MDD < -20%：較高，長期持有才能回補")
    if bond_stats:
        # MDD 最小的（最好的）
        best_mdd = min(bond_stats.values(), key=lambda x: x["mdd"])   # mdd 是負數，最接近0
        worst_mdd = max(bond_stats.values(), key=lambda x: x["mdd"])  # 最大負值=最深回撤
        summary_lines.append(
            f"→ <b>本次比較中，{best_mdd['name'][:10]} 最大回撤最小（{best_mdd['mdd']:.2f}%），"
            f"下行風險控制較佳；{worst_mdd['name'][:10]} 回撤相對較深（{worst_mdd['mdd']:.2f}%）。</b>"
        )

    summary_lines.append("")
    # 整體結論
    summary_lines.append("<b>【整體投資建議】</b>")
    if bond_stats:
        # 綜合排名：Sharpe 加權
        ranked = sorted(bond_stats.items(), key=lambda x: x[1]["sharpe"], reverse=True)
        top = ranked[0]
        summary_lines.append(
            f"綜合夏普比率、最大回撤與各期間勝出次數，<b>{top[1]['name'][:10]}</b> 整體風險調整後表現最為突出，"
            f"票息收益穩定，適合作為核心配置。"
        )
        if len(ranked) >= 2:
            second = ranked[1]
            summary_lines.append(
                f"<b>{second[1]['name'][:10]}</b> 表現次之，可作為補充配置，"
                f"兩者搭配可在報酬與風險之間取得較佳平衡。"
            )

    story.append(Paragraph("<br/>".join(summary_lines), summary_style))
    story.append(Spacer(1, 0.4*cm))

    # 免責聲明
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY, spaceBefore=8, spaceAfter=6))
    story.append(Paragraph(L["disclaimer"], warn_style))

    doc.build(story)
    buf.seek(0)
    return buf


# ==========================================
# 主介面
# ==========================================
st.markdown("## 📊 債券投資工具")
st.markdown("---")
st.markdown("從 bond_master 主資料表讀取清單，選擇債券後比較績效")

folder_id = st.secrets.get("FOLDER_ID", "")

try:
    with st.spinner("正在讀取 bond_master 主資料表..."):
        creds_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.readonly"]
        )
        gc = gspread.authorize(creds)
        master_sh = gc.open_by_key(MASTER_SHEET_ID)
        master_ws = master_sh.get_worksheet(0)
        master_rows = master_ws.get_all_records()

    if not master_rows:
        st.warning("⚠️ bond_master 試算表是空的，請先填入債券資料。")
        st.stop()

    with st.spinner("正在讀取 bond-data 資料夾..."):
        files = list_sheets_in_folder(folder_id)
    file_options = {f["name"]: f["id"] for f in files if "bond_master" not in f["name"].lower()}

    if not file_options:
        st.error(f"❌ bond-data 資料夾是空的！FOLDER_ID={folder_id}")
        st.stop()

    bond_info_cache = {}
    display_to_sheet = {}
    display_to_isin  = {}

    for row in master_rows:
        keys = list(row.keys())
        if len(keys) == 1 and ',' in keys[0]:
            import csv as _csv
            col_names = [c.strip() for c in next(_csv.reader([keys[0]]))]
            values = [v.strip() for v in list(next(_csv.reader([str(list(row.values())[0])])))]
            row = dict(zip(col_names, values))

        filename  = str(row.get("檔名", "")).strip()
        isin      = str(row.get("ISIN/代碼", "")).strip()
        bond_name = str(row.get("債券名稱", "")).strip()
        if not filename or not bond_name:
            continue

        sheet_id = None
        for fname, fid in file_options.items():
            clean_master = filename.replace(", 1D", "").replace(",1D", "").strip()
            clean_fname  = fname.replace(", 1D", "").replace(",1D", "").replace(".csv", "").strip()
            if clean_master == clean_fname or clean_master in clean_fname or clean_fname in clean_master:
                sheet_id = fid
                break
        if not sheet_id:
            continue

        raw_coupon = row.get("票息率", "")
        try:
            coupon = float(str(raw_coupon).replace("%", "").strip())
        except:
            coupon = LOCAL_DB.get(isin, {}).get("coupon", 0.0)

        raw_maturity = row.get("到期日", "")
        try:
            maturity = str(raw_maturity).strip()[:4]
            if not maturity.isdigit():
                maturity = LOCAL_DB.get(isin, {}).get("maturity", "")
        except:
            maturity = LOCAL_DB.get(isin, {}).get("maturity", "")

        bond_info_cache[isin] = {"issuer": bond_name, "coupon": coupon, "maturity": maturity}
        display_name = f"{bond_name}（{isin}）" if isin else bond_name
        display_to_sheet[display_name] = sheet_id
        display_to_isin[display_name]  = isin

    display_names = sorted(display_to_sheet.keys())

    if not display_names:
        st.warning("⚠️ bond_master 的債券都找不到對應的 bond-data 試算表。")
        with st.expander("🔍 Debug 資訊"):
            st.write(f"bond-data 資料夾共 {len(file_options)} 個試算表")
            st.write("前5個檔名：", list(file_options.keys())[:5])
            st.write(f"bond_master 共 {len(master_rows)} 行")
            if master_rows:
                st.write("第1行的所有欄位key：", list(master_rows[0].keys()))
                st.write("第1行內容：", master_rows[0])
        st.stop()

except Exception as e:
    st.error(f"❌ 無法連接 Google Drive：{e}")
    st.stop()

# 選檔數
n = st.radio("比較幾檔債券？", [2, 3, 4, 5, 6], horizontal=True)
st.markdown("---")

bonds = []
cols = st.columns(n)
for i in range(n):
    with cols[i]:
        color = COLORS[i]
        label = LABELS[i]
        st.markdown(f'<span class="bond-tag" style="background:{color}">債券 {label}</span>', unsafe_allow_html=True)
        selected_display = st.selectbox("選擇債券", options=["（請選擇）"] + display_names, key=f"sel_{i}")
        sheet_id = display_to_sheet.get(selected_display) if selected_display != "（請選擇）" else None
        isin = display_to_isin.get(selected_display, "") if selected_display != "（請選擇）" else ""

        if sheet_id and isin and isin in bond_info_cache:
            info = bond_info_cache[isin]
            auto_coupon = info["coupon"]
            maturity    = info["maturity"]
            default_name = f"{info['issuer']} {auto_coupon}% {maturity}".strip()
            if st.session_state.get(f"last_sel_{i}") != selected_display:
                st.session_state[f"name_{i}"] = default_name
                st.session_state[f"coupon_{i}"] = auto_coupon
                st.session_state[f"last_sel_{i}"] = selected_display
            if auto_coupon > 0:
                st.success(f"✅ {isin}｜票息 {auto_coupon}%｜到期 {maturity}")
        else:
            if st.session_state.get(f"last_sel_{i}") != selected_display:
                st.session_state[f"name_{i}"] = ""
                st.session_state[f"coupon_{i}"] = 0.0
                st.session_state[f"last_sel_{i}"] = selected_display

        name   = st.text_input("債券名稱（可修改）", placeholder="例：Apple 3% 2027", key=f"name_{i}")
        coupon = st.number_input("票息率 % （可修改）", step=0.01, min_value=0.0, max_value=20.0, key=f"coupon_{i}")
        bonds.append({"sheet_id": sheet_id, "name": name or f"債券{label}", "coupon": coupon,
                      "color": color, "label": label, "selected": selected_display})

st.markdown("---")

loaded = []
for b in bonds:
    if b["sheet_id"]:
        try:
            with st.spinner(f"讀取 {b['selected']}..."):
                df = read_sheet(b["sheet_id"])
            loaded.append((b, df))
        except Exception as e:
            st.error(f"❌ 讀取 {b['selected']} 失敗：{e}")

if loaded:
    periods = [("1個月",30),("3個月",90),("6個月",180),
               ("1年",365),("2年",730),("3年",1095),("5年",1825)]

    info_cols = st.columns(len(loaded))
    for idx, (b, df) in enumerate(loaded):
        with info_cols[idx]:
            st.markdown(f'<span class="bond-tag" style="background:{b["color"]}">{b["label"]}</span> **{b["name"]}**', unsafe_allow_html=True)
            st.caption(f"{df['date'].min().strftime('%Y-%m-%d')} ～ {df['date'].max().strftime('%Y-%m-%d')}（{len(df)} 筆）")

    all_data = [(b, {label: calc_period(df, b["coupon"], days) for label, days in periods}) for b, df in loaded]

    # 一、各期間績效比較表
    st.subheader("🏆 各期間績效比較")
    html = '<table class="compare-table"><thead><tr>'
    html += '<th class="period-col" rowspan="2">期間</th>'
    for idx, (b, _) in enumerate(all_data):
        if idx > 0: html += '<th class="divider" rowspan="2"></th>'
        short = b["name"][:14] + ("…" if len(b["name"]) > 14 else "")
        html += f'<th colspan="3" style="background:{b["color"]};color:white;">{b["label"]}. {short}</th>'
    html += "</tr><tr>"
    for idx in range(len(all_data)):
        html += '<th class="sub-header">價格漲跌</th><th class="sub-header">票息收益</th><th class="hl">總報酬 ★</th>'
    html += "</tr></thead><tbody>"

    for period_label, _ in periods:
        html += f'<tr><td class="period-col">{period_label}</td>'
        for idx, (b, period_data) in enumerate(all_data):
            if idx > 0: html += '<td class="divider"></td>'
            r = period_data.get(period_label)
            html += f'<td>{fmt(r["price"]) if r else "—"}</td>'
            html += f'<td>{fmt(r["coupon"]) if r else "—"}</td>'
            html += f'<td class="hl">{fmt(r["total"], bold=True) if r else "—"}</td>'
        html += "</tr>"

    wins = [0] * len(all_data)
    for period_label, _ in periods:
        valid = [(i, all_data[i][1].get(period_label)) for i in range(len(all_data))]
        valid = [(i, r) for i, r in valid if r]
        if valid:
            best = max(r["total"] for _, r in valid)
            for i, r in valid:
                if r["total"] >= best - 0.0001: wins[i] += 1

    html += '<tr style="background:#1a2744;"><td class="period-col" style="background:#1a2744;color:#ffd700;font-weight:700;">🏆 勝出</td>'
    for idx, (b, _) in enumerate(all_data):
        if idx > 0: html += '<td class="divider" style="background:#0d1b33;"></td>'
        html += f'<td colspan="2" style="text-align:center;color:#ccc;font-size:0.8rem;">{b["label"]}. {b["name"][:8]}</td>'
        html += f'<td style="text-align:center;color:#ffd700;font-weight:700;">{wins[idx]} 期間</td>'
    html += "</tr>"

    max_wins = max(wins)
    winners = [all_data[i][0] for i, w in enumerate(wins) if w == max_wins]
    overall = (f'🏆 整體較佳：{winners[0]["label"]}. {winners[0]["name"]}' if len(winners)==1
               else "🤝 勢均力敵：" + "、".join(f'{w["label"]}.{w["name"][:6]}' for w in winners))
    oc = winners[0]["color"] if len(winners)==1 else "#888"
    total_cols = len(all_data)*3 + (len(all_data)-1) + 1
    html += f'<tr><td colspan="{total_cols}" style="text-align:center;background:{oc}18;color:{oc};font-weight:700;padding:14px;font-size:0.95rem;">{overall}</td></tr>'
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("""
    <div class="legend">
        <div class="legend-item"><span class="dot" style="background:#c8a84b;"></span>★ 總報酬 = 價格漲跌 + 票息（依實際持有天數）</div>
        <div class="legend-item"><span class="dot" style="background:#2e7d32;"></span>綠色 = 正報酬</div>
        <div class="legend-item"><span class="dot" style="background:#c62828;"></span>紅色 = 負報酬</div>
    </div>
    """, unsafe_allow_html=True)

    # 二、走勢圖
    st.markdown("---")
    st.subheader("📈 價格走勢圖")

    all_min_date = min(df["date"].min() for _, df in loaded).date()
    all_max_date = max(df["date"].max() for _, df in loaded).date()
    today = all_max_date

    st.markdown("**快速選擇區間：**")
    qcol1, qcol2, qcol3, qcol4, qcol5 = st.columns(5)
    if qcol1.button("1年"):
        st.session_state["chart_start_val"] = max(today - timedelta(days=365), all_min_date); st.rerun()
    if qcol2.button("2年"):
        st.session_state["chart_start_val"] = max(today - timedelta(days=730), all_min_date); st.rerun()
    if qcol3.button("3年"):
        st.session_state["chart_start_val"] = max(today - timedelta(days=1095), all_min_date); st.rerun()
    if qcol4.button("5年"):
        st.session_state["chart_start_val"] = max(today - timedelta(days=1825), all_min_date); st.rerun()
    if qcol5.button("全部"):
        st.session_state["chart_start_val"] = all_min_date; st.rerun()

    default_start = st.session_state.get("chart_start_val", all_min_date)
    default_start = max(min(default_start, all_max_date), all_min_date)
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        chart_start = st.date_input("圖表起始日", value=default_start, min_value=all_min_date, max_value=all_max_date, key="chart_start_input")
    with date_col2:
        chart_end = st.date_input("圖表結束日", value=all_max_date, min_value=all_min_date, max_value=all_max_date, key="chart_end_input")

    chart_start_ts = pd.Timestamp(chart_start)
    chart_end_ts   = pd.Timestamp(chart_end)
    loaded_filtered = [(b, df[(df["date"] >= chart_start_ts) & (df["date"] <= chart_end_ts)].copy()) for b, df in loaded]

    tab1, tab2, tab3 = st.tabs(["📊 標準化（不含息）", "📊 標準化（含息）", "💰 實際價格"])
    with tab1:
        st.info("📌 純價格走勢，**不含票息**。起始=100，僅反映債券市價漲跌。")
        fig = go.Figure()
        for b, df in loaded_filtered:
            if df.empty: continue
            norm = df["close"] / df["close"].iloc[0] * 100
            fig.add_trace(go.Scatter(x=df["date"], y=norm, name=f'{b["label"]}. {b["name"]}', line=dict(color=b["color"], width=2)))
        fig.update_layout(yaxis_title="相對價格（起始=100，不含息）", hovermode="x unified", height=430, legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        st.info("📌 **含票息**的總報酬指數。起始=100，每日將票息（年票息率 ÷ 365）累積計入。")
        fig2 = go.Figure()
        for b, df in loaded_filtered:
            if df.empty: continue
            tri = total_return_index(df, b["coupon"])
            fig2.add_trace(go.Scatter(x=df["date"], y=tri, name=f'{b["label"]}. {b["name"]}', line=dict(color=b["color"], width=2)))
        fig2.update_layout(yaxis_title="總報酬指數（起始=100，含息）", hovermode="x unified", height=430, legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig2, use_container_width=True)
    with tab3:
        st.info("📌 TradingView 原始收盤價，面值100為基準，**不含票息**。")
        fig3 = go.Figure()
        for b, df in loaded_filtered:
            if df.empty: continue
            fig3.add_trace(go.Scatter(x=df["date"], y=df["close"], name=f'{b["label"]}. {b["name"]}', line=dict(color=b["color"], width=2)))
        fig3.update_layout(yaxis_title="價格（面值100）", hovermode="x unified", height=430, legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig3, use_container_width=True)

    # 三、年度報酬表
    st.markdown("---")
    st.subheader("📅 年度報酬回顧")

    all_annual = [(b, calc_annual(df, b["coupon"])) for b, df in loaded]
    all_years = sorted(set(r["year"] for _, rows in all_annual for r in rows), reverse=True)

    ann_html = '<table style="width:100%;border-collapse:collapse;font-size:0.84rem;border-radius:8px;overflow:hidden;">'
    ann_html += '<thead><tr><th style="background:#1a2744;color:white;padding:8px 12px;text-align:left;">年度</th>'
    for b, _ in all_annual:
        short = b["name"][:12] + ("…" if len(b["name"]) > 12 else "")
        ann_html += f'<th style="background:{b["color"]};color:white;padding:8px 12px;text-align:center;">{b["label"]}. {short}<br><small style="font-weight:400;">價格漲跌</small></th>'
        ann_html += f'<th style="background:{b["color"]};color:white;padding:8px 12px;text-align:center;">票息收益</th>'
        ann_html += f'<th style="background:{b["color"]};color:white;padding:8px 12px;text-align:center;">總報酬 ★</th>'
    ann_html += "</tr></thead><tbody>"
    for year in all_years:
        ann_html += f'<tr><td style="padding:7px 12px;font-weight:700;color:#1a2744;border-bottom:1px solid #f0f0f0;">{year}</td>'
        for b, rows in all_annual:
            row = next((r for r in rows if r["year"] == year), None)
            if row:
                ann_html += f'<td style="padding:7px 12px;text-align:center;border-bottom:1px solid #f0f0f0;{color_cell(row["price"])}">{row["price"]:+.2%}</td>'
                ann_html += f'<td style="padding:7px 12px;text-align:center;border-bottom:1px solid #f0f0f0;color:#2e7d32;">{row["coupon"]:+.2%}</td>'
                ann_html += f'<td style="padding:7px 12px;text-align:center;border-bottom:1px solid #f0f0f0;{color_cell(row["total"])}font-weight:700;">{row["total"]:+.2%}</td>'
            else:
                ann_html += '<td colspan="3" style="text-align:center;color:#ccc;border-bottom:1px solid #f0f0f0;">無資料</td>'
        ann_html += "</tr>"
    ann_html += "</tbody></table>"
    st.markdown(ann_html, unsafe_allow_html=True)

    # 四、生成 PDF 報告
    st.markdown("---")
    st.subheader("📄 生成比較報告")
    st.caption("PDF 包含：基本資訊、期間績效＋點評、走勢圖＋趨勢解讀、年度報酬＋趨勢分析、Sharpe/MDD 綜合摘要頁")

    report_lang = st.radio("報告語言版本", ["中文版", "English"], horizontal=True)
    lang_code = "zh" if report_lang == "中文版" else "en"
    max_years_pdf = st.slider("年度報酬顯示幾年", min_value=1, max_value=10, value=5, step=1)

    if st.button("🖨️ 生成 PDF 報告", type="primary", use_container_width=True):
        with st.spinner("正在生成報告，請稍候..."):
            try:
                pdf_buf = generate_pdf_report(
                    loaded=loaded, loaded_filtered=loaded_filtered,
                    all_data=all_data, periods=periods,
                    all_annual=all_annual, all_years=all_years,
                    chart_start=str(chart_start), chart_end=str(chart_end),
                    lang=lang_code, max_years=max_years_pdf
                )
                report_date = date.today().strftime("%Y%m%d")
                bond_names = "_".join([b["label"] for b, _ in loaded])
                suffix = "ZH" if lang_code == "zh" else "EN"
                filename = f"Bond_Report_{bond_names}_{report_date}_{suffix}.pdf"
                st.download_button(label="📥 下載 PDF 報告", data=pdf_buf, file_name=filename,
                                   mime="application/pdf", use_container_width=True)
                st.success("✅ 報告生成完成！點擊上方按鈕下載。")
            except Exception as e:
                st.error(f"❌ 報告生成失敗：{e}")
                st.info("💡 請確認 requirements.txt 已包含 reportlab 和 matplotlib")

else:
    st.info("👆 請在上方選擇至少一檔債券開始分析")
    st.markdown("""
    **如何新增債券資料？**
    1. 在 TradingView 搜尋債券 ISIN（需 Plus 以上方案）
    2. 開啟圖表，時間軸往左捲到最左邊
    3. 右上角選單 → **匯出圖表資料...**
    4. 上傳 CSV 到 Google 雲端硬碟的 `bond-data` 資料夾
    5. 重新整理此頁面，下拉選單會自動更新！
    """)

st.markdown("---")
st.warning("⚠️ **免責聲明**：本工具所顯示之價格資料來源為 TradingView，僅供參考，並非本行實際報價。實際申購價格以本行公告為準，投資人應自行評估風險。本工具**僅供內部教育訓練使用，請勿外流**。")
st.caption("資料來源：TradingView ｜ 總報酬 = 價格漲跌 + 票息（依實際持有天數）｜ 僅供參考，不構成投資建議")

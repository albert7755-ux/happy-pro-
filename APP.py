import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import minimize
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import json
import requests
from datetime import datetime
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
MASTER_SHEET_ID = "1PVXcY12Dly5l0HlOyOAKdRzegt4K6gAAQFj1YnhiHqw"
CUTOFF_YEAR = datetime.now().year + 15

# LOCAL_DB 作為備份（bond_master 讀取失敗時使用）
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


# ==========================================
# 現金流試算常數
# ==========================================
FUND_YIELD_DB = {
    "F00001DRQQ_FO": 0.0900,
    "F0GBR04SG1_FO": 0.0850,
    "F00000ZXFV_FO": 0.0938,
    "F00000PR1I_FO": 0.0849,
    "F0000176Y4_FO": 0.0819,
    "F000011JGT_FO": 0.0700,
    "F0GBR04MRL_FO": 0.0781,
    "FOGBR05KHT_FO": 0.0850,
    "F0000000P6_FO": 0.0743,
    "F0GBR04AMK_FO": 0.0660,
    "F00000MLER_FO": 0.0551,
    "F00000T0K2_FO": 0.1259,
    "F00000T1CG_FO": 0.0885,
    "F00000V557_FO": 0.0824,
    "F00001EQPP_FO": 0.0904,
    "F000015CRE_FO": 0.0821,
    "F00000VH29_FO": 0.1000,
}

BOND_CURRENT_YIELD = {
    "US88579YBD22": 0.0489, "US084664CQ25": 0.0484, "XS1807174559": 0.0520,
    "US023135BJ40": 0.0476, "US375558BK80": 0.0483, "US037833CH12": 0.0472,
    "US002824BH26": 0.0505, "XS1508675508": 0.0518, "US02209SAV51": 0.0498,
    "US92343VCK89": 0.0520, "US594918BT09": 0.0442, "US125523CF53": 0.0522,
    "US20030NBU46": 0.0469, "US375558BD48": 0.0508, "US02079KBN63": 0.0521,
    "US30303M8X35": 0.0546, "US747525AK99": 0.0513, "US25468PDB94": 0.0468,
    "US717081DK61": 0.0481, "US449276AF17": 0.0543, "US02209SAR40": 0.0550,
    "US12572QAF28": 0.0513, "US037833AL42": 0.0442, "US084670BK32": 0.0460,
    "US594918BZ68": 0.0412, "US717081EC37": 0.0415, "US035242AM81": 0.0465,
    "US91159HJN17": 0.0543, "US55608KBG94": 0.0521, "US686330AR22": 0.0498,
    "USG91139AL26": 0.0442, "US92556HAC16": 0.0741, "US31428XCA28": 0.0544,
    "US09062XAG88": 0.0468, "US37045VAT70": 0.0595, "US854502AJ02": 0.0541,
    "US00206RCU41": 0.0556, "US94974BGU89": 0.0534, "US172967KR13": 0.0531,
    "US00206RCQ39": 0.0530, "US58013MFA71": 0.0517, "US42824CAY57": 0.0604,
    "US09062XAD57": 0.0543, "US37045VAJ98": 0.0564, "US61747YDY86": 0.0492,
    "US94974BGE48": 0.0525, "US172967HS33": 0.0546, "XS1049699926": 0.0559,
    "US404280AQ21": 0.0530, "US37045VAF76": 0.0600, "US92553PAP71": 0.0638,
    "US00206RBH49": 0.0492, "US71568QAB32": 0.0560, "US854502AA92": 0.0527,
    "US50076QAN60": 0.0594, "XS2885079702": 0.0515, "US46625HHF01": 0.0557,
    "US37045VAP58": 0.0524, "US126650CY46": 0.0495, "US38141GFD16": 0.0594,
    "US00206RDR03": 0.0504, "US404280AG49": 0.0576, "US38143YAC75": 0.0582,
    "US925524AX89": 0.0700, "US37045VAK61": 0.0598, "XS3151416727": 0.0533,
    "US06051GLU12": 0.0545, "XS2852920342": 0.0556, "US458140CA64": 0.0423,
    "US02079KBP12": 0.0565, "US30303MAE21": 0.0563, "US64110LBA35": 0.0540,
    "US03769MAC01": 0.0580, "US191216DS69": 0.0530, "US92343VGW81": 0.0550,
    "XS2747599509": 0.0575, "US29736RAU41": 0.0515, "US037833EW60": 0.0485,
    "US91324PEW86": 0.0505, "US532457CG18": 0.0488, "US91324PES74": 0.0588,
    "US459200KZ37": 0.0510, "US459200KV23": 0.0490, "US45866FAX24": 0.0495,
    "US872898AJ06": 0.0450, "US084664DB47": 0.0385, "US92343VGP31": 0.0388,
    "US828807DJ39": 0.0380, "US191216CQ13": 0.0420, "US254687FM36": 0.0275,
    "XS1982116136": 0.0438, "US58933YAW57": 0.0400, "US125523AK66": 0.0490,
}

BOND_PAY_MONTHS = {
    "US88579YBD22": (9, 3), "US084664CQ25": (8, 2), "XS1807174559": (4, 10),
    "US023135BJ40": (8, 2), "US375558BK80": (3, 9), "US037833CH12": (2, 8),
    "US002824BH26": (11, 5), "XS1508675508": (10, 4), "US02209SAV51": (9, 3),
    "US92343VCK89": (8, 2), "US594918BT09": (8, 2), "US125523CF53": (7, 1),
    "US20030NBU46": (7, 1), "US375558BD48": (3, 9), "US02079KBN63": (2, 8),
    "US30303M8X35": (11, 5), "US747525AK99": (5, 11), "US25468PDB94": (6, 12),
    "US717081DK61": (5, 11), "US449276AF17": (2, 8), "US02209SAR40": (1, 7),
    "US12572QAF28": (9, 3), "US037833AL42": (5, 11), "US084670BK32": (2, 8),
    "US594918BZ68": (2, 8), "US717081EC37": (12, 6), "US035242AM81": (2, 8),
    "US91159HJN17": (6, 12), "US55608KBG94": (11, 5), "US686330AR22": (9, 3),
    "USG91139AL26": (7, 1), "US92556HAC16": (5, 11), "US31428XCA28": (5, 11),
    "US09062XAG88": (5, 11), "US37045VAT70": (4, 10), "US854502AJ02": (11, 5),
    "US00206RCU41": (2, 8), "US94974BGU89": (12, 6), "US172967KR13": (5, 11),
    "US00206RCQ39": (5, 11), "US58013MFA71": (12, 6), "US42824CAY57": (10, 4),
    "US09062XAD57": (9, 3), "US37045VAJ98": (4, 10), "US61747YDY86": (1, 7),
    "US94974BGE48": (11, 5), "US172967HS33": (5, 11), "XS1049699926": (3, 9),
    "US404280AQ21": (3, 9), "US37045VAF76": (10, 4), "US92553PAP71": (3, 9),
    "US00206RBH49": (12, 6), "US71568QAB32": (10, 4), "US854502AA92": (9, 3),
    "US50076QAN60": (2, 8), "XS2885079702": (9, 3), "US46625HHF01": (5, 11),
    "US37045VAP58": (4, 10), "US126650CY46": (3, 9), "US38141GFD16": (10, 4),
    "US00206RDR03": (3, 9), "US404280AG49": (5, 11), "US38143YAC75": (5, 11),
    "US925524AX89": (4, 10), "US37045VAK61": (4, 10), "XS3151416727": (12, 6),
    "US06051GLU12": (9, 3), "XS2852920342": (7, 1), "US458140CA64": (8, 2),
    "US02079KBP12": (1, 7), "US30303MAE21": (11, 5), "US64110LBA35": (9, 3),
    "US03769MAC01": (8, 2), "US191216DS69": (10, 4), "US92343VGW81": (3, 9),
    "XS2747599509": (9, 3), "US29736RAU41": (9, 3), "US037833EW60": (2, 8),
    "US91324PEW86": (10, 4), "US532457CG18": (2, 8), "US91324PES74": (10, 4),
    "US459200KZ37": (2, 8), "US459200KV23": (9, 3), "US45866FAX24": (3, 9),
    "US872898AJ06": (4, 10), "US084664DB47": (3, 9), "US92343VGP31": (8, 2),
    "US828807DJ39": (7, 1), "US191216CQ13": (10, 4), "US254687FM36": (9, 3),
    "XS1982116136": (3, 9), "US58933YAW57": (9, 3), "US125523AK66": (3, 9),
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
    "F000015CRE_FO": "富蘭克林穩定月收益A(acc)",
    "F00000VH29_FO": "施羅德環球收益成長基金",
}

# FINRA ISIN → ticker 對照（用於比對 bond-data 試算表名稱）
FINRA_ISIN_TO_TICKER = {
    "US03769MAC01": "APO5813716",
    "US09062XAG88": "BIIB4981508",
    "US084670BK32": "BRK3963113",
    "US035242AM81": "BUD4327587",
    "US125523AK66": "CI4866401",
    "US125523CF53": "CI5003121",
    "US20030NBU46": "CMCS4382861",
    "US31428XCA28": "FBUO6172956",
    "US375558BD48": "GILD4287890",
    "US37045VAT70": "GM4181484",
    "US404280AG49": "HBC US404280AG49",
    "US449276AF17": "IBM5449458",
    "US45866FAX24": "ICE5414190",
    "US191216CQ13": "KO4969567",
    "US02209SAR40": "MO4065695",
    "US02209SAV51": "MO4403915",
    "US61747YDY86": "MS4204532",
    "US64110LBA35": "NFLX5862368",
    "US747525AK99": "QCOM4246685",
    "XS1049699926": "SCBFF4110430",
    "US854502AJ02": "SDBO4820048",
    "US854502AA92": "SWK.GM",
    "US00206RCQ39": "T4237450",
    "US00206RCU41": "T4451561",
    "US91159HJN17": "USB5600582",
    "US92556HAC16": "VIA4987234",
    "US92343VGW81": "VZ4968008",
    "US92343VFD10": "VZ5363445",
}

# ISIN → LUXSE ticker 對照
LUXSE_ISIN_TO_TICKER = {
    "US06051GLU12": "US06051GLU12",
    "US037833EW60": "US037833EW60",
    "US46625HHF01": "US46625HHF01",
    "US172967HS33": "US172967HS33",
    "XS1807174559": "XS1807174559",
}
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
def load_bond_master():
    """從 bond_master 讀取債券清單（名稱、票息、到期年），失敗則用 LOCAL_DB"""
    try:
        client = get_gspread_client()
        sh = client.open_by_key(MASTER_SHEET_ID)
        ws = sh.get_worksheet(0)
        rows = ws.get_all_records()
        db = dict(LOCAL_DB)  # 以LOCAL_DB為底，用bond_master覆蓋
        import csv as _csv
        for row in rows:
            keys = list(row.keys())
            # 處理欄位擠在一起的CSV格式
            if len(keys) == 1 and ',' in keys[0]:
                col_names = list(next(_csv.reader([keys[0]])))
                values = list(next(_csv.reader([str(list(row.values())[0])])))
                row = dict(zip([c.strip() for c in col_names], [v.strip() for v in values]))
            isin     = str(row.get("ISIN/代碼", "")).strip()
            name     = str(row.get("債券名稱", "")).strip()
            coupon   = row.get("票息率", "")
            maturity = str(row.get("到期年", "")).strip()
            if not isin or not name:
                continue
            try:
                coupon_f = float(coupon) if coupon != "" else db.get(isin, {}).get("coupon", 0.0)
            except:
                coupon_f = db.get(isin, {}).get("coupon", 0.0)
            if not maturity or maturity == "":
                maturity = db.get(isin, {}).get("maturity", "")
            db[isin] = {"issuer": name, "coupon": coupon_f, "maturity": maturity}
        return db
    except Exception as e:
        st.warning(f"⚠️ 無法讀取 bond_master，使用內建資料：{e}")
        return LOCAL_DB

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
    date_col = df.columns[0]
    val_col = df.columns[1]
    try:
        # 先嘗試字串日期（YYYY-MM-DD），再試 Unix timestamp
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")
        if df["date"].isna().mean() > 0.5:
            df["date"] = pd.to_datetime(df[date_col], unit="s", errors="coerce")
    except:
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").set_index("date")
    return df[val_col].astype(float).rename(label)

# ==========================================
# 核心計算函式
# ==========================================
def total_return_series(price_series, coupon_rate):
    prices = price_series.values
    daily_coupon = (coupon_rate / 100) / 365
    tri = [100.0]
    for i in range(1, len(prices)):
        price_ret = (prices[i] - prices[i-1]) / prices[i-1]
        tri.append(tri[-1] * (1 + price_ret + daily_coupon))
    return pd.Series(tri, index=price_series.index)

def calc_annual_ret(price_series):
    """按年度計算平均年化報酬（排除當年度），與智能投資組合優化器一致"""
    ann = price_series.resample('YE').last().pct_change().dropna()
    current_year = datetime.now().year
    if current_year in ann.index.year:
        ann = ann[ann.index.year != current_year]
    return ann.mean() if len(ann) > 0 else price_series.pct_change().mean() * 252

def calc_stats(returns_df):
    """計算年化報酬（年度平均）、標準差、夏普比率"""
    # 先從 returns_df 還原價格指數，再算年度報酬
    price_df = (1 + returns_df).cumprod()
    ann_ret = price_df.apply(calc_annual_ret)
    ann_vol = returns_df.std() * np.sqrt(252)
    sharpe = (ann_ret - RISK_FREE_RATE) / ann_vol
    return ann_ret, ann_vol, sharpe

def calc_max_drawdown(returns_series):
    """計算最大回撤"""
    cum = (1 + returns_series).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    return drawdown.min()

def calc_portfolio_drawdown(returns_df, weights):
    """計算投資組合的最大回撤"""
    port_returns = returns_df.dot(weights)
    return calc_max_drawdown(port_returns)

def run_optimization(returns_df, method="max_sharpe", target_return=0.08, mdd_limit=0.5):
    n = len(returns_df.columns)
    mean_ret = returns_df.mean() * 252
    cov = returns_df.cov() * 252
    bounds = tuple((0, 1) for _ in range(n))
    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    # 加入最大回撤限制（用組合歷史回撤近似）
    if mdd_limit < 0.5:
        port_daily = returns_df.values
        def mdd_constraint(w):
            port_ret_series = port_daily.dot(w)
            cum = np.cumprod(1 + port_ret_series)
            peak = np.maximum.accumulate(cum)
            drawdown = (cum - peak) / peak
            return mdd_limit + drawdown.min()  # >= 0 表示回撤在限制內
        constraints.append({"type": "ineq", "fun": mdd_constraint})
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
    else:
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
    for path in ["/tmp/wqy_microhei.ttc", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]:
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
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=2*cm, bottomMargin=2*cm)
    title_s = ParagraphStyle("t", fontName=font, fontSize=20, textColor=WHITE, alignment=TA_CENTER)
    sub_s   = ParagraphStyle("s", fontName=font, fontSize=10, textColor=colors.HexColor("#cce0ff"), alignment=TA_CENTER)
    h2_s    = ParagraphStyle("h2", fontName=font, fontSize=12, textColor=NAVY, spaceBefore=12, spaceAfter=6)
    small_s = ParagraphStyle("sm", fontName=font, fontSize=8, textColor=colors.HexColor("#555"))
    warn_s  = ParagraphStyle("w", fontName=font, fontSize=7.5, textColor=RED, backColor=colors.HexColor("#fff3cd"), borderPadding=6, spaceBefore=8)
    story = []
    title_tbl = Table(
        [[Paragraph("最適投資組合分析報告", title_s)],
         [Paragraph(f"策略：{method_name}　｜　回測期間：{period_label}　｜　製作日期：{datetime.today().strftime('%Y-%m-%d')}", sub_s)]],
        colWidths=[17*cm]
    )
    title_tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),("TOPPADDING",(0,0),(-1,-1),16),("BOTTOMPADDING",(0,0),(-1,-1),16)]))
    story.append(title_tbl)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("一、整體組合預期績效", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    var_68 = port_ret - port_vol
    var_95 = port_ret - 1.645 * port_vol
    var_99 = port_ret - 2.326 * port_vol
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
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("ROWBACKGROUNDS",(0,1),(-1,-1),[BG,WHITE]),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("TEXTCOLOR",(1,4),(1,6),RED),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("※ 信賴區間基於常態分配假設計算，實際報酬分佈可能有厚尾風險，請審慎參考。", small_s))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("二、建議配置權重", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    w_data = [["標的", "配置比例", "年化報酬", "年化波動", "夏普比率"]]
    for i, (lbl, w) in enumerate(zip(labels, weights)):
        if w > 0.001:
            w_data.append([lbl, f"{w:.1%}", f"{ann_ret.iloc[i]:.2%}", f"{ann_vol.iloc[i]:.2%}", f"{sharpe.iloc[i]:.2f}"])
    w_tbl = Table(w_data, colWidths=[6.5*cm, 2.2*cm, 2.5*cm, 2.5*cm, 2.3*cm])
    w_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("ROWBACKGROUNDS",(0,1),(-1,-1),[BG,WHITE]),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(w_tbl)
    story.append(Spacer(1, 0.3*cm))
    # 各標的完整統計（含MDD）
    stats_hdr = ["標的", "建議配置", "年化報酬", "年化波動", "夏普比率", "最大回撤"]
    stats_rows = [stats_hdr]
    for i, lbl in enumerate(labels):
        w_i = weights[i]
        mdd_val = "-"
        if lbl in returns_df.columns:
            cum = (1 + returns_df[lbl]).cumprod()
            peak = cum.cummax()
            mdd_val = f"{((cum - peak) / peak).min():.2%}"
        # 配置0%用灰色標示
        stats_rows.append([
            lbl[:14], f"{w_i:.1%}",
            f"{ann_ret.iloc[i]:.2%}", f"{ann_vol.iloc[i]:.2%}",
            f"{sharpe.iloc[i]:.2f}", mdd_val
        ])
    stats_tbl = Table(stats_rows, colWidths=[5.5*cm, 2*cm, 2.2*cm, 2.2*cm, 2*cm, 2.1*cm])
    # 0%配置的行用灰色標示
    stats_style = [
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("ROWBACKGROUNDS",(0,1),(-1,-1),[BG,WHITE]),
    ]
    for ri in range(1, len(stats_rows)):
        if stats_rows[ri][1] == "0.0%":
            stats_style.append(("TEXTCOLOR",(0,ri),(-1,ri),colors.HexColor("#999999")))
    stats_tbl.setStyle(TableStyle(stats_style + [
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(stats_tbl)
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("三、相關係數矩陣", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    corr = returns_df.corr()
    short_labels = [lbl[:10] for lbl in corr.columns.tolist()]
    corr_rows = [[""] + short_labels]
    for i, lbl in enumerate(short_labels):
        corr_rows.append([lbl] + [f"{corr.iloc[i,j]:.2f}" for j in range(len(short_labels))])
    n_cols = len(short_labels) + 1
    corr_tbl = Table(corr_rows, colWidths=[17*cm/n_cols]*n_cols)
    corr_style = [
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("BACKGROUND",(0,0),(0,-1),NAVY),("TEXTCOLOR",(0,0),(0,-1),WHITE),
        ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),7),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]
    for i in range(1, len(corr_rows)):
        for j in range(1, n_cols):
            try:
                val = float(corr_rows[i][j])
                if i != j:
                    if val > 0.7:
                        corr_style.append(("BACKGROUND",(j,i),(j,i),colors.HexColor("#ffcdd2")))
                    elif val < 0.3:
                        corr_style.append(("BACKGROUND",(j,i),(j,i),colors.HexColor("#c8e6c9")))
            except:
                pass
    corr_tbl.setStyle(TableStyle(corr_style))
    story.append(corr_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("※ 紅底=高相關(>0.7)，綠底=低相關(<0.3)。低相關標的有助分散風險。", small_s))

    # ── 四、持有期間正報酬機率 ──
    story.append(PageBreak())
    story.append(Paragraph("四、持有期間正報酬機率", h2_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    holding_periods_pdf = {"1個月":21,"3個月":63,"6個月":126,"1年":252,"2年":504,"3年":756}
    port_daily_pdf = returns_df.dot(weights)
    all_series_pdf = {"投資組合": port_daily_pdf}
    for lbl in returns_df.columns:
        all_series_pdf[lbl[:8]] = returns_df[lbl]
    win_headers = ["持有期間"] + list(all_series_pdf.keys())
    win_rows = [win_headers]
    for pname, days in holding_periods_pdf.items():
        row = [pname]
        for sname, series in all_series_pdf.items():
            rolling = (1 + series).rolling(days).apply(np.prod, raw=True) - 1
            rolling = rolling.dropna()
            if len(rolling) > 0:
                row.append(f"{(rolling > 0).mean():.1%}")
            else:
                row.append("-")
        win_rows.append(row)
    n_wcols = len(win_headers)
    win_tbl = Table(win_rows, colWidths=[17*cm/n_wcols]*n_wcols)
    win_style = [
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("BACKGROUND",(0,1),(0,-1),colors.HexColor("#e8edf5")),("TEXTCOLOR",(0,1),(0,-1),NAVY),
        ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),7.5),
        ("FONTNAME",(0,1),(0,-1),font),("FONTSIZE",(0,1),(0,-1),7.5),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("ROWBACKGROUNDS",(1,1),(-1,-1),[BG,WHITE]),
    ]
    for ri in range(1, len(win_rows)):
        for ci in range(1, n_wcols):
            try:
                v = float(win_rows[ri][ci].replace("%","")) / 100
                if v >= 0.8:
                    win_style.append(("BACKGROUND",(ci,ri),(ci,ri),colors.HexColor("#c8e6c9")))
                elif v < 0.6:
                    win_style.append(("BACKGROUND",(ci,ri),(ci,ri),colors.HexColor("#ffcdd2")))
            except: pass
    win_tbl.setStyle(TableStyle(win_style))
    story.append(win_tbl)

    # ── 六、現金流試算 ──
    cf_items_pdf = st.session_state.get("cf_items_auto", [])
    monthly_total_pdf = st.session_state.get("monthly_total", [])
    principal_cf_pdf = st.session_state.get("principal_cf", 0)
    total_income_pdf = st.session_state.get("total_income_cf", 0)
    avg_yield_pdf = st.session_state.get("avg_yield_cf", 0)

    if cf_items_pdf and monthly_total_pdf:
        story.append(PageBreak())
        story.append(Paragraph("五、配息現金流試算", h2_s))
        story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))

        # KPI 摘要
        kpi_cf = [
            ["投資本金", "年化配息率", "年領總息", "月均領息"],
            [f"NT${principal_cf_pdf:,.0f}", f"{avg_yield_pdf:.2f}%", f"NT${total_income_pdf:,.0f}", f"NT${total_income_pdf/12:,.0f}"],
        ]
        kpi_cf_tbl = Table(kpi_cf, colWidths=[4.25*cm]*4)
        kpi_cf_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("BACKGROUND",(0,1),(-1,1),BG),
            ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),9),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(kpi_cf_tbl)
        story.append(Spacer(1, 0.4*cm))

        # 各標的配息明細
        story.append(Paragraph("各標的配息明細", h2_s))
        detail_hdr = ["標的","類型","配置比例","配置金額","殖利率/配息率","年配息","配息頻率"]
        detail_rows_pdf = [detail_hdr]
        for item in cf_items_pdf:
            freq = "月配" if item["type"] == "FUND" else f"{item['pay_months'][0]}月/{item['pay_months'][1]}月"
            detail_rows_pdf.append([
                item["name"][:12], item["type"],
                f"{item['weight']:.1%}", f"NT${item['amount']:,.0f}",
                f"{item['yield_pct']:.2%}", f"NT${item['annual_income']:,.0f}", freq
            ])
        detail_tbl = Table(detail_rows_pdf, colWidths=[4*cm,1.5*cm,2*cm,2.5*cm,2.5*cm,2.5*cm,2*cm])
        detail_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),7.5),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),("ROWBACKGROUNDS",(0,1),(-1,-1),[BG,WHITE]),
            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        story.append(detail_tbl)
        story.append(Spacer(1, 0.4*cm))

        # 逐月現金流表
        story.append(Paragraph("逐月現金流明細", h2_s))
        months_pdf = ["一月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","十二月"]
        cf_hdr = ["月份"] + [f"{x['label']}.{x['name'][:6]}" for x in cf_items_pdf] + ["當月合計"]
        cf_tbl_rows = [cf_hdr]
        for m_idx, mname in enumerate(months_pdf):
            m = m_idx + 1
            row = [mname]
            for item in cf_items_pdf:
                if item["type"] == "FUND":
                    row.append(f"NT${item['annual_income']/12:,.0f}")
                else:
                    if m in item["pay_months"]:
                        row.append(f"NT${item['annual_income']/2:,.0f}")
                    else:
                        row.append("—")
            row.append(f"${monthly_total_pdf[m_idx]:,.0f}")
            cf_tbl_rows.append(row)
        # 全年合計行
        total_row = ["全年合計"] + [f"${x['annual_income']:,.0f}" for x in cf_items_pdf] + [f"NT${total_income_pdf:,.0f}"]
        cf_tbl_rows.append(total_row)

        n_cf_cols = len(cf_hdr)
        cf_pdf_tbl = Table(cf_tbl_rows, colWidths=[17*cm/n_cf_cols]*n_cf_cols)
        cf_pdf_style = [
            ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("BACKGROUND",(0,-1),(-1,-1),NAVY),("TEXTCOLOR",(0,-1),(-1,-1),colors.HexColor("#ffd700")),
            ("BACKGROUND",(-1,1),(-1,-2),colors.HexColor("#fff9e6")),
            ("TEXTCOLOR",(-1,1),(-1,-2),colors.HexColor("#b8860b")),
            ("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),7),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),("ROWBACKGROUNDS",(0,1),(-1,-2),[BG,WHITE]),
            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ]
        cf_pdf_tbl.setStyle(TableStyle(cf_pdf_style))
        story.append(cf_pdf_tbl)

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#888"), spaceAfter=6))
    story.append(Paragraph("⚠️ 免責聲明：本報告所有數據均基於歷史資料計算，不代表未來績效。配息金額以各機構實際公告為準。僅供內部教育訓練使用，請勿外流。", warn_s))
    doc.build(story)
    buf.seek(0)
    buf.seek(0)
    return buf

# ==========================================
# 主介面
# ==========================================
st.markdown("## 📐 最適投資組合優化器")
st.markdown("結合債券（94檔）、基金（15檔）、自選股票/ETF，計算最適配置比例")
st.markdown("---")

# 載入 bond_master
BOND_DB = load_bond_master()

st.sidebar.header("1. 回測期間")
period_options = {"1年": 1, "2年": 2, "3年": 3, "4年": 4, "5年": 5}
period_label = st.sidebar.radio("選擇回測期間", list(period_options.keys()), horizontal=True)
years = period_options[period_label]
st.sidebar.header("2. 優化目標")
method_map = {"最大夏普比率": "max_sharpe", "最小風險": "min_vol", "鎖定目標報酬": "target_return"}
method_label = st.sidebar.radio("選擇策略", list(method_map.keys()))
method = method_map[method_label]
target_return = 0.08
if method == "target_return":
    target_return = st.sidebar.slider("目標年化報酬率 %", 1.0, 30.0, 8.0, 0.5) / 100

st.sidebar.header("3. 最大回撤限制")
mdd_limit_pct = st.sidebar.slider(
    "可接受最大回撤上限 %",
    min_value=5, max_value=50, value=50, step=1,
    help="設定越小，組合越保守；50% 表示不限制"
)
mdd_limit = mdd_limit_pct / 100

tab_select, tab_result, tab_manual = st.tabs(["📋 標的選擇", "📊 分析結果", "✏️ 手動配置試算"])

with tab_select:
    st.subheader("選擇要納入的標的")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**債券（{len(BOND_DB)}檔）**")
        bond_names = {
            f"{v['issuer']} {v['coupon']}% {v['maturity']}": k
            for k, v in BOND_DB.items()
            if v.get("coupon") and v.get("maturity")
        }
        selected_bond_names = st.multiselect("選擇債券（可多選）", options=sorted(bond_names.keys()), default=[])
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
        extra_input = st.text_area("輸入代號（每行一個或空白隔開）", placeholder="例如：\nAAPL\nTSLA\nSPY", height=180)
        extra_tickers = [t.strip().upper() for t in extra_input.replace(",", " ").split() if t.strip()]

    total_selected = len(selected_bonds) + len(selected_funds) + len(extra_tickers)
    if total_selected < 2:
        st.warning("請至少選擇 2 個標的！")
    else:
        st.success(f"已選擇 {total_selected} 個標的（債券 {len(selected_bonds)} + 基金 {len(selected_funds)} + 股票/ETF {len(extra_tickers)}）")
    run_btn = st.button("🚀 開始計算最適組合", type="primary", use_container_width=True, disabled=(total_selected < 2))

# ==========================================
# 執行計算
# ==========================================
if "result_ready" not in st.session_state:
    st.session_state.result_ready = False

if run_btn and total_selected >= 2:
    with st.spinner("正在讀取資料並計算中，請稍候..."):
        try:
            end_date = pd.Timestamp.today()
            start_date = end_date - pd.DateOffset(years=years)
            all_series = {}
            labels = []

            if selected_bonds:
                bond_sheets = list_sheets_in_folder(BOND_FOLDER_ID)
                vclt_raw = yf.download("VCLT", start=start_date - pd.DateOffset(years=3), end=end_date, auto_adjust=True, progress=False)["Close"].squeeze()
                lqd_raw  = yf.download("LQD",  start=start_date - pd.DateOffset(years=3), end=end_date, auto_adjust=True, progress=False)["Close"].squeeze()
                vclt_ret = vclt_raw.pct_change().dropna()
                lqd_ret  = lqd_raw.pct_change().dropna()
                for isin in selected_bonds:
                    info  = BOND_DB[isin]
                    label = info["issuer"]
                    sheet_id = None
                    # 先查 FINRA 對照表
                    finra_ticker = FINRA_ISIN_TO_TICKER.get(isin)
                    if finra_ticker:
                        for sname, sid in bond_sheets.items():
                            if finra_ticker in sname:
                                sheet_id = sid
                                break
                    # 再查 LUXSE
                    if not sheet_id and isin in LUXSE_ISIN_TO_TICKER:
                        for sname, sid in bond_sheets.items():
                            if "LUXSE" in sname and isin in sname:
                                sheet_id = sid
                                break
                    # 最後用 ISIN 直接比對（SWB、EUROTLX）
                    if not sheet_id:
                        for sname, sid in bond_sheets.items():
                            if isin in sname:
                                sheet_id = sid
                                break
                    if not sheet_id:
                        st.warning(f"找不到 {label} 的資料，跳過")
                        continue
                    price_s = read_sheet_as_series(sheet_id, label)
                    tri = total_return_series(price_s, info["coupon"])
                    tri_ret = tri.pct_change().dropna()
                    tri_ret = tri_ret[tri_ret.index >= start_date]
                    maturity_year = int(info["maturity"]) if info["maturity"] else CUTOFF_YEAR
                    proxy_ret   = vclt_ret if maturity_year >= CUTOFF_YEAR else lqd_ret
                    proxy_label = "VCLT"   if maturity_year >= CUTOFF_YEAR else "LQD"
                    if len(tri_ret) < 20:
                        all_series[label] = proxy_ret[proxy_ret.index >= start_date]
                        st.info(f"{label}：資料不足，使用 {proxy_label} 替代")
                    else:
                        first_date = tri_ret.index[0]
                        if first_date > start_date:
                            pre_ret = proxy_ret[(proxy_ret.index >= start_date) & (proxy_ret.index < first_date)]
                            combined = pd.concat([pre_ret.rename(label), tri_ret])
                        else:
                            combined = tri_ret
                        all_series[label] = combined
                    labels.append(label)

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

            if extra_tickers:
                raw = yf.download(extra_tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)
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
            weights = run_optimization(returns_df, method=method, target_return=target_return, mdd_limit=mdd_limit)
            cov = returns_df.cov() * 252
            # 組合年化報酬：用實際組合日報酬序列算年度平均
            port_daily_ret = returns_df.dot(weights)
            port_ret    = float(calc_annual_ret((1 + port_daily_ret).cumprod()))
            port_vol    = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))
            port_sharpe = (port_ret - RISK_FREE_RATE) / port_vol
            port_mdd    = float(calc_portfolio_drawdown(returns_df, weights))
            mdd_series  = returns_df.apply(calc_max_drawdown)

            st.session_state.update({
                "result_ready": True,
                "returns_df": returns_df,
                "ann_ret": ann_ret, "ann_vol": ann_vol, "sharpe_r": sharpe_r,
                "weights": weights, "labels": labels,
                "port_ret": port_ret, "port_vol": port_vol, "port_sharpe": port_sharpe,
                "port_mdd": port_mdd, "mdd_series": mdd_series,
                "period_label": period_label, "method_label": method_label,
            })
        except Exception as e:
            st.error(f"發生錯誤：{e}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# 顯示結果
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
    port_mdd    = st.session_state.get("port_mdd", None)
    mdd_series  = st.session_state.get("mdd_series", None)

    with tab_result:
        st.subheader(f"最適組合：{st.session_state.method_label}")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("組合年化報酬", f"{port_ret:.2%}")
        k2.metric("組合年化波動", f"{port_vol:.2%}")
        k3.metric("組合夏普比率", f"{port_sharpe:.2f}")
        k4.metric("最大回撤 MDD", f"{port_mdd:.2%}" if port_mdd is not None else "-")
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

        left_col, right_col = st.columns([3, 2])
        with left_col:
            st.markdown("**各標的統計**")
            stats_data = []
            for i, lbl in enumerate(labels):
                mdd_val = f"{mdd_series[lbl]:.2%}" if mdd_series is not None and lbl in mdd_series else "-"
                stats_data.append({
                    "標的": lbl,
                    "配置": f"{weights[i]:.1%}",
                    "年化報酬": f"{ann_ret.iloc[i]:.2%}",
                    "年化波動": f"{ann_vol.iloc[i]:.2%}",
                    "夏普": f"{sharpe_r.iloc[i]:.2f}",
                    "最大回撤": mdd_val,
                })
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
        with right_col:
            sig_weights = [(lbl, w) for lbl, w in zip(labels, weights) if w > 0.01]
            if sig_weights:
                pie_labels, pie_values = zip(*sig_weights)
                fig_pie = go.Figure(go.Pie(labels=pie_labels, values=pie_values, hole=0.4, textinfo="none", showlegend=True))
                fig_pie.update_layout(
                    height=320, margin=dict(t=10, b=0),
                    legend=dict(font=dict(size=13), itemsizing="constant")
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("---")

        st.markdown("**有效前緣**")
        with st.spinner("計算有效前緣中..."):
            vols, rets = efficient_frontier(returns_df)
        cov = returns_df.cov() * 252
        opt_w_sharpe = run_optimization(returns_df, method="max_sharpe")
        opt_w_minvol = run_optimization(returns_df, method="min_vol")
        # 計算當前投組（使用者選擇的策略）的位置
        cur_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))
        cur_ret = float(port_ret)
        fig_ef = go.Figure()
        fig_ef.add_trace(go.Scatter(x=vols, y=rets, mode="lines", line=dict(color="#1565c0", width=2.5), name="有效前緣"))
        fig_ef.add_trace(go.Scatter(x=ann_vol.values, y=ann_ret.values, mode="markers+text", text=labels, textposition="top center", marker=dict(size=8, color="#888"), name="各標的"))
        fig_ef.add_trace(go.Scatter(x=[float(np.sqrt(np.dot(opt_w_sharpe.T, np.dot(cov, opt_w_sharpe))))], y=[float(np.dot(opt_w_sharpe, ann_ret))], mode="markers", marker=dict(size=14, color="#c8a84b", symbol="star"), name="最大夏普"))
        fig_ef.add_trace(go.Scatter(x=[float(np.sqrt(np.dot(opt_w_minvol.T, np.dot(cov, opt_w_minvol))))], y=[float(np.dot(opt_w_minvol, ann_ret))], mode="markers", marker=dict(size=12, color="#2e7d32", symbol="diamond"), name="最小風險"))
        # ★ 加入當前投組位置
        fig_ef.add_trace(go.Scatter(
            x=[cur_vol], y=[cur_ret], mode="markers+text",
            text=[f"▶ 目前投組（{st.session_state.method_label}）"],
            textposition="top right",
            marker=dict(size=16, color="#e53935", symbol="circle"),
            name=f"目前投組（{st.session_state.method_label}）"
        ))
        fig_ef.update_layout(xaxis_title="年化波動率", yaxis_title="年化報酬率", hovermode="closest", height=420, xaxis=dict(tickformat=".1%"), yaxis=dict(tickformat=".1%"))
        st.plotly_chart(fig_ef, use_container_width=True)
        st.markdown("---")

        st.markdown("**持有期間愈長，正報酬機率**")
        holding_periods = {
            "1個月": 21, "3個月": 63, "6個月": 126,
            "1年": 252, "2年": 504, "3年": 756
        }

        def calc_win_rate(ret_series, days):
            rolling = (1 + ret_series).rolling(days).apply(np.prod, raw=True) - 1
            rolling = rolling.dropna()
            if len(rolling) == 0:
                return None
            return (rolling > 0).mean()

        # 建立橫軸=標的、縱軸=持有期間的矩陣
        port_daily_ret_prob = returns_df.dot(weights)
        all_series = {"📐 投資組合": port_daily_ret_prob}
        for lbl in labels:
            if lbl in returns_df.columns:
                all_series[lbl] = returns_df[lbl]

        prob_matrix = {}
        for period_name, days in holding_periods.items():
            row = {}
            for name, series in all_series.items():
                wr = calc_win_rate(series, days)
                row[name] = f"{wr:.1%}" if wr is not None else "-"
            prob_matrix[period_name] = row

        prob_df = pd.DataFrame(prob_matrix).T
        prob_df.index.name = "持有期間"
        prob_df = prob_df.reset_index()

        def color_winrate(val):
            try:
                v = float(str(val).replace("%","")) / 100
                if v >= 0.8: return "background-color: #c8e6c9; color: #1b5e20; font-weight:bold"
                elif v >= 0.6: return "background-color: #fff9c4; color: #f57f17"
                else: return "background-color: #ffcdd2; color: #b71c1c"
            except: return ""

        # 所有欄位（除了持有期間）都上色
        color_cols = [c for c in prob_df.columns if c != "持有期間"]
        st.dataframe(
            prob_df.style.map(color_winrate, subset=color_cols),
            use_container_width=True, hide_index=True
        )
        st.caption("※ 基於歷史滾動報酬計算。綠=≥80%、黃=60-80%、紅=<60%，結果僅供參考。")
        st.markdown("---")

        st.markdown("**相關係數矩陣**")
        corr = returns_df.corr()
        fig_corr = go.Figure(go.Heatmap(z=corr.values, x=[l[:10] for l in corr.columns.tolist()], y=[l[:10] for l in corr.index.tolist()], colorscale="RdYlGn", zmin=-1, zmax=1, text=np.round(corr.values, 2), texttemplate="%{text}", textfont={"size": 9}))
        fig_corr.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_corr, use_container_width=True)
        st.markdown("---")

        with st.expander("🔍 資料明細（點擊展開）"):
            st.markdown("**各標的資料來源說明**")
            meta_rows = []
            for lbl in labels:
                isin = next((k for k, v in BOND_DB.items() if v["issuer"] == lbl), None)
                col_data = returns_df[lbl].dropna() if lbl in returns_df.columns else None
                data_start = col_data.index[0].strftime("%Y-%m-%d") if col_data is not None else "-"
                data_end   = col_data.index[-1].strftime("%Y-%m-%d") if col_data is not None else "-"
                n_days     = len(col_data) if col_data is not None else 0
                if isin:
                    info = BOND_DB[isin]
                    maturity_year = int(info["maturity"]) if info["maturity"] else CUTOFF_YEAR
                    proxy = "VCLT（15年以上）" if maturity_year >= CUTOFF_YEAR else "LQD（15年以下）"
                    meta_rows.append({"標的": lbl, "類型": "債券", "ISIN": isin, "到期年": info["maturity"], "票息": f"{info['coupon']}%", "不足時補齊用": proxy, "資料起始": data_start, "資料結束": data_end, "有效交易日": n_days})
                elif lbl in FUND_DB.values():
                    meta_rows.append({"標的": lbl, "類型": "基金", "ISIN": "-", "到期年": "-", "票息": "-", "不足時補齊用": "-", "資料起始": data_start, "資料結束": data_end, "有效交易日": n_days})
                else:
                    meta_rows.append({"標的": lbl, "類型": "股票/ETF", "ISIN": "-", "到期年": "-", "票息": "-", "不足時補齊用": "-", "資料起始": data_start, "資料結束": data_end, "有效交易日": n_days})
            st.dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)
            st.markdown("---")
            st.markdown("**月報酬率（各標的 + 投資組合）**")
            # 各標的月報酬
            monthly_df = (1 + returns_df).resample("ME").prod() - 1
            # 加入投組月報酬
            port_daily_ret_disp = returns_df.dot(weights)
            port_monthly_ret = (1 + port_daily_ret_disp).resample("ME").prod() - 1
            monthly_df.insert(0, "📐 投資組合", port_monthly_ret)
            monthly_df.index = monthly_df.index.strftime("%Y-%m")
            monthly_df = monthly_df.sort_index(ascending=False)
            st.dataframe(
                monthly_df.style.format("{:.2%}").background_gradient(cmap="RdYlGn", vmin=-0.08, vmax=0.08),
                use_container_width=True, height=400
            )
        st.markdown("---")

        # ==========================================
        # 現金流試算區塊
        # ==========================================
        st.markdown("---")
        st.subheader("💰 配息現金流試算")
        st.caption("根據最適配置比例自動帶入，債券使用當前殖利率，基金配息率可手動調整。")

        principal_cf = st.number_input("投資本金（台幣）", min_value=100000, max_value=100000000, value=10000000, step=100000, format="%d")

        # 基金配息率調整
        fund_labels_in = [lbl for lbl, w in zip(labels, weights) if w > 0.001 and lbl in [FUND_DB.get(k, "") for k in FUND_DB]]
        fund_ticker_map = {v: k for k, v in FUND_DB.items()}

        adjusted_yields = {}
        bond_labels_in = []
        fund_labels_cf = []

        for lbl, w in zip(labels, weights):
            if w <= 0.001:
                continue
            ticker = fund_ticker_map.get(lbl)
            if ticker and ticker in FUND_YIELD_DB:
                fund_labels_cf.append((lbl, ticker, w))
            else:
                # 找 ISIN
                isin = next((k for k, v in BOND_DB.items() if v["issuer"] == lbl), None)
                if isin:
                    bond_labels_in.append((lbl, isin, w))

        if fund_labels_cf:
            st.markdown("**📊 基金配息率調整**")
            fund_cols = st.columns(min(len(fund_labels_cf), 3))
            for i, (lbl, ticker, w) in enumerate(fund_labels_cf):
                default_yield = FUND_YIELD_DB.get(ticker, 0.08)
                with fund_cols[i % 3]:
                    adj = st.slider(
                        f"{lbl[:12]}",
                        min_value=1.0, max_value=20.0,
                        value=round(default_yield * 100, 2),
                        step=0.01, format="%.2f%%"
                    ) / 100
                    adjusted_yields[ticker] = adj

        # 計算現金流
        months_names = ["一月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","十二月"]
        monthly_total = [0.0] * 12
        cf_items_auto = []
        COLORS_CF = ["#1565c0","#c62828","#2e7d32","#6a1b9a","#e65100","#00838f","#ad1457","#00695c","#f57f17","#4527a0"]

        for i, (lbl, ticker, w) in enumerate(fund_labels_cf):
            amt = principal_cf * w
            yield_rate = adjusted_yields.get(ticker, FUND_YIELD_DB.get(ticker, 0.08))
            annual_income = amt * yield_rate
            monthly_income = annual_income / 12
            cf_items_auto.append({
                "label": chr(65+i), "name": lbl, "type": "FUND",
                "amount": amt, "weight": w, "yield_pct": yield_rate,
                "annual_income": annual_income, "color": COLORS_CF[i % len(COLORS_CF)]
            })
            for m in range(12):
                monthly_total[m] += monthly_income

        bond_offset = len(fund_labels_cf)
        for j, (lbl, isin, w) in enumerate(bond_labels_in):
            amt = principal_cf * w
            yield_rate = BOND_CURRENT_YIELD.get(isin, BOND_DB.get(isin, {}).get("coupon", 5.0) / 100)
            annual_income = amt * yield_rate
            pay_months = BOND_PAY_MONTHS.get(isin, (3, 9))
            cf_items_auto.append({
                "label": chr(65 + bond_offset + j), "name": lbl, "type": "BOND",
                "isin": isin, "amount": amt, "weight": w, "yield_pct": yield_rate,
                "annual_income": annual_income, "color": COLORS_CF[(bond_offset+j) % len(COLORS_CF)],
                "pay_months": pay_months
            })
            for m in pay_months:
                monthly_total[m-1] += annual_income / 2

        if cf_items_auto:
            total_income_cf = sum(x["annual_income"] for x in cf_items_auto)
            avg_yield_cf = total_income_cf / principal_cf * 100 if principal_cf > 0 else 0
            max_m_idx = monthly_total.index(max(monthly_total))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 本金", f"NT${principal_cf:,.0f}")
            c2.metric("📈 年化配息率", f"{avg_yield_cf:.2f}%")
            c3.metric("🎯 年領總息", f"NT${total_income_cf:,.0f}")
            c4.metric("📅 月均領息", f"NT${total_income_cf/12:,.0f}")

            st.markdown("---")
            # 逐月現金流表格
            st.markdown("**📅 逐月現金流明細**")
            cf_html = '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;border-radius:8px;overflow:hidden;">'
            cf_html += '<thead><tr><th style="background:#1a2744;color:white;padding:8px 12px;text-align:left;">月份</th>'
            for item in cf_items_auto:
                cf_html += f'<th style="background:{item["color"]};color:white;padding:8px 12px;text-align:center;">{item["label"]}. {item["name"][:8]}</th>'
            cf_html += '<th style="background:#c8a84b;color:white;padding:8px 12px;text-align:center;">當月合計</th></tr></thead><tbody>'

            for m_idx, mname in enumerate(months_names):
                m = m_idx + 1
                bg = "#f0f4ff" if m_idx % 2 == 0 else "white"
                cf_html += f'<tr style="background:{bg};"><td style="padding:7px 12px;font-weight:700;color:#1a2744;">{mname}</td>'
                for item in cf_items_auto:
                    if item["type"] == "FUND":
                        val = item["annual_income"] / 12
                        cf_html += f'<td style="padding:7px 12px;text-align:right;">${val:,.0f}</td>'
                    else:
                        if m in item["pay_months"]:
                            val = item["annual_income"] / 2
                            cf_html += f'<td style="padding:7px 12px;text-align:right;font-weight:600;color:#1565c0;">${val:,.0f}</td>'
                        else:
                            cf_html += '<td style="padding:7px 12px;text-align:center;color:#ccc;">—</td>'
                cf_html += f'<td style="padding:7px 12px;text-align:right;font-weight:700;color:#c8a84b;">${monthly_total[m_idx]:,.0f}</td></tr>'

            cf_html += '<tr style="background:#1a2744;"><td style="padding:8px 12px;color:#ffd700;font-weight:700;">全年合計</td>'
            for item in cf_items_auto:
                cf_html += f'<td style="padding:8px 12px;text-align:right;color:white;font-weight:700;">${item["annual_income"]:,.0f}</td>'
            cf_html += f'<td style="padding:8px 12px;text-align:right;color:#ffd700;font-weight:700;">${total_income_cf:,.0f}</td></tr>'
            cf_html += '</tbody></table>'
            st.markdown(cf_html, unsafe_allow_html=True)

            st.markdown("---")
            # 月現金流長條圖
            st.markdown("**📊 月現金流圖表**")
            fig_cf = go.Figure()
            fig_cf.add_trace(go.Bar(
                x=months_names, y=monthly_total,
                marker_color=["#1565c0" if i == max_m_idx else "#90caf9" for i in range(12)],
                text=[f"${v:,.0f}" for v in monthly_total],
                textposition="outside"
            ))
            fig_cf.update_layout(
                yaxis_title="配息金額（美元）", height=350,
                plot_bgcolor="#f8f9ff", paper_bgcolor="white",
                showlegend=False, margin=dict(t=20, b=40)
            )
            st.plotly_chart(fig_cf, use_container_width=True)

            # 配息率明細
            st.markdown("**📋 各標的配息明細**")
            detail_rows = []
            for item in cf_items_auto:
                detail_rows.append({
                    "標的": item["name"],
                    "類型": item["type"],
                    "配置比例": f"{item['weight']:.1%}",
                    "配置金額": f"NT${item['amount']:,.0f}",
                    "殖利率/配息率": f"{item['yield_pct']:.2%}",
                    "年配息": f"NT${item['annual_income']:,.0f}",
                    "月均配息": f"NT${item['annual_income']/12:,.0f}",
                    "配息頻率": "月配" if item["type"] == "FUND" else f"{item['pay_months'][0]}月/{item['pay_months'][1]}月",
                })
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
            st.caption("※ 債券使用當前殖利率估算，基金配息率可調整。實際配息以各機構公告為準，僅供參考。")

            # 存入 session_state 供 PDF 使用
            st.session_state["cf_items_auto"] = cf_items_auto
            st.session_state["monthly_total"] = monthly_total
            st.session_state["principal_cf"] = principal_cf
            st.session_state["total_income_cf"] = total_income_cf
            st.session_state["avg_yield_cf"] = avg_yield_cf

        st.markdown("---")
        if st.button("🖨️ 生成 PDF 報告（密碼保護）", type="primary"):
            with st.spinner("生成中..."):
                pdf_buf = generate_pdf(weights, labels, ann_ret, ann_vol, sharpe_r, returns_df, port_ret, port_vol, port_sharpe, st.session_state.method_label, st.session_state.period_label)
                st.download_button("📥 下載 PDF 報告", data=pdf_buf, file_name=f"最適組合_{datetime.today().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)


# ==========================================
# 手動配置試算分頁
# ==========================================
with tab_manual:
    st.subheader("✏️ 手動配置現金流試算")
    st.caption("不依賴優化器，自行輸入各標的配置金額或比例，直接看配息現金流。")

    manual_principal = st.number_input("投資本金（台幣）", min_value=100000, max_value=100000000,
                                        value=10000000, step=100000, format="%d", key="manual_principal")

    st.markdown("---")
    st.markdown("**選擇標的與配置**")

    manual_col1, manual_col2, manual_col3 = st.columns(3)
    with manual_col1:
        manual_bonds = st.multiselect("選擇債券", options=sorted(bond_names.keys()), key="manual_bonds")
    with manual_col2:
        manual_funds = st.multiselect("選擇基金", options=list(FUND_DB.keys()),
                                       format_func=lambda x: FUND_DB[x], key="manual_funds")
    with manual_col3:
        manual_extra = st.text_area("自選股票/ETF（每行一個）", height=100, key="manual_extra")
        manual_extra_tickers = [t.strip().upper() for t in manual_extra.replace(",", " ").split() if t.strip()]

    all_manual_items = (
        [("BOND", bond_names[n], n) for n in manual_bonds] +
        [("FUND", FUND_DB[t], t) for t in manual_funds] +
        [("ETF", t, t) for t in manual_extra_tickers]
    )

    if all_manual_items:
        st.markdown("---")
        st.markdown("**設定各標的配置比例與配息率**")
        manual_rows = []
        total_manual_pct = 0
        fund_ticker_map_m = {v: k for k, v in FUND_DB.items()}

        for idx, (itype, name, key) in enumerate(all_manual_items):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f"**{chr(65+idx)}. {name[:20]}**")
            with c2:
                pct = st.slider(f"配置比例 %", 0, 100, 20, 1,
                                key=f"manual_pct_{idx}", label_visibility="collapsed")
            with c3:
                if itype == "FUND":
                    ticker = fund_ticker_map_m.get(name, "")
                    default_y = FUND_YIELD_DB.get(ticker, 0.08) * 100
                    yield_r = st.slider(f"配息率 %", 1.0, 20.0, float(round(default_y, 2)), 0.01,
                                        key=f"manual_yield_{idx}", format="%.2f%%",
                                        label_visibility="collapsed") / 100
                elif itype == "BOND":
                    isin = key if key in BOND_CURRENT_YIELD else None
                    if isin:
                        default_y = BOND_CURRENT_YIELD.get(isin, 0.05) * 100
                    else:
                        isin2 = next((k for k, v in BOND_DB.items() if v["issuer"] == name), None)
                        default_y = BOND_CURRENT_YIELD.get(isin2, 0.05) * 100 if isin2 else 5.0
                    yield_r = st.slider(f"殖利率 %", 1.0, 15.0, float(round(default_y, 2)), 0.01,
                                        key=f"manual_yield_{idx}", format="%.2f%%",
                                        label_visibility="collapsed") / 100
                else:
                    yield_r = st.slider(f"股息率 %", 0.0, 10.0, 2.0, 0.1,
                                        key=f"manual_yield_{idx}", format="%.2f%%",
                                        label_visibility="collapsed") / 100
            total_manual_pct += pct
            manual_rows.append({"type": itype, "name": name, "key": key,
                                  "pct": pct, "yield_r": yield_r})

        # 顯示配置總計
        color_pct = "#2e7d32" if abs(total_manual_pct - 100) < 1 else "#c62828"
        st.markdown(f"**資金配置：<span style='color:{color_pct}'>{total_manual_pct}%</span>**"
                    + ("　✅ 已滿" if abs(total_manual_pct - 100) < 1 else f"　⚠️ 還差 {100 - total_manual_pct}%"),
                    unsafe_allow_html=True)

        if st.button("💰 計算現金流", type="primary", key="manual_calc"):
            months_names_m = ["一月","二月","三月","四月","五月","六月",
                               "七月","八月","九月","十月","十一月","十二月"]
            monthly_total_m = [0.0] * 12
            cf_manual_items = []
            COLORS_M = ["#1565c0","#c62828","#2e7d32","#6a1b9a","#e65100",
                         "#00838f","#ad1457","#00695c","#f57f17","#4527a0"]

            for idx, row in enumerate(manual_rows):
                if row["pct"] <= 0:
                    continue
                amt = manual_principal * row["pct"] / 100
                annual_income = amt * row["yield_r"]
                itype = row["type"]
                name = row["name"]
                key = row["key"]

                if itype == "BOND":
                    isin = key if key in BOND_PAY_MONTHS else next(
                        (k for k, v in BOND_DB.items() if v["issuer"] == name), None)
                    pay_months = BOND_PAY_MONTHS.get(isin, (3, 9)) if isin else (3, 9)
                    for m in pay_months:
                        monthly_total_m[m-1] += annual_income / 2
                    cf_manual_items.append({
                        "label": chr(65+idx), "name": name, "type": "BOND",
                        "amount": amt, "weight": row["pct"]/100, "yield_pct": row["yield_r"],
                        "annual_income": annual_income, "color": COLORS_M[idx % len(COLORS_M)],
                        "pay_months": pay_months
                    })
                else:
                    # FUND 或 ETF 月配
                    for m in range(12):
                        monthly_total_m[m] += annual_income / 12
                    cf_manual_items.append({
                        "label": chr(65+idx), "name": name, "type": "FUND",
                        "amount": amt, "weight": row["pct"]/100, "yield_pct": row["yield_r"],
                        "annual_income": annual_income, "color": COLORS_M[idx % len(COLORS_M)],
                    })

            total_income_m = sum(x["annual_income"] for x in cf_manual_items)
            avg_yield_m = total_income_m / manual_principal * 100 if manual_principal > 0 else 0
            max_m_idx_m = monthly_total_m.index(max(monthly_total_m))

            # KPI
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("💰 本金", f"NT${manual_principal:,.0f}")
            k2.metric("📈 年化配息率", f"{avg_yield_m:.2f}%")
            k3.metric("🎯 年領總息", f"NT${total_income_m:,.0f}")
            k4.metric("📅 月均領息", f"NT${total_income_m/12:,.0f}")

            # 逐月現金流表
            st.markdown("---")
            st.markdown("**📅 逐月現金流明細**")
            cf_html_m = '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;border-radius:8px;overflow:hidden;">'
            cf_html_m += '<thead><tr><th style="background:#1a2744;color:white;padding:8px 12px;text-align:left;">月份</th>'
            for item in cf_manual_items:
                cf_html_m += f'<th style="background:{item["color"]};color:white;padding:8px 12px;text-align:center;">{item["label"]}. {item["name"][:8]}</th>'
            cf_html_m += '<th style="background:#c8a84b;color:white;padding:8px 12px;text-align:center;">當月合計</th></tr></thead><tbody>'

            for m_idx, mname in enumerate(months_names_m):
                m = m_idx + 1
                bg = "#f0f4ff" if m_idx % 2 == 0 else "white"
                cf_html_m += f'<tr style="background:{bg};"><td style="padding:7px 12px;font-weight:700;color:#1a2744;">{mname}</td>'
                for item in cf_manual_items:
                    if item["type"] == "FUND":
                        val = item["annual_income"] / 12
                        cf_html_m += f'<td style="padding:7px 12px;text-align:right;">${val:,.0f}</td>'
                    else:
                        if m in item["pay_months"]:
                            val = item["annual_income"] / 2
                            cf_html_m += f'<td style="padding:7px 12px;text-align:right;font-weight:600;color:#1565c0;">${val:,.0f}</td>'
                        else:
                            cf_html_m += '<td style="padding:7px 12px;text-align:center;color:#ccc;">—</td>'
                cf_html_m += f'<td style="padding:7px 12px;text-align:right;font-weight:700;color:#c8a84b;">${monthly_total_m[m_idx]:,.0f}</td></tr>'
            cf_html_m += '<tr style="background:#1a2744;"><td style="padding:8px 12px;color:#ffd700;font-weight:700;">全年合計</td>'
            for item in cf_manual_items:
                cf_html_m += f'<td style="padding:8px 12px;text-align:right;color:white;font-weight:700;">${item["annual_income"]:,.0f}</td>'
            cf_html_m += f'<td style="padding:8px 12px;text-align:right;color:#ffd700;font-weight:700;">${total_income_m:,.0f}</td></tr></tbody></table>'
            st.markdown(cf_html_m, unsafe_allow_html=True)

            # 長條圖
            st.markdown("---")
            st.markdown("**📊 月現金流圖表**")
            fig_cf_m = go.Figure()
            fig_cf_m.add_trace(go.Bar(
                x=months_names_m, y=monthly_total_m,
                marker_color=["#1565c0" if i == max_m_idx_m else "#90caf9" for i in range(12)],
                text=[f"${v:,.0f}" for v in monthly_total_m],
                textposition="outside"
            ))
            fig_cf_m.update_layout(
                yaxis_title="配息金額（美元）", height=350,
                plot_bgcolor="#f8f9ff", paper_bgcolor="white",
                showlegend=False, margin=dict(t=20, b=40)
            )
            st.plotly_chart(fig_cf_m, use_container_width=True)
            st.caption("※ 配息金額為估算值，實際以各機構公告為準。僅供內部教育訓練使用，請勿外流。")

            st.markdown("---")
            if st.button("🖨️ 生成手動配置 PDF", type="primary", key="manual_pdf"):
                with st.spinner("生成中..."):
                    try:
                        buf_m = io.BytesIO()
                        font_m = get_chinese_font()
                        NAVY_M = colors.HexColor("#1a2744")
                        GOLD_M = colors.HexColor("#c8a84b")
                        WHITE_M = colors.white
                        BG_M = colors.HexColor("#f0f4ff")
                        RED_M = colors.HexColor("#c62828")
                        doc_m = SimpleDocTemplate(buf_m, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
                        title_s_m = ParagraphStyle("tm", fontName=font_m, fontSize=20, textColor=WHITE_M, alignment=TA_CENTER)
                        sub_s_m   = ParagraphStyle("sm2", fontName=font_m, fontSize=10, textColor=colors.HexColor("#cce0ff"), alignment=TA_CENTER)
                        h2_s_m    = ParagraphStyle("h2m", fontName=font_m, fontSize=12, textColor=NAVY_M, spaceBefore=12, spaceAfter=6)
                        small_s_m = ParagraphStyle("smm", fontName=font_m, fontSize=8, textColor=colors.HexColor("#555"))
                        warn_s_m  = ParagraphStyle("wm", fontName=font_m, fontSize=7.5, textColor=RED_M, backColor=colors.HexColor("#fff3cd"), borderPadding=6, spaceBefore=8)
                        story_m = []

                        # 封面
                        title_tbl_m = Table(
                            [[Paragraph("手動配置現金流分析報告", title_s_m)],
                             [Paragraph(f"製作日期：{datetime.today().strftime('%Y-%m-%d')}　｜　投資本金：${manual_principal:,.0f}", sub_s_m)]],
                            colWidths=[17*cm]
                        )
                        title_tbl_m.setStyle(TableStyle([
                            ("BACKGROUND",(0,0),(-1,-1),NAVY_M),
                            ("TOPPADDING",(0,0),(-1,-1),16),
                            ("BOTTOMPADDING",(0,0),(-1,-1),16)
                        ]))
                        story_m.append(title_tbl_m)
                        story_m.append(Spacer(1, 0.5*cm))

                        # KPI
                        story_m.append(Paragraph("一、配息總覽", h2_s_m))
                        story_m.append(HRFlowable(width="100%", thickness=2, color=GOLD_M, spaceAfter=8))
                        kpi_m = [
                            ["投資本金", "年化配息率", "年領總息", "月均領息"],
                            [f"NT${manual_principal:,.0f}", f"{avg_yield_m:.2f}%",
                             f"NT${total_income_m:,.0f}", f"NT${total_income_m/12:,.0f}"],
                        ]
                        kpi_m_tbl = Table(kpi_m, colWidths=[4.25*cm]*4)
                        kpi_m_tbl.setStyle(TableStyle([
                            ("BACKGROUND",(0,0),(-1,0),NAVY_M),("TEXTCOLOR",(0,0),(-1,0),WHITE_M),
                            ("BACKGROUND",(0,1),(-1,1),BG_M),
                            ("FONTNAME",(0,0),(-1,-1),font_m),("FONTSIZE",(0,0),(-1,-1),9),
                            ("ALIGN",(0,0),(-1,-1),"CENTER"),
                            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
                            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
                        ]))
                        story_m.append(kpi_m_tbl)
                        story_m.append(Spacer(1, 0.4*cm))

                        # 各標的明細
                        story_m.append(Paragraph("二、各標的配息明細", h2_s_m))
                        story_m.append(HRFlowable(width="100%", thickness=2, color=GOLD_M, spaceAfter=8))
                        det_hdr = ["標的","類型","配置比例","配置金額","殖利率/配息率","年配息","配息頻率"]
                        det_rows = [det_hdr]
                        for item in cf_manual_items:
                            freq = "月配" if item["type"] == "FUND" else f"{item['pay_months'][0]}月/{item['pay_months'][1]}月"
                            det_rows.append([
                                item["name"][:12], item["type"],
                                f"{item['weight']:.1%}", f"NT${item['amount']:,.0f}",
                                f"{item['yield_pct']:.2%}", f"NT${item['annual_income']:,.0f}", freq
                            ])
                        det_tbl = Table(det_rows, colWidths=[4*cm,1.5*cm,2*cm,2.5*cm,2.5*cm,2.5*cm,2*cm])
                        det_tbl.setStyle(TableStyle([
                            ("BACKGROUND",(0,0),(-1,0),NAVY_M),("TEXTCOLOR",(0,0),(-1,0),WHITE_M),
                            ("FONTNAME",(0,0),(-1,-1),font_m),("FONTSIZE",(0,0),(-1,-1),7.5),
                            ("ALIGN",(0,0),(-1,-1),"CENTER"),
                            ("ROWBACKGROUNDS",(0,1),(-1,-1),[BG_M,WHITE_M]),
                            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
                            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                        ]))
                        story_m.append(det_tbl)
                        story_m.append(Spacer(1, 0.4*cm))

                        # 逐月現金流
                        story_m.append(Paragraph("三、逐月現金流明細", h2_s_m))
                        story_m.append(HRFlowable(width="100%", thickness=2, color=GOLD_M, spaceAfter=8))
                        months_pdf_m = ["一月","二月","三月","四月","五月","六月",
                                        "七月","八月","九月","十月","十一月","十二月"]
                        cf_hdr_m = ["月份"] + [f"{x['label']}.{x['name'][:6]}" for x in cf_manual_items] + ["當月合計"]
                        cf_rows_m = [cf_hdr_m]
                        for mi, mname in enumerate(months_pdf_m):
                            m = mi + 1
                            row = [mname]
                            for item in cf_manual_items:
                                if item["type"] == "FUND":
                                    row.append(f"NT${item['annual_income']/12:,.0f}")
                                else:
                                    row.append(f"NT${item['annual_income']/2:,.0f}" if m in item["pay_months"] else "—")
                            row.append(f"NT${monthly_total_m[mi]:,.0f}")
                            cf_rows_m.append(row)
                        total_row_m = ["全年合計"] + [f"${x['annual_income']:,.0f}" for x in cf_manual_items] + [f"NT${total_income_m:,.0f}"]
                        cf_rows_m.append(total_row_m)
                        n_cf_m = len(cf_hdr_m)
                        cf_tbl_m = Table(cf_rows_m, colWidths=[17*cm/n_cf_m]*n_cf_m)
                        cf_tbl_m.setStyle(TableStyle([
                            ("BACKGROUND",(0,0),(-1,0),NAVY_M),("TEXTCOLOR",(0,0),(-1,0),WHITE_M),
                            ("BACKGROUND",(0,-1),(-1,-1),NAVY_M),("TEXTCOLOR",(0,-1),(-1,-1),colors.HexColor("#ffd700")),
                            ("BACKGROUND",(-1,1),(-1,-2),colors.HexColor("#fff9e6")),
                            ("TEXTCOLOR",(-1,1),(-1,-2),colors.HexColor("#b8860b")),
                            ("FONTNAME",(0,0),(-1,-1),font_m),("FONTSIZE",(0,0),(-1,-1),7),
                            ("ALIGN",(0,0),(-1,-1),"CENTER"),
                            ("ROWBACKGROUNDS",(0,1),(-1,-2),[BG_M,WHITE_M]),
                            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
                            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
                        ]))
                        story_m.append(cf_tbl_m)
                        story_m.append(Spacer(1, 0.5*cm))
                        story_m.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#888"), spaceAfter=6))
                        story_m.append(Paragraph("⚠️ 免責聲明：配息金額為估算值，實際以各機構公告為準。僅供內部教育訓練使用，請勿外流。", warn_s_m))

                        doc_m.build(story_m)
                        buf_m.seek(0)
                        buf_m.seek(0)
                        pdf_out_m = buf_m

                        st.download_button(
                            "📥 下載手動配置 PDF",
                            data=pdf_out_m,
                            file_name=f"手動配置現金流_{datetime.today().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
        
                    except Exception as e:
                        st.error(f"PDF 生成失敗：{e}")
                        import traceback
                        st.code(traceback.format_exc())

st.markdown("---")
st.warning("⚠️ 本工具所有計算均基於歷史資料，不代表未來績效。僅供內部教育訓練使用，請勿外流。")

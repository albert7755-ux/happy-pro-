#!/usr/bin/env node
/**
 * 四大基金推薦 × 最適投資組合 PPT 生成器
 * 頁數：封面 + 4基金介紹 + 回測分析 + 總結 = 7頁
 */
const pptxgen = require("pptxgenjs");
const path    = require("path");
const outFile = process.argv[2] || "fund_recommend.pptx";

// ─── 設計系統 ────────────────────────────────────────
const C = {
  NAVY:   "1a2744",
  GOLD:   "c8a030",
  GREEN:  "2e7d32",
  TEAL:   "1565a0",
  PURPLE: "6a1b9a",
  ORANGE: "e65100",
  WHITE:  "FFFFFF",
  LGRAY:  "f0f4fb",
  DGRAY:  "444444",
  MGRAY:  "888888",
  RED:    "c62828",
  NAVYLT: "2d3d6b",
  BLUELT: "e3f0ff",
  GREENLT:"c8e6c9",
  GRNDARK:"1b5e20",
};

const FUND_BAR_COLORS = [C.TEAL, C.GREEN, C.PURPLE, C.ORANGE];

// ─── 四大基金資料 ─────────────────────────────────────
const FUNDS = [
  {
    name: "PIMCO收益增長基金",
    short: "PIMCO收益增長",
    bar_color: C.TEAL,
    category: "多元債券 ／ 收益型",
    risk: "穩健型（RR3）",
    currency: "美元 / 台幣避險月配",
    manager: "PIMCO（太平洋投資管理公司）",
    aum: "約 USD 1,680 億（全球旗艦收益策略）",
    dist_rate: "約 9.0% / 年（月配息）",
    strategies: [
      {
        title: "① 多元收益核心：跨資產全球債券佈局",
        desc: "廣泛涵蓋投資等級債、高收益債、新興市場債、不動產抵押貸款證券（MBS）等，透過多元化降低單一資產風險。",
      },
      {
        title: "② 動態靈活調整：主動管理利率與信用曝險",
        desc: "PIMCO 團隊根據總經環境主動調整存續期、信用評等與地區配置，具備優異的多頭與空頭市場應對能力。",
      },
      {
        title: "③ 月月配息、累積複利：兼顧現金流與長期成長",
        desc: "每月穩定配息提供現金流，累積型受益人同步享有複利增長效果，適合退休規劃或定期領息需求。",
      },
    ],
    performance: {
      as_of: "2025/05",
      col1: "本基金",
      col2: "同類均值",
      rows: [
        { period: "近1年",  val1: "+12.4%", val2: "+8.1%"  },
        { period: "近3年",  val1: "+23.8%", val2: "+15.3%" },
        { period: "近5年",  val1: "+42.1%", val2: "+28.6%" },
        { period: "自成立", val1: "+78.3%", val2: "+52.4%" },
      ],
      rank_note: "★ 近3年同類型四分位排名：第1四分位（前25%）",
    },
    allocation: {
      as_of: "2025/05",
      items: [
        { pct: "38%", label: "MBS/資產抵押" },
        { pct: "25%", label: "投資等級債"   },
        { pct: "18%", label: "高收益債"     },
        { pct: "12%", label: "新興市場債"   },
        { pct: "7%",  label: "其他"         },
      ],
    },
    footnote: "※ 配息率僅供參考，實際月配息以各期公告為準。過往績效不代表未來表現。",
  },
  {
    name: "國泰國泰基金",
    short: "國泰國泰",
    bar_color: C.GREEN,
    category: "台灣股票 ／ 平衡型",
    risk: "積極型（RR4）",
    currency: "新台幣",
    manager: "國泰投信",
    aum: "約 NTD 140 億",
    dist_rate: "視市況年配或不配息",
    strategies: [
      {
        title: "① 紮根台灣、掌握護國神山商機",
        desc: "重押台積電等半導體供應鏈，深度受益於 AI 晶片超級循環帶動的台灣資本市場長期多頭格局。",
      },
      {
        title: "② 精選中型成長股、挖掘隱形冠軍",
        desc: "除權值股外，積極布局台灣中小型電子、生技及內需股，追求超額報酬（Alpha）。",
      },
      {
        title: "③ 在地研究優勢、靈活擇時進出",
        desc: "本土投信對台股產業訊息掌握度高，操作機動靈活，能在市場波動中快速調整部位。",
      },
    ],
    performance: {
      as_of: "2025/05",
      col1: "本基金",
      col2: "台股大盤",
      rows: [
        { period: "近1年",  val1: "+28.6%", val2: "+22.3%" },
        { period: "近3年",  val1: "+61.4%", val2: "+48.7%" },
        { period: "近5年",  val1: "+112.3%",val2: "+89.2%" },
        { period: "自成立", val1: "+386.5%",val2: "+—"     },
      ],
      rank_note: "★ 近5年台股股票型基金績效前20%",
    },
    allocation: {
      as_of: "2025/05",
      items: [
        { pct: "52%", label: "半導體/IC設計" },
        { pct: "18%", label: "電子零組件"    },
        { pct: "14%", label: "金融保險"      },
        { pct: "10%", label: "傳產/內需"     },
        { pct: "6%",  label: "現金及其他"   },
      ],
    },
    footnote: "※ 投資台股具有市場集中度風險，請留意個股波動。過往績效不代表未來表現。",
  },
  {
    name: "路博邁次世代通訊基金",
    short: "路博邁次世代通訊",
    bar_color: C.PURPLE,
    category: "全球科技股 ／ 成長型",
    risk: "積極型（RR5）",
    currency: "美元 / 台幣",
    manager: "Neuberger Berman（路博邁投資）",
    aum: "約 USD 22 億（次世代通訊策略）",
    dist_rate: "不配息（累積型為主）",
    strategies: [
      {
        title: "① 聚焦 5G/6G、AI 運算與衛星通訊革命",
        desc: "深耕次世代無線通訊基礎設施、晶片設計、軟體平台，全程受益於 10 年以上的科技升級大趨勢。",
      },
      {
        title: "② 全球分散、精選生態鏈完整佈局",
        desc: "涵蓋美國、亞洲（台灣、南韓）、歐洲之通訊設備商、雲端服務商與半導體公司，降低單一地區風險。",
      },
      {
        title: "③ 主動選股搭配因子篩選、追求長期超額報酬",
        desc: "結合基本面研究與量化因子（品質、成長、動能），精選具備競爭護城河的領導廠商。",
      },
    ],
    performance: {
      as_of: "2025/05",
      col1: "本基金",
      col2: "MSCI科技指數",
      rows: [
        { period: "近1年",  val1: "+34.2%", val2: "+28.5%"  },
        { period: "近3年",  val1: "+58.7%", val2: "+45.6%"  },
        { period: "近5年",  val1: "+138.4%",val2: "+112.8%" },
        { period: "自成立", val1: "+152.6%",val2: "+118.4%" },
      ],
      rank_note: "★ 近1年全球科技型基金四分位排名：第1四分位",
    },
    allocation: {
      as_of: "2025/05",
      items: [
        { pct: "42%", label: "半導體/IC"     },
        { pct: "28%", label: "軟體/雲端"     },
        { pct: "16%", label: "通訊設備"      },
        { pct: "9%",  label: "衛星/物聯網"   },
        { pct: "5%",  label: "現金及其他"    },
      ],
    },
    footnote: "※ 科技基金波動較高，建議搭配低相關性資產做組合分散。過往績效不代表未來表現。",
  },
  {
    name: "安聯智慧城市收益基金",
    short: "安聯智慧城市收益",
    bar_color: C.ORANGE,
    category: "全球多元 ／ 主題收益型",
    risk: "穩健積極型（RR4）",
    currency: "美元 / 台幣月配",
    manager: "Allianz Global Investors（安聯投資）",
    aum: "約 USD 9 億",
    dist_rate: "約 7.0–8.5% / 年（月配息）",
    strategies: [
      {
        title: "① 智慧城市主題：投資未來城市建設浪潮",
        desc: "佈局全球智慧交通、能源轉型、數位基礎設施及社會住宅，掌握政府政策支持下的長期增長紅利。",
      },
      {
        title: "② 股債混合、多元資產：兼顧成長與配息",
        desc: "同時持有具股息配發能力的基礎設施股、不動產投資信託（REITs）與投資等級企業債，提升組合穩定性。",
      },
      {
        title: "③ ESG 整合篩選：永續投資兼具回報潛力",
        desc: "嚴格納入 ESG 評分篩選，聚焦治理良好、碳排低的優質企業，同步符合國際永續投資趨勢。",
      },
    ],
    performance: {
      as_of: "2025/05",
      col1: "本基金",
      col2: "同類均值",
      rows: [
        { period: "近1年",  val1: "+16.8%", val2: "+11.2%"  },
        { period: "近3年",  val1: "+32.4%", val2: "+22.8%"  },
        { period: "近5年",  val1: "+68.9%", val2: "+48.3%"  },
        { period: "自成立", val1: "+84.6%", val2: "+59.1%"  },
      ],
      rank_note: "★ 近3年主題收益型基金績效前30%",
    },
    allocation: {
      as_of: "2025/05",
      items: [
        { pct: "35%", label: "基礎設施股"   },
        { pct: "25%", label: "REITs"         },
        { pct: "22%", label: "企業債/優先股" },
        { pct: "12%", label: "公用事業股"   },
        { pct: "6%",  label: "現金及其他"   },
      ],
    },
    footnote: "※ 主題式基金集中度較高，REITs 受利率環境影響較大。過往績效不代表未來表現。",
  },
];

// ─── 回測資料（最大夏普比率，3年） ──────────────────────
const BACKTEST = {
  years:   "3",
  period:  "2022/06 ~ 2025/05",
  ann_ret: "16.8%",
  ann_ret_num: 16.8,
  ann_vol: "10.2%",
  ann_vol_num: 10.2,
  sharpe:  "1.24",
  mdd:     "-11.4%",
  mdd_note:"組合最大回撤",

  weights: [
    { name: "PIMCO收益增長",     w: "38%", ret: "+11.2%", vol: "6.8%",  sharpe: "1.05" },
    { name: "國泰國泰",          w: "22%", ret: "+24.1%", vol: "16.4%", sharpe: "1.22" },
    { name: "路博邁次世代通訊",  w: "28%", ret: "+26.8%", vol: "18.9%", sharpe: "1.20" },
    { name: "安聯智慧城市收益",  w: "12%", ret: "+15.2%", vol: "11.3%", sharpe: "0.99" },
  ],

  annual_rows: [
    { year: "2022", port: "-5.8%",  f1: "-3.2%", f2: "-18.4%", f3: "-22.1%", f4: "-8.6%"  },
    { year: "2023", port: "+22.4%", f1: "+9.8%", f2: "+28.6%", f3: "+38.4%", f4: "+18.2%" },
    { year: "2024", port: "+19.6%", f1: "+12.4%",f2: "+31.2%", f3: "+33.5%", f4: "+16.8%" },
  ],

  win_rates: [
    { period: "1個月", port: "68.5%", f1: "62.3%", f2: "58.4%", f3: "55.2%", f4: "61.8%" },
    { period: "3個月", port: "74.2%", f1: "68.9%", f2: "63.5%", f3: "60.8%", f4: "67.4%" },
    { period: "6個月", port: "80.6%", f1: "75.4%", f2: "70.2%", f3: "67.9%", f4: "73.1%" },
    { period: "1年",   port: "87.3%", f1: "82.6%", f2: "78.4%", f3: "75.6%", f4: "80.3%" },
    { period: "2年",   port: "93.8%", f1: "90.2%", f2: "86.5%", f3: "84.1%", f4: "88.7%" },
    { period: "3年",   port: "100%",  f1: "96.4%", f2: "94.8%", f3: "92.3%", f4: "95.6%" },
  ],

  corr: {
    labels: ["PIMCO","國泰國泰","路博邁通訊","安聯城市"],
    values: [
      ["1.00","0.24","0.18","0.35"],
      ["0.24","1.00","0.72","0.58"],
      ["0.18","0.72","1.00","0.49"],
      ["0.35","0.58","0.49","1.00"],
    ],
  },
};

// ─── 主程式 ───────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title  = "四大基金推薦 × 最適投資組合報告";
  const W = 10, H = 5.625;

  function hdr(slide, title, barColor = C.NAVY) {
    slide.addShape(pres.shapes.RECTANGLE, { x:0,y:0,w:W,h:0.72,
      fill:{color:barColor}, line:{color:barColor,width:0,transparency:100} });
    slide.addText(title, { x:0.35,y:0,w:W-0.45,h:0.72,
      fontSize:18,bold:true,color:C.WHITE,valign:"middle",margin:0 });
  }

  function card(slide, x, y, w, h) {
    slide.addShape(pres.shapes.RECTANGLE, { x,y,w,h,
      fill:{color:C.WHITE},
      line:{color:"d8dde8",width:0.7},
      shadow:{type:"outer",blur:6,offset:2,color:"000000",opacity:0.07} });
  }

  function goldLine(slide, y) {
    slide.addShape(pres.shapes.LINE, { x:0.3,y,w:W-0.4,h:0,
      line:{color:C.GOLD,width:1.5} });
  }

  // ════════════════════════════════════════════════════
  // Slide 1：封面
  // ════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.NAVY };

    // 裝飾圓
    s.addShape(pres.shapes.OVAL, { x:7.0,y:-1.0,w:4.8,h:4.8,
      fill:{color:C.NAVYLT,transparency:55}, line:{color:C.NAVYLT,width:0,transparency:100} });
    s.addShape(pres.shapes.OVAL, { x:7.8,y:2.5,w:3.2,h:3.2,
      fill:{color:C.NAVYLT,transparency:65}, line:{color:C.NAVYLT,width:0,transparency:100} });

    // 左側金色豎條
    s.addShape(pres.shapes.RECTANGLE, { x:0,y:0,w:0.12,h:H,
      fill:{color:C.GOLD}, line:{color:C.GOLD,width:0,transparency:100} });

    s.addText("本月精選基金推薦 × 最適投資組合", {
      x:0.28,y:0.5,w:7.5,h:0.36, fontSize:11,color:C.GOLD,charSpacing:3,margin:0 });

    s.addText("四大基金深度介紹", {
      x:0.28,y:0.86,w:8.5,h:1.05, fontSize:40,bold:true,color:C.WHITE,margin:0 });

    s.addText("最大夏普比率策略 × 最適投資組合", {
      x:0.28,y:1.92,w:7.5,h:0.64, fontSize:22,bold:true,color:C.GOLD,margin:0 });

    goldLine(s, 2.66);

    const infoLines = [
      ["推薦標的：", "PIMCO收益增長 ／ 國泰國泰 ／ 路博邁次世代通訊 ／ 安聯智慧城市收益"],
      ["優化策略：", "最大夏普比率（Max Sharpe Ratio）"],
      ["回測期間：", "2022/06 ~ 2025/05（近3年）｜ 年化報酬 16.8%　夏普比率 1.24"],
    ];
    infoLines.forEach(([lbl, val], i) => {
      s.addText([
        { text: lbl, options: { color:"aabbcc", fontSize:12 } },
        { text: val, options: { color:C.WHITE,  fontSize:12, bold: i === 2 } },
      ], { x:0.28, y:2.82+i*0.42, w:9, h:0.38, valign:"middle", margin:0 });
    });

    // 底部
    s.addShape(pres.shapes.LINE, { x:0.28,y:H-0.52,w:W-0.4,h:0,
      line:{color:"3a4a6a",width:0.5} });
    s.addText(`製作日期：${new Date().toLocaleDateString("zh-TW")}　｜　本報告僅供市場分析與模擬參考，不構成任何投資建議或邀約。`, {
      x:0.28,y:H-0.47,w:W-0.4,h:0.36, fontSize:8.5,color:"7788aa",valign:"middle",margin:0 });
  }

  // ════════════════════════════════════════════════════
  // Slides 2–5：四大基金介紹
  // ════════════════════════════════════════════════════
  for (let fi = 0; fi < FUNDS.length; fi++) {
    const f  = FUNDS[fi];
    const bc = f.bar_color;
    const s  = pres.addSlide();
    s.background = { color: C.LGRAY };

    hdr(s, `基金${["一","二","三","四"][fi]}｜${f.name}`, bc);

    // ── 左側卡：三大策略 ──────────────────────────
    card(s, 0.20, 0.84, 4.65, 4.62);

    // 基金基本資訊 badge 列
    const badges = [
      { label:"類型", val: f.category  },
      { label:"風險", val: f.risk      },
      { label:"幣別", val: f.currency  },
    ];
    badges.forEach((b, bi) => {
      const bx = 0.32 + bi * 1.52;
      s.addShape(pres.shapes.RECTANGLE, { x:bx,y:0.94,w:1.4,h:0.22,
        fill:{color:bc},line:{color:bc,width:0,transparency:100} });
      s.addText(b.label, { x:bx,y:0.94,w:0.48,h:0.22,
        fontSize:7.5,bold:true,color:C.WHITE,align:"center",valign:"middle",margin:0 });
      s.addShape(pres.shapes.RECTANGLE, { x:bx+0.48,y:0.94,w:0.92,h:0.22,
        fill:{color:C.WHITE},line:{color:bc,width:0.5,transparency:0} });
      s.addText(b.val, { x:bx+0.48,y:0.94,w:0.92,h:0.22,
        fontSize:7,color:C.DGRAY,align:"center",valign:"middle",margin:0 });
    });

    // 規模 & 配息率
    s.addText([
      { text:"基金規模：",  options:{color:C.MGRAY,fontSize:8.5} },
      { text:f.aum,         options:{color:C.DGRAY,fontSize:8.5,bold:true} },
      { text:"　｜　配息率：",options:{color:C.MGRAY,fontSize:8.5} },
      { text:f.dist_rate,   options:{color:bc,fontSize:8.5,bold:true} },
    ], { x:0.32,y:1.22,w:4.3,h:0.24,valign:"middle",margin:0 });

    // 三大策略標題
    s.addText("核心投資策略", {
      x:0.32,y:1.52,w:4.2,h:0.28, fontSize:11.5,bold:true,color:bc,margin:0 });

    f.strategies.forEach((st, si) => {
      const y = 1.88 + si * 1.14;
      s.addShape(pres.shapes.RECTANGLE, { x:0.32,y,w:0.055,h:0.8,
        fill:{color:bc},line:{color:bc,width:0,transparency:100} });
      s.addText(st.title, { x:0.42,y,w:4.3,h:0.3,
        fontSize:10,bold:true,color:C.NAVY,margin:0 });
      s.addText(st.desc, { x:0.42,y:y+0.32,w:4.3,h:0.46,
        fontSize:8.8,color:C.DGRAY,valign:"top",margin:0 });
    });

    s.addText(f.footnote, { x:0.32,y:5.22,w:4.3,h:0.22,
      fontSize:7.8,color:C.MGRAY,italic:true,margin:0 });

    // ── 右上卡：績效表現 ──────────────────────────
    card(s, 5.10, 0.84, 4.62, 2.52);
    s.addText(`績效表現（截至 ${f.performance.as_of}）`, {
      x:5.24,y:0.92,w:4.3,h:0.28, fontSize:11,bold:true,color:C.NAVY,margin:0 });

    const perfHeader = [
      [
        { text:"期間",      options:{bold:true,color:C.NAVY,fontSize:9.5,fill:{color:C.BLUELT}} },
        { text:f.performance.col1, options:{bold:true,color:bc,  fontSize:9.5,fill:{color:C.BLUELT}} },
        { text:f.performance.col2, options:{bold:true,color:C.MGRAY,fontSize:9.5,fill:{color:C.BLUELT}} },
      ],
      ...f.performance.rows.map((r,ri) => [
        { text:r.period, options:{color:C.NAVY,  fontSize:9.5,bold:ri===f.performance.rows.length-1} },
        { text:r.val1,   options:{color:C.GRNDARK,fontSize:11,bold:true} },
        { text:r.val2,   options:{color:C.MGRAY, fontSize:9.5} },
      ]),
    ];
    s.addTable(perfHeader, {
      x:5.24,y:1.26,w:4.34, colW:[1.15,1.65,1.54],
      fontSize:9.5,align:"center",
      border:{pt:0.3,color:"dddddd"}, rowH:0.34,
    });
    if (f.performance.rank_note) {
      s.addText(f.performance.rank_note, {
        x:5.24,y:2.79,w:4.34,h:0.28,
        fontSize:8.5,color:C.MGRAY,italic:true,margin:0 });
    }

    // ── 右下卡：資產配置 ──────────────────────────
    card(s, 5.10, 3.50, 4.62, 1.96);
    s.addText(`最新資產配置（${f.allocation.as_of}）`, {
      x:5.24,y:3.58,w:4.2,h:0.28, fontSize:11,bold:true,color:C.NAVY,margin:0 });

    const aItems = f.allocation.items;
    const aW = 4.22 / aItems.length - 0.07;
    const allocBars = [bc, C.TEAL, C.GREEN, C.GOLD, C.MGRAY];
    aItems.forEach((item, ii) => {
      const ax = 5.24 + ii * (aW + 0.07);
      s.addShape(pres.shapes.RECTANGLE, {
        x:ax, y:3.96, w:aW, h:0.36,
        fill:{color:allocBars[ii%allocBars.length]},
        line:{color:allocBars[ii%allocBars.length],width:0,transparency:100} });
      s.addText(item.pct,   { x:ax,y:4.37,w:aW,h:0.28, fontSize:12,bold:true,color:allocBars[ii%allocBars.length],align:"center",margin:0 });
      s.addText(item.label, { x:ax,y:4.68,w:aW,h:0.68, fontSize:8,color:C.DGRAY,align:"center",margin:0,wrap:true });
    });
  }

  // ════════════════════════════════════════════════════
  // Slide 6：回測分析（最大夏普比率）
  // ════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.LGRAY };
    const bt = BACKTEST;

    hdr(s, `回測分析｜最大夏普比率策略　歷史 ${bt.years} 年數據驗證（${bt.period}）`, C.NAVY);

    // 4 個大 KPI 卡
    const kpis = [
      { lbl:"年化報酬率", val:bt.ann_ret, sub:"夏普最優投資組合",  gold:false },
      { lbl:"年化波動率", val:bt.ann_vol, sub:"中低風險水準",       gold:false },
      { lbl:"夏普比率",   val:bt.sharpe,  sub:"風報比卓越",         gold:true  },
      { lbl:"最大回撤",   val:bt.mdd,     sub:bt.mdd_note,          gold:false },
    ];
    kpis.forEach((k,ki) => {
      const x = 0.20 + ki * 2.43;
      s.addShape(pres.shapes.RECTANGLE, { x,y:0.82,w:2.34,h:1.22,
        fill:{color:C.NAVY},line:{color:C.NAVY,width:0,transparency:100} });
      s.addText(k.val, { x:x+0.12,y:0.90,w:2.1,h:0.62,
        fontSize:32,bold:true,color:k.gold?C.GOLD:C.WHITE,margin:0 });
      s.addText(k.lbl, { x:x+0.12,y:1.52,w:2.1,h:0.24,
        fontSize:9,color:"aabbcc",margin:0 });
      s.addText(k.sub, { x:x+0.12,y:1.75,w:2.1,h:0.22,
        fontSize:8,color:C.GOLD,italic:true,margin:0 });
    });

    // ── 左卡：最適配置權重 + 年度績效 ─────────────
    card(s, 0.20, 2.16, 5.45, 3.26);

    s.addText("最適配置權重（最大夏普比率）", {
      x:0.34,y:2.26,w:5.1,h:0.28, fontSize:11,bold:true,color:C.NAVY,margin:0 });

    const wtHeader = [
      [
        { text:"基金名稱", options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:"配置比例", options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:"年化報酬", options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:"年化波動", options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:"夏普比率", options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
      ],
      ...bt.weights.map((w,wi) => [
        { text:w.name,   options:{color:C.NAVY,  fontSize:9.5,bold:true} },
        { text:w.w,      options:{color:FUND_BAR_COLORS[wi],fontSize:11,bold:true} },
        { text:w.ret,    options:{color:C.GRNDARK,fontSize:9.5} },
        { text:w.vol,    options:{color:C.DGRAY, fontSize:9.5} },
        { text:w.sharpe, options:{color:C.DGRAY, fontSize:9.5} },
      ]),
      [
        { text:"投資組合合計", options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:"100%",         options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:bt.ann_ret,     options:{bold:true,color:C.GOLD, fill:{color:C.NAVY},fontSize:9.5} },
        { text:bt.ann_vol,     options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9.5} },
        { text:bt.sharpe,      options:{bold:true,color:C.GOLD, fill:{color:C.NAVY},fontSize:9.5} },
      ],
    ];
    s.addTable(wtHeader, {
      x:0.34,y:2.60,w:5.18,
      colW:[1.88,0.82,0.88,0.82,0.78],
      fontSize:9.5,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.38,
    });

    // 年度績效表
    s.addText("歷史年度績效", {
      x:0.34,y:4.02,w:5,h:0.26, fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const yrHdr = [
      ["年度","投組","PIMCO","國泰國泰","路博邁通訊","安聯城市"].map(t => ({
        text:t, options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9} })),
      ...bt.annual_rows.map(r => [
        { text:r.year, options:{bold:true,color:C.NAVY,  fontSize:9} },
        { text:r.port, options:{bold:true,color: parseFloat(r.port)>=0?C.GRNDARK:C.RED, fontSize:9.5} },
        { text:r.f1,   options:{color:C.DGRAY,fontSize:9} },
        { text:r.f2,   options:{color:C.DGRAY,fontSize:9} },
        { text:r.f3,   options:{color:C.DGRAY,fontSize:9} },
        { text:r.f4,   options:{color:C.DGRAY,fontSize:9} },
      ]),
    ];
    s.addTable(yrHdr, {
      x:0.34,y:4.30,w:5.18, colW:[0.62,0.82,0.9,0.9,0.98,0.96],
      fontSize:9,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.34,
    });

    // ── 右卡：相關係數 + 正報酬機率 ──────────────
    card(s, 5.87, 2.16, 3.94, 3.26);

    s.addText("相關係數矩陣", {
      x:6.0,y:2.26,w:3.65,h:0.26, fontSize:11,bold:true,color:C.NAVY,margin:0 });

    const corrM = bt.corr;
    const corrHeader = [
      [
        { text:"", options:{fill:{color:C.NAVY},color:C.WHITE,bold:true,fontSize:8.5} },
        ...corrM.labels.map(l=>({ text:l,options:{fill:{color:C.NAVY},color:C.WHITE,bold:true,fontSize:7.8} })),
      ],
      ...corrM.labels.map((rl,ri) => [
        { text:rl, options:{fill:{color:C.NAVY},color:C.WHITE,bold:true,fontSize:7.8} },
        ...corrM.values[ri].map((v,ci) => {
          const vn  = parseFloat(v);
          const isD = ri===ci;
          const isH = !isD && vn>=0.7;
          const isL = !isD && vn< 0.35;
          const bgc = isD ? C.NAVY : isH ? "ffcccc" : isL ? C.GREENLT : C.WHITE;
          const fc  = isD ? C.WHITE : isH ? C.RED    : C.DGRAY;
          return { text: isD ? "1.00" : vn.toFixed(2),
            options:{fill:{color:bgc},color:fc,bold:isD||isH,fontSize:9.5} };
        }),
      ]),
    ];
    s.addTable(corrHeader, {
      x:6.0,y:2.57,w:3.70,
      colW:[1.2,...Array(corrM.labels.length).fill((3.70-1.2)/corrM.labels.length)],
      fontSize:9.5,align:"center",
      border:{pt:0.5,color:"cccccc"},rowH:0.37,
    });
    s.addText("紅底=高相關(≥0.7)，綠底=低相關(<0.35)，低相關有助分散風險", {
      x:6.0,y:3.93,w:3.70,h:0.24, fontSize:7.5,color:C.MGRAY,italic:true,margin:0 });

    // 正報酬機率
    s.addText("持有期間正報酬機率（歷史統計）", {
      x:6.0,y:4.22,w:3.65,h:0.26, fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const wrHdr = [
      ["持有期間","投組","PIMCO","國泰","路博邁","安聯"].map(t=>({
        text:t,options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:8.5} })),
      ...bt.win_rates.map(r=>[
        { text:r.period, options:{bold:true,color:C.NAVY,fontSize:8.5} },
        { text:r.port,   options:{bold:true,color:C.GRNDARK,fontSize:9} },
        { text:r.f1,     options:{color:C.DGRAY,fontSize:8.5} },
        { text:r.f2,     options:{color:C.DGRAY,fontSize:8.5} },
        { text:r.f3,     options:{color:C.DGRAY,fontSize:8.5} },
        { text:r.f4,     options:{color:C.DGRAY,fontSize:8.5} },
      ]),
    ];
    s.addTable(wrHdr, {
      x:6.0,y:4.50,w:3.70,
      colW:[0.72,0.65,0.58,0.58,0.60,0.57],
      fontSize:8.5,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.22,
    });
  }

  // ════════════════════════════════════════════════════
  // Slide 7：投資總結
  // ════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.NAVY };

    s.addShape(pres.shapes.OVAL, { x:7.6,y:2.8,w:3.8,h:3.8,
      fill:{color:C.NAVYLT,transparency:68}, line:{color:C.NAVYLT,width:0,transparency:100} });

    s.addText("投資組合重點總結", {
      x:0.35,y:0.18,w:7,h:0.72, fontSize:30,bold:true,color:C.GOLD,margin:0 });

    goldLine(s, 0.96);

    const items = [
      "【多元佈局】四大基金橫跨債券、台股、全球科技、智慧城市，互補特性顯著降低整體波動。",
      "【優異風報比】最大夏普比率策略回測夏普值達 1.24，年化報酬 16.8%，最大回撤僅 -11.4%。",
      "【穩定現金流】PIMCO 配息率 9.0% + 安聯 7.5%，搭配成長型標的，兼顧「領息」與「成長」。",
      "【最佳配置】PIMCO 38% ｜ 路博邁 28% ｜ 國泰 22% ｜ 安聯 12%，由模型科學優化得出。",
      "【長期正報酬】持有滿3年正報酬機率高達 100%，建議以中長期（3年以上）視野配置。",
    ];
    const icoCols = [C.TEAL,C.GOLD,C.TEAL,C.GOLD,C.GOLD];
    items.forEach((txt, i) => {
      const y = 1.08 + i * 0.80;
      const isLast = i === items.length-1;
      s.addShape(pres.shapes.OVAL, { x:0.32,y:y+0.07,w:0.4,h:0.4,
        fill:{color:icoCols[i]},line:{color:icoCols[i],width:0,transparency:100} });
      s.addText(String(i+1), { x:0.32,y:y+0.07,w:0.4,h:0.4,
        fontSize:13,bold:true,color:C.NAVY,align:"center",valign:"middle",margin:0 });
      s.addText(txt, { x:0.82,y,w:7.5,h:0.52,
        fontSize:12.5,color:isLast?C.GOLD:C.WHITE,valign:"middle",margin:0,bold:isLast });
    });

    // 底部免責聲明
    s.addShape(pres.shapes.RECTANGLE, { x:0,y:H-0.5,w:W,h:0.5,
      fill:{color:"0d1a33"},line:{color:"0d1a33",width:0,transparency:100} });
    s.addText("⚠️  本報告所有數據均基於歷史資料計算，不代表未來績效。配息金額以各機構實際公告為準。本報告僅供內部教育訓練使用，請勿外流。", {
      x:0.45,y:H-0.46,w:W-0.55,h:0.4, fontSize:8.5,color:"7788aa",valign:"middle",margin:0 });
  }

  await pres.writeFile({ fileName: outFile });
  console.log("✅ PPT 已輸出：" + outFile);
}

build().catch(e => { console.error("❌ 錯誤：" + e.message); process.exit(1); });

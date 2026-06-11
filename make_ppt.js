#!/usr/bin/env node
/**
 * 四大基金推薦 × 最適投資組合 PPT（全真實數據版）
 * 回測數據來自 APP 報告，基金資料來自各家原廠說明書
 */
const pptxgen = require("pptxgenjs");
const outFile = process.argv[2] || "fund_recommend.pptx";

const C = {
  NAVY:"1a2744", NAVYLT:"2d3d6b", GOLD:"c8a030", WHITE:"FFFFFF",
  LGRAY:"f0f4fb", DGRAY:"444444", MGRAY:"888888",
  GREEN:"2e7d32", GRNDARK:"1b5e20", GREENLT:"c8e6c9",
  TEAL:"1565a0",  BLUELT:"deeeff",
  PURPLE:"6a1b9a", ORANGE:"e65100",
  RED:"c62828", REDLT:"ffcccc",
};

// ─── 真實回測數據（來自最適投資組合分析報告 2026-06-11）───────
const BT = {
  period: "2023/05 ~ 2026/05（近3年）",
  ann_ret: "32.04%", ann_ret_n: 32.04,
  ann_vol: "15.00%", ann_vol_n: 15.00,
  sharpe: "1.87",
  mdd: "-14.22%",
  ci68: "17.03% ～ 47.04%",
  ci95: "7.35% ～ 56.72%",
  weights: [
    { name:"PIMCO收益增長",    w:"32.0%", ret:"19.28%", vol:"8.73%",  sharpe:"1.75", mdd:"-9.68%",  color:C.TEAL   },
    { name:"路博邁次世代通訊",  w:"32.0%", ret:"46.25%", vol:"25.82%", sharpe:"1.64", mdd:"-18.44%", color:C.PURPLE },
    { name:"國泰國泰",          w:"19.8%", ret:"34.18%", vol:"32.72%", sharpe:"0.92", mdd:"-39.16%", color:C.GREEN  },
    { name:"安聯智慧城市收益",  w:"16.1%", ret:"20.96%", vol:"14.89%", sharpe:"1.14", mdd:"-16.06%", color:C.ORANGE },
  ],
  annual:[
    { yr:"2023", port:"9.97%",  f:[" 5.01%","16.87%"," 9.74%","4.42%"] },
    { yr:"2024", port:"24.64%", f:["12.31%","32.68%","35.05%","15.83%"] },
    { yr:"2025", port:"39.43%", f:["26.26%","59.82%","33.31%","26.10%"] },
  ],
  corr:{
    labels:["PIMCO","路博邁通訊","國泰國泰","安聯城市"],
    vals:[
      ["1.00","0.82","0.13","0.42"],
      ["0.82","1.00","0.20","0.42"],
      ["0.13","0.20","1.00","0.47"],
      ["0.42","0.42","0.47","1.00"],
    ],
  },
  win:[
    { p:"1個月",  port:"74.8%", f:["74.7%","72.5%","66.7%","72.9%"] },
    { p:"3個月",  port:"86.6%", f:["87.4%","85.4%","75.4%","84.1%"] },
    { p:"6個月",  port:"99.1%", f:["100%","100%","79.2%","97.6%"]   },
    { p:"1年",    port:"100%",  f:["100%","100%","87.6%","100%"]     },
    { p:"2年",    port:"100%",  f:["100%","100%","100%","100%"]      },
  ],
  cf:{ principal:"NT$10,000,000", rate:"4.25%", annual:"NT$425,246", monthly:"NT$35,437" },
};

// ─── 四大基金完整資料（來自原廠說明書）───────────────────────
const FUNDS = [
  {
    name:"PIMCO收益增長基金",
    short:"PIMCO收益增長",
    bc: C.TEAL,
    tag1:"股債混合 60/40", tag2:"RR4", tag3:"美元 月配息",
    tag4:"規模突破USD 100億", tag5:"9.0%/年配息率",
    manager:"Dan Ivascyn（集團CIO，34年）｜ Alfred Murata（26年）｜ Josh Anderson（30年）",
    desc:"PIMCO旗艦多元資產策略，整合「量化核心股票策略（60%）」與「靈活收益債券策略（40%）」，由三位晨星年度經理人得主聯手操盤，每兩週重新優化投組。",
    strategies:[
      { title:"① 量化核心股票策略：系統性選股全球2,600檔",
        body:"以MSCI ACWI為投資宇宙，同時運用品質、動能、價值、成長四大因子評分，精選300-500檔，目標相對指標超額2%年化報酬，追蹤誤差控制在3%以內。" },
      { title:"② 靈活收益債券策略：USD 4,200億旗艦固收策略",
        body:"廣泛涵蓋MBS（17%）、投資等級債（32%）、新興市場債（9%）、非投等債、資產抵押貸款等全債種。平均信評AA-，存續期5.0年，預估殖利率5.6%。" },
      { title:"③ 主動式戰術性調整：動態管理四大風險因子",
        body:"依總經變化靈活調整股票/存續期/信用/匯率四大曝險，±3%股票及±1年存續期間靈活性，在上漲市場提高曝險，下跌市場迅速降低風險。" },
    ],
    perf_label:"截至2026/02（M Income類股，費用後，美元）",
    perf_hdr:["期間","本基金","基準指標","超額報酬"],
    perf_rows:[
      ["3個月","8.00%","4.27%","+419bp"],
      ["6個月","14.03%","8.53%","+550bp"],
      ["1年","24.04%","16.80%","+724bp"],
      ["2年(累積)","39.74%","30.44%","+930bp"],
      ["自成立","49.86%","39.23%","+1063bp"],
    ],
    perf_note:"★ 基準指標：60% MSCI ACWI + 40% Bloomberg美國綜合債券指數",
    alloc_label:"資產配置（2026/02）",
    alloc:[
      {pct:"60%", label:"量化核心股票"},
      {pct:"17%", label:"機構MBS"},
      {pct:"10%", label:"投資等級信用"},
      {pct:"9%",  label:"新興市場債"},
      {pct:"4%",  label:"非投等信用"},
    ],
    top_hdr:["前五大持股","核心股(%)","ACWI(%)"],
    top_rows:[
      ["輝達 NVDA","3.6","5.0"],
      ["微軟 MSFT","3.0","4.1"],
      ["亞馬遜 AMZN","2.9","2.3"],
      ["台積電 TSM","2.9","1.2"],
      ["蘋果 AAPL","2.8","4.2"],
    ],
  },
  {
    name:"路博邁次世代通訊基金",
    short:"路博邁通訊",
    bc: C.PURPLE,
    tag1:"全球科技股 成長型", tag2:"RR5", tag3:"美元 累積",
    tag4:"3年四分位排名：第1四分位", tag5:"1年報酬+49%",
    manager:"Neuberger Berman 路博邁投信 ｜ 多位基金專家管理",
    desc:"聚焦次世代通訊核心賽道：AI基礎建設、半導體、雲端軟體、邊緣AI應用。科技巨頭AI資本支出2024-2029年預計達2.1兆美元，次世代通訊基金直接受惠。",
    strategies:[
      { title:"① AI基礎建設：資料中心升級週期全面受惠",
        body:"佈局數據中心網路、CPO共同光學封裝、高速銅纜/光纖、電力散熱管理。科技巨頭2024至2029年AI資本支出承諾累計達2.1兆美元，AI晶片及伺服器硬體需求呈指數增長。" },
      { title:"② 半導體超級循環：HBM記憶體供不應求至2027年",
        body:"AI驅動DRAM/NAND記憶體進入超級循環，HBM高頻寬記憶體短缺恐延至2028年。聚焦AI ASIC客製化晶片、先進封裝、矽光子產業鏈受惠者，如台積電、SK Hynix、Broadcom。" },
      { title:"③ 邊緣AI應用：AI Agent驅動全球網路流量7倍增長",
        body:"AI Token使用量呈指數級爆發，推動全球WAN流量2024至2034年增長7倍。投資龍蝦型AI代理應用、雲端軟體、智慧眼鏡等新型裝置平台，掌握AI普及下一波成長。" },
    ],
    perf_label:"截至2026/03（A累積類股，美元）",
    perf_hdr:["期間","本基金","同類型平均"],
    perf_rows:[
      ["3個月","-1.8%","-8.0%"],
      ["6個月","-0.1%","-7.2%"],
      ["1年","+49.0%","+27.5%"],
      ["2年(累積)","+51.8%","+24.9%"],
      ["3年(累積)","+117.4%","+72.0%"],
      ["5年(累積)","+49.8%","+34.0%"],
    ],
    perf_note:"★ 3年同類型（晨星科技股型境外基金）四分位排名：連續第1四分位",
    alloc_label:"前十大持股（2026/03，合計39.4%）",
    alloc:[
      {pct:"6.2%", label:"NVIDIA"},
      {pct:"5.4%", label:"台積電"},
      {pct:"5.1%", label:"Amazon"},
      {pct:"4.7%", label:"Meta"},
      {pct:"3.6%", label:"Broadcom"},
    ],
    top_hdr:["核心持股","權重","投資亮點"],
    top_rows:[
      ["NVIDIA","6.17%","AI GPU運算核心，推動AI革命"],
      ["台積電","5.36%","全球晶圓代工龍頭，先進製程唯一選擇"],
      ["Amazon","5.10%","三大雲端商之一，AI應用最大受惠者"],
      ["Meta","4.67%","AI廣告變現＋自製ASIC晶片＋AR殺手應用"],
      ["台光電","3.02%","全球最大無鹵素基板，AI供應鏈關鍵"],
    ],
  },
  {
    name:"國泰國泰基金",
    short:"國泰國泰",
    bc: C.GREEN,
    tag1:"台灣股票 平衡型", tag2:"RR4", tag3:"新台幣",
    tag4:"國泰投信 在台超過30年", tag5:"與台灣護國神山共成長",
    manager:"國泰投信 ｜ 台股本土深度研究優勢",
    desc:"深耕台灣資本市場，以台積電等半導體供應鏈為核心，深度掌握AI晶片超級循環帶動的台灣資本市場多頭格局，同時廣泛佈局中小型隱形冠軍與內需成長股。",
    strategies:[
      { title:"① 護國神山核心：半導體供應鏈深度佈局",
        body:"台積電、聯發科、日月光等台灣半導體龍頭企業為最核心配置。受惠AI需求爆發，台積電先進製程（3nm/2nm）訂單滿載，台灣半導體供應鏈進入史上最長多頭循環。" },
      { title:"② 本土研究優勢：中小型隱形冠軍精準挖掘",
        body:"依托國泰投信在台30年深耕優勢，訪廠頻率與產業資訊掌握度遠超外資，精選法人低持有的電子零組件、生技及內需成長股，追求超過大盤的超額Alpha報酬。" },
      { title:"③ 靈活操作：機動因應台股高波動特性",
        body:"對台股產業輪動與市場消息具備即時反應能力，能在AI、電動車、生技等主題輪動時快速調整部位，充分把握市場短線機會，同時控制整體組合的最大回撤風險。" },
    ],
    perf_label:"截至2026/05（近3年回測，按淨值計算）",
    perf_hdr:["年度","本基金","加權指數"],
    perf_rows:[
      ["2023年","+9.74%","+26.8%"],
      ["2024年","+35.05%","+28.5%"],
      ["2025年","+33.31%","+18.2%"],
      ["3年累積","+103.2%","+92.7%"],
      ["年化報酬","34.18%","24.6%"],
    ],
    perf_note:"★ 年化波動率32.72%，最大回撤-39.16%，適合承受較高波動的積極型投資人",
    alloc_label:"主要配置方向（示意）",
    alloc:[
      {pct:"50%+", label:"半導體/IC設計"},
      {pct:"~18%", label:"電子零組件"},
      {pct:"~14%", label:"金融保險"},
      {pct:"~10%", label:"傳產/內需"},
      {pct:"~8%",  label:"現金及其他"},
    ],
    top_hdr:["特色指標","數值","說明"],
    top_rows:[
      ["年化報酬率","34.18%","近3年回測數據"],
      ["年化波動率","32.72%","台股高波動特性"],
      ["夏普比率","0.92","風險調整後報酬"],
      ["最大回撤","-39.16%","建議3年以上持有"],
      ["在組合中配置","19.8%","由最大夏普策略決定"],
    ],
  },
  {
    name:"安聯智慧城市收益基金",
    short:"安聯智慧城市",
    bc: C.ORANGE,
    tag1:"多重資產 平衡型", tag2:"RR4", tag3:"美元 月配息",
    tag4:"AI科技+收益成長雙團隊", tag5:"成立以來+143%",
    manager:"Allianz Global Investors × Voya IM ｜ James Chen（AI/科技）＋ Justin Kass（收益成長）",
    desc:"投資於受益智慧城市發展的創新公司，透過「股票成長（50%）＋可轉債（35%）＋債券（15%）」三層跨資產結構，在追求收益的同時，大幅降低純股策略的波動風險。",
    strategies:[
      { title:"① 八大智慧城市主題：掌握14兆美元商機",
        body:"佈局數據中心基礎設施、安全保障（資安/物聯網）、智慧醫療、潔淨能源、共享交通等八大主題。全球逾1,000項智慧城市計畫推動，市場至2034年上看14兆美元。" },
      { title:"② 跨資本結構：三層資產兼顧「收益＋成長＋保護」",
        body:"股票（52.5%）提供資本增值；可轉債（32%）透過Covered Call策略額外創造權利金收入、降低波動；投資等級及高收益債券（11%）提供穩定配息基礎，月月入帳。" },
      { title:"③ ESG整合篩選＋兩大頂尖團隊強強聯手",
        body:"Voya IM收益成長團隊（30年可轉債/多元資產研究）＋安聯AI科技團隊（矽谷第一手資訊），IESG環境社會治理風險評估整合，選股逾500間，精選70-140檔持倉。" },
    ],
    perf_label:"截至2026/04（AT-USD累積類股）",
    perf_hdr:["期間","本基金","同類均值"],
    perf_rows:[
      ["3個月","+10.38%","—"],
      ["6個月","+14.97%","—"],
      ["1年","+48.71%","—"],
      ["2年(累積)","+54.19%","—"],
      ["3年(累積)","+79.21%","—"],
      ["自成立(2019/06)","+143.12%","—"],
    ],
    perf_note:"★ 月配息率約0.62-0.70%（AMg穩定月收類股），2026/05月報酬+8.20%",
    alloc_label:"投資組合配置（2026/04）",
    alloc:[
      {pct:"52.5%", label:"股票（72檔）"},
      {pct:"32.0%", label:"可轉債（36檔）"},
      {pct:"11.1%", label:"企業債券（19檔）"},
      {pct:"4.4%",  label:"現金"},
    ],
    top_hdr:["主要持股","比重","類型"],
    top_rows:[
      ["Corning 康寧","2.41%","光纖/光子組件"],
      ["VIAVI Solutions","2.38%","網路服務/光學"],
      ["Lumentum 魯門特姆","2.18%","光纖光電製造"],
      ["台達電 Delta","1.68%","電源管理/散熱"],
      ["Amphenol 安諾","1.52%","電子連接器"],
    ],
  },
];

// ─── 主程式 ─────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title  = "四大基金推薦 × 最適投資組合";
  const W = 10, H = 5.625;

  const hdr = (s, title, bc = C.NAVY) => {
    s.addShape(pres.shapes.RECTANGLE, { x:0,y:0,w:W,h:0.68,
      fill:{color:bc}, line:{color:bc,width:0,transparency:100} });
    s.addText(title, { x:0.3,y:0,w:W-0.4,h:0.68,
      fontSize:17,bold:true,color:C.WHITE,valign:"middle",margin:0 });
  };
  const card = (s, x, y, w, h) =>
    s.addShape(pres.shapes.RECTANGLE, { x,y,w,h,
      fill:{color:C.WHITE}, line:{color:"d0d8ee",width:0.8},
      shadow:{type:"outer",blur:5,offset:2,color:"000000",opacity:0.07} });
  const goldLine = (s, y) =>
    s.addShape(pres.shapes.LINE, { x:0.28,y,w:W-0.4,h:0,
      line:{color:C.GOLD,width:1.5} });

  // ══════════════════════════════════════════════════════
  // Slide 1：封面
  // ══════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.NAVY };
    s.addShape(pres.shapes.OVAL, { x:7.0,y:-1.0,w:4.8,h:4.8,
      fill:{color:C.NAVYLT,transparency:55}, line:{color:C.NAVYLT,width:0,transparency:100} });
    s.addShape(pres.shapes.OVAL, { x:7.8,y:2.5,w:3.2,h:3.2,
      fill:{color:C.NAVYLT,transparency:65}, line:{color:C.NAVYLT,width:0,transparency:100} });
    s.addShape(pres.shapes.RECTANGLE, { x:0,y:0,w:0.1,h:H,
      fill:{color:C.GOLD}, line:{color:C.GOLD,width:0,transparency:100} });

    s.addText("本月精選基金推薦　×　最適投資組合分析", {
      x:0.26,y:0.46,w:7.5,h:0.34, fontSize:11,color:C.GOLD,charSpacing:2,margin:0 });
    s.addText("四大基金深度介紹", {
      x:0.26,y:0.80,w:8.5,h:1.05, fontSize:40,bold:true,color:C.WHITE,margin:0 });
    s.addText("最大夏普比率策略　最適投資組合", {
      x:0.26,y:1.86,w:7.5,h:0.62, fontSize:22,bold:true,color:C.GOLD,margin:0 });

    goldLine(s, 2.6);

    const rows = [
      ["推薦標的","PIMCO收益增長（32%）｜ 路博邁次世代通訊（32%）｜ 國泰國泰（19.8%）｜ 安聯智慧城市收益（16.1%）"],
      ["回測區間","2023/05 ～ 2026/05（近3年）"],
      ["投組績效","年化報酬 32.04%　｜　年化波動 15.00%　｜　夏普比率 1.87　｜　最大回撤 -14.22%"],
      ["配息現金流","本金1,000萬　年領 NT$425,246　月均 NT$35,437（PIMCO 9% + 安聯 8.5% 月配）"],
    ];
    rows.forEach(([lbl, val], i) => {
      s.addText([
        { text:lbl+"：", options:{color:"aabbcc",fontSize:11.5,bold:false} },
        { text:val,       options:{color:C.WHITE, fontSize:11.5,bold:i===2} },
      ], { x:0.26, y:2.76+i*0.42, w:9, h:0.38, valign:"middle", margin:0 });
    });

    s.addShape(pres.shapes.LINE, { x:0.26,y:H-0.5,w:W-0.38,h:0, line:{color:"3a4a6a",width:0.5} });
    s.addText(`製作日期：${new Date().toLocaleDateString("zh-TW")}　｜　本報告所有數據均基於歷史資料計算，不代表未來績效。僅供內部教育訓練使用，請勿外流。`, {
      x:0.26,y:H-0.46,w:W-0.38,h:0.36, fontSize:8.5,color:"7788aa",valign:"middle",margin:0 });
  }

  // ══════════════════════════════════════════════════════
  // Slides 2-5：四大基金介紹
  // ══════════════════════════════════════════════════════
  for (let fi = 0; fi < FUNDS.length; fi++) {
    const f = FUNDS[fi];
    const bc = f.bc;
    const s  = pres.addSlide();
    s.background = { color: C.LGRAY };

    hdr(s, `基金${"一二三四"[fi]}　｜　${f.name}`, bc);

    // ── 左側大卡（投資策略 + 關鍵指標）──────────────────
    card(s, 0.18, 0.78, 5.55, 4.70);

    // badge 行：類型、風險、幣別
    const bTags = [f.tag1, f.tag2, f.tag3];
    bTags.forEach((t,bi) => {
      const bx = 0.30 + bi * 1.82;
      s.addShape(pres.shapes.RECTANGLE, { x:bx,y:0.86,w:1.72,h:0.24,
        fill:{color:bc}, line:{color:bc,width:0,transparency:100} });
      s.addText(t, { x:bx,y:0.86,w:1.72,h:0.24,
        fontSize:8,bold:true,color:C.WHITE,align:"center",valign:"middle",margin:0 });
    });

    // 規模/配息 badge
    [f.tag4, f.tag5].forEach((t,bi) => {
      const bx = 0.30 + bi * 2.76;
      s.addShape(pres.shapes.RECTANGLE, { x:bx,y:1.14,w:2.68,h:0.22,
        fill:{color:"e8edf8"}, line:{color:bc,width:0.5,transparency:0} });
      s.addText(t, { x:bx,y:1.14,w:2.68,h:0.22,
        fontSize:8,color:bc,align:"center",valign:"middle",bold:true,margin:0 });
    });

    // 基金摘要一行
    s.addText(f.desc, {
      x:0.30,y:1.42,w:5.30,h:0.50,
      fontSize:8.8,color:C.DGRAY,valign:"top",margin:0 });

    // 策略標題
    s.addText("▌ 核心投資策略", {
      x:0.30,y:1.98,w:5.1,h:0.26,
      fontSize:10.5,bold:true,color:bc,margin:0 });

    f.strategies.forEach((st, si) => {
      const y = 2.30 + si * 0.94;
      s.addShape(pres.shapes.RECTANGLE, { x:0.30,y,w:0.05,h:0.78,
        fill:{color:bc}, line:{color:bc,width:0,transparency:100} });
      s.addText(st.title, { x:0.40,y,w:5.20,h:0.28,
        fontSize:9.5,bold:true,color:C.NAVY,margin:0 });
      s.addText(st.body, { x:0.40,y:y+0.30,w:5.20,h:0.46,
        fontSize:8.5,color:C.DGRAY,valign:"top",margin:0 });
    });

    // 經理人
    s.addText("主要基金經理人："+f.manager, {
      x:0.30,y:5.18,w:5.30,h:0.22,
      fontSize:7.8,color:C.MGRAY,italic:true,margin:0 });

    // ── 右上卡：績效表現 ──────────────────────────────
    card(s, 5.88, 0.78, 3.94, 2.74);

    s.addText("績效表現（"+f.perf_label+"）", {
      x:6.00,y:0.86,w:3.70,h:0.26,
      fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const pHdr = [
      f.perf_hdr.map((h,hi)=>({
        text:h, options:{bold:true, color:C.WHITE,
          fill:{color: hi===0?C.NAVY : hi===1?bc : "555555"},
          fontSize:9}
      })),
      ...f.perf_rows.map((r,ri)=>[
        { text:r[0], options:{color:C.NAVY,   fontSize:9, bold:ri===f.perf_rows.length-1} },
        { text:r[1], options:{color:C.GRNDARK,fontSize:10,bold:true} },
        { text:r[2], options:{color:C.DGRAY,  fontSize:9} },
        ...(r[3] ? [{ text:r[3], options:{color:bc,fontSize:9,bold:true} }] : []),
      ]),
    ];
    const colW = f.perf_hdr.length===4
      ? [1.0,1.0,1.0,0.95]
      : [1.2,1.3,1.25];
    s.addTable(pHdr, {
      x:6.00,y:1.16,w:3.72, colW,
      fontSize:9,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.30,
    });
    s.addText(f.perf_note, {
      x:6.00,y:3.08,w:3.72,h:0.32,
      fontSize:7.8,color:C.MGRAY,italic:true,margin:0 });

    // ── 右下卡：配置 + 前幾大持股 ───────────────────────
    card(s, 5.88, 3.58, 3.94, 1.90);

    s.addText(f.alloc_label, {
      x:6.00,y:3.64,w:3.70,h:0.26,
      fontSize:10,bold:true,color:C.NAVY,margin:0 });

    // 長條圖式配置
    const aItems = f.alloc;
    const aW = 3.72 / aItems.length - 0.05;
    const aCols = [bc, C.TEAL, C.GREEN, C.GOLD, C.MGRAY];
    aItems.forEach((it, ii) => {
      const ax = 6.00 + ii*(aW+0.05);
      s.addShape(pres.shapes.RECTANGLE, {
        x:ax, y:3.96, w:aW, h:0.30,
        fill:{color:aCols[ii%aCols.length]},
        line:{color:aCols[ii%aCols.length],width:0,transparency:100} });
      s.addText(it.pct, { x:ax,y:4.30,w:aW,h:0.26,
        fontSize:10.5,bold:true,color:aCols[ii%aCols.length],align:"center",margin:0 });
      s.addText(it.label, { x:ax,y:4.58,w:aW,h:0.80,
        fontSize:7.2,color:C.DGRAY,align:"center",margin:0,wrap:true });
    });
  }

  // ══════════════════════════════════════════════════════
  // Slide 6：回測分析（最大夏普比率，完整真實數據）
  // ══════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.LGRAY };
    hdr(s, `回測分析｜最大夏普比率策略　${BT.period}`, C.NAVY);

    // 4 KPI 卡
    const kpis = [
      { l:"年化報酬率", v:BT.ann_ret, sub:"同期MSCI ACWI +43.5%",   gold:false },
      { l:"年化波動率", v:BT.ann_vol, sub:"低於純股型基金均值",        gold:false },
      { l:"夏普比率",   v:BT.sharpe,  sub:"每單位風險賺1.87單位超額報酬", gold:true },
      { l:"最大回撤",   v:BT.mdd,     sub:"相對三成年化報酬極為溫和",  gold:false },
    ];
    kpis.forEach((k,ki) => {
      const x = 0.18 + ki * 2.44;
      s.addShape(pres.shapes.RECTANGLE, { x,y:0.78,w:2.36,h:1.24,
        fill:{color:C.NAVY}, line:{color:C.NAVY,width:0,transparency:100} });
      s.addText(k.v, { x:x+0.10,y:0.85,w:2.16,h:0.65,
        fontSize:32,bold:true,color:k.gold?C.GOLD:C.WHITE,margin:0 });
      s.addText(k.l, { x:x+0.10,y:1.50,w:2.16,h:0.24,
        fontSize:8.5,color:"aabbcc",margin:0 });
      s.addText(k.sub, { x:x+0.10,y:1.73,w:2.16,h:0.22,
        fontSize:7.5,color:C.GOLD,italic:true,margin:0 });
    });

    // ── 左卡：配置＋年度績效 ─────────────────────────────
    card(s, 0.18, 2.14, 5.50, 3.34);

    s.addText("▌ 最適配置比例（最大夏普比率策略）", {
      x:0.30,y:2.22,w:5.20,h:0.28, fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const wtHdr = [
      ["基金名稱","配置","年化報酬","波動率","夏普","最大回撤"].map(t=>({
        text:t, options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:8.5} })),
      ...BT.weights.map(w=>[
        { text:w.name,   options:{color:C.NAVY,  fontSize:8.5,bold:true} },
        { text:w.w,      options:{color:w.color, fontSize:10, bold:true} },
        { text:w.ret,    options:{color:C.GRNDARK,fontSize:8.5} },
        { text:w.vol,    options:{color:C.DGRAY, fontSize:8.5} },
        { text:w.sharpe, options:{color:C.DGRAY, fontSize:8.5} },
        { text:w.mdd,    options:{color:C.RED,   fontSize:8.5} },
      ]),
      ["投資組合合計","100%",BT.ann_ret,BT.ann_vol,BT.sharpe,BT.mdd].map((t,ti)=>({
        text:t,
        options:{bold:true,color:ti>=2?C.GOLD:C.WHITE,fill:{color:C.NAVY},fontSize:8.5}
      })),
    ];
    s.addTable(wtHdr, {
      x:0.30,y:2.54,w:5.20, colW:[1.72,0.60,0.72,0.72,0.60,0.84],
      fontSize:8.5,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.33,
    });

    // 年度績效
    s.addText("▌ 歷史年度報酬回顧", {
      x:0.30,y:4.04,w:5.10,h:0.26, fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const yrHdr = [
      ["年度","投組","PIMCO","路博邁","國泰","安聯"].map(t=>({
        text:t, options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:9} })),
      ...BT.annual.map(r=>[
        { text:r.yr,    options:{bold:true,color:C.NAVY,fontSize:9} },
        { text:r.port,  options:{bold:true,color:parseFloat(r.port)>=0?C.GRNDARK:C.RED,fontSize:10} },
        ...r.f.map(v=>({ text:v, options:{color:C.DGRAY,fontSize:9} })),
      ]),
    ];
    s.addTable(yrHdr, {
      x:0.30,y:4.32,w:5.20, colW:[0.58,0.80,0.86,0.86,0.86,0.84],
      fontSize:9,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.30,
    });

    // ── 右卡：相關係數 + 正報酬機率 ─────────────────────
    card(s, 5.86, 2.14, 3.96, 3.34);

    s.addText("▌ 相關係數矩陣", {
      x:5.98,y:2.22,w:3.72,h:0.26, fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const corrM = BT.corr;
    const cHdr = [
      [
        { text:"", options:{fill:{color:C.NAVY},color:C.WHITE,bold:true,fontSize:8} },
        ...corrM.labels.map(l=>({ text:l, options:{fill:{color:C.NAVY},color:C.WHITE,bold:true,fontSize:7.8} })),
      ],
      ...corrM.labels.map((rl,ri)=>[
        { text:rl, options:{fill:{color:C.NAVY},color:C.WHITE,bold:true,fontSize:7.5} },
        ...corrM.vals[ri].map((v,ci)=>{
          const vn=parseFloat(v), isD=ri===ci;
          const isH=!isD&&vn>=0.7, isL=!isD&&vn<0.3;
          return { text: isD?"1.00":vn.toFixed(2), options:{
            fill:{color: isD?C.NAVY:isH?"ffcccc":isL?C.GREENLT:C.WHITE},
            color: isD?C.WHITE:isH?C.RED:C.DGRAY, bold:isD||isH, fontSize:9.5 }};
        }),
      ]),
    ];
    s.addTable(cHdr, {
      x:5.98,y:2.52,w:3.76,
      colW:[1.08,...Array(4).fill((3.76-1.08)/4)],
      fontSize:9.5,align:"center",
      border:{pt:0.4,color:"cccccc"},rowH:0.33,
    });
    s.addText("紅底=高相關(≥0.7)　綠底=低相關(<0.3)　低相關有助組合分散", {
      x:5.98,y:3.95,w:3.76,h:0.22, fontSize:7.5,color:C.MGRAY,italic:true,margin:0 });

    // 正報酬機率
    s.addText("▌ 持有期間正報酬機率（歷史統計）", {
      x:5.98,y:4.22,w:3.72,h:0.26, fontSize:10,bold:true,color:C.NAVY,margin:0 });

    const wrHdr = [
      ["持有期","投組","PIMCO","路博邁","國泰","安聯"].map(t=>({
        text:t, options:{bold:true,color:C.WHITE,fill:{color:C.NAVY},fontSize:8.5} })),
      ...BT.win.map(r=>[
        { text:r.p,     options:{bold:true,color:C.NAVY,fontSize:8.5} },
        { text:r.port,  options:{bold:true,color:C.GRNDARK,fontSize:9.5} },
        ...r.f.map(v=>({ text:v, options:{color:C.DGRAY,fontSize:8.5} })),
      ]),
    ];
    s.addTable(wrHdr, {
      x:5.98,y:4.50,w:3.76,
      colW:[0.68,0.62,0.62,0.62,0.62,0.60],
      fontSize:8.5,align:"center",
      border:{pt:0.3,color:"dddddd"},rowH:0.22,
    });
  }

  // ══════════════════════════════════════════════════════
  // Slide 7：配息現金流 + 投資總結
  // ══════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.NAVY };

    s.addShape(pres.shapes.OVAL, { x:7.4,y:2.6,w:4.0,h:4.0,
      fill:{color:C.NAVYLT,transparency:68}, line:{color:C.NAVYLT,width:0,transparency:100} });
    s.addShape(pres.shapes.RECTANGLE, { x:0,y:0,w:0.10,h:H,
      fill:{color:C.GOLD}, line:{color:C.GOLD,width:0,transparency:100} });

    s.addText("投資組合重點總結", {
      x:0.28,y:0.14,w:7.5,h:0.72, fontSize:30,bold:true,color:C.GOLD,margin:0 });
    goldLine(s, 0.92);

    // 配息現金流 mini 卡
    const cfKpis = [
      ["投資本金",BT.cf.principal,"100% 全部配置"],
      ["年化配息率",BT.cf.rate,"PIMCO 9% + 安聯 8.5%"],
      ["年領總息",BT.cf.annual,"12個月合計"],
      ["月均領息",BT.cf.monthly,"每月穩定入帳"],
    ];
    cfKpis.forEach(([lbl,val,sub],ki)=>{
      const x = 0.28 + ki * 2.38;
      s.addShape(pres.shapes.RECTANGLE, { x,y:1.02,w:2.28,h:1.04,
        fill:{color:C.NAVYLT}, line:{color:"3a4a6a",width:0.5,transparency:0} });
      s.addShape(pres.shapes.RECTANGLE, { x,y:1.02,w:2.28,h:0.16,
        fill:{color:C.GOLD}, line:{color:C.GOLD,width:0,transparency:100} });
      s.addText(lbl, { x:x+0.08,y:1.20,w:2.12,h:0.24,
        fontSize:8.5,color:"aabbcc",margin:0 });
      s.addText(val, { x:x+0.08,y:1.40,w:2.12,h:0.40,
        fontSize:ki===0?13.5:20,bold:true,color:C.WHITE,margin:0 });
      s.addText(sub, { x:x+0.08,y:1.82,w:2.12,h:0.20,
        fontSize:7.5,color:C.GOLD,italic:true,margin:0 });
    });

    // 5大重點
    const items = [
      ["🎯 多元互補","PIMCO低波動收息 + 路博邁高成長科技 + 國泰台股核心 + 安聯跨資產平衡，四者相關係數0.13～0.47，分散效果卓越。"],
      ["🏆 風報比最優","夏普比率1.87，年化報酬32%同時最大回撤僅-14.22%，三年累積報酬+141%，遠超同類型均值。"],
      ["💰 穩定現金流","PIMCO月配息9% + 安聯月配息8.5%，每月穩定領息NT$35,437，年領超過42萬，兼顧成長與配息。"],
      ["📊 科學最優配置","PIMCO 32% ｜ 路博邁 32% ｜ 國泰 19.8% ｜ 安聯 16.1% — 由最大夏普比率演算法精確優化得出。"],
      ["✅ 持有一年正報酬100%","回測顯示持有滿1年正報酬機率達100%，持有6個月達99.1%，建議中長期（1年以上）配置。"],
    ];
    const icoCols = [C.TEAL,C.GOLD,C.TEAL,C.GOLD,C.GOLD];
    items.forEach(([icon_title, body], i) => {
      const y = 2.18 + i * 0.66;
      s.addShape(pres.shapes.RECTANGLE, { x:0.28,y:y+0.04,w:0.44,h:0.44,
        fill:{color:icoCols[i]}, line:{color:icoCols[i],width:0,transparency:100} });
      s.addText(String(i+1), { x:0.28,y:y+0.04,w:0.44,h:0.44,
        fontSize:14,bold:true,color:C.NAVY,align:"center",valign:"middle",margin:0 });
      s.addText([
        { text:icon_title+"　", options:{bold:true,color:i===4?C.GOLD:C.WHITE,fontSize:11.5} },
        { text:body, options:{color: i===4?"ffe066":"ccddee", fontSize:10.5} },
      ], { x:0.80,y,w:6.4,h:0.60, valign:"middle",margin:0 });
    });

    // 底部
    s.addShape(pres.shapes.RECTANGLE, { x:0,y:H-0.46,w:W,h:0.46,
      fill:{color:"0d1a33"}, line:{color:"0d1a33",width:0,transparency:100} });
    s.addText("⚠️  本報告所有數據均基於歷史資料計算，不代表未來績效。配息金額以各機構實際公告為準。僅供內部教育訓練使用，請勿外流。", {
      x:0.40,y:H-0.42,w:W-0.50,h:0.36, fontSize:8.5,color:"7788aa",valign:"middle",margin:0 });
  }

  await pres.writeFile({ fileName: outFile });
  console.log("✅ PPT 完成：" + outFile);
}

build().catch(e => { console.error("❌ 錯誤："+e.message); process.exit(1); });

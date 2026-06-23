import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path


# =========================
# 基础设置
# =========================

st.set_page_config(
    page_title="寻艺点赞榜",
    page_icon="💜",
    layout="centered",
)

CSV_FILE = Path("xunyee_like_fans_count.csv")


# =========================
# 工具函数
# =========================

def to_int(value):
    if pd.isna(value) or value == "":
        return 0

    try:
        return int(float(str(value).replace(",", "").replace("+", "").strip()))
    except Exception:
        return 0


def format_num(value):
    value = to_int(value)
    return f"{value:,}"


def get_col(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def normalize_xunyee_df(df):
    col_name = get_col(df, ["姓名", "艺人姓名", "超话名称"])
    col_rank = get_col(df, ["排名"])
    col_like = get_col(df, ["今日点赞", "实时获赞数", "获赞数"])
    col_distance = get_col(df, ["距上一名", "距离上一名", "超Like距离上一名"])
    col_fans = get_col(df, ["总粉丝量", "粉丝数"])
    col_check1 = get_col(df, ["1次人数", "点赞一次"])
    col_check2 = get_col(df, ["2次人数", "点赞两次"])
    col_check3 = get_col(df, ["3次人数", "点赞三次"])
    col_time = get_col(df, ["抓取时间", "更新时间"])

    output = pd.DataFrame()

    output["姓名"] = df[col_name] if col_name else ""
    output["排名"] = df[col_rank] if col_rank else ""
    output["今日点赞"] = df[col_like] if col_like else 0
    output["距上一名"] = df[col_distance] if col_distance else ""
    output["总粉丝量"] = df[col_fans] if col_fans else 0
    output["1次人数"] = df[col_check1] if col_check1 else 0
    output["2次人数"] = df[col_check2] if col_check2 else 0
    output["3次人数"] = df[col_check3] if col_check3 else 0
    output["抓取时间"] = df[col_time] if col_time else ""

    output["今日人数"] = (
        output["1次人数"].apply(to_int)
        + output["2次人数"].apply(to_int)
        + output["3次人数"].apply(to_int)
    )

    output["今日点赞_num"] = output["今日点赞"].apply(to_int)

    output = output.sort_values("今日点赞_num", ascending=False).reset_index(drop=True)
    output["排名"] = output.index + 1

    return output


def make_card(row):
    rank = int(row["排名"])
    name = row["姓名"]

    today_like = to_int(row["今日点赞"])
    fans = to_int(row["总粉丝量"])
    today_people = to_int(row["今日人数"])

    check1 = to_int(row["1次人数"])
    check2 = to_int(row["2次人数"])
    check3 = to_int(row["3次人数"])

    distance = row["距上一名"]

    total_people = max(today_people, 1)
    p3 = check3 / total_people * 100
    p2 = check2 / total_people * 100
    p1 = check1 / total_people * 100

    medal = ""
    if rank == 1:
        medal = "🥇"
    elif rank == 2:
        medal = "🥈"
    elif rank == 3:
        medal = "🥉"

    distance_html = ""
    if rank != 1 and str(distance) not in ["", "nan", "None"]:
        distance_html = f'<div class="distance">距上一名 {format_num(distance)}</div>'

    return f"""
    <div class="rank-card">
        <div class="card-top">
            <div class="left-area">
                <div class="rank-line">
                    <span class="rank-badge">#{rank}</span>
                    <span class="medal">{medal}</span>
                </div>
                <div class="name">{name}</div>
                {distance_html}
            </div>

            <div class="right-area">
                <div class="main-number">{format_num(today_like)}</div>
                <div class="main-label">今日点赞</div>
            </div>
        </div>

        <div class="meta-row">
            <div class="meta-box">
                <div class="meta-label">总粉丝量</div>
                <div class="meta-value">{format_num(fans)}</div>
            </div>
            <div class="meta-box">
                <div class="meta-label">今日人数</div>
                <div class="meta-value">{format_num(today_people)}</div>
            </div>
        </div>

        <div class="bar">
            <div class="bar-3" style="width:{p3}%"></div>
            <div class="bar-2" style="width:{p2}%"></div>
            <div class="bar-1" style="width:{p1}%"></div>
        </div>

        <div class="bottom-row">
            <div><span class="dot green"></span>3次 <b>{format_num(check3)}</b> <span>{p3:.0f}%</span></div>
            <div><span class="dot blue"></span>2次 <b>{format_num(check2)}</b> <span>{p2:.0f}%</span></div>
            <div><span class="dot pink"></span>1次 <b>{format_num(check1)}</b> <span>{p1:.0f}%</span></div>
        </div>
    </div>
    """


# =========================
# 读取数据
# =========================

if not CSV_FILE.exists():
    st.error(f"没有找到 CSV 文件：{CSV_FILE}")
    st.stop()

df_raw = pd.read_csv(CSV_FILE)
df = normalize_xunyee_df(df_raw)

last_update = ""
if "抓取时间" in df.columns and len(df) > 0:
    last_update = str(df["抓取时间"].iloc[0])

top_like = df["今日点赞_num"].max() if len(df) > 0 else 0
total_people = len(df)

cards_html = ""
for _, row in df.iterrows():
    cards_html += make_card(row)


# =========================
# 整体 HTML 页面
# =========================

full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 20px 14px 34px 14px;
    background: linear-gradient(180deg, #f7f6ff 0%, #ffffff 58%);
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
    color: #22243a;
}}

.page {{
    max-width: 520px;
    margin: 0 auto;
}}

.header {{
    margin-bottom: 18px;
}}

.title-row {{
    display: flex;
    align-items: center;
    gap: 9px;
}}

.title {{
    font-size: 31px;
    font-weight: 900;
    letter-spacing: -0.5px;
    color: #23233f;
}}

.status-dot {{
    width: 9px;
    height: 9px;
    background: #22c986;
    border-radius: 50%;
    display: inline-block;
}}

.status-text {{
    color: #6e6d83;
    font-size: 14px;
    font-weight: 700;
}}

.sub-title {{
    color: #9a99ad;
    font-size: 14px;
    margin-top: 6px;
}}

.top-info {{
    background: rgba(255,255,255,0.86);
    border: 1px solid #efeff8;
    padding: 13px 15px;
    border-radius: 18px;
    margin-bottom: 20px;
    color: #6e6d83;
    font-size: 14px;
    line-height: 1.7;
    box-shadow: 0 6px 18px rgba(86, 74, 140, 0.04);
}}

.top-info b {{
    color: #34344f;
}}

.rank-card {{
    background: rgba(255,255,255,0.98);
    border-radius: 24px;
    padding: 20px 20px 17px 20px;
    margin-bottom: 17px;
    box-shadow: 0 10px 26px rgba(86, 74, 140, 0.11);
    border: 1px solid #eeeeF7;
    position: relative;
    overflow: hidden;
}

.rank-card::after {{
    content: "四唱一张奕然;
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%) rotate(-18deg);
    font-size: 30px;
    font-weight: 900;
    letter-spacing: 2px;
    color: rgba(98, 87, 216, 0.18);
    pointer-events: none;
    white-space: nowrap;
    z-index: 2;
}

.rank-card > * {{
    position: relative;
    z-index: 3;
}
.card-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
}}

.rank-line {{
    display: flex;
    align-items: center;
    gap: 8px;
}}

.rank-badge {{
    display: inline-block;
    background: #f0edff;
    color: #6557e8;
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 800;
    font-size: 14px;
}}

.medal {{
    font-size: 18px;
}}

.name {{
    font-size: 28px;
    font-weight: 900;
    margin-top: 9px;
    color: #22243a;
    line-height: 1.1;
}}

.right-area {{
    text-align: right;
    min-width: 135px;
}}

.main-number {{
    font-size: 43px;
    font-weight: 950;
    color: #6257d8;
    line-height: 1;
}}

.main-label {{
    margin-top: 6px;
    font-size: 13px;
    color: #9b9ab0;
    font-weight: 700;
}}

.distance {{
    margin-top: 9px;
    color: #df3360;
    background: #fff0f4;
    display: inline-block;
    padding: 5px 10px;
    border-radius: 10px;
    font-weight: 800;
    font-size: 13px;
}}

.meta-row {{
    margin-top: 20px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}}

.meta-box {{
    background: #fafaff;
    border: 1px solid #f0f0fa;
    border-radius: 16px;
    padding: 11px 12px;
}}

.meta-label {{
    color: #9a9aad;
    font-size: 13px;
    font-weight: 700;
}}

.meta-value {{
    color: #34344f;
    font-size: 21px;
    font-weight: 900;
    margin-top: 2px;
}}

.bar {{
    display: flex;
    height: 10px;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 17px;
    background: #eeeef6;
}}

.bar-3 {{
    background: #23cfa4;
}}

.bar-2 {{
    background: #7b8cff;
}}

.bar-1 {{
    background: #ff6f91;
}}

.bottom-row {{
    margin-top: 13px;
    color: #85849a;
    font-size: 13px;
    display: flex;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
}}

.bottom-row b {{
    color: #34344f;
}}

.dot {{
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 5px;
}}

.green {{ background: #23cfa4; }}
.blue {{ background: #7b8cff; }}
.pink {{ background: #ff6f91; }}

.footer {{
    text-align: center;
    color: #aaa9bc;
    font-size: 12px;
    margin-top: 24px;
    padding-bottom: 20px;
}}

@media (max-width: 430px) {{
    body {{
        padding: 18px 12px 30px 12px;
    }}

    .title {{
        font-size: 28px;
    }}

    .name {{
        font-size: 25px;
    }}

    .main-number {{
        font-size: 38px;
    }}

    .right-area {{
        min-width: 120px;
    }}
}}
</style>
</head>

<body>
<div class="page">
    <div class="header">
        <div class="title-row">
            <div class="title">寻艺点赞榜</div>
            <span class="status-dot"></span>
            <span class="status-text">只读展示</span>
        </div>
        <div class="sub-title">公开只读数据面板 · 第一版</div>
    </div>

    <div class="top-info">
        当前人数：<b>{total_people}</b>　
        最高点赞：<b>{format_num(top_like)}</b><br>
        上次更新时间：<b>{last_update}</b>
    </div>

    {cards_html}

    <div class="footer">
        数据来源：寻艺接口抓取 CSV · 页面仅展示，不含任何登录信息
    </div>
</div>
</body>
</html>
"""

height = max(900, 260 + len(df) * 275)

components.html(
    full_html,
    height=height,
    scrolling=True,
)

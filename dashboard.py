import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="🎀数据榜",
    page_icon="💜",
    layout="centered",
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    .stDeployButton {display: none !important;}

    .block-container {
        max-width: 760px;
        padding-top: 10px;
        padding-left: 8px;
        padding-right: 8px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
        background: #f7f5ff;
        border: 1px solid #eeebff;
        padding: 6px;
        border-radius: 999px;
        width: fit-content;
        margin: 0 auto 8px auto;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        padding: 7px 16px;
        color: #6257d8;
        font-weight: 900;
    }

    .stTabs [aria-selected="true"] {
        background: white;
        box-shadow: 0 5px 14px rgba(98, 87, 216, 0.12);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

XUNYEE_CSV = Path("xunyee_like_fans_count.csv")
BAIDU_CSV = Path("baidu_send_flower_data.csv")


def to_int(value):
    if pd.isna(value) or value == "":
        return 0
    try:
        return int(float(str(value).replace(",", "").replace("+", "").strip()))
    except Exception:
        return 0


def format_num(value):
    return f"{to_int(value):,}"


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


def normalize_baidu_df(df):
    col_name = get_col(df, ["姓名", "艺人姓名"])
    col_rank = get_col(df, ["排名"])
    col_gift = get_col(df, ["今日送花", "送花数"])
    col_user = get_col(df, ["送花人数", "参与人数"])
    col_avg = get_col(df, ["人均送花"])
    col_level = get_col(df, ["等级"])
    col_time = get_col(df, ["抓取时间", "更新时间"])
    col_error = get_col(df, ["错误信息"])

    output = pd.DataFrame()
    output["姓名"] = df[col_name] if col_name else ""
    output["排名"] = df[col_rank] if col_rank else ""
    output["今日送花"] = df[col_gift] if col_gift else 0
    output["送花人数"] = df[col_user] if col_user else 0
    output["人均送花"] = df[col_avg] if col_avg else 0
    output["等级"] = df[col_level] if col_level else ""
    output["抓取时间"] = df[col_time] if col_time else ""
    output["错误信息"] = df[col_error] if col_error else ""
    output["今日送花_num"] = output["今日送花"].apply(to_int)
    output = output.sort_values("今日送花_num", ascending=False).reset_index(drop=True)
    output["排名"] = output.index + 1

    distances = []
    for i, row in output.iterrows():
        if i == 0:
            distances.append("")
        else:
            prev_val = to_int(output.loc[i - 1, "今日送花"])
            curr_val = to_int(row["今日送花"])
            distances.append(prev_val - curr_val if prev_val and curr_val else "")
    output["距上一名"] = distances
    return output


def medal_for(rank):
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    return ""


def make_xunyee_card(row):
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

    distance_html = ""
    if rank != 1 and str(distance) not in ["", "nan", "None"]:
        distance_html = f'<span class="gap-pill">距上一名 {format_num(distance)}</span>'

    return f"""
    <div class="compact-card">
        <div class="card-watermark">四唱一张奕然</div>
        <div class="card-content">
            <div class="top-line">
                <div class="identity">
                    <span class="rank-badge">#{rank}</span>
                    <span class="medal">{medal_for(rank)}</span>
                    <span class="name">{name}</span>
                </div>
                <div class="main-data">
                    <div class="main-number">{format_num(today_like)}</div>
                    <div class="main-label">今日点赞</div>
                </div>
            </div>

            <div class="gap-row">{distance_html}</div>

            <div class="mini-stats">
                <span>总粉丝 <b>{format_num(fans)}</b></span>
                <span>今日人数 <b>{format_num(today_people)}</b></span>
                <span>3次 <b>{format_num(check3)}</b></span>
            </div>

            <div class="bar">
                <div class="bar-3" style="width:{p3}%"></div>
                <div class="bar-2" style="width:{p2}%"></div>
                <div class="bar-1" style="width:{p1}%"></div>
            </div>

            <div class="bottom-row">
                <span><i class="dot green"></i>3次 {p3:.0f}%</span>
                <span><i class="dot blue"></i>2次 {p2:.0f}%</span>
                <span><i class="dot pink"></i>1次 {p1:.0f}%</span>
            </div>
        </div>
    </div>
    """


def make_baidu_card(row):
    rank = int(row["排名"])
    name = row["姓名"]
    today_gift = to_int(row["今日送花"])
    flower_users = to_int(row["送花人数"])
    avg_gift = to_int(row["人均送花"])
    level = row["等级"]
    distance = row["距上一名"]

    distance_html = ""
    if rank != 1 and str(distance) not in ["", "nan", "None"]:
        distance_html = f'<span class="gap-pill">距上一名 {format_num(distance)}</span>'

    level_html = ""
    if str(level) not in ["", "nan", "None"]:
        level_html = f'<span class="level-badge">{level}</span>'

    return f"""
    <div class="compact-card flower-card">
        <div class="card-watermark">四唱一张奕然</div>
        <div class="card-content">
            <div class="top-line">
                <div class="identity">
                    <span class="rank-badge">#{rank}</span>
                    <span class="medal">{medal_for(rank)}</span>
                    <span class="name">{name}</span>
                    {level_html}
                </div>
                <div class="main-data">
                    <div class="main-number flower-number">{format_num(today_gift)}</div>
                    <div class="main-label">今日送花</div>
                </div>
            </div>

            <div class="gap-row">{distance_html}</div>

            <div class="mini-stats two">
                <span>送花人数 <b>{format_num(flower_users)}</b></span>
                <span>人均送花 <b>{format_num(avg_gift)}</b></span>
            </div>

            <div class="single-bar">
                <div class="single-bar-fill"></div>
            </div>

            <div class="bottom-row">
                <span><i class="dot pink"></i>排名 #{rank}</span>
                <span><i class="dot green"></i>送花 {format_num(today_gift)}</span>
                <span><i class="dot blue"></i>人数 {format_num(flower_users)}</span>
            </div>
        </div>
    </div>
    """


COMMON_STYLE = """
<style>
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
    background: linear-gradient(180deg, #f6f3ff 0%, #ffffff 64%);
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
    color: #23233f;
}
.page {
    max-width: 620px;
    margin: 0 auto;
    padding: 12px 10px 28px 10px;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
}
.title-wrap { min-width: 0; }
.title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.title {
    font-size: 28px;
    font-weight: 950;
    letter-spacing: -0.6px;
    color: #23233f;
    line-height: 1.1;
}
.status-dot {
    width: 8px;
    height: 8px;
    background: #22c986;
    border-radius: 50%;
    display: inline-block;
}
.status-text {
    color: #7a7892;
    font-size: 12px;
    font-weight: 800;
}
.sub-title {
    color: #9a99ad;
    font-size: 12px;
    margin-top: 5px;
}
.update-time {
    text-align: right;
    color: #8d8ba5;
    font-size: 11px;
    line-height: 1.45;
    white-space: nowrap;
    padding-top: 2px;
}
.update-time b {
    display: block;
    color: #34344f;
    font-size: 12px;
}
.mini-bar {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin: 10px 0 12px 0;
}
.mini-box {
    background: rgba(255,255,255,0.92);
    border: 1px solid #efecff;
    border-radius: 16px;
    padding: 9px 10px;
    box-shadow: 0 6px 18px rgba(86, 74, 140, 0.06);
}
.mini-label {
    color: #9a99ad;
    font-size: 11px;
    font-weight: 800;
    margin-bottom: 2px;
}
.mini-value {
    color: #34344f;
    font-size: 17px;
    font-weight: 950;
    line-height: 1.1;
}
.compact-card {
    position: relative;
    overflow: hidden;
    background: rgba(255,255,255,0.98);
    border: 1px solid #eeebfb;
    border-radius: 20px;
    padding: 13px 14px 12px 14px;
    margin-bottom: 10px;
    box-shadow: 0 8px 22px rgba(86, 74, 140, 0.10);
}
.card-watermark {
    position: absolute;
    left: 58%;
    top: 53%;
    transform: translate(-50%, -50%) rotate(-18deg);
    font-size: 26px;
    font-weight: 950;
    letter-spacing: 2px;
    color: rgba(98, 87, 216, 0.08);
    pointer-events: none;
    white-space: nowrap;
    z-index: 4;
    mix-blend-mode: multiply;
}
.card-content {
    position: relative;
    z-index: 8;
}
.top-line {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
}
.identity {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    flex-wrap: wrap;
}
.rank-badge {
    background: #f0edff;
    color: #6557e8;
    border-radius: 9px;
    padding: 4px 8px;
    font-weight: 950;
    font-size: 12px;
}
.medal { font-size: 13px; }
.name {
    font-size: 23px;
    font-weight: 950;
    color: #22243a;
    line-height: 1.1;
}
.level-badge {
    background: #fff0f4;
    color: #df3360;
    border-radius: 999px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 950;
}
.main-data { text-align: right; min-width: 108px; }
.main-number {
    font-size: 34px;
    font-weight: 950;
    color: #6257d8;
    line-height: 0.95;
    letter-spacing: -0.8px;
}
.main-label {
    margin-top: 4px;
    font-size: 11px;
    color: #9b9ab0;
    font-weight: 850;
}
.gap-row { min-height: 22px; margin-top: 3px; }
.gap-pill {
    display: inline-block;
    background: #fff0f4;
    color: #df3360;
    border-radius: 999px;
    padding: 4px 9px;
    font-size: 12px;
    font-weight: 950;
}
.mini-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 7px;
    margin-top: 4px;
}
.mini-stats.two { grid-template-columns: repeat(2, 1fr); }
.mini-stats span {
    background: #fbfaff;
    border: 1px solid #f0eefb;
    border-radius: 12px;
    padding: 7px 8px;
    color: #8d8ba5;
    font-size: 11px;
    font-weight: 850;
}
.mini-stats b {
    color: #34344f;
    font-size: 15px;
    font-weight: 950;
    margin-left: 3px;
}
.bar, .single-bar {
    display: flex;
    height: 8px;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 10px;
    background: #eeeef6;
}
.bar-3 { background: #23cfa4; }
.bar-2 { background: #7b8cff; }
.bar-1 { background: #ff6f91; }
.single-bar-fill {
    width: 100%;
    background: linear-gradient(90deg, #ff6f91 0%, #6257d8 100%);
}
.bottom-row {
    margin-top: 8px;
    color: #85849a;
    font-size: 11px;
    display: flex;
    justify-content: space-between;
    gap: 6px;
    flex-wrap: wrap;
    font-weight: 800;
}
.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 4px;
}
.green { background: #23cfa4; }
.blue { background: #7b8cff; }
.pink { background: #ff6f91; }
.footer {
    text-align: center;
    color: #aaa9bc;
    font-size: 11px;
    margin-top: 16px;
    padding-bottom: 14px;
}
@media (max-width: 430px) {
    .page { padding: 10px 8px 24px 8px; }
    .title { font-size: 25px; }
    .name { font-size: 21px; }
    .main-number { font-size: 30px; }
    .main-data { min-width: 96px; }
    .mini-bar { gap: 6px; }
    .mini-box { padding: 8px 8px; }
    .mini-value { font-size: 15px; }
    .mini-stats { gap: 6px; }
    .mini-stats span { padding: 6px 6px; }
    .mini-stats b { display: block; margin-left: 0; margin-top: 1px; }
    .card-watermark { font-size: 22px; left: 56%; }
}
</style>
"""


def build_page(title, subtitle, status_text, last_update, mini_items, cards_html, footer_text):
    mini_html = "".join(
        f"""
        <div class="mini-box">
            <div class="mini-label">{label}</div>
            <div class="mini-value">{value}</div>
        </div>
        """
        for label, value in mini_items
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
{COMMON_STYLE}
</head>
<body>
<div class="page">
    <div class="header">
        <div class="title-wrap">
            <div class="title-row">
                <div class="title">{title}</div>
                <span class="status-dot"></span>
                <span class="status-text">{status_text}</span>
            </div>
            <div class="sub-title">{subtitle}</div>
        </div>
        <div class="update-time">
            上次更新
            <b>{last_update}</b>
        </div>
    </div>

    <div class="mini-bar">
        {mini_html}
    </div>

    {cards_html}

    <div class="footer">{footer_text}</div>
</div>
</body>
</html>
"""


def render_xunyee_page():
    if not XUNYEE_CSV.exists():
        st.error(f"没有找到 CSV 文件：{XUNYEE_CSV}")
        return

    df_raw = pd.read_csv(XUNYEE_CSV)
    df = normalize_xunyee_df(df_raw)
    last_update = str(df["抓取时间"].iloc[0]) if len(df) > 0 else ""
    top_like = df["今日点赞_num"].max() if len(df) > 0 else 0
    total_people = len(df)
    total_today_people = df["今日人数"].apply(to_int).sum() if len(df) > 0 else 0

    cards_html = "".join(make_xunyee_card(row) for _, row in df.iterrows())
    full_html = build_page(
        title="寻艺点赞榜",
        subtitle="自动更新 · 紧凑看板版",
        status_text="整点更新",
        last_update=last_update,
        mini_items=[
            ("当前人数", format_num(total_people)),
            ("最高点赞", format_num(top_like)),
            ("总参与人数", format_num(total_today_people)),
        ],
        cards_html=cards_html,
        footer_text="数据来源：寻艺接口抓取 CSV · 页面仅展示，不含任何登录信息",
    )
    height = max(900, 160 + len(df) * 160)
    components.html(full_html, height=height, scrolling=True)


def render_baidu_page():
    if not BAIDU_CSV.exists():
        st.error(f"没有找到 CSV 文件：{BAIDU_CSV}")
        return

    df_raw = pd.read_csv(BAIDU_CSV)
    df = normalize_baidu_df(df_raw)
    last_update = str(df["抓取时间"].iloc[0]) if len(df) > 0 else ""
    top_gift = df["今日送花_num"].max() if len(df) > 0 else 0
    total_people = len(df)
    total_flowers = df["今日送花"].apply(to_int).sum() if len(df) > 0 else 0

    cards_html = "".join(make_baidu_card(row) for _, row in df.iterrows())
    full_html = build_page(
        title="百度送花榜",
        subtitle="自动更新 · 紧凑看板版",
        status_text="整点更新",
        last_update=last_update,
        mini_items=[
            ("当前人数", format_num(total_people)),
            ("最高送花", format_num(top_gift)),
            ("总送花", format_num(total_flowers)),
        ],
        cards_html=cards_html,
        footer_text="数据来源：百度送花接口抓取 CSV · 页面仅展示，不含任何登录信息",
    )
    height = max(900, 160 + len(df) * 150)
    components.html(full_html, height=height, scrolling=True)


tab1, tab2 = st.tabs(["💜 寻艺点赞", "🌸 百度送花"])
with tab1:
    render_xunyee_page()
with tab2:
    render_baidu_page()

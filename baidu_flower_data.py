import csv
import time
import os
import requests
from datetime import datetime, timezone, timedelta

from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd


def append_history(df, history_path):
    history_path = Path(history_path)

    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    df_history = df.copy()

    if "抓取时间" not in df_history.columns:
        df_history["抓取时间"] = now
    else:
        df_history["抓取时间"] = df_history["抓取时间"].fillna(now)
        df_history.loc[
            df_history["抓取时间"].astype(str).str.strip() == "",
            "抓取时间"
        ] = now

    if history_path.exists():
        old = pd.read_csv(history_path)
        combined = pd.concat([old, df_history], ignore_index=True)
    else:
        combined = df_history

    combined.to_csv(history_path, index=False, encoding="utf-8-sig")


# =========================
# 1. 粘贴你的 Cookie
# =========================
# 把 curl 里 -b 'BDUSS=...; BAIDUID=...; ...' 那一整段粘贴到这里
COOKIE = os.getenv("BAIDU_COOKIE")

if not COOKIE:
    raise ValueError("缺少 BAIDU_COOKIE，请在 GitHub Secrets 里设置")
# =========================
# 2. 人员配置
# baikeid 需要你从对应页面 url 里拿
# =========================

PEOPLE = [
    {
        "name": "王橹杰",
        "abbr": "wlj",
        "baikeid": "64787018",
        "level": "L6",
    },
    {
        "name": "杨博文",
        "abbr": "ybw",
        "baikeid": "64790097",
        "level": "L6",
    },
    {
        "name": "左奇函",
        "abbr": "zqh",
        "baikeid": "60705549",
        "level": "L5",
    },
    {
        "name": "陈浚铭",
        "abbr": "cjm",
        "baikeid": "64762675",
        "level": "L6",
    },
    {
        "name": "张桂源",
        "abbr": "zgy",
        "baikeid": "64767448",
        "level": "L6",
    },
    {
        "name": "张函瑞",
        "abbr": "zhr",
        "baikeid": "64761230",
        "level": "L6",
    },
    {
        "name": "陈奕恒",
        "abbr": "cyh",
        "baikeid": "64786973",
        "level": "L5",
    },
    {
        "name": "张奕然",
        "abbr": "ZYR",
        "baikeid": "64787131",
        "level": "L1",
    },
    {
        "name": "李煜东",
        "abbr": "lyd",
        "baikeid": "65070593",
        "level": "L1",
    },
    {
        "name": "陈思罕",
        "abbr": "csh",
        "baikeid": "65213161",
        "level": "L3",
    },
]


# =========================
# 3. 接口配置
# =========================

URL = "https://figure.baidu.com/api/land/interact/getTrend"

HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    "origin": "https://figure.baidu.com",
    "referer": "https://figure.baidu.com/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "cookie": COOKIE,
}


# =========================
# 4. 工具函数
# =========================

def safe_int(value):
    if value is None or value == "":
        return 0

    value = str(value).replace(",", "").strip()

    try:
        if value.endswith("w"):
            return int(float(value[:-1]) * 10000)
        if value.endswith("万"):
            return int(float(value[:-1]) * 10000)
        return int(float(value))
    except Exception:
        return 0

def format_arrow_number(value):
    """
    用来显示同比涨幅。
    正数：↑ 20000
    负数：↓ -200
    0：↑ 0
    """
    value = safe_int(value)

    if value < 0:
        return f"↓ {value}"
    else:
        return f"↑ {value}"


def fetch_flower_data(person):
    """
    抓单个人的送花趋势数据。
    """
    payload = {
        "baikeid": person["baikeid"],
        "type": "0",
    }

    resp = requests.post(
        URL,
        headers=HEADERS,
        data=payload,
        timeout=20,
    )

    resp.raise_for_status()
    data = resp.json()

    if data.get("errno") != 0:
        raise ValueError(f"接口返回异常: {data}")

    return data


def extract_flower_data(person, response_json):
    """
    从 response 里提取：
    今日送花、送花人数、昨日同期送花、同比涨幅、同比人数涨幅。

    适配百度接口真实结构：
    {
        "data": {
            "trend": [...],
            "userGift": 10831,
            "userGiftStr": "1w",
            "userNum": 383,
            "userNumStr": "383"
        },
        "errno": 0
    }
    """

    # 重点：真实数据在 response_json["data"] 里面
    data = response_json.get("data", {})

    if not isinstance(data, dict):
        data = {}

    trend_list = []

    # 趋势列表一般在 data["trend"] 里
    if isinstance(data.get("trend"), list):
        trend_list = data.get("trend")
    elif isinstance(data.get("list"), list):
        trend_list = data.get("list")

    # 今日数据：优先用 data 顶层的 userGift / userNum
    today_gift = safe_int(
        data.get("userGift")
        or data.get("giftNum")
        or data.get("gift_num")
    )

    today_user = safe_int(
        data.get("userNum")
        or data.get("user_num")
        or data.get("userNumStr")
    )

    # 如果 data 顶层没有，再用 trend 最后一条
    latest_item = trend_list[-1] if trend_list else {}
    previous_item = trend_list[-2] if len(trend_list) >= 2 else {}

    if today_gift == 0:
        today_gift = safe_int(
            latest_item.get("giftNum")
            or latest_item.get("gift_num")
            or latest_item.get("userGift")
        )

    if today_user == 0:
        today_user = safe_int(
            latest_item.get("userNum")
            or latest_item.get("user_num")
            or latest_item.get("userNumStr")
        )

    # 昨日同期数据：用 trend 倒数第二条
    yesterday_gift = safe_int(
        previous_item.get("giftNum")
        or previous_item.get("gift_num")
        or previous_item.get("userGift")
    )

    yesterday_user = safe_int(
        previous_item.get("userNum")
        or previous_item.get("user_num")
        or previous_item.get("userNumStr")
    )

    avg_gift = ""
    if today_user > 0:
        avg_gift = int(today_gift / today_user)

    gift_diff = today_gift - yesterday_gift
    user_diff = today_user - yesterday_user

    return {
        "抓取时间": "",
        "缩写": person["abbr"],
        "姓名": person["name"],

        "今日送花": today_gift,
        "送花人数": today_user,
        "人均送花": avg_gift,

        "排名": "",

        "昨日同期送花": yesterday_gift,
        "同比涨幅": gift_diff,
        "同比涨幅显示": format_arrow_number(gift_diff),

        "昨日同期送花人数": yesterday_user,
        "同比人数涨幅": user_diff,
        "同比人数涨幅显示": format_arrow_number(user_diff),

        "等级": person.get("level", ""),
        "错误信息": "",
    }

# =========================
# 5. 主程序
# =========================

def main():
    rows = []

    china_tz = timezone(timedelta(hours=8))
    crawl_time = datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")

    for person in PEOPLE:
        name = person["name"]
        print(f"正在处理：{name}")

        try:
            data = fetch_flower_data(person)
            row = extract_flower_data(person, data)
            row["抓取时间"] = crawl_time
            rows.append(row)

            print(
                name,
                "今日送花 =", row["今日送花"],
                "送花人数 =", row["送花人数"],
                "人均送花 =", row["人均送花"],
            )

            time.sleep(0.5)

        except Exception as e:
            print(name, "抓取失败：", e)

            rows.append({
                "抓取时间": crawl_time,
                "缩写": person["abbr"],
                "姓名": person["name"],
                "今日送花": "",
                "送花人数": "",
                "人均送花": "",
                "排名": "",
                "昨日同期送花": "",
                "同比涨幅": "",
                "同比涨幅显示": "",
                "同比人数涨幅": "",
                "同比人数涨幅显示": "",
                "等级": person.get("level", ""),
                "错误信息": str(e),
            })

    # 按今日送花排序
    valid_rows = [r for r in rows if safe_int(r.get("今日送花")) > 0]
    invalid_rows = [r for r in rows if safe_int(r.get("今日送花")) <= 0]

    valid_rows.sort(
        key=lambda x: safe_int(x["今日送花"]),
        reverse=True
    )

    for i, row in enumerate(valid_rows):
        row["排名"] = i + 1

    final_rows = valid_rows + invalid_rows

    output_file = "baidu_send_flower_data.csv"

    fieldnames = [
        "抓取时间",

        "姓名",
        "今日送花",
        "送花人数",
        "人均送花",
        "排名",
        "等级",
        "错误信息",
    ]

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(final_rows)

    print("\n完成，已导出：", output_file)


if __name__ == "__main__":
    main()

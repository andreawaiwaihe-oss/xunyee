
import time
import csv
import os
import requests
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("XUNYEE_TOKEN")
JSESSIONID = os.getenv("XUNYEE_JSESSIONID")

if not TOKEN or not JSESSIONID:
    raise ValueError("缺少 XUNYEE_TOKEN 或 XUNYEE_JSESSIONID，请在 GitHub Secrets 里设置")

#若运行不了 重新抓取cURL  填入正确的 Token和jsessionid


NAMES = [
    "王橹杰",
    "杨博文",
    "左奇函",
    "陈浚铭",
    "张桂源",
    "张函瑞",
    "张奕然",
    "李煜东",
    "陈思罕",
    "陈奕恒",
]


# =========================
# 3. 接口配置
# =========================

SEARCH_URL = "https://api.xunyee.cn/xunyee/person/search"
INFO_URL = "https://api.xunyee.cn/xunyee/vcuser_person/person_info"
FANS_URL = "https://api.xunyee.cn/xunyee/vcuser_person/fans_check"

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "User-Agent": "xunyee/3 CFNetwork/3826.600.41.2.1 Darwin/24.6.0",
    "token": TOKEN,
    "Cookie": f"JSESSIONID={JSESSIONID}",
}


# =========================
# 4. 搜索名字，拿 person_id
# =========================

def search_person(name):
    params = {
        "current": 1,
        "size": 18,
        "name": name,
    }

    resp = requests.get(
        SEARCH_URL,
        headers=HEADERS,
        params=params,
        timeout=15
    )
    resp.raise_for_status()

    data = resp.json()

    if data.get("code") != 0:
        raise ValueError(f"搜索接口返回异常: {data}")

    records = data.get("data", {}).get("records", [])

    if not records:
        return None

    first = records[0]

    person_id = first.get("person") or first.get("id")
    matched_name = first.get("zh_name") or first.get("name")

    return {
        "person_id": person_id,
        "matched_name": matched_name,
    }


# =========================
# 5. 抓实时获赞数
# =========================

def get_like_count(person_id):
    resp = requests.get(
        INFO_URL,
        headers=HEADERS,
        params={"person": person_id},
        timeout=15
    )
    resp.raise_for_status()

    data = resp.json()

    if data.get("code") != 0:
        raise ValueError(f"实时获赞数接口返回异常: {data}")

    info = data.get("data", {}) or {}

    return {
        "name": info.get("zh_name"),
        "like_count": info.get("check"),  # check = 实时获赞数
    }


# =========================
# 6. 抓粉丝数 + 点赞一次/两次/三次
# =========================

def get_fans_data(person_id):
    resp = requests.get(
        FANS_URL,
        headers=HEADERS,
        params={"person": person_id},
        timeout=15
    )
    resp.raise_for_status()

    data = resp.json()

    if data.get("code") != 0:
        raise ValueError(f"粉丝数接口返回异常: {data}")

    info = data.get("data", {}) or {}

    return {
        "fans_count": info.get("fans_count"),  # 粉丝数
        "check1": info.get("check1"),          # 点赞一次
        "check2": info.get("check2"),          # 点赞两次
        "check3": info.get("check3"),          # 点赞三次
    }


# =========================
# 7. 主程序
# =========================

def main():
    rows = []

    # 导出文件里的抓取时间
    china_tz = timezone(timedelta(hours=8))
    crawl_time = datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")

    for name in NAMES:
        print(f"正在处理：{name}")

        try:
            search_result = search_person(name)

            if search_result is None:
                print(f"{name}：未搜索到")

                rows.append({
                    "抓取时间": crawl_time,
                    "艺人姓名": name,
                    "实时获赞数": "",
                    "粉丝数": "",
                    "点赞一次": "",
                    "点赞两次": "",
                    "点赞三次": "",
                    "错误信息": "未搜索到",
                })

                continue

            person_id = search_result["person_id"]
            matched_name = search_result["matched_name"]

            print(f"搜索匹配：{name} → {matched_name}, person_id={person_id}")

            like_info = get_like_count(person_id)
            fans_data = get_fans_data(person_id)

            row = {
                "抓取时间": crawl_time,
                "艺人姓名": name,
                "实时获赞数": like_info["like_count"],
                "粉丝数": fans_data["fans_count"],
                "点赞一次": fans_data["check1"],
                "点赞两次": fans_data["check2"],
                "点赞三次": fans_data["check3"],
                "错误信息": "",
            }

            rows.append(row)

            print(
                f"{name} → "
                f"实时获赞数: {row['实时获赞数']}，"
                f"粉丝数: {row['粉丝数']}，"
                f"点赞一次: {row['点赞一次']}，"
                f"点赞两次: {row['点赞两次']}，"
                f"点赞三次: {row['点赞三次']}"
            )

            time.sleep(0.5)

        except Exception as e:
            print(f"{name} 抓取失败：{e}")

            rows.append({
                "抓取时间": crawl_time,
                "艺人姓名": name,
                "实时获赞数": "",
                "粉丝数": "",
                "点赞一次": "",
                "点赞两次": "",
                "点赞三次": "",
                "错误信息": str(e),
            })

    # 按实时获赞数从高到低排序
    # 按实时获赞数从高到低排序
    rows.sort(
        key=lambda x: int(x["实时获赞数"]) if x["实时获赞数"] not in [None, ""] else -1,
        reverse=True
    )

    # 加排名 + 计算距离上一名
    for i, row in enumerate(rows):
        row["排名"] = i + 1

        if i == 0:
            row["距离上一名"] = ""
        else:
            prev_like = rows[i - 1]["实时获赞数"]
            curr_like = row["实时获赞数"]

            if prev_like not in [None, ""] and curr_like not in [None, ""]:
                row["距离上一名"] = int(prev_like) - int(curr_like)
            else:
                row["距离上一名"] = ""

   output_file = "xunyee_like_fans_count.csv"

    fieldnames = [
        "抓取时间",
        "排名",
        "艺人姓名",
        "实时获赞数",
        "距离上一名",
        "粉丝数",
        "点赞一次",
        "点赞两次",
        "点赞三次",
        "错误信息",
]

with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(rows)

history_file = "xunyee_like_fans_count_history.csv"
history_exists = os.path.exists(history_file)

with open(history_file, "a", newline="", encoding="utf-8-sig") as hf:
    history_writer = csv.DictWriter(
        hf,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )

    if not history_exists:
        history_writer.writeheader()

    history_writer.writerows(rows)

    print("\n抓取完成，已导出：")
    print(output_file)

    print("\n结果如下：")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()

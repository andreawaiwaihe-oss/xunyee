# -*- coding: utf-8 -*-
"""
微博超话数据抓取脚本

功能：
1. 抓帖子总数、粉丝数、阅读数
2. 抓日新帖、今日新增互动、今日新增粉丝
3. 抓今日签到人数
4. 抓准确超Like人数；如果主页面抓不到，则用 cardlist 兜底
5. 按日新帖排序
6. 计算距离上一名
7. 导出 CSV

注意：
AUTHORIZATION / GSID / X_SESSIONID / X_VALIDATOR / X_SHANHAI_PASS 会过期。
如果运行时报 401 / 403 / 登录失败 / 数据为空，需要重新用 Charles 抓新的 cURL 替换顶部变量。
"""

import csv
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests


# =========================
# 1. 微博登录信息
# 来自你刚刚发的 cURL
# =========================

AUTHORIZATION = os.getenv("WEIBO_AUTHORIZATION", "").strip()
GSID = os.getenv("WEIBO_GSID", "").strip()
AID = os.getenv("WEIBO_AID", "").strip()
X_SESSIONID = os.getenv("WEIBO_X_SESSIONID", "").strip()
X_VALIDATOR = os.getenv("WEIBO_X_VALIDATOR", "").strip()
X_SHANHAI_PASS = os.getenv("WEIBO_X_SHANHAI_PASS", "").strip()

missing_secrets = [
    name for name, value in {
        "WEIBO_AUTHORIZATION": AUTHORIZATION,
        "WEIBO_GSID": GSID,
        "WEIBO_AID": AID,
        "WEIBO_X_SESSIONID": X_SESSIONID,
        "WEIBO_X_VALIDATOR": X_VALIDATOR,
        "WEIBO_X_SHANHAI_PASS": X_SHANHAI_PASS,
    }.items()
    if not value
]

if missing_secrets:
    raise ValueError(f"缺少 GitHub Secrets / 环境变量: {missing_secrets}")


# =========================
# 2. 接口 URL
# =========================

DETAIL_URL = "https://api.weibo.cn/2/!/wbox/c0p9sg9tw9/topic_page_detail"
CARDLIST_URL = "https://api.weibo.cn/2/cardlist"
TIMELINE_URL = "https://api.weibo.cn/2/statuses/container_timeline_topicpage"


# =========================
# 3. 通用 headers
# =========================

COMMON_HEADERS = {
    "Host": "api.weibo.cn",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "snrt": "normal",
    "authorization": AUTHORIZATION,
    "x-sessionid": X_SESSIONID,
    "x-engine-type": "cronet-114.0.5735.246",
    "x-shanhai-pass": X_SHANHAI_PASS,
    "user-agent": "Weibo/99891 (iPhone; iOS 18.7.8; Scale/3.00)",
    "x-log-uid": "4076053770",
    "x-validator": X_VALIDATOR,
    "x-log-level": "sla",
    "accept": "*/*",
    "accept-language": "en-US,en",
}


# =========================
# 4. 通用 params
# =========================

BASE_PARAMS = {
    "aid": AID,
    "b": "0",
    "c": "iphone",
    "dlang": "zh-Hans-CA",
    "from": "10G6093010",
    "ft": "0",
    "gsid": GSID,
    "lang": "zh_CN",
    "launchid": "10000365--x",
    "networktype": "wifi",
    "s": "f77c5241",
    "sflag": "1",
    "skin": "default",
    "ua": "iPhone16,2__weibo__16.6.0__iphone__os18.7.8",
    "v_f": "1",
    "v_p": "93",
    "wm": "3333_2001",
    "ul_sid": "F7CDAD7D-F5DA-488A-A339-734A554CF938",
    "ul_hid": "F7CDAD7D-F5DA-488A-A339-734A554CF938",
    "ul_ctime": "1781058978676",
}


# =========================
# 5. 超话名单
# 继续用 flow_id，不需要改成 topic_id
# =========================

TOPICS = [
    {"name": "张奕然", "flow_id": "100808db807a7a7c131532c93920af92091f0e"},
    {"name": "王橹杰", "flow_id": "1008080587fa0e8198ad45108f3a0ef6e08d3a"},
    {"name": "杨博文", "flow_id": "100808d6a74ff407eb78a82d25736e3d9b70e6"},
    {"name": "陈浚铭", "flow_id": "1008084355c9e8721265763013249de968659b"},
    {"name": "张桂源", "flow_id": "10080831fefcc84e0d418e5c8e770cc744a6b9"},
    {"name": "张函瑞", "flow_id": "100808401952cfddf46fb45006244104aeee57"},
    {"name": "陈奕恒", "flow_id": "100808416561dd8d6e5365a23477dce47fa369"},
    {"name": "左奇函", "flow_id": "100808cd4fd2228cfcafbc05e5a648d226d33a"},
    {"name": "李煜东", "flow_id": "1008082b86ead745096b54876594bc81231735"},
    {"name": "陈思罕", "flow_id": "10080830d522c8bbfa0aea0f9c4fba44dc4bee"},
    {"name": "官俊臣", "flow_id": "10080858efc801d295f5a2a5b0b2f5ca787f3c"},
    {"name": "王烁然", "flow_id": "100808fa667753a291cb66da074b5c3767e037"},
    {"name": "聂玮辰", "flow_id": "100808939ae616ddabb6fc03221cdb2b81438f"},
    {"name": "魏子宸", "flow_id": "100808ba6fef03a4d777b0d760bf631cc89665"},
    {"name": "杨涵博", "flow_id": "100808deeb48e80d17c7e4feb0f072bec910b0"},
]


# =========================
# 6. 导出设置
# =========================

OUTPUT_FILE = "weibo_chaohua_data.csv"
SORT_FIELD = "日新帖"

FIELDNAMES = [
    "抓取时间",
    "排名",
    "超话名称",
    "艺人姓名",

    "日新帖",

    "今日新增粉丝",

    "今日签到人数",
    "今日签到",

    "超Like人数",
    "超Like",
    "距离上一名",

    "错误信息",
]


# =========================
# 7. 工具函数
# =========================

def parse_chinese_number(text):
    """
    把 2539万、40万、3.6万、1.2万、6432 转成整数。
    """
    if text is None or text == "":
        return ""

    text = str(text).replace(",", "").strip()

    try:
        if text.endswith("万"):
            return int(float(text[:-1]) * 10000)
        if text.endswith("亿"):
            return int(float(text[:-1]) * 100000000)
        return int(float(text))
    except ValueError:
        return ""


def parse_chaolike_display(raw_value):
    """
    cardlist 兜底用：
    6432 -> 6432
    1.2万 -> 12000+
    """
    if raw_value is None or raw_value == "":
        return ""

    raw_value = str(raw_value).replace(",", "").strip()

    try:
        if raw_value.endswith("万"):
            number = int(float(raw_value[:-1]) * 10000)
            return f"{number}+"

        if raw_value.endswith("亿"):
            number = int(float(raw_value[:-1]) * 100000000)
            return f"{number}+"

        return int(float(raw_value))

    except ValueError:
        return ""


def force_text_for_csv(value):
    """
    防止 Numbers / Excel 把 12000+ 自动改成 12000。
    """
    if value is None or value == "":
        return ""

    value = str(value)

    if value.endswith("+"):
        return f'="{value}"'

    return value


def walk(obj):
    """
    递归遍历 JSON。
    """
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def get_topic_id(topic):
    """
    兼容：
    flow_id = 100808...
    topic_id = 1022:100808...
    """
    if "topic_id" in topic:
        return topic["topic_id"]

    if "flow_id" in topic:
        return "1022:" + topic["flow_id"]

    raise KeyError("topic_id 或 flow_id 都没有")


def get_raw_topic_id(topic):
    """
    1022:100808xxxx -> 100808xxxx
    """
    topic_id = get_topic_id(topic)

    if ":" in topic_id:
        return topic_id.split(":", 1)[1]

    return topic_id


def get_core_id(topic):
    """
    100808db807... -> db807...
    """
    raw_topic_id = get_raw_topic_id(topic)

    if raw_topic_id.startswith("100808"):
        return raw_topic_id.replace("100808", "", 1)

    return raw_topic_id


def get_chaolike_container_id(topic):
    """
    db807... -> 231140db807..._-_chaolikenew
    """
    core_id = get_core_id(topic)
    return f"231140{core_id}_-_chaolikenew"


def get_profile_container_id(topic):
    """
    db807... -> 232476db807...
    """
    core_id = get_core_id(topic)
    return f"232476{core_id}"


def to_sort_number(value):
    """
    排序用。兼容数字、空值、12000+、='12000+'。
    """
    if value is None or value == "":
        return -1

    value = str(value).replace('="', "").replace('"', "").replace("+", "").strip()

    try:
        return int(float(value))
    except ValueError:
        return -1


# =========================
# 8. 接口函数
# =========================

def fetch_topic_detail(topic):
    """
    日新帖接口：
    抓帖子总数、粉丝数、阅读数、日新帖、今日新增互动、今日新增粉丝。
    """
    params = BASE_PARAMS.copy()

    params.update({
        "topic_id": get_topic_id(topic),
    })

    resp = requests.get(
        DETAIL_URL,
        headers=COMMON_HEADERS,
        params=params,
        timeout=20,
    )

    resp.raise_for_status()
    return resp.json()


def fetch_timeline_topicpage(topic):
    """
    主页面接口：
    抓准确超Like人数 + 今日签到人数。
    """
    raw_topic_id = get_raw_topic_id(topic)
    topic_name = topic["name"]

    params = BASE_PARAMS.copy()

    params.update({
        "flowId": f"{raw_topic_id}_-_recommend",
        "invokeType": "manual",
        "manualType": "pull",
        "pageDataType": "flow",
        "taskType": "refresh",
    })

    data = {
        "bizType": "common|supergroup",
        "book_reservation": "1",
        "card159164_emoji_enable": "1",
        "count": "15",
        "dynamicBundleVersion": "1514497",
        "featurecode": "10000085",
        "feedDynamicEnable": "1",

        "fid": f"{raw_topic_id}_-_recommend",
        "flowId": f"{raw_topic_id}_-_recommend",
        "flowVersion": "0.0.1",

        "image_fusion_3_iOS": "1",
        "invokeType": "manual",
        "is_album_water_fall": "1",
        "is_container": "1",
        "is_header_sticky": "0",
        "is_push_alert": "1",
        "is_push_open": "1",
        "lastItemTime": "0",

        "manualType": "pull",
        "mix_media_enable": "1",
        "moduleID": "pagecard",
        "need_new_pop": "1",

        "page": "1",
        "pageDataType": "flow",
        "page_common_ext": "topicPrompt:1|page:recommend=1|hide_page:2",
        "page_interrupt_enable": "1",
        "pagingType": "page",

        "pd_redpacket2022_enable": "1",
        "refreshtype": "clear",
        "sg_flow_header_enable": "1",
        "sg_tab_config": "2",
        "sgtotal_activity_enable": "1",

        "taskType": "refresh",
        "tz": "America/Toronto",
        "uicode": "10000011",

        # 这个是搜索词，不影响核心抓取
        "extparam": topic_name,
    }

    resp = requests.post(
        TIMELINE_URL,
        headers=COMMON_HEADERS,
        params=params,
        data=data,
        timeout=20,
    )

    resp.raise_for_status()
    return resp.json()


def fetch_cardlist(topic):
    """
    cardlist 接口：兜底抓超Like。
    如果主页面接口抓不到准确超Like，就用这个接口抓 6432 / 12000+。
    """
    raw_topic_id = get_raw_topic_id(topic)
    chaolike_container_id = get_chaolike_container_id(topic)
    profile_container_id = get_profile_container_id(topic)

    params = BASE_PARAMS.copy()

    params.update({
        "card159164_emoji_enable": "1",
        "client_key": "59aa7c733bbc2cb9f5b8de4898486026",

        "containerid": chaolike_container_id,
        "fid": chaolike_container_id,
        "lfid": "0",

        "count": "20",
        "page": "1",

        "follow_more_btn_enable": "1",
        "image_fusion_3_iOS": "1",
        "image_type": "heif",
        "is_push_alert": "1",
        "luicode": "80000001",
        "moduleID": "pagecard",
        "need_head_cards": "1",
        "need_new_pop": "1",

        "orifid": (
            f"profile_me$${raw_topic_id}_-_recommend$$"
            f"{profile_container_id}__5603091503_-_page_profile$$"
            f"{profile_container_id}_-_profile_allbadge$$0"
        ),

        "oriuicode": "10000011_10000011_10001419_10000011_80000001",
        "pd_redpacket2022_enable": "1",
        "profile_search_opt": "1",
        "qa_optimize_enable": "1",
        "refresh_type": "0",
        "request_referer": "-1",
        "source_code": "10000011_profile_me",
        "st_bottom_bar_new_style_enable": "1",
        "sys_notify_open": "1",
        "tz": "America/Toronto",
        "uicode": "10000011",
    })

    resp = requests.get(
        CARDLIST_URL,
        headers=COMMON_HEADERS,
        params=params,
        timeout=20,
    )

    resp.raise_for_status()
    return resp.json()


# =========================
# 9. 提取函数
# =========================

def split_summary(summary_text):
    """
    把：
    2544.8万帖子 ｜ 40.3万椰蓉 ｜ 28.3亿阅读
    拆成帖子、粉丝、阅读。
    """
    result = {
        "帖子总数_原始": "",
        "帖子总数": "",
        "粉丝数_原始": "",
        "粉丝数": "",
        "阅读数_原始": "",
        "阅读数": "",
    }

    if not summary_text:
        return result

    parts = re.split(r"[｜|]", summary_text)

    for part in parts:
        part = part.strip()

        if "帖子" in part:
            raw = part.replace("帖子", "").strip()
            result["帖子总数_原始"] = raw
            result["帖子总数"] = parse_chinese_number(raw)

        elif "椰蓉" in part or "粉丝" in part:
            raw = part.replace("椰蓉", "").replace("粉丝", "").strip()
            result["粉丝数_原始"] = raw
            result["粉丝数"] = parse_chinese_number(raw)

        elif "阅读" in part:
            raw = part.replace("阅读", "").strip()
            result["阅读数_原始"] = raw
            result["阅读数"] = parse_chinese_number(raw)

    return result


def empty_row(topic_name, crawl_time, error_message=""):
    return {
        "抓取时间": crawl_time,
        "排名": "",
        "超话名称": topic_name,
        "艺人姓名": topic_name,

        "帖子总数_原始": "",
        "帖子总数": "",
        "粉丝数_原始": "",
        "粉丝数": "",
        "阅读数_原始": "",
        "阅读数": "",

        "日新帖_原始": "",
        "日新帖": "",


        "今日新增互动_原始": "",
        "今日新增互动": "",

        "今日新增粉丝_原始": "",
        "今日新增粉丝": "",

        "今日签到人数_原始": "",
        "今日签到人数": "",
        "今日签到": "",

        "超Like人数": "",
        "超Like": "",
        "距离上一名": "",

        "错误信息": error_message,
    }


def extract_detail_data(topic, data, crawl_time):
    """
    从 topic_page_detail 提取：
    帖子总数、粉丝数、阅读数、日新帖、今日新增互动、今日新增粉丝。
    """
    row = empty_row(topic["name"], crawl_time)

    try:
        found_data_block = None

        for item in walk(data):
            if not isinstance(item, dict):
                continue

            if item.get("title") == "数据" and "details" in item:
                found_data_block = item
                break

        if found_data_block is None:
            row["错误信息"] = "未找到数据模块"
            return row

        summary_text = found_data_block.get("content", "")
        summary_result = split_summary(summary_text)
        row.update(summary_result)

        details = found_data_block.get("details", [])

        for item in details:
            title = str(item.get("title", ""))
            content = str(item.get("content", ""))

            if "互动" in title:
                row["今日新增互动_原始"] = content
                row["今日新增互动"] = parse_chinese_number(content)

            elif "粉丝" in title:
                row["今日新增粉丝_原始"] = content
                row["今日新增粉丝"] = parse_chinese_number(content)

            elif title in ["今日新增", "今日新增帖子", "今日新帖", "今日发帖"] or "新帖" in title or "发帖" in title:
                row["日新帖_原始"] = content
                row["日新帖"] = parse_chinese_number(content)

        return row

    except Exception as e:
        row["错误信息"] = str(e)
        return row


def extract_timeline_extra_data(data):
    """
    从 container_timeline_topicpage 里提取：
    1. 准确超Like人数：超LIKE 14437人
    2. 今日签到人数：今日签到10万人
    """
    result = {
        "超Like人数": "",
        "今日签到人数_原始": "",
        "今日签到人数": "",
    }

    for item in walk(data):
        if not isinstance(item, dict):
            continue

        text = str(item.get("text", ""))
        desc = str(item.get("desc", ""))

        combined_text = text + " " + desc

        # 抓准确超Like：超LIKE 14437人
        if result["超Like人数"] == "":
            match = re.search(r"超LIKE\s*([0-9,]+)人", combined_text, re.IGNORECASE)
            if match:
                result["超Like人数"] = int(match.group(1).replace(",", ""))

        # 抓今日签到：今日签到10万人 / 今日签到3.6万人 / 今日签到301人
        if result["今日签到人数"] == "":
            match = re.search(r"今日签到\s*([0-9.]+万?)人", combined_text)
            if match:
                raw_value = match.group(1)
                result["今日签到人数_原始"] = raw_value
                result["今日签到人数"] = parse_chinese_number(raw_value)

    return result


def extract_chaolike_count(data, topic_name=""):
    """
    从 cardlist 兜底提取：
    超LIKE(6432人)
    超LIKE(1.4万人) -> 14000+
    """
    possible_descs = []

    for item in walk(data):
        if not isinstance(item, dict):
            continue

        itemid = str(item.get("itemid", ""))
        desc = str(item.get("desc", ""))
        title = str(item.get("title", ""))

        if "chaolike" in itemid.lower() or "超LIKE" in desc or "超Like" in desc or "超LIKE" in title:
            possible_descs.append({
                "itemid": itemid,
                "title": title,
                "desc": desc,
            })

        if itemid == "badge_chaolike":
            match = re.search(r"超LIKE\(([0-9.]+万?)人\)", desc, re.IGNORECASE)

            if match:
                raw_value = match.group(1)
                return parse_chaolike_display(raw_value)

            match = re.search(r"\(([0-9.]+万?)人\)", desc)

            if match:
                raw_value = match.group(1)
                return parse_chaolike_display(raw_value)

            print(topic_name, "找到 badge_chaolike，但 desc 没匹配到数字：", desc)
            return ""

    print(topic_name, "没找到 badge_chaolike。相关字段如下：")
    for x in possible_descs[:20]:
        print(x)

    return ""


# =========================
# 10. 单个超话抓取
# =========================

def fetch_one_topic(topic, crawl_time):
    name = topic["name"]

    print(f"正在处理：{name}")

    # 1. 原来的接口：日新帖等
    try:
        detail_json = fetch_topic_detail(topic)
        row = extract_detail_data(topic, detail_json, crawl_time)
    except Exception as e:
        row = empty_row(name, crawl_time, f"日新帖接口失败：{e}")

    # 2. 主页面接口：准确超Like + 今日签到
    timeline_extra = {
        "超Like人数": "",
        "今日签到人数_原始": "",
        "今日签到人数": "",
    }

    try:
        timeline_json = fetch_timeline_topicpage(topic)
        timeline_extra = extract_timeline_extra_data(timeline_json)
    except Exception as e:
        print(name, "主页面数据抓取失败：", e)

    chaolike_count = timeline_extra.get("超Like人数", "")

    # 3. 如果主页面没抓到超Like，用 cardlist 兜底
    if chaolike_count == "":
        try:
            cardlist_json = fetch_cardlist(topic)
            chaolike_count = extract_chaolike_count(cardlist_json, name)
        except Exception as e:
            print(name, "cardlist超Like抓取失败：", e)

    row["超Like人数"] = chaolike_count
    row["今日签到人数_原始"] = timeline_extra.get("今日签到人数_原始", "")
    row["今日签到人数"] = timeline_extra.get("今日签到人数", "")

    print(
        name,
        "日新帖 =", row.get("日新帖"),
        "今日签到 =", row.get("今日签到人数"),
        "超Like =", row.get("超Like人数"),
    )

    return row


# =========================
# 11. 主程序
# =========================

def main():
    china_tz = timezone(timedelta(hours=8))
    crawl_time = datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")

    rows = []

    for topic in TOPICS:
        row = fetch_one_topic(topic, crawl_time)
        rows.append(row)
        time.sleep(0.6)

    # 按日新帖从高到低排序
    valid_rows = [row for row in rows if to_sort_number(row.get(SORT_FIELD)) >= 0]
    invalid_rows = [row for row in rows if to_sort_number(row.get(SORT_FIELD)) < 0]

    # 按超Like人数从高到低排序
    def to_number(value):
        if value is None or value == "":
            return None

        value = str(value).replace(",", "").replace("+", "").strip()

        try:
            return float(value)
        except ValueError:
            return None
    valid_rows.sort(
        key=lambda x: to_number(x["超Like人数"]),
        reverse=True
    )

    for i, row in enumerate(valid_rows):
        row["排名"] = i + 1

        if i == 0:
            row["距离上一名"] = ""
        else:
            prev_value = to_number(valid_rows[i - 1]["超Like人数"])
            curr_value = to_number(row["超Like人数"])

            if prev_value is not None and curr_value is not None:
                row["距离上一名"] = int(prev_value - curr_value)
            else:
                row["距离上一名"] = ""

    final_rows = valid_rows + invalid_rows

    # 失败保护：如果微博返回全空，说明 token/接口大概率失效。
    # 此时直接报错，不覆盖旧 CSV，Streamlit 还能继续展示上一次成功数据。
    has_valid_data = any(
        to_sort_number(row.get("超Like人数")) >= 0
        or to_sort_number(row.get("日新帖")) >= 0
        or to_sort_number(row.get("今日签到人数")) >= 0
        for row in final_rows
    )

    if not has_valid_data:
        raise ValueError("微博数据全空，可能 token 已过期；本次停止写入，保留旧 CSV。")

    # 给 Streamlit 简化展示用的别名列
    for row in final_rows:
        row["艺人姓名"] = row.get("超话名称", "")
        row["今日签到"] = row.get("今日签到人数", "")
        row["超Like"] = row.get("超Like人数", "")

    # 防止 Numbers / Excel 吃掉 12000+ 的 +
    for row in final_rows:
        row["超Like人数"] = force_text_for_csv(row.get("超Like人数", ""))
        row["超Like"] = force_text_for_csv(row.get("超Like", ""))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(final_rows)

    print("\n抓取完成，已导出：")
    print(OUTPUT_FILE)

    print("\n最终结果：")
    for row in final_rows:
        print(row)


if __name__ == "__main__":
    main()

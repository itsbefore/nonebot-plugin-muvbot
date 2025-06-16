import re
import asyncio
import json
from typing import List
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment, Message
from nonebot.plugin import PluginMetadata
from instacapture import InstaStory, InstaPost
import datetime
from datetime import UTC
from .config import instagram_cookie,allow_group

__plugin_meta__ = PluginMetadata(
    name="Instagram媒体抓取",
    description="可以下载Instagram的post/story/reel图片视频资源",
    usage="发送post/reel链接，会抓取并下载\n发送:快拍 <用户名>，会下载该用户所有快拍",
)

# Instagram 链接正则
ins_post_pattern = re.compile(r"https?://(www\.)?instagram\.com/(p|reel|reels|tv)/[\w-]+/?")

# 下载快拍
def insDownStory(username):
    cookies = instagram_cookie
    story_obj = InstaStory()
    story_obj.cookies = cookies

    story_obj.username = username
    rtn = story_obj.story_download()
    if rtn == {}:
        print("No stories found.")
        return None

    print('./story/'+story_obj.username+'/story-main.json')

    file_path = './story/'+story_obj.username+'/story-main.json'

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    stories_info = []
    for item in data.get('items', []):
        story_info = {}
        
        # 提取发布时间
        taken_at = item.get('taken_at')
        if taken_at:
            story_info['publish_time'] = datetime.datetime.fromtimestamp(taken_at).strftime('%Y-%m-%d %H:%M:%S')
        
        # 判断是否是转发的story并获取原作者
        reshared_author = item.get('reshared_story_media_author')
        is_reshare = reshared_author is not None

        reshared_from =[]
        # 如果是转发的story，先添加原作者
        if is_reshare and isinstance(reshared_author, dict):
            reshared_username = reshared_author.get('username')
            if reshared_username:
                reshared_from.append(f"{reshared_username}")
        story_info['reshared_from'] = reshared_from

        mentioned_people = []
        # 提取标记的人名
        stickers = item.get('story_bloks_stickers') or []
        for sticker in stickers:
            sticker_data = sticker.get('bloks_sticker', {}).get('sticker_data', {})
            if 'ig_mention' in sticker_data:
                mention = sticker_data['ig_mention']
                full_name = mention.get('full_name', '')
                username = mention.get('username', '')
                if full_name or username:
                    mentioned_people.append(f"{username}")
        story_info['mentioned_people'] = mentioned_people
        
        # 提取最高分辨率的媒体URL
        media_url = None
        if item.get('media_type') == 1:  # 图片
            candidates = item.get('image_versions2', {}).get('candidates', [])
            if candidates:
                # 按分辨率排序，取最大的
                candidates.sort(key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                media_url = candidates[0].get('url')
        elif item.get('media_type') == 2:  # 视频
            video_versions = item.get('video_versions', [])
            if video_versions:
                # 按类型排序，取最高质量的
                video_versions.sort(key=lambda x: x.get('type', 0), reverse=True)
                media_url = video_versions[0].get('url')
        story_info['media_url'] = media_url
        
        # 提取无障碍标题
        story_info['accessibility_caption'] = item.get('accessibility_caption') if item.get('accessibility_caption') else ''
        
        stories_info.append(story_info)
    return stories_info

# 下载帖子
def InsDownPost(url):
    post_obj = InstaPost()
    post_obj.reel_id = url
    post_obj.media_download()

    postjson = './post/'+post_obj.username+'/'+post_obj.reel_id+'-main.json'
    print(postjson)
    try:
        with open(postjson, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print("文件不存在")
        return None,None
    # 提取用户名
    username = data["owner"]["username"]

    # 生成帖子 URL
    post_url = f"https://www.instagram.com/p/{data['shortcode']}/"

    # 提取描述（description）
    try:
        description = data.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "")
    except:
        description = ''
    # 转换发布时间（时间戳转换为标准格式）
    timestamp = data.get("taken_at_timestamp", 0)
    post_time = (datetime.datetime.fromtimestamp(timestamp, UTC) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S BJT")

    # 头像本地存储路径（按照你的格式）
    profile_pic_path = f"./post/{username}/profile/profile.png"

    # 提取所有媒体数据
    media_data = []
    if "edge_sidecar_to_children" in data:  # 处理多个图片或视频
        for item in data["edge_sidecar_to_children"]["edges"]:
            node = item["node"]
            media_id = node["id"]
            
            if node.get("is_video", False):
                # 选择最高分辨率的视频 URL
                media_link = node.get("video_url", "")
            else:
                # 选择最大尺寸的图片 URL
                media_resources = node.get("display_resources", [])
                media_link = max(media_resources, key=lambda img: img.get("config_width", 0))["src"]

            # 提取 @Tag（如果存在）
            tagged_users = node.get("edge_media_to_tagged_user", {}).get("edges", [])
            tag = tagged_users[0]["node"]["user"]["username"] if tagged_users else ""

            media_data.append({"Tag": tag, "Link": media_link})
    else:  # 只有单个图片或视频
        media_id = data["id"]
        
        if data.get("is_video", False):
            media_link = data.get("video_url", "")
        else:
            media_resources = data.get("display_resources", [])
            media_link = max(media_resources, key=lambda img: img.get("config_width", 0))["src"]

        media_data.append({"Tag": "", "Link": media_link})

    # 组装 JSON 结构
    formatted_result = {
        username: {
            "url": post_url,
            "description": description,
            "profile pic": profile_pic_path,
            "Time": post_time,
            "Media Data": media_data
        }
    }
    # data = parse_ins_post_json(postjson)
    # print(data)

    # 提取 description
    username = list(formatted_result.keys())[0]  # 获取用户名，如 'loverrukk'
    desc = formatted_result[username]["description"]
    Ti = formatted_result[username]["Time"]
    media_files = [item["Link"] for item in formatted_result[username]["Media Data"]]
    descinfo = f"😻哞哞识别：instagram\n🌟来自 {username} 的帖子\n⏰发布时间：{Ti}\n📝发布内容：{desc}"
    return descinfo, media_files


# 注册消息监听器
igdownload = on_message(priority=5, block=False)

@igdownload.handle()
async def handle_ins(event: Event, bot: Bot):
    message = str(event.get_message())
    session_id = event.get_session_id()

    if "group" in session_id:
        group_id = session_id.split("_")[-1]
        if "all" not in allow_group and group_id not in allow_group:
            return

    if ins_post_pattern.search(message):
        # 下载内容
        desc, media_files = InsDownPost(message)
        
        if desc is None:
            await igdownload.finish("未找到帖子")
            return
        
        # 回复描述信息
        await igdownload.send(desc)
        # await asyncio.sleep(1)

        # 逐个发送媒体文件
        for url in media_files:
            try:
                clean_url = url.split("?")[0]
                if clean_url.lower().endswith(".mp4"):
                    # segment = MessageSegment.video(url)
                    msg = Message(MessageSegment.video(url))
                else:
                    # segment = MessageSegment.image(url)
                    msg = Message(MessageSegment.image(url))
                await bot.send(event=event, message=msg)

                await asyncio.sleep(1)
            except Exception as e:
                await igdownload.send(f"⚠️ 媒体发送失败: {e}")
        return

     # Story 快拍：匹配 “快拍 username”
    if message.startswith("快拍 "):
        username = message[3:].strip()
        if not username:
            await igdownload.send("请提供 Instagram 用户名，如：快拍 loverrukk")
            return

        # await igdownload.send(f"🐮正在获取 {username} 的 Story...")

        stories = insDownStory(username)
        if stories is None:
            await igdownload.send("未找到快拍内容")
            return

        for i, story in enumerate(stories, 1):
            # 打印快拍信息
            time_info = story.get('publish_time')
            reshared_from = story.get('reshared_from')
            mentioned_people = story.get('mentioned_people')
            media_url = story.get('media_url')
            accessibility_caption = story.get('accessibility_caption')

            desc_info = (
                f"😻哞哞识别：InstagramStory\n"
                f"🌟来自{username}的Story {i}\n"
                f"⏰ 发布时间: {time_info}\n"
            )

            print(f"Story {i}:")
            print(f"发布时间: {time_info}")
            if reshared_from !=[]:
                print(f"🔁转发自 {', '.join(reshared_from)}")
                desc_info += f"🔁转发自 {', '.join(reshared_from)}\n"
            else:
                print(f"👤提到的人: {', '.join(mentioned_people)}")
                desc_info += f"👤提到的人: {', '.join(mentioned_people)}\n"
            print(f"最高分辨率媒体URL: {media_url}")
            if accessibility_caption != '':
                print(f"💬无障碍标题: {accessibility_caption}")
                desc_info += f"💬无障碍标题: {accessibility_caption}\n"
            print("-" * 50)
            
            # 发送文字
            await igdownload.send(desc_info)
            # await asyncio.sleep(1)

            # 发送媒体
            if media_url:
                try:
                    clean_url = media_url.split("?")[0]
                    if clean_url.lower().endswith(".mp4"):
                        # segment = MessageSegment.video(url)
                        msg = Message(MessageSegment.video(media_url))
                    else:
                        # segment = MessageSegment.image(url)
                        msg = Message(MessageSegment.image(media_url))
                    await bot.send(event=event, message=msg)
                    await asyncio.sleep(1)
                except Exception as e:
                    await igdownload.send(f"⚠️ 快拍媒体发送失败: {e}")
        return
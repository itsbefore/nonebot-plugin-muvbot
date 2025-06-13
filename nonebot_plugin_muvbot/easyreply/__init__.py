from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="easyreply",
    description="关键词自动回复",
    usage="设置好关键词回复字典,当收到关键字时会自动回复",
)

# 自定义关键词自动回复字典
replies = {
    "哞了个哞": "哞哞哞~ 安装链接奉上：https://chromewebstore.google.com/detail/memcggjeojecdnjohlmaoadlgighehda?utm_source=item-share-cb",
    "早上好": "早上好！今天也要元气满满喵～",
    "你好": "你好哇！(｡･∀･)ﾉﾞ"
}


from nonebot import on_message
from nonebot.adapters import Event

mlgm = on_message(priority=5, block=True)

@mlgm.handle()
async def handle_function(event: Event):
    text = str(event.get_message())
    if text in replies:
        await mlgm.finish(replies[text])

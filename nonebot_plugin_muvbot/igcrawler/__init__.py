from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="igCrawler",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

# 还没写

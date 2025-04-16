from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import PersonNormalMessageReceived, GroupNormalMessageReceived
from pkg.platform.types.message import Image
import httpx
import re
import asyncio
import os
import uuid
from io import BytesIO
from .config import config
from .draw import SeparateMsg, draw_pic


USER_SPLIT = re.escape(config.user_split)  
NICK_START = re.escape(config.nick_start)
NICK_END = re.escape(config.nick_end)
MSG_SPLIT = config.message_split

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


class MsgInfo:
    def __init__(self, text: str, images: list[BytesIO]):
        self.text = text
        self.images = images

class User:
    def __init__(self, user_id: str, nick_name: str, is_robot: bool, messages: list[MsgInfo]):
        self.user_id = user_id
        self.nick_name = nick_name
        self.is_robot = is_robot
        self.messages = messages


@register(name="伪造聊天记录", description="伪造聊天记录生成器，伪造QQ聊天记录截图，请不要用于非法用途，否则后果自负。", version="0.1", author="小馄饨")
class FakePicPlugin(BasePlugin):
    
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.temp_files = []
    
    async def initialize(self):
        pass
    
    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        text = ctx.event.text_message
        if text.startswith("/伪造"):
            await self.handle_fakepic_command(ctx)
    
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        text = ctx.event.text_message
        if text.startswith("/伪造"):
            await self.handle_fakepic_command(ctx)
    
    async def get_user_name(self, user_id: str) -> str:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"https://api.leafone.cn/api/qqnick?qq={user_id}")
                data = res.json()
                nick = data.get("data", {}).get("nickname", "QQ用户")
                return nick
        except Exception:
            return "QQ用户"
    
    async def handle_message(self, message: str) -> MsgInfo:
        return MsgInfo(message, [])
    
    async def trans_to_list(self, msg: str) -> list[User]:
        try:
            s = USER_SPLIT + msg
            pattern = rf'{USER_SPLIT}(\d{{5,10}})({NICK_START}.*?{NICK_END})?说'
            
            matches = re.findall(pattern, s)
            if not matches:
                return []
                
            parts = re.split(pattern, s)
            
            users: list[User] = []
            for i in range(1, len(parts), 3):
                if i // 3 < len(matches):
                    user_id, nick_name = matches[i // 3]
                    user_id = user_id
                    messages = parts[i + 2].split(MSG_SPLIT)
                    
                    messages = [await self.handle_message(msg) for msg in messages if msg]
                    is_robot = True if user_id.startswith("3889") else False
                    
                    if nick_name:
                        nick_name = nick_name[1:-1]
                    else:
                        nick_name = await self.get_user_name(user_id)
                    
                    users.append(User(user_id, nick_name, is_robot, messages))
            
            return users
        except Exception:
            return []
    
    def save_image_to_temp(self, image_bytes: BytesIO) -> str:
        try:
            filename = f"fakepic_{uuid.uuid4().hex}.png"
            filepath = os.path.join(TEMP_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_bytes.getvalue())
            
            self.temp_files.append(filepath)
            return filepath
        except Exception:
            return ""
    
    async def handle_fakepic_command(self, ctx: EventContext):
        try:
            command_content = ctx.event.text_message[3:].strip()
            
            if not command_content:
                ctx.add_return("reply", ["请输入伪造内容，格式如：QQ号【昵称】说内容 + QQ号【昵称】说内容"])
                ctx.prevent_default()
                return
            
            users = await self.trans_to_list(command_content)
            
            if not users:
                ctx.add_return("reply", ["解析失败，请确认格式是否正确"])
                ctx.prevent_default()
                return
            
            sep_list: list[SeparateMsg] = []
            users_info: dict[str, dict] = {}
            
            for user in users:
                user_id = user.user_id
                if user_id not in users_info:
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100")
                            if resp.status_code == 200:
                                head_image = BytesIO(resp.content)
                                users_info[user_id] = {"head": head_image, "nick_name": user.nick_name}
                            else:
                                default_image = open("plugins/fakepic_plugin/resources/level_icon.png", "rb").read()
                                head_image = BytesIO(default_image)
                                users_info[user_id] = {"head": head_image, "nick_name": user.nick_name}
                    except Exception:
                        default_image = open("plugins/fakepic_plugin/resources/level_icon.png", "rb").read()
                        head_image = BytesIO(default_image)
                        users_info[user_id] = {"head": head_image, "nick_name": user.nick_name}
                else:
                    head_image = users_info[user_id]['head']
                
                for m in user.messages:
                    sep_list.append(SeparateMsg(head_image, user.nick_name, user.is_robot, m.text, m.images))
            
            pic_bytes = await asyncio.to_thread(draw_pic, sep_list)
            
            try:
                image_path = self.save_image_to_temp(pic_bytes)
                if image_path:
                    image = Image(path=image_path)
                    ctx.add_return("reply", [image])
                else:
                    raise Exception("保存图片失败")
            except Exception:
                ctx.add_return("reply", ["生成图片失败，请稍后再试"])
            
            ctx.prevent_default()
            
        except Exception:
            ctx.add_return("reply", ["生成伪造聊天记录失败，请检查格式是否正确"])
            ctx.prevent_default() 
            
    def __del__(self):
        for filepath in self.temp_files:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass

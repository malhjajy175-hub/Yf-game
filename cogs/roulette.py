"""
لعبة الروليت الجماعية — YF Games
=================================
ملف كبير لأن اللعبة معقدة (متجر + حقيبة + أدوار + 9 خصائص هجومية/دفاعية).
كل قسم معلّق بالعربية لتسهيل طلب التعديلات لاحقاً.

ملخص الخصائص:
- نيزك   (فعّالة): يقصي 2 لاعبين عشوائيين (المضاد يحميهم منه تحديداً)
- طبيب   (فعّالة): يرجّع كل اللاعبين المقصيين دفعة وحدة (إنعاش جماعي)
- قنص    (فعّالة): يفتح خيار "طرد معين" باختيار لاعب بالاسم
- انعاش  (فعّالة): يرجّع لاعباً واحداً تم إقصاؤه من قبل
- منع    (فعّالة): يمنع لاعباً من استخدام أي خاصية في دوره الجاي
- قنبلة  (فعّالة): يقصي لاعباً معيناً + لاعب عشوائي إضافي (حماية فقط تحميه)
- حماية  (دفاعية): تلغي أي محاولة إقصاء تلقائياً (تخدم مع الكل)
- مرتدة  (دفاعية): تفشّل القنص تحديداً فقط (ماتأثرش على قنبلة/عشوائي/نيزك)
- مضاد   (دفاعية): يحمي تحديداً من "نيزك"
"""

import asyncio
import random
import discord
from discord.ext import commands

from points import get_points, add_group_points, get_collection

# ============================================================
# إعدادات عامة
# ============================================================

MIN_PLAYERS = 4
MAX_PLAYERS = 60
LOBBY_SECONDS = 30
TURN_SECONDS = 15
METEOR_VICTIMS = 2  # كم لاعب يقصي "نيزك" في الضربة الواحدة
CONFIRM_DISMISS_SECONDS = 5  # مدة اختفاء رسائل التأكيد التلقائي (دخول/خروج/تنبيه المتجر)
CURRENCY = "نقطة"  # الصورة النهائية مافيهاش "UF"، رجعنا لتسمية النقاط العادية
SHOP_IMAGE_PATH = "assets/yf_shop.jpg"  # صورة المتجر التصميمية (خاصها تكون فنفس المجلد ديال البوت)

# الترقيم والأسعار مطابقين بالضبط للأرقام اللي بانت فالصورة النهائية (YF Games) — بالترتيب 1-9
ITEMS = {
    "doctor":  {"number": 1, "name": "طبيب",   "price": 1,   "emoji": "💉", "type": "active"},
    "snipe":   {"number": 2, "name": "قنص",    "price": 20,  "emoji": "🎯", "type": "active"},
    "meteor":  {"number": 3, "name": "نيزك",   "price": 100, "emoji": "☄️", "type": "active"},
    "revive":  {"number": 4, "name": "انعاش",  "price": 20,  "emoji": "💫", "type": "active"},
    "block":   {"number": 5, "name": "منع",    "price": 10,  "emoji": "🚫", "type": "active"},
    "bomb":    {"number": 6, "name": "قنبلة",  "price": 50,  "emoji": "💣", "type": "active"},
    "shield":  {"number": 7, "name": "حماية",  "price": 15,  "emoji": "🛡️", "type": "defense"},
    "reflect": {"number": 8, "name": "مرتدة",  "price": 25,  "emoji": "🔄", "type": "defense"},
    "immune":  {"number": 9, "name": "مضاد",   "price": 30,  "emoji": "☣️", "type": "defense"},
}
ACTIVE_ITEMS = [k for k, v in ITEMS.items() if v["type"] == "active"]
NUMBER_EMOJI = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

active_games: dict[int, "GameState"] = {}


async def spend_points(user_id: int, amount: int) -> bool:
    """يخصم نقاط (solo أولاً ثم group). يرجع False إذا الرصيد ما كافيش."""
    pts = await get_points(user_id)
    total = pts["solo"] + pts["group"]
    if total < amount:
        return False
    coll = get_collection()
    if pts["solo"] >= amount:
        await coll.update_one({"user_id": user_id}, {"$inc": {"solo": -amount}}, upsert=True)
    else:
        remaining = amount - pts["solo"]
        await coll.update_one(
            {"user_id": user_id},
            {"$set": {"solo": 0}, "$inc": {"group": -remaining}},
            upsert=True,
        )
    return True


async def refund_points(user_id: int, amount: int):
    coll = get_collection()
    await coll.update_one({"user_id": user_id}, {"$inc": {"solo": amount}}, upsert=True)


async def send_temp(interaction: discord.Interaction, content: str, *, seconds: int = CONFIRM_DISMISS_SECONDS):
    """يرسل رسالة ephemeral وتختفي وحدها من غير ما يحتاج اللاعب يدوس Dismiss message."""
    await interaction.response.send_message(content, ephemeral=True)
    try:
        msg = await interaction.original_response()
        await msg.delete(delay=seconds)
    except discord.HTTPException:
        pass


# ============================================================
# حالة اللعبة
# ============================================================

class Player:
    def __init__(self, user: discord.Member):
        self.user = user
        self.alive = True
        self.inventory: dict[str, int] = {}
        self.blocked_next_turn = False

    def has(self, item_key: str) -> bool:
        return self.inventory.get(item_key, 0) > 0

    def use(self, item_key: str) -> bool:
        if self.has(item_key):
            self.inventory[item_key] -= 1
            return True
        return False

    def add(self, item_key: str, qty: int = 1):
        self.inventory[item_key] = self.inventory.get(item_key, 0) + qty

    def owned_active_items(self) -> list[str]:
        return [k for k in ACTIVE_ITEMS if self.has(k)]


class GameState:
    def __init__(self, channel: discord.abc.Messageable, host: discord.Member):
        self.channel = channel
        self.host = host
        self.phase = "lobby"  # lobby -> running -> ended
        self.players: dict[int, Player] = {}
        self.eliminated: list[int] = []
        self.lobby_message: discord.Message | None = None
        self.lobby_view: "LobbyView | None" = None

    def alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.alive]

    def get_player(self, user_id: int) -> Player | None:
        return self.players.get(user_id)


# ============================================================
# صالة الانتظار (اللوبي)
# ============================================================

class LobbyView(discord.ui.View):
    def __init__(self, game: GameState):
        super().__init__(timeout=LOBBY_SECONDS + 5)
        self.game = game

    def build_embed(self) -> discord.Embed:
        g = self.game
        embed = discord.Embed(
            title="🎡 روليت",
            description="آخر لاعب صامد يفوز — اضغط دخول للانضمام",
            color=0x145C42,
        )
        embed.add_field(name="اللاعبون", value=f"{len(g.players)} / {MAX_PLAYERS}")
        embed.add_field(name="الحد الأدنى", value=str(MIN_PLAYERS))
        return embed

    async def refresh(self):
        try:
            await self.game.lobby_message.edit(embed=self.build_embed(), view=self)
        except discord.HTTPException:
            pass

    async def lock(self):
        """يوقف الأزرار (يبقاو بادين لكن ماكيتضغطوش) بلا ما يختفيو من الرسالة."""
        for child in self.children:
            child.disabled = True
        try:
            await self.game.lobby_message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="دخول", emoji="✅", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        g = self.game
        if g.phase != "lobby":
            return await interaction.response.send_message("⚠️ اللعبة بدات أو انتهت.", ephemeral=True)
        if interaction.user.id in g.players:
            return await interaction.response.send_message("أنت داخل أصلاً!", ephemeral=True)
        if len(g.players) >= MAX_PLAYERS:
            return await interaction.response.send_message("⚠️ العدد الأقصى مكتمل.", ephemeral=True)
        g.players[interaction.user.id] = Player(interaction.user)
        await send_temp(interaction, "✅ دخلت اللعبة!")
        await self.refresh()

    @discord.ui.button(label="خروج", emoji="🚪", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        g = self.game
        if g.phase != "lobby":
            return await interaction.response.send_message("⚠️ اللعبة بدات أو انتهت.", ephemeral=True)
        if interaction.user.id not in g.players:
            return await interaction.response.send_message("ماأنتش داخل أصلاً.", ephemeral=True)
        p = g.players.pop(interaction.user.id)
        spent = sum(ITEMS[k]["price"] * v for k, v in p.inventory.items())
        if spent:
            await refund_points(interaction.user.id, spent)
        await send_temp(interaction, "🚪 خرجت، وترجعت نقاط مشترياتك.")
        await self.refresh()

    @discord.ui.button(label="المتجر", emoji="🛒", style=discord.ButtonStyle.secondary)
    async def shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        g = self.game
        if g.phase != "lobby":
            return await interaction.response.send_message("⚠️ المتجر مقفول.", ephemeral=True)
        if interaction.user.id not in g.players:
            return await send_temp(interaction, "خاصك تدخل اللعبة أولاً.")
        pts = await get_points(interaction.user.id)
        balance = pts["solo"] + pts["group"]
        embed = discord.Embed(color=0xC9A227)
        embed.set_image(url="attachment://yf_shop.jpg")
        embed.set_footer(text=f"رصيدك: {balance} {CURRENCY}")
        await interaction.response.send_message(
            embed=embed,
            file=discord.File(SHOP_IMAGE_PATH, filename="yf_shop.jpg"),
            view=ShopView(g, interaction.user.id),
            ephemeral=True,
        )

    @discord.ui.button(label="الحقيبة", emoji="🎒", style=discord.ButtonStyle.secondary)
    async def bag(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.game.get_player(interaction.user.id)
        if not p or all(v == 0 for v in p.inventory.values()):
            return await interaction.response.send_message("🎒 حقيبتك فارغة.", ephemeral=True)
        lines = [f"{ITEMS[k]['emoji']} {ITEMS[k]['name']}: {v}" for k, v in p.inventory.items() if v > 0]
        await interaction.response.send_message("🎒 **حقيبتك:**\n" + "\n".join(lines), ephemeral=True)

    async def on_timeout(self):
        if self.game.phase == "lobby":
            await start_round_phase(self.game)


class ShopView(discord.ui.View):
    """أزرار مرقّمة 1-9 بس (بلا نص) — كتبان تحت صورة المتجر، كل رقم كيداللعب على البطاقة المقابلة له."""
    def __init__(self, game: GameState, user_id: int):
        super().__init__(timeout=60)
        self.game = game
        self.user_id = user_id
        for key, data in sorted(ITEMS.items(), key=lambda kv: kv[1]["number"]):
            self.add_item(self._make_button(key, data))

    def _make_button(self, key: str, data: dict):
        n = data["number"]
        btn = discord.ui.Button(
            label=str(n),
            emoji=data["emoji"],
            style=discord.ButtonStyle.secondary,
            row=(n - 1) // 3,  # يرتب الأزرار 3×3 تحت الصورة بنفس ترتيب البطاقات
        )

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("هذا المتجر ماشي ليك.", ephemeral=True)
            if self.game.phase != "lobby":
                return await interaction.response.send_message("⚠️ المتجر مقفول.", ephemeral=True)
            ok = await spend_points(interaction.user.id, data["price"])
            if not ok:
                return await interaction.response.send_message(f"❌ رصيدك ما كافيش ({data['price']} {CURRENCY}).", ephemeral=True)
            self.game.players[interaction.user.id].add(key)
            await interaction.response.send_message(f"✅ شريت {data['emoji']} {data['name']}!", ephemeral=True)

        btn.callback = callback
        return btn


# ============================================================
# مرحلة الأدوار
# ============================================================

async def start_round_phase(g: GameState):
    if len(g.players) < MIN_PLAYERS:
        g.phase = "ended"
        await g.channel.send(f"⚠️ العدد ما وصلش للحد الأدنى ({MIN_PLAYERS})، اتلغات اللعبة وترجعت النقاط.")
        for p in g.players.values():
            spent = sum(ITEMS[k]["price"] * v for k, v in p.inventory.items())
            if spent:
                await refund_points(p.user.id, spent)
        if g.lobby_view:
            await g.lobby_view.lock()
        active_games.pop(g.channel.id, None)
        return

    g.phase = "running"
    if g.lobby_view:
        await g.lobby_view.lock()
    await g.channel.send(f"🔒 المتجر أقفل! بدات اللعبة بـ **{len(g.players)}** لاعب. حظ سعيد!")
    await play_round(g)


async def play_round(g: GameState):
    alive = g.alive_players()
    if len(alive) <= 1:
        return await end_game(g)

    actor = random.choice(alive)

    # استهلاك أثر "منع" إذا كان مفعّل على هاد اللاعب
    blocked = actor.blocked_next_turn
    actor.blocked_next_turn = False

    view = TurnView(g, actor, blocked)
    note = "\n🚫 **ممنوع تستخدم أي خاصية هاد الجولة!**" if blocked else ""
    msg = await g.channel.send(
        f"🎲 دور <@{actor.user.id}> — عندك {TURN_SECONDS} ثانية باش تختار!{note}",
        view=view,
    )
    view.message = msg


class TurnView(discord.ui.View):
    def __init__(self, game: GameState, actor: Player, blocked: bool):
        super().__init__(timeout=TURN_SECONDS)
        self.game = game
        self.actor = actor
        self.blocked = blocked
        self.message: discord.Message | None = None
        self.resolved = False

        if not blocked:
            for key in actor.owned_active_items():
                self.add_item(self._make_active_button(key))

    # ---------- أزرار الخصائص الفعّالة (ديناميكية حسب حقيبة اللاعب) ----------
    def _make_active_button(self, key: str):
        data = ITEMS[key]
        btn = discord.ui.Button(label=f"{data['name']} {data['emoji']}", style=discord.ButtonStyle.danger)

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.actor.user.id:
                return await interaction.response.send_message("ماشي دورك!", ephemeral=True)
            self.resolved = True
            self.stop()
            await self._dispatch(interaction, key)

        btn.callback = callback
        return btn

    async def _dispatch(self, interaction: discord.Interaction, key: str):
        g, actor = self.game, self.actor
        others = [p for p in g.alive_players() if p.user.id != actor.user.id]

        if key == "snipe":
            if not others:
                return await interaction.response.send_message("مافماش لاعبين آخرين.", ephemeral=True)
            actor.use("snipe")
            await interaction.response.send_message(
                "🎯 اختار الضحية:",
                view=PlayerSelectView(others, lambda t: resolve_targeted_kick(g, actor, t)),
                ephemeral=True,
            )

        elif key == "bomb":
            if not others:
                return await interaction.response.send_message("مافماش لاعبين آخرين.", ephemeral=True)
            actor.use("bomb")
            await interaction.response.send_message(
                "💣 اختار اللاعب اللي غادي تضرب عليه القنبلة:",
                view=PlayerSelectView(others, lambda t: resolve_bomb(g, actor, t)),
                ephemeral=True,
            )

        elif key == "doctor":
            if not g.eliminated:
                return await interaction.response.send_message("مافماش حد مقصي حالياً.", ephemeral=True)
            actor.use("doctor")
            await interaction.response.send_message("💉 الطبيب رجّع كل اللاعبين المقصيين!", ephemeral=True)
            await revive_all(g)

        elif key == "revive":
            if not g.eliminated:
                return await interaction.response.send_message("مافماش حد مقصي حالياً.", ephemeral=True)
            actor.use("revive")
            options = [g.players[uid] for uid in g.eliminated]
            await interaction.response.send_message(
                "💫 اختار اللاعب اللي بغيتي ترجعه:",
                view=PlayerSelectView(options, lambda t: revive_player(g, t)),
                ephemeral=True,
            )

        elif key == "block":
            if not others:
                return await interaction.response.send_message("مافماش لاعبين آخرين.", ephemeral=True)
            actor.use("block")
            await interaction.response.send_message(
                "🚫 اختار اللاعب اللي بغيتي تمنعو من الخصائص فدوره الجاي:",
                view=PlayerSelectView(others, lambda t: apply_block(g, t)),
                ephemeral=True,
            )

        elif key == "meteor":
            actor.use("meteor")
            await interaction.response.send_message("☄️ نيزك يهبط...", ephemeral=True)
            await resolve_meteor(g, actor)

    # ---------- طرد عشوائي / انسحاب (ثابتين دائماً) ----------
    @discord.ui.button(label="طرد عشوائي 🎲", style=discord.ButtonStyle.secondary, row=4)
    async def random_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.actor.user.id:
            return await interaction.response.send_message("ماشي دورك!", ephemeral=True)
        self.resolved = True
        self.stop()
        await interaction.response.defer()
        await resolve_random_kick(self.game, self.actor)

    @discord.ui.button(label="انسحاب 🚪", style=discord.ButtonStyle.secondary, row=4)
    async def withdraw(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.actor.user.id:
            return await interaction.response.send_message("ماشي دورك!", ephemeral=True)
        self.resolved = True
        self.stop()
        await interaction.response.defer()
        await eliminate(self.game, self.actor, reason=f"🚪 <@{self.actor.user.id}> انسحب من اللعبة طوعاً!")
        await continue_or_end(self.game)

    async def on_timeout(self):
        if self.resolved:
            return
        try:
            await self.message.edit(
                content=f"⏱️ <@{self.actor.user.id}> ماختارش فالوقت، طرد عشوائي تلقائي!", view=None
            )
        except discord.HTTPException:
            pass
        await resolve_random_kick(self.game, self.actor)


class PlayerSelectView(discord.ui.View):
    """قائمة اختيار لاعب — تُستخدم لكل الخصائص اللي محتاجة تحديد هدف."""
    def __init__(self, candidates: list[Player], on_pick):
        super().__init__(timeout=30)
        self.on_pick = on_pick
        options = [
            discord.SelectOption(label=p.user.display_name, value=str(p.user.id))
            for p in candidates[:25]
        ]
        select = discord.ui.Select(placeholder="اختار اللاعب", options=options)

        async def callback(interaction: discord.Interaction):
            target_id = int(select.values[0])
            await interaction.response.edit_message(content=f"✅ اخترت <@{target_id}>!", view=None)
            await self.on_pick(target_id)

        select.callback = callback
        self.add_item(select)


# ============================================================
# منطق تنفيذ الخصائص
# ============================================================

async def resolve_targeted_kick(g: GameState, actor: Player, target_id: int):
    """قنص: حماية تحمي عموماً، مرتدة تحمي خصيصاً من القنص (تفشل العملية بلا ما ترد على المهاجم)."""
    target = g.get_player(target_id)
    if target.has("shield"):
        target.use("shield")
        await g.channel.send(f"🛡️ <@{target.user.id}> استخدم **حماية** ونجا من الطرد!")
    elif target.has("reflect"):
        target.use("reflect")
        await g.channel.send(f"🔄 ❌ فشل القنص! <@{target.user.id}> عنده **مرتدة**.")
    else:
        await eliminate(g, target, reason=f"🎯 <@{actor.user.id}> طرد <@{target.user.id}>!")
    await continue_or_end(g)


async def resolve_bomb(g: GameState, actor: Player, target_id: int):
    """قنبلة: حماية فقط تحمي الهدف الرئيسي — مرتدة ماتأثرش عليها (تخدم غير مع القنص)."""
    target = g.get_player(target_id)
    if target.has("shield"):
        target.use("shield")
        await g.channel.send(f"🛡️ 💣 <@{target.user.id}> استخدم **حماية** ونجا من القنبلة!")
    else:
        await eliminate(g, target, reason=f"💣 <@{actor.user.id}> فجّر <@{target.user.id}>!")

    # لاعب إضافي عشوائي يتأثر بالانفجار (يحترم حماية فقط)
    splash_pool = [p for p in g.alive_players() if p.user.id not in (actor.user.id, target_id)]
    if splash_pool:
        splash = random.choice(splash_pool)
        if splash.has("shield"):
            splash.use("shield")
            await g.channel.send(f"🛡️ شظايا القنبلة وصلات لـ <@{splash.user.id}>، لكنه نجا بـ**حماية**!")
        else:
            await eliminate(g, splash, reason=f"💥 شظايا القنبلة قصت كمان <@{splash.user.id}>!")

    await continue_or_end(g)


async def resolve_random_kick(g: GameState, actor: Player):
    candidates = [p for p in g.alive_players() if p.user.id != actor.user.id]
    if not candidates:
        return await continue_or_end(g)
    victim = random.choice(candidates)
    if victim.has("shield"):
        victim.use("shield")
        await g.channel.send(f"🛡️ العجلة اختارت <@{victim.user.id}>، لكنه نجا بـ**حماية**!")
    else:
        await eliminate(g, victim, reason=f"🎲 العجلة دارت... تم إقصاء <@{victim.user.id}>!")
    await continue_or_end(g)


async def resolve_meteor(g: GameState, actor: Player):
    """نيزك: يقصي حتى METEOR_VICTIMS لاعبين. مضاد يحمي منه تحديداً، وحماية تحمي عموماً."""
    pool = [p for p in g.alive_players() if p.user.id != actor.user.id]
    random.shuffle(pool)
    hit = 0
    for victim in pool:
        if hit >= METEOR_VICTIMS:
            break
        if victim.has("immune"):
            victim.use("immune")
            await g.channel.send(f"☣️ <@{victim.user.id}> استخدم **مضاد** ونجا من النيزك!")
            continue
        if victim.has("shield"):
            victim.use("shield")
            await g.channel.send(f"🛡️ <@{victim.user.id}> استخدم **حماية** ونجا من النيزك!")
            continue
        await eliminate(g, victim, reason=f"☄️ النيزك اللي رماه <@{actor.user.id}> قصى <@{victim.user.id}>!")
        hit += 1
    await continue_or_end(g)


async def revive_all(g: GameState):
    revived_ids = list(g.eliminated)
    for uid in revived_ids:
        g.players[uid].alive = True
    g.eliminated.clear()
    if revived_ids:
        mentions = " ".join(f"<@{uid}>" for uid in revived_ids)
        await g.channel.send(f"💉 **الطبيب أنعش كل اللاعبين المقصيين!** رجعوا: {mentions}")
    await continue_or_end(g)


async def revive_player(g: GameState, target_id: int):
    target = g.get_player(target_id)
    target.alive = True
    g.eliminated.remove(target_id)
    await g.channel.send(f"💫 <@{target.user.id}> رجع للعبة من جديد!")
    await continue_or_end(g)


async def apply_block(g: GameState, target_id: int):
    target = g.get_player(target_id)
    target.blocked_next_turn = True
    await g.channel.send(f"🚫 <@{target.user.id}> ممنوع من استخدام الخصائص فدوره الجاي!")
    await continue_or_end(g)


async def eliminate(g: GameState, player: Player, reason: str):
    player.alive = False
    if player.user.id not in g.eliminated:
        g.eliminated.append(player.user.id)
    await g.channel.send(reason)


async def continue_or_end(g: GameState):
    await asyncio.sleep(1.5)
    if len(g.alive_players()) <= 1:
        await end_game(g)
    else:
        await play_round(g)


async def end_game(g: GameState):
    g.phase = "ended"
    survivors = g.alive_players()
    if survivors:
        winner = survivors[0]
        await add_group_points(winner.user.id, 1)
        await g.channel.send(f"🏆 الفايز هو <@{winner.user.id}>! (+1 نقطة)")
    else:
        await g.channel.send("🏁 اللعبة انتهت بلا فايز.")
    active_games.pop(g.channel.id, None)


# ============================================================
# الأمر الرئيسي
# ============================================================

class RouletteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="روليت")
    async def roulette(self, ctx: commands.Context):
        if ctx.channel.id in active_games:
            await ctx.send("⚠️ فيه لعبة روليت شغالة فهاد القناة أصلاً!")
            return

        game = GameState(ctx.channel, ctx.author)
        active_games[ctx.channel.id] = game

        view = LobbyView(game)
        game.lobby_view = view
        msg = await ctx.send(embed=view.build_embed(), view=view)
        game.lobby_message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(RouletteCog(bot))

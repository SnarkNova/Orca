import json
import random
import discord
import sqlite3
from discord.ext import commands

client = commands.Bot(command_prefix=".", intents=discord.Intents.all())
con = sqlite3.connect("database.db")
cursor = con.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user TEXT UNIQUE, money TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS inventory (user TEXT, item TEXT, count TEXT)")

rarityChance = {1: 0.75, 2: 0.1, 3: 0.05, 4: 0.01, 5: 0.005}
fishs = json.load(open("fish.json", "r", encoding="utf-8"))

PRIMARY = 0x303098
RED = 0xaa0000
GREEN = 0x00aa00

async def back(ctx):
    return await ctx.send(embed=discord.Embed(title="실패", description="아직 회원가입하지 않았습니다.\n`/회원가입`으로 회원가입부터 진행해주세요.", color=RED))

def fishing(rarity):
    filtered = [item for item in fishs if item["rarity"] == rarity]
    return random.choice(filtered)

def checkRegister(user):
    cursor.execute("SELECT * FROM users WHERE user = ?", (user,))
    result = cursor.fetchone()
    if result == None: return False
    else: return True

def addItem(user, item):
    cursor.execute("SELECT count FROM inventory WHERE user = ? AND item = ?", (user, item))
    result = cursor.fetchone()
    if not result == None:
        cursor.execute("UPDATE inventory SET count = ? WHERE user = ? AND item = ?", (int(result[0]) + 1, user, item))
        con.commit()
    else:
        cursor.execute("INSERT INTO inventory (user, item, count) VALUES (?, ?, ?)", (user, item, 1))
        con.commit()

def minItem(user, item):
    cursor.execute("SELECT count FROM inventory WHERE user = ? AND item = ?", (user, item))
    result = cursor.fetchone()
    if not result == None:
        if int(result[0]) <= 1:
            cursor.execute("DELETE FROM inventory WHERE user = ? AND item = ?", (user, item))
            con.commit()
        else:
            cursor.execute("UPDATE inventory SET count = ? WHERE user = ? AND item = ?", (int(result[0]) - 1, user, item))
            con.commit()
        return True
    else:
        return False

@client.event
async def on_ready():
    await client.tree.sync()

@client.hybrid_command(name="도움말", description="아직 개발중인 명령어에요.")
async def help(ctx):
    await ctx.send(embed=discord.Embed(title="도움말", description="회원가입, 회원탈퇴, 낚시, 도박, 판매, 인벤토리, 잔액, 랭킹", color=PRIMARY))

@client.hybrid_command(name="회원가입", description="오르카와의 첫걸음이에요.")
async def register(ctx):
    if checkRegister(ctx.author.id) == False:
        cursor.execute("INSERT INTO users (user, money) VALUES (?, ?)", (ctx.author.id, 0))
        con.commit()
        await ctx.send(embed=discord.Embed(title="회원가입", description="성공적으로 회원가입했어요!", color=GREEN))
    else:
        await ctx.send(embed=discord.Embed(title="회원가입", description="이미 회원가입한 유저에요.", color=RED))

@client.hybrid_command(name="회원탈퇴", description="오르카와 작별인사할때 써요.")
async def delete(ctx):
    if checkRegister(ctx.author.id) == False:
        await back(ctx)
    else:
        button1 = discord.ui.Button(label="회원탈퇴", style=discord.ButtonStyle.green)

        async def clicked1(interaction: discord.Interaction):
            cursor.execute("DELETE FROM users WHERE user = ?", (interaction.user.id,))
            cursor.execute("DELETE FROM inventory WHERE user = ?", (interaction.user.id,))
            con.commit()
            await interaction.response.send_message(embed=discord.Embed(title="회원탈퇴", description="성공적으로 회원탈퇴했어요!", color=GREEN))

        button1.callback = clicked1

        button2 = discord.ui.Button(label="취소", style=discord.ButtonStyle.red)

        async def clicked2(interaction: discord.Interaction):
            await interaction.response.send_message(embed=discord.Embed(title="회원탈퇴", description="회원탈퇴를 취소했어요.", color=RED))

        button2.callback = clicked2

        view = discord.ui.View()
        view.add_item(button1)
        view.add_item(button2)

        await ctx.send(embed=discord.Embed(title="회원탈퇴", description="회원탈퇴를 진행할까요?\n-# 경고! 이 작업은 되돌릴 수 없습니다.", color=RED), view=view)

@client.hybrid_command(name="낚시", description="낚시 게임을 시작해요.")
async def fish(ctx):
    if checkRegister(ctx.author.id):
        rarity = random.choices(list(rarityChance.keys()), weights=list(rarityChance.values()))[0]
        fish = fishing(rarity)
        embed = discord.Embed(title=fish["name"], description="**이/가 낚였어요!**", color=PRIMARY)
        embed.add_field(name="`1` 가격", value="```python\n{}원```".format(fish["cost"]))
        embed.add_field(name="`2` 희귀도", value=f"```python\n{rarity}등급```")
        await ctx.send(embed=embed)
        addItem(ctx.author.id, fish["name"])
    else:
        await back(ctx)

@client.hybrid_command(name="도박", description="일확천금의 기회를 노려봐요.")
@discord.app_commands.describe(액수="베팅할 액수")
async def gamble(ctx, 액수: int):
    cursor.execute("SELECT money FROM users WHERE user = ?", (ctx.author.id,))
    result = cursor.fetchone()
    if not result is None:
        nowMoney = int(result[0])
        betMoney = 액수

        if betMoney > nowMoney or betMoney <= 0:
            await ctx.send(embed=discord.Embed(title="도박", description=f"베팅할 수 없습니다. 베팅 금액은 올인과 하프 그리고 숫자만 지원합니다.\n-# 현재 잔액은 **{nowMoney}**원입니다.", color=RED))
            return

        if random.choice([True, False]):
            nowMoney += betMoney
            message = [f"`🎉` 축하합니다! **{betMoney * 2}**원을 얻었습니다.", GREEN]
        else:
            nowMoney -= betMoney
            message = [f"`💸` 아쉽습니다.. **{betMoney}**원을 잃었습니다.", RED]

        cursor.execute("UPDATE users SET money = ? WHERE user = ?", (nowMoney, ctx.author.id))
        con.commit()

        await ctx.send(embed=discord.Embed(title="도박", description=f"{message[0]}\n현재 잔액은 **{nowMoney}**원입니다.", color=message[1]))
    else:
        await back(ctx)

async def fishAutocomplete(interaction: discord.Interaction, current: str):
    cursor.execute("SELECT item FROM inventory WHERE user = ?", (interaction.user.id,))
    result = cursor.fetchall()
    return [discord.app_commands.Choice(name=fish[0], value=fish[0]) for fish in result if current.lower() in fish[0].lower()]

@client.hybrid_command(name="판매", description="보유한 물고기를 판매해요.")
@discord.app_commands.describe(물고기="판매할 물고기")
@discord.app_commands.autocomplete(물고기=fishAutocomplete)
async def sell(ctx, 물고기: str):
    cursor.execute("SELECT money FROM users WHERE user = ?", (ctx.author.id,))
    result = cursor.fetchone()
    fish = 물고기
    if not result == None:
        if fish == "모두":
            cursor.execute("SELECT item, count FROM inventory WHERE user = ?", (ctx.author.id,))
            inventory = cursor.fetchall()
            
            if inventory:
                total = 0
                for item, count in inventory:
                    cost = next((f["cost"] for f in fishs if f["name"] == item), None)
                    if cost:
                        total += cost * int(count)
                
                cursor.execute("UPDATE users SET money = ? WHERE user = ?", (int(result[0]) + total, ctx.author.id))
                cursor.execute("DELETE FROM inventory WHERE user = ?", (ctx.author.id,))
                con.commit()
                
                await ctx.send(embed=discord.Embed(title="판매", description=f"모든 물고기를 판매해서 **{total}**원을 얻었어요.\n-# 현재 잔액은 **{int(result[0]) + total}**원입니다.", color=GREEN))
            else:
                await ctx.send(embed=discord.Embed(title="판매", description="판매할 물고기가 없습니다.", color=RED))
        else:
            cost = next((item["cost"] for item in fishs if item["name"] == fish), None)
            if minItem(ctx.author.id, fish):
                cursor.execute("UPDATE users SET money = ? WHERE user = ?", (int(result[0]) + cost, ctx.author.id))
                con.commit()
                await ctx.send(embed=discord.Embed(title="판매", description=f"물고기를 판매해서 **{cost}**원을 얻었어요.\n-# 현재 잔액은 **{int(result[0]) + cost}**원입니다.", color=GREEN))
            else:
                await ctx.send(embed=discord.Embed(title="판매", description="물고기를 보유하고 있지 않아요.", color=RED))
    else:
        await back(ctx)

@client.hybrid_command(name="인벤토리", description="자신의 인벤토리를 확인해요.")
async def inventory(ctx):
    if checkRegister(ctx.author.id):
        cursor.execute("SELECT item, count FROM inventory WHERE user = ?", (ctx.author.id,))
        result = cursor.fetchall()

        if not result:
            await ctx.send(embed=discord.Embed(title="인벤토리", description="인벤토리가 비어있습니다.", color=RED))

        page = [result[i:i + 9] for i in range(0, len(result), 9)]
        totalPage = len(page)
        nowPage = 0

        def getEmbed(page):
            embed = discord.Embed(title=f"{nowPage + 1}/{totalPage}", color=PRIMARY)
            for item, count in page:
                embed.add_field(name=item, value=f"```python\n{count}개```", inline=True)
            return embed

        embed = getEmbed(page[nowPage])
        view = discord.ui.View()

        backButton = discord.ui.Button(label="이전", style=discord.ButtonStyle.primary, disabled=True)

        async def backCallback(interaction: discord.Interaction):
            nonlocal nowPage
            nowPage -= 1
            if nowPage == 0:
                backButton.disabled = True
            nextButton.disabled = False
            await interaction.response.edit_message(embed=getEmbed(page[nowPage]), view=view)

        backButton.callback = backCallback
        view.add_item(backButton)

        nextButton = discord.ui.Button(label="다음", style=discord.ButtonStyle.primary, disabled=(totalPage == 1))

        async def nextCallback(interaction: discord.Interaction):
            nonlocal nowPage
            nowPage += 1
            if nowPage == totalPage - 1:
                nextButton.disabled = True
            backButton.disabled = False
            await interaction.response.edit_message(embed=getEmbed(page[nowPage]), view=view)

        nextButton.callback = nextCallback
        view.add_item(nextButton)

        await ctx.send(embed=embed, view=view)
    else:
        await back(ctx)

@client.hybrid_command(name="잔액", description="자신의 잔액을 확인해요.")
async def balance(ctx):
    cursor.execute("SELECT money FROM users WHERE user = ?", (ctx.author.id,))
    result = cursor.fetchone()
    if not result == None:
        await ctx.send(embed=discord.Embed(title="잔액", description=f"현재 잔액은 **{result[0]}**원입니다.", color=discord.Color.gold()))
    else:
        await back(ctx)

@client.hybrid_command(name="랭킹", description="가장 돈이 많은 유저순으로 랭킹을 보여줘요.")
async def ranking(ctx):
    cursor.execute("SELECT user, money FROM users ORDER BY money DESC LIMIT 5")
    result = cursor.fetchall()

    icon = ["🥇", "🥈", "🥉"]

    embed = discord.Embed(title="랭킹", description="가장 돈이 많은 유저들입니다.", color=discord.Color.gold())
    for i, (user_id, money) in enumerate(result):
        user = await client.fetch_user(user_id)
        name = user.display_name if user else "Unknown User"
        icon = icon[i] if i < len(icon) else ""
        embed.add_field(name=f"{icon} {i + 1}위 **{name}**", value=f"```python\n{money}원```", inline=True)
    await ctx.send(embed=embed)

client.run("")
import discord
from discord.ext import tasks, commands
from fuzzywuzzy import fuzz
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', help_command=None, intents=intents)

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def get_tournaments():
    url = 'https://aicf.in/all-events/'
    async with aiohttp.ClientSession() as session:
        response = await fetch(session, url)
    soup = BeautifulSoup(response, 'html.parser')

    tournaments = []
    for row in soup.find_all('table')[0].tbody.find_all('tr')[1:]:
        name = row.find_all('td')[1].text
        start_date_str = row.find_all('td')[3].text.strip().replace('\n', '').replace('-', ' ')
        end_date_str = row.find_all('td')[4].text.strip().replace('\n', '').replace('-', ' ')

        if start_date_str == 'TBD':
            start_date = datetime.now()
        else:
            start_date = datetime.strptime(start_date_str, '%d %m %Y')

        if end_date_str == 'TBD':
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date_str, '%d %m %Y')

        city = row.find_all('td')[5].text
        brochure_link = row.find_all('td')[6].find('a')
        brochure = brochure_link.get('href') if brochure_link else None
        tournaments.append({
            'name': name,
            'start_date': start_date,
            'end_date': end_date,
            'city': city,
            'brochure': brochure,
        })
    return tournaments

def search_tournaments(tournaments, name=None, city=None, date=None, max_results=5):
    results = []
    today = datetime.today()
    for tournament in tournaments:
        if len(results) >= max_results:
            break
        if tournament['start_date'] < today:
            continue
        if name and fuzz.partial_ratio(name.lower(), tournament['name'].lower()) < 80:
            continue
        if city and fuzz.token_set_ratio(city.lower(), tournament['city'].lower()) < 80:
            continue
        if date and (date not in tournament['start_date'].strftime('%d-%m-%Y') and date not in tournament['end_date'].strftime('%d-%m-%Y')):
            continue
        results.append(tournament)
    return results

@bot.command()
async def search(ctx, *, query=None):
    if not query:
        await ctx.send("Please provide a search query.")
        return
    tournaments = await get_tournaments()
    results_name = search_tournaments(tournaments, name=query)
    results_city = search_tournaments(tournaments, city=query)
    results_date = search_tournaments(tournaments, date=query)
    results = results_name + results_city + results_date
    if not results:
        await ctx.send("No tournaments found.")
        return
    for tournament in results:
        await ctx.send(f"Tournament: {tournament['name']}\nDates: {tournament['start_date'].strftime('%d-%m-%Y')} to {tournament['end_date'].strftime('%d-%m-%Y')}\nCity: {tournament['city']}\nBrochure: {tournament['brochure'] or 'No brochure available'}")

@bot.command()
async def help(ctx):
    await ctx.send("Welcome to the Chess Tournament Bot!\nYou can use the following commands:\n!search [query]: Search for tournaments by name, city, or date. Just provide the query and the bot will do the rest.\n!help: Show this help message.")

# News update code
CHANNEL_ID = 1094334260833439805  # Replace with your channel ID
URL = 'https://chessbase.in/'
latest_article = None

@tasks.loop(minutes=60.0)
async def check_website():
    global latest_article
    channel = bot.get_channel(CHANNEL_ID)

    async with aiohttp.ClientSession() as session:
        response = await fetch(session, URL)

    soup = BeautifulSoup(response, 'html.parser')
    article = soup.find('article', class_='newsitem featured')

    if article is None:
        return

    article_url = 'https://chessbase.in' + article.h1.a['href']
    article_title = article.h1.a.text
    article_image = article.img['src']
    article_summary = article.p.text

    if article_url != latest_article:
        embed = discord.Embed(title=article_title, url=article_url, description=article_summary)
        embed.set_image(url=article_image)
        await channel.send("@everyone Chessbase India just posted an article:")
        await channel.send(embed=embed)
        latest_article = article_url

    print(f'Latest article URL: {latest_article}')

@check_website.before_loop
async def before_check_website():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f'Bot is ready! Running as: {bot.user}')
    check_website.start()

@bot.command()
async def introduce(ctx):
    await ctx.send("Hello! I'm Chess-Pa, your friendly chess assistant. I can help you find chess tournaments and keep you updated with the latest chess news. Use !help to see what I can do.")

TOKEN = "MTExNDE5MjUwNzIxMTg4NjYyMg.GQDxA-.C8hScY-d9HYvb1MgtE2JEPDzzYpe5AYOVKB9VM"
bot.run(TOKEN)

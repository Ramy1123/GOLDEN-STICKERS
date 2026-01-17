import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

"""
🤖 بوت الديسكورد - نظام التفاعل والتكتات
مطور بواسطة: رامي (@r82d)
"""

# تحميل متغيرات البيئة
load_dotenv()

# ========== إعدادات البوت ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

# ========== بيانات سيرفرك ==========
YOUR_SERVER_ID = 1142559110693408788

# الأونرز
OWNER_USERS = [
    1004455171906076782,  # أنت
    764090152544763904,   # زميلك الأول
    1114555074920857600   # زميلك الثاني
]

# أدوار المشرفين
ADMIN_ROLES = ["مشرف", "ادمن", "مدير", "Admin", "Moderator"]

# ========== ملفات البيانات ==========
DAILY_DATA_FILE = 'daily_data.json'
WEEKLY_DATA_FILE = 'weekly_data.json'
TICKET_DATA_FILE = 'ticket_data.json'

# ========== نظام الجلسات الذكي ==========
USER_SESSIONS = {}  # {user_id: {'start': datetime, 'last_msg': datetime, 'total': minutes}}
MAX_SESSION_GAP = 5  # إذا انقطع أكثر من 5 دقائق = جلسة جديدة
MAX_SESSION_TIME = 120  # أقصى وقت للجلسة الواحدة (دقيقتان)
MIN_MESSAGE_GAP = 0.5  # أقل فرق بين رسالتين لنحسبه (30 ثانية)

# ========== دوال البيانات ==========
def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def end_user_session(user_id):
    """إنهاء جلسة المستخدم وحفظ وقتها"""
    if user_id in USER_SESSIONS:
        session = USER_SESSIONS[user_id]
        session_duration = (session['last_msg'] - session['start']).total_seconds() / 60
        session_minutes = min(session_duration + 1, MAX_SESSION_TIME)  # +1 لأول رسالة
        
        del USER_SESSIONS[user_id]
        return session_minutes
    return 0

# ========== حدث تشغيل البوت ==========
@bot.event
async def on_ready():
    print('=' * 50)
    print(f'🤖 البوت: {bot.user.name}')
    print(f'🆔 ID البوت: {bot.user.id}')
    print('=' * 50)
    
    # التحقق من السيرفرات
    print('🏰 السيرفرات الموجودة:')
    for guild in bot.guilds:
        print(f'   • {guild.name} (ID: {guild.id})')
        print(f'     👥 الأعضاء: {guild.member_count}')
        print(f'     👑 أنا موجود: {guild.get_member(bot.user.id) is not None}')
    
    if not bot.guilds:
        print('⚠️  البوت غير موجود في أي سيرفر!')
        print('🔗 استخدم هذا الرابط لإضافة البوت:')
        client_id = bot.user.id
        print(f'https://discord.com/oauth2/authorize?client_id={client_id}&scope=bot+applications.commands&permissions=8')
    
    # مزامنة الأوامر لكل سيرفر
    print('=' * 50)
    print('🔄 جاري مزامنة الأوامر...')
    try:
        for guild in bot.guilds:
            try:
                guild_object = discord.Object(id=guild.id)
                tree.copy_global_to(guild=guild_object)
                await tree.sync(guild=guild_object)
                print(f'✅ تم مزامنة الأوامر لـ {guild.name}')
            except Exception as e:
                print(f'⚠️  خطأ في {guild.name}: {e}')
        
        # المزامنة العامة أيضاً
        synced = await tree.sync()
        print(f'✅ تم مزامنة إجمالي {len(synced)} أمر')
        for cmd in synced:
            print(f'   • /{cmd.name}')
    except Exception as e:
        print(f'❌ خطأ في المزامنة: {e}')
    
    # بدء المهام التلقائية
    daily_reset_check.start()
    
    print('=' * 50)
    print('📝 لاختبار الأوامر:')
    print('   1. انتظر 1-2 دقيقة')
    print('   2. اكتب / في أي روم')
    print('   3. إذا ما ظهرت الأوامر، أعد تشغيل Discord')
    print('=' * 50)
    
    # تغيير حالة البوت
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="التفاعل + التكتات 📊"
        )
    )

# ========== إعادة الضبط اليومي ==========
@tasks.loop(minutes=1)
async def daily_reset_check():
    """تتحقق كل دقيقة إذا حان وقت إعادة الضبط (12 صباحًا)"""
    now = datetime.now()
    if now.hour == 0 and now.minute == 0:
        await reset_daily_interaction()
        print(f"🔄 تم إعادة ضبط التفاعل اليومي: {date.today()}")

async def reset_daily_interaction():
    """إعادة ضبط التفاعل اليومي وحفظ الإحصائيات"""
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    
    # إنهاء جميع الجلسات النشطة وحفظ وقتها
    for user_id in list(USER_SESSIONS.keys()):
        session_minutes = end_user_session(user_id)
        if session_minutes > 0:
            daily_data = load_data(DAILY_DATA_FILE)
            current = daily_data.get(user_id, 0)
            daily_data[user_id] = current + session_minutes
            save_data(daily_data, DAILY_DATA_FILE)
    
    # تحميل البيانات
    daily_data = load_data(DAILY_DATA_FILE)
    weekly_data = load_data(WEEKLY_DATA_FILE)
    
    # تهيئة البيانات الأسبوعية
    if 'weekly_stats' not in weekly_data:
        weekly_data['weekly_stats'] = {}
    
    # حفظ بيانات الأمس
    active_users = 0
    total_minutes = 0
    
    for user_id, minutes in daily_data.items():
        if minutes > 0:
            active_users += 1
            total_minutes += minutes
            
            if user_id not in weekly_data['weekly_stats']:
                weekly_data['weekly_stats'][user_id] = []
            
            # تحويل الدقائق لساعات
            hours = minutes / 60
            
            weekly_data['weekly_stats'][user_id].append({
                'date': yesterday,
                'hours': round(hours, 2),
                'minutes': minutes,
                'sessions': len([m for m in [minutes] if m > 0])
            })
    
    # حفظ آخر 7 أيام فقط
    for user_id in weekly_data['weekly_stats']:
        weekly_data['weekly_stats'][user_id] = weekly_data['weekly_stats'][user_id][-7:]
    
    weekly_data['last_reset'] = today
    save_data(weekly_data, WEEKLY_DATA_FILE)
    
    # إرسال إشعار للسيرفر
    try:
        guild = bot.get_guild(YOUR_SERVER_ID)
        if guild:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    embed = discord.Embed(
                        title="🔄 إعادة ضبط التفاعل اليومي",
                        description=f"بدأ يوم جديد! تم حفظ إحصائيات أمس.",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="📅 تاريخ اليوم", value=today, inline=True)
                    embed.add_field(name="👥 النشطين أمس", value=f"{active_users} عضو", inline=True)
                    embed.add_field(name="⏱️ وقت التفاعل", value=f"{total_minutes} دقيقة", inline=True)
                    embed.set_footer(text="نظام الجلسات الذكي: يحسب وقت التفاعل الفعلي")
                    await channel.send(embed=embed)
                    break
    except Exception as e:
        print(f"⚠️  لم أتمكن من إرسال إشعار: {e}")
    
    # مسح بيانات اليوم
    save_data({}, DAILY_DATA_FILE)
    print(f"📊 تم حفظ بيانات {yesterday}: {active_users} عضو, {total_minutes} دقيقة")

# ========== حساب التفاعل عند كل رسالة ==========
@bot.event
async def on_message(message):
    # تجاهل رسائل البوتات
    if message.author.bot:
        return
    
    user_id = str(message.author.id)
    now = datetime.now()
    
    # ========== نظام الجلسات الذكي ==========
    time_to_add = 0
    
    if user_id in USER_SESSIONS:
        session = USER_SESSIONS[user_id]
        last_msg_time = session['last_msg']
        time_gap = (now - last_msg_time).total_seconds() / 60
        
        if time_gap > MAX_SESSION_GAP:
            # حساب وقت الجلسة السابقة
            session_duration = (last_msg_time - session['start']).total_seconds() / 60
            session_minutes = min(session_duration + 1, MAX_SESSION_TIME)
            
            # حفظ وقت الجلسة السابقة
            daily_data = load_data(DAILY_DATA_FILE)
            current = daily_data.get(user_id, 0)
            daily_data[user_id] = current + session_minutes
            save_data(daily_data, DAILY_DATA_FILE)
            
            print(f"📊 جلسة منتهية لـ {message.author.name}: {session_minutes:.1f} دقيقة")
            
            # بدء جلسة جديدة
            USER_SESSIONS[user_id] = {
                'start': now,
                'last_msg': now,
                'message_count': 1
            }
            time_to_add = 1
            
        else:
            if time_gap >= MIN_MESSAGE_GAP:
                time_to_add = min(time_gap, MAX_SESSION_GAP)
            else:
                time_to_add = 0
            
            session['last_msg'] = now
            session['message_count'] = session.get('message_count', 0) + 1
    else:
        # أول جلسة للمستخدم اليوم
        USER_SESSIONS[user_id] = {
            'start': now,
            'last_msg': now,
            'message_count': 1
        }
        time_to_add = 1
    
    # تحديث التفاعل اليومي
    if time_to_add > 0:
        daily_data = load_data(DAILY_DATA_FILE)
        current = daily_data.get(user_id, 0)
        daily_data[user_id] = current + time_to_add
        save_data(daily_data, DAILY_DATA_FILE)
    
    # السماح بتنفيذ الأوامر
    await bot.process_commands(message)

# ========== أوامر الاختبار والتحقق ==========
@tree.command(name="ping", description="اختبار استجابة البوت")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! البوت شغال!")

@tree.command(name="سيرفر", description="معلومات السيرفر")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title=f"معلومات {guild.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="🆔 ID", value=guild.id, inline=True)
    embed.add_field(name="👥 الأعضاء", value=guild.member_count, inline=True)
    embed.add_field(name="📅 تاريخ الإنشاء", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="👑 المالك", value=guild.owner.mention, inline=True)
    
    # تحقق من وجود البوت
    bot_member = guild.get_member(bot.user.id)
    if bot_member:
        embed.add_field(name="🤖 البوت", value="✅ متصل", inline=True)
    else:
        embed.add_field(name="🤖 البوت", value="❌ غير متصل", inline=True)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="sync", description="مزامنة الأوامر يدوياً (للأونرز فقط)")
async def sync_commands(interaction: discord.Interaction):
    if interaction.user.id not in OWNER_USERS:
        await interaction.response.send_message("❌ هذا الأمر للأونرز فقط!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        synced = await tree.sync()
        await interaction.followup.send(f"✅ تم مزامنة {len(synced)} أمر!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ خطأ: {e}", ephemeral=True)

# ========== الأوامر الرئيسية ==========
@tree.command(
    name="تفاعل",
    description="عرض تفاعل عضو معين لليوم",
)
@app_commands.describe(عضو="العضو الذي تريد عرض تفاعله (اختياري)")
async def تفاعل(interaction: discord.Interaction, عضو: discord.Member = None):
    if not عضو:
        عضو = interaction.user
    
    await interaction.response.defer()
    
    daily_data = load_data(DAILY_DATA_FILE)
    user_id = str(عضو.id)
    
    minutes_today = daily_data.get(user_id, 0)
    hours = minutes_today // 60
    remaining_minutes = minutes_today % 60
    
    embed = discord.Embed(
        title=f"📊 تفاعل اليوم - {عضو.display_name}",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    if عضو.avatar:
        embed.set_thumbnail(url=عضو.avatar.url)
    
    if minutes_today == 0:
        time_str = "**لم يتفاعل اليوم**"
    elif hours > 0:
        time_str = f"**{hours} ساعة و {remaining_minutes} دقيقة**"
    else:
        time_str = f"**{minutes_today} دقيقة**"
    
    embed.add_field(name="⏱️ الوقت النشط", value=time_str, inline=False)
    
    if minutes_today == 0:
        estimate = "🔴 غير متفاعل"
    elif minutes_today < 30:
        estimate = "🟡 متفاعل خفيف"
    elif minutes_today < 120:
        estimate = "🟢 متفاعل متوسط"
    elif minutes_today < 240:
        estimate = "🔵 متفاعل نشيط"
    else:
        estimate = "🟣 متفاعل مكثف ⭐"
    
    embed.add_field(name="التقدير", value=estimate, inline=False)
    embed.set_footer(text=f"طلب بواسطة {interaction.user.display_name}")
    
    await interaction.followup.send(embed=embed)

@tree.command(
    name="افضل_متفاعل",
    description="عرض أكثر الأعضاء تفاعلاً بالأسبوع",
)
async def افضل_متفاعل(interaction: discord.Interaction):
    await interaction.response.defer()
    
    weekly_data = load_data(WEEKLY_DATA_FILE)
    ticket_data = load_data(TICKET_DATA_FILE)
    
    if 'weekly_stats' not in weekly_data:
        embed = discord.Embed(
            title="🏆 أكثر الأعضاء تفاعلاً بالأسبوع",
            description="📭 لا توجد بيانات أسبوعية بعد",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # حساب التفاعل (مع استثناء الأونرز)
    user_stats = []
    for user_id, days in weekly_data['weekly_stats'].items():
        if int(user_id) in OWNER_USERS:
            continue
            
        total_minutes = sum(day.get('minutes', 0) for day in days)
        if total_minutes > 0:
            total_hours = total_minutes / 60
            
            tickets = 0
            if 'tickets' in ticket_data and user_id in ticket_data['tickets']:
                tickets = sum(ticket_data['tickets'][user_id].values())
            
            user_stats.append({
                'user_id': user_id,
                'hours': total_hours,
                'tickets': tickets
            })
    
    user_stats.sort(key=lambda x: x['hours'], reverse=True)
    
    if not user_stats:
        embed = discord.Embed(
            title="🏆 أكثر الأعضاء تفاعلاً بالأسبوع",
            description="📭 لا توجد بيانات كافية",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🏆 أفضل الأعضاء تفاعلاً بالأسبوع",
        description="ترتيب الأعضاء حسب وقت التفاعل",
        color=discord.Color.purple()
    )
    
    top_list = ""
    for i, user in enumerate(user_stats[:10], 1):
        user_id = user['user_id']
        
        try:
            member = await bot.fetch_user(int(user_id))
            mention = member.mention
        except:
            mention = f"مستخدم ({user_id[:8]}...)"
        
        hours = user['hours']
        tickets = user['tickets']
        
        top_list += f"**{i}. {mention}**\n"
        top_list += f"   ⏱️ **{hours:.1f} ساعة**"
        if tickets > 0:
            top_list += f" | 🎫 **{tickets} تكت**"
        top_list += "\n\n"
    
    embed.add_field(name="🏅 الترتيب", value=top_list, inline=False)
    
    # إحصائيات
    total_users = len(user_stats)
    total_hours = sum(user['hours'] for user in user_stats)
    
    if total_users > 0:
        avg_hours = total_hours / total_users
        stats_text = f"""
        **👥 عدد الأعضاء النشطين:** {total_users}
        **⏱️ إجمالي وقت التفاعل:** {total_hours:.1f} ساعة
        **📊 معدل التفاعل للعضو:** {avg_hours:.1f} ساعة
        """
        
        if user_stats:
            top_user = user_stats[0]
            try:
                top_member = await bot.fetch_user(int(top_user['user_id']))
                top_name = top_member.display_name
            except:
                top_name = f"مستخدم ({top_user['user_id'][:8]})"
            
            stats_text += f"\n\n**👑 الأعلى تفاعلاً:** {top_name}"
            stats_text += f"\n**⏱️ وقت التفاعل:** {top_user['hours']:.1f} ساعة"
        
        embed.add_field(name="📈 الإحصائيات", value=stats_text, inline=False)
    
    embed.set_footer(text=f"تاريخ اليوم: {date.today()} | فترة التتبع: 7 أيام")
    await interaction.followup.send(embed=embed)

# ========== أمر استلام_تكت المعدل (يدعم + و -) ==========
@tree.command(
    name="استلام_تكت",
    description="إضافة أو طرح تكتات لعضو (للأونرز فقط)",
)
@app_commands.describe(
    عضو="العضو المراد تعديل تكتاته",
    عدد="عدد التكتات (موجب للإضافة، سالب للطرح، -100 إلى 100)",
    السبب="سبب التعديل (اختياري)"
)
async def استلام_تكت(interaction: discord.Interaction, عضو: discord.Member, عدد: int, السبب: str = "لا يوجد"):
    if interaction.user.id not in OWNER_USERS:
        embed = discord.Embed(
            title="❌ غير مصرح",
            description="هذا الأمر للأونرز فقط!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if عدد == 0:
        await interaction.response.send_message("❌ العدد لا يمكن أن يكون صفراً!", ephemeral=True)
        return
    
    if عدد < -100 or عدد > 100:
        await interaction.response.send_message("❌ العدد يجب أن يكون بين -100 و 100", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    ticket_data = load_data(TICKET_DATA_FILE)
    
    if 'tickets' not in ticket_data:
        ticket_data['tickets'] = {}
    
    user_id = str(عضو.id)
    today = str(date.today())
    
    if user_id not in ticket_data['tickets']:
        ticket_data['tickets'][user_id] = {}
    
    if today not in ticket_data['tickets'][user_id]:
        ticket_data['tickets'][user_id][today] = 0
    
    # التحقق من عدم وجود سالب بعد الطرح
    new_value = ticket_data['tickets'][user_id][today] + عدد
    if new_value < 0:
        await interaction.followup.send("❌ لا يمكن أن يصبح عدد التكتات سالباً!")
        return
    
    ticket_data['tickets'][user_id][today] = new_value
    save_data(ticket_data, TICKET_DATA_FILE)
    
    # حساب الإجمالي بعد التعديل
    total_tickets = sum(ticket_data['tickets'][user_id].values())
    
    # إنشاء التقرير
    if عدد > 0:
        title = "🎫 تم إضافة تكتات"
        color = discord.Color.green()
        emoji = "➕"
        action = "إضافة"
    else:
        title = "🗑️ تم طرح تكتات"
        color = discord.Color.orange()
        emoji = "➖"
        action = "طرح"
    
    embed = discord.Embed(
        title=title,
        description=f"تم {action} تكتات لـ {عضو.display_name}",
        color=color
    )
    
    embed.add_field(name="👤 العضو", value=عضو.mention, inline=True)
    embed.add_field(name="📅 التاريخ", value=today, inline=True)
    embed.add_field(name="🎫 التعديل", value=f"{emoji} **{عدد}**", inline=True)
    
    embed.add_field(name="📊 تكتات اليوم", value=f"**{ticket_data['tickets'][user_id][today]}**", inline=True)
    embed.add_field(name="🏆 الإجمالي الكلي", value=f"**{total_tickets}**", inline=True)
    embed.add_field(name="📝 السبب", value=السبب, inline=True)
    
    embed.add_field(name="👤 تم التعديل بواسطة", value=interaction.user.mention, inline=False)
    
    embed.set_footer(text=f"تم التعديل: {datetime.now().strftime('%H:%M:%S')}")
    
    await interaction.followup.send(embed=embed)

# ========== أمر حذف_تكتات الجديد ==========
@tree.command(
    name="حذف_تكتات",
    description="حذف جميع تكتات عضو معين (للأونرز فقط)",
)
@app_commands.describe(
    عضو="العضو المراد حذف تكتاته",
    السبب="سبب الحذف (اختياري)"
)
async def حذف_تكتات(interaction: discord.Interaction, عضو: discord.Member, السبب: str = "لا يوجد"):
    if interaction.user.id not in OWNER_USERS:
        embed = discord.Embed(
            title="❌ غير مصرح",
            description="هذا الأمر للأونرز فقط!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # إنشاء زر تأكيد
    class ConfirmDeleteView(discord.ui.View):
        def __init__(self, عضو, السبب):
            super().__init__(timeout=60)
            self.عضو = عضو
            self.السبب = السبب
        
        @discord.ui.button(label="🗑️ تأكيد الحذف", style=discord.ButtonStyle.danger)
        async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id not in OWNER_USERS:
                await interaction.response.send_message("❌ ليس لديك صلاحية!", ephemeral=True)
                return
            
            ticket_data = load_data(TICKET_DATA_FILE)
            user_id = str(self.عضو.id)
            
            if 'tickets' in ticket_data and user_id in ticket_data['tickets']:
                # حفظ نسخة احتياطية قبل الحذف
                backup_data = ticket_data['tickets'][user_id].copy()
                deleted_count = sum(backup_data.values())
                
                # حذف التكتات
                del ticket_data['tickets'][user_id]
                save_data(ticket_data, TICKET_DATA_FILE)
                
                # إرسال رسالة التأكيد
                embed = discord.Embed(
                    title="✅ تم حذف التكتات",
                    description=f"تم حذف جميع تكتات {self.عضو.display_name}",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="👤 العضو", value=self.عضو.mention, inline=True)
                embed.add_field(name="📊 عدد التكتات المحذوفة", value=f"**{deleted_count}**", inline=True)
                embed.add_field(name="📝 السبب", value=self.السبب, inline=True)
                embed.add_field(name="👤 تم الحذف بواسطة", value=interaction.user.mention, inline=True)
                embed.add_field(name="🕒 وقت الحذف", value=datetime.now().strftime("%H:%M:%S"), inline=True)
                
                # إضافة نسخة احتياطية
                if backup_data:
                    backup_text = ""
                    for date_str, count in list(backup_data.items())[:5]:
                        backup_text += f"**{date_str}**: {count} تكت\n"
                    embed.add_field(name="📋 آخر 5 أيام (نسخة احتياطية)", value=backup_text, inline=False)
                
                embed.set_footer(text="⚠️  لا يمكن استرجاع التكتات المحذوفة")
                
                await interaction.response.edit_message(embed=embed, view=None)
                
                # طباعة للترمينال
                print(f"🗑️  {interaction.user.name} حذف {deleted_count} تكت من {self.عضو.name} - السبب: {self.السبب}")
            else:
                embed = discord.Embed(
                    title="⚠️  لا توجد تكتات",
                    description=f"{self.عضو.display_name} لا يمتلك أي تكتات",
                    color=discord.Color.orange()
                )
                await interaction.response.edit_message(embed=embed, view=None)
        
        @discord.ui.button(label="❌ إلغاء", style=discord.ButtonStyle.secondary)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="❌ تم الإلغاء",
                description="لم يتم حذف أي تكتات",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)
    
    # إرسال رسالة التأكيد
    embed = discord.Embed(
        title="⚠️  تأكيد حذف التكتات",
        description=f"هل أنت متأكد من حذف **جميع** تكتات {عضو.mention}؟\n\n**هذا الإجراء لا يمكن التراجع عنه!**",
        color=discord.Color.red()
    )
    
    # التحقق من وجود تكتات
    ticket_data = load_data(TICKET_DATA_FILE)
    user_id = str(عضو.id)
    
    if 'tickets' in ticket_data and user_id in ticket_data['tickets']:
        total_tickets = sum(ticket_data['tickets'][user_id].values())
        today_tickets = ticket_data['tickets'][user_id].get(str(date.today()), 0)
        
        embed.add_field(name="📊 التكتات الحالية", value=f"**{total_tickets}** تكت", inline=True)
        embed.add_field(name="📅 تكتات اليوم", value=f"**{today_tickets}** تكت", inline=True)
        embed.add_field(name="📝 سبب الحذف", value=السبب, inline=True)
    else:
        embed.description = f"{عضو.mention} لا يمتلك أي تكتات للحذف"
    
    embed.set_footer(text="سيتم إلغاء هذا الطلب بعد 60 ثانية")
    
    view = ConfirmDeleteView(عضو, السبب)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@tree.command(
    name="تكتات",
    description="عرض عدد التكتات المستلمة",
)
@app_commands.describe(عضو="العضو الذي تريد عرض تكتاته (اختياري)")
async def تكتات(interaction: discord.Interaction, عضو: discord.Member = None):
    if not عضو:
        عضو = interaction.user
    
    await interaction.response.defer()
    
    ticket_data = load_data(TICKET_DATA_FILE)
    user_id = str(عضو.id)
    
    embed = discord.Embed(
        title=f"🎫 تكتات {عضو.display_name}",
        color=discord.Color.blue()
    )
    
    if عضو.avatar:
        embed.set_thumbnail(url=عضو.avatar.url)
    
    if 'tickets' in ticket_data and user_id in ticket_data['tickets']:
        user_tickets = ticket_data['tickets'][user_id]
        
        total_tickets = sum(user_tickets.values())
        today_tickets = user_tickets.get(str(date.today()), 0)
        
        # تكتات الأسبوع
        week_ago = date.today() - timedelta(days=7)
        weekly_tickets = 0
        for ticket_date, count in user_tickets.items():
            if datetime.strptime(ticket_date, "%Y-%m-%d").date() >= week_ago:
                weekly_tickets += count
        
        embed.add_field(name="🎫 الإجمالي الكلي", value=f"**{total_tickets}** تكت", inline=True)
        embed.add_field(name="📅 تكتات اليوم", value=f"**{today_tickets}** تكت", inline=True)
        embed.add_field(name="📊 تكتات الأسبوع", value=f"**{weekly_tickets}** تكت", inline=True)
        
        if user_tickets:
            avg_daily = total_tickets / len(user_tickets)
            embed.add_field(name="📈 متوسط يومي", value=f"**{avg_daily:.1f}** تكت/يوم", inline=True)
        
        # آخر 5 أيام
        sorted_dates = sorted(user_tickets.keys(), reverse=True)[:5]
        if sorted_dates:
            recent_text = ""
            for ticket_date in sorted_dates:
                count = user_tickets[ticket_date]
                recent_text += f"**{ticket_date}**: {count} تكت\n"
            
            embed.add_field(name="📅 آخر 5 أيام", value=recent_text, inline=False)
    else:
        embed.description = "📭 لا توجد تكتات مسجلة لهذا العضو"
    
    embed.set_footer(text=f"تاريخ اليوم: {date.today()}")
    await interaction.followup.send(embed=embed)

@tree.command(
    name="مساعدة",
    description="عرض جميع أوامر البوت",
)
async def مساعدة(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 قائمة أوامر البوت الخاص",
        description="🔐 **بوت خاص يعمل في سيرفر واحد فقط**",
        color=discord.Color.blue()
    )
    
    commands_list = """
    **📊 أوامر التفاعل:**
    `/تفاعل [@عضو]` - عرض تفاعل عضو لليوم
    `/افضل_متفاعل` - أكثر الأعضاء تفاعلاً بالأسبوع
    
    **🎫 أوامر التكتات:**
    `/استلام_تكت @عضو [عدد] [سبب]` - إضافة/طرح تكتات (للأونرز فقط)
    `/حذف_تكتات @عضو [سبب]` - حذف جميع تكتات العضو (للأونرز فقط)
    `/تكتات [@عضو]` - عرض تكتات العضو
    
    **⚙️ أوامر الإدارة:**
    `/مساعدة` - عرض هذه القائمة
    `/sync` - مزامنة الأوامر (للأونرز)
    `/ping` - اختبار البوت
    `/سيرفر` - معلومات السيرفر
    """
    
    embed.add_field(name="🛠️ الأوامر المتاحة", value=commands_list, inline=False)
    
    if interaction.user.id in OWNER_USERS:
        embed.add_field(
            name="⭐ صلاحيات خاصة للأونرز", 
            value="• `/استلام_تكت @عضو -5` - طرح 5 تكتات\n• `/حذف_تكتات @عضو` - حذف جميع التكتات\n• `/sync` - مزامنة الأوامر", 
            inline=False
        )
    
    embed.set_footer(text=f"📅 {date.today()} | الإصدار 4.0 مع إدارة التكتات المتقدمة")
    await interaction.response.send_message(embed=embed)

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if TOKEN:
        print("=" * 60)
        print("🚀 جاري تشغيل البوت...")
        print("=" * 60)
        bot.run(TOKEN)
    else:
        print("❌ لم يتم العثور على التوكن!")
        print("=" * 50)
        print("🔧 تأكد من إضافة DISCORD_TOKEN في Secrets")
        print("=" * 50)

"""初始化数据库并写入示例数据"""
from datetime import datetime, timedelta, timezone

from models import SessionLocal, engine, Base, Letter, Code, Question

# 建表
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 写入信件模板
if db.query(Letter).count() == 0:
    letters = [
        Letter(
            type="healing",
            title="今日解忧",
            content="生活也许会有遗憾，但未来依旧值得期待。\n\n允许自己偶尔的脆弱，因为那是光照进来的地方。\n\n今天也要好好照顾自己哦！",
            signature="—— 伴你同行的人",
        ),
        Letter(
            type="healing",
            title="静心时刻",
            content="如果觉得周围太喧嚣，那就闭上眼睛，听听自己心跳的声音。\n\n你不需要迎合所有人的期待，你只需要成为你自己。",
            signature="—— 守护你的星",
        ),
        Letter(
            type="birthday",
            title="生日祝福",
            content="祝你岁岁常欢愉，万事皆胜意。\n\n愿所有的美好都如期而至，所有的幸运都如影随形。\n\n生日快乐！",
            signature="—— 远方的祝福",
        ),
        Letter(
            type="encouragement",
            title="为你加油",
            content="今天的你已经足够努力了。\n\n别对自己太苛刻，每一步向前都是值得庆祝的小胜利。\n\n累了就休息，但永远不要放弃那个闪闪发光的自己。",
            signature="—— 相信你的人",
        ),
        Letter(
            type="night",
            title="晚安好梦",
            content="夜深了，把今天的烦恼都叠好放进抽屉吧。\n\n星星会为你守夜，月亮会为你掌灯。\n\n闭上眼睛，让温柔梦乡拥抱你。晚安，世界和我爱着你。",
            signature="—— 守护你安眠的人",
        ),
        Letter(
            type="love",
            title="遇见你真好",
            content="遇见你，是我人生中最美丽的意外。\n\n就像冬日里的一杯热可可，温暖了整个季节。\n\n不需要什么轰轰烈烈，只愿细水长流，与你慢慢变老。",
            signature="—— 偷偷喜欢你的人",
        ),
    ]
    db.add_all(letters)
    db.commit()
    print(f"[OK] Created {len(letters)} letter templates")
else:
    print(f"[SKIP] Letters already exist: {db.query(Letter).count()}")

# 写入示例兑换码
if db.query(Code).count() == 0:
    all_letters = db.query(Letter).all()
    codes = [
        Code(code="XJ-888888", letter_id=all_letters[0].id, batch_id="demo"),
        Code(code="XJ-666666", letter_id=all_letters[1].id, batch_id="demo"),
        Code(code="ZF-999999", letter_id=all_letters[2].id, batch_id="demo"),
        Code(code="GL-123456", letter_id=all_letters[3].id, batch_id="demo"),
        Code(code="WA-520131", letter_id=all_letters[4].id, batch_id="demo"),
        Code(code="QS-999999", letter_id=all_letters[5].id, batch_id="demo"),
    ]
    db.add_all(codes)
    db.commit()
    print(f"[OK] Created {len(codes)} demo codes:")
    for c in codes:
        print(f"    {c.code}")
else:
    print(f"[SKIP] Codes already exist: {db.query(Code).count()}")

# ===== 写入50条种子问题 =====
SEED_QUESTIONS = [
    # 小学生/初中生提问（8-15岁）
    ("小星用户", 10, "考试考砸了，妈妈会失望吗？我真的很害怕回家"),
    ("小月用户", 11, "我的好朋友突然不理我了，我不知道自己做错了什么"),
    ("小阳用户", 12, "长大以后还会像现在这么快乐吗？"),
    ("小乐用户", 9, "为什么大人们总是说小孩子没有烦恼？我明明有很多烦恼"),
    ("小风用户", 13, "我总是不敢举手回答问题，怕答错了被同学笑话，怎么办？"),
    ("小雪用户", 10, "转学后我一个朋友都没有，每天午餐都是一个人吃"),
    ("小雨用户", 14, "我偷偷喜欢班上的一个同学，但又不敢和任何人说"),
    ("小云用户", 11, "爸妈总是吵架，我躲在被子里哭，他们不知道"),
    ("小光用户", 12, "怎么才能让老师注意到我？我坐在最后一排，好像透明人"),
    ("小草用户", 15, "我考上了重点班，但好累啊，每天学到很晚还是跟不上"),
    ("小苗用户", 13, "被同学起外号，虽然他们说只是开玩笑，但我真的很难过"),
    ("小树用户", 10, "养了三年的小金鱼死了，我哭了很久，这很幼稚吗？"),
    ("小花用户", 14, "我不想上那么多补习班，我想有时间做自己喜欢的事情"),
    ("小鸟用户", 11, "我画画很好看，但爸爸说那没用，让我多做数学题"),
    ("小鱼用户", 9, "晚上一个人睡觉的时候总是害怕，有什么办法吗？"),
    ("小兔用户", 12, "我体育特别差，每次跑步都是最后一名，好丢脸"),
    ("小猫用户", 15, "初中的友谊好复杂，不知道谁才是真心对我好的"),

    # 高中生/大学生提问（16-23岁）
    ("阿辰用户", 17, "高考压力太大了，有时候想放弃，又害怕对不起父母"),
    ("阿楠用户", 18, "考上大学后发现身边的人都好优秀，觉得自己特别普通"),
    ("阿薇用户", 19, "选了一个不喜欢的专业，每天上课都很痛苦，要不要转？"),
    ("阿泽用户", 20, "大学里融不进宿舍圈子，她们出去吃饭从不叫我"),
    ("阿瑶用户", 21, "实习的时候被领导骂了，明明不是我的错，但不敢反驳"),
    ("阿飞用户", 18, "高考失利复读了一年，很怕今年还是考不好"),
    ("阿月用户", 22, "马上要毕业了，完全不知道自己想做什么，很迷茫"),
    ("阿星用户", 20, "大学里谈了恋爱，但家里不同意，夹在中间好累"),
    ("阿雨用户", 19, "室友经常熬夜打游戏很吵，我又不好意思说，怎么办？"),
    ("阿风用户", 23, "第一份工作工资很低，连房租都快交不起了，大城市好难"),
    ("阿云用户", 17, "艺考集训离家很远，想家但又不想让爸妈担心"),
    ("阿光用户", 21, "考研还是就业？每天在想这个问题想到头疼"),
    ("阿雪用户", 20, "觉得自己什么都做不好，社恐、拖延、还挂了科"),
    ("阿雷用户", 22, "创业团队散伙了，投入的钱全打了水漂，不知道下一步怎么办"),
    ("阿霜用户", 19, "总是不自觉地和别人比较，越比越焦虑，怎么停下来？"),
    ("阿阳用户", 18, "高中最好的朋友去了不同的城市，感觉关系慢慢变淡了"),
    ("阿墨用户", 23, "面试被拒了十几次，简历改了又改，快没信心了"),

    # 职场人/青年提问（24-35岁）
    ("大海用户", 25, "工作三年还是感觉自己很菜，什么时候才能独当一面？"),
    ("小山用户", 27, "996熬不动了，但辞职后又怕找不到下一份工作"),
    ("小河用户", 28, "被催婚催到窒息，可我真的还没遇到对的人"),
    ("小林用户", 30, "在大城市漂了六年，还是买不起房，要不要回老家？"),
    ("小湖用户", 26, "和同事发生了矛盾，每天上班都很尴尬，要不要换组？"),
    ("小森用户", 32, "创业两年还在亏钱，家人都劝我放弃，但我不甘心"),
    ("小川用户", 29, "感觉每天的生活就是上班下班，找不到什么意义"),
    ("小岩用户", 31, "终于买了房，但背上了三十年的贷款，好像人生被锁住了"),
    ("小溪用户", 24, "刚入职场，不太会跟领导沟通，总是被说不够主动"),
    ("小泉用户", 35, "35岁了还在做基础岗，有时候觉得这辈子就这样了"),
    ("小峰用户", 27, "和女朋友异地恋三年了，不知道该不该继续坚持"),
    ("小谷用户", 33, "存款不多但又很想养一只猫，这算不负责任吗？"),
    ("小坡用户", 26, "下班后只想躺着，什么爱好都没了，正常吗？"),

    # 中年人提问（36-55岁）
    ("老松用户", 40, "人到中年，上有老下有小，感觉自己的需求永远排最后"),
    ("老柏用户", 45, "和孩子越来越没话聊了，一说话就吵架，怎么办？"),
    ("老柳用户", 38, "身体开始出问题了，但还是不敢请假，怕丢了工作"),
    ("老杨用户", 50, "孩子们都长大了，突然觉得家里好安静，有点不适应"),
    ("老槐用户", 42, "中年失业，投了好多简历都没回音，家里还有房贷"),
    ("老榆用户", 48, "父母身体越来越差，想多陪他们但工作又走不开"),
    ("老杉用户", 36, "结婚十年了，和老公更像是合租室友，这正常吗？"),
    ("老桐用户", 55, "快退休了，反而更焦虑，不知道退休后要做什么"),
    ("老枫用户", 43, "年轻时的梦想早就忘了，偶尔想起来会觉得遗憾"),
    ("老楠用户", 39, "孩子叛逆期，说什么都顶嘴，我快崩溃了"),
]

if db.query(Question).count() == 0:
    seven_days = timedelta(days=7)
    now = datetime.now(timezone.utc)
    seed_questions = []
    for nickname, age, content in SEED_QUESTIONS:
        q = Question(
            asker_code="seed",
            asker_nickname=nickname,
            asker_age=age,
            content=content,
            source="seed",
            status="approved",
            created_at=now,
            expires_at=now + seven_days,
        )
        seed_questions.append(q)
    db.add_all(seed_questions)
    db.commit()
    print(f"[OK] Created {len(seed_questions)} seed questions")
else:
    print(f"[SKIP] Questions already exist: {db.query(Question).count()}")

db.close()
print("\n[OK] Database init complete!")

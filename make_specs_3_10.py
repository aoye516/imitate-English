"""
Generate starter specs for Peppa Pig S01E03-E10.

This is the scalable v2 workflow:
- L1 only includes newly introduced, imageable words for the episode.
- Reused/global words stay in the lesson through chunks/sentences, but are not
  duplicated as L1 cards.
- L2/L3 are episode-scoped and focus on the story-critical expressions.

The sentence timestamps are derived from parsed transcript start times by keyword
matching. They are good enough for a first full-pass production; tighten individual
clips later if a real-device review finds rough edges.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent

WORD_STYLE = "儿童 App UI 素材, painterly children book illustration, 温暖配色（赭石、琥珀、柔和粉橙）, 柔和阴影, ⚠️纯白色背景 pure white background, 居中构图, 单个物体/主体, 正方形, 无任何文字"
CHUNK_STYLE = "儿童 App UI 素材, painterly children book illustration, 温暖配色（赭石、琥珀、柔和粉橙）, 柔和阴影, ⚠️纯白色背景 pure white background, 居中构图, 单一动作场景, 正方形, 无任何文字"
SENT_STYLE = "儿童 App UI 素材, painterly children book illustration, 温暖配色（赭石、琥珀、柔和粉橙）, 柔和阴影, ⚠️纯白色背景 pure white background, 居中构图, 完整剧情场景, 横向构图（4:3），无任何文字"

WORD_META = {
    "susie": ("苏西", "a cute white sheep girl wearing a pink dress, friendly smile, full body, child character"),
    "friend": ("朋友", "two child animal friends holding hands and smiling at each other, warm friendship feeling"),
    "best": ("最好的", "a gold star medal with a big number one feeling, celebratory best-choice symbol, no text"),
    "help": ("帮助", "one small child animal helping another stand up gently, caring supportive gesture"),
    "cookie": ("饼干", "a round chocolate chip cookie on a small plate, warm baked texture, no crumbs spelling"),
    "doctor": ("医生", "a friendly child doctor character with a toy stethoscope, clean medical bag, reassuring smile"),
    "nurse": ("护士", "a friendly nurse character holding a small first-aid kit, gentle caring smile"),
    "patient": ("病人", "a small child animal sitting in bed with a thermometer and blanket, being cared for"),
    "need": ("需要", "a small child animal reaching toward a needed object with hopeful eyes, clear wanting gesture"),
    "sheep": ("羊", "a cute fluffy white sheep standing on grass, round woolly body, gentle smile"),
    "better": ("好转", "a sick child animal becoming healthy, sitting up in bed with a happy recovering smile"),

    "parrot": ("鹦鹉", "a colorful green parrot perched on a simple wooden stand, bright feathers, friendly expression"),
    "polly": ("波莉", "a colorful pet parrot on a perch, slightly theatrical and clever, friendly bird character"),
    "granny": ("奶奶", "a kind elderly mother pig with glasses and a warm dress, smiling grandmother portrait"),
    "grandpa": ("爷爷", "a friendly elderly father pig with a cap and gardening clothes, smiling grandfather portrait"),
    "pet": ("宠物", "a beloved small pet animal sitting happily beside a food bowl and toy, cared-for feeling"),
    "noisy": ("吵闹", "a colorful parrot squawking loudly with sound waves around its beak, no text"),
    "clever": ("聪明", "a cute animal with a lightbulb above its head and a proud clever smile"),
    "sweet": ("可爱/亲切", "a cute child animal offering a small cake with a gentle sweet smile and hearts"),
    "cake": ("蛋糕", "a small round cake with pink icing and one cherry on top, no candles, no text"),
    "copy": ("模仿", "two parrots side by side, one copying the other's pose exactly, mirror-like action"),
    "say": ("说", "a cute animal speaking with a simple speech bubble containing no letters, mouth open"),
    "pretty": ("漂亮", "a colorful parrot with shiny feathers and sparkles around it, elegant pose"),

    "hide": ("藏", "a small child animal hiding behind a curtain with only eyes peeking out, playful secret"),
    "seek": ("找", "a child animal looking around with a magnifying glass, searching game mood"),
    "count": ("数数", "a child animal covering eyes and counting on fingers, hide-and-seek start, no numbers"),
    "turn": ("轮到", "two child animals passing a small turn marker between them, taking turns in a game"),
    "table": ("桌子", "a simple wooden table in a cozy room, centered object, no characters"),
    "basket": ("篮子", "a woven basket sitting on the floor with a cloth inside, warm home object"),
    "eye": ("眼睛", "a large friendly cartoon eye looking sideways, simple iconic close-up"),
    "newspaper": ("报纸", "a folded newspaper on a table, simple grey pages with no readable text"),
    "behind": ("在后面", "a small child animal partly hidden behind a big chair, back-position clearly shown"),
    "ready": ("准备好", "a child animal standing in a ready pose before a game, knees bent, excited smile"),
    "somewhere": ("某处", "a room with several possible hiding places highlighted by question marks, no text"),

    "paint": ("画画", "a brush painting colorful strokes on paper, paint palette beside it, bright colors"),
    "brilliant": ("太棒了", "a child animal proudly showing a sparkling picture, amazed happy reaction"),
    "flower": ("花", "a single bright flower with green leaves in a small patch of soil, centered"),
    "picture": ("图画", "a colorful childlike painting on paper clipped to a board, no text"),
    "wrong": ("错了", "a puzzled child animal looking at a mismatched picture piece, red cross symbol without text"),
    "group": ("小组", "a small group of child animal classmates sitting together in a circle, friendly class mood"),
    "playgroup": ("幼儿园", "a cheerful classroom with toys, paint easel, and small chairs, preschool atmosphere"),
    "children": ("孩子们", "a cheerful group of different child animal friends standing together"),
    "proud": ("骄傲", "a child animal holding up a finished drawing with chest puffed proudly, happy smile"),
    "circle": ("圆圈", "a simple colorful circle shape painted on paper, no text"),
    "color": ("颜色", "a painter palette with bright blobs of red, yellow, blue, green paint"),

    "computer": ("电脑", "a simple desktop computer with keyboard and mouse on a desk, no readable text on screen"),
    "work": ("工作", "an adult pig sitting at a desk working seriously on a computer, focused pose"),
    "chicken": ("小鸡", "a small yellow chick standing on the ground, cute round body, tiny beak"),
    "touch": ("触碰", "a small hand reaching toward a computer button, warning-like careful gesture"),
    "mend": ("修理", "a friendly adult fixing a broken computer with a small screwdriver, repair scene"),
    "important": ("重要", "a red exclamation mark symbol inside a glowing badge, serious important feeling, no text"),
    "lunch": ("午餐", "a lunch plate with sandwich, fruit, and cup on a small table, cheerful meal"),
    "disturb": ("打扰", "a child animal interrupting an adult at a desk, adult looks mildly distracted"),
    "finish": ("完成", "a completed checklist with a big green checkmark, no readable words"),
    "ask": ("问", "a child animal raising one hand with a question bubble containing no text"),

    "ball": ("球", "a bright red ball on grass, simple centered toy ball"),
    "piggy": ("小猪", "a small round pink piglet standing happily, playful childlike body"),
    "middle": ("中间", "one small piglet standing between two other children, clearly in the center"),
    "hooray": ("好耶", "three child animals cheering with arms up, confetti and stars, joyful celebration"),
    "try": ("试试", "a child animal attempting to catch a ball with focused effort, trying hard"),
    "stand": ("站", "a child animal standing upright with feet planted, simple full-body pose"),
    "teach": ("教", "an older child animal showing a younger one how to hold a ball, teaching gesture"),
    "hand": ("手", "two small hands reaching toward a ball, close-up of hands"),
    "enough": ("足够", "a bowl filled just to the right amount with a green checkmark, enough quantity"),
    "caught": ("接住了", "a child animal successfully catching a red ball in both hands, proud smile"),

    "glasses": ("眼镜", "a pair of round black glasses on a white surface, centered, no face"),
    "grumpy": ("烦躁", "a father pig with crossed arms and a frowning grumpy face, comic annoyance"),
    "put": ("放", "a hand placing a pair of glasses carefully onto a table, clear placing action"),
    "without": ("没有", "a father pig squinting with empty face and no glasses, looking confused"),
    "clearly": ("清楚地", "a pair of glasses making a blurry scene become sharp and clear, before-after feeling"),
    "bathroom": ("浴室", "a clean bathroom with sink, mirror, and bathtub, no people"),
    "bedroom": ("卧室", "a cozy bedroom with bed, lamp, and small rug, no people"),
    "lose": ("弄丢", "a sad father pig searching pockets with a missing glasses outline and question mark"),
    "silly": ("傻乎乎", "a goofy father pig smiling sheepishly with glasses crooked, harmless funny mood"),
    "bump": ("撞到", "a father pig gently bumping into a chair with surprise lines, comic safe accident"),
    "careful": ("小心", "a child animal holding up one cautious hand near an obstacle, careful warning pose"),

    "grow": ("生长", "a small green sprout growing upward from soil with motion lines and sunlight"),
    "seed": ("种子", "several tiny brown seeds in an open palm, close-up, simple natural object"),
    "plant": ("种/植物", "a small green plant with two leaves growing in a pot of soil"),
    "strawberry": ("草莓", "a bright red strawberry with green leaves, juicy and centered"),
    "apple": ("苹果", "a shiny red apple with one green leaf, centered on white background"),
    "carrot": ("胡萝卜", "an orange carrot with leafy green top, centered"),
    "choose": ("选择", "a child animal pointing between two baskets of fruit, choosing gesture"),
    "tiny": ("很小", "a tiny sprout next to a much larger plant for size contrast, tiny one highlighted"),
    "water": ("浇水", "a watering can pouring water onto a small plant, gentle blue droplets"),
    "bigger": ("更大", "a small sprout beside a larger plant with upward growth arrow, no text"),
    "earth": ("泥土", "a small mound of brown garden soil with crumbly texture, centered"),
    "hole": ("洞", "a small round hole dug in garden soil, viewed from above"),
    "wait": ("等待", "a child animal sitting patiently beside a flower pot, watching it quietly"),
}

EPISODES = {
    "peppa-s01e03": {
        "title": "Best Friend", "episode": 3,
        "words": ["susie","friend","best","help","cookie","doctor","nurse","patient","need","sheep","better"],
        "chunks": [
            ("best_friend", "best friend", "最好的朋友", ["best","friend"]),
            ("this_is_susie", "This is Susie Sheep", "这是小羊Susie", ["susie","sheep"]),
            ("play_doctor", "play doctors and nurses", "玩医生护士游戏", ["doctor","nurse"]),
            ("need_help", "need some help", "需要帮助", ["need","help"]),
            ("feel_better", "feel better", "感觉好些了", ["better"]),
            ("make_cookies", "make cookies", "做饼干", ["cookie"]),
        ],
        "sentences": [
            ("s01","This is Peppa's best friend, Susie Sheep.","这是Peppa最好的朋友Susie羊。",["best","friend","susie","sheep"],["best_friend","this_is_susie"]),
            ("s02","Peppa and Susie are best friends.","Peppa和Susie是最好的朋友。",["best","friend"],["best_friend"]),
            ("s03","They like to play together.","她们喜欢一起玩。",["play"],[]),
            ("s04","Peppa wants to play doctors and nurses.","Peppa想玩医生护士游戏。",["doctor","nurse"],["play_doctor"]),
            ("s05","Susie is the nurse and Peppa is the doctor.","Susie当护士,Peppa当医生。",["susie","nurse","doctor"],["play_doctor"]),
            ("s06","George needs some help.","George需要帮助。",["need","help"],["need_help"]),
            ("s07","The patient is feeling much better.","病人感觉好多了。",["patient","better"],["feel_better"]),
            ("s08","Mummy Pig is making cookies.","猪妈妈正在做饼干。",["cookie"],["make_cookies"]),
            ("s09","Peppa and Susie love cookies.","Peppa和Susie喜欢饼干。",["cookie","love"],["make_cookies"]),
            ("s10","Best friends can play nicely together.","好朋友可以一起开心地玩。",["best","friend","play"],["best_friend"]),
        ],
    },
    "peppa-s01e04": {
        "title": "Polly Parrot", "episode": 4,
        "words": ["parrot","polly","granny","grandpa","pet","noisy","clever","sweet","cake","copy","say","pretty"],
        "chunks": [
            ("polly_parrot", "Polly Parrot", "鹦鹉Polly", ["polly","parrot"]),
            ("granny_pig", "Granny Pig", "猪奶奶", ["granny"]),
            ("grandpa_pig", "Grandpa Pig", "猪爷爷", ["grandpa"]),
            ("a_pet_parrot", "a pet parrot", "宠物鹦鹉", ["pet","parrot"]),
            ("very_noisy", "very noisy", "非常吵", ["noisy"]),
            ("clever_parrot", "clever parrot", "聪明的鹦鹉", ["clever","parrot"]),
            ("have_some_cake", "have some cake", "吃点蛋糕", ["cake"]),
            ("copy_what_you_say", "copy what you say", "模仿你说的话", ["copy","say"]),
        ],
        "sentences": [
            ("s01","Peppa and George are visiting Granny Pig and Grandpa Pig.","Peppa和George去看猪奶奶和猪爷爷。",["granny","grandpa"],["granny_pig","grandpa_pig"]),
            ("s02","Granny Pig has a pet parrot.","猪奶奶有一只宠物鹦鹉。",["granny","pet","parrot"],["a_pet_parrot"]),
            ("s03","Polly Parrot is very pretty.","鹦鹉Polly很漂亮。",["polly","parrot","pretty"],["polly_parrot"]),
            ("s04","Polly is a clever parrot.","Polly是一只聪明的鹦鹉。",["polly","clever","parrot"],["clever_parrot"]),
            ("s05","Polly can copy what you say.","Polly会模仿你说的话。",["copy","say"],["copy_what_you_say"]),
            ("s06","Peppa says hello to Polly.","Peppa跟Polly打招呼。",["say","polly"],["polly_parrot"]),
            ("s07","Polly is very noisy.","Polly非常吵。",["polly","noisy"],["very_noisy"]),
            ("s08","Granny Pig gives everyone cake.","猪奶奶给大家蛋糕。",["granny","cake"],["have_some_cake"]),
            ("s09","Polly wants some cake too.","Polly也想吃蛋糕。",["polly","cake","want"],["have_some_cake"]),
            ("s10","Peppa thinks Polly is sweet.","Peppa觉得Polly很可爱。",["polly","sweet"],["polly_parrot"]),
        ],
    },
    "peppa-s01e05": {
        "title": "Hide and Seek", "episode": 5,
        "words": ["hide","seek","count","turn","table","basket","eye","newspaper","behind","ready","somewhere"],
        "chunks": [
            ("hide_and_seek", "hide and seek", "捉迷藏", ["hide","seek"]),
            ("your_turn", "your turn", "轮到你了", ["turn"]),
            ("count_to_ten", "count to ten", "数到十", ["count"]),
            ("close_your_eyes", "close your eyes", "闭上眼睛", ["eye"]),
            ("are_you_ready", "Are you ready?", "你准备好了吗", ["ready"]),
            ("behind_the_table", "behind the table", "在桌子后面", ["behind","table"]),
            ("in_the_basket", "in the basket", "在篮子里", ["basket"]),
            ("behind_the_newspaper", "behind the newspaper", "在报纸后面", ["behind","newspaper"]),
        ],
        "sentences": [
            ("s01","Peppa and George are playing hide and seek.","Peppa和George在玩捉迷藏。",["hide","seek"],["hide_and_seek"]),
            ("s02","It is George's turn to hide.","轮到George藏了。",["turn","hide"],["your_turn"]),
            ("s03","Peppa must count to ten.","Peppa必须数到十。",["count"],["count_to_ten"]),
            ("s04","Peppa closes her eyes.","Peppa闭上眼睛。",["eye"],["close_your_eyes"]),
            ("s05","George is hiding somewhere.","George藏在某个地方。",["hide","somewhere"],["hide_and_seek"]),
            ("s06","Is he behind the table?","他在桌子后面吗？",["behind","table"],["behind_the_table"]),
            ("s07","Is he in the basket?","他在篮子里吗？",["basket"],["in_the_basket"]),
            ("s08","Daddy Pig is behind the newspaper.","猪爸爸躲在报纸后面。",["behind","newspaper"],["behind_the_newspaper"]),
            ("s09","George is ready to be found.","George准备好被找到了。",["ready"],["are_you_ready"]),
            ("s10","Peppa has found George.","Peppa找到George了。",["find"],["hide_and_seek"]),
        ],
    },
    "peppa-s01e06": {
        "title": "The Playgroup", "episode": 6,
        "words": ["paint","brilliant","flower","picture","wrong","group","playgroup","children","proud","circle","color"],
        "chunks": [
            ("the_playgroup", "the playgroup", "幼儿园/游戏班", ["playgroup"]),
            ("paint_a_picture", "paint a picture", "画一幅画", ["paint","picture"]),
            ("a_big_flower", "a big flower", "一朵大花", ["flower"]),
            ("wrong_color", "wrong color", "颜色错了", ["wrong","color"]),
            ("very_brilliant", "very brilliant", "太棒了", ["brilliant"]),
            ("children_playing", "children playing", "孩子们玩耍", ["children"]),
            ("make_a_circle", "make a circle", "围成圆圈", ["circle"]),
            ("feel_proud", "feel proud", "感到骄傲", ["proud"]),
        ],
        "sentences": [
            ("s01","Today George is going to the playgroup.","今天George要去幼儿园。",["playgroup"],["the_playgroup"]),
            ("s02","There are lots of children at playgroup.","幼儿园里有很多孩子。",["children","playgroup"],["children_playing"]),
            ("s03","The children are painting pictures.","孩子们在画画。",["paint","picture"],["paint_a_picture"]),
            ("s04","George paints a flower.","George画了一朵花。",["paint","flower"],["a_big_flower"]),
            ("s05","Peppa thinks George has used the wrong color.","Peppa觉得George用错颜色了。",["wrong","color"],["wrong_color"]),
            ("s06","Madame Gazelle says it is brilliant.","Gazelle老师说这太棒了。",["brilliant"],["very_brilliant"]),
            ("s07","George is very proud of his picture.","George为自己的画很骄傲。",["proud","picture"],["feel_proud"]),
            ("s08","The children make a circle.","孩子们围成一个圆圈。",["children","circle"],["make_a_circle"]),
            ("s09","Peppa shows George what to do.","Peppa给George示范怎么做。",["show"],[]),
            ("s10","George likes playgroup.","George喜欢幼儿园。",["playgroup"],["the_playgroup"]),
        ],
    },
    "peppa-s01e07": {
        "title": "Mummy Pig at Work", "episode": 7,
        "words": ["computer","work","chicken","touch","mend","important","lunch","disturb","finish","ask"],
        "chunks": [
            ("at_work", "at work", "在工作", ["work"]),
            ("on_the_computer", "on the computer", "在电脑上", ["computer"]),
            ("dont_touch", "don't touch", "不要碰", ["touch"]),
            ("very_important", "very important", "非常重要", ["important"]),
            ("mend_the_computer", "mend the computer", "修电脑", ["mend","computer"]),
            ("make_lunch", "make lunch", "做午餐", ["lunch"]),
            ("dont_disturb", "don't disturb", "不要打扰", ["disturb"]),
            ("finish_work", "finish work", "完成工作", ["finish","work"]),
        ],
        "sentences": [
            ("s01","Mummy Pig is working on her computer.","猪妈妈正在电脑上工作。",["mummy","work","computer"],["at_work","on_the_computer"]),
            ("s02","Peppa and George must not touch the computer.","Peppa和George不能碰电脑。",["touch","computer"],["dont_touch"]),
            ("s03","Mummy Pig has some very important work to do.","猪妈妈有很重要的工作要做。",["important","work"],["very_important"]),
            ("s04","Peppa wants to play a computer game.","Peppa想玩电脑游戏。",["computer","game"],["on_the_computer"]),
            ("s05","The computer is not working.","电脑坏了。",["computer","work"],[]),
            ("s06","Daddy Pig can mend the computer.","猪爸爸会修电脑。",["mend","computer"],["mend_the_computer"]),
            ("s07","Mummy Pig is making lunch.","猪妈妈在做午餐。",["lunch"],["make_lunch"]),
            ("s08","Please do not disturb Mummy Pig.","请不要打扰猪妈妈。",["disturb"],["dont_disturb"]),
            ("s09","Mummy Pig has finished her work.","猪妈妈完成了工作。",["finish","work"],["finish_work"]),
            ("s10","George likes the happy chicken game.","George喜欢开心小鸡游戏。",["chicken","happy"],[]),
        ],
    },
    "peppa-s01e08": {
        "title": "Piggy in the Middle", "episode": 8,
        "words": ["ball","piggy","middle","hooray","try","stand","teach","hand","enough","caught"],
        "chunks": [
            ("piggy_middle", "piggy in the middle", "中间的小猪", ["piggy","middle"]),
            ("throw_the_ball", "throw the ball", "扔球", ["ball"]),
            ("catch_the_ball", "catch the ball", "接球", ["ball","caught"]),
            ("stand_in_middle", "stand in the middle", "站在中间", ["stand","middle"]),
            ("try_again", "try again", "再试一次", ["try"]),
            ("teach_george", "teach George", "教George", ["teach"]),
            ("hands_ready", "hands ready", "手准备好", ["hand","ready"]),
            ("thats_enough", "that's enough", "够了", ["enough"]),
        ],
        "sentences": [
            ("s01","Peppa and George are playing with a ball.","Peppa和George在玩球。",["ball"],["throw_the_ball"]),
            ("s02","Peppa throws the ball to George.","Peppa把球扔给George。",["ball","throw"],["throw_the_ball"]),
            ("s03","George tries to catch the ball.","George试着接球。",["try","ball","caught"],["catch_the_ball","try_again"]),
            ("s04","George cannot catch the ball.","George接不到球。",["ball","caught"],["catch_the_ball"]),
            ("s05","Mummy Pig teaches George how to catch.","猪妈妈教George怎么接球。",["teach","caught"],["teach_george"]),
            ("s06","George must stand in the middle.","George必须站在中间。",["stand","middle"],["stand_in_middle"]),
            ("s07","Peppa and Daddy Pig throw the ball.","Peppa和猪爸爸扔球。",["ball","throw"],["throw_the_ball"]),
            ("s08","George catches the ball.","George接住球了。",["caught","ball"],["catch_the_ball"]),
            ("s09","Hooray for George!","George好耶！",["hooray"],[]),
            ("s10","Now George is piggy in the middle.","现在George是中间的小猪。",["piggy","middle"],["piggy_middle"]),
        ],
    },
    "peppa-s01e09": {
        "title": "Daddy Loses His Glasses", "episode": 9,
        "words": ["glasses","grumpy","put","without","clearly","bathroom","bedroom","lose","silly","bump","careful"],
        "chunks": [
            ("daddy_glasses", "Daddy's glasses", "爸爸的眼镜", ["glasses"]),
            ("lost_glasses", "lost his glasses", "弄丢了眼镜", ["lose","glasses"]),
            ("without_glasses", "without his glasses", "没戴眼镜", ["without","glasses"]),
            ("look_clearly", "see clearly", "看清楚", ["clearly"]),
            ("in_bathroom", "in the bathroom", "在浴室里", ["bathroom"]),
            ("in_bedroom", "in the bedroom", "在卧室里", ["bedroom"]),
            ("be_careful", "be careful", "小心点", ["careful"]),
            ("feels_grumpy", "feels grumpy", "有点烦躁", ["grumpy"]),
        ],
        "sentences": [
            ("s01","Daddy Pig wears glasses.","猪爸爸戴眼镜。",["daddy","glasses"],["daddy_glasses"]),
            ("s02","Daddy Pig cannot see clearly without his glasses.","猪爸爸没有眼镜就看不清楚。",["clearly","without","glasses"],["without_glasses","look_clearly"]),
            ("s03","Daddy Pig has lost his glasses.","猪爸爸把眼镜弄丢了。",["lose","glasses"],["lost_glasses"]),
            ("s04","Peppa and George help Daddy Pig look for them.","Peppa和George帮爸爸找眼镜。",["help","look"],[]),
            ("s05","Are they in the bathroom?","眼镜在浴室里吗？",["bathroom"],["in_bathroom"]),
            ("s06","Are they in the bedroom?","眼镜在卧室里吗？",["bedroom"],["in_bedroom"]),
            ("s07","Daddy Pig is getting grumpy.","猪爸爸有点烦躁了。",["grumpy"],["feels_grumpy"]),
            ("s08","Daddy Pig bumps into things without his glasses.","猪爸爸没戴眼镜会撞到东西。",["bump","without","glasses"],["without_glasses"]),
            ("s09","Be careful Daddy Pig.","小心点,猪爸爸。",["careful"],["be_careful"]),
            ("s10","Peppa has found Daddy's glasses.","Peppa找到了爸爸的眼镜。",["glasses"],["daddy_glasses"]),
        ],
    },
    "peppa-s01e10": {
        "title": "Gardening", "episode": 10,
        "words": ["grow","seed","plant","strawberry","apple","carrot","choose","tiny","water","bigger","earth","hole","wait"],
        "chunks": [
            ("plant_seeds", "plant seeds", "种种子", ["plant","seed"]),
            ("grow_big", "grow big", "长大", ["grow","bigger"]),
            ("water_plants", "water the plants", "给植物浇水", ["water","plant"]),
            ("dig_hole", "dig a hole", "挖洞", ["hole"]),
            ("in_the_earth", "in the earth", "在泥土里", ["earth"]),
            ("tiny_seed", "tiny seed", "小小种子", ["tiny","seed"]),
            ("choose_seeds", "choose some seeds", "选择种子", ["choose","seed"]),
            ("wait_and_see", "wait and see", "等等看", ["wait","see"]),
        ],
        "sentences": [
            ("s01","Grandpa Pig is gardening.","猪爷爷在园艺。",["garden"],[]),
            ("s02","Peppa and George want to plant seeds.","Peppa和George想种种子。",["plant","seed"],["plant_seeds"]),
            ("s03","They choose some seeds.","他们选择了一些种子。",["choose","seed"],["choose_seeds"]),
            ("s04","The seeds are very tiny.","种子非常小。",["seed","tiny"],["tiny_seed"]),
            ("s05","Grandpa Pig digs a hole in the earth.","猪爷爷在泥土里挖了个洞。",["hole","earth"],["dig_hole","in_the_earth"]),
            ("s06","Peppa waters the seeds.","Peppa给种子浇水。",["water","seed"],["water_plants"]),
            ("s07","Now they must wait.","现在他们必须等待。",["wait"],["wait_and_see"]),
            ("s08","The plants are growing bigger.","植物越长越大。",["plant","grow","bigger"],["grow_big"]),
            ("s09","There are strawberries and carrots.","有草莓和胡萝卜。",["strawberry","carrot"],[]),
            ("s10","An apple tree grows from a seed.","苹果树从种子长出来。",["apple","tree","grow","seed"],["grow_big"]),
        ],
    },
}


def read_transcript(eid):
    rows = []
    path = ROOT / "out" / eid / "transcript.txt"
    for line in path.read_text().splitlines():
        m = re.match(r"\[(\d\d:\d\d:\d\d\.\d+)\]\s+(.*)", line)
        if m:
            rows.append((m.group(1), re.sub(r"\[[^\]]+\]", " ", m.group(2)).strip()))
    return rows


def to_seconds(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def to_stamp(sec):
    sec = max(0, sec)
    h = int(sec // 3600)
    sec -= h * 3600
    m = int(sec // 60)
    s = sec - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def norm_text(s):
    return re.sub(r"[^a-z]+", " ", s.lower())


def find_time(rows, keywords, fallback_idx):
    kws = [k.lower().replace("glasses", "glasse").replace("cookie", "cooky") for k in keywords[:3]]
    best = None
    for i, (start, text) in enumerate(rows):
        nt = norm_text(text)
        score = sum(1 for k in kws if k in nt)
        if score and (best is None or score > best[0] or (score == best[0] and len(text) > len(best[2]))):
            best = (score, start, text, i)
    if best:
        st = to_seconds(best[1])
    else:
        st = 25 + fallback_idx * 18
    return to_stamp(st), to_stamp(st + 4.5)


def sentence_subject(text, meaning):
    return f"a warm story scene from a children's cartoon showing: {meaning}; main action from the sentence '{text}', no text, expressive characters, clear single moment"


def chunk_subject(text, meaning):
    return f"a clear child-friendly illustration of the phrase '{text}' meaning {meaning}, no written words, one simple action, expressive characters"


def main():
    for eid, cfg in EPISODES.items():
        spec_dir = ROOT / "specs" / eid
        spec_dir.mkdir(parents=True, exist_ok=True)
        prompts = {
            "_style": WORD_STYLE,
            "_notes": {"episode": eid, "generated_by": "make_specs_3_10.py"},
            "words": [
                {"lemma": w, "subject": WORD_META[w][1]}
                for w in cfg["words"]
            ],
        }
        meanings = {
            "_note": "Generated L1 meanings for S01E03-E10 starter pass.",
            "words": {w: {"meaning_zh": WORD_META[w][0], "spelling_visible": True} for w in cfg["words"]},
        }
        chunks = {
            "_style": CHUNK_STYLE,
            "chunks": [
                {"id": cid, "text": text, "subject": chunk_subject(text, zh), "meaning_zh": zh, "covers_words": covers}
                for cid, text, zh, covers in cfg["chunks"]
            ],
        }
        rows = read_transcript(eid)
        sent_items = []
        for idx, (sid, text, zh, keys, chunk_ids) in enumerate(cfg["sentences"]):
            start, end = find_time(rows, keys or text.split()[:2], idx)
            sent_items.append({
                "id": sid,
                "text": text,
                "meaning_zh": zh,
                "subject": sentence_subject(text, zh),
                "time_start": start,
                "time_end": end,
                "chunks": chunk_ids,
                "key_words": keys,
            })
        sentences = {"_style": SENT_STYLE, "sentences": sent_items}
        (spec_dir / "prompts.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=2))
        (spec_dir / "words_meaning.json").write_text(json.dumps(meanings, ensure_ascii=False, indent=2))
        (spec_dir / "chunks_prompts.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2))
        (spec_dir / "sentences_prompts.json").write_text(json.dumps(sentences, ensure_ascii=False, indent=2))
        print(eid, "words", len(cfg["words"]), "chunks", len(cfg["chunks"]), "sentences", len(sent_items))


if __name__ == "__main__":
    main()

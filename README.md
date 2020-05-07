# SmartySBot

Telegram timetable bot, for Zhytomyr Ivan Franko State University students. It uses [Politek-soft Dekanat system](https://dekanat.zu.edu.ua/cgi-bin/timetable.cgi?n=999) for getting data. With 500+ active users.

![Politek-soft Dekanat](https://i.imgur.com/VLOoMbw.png)

### Getting started:
1. Add **@ZDU_bot** to your Telegram contacts.
2. Use [this](https://t.me/zdu_bot) link

### How to run locally:
```shell script
git clone https://github.com/0xVK/SmartyScheduleBot.git

cd SmartyScheduleBot 

python3 -m venv VENV

source VENV/bin/activate

pip install -r requirements.txt

!! open file settings.py and set your BOT_TOKEN value

python app.py # to run bot
!! or 
python app.py web # to run web
```


### Bot features:
- Today/tomorrow/all week schedule.
- Schedule by date.
- Schedule by teacher.
- Schedule by group.
- Lessons time info.
- Weather forecast.
- Schedule caching system. Requests are cached to increase speed. It saves about 35% requests to timetable server.

### Screenshots

<img src="https://i.imgur.com/a03uins.jpg" width="270">





<img src="https://i.imgur.com/PBwE2vr.jpg" width="270">

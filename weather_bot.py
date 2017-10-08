# -*- coding: utf-8 -*-

import requests
import datetime
import time


def getEmoji(weather_id):

    # Openweathermap Weather codes and corressponding emojis
    thunderstorm = u'\U0001F4A8'  # Code: 200's, 900, 901, 902, 905
    drizzle = u'\U0001F4A7'  # Code: 300's
    rain = u'\U00002614'  # Code: 500's
    snowflake = u'\U00002744'  # Code: 600's snowflake
    snowman = u'\U000026C4'  # Code: 600's snowman, 903, 906
    atmosphere = u'\U0001F301'  # Code: 700's foogy
    clearSky = u'\U00002600'  # Code: 800 clear sky
    fewClouds = u'\U000026C5'  # Code: 801 sun behind clouds
    clouds = u'\U00002601'  # Code: 802-803-804 clouds general
    hot = u'\U0001F525'  # Code: 904
    defaultEmoji = u'\U0001F300'  # default emojis

    if weather_id:
        if str(weather_id)[0] == '2' or weather_id == 900 or weather_id == 901 or weather_id == 902 or weather_id == 905:
            return thunderstorm
        elif str(weather_id)[0] == '3':
            return drizzle
        elif str(weather_id)[0] == '5':
            return rain
        elif str(weather_id)[0] == '6' or weather_id == 903 or weather_id== 906:
            return snowflake + ' ' + snowman
        elif str(weather_id)[0] == '7':
            return atmosphere
        elif weather_id == 800:
            return clearSky
        elif weather_id == 801:
            return fewClouds
        elif weather_id == 802 or weather_id == 803 or weather_id == 803:
            return clouds
        elif weather_id == 904:
            return hot
        else:
            return defaultEmoji    # Default emoji

    else:
        return defaultEmoji  # Default emoji


def render_forecast(date, temp, weather_emoji, desc):

    clocks_emoji = {
        9:  '\U0001F558',
        12: '\U0001F55B',
        15: '\U0001F552',
        18: '\U0001F555',
        21: '\U0001F558',
    }

    r = ''

    r += '{} {} - \U0001F321{}\U000000B0 {} <i>{}</i>\n'.\
        format(clocks_emoji[date.hour], date.strftime('%H:%M'), int(temp), weather_emoji, desc)

    return r


def update_forecast():

    API_LINK_FORECAST = 'http://api.openweathermap.org/data/2.5/forecast'

    request_params = {
        'APPID': '<APP_ID>',
        'id': '686967',  # Zhytomyr ID
        'units': 'metric',
        'lang': 'uk'
    }

    r = requests.get(API_LINK_FORECAST, params=request_params)
    five_days_weather_forecast = r.json()

    today_day = datetime.datetime.now().day
    tomorrow_date = datetime.datetime.now() + datetime.timedelta(days=1)
    tomorrow_day = tomorrow_date.day

    hidden_hours = [0, 3, 6]

    result = ''
    result += ':::::: \U0001F30E <b>Сьогодні:</b> ::::::\n'
    for hour_forecast in five_days_weather_forecast['list']:

        forecast_time = datetime.datetime.fromtimestamp(hour_forecast['dt'])

        if forecast_time.day == today_day:
            if forecast_time.hour not in hidden_hours:
                result += render_forecast(forecast_time,
                                          hour_forecast['main']['temp'],
                                          getEmoji(hour_forecast['weather'][0]['id']),
                                          hour_forecast['weather'][0]['description'])

    result += '\n:::::: \U0001F30E <b>Завтра:</b> ::::::\n'
    for hour_forecast in five_days_weather_forecast['list']:

        forecast_time = datetime.datetime.fromtimestamp(hour_forecast['dt'])

        if forecast_time.day == tomorrow_day:
            if forecast_time.hour not in hidden_hours:
                result += render_forecast(forecast_time,
                                          hour_forecast['main']['temp'],
                                          getEmoji(hour_forecast['weather'][0]['id']),
                                          hour_forecast['weather'][0]['description'])

    with open('forecast.txt', 'w') as f_file:
        f_file.write(result)


def log(m=''):

    now_time = datetime.datetime.now().strftime('%d-%m %H:%M:%S')

    with open('bot_log.txt', 'a') as log_file:

        log_file.write('[{}]: (Server) > {}\n'.format(now_time, m))

if __name__ == '__main__':

    while True:

        update_forecast()
        log('Оновлено погоду')
        time.sleep(10800)  # 3 hours


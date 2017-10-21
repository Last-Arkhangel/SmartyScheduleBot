# -*- coding: utf-8 -*-
import cache
import settings
import requests

cache_items_count = len(cache.Cache.get_keys() or '')
cache.Cache.clear_cache()

for admin in settings.ADMINS_ID:

    data = {
        'chat_id': admin,
        'text': 'Cache cleaned. Deleted {} records.'.format(cache_items_count)
    }

    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)

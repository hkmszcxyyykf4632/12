"""Keep the requested bookmaker separate from secondary-source observations."""
import re

PREFERRED = '澳门彩票有限公司'
ALIASES = {'macauslot', 'macaoslot', '澳彩', '澳门', '澳門', '澳门彩票有限公司', '澳門彩票有限公司', '澳门彩票', '澳門彩票'}


def preferred(quote):
    name = re.sub(r'[\s._-]+', '', str(quote.get('provider', '')).casefold())
    return name in ALIASES


def policy(quotes):
    primary = [q for q in quotes if preferred(q)]
    chosen = primary or list(quotes)
    providers = sorted({q['provider'] for q in chosen})
    return chosen, {'preferredProvider': PREFERRED, 'usingPreferred': bool(primary),
                    'actualProviders': providers,
                    'note': ('本次以澳门彩票有限公司报价为分析参考；变盘只比较同来源、同市场。' if primary else
                             '本场尚未取得可核对的澳门彩票有限公司最新报价；当前记录为其他来源参考，不能代表澳门盘。')}

from ..scrapper import Scrapper
import inspect

class Facebook():
    def __init__(self, user: str, mentions: bool = True, recent: bool = False):
        self.url = f'https://www.facebook.com/{user}'
        if mentions:
            self.url += '/mentions'

        self.recent = recent
        pass

    def __str__(self):
        return f"Facebook({self.url})"

    async def start(self, Scrapper: Scrapper):
        await Scrapper.open(self.url)

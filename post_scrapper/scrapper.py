import os
import logging
import asyncio
from patchright.async_api import async_playwright, Browser, BrowserContext, Page

log = logging.getLogger("Scrapper")
formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s', "%H:%M:%S")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
log.addHandler(ch)



class Scrapper:
    def __init__(self, headless: bool = False, user_data_dir: str = "./chromedata", log_level=logging.INFO):
        self.headless = headless
        self.user_data_dir = os.path.abspath(user_data_dir)
        self._pw_ctx = None
        self._playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._target = None
        log.setLevel(log_level)

    async def __aenter__(self) -> "Scrapper":
        self._pw_ctx = async_playwright()
        self._playwright = await self._pw_ctx.__aenter__()
        log.debug(f"Launching persistent context with user_data_dir={self.user_data_dir}, headless={self.headless}")
        self.context = await self._playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            channel="chrome",
            headless=self.headless,
            no_viewport=True
        )
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.browser = None
        log.info("Stealth Scrapper ready!")
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        # allow manual interaction before closing: do not block event loop
        loop = asyncio.get_running_loop()
        prompt = "Code is finished; Press enter to exit. Type 'debug' to enable debug mode for exit: "
        inp = await loop.run_in_executor(None, input, prompt)
        if isinstance(inp, str) and inp.lower() == "debug":
            log.setLevel(logging.DEBUG)


        log.debug("Exiting Scrapper context")
        if self.context:
            await self.context.close()
            log.debug("Closed context")
        if self._pw_ctx:
            await self._pw_ctx.__aexit__(exc_t, exc_v, exc_tb)
            log.debug("Closed playwright")
        log.info("Scrapper closed!")




    async def close(self):
        await self.__aexit__(None, None, None)

    async def open(self, url):
        log.debug(f"Opening page: {url}")
        page = await self.page.goto(url)
        if not (200 <= page.status < 300):
            log.warning(f"{url} : {page.status}")
        else:
            log.info(f"{url} : {page.status}")

        
    async def setJob(self, target):
        """Assign the target job to run (instance, class, or module)."""
        self._target = target
        log.debug(f"Target job assigned: {self._target}")

    async def start(self):
        if not self._target:
            raise RuntimeError("No target job assigned")
        log.debug(f"Target job is assigned: {self._target}")

        log.info(f"Starting target job: {self._target}")
        await self._target.start(self)
        log.info(f"Target job completed: {self._target}")
    


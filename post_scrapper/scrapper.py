import subprocess
import requests
import asyncio
import os
import logging
from playwright.async_api import Browser, BrowserContext, Page
from playwright_stealth import Stealth
from playwright.async_api import async_playwright

log = logging.getLogger("Scrapper")
formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s', "%H:%M:%S")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
log.addHandler(ch)


def open_chrome(port: int):
    log.debug(f"Launching Chrome on port {port}")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    data_dir = os.path.join(os.getcwd(), "chromedata")
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={data_dir}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    log.debug(f"Starting Chrome subprocess: {cmd}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log.debug(f"Chrome process started with PID {proc.pid}")
    return proc


class Scrapper:
    def __init__(self, port=9222, log_level=logging.INFO):
        log.debug(f"Scrapper.__init__ called with port={port}")
        self.port = port
        self.page: Page | None = None
        self.context: BrowserContext | None = None
        self.browser: Browser | None = None
        self._plugin_ctx = None
        self._playwright = None
        self._chrome_proc = None
        self._target = None

        log.setLevel(log_level)

    async def wait_cdp(self, timeout=15):
        log.debug(f"Waiting up to {timeout}s for CDP endpoint on port {self.port}...")
        start = asyncio.get_event_loop().time()
        while True:
            try:
                resp = requests.get(f"http://localhost:{self.port}/json/version", timeout=1)
                resp.raise_for_status()
                data = resp.json()
                ws_url = data.get("webSocketDebuggerUrl")
                log.debug(f"Found CDP websocket URL: {ws_url}")
                return ws_url
            except Exception:
                if asyncio.get_event_loop().time() - start > timeout:
                    raise TimeoutError("Could not connect to Chrome CDP endpoint.")
                await asyncio.sleep(0.5)

    async def __aenter__(self) -> "Scrapper":
        log.debug("Entering Scrapper context manager")
        # Launch Chrome if not already running
        try:
            requests.get(f"http://localhost:{self.port}/json/version", timeout=1)
        except Exception:
            log.debug("Chrome isn't running; launching it.")
            self._chrome_proc = open_chrome(self.port)

        ws = await self.wait_cdp()
        log.debug(f"Connecting to CDP websocket: {ws}")

        log.debug("Initializing Playwright stealth plugin")
        self._plugin_ctx = Stealth().use_async(async_playwright())
        self._playwright = await self._plugin_ctx.__aenter__()
        log.debug("Stealth plugin context entered; Playwright ready")

        log.debug("Connecting Chromium over CDP")
        try:
            self.browser = await self._playwright.chromium.connect_over_cdp(ws)
            log.debug(f"Connected to Chromium browser via CDP; Browser object: {self.browser}")
        except Exception as e:
            log.error("Failed to connect to Chromium over CDP", exc_info=e)
            raise
        if self.browser:
            contexts = self.browser.contexts
            log.debug(f"Existing browser contexts count: {len(contexts)}")
            self.context = contexts[0] if contexts else await self.browser.new_context()
            log.debug(f"Using browser context: {self.context}")
            pages = self.context.pages
            log.debug(f"Existing pages count in context: {len(pages)}")
            self.page = pages[0] if pages else await self.context.new_page()
            log.debug(f"Page ready: {self.page}")
            log.info("Stealth Scrapper ready!")
            return self
        else:
            raise RuntimeError("Failed to initialize Playwright")

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        log.debug("Exiting Scrapper context manager")

        if self.context:
            log.debug(f"Closing browser context: {self.context}")
            try:
                await self.context.close()
                log.debug("Browser context closed")
            except Exception as e:
                log.error("Error closing browser context", exc_info=e)

        if self.browser:
            log.debug(f"Closing browser: {self.browser}")
            try:
                await self.browser.close()
                log.debug("Browser closed")
            except Exception as e:
                log.error("Error closing browser", exc_info=e)

        if self._plugin_ctx:
            log.debug("Exiting stealth plugin context")
            try:
                await self._plugin_ctx.__aexit__(exc_t, exc_v, exc_tb)
                log.debug("Stealth plugin context exited")
            except Exception as e:
                log.error("Error exiting stealth plugin context", exc_info=e)

        if self._chrome_proc:
            log.debug(f"Terminating Chrome process PID {self._chrome_proc.pid}")
            try:
                self._chrome_proc.terminate()
                self._chrome_proc.wait(timeout=5)
                log.debug("Chrome process terminated")
            except Exception as e:
                log.error("Error terminating Chrome process", exc_info=e)

        input("Press enter to exit...")



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

    async def start(self):
        if not self._target:
            raise RuntimeError("No target job assigned")

        log.info(f"Starting target job: {self._target}")
        await self._target.start(self)
        log.info(f"Target job completed: {self._target}")
    


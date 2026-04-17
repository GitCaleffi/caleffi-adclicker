import random
import subprocess
import sys
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor, wait
from datetime import datetime
from itertools import cycle
from pathlib import Path
from time import sleep
from typing import Optional

from adb import adb_controller
from config_reader import config
from logger import logger
from proxy import get_proxies
from utils import get_queries


def _inside_running_interval() -> bool:
    start_str = config.behavior.running_interval_start
    end_str = config.behavior.running_interval_end
    if start_str == "00:00" and end_str == "00:00":
        return True
    start = datetime.strptime(start_str, "%H:%M").time()
    end = datetime.strptime(end_str, "%H:%M").time()
    return start <= datetime.now().time() <= end


def _persistent_worker(
    browser_id: int,
    queries: list,
    proxy_cycle,
    proxy_lock: threading.Lock,
    device_id: Optional[str],
) -> None:
    """Persistent browser worker: restarts automatically after each session.
    Each browser slot runs independently — no waiting for other browsers.
    """
    q_idx = browser_id - 1  # stagger initial query across browsers
    while True:
        if not _inside_running_interval():
            logger.info(f"[Browser {browser_id}] Outside running interval. Waiting 60s...")
            sleep(60)
            continue

        query = queries[q_idx % len(queries)]
        q_idx += 1

        with proxy_lock:
            proxy = next(proxy_cycle)

        start_tool(browser_id, query, proxy, start_timeout=0, device_id=device_id)

        wait_time = config.behavior.loop_wait_time
        logger.info(f"[Browser {browser_id}] Session complete. Restarting in {wait_time}s...")
        sleep(wait_time)


def start_tool(
    browser_id: int, query: str, proxy: str, start_timeout: float, device_id: Optional[str] = None
) -> None:
    """Start the tool

    :type browser_id: int
    :param browser_id: Browser id to separate instances in log for multiprocess runs
    :type query: str
    :param query: Search query
    :type proxy: str
    :param proxy: Proxy to use in ip:port or user:pass@host:port format
    :type start_timeout: float
    :param start_timeout: Start timeout to avoid race condition in driver patching
    :type device_id: str
    :param device_id: Android device ID to assign
    """

    sleep(start_timeout * config.behavior.wait_factor)

    if getattr(sys, "frozen", False):
        # reinvoke the same EXE and dispatch into ad_clicker.main
        command = [sys.executable, "--ad-clicker"]
    else:
        # command line mode: run the script like before
        command = [sys.executable, "ad_clicker.py"]

    command.extend(["-q", query, "-p", proxy, "--id", str(browser_id)])

    if device_id:
        command.extend(["-d", device_id])

    subprocess.run(command)


def main() -> None:

    multi_browser_flag_file = Path(".MULTI_BROWSERS_IN_USE")
    multi_browser_flag_file.unlink(missing_ok=True)

    MAX_WORKERS = config.behavior.browser_count

    if MAX_WORKERS > 1:
        logger.debug(f"Creating {multi_browser_flag_file} flag file...")
        multi_browser_flag_file.touch()

    if config.paths.query_file:
        queries = get_queries()

        if config.behavior.multiprocess_style == 1:
            random.shuffle(queries)

        query = cycle(queries) if len(queries) <= MAX_WORKERS else iter(queries)
    else:
        raise SystemExit("Missing query_file parameter!")

    if config.paths.proxy_file:
        proxies = get_proxies()
        random.shuffle(proxies)
        proxy = cycle(proxies) if len(proxies) <= MAX_WORKERS else iter(proxies)
    else:
        raise SystemExit("Missing proxy_file parameter!")

    if config.behavior.send_to_android:
        adb_controller.get_connected_devices()
        devices = adb_controller.devices
        random.shuffle(devices)
        device_ids = devices + [None] * (MAX_WORKERS - len(devices))
    else:
        device_ids = [None] * MAX_WORKERS

    logger.info(f"Running with {MAX_WORKERS} browser{'s' if MAX_WORKERS > 1 else ''}...")

    # 1st way - persistent pool: each browser restarts independently (default)
    if config.behavior.multiprocess_style == 1:
        proxy_lock = threading.Lock()
        threads = [
            threading.Thread(
                target=_persistent_worker,
                args=(i, queries, proxy, proxy_lock, device_ids[i - 1]),
                daemon=True,
                name=f"browser-{i}",
            )
            for i in range(1, MAX_WORKERS + 1)
        ]

        for i, t in enumerate(threads):
            t.start()
            sleep(0.5)  # stagger avoids race condition in chromedriver patching

        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            logger.info("Persistent pool interrupted by user.")
        finally:
            multi_browser_flag_file.unlink(missing_ok=True)

    # 2nd way - same query on each browser
    elif config.behavior.multiprocess_style == 2:
        for query in queries:
            proxies = get_proxies()
            random.shuffle(proxies)
            proxy = cycle(proxies)

            if config.behavior.send_to_android:
                devices = adb_controller.devices
                random.shuffle(devices)
                device_ids = devices + [None] * (MAX_WORKERS - len(devices))

            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [
                    executor.submit(
                        start_tool,
                        i,
                        query,
                        next(proxy),
                        start_timeout=i * 0.5,
                        device_id=device_ids[i - 1],
                    )
                    for i in range(1, MAX_WORKERS + 1)
                ]

                # wait for all tasks to complete
                _, _ = wait(futures)

    else:
        logger.error("Invalid multiprocess style!")


if __name__ == "__main__":
    try:
        main()

    except Exception as exp:
        logger.error("Exception occurred. See the details in the log file.")

        message = str(exp).split("\n")[0]
        logger.debug(f"Exception: {message}")
        details = traceback.format_tb(exp.__traceback__)
        logger.debug(f"Exception details: \n{''.join(details)}")

        logger.debug(f"Exception cause: {exp.__cause__}") if exp.__cause__ else None

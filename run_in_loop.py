import traceback
import subprocess
import sys
from time import sleep
from datetime import datetime

from logger import logger
from config_reader import config


def _inside_running_interval() -> bool:
    """Check if the current time is in the running interval

    :rtype: bool
    :returns: Whether the current time is in the running interval or not
    """

    start_time_str = config.behavior.running_interval_start
    end_time_str = config.behavior.running_interval_end

    if start_time_str == "00:00" and end_time_str == "00:00":
        return True

    start_time = datetime.strptime(start_time_str, "%H:%M").time()
    end_time = datetime.strptime(end_time_str, "%H:%M").time()

    if start_time > end_time:
        raise SystemExit("Start time must be before the end time!")

    now = datetime.now().time()

    current_hour = now.hour

    if current_hour == start_time.hour and current_hour == end_time.hour:
        if end_time.minute - start_time.minute < 10:
            raise SystemExit("There should be at least 10 minutes between the start and end!")

    return start_time <= now <= end_time


def main() -> None:

    if getattr(sys, "frozen", False):
        # reinvoke the same EXE and dispatch into run_ad_clicker.main
        command = [sys.executable, "--run-ad-clicker"]
    else:
        # command line mode: run the script like before
        command = [sys.executable, "run_ad_clicker.py"]

    # run_ad_clicker.py now manages its own persistent pool internally.
    # It runs until killed — if it exits unexpectedly, we restart it.
    while True:
        subprocess.run(command)
        logger.info("run_ad_clicker exited unexpectedly. Restarting in 10s...")
        sleep(10)


if __name__ == "__main__":

    try:
        main()
    except Exception as exp:
        logger.error("Exception occurred. See the details in the log file.")

        message = str(exp).split("\n")[0]
        logger.debug(f"Exception: {message}")
        details = traceback.format_tb(exp.__traceback__)
        logger.debug(f"Exception details: \n{''.join(details)}")

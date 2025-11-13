import sys
import time

from loguru import logger

# 1. Add logging to stdout
logger.add(sys.stdout, level="INFO")

# 2. Add logging to a file
logger.add(
    "app.log",
    rotation="1 MB",  # Create a new file when it reaches 1 MB
    retention="7 days",  # Keep logs for 7 days
    compression="zip",  # Compress old logs automatically
)


def process_data(x):
    logger.debug(f"Starting process_data with x={x}")
    y = 1 / 0  # force zero division error
    return x * 2


def main():
    logger.info("Program started")

    for i in range(3):
        result = process_data(i)
        logger.info(f"Result for {i}: {result}")
        time.sleep(0.2)

    logger.success("Program finished successfully!")


# Log uncaught exceptions automatically
@logger.catch
def run():
    main()


run()

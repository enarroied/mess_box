from loguru import logger


def divide(a, b):
    try:
        logger.info(f"Dividing {a} by {b}")
        result = a / b
    except ZeroDivisionError as e:
        logger.error(f"Cannot divide by zero: {e}")
        result = None
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        result = None
    finally:
        logger.info("Division attempt complete.")
    return result


divide(10, 2)
divide(10, 0)

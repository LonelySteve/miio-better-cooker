import logging

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s", level=logging.INFO
)

main_logger = logging.getLogger("main")
cooker_logger = logging.getLogger("cooker")
bark_logger = logging.getLogger("bark")

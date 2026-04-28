import logging

# from uvicorn.logging import DefaultFormatter

handler = logging.StreamHandler()
# handler.setFormatter(
#     DefaultFormatter(fmt="%(levelprefix)s %(message)s", use_colors=True)
# )

logger = logging.getLogger("fastapi-insights")
# logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)
# logger.propagate = False

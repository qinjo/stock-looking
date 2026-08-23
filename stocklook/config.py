DEFAULT_STOCKS = ["600519", "000001", "300750", "600036", "601318"]

HORIZON = 1

THRESHOLD = 0.0

START_DATE = "20150101"

ADJUST = "qfq"

MIN_TRAIN_DAYS = 500

WALK_STEP = 60

CACHE_DIR = ".cache"


def _load_env():
    """从 .env 读配置（如 DEEPSEEK_API_KEY），不覆盖已有的环境变量；文件不存在则静默跳过。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:
        pass


_load_env()

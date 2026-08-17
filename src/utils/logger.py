import logging
import json
import sys
from datetime import datetime
from pathlib import Path


def get_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    İsimlendirilmiş logger oluşturur.
    Her modül kendi logger'ını alır:
        logger = get_logger("gmail")
        logger.info("3 yeni mail çekildi")
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"briefme.{name}")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Konsol formatı (geliştirirken görürsün)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Dosya formatı (daha detaylı)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsola yaz (Windows'ta varsayılan konsol kod sayfası Türkçe
    # karakterleri bozduğu için StreamHandler'ın kullandığı stderr'i
    # UTF-8'e zorluyoruz — StreamHandler(), argümansız çağrıldığında
    # stdout'a değil stderr'e yazar)
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_fmt)

    # Dosyaya yaz
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(log_path / f"{today}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)

    # Hata dosyasına yaz
    eh = logging.FileHandler(log_path / f"{today}_errors.log", encoding="utf-8")
    eh.setLevel(logging.ERROR)
    eh.setFormatter(file_fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.addHandler(eh)

    return logger


def log_event(logger: logging.Logger, event: str, data: dict = None) -> None:
    """
    JSON formatında event log'u.
    Kullanım:
        log_event(logger, "EMAIL_FETCHED", {"count": 42})
    """
    payload = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        **(data or {}),
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
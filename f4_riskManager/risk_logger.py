"""
F4 RiskLogger - 리스크/상태/이벤트 로그 및 알림
"""
import logging

class RiskLogger:
    def __init__(self, log_path):
        self.logger = logging.getLogger("F4_risk_manager")
        fh = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s [F4] %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.INFO)

    def info(self, msg): self.logger.info(msg)
    def warn(self, msg): self.logger.warning(msg)
    def critical(self, msg): self.logger.critical(msg)

import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [F3] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

def entry(signal: Dict[str, Any]) -> None:
    """Handle entry signal.

    This placeholder simply logs the incoming signal. In a real system this
    function would submit orders, manage positions and update state machines.
    """
    logging.info("[F3] Received signal: %s", signal)


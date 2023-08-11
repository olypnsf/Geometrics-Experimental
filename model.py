from typing import Any, List, Optional, Dict, Tuple
import logging
import datetime
import math
from enum import Enum
from timer import Timer
from config import Configuration
from urllib.parse import urljoin
from collections import defaultdict

logger = logging.getLogger(__name__)

class Player:
    """Store information about a player."""

    def __init__(self, player_info: Dict[str, Any]) -> None:
        self.name: str = player_info.get("name", "")
        self.title = player_info.get("title")
        self.is_bot = self.title == "BOT"
        self.rating = player_info.get("rating")
        self.provisional = player_info.get("provisional")
        self.aiLevel = player_info.get("aiLevel")

    def __str__(self) -> str:
        if self.aiLevel:
            return f"AI level {self.aiLevel}"
        else:
            rating = f'{self.rating}{"?" if self.provisional else ""}'
            return f'{self.title or ""} {self.name} ({rating})'.strip()

    def __repr__(self) -> str:
        return self.__str__()

class Termination(str, Enum):
    """The possible game terminations."""
    MATE = "mate"
    TIMEOUT = "outoftime"
    RESIGN = "resign"
    ABORT = "aborted"
    DRAW = "draw"

class Challenge:
    """Store information about a challenge."""

    def __init__(self, challenge_info: Dict[str, Any], user_profile: Dict[str, Any]) -> None:
        self.id = challenge_info["id"]
        self.rated = challenge_info["rated"]
        self.variant = challenge_info["variant"]["key"]
        self.perf_name = challenge_info["perf"]["name"]
        self.speed = challenge_info["speed"]
        self.increment: int = challenge_info.get("timeControl", {}).get("increment")
        self.base: int = challenge_info.get("timeControl", {}).get("limit")
        self.days: int = challenge_info.get("timeControl", {}).get("daysPerTurn")
        self.challenger = Player(challenge_info.get("challenger") or {})
        self.opponent = Player(challenge_info.get("destUser") or {})
        self.from_self = self.challenger.name == user_profile["username"]

    # ... (The rest of the Challenge class remains unchanged)

class Game:
    """Store information about a game."""

    def __init__(
        self, game_info: Dict[str, Any], username: str, base_url: str, abort_time: int
    ) -> None:
        self.username = username
        self.id: str = game_info["id"]
        self.speed = game_info.get("speed")
        clock = game_info.get("clock") or {}
        ten_years_in_ms = 1000 * 3600 * 24 * 365 * 10
        self.clock_initial = clock.get("initial", ten_years_in_ms)
        self.clock_increment = clock.get("increment", 0)
        self.perf_name = (game_info.get("perf") or {}).get("name", "{perf?}")
        self.variant_name = game_info["variant"]["name"]
        self.mode = "rated" if game_info.get("rated") else "casual"

    # ... (The rest of the Game class remains unchanged)

# The rest of your code remains unchanged.

# Example usage
user_profile = {
    "username": "your_username"
}
challenge_info = {
    # ... (Provide challenge info here)
}
game_info = {
    # ... (Provide game info here)
}
challenge = Challenge(challenge_info, user_profile)
game = Game(game_info, user_profile["username"], "base_url", 123456)

# You can now work with the challenge and game objects as needed.


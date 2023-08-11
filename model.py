from typing import Any, List, Optional, Dict
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

    def is_supported_variant(self, challenge_cfg: Configuration) -> bool:
        return self.variant in challenge_cfg.variants

    def is_supported_time_control(self, challenge_cfg: Configuration) -> bool:
        speeds = challenge_cfg.time_controls
        increment_max: int = challenge_cfg.max_increment
        increment_min: int = challenge_cfg.min_increment
        base_max: int = challenge_cfg.max_base
        base_min: int = challenge_cfg.min_base
        days_max: int = challenge_cfg.max_days
        days_min: int = challenge_cfg.min_days

        if self.speed not in speeds:
            return False

        if self.base is not None and self.increment is not None:
            return increment_min <= self.increment <= increment_max and base_min <= self.base <= base_max
        elif self.days is not None:
            return days_min <= self.days <= days_max
        else:
            return days_max == math.inf

    def is_supported_mode(self, challenge_cfg: Configuration) -> bool:
        return ("rated" if self.rated else "casual") in challenge_cfg.modes

    def is_supported_recent(self, config: Configuration, recent_bot_challenges: defaultdict[str, List[Timer]]) -> bool:
        recent_bot_challenges[self.challenger.name] = [
            timer for timer in recent_bot_challenges[self.challenger.name] if not timer.is_expired()]
        max_recent_challenges = config.max_recent_bot_challenges
        return (
            not self.challenger.is_bot
            or max_recent_challenges is None
            or len(recent_bot_challenges[self.challenger.name]) < max_recent_challenges
        )

    def decline_due_to(self, requirement_met: bool, decline_reason: str) -> str:
        return "" if requirement_met else decline_reason

    def is_supported(self, config: Configuration, recent_bot_challenges: defaultdict[str, List[Timer]]) -> Tuple[bool, str]:
        try:
            if self.from_self:
                return True, ""

            allowed_opponents: List[str] = list(filter(None, config.allow_list)) or [self.challenger.name]
            decline_reason = (
                self.decline_due_to(config.accept_bot or not self.challenger.is_bot, "noBot")
                or self.decline_due_to(not config.only_bot or self.challenger.is_bot, "onlyBot")
                or self.decline_due_to(self.is_supported_time_control(config), "timeControl")
                or self.decline_due_to(self.is_supported_variant(config), "variant")
                or self.decline_due_to(
                    self.is_supported_mode(config), "casual" if self.rated else "rated"
                )
                or self.decline_due_to(
                    self.challenger.name not in config.block_list, "generic"
                )
                or self.decline_due_to(
                    self.challenger.name in allowed_opponents, "generic"
                )
                or self.decline_due_to(
                    self.is_supported_recent(config, recent_bot_challenges), "later"
                )
            )

            return not decline_reason, decline_reason

        except Exception:
            logger.exception(f"Error while checking challenge {self.id}:")
            return False, "generic"

    def score(self) -> int:
        rated_bonus = 200 if self.rated else 0
        challenger_master_title = (
            self.challenger.title if not self.challenger.is_bot else None
        )
        titled_bonus = 200 if challenger_master_title else 0
        challenger_rating_int = self.challenger.rating or 0
        return challenger_rating_int + rated_bonus + titled_bonus

    def mode(self) -> str:
        return "rated" if self.rated else "casual"

    def __str__(self) -> str:
        return f"{self.perf_name} {self.mode()} challenge from {self.challenger} ({self.id})"

    def __repr__(self) -> str:
        return self.__str__()


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
        self.mode = "rated" if game_info.get("rated


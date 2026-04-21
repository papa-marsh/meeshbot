from .help import help
from .ping import ping
from .reminders import reminders, remindme
from .roll import roll
from .scoreboard import scoreboard, scoreboard_all
from .sync import sync
from .what_is_jeff import what_is_jeff
from .what_is_sam import what_is_sam

__all__ = [
    help.__name__,
    ping.__name__,
    reminders.__name__,
    remindme.__name__,
    roll.__name__,
    scoreboard.__name__,
    scoreboard_all.__name__,
    sync.__name__,
    what_is_sam.__name__,
    what_is_jeff.__name__,
]

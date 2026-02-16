"""Project configuration"""

# --- Colors (HEX) ---
frameColor: str = "#6f42f5"  # table frame color
pointsColor: str = ""  # points color in the table
logColor: str = "#404040"  # informational messages color
warnColor: str = "#b84c44"  # warnings and errors color

# --- Parallelism ---
threadCount: int = 3  # number of parallel profiles

# --- Delays (hh:mm:ss) ---
startDelay: list[str] = [  # random delay range before starting the next profile
    "00:00:01",
    "00:00:05",
]

messageDelay: list[str] = [  # delay range between messages
    "00:00:00",
    "00:00:02",
]

# --- Retries ---
retries: int = 5  # number of retry attempts

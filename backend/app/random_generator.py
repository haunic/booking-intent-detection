"""Coherent random test-session generator with optional intent profiles.

The intent profile biases the *shape* of the generated data (convergence vs
exploration, advance window). It never sets the prediction result.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Literal

from .models import (
    Channel,
    ChatMessage,
    ConversationalInput,
    FlightSearch,
    SearchMode,
    Session,
    TraditionalInput,
)

# Small local IATA reference list (valid-looking 3-letter codes).
AIRPORTS = [
    ("NCE", "Nice"), ("CDG", "Paris"), ("LHR", "London"), ("JFK", "New York"),
    ("BKK", "Bangkok"), ("DXB", "Dubai"), ("SIN", "Singapore"), ("LAX", "Los Angeles"),
    ("FCO", "Rome"), ("BCN", "Barcelona"), ("AMS", "Amsterdam"), ("MAD", "Madrid"),
    ("IST", "Istanbul"), ("HND", "Tokyo"), ("SYD", "Sydney"), ("GRU", "Sao Paulo"),
]

Profile = Literal["random", "high", "medium", "low"]


def _pick_two_airports() -> tuple[tuple[str, str], tuple[str, str]]:
    a, b = random.sample(AIRPORTS, 2)
    return a, b


def _rand_adults_children() -> tuple[int, int]:
    adults = random.choices([1, 2, 3, 4], weights=[5, 6, 2, 1])[0]
    children = random.choices([0, 1, 2], weights=[7, 2, 1])[0]
    return adults, children


def _normalize_profile(profile: str) -> Profile:
    p = (profile or "random").strip().lower()
    if p in ("high", "likely high"):
        return "high"
    if p in ("medium", "likely medium"):
        return "medium"
    if p in ("low", "likely low"):
        return "low"
    if p == "random":
        return "random"
    return "random"


def _resolve_profile(profile: str) -> Profile:
    p = _normalize_profile(profile)
    if p == "random":
        return random.choice(["high", "medium", "low"])
    return p


def _advance_window_days(profile: Profile) -> int:
    if profile == "high":
        return random.randint(2, 10)        # near-term
    if profile == "medium":
        return random.randint(14, 45)
    return random.randint(90, 240)          # far in advance for low


def _stay_length(profile: Profile) -> int:
    if profile == "high":
        return random.randint(3, 10)
    if profile == "medium":
        return random.randint(5, 14)
    return random.randint(7, 21)


def _gen_traditional(profile: Profile, browsing: date) -> TraditionalInput:
    (orig_code, _), (dest_code, _) = _pick_two_airports()
    adults, children = _rand_adults_children()

    advance = _advance_window_days(profile)
    dep = browsing + timedelta(days=advance)
    stay = _stay_length(profile)
    ret = dep + timedelta(days=stay)

    current = FlightSearch(
        origin=orig_code,
        destination=dest_code,
        departure_date=dep.isoformat(),
        return_date=ret.isoformat(),
        adults=adults,
        children=children,
    )

    previous: list[FlightSearch] = []
    n_prev = random.randint(1, 4)

    for _ in range(n_prev):
        if profile == "high":
            # Convergence: repeat the (near) identical query.
            prev = FlightSearch(
                origin=orig_code,
                destination=dest_code,
                departure_date=dep.isoformat(),
                return_date=ret.isoformat(),
                adults=adults,
                children=children,
            )
        elif profile == "medium":
            # Same route, small date variations (+/- a few days).
            jitter = random.randint(-4, 4)
            p_dep = dep + timedelta(days=jitter)
            p_ret = p_dep + timedelta(days=stay + random.randint(-2, 2))
            prev = FlightSearch(
                origin=orig_code,
                destination=dest_code,
                departure_date=p_dep.isoformat(),
                return_date=p_ret.isoformat(),
                adults=adults,
                children=children,
            )
        else:
            # Low: broad exploration, different destinations and big date shifts.
            (po_code, _), (pd_code, _) = _pick_two_airports()
            p_dep = browsing + timedelta(days=random.randint(60, 300))
            p_ret = p_dep + timedelta(days=random.randint(5, 25))
            prev = FlightSearch(
                origin=po_code,
                destination=pd_code,
                departure_date=p_dep.isoformat(),
                return_date=p_ret.isoformat(),
                adults=random.randint(1, 3),
                children=random.randint(0, 2),
            )
        previous.append(prev)

    return TraditionalInput(previous_searches=previous, current_search=current)


def _gen_conversational(profile: Profile, browsing: date) -> ConversationalInput:
    (orig_code, orig_city), (dest_code, dest_city) = _pick_two_airports()
    adults, children = _rand_adults_children()
    advance = _advance_window_days(profile)
    dep = browsing + timedelta(days=advance)
    stay = _stay_length(profile)
    pax = f"{adults} adult" + ("s" if adults != 1 else "") + (
        f" and {children} child" + ("ren" if children != 1 else "") if children else ""
    )

    previous: list[ChatMessage] = []
    if profile == "high":
        previous = [
            ChatMessage(text=f"I need to fly from {orig_city} to {dest_city} on {dep.isoformat()} for {pax}."),
            ChatMessage(text=f"Can you confirm a return about {stay} days later? I'd like to book soon."),
        ]
        current = (
            f"Please find the exact return flight {orig_city} to {dest_city} departing {dep.isoformat()}, "
            f"returning {(dep + timedelta(days=stay)).isoformat()} for {pax}. Ready to book."
        )
    elif profile == "medium":
        previous = [
            ChatMessage(text=f"Looking at flights from {orig_city} to {dest_city} sometime next month for {pax}."),
            ChatMessage(text="Could you compare a few departure dates within the same week?"),
        ]
        current = (
            f"Show me {orig_city} to {dest_city} options around {dep.isoformat()}, flexible by a few days, "
            f"roughly a {stay}-day trip."
        )
    else:
        (alt_code, alt_city) = random.choice([a for a in AIRPORTS if a[0] != orig_code])
        previous = [
            ChatMessage(text=f"Just dreaming about a trip somewhere warm later this year for {pax}."),
            ChatMessage(text=f"Maybe {dest_city}, or possibly {alt_city}? Not sure on dates yet."),
        ]
        current = (
            f"What are some ideas for a holiday from {orig_city}? Open to {dest_city} or elsewhere, "
            f"sometime in the next several months, flexible on everything."
        )

    return ConversationalInput(previous_messages=previous, current_request=current)


def generate_session(mode: str, profile: str = "random") -> Session:
    resolved = _resolve_profile(profile)
    browsing = date.today()
    local_time = f"{random.randint(7, 22):02d}:{random.choice(['00', '15', '30', '45'])}"
    channel = random.choice(list(Channel))
    tz = random.choice(["UTC+00:00", "UTC+01:00", "UTC+02:00", "UTC-05:00", "UTC+07:00", "UTC+09:00"])

    search_mode = SearchMode.CONVERSATIONAL if mode == "conversational" else SearchMode.TRADITIONAL

    session = Session(
        mode=search_mode,
        channel=channel,
        browsingDate=browsing.isoformat(),
        browsingLocalTime=local_time,
        timeZone=tz,
        name=f"Random {resolved} {search_mode.value} session",
    )

    if search_mode == SearchMode.CONVERSATIONAL:
        session.conversational = _gen_conversational(resolved, browsing)
    else:
        session.traditional = _gen_traditional(resolved, browsing)

    return session

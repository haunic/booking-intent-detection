"""Build a concise but complete natural-language `state` from a session.

The state must not contain empty, undefined, or contradictory values. It
includes derived facts (trip type, length of stay, days-to-departure, route /
date / passenger changes vs the previous search, convergence/exploration
signals) so the decision model has the behavioral evidence it needs.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .models import FlightSearch, Session, SearchMode


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def _pax_phrase(adults: int, children: int) -> str:
    parts = []
    if adults:
        parts.append(f"{adults} adult" + ("s" if adults != 1 else ""))
    if children:
        parts.append(f"{children} child" + ("ren" if children != 1 else ""))
    return " and ".join(parts) if parts else "unspecified passengers"


def _describe_search(s: FlightSearch, browsing: Optional[date]) -> list[str]:
    lines: list[str] = []
    if s.origin and s.destination:
        route = f"{s.origin} to {s.destination}"
    elif s.origin:
        route = f"from {s.origin}"
    elif s.destination:
        route = f"to {s.destination}"
    else:
        route = None

    dep = _parse_date(s.departure_date)
    ret = _parse_date(s.return_date)

    if route:
        lines.append(f"Route: {route}.")
    if dep:
        trip_type = "round-trip" if ret else "one-way"
        lines.append(f"Trip type: {trip_type}.")
        lines.append(f"Departure: {dep.isoformat()}.")
        if ret:
            lines.append(f"Return: {ret.isoformat()}.")
            stay = (ret - dep).days
            if stay >= 0:
                lines.append(f"Length of stay: {stay} day" + ("s" if stay != 1 else "") + ".")
        if browsing:
            days_before = (dep - browsing).days
            lines.append(f"Days before departure: {days_before}.")
    lines.append(f"Passengers: {_pax_phrase(s.adults, s.children)}.")
    return lines


def _compare_searches(current: FlightSearch, previous: FlightSearch) -> list[str]:
    """Describe changes between the most recent previous search and the current one."""
    lines: list[str] = []
    route_changed = (current.origin, current.destination) != (previous.origin, previous.destination)
    if route_changed:
        lines.append(
            f"Route changed from {previous.origin or '?'}-{previous.destination or '?'} "
            f"to {current.origin or '?'}-{current.destination or '?'}."
        )
    else:
        lines.append("Route unchanged from the previous search.")

    cur_dep = _parse_date(current.departure_date)
    prev_dep = _parse_date(previous.departure_date)
    if cur_dep and prev_dep:
        shift = (cur_dep - prev_dep).days
        if shift == 0:
            lines.append("Departure date unchanged from the previous search.")
        else:
            lines.append(f"Departure date shifted by {abs(shift)} day(s) vs the previous search.")

    if (current.adults, current.children) != (previous.adults, previous.children):
        lines.append(
            f"Passenger counts changed from {previous.adults}a/{previous.children}c "
            f"to {current.adults}a/{current.children}c."
        )
    else:
        lines.append("Passenger counts unchanged from the previous search.")

    # Convergence / exploration heuristic signal (behavioral evidence, not a verdict).
    cur_ret = _parse_date(current.return_date)
    prev_ret = _parse_date(previous.return_date)
    if not route_changed and cur_dep and prev_dep and abs((cur_dep - prev_dep).days) <= 5:
        lines.append("Behavioral signal: same route with a small date variation (possible convergence).")
    elif route_changed:
        lines.append("Behavioral signal: destination/route switching (possible broad exploration).")
    return lines


def build_traditional_state(session: Session) -> str:
    browsing = _parse_date(session.browsingDate)
    data = session.traditional
    blocks: list[str] = []

    blocks.append(
        "Browsing context: "
        f"channel={session.channel.value}; "
        f"browsing date={session.browsingDate or 'unknown'}; "
        f"local time={session.browsingLocalTime or 'unknown'}; "
        f"time zone={session.timeZone or 'unknown'}."
    )

    if data.previous_searches:
        blocks.append(f"The traveler ran {len(data.previous_searches)} previous search(es), oldest first:")
        for idx, s in enumerate(data.previous_searches, start=1):
            desc = " ".join(_describe_search(s, browsing))
            blocks.append(f"Previous search {idx}: {desc}")
    else:
        blocks.append("The traveler has no previous searches in this session.")

    cur = data.current_search
    blocks.append("Current search: " + " ".join(_describe_search(cur, browsing)))

    if data.previous_searches:
        most_recent = data.previous_searches[-1]
        blocks.append("Changes vs the most recent previous search: " + " ".join(_compare_searches(cur, most_recent)))

    return "\n".join(b for b in blocks if b.strip())


def build_conversational_state(session: Session) -> str:
    data = session.conversational
    blocks: list[str] = []

    blocks.append(
        "Browsing context: "
        f"channel={session.channel.value}; "
        f"browsing date={session.browsingDate or 'unknown'}; "
        f"local time={session.browsingLocalTime or 'unknown'}; "
        f"time zone={session.timeZone or 'unknown'}."
    )

    if data.previous_messages:
        blocks.append("Conversation history (oldest first):")
        for idx, m in enumerate(data.previous_messages, start=1):
            text = (m.text or "").strip()
            if text:
                blocks.append(f"Traveler message {idx}: {text}")
    else:
        blocks.append("No prior conversation messages in this session.")

    current = (data.current_request or "").strip()
    if current:
        blocks.append(f"Current traveler request: {current}")

    blocks.append(
        "Assess convergence vs exploration from the conversation: whether the traveler has settled on a "
        "specific route, dates, and passenger count, or is still exploring broadly."
    )
    return "\n".join(b for b in blocks if b.strip())


def build_state(session: Session) -> str:
    if session.mode == SearchMode.CONVERSATIONAL:
        return build_conversational_state(session)
    return build_traditional_state(session)

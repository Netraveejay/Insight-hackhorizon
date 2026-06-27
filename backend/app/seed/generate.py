"""Synthetic seed data — fictional sites, realistic guest/staff voice."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from app.schemas import SITES

random.seed(42)

RECENT_WEEKS = ["2026-W22", "2026-W23", "2026-W24", "2026-W25", "2026-W26"]
LATEST_WEEK = RECENT_WEEKS[-1]

FILMS = [
    "Midnight Horizon",
    "The Last Reef",
    "Steel City",
    "Echoes of Summer",
    "Night Run",
    "Pacific Drift",
]

# Harbourview projection arc — unique messages, compounding W24→W26
HARBOURVIEW_PROJECTION = {
    "2026-W24": [
        ("csat", 2, "Auditorium 3, Saturday 7:30pm — screen looked a bit dim but we managed. Noticed it more in night scenes."),
        ("public_review", 2, "Watched Midnight Horizon at Harbourview. Picture was softer than other sites — slightly washed out in the middle."),
        ("guest_services_inbox", None, "Hello, we visited last Friday. The projection in auditorium 3 seemed darker than usual. Booking ref HV-88421."),
        ("contact_form", None, "Screen brightness felt low during our session. Hoping this can be checked before next weekend."),
    ],
    "2026-W25": [
        ("csat", 2, "7:45pm session — image was blurry at the start and never quite sharpened up. Disappointing for a premium ticket."),
        ("public_review", 1, "Projector seemed out of focus the whole film. Dark scenes were almost black. Lamp might need replacing?"),
        ("guest_services_inbox", None, "Following up on my visit Sunday — the screen was noticeably dim again in auditorium 3. Same issue as a few weeks ago."),
        ("social", None, "Anyone else get a really dark screen at @HarbourviewCinema last night? Could barely see Pacific Drift in the cave sequence."),
        ("csat", 2, "Flickering during adverts then settled but still dim. Staff said they'd log it with technical."),
        ("public_review", 2, "Love this cinema usually but projection quality has slipped — washed out colours and low brightness."),
    ],
    "2026-W26": [
        ("csat", 1, "Auditorium 3 again — screen was very dim tonight, hard to see the picture. Manager apologised but film was ruined."),
        ("csat", 2, "Projection quality was poor — image looked washed out and out of focus for the entire film."),
        ("guest_services_inbox", None, "Hi team, third visit this month with a dim screen in aud 3. Please call me on 0412 345 678 or email sarah.k@example.com."),
        ("public_review", 1, "Harbourview needs to fix their projector. Dark scenes impossible to see. Lamp clearly failing."),
        ("contact_form", None, "We left early because the picture was blurry and too dark. Requesting a refund for four tickets."),
        ("public_review", 2, "Screen brightness dropped halfway through Night Run. Very distracting flicker in act two."),
        ("social", None, "Third week in a row with a dim screen at Harbourview 😤 projector lamp overdue surely"),
        ("csat", 2, "Pixelated corners and soft focus — not what you expect for $24 tickets."),
        ("guest_services_inbox", None, "Staff were lovely but technical issue ruined Steel City — screen dark throughout."),
    ],
}

HARBOURVIEW_STAFF_KPI = [
    (
        "2026-W25",
        "Site KPI — Harbourview | Week 2026-W25\n"
        "Auditorium 3: lamp hours 1,240 (replace threshold 1,200). Measured 9.1 fL vs target 14 fL. "
        "Maintenance ticket HV-4821 raised with Technical Operations.",
    ),
    (
        "2026-W26",
        "Site KPI — Harbourview | Week 2026-W26\n"
        "Follow-up: Auditorium 3 lamp still in service. Guest complaints up 3x WoW. "
        "Alignment drift reported by duty manager after Saturday peak. Escalate to regional tech.",
    ),
]

HARBOURVIEW_POSITIVE = [
    ("csat", 5, "Usher in auditorium 1 was fantastic — helped us with booster seats for the kids."),
    ("csat", 4, "Clean foyer and friendly team at concessions. Shame about aud 3 picture but staff tried their best."),
    ("public_review", 4, "Great location and comfy seats. Usually a solid night out — just had one off projection visit."),
]

HARBOURVIEW_MULTILINGUAL = [
    ("屏幕太暗了，7号厅几乎看不清电影画面", "zh-cn"),
    ("La pantalla estaba muy oscura en la sala 3, difícil de ver la película", "es"),
    ("L'écran était très sombre ce soir, impossible de profiter du film", "fr"),
]

# Northgate ticketing compounding
NORTHGATE_TICKETING = {
    "2026-W24": [
        ("contact_form", None, "Waited 18 minutes to buy two tickets on Thursday evening. Only one counter open."),
        ("csat", 3, "Queue moved slowly — understaffed at the ticket desk for a busy session."),
    ],
    "2026-W25": [
        ("csat", 2, "Ticketing queue stretched past the candy bar. Kiosk 2 was out of order."),
        ("guest_services_inbox", None, "Peak Saturday — 25+ minute wait at box office. Several guests walked out."),
        ("public_review", 2, "Slow service at the ticket desk again. Need more staff on weekends."),
        ("contact_form", None, "Only one kiosk working, massive line. Pre-booked online but still queued for popcorn pickup confusion."),
    ],
    "2026-W26": [
        ("csat", 2, "Queue at the ticket counter was extremely long — missed our trailers."),
        ("guest_services_inbox", None, "Northgate Friday 6pm: four counters, two staffed. Queue management needs attention."),
        ("public_review", 1, "Waited 25 minutes in the ticketing queue. Unacceptable for a flagship site."),
        ("social", None, "Northgate box office chaos again 🙄 one person on tickets at 7pm on a Friday??"),
        ("contact_form", None, "Ticketing queue times unacceptable — suggest roster review for peak windows."),
    ],
}

NORTHGATE_STAFF_KPI = (
    "Staff KPI — Northgate | Week 2026-W26\n"
    "Peak Fri–Sat: avg queue time 14 min (target 5 min). 2 of 4 counters staffed 17:00–20:00. "
    "POS terminal 3 intermittent. Roster gap flagged to site manager."
)

# Realistic F&B friction — varied wording, lexicon-driven classification
FNB_GUEST = [
    ("Popcorn was lukewarm by the time we sat down — batch must have been sitting too long.", 2),
    ("Coffee from the candy bar was cold. $6.50 for an iced latte that's room temperature is rough.", 2),
    ("Nachos were lukewarm with congealed cheese. Expected better for the price.", 2),
    ("Overpriced snacks as usual but the choc tops were fine. Popcorn stale though.", 3),
    ("Food prices are too high for the quality — $12 popcorn should be fresh.", 2),
    ("Kids combo drink was flat and the hot dog was cold. Disappointing.", 2),
    ("Candy bar queue almost as long as ticketing. Coffee machine seemed broken.", 3),
]

# Positive staff — natural CSAT voice
POSITIVE_STAFF = [
    ("Staff were incredibly friendly and welcoming from the moment we arrived.", 5),
    ("Usher helped us find seats in a packed session — really appreciated.", 5),
    ("Manager resolved our booking mix-up quickly and with a smile.", 5),
    ("Great service from the team tonight, especially the concessions crew.", 4),
    ("Warm and welcoming staff made our first visit with toddlers much easier.", 5),
    ("Duty manager checked on us after a minor spill — professional and kind.", 4),
]

# Film criticism — non-controllable
NON_CONTROLLABLE = [
    ("Didn't enjoy the film — plot was predictable and too long.", 2),
    ("Not my genre. Storyline was boring and the ending felt rushed.", 2),
    ("Movie itself was disappointing but cinema was fine.", 3),
    ("Too many trailers before the feature. Film was okay.", 3),
    ("Left at interval — just wasn't for us.", 2),
]

# Coordinated review bomb at Southbank (identical opening triggers spam filter)
SPAM_REVIEW_OPENING = "Absolute worst cinema in Sydney. Never coming back. Avoid Southbank"

# Background operational friction — no theme hints; scoring uses lexicon
BACKGROUND_GUEST = [
    ("The toilets on level 2 were dirty and smelled bad before the evening sessions.", "cleanliness", 2),
    ("Sticky floors in auditorium 5 — spilled drink not cleaned between sessions.", "cleanliness", 2),
    ("Seat 12F armrest broken and dug into my arm the whole film.", "comfort_seating", 2),
    ("Booking app crashed twice when selecting seats — had to call the desk.", "booking_app", 2),
    ("Sound was muffled and dialogue hard to hear in auditorium 2.", "audio_sound", 2),
    ("Volume jumped between trailers and feature — too loud then too quiet.", "audio_sound", 3),
    ("Ticket prices are expensive compared to streaming at home.", "value_pricing", 3),
    ("Paid for premium recliners — seat wouldn't recline properly.", "comfort_seating", 2),
    ("Air conditioning too cold in the back row.", "comfort_seating", 3),
    ("Parking was chaotic after the late session — not really cinema's fault but stressful.", "non_controllable", 3),
]

RIVERSIDE_DISRUPTION = (
    "DISRUPTION NOTIFICATION — Riverside | 2026-W26 Sat 21:15\n"
    "Fire alarm triggered auditorium 2 during 'Echoes of Summer'. Evacuation completed; "
    "all guests accounted for. Session cancelled. Refunds to be processed. "
    "Cause: burnt popcorn in adjacent prep area — no injury. Fire brigade attended as precaution."
)

GUEST_CHANNELS = ("csat", "guest_services_inbox", "contact_form", "public_review", "social")


def _ts_for_week(week: str, weekend_bias: bool = False) -> datetime:
    year, w = int(week[:4]), int(week.split("W")[1])
    jan1 = datetime(year, 1, 1)
    day = random.choice([4, 5, 5, 6]) if weekend_bias else random.randint(0, 6)
    hour = random.choice([18, 19, 19, 20, 20, 21]) if weekend_bias else random.randint(10, 21)
    return jan1 + timedelta(weeks=w - 1, days=day, hours=hour, minutes=random.randint(0, 59))


def generate() -> list[dict]:
    items: list[dict] = []

    def add(
        source_type,
        channel,
        site_id,
        week,
        text,
        rating=None,
        theme_hint=None,
        sentiment_hint=None,
        lang_hint=None,
        weekend_bias=False,
    ):
        items.append({
            "source_type": source_type,
            "channel": channel,
            "site_id": site_id,
            "ts": _ts_for_week(week, weekend_bias=weekend_bias).isoformat(),
            "week": week,
            "rating": rating,
            "theme_hint": theme_hint,
            "sentiment_hint": sentiment_hint,
            "lang_hint": lang_hint,
            "text": text,
        })

    # ── Hero: Harbourview projection compounding + staff cross-source ──
    for week, entries in HARBOURVIEW_PROJECTION.items():
        for channel, rating, text in entries:
            add(
                "guest", channel, "harbourview", week, text,
                rating=rating, theme_hint="projection_quality", sentiment_hint="negative",
                weekend_bias=True,
            )

    for week, body in HARBOURVIEW_STAFF_KPI:
        add("staff", "kpi_email", "harbourview", week, body, theme_hint="projection_quality", sentiment_hint="negative")

    for channel, rating, text in HARBOURVIEW_POSITIVE:
        add("guest", channel, "harbourview", LATEST_WEEK, text, rating=rating, weekend_bias=True)

    for text, lang in HARBOURVIEW_MULTILINGUAL:
        add(
            "guest", "public_review", "harbourview", LATEST_WEEK, text,
            rating=2, theme_hint="projection_quality", sentiment_hint="negative", lang_hint=lang,
        )

    # Duplicate submission (same guest double-taps CSAT)
    dup_text = "Auditorium 3 again — screen was very dim tonight, hard to see the picture. Manager apologised but film was ruined."
    add("guest", "csat", "harbourview", LATEST_WEEK, dup_text, rating=1, theme_hint="projection_quality", sentiment_hint="negative")

    # ── Secondary: Northgate ticketing ──
    for week, entries in NORTHGATE_TICKETING.items():
        for channel, rating, text in entries:
            add(
                "guest", channel, "northgate", week, text,
                rating=rating, theme_hint="ticketing_queue", sentiment_hint="negative",
                weekend_bias=week == LATEST_WEEK,
            )
    add("staff", "kpi_email", "northgate", LATEST_WEEK, NORTHGATE_STAFF_KPI, theme_hint="ticketing_queue", sentiment_hint="negative")

    # ── National F&B friction (lexicon classifies; no hints) ──
    for site in SITES:
        n = random.randint(2, 4)
        for text, rating in random.sample(FNB_GUEST, min(n, len(FNB_GUEST))):
            add(
                "guest", random.choice(["public_review", "social", "contact_form", "csat"]),
                site["id"], LATEST_WEEK, text, rating=rating, weekend_bias=True,
            )

    # ── Positive staff nationally ──
    for site in SITES:
        for text, rating in random.sample(POSITIVE_STAFF, random.randint(2, 4)):
            add("guest", "csat", site["id"], random.choice(RECENT_WEEKS), text, rating=rating)

    # ── Southbank review bomb (coordinated low reviews, same opening line) ──
    spam_suffixes = [
        ". Staff rude too.",
        " — save your money.",
        "!!!",
        " Worst experience ever.",
        " Total scam.",
        " Never again.",
    ]
    for suffix in spam_suffixes:
        add(
            "guest", "public_review", "southbank", LATEST_WEEK,
            SPAM_REVIEW_OPENING + suffix,
            rating=1, sentiment_hint="negative",
        )

    # ── Riverside evacuation (high urgency) ──
    add(
        "staff", "disruption_notification", "riverside", LATEST_WEEK,
        RIVERSIDE_DISRUPTION,
        theme_hint="cleanliness", sentiment_hint="negative",
    )

    # Guest reactions to Riverside evacuation
    add(
        "guest", "guest_services_inbox", "riverside", LATEST_WEEK,
        "We were evacuated during the film — fire alarm. Staff handled it well but scary for the kids. "
        "Happy to get a refund but wanted to acknowledge the team.",
        rating=None,
    )
    add(
        "guest", "csat", "riverside", LATEST_WEEK,
        "Session cancelled after evacuation. Staff were calm and professional during the alarm.",
        rating=4,
    )

    # ── Non-controllable film complaints ──
    for site in random.sample(SITES, 6):
        text, rating = random.choice(NON_CONTROLLABLE)
        add("guest", "public_review", site["id"], LATEST_WEEK, text, rating=rating, theme_hint="non_controllable")

    # ── Multilingual at other sites ──
    extra_ml = [
        ("northgate", "Hàng đợi mua vé rất dài, phải chờ gần nửa tiếng", "vi"),
        ("lakeside", "الشاشة كانت مظلمة جداً ولم أستطع رؤية الفيلم بوضوح", "ar"),
        ("cityplaza", "爆米花是温的，而且太贵了，不太满意", "zh-cn"),
        ("greenwood", "L'écran était très sombre, difficile de voir le film", "fr"),
        ("oakridge", "स्टाफ बहुत मददगार और विनम्र था, धन्यवाद", "hi"),
        ("baytown", "جودة الصوت سيئة والحجم منخفض جداً في القاعة", "ar"),
    ]
    for site_id, text, lang in extra_ml:
        add(
            "guest", random.choice(["public_review", "contact_form"]), site_id, LATEST_WEEK,
            text, rating=2 if lang != "hi" else 5, lang_hint=lang,
        )

    # ── Weekly background noise across sites (lexicon-driven) ──
    for week in RECENT_WEEKS:
        for site in random.sample(SITES, 10):
            text, _theme, rating = random.choice(BACKGROUND_GUEST)
            film = random.choice(FILMS)
            if random.random() < 0.4:
                text = f"{text} ({film} session)"
            add(
                "guest", random.choice(GUEST_CHANNELS), site["id"], week,
                text, rating=rating,
                weekend_bias=week == LATEST_WEEK,
            )

    # ── Neutral / mixed CSAT filler ──
    neutral_csat = [
        "Fine overall — nothing special but no major issues.",
        "Decent visit. Sound was good, seats okay.",
        "Average experience. Would come back for the right film.",
        "Parking easy, session on time. Concessions a bit pricey.",
    ]
    for site in random.sample(SITES, 12):
        add(
            "guest", "csat", site["id"], random.choice(RECENT_WEEKS),
            random.choice(neutral_csat), rating=3,
        )

    return items


def main():
    data = generate()
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "feedback.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} seed items → {out_path}")


if __name__ == "__main__":
    main()

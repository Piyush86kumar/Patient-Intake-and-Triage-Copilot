EMERGENCY_TRIGGER_KEYWORDS = [
    "shot", "gunshot", "stabbed", "stabbing", "hit by a car", "hit by a truck",
    "car accident", "fell from", "fell down stairs", "can't breathe",
    "cannot breathe", "not breathing", "unconscious", "passed out",
    "won't wake up", "seizure", "overdose", "severe bleeding",
    "won't stop bleeding", "bleeding a lot", "choking", "allergic reaction",
    "anaphylaxis", "can't move my", "crushed", "electrocuted", "drowning",
]

def check_trigger_keywords(raw_text : str) -> bool:
    text_lower= raw_text.lower()
    return any(kw in text_lower for kw in EMERGENCY_TRIGGER_KEYWORDS)
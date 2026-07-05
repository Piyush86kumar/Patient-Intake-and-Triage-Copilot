EMERGENCY_TRIGGER_KEYWORDS = [
    # Penetrating / violent trauma
    "shot", "gunshot", "gsw", "stabbed", "stabbing", "knifed", "impaled",
    "hit by a car", "hit by a truck", "car accident", "car crash", "run over",
    "fell from", "fell down stairs", "fell off a ladder", "crushed",
    "broken bone", "broken leg", "broken arm", "fracture", "fractured",
    "electrocuted", "drowning", "burned badly", "severe burn",
    # Breathing
    "can't breathe", "cannot breathe", "not breathing", "no longer breathing",
    "difficulty breathing", "difficult to breathe", "hard to breathe",
    "trouble breathing", "struggling to breathe", "can't catch my breath",
    "can't catch breath", "breathlessness", "short of breath",
    "gasping for air", "turning blue", "lips are blue",
    # Consciousness / neuro
    "unconscious", "passed out", "won't wake up", "unresponsive",
    "seizure", "convulsing", "sudden confusion", "can't speak",
    "face drooping", "one side of my face", "sudden weakness on one side",
    # Bleeding / circulation
    "bleeding", "severe bleeding", "won't stop bleeding", "bleeding a lot",
    "bleeding heavily", "spurting blood", "vomiting blood", "coughing up blood",
    # Allergic / toxic
    "allergic reaction", "anaphylaxis", "throat closing", "throat closing up",
    "swelling face", "swelling of the face", "overdose", "took too many pills",
    "poisoned", "ingested poison",
    # Other acute
    "choking", "can't move my", "paralyzed", "severe head injury",
    "worst headache of my life",
    # Patient-stated emergencies
    "heart attack", "having a heart attack", "asthma attack", "having a stroke",
]

def check_trigger_keywords(raw_text : str) -> bool:
    text_lower= raw_text.lower()
    return any(kw in text_lower for kw in EMERGENCY_TRIGGER_KEYWORDS)
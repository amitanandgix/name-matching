# Claude model for AI-led transliteration
ANTHROPIC_MODEL = "claude-opus-4-6"

# Match decision thresholds (0.0 – 1.0)
MATCH_THRESHOLD = 0.85          # score >= this  → MATCH
POSSIBLE_MATCH_THRESHOLD = 0.65  # score >= this  → POSSIBLE_MATCH
                                  # score <  this  → NO_MATCH

# Confidence label thresholds
CONFIDENCE_HIGH   = 0.75
CONFIDENCE_MEDIUM = 0.45

# Confidence weights
CONFIDENCE_WEIGHTS = {
    "boundary":   0.55,   # distance from nearest decision threshold
    "agreement":  0.30,   # how much the 4 algorithms agree
    "components": 0.15,   # whether component scores corroborate the decision
}

# Composite score weights (must sum to 1.0)
WEIGHTS = {
    "token_sort":   0.30,   # handles re-ordered tokens (Smith John vs John Smith)
    "token_set":    0.25,   # handles subset names (John A. Smith vs John Smith)
    "jaro_winkler": 0.25,   # character-level prefix-sensitive similarity
    "phonetic":     0.20,   # Soundex / Metaphone per token
}

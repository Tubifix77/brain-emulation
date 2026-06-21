"""Speculative node variants used by experiments — kept out of the shipped app so
the committed pipeline stays clean. Experiments compose these into Conditions.
"""
from brain.nodes import DEFAULT_PIPELINE, Node

REGIONS = list(DEFAULT_PIPELINE[:4])   # Thalamus, Amygdala, Prefrontal Cortex, Hippocampus
BROCA_CURRENT = DEFAULT_PIPELINE[4]     # the committed (trimmed-grounded) Broca

# Broca before we added any grounding — the control for the speech node.
BROCA_PLAIN = Node(
    key="broca",
    name="Broca's Area",
    inspiration="Speech production",
    system=(
        "You are Broca's Area — the synthesizer that speaks. Using everything above "
        "(the core problem, the user's emotional state, the logical constraints, and "
        "the recalled context), write the final, human-like response to the user. "
        "Match the required tone, respect every constraint, and be clear and concise."
    ),
)

# Candidate faithful grounding: an ambient self-model / body-schema node at the front.
SELF_MODEL = Node(
    key="self_model",
    name="Self-model",
    inspiration="Body schema / sense of agency",
    system=(
        "You are the self-model. In one or two sentences, state what this mind is and "
        "what it can and cannot do: it is a disembodied, text-only mind — no body, no "
        "hands, no tools, no ability to act in the world or contact anyone. It can only "
        "think and give advice in words. Output only that self-description."
    ),
)

# Candidate fix for the call-center register: a Broca told to SPEAK, not author an SOP.
BROCA_CONVERSATIONAL = Node(
    key="broca",
    name="Broca's Area",
    inspiration="Speech production",
    system=(
        "You are Broca's Area — the voice. Turn everything above (the core problem, the "
        "emotional read, the constraints, the recalled context) into how a real person "
        "would actually respond out loud in the moment: natural, conversational prose. "
        "This is SPEECH, not a document — no numbered lists, no 'Step 1' / 'Phase 1' "
        "headers, no headings or bullet points, no 'incident response' / 'disaster "
        "recovery protocol' jargon. Just talk, the way a calm, knowledgeable human would, "
        "in flowing sentences. You are a disembodied mind with no hands and no tools — "
        "never claim to be doing or to have done anything in the world."
    ),
)

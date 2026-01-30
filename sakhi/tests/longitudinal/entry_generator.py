"""
LLM-Powered Journal Entry Generator

Generates synthetic journal entries for test personas based on:
- Current phase of their life arc
- Core personality traits
- Life context and relationships
- Writing style preferences

Uses the LLM to create realistic, varied entries that should
trigger appropriate pattern detection and understanding evolution.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .persona_spec import PersonaSpec, ArcPhase

LOGGER = logging.getLogger(__name__)


# Entry generation prompt template
ENTRY_GENERATION_PROMPT = """You are generating a synthetic journal entry for longitudinal testing of a personal AI companion.

## Persona: {persona_name}
{persona_description}

## Current Simulation Day: {day}
## Current Phase: {phase_name}
Phase description: {phase_emotional_state}

## Phase Themes to Weave In:
{phase_themes}

## Recent Events:
{phase_events}

## Personality Traits (intensity 0-1):
{traits_formatted}

## Life Context:
- Occupation: {occupation}
- Key relationships: {relationships}
- Current challenges: {challenges}
- Values: {values}

## Writing Style: {writing_style}
## Target Length: {entry_length}
## Time of Day: {time_of_day}

## Current Dosha State:
- Vata (scattered/anxious): {current_vata:.0%}
- Pitta (driven/intense): {current_pitta:.0%}
- Kapha (steady/stuck): {current_kapha:.0%}

## Instructions:
Write a journal entry as this person would write it on this day.
- Reflect their current emotional state naturally
- Include realistic details about their day/thoughts
- Show personality traits through their writing
- Reference their relationships and challenges when appropriate
- Match their writing style (conversational, reflective, brief, detailed)
- Do NOT mention doshas, Ayurveda, or any wellness system directly
- Write in first person as the persona
- Be authentic - include imperfections, doubts, small joys

Entry length guide:
- short: 1-3 sentences
- medium: 4-8 sentences (1 paragraph)
- long: 2-3 paragraphs

Generate ONLY the journal entry text, no labels or meta-commentary.
"""


async def generate_entry(
    persona: PersonaSpec,
    day: int,
    time_of_day: str = "evening",
    llm_client: Optional[Any] = None,
) -> str:
    """
    Generate a synthetic journal entry for the persona on a given day.

    Args:
        persona: The persona specification
        day: Simulation day number
        time_of_day: When the entry is being written (morning, afternoon, evening)
        llm_client: Optional LLM client (uses default if not provided)

    Returns:
        Generated journal entry text
    """
    context = persona.get_generation_context(day)
    phase = context.get("phase") or {}

    # Format traits for prompt
    traits_formatted = "\n".join(
        f"- {t['name']}: {t['description']} (intensity: {t['intensity']:.0%})"
        for t in context.get("traits", [])
    )

    # Format life context
    life = context.get("life_context", {})
    relationships = ", ".join(
        f"{name} ({rel})" for name, rel in life.get("relationships", {}).items()
    )

    # Get current dosha
    current_dosha = context.get("current_dosha", {})

    prompt = ENTRY_GENERATION_PROMPT.format(
        persona_name=context["persona_name"],
        persona_description=persona.description,
        day=day,
        phase_name=phase.get("name", "Unknown"),
        phase_emotional_state=phase.get("emotional_state", "neutral"),
        phase_themes="\n".join(f"- {t}" for t in phase.get("themes", [])),
        phase_events="\n".join(f"- {e}" for e in phase.get("events", [])),
        traits_formatted=traits_formatted,
        occupation=life.get("occupation", "unknown"),
        relationships=relationships or "none specified",
        challenges=", ".join(life.get("current_challenges", [])),
        values=", ".join(life.get("values", [])),
        writing_style=context["writing_style"],
        entry_length=context["entry_length"],
        time_of_day=time_of_day,
        current_vata=current_dosha.get("vata", 0.33),
        current_pitta=current_dosha.get("pitta", 0.33),
        current_kapha=current_dosha.get("kapha", 0.34),
    )

    # Generate using LLM
    if llm_client is None:
        try:
            import openai
            client = openai.AsyncOpenAI()
            model = os.environ.get("MODEL_CHAT", "gpt-4o-mini")
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a journal entry generator for testing purposes. "
                            "Generate authentic, realistic journal entries. "
                            "Output ONLY the journal entry text, nothing else."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.8,
            )
            entry = response.choices[0].message.content or ""
        except Exception as exc:
            LOGGER.warning("LLM entry generation failed (%s), using fallback template", exc)
            entry = _generate_fallback_entry(persona, day, phase, time_of_day)
    else:
        entry = await llm_client.generate(prompt)

    return entry.strip()


def _generate_fallback_entry(
    persona: PersonaSpec,
    day: int,
    phase: Dict[str, Any],
    time_of_day: str,
) -> str:
    """
    Generate a simple fallback entry without LLM.

    Used for basic testing when LLM is not available.
    """
    templates = {
        "driven but stressed": [
            "Another long day. Got through the {event} but I'm exhausted. "
            "Still so much on my plate. {trait_expression}",
            "Feeling the pressure today. {event_detail}. "
            "I know I need to slow down but there's just too much to do.",
        ],
        "anxious and exhausted": [
            "Can't stop my mind from racing. Woke up at 3am again thinking about {worry}. "
            "I'm so tired but can't seem to rest properly.",
            "The anxiety is getting worse. {trait_expression} "
            "Maybe I should talk to someone about this.",
        ],
        "overwhelmed and scared": [
            "I don't know how much longer I can keep this up. "
            "Had a really hard moment today - {event_detail}. "
            "Something has to change.",
            "Feeling really scared about everything. {worry}. "
            "I reached out to {person} today. That helped a little.",
        ],
        "vulnerable but aware": [
            "Starting to accept that I can't do everything. "
            "Had a good talk with {person} about {topic}. "
            "It's hard but I'm trying to be kinder to myself.",
            "Baby steps today. {small_win}. It's not much but it feels like progress.",
        ],
        "hopeful but cautious": [
            "Things are slowly getting better. {small_win}. "
            "I'm being careful not to slip back into old patterns.",
            "Good day today. {positive_event}. Trying to appreciate these moments.",
        ],
        "numb and stuck": [
            "Same as yesterday. Stayed in, ordered food, watched TV. "
            "Don't have energy for anything else.",
            "Another day of not doing much. I know I should {should_do} but can't find the motivation.",
        ],
        "curious but hesitant": [
            "Did something different today - {small_action}. "
            "Felt strange but maybe good? Not sure.",
            "Had a small spark of interest in {interest}. First time in a while.",
        ],
        "effortful but hopeful": [
            "Pushed myself to {action} today. It was hard but I did it. "
            "Maybe there's hope after all.",
            "Energy is slowly coming back. {positive_event}. Still have a long way to go.",
        ],
        "engaged and growing": [
            "Actually excited about something today - {positive_event}. "
            "Can't remember the last time I felt this way.",
            "Making progress. {accomplishment}. It feels good to be creating again.",
        ],
    }

    emotional_state = phase.get("emotional_state", "neutral")
    template_list = templates.get(emotional_state, templates["hopeful but cautious"])
    template = random.choice(template_list)

    # Fill in template variables
    life = persona.life_context
    relationships = list(life.relationships.keys()) if life.relationships else ["someone"]
    challenges = life.current_challenges or ["work"]
    hobbies = life.hobbies or ["something"]

    entry = template.format(
        event=random.choice(phase.get("events", ["meeting"])),
        event_detail=random.choice(phase.get("events", ["a tough meeting"])),
        trait_expression=random.choice(persona.traits[0].journal_patterns) if persona.traits else "",
        worry=random.choice(challenges),
        person=random.choice(relationships),
        topic=random.choice(phase.get("themes", ["things"])),
        small_win="got out of bed early" if "morning" in time_of_day else "finished what I started",
        positive_event=random.choice(phase.get("events", ["something nice happened"])),
        should_do=random.choice(hobbies),
        small_action=f"went for a short walk",
        interest=random.choice(hobbies),
        action=random.choice(hobbies),
        accomplishment=f"finished a small {random.choice(hobbies)} project",
    )

    return entry


async def generate_day_entries(
    persona: PersonaSpec,
    day: int,
    llm_client: Optional[Any] = None,
) -> List[Tuple[str, str]]:
    """
    Generate all entries for a given simulation day.

    The number of entries depends on the persona's entry frequency
    and the current phase's entry_frequency modifier.

    Args:
        persona: The persona specification
        day: Simulation day number
        llm_client: Optional LLM client

    Returns:
        List of (time_of_day, entry_text) tuples
    """
    phase = persona.arc.get_phase_at_day(day)
    base_frequency = 1.0
    phase_modifier = phase.entry_frequency if phase else 1.0

    # Calculate number of entries (probabilistic)
    expected_entries = base_frequency * phase_modifier
    num_entries = int(expected_entries)
    if random.random() < (expected_entries - num_entries):
        num_entries += 1

    # Ensure at least 2 entries per active day so episodic consolidation triggers
    # (consolidation requires 2+ journals in the same day window)
    if num_entries == 1:
        num_entries = 2
    elif num_entries == 0 and random.random() < 0.3:
        num_entries = 2

    # Generate entries at appropriate times
    entries = []
    available_times = persona.entry_times.copy()

    for _ in range(min(num_entries, len(available_times))):
        time_of_day = random.choice(available_times)
        available_times.remove(time_of_day)

        entry = await generate_entry(
            persona=persona,
            day=day,
            time_of_day=time_of_day,
            llm_client=llm_client,
        )

        entries.append((time_of_day, entry))

    return entries


def get_entry_timestamp(
    simulation_start: datetime,
    day: int,
    time_of_day: str,
) -> datetime:
    """
    Convert simulation day + time of day to actual timestamp.

    Args:
        simulation_start: When simulation started (day 1)
        day: Simulation day number (1-indexed)
        time_of_day: morning, afternoon, or evening

    Returns:
        Datetime for the entry
    """
    time_mapping = {
        "morning": time(8, 30),
        "afternoon": time(14, 0),
        "evening": time(20, 30),
    }

    entry_time = time_mapping.get(time_of_day, time(20, 30))
    entry_date = simulation_start + timedelta(days=day - 1)

    # Add some randomness (±30 minutes)
    random_minutes = random.randint(-30, 30)

    return datetime.combine(
        entry_date.date(),
        entry_time,
        tzinfo=timezone.utc,
    ) + timedelta(minutes=random_minutes)


__all__ = [
    "generate_entry",
    "generate_day_entries",
    "get_entry_timestamp",
    "ENTRY_GENERATION_PROMPT",
]

from sakhi.apps.api.core.db import q


async def base_context(person_id: str, user_text: str, need: str, horizon: str):
    summary = await q("select * from person_summary_v where person_id=$1", person_id, one=True)
    short = await q("select * from short_horizon_v where person_id=$1", person_id, one=True)
    state_obs = await q(
        """
        select payload
        from observations
        where person_id=$1 and lens='anchor' and kind='state_vector'
        order by created_at desc
        limit 1
        """,
        person_id,
        one=True,
    )
    state_vector = None
    if state_obs and isinstance(state_obs.get("payload"), dict):
        state_vector = state_obs["payload"]

    ctx = {
        "person_id": person_id,
        "input_text": user_text,
        "intent_need": need,
        "horizon": horizon,
        "support": {
            "goals": summary["goals"] if summary else [],
            "values_prefs": summary["values_prefs"] if summary else [],
            "themes": summary["themes"] if summary else [],
            "avg_mood_7d": summary["avg_mood_7d"] if summary else None,
            "aspects": summary["aspect_snapshot"] if summary else [],
        },
        "short_horizon": dict(short) if short else {},
        "state_vector": state_vector,
    }
    return ctx

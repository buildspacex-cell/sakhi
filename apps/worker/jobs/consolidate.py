from __future__ import annotations


async def consolidate_person(db, pid: str):
    rows = await db.fetch(
        """
        select t, count(*) n from (
            select unnest(tags) as t from journal_entries
            where user_id=$1 and created_at > now() - interval '30 days' and array_length(tags,1) is not null
        ) s group by t having count(*) >= 3 order by n desc limit 8
        """,
        pid,
    )
    for row in rows:
        await db.execute(
            """
            insert into themes (person_id, name, scope, signals)
            values ($1,$2,'', jsonb_build_object('count',$3))
            on conflict do nothing
            """,
            pid,
            row["t"],
            row["n"],
        )

    goals = await db.fetch(
        """
        select g.id from goals g
        join journal_entries e on e.user_id=g.person_id
        where g.person_id=$1 and g.status='proposed' and e.content ilike '%' || g.title || '%'
          and e.created_at > now() - interval '14 days'
        group by g.id having count(*) >= 3
        """,
        pid,
    )
    for row in goals:
        await db.execute("update goals set status='active' where id=$1", row["id"])

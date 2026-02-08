"""
Email Cognitive Offload – Digest Pipeline
------------------------------------------
Reads email bodies transiently, runs them through an LLM for triage,
and stores structured insights. Bodies are NEVER persisted.

Pipeline:
1. select_emails_for_digest  → pick ~50 most relevant emails
2. fetch_bodies_transient    → fetch bodies via Gmail API (in-memory only)
3. analyze_batch             → LLM triage + commitment extraction
4. generate_digest           → orchestrate full pipeline, store result
"""

from __future__ import annotations

import asyncio
import hashlib
import json as _json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.email.adapters.gmail import GmailAdapter
from sakhi.apps.api.services.email.digest_models import (
    EmailBatchAnalysis,
)
from sakhi.apps.api.services.email.models import EmailProvider, SyncState
from sakhi.apps.api.services.email.sync import get_sync_state

LOGGER = logging.getLogger(__name__)

# Configuration
DIGEST_FRESHNESS_HOURS = 6
LLM_BATCH_SIZE = 3
BODY_TRUNCATE_CHARS = 800
BODY_FETCH_CONCURRENCY = 5
BODY_FETCH_DELAY_MS = 200
LLM_MODEL = "gpt-4o-mini"
LLM_MAX_TOKENS = 4096


# =============================================================================
# 0. Verification Email Filter
# =============================================================================

_VERIFICATION_SUBJECT_PATTERNS = re.compile(
    r"(?i)("
    r"verif(?:y|ication)\b"
    r"|confirm your (?:email|account|identity)"
    r"|one.time (?:password|code|passcode)"
    r"|\bOTP\b"
    r"|password reset"
    r"|reset your password"
    r"|security (?:code|alert|notification)"
    r"|sign.in (?:attempt|code|verification)"
    r"|login (?:code|verification|attempt)"
    r"|two.(?:factor|step)"
    r"|2.(?:factor|step)"
    r"|activation (?:link|code)"
    r"|email confirmation"
    r"|confirm (?:your )?(?:registration|sign.?up)"
    r")",
)

_VERIFICATION_SENDER_PATTERNS = re.compile(
    r"(?i)^(?:no.?reply|noreply|verify|security|account.?security|auth|authentication)@",
)


def _is_verification_email(email: Dict[str, Any]) -> bool:
    """Check if an email is a verification/transactional message that should be skipped."""
    subject = email.get("subject") or ""
    sender = email.get("sender_email") or ""

    if _VERIFICATION_SUBJECT_PATTERNS.search(subject):
        return True

    # Sender-based detection only if subject also looks transactional
    if _VERIFICATION_SENDER_PATTERNS.search(sender):
        transactional_keywords = re.compile(
            r"(?i)(code|token|link|confirm|activate|reset|expire)", re.IGNORECASE
        )
        if transactional_keywords.search(subject):
            return True

    return False


# Calendar / meeting notification senders that are always noise
_CALENDAR_SENDER_PATTERNS = re.compile(
    r"(?i)("
    r"calendar-notification@google\.com"
    r"|calendar-server@google\.com"
    r"|noreply@zoom\.us"
    r"|no-reply@zoom\.us"
    r"|notifications@teams\.microsoft\.com"
    r"|noreply@teams\.microsoft\.com"
    r")",
)

# Calendar/meeting subject patterns (auto-generated invites)
_CALENDAR_SUBJECT_PATTERNS = re.compile(
    r"(?i)("
    r"^invitation:"
    r"|^accepted:"
    r"|^declined:"
    r"|^tentative:"
    r"|^canceled:"
    r"|^updated invitation:"
    r"|^cancelled event:"
    r")",
)


def _is_calendar_notification(email: Dict[str, Any]) -> bool:
    """Check if an email is an auto-generated calendar/meeting notification."""
    sender = email.get("sender_email") or ""
    subject = email.get("subject") or ""

    if _CALENDAR_SENDER_PATTERNS.search(sender):
        return True

    if _CALENDAR_SUBJECT_PATTERNS.search(subject):
        return True

    return False


_VERIFICATION_COMMITMENT_PATTERNS = re.compile(
    r"(?i)("
    r"verify\b"
    r"|verification"
    r"|confirm (?:your |the )?(?:email|account|identity|registration)"
    r"|activate (?:your )?account"
    r"|reset (?:your )?password"
    r"|one.time (?:password|code)"
    r"|\bOTP\b"
    r"|security code"
    r"|sign.?in (?:attempt|code)"
    r"|login (?:code|verification)"
    r"|two.factor"
    r"|2.factor"
    r")",
)


def _is_verification_commitment(commitment: str, subject: str) -> bool:
    """Check if a commitment is really a verification/transactional action (not trackable)."""
    if _VERIFICATION_COMMITMENT_PATTERNS.search(commitment):
        return True
    if _VERIFICATION_COMMITMENT_PATTERNS.search(subject):
        return True
    return False


# =============================================================================
# 1. Email Selection
# =============================================================================

async def select_emails_for_digest(
    person_id: str,
    *,
    max_total: int = 50,
) -> List[Dict[str, Any]]:
    """
    Pick the most relevant emails for digest generation.

    Tier 1 (20): Recent human emails (7d, not newsletter/automated, incoming)
    Tier 2 (15): Avoidance candidates (threads with no outgoing reply)
    Tier 3 (10): Starred/important from 30d
    Tier 4 (5):  User's sent emails from 7d (for commitment extraction)
    """
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    selected: Dict[str, Dict[str, Any]] = {}  # message_id -> row

    # Tier 1: Recent human incoming emails
    tier1 = await dbfetch(
        """
        SELECT message_id, provider_message_id, thread_id, subject,
               sender_email, sender_name, direction, timestamp
        FROM email_events
        WHERE person_id = $1
          AND timestamp >= $2
          AND direction = 'incoming'
          AND is_newsletter = FALSE
          AND is_automated = FALSE
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        person_id,
        seven_days_ago,
    )
    for row in tier1 or []:
        mid = row["message_id"]
        d = dict(row)
        if mid not in selected and not _is_verification_email(d) and not _is_calendar_notification(d):
            selected[mid] = d

    # Tier 2: Threads awaiting reply (incoming with no outgoing in same thread)
    tier2 = await dbfetch(
        """
        SELECT DISTINCT ON (e.thread_id)
               e.message_id, e.provider_message_id, e.thread_id, e.subject,
               e.sender_email, e.sender_name, e.direction, e.timestamp
        FROM email_events e
        WHERE e.person_id = $1
          AND e.direction = 'incoming'
          AND e.is_newsletter = FALSE
          AND e.is_automated = FALSE
          AND NOT EXISTS (
              SELECT 1 FROM email_events o
              WHERE o.person_id = $1
                AND o.thread_id = e.thread_id
                AND o.direction = 'outgoing'
                AND o.timestamp > e.timestamp
          )
        ORDER BY e.thread_id, e.timestamp DESC
        LIMIT 15
        """,
        person_id,
    )
    for row in tier2 or []:
        mid = row["message_id"]
        d = dict(row)
        if mid not in selected and len(selected) < max_total and not _is_verification_email(d) and not _is_calendar_notification(d):
            selected[mid] = d

    # Tier 3: Starred or important (30d)
    tier3 = await dbfetch(
        """
        SELECT message_id, provider_message_id, thread_id, subject,
               sender_email, sender_name, direction, timestamp
        FROM email_events
        WHERE person_id = $1
          AND timestamp >= $2
          AND (is_starred = TRUE OR is_important = TRUE)
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        person_id,
        thirty_days_ago,
    )
    for row in tier3 or []:
        mid = row["message_id"]
        if mid not in selected and len(selected) < max_total:
            selected[mid] = dict(row)

    # Tier 4: User's sent emails (7d, for commitments)
    tier4 = await dbfetch(
        """
        SELECT message_id, provider_message_id, thread_id, subject,
               sender_email, sender_name, direction, timestamp
        FROM email_events
        WHERE person_id = $1
          AND timestamp >= $2
          AND direction = 'outgoing'
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        person_id,
        seven_days_ago,
    )
    for row in tier4 or []:
        mid = row["message_id"]
        if mid not in selected and len(selected) < max_total:
            selected[mid] = dict(row)

    LOGGER.info(
        "[Digest] Selected %d emails for %s (tier1=%d, tier2=%d, tier3=%d, tier4=%d)",
        len(selected), person_id,
        len(tier1 or []), len(tier2 or []), len(tier3 or []), len(tier4 or []),
    )

    return list(selected.values())


# =============================================================================
# 2. Body Fetching (transient, never stored)
# =============================================================================

async def fetch_bodies_transient(
    adapter: GmailAdapter,
    access_token: str,
    emails: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Fetch email bodies from Gmail API. Returns {message_id: body_text}.
    Bodies are held in memory only and discarded after LLM analysis.
    """
    bodies: Dict[str, str] = {}

    # Process in mini-batches to avoid rate limits
    for i in range(0, len(emails), BODY_FETCH_CONCURRENCY):
        batch = emails[i:i + BODY_FETCH_CONCURRENCY]

        tasks = []
        for email in batch:
            provider_msg_id = email.get("provider_message_id") or email.get("message_id")
            tasks.append(_fetch_one_body(adapter, access_token, provider_msg_id))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for email, result in zip(batch, results):
            mid = email["message_id"]
            if isinstance(result, str) and result:
                bodies[mid] = result[:BODY_TRUNCATE_CHARS]
            elif isinstance(result, Exception):
                LOGGER.warning("[Digest] Failed to fetch body for %s: %s", mid, result)

        # Rate limit delay between batches
        if i + BODY_FETCH_CONCURRENCY < len(emails):
            await asyncio.sleep(BODY_FETCH_DELAY_MS / 1000)

    LOGGER.info("[Digest] Fetched %d/%d bodies", len(bodies), len(emails))
    return bodies


async def _fetch_one_body(
    adapter: GmailAdapter,
    access_token: str,
    provider_message_id: str,
) -> str:
    """Fetch a single email body."""
    return await adapter.fetch_message_body(access_token, provider_message_id)


# =============================================================================
# 3. LLM Analysis
# =============================================================================

async def analyze_batch(
    emails_with_bodies: List[Dict[str, Any]],
    person_id: Optional[str] = None,
) -> EmailBatchAnalysis:
    """
    Run a batch of emails through the LLM for triage and commitment extraction.

    If person_id is provided, injects contact preferences into the prompt
    so the LLM can personalize triage based on user-defined priorities.
    """
    from sakhi.apps.api.core.llm import call_llm

    # Build the prompt with email data
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d %H:%M UTC")

    # Fetch contact preferences for personalized triage
    prefs_context = ""
    if person_id:
        try:
            from sakhi.apps.api.services.email.contact_preferences import (
                format_preferences_for_llm,
                get_preferences,
            )
            preferences = await get_preferences(person_id)
            prefs_context = format_preferences_for_llm(preferences)
        except Exception as e:
            LOGGER.warning("[Digest] Failed to load contact preferences: %s", e)

    email_descriptions = []
    for i, email in enumerate(emails_with_bodies, 1):
        direction = email.get("direction", "incoming")
        sender = email.get("sender_name") or email.get("sender_email", "Unknown")
        subject = email.get("subject", "(no subject)")
        body = email.get("body", "")[:BODY_TRUNCATE_CHARS]
        msg_id = email.get("message_id", "")

        # Include email timestamp so LLM can judge freshness
        ts = email.get("timestamp")
        ts_str = ""
        if ts:
            if hasattr(ts, "strftime"):
                ts_str = ts.strftime("%Y-%m-%d %H:%M UTC")
            elif isinstance(ts, str):
                ts_str = ts[:19]

        email_descriptions.append(
            f"--- Email {i} ---\n"
            f"ID: {msg_id}\n"
            f"Date: {ts_str}\n"
            f"Direction: {direction}\n"
            f"From: {sender} <{email.get('sender_email', '')}>\n"
            f"Subject: {subject}\n"
            f"Body:\n{body}\n"
        )

    emails_text = "\n".join(email_descriptions)

    prompt = f"""Today's date: {today_str}

{prefs_context}

Analyze these emails. Return JSON with this EXACT structure:

{{
  "items": [
    {{
      "message_id": "<the ID from the email>",
      "subject": "<email subject>",
      "sender": "<sender email>",
      "sender_name": "<sender name or null>",
      "triage": "action" | "fyi" | "noise",
      "action_summary": "<what to do, ~15 words. Only if triage=action>",
      "deadline": "<deadline if mentioned, else null>",
      "priority": "high" | "medium" | "low",
      "draft_reply": "<suggested 1-2 sentence reply. Only if triage=action>",
      "one_line_summary": "<summary. Only if triage=fyi>"
    }}
  ],
  "commitments": [
    {{
      "commitment": "<what user promised>",
      "deadline": "<when, or null>",
      "subject": "<email subject>",
      "recipient": "<who they promised>",
      "commitment_type": "people" | "subscription"
    }}
  ]
}}

Rules:
- triage=action: needs reply or user action NOW (not in the past)
- triage=fyi: worth knowing, no action needed
- triage=noise: newsletters, automated, marketing, outdated/expired content
- Verification emails (password reset, OTP, email confirmation, security codes) are ALWAYS noise

Contact priority rules (if preferences are provided above):
- If a sender is marked "critical" or "high", prefer triage=action unless clearly noise (e.g. automated/expired)
- If a sender is marked "muted", ALWAYS classify as noise regardless of content
- If a sender is marked "low", prefer triage=fyi unless explicitly urgent
- Use the relationship and notes to inform draft reply tone and urgency assessment

Time intelligence (IMPORTANT — today is {today_str}):
- If a deadline, event date, or expiry mentioned in the email has ALREADY PASSED, classify as noise — not action.
- Meeting invites for past dates → noise. An old "Join meeting" link is useless.
- "Plan ends in 3 days" sent on Jan 31 → deadline was Feb 3. If today is past Feb 3, it's noise or fyi ("plan already ended"), NOT a high-priority action.
- If multiple emails are about the SAME topic (e.g. "plan ending" + "plan ended"), keep only the most recent/relevant one as action (if still actionable) and mark others as noise.

Memberships & renewals:
- Emails about plan expiry, subscription renewal, billing, account upgrades from automated senders (e.g. Google, Apple, AWS): classify as action but set draft_reply to null (you can't reply to noreply@).
- The action_summary should be a reminder: "Renew X plan" or "Decide whether to keep X subscription".
- ALSO extract these as a commitment: e.g. {{"commitment": "Decide on Google AI Pro renewal", "deadline": null, "recipient": "self"}}. This way the user can track and dismiss it.

Draft replies:
- Only provide draft_reply for emails from real people that warrant a response.
- Never provide draft_reply for automated/noreply senders — set to null.
- Write in a natural, warm, first-person tone — like a real person would write.
- Never start with "Thank you for the update" or other robotic openers.
- Be specific to the email content. Reference the actual topic.

Commitments:
- For outgoing emails: extract commitments the user made to real people. Set commitment_type = "people" and recipient = the person's name.
- For membership/renewal/billing emails: extract as a subscription tracker. Set commitment_type = "subscription" and recipient = "self".
- NEVER extract verification emails (password reset, OTP, email confirmation, account verification) as commitments. These are transient one-time actions, not trackable commitments.
- Deduplicate: if the user made the same promise in multiple emails (even worded differently), extract it only ONCE.
- Be concise. Every email MUST appear in items.

{emails_text}"""

    LOGGER.info("[Digest] LLM prompt length: %d chars, %d emails in batch", len(prompt), len(emails_with_bodies))

    # Call LLM without schema first to get raw JSON, then parse manually
    # This avoids the strict schema validation failing on the entire batch
    raw_text = await call_llm(
        messages=[
            {"role": "system", "content": (
                "You are an email triage assistant. Return ONLY valid JSON matching the exact schema provided. "
                "Every email must appear in the items array with the correct field names."
            )},
            {"role": "user", "content": prompt},
        ],
        model=LLM_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        response_format={"type": "json_object"},
    )

    LOGGER.info("[Digest] Raw LLM response length: %d chars", len(raw_text) if isinstance(raw_text, str) else 0)

    # Parse raw text to dict
    try:
        payload = _json.loads(raw_text) if isinstance(raw_text, str) else {}
    except Exception:
        LOGGER.warning("[Digest] Failed to parse LLM JSON response")
        return EmailBatchAnalysis(items=[], commitments=[])

    # Parse items individually (resilient to per-item errors)
    raw_items = payload.get("items", [])
    parsed_items = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        try:
            from sakhi.apps.api.services.email.digest_models import EmailTriageItem
            parsed_items.append(EmailTriageItem.model_validate(raw_item))
        except Exception:
            # Try mapping common LLM field name variations
            mapped = {
                "message_id": raw_item.get("message_id") or raw_item.get("id", ""),
                "subject": raw_item.get("subject", ""),
                "sender": raw_item.get("sender") or raw_item.get("from", ""),
                "sender_name": raw_item.get("sender_name") or raw_item.get("from_name"),
                "triage": raw_item.get("triage") or raw_item.get("category", "noise"),
                "action_summary": raw_item.get("action_summary") or raw_item.get("action"),
                "deadline": raw_item.get("deadline"),
                "priority": raw_item.get("priority", "medium"),
                "draft_reply": raw_item.get("draft_reply") or raw_item.get("reply"),
                "one_line_summary": raw_item.get("one_line_summary") or raw_item.get("summary"),
            }
            try:
                parsed_items.append(EmailTriageItem.model_validate(mapped))
            except Exception as e2:
                LOGGER.debug("[Digest] Skipping unparseable item: %s", e2)

    # Parse commitments individually
    raw_commitments = payload.get("commitments", [])
    parsed_commitments = []
    for raw_c in raw_commitments:
        if not isinstance(raw_c, dict):
            continue
        try:
            from sakhi.apps.api.services.email.digest_models import EmailCommitment
            parsed_commitments.append(EmailCommitment.model_validate(raw_c))
        except Exception:
            pass

    result = EmailBatchAnalysis(items=parsed_items, commitments=parsed_commitments)

    LOGGER.info(
        "[Digest] LLM returned %d items (%d raw), %d commitments",
        len(result.items), len(raw_items), len(result.commitments),
    )

    return result


# =============================================================================
# 4. Full Pipeline
# =============================================================================

async def generate_digest(
    person_id: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Generate a complete email digest.

    1. Check freshness cache (skip if recent digest exists)
    2. Select emails for analysis
    3. Fetch bodies transiently from Gmail
    4. Run LLM analysis in batches
    5. Assemble and store digest
    6. Discard all body content
    """
    start_time = time.time()

    # Check freshness
    if not force:
        latest = await get_latest_digest(person_id)
        if latest and latest.get("status") == "complete":
            created = latest.get("created_at")
            if created:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                age = datetime.now(timezone.utc) - created
                if age < timedelta(hours=DIGEST_FRESHNESS_HOURS):
                    LOGGER.debug("[Digest] Fresh digest exists for %s, skipping", person_id)
                    return latest

    # Get sync state and token
    state = await get_sync_state(person_id)
    if not state:
        return {"status": "not_connected"}

    # Create a pending digest record
    digest_id = await _create_digest_record(person_id)

    try:
        # Get valid token
        from sakhi.apps.api.services.email.sync import _get_valid_token
        adapter = GmailAdapter(person_id)
        access_token = await _get_valid_token(person_id, state, adapter)

        # Step 1: Select emails
        emails = await select_emails_for_digest(person_id)
        if not emails:
            await _update_digest_status(digest_id, "complete", emails_analyzed=0)
            return await get_latest_digest(person_id)

        # Step 2: Fetch bodies (transient)
        LOGGER.info("[Digest] Fetching bodies for %d emails, token=%s", len(emails), "present" if access_token else "NONE")
        bodies = await fetch_bodies_transient(adapter, access_token, emails)
        LOGGER.info("[Digest] Got %d bodies out of %d emails", len(bodies), len(emails))

        # Step 3: Merge bodies with email metadata
        emails_with_bodies = []
        for email in emails:
            mid = email["message_id"]
            body = bodies.get(mid, "")
            if body:  # Only analyze emails where we got bodies
                emails_with_bodies.append({**email, "body": body})

        LOGGER.info("[Digest] %d emails have bodies (ready for LLM)", len(emails_with_bodies))

        if not emails_with_bodies:
            LOGGER.warning("[Digest] No bodies fetched - aborting digest for %s", person_id)
            await _update_digest_status(digest_id, "complete", emails_analyzed=0)
            return await get_latest_digest(person_id)

        # Step 4: LLM analysis in batches
        all_items = []
        all_commitments = []

        batch_results = []
        for i in range(0, len(emails_with_bodies), LLM_BATCH_SIZE):
            batch = emails_with_bodies[i:i + LLM_BATCH_SIZE]
            batch_num = i // LLM_BATCH_SIZE
            try:
                analysis = await analyze_batch(batch, person_id=person_id)
                all_items.extend(analysis.items)
                all_commitments.extend(analysis.commitments)
                batch_results.append(f"batch{batch_num}={len(analysis.items)}items")
            except Exception as e:
                batch_results.append(f"batch{batch_num}=ERROR:{str(e)[:100]}")

        LOGGER.info("[Digest] Batch results: %s, total=%d items", ", ".join(batch_results), len(all_items))

        # Step 4b: Cross-batch dedup for action items from the same sender
        # (LLM only sees batches of 3, so it can't dedup across batches)
        seen_action_senders: Dict[str, int] = {}
        for i, item in enumerate(all_items):
            if item.triage != "action":
                continue
            sender_key = (item.sender or "").strip().lower()
            if sender_key in seen_action_senders:
                prev_idx = seen_action_senders[sender_key]
                # Downgrade the earlier duplicate to fyi
                prev = all_items[prev_idx]
                all_items[prev_idx] = prev.model_copy(update={"triage": "fyi", "one_line_summary": prev.action_summary})
                LOGGER.debug("[Digest] Deduped action from %s (kept newer)", sender_key)
            seen_action_senders[sender_key] = i

        # Step 4c: Filter out verification-style commitments
        pre_filter_count = len(all_commitments)
        all_commitments = [
            c for c in all_commitments
            if not _is_verification_commitment(c.commitment or "", c.subject or "")
        ]
        if len(all_commitments) < pre_filter_count:
            LOGGER.debug("[Digest] Filtered %d verification commitments", pre_filter_count - len(all_commitments))

        # Step 4d: Cross-batch dedup for commitments (by fuzzy hash)
        seen_hashes: set = set()
        deduped_commitments = []
        for c in all_commitments:
            h = _commitment_hash(
                c.commitment or "", c.recipient or "", c.subject or ""
            )
            if h not in seen_hashes:
                seen_hashes.add(h)
                deduped_commitments.append(c)
        if len(deduped_commitments) < len(all_commitments):
            LOGGER.debug("[Digest] Deduped %d → %d commitments", len(all_commitments), len(deduped_commitments))
        all_commitments = deduped_commitments

        # Step 5: Assemble digest
        action_items = [
            item.model_dump() for item in all_items
            if item.triage == "action"
        ]
        fyi_items = [
            item.model_dump() for item in all_items
            if item.triage == "fyi"
        ]
        noise_items = [
            item for item in all_items
            if item.triage == "noise"
        ]

        # Build noise summary
        noise_categories: Dict[str, int] = {}
        for item in noise_items:
            cat = "other"
            subject_lower = (item.subject or "").lower()
            if any(kw in subject_lower for kw in ["newsletter", "digest", "weekly"]):
                cat = "newsletters"
            elif any(kw in subject_lower for kw in ["sale", "off", "deal", "promo"]):
                cat = "marketing"
            elif any(kw in subject_lower for kw in ["notification", "alert", "update"]):
                cat = "notifications"
            noise_categories[cat] = noise_categories.get(cat, 0) + 1

        triage_counts = {
            "needs_action": len(action_items),
            "fyi": len(fyi_items),
            "noise": len(noise_items),
        }

        noise_summary = {
            "count": len(noise_items),
            "categories": noise_categories,
        }

        commitments = [c.model_dump() for c in all_commitments]

        generation_time_ms = int((time.time() - start_time) * 1000)

        # Step 6: Store digest (bodies already out of scope / garbage collected)
        await _store_digest(
            digest_id,
            person_id=person_id,
            triage_counts=triage_counts,
            action_items=action_items,
            fyi_items=fyi_items,
            noise_summary=noise_summary,
            commitments=commitments,
            emails_analyzed=len(emails_with_bodies),
            model_used=LLM_MODEL,
            generation_time_ms=generation_time_ms,
        )

        # Step 7: Persist commitments to dedicated table (survives digest regeneration)
        if commitments:
            await _upsert_commitments(person_id, commitments, digest_id)

        LOGGER.info(
            "[Digest] Generated for %s: %d action, %d fyi, %d noise, %d commitments (%dms)",
            person_id, len(action_items), len(fyi_items), len(noise_items),
            len(commitments), generation_time_ms,
        )

        return await get_latest_digest(person_id)

    except Exception as e:
        LOGGER.exception("[Digest] Generation failed for %s: %s", person_id, e)
        await _update_digest_status(digest_id, "error", error_message=str(e))
        return {"status": "error", "error": str(e)}


# =============================================================================
# Digest Retrieval
# =============================================================================

async def get_latest_digest(person_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent completed digest for a user."""
    row = await dbfetch(
        """
        SELECT id, digest_type, status, period_start, period_end,
               triage_counts, action_items, fyi_items, noise_summary,
               commitments, emails_analyzed, model_used,
               generation_time_ms, error_message, created_at, updated_at
        FROM email_digests
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )

    if not row:
        return None

    # Parse JSONB fields (asyncpg returns as strings)
    result = dict(row)
    for field in ("triage_counts", "action_items", "fyi_items", "noise_summary", "commitments"):
        val = result.get(field)
        if isinstance(val, str):
            result[field] = _json.loads(val)

    # Serialize datetimes
    for field in ("period_start", "period_end", "created_at", "updated_at"):
        val = result.get(field)
        if val and hasattr(val, "isoformat"):
            result[field] = val.isoformat()

    # Convert UUID to string
    if result.get("id"):
        result["id"] = str(result["id"])

    # Always use persistent commitments table (not digest JSONB snapshot)
    # Split into people commitments and subscription trackers
    result["commitments"] = await get_active_commitments(person_id, commitment_type="people")
    result["subscriptions"] = await get_active_commitments(person_id, commitment_type="subscription")

    # Filter out dismissed action items
    dismissed = await get_dismissed_action_ids(person_id)
    if dismissed and result.get("action_items"):
        original_count = len(result["action_items"])
        result["action_items"] = [
            a for a in result["action_items"]
            if a.get("message_id") not in dismissed
        ]
        if len(result["action_items"]) < original_count:
            # Update triage counts to reflect filtered actions
            if result.get("triage_counts"):
                result["triage_counts"]["needs_action"] = len(result["action_items"])

    return result


# =============================================================================
# DB Helpers
# =============================================================================

async def _create_digest_record(person_id: str) -> str:
    """Create a pending digest record and return its ID."""
    row = await dbfetch(
        """
        INSERT INTO email_digests (person_id, status, period_start, period_end)
        VALUES ($1, 'generating', $2, $3)
        RETURNING id
        """,
        person_id,
        datetime.now(timezone.utc) - timedelta(days=7),
        datetime.now(timezone.utc),
        one=True,
    )
    return str(row["id"])


async def _update_digest_status(
    digest_id: str,
    status: str,
    *,
    emails_analyzed: int = 0,
    error_message: Optional[str] = None,
) -> None:
    """Update digest status."""
    await dbexec(
        """
        UPDATE email_digests
        SET status = $2, emails_analyzed = $3, error_message = $4, updated_at = NOW()
        WHERE id = $1
        """,
        digest_id,
        status,
        emails_analyzed,
        error_message,
    )


async def _store_digest(
    digest_id: str,
    *,
    person_id: str,
    triage_counts: Dict[str, Any],
    action_items: List[Dict[str, Any]],
    fyi_items: List[Dict[str, Any]],
    noise_summary: Dict[str, Any],
    commitments: List[Dict[str, Any]],
    emails_analyzed: int,
    model_used: str,
    generation_time_ms: int,
) -> None:
    """Store the completed digest."""
    await dbexec(
        """
        UPDATE email_digests
        SET status = 'complete',
            triage_counts = $2::jsonb,
            action_items = $3::jsonb,
            fyi_items = $4::jsonb,
            noise_summary = $5::jsonb,
            commitments = $6::jsonb,
            emails_analyzed = $7,
            model_used = $8,
            generation_time_ms = $9,
            updated_at = NOW()
        WHERE id = $1
        """,
        digest_id,
        _json.dumps(triage_counts),
        _json.dumps(action_items),
        _json.dumps(fyi_items),
        _json.dumps(noise_summary),
        _json.dumps(commitments),
        emails_analyzed,
        model_used,
        generation_time_ms,
    )


# =============================================================================
# Commitment Persistence
# =============================================================================

_STOP_WORDS = frozenset(
    "a an the to for with of in on by from using and or but is are was were "
    "will shall would could should can may might be been being have has had "
    "do does did that this these those it its i me my we our they them their "
    "your you he she him her provided prepared".split()
)


def _extract_key_words(text: str, max_words: int = 4) -> str:
    """Extract top N alphabetic content words (sorted) for fuzzy matching."""
    words = re.findall(r"[a-z]{3,}", text.strip().lower())
    key_words = sorted(set(w for w in words if w not in _STOP_WORDS))
    return " ".join(key_words[:max_words])


def _commitment_hash(commitment: str, recipient: str, subject: str) -> str:
    """Generate a fuzzy hash for deduplicating commitments across digests.

    Uses top-4 alphabetic content words (sorted, stop words removed) so that
    "Prepare for the call with Jeff Immelt using the provided script"
    and "Prepare for the 1:1 call with Jeff Immelt" produce the same hash.
    """
    norm_subject = _extract_key_words(subject)
    norm_commitment = _extract_key_words(commitment)
    raw = f"{norm_subject}|{norm_commitment}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _upsert_commitments(
    person_id: str,
    commitments: List[Dict[str, Any]],
    digest_id: str,
) -> int:
    """
    Persist new commitments to email_commitments table.

    Uses ON CONFLICT DO NOTHING so existing commitments (even if marked
    done/dismissed) are never overwritten.

    Returns number of new commitments inserted.
    """
    inserted = 0
    for c in commitments:
        text = c.get("commitment", "")
        recipient = c.get("recipient", "")
        subject = c.get("subject", "")
        ctype = c.get("commitment_type", "people")
        if not text:
            continue

        # Infer type from recipient if LLM didn't set it
        if ctype not in ("people", "subscription"):
            ctype = "subscription" if (recipient or "").lower() == "self" else "people"

        chash = _commitment_hash(text, recipient, subject)
        try:
            row = await dbfetch(
                """
                INSERT INTO email_commitments (
                    person_id, commitment_hash, commitment, deadline,
                    subject, recipient, source_digest_id, commitment_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (person_id, commitment_hash) DO NOTHING
                RETURNING id
                """,
                person_id,
                chash,
                text,
                c.get("deadline"),
                subject,
                recipient,
                digest_id,
                ctype,
                one=True,
            )
            if row:
                inserted += 1
        except Exception as e:
            LOGGER.debug("[Digest] Failed to upsert commitment: %s", e)

    LOGGER.info("[Digest] Upserted %d/%d commitments for %s", inserted, len(commitments), person_id)
    return inserted


async def get_active_commitments(
    person_id: str,
    commitment_type: Optional[str] = "people",
) -> List[Dict[str, Any]]:
    """Get active commitments for a user, filtered by type.

    Args:
        commitment_type: 'people' for person-to-person, 'subscription' for
            memberships/renewals, or None for all types.
    """
    if commitment_type:
        rows = await dbfetch(
            """
            SELECT id, commitment, deadline, subject, recipient,
                   commitment_type, status, extracted_at, created_at
            FROM email_commitments
            WHERE person_id = $1 AND status = 'active' AND commitment_type = $2
            ORDER BY extracted_at DESC
            """,
            person_id,
            commitment_type,
        )
    else:
        rows = await dbfetch(
            """
            SELECT id, commitment, deadline, subject, recipient,
                   commitment_type, status, extracted_at, created_at
            FROM email_commitments
            WHERE person_id = $1 AND status = 'active'
            ORDER BY extracted_at DESC
            """,
            person_id,
        )

    result = []
    for row in rows or []:
        item = dict(row)
        # Convert UUID/datetime for JSON serialization
        if item.get("id"):
            item["id"] = str(item["id"])
        for dt_field in ("extracted_at", "created_at"):
            val = item.get(dt_field)
            if val and hasattr(val, "isoformat"):
                item[dt_field] = val.isoformat()
        result.append(item)

    return result


async def update_commitment_status(
    commitment_id: str,
    person_id: str,
    status: str,
) -> bool:
    """Update a commitment's status. Returns True if updated."""
    if status not in ("done", "dismissed"):
        return False

    result = await dbexec(
        """
        UPDATE email_commitments
        SET status = $3, status_changed_at = NOW()
        WHERE id = $1 AND person_id = $2 AND status = 'active'
        """,
        commitment_id,
        person_id,
        status,
    )
    return True


# =============================================================================
# Dismissed Action Items
# =============================================================================

async def dismiss_action_item(person_id: str, message_id: str) -> bool:
    """Dismiss an action item so it doesn't show up in future digests."""
    try:
        await dbexec(
            """
            INSERT INTO email_dismissed_actions (person_id, message_id)
            VALUES ($1, $2)
            ON CONFLICT (person_id, message_id) DO NOTHING
            """,
            person_id,
            message_id,
        )
        return True
    except Exception as e:
        LOGGER.debug("[Digest] Failed to dismiss action: %s", e)
        return False


async def get_dismissed_action_ids(person_id: str) -> set:
    """Get set of dismissed action message_ids for a user."""
    rows = await dbfetch(
        """
        SELECT message_id
        FROM email_dismissed_actions
        WHERE person_id = $1
        """,
        person_id,
    )
    return {row["message_id"] for row in rows or []}


# =============================================================================
# Send Reply
# =============================================================================

async def send_reply(
    person_id: str,
    message_id: str,
    reply_body: str,
) -> Dict[str, Any]:
    """
    Send a reply to an email via Gmail API.

    The message_id is the internal message_id (e.g. "gmail:abc123").
    The reply is threaded properly using the original message's headers.
    """
    # Look up the provider_message_id
    row = await dbfetch(
        """
        SELECT provider_message_id
        FROM email_events
        WHERE person_id = $1 AND message_id = $2
        LIMIT 1
        """,
        person_id,
        message_id,
        one=True,
    )

    if not row:
        return {"error": "Email not found", "sent": False}

    provider_msg_id = row["provider_message_id"]

    # Get sync state for access token
    state = await get_sync_state(person_id)
    if not state:
        return {"error": "Email not connected", "sent": False}

    try:
        from sakhi.apps.api.services.email.sync import _get_valid_token
        adapter = GmailAdapter(person_id)
        access_token = await _get_valid_token(person_id, state, adapter)

        result = await adapter.send_reply(access_token, provider_msg_id, reply_body)

        LOGGER.info("[Digest] Reply sent for %s, message=%s", person_id, message_id)
        return {
            "sent": True,
            "gmail_message_id": result.get("id"),
            "thread_id": result.get("threadId"),
        }
    except Exception as e:
        LOGGER.exception("[Digest] Failed to send reply for %s: %s", person_id, e)
        return {"error": str(e), "sent": False}


# =============================================================================
# Single Email Peek (transient body fetch for detail view)
# =============================================================================

async def fetch_email_detail(
    person_id: str,
    message_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single email's metadata + body for the peek/context view.

    The body is fetched transiently from Gmail and never stored.
    Returns None if email not found or not connected.
    """
    # Get email metadata from DB
    row = await dbfetch(
        """
        SELECT message_id, provider_message_id, thread_id, subject,
               sender_email, sender_name, direction, timestamp
        FROM email_events
        WHERE person_id = $1 AND message_id = $2
        LIMIT 1
        """,
        person_id,
        message_id,
        one=True,
    )

    if not row:
        return None

    email_meta = dict(row)

    # Serialize timestamp
    ts = email_meta.get("timestamp")
    if ts and hasattr(ts, "isoformat"):
        email_meta["timestamp"] = ts.isoformat()

    # Get sync state for access token
    state = await get_sync_state(person_id)
    if not state:
        return {**email_meta, "body": None, "gmail_url": None}

    # Fetch body transiently
    body = None
    try:
        from sakhi.apps.api.services.email.sync import _get_valid_token
        adapter = GmailAdapter(person_id)
        access_token = await _get_valid_token(person_id, state, adapter)
        provider_msg_id = email_meta.get("provider_message_id") or message_id
        body = await adapter.fetch_message_body(access_token, provider_msg_id)
    except Exception as e:
        LOGGER.warning("[Digest] Failed to fetch body for peek: %s", e)

    # Gmail web URL
    provider_msg_id = email_meta.get("provider_message_id")
    gmail_url = (
        f"https://mail.google.com/mail/u/0/#inbox/{provider_msg_id}"
        if provider_msg_id
        else None
    )

    return {
        **email_meta,
        "body": body,
        "gmail_url": gmail_url,
    }


__all__ = [
    "generate_digest",
    "get_latest_digest",
    "select_emails_for_digest",
    "fetch_bodies_transient",
    "analyze_batch",
    "get_active_commitments",
    "update_commitment_status",
    "dismiss_action_item",
    "get_dismissed_action_ids",
    "fetch_email_detail",
    "send_reply",
]

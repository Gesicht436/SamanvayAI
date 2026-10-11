"""Candidate Retrieval Pipeline.

Implements Section 4.5 candidate generation:
1. Alias exact lookup (golden_aliases).
2. OEM part number exact lookup.
3. Block key lookup (category, subcategory, primary dimension value + unit).
4. Fuzzy candidate recall in block using trigram similarity and Jaro-Winkler,
   falling back to (category, subcategory) when block is empty or primary dimension is NULL (marked PARTIAL_BLOCK).
5. At most 200 candidates.
6. Compares in application code without hard-attribute SQL filters (NULL-safe).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.jaro_winkler import jaro_winkler
from api.core.trigram import similarity as trigram_similarity
from api.extractors.registry import IdentityMode, default_registry
from api.models.entities import GoldenAlias, GoldenMaster
from api.services.classify import SUBCATEGORY_MAP


@dataclass
class RetrievedCandidate:
    """A golden master candidate retrieved for attribute comparison."""

    golden_master_id: UUID | str
    golden_code: str
    descriptor: str
    subcategory: str
    canonical_text: str
    attributes: dict[str, Any]
    block_key: str
    identity_mode: IdentityMode = IdentityMode.PARAMETRIC
    oem_name_norm: str | None = None
    oem_part_number_norm: str | None = None
    alias_exact: bool = False
    mpn_exact: bool = False
    is_partial_block: bool = False
    retrieval_score: float = 0.0
    retrieval_method: str = "block_fuzzy"  # "alias_exact", "mpn_exact", "block_fuzzy", "fallback_subcategory"


def compute_block_key(subcategory: str, extracted_attrs: dict[str, Any]) -> tuple[str, bool]:
    """Computes the candidate retrieval block key from primary dimension.

    Args:
        subcategory: Canonical subcategory (e.g. 'VALVES.GATE').
        extracted_attrs: Dictionary of extracted attribute values.

    Returns:
        tuple of (block_key, is_partial_block)
    """
    major = SUBCATEGORY_MAP.get(subcategory, subcategory.split(".")[0])
    spec = default_registry.get_spec(subcategory)

    if not spec or not spec.primary_dimension:
        # No primary dimension defined for family
        return f"{major}:{subcategory}:GENERAL", False

    prim = spec.primary_dimension
    attr_name = prim.attr
    unit = prim.unit

    val = extracted_attrs.get(attr_name)
    if val is None or val == "":
        # Primary dimension missing or null -> PARTIAL_BLOCK
        return f"{major}:{subcategory}:NULL", True

    val_str = str(val).strip().upper()
    return f"{major}:{subcategory}:{attr_name}={val_str}_{unit}", False


def rank_candidate_fuzzy(query_text: str, candidate_text: str) -> float:
    """Computes candidate retrieval score combining trigram and Jaro-Winkler."""
    tri_sim = trigram_similarity(query_text, candidate_text)
    jw_sim = jaro_winkler(query_text.lower(), candidate_text.lower())
    return 0.7 * tri_sim + 0.3 * jw_sim


async def retrieve_candidates_db(
    session: AsyncSession,
    clean_text: str,
    subcategory: str,
    extracted_attrs: dict[str, Any],
    top_k: int = 10,
    org_id: str | None = None,
) -> list[RetrievedCandidate]:
    """Retrieves golden master candidates from PostgreSQL.

    Strictly executes retrieval stages in order:
    1. Alias exact lookup.
    2. OEM part-number exact lookup.
    3. Block key exact lookup.
    4. Fuzzy candidate recall in block (falling back to subcategory if empty/null).
    """
    top_k = min(max(1, top_k), 200)
    seen_ids: set[UUID] = set()
    results: list[RetrievedCandidate] = []

    clean_norm = clean_text.strip().upper()

    # -------------------------------------------------------------
    # Stage 1: Alias exact lookup
    # -------------------------------------------------------------
    alias_stmt = (
        select(GoldenMaster)
        .join(GoldenAlias, GoldenAlias.golden_id == GoldenMaster.id)
        .where(
            GoldenMaster.status != "DEPRECATED",
            GoldenAlias.value_norm == clean_norm,
            or_(GoldenAlias.org_id == org_id, GoldenAlias.org_id.is_(None)),
        )
        .limit(top_k)
    )
    alias_res = await session.execute(alias_stmt)
    for master in alias_res.scalars().all():
        if master.id not in seen_ids:
            seen_ids.add(master.id)
            results.append(
                RetrievedCandidate(
                    golden_master_id=master.id,
                    golden_code=master.code,
                    descriptor=master.descriptor,
                    subcategory=master.subcategory,
                    canonical_text=master.canonical_text,
                    attributes=master.attributes or {},
                    block_key=master.block_key,
                    identity_mode=IdentityMode(master.identity_mode),
                    oem_name_norm=master.oem_name_norm,
                    oem_part_number_norm=master.oem_part_number_norm,
                    alias_exact=True,
                    retrieval_score=1.0,
                    retrieval_method="alias_exact",
                )
            )

    # -------------------------------------------------------------
    # Stage 2: OEM part-number exact lookup
    # -------------------------------------------------------------
    mpn_token: str | None = None
    # Check if raw item contains MPN or drawing number
    for mpn_key in ("oem_part_number", "part_number", "drawing_number", "base_designation"):
        if extracted_attrs.get(mpn_key):
            mpn_token = str(extracted_attrs[mpn_key]).strip().upper()
            break

    if mpn_token:
        mpn_stmt = (
            select(GoldenMaster)
            .where(
                GoldenMaster.status != "DEPRECATED",
                GoldenMaster.oem_part_number_norm == mpn_token,
            )
            .limit(top_k)
        )
        mpn_res = await session.execute(mpn_stmt)
        for master in mpn_res.scalars().all():
            if master.id not in seen_ids:
                seen_ids.add(master.id)
                results.append(
                    RetrievedCandidate(
                        golden_master_id=master.id,
                        golden_code=master.code,
                        descriptor=master.descriptor,
                        subcategory=master.subcategory,
                        canonical_text=master.canonical_text,
                        attributes=master.attributes or {},
                        block_key=master.block_key,
                        identity_mode=IdentityMode(master.identity_mode),
                        oem_name_norm=master.oem_name_norm,
                        oem_part_number_norm=master.oem_part_number_norm,
                        mpn_exact=True,
                        retrieval_score=0.99,
                        retrieval_method="mpn_exact",
                    )
                )

    # -------------------------------------------------------------
    # Stage 3 & 4: Block key lookup & Fuzzy recall
    # -------------------------------------------------------------
    block_key, is_partial = compute_block_key(subcategory, extracted_attrs)

    # Query masters in the specific block
    block_candidates: list[GoldenMaster] = []
    if not is_partial:
        block_stmt = (
            select(GoldenMaster)
            .where(
                GoldenMaster.status != "DEPRECATED",
                GoldenMaster.subcategory == subcategory,
                GoldenMaster.block_key == block_key,
            )
            .limit(top_k * 3)
        )
        b_res = await session.execute(block_stmt)
        block_candidates = list(b_res.scalars().all())

    is_fallback = False
    if not block_candidates or is_partial:
        # Fall back to (category, subcategory) and mark PARTIAL_BLOCK
        is_fallback = True
        fallback_stmt = (
            select(GoldenMaster)
            .where(
                GoldenMaster.status != "DEPRECATED",
                GoldenMaster.subcategory == subcategory,
            )
            .limit(top_k * 4)
        )
        f_res = await session.execute(fallback_stmt)
        block_candidates = list(f_res.scalars().all())

    # Rank fuzzy candidates
    fuzzy_scored: list[tuple[float, GoldenMaster]] = []
    for master in block_candidates:
        if master.id in seen_ids:
            continue
        score = rank_candidate_fuzzy(clean_text, master.canonical_text)
        fuzzy_scored.append((score, master))

    fuzzy_scored.sort(key=lambda x: x[0], reverse=True)

    for score, master in fuzzy_scored:
        if len(results) >= top_k:
            break
        seen_ids.add(master.id)
        results.append(
            RetrievedCandidate(
                golden_master_id=master.id,
                golden_code=master.code,
                descriptor=master.descriptor,
                subcategory=master.subcategory,
                canonical_text=master.canonical_text,
                attributes=master.attributes or {},
                block_key=master.block_key,
                identity_mode=IdentityMode(master.identity_mode),
                oem_name_norm=master.oem_name_norm,
                oem_part_number_norm=master.oem_part_number_norm,
                is_partial_block=is_fallback,
                retrieval_score=score,
                retrieval_method="fallback_subcategory" if is_fallback else "block_fuzzy",
            )
        )

    # -------------------------------------------------------------
    # Stage 5: Vector Recall (Section 8.1 - active only if ML_LAYER=on)
    # -------------------------------------------------------------
    from api.config import get_settings
    if get_settings().ml_layer == "on" and len(results) < top_k:
        from api.ml.subvectors import build_domain_texts, calculate_composite_cosine

        raw_dom_texts = build_domain_texts(extracted_attrs)
        vr_stmt = (
            select(GoldenMaster)
            .where(
                GoldenMaster.status != "DEPRECATED",
                GoldenMaster.subcategory == subcategory,
            )
            .limit(top_k * 4)
        )
        vr_res = await session.execute(vr_stmt)
        vr_candidates = list(vr_res.scalars().all())
        vr_scored: list[tuple[float, GoldenMaster]] = []
        for master in vr_candidates:
            if master.id in seen_ids:
                continue
            cand_dom_texts = build_domain_texts(master.attributes or {})
            cos_score, _ = calculate_composite_cosine(raw_dom_texts, cand_dom_texts, subcategory)
            if cos_score >= 0.40:
                vr_scored.append((cos_score, master))
        vr_scored.sort(key=lambda x: x[0], reverse=True)
        for score, master in vr_scored:
            if len(results) >= top_k:
                break
            seen_ids.add(master.id)
            results.append(
                RetrievedCandidate(
                    golden_master_id=master.id,
                    golden_code=master.code,
                    descriptor=master.descriptor,
                    subcategory=master.subcategory,
                    canonical_text=master.canonical_text,
                    attributes=master.attributes or {},
                    block_key=master.block_key,
                    identity_mode=IdentityMode(master.identity_mode),
                    oem_name_norm=master.oem_name_norm,
                    oem_part_number_norm=master.oem_part_number_norm,
                    retrieval_score=score,
                    retrieval_method="VECTOR_RECALL",
                )
            )

    return results[:top_k]


def retrieve_candidates_in_memory(
    candidate_pool: list[RetrievedCandidate],
    clean_text: str,
    subcategory: str,
    extracted_attrs: dict[str, Any],
    top_k: int = 10,
    aliases_map: dict[str, list[str]] | None = None,
) -> list[RetrievedCandidate]:
    """In-memory candidate retrieval pipeline for testing, batch processing, and offline evaluation.

    Follows the exact same 4-stage retrieval priority as the database pipeline.
    """
    top_k = min(max(1, top_k), 200)
    seen_ids: set[str | UUID] = set()
    results: list[RetrievedCandidate] = []
    clean_norm = clean_text.strip().upper()
    aliases = aliases_map or {}

    # 1. Alias exact lookup
    for cand in candidate_pool:
        cid_str = str(cand.golden_master_id)
        cand_aliases = [a.strip().upper() for a in aliases.get(cid_str, [])]
        if clean_norm in cand_aliases and cand.golden_master_id not in seen_ids:
            seen_ids.add(cand.golden_master_id)
            cand.alias_exact = True
            cand.retrieval_score = 1.0
            cand.retrieval_method = "alias_exact"
            results.append(cand)

    # 2. OEM part number exact lookup
    mpn_token: str | None = None
    for mpn_key in ("oem_part_number", "part_number", "drawing_number", "base_designation"):
        if extracted_attrs.get(mpn_key):
            mpn_token = str(extracted_attrs[mpn_key]).strip().upper()
            break

    if mpn_token:
        for cand in candidate_pool:
            if cand.golden_master_id in seen_ids:
                continue
            if cand.oem_part_number_norm and cand.oem_part_number_norm.upper() == mpn_token:
                seen_ids.add(cand.golden_master_id)
                cand.mpn_exact = True
                cand.retrieval_score = 0.99
                cand.retrieval_method = "mpn_exact"
                results.append(cand)

    # 3. Block key lookup
    block_key, is_partial = compute_block_key(subcategory, extracted_attrs)

    block_candidates = [c for c in candidate_pool if c.subcategory == subcategory and c.block_key == block_key]

    is_fallback = False
    if not block_candidates or is_partial:
        # Fall back to subcategory
        is_fallback = True
        block_candidates = [c for c in candidate_pool if c.subcategory == subcategory]

    # Rank fuzzy
    fuzzy_scored: list[tuple[float, RetrievedCandidate]] = []
    for cand in block_candidates:
        if cand.golden_master_id in seen_ids:
            continue
        score = rank_candidate_fuzzy(clean_text, cand.canonical_text)
        fuzzy_scored.append((score, cand))

    fuzzy_scored.sort(key=lambda x: x[0], reverse=True)

    for score, cand in fuzzy_scored:
        if len(results) >= top_k:
            break
        seen_ids.add(cand.golden_master_id)
        cand.is_partial_block = is_fallback
        cand.retrieval_score = score
        cand.retrieval_method = "fallback_subcategory" if is_fallback else "block_fuzzy"
        results.append(cand)

    # 5. Vector Recall (Section 8.1 - active only if ML_LAYER=on)
    from api.config import get_settings
    if get_settings().ml_layer == "on" and len(results) < top_k:
        from api.ml.subvectors import build_domain_texts, calculate_composite_cosine

        raw_dom_texts = build_domain_texts(extracted_attrs)
        vr_scored: list[tuple[float, RetrievedCandidate]] = []
        for cand in candidate_pool:
            if cand.golden_master_id in seen_ids or cand.subcategory != subcategory:
                continue
            cand_dom_texts = build_domain_texts(cand.attributes or {})
            cos_score, _ = calculate_composite_cosine(raw_dom_texts, cand_dom_texts, subcategory)
            if cos_score >= 0.40:
                vr_scored.append((cos_score, cand))
        vr_scored.sort(key=lambda x: x[0], reverse=True)
        for score, cand in vr_scored:
            if len(results) >= top_k:
                break
            seen_ids.add(cand.golden_master_id)
            cand.retrieval_score = score
            cand.retrieval_method = "VECTOR_RECALL"
            results.append(cand)

    return results[:top_k]

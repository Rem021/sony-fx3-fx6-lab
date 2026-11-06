#!/usr/bin/env python3
"""Pure host design counterexamples; no production imports, VM, HTTP or browser.

The oracle revision/completeness fields are ASSUMED evidence, not available FX3
signals. A passing oracle policy demonstrates a necessary contract only.
"""
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path


@dataclass(frozen=True)
class State:
    run: str = "run-A"
    lifecycle: int = 1
    context_revision: int = 1  # Hypothetical complete native semantic revision.
    screen: str = "menu-A"
    focus: str = "item-1"
    resource: str = "raster-1"
    png: str = "PNG-A"
    generation: int = 1
    steps: int = 0
    ready: bool = True
    render_valid: bool = True
    pending: bool = False
    review_required: bool = False
    error: bool = False
    stopped: bool = False
    delivery_unknown: bool = False
    complete_context_evidence: bool = True


def base(s):
    return (s.ready and s.render_valid and not s.pending and not s.review_required
            and not s.error and not s.stopped and not s.delivery_unknown)


def steps_ready(old, now):
    return base(now) and old.steps == now.steps


def png_identity(old, now):
    return base(now) and (old.png, old.generation) == (now.png, now.generation)


def oracle_context(old, now, consumed=False):
    return (base(now) and now.complete_context_evidence and not consumed
            and (old.run, old.lifecycle, old.context_revision, old.steps)
            == (now.run, now.lifecycle, now.context_revision, now.steps))


def protocol_cases():
    old = State()
    out = []

    def case(name, now, unsafe_policy, unsafe_accepts, oracle_accepts, trace,
             *, seen=old, consumed=False):
        actual = unsafe_policy(seen, now)
        oracle = oracle_context(seen, now, consumed)
        assert actual == unsafe_accepts, name
        assert oracle == oracle_accepts, name
        out.append(dict(name=name, trace=trace, clicked=asdict(seen),
                        at_admission=asdict(now), simplified_policy_accepts=actual,
                        hypothetical_complete_context_policy_accepts=oracle))

    case("steps_ready_misses_unsolicited_menu", replace(old, screen="modal-B", png="PNG-B",
         generation=2, context_revision=2), steps_ready, True, False,
         ["see A", "native timer opens B; no host key", "send old OK with steps=0"])
    case("screen_id_misses_focus", replace(old, focus="item-2", png="PNG-focus-2",
         generation=2, context_revision=2),
         lambda a,b: steps_ready(a,b) and a.screen == b.screen, True, False,
         ["see item-1", "same screen focus becomes item-2", "old OK selects item-2"])
    case("raster_identity_misses_menu", replace(old, screen="menu-B", png="PNG-B",
         generation=2, context_revision=2),
         lambda a,b: steps_ready(a,b) and a.resource == b.resource, True, False,
         ["A and B reuse one raster allocation", "old click targets B"])
    case("same_png_can_hide_semantic_change", replace(old, screen="menu-B",
         context_revision=2), png_identity, True, False,
         ["native receiver changes before next published frame", "PNG+generation still A"])
    case("sha_only_ABA", replace(old, generation=3, context_revision=3),
         lambda a,b: base(b) and a.png == b.png, True, False,
         ["A -> B -> A; same PNG again", "old incarnation click arrives"])
    case("whitelist_or_mask_has_no_context_proof", replace(old, screen="modal-B",
         png="PNG-B", generation=2, context_revision=2),
         lambda a,b: steps_ready(a,b) and b.png in {"PNG-A", "PNG-B"}, True, False,
         ["two allowed PNGs need not share receiver", "old click accepted on B"])
    case("preflight_rebinds_original_intent", replace(old, screen="menu-B", png="PNG-B",
         generation=2, context_revision=2), lambda a,b: png_identity(b,b), True, False,
         ["click A", "preflight sees B", "overwrite observed identity with B", "send old key"])
    case("queue_to_write_race", replace(old, screen="modal-B", context_revision=2),
         lambda a,b: png_identity(a,a), True, False,
         ["validate A at HTTP lock", "native transition B", "write key without revalidation"])
    case("snapshot_to_consume_race", replace(old, screen="modal-B", context_revision=2),
         lambda a,b: oracle_context(a,a), True, False,
         ["paused snapshot proves A", "resume", "queued transition B wins before native key handler"])
    case("consumed_permit_replay", replace(old, steps=1), png_identity, True, False,
         ["same-context no-change key accepted", "review completes", "delayed duplicate arrives"],
         consumed=True)
    case("cosmetic_change_needs_real_equivalence", replace(old, png="PNG-cosmetic",
         generation=2), png_identity, False, True,
         ["hypothetically proven same context", "cosmetic refresh", "one old-frame click allowed"])
    case("unknown_context_fails_closed", replace(old, complete_context_evidence=False),
         steps_ready, True, False, ["no complete semantic observer", "steps=0 alone cannot authorize"])
    case("lifecycle_restart_with_reused_ids", replace(old, run="run-B", lifecycle=2),
         steps_ready, True, False, ["same counters/PNG after restart", "old permit invalid"])
    return out


def recovery_allowed(*, outcome, own_no_enqueue_proven=True, steps_unchanged=True,
                     outstanding_accepted=False, current_ready=True, current_loaded=True,
                     native_error=False, new_human_click=True, attempt_matches=True,
                     nonce_matches=True, mutation_in_flight=False):
    """New manual attempt only; never replay the refused request or clear native timer."""
    return (outcome in {"local_no_post", "explicit_server_rejection"}
            and own_no_enqueue_proven and steps_unchanged and not outstanding_accepted
            and current_ready and current_loaded and not native_error and new_human_click
            and attempt_matches and nonce_matches and not mutation_in_flight)


def recovery_cases():
    cases = [
        ("local_preflight_no_post", dict(outcome="local_no_post"), True),
        ("explicit_409_then_human_click", dict(outcome="explicit_server_rejection"), True),
        ("5xx_unknown_even_if_steps_unchanged", dict(outcome="5xx_unknown"), False),
        ("network_timeout_even_if_ready", dict(outcome="network_timeout"), False),
        ("409_does_not_cancel_other_accepted_step", dict(outcome="explicit_server_rejection",
         outstanding_accepted=True), False),
        ("unloaded_new_frame", dict(outcome="explicit_server_rejection", current_loaded=False), False),
        ("automatic_retry_forbidden", dict(outcome="explicit_server_rejection", new_human_click=False), False),
        ("native_error_outranks_local_409", dict(outcome="explicit_server_rejection", native_error=True), False),
        ("old_rejection_is_not_current_attempt", dict(outcome="explicit_server_rejection",
         attempt_matches=False), False),
        ("old_hint_during_new_POST", dict(outcome="explicit_server_rejection",
         mutation_in_flight=True), False),
        ("rejection_cannot_cancel_another_alarm", dict(outcome="explicit_server_rejection",
         nonce_matches=False), False),
    ]
    rows = []
    for name, inputs, expected in cases:
        actual = recovery_allowed(**inputs)
        assert actual == expected, name
        rows.append(dict(name=name, inputs=inputs, may_begin_new_manual_attempt=actual))
    return rows


if __name__ == "__main__":
    result = dict(scope="abstract host model only; no FX3 execution or verified native context",
                  protocol_cases=protocol_cases(), recovery_cases=recovery_cases())
    path = Path(__file__).with_name("host-model-results.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS {len(result['protocol_cases'])} protocol + {len(result['recovery_cases'])} recovery assertions")

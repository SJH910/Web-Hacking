"""Server-only companion contract; no scoring, model SDK, or network access."""
import json

STANCES = {"optimistic_error", "pessimistic_error", "evidence_guidance", "acknowledge"}
STAGES = {"exploration", "judgment", "feedback"}


class ValidationError(ValueError):
    pass


def obj(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValidationError("Unexpected or missing fields")


def text(value, limit):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValidationError("Invalid string")


def refs(value, available):
    if type(value) is not list or any(type(v) is not str for v in value):
        raise ValidationError("Invalid evidence references")
    if len(set(value)) != len(value) or not set(value) <= available:
        raise ValidationError("Unknown or duplicate evidence references")


def validate_context(c):
    """Input must be built from authoritative backend state, never client JSON."""
    obj(c, ("scenario_id", "stage", "visible_evidence", "player_claim",
            "backend_feedback", "raon_trust", "hint_directive"))
    text(c["scenario_id"], 128)
    if type(c["stage"]) is not str or c["stage"] not in STAGES:
        raise ValidationError("Invalid stage")
    if type(c["raon_trust"]) is not int or not 0 <= c["raon_trust"] <= 100:
        raise ValidationError("Invalid trust")
    evidence = c["visible_evidence"]
    if type(evidence) is not list or len(evidence) > 50:
        raise ValidationError("Invalid evidence")
    ids = set()
    for e in evidence:
        obj(e, ("id", "content"))
        text(e["id"], 128)
        text(e["content"], 4000)
        if e["id"] in ids:
            raise ValidationError("Duplicate evidence ID")
        ids.add(e["id"])
    claim = c["player_claim"]
    if claim is not None:
        obj(claim, ("text", "evidence_ids"))
        text(claim["text"], 2000)
        refs(claim["evidence_ids"], ids)
    feedback = c["backend_feedback"]
    if feedback is not None:
        obj(feedback, ("claim_status", "reason"))
        if feedback["claim_status"] not in ("supported", "unsupported", "inconclusive"):
            raise ValidationError("Invalid claim status")
        text(feedback["reason"], 500)
    h = c["hint_directive"]
    obj(h, ("stance", "hint_level", "verification_cue"))
    if type(h["stance"]) is not str or h["stance"] not in STANCES:
        raise ValidationError("Invalid stance")
    if h["hint_level"] not in ("basic", "focused", "detailed"):
        raise ValidationError("Invalid hint level")
    text(h["verification_cue"], 200)
    if h["stance"] in ("optimistic_error", "pessimistic_error") and not ids:
        raise ValidationError("Error stance requires visible evidence")
    if h["stance"] == "acknowledge" and not (
        c["stage"] == "feedback" and claim and claim["evidence_ids"]
        and feedback and feedback["claim_status"] == "supported"
    ):
        raise ValidationError("Acknowledgement requires backend-supported evidence")
    return c


def validate_response(raw, context):
    validate_context(context)
    if isinstance(raw, str):
        if len(raw) > 10000:
            raise ValidationError("Response too large")
        def pairs(items):
            d = {}
            for k, v in items:
                if k in d:
                    raise ValidationError("Duplicate JSON key")
                d[k] = v
            return d
        try:
            raw = json.loads(raw, object_pairs_hook=pairs)
        except (ValueError, TypeError) as exc:
            raise ValidationError("Invalid JSON") from exc
    obj(raw, ("schema_version", "scenario_id", "stance", "dialogue",
              "evidence_refs", "verification_cue"))
    if raw["schema_version"] != "1.0" or raw["scenario_id"] != context["scenario_id"]:
        raise ValidationError("Version or scenario mismatch")
    if raw["stance"] != context["hint_directive"]["stance"]:
        raise ValidationError("Stance mismatch")
    text(raw["dialogue"], 300)
    text(raw["verification_cue"], 200)
    refs(raw["evidence_refs"], {e["id"] for e in context["visible_evidence"]})
    if context["visible_evidence"] and not raw["evidence_refs"]:
        raise ValidationError("Evidence reference required")
    if raw["verification_cue"] != context["hint_directive"]["verification_cue"]:
        raise ValidationError("Only the backend-approved cue is permitted")
    return raw


def fallback(context):
    """Never quote failed model output or claim that a model generated this hint."""
    validate_context(context)
    cue = context["hint_directive"]["verification_cue"]
    dialogue = "현재 AI 응답 대신 규칙 기반 안내를 제공합니다."
    if context["hint_directive"]["stance"] == "acknowledge":
        dialogue += " 제출한 증거가 주장을 뒷받침한다는 서버 확인을 받았어요. 앞선 판단을 수정할게요."
    return {
        "response": {
            "schema_version": "1.0", "scenario_id": context["scenario_id"],
            "stance": "acknowledge" if context["hint_directive"]["stance"] == "acknowledge"
                      else "evidence_guidance",
            "dialogue": dialogue,
            "evidence_refs": [e["id"] for e in context["visible_evidence"]],
            "verification_cue": cue,
        },
        "hint": {"level": {"basic": 1, "focused": 2, "detailed": 3}[
            context["hint_directive"]["hint_level"]], "text": dialogue + " " + cue, "source": "rule"},
        "source": "rule", "is_fallback": True,
    }


def generate(context, provider=None):
    """Provider must enforce its own network timeout; exceptions trigger L4.
    Invalid backend context is rejected before any provider call.
    """
    validate_context(context)
    if provider is not None:
        try:
            # Isolate trusted state from accidental provider mutation.
            output = validate_response(provider(json.loads(json.dumps(context))), context)
            return {"response": output,
                    "hint": {"level": {"basic": 1, "focused": 2, "detailed": 3}[
                        context["hint_directive"]["hint_level"]],
                        "text": output["dialogue"] + " " + output["verification_cue"],
                        "source": "llm"},
                    "source": "llm", "is_fallback": False}
        except Exception:
            # Do not log potentially sensitive failed model output.
            pass
    return fallback(context)

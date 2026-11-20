import copy
import unittest
from raon import ValidationError, validate_context, validate_response, generate

def context():
    return {"scenario_id":"archive-01","stage":"exploration",
            "visible_evidence":[{"id":"EV-01","content":"합성 접근 기록"}],
            "player_claim":None,"backend_feedback":None,"raon_trust":60,
            "hint_directive":{"stance":"optimistic_error","hint_level":"basic",
                              "verification_cue":"EV-01에서 요청 계정과 응답을 비교하세요."}}

def response(c):
    return {"schema_version":"1.0","scenario_id":c["scenario_id"],
            "stance":c["hint_directive"]["stance"],"dialogue":"안전할 거예요. 증거를 확인해 봐요.",
            "evidence_refs":["EV-01"],"verification_cue":c["hint_directive"]["verification_cue"]}

class Contracts(unittest.TestCase):
    def test_context(self):
        self.assertIsNotNone(validate_context(context()))
    def test_hidden_field_rejected(self):
        c=context(); c["flag"]="hidden"
        with self.assertRaises(ValidationError): validate_context(c)
    def test_unknown_claim_evidence(self):
        c=context(); c["player_claim"]={"text":"주장","evidence_ids":["SECRET"]}
        with self.assertRaises(ValidationError): validate_context(c)
    def test_trust_bool_rejected(self):
        c=context(); c["raon_trust"]=True
        with self.assertRaises(ValidationError): validate_context(c)
    def test_ack_requires_backend_support(self):
        c=context(); c["hint_directive"]["stance"]="acknowledge"
        with self.assertRaises(ValidationError): validate_context(c)
    def test_response_rejections(self):
        c=context()
        for key,value in [("scenario_id","other"),("stance","acknowledge"),
                          ("evidence_refs",["SECRET"]),("dialogue","x"*301),
                          ("verification_cue","invented clue")]:
            with self.subTest(key=key):
                r=response(c);r[key]=value
                with self.assertRaises(ValidationError):validate_response(r,c)
    def test_extra_response_field(self):
        c=context();r=response(c);r["score"]=100
        with self.assertRaises(ValidationError): validate_response(r,c)
    def test_json(self):
        c=context()
        for raw in ["not json",'{"schema_version":"1.0","schema_version":"2"}']:
            with self.assertRaises(ValidationError):validate_response(raw,c)
    def test_valid_provider(self):
        c=context();result=generate(c,response)
        self.assertEqual(result["hint"]["source"],"llm")
        self.assertFalse(result["is_fallback"])
    def test_fallback_no_provider(self):
        c=context();before=copy.deepcopy(c);result=generate(c)
        self.assertEqual(result["hint"]["source"],"rule")
        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["response"]["stance"],"evidence_guidance")
        self.assertEqual(c,before)
    def test_timeout_and_invalid_output_fallback(self):
        def timeout(c):raise TimeoutError("private details")
        for provider in [timeout,lambda c:"bad",lambda c:{"flag":"secret"}]:
            r=generate(context(),provider)
            self.assertEqual(r["source"],"rule")
            self.assertNotIn("secret",str(r));self.assertNotIn("private details",str(r))
    def test_invalid_context_not_sent(self):
        c=context();c["raon_trust"]=101
        def never(c):self.fail("Provider must not be called")
        with self.assertRaises(ValidationError):generate(c,never)
    def test_supported_ack(self):
        c=context(); c["stage"]="feedback"
        c["player_claim"]={"text":"증거 반박","evidence_ids":["EV-01"]}
        c["backend_feedback"]={"claim_status":"supported","reason":"증거와 일치"}
        c["hint_directive"]["stance"]="acknowledge"
        r=generate(c)
        self.assertEqual(r["response"]["stance"],"acknowledge")
        self.assertNotIn("score",r)
    def test_empty_evidence_guidance(self):
        c=context();c["visible_evidence"]=[];c["hint_directive"]["stance"]="evidence_guidance"
        self.assertEqual(generate(c)["response"]["evidence_refs"],[])
if __name__=="__main__":unittest.main()

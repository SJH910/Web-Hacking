import assert from "node:assert/strict";
import test from "node:test";
import { judgeEvidence, scenarios } from "../app/scenarios.ts";

for (const scenario of scenarios) {
  test(`${scenario.title}: 필요한 증거를 모두 선택했을 때만 완료`, () => {
    assert.equal(judgeEvidence(scenario, scenario.requiredIds), true);
    assert.equal(judgeEvidence(scenario, [...scenario.requiredIds].reverse()), true);
    assert.equal(judgeEvidence(scenario, []), false);
    assert.equal(judgeEvidence(scenario, [scenario.requiredIds[0]]), false);
    assert.equal(judgeEvidence(scenario, scenario.evidence.map((item) => item.id)), false);
    assert.equal(judgeEvidence(scenario, ["unknown", scenario.requiredIds[0]]), false);
    assert.equal(judgeEvidence(scenario, [scenario.requiredIds[0], scenario.requiredIds[0]]), false);
  });
  test(`${scenario.title}: 정답과 로그는 제공된 시나리오 안에 존재`, () => {
    assert.equal(new Set(scenario.evidence.map((item) => item.id)).size, scenario.evidence.length);
    assert.equal(scenario.requiredIds.length, 2);
    assert(scenario.requiredIds.every((id) => scenario.evidence.some((item) => item.id === id)));
    assert(scenario.observation.length > 0);
    assert(scenario.simulation.length > 0);
  });
}

test("다른 시나리오의 증거로 완료할 수 없음", () => {
  assert.equal(judgeEvidence(scenarios[0], scenarios[1].requiredIds), false);
});

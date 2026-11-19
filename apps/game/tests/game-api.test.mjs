import assert from 'node:assert/strict';
import test from 'node:test';
import { isGame, isRanks, readSave, gameRequest } from '../app/play/game-api.ts';
const state = {
 runId:'run_1', revision:0, seed:'seed', floor:1, score:0, trust:60, progress:0, cleared:false,
 canJudge:false,totalWrong:0,totalHints:0,problem:{id:'night-log',title:'야간 접속 기록',type:'terminal',difficulty:'쉬움',objective:'기록 조사',allyOpening:'정상 같아'},evidence:[],step:null,hints:[]
};
test('서버 상태만 허용하고 범위가 잘못된 응답 거부',()=>{
 assert(isGame(state));
 for (const patch of [{floor:0},{floor:11},{trust:101},{score:-1},{progress:4},{problem:{}},{hints:[{}]},{evidence:[null]},{step:undefined},{ending:{}}]) assert.equal(isGame({...state,...patch}),false);
});
test('세 판정 단계 및 선택형 문제 지원',()=>{
 for (const key of ['classify','verdict','action']) assert(isGame({...state,problem:{...state.problem,type:'choice'},step:{key,question:'질문',choices:[{id:'c1',label:'보기'}]}}));
});
test('손상된 저장 데이터 및 구버전 거부',()=>{
 for(const raw of [null,'{','null','{}','{"version":2,"runId":"r"}','{"version":1,"runId":"../x"}']) assert.equal(readSave(raw),null);
 assert.equal(readSave(JSON.stringify({version:1,runId:'run_1',score:99999})),'run_1');
});
test('랭킹의 빈 결과 및 잘못된 행 구분',()=>{
 assert(isRanks([])); assert(isRanks([{rank:1,name:'탐험가',floor:10,score:300,trust:80,hints:1}])); assert.equal(isRanks([{}]),false);
});
test('명령은 API로 전달하고 서버 응답을 사용',async(t)=>{
 t.mock.method(globalThis,'fetch',async(url,options)=>{
 assert.equal(url,'/api/game/runs/run_1/commands');
 assert.equal(options.method,'POST'); assert.equal(JSON.parse(options.body).command,'help');
 return Response.json({state,output:'허용 명령'});
 });
 assert.equal((await gameRequest('runs/run_1/commands',{command:'help'})).output,'허용 명령');
});
test('404는 연결 안내, 잘못된 JSON 상태는 오류로 처리',async(t)=>{
 const fetch=t.mock.method(globalThis,'fetch',async()=>new Response('',{status:404}));
 await assert.rejects(gameRequest('runs',{}),/아직 연결/);
 fetch.mock.mockImplementation(async()=>Response.json({state:{...state,trust:-1}}));
 await assert.rejects(gameRequest('runs',{}),/응답 형식/);
});
test('타임아웃과 통신 실패를 성공으로 처리하지 않음',async(t)=>{
 t.mock.method(globalThis,'fetch',async()=>{throw new Error('network failure');});
 await assert.rejects(gameRequest('runs',{}),/network failure/);
});

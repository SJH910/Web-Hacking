import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup:render}=require('react-dom/server');
const source=fs.readFileSync(new URL('../app/play/play-panels.tsx',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText;
const exports={};
vm.runInNewContext(code,{exports,require:(id)=>id.endsWith('.css')?{default:{}}:require(id)});
const game={runId:'run',floor:1,progress:0,canJudge:false,cleared:false,trust:60,problem:{type:'terminal',objective:'로그 조사',allyOpening:'동료 의견'},evidence:[],hints:[],step:{key:'classify',question:'무엇인가?',choices:[{id:'a',label:'선택지'}]}};
const act=async()=>{};
test('탐색 전 판정 잠금과 터미널 입력 표시',()=>{
 const html=render(React.createElement(exports.Judgment,{game,busy:false,act}));
 assert.match(html,/fieldset disabled/); assert.match(html,/먼저 기록/);
 const terminal=render(React.createElement(exports.Investigation,{game,busy:false,output:[],act}));
 assert.match(terminal,/명령 입력/); assert.match(terminal,/아직 실행한 명령/);
});
test('선택형 증거와 통과 상태에서 다음 층 버튼 표시',()=>{
 const choice=render(React.createElement(exports.Investigation,{game:{...game,problem:{...game.problem,type:'choice'},evidence:[{number:'E1',title:'기록',detail:'상세',tag:'로그'}]},busy:false,output:[],act}));
 assert.match(choice,/checkbox/); assert.doesNotMatch(choice,/명령 입력/);
 const clear=render(React.createElement(exports.Judgment,{game:{...game,cleared:true,flag:'FLAG{test}'},busy:false,act}));
 assert.match(clear,/다음 층으로/); assert.match(clear,/FLAG\{test\}/); assert.doesNotMatch(clear,/판정 제출/);
 const last=render(React.createElement(exports.Judgment,{game:{...game,cleared:true,floor:10},busy:false,act}));
 assert.doesNotMatch(last,/다음 층으로/);
});
test('규칙 기반 힌트 표기와 빈 랭킹 안내',()=>{
 const hint=render(React.createElement(exports.Companion,{game:{...game,hints:[{level:1,text:'기록 비교',source:'rule'}]},busy:false,act}));
 assert.match(hint,/규칙 기반 안내/);
 assert.match(render(React.createElement(exports.Rankings,{ranks:[]})),/아직 등록된/);
});

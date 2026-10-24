'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const script=fs.readFileSync(path.join(__dirname,'..','js','config.js'),'utf8');
function configuration(hostname,pathname,initial){
  const store={getItem:() => null};
  const context={window:{location:{hostname,pathname,origin:'https://eventora.example'},API_BASE_URL:initial},localStorage:store,sessionStorage:store};
  vm.runInNewContext(script,context);return context.window.Eventora;
}
assert.equal(configuration('localhost','/pages/events.html').api,'http://127.0.0.1:8000/api');
assert.equal(configuration('localhost','/admin/pages/admin_event.html').loginUrl,'../../pages/login.html');
assert.equal(configuration('localhost','/admin/admin.html').loginUrl,'../pages/login.html');
assert.equal(configuration('example.com','/pages/events.html','https://api.example.com/').api,'https://api.example.com/api');
assert.equal(configuration('example.com','/pages/events.html').api,'https://eventora.example/api');
console.log('PASS: shared local and hosted API config, safe admin login paths');
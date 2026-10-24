'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function node(){const classes=new Set(['d-none']);const events={};return {className:'',value:'',disabled:false,textContent:'',type:'password',dataset:{},children:[],classList:{add(x){classes.add(x)},remove(x){classes.delete(x)},toggle(x,enabled){enabled?classes.add(x):classes.delete(x)},contains(x){return classes.has(x)}},setAttribute(){},addEventListener(x,fn){events[x]=fn},append(...children){this.children.push(...children)},appendChild(child){this.children.push(child)},replaceChildren(){this.children=[]},reset(){this.resetCalled=true},get onSubmit(){return events.submit},get click(){return events.click},querySelector(){return {className:''}}};}
(async()=>{
  const ids=new Map(),get=id=>{if(!ids.has(id)) ids.set(id,node());return ids.get(id)};
  let posted=[];const storage=new Map();
  const window={Eventora:{api:'http://127.0.0.1:8000/api',error:d=>d.detail||'Request failed'}};
  const location={search:'?next=event-details.html%3Fid%3D7',href:''};
  const document={getElementById:get,querySelectorAll:()=>[],createElement:()=>Object.assign(node(),{href:''})};
  const fetch=async(url,opts)=>{
    if(!opts) return {ok:true,json:async()=>[{id:7,title:'Demo Concert',location:'Hall',price:350}]};
    posted.push({url,body:JSON.parse(opts.body)});
    if(url.endsWith('/auth/register'))return {ok:true,json:async()=>({username:'alice'})};
    if(url.endsWith('/auth/login'))return {ok:true,json:async()=>({access_token:'sample-jwt'})};
  };
  const ctx={window,document,location,fetch,URLSearchParams,console,Number,localStorage:{setItem(k,v){storage.set(k,v)}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','js','login.js'),'utf8'),ctx);
  assert.equal(get('liveEvents').children.length,0);
  get('regUsername').value='alice';get('regEmail').value='alice@example.com';get('regPassword').value='a-safe-passphrase';
  await get('registerForm').onSubmit({preventDefault(){}});
  assert.equal(posted[0].url,'http://127.0.0.1:8000/api/auth/register');
  assert.equal(posted[0].body.role,'user');assert.equal(get('loginIdentifier').value,'alice');
  assert.equal(get('authMessage').textContent,'Your account was created. Sign in to continue.');
  get('loginPassword').value='a-safe-passphrase';
  await get('loginForm').onSubmit({preventDefault(){}});
  assert.equal(posted[1].body.username,'alice');assert.equal(storage.get('token'),'sample-jwt');
  assert.equal(location.href,'event-details.html?id=7');
  await new Promise(setImmediate);
  assert.equal(get('liveEvents').children.length,1);
  console.log('PASS: create-account -> sign-in -> resume selected event, public event preview');
})().catch(e=>{console.error(e);process.exitCode=1});

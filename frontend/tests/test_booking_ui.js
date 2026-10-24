/* Zero-dependency UI state and request-contract checks. Run: node frontend/tests/test_booking_ui.js
   This does not replace live browser tests; it tests booking JS against a tiny mocked DOM.
*/
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'js', 'event-details.js'), 'utf8');
const nodes = new Map();
const makeNode = () => ({
  textContent: '', innerHTML: '', value: '1', max: '', style: {}, dataset: {}, disabled: false,
  classList: { add() {}, remove() {}, toggle() {} },
  addEventListener() {}, appendChild(child) { this.children.push(child); },
  querySelector(selector) { const id = (selector.match(/data-ticket-type-id="([^"]*)"/) || [])[1]; return this.children.find(n => String(n.dataset.ticketTypeId) === id) || null; },
  children: []
});
const doc = {
  addEventListener() {},
  createElement() { return makeNode(); },
  querySelectorAll(sel) { return sel === '#generalTicketList .zone-option' ? doc.getElementById('generalTicketList').children : []; },
  getElementById(id) { if (!nodes.has(id)) nodes.set(id, makeNode()); return nodes.get(id); }
};
const storage = () => {
  const map = new Map();
  return { getItem: key => map.get(key) ?? null, setItem: (k,v) => map.set(k,String(v)), removeItem: k => map.delete(k) };
};
const ctx = vm.createContext({
  document: doc, window: { location: { hostname:'localhost', search:'?id=11' } },
  location: { href:'' }, sessionStorage: storage(), localStorage: storage(),
  URLSearchParams, crypto: { randomUUID: () => 'demo-test-request-id' },
  console, Number, String, Date, Math, JSON,
});
vm.runInContext(source, ctx, { filename:'event-details.js' });
vm.runInContext(`currentEvent={inventory_type:'general',price:0};
  renderGeneralInventory({ticket_types:[{id:8,name:'All Day',price:420,available:null}]});`, ctx);
assert.equal(doc.getElementById('availabilityStatus').textContent, 'Available', 'Unlimited admission must not look sold out');
assert.equal(doc.getElementById('seats').textContent, 'Available');
assert.equal(doc.getElementById('quantity').max, 10);
vm.runInContext('changeQuantity(1000)', ctx);
assert.equal(doc.getElementById('quantity').value, 10, 'Quantity capped at backend maximum of 10');
const payload = vm.runInContext('buildBookingPayload()', ctx);
assert.deepEqual(JSON.parse(JSON.stringify(payload)), {event_id:11,tickets:10,idempotency_key:'demo-test-request-id',ticket_type_id:8});
vm.runInContext(`currentEvent={inventory_type:'seat',price:0};
 selectedTicketType=null;selectedSeats=[{id:2,seat_code:'VIP-A-1',price:800},{id:4,seat_code:'VIP-A-3',price:850}];quantity=2;`, ctx);
const seats = vm.runInContext('buildBookingPayload()',ctx);
assert.deepEqual(Array.from(seats.seat_ids),[2,4]);
assert.equal(seats.tickets,2);
console.log('PASS: unlimited admission, quantity cap, general booking payload and exact seat payload');

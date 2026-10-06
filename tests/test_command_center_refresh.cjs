const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const assert = require('node:assert/strict');
const { test } = require('node:test');

// Execute the actual refresh callback with controlled endpoint failures.
const source = readFileSync(join(__dirname, '../frontend/src/views/SupervisorCommandCenterView.tsx'), 'utf8');
const body = source.split('const loadData = useCallback(async () => {')[1].split('\n  }, []);')[0];
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const refresh = new AsyncFunction('fetchTickets', 'fetchApprovals', 'fetchAuditLogs', 'fetchPiiFeed',
  'setTickets', 'setApprovals', 'setAuditLogs', 'setPiiFeed', 'console', body);

test('audit feed errors do not hide pending approvals or tickets', async () => {
  const values = {};
  await refresh(async () => [{ thread_id: 'thread_1', status: 'pending_approval' }],
    async () => [{ thread_id: 'thread_1', status: 'pending' }],
    async () => { throw new Error('Audit unavailable'); },
    async () => { throw new Error('PII feed unavailable'); },
    data => { values.tickets = data; }, data => { values.approvals = data; },
    data => { values.audit = data; }, data => { values.pii = data; }, { error() {} });
  assert.equal(values.approvals[0].status, 'pending');
  assert.equal(values.tickets[0].status, 'pending_approval');
  assert.equal(values.audit, undefined);
  assert.equal(values.pii, undefined);
});

test('a failed approval refresh preserves the queue and updates other feeds', async () => {
  const values = { approvals: [{ thread_id: 'existing', status: 'pending' }] };
  await refresh(async () => [{ thread_id: 'new_ticket' }],
    async () => { throw new Error('Approvals unavailable'); },
    async () => ['audit'], async () => ['pii'],
    data => { values.tickets = data; }, data => { values.approvals = data; },
    data => { values.audit = data; }, data => { values.pii = data; }, { error() {} });
  assert.equal(values.approvals[0].thread_id, 'existing');
  assert.equal(values.tickets[0].thread_id, 'new_ticket');
  assert.deepEqual(values.audit, ['audit']);
});

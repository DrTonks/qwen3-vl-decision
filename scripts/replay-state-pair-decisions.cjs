// Offline contract replay only: no routes, database, model, or credentials.
const fs = require('node:fs');
const path = require('node:path');
const [backend, fixturesPath, targetPath] = process.argv.slice(2);
if (!backend || !fixturesPath || !targetPath) throw new Error('Expected backend fixtures targets');
const contract = require(path.resolve(backend, 'services/customerSupport/financialContract.js'));
const fixtures = JSON.parse(fs.readFileSync(fixturesPath, 'utf8'));
const targets = JSON.parse(fs.readFileSync(targetPath, 'utf8'));
if (fixtures.length !== targets.length) throw new Error('Row count mismatch');
const output = fixtures.map((row, i) => {
  const target = targets[i];
  if (row.id !== target.id) throw new Error('Row identity mismatch');
  const c = row.context;
  const ctx = {...c, tools: c.availableTools.map(name => ({name}))};
  // Deliberately request the query on negative variants to inspect guards.
  // Guard behavior is not an oracle for the upstream semantic action label.
  const forcedQuery = contract.toDecision('tool', row.target_tool, ctx);
  contract.validateDecision(forcedQuery);
  const decision = contract.toDecision(target.annotation.action, target.annotation.tool_name, ctx);
  contract.validateDecision(decision);
  const expected = target.annotation;
  if (decision.action !== expected.action || (decision.tool || null) !== expected.tool_name
      || JSON.stringify(decision.arguments || {}) !== JSON.stringify(expected.tool_arguments)) {
    throw new Error('Expected label does not survive adapter: ' + row.id);
  }
  const guardAction = {ready:'tool', unauthenticated:'clarify', unavailable:'human', missing:'clarify'}[row.variant];
  if (forcedQuery.action !== guardAction) throw new Error('Unexpected query guard: ' + row.id);
  return {id: row.id, decision, forced_query_decision: forcedQuery,
    semantic_and_guard_action_equal: decision.action === forcedQuery.action,
    note: 'Guard replay is structural evidence, not independent semantic labeling or database ownership verification.'};
});
process.stdout.write(JSON.stringify(output));

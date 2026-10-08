// Read-only inspection of the actual Node input adapter; no DB/model/server.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const backend = path.resolve(process.argv[2] || path.join(root, '../uestc_Integrated_Design/后端'));
const contract = require(path.join(backend, 'services/customerSupport/financialContract.js'));
const rows = JSON.parse(fs.readFileSync(path.join(root, 'data/financial-service-v2/development.json'), 'utf8'));
const output = rows.filter(r => r.cohort === 'current-service').map(r => {
  const v = r.input;
  // Reconstruct only the visible conversational fields; this is not a real session.
  const state = { pending: v.state.pending || null, selectedApplicationId: v.state.application_id || null };
  const context = {message:v.message, history:v.history, authenticated:v.state.authenticated,
    state, tools:v.available_tools.map(name => ({name}))};
  const actual = contract.modelInput(context);
  return {id:r.id, original_state:v.state, reconstructed_node_state:actual.state,
    original_action:r.annotation.action, original_tool:r.annotation.tool_name,
    grounded_gold_decision:contract.toDecision(r.annotation.action,r.annotation.tool_name,context)};
});
process.stdout.write(JSON.stringify({scope:'Current-service development only; reconstructed context, not actual session or model inference',rows:output}));

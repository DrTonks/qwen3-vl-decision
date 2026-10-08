// Training-only CPU replay of actual Node parameter/input helpers. No DB/server/model.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const backend = path.resolve(process.argv[2] || path.join(root, '../uestc_Integrated_Design/后端'));
const contract = require(path.join(backend, 'services/customerSupport/financialContract.js'));
const rows = JSON.parse(fs.readFileSync(path.join(root, 'data/financial-sampling-study-v1/pool-v1/train.json'), 'utf8'));
if (rows.some(r => r.split !== 'train' || r.training_eligible !== false)) throw new Error('Training-only audit role mismatch');
const output = rows.map(r => {
  const v = r.input;
  // Reconstructed visible state is not the original server session.
  const context = { message: v.message, history: v.history, authenticated: v.state.authenticated,
    state: { pending: v.state.pending || null, selectedApplicationId: v.state.application_id || null },
    tools: v.available_tools.map(name => ({name})) };
  const actual = contract.modelInput(context);
  return { id: r.id, parsed_state: actual.state,
    grounded_gold: contract.toDecision(r.annotation.action, r.annotation.tool_name, context) };
});
process.stdout.write(JSON.stringify({adapter_version: contract.INPUT_ADAPTER_VERSION,
  scope: 'Training-only reconstructed parameter replay; capability deployment, database, actual session and model predictions not tested', rows:output}));

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../hooks/useApi';
import { showToast } from '../common/Toast';

interface AlertRule {
  id: number;
  name: string;
  description: string | null;
  metric: string;
  operator: string;
  threshold: number;
  window_days: number;
  severity: string;
  enabled: boolean;
}

const METRICS = ['risk_score', 'cases', 'rainfall_mm', 'flood_extent_pct', 'ndwi'];
const OPERATORS = ['>', '>=', '<', '<=', '=='];
const SEVERITIES = ['info', 'warning', 'critical'];

const RULES_QUERY_KEY = ['alertRules'] as const;

const inputClass =
  'w-full px-3 py-2 text-sm border border-[#e6e8eb] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary';
const labelClass = 'block text-xs font-medium text-[#637588] mb-1';

export default function AlertRulesPanel() {
  const queryClient = useQueryClient();
  const { data: rules, isLoading, error } = useQuery<AlertRule[]>({
    queryKey: RULES_QUERY_KEY,
    queryFn: apiService.getAlertRules,
    staleTime: 60 * 1000,
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Partial<AlertRule>>({});

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    metric: METRICS[0],
    operator: OPERATORS[0],
    threshold: 0,
    window_days: 7,
    severity: SEVERITIES[1],
    enabled: true,
  });

  const invalidateRules = () => {
    queryClient.invalidateQueries({ queryKey: RULES_QUERY_KEY });
  };

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      apiService.updateAlertRule(id, body),
    onSuccess: () => {
      invalidateRules();
      showToast.success('Alert rule updated');
      setEditingId(null);
      setDraft({});
    },
    onError: () => showToast.error('Failed to update alert rule'),
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => apiService.createAlertRule(body),
    onSuccess: () => {
      invalidateRules();
      showToast.success('Alert rule created');
      setShowCreate(false);
      setCreateForm({
        name: '',
        description: '',
        metric: METRICS[0],
        operator: OPERATORS[0],
        threshold: 0,
        window_days: 7,
        severity: SEVERITIES[1],
        enabled: true,
      });
    },
    onError: () => showToast.error('Failed to create alert rule'),
  });

  const toggleEnabled = (rule: AlertRule) => {
    updateMutation.mutate({ id: rule.id, body: { enabled: !rule.enabled } });
  };

  const startEdit = (rule: AlertRule) => {
    setEditingId(rule.id);
    setDraft({ ...rule });
  };

  const saveEdit = (id: number) => {
    const { id: _id, ...rest } = draft;
    void _id;
    updateMutation.mutate({ id, body: rest });
  };

  const handleCreate = () => {
    if (!createForm.name.trim()) {
      showToast.error('Rule name is required');
      return;
    }
    createMutation.mutate({ ...createForm });
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-[#f0f2f5] rounded w-1/4"></div>
          <div className="h-16 bg-[#f0f2f5] rounded-xl"></div>
          <div className="h-16 bg-[#f0f2f5] rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-[#e6e8eb] p-6 text-center">
        <span
          className="material-symbols-outlined text-red-400 mb-2"
          style={{ fontSize: '36px' }}
        >
          error
        </span>
        <p className="text-sm font-medium text-red-600">Failed to load alert rules</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[#e6e8eb] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#f0f2f5] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#637588]" style={{ fontSize: '20px' }}>
              rule
            </span>
          </div>
          <div>
            <h3 className="font-bold text-[#111518]">Alert Rules</h3>
            <p className="text-sm text-[#637588]">Configure thresholds that generate alerts</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="flex items-center gap-2 px-3 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
            {showCreate ? 'close' : 'add'}
          </span>
          {showCreate ? 'Cancel' : 'New Rule'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="mb-6 border border-[#e6e8eb] rounded-xl p-4 bg-[#f6f7f8]">
          <h4 className="text-sm font-semibold text-[#111518] mb-3">Create Alert Rule</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className={labelClass}>Name</label>
              <input
                className={inputClass}
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                placeholder="e.g. High case spike"
              />
            </div>
            <div>
              <label className={labelClass}>Severity</label>
              <select
                className={inputClass}
                value={createForm.severity}
                onChange={(e) => setCreateForm({ ...createForm, severity: e.target.value })}
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-3">
              <label className={labelClass}>Description</label>
              <input
                className={inputClass}
                value={createForm.description}
                onChange={(e) =>
                  setCreateForm({ ...createForm, description: e.target.value })
                }
                placeholder="Optional description"
              />
            </div>
            <div>
              <label className={labelClass}>Metric</label>
              <select
                className={inputClass}
                value={createForm.metric}
                onChange={(e) => setCreateForm({ ...createForm, metric: e.target.value })}
              >
                {METRICS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Operator</label>
              <select
                className={inputClass}
                value={createForm.operator}
                onChange={(e) =>
                  setCreateForm({ ...createForm, operator: e.target.value })
                }
              >
                {OPERATORS.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Threshold</label>
              <input
                type="number"
                step="any"
                className={inputClass}
                value={createForm.threshold}
                onChange={(e) =>
                  setCreateForm({ ...createForm, threshold: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <label className={labelClass}>Window (days)</label>
              <input
                type="number"
                min={1}
                className={inputClass}
                value={createForm.window_days}
                onChange={(e) =>
                  setCreateForm({ ...createForm, window_days: Number(e.target.value) })
                }
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm text-[#111518]">
                <input
                  type="checkbox"
                  checked={createForm.enabled}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, enabled: e.target.checked })
                  }
                  className="rounded"
                />
                Enabled
              </label>
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Rule'}
            </button>
          </div>
        </div>
      )}

      {/* Rules table */}
      {!rules || rules.length === 0 ? (
        <div className="text-center py-10">
          <span
            className="material-symbols-outlined text-[#637588] mb-2"
            style={{ fontSize: '40px' }}
          >
            inbox
          </span>
          <p className="text-sm font-medium text-[#111518]">No alert rules configured</p>
          <p className="text-xs text-[#637588] mt-1">
            Create a rule to define when alerts are triggered
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-[#637588] border-b border-[#e6e8eb]">
                <th className="py-2 pr-3 font-medium">Name</th>
                <th className="py-2 px-3 font-medium">Metric</th>
                <th className="py-2 px-3 font-medium">Op</th>
                <th className="py-2 px-3 font-medium">Threshold</th>
                <th className="py-2 px-3 font-medium">Window</th>
                <th className="py-2 px-3 font-medium">Severity</th>
                <th className="py-2 px-3 font-medium">Enabled</th>
                <th className="py-2 pl-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => {
                const isEditing = editingId === rule.id;
                const d = isEditing ? (draft as AlertRule) : rule;
                return (
                  <tr key={rule.id} className="border-b border-[#e6e8eb] last:border-0">
                    <td className="py-3 pr-3 align-top">
                      {isEditing ? (
                        <input
                          className={inputClass}
                          value={d.name}
                          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                        />
                      ) : (
                        <div>
                          <p className="font-medium text-[#111518]">{rule.name}</p>
                          {rule.description && (
                            <p className="text-xs text-[#637588] mt-0.5">{rule.description}</p>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-3 align-top">
                      {isEditing ? (
                        <select
                          className={inputClass}
                          value={d.metric}
                          onChange={(e) => setDraft({ ...draft, metric: e.target.value })}
                        >
                          {METRICS.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="font-mono text-xs text-[#111518]">{rule.metric}</span>
                      )}
                    </td>
                    <td className="py-3 px-3 align-top">
                      {isEditing ? (
                        <select
                          className={inputClass}
                          value={d.operator}
                          onChange={(e) => setDraft({ ...draft, operator: e.target.value })}
                        >
                          {OPERATORS.map((o) => (
                            <option key={o} value={o}>
                              {o}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="font-mono text-xs text-[#111518]">{rule.operator}</span>
                      )}
                    </td>
                    <td className="py-3 px-3 align-top">
                      {isEditing ? (
                        <input
                          type="number"
                          step="any"
                          className={inputClass}
                          value={d.threshold}
                          onChange={(e) =>
                            setDraft({ ...draft, threshold: Number(e.target.value) })
                          }
                        />
                      ) : (
                        <span className="font-mono text-xs text-[#111518]">{rule.threshold}</span>
                      )}
                    </td>
                    <td className="py-3 px-3 align-top">
                      {isEditing ? (
                        <input
                          type="number"
                          min={1}
                          className={inputClass}
                          value={d.window_days}
                          onChange={(e) =>
                            setDraft({ ...draft, window_days: Number(e.target.value) })
                          }
                        />
                      ) : (
                        <span className="font-mono text-xs text-[#111518]">{rule.window_days}d</span>
                      )}
                    </td>
                    <td className="py-3 px-3 align-top">
                      {isEditing ? (
                        <select
                          className={inputClass}
                          value={d.severity}
                          onChange={(e) => setDraft({ ...draft, severity: e.target.value })}
                        >
                          {SEVERITIES.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            rule.severity === 'critical'
                              ? 'bg-red-100 text-red-800'
                              : rule.severity === 'warning'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {rule.severity}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 align-top">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isEditing ? d.enabled : rule.enabled}
                          onChange={(e) =>
                            isEditing
                              ? setDraft({ ...draft, enabled: e.target.checked })
                              : toggleEnabled(rule)
                          }
                          className="rounded"
                        />
                      </label>
                    </td>
                    <td className="py-3 pl-3 align-top text-right">
                      {isEditing ? (
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => saveEdit(rule.id)}
                            disabled={updateMutation.isPending}
                            className="px-2.5 py-1.5 bg-primary text-white rounded-lg text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => {
                              setEditingId(null);
                              setDraft({});
                            }}
                            className="px-2.5 py-1.5 bg-[#f0f2f5] text-[#637588] rounded-lg text-xs font-medium hover:bg-[#e6e8eb] transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(rule)}
                          className="px-2.5 py-1.5 bg-[#f0f2f5] text-[#637588] rounded-lg text-xs font-medium hover:bg-[#e6e8eb] transition-colors inline-flex items-center gap-1"
                        >
                          <span
                            className="material-symbols-outlined"
                            style={{ fontSize: '14px' }}
                          >
                            edit
                          </span>
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

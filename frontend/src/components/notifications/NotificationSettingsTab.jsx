import React, { useState, useEffect } from 'react';
import { useProject } from '@/context/ProjectContext';
import { notificationsApi } from '@/api/notifications';
import { Modal } from '@/components/common/Modal';
import {
  Bell,
  Plus,
  Send,
  Trash2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ExternalLink,
  MessageSquare,
  Mail,
  Globe,
  ShieldAlert,
  Power,
  Info
} from 'lucide-react';
import { clsx } from 'clsx';

export const NotificationSettingsTab = () => {
  const { activeProject } = useProject();

  const [configs, setConfigs] = useState([]);
  const [history, setHistory] = useState([]);
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [channelType, setChannelType] = useState('slack');
  const [targetUrl, setTargetUrl] = useState('');
  const [targetEmail, setTargetEmail] = useState('');
  const [severityFilter, setSeverityFilter] = useState('P2');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Channel Action States
  const [testingId, setTestingId] = useState(null);
  const [testFeedback, setTestFeedback] = useState(null); // { configId, success, message }
  const [deletingId, setDeletingId] = useState(null);

  const loadConfigs = async () => {
    if (!activeProject?.id) return;
    setIsLoadingConfigs(true);
    try {
      const data = await notificationsApi.listConfigs(activeProject.id);
      setConfigs(data || []);
    } catch (err) {
      console.error('Failed to load notification configs:', err);
    } finally {
      setIsLoadingConfigs(false);
    }
  };

  const loadHistory = async () => {
    if (!activeProject?.id) return;
    setIsLoadingHistory(true);
    try {
      const data = await notificationsApi.getHistory(activeProject.id, 25);
      setHistory(data || []);
    } catch (err) {
      console.error('Failed to load notification history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeProject?.id) {
      loadConfigs();
      loadHistory();
      setTestFeedback(null);
    }
  }, [activeProject?.id]);

  const handleCreateChannel = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!activeProject?.id) {
      setFormError('No active project selected.');
      return;
    }

    if (channelType === 'email') {
      if (!targetEmail.trim()) {
        setFormError('Please provide a valid recipient email address.');
        return;
      }
    } else {
      if (!targetUrl.trim() || !targetUrl.startsWith('http')) {
        setFormError('Please provide a valid webhook URL starting with http:// or https://');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const payload = {
        channel_type: channelType,
        target_url: channelType !== 'email' ? targetUrl.trim() : undefined,
        settings_json: {
          severity_filter: severityFilter,
          ...(channelType === 'email' ? { email: targetEmail.trim() } : {}),
        },
        is_enabled: true,
      };

      await notificationsApi.createConfig(activeProject.id, payload);
      setIsAddModalOpen(false);
      setTargetUrl('');
      setTargetEmail('');
      setSeverityFilter('P2');
      await loadConfigs();
    } catch (err) {
      setFormError(err.message || 'Failed to create notification channel.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleChannel = async (config) => {
    if (!activeProject?.id) return;
    try {
      await notificationsApi.updateConfig(activeProject.id, config.id, {
        is_enabled: !config.is_enabled,
      });
      setConfigs((prev) =>
        prev.map((c) => (c.id === config.id ? { ...c, is_enabled: !c.is_enabled } : c))
      );
    } catch (err) {
      console.error('Failed to toggle channel status:', err);
    }
  };

  const handleDeleteChannel = async (configId) => {
    if (!activeProject?.id) return;
    if (!window.confirm('Are you sure you want to delete this notification channel?')) return;

    setDeletingId(configId);
    try {
      await notificationsApi.deleteConfig(activeProject.id, configId);
      setConfigs((prev) => prev.filter((c) => c.id !== configId));
    } catch (err) {
      console.error('Failed to delete channel:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleTestChannel = async (configId) => {
    if (!activeProject?.id) return;
    setTestingId(configId);
    setTestFeedback(null);

    try {
      const result = await notificationsApi.testConfig(activeProject.id, configId);
      setTestFeedback({
        configId,
        success: result.success,
        message: result.message,
      });
      // Refresh delivery history to reflect the test dispatch
      loadHistory();
    } catch (err) {
      setTestFeedback({
        configId,
        success: false,
        message: err.message || 'Verification test failed to send.',
      });
    } finally {
      setTestingId(null);
    }
  };

  const getChannelIcon = (type) => {
    switch ((type || '').toLowerCase()) {
      case 'slack':
        return <MessageSquare className="w-5 h-5 text-[#4A154B]" />;
      case 'discord':
        return <MessageSquare className="w-5 h-5 text-[#5865F2]" />;
      case 'email':
        return <Mail className="w-5 h-5 text-blue-500" />;
      default:
        return <Globe className="w-5 h-5 text-emerald-500" />;
    }
  };

  const getChannelTitle = (type) => {
    switch ((type || '').toLowerCase()) {
      case 'slack':
        return 'Slack Webhook';
      case 'discord':
        return 'Discord Webhook';
      case 'email':
        return 'Email Alert Notification';
      default:
        return 'Custom HTTP Webhook';
    }
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
        <ShieldAlert className="w-8 h-8 text-amber-500 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">No Active Project Selected</h3>
        <p className="text-xs text-slate-400 mt-1">
          Select or create a project to configure alert channels and view dispatch histories.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header & Add Channel Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Notification & Alert Channels
            </h2>
            <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-500 border border-brand-500/20">
              {activeProject.name}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Dispatch instant incident alerts and AI Root Cause Analysis reports to Slack, Discord, webhooks, or email.
          </p>
        </div>

        <button
          onClick={() => {
            setFormError('');
            setIsAddModalOpen(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold shadow-sm transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Alert Channel</span>
        </button>
      </div>

      {/* Channel Cards Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Configured Channels ({configs.length})
          </h3>
          <button
            onClick={loadConfigs}
            disabled={isLoadingConfigs}
            className="text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', isLoadingConfigs && 'animate-spin')} />
            <span>Refresh</span>
          </button>
        </div>

        {isLoadingConfigs ? (
          <div className="p-12 text-center text-xs text-slate-400 flex flex-col items-center gap-2 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
            <RefreshCw className="w-6 h-6 animate-spin text-brand-500" />
            <span>Loading configured alert channels...</span>
          </div>
        ) : configs.length === 0 ? (
          <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-brand-500/10 text-brand-500 flex items-center justify-center mx-auto">
              <Bell className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                No notification channels configured yet
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                Connect your team's Slack, Discord, or webhooks to receive real-time incident warnings and AI findings.
              </p>
            </div>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Configure your first channel</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {configs.map((config) => {
              const feedback = testFeedback?.configId === config.id ? testFeedback : null;
              const isTesting = testingId === config.id;
              const isDeleting = deletingId === config.id;

              return (
                <div
                  key={config.id}
                  className={clsx(
                    'p-5 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm transition-all flex flex-col justify-between space-y-4',
                    config.is_enabled
                      ? 'border-slate-200 dark:border-slate-800'
                      : 'border-slate-200/50 dark:border-slate-800/40 opacity-70'
                  )}
                >
                  <div className="space-y-3">
                    {/* Card Top: Icon, Title, Status Toggle */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                          {getChannelIcon(config.channel_type)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                              {getChannelTitle(config.channel_type)}
                            </h4>
                            <span
                              className={clsx(
                                'text-[9px] font-bold uppercase font-mono px-1.5 py-0.5 rounded',
                                config.is_enabled
                                  ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                  : 'bg-slate-200 dark:bg-slate-800 text-slate-500'
                              )}
                            >
                              {config.is_enabled ? 'Active' : 'Disabled'}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 font-mono truncate max-w-xs mt-0.5">
                            {config.channel_type === 'email'
                              ? config.settings_json?.email || 'Default Admin Email'
                              : config.target_url || 'Webhook URL'}
                          </p>
                        </div>
                      </div>

                      {/* Enable / Disable Switch */}
                      <button
                        onClick={() => handleToggleChannel(config)}
                        className={clsx(
                          'p-1.5 rounded-xl border transition-colors',
                          config.is_enabled
                            ? 'text-emerald-500 border-emerald-500/20 hover:bg-emerald-50 dark:hover:bg-emerald-950/30'
                            : 'text-slate-400 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                        )}
                        title={config.is_enabled ? 'Disable Channel' : 'Enable Channel'}
                      >
                        <Power className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Metadata Badges */}
                    <div className="flex items-center gap-2 pt-1">
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        Min Severity: <span className="font-bold text-brand-500">{config.settings_json?.severity_filter || 'P2'}</span>
                      </span>
                      <span className="text-[10px] text-slate-400">
                        Added {new Date(config.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {/* Test Dispatch Feedback Banner */}
                    {feedback && (
                      <div
                        className={clsx(
                          'p-2.5 rounded-xl text-xs flex items-start gap-2 border animate-fade-in',
                          feedback.success
                            ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
                            : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                        )}
                      >
                        {feedback.success ? (
                          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-500" />
                        ) : (
                          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                        )}
                        <span className="leading-snug">{feedback.message}</span>
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800">
                    <button
                      onClick={() => handleTestChannel(config.id)}
                      disabled={isTesting}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition-colors disabled:opacity-50"
                    >
                      {isTesting ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-500" />
                      ) : (
                        <Send className="w-3.5 h-3.5 text-brand-500" />
                      )}
                      <span>{isTesting ? 'Sending Test...' : 'Send Test Alert'}</span>
                    </button>

                    <button
                      onClick={() => handleDeleteChannel(config.id)}
                      disabled={isDeleting}
                      className="p-1.5 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors disabled:opacity-50"
                      title="Delete Channel"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Notification Delivery History Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Delivery History
            </h3>
            <p className="text-[11px] text-slate-500">
              Audit log of dispatched incident alerts and channel verification tests
            </p>
          </div>
          <button
            onClick={loadHistory}
            disabled={isLoadingHistory}
            className="text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', isLoadingHistory && 'animate-spin')} />
            <span>Refresh Logs</span>
          </button>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
          {isLoadingHistory ? (
            <div className="p-8 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-brand-500" />
              <span>Loading delivery history...</span>
            </div>
          ) : history.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No notification deliveries recorded for this project yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Channel</th>
                    <th className="py-3 px-4">Target / Recipient</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Dispatched At</th>
                    <th className="py-3 px-4">Details / Errors</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                  {history.map((log) => {
                    const isSuccess = log.status?.toUpperCase() === 'SENT';
                    return (
                      <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className="p-1 rounded bg-slate-100 dark:bg-slate-800">
                              {getChannelIcon(log.channel_type)}
                            </span>
                            <span className="font-semibold uppercase font-mono text-[11px] text-slate-700 dark:text-slate-300">
                              {log.channel_type}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-600 dark:text-slate-400 truncate max-w-xs">
                          {log.recipient}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span
                            className={clsx(
                              'text-[10px] font-bold px-2 py-0.5 rounded-full font-mono uppercase inline-flex items-center gap-1',
                              isSuccess
                                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                            )}
                          >
                            <span
                              className={clsx(
                                'w-1.5 h-1.5 rounded-full',
                                isSuccess ? 'bg-emerald-500' : 'bg-rose-500'
                              )}
                            />
                            {log.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                          {new Date(log.sent_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-slate-500 dark:text-slate-400">
                          {log.error_message ? (
                            <span className="text-rose-500 font-mono text-[11px]">{log.error_message}</span>
                          ) : log.incident_id ? (
                            <span className="text-slate-400 font-mono text-[11px]">
                              Incident: {log.incident_id.slice(0, 8)}...
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[11px]">Channel Test Verification</span>
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
      </div>

      {/* Add Alert Channel Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Alert Channel"
      >
        <form onSubmit={handleCreateChannel} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-600 dark:text-rose-400 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Channel Type
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { id: 'slack', label: 'Slack', icon: MessageSquare },
                { id: 'discord', label: 'Discord', icon: MessageSquare },
                { id: 'webhook', label: 'Webhook', icon: Globe },
                { id: 'email', label: 'Email', icon: Mail },
              ].map((t) => {
                const Icon = t.icon;
                const isSelected = channelType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setChannelType(t.id)}
                    className={clsx(
                      'flex flex-col items-center justify-center p-3 rounded-xl border text-xs font-semibold transition-all gap-1.5',
                      isSelected
                        ? 'border-brand-500 bg-brand-500/10 text-brand-500 shadow-sm'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {channelType === 'email' ? (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Recipient Email Address
              </label>
              <input
                type="email"
                required
                value={targetEmail}
                onChange={(e) => setTargetEmail(e.target.value)}
                placeholder="oncall@company.com"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Incident alerts will be sent to this email address.
              </p>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Webhook URL
              </label>
              <input
                type="url"
                required
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder={
                  channelType === 'slack'
                    ? 'https://hooks.slack.com/services/T000/B000/XXXX'
                    : channelType === 'discord'
                    ? 'https://discord.com/api/webhooks/000/XXXX'
                    : 'https://api.yourcompany.com/incidents/webhook'
                }
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono text-[11px]"
              />
              <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <Info className="w-3 h-3 text-slate-400" />
                <span>
                  {channelType === 'slack'
                    ? 'Create an Incoming Webhook in your Slack Workspace App settings.'
                    : channelType === 'discord'
                    ? 'Create a Webhook integration in your Discord channel settings.'
                    : 'Standard POST payload containing incident title, severity, and root cause analysis.'}
                </span>
              </p>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Minimum Incident Severity Threshold
            </label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="P3">P3 & Above (All Incidents)</option>
              <option value="P2">P2 & Above (Low, High & Critical)</option>
              <option value="P1">P1 & Above (High & Critical Only)</option>
              <option value="P0">P0 Only (Critical Outages Only)</option>
            </select>
            <p className="text-[11px] text-slate-400 mt-1">
              Incidents with severity lower than this threshold will not trigger alerts on this channel.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsAddModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-brand-500 hover:bg-brand-600 rounded-xl transition-colors shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? 'Adding...' : 'Add Alert Channel'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

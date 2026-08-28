import React, { useState, useEffect, useCallback } from 'react';
import { useProject } from '@/context/ProjectContext';
import { projectsApi } from '@/api/projects';
import { Check, Copy, Key, Server, Terminal, ShieldAlert, Trash2, AlertCircle, ShieldCheck, Eye, EyeOff } from 'lucide-react';
import { Modal } from '../common/Modal';
import { ConfirmModal } from '../common/ConfirmModal';

export const SdkOnboardingStep = () => {
  const { activeProject } = useProject();
  const [selectedTech, setSelectedTech] = useState('nodejs');
  const [keyName, setKeyName] = useState('Service Ingestion Key');
  const [generatedKey, setGeneratedKey] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // SDK Key state
  const [apiKeys, setApiKeys] = useState([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);
  const [isDeletingKey, setIsDeletingKey] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Reveal state
  const [revealedKey, setRevealedKey] = useState(null);
  const [isRevealing, setIsRevealing] = useState(false);
  const [copiedRevealedKey, setCopiedRevealedKey] = useState(false);

  // Custom Confirmation Modal state
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState(null);
  const [confirmError, setConfirmError] = useState('');

  const refetchKeys = useCallback(async () => {
    if (!activeProject?.id) return;
    setIsLoadingKeys(true);
    setErrorMsg('');
    try {
      const keys = await projectsApi.listApiKeys(activeProject.id);
      setApiKeys(keys || []);
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
    } finally {
      setIsLoadingKeys(false);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    let isCancelled = false;

    // Reset all project-specific local state immediately when switching active project
    setApiKeys([]);
    setRevealedKey(null);
    setGeneratedKey(null);
    setKeyToRevoke(null);
    setIsConfirmModalOpen(false);
    setConfirmError('');
    setErrorMsg('');
    setCopiedKey(false);
    setCopiedRevealedKey(false);

    if (!activeProject?.id) {
      setIsLoadingKeys(false);
      return;
    }

    setIsLoadingKeys(true);

    const loadKeysForProject = async () => {
      const targetProjectId = activeProject.id;
      try {
        const keys = await projectsApi.listApiKeys(targetProjectId);
        if (!isCancelled) {
          setApiKeys(keys || []);
        }
      } catch (err) {
        if (!isCancelled) {
          console.error('Failed to fetch API keys:', err);
          const apiErr = err.response?.data?.error?.message || err.message || 'Failed to fetch project SDK API keys.';
          setErrorMsg(typeof apiErr === 'string' ? apiErr : JSON.stringify(apiErr));
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingKeys(false);
        }
      }
    };

    loadKeysForProject();

    return () => {
      isCancelled = true;
    };
  }, [activeProject?.id]);

  const activeApiKey = apiKeys.find((k) => k.is_active);

  const handleCreateApiKey = async (e) => {
    e.preventDefault();
    if (!activeProject) return;

    setIsGenerating(true);
    setErrorMsg('');
    setRevealedKey(null);
    try {
      const res = await projectsApi.createApiKey(activeProject.id, {
        name: keyName,
        environment: activeProject.environment || 'production',
      });
      setGeneratedKey(res.raw_key || '');
      setIsModalOpen(true);
      await refetchKeys();
    } catch (err) {
      console.error('Failed to create API key:', err);
      const apiErr = err.response?.data?.error?.message || err.response?.data?.message || err.response?.data?.detail || err.message || 'Failed to generate SDK API key.';
      setErrorMsg(typeof apiErr === 'string' ? apiErr : JSON.stringify(apiErr));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevealApiKey = async (keyId) => {
    if (!activeProject) return;
    if (revealedKey) {
      setRevealedKey(null);
      return;
    }

    setIsRevealing(true);
    setErrorMsg('');
    try {
      const res = await projectsApi.revealApiKey(activeProject.id, keyId);
      setRevealedKey(res.raw_key);
    } catch (err) {
      console.error('Failed to reveal API key:', err);
      const apiErr = err.response?.data?.error?.message || err.response?.data?.message || err.response?.data?.detail || err.message || 'Failed to reveal SDK API key.';
      setErrorMsg(typeof apiErr === 'string' ? apiErr : JSON.stringify(apiErr));
    } finally {
      setIsRevealing(false);
    }
  };

  const handleOpenConfirmModal = (key) => {
    setKeyToRevoke(key);
    setConfirmError('');
    setIsConfirmModalOpen(true);
  };

  const handleConfirmRevokeApiKey = async () => {
    if (!activeProject || !keyToRevoke) return;

    setIsDeletingKey(true);
    setConfirmError('');
    try {
      await projectsApi.deleteApiKey(activeProject.id, keyToRevoke.id);
      setGeneratedKey(null);
      setRevealedKey(null);
      setIsConfirmModalOpen(false);
      setKeyToRevoke(null);
      await refetchKeys();
    } catch (err) {
      console.error('Failed to delete API key:', err);
      const apiErr = err.message || err.response?.data?.error?.message || err.response?.data?.message || 'Unable to revoke this key. Please try again.';
      setConfirmError(typeof apiErr === 'string' ? apiErr : JSON.stringify(apiErr));
    } finally {
      setIsDeletingKey(false);
    }
  };

  const handleCopyKey = () => {
    if (generatedKey) {
      navigator.clipboard.writeText(generatedKey);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleCopyRevealedKey = () => {
    if (revealedKey) {
      navigator.clipboard.writeText(revealedKey);
      setCopiedRevealedKey(true);
      setTimeout(() => setCopiedRevealedKey(false), 2000);
    }
  };

  const currentDisplayKey = revealedKey || generatedKey;

  const backendIngestUrl = (import.meta.env.VITE_API_BASE_URL || 'https://sentinelai-backend-w23eki576a-uc.a.run.app/api/v1') + '/sdk/ingest';

  const nodeCodeExample = `import { SentinelAIClient } from '@sentinelai/sdk';

const sdk = new SentinelAIClient({
    apiKey: "${currentDisplayKey || (activeApiKey ? activeApiKey.prefix + '...' : 'YOUR_SENTINELAI_API_KEY')}",
    serviceName: "${activeProject?.name?.toLowerCase().replace(/\s+/g, '-') || 'my-service'}",
    endpointUrl: "${backendIngestUrl}"
});

// Capture HTTP request telemetry, errors, and traces
app.use(sdk.expressMiddleware());`;

  const pythonCodeExample = `from backend.sdk.client import SentinelAISDKClient

sdk = SentinelAISDKClient(
    api_key="${currentDisplayKey || (activeApiKey ? activeApiKey.prefix + '...' : 'YOUR_SENTINELAI_API_KEY')}",
    service_name="${activeProject?.name?.toLowerCase().replace(/\s+/g, '-') || 'my-service'}",
    endpoint_url="${backendIngestUrl}"
)

# Capture log signal
sdk.capture_log("ERROR", "Database connection pool timeout", attributes={"pool_size": 50})`;

  const activeCode = selectedTech === 'nodejs' ? nodeCodeExample : pythonCodeExample;

  const handleCopyCode = () => {
    navigator.clipboard.writeText(activeCode);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Onboarding Stepper Header */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Server className="w-5 h-5 text-brand-500" />
          Connect Your Application via SDK
        </h3>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Connect your microservices to Sentinel AI to automatically ingest logs, uncaught exceptions, trace spans, and metric anomalies for AI Root Cause Analysis.
        </p>

        {/* Tech Selector */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={() => setSelectedTech('nodejs')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
              selectedTech === 'nodejs'
                ? 'bg-brand-500 text-white border-brand-500 shadow-md shadow-brand-500/20'
                : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100'
            }`}
          >
            Node.js (Express)
          </button>
          <button
            onClick={() => setSelectedTech('python')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
              selectedTech === 'python'
                ? 'bg-brand-500 text-white border-brand-500 shadow-md shadow-brand-500/20'
                : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100'
            }`}
          >
            Python (FastAPI / Flask)
          </button>
        </div>
      </div>

      {/* Error Message Banner */}
      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Step 1: SDK Ingestion API Key Management */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Key className="w-4 h-4 text-amber-500" />
          Step 1: SDK Ingestion API Key
        </h4>

        {isLoadingKeys ? (
          <div className="py-4 text-xs text-slate-500 flex items-center gap-2">
            <span className="w-4 h-4 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            <span>Fetching SDK API key for {activeProject?.name || 'selected project'}...</span>
          </div>
        ) : activeApiKey ? (
          /* Active Key Display State */
          <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                    {activeApiKey.name}
                  </span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                    <ShieldCheck className="w-3 h-3" />
                    Active Ingestion Key
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-500 mt-1">
                  Prefix: <span className="font-bold text-slate-700 dark:text-slate-300">{activeApiKey.prefix}...</span>
                  <span className="mx-2">•</span>
                  Environment: <span className="uppercase text-[10px] font-bold">{activeApiKey.environment}</span>
                  <span className="mx-2">•</span>
                  Created: {new Date(activeApiKey.created_at).toLocaleDateString()}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleRevealApiKey(activeApiKey.id)}
                  disabled={isRevealing}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  {revealedKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5 text-brand-500" />}
                  {isRevealing ? 'Revealing...' : revealedKey ? 'Hide Key' : 'Reveal Key'}
                </button>

                <button
                  type="button"
                  onClick={() => handleOpenConfirmModal(activeApiKey)}
                  disabled={isDeletingKey}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/20 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Revoke / Delete Key
                </button>
              </div>
            </div>

            {/* Revealed Raw Key Banner */}
            {revealedKey && (
              <div className="pt-2 space-y-2 border-t border-emerald-500/20">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between font-mono text-xs text-amber-400">
                  <span className="truncate">{revealedKey}</span>
                  <button
                    type="button"
                    onClick={handleCopyRevealedKey}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-brand-500 hover:bg-brand-600 text-white text-xs font-sans font-semibold transition-colors"
                  >
                    {copiedRevealedKey ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedRevealedKey ? 'Copied' : 'Copy Key'}
                  </button>
                </div>
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-[11px] flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                  <span>Keep this key secure. Do not share or commit raw keys to public code repositories.</span>
                </div>
              </div>
            )}

            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              This project currently has an active SDK key. To generate a replacement key, you must explicitly revoke/delete the existing active key first.
            </p>
          </div>
        ) : (
          /* Generate Key Form State (No Active Key) */
          <form onSubmit={handleCreateApiKey} className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              placeholder="Key Name (e.g. Service Ingestion Key)"
              className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500 flex-1 min-w-[200px]"
            />
            <button
              type="submit"
              disabled={isGenerating || !activeProject}
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors shadow-sm disabled:opacity-50"
            >
              {isGenerating ? 'Generating...' : 'Generate SDK Key'}
            </button>
          </form>
        )}

        {generatedKey && !revealedKey && (
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between font-mono text-xs text-amber-400">
            <span className="truncate">{generatedKey}</span>
            <button
              onClick={handleCopyKey}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-sans font-semibold transition-colors"
            >
              {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copiedKey ? 'Copied' : 'Copy'}
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Code Integration Snippet */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-500" />
            Step 2: Install & Initialize SDK Code
          </h4>
          <button
            onClick={handleCopyCode}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition-colors"
          >
            {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            {copiedCode ? 'Copied Snippet' : 'Copy Code'}
          </button>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-emerald-400 overflow-x-auto">
          <pre>{activeCode}</pre>
        </div>
      </div>

      {/* Raw API Key Display Modal (Displayed ONCE upon creation) */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Copy Your SDK API Key"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-xs flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-500 flex-shrink-0" />
            <span>Save this raw key now. It is encrypted securely in the database and can be revealed anytime by authorized project members.</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-sm text-amber-400 flex items-center justify-between">
            <span className="truncate">{generatedKey}</span>
            <button
              onClick={handleCopyKey}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-brand-500 text-white font-semibold text-xs hover:bg-brand-600 transition-colors"
            >
              {copiedKey ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copiedKey ? 'Copied' : 'Copy Key'}
            </button>
          </div>

          <div className="pt-2 text-right">
            <button
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200"
            >
              Done & Dismiss
            </button>
          </div>
        </div>
      </Modal>

      {/* Custom Confirmation Modal for SDK Key Revocation */}
      <ConfirmModal
        isOpen={isConfirmModalOpen}
        onClose={() => {
          if (!isDeletingKey) {
            setIsConfirmModalOpen(false);
            setKeyToRevoke(null);
            setConfirmError('');
          }
        }}
        onConfirm={handleConfirmRevokeApiKey}
        title="Revoke SDK ingestion key?"
        description="This will immediately stop this key from sending telemetry to Sentinel AI. The key will be permanently deleted and cannot be recovered."
        keyPrefix={keyToRevoke ? keyToRevoke.prefix : ''}
        confirmText="Revoke Key"
        cancelText="Cancel"
        isLoading={isDeletingKey}
        error={confirmError}
      />
    </div>
  );
};

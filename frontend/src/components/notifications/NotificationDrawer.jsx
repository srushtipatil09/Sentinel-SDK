import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationsApi } from '@/api/notifications';
import { NotificationHistoryItem } from '@/types/api';
import {
  Bell,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Sliders,
  Send,
  Mail,
  MessageSquare,
  Globe
} from 'lucide-react';
import { clsx } from 'clsx';

export const NotificationDrawer = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchRecent = async () => {
    setIsLoading(true);
    try {
      const data = await notificationsApi.getRecentNotifications(10);
      setItems(data || []);
    } catch (err) {
      console.error('Failed to fetch recent notifications:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchRecent();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const getChannelIcon = (channel) => {
    switch ((channel || '').toLowerCase()) {
      case 'slack':
        return <MessageSquare className="w-3.5 h-3.5 text-[#4A154B]" />;
      case 'discord':
        return <MessageSquare className="w-3.5 h-3.5 text-[#5865F2]" />;
      case 'email':
        return <Mail className="w-3.5 h-3.5 text-blue-500" />;
      default:
        return <Globe className="w-3.5 h-3.5 text-emerald-500" />;
    }
  };

  const formatTimestamp = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/10 dark:bg-black/30 backdrop-blur-[1px]"
        onClick={onClose}
      />

      {/* Popover Card */}
      <div className="absolute right-0 top-12 w-80 sm:w-96 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden animate-fade-in text-slate-900 dark:text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-brand-500/10 text-brand-500">
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 leading-tight">
                Alerts & Notifications
              </h4>
              <p className="text-[10px] text-slate-400 leading-tight">
                Real-time incident dispatch logs
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={fetchRecent}
              disabled={isLoading}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={clsx('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            </button>
            <button
              onClick={() => {
                onClose();
                navigate('/settings?tab=notifications');
              }}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
              title="Configure Channels"
            >
              <Sliders className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Content list */}
        <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/60 p-1">
          {isLoading && items.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-brand-500" />
              <span>Loading notification activity...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="py-8 px-4 text-center">
              <div className="w-10 h-10 mx-auto rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center mb-2">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                All Systems Operational
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                No recent alerts or failed dispatches recorded.
              </p>
            </div>
          ) : (
            items.map((item) => {
              const isSuccess = item.status?.toUpperCase() === 'SENT';
              return (
                <div
                  key={item.id}
                  className="p-3 hover:bg-slate-50 dark:hover:bg-slate-800/40 rounded-xl transition-colors space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="p-1 rounded bg-slate-100 dark:bg-slate-800">
                        {getChannelIcon(item.channel_type)}
                      </span>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                        {item.channel_type}
                      </span>
                      <span
                        className={clsx(
                          'text-[9px] font-bold px-1.5 py-0.2 rounded font-mono uppercase',
                          isSuccess
                            ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                        )}
                      >
                        {item.status}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      {formatTimestamp(item.sent_at)}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-600 dark:text-slate-400 truncate font-mono">
                    {item.recipient}
                  </div>

                  {item.error_message && (
                    <div className="flex items-start gap-1 text-[10px] text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 p-1.5 rounded-lg border border-rose-200 dark:border-rose-900/50">
                      <AlertCircle className="w-3 h-3 shrink-0 mt-0.5" />
                      <span className="truncate">{item.error_message}</span>
                    </div>
                  )}

                  {item.incident_id && (
                    <button
                      onClick={() => {
                        onClose();
                        navigate(`/incidents/${item.incident_id}`);
                      }}
                      className="text-[10px] font-medium text-brand-500 hover:text-brand-600 dark:hover:text-brand-400 flex items-center gap-1 pt-0.5"
                    >
                      <span>View Related Incident</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-2.5 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-100 dark:border-slate-800 text-center">
          <button
            onClick={() => {
              onClose();
              navigate('/settings?tab=notifications');
            }}
            className="text-xs font-semibold text-brand-500 hover:text-brand-600 dark:hover:text-brand-400 transition-colors inline-flex items-center gap-1.5"
          >
            <span>Manage Notification Channels in Settings</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </>
  );
};

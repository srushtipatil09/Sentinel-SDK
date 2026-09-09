import { apiClient, unwrapData } from './client';
import {
  APIResponse,
  CreateNotificationConfigPayload,
  NotificationConfig,
  NotificationHistoryItem,
  NotificationTestResult,
  UpdateNotificationConfigPayload,
} from '@/types/api';

export const notificationsApi = {
  async listConfigs(projectId: string): Promise<NotificationConfig[]> {
    const res = await apiClient.get<APIResponse<NotificationConfig[]>>(
      `/projects/${projectId}/notifications/configs`
    );
    return unwrapData(res);
  },

  async createConfig(
    projectId: string,
    payload: CreateNotificationConfigPayload
  ): Promise<NotificationConfig> {
    const res = await apiClient.post<APIResponse<NotificationConfig>>(
      `/projects/${projectId}/notifications/configs`,
      payload
    );
    return unwrapData(res);
  },

  async updateConfig(
    projectId: string,
    configId: string,
    payload: UpdateNotificationConfigPayload
  ): Promise<NotificationConfig> {
    const res = await apiClient.put<APIResponse<NotificationConfig>>(
      `/projects/${projectId}/notifications/configs/${configId}`,
      payload
    );
    return unwrapData(res);
  },

  async deleteConfig(projectId: string, configId: string): Promise<{ deleted: boolean }> {
    const res = await apiClient.delete<APIResponse<{ deleted: boolean }>>(
      `/projects/${projectId}/notifications/configs/${configId}`
    );
    return unwrapData(res);
  },

  async testConfig(projectId: string, configId: string): Promise<NotificationTestResult> {
    const res = await apiClient.post<APIResponse<NotificationTestResult>>(
      `/projects/${projectId}/notifications/configs/${configId}/test`
    );
    return unwrapData(res);
  },

  async getHistory(
    projectId: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<NotificationHistoryItem[]> {
    const res = await apiClient.get<APIResponse<NotificationHistoryItem[]>>(
      `/projects/${projectId}/notifications/history`,
      { params: { limit, offset } }
    );
    return unwrapData(res);
  },

  async getRecentNotifications(limit: number = 15): Promise<NotificationHistoryItem[]> {
    const res = await apiClient.get<APIResponse<NotificationHistoryItem[]>>(
      '/notifications/recent',
      { params: { limit } }
    );
    return unwrapData(res);
  },
};

import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export interface Item {
  type_id: number;
  name: string;
  avg_buy_price: number;
  avg_sell_price: number;
  predicted_buy_price: number;
  predicted_sell_price: number;
  profit_per_unit: number;
  roi_percent: number;
  volume_30d_avg: number;
  volatility: number;
  trend_direction: string;
  last_updated: string;
}

export interface ItemDetail extends Item {
  description: string;
  thumbnail_url: string;
  price_history: { date: string; buy: number; sell: number }[];
  volume_history: { date: string; volume: number }[];
  profit_history: { date: string; profit_per_unit: number; roi_percent: number }[];
}

export interface Status {
  status: string;
  last_data_refresh: string;
  total_items_analyzed: number;
  system_uptime: string;
}

export const getTopItems = async (region: string = '10000002', limit: number = 100): Promise<Item[]> => {
  const response = await api.get(`/top-items?region=${region}&limit=${limit}`);
  return response.data;
};

export const getItemDetails = async (typeId: number): Promise<ItemDetail> => {
  const response = await api.get(`/item/${typeId}`);
  return response.data;
};

export const getStatus = async (): Promise<Status> => {
  const response = await api.get('/status');
  return response.data;
};
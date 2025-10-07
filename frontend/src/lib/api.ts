import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export interface Item {
  type_id: number;
  name: string;
  avg_buy_price: number | null;
  avg_sell_price: number | null;
  predicted_buy_price: number | null;
  predicted_sell_price: number | null;
  profit_per_unit: number | null;
  roi_percent: number | null;
  volume_30d_avg: number | null;
  volatility: number | null;
  trend_direction: string | null;
  last_updated: string | null;
}

export interface ItemDetail extends Item {
  description: string | null;
  thumbnail_url: string;
  price_history: { date: string; buy: number; sell: number }[];
  volume_history: { date: string; volume: number }[];
  profit_history: { date: string; profit_per_unit: number; roi_percent: number }[];
}

export interface Status {
  pipeline_status: string;
  initial_seeding_complete: boolean;
  last_data_update: string | null;
  last_analysis_update: string | null;
}

export const getTopItems = async (region: string = '10000002', limit: number = 100): Promise<Item[]> => {
  const response = await api.get(`/top-items?region=${region}&limit=${limit}`);
  return response.data;
};

export const getItemDetails = async (typeId: number, regionId: number): Promise<ItemDetail> => {
  const response = await api.get(`/item/${typeId}?region_id=${regionId}`);
  return response.data;
};

export const getStatus = async (): Promise<Status> => {
  const response = await api.get('/status');
  return response.data;
};
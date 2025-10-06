import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  region: string;
  minRoi: number;
  minVolume: number;
  taxRate: number;
  brokerFee: number;
  setRegion: (region: string) => void;
  setMinRoi: (minRoi: number) => void;
  setMinVolume: (minVolume: number) => void;
  setTaxRate: (taxRate: number) => void;
  setBrokerFee: (brokerFee: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      region: '10000002', // The Forge
      minRoi: 0,
      minVolume: 0,
      taxRate: 0.05,
      brokerFee: 0.03,
      setRegion: (region) => set({ region }),
      setMinRoi: (minRoi) => set({ minRoi }),
      setMinVolume: (minVolume) => set({ minVolume }),
      setTaxRate: (taxRate) => set({ taxRate }),
      setBrokerFee: (brokerFee) => set({ brokerFee }),
    }),
    {
      name: 'eve-market-analyzer-settings', // name of the item in the storage (must be unique)
    }
  )
);
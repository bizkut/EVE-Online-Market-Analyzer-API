'use client';

import React from 'react';
import { useSettingsStore } from '@/stores/settingsStore';

const SettingsPanel = () => {
  const {
    region,
    minRoi,
    minVolume,
    taxRate,
    brokerFee,
    setRegion,
    setMinRoi,
    setMinVolume,
    setTaxRate,
    setBrokerFee,
  } = useSettingsStore();

  return (
    <div className="bg-panel p-4 rounded-2xl shadow-lg border border-gray-700/50">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div>
          <label htmlFor="region" className="block text-sm font-medium text-gray-300">
            Region
          </label>
          <select
            id="region"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-600 bg-background/50 text-white focus:outline-none focus:ring-accent focus:border-accent sm:text-sm rounded-md"
          >
            <option value="10000002">The Forge</option>
            <option value="10000043">Jita</option>
            <option value="10000032">Domain</option>
            <option value="10000042">Metropolis</option>
            <option value="10000030">Heimatar</option>
          </select>
        </div>
        <div>
          <label htmlFor="minRoi" className="block text-sm font-medium text-gray-300">
            Min ROI (%)
          </label>
          <input
            type="number"
            id="minRoi"
            value={minRoi * 100}
            onChange={(e) => setMinRoi(parseFloat(e.target.value) / 100)}
            className="mt-1 block w-full border-gray-600 bg-background/50 text-white rounded-md shadow-sm focus:ring-accent focus:border-accent sm:text-sm"
          />
        </div>
        <div>
          <label htmlFor="minVolume" className="block text-sm font-medium text-gray-300">
            Min Daily Volume
          </label>
          <input
            type="number"
            id="minVolume"
            value={minVolume}
            onChange={(e) => setMinVolume(parseInt(e.target.value))}
            className="mt-1 block w-full border-gray-600 bg-background/50 text-white rounded-md shadow-sm focus:ring-accent focus:border-accent sm:text-sm"
          />
        </div>
        <div>
          <label htmlFor="taxRate" className="block text-sm font-medium text-gray-300">
            Tax Rate (%)
          </label>
          <input
            type="number"
            id="taxRate"
            value={taxRate * 100}
            onChange={(e) => setTaxRate(parseFloat(e.target.value) / 100)}
            className="mt-1 block w-full border-gray-600 bg-background/50 text-white rounded-md shadow-sm focus:ring-accent focus:border-accent sm:text-sm"
          />
        </div>
        <div>
          <label htmlFor="brokerFee" className="block text-sm font-medium text-gray-300">
            Broker Fee (%)
          </label>
          <input
            type="number"
            id="brokerFee"
            value={brokerFee * 100}
            onChange={(e) => setBrokerFee(parseFloat(e.target.value) / 100)}
            className="mt-1 block w-full border-gray-600 bg-background/50 text-white rounded-md shadow-sm focus:ring-accent focus:border-accent sm:text-sm"
          />
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
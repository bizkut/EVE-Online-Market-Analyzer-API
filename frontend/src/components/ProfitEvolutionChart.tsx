'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ProfitHistoryPoint {
  date: string;
  profit_per_unit: number;
  roi_percent: number;
}

interface ProfitEvolutionChartProps {
  data: ProfitHistoryPoint[];
}

const ProfitEvolutionChart: React.FC<ProfitEvolutionChartProps> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9CA3AF" />
        <YAxis yAxisId="left" stroke="#10B981" />
        <YAxis yAxisId="right" orientation="right" stroke="#00b0ff" />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            borderColor: '#374151',
          }}
        />
        <Legend />
        <Line yAxisId="left" type="monotone" dataKey="profit_per_unit" stroke="#10B981" name="Profit Per Unit" />
        <Line yAxisId="right" type="monotone" dataKey="roi_percent" stroke="#00b0ff" name="ROI (%)" />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default ProfitEvolutionChart;
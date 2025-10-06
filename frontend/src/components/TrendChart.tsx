'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TrendChartProps {
  data: { date: string; buy: number; sell: number }[];
}

const TrendChart: React.FC<TrendChartProps> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9CA3AF" />
        <YAxis stroke="#9CA3AF" />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            borderColor: '#374151',
          }}
        />
        <Legend />
        <Line type="monotone" dataKey="buy" stroke="#10B981" name="Buy Price" />
        <Line type="monotone" dataKey="sell" stroke="#EF4444" name="Sell Price" />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default TrendChart;
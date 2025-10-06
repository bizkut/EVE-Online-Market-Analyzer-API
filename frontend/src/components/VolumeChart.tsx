'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface VolumeChartProps {
  data: { date: string; volume: number }[];
}

const VolumeChart: React.FC<VolumeChartProps> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
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
        <Bar dataKey="volume" fill="#00b0ff" name="Volume" />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default VolumeChart;
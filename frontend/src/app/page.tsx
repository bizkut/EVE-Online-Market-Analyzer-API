import Layout from '@/components/Layout';
import TopItemsTable from '@/components/TopItemsTable';
import ItemDetailModal from '@/components/ItemDetailModal';
import SettingsPanel from '@/components/SettingsPanel';
import React from 'react';

const HomePage: React.FC = () => {
  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-3xl font-bold text-white font-orbitron">Top Profitable Items</h2>
        </div>
        <SettingsPanel />
        <div>
          <TopItemsTable />
          <ItemDetailModal />
        </div>
      </div>
    </Layout>
  );
};

export default HomePage;
'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTopItems, Item } from '@/lib/api';
import { useModalStore } from '@/stores/modalStore';
import { useSettingsStore } from '@/stores/settingsStore';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown, Minus } from 'lucide-react';

const formatNumber = (num: number) => new Intl.NumberFormat('en-US').format(num);
const formatCurrency = (num: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'ISK' }).format(num);
const formatPercent = (num: number) => `${(num * 100).toFixed(2)}%`;

const columns: ColumnDef<Item>[] = [
    {
        accessorKey: 'name',
        header: 'Item',
    },
    {
        accessorKey: 'avg_buy_price',
        header: ({ column }) => {
            return (
                <button
                    className="flex items-center space-x-2"
                    onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                >
                    <span>Buy Price</span>
                    <ArrowUpDown className="h-4 w-4" />
                </button>
            )
        },
        cell: ({ row }) => formatCurrency(row.original.avg_buy_price),
    },
    {
        accessorKey: 'avg_sell_price',
        header: ({ column }) => {
            return (
                <button
                    className="flex items-center space-x-2"
                    onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                >
                    <span>Sell Price</span>
                    <ArrowUpDown className="h-4 w-4" />
                </button>
            )
        },
        cell: ({ row }) => formatCurrency(row.original.avg_sell_price),
    },
    {
        accessorKey: 'profit_per_unit',
        header: ({ column }) => {
            return (
                <button
                    className="flex items-center space-x-2"
                    onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                >
                    <span>Profit</span>
                    <ArrowUpDown className="h-4 w-4" />
                </button>
            )
        },
        cell: ({ row }) => {
            const profit = row.original.profit_per_unit;
            const color = profit > 0 ? 'text-profit-positive' : profit < 0 ? 'text-profit-negative' : '';
            return <span className={color}>{formatCurrency(profit)}</span>;
        },
    },
    {
        accessorKey: 'roi_percent',
        header: ({ column }) => {
            return (
                <button
                    className="flex items-center space-x-2"
                    onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                >
                    <span>ROI</span>
                    <ArrowUpDown className="h-4 w-4" />
                </button>
            )
        },
        cell: ({ row }) => {
            const roi = row.original.roi_percent;
            const color = roi > 0 ? 'text-profit-positive' : roi < 0 ? 'text-profit-negative' : '';
            return <span className={color}>{formatPercent(roi)}</span>;
        },
    },
    {
        accessorKey: 'volume_30d_avg',
        header: ({ column }) => {
            return (
                <button
                    className="flex items-center space-x-2"
                    onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                >
                    <span>Volume</span>
                    <ArrowUpDown className="h-4 w-4" />
                </button>
            )
        },
        cell: ({ row }) => formatNumber(row.original.volume_30d_avg),
    },
    {
        accessorKey: 'trend_direction',
        header: 'Trend',
        cell: ({ row }) => {
            const trend = row.original.trend_direction;
            if (trend === 'up') return <ArrowUp className="text-profit-positive" />;
            if (trend === 'down') return <ArrowDown className="text-profit-negative" />;
            return <Minus className="text-gray-500" />;
        },
    },
];

const TopItemsTable = () => {
    const [sorting, setSorting] = useState<SortingState>([]);
    const { openModal } = useModalStore();
    const { region, minRoi, minVolume } = useSettingsStore();

    const { data: items, isLoading, error } = useQuery({
        queryKey: ['topItems', region],
        queryFn: () => getTopItems(region),
    });

    const filteredItems = useMemo(() => {
        if (!items) return [];
        return items.filter(item => item.roi_percent >= minRoi && item.volume_30d_avg >= minVolume);
    }, [items, minRoi, minVolume]);

    const table = useReactTable({
        data: filteredItems,
        columns,
        getCoreRowModel: getCoreRowModel(),
        onSortingChange: setSorting,
        getSortedRowModel: getSortedRowModel(),
        state: {
            sorting,
        },
    });

    if (isLoading) return <p>Loading...</p>;
    if (error) return <p>Error loading data</p>;

    return (
        <div className="bg-panel rounded-2xl shadow-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-800/50">
                    {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id}>
                            {headerGroup.headers.map((header) => (
                                <th key={header.id} className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                                </th>
                            ))}
                        </tr>
                    ))}
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                    {table.getRowModel().rows.map((row) => (
                        <tr
                            key={row.id}
                            className="hover:bg-gray-700/50 cursor-pointer"
                            onClick={() => openModal(row.original.type_id)}
                        >
                            {row.getVisibleCells().map((cell) => (
                                <td key={cell.id} className="px-6 py-4 whitespace-nowrap">
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default TopItemsTable;
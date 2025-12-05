"use client";
import { useEffect, useState } from 'react';
import OrderTrends from '../OrderTrends';
import MostFrequentCustomers from '../MostFrequentCustomers';
import TopCustomersBySpending from '../TopCustomersBySpending';
import { AlertCircle, RefreshCcw } from 'lucide-react';

interface OrderTrendsData {
  dates: string[];
  counts: number[];
}

interface FrequentCustomersData {
  names: string[];
  counts: number[];
}

interface TopSpendersData {
  names: string[];
  amounts: number[];
}

interface CustomerAnalyticsData {
  orderTrends: OrderTrendsData;
  frequentCustomers: FrequentCustomersData;
  topSpenders: TopSpendersData;
}

export default function CustomerDashboard() {
  const [data, setData] = useState<CustomerAnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/customer-analytics`);
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      
      const jsonData = await response.json();
      setData(jsonData);
      
    } catch (error) {
      console.error("Error fetching customer analytics:", error);
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] w-full">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-[#00E676] mb-4"></div>
        <p className="text-gray-400 animate-pulse">Analyzing customer data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] w-full text-red-500">
        <div className="bg-[#1A1A1A] border border-red-900/50 p-8 rounded-xl flex flex-col items-center shadow-lg">
          <AlertCircle size={48} className="mb-4 text-red-500" />
          <h2 className="text-xl font-bold mb-2 text-white">Unable to Load Data</h2>
          <p className="text-gray-400 text-center mb-6 max-w-md">{error}</p>
          <button 
            onClick={fetchData}
            className="flex items-center gap-2 px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            <RefreshCcw size={18} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto text-white animate-in fade-in duration-500">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#111111] p-6 rounded-xl border border-gray-800 shadow-xl">
          <h2 className="text-lg font-bold mb-6 text-gray-200 border-l-4 border-[#00E676] pl-3">
            Order Trends (30 Days)
          </h2>
          {data && <OrderTrends data={data.orderTrends} />}
        </div>
    
        <div className="bg-[#111111] p-6 rounded-xl border border-gray-800 shadow-xl">
          <h2 className="text-lg font-bold mb-6 text-gray-200 border-l-4 border-[#00E676] pl-3">
            Top 10 Customers (Spending)
          </h2>
          {data && <TopCustomersBySpending data={data.topSpenders} />}
        </div>
    
        <div className="bg-[#111111] p-6 rounded-xl border border-gray-800 shadow-xl col-span-1 lg:col-span-2">
          <h2 className="text-lg font-bold mb-6 text-gray-200 border-l-4 border-[#00E676] pl-3">
            Most Frequent Buyers
          </h2>
          {data && <MostFrequentCustomers data={data.frequentCustomers} />}
        </div>
      </div>
    </div>
  );
}
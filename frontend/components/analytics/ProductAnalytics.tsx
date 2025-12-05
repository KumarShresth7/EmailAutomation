"use client";
import { useEffect, useState } from 'react';
import BestWorstProducts from '../BestWorstProducts';
import RevenuePerDay from '../RevenuePerDay';
import CustomerFeedback from '../CustomerFeedback';
import { AnalyticsData } from '@/lib/types/analytics';
import { AlertCircle, RefreshCcw } from 'lucide-react';

export interface CustomerFeedbackItem {
  name: string;
  feedback: string;
  sentiment: string;
  date?: string; // Made optional as backend might not send it
}

export default function ProductDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [feedbackData, setFeedbackData] = useState<CustomerFeedbackItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAllData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/product-analytics`);
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const analyticsData = await response.json();
      
      // Validate data structure before setting state
      if (!analyticsData.productSales || !analyticsData.revenuePerDay) {
        throw new Error("Invalid data format received from server");
      }

      setData(analyticsData);
      setFeedbackData(analyticsData.customerFeedback || []);
      
    } catch (error) {
      console.error("Error fetching product analytics:", error);
      setError(error instanceof Error ? error.message : 'Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] w-full">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-[#00E676] mb-4"></div>
        <p className="text-gray-400 animate-pulse">Analyzing product data...</p>
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
            onClick={fetchAllData}
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
        {/* Best/Worst Chart */}
        <div className="bg-[#111111] p-6 rounded-xl border border-gray-800 shadow-xl">
          <h2 className="text-lg font-bold mb-6 text-gray-200 border-l-4 border-[#00E676] pl-3">
            Product Performance
          </h2>
          {data?.productSales && <BestWorstProducts data={data.productSales} />}
        </div>

        {/* Feedback Chart */}
        <div className="bg-[#111111] p-6 rounded-xl border border-gray-800 shadow-xl">
          <h2 className="text-lg font-bold mb-6 text-gray-200 border-l-4 border-[#00E676] pl-3">
            Customer Sentiment
          </h2>
          <CustomerFeedback data={feedbackData || []} />
        </div>

        {/* Revenue Chart */}
        <div className="bg-[#111111] p-6 rounded-xl border border-gray-800 shadow-xl lg:col-span-2">
          <h2 className="text-lg font-bold mb-6 text-gray-200 border-l-4 border-[#00E676] pl-3">
            Revenue Trend (30 Days)
          </h2>
          {data?.revenuePerDay && <RevenuePerDay data={data.revenuePerDay} />}
        </div>
      </div>
    </div>
  );
}
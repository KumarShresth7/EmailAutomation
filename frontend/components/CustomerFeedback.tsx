// components/CustomerFeedback.js
"use client";
import { Chart, registerables, ChartData, ChartOptions, TooltipItem } from 'chart.js';
import { Pie } from 'react-chartjs-2';

Chart.register(...registerables);

interface FeedbackData {
  sentiment: string;
}

interface CustomerFeedbackProps {
  data: FeedbackData[];
}

export default function CustomerFeedback({ data }: CustomerFeedbackProps) {
  // Count sentiment distribution
  const sentimentCounts = data.reduce((acc: { [key: string]: number }, item) => {
    acc[item.sentiment] = (acc[item.sentiment] || 0) + 1;
    return acc;
  }, {});
  
  const chartData: ChartData<'pie'> = {
    labels: Object.keys(sentimentCounts).map(key => 
      key.charAt(0).toUpperCase() + key.slice(1)
    ),
    datasets: [
      {
        data: Object.values(sentimentCounts),
        backgroundColor: [
          'rgba(144, 238, 129, 0.8)',  // positive - green
          'rgba(251, 191, 36, 0.8)',  // neutral - yellow
          'rgba(239, 68, 68, 0.8)'    // negative - red
        ],
        borderColor: [
          'rgba(16, 185, 129, 1)',
          'rgba(251, 191, 36, 1)',
          'rgba(239, 68, 68, 1)'
        ],
        borderWidth: 1,
      }
    ]
  };

  const options: ChartOptions<'pie'> = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: 'right' as const,
        labels: {
          color: 'rgba(255, 255, 255, 0.7)',
          padding: 20,
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        callbacks: {
          label: function(context: TooltipItem<'pie'>) {
            const label = context.label || '';
            const value = context.raw as number;
            const total = (context.dataset.data as number[]).reduce((acc, val) => acc + val, 0);
            const percentage = Math.round((value / total) * 100);
            return `${label}: ${value} (${percentage}%)`;
          }
        }
      }
    }
  };

  return (
    <div className="flex justify-center">
      <div className="w-3/4">
        <Pie data={chartData} options={options} />
      </div>
    </div>
  );
}

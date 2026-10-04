import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

interface SlaCountdownBadgeProps {
  deadlineIso?: string;
  priority: string;
}

export const SlaCountdownBadge: React.FC<SlaCountdownBadgeProps> = ({ deadlineIso, priority }) => {
  const [timeLeft, setTimeLeft] = useState<{ text: string; status: 'green' | 'amber' | 'red' }>({
    text: 'Calculating...',
    status: 'green'
  });

  useEffect(() => {
    if (!deadlineIso) {
      setTimeLeft({ text: `${priority} SLA`, status: 'green' });
      return;
    }

    const updateTimer = () => {
      const now = new Date().getTime();
      const target = new Date(deadlineIso).getTime();
      const diffMs = target - now;

      if (diffMs <= 0) {
        setTimeLeft({ text: 'SLA BREACHED', status: 'red' });
        return;
      }

      const diffMins = Math.floor(diffMs / 60000);
      const hours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;
      const secs = Math.floor((diffMs % 60000) / 1000);

      let text = '';
      if (hours > 0) {
        text = `${hours}h ${mins}m left`;
      } else {
        text = `${mins}m ${secs}s left`;
      }

      let status: 'green' | 'amber' | 'red' = 'green';
      if (diffMins < 15) {
        status = 'red';
      } else if (diffMins < 60) {
        status = 'amber';
      }

      setTimeLeft({ text, status });
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [deadlineIso, priority]);

  const colorStyles = {
    green: 'bg-[#F0FDF4] border-[#16A34A]/40 text-[#16A34A]',
    amber: 'bg-[#FFFBEB] border-[#F59E0B]/50 text-[#B45309] animate-pulse',
    red: 'bg-[#FEF2F2] border-[#DC2626]/50 text-[#DC2626] font-bold'
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[10px] font-mono tracking-wider ${
        colorStyles[timeLeft.status]
      }`}
    >
      <Clock className="w-2.5 h-2.5" />
      {timeLeft.text}
    </span>
  );
};

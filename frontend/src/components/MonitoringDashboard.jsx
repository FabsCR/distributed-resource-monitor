"use client";

import { useState, useEffect } from "react";
import { Terminal } from "./Terminal";
import { ComputerCard } from "./ComputerCard";

export default function MonitoringDashboard() {
  const [computers, setComputers] = useState([]);
  const [logs, setLogs] = useState(["> Initializing…"]);

  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const res = await fetch(`${API_URL}/metrics`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        setComputers(data);
        setLogs((l) => [...l, `> Fetched ${data.length} hosts`]);
      } catch (e) {
        setLogs((l) => [...l, `> Error: ${e.message}`]);
      }
    }
    fetchMetrics();
    const id = setInterval(fetchMetrics, 5000);
    return () => clearInterval(id);
  }, [API_URL]);

  return (
    <div className="min-h-screen p-6 bg-gray-100">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {computers.map((c) => (
          <ComputerCard key={c.hostname} computer={c} />
        ))}
      </div>
      <Terminal logs={logs} />
    </div>
  );
}

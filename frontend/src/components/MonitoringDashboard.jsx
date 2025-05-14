// src/components/MonitoringDashboard.jsx
import React, { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Terminal } from "./Terminal";
import { ComputerCard } from "./ComputerCard";

const API_URL = import.meta.env.VITE_API_URL;

async function fetchMetrics() {
  const res = await fetch(`${API_URL}/metrics`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export default function MonitoringDashboard() {
  const [logs, setLogs] = useState([{ type: "info", text: "> Initializing…" }]);
  const [tick, setTick] = useState(0);

  // SSE de Celery
  useEffect(() => {
    const logsUrl = `${API_URL.replace(/\/$/, "")}/logs/stream`;
    console.log("Conectando SSE a:", logsUrl);
    const es = new EventSource(logsUrl);
    es.onopen = () => console.log("SSE conectado");
    es.onerror = (e) => console.error("SSE error", e);

    es.addEventListener("assigned", (e) => {
      const { worker, task } = JSON.parse(e.data);
      setLogs((prev) => [
        ...prev,
        { type: "assigned", text: `${worker} se le asignó ${task}` },
      ]);
    });
    es.addEventListener("finished", (e) => {
      const { worker, task } = JSON.parse(e.data);
      setLogs((prev) => [
        ...prev,
        { type: "finished", text: `${worker} finalizó ${task}` },
      ]);
    });

    return () => es.close();
  }, []);

  // Tick para contadores
  useEffect(() => {
    const iv = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(iv);
  }, []);

  // Única llamada a useQuery (objeto)
  const { data: computers = [] } = useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    refetchInterval: 2000,
    onSuccess(data) {
      setLogs((prev) => [
        ...prev,
        { type: "info", text: `> Fetched ${data.length} hosts at ${new Date().toLocaleTimeString()}` },
      ]);
    },
    onError(error) {
      setLogs((prev) => [
        ...prev,
        { type: "error", text: `> Error: ${error.message}` },
      ]);
    },
  });

  // Calcula edad y re-render con tick
  const withAge = useMemo(() => {
    const now = Date.now();
    return computers.map((c) => {
      const ageMs = now - new Date(c.timestamp).getTime();
      return { ...c, ageMs, ageSec: ageMs / 1000 };
    });
  }, [computers, tick]);

  // Orden fijo
  const sorted = useMemo(
    () => [...withAge].sort((a, b) => a.hostname.localeCompare(b.hostname)),
    [withAge]
  );

  return (
    <div className="min-h-screen p-6 bg-gray-100">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {sorted.map((c) => {
          if (c.ageMs > 30000) return null;
          if (c.ageMs <= 10000) {
            return <ComputerCard key={c.hostname} computer={c} />;
          }
          const remaining = Math.max(0, Math.ceil(30 - c.ageSec));
          const progress = ((c.ageSec - 10) / 20) * 100;

          return (
            <div key={c.hostname} className="w-full shadow-lg rounded-xl bg-white">
              <div className="bg-gray-100 flex justify-between items-center p-4">
                <span className="font-semibold">{c.hostname}</span>
                <span className="text-sm text-gray-600">
                  {new Date(c.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex justify-between items-center">
                  <span className="flex items-center gap-2 text-red-500">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm.75 4a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h2.5a.75.75 0 000-1.5h-1.75V6z"/>
                    </svg>
                    <span className="text-sm text-gray-700">Inactividad</span>
                  </span>
                  <span className="text-red-600 font-medium">{remaining}s</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded overflow-hidden">
                  <div
                    className="h-full bg-red-500 transition-all duration-1000"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 italic">Se eliminará al llegar a 30 s</p>
              </div>
            </div>
          );
        })}
      </div>
      <Terminal logs={logs} />
    </div>
  );
}
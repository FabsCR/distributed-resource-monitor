// src/components/MonitoringDashboard.jsx
import React, { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Terminal } from "./Terminal";
import { ComputerCard } from "./ComputerCard";
import {
  Card,
  CardHeader,
  CardBody,
  Typography,
} from "@material-tailwind/react";
import { Clock } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL;

async function fetchMetrics() {
  const res = await fetch(`${API_URL}/metrics`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export default function MonitoringDashboard() {
  const [logs, setLogs] = useState(["> Initializing…"]);
  const [tick, setTick] = useState(0);

  // Tick cada segundo para forzar re-render y actualizar contadores
  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const { data: computers = [] } = useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    refetchInterval: 2000,
    onSuccess(data) {
      setLogs((prev) => [
        ...prev,
        `> Fetched ${data.length} hosts at ${new Date().toLocaleTimeString()}`,
      ]);
    },
    onError(error) {
      setLogs((prev) => [...prev, `> Error: ${error.message}`]);
    },
  });

  // Calcula edad en ms y s de cada máquina
  const withAge = useMemo(() => {
    const now = Date.now();
    return computers.map((c) => {
      const ageMs = now - new Date(c.timestamp).getTime();
      return { ...c, ageMs, ageSec: ageMs / 1000 };
    });
  }, [computers, tick]);

  // Orden fijo por hostname para que no “salten” de posición
  const sorted = useMemo(
    () => [...withAge].sort((a, b) => a.hostname.localeCompare(b.hostname)),
    [withAge]
  );

  return (
    <div className="min-h-screen p-6 bg-gray-100">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {sorted.map((c) => {
          // >30 s: no renderizar
          if (c.ageMs > 30_000) return null;

          // 0–10 s: host activo, tarjeta normal
          if (c.ageMs <= 10_000) {
            return <ComputerCard key={c.hostname} computer={c} />;
          }

          // 10–30 s: tarjeta de inactividad con contador animado
          const remaining = Math.max(0, Math.ceil(30 - c.ageSec));
          // Progreso: 0% a los 10 s, 100% a los 30 s
          const progress = ((c.ageSec - 10) / 20) * 100;

          return (
            <Card key={c.hostname} className="w-full shadow-lg rounded-xl">
              <CardHeader
                floated={false}
                shadow={false}
                className="bg-gray-100 flex justify-between items-center p-4"
              >
                <Typography variant="h6">{c.hostname}</Typography>
                <Typography variant="small" color="gray">
                  {new Date(c.timestamp).toLocaleTimeString()}
                </Typography>
              </CardHeader>
              <CardBody className="p-6 space-y-4">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <Clock className="w-5 h-5 text-red-500" />
                    <Typography variant="small" color="gray">
                      Tiempo de inactividad
                    </Typography>
                  </div>
                  {/* Añadimos transición al cambio de número */}
                  <Typography
                    variant="small"
                    className="text-red-600 transition-all duration-500"
                  >
                    {remaining}s restantes
                  </Typography>
                </div>

                {/* Barra de progreso animada */}
                <div className="w-full h-2 bg-gray-200 rounded overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded transition-all duration-1000"
                    style={{ width: `${progress}%` }}
                  />
                </div>

                <Typography variant="small" color="gray" className="italic">
                  Esta sesión se cerrará automáticamente por inactividad
                </Typography>
              </CardBody>
            </Card>
          );
        })}
      </div>
      <Terminal logs={logs} />
    </div>
  );
}

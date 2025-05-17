import React, { useMemo, useEffect, useRef } from "react";
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

async function fetchLogs() {
  const res = await fetch(`${API_URL}/logs?limit=10`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json(); 
}

export default function MonitoringDashboard() {
  // machine data
  const { data: computers = [] } = useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    refetchInterval: 2000,
  });

  // logs data
  const { data: rawLogs = [] } = useQuery({
    queryKey: ["task-logs"],
    queryFn: fetchLogs,
    refetchInterval: 2000,
  });

  // prepare logs for Terminal
  const logs = useMemo(() => {
    return rawLogs
      // sort from most recent to oldest
      .slice()
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      // limit to 10
      .slice(0, 10)
      .map((log) => ({
        text: `${log.task_name} ${
          log.delivered ? "completed" : "assigned"
        } by ${log.hostname} @ ${new Date(log.created_at).toLocaleTimeString()}`,
        type: log.delivered ? "finished" : "assigned",
      }));
  }, [rawLogs]);

  // calculate age (as before)
  const withAge = useMemo(() => {
    const now = Date.now();
    return computers.map((c) => {
      let tsRaw = c.timestamp;
      let tsMs =
        typeof tsRaw === "number"
          ? tsRaw < 1e12
            ? tsRaw * 1000
            : tsRaw
          : new Date(tsRaw).getTime();
      const ageMs = now - tsMs;
      return { ...c, ageMs, ageSec: ageMs / 1000, timestamp: tsMs };
    });
  }, [computers]);

  const sorted = useMemo(
    () => [...withAge].sort((a, b) => a.hostname.localeCompare(b.hostname)),
    [withAge]
  );

  return (
    <div className="min-h-screen p-6 bg-gray-100">
      {/* MACHINE CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {sorted.map((c) => {
          if (c.ageMs > 30_000) return null;
          if (c.ageMs <= 10_000) {
            return <ComputerCard key={c.hostname} computer={c} />;
          }
          const remaining = Math.max(0, Math.ceil(30 - c.ageSec));
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
                      Idle time
                    </Typography>
                  </div>
                  <Typography
                    variant="small"
                    className="text-red-600 transition-all duration-500"
                  >
                    {remaining}s remaining
                  </Typography>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded transition-all duration-1000"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <Typography variant="small" color="gray" className="italic">
                  This session will automatically close due to inactivity
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

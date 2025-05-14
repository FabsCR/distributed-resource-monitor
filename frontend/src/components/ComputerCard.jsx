// src/components/ComputerCard.jsx
import React from "react";
import {
  Card,
  CardHeader,
  CardBody,
  Typography,
} from "@material-tailwind/react";
import { Cpu, MemoryStickIcon as Memory, Thermometer } from "lucide-react";

export function ComputerCard({ computer }) {
  const {
    hostname,
    cpu_percent,
    ram_total_mb,
    ram_used_mb,
    ram_percent,
    temperature,
    timestamp,
  } = computer;

  const textColor = (pct) =>
    pct > 80
      ? "text-red-600"
      : pct > 60
      ? "text-yellow-600"
      : "text-green-600";

  return (
    <Card className="w-full shadow-lg rounded-xl">
      <CardHeader
        floated={false}
        shadow={false}
        className="bg-gray-100 flex justify-between items-center p-4"
      >
        <Typography variant="h6" color="blue-gray">
          {hostname}
        </Typography>
        <Typography variant="small" color="gray">
          {new Date(timestamp).toLocaleTimeString()}
        </Typography>
      </CardHeader>
      <CardBody className="p-6 space-y-6">
        {/* CPU */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-blue-500" />
              <Typography variant="small" color="gray">
                CPU
              </Typography>
            </div>
            <Typography variant="small" className={textColor(cpu_percent)}>
              {cpu_percent.toFixed(2)}%
            </Typography>
          </div>
          <div className="h-2 bg-gray-200 rounded overflow-hidden">
            <div
              className={`h-full rounded !bg-gradient-to-tr ${
                cpu_percent > 80
                  ? "from-red-500 to-red-400"
                  : cpu_percent > 60
                  ? "from-yellow-500 to-yellow-400"
                  : "from-green-500 to-green-400"
              } transition-all duration-500`}
              style={{ width: `${cpu_percent}%` }}
            />
          </div>
        </div>

        {/* RAM */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Memory className="w-5 h-5 text-blue-500" />
              <Typography variant="small" color="gray">
                RAM
              </Typography>
            </div>
            <Typography variant="small" className={textColor(ram_percent)}>
              {ram_used_mb.toFixed(2)} / {ram_total_mb.toFixed(2)} MB
            </Typography>
          </div>
          <div className="h-2 bg-gray-200 rounded overflow-hidden">
            <div
              className={`h-full rounded !bg-gradient-to-tr ${
                ram_percent > 80
                  ? "from-red-500 to-red-400"
                  : ram_percent > 60
                  ? "from-yellow-500 to-yellow-400"
                  : "from-green-500 to-green-400"
              } transition-all duration-500`}
              style={{ width: `${ram_percent}%` }}
            />
          </div>
        </div>

        {/* Temperatura */}
        <div className="flex items-center gap-2">
          <Thermometer className="w-5 h-5 text-blue-500" />
          <Typography variant="small" color="gray">
            Temperature: {temperature != null ? `${temperature.toFixed(1)}°C` : "N/A"}
          </Typography>
        </div>
      </CardBody>
    </Card>
  );
}
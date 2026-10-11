"use client";

import React from "react";
import { TaskQueue } from "@/components/queue/TaskQueue";

export default function QueuePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <TaskQueue />
    </div>
  );
}

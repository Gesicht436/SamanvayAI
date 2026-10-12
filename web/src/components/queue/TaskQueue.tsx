"use client";

import React, { useState, useEffect, useCallback } from "react";
import { StewardTask } from "@/types";
import { getTasks, approveTask, rejectTask } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { StatusBadge } from "@/components/common/Badge";
import {
  ListTodo,
  CheckCircle,
  XCircle,
  AlertOctagon,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Hash,
  Keyboard,
  Clock,
} from "lucide-react";

export function TaskQueue() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<StewardTask[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(6);
  const [loading, setLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [kindFilter, setKindFilter] = useState<string>("ALL");
  const [sectorFilter, setSectorFilter] = useState<string>("ALL");

  // Selection & Keyboard navigation
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  // Modals & Bulk actions
  const [activeTask, setActiveTask] = useState<StewardTask | null>(null);
  const [modalMode, setModalMode] = useState<"APPROVE" | "REJECT" | null>(null);
  const [rationale, setRationale] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>([]);
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
  const [bulkRationale, setBulkRationale] = useState("");
  const [bulkProcessing, setBulkProcessing] = useState(false);

  const openModal = useCallback((task: StewardTask, mode: "APPROVE" | "REJECT") => {
    setActiveTask(task);
    setModalMode(mode);
    setRationale("");
    setActionError(null);
    setActionSuccess(null);
  }, []);

  const closeModal = useCallback(() => {
    setActiveTask(null);
    setModalMode(null);
    setRationale("");
    setActionError(null);
  }, []);

  const refreshTasks = useCallback(() => {
    setLoading(true);
    getTasks({
      status: statusFilter,
      kind: kindFilter,
      sector: sectorFilter,
      page,
      size: pageSize,
    }).then((res) => {
      setTasks(res.items);
      setTotal(res.total);
      setLoading(false);
    });
  }, [statusFilter, kindFilter, sectorFilter, page, pageSize]);

  useEffect(() => {
    let active = true;
    getTasks({
      status: statusFilter,
      kind: kindFilter,
      sector: sectorFilter,
      page,
      size: pageSize,
    }).then((res) => {
      if (active) {
        setTasks(res.items);
        setTotal(res.total);
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, [statusFilter, kindFilter, sectorFilter, page, pageSize]);

  // Keyboard navigation shortcuts: J (down), K (up), A (approve), R (reject)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept typing in inputs or textareas
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA" ||
        modalMode !== null
      ) {
        return;
      }

      if (e.key === "j" || e.key === "J") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(tasks.length - 1, prev + 1));
      } else if (e.key === "k" || e.key === "K") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(0, prev - 1));
      } else if (e.key === "a" || e.key === "A") {
        if (tasks[selectedIndex] && tasks[selectedIndex].status === "PROPOSED") {
          e.preventDefault();
          openModal(tasks[selectedIndex], "APPROVE");
        }
      } else if (e.key === "r" || e.key === "R") {
        if (tasks[selectedIndex] && tasks[selectedIndex].status === "PROPOSED") {
          e.preventDefault();
          openModal(tasks[selectedIndex], "REJECT");
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [tasks, selectedIndex, modalMode, openModal]);

  const handleActionSubmit = async () => {
    if (!activeTask || !modalMode) return;
    if (!rationale.trim()) {
      setActionError("A formal engineering rationale is required for the immutable audit log.");
      return;
    }

    if (modalMode === "APPROVE") {
      const res = await approveTask(activeTask.id, rationale, user);
      if (res.success) {
        setActionSuccess(
          `Task approved successfully! Audit Seq: #${res.audit_seq} | Hash: ${res.audit_hash?.substring(0, 16)}...`
        );
        setTimeout(() => {
          closeModal();
          refreshTasks();
        }, 1500);
      } else {
        setActionError(res.message);
      }
    } else {
      const res = await rejectTask(activeTask.id, rationale, user);
      if (res.success) {
        setActionSuccess("Task rejected and recorded in audit log.");
        setTimeout(() => {
          closeModal();
          refreshTasks();
        }, 1200);
      } else {
        setActionError(res.message);
      }
    }
  };

  const handleBulkSubmit = async () => {
    if (selectedTaskIds.length === 0 || !bulkRationale.trim()) {
      setActionError("A formal engineering rationale is required for the immutable audit log.");
      return;
    }
    setBulkProcessing(true);
    setActionError(null);
    for (const taskId of selectedTaskIds) {
      await approveTask(taskId, bulkRationale, user);
    }
    setBulkProcessing(false);
    setIsBulkModalOpen(false);
    setSelectedTaskIds([]);
    setBulkRationale("");
    refreshTasks();
  };

  const proposedOnPage = tasks.filter((t) => t.status === "PROPOSED");
  const allProposedSelected =
    proposedOnPage.length > 0 && proposedOnPage.every((t) => selectedTaskIds.includes(t.id));

  const toggleSelectAllProposed = () => {
    if (allProposedSelected) {
      setSelectedTaskIds([]);
    } else {
      setSelectedTaskIds(proposedOnPage.map((t) => t.id));
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header & Keyboard shortcuts legend */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-lg p-5">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <ListTodo className="w-5 h-5 text-emerald-400" />
            Stewardship Governance Queue
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Maker-Checker workflow ($Maker \ne Checker$) enforcing safety-critical domain tags and transactional SHA-256 audit logs.
          </p>
        </div>

        {/* Keyboard shortcut hint */}
        <div className="flex items-center gap-2 text-xs font-mono bg-slate-950 px-3 py-1.5 rounded border border-slate-800 text-slate-400">
          <Keyboard className="w-3.5 h-3.5 text-emerald-400" />
          <span>
            <kbd className="bg-slate-800 px-1 py-0.5 rounded text-slate-200">J</kbd>/<kbd className="bg-slate-800 px-1 py-0.5 rounded text-slate-200">K</kbd> Navigate &middot;{" "}
            <kbd className="bg-slate-800 px-1 py-0.5 rounded text-emerald-300">A</kbd> Approve &middot;{" "}
            <kbd className="bg-slate-800 px-1 py-0.5 rounded text-rose-300">R</kbd> Reject
          </span>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className="text-slate-400">Status:</span>
          <select
            aria-label="Filter Tasks by Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded px-2.5 py-1 focus:ring-1 focus:ring-emerald-500"
          >
            <option value="ALL">ALL STATUSES</option>
            <option value="PROPOSED">PROPOSED</option>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className="text-slate-400">Kind:</span>
          <select
            aria-label="Filter Tasks by Kind"
            value={kindFilter}
            onChange={(e) => {
              setKindFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded px-2.5 py-1 focus:ring-1 focus:ring-emerald-500"
          >
            <option value="ALL">ALL KINDS</option>
            <option value="LINK">LINK</option>
            <option value="CREATE_MASTER">CREATE_MASTER</option>
            <option value="MERGE">MERGE</option>
            <option value="SPLIT">SPLIT</option>
            <option value="CORRECT_ATTR">CORRECT_ATTR</option>
            <option value="DOC_REVIEW">DOC_REVIEW</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className="text-slate-400">Sector:</span>
          <select
            aria-label="Filter Tasks by Sector"
            value={sectorFilter}
            onChange={(e) => {
              setSectorFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded px-2.5 py-1 focus:ring-1 focus:ring-emerald-500"
          >
            <option value="ALL">ALL SECTORS</option>
            <option value="COMMON">COMMON</option>
            <option value="POWER">POWER</option>
            <option value="STEEL">STEEL</option>
            <option value="MINING">MINING</option>
            <option value="HEAVY_ENG">HEAVY_ENG</option>
          </select>
        </div>

        <div className="ml-auto text-xs font-mono text-slate-400">
          Total Tasks: <strong className="text-slate-200">{total}</strong>
        </div>
      </div>

      {/* Cluster Bulk Action Toolbar */}
      {proposedOnPage.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 border border-slate-800 rounded-lg p-3 text-xs font-mono">
          <label className="flex items-center gap-2 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={allProposedSelected}
              onChange={toggleSelectAllProposed}
              className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-emerald-500 cursor-pointer"
            />
            <span>Select All Proposed ({proposedOnPage.length})</span>
          </label>

          {selectedTaskIds.length > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-emerald-400 font-semibold">
                {selectedTaskIds.length} tasks selected
              </span>
              <button
                type="button"
                onClick={() => {
                  setBulkRationale("");
                  setActionError(null);
                  setIsBulkModalOpen(true);
                }}
                className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold transition-colors shadow-md shadow-emerald-950/40"
              >
                Bulk Approve Selected ({selectedTaskIds.length})
              </button>
              <button
                type="button"
                onClick={() => setSelectedTaskIds([])}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}

      {/* Task List / Table */}
      {loading ? (
        <div className="p-12 text-center text-xs font-mono text-slate-400 bg-slate-900 rounded-lg border border-slate-800 animate-pulse">
          Loading stewardship tasks...
        </div>
      ) : tasks.length === 0 ? (
        <div className="p-12 text-center bg-slate-900 rounded-lg border border-slate-800 space-y-2">
          <ListTodo className="w-8 h-8 text-slate-600 mx-auto" />
          <p className="text-sm font-medium text-slate-300">No stewardship tasks match filter</p>
          <p className="text-xs text-slate-500">Change status or sector filter to inspect other tasks.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task, idx) => {
            const isSelected = idx === selectedIndex;
            const isProposer = task.proposed_by === user.id;
            const hasDomainTag =
              user.domains.includes(task.sector) || user.domains.includes("COMMON");

            return (
              <div
                key={task.id}
                onClick={() => setSelectedIndex(idx)}
                className={`p-4 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? "bg-slate-900/90 border-emerald-500/60 shadow-lg shadow-emerald-950/20"
                    : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {task.status === "PROPOSED" && (
                      <input
                        type="checkbox"
                        checked={selectedTaskIds.includes(task.id)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          e.stopPropagation();
                          setSelectedTaskIds((prev) =>
                            prev.includes(task.id)
                              ? prev.filter((id) => id !== task.id)
                              : [...prev, task.id]
                          );
                        }}
                        className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-emerald-500 cursor-pointer"
                      />
                    )}
                    <span className="text-xs font-mono text-slate-400">#{task.id}</span>
                    <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                      {task.kind}
                    </span>
                    <span className="text-xs font-mono text-emerald-400">
                      {task.subcategory}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      {task.sector}
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusBadge status={task.status} />
                    <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>

                {/* Task Content / Description */}
                <div className="mt-2.5 text-xs font-mono text-slate-300 bg-slate-950/70 p-2.5 rounded border border-slate-800/80">
                  {task.kind === "LINK" && (
                    <div>
                      Link Raw: <span className="text-slate-100">{String(task.payload.raw_description ?? "")}</span> → Master:{" "}
                      <span className="text-emerald-400 font-bold">{String(task.payload.golden_code ?? "")}</span>
                    </div>
                  )}
                  {task.kind === "CREATE_MASTER" && (
                    <div>
                      Create Master: <span className="text-emerald-300 font-semibold">{String(task.payload.descriptor ?? "")}</span>
                    </div>
                  )}
                  {task.kind === "MERGE" && (
                    <div>
                      Merge Source <span className="text-rose-400">{String(task.payload.source_code ?? "")}</span> into{" "}
                      <span className="text-emerald-400">{String(task.payload.target_code ?? "")}</span>
                    </div>
                  )}
                  {task.kind === "CORRECT_ATTR" && (
                    <div>
                      Correct Attribute <span className="text-amber-400">{String(task.payload.attr_name ?? "")}</span>:{" "}
                      <span className="line-through text-slate-500">{String(task.payload.old_value ?? "")}</span> →{" "}
                      <span className="text-emerald-400">{String(task.payload.new_value ?? "")}</span>
                    </div>
                  )}
                  {task.kind === "DOC_REVIEW" && (
                    <div>
                      Doc OCR Review: <span className="text-slate-200">{String(task.payload.ocr_text ?? "")}</span>
                    </div>
                  )}
                </div>

                {/* Proposer Info & Governance Notes */}
                <div className="mt-2.5 flex flex-wrap items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60">
                  <div className="flex items-center gap-4">
                    <span>
                      Maker: <strong className="text-slate-300 font-mono">{task.proposed_by}</strong>
                    </span>
                    {task.approved_by && (
                      <span>
                        Checker: <strong className="text-emerald-300 font-mono">{task.approved_by}</strong>
                      </span>
                    )}
                    {task.audit_seq && (
                      <span className="text-[11px] font-mono text-emerald-400/90 flex items-center gap-1">
                        <Hash className="w-3 h-3" />
                        Audit Seq: #{task.audit_seq}
                      </span>
                    )}
                  </div>

                  {/* Maker-Checker Action Buttons */}
                  {task.status === "PROPOSED" && (
                    <div className="flex items-center gap-2">
                      {isProposer && (
                        <span className="text-[11px] text-amber-400 font-mono flex items-center gap-1 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-600/30">
                          <AlertOctagon className="w-3 h-3" />
                          Maker-Checker Violation: You proposed this
                        </span>
                      )}

                      {!hasDomainTag && (
                        <span className="text-[11px] text-rose-400 font-mono flex items-center gap-1 bg-rose-950/40 px-2 py-0.5 rounded border border-rose-600/30">
                          <ShieldAlert className="w-3 h-3" />
                          Lacks domain tag [{task.sector}]
                        </span>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openModal(task, "APPROVE");
                        }}
                        disabled={isProposer || (!hasDomainTag && user.role !== "ADMIN")}
                        className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-600 text-slate-950 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        Approve
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openModal(task, "REJECT");
                        }}
                        className="px-2.5 py-1 rounded text-xs font-semibold bg-rose-900/60 text-rose-200 hover:bg-rose-900 border border-rose-700/60 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>

                {task.rejection_reason && (
                  <div className="mt-2 text-xs text-rose-300 bg-rose-950/40 p-2 rounded border border-rose-600/30 font-mono">
                    Rejection Rationale: {task.rejection_reason}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Server-Side Pagination Controls */}
      <div className="flex items-center justify-between text-xs font-mono text-slate-400 bg-slate-900 p-3 rounded-lg border border-slate-800">
        <div>
          Page <strong className="text-slate-200">{page}</strong> of{" "}
          <strong className="text-slate-200">{totalPages}</strong>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="p-1.5 rounded bg-slate-800 text-slate-200 disabled:opacity-40 hover:bg-slate-700 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="p-1.5 rounded bg-slate-800 text-slate-200 disabled:opacity-40 hover:bg-slate-700 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Approve / Reject Modal Dialog */}
      {modalMode && activeTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-lg w-full space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                {modalMode === "APPROVE" ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    Checker Approval — Task #{activeTask.id}
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 text-rose-400" />
                    Checker Rejection — Task #{activeTask.id}
                  </>
                )}
              </h3>
              <button
                type="button"
                onClick={closeModal}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                ✕ Esc
              </button>
            </div>

            <div className="text-xs font-mono text-slate-300 bg-slate-950 p-3 rounded border border-slate-800">
              Kind: <strong className="text-emerald-400">{activeTask.kind}</strong> &middot; Subcategory:{" "}
              <strong className="text-slate-200">{activeTask.subcategory}</strong>
            </div>

            <div>
              <label className="text-xs font-mono text-slate-300 block mb-1">
                Engineering Rationale (Appended to SHA-256 Audit Log) *
              </label>
              <textarea
                rows={3}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder={
                  modalMode === "APPROVE"
                    ? "e.g. Technical datasheet and inspection certificate verified against spec..."
                    : "e.g. Failed safety lattice check due to non-substitutable rating..."
                }
                className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            {actionError && (
              <div className="p-3 rounded bg-rose-950/70 border border-rose-500/40 text-rose-300 text-xs font-mono">
                {actionError}
              </div>
            )}

            {actionSuccess && (
              <div className="p-3 rounded bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 text-xs font-mono">
                {actionSuccess}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={closeModal}
                className="px-3 py-1.5 rounded text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleActionSubmit}
                className={`px-4 py-1.5 rounded text-xs font-semibold transition-colors ${
                  modalMode === "APPROVE"
                    ? "bg-emerald-600 text-slate-950 hover:bg-emerald-500 shadow-lg shadow-emerald-950/50"
                    : "bg-rose-600 text-white hover:bg-rose-500 shadow-lg shadow-rose-950/50"
                }`}
              >
                Confirm {modalMode === "APPROVE" ? "Approval" : "Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cluster Bulk Approval Modal */}
      {isBulkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-lg w-full space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                Cluster Bulk Approval ({selectedTaskIds.length} tasks)
              </h3>
              <button
                type="button"
                onClick={() => setIsBulkModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                ✕ Esc
              </button>
            </div>

            <p className="text-xs text-slate-400 font-sans">
              Apply collective maker-checker approval to {selectedTaskIds.length} stewardship tasks. Each task writes a distinct SHA-256 audit entry.
            </p>

            <div>
              <label className="text-xs font-mono text-slate-300 block mb-1">
                Collective Engineering Rationale *
              </label>
              <textarea
                rows={3}
                value={bulkRationale}
                onChange={(e) => setBulkRationale(e.target.value)}
                placeholder="e.g. Batch verified against OEM catalog revision and standard specifications..."
                className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            {actionError && (
              <div className="p-3 rounded bg-rose-950/70 border border-rose-500/40 text-rose-300 text-xs font-mono">
                {actionError}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsBulkModalOpen(false)}
                disabled={bulkProcessing}
                className="px-3 py-1.5 rounded text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleBulkSubmit}
                disabled={bulkProcessing || !bulkRationale.trim()}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-emerald-600 text-slate-950 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-lg shadow-emerald-950/50"
              >
                {bulkProcessing ? "Processing..." : `Confirm Approval (${selectedTaskIds.length})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

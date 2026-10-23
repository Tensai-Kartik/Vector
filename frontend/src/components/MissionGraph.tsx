import React, { useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  Node,
  Edge,
  Position,
  Handle,
  BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ShieldCheck, CheckCircle2, XCircle, Zap } from 'lucide-react';
import { MissionStepState } from '../types';

interface MissionGraphProps {
  steps: MissionStepState[];
  selectedStepId?: string;
  onSelectStep: (stepId: string) => void;
  missionStatus?: string;
}

// Custom Node for Mission Graph
const CustomStepNode = ({ data }: any) => {
  const { title, subtitle, status, isSelected, actionType, icon: Icon } = data;

  const getStatusColor = () => {
    switch (status) {
      case 'running':
      case 'validating':
        return 'border-[#d4ff00] bg-[#0c121d] shadow-lg shadow-[#d4ff00]/10';
      case 'completed':
        return 'border-emerald-500/50 bg-[#091512]';
      case 'rejected':
      case 'failed':
        return 'border-rose-500/60 bg-[#160b0d]';
      case 'awaiting_approval':
        return 'border-amber-400 bg-amber-950/30 animate-pulse';
      default:
        return 'border-white/10 bg-[#080c13] opacity-80';
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'running':
      case 'validating':
        return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-[#d4ff00] text-black font-bold animate-pulse">ACTIVE</span>;
      case 'completed':
        return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-emerald-500/20 text-emerald-400 font-semibold flex items-center gap-1"><CheckCircle2 className="w-2.5 h-2.5" /> VERIFIED</span>;
      case 'rejected':
        return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-rose-500/20 text-rose-400 font-semibold flex items-center gap-1"><XCircle className="w-2.5 h-2.5" /> REJECTED</span>;
      case 'failed':
        return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-rose-500/20 text-rose-400 font-semibold">FAILED</span>;
      case 'awaiting_approval':
        return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-300 font-semibold">APPROVAL REQUIRED</span>;
      default:
        return <span className="text-[9px] font-mono text-slate-500">PENDING</span>;
    }
  };

  return (
    <div
      className={`px-3.5 py-3 rounded-xl border text-left min-w-[210px] max-w-[270px] cursor-pointer transition shadow-xl ${getStatusColor()} ${
        isSelected ? 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-black' : ''
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-600 !w-2 !h-2" />
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          {Icon ? <Icon className="w-3.5 h-3.5 text-cyan-400 shrink-0" /> : <Zap className="w-3.5 h-3.5 text-[#d4ff00] shrink-0" />}
          <span className="font-mono text-xs font-bold text-white truncate">{title}</span>
        </div>
        {getStatusBadge()}
      </div>
      <p className="text-[11px] text-slate-300 line-clamp-2 leading-tight">{subtitle}</p>
      {actionType && (
        <div className="mt-2 pt-1 border-t border-white/5 flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span>OP: <span className="text-cyan-400">{actionType}</span></span>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-600 !w-2 !h-2" />
    </div>
  );
};

const nodeTypes = {
  customStep: CustomStepNode,
};

export const MissionGraph: React.FC<MissionGraphProps> = ({
  steps,
  selectedStepId,
  onSelectStep,
  missionStatus = 'ready',
}) => {
  const { nodes, edges } = useMemo(() => {
    const rawNodes: Node[] = [];
    const rawEdges: Edge[] = [];

    let currentY = 50;

    // Root Node: Task Ingestion & Planning
    rawNodes.push({
      id: 'node-plan',
      type: 'customStep',
      position: { x: 300, y: currentY },
      data: {
        title: 'Task Ingestion & Plan',
        subtitle: 'Deconstruct NL instruction into typed action plan',
        status: steps.length > 0 ? 'completed' : (missionStatus === 'planning' ? 'running' : 'pending'),
        icon: Zap,
        isSelected: selectedStepId === 'node-plan',
      },
    });

    currentY += 120;
    let lastNodeId = 'node-plan';

    if (steps.length > 0) {
      steps.forEach((step, idx) => {
        const stepNodeId = `step-${step.step_id}`;
        rawNodes.push({
          id: stepNodeId,
          type: 'customStep',
          position: { x: 300, y: currentY },
          data: {
            title: `Step ${idx + 1}: ${step.action_type.toUpperCase()}`,
            subtitle: step.intent,
            status: step.status,
            actionType: step.action_type,
            isSelected: selectedStepId === step.step_id,
          },
        });

        rawEdges.push({
          id: `e-${lastNodeId}-${stepNodeId}`,
          source: lastNodeId,
          target: stepNodeId,
          animated: step.status === 'running' || step.status === 'validating',
        });

        lastNodeId = stepNodeId;
        currentY += 120;
      });
    }

    // Final Node: Outcome Verification
    rawNodes.push({
      id: 'node-verify',
      type: 'customStep',
      position: { x: 300, y: currentY },
      data: {
        title: 'Outcome Verifier',
        subtitle: 'Independent Proof Check & Audit Synthesis',
        status: missionStatus === 'completed' ? 'completed' : (missionStatus === 'failed' ? 'failed' : 'pending'),
        icon: ShieldCheck,
        isSelected: selectedStepId === 'node-verify',
      },
    });

    rawEdges.push({
      id: `e-${lastNodeId}-verify`,
      source: lastNodeId,
      target: 'node-verify',
      animated: missionStatus === 'running' && steps.every(s => s.status === 'completed'),
    });

    return { nodes: rawNodes, edges: rawEdges };
  }, [steps, selectedStepId, missionStatus]);

  return (
    <div
      className="w-full h-[380px] sm:h-[460px] lg:h-[520px] relative bg-[#0b0f17] border border-white/10 rounded-2xl overflow-hidden shadow-2xl"
    >
      <div className="absolute top-3 left-3 z-10 flex items-center space-x-2 bg-[#080c13]/90 backdrop-blur-md px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-xl border border-white/10 text-[11px] sm:text-xs font-mono pointer-events-none">
        <Zap className="w-3.5 h-3.5 text-[#d4ff00]" />
        <span className="text-slate-200">MISSION GRAPH</span>
        <span className="text-[10px] text-slate-500">({nodes.length} Nodes)</span>
      </div>

      <div className="w-full h-full">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            onNodeClick={(_, node) => onSelectStep(node.id)}
            minZoom={0.5}
            maxZoom={1.5}
            style={{ width: '100%', height: '100%' }}
          >
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#1c2738" />
            <Controls className="!bg-[#080c13] !border-white/10 !fill-slate-300" />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
    </div>
  );
};

export default MissionGraph;
